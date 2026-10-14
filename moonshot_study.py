"""Owner 2026-10-14: "there's gotta be a better way for bigger gains, maybe even stocks - build a portfolio from
$1k to $10k in a few months." Which concentrated, fast strategies have real evidence of very large gains on
unseen data - and how often does each one wipe out?

Everything here is FIXED IN ADVANCE (no tuned parameters), scored on two halves of 16 years (3x ETFs exist from
2010) plus a walk-forward "re-pick" test, at realistic costs (and 3x costs). Signals use day t's close, fills at
day t+1's open (lab.simulate). Long-only, no margin.

Universes (today's lists = HINDSIGHT; the bust names and the "ex-winners" cut are the honesty check):
  LEV3     3x / 2x leveraged ETFs across sectors, winners AND losers (TQQQ, SOXL, TNA, LABU, NUGT, YINN ...)
  LEV3+inv the same plus inverse 3x ETFs (so a rotation can go short-ish in bear markets)
  HIBETA   high-beta single stocks: the famous winners (MSTR, COIN, PLTR, SMCI, NVDA ...) AND the famous busts
           (GME, AMC, PTON, PLUG, LCID, BYND, SPCE, TLRY, NIO ...)
  HIBETA-x HIBETA without its 10 best full-span performers (what a list picked WITHOUT hindsight looks like)
Strategies:
  mom      weekly rotation into the top-K by 3-month return (asset above its 50-day avg; SPY above its 200-day avg
           or everything to cash); 20% trailing stop from the highest close since entry, checked daily
  52w      buy a close at a new 252-day high (SPY above 200d), rank by 6-month return; sell below the 50-day avg or
           a 20% trail; K slots
  gap      "post-earnings"-style gap: open >= +8% over the prior close on >= 3x the 20-day volume, closing above
           the open; buy next open, sell after 20 trading days or a 15% drop; 3 slots
Report per strategy: CAGR / max drawdown by half, every calendar quarter, and ROLLING 3- and 6-month windows
(start any day with $1,000): share that reached 2x / 5x / 10x, share that lost 50%+, median / bad / good case.

    python moonshot_study.py               # real data (GitHub Actions, yfinance)
    python moonshot_study.py --synthetic   # offline plumbing check (fake prices!)
"""
import argparse
import math
import random
import statistics
from datetime import date, timedelta

import lab

LEV3 = ["TQQQ", "UPRO", "SOXL", "TNA", "FAS", "TECL", "LABU", "NUGT", "JNUG", "ERX", "CURE", "DPST", "DFEN", "NAIL",
        "RETL", "UDOW", "TMF", "YINN", "EDC", "KORU", "FNGU", "BULZ", "WEBL", "HIBL", "CONL", "MSTU", "NVDL", "TSLL",
        "BITX", "BOIL", "UCO", "GUSH", "DRN", "UTSL", "MIDU", "SPXL", "TPOR", "WANT", "PILL"]
INVERSE = ["SQQQ", "SPXS", "TZA", "SOXS", "FAZ", "TMV", "DRV", "YANG", "TECS", "SDOW"]
HIBETA = ["MSTR", "COIN", "PLTR", "SMCI", "TSLA", "NVDA", "AMD", "MARA", "RIOT", "HOOD", "APP", "IONQ", "RGTI", "QBTS",
          "CVNA", "UPST", "AFRM", "SOFI", "GME", "AMC", "ROKU", "SHOP", "XYZ", "NET", "CRWD", "SNOW", "DDOG", "TTD",
          "ENPH", "PLUG", "FCEL", "LCID", "RIVN", "BYND", "SPCE", "TLRY", "NIO", "CLSK", "HUT", "BITF", "CIFR", "IREN",
          "OKLO", "SMR", "VST", "CEG", "RKLB", "ASTS", "LUNR", "ARM", "NBIS", "HIMS", "CELH", "ELF", "DKNG", "NFLX",
          "META", "UBER", "AVGO", "MU", "PTON", "ZM", "DOCU", "SNAP", "PINS", "LYFT", "WOLF", "RUN", "SEDG", "NKLA",
          "CHPT", "QS", "BB", "CLOV", "SAVA", "NVAX", "MRNA", "BNTX", "SE", "MELI", "BABA", "JD", "PDD", "BIDU"]
REFS = ["SPY", "QQQ"]
COST_STOCK, COST_ETF = 0.001, 0.0005      # per side: realistic slippage for a small account (live config is 0.05%)
WARMUP = 260
K_MAX = 3
GAP_HOLD, GAP_STOP = 20, 0.15


# ---------------------------------------------------------------- data (with volume)
def load_stocks_vol(symbols, years):
    import yfinance as yf
    start = (date.today() - timedelta(days=years * 365)).isoformat()
    df = yf.download(sorted(set(symbols)), start=start, interval="1d", auto_adjust=True, group_by="ticker",
                     progress=False, threads=True)
    prices, vols = {}, {}
    for s in sorted(set(symbols)):
        try:
            d = df[s].dropna()
        except KeyError:
            print(f"  skip {s}: no data")
            continue
        if len(d) < 60:
            print(f"  skip {s}: only {len(d)} bars")
            continue
        prices[s] = {int(ix.timestamp()) // 86_400: (float(r["Open"]), float(r["High"]), float(r["Low"]), float(r["Close"]))
                     for ix, r in d.iterrows()}
        vols[s] = {int(ix.timestamp()) // 86_400: float(r["Volume"]) for ix, r in d.iterrows()}
        print(f"  {s}: {len(d)} days from {d.index[0].date()}")
    return prices, vols


def load_synth_vol(symbols, years):
    prices = lab.load_synthetic(symbols, years, "stocks")
    rng = random.Random(5)
    vols = {s: {d: rng.lognormvariate(14, 0.8) for d in ser} for s, ser in prices.items()}
    return prices, vols


def drop_delisted(prices, vols, end_day, grace=15):
    """A symbol whose bars stop well before the end can't be sold in the simulation (it would sit at a stale
    price forever), so it is dropped - and named, because dropping dead names is itself survivorship bias."""
    gone = [s for s, ser in prices.items() if end_day - max(ser) > grace]
    for s in gone:
        del prices[s]
        del vols[s]
    if gone:
        print(f"  dropped (history ends early - delisted / renamed): {', '.join(sorted(gone))}")
    return prices, vols


# ---------------------------------------------------------------- strategies (lab.simulate interface)
def peak_since(ctx, s, e, i):
    return max(x for x in ctx.c[s][e:i + 1] if x is not None)


def mom_strategy(uni, K, L=63, trend=True, trail=0.20, above50=True):
    def fn(ctx, i, held, p):
        keep = {}
        for s, (e, px) in held.items():
            if trail and ctx.c[s][i] < peak_since(ctx, s, e, i) * (1 - trail):
                continue
            keep[s] = 1 / K
        if not ctx.wend[i]:
            return keep, False
        if trend and not ctx.regime(i, 200):
            return {}, True
        cands = []
        for s in uni:
            if s not in ctx.c or not ctx.live[s][i]:
                continue
            r, m = ctx.ind(s, "ret", L)[i], ctx.ind(s, "sma", 50)[i]
            if r is None or m is None or r <= 0 or (above50 and ctx.c[s][i] <= m):
                continue
            cands.append((r, s))
        cands.sort(reverse=True)
        return {s: 1 / K for _, s in cands[:K]}, True
    return fn


def inv_mom_strategy(uni, inv, K):
    """Rotation that may hold inverse ETFs: when SPY is below its 200-day avg the candidates are the inverse
    list, else the long list. Same ranking / trail as mom."""
    long_fn, short_fn = mom_strategy(uni, K, trend=False), mom_strategy(inv, K, trend=False)

    def fn(ctx, i, held, p):
        return (long_fn if ctx.regime(i, 200) else short_fn)(ctx, i, held, p)
    return fn


def breakout_strategy(uni, K, trail=0.20):
    def fn(ctx, i, held, p):
        keep = {}
        for s, (e, px) in held.items():
            m50 = ctx.ind(s, "sma", 50)[i]
            if (m50 is not None and ctx.c[s][i] < m50) or ctx.c[s][i] < peak_since(ctx, s, e, i) * (1 - trail):
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


def gap_strategy(uni, vols, K=3):
    def fn(ctx, i, held, p):
        keep = {}
        for s, (e, px) in held.items():
            if i - e + 1 >= GAP_HOLD or ctx.c[s][i] < px * (1 - GAP_STOP):
                continue
            keep[s] = 1 / K
        if len(keep) >= K:
            return keep, False
        cands = []
        for s in uni:
            if s in keep or s not in ctx.c or not ctx.live[s][i] or i < 21:
                continue
            o, c, pc = ctx.o[s][i], ctx.c[s][i], ctx.c[s][i - 1]
            v = vols[s].get(ctx.days[i])
            prev = [vols[s].get(ctx.days[j]) for j in range(i - 20, i)]
            prev = [x for x in prev if x]
            if not o or not pc or v is None or len(prev) < 15:
                continue
            avg = sum(prev) / len(prev)
            gap = o / pc - 1
            if gap >= 0.08 and v >= 3 * avg and c > o:
                cands.append((gap, s))
        cands.sort(reverse=True)
        for _, s in cands[:K - len(keep)]:
            keep[s] = 1 / K
        return keep, False
    return fn


def hold_strategy(sym):
    def fn(ctx, i, held, p):
        return ({sym: 1.0} if sym in ctx.c and ctx.live[sym][i] else {}), False
    return fn


def ew_strategy(uni):
    """Equal weight, rebalanced monthly (a hindsight ceiling for the universe itself)."""
    def fn(ctx, i, held, p):
        live = [s for s in uni if s in ctx.c and ctx.live[s][i]]
        if ctx.mrem[i] != 1:
            return {s: 1 / max(1, len(live)) for s in held}, False
        return {s: 1 / len(live) for s in live}, True
    return fn


# ---------------------------------------------------------------- metrics
def curve(rets):
    eq, out = 1.0, [1.0]
    for r in rets:
        eq *= 1 + r
        out.append(eq)
    return out


def rolling(rets, n):
    eq = curve(rets)
    g = [eq[k + n] / eq[k] for k in range(0, len(eq) - n)]
    if not g:
        return None
    g.sort()
    q = lambda f: g[min(len(g) - 1, int(f * len(g)))]
    return {"n": len(g), "2x": sum(x >= 2 for x in g) / len(g), "5x": sum(x >= 5 for x in g) / len(g),
            "10x": sum(x >= 10 for x in g) / len(g), "half": sum(x <= 0.5 for x in g) / len(g),
            "p10": q(0.10), "med": q(0.50), "p90": q(0.90), "min": g[0], "max": g[-1]}


def quarters(rets, dates):
    out, cur, last = {}, 1.0, None
    for r, d in zip(rets, dates):
        q = (d.year, (d.month - 1) // 3 + 1)
        if q != last and last is not None:
            out[last] = cur - 1
            cur = 1.0
        cur *= 1 + r
        last = q
    out[last] = cur - 1
    return out


def fmt_roll(r):
    if not r:
        return "n/a"
    return (f"2x {r['2x']:4.0%}  5x {r['5x']:4.0%}  10x {r['10x']:4.0%}  lost half+ {r['half']:4.0%} | "
            f"$1,000 -> bad {1000 * r['p10']:>6,.0f}  median {1000 * r['med']:>6,.0f}  good {1000 * r['p90']:>6,.0f}  "
            f"(worst {1000 * r['min']:,.0f}, best {1000 * r['max']:,.0f}; n {r['n']})")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=16)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    syms = sorted(set(LEV3) | set(INVERSE) | set(HIBETA) | set(REFS))
    print(f"=== moonshot study: {len(syms)} symbols, {a.years} years, cost {COST_STOCK:.2%}/side stocks, "
          f"{COST_ETF:.2%}/side ETFs ===")
    prices, vols = load_synth_vol(syms, a.years) if a.synthetic else load_stocks_vol(syms, a.years)
    if a.synthetic:
        print("*** SYNTHETIC DATA: tests the code only ***")
    end_day = max(max(ser) for ser in prices.values())
    prices, vols = drop_delisted(prices, vols, end_day)
    ctx = lab.Ctx(prices, "stocks", "SPY")
    lev = [s for s in LEV3 if s in prices]
    inv = [s for s in INVERSE if s in prices]
    hib = [s for s in HIBETA if s in prices]
    first = min(i for i in range(ctx.n) if ctx.live["SPY"][i]) + WARMUP
    mid = first + (ctx.n - first) // 2
    # hindsight cut: the 10 best full-span performers of HIBETA (first close -> last close)
    perf = []
    for s in hib:
        ser = prices[s]
        d0, d1 = min(ser), max(ser)
        perf.append((ser[d1][3] / ser[d0][3], s))
    perf.sort(reverse=True)
    winners = [s for _, s in perf[:10]]
    hib_x = [s for s in hib if s not in winners]
    print(f"\nLEV3 {len(lev)}: {' '.join(lev)}\nINVERSE {len(inv)}: {' '.join(inv)}\nHIBETA {len(hib)}: {' '.join(hib)}")
    print(f"HIBETA's 10 best full-span names (removed in HIBETA-x): {' '.join(f'{s} {m:,.0f}x' for m, s in perf[:10])}")
    print(f"span {ctx.dates[first]} .. {ctx.dates[-1]}; halves split {ctx.dates[mid]}")

    S = [
        ("hold SPY", hold_strategy("SPY"), COST_ETF),
        ("hold QQQ", hold_strategy("QQQ"), COST_ETF),
        ("hold TQQQ", hold_strategy("TQQQ"), COST_ETF),
        ("hold SOXL", hold_strategy("SOXL"), COST_ETF),
        ("HIBETA equal-weight (ceiling)", ew_strategy(hib), COST_STOCK),
        ("LEV3 mom top1 +trend", mom_strategy(lev, 1), COST_ETF),
        ("LEV3 mom top2 +trend", mom_strategy(lev, 2), COST_ETF),
        ("LEV3 mom top1 no filter", mom_strategy(lev, 1, trend=False, above50=False), COST_ETF),
        ("LEV3 mom top1 1-month", mom_strategy(lev, 1, L=21), COST_ETF),
        ("LEV3+inv mom top1", inv_mom_strategy(lev, inv, 1), COST_ETF),
        ("HIBETA mom top1 +trend", mom_strategy(hib, 1), COST_STOCK),
        ("HIBETA mom top3 +trend", mom_strategy(hib, 3), COST_STOCK),
        ("HIBETA mom top1 1-month", mom_strategy(hib, 1, L=21), COST_STOCK),
        ("HIBETA mom top1 no filter", mom_strategy(hib, 1, trend=False, above50=False), COST_STOCK),
        ("HIBETA-x mom top1 +trend", mom_strategy(hib_x, 1), COST_STOCK),
        ("HIBETA-x mom top3 +trend", mom_strategy(hib_x, 3), COST_STOCK),
        ("HIBETA 52w-high top1", breakout_strategy(hib, 1), COST_STOCK),
        ("HIBETA 52w-high top3", breakout_strategy(hib, 3), COST_STOCK),
        ("HIBETA-x 52w-high top3", breakout_strategy(hib_x, 3), COST_STOCK),
        ("HIBETA gap-up 3 slots", gap_strategy(hib, vols, 3), COST_STOCK),
        ("HIBETA-x gap-up 3 slots", gap_strategy(hib_x, vols, 3), COST_STOCK),
        ("ALL (HIBETA+LEV3) mom top1", mom_strategy(hib + lev, 1), COST_STOCK),
        ("ALL mom top2 +trend", mom_strategy(hib + lev, 2), COST_STOCK),
        # maximum aggression: all-in on the single hottest name of the last month, no filter, no stop
        ("YOLO HIBETA top1 1-month no stop", mom_strategy(hib, 1, L=21, trend=False, trail=0, above50=False), COST_STOCK),
        ("YOLO LEV3 top1 1-month no stop", mom_strategy(lev, 1, L=21, trend=False, trail=0, above50=False), COST_ETF),
    ]
    R = {}
    hdr = f"{'strategy':<32} {'CAGR':>7} {'maxDD':>6} {'trd/yr':>6} {'win%':>5} | {'older CAGR/DD':>14} | {'newer CAGR/DD':>14} | {'3x cost CAGR':>12} | $1,000 -> full"
    print("\n=== FULL SPAN, TWO HALVES (each from a flat start) ===")
    print(hdr)
    print("-" * len(hdr))
    for name, fn, cost in S:
        rets, expo, trades = lab.simulate(ctx, fn, {}, first, ctx.n, cost)
        st = lab.stats(rets, expo, trades, ctx.month[first:], ctx.ppy)
        ro, eo, to = lab.simulate(ctx, fn, {}, first, mid, cost)
        rn, en, tn = lab.simulate(ctx, fn, {}, mid, ctx.n, cost)
        so = lab.stats(ro, eo, to, ctx.month[first:mid], ctx.ppy)
        sn = lab.stats(rn, en, tn, ctx.month[mid:], ctx.ppy)
        r3, e3, t3 = lab.simulate(ctx, fn, {}, first, ctx.n, 3 * cost)
        s3 = lab.stats(r3, e3, t3, ctx.month[first:], ctx.ppy)
        R[name] = {"rets": rets, "st": st, "older": so, "newer": sn, "c3": s3, "trades": trades}
        print(f"{name:<32} {st['cagr']:>+7.1%} {st['mdd']:>6.0%} {st['n_trades'] / (st['days'] / 252):>6.0f} "
              f"{(st['win'] if st['win'] == st['win'] else 0):>5.0%} | {so['cagr']:>+6.1%} / {so['mdd']:>4.0%} | "
              f"{sn['cagr']:>+6.1%} / {sn['mdd']:>4.0%} | {s3['cagr']:>+11.1%} | {1000 * (1 + st['total']):>12,.0f}")

    print("\n=== ROLLING WINDOWS: start any day with $1,000 (full span; windows overlap, so n is NOT independent trials) ===")
    for n, lbl in ((63, "3 months"), (126, "6 months")):
        print(f"\n--- {lbl} ({n} trading days) ---")
        for name, _, _ in S:
            print(f"{name:<32} {fmt_roll(rolling(R[name]['rets'], n))}")
    print("\n--- 6 months, NEWER HALF only (the part no list was fitted on... but the names are still today's) ---")
    for name, _, _ in S:
        print(f"{name:<32} {fmt_roll(rolling(R[name]['rets'][mid - first:], 126))}")

    print("\n=== PER-QUARTER RETURNS (fast strategies only) ===")
    show = [n for n, _, _ in S if not n.startswith("hold") and "ceiling" not in n]
    yrs = sorted({d.year for d in ctx.dates[first:]})
    for name in show:
        q = quarters(R[name]["rets"], ctx.dates[first:])
        print(f"\n{name}:")
        for y in yrs:
            cells = [f"Q{k} {q[(y, k)]:>+6.0%}" if (y, k) in q else f"Q{k}      -" for k in (1, 2, 3, 4)]
            yr = math.prod(1 + q[(y, k)] for k in (1, 2, 3, 4) if (y, k) in q) - 1
            print(f"  {y}  " + "  ".join(cells) + f"   year {yr:>+6.0%}")

    # walk-forward re-pick: every 6 months choose, among the fast strategies, the best Sharpe on the prior 18
    # months and trade it on the next 6 (lab.windows). Shows what "let the engine switch" would have done.
    print("\n=== WALK-FORWARD RE-PICK among the fast strategies (chosen on the prior 18 months by Sharpe, traded on "
          "the unseen next 6) ===")
    fast = [(n, fn, c) for n, fn, c in S if n in show]
    full = {n: (lab.simulate(ctx, fn, {}, 0, ctx.n, c), fn, c) for n, fn, c in fast}
    rets_o, picks = [], []
    for ts0, te0, te1 in lab.windows(ctx):
        if te0 < first:
            continue
        best = max(full, key=lambda n: lab.sharpe(full[n][0][0][ts0:te0], ctx.ppy))
        r, e, t = lab.simulate(ctx, full[best][1], {}, te0, te1, full[best][2])
        rets_o += r
        picks.append((ctx.dates[te0], best, math.prod(1 + x for x in r) - 1))
    if rets_o:
        st = lab.stats(rets_o, [1.0] * len(rets_o), [], ctx.month[-len(rets_o):], ctx.ppy)
        print(f"stitched OOS: CAGR {st['cagr']:+.1%}  maxDD {st['mdd']:.0%}  $1,000 -> {1000 * (1 + st['total']):,.0f}")
        print(f"  3 months: {fmt_roll(rolling(rets_o, 63))}\n  6 months: {fmt_roll(rolling(rets_o, 126))}")
        for d, n, r in picks:
            print(f"    {d}  {n:<32} {r:>+7.1%}")

    print("\n=== TRADE-LEVEL (full span): what the single trades look like ===")
    for name in show:
        t = R[name]["trades"]
        if not t:
            continue
        t2 = sorted(t)
        print(f"{name:<32} n {len(t):>5}  mean {statistics.mean(t):>+7.1%}  median {statistics.median(t):>+7.1%}  "
              f"win {sum(x > 0 for x in t) / len(t):>4.0%}  >=+100% {sum(x >= 1 for x in t) / len(t):>4.1%}  "
              f"<=-30% {sum(x <= -0.3 for x in t) / len(t):>4.1%}  worst {t2[0]:>+6.0%}  best {t2[-1]:>+7.0%}")
    print("\nCaveats: today's ticker lists (hindsight; HIBETA-x removes the 10 best names, the busts are in); names "
          "dropped when their history ends early; daily bars, next-open fills; no borrow / options / margin; leveraged "
          "ETFs carry their real decay in the prices. Rolling windows overlap (not independent).")


if __name__ == "__main__":
    main()
