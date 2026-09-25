"""Strategy tournament: test hundreds of momentum/trend variants on years of daily
prices, pick winners on the first part of history (in-sample), then judge them
ONLY on the later part they never saw (out-of-sample). Winners must beat simply
holding the benchmark out-of-sample, after fees.

    python tournament.py --market crypto
    python tournament.py --market stocks
    python tournament.py --synthetic        # code check only
"""
import argparse
import itertools
import math
import time

import config

SPLIT = 0.6   # first 60% of days = in-sample (tuning), last 40% = out-of-sample (the real test)

GRID = {
    "signal": ["tsmom", "donchian"],            # tsmom: own N-day return > 0; donchian: buy N-day high, exit N/2-day low
    "lookback": [7, 10, 14, 21, 30, 45, 60, 90],  # days of history used for the signal
    "rebalance": [1, 3, 7],                     # days between portfolio updates
    "top_n": [2, 3, 5, 99],                     # hold the N strongest (99 = all with positive momentum)
    "regime": [0, 50, 100, 200],                # benchmark must be above its N-day average (0 = off)
    "weighting": ["equal", "inv_vol"],
}


# ---------------------------------------------------------------- data
def daily_crypto(symbols, days):
    from data_source import CryptoComClient
    c, out = CryptoComClient(), {}
    for s in symbols:
        try:
            cs = c.candles(s, timeframe="1D", count=days)
            out[s] = {x["t"] // 86_400_000: x["c"] for x in cs}
        except Exception as e:
            print(f"  skip {s}: {e}")
        time.sleep(0.1)
    return out


def daily_stocks(symbols, days):
    import yfinance as yf
    df = yf.download(sorted(symbols), period=f"{days}d", interval="1d", auto_adjust=True,
                     progress=False, group_by="ticker")
    out = {}
    for s in symbols:
        try:
            d = df[s]["Close"].dropna()
            out[s] = {int(ix.timestamp()) // 86_400: float(v) for ix, v in d.items()}
        except KeyError:
            pass
    return out


def synthetic(symbols, days):
    import random
    rng, out = random.Random(3), {}
    for s in symbols:
        p, drift = 100.0, 0.0
        out[s] = {}
        for d in range(days):
            if d % 90 == 0:
                drift = rng.gauss(0, 0.004)
            p *= math.exp(drift + rng.gauss(0, 0.035))
            out[s][d] = p
    return out


def align(prices):
    """Common calendar; forward-fill gaps; an asset only trades once it has history."""
    days = sorted({d for s in prices.values() for d in s})
    table = {}
    for s, ser in prices.items():
        last, col = None, []
        for d in days:
            last = ser.get(d, last)
            col.append(last)
        table[s] = col
    return days, table


# ---------------------------------------------------------------- simulation
def simulate(days, table, bench, p, cost, start, end):
    """Daily portfolio: at each rebalance close, set target weights; pay cost on turnover."""
    syms = list(table)
    L, R, N, M = p["lookback"], p["rebalance"], p["top_n"], p["regime"]
    held = set()                 # donchian mode: positions persist until an exit signal
    b = table[bench]
    w = {}                       # current weights (drift with prices between rebalances)
    eq, curve, turnover_total = 1.0, [1.0], 0.0
    for i in range(max(start, L + 1, M + 1, 21), end - 1):
        if (i - start) % R == 0:
            target = {}
            risk_on = M == 0 or (b[i] is not None and all(b[j] is not None for j in (i - M, i)) and
                                 b[i] > sum(b[i - M + 1:i + 1]) / M)
            if not risk_on:
                held.clear()
            if risk_on:
                cands = []
                for s in syms:
                    col = table[s]
                    if col[i] is None or col[i - L] is None or col[i - 20] is None:
                        continue
                    mom = col[i] / col[i - L] - 1
                    if p["signal"] == "tsmom":
                        if mom <= 0:
                            continue
                    else:
                        if s in held and col[i] < min(col[i - max(2, L // 2):i]):
                            held.discard(s)
                        elif s not in held and col[i] >= max(col[i - L:i]):
                            held.add(s)
                        if s not in held:
                            continue
                    rets = [col[j] / col[j - 1] - 1 for j in range(i - 19, i + 1)]
                    vol = math.sqrt(sum(r * r for r in rets) / 20) or 1e-9
                    cands.append((mom / vol, s, vol))
                cands.sort(reverse=True)
                pick = cands[:N]
                if p["signal"] == "donchian":
                    held &= {x for _, x, _ in pick}
                if pick:
                    if p["weighting"] == "equal":
                        target = {s: 1 / len(pick) for _, s, _ in pick}
                    else:
                        inv = {s: 1 / v for _, s, v in pick}
                        tot = sum(inv.values())
                        target = {s: x / tot for s, x in inv.items()}
                    target = {s: x * (1 - config.MIN_CASH_RESERVE_PCT) for s, x in target.items()}
            turn = sum(abs(target.get(s, 0) - w.get(s, 0)) for s in set(target) | set(w))
            eq *= 1 - turn * cost
            turnover_total += turn
            w = target
        # hold to next close
        growth = 1 - sum(w.values())
        new_w = {}
        for s, x in w.items():
            r = table[s][i + 1] / table[s][i]
            growth += x * r
            new_w[s] = x * r
        eq *= growth
        w = {s: x / growth for s, x in new_w.items()} if growth > 0 else {}
        curve.append(eq)
    return stats(curve, turnover_total)


def stats(curve, turnover):
    n = len(curve) - 1
    if n < 20:
        return None
    rets = [curve[i] / curve[i - 1] - 1 for i in range(1, len(curve))]
    mean = sum(rets) / n
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / n) or 1e-12
    peak, mdd = curve[0], 0.0
    for e in curve:
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
    return {"total": curve[-1] - 1, "monthly": curve[-1] ** (30 / n) - 1,
            "sharpe": mean / sd * math.sqrt(365), "mdd": mdd, "turnover_yr": turnover / n * 365}


def hold(table, s, start, end):
    col = [x for x in table[s][start:end] if x is not None]
    return col[-1] / col[0] - 1 if len(col) > 1 else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["crypto", "stocks"], default="crypto")
    ap.add_argument("--days", type=int, default=1500)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    if a.market == "crypto":
        syms, bench, cost = config.UNIVERSE, "BTC", config.FEE_RATE + config.SLIPPAGE_RATE
        load = daily_crypto
    else:
        syms, bench, cost = config.STOCK_UNIVERSE, "SPY", config.STOCK_FEE_RATE + config.STOCK_SLIPPAGE_RATE
        load = daily_stocks
    if a.synthetic:
        load = synthetic
        print("*** SYNTHETIC DATA: tests the code only ***")
    prices = load(sorted(set(syms) | {bench}), a.days)
    days, table = align(prices)
    n = len(days)
    split = int(n * SPLIT)
    print(f"{a.market}: {len(table)} assets, {n} days; in-sample days 0-{split}, out-of-sample {split}-{n}")
    print(f"cost per unit traded: {cost:.2%}   (survivorship caveat: universe = coins/stocks listed today)")

    keys = list(GRID)
    results = []
    for combo in itertools.product(*GRID.values()):
        p = dict(zip(keys, combo))
        ins = simulate(days, table, bench, p, cost, 0, split)
        if ins:
            results.append((p, ins))
    results.sort(key=lambda r: r[1]["sharpe"], reverse=True)

    b_is, b_oos = hold(table, bench, 0, split), hold(table, bench, split, n)
    print(f"\nBenchmark hold {bench}: in-sample {b_is:+.1%}, out-of-sample {b_oos:+.1%}")
    print(f"{len(results)} variants tested. Top 15 by in-sample Sharpe, then their UNSEEN results:\n")
    hdr = f"{'signal':>8} {'lookback':>8} {'rebal':>5} {'top':>4} {'regime':>6} {'weights':>8} | {'IS ret':>8} {'IS shp':>6} | " \
          f"{'OOS ret':>8} {'OOS/mo':>7} {'OOS shp':>7} {'OOS DD':>7} {'turn/yr':>7}"
    print(hdr)
    print("-" * len(hdr))
    winners = []
    for p, ins in results[:15]:
        oos = simulate(days, table, bench, p, cost, split, n)
        if not oos:
            continue
        beat = oos["total"] > b_oos
        winners.append((p, oos, beat))
        print(f"{p['signal']:>8} {p['lookback']:>8} {p['rebalance']:>5} {p['top_n']:>4} {p['regime']:>6} {p['weighting']:>8} | "
              f"{ins['total']:>+8.1%} {ins['sharpe']:>6.2f} | {oos['total']:>+8.1%} {oos['monthly']:>+7.1%} "
              f"{oos['sharpe']:>7.2f} {oos['mdd']:>7.1%} {oos['turnover_yr']:>7.1f}{'  <- beats hold' if beat else ''}")
    n_beat = sum(1 for *_, b in winners if b)
    print(f"\n{n_beat} of the top {len(winners)} in-sample variants also beat holding {bench} on unseen data.")


if __name__ == "__main__":
    main()
