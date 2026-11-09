"""S1 - THE BUILT COLLEGE HOOPS EARLY ROAD DOG FADE, RE-CHECKED (sports.ncaab_early_road_dog, -2 on the dog score since
11/3; its tracker tag 'college hoops road dog, games 1-3 (fade)' is +23.4% for the faded dogs on 43 live).
The same cell as the 11/3 build (results/studies/cbb_1103_a/s7_road_dog_early.py): a moneyline dog +100..+350 on a TRUE
road floor (not neutral) in its own games 1-3 (regular season, every final on file = sports.season_games), read:
 (a) every season apart at the CLOSE and ESPN's OPEN, 2018-25 (2025 = 2025-26, the newest completed season) + 2026-27
     live from the game file (every such dog, not only the ones the board saw);
 (b) the 2026-27 live rows by price band / game number;
 (c) the tracker's own graded rows (sports_leads, in band) - what the engine actually saw;
 (d) the base it is judged against: the road dog in games 4-6 / 7+ each season.
Seasons are named by the year they start. Close = the game file's ml_home / ml_away."""
import os
from collections import defaultdict
import lib
import sports_leads as sl
import sports_data as sd

fin = lib.finals("ncaab")
allf = [g for g in lib.all_finals("ncaab") if g["stype"] == "2"]
gn = {}
cnt = defaultdict(int)
for g in allf:
    for side in ("home", "away"):
        t = g[side]
        cnt[(g["season"], t)] += 1
        gn[(g["id"], side)] = cnt[(g["season"], t)]          # 1 = the opener (this game included)

cells = lib.Cells()
live = []
for g in fin:
    if g["neutral"] or g["stype"] != "2":
        continue
    o = g["mla"]
    if not lib.dog_band(o):
        continue
    n = gn.get((g["id"], "away"))
    if n is None:
        continue
    won = g["as"] > g["hs"]
    s = g["season"]
    p = lib.profit(won, lib.dec(o))
    lab = "games 1-3" if n <= 3 else ("games 4-6" if n <= 6 else "games 7+")
    cells.add(f"ROAD dog close | {lab}", s, p)
    if g["oa"] and lib.dog_band(g["oa"]):
        cells.add(f"ROAD dog OPEN  | {lab}", s, lib.profit(won, lib.dec(g["oa"])))
    a = lib.ats(g, "away")
    cells.add(f"ROAD dog ATS   | {lab}", s, a)
    if n <= 3:
        band = "+100..+150" if o <= 150 else ("+151..+250" if o <= 250 else "+251..+350")
        cells.add(f"ROAD dog close | games 1-3 {band}", s, p)
        if s == 2026:
            live.append({"day": g["start"][:10], "away": g["an"], "home": g["hn"], "odds": o, "open": g["oa"],
                         "won": won, "n": n, "p": round(p, 3), "ats": a})

cells.dump("s1", "S1 - college hoops ROAD dog +100..+350 by the dog's game number, every season apart "
           "(TRAIN 2018-22, held 2023 / 2024 / 2025, 2026 = live)", (2018, 2022), (2023, 2024, 2025, 2026))

out = [""]
out.append(f"2026-27 LIVE, every early road dog (games 1-3) on file: {len(live)} sides, "
           f"{sum(x['won'] for x in live)}-{sum(not x['won'] for x in live)}, "
           f"{sum(x['p'] for x in live):+.2f}u, roi {sum(x['p'] for x in live) / max(1, len(live)):+.1%}")
for lab, f in (("+100..+150", lambda x: x["odds"] <= 150), ("+151..+250", lambda x: 150 < x["odds"] <= 250),
               ("+251..+350", lambda x: x["odds"] > 250), ("game 1", lambda x: x["n"] == 1),
               ("game 2", lambda x: x["n"] == 2), ("game 3", lambda x: x["n"] == 3)):
    xs = [x for x in live if f(x)]
    if xs:
        out.append(f"   {lab:11s} {sum(x['won'] for x in xs)}-{sum(not x['won'] for x in xs)} "
                   f"{sum(x['p'] for x in xs):+.2f}u roi {sum(x['p'] for x in xs) / len(xs):+.1%} on {len(xs)}")
ats = [x["ats"] for x in live if x["ats"] is not None]
out.append(f"   ATS on the same games: {sum(1 for v in ats if v > 0)}-{sum(1 for v in ats if v < 0)} "
           f"roi {sum(ats) / max(1, len(ats)):+.1%}")
exp = sum(1 / lib.dec(x["odds"]) for x in live)
out.append(f"   won {sum(x['won'] for x in live)} vs {exp:.1f} the raw close price expects")

games = sd.load_games("ncaab")
TAG = "college hoops road dog, games 1-3 (fade)"
tr = [r for r in sl.load() if TAG in r.get("tags", []) and sl.counts(TAG, r.get("odds"))]
w = l = 0
pl = 0.0
byday = defaultdict(lambda: [0, 0, 0.0])
for r in tr:
    g = games.get(r["game_id"])
    if not g or g.get("status") != "final":
        continue
    hs, as_ = float(g["home_score"]), float(g["away_score"])
    won = (as_ > hs) if r["side"] == "away" else (hs > as_)
    pp = lib.profit(won, lib.dec(r["odds"]))
    w += won; l += not won; pl += pp
    b = byday[r["day"]]; b[0] += won; b[1] += not won; b[2] += pp
out.append(f"TRACKER rows in band, graded at the logged price: {w}-{l} {pl:+.2f}u roi {pl / max(1, w + l):+.1%} on {w + l}")
out.append("   by day: " + ", ".join(f"{d} {v[0]}-{v[1]} {v[2]:+.1f}u" for d, v in sorted(byday.items())))
out.append("   the live rows (day, road dog, odds, open, game no., result):")
for x in sorted(live, key=lambda x: x["day"]):
    out.append(f"     {x['day']} {x['away']:22s} @ {x['home']:22s} {x['odds']:+5.0f} open {x['open'] or 0:+5.0f} "
               f"g{x['n']} {'W' if x['won'] else 'L'}")
txt = "\n".join(out)
print(txt)
open(os.path.join(lib.OUT, "s1_out.txt"), "a").write(txt + "\n")
