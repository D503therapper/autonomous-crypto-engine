"""Lottery odds of the fresh-pump (momentum) DEX entry (experiment 14, owner 10-18 "go to the moon").
Scanner snapshots data/dex/scan/*.csv.gz: every pool's FIRST reading that meets the live momentum entry
(config.DEX entry + prefilter floors), then its price path for 7 days from later snapshots.
Prints how many reached 2x / 3x / 5x / 10x, and the result of holding vs 'sell all at Nx'."""
import csv, glob, gzip
from collections import defaultdict
from datetime import datetime
import config

E, S = config.DEX["entry"], config.DEX["screen"]
C = 0.003                                             # ~0.3%/side swap cost + impact


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def ok(r):
    liq, age, v24, h1, h6 = f(r["liq"]), f(r["age_h"]), f(r["vol24"]), f(r["h1"]), f(r["h6"])
    b1, s1 = f(r["b1"]) or 0, f(r["s1"]) or 0
    return (liq and liq >= S["min_liq"] and age is not None and age >= S["min_age_h"] and v24 and v24 >= S["min_vol24"]
            and h1 is not None and h6 is not None and E["h1"] <= h1 < E.get("h1_max", 9e9) and h6 >= E["h6"]
            and b1 >= max(1, s1 * E["buy_ratio"]))


paths, entry = defaultdict(list), {}
for fn in sorted(glob.glob("data/dex/scan/*.csv.gz")):
    for r in csv.DictReader(gzip.open(fn, "rt")):
        k, p = (r["chain"], r["addr"].lower()), f(r["price"])
        if not p or p <= 0:
            continue
        t = datetime.strptime(r["time"], "%Y-%m-%d %H:%M").timestamp()
        if k in entry:
            paths[k].append((t, p, f(r["liq"]) or 0))
        elif ok(r):
            entry[k] = (t, p, r["sym"], f(r["liq"]))
last_t = max(t for v in paths.values() for t, _, _ in v) if paths else 0
R = []
for k, (t0, p0, sym, l0) in entry.items():
    if last_t - t0 < 3 * 86400:                           # need 3+ days of follow-up
        continue
    pth = [(t, p, l) for t, p, l in paths[k] if t - t0 <= 7 * 86400]
    rug = next((i for i, (_, p, l) in enumerate(pth) if l < 0.5 * l0 * (p / p0) ** 0.5 or p < p0 * 0.02), None)
    live = pth[:rug + 1] if rug is not None else pth
    # a peak counts only if it held for 2 snapshots in a row with real liquidity behind it (feeds glitch to 1e6x)
    ok2 = [min(a[1], b[1]) for a, b in zip(live, live[1:]) if min(a[2], b[2]) >= 0.3 * l0 and max(a[1], b[1]) <= 50 * min(a[1], b[1])]
    peak = max(ok2 + [p0]) / p0
    if peak > 1000:                                       # still implausible in 7 days: bad data, drop the pool
        continue
    end = min(live[-1][1] / p0, peak) if live and rug is None else (0.0 if rug is not None else 1.0)
    R.append(dict(sym=sym, t0=t0, peak=peak, end=end, path=[p / p0 for _, p, _ in live], rug=rug is not None))
R.sort(key=lambda r: r["t0"])
n = len(R)
print(f"pools that met the fresh-pump entry with 3+ days of follow-up: {n}")
for x in (1.5, 2, 3, 5, 10, 25):
    print(f"  peaked >= {x:>4}x within 7d: {sum(r['peak'] >= x for r in R):4d}  ({sum(r['peak'] >= x for r in R) / max(n, 1):.1%})")
print(f"  rugged / dumped 98%: {sum(r['rug'] for r in R)}")


def sell_at(r, x):
    return x * (1 - C) ** 2 - 1 if r["peak"] >= x else r["end"] * (1 - C) ** 2 - 1


def half(rs, fn):
    return sum(fn(r) for r in rs) / max(len(rs), 1)


h = n // 2
for name, fn in [("hold 7d", lambda r: r["end"] * (1 - C) ** 2 - 1)] + [(f"sell all at {x}x", lambda r, x=x: sell_at(r, x)) for x in (2, 3, 5, 10)]:
    print(f"  {name:15} mean per $1: all {half(R, fn):+.3f}   first half {half(R[:h], fn):+.3f}   second half {half(R[h:], fn):+.3f}")


def part(r, x, q):                                       # sell q at x (if reached), hold the rest 7 days
    rest = r["end"] * (1 - C) ** 2
    return (q * x * (1 - C) ** 2 + (1 - q) * rest - 1) if r["peak"] >= x else rest - 1


for x, q in ((3, 0.5), (5, 0.5), (5, 0.75), (5, 0.8), (3, 0.34), (4, 0.8)):
    fn = lambda r, x=x, q=q: part(r, x, q)
    print(f"  sell {q:.0%} at {x}x, hold rest: all {half(R, fn):+.3f}   first half {half(R[:h], fn):+.3f}   second half {half(R[h:], fn):+.3f}")
print("  biggest peaks:", ", ".join(f"{r['sym']} {r['peak']:.1f}x" for r in sorted(R, key=lambda r: -r['peak'])[:10]))
