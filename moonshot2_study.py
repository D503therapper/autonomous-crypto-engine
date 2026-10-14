"""Follow-up to moonshot_study.py (owner 2026-10-14: "$1k to $10k in a few months"). Run 1 found: every TOP-1 rotation
(weekly, 3-month momentum, 20% trailing stop) went to ~zero over 15 years - the stop plus weekly churn turned a
+1%/trade edge into -20..-45%/yr; the only robust fast strategy was 52-week-high breakouts in 3 slots (+35..38%/yr,
both halves, with and without the hindsight names). This run tests the neighbours, fixed in advance:
  - 52w-high breakouts: 2 / 3 / 5 slots, with the 20% trail or only the 50-day-average exit, on HIBETA / HIBETA-x
    and on the 3x ETFs
  - classic momentum WITHOUT a stop: monthly, 12-1 month (academic) or 6-month lookback, top 1 / top 3, trend filter
  - 3x ETFs only while above their 200-day average (TQQQ, SOXL; top-1 of the 4 big ones by 6-month return)
  - the 3-month weekly rotation with a wider (35%) trail or none, top 1, to see whether the stop was the killer
Same data, costs, halves, rolling 3- / 6-month windows and quarter tables as run 1 (functions imported from it).

    python moonshot2_study.py               # real data (GitHub Actions)
    python moonshot2_study.py --synthetic   # offline plumbing check
"""
import argparse
import math
import statistics

import lab
import moonshot_study as m1

CORE4 = ["TQQQ", "SOXL", "TNA", "UPRO"]


def mom2(uni, K, L=63, skip=0, monthly=False, trend=True, trail=0.20, above50=True):
    """Rotation into the top-K by the return over L days ending `skip` days ago (12-1 momentum: L=231, skip=21),
    rebalanced weekly or monthly; optional SPY 200-day filter, 50-day filter and trailing stop (0 = none)."""
    def fn(ctx, i, held, p):
        keep = {}
        for s, (e, px) in held.items():
            if trail and ctx.c[s][i] < m1.peak_since(ctx, s, e, i) * (1 - trail):
                continue
            keep[s] = 1 / K
        if not (ctx.mrem[i] == 1 if monthly else ctx.wend[i]):
            return keep, False
        if trend and not ctx.regime(i, 200):
            return {}, True
        cands = []
        for s in uni:
            if s not in ctx.c or not ctx.live[s][i] or i < L + skip:
                continue
            c0, c1, m = ctx.c[s][i - L - skip], ctx.c[s][i - skip], ctx.ind(s, "sma", 50)[i]
            if not c0 or not c1 or m is None:
                continue
            r = c1 / c0 - 1
            if r <= 0 or (above50 and ctx.c[s][i] <= m):
                continue
            cands.append((r, s))
        cands.sort(reverse=True)
        return {s: 1 / K for _, s in cands[:K]}, True
    return fn


def breakout2(uni, K, trail=0.20, exit_sma=50):
    def fn(ctx, i, held, p):
        keep = {}
        for s, (e, px) in held.items():
            m = ctx.ind(s, "sma", exit_sma)[i]
            if (m is not None and ctx.c[s][i] < m) or (trail and ctx.c[s][i] < m1.peak_since(ctx, s, e, i) * (1 - trail)):
                continue
            keep[s] = 1 / K
        if len(keep) >= K or not ctx.regime(i, 200):
            return keep, False
        cands = []
        for s in uni:
            if s in keep or s not in ctx.c or not ctx.live[s][i]:
                continue
            hh, r = ctx.ind(s, "hh", 252)[i], ctx.ind(s, "ret", 126)[i]
            if hh is not None and r is not None and ctx.c[s][i] >= hh:
                cands.append((r, s))
        cands.sort(reverse=True)
        for _, s in cands[:K - len(keep)]:
            keep[s] = 1 / K
        return keep, False
    return fn


def trend_hold(sym, n=200):
    """Hold the ETF while it closes above its own n-day average, else cash (checked daily)."""
    def fn(ctx, i, held, p):
        if sym not in ctx.c or not ctx.live[sym][i]:
            return {}, False
        m = ctx.ind(sym, "sma", n)[i]
        return ({sym: 1.0} if m is not None and ctx.c[sym][i] > m else {}), False
    return fn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=16)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    syms = sorted(set(m1.LEV3) | set(m1.HIBETA) | set(m1.REFS))
    print(f"=== moonshot study 2: {len(syms)} symbols, {a.years} years, cost {m1.COST_STOCK:.2%}/side stocks, "
          f"{m1.COST_ETF:.2%}/side ETFs ===")
    prices, vols = m1.load_synth_vol(syms, a.years) if a.synthetic else m1.load_stocks_vol(syms, a.years)
    if a.synthetic:
        print("*** SYNTHETIC DATA: tests the code only ***")
    end_day = max(max(ser) for ser in prices.values())
    prices, vols = m1.drop_delisted(prices, vols, end_day)
    ctx = lab.Ctx(prices, "stocks", "SPY")
    lev = [s for s in m1.LEV3 if s in prices]
    hib = [s for s in m1.HIBETA if s in prices]
    core = [s for s in CORE4 if s in prices]
    first = min(i for i in range(ctx.n) if ctx.live["SPY"][i]) + m1.WARMUP
    mid = first + (ctx.n - first) // 2
    perf = sorted(((prices[s][max(prices[s])][3] / prices[s][min(prices[s])][3], s) for s in hib), reverse=True)
    winners = [s for _, s in perf[:10]]
    hib_x = [s for s in hib if s not in winners]
    print(f"span {ctx.dates[first]} .. {ctx.dates[-1]}; halves split {ctx.dates[mid]}; HIBETA-x drops {' '.join(winners)}")
    CS, CE = m1.COST_STOCK, m1.COST_ETF
    S = [
        ("hold QQQ", m1.hold_strategy("QQQ"), CE),
        ("TQQQ above 200d else cash", trend_hold("TQQQ"), CE),
        ("SOXL above 200d else cash", trend_hold("SOXL"), CE),
        ("CORE4 top1 6-mo monthly 200d", mom2(core, 1, L=126, monthly=True, trail=0, above50=False), CE),
        ("CORE4 top1 3-mo monthly 200d", mom2(core, 1, L=63, monthly=True, trail=0, above50=False), CE),
        ("LEV3 top1 12-1 monthly no stop", mom2(lev, 1, L=231, skip=21, monthly=True, trail=0), CE),
        ("LEV3 top3 12-1 monthly no stop", mom2(lev, 3, L=231, skip=21, monthly=True, trail=0), CE),
        ("LEV3 52w-high top1 50d exit", breakout2(lev, 1, trail=0), CE),
        ("LEV3 52w-high top3 50d exit", breakout2(lev, 3, trail=0), CE),
        ("LEV3 52w-high top3 +20% trail", breakout2(lev, 3), CE),
        ("HIBETA top1 12-1 monthly no stop", mom2(hib, 1, L=231, skip=21, monthly=True, trail=0), CS),
        ("HIBETA top3 12-1 monthly no stop", mom2(hib, 3, L=231, skip=21, monthly=True, trail=0), CS),
        ("HIBETA-x top3 12-1 monthly", mom2(hib_x, 3, L=231, skip=21, monthly=True, trail=0), CS),
        ("HIBETA top1 6-mo monthly no stop", mom2(hib, 1, L=126, monthly=True, trail=0), CS),
        ("HIBETA top3 6-mo monthly no stop", mom2(hib, 3, L=126, monthly=True, trail=0), CS),
        ("HIBETA top1 3-mo weekly 35% trail", mom2(hib, 1, L=63, trail=0.35), CS),
        ("HIBETA top1 3-mo weekly no stop", mom2(hib, 1, L=63, trail=0), CS),
        ("HIBETA 52w-high top2 +trail", breakout2(hib, 2), CS),
        ("HIBETA 52w-high top3 +trail (run1)", breakout2(hib, 3), CS),
        ("HIBETA 52w-high top5 +trail", breakout2(hib, 5), CS),
        ("HIBETA 52w-high top3 50d exit only", breakout2(hib, 3, trail=0), CS),
        ("HIBETA 52w-high top3 20d exit", breakout2(hib, 3, trail=0, exit_sma=20), CS),
        ("HIBETA-x 52w-high top2 +trail", breakout2(hib_x, 2), CS),
        ("HIBETA-x 52w-high top3 50d only", breakout2(hib_x, 3, trail=0), CS),
        ("HIBETA-x 52w-high top5 +trail", breakout2(hib_x, 5), CS),
        ("ALL 52w-high top3 +trail", breakout2(hib + lev, 3), CS),
    ]
    R = {}
    hdr = (f"{'strategy':<36} {'CAGR':>7} {'maxDD':>6} {'trd/yr':>6} {'win%':>5} | {'older CAGR/DD':>14} | "
           f"{'newer CAGR/DD':>14} | {'3x cost CAGR':>12} | $1,000 -> full")
    print("\n=== FULL SPAN, TWO HALVES (each from a flat start) ===")
    print(hdr)
    print("-" * len(hdr))
    for name, fn, cost in S:
        rets, expo, trades = lab.simulate(ctx, fn, {}, first, ctx.n, cost)
        st = lab.stats(rets, expo, trades, ctx.month[first:], ctx.ppy)
        so = lab.stats(*lab.simulate(ctx, fn, {}, first, mid, cost), ctx.month[first:mid], ctx.ppy)
        sn = lab.stats(*lab.simulate(ctx, fn, {}, mid, ctx.n, cost), ctx.month[mid:], ctx.ppy)
        s3 = lab.stats(*lab.simulate(ctx, fn, {}, first, ctx.n, 3 * cost), ctx.month[first:], ctx.ppy)
        R[name] = {"rets": rets, "st": st, "trades": trades}
        print(f"{name:<36} {st['cagr']:>+7.1%} {st['mdd']:>6.0%} {st['n_trades'] / (st['days'] / 252):>6.0f} "
              f"{(st['win'] if st['win'] == st['win'] else 0):>5.0%} | {so['cagr']:>+6.1%} / {so['mdd']:>4.0%} | "
              f"{sn['cagr']:>+6.1%} / {sn['mdd']:>4.0%} | {s3['cagr']:>+11.1%} | {1000 * (1 + st['total']):>12,.0f}")

    print("\n=== ROLLING WINDOWS: start any day with $1,000 (windows overlap, so n is NOT independent trials) ===")
    for n, lbl in ((63, "3 months"), (126, "6 months")):
        print(f"\n--- {lbl} ({n} trading days), full span ---")
        for name, _, _ in S:
            print(f"{name:<36} {m1.fmt_roll(m1.rolling(R[name]['rets'], n))}")
    print("\n--- 6 months, NEWER HALF only ---")
    for name, _, _ in S:
        print(f"{name:<36} {m1.fmt_roll(m1.rolling(R[name]['rets'][mid - first:], 126))}")

    print("\n=== PER-YEAR RETURNS ===")
    yrs = sorted({d.year for d in ctx.dates[first:]})
    print(f"{'strategy':<36} " + " ".join(f"{y % 100:>5}" for y in yrs))
    for name, _, _ in S:
        q = m1.quarters(R[name]["rets"], ctx.dates[first:])
        cells = []
        for y in yrs:
            ks = [k for k in (1, 2, 3, 4) if (y, k) in q]
            cells.append(f"{math.prod(1 + q[(y, k)] for k in ks) - 1:>+5.0%}" if ks else "    -")
        print(f"{name:<36} " + " ".join(cells))

    print("\n=== PER-QUARTER RETURNS (the breakout strategies) ===")
    for name, _, _ in S:
        if "52w" not in name or "HIBETA" not in name:
            continue
        q = m1.quarters(R[name]["rets"], ctx.dates[first:])
        print(f"\n{name}:")
        for y in yrs:
            cells = [f"Q{k} {q[(y, k)]:>+6.0%}" if (y, k) in q else f"Q{k}      -" for k in (1, 2, 3, 4)]
            yr = math.prod(1 + q[(y, k)] for k in (1, 2, 3, 4) if (y, k) in q) - 1
            print(f"  {y}  " + "  ".join(cells) + f"   year {yr:>+6.0%}")

    print("\n=== TRADE-LEVEL (full span) ===")
    for name, _, _ in S:
        t = R[name]["trades"]
        if not t:
            continue
        t2 = sorted(t)
        print(f"{name:<36} n {len(t):>5}  mean {statistics.mean(t):>+7.1%}  median {statistics.median(t):>+7.1%}  "
              f"win {sum(x > 0 for x in t) / len(t):>4.0%}  >=+100% {sum(x >= 1 for x in t) / len(t):>4.1%}  "
              f"<=-30% {sum(x <= -0.3 for x in t) / len(t):>4.1%}  worst {t2[0]:>+6.0%}  best {t2[-1]:>+7.0%}")
    print("\nCaveats as in moonshot_study.py: today's ticker lists (hindsight), delisted names dropped, daily bars, "
          "no margin / options; rolling windows overlap.")


if __name__ == "__main__":
    main()
