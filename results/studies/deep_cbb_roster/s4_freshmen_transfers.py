"""S4 - FRESHMAN-HEAVY and TRANSFER-HEAVY teams, early vs late (the market learning a new roster).

sf_new = this season's minutes SO FAR (before tonight) by men with no D1 box score in any earlier season we hold
(freshmen, JUCO, overseas, D2 transfers); sf_tin = by D1 transfers; sf_ret = by returners. Each season cut in thirds
(the team-side rows of that season's games 2+). Part of season: games 2-5 / 6-10 / 11-20 / 21+ and Nov-Dec vs Jan-Mar.
Graded at the close: ATS (every side), dogs +100..+350, favorites -101..-250; the PRE transfer share (tin_pts top third)
in games 1-5 too (the s2 ML shape). Read against the base = the same window's middle third."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import table, cell, profit_ml, profit_ats, profit_open  # noqa: E402
import numpy as np

tb = [x for x in table() if x["stype"] == "2" and x["season"] >= 2022]
out = []


def P(s):
    print(s)
    out.append(s)


def thirds(key, pre=False):
    cut = {}
    for s in {x["season"] for x in tb}:
        v = sorted(x["f"][key] for x in tb if x["season"] == s and x["f"].get(key) is not None
                   and (pre or x["f"].get("sf_n", 0) >= 1))
        if len(v) > 30:
            cut[s] = (v[len(v) // 3], v[2 * len(v) // 3])
    return cut


def lvl(x, key, cut):
    v = x["f"].get(key)
    c = cut.get(x["season"])
    if v is None or not c:
        return None
    return "LOW" if v < c[0] else "HIGH" if v >= c[1] else "mid"


WINS = {"g2-5": lambda x: 2 <= x["gn"] <= 5, "g6-10": lambda x: 6 <= x["gn"] <= 10,
        "g11-20": lambda x: 11 <= x["gn"] <= 20, "g21+": lambda x: x["gn"] >= 21}
for key in ("sf_new", "sf_tin", "sf_ret"):
    cut = thirds(key)
    P(f"=== {key} thirds by season: " + ", ".join(f"{s} {a:.2f}/{b:.2f}" for s, (a, b) in sorted(cut.items())))
    for w, wf in WINS.items():
        for lv in ("HIGH", "LOW"):
            xs = [x for x in tb if wf(x) and lvl(x, key, cut) == lv]
            cell(f"{key} {lv:4s} {w:6s} ATS", xs, profit_ats, out)
            cell(f"{key} {lv:4s} {w:6s} dog", [x for x in xs if x.get("ml") and 100 <= x["ml"] <= 350], profit_ml, out)
            cell(f"{key} {lv:4s} {w:6s} fav", [x for x in xs if x.get("ml") and -250 <= x["ml"] <= -101], profit_ml, out)
        # residual gap HIGH - LOW in points / win %
        gs = []
        for s in (2022, 2023, 2024, 2025):
            hi = [x for x in tb if x["season"] == s and wf(x) and lvl(x, key, cut) == "HIGH"]
            lo = [x for x in tb if x["season"] == s and wf(x) and lvl(x, key, cut) == "LOW"]
            ra = lambda xs: np.mean([x["margin"] + x["sp"] for x in xs if x.get("sp") is not None])
            rm = lambda xs: np.mean([x["won"] - x["p"] for x in xs if x.get("p") is not None]) * 100
            gs.append(f"{s} {ra(hi) - ra(lo):+5.2f}pt {rm(hi) - rm(lo):+5.1f}%")
        P(f"    HIGH - LOW {w}: " + " | ".join(gs))
P("=== PRE transfer points (tin_pts) thirds, games 1-5 (s2's ML shape) and the transfer x last-season-Elo (tin_q)")
for key in ("tin_pts", "tin_q", "ret_pts"):
    cut = thirds(key, pre=True)
    for w, wf in (("g1-5", lambda x: x["gn"] <= 5), ("g1-3", lambda x: x["gn"] <= 3), ("g6-10", lambda x: 6 <= x["gn"] <= 10)):
        for lv in ("HIGH", "LOW"):
            xs = [x for x in tb if wf(x) and x["f"].get("has_pre") and lvl(x, key, cut) == lv]
            cell(f"{key} {lv:4s} {w} ATS", xs, profit_ats, out)
            cell(f"{key} {lv:4s} {w} fav -101..-250", [x for x in xs if x.get("ml") and -250 <= x["ml"] <= -101], profit_ml, out)
            cell(f"{key} {lv:4s} {w} fav -251..-1000", [x for x in xs if x.get("ml") and -1000 <= x["ml"] <= -251], profit_ml, out)
            cell(f"{key} {lv:4s} {w} dog", [x for x in xs if x.get("ml") and 100 <= x["ml"] <= 350], profit_ml, out)
            cell(f"{key} {lv:4s} {w} dog @OPEN", [x for x in xs if x.get("mlo") and 100 <= x["mlo"] <= 350], profit_open, out)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s4_out.txt"), "w").write("\n".join(out) + "\n")
