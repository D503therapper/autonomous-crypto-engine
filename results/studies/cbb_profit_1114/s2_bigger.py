"""11/14 STUDY 2 - BIGGER CELLS: MORE PLAYS A NIGHT OR MORE UNITS (priority 2). On the funnel5 rows (today's code, the
full nightly rankings with no cap): the dog slot's 3rd / 4th / 5th dog of a night, the stack play's 3rd+ side, the dog
read's dose (for the size), the gap play's dog read 6+ / 8+, the gap + slot twin, the Lock. A bigger size has to be
earned the 10/30 way: the bigger cell wins MORE per unit than its sibling in BOTH halves (and survives the placebo);
more plays a night have to win on their own in both halves."""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L

R = L.load()
assert any(r.get("slot_i") is not None for r in R), "needs the funnel5 rows"
ML = [r for r in R if r["market"] == "ml"]
DOGPOOL = [r for r in ML if 100 <= r["odds"] <= 350]
SP = [r for r in R if r["market"] == "spread"]


def worst(rows, u="u"):
    """the worst peak-to-trough run in units, by date order."""
    t = pk = dd = 0.0
    for r in sorted(rows, key=lambda r: r["date"]):
        t += r.get(u, 1.0) * r["pnl"]
        pk = max(pk, t)
        dd = min(dd, t - pk)
    return dd


print("1. THE DOG SLOT BY ITS RANK ON THE NIGHT (slot_i: 0-1 are posted; the slot is capped at 2)")
cand = [r for r in ML if r.get("slot_i") is not None]
for i in range(5):
    L.rec(f"slot rank {i}", [r for r in cand if r["slot_i"] == i], DOGPOOL)
L.rec("slot rank 2+ (what a bigger cap adds)", [r for r in cand if r["slot_i"] >= 2], DOGPOOL)
L.rec("slot rank 2 only (a cap of 3)", [r for r in cand if r["slot_i"] == 2], DOGPOOL)
print("\n2. THE DOG READ'S DOSE (every slot-eligible dog, any rank)")
for lo, hi in ((4, 5), (5, 6), (6, 7), (7, 8), (8, 99), (6, 99)):
    L.rec(f"dog read {lo}-{hi}", [r for r in cand if lo <= (r.get("dog_read") or 0) < hi], DOGPOOL)
print("   posted only (rank 0-1):")
for lo, hi in ((4, 5), (5, 6), (6, 8), (8, 99)):
    L.rec(f"   posted, dog read {lo}-{hi}", [r for r in cand if r["slot_i"] < 2 and lo <= (r.get("dog_read") or 0) < hi], DOGPOOL)

print("\n3. THE GAP PLAY (every one posts) by its dog read and gap")
gp = [r for r in ML if r.get("gap_i") is not None and r["kind"] == "gap"]
for lo, hi in ((0, 4), (4, 6), (6, 8), (8, 99)):
    L.rec(f"gap, dog read {lo}-{hi}", [r for r in gp if lo <= (r.get("dog_read") or 0) < hi], DOGPOOL)
for lo, hi in ((0.15, 0.20), (0.20, 0.25), (0.25, 1)):
    L.rec(f"gap, eff gap {100 * lo:.0f}-{100 * hi:.0f}", [r for r in gp if r.get("eff_p") is not None and lo <= r["eff_p"] - r["p_market"] < hi], DOGPOOL)
L.rec("gap AND the slot's pick (the twin - two bets on it)", [r for r in gp if r.get("slot_i") is not None and r["slot_i"] < 2], DOGPOOL)
L.rec("gap, not the slot's pick", [r for r in gp if not (r.get("slot_i") is not None and r["slot_i"] < 2)], DOGPOOL)

print("\n4. THE STACK PLAY BY ITS RANK ON THE NIGHT (stack_i: 0-1 are posted)")
sc = [r for r in SP if r.get("stack_i") is not None]
for i in range(4):
    L.rec(f"stack rank {i}", [r for r in sc if r["stack_i"] == i], SP)
L.rec("stack rank 2+", [r for r in sc if r["stack_i"] >= 2], SP)
for lo, hi in ((0.05, 0.06), (0.06, 0.08), (0.08, 0.10), (0.10, 9)):
    L.rec(f"stack {lo}-{hi} (any rank)", [r for r in sc if lo <= (r.get("stack") or 0) < hi], SP)

print("\n5. THE BOARD'S COLLEGE HOOPS UNITS AS SIZED TODAY vs THE ALTERNATIVES (units, worst stretch)")
P = L.plays(R)
base = [r for k in ("gap", "dog", "fav", "stack", "lock") for r in P.get(k, [])]
def show(name, rows):
    risk = sum(r["u"] for r in rows)
    net = sum(r["u"] * r["pnl"] for r in rows)
    tr = [r for r in rows if r["season"] <= 2022]
    he = [r for r in rows if r["season"] >= 2023]
    f = lambda v: sum(r["u"] * r["pnl"] for r in v)
    by = defaultdict(float)
    for r in rows:
        by[r["season"]] += r["u"] * r["pnl"]
    print(f"   {name:56s} {len(rows):4d} plays {net:+7.1f}u on {risk:6.1f}u ({100 * net / max(risk, 1):+5.1f}%) | train {f(tr):+6.1f}u held {f(he):+6.1f}u"
          f" | worst {worst(rows):+6.1f}u | seasons up {sum(v > 0 for v in by.values())}/{len(by)}")
show("TODAY (gap / slot 2 / fav / stack 2 / lock)", base)
for k in ("gap", "dog", "fav", "stack", "lock"):
    show(f"   {k}", P.get(k, []))
extra3 = [dict(r, u=2.0 if (r.get("dog_read") or 0) >= 6 else 1.0) for r in cand if r["slot_i"] == 2 and r["kind"] in (None, "gap", "ncaabplay")]
show("+ a 3rd slot dog a night", base + extra3)
st3 = [dict(r, u=0.5) for r in sc if r["stack_i"] == 2 and not r["kind"]]
show("+ a 3rd stack side a night", base + st3)
show("gap at 3u when dog read 6+", [dict(r, u=3.0) if k == "gap" and r["u"] == 2.0 else r for k in ("gap", "dog", "fav", "stack", "lock") for r in P.get(k, [])])
show("slot at 3u when dog read 6+", [dict(r, u=3.0) if k == "dog" and r["u"] == 2.0 else r for k in ("gap", "dog", "fav", "stack", "lock") for r in P.get(k, [])])
show("stack at 1u when the stack is .08+", [dict(r, u=1.0) if k == "stack" and (r.get("stack") or 0) >= 0.08 else r for k in ("gap", "dog", "fav", "stack", "lock") for r in P.get(k, [])])
print(f"\ncells read: {L.CELLS[0]}")
