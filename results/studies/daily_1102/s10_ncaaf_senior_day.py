"""11/2 #10 - COLLEGE FOOTBALL SENIOR DAY: the team's LAST regular-season HOME game (the schedule is known all season -
no look-ahead). The seniors' last game at home, emotion, the crowd - or a market that pays for the story? The home side
on its final home date vs every other November home game: dogs +100..+350, favorites -101..-150 / -151..-400, ATS; at
the close and at the paid history's FIRST FAIR moneyline. Plus: senior day for a home team ALREADY eliminated from a
bowl (can't reach 6 wins) - nothing to play for but the seniors. Train 2016-2022, held 2023 / 2024 / 2025, now 2026
(2026's senior days run 11/7-11/29 - only games already played count)."""
from lib import *

TRAIN, HELD = (2016, 2022), [2023, 2024, 2025, 2026]
games = sd.load_games("ncaaf")
# each team's last scheduled regular-season, non-neutral home date per season (finals AND scheduled games)
last_home = {}
for gid, g in games.items():
    if str(g.get("stype") or "2") != "2" or str(g.get("neutral")) == "1" or not g.get("start"):
        continue
    k = (g["home"], season(g["start"]))
    if g["start"] > last_home.get(k, ""):
        last_home[k] = g["start"]
fin = [g for g in finals("ncaaf") if g["stype"] == "2" and not g["neutral"]]
tl = team_log(all_finals("ncaaf"))
xby = {x["id"]: x for x in load_football("ncaaf")}
c = Cells()
for g in fin:
    s = g["season"]
    m = int(g["start"][5:7])
    if m not in (11, 12):
        continue
    senior = last_home.get((g["home"], s)) == g["start"]
    k = "SENIOR DAY" if senior else "other Nov home"
    won = g["hs"] > g["as"]
    o = g["mlh"]
    p = profit(won, dec(o))
    band = ("home DOG" if dog_band(o) else "home FAV -101..-150" if -150 <= o <= -101 else
            "home FAV -151..-400" if -400 <= o <= -151 else None)
    if band:
        c.add(f"{k} {band}", s, p)
        ep = early_price(xby, g["id"], "home")
        if ep:
            c.add(f"first-fair {k} {band}", s, profit(won, ep[1]))
    c.add(f"{k} home ATS", s, ats(g, "home"))
    c.add(f"{k} home ML any price", s, p)
    if senior:
        pr = [x for x in before(tl, g["home"], g["start"]) if x["season"] == s]
        w = sum(1 for x in pr if won_g(x, g["home"]))
        left = 1                                                   # this game; regular seasons are 12 games
        out_of_it = w + left + max(0, 12 - len(pr) - 1) < 6 and len(pr) >= 9
        if out_of_it:
            c.add("SENIOR DAY, bowl hopes gone, home ATS", s, ats(g, "home"))
            if dog_band(o):
                c.add("SENIOR DAY, bowl hopes gone, home DOG", s, p)
c.dump("s10", "College football senior day (last home game) vs other Nov home games (train 2016-22, held 2023-26)",
       TRAIN, HELD)
