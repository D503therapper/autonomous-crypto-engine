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
