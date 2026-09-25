"""Day-trading tournament: fast setups (hold minutes-to-hours) on hourly bars.
Tune on the first 60% of history, judge on the last 40% it never saw, after fees.

Setups (long-only, spot / cash account):
  hbreak  - crypto: buy a close above the N-hour high; exit below the M-hour low,
            at a k*ATR stop, or after H hours.
  noise   - intraday momentum (Zarattini/Aziz/Barbon 2024, adapted to hourly bars):
            buy when price leaves the day's "noise area" (open +/- average move from
            the open at that time of day over the last D days); exit when it falls back
            inside, or at the end of the day. Stocks and crypto (crypto day = UTC day).
  orb     - stocks: opening-range breakout on the first hourly bar; exit at the
            first bar's low or at the close.

    python daytrade.py --market crypto
    python daytrade.py --market stocks
    python daytrade.py --synthetic
"""
import argparse
import itertools
import math
from datetime import datetime, timezone

import config

SPLIT = 0.6
HOUR = 3_600_000


# ---------------------------------------------------------------- data
def load_crypto(symbols, days):
    from data_source import CryptoComClient
    c, out = CryptoComClient(), {}
    for s in symbols:
        try:
            out[s] = c.candles(s, timeframe="1h", count=days * 24)
            print(f"  {s}: {len(out[s])} bars")
        except Exception as e:
            print(f"  skip {s}: {e}")
    return out


def load_stocks(symbols, days):
    from data_source import YahooClient
    c = YahooClient()
    return {s: c.candles(s, count=days * 7, universe=symbols) for s in symbols}


def load_synthetic(symbols, days):
    from data_source import SyntheticClient
    c = SyntheticClient(n=days * 24)
    return {s: c.candles(s, count=days * 24) for s in symbols}


def day_key(t, market):
    d = datetime.fromtimestamp(t / 1000, timezone.utc)
    return d.strftime("%Y-%m-%d")   # UTC day; for US stocks the regular session sits inside one UTC day


# ---------------------------------------------------------------- helpers
def atr_list(c, n=14):
    out, prev = [], None
    for i, x in enumerate(c):
        tr = x["h"] - x["l"] if i == 0 else max(x["h"] - x["l"], abs(x["h"] - c[i - 1]["c"]),
                                                 abs(x["l"] - c[i - 1]["c"]))
        prev = tr if prev is None else (prev * (n - 1) + tr) / n
        out.append(prev)
    return out


def sessions(c, market):
    """Group bar indexes by trading day."""
    days, cur, key = [], [], None
    for i, x in enumerate(c):
        k = day_key(x["t"], market)
        if k != key and cur:
            days.append(cur)
            cur = []
        key = k
        cur.append(i)
    if cur:
        days.append(cur)
    return days


# ---------------------------------------------------------------- setups
_CACHE = {}


def rolling(c, n, key, fn):
    """fn over the previous n bars (excluding the current one), cached per series."""
    k = (id(c), n, key)
    if k not in _CACHE:
        from collections import deque
        out, dq = [None] * len(c), deque()
        vals = [x[key] for x in c]
        better = (lambda a, b: a >= b) if fn is max else (lambda a, b: a <= b)
        for i in range(len(c)):
            while dq and dq[0] < i - n:
                dq.popleft()
            if i >= n:
                out[i] = vals[dq[0]]
            while dq and better(vals[i], vals[dq[-1]]):
                dq.pop()
            dq.append(i)
        _CACHE[k] = out
    return _CACHE[k]


def run_hbreak(c, p, cost, lo, hi):
    """Returns list of per-trade net returns."""
    N, M, K, H = p["n"], p["m"], p["k"], p["h"]
    if (id(c), "atr") not in _CACHE:
        _CACHE[(id(c), "atr")] = atr_list(c)
    a = _CACHE[(id(c), "atr")]
    hi_n, lo_m = rolling(c, N, "h", max), rolling(c, M, "l", min)
    trades, pos = [], None
    for i in range(max(lo, N + 1, M + 1), hi):
        x = c[i]
        if pos is None:
            if x["c"] > hi_n[i]:
                pos = {"entry": x["c"], "stop": x["c"] - K * a[i], "i": i}
        else:
            exit_px = None
            if x["l"] <= pos["stop"]:
                exit_px = min(pos["stop"], x["o"])
            elif x["c"] < lo_m[i]:
                exit_px = x["c"]
            elif H and i - pos["i"] >= H:
                exit_px = x["c"]
            if exit_px is not None:
                trades.append(exit_px / pos["entry"] * (1 - cost) / (1 + cost) - 1)
                pos = None
    return trades


def _noise_tables(c, market, D):
    k = (id(c), "noise", D)
    if k not in _CACHE:
        days = sessions(c, market)
        moves = [[abs(c[i]["c"] / c[idx[0]]["o"] - 1) for i in idx] for idx in days]
        avg = []
        for di in range(len(days)):
            prev = moves[max(0, di - D):di]
            row = []
            for j in range(len(days[di])):
                vals = [m[j] for m in prev if len(m) > j]
                row.append(sum(vals) / len(vals) if len(vals) >= max(1, D // 2) else None)
            avg.append(row)
        _CACHE[k] = (days, avg)
    return _CACHE[k]


def run_noise(c, p, cost, lo, hi, market):
    """Intraday noise-area breakout, one trade per day, flat at end of day."""
    days, avg = _noise_tables(c, market, p["d"])
    mult, trades = p["mult"], []
    for di, idx in enumerate(days):
        if idx[0] < lo or idx[-1] >= hi:
            continue
        o = c[idx[0]]["o"]
        row = avg[di]
        for j in range(1, len(idx) - 1):          # never enter on the first or last bar
            if row[j] is None or c[idx[j]]["c"] <= o * (1 + mult * row[j]):
                continue
            entry, exit_px = c[idx[j]]["c"], c[idx[-1]]["c"]
            for k in range(j + 1, len(idx) - 1):
                if row[k] is not None and c[idx[k]]["c"] < o * (1 + mult * row[k]):
                    exit_px = c[idx[k]]["c"]
                    break
            trades.append(exit_px / entry * (1 - cost) / (1 + cost) - 1)
            break
    return trades


def run_orb(c, p, cost, lo, hi, market):
    """First-bar opening range breakout, flat at the close. Stop = first bar's low."""
    if (id(c), "sess") not in _CACHE:
        _CACHE[(id(c), "sess")] = sessions(c, market)
    days, trades = _CACHE[(id(c), "sess")], []
    for idx in days:
        if idx[0] < lo or idx[-1] >= hi or len(idx) < 4:
            continue
        first = c[idx[0]]
        rng = first["h"] - first["l"]
        if p["dir_filter"] and first["c"] <= first["o"]:
            continue                                # only trade days that opened strong
        for i in idx[1:-1]:
            if c[i]["h"] > first["h"]:
                entry = max(first["h"], c[i]["o"])
                stop = entry - p["stop_r"] * rng
                exit_px = c[idx[-1]]["c"]
                for k in range(i, idx[-1] + 1):
                    if c[k]["l"] <= stop:
                        exit_px = min(stop, c[k]["o"])
                        break
                trades.append(exit_px / entry * (1 - cost) / (1 + cost) - 1)
                break
    return trades


GRIDS = {
    "crypto": {
        "hbreak": {"n": [12, 24, 48, 72], "m": [6, 12, 24], "k": [1.5, 2.5, 4.0], "h": [12, 24, 72, 0]},
        "noise": {"d": [7, 14, 30], "mult": [1.0, 1.5, 2.0]},
    },
    "stocks": {
        "noise": {"d": [7, 14, 30], "mult": [0.8, 1.0, 1.5]},
        "orb": {"stop_r": [0.5, 1.0], "dir_filter": [0, 1]},
    },
}


# ---------------------------------------------------------------- scoring
def portfolio_stats(per_asset_trades, months, slots):
    """Equal capital slots per asset; each trade's return applies to its slot."""
    all_t = [t for ts_ in per_asset_trades.values() for t in ts_]
    if not all_t or months <= 0:
        return None
    # growth per slot, then average across slots
    growths = []
    for ts_ in per_asset_trades.values():
        g = 1.0
        for t in ts_:
            g *= 1 + t
        growths.append(g)
    growths += [1.0] * max(0, slots - len(growths))
    total = sum(growths) / len(growths) - 1
    wins = sum(1 for t in all_t if t > 0)
    mean = sum(all_t) / len(all_t)
    return {"total": total, "monthly": (1 + total) ** (1 / months) - 1 if total > -1 else -1,
            "trades_mo": len(all_t) / months, "win": wins / len(all_t), "avg": mean}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["crypto", "stocks"], default="crypto")
    ap.add_argument("--days", type=int, default=720)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    if a.market == "crypto":
        syms, cost, load = config.UNIVERSE, config.FEE_RATE + config.SLIPPAGE_RATE, load_crypto
    else:
        syms, cost, load = config.STOCK_UNIVERSE, config.STOCK_FEE_RATE + config.STOCK_SLIPPAGE_RATE, load_stocks
    if a.synthetic:
        load = load_synthetic
        print("*** SYNTHETIC DATA: tests the code only ***")
    data = {s: c for s, c in load(syms, a.days).items() if len(c) > 500}
    print(f"\n{a.market}: {len(data)} symbols; cost per side {cost:.2%}")
    t_all = sorted({x["t"] for c in data.values() for x in c})
    t_split = t_all[int(len(t_all) * SPLIT)]
    months_is = (t_split - t_all[0]) / (30 * 86_400_000)
    months_oos = (t_all[-1] - t_split) / (30 * 86_400_000)
    print(f"in-sample {months_is:.1f} months, out-of-sample {months_oos:.1f} months\n")

    splits = {s: next((i for i, x in enumerate(c) if x["t"] >= t_split), len(c)) for s, c in data.items()}
    rows = []
    for setup, grid in GRIDS[a.market].items():
        for combo in itertools.product(*grid.values()):
            p = dict(zip(grid, combo))
            res = {}
            for half in ("is", "oos"):
                per = {}
                for s, c in data.items():
                    split_i = splits[s]
                    lo, hi = (0, split_i) if half == "is" else (split_i, len(c))
                    if setup == "hbreak":
                        per[s] = run_hbreak(c, p, cost, lo, hi)
                    elif setup == "noise":
                        per[s] = run_noise(c, p, cost, lo, hi, a.market)
                    else:
                        per[s] = run_orb(c, p, cost, lo, hi, a.market)
                res[half] = portfolio_stats(per, months_is if half == "is" else months_oos, len(data))
            if res["is"] and res["oos"]:
                rows.append((setup, p, res["is"], res["oos"]))
    rows.sort(key=lambda r: r[2]["monthly"], reverse=True)
    print(f"{len(rows)} variants. Top 15 by in-sample monthly return, then UNSEEN results:\n")
    print(f"{'setup':>7} {'params':<34} | {'IS/mo':>7} | {'OOS/mo':>7} {'OOS tot':>8} {'trades/mo':>9} {'win':>5} {'avg/trade':>9}")
    for setup, p, i, o in rows[:15]:
        ps = " ".join(f"{k}={v}" for k, v in p.items())
        print(f"{setup:>7} {ps:<34} | {i['monthly']:>+7.1%} | {o['monthly']:>+7.1%} {o['total']:>+8.1%} "
              f"{o['trades_mo']:>9.1f} {o['win']:>5.0%} {o['avg']:>+9.2%}")
    best_oos = sorted(rows, key=lambda r: r[3]["monthly"], reverse=True)[:5]
    print("\nFor reference, best 5 by UNSEEN result (picked with hindsight, so optimistic):")
    for setup, p, i, o in best_oos:
        ps = " ".join(f"{k}={v}" for k, v in p.items())
        print(f"{setup:>7} {ps:<34} | IS {i['monthly']:>+6.1%}/mo | OOS {o['monthly']:>+6.1%}/mo, {o['trades_mo']:.0f} trades/mo")


if __name__ == "__main__":
    main()
