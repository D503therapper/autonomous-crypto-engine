"""11/24 - S9d: IS THE DEEP-TEAM-ON-ITS-SECOND-DAY CELL REAL? The check that has to pass before a weight: is the
"game the day before" a real earlier game, or the SAME game on file twice (an event's placeholder row and its real
row, a day apart)? A twin would put tonight's own box score into the team's minutes before the game is read - a
blowout loser empties its bench, reads "deep", and has already failed to cover.
python results/studies/daily_1124/s9d_check.py"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import h  # noqa: E402
import s_follow as F  # noqa: E402

read, fin = F.depth_reads()
allf = [g for g in lib.all_finals("ncaab") if g["season"] >= 2021]
tl = lib.team_log(allf)
O = h.Out("s9d_check", (2021, 2023), [2024, 2025, 2026])
O.p("S9d - THE DEEP TEAM ON ITS SECOND DAY: is yesterday's game a real game?")
n = twin = 0
shown = 0
for g in fin:
    for side, team, opp, o, won, _ in lib.sides(g):
        me = read.get((g["id"], team))
        if not me or me[2] > 1.3:
            continue
        pv = lib.before(tl, team, g["start"], 1)
        if not pv:
            continue
        p = pv[0]
        same_opp = opp in (p["home"], p["away"])
        my = (g["hs"], g["as"]) if side == "home" else (g["as"], g["hs"])
        pm = (p["hs"], p["as"]) if p["home"] == team else (p["as"], p["hs"])
        is_twin = same_opp and my == pm
        at = lib.ats(g, side)
        deep = me[1] <= 0.2
        n += 1
        twin += is_twin
        O.add(f"second day, {'yesterday is the SAME game on file twice' if is_twin else 'same opponent, another score' if same_opp else 'a real earlier game (another opponent)'}: ATS", g["season"], at)
        if deep:
            O.add(f"DEEP second day, {'yesterday is the SAME game on file twice' if is_twin else 'same opponent, another score' if same_opp else 'a real earlier game (another opponent)'}: ATS", g["season"], at)
            if is_twin and shown < 6:
                shown += 1
                O.p(f"   twin: {g['id']} {g['start']} vs {p['id']} {p['start']}  score {my} / {pm}")
O.p(f"second-day sides read: {n}; the day-before game is the same game twice: {twin}")
O.show()
O.save()
