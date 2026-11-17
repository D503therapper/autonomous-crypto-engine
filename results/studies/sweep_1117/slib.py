"""11/17 FULL SWEEP - the shared five-check printer. A cell = [(day, row, units)] with row["dec"], row["result"] in
won / lost / push; a pool = the cell's siblings (the same kind of play), the cell included.
THE BAR (every one): 1. wins more vs the price than its siblings in BOTH halves (train / held out); 2. up in most
seasons; 3. a placebo - a random same-size draw from the pool does as well under 5% of the time (100 of 2,000);
4. the worst stretch does not blow out; 5. it holds a point worse than the close."""
import math
import random
from collections import defaultdict


def flat(r, worse=0.0):
    """flat 1u profit; worse = points of win chance the price is made worse by (0.01 = a point worse than the close)"""
    dec = r["dec"] if not worse else 1 / (1 / r["dec"] + worse)
    return (dec - 1) if r["result"] == "won" else -1.0 if r["result"] == "lost" else 0.0


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{(y + 1) % 100:02d}" if m >= 7 else f"{y - 1}-{y % 100:02d}"


def st(rs, worse=0.0):
    n = len(rs)
    w = sum(r["result"] == "won" for _, r, _ in rs)
    l = sum(r["result"] == "lost" for _, r, _ in rs)
    fl = sum(flat(r, worse) for _, r, _ in rs)
    bev = sum(1 / r["dec"] for _, r, _ in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for _, r, _ in rs)
    return dict(n=n, w=w, l=l, fl=fl, roi=100 * fl / n if n else 0.0, z=(w - bev) / math.sqrt(var) if var else 0.0)


def worst(rs, units=False):
    per = defaultdict(float)
    for d, r, u in rs:
        per[d] += flat(r) * (u if units else 1.0)
    cum = peak = w = 0.0
    for d in sorted(per):
        cum += per[d]
        peak = max(peak, cum)
        w = min(w, cum - peak)
    return w


def placebo(cell, pool, draws=2000, seed=1117):
    n = len(cell)
    if n < 10 or len(pool) <= n:
        return None
    mine = sum(flat(r) for _, r, _ in cell) / n
    rnd = random.Random(seed)
    return sum(1 for _ in range(draws) if sum(flat(r) for _, r, _ in rnd.sample(pool, n)) / n >= mine)


def five(name, cell, pool=None, half=None, live=None):
    """Print the five checks for `cell` against `pool` (its siblings incl. the cell). half(day) -> 'train' / 'held' /
    'live' (live rows are reported apart, never judged). -> dict with 'clears'."""
    half = half or (lambda d: "held" if d >= "2025-07-01" else "train")
    cell_ = [x for x in cell if half(x[0]) != "live"]
    lv = [x for x in cell if half(x[0]) == "live"]
    pool_ = [x for x in (pool or []) if half(x[0]) != "live"]
    rest = [x for x in pool_ if not any(x[1] is y[1] for y in cell_)] if pool else []
    a = st(cell_)
    t, h = st([x for x in cell_ if half(x[0]) == "train"]), st([x for x in cell_ if half(x[0]) == "held"])
    rt, rh = st([x for x in rest if half(x[0]) == "train"]), st([x for x in rest if half(x[0]) == "held"])
    seas = defaultdict(float)
    for d, r, _ in cell_:
        seas[season(d)] += flat(r)
    up = sum(v > 0 for v in seas.values())
    pb = placebo(cell_, pool_) if pool else None
    w1 = st(cell_, 0.01)
    lvs = st(lv)
    s = (f"  {name:58s} n {a['n']:4d} {a['w']:3d}-{a['l']:<3d} flat {a['roi']:+6.1f}% z {a['z']:+5.2f} | train {t['roi']:+6.1f}% ({t['n']}) "
         f"held {h['roi']:+6.1f}% ({h['n']})")
    if pool:
        s += f" | the rest: train {rt['roi']:+6.1f}% ({rt['n']}) held {rh['roi']:+6.1f}% ({rh['n']})"
    s += (f" | up {up}/{len(seas)} | placebo {pb if pb is not None else '-'}/2000 | worst {worst(cell_):+.1f}u | a point worse "
          f"{w1['roi']:+.1f}%" + (f" | live {lvs['w']}-{lvs['l']}" if lv else ""))
    ok_halves = t["n"] >= 10 and h["n"] >= 10 and t["roi"] > 0 and h["roi"] > 0 and (not pool or (t["roi"] > rt["roi"] and h["roi"] > rh["roi"]))
    ok = bool(ok_halves and up * 2 > len(seas) and (pb is not None and pb < 100) and w1["roi"] > 0)
    print(s + ("   <== CLEARS" if ok else ""))
    return dict(all=a, train=t, held=h, up=up, ns=len(seas), placebo=pb, clears=ok, worse=w1["roi"], rest_train=rt, rest_held=rh)


def loses(name, cell, pool, half=None):
    """A CUT's checks: the cell LOSES vs the price in both halves and does worse than its siblings in both; the placebo
    counts random draws doing as BADLY."""
    half = half or (lambda d: "held" if d >= "2025-07-01" else "train")
    cell_ = [x for x in cell if half(x[0]) != "live"]
    pool_ = [x for x in pool if half(x[0]) != "live"]
    rest = [x for x in pool_ if not any(x[1] is y[1] for y in cell_)]
    a = st(cell_)
    t, h = st([x for x in cell_ if half(x[0]) == "train"]), st([x for x in cell_ if half(x[0]) == "held"])
    rt, rh = st([x for x in rest if half(x[0]) == "train"]), st([x for x in rest if half(x[0]) == "held"])
    seas = defaultdict(float)
    for d, r, _ in cell_:
        seas[season(d)] += flat(r)
    dn = sum(v < 0 for v in seas.values())
    n = len(cell_)
    pb = None
    if n >= 10 and len(pool_) > n:
        mine = a["fl"] / n
        rnd = random.Random(1117)
        pb = sum(1 for _ in range(2000) if sum(flat(r) for _, r, _ in rnd.sample(pool_, n)) / n <= mine)
    ok = bool(t["n"] >= 10 and h["n"] >= 10 and t["roi"] < 0 and h["roi"] < 0 and t["roi"] < rt["roi"] and h["roi"] < rh["roi"]
              and dn * 2 > len(seas) and pb is not None and pb < 100)
    print(f"  {name:58s} n {a['n']:4d} {a['w']:3d}-{a['l']:<3d} flat {a['roi']:+6.1f}% z {a['z']:+5.2f} | train {t['roi']:+6.1f}% ({t['n']}) "
          f"held {h['roi']:+6.1f}% ({h['n']}) | the rest: train {rt['roi']:+6.1f}% ({rt['n']}) held {rh['roi']:+6.1f}% ({rh['n']}) | "
          f"down {dn}/{len(seas)} | as bad by luck {pb if pb is not None else '-'}/2000" + ("   <== A CUT CLEARS" if ok else ""))
    return dict(all=a, train=t, held=h, down=dn, ns=len(seas), placebo=pb, clears=ok)
