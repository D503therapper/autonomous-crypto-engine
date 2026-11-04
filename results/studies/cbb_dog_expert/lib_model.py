"""The dog model pieces shared by s2 / s5: the features of a dog row, a ridge logistic fit by Newton's method
(the intercept and the market logit unpenalized), predict, log loss."""
import math

import numpy as np

import lib


def logit(p):
    p = min(0.995, max(0.005, p))
    return math.log(p / (1 - p))


def f0(v):
    return 0.0 if v is None else float(v)


def feats(x):
    g = lib.gap(x)
    backed = 1.0 if lib.backed(x) else 0.0
    gn = min(x["gn"], x["ogn"])
    conf = 1.0 if x.get("same_conf") else 0.0
    home = 1.0 if x["venue"] == "home" else 0.0
    away = 1.0 if x["venue"] == "away" else 0.0
    f = {
        "mkt_logit": logit(x["p"]),
        "eff_logit_gap": logit(x["eff"]) - logit(x["p"]),
        "eff_m": f0(x.get("eff_m")),
        "backed": backed,
        "gap15_backed": 1.0 if (backed and g >= 15) else 0.0,
        "gap10_backed": 1.0 if (backed and g >= 10) else 0.0,
        "gap15_home": 1.0 if (backed and g >= 15 and home) else 0.0,
        "gap15_conf": 1.0 if (backed and g >= 15 and conf) else 0.0,
        "raw_gap": (f0(x.get("raw")) - x["p"]) if x.get("raw") is not None else 0.0,
        "em": f0(x.get("em")) / 10,
        "home": home, "away": away,
        "rest": min(f0(x.get("rest")), 10) if x.get("rest") is not None else 4.0,
        "orest": min(f0(x.get("orest")), 10) if x.get("orest") is not None else 4.0,
        "trip": min(f0(x.get("trip")), 4), "miles": min(f0(x.get("miles")), 3000) / 1000,
        "streak": max(-8, min(8, f0(x.get("streak")))), "ostreak": max(-8, min(8, f0(x.get("ostreak")))),
        "wpct_gap": f0(x.get("wpct")) - f0(x.get("owpct")) if x.get("wpct") is not None and x.get("owpct") is not None else 0.0,
        "dog_pts": f0(x.get("dog_pts")),
        "top_out": 1.0 if x.get("top_out") else 0.0, "o_top_out": 1.0 if x.get("o_top_out") else 0.0,
        "rank25": 1.0 if x.get("rank25") else 0.0, "orank25": 1.0 if x.get("orank25") else 0.0,
        "conf": conf, "early": 1.0 if gn <= 3 else 0.0, "gn": min(gn, 30) / 30,
        "nd": 1.0 if x.get("nd") else 0.0, "mar": 1.0 if x.get("month") == "03" else 0.0,
        "tierP": 1.0 if lib.tier_of(x) == "P" else 0.0, "tierL": 1.0 if lib.tier_of(x) == "L" else 0.0,
        "lresid": max(-10, min(10, f0(x.get("lresid")))) / 10, "olresid": max(-10, min(10, f0(x.get("olresid")))) / 10,
        "cw5": f0(x.get("cw5")), "o_cw5": f0(x.get("o_cw5")), "ice_cold": 1.0 if x.get("ice_cold") else 0.0,
        "o_ice_cold": 1.0 if x.get("o_ice_cold") else 0.0,
        "last_m": max(-30, min(30, f0(x.get("last_m")))) / 10, "olast_m": max(-30, min(30, f0(x.get("olast_m")))) / 10,
        "reb_gap": max(-12, min(12, f0(x.get("rebm")) - f0(x.get("o_rebm")))) / 6 if x.get("rebm") is not None and x.get("o_rebm") is not None else 0.0,
        "ats_gap": max(-10, min(10, f0(x.get("cm_mean")) - f0(x.get("o_cm_mean")))) / 5 if (x.get("n_cm") or 0) >= 10 and (x.get("o_n_cm") or 0) >= 10 else 0.0,
        "rubber": 1.0 if x.get("rubber") else 0.0,
    }
    return f


def fit(Xt, yt, names, lam=3.0, iters=60):
    """Ridge logistic by Newton's method (the intercept and the market logit unpenalized)."""
    n, k = Xt.shape
    mu, sd = Xt.mean(0), Xt.std(0) + 1e-9
    Z = np.hstack([np.ones((n, 1)), (Xt - mu) / sd])
    w = np.zeros(k + 1)
    pen = np.full(k + 1, lam)
    pen[0] = 0.0
    pen[1 + names.index("mkt_logit")] = 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Z @ w))
        g = Z.T @ (p - yt) + pen * w
        H = (Z * (p * (1 - p))[:, None]).T @ Z + np.diag(pen)
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return w, mu, sd


def predict(m, Xv):
    w, mu, sd = m
    Z = np.hstack([np.ones((Xv.shape[0], 1)), (Xv - mu) / sd])
    return 1 / (1 + np.exp(-Z @ w))


def ll(p, yv):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -np.mean(yv * np.log(p) + (1 - yv) * np.log(1 - p))
