"""11/17 UNDERDOG EDGE - (7) DOG SIZING by price and by read (R3 - funnel6.py, today's code, 2023-10 -> 2026-11; the
college football Dog on the long football board 2018-26). Yesterday's sizing study (sizing_1117) ran the two older
boards and found the ½u dogs pay and no size-up cell clears; this is the same question on the board today's code builds,
kind by kind: the Dog of the Day's 2u / ½u price split (hockey, football), the hockey Dog by score, the NBA ½u dogs, the
floor's sizes. A bigger size needs the bigger cell to win MORE than its siblings in both halves, a placebo under 100 of
2,000 against its own kind, and a worst stretch that does not blow out.
Usage: python results/studies/dogs_1117/s7_sizing.py > results/studies/dogs_1117/s7_sizing.out"""
import glob
import json
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dlib as D  # noqa: E402

DOGS = D.r3(dogs_only=True)
P = [r for r in DOGS if r.get("kind")]
sc = lambda r: r["dog_score"] if r.get("dog_score") is not None else -99   # noqa: E731
home = lambda r: bool(r["home"]) and not r.get("neutral")     # noqa: E731
FINE = ((100, 119), (120, 150), (151, 199), (200, 350))


def kind_block(name, rs):
    print(f"\n===== {name}: {len(rs)} plays")
    if not rs:
        return
    D.cell("every play", rs)
    D.sched("at today's units", [(r, r.get("units") or 0) for r in rs])
    for lo, hi in FINE:
        c = [r for r in rs if lo <= r["odds"] <= hi]
        D.cell(f"   +{lo}..+{hi}", c)
        if 10 <= len(c) < len(rs):
            print(f"        placebo vs its own kind: {D.placebo(c, rs)}")
    D.cell("   short +100..+150", [r for r in rs if r["odds"] <= 150])
    lng = [r for r in rs if r["odds"] > 150]
    D.cell("   long +151..+350", lng)
    if 10 <= len(lng) < len(rs):
        print(f"        placebo: the long ones as GOOD as a random set of the kind {D.placebo(lng, rs)} / as BAD {D.placebo_lo(lng, rs)}")
    D.cell("   home", [r for r in rs if home(r)])
    D.cell("   road", [r for r in rs if not home(r)])
    for u, nm in ((0.5, "flat ½u"), (1.0, "flat 1u"), (2.0, "flat 2u")):
        D.sched(f"   {nm}", [(r, u) for r in rs])
    D.sched("   2u short / ½u long", [(r, 2.0 if r["odds"] <= 150 else 0.5) for r in rs])
    D.sched("   2u short / 1u long", [(r, 2.0 if r["odds"] <= 150 else 1.0) for r in rs])
    D.sched("   1u short / ½u long", [(r, 1.0 if r["odds"] <= 150 else 0.5) for r in rs])


for lg in ("nhl", "ncaaf", "nfl", "nba"):
    rs = [r for r in P if r["kind"] == "dog" and r["league"] == lg]
    kind_block(f"THE DOG OF THE DAY - {lg}", rs)
    if lg == "nhl" and rs:
        print("   -- the hockey Dog by its score / the b2b spot (the 💎 max play = 8+ on the spot)")
        for lo, hi in ((3, 6), (6, 8), (8, 10), (10, 99)):
            D.cell(f"   score {lo}..{hi}", [r for r in rs if lo <= sc(r) < hi])
        b = [r for r in rs if r["x"].get("rested_vs_b2b")]
        D.cell("   rested vs a favorite that played last night", b)
        D.cell("      ... at 8+ (the max play)", [r for r in b if sc(r) >= 8])
        D.cell("      ... under 8", [r for r in b if sc(r) < 8])
        D.cell("   not the b2b spot", [r for r in rs if not r["x"].get("rested_vs_b2b")])
        D.cell("   not the b2b spot, 8+", [r for r in rs if not r["x"].get("rested_vs_b2b") and sc(r) >= 8])
        mx = [r for r in rs if r["x"].get("rested_vs_b2b") and sc(r) >= 8]
        print(f"        placebo: the max-play spot vs a random set of hockey Dogs: {D.placebo(mx, rs)}")
        D.sched("   the hockey Dog, the max play at 3u (as wired)", [(r, 3.0 if (r["x"].get("rested_vs_b2b") and sc(r) >= 8) else (2.0 if r["odds"] <= 150 else 0.5)) for r in rs])
        D.sched("   the hockey Dog, no max play", [(r, 2.0 if r["odds"] <= 150 else 0.5) for r in rs])
        print("   -- thin (own read under 3c over the price) or not")
        D.cell("   thin", [r for r in rs if r.get("thin")])
        D.cell("   not thin", [r for r in rs if not r.get("thin")])
kind_block("THE FLOOR - hockey", [r for r in P if r["kind"] == "floor" and r["league"] == "nhl"])
fl = [r for r in P if r["kind"] == "floor" and r["league"] == "nhl"]
if fl:
    print("   -- the hockey floor dog by its score")
    for lo, hi in ((-99, 0), (0, 2), (2, 4), (4, 6), (6, 99)):
        D.cell(f"   score {lo}..{hi}", [r for r in fl if lo <= sc(r) < hi])
    hi4 = [r for r in fl if sc(r) >= 4]
    print(f"        placebo: the floor's score-4+ dogs vs a random set of the hockey floor: {D.placebo(hi4, fl)}")
    D.sched("   the hockey floor: ½u, 1u at a score of 4+", [(r, 1.0 if sc(r) >= 4 else 0.5) for r in fl])
kind_block("THE FLOOR - every other sport", [r for r in P if r["kind"] == "floor" and r["league"] != "nhl"])
kind_block("THE NBA FLOOR", [r for r in P if r["kind"] == "nbafloor"])
nf = [r for r in P if r["kind"] == "nbafloor"]
if nf:
    for lo, hi in ((0, 2), (2, 4), (4, 99)):
        D.cell(f"   NBA floor score {lo}..{hi}", [r for r in nf if lo <= sc(r) < hi])
kind_block("THE RUNNER-UP DOG PLAY (hockey / NFL)", [r for r in P if r["kind"] == "dogplay"])
kind_block("COLLEGE HOOPS: the dog slot (3 seasons on today's code)", [r for r in P if r["kind"] == "ncaabplay"])
kind_block("COLLEGE HOOPS: the 🔍 gap play", [r for r in P if r["kind"] == "gap"])
print("\n===== EVERY POSTED DOG, the board's dog money by size")
for u in sorted({r.get("units") for r in P if r.get("units")}):
    rs = [r for r in P if r.get("units") == u]
    D.cell(f"posted at {u:g}u", rs)
    D.sched(f"   at {u:g}u", [(r, u) for r in rs])
D.sched("ALL at today's units", [(r, r.get("units") or 0) for r in P])
D.sched("ALL: every ½u dog at 1u", [(r, max(1.0, r.get("units") or 0)) for r in P if r.get("units")])
D.sched("ALL: flat 1u", [(r, 1.0) for r in P if r.get("units")])

print("\n===== THE COLLEGE FOOTBALL DOG OF THE DAY ON THE LONG BOARD (football_1114 rows, 2018-26, 7 seasons with a board)")
rows = []
for f in sorted(glob.glob(os.path.expanduser("~/.cache/d503_fb1114/rows/f*.jsonl"))):
    for ln in open(f):
        if ln.strip():
            r = json.loads(ln)
            if r["market"] == "ml" and 100 <= r["odds"] <= 350 and r.get("result") in ("won", "lost"):
                rows.append(r)


def fs(d):
    y, m = int(d[:4]), int(d[5:7])
    return y if m >= 7 else y - 1


fl1 = lambda r, pts=0.0: (1 / min(.99, 1 / r["dec"] + pts / 100) - 1) if r["result"] == "won" else -1.0   # noqa: E731


def fcell(name, rs, pool=None, lo=False):
    if not rs:
        print(f"  {name:58s} n    0")
        return
    tr = [r for r in rs if fs(r["date"]) <= 2021]
    he = [r for r in rs if fs(r["date"]) >= 2022]
    f = lambda x: 100 * sum(map(fl1, x)) / len(x) if x else 0.0   # noqa: E731
    seas = defaultdict(float)
    for r in rs:
        seas[fs(r["date"])] += fl1(r)
    w = sum(r["result"] == "won" for r in rs)
    need = 100 * sum(1 / r["dec"] for r in rs) / len(rs)
    pb = ""
    if pool and 10 <= len(rs) < len(pool):
        rnd = random.Random(1117)
        v = [fl1(r) for r in pool]
        m = sum(map(fl1, rs)) / len(rs)
        pb = f" | placebo {sum(1 for _ in range(2000) if (sum(rnd.sample(v, len(rs))) / len(rs) <= m if lo else sum(rnd.sample(v, len(rs))) / len(rs) >= m))}"
    print(f"  {name:58s} n {len(rs):4d} {w:3d}-{len(rs) - w:<4d} {100 * w / len(rs):4.1f}% (needs {need:4.1f}) {f(rs):+6.1f}%"
          f" | 2018-21 {f(tr):+6.1f}% ({len(tr):3d}) | 2022-26 {f(he):+6.1f}% ({len(he):3d}) | up {sum(v > 0 for v in seas.values())}/{len(seas)}"
          f" | 1pt worse {100 * sum(fl1(r, 1.0) for r in rs) / len(rs):+6.1f}%{pb} | " + " ".join(f"{s % 100}:{v:+.0f}" for s, v in sorted(seas.items())))


def fsched(name, rs, uf):
    per = defaultdict(float)
    net = risk = 0.0
    h = {"t": [0.0, 0.0], "h": [0.0, 0.0]}
    for r in rs:
        u = uf(r)
        p = u * fl1(r)
        per[r["date"]] += p
        net += p
        risk += u
        k = "t" if fs(r["date"]) <= 2021 else "h"
        h[k][0] += p
        h[k][1] += u
    print(f"  {name:44s} {net:+6.1f}u on {risk:5.1f}u ({100 * net / risk if risk else 0:+5.1f}%) worst {D.worst(per):+5.1f}u"
          f" | 2018-21 {h['t'][0]:+5.1f}u/{h['t'][1]:.0f}u | 2022-26 {h['h'][0]:+5.1f}u/{h['h'][1]:.0f}u")


for lg in ("ncaaf", "nfl"):
    d = [r for r in rows if r["league"] == lg]
    dog = [r for r in d if r["kind"] == "dog"]
    gated = [r for r in d if r.get("good")]
    print(f"-- {lg}: the Dog of the Day ({len(dog)}); every gated dog ({len(gated)})")
    fcell("the Dog of the Day", dog, d)
    for lo, hi in FINE:
        fcell(f"   +{lo}..+{hi}", [r for r in dog if lo <= r["odds"] <= hi], dog)
    sh = [r for r in dog if r["odds"] <= 150]
    lg_ = [r for r in dog if r["odds"] > 150]
    fcell("   SHORT +100..+150 (2u today)", sh, dog)
    fcell("   LONG +151..+350 (½u today) - as good as a random set of its kind", lg_, dog)
    fcell("   LONG - as BAD as a random set of its kind", lg_, dog, lo=True)
    fcell("   LONG vs every dog of the sport at +151..+350", lg_, [r for r in d if r["odds"] > 150])
    fcell("   every gated dog, LONG (the Dog + the held ones) vs the gated", [r for r in gated if r["odds"] > 150], gated)
    fcell("   every gated dog, SHORT", [r for r in gated if r["odds"] <= 150], gated)
    fsched("   TODAY: 2u short / ½u long", dog, lambda r: 2.0 if r["odds"] <= 150 else 0.5)
    fsched("   2u short / 1u long", dog, lambda r: 2.0 if r["odds"] <= 150 else 1.0)
    fsched("   flat 2u", dog, lambda r: 2.0)
    fsched("   flat 1u", dog, lambda r: 1.0)
    fsched("   the long ones alone at ½u", lg_, lambda r: 0.5)
    fsched("   the long ones alone at 1u", lg_, lambda r: 1.0)
    he = [r for r in lg_ if fs(r["date"]) >= 2022]
    if he:
        import math
        w, n = sum(r["result"] == "won" for r in he), len(he)
        p = w / n
        dec = sum(r["dec"] for r in he) / n
        for z, nm in ((1.0, "one sd under"), (1.645, "the 5% end")):
            lo_ = (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)
            k = max(0.0, (lo_ * (dec - 1) - (1 - lo_)) / (dec - 1)) / 4 * 100
            print(f"      the long Dog's size the 2022-26 half can prove: {w}-{n - w} at an average {dec:.2f}, {nm} {100 * lo_:.1f}% -> {k:.1f}u")
