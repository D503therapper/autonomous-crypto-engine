"""11/13 EARLY-SEASON COLLEGE HOOPS - s5: the s4 early dog's profit sits on neutral-site games (8-1 at gate 2). Is there a
broad neutral-site cell under it (the early-season events), or is it nine bets? The neutral dog the efficiency read
backs, by window and gap, early (either team under 4 games) vs later, and the nominal home / away side of it."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E
from s2_cells import ML, DOGP

for lab, lo, hi in (("early 0-3", 0, 3), ("early 2-3", 2, 3), ("4+", 4, 999), ("4+, Nov-Dec", 4, 999)):
    rows = [r for r in DOGP(ML) if lo <= r["mn"] <= hi and r["neu"] and not r["trap"] and r.get("eff_p") is not None]
    if "Nov" in lab:
        rows = [r for r in rows if r["nd"]]
    print(f"\n== {lab}: neutral-site dogs +100..+350")
    E.rec("every one", rows)
    E.rec("the efficiency read backs it (over 50%)", [r for r in rows if r["eff_p"] > 0.5], pool=rows)
    for a, b in ((0, 0.05), (0.05, 0.10), (0.10, 0.15), (0.15, 1)):
        E.rec(f"eff over the no-vig [{a:.2f},{b:.2f})", [r for r in rows if a <= r["eff_p"] - r["p_market"] < b], pool=rows, min_n=15)
    E.rec("backed + not fighting + dog read 4+", [r for r in rows if r["eff_p"] > 0.5 and not r["fighting"] and (r.get("dog_read") or -9) >= 4], pool=rows, min_n=10)
    E.rec("nominal home side", [r for r in rows if r["home"]], pool=rows)
    E.rec("nominal away side", [r for r in rows if not r["home"]], pool=rows)
print(f"\ncells looked at: {E.CELLS[0]}")
