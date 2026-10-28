"""10/28 THE HOT 3-POINT NIGHT (the owner and his brother: "85% of the time the team that hits more 3s wins - reverse
study it: what makes a hot 3-point night? That's locks"). Pure Python (no numpy here).
1. the after-the-fact check: how often the team with more made threes wins, by margin band;
2. how predictable the 3PM edge is BEFORE tip (OLS on pre-game inputs, train 2018-23, judged 2024 / 2025 / 2026 apart);
3. does the prediction make money at the closing moneyline / spread, and is it already in the price (win % vs the
   no-vig implied inside each predicted-edge bucket; a logistic residual on top of the market and Elo)."""
import math
import os
import pickle
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))

HERE = os.path.dirname(__file__)
sides = pickle.load(open(os.path.join(HERE, "sides.pkl"), "rb"))
HOME = [d for d in sides if d["home"]]                     # one row per game
TRAIN = {2018, 2019, 2020, 2021, 2022, 2023}
HOLD = [2024, 2025, 2026]


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


# ------------------------------------------------------------------ 1. the claim
print("=== 1. THE CLAIM (after the fact): the team that made more threes won straight up, NBA 2018-26 ===")
bands = [("tie", 0, 0), ("1-2 more", 1, 2), ("3-4 more", 3, 4), ("5-7 more", 5, 7), ("8+ more", 8, 99)]
tot_n = tot_w = 0
for lab, lo, hi in bands:
    n = w = 0
    for d in HOME:
        df = d["tpm"] - d["o_tpm"]
        if lo <= abs(df) <= hi:
            n += 1
            if df == 0:
                continue
            w += 1 if (d["won"] if df > 0 else not d["won"]) else 0
    if lo > 0:
        tot_n += n
        tot_w += w
    print(f"  {lab:10s} {n:5d} games - the 3PM leader won {w / n * 100 if n else 0:5.1f}%" if lo > 0 else f"  {lab:10s} {n:5d} games (no leader)")
print(f"  ALL with a leader: {tot_n} games, the team with more threes won {tot_w / tot_n * 100:.1f}%")
by = defaultdict(lambda: [0, 0])
for d in HOME:
    df = d["tpm"] - d["o_tpm"]
    if df:
        by[d["season"]][0] += 1
        by[d["season"]][1] += 1 if (d["won"] if df > 0 else not d["won"]) else 0
print("  by season: " + ", ".join(f"{s}-{str(s + 1)[2:]} {w / n * 100:.1f}%" for s, (n, w) in sorted(by.items())))
# the same statistic for other after-the-fact stats, for scale
for lab, key in (("more points in the paint? (n/a)", None),):
    pass
n = w = 0
for d in HOME:
    if d["tpa"] != d["o_tpa"]:
        n += 1
        w += 1 if (d["won"] if d["tpa"] > d["o_tpa"] else not d["won"]) else 0
print(f"  for scale - the team that ATTEMPTED more threes won {w / n * 100:.1f}% ({n}); the team that shot the better 3P%:", end=" ")
n = w = 0
for d in HOME:
    p1 = d["tpm"] / d["tpa"] if d["tpa"] else 0
    p2 = d["o_tpm"] / d["o_tpa"] if d["o_tpa"] else 0
    if p1 != p2:
        n += 1
        w += 1 if (d["won"] if p1 > p2 else not d["won"]) else 0
print(f"{w / n * 100:.1f}% ({n})")
# how big is the threes swing vs the outcome: 3PM diff vs margin correlation
xs = [d["tpm"] - d["o_tpm"] for d in HOME]
ys = [d["margin"] for d in HOME]


def corr(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x) / n)
    sy = math.sqrt(sum((b - my) ** 2 for b in y) / n)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / n / (sx * sy) if sx and sy else 0.0


print(f"  the 3PM margin vs the final margin: correlation {corr(xs, ys):.3f} (R² {corr(xs, ys) ** 2:.3f}); 3PM diff sd {math.sqrt(sum(x * x for x in xs) / len(xs)):.2f}")

# ------------------------------------------------------------------ 2. predict the 3PM edge before tip
print("\n=== 2. CAN WE PREDICT IT BEFORE TIP? (every input from games already played; home row = home minus away) ===")


import study_lib as sl   # noqa: E402
from study_lib import NAMES, feats, fit_eval, ols, predict, r2, solve, roi, seasons_up, cell, ml_pick, ats_pick   # noqa: E402,F401
sl.HOME = HOME

beta, rows = fit_eval(False, "A. HONEST (pre-tip inputs only)")
print("     coefficients (3PM diff per unit):")
for nm, b in zip(NAMES, beta):
    print(f"       {nm:36s} {b:+.3f}")
beta_la, rows_la = fit_eval(True, "B. WITH LOOK-AHEAD (how many of the top-3 shooters are missing from tonight's box) - a ceiling, not a bet")
print(f"     top-3 shooter out tonight coefficient {beta_la[-1]:+.3f} 3PM each")
# single-input correlations with the actual 3PM diff (train) - what predicts a hot night
print("  C. one input at a time (train seasons, correlation with the actual 3PM margin):")
tr = [r for r in rows if r[0]["season"] in TRAIN]
y = [r[0]["tpm"] - r[0]["o_tpm"] for r in tr]
for i, nm in enumerate(NAMES[:len(beta)]):
    if i == 0:
        continue
    print(f"       {nm:36s} {corr([r[1][i] for r in tr], y):+.3f}")
# how hot is a hot night: the team's own 3PM vs its season average - sd of the residual
res = []
for r in rows:
    d = r[0]
    if d["s_tpm"] is not None:
        res.append(d["tpm"] - d["s_tpm"])
sd = math.sqrt(sum(x * x for x in res) / len(res))
print(f"  D. a team's 3PM on a night vs its own season average: sd {sd:.2f} threes (the night-to-night noise). "
      f"The honest model's predicted 3PM DIFF has sd {math.sqrt(sum(predict(beta, r[1]) ** 2 for r in rows) / len(rows)):.2f} "
      f"against an actual-diff sd of {math.sqrt(sum((r[0]['tpm'] - r[0]['o_tpm']) ** 2 for r in rows) / len(rows)):.2f}.")

# ------------------------------------------------------------------ 3. money
print("\n=== 3. DOES IT MAKE MONEY? bet the side predicted to win the 3-point battle, closing prices, flat 1u ===")


pred = {r[0]["gid"]: predict(beta, r[1]) for r in rows}
sl.pred = pred

print("  MONEYLINE:")
for thr in (0.5, 1.5, 2.5, 3.5):
    cell(f"any price, predicted edge {thr}+ threes", ml_pick(thr, (-100000, 100000)))
for thr in (0.5, 1.5, 2.5, 3.5):
    cell(f"dogs +100..+350, predicted edge {thr}+ threes", ml_pick(thr, (100, 350)))
for thr in (0.5, 1.5, 2.5, 3.5):
    cell(f"favorites -101..-150, predicted edge {thr}+ threes", ml_pick(thr, (-150, -101)))
cell("the FADE: dogs predicted to LOSE the 3-pt battle by 2.5+", lambda d, p: ml_pick(2.5, (100, 350))(d, -p))
cell("the FADE: favs -101..-150 predicted to LOSE it by 2.5+", lambda d, p: ml_pick(2.5, (-150, -101))(d, -p))
print("  SPREAD (-110 assumed):")
for thr in (0.5, 1.5, 2.5, 3.5):
    cell(f"predicted edge {thr}+ threes, ATS", ats_pick(thr))
# the hand-built version as a second check
hand = {r[0]["gid"]: r[2] for r in rows}
print("  SECOND CHECK, the hand-built expected threes instead of the fit (dogs +100..+350):")
pred_saved = pred
sl.pred = hand
for thr in (1.5, 2.5):
    cell(f"hand-built edge {thr}+, dogs", ml_pick(thr, (100, 350)))
    cell(f"hand-built edge {thr}+, favs -101..-150", ml_pick(thr, (-150, -101)))
sl.pred = pred_saved

# ------------------------------------------------------------------ 3b. is it in the price?
print("\n=== 3b. IS IT ALREADY IN THE PRICE? win % vs the no-vig implied by predicted-edge bucket (all rows, both sides) ===")
buck = [("-4 or worse", -99, -4), ("-4..-2", -4, -2), ("-2..0", -2, 0), ("0..2", 0, 2), ("2..4", 2, 4), ("4+", 4, 99)]
for lab, S in (("train", TRAIN), ("holdout 2024-26", set(HOLD))):
    print(f"  {lab}:")
    for bl, lo, hi in buck:
        n = w = e = 0
        for d in sides:
            p = pred.get(d["gid"])
            if p is None:
                continue
            p = p if d["home"] else -p
            if lo <= p < hi and d["season"] in S:
                n += 1
                w += 1 if d["won"] else 0
                e += d["nv"]
        if n:
            print(f"    predicted 3PM edge {bl:12s} n {n:5d}  won {w / n * 100:5.1f}%  implied {e / n * 100:5.1f}%  gap {(w - e) / n * 100:+.1f} pts  z {(w - e) / math.sqrt(sum(0.2275 for _ in range(n))):+.1f}")


# the logistic residual: won ~ logit(nv) + Elo gap + predicted 3PM edge (train), then judge held out
def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def logistic(X, y, iters=25):
    k = len(X[0])
    beta = [0.0] * k
    for _ in range(iters):
        g = [0.0] * k
        H = [[0.0] * k for _ in range(k)]
        for x, yy in zip(X, y):
            z = sum(b * v for b, v in zip(beta, x))
            p = 1 / (1 + math.exp(-z)) if z > -30 else 0.0
            for i in range(k):
                g[i] += (yy - p) * x[i]
                for j in range(k):
                    H[i][j] += p * (1 - p) * x[i] * x[j]
        step = solve(H, g)
        beta = [b + s for b, s in zip(beta, step)]
        if max(abs(s) for s in step) < 1e-6:
            break
    return beta


Xtr, ytr = [], []
for d in HOME:
    p = pred.get(d["gid"])
    if p is None or d["season"] not in TRAIN:
        continue
    Xtr.append([1.0, logit(d["nv"]), (d["elo"] + 70 - d["opp_elo"]) / 100, p])
    ytr.append(1 if d["won"] else 0)
bl = logistic(Xtr, ytr)
# standard errors from the Hessian at the fit
k = len(bl)
H = [[0.0] * k for _ in range(k)]
for x in Xtr:
    z = sum(b * v for b, v in zip(bl, x))
    p = 1 / (1 + math.exp(-z))
    for i in range(k):
        for j in range(k):
            H[i][j] += p * (1 - p) * x[i] * x[j]
# invert H's diagonal via solving unit vectors
se = []
for i in range(k):
    e = [0.0] * k
    e[i] = 1.0
    col = solve(H, e)
    se.append(math.sqrt(max(col[i], 0)))
print(f"\n  logistic on the train seasons: won ~ market logit {bl[1]:+.3f} (se {se[1]:.3f}) + Elo/100 {bl[2]:+.3f} (se {se[2]:.3f}) "
      f"+ predicted 3PM edge {bl[3]:+.4f} (se {se[3]:.4f}, z {bl[3] / se[3] if se[3] else 0:+.1f}) per three")
# the same with the ACTUAL 3PM edge (after the fact) for scale
Xa = [[x[0], x[1], x[2], d["tpm"] - d["o_tpm"]] for x, d in zip(Xtr, [d for d in HOME if pred.get(d["gid"]) is not None and d["season"] in TRAIN])]
ba = logistic(Xa, ytr)
print(f"  for scale, the ACTUAL 3PM edge (known only after the game) on top of the market: {ba[3]:+.3f} per three")
# held-out: bet where the model's p beats the price by 3+ points
for lab, S in (("train", TRAIN), ("2024-25", {2024}), ("2025-26", {2025}), ("2026-27", {2026})):
    bets = []
    for d in HOME:
        p = pred.get(d["gid"])
        if p is None or d["season"] not in S:
            continue
        z = bl[0] + bl[1] * logit(d["nv"]) + bl[2] * (d["elo"] + 70 - d["opp_elo"]) / 100 + bl[3] * p
        ph = 1 / (1 + math.exp(-z))
        for home_side, pm, ml in ((True, ph, d["ml"]), (False, 1 - ph, d["opp_ml"])):
            nv = d["nv"] if home_side else 1 - d["nv"]
            if pm - nv >= 0.03 and -150 <= ml <= 350:
                bets.append((d["won"] if home_side else not d["won"], dec(ml), nv))
    n, w, ro, wp, imp, z = roi(bets)
    print(f"  model p 3+ points over the no-vig price, -150..+350: {lab:8s} {w}-{n - w} {ro:+.1f}% (z {z:+.1f})")
print(f"\n  cells run in part 3: {sl.CELLS} (+ 12 buckets, 4 model lines) - at 5% chance expect ~{(sl.CELLS + 16) * 0.05:.1f} |z|>2 by luck")
