"""11/14 STUDY 1c - THE HOME DOG IN THE DOG SLOT, deeper (the cut s1b found), + the slot's 3rd+ dog a night.
(1) every dog the slot could take (dog read 4+, both 4+ games, not a trap / fighting, any rank) - home / road /
neutral x the efficiency gap 15+ (the gap play's bar); (2) the same on the slot's posted two; (3) the price-free
check - how often the home dog the ratings like wins vs what the no-vig price says; (4) the ESPN open 2023-26;
(5) more dogs a night (rank 2, 3, 4+)."""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
import recon

R = L.load(L.OLD)
S = recon.slot(R)
DOGPOOL = [r for r in R if r["market"] == "ml" and 100 <= r["odds"] <= 350]
g15 = lambda r: r.get("effgap") is not None and r["effgap"] >= 0.15
print("(1) EVERY SLOT-ELIGIBLE DOG (any rank on the night)")
for w in ("home", "road", "neutral"):
    for lab, f in (("eff gap 15+", g15), ("eff gap under 15", lambda r: not g15(r))):
        rows = [r for r in S if r["where"] == w and f(r)]
        L.rec(f"{w}, {lab}", rows, DOGPOOL)
        wins = sum(r["win"] for r in rows)
        if rows:
            print(f"      won {wins} of {len(rows)} = {100 * wins / len(rows):.1f}% vs the no-vig price {100 * sum(r['p_market'] for r in rows) / len(rows):.1f}%"
                  f" vs the dog read's chance {100 * sum(min(0.95, r['p_market'] + r['dog_read'] / 100) for r in rows) / len(rows):.1f}%")
print("\n(2) THE POSTED TWO")
P = [r for r in S if r["rslot"] < 2]
for w in ("home", "road", "neutral"):
    for lab, f in (("eff gap 15+", g15), ("eff gap under 15", lambda r: not g15(r))):
        L.rec(f"posted, {w}, {lab}", [r for r in P if r["where"] == w and f(r)], DOGPOOL)
L.rec("posted, home, eff gap under 15, read 5+", [r for r in P if r["where"] == "home" and not g15(r) and r["dog_read"] >= 5], DOGPOOL)
L.rec("posted, home, eff gap under 15, read 4-5", [r for r in P if r["where"] == "home" and not g15(r) and r["dog_read"] < 5], DOGPOOL)
print("\n(4) THE OPEN (ESPN's opening moneyline, where held)")
G = {}
import tlib
for g in tlib.build():
    G[g["id"]] = g
for nm, rows in (("posted home under 15 (the cut)", [r for r in P if r["where"] == "home" and not g15(r)]),
                 ("posted, the rest (kept)", [r for r in P if not (r["where"] == "home" and not g15(r))])):
    op = []
    for r in rows:
        # the funnel rows carry ml opens on the side
        pass
    L.rec(nm, rows, DOGPOOL)
print("\n(5) MORE DOGS A NIGHT (the slot's rank)")
for i in (0, 1, 2, 3):
    L.rec(f"rank {i}", [r for r in S if r["rslot"] == i], DOGPOOL)
L.rec("rank 2+", [r for r in S if r["rslot"] >= 2], DOGPOOL)
L.rec("rank 2+, not a home dog under 15", [r for r in S if r["rslot"] >= 2 and not (r["where"] == "home" and not g15(r))], DOGPOOL)
L.rec("rank 2+, read 5+", [r for r in S if r["rslot"] >= 2 and r["dog_read"] >= 5], DOGPOOL)
print(f"\ncells read: {L.CELLS[0]}")
