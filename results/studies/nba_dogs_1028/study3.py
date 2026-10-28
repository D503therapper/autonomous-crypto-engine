"""The two wire candidates in the form the live engine can read: the favorite's next opponent by RECORD (the schedule
holds records, not an Elo lookup) and the slate size, plus a weekday check on the slate."""
import os
import pickle
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(__file__)
sides = pickle.load(open(os.path.join(HERE, "sides.pkl"), "rb"))
DOGS = [d for d in sides if 100 <= d["ml"] <= 350]
TRAIN = {2018, 2019, 2020, 2021, 2022, 2023}


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def roi(rows):
    if not rows:
        return "0-0"
    w = sum(1 for d in rows if d["won"])
    pnl = sum((dec(d["ml"]) - 1) if d["won"] else -1 for d in rows)
    var = sum(d["nv"] * (1 - d["nv"]) for d in rows)
    z = (w - sum(d["nv"] for d in rows)) / var ** 0.5 if var else 0
    return f"{w}-{len(rows)-w} {pnl/len(rows)*100:+.1f}% ({w/len(rows)*100:.1f} vs {100*sum(d['nv'] for d in rows)/len(rows):.1f}) z{z:+.1f}"


def cell(name, rows):
    tr = [d for d in rows if d["season"] in TRAIN]
    by = defaultdict(list)
    for d in tr:
        by[d["season"]].append(d)
    ups = sum(1 for s in by if roi(by[s]).split()[1].startswith("+"))
    s = f"  {name:58s} | train {roi(tr)} ({ups}/{len(by)} up)"
    for y in (2024, 2025, 2026):
        s += f" | {y} {roi([d for d in rows if d['season'] == y])}"
    print(s)


print("=== THE FAVORITE'S NEXT GAME IS SOFT - by the next opponent's RECORD ===")
L = [d for d in DOGS if d["o_next_opp_wp"] is not None and d["o_next_opp_g"] >= 10 and d["o_g"] >= 10]
cell("all with a next game (10+ games in)", L)
for wp in (.35, .40, .45):
    cell(f"fav's next opp under .{int(wp*100)} within 2 days", [d for d in L if d["o_next_opp_wp"] < wp and d["o_next_days"] <= 2])
cell("fav's next opp under .400 within 3 days", [d for d in L if d["o_next_opp_wp"] < .40 and d["o_next_days"] <= 3])
cell("fav's next opp under .400, next day", [d for d in L if d["o_next_opp_wp"] < .40 and d["o_next_days"] <= 1])
cell("fav's next opp .400-.550 within 2 days (control)", [d for d in L if .40 <= d["o_next_opp_wp"] < .55 and d["o_next_days"] <= 2])
cell("fav's next opp .600+ within 2 days (the marquee look-ahead)", [d for d in L if d["o_next_opp_wp"] >= .60 and d["o_next_days"] <= 2])
cell("fav's next opp under .400, AND under .400 record is worse than the dog's", [d for d in L if d["o_next_opp_wp"] < .40 and d["o_next_days"] <= 2 and d["wp"] is not None and d["o_next_opp_wp"] < d["wp"]])
cell("fav's next opp under .400 (2 days), dog +100-150", [d for d in L if d["o_next_opp_wp"] < .40 and d["o_next_days"] <= 2 and d["ml"] < 150])
cell("fav's next opp under .400 (2 days), dog +150-250", [d for d in L if d["o_next_opp_wp"] < .40 and d["o_next_days"] <= 2 and 150 <= d["ml"] < 250])
cell("fav's next opp under .400 (2 days), dog +250-350", [d for d in L if d["o_next_opp_wp"] < .40 and d["o_next_days"] <= 2 and d["ml"] >= 250])
cell("fav's next opp under .400 (2 days), home dog", [d for d in L if d["o_next_opp_wp"] < .40 and d["o_next_days"] <= 2 and d["home"]])
cell("fav's next opp under .400 (2 days), road dog", [d for d in L if d["o_next_opp_wp"] < .40 and d["o_next_days"] <= 2 and not d["home"]])
cell("DOG's next opp under .400 within 2 days (control)", [d for d in DOGS if d["next_opp_wp"] is not None and d["next_opp_g"] >= 10 and d["next_opp_wp"] < .40 and d["next_days"] <= 2])

print("\n=== SLATE 12+ vs the weekday ===")
for d in DOGS:
    d["wd"] = datetime.strptime(d["day"], "%Y-%m-%d").weekday()
for wd, nm in enumerate("Mon Tue Wed Thu Fri Sat Sun".split()):
    cell(f"{nm}, all dogs", [d for d in DOGS if d["wd"] == wd])
for wd, nm in enumerate("Mon Tue Wed Thu Fri Sat Sun".split()):
    r = [d for d in DOGS if d["wd"] == wd and d["slate"] >= 12]
    if len(r) >= 40:
        cell(f"{nm}, slate 12+", r)
cell("slate 12+ (Wed/Fri excluded)", [d for d in DOGS if d["slate"] >= 12 and d["wd"] not in (2, 4)])
cell("slate 9-11 (control)", [d for d in DOGS if 9 <= d["slate"] <= 11])
cell("slate 12+, 10/21 dog-score-ish: no fade flags", [d for d in DOGS if d["slate"] >= 12])
cell("slate 12+, fav's next game soft (both)", [d for d in DOGS if d["slate"] >= 12 and d["o_next_opp_wp"] is not None and d["o_next_opp_g"] >= 10 and d["o_next_opp_wp"] < .40 and (d["o_next_days"] or 9) <= 2])
cell("slate 12+, fav's next game NOT soft", [d for d in DOGS if d["slate"] >= 12 and not (d["o_next_opp_wp"] is not None and d["o_next_opp_g"] >= 10 and d["o_next_opp_wp"] < .40 and (d["o_next_days"] or 9) <= 2)])
