"""H42-H45 - THE NIGHTLY COLLEGE HOOPS BEST BET + THE MAX PLAY AS WIRED.
H42 a nightly #1 by kind trust (the Lock, a dog read 6+, the gap play, the slot dog, the biggest stack) against the
    night's other unit plays and a random one of them.
H43 the same #1 by the biggest read over the price / by the shortest price.
H44 THE MAX PLAY AS WIRED: a favorite -150..-101, 56%+, the weighed read over the no-vig market AND over the price
    (the Lock's own test), the studies on the dog across lifting it 2+ points, both teams 10+ games (the early-Lock
    rule stays) - the best one a night. Its units at 3u, by season, the worst losing stretch, the price a nickel /
    a dime / 15 cents worse, the leave-one-season-out low end.
H45 the max play's siblings: is it better than the other favorites the engine likes / the other Locks."""
import math
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M

random.seed(1116)
R = M.rows()
rec = M.rec
ML = [r for r in R if r["market"] == "ml"]
FAV = [r for r in ML if -150 <= r["odds"] <= -101 and r["mn"] >= 3]
dr = lambda r: r.get("dog_read") if r.get("dog_read") is not None else -99
UNIT = [r for r in R if r["kind"] in ("lock", "gap", "ncaabplay", "stackplay")]


def trust(r):
    if r["kind"] == "lock":
        return 0
    if r["market"] == "ml" and r["odds"] > 0 and dr(r) >= 6:
        return 1
    if r["kind"] == "gap":
        return 2
    if r["kind"] == "ncaabplay":
        return 3
    return 4


by = defaultdict(list)
for r in UNIT:
    by[r["date"]].append(r)
multi = {d: v for d, v in by.items() if len(v) >= 2}
print(f"nights with 2+ college hoops unit plays: {len(multi)} of {len(by)}")
for nm, key in (("H42 #1 by kind trust (Lock, read 6+, gap, slot, stack)", lambda r: (trust(r), -(r.get("stack") or 0), -dr(r))),
                ("H43a #1 by the shortest price", lambda r: r["odds"] if r["odds"] < 0 else 1000 + r["odds"]),
                ("H43b #1 by the dog read then the stack", lambda r: (-dr(r), -(r.get("stack") or 0)))):
    top = [sorted(v, key=key)[0] for v in multi.values()]
    rest = [r for v in multi.values() for r in sorted(v, key=key)[1:]]
    rec(nm, top, UNIT)
    rec("    the night's other unit plays", rest, UNIT)
    mine = sum(r["pnl"] for r in top)
    hit = sum(sum(random.choice(v)["pnl"] for v in multi.values()) >= mine for _ in range(2000))
    print(f"      a random one of the night's unit plays did as well {hit} of 2000 times")

print("\nH44 THE MAX PLAY AS WIRED")
for r in FAV:
    r["lift"] = None if (r["w_p"] is None or r["edge_own"] is None) else r["w_p"] - (r["edge_own"] + 1) / r["dec"]


def ok(r, games=10, lift=0.02, p=0.56):
    return (r["lift"] is not None and r["lift"] >= lift - 1e-9 and r["p"] >= p and r["w_p"] >= r["p_market"]
            and r["w_p"] * r["dec"] >= 1 and not r["trap"] and not r["fighting"] and r["mn"] >= games)


def nightly(pool):
    b = defaultdict(list)
    for r in pool:
        b[r["date"]].append(r)
    return [max(v, key=lambda r: (r["w_p"] * r["dec"], r["p"])) for v in b.values()]


POOL = [r for r in FAV if ok(r)]
MAXP = nightly(POOL)
rec("every qualifying favorite (10+ games)", POOL, FAV, kelly=True)
x = rec("THE MAX PLAY - the best one a night", MAXP, FAV, kelly=True)
rec("   ... that the replay board titled the Lock", [r for r in MAXP if r["kind"] == "lock"], FAV)
rec("   ... that it did not (another sport's Lock that day / no Lock)", [r for r in MAXP if r["kind"] != "lock"], FAV)
rec("   the qualifying favorites in games 3-9 (left to the early-Lock rule)", [r for r in FAV if ok(r, games=3) and r["mn"] < 10], FAV)
rec("   max play, league game", [r for r in MAXP if r["conf"]], FAV)
rec("   max play, home", [r for r in MAXP if r["where"] == "home"], FAV)
rec("   max play, road / neutral", [r for r in MAXP if r["where"] != "home"], FAV)
for mo in ("11", "12", "01", "02", "03"):
    rec(f"   max play, month {mo}", [r for r in MAXP if r["month"] == mo], FAV, min_n=3)
for c in (5, 10, 15, 20):
    print(f"   at a price {c} cents worse: ROI {100 * sum(M.worse(r, c) for r in MAXP) / len(MAXP):+.1f}%")
S = sorted(MAXP, key=lambda r: r["date"])
for u in (2, 3, 4):
    eq = pk = dd = 0.0
    for r in S:
        eq += u * r["pnl"]
        pk = max(pk, eq)
        dd = min(dd, eq - pk)
    bys = defaultdict(float)
    for r in S:
        bys[r["season"]] += u * r["pnl"]
    print(f"   at {u}u: {eq:+.1f}u on {u * len(S)}u risked, worst losing stretch {dd:.1f}u, by season " + " ".join(f"{s % 100}:{v:+.1f}" for s, v in sorted(bys.items())))
run = worst = 0
for r in S:
    run = run + 1 if r["pnl"] < 0 else 0
    worst = max(worst, run)
print(f"   the longest run of losses: {worst}; plays a season: " + " ".join(f"{s % 100}:{sum(1 for r in S if r['season'] == s)}" for s in sorted({r['season'] for r in S})))
print("   leave one season out (the win rate without it, its 5% low end, quarter-Kelly):")
for s in sorted({r["season"] for r in S}):
    v = [r for r in S if r["season"] != s]
    w, l_ = sum(r["win"] for r in v), sum(r["pnl"] < 0 for r in v)
    lo = M.wilson_lo(w, w + l_, 1.645)
    print(f"      without {s}: {w}-{l_} {100 * w / (w + l_):.1f}% low end {100 * lo:.1f}% -> {M.qkelly(lo, sum(r['dec'] for r in v) / len(v)):.1f}u")
he = [r for r in S if r["season"] >= 2023]
w, l_ = sum(r["win"] for r in he), sum(r["pnl"] < 0 for r in he)
p = w / (w + l_)
lo_n = p - 1.645 * math.sqrt(p * (1 - p) / (w + l_))
d = sum(r["dec"] for r in he) / len(he)
print(f"   THE SIZE: held out {w}-{l_} = {100 * p:.1f}% at an average price of {d:.3f}; the 5% low end {100 * lo_n:.1f}% (normal) / "
      f"{100 * M.wilson_lo(w, w + l_, 1.645):.1f}% (Wilson) -> quarter-Kelly {M.qkelly(lo_n, d):.1f}u / {M.qkelly(M.wilson_lo(w, w + l_, 1.645), d):.1f}u; "
      f"the price needs {100 / d:.1f}%")
half = 0.5 * (sum(r["win"] for r in S) / len(S)) + 0.5 * (sum(1 / r["dec"] for r in S) / len(S))
print(f"   with HALF the replay's edge gone (the weights were fit on these seasons): {100 * half:.1f}% -> quarter-Kelly {M.qkelly(half, sum(r['dec'] for r in S) / len(S)):.1f}u")
print("\n   the quit rule (25 graded, under 60% won = off): how often it trips")
for tp in (0.58, 0.62, 0.66, 0.70, 0.73):
    c = sum(math.comb(25, k) * tp ** k * (1 - tp) ** (25 - k) for k in range(0, 15))
    print(f"      a true win rate of {100 * tp:.0f}%: {100 * c:.0f}%")

print("\nH45 THE SIBLINGS")
rec("favorites 56%+, weighed over the price, lift under 2", [r for r in FAV if r["lift"] is not None and r["lift"] < 0.02 and r["p"] >= 0.56 and r["w_p"] * r["dec"] >= 1 and r["mn"] >= 10], FAV)
rec("favorites lift 2+ but under 56%", [r for r in FAV if (r["lift"] or 0) >= 0.02 and r["p"] < 0.56 and r["mn"] >= 10], FAV)
rec("favorites lift 2+, 56%+, a trap / fighting", [r for r in FAV if (r["lift"] or 0) >= 0.02 and r["p"] >= 0.56 and (r["trap"] or r["fighting"]) and r["mn"] >= 10], FAV, min_n=3)
rec("the night's 2nd+ qualifying favorite", [r for r in POOL if r not in MAXP], FAV, min_n=3)
