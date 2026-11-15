"""S4 the college hoops dog the night after a road game (the owner's Northern Iowa question: lost at Oakland the night
after playing at Michigan St) - every dog at the close, then the dog slot's own picks.
S5 the dog slot's missing volume: road / neutral dogs at a dog read of 3-4 (the 11/14 home-dog weight's mirror).
S6 more of the best cell: the college hoops favorites that pass the Lock's bars on a night the Lock went elsewhere.
Rows: the 11/13 lean funnel (2018-26, ESPN's close). TRAIN 2018-22 / HELD 2023-26."""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clib as C  # noqa: E402

L = C.L
R = L.load(L.OLD, markets=("ml",), keep_all=True)
C.attach(R)
print(f"{len(R)} moneyline rows, seasons {sorted({r['season'] for r in R})}")
DOG = [r for r in R if 100 <= r["odds"] <= 350]
FAV = [r for r in R if -150 <= r["odds"] <= -101]

print("\n==== S4. THE DOG THE NIGHT AFTER (every dog +100..+350 at the close) ====")
L.rec("every dog", DOG)
L.rec("every ROAD dog (true road)", [r for r in DOG if r["where"] == "road"])
b2b = lambda r: r["gap_h"] is not None and r["gap_h"] <= 30
two = lambda r: r["gap_h"] is not None and 30 < r["gap_h"] <= 54
L.rec("dog on a back-to-back (last game within 30h)", [r for r in DOG if b2b(r)], DOG)
L.rec("  .. tonight a true road game", [r for r in DOG if b2b(r) and r["where"] == "road"], DOG)
x = [r for r in DOG if b2b(r) and r["where"] == "road" and r["pwhere"] == "road"]
L.rec("  .. ROAD last night, ROAD tonight (the Northern Iowa spot)", x, DOG)
L.rec("  .. road last night, road tonight, opp rested 2+ days", [r for r in x if (r["ogap_h"] or 999) >= 48], DOG)
L.rec("  .. neutral last night, neutral tonight (a tournament)", [r for r in DOG if b2b(r) and r["where"] == "neutral" and r["pwhere"] == "neutral"], DOG)
L.rec("  .. b2b, at home tonight", [r for r in DOG if b2b(r) and r["where"] == "home"], DOG)
L.rec("road dog, last game 31-54h ago, also on the road", [r for r in DOG if two(r) and r["where"] == "road" and r["pwhere"] == "road"], DOG)
L.rec("road dog, 2nd+ straight game away, within 54h", [r for r in DOG if r["where"] == "road" and r["n_away"] >= 1 and r["gap_h"] is not None and r["gap_h"] <= 54], DOG)
L.rec("road dog, 3rd+ straight game away from home", [r for r in DOG if r["where"] == "road" and r["n_away"] >= 2], DOG)
L.rec("road dog, 3rd game in 4.5 days", [r for r in DOG if r["where"] == "road" and r["n3"] >= 2], DOG)
L.rec("dog vs a team on a back-to-back (dog rested 48h+)", [r for r in DOG if r["ogap_h"] is not None and r["ogap_h"] <= 30 and (r["gap_h"] or 999) >= 48], DOG)
L.rec("FAV -150..-101 on a b2b, road last night + road tonight", [r for r in FAV if b2b(r) and r["where"] == "road" and r["pwhere"] == "road"], FAV)
L.rec("FAV -150..-101 vs a team road last night + road tonight", [r for r in FAV if r["ogap_h"] is not None and r["ogap_h"] <= 30 and r["where"] == "home" and r["opwhere"] == "road"], FAV)
print(" -- the slot's own dogs (dog read 4+, both 4+ games, the best two a night)")
S = C.recon.slot(R)
P = [r for r in S if r["rslot"] < 2]
L.rec("the slot (rebuilt), posted two", P)
L.rec("  slot dog within 54h of its last game", [r for r in P if r["gap_h"] is not None and r["gap_h"] <= 54])
L.rec("  slot dog on a b2b (30h)", [r for r in P if b2b(r)], min_n=1)
L.rec("  slot ROAD dog, last game also away, within 54h", [r for r in P if r["where"] == "road" and r["pwhere"] in ("road", "neutral") and r["gap_h"] is not None and r["gap_h"] <= 54], min_n=1)
L.rec("  slot-eligible (any rank) road dog, last game away, within 54h", [r for r in S if r["where"] == "road" and r["pwhere"] in ("road", "neutral") and r["gap_h"] is not None and r["gap_h"] <= 54], min_n=1)
L.rec("  slot road dog, 2nd+ straight away", [r for r in P if r["where"] == "road" and r["n_away"] >= 1], min_n=1)
L.rec("  slot road dog, 1st game away (off a home game)", [r for r in P if r["where"] == "road" and r["n_away"] == 0], min_n=1)

print("\n==== S5. THE SLOT'S MISSING VOLUME: dog read 3-4 ====")
K = None


def pool(lo, hi):
    out = []
    for r in R:
        if not 100 <= r["odds"] <= 350 or r["mn"] < 4 or r["trap"] or r["fighting"]:
            continue
        dr = r.get("dog_read")
        if dr is None or not lo <= dr < hi:
            continue
        if min(0.95, r["p_market"] + dr / 100) * r["dec"] - 1 <= 0:
            continue
        out.append(r)
    return out


eff = {}
import pickle
for x in pickle.load(open(os.path.expanduser("~/.cache/d503_studies/cbb_knowledge_b_rows.pkl"), "rb")):
    eff[(x["id"], x["side"])] = x.get("eff")
for r in R:
    e = r.get("eff_p") if r.get("eff_p") is not None else eff.get((r["gid"], r["side"]))
    r["effgap"] = None if e is None or r["p_market"] is None else e - r["p_market"]
for lo, hi in ((4, 99), (3, 4), (2, 3), (1, 2), (0, 1)):
    v = pool(lo, hi)
    print(f" -- dog read {lo}..{hi}")
    L.rec(f"all eligible, read {lo}-{hi}", v, DOG)
    for w in ("home", "road", "neutral"):
        L.rec(f"   {w}", [r for r in v if r["where"] == w], DOG)
    L.rec("   road / neutral, eff gap 15+", [r for r in v if r["where"] != "home" and (r["effgap"] or 0) >= 0.15], DOG)
    L.rec("   road / neutral, eff gap under 15", [r for r in v if r["where"] != "home" and (r["effgap"] or 0) < 0.15], DOG)
    L.rec("   road / neutral, +100..+150", [r for r in v if r["where"] != "home" and r["odds"] <= 150], DOG)
    L.rec("   road / neutral, +151..+350", [r for r in v if r["where"] != "home" and r["odds"] > 150], DOG)
v = [r for r in pool(3, 4) if r["where"] != "home"]
by = defaultdict(list)
for r in v:
    by[r["date"]].append(r)
first = [max(x, key=lambda r: (r["dog_read"], r["effgap"] or 0)) for x in by.values()]
L.rec("road / neutral read 3-4: the best one a night", first, DOG)
slot_days = defaultdict(int)
for r in P:
    slot_days[r["date"]] += 1
L.rec("  .. on a night the slot posted under 2", [r for r in first if slot_days[r["date"]] < 2], DOG)
L.rec("  .. on a night the slot posted nothing", [r for r in first if slot_days[r["date"]] == 0], DOG)
print("  price-free: road / neutral read 3-4 won %.1f%% vs the no-vig %.1f%% (%d)" % (
    100 * sum(r["win"] for r in v) / max(1, len(v)), 100 * sum(r["p_market"] for r in v) / max(1, len(v)), len(v)))

print("\n==== S6. MORE LOCKS: the favorites that pass the Lock's bars and were not the Lock ====")
LOCK = [r for r in R if r["kind"] == "lock"]
L.rec("the college hoops Lock (as posted)", LOCK, FAV)
print("   the Locks' own bars: p min %.3f, odds %d..%d, own edge min %.3f, w_p-over-price min %.3f" % (
    min(r["p"] for r in LOCK), min(r["odds"] for r in LOCK), max(r["odds"] for r in LOCK),
    min(r["edge_own"] for r in LOCK if r["edge_own"] is not None),
    min((r["w_p"] or r["p"]) * r["dec"] - 1 for r in LOCK)))
cand = [r for r in R if r["kind"] != "lock" and -150 <= r["odds"] <= -120 and r["p"] >= 0.56 and not r["trap"] and not r["fighting"]
        and r["edge_own"] is not None and r["edge_own"] > 0 and (r["w_p"] or r["p"]) * r["dec"] > 1 and r["mn"] >= 3]
L.rec("Lock-grade, not the Lock (p 56%+, -150..-120, own + weighed over)", cand, FAV)
lock_days = {r["date"] for r in LOCK}
L.rec("  .. on a night a college hoops Lock posted", [r for r in cand if r["date"] in lock_days], FAV)
L.rec("  .. on a night with no college hoops Lock", [r for r in cand if r["date"] not in lock_days], FAV)
L.rec("  .. own edge 3c+ (not thin)", [r for r in cand if r["edge_own"] >= 0.03], FAV)
L.rec("  .. own edge under 3c (thin)", [r for r in cand if r["edge_own"] < 0.03], FAV)
L.rec("  .. kind = " + "/".join(sorted({str(r["kind"]) for r in cand})), cand, FAV)
for k in sorted({str(r["kind"]) for r in cand}):
    L.rec(f"     kind {k}", [r for r in cand if str(r["kind"]) == k], FAV)
for nm, f in (("p 56-58", lambda r: r["p"] < 0.58), ("p 58-60", lambda r: 0.58 <= r["p"] < 0.60), ("p 60+", lambda r: r["p"] >= 0.60)):
    L.rec(f"  .. {nm}", [r for r in cand if f(r)], FAV)
for w in ("home", "road", "neutral"):
    L.rec(f"  .. {w}", [r for r in cand if r["where"] == w], FAV)
    L.rec(f"     (the Lock, {w})", [r for r in LOCK if r["where"] == w], FAV)
L.rec("  .. league game", [r for r in cand if r["conf"]], FAV)
L.rec("  .. non-league", [r for r in cand if r["conf"] is False], FAV)
loose = [r for r in R if r["kind"] != "lock" and -150 <= r["odds"] <= -120 and 0.54 <= r["p"] < 0.56 and not r["trap"] and not r["fighting"]
         and r["edge_own"] is not None and r["edge_own"] > 0]
L.rec("the next band down (p 54-56, own over)", loose, FAV)
L.rec("every favorite -150..-120", [r for r in FAV if r["odds"] <= -120])
L.rec("every favorite -150..-120, p 56%+", [r for r in FAV if r["odds"] <= -120 and r["p"] >= 0.56])
print(f"\ncells read: {L.CELLS[0]}")
