"""Is "TQQQ only while it closes above its 200-day average, else cash" good enough for the OFFICIAL stocks account?
(owner 2026-11-17: "the stocks aren't doing much ... run studies and figure it out" / "do whatever Fable thinks is best")

moonshot2_study.py scored it +37.5%/yr 2011-2026 (both halves, max drawdown 48%) - but TQQQ has only existed since
2010, i.e. only inside one long Nasdaq bull market. The honest test is the part TQQQ never lived through: the
2000-2002 dot-com crash and 2008. This study rebuilds a 3x daily Nasdaq-100 fund from QQQ's own daily bars back to
1999 (3x the daily move, minus the 0.95% fee and the cost of borrowing 2x at the T-bill rate + 0.4%), checks the
rebuild against the real TQQQ on the years both exist, and runs the rule and its neighbours on it.

Everything fixed in advance (no tuning): signal at the close, trade at the NEXT open, 0.05%/side (and 3x that), cash
earns nothing. Rules:
    own200      hold the 3x fund while ITS close is above ITS 200-day average (the live candidate)
    own100/150/250   the same with a 100 / 150 / 250-day average (neighbours: does 200 stand alone?)
    qqq200      hold the 3x fund while QQQ (the plain index fund) is above QQQ's 200-day average
    2x own200   the 2x fund (QLD / rebuilt) under the same rule
    late        own200 traded one full day late (at the next close) - how much does sloppy execution cost?
    hold        buy and hold (QQQ, the 3x fund)
Eras: 2000-2010 (before TQQQ existed - the true out-of-sample test), 2010-2018, 2018-today.

THE BAR, written before the run: adopt for the official account only if on 2000-2010 the rule (a) did not lose money,
(b) beat holding QQQ and (c) never fell more than 65% from a high - and the 150 / 250-day neighbours agree in every era.

    python stock_tqqq_study.py               # real data (GitHub Actions; Yahoo is not reachable from the sandbox)
    python stock_tqqq_study.py --synthetic   # offline plumbing check (random walk; numbers mean nothing)
"""
import argparse
import math
import random
from datetime import date, timedelta

COST = 0.0005            # per side, ETFs (moonshot_study.COST_ETF)
FEE = 0.0095             # TQQQ / UPRO expense ratio per year
SPREAD = 0.004           # financing spread over the T-bill rate on the borrowed part
BAR = {"max_dd": 0.65}


def sma(xs, n):
    out, s = [None] * len(xs), 0.0
    for i, x in enumerate(xs):
        s += x
        if i >= n:
            s -= xs[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def leveraged(o, c, rate, lev):
    """Daily-reset `lev`x fund rebuilt from the plain fund's opens / closes: each day lev x the move, minus the fee
    and the financing of the borrowed (lev - 1) part. Returns (opens, closes), starting at 100."""
    so, sc = [100.0], [100.0]
    for j in range(1, len(c)):
        drag = (FEE + (lev - 1) * (rate[j] + SPREAD)) / 252
        so.append(sc[-1] * max(1e-9, 1 + lev * (o[j] / c[j - 1] - 1)))
        sc.append(sc[-1] * max(1e-9, 1 + lev * (c[j] / c[j - 1] - 1) - drag))
    return so, sc


def run(o, c, signal, cost=COST, late=False):
    """Daily returns of: be in the fund on day j iff signal[j-1] (the close before) - bought / sold at day j's open
    (late=True: at day j's close instead). signal[i] is True / False / None (None = no average yet = cash).
    Returns (rets, n_trades) with rets[j] for j >= 1."""
    rets, trades, inpos = [0.0], 0, False
    for j in range(1, len(c)):
        want = bool(signal[j - 1])
        if late:
            r = c[j] / c[j - 1] - 1 if inpos else 0.0
            if want != inpos:
                r = (1 + r) * (1 - cost) - 1
                trades += 1
        elif inpos and want:
            r = c[j] / c[j - 1] - 1
        elif inpos and not want:
            r = o[j] / c[j - 1] * (1 - cost) - 1
            trades += 1
        elif want:
            r = c[j] / o[j] * (1 - cost) - 1
            trades += 1
        else:
            r = 0.0
        inpos = want
        rets.append(r)
    return rets, trades


def stats(rets):
    eq, peak, dd = 1.0, 1.0, 0.0
    for r in rets:
        eq *= 1 + r
        peak = max(peak, eq)
        dd = max(dd, 1 - eq / peak)
    yrs = max(len(rets) / 252, 1e-9)
    return {"total": eq - 1, "cagr": eq ** (1 / yrs) - 1 if eq > 0 else -1.0, "mdd": dd}


def rolling(rets, n):
    out, eq = [], [1.0]
    for r in rets:
        eq.append(eq[-1] * (1 + r))
    for i in range(0, len(eq) - n):
        out.append(eq[i + n] / eq[i])
    return sorted(out)


def pct(xs, q):
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else float("nan")


def load_real(years):
    import yfinance as yf
    start = (date.today() - timedelta(days=int(years * 365.25))).isoformat()
    syms = ["QQQ", "SPY", "TQQQ", "QLD", "UPRO", "^IRX"]
    df = yf.download(syms, start=start, interval="1d", auto_adjust=True, group_by="ticker", progress=False, threads=True)
    out = {}
    for s in syms:
        d = df[s].dropna(subset=["Close"])
        out[s] = {ix.date(): (float(r["Open"]), float(r["Close"])) for ix, r in d.iterrows()}
        print(f"  {s}: {len(d)} days from {d.index[0].date()}")
    return out


def load_synth(years):
    rng, out = random.Random(11), {}
    days = [date(2026, 11, 13) - timedelta(days=k) for k in range(int(years * 365.25))][::-1]
    days = [d for d in days if d.weekday() < 5]
    for s, (mu, sd) in {"QQQ": (0.0005, 0.016), "SPY": (0.0004, 0.012)}.items():
        px, ser = 100.0, {}
        for d in days:
            op = px * (1 + rng.gauss(0, sd / 3))
            px = op * (1 + rng.gauss(mu, sd))
            ser[d] = (op, px)
        out[s] = ser
    out["^IRX"] = {d: (2.0, 2.0) for d in days}
    for s, base, lev in (("TQQQ", "QQQ", 3), ("QLD", "QQQ", 2), ("UPRO", "SPY", 3)):
        ds = [d for d in days if d >= date(2010, 2, 11)]
        o, c = leveraged([out[base][d][0] for d in ds], [out[base][d][1] for d in ds], [0.02] * len(ds), lev)
        out[s] = {d: (o[k], c[k]) for k, d in enumerate(ds)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=float, default=28)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    print(f"=== TQQQ-above-its-200-day-average study: cost {COST:.2%}/side, signal at the close, trade at the next open ===")
    data = load_synth(a.years) if a.synthetic else load_real(a.years)
    if a.synthetic:
        print("*** SYNTHETIC DATA: tests the code only ***")
    days = sorted(data["QQQ"])
    irx, last = data.get("^IRX", {}), 0.02
    rate = []
    for d in days:                                       # T-bill rate, % a year; carried forward over gaps
        if d in irx and irx[d][1] == irx[d][1]:
            last = max(0.0, irx[d][1] / 100)
        rate.append(last)
    qo, qc = [data["QQQ"][d][0] for d in days], [data["QQQ"][d][1] for d in days]
    s3o, s3c = leveraged(qo, qc, rate, 3)
    s2o, s2c = leveraged(qo, qc, rate, 2)

    print("\n=== 1) Is the rebuilt 3x fund honest? Rebuilt vs the REAL fund on the days both exist (buy and hold) ===")
    for real, (so, sc) in (("TQQQ", (s3o, s3c)), ("QLD", (s2o, s2c))):
        ds = [d for d in days if d in data[real]]
        if len(ds) < 300:
            continue
        i0, i1 = days.index(ds[0]), days.index(ds[-1])
        yrs = (i1 - i0) / 252
        r_real = (data[real][ds[-1]][1] / data[real][ds[0]][1]) ** (1 / yrs) - 1
        r_syn = (sc[i1] / sc[i0]) ** (1 / yrs) - 1
        print(f"  {real}: real {r_real:+.1%}/yr   rebuilt {r_syn:+.1%}/yr   ({ds[0]} .. {ds[-1]})")

    def above(c, n):
        m = sma(c, n)
        return [None if m[i] is None else c[i] > m[i] for i in range(len(c))]

    S = [
        ("hold QQQ", qo, qc, [True] * len(days), {}),
        ("hold 3x", s3o, s3c, [True] * len(days), {}),
        ("3x own200  (LIVE CANDIDATE)", s3o, s3c, above(s3c, 200), {}),
        ("3x own100", s3o, s3c, above(s3c, 100), {}),
        ("3x own150", s3o, s3c, above(s3c, 150), {}),
        ("3x own250", s3o, s3c, above(s3c, 250), {}),
        ("3x qqq200", s3o, s3c, above(qc, 200), {}),
        ("3x own200 one day late", s3o, s3c, above(s3c, 200), {"late": True}),
        ("3x own200 3x costs", s3o, s3c, above(s3c, 200), {"cost": 3 * COST}),
        ("2x own200", s2o, s2c, above(s2c, 200), {}),
        ("QQQ own200 (no leverage)", qo, qc, above(qc, 200), {}),
    ]
    first = 260                                           # every average is ready
    cuts = [first]
    for y, m_, d_ in ((2010, 2, 11), (2018, 7, 1)):
        k = next((i for i, d in enumerate(days) if d >= date(y, m_, d_)), None)
        if k is not None and k > first + 250 and k < len(days) - 250:
            cuts.append(k)
    cuts.append(len(days))
    eras = [(cuts[k], cuts[k + 1]) for k in range(len(cuts) - 1)]
    print(f"\nspan {days[first]} .. {days[-1]}; eras: " + " | ".join(f"{days[a_]} .. {days[b_ - 1]}" for a_, b_ in eras))

    print("\n=== 2) REBUILT 3x Nasdaq fund from QQQ, 2000 -> today (each era from a flat start) ===")
    hdr = f"{'rule':<30} {'full CAGR':>9} {'maxDD':>6} {'trd/yr':>6} | " + " | ".join(
        f"{str(days[a_].year) + '-' + str(days[b_ - 1].year):>9} {'DD':>4}" for a_, b_ in eras) + " | $1,000 -> full"
    print(hdr)
    print("-" * len(hdr))
    R = {}
    for name, o, c, sig, kw in S:
        def seg(a_, b_):
            rets, n = run(o[a_ - 1:b_], c[a_ - 1:b_], sig[a_ - 1:b_], **kw)
            return rets[1:], n
        rets, n = seg(first, len(days))
        st = stats(rets)
        R[name] = {"rets": rets, "st": st, "eras": []}
        cells = []
        for a_, b_ in eras:
            se = stats(seg(a_, b_)[0])
            R[name]["eras"].append(se)
            cells.append(f"{se['cagr']:>+9.1%} {se['mdd']:>4.0%}")
        print(f"{name:<30} {st['cagr']:>+9.1%} {st['mdd']:>6.0%} {n / (len(rets) / 252):>6.1f} | " + " | ".join(cells)
              + f" | {1000 * (1 + st['total']):>12,.0f}")

    print("\n=== 3) Per-year returns (rebuilt fund) ===")
    yrs = sorted({d.year for d in days[first:]})
    for chunk in (yrs[:14], yrs[14:]):
        if not chunk:
            continue
        print(f"{'rule':<30} " + " ".join(f"{y % 100:>5}" for y in chunk))
        for name in ("hold QQQ", "hold 3x", "3x own200  (LIVE CANDIDATE)", "3x qqq200", "2x own200"):
            by = {}
            for d, r in zip(days[first:], R[name]["rets"]):
                by[d.year] = by.get(d.year, 1.0) * (1 + r)
            print(f"{name:<30} " + " ".join(f"{by[y] - 1:>+5.0%}" for y in chunk))

    print("\n=== 4) Start any day with $1,000 (windows overlap) ===")
    for n, lbl in ((126, "6 months"), (252, "12 months")):
        print(f"--- after {lbl} ---")
        for name in ("hold QQQ", "hold 3x", "3x own200  (LIVE CANDIDATE)", "3x qqq200", "2x own200"):
            r = rolling(R[name]["rets"], n)
            print(f"{name:<30} bad {1000 * pct(r, 0.10):>6,.0f}  median {1000 * pct(r, 0.50):>6,.0f}  good "
                  f"{1000 * pct(r, 0.90):>6,.0f}  worst {1000 * r[0]:>6,.0f}  best {1000 * r[-1]:>6,.0f}  "
                  f"lost half+ {sum(x <= 0.5 for x in r) / len(r):>4.0%}  2x {sum(x >= 2 for x in r) / len(r):>4.0%}")

    print("\n=== 5) The REAL funds, same rules (real opens / closes; their whole listed life) ===")
    for sym in ("TQQQ", "QLD", "UPRO"):
        ds = sorted(data.get(sym, {}))
        if len(ds) < 520:
            continue
        o, c = [data[sym][d][0] for d in ds], [data[sym][d][1] for d in ds]
        mid = 260 + (len(ds) - 260) // 2
        for n in (150, 200, 250):
            sig = above(c, n)
            full = stats(run(o[259:], c[259:], sig[259:])[0][1:])
            h1 = stats(run(o[259:mid], c[259:mid], sig[259:mid])[0][1:])
            h2 = stats(run(o[mid - 1:], c[mid - 1:], sig[mid - 1:])[0][1:])
            print(f"  {sym} above its {n}-day avg: {full['cagr']:+.1%}/yr, maxDD {full['mdd']:.0%} | older half "
                  f"{h1['cagr']:+.1%} / {h1['mdd']:.0%} | newer half {h2['cagr']:+.1%} / {h2['mdd']:.0%}   ({ds[259]} .. {ds[-1]})")
        hold = stats([c[j] / c[j - 1] - 1 for j in range(260, len(c))])
        print(f"  {sym} buy and hold: {hold['cagr']:+.1%}/yr, maxDD {hold['mdd']:.0%}")
        m = sma(c, 200)
        print(f"  {sym} today: close {c[-1]:.2f}, 200-day avg {m[-1]:.2f} -> {'ABOVE (hold)' if c[-1] > m[-1] else 'BELOW (cash)'}")

    print("\n=== 6) VERDICT against the bar written before the run ===")
    cand, hq = R["3x own200  (LIVE CANDIDATE)"], R["hold QQQ"]
    e0, q0 = cand["eras"][0], hq["eras"][0]
    a_ok, b_ok, c_ok = e0["total"] >= 0, e0["cagr"] > q0["cagr"], e0["mdd"] <= BAR["max_dd"]
    nb = all(R[k]["eras"][j]["cagr"] > 0 for k in ("3x own150", "3x own250") for j in range(1, len(eras)))
    nb0 = all(R[k]["eras"][0]["cagr"] >= 0 for k in ("3x own150", "3x own250"))
    print(f"  first era ({days[eras[0][0]]} .. {days[eras[0][1] - 1]}): rule {e0['cagr']:+.1%}/yr, maxDD {e0['mdd']:.0%}; "
          f"hold QQQ {q0['cagr']:+.1%}/yr, maxDD {q0['mdd']:.0%}")
    print(f"  (a) did not lose money: {'PASS' if a_ok else 'FAIL'}   (b) beat holding QQQ: {'PASS' if b_ok else 'FAIL'}   "
          f"(c) never fell more than {BAR['max_dd']:.0%}: {'PASS' if c_ok else 'FAIL'}")
    print(f"  neighbours (150 / 250-day) positive in the later eras: {'PASS' if nb else 'FAIL'}; not losing in the first era: "
          f"{'PASS' if nb0 else 'FAIL'}")
    print(f"  => {'ALL PASS' if a_ok and b_ok and c_ok and nb and nb0 else 'NOT ALL PASS'}")
    print("\nCaveats: the rebuilt fund is a model (real 3x funds also lose a little to swaps and tracking - see part 1); "
          "daily bars; one index (the Nasdaq-100 was the best big index of the last 15 years - its future is not promised); "
          "windows overlap.")
    return R


if __name__ == "__main__":
    main()
