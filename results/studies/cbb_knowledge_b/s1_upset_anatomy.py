"""S1 - ANATOMY OF AN UPSET: every college hoops dog +150..+350 at the close, regular season 2018-25. What did the
dogs that WON have before tip that the losers didn't - form, rest, venue, style, the rating gaps, the line move, the
opponent's spot (letdown / lookahead / travel), the time of season? Each feature is read two ways: (A) the winners'
and losers' average of it (does it separate them at all), (B) the ROI of the dogs in each bucket at the close
(does the market already charge for it - the honest test). Then (C) a ridge-logistic DOG MODEL on the market's logit
plus the honest features, walk-forward by season (fit on the seasons before), bet where it reads the dog over the
no-vig price. Train 2018-22, held out 2023 / 2024 / 2025 apart; the ESPN open (2023-25) is the second check."""
import math
from collections import defaultdict

import numpy as np

import lib

rows = lib.regular(lib.build())
by_i = rows                                                   # (next_i / o_next_i index into the full table)
full = lib.build()
D = [x for x in rows if x.get("ml") is not None and 150 <= x["ml"] <= 350 and x.get("own") is not None]
o = lib.Out("s1")
o.note(f"dogs +150..+350 with a close and an engine read: {len(D)} (train {sum(1 for x in D if x['season'] <= 2022)}, "
       f"held {sum(1 for x in D if x['season'] in lib.HELD)})")
w, p_, n = lib.win_vs_price(D)
o.note(f"they won {w * 100:.1f}% of the time; the no-vig close said {p_ * 100:.1f}% - the price already carries the upsets")


def opp_next_ranked(x):
    """The opponent's NEXT game is vs a top-25 team (lookahead) - home / road games before March only (the 11/3 (B)
    bracket leak: in a tournament the next game exists only for the winner)."""
    j = x.get("o_next_i")
    if j is None or x["venue"] == "neutral" or x["month"] == "03":
        return None
    nx = full[j]
    if nx["venue"] == "neutral":
        return None
    return bool(nx.get("orank25"))


FEATS = {
    # name: (fn -> value or None, edges for buckets)
    "win streak (- = skid)": (lambda x: x.get("streak"), [-5, -3, -1, 1, 3, 5]),
    "win % so far (5+ games)": (lambda x: x["wpct"] if x["gn"] > 5 else None, [0.3, 0.5, 0.7]),
    "last margin": (lambda x: x.get("last_m"), [-15, -5, 0, 5, 15]),
    "avg margin so far (5+)": (lambda x: x.get("avg_m"), [-10, -5, 0, 5]),
    "luck (win% - margin-implied)": (lambda x: x.get("luck"), [-0.1, 0, 0.1]),
    "cover run": (lambda x: x.get("ats"), [-4, -2, 0, 2, 4]),
    "rest nights": (lambda x: x.get("rest"), [2, 3, 5, 8]),
    "opp rest nights": (lambda x: x.get("orest"), [2, 3, 5, 8]),
    "rest gap (mine - theirs)": (lambda x: (x["rest"] - x["orest"]) if x.get("rest") is not None and x.get("orest") is not None else None, [-2, 0, 1, 3]),
    "games in 3 nights": (lambda x: x.get("g3"), [1, 2]),
    "miles traveled": (lambda x: x.get("miles") if x["venue"] != "home" else None, [300, 1000, 2000]),
    "road trip game #": (lambda x: x.get("trip") if x["venue"] == "away" else None, [2, 3]),
    "pace gap (FGA/g)": (lambda x: (x["pace"] - x["o_pace"]) if x.get("pace") is not None and x.get("o_pace") is not None else None, [-8, -3, 3, 8]),
    "rebound margin gap": (lambda x: lib.reb_gap(x), [-8, -4, 0, 4, 8]),
    "FG% gap (offense)": (lambda x: (x["fgp"] - x["o_fgp"]) if x.get("fgp") is not None and x.get("o_fgp") is not None else None, [-0.04, -0.01, 0.01, 0.04]),
    "FG% allowed gap (defense, - = better)": (lambda x: (x["ofgp"] - x["o_ofgp"]) if x.get("ofgp") is not None and x.get("o_ofgp") is not None else None, [-0.04, -0.01, 0.01, 0.04]),
    "Elo gap (mine - theirs)": (lambda x: x["elo"] - x["oelo"], [-300, -200, -100, 0]),
    "efficiency read - no-vig price": (lambda x: (x["eff"] - x["p"]) if x.get("eff") is not None else None, [-0.06, -0.03, 0, 0.03, 0.06]),
    "engine own read - no-vig price": (lambda x: x["own"] - x["p"], [-0.03, 0, 0.03, 0.06]),
    "line move open->close (to the dog +)": (lambda x: x.get("move"), [-0.04, -0.015, 0.015, 0.04]),
    "opp last margin (letdown)": (lambda x: x.get("olast_m"), [-10, 0, 10, 20]),
    "opp next vs top-25 (lookahead)": (lambda x: opp_next_ranked(x), None),
    "opp road trip game #": (lambda x: x.get("o_trip") if x["venue"] == "home" else None, [2, 3]),
    "opp miles": (lambda x: x.get("o_miles") if x["venue"] == "home" else None, [300, 1000, 2000]),
    "opp win streak": (lambda x: x.get("o_streak"), [-3, 0, 3, 6]),
    "opp ice cold": (lambda x: x.get("o_ice_cold"), None),
    "my ice cold": (lambda x: x.get("ice_cold"), None),
    "my top scorer missed last game": (lambda x: x.get("top_out"), None),
    "opp top scorer missed last game": (lambda x: x.get("o_top_out"), None),
    "games played": (lambda x: x["gn"], [4, 11, 21]),
    "ats gap (hot-ATS +)": (lambda x: lib.ats_gap(x), [-5, -2, 2, 5]),
}
TIER = ("P", "M", "L")

o.h("A. WINNERS vs LOSERS - the average of each feature before tip (the dogs that won | the dogs that lost), "
    "train 2018-22 then held out 2023-25")
for name, (fn, _e) in FEATS.items():
    for lab, S in (("train", [x for x in D if x["season"] <= 2022]), ("held", [x for x in D if x["season"] in lib.HELD])):
        vw = [fn(x) for x in S if x["won"]]
        vl = [fn(x) for x in S if not x["won"]]
        vw = [float(v) for v in vw if v is not None]
        vl = [float(v) for v in vl if v is not None]
        if len(vw) < 30 or len(vl) < 30:
            continue
        mw, ml_ = sum(vw) / len(vw), sum(vl) / len(vl)
        sd = math.sqrt((np.var(vw) * len(vw) + np.var(vl) * len(vl)) / (len(vw) + len(vl)))
        d = (mw - ml_) / sd if sd else 0
        o.note(f"{name:40s} {lab:5s} won {mw:+8.3f} (n{len(vw)}) | lost {ml_:+8.3f} (n{len(vl)}) | d {d:+.2f}")
o.note("(d = the gap in standard deviations - the market's own price separates them at d ~ +0.3; anything under 0.1 "
       "is nothing)")
o.note("(the price itself:)")
for lab, S in (("train", [x for x in D if x["season"] <= 2022]), ("held", [x for x in D if x["season"] in lib.HELD])):
    vw = [x["p"] for x in S if x["won"]]
    vl = [x["p"] for x in S if not x["won"]]
    o.note(f"{'no-vig price':40s} {lab:5s} won {sum(vw) / len(vw):+8.3f} | lost {sum(vl) / len(vl):+8.3f}")

o.h("B. THE MONEY TEST - the dogs in each bucket at the close (ALL / train seasons up / held out / the open)")
o.c("every dog +150..+350 (the base)", D)
for name, (fn, edges) in FEATS.items():
    if edges is None:
        lib.cuts(o, name, D, lambda x, fn=fn: {True: "yes", False: "no"}.get(fn(x)), ["yes", "no"])
    else:
        lib.cuts(o, name, D, lambda x, fn=fn, e=edges: lib.bk(fn(x), e), lib.bk_labels(edges))
lib.cuts(o, "venue", D, lambda x: x["venue"], ["home", "away", "neutral"])
lib.cuts(o, "month", D, lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"])
lib.cuts(o, "tier", D, lib.tier_of, TIER)
lib.cuts(o, "conference game", D, lambda x: "yes" if x.get("same_conf") else "no", ["yes", "no"])
lib.cuts(o, "price", D, lambda x: lib.bk(x["ml"], [200, 250, 300]), lib.bk_labels([200, 250, 300]))


o.h("C. THE DOG MODEL - ridge logistic on the market logit + the honest features, walk-forward by season")


def feats(x):
    rg = lib.reb_gap(x)
    ag = lib.ats_gap(x)
    f = [
        1.0,
        float(x["venue"] == "home"), float(x["venue"] == "neutral"),
        (x.get("streak") or 0) / 3, (x.get("last_m") or 0) / 10, (x.get("olast_m") or 0) / 10,
        ((x["wpct"] - 0.5) if x.get("wpct") is not None and x["gn"] > 5 else 0.0),
        (x.get("luck") or 0) * 5,
        ((x["rest"] - x["orest"]) / 2 if x.get("rest") is not None and x.get("orest") is not None else 0.0),
        float((x.get("g3") or 0) >= 2), float((x.get("og3") or 0) >= 2),
        ((x.get("miles") or 0) / 1000 if x["venue"] != "home" else 0.0),
        float((x.get("trip") or 0) >= 2),
        ((x["pace"] - x["o_pace"]) / 8 if x.get("pace") is not None and x.get("o_pace") is not None else 0.0),
        (max(-12, min(12, rg)) / 6 if rg is not None else 0.0),
        ((x["fgp"] - x["o_fgp"]) * 20 if x.get("fgp") is not None and x.get("o_fgp") is not None else 0.0),
        (x["elo"] - x["oelo"]) / 100,
        ((x["eff"] - x["p"]) * 10 if x.get("eff") is not None else 0.0),
        (x["own"] - x["p"]) * 10,
        float(x.get("ice_cold")), float(x.get("o_ice_cold")),
        float(bool(x.get("top_out"))), float(bool(x.get("o_top_out"))),
        float(x["gn"] <= 3 and x["venue"] == "away"), float(x["gn"] <= 5),
        float(x["nd"]), float(x.get("same_conf")),
        float(x.get("rank25") and x["venue"] == "away" and x["nd"]), float(x.get("orank25") and x["venue"] == "home" and x["nd"]),
        (max(-10, min(10, ag)) / 5 if ag is not None else 0.0),
        float(x.get("rubber")), float((x.get("streak") or 0) <= -5),
        (x["ml"] - 250) / 100,
    ]
    return f


NAMES = ["const", "home", "neutral", "streak/3", "last m/10", "opp last m/10", "wpct-.5", "luck x5", "rest gap/2", "2in3",
         "opp 2in3", "miles/1000", "trip 2+", "pace gap/8", "reb gap/6", "fg% gap x20", "elo gap/100", "eff-p x10",
         "own-p x10", "ice cold", "opp ice cold", "top out", "opp top out", "early road", "games<=5", "Nov-Dec", "conf",
         "ranked road ND", "home vs ranked ND", "ats gap/5", "rubber", "skid 5+", "price/100"]


def fit(X, y, off, lam=20.0):
    """ridge logistic with an offset (the market logit), Newton steps; the constant is not penalized."""
    b = np.zeros(X.shape[1])
    pen = np.full(X.shape[1], lam)
    pen[0] = 0.0
    for _ in range(30):
        z = off + X @ b
        p = 1 / (1 + np.exp(-z))
        g = X.T @ (p - y) + pen * b
        W = p * (1 - p)
        H = (X * W[:, None]).T @ X + np.diag(pen)
        step = np.linalg.solve(H, g)
        b -= step
        if np.abs(step).max() < 1e-7:
            break
    return b


X = np.array([feats(x) for x in D])
y = np.array([1.0 if x["won"] else 0.0 for x in D])
S = np.array([x["season"] for x in D])
off = np.array([math.log(x["p"] / (1 - x["p"])) for x in D])
tr = (S >= 2018) & (S <= 2022)
b = fit(X[tr], y[tr], off[tr])
# t-stats on train
z = off[tr] + X[tr] @ b
pp = 1 / (1 + np.exp(-z))
H = (X[tr] * (pp * (1 - pp))[:, None]).T @ X[tr] + np.diag(np.r_[0.0, np.full(X.shape[1] - 1, 20.0)])
se = np.sqrt(np.diag(np.linalg.inv(H)))
o.note("train fit 2018-22 (coefficients in log odds over the market, t):")
for nm, bb, s in sorted(zip(NAMES, b, se), key=lambda t: -abs(t[1] / t[2]) if t[2] else 0):
    o.note(f"   {nm:18s} {bb:+.3f}  t {bb / s:+.1f}")
ll_m = -np.mean(y[tr] * np.log(1 / (1 + np.exp(-off[tr]))) + (1 - y[tr]) * np.log(1 - 1 / (1 + np.exp(-off[tr]))))
ll_f = -np.mean(y[tr] * np.log(pp) + (1 - y[tr]) * np.log(1 - pp))
o.note(f"train log loss: the market {ll_m:.4f} | the model {ll_f:.4f} (in sample)")


def walk(min_edge):
    """bet every dog the model (fit on the seasons before) reads min_edge+ over the no-vig price; return rows."""
    picks = []
    for s in lib.HELD:
        m = S < s
        bb = fit(X[m], y[m], off[m])
        t = S == s
        pm = 1 / (1 + np.exp(-(off[t] + X[t] @ bb)))
        for i, (x, q) in enumerate(zip([d for d, f in zip(D, t) if f], pm)):
            x["model_p"] = float(q)
            if q - x["p"] >= min_edge:
                picks.append(x)
    return picks


for s in lib.HELD:
    m = S < s
    bb = fit(X[m], y[m], off[m])
    t = S == s
    pm = 1 / (1 + np.exp(-(off[t] + X[t] @ bb)))
    mk = 1 / (1 + np.exp(-off[t]))
    llm = -np.mean(y[t] * np.log(mk) + (1 - y[t]) * np.log(1 - mk))
    llf = -np.mean(y[t] * np.log(pm) + (1 - y[t]) * np.log(1 - pm))
    o.note(f"held out {s}: log loss the market {llm:.4f} | the model {llf:.4f} ({(llm - llf) * 1000:+.2f} milli, + = the model is better) on {t.sum()}")
for e in (0.0, 0.02, 0.03, 0.05, 0.08):
    o.c(f"walk-forward: the model reads the dog {e * 100:.0f}+ pts over the no-vig (held out only)", walk(e))
# the model's deciles on the held seasons
walk(-9)
hp = [x for x in D if x.get("model_p") is not None]
hp.sort(key=lambda x: x["model_p"] - x["p"])
k = len(hp) // 5
for i in range(5):
    o.c(f"walk-forward: model - price, fifth {i + 1} of 5 (1 = the model likes it least)", hp[i * k:(i + 1) * k])
# the same with the OWN-read and eff inputs removed (what the schedule / form / style alone carry)
keep = [i for i, nm in enumerate(NAMES) if nm not in ("eff-p x10", "own-p x10", "elo gap/100")]
X2 = X[:, keep]
picks = []
for s in lib.HELD:
    m = S < s
    bb = fit(X2[m], y[m], off[m])
    t = S == s
    pm = 1 / (1 + np.exp(-(off[t] + X2[t] @ bb)))
    for x, q in zip([d for d, f in zip(D, t) if f], pm):
        if q - x["p"] >= 0.03:
            picks.append(x)
o.c("walk-forward, NO rating inputs (schedule / form / style only): the model 3+ over the no-vig", picks)
o.save()
