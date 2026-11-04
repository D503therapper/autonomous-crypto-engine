"""The live cuts: the season-by-season terciles behind s4's identities (turnover margin, offense / defense vs the D1
average) and s3's roster shares, so sports.py can carry fixed constants (python cuts.py prints them)."""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *  # noqa: F401,F403

TB = teambox()
rows_ = [x for x in regular(rows()) if x["season"] >= 2021]
rows_.sort(key=lambda x: (x["start"], x["id"]))
score = {(x["id"], x["team"]): (x["pts"] + x["margin"]) / 2 for x in rows_}
agg, lg, feat = defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(float)), {}
for x in rows_:
    s, tm, op = x["season"], x["team"], x["opp"]
    a, L = agg[(s, tm)], lg[s]
    if a["n"] >= 5 and L["n"] >= 200:
        feat[(x["id"], tm)] = (100 * a["pts"] / a["poss"] - 100 * L["pts"] / L["poss"],
                               100 * a["opts"] / a["oposs"] - 100 * L["pts"] / L["poss"], (a["oto"] - a["to"]) / a["n"])
    b = TB.get(x["id"])
    if b and tm in b and op in b and (x["id"], tm) in score and (x["id"], op) in score:
        me, th = b[tm], b[op]
        for d in (a, L):
            d["n"] += 1; d["pts"] += score[(x["id"], tm)]; d["poss"] += me["poss"]; d["opts"] += score[(x["id"], op)]
            d["oposs"] += th["poss"]; d["to"] += me["to"]; d["oto"] += th["to"]
for i, name in enumerate(("off", "def", "tom")):
    by = defaultdict(list)
    for x in rows_:
        f = feat.get((x["id"], x["team"]))
        if f:
            by[x["season"]].append(f[i])
    for s, v in sorted(by.items()):
        v.sort()
        print(name, s, "terciles %.2f / %.2f" % (v[len(v) // 3], v[2 * len(v) // 3]), "n", len(v))
