"""Study 9 (11/1): COLLEGE HOOPS PREP - THE EARLY-SEASON TOURNAMENT BACK-TO-BACK. November / December feast-week
events (Maui, Battle 4 Atlantis, the Thanksgiving fields) play 2-3 games on consecutive days at a neutral site - the only
time most college teams play on no rest. Cells (Nov 1 - Dec 31, neutral site, both teams' previous games on file):
the side on its 2nd game in 2 days vs a team that is NOT (rested), both on a back-to-back, the 3rd game in 3 days;
the side's previous game went to overtime / was a 15+ point loss (the consolation-bracket letdown). Bet the moneyline
(dog +100..+350, favorite -101..-150 / -151..-300) and ATS at the close, and the total (tired legs - the under?).
College hoops has no live season yet (opens 11/3), so check 4 is n/a. Train 2018-21, held out 2022 / 2023 / 2024 /
2025 apart."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TR, HE = (2018, 2021), (2022, 2023, 2024, 2025)
allf = [g for g in lib.all_finals("ncaab") if g["stype"] == "2"]
tl = lib.team_log(allf)
C = lib.Cells()
for g in lib.finals("ncaab"):
    if g["stype"] != "2":
        continue
    md = g["start"][5:7]
    if md not in ("11", "12"):
        continue
    s = g["season"]
    rest = {}
    lastg = {}
    for t in (g["home"], g["away"]):
        L = lib.before(tl, t, g["start"], 2)
        if not L or L[-1]["season"] != s:
            rest[t] = None
            continue
        rest[t] = lib.days_between(L[-1]["start"], g["start"])
        lastg[t] = L
    if rest[g["home"]] is None or rest[g["away"]] is None:
        continue
    neutral = g["neutral"]
    site = "neutral" if neutral else "true road / home"
    for side, team, opp, o, won, home in lib.sides(g):
        r, ro = rest[team], rest[opp]
        b2b, ob2b = r <= 1.4, ro <= 1.4
        tags = []
        if b2b and not ob2b:
            tags.append(f"{site} | 2nd day in a row vs a RESTED team (2+ days)")
        if b2b and ob2b:
            tags.append(f"{site} | both on a back-to-back")
        if b2b:
            L = lastg[team]
            if len(L) == 2 and lib.days_between(L[0]["start"], g["start"]) <= 2.6:
                tags.append(f"{site} | 3rd game in 3 days")
            if lib.margin_g(L[-1], team) <= -15:
                tags.append(f"{site} | back-to-back after a 15+ loss")
            if ob2b and lib.margin_g(lastg[opp][-1], opp) <= -15 and lib.margin_g(L[-1], team) > 0:
                tags.append(f"{site} | b2b, won yesterday vs a team that lost by 15+ yesterday")
        if not b2b and ob2b:
            tags.append(f"{site} | RESTED vs a team on the 2nd day in a row")
        if not tags:
            continue
        pr = lib.profit(won, lib.dec(o))
        band = "dog +100..+350" if lib.dog_band(o) else "fav -101..-150" if -150 <= o <= -101 else \
            "fav -151..-300" if -300 <= o < -150 else None
        for t in tags:
            if band:
                C.add(f"{band} | {t}", s, pr)
            C.add(f"ATS | {t}", s, lib.ats(g, side))
    if rest[g["home"]] <= 1.4 and rest[g["away"]] <= 1.4:
        C.add(f"UNDER | {site} | both on a back-to-back", s, lib.tot_profit(g, False))
    elif rest[g["home"]] <= 1.4 or rest[g["away"]] <= 1.4:
        C.add(f"UNDER | {site} | one team on a back-to-back", s, lib.tot_profit(g, False))
    else:
        C.add(f"UNDER | {site} | neither on a back-to-back", s, lib.tot_profit(g, False))

C.dump("s9", "COLLEGE HOOPS EARLY-SEASON TOURNAMENT BACK-TO-BACK (Nov-Dec; closing prices; train 2018-21, held "
       "2022-25)", TR, HE)
