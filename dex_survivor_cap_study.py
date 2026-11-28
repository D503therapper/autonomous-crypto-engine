"""DEX survivor entry: refuse a buy when the entry hour has jumped too much and / or sellers outnumber buyers?
(2026-11-28, after COGE 1h +84% -> -$17 and PUMPCHAN 1h +83%, buys/sells 216/395 -> 0.58x in 23 minutes.)

Scanner log data/dex/scan/*.csv.gz (hourly rows per pool, $50k+ liquidity; loader and exit simulation from
dex_entry_grid_study: 80% out at 5x, after 3x a 40% drop sells all, 7 days, liquidity pull / -98% = rug, fills at the
lower of two looks, feed glitches dropped, a pool the scanner stopped tracking counts as lost).  No scam screen and no
experiment-20 LP-flag exit can be replayed (the log has no RugCheck data) - the same for every variant.
Survivor rule = config.DEX["entry"]["survivor"]: 2-6 days old, $250k+ liquidity grown 20%+ in 24h, price up on the day
and within 30% of the high seen.  CURRENT = the first hour a pool meets it.  A VARIANT buys at the first hour the pool
meets the rule AND the filter (so a filtered coin can still be bought a later, calmer hour - what the engine would
do); "skip" columns show the coins never bought at all.  Halves by entry time of the CURRENT rule's entries (median).
A variant must beat CURRENT per $1 in total and in both halves.   python dex_survivor_cap_study.py"""
import os
from datetime import datetime

import config
import dex_entry_grid_study as G

ROOT = os.path.dirname(os.path.abspath(__file__))
V = config.DEX["entry"]["survivor"]
F = G.F


def entries(data, tmax, filt=None, follow=3):
    """-> {pool key: (t, sym, row, x)}: first hour each pool meets the survivor rule (and filt), live exit result."""
    out = {}
    for k, s in data.items():
        hi = 0.0
        for i, (t, r, p, l) in enumerate(s):
            hi = max(hi, p)
            age = F(r["age_h"])
            if age is None or not V["age_h"] <= age <= V["max_age_h"] or l < V["liq"] or tmax - t < follow * 86400:
                continue
            old = [x for x in s[:i] if 24 * 3600 <= t - x[0] <= 30 * 3600]
            if not old or l < old[-1][3] * V["liq_grow"] or p < old[-1][2] or p < hi * V["from_high"]:
                continue
            if filt and not filt(r):
                continue
            path = [(tt, pp, ll) for tt, _, pp, ll in s[i + 1:] if tt - t <= 7 * 86400]
            horizon = min(t + 7 * 86400, tmax)
            if not path or horizon - path[-1][0] > 24 * 3600:
                path = path + [(horizon, 0.0, 0.0)]
            x = G.sim(path, p, l)
            if x is not None:
                out[k] = (t, r["sym"], r, min(x, 100.0))
            break
    return out


def h(r, k):
    return F(r.get(k))


def cap(k, m):
    return lambda r: h(r, k) is None or h(r, k) <= m


def ratio(q, b="b1", s="s1"):
    return lambda r: (h(r, b) or 0) >= q * (h(r, s) or 0)


def both(*fs):
    return lambda r: all(f(r) for f in fs)


VARIANTS = [("1h <= +25%", cap("h1", 0.25)), ("1h <= +40%", cap("h1", 0.40)), ("1h <= +60%", cap("h1", 0.60)),
            ("1h <= +100%", cap("h1", 1.0)),
            ("6h <= +50%", cap("h6", 0.5)), ("6h <= +100%", cap("h6", 1.0)), ("6h <= +200%", cap("h6", 2.0)),
            ("1h buys >= sells", ratio(1.0)), ("1h buys >= 0.8x sells", ratio(0.8)), ("1h buys >= 1.2x sells", ratio(1.2)),
            ("24h buys >= sells", ratio(1.0, "b24", "s24")),
            ("1h <= +40% and buys >= sells", both(cap("h1", 0.40), ratio(1.0))),
            ("1h <= +60% and buys >= sells", both(cap("h1", 0.60), ratio(1.0))),
            ("1h <= +60% and buys >= 0.8x sells", both(cap("h1", 0.60), ratio(0.8))),
            ("1h <= +40% and 6h <= +100%", both(cap("h1", 0.40), cap("h6", 1.0))),
            ("1h <= +60% and 6h <= +200%", both(cap("h1", 0.60), cap("h6", 2.0))),
            ("not (1h > +60% and buys < sells)", lambda r: cap("h1", 0.60)(r) or ratio(1.0)(r))]


def mean(v):
    return sum(v) / len(v) if v else 0.0


def main():
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        data = G.load()
    finally:
        os.chdir(cwd)
    tmin = min(s[0][0] for s in data.values()); tmax = max(s[-1][0] for s in data.values())
    base = entries(data, tmax)
    ts = sorted(e[0] for e in base.values())
    mid = ts[len(ts) // 2]
    D = lambda t: f"{datetime.utcfromtimestamp(t):%m-%d}"
    L = []
    w = L.append
    w("DEX survivor entry: cap the entry hour's jump / require buyers >= sellers?  (dex_survivor_cap_study.py)")
    w(f"scanner log {D(tmin)} .. {D(tmax)}, {len(data)} pools; survivor-rule entries with 3+ days of follow-up: {len(base)}; "
      f"halves split at {D(mid)}")
    w("per $1 bet, live exit (80% at 5x, 3x then -40%, 7 days, rug = lost), 0.3%/side; no scam screen in the replay")
    w("")

    def stats(E):
        a = [e[3] - 1 for e in E.values() if e[0] < mid]; b = [e[3] - 1 for e in E.values() if e[0] >= mid]
        return a, b

    a0, b0 = stats(base)
    m0, ma0, mb0 = mean(a0 + b0), mean(a0), mean(b0)
    hdr = f"{'rule':36}{'n':>4}{'sum $':>8}{'per $1':>8}{'older':>8}{'n':>4}{'newer':>8}{'n':>4}{'lost80%+':>9}{'2x+':>4}{'skip':>5}{'later':>6}  verdict"
    w(hdr)

    def line(name, E):
        a, b = stats(E)
        al = a + b
        skip = sum(1 for k in base if k not in E)
        later = sum(1 for k in E if k in base and E[k][0] != base[k][0])
        ok = (mean(al) > m0 and mean(a) > ma0 and mean(b) > mb0 and sum(al) > sum(a0 + b0))
        thin = len(a) < 15 or len(b) < 15
        v = "CURRENT" if E is base else ("beats current in both halves" + (" (thin)" if thin else "") if ok else "no")
        w(f"{name:36}{len(al):4d}{sum(al):+8.2f}{mean(al):+8.3f}{mean(a):+8.3f}{len(a):4d}{mean(b):+8.3f}{len(b):4d}"
          f"{sum(x <= -0.8 for x in al):9d}{sum(x >= 1 for x in al):4d}{skip:5d}{later:6d}  {v}")
        return ok

    line("CURRENT (no filter)", base)
    res = {}
    for name, f in VARIANTS:
        res[name] = entries(data, tmax, f)
        line(name, res[name])
    w("")
    w("skip = current entries never bought under the variant; later = bought a later hour instead.")
    w("")
    w("Buckets of the CURRENT entries by the entry row (per $1; older / newer):")
    BK = [("1h <= 0", lambda r: (h(r, "h1") or 0) <= 0), ("1h 0..+10%", lambda r: 0 < (h(r, "h1") or 0) <= 0.1),
          ("1h +10..25%", lambda r: 0.1 < (h(r, "h1") or 0) <= 0.25), ("1h +25..60%", lambda r: 0.25 < (h(r, "h1") or 0) <= 0.6),
          ("1h > +60%", lambda r: (h(r, "h1") or 0) > 0.6),
          ("6h <= 0", lambda r: (h(r, "h6") or 0) <= 0), ("6h 0..+50%", lambda r: 0 < (h(r, "h6") or 0) <= 0.5),
          ("6h +50..100%", lambda r: 0.5 < (h(r, "h6") or 0) <= 1.0), ("6h > +100%", lambda r: (h(r, "h6") or 0) > 1.0),
          ("1h buys < 0.8x sells", lambda r: not ratio(0.8)(r)), ("1h buys 0.8-1x sells", lambda r: ratio(0.8)(r) and not ratio(1.0)(r)),
          ("1h buys 1-1.5x sells", lambda r: ratio(1.0)(r) and not ratio(1.5)(r)), ("1h buys >= 1.5x sells", ratio(1.5))]
    for name, f in BK:
        a = [e[3] - 1 for e in base.values() if f(e[2]) and e[0] < mid]
        b = [e[3] - 1 for e in base.values() if f(e[2]) and e[0] >= mid]
        al = a + b
        w(f"  {name:24} n {len(al):3d}  per $1 {mean(al):+.3f}  ({mean(a):+.3f} n {len(a)} / {mean(b):+.3f} n {len(b)})"
          f"  lost 80%+ {sum(x <= -0.8 for x in al)}  2x+ {sum(x >= 1 for x in al)}")
    w("")
    w("Winners (current result >= +50%) each variant gives up or changes (current -> variant per $1):")
    for name, _ in VARIANTS:
        E = res[name]
        lost = [(e[1], e[3] - 1, (E[k][3] - 1) if k in E else None) for k, e in base.items()
                if e[3] - 1 >= 0.5 and (k not in E or E[k][0] != e[0])]
        lost.sort(key=lambda x: -x[1])
        w(f"  {name:36} " + (", ".join(f"{s} {x:+.2f} -> {'skip' if y is None else f'{y:+.2f}'}" for s, x, y in lost[:8]) or "none"))
    w("")
    w("CURRENT entries with 1h > +40% or 1h buys < sells (time, coin, 1h, 6h, buys/sells, result per $1):")
    for k, e in sorted(base.items(), key=lambda kv: kv[1][0]):
        r = e[2]
        if (h(r, "h1") or 0) > 0.4 or not ratio(1.0)(r):
            w(f"  {datetime.utcfromtimestamp(e[0]):%m-%d %H:00} {e[1][:12]:12} {k[0][:8]:8} 1h {(h(r, 'h1') or 0):+5.0%} 6h {(h(r, 'h6') or 0):+5.0%} "
              f"{int(h(r, 'b1') or 0):5d}/{int(h(r, 's1') or 0):<5d} {e[3] - 1:+.2f}")
    txt = "\n".join(L)
    print(txt)
    with open(f"{ROOT}/results/dex_survivor_cap_study.txt", "w") as fh:
        fh.write(txt + "\n")


if __name__ == "__main__":
    main()
