"""S4b / S8b - THE LUCKY FOOTBALL DOG, ROBUSTNESS (S4 / S8's moneyline cell: a dog +100..+350 whose point margin a
game runs over what its yard margin says, 3+ boxed games). Cuts: the dose, the price band, home / road, with and
without interception luck (the built 11/4 college weight reads INT margin - is this the same thing?), the first fair
number; and the teams flagged right now (this week's games). Same slope as S4 / S8 (the train fit)."""
import sys
from collections import defaultdict

import lib

LG = sys.argv[1] if len(sys.argv) > 1 else "ncaaf"
TAG = "s4b" if LG == "nfl" else "s8b"
box = lib.box_rows(LG)
fin = lib.finals(LG)
allf = [g for g in lib.all_finals(LG) if g["stype"] == "2"]
hist = {x["id"]: x for x in lib.load_football(LG)}


def team_line(gid, team):
    b = (box.get(gid) or {}).get(team)
    if not b:
        return None
    y = 0.0
    seen = False
    made = thrown = 0.0
    for r in b:
        st = r["st"]
        if r["group"] == "passing":
            v = lib.num(st.get("passingYards"))
            if v is not None:
                y += v
                seen = True
            thrown += lib.num(st.get("interceptions")) or 0
        elif r["group"] == "rushing":
            v = lib.num(st.get("rushingYards"))
            if v is not None:
                y += v
                seen = True
        elif r["group"] == "interceptions":
            made += lib.num(st.get("interceptions")) or 0
    return (y, made - thrown) if seen else None


run = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
pre = {}
pts = []
for g in allf:
    for side in ("home", "away"):
        pre[(g["id"], side)] = tuple(run[(g["season"], g[side])])
    lh, la = team_line(g["id"], g["home"]), team_line(g["id"], g["away"])
    if lh is None or la is None:
        continue
    m = g["hs"] - g["as"]
    for side, sg, me in (("home", 1, lh), ("away", -1, la)):
        r = run[(g["season"], g[side])]
        r[0] += 1
        r[1] += sg * m
        r[2] += sg * (lh[0] - la[0])
        r[3] += me[1]
    pts.append((g["season"], m, lh[0] - la[0]))
tr = [(m, y) for s, m, y in pts if s <= 2022]
b = sum(m * y for m, y in tr) / sum(y * y for m, y in tr)
CUTS = (2, 4, 7) if LG == "nfl" else (3, 6, 10)
LUCKY = CUTS[1]
cells = lib.Cells()
now = []
for g in fin:
    if g["stype"] != "2" or g["season"] < 2021:
        continue
    st = {}
    for side in ("home", "away"):
        n, pm, ym, im = pre.get((g["id"], side), (0, 0, 0, 0))
        if n < 3:
            break
        st[side] = (pm / n - b * ym / n, im / n, n)
    else:
        for side, team, opp, o, won, home in lib.sides(g):
            if not lib.dog_band(o):
                continue
            L, im, n = st[side]
            s = g["season"]
            pl = lib.profit(won, lib.dec(o))
            ep = lib.early_price(hist, g["id"], side)
            lab = []
            for c_ in CUTS:
                if L >= c_:
                    lab.append(f"dose: luck +{c_}+")
            lab.append("dose: luck under +0 (the rest)" if L < 0 else "dose: luck 0..+" + str(LUCKY) if L < LUCKY else
                       "LUCKY")
            if L >= LUCKY:
                lab += [f"LUCKY | {'+100..+150' if o <= 150 else '+151..+250' if o <= 250 else '+251..+350'}",
                        f"LUCKY | {'home' if home else 'road'}",
                        f"LUCKY | INT margin {'+0.5 or better (INT-lucky)' if im >= 0.5 else 'under +0.5'}",
                        f"LUCKY | games {'3-5' if n <= 5 else '6+'}",
                        f"LUCKY | opponent luck {'under 0' if st['away' if home else 'home'][0] < 0 else '0+'}"]
            for x in lab:
                cells.add(x, s, pl)
                if ep and lib.dog_band(ep[0]):
                    cells.add(x + " | first fair", s, lib.profit(won, ep[1]))
# the teams flagged now (2026 season, games after the last final): the season-to-date luck of every team
cur = max(s for s, _, _ in pts)
last = defaultdict(lambda: None)
for (s, t), r in run.items():
    if s == cur and r[0] >= 3:
        last[t] = (r[1] / r[0] - b * r[2] / r[0], r[0])
flag = sorted(((v[0], t, v[1]) for t, v in last.items() if v and v[0] >= LUCKY), reverse=True)
names = {}
for g in allf:
    names[g["home"]] = g["home"]
print(f"{LG} slope {b:.4f}; teams now at luck +{LUCKY}+ (3+ boxed games): {len(flag)}")
res = cells.dump(TAG, f"{TAG.upper()} {LG} - the lucky dog's cuts (dogs +100..+350, close + first fair)", (2021, 2022),
                 (2023, 2024, 2025, 2026))
import json, os  # noqa: E401,E402
json.dump([(round(v, 1), t, n) for v, t, n in flag], open(os.path.join(lib.OUT, f"{TAG}_flagged_now.json"), "w"))
