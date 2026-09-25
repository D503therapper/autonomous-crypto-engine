"""Live paper-trading engine for crypto and stocks.

    python run_live.py                  # one full cycle (every strategy, every market)
    python run_live.py --watch 350      # stay on for 350 minutes: live stop/target checks every
                                        # second (crypto) / 15s (stocks), full strategy cycle hourly
Every strategy in every market has its own $500 paper account under data/<market>/<strategy>/.
"""
import argparse
import json
import os
import subprocess
import time
import urllib.request

import config
from engine import Portfolio, append_csv, step, ts
from markets import MARKETS
from strategy import regime_ok

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")   # phone alerts via the free ntfy app


def notify(title, msg, priority="default"):
    print(f"   [alert] {title}: {msg}")
    if not NTFY_TOPIC:
        return
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode(),
                                     headers={"Title": title, "Priority": priority})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"   alert failed: {e}")


def acct_dir(mname, sname):
    return f"data/{mname}/{sname}"


def load_pf(mname, sname):
    m = MARKETS[mname]
    return Portfolio.load(f"{acct_dir(mname, sname)}/portfolio.json", fee=m["fee"], slippage=m["slippage"])


def save_pf(mname, sname, pf, n_before, prices):
    d = acct_dir(mname, sname)
    new = pf.trades[n_before:]
    append_csv(f"{d}/trades.csv", new)
    pf.save(f"{d}/portfolio.json")
    for t in new:
        pnl = "" if t["pnl"] is None else f", P/L ${t['pnl']:+.2f}"
        print(f"   >> {mname}/{sname}: {t['side']} ${t['usd']:.2f} of {t['coin']} @ {t['price']:g}{pnl} ({t['reason']})")
    return pf.equity(prices)


def check_new_listings(client):
    """Crypto has no IPOs; the closest thing is a new coin listing. Flag only, never auto-buy."""
    now = client.list_spot_symbols()
    new = []
    if os.path.exists(config.LISTINGS_FILE):
        with open(config.LISTINGS_FILE) as f:
            new = sorted(set(now) - set(json.load(f)))
    os.makedirs(os.path.dirname(config.LISTINGS_FILE), exist_ok=True)
    with open(config.LISTINGS_FILE, "w") as f:
        json.dump(now, f)
    return new


def full_cycle(mname, client):
    """Pull candles, run every strategy in this market, log equity."""
    m = MARKETS[mname]
    if mname == "stocks" and not client.market_open():
        return {}
    syms = sorted({s for st in m["strategies"] for s in st.universe} | {m["benchmark"]})
    data = {}
    for s in syms:
        try:
            data[s] = client.candles(s)
        except Exception as e:
            print(f"  skip {s}: {e}")
    prices = {s: cs[-1]["c"] for s, cs in data.items() if cs}
    ok = regime_ok([c["c"] for c in data.get(m["benchmark"], [])], m["bars_per_day"])
    now = ts(int(time.time() * 1000))
    for st in m["strategies"]:
        pf = load_pf(mname, st.name)
        n_before, was_halted = len(pf.trades), pf.halted
        step(pf, {s: data[s] for s in st.universe if s in data}, st, ok)
        eq = save_pf(mname, st.name, pf, n_before, prices)
        append_csv(f"{acct_dir(mname, st.name)}/equity.csv",
                   [{"time": now, "equity": round(eq, 2), "cash": round(pf.cash, 2),
                     "positions": len(pf.positions)}])
        if pf.halted and not was_halted:
            notify(f"{mname}/{st.name} paused", f"Equity ${eq:,.2f}: drawdown limit hit, "
                   f"new trades paused {config.HALT_HOURS // 24} days.", "high")
        print(f"[{now} UTC] {mname}/{st.name:9} equity ${eq:,.2f} "
              f"({eq / config.STARTING_CASH_USD - 1:+.1%}) {len(pf.positions)} open"
              f"{'  [HALTED]' if pf.halted else ''}  market {'UP' if ok else 'DOWN'}")
    if mname == "crypto":
        try:
            for coin in check_new_listings(client):
                print(f"   ** new Crypto.com listing: {coin} (watch only, not traded)")
        except Exception as e:
            print(f"   listing check failed: {e}")
    return prices


def fast_check(mname, client):
    """Live check (every 1s crypto / 15s stocks): exit positions whose stop or target was hit."""
    if mname == "stocks" and not client.market_open():
        return
    held = {}
    for st in MARKETS[mname]["strategies"]:
        pf = load_pf(mname, st.name)
        if pf.positions:
            held[st] = pf
    syms = {s for pf in held.values() for s in pf.positions}
    if not syms:
        return
    try:
        px = client.last_prices(sorted(syms))
    except Exception as e:
        print(f"   price check failed: {e}")
        return
    now = int(time.time() * 1000)
    for st, pf in held.items():
        n_before = len(pf.trades)
        for s in list(pf.positions):
            p, pos = px.get(s), pf.positions[s]
            if p is None:
                continue
            if p <= pos["stop"]:
                pf.sell(now, s, 1.0, p, "stop hit (live check)")
            elif st.name == "breakout" and not pos["took_profit"] and \
                    p >= pos["entry"] * (1 + config.BREAKOUT["take_profit"]):
                pf.sell(now, s, 0.5, p, f"secured +{config.BREAKOUT['take_profit']:.0%} (live check)")
                pos["took_profit"] = True
                pos["stop"] = max(pos["stop"], pos["entry"] * 1.01)
        if len(pf.trades) > n_before:
            save_pf(mname, st.name, pf, n_before, px)


def scoreboard():
    """Write SCOREBOARD.md: every paper account side by side."""
    rows = []
    for mname, m in MARKETS.items():
        for st in m["strategies"]:
            d = acct_dir(mname, st.name)
            eq, n = config.STARTING_CASH_USD, 0
            if os.path.exists(f"{d}/equity.csv"):
                with open(f"{d}/equity.csv") as f:
                    lines = f.read().strip().splitlines()
                if len(lines) > 1:
                    eq = float(lines[-1].split(",")[1])
            if os.path.exists(f"{d}/trades.csv"):
                with open(f"{d}/trades.csv") as f:
                    n = max(0, len(f.read().strip().splitlines()) - 1)
            rows.append((mname, st.name, eq, n))
    rows.sort(key=lambda r: -r[2])
    out = ["# Paper trading scoreboard", "",
           f"Updated {ts(int(time.time() * 1000))} UTC. Each account started with "
           f"${config.STARTING_CASH_USD:,.0f} of pretend money.", "",
           "| Rank | Market | Strategy | Balance | Return | Trades |", "|---|---|---|---|---|---|"]
    for i, (mn, sn, eq, n) in enumerate(rows, 1):
        out.append(f"| {i} | {mn} | {sn} | ${eq:,.2f} | {eq / config.STARTING_CASH_USD - 1:+.1%} | {n} |")
    total = sum(r[2] for r in rows)
    out += ["", f"**All accounts combined: ${total:,.2f}** "
            f"({total - config.STARTING_CASH_USD * len(rows):+,.2f} on ${config.STARTING_CASH_USD * len(rows):,.0f} of pretend money)"]
    with open("SCOREBOARD.md", "w") as f:
        f.write("\n".join(out) + "\n")
    return rows


def daily_summary(rows):
    """One evening message: today's profit/loss and total, per market."""
    stamp = "data/last_summary.json"
    today = time.strftime("%Y-%m-%d", time.gmtime())
    prev = {}
    if os.path.exists(stamp):
        with open(stamp) as f:
            prev = json.load(f)
    if prev.get("date") == today or time.gmtime().tm_hour < 22:   # once a day, ~6pm US Eastern
        return
    start = config.STARTING_CASH_USD
    lines, now_bal = [], {}
    for mn, sn, eq, _ in rows:
        key = f"{mn}/{sn}"
        now_bal[key] = eq
        day = eq - prev.get("balances", {}).get(key, start)
        lines.append(f"{key}: ${eq:,.2f}  today {day:+,.2f}  total {eq - start:+,.2f}")
    total = sum(now_bal.values())
    day_total = total - sum(prev.get("balances", {}).get(k, start) for k in now_bal)
    notify(f"Today {day_total:+,.2f} | Total {total - start * len(now_bal):+,.2f}", "\n".join(lines))
    with open(stamp, "w") as f:
        json.dump({"date": today, "balances": now_bal}, f)


def git_sync():
    """In the cloud runner: commit the paper accounts back to GitHub every hour."""
    if os.environ.get("GIT_AUTOPUSH") != "1":
        return
    cmds = ["git add data SCOREBOARD.md",
            f"git commit -qm 'paper-trade {ts(int(time.time() * 1000))} UTC'",
            "git pull -q --rebase -X theirs", "git push -q"]
    for c in cmds:
        if subprocess.run(c, shell=True).returncode and c.startswith("git commit"):
            return   # nothing changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0, help="minutes to stay on (0 = one cycle)")
    a = ap.parse_args()
    clients = {m: MARKETS[m]["client"]() for m in MARKETS}
    end = time.time() + a.watch * 60
    fast_every = {"crypto": 1, "stocks": 15}   # seconds between live stop/target checks
    last_fast = {m: 0.0 for m in clients}
    last_hour = None
    while True:
        hour = time.strftime("%Y%m%d%H", time.gmtime())
        if hour != last_hour and time.gmtime().tm_min >= 1:   # new hourly candle has closed
            for m, c in clients.items():
                try:
                    full_cycle(m, c)
                except Exception as e:
                    print(f"{m} cycle failed: {e}")
            daily_summary(scoreboard())
            git_sync()
            last_hour = hour
        for m, c in clients.items():
            if time.time() - last_fast[m] >= fast_every[m]:
                last_fast[m] = time.time()
                try:
                    fast_check(m, c)
                except Exception as e:
                    print(f"{m} fast check failed: {e}")
        if time.time() >= end or not a.watch:
            break
        time.sleep(1 - time.time() % 1)

if __name__ == "__main__":
    main()
