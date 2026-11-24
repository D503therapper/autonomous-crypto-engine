"""11/24 - S9e: THE ENGINE'S OWN READ of the deep team on its second day (sports_ncaab_roster.deep_second_day - every
boxed game before the tip, the league's bottom-fifth cut that morning) on every priced game 2021-26: does the function
the board will call find the study's cell?
python results/studies/daily_1124/s9e_engine_read.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import sports_data as sd  # noqa: E402
import sports_ncaab_roster as nr  # noqa: E402

games = sd.load_games("ncaab")
fin = [g for g in lib.finals("ncaab") if g["stype"] == "2" and g["season"] >= 2021]
O = h.Out("s9e_engine_read", (2021, 2023), [2024, 2025, 2026])
O.p("S9e - THE ENGINE'S READ (sports_ncaab_roster.deep_second_day) on every priced game 2021-26, ATS at the close")
for g in fin:
    r = {s_: nr.deep_second_day(games, g[s_], g["start"]) for s_ in ("home", "away")}
    for side, team, opp, o, won, _ in lib.sides(g):
        me, th = r[side], r["away" if side == "home" else "home"]
        at = lib.ats(g, side)
        if me is True and th is not True:
            O.add("the deep team on its second day (the engine's read): ATS", g["season"], at)
            if 100 <= o <= 350:
                O.add("the deep team on its second day (the engine's read): dog +100..+350", g["season"], lib.profit(won, lib.dec(o)), o)
        if th is True and me is not True:
            O.add("ACROSS it (the engine's read): ATS", g["season"], at)
        if me is True and th is True:
            O.add("both deep, both on the second day (no weight): ATS", g["season"], at)
O.show()
O.save()
