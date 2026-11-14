"""11/14 STUDY 10 - THE CHECK ON THE REBUILT SLOT: the funnel5 re-run (the dog slot's real nightly ranking, the gap
twins, the engine's own efficiency read, the dog read's parts) on the seasons it finished before the board (a shared
machine: two at a time). The seasons started before the 11/14 home-dog weight was written (2026, 2023, 2018) run the
slot WITHOUT it; the later ones run WITH it (the funnel opens every 2026 date gate) - each printed apart: the first
group checks the cut's cell, the second shows the slot after the cut. Usage: python s10_new_rows.py"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L

R = L.load(L.NEW)
P = L.plays(R, new=True)
withcut = {r["season"] for r in R if (r.get("dog_read_parts") or {}).get("home")}
print("seasons on file:", sorted({r["season"] for r in R}), "| run WITH the home-dog weight:", sorted(withcut))
g15 = lambda r: r.get("eff_p") is not None and r["eff_p"] - r["p_market"] >= 0.15
for lab, keep in (("WITHOUT the weight", lambda s: s not in withcut), ("WITH the weight", lambda s: s in withcut)):
    print(f"\n== seasons {lab}")
    for k in ("gap", "dog", "fav", "stack", "lock"):
        L.rec(k, [r for r in P.get(k, []) if keep(r["season"])], None, units=True, min_n=5)
    D = [r for r in P.get("dog", []) if keep(r["season"])]
    cut = [r for r in D if r["where"] == "home" and not g15(r)]
    L.rec("dog slot: home, no 15-pt gap", cut, None, units=True, min_n=5)
    L.rec("dog slot: home, no 15-pt gap, read under 5", [r for r in cut if r["dog_read"] < 5], None, units=True, min_n=5)
    L.rec("dog slot: the rest", [r for r in D if not (r["where"] == "home" and not g15(r))], None, units=True, min_n=5)
    print(f"   gap twins in the slot: {sum(r['kind'] == 'gap' for r in D)} of {len(D)}")
    ML = [r for r in R if r["market"] == "ml" and keep(r["season"])]
    L.rec("slot rank 2+ (a bigger cap)", [r for r in ML if r.get("slot_i") is not None and r["slot_i"] >= 2], None, min_n=5)
    L.rec("stack rank 2+ (a bigger cap)", [r for r in R if keep(r["season"]) and r.get("stack_i") is not None and r["stack_i"] >= 2], None, min_n=5)
    dropped = [r for r in ML if (r.get("dog_read_parts") or {}).get("home") and r.get("dog_read") is not None
               and 3 <= r["dog_read"] < 4 and (r.get("dog_read_parts") or {}).get("games_ok") and not r["trap"] and not r["fighting"]]
    L.rec("dogs the weight took under the gate (any rank)", dropped, None, min_n=5)
