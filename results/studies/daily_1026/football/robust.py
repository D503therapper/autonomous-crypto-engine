"""10/26 robustness on the two cells that looked like something: (a) the shootout WINNER as a big favorite (NFL z +3.0,
college the same sign), other cutoffs + the mirror dog + the bettable band; (b) the college road dog off a 21+ home
loss (-19%), with the engine's built cold-dog / skid fades taken out (is it new information?)."""
import os, sys
sys.argv = [sys.argv[0]]
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "studies.py")).read().split("# ---------------- S1 LOOK-AHEAD")[0])

LINES.append("(a) SHOOTOUT WINNER, other cutoffs")
for lg, rows in LG.items():
    pool = [x for x in rows if x["last_pf"] is not None]
    for cut in ((28, 31, 35, 40) if lg == "nfl" else (31, 35, 42, 49)):
        so = [x for x in pool if x["last_pf"] >= cut and x["last_pa"] >= cut and x["last_won"] is True]
        cell(f"{lg} shootout ({cut}+ both) WINNER fav -151..-400", [x for x in so if band(x, -400, -151)],
             [x for x in pool if band(x, -400, -151)])
        cell(f"{lg} shootout ({cut}+ both) WINNER fav -101..-200", [x for x in so if band(x, -200, -101)],
             [x for x in pool if band(x, -200, -101)])
    # allowed 30+/35+ and WON, any score for the other side (is it 'the defense looked bad' or the shootout?)
    cut = 30 if lg == "nfl" else 35
    aw = [x for x in pool if x["last_pa"] >= cut and x["last_won"] is True]
    cell(f"{lg} WON while allowing {cut}+ - fav -151..-400", [x for x in aw if band(x, -400, -151)], [x for x in pool if band(x, -400, -151)])
    # mirror: the dog facing such a favorite
    idx = {(x["gid"], x["side"]): x for x in pool}
    mir = []
    for x in rows:
        o = idx.get((x["gid"], "away" if x["side"] == "home" else "home"))
        if o and o["last_pf"] >= cut and o["last_pa"] >= cut and o["last_won"] is True and band(o, -400, -151):
            mir.append(x)
    cell(f"{lg} the DOG facing a shootout-winner favorite (-151..-400)", mir, [x for x in rows if band(x, 151, 400)])

LINES.append("\n(b) COLLEGE ROAD DOG OFF A 21+ HOME LOSS, cold dogs out")
nc = LG["ncaaf"]
pool = [x for x in nc if x["last_margin"] is not None and band(x, 100, 350) and not x["home"]]
hl = [x for x in pool if x["last_home"] is True and x["last_margin"] <= -21]
cold = lambda x: x["w"] + x["l"] >= 4 and x["w"] / (x["w"] + x["l"]) < 0.30
cell("road dog off a 21+ home loss, NOT under .300", [x for x in hl if not cold(x)], [x for x in pool if not cold(x)])
cell("road dog off a 21+ home loss, winning record", [x for x in hl if x["w"] > x["l"]], [x for x in pool if x["w"] > x["l"]])
cell("road dog off a 21+ home loss, games 2-5", [x for x in hl if x["w"] + x["l"] <= 5], [x for x in pool if x["w"] + x["l"] <= 5])
for m in (14, 28, 35):
    cell(f"road dog off a {m}+ home loss", [x for x in pool if x["last_home"] is True and x["last_margin"] <= -m], pool)
cell("road dog off a 21+ ROAD loss (control)", [x for x in pool if x["last_home"] is False and x["last_margin"] <= -21], pool)
cell("home dog off a 21+ home loss (control)", [x for x in nc if band(x, 100, 350) and x["home"] and x["last_home"] is True
                                                and x["last_margin"] is not None and x["last_margin"] <= -21],
     [x for x in nc if band(x, 100, 350) and x["home"] and x["last_margin"] is not None])

print("\n".join(LINES))
