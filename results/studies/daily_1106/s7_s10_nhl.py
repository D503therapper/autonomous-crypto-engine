"""S7 - NHL SCHEDULE DENSITY beyond the back-to-back: tonight is the team's 3rd game in 4 nights / 4th in 6 nights,
NOT the 2nd night of a back-to-back (the b2b read is built) - vs a rested opponent (1+ day off) and any opponent.
S10 - NHL: THE PROJECTED BACKUP, knowable at 8 AM (11/6 - the wired projected_starter): the side whose PROJECTION is
its backup (the #1 projected out: a b2b with the #1 in net last night) vs the side whose projection is its #1 - at
ESPN's OPEN (2023-26, the 8 AM stand-in) and the close. 11/5 study 3 read the ACTUAL switch (not knowable); this is the
version the morning board can use.
Regular season 2016-26, dogs +100..+350 / favorites -101..-150. Train 2016-22, held out 2023 / 2024 / 2025 / 2026."""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402
import sports_players as sp  # noqa: E402

allf = [g for g in lib.all_finals("nhl") if g["stype"] == "2"]
tl = lib.team_log(allf)
fin = [g for g in lib.finals("nhl") if g["stype"] == "2" and g["season"] >= 2016]
rows = [r for r in sp.load()["nhl"] if r.get("role") == "G"]
by_team = defaultdict(list)
for r in rows:
    by_team[r["team"]].append(r)
C = lib.Cells()


def dens(team, start):
    prev = lib.before(tl, team, start, 6)
    d = [lib.days_between(x["start"], start) for x in prev]
    b2b = bool(d) and d[-1] < 1.5
    in4 = 1 + sum(1 for x in d if x < 3.5)        # games in the 4 nights ending tonight
    in6 = 1 + sum(1 for x in d if x < 5.5)
    rest = d[-1] if d else 9
    return b2b, in4, in6, rest


for g in fin:
    for side, team, opp, o_close, won, home in lib.sides(g):
        s = g["season"]
        o_open = g["oh"] if side == "home" else g["oa"]
        b2b, in4, in6, rest = dens(team, g["start"])
        ob2b, oin4, oin6, orest = dens(opp, g["start"])
        cells = []
        if not b2b:
            if in4 >= 3:
                cells.append("S7 3rd in 4 nights, not a b2b")
                if orest >= 1.5 and not ob2b:
                    cells.append("S7 3rd in 4 nights, not a b2b, vs a rested opponent")
            if in6 >= 4:
                cells.append("S7 4th in 6 nights, not a b2b")
            if in4 <= 2 and in6 <= 3:
                cells.append("S7 control: not a b2b, not dense")
        # S10
        trows = [r for r in by_team[team] if r["start"] < g["start"]]
        proj = sp.projected_starter(trows, team, g["start"])
        last = sp.last_starter(trows, team, g["start"])
        if proj and last:
            y, m = int(g["start"][:4]), int(g["start"][5:7])
            floor = f"{y if m >= 9 else y - 1}-09-01"
            seq = [r["player"] for r in trows if r["start"] >= floor][-10:]
            if len(seq) >= 6:
                n1, c1 = Counter(seq).most_common(1)[0]
                tag = "projected the #1" if proj == n1 else "projected a BACKUP"
                cells.append(f"S10 {tag}{' (b2b)' if b2b else ' (rested)'}")
                if proj != n1 and b2b:
                    oseq = None
                cells.append(f"S10 {tag}")
        for c in cells:
            if lib.dog_band(o_close):
                C.add(f"{c} | close dog", s, lib.profit(won, lib.dec(o_close)))
            if lib.fav_band(o_close):
                C.add(f"{c} | close fav", s, lib.profit(won, lib.dec(o_close)))
            if o_open and s >= 2023 and lib.dog_band(o_open):
                C.add(f"{c} | OPEN dog", s, lib.profit(won, lib.dec(o_open)))
            if o_open and s >= 2023 and lib.fav_band(o_open):
                C.add(f"{c} | OPEN fav", s, lib.profit(won, lib.dec(o_open)))
C.dump("s7_s10", "S7 NHL density (not a b2b) / S10 the projected backup (knowable at 8 AM)", (2016, 2022), [2023, 2024, 2025, 2026])
