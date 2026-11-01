"""Study 8 (11/1): NBA - THE OVER / UNDER STREAK. Does the market chase a team whose games keep going OVER (or UNDER)
its closing total? Each team's last 3 / 4 games this season vs THAT game's closing total (games before tonight only).
Bet the opposite (the under when both teams went over in each of their last 3, the over after both went under), and
the streak itself, at tonight's closing total and its juice - against every game. Second check: the NHL (closing totals
2018-26; the 10/16 study looked at goals scored, not over / under the line). Train 2018-22, held out 2023-26 apart."""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TR, HE = (2018, 2022), (2023, 2024, 2025, 2026)
C = lib.Cells()
for lg in ("nba", "nhl"):
    hist = defaultdict(list)                      # (season, team) -> [+1 over / -1 under / 0 push]
    for g in lib.finals(lg):
        if g["stype"] != "2":
            continue
        s = g["season"]
        if g["total"] is not None:
            st = {}
            for t in (g["home"], g["away"]):
                h = hist[(s, t)]
                st[t] = (h[-3:] if len(h) >= 3 else None, h[-4:] if len(h) >= 4 else None)
            o, u = lib.tot_profit(g, True), lib.tot_profit(g, False)
            C.add(f"{lg} | OVER | every game", s, o)
            C.add(f"{lg} | UNDER | every game", s, u)
            a3, b3 = st[g["home"]][0], st[g["away"]][0]
            if a3 and b3:
                ao, bo = all(x == 1 for x in a3), all(x == 1 for x in b3)
                au, bu = all(x == -1 for x in a3), all(x == -1 for x in b3)
                if ao and bo:
                    C.add(f"{lg} | UNDER | both teams went OVER 3 straight", s, u)
                    C.add(f"{lg} | OVER | both teams went OVER 3 straight", s, o)
                elif ao or bo:
                    C.add(f"{lg} | UNDER | one team went OVER 3 straight", s, u)
                if au and bu:
                    C.add(f"{lg} | OVER | both teams went UNDER 3 straight", s, o)
                    C.add(f"{lg} | UNDER | both teams went UNDER 3 straight", s, u)
                elif au or bu:
                    C.add(f"{lg} | OVER | one team went UNDER 3 straight", s, o)
                net = sum(a3) + sum(b3)
                if net >= 4:
                    C.add(f"{lg} | UNDER | the two teams' last 3: 5+ of 6 over", s, u)
                if net <= -4:
                    C.add(f"{lg} | OVER | the two teams' last 3: 5+ of 6 under", s, o)
            a4, b4 = st[g["home"]][1], st[g["away"]][1]
            for t4 in (a4, b4):
                if t4 and all(x == 1 for x in t4):
                    C.add(f"{lg} | UNDER | a team went OVER 4 straight", s, u)
                if t4 and all(x == -1 for x in t4):
                    C.add(f"{lg} | OVER | a team went UNDER 4 straight", s, o)
            pts = g["hs"] + g["as"]
            r = 1 if pts > g["total"] else -1 if pts < g["total"] else 0
            hist[(s, g["home"])].append(r)
            hist[(s, g["away"])].append(r)

C.dump("s8", "THE OVER / UNDER STREAK, NBA (+ NHL second check), closing total + juice; train 2018-22, held 2023-26",
       TR, HE)
