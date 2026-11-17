"""11/17 UNDERDOG EDGE - (6) THE 🔍 COLLEGE FOOTBALL GAP PLAY (paused 11/13): does ANY honest version earn it back?
The 11/14 football replay board's rows (football_1114/funnel5.py - every college football board day 2018-26 at the
close on the 11/14 code, the raw ratings read + the books' no-vig number on every dog; ~/.cache/d503_fb1114/rows).
A version has to clear the bar: up in BOTH halves (2018-21 / 2022-26), most seasons, a placebo against every college
dog +100..+350, a point worse than the close.
Usage: python results/studies/dogs_1117/s6_gap_ncaaf.py > results/studies/dogs_1117/s6_gap_ncaaf.out"""
import glob
import json
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dlib as D  # noqa: E402

rows = []
for f in sorted(glob.glob(os.path.expanduser("~/.cache/d503_fb1114/rows/f*.jsonl"))):
    for ln in open(f):
        if ln.strip():
            r = json.loads(ln)
            if r["league"] == "ncaaf" and r["market"] == "ml" and 100 <= r["odds"] <= 350 and r.get("result") in ("won", "lost") \
                    and r.get("raw_own") is not None and r.get("p_market") is not None:
                r["gap"] = r["raw_own"] - r["p_market"]
                rows.append(r)
seen, dogs = set(), []
for r in rows:
    if (r["gid"], r["side"]) not in seen:
        seen.add((r["gid"], r["side"]))
        dogs.append(r)


def fseason(d):
    y, m = int(d[:4]), int(d[5:7])
    return y if m >= 7 else y - 1


def fl(r, pts=0.0):
    return (D.worse_dec(r, pts) - 1) if r["result"] == "won" else -1.0


def cell(name, rs, pool=None):
    if not rs:
        print(f"  {name:66s} n    0")
        return
    tr = [r for r in rs if fseason(r["date"]) <= 2021]
    he = [r for r in rs if fseason(r["date"]) >= 2022]
    seas = defaultdict(float)
    for r in rs:
        seas[fseason(r["date"])] += fl(r)
    f = lambda x: (100 * sum(fl(r) for r in x) / len(x)) if x else 0.0   # noqa: E731
    w = sum(r["result"] == "won" for r in rs)
    need = 100 * sum(1 / r["dec"] for r in rs) / len(rs)
    pb = ""
    if pool and len(rs) >= 10 and len(pool) > len(rs):
        rnd = random.Random(1117)
        v = [fl(r) for r in pool]
        mine = sum(fl(r) for r in rs) / len(rs)
        pb = f" | placebo {sum(1 for _ in range(2000) if sum(rnd.sample(v, len(rs))) / len(rs) >= mine)}"
    print(f"  {name:66s} n {len(rs):4d} {w:3d}-{len(rs) - w:<4d} {100 * w / len(rs):4.1f}% (needs {need:4.1f}) {f(rs):+6.1f}%"
          f" | 2018-21 {f(tr):+6.1f}% ({len(tr):3d}) | 2022-26 {f(he):+6.1f}% ({len(he):3d}) | up {sum(v > 0 for v in seas.values())}/{len(seas)}"
          f" | 1pt worse {100 * sum(fl(r, 1.0) for r in rs) / len(rs):+6.1f}%{pb}"
          f" | " + " ".join(f"{s % 100}:{v:+.0f}" for s, v in sorted(seas.items())))


print(f"college football dogs +100..+350 with a raw read and a market, {min(r['date'] for r in dogs)} -> {max(r['date'] for r in dogs)}: {len(dogs)}")
cell("every college dog (the vig)", dogs)
road = lambda r: not r["home"] and not r.get("neutral")   # noqa: E731
home = lambda r: r["home"] and not r.get("neutral")       # noqa: E731
study = lambda r: (r.get("dog_score") or 0) - (r.get("dog_base") or 0)   # noqa: E731
print("-- THE RAW GAP (the ratings read minus the books' no-vig number), every band")
for lo, hi in ((-1, 0), (0, .05), (.05, .10), (.10, .15), (.15, .20), (.20, .25), (.25, .35), (.35, 2)):
    cell(f"gap {lo:+.2f}..{hi:+.2f}", [r for r in dogs if lo <= r["gap"] < hi], dogs)
g15 = [r for r in dogs if r["gap"] >= .15]
print("-- THE RULE'S VERSIONS (15+)")
cell("15+ (the 10/24 rule)", g15, dogs)
cell("15+ home dog", [r for r in g15 if home(r)], dogs)
cell("15+ ROAD dog (the 11/11 rule)", [r for r in g15 if road(r)], dogs)
cell("15+ neutral", [r for r in g15 if r.get("neutral")], dogs)
cell("15..35 road (the rule as it ran 11/12)", [r for r in g15 if road(r) and r["gap"] < .35], dogs)
cell("15..25 road", [r for r in g15 if road(r) and r["gap"] < .25], dogs)
cell("25+ road", [r for r in g15 if road(r) and r["gap"] >= .25], dogs)
for b in D.BANDS:
    cell(f"15+ {b}", [r for r in g15 if D.band(r) == b], dogs)
    cell(f"15+ road {b}", [r for r in g15 if road(r) and D.band(r) == b], dogs)
print("-- NEW HONEST VERSIONS: the gap AND the rest of the engine agreeing")
cell("15+ AND the studies beat the price (weighed_dog_beats)", [r for r in g15 if r.get("wdb")], dogs)
cell("15+ road AND the studies beat the price", [r for r in g15 if road(r) and r.get("wdb")], dogs)
cell("15+ AND NOT (the studies beat the price)", [r for r in g15 if not r.get("wdb")], dogs)
cell("15+ AND a dog score of 8+ (the football Dog gate)", [r for r in g15 if (r.get("dog_score") or -99) >= 8], dogs)
cell("15+ AND the STUDY part (score - base) 2+", [r for r in g15 if study(r) >= 2], dogs)
cell("15+ AND the study part 4+", [r for r in g15 if study(r) >= 4], dogs)
cell("15+ AND the study part under 0", [r for r in g15 if study(r) < 0], dogs)
cell("15+ AND a real play (good: a named reason, no red flag)", [r for r in g15 if r.get("good")], dogs)
cell("15+ AND not fighting", [r for r in g15 if not r.get("fighting")], dogs)
cell("15+ road, the studies beat the price, +100..+250", [r for r in g15 if road(r) and r.get("wdb") and r["odds"] <= 250], dogs)
cell("15+ in Aug-Sept (the ratings lean on last year)", [r for r in g15 if r["date"][5:7] in ("08", "09")], dogs)
cell("15+ Oct on", [r for r in g15 if r["date"][5:7] in ("10", "11", "12", "01")], dogs)
cell("15+ road Oct on", [r for r in g15 if road(r) and r["date"][5:7] in ("10", "11", "12", "01")], dogs)
print("-- WITHOUT the gap: the same 'studies beat the price' dogs (is it the gap or the studies?)")
cell("gap under 15, the studies beat the price", [r for r in dogs if r["gap"] < .15 and r.get("wdb")], dogs)
cell("gap under 15, study part 4+", [r for r in dogs if r["gap"] < .15 and study(r) >= 4], dogs)
cell("any gap, study part 4+", [r for r in dogs if study(r) >= 4], dogs)
cell("any gap, study part 6 (the cap)", [r for r in dogs if study(r) >= 6], dogs)
print("-- THE BEST GAP A DAY (the rule posts every one; one a day = the biggest)")
by = defaultdict(list)
for r in g15:
    by[r["date"]].append(r)
cell("the biggest 15+ gap a day", [max(v, key=lambda r: r["gap"]) for v in by.values()], dogs)
by2 = {d: [r for r in v if road(r) and r["gap"] < .35] for d, v in by.items()}
cell("the biggest 15..35 road gap a day", [max(v, key=lambda r: r["gap"]) for v in by2.values() if v], dogs)
