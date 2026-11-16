"""H30-H41 - COLLEGE FOOTBALL: the big-size candidates on the 11/14 football replay board (today's code, every football
board day 2018-08 -> 2026-11-13, closes; train = seasons 2018-22, held out = 2023-26). The paid odds history
(early_1111) is the early number, not the board's - not re-pulled."""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M

rec = M.rec
R, seen = [], set()
for fp in sorted(glob.glob(os.path.expanduser("~/.cache/d503_fb1114/rows/f*.jsonl"))):
    for ln in open(fp):
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r["league"] != "ncaaf" or r["market"] != "ml" or r.get("result") not in ("won", "lost", "push"):
            continue
        k = (r["date"], r["gid"], r["side"])
        if k in seen:
            continue
        seen.add(k)
        y, m = int(r["date"][:4]), int(r["date"][5:7])
        r["season"] = y if m >= 7 else y - 1
        r["win"] = r["result"] == "won"
        r["pnl"] = 0.0 if r["result"] == "push" else ((r["dec"] - 1) if r["win"] else -1.0)
        r["own"] = None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]
        r["lift"] = None if (r.get("w_p") is None or r["own"] is None) else r["w_p"] - r["own"]
        r["where"] = "neutral" if r.get("neutral") else ("home" if r["home"] else "road")
        r["month"] = r["date"][5:7]
        R.append(r)
print(len(R), "college football moneyline sides")
DOG = [r for r in R if 100 <= r["odds"] <= 350]
FAV = [r for r in R if -150 <= r["odds"] <= -101]
PASS = [r for r in DOG if r.get("dog_own_ok")]
print("== DOGS +100..+350")
rec("H30 the college Dog of the Day (posted)", [r for r in DOG if r["kind"] == "dog"], DOG, kelly=True)
rec("H31 ... at a dog score of 8+", [r for r in DOG if r["kind"] == "dog" and (r.get("dog_score") or 0) >= 8], DOG, kelly=True)
rec("    ... under 8", [r for r in DOG if r["kind"] == "dog" and (r.get("dog_score") or 0) < 8], DOG)
rec("H32 ... at +100..+150", [r for r in DOG if r["kind"] == "dog" and r["odds"] <= 150], DOG, kelly=True)
rec("H33 every dog the own read AND the honest weighed check pass", PASS, DOG, kelly=True)
rec("H34 ... ROAD (the 11/12 lead: +13% both halves)", [r for r in PASS if r["where"] == "road"], DOG, kelly=True)
rec("    ... HOME", [r for r in PASS if r["where"] == "home"], DOG, kelly=True)
rec("H35 ... HOME at +100..+150", [r for r in PASS if r["where"] == "home" and r["odds"] <= 150], DOG, kelly=True)
rec("H36 ... dog score 8+", [r for r in PASS if (r.get("dog_score") or 0) >= 8], DOG, kelly=True)
rec("    ... dog score 10+", [r for r in PASS if (r.get("dog_score") or 0) >= 10], DOG, kelly=True)
rec("H37 ... the study part (dog_base) 6+", [r for r in PASS if (r.get("dog_base") or 0) >= 6], DOG, kelly=True)
rec("H38 ... October-November (league play)", [r for r in PASS if r["month"] in ("10", "11")], DOG, kelly=True)
rec("    ... August-September", [r for r in PASS if r["month"] in ("08", "09")], DOG)
print("== FAVORITES -150..-101")
rec("H39 the college Lock (posted)", [r for r in FAV if r["kind"] == "lock"], FAV, kelly=True)
rec("    ... -150..-131", [r for r in FAV if r["kind"] == "lock" and r["odds"] <= -131], FAV, kelly=True)
print("   the hoops max play's twin: a favorite the studies on the dog across LIFT (weighed read minus own read)")
for a, b in ((-1, -0.02), (-0.02, 0), (0.0001, 0.02), (0.02, 0.03), (0.03, 1)):
    rec(f"H40 lift {100 * a:+.1f}..{100 * b:+.1f} pts", [r for r in FAV if r["lift"] is not None and a <= r["lift"] < b], FAV)
rec("H41 lift 2+ and the weighed read over the price", [r for r in FAV if (r["lift"] or 0) >= 0.02 and r["w_p"] * r["dec"] >= 1], FAV, kelly=True)
rec("    lift 2+, weighed over, 56%+", [r for r in FAV if (r["lift"] or 0) >= 0.02 and r["w_p"] * r["dec"] >= 1 and r["p"] >= 0.56], FAV, kelly=True)
rec("    lift 2+, weighed over, the own read UNDER the price", [r for r in FAV if (r["lift"] or 0) >= 0.02 and r["w_p"] * r["dec"] >= 1 and r["edge_own"] < 0], FAV, kelly=True)
rec("    lift 2+, weighed over, the own read over the price", [r for r in FAV if (r["lift"] or 0) >= 0.02 and r["w_p"] * r["dec"] >= 1 and r["edge_own"] >= 0], FAV)
