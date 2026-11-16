"""H1-H25 - COLLEGE HOOPS: every named big-size candidate on the 2018-26 replay rows (the close, train 2018-22 /
held 2023-26, placebo 2,000 from the cell's own pool, the price 10 cents worse, quarter-Kelly on the low end of the
HELD-OUT win rate). One line a cell."""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M

R = M.rows()
ML = [r for r in R if r["market"] == "ml"]
SP = [r for r in R if r["market"] == "spread"]
spk = {(r["gid"], r["side"]): r for r in SP}
mlk = {(r["gid"], r["side"]): r for r in ML}
DOG = [r for r in ML if 100 <= r["odds"] <= 350 and r["mn"] >= 4]
FAV = [r for r in ML if -150 <= r["odds"] <= -101 and r["mn"] >= 3]
LOCK = [r for r in ML if r["kind"] == "lock"]
dr = lambda r: r.get("dog_read") if r.get("dog_read") is not None else -99
eg = lambda r: r["effgap"] if r.get("effgap") is not None else -9
other = lambda r: "away" if r["side"] == "home" else "home"
rec = M.rec

print("== A. THE COLLEGE HOOPS LOCK (2u; 1u at a 7-point own gap; half a unit through game 10)")
rec("H1 every Lock", LOCK, FAV, kelly=True)
rec("H2 Lock, league game", [r for r in LOCK if r["conf"]], FAV, kelly=True)
rec("   Lock, non-league", [r for r in LOCK if not r["conf"]], FAV)
rec("H3 Lock -150..-131", [r for r in LOCK if r["odds"] <= -131], FAV, kelly=True)
rec("   Lock -130..-101", [r for r in LOCK if r["odds"] > -131], FAV)
rec("H4 Lock, efficiency read 3+ over the market", [r for r in LOCK if eg(r) >= 0.03], FAV, kelly=True)
rec("   Lock, efficiency read under +3", [r for r in LOCK if eg(r) < 0.03], FAV)
rec("   Lock, efficiency read UNDER the market", [r for r in LOCK if eg(r) < 0.0], FAV)
for a, b in ((-1, 0.01), (0.01, 0.02), (0.02, 0.04), (0.04, 1)):
    rec(f"H5 Lock, weighed read {a:+.2f}..{b:+.2f} over the no-vig", [r for r in LOCK if r["w_p"] is not None and a <= r["w_p"] - r["p_market"] < b], FAV)
rec("H25 Lock, both teams 11+ games", [r for r in LOCK if r["mn"] >= 11], FAV, kelly=True)
rec("    Lock, a team 10 or fewer games", [r for r in LOCK if r["mn"] < 11], FAV)
for w in ("home", "road", "neutral"):
    rec(f"   Lock, {w}", [r for r in LOCK if r["where"] == w], FAV)
for mo in ("11", "12", "01", "02", "03"):
    rec(f"   Lock, month {mo}", [r for r in LOCK if r["month"] == mo], FAV)
stk = lambda r: (spk.get((r["gid"], r["side"])) or {}).get("stack") or 0
ostk = lambda r: (spk.get((r["gid"], other(r))) or {}).get("stack") or 0
rec("H17 Lock, its spread side carries a stack 0.02+", [r for r in LOCK if stk(r) >= 0.02], FAV)
rec("    Lock, the OTHER spread side carries a stack 0.02+", [r for r in LOCK if ostk(r) >= 0.02], FAV)

print("== B. THE DOG READ (every dog +100..+350, both 4+ games)")
for a, b in ((4, 5), (5, 6), (6, 7), (7, 99)):
    rec(f"   dog read {a}-{b}", [r for r in DOG if a <= dr(r) < b], DOG)
D6 = [r for r in DOG if dr(r) >= 6]
D5 = [r for r in DOG if dr(r) >= 5]
rec("H6 dog read 6+", D6, DOG, kelly=True)
rec("H7 dog read 6+ and the efficiency gap 15+", [r for r in D6 if eg(r) >= 0.15], DOG, kelly=True)
rec("   dog read 6+ and the gap under 15", [r for r in D6 if eg(r) < 0.15], DOG)
rec("H8 dog read 5+ and the efficiency gap 15+", [r for r in D5 if eg(r) >= 0.15], DOG, kelly=True)
rec("   dog read 5+ and the gap under 15", [r for r in D5 if eg(r) < 0.15], DOG)
rec("H9 dog read 6+ at +100..+150", [r for r in D6 if r["odds"] <= 150], DOG, kelly=True)
rec("   dog read 6+ at +151..+350", [r for r in D6 if r["odds"] > 150], DOG)
rec("H10 dog read 6+ road / neutral", [r for r in D6 if r["where"] != "home"], DOG, kelly=True)
rec("    dog read 6+ home", [r for r in D6 if r["where"] == "home"], DOG)
rec("H11 dog read 5+, a 'trap' or 'fighting' (left out of the slot)", [r for r in D5 if r["trap"] or r["fighting"]], DOG, kelly=True)
rec("    dog read 5+, clean (the slot's own)", [r for r in D5 if not (r["trap"] or r["fighting"])], DOG)
rec("H22 dog read 6+ Nov-Dec", [r for r in D6 if r["month"] in ("11", "12")], DOG)
rec("    dog read 6+ Jan-Mar", [r for r in D6 if r["month"] in ("01", "02", "03")], DOG)
rec("H23 dog read 5+ league game", [r for r in D5 if r["conf"]], DOG, kelly=True)
rec("    dog read 5+ non-league", [r for r in D5 if not r["conf"]], DOG)
rec("H19 dog read 4+ and its spread side carries a stack 0.03+", [r for r in DOG if dr(r) >= 4 and stk(r) >= 0.03], DOG, kelly=True)
rec("    dog read 4+ and the favorite's spread side carries the stack", [r for r in DOG if dr(r) >= 4 and ostk(r) >= 0.03], DOG)
G = [r for r in ML if r["kind"] == "gap"]
rec("H20 the gap play (posted)", G, DOG)
rec("    gap play, gap 20+", [r for r in G if eg(r) >= 0.20], DOG)
rec("    gap play, read 6+", [r for r in G if dr(r) >= 6], DOG, kelly=True)
for a, b in ((0.15, 0.20), (0.20, 0.25), (0.25, 1)):
    rec(f"    every dog read 4+ with the gap {a:.2f}-{b:.2f}", [r for r in DOG if dr(r) >= 4 and a <= eg(r) < b], DOG)

print("== C. THE SPREAD STACK (every spread side, both 4+ games; the pool = every spread side with a stack 0.03+)")
SS = [r for r in SP if (r.get("stack") or 0) >= 0.03]
for a, b in ((0.05, 0.06), (0.06, 0.08), (0.08, 0.10), (0.10, 9)):
    rec(f"   stack {a:.2f}-{b:.2f}", [r for r in SS if a <= r["stack"] < b], SS)
rec("H12 stack 0.06+", [r for r in SS if r["stack"] >= 0.06], SS, kelly=True)
rec("H13 stack 0.08+", [r for r in SS if r["stack"] >= 0.08], SS, kelly=True)
rec("    stack 0.08+, the night's biggest only", None or [r for r in SS if r["stack"] >= 0.08 and r.get("kind") == "stackplay"], SS)
rec("H14 stack 0.05+, 3+ fades in the stack", [r for r in SS if r["stack"] >= 0.05 and (r.get("stack_n") or 0) >= 3], SS, kelly=True)
rec("H15 stack 0.05+ and the efficiency read on its side (3+ over)", [r for r in SS if r["stack"] >= 0.05 and eg(mlk.get((r["gid"], r["side"])) or {"effgap": None}) >= 0.03], SS, kelly=True)
rec("    stack 0.05+ and the efficiency read against it (3+ under)", [r for r in SS if r["stack"] >= 0.05 and -9 < eg(mlk.get((r["gid"], r["side"])) or {"effgap": None}) <= -0.03], SS)
rec("H18 stack 0.05+ side's MONEYLINE when it is a favorite -150..-101", [mlk[(r["gid"], r["side"])] for r in SS if r["stack"] >= 0.05 and (r["gid"], r["side"]) in mlk and -150 <= mlk[(r["gid"], r["side"])]["odds"] <= -101], FAV, kelly=True)
rec("    stack 0.05+ side's MONEYLINE when it is a dog +100..+350", [mlk[(r["gid"], r["side"])] for r in SS if r["stack"] >= 0.05 and (r["gid"], r["side"]) in mlk and 100 <= mlk[(r["gid"], r["side"])]["odds"] <= 350], DOG, kelly=True)
rec("    stack 0.05+, laying 0.5-5", [r for r in SS if r["stack"] >= 0.05 and -5 <= (r["line"] or 0) < 0], SS, kelly=True)
rec("    stack 0.05+, home", [r for r in SS if r["stack"] >= 0.05 and r["where"] == "home"], SS)

print("== D. FAVORITES BY THE READS (-150..-101, both 3+ games)")
wg = lambda r: (r["w_p"] - 1 / r["dec"]) if r["w_p"] is not None else -9
rec("H24 weighed read 0..+1 over the PRICE", [r for r in FAV if 0 <= wg(r) < 0.01], FAV)
rec("    weighed read +1..+3 over the price", [r for r in FAV if 0.01 <= wg(r) < 0.03], FAV)
rec("    weighed read 3+ over the price", [r for r in FAV if wg(r) >= 0.03], FAV)
rec("H21 favorite: weighed over the price AND the efficiency read 3+ over", [r for r in FAV if wg(r) >= 0 and eg(r) >= 0.03], FAV, kelly=True)
rec("    ... and not the Lock", [r for r in FAV if wg(r) >= 0 and eg(r) >= 0.03 and r["kind"] != "lock"], FAV)
rec("H16a favorite across a dog carrying a dog fade (dog read -4 or less), weighed over", [r for r in FAV if wg(r) >= 0 and dr(mlk.get((r["gid"], other(r))) or {}) <= -4 and dr(mlk.get((r["gid"], other(r))) or {}) > -99], FAV)
