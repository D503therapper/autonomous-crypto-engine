"""S6 - ONE HONEST REGULARIZED MULTI-FACTOR MODEL: the engine's NBA weights (as ±1 facts), the schedule, form, the Elo
gap, the box-score style, the lineup read with the report's outs, and the market's own logit - a ridge logistic fit
walk-forward (each season on the seasons before it; lambda picked on the 2020-22 walk-forward log loss), graded on
2023 / 2024 / 2025 it never saw. Does the combination beat the market (log loss), and does betting its edge pay at
the close (and at the paid 2020-22 morning price)? Compared with the hand dog score (the 10/21 / 10/28 weights, gate 4+)."""
import json
import math
import os

import numpy as np

import lib

T = lib.build()
OUT = lib.OUT


def logit(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def f0(x):
    return float(x) if x is not None else 0.0


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def facts(d):
    """The engine's NBA dog-weight facts as ±1 for THIS side (a fade on us = -1, a fade on the opponent = +1)."""
    o = {k[2:]: v for k, v in d.items() if k.startswith("o_")}
    f = {}
    f["rested_vs_b2b"] = 1.0 if (d["rest"] or 0) >= 2 and o["b2b"] else (-1.0 if d["b2b"] and (o["rest"] or 0) >= 2 else 0.0)
    f["won_big_last"] = (1.0 if (o["last_margin"] or 0) >= 20 else 0.0) - (1.0 if (d["last_margin"] or 0) >= 15 else 0.0)
    f["lost_big_last"] = (1.0 if (d["last_margin"] or 0) <= -15 else 0.0) - (1.0 if (o["last_margin"] or 0) <= -15 else 0.0)
    f["ot_last"] = (1.0 if o["last_ot"] else 0.0) - (1.0 if d["last_ot"] else 0.0)
    f["pts_last"] = (1.0 if (o["last_pts"] or 100) <= 95 else 0.0) - (1.0 if (d["last_pts"] or 0) >= 130 else 0.0)
    f["streak3"] = (1.0 if o["win_streak"] >= 3 else 0.0) - (1.0 if d["win_streak"] >= 3 else 0.0)
    f["rest_gap"] = clip(f0(d["rest"] if d["rest"] is not None else 3) - f0(o["rest"] if o["rest"] is not None else 3), -3, 3)
    f["home_after_trip"] = (1.0 if o["home_after_trip"] >= 4 else 0.0) - (1.0 if d["home_after_trip"] >= 4 else 0.0)
    f["trip4"] = (1.0 if o["trip_game"] >= 4 else 0.0) - (1.0 if d["trip_game"] >= 4 else 0.0)
    f["trip_end"] = (1.0 if o["trip_end"] and o["trip_game"] >= 4 else 0.0) - (1.0 if d["trip_end"] and d["trip_game"] >= 4 else 0.0)
    f["dense"] = (1.0 if o["in6"] >= 4 else 0.0) - (1.0 if d["in6"] >= 4 else 0.0)
    f["slate12"] = 1.0 if d["slate"] >= 12 else 0.0
    soft = lambda x: 1.0 if x["next_days"] is not None and x["next_days"] <= 2 and x["next_opp_wp"] is not None and x["next_opp_wp"] < 0.4 else 0.0  # noqa: E731
    f["next_soft"] = soft(d) - soft(o)
    cold = lambda x: 1.0 if x["g"] >= 8 and (x["wp"] or 1) < 0.3 else 0.0   # noqa: E731
    f["cold"] = cold(o) - cold(d)
    g = d["g"] + 1
    f["home_dog_6_20"] = 1.0 if d["home"] and d["ml"] > 0 and 6 <= g <= 20 else 0.0
    f["home_31_60"] = (1.0 if d["home"] and 31 <= g <= 60 else 0.0) - (1.0 if not d["home"] and 31 <= o["g"] + 1 <= 60 else 0.0)
    f["early_wp_last"] = (1.0 if g <= 15 and (d["last_wp"] or 0) >= 0.55 else 0.0) - (1.0 if o["g"] + 1 <= 15 and (o["last_wp"] or 0) >= 0.55 else 0.0)
    return f


def features(d):
    o = {k[2:]: v for k, v in d.items() if k.startswith("o_")}
    p_elo = 1 / (1 + 10 ** (-((d["elo"] + (70 if d["home"] else -70)) - d["opp_elo"]) / 400))
    x = {"logit_nv": logit(d["nv"]), "home": 1.0 if d["home"] else 0.0, "dog": 1.0 if d["ml"] > 0 else 0.0,
         "elo_gap": logit(p_elo) - logit(d["nv"]),
         "m5": clip(f0(d["m5"]) - f0(o["m5"]), -25, 25) / 10, "m10": clip(f0(d["m10"]) - f0(o["m10"]), -20, 20) / 10,
         "wp": f0(d["wp"]) - f0(o["wp"]), "last_wp": f0(d["last_wp"]) - f0(o["last_wp"]),
         "sd10": clip(f0(d["sd10"]) - f0(o["sd10"]), -10, 10) / 5,
         "pace": clip(f0(d["pace"]) - f0(o["pace"]), -8, 8) / 4 if d["pace"] and o["pace"] else 0.0,
         "oreb": clip(f0(d["oreb_pct"]) - f0(o["oreb_pct"]), -0.1, 0.1) * 10 if d["oreb_pct"] and o["oreb_pct"] else 0.0,
         "to": clip(f0(d["to_rate"]) - f0(o["to_rate"]), -0.05, 0.05) * 20 if d["to_rate"] and o["to_rate"] else 0.0,
         "tp_rate": clip(f0(d["tp_rate"]) - f0(o["tp_rate"]), -0.15, 0.15) / 0.1 if d["tp_rate"] and o["tp_rate"] else 0.0,
         "lineup": clip(f0(d["strength_avail"]) - f0(o["strength_avail"]), -15, 15) / 5
         if d["strength_avail"] is not None and o["strength_avail"] is not None else 0.0,
         "lost": clip((f0(d["strength_full"]) - f0(d["strength_avail"])) - (f0(o["strength_full"]) - f0(o["strength_avail"])), -8, 8) / 3
         if d["strength_avail"] is not None and o["strength_avail"] is not None else 0.0,
         "out_rot": clip(f0(d["out_rot"]) - f0(o["out_rot"]), -4, 4) / 2, "out_key": clip(f0(d["out_key"]) - f0(o["out_key"]), -2, 2),
         "back": f0(d["back_n"]) - f0(o["back_n"]),
         "bias_last": clip(f0(d["bias_last"]) - f0(o["bias_last"]), -0.2, 0.2) * 5,
         "bias_now": clip(f0(d["bias_now"]) - f0(o["bias_now"]), -0.3, 0.3) * 3,
         "g_early": 1.0 if d["g"] < 10 or o["g"] < 10 else 0.0, "late": 1.0 if d["month"] in (3, 4) else 0.0}
    x.update(facts(d))
    return x


rows = [d for d in T if d["g"] >= 5 and d["o_g"] >= 5]
keys = list(features(rows[0]).keys())
X = np.array([[features(d)[k] for k in keys] for d in rows])
y = np.array([1.0 if d["won"] else 0.0 for d in rows])
S = np.array([d["season"] for d in rows])
NV = np.array([d["nv"] for d in rows])
print("rows", len(rows), "features", len(keys))


def fit(Xa, ya, lam, iters=25):
    """Ridge logistic by Newton's method; the intercept and the market logit are NOT penalized."""
    n, k = Xa.shape
    A = np.hstack([np.ones((n, 1)), Xa])
    w = np.zeros(k + 1)
    pen = np.full(k + 1, lam)
    pen[0] = 0.0
    pen[1] = 0.0                                  # column 1 = logit_nv
    for _ in range(iters):
        z = A @ w
        p = 1 / (1 + np.exp(-z))
        g = A.T @ (p - ya) + pen * w
        W = p * (1 - p)
        H = (A * W[:, None]).T @ A + np.diag(pen)
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-7:
            break
    return w


def predict(w, Xa):
    A = np.hstack([np.ones((len(Xa), 1)), Xa])
    return 1 / (1 + np.exp(-(A @ w)))


def ll(p, yy):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(yy * np.log(p) + (1 - yy) * np.log(1 - p)))


# standardize on the whole table's spread (a fixed scale, not a leak - it only sets the penalty's units)
mu, sd = X.mean(0), X.std(0) + 1e-9
mu[0] = 0.0
sd[0] = 1.0                                       # keep the market logit raw
Xs = (X - mu) / sd
out = {"keys": keys}
# 1. lambda on the 2020-22 walk-forward (fit on seasons < s)
print("\nLAMBDA (walk-forward log loss 2020-22 vs the market's own):")
best = None
for lam in (10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0):
    tot, totm, n = 0.0, 0.0, 0
    for s in (2020, 2021, 2022):
        tr, te = S < s, S == s
        w = fit(Xs[tr], y[tr], lam)
        p = predict(w, Xs[te])
        tot += ll(p, y[te]) * te.sum()
        totm += ll(NV[te], y[te]) * te.sum()
        n += te.sum()
    print(f"  lam {lam:7.0f}: model {tot / n:.5f}  market {totm / n:.5f}  gain {1000 * (totm - tot) / n:+.2f} milli")
    if best is None or tot < best[1]:
        best = (lam, tot)
LAM = best[0]
print("  chosen", LAM)
out["lam"] = LAM
# 2. held out 2023 / 2024 / 2025 (+ 2026), fit on everything before each
print("\nHELD OUT (fit on the seasons before each):")
res = {}
preds = np.zeros(len(rows))
for s in (2020, 2021, 2022, 2023, 2024, 2025, 2026):
    tr, te = S < s, S == s
    if te.sum() == 0:
        continue
    w = fit(Xs[tr], y[tr], LAM)
    p = predict(w, Xs[te])
    preds[te] = p
    res[s] = {"n": int(te.sum()), "model": round(ll(p, y[te]), 5), "market": round(ll(NV[te], y[te]), 5)}
    print(f"  {s}: n {te.sum():5d} model {res[s]['model']:.5f} market {res[s]['market']:.5f} "
          f"gain {1000 * (res[s]['market'] - res[s]['model']):+.2f} milli")
out["logloss"] = res
# the weights of the final fit (on 2018-24, for 2025) - which facts carry anything after the market
w = fit(Xs[S < 2025], y[S < 2025], LAM)
wt = sorted(zip(["intercept"] + keys, w), key=lambda kv: -abs(kv[1]))
print("\nWEIGHTS (standardized, fit 2018-24):")
print("  " + ", ".join(f"{k} {v:+.3f}" for k, v in wt[:20]))
out["weights"] = {k: round(float(v), 4) for k, v in wt}
# 3. betting the edge: model p minus the no-vig price, at the close; dogs / favorites; top side a night
C = lib.Cells()
edge = preds - NV
for i, d in enumerate(rows):
    if d["season"] < 2020:
        continue
    s = d["season"]
    e = edge[i]
    kind = "dog" if lib.dog(d) else "fav-150..-101" if lib.fav(d) else "fav big" if d["ml"] < -150 else "dog long" if d["ml"] > 350 else None
    if not kind:
        continue
    for cut in (0.02, 0.03, 0.05, 0.08):
        if e >= cut:
            C.add(f"1 model edge {cut:+.2f}+: {kind} [ML close]", s, lib.ml(d))
            if d.get("m_dec"):
                C.add(f"1 model edge {cut:+.2f}+: {kind} [ML morning]", s, lib.ml(d, "morning"))
            if d.get("dec_open"):
                C.add(f"1 model edge {cut:+.2f}+: {kind} [ML open]", s, lib.ml(d, "open"))
    if e <= -0.05:
        C.add(f"1b model edge -0.05 or worse (the fade side): {kind} [ML close]", s, lib.ml(d))
    b = "<-0.05" if e < -0.05 else "-0.05..-0.02" if e < -0.02 else "-0.02..0.02" if e < 0.02 else "0.02..0.05" if e < 0.05 else "0.05+"
    C.add(f"1c calibration edge {b}: {kind} [ML close]", s, lib.ml(d))
# the best side a night by edge
by_day = {}
for i, d in enumerate(rows):
    if d["season"] >= 2020:
        by_day.setdefault(d["day"], []).append((edge[i], i))
for day, lst in by_day.items():
    lst.sort(reverse=True)
    e, i = lst[0]
    d = rows[i]
    if e >= 0.03 and -150 <= d["ml"] <= 350:
        C.add("2 best side a night, edge 0.03+, -150..+350 [ML close]", d["season"], lib.ml(d))
        if d.get("m_dec"):
            C.add("2 best side a night, edge 0.03+, -150..+350 [ML morning]", d["season"], lib.ml(d, "morning"))
    if len(lst) > 1 and lst[1][0] >= 0.03 and -150 <= rows[lst[1][1]]["ml"] <= 350:
        C.add("2b the #2 side a night, edge 0.03+ [ML close]", rows[lst[1][1]]["season"], lib.ml(rows[lst[1][1]]))
# 4. the hand dog score (the built weights, as a proxy) on the same rows, gate 4+ vs the model's dogs
for i, d in enumerate(rows):
    if d["season"] < 2020 or not lib.dog(d):
        continue
    f = facts(d)
    hand = 2 * (f["rested_vs_b2b"] * 1.5 + f["won_big_last"] + f["lost_big_last"] * 0 + f["ot_last"] + f["pts_last"]
                + f["streak3"] + (1 if f["rest_gap"] <= -2 else 0) * -1 + f["home_after_trip"] + f["trip4"] + f["slate12"]
                + f["next_soft"] + f["cold"] + f["home_dog_6_20"] + f["home_31_60"] * 1 + f["early_wp_last"])
    hand += 5 if f["lost_big_last"] > 0 else 0        # the overreaction bounce (+5)
    hand = max(-6, min(6, hand))
    s = d["season"]
    b = "4+" if hand >= 4 else "2..4" if hand >= 2 else "0..2" if hand >= 0 else "<0"
    C.add(f"3 hand dog score {b}: dog [ML close]", s, lib.ml(d))
    if hand >= 4:
        mb = "model edge 0.02+" if edge[i] >= 0.02 else "model edge under 0.02"
        C.add(f"3b hand score 4+ AND {mb}: dog [ML close]", s, lib.ml(d))
    if edge[i] >= 0.03:
        hb = "hand 4+" if hand >= 4 else "hand 0..4" if hand >= 0 else "hand <0"
        C.add(f"3c model edge 0.03+ AND {hb}: dog [ML close]", s, lib.ml(d))
res = C.dump("s6", lib.header("S6 THE MULTI-FACTOR MODEL vs THE MARKET (walk-forward; TRAIN here = 2020-22 walk-forward, HELD 2023-25)", len(rows)),
             lambda k: ((2020, 2022), lib.HELD))
json.dump(out, open(os.path.join(OUT, "s6_model.json"), "w"), indent=1)
