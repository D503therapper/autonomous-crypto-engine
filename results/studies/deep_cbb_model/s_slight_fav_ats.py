"""The spread face of s_slight_fav: a college hoops favorite laying 1-9.5 whose model margin is N+ points SHORT of the
spread (the model says it wins by less than it's laying) - its ATS, by gap, TRAIN 2018-22 / HELD 2023-25; and the dog
across. Usage: python s_slight_fav_ats.py [out.txt]"""
import os
import pickle
import sys
from collections import defaultdict

import lib
from s_short_dog import fmt


def main():
    gs, _ = lib.data()
    preds = pickle.load(open(os.path.join(lib.CACHE, "deep_final.pkl"), "rb"))
    cells = defaultdict(list)
    for g in gs:
        if g["id"] not in preds or g["season"] < 2018 or g["spread"] is None or not g["sp_h_odds"] or not g["sp_a_odds"]:
            continue
        sp = g["spread"]
        if sp == 0 or abs(sp) > 9.5:
            continue
        fav_h = sp < 0
        lay = abs(sp)
        mfav = preds[g["id"]]["mh"] * (1 if fav_h else -1)        # model margin for the favorite
        short = lay - mfav                                          # + = the model says it wins by less than it lays
        res = (g["hs"] - g["as_"] + sp) * (1 if fav_h else -1)
        pf = lib.ats_profit(res, g["sp_h_odds"] if fav_h else g["sp_a_odds"])
        pd = lib.ats_profit(-res, g["sp_a_odds"] if fav_h else g["sp_h_odds"])
        b = ("model 3+ OVER the spread" if short <= -3 else "model within 3" if short < 3 else
             "model 3-5 SHORT" if short < 5 else "model 5+ SHORT")
        cells["fav ATS: " + b].append((g["season"], pf))
        if short >= 3:
            cells["fav ATS: model 3+ SHORT (all)"].append((g["season"], pf))
            cells["  dog across ATS: model 3+ short on the fav"].append((g["season"], pd))
            cells["  fav ATS 3+ short, laying " + ("1-4.5" if lay < 5 else "5-9.5")].append((g["season"], pf))
    out = [fmt(v, k) for k, v in sorted(cells.items())]
    txt = "\n".join(out)
    print(txt)
    return txt


if __name__ == "__main__":
    t = main()
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(t + "\n")
