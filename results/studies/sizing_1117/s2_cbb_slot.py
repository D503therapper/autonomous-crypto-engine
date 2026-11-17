"""11/17 - SIZING: THE COLLEGE HOOPS DOG SLOT (dog read 4+; 1u, 2u at 6+) - should the 4-6 band be 2u, the 6+ band 3u?

Rows: the 11/16 max-play hunt's cached college hoops replay rows (maxcol_1116/mlib.rows - the 11/13 funnel4 board
re-built at ESPN's close every college hoops day 2018-26; TRAIN = seasons 2018-22, HELD OUT = 2023-26).
THE SLOT AS WIRED TODAY (the 11/16 owner call - a trap / a fought side posts): every dog +100..+350 at a dog read of 4+,
both teams 4+ games, the read clears the price, never a game the board is already on, the best two reads a night.
A bigger size has to be EARNED: the band wins MORE vs the price than the band under it in BOTH halves, a random same-size
set of slot dogs does as well under 5% of the time (100 of 2,000), and the worst stretch does not blow out.
Usage: python results/studies/sizing_1117/s2_cbb_slot.py > results/studies/sizing_1117/s2_cbb_slot.out"""
import math
import os
import pickle
import random
import sys
from collections import defaultdict

CACHE = os.path.expanduser("~/.cache/d503_maxcol1116/cbb_rows.pkl")
if not os.path.exists(CACHE):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "maxcol_1116"))
    import mlib  # noqa: E402
    R = mlib.rows()
else:
    R = pickle.load(open(CACHE, "rb"))
if "--keys" in sys.argv:
    print(sorted(R[0].keys()))
    print(R[0])
    sys.exit()

DOG = [r for r in R if r.get("market", "ml") == "ml" and 100 <= r["odds"] <= 350]
A = [r for r in DOG if (r.get("dog_read") or -99) >= 4 and r["mn"] >= 4]
clears = lambda r: min(0.95, r["p_market"] + r["dog_read"] / 100) * r["dec"] - 1 > 0      # noqa: E731


def slot(cap=2, lo=4.0):
    lockg = {r["gid"] for r in R if r["kind"] in ("lock", "play", "dogplay")}
    pool = defaultdict(list)
    for r in A:
        if r["dog_read"] < lo or r["gid"] in lockg or r["kind"] in ("stackplay", "floor") or not clears(r):
            continue
        pool[r["date"]].append(r)
    out = []
    for d, v in pool.items():
        seen = set()
        for r in sorted(v, key=lambda r: (-r["dog_read"], -(r.get("effgap") or 0))):
            if r["gid"] not in seen:
                seen.add(r["gid"])
                if len(seen) <= cap:
                    out.append(r)
    return sorted(out, key=lambda r: (r["date"], r["gid"]))


def st(rs):
    n = len(rs)
    if not n:
        return dict(n=0, w=0, l=0, roi=0.0, z=0.0, wp=0.0, need=0.0)
    w = sum(r["win"] for r in rs)
    l_ = sum(r["pnl"] < 0 for r in rs)
    need = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    return dict(n=n, w=w, l=l_, roi=100 * sum(r["pnl"] for r in rs) / n, z=(w - need) / math.sqrt(var), wp=100 * w / n, need=100 * need / n)


def placebo(rs, pool, draws=2000, seed=1117):
    if len(rs) < 10 or len(pool) <= len(rs):
        return None
    rnd = random.Random(seed)
    mine = sum(r["pnl"] for r in rs)
    ps = [r["pnl"] for r in pool]
    return sum(1 for _ in range(draws) if sum(rnd.sample(ps, len(rs))) >= mine)


def line(name, rs, pool=None):
    tr = [r for r in rs if r["season"] <= 2022]
    he = [r for r in rs if r["season"] >= 2023]
    a, t, h = st(rs), st(tr), st(he)
    by = defaultdict(list)
    for r in rs:
        by[r["season"]].append(r["pnl"])
    up = sum(sum(v) > 0 for v in by.values())
    pb = placebo(rs, pool) if pool is not None else None
    print(f"  {name:50s} {a['w']:3d}-{a['l']:<3d} {a['wp']:4.1f}% (needs {a['need']:4.1f}) {a['roi']:+6.1f}% z {a['z']:+4.1f}"
          f" | train {t['w']}-{t['l']} {t['roi']:+6.1f}% | held {h['w']}-{h['l']} {h['roi']:+6.1f}% | up {up}/{len(by)}"
          + (f" | placebo {pb}" if pb is not None else "")
          + " | " + " ".join(f"{s % 100}:{len(v)}/{100 * sum(v) / len(v):+.0f}" for s, v in sorted(by.items())))
    return a, t, h, up, pb


def worst(rs, uf):
    per = defaultdict(float)
    for r in rs:
        per[r["date"]] += uf(r) * r["pnl"]
    cum = peak = w = 0.0
    for d in sorted(per):
        cum += per[d]
        peak = max(peak, cum)
        w = min(w, cum - peak)
    return w


def sched(name, rs, uf):
    tr = [r for r in rs if r["season"] <= 2022]
    he = [r for r in rs if r["season"] >= 2023]
    f = lambda v: (sum(uf(r) * r["pnl"] for r in v), sum(uf(r) for r in v))   # noqa: E731
    (a, ar), (t, trr), (h, hr) = f(rs), f(tr), f(he)
    by = defaultdict(float)
    for r in rs:
        by[r["season"]] += uf(r) * r["pnl"]
    print(f"  {name:44s} ALL {a:+6.1f}u on {ar:4.0f}u ({100 * a / ar:+5.1f}%) worst {worst(rs, uf):+5.1f}u | train {t:+6.1f}u/{trr:.0f}u"
          f" | held {h:+6.1f}u/{hr:.0f}u ({100 * h / hr:+5.1f}%) worst {worst(he, uf):+5.1f}u | " + " ".join(f"{s % 100}:{v:+.1f}" for s, v in sorted(by.items())))


S = slot()
print(f"THE SLOT AS WIRED (the 11/16 call in): {len(S)} plays 2018-26, {len(S) / 8:.0f} a season")
line("the slot, every play", S, DOG)
print("-- by the dog read (the placebo = a random same-size set of SLOT plays)")
for lo, hi in ((4, 4.5), (4.5, 5), (4, 5), (5, 6), (5, 5.5), (5.5, 6), (6, 7), (7, 99), (5, 99), (6, 99), (4, 6)):
    line(f"read {lo}-{hi if hi < 99 else ''}", [r for r in S if lo <= r["dog_read"] < hi], S)
print("-- EVERY dog at the read (not just the slot's two a night; the placebo = every read-4+ dog)")
for lo, hi in ((4, 5), (5, 6), (6, 99), (5, 99)):
    line(f"every dog, read {lo}-{hi if hi < 99 else ''}", [r for r in A if lo <= r["dog_read"] < hi and clears(r)], [r for r in A if clears(r)])
print("-- the 4-6 band by the other things a size could ride on")
B = [r for r in S if r["dog_read"] < 6]
for nm, f in (("+100..+150", lambda r: r["odds"] <= 150), ("+151..+350", lambda r: r["odds"] > 150),
              ("the own read over the price", lambda r: (r.get("edge_own") or -1) > 0), ("the own read under the price", lambda r: (r.get("edge_own") or -1) <= 0),
              ("the efficiency read 15+ over the no-vig (the 🔍 twin)", lambda r: (r.get("effgap") or 0) >= 0.15),
              ("the efficiency read under 15 over", lambda r: (r.get("effgap") or 0) < 0.15),
              ("home", lambda r: r.get("where") == "home"), ("road / neutral", lambda r: r.get("where") != "home"),
              ("a trap / fought side (the 11/16 adds)", lambda r: r["trap"] or r["fighting"]), ("clean", lambda r: not (r["trap"] or r["fighting"]))):
    line("4-6: " + nm, [r for r in B if f(r)], B)
print("-- the 6+ band the same way (2u today)")
T = [r for r in S if r["dog_read"] >= 6]
for nm, f in (("+100..+150", lambda r: r["odds"] <= 150), ("+151..+350", lambda r: r["odds"] > 150),
              ("the own read over the price", lambda r: (r.get("edge_own") or -1) > 0), ("the own read under the price", lambda r: (r.get("edge_own") or -1) <= 0),
              ("the efficiency read 15+ over", lambda r: (r.get("effgap") or 0) >= 0.15), ("under 15", lambda r: (r.get("effgap") or 0) < 0.15),
              ("read 7+", lambda r: r["dog_read"] >= 7)):
    line("6+: " + nm, [r for r in T if f(r)], T)
print("-- THE SIZES (same plays)")
sched("TODAY: 1u, 2u at 6+", S, lambda r: 2.0 if r["dog_read"] >= 6 else 1.0)
sched("flat 1u", S, lambda r: 1.0)
sched("flat 2u (the 4-6 band at 2u)", S, lambda r: 2.0)
sched("1u at 4-5, 2u at 5+", S, lambda r: 2.0 if r["dog_read"] >= 5 else 1.0)
sched("½u at 4-5, 2u at 5+", S, lambda r: 2.0 if r["dog_read"] >= 5 else 0.5)
sched("1u, 3u at 6+", S, lambda r: 3.0 if r["dog_read"] >= 6 else 1.0)
sched("1u at 4-5, 2u at 5-6, 3u at 6+", S, lambda r: 3.0 if r["dog_read"] >= 6 else 2.0 if r["dog_read"] >= 5 else 1.0)
sched("2u, 3u at 6+", S, lambda r: 3.0 if r["dog_read"] >= 6 else 2.0)
print("-- the size the held-out half can prove: a quarter of Kelly on the low end (one sd / the 5% end) of the HELD win rate")
for lo, hi in ((4, 5), (5, 6), (5, 99), (6, 99), (4, 6)):
    he = [r for r in S if lo <= r["dog_read"] < hi and r["season"] >= 2023]
    n, w = len(he), sum(r["win"] for r in he)
    if not n:
        continue
    p = w / n
    d = n / sum(1 / r["dec"] for r in he)

    def wl(z):
        dd = 1 + z * z / n
        return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / dd
    qk = lambda q: max(0.0, (q * (d - 1) - (1 - q)) / (d - 1)) * 25   # noqa: E731
    print(f"  read {lo}-{hi if hi < 99 else ''}: held {w}-{n - w} {100 * p:.1f}% at avg dec {d:.3f} (needs {100 / d:.1f}%) -> low end {100 * wl(1):.1f}% = {qk(wl(1)):.1f}u, 5% end {100 * wl(1.645):.1f}% = {qk(wl(1.645)):.1f}u")

# ---------------------------------------------------------------- THE SECOND REPLAY (the 11/14 code's own run, 2023-25)
import glob  # noqa: E402
import json  # noqa: E402


def load2(src):
    out = []
    for f in sorted(glob.glob(os.path.expanduser(f"~/.cache/{src}/rows/s20*.jsonl"))):
        for ln in open(f):
            r = json.loads(ln)
            if r["market"] != "ml" or r.get("result") not in ("won", "lost", "push") or not 100 <= r["odds"] <= 350:
                continue
            y, m = int(r["date"][:4]), int(r["date"][5:7])
            r["season"] = y if m >= 7 else y - 1
            if not 2023 <= r["season"] <= 2025:
                continue
            r["win"] = r["result"] == "won"
            r["pnl"] = 0.0 if r["result"] == "push" else ((r["dec"] - 1) if r["win"] else -1.0)
            r["mn"] = min(r.get("games_in") or 0, r.get("opp_games_in") or 0)
            if (r.get("dog_read") or -99) >= 4 and r["mn"] >= 4 and min(0.95, r["p_market"] + r["dog_read"] / 100) * r["dec"] - 1 > 0:
                out.append(r)
    return out


print("-- THE TWO REPLAYS ON THE SAME SEASONS (2023-25): every dog at the read (both teams 4+ games, the read clears the price)")
for nm, src in (("the 11/13 rows", "d503_leans1113"), ("the 11/14 rows (a day of code apart)", "d503_cbb1114")):
    X = load2(src)
    print(f"  {nm}: {len(X)} dogs at a read of 4+")
    for lo, hi in ((4, 5), (5, 6), (6, 99), (5, 99)):
        line(f"   read {lo}-{hi if hi < 99 else ''}", [r for r in X if lo <= r["dog_read"] < hi], X)
print("-- the 🔍 college hoops gap play's pool (the efficiency read 15+ over the no-vig, a read of 0+, both teams 4+ games): by the read")
G = [r for r in DOG if (r.get("effgap") or 0) >= 0.15 and (r.get("dog_read") or -99) >= 0 and r["mn"] >= 4]
print(f"  dogs in the gap play's pool: {len(G)}")
for lo, hi in ((0, 4), (4, 5), (5, 6), (6, 99)):
    line(f"   gap pool, read {lo}-{hi if hi < 99 else ''}", [r for r in G if lo <= r["dog_read"] < hi], G)
