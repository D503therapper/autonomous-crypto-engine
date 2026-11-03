"""S8 - ONE HONEST MULTI-FACTOR MODEL, walk-forward by season: a ridge on the cover margin (margin + spread) over every
situational input on the table - the three S6 / S7 findings (ranked road Nov-Dec, the hot-ATS gap, the rebound gap),
the earlier built college hoops weights' inputs (the Nov-Dec away small favorite, the early road dog, the 5+ skid, the
rubber match, the cover run), and the dead ones (luck, variance, 2nd-half gain, pace, rotation, weekday, slate, trip).
Fit on the seasons BEFORE each graded season (2023 / 2024 / 2025, each with 2018..s-1), graded as ATS bets in bins of the
predicted edge. The question: does stacking the weights find a bettable cell the single cuts don't, and does the fit
agree the three new inputs carry their own weight next to the old ones (the t-stats)."""
import numpy as np
import lib

rows = lib.spreads(lib.regular(lib.build()))
o = lib.Out("s8")
ND = ("11", "12")


def feats(x):
    nd = x["start"][5:7] in ND
    road = x["venue"] == "away"
    hot = (x["cm_mean"] - x["o_cm_mean"]) if x.get("cm_mean") is not None and x.get("o_cm_mean") is not None and x.get("n_cm", 0) >= 10 else 0.0
    reb = (x["rebm"] - x["o_rebm"]) if x.get("rebm") is not None and x.get("o_rebm") is not None else 0.0
    pm = x.get("prev_meet") or []
    rubber = len(pm) == 2 and (pm[0]["margin"] > 0) != (pm[1]["margin"] > 0)
    return [
        1.0,
        float(x["rank25"] and road and nd),                           # NEW: the ranked road side, Nov-Dec
        float(x["rank25"] and road and not nd),                       # ranked road, Jan-Mar
        float(x["orank25"] and x["venue"] == "home" and nd),          # the home side across it
        max(-10, min(10, hot)) / 5,                                   # NEW: the hot-vs-cold ATS gap (per 5 pts)
        max(-12, min(12, reb)) / 6,                                   # NEW: the rebound-margin gap (per 6 boards)
        float(x.get("ml") is not None and -150 <= x["ml"] <= -101 and x["venue"] != "home" and nd),   # built: away small fav
        float(x.get("ml") is not None and 100 <= x["ml"] <= 350 and road and x["gn"] <= 3),           # built: early road dog
        float(x["streak"] <= -5 and x["sp"] > 0),                                                      # built: 5+ skid dog
        float(rubber and x["sp"] > 0),                                                                 # built: rubber dog
        float(x["ats"] >= 4) - float(x["ats"] <= -4),                                                  # built: cover run
        (x["luck"] - x["o_luck"]) if x.get("luck") is not None and x.get("o_luck") is not None else 0.0,
        ((x["m_sd"] - x["o_m_sd"]) / 5) if x.get("m_sd") is not None and x.get("o_m_sd") is not None else 0.0,
        ((x["h2_gain"] - x["o_h2_gain"]) / 3) if x.get("h2_gain") is not None and x.get("o_h2_gain") is not None else 0.0,
        ((x["pace"] - x["o_pace"]) / 8) if x.get("pace") is not None and x.get("o_pace") is not None else 0.0,
        ((x["top5"] - x["o_top5"]) * 10) if x.get("top5") is not None and x.get("o_top5") is not None else 0.0,
        float(x.get("ldow") == 5 and x["dow"] in (0, 1) and road),    # Saturday -> Mon/Tue on the road
        float(x["trip"] == 2 and (x.get("rest") or 9) <= 3),           # the 2nd stop of a swing
        (x["slate"] - 40) / 40,
        float(road), float(x["venue"] == "neutral"), x["sp"] / 10,
        (x["elo"] - x["oelo"]) / 100,
    ]


NAMES = ["const", "ranked road ND", "ranked road JM", "home vs ranked ND", "hot ATS gap/5", "reb gap/6", "away small fav ND",
         "early road dog", "skid dog", "rubber dog", "cover run", "luck gap", "sd gap/5", "h2 gain gap/3", "pace gap/8",
         "top5 gap x10", "Sat->Mon/Tue road", "swing stop 2", "slate", "road", "neutral", "spread/10", "elo gap/100"]
X = np.array([feats(x) for x in rows])
y = np.array([x["margin"] + x["sp"] for x in rows])
S = np.array([x["season"] for x in rows])
lam = 50.0
o.h("A. The full fit 2018-22 (train) - coefficients in points of cover margin, with t-stats")
tr = (S >= 2018) & (S <= 2022)
A = X[tr].T @ X[tr] + lam * np.eye(X.shape[1])
beta = np.linalg.solve(A, X[tr].T @ y[tr])
res = y[tr] - X[tr] @ beta
s2 = res @ res / (tr.sum() - X.shape[1])
cov = s2 * np.linalg.inv(A)
for n, b, se in zip(NAMES, beta, np.sqrt(np.diag(cov))):
    o.note(f"  {n:20s} {b:+.3f} pts  (t {b / se:+.1f})")
o.h("B. Walk-forward: each held season graded on a fit of the seasons before it; ATS by predicted-edge bin")
cells = 0
for s in (2023, 2024, 2025):
    fit = (S >= 2018) & (S < s)
    A = X[fit].T @ X[fit] + lam * np.eye(X.shape[1])
    b = np.linalg.solve(A, X[fit].T @ y[fit])
    pred = X[S == s] @ b
    R = [x for x in rows if x["season"] == s]
    for lo, hi in ((-99, -2), (-2, -1), (-1, 0), (0, 1), (1, 2), (2, 99)):
        pick = [x for x, p in zip(R, pred) if lo <= p < hi]
        prof = [lib.profit_ats(x) for x in pick]
        prof = [p for p in prof if p is not None]
        cells += 1
        if prof:
            o.note(f"  {s} pred {lo:+d}..{hi:+d}: n {len(prof):5d} ATS {100 * sum(prof) / len(prof):+5.1f}%  "
                   f"mean cover margin {sum(x['margin'] + x['sp'] for x in pick) / len(pick):+.2f}")
o.h("C. Walk-forward on the NEW three alone (ranked road ND, hot gap, reb gap + road / spread / elo)")
keep = [0, 1, 3, 4, 5, 19, 20, 21, 22]
X3 = X[:, keep]
for s in (2023, 2024, 2025):
    fit = (S >= 2018) & (S < s)
    A = X3[fit].T @ X3[fit] + lam * np.eye(X3.shape[1])
    b = np.linalg.solve(A, X3[fit].T @ y[fit])
    pred = X3[S == s] @ b
    R = [x for x in rows if x["season"] == s]
    for lo, hi in ((-99, -1.5), (-1.5, -0.5), (-0.5, 0.5), (0.5, 1.5), (1.5, 99)):
        pick = [x for x, p in zip(R, pred) if lo <= p < hi]
        prof = [lib.profit_ats(x) for x in pick]
        prof = [p for p in prof if p is not None]
        cells += 1
        if prof:
            o.note(f"  {s} pred {lo:+.1f}..{hi:+.1f}: n {len(prof):5d} ATS {100 * sum(prof) / len(prof):+5.1f}%")
    o.note("  coefficients: " + ", ".join(f"{NAMES[k]} {v:+.2f}" for k, v in zip(keep, b)))
o.cells += cells
o.save()
