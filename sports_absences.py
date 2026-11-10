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


def missed_lately(games, league, team, name, before, n=2):
    """10/23 (Air Force's QB L. Szarka, out since 10/10 - the backup started and won the last 2): a key player who sat
    the team's last `n` games is old news, never sold on a card as a fresh edge. False when we hold fewer box scores."""
    real = [(s, gid, rs) for s, gid, rs in _games(league).get(str(team), [])
            if s < before and str(((games or {}).get(gid) or {}).get("stype") or "2") in sd.REAL]
    if len(real) < n:
        return False
    return not any(match(name, {_nm(r["player"]) for r in rs}) for _, _, rs in real[-n:])


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


QB_MIN_ATT = 8      # 🏈 11/7 daily study (results/studies/daily_1107/s1b_followups.py): a game's QB = its top passer, 8+ attempts


def qbs_used(games, league, team, before, rows=None):
    """🏈 11/7: {"n": distinct quarterbacks this season, "games": box games, "names": [in order of first start]} - a
    game's QB is its top passer by attempts (QB_MIN_ATT+), this season's real games before `before` only. None when the
    box scores hold under 2 such games (unknown, never a guess). `rows` = [(start, gid, rows)] for the tests."""
    if league not in ("nfl", "ncaaf"):
        return None
    before = str(before or "")
    if len(before) < 7:
        return None
    y, m = int(before[:4]), int(before[5:7])
    since = f"{y if m >= 7 else y - 1}-07-01"
    src = rows if rows is not None else _games(league).get(str(team), [])
    names = []
    n = 0
    for s, gid, rs in sorted(src, key=lambda x: x[0]):
        if not since <= s < before or str(((games or {}).get(gid) or {}).get("stype") or "2") not in sd.REAL:
            continue
        best, att = None, 0
        for r in rs:
            if r.get("group") != "passing":
                continue
            try:
                a = int(str(json.loads(r.get("stats") or "{}").get("completions/passingAttempts", "0/0")).split("/")[1])
            except (ValueError, IndexError, TypeError):
                continue
            if a > att:
                best, att = (r.get("pid") or r.get("player"), r.get("player") or ""), a
        if best is None or att < QB_MIN_ATT:
            continue
        n += 1
        if best[0] not in [x[0] for x in names]:
            names.append(best)
    if n < 2:
        return None
    return {"n": len(names), "games": n, "names": [nm for _, nm in names]}


INT_LUCK_MIN_GAMES = 5                                   # 🏈 11/4 daily study 1: the season INT margin needs 5+ box games


def int_margin(games, league, team, before, rows=None):
    """🏈 11/4 daily study 1: {"margin": interceptions made minus thrown A GAME this season, "games": n} for a football
    team from its box scores before `before` (this season's real games only, INT_LUCK_MIN_GAMES+ of them), or None
    (no box scores / too few = unknown, never a guess). The box holds interceptions thrown (the passing group) and
    made (the interceptions group) - no fumbles. `rows` = [(start, gid, rows)] for the tests (else the saved box files)."""
    if league not in ("nfl", "ncaaf"):
        return None
    before = str(before or "")
    if len(before) < 7:
        return None
    y, m = int(before[:4]), int(before[5:7])
    since = f"{y if m >= 7 else y - 1}-07-01"
    src = rows if rows is not None else _games(league).get(str(team), [])
    real = [(s, gid, rs) for s, gid, rs in src if since <= s < before
            and str(((games or {}).get(gid) or {}).get("stype") or "2") in sd.REAL]
    if len(real) < INT_LUCK_MIN_GAMES:
        return None
    made = thrown = 0.0
    for _, _, rs in real:
        for r in rs:
            try:
                st = json.loads(r.get("stats") or "{}")
            except ValueError:
                continue
            if r.get("group") == "passing":
                thrown += _num(st.get("interceptions"))
            elif r.get("group") == "interceptions":
                made += _num(st.get("interceptions"))
    return {"margin": round((made - thrown) / len(real), 2), "games": len(real)}


YARD_LUCK_MIN_GAMES = 3                                  # 🏈 11/10 daily studies 4 / 8 (results/studies/daily_1110/s4_s8 +
YARD_LUCK_SLOPE = {"nfl": 0.0695, "ncaaf": 0.1089}       # s4b): points of margin per yard of margin, fit on 2021-22 only


def _yards(rs):
    """Passing + rushing yards in one team's box rows (None if the box carries neither)."""
    y, seen = 0.0, False
    for r in rs:
        g = r.get("group")
        if g not in ("passing", "rushing"):
            continue
        try:
            st = json.loads(r.get("stats") or "{}")
        except ValueError:
            continue
        v = st.get("passingYards" if g == "passing" else "rushingYards")
        if v is None or str(v).strip() == "":
            continue
        y += _num(v)
        seen = True
    return y if seen else None


def yard_luck(games, league, team, before, rows=None):
    """🏈 11/10 daily studies 4 / 8: {"luck": the team's point margin a game MINUS what its yard margin a game says it
    should be (YARD_LUCK_SLOPE), "games": n} this season before `before` - a game counts when both teams' box scores
    (passing + rushing yards) and the final score are on file, YARD_LUCK_MIN_GAMES+ of them; else None (unknown, never a
    guess). Big plus = the scoreboard has run ahead of the yards (returns, fumbles, red-zone luck - what the public
    reads as 'they just win'). `rows` = {team: [(start, gid, rows)]} for the tests (else the saved box files)."""
    if league not in YARD_LUCK_SLOPE:
        return None
    before = str(before or "")
    if len(before) < 7:
        return None
    y, m = int(before[:4]), int(before[5:7])
    since = f"{y if m >= 7 else y - 1}-07-01"
    src = rows if rows is not None else _games(league)
    n, pm, ym = 0, 0.0, 0.0
    for s, gid, rs in src.get(str(team), []):
        if not (since <= s < before):
            continue
        g = (games or {}).get(gid) or {}
        if str(g.get("stype") or "2") not in sd.REAL or g.get("status") != "final":
            continue
        home = str(g.get("home")) == str(team)
        opp = str(g.get("away") if home else g.get("home"))
        theirs = next((r2 for s2, gid2, r2 in src.get(opp, []) if gid2 == gid), None)
        if not theirs:
            continue
        mine_y, their_y = _yards(rs), _yards(theirs)
        if mine_y is None or their_y is None:
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, TypeError, ValueError):
            continue
        n += 1
        pm += (hs - as_) if home else (as_ - hs)
        ym += mine_y - their_y
    if n < YARD_LUCK_MIN_GAMES:
        return None
    return {"luck": round(pm / n - YARD_LUCK_SLOPE[league] * ym / n, 1), "games": n}


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
    rows = sd._team_rows(inj, g[side], g[side + "_name"])
    out = {_nm(r[0]) for r in rows if _gone(r[2])}
    thru = set()                                     # 🏀 10/30: a questionable man the board treats as PLAYING (he plays
    if lg == "nba":                                  # through it - sports_questionable): no hold, so his 1-in-5 chance
        try:                                         # to sit is weighed here instead
            import sports
            thru = {_nm(r[0]) for r in rows if not _gone(r[2]) and any(x in str(r[2]).lower() for x in sd.UNSURE)
                    and sports.NBA_PLAYS_THROUGH and __import__("sports_questionable").usually_plays(r[0])}
        except Exception:                            # noqa: BLE001
            thru = set()
    if not out and not thru:
        return 0.0, []
    if thru:
        base = penalty(games, g, side, {lg: {g[side]: [r for r in rows if _nm(r[0]) not in thru]}}, skip_qb)
        worst = penalty(games, g, side, {lg: {g[side]: [r for r in rows if _nm(r[0]) not in thru]
                                                      + [(r[0], r[1], "Out") for r in rows if _nm(r[0]) in thru]}}, skip_qb)
        import sports_questionable as sq
        return base[0] + (1 - sq.USUALLY_PLAYS) * max(0.0, worst[0] - base[0]), base[1]
    kp = key_players(games, lg, g[side], g.get("start") or "9")
    is_out = lambda p: p is not None and match(p, out)          # noqa: E731
    if lg in ("nfl", "ncaaf"):
        roles = [("QB", kp.get("qb"))] if not skip_qb else []
        roles += [("RB", kp.get("rb"))] + [("WR", w) for w in kp.get("wr") or []]
        seen_ = set()                                # (11/4 audit: one man, one role - C Michigan's Angel Flores was
        roles_ = []                                  #  the QB AND the 'RB' (his rushing yards) and counted twice)
        for r, p in roles:
            if p is not None and _nm(p) not in seen_:
                seen_.add(_nm(p))
                roles_.append((r, p))
        roles = roles_
        if lg == "ncaaf":                            # (11/4 audit: a college key man who ALREADY MISSED the team's last
            roles = [(r, p) for r, p in roles        #  game is no fresh hole - results/studies/audit_1104/qb_known_out:
                     if not missed_lately(games, lg, g[side], p, g.get("start") or "9", n=1)]   # the QB out again
            #   +0.1 pts vs the own read on 1,398 (the fresh one -3.0 on 1,309 = the built -3). The NFL's 'known' QB out
            #   still runs -3.1 on 400 (5 of 6 seasons) - the NFL keeps the weight.
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
