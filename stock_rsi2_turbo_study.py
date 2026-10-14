"""Owner 2026-10-14: "we gotta figure out how to profit" - the stock dip-buyer (rsi2) is the only part with a real
record (24y backtest +17..+22%/yr). Can it be made faster without blowing up?

Variants (all rsi2 RSI(2) < 25, hold 10 days, next-open fills, same costs as live), fixed in advance:
  live         3 slots x 1/3, live universe (config.STOCK_UNIVERSE + STOCK_ETFS)
  +lev ETFs    same + 3x index / chip ETFs (TQQQ, UPRO, SOXL, TNA, FAS)
  +crypto stk  same + crypto stocks (MARA, RIOT, HOOD, CLSK)
  +both        both additions
  lev only     only the 3x ETFs (+ SPY for the trend filter)
  2 slots      live universe, 2 x 1/2 (bigger bets)
Window: 16 years (the 3x ETFs exist from 2010), two halves. Decision rule (pre-registered): a variant replaces live
only if its CAGR beats live in BOTH halves, also at 3x costs, and its max drawdown is at most 10 points deeper.

    python stock_rsi2_turbo_study.py               # real data (GitHub Actions)
    python stock_rsi2_turbo_study.py --synthetic   # offline plumbing check
"""
import argparse

import lab
import stock_park_study as sp

LEV = ["TQQQ", "UPRO", "SOXL", "TNA", "FAS"]
CRYPTO = ["MARA", "RIOT", "HOOD", "CLSK"]
DD_SLACK = 0.10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=16)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    syms = sorted(set(sp.UNIVERSE) | set(LEV) | set(CRYPTO))
    prices = lab.load_synthetic(syms, a.years, "stocks") if a.synthetic else lab.load_stocks(syms, a.years)
    base = set(sp.UNIVERSE)
    U = {"live": base, "+lev ETFs": base | set(LEV), "+crypto stk": base | set(CRYPTO),
         "+both": base | set(LEV) | set(CRYPTO), "lev only": set(LEV) | {"SPY"}, "2 slots": base}
    print(f"=== rsi2 turbo study: {a.years} years of daily bars, cost {sp.COST:.3%}/side, RSI(2) < 25, hold 10d ===")
    ref = lab.Ctx(prices, "stocks", "SPY")
    first = min(i for i in range(ref.n) if ref.live["SPY"][i]) + sp.WARMUP
    mid = first + (ref.n - first) // 2
    T = {}
    for name, u in U.items():
        ctx = lab.Ctx({s: x for s, x in prices.items() if s in u}, "stocks", "SPY")
        slots, size = (2, 0.5) if name == "2 slots" else (3, 1 / 3)
        v = sp.variant(name, slots=slots, size=size, reserve=0.0, rsi_max=25, hold=10)
        for h, s0, s1 in (("older", first, mid), ("newer", mid, ref.n), ("full", first, ref.n)):
            for mult in (1, 3):
                rets, expo, trades, _, _ = sp.simulate(ctx, v, s0, s1, cost=mult * sp.COST)
                st = lab.stats(rets, expo, trades, ctx.month[s0:s1], ctx.ppy)
                T[(name, h, mult)] = st
        print(f"{name:<12} " + "  ".join(f"{h} CAGR {T[(name, h, 1)]['cagr']:+6.1%} DD {T[(name, h, 1)]['mdd']:5.1%}"
                                       for h in ("older", "newer", "full"))
              + f"  | 3x cost full {T[(name, 'full', 3)]['cagr']:+6.1%}  $500 -> {sp.BASE * (1 + T[(name, 'full', 1)]['total']):,.0f}")
    print(f"\n=== DECISION vs live: CAGR better in both halves at 1x and 3x cost, max DD at most {DD_SLACK:.0%} deeper ===")
    for name in list(U)[1:]:
        ok = all(T[(name, h, m)]["cagr"] > T[("live", h, m)]["cagr"] and
                 T[(name, h, m)]["mdd"] <= T[("live", h, m)]["mdd"] + DD_SLACK for h in ("older", "newer") for m in (1, 3))
        print(f"  {'PASS' if ok else 'fail'}  {name}")
    print("\nCaveat: today's names (hindsight) - absolute returns are a ceiling; the comparison is what matters.")


if __name__ == "__main__":
    main()
