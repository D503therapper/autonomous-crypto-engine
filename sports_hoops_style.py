"""🏀 HOOPS "WIN INSIDE" FAVORITES (10/1 styles round 2, NBA + college hoops 2023-25, closing prices, vs the same
season / side / price band): a favorite that crashes the offensive glass (top third, offensive rebounds per shot) - or,
in college, takes few 3s (bottom third of 3-point rate) - beat its price band 3 of 3 seasons under every cutoff tried
(+3 to +7 pts); a college favorite facing a top-third offensive-rebounding team did worse (the mirror). A LEAD (best z
2.7 of 120 tests): +1 win-% point on such a favorite's read (sports.weigh_hoops_inside), never a trigger. Each team's
style comes from its EARLIER games this season only (no look-ahead); thirds are cut across the league's teams today."""
from datetime import datetime

MIN_G = {"nba": 10, "ncaab": 8}
_CACHE = {}


def _n(v, k=None):
    try:
        v = str(v)
        return float(v.split("-")[k]) if k is not None else float(v)
    except (ValueError, IndexError):
        return None


def states(lg, now_iso, rows=None, games=None):
    """{team id: {"3pt": rate, "oreb": per shot, "n": games}} this season so far, plus the thirds cutoffs."""
    key = (lg, now_iso[:10])
    if key in _CACHE:
        return _CACHE[key]
    if rows is None:
        import sports_roster as sr
        try:
            rows = sr.team_rows(lg)
        except Exception:                                    # noqa: BLE001
            rows = []
    y, mo = int(now_iso[:4]), int(now_iso[5:7])
    season0 = f"{y if mo >= 7 else y - 1}-07-01"
    acc = {}
    for r in rows:
        st_ = r.get("start") or ""
        if not (season0 <= st_ < now_iso):
            continue
        for tid, s in (r.get("teams") or {}).items():
            fga = _n(s.get("fieldGoalsMade-fieldGoalsAttempted"), 1)
            tpa = _n(s.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"), 1)
            orb = _n(s.get("offensiveRebounds"))
            if not fga or tpa is None or orb is None:
                continue
            a = acc.setdefault(str(tid), [0.0, 0.0, 0])
            a[0] += tpa / fga
            a[1] += orb / fga
            a[2] += 1
    teams = {t: {"3pt": a[0] / a[2], "oreb": a[1] / a[2], "n": a[2]} for t, a in acc.items() if a[2] >= MIN_G.get(lg, 8)}
    cut = {}
    if len(teams) >= 9:
        t3 = sorted(v["3pt"] for v in teams.values())
        ob = sorted(v["oreb"] for v in teams.values())
        cut = {"3pt_low": t3[len(t3) // 3], "oreb_high": ob[(2 * len(ob)) // 3]}
    out = {"teams": teams, "cut": cut}
    _CACHE[key] = out
    return out


def inside(st, lg, me, them):
    """+1 when this favorite wins inside (and, in college, isn't facing a glass-crashing team); else 0."""
    t, c = st.get("teams") or {}, st.get("cut") or {}
    a, b = t.get(str(me)), t.get(str(them))
    if not a or not c:
        return 0
    good = a["oreb"] >= c["oreb_high"] or (lg == "ncaab" and a["3pt"] <= c["3pt_low"])
    if not good:
        return 0
    if lg == "ncaab" and b and b["oreb"] >= c["oreb_high"]:
        return 0
    return 1


# 🏀 11/22 DAILY STUDIES S1 - THE NBA TEAM THAT SHUTS THE PAINT (results/studies/daily_1122/s_hoops.py / s1b_nba_paint.py /
# s1c_nba_paint_controls.py; ESPN's team box 2021-26 - pointsInPaint, a column no study had read). The share of the
# points a team GIVES UP that come in the paint, season to date (10+ box games), ranked among the league's current
# values (20+ teams read): the bottom fifth "shuts the paint". The read sports.mark_nba_paint / nba_paint_pts weighs.
PAINT_MIN_G = 10
PAINT_MIN_TEAMS = 20
PAINT_FIFTH = 0.2
_PAINT = {}


def _pts(s):
    """A team's points from its box line (2 a field goal + 1 a three + the free throws), or None."""
    fgm = _n(s.get("fieldGoalsMade-fieldGoalsAttempted"), 0)
    tpm = _n(s.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"), 0)
    ftm = _n(s.get("freeThrowsMade-freeThrowsAttempted"), 0)
    if fgm is None or tpm is None or ftm is None:
        return None
    return 2 * fgm + tpm + ftm


def paint_states(now_iso, rows=None, games=None):
    """{team id: {"share": the paint's share of the points it gives up, "n": box games, "pct": its place in the league
    (0 = shuts the paint best)}} - the NBA this season before `now_iso`, regular-season games only when `games` says
    which they are; a team under PAINT_MIN_G box games isn't read, and under PAINT_MIN_TEAMS teams nobody is ranked."""
    key = (now_iso[:13], id(rows) if rows is not None else 0)
    if key in _PAINT:
        return _PAINT[key]
    if rows is None:
        import sports_roster as sr
        try:
            rows = sr.team_rows("nba")
        except Exception:                                    # noqa: BLE001
            rows = []
    y, mo = int(now_iso[:4]), int(now_iso[5:7])
    season0 = f"{y if mo >= 7 else y - 1}-07-01"
    acc = {}
    for r in rows:
        st_ = r.get("start") or ""
        if not (season0 <= st_ < now_iso):
            continue
        if games is not None:
            g = games.get(r.get("gid")) or {}
            if str(g.get("stype") or "2") != "2":
                continue                                     # (preseason boxes are no read)
        tm = r.get("teams") or {}
        if len(tm) != 2:
            continue
        (ta, sa), (tb_, sb) = tm.items()
        for me, opp in ((ta, sb), (tb_, sa)):
            paint, pts = _n(opp.get("pointsInPaint")), _pts(opp)
            if paint is None or not pts:
                continue
            a = acc.setdefault(str(me), [0.0, 0.0, 0])
            a[0] += paint
            a[1] += pts
            a[2] += 1
    teams = {t: {"share": a[0] / a[1], "n": a[2]} for t, a in acc.items() if a[2] >= PAINT_MIN_G and a[1]}
    if len(teams) >= PAINT_MIN_TEAMS:
        for t, v in teams.items():
            v["pct"] = sum(1 for x in teams.values() if x["share"] < v["share"]) / (len(teams) - 1)
    _PAINT.clear()
    _PAINT[key] = teams
    return teams


def paint_shut(st, team):
    """True = this team is in the league's best fifth at keeping points out of the paint, False = it isn't, None = unread."""
    v = (st or {}).get(str(team))
    if not v or v.get("pct") is None:
        return None
    return v["pct"] <= PAINT_FIFTH
