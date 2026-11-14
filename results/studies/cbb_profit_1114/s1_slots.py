"""11/14 STUDY 1 - THE COLLEGE HOOPS UNIT SLOTS ON TODAY'S CODE, AND THEIR LEAKS (priority 1). The replay board
(lib.load) re-built at the close every college hoops day 2018-26; each kind graded flat at the close and at its own
units, then split by price band, home / road / neutral, conference vs non-conference, month, games played, the dog
read, the efficiency gap, rest. A leak = a slice that loses in BOTH halves with the rest of the kind up in both.
Usage: python s1_slots.py [old]  (old = the 11/13 funnel4 rows)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L

R = L.load(L.OLD if "old" in sys.argv else None)
P = L.plays(R)
if "old" in sys.argv:                                   # the dog slot rebuilt (recon.py - 192 of 195 real picks + the
    import recon                                        # gap twins the funnel saved as 'gap')
    P["dog"] = [dict(r, u=2.0 if r["dog_read"] >= 6 else 1.0) for r in recon.slot(R) if r["rslot"] < 2]
ML = [r for r in R if r["market"] == "ml"]
DOGPOOL = [r for r in ML if 100 <= r["odds"] <= 350]
FAVPOOL = [r for r in ML if -150 <= r["odds"] <= -101]
SPPOOL = [r for r in R if r["market"] == "spread"]
print(f"rows {len(R)}; plays: " + ", ".join(f"{k} {len(v)}" for k, v in P.items()))
pools = {"gap": DOGPOOL, "dog": DOGPOOL, "fav": FAVPOOL, "lock": FAVPOOL, "stack": SPPOOL}

print("\n1. EACH KIND, flat 1u at the close (and at its units)")
for k in ("gap", "dog", "fav", "stack", "lock"):
    L.rec(k, P.get(k, []), pools[k], units=True)
both = {(r["gid"], r["side"]) for r in P["gap"]} & {(r["gid"], r["side"]) for r in P["dog"]}
print(f"   (gap & dog slot on the same dog: {len(both)})")
L.rec("gap only (not the slot)", [r for r in P["gap"] if (r["gid"], r["side"]) not in both], DOGPOOL, units=True)
L.rec("dog slot only (not the gap)", [r for r in P["dog"] if (r["gid"], r["side"]) not in both], DOGPOOL, units=True)
L.rec("both (gap + slot, one bet)", [r for r in P["gap"] if (r["gid"], r["side"]) in both], DOGPOOL, units=True)

def gapb(r):
    if r.get("effgap") is not None:
        g = r["effgap"]
        return "eff gap <0" if g < 0 else "0-5" if g < .05 else "5-10" if g < .10 else "10-15" if g < .15 else "15-20" if g < .20 else "20+"
    if r.get("eff_p") is None or r.get("p_market") is None:
        return "no eff"
    g = r["eff_p"] - r["p_market"]
    return "eff gap <0" if g < 0 else "0-5" if g < .05 else "5-10" if g < .10 else "10-15" if g < .15 else "15-20" if g < .20 else "20+"

SPLITS = (("price", lambda r: L.band(r["odds"])),
          ("where", lambda r: r["where"]),
          ("conference", lambda r: {True: "conference", False: "non-conference", None: "?"}[r["conf"]]),
          ("month", lambda r: {"11": "Nov", "12": "Dec", "01": "Jan", "02": "Feb", "03": "Mar"}.get(r["month"], r["month"])),
          ("games in (fewer)", lambda r: "4-6" if r["mn"] <= 6 else "7-10" if r["mn"] <= 10 else "11-19" if r["mn"] <= 19 else "20+"),
          ("dog read", lambda r: "?" if r.get("dog_read") is None else "<4" if r["dog_read"] < 4 else "4-5" if r["dog_read"] < 5 else "5-6" if r["dog_read"] < 6 else "6-8" if r["dog_read"] < 8 else "8+"),
          ("eff gap", gapb),
          ("rest (mine)", lambda r: "?" if r["rest"] is None else "0-2" if r["rest"] < 2.5 else "3-4" if r["rest"] < 4.5 else "5-6" if r["rest"] < 6.5 else "7+"),
          ("rest edge", lambda r: "?" if r["rest"] is None or r["orest"] is None else "fresher 2+" if r["rest"] - r["orest"] >= 2 else "tireder 2+" if r["rest"] - r["orest"] <= -2 else "even"),
          ("power", lambda r: f"me {'P' if r['pow'] else 'm'} / them {'P' if r['opow'] else 'm'}"),
          ("stack", lambda r: "?" if r.get("stack") is None else ".05-.06" if r["stack"] < .06 else ".06-.08" if r["stack"] < .08 else ".08+"),
          ("spread", lambda r: "?" if r.get("line") is None else ("dog " if r["line"] > 0 else "fav ") + ("0-5" if abs(r["line"]) <= 5 else "5.5-10" if abs(r["line"]) <= 10 else "10.5-15" if abs(r["line"]) <= 15 else "15.5+")),
          ("night rank", lambda r: str(r.get("slot_i") if r.get("slot_i") is not None else r.get("rslot") if r.get("rslot") is not None else r.get("stack_i") if r.get("stack_i") is not None else "?")),
          ("twin", lambda r: "gap twin" if r.get("kind") == "gap" else "alone"))

print("\n2. THE SPLITS (flat at the close; a slice needs 15+ plays to print a line)")
for k in ("gap", "dog", "stack", "lock", "fav"):
    rows = P.get(k, [])
    if len(rows) < 30:
        continue
    print(f"\n== {k} ({len(rows)})")
    for nm, f in SPLITS:
        if nm in ("stack", "spread") and k != "stack" or nm in ("dog read", "eff gap") and k in ("stack", "lock", "fav"):
            continue
        groups = {}
        for r in rows:
            groups.setdefault(f(r), []).append(r)
        print(f"  -- by {nm}")
        for g in sorted(groups):
            L.rec(f"{k} | {nm} {g}", groups[g], pools[k], units=True)
print(f"\ncells read: {L.CELLS[0]} (about {L.CELLS[0] // 20} clear |z| 2 by luck)")
