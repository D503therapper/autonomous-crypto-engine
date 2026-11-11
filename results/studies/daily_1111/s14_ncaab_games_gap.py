"""S14 (college hoops) - THE GAMES-PLAYED GAP IN NOVEMBER (never studied: the early-season cells read a team's OWN game
number (games 1-3, the first D1 game after non-D1 openers, the road debut) - never the GAP between the two teams; a team
in its 4th game, with a rotation and its legs, against a team in its 1st or 2nd).
GAP = this team's games played this season before tonight (every final on file, D1 or not) minus the opponent's.
November only (regular season, the first ~4 weeks). Cells: the side with 2+ / 3+ MORE games, the side with 2+ FEWER,
the opener (0 games) vs a team with 2+, and the control (gap 0); as a favorite -101..-250 / dog +100..+350 at the close,
ATS at the close, ESPN's open (2023-26) as the second price. TRAIN 2016-21, HELD 2022 / 2023 / 2024 / 2025 apart,
2026 live (this week's games)."""
from collections import defaultdict

import lib

fin = [g for g in lib.finals("ncaab") if g["stype"] == "2"]
allf = sorted(lib.all_finals("ncaab"), key=lambda x: x["start"])
seen = defaultdict(int)
pre = {}
for g in allf:
    for side in ("home", "away"):
        pre[(g["id"], side)] = seen[(g["season"], g[side])]
    for side in ("home", "away"):
        seen[(g["season"], g[side])] += 1

cells = lib.Cells()
for g in fin:
    if g["start"][5:7] != "11":
        continue
    nh, na = pre.get((g["id"], "home")), pre.get((g["id"], "away"))
    if nh is None or na is None:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        me, op = (nh, na) if home else (na, nh)
        gap = me - op
        labs = []
        if gap >= 2:
            labs.append("MORE games: 2+")
        if gap >= 3:
            labs.append("MORE games: 3+")
        if gap <= -2:
            labs.append("FEWER games: 2+")
        if me == 0 and op >= 2:
            labs.append("OPENER vs a team with 2+ played")
        if gap == 0:
            labs.append("control: same games played")
        if gap >= 2:
            labs.append(f"MORE games 2+, {'home' if home and not g['neutral'] else 'neutral' if g['neutral'] else 'road'}")
        s = g["season"]
        pl = lib.profit(won, lib.dec(o))
        a = lib.ats(g, side)
        oo = g["oh"] if home else g["oa"]
        for lab in labs:
            if -250 <= o <= -101:
                cells.add(f"{lab} | FAV ML", s, pl)
                if oo and -250 <= oo <= -101:
                    cells.add(f"{lab} | FAV ML ESPN open", s, lib.profit(won, lib.dec(oo)))
            if lib.dog_band(o):
                cells.add(f"{lab} | DOG ML", s, pl)
                if oo and lib.dog_band(oo):
                    cells.add(f"{lab} | DOG ML ESPN open", s, lib.profit(won, lib.dec(oo)))
            cells.add(f"{lab} | ATS", s, a)
cells.dump("s14", "S14 college hoops - the games-played gap in November; close / ATS / ESPN open; TRAIN 2016-21",
           (2016, 2021), (2022, 2023, 2024, 2025, 2026))
