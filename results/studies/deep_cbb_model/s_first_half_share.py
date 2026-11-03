"""FIRST HALVES, the book's own shape: the 1st-half spread as a share of the full spread (full 3+), by spread size -
bet the 1st-half DOG (and the full-game dog ATS on the same games, for the second check). TRAIN 2018-22, HELD 2023-25.
Usage: python s_first_half_share.py [out.txt]"""
import math
import sys
from collections import defaultdict

import numpy as np

import lib


def main():
    gs, _ = lib.data()
    cells = defaultdict(lambda: defaultdict(list))
    for g in gs:
        if g["season"] not in lib.TRAIN + lib.HELD or g["h1_sp"] is None or g["spread"] is None:
            continue
        if g["h1_h"] is None or not g["h1_sp_h_odds"] or not g["h1_sp_a_odds"] or not g["sp_h_odds"]:
            continue
        sp = g["spread"]
        if abs(sp) < 3:
            continue
        share = g["h1_sp"] / sp
        dog_h = sp > 0
        y1 = (g["h1_h"] - g["h1_a"] + g["h1_sp"]) * (1 if dog_h else -1)
        p1 = lib.ats_profit(y1, g["h1_sp_h_odds"] if dog_h else g["h1_sp_a_odds"])
        yf = (g["hs"] - g["as_"] + sp) * (1 if dog_h else -1)
        pf = lib.ats_profit(yf, g["sp_h_odds"] if dog_h else g["sp_a_odds"])
        sb = "<0.50" if share < 0.50 else "0.50-0.549" if share < 0.55 else "0.55-0.599" if share < 0.60 else "0.60+"
        zb = "full 3-6.5" if abs(sp) < 7 else "full 7-11.5" if abs(sp) < 12 else "full 12+"
        p1f = lib.ats_profit(-y1, g["h1_sp_a_odds"] if dog_h else g["h1_sp_h_odds"])
        pff = lib.ats_profit(-yf, g["sp_a_odds"] if dog_h else g["sp_h_odds"])
        mlf = None
        if g["ml_h"] is not None and g["ml_a"] is not None and g["hs"] != g["as_"]:
            fo = g["ml_a"] if dog_h else g["ml_h"]
            mlf = lib.ml_profit(fo, (g["as_"] > g["hs"]) if dog_h else (g["hs"] > g["as_"]))
        for k in (f"share {sb}", f"share {sb} {zb}"):
            cells["1H dog " + k][g["season"]].append(p1)
            cells["FULL dog " + k][g["season"]].append(pf)
            cells["1H fav " + k][g["season"]].append(p1f)
            cells["FULL fav " + k][g["season"]].append(pff)
            if mlf is not None:
                cells["ML fav " + k][g["season"]].append(mlf)
    out = []
    for c in sorted(cells):
        by = cells[c]
        tv = [x for s in lib.TRAIN for x in by.get(s, [])]
        hv = [x for s in lib.HELD for x in by.get(s, [])]
        if len(tv) + len(hv) < 100:
            continue
        ut = sum(1 for s in lib.TRAIN if by.get(s) and sum(by[s]) > 0)
        uh = sum(1 for s in lib.HELD if by.get(s) and sum(by[s]) > 0)
        z = np.mean(hv) / (np.std(hv) / math.sqrt(len(hv))) if len(hv) > 2 else 0
        out.append(f"{c:<44} TRAIN {np.mean(tv):+6.1%} on {len(tv):5d} ({ut}/5) | HELD {np.mean(hv):+6.1%} on "
                   f"{len(hv):5d} ({uh}/3, z {z:+.1f})")
    txt = "\n".join(out)
    print(txt)
    return txt


if __name__ == "__main__":
    t = main()
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(t + "\n")
