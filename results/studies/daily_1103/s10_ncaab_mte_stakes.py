"""Study 10 (11/3): COLLEGE HOOPS - THE EARLY TOURNAMENT'S LAST DAY, BY WHAT'S AT STAKE, AND THE TRIP HOME. The 11/1
study graded the day-after-a-blowout consolation game. New cuts for the November / December exempt tournaments (neutral
site, 3 games in 3-5 days): the last day's CHAMPIONSHIP (both teams 2-0 in the event) vs the CONSOLATION (both 0-2) vs the
mixed games; the team playing its 3rd game in 4 days vs one on its 2nd; and THE TRIP HOME - a team's first game back
(home, within 10 days) after 3+ straight neutral-site games. Sides (dog +100..+350 ML, favorite -101..-200 ML, ATS)
and the UNDER. Closing prices 2016-26. Train 2016-21, held out 2022 / 2023 / 2024 / 2025 apart (the 2026 season has
one night of games)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2016, 2021), (2022, 2023, 2024, 2025)
fin = lib.finals("ncaab")
allf = lib.all_finals("ncaab")
tl = lib.team_log(allf)
C = lib.Cells()
for g in fin:
    if g["start"][5:7] not in ("11", "12"):
        continue
    info = {}
    for side, team in (("home", g["home"]), ("away", g["away"])):
        prev = [x for x in lib.before(tl, team, g["start"], 4) if x["season"] == g["season"]]
        rec = [x for x in prev if lib.days_between(x["start"], g["start"]) <= 4]   # games in the last 4 days
        neut_run = 0
        for x in reversed(prev):
            if x["neutral"]:
                neut_run += 1
            else:
                break
        info[side] = {"n4": len(rec), "wins4": sum(1 for x in rec if lib.won_g(x, team)),
                      "neut_run": neut_run,
                      "days": lib.days_between(prev[-1]["start"], g["start"]) if prev else None}
    h, a_ = info["home"], info["away"]
    stake = None
    if g["neutral"] and h["n4"] >= 2 and a_["n4"] >= 2:
        if h["wins4"] == h["n4"] and a_["wins4"] == a_["n4"]:
            stake = "championship (both unbeaten in the event)"
        elif h["wins4"] == 0 and a_["wins4"] == 0:
            stake = "consolation (both winless in the event)"
        else:
            stake = "mixed (one winner, one loser)"
    for side, team, opp, o, won, is_home in lib.sides(g):
        me, ot = info[side], info["away" if side == "home" else "home"]
        d = lib.dec(o)
        p = lib.profit(won, d)
        a = lib.ats(g, side)
        tags = []
        if stake:
            tags.append(f"MTE last day: {stake}")
            if me["wins4"] == me["n4"] and ot["wins4"] < ot["n4"]:
                tags.append("MTE mixed: the unbeaten side")
            if me["wins4"] < me["n4"] and ot["wins4"] == ot["n4"]:
                tags.append("MTE mixed: the beaten side")
        if g["neutral"] and me["n4"] >= 2 and ot["n4"] <= 1:
            tags.append("neutral: 3rd game in 4 days vs a team on its 1st/2nd")
        if not g["neutral"] and is_home and me["neut_run"] >= 3 and me["days"] is not None and me["days"] <= 10:
            tags.append("home again after 3+ straight neutral games")
        if not g["neutral"] and not is_home and ot["neut_run"] >= 3 and ot["days"] is not None and ot["days"] <= 10:
            tags.append("road team vs a host just home from 3+ neutral games")
        for tg in tags:
            C.add(f"{tg} | ATS", g["season"], a)
            if lib.dog_band(o):
                C.add(f"{tg} | dog ML +100..+350", g["season"], p)
            if -200 <= o <= -101:
                C.add(f"{tg} | fav ML -101..-200", g["season"], p)
    if stake:
        C.add(f"MTE last day: {stake} | UNDER", g["season"], lib.tot_profit(g, False))
    if g["neutral"]:
        C.add("neutral Nov-Dec base | UNDER", g["season"], lib.tot_profit(g, False))
C.dump("s10", "COLLEGE HOOPS: THE EXEMPT TOURNAMENT'S LAST DAY BY STAKES (championship / consolation / mixed) AND THE "
       "TRIP HOME (close 2016-26; train 2016-21, held 2022-25)", TRAIN, HELD)
