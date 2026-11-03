"""FIRST HALVES - a thinner market (ESPN's closing 1st-half spread 2018-25, ~3,900 games a season; 1st-half scores from
the line scores). Two signals, both fit on TRAIN (2018-22) and graded on 2023 / 2024 / 2025:
  S1 THE STRUCTURE - the full-game line says a 1st-half line of k x spread (+ a home / favorite shape fit on train);
     when the posted 1st-half line sits N+ points off that, bet the 1st half against the posted line.
  S2 THE MODEL - the efficiency model's margin x f (+ the same fit) vs the posted 1st-half line.
  S3 BOTH - the regression of the 1st-half result on the 1st-half line, the full line and the model, fit on TRAIN.
Usage: python s_first_half.py [out.txt]"""
import math
import os
import pickle
import sys
from collections import defaultdict

import numpy as np

import lib


def main():
    gs, _ = lib.data()
    preds = pickle.load(open(os.path.join(lib.CACHE, "deep_final.pkl"), "rb"))
    rows = [g for g in gs if g["id"] in preds and g["h1_sp"] is not None and g["spread"] is not None
            and g["h1_h"] is not None and g["h1_a"] is not None and g["h1_sp_h_odds"] and g["h1_sp_a_odds"]
            and g["season"] in lib.TRAIN + lib.HELD]
    out = []
    P = out.append
    y = np.array([g["h1_h"] - g["h1_a"] for g in rows], float)
    h1 = np.array([-g["h1_sp"] for g in rows])
    fs = np.array([-g["spread"] for g in rows])
    md = np.array([preds[g["id"]]["mh"] for g in rows])
    tr = np.array([g["season"] in lib.TRAIN for g in rows])
    k = float(np.sum(h1[tr] * fs[tr]) / np.sum(fs[tr] ** 2))
    P(f"games: {len(rows)} (train {tr.sum()}); 1st-half line = {k:.3f} x full line on train "
      f"(rmse {np.sqrt(np.mean((h1[tr] - k * fs[tr]) ** 2)):.2f})")
    X = np.stack([np.ones(len(rows)), h1, fs, md], 1)
    b, *_ = np.linalg.lstsq(X[tr], y[tr], rcond=None)
    P(f"TRAIN fit: 1H margin = {b[0]:+.2f} + {b[1]:.3f} x 1H line + {b[2]:.3f} x full line + {b[3]:.3f} x model margin")
    for s in lib.TRAIN + lib.HELD:
        m = np.array([g["season"] == s for g in rows])
        r0 = np.sqrt(np.mean((y[m] - h1[m]) ** 2))
        r1 = np.sqrt(np.mean((y[m] - X[m] @ b) ** 2))
        bs, *_ = np.linalg.lstsq(X[m], y[m], rcond=None)
        P(f"  {s}: n {m.sum()} rmse 1H line {r0:.3f} | train fit {r1:.3f} | season's own weights: 1H line {bs[1]:+.2f} "
          f"full {bs[2]:+.2f} model {bs[3]:+.2f}")
    # signals
    b1, *_ = np.linalg.lstsq(np.stack([np.ones(tr.sum()), fs[tr]], 1), y[tr], rcond=None)
    b2, *_ = np.linalg.lstsq(np.stack([np.ones(tr.sum()), md[tr]], 1), y[tr], rcond=None)
    sig = {"S1 structure": b1[0] + b1[1] * fs - h1, "S2 model": b2[0] + b2[1] * md - h1, "S3 both": X @ b - h1}
    cells = defaultdict(lambda: defaultdict(list))
    for name, d in sig.items():
        for i, g in enumerate(rows):
            side_h = d[i] > 0
            res = (y[i] - h1[i]) * (1 if side_h else -1)
            pl = lib.ats_profit(res, g["h1_sp_h_odds"] if side_h else g["h1_sp_a_odds"])
            fav = (g["h1_sp"] < 0) == side_h
            for n in (0.5, 1.0, 1.5, 2.0, 3.0):
                if abs(d[i]) >= n:
                    cells[f"{name} |gap|>={n}"][g["season"]].append(pl)
                    cells[f"{name} |gap|>={n} {'fav' if fav else 'dog'}"][g["season"]].append(pl)
    P("\n1st-half ATS, flat 1u at the posted 1st-half odds")
    for c in sorted(cells):
        by = cells[c]
        tv = [x for s in lib.TRAIN for x in by.get(s, [])]
        hv = [x for s in lib.HELD for x in by.get(s, [])]
        if len(tv) + len(hv) < 100:
            continue
        ut = sum(1 for s in lib.TRAIN if by.get(s) and sum(by[s]) > 0)
        uh = sum(1 for s in lib.HELD if by.get(s) and sum(by[s]) > 0)
        z = np.mean(hv) / (np.std(hv) / math.sqrt(len(hv))) if len(hv) > 2 else 0
        per = " ".join(f"{s}:{np.mean(by[s]):+.1%}/{len(by[s])}" for s in lib.HELD if by.get(s))
        P(f"{c:<34} TRAIN {np.mean(tv):+6.1%} on {len(tv):5d} ({ut}/5) | HELD {np.mean(hv):+6.1%} on {len(hv):5d} "
          f"({uh}/3, z {z:+.1f}) [{per}]")
    txt = "\n".join(out)
    print(txt)
    return txt


if __name__ == "__main__":
    t = main()
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(t + "\n")
