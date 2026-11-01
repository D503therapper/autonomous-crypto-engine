"""Study 10 (11/1): COLLEGE HOOPS PREP - THE SEASON OPENER vs A TEAM THAT HAS ALREADY PLAYED. Opening week (11/3)
puts teams playing their FIRST game against teams that already have 1-3 games under their belt (the early-tip events,
the first-night games). Is the rust / the game-legs edge priced? A side in its first game this season (no earlier final
on file for that team in the season - every game on file counts, priced or not) vs an opponent with 1+ / 2+ games
played; next to openers vs openers (the base) and to the team with games played vs an opener. Moneyline (dog +100..+350,
favorite -101..-150 / -151..-400), ATS and the total (a first game runs sloppy - under?) at the close. No live season
yet (check 4 n/a). Train 2018-21, held out 2022 / 2023 / 2024 / 2025 apart."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TR, HE = (2018, 2021), (2022, 2023, 2024, 2025)
allf = [g for g in lib.all_finals("ncaab") if g["stype"] == "2"]
tl = lib.team_log(allf)
C = lib.Cells()
for g in lib.finals("ncaab"):
    if g["stype"] != "2" or g["start"][5:7] not in ("11", "12"):
        continue
    s = g["season"]
    n = {t: len([x for x in lib.before(tl, t, g["start"]) if x["season"] == s]) for t in (g["home"], g["away"])}
    if min(n.values()) > 0:
        continue                                  # only games with at least one team in its opener
    both_open = max(n.values()) == 0
    if both_open:
        C.add("UNDER | both teams' opener", s, lib.tot_profit(g, False))
    else:
        C.add("UNDER | one team's opener vs a team that has played", s, lib.tot_profit(g, False))
    for side, team, opp, o, won, home in lib.sides(g):
        me, op = n[team], n[opp]
        site = "neutral" if g["neutral"] else "home" if home else "road"
        if me == 0 and op == 0:
            tags = ["OPENER vs an opener (base)"]
        elif me == 0:
            tags = ["OPENER vs a team with 1+ games"] + (["OPENER vs a team with 2+ games"] if op >= 2 else [])
        else:
            tags = ["team WITH games vs an opener"] + (["team with 2+ games vs an opener"] if me >= 2 else [])
        pr = lib.profit(won, lib.dec(o))
        band = "dog +100..+350" if lib.dog_band(o) else "fav -101..-150" if -150 <= o <= -101 else \
            "fav -151..-400" if -400 <= o < -150 else None
        for t in tags:
            if band:
                C.add(f"{band} | {t}", s, pr)
                C.add(f"{band} | {t} | {site}", s, pr)
            C.add(f"ATS | {t}", s, lib.ats(g, side))
            C.add(f"ATS | {t} | {site}", s, lib.ats(g, side))

C.dump("s10", "COLLEGE HOOPS: THE SEASON OPENER vs A TEAM THAT HAS PLAYED (closing prices; train 2018-21, held 2022-25)",
       TR, HE)
