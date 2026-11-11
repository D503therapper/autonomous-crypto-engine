"""S6 (NHL) - THE TOP-HEAVY ICE TIME (never studied: the 11/3 lost man / 11/x ice-time leader OUT studies read one
man missing; the 11/10 top-heavy SCORING read goals; the 10/x b2b / 3-in-4 studies read the schedule, never who logs
the minutes).
TOP-4 SHARE = the share of the team's skater ice time logged by its 4 busiest skaters each game, season average before
tonight (10+ boxed games) - a coach leaning on 4 men (a thin roster) vs a team rolling 4 lines. And the HEAVY LAST
GAME: its ice-time leader logged 26+ minutes last game (OT / a chase / a short bench), crossed with tonight on the 2nd
night of a back-to-back.
Cuts from TRAIN quantiles (2016-21). Cells: favorite -101..-250 / dog +100..+350 at the close and at the paid NHL
game-day morning look (2021-23). TRAIN 2016-21, HELD 2022-25 apart, 2026 live."""
from collections import defaultdict

import lib

fin = [g for g in lib.finals("nhl") if g["stype"] == "2"]
allf = [g for g in lib.all_finals("nhl") if g["stype"] == "2"]
rows = lib.box_rows("nhl")
mo = lib.nhl_morning()
TRAIN, HELD = (2016, 2021), (2022, 2023, 2024, 2025, 2026)


def team_game(gid, team):
    rs = (rows.get(gid) or {}).get(team)
    if not rs:
        return None
    t = []
    for r in rs:
        if r.get("group") == "goalies" or r.get("pos") == "G" or "saves" in r["st"]:
            continue
        m = lib.toi(r["st"].get("timeOnIce"))
        if m:
            t.append(m)
    if len(t) < 15:
        return None
    t.sort(reverse=True)
    return sum(t[:4]) / sum(t), t[0]


run = defaultdict(lambda: [0, 0.0])
pre, last = {}, {}
lastmax = {}
for g in allf:
    for side in ("home", "away"):
        k = (g["season"], g[side])
        pre[(g["id"], side)] = tuple(run[k])
        last[(g["id"], side)] = lastmax.get(k)
    for side in ("home", "away"):
        x = team_game(g["id"], g[side])
        k = (g["season"], g[side])
        lastmax[k] = x[1] if x else None
        if not x:
            continue
        run[k][0] += 1
        run[k][1] += x[0]
tl = lib.team_log(allf)


def b2b(team, start):
    p = lib.before(tl, team, start, 1)
    return bool(p) and lib.days_between(p[-1]["start"], start) < 1.5


tr = []
for g in fin:
    if TRAIN[0] <= g["season"] <= TRAIN[1]:
        for side in ("home", "away"):
            n, s4 = pre.get((g["id"], side), (0, 0))
            if n >= 10:
                tr.append(s4 / n)
tr.sort()
q = {p: tr[int(len(tr) * p)] for p in (.1, .2, .5, .8, .9)}
print("train top-4 share quantiles", {p: round(v, 4) for p, v in q.items()}, "n", len(tr))

cells = lib.Cells()
for g in fin:
    for side, team, opp, o, won, home in lib.sides(g):
        n, s4 = pre.get((g["id"], side), (0, 0))
        lm = last.get((g["id"], side))
        labs = []
        if n >= 10:
            x = s4 / n
            if x >= q[.9]:
                labs.append("TOP-HEAVY ice time (top-4 share top 10%)")
            if x >= q[.8]:
                labs.append("TOP-HEAVY top 20%")
            if x <= q[.2]:
                labs.append("ROLLS 4 LINES (bottom 20%)")
            if q[.2] < x < q[.8]:
                labs.append("ICE control: middle 60%")
            if x >= q[.8] and b2b(team, g["start"]):
                labs.append("TOP-HEAVY top 20% x 2nd night of a b2b")
            if x <= q[.2] and b2b(team, g["start"]):
                labs.append("ROLLS 4 LINES x 2nd night of a b2b")
        if lm is not None:
            if lm >= 26:
                labs.append("HEAVY LAST GAME (leader 26+ min)")
                if b2b(team, g["start"]):
                    labs.append("HEAVY LAST GAME x 2nd night of a b2b")
            elif lm < 23:
                labs.append("light last game (leader under 23)")
        s = g["season"]
        pl = lib.profit(won, lib.dec(o))
        m = lib.morning_side(mo, g["id"], side) if mo else None
        for lab in labs:
            if -250 <= o <= -101:
                cells.add(f"{lab} | FAV ML", s, pl)
                if m and -250 <= m[0] <= -101:
                    cells.add(f"{lab} | FAV ML paid morning", s, lib.profit(won, m[1]))
            if lib.dog_band(o):
                cells.add(f"{lab} | DOG ML", s, pl)
                if m and lib.dog_band(m[0]):
                    cells.add(f"{lab} | DOG ML paid morning", s, lib.profit(won, m[1]))
cells.dump("s6", "S6 NHL - top-4 skater ice-time share (season avg, 10+ boxed games) and the heavy last game; close / paid "
           "morning; TRAIN 2016-21", TRAIN, HELD)
