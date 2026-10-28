"""10/28 NBA DOG STUDIES - reality check + 5 angles. Dogs +100..+350 at the close, flat 1u.
Train = seasons 2018-23, HOLDOUT = 2024-25, NOW = 2026 (a few weeks)."""
import os
import pickle
import statistics
from collections import defaultdict

HERE = os.path.dirname(__file__)
sides = pickle.load(open(os.path.join(HERE, "sides.pkl"), "rb"))
DOGS = [d for d in sides if 100 <= d["ml"] <= 350]
TRAIN = {2018, 2019, 2020, 2021, 2022, 2023}
HOLD = {2024, 2025}


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def roi(rows):
    if not rows:
        return 0, 0, 0.0, 0.0, 0.0, 0.0
    w = sum(1 for d in rows if d["won"])
    pnl = sum((dec(d["ml"]) - 1) if d["won"] else -1 for d in rows)
    imp = sum(d["nv"] for d in rows) / len(rows)
    var = sum(d["nv"] * (1 - d["nv"]) for d in rows)
    z = (w - sum(d["nv"] for d in rows)) / var ** 0.5 if var else 0
    return len(rows), w, pnl / len(rows) * 100, w / len(rows) * 100, imp * 100, z


def seasons_up(rows):
    by = defaultdict(list)
    for d in rows:
        by[d["season"]].append(d)
    ups = [s for s, r in by.items() if roi(r)[2] > 0 and len(r) >= 5]
    return len(ups), len([s for s in by if len(by[s]) >= 5])


def cell(name, rows, base=None):
    out = []
    for lab, S in (("train", TRAIN), ("hold", HOLD), ("now", {2026})):
        r = [d for d in rows if d["season"] in S]
        n, w, ro, wp, imp, z = roi(r)
        if lab == "train":
            u, t = seasons_up(r)
            out.append(f"train {w}-{n-w} {ro:+.1f}% ({wp:.1f} vs {imp:.1f}, z {z:+.1f}, {u}/{t} up)")
        else:
            out.append(f"{lab} {w}-{n-w} {ro:+.1f}% ({wp:.1f} vs {imp:.1f}, z {z:+.1f})")
    print(f"  {name:62s} | " + " | ".join(out))


def band(d):
    return "+100-150" if d["ml"] < 150 else ("+150-250" if d["ml"] < 250 else "+250-350")


print("=== REALITY CHECK: NBA dogs +100..+350 at the close, flat 1u (win % vs the no-vig implied) ===")
by = defaultdict(list)
for d in DOGS:
    by[(d["season"], band(d))].append(d)
    by[(d["season"], "all")].append(d)
for s in sorted({k[0] for k in by}):
    line = []
    for b in ("all", "+100-150", "+150-250", "+250-350"):
        n, w, ro, wp, imp, z = roi(by[(s, b)])
        line.append(f"{b} {w}-{n-w} {wp:.1f}% vs {imp:.1f}% implied, {ro:+.1f}%")
    print(f"  {s}-{str(s+1)[2:]}: " + " | ".join(line))
for b in ("all", "+100-150", "+150-250", "+250-350"):
    n, w, ro, wp, imp, z = roi([d for d in DOGS if band(d) == b or b == "all"])
    print(f"  ALL {b}: {w}-{n-w}, won {wp:.1f}% vs {imp:.1f}% implied (raw price says {100*sum(1/dec(d['ml']) for d in DOGS if band(d)==b or b=='all')/n:.1f}%), flat ROI {ro:+.1f}%, z {z:+.1f}")
print("  home dogs:"); cell("home", [d for d in DOGS if d["home"]]); cell("road", [d for d in DOGS if not d["home"]])

print("\n=== STUDY 1: THREES / VARIANCE - the dog's three-point rate (last 10 box scores, 3PA / FGA), the favorite's; 3P% luck ===")
D = [d for d in DOGS if d["tp_rate"] is not None and d["o_tp_rate"] is not None and d["g"] >= 10 and d["o_g"] >= 10]
# relative to the league's season-to-date: use rank within season by quantile
bys = defaultdict(list)
for d in D:
    bys[d["season"]].append(d["tp_rate"])
q = {s: (statistics.quantiles(v, n=4)) for s, v in bys.items()}
for d in D:
    lo, mid, hi = q[d["season"]]
    d["tp_q"] = 0 if d["tp_rate"] < lo else (3 if d["tp_rate"] >= hi else (1 if d["tp_rate"] < mid else 2))
    d["o_tp_q"] = 0 if d["o_tp_rate"] < lo else (3 if d["o_tp_rate"] >= hi else (1 if d["o_tp_rate"] < mid else 2))
cell("all with box", D)
for k in range(4):
    cell(f"dog 3PA-rate quartile {k} (3 = most threes)", [d for d in D if d["tp_q"] == k])
for k in range(4):
    cell(f"favorite 3PA-rate quartile {k}", [d for d in D if d["o_tp_q"] == k])
cell("high-3 dog (q3) vs low-3 fav (q0/1)", [d for d in D if d["tp_q"] == 3 and d["o_tp_q"] <= 1])
cell("low-3 dog (q0) vs high-3 fav (q2/3)", [d for d in D if d["tp_q"] == 0 and d["o_tp_q"] >= 2])
cell("dog shoots 3s 5+ pts of rate more than fav", [d for d in D if d["tp_rate"] - d["o_tp_rate"] >= .05])
cell("dog shoots 3s 5+ pts of rate LESS than fav", [d for d in D if d["o_tp_rate"] - d["tp_rate"] >= .05])
cell("big dog +200..+350, high-3 (q3)", [d for d in D if d["tp_q"] == 3 and d["ml"] >= 200])
cell("big dog +200..+350, low-3 (q0)", [d for d in D if d["tp_q"] == 0 and d["ml"] >= 200])
# 3P% luck: season-to-date 3P% over last 10 vs its last game
cell("dog hot from 3 last game (45%+ on 25+ att)", [d for d in D if d["last_tp_pct"] is not None and d["last_tpa"] and d["last_tpa"] >= 25 and d["last_tp_pct"] >= .45])
cell("dog cold from 3 last game (<25% on 25+ att)", [d for d in D if d["last_tp_pct"] is not None and d["last_tpa"] and d["last_tpa"] >= 25 and d["last_tp_pct"] < .25])
cell("fav hot from 3 last game (45%+)", [d for d in D if d["o_last_tp_pct"] is not None and d["o_last_tpa"] and d["o_last_tpa"] >= 25 and d["o_last_tp_pct"] >= .45])
cell("fav cold from 3 last game (<25%)", [d for d in D if d["o_last_tp_pct"] is not None and d["o_last_tpa"] and d["o_last_tpa"] >= 25 and d["o_last_tp_pct"] < .25])
cell("dog 10-game 3P% 40%+ (hot stretch)", [d for d in D if d["tp_pct"] >= .40])
cell("dog 10-game 3P% under 33% (cold stretch)", [d for d in D if d["tp_pct"] < .33])

print("\n=== STUDY 2: MARGIN VARIANCE - the dog's result spread over its last 10 games (pstdev of margins), the favorite's ===")
V = [d for d in DOGS if d["sd10"] is not None and d["o_sd10"] is not None]
bys = defaultdict(list)
for d in V:
    bys[d["season"]].append(d["sd10"])
q = {s: statistics.quantiles(v, n=4) for s, v in bys.items()}
for d in V:
    lo, mid, hi = q[d["season"]]
    d["sd_q"] = 0 if d["sd10"] < lo else (3 if d["sd10"] >= hi else (1 if d["sd10"] < mid else 2))
    d["o_sd_q"] = 0 if d["o_sd10"] < lo else (3 if d["o_sd10"] >= hi else (1 if d["o_sd10"] < mid else 2))
cell("all with 8+ games", V)
for k in range(4):
    cell(f"dog margin-variance quartile {k} (3 = wildest)", [d for d in V if d["sd_q"] == k])
for k in range(4):
    cell(f"favorite margin-variance quartile {k}", [d for d in V if d["o_sd_q"] == k])
cell("wild dog (q3) vs steady fav (q0)", [d for d in V if d["sd_q"] == 3 and d["o_sd_q"] == 0])
cell("steady dog (q0) vs wild fav (q3)", [d for d in V if d["sd_q"] == 0 and d["o_sd_q"] == 3])
cell("big dog +200+, wild (q3)", [d for d in V if d["sd_q"] == 3 and d["ml"] >= 200])
cell("big dog +200+, steady (q0)", [d for d in V if d["sd_q"] == 0 and d["ml"] >= 200])
cell("wild fav (q3) any dog", [d for d in V if d["o_sd_q"] == 3])
cell("steady fav (q0) +200+ dog", [d for d in V if d["o_sd_q"] == 0 and d["ml"] >= 200])

print("\n=== STUDY 3: THE FAVORITE'S SCHEDULE SANDWICH - look-ahead to a marquee game / letdown after one ===")
L = [d for d in DOGS if d["o_next_opp_elo"] is not None and d["o_g"] >= 10]
cell("all with a next game", L)
cell("fav's next game vs a 1600+ Elo team within 2 days", [d for d in L if d["o_next_opp_elo"] >= 1600 and d["o_next_days"] <= 2])
cell("fav's next game vs a 1600+ Elo team, next day", [d for d in L if d["o_next_opp_elo"] >= 1600 and d["o_next_days"] <= 1])
cell("fav's next game vs a 1575+ team within 2 days", [d for d in L if d["o_next_opp_elo"] >= 1575 and d["o_next_days"] <= 2])
cell("fav's next opp 100+ Elo better than tonight's dog, within 2 days", [d for d in L if d["o_next_opp_elo"] - d["elo"] >= 100 and d["o_next_days"] <= 2])
cell("fav's next opp 150+ Elo better than the dog, within 2 days", [d for d in L if d["o_next_opp_elo"] - d["elo"] >= 150 and d["o_next_days"] <= 2])
cell("  ... and the dog is a weak team (Elo under 1470)", [d for d in L if d["o_next_opp_elo"] - d["elo"] >= 150 and d["o_next_days"] <= 2 and d["elo"] < 1470])
cell("  ... and the fav is on the road tonight", [d for d in L if d["o_next_opp_elo"] - d["elo"] >= 150 and d["o_next_days"] <= 2 and d["home"]])
cell("fav's next game vs a weak team (control)", [d for d in L if d["o_next_opp_elo"] < 1450 and d["o_next_days"] <= 2])
cell("fav's LAST game vs a 1600+ team (letdown)", [d for d in L if d["o_last_opp_elo"] is not None and d["o_last_opp_elo"] >= 1600])
cell("fav's LAST game a WIN vs a 1600+ team", [d for d in L if d["o_last_opp_elo"] is not None and d["o_last_opp_elo"] >= 1600 and d["o_last_won"]])
cell("fav's last opp 1575+ AND won", [d for d in L if d["o_last_opp_elo"] is not None and d["o_last_opp_elo"] >= 1575 and d["o_last_won"]])
cell("sandwich: fav beat a 1575+ team last AND next is 1575+ within 2 days", [d for d in L if d["o_last_opp_elo"] is not None and d["o_last_opp_elo"] >= 1575 and d["o_last_won"] and d["o_next_opp_elo"] >= 1575 and d["o_next_days"] <= 2])
cell("DOG's next game vs a 1600+ team within 2 days (dog looking ahead)", [d for d in DOGS if d["next_opp_elo"] is not None and d["next_opp_elo"] >= 1600 and d["next_days"] <= 2])

print("\n=== STUDY 4: THE IMMEDIATE REMATCH - the same two teams again within 3 days (the 2-game sets) ===")
R = [d for d in DOGS if d["last_opp_same"] is not None]
cell("all dogs (control)", R)
cell("rematch within 3 days, any", [d for d in R if d["last_opp_same"] and d["last_opp_same_days"] <= 3])
cell("rematch: dog LOST game 1", [d for d in R if d["last_opp_same"] and d["last_opp_same_days"] <= 3 and not d["last_won"]])
cell("rematch: dog lost game 1 by 15+", [d for d in R if d["last_opp_same"] and d["last_opp_same_days"] <= 3 and d["last_margin"] <= -15])
cell("rematch: dog lost game 1 by 1-9", [d for d in R if d["last_opp_same"] and d["last_opp_same_days"] <= 3 and -9 <= d["last_margin"] <= -1])
cell("rematch: dog WON game 1 (still a dog)", [d for d in R if d["last_opp_same"] and d["last_opp_same_days"] <= 3 and d["last_won"]])
cell("rematch: dog won game 1 AND +150 or longer", [d for d in R if d["last_opp_same"] and d["last_opp_same_days"] <= 3 and d["last_won"] and d["ml"] >= 150])
cell("rematch, same court both games", [d for d in R if d["last_opp_same"] and d["last_opp_same_days"] <= 3 and d["next_opp_same"] is False])
cell("rematch, dog at home game 2", [d for d in R if d["last_opp_same"] and d["last_opp_same_days"] <= 3 and d["home"]])
cell("rematch, dog on the road game 2", [d for d in R if d["last_opp_same"] and d["last_opp_same_days"] <= 3 and not d["home"]])
cell("game 1 of a 2-game set (plays the same team next within 3 days)", [d for d in DOGS if d["next_opp_same"] and d["next_days"] is not None and d["next_days"] <= 3])
cell("game 1 of a set, dog at home", [d for d in DOGS if d["next_opp_same"] and d["next_days"] is not None and d["next_days"] <= 3 and d["home"]])
cell("2nd+ meeting this season, lost ALL previous meetings (2+)", [d for d in DOGS if d["met"] >= 2 and d["last_meet_margin"] is not None and d["last_meet_margin"] < 0])

print("\n=== STUDY 5: THE FAVORITE'S LEGS - heavy minutes last game, dense schedule, the dog fresh ===")
M = [d for d in DOGS if d["o_last_top3_min"] is not None and d["o_rest"] is not None and d["o_g"] >= 5]
cell("all with the fav's last box", M)
cell("fav's top 3 averaged 38+ min last game", [d for d in M if d["o_last_top3_min"] >= 38])
cell("fav's top 3 averaged 38+ min last game AND b2b", [d for d in M if d["o_last_top3_min"] >= 38 and d["o_rest"] <= 1])
cell("fav's top 3 averaged 38+ AND b2b AND dog rested 2+", [d for d in M if d["o_last_top3_min"] >= 38 and d["o_rest"] <= 1 and (d["rest"] or 0) >= 2])
cell("fav's top man 42+ min last game", [d for d in M if d["o_last_max_min"] >= 42])
cell("fav's top man 42+ min AND b2b", [d for d in M if d["o_last_max_min"] >= 42 and d["o_rest"] <= 1])
cell("fav's top 3 under 32 min last game (light night) AND b2b", [d for d in M if d["o_last_top3_min"] < 32 and d["o_rest"] <= 1])
cell("fav on a b2b (control)", [d for d in M if d["o_rest"] <= 1])
cell("fav 4 games in 6 nights (control, dead before)", [d for d in M if d["o_in6"] >= 4])
cell("fav 4-in-6 AND heavy minutes last game (38+)", [d for d in M if d["o_in6"] >= 4 and d["o_last_top3_min"] >= 38])
cell("fav 3-in-4 AND heavy minutes last game (38+)", [d for d in M if d["o_in4"] >= 3 and d["o_last_top3_min"] >= 38])
cell("fav played OT last game (built, control)", [d for d in M if d["o_last_top3_min"] >= 40])
cell("dog's own top 3 38+ last game AND dog on b2b (fade?)", [d for d in M if d["last_top3_min"] is not None and d["last_top3_min"] >= 38 and (d["rest"] or 9) <= 1])

print("\n=== EXTRA: SLATE SIZE (how many NBA games that night) ===")
for lo, hi in ((1, 3), (4, 6), (7, 9), (10, 11), (12, 15)):
    cell(f"slate {lo}-{hi} games", [d for d in DOGS if lo <= d["slate"] <= hi])
cell("slate 11+ AND +200..+350", [d for d in DOGS if d["slate"] >= 11 and d["ml"] >= 200])
cell("slate 1-4 AND +200..+350", [d for d in DOGS if d["slate"] <= 4 and d["ml"] >= 200])
