"""S8 (NBA) - THE ASSIST RATE, and S10 = X2 (a RE-CUT, not counted as new: the 10/23 NBA benches study read fatigue x depth, b2b / 3-in-4, dead blind) - THE TIGHT ROTATION (never run in the NBA: the 11/3 college hoops
style study read assist share / bench share / the top-5 minutes share x schedule density on the COLLEGE box - S8 / S10
are the NBA twins; the NBA's style studies read pace, offensive rebounds, turnovers, threes, never assists or minutes).
ASSIST RATE = assists / field goals made, season to date before tonight (10+ boxed games): the ball-movement team the
TV crowd loves - is it over- or under-priced?
TIGHT ROTATION = the share of the team's minutes played by its 5 busiest men each game, season average (10+ games):
a team leaning on five men - does it fade, and worst on the 2nd night of a back-to-back / 3 games in 4 nights?
Cuts from the TRAIN quantiles (2016-22). Cells: favorite -101..-250 / dog +100..+350 at the close, ATS at the close,
ESPN's open (2023-26) and the paid NBA game-day morning look (2020-23) as second prices.
TRAIN 2016-22, HELD 2023 / 2024 / 2025 apart, 2026 live."""
from collections import defaultdict

import lib

fin = [g for g in lib.finals("nba") if g["stype"] == "2"]
allf = [g for g in lib.all_finals("nba") if g["stype"] == "2"]
rows = lib.box_rows("nba")
mo = lib.nba_morning()
TRAIN, HELD = (2016, 2022), (2023, 2024, 2025, 2026)


def split(s):
    try:
        a, b = str(s).split("-")
        return int(a), int(b)
    except (ValueError, AttributeError):
        return None


def team_game(gid, team):
    rs = (rows.get(gid) or {}).get(team)
    if not rs:
        return None
    ast = fgm = 0
    mins = []
    for r in rs:
        st = r["st"]
        fg = split(st.get("fieldGoalsMade-fieldGoalsAttempted"))
        if fg:
            fgm += fg[0]
        ast += lib.num(st.get("assists")) or 0
        m = lib.num(st.get("minutes"))
        if m:
            mins.append(m)
    if fgm <= 0 or len(mins) < 7:
        return None
    mins.sort(reverse=True)
    tot = sum(mins)
    return ast, fgm, (sum(mins[:5]) / tot if tot > 0 else None)


run = defaultdict(lambda: [0, 0.0, 0.0, 0.0])          # (season, team) -> n, ast, fgm, top5 share sum
pre = {}
for g in allf:
    for side in ("home", "away"):
        pre[(g["id"], side)] = tuple(run[(g["season"], g[side])])
    for side in ("home", "away"):
        t = team_game(g["id"], g[side])
        if not t or t[2] is None:
            continue
        r = run[(g["season"], g[side])]
        r[0] += 1
        r[1] += t[0]
        r[2] += t[1]
        r[3] += t[2]
tl = lib.team_log(allf)


def feats(gid, side):
    n, a, f, t5 = pre.get((gid, side), (0, 0, 0, 0))
    if n < 10 or f <= 0:
        return None
    return {"ast": a / f, "top5": t5 / n}


def density(team, start):
    prev = lib.before(tl, team, start, 3)
    if not prev:
        return "rested"
    d1 = lib.days_between(prev[-1]["start"], start)
    if d1 < 1.5:
        return "b2b"
    if len(prev) >= 2 and lib.days_between(prev[-2]["start"], start) < 3.5:
        return "3in4"
    return "rested"


tr = {"ast": [], "top5": []}
for g in fin:
    if TRAIN[0] <= g["season"] <= TRAIN[1]:
        for side in ("home", "away"):
            f = feats(g["id"], side)
            if f:
                for k in tr:
                    tr[k].append(f[k])
for k in tr:
    tr[k].sort()
q = {k: {p: tr[k][int(len(tr[k]) * p)] for p in (.1, .2, .5, .8, .9)} for k in tr}
print("train quantiles", {k: {p: round(v, 3) for p, v in d.items()} for k, d in q.items()})

c8, c10 = lib.Cells(), lib.Cells()
for g in fin:
    F = {s: feats(g["id"], s) for s in ("home", "away")}
    if not F["home"] or not F["away"]:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        me, op = F[side], F["away" if home else "home"]
        s = g["season"]
        pl = lib.profit(won, lib.dec(o))
        a = lib.ats(g, side)
        oo = g["oh"] if home else g["oa"]
        m = lib.morning_side(mo, g["id"], side) if mo else None
        dens = density(team, g["start"])

        def add(cells, lab):
            if -250 <= o <= -101:
                cells.add(f"{lab} | FAV ML", s, pl)
                if oo and -250 <= oo <= -101:
                    cells.add(f"{lab} | FAV ML ESPN open", s, lib.profit(won, lib.dec(oo)))
                if m and -250 <= m[0] <= -101:
                    cells.add(f"{lab} | FAV ML paid morning", s, lib.profit(won, m[1]))
            if lib.dog_band(o):
                cells.add(f"{lab} | DOG ML", s, pl)
                if oo and lib.dog_band(oo):
                    cells.add(f"{lab} | DOG ML ESPN open", s, lib.profit(won, lib.dec(oo)))
                if m and lib.dog_band(m[0]):
                    cells.add(f"{lab} | DOG ML paid morning", s, lib.profit(won, m[1]))
            cells.add(f"{lab} | ATS", s, a)

        x = me["ast"]
        if x >= q["ast"][.9]:
            add(c8, "ASSIST rate top 10%")
        if x >= q["ast"][.8]:
            add(c8, "ASSIST rate top 20%")
        if x <= q["ast"][.2]:
            add(c8, "ASSIST rate bottom 20% (iso-heavy)")
        if x <= q["ast"][.1]:
            add(c8, "ASSIST rate bottom 10%")
        if q["ast"][.2] < x < q["ast"][.8]:
            add(c8, "ASSIST control: middle 60%")
        if x - op["ast"] >= q["ast"][.8] - q["ast"][.2]:
            add(c8, "ASSIST gap vs the opponent (20-80 wide)+")
        y = me["top5"]
        labs = []
        if y >= q["top5"][.8]:
            labs.append("TIGHT rotation (top-5 share top 20%)")
        if y >= q["top5"][.9]:
            labs.append("TIGHT rotation top 10%")
        if y <= q["top5"][.2]:
            labs.append("DEEP rotation (bottom 20%)")
        if q["top5"][.2] < y < q["top5"][.8]:
            labs.append("ROTATION control: middle 60%")
        for lab in labs:
            add(c10, lab)
            add(c10, f"{lab} x {dens}")
c8.dump("s8", "S8 NBA - assist rate (AST / FGM) season to date, 10+ boxed games; close / ATS / ESPN open / paid morning; "
        "TRAIN 2016-22", TRAIN, HELD)
c10.dump("s10", "S10 NBA - the tight rotation (top-5 minutes share, season avg) x schedule density; close / ATS / ESPN open "
         "/ paid morning; TRAIN 2016-22", TRAIN, HELD)
