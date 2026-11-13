"""11/13 EARLY-SEASON COLLEGE HOOPS - s2: the candidate cells, early window (either team under 4 games in) vs the rest.
Rows: s1's cache (the 11/13 funnel at the close, today's code, + the walk-forward efficiency chance with last season's
final ratings carried in as the prior). TRAIN 2018-22, HELD OUT 2023-26. Every cell: W-L, ROI at the close, z, both
halves, seasons up, ESPN's open where we hold it, a placebo (2,000 random sets of the same size / season mix from the
cell's own price-band pool - does the RULE beat just betting that band?).
  (a) the unit slots with the 4-game gate lowered: the dog slot (dog read 4+, best 2 a night), the 🔍 gap play
      (efficiency read 15+ over the no-vig, backed, no fade), the favorite slot (-120..-150, weighed 56%+, 1-5 pts over,
      own over, no Nov-Dec road / neutral favorite, no efficiency-against) - by the fewer games either team has (0/1/2/3)
  (b) the moneyline favorite lean cell -150..-130 as a ½u value play (the lean rule's pool; + the value-play bar: the own
      read 1+ pt over what the price needs)
  (c) last season carried in: the efficiency read alone in the early window (favorites / dogs by how far it sits from
      the no-vig), home / road / neutral, the buy game."""
import os, pickle, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E

R = pickle.load(open(os.path.join(os.path.expanduser("~"), ".cache", "d503_early1113", "rows.pkl"), "rb"))
ML = [r for r in R if r["market"] == "ml" and r.get("p_market") is not None and r.get("dec")]
for r in ML:
    r["own"] = None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]
    r["wp"] = r["w_p"] if r.get("w_p") is not None else r["own"]
    r["need"] = 1 / r["dec"]
    r["neu"] = str(r.get("neutral")) in ("1", "True", "true")
    r["nd"] = r["date"][5:7] in ("11", "12")
EARLY = [r for r in ML if r["mn"] < 4]
LATE = [r for r in ML if r["mn"] >= 4]
DOGP = lambda rows: [r for r in rows if 100 <= r["odds"] <= 350]
FAVP = lambda rows, lo=-150, hi=-120: [r for r in rows if lo <= r["odds"] <= hi]


def dog_slot(rows, gate=4):
    c = [r for r in DOGP(rows) if not r["trap"] and not r["fighting"] and r.get("dog_read") is not None and r["dog_read"] >= gate
         and r["p_market"] + r["dog_read"] / 100 > r["need"]]
    return E.per_night(c, key=lambda r: (r["dog_read"], (r["eff_p"] or 0) - r["p_market"]), cap=2)


def gap_play(rows):
    c = [r for r in DOGP(rows) if not r["trap"] and r.get("eff_p") is not None and r["eff_p"] > 0.5
         and r["eff_p"] - r["p_market"] >= 0.15 and (r.get("dog_read") or -9) >= 4]
    return E.per_night(c, key=lambda r: r["eff_p"] - r["p_market"], cap=99)


def fav_ok(r):
    if r["trap"] or r["fighting"] or r["own"] is None or r["edge_own"] <= 0:
        return False
    if r["nd"] and (not r["home"] or r["neu"]):
        return False                                   # the Nov-Dec road / neutral favorite fade
    if r.get("eff_p") is not None and r["eff_p"] - r["p_market"] <= -0.03:
        return False                                   # the efficiency read against it
    return True


def fav_slot(rows):
    c = [r for r in FAVP(rows) if fav_ok(r) and r["wp"] >= 0.56 and 0.01 <= r["wp"] - r["need"] <= 0.05]
    return E.per_night(c, key=lambda r: r["wp"] * r["dec"] - 1, cap=1)


def by_mn(name, fn, pool):
    print(f"\n== {name}")
    for lab, lo, hi in (("mn 0", 0, 0), ("mn 1", 1, 1), ("mn 2", 2, 2), ("mn 3", 3, 3), ("mn 1-3", 1, 3), ("mn 2-3", 2, 3),
                        ("early ALL 0-3", 0, 3), ("4+ (as wired)", 4, 999)):
        rows = [r for r in ML if lo <= r["mn"] <= hi]
        E.rec(lab, fn(rows), pool=pool([r for r in rows]))


if __name__ == "__main__":
    by_mn("(a1) THE DOG SLOT (dog read 4+, best 2 a night)", dog_slot, lambda rows: DOGP(rows))
    by_mn("(a1') the dog slot at a dog read of 6+", lambda rows: dog_slot(rows, 6), lambda rows: DOGP(rows))
    by_mn("(a2) THE GAP PLAY (efficiency read 15+ over, backed, no fade)", gap_play, lambda rows: DOGP(rows))
    by_mn("(a3) THE FAVORITE SLOT (-120..-150, best 1 a day)", fav_slot, lambda rows: FAVP(rows))

    print("\n== (b) THE MONEYLINE FAVORITE LEAN CELL -150..-130")
    for lab, rows in (("early 0-3", EARLY), ("4+", LATE), ("ALL", ML)):
        band = FAVP(rows, -150, -130)
        E.rec(f"{lab}: every favorite -150..-130 (the band)", band)
        lp = [r for r in band if r.get("lean_any")]
        E.rec(f"{lab}: the lean rule's pool (lean_any)", lp, pool=band)
        E.rec(f"{lab}: the board's leans (lean)", [r for r in band if r.get("lean")], pool=band)
        vb = [r for r in lp if r["own"] is not None and r["own"] - r["need"] >= 0.01 and not r["fighting"] and not r["trap"]]
        E.rec(f"{lab}: lean pool + the value-play bar (own 1+ pt over)", vb, pool=band)
        E.rec(f"{lab}: lean pool + value bar, real edge (own 3+ pts over)", [r for r in vb if r["own"] - r["need"] >= 0.03], pool=band)
        E.rec(f"{lab}: lean pool + value bar, home only", [r for r in vb if r["home"] and not r["neu"]], pool=band)
        E.rec(f"{lab}: lean pool, home, no fade (fav_ok)", [r for r in lp if fav_ok(r)], pool=band)

    print("\n== (c) LAST SEASON CARRIED IN: the efficiency read alone, early window")
    for lab, rows in (("early 0-3", EARLY), ("4+", LATE)):
        fv = FAVP(rows, -150, -101)
        dg = DOGP(rows)
        for g0, g1 in ((-1, -0.03), (-0.03, 0.03), (0.03, 0.08), (0.08, 1)):
            E.rec(f"{lab}: fav -101..-150, eff - no-vig in [{g0:+.2f},{g1:+.2f})",
                  [r for r in fv if r["eff_p"] is not None and g0 <= r["eff_p"] - r["p_market"] < g1], pool=fv)
        for g0, g1 in ((-1, 0), (0, 0.08), (0.08, 0.15), (0.15, 1)):
            E.rec(f"{lab}: dog +100..+350, eff - no-vig in [{g0:+.2f},{g1:+.2f})",
                  [r for r in dg if r["eff_p"] is not None and g0 <= r["eff_p"] - r["p_market"] < g1], pool=dg)
        E.rec(f"{lab}: dog, eff backs it (over 50%)", [r for r in dg if (r["eff_p"] or 0) > 0.5], pool=dg)
        for v, f in (("home", lambda r: r["home"] and not r["neu"]), ("road", lambda r: not r["home"] and not r["neu"]),
                     ("neutral", lambda r: r["neu"])):
            E.rec(f"{lab}: every dog +100..+350, {v}", [r for r in dg if f(r)])
            E.rec(f"{lab}: every fav -101..-150, {v}", [r for r in fv if f(r)])
            E.rec(f"{lab}: every fav -151..-400, {v}", [r for r in FAVP(rows, -400, -151) if f(r)])
        E.rec(f"{lab}: the big home favorite -400..-1000 (the buy game)", [r for r in FAVP(rows, -1000, -400) if r["home"] and not r["neu"]])
        E.rec(f"{lab}: the road dog +350..+1000 in the buy game", [r for r in rows if 350 < r["odds"] <= 1000 and not r["home"] and not r["neu"]])
    print(f"\ncells looked at: {E.CELLS[0]}")
