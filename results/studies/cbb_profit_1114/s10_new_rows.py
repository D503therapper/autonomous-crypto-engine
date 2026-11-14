"""11/14 STUDY 10 - THE CHECK ON THE REBUILT SLOT: the funnel5 re-run on the 11/14 code (the dog slot's real nightly
ranking, the gap twins, the engine's own efficiency read, the dog read's parts) on the seasons it finished before the
board (a shared machine: two at a time). Same kinds and the home-dog cut, read off the real picks."""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L

R = L.load(L.NEW)
print("seasons on file:", sorted({r["season"] for r in R}))
P = L.plays(R, new=True)
ML = [r for r in R if r["market"] == "ml"]
DOGPOOL = [r for r in ML if 100 <= r["odds"] <= 350]
for k in ("gap", "dog", "fav", "stack", "lock"):
    L.rec(k, P.get(k, []), None, units=True, min_n=5)
g15 = lambda r: r.get("eff_p") is not None and r["eff_p"] - r["p_market"] >= 0.15
D = P.get("dog", [])
cut = [r for r in D if r["where"] == "home" and not g15(r)]
L.rec("dog slot: home, no 15-pt gap (the cut's cell)", cut, None, units=True, min_n=5)
L.rec("dog slot: home, no 15-pt gap, read under 5 (what the -1 drops)", [r for r in cut if r["dog_read"] < 5], None, units=True, min_n=5)
L.rec("dog slot: the rest", [r for r in D if not (r["where"] == "home" and not g15(r))], None, units=True, min_n=5)
twins = [r for r in D if r["kind"] == "gap"]
print(f"gap twins in the slot: {len(twins)} of {len(D)}")
L.rec("slot rank 2+ (a bigger cap)", [r for r in ML if r.get("slot_i") is not None and r["slot_i"] >= 2], None, min_n=5)
L.rec("stack rank 2+ (a bigger cap)", [r for r in R if r.get("stack_i") is not None and r["stack_i"] >= 2], None, min_n=5)
