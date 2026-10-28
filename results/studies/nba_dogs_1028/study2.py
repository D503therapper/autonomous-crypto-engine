"""Refinements of the 10/28 cells that showed life: dose-response, the holdout by season, overlap with built weights."""
import os
import pickle
import statistics
from collections import defaultdict

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
    return f"{w}-{len(rows)-w} {pnl/len(rows)*100:+.1f}% z{z:+.1f}"


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


print("=== HEAVY MINUTES: the favorite's top 3 by minutes last game ===")
M = [d for d in DOGS if d["o_last_top3_min"] is not None and d["o_rest"] is not None and d["o_g"] >= 5]
cell("all with the fav's last box", M)
for th in (35, 36, 37, 38, 39, 40):
    cell(f"fav top-3 avg {th}+ last game", [d for d in M if d["o_last_top3_min"] >= th])
cell("fav top-3 avg under 34 (control)", [d for d in M if d["o_last_top3_min"] < 34])
cell("fav top-3 38+ and NO OT last game (the built OT weight aside)", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"]])
cell("fav top-3 38+ and OT last game", [d for d in M if d["o_last_top3_min"] >= 38 and d["o_last_ot"]])
cell("fav OT last game, top-3 under 38", [d for d in M if d["o_last_top3_min"] < 38 and d["o_last_ot"]])
cell("fav top-3 38+, no OT, dog +100..+150", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and d["ml"] < 150])
cell("fav top-3 38+, no OT, dog +150..+250", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and 150 <= d["ml"] < 250])
cell("fav top-3 38+, no OT, dog +250..+350", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and d["ml"] >= 250])
cell("fav top-3 38+, no OT, home dog", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and d["home"]])
cell("fav top-3 38+, no OT, road dog", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and not d["home"]])
cell("fav top-3 38+, no OT, fav rest 1 (b2b)", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and d["o_rest"] <= 1])
cell("fav top-3 38+, no OT, fav rest 2", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and d["o_rest"] == 2])
cell("fav top-3 38+, no OT, fav rest 3+", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and d["o_rest"] >= 3])
cell("fav top-3 38+, no OT, fav WON last game", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and d["o_last_won"]])
cell("fav top-3 38+, no OT, fav LOST last game", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and not d["o_last_won"]])
cell("fav top-3 38+, no OT, last game close (within 5)", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and abs(d["o_last_margin"]) <= 5])
cell("fav top-3 38+, no OT, last game NOT close (6+)", [d for d in M if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and abs(d["o_last_margin"]) > 5])
cell("fav last game close (within 5), top-3 under 38 (control)", [d for d in M if d["o_last_top3_min"] < 38 and not d["o_last_ot"] and abs(d["o_last_margin"]) <= 5])
cell("the DOG's own top-3 38+ last game (its legs)", [d for d in M if d["last_top3_min"] is not None and d["last_top3_min"] >= 38])

print("\n=== MARGIN VARIANCE ===")
V = [d for d in DOGS if d["sd10"] is not None and d["o_sd10"] is not None]
bys = defaultdict(list)
for d in V:
    bys[d["season"]].append(d["sd10"])
q = {s: statistics.quantiles(v, n=4) for s, v in bys.items()}
for d in V:
    lo, mid, hi = q[d["season"]]
    d["sd_q"] = 0 if d["sd10"] < lo else (3 if d["sd10"] >= hi else (1 if d["sd10"] < mid else 2))
    d["o_sd_q"] = 0 if d["o_sd10"] < lo else (3 if d["o_sd10"] >= hi else (1 if d["o_sd10"] < mid else 2))
cell("steady fav (q0)", [d for d in V if d["o_sd_q"] == 0])
cell("steady fav (q0), dog +100-150", [d for d in V if d["o_sd_q"] == 0 and d["ml"] < 150])
cell("steady fav (q0), dog +150-250", [d for d in V if d["o_sd_q"] == 0 and 150 <= d["ml"] < 250])
cell("steady fav (q0), dog +250-350", [d for d in V if d["o_sd_q"] == 0 and d["ml"] >= 250])
cell("fav sd10 under 9 points (absolute)", [d for d in V if d["o_sd10"] < 9])
cell("fav sd10 under 10 points", [d for d in V if d["o_sd10"] < 10])
cell("fav sd10 16+ (wild fav, fade?)", [d for d in V if d["o_sd10"] >= 16])
cell("wild dog (q3)", [d for d in V if d["sd_q"] == 3])
cell("dog sd10 16+ (absolute)", [d for d in V if d["sd10"] >= 16])
cell("wild dog q3 vs steady fav q0", [d for d in V if d["sd_q"] == 3 and d["o_sd_q"] == 0])
cell("dog sd10 - fav sd10 >= 6", [d for d in V if d["sd10"] - d["o_sd10"] >= 6])
cell("dog sd10 - fav sd10 >= 4", [d for d in V if d["sd10"] - d["o_sd10"] >= 4])
cell("fav sd10 - dog sd10 >= 4 (fade?)", [d for d in V if d["o_sd10"] - d["sd10"] >= 4])
cell("big dog +200+, wild q3", [d for d in V if d["sd_q"] == 3 and d["ml"] >= 200])

print("\n=== THE FAVORITE'S NEXT GAME IS EASY (a fade on the dog?) ===")
L = [d for d in DOGS if d["o_next_opp_elo"] is not None and d["o_g"] >= 10]
cell("fav's next opp Elo under 1450 within 2 days", [d for d in L if d["o_next_opp_elo"] < 1450 and d["o_next_days"] <= 2])
cell("fav's next opp Elo under 1450 within 3 days", [d for d in L if d["o_next_opp_elo"] < 1450 and d["o_next_days"] <= 3])
cell("fav's next opp Elo under 1430 within 2 days", [d for d in L if d["o_next_opp_elo"] < 1430 and d["o_next_days"] <= 2])
cell("fav's next opp Elo under 1470 within 2 days", [d for d in L if d["o_next_opp_elo"] < 1470 and d["o_next_days"] <= 2])
cell("fav's next opp 50+ Elo WORSE than tonight's dog, 2 days", [d for d in L if d["elo"] - d["o_next_opp_elo"] >= 50 and d["o_next_days"] <= 2])
cell("fav's next opp 100+ Elo worse than the dog, 2 days", [d for d in L if d["elo"] - d["o_next_opp_elo"] >= 100 and d["o_next_days"] <= 2])
cell("fav's next opp under 1450, dog itself under 1450 too", [d for d in L if d["o_next_opp_elo"] < 1450 and d["o_next_days"] <= 2 and d["elo"] < 1450])
cell("fav's next opp under 1450, dog 1450+", [d for d in L if d["o_next_opp_elo"] < 1450 and d["o_next_days"] <= 2 and d["elo"] >= 1450])
cell("fav's next opp under 1450, fav's game-in 10-40", [d for d in L if d["o_next_opp_elo"] < 1450 and d["o_next_days"] <= 2 and d["o_g"] <= 40])
cell("fav's next opp under 1450, fav's game-in 41+", [d for d in L if d["o_next_opp_elo"] < 1450 and d["o_next_days"] <= 2 and d["o_g"] > 40])
cell("DOG's next opp under 1450 within 2 days (control)", [d for d in L if d["next_opp_elo"] is not None and d["next_opp_elo"] < 1450 and d["next_days"] <= 2])

print("\n=== SLATE SIZE ===")
for n in (11, 12, 13):
    cell(f"slate {n}+ games", [d for d in DOGS if d["slate"] >= n])
cell("slate 12+, dog +100-150", [d for d in DOGS if d["slate"] >= 12 and d["ml"] < 150])
cell("slate 12+, dog +150-250", [d for d in DOGS if d["slate"] >= 12 and 150 <= d["ml"] < 250])
cell("slate 12+, dog +250-350", [d for d in DOGS if d["slate"] >= 12 and d["ml"] >= 250])
cell("slate 12+, home dog", [d for d in DOGS if d["slate"] >= 12 and d["home"]])
cell("slate 12+, road dog", [d for d in DOGS if d["slate"] >= 12 and not d["home"]])

print("\n=== STACK: heavy-minutes fav (38+, no OT) + steady fav (q0) ===")
for d in M:
    pass
VM = [d for d in V if d["o_last_top3_min"] is not None and d["o_g"] >= 5]
cell("heavy fav AND steady fav", [d for d in VM if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and d["o_sd_q"] == 0])
cell("heavy fav AND wild dog", [d for d in VM if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and d["sd_q"] == 3])
cell("heavy fav, NOT steady fav", [d for d in VM if d["o_last_top3_min"] >= 38 and not d["o_last_ot"] and d["o_sd_q"] != 0])
cell("steady fav, NOT heavy", [d for d in VM if not (d["o_last_top3_min"] >= 38 and not d["o_last_ot"]) and d["o_sd_q"] == 0])
