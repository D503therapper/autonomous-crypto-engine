"""11/2 #3 - NBA REST-ADVANTAGE STACKING: the team on 2+ days off vs a team on the 2nd night of a back-to-back (0 days),
vs the plain 1-day-rest side across a b2b team (the built +3 rested_vs_b2b dog weight's cell). The question: does more
rest add MORE than the built +3 (a dose)? Dogs +100..+350, favorites -101..-300 (the 10/30 -101..-150 favorite cell is
not re-cut), ATS. Plus the full stack: 2+ days off AND the b2b team on its 3rd game in 4 nights. Second check: the 2020-23
game-day morning price. Train 2016-2022, held 2023 / 2024 / 2025, now 2026."""
from lib import *
from s2_nba_b2b_travel import table, TRAIN, HELD

c = Cells()
mo = nba_morning()
fin = [g for g in finals("nba") if g["stype"] == "2"]
tl = team_log(all_finals("nba"))


def third_in_four(team, start):
    pr = before(tl, team, start, 2)
    return len(pr) == 2 and days_between(pr[0]["start"], start) <= 3.3


for r in table():
    g = r["g"]
    s = g["season"]
    for side, tm, opp, odds, won, home in sides(g):
        me, op = r[side], r["away" if home else "home"]
        if not me or not op or me["b2b"] or not op["b2b"]:
            continue
        rd = me["rest"]
        b = "odd gap" if rd < 1.6 else "1 day off" if rd < 2.6 else "2+ days off"     # tip-to-tip 2 days = 1 day off
        t34 = third_in_four(opp, g["start"])
        a = ats(g, side)
        p = profit(won, dec(odds))
        if dog_band(odds):
            c.add(f"rested DOG ({b}) vs b2b", s, p)
            if b == "2+ days off":
                c.add(f"rested DOG (2+ days off) vs b2b {'3rd-in-4' if t34 else 'not 3rd-in-4'}", s, p)
            c.add(f"rested DOG ({b}) vs b2b {'home' if home else 'road'}", s, p)
            m = mo.get(g["id"])
            if m and m.get("dh"):
                dm = m["dh"] if home else m["da"]
                if dog_band(american(dm)):
                    c.add(f"morning rested DOG ({b}) vs b2b", s, profit(won, dm))
        elif -300 <= odds <= -151:
            c.add(f"rested FAV -151..-300 ({b}) vs b2b", s, p)
        c.add(f"rested ATS ({b}) vs b2b", s, a)
        if b == "2+ days off":
            c.add(f"rested ATS (2+ days off) vs b2b {'3rd-in-4' if t34 else 'not 3rd-in-4'}", s, a)
c.dump("s3", "NBA rest stacking: rested side vs a team on a back-to-back, by the rested side's days off", TRAIN, HELD)
