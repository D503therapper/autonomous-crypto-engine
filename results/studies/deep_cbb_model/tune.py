"""Tune the model's settings on the TRAIN seasons only (2018-22 starts; 2016-17 = burn-in for the priors).
Coordinate descent: one setting at a time over a grid, 4 processes. Objective = the model's own margin RMSE on
priced train games (no market input). Also prints the 2021-22 (box-score seasons) RMSE and the totals RMSE.
Writes tune_out.txt."""
import json
import os
import sys
from multiprocessing import Pool

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

import lib  # noqa: E402

GS = CONF = None


def init():
    global GS, CONF
    gs, _ = lib.data()
    GS = [g for g in gs if g["season"] <= 2022]
    CONF = lib.conferences(gs)


def score(prm):
    preds, _ = lib.run(GS, CONF, prm)
    out = {}
    for name, ss in (("train", lib.TRAIN), ("box", (2021, 2022)), ("early", lib.TRAIN)):
        m, t, e2 = [], [], []
        for g in GS:
            if g["season"] not in ss or g["spread"] is None or g["id"] not in preds:
                continue
            p = preds[g["id"]]
            if name == "early" and min(p["gn_h"], p["gn_a"]) >= 10:
                continue
            m.append((g["hs"] - g["as_"]) - p["mh"])
            if g["total"] is not None:
                t.append(g["hs"] + g["as_"] - p["tot"])
        out[name] = float(np.sqrt(np.mean(np.square(m))))
        out[name + "_tot"] = float(np.sqrt(np.mean(np.square(t))))
    return prm, out


GRID = {
    "prior_fade": [0.0, 0.5, 1.0],
    "nond1_w": [0.25, 0.5, 1.0],
    "prev2_w": [0.0, 0.2, 0.35],
    "tempo_prior": [2, 6, 15],
    "tempo_shrink": [0.5, 0.75, 0.9],
    "prior_games": [4, 6, 9],
    "shrink": [0.7, 0.8, 0.9],
    "halflife": [60, 120, 0],
    "blow_cap": [20, 25, 30, 0],
}

if __name__ == "__main__":
    base = dict(lib.DEFAULT)
    if len(sys.argv) > 1:
        base.update(json.loads(sys.argv[1]))
    log = open(os.path.join(lib.OUT, "tune_out.txt"), "a")
    rounds = 1
    with Pool(4, initializer=init) as pool:
        for r in range(rounds):
            for key, vals in GRID.items():
                tries = [{**base, key: v} for v in vals]
                res = pool.map(score, tries)
                obj = "box_tot" if key.startswith("tempo") else "train"
                best = min(res, key=lambda x: x[1][obj])
                for prm, o in res:
                    line = (f"r{r} {key}={prm[key]}: train {o['train']:.3f} box {o['box']:.3f} early(<10) "
                            f"{o['early']:.3f} | totals train {o['train_tot']:.3f} box {o['box_tot']:.3f}")
                    print(line, flush=True)
                    log.write(line + "\n")
                base[key] = best[0][key]
                log.write(f"-> {key} = {base[key]}\n")
                log.flush()
                print("->", key, base[key], flush=True)
    log.write("FINAL " + json.dumps(base) + "\n")
    print("FINAL", json.dumps(base))
