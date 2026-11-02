"""11/2 #9 - COLLEGE HOOPS PREP: THE NOVEMBER LINE FOR TEAMS WITH BIG ROSTER TURNOVER (the portal era). The NBA version
(10/31, games 3-20) was dead; college rosters turn over far more. RETURNING SHARE = of a team's minutes in its games
so far this season (before tonight - no look-ahead), the share played by men who logged minutes for the SAME team last
season (box scores 2021-26). Games 2-8 of the season (November / early December). Cut in thirds within each season
(new-look / middle / same-old); also the turnover GAP between the two teams. Graded at the close: ATS, dogs +100..+350,
favorites -101..-150 / -151..-400. Train 2021-2022 seasons, held 2023 / 2024 / 2025 apart (box scores start 2021)."""
from lib import *

TRAIN, HELD = (2021, 2022), [2023, 2024, 2025]


def mins(st, r):
    try:
        return float(st.get("minutes") or 0)
    except ValueError:
        return None


box = boxes("ncaab", mins)
allg = all_finals("ncaab")
tl = team_log(allg)
# who played for whom, per season
played = {}
for g in allg:
    for tm, ps in (box.get(g["id"]) or {}).items():
        for pid, m in ps.items():
            if m and m > 0:
                played.setdefault((tm, g["season"]), set()).add(pid)


def returning_share(team, start, season):
    last = played.get((str(team), season - 1))
    if not last:
        return None, 0
    tot = ret = 0.0
    n = 0
    for x in before(tl, team, start):
        if x["season"] != season:
            continue
        b = (box.get(x["id"]) or {}).get(str(team))
        if not b:
            continue
        n += 1
        for pid, m in b.items():
            tot += m or 0
            if pid in last:
                ret += m or 0
    return (ret / tot if tot else None), n


rows = []
for g in finals("ncaab"):
    if g["stype"] != "2":
        continue
    s = g["season"]
    if s < 2021:
        continue
    r = {"g": g}
    ok = True
    for side in ("home", "away"):
        sh, n = returning_share(g[side], g["start"], s)
        gn = len([x for x in before(tl, g[side], g["start"]) if x["season"] == s])
        if sh is None or n < 1 or not 1 <= gn <= 7:
            ok = False
            break
        r[side] = sh
    if ok:
        rows.append(r)
# thirds within each season
cut = {}
for s in {r["g"]["season"] for r in rows}:
    v = sorted(x for r in rows if r["g"]["season"] == s for x in (r["home"], r["away"]))
    cut[s] = (v[len(v) // 3], v[2 * len(v) // 3])
print("games 2-8 with both shares:", len(rows), {s: tuple(round(x, 2) for x in v) for s, v in sorted(cut.items())})
c = Cells()
for r in rows:
    g = r["g"]
    s = g["season"]
    lo, hi = cut[s]
    for side, tm, opp, odds, won, home in sides(g):
        me, op = r[side], r["away" if home else "home"]
        k = "NEW-LOOK" if me < lo else "SAME-OLD" if me >= hi else "middle"
        p = profit(won, dec(odds))
        band = ("DOG" if dog_band(odds) else "FAV -101..-150" if -150 <= odds <= -101 else
                "FAV -151..-400" if -400 <= odds <= -151 else None)
        if band:
            c.add(f"{band} {k}", s, p)
        c.add(f"ATS {k}", s, ats(g, side))
        gap = me - op
        if gap <= -0.30:
            gk = "30+ pts LESS returning than the opponent"
            if band:
                c.add(f"{band} {gk}", s, p)
            c.add(f"ATS {gk}", s, ats(g, side))
c.dump("s9", "College hoops games 2-8: returning-minutes share (train 2021-22, held 2023-25 apart)", TRAIN, HELD)
