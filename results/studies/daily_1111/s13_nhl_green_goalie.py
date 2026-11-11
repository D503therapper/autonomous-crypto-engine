"""S13 (NHL) - THE GREEN GOALIE (never studied: the goalie studies read form / workload / roles / the #1 sitting / the
backup on a rested night - never how many NHL starts the man in net has; 'rookie goalie' / 'career starts' appear
nowhere in SPORTS_FINDINGS).
GREEN = tonight's starter has fewer than N career starts in our goalie file (data/sports/players/nhl.csv - the starter
per team-game 2016-26); seasons 2018-26 only, so two full seasons seed every veteran's count (a man first seen in
2018+ with under N starts is really new). Tonight's ACTUAL starter is a game-day fact (the engine confirms the goalie
in the morning - Daily Faceoff - and waits on it), and as the no-look-ahead check the team's LAST game's starter was
green too (a green man already in the job). Both sides: the green goalie's team as a dog / favorite, and the side
FACING a green goalie. Close + the paid game-day morning look (2021-23).
TRAIN 2018-21, HELD 2022 / 2023 / 2024 / 2025 apart, 2026 live."""
import csv
from collections import defaultdict

import lib

fin = [g for g in lib.finals("nhl") if g["stype"] == "2"]
mo = lib.nhl_morning()
start = {}
with open(lib.os.path.join(lib.sd.DATA, "players", "nhl.csv")) as f:
    for r in csv.DictReader(f):
        if r["role"] != "G":
            continue
        sa = lib.num(r["sa"]) or 0
        k = (r["gid"], r["team"])
        if k not in start or sa > start[k][1]:
            start[k] = (r["player"], sa, r["start"])
seq = sorted(((v[2], gid, team, v[0]) for (gid, team), v in start.items()))
count = defaultdict(int)
before = {}                    # (gid, team) -> starts the man had before this game
for st, gid, team, p in seq:
    before[(gid, team)] = count[p]
    count[p] += 1
allf = [g for g in lib.all_finals("nhl") if g["stype"] == "2"]
tl = lib.team_log(allf)


def green_n(gid, team):
    k = (gid, team)
    return before.get(k) if k in start else None


cells = lib.Cells()
for g in fin:
    if g["season"] < 2018:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        mine, theirs = green_n(g["id"], team), green_n(g["id"], opp)
        if mine is None or theirs is None:
            continue
        prev = lib.before(tl, team, g["start"], 1)
        last_green = None
        if prev:
            lp = green_n(prev[-1]["id"], team)
            last_green = lp is not None and lp < 15
        labs = []
        if mine < 5:
            labs.append("MY goalie under 5 career starts")
        if mine < 15:
            labs.append("MY goalie under 15")
            if last_green:
                labs.append("MY goalie under 15, and last game's starter green too (no look-ahead)")
        if 15 <= mine < 60:
            labs.append("MY goalie 15-59")
        if mine >= 150:
            labs.append("control: MY goalie 150+")
        if theirs < 15:
            labs.append("FACING a goalie under 15")
        if theirs < 5:
            labs.append("FACING a goalie under 5")
        if mine < 15 and theirs >= 150:
            labs.append("green (under 15) vs a veteran (150+)")
        s = g["season"]
        pl = lib.profit(won, lib.dec(o))
        m = lib.morning_side(mo, g["id"], side) if mo else None
        for lab in labs:
            if -250 <= o <= -101:
                cells.add(f"{lab} | FAV ML", s, pl)
                if m and -250 <= m[0] <= -101:
                    cells.add(f"{lab} | FAV ML paid morning", s, lib.profit(won, m[1]))
            if lib.dog_band(o):
                cells.add(f"{lab} | DOG ML", s, pl)
                if m and lib.dog_band(m[0]):
                    cells.add(f"{lab} | DOG ML paid morning", s, lib.profit(won, m[1]))
cells.dump("s13", "S13 NHL - the green goalie (career starts in our file, seasons 2018+); close / paid morning; TRAIN 2018-21",
           (2018, 2021), (2022, 2023, 2024, 2025, 2026))
