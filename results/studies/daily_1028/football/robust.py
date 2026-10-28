"""10/28 robustness on the football cells that looked like something: (a) a college -101..-150 favorite that ALLOWED 40+
last game (z -3.7) - is it more than the built 'college favorite off a loss' fade? other cutoffs, home / road, the mirror
dog; (b) an NFL dog whose defense held its last 2 foes to 10 or fewer (2-20) - other cutoffs; (c) the NFL dog that blew a
4th-quarter lead (2023+ -39%) - other cuts."""
import os, sys
sys.argv = [sys.argv[0]]
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "studies.py")).read().split("# ---------------- S1 ALLOWED 40+")[0])


def mirror(rows, pick):
    idx = {(x["gid"], x["side"]): x for x in rows}
    out = []
    for x in rows:
        o = idx.get((x["gid"], "away" if x["side"] == "home" else "home"))
        if o is not None and pick(o):
            out.append(x)
    return out


nc, nf = LG["ncaaf"], LG["nfl"]
F = [x for x in nc if band(x, -150, -101) and x["last_pa"] is not None]
LINES.append("(a) COLLEGE -101..-150 FAVORITE THAT ALLOWED A LOT LAST GAME (base = every band favorite with a last game)")
offl = [x for x in F if x["last_won"] is False]
cell("fav off a LOSS (the built 10/14 fade, all)", offl, F)
for lo, hi in ((0, 20), (21, 29), (30, 39), (40, 99)):
    cell(f"fav off a LOSS allowing {lo}-{hi}", [x for x in offl if lo <= x["last_pa"] <= hi], offl)
for c in (35, 45, 50):
    cell(f"fav allowed {c}+ last game (win or loss)", [x for x in F if x["last_pa"] >= c], F)
cell("fav off a WIN, allowed 30+", [x for x in F if x["last_won"] and x["last_pa"] >= 30], [x for x in F if x["last_won"]])
cell("fav off a LOSS allowing 40+, HOME", [x for x in offl if x["last_pa"] >= 40 and x["home"]], [x for x in offl if x["home"]])
cell("fav off a LOSS allowing 40+, ROAD/neutral", [x for x in offl if x["last_pa"] >= 40 and not x["home"]], [x for x in offl if not x["home"]])
cell("fav off a LOSS allowing 40+, lost by 14+", [x for x in offl if x["last_pa"] >= 40 and x["last_margin"] <= -14], offl)
cell("fav off a LOSS allowing 40+, lost by <14", [x for x in offl if x["last_pa"] >= 40 and x["last_margin"] > -14], offl)
cell("fav -151..-200 off a LOSS allowing 40+", [x for x in nc if band(x, -200, -151) and x["last_won"] is False and (x["last_pa"] or 0) >= 40],
     [x for x in nc if band(x, -200, -151) and x["last_won"] is False])
cell("MIRROR: the dog +101..+150 across from it", [x for x in mirror(nc, lambda o: band(o, -150, -101) and o["last_pa"] is not None
                                                                     and o["last_pa"] >= 40) if band(x, 100, 150)],
     [x for x in nc if band(x, 100, 150)])
cell("NFL fav -101..-150 allowed 35+ last game", [x for x in nf if band(x, -150, -101) and (x["last_pa"] or 0) >= 35],
     [x for x in nf if band(x, -150, -101)])
cell("NFL fav -101..-150 allowed 30+ AND LOST", [x for x in nf if band(x, -150, -101) and (x["last_pa"] or 0) >= 30 and x["last_won"] is False],
     [x for x in nf if band(x, -150, -101) and x["last_won"] is False])

LINES.append("\n(b) NFL DOG WITH A DEFENSE ON A ROLL (allowed X or fewer in each of the last 2)")
D = [x for x in nf if band(x, 100, 350) and len(x["pa2"]) == 2]
for c in (10, 13, 14, 17):
    cell(f"NFL dog, held last 2 to {c} or fewer", [x for x in D if max(x["pa2"]) <= c], D)
cell("NFL dog, held LAST game to 10 or fewer", [x for x in D if x["pa2"][-1] <= 10], D)
cell("college dog, held last 2 to 10 or fewer", [x for x in nc if band(x, 100, 350) and len(x["pa2"]) == 2 and max(x["pa2"]) <= 10],
     [x for x in nc if band(x, 100, 350)])

LINES.append("\n(c) NFL DOG THAT BLEW A 4TH-QUARTER LEAD AND LOST")
P = [x for x in nf if band(x, 100, 350) and x["q3_last"] is not None and x["last_won"] is not None]
for c in (1, 4, 8):
    cell(f"NFL dog led by {c}+ after 3, lost", [x for x in P if x["q3_last"] >= c and not x["last_won"]], P)
cell("NFL dog lost a one-score game it led after 3", [x for x in P if x["q3_last"] > 0 and not x["last_won"] and x["last_margin"] >= -8], P)
cell("NFL dog lost by 1-8 (any)", [x for x in P if not x["last_won"] and x["last_margin"] >= -8], P)

print("\n".join(LINES))
