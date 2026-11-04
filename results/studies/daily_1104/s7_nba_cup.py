"""s7 - NBA CUP GROUP-PLAY NIGHTS (the in-season tournament, from 2023-24: every game on a designated night is a
group game - money and a trip to Las Vegas on the line, the courts painted). Nights (ET dates; the two first seasons
are documented, 2025-26's from the published schedule - a WATCH if the list is off): 2023 Nov 3 / 10 / 14 / 17 / 21 /
24 / 28; 2024 Nov 12 / 15 / 19 / 22 / 26 / 29 / Dec 3; 2025 Oct 31 / Nov 7 / 14 / 21 / 25 / 26 / 28. Cells: Cup
nights vs the other nights of the same window (Oct 31 - Dec 3) in the Cup seasons, and the same Tue / Fri window
2018-22 before the Cup existed: dogs +100..+350, home / road, favorites, ATS, the over. Train = 2023 + 2024, held
2025 (no 2026 list yet)."""
import lib
from datetime import timedelta

C = lib.Cells()
CUP = {2023: {"11-03", "11-10", "11-14", "11-17", "11-21", "11-24", "11-28"},
       2024: {"11-12", "11-15", "11-19", "11-22", "11-26", "11-29", "12-03"},
       2025: {"10-31", "11-07", "11-14", "11-21", "11-25", "11-26", "11-28"}}
fin = lib.finals("nba")
mo = lib.nba_morning()
for g in fin:
    if g["stype"] != "2":
        continue
    s = g["season"]
    et = (lib._t(g["start"]) - timedelta(hours=5)).strftime("%m-%d")
    if not ("10-31" <= et <= "12-03"):
        continue
    wd = (lib._t(g["start"]) - timedelta(hours=5)).weekday()
    if s in CUP:
        tag = "CUP night" if et in CUP[s] else "same window, other night"
    elif 2018 <= s <= 2022 and wd in (1, 4):
        tag = "pre-Cup Tue/Fri 2018-22"
    else:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        p = lib.profit(won, lib.dec(o))
        a = lib.ats(g, side)
        hr = "home" if home else "road"
        C.add(f"{tag} {hr} ATS", s, a)
        C.add(f"{tag} {hr} ML any", s, p)
        if lib.dog_band(o):
            C.add(f"{tag} dog +100..+350", s, p)
            C.add(f"{tag} {hr} dog +100..+350", s, p)
            if o >= 200:
                C.add(f"{tag} dog +200..+350", s, p)
        if lib.fav_band(o):
            C.add(f"{tag} fav -101..-150", s, p)
        if -300 <= o <= -151:
            C.add(f"{tag} fav -151..-300", s, p)
        if g["sp"] is not None:
            my = g["sp"] if home else -g["sp"]
            if my <= -7:
                C.add(f"{tag} ATS laying 7+", s, a)
            if my >= 7:
                C.add(f"{tag} ATS getting 7+", s, a)
    C.add(f"{tag} over", s, lib.tot_profit(g, True))
    C.add(f"{tag} under", s, lib.tot_profit(g, False))

C.dump("s7", "s7 NBA CUP GROUP-PLAY NIGHTS vs the other nights of the window (Oct 31 - Dec 3) - train 2023 + 2024, held 2025 "
       "(the 2018-22 Tue/Fri rows = the window before the Cup existed)", (2023, 2024), [2025, 2018, 2019, 2020, 2021, 2022])
