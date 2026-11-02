"""S1 - RETURNING PRODUCTION + TRANSFERS vs the closing line, by part of season (games 1-3 / 4-5 / 6-10 / 11+).

Each game read ONCE (the home side's view, so the two mirror rows don't double count). The target = the points the side
beat its closing spread by (margin + spread). The features are DIFFERENCES (side minus opponent):
  d_ret = ret_pts gap, d_retm = ret_min gap, d_tin = tin_pts gap, d_tinq = transfer points x source Elo gap,
  d_pow = power-program transfer points gap, d_new = newcomer count gap, d_top = top scorer back (1/0) gap,
  d_sfnew / d_sfret = this season's minutes so far by newcomers / returners (strict, game 2+).
Per bucket x season: the slope of the residual on each feature (points per 1.0 of the feature) and its t; then a
pooled OLS on TRAIN read on HELD OUT (does it cut the squared error vs the close's 0?)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import table, TRAIN, HELD  # noqa: E402
import numpy as np

tb = [x for x in table() if x["side"] == "home" and x.get("sp") is not None and x["f"].get("has_pre")
      and x["of"].get("has_pre")]
out = []


def P(s):
    print(s)
    out.append(s)


def bucket(g):
    return "g1-3" if g <= 3 else "g4-5" if g <= 5 else "g6-10" if g <= 10 else "g11+"


FEATS = {
    "d_ret": lambda f, o: f["ret_pts"] - o["ret_pts"],
    "d_retm": lambda f, o: f["ret_min"] - o["ret_min"],
    "d_tin": lambda f, o: f["tin_pts"] - o["tin_pts"],
    "d_tinq": lambda f, o: f["tin_q"] - o["tin_q"],
    "d_pow": lambda f, o: f["tin_pts_pow"] - o["tin_pts_pow"],
    "d_new": lambda f, o: f["n_new"] - o["n_new"],
    "d_top": lambda f, o: int(f["top1_back"]) - int(o["top1_back"]),
    "d_roster": lambda f, o: (f["ret_pts"] + f["tin_pts"]) - (o["ret_pts"] + o["tin_pts"]),
    "d_sfnew": lambda f, o: (f.get("sf_new") - o.get("sf_new")) if f.get("sf_new") is not None and o.get("sf_new") is not None else None,
    "d_sfret": lambda f, o: (f.get("sf_ret") - o.get("sf_ret")) if f.get("sf_ret") is not None and o.get("sf_ret") is not None else None,
}
P(f"{len(tb)} games with both rosters + a closing spread")
P("slope = points vs the spread per 1.0 of the feature gap (t in brackets); bucket = the HOME side's game number"
  " (both teams' max gn)")
for fn, fx in FEATS.items():
    P(f"--- {fn}")
    for b in ("g1-3", "g4-5", "g6-10", "g11+"):
        cells = []
        for s in (2022, 2023, 2024, 2025):
            xs, ys = [], []
            for x in tb:
                if x["season"] != s or bucket(max(x["gn"], x["ogn"])) != b:
                    continue
                v = fx(x["f"], x["of"])
                if v is None:
                    continue
                xs.append(v)
                ys.append(x["margin"] + x["sp"])
            if len(xs) < 50:
                cells.append(f"{s} -")
                continue
            X, Y = np.array(xs), np.array(ys)
            Xc = X - X.mean()
            sl = (Xc * (Y - Y.mean())).sum() / (Xc ** 2).sum()
            res = Y - Y.mean() - sl * Xc
            se = np.sqrt((res ** 2).sum() / (len(X) - 2) / (Xc ** 2).sum())
            cells.append(f"{s} {sl:+6.2f}({sl/se:+4.1f}) n{len(X)}")
        P(f"  {b:6s} " + " | ".join(cells))

# pooled OLS, games 1-5 and 6-10: train fit -> held read
for b in (("g1-5", 1, 5), ("g6-10", 6, 10), ("g11+", 11, 99)):
    name, lo, hi = b
    keys = ["d_ret", "d_tin", "d_tinq", "d_new", "d_top"]

    def mat(ss):
        X, Y = [], []
        for x in tb:
            g = max(x["gn"], x["ogn"])
            if x["season"] in ss and lo <= g <= hi:
                X.append([FEATS[k](x["f"], x["of"]) for k in keys])
                Y.append(x["margin"] + x["sp"])
        return np.array(X), np.array(Y)
    X, Y = mat(range(TRAIN[0], TRAIN[1] + 1))
    A = np.c_[np.ones(len(X)), X]
    beta = np.linalg.lstsq(A, Y, rcond=None)[0]
    P(f"=== {name} train OLS ({len(X)} games): " + ", ".join(f"{k} {v:+.2f}" for k, v in zip(["c"] + keys, beta)))
    for s in HELD:
        Xh, Yh = mat([s])
        pred = np.c_[np.ones(len(Xh)), Xh] @ beta
        base = ((Yh - Y.mean()) ** 2).mean()
        mse = ((Yh - pred) ** 2).mean()
        # bet the side the model likes by 2+ points (no-juice ATS win rate)
        sel = np.abs(pred - beta[0]) >= 2
        hit = ((np.sign(pred - beta[0]) == np.sign(Yh)) & sel & (Yh != 0)).sum()
        tot = (sel & (Yh != 0)).sum()
        P(f"    held {s}: n {len(Xh)} mse close {base:.2f} model {mse:.2f} ({mse-base:+.2f}); |edge|>=2 pts: "
          f"{hit}/{tot} = {hit/max(tot,1):.3f} ATS")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s1_out.txt"), "w").write("\n".join(out) + "\n")
