"""Study 9b (11/1): robustness of study 9's lead - the college hoops side playing the DAY AFTER a blowout loss
(the early-season tournament consolation game). Dose by yesterday's margin (lost by 1-9 / 10-14 / 15-19 / 20+, and
won), neutral vs not, Nov vs Dec, the opponent rested or not; moneyline (every price -400..+350 and the bands) and ATS
at the close. Train 2018-21, held out 2022-25 apart."""
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
    for side, team, opp, o, won, home in lib.sides(g):
        L = lib.before(tl, team, g["start"], 1)
        if not L or L[0]["season"] != s or lib.days_between(L[0]["start"], g["start"]) > 1.4:
            continue
        m = lib.margin_g(L[0], team)
        d = "won yesterday" if m > 0 else "lost by 1-9" if m > -10 else "lost by 10-14" if m > -15 else \
            "lost by 15-19" if m > -20 else "lost by 20+"
        tags = [d]
        if m <= -15:
            tags += ["lost by 15+ | " + ("neutral" if g["neutral"] else "home / road"),
                     "lost by 15+ | " + ("Nov" if g["start"][5:7] == "11" else "Dec")]
            OL = lib.before(tl, opp, g["start"], 1)
            orest = lib.days_between(OL[0]["start"], g["start"]) if OL and OL[0]["season"] == s else 9
            tags.append("lost by 15+ | opponent " + ("also on a b2b" if orest <= 1.4 else "rested"))
        pr = lib.profit(won, lib.dec(o))
        for t in tags:
            C.add(f"ATS | {t}", s, lib.ats(g, side))
            if -400 <= o <= 350:
                C.add(f"ML -400..+350 | {t}", s, pr)
            if lib.dog_band(o):
                C.add(f"dog +100..+350 | {t}", s, pr)
            elif -400 <= o <= -101:
                C.add(f"fav -101..-400 | {t}", s, pr)

C.dump("s9b", "COLLEGE HOOPS: THE DAY AFTER A BLOWOUT LOSS (Nov-Dec back-to-backs) - dose (closing prices; train "
       "2018-21, held 2022-25)", TR, HE)
