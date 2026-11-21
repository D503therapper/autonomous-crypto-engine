"""11/20 - THIN DAYS, part 2b: THE ONE CELL s1 LEFT STANDING - a floor-pool dog the floor's rules do NOT hold back
(hockey / an NFL road dog, a named reason, not fighting, a thin own edge) with a dog score of 0+, that the floor did
not post because the board already had its 2 unit plays: +13.6% on 319, both halves. Is it a real "more plays" rule
(the floor without the stop at 2), or the leftover half of a flat pool? The honest cell is the WHOLE pool at 0+ -
posted or not - since which of them the floor took that day is an accident of what else was on the board.
Usage: python3 results/studies/early_thin_1120/s2_floor_deeper.py > results/studies/early_thin_1120/s2_floor_deeper.out"""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "money_1117"))
import mlib as M  # noqa: E402

D = M.D
R = D.r3()
plays, days = M.board()
N = Counter(p["date"] for p in plays)
ONKEY = {(p["gid"], p["side"]) for p in plays}
ONGAME = defaultdict(set)
for p in plays:
    ONGAME[p["date"]].add(p["gid"])


def say(*a):
    print(*a, flush=True)


def sc(r):
    return r["dog_score"] if r.get("dog_score") is not None else -99


def pool_ok(r):
    return 100 <= r["odds"] <= 350 and not r.get("trap") and r.get("reasons") and not r.get("fighting") and not r.get("waiting") \
        and not (r["league"] == "nba" and r["odds"] > 199)


def free(r):
    return (r["gid"], r["side"]) not in ONKEY and r["gid"] not in ONGAME[r["date"]]


def cell(name, rs, pool=None):
    c = D.cell(name, rs, say=say, w=70)
    if pool is not None:
        pb = D.placebo(rs, pool)
        if pb is not None:
            say(f"      placebo: a random same-size set from its pool as good {pb} of 2,000")
    return c


FLOORP = [p for p in plays if p["kind"] == "floor"]
say("== the floor's POSTED plays on the rig (kind floor), flat")
cell("every posted floor play", FLOORP)
cell("  score 0+", [p for p in FLOORP if sc(p) >= 0])
cell("  score under 0 (a no-play day's first / the fallback)", [p for p in FLOORP if sc(p) < 0])
for lg in ("nhl", "nfl", "ncaab", "ncaaf", "nba"):
    cell(f"  {lg}", [p for p in FLOORP if p["league"] == lg])
    cell(f"  {lg}, score 0+", [p for p in FLOORP if p["league"] == lg and sc(p) >= 0])

LEFT = [r for r in R if pool_ok(r) and free(r) and not r.get("kind") and not r.get("floor_skip") and sc(r) >= 0]
ALLNS = [r for r in R if pool_ok(r) and not r.get("floor_skip") and (r.get("kind") in (None, "floor"))]
say("\n== the pool the floor's rules do not hold back (not skipped), score 0+ - LEFT on the table (the board had its 2)")
cell("left on the table, score 0+", LEFT, pool=[r for r in ALLNS if not r.get("kind")])
for lg in ("nhl", "nfl"):
    cell(f"  {lg}", [r for r in LEFT if r["league"] == lg])
for lab, f in (("score 0 to 2", lambda r: sc(r) < 2), ("score 2 to 4", lambda r: 2 <= sc(r) < 4), ("score 4+", lambda r: sc(r) >= 4)):
    cell(f"  {lab}", [r for r in LEFT if f(r)])
for b in D.BANDS:
    cell(f"  {b}", [r for r in LEFT if D.band(r) == b])
seas = defaultdict(list)
for r in LEFT:
    seas[D.season(r["date"])].append(r)
say("  by season: " + " · ".join(f"{s} {D.stat(v)['w']}-{D.stat(v)['n'] - D.stat(v)['w']} {D.stat(v)['roi']:+.1f}%" for s, v in sorted(seas.items())))
say(f"  how many a day it would add: on {len({r['date'] for r in LEFT})} days, {Counter(Counter(r['date'] for r in LEFT).values()).most_common()}")
say(f"  the board's count on those days: {Counter(N[r['date']] for r in LEFT).most_common()}")

say("\n== THE HONEST CELL: every not-skipped pool dog at a score of 0+, posted by the floor or not")
BOTH = [r for r in ALLNS if sc(r) >= 0]
cell("the whole pool, score 0+", BOTH, pool=ALLNS)
for lg in ("nhl", "nfl"):
    cell(f"  {lg}", [r for r in BOTH if r["league"] == lg], pool=[r for r in ALLNS if r["league"] == lg])
cell("the whole pool, score under 0", [r for r in ALLNS if sc(r) < 0])
say("  ... by the rank that day (the dog score's order among the day's not-skipped pool dogs at 0+):")
by = defaultdict(list)
for r in BOTH:
    by[r["date"]].append(r)
rk = defaultdict(list)
for d, rs in by.items():
    for i, r in enumerate(sorted(rs, key=lambda r: -sc(r))):
        rk[min(i, 3)].append(r)
for i in sorted(rk):
    cell(f"    the day's #{i + 1}{'+' if i == 3 else ''} by score", rk[i])

say("\n== hockey dogs by what the board already does with them (the score ladder, every not-fighting, not-trap hockey dog)")
NH = [r for r in R if r["league"] == "nhl" and 100 <= r["odds"] <= 350 and not r.get("trap") and not r.get("fighting")]
for lab, f in (("posted (any kind)", lambda r: r.get("kind")),
               ("not posted, named reason, score 0+", lambda r: not r.get("kind") and r.get("reasons") and sc(r) >= 0),
               ("not posted, named reason, score 0+, thin own edge", lambda r: not r.get("kind") and r.get("reasons") and sc(r) >= 0 and r.get("thin")),
               ("not posted, no reason, score 0+", lambda r: not r.get("kind") and not r.get("reasons") and sc(r) >= 0),
               ("not posted, score under 0", lambda r: not r.get("kind") and sc(r) < 0)):
    cell(lab, [r for r in NH if f(r)])

say("\n== as a schedule: today's board, + every left-on-the-table floor dog at 0+ at ½u (no stop at 2)")
D.sched("TODAY (the rig)", [(p, p["u"]) for p in plays], say=say)
D.sched("+ the left-over floor dogs at ½u", [(p, p["u"]) for p in plays] + [(r, 0.5) for r in LEFT], say=say)
D.sched("  the added plays alone at ½u", [(r, 0.5) for r in LEFT], say=say)
D.sched("  hockey only, at ½u", [(r, 0.5) for r in LEFT if r["league"] == "nhl"], say=say)
