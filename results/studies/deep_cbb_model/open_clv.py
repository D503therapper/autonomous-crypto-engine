"""Does the model call the market's move? For every 2023-25 game with ESPN's OPEN and close moneyline: the model's edge
vs the open (no-vig), and how far the close moved toward the model's side (closing-line value). The open data never
touched a fit (the model's settings were tuned on 2018-22 margins; the calibration on 2018-22 results), so all three
seasons are out of sample. Usage: python open_clv.py PREDS.pkl [out.txt]"""
import math
import pickle
import sys
from collections import defaultdict

import numpy as np

import lib
from analyze import fit_logit, sig, tiers, game_tier


def main(path):
    gs, _ = lib.data()
    preds = pickle.load(open(path, "rb"))
    finals = pickle.load(open(path.replace(".pkl", "_finals.pkl"), "rb"))
    tr = tiers(gs, finals)
    cal = [g for g in gs if g["season"] in lib.TRAIN and g["id"] in preds and g["hs"] != g["as_"]]
    w = fit_logit(np.array([[1.0, preds[g["id"]]["mh"]] for g in cal]),
                  np.array([1.0 if g["hs"] > g["as_"] else 0.0 for g in cal]))
    season_start = {}
    for g in gs:
        season_start.setdefault(g["season"], g["night"])
    out = []
    P = out.append
    cells = defaultdict(list)
    for g in gs:
        if g["season"] not in lib.HELD or g["id"] not in preds or None in (g["ml_h"], g["ml_a"], g["mlo_h"], g["mlo_a"]):
            continue
        if g["hs"] == g["as_"]:
            continue
        p = preds[g["id"]]
        pm = float(sig(w[0] + w[1] * p["mh"]))
        po = lib.nv(g["mlo_h"], g["mlo_a"])
        pc = lib.nv(g["ml_h"], g["ml_a"])
        side_h = pm > po
        e = (pm - po) if side_h else (po - pm)
        clv = (pc - po) if side_h else (po - pc)
        oo = g["mlo_h"] if side_h else g["mlo_a"]
        oc = g["ml_h"] if side_h else g["ml_a"]
        won = (g["hs"] > g["as_"]) == side_h
        if not (-400 <= oo <= 350):
            continue
        d = g["night"] - season_start[g["season"]]
        stg = "openwk" if d <= 7 else lib.phase(g)
        fav = "fav" if oo < 0 else "dog"
        gn = min(p["gn_h"], p["gn_a"])
        for E in (0.0, 0.03, 0.05, 0.08, 0.12):
            if e < E:
                continue
            for key in ("all", fav, "st:" + stg, "tier:" + game_tier(tr, g), f"{fav} st:{stg}",
                        "gn<6" if gn < 6 else "gn6+"):
                pcs = pc if side_h else 1 - pc
                cells[(E, key)].append((g["season"], clv, lib.ml_profit(oo, won), lib.ml_profit(oc, won),
                                        pcs * lib.dec(oo) - 1))
    P("edge vs OPEN >= E | cell | n | mean CLV (no-vig pts the close moved our way) | ROI at the OPEN | ROI at the CLOSE "
      "| the close-implied EV (the close's no-vig chance x the open's price - 1: what the bet was worth if the close is "
      "right, the low-noise read) | by season (CLV / open ROI)")
    for (E, key) in sorted(cells):
        v = cells[(E, key)]
        if len(v) < 60:
            continue
        c = np.array([x[1] for x in v])
        ro = np.array([x[2] for x in v])
        rc = np.array([x[3] for x in v])
        zc = c.mean() / (c.std() / math.sqrt(len(c)))
        ev = np.array([x[4] for x in v])
        evs = " ".join(f"{np.mean([x[4] for x in v if x[0] == s]):+.1%}" for s in lib.HELD if any(x[0] == s for x in v))
        per = " ".join(f"{s}:{np.mean([x[1] for x in v if x[0] == s]) * 100:+.2f}/{np.mean([x[2] for x in v if x[0] == s]):+.1%}"
                       f"({sum(1 for x in v if x[0] == s)})" for s in lib.HELD if any(x[0] == s for x in v))
        P(f"E>={E:.2f} {key:<22} n {len(v):5d} CLV {c.mean() * 100:+.2f} pts (z {zc:+.1f}) | open {ro.mean():+.1%} | "
          f"close {rc.mean():+.1%} | CLOSE-IMPLIED EV at the open {ev.mean():+.2%} (+/- {ev.std() / math.sqrt(len(ev)):.2%}; {evs}) | {per}")
    txt = "\n".join(out)
    print(txt)
    return txt


if __name__ == "__main__":
    t = main(sys.argv[1])
    if len(sys.argv) > 2:
        open(sys.argv[2], "w").write(t + "\n")
