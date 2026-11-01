"""Study 6 (11/1): NBA + NHL - THE FIRST MEETING AFTER A PLAYOFF SERIES. The team that got knocked out of the playoffs
last spring meets the team that eliminated it for the first time in the new regular season - the "revenge" spot the
TV talks about. Series from our playoff finals (stype 3): the pair's games in that postseason, the winner = the team
that won more of them. Bet the ELIMINATED team (and the eliminator) at the closing moneyline in that first meeting;
the second check = every regular-season meeting the next season, and the eliminated team only when it's a dog. Small
by nature (~15 series a sport a season). Train = the series of 2018-2022 (meetings 2019-23 seasons), held out = the
later seasons apart."""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TR, HE = (2018, 2022), (2023, 2024, 2025, 2026)
C = lib.Cells()
for lg in ("nba", "nhl"):
    allf = lib.all_finals(lg)
    series = defaultdict(lambda: defaultdict(int))     # (season, pair) -> {team: wins}
    for g in allf:
        if g["stype"] != "3":
            continue
        w = g["home"] if g["hs"] > g["as"] else g["away"]
        series[(g["season"], frozenset((g["home"], g["away"])))][w] += 1
    elim = {}                                           # (next season, eliminated team, eliminator) -> games won by loser
    for (s, pair), wins in series.items():
        if len(pair) != 2 or sum(wins.values()) < 4:    # a play-in game is not a series
            continue
        a, b = sorted(pair, key=lambda t: -wins.get(t, 0))
        if wins.get(a, 0) == wins.get(b, 0):
            continue
        elim[(s + 1, b, a)] = (wins.get(b, 0), wins.get(a, 0))
    seen = set()
    for g in lib.finals(lg):
        if g["stype"] != "2":
            continue
        s = g["season"]
        pk = (s, frozenset((g["home"], g["away"])))
        first = pk not in seen
        seen.add(pk)
        for side, team, opp, o, won, home in lib.sides(g):
            k = (s, team, opp)
            if k in elim:
                lw, ww = elim[k]
                pr = lib.profit(won, lib.dec(o))
                tags = ["every meeting the next season"] + (["FIRST meeting"] if first else [])
                for t in tags:
                    C.add(f"{lg} | ELIMINATED team | {t}", s, pr)
                    if o >= 100:
                        C.add(f"{lg} | ELIMINATED team as a dog | {t}", s, pr)
                    else:
                        C.add(f"{lg} | ELIMINATED team as a fav | {t}", s, pr)
                    if home:
                        C.add(f"{lg} | ELIMINATED team at home | {t}", s, pr)
                    if lw <= 1:
                        C.add(f"{lg} | ELIMINATED team, swept / won 1 | {t}", s, pr)
                    C.add(f"{lg} | ATS ELIMINATED team | {t}", s, lib.ats(g, side) if lg == "nba" else None)
            elif (s, opp, team) in elim:
                pr = lib.profit(won, lib.dec(o))
                for t in ["every meeting the next season"] + (["FIRST meeting"] if first else []):
                    C.add(f"{lg} | ELIMINATOR | {t}", s, pr)

C.dump("s6", "THE FIRST MEETING AFTER A PLAYOFF SERIES, NBA + NHL (closing ML; train 2018-22, held 2023-26)", TR, HE)
