"""11/13 EARLY-SEASON COLLEGE HOOPS - s4: THE CANDIDATE AS IT WOULD BE WIRED, one bet a side (no twin double count).
The early dog: a college hoops dog +100..+350, the fewer games either team has in [gate, 3] (4+ is the wired slots'),
never a trap, never a side the own read fights, and EITHER the dog slot's read (dog read 4+, the price beaten by it) OR
the 🔍 gap play's rule (the efficiency read backing it 15+ points over the no-vig, no study fade) - the best 2 a night
by the dog read, then the efficiency gap. The gate is CHOSEN ON TRAIN (2018-22) and only then read held out (2023-26).
Flat ½u (a new cell: no bigger-size cell has a held-out sample)."""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E
from s2_cells import ML, DOGP


def early_ok(r):
    if r["trap"] or r["fighting"] or not 100 <= r["odds"] <= 350:
        return False
    slot = r.get("dog_read") is not None and r["dog_read"] >= 4 and r["p_market"] + r["dog_read"] / 100 > r["need"]
    gap = (r.get("eff_p") is not None and r["eff_p"] > 0.5 and r["eff_p"] - r["p_market"] >= 0.15 and (r.get("dog_read") or -9) >= 4)
    return slot or gap


def plays(rows, cap=2):
    c = [r for r in rows if early_ok(r)]
    return E.per_night(c, key=lambda r: (r["dog_read"], (r["eff_p"] or 0) - r["p_market"]), cap=cap)


print("== the early dog, one bet a side, best 2 a night - by gate (games 'gate'..3 for the fewer games in)")
res = {}
for k in (0, 1, 2, 3):
    rows = [r for r in ML if k <= r["mn"] <= 3]
    P = plays(rows)
    res[k] = E.rec(f"gate {k}", P, pool=DOGP(rows))
    n = Counter(r["date"] for r in P)
    print(f"      {len(P)} plays on {len(n)} nights, {len(P) / max(1, len(n)):.2f} a night; by season "
          + " ".join(f"{s % 100}:{c}" for s, c in sorted(Counter(r['season'] for r in P).items())))
best = max((k for k in res if res[k]), key=lambda k: res[k]["tr"])
best = int(os.environ.get("GATE", best))
print(f"\nTHE GATE CHOSEN ON TRAIN: {best} (train ROI {res[best]['tr']:+.1f}%) -> held out {res[best]['he']:+.1f}%")

rows = [r for r in ML if best <= r["mn"] <= 3]
P = plays(rows)
print(f"\n== gate {best}: the pieces")
E.rec("no neutral site", [r for r in P if not r["neu"]], pool=DOGP([r for r in rows if not r["neu"]]))
E.rec("neutral site only", [r for r in P if r["neu"]], min_n=10)
E.rec("home", [r for r in P if r["home"] and not r["neu"]], min_n=10)
E.rec("road", [r for r in P if not r["home"] and not r["neu"]], min_n=10)
E.rec("+100..+150", [r for r in P if r["odds"] <= 150], min_n=10)
E.rec("+151..+350", [r for r in P if r["odds"] > 150], min_n=10)
E.rec("1 a night (the best)", plays(rows, 1), pool=DOGP(rows))
E.rec("no cap", plays(rows, 99), pool=DOGP(rows))
E.rec("the slot read alone (dog read 4+)", [r for r in P if r["dog_read"] >= 4 and r["p_market"] + r["dog_read"] / 100 > r["need"]], min_n=10)
E.rec("the gap rule alone", [r for r in P if r.get("eff_p") is not None and r["eff_p"] > 0.5 and r["eff_p"] - r["p_market"] >= 0.15], min_n=10)
E.rec("dog read 6+ (a 1u cell?)", [r for r in P if r["dog_read"] >= 6], min_n=10)
E.rec("dog read 4-6", [r for r in P if r["dog_read"] < 6], min_n=10)
print("\n== every play, gate", best)
for r in sorted(P, key=lambda r: r["date"]):
    print(f"   {r['date']} {r['team']:22s} {r['odds']:+5d} vs {r['opp']:20s} {'N' if r['neu'] else 'H' if r['home'] else 'A'} mn {r['mn']} read {r['dog_read']:+.1f} "
          f"eff {'' if r['eff_p'] is None else round(100 * (r['eff_p'] - r['p_market']))} {r['result']}")
print(f"\ncells looked at: {E.CELLS[0]}")
