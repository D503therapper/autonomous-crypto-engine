"""THE OPEN, market-anchored: p = sig(logit(open no-vig) + w x (logit(model) - logit(open))), w fit LEAVE-ONE-SEASON-OUT
on 2023-25 (the only seasons with ESPN's open; the model's settings and calibration come from 2018-22, so the open
never touched them). Graded on the left-out season: log loss vs the open alone and vs the close; the bet = the side
whose p beats the OPEN price's own implied chance (vig in) by T, ML -400..+350, flat 1u at the open price.
Usage: python open_anchor.py PREDS.pkl [out.txt]"""
import math
import pickle
import sys
from collections import defaultdict

import numpy as np

import lib
from analyze import fit_logit, sig, logit, tiers, game_tier

FEATS = ("base",)


def main(path):
    gs, _ = lib.data()
    preds = pickle.load(open(path, "rb"))
    finals = pickle.load(open(path.replace(".pkl", "_finals.pkl"), "rb"))
    tr = tiers(gs, finals)
    cal = [g for g in gs if g["season"] in lib.TRAIN and g["id"] in preds and g["hs"] != g["as_"]]
    wc = fit_logit(np.array([[1.0, preds[g["id"]]["mh"]] for g in cal]),
                   np.array([1.0 if g["hs"] > g["as_"] else 0.0 for g in cal]))
    season_start = {}
    for g in gs:
        season_start.setdefault(g["season"], g["night"])
    rows = []
    for g in gs:
        if g["season"] not in lib.HELD or g["id"] not in preds or g["hs"] == g["as_"]:
            continue
        if None in (g["ml_h"], g["ml_a"], g["mlo_h"], g["mlo_a"]):
            continue
        p = preds[g["id"]]
        pm = float(sig(wc[0] + wc[1] * p["mh"]))
        po, pc = lib.nv(g["mlo_h"], g["mlo_a"]), lib.nv(g["ml_h"], g["ml_a"])
        d = g["night"] - season_start[g["season"]]
        rows.append(dict(g=g, pm=pm, po=po, pc=pc, y=1.0 if g["hs"] > g["as_"] else 0.0,
                         stage="openwk" if d <= 7 else lib.phase(g), tier=game_tier(tr, g),
                         gn=min(p["gn_h"], p["gn_a"]),
                         vig=1 / lib.dec(g["mlo_h"]) + 1 / lib.dec(g["mlo_a"]) - 1,
                         vigc=1 / lib.dec(g["ml_h"]) + 1 / lib.dec(g["ml_a"]) - 1))
    out = []
    P = out.append
    P(f"games with open + close 2023-25: {len(rows)}; mean overround open {np.mean([r['vig'] for r in rows]):.2%} "
      f"close {np.mean([r['vigc'] for r in rows]):.2%}")
    cells = defaultdict(list)
    for s in lib.HELD:
        trn = [r for r in rows if r["g"]["season"] != s]
        tst = [r for r in rows if r["g"]["season"] == s]
        X = np.array([[logit(r["pm"]) - logit(r["po"])] for r in trn])
        w = fit_logit(X, [r["y"] for r in trn], off=[logit(r["po"]) for r in trn])[0]
        Xc = np.array([[logit(r["pm"]) - logit(r["pc"])] for r in trn])
        wcl = fit_logit(Xc, [r["y"] for r in trn], off=[logit(r["pc"]) for r in trn])[0]
        # how much of the gap the close takes (least squares on logits)
        dx = np.array([logit(r["pm"]) - logit(r["po"]) for r in trn])
        dy = np.array([logit(r["pc"]) - logit(r["po"]) for r in trn])
        mv = float(np.sum(dx * dy) / np.sum(dx * dx))
        y = [r["y"] for r in tst]
        ph = [float(sig(logit(r["po"]) + w * (logit(r["pm"]) - logit(r["po"])))) for r in tst]
        phc = [float(sig(logit(r["pc"]) + wcl * (logit(r["pm"]) - logit(r["pc"])))) for r in tst]
        P(f"{s}: w(open) {w:+.3f} w(close) {wcl:+.3f} close moves {mv:.1%} of the model-open gap (fit on the other two) | "
          f"logloss open {lib.logloss([r['po'] for r in tst], y):.4f} open+model {lib.logloss(ph, y):.4f} | close "
          f"{lib.logloss([r['pc'] for r in tst], y):.4f} close+model {lib.logloss(phc, y):.4f} | model alone "
          f"{lib.logloss([r['pm'] for r in tst], y):.4f} (n {len(tst)})")
        for r, p_ in zip(tst, ph):
            g = r["g"]
            for side, pp, odds, oc, won in (("h", p_, g["mlo_h"], g["ml_h"], r["y"] == 1.0),
                                             ("a", 1 - p_, g["mlo_a"], g["ml_a"], r["y"] == 0.0)):
                if not (-400 <= odds <= 350):
                    continue
                e = pp - 1 / lib.dec(odds)
                band = "dog" if odds > 0 else "fav"
                for T in (0.0, 0.01, 0.02, 0.03, 0.05):
                    if e >= T:
                        for k in ("all", band, "st:" + r["stage"], f"{band} st:{r['stage']}", "tier:" + r["tier"],
                                  "gn<6" if r["gn"] < 6 else "gn6+"):
                            cells[(T, k)].append((s, lib.ml_profit(odds, won), lib.ml_profit(oc, won),
                                                  (lib.nv(g["ml_h"], g["ml_a"]) - lib.nv(g["mlo_h"], g["mlo_a"])) *
                                                  (1 if side == "h" else -1)))
    P("\nBET AT THE OPEN when the open+model chance beats the open price (vig in) by T - flat 1u, left-out seasons only")
    for (T, k) in sorted(cells):
        v = cells[(T, k)]
        if len(v) < 50:
            continue
        ro = np.array([x[1] for x in v])
        z = ro.mean() / (ro.std() / math.sqrt(len(ro)))
        per = " ".join(f"{s}:{np.mean([x[1] for x in v if x[0] == s]):+.1%}/{sum(1 for x in v if x[0] == s)}"
                       for s in lib.HELD if any(x[0] == s for x in v))
        up = sum(1 for s in lib.HELD if any(x[0] == s for x in v) and np.sum([x[1] for x in v if x[0] == s]) > 0)
        P(f"T>={T:.2f} {k:<24} n {len(v):5d} open ROI {ro.mean():+6.1%} (z {z:+.1f}, {up}/3 up) | same side at the close "
          f"{np.mean([x[2] for x in v]):+6.1%} | CLV {np.mean([x[3] for x in v]) * 100:+.2f} pts | {per}")
    txt = "\n".join(out)
    print(txt)
    return txt


if __name__ == "__main__":
    t = main(sys.argv[1])
    if len(sys.argv) > 2:
        open(sys.argv[2], "w").write(t + "\n")
