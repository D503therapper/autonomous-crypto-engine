"""THE MODEL x THE ENGINE'S BUILT COLLEGE HOOPS WEIGHTS: inside each built cell, does the efficiency model's side (vs the
close's no-vig) separate winners from losers? Cells: (1) the Nov-Dec -101..-150 favorite away from home (built -3,
11/3 B) - its home / neutral dog across; (2) the early road dog +100..+350 in its first 3 games (built -2, 11/3 A);
(3) the big home favorite laying 12+ (the spread guard, 11/3 A) - its dog ATS; (4) the -120..-150 'Lock band' favorite.
TRAIN 2018-22 / HELD 2023-25. Usage: python s_combos.py [out.txt]"""
import math
import os
import pickle
import sys
from collections import defaultdict

import numpy as np

import lib
from analyze import fit_logit, sig


def main():
    gs, _ = lib.data()
    preds = pickle.load(open(os.path.join(lib.CACHE, "deep_final.pkl"), "rb"))
    cal = [g for g in gs if g["season"] in lib.TRAIN and g["id"] in preds and g["hs"] != g["as_"]]
    w = fit_logit(np.array([[1.0, preds[g["id"]]["mh"]] for g in cal]),
                  np.array([1.0 if g["hs"] > g["as_"] else 0.0 for g in cal]))
    cells = defaultdict(lambda: defaultdict(list))
    for g in gs:
        if g["id"] not in preds or g["season"] not in lib.TRAIN + lib.HELD or g["hs"] == g["as_"]:
            continue
        p = preds[g["id"]]
        md = g["start"][5:7]
        if g["ml_h"] is not None and g["ml_a"] is not None:
            pm = float(sig(w[0] + w[1] * p["mh"]))
            mk = lib.nv(g["ml_h"], g["ml_a"])
            for side_h in (True, False):
                odds = g["ml_h"] if side_h else g["ml_a"]
                oo = g["ml_a"] if side_h else g["ml_h"]
                won = (g["hs"] > g["as_"]) == side_h
                e = (pm - mk) * (1 if side_h else -1)
                agree = "model agrees (edge>=+3)" if e >= 0.03 else "model against (edge<=-3)" if e <= -0.03 else "model ~0"
                gn = p["gn_h"] if side_h else p["gn_a"]
                # (1) the away small favorite Nov-Dec: we look at the FAVORITE (the side the weight fades)
                if -150 <= odds <= -101 and (g["neutral"] or not side_h) and md in ("11", "12"):
                    cells["(1) Nov-Dec away small fav ML: " + agree][g["season"]].append(lib.ml_profit(odds, won))
                    cells["(1) Nov-Dec away small fav ML: all"][g["season"]].append(lib.ml_profit(odds, won))
                # (2) the early road dog
                if 100 <= odds <= 350 and not side_h and not g["neutral"] and gn < 3 and g["stype"] == "2":
                    cells["(2) early road dog ML games 1-3: " + agree][g["season"]].append(lib.ml_profit(odds, won))
                    cells["(2) early road dog ML games 1-3: all"][g["season"]].append(lib.ml_profit(odds, won))
                # (4) Lock band
                if -150 <= odds <= -120:
                    cells["(4) -120..-150 fav ML: " + agree][g["season"]].append(lib.ml_profit(odds, won))
        if g["spread"] is not None and g["spread"] <= -12 and not g["neutral"] and g["sp_a_odds"]:
            dd = p["mh"] + g["spread"]
            res = -(g["hs"] - g["as_"] + g["spread"])
            pl = lib.ats_profit(res, g["sp_a_odds"])
            k = "model on the dog (gap>=2)" if dd <= -2 else "model on the fav (gap>=2)" if dd >= 2 else "model ~line"
            cells["(3) the dog vs a 12+ home fav ATS: " + k][g["season"]].append(pl)
            cells["(3) the dog vs a 12+ home fav ATS: all"][g["season"]].append(pl)
    out = []
    for c in sorted(cells):
        by = cells[c]
        tv = [x for s in lib.TRAIN for x in by.get(s, [])]
        hv = [x for s in lib.HELD for x in by.get(s, [])]
        ut = sum(1 for s in lib.TRAIN if by.get(s) and sum(by[s]) > 0)
        uh = sum(1 for s in lib.HELD if by.get(s) and sum(by[s]) > 0)
        z = np.mean(hv) / (np.std(hv) / math.sqrt(len(hv))) if len(hv) > 2 else 0
        out.append(f"{c:<62} TRAIN {np.mean(tv) if tv else 0:+6.1%} on {len(tv):5d} ({ut}/5) | HELD "
                   f"{np.mean(hv) if hv else 0:+6.1%} on {len(hv):5d} ({uh}/3, z {z:+.1f})")
    txt = "\n".join(out)
    print(txt)
    return txt


if __name__ == "__main__":
    t = main()
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(t + "\n")
