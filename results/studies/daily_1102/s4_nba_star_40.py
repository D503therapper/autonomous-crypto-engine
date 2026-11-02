"""11/2 #4 - NBA: THE TEAM WHOSE STAR JUST SCORED 40+ (box scores 2016-26). Does the market chase the big night (fade the
team next game) or under-rate it? The team's NEXT game (same season, within 4 days): dogs +100..+350, favorites
-101..-150 / -151..-300, ATS, the over; split by won / lost the 40-point game and 50+. The opponent across it too
(the mirror). Second check: the 2020-23 game-day morning price. Train 2016-2022, held 2023 / 2024 / 2025, now 2026."""
from lib import *

TRAIN, HELD = (2016, 2022), [2023, 2024, 2025, 2026]


def pts(st, r):
    try:
        return int(float(st.get("points") or 0))
    except ValueError:
        return None


box = boxes("nba", pts)
allg = all_finals("nba")
tl = team_log(allg)
fin = [g for g in finals("nba") if g["stype"] == "2"]
mo = nba_morning()
c = Cells()
seen = 0
for g in fin:
    s = g["season"]
    for side, tm, opp, odds, won, home in sides(g):
        pr = before(tl, tm, g["start"], 1)
        if not pr or pr[0]["season"] != s or days_between(pr[0]["start"], g["start"]) > 4.5:
            continue
        p0 = pr[0]
        bx = (box.get(p0["id"]) or {}).get(str(tm))
        if not bx:
            continue
        seen += 1
        top = max(bx.values())
        if top < 40:
            key = "no 40"
        else:
            key = ("50+" if top >= 50 else "40-49") + (" in a WIN" if won_g(p0, tm) else " in a LOSS")
        p = profit(won, dec(odds))
        band = ("DOG" if dog_band(odds) else "FAV -101..-150" if -150 <= odds <= -101 else
                "FAV -151..-300" if -300 <= odds <= -151 else None)
        if band:
            c.add(f"{band} after star {key}", s, p)
            if top >= 40:
                c.add(f"{band} after star 40+ (all)", s, p)
        c.add(f"ATS after star {key}", s, ats(g, side))
        if top >= 40:
            c.add("ATS after star 40+ (all)", s, ats(g, side))
            c.add("OVER after star 40+ (all)", s, tot_profit(g, True))
            oo = g["mla"] if home else g["mlh"]
            if dog_band(oo):
                c.add("OPP DOG across a team whose star had 40+", s, profit(not won, dec(oo)))
            m = mo.get(g["id"])
            if m and m.get("dh") and band:
                dm = m["dh"] if home else m["da"]
                c.add(f"morning {band} after star 40+", s, profit(won, dm))
        else:
            c.add("OVER after no 40", s, tot_profit(g, True))
print("sides with a last box score:", seen)
c.dump("s4", "NBA: the next game after the team's top scorer had 40+ (train 2016-22, held 2023-26 apart)", TRAIN, HELD)
