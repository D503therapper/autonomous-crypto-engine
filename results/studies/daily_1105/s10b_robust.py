"""S10 (part B) - robustness of the two S10 cells: (1) the ROAD DOG in its first game back from a neutral site
(Nov-Dec) and (2) the HOME side's ATS after 2+ neutral games. Cuts: outside the built early road dog (the team's
games 1-3), by price band / spread band against the SAME band's control (last game not neutral), by days since the
event, December only."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402

fin = [g for g in lib.finals("ncaab") if g["stype"] == "2"]
allf = [g for g in lib.all_finals("ncaab") if g["stype"] == "2"]
tl = lib.team_log(allf)
C = lib.Cells()
for g in fin:
    if g["season"] < 2018 or int(g["start"][5:7]) not in (11, 12) or g["neutral"]:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        prev = [x for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"]]
        if not prev:
            continue
        back = prev[-1]["neutral"] and lib.days_between(prev[-1]["start"], g["start"]) <= 10
        if not back and prev[-1]["neutral"]:
            continue
        n_neu = 0
        for x in reversed(prev):
            if not x["neutral"]:
                break
            n_neu += 1
        grp = "BACK" if back else "ctrl"
        s = g["season"]
        gp = len(prev)
        oprev = lib.before(tl, opp, g["start"], 1)
        opp_neu = bool(oprev) and oprev[-1]["neutral"] and oprev[-1]["season"] == g["season"]
        if not home and lib.dog_band(o):
            p = lib.profit(won, lib.dec(o))
            C.add(f"(1) road dog {grp}", s, p)
            C.add(f"(1) road dog {grp} games 4+", s, p if gp >= 3 else None)
            for lo, hi in ((100, 150), (151, 250), (251, 350)):
                if lo <= o <= hi:
                    C.add(f"(1) road dog {grp} +{lo}..+{hi}", s, p)
            C.add(f"(1) road dog {grp} December", s, p if g["start"][5:7] == "12" else None)
            if back:
                d = lib.days_between(prev[-1]["start"], g["start"])
                C.add(f"(1) road dog BACK {'1-3 days' if d < 3.5 else '4-10 days'} after", s, p)
                C.add(f"(1) road dog BACK, home team ALSO back from neutral" if opp_neu else
                      "(1) road dog BACK, home team not", s, p)
                C.add(f"(1) road dog BACK after {'2+' if n_neu >= 2 else '1'} neutral", s, p)
        if home and g["sp"] is not None:
            a = lib.ats(g, side)
            sp = g["sp"]
            band = "home fav 12+" if sp <= -12 else "home fav 0.5-11.5" if sp < 0 else "home dog"
            k = "2+" if n_neu >= 2 else "1" if back else "ctrl"
            C.add(f"(2) home ATS {k} | {band}", s, a)
            C.add(f"(2) home ATS {k}", s, a)
            C.add(f"(2) home ATS {k} games 4+", s, a if gp >= 3 else None)
C.dump("s10b", "S10 robustness", (2018, 2022), [2023, 2024, 2025])
