"""H46-H48 - THE DOSE THE MAX PLAY RIDES ON: the weighed read's edge over the REAL price (juice in). Live, the rule
check pulls any unit play whose read doesn't beat its price - so the replay's Locks split in two: the ones whose
weighed read beats the price (postable but for the no-thin-Lock rule) and the ones it doesn't (never postable)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M

R = M.rows()
rec = M.rec
ML = [r for r in R if r["market"] == "ml"]
FAV = [r for r in ML if -150 <= r["odds"] <= -101 and r["mn"] >= 3]
LOCK = [r for r in FAV if r["kind"] == "lock"]
for r in FAV:
    r["lift"] = None if (r["w_p"] is None or r["edge_own"] is None) else r["w_p"] - (r["edge_own"] + 1) / r["dec"]
    r["we"] = None if r["w_p"] is None else r["w_p"] * r["dec"] - 1
print("H46 THE REPLAY'S LOCKS BY THE WEIGHED READ'S EDGE OVER THE PRICE (cents on the dollar)")
for a, b in ((-1, -0.01), (-0.01, 0), (0, 0.01), (0.01, 0.02), (0.02, 0.03), (0.03, 1)):
    rec(f"weighed edge {100 * a:+.0f}..{100 * b:+.0f}c", [r for r in LOCK if r["we"] is not None and a <= r["we"] < b], FAV, min_n=1)
rec("weighed read UNDER the price (never postable - the rule check)", [r for r in LOCK if r["we"] is not None and r["we"] <= 0], FAV, kelly=True)
rec("weighed read OVER the price", [r for r in LOCK if r["we"] is not None and r["we"] > 0], FAV, kelly=True)
rec("no weighed read", [r for r in LOCK if r["we"] is None], FAV, min_n=1)
print("\nH47 EVERY FAVORITE -150..-101 AT 56%+ BY THE WEIGHED EDGE (clean: not a trap / fighting)")
C = [r for r in FAV if r["p"] >= 0.56 and r["we"] is not None and not r["trap"] and not r["fighting"]]
for a, b in ((-1, -0.03), (-0.03, -0.01), (-0.01, 0), (0, 0.01), (0.01, 0.02), (0.02, 0.03), (0.03, 1)):
    rec(f"weighed edge {100 * a:+.0f}..{100 * b:+.0f}c", [r for r in C if a <= r["we"] < b], FAV)
print("   ... under 56%")
C2 = [r for r in FAV if r["p"] < 0.56 and r["we"] is not None and not r["trap"] and not r["fighting"]]
for a, b in ((-1, -0.03), (-0.03, 0), (0, 0.02), (0.02, 1)):
    rec(f"weighed edge {100 * a:+.0f}..{100 * b:+.0f}c", [r for r in C2 if a <= r["we"] < b], FAV)
print("\nH48 THE POSTABLE SET, EVERY WAY TO DRAW IT (56%+, weighed over the no-vig market and over the price, clean)")
B = [r for r in C if r["we"] > 0 and r["w_p"] >= r["p_market"]]
rec("B: every one (3+ games)", B, FAV, kelly=True)
rec("B: the studies lift it 2+ points", [r for r in B if (r["lift"] or 0) >= 0.02 - 1e-9], FAV, kelly=True)
rec("B: lift under 2", [r for r in B if (r["lift"] or 0) < 0.02 - 1e-9], FAV)
rec("B: lift 1+", [r for r in B if (r["lift"] or 0) >= 0.01 - 1e-9], FAV, kelly=True)
rec("B: both teams 10+ games", [r for r in B if r["mn"] >= 10], FAV, kelly=True)
rec("B: titled the Lock by the replay", [r for r in B if r["kind"] == "lock"], FAV, kelly=True)
rec("B: not titled the Lock", [r for r in B if r["kind"] != "lock"], FAV)
rec("B: the own read over the price too", [r for r in B if r["edge_own"] > 0], FAV)
rec("B: the own read under the price", [r for r in B if r["edge_own"] <= 0], FAV, kelly=True)
print("   the same set with 54%+ in place of 56%+ (the next band down)")
B54 = [r for r in FAV if 0.54 <= r["p"] < 0.56 and r["we"] is not None and r["we"] > 0 and not r["trap"] and not r["fighting"] and (r["lift"] or 0) >= 0.02 - 1e-9]
rec("54-56%, weighed over the price, lift 2+", B54, FAV)
