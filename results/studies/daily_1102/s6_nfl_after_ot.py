"""11/2 #6 - NFL: THE GAME AFTER AN OVERTIME GAME (college 10/12, NBA 10/23, NHL 10/18 done - never the NFL). An extra
period = more snaps on tired legs and, for the loser, a gut punch. The team's NEXT game (same season, 4-14 days later)
by OT WIN / OT LOSS / OT TIE: dogs +100..+350, favorites -101..-150 / -151..-400, ATS - at the close, and at the paid
history's FIRST FAIR moneyline (posted after both teams' last games). Also the short week after OT (Thursday next).
Train 2016-2022, held 2023 / 2024 / 2025, now 2026."""
from lib import *

TRAIN, HELD = (2016, 2022), [2023, 2024, 2025, 2026]


def ot(g):
    ls = g.get("ls_h") or ""
    return len([x for x in str(ls).split(",") if x.strip() != ""]) > 4


fin = [g for g in finals("nfl") if g["stype"] == "2"]
allf = finals("nfl")
tl = team_log(allf)
xby = {x["id"]: x for x in load_football("nfl")}
c = Cells()
n_ot = 0
for g in fin:
    s = g["season"]
    for side, tm, opp, odds, won, home in sides(g):
        pr = before(tl, tm, g["start"], 1)
        if not pr or pr[0]["season"] != s:
            continue
        p0 = pr[0]
        gap = days_between(p0["start"], g["start"])
        if not 3.5 <= gap <= 15:
            continue
        if ot(p0):
            m = margin_g(p0, tm)
            key = "OT WIN" if m > 0 else "OT LOSS" if m < 0 else "OT TIE"
            n_ot += 1
        else:
            key = "no OT"
        p = profit(won, dec(odds))
        band = ("DOG" if dog_band(odds) else "FAV -101..-150" if -150 <= odds <= -101 else
                "FAV -151..-400" if -400 <= odds <= -151 else None)
        if band:
            c.add(f"{band} after {key}", s, p)
            ep = early_price(xby, g["id"], side)
            if ep:
                c.add(f"first-fair {band} after {key}", s, profit(won, ep[1]))
        c.add(f"ATS after {key}", s, ats(g, side))
        if key != "no OT" and gap < 5.5:
            c.add(f"ATS after {key}, short week", s, ats(g, side))
        # both teams: the OT team vs an opponent that didn't go to OT
        if key != "no OT":
            c.add("ATS after any OT game", s, ats(g, side))
            if band:
                c.add(f"{band} after any OT game", s, p)
print("sides after an OT game:", n_ot)
c.dump("s6", "NFL: the next game after an overtime game (close + first fair price; train 2016-22, held 2023-26)", TRAIN, HELD)
