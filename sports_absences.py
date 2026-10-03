"""🚑 WHAT A MISSING PLAYER IS WORTH (the owner, 10/2: "if the running backs are out and the wide receivers are out
and they got a bunch of backups, that changes everything" / the Red Wings without Dylan Larkin). The 10/2 studies
(our own box scores, 2021-26 regular seasons, the engine's own read replayed pre-game, vs a no-one-out control) - how
many points of win probability the engine's OWN read overstates a team when a key player is out:
  NFL      QB -8 (5 of 5 seasons), lead RB -3, a top-2 WR -3, two or more of those -10 (cap, never stacked)
  college  QB -3, two or more of QB / lead RB / top-2 WR -5 (RB / WR alone: the market and the ratings already have it)
  NHL      top point scorer -6, one of the top 2 -4, two of the top 3 -7, cap 8 (a backup goalie ~1: no weight)
  NBA      top scorer -9, two of the top 3 -11, cap 12 (every season the same way; the market prices it fully)
  MLB      a missing bat: noise - no weight
Key players come from the team's own recent box scores (no look-ahead): football its last 3 games (most pass attempts,
most rushing yards, top-2 receiving yards), hockey / hoops its last 10 (points). 'Out' = the injury report lists him
out / doubtful / suspended. Only the engine's OWN read moves (the market already prices most of it), and a starting QB
/ goalie the engine already treats as key keeps that path (the read goes to the market) - never counted twice."""
import json
import re

import sports_data as sd
import sports_roster as sr

WINDOW = {"nfl": 3, "ncaaf": 3, "nhl": 10, "nba": 10}
_TEAM = {}                                   # league -> {team id: [(start, gid, rows)]}


def _nm(x):
    return " ".join(re.sub(r"[^a-z ]", "", str(x or "").lower().replace(" jr", "").replace(" iii", "")
                           .replace(" ii", "")).split())


def _games(league):
    if league not in _TEAM:
        by = {}
        try:
            rows = sr.load(league)
        except Exception:                                    # noqa: BLE001
            rows = []
        for r in rows:
            by.setdefault(r["team"], {}).setdefault(r["gid"], (r["start"], []))[1].append(r)
        _TEAM[league] = {t: sorted((s, gid, rs) for gid, (s, rs) in d.items()) for t, d in by.items()}
    return _TEAM[league]


def _num(x):
    try:
        return float(str(x).split("/")[-1] if "/" in str(x) else x)
    except (TypeError, ValueError):
        return 0.0


def key_players(games, league, team, before):
    """{"qb": name, "rb": name, "wr": [..2], "top": [..3]} from the team's last WINDOW real games before `before`."""
    n = WINDOW.get(league)
    if not n:
        return {}
    real = [(s, gid, rs) for s, gid, rs in _games(league).get(str(team), [])
            if s < before and str((games.get(gid) or {}).get("stype") or "2") in sd.REAL]
    last = real[-n:]
    tot = {}
    for _, _, rs in last:
        for r in rs:
            try:
                st = json.loads(r.get("stats") or "{}")
            except ValueError:
                continue
            t = tot.setdefault(r["player"], {})
            if league in ("nfl", "ncaaf"):
                t["pass"] = t.get("pass", 0) + _num(st.get("completions/passingAttempts"))
                t["rush"] = t.get("rush", 0) + _num(st.get("rushingYards"))
                t["rec"] = t.get("rec", 0) + _num(st.get("receivingYards"))
            else:
                t["pts"] = t.get("pts", 0) + (_num(st.get("points")) if league == "nba"
                                              else _num(st.get("goals")) + _num(st.get("assists")))
    if not tot:
        return {}
    top = lambda k, m: [p for p, v in sorted(tot.items(), key=lambda x: -x[1].get(k, 0)) if v.get(k, 0) > 0][:m]   # noqa: E731
    if league in ("nfl", "ncaaf"):
        return {"qb": (top("pass", 1) or [None])[0], "rb": (top("rush", 1) or [None])[0], "wr": top("rec", 2)}
    return {"top": top("pts", 3)}


REGULARS = {"pass": 1, "rush": 2, "rec": 4, "tkl": 11}   # football: who actually plays (QB, 2 backs, 4 catchers, 11 tacklers)
PLAYED_WINDOW = {"nhl": 10, "mlb": 15}                   # hockey / baseball: the team's last N games...
PLAYED_MIN = 0.3                                         # ...a regular played in 30%+ of them (3 of 10 / 5 of 15)


def played_lately(games, league, team, before):
    """Normalized names of players who've actually been playing (in 30%+ of the team's last N box scores). None = no
    box scores (the old rule stays)."""
    real = [(s, gid, rs) for s, gid, rs in _games(league).get(str(team), [])
            if s < before and str(((games or {}).get(gid) or {}).get("stype") or "2") in sd.REAL]
    last = real[-PLAYED_WINDOW[league]:]
    if not last:
        return None
    seen = {}
    for _, _, rs in last:
        for p in {_nm(r["player"]) for r in rs}:
            seen[p] = seen.get(p, 0) + 1
    need = max(1, round(PLAYED_MIN * len(last)))
    return {p for p, k in seen.items() if k >= need} or None


NBA_ROTATION = 3                                         # hoops: played in 3+ of the team's last 10 games


def match(name, pool):
    """Is this player in `pool` (normalized names from the box scores / the report)? The exact name, else the ONE pool
    name with the same last name whose first name starts the same way ('Mike Hughes' ~ 'Michael Hughes', "Brenton
    'Inky' Jones" ~ 'Brenten Jones', 'Kait Wheaton' ~ 'Kai Wheaton' - the 10/3 sweep: 23 of 485 official-report names
    were spelled differently from ESPN's box score, so a starter ruled out wasn't counted). Two candidates = no guess."""
    n = _nm(name)
    if not pool or not n:
        return False
    if n in pool:
        return True
    w = n.split()
    if len(w) < 2:
        return False
    k = 1 if len(w[0]) == 1 else 2                         # 'J. Dawson' (an injury page's short name) ~ 'Jalen Dawson'
    close = [p for p in pool if len(q := p.split()) >= 2 and q[-1] == w[-1] and q[0][:k] == w[0][:k]]
    return len(close) == 1


def regulars(games, league, team, before):
    """Players who actually play for this team - football (its last 3 real games' box scores): the QB, the top 2 ball
    carriers, top 4 pass catchers, top 11 tacklers; hoops (its last 10): the rotation, anyone who played 3+ of them -
    normalized names. None = no box scores / not a league this covers (the old rule stays).
    (10/3, the owner: Saturday's board had NO college picks - college availability reports list backup linemen,
    redshirts and walk-ons, so nearly every team tripped '2+ out'. Only players who play count now.)"""
    if league in PLAYED_WINDOW:                              # hockey / baseball (10/3, the owner: "a lot of these times
        return played_lately(games, league, team, before)    # the teams still be doing good without them" - a player
    if league not in ("nfl", "ncaaf", "nba"):                # on the 10-day IL who hasn't played lately isn't a factor)
        return None
    real = [(s, gid, rs) for s, gid, rs in _games(league).get(str(team), [])
            if s < before and str(((games or {}).get(gid) or {}).get("stype") or "2") in sd.REAL]
    last = real[-WINDOW[league]:]
    if league == "nba":
        played = {}
        for _, _, rs in last:
            for r in rs:
                try:
                    st = json.loads(r.get("stats") or "{}")
                except ValueError:
                    continue
                if _num(st.get("minutes")) > 0:
                    played[_nm(r["player"])] = played.get(_nm(r["player"]), 0) + 1
        if not played:
            return None
        return {p for p, k in played.items() if k >= min(NBA_ROTATION, len(last))}
    tot = {}
    for _, _, rs in last:
        for r in rs:
            try:
                st = json.loads(r.get("stats") or "{}")
            except ValueError:
                continue
            t = tot.setdefault(r["player"], {})
            t["pass"] = t.get("pass", 0) + _num(st.get("completions/passingAttempts"))
            t["rush"] = t.get("rush", 0) + _num(st.get("rushingAttempts"))
            t["rec"] = t.get("rec", 0) + _num(st.get("receptions"))
            t["tkl"] = t.get("tkl", 0) + _num(st.get("totalTackles"))
    if not tot:
        return None
    out = set()
    for k, n in REGULARS.items():
        out |= {_nm(p) for p, v in sorted(tot.items(), key=lambda x: -x[1].get(k, 0))[:n] if v.get(k, 0) > 0}
    return out


def _gone(status):
    """Ruled out: out / doubtful / a short IL stint, or long-term (injured reserve, suspended, out for the season) - a
    key player here PLAYED in the team's last games, so a fresh trip to IR is a new absence the results don't hold yet
    (the 10/3 sweep: a lead back put on injured reserve midweek was weighed as playing)."""
    s = str(status).lower()
    return any(x in s for x in sd.SHORT_TERM + sd.LONG_OUT)


def penalty(games, g, side, injuries, skip_qb=False):
    """(points of win prob off this side's OWN read, [who's out]) - 0 when nobody key is out."""
    lg = g.get("league")
    if lg not in WINDOW:
        return 0.0, []
    inj = (injuries or {}).get(lg)
    out = {_nm(r[0]) for r in sd._team_rows(inj, g[side], g[side + "_name"]) if _gone(r[2])}
    if not out:
        return 0.0, []
    kp = key_players(games, lg, g[side], g.get("start") or "9")
    is_out = lambda p: p is not None and match(p, out)          # noqa: E731
    if lg in ("nfl", "ncaaf"):
        roles = [("QB", kp.get("qb"))] if not skip_qb else []
        roles += [("RB", kp.get("rb"))] + [("WR", w) for w in kp.get("wr") or []]
        gone = [(r, p) for r, p in roles if is_out(p)]
        kinds = {r for r, _ in gone}
        if lg == "nfl":
            pts = 10 if len(kinds) >= 2 else 8 if "QB" in kinds else 3 if kinds else 0
        else:
            pts = 5 if len(kinds) >= 2 else 3 if "QB" in kinds else 0
        return pts / 100, [f"{r} {p}" for r, p in gone]
    top = kp.get("top") or []
    gone = [p for p in top if is_out(p)]
    if not gone:
        return 0.0, []
    if lg == "nhl":
        pts = max(6 if top and is_out(top[0]) else 4 if any(is_out(p) for p in top[:2]) else 0,
                  7 if len(gone) >= 2 else 0)
        pts = min(pts, 8)
    else:
        pts = min(max(9 if is_out(top[0]) else 0, 11 if len(gone) >= 2 else 0), 12)
    return pts / 100, gone
