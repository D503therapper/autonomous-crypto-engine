"""S5b - the new-look dog with a definition the engine can compute live: source-team strength = its average scoring
margin per game LAST season (every final we hold) instead of the study Elo; tin_m = sum over the roster's D1 transfers
of (last-season points x source margin / 10) / this team's last-season points. Roster = the men in this season's box
scores BEFORE tonight (strict - by game 6 the rotation has shown up). A FIXED cut (no in-season thirds)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import table, cell, profit_ml, profit_open, profit_ats  # noqa: E402
from lib import load_box, rows, season_lines  # noqa: E402
import numpy as np
from collections import defaultdict

rws = rows()
box, names, starts = load_box()
P_, T_ = season_lines(box, starts, rws)
marg = defaultdict(list)
for x in rws:
    marg[(x["season"], x["team"])].append(x["margin"])
avgm = {k: np.mean(v) for k, v in marg.items()}
tb = [x for x in table() if x["stype"] == "2" and x["season"] >= 2022]
allrows = defaultdict(list)
for x in rws:
    if x["season"] >= 2022:
        allrows[(x["season"], x["team"])].append(x)
tm = {}
for (s, t), xs in allrows.items():
    xs.sort(key=lambda x: x["start"])
    R = set()
    TL = T_[s - 1].get(t)
    for x in xs:
        val = None
        if TL and TL[1] > 0 and R:
            v = 0.0
            for pid in R:
                for ot, a in (P_[s - 1].get(pid) or {}).items():
                    if ot != t:
                        v += a[1] * avgm.get((s - 1, ot), 0) / 10
            val = v / TL[1]
        tm[(x["id"], t)] = val
        b = (box.get(x["id"]) or {}).get(t)
        if b:
            R |= {p for p, r in b.items() if r[0] > 0}
for x in tb:
    x["tin_m"] = tm.get((x["id"], x["team"]))
out = []


def P(s):
    print(s)
    out.append(s)


v = sorted(x["tin_m"] for x in tb if x["tin_m"] is not None and 6 <= x["gn"] <= 10)
P("tin_m quantiles g6-10 (25/50/67/75/90%): " + str([round(v[int(len(v) * q)], 3) for q in (0.25, 0.5, 0.667, 0.75, 0.9)]))
for s in (2022, 2023, 2024, 2025):
    w = sorted(x["tin_m"] for x in tb if x["tin_m"] is not None and 6 <= x["gn"] <= 10 and x["season"] == s)
    P(f"{s} top-third cut {w[2 * len(w) // 3]:.3f}")
dog = lambda x: x.get("ml") is not None and 100 <= x["ml"] <= 350
for cut in (0.03, 0.06):
    for w, (a, b) in (("g2-5", (2, 5)), ("g6-10", (6, 10)), ("g11-15", (11, 15)), ("g16+", (16, 99))):
        cell(f"dog tin_m >= {cut} {w}", [x for x in tb if a <= x["gn"] <= b and dog(x) and (x["tin_m"] or -9) >= cut], profit_ml, out)
    cell(f"dog tin_m >= {cut} g6-10 @OPEN", [x for x in tb if 6 <= x["gn"] <= 10 and x.get("mlo") and 100 <= x["mlo"] <= 350 and (x["tin_m"] or -9) >= cut], profit_open, out)
    cell(f"fav -101..-250 tin_m >= {cut} g6-10", [x for x in tb if 6 <= x["gn"] <= 10 and x.get("ml") and -250 <= x["ml"] <= -101 and (x["tin_m"] or -9) >= cut], profit_ml, out)
cell("base: dog tin_m < 0.03 g6-10", [x for x in tb if 6 <= x["gn"] <= 10 and dog(x) and x["tin_m"] is not None and x["tin_m"] < 0.03], profit_ml, out)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s5b_out.txt"), "w").write("\n".join(out) + "\n")
