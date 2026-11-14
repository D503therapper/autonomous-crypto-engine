"""11/14 STUDY 1b - THE DOG SLOT'S CANDIDATE CUTS (the rebuilt slot on all nine seasons, recon.py). A cut must hold the
five checks the other way: the cut cell at or under the vig in BOTH halves, what is kept better in BOTH halves, a
placebo (random same-size cuts of the slot), seasons. Each cut printed as (cut | kept)."""
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
import recon

random.seed(11141)
R = L.load(L.OLD)
D = [dict(r, u=2.0 if r["dog_read"] >= 6 else 1.0) for r in recon.slot(R) if r["rslot"] < 2]
DOGPOOL = [r for r in R if r["market"] == "ml" and 100 <= r["odds"] <= 350]
twin = lambda r: r["kind"] == "gap"
L.rec("THE DOG SLOT (rebuilt, twins in)", D, DOGPOOL, units=True)
CUTS = (("dog read under 5", lambda r: r["dog_read"] < 5),
        ("dog read under 5, not a gap twin", lambda r: r["dog_read"] < 5 and not twin(r)),
        ("not a gap twin", lambda r: not twin(r)),
        ("the night's 2nd dog", lambda r: r["rslot"] == 1),
        ("the night's 2nd dog, not a twin", lambda r: r["rslot"] == 1 and not twin(r)),
        ("home dog", lambda r: r["where"] == "home"),
        ("home dog, not a twin", lambda r: r["where"] == "home" and not twin(r)),
        ("home dog, read under 5", lambda r: r["where"] == "home" and r["dog_read"] < 5),
        ("efficiency gap under 15, read under 5", lambda r: (r.get("effgap") or 0) < 0.15 and r["dog_read"] < 5),
        ("efficiency gap 5-15", lambda r: r.get("effgap") is not None and 0.05 <= r["effgap"] < 0.15),
        ("games in 11-19", lambda r: 11 <= r["mn"] <= 19),
        ("March", lambda r: r["month"] == "03"))
for nm, f in CUTS:
    cut = [r for r in D if f(r)]
    kept = [r for r in D if not f(r)]
    print(f"\n-- CUT: {nm}")
    L.rec("   the cut", cut, None, units=True)
    L.rec("   kept", kept, None, units=True)
    if len(cut) >= 20:                      # placebo: a random cut of the same size does as badly
        mine = sum(r["u"] * r["pnl"] for r in cut)
        hit = sum(sum(r["u"] * r["pnl"] for r in random.sample(D, len(cut))) <= mine for _ in range(2000))
        print(f"   placebo: a random {len(cut)} of the slot did as badly {hit} of 2,000")
print(f"\ncells read: {L.CELLS[0]}")
