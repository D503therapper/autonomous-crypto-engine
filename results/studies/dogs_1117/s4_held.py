"""11/17 UNDERDOG EDGE - (4) ARE WE LEAVING GOOD DOGS ON THE TABLE? (R3 - funnel6.py, today's code, 2023-10 -> 2026-11;
+ the 11/14 football replay board 2018-26 for football, where R3 has two empty seasons)
A dog the engine LIKED = its dog score at / over its sport's Dog gate (hockey 6, NBA 4, NFL 8, college football 4). For
each one that never posted: WHICH RULE HELD IT (the first that applies, in the order the board checks them):
  waiting on news -> a trap price band -> the own read / the money is fighting it -> the own-read rule (dog_own_ok; in
  football that includes the honest weighed check) -> no named reason -> the board was already on that game ->
  PASSED EVERYTHING (one Dog a day; the runner-up play is one a day, hockey / NFL only; the floor fills to two)
and how each group did. Then the band just UNDER each gate.
Usage: python results/studies/dogs_1117/s4_held.py > results/studies/dogs_1117/s4_held.out"""
import glob
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dlib as D  # noqa: E402

DOGS = D.r3(dogs_only=True)
GATE = {"nhl": 6.0, "nba": 4.0, "nfl": 8.0, "ncaaf": 4.0}
sc = lambda r: r["dog_score"] if r.get("dog_score") is not None else -99   # noqa: E731
home = lambda r: bool(r["home"]) and not r.get("neutral")     # noqa: E731


def why(r):
    if r.get("waiting"):
        return "1 waiting on news"
    if r.get("trap"):
        return "2 a trap price band"
    if r.get("fighting"):
        return "3 the own read / the money fights it"
    if not r.get("dog_own_ok"):
        if r["league"] in ("nfl", "ncaaf") and not r.get("wdb"):
            return "4b football: the studies don't beat the price (the 11/14 weighed check)"
        return "4 the own-read rule (own read under the price / the market)"
    if not r.get("n_reasons2"):
        return "5 no named reason"
    if r.get("game_taken"):
        return "6 the board was already on that game"
    return "7 PASSED EVERYTHING - one Dog a day / the runner-up cap"


for lg in ("nhl", "nba", "nfl", "ncaaf"):
    d = [r for r in DOGS if r["league"] == lg]
    g = GATE[lg]
    liked = [r for r in d if sc(r) >= g]
    posted = [r for r in liked if r.get("kind")]
    held = [r for r in liked if not r.get("kind")]
    print(f"\n===== {lg}: the Dog gate is a score of {g:g}+")
    D.cell("every dog (the vig)", d)
    D.cell(f"LIKED: a dog score of {g:g}+", liked)
    print(f"        placebo vs every {lg} dog: {D.placebo(liked, d)}")
    D.cell("   ... posted (any kind)", posted)
    by = defaultdict(list)
    for r in posted:
        by[r["kind"]].append(r)
    for k, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        D.cell(f"       as {k}", rs)
    D.cell("   ... NEVER POSTED", held)
    by = defaultdict(list)
    for r in held:
        by[why(r)].append(r)
    for k in sorted(by):
        c = D.cell(f"       {k}", by[k])
        if len(by[k]) >= 15:
            print(f"            placebo vs every {lg} dog: {D.placebo(by[k], d)} | home {sum(home(r) for r in by[k])} / road {sum(not home(r) for r in by[k])}"
                  f" | +100..+150 {sum(r['odds'] <= 150 for r in by[k])} / longer {sum(r['odds'] > 150 for r in by[k])}")
    passed = by.get("7 PASSED EVERYTHING - one Dog a day / the runner-up cap", [])
    if passed:
        for b in D.BANDS:
            D.cell(f"          passed everything, {b}", [r for r in passed if D.band(r) == b])
        D.cell("          passed everything, home", [r for r in passed if home(r)])
        D.cell("          passed everything, road", [r for r in passed if not home(r)])
        bd = defaultdict(list)
        for r in passed:
            bd[r["date"]].append(r)
        D.cell("          passed everything: the BEST score a day (the next runner-up)", [max(v, key=sc) for v in bd.values()])
        D.sched("          ... at ½u", [(max(v, key=sc), 0.5) for v in bd.values()])
    print(f"   -- just under the gate: a score of {g - 2:g}..{g:g}")
    under = [r for r in d if g - 2 <= sc(r) < g]
    D.cell("   every dog in the band", under)
    D.cell("      posted (floor / runner-up / NBA floor ...)", [r for r in under if r.get("kind")])
    clean = [r for r in under if not r.get("kind") and not r.get("trap") and not r.get("fighting") and not r.get("waiting") and r.get("n_reasons2") and not r.get("game_taken")]
    D.cell("      not posted, clean (no trap / fight / wait, a reason, the game free)", clean)
    D.cell("         ... and the own-read rule passes", [r for r in clean if r.get("dog_own_ok")])
    D.cell("         ... the own-read rule fails", [r for r in clean if not r.get("dog_own_ok")])
    if lg == "nhl":
        print("   -- hockey: the FALLBACK Dog's bar (a score of 3+, the own read 2+ points over the no-vig market)")
        fb = [r for r in d if 3 < sc(r) < 6 and not r.get("trap") and not r.get("fighting")]
        D.cell("   score 3-6, not a trap / fighting", fb)
        D.cell("      the own gap 2+ (own_gap_ok)", [r for r in fb if r.get("own_gap_ok")])
        D.cell("      the own gap under 2", [r for r in fb if not r.get("own_gap_ok")])
        D.cell("      not posted", [r for r in fb if not r.get("kind")])
        D.cell("      not posted, rested vs a favorite off a game last night", [r for r in fb if not r.get("kind") and r["x"].get("rested_vs_b2b")])

print("\n===== FOOTBALL ON THE LONG BOARD (football_1114 rows, 2018-26, the 11/14 code): the same question")
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


def fcell(name, rs, pool=None):
    if not rs:
        print(f"  {name:64s} n    0")
        return
    import random
    fl = lambda r: r["dec"] - 1 if r["result"] == "won" else -1.0   # noqa: E731
    tr = [r for r in rs if fs(r["date"]) <= 2021]
    he = [r for r in rs if fs(r["date"]) >= 2022]
    f = lambda x: 100 * sum(map(fl, x)) / len(x) if x else 0.0   # noqa: E731
    seas = defaultdict(float)
    for r in rs:
        seas[fs(r["date"])] += fl(r)
    w = sum(r["result"] == "won" for r in rs)
    need = 100 * sum(1 / r["dec"] for r in rs) / len(rs)
    w1 = 100 * sum((1 / min(.99, 1 / r["dec"] + .01) - 1) if r["result"] == "won" else -1.0 for r in rs) / len(rs)
    pb = ""
    if pool and 10 <= len(rs) < len(pool):
        rnd = random.Random(1117)
        v = [fl(r) for r in pool]
        m = sum(map(fl, rs)) / len(rs)
        pb = f" | placebo {sum(1 for _ in range(2000) if sum(rnd.sample(v, len(rs))) / len(rs) >= m)}"
    print(f"  {name:64s} n {len(rs):4d} {w:3d}-{len(rs) - w:<4d} {100 * w / len(rs):4.1f}% (needs {need:4.1f}) {f(rs):+6.1f}%"
          f" | 2018-21 {f(tr):+6.1f}% ({len(tr):3d}) | 2022-26 {f(he):+6.1f}% ({len(he):3d}) | up {sum(v > 0 for v in seas.values())}/{len(seas)}"
          f" | 1pt worse {w1:+6.1f}%{pb} | " + " ".join(f"{s % 100}:{v:+.0f}" for s, v in sorted(seas.items())))


fsc = lambda r: r["dog_score"] if r.get("dog_score") is not None else -99   # noqa: E731
for lg in ("ncaaf", "nfl"):
    d = [r for r in rows if r["league"] == lg]
    print(f"-- {lg}")
    fcell("every dog", d)
    g = [r for r in d if r.get("good")]
    fcell("GATED (a real play: the Dog gate, the own-read rule, the weighed check, a reason)", g, d)
    fcell("   the Dog of the Day", [r for r in g if r["kind"] == "dog"], d)
    fcell("   the runner-up dog play", [r for r in g if r["kind"] == "dogplay"], d)
    un = [r for r in g if r["kind"] is None]
    fcell("   NEVER POSTED (one Dog a day)", un, d)
    fcell("      home", [r for r in un if r["home"] and not r.get("neutral")], d)
    fcell("      road", [r for r in un if not r["home"] and not r.get("neutral")], d)
    for b in D.BANDS:
        fcell(f"      {b}", [r for r in un if D.band(r) == b], d)
    bd = defaultdict(list)
    for r in un:
        bd[r["date"]].append(r)
    fcell("      the best score a day (the runner-up)", [max(v, key=fsc) for v in bd.values()], d)
    road = lambda r: not r["home"] and not r.get("neutral")   # noqa: E731
    if lg == "nfl":
        print("   NFL: the ROAD dog at a score of 4+ whose studies beat the price (the gate is 8)")
        c = [r for r in d if fsc(r) >= 4 and r.get("wdb") and road(r)]
        fcell("   road, score 4+, the studies beat the price", c, d)
        fcell("      posted (floor / Dog / runner-up)", [r for r in c if r["kind"]], d)
        fcell("      NEVER POSTED", [r for r in c if not r["kind"]], d)
        fcell("      never posted, score 4-6", [r for r in c if not r["kind"] and fsc(r) < 6], d)
        fcell("      never posted, score 6-8", [r for r in c if not r["kind"] and 6 <= fsc(r) < 8], d)
        fcell("      never posted, the own-read rule passes", [r for r in c if not r["kind"] and r.get("dog_own_ok")], d)
        fcell("      never posted, the own-read rule fails", [r for r in c if not r["kind"] and not r.get("dog_own_ok")], d)
        fcell("   home, score 4+, the studies beat the price", [r for r in d if fsc(r) >= 4 and r.get("wdb") and r["home"]], d)
        fcell("   placebo against ROAD dogs only: road score 4+ wdb", c, [r for r in d if road(r)])
