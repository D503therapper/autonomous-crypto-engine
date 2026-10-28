"""10/28 BIG-SLATE NBA UPSET STUDIES - 5 studies on WHICH NBA dogs (+100..+350 at the close, flat 1u) win on 12+ game
nights. Train = 2018-19..2023-24, HOLDOUT = 2024-25 and 2025-26 (graded apart), NOW = 2026-27. Every cell is written
down before it runs; survival = up in train AND both holdout seasons (the five-checks rule)."""
import os
import pickle
import statistics
from collections import defaultdict

HERE = os.path.dirname(__file__)
sides = pickle.load(open(os.path.join(HERE, "sides.pkl"), "rb"))
DOGS = [d for d in sides if 100 <= d["ml"] <= 350]
BIG = [d for d in DOGS if d["slate"] >= 12]
SMALLS = [d for d in DOGS if d["slate"] < 12]
TRAIN = {2018, 2019, 2020, 2021, 2022, 2023}
H1, H2 = {2024}, {2025}


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


CELLS = []


def cell(name, rows, note=""):
    out = []
    res = {}
    for lab, S in (("train", TRAIN), ("24-25", H1), ("25-26", H2), ("now", {2026})):
        r = [d for d in rows if d["season"] in S]
        n, w, ro, wp, imp, z = roi(r)
        res[lab] = (n, ro, z)
        if lab == "train":
            u, t = seasons_up(r)
            out.append(f"train {w}-{n-w} {ro:+.1f}% ({wp:.1f} vs {imp:.1f}, z {z:+.1f}, {u}/{t} up)")
        else:
            out.append(f"{lab} {w}-{n-w} {ro:+.1f}% (z {z:+.1f})")
    surv = res["train"][1] > 0 and res["24-25"][1] > 0 and res["25-26"][1] > 0 and res["train"][0] >= 30 and res["24-25"][0] >= 10 and res["25-26"][0] >= 10
    fade = res["train"][1] < 0 and res["24-25"][1] < 0 and res["25-26"][1] < 0 and res["train"][0] >= 30 and res["24-25"][0] >= 10 and res["25-26"][0] >= 10
    CELLS.append((name, surv, fade))
    print(f"  {name:66s} | " + " | ".join(out) + ("   <== UP all three" if surv else "   <== RED all three" if fade else ""))


def band(d):
    return "+100-150" if d["ml"] < 150 else ("+150-250" if d["ml"] < 250 else "+250-350")


def q4(rows, key, okey=None):
    """season quartiles of `key` over rows (0 = lowest .. 3 = highest), written on each row as key+'_q' (and the
    opponent's as o_key_q against the same cut)."""
    bys = defaultdict(list)
    for d in rows:
        if d.get(key) is not None:
            bys[d["season"]].append(d[key])
    q = {s: statistics.quantiles(v, n=4) for s, v in bys.items() if len(v) >= 8}
    for d in rows:
        for k in (key, "o_" + key):
            v = d.get(k)
            if v is None or d["season"] not in q:
                d[k + "_q"] = None
                continue
            lo, mid, hi = q[d["season"]]
            d[k + "_q"] = 0 if v < lo else (3 if v >= hi else (1 if v < mid else 2))


print(f"=== BIG SLATES (12+ games, PT night): {len(BIG)} dogs of {len(DOGS)} (+100..+350) ===")
cell("ALL big-slate dogs (the built +2 - control)", BIG)
cell("ALL small-slate dogs (under 12 games - control)", SMALLS)

print("\n=== STUDY 1: INSIDE THE BIG SLATE - which dog traits separate the winners (each trait also on small slates as the control) ===")
pairs = [
    ("home dog", lambda d: d["home"]),
    ("road dog", lambda d: not d["home"]),
    ("+100..+150", lambda d: band(d) == "+100-150"),
    ("+150..+250", lambda d: band(d) == "+150-250"),
    ("+250..+350", lambda d: band(d) == "+250-350"),
    ("dog rested 2+ days, favorite on a back-to-back", lambda d: (d["rest"] or 0) >= 2 and d["o_rest"] is not None and d["o_rest"] <= 1),
    ("favorite on a back-to-back (any dog rest)", lambda d: d["o_rest"] is not None and d["o_rest"] <= 1),
    ("dog on a back-to-back", lambda d: d["rest"] is not None and d["rest"] <= 1),
    ("both rested 2+", lambda d: (d["rest"] or 0) >= 2 and (d["o_rest"] or 0) >= 2),
    ("dog's net rating (last 10, per 100) BETTER than the favorite's", lambda d: d["net100"] is not None and d["o_net100"] is not None and d["net100"] > d["o_net100"]),
    ("dog's net rating 5+ worse than the favorite's", lambda d: d["net100"] is not None and d["o_net100"] is not None and d["o_net100"] - d["net100"] >= 5),
    ("dog's net rating 10+ worse", lambda d: d["net100"] is not None and d["o_net100"] is not None and d["o_net100"] - d["net100"] >= 10),
    ("dog won 3+ of its last 5", lambda d: d["w5"] is not None and d["w5"] >= 3),
    ("dog won 1 or 0 of its last 5", lambda d: d["w5"] is not None and d["w5"] <= 1),
    ("favorite won 4+ of its last 5", lambda d: d["o_w5"] is not None and d["o_w5"] >= 4),
    ("favorite won 2 or fewer of its last 5", lambda d: d["o_w5"] is not None and d["o_w5"] <= 2),
    ("dog off a loss", lambda d: d["last_won"] is False),
    ("dog off a win", lambda d: d["last_won"] is True),
    ("favorite off a loss", lambda d: d["o_last_won"] is False),
    ("dog .500+ this season (10+ games)", lambda d: d["g"] >= 10 and d["wp"] >= .5),
    ("dog under .350 this season (10+ games)", lambda d: d["g"] >= 10 and d["wp"] < .35),
    ("Elo gap (fav - dog, home edge in) under 60", lambda d: (d["o_elo"] + (70 if d["o_home"] else -70)) - d["elo"] < 60),
    ("Elo gap 60-120", lambda d: 60 <= (d["o_elo"] + (70 if d["o_home"] else -70)) - d["elo"] < 120),
    ("Elo gap 120+", lambda d: (d["o_elo"] + (70 if d["o_home"] else -70)) - d["elo"] >= 120),
    ("favorite on its 3rd+ straight road game", lambda d: d["o_road_run"] >= 2),
    ("favorite 4 games in 6 nights", lambda d: d["o_in6"] >= 4),
    ("dog 4 games in 6 nights", lambda d: d["in6"] >= 4),
    ("favorite's next game soft (built -2; within 2 days vs under .400, 10+ g)", lambda d: d["o_next_days"] is not None and d["o_next_days"] <= 2 and d["o_next_opp_wp"] is not None and d["o_next_opp_g"] >= 10 and d["o_next_opp_wp"] < .4),
    ("favorite's next game NOT soft (the rest)", lambda d: not (d["o_next_days"] is not None and d["o_next_days"] <= 2 and d["o_next_opp_wp"] is not None and d["o_next_opp_g"] >= 10 and d["o_next_opp_wp"] < .4)),
]
for name, f in pairs:
    cell("BIG: " + name, [d for d in BIG if f(d)])
    cell("  small-slate control: " + name, [d for d in SMALLS if f(d)])
print("  -- the +150..+250 band inside big slates, by home / road and rest --")
MID = [d for d in BIG if band(d) == "+150-250"]
cell("BIG +150..+250 home", [d for d in MID if d["home"]])
cell("BIG +150..+250 road", [d for d in MID if not d["home"]])
cell("BIG +150..+250, favorite on a b2b", [d for d in MID if d["o_rest"] is not None and d["o_rest"] <= 1])
cell("BIG +150..+250, favorite rested 2+", [d for d in MID if (d["o_rest"] or 0) >= 2])
cell("BIG +150..+250, dog net rating within 5 of the fav's", [d for d in MID if d["net100"] is not None and d["o_net100"] is not None and d["o_net100"] - d["net100"] < 5])

print("\n=== STUDY 2: MARKET ATTENTION - small-market dogs, late tips, the night's order, the weekday ===")
for lab, rows in (("BIG", BIG), ("small-slate control", SMALLS)):
    cell(f"{lab}: small-market dog", [d for d in rows if d["market"] == "small"])
    cell(f"{lab}: big-market dog", [d for d in rows if d["market"] == "big"])
    cell(f"{lab}: small-market dog vs a big-market favorite", [d for d in rows if d["market"] == "small" and d["o_market"] == "big"])
    cell(f"{lab}: big-market dog vs a small-market favorite", [d for d in rows if d["market"] == "big" and d["o_market"] == "small"])
    cell(f"{lab}: late tip (10 PM ET or later = 02:00+ UTC)", [d for d in rows if 2 <= d["tip_utc"] < 9])
    cell(f"{lab}: the night's LAST tip", [d for d in rows if d["last_tip"]])
    cell(f"{lab}: early tip (7 PM ET and earlier = 23:xx / 00:xx UTC... before 00:30)", [d for d in rows if d["tip_utc"] >= 22 or d["tip_utc"] < 0.5])
    cell(f"{lab}: the night's FIRST tip", [d for d in rows if d["first_tip"]])
    cell(f"{lab}: mid-evening (00:30-02:00 UTC)", [d for d in rows if 0.5 <= d["tip_utc"] < 2])
    cell(f"{lab}: tipped 8+ games into the night", [d for d in rows if d["order"] >= 8])
for wd, nm in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
    cell(f"BIG: {nm}", [d for d in BIG if d["wday"] == wd])
cell("BIG: weekend (Fri / Sat / Sun)", [d for d in BIG if d["wday"] >= 4])
cell("BIG: midweek (Mon-Thu)", [d for d in BIG if d["wday"] < 4])
cell("BIG: late tip +150..+250", [d for d in BIG if 2 <= d["tip_utc"] < 9 and band(d) == "+150-250"])
cell("BIG: small-market dog +150..+250", [d for d in BIG if d["market"] == "small" and band(d) == "+150-250"])

print("\n=== STUDY 3: LINE MOVEMENT open -> close (both prices known at the close; 2023-24 on, the only seasons with an open) ===")
OPEN = [d for d in DOGS if d["ml_open"] is not None and d["nv_open"] is not None]
print(f"  dogs with an opening price: {len(OPEN)} (by season {sorted(((s, sum(1 for d in OPEN if d['season']==s)) for s in {d['season'] for d in OPEN}))})")
for d in OPEN:
    d["mv"] = d["nv"] - d["nv_open"]           # + = the close likes the dog more than the open did (money came to the dog)
for lab, rows in (("BIG", [d for d in OPEN if d["slate"] >= 12]), ("small-slate control", [d for d in OPEN if d["slate"] < 12]), ("ALL", OPEN)):
    cell(f"{lab}: any dog with an open (control)", rows)
    cell(f"{lab}: money came TO the dog 2+ pts (close prob - open prob >= .02)", [d for d in rows if d["mv"] >= .02])
    cell(f"{lab}: money came to the dog 1-2 pts", [d for d in rows if .01 <= d["mv"] < .02])
    cell(f"{lab}: the line sat still (within 1 pt)", [d for d in rows if -.01 < d["mv"] < .01])
    cell(f"{lab}: money ran AWAY 1-2 pts", [d for d in rows if -.02 < d["mv"] <= -.01])
    cell(f"{lab}: money ran AWAY 2+ pts (the built -4 drift fade)", [d for d in rows if d["mv"] <= -.02])
    cell(f"{lab}: opened a FAVORITE, closed a dog (flipped)", [d for d in rows if d["ml_open"] < 0])
    cell(f"{lab}: opened +350 or longer, closed +100..+350 (money came in hard)", [d for d in rows if d["ml_open"] > 350])

print("\n=== STUDY 4: THE FAVORITE'S STAR (its top man by minutes a game this season, 5+ games) sat out its LAST game ===")
ST = [d for d in DOGS if d["o_star_out_last"] is not None and d["o_g"] >= 8]
for lab, rows in (("BIG", [d for d in ST if d["slate"] >= 12]), ("small-slate control", [d for d in ST if d["slate"] < 12]), ("ALL", ST)):
    cell(f"{lab}: fav's star PLAYED last game (control)", [d for d in rows if not d["o_star_out_last"]])
    cell(f"{lab}: fav's star sat out last game", [d for d in rows if d["o_star_out_last"]])
    cell(f"{lab}: fav's star sat out the last 2+", [d for d in rows if d["o_star_out_2"]])
    cell(f"{lab}: fav's star sat out last game, dog +150 or longer", [d for d in rows if d["o_star_out_last"] and d["ml"] >= 150])
    cell(f"{lab}: fav's star BACK last game after missing one", [d for d in rows if d["o_star_back"]])
    cell(f"{lab}: DOG's star sat out last game", [d for d in rows if d["star_out_last"]])
    cell(f"{lab}: DOG's star back last game after missing one", [d for d in rows if d["star_back"]])
    cell(f"{lab}: fav's star out last game AND fav on a b2b", [d for d in rows if d["o_star_out_last"] and d["o_rest"] is not None and d["o_rest"] <= 1])

print("\n=== STUDY 5: THE MATCHUP from the box scores (last 10 games): pace, offensive rebounding, turnovers ===")
MX = [d for d in DOGS if d["pace"] is not None and d["o_pace"] is not None]
q4(MX, "pace")
q4(MX, "oreb_pct")
q4(MX, "tov_rate")
for lab, rows in (("BIG", [d for d in MX if d["slate"] >= 12]), ("small-slate control", [d for d in MX if d["slate"] < 12]), ("ALL", MX)):
    cell(f"{lab}: with box rates (control)", rows)
    cell(f"{lab}: SLOW dog (pace q0) vs FAST favorite (q3)", [d for d in rows if d["pace_q"] == 0 and d["o_pace_q"] == 3])
    cell(f"{lab}: FAST dog (q3) vs SLOW favorite (q0)", [d for d in rows if d["pace_q"] == 3 and d["o_pace_q"] == 0])
    cell(f"{lab}: slow dog (q0), any favorite", [d for d in rows if d["pace_q"] == 0])
    cell(f"{lab}: fast dog (q3), any favorite", [d for d in rows if d["pace_q"] == 3])
    cell(f"{lab}: dog out-rebounds (oreb% q3) a weak-glass favorite (q0/1)", [d for d in rows if d["oreb_pct_q"] == 3 and d["o_oreb_pct_q"] is not None and d["o_oreb_pct_q"] <= 1])
    cell(f"{lab}: dog oreb% q3", [d for d in rows if d["oreb_pct_q"] == 3])
    cell(f"{lab}: dog oreb% q0", [d for d in rows if d["oreb_pct_q"] == 0])
    cell(f"{lab}: careful dog (turnover rate q0)", [d for d in rows if d["tov_rate_q"] == 0])
    cell(f"{lab}: sloppy dog (turnover rate q3)", [d for d in rows if d["tov_rate_q"] == 3])
    cell(f"{lab}: sloppy favorite (q3)", [d for d in rows if d["o_tov_rate_q"] == 3])
    cell(f"{lab}: careful dog (q0) vs sloppy favorite (q3)", [d for d in rows if d["tov_rate_q"] == 0 and d["o_tov_rate_q"] == 3])
    cell(f"{lab}: dog's pace 4+ possessions SLOWER than the fav's", [d for d in rows if d["o_pace"] - d["pace"] >= 4])
    cell(f"{lab}: dog's pace 4+ possessions FASTER than the fav's", [d for d in rows if d["pace"] - d["o_pace"] >= 4])

print("\n=== THE TALLY (multiple testing): cells run, up in train AND both holdout seasons, red in all three ===")
print(f"  cells {len(CELLS)}; UP all three: {sum(1 for c in CELLS if c[1])}; RED all three: {sum(1 for c in CELLS if c[2])}")
print("  (chance: a cell with no edge is up in train ~50% of the time and in each holdout season ~50% - ~1 in 8 cells "
      "come up 'up all three' by luck, the same for red; survival here means the SIZE and the CONTROL matter, not the sign alone)")
for name, s, f in CELLS:
    if s or f:
        print("   ", "UP " if s else "RED", name)
