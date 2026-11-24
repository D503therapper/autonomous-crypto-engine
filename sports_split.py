"""🏠 11/24 DAILY STUDIES - S1 / S2 (results/studies/daily_1124/s_today.py -> s_follow.py -> s2c_board_replay.py): A PRO
TEAM'S HOME / ROAD SPLIT - its margin a game at home minus its margin a game on the road, this season before tonight
(regular season, 15+ games, 6+ at home and 6+ on the road; a hockey margin counts at most 6, an NBA one at most 30;
a neutral site is neither), placed in the league that night.

Two tracker LEADS stand on it (sports.mark_split stamps them, sports_leads.daily_1124_tags tracks them) - no weight:
  NHL  the HOME side in the league's bottom fifth (its home margin lags its road margin): -11.7% on 1,316 at the close
       2018-26 at -200..+350 (train -12.1% / held -11.4%, 9 of 9 seasons down; the same prices at random as bad 14 of
       2,000; ESPN's open 2023-26 -11.6% on 589) - but the replay board posted 20 such sides in three seasons;
  NBA  the ROAD dog in the top fifth (home-heavy) with a winning margin overall: -25.3% on 306 (train -28.3% / held
       -22.7%, same-price placebo 1 of 2,000) - but the paid morning price 2020-23 does not confirm it.
Read-only on the games file; unknown = None, never a guess."""

MIN_GAMES = 15
MIN_EACH = 6
MIN_TEAMS = 20
CAP = {"nhl": 6.0, "nba": 30.0}
_CACHE = {}                  # (league, id(games), len(games), day) -> {team: {"split", "all"}}


def season_of(start):
    y, m = int(str(start)[:4]), int(str(start)[5:7])
    return y if m >= 7 else y - 1


def reads(games, lg, start):
    """{team id: {"split": home margin a game minus road margin a game, "all": margin a game}} for every team of `lg`
    with enough games this season before `start`."""
    start = str(start or "")
    if lg not in CAP or len(start) < 10:
        return {}
    key = (lg, id(games), len(games or {}), start[:10])
    if key in _CACHE:
        return _CACHE[key]
    lo, cap = f"{season_of(start)}-07-01", CAP[lg]
    day = start[:10]
    acc = {}
    for gid, g in (games or {}).items():
        if g.get("league", lg) != lg or not str(g.get("id") or gid).startswith(lg + ":") or g.get("status") != "final":
            continue
        s = str(g.get("start") or "")
        if not (lo <= s and s[:10] < day) or str(g.get("stype") or "2") != "2":
            continue
        try:
            m = float(g["home_score"]) - float(g["away_score"])
        except (KeyError, TypeError, ValueError):
            continue
        m = max(-cap, min(cap, m))
        neutral = str(g.get("neutral") or "0") == "1"
        for t, mine, home in ((str(g.get("home")), m, True), (str(g.get("away")), -m, False)):
            a = acc.setdefault(t, [0, 0.0, 0, 0.0, 0, 0.0])       # home n / sum, road n / sum, all n / sum
            a[4] += 1
            a[5] += mine
            if not neutral:
                a[0 if home else 2] += 1
                a[1 if home else 3] += mine
    out = {t: {"split": a[1] / a[0] - a[3] / a[2], "all": a[5] / a[4]}
           for t, a in acc.items() if a[4] >= MIN_GAMES and a[0] >= MIN_EACH and a[2] >= MIN_EACH}
    if len(_CACHE) > 40:
        _CACHE.clear()
    _CACHE[key] = out
    return out


def place(games, lg, team, start):
    """{"split": the share of the league's other teams under this team's split, "all": the same on its margin} - or
    None (too few games, under MIN_TEAMS teams read)."""
    r = reads(games, lg, start)
    me = r.get(str(team))
    if not me or len(r) < MIN_TEAMS:
        return None
    n = len(r) - 1
    return {k: sum(1 for x in r.values() if x[k] < me[k]) / n for k in ("split", "all")}


def lags_at_home(games, team, start):
    """NHL: is this team in the league's bottom fifth on home-minus-road margin? True / False / None."""
    p = place(games, "nhl", team, start)
    return None if p is None else p["split"] <= 0.2


def home_heavy_winner(games, team, start):
    """NBA: is this team in the league's top fifth on home-minus-road margin AND in the top half on its margin overall?
    True / False / None."""
    p = place(games, "nba", team, start)
    return None if p is None else (p["split"] >= 0.8 and p["all"] >= 0.5)
