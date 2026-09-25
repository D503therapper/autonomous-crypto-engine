"""Replay history candle-by-candle through the exact live engine.

    python backtest.py              # real Crypto.com data (needs network access)
    python backtest.py --synthetic  # fake data, only to prove the code works
    python backtest.py --days 180
"""
import argparse
import math

import config
from data_source import CryptoComClient, SyntheticClient
from engine import Portfolio, step, ts


def run(client, days):
    hours = days * 24 + config.EMA_TREND + 10
    data = {}
    for coin in config.UNIVERSE:
        try:
            cs = client.candles(coin, count=hours)
            if len(cs) > config.EMA_TREND + 50:
                data[coin] = cs
        except Exception as e:
            print(f"  skip {coin}: {e}")
    if not data:
        raise SystemExit("No data loaded.")
    times = sorted({c["t"] for cs in data.values() for c in cs})
    idx = {coin: {c["t"]: i for i, c in enumerate(cs)} for coin, cs in data.items()}
    pf = Portfolio()
    curve, window = [], config.EMA_TREND + 30
    for t in times[config.EMA_TREND + 5:]:
        view = {}
        for coin, cs in data.items():
            i = idx[coin].get(t)
            if i is not None and i >= config.EMA_TREND + 5:
                view[coin] = cs[max(0, i - window):i + 1]
        step(pf, view)
        prices = {c: v[-1]["c"] for c, v in view.items()}
        curve.append((t, pf.equity(prices)))
    return pf, curve, data


def report(pf, curve, data):
    start, end = curve[0][1], curve[-1][1]
    peak, mdd = start, 0.0
    rets = []
    for i, (_, e) in enumerate(curve):
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
        if i:
            rets.append(e / curve[i - 1][1] - 1)
    mean = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / len(rets)) or 1e-12
    sharpe = mean / sd * math.sqrt(24 * 365)
    sells = [t for t in pf.trades if t["side"] == "SELL"]
    wins = [t for t in sells if t["pnl"] > 0]
    fees = sum(t["fee"] for t in pf.trades)
    t0, t1 = curve[0][0], curve[-1][0]

    def hold(coin):
        cs = [c for c in data[coin] if t0 <= c["t"] <= t1]
        return cs[-1]["c"] / cs[0]["c"] - 1 if cs else float("nan")

    ew = [hold(c) for c in data]
    print(f"\n=== Backtest {ts(t0)} -> {ts(t1)} UTC ({len(data)} coins) ===")
    print(f"Start equity        ${start:,.2f}")
    print(f"End equity          ${end:,.2f}  ({end / start - 1:+.1%})")
    print(f"Max drawdown        {mdd:.1%}")
    print(f"Sharpe (annualized) {sharpe:.2f}")
    print(f"Trades              {len(pf.trades)} fills, {len(sells)} exits, "
          f"win rate {len(wins) / max(1, len(sells)):.0%}")
    print(f"Fees + spread paid  ${fees:,.2f}")
    if "BTC" in data:
        print(f"Benchmark: hold BTC {hold('BTC'):+.1%}")
    print(f"Benchmark: equal-weight hold all {sum(ew) / len(ew):+.1%}")
    print("\nLast 10 fills:")
    for t in pf.trades[-10:]:
        pnl = "" if t["pnl"] is None else f" pnl ${t['pnl']:+.2f}"
        print(f"  {t['time']} {t['side']:4} {t['coin']:5} ${t['usd']:>8.2f} @ {t['price']:<12g}{pnl}  ({t['reason']})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--days", type=int, default=120)
    a = ap.parse_args()
    client = SyntheticClient(n=a.days * 24 + 400) if a.synthetic else CryptoComClient()
    if a.synthetic:
        print("*** SYNTHETIC DATA: tests the code only, NOT the strategy ***")
    report(*run(client, a.days))
