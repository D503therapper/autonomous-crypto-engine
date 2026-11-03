"""THE SLIGHT FAVORITE THE MODEL DOESN'T BELIEVE (s_combos (4) + the hunt's short-dog cell, two faces of one thing):
a college hoops -101..-150 favorite whose efficiency-model chance sits 3+ points UNDER the close's no-vig. The checks a
fake edge fails: the base (every slight favorite), a DOSE (does a bigger disagreement lose more?), the open price
(2023-25), the lag-2 model (ratings 2 nights old), the old Elo raw read in the same seat, every cut (venue / stage /
price / games played / tier), the overlap with the built Nov-Dec away-favorite weight, and the dog across.
Usage: python s_slight_fav.py [out.txt]"""
import math
import os
import pickle
import sys
from collections import defaultdict

import numpy as np

import lib
from analyze import tiers, game_tier
from s_short_dog import calib, fmt

C = lib.CACHE


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
    from analyze import sig
    for g in gs:
        if g["id"] not in preds or g["hs"] == g["as_"] or g["ml_h"] is None or g["ml_a"] is None or g["season"] < 2018:
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
            if not (-150 <= odds <= -101):
                continue
            dog_odds = g["ml_a"] if side_h else g["ml_h"]
            won = (g["hs"] > g["as_"]) == side_h
            m = mk if side_h else 1 - mk
            e = (pm if side_h else 1 - pm) - m
            e2 = (pl2 if side_h else 1 - pl2) - m
            eo = None if oe is None else (oe if side_h else 1 - oe) - m
            pl = lib.ml_profit(odds, won)
            s = g["season"]
            ven = "neutral" if g["neutral"] else ("home" if side_h else "road")
            away_w = (g["neutral"] or not side_h) and g["start"][5:7] in ("11", "12")
            cells["base: every -101..-150 favorite"].append((s, pl))
            band = ("model AGREES 3+" if e >= 0.03 else "model -3..+3" if e > -0.03 else "model under 3-6" if e > -0.06
                    else "model under 6-10" if e > -0.10 else "model under 10+")
            cells["dose: " + band].append((s, pl))
            # data check: the moneyline favorite and the spread favorite agree (a swapped / stale row would fake a fade)
            sp_ = g["spread"]
            consistent = sp_ is not None and abs(sp_) >= 1 and (sp_ < 0) == side_h
            if e <= -0.03:
                cells["THE CELL, rows whose spread agrees (clean)" if consistent else
                      "THE CELL, rows with no / a disagreeing spread"].append((s, pl))
            if e > -0.03 and consistent:
                cells["clean rows, model NOT 3+ under (the base)"].append((s, pl))
            if e <= -0.03:
                cells["THE CELL: model 3+ under the price"].append((s, pl))
                cells["  the DOG across (bet it)"].append((s, lib.ml_profit(dog_odds, not won)))
                cells["  cell " + ven].append((s, pl))
                cells["  cell st:" + stg].append((s, pl))
                cells["  cell " + ("-101..-119" if odds >= -119 else "-120..-150")].append((s, pl))
                cells["  cell " + ("gn<6" if gn < 6 else "gn6-15" if gn < 16 else "gn16+")].append((s, pl))
                cells["  cell tier:" + game_tier(tr, g)].append((s, pl))
                cells["  cell OUTSIDE the built Nov-Dec away-fav weight" if not away_w else
                      "  cell INSIDE the built Nov-Dec away-fav weight"].append((s, pl))
                if g["mlo_h"] is not None and g["mlo_a"] is not None:
                    oo = g["mlo_h"] if side_h else g["mlo_a"]
                    cells["  cell at the OPEN price (2023-25)"].append((s, lib.ml_profit(oo, won)))
                    cells["  cell at the close, same games"].append((s, pl))
            if e2 <= -0.03:
                cells["LAG-2 model 3+ under (ratings 2 nights old)"].append((s, pl))
            if eo is not None and eo <= -0.03:
                cells["OLD Elo raw read 3+ under (same seat)"].append((s, pl))
            if eo is not None and eo <= -0.03 and e <= -0.03:
                cells["model AND old Elo both 3+ under"].append((s, pl))
            if e <= -0.03 and (eo is None or eo > -0.03):
                cells["model 3+ under, old Elo not"].append((s, pl))
            if eo is not None and eo <= -0.03 and e > -0.03:
                cells["old Elo 3+ under, model not"].append((s, pl))
    out = [fmt(v, k) for k, v in cells.items()]
    txt = "\n".join(out)
    print(txt)
    return txt


if __name__ == "__main__":
    t = main()
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(t + "\n")
