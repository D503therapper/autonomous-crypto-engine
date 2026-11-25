"""⏱️ 11/25 DAILY STUDIES - S9 (results/studies/daily_1125/s_today.py s9 -> s_follow.py s9 / s9c): THE COLLEGE HOOPS
SECOND-HALF TEAM - its second-half margin minus its first-half margin a game (each half counts at most 20), this
season before tonight (5+ games with a line score), placed among the league's teams that night (100+ read).

A tracker LEAD stands on it (sports.mark_halves stamps it, sports_leads.daily_1125_tags tracks it) - no weight:
  the team in the league's top fifth as a ROAD favorite is overpriced: laying points on a true road floor it covered
  41.6% (ATS -15.6% on 1,122 at the close 2018-26), the HOME side getting points across it ATS +6.8% on 1,122 against
  -3.0% for every home side getting points (train 2018-21 +3.0%, 3 of 4 seasons up / held 2022-26 +10.3%, 4 of 4; a
  random same-size set as good 0 of 2,000), the home dog +100..+350 across it +4.7% on 915 against -5.9% (same-price
  placebo 5 of 2,000; +100..+199 +9.1% on 679, 8 of 8 seasons up), the road favorite past -150 itself -9.4% on 730.
  NOT a weight: only the top fifth shows it (the fifth under it is the worst of the five), the same read over a team's
  last 10 games is flat (+0.5% on 1,172), and a second-half team at home or on a neutral floor is priced right.
Read-only on the games file; unknown = None, never a guess."""

MIN_GAMES = 5
MIN_TEAMS = 100
CAP = 20.0
TOP = 0.8
_CACHE = {}                  # (id(games), len(games), day) -> {team: second-half margin minus first-half margin a game}


def season_of(start):
    y, m = int(str(start)[:4]), int(str(start)[5:7])
    return y if m >= 7 else y - 1


def _halves(ls):
    try:
        v = [int(x) for x in str(ls).split(",")]
    except (TypeError, ValueError):
        return None
    return v if len(v) >= 2 else None


def reads(games, start):
    """{team id: second-half margin minus first-half margin a game} for every college hoops team with MIN_GAMES line
    scores this season before the day of `start` (regular season)."""
    start = str(start or "")
    if len(start) < 10:
        return {}
    key = (id(games), len(games or {}), start[:10])
    if key in _CACHE:
        return _CACHE[key]
    lo, day = f"{season_of(start)}-07-01", start[:10]
    acc = {}
    for gid, g in (games or {}).items():
        if g.get("league", "ncaab") != "ncaab" or not str(g.get("id") or gid).startswith("ncaab:") or g.get("status") != "final":
            continue
        s = str(g.get("start") or "")
        if not (lo <= s and s[:10] < day) or str(g.get("stype") or "2") != "2":
            continue
        a, b = _halves(g.get("ls_home")), _halves(g.get("ls_away"))
        if not a or not b:
            continue
        m1 = max(-CAP, min(CAP, a[0] - b[0]))
        m2 = max(-CAP, min(CAP, a[1] - b[1]))
        for t, d in ((str(g.get("home")), m2 - m1), (str(g.get("away")), m1 - m2)):
            x = acc.setdefault(t, [0, 0.0])
            x[0] += 1
            x[1] += d
    out = {t: x[1] / x[0] for t, x in acc.items() if x[0] >= MIN_GAMES}
    if len(_CACHE) > 40:
        _CACHE.clear()
    _CACHE[key] = out
    return out


def place(games, team, start):
    """The share of the league's other teams under this team's read - or None (too few games, under MIN_TEAMS read)."""
    r = reads(games, start)
    me = r.get(str(team))
    if me is None or len(r) < MIN_TEAMS:
        return None
    return sum(1 for x in r.values() if x < me) / (len(r) - 1)


def second_half_team(games, team, start):
    """Is this team in the league's top fifth on second-half margin minus first-half margin? True / False / None."""
    p = place(games, team, start)
    return None if p is None else p >= TOP
