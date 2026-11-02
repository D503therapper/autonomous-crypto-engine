"""Follow-up of s0 / s5 (the one early picture that shows in BOTH markets): the college hoops ROAD dog (+100..+350,
a true road game, not a neutral floor) early in the season. Windows by the calendar (days 0-7 / 0-14) and by the dog's
own game number (1-2 / 1-3 / 4-6 / 7+), at the close and at ESPN's OPEN (2023-25 - the second check), ATS on the same
games, and the HOME dog in the same windows (the mirror). The college hoops Dog is off and dog_plays skip college
hoops, but the daily floor (sports.floor_plays) still takes college hoops dogs by dog score - this is where it bites.
Train 2018-22, held out 2023 / 24 / 25 apart."""
import lib
from collections import defaultdict

rows = [r for r in lib.annotate(lib.load()) if r["season"] >= 2018]
cells = defaultdict(lib.Cell)
for r in rows:
    if str(r["neutral"]) == "1":
        continue
    try:
        mh, ma = float(r["ml_home"]), float(r["ml_away"])
    except (TypeError, ValueError):
        continue
    if abs(mh) < 100 or abs(ma) < 100:
        continue
    d = r["day_in_season"]
    sp = lib.fnum(r["spread_home"])
    for side, odds, won in (("away", ma, r["as_"] > r["hs"]), ("home", mh, r["hs"] > r["as_"])):
        if not 100 <= odds <= 350:
            continue
        gn = r["gn_" + side]
        s = r["season"]
        labs = []
        labs.append("days 0-7" if d <= 7 else ("days 8-14" if d <= 14 else "day 15+"))
        labs.append("dog game 1-2" if gn <= 2 else ("dog game 3" if gn == 3 else ("dog game 4-6" if gn <= 6 else "dog game 7+")))
        if gn <= 3:
            labs.append("dog game 1-3")
        who = "ROAD dog" if side == "away" else "HOME dog"
        for lab in labs:
            cells[f"{who} ML close | {lab}"].add(s, lib.ml_profit(odds, won), won)
            oo = lib.fnum(r.get(f"ml_{side}_open"))
            if oo and 100 <= oo <= 350:
                cells[f"{who} ML OPEN  | {lab}"].add(s, lib.ml_profit(oo, won), won)
            if sp is not None:
                line = sp if side == "home" else -sp
                m = (r["hs"] - r["as_"]) * (1 if side == "home" else -1)
                cells[f"{who} ATS      | {lab}"].add(s, lib.ats_profit(m + line, -110.0))
print(__doc__)
for k in sorted(cells):
    print(cells[k].line(k))
