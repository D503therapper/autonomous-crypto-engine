"""S3 - COLLEGE HOOPS: THE STAR OFF A DUD (the 11/8 NBA build's college twin - never studied in college hoops; the
11/4 expert knowledge read the star's 2nd game BACK from a miss and his absence, never his bad shooting night).
The star = the team's top scorer this season (points a game, 3+ games with the team, 13+ a game), 3+ team games before
tonight (week 2 counts); the dud = under 35% from the field on 12+ shots in the team's last game.
Cells: the dud team's side and the side ACROSS it (the NBA build fades the favorite across), as a favorite
-101..-250 / dog +100..+350 at the close and ATS, ESPN's open the second price; split early (games 4-8, where the
board is now) vs later. TRAIN 2021-22 (player boxes start 2021), HELD 2023 / 2024 / 2025, 2026 live."""
from collections import Counter

import lib

TRAIN, HELD = (2021, 2022), [2023, 2024, 2025, 2026]
C = lib.Cells()


def add_side(tag, g, side, o, won, s):
    p = lib.profit(won, lib.dec(o))
    if -250 <= o <= -101:
        C.add(f"{tag} | fav -101..-250", s, p)
    if 100 <= o <= 350:
        C.add(f"{tag} | dog +100..+350", s, p)
    C.add(f"{tag} | ATS", s, lib.ats(g, side))
    oo = g["oh"] if side == "home" else g["oa"]
    if oo:
        if -250 <= oo <= -101:
            C.add(f"{tag} | fav OPEN", s, lib.profit(won, lib.dec(oo)))
        if 100 <= oo <= 350:
            C.add(f"{tag} | dog OPEN", s, lib.profit(won, lib.dec(oo)))


def bare(x):
    return str(x).split(":")[-1]


def val(st, r):
    try:
        fgm, fga = [int(x) for x in str(st.get("fieldGoalsMade-fieldGoalsAttempted", "")).split("-")]
        return (int(st.get("points") or 0), fgm, fga)
    except (ValueError, TypeError):
        return None


bx = lib.boxes("ncaab", val)
by_tg = {}
for gid, teams in bx.items():
    for t, pl in teams.items():
        by_tg[(bare(gid), bare(t))] = pl
fin = [g for g in lib.finals("ncaab") if g["stype"] == "2" and g["season"] >= 2021]
tl = lib.team_log([g for g in lib.all_finals("ncaab") if g["stype"] == "2"])
n_dud = 0
for g in fin:
    for side, team, opp, o, won, home in lib.sides(g):
        prev = [x for x in lib.before(tl, team, g["start"]) if x["season"] == g["season"]]
        if len(prev) < 3:
            continue
        pts, gp = Counter(), Counter()
        for x in prev:
            for pid, v in (by_tg.get((bare(x["id"]), bare(team))) or {}).items():
                pts[pid] += v[0]
                gp[pid] += 1
        cand = [(pts[p] / gp[p], p) for p in pts if gp[p] >= 3]
        if not cand:
            continue
        ppg, star = max(cand)
        last = by_tg.get((bare(prev[-1]["id"]), bare(team))) or {}
        v = last.get(star)
        if not v or ppg < 13:
            continue
        _, fgm, fga = v
        stage = "games 4-8" if len(prev) <= 7 else "games 9+"
        oside = "away" if side == "home" else "home"
        oo = g["mla"] if side == "home" else g["mlh"]
        if fga >= 12 and fgm / fga < 0.35:
            n_dud += 1
            for st in ("all", stage):
                add_side(f"S3 [{st}] the star shot under 35% on 12+ last game", g, side, o, won, g["season"])
                add_side(f"S3x [{st}] facing a star off a dud", g, oside, oo, not won, g["season"])
            if fgm / fga < 0.30:
                add_side("S3 [all] ... under 30%", g, side, o, won, g["season"])
                add_side("S3x [all] facing ... under 30%", g, oside, oo, not won, g["season"])
            if not lib.won_g(prev[-1], team):
                add_side("S3x [all] facing a star off a dud AND a loss", g, oside, oo, not won, g["season"])
        elif fga >= 12 and fgm / fga >= 0.45:
            add_side(f"S3 [{stage}] control: the star shot 45%+ on 12+", g, side, o, won, g["season"])
            add_side(f"S3x [{stage}] control: facing a star off 45%+", g, oside, oo, not won, g["season"])
        else:
            add_side(f"S3x [{stage}] control: facing anything else", g, oside, oo, not won, g["season"])
print("dud sides", n_dud)
C.dump("s3", "S3 college hoops - the star (13+ ppg) off a dud (<35% on 12+); closing prices + ESPN's open; TRAIN 2021-22",
       TRAIN, HELD)
