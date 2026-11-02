"""11/2 #2 - NBA SECOND NIGHT OF A BACK-TO-BACK BY TRAVEL DISTANCE (never cut by miles: the 10/30 study had the rested
favorite -101..-150 vs a b2b team and "opponent travelled"; the built +3 rested_vs_b2b is a flat dog weight).
The b2b team = played the day before (previous tip 0.6-1.3 days earlier); miles = previous game's venue -> tonight's
(venues.json). Sides graded at the close: the b2b team as a dog +100..+350 / a favorite -101..-300 and ATS; the RESTED
dog across a b2b team by that team's miles (the built weight's cell, as a dose). Second check: the 2020-23 morning.
#3 (rest stacking) is s3_nba_rest_stack.py on the same table. Train 2016-2022, held 2023 / 2024 / 2025, now 2026."""
from lib import *

TRAIN, HELD = (2016, 2022), [2023, 2024, 2025, 2026]


def table():
    fin = [g for g in finals("nba") if g["stype"] == "2"]
    allg = all_finals("nba")
    tl = team_log(allg)
    xy = coords("nba")
    rows = []
    for g in fin:
        r = {"g": g}
        for side in ("home", "away"):
            tm = g[side]
            prev = before(tl, tm, g["start"], 1)
            if not prev or prev[0]["season"] != g["season"]:
                r[side] = None
                continue
            p = prev[0]
            rest = days_between(p["start"], g["start"])
            a, b = xy.get(p["id"]), xy.get(g["id"])
            mi = miles(a, b) if a and b else None
            r[side] = {"rest": rest, "b2b": 0.6 <= rest <= 1.3, "mi": mi}
        rows.append(r)
    return rows


def mb(mi):
    if mi is None:
        return None
    return "0 same arena" if mi < 5 else "1-499" if mi < 500 else "500-999" if mi < 1000 else "1000+"


if __name__ == "__main__":
    c = Cells()
    mo = nba_morning()
    for r in table():
        g = r["g"]
        s = g["season"]
        for side, tm, opp, odds, won, home in sides(g):
            me, op = r[side], r["away" if home else "home"]
            if not me or not op or not me["b2b"]:
                continue
            b = mb(me["mi"])
            if b is None:
                continue
            ctx = "vs rested" if not op["b2b"] else "both b2b"
            d = dec(odds)
            p = profit(won, d)
            a = ats(g, side)
            if dog_band(odds):
                c.add(f"b2b team DOG miles {b} {ctx}", s, p)
            elif -300 <= odds <= -101:
                c.add(f"b2b team FAV -101..-300 miles {b} {ctx}", s, p)
            c.add(f"b2b team ATS miles {b} {ctx}", s, a)
            # the other side: the rested team across a b2b team, by the b2b team's miles (the built +3's cell)
            oside = "away" if home else "home"
            oodds = g["mla"] if home else g["mlh"]
            if not op["b2b"]:
                po = profit(not won, dec(oodds))
                if dog_band(oodds):
                    c.add(f"RESTED DOG vs b2b team that flew {b}", s, po)
                c.add(f"RESTED side ATS vs b2b team that flew {b}", s, ats(g, oside))
                m = mo.get(g["id"])
                if m and m.get("p") is not None and dog_band(american(m["dh"] if oside == "home" else m["da"])):
                    dm = m["dh"] if oside == "home" else m["da"]
                    c.add(f"morning RESTED DOG vs b2b team that flew {b}", s, profit(not won, dm))
    c.dump("s2", "NBA 2nd night of a back-to-back by travel miles (train 2016-22, held 2023-26 apart)", TRAIN, HELD)
