"""Calibration of the model's win chance (fit on 2018-22) on the held-out seasons 2023-25: deciles of the home win
chance -> games, mean predicted, actual. Priced games and every D1 game. Writes calib_out.txt."""
import os
import pickle

import numpy as np

import lib
from analyze import fit_logit, sig

gs, _ = lib.data()
preds = pickle.load(open(os.path.join(lib.CACHE, "deep_final.pkl"), "rb"))
cal = [g for g in gs if g["season"] in lib.TRAIN and g["id"] in preds and g["hs"] != g["as_"]]
w = fit_logit(np.array([[1.0, preds[g["id"]]["mh"]] for g in cal]), np.array([1.0 if g["hs"] > g["as_"] else 0.0 for g in cal]))
out = [f"P(home) = sig({w[0]:+.4f} + {w[1]:.4f} x margin), fit on 2018-22"]
for label, sel in (("held-out PRICED games", lambda g: g["ml_h"] is not None),
                   ("held-out every game", lambda g: True)):
    rows = [g for g in gs if g["season"] in lib.HELD and g["id"] in preds and g["hs"] != g["as_"] and sel(g)]
    p = np.array([float(sig(w[0] + w[1] * preds[g["id"]]["mh"])) for g in rows])
    y = np.array([1.0 if g["hs"] > g["as_"] else 0.0 for g in rows])
    out.append(f"\n{label}: n {len(rows)}, log loss {lib.logloss(p, y):.4f}, Brier {np.mean((p - y) ** 2):.4f}")
    qs = np.quantile(p, np.linspace(0, 1, 11))
    for i in range(10):
        m = (p >= qs[i]) & (p <= qs[i + 1]) if i == 9 else (p >= qs[i]) & (p < qs[i + 1])
        out.append(f"  {qs[i]:.2f}-{qs[i + 1]:.2f}: n {m.sum():5d} predicted {p[m].mean():.3f} actual {y[m].mean():.3f}")
txt = "\n".join(out)
print(txt)
open(os.path.join(lib.OUT, "calib_out.txt"), "w").write(txt + "\n")
