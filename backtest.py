"""Replay history candle-by-candle through the exact live engine.

    python backtest.py --market crypto --days 180          # real data (needs network)
    python backtest.py --market stocks --days 365
    python backtest.py --market all --strategy momentum
    python backtest.py --synthetic                          # fake data: tests the code only
"""
import argparse
import math

import config

from data_source import SyntheticClient
from engine import Portfolio, step, ts
from markets import MARKETS


def load(client, symbols, bars):
    data = {}
    for s in symbols:
        try:
            cs = client.candles(s, count=bars)
            if len(cs) > 50:
                data[s] = cs
        except Exception as e:
            print(f"  skip {s}: {e}")
    return data


def run(data, strat, mkt):
    bench = mkt["benchmark"]
    bpd = mkt["bars_per_day"]
    times = sorted({c["t"] for cs in data.values() for c in cs})
    idx = {s: {c["t"]: i for i, c in enumerate(cs)} for s, cs in data.items()}
    # Precompute the benchmark regime (close above its long average) per timestamp.
    n = config.REGIME_DAYS * bpd
    regime, run_sum = {}, 0.0
    bc = data.get(bench, [])
    for i, c in enumerate(bc):
        run_sum += c["c"] - (bc[i - n]["c"] if i >= n else 0)
        regime[c["t"]] = True if i + 1 < n else c["c"] > run_sum / n
    pf = Portfolio(fee=mkt["fee"], slippage=mkt["slippage"])
    curve, start = [], strat.min_candles
    for t in times[start:]:
        view = {}
        for s in strat.universe:
            i = idx.get(s, {}).get(t)
            if i is not None and i >= strat.min_candles:
                view[s] = data[s][max(0, i - strat.window):i + 1]
        step(pf, view, strat, regime.get(t, True))
        prices = {s: v[-1]["c"] for s, v in view.items()}
        curve.append((t, pf.equity(prices)))
    return pf, curve


def report(pf, curve, data, name, bench, bars_per_year):
    if not curve:
        print(f"\n=== [{name}] not enough data ===")
        return
    start, end = curve[0][1], curve[-1][1]
    peak, mdd, rets = start, 0.0, []
    for i, (_, e) in enumerate(curve):
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
        if i:
            rets.append(e / curve[i - 1][1] - 1)
    mean = sum(rets) / max(1, len(rets))
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / max(1, len(rets))) or 1e-12
    sharpe = mean / sd * math.sqrt(bars_per_year)
    sells = [t for t in pf.trades if t["side"] == "SELL"]
    wins = [t for t in sells if t["pnl"] > 0]
    fees = sum(t["fee"] for t in pf.trades)
    t0, t1 = curve[0][0], curve[-1][0]
    days = (t1 - t0) / 86_400_000
    monthly = (end / start) ** (30 / max(days, 1)) - 1

    def hold(s):
        cs = [c for c in data.get(s, []) if t0 <= c["t"] <= t1]
        return cs[-1]["c"] / cs[0]["c"] - 1 if cs else float("nan")

    print(f"\n=== [{name}] {ts(t0)} -> {ts(t1)} UTC ({days:.0f} days) ===")
    print(f"Start -> end        ${start:,.2f} -> ${end:,.2f}  ({end / start - 1:+.1%})")
    print(f"Avg per month       {monthly:+.1%}")
    print(f"Max drawdown        {mdd:.1%}")
    print(f"Sharpe (annualized) {sharpe:.2f}")
    print(f"Trades              {len(pf.trades)} fills, {len(sells)} exits, "
          f"win rate {len(wins) / max(1, len(sells)):.0%}")
    print(f"Fees + slippage     ${fees:,.2f}")
    print(f"Benchmark: hold {bench:5} {hold(bench):+.1%}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--market", choices=[*MARKETS, "all"], default="all")
    ap.add_argument("--strategy", default="all")
    a = ap.parse_args()
    if a.synthetic:
        print("*** SYNTHETIC DATA: tests the code only, NOT the strategy ***")
    for mname in (MARKETS if a.market == "all" else [a.market]):
        mkt = MARKETS[mname]
        client = SyntheticClient(n=a.days * 24 + 800) if a.synthetic else mkt["client"]()
        strats = [s for s in mkt["strategies"] if a.strategy in ("all", s.name)]
        warmup = max(s.min_candles for s in strats) + 10
        bpd = mkt["bars_per_day"]
        symbols = sorted({x for s in strats for x in s.universe} | {mkt["benchmark"]})
        print(f"\nLoading {len(symbols)} {mname} symbols...")
        data = load(client, symbols, a.days * bpd + warmup + 50 * bpd)
        for s in strats:
            pf, curve = run(data, s, mkt)
            report(pf, curve, data, f"{mname}/{s.name}", mkt["benchmark"], bpd * 365 if mname == "crypto" else bpd * 252)
