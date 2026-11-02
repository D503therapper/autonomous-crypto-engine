"""S2 - TEAM LEVEL: does the preseason roster predict how a team does AGAINST THE NUMBER over its first games?
(More power than game by game: 5 games average the noise down.) Per team-season: the mean of (margin + closing spread)
over the team's games 1-5 / 6-10 / 11-20 / 21+ (every priced game, any opponent), regressed on its PRE roster features
one at a time, season by season; then the extremes (bottom / top tenth) as cells. Also at the OPEN: the mean of
(won - the open's no-vig win chance) over games 1-5 (2023-25, the ML open)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import table  # noqa: E402
import numpy as np
from collections import defaultdict

tb = [x for x in table() if x["f"].get("has_pre") and x["stype"] == "2"]
out = []


def P(s):
    print(s)
    out.append(s)


WIN = {"g1-5": (1, 5), "g6-10": (6, 10), "g11-20": (11, 20), "g21+": (21, 99)}
agg = defaultdict(lambda: defaultdict(list))
openr = defaultdict(list)
mlr = defaultdict(list)
F = {}
for x in tb:
    k = (x["season"], x["team"])
    F[k] = x["f"]
    if x.get("sp") is not None:
        for w, (lo, hi) in WIN.items():
            if lo <= x["gn"] <= hi:
                agg[k][w].append(x["margin"] + x["sp"])
    if 1 <= x["gn"] <= 5:
        if x.get("po") is not None:
            openr[k].append(x["won"] - x["po"])
        if x.get("p") is not None:
            mlr[k].append(x["won"] - x["p"])

feats = {"ret_pts": lambda f: f["ret_pts"], "ret_min": lambda f: f["ret_min"], "tin_pts": lambda f: f["tin_pts"],
         "tin_q": lambda f: f["tin_q"], "tin_pow": lambda f: f["tin_pts_pow"], "n_new": lambda f: f["n_new"],
         "top1_back": lambda f: int(f["top1_back"]), "top2_back": lambda f: f["top2_back"],
         "roster(ret+tin)": lambda f: f["ret_pts"] + f["tin_pts"],
         "ret x last_elo": lambda f: f["ret_pts"] * ((f["last_elo"] or 1500) - 1500) / 100,
         "(1-ret) x last_elo": lambda f: (1 - f["ret_pts"]) * ((f["last_elo"] or 1500) - 1500) / 100,
         "last_elo": lambda f: ((f["last_elo"] or 1500) - 1500) / 100}


def slope(X, Y):
    X, Y = np.array(X, float), np.array(Y, float)
    Xc = X - X.mean()
    if (Xc ** 2).sum() == 0 or len(X) < 30:
        return None
    sl = (Xc * (Y - Y.mean())).sum() / (Xc ** 2).sum()
    res = Y - Y.mean() - sl * Xc
    se = np.sqrt((res ** 2).sum() / (len(X) - 2) / (Xc ** 2).sum())
    return sl, sl / se, len(X)


P("Per team-season: slope of the team's mean (margin + closing spread) on each preseason feature (points per 1.0; t)")
for fn, fx in feats.items():
    P(f"--- {fn}")
    for w in WIN:
        cs = []
        for s in (2022, 2023, 2024, 2025):
            X, Y = [], []
            for k, d in agg.items():
                if k[0] == s and len(d.get(w, [])) >= 2:
                    X.append(fx(F[k]))
                    Y.append(np.mean(d[w]))
            r = slope(X, Y)
            cs.append(f"{s} " + (f"{r[0]:+6.2f}({r[1]:+4.1f}) n{r[2]}" if r else "-"))
        P(f"  {w:7s} " + " | ".join(cs))
P("--- the same at the ML: mean (won - no-vig win chance) over games 1-5, slope per 1.0 (x100 = win-% points)")
for fn, fx in feats.items():
    cs = []
    for lab, src, ss in (("close", mlr, (2022, 2023, 2024, 2025)), ("open", openr, (2023, 2024, 2025))):
        for s in ss:
            X, Y = [], []
            for k, v in src.items():
                if k[0] == s and len(v) >= 2:
                    X.append(fx(F[k]))
                    Y.append(np.mean(v) * 100)
            r = slope(X, Y)
            cs.append(f"{lab}{s} " + (f"{r[0]:+6.1f}({r[1]:+4.1f})" if r else "-"))
    P(f"  {fn:20s} " + " | ".join(cs))
# extremes: bottom / top tenth of each feature within the season -> mean ATS residual games 1-5
P("--- extremes (within-season tenths): mean (margin + spread) games 1-5, bottom 10% vs top 10% (pts, n teams)")
for fn, fx in feats.items():
    cs = []
    for s in (2022, 2023, 2024, 2025):
        ks = [k for k in agg if k[0] == s and len(agg[k].get("g1-5", [])) >= 2]
        v = sorted(ks, key=lambda k: fx(F[k]))
        n = max(1, len(v) // 10)
        lo = np.mean([np.mean(agg[k]["g1-5"]) for k in v[:n]])
        hi = np.mean([np.mean(agg[k]["g1-5"]) for k in v[-n:]])
        cs.append(f"{s} lo {lo:+5.1f} hi {hi:+5.1f} (n{n})")
    P(f"  {fn:20s} " + " | ".join(cs))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s2_out.txt"), "w").write("\n".join(out) + "\n")
