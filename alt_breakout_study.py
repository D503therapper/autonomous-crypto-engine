"""Owner 2026-10-14: "what about alt coins - did Fable study them?" The stock winner (moonshot2_study: 52-week-high
breakouts, top 5, market filter, sell below the 50-day average or 20% off the high: +44.8%/yr) applied to ~60
Crypto.com alt coins (alt_lab_study.ALTS), market filter = BTC above its 200-day average. Fixed in advance: top 3 and
top 5, with / without the 20% trail, and a 90-day-high version (crypto moves faster); fees 0.5% and 0.2% per side.
Scored on two halves and on rolling 3- / 6-month windows ($1,000 -> bad / median / good, 2x / 5x / 10x, lost half).

    python alt_breakout_study.py --years 5
"""
import argparse

import alt_lab_study as A
import config
import lab
import moonshot_study as m1


def breakout(uni, K, hh_n=252, trail=0.20, exit_sma=50, ret_n=126):
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
            hh, r = ctx.ind(s, "hh", hh_n)[i], ctx.ind(s, "ret", ret_n)[i]
            if hh is not None and r is not None and ctx.c[s][i] >= hh:
                cands.append((r, s))
        cands.sort(reverse=True)
        for _, s in cands[:K - len(keep)]:
            keep[s] = 1 / K
        return keep, False
    return fn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    syms = sorted(set(A.ALTS) | set(config.UNIVERSE))
    prices = lab.load_synthetic(syms, a.years, "crypto") if a.synthetic else lab.load_crypto(syms, a.years)
    ctx = lab.Ctx(prices, "crypto", "BTC")
    uni = [s for s in ctx.syms if s != "BTC"]
    first = min(i for i in range(ctx.n) if ctx.live["BTC"][i]) + 260
    mid = first + (ctx.n - first) // 2
    V = {"52w top5": breakout(uni, 5), "52w top3": breakout(uni, 3), "52w top5 50d-only": breakout(uni, 5, trail=0),
         "90d top5": breakout(uni, 5, hh_n=90, ret_n=60), "90d top3": breakout(uni, 3, hh_n=90, ret_n=60)}
    print(f"=== alt-coin breakout study: {len(uni)} alts, {ctx.dates[first]} .. {ctx.dates[-1]}, halves split {ctx.dates[mid]} ===")
    for cost in (0.005, 0.002):
        print(f"\n--- cost {cost:.1%} per side ---")
        for name, fn in V.items():
            r_full, _, tr = lab.simulate(ctx, fn, {}, first, ctx.n, cost)
            r_old = lab.simulate(ctx, fn, {}, first, mid, cost)[0]
            r_new = lab.simulate(ctx, fn, {}, mid, ctx.n, cost)[0]
            st = lab.stats(r_full, *lab.simulate(ctx, fn, {}, first, ctx.n, cost)[1:], ctx.month[first:], ctx.ppy)
            so = lab.stats(r_old, *lab.simulate(ctx, fn, {}, first, mid, cost)[1:], ctx.month[first:mid], ctx.ppy)
            sn = lab.stats(r_new, *lab.simulate(ctx, fn, {}, mid, ctx.n, cost)[1:], ctx.month[mid:], ctx.ppy)
            print(f"{name:<18} CAGR {st['cagr']:+7.1%} (older {so['cagr']:+7.1%} / newer {sn['cagr']:+7.1%})  maxDD {st['mdd']:5.1%}  trades {len(tr)}")
            print(f"{'':<18} 3 months: {m1.fmt_roll(m1.rolling(r_full, 91))}")
            print(f"{'':<18} 6 months: {m1.fmt_roll(m1.rolling(r_full, 182))}")
    hb = lab.hold_bench(ctx, first, ctx.n, 0.005)
    st = lab.stats(*hb, ctx.month[first:], ctx.ppy)
    print(f"\nreference hold BTC: CAGR {st['cagr']:+.1%} maxDD {st['mdd']:.1%}")
    print("Caveat: today's coin list (survivorship) - dead alts are missing, so results are a ceiling.")


if __name__ == "__main__":
    main()
