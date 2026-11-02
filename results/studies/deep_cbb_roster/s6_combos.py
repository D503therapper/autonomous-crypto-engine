"""S6 - THE TOP-SCORER-MISSED-LAST-GAME signal against the engine's EXISTING college hoops weights (is it new?), and the
pooled new-look game 6-10 dog (both sides of a transfer-heavy team's games).

Existing dog weights (sports.dog_spots, ncaab): 'we lost our last, they won theirs' -3 / 'the favorite lost its last' +2,
the 5+ game skid -2, the early true-road dog (games 1-3) -2, the rubber match -2, 2+ close wins in the last 5 -1;
favorites: the Nov-Dec small favorite away from home -3 on the read. Within each existing flag (and with none of them),
top-missed vs not: does the residual survive? Also a logistic fit (train 2022-23 -> held 2024-25) of won on the no-vig
close + the flags + top-missed, so the new term is read net of the old ones."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import table, cell, profit_ml, profit_ats  # noqa: E402
from lib import load_box  # noqa: E402
import numpy as np
from collections import defaultdict

tb = [x for x in table() if x["stype"] == "2" and x["season"] >= 2022]
box, _, _ = load_box()
order = defaultdict(list)
for x in tb:
    order[(x["season"], x["team"])].append(x)
for (s, t), xs in order.items():
    xs.sort(key=lambda x: x["start"])
    for i, x in enumerate(xs):
        st = x["f"].get("stars")
        x["top_miss"] = False
        if st and i:
            b = (box.get(xs[i - 1]["id"]) or {}).get(t)
            if b is not None:
                x["top_miss"] = st[0] not in b or b[st[0]][0] <= 0
        x["won_last"] = xs[i - 1]["won"] if i else None
idx = {(x["id"], x["team"]): x for x in tb}
for x in tb:
    o = idx.get((x["id"], x["opp"]))
    x["o_top_miss"] = o["top_miss"] if o else False
    x["o_won_last"] = o["won_last"] if o else None
out = []


def P(s):
    print(s)
    out.append(s)


def flags(x):
    f = []
    if x["won_last"] is False and x["o_won_last"] is True:
        f.append("lost/won")
    if x["o_won_last"] is False:
        f.append("fav lost last")
    if (x.get("streak") or 0) <= -5:
        f.append("skid5")
    if x["gn"] <= 3 and x["venue"] == "away":
        f.append("early road")
    return f


dogs = [x for x in tb if x.get("ml") and 100 <= x["ml"] <= 350 and x["f"].get("stars")]
P("=== dogs +100..+350 (stars defined): top scorer missed the last game vs not, WITHIN each existing weight's flag")
for lab, sel in (("no existing flag", lambda x: not flags(x)), ("'lost / won' (-3)", lambda x: "lost/won" in flags(x)),
                 ("'fav lost last' (+2)", lambda x: "fav lost last" in flags(x)), ("5+ skid (-2)", lambda x: "skid5" in flags(x)),
                 ("lost its last game (any)", lambda x: x["won_last"] is False),
                 ("WON its last game", lambda x: x["won_last"] is True)):
    a = [x for x in dogs if sel(x) and x["top_miss"] and not x["o_top_miss"]]
    b = [x for x in dogs if sel(x) and not x["top_miss"] and not x["o_top_miss"]]
    cell(f"top MISSED  | {lab}", a, profit_ml, out)
    cell(f"top played  | {lab}", b, profit_ml, out)
favs = [x for x in tb if x.get("ml") and -250 <= x["ml"] <= -101 and x["f"].get("stars")]
P("=== favorites -101..-250 ACROSS a dog whose top scorer missed its last game, within the dog's flags")
for lab, sel in (("dog has no flag", lambda o: not flags(o)), ("dog lost/won", lambda o: "lost/won" in flags(o)),
                 ("dog lost its last", lambda o: o["won_last"] is False), ("dog won its last", lambda o: o["won_last"] is True)):
    a = [x for x in favs if x["o_top_miss"] and not x["top_miss"] and idx.get((x["id"], x["opp"])) and sel(idx[(x["id"], x["opp"])])]
    b = [x for x in favs if not x["o_top_miss"] and not x["top_miss"] and idx.get((x["id"], x["opp"])) and sel(idx[(x["id"], x["opp"])])]
    cell(f"fav across top-MISSED | {lab}", a, profit_ml, out)
    cell(f"fav across top-played | {lab}", b, profit_ml, out)
# logistic: won ~ logit(p_close) + flags + top_miss + o_top_miss, train -> held
try:
    import math
    def feats(x):
        p = min(max(x["p"], 0.01), 0.99)
        fl = flags(x)
        return [math.log(p / (1 - p)), int("lost/won" in fl), int("fav lost last" in fl), int("skid5" in fl),
                int(x["top_miss"]), int(x["o_top_miss"])]
    names = ["logit_close", "lost/won", "opp lost last", "skid5", "TOP MISSED", "OPP TOP MISSED"]
    D = [x for x in tb if x.get("p") is not None and x["f"].get("stars") and x["side"] == "home"]

    def fit(rows):
        X = np.array([[1.0] + feats(x) for x in rows])
        y = np.array([float(x["won"]) for x in rows])
        w = np.zeros(X.shape[1])
        for _ in range(50):
            p = 1 / (1 + np.exp(-X @ w))
            g = X.T @ (y - p)
            H = (X * (p * (1 - p))[:, None]).T @ X + np.eye(X.shape[1]) * 1e-6
            w += np.linalg.solve(H, g)
        se = np.sqrt(np.diag(np.linalg.inv(H)))
        return w, se

    def ll(rows, w):
        X = np.array([[1.0] + feats(x) for x in rows])
        y = np.array([float(x["won"]) for x in rows])
        p = np.clip(1 / (1 + np.exp(-X @ w)), 1e-6, 1 - 1e-6)
        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    tr = [x for x in D if x["season"] in (2022, 2023)]
    w, se = fit(tr)
    P("=== logistic (home side rows, won ~ close + flags + roster), TRAIN 2022-23: " +
      ", ".join(f"{n} {a:+.3f} (t{a/s:+.1f})" for n, a, s in zip(["c"] + names, w, se)))
    wa, sea = fit(D)
    P("    ALL 2022-25: " + ", ".join(f"{n} {a:+.3f} (t{a/s:+.1f})" for n, a, s in zip(["c"] + names, wa, sea)))
    for s in (2024, 2025):
        he = [x for x in D if x["season"] == s]
        w0 = np.zeros_like(w)
        w0[1] = 1.0                       # the close alone
        P(f"    held {s}: log loss close {ll(he, w0):.5f} | train model {ll(he, w):.5f}")
except Exception as e:  # noqa: BLE001
    P(f"logistic failed: {e}")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s6_out.txt"), "w").write("\n".join(out) + "\n")
