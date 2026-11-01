"""Study 2 (11/1): NFL DIVISION GAMES LATE IN THE SEASON (the owner's example list). The "division games get tight and
go under late in the year" idea. A division pair = two teams that met twice in that regular season (the schedule is
known before the season). LATE = games from November 15 on (weeks ~11-18), EARLY = before. Cells: the division dog
+100..+350 / favorite -101..-150 (closing ML and the FIRST FAIR early number), the dog ATS, and the UNDER at the closing
total with its juice - each against the same cell in non-division games, so the base is the right one. Second check:
December-January only, and the dog getting 3+ points. Train 2018-23, held out 2024 / 2025 / 2026 apart."""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TR, HE = (2018, 2023), (2024, 2025, 2026)
allf = [g for g in lib.all_finals("nfl") if g["stype"] == "2"]
meet = Counter()
for g in lib.sd.load_games("nfl").values():          # the full regular-season schedule (finished or not)
    if g.get("league") != "nfl" or str(g.get("stype") or "2") != "2" or not g.get("start"):
        continue
    meet[(lib.season(g["start"]), frozenset((g["home"], g["away"])))] += 1
xby = {x["id"]: x for x in lib.load_football("nfl")}
C = lib.Cells()
for g in lib.finals("nfl"):
    if g["stype"] != "2" or g["neutral"]:
        continue
    s = g["season"]
    div = meet[(s, frozenset((g["home"], g["away"])))] >= 2
    md = g["start"][5:10]
    late = md >= "11-15" or md < "03-01"
    dec_jan = md >= "12-01" or md < "03-01"
    when = ["late (Nov 15+)" if late else "early (before Nov 15)"] + (["Dec-Jan"] if dec_jan else [])
    kind = "division" if div else "non-division"
    for w in when:
        tag = f"{kind} | {w}"
        C.add(f"UNDER | {tag}", s, lib.tot_profit(g, False))
        if g["total"] is not None and g["total"] <= 42:
            C.add(f"UNDER | {tag} | total 42 or less", s, lib.tot_profit(g, False))
        for side, team, opp, o, won, home in lib.sides(g):
            pr = lib.profit(won, lib.dec(o))
            e = lib.early_price(xby, g["id"], side)
            if lib.dog_band(o):
                C.add(f"dog +100..+350 | {tag}", s, pr)
                C.add(f"dog +100..+350 | {tag} | {'home' if home else 'road'}", s, pr)
                if e and 100 <= e[0] <= 350:
                    C.add(f"dog +100..+350 | {tag} | FIRST FAIR", s, lib.profit(won, e[1]))
                C.add(f"ATS dog | {tag}", s, lib.ats(g, side))
                sp = g["sp"] if home else (-g["sp"] if g["sp"] is not None else None)
                if sp is not None and sp >= 3:
                    C.add(f"ATS dog getting 3+ | {tag}", s, lib.ats(g, side))
            elif -150 <= o <= -101:
                C.add(f"fav -101..-150 | {tag}", s, pr)
                if e and -150 <= e[0] <= -101:
                    C.add(f"fav -101..-150 | {tag} | FIRST FAIR", s, lib.profit(won, e[1]))

C.dump("s2", "NFL DIVISION GAMES LATE IN THE SEASON (closing prices unless FIRST FAIR; train 2018-23, held 2024/25/26)",
       TR, HE)
