"""S10 (part B) - the S10 cell made exact and checked: an NHL side on a RESTED night (not the 2nd of a b2b) whose #1
(sports_goalies.number_one - most starts in the last 10 this season, 6+ held, a clear leader) did NOT start either of the
team's last 2 games (hurt / benched - knowable at 8 AM from box scores). Dogs +100..+350 / favorites -101..-150 at the
close and ESPN's open; splits: sat exactly 2 vs 3+, and (diagnostic only - not knowable at 8 AM) whether the #1 came
back tonight. Train 2016-22, held out 2023-26 apart."""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402
import sports_players as sp  # noqa: E402
import sports_goalies as sg  # noqa: E402

allf = [g for g in lib.all_finals("nhl") if g["stype"] == "2"]
tl = lib.team_log(allf)
fin = [g for g in lib.finals("nhl") if g["stype"] == "2" and g["season"] >= 2016]
rows = [r for r in sp.load()["nhl"] if r.get("role") == "G"]
act = {(r["gid"], r["team"]): r["player"] for r in rows}
by_team = defaultdict(list)
for r in rows:
    by_team[r["team"]].append(r)
C = lib.Cells()
for g in fin:
    for side, team, opp, o_close, won, home in lib.sides(g):
        prev = lib.before(tl, team, g["start"], 1)
        if not prev or lib.days_between(prev[-1]["start"], g["start"]) < 1.5:
            continue
        trows = [r for r in by_team[team] if r["start"] < g["start"]]
        n1 = sg.number_one(trows, team, g["start"])
        if not n1:
            continue
        seq = [r["player"] for r in reversed(trows) if r["start"] >= sg.season_start(g["start"])]
        sat = 0
        for p in seq:
            if p == n1[0]:
                break
            sat += 1
        s = g["season"]
        o_open = g["oh"] if side == "home" else g["oa"]
        cells = []
        if sat >= 2:
            cells += ["the #1 SAT the last 2+", f"the #1 sat {'exactly 2' if sat == 2 else '3+'}",
                      "the #1 sat 2+ | (diag) he started tonight" if act.get((g["id"], team)) == n1[0] else
                      "the #1 sat 2+ | (diag) he sat again"]
            ob = sg.number_one([r for r in by_team[opp] if r["start"] < g["start"]], opp, g["start"])
            cells.append("the #1 sat 2+ | vs an opponent with a #1" if ob else "the #1 sat 2+ | opponent no clear #1")
        elif sat == 1:
            cells.append("control: the #1 sat only the last game")
        else:
            cells.append("control: the #1 started the last game")
        for c in cells:
            if lib.dog_band(o_close):
                C.add(f"{c} | close dog", s, lib.profit(won, lib.dec(o_close)))
            if lib.fav_band(o_close):
                C.add(f"{c} | close fav", s, lib.profit(won, lib.dec(o_close)))
            if lib.dog_band(o_close) or lib.fav_band(o_close):
                C.add(f"{c} | close dog+fav", s, lib.profit(won, lib.dec(o_close)))
            if o_open and s >= 2023 and lib.dog_band(o_open):
                C.add(f"{c} | OPEN dog", s, lib.profit(won, lib.dec(o_open)))
            if o_open and s >= 2023 and lib.fav_band(o_open):
                C.add(f"{c} | OPEN fav", s, lib.profit(won, lib.dec(o_open)))
C.dump("s10b", "S10b NHL: the side whose #1 sat the last 2+ games, on a rested night", (2016, 2022), [2023, 2024, 2025, 2026])
