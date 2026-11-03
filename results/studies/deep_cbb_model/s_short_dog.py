"""The one hunt cell with size: the college hoops SHORT DOG (+100..+150) the model likes 3+ points over the close's no-vig.
Five checks + the questions a fake edge fails: the base (every short dog, no model), a DOSE (does a bigger model edge do
better?), the open (2023-25), the lag-2 model (ratings 2 nights stale - what a day-before post could know), venue /
stage / tier / games-played cuts, the old read (Elo) in the same seat, and 2026 so far.
Usage: python s_short_dog.py [out.txt]"""
import math
import os
import pickle
import sys
from collections import defaultdict

import numpy as np

import lib
from analyze import fit_logit, sig, tiers, game_tier

C = lib.CACHE


def calib(gs, preds):
    cal = [g for g in gs if g["season"] in lib.TRAIN and g["id"] in preds and g["hs"] != g["as_"]]
    return fit_logit(np.array([[1.0, preds[g["id"]]["mh"]] for g in cal]),
                     np.array([1.0 if g["hs"] > g["as_"] else 0.0 for g in cal]))


def fmt(v, label):
    by = defaultdict(list)
    for s, x in v:
        by[s].append(x)
    allv = [x for _, x in v]
    tv = [x for s in lib.TRAIN for x in by.get(s, [])]
    hv = [x for s in lib.HELD for x in by.get(s, [])]
    up_t = sum(1 for s in lib.TRAIN if by.get(s) and sum(by[s]) > 0)
    up_h = sum(1 for s in lib.HELD if by.get(s) and sum(by[s]) > 0)
    z = (np.mean(allv) / (np.std(allv) / math.sqrt(len(allv)))) if len(allv) > 2 else 0.0
    per = " ".join(f"{s}:{np.mean(by[s]):+.0%}/{len(by[s])}" for s in sorted(by))
    tr = f"{np.mean(tv):+6.1%} on {len(tv):4d} ({up_t}/5)" if tv else "   n/a"
    he = f"{np.mean(hv):+6.1%} on {len(hv):4d} ({up_h}/3)" if hv else "   n/a"
    return f"{label:<52} ALL {np.mean(allv) if allv else 0:+6.1%} on {len(allv):5d} z {z:+.1f} | TRAIN {tr} | HELD {he} | {per}"


def main():
    gs, _ = lib.data()
    preds = pickle.load(open(os.path.join(C, "deep_final.pkl"), "rb"))
    lag2 = pickle.load(open(os.path.join(C, "deep_final_lag2.pkl"), "rb"))
    finals = pickle.load(open(os.path.join(C, "deep_final_finals.pkl"), "rb"))
    old = pickle.load(open(os.path.join(C, "deep_old_read.pkl"), "rb"))
    tr = tiers(gs, finals)
    w0, w2 = calib(gs, preds), calib(gs, lag2)
    season_start = {}
    for g in gs:
        season_start.setdefault(g["season"], g["night"])
    cells = defaultdict(list)
    for g in gs:
        if g["id"] not in preds or g["hs"] == g["as_"] or g["ml_h"] is None or g["ml_a"] is None:
            continue
        if g["season"] < 2018:
            continue
        p = preds[g["id"]]
        mk = lib.nv(g["ml_h"], g["ml_a"])
        pm = float(sig(w0[0] + w0[1] * p["mh"]))
        pl2 = float(sig(w2[0] + w2[1] * lag2[g["id"]]["mh"]))
        oe = old.get(g["id"], (None, None, None))[1]
        d = g["night"] - season_start[g["season"]]
        stg = "openwk" if d <= 7 else lib.phase(g)
        gn = min(p["gn_h"], p["gn_a"])
        for side_h in (True, False):
            odds = g["ml_h"] if side_h else g["ml_a"]
            if not (100 <= odds <= 150):
                continue
            won = (g["hs"] > g["as_"]) == side_h
            m = mk if side_h else 1 - mk
            e = (pm if side_h else 1 - pm) - m
            e2 = (pl2 if side_h else 1 - pl2) - m
            eo = None if oe is None else (oe if side_h else 1 - oe) - m
            pl = lib.ml_profit(odds, won)
            s = g["season"]
            ven = "neutral" if g["neutral"] else ("home" if side_h else "road")
            cells["base: every short dog +100..+150"].append((s, pl))
            cells["base " + ven].append((s, pl))
            if e < 0:
                cells["model AGAINST (edge < 0)"].append((s, pl))
            elif e < 0.03:
                cells["model edge 0-3"].append((s, pl))
            elif e < 0.06:
                cells["model edge 3-6"].append((s, pl))
            elif e < 0.10:
                cells["model edge 6-10"].append((s, pl))
            else:
                cells["model edge 10+"].append((s, pl))
            if e >= 0.03:
                cells["THE CELL: model edge 3+"].append((s, pl))
                cells["  cell " + ven].append((s, pl))
                cells["  cell st:" + stg].append((s, pl))
                cells["  cell tier:" + game_tier(tr, g)].append((s, pl))
                cells["  cell " + ("gn<6" if gn < 6 else "gn6-15" if gn < 16 else "gn16+")].append((s, pl))
                cells["  cell odds " + ("+100..+120" if odds <= 120 else "+121..+150")].append((s, pl))
                if g["mlo_h"] is not None and g["mlo_a"] is not None:
                    oo = g["mlo_h"] if side_h else g["mlo_a"]
                    cells["  cell at the OPEN price (2023-25)"].append((s, lib.ml_profit(oo, won)))
                    cells["  cell at the close, same games"].append((s, pl))
            if e2 >= 0.03:
                cells["LAG-2 model edge 3+ (ratings 2 nights old)"].append((s, pl))
            if eo is not None and eo >= 0.03:
                cells["OLD Elo raw read edge 3+ (same seat)"].append((s, pl))
            if eo is not None and eo >= 0.03 and e >= 0.03:
                cells["model AND old Elo both 3+"].append((s, pl))
            if e >= 0.03 and (eo is None or eo < 0.03):
                cells["model 3+, old Elo not"].append((s, pl))
    out = [fmt(v, k) for k, v in cells.items()]
    # 2026 so far
    txt = "\n".join(out)
    print(txt)
    return txt


if __name__ == "__main__":
    t = main()
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(t + "\n")
