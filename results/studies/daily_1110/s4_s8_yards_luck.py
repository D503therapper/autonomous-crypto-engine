"""S4 (NFL) / S8 (college football) - THE SCOREBOARD vs THE YARDS (never studied: no yards study on file; the 11/4
interception luck read turnovers, the 10/13 Pythagorean read the NBA / NHL; every 'yards' line in SPORTS_FINDINGS
is a player prop or a card line).
A team's season-to-date POINT margin a game against what its YARD margin a game says it should be (passing + rushing
yards from its box scores, both sides; the points-per-yard slope fit on the TRAIN seasons only). LUCKY = scoring
margin well over the yards (red-zone / turnover / return luck the public reads as 'they win'), UNLUCKY = under.
3+ boxed games before tonight (college: both teams FBS-boxed, a non-boxed game simply doesn't count).
Cells per league: the side as a favorite -101..-250 / a dog +100..+350 at the close, ATS at the close, and the
first FAIR number from the paid odds history (football: ready_at / fair - no look-ahead) as the second price.
TRAIN 2021-22 (box scores start 2021), HELD 2023 / 2024 / 2025 apart, 2026 live."""
import sys
from collections import defaultdict

import lib

LG = sys.argv[1] if len(sys.argv) > 1 else "nfl"
TAG = "s4" if LG == "nfl" else "s8"
box = lib.box_rows(LG)
fin = lib.finals(LG)
allf = [g for g in lib.all_finals(LG) if g["stype"] == "2"]
hist = {x["id"]: x for x in lib.load_football(LG)}


def yards(gid, team):
    b = (box.get(gid) or {}).get(team)
    if not b:
        return None
    y = 0.0
    seen = False
    for r in b:
        if r["group"] == "passing":
            v = lib.num(r["st"].get("passingYards"))
            if v is not None:
                y += v
                seen = True
        elif r["group"] == "rushing":
            v = lib.num(r["st"].get("rushingYards"))
            if v is not None:
                y += v
                seen = True
    return y if seen else None


run = defaultdict(lambda: [0, 0.0, 0.0])          # (season, team) -> [boxed games, point margin sum, yard margin sum]
pre = {}
pts = []                                          # (season, point margin, yard margin) per team-game for the slope
for g in allf:
    for side in ("home", "away"):
        pre[(g["id"], side)] = tuple(run[(g["season"], g[side])])
    yh, ya = yards(g["id"], g["home"]), yards(g["id"], g["away"])
    if yh is None or ya is None:
        continue
    m = g["hs"] - g["as"]
    for side, sg in (("home", 1), ("away", -1)):
        r = run[(g["season"], g[side])]
        r[0] += 1
        r[1] += sg * m
        r[2] += sg * (yh - ya)
    pts.append((g["season"], m, yh - ya))

tr = [(m, y) for s, m, y in pts if s <= 2022]
b = sum(m * y for m, y in tr) / sum(y * y for m, y in tr)
print(f"{LG}: {len(pts)} boxed games; points per yard of margin (train fit) {b:.4f}")
CUT = (4.0, 7.0) if LG == "nfl" else (6.0, 10.0)
cells = lib.Cells()
dist = []
for g in fin:
    if g["stype"] != "2" or g["season"] < 2021:
        continue
    luck = {}
    for side in ("home", "away"):
        n, pm, ym = pre.get((g["id"], side), (0, 0, 0))
        if n < 3:
            break
        luck[side] = pm / n - b * ym / n
    else:
        for side, team, opp, o, won, home in lib.sides(g):
            L = luck[side]
            dist.append(L)
            Lo = luck["away" if home else "home"]
            labs = []
            if L >= CUT[1]:
                labs.append(f"LUCKY +{CUT[1]:.0f}+ pts a game over the yards")
            if L >= CUT[0]:
                labs.append(f"LUCKY +{CUT[0]:.0f}+")
            if L <= -CUT[0]:
                labs.append(f"UNLUCKY -{CUT[0]:.0f} or worse")
            if L <= -CUT[1]:
                labs.append(f"UNLUCKY -{CUT[1]:.0f} or worse")
            if abs(L) < 2:
                labs.append("control: within 2")
            if L - Lo >= 2 * CUT[0]:
                labs.append(f"luck gap vs the opponent +{2*CUT[0]:.0f}+")
            s = g["season"]
            pl = lib.profit(won, lib.dec(o))
            a = lib.ats(g, side)
            ep = lib.early_price(hist, g["id"], side)
            for lab in labs:
                if -250 <= o <= -101:
                    cells.add(f"{lab} | FAV ML", s, pl)
                    if ep and -250 <= ep[0] <= -101:
                        cells.add(f"{lab} | FAV ML first fair", s, lib.profit(won, ep[1]))
                if lib.dog_band(o):
                    cells.add(f"{lab} | DOG ML", s, pl)
                    if ep and lib.dog_band(ep[0]):
                        cells.add(f"{lab} | DOG ML first fair", s, lib.profit(won, ep[1]))
                cells.add(f"{lab} | ATS", s, a)
dist.sort()
print("luck quantiles 10/25/50/75/90:", [round(dist[int(len(dist) * q)], 1) for q in (.1, .25, .5, .75, .9)])
cells.dump(TAG, f"{TAG.upper()} {LG} - point margin over the yard margin (slope {b:.4f}), 3+ boxed games; close / ATS / "
           f"first fair; TRAIN 2021-22", (2021, 2022), (2023, 2024, 2025, 2026))
