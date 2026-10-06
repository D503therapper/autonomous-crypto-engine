"""Key players: starting QBs (NFL, college), starting pitchers (MLB) and goalies (NHL), from ESPN box scores.

Stored in data/sports/players/<league>.csv (one row per starter per finished game). Used two ways:
  - the model: a "key player" edge per game (recent form of each side's QB / starting pitcher / goalie),
    whose weight the engine learns like every other input;
  - the Full breakdown: "3 picks in his last 2 games", "getting shelled his last 3 starts"."""
import csv
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import sports_data as sd

CACHE = {}          # {league: rows} loaded once per run, for the breakdowns

SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={eid}"
ROLE = {"nfl": "QB", "ncaaf": "QB", "mlb": "SP", "nhl": "G"}
FIELDS = ["gid", "start", "team", "player", "role", "att", "cmp", "yds", "td", "int", "ip", "h", "r", "er", "bb", "k",
          "sa", "ga"]
RECENT = {"QB": 4, "SP": 5, "G": 5}          # games of form that count
# league-average priors, so a few games can't swing a rating too far
QB_AVG, QB_PRIOR_ATT = 6.0, 80               # adjusted yards per attempt
SP_AVG, SP_PRIOR_IP = 4.5, 20                # runs allowed per 9 innings
G_AVG, G_PRIOR_SA = 0.900, 150               # save percentage


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _ip(x):
    """'6.2' innings -> 6.667."""
    whole, _, part = str(x).partition(".")
    return _f(whole) + (_f(part) / 3 if part else 0)


def parse_box(league, gid, start, payload):
    """Starters' lines from an ESPN summary: [{FIELDS...}]."""
    out = []
    for team in (payload.get("boxscore") or {}).get("players") or []:
        tid = str((team.get("team") or {}).get("id") or "")
        for grp in team.get("statistics") or []:
            keys = grp.get("keys") or []
            ath = [a for a in grp.get("athletes") or [] if a.get("stats")]
            if not ath:
                continue
            row = None
            if league in ("nfl", "ncaaf") and grp.get("name") == "passing":
                def att(a):
                    return _f(str(a["stats"][keys.index("completions/passingAttempts")]).split("/")[-1])
                a = max(ath, key=att)
                s = dict(zip(keys, a["stats"]))
                c, _, n = str(s.get("completions/passingAttempts", "0/0")).partition("/")
                row = {"att": _f(n), "cmp": _f(c), "yds": _f(s.get("passingYards")), "td": _f(s.get("passingTouchdowns")),
                       "int": _f(s.get("interceptions"))}
            elif league == "mlb" and "fullInnings.partInnings" in keys:
                a = ath[0]                                     # the starter is listed first
                s = dict(zip(keys, a["stats"]))
                row = {"ip": _ip(s.get("fullInnings.partInnings")), "h": _f(s.get("hits")), "r": _f(s.get("runs")),
                       "er": _f(s.get("earnedRuns")), "bb": _f(s.get("walks")), "k": _f(s.get("strikeouts"))}
            elif league == "nhl" and grp.get("name") == "goalies":
                a = max(ath, key=lambda a: _f(dict(zip(keys, a["stats"])).get("shotsAgainst")))
                s = dict(zip(keys, a["stats"]))
                row = {"sa": _f(s.get("shotsAgainst")), "ga": _f(s.get("goalsAgainst"))}
            if row:
                out.append({"gid": gid, "start": start, "team": tid, "player": (a.get("athlete") or {}).get("displayName") or "?",
                            "role": ROLE[league], **row})
    return out


def fetch_box(league, gid, start):
    path = sd.LEAGUES[league][0]
    url = SUMMARY.format(path=path, eid=gid.split(":", 1)[1])
    for i in range(2):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return parse_box(league, gid, start, json.load(r))
        except Exception as e:                           # noqa: BLE001
            if i == 1:
                sd.ERRORS.append(f"box {gid}: {str(e)[:100]}")
                return None
            time.sleep(1.5)


def _nm(x):
    return " ".join(str(x or "").lower().replace(".", "").replace(" jr", "").replace(" sr", "").replace(" iii", "")
                    .replace(" ii", "").split())


def recent_starters(league, team_id, n=3):
    """The names that started at QB / in goal for this team in its last `n` games (our box scores), or None when we
    hold none (unknown). The 10/2 Steelers card: 'both teams are down their starting quarterback' - Drew Allar and
    Taylen Green, two BACKUPS on the injury report; Rodgers and Watson started. Only a real starter is a key player."""
    rows = [r for r in CACHE.get(league) or [] if str(r.get("team")) == str(team_id)]
    if not rows:
        return None
    gids = []
    for r in reversed(rows):                         # rows are sorted by start: the last n games
        if r["gid"] not in gids:
            gids.append(r["gid"])
        if len(gids) >= n:
            break
    return {_nm(r["player"]) for r in rows if r["gid"] in gids}


_NBA = {}


def nba_starters(team_id, n=10, need=3):
    """NBA: the players who started 3+ of the team's last 10 games (the roster box scores), or None when we hold none
    this season. (10/2, the owner: "that goes for all sports" - any NBA player on the report counted as key, the 15th
    man too.)"""
    if "rows" not in _NBA:
        import csv
        import glob
        import gzip
        from datetime import datetime, timedelta, timezone
        rows = []
        for f in sorted(glob.glob(os.path.join(sd.DATA, "roster", "nba_*.csv.gz")))[-1:]:
            try:
                with gzip.open(f, "rt", newline="") as fh:
                    rows = [r for r in csv.DictReader(fh) if r.get("starter") == "1"]
            except (OSError, EOFError, ValueError):
                rows = []
        cut = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
        _NBA["rows"] = [r for r in rows if (r.get("start") or "") >= cut]
    rows = [r for r in _NBA["rows"] if str(r.get("team")) == str(team_id)]
    if not rows:
        return None
    gids = sorted({(r["start"], r["gid"]) for r in rows})[-n:]
    keep = {g for _, g in gids}
    count = {}
    for r in rows:
        if r["gid"] in keep:
            count[_nm(r["player"])] = count.get(_nm(r["player"]), 0) + 1
    return {p for p, k in count.items() if k >= min(need, len(keep))}


def _starter_of(lg, tid, name):
    st = nba_starters(tid) if lg == "nba" else recent_starters(lg, tid, n=1 if lg in ("nfl", "ncaaf") else 3)
    #   (10/5, the owner: "⚠️ Cooper Rush (Falcons QB) is now out" - Rush started 2 of the Falcons' last 3, but Penix
    #   started the latest one: in football the starting QB is the one who started the LAST game; hockey keeps 3 - goalies
    #   split starts)
    return None if st is None else _nm(name) in st


sd.STARTER_OF = _starter_of


def _path(league):
    return os.path.join(sd.DATA, "players", f"{league}.csv")


def load():
    """{league: [rows sorted by start]}"""
    out = {}
    for lg in ROLE:
        p = _path(lg)
        rows = []
        if os.path.exists(p):
            with open(p) as f:
                rows = list(csv.DictReader(f))
        rows.sort(key=lambda r: (r["start"], r["gid"]))
        out[lg] = rows
    return out


def save(players):
    for lg, rows in players.items():
        p = _path(lg)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + ".tmp", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: (r["start"], r["gid"])))
        os.replace(p + ".tmp", p)


def sync(games, state, workers=8, budget_s=420):
    """Fetch box scores for finished real games we don't have yet (a stretch per run until caught up)."""
    import sports_model as sm
    players = load()
    have = {r["gid"] for rows in players.values() for r in rows} | set(state.get("box_none", []))
    jobs = [(lg, g["id"], g["start"]) for lg in ROLE for g in sm.finals(games, lg) if g["id"] not in have]
    jobs.sort(key=lambda j: j[2], reverse=True)            # newest first: they matter most
    deadline = time.time() + budget_s

    def run(job):
        return job, (fetch_box(*job) if time.time() < deadline else None)
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(run, jobs))
    got = 0
    none = set(state.get("box_none", []))
    for (lg, gid, _), rows in results:
        if rows is None:
            continue
        if rows:
            players[lg].extend(rows)
            got += 1
        else:
            none.add(gid)                                   # ESPN has no box score for this one: don't ask again
    state["box_none"] = sorted(none)[-20000:]
    save(players)
    return got, len(jobs), sum(1 for _, r in results if r is None)


# ---------------------------------------------------------------- form of one player / one team's starter
def last_starter(rows, team, before):
    for r in reversed(rows):
        if r["team"] == team and r["start"] < before:
            return r["player"]
    return None


def starter_for(rows, g, side):
    """The goalie to weigh for a side of an NHL game: the CONFIRMED / likely starter when one is known (sports_goalies -
    the 10/6 build; spelled the way our box scores spell him), else the team's last starter (the old guess). Any other
    league: the last starter."""
    if g.get("league") == "nhl":
        try:
            import sports_goalies
            k = sports_goalies.starter(g.get("id"), side)
        except Exception:                                    # noqa: BLE001 - unknown: the old guess
            k = None
        if k and k.get("name"):
            want = _nm(k["name"])
            for r in reversed(rows):
                if r["team"] == g[side] and _nm(r["player"]) == want:
                    return r["player"]
            return k["name"]                                 # (no box score of his yet: the form reads 'not enough')
    return last_starter(rows, g[side], g["start"])


def score(role, starts):
    """One number per role, shrunk toward league average: QB adjusted yards/attempt, SP runs per 9, G save %."""
    if role == "QB":
        att = sum(_f(r["att"]) for r in starts)
        val = sum(_f(r["yds"]) + 20 * _f(r["td"]) - 45 * _f(r["int"]) for r in starts)
        return (val + QB_AVG * QB_PRIOR_ATT) / (att + QB_PRIOR_ATT)
    if role == "SP":
        ip = sum(_f(r["ip"]) for r in starts)
        runs = sum(_f(r["r"]) for r in starts)
        return (runs + SP_AVG / 9 * SP_PRIOR_IP) / (ip + SP_PRIOR_IP) * 9
    sa = sum(_f(r["sa"]) for r in starts)
    saves = sum(_f(r["sa"]) - _f(r["ga"]) for r in starts)
    return (saves + G_AVG * G_PRIOR_SA) / (sa + G_PRIOR_SA)


def edge_units(role, home, away):
    """Home-minus-away key player edge on a common scale (positive = home's guy is better)."""
    if role == "QB":
        return (home - away) / 2          # 2 yards/attempt ~ one unit
    if role == "SP":
        return (away - home) / 2          # fewer runs allowed is better
    return (home - away) * 50             # .020 of save % ~ one unit


def key_edges(games, players):
    """{game id: key player edge} for every game in stored leagues (finished: the actual starters; upcoming: the
    announced starting pitcher, else the team's most recent starter)."""
    out = {}
    for lg, role in ROLE.items():
        rows = players.get(lg) or []
        if not rows:
            continue
        by_game = {}
        for r in rows:
            by_game.setdefault(r["gid"], {})[r["team"]] = r["player"]
        by_player = {}
        for r in rows:
            by_player.setdefault(r["player"], []).append(r)
        for g in games.values():
            if g["league"] != lg:
                continue
            start = g["start"]
            names = {}
            for side in ("home", "away"):
                if g["status"] == "final":
                    who = by_game.get(g["id"], {}).get(g[side])
                elif role == "SP":
                    who = g.get("sp_" + side) or None
                elif role == "G":
                    who = starter_for(rows, g, side)         # (the confirmed / likely goalie when known)
                else:
                    who = last_starter(rows, g[side], start)
                names[side] = who
            if not names["home"] or not names["away"]:
                continue
            h = score(role, [r for r in by_player.get(names["home"], []) if r["start"] < start][-RECENT[role]:])
            a = score(role, [r for r in by_player.get(names["away"], []) if r["start"] < start][-RECENT[role]:])
            out[g["id"]] = edge_units(role, h, a)
    return out


def form_line(league, player, rows, before):
    """Plain-talk recap of a player's last few starts, and whether that's good or bad: (text, 'hot'|'cold'|None)."""
    role = ROLE.get(league)
    try:                                                     # (10/1 audit: "lately" was last May's playoff starts -
        from datetime import datetime, timedelta             # a 45-day window, so "lately" means this season)
        lo = (datetime.strptime(before[:10], "%Y-%m-%d") - timedelta(days=45)).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        lo = ""
    starts = [r for r in rows if r["player"] == player and lo <= r["start"] < before][-3:]
    if not role or not starts:
        return None, None
    n = len(starts)
    games = f"his last {n} game{'s' if n > 1 else ''}" if role == "QB" else f"his last {n} start{'s' if n > 1 else ''}"
    if role == "QB":
        td, it = sum(_f(r["td"]) for r in starts), sum(_f(r["int"]) for r in starts)
        yds = sum(_f(r["yds"]) for r in starts)
        txt = f"{td:.0f} TD{'s' if td != 1 else ''}, {it:.0f} pick{'s' if it != 1 else ''} and {yds:.0f} yards in {games}"
        mood = "cold" if it >= 2 and it >= td else "hot" if td >= 2 * n and it <= 1 else None
    elif role == "SP":
        ip, r, k = sum(_f(x["ip"]) for x in starts), sum(_f(x["r"]) for x in starts), sum(_f(x["k"]) for x in starts)
        txt = f"{r:.0f} runs in {ip:.0f} innings with {k:.0f} K's over {games}"
        ra9 = r / ip * 9 if ip else 9
        mood = "cold" if ra9 >= 5.5 else "hot" if ra9 <= 2.8 else None
    else:
        sa, ga = sum(_f(x["sa"]) for x in starts), sum(_f(x["ga"]) for x in starts)
        pct = (sa - ga) / sa if sa else 0.9
        txt = f"a {pct:.3f} save % ({ga:.0f} goals on {sa:.0f} shots) over {games}"
        mood = "cold" if pct < 0.885 else "hot" if pct >= 0.925 else None
    return txt, mood

