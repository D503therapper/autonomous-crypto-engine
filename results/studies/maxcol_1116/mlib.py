"""11/16 MAX PLAY HUNT (college) - shared loader + scoring. The 11/13 funnel4 replay rows (the college hoops board
re-built at ESPN's close every college hoops day 2018-26) through the 11/14 / 11/15 helpers, cached compact in
~/.cache/d503_maxcol1116. Read-only on the repo. TRAIN = seasons 2018-22, HELD OUT = 2023-26."""
import math
import os
import pickle
import random
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ST, "ten_1115"))
sys.path.insert(0, os.path.join(ST, "cbb_profit_1114"))
CACHE = os.path.expanduser("~/.cache/d503_maxcol1116")
os.makedirs(CACHE, exist_ok=True)
import lib as L  # noqa: E402

random.seed(1116)


def rows():
    f = os.path.join(CACHE, "cbb_rows.pkl")
    if os.path.exists(f):
        return pickle.load(open(f, "rb"))
    import clib as C
    R = L.load(L.OLD, keep_all=True)
    C.attach(R)
    K = pickle.load(open(os.path.expanduser("~/.cache/d503_studies/cbb_knowledge_b_rows.pkl"), "rb"))
    eff = {(x["id"], x["side"]): x.get("eff") for x in K}
    del K
    for r in R:
        e = r.get("eff_p") if r.get("eff_p") is not None else eff.get((r["gid"], r["side"]))
        r["eff"] = e
        r["effgap"] = None if (e is None or r["p_market"] is None) else e - r["p_market"]
    pickle.dump(R, open(f, "wb"))
    return R


def wilson_lo(w, n, z=1.0):
    """the low end of a win rate: the Wilson lower bound (z=1 -> about the 16th percentile, z=1.645 -> the 5th)."""
    if not n:
        return 0.0
    p = w / n
    d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def qkelly(p, dec):
    b = dec - 1
    return max(0.0, (p * b - (1 - p)) / b) / 4 * 100       # units, 1u = 1% of the roll


def worse(r, cents=0):
    """pnl of the row at a price `cents` worse (American)."""
    if r["pnl"] == 0:
        return 0.0
    if not r["win"]:
        return -1.0
    o = r["odds"]
    o2 = o - cents
    if o > 0 and o2 < 100:
        o2 = -100 - (100 - o2)
    return (o2 / 100) if o2 > 0 else (100 / -o2)


def rec(name, rows, pool=None, min_n=10, kelly=False):
    """W-L, ROI flat at the close, z, TRAIN / HELD, seasons up, placebo, the price-free line (won % vs priced %)."""
    n = len(rows)
    if n < min_n:
        if rows:
            print(f"   {name:56s} only {n} ({sum(r['win'] for r in rows)}-{sum(r['pnl'] < 0 for r in rows)})")
        return None
    w = sum(r["win"] for r in rows)
    l_ = sum(r["pnl"] < 0 for r in rows)
    m = sum(r["pnl"] for r in rows) / n
    sd = math.sqrt(sum((r["pnl"] - m) ** 2 for r in rows) / n) or 1
    z = m / (sd / math.sqrt(n))
    tr = [r for r in rows if r["season"] <= 2022]
    he = [r for r in rows if r["season"] >= 2023]
    f = lambda v: (100 * sum(r["pnl"] for r in v) / len(v)) if v else float("nan")
    by = defaultdict(list)
    for r in rows:
        by[r["season"]].append(r["pnl"])
    up = sum(sum(v) > 0 for v in by.values())
    pb = L.placebo(rows, pool) if pool is not None and n >= 30 else None
    need = sum(1 / r["dec"] for r in rows) / n
    hw, hl = sum(r["win"] for r in he), sum(r["pnl"] < 0 for r in he)
    s = (f"   {name:56s} {w:4d}-{l_:<4d} {100 * w / max(1, w + l_):4.1f}% (needs {100 * need:4.1f}) ROI {100 * m:+6.1f}% z {z:+4.1f}"
         f" | tr {f(tr):+6.1f}% n{len(tr):<4d}| held {hw}-{hl} {f(he):+6.1f}% | up {up}/{len(by)}"
         + (f" | pb {pb}" if pb is not None else "") + f" | -10c {100 * sum(worse(r, 10) for r in rows) / n:+.1f}%"
         + " | " + " ".join(f"{s_ % 100}:{len(v)}/{100 * sum(v) / len(v):+.0f}" for s_, v in sorted(by.items())))
    if kelly and hw + hl:
        hd = sum(r["dec"] for r in he) / len(he)
        s += (f"\n      size: held win {100 * hw / (hw + hl):.1f}% low end (1 sd) {100 * wilson_lo(hw, hw + hl):.1f}% / (5th pct) "
              f"{100 * wilson_lo(hw, hw + hl, 1.645):.1f}% at avg dec {hd:.3f} -> quarter-Kelly {qkelly(wilson_lo(hw, hw + hl), hd):.1f}u / "
              f"{qkelly(wilson_lo(hw, hw + hl, 1.645), hd):.1f}u ; all seasons low end {100 * wilson_lo(w, w + l_, 1.645):.1f}% -> "
              f"{qkelly(wilson_lo(w, w + l_, 1.645), sum(r['dec'] for r in rows) / n):.1f}u")
    print(s)
    return {"n": n, "roi": m, "z": z, "tr": f(tr), "he": f(he), "up": up, "ns": len(by), "pb": pb}
