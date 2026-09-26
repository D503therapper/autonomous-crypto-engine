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
import dashboard
import dex
import social
from engine import Portfolio, append_csv, is_runner, open_trades, runner_stop_hit, step, ts
from markets import MARKETS
from scanner import MinuteScanner, describe
from signals import ListingNoticeReactor, PrePumpFootprint, PumpGuard
from strategy import regime_ok

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")   # phone alerts via the free ntfy app
CRYPTO_CANDLES = {}   # hourly candles from the last crypto cycle (warm-starts the minute scanner)
_CRYPTO = {s.name: s for s in MARKETS["crypto"]["strategies"]}
EARLY, MOVER, ANNOUNCE = _CRYPTO["early_mover"], _CRYPTO["mover"], _CRYPTO["announce"]


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
    bpd = m["bars_per_day"]
    need = max(max(st.min_candles for st in m["strategies"]) + 10, config.CANDLES_NEEDED)
    bench_need = max(getattr(st, "regime_days", config.REGIME_DAYS) for st in m["strategies"]) * bpd + 10
    data = {}
    for s in syms:
        try:
            data[s] = client.candles(s, count=max(need, bench_need) if s == m["benchmark"] else need)
        except Exception as e:
            print(f"  skip {s}: {e}")
    # strategies that scan the whole exchange: refresh their coin list and pull a
    # short history (one API call per coin) for coins not already loaded. Every such
    # strategy reads the same candles, so pull the longest window any of them needs.
    dyn = [st for st in m["strategies"] if getattr(st, "dynamic_universe", False)]
    dyn_window = max((st.window for st in dyn), default=0)
    for st in dyn:
        try:
            st.universe = client.list_spot_symbols()
        except Exception as e:
            print(f"   coin list failed: {e}")
        for s in st.universe:
            if s not in data:
                try:
                    data[s] = client.candles(s, count=dyn_window)
                except Exception:
                    pass
    if mname == "crypto":
        CRYPTO_CANDLES.clear()
        CRYPTO_CANDLES.update(data)
    prices = {s: cs[-1]["c"] for s, cs in data.items() if cs}
    bench_closes = [c["c"] for c in data.get(m["benchmark"], [])]
    now = ts(int(time.time() * 1000))
    for st in m["strategies"]:
        ok = regime_ok(bench_closes, bpd, getattr(st, "regime_days", None))
        pf = load_pf(mname, st.name)
        n_before, was_halted = len(pf.trades), pf.halted
        coins = {s: data[s] for s in st.universe if s in data}
        step(pf, social.tag(coins) if getattr(st, "needs_coin", False) else coins, st, ok, runners=mname == "crypto")
        if st is EARLY:                                # keep the official listing hunter fully invested
            park_idle(pf, int(time.time() * 1000), prices, park_targets())
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
                print(f"   ** new Crypto.com listing: {coin} (early_mover buys it in its first hours)")
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
            if p is None or pos.get("park"):          # parked idle cash has no stop
                continue
            if hasattr(st, "trail"):
                pos["peak"] = max(pos["peak"], p)
                pos["stop"] = max(pos["stop"], pos["peak"] * (1 - st.trail))
            runner = mname == "crypto" and is_runner(pos, p)
            if runner and runner_stop_hit(pos, p):
                pf.sell(now, s, 1.0, p, f"runner trail: gave back {config.MOON['trail']:.0%} from its high (live check)")
            elif p <= pos["stop"]:
                if pf.sell(now, s, 1.0, p, "stop hit (live check)") < 0:
                    pf.cooldown[s] = now + config.COOLDOWN_CANDLES * 3_600_000   # as in engine.step
            elif st.name == "breakout" and not runner and not pos["took_profit"] and \
                    p >= pos["entry"] * (1 + config.BREAKOUT["take_profit"]):
                pf.sell(now, s, 0.5, p, f"secured +{config.BREAKOUT['take_profit']:.0%} (live check)")
                pos["took_profit"] = True
                pos["stop"] = max(pos["stop"], pos["entry"] * 1.01)
        if len(pf.trades) > n_before or hasattr(st, "trail"):
            save_pf(mname, st.name, pf, n_before, px)


def guard_check(guard, scanner, coin):
    """signals.PumpGuard verdict for one coin: latest ticker (24h change) + ring buffer (last-hour
    spike-and-fade) from the minute scanner, hourly candles as the 24h fallback."""
    return guard.check(coin, int(time.time() * 1000), cur=scanner.last.get(coin),
                       buf=scanner.hist.get(coin), candles=CRYPTO_CANDLES.get(coin))


def early_veto(guard, scanner):
    """Hook for engine.step: vetoes the hourly EarlyMover buys through the same pump guard."""
    def veto(coin, sig):
        ok, why = guard_check(guard, scanner, coin)
        if not ok:
            print(f"   early_mover: {coin} vetoed by pump guard: {why}")
        return not ok
    return veto


ACTIVE = "breakout10"   # the listing hunter keeps idle cash in whatever this rotation holds


def park_targets():
    """Coins the active rotation holds right now (the listing hunter's idle cash rides them)."""
    try:
        return [c for c in load_pf("crypto", ACTIVE).positions]
    except Exception:
        return []


def park_idle(pf, now, prices, targets):
    """Keep the listing hunter fully invested: parked money follows the active rotation's picks
    (none = rotation is in cash because the market is in a downtrend, so we hold cash too)."""
    for c in [c for c, p in pf.positions.items() if p.get("park") and c not in targets and prices.get(c)]:
        pf.sell(now, c, 1.0, prices[c], "unpark: rotation moved on")
    tg = [c for c in targets if prices.get(c)]
    if not tg:
        return
    eq = pf.equity(prices)
    spare = pf.cash - eq * config.MIN_CASH_RESERVE_PCT
    if spare < 2 * config.MIN_ORDER_USD * len(tg):
        return
    for c in tg:
        pf.buy(now, c, spare / len(tg), prices[c], 0.0, reason="ride the active rotation")
        pf.positions[c]["park"] = True


def unpark(pf, now, need, prices):
    """Sell parked positions pro rata to raise `need` dollars for a new listing."""
    parked = {c: p["qty"] * prices[c] for c, p in pf.positions.items()
              if p.get("park") and prices.get(c) and not is_runner(p, prices[c])}   # never sell a runner
    total = sum(parked.values())
    if need <= 0 or not total:
        return
    frac = min(1.0, need / (total * (1 - pf.fee - pf.slippage)))
    for c in parked:
        pf.sell(now, c, frac if frac < 0.999 else 1.0, prices[c], "unpark for a new listing")


def buy_early(cands, scanner, guard, tag, st=None):
    """Buy candidates [{coin, price, reason, text}] (best first) into the early_mover account.
    The one code path for the minute scanner, the listing reactor and the footprint scanner:
    same Portfolio accounting as the hourly cycle (which then manages the trailing stop / time
    limit like any other position), pump guard on every entry, reason recorded in trades.csv."""
    if not cands:
        return
    st = st or EARLY
    pf = load_pf("crypto", st.name)
    now = int(time.time() * 1000)
    prices = {c: scanner.last[c]["price"] for c in pf.positions if c in scanner.last}
    prices.update({c["coin"]: c["price"] for c in cands})
    eq, n_before = pf.equity(prices), len(pf.trades)
    for c in cands:
        if pf.halted or open_trades(pf) >= st.max_positions:
            break
        coin = c["coin"]
        if coin in pf.positions or pf.cooldown.get(coin, 0) > now:
            continue
        ok, why = (True, "") if st is EARLY else guard_check(guard, scanner, coin)
        if not ok:   # (brand-new listings are exempt: buying the first hours is the tested rule)
            print(f"   {tag}: {coin} vetoed by pump guard: {why}")
            continue
        if st is EARLY:                                # official account: free cash from the BTC park
            unpark(pf, now, eq * st.position_pct - (pf.cash - eq * config.MIN_CASH_RESERVE_PCT),
                   {c: v["price"] for c, v in scanner.last.items() if v.get("price")})
        usd = min(eq * st.position_pct, pf.cash - eq * config.MIN_CASH_RESERVE_PCT)
        if usd < config.MIN_ORDER_USD:
            break
        pf.buy(now, coin, usd, c["price"], c["price"] * (1 - st.trail), reason=c["reason"])
        print(f"   {tag}: BUY {coin} ({c['reason']}): {c['text']}")   # no phone alert: owner wants daily P/L only
    if len(pf.trades) > n_before:
        save_pf("crypto", st.name, pf, n_before, prices)


def scan_movers(client, scanner, guard, footprint=None):
    """Once a minute: one tickers call -> minute scanner -> buy take-offs and new listings
    into the early_mover account (buy_early). The same tickers feed the footprint scanner's
    open-interest history (perp instruments carry `oi`)."""
    tick = client.tickers()
    if not getattr(scanner, "_logged", False):   # once per run: confirm live field names
        scanner._logged = True
        print(f"   scanner: {len(tick)} tickers, sample: {next((t for t in tick if t.get('i') == 'BTC_USD'), tick[:1])}")
    scanner.update(tick)
    if footprint is not None:
        try:
            footprint.note_oi(tick)              # self-limits to one snapshot per 30 min
        except Exception as e:
            print(f"   footprint: oi snapshot failed: {e}")
    sigs = scanner.signals()
    if not sigs:
        return
    for s in sigs[:5]:
        print(f"   scanner: {describe(s)}")
    cand = lambda s: {"coin": s["coin"], "price": s["price"], "reason": f"scanner {s['kind']}", "text": describe(s)}
    if EARLY.P["buy_listings"]:            # official account: brand-new listings
        buy_early([cand(s) for s in sigs if s["kind"] == "new_listing"], scanner, guard, "new listing", EARLY)
    buy_early([cand(s) for s in sigs if s["kind"] == "mover"], scanner, guard, "take-off", MOVER)


def react_listings(client, scanner, reactor, guard):
    """Every ~10 s: poll the announcement sources that are due (short timeouts, per-source
    backoff); on a new listing notice for a coin that trades on Crypto.com, refresh the tickers
    and buy if the not-yet-moved gate passes. Every verdict goes to data/listing_events.csv."""
    events = reactor.poll()
    if not events:
        return
    for ev in events:
        print(f"   listing: {ev['source']} #{ev['id'][:24]} {ev['title'][:90]!r} -> {ev['coins']}")
    if any(c in scanner.last for ev in events for c in ev["coins"]):
        try:
            scanner.update(client.tickers())     # fresh price + 24h change for the gate
        except Exception as e:
            print(f"   listing: ticker refresh failed: {e}")
    buy_early(reactor.candidates(events, scanner), scanner, guard, "listing notice", ANNOUNCE)


def footprint_cycle(scanner, footprint, guard):
    """Once an hour, after the crypto cycle: rank accumulation footprints on the candles it
    just loaded (every USD coin) and buy the top scores into free early_mover slots."""
    cands = footprint.rank(CRYPTO_CANDLES)
    for c in cands:
        print(f"   footprint: {c['text']}")
    buy_early(cands, scanner, guard, "footprint", MOVER)


def _balance(mname, sname):
    d = acct_dir(mname, sname)
    eq, n = config.STARTING_CASH_USD, 0
    if os.path.exists(f"{d}/equity.csv"):
        with open(f"{d}/equity.csv") as f:
            lines = f.read().strip().splitlines()
        if len(lines) > 1:
            eq = float(lines[-1].split(",")[1])
    if os.path.exists(f"{d}/trades.csv"):
        with open(f"{d}/trades.csv") as f:
            n = max(0, len(f.read().strip().splitlines()) - 1)
    return eq, n


def trade_social(client, tracker):
    """After each social poll: buy the hottest Crypto.com coins into the social_heat account
    (one tickers call for price + 24h change; same Portfolio accounting as the hourly cycle,
    which together with fast_check manages the trailing stop / time limit / heat collapse)."""
    st = next((s for s in MARKETS["crypto"]["strategies"] if s.name == "social_heat"), None)
    hot = [h for h in tracker.heat() if h["score"] >= st.P["enter"]] if st else []
    if not hot:
        return
    pf = load_pf("crypto", st.name)
    if pf.halted or len(pf.positions) >= st.max_positions:
        return
    tick = social.parse_tickers(client.tickers())
    now = int(time.time() * 1000)
    prices = {c: float(tick[c]["a"]) for c in pf.positions if tick.get(c, {}).get("a")}
    eq, n_before = pf.equity(prices), len(pf.trades)
    for h in hot:
        coin = h["coin"]
        if len(pf.positions) >= st.max_positions:
            break
        if coin in pf.positions or pf.cooldown.get(coin, 0) > now or coin not in tick:
            continue
        e = st.entry(coin, tick[coin], now)
        if not e:
            continue
        usd = min(eq * st.position_pct, pf.cash - eq * config.MIN_CASH_RESERVE_PCT)
        if usd < config.MIN_ORDER_USD:
            break
        pf.buy(now, coin, usd, e[0], e[0] * (1 - st.trail))
        prices[coin] = e[0]
        print(f"   social heat: BUY {coin}: {e[1]}")   # no phone alert: owner wants daily P/L only
    if len(pf.trades) > n_before:
        save_pf("crypto", st.name, pf, n_before, prices)


def _mains(m):
    """Official account(s) of a market: one strategy name, or several that split the $500."""
    return list(m["main"]) if isinstance(m["main"], (list, tuple)) else [m["main"]]


def _official(mn, m):
    """(balance, trades) of a market's official $500. When several strategies split it, each runs
    its own $500 test account, so the official balance is their average (= equal split)."""
    bals = [_balance(mn, s) for s in _mains(m)]
    return sum(b[0] for b in bals) / len(bals), sum(b[1] for b in bals)


def scoreboard():
    """SCOREBOARD.md: the two official $500 accounts. LAB.md: every test strategy."""
    start = config.STARTING_CASH_USD
    main = [(mn, _mains(m), *_official(mn, m)) for mn, m in MARKETS.items()]
    total = sum(r[2] for r in main)
    out = ["# Scoreboard (pretend money)", ""]
    for mn, _, eq, _ in main:
        out.append(f"**{mn.title()}: ${eq:,.2f}**  ({eq - start:+,.2f})  ")
    out.append(dex.scoreboard_line() + "  ")       # on-chain paper account (dex.py); not part of the total
    out += ["", f"**Total: ${total:,.2f}** of ${start * len(main):,.0f}  ({total - start * len(main):+,.2f})", "",
            f"Updated {ts(int(time.time() * 1000))} UTC"]
    with open("SCOREBOARD.md", "w") as f:
        f.write("\n".join(out) + "\n")

    lab = [(mn, st.name, *_balance(mn, st.name)) for mn, m in MARKETS.items() for st in m["strategies"]]
    lab.append(("dex", dex.DEX["name"], *_balance("dex", dex.DEX["name"])))   # data/dex/dex_hunter
    lab.sort(key=lambda r: -r[2])
    out = ["# Strategy lab (behind the scenes)", "",
           "Every candidate strategy runs its own separate pretend $500 so they can be compared. "
           "The best one in each market trades the official account on SCOREBOARD.md.", "",
           "| Market | Strategy | Balance | Return | Trades |", "|---|---|---|---|---|"]
    for mn, sn, eq, n in lab:
        star = " (official)" if mn in MARKETS and sn in _mains(MARKETS[mn]) else ""
        out.append(f"| {mn} | {sn}{star} | ${eq:,.2f} | {eq / start - 1:+.1%} | {n} |")
    with open("LAB.md", "w") as f:
        f.write("\n".join(out) + "\n")
    write_dashboard(main, total)
    return main


def _live_prices(mn, pfs):
    """One fresh quote call for every coin the account(s) hold ({} if it fails)."""
    held = sorted({c for pf in pfs for c in pf.positions})
    if not held:
        return {}
    try:
        return MARKETS[mn]["client"]().last_prices(held)
    except Exception as e:
        print(f"   dashboard: {mn} prices failed: {e}")
        return {}


def _holdings(pfs, k, px):
    """What the official account holds right now: [{coin, value, pnl}] (the accounts that split
    the $500 are summed then divided by k, like the balance)."""
    agg = {}
    for pf in pfs:
        for coin, p in pf.positions.items():
            a = agg.setdefault(coin, {"qty": 0.0, "cost": 0.0})
            a["qty"] += p["qty"]
            a["cost"] += p["cost"]
    out = []
    for coin, a in agg.items():
        value = a["qty"] * px.get(coin, a["cost"] / a["qty"] if a["qty"] else 0) / k
        out.append({"coin": coin, "value": value, "pnl": value - a["cost"] / k})
    return sorted(out, key=lambda h: -h["value"])


def write_dashboard(rows=None, total=None):
    """docs/index.html: the phone dashboard (dashboard.py). Official accounts + the DEX card.
    Balances are marked at live prices each time (every 5 minutes from the main loop), and the
    live value is added as the newest point of each chart."""
    look = {"crypto": ("₿", "#3b82ff", "#22d3ee"), "stocks": ("📈", "#7c3aed", "#3b82ff")}
    now = int(time.time() * 1000)
    cards = []
    for mn, m in MARKETS.items():
        names = _mains(m)
        k = len(names)                                 # several strategies split the $500 equally
        pfs = [load_pf(mn, s) for s in names]
        px = _live_prices(mn, pfs)
        eq = sum(pf.equity(px) for pf in pfs) / k
        series = dashboard._combine([dashboard._series(f"{acct_dir(mn, s)}/equity.csv") for s in names])
        icon, c1, c2 = look.get(mn, ("•", "#3b82ff", "#22d3ee"))
        cards.append({"holdings": _holdings(pfs, k, px), "name": mn.title(), "icon": icon, "c1": c1, "c2": c2,
                      "official": True, "equity": eq, "series": [(t, v / k) for t, v in series] + [(now, eq)],
                      "positions": len({c for pf in pfs for c in pf.positions})})
    try:                                               # DEX paper account: not part of the total
        st = dex.scoreboard_stats()
        d = f'{dex.DEX["dir"]}/{dex.DEX["name"]}'
        paused = st.get("paused")
        scams, lost = st.get("scammed", 0), st.get("lost", 0.0)
        try:
            with open(f"{d}/portfolio.json") as f:
                dpf = json.load(f)
        except (OSError, ValueError):
            dpf = {}
        dpos, dhold = dpf.get("positions", {}), []
        for p in dpos.values():                        # px = last price the DEX hunter saw (it polls itself)
            value = p["qty"] * (p.get("px") if p.get("px") is not None else p["entry"])
            dhold.append({"coin": p.get("sym", "?"), "value": value, "pnl": value - p["cost"]})
        deq = dpf["cash"] + sum(h["value"] for h in dhold) if "cash" in dpf else st["equity"]
        cards.append({"holdings": sorted(dhold, key=lambda h: -h["value"]), "name": "DEX", "icon": "◆",
                      "c1": "#22e39a", "c2": "#3b82ff", "official": False, "equity": deq,
                      "series": dashboard._series(f"{d}/equity.csv") + [(now, deq)], "positions": len(dpos),
                      "extra": "Paused: scam limit" if paused else (f"Scammed {scams} · −${abs(lost):,.2f}" if scams else "Scammed 0"),
                      "extra_cls": "bad" if (paused or scams) else "ok"})
    except Exception as e:
        print(f"   dashboard: dex card failed: {e}")
    dashboard.write(cards)


def dashboard_sync():
    """Every 5 minutes: redraw the dashboard at live prices and push just docs/ (the hourly
    git_sync still commits everything)."""
    try:
        write_dashboard()
    except Exception as e:
        print(f"   dashboard refresh failed: {e}")
        return
    if os.environ.get("GIT_AUTOPUSH") != "1":
        return
    push_docs()


def push_docs(remote="origin", branch="main"):
    """Publish docs/index.html as its own commit on top of the remote branch, built with a
    throwaway index: the working tree, the local branch and the engine's data files are never
    touched (a pull here would trip over the uncommitted data files). A lost race is skipped;
    the next refresh 5 minutes later tries again, and the hourly git_sync commits everything."""
    env = dict(os.environ, GIT_INDEX_FILE=os.path.abspath(".git/dash_index"))

    def git(*args):
        return subprocess.run(["git", *args], env=env, capture_output=True, text=True, check=True).stdout.strip()
    try:
        git("fetch", "-q", remote, branch)
        base = git("rev-parse", "FETCH_HEAD")
        git("read-tree", base)
        blob = git("hash-object", "-w", "docs/index.html")
        git("update-index", "--add", "--cacheinfo", f"100644,{blob},docs/index.html")
        tree = git("write-tree")
        if tree == git("rev-parse", f"{base}^{{tree}}"):
            return                                     # unchanged
        commit = git("commit-tree", tree, "-p", base, "-m", "dashboard refresh")
        git("push", "-q", remote, f"{commit}:refs/heads/{branch}")
    except subprocess.CalledProcessError as e:
        print(f"   dashboard push skipped: {(e.stderr or '').strip()[:200]}")


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
        key = mn.title()
        now_bal[key] = eq
        day = eq - prev.get("balances", {}).get(key, start)
        lines.append(f"{key}: ${eq:,.2f}  today {day:+,.2f}  total {eq - start:+,.2f}")
    total = sum(now_bal.values())
    day_total = total - sum(prev.get("balances", {}).get(k, start) for k in now_bal)
    lines.append(dex.scoreboard_line(md=False))    # DEX paper account: shown, not in the total
    notify(f"Today {day_total:+,.2f} | Total {total - start * len(now_bal):+,.2f}", "\n".join(lines))
    with open(stamp, "w") as f:
        json.dump({"date": today, "balances": now_bal}, f)


def git_sync():
    """In the cloud runner: commit the paper accounts back to GitHub every hour."""
    if os.environ.get("GIT_AUTOPUSH") != "1":
        return
    # `git add data` already covers data/social and data/dex; naming a subdirectory that does
    # not exist yet makes the whole add fail (pathspec error) and nothing gets committed
    cmds = ["git add data SCOREBOARD.md LAB.md docs",
            f"git commit -qm 'paper-trade {ts(int(time.time() * 1000))} UTC'",
            "git pull -q --rebase -X theirs", "git push -q"]
    for c in cmds:
        if subprocess.run(c, shell=True).returncode:
            if c.startswith("git commit"):
                return   # nothing changed
            if c.startswith("git pull"):   # never leave a rebase in progress: it would block every later sync
                subprocess.run("git rebase --abort", shell=True, stderr=subprocess.DEVNULL)
                return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0, help="minutes to stay on (0 = one cycle)")
    a = ap.parse_args()
    clients = {m: MARKETS[m]["client"]() for m in MARKETS}
    tracker = social.tracker()                  # social heat: CoinGecko / Reddit / DEX collectors
    try:
        tracker.universe |= set(clients["crypto"].list_spot_symbols())
        tracker.self_check()                    # logs each source's HTTP status once per run
    except Exception as e:
        print(f"social self-check failed: {e}")
    hunter = dex.hunter()                       # DEX paper trader (dex.py): one request per tick at most
    try:
        hunter.self_check()                     # HTTP status per source once per run
    except Exception as e:
        print(f"dex self-check failed: {e}")
    end = time.time() + a.watch * 60
    fast_every = {"crypto": 1, "stocks": 15}   # seconds between live stop/target checks
    last_fast = {m: 0.0 for m in clients}
    last_hour = None
    scanner, last_scan = MinuteScanner(), 0.0   # minute-level early mover scanner (crypto)
    guard, reactor, footprint = PumpGuard(), ListingNoticeReactor(), PrePumpFootprint()   # signals.py
    MOVER.veto = early_veto(guard, scanner)     # hourly take-off buys go through the pump guard too
    last_listing = 0.0
    last_dash = time.time()                     # first refresh 5 min in (the hourly cycle draws it at start)
    while True:
        hour = time.strftime("%Y%m%d%H", time.gmtime())
        if hour != last_hour and time.gmtime().tm_min >= 1:   # new hourly candle has closed
            for m, c in clients.items():
                try:
                    full_cycle(m, c)
                except Exception as e:
                    print(f"{m} cycle failed: {e}")
            tracker.universe |= set(CRYPTO_CANDLES)
            print(f"   {tracker.top_line()}")     # hourly: top-5 social heat in run.log
            daily_summary(scoreboard())
            git_sync()
            last_hour = hour
            scanner.warm_start(CRYPTO_CANDLES)   # hourly closes + 7-day volume baseline
            try:
                footprint_cycle(scanner, footprint, guard)
            except Exception as e:
                print(f"footprint scan failed: {e}")
        if time.time() - last_dash >= 300:      # dashboard at live prices every 5 minutes
            last_dash = time.time()
            dashboard_sync()
        if time.time() - last_scan >= 60:
            last_scan = time.time()
            try:
                scan_movers(clients["crypto"], scanner, guard, footprint)
            except Exception as e:
                print(f"crypto scanner failed: {e}")
            hunter.cex = set(scanner.last)      # Crypto.com-listed symbols qualify for the DEX "blue" tier
        if time.time() - last_listing >= reactor.p["loop_s"]:
            last_listing = time.time()
            try:
                react_listings(clients["crypto"], scanner, reactor, guard)
            except Exception as e:
                print(f"listing reactor failed: {e}")
        for m, c in clients.items():
            if time.time() - last_fast[m] >= fast_every[m]:
                last_fast[m] = time.time()
                try:
                    fast_check(m, c)
                except Exception as e:
                    print(f"{m} fast check failed: {e}")
        try:                                     # social: at most one source per tick (<= 2 calls, 8s timeout)
            if tracker.poll():
                trade_social(clients["crypto"], tracker)
        except Exception as e:
            print(f"social heat failed: {e}")
        try:                                     # DEX: bookkeeping + at most one HTTP request (<= 8s) per tick
            hunter.tick()
        except Exception as e:
            print(f"dex hunter failed: {e}")
        if time.time() >= end or not a.watch:
            break
        time.sleep(1 - time.time() % 1)

if __name__ == "__main__":
    main()
