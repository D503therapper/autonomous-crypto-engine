"""11/17 UNDERDOG EDGE - (5) COLLEGE HOOPS: the dog slot (dog read 4+, two a night, 1u / 2u at 5+) and the 🔍 gap play.
Rows: the 11/16 max-play hunt's cached college hoops replay rows (maxcol_1116/mlib.rows - the board re-built at ESPN's
close every college hoops day 2018-26; TRAIN = seasons 2018-22, HELD OUT = 2023-26). The slot is built the way LIVE runs
it today (sizing_1117/s2b_read5.py): the 11/16 open slot (a trap / a fought side posts), the 11/14 home-dog -1 in the
read (a true-home dog whose efficiency read is not 15+ over the no-vig reads 1 less), the read clears the price, never
a game the board is already on, the best two reads a night. Yesterday's sizing study did the read's dose (2u at 5+,
wired) - NOT redone. Here:
  1  where the slot's edge lives: price band, home / road / neutral, month, conference, rest
  2  the read x where grid - every dog (both teams 4+ games, the read clears the price)
  3  THE DOGS THE SLOT LEAVES ON THE TABLE: the third+ dog a night (the cap), the read-3 dogs (under the gate), the
     read-4+ dogs before both teams have 4 games (the early gate)
  4  the candidate: a TRUE ROAD dog at a read of 3 - the five checks
  5  the 🔍 college hoops gap play as the replay posted it
Usage: python results/studies/dogs_1117/s5_cbb.py > results/studies/dogs_1117/s5_cbb.out"""
import os
import random
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "sizing_1117", "s2_cbb_slot.py")
code = open(SRC).read()
S2 = {"__file__": SRC}
sys.argv = [sys.argv[0]]
exec(compile(code[:code.index("\nS = slot()")], SRC, "exec"), S2)   # its loaders + line() / sched() - none of its prints
R, DOG0, line, sched = S2["R"], S2["DOG"], S2["line"], S2["sched"]


def live_read(r):
    x = r["dog_read"]
    if r.get("where") == "home" and not (r.get("dog_read_parts") or {}).get("home"):
        if not ((r.get("effgap") or 0) >= 0.15):
            x -= 1
    return x


DOG = []
for r in DOG0:
    r = dict(r)
    r["lr"] = None if r.get("dog_read") is None else live_read(r)
    DOG.append(r)
LOCKG = {r["gid"] for r in R if r["kind"] in ("lock", "play", "dogplay")}
clears = lambda r: min(0.95, r["p_market"] + r["lr"] / 100) * r["dec"] - 1 > 0      # noqa: E731
READ = [r for r in DOG if r["lr"] is not None and r["mn"] >= 4 and clears(r)]          # every dog with a read that clears
free = lambda r: r["gid"] not in LOCKG and r["kind"] not in ("stackplay", "floor")    # noqa: E731


def slot(cap=2, gate=4.0, road_gate=None, pool=None, road_ok=None):
    by = defaultdict(list)
    for r in (pool if pool is not None else READ):
        g = road_gate if (road_gate is not None and r["where"] == "road" and (road_ok is None or road_ok(r))) else gate
        if r["lr"] >= g and free(r):
            by[r["date"]].append(r)
    out = []
    for d, v in by.items():
        seen = set()
        for r in sorted(v, key=lambda r: (-r["lr"], -(r.get("effgap") or 0))):
            if r["gid"] not in seen:
                seen.add(r["gid"])
                if len(seen) <= cap:
                    out.append(r)
    return sorted(out, key=lambda r: (r["date"], r["gid"]))


def band(r):
    return "+100..+150" if r["odds"] <= 150 else "+151..+250" if r["odds"] <= 250 else "+251..+350"


def worse1(rs):
    """flat ROI a point of win chance worse than the close"""
    t = 0.0
    for r in rs:
        t += (1 / min(0.99, 1 / r["dec"] + 0.01) - 1) if r["win"] else (-1.0 if r["pnl"] < 0 else 0.0)
    return 100 * t / len(rs) if rs else 0.0


BANDS = ("+100..+150", "+151..+250", "+251..+350")
SL = slot()
units = lambda r: 2.0 if r["lr"] >= 5 else 1.0     # noqa: E731
P4 = [r for r in READ if r["lr"] >= 4]
print(f"college hoops dogs +100..+350, 2018-26: {len(DOG)}; with a read that clears its price (both teams 4+ games): {len(READ)}; "
      f"at 4+: {len(P4)}; THE SLOT (two a night): {len(SL)}, {len(SL) / 8:.0f} a season")
line("every college hoops dog (the vig)", DOG)
line("THE SLOT as it runs today", SL, DOG)
sched("THE SLOT at today's sizes (1u, 2u at 5+)", SL, units)

print("\n===== 1. WHERE THE SLOT'S EDGE LIVES (placebo = a random same-size set of SLOT plays)")
for b in BANDS:
    line(f"   {b}", [r for r in SL if band(r) == b], SL)
    line("      read 4", [r for r in SL if band(r) == b and r["lr"] < 5], SL)
    line("      read 5+", [r for r in SL if band(r) == b and r["lr"] >= 5], SL)
for w in ("home", "road", "neutral"):
    line(f"   {w}", [r for r in SL if r["where"] == w], SL)
    for b in BANDS:
        line(f"      {w} {b}", [r for r in SL if r["where"] == w and band(r) == b], SL)
for m in ("11", "12", "01", "02", "03"):
    line(f"   month {m}", [r for r in SL if r["month"] == m], SL)
line("   conference game", [r for r in SL if r["conf"]], SL)
line("   non-conference", [r for r in SL if not r["conf"]], SL)
line("   the favorite on more rest than the dog", [r for r in SL if r["rest"] and r["orest"] and r["orest"] > r["rest"]], SL)
line("   the dog on more rest", [r for r in SL if r["rest"] and r["orest"] and r["rest"] > r["orest"]], SL)
line("   the same rest", [r for r in SL if r["rest"] and r["orest"] and r["rest"] == r["orest"]], SL)
line("   own read over the price", [r for r in SL if r["edge_own"] is not None and r["edge_own"] > 0], SL)
line("   own read under the price", [r for r in SL if r["edge_own"] is not None and r["edge_own"] <= 0], SL)
line("   a trap / a fought side (posts since 11/16)", [r for r in SL if r["trap"] or r["fighting"]], SL)
line("   neither", [r for r in SL if not (r["trap"] or r["fighting"])], SL)

print("\n===== 2. THE READ x WHERE GRID - every dog with a read (both teams 4+ games, the read clears; placebo vs every dog)")
for lo, hi in ((1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 99)):
    rs = [r for r in READ if lo <= r["lr"] < hi]
    line(f"read {lo}{'-' + str(hi) if hi < 99 else '+'}", rs, DOG)
    for w in ("home", "road", "neutral"):
        line(f"   {w}", [r for r in rs if r["where"] == w], DOG)

print("\n===== 3. THE DOGS THE SLOT LEAVES ON THE TABLE")
ids = {(r["gid"], r["side"]) for r in SL}
left = [r for r in P4 if (r["gid"], r["side"]) not in ids]
line("every read-4+ dog that clears its price", P4, DOG)
line("... NOT in the slot", left, P4)
line("   the board was already on the game / the stack or floor play", [r for r in left if not free(r)], P4)
capd = [r for r in left if free(r)]
line("   THE CAP: the third+ read-4+ dog of the night", capd, P4)
for b in BANDS:
    line(f"      {b}", [r for r in capd if band(r) == b], P4)
for cap in (2, 3, 4, 99):
    s = slot(cap=cap)
    line(f"   the slot at {cap if cap < 99 else 'no cap'} a night", s, DOG)
    sched("      ... at 1u / 2u at 5+", s, units)
by = defaultdict(list)
for r in slot(cap=99):
    by[r["date"]].append(r)
for k in (1, 2, 3, 4):
    line(f"   the #{k} read of the night", [sorted(v, key=lambda r: (-r["lr"], -(r.get('effgap') or 0)))[k - 1] for v in by.values() if len(v) >= k], P4)
print("-- under the gate (the live read, both teams 4+ games, clears the price)")
R3 = [r for r in READ if 3 <= r["lr"] < 4]
line("   read 3", R3, DOG)
for w in ("home", "road", "neutral"):
    line(f"   read 3, {w}", [r for r in R3 if r["where"] == w], DOG)
line("   read 3 home: a raw read of 4 the 11/14 home-dog -1 took down", [r for r in R3 if r["where"] == "home" and r["dog_read"] >= 4], DOG)
line("   read 3 home: a raw read of 3 with the 15-point gap", [r for r in R3 if r["where"] == "home" and r["dog_read"] < 4], DOG)
print("-- the early gate: a read of 4+ before both teams have 4 games")
early = [r for r in DOG if r["lr"] is not None and r["lr"] >= 4 and r["mn"] < 4 and clears(r)]
line("   read 4+, a team under 4 games", early, DOG)
line("   read 5+, a team under 4 games", [r for r in early if r["lr"] >= 5], DOG)
for n in (0, 1, 2, 3):
    line(f"   read 4+, the fewer-games team has {n}", [r for r in early if r["mn"] == n], DOG)

print("\n===== 4. THE CANDIDATE: THE SLOT TAKES A TRUE ROAD DOG AT A READ OF 3 (the road dog's gate 3; home / neutral stay 4)")
RR = [r for r in R3 if r["where"] == "road"]
a, t, h, up, pb = line("every road dog at a read of 3", RR, DOG)
print(f"      a point worse than the close: {worse1(RR):+.1f}%   | placebo vs every ROAD dog: {S2['placebo'](RR, [r for r in DOG if r['where'] == 'road'])}"
      f" | vs the slot's plays: {S2['placebo'](RR, SL)} | vs every read-3+ dog: {S2['placebo'](RR, [r for r in READ if r['lr'] >= 3])}")
for b in BANDS:
    line(f"      {b}", [r for r in RR if band(r) == b], DOG)
line("      a trap / a fought side", [r for r in RR if r["trap"] or r["fighting"]], DOG)
line("      neither", [r for r in RR if not (r["trap"] or r["fighting"])], DOG)
line("      conference game", [r for r in RR if r["conf"]], DOG)
line("      non-conference", [r for r in RR if not r["conf"]], DOG)
for m in ("11", "12", "01", "02", "03"):
    line(f"      month {m}", [r for r in RR if r["month"] == m], DOG)
line("      the weights alone 3 (no ratings / knowledge points)", [r for r in RR if (r.get("dog_score") is not None)], DOG)
for cap in (2, 3):
    S3 = slot(cap=cap, road_gate=3.0)
    base = slot(cap=cap)
    bid = {(r["gid"], r["side"]) for r in base}
    add = [r for r in S3 if (r["gid"], r["side"]) not in bid]
    s3id = {(r["gid"], r["side"]) for r in S3}
    lost = [r for r in base if (r["gid"], r["side"]) not in s3id]
    print(f"-- the slot at {cap} a night with the road gate at 3: {len(S3)} plays ({len(base)} today); added {len(add)}, bumped out {len(lost)}")
    line("   the slot after", S3, DOG)
    line("   THE ADDED PLAYS", add, DOG)
    print(f"         a point worse: {worse1(add):+.1f}% | placebo vs the slot's plays today: {S2['placebo'](add, base)} | vs every road dog: {S2['placebo'](add, [r for r in DOG if r['where'] == 'road'])}")
    sched("   TODAY (1u, 2u at 5+)", base, units)
    sched("   AFTER: the read-3 road dog at 1u", S3, units)
    sched("   AFTER: the read-3 road dog at 0.5u", S3, lambda r: 0.5 if r["lr"] < 4 else units(r))
    sched("   the added plays alone at 1u", add, lambda r: 1.0)
    sched("   the added plays alone at 0.5u", add, lambda r: 0.5)
print("-- WHEN: the calendar (Nov-Dec = mostly non-conference; Jan-Mar = conference play). The added plays, two a night:")
LATE = ("01", "02", "03")
for nm, ok_ in (("every month (as wired)", None), ("January-March only", lambda r: r["month"] in LATE), ("Nov-Dec only", lambda r: r["month"] not in LATE),
                ("conference games only", lambda r: bool(r["conf"])), ("non-conference only", lambda r: not r["conf"])):
    S3 = slot(road_gate=3.0, road_ok=ok_)
    base = slot()
    bid = {(r["gid"], r["side"]) for r in base}
    add = [r for r in S3 if (r["gid"], r["side"]) not in bid]
    a_ = line(f"   added, {nm}", add, DOG)
    if len(add) >= 10:
        print(f"         a point worse: {worse1(add):+.1f}% | placebo vs every road dog: {S2['placebo'](add, [r for r in DOG if r['where'] == 'road'])}"
              f" | vs the slot's plays: {S2['placebo'](add, base)}")
        sched(f"      the slot AFTER ({nm}), the added at 0.5u", S3, lambda r: 0.5 if r["lr"] < 4 else units(r))
        sched("      the added plays alone at 0.5u", add, lambda r: 0.5)
print("-- is it the ROAD or the read? every road dog by the read (clears the price, both 4+ games)")
for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 99)):
    line(f"   road, read {lo}{'-' + str(hi) if hi < 99 else '+'}", [r for r in READ if r["where"] == "road" and lo <= r["lr"] < hi], DOG)
print("-- the read-3 road dog, the size the held-out half can prove (a quarter of Kelly on the low end of the HELD win rate)")
he = [r for r in RR if r["season"] >= 2023]
if he:
    import math
    w, n = sum(r["win"] for r in he), len(he)
    p = w / n
    dec = sum(r["dec"] for r in he) / n
    for z, nm in ((1.0, "one sd under"), (1.645, "the 5% end")):
        lo = (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)
        k = max(0.0, (lo * (dec - 1) - (1 - lo)) / (dec - 1)) / 4 * 100
        print(f"   held {w}-{n - w} ({100 * p:.1f}%) at an average {dec:.2f}: {nm} {100 * lo:.1f}% -> {k:.1f}u")

print("\n===== 5. THE 🔍 COLLEGE HOOPS GAP PLAY as the replay posted it (kind = gap)")
G = [r for r in DOG if r["kind"] == "gap"]
line("the gap play", G, DOG)
for b in BANDS:
    line(f"   {b}", [r for r in G if band(r) == b], G)
for w in ("home", "road", "neutral"):
    line(f"   {w}", [r for r in G if r["where"] == w], G)
line("   also a slot dog today", [r for r in G if (r["gid"], r["side"]) in ids], G)
line("   not a slot dog", [r for r in G if (r["gid"], r["side"]) not in ids], G)
line("   read 6+ (2u)", [r for r in G if (r["lr"] or 0) >= 6], G)
line("   read 4-5", [r for r in G if 4 <= (r["lr"] or 0) < 6], G)
line("   read under 4", [r for r in G if (r["lr"] or 0) < 4], G)
random.seed(1117)
