"""10/27 robustness on the football cells that looked like something: (a) a college -151..-400 favorite that TRAILED at
the half in each of its last 2 games (z -3.0) - other cutoffs, the mirror dog, with the engine's cold / skid items out;
(b) a college -101..-150 favorite whose record sits 0.20+ UNDER its points (z -2.5) - other cutoffs + the mirror dog;
(c) the NFL 'lucky' small favorite (+30% on 27) - other cutoffs."""
import os, sys
sys.argv = [sys.argv[0]]
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "studies.py")).read().split("# ---------------- S1 PYTHAGOREAN LUCK")[0])


def mirror(rows, pick):
    idx = {(x["gid"], x["side"]): x for x in rows}
    out = []
    for x in rows:
        o = idx.get((x["gid"], "away" if x["side"] == "home" else "home"))
        if o is not None and pick(o):
            out.append(x)
    return out


nc = LG["ncaaf"]
h2 = [x for x in nc if len(x["half2"]) == 2 and None not in x["half2"]]
LINES.append("(a) COLLEGE BIG FAVORITE THAT TRAILED AT THE HALF IN BOTH OF ITS LAST 2")
for lo, hi in ((-250, -151), (-400, -251), (-1000, -401)):
    cell(f"trailed both, fav {lo}..{hi}", [x for x in h2 if x["half2"][0] < 0 and x["half2"][1] < 0 and band(x, lo, hi)],
         [x for x in h2 if band(x, lo, hi)])
for d in (7, 14):
    cell(f"trailed both by {d}+, fav -151..-400", [x for x in h2 if x["half2"][0] <= -d and x["half2"][1] <= -d and band(x, -400, -151)],
         [x for x in h2 if band(x, -400, -151)])
cell("trailed the LAST half only, fav -151..-400", [x for x in h2 if x["half2"][1] < 0 and x["half2"][0] >= 0 and band(x, -400, -151)],
     [x for x in h2 if band(x, -400, -151)])
cell("trailed both but WON both, fav -151..-400", [x for x in h2 if x["half2"][0] < 0 and x["half2"][1] < 0 and band(x, -400, -151)
                                                   and x["last_won"] is True and x["w"] >= 2],
     [x for x in h2 if band(x, -400, -151)])
cell("trailed both, winning record, fav -151..-400", [x for x in h2 if x["half2"][0] < 0 and x["half2"][1] < 0 and band(x, -400, -151)
                                                      and x["w"] > x["l"]], [x for x in h2 if band(x, -400, -151) and x["w"] > x["l"]])
tb = lambda o: len(o["half2"]) == 2 and None not in o["half2"] and o["half2"][0] < 0 and o["half2"][1] < 0 and band(o, -400, -151)  # noqa: E731
cell("MIRROR: the dog +151..+400 facing it", [x for x in mirror(nc, tb) if band(x, 151, 400)], [x for x in nc if band(x, 151, 400)])
cell("MIRROR: the dog +151..+400 facing it, home dog", [x for x in mirror(nc, tb) if band(x, 151, 400) and x["home"]],
     [x for x in nc if band(x, 151, 400) and x["home"]])
cell("same, NFL fav -151..-400", [x for x in LG["nfl"] if len(x["half2"]) == 2 and None not in x["half2"] and x["half2"][0] < 0
                                  and x["half2"][1] < 0 and band(x, -400, -151)], [x for x in LG["nfl"] if band(x, -400, -151)])

LINES.append("\n(b) COLLEGE SMALL FAVORITE WHOSE RECORD SITS UNDER ITS POINTS")
pool = [x for x in nc if pyth(x) is not None]
for c in (0.10, 0.15, 0.25, 0.30):
    cell(f"unlucky {c:.2f}+, fav -101..-150", [x for x in pool if pyth(x) <= -c and band(x, -150, -101)], [x for x in pool if band(x, -150, -101)])
cell("unlucky 0.20+, fav -101..-200", [x for x in pool if pyth(x) <= -0.2 and band(x, -200, -101)], [x for x in pool if band(x, -200, -101)])
ul = lambda o: pyth(o) is not None and pyth(o) <= -0.2 and band(o, -150, -101)  # noqa: E731
cell("MIRROR: the dog facing it (+100..+150)", [x for x in mirror(nc, ul) if band(x, 100, 150)], [x for x in nc if band(x, 100, 150)])
cell("unlucky 0.20+, fav -101..-150, losing record", [x for x in pool if pyth(x) <= -0.2 and band(x, -150, -101) and x["w"] < x["l"]],
     [x for x in pool if band(x, -150, -101) and x["w"] < x["l"]])

LINES.append("\n(c) NFL 'LUCKY' SMALL FAVORITE")
pool = [x for x in LG["nfl"] if pyth(x) is not None]
for c in (0.10, 0.15, 0.25):
    cell(f"lucky {c:.2f}+, fav -101..-150", [x for x in pool if pyth(x) >= c and band(x, -150, -101)], [x for x in pool if band(x, -150, -101)])
cell("lucky 0.20+, fav -101..-200", [x for x in pool if pyth(x) >= 0.2 and band(x, -200, -101)], [x for x in pool if band(x, -200, -101)])
print("\n".join(LINES))

LINES.clear()
LINES.append("\n(b2) the unlucky college small favorite, split")
pool = [x for x in nc if pyth(x) is not None and band(x, -150, -101)]
ul2 = [x for x in pool if pyth(x) <= -0.15]
cell("unlucky 0.15+, off a LOSS", [x for x in ul2 if x["last_won"] is False], [x for x in pool if x["last_won"] is False])
cell("unlucky 0.15+, off a WIN", [x for x in ul2 if x["last_won"] is True], [x for x in pool if x["last_won"] is True])
cell("unlucky 0.15+, at HOME", [x for x in ul2 if x["home"]], [x for x in pool if x["home"]])
cell("unlucky 0.15+, on the ROAD", [x for x in ul2 if not x["home"]], [x for x in pool if not x["home"]])
cell("unlucky 0.15+, games 4-6", [x for x in ul2 if x["gp"] <= 6], [x for x in pool if x["gp"] <= 6])
cell("unlucky 0.15+, games 7+", [x for x in ul2 if x["gp"] >= 7], [x for x in pool if x["gp"] >= 7])
cell("unlucky 0.15+, Elo better than the opponent", [x for x in ul2 if x["elo"] > x["o_elo"]], [x for x in pool if x["elo"] > x["o_elo"]])
cell("NFL unlucky 0.15+, fav -101..-150", [x for x in LG["nfl"] if pyth(x) is not None and pyth(x) <= -0.15 and band(x, -150, -101)],
     [x for x in LG["nfl"] if band(x, -150, -101)])
print("\n".join(LINES))
