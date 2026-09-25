"""Early-mover hunter backtest across EVERY USD coin on Crypto.com (hourly bars).

Two setups, tested on history (tune on the first 60%, judge on the last 40%):
  mover   - buy a coin whose price rose >= X% over the last K hours on volume >= V times
            its normal hourly volume; ride it with a trailing stop (T% below the peak)
            or sell after H hours.
  listing - buy a newly listed coin in its first hours of trading, same exits.

Small coins cost more to trade (wide spreads), so COST_PER_SIDE is set high on purpose.

    python pumps.py --days 120
    python pumps.py --synthetic
"""
import argparse
import itertools
import time

COST_PER_SIDE = 0.008      # 0.5% fee + ~0.3% spread/slippage on small coins
SPLIT = 0.6
GRID = {
    "k": [1, 3, 6],            # hours the move is measured over
    "x": [0.05, 0.10, 0.20],   # minimum rise over those hours
    "v": [3, 5],               # volume vs normal (average hourly volume over the prior 7 days)
    "trail": [0.10, 0.20],     # trailing stop below the highest price since entry
    "h": [24, 72],             # max hours to hold
}


def load_all(days):
    from data_source import CryptoComClient
    c = CryptoComClient()
    syms = c.list_spot_symbols()
    print(f"{len(syms)} USD coins listed on Crypto.com")
    out = {}
    for n, s in enumerate(syms):
        try:
            cs = c.candles(s, timeframe="1h", count=days * 24)
            if len(cs) >= 48:
                out[s] = cs
        except Exception as e:
            print(f"  skip {s}: {e}")
        time.sleep(0.05)
        if n % 50 == 0:
            print(f"  loaded {n}/{len(syms)}")
    return out


def load_synthetic(days):
    from data_source import SyntheticClient
    c = SyntheticClient(n=days * 24)
    return {f"C{i}": c.candles(f"C{i}", count=days * 24) for i in range(60)}


def exit_trade(c, i, entry, p):
    """Walk forward from entry bar i; return (exit_return_net, peak_gain, hours_held)."""
    peak = entry
    for j in range(i + 1, min(len(c), i + 1 + p["h"])):
        peak = max(peak, c[j]["h"])
        stop = peak * (1 - p["trail"])
        if c[j]["l"] <= stop:
            px = min(stop, c[j]["o"])
            return px / entry * (1 - COST_PER_SIDE) / (1 + COST_PER_SIDE) - 1, peak / entry - 1, j - i
    j = min(len(c) - 1, i + p["h"])
    return c[j]["c"] / entry * (1 - COST_PER_SIDE) / (1 + COST_PER_SIDE) - 1, peak / entry - 1, j - i


def run_mover(data, p, t_lo, t_hi):
    trades = []
    for s, c in data.items():
        vol_usd = [x["v"] * x["c"] for x in c]
        i = 7 * 24 + p["k"]
        while i < len(c) - 1:
            t = c[i]["t"]
            if not (t_lo <= t < t_hi):
                i += 1
                continue
            base = sum(vol_usd[i - 7 * 24 - p["k"]:i - p["k"]]) / (7 * 24)
            recent = sum(vol_usd[i - p["k"] + 1:i + 1]) / p["k"]
            rise = c[i]["c"] / c[i - p["k"]]["c"] - 1
            if base > 0 and rise >= p["x"] and recent >= p["v"] * base and base * 24 >= 50_000:
                entry = c[i]["c"] * (1 + 0.002)
                r, peak, held = exit_trade(c, i, entry, p)
                trades.append((s, t, r, peak))
                i += max(1, held)       # one position per coin at a time
            else:
                i += 1
    return trades


def run_listing(data, p, t_lo, t_hi, first_seen):
    """Buy at the close of a new coin's first hour (only coins whose history starts inside
    the window, i.e. listed during the test period)."""
    trades = []
    for s, c in data.items():
        t0 = c[0]["t"]
        if t0 <= first_seen + 86_400_000 or not (t_lo <= t0 < t_hi) or len(c) < 3:
            continue
        entry = c[0]["c"] * (1 + 0.005)
        r, peak, _ = exit_trade(c, 0, entry, p)
        trades.append((s, t0, r, peak))
    return trades


def summarize(trades, months):
    if not trades:
        return None
    rs = [t[2] for t in trades]
    wins = sum(1 for r in rs if r > 0)
    big = sum(1 for t in trades if t[3] >= 1.0)
    # portfolio: 5 equal slots, each trade uses one slot (approximation: average trade compounding)
    per_month = len(rs) / months
    avg = sum(rs) / len(rs)
    return {"n": len(rs), "per_mo": per_month, "avg": avg, "win": wins / len(rs),
            "big": big, "best": max(rs), "worst": min(rs),
            "est_mo": (1 + avg * min(per_month, 60) / 5) - 1}   # 5 slots, capped turnover


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    data = load_synthetic(a.days) if a.synthetic else load_all(a.days)
    t_all = sorted({x["t"] for c in data.values() for x in c})
    t0, t_end = t_all[0], t_all[-1] + 1
    t_split = t0 + int((t_end - t0) * SPLIT)
    m_is, m_oos = (t_split - t0) / 2.6e9, (t_end - t_split) / 2.6e9
    print(f"\n{len(data)} coins with data; {m_is:.1f} months in-sample, {m_oos:.1f} months out-of-sample")
    print(f"cost per side {COST_PER_SIDE:.1%} (fees + small-coin spread)\n")

    rows = []
    for combo in itertools.product(*GRID.values()):
        p = dict(zip(GRID, combo))
        is_ = summarize(run_mover(data, p, t0, t_split), m_is)
        oos = summarize(run_mover(data, p, t_split, t_end), m_oos)
        if is_ and oos:
            rows.append((p, is_, oos))
    rows.sort(key=lambda r: r[1]["avg"] * min(r[1]["per_mo"], 60), reverse=True)
    print("EARLY MOVER: top 12 by in-sample, then UNSEEN results "
          "(avg = average net return per trade; big = trades that at some point doubled)")
    print(f"{'params':<40}| {'IS avg':>7} {'IS n':>5} | {'OOS avg':>7} {'OOS n':>5} {'win':>5} {'big':>4} {'best':>7} {'worst':>7} {'~/mo':>7}")
    for p, i, o in rows[:12]:
        ps = " ".join(f"{k}={v}" for k, v in p.items())
        print(f"{ps:<40}| {i['avg']:>+7.2%} {i['n']:>5} | {o['avg']:>+7.2%} {o['n']:>5} {o['win']:>5.0%} "
              f"{o['big']:>4} {o['best']:>+7.0%} {o['worst']:>+7.0%} {o['est_mo']:>+7.1%}")

    print("\nNEW LISTINGS (buy in the first hour of trading), whole period:")
    for trail, h in itertools.product([0.10, 0.20, 0.35], [24, 72, 240]):
        s = summarize(run_listing(data, {"trail": trail, "h": h}, t0, t_end, t0), (t_end - t0) / 2.6e9)
        if s:
            print(f"  trail={trail:.0%} hold<={h}h: {s['n']} listings, avg {s['avg']:+.1%}/trade, "
                  f"win {s['win']:.0%}, doubled at some point: {s['big']}, best {s['best']:+.0%}, worst {s['worst']:+.0%}")


if __name__ == "__main__":
    main()
