"""S5 - THE NEW-LOOK DOG IN GAMES 6-10 (s4's shape): a college hoops dog +100..+350 whose roster leans on D1 transfers
(PRE tin_q / tin_pts top third of its season) - the dose by game window, the price band, venue, the early start (its
record vs its prices in games 1-5: did it under-perform early?), and the opponent's roster. Base = every other dog in
the same game window. Also the bet-free read: (won - no-vig) for those dogs by window."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import table, cell, profit_ml, profit_ats, profit_open  # noqa: E402
import numpy as np
from collections import defaultdict

tb = [x for x in table() if x["stype"] == "2" and x["season"] >= 2022 and x["f"].get("has_pre")]
out = []


def P(s):
    print(s)
    out.append(s)


def cuts(key):
    c = {}
    for s in {x["season"] for x in tb}:
        v = sorted(x["f"][key] for x in tb if x["season"] == s and x["gn"] == 1)
        if len(v) > 30:
            c[s] = (v[len(v) // 3], v[2 * len(v) // 3])
    return c


CQ, CP, CR = cuts("tin_q"), cuts("tin_pts"), cuts("ret_pts")
hi = lambda x, key, C: x["f"][key] >= C[x["season"]][1] if x["season"] in C else False
lo = lambda x, key, C: x["f"][key] < C[x["season"]][0] if x["season"] in C else False
# early form: the team's mean (won - no-vig) over its games 1-5 so far (strictly before tonight)
hist = defaultdict(list)
for x in sorted(tb, key=lambda x: x["start"]):
    k = (x["season"], x["team"])
    h = hist[k]
    x["early_res"] = np.mean([a for a in h[:5]]) if len(h) >= 3 else None
    if x.get("p") is not None:
        h.append(x["won"] - x["p"])
dog = lambda x: x.get("ml") is not None and 100 <= x["ml"] <= 350
NEW = lambda x: hi(x, "tin_q", CQ)
for w, (a, b) in (("g1-3", (1, 3)), ("g4-5", (4, 5)), ("g6-8", (6, 8)), ("g9-10", (9, 10)), ("g6-10", (6, 10)),
                  ("g11-15", (11, 15)), ("g16-20", (16, 20)), ("g21+", (21, 99))):
    xs = [x for x in tb if a <= x["gn"] <= b and dog(x)]
    cell(f"dog tin_q TOP third {w}", [x for x in xs if NEW(x)], profit_ml, out)
    cell(f"   base: every other dog {w}", [x for x in xs if not NEW(x)], profit_ml, out)
P("--- games 6-10, the tin_q top-third dog, split")
W = [x for x in tb if 6 <= x["gn"] <= 10 and dog(x) and NEW(x)]
for lab, sel in (("+100..+150", lambda x: x["ml"] <= 150), ("+151..+250", lambda x: 150 < x["ml"] <= 250),
                 ("+251..+350", lambda x: x["ml"] > 250), ("home", lambda x: x["venue"] == "home"),
                 ("road", lambda x: x["venue"] == "away"), ("neutral", lambda x: x["venue"] == "neutral"),
                 ("power", lambda x: x["tier"] == "power"), ("mid", lambda x: x["tier"] == "mid"),
                 ("low", lambda x: x["tier"] == "low"),
                 ("started BELOW its prices (games so far)", lambda x: x["early_res"] is not None and x["early_res"] < -0.05),
                 ("started at / above its prices", lambda x: x["early_res"] is not None and x["early_res"] >= -0.05),
                 ("opp ALSO transfer-heavy", lambda x: x["of"].get("tin_q") is not None and x["season"] in CQ and x["of"]["tin_q"] >= CQ[x["season"]][1]),
                 ("opp NOT transfer-heavy", lambda x: not (x["of"].get("tin_q") is not None and x["season"] in CQ and x["of"]["tin_q"] >= CQ[x["season"]][1])),
                 ("also LOW returning (ret_pts bottom third)", lambda x: lo(x, "ret_pts", CR)),
                 ("transfer pts top third too", lambda x: hi(x, "tin_pts", CP)),
                 ("last season's Elo over 1600", lambda x: (x["f"]["last_elo"] or 1500) > 1600),
                 ("last season's Elo 1600 or under", lambda x: (x["f"]["last_elo"] or 1500) <= 1600),
                 ("conference game", lambda x: x["same_conf"]), ("non-conference", lambda x: not x["same_conf"]),
                 ("ATS (same sides)", None), ("@OPEN (same sides, 2023-25)", "open")):
    if sel is None:
        cell(f"  {lab}", W, profit_ats, out)
    elif sel == "open":
        cell(f"  {lab}", [x for x in tb if 6 <= x["gn"] <= 10 and NEW(x) and x.get("mlo") and 100 <= x["mlo"] <= 350], profit_open, out)
    else:
        cell(f"  {lab}", [x for x in W if sel(x)], profit_ml, out)
P("--- the bet-free read: (won - no-vig) x100 for the tin_q top-third dogs vs other dogs, by window and season")
for w, (a, b) in (("g1-5", (1, 5)), ("g6-10", (6, 10)), ("g11-20", (11, 20)), ("g21+", (21, 99))):
    cs = []
    for s in (2022, 2023, 2024, 2025):
        n = [(x["won"] - x["p"]) * 100 for x in tb if x["season"] == s and a <= x["gn"] <= b and dog(x) and NEW(x)]
        o = [(x["won"] - x["p"]) * 100 for x in tb if x["season"] == s and a <= x["gn"] <= b and dog(x) and not NEW(x)]
        cs.append(f"{s} {np.mean(n) - np.mean(o):+5.1f} (n{len(n)})")
    P(f"  {w:7s} " + " | ".join(cs))
P("--- the same teams as FAVORITES -101..-250 and the same window for every side (ATS)")
for w, (a, b) in (("g1-5", (1, 5)), ("g6-10", (6, 10)), ("g11-20", (11, 20))):
    cell(f"fav tin_q TOP third {w}", [x for x in tb if a <= x["gn"] <= b and NEW(x) and x.get("ml") and -250 <= x["ml"] <= -101], profit_ml, out)
    cell(f"ATS tin_q TOP third {w}", [x for x in tb if a <= x["gn"] <= b and NEW(x)], profit_ats, out)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s5_out.txt"), "w").write("\n".join(out) + "\n")
