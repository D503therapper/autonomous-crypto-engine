"""10/29 football robustness - the cells that printed a SURVIVOR / FADE line in studies_out.txt, cut every way that
could fake them: the full spread's size (key numbers set the 1st-half share), the open-to-close move (a stale 1st-half
line next to a moved full line looks like a 'big share'), the dose, the season, the other sport."""
import os, sys, pickle
sys.argv = [sys.argv[0]]
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "studies.py")).read().split("# ---------------- S1")[0]
exec(compile(src, "harness", "exec"))


def share(x):
    if x["h1sp"] is None or x["pts"] is None or abs(x["pts"]) < 2.5:
        return None
    return x["h1sp"] / x["pts"]


def moved(x):           # the side's no-vig win chance, close minus open (+ = the money came to it)
    return None if x["op"] is None else x["mp"] - x["op"]


LINES.append("R1 NFL / college 1st-half share, dogs +100..+350, by the full spread's size")
for lg, rows in LG.items():
    d = [x for x in rows if share(x) is not None and band(x, 100, 350)]
    for nm, lo, hi in (("2.5-3.5", 2.5, 3.5), ("4-6.5", 4, 6.5), ("7-9.5", 7, 9.5), ("10+", 10, 99)):
        b = [x for x in d if lo <= x["pts"] <= hi]
        cell(f"{lg} spread {nm} - share 0.60+", [x for x in b if share(x) >= 0.60], b, primary=False)
        cell(f"{lg} spread {nm} - share under 0.45", [x for x in b if share(x) < 0.45], b, primary=False)
        cell(f"{lg} spread {nm} - share 0.45-0.60", [x for x in b if 0.45 <= share(x) < 0.60], b, primary=False)

LINES.append("\nR2 NFL dogs: the 1st-half share vs the open-to-close move (does the share just carry the move?)")
d = [x for x in LG["nfl"] if share(x) is not None and band(x, 100, 350) and moved(x) is not None]
for nm, f_ in (("money came to the dog (+1 pt+)", lambda x: moved(x) >= 0.01), ("flat (-1..+1)", lambda x: -0.01 < moved(x) < 0.01),
               ("money left the dog (-1 pt+)", lambda x: moved(x) <= -0.01)):
    b = [x for x in d if f_(x)]
    cell(f"nfl dog, {nm} - share 0.60+", [x for x in b if share(x) >= 0.60], b, primary=False)
    cell(f"nfl dog, {nm} - share under 0.60", [x for x in b if share(x) < 0.60], b, primary=False)
avg = lambda xs: sum(xs) / len(xs) if xs else float("nan")
LINES.append(f"  mean move (pts): share 0.60+ {100*avg([moved(x) for x in d if share(x) >= .6]):+.2f}  "
             f"under 0.45 {100*avg([moved(x) for x in d if share(x) < .45]):+.2f}  0.45-0.60 {100*avg([moved(x) for x in d if .45 <= share(x) < .6]):+.2f}")

LINES.append("\nR3 NFL dog off a shootout (last game 17+ over its total): the dose, its own points vs allowed, won / lost")
d = [x for x in LG["nfl"] if x["tmiss"] is not None and band(x, 100, 350)]
for nm, lo, hi in (("over 7-16", 7, 16.5), ("over 17-23", 17, 23.5), ("over 24+", 24, 99), ("under 7+", -99, -7)):
    cell(f"nfl dog, last game {nm}", [x for x in d if lo <= x["tmiss"] <= hi], d, primary=False)
s = [x for x in d if x["tmiss"] >= 17]
cell("nfl dog off a shootout it WON", [x for x in s if x["last_won"]], d, primary=False)
cell("nfl dog off a shootout it LOST", [x for x in s if x["last_won"] is False], d, primary=False)
cell("nfl dog off a shootout, scored 30+ itself", [x for x in s if (x["last_pf"] or 0) >= 30], d, primary=False)
cell("nfl dog off a shootout, allowed 30+", [x for x in s if (x["last_pa"] or 0) >= 30], d, primary=False)
cell("nfl dog off a shootout, NOT allowing 35+ (outside the 10/28 cell)", [x for x in s if (x["last_pa"] or 0) < 35], d, primary=False)
cell("nfl dog +100..+150 off a shootout", [x for x in s if x["ml"] <= 150], [x for x in d if x["ml"] <= 150], primary=False)
cell("nfl dog +151..+350 off a shootout", [x for x in s if x["ml"] > 150], [x for x in d if x["ml"] > 150], primary=False)
cell("nfl FAV across from a dog off a shootout (-101..-400)", [x for x in LG["nfl"] if band(x, -400, -101) and (x["o_tmiss"] or -99) >= 17],
     [x for x in LG["nfl"] if band(x, -400, -101) and x["o_tmiss"] is not None], primary=False)

LINES.append("\nR4 NFL dog that was a dog in each of its last 4: the dose and the record")
d = [x for x in LG["nfl"] if band(x, 100, 350) and len(x["prev_ml"]) >= 4]
for k in (3, 4, 5, 6):
    dd = [x for x in LG["nfl"] if band(x, 100, 350) and len(x["prev_ml"]) >= k]
    cell(f"nfl dog, a dog in each of its last {k}", [x for x in dd if min(x["prev_ml"][-k:]) > 0], dd, primary=False)
s = [x for x in d if min(x["prev_ml"][-4:]) > 0]
cell("  ... with a .250 or worse record", [x for x in s if x["w"] <= 0.25 * (x["w"] + x["l"])], d, primary=False)
cell("  ... with a better than .250 record", [x for x in s if x["w"] > 0.25 * (x["w"] + x["l"])], d, primary=False)
cell("  ... +100..+150", [x for x in s if x["ml"] <= 150], [x for x in d if x["ml"] <= 150], primary=False)
cell("  ... +151..+350", [x for x in s if x["ml"] > 150], [x for x in d if x["ml"] > 150], primary=False)
cell("  ... at home", [x for x in s if x["home"]], [x for x in d if x["home"]], primary=False)
cell("  ... on the road", [x for x in s if not x["home"]], [x for x in d if not x["home"]], primary=False)

print("\n".join(LINES))
