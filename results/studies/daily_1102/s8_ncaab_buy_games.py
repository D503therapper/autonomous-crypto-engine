"""11/2 #8 - COLLEGE HOOPS PREP: THE EARLY-SEASON "BUY GAME" (a big program pays a small school to come lose at its gym).
No conference field on file, so a buy game = a HOME (not neutral) favorite of 12+ points from the season's first games
to Dec 20 (the non-conference window); the same spread sizes in conference season (Jan+) are the base. Graded at the
close: the favorite ATS by size (12-16.5 / 17-21.5 / 22+), the team's game number (1-3 / 4+), the total (over / under),
and whether the favorite covered its LAST buy game (a 'they run it up' read). Train 2016-2021 seasons, held 2022 / 2023
/ 2024 / 2025 apart (the 2025-26 season = held; 11/3 opens 2026-27)."""
from lib import *

TRAIN, HELD = (2016, 2021), [2022, 2023, 2024, 2025]


def size(a):
    return "12-16.5" if a < 17 else "17-21.5" if a < 22 else "22+"


c = Cells()
allg = all_finals("ncaab")
tl = team_log(allg)
last_buy_cover = {}
n = 0
for g in sorted(finals("ncaab"), key=lambda x: x["start"]):
    if g["stype"] != "2" or g["sp"] is None or g["neutral"]:
        continue
    if g["sp"] > -12:
        continue                                     # home favorites of 12+ only
    s = g["season"]
    m, d = int(g["start"][5:7]), int(g["start"][8:10])
    window = "Nov-Dec20" if (m == 11 or (m == 12 and d <= 20)) else ("Jan+" if m in (1, 2, 3) else None)
    if not window:
        continue
    a = abs(g["sp"])
    sz = size(a)
    pf = ats(g, "home")
    if pf is None:
        continue
    n += 1
    gn = len([x for x in before(tl, g["home"], g["start"]) if x["season"] == s])
    c.add(f"{window} home fav {sz} ATS", s, pf)
    c.add(f"{window} home fav 12+ ATS", s, pf)
    c.add(f"{window} home fav 12+ OVER", s, tot_profit(g, True))
    c.add(f"{window} home fav 12+ UNDER", s, tot_profit(g, False))
    c.add(f"{window} home fav {sz} UNDER", s, tot_profit(g, False))
    if window == "Nov-Dec20":
        c.add(f"buy game ATS team game {'1-3' if gn < 3 else '4+'}", s, pf)
        lb = last_buy_cover.get((g["home"], s))
        if lb is not None:
            c.add(f"buy game ATS, covered its last buy game {'YES' if lb else 'NO'}", s, pf)
        last_buy_cover[(g["home"], s)] = pf > 0
print("home favorites 12+:", n)
c.dump("s8", "College hoops buy games: home favorites 12+ before Dec 20 vs Jan+ (train 2016-21, held 2022-25 apart)",
       TRAIN, HELD)
