"""🏀 THE ROSTER-AWARE NBA PRESEASON PRIOR (the owner, 10/20: "with LeBron, Embiid, Maxey, Edgecombe this don't make no
sense" / "the engine needs a full updated roster on all NBA teams and needs to know who's playing, who the teams
traded and who they got, at all times").

The NBA Elo (sports_model.Elo) is team results only: on opening night it rates LAST season's teams (the 76ers 26% vs
the market's 38% after LeBron James joined Philly). This module gives the engine a read of its own from day one:

  1. PLAYER VALUE from last season's box scores (data/sports/roster/nba_<season>.csv.gz - every player, every game):
     production per minute = (points + 0.4 FG made - 0.7 FG tried + 0.5 rebounds + 0.7 assists) / minutes - a cut-down
     Hollinger game score built from the numbers the box holds - minus the league's replacement rate (the 11th-15th
     men), times his minutes a game. A player under MIN_GAMES last season (a rookie, a long injury) is worth the
     replacement rate at the minutes he gets. Documented, simple, no black box.
  2. TODAY'S ROSTERS from ESPN's team roster pages (one call per team), cached per day in data/sports/rosters/
     nba_<season>.json; fails soft (no network = the last saved roster, none = no prior). Each refresh is diffed against
     the last saved one: a player who changed teams is written to nba_moves.json (who, from, to, the day we saw it) and
     his value counts for his NEW team right away.
  3. WHO'S PLAYING TONIGHT: the injury report by STATUS (the owner, 10/20): probable = playing (95%), questionable =
     half a player (50% - a game-time decision, flagged so the board can wait for news before a unit play), doubtful =
     25%, out / suspended / injured reserve = 0. A questionable note that says 'expected to play' / 'probable' counts
     as playing.
  4. TEAM STRENGTH = the sum of the current players' value at their expected minutes (the top ROTATION by minutes,
     scaled to a 240-minute game), turned into Elo points with a scale fitted on the season before (margin a game
     ~ strength, ELO_PER_PT per point), then BLENDED with the carried Elo: the roster at game 0, the Elo by BLEND_GAMES.

Validated before it touched a pick (SPORTS_FINDINGS.md, 10/20): each past season graded with the season before it.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

import sports_data as sd
import sports_model as sm

DIR = os.path.join(sd.DATA, "rosters")
MOVES_PATH = os.path.join(DIR, "nba_moves.json")
ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{tid}/roster"
TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams?limit=50"

MIN_GAMES = 15          # fewer last season = no read on him: the replacement rate at his minutes
ROTATION = 10           # the players who play: the top 10 by expected minutes
GAME_MIN = 240.0        # five men, 48 minutes
REPL_PCT = 0.25         # the replacement rate: the 25th percentile of rotation players' per-minute production
ELO_PER_PT = 25.0       # NBA Elo points per point of margin a game (a 1-point favorite ~ 53%)
BLEND_GAMES = 10        # the roster prior carries the read at game 0, the Elo takes over by here
PLAY = {"probable": 0.95, "questionable": 0.5, "game-time": 0.5, "game time": 0.5, "day-to-day": 0.5,
        "day to day": 0.5, "doubtful": 0.25}       # anything else on the report (out / suspended / IR / season) = 0
PLAY_NOTE = ("expected to play", "probable", "will play", "available")   # a questionable note that says he's playing
MIN_ROSTER = 8          # fewer players on a fetched roster = a broken page, never 'a thin team'


def _nm(x):
    return " ".join(re.sub(r"[^a-z ]", "", str(x or "").lower().replace(" jr", "").replace(" iii", "")
                           .replace(" ii", "")).split())


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def season_of(start):
    """'2026-10-20...' -> 2026 (a fall-to-spring season is its first year; July starts the new one)."""
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 7 else y - 1


# ---------------------------------------------------------------- 1. player value from the box scores
METRIC = ["pm"]         # "pm" = plus-minus (what the 10/20 study picked), "gs" = the cut-down game score


def game_score(st):
    """A cut-down Hollinger game score from what the box holds. 'fieldGoalsMade-fieldGoalsAttempted' is '9-16'."""
    fg = str(st.get("fieldGoalsMade-fieldGoalsAttempted") or "0-0").split("-")
    made, tried = (_num(fg[0]), _num(fg[1])) if len(fg) == 2 else (0.0, 0.0)
    return _num(st.get("points")) + 0.4 * made - 0.7 * tried + 0.5 * _num(st.get("rebounds")) + 0.7 * _num(st.get("assists"))


def production(st):
    """One box line -> (minutes, his production that game): the team's plus-minus while he was on the floor (the 10/20
    study: it told the coming season's margins better than the box-score line every season - 0.55-0.65 vs 0.07-0.63)."""
    mins = _num(st.get("minutes"))
    if METRIC[0] == "gs":
        return mins, game_score(st)
    return mins, _num(str(st.get("plusMinus") or "0").replace("+", ""))


def player_values(rows, min_games=MIN_GAMES):
    """Box-score rows (one season) -> {"players": {pid: {"name", "mpg", "rate", "games", "team"}}, "repl": rate}.
    rate = production per minute; team = where he played most. Players under min_games are kept (their minutes,
    their name) but get no rate of their own (None) - the replacement rate stands in for them."""
    acc = {}
    for r in rows:
        try:
            st = json.loads(r.get("stats") or "{}")
        except ValueError:
            continue
        mins, gs = production(st)
        if mins <= 0:
            continue
        a = acc.setdefault(r["pid"], {"name": r["player"], "min": 0.0, "gs": 0.0, "games": 0, "teams": {}})
        a["min"] += mins
        a["gs"] += gs
        a["games"] += 1
        a["teams"][r["team"]] = a["teams"].get(r["team"], 0) + 1
    players = {}
    for pid, a in acc.items():
        mpg = a["min"] / a["games"]
        players[pid] = {"name": a["name"], "mpg": round(mpg, 2), "games": a["games"],
                        "rate": round(a["gs"] / a["min"], 4) if a["games"] >= min_games else None,
                        "team": max(a["teams"], key=a["teams"].get)}
    rates = sorted(p["rate"] for p in players.values() if p["rate"] is not None and p["mpg"] >= 12)
    repl = rates[int(len(rates) * REPL_PCT)] if rates else 0.0
    return {"players": players, "repl": repl}


def _norm_name_index(values):
    return {_nm(p["name"]): pid for pid, p in values["players"].items()}


# ---------------------------------------------------------------- 3. who's playing (the injury report by status)
RESTRICTED_MIN = 22.0   # a man on a minutes restriction / limit: ~20-24 of his usual (the owner, 10/20)
RESTRICT_NOTE = ("minutes restriction", "minute restriction", "minutes limit", "minute limit", "limited minutes",
                 "restricted minutes", "on a minutes", "limited")


def play_chance(status, note=""):
    """How much of a player the report leaves us: probable 0.95, questionable 0.5, doubtful 0.25, out 0.
    A questionable note saying he's expected to play = 0.95 (the owner, 10/20)."""
    s, n = str(status or "").lower(), str(note or "").lower()
    if any(w in n for w in PLAY_NOTE) and "doubtful" not in s and "out" not in s.split():
        return PLAY["probable"]
    for k, v in PLAY.items():
        if k in s:
            return v
    return 0.0


def restricted(note):
    """Does the note put him on a minutes restriction?"""
    return any(w in str(note or "").lower() for w in RESTRICT_NOTE)


def report_chances(inj, team_id, team_name, notes=None):
    """{normalized name: (play chance, minutes cap or None)} for every player on this team's injury report (rows are
    (player, pos, status) - a 4th item, the note, when the feed has one). notes = sd.INJ_NOTES-style {plain name:
    {"status", "note"}} - carries the probable men and the notes ESPN's rows drop. Not listed = playing (1.0)."""
    out = {}
    notes = notes or getattr(sd, "INJ_NOTES", {}) or {}
    for r in sd._team_rows(inj, str(team_id), team_name) if inj else []:
        try:
            n = _nm(r[0])
            note = r[3] if len(r) > 3 else (notes.get(n) or {}).get("note", "")
            out[n] = (play_chance(r[2], note), RESTRICTED_MIN if restricted(note) else None)
        except (IndexError, TypeError):
            continue
    return out


def team_notes(notes, roster):
    """The feed's notes for this roster's men not on the rows (probable, a minutes restriction) -> same shape."""
    out = {}
    for p in roster or []:
        n = _nm(p.get("name"))
        d = (notes or {}).get(n)
        if d and (play_chance(d.get("status"), d.get("note")) < 1 or restricted(d.get("note"))):
            out[n] = (play_chance(d.get("status"), d.get("note")) if d.get("status") else 1.0,
                      RESTRICTED_MIN if restricted(d.get("note")) else None)
    return out


def _mpg(v):
    return (v or {}).get("mpg") or 12.0


def _lookup(values, p):
    idx = _norm_name_index(values)
    pid = p.get("pid") or idx.get(_nm(p.get("name")))
    v = values["players"].get(str(pid)) if pid else None
    return v if v is not None else values["players"].get(idx.get(_nm(p.get("name"))) or "")


def tonight(inj, team_id, team_name, roster, notes=None):
    """The report's chances for this roster: the rows (status) plus the feed's notes (probable men, minutes caps)."""
    notes = notes if notes is not None else getattr(sd, "INJ_NOTES", {})
    ch = report_chances(inj, team_id, team_name, notes)
    ch.update({k: v for k, v in team_notes(notes, roster).items() if k not in ch})
    return ch


def flags(inj, team_id, team_name, roster, values, notes=None):
    """What the card / the board should know about tonight's roster: {"game_time": [names - rotation men still a
    game-time decision], "restricted": [names on a minutes restriction], "out": [rotation men out / doubtful]}.
    Rotation = a value of their own last season and 20+ minutes a game."""
    ch = tonight(inj, team_id, team_name, roster, notes)
    out = {"game_time": [], "restricted": [], "out": []}
    for p in roster or []:
        n = _nm(p.get("name"))
        v = _lookup(values, p)
        if n not in ch or not v or (v.get("mpg") or 0) < 20:
            continue
        c, cap = ch[n]
        if cap:
            out["restricted"].append(p.get("name"))
        if PLAY["doubtful"] < c < PLAY["probable"]:
            out["game_time"].append(p.get("name"))
        elif c <= PLAY["doubtful"]:
            out["out"].append(p.get("name"))
    return out


def game_time_decisions(inj, team_id, team_name, roster, values, notes=None):
    return flags(inj, team_id, team_name, roster, values, notes)["game_time"]


# ---------------------------------------------------------------- 4. team strength -> Elo
NEXT_MAN_MAX = 24.0     # a bench man picks up minutes to about 24 a night; the rest goes down the bench, then to
#                         the replacement rate (worth 0 above replacement)


def lineup(roster, values, chances=None, depth=ROTATION):
    """Tonight's expected minutes, man by man: [(name, minutes tonight, value above replacement per minute,
    usual minutes)]. The usual rotation = the top `depth` by last season's minutes (a man with no last season: 12).
    A player at chance c gives c of his minutes (a cap for a minutes restriction); the minutes he leaves go to the
    NEXT MEN UP on this roster in order (each up to NEXT_MAN_MAX a night) at THEIR value per minute - a deep bench
    barely drops, a thin one drops a lot (the owner, 10/20). Scaled to a 240-minute game."""
    chances = chances or {}
    men = []
    for p in roster or []:
        v = _lookup(values, p)
        rate = (v or {}).get("rate")
        c, cap = chances.get(_nm(p.get("name")), (1.0, None))
        usual = _mpg(v)
        play = min(usual, cap) * c if cap else usual * c
        men.append([p.get("name"), play, (rate - values["repl"]) if rate is not None else 0.0, usual])
    men.sort(key=lambda x: -x[3])
    core, bench = men[:depth], men[depth:]
    missing = sum(m[3] - m[1] for m in core)
    for m in bench:                                      # the next men up, in order, pick the minutes up
        if missing <= 0:
            break
        take = min(missing, max(0.0, NEXT_MAN_MAX - m[1]))
        m[1] += take
        missing -= take
    out = [m for m in core + bench if m[1] > 0]
    tot = sum(m[1] for m in out) or 1.0
    scale = min(1.0, GAME_MIN / tot)
    return [(m[0], m[1] * scale, m[2], m[3]) for m in out]


def team_strength(roster, values, chances=None, depth=ROTATION):
    """The sum of tonight's lineup's minutes times value above replacement (see lineup)."""
    return sum(mins * above for _, mins, above, _ in lineup(roster, values, chances, depth))


def bench_strength(roster, values):
    """How good the bench is: the value above replacement per 48 minutes of the men 6-10 by usual minutes (a healthy
    roster). 0 = replacement level; +3 is a bench that outplays most teams' second units."""
    men = sorted(((_mpg(_lookup(values, p)), (_lookup(values, p) or {}).get("rate")) for p in roster or []),
                 key=lambda x: -x[0])[5:10]
    rated = [(m, r - values["repl"]) for m, r in men if r is not None]
    if not rated:
        return 0.0
    return 48.0 * sum(m * a for m, a in rated) / sum(m for m, _ in rated)


# ---------------------------------------------------------------- the coaching style (the owner, 10/20)
STYLE_MIN = 15.0        # a man in the rotation plays 15+ minutes


def coach_style(rows, games, team, season, last_n=None):
    """How the coach runs his team, from the box scores (optionally only the last `last_n` games): rotation depth
    (men at 15+ minutes a game), how hard he rides his starters (their share of the minutes), pace (a proxy: points
    both teams score a game - the box holds no possessions), and rest (how often one of his top 3 by minutes sits the
    second night of a back-to-back vs any other night). INFO for the cards; only depth feeds the lineup math (how many
    men the minutes spread over). None = no box scores."""
    by = {}
    for r in rows:
        if r["team"] == str(team) and season_of(r["start"]) == season:
            by.setdefault((r["start"], r["gid"]), []).append(r)
    keys = sorted(by)[-last_n:] if last_n else sorted(by)
    if not keys:
        return None
    depth, share, mins = [], [], {}
    for k in keys:
        tot, st, n = 0.0, 0.0, 0
        for r in by[k]:
            try:
                m = _num(json.loads(r.get("stats") or "{}").get("minutes"))
            except ValueError:
                m = 0.0
            tot += m
            st += m if r.get("starter") == "1" else 0.0
            n += m >= STYLE_MIN
            mins[r["player"]] = mins.get(r["player"], 0.0) + m
        depth.append(n)
        share.append(st / tot if tot else 0.0)
    top3 = {p for p, _ in sorted(mins.items(), key=lambda x: -x[1])[:3]}
    sat, sat_b2b, nb2b, pts = 0, 0, 0, []
    last_day = None
    for k in keys:
        day = datetime.strptime(k[0][:10], "%Y-%m-%d")
        b2b = last_day is not None and (day - last_day).days == 1
        last_day = day
        missing = top3 - {r["player"] for r in by[k]}
        if b2b:
            nb2b += 1
            sat_b2b += bool(missing)
        else:
            sat += bool(missing)
        g = games.get(k[1]) if games else None
        if g and g.get("home_score") not in ("", None):
            pts.append(int(g["home_score"]) + int(g["away_score"]))
    n_other = len(keys) - nb2b
    return {"games": len(keys), "depth": round(sum(depth) / len(depth), 1), "starters_share": round(sum(share) / len(share), 3),
            "pace": round(sum(pts) / len(pts), 1) if pts else None,
            "rest_b2b": round(sat_b2b / nb2b, 2) if nb2b else None, "rest_other": round(sat / n_other, 2) if n_other else None}


def rotation_depth(style):
    """How many men the minutes spread over tonight: the coach's depth + 1, within 8..11; 10 when unknown."""
    if not style or not style.get("depth"):
        return ROTATION
    return max(8, min(11, int(round(style["depth"])) + 1))


def fit_scale(strengths, margins):
    """{team: strength} and {team: margin a game} from the same season -> (points of margin per unit of strength).
    A one-number least squares through the means; a flat read (no spread) = 0."""
    teams = [t for t in strengths if t in margins]
    if len(teams) < 5:
        return 0.0
    ms = sum(strengths[t] for t in teams) / len(teams)
    mm = sum(margins[t] for t in teams) / len(teams)
    sxx = sum((strengths[t] - ms) ** 2 for t in teams)
    sxy = sum((strengths[t] - ms) * (margins[t] - mm) for t in teams)
    return sxy / sxx if sxx else 0.0


def to_elo(strengths, scale):
    """{team: strength} -> {team: Elo rating} around 1500 (scale = margin per unit of strength)."""
    if not strengths:
        return {}
    mean = sum(strengths.values()) / len(strengths)
    return {t: 1500 + ELO_PER_PT * scale * (s - mean) for t, s in strengths.items()}


def blend(roster_elo, carried_elo, games_played):
    w = blend_weight(games_played)
    return w * roster_elo + (1 - w) * carried_elo


def season_margins(games, season):
    """{team id: average margin a game} over a season's regular-season finals."""
    acc = {}
    for g in games.values():
        if g.get("league") != "nba" or g.get("status") != "final" or str(g.get("stype")) != "2" \
                or season_of(g["start"]) != season or g.get("home_score") in ("", None):
            continue
        d = int(g["home_score"]) - int(g["away_score"])
        for tm, m in ((g["home"], d), (g["away"], -d)):
            a = acc.setdefault(str(tm), [0.0, 0])
            a[0] += m
            a[1] += 1
    return {t: s / n for t, (s, n) in acc.items() if n >= 20}


def played_roster(rows, season, team, first_n=10):
    """The study's roster proxy when no roster was saved: who played in the team's first `first_n` box scores of a
    season -> [{"pid", "name"}]."""
    gids = sorted({(r["start"], r["gid"]) for r in rows if r["team"] == str(team) and season_of(r["start"]) == season})[:first_n]
    keep = {g for _, g in gids}
    seen = {}
    for r in rows:
        if r["gid"] in keep and r["team"] == str(team):
            seen.setdefault(r["pid"], r["player"])
    return [{"pid": pid, "name": nm} for pid, nm in seen.items()]


# ---------------------------------------------------------------- 2. today's rosters (ESPN), cached, diffed
def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as r:
        return json.load(r)


def parse_roster(payload):
    """ESPN's team roster page -> [{"pid", "name", "pos", "status"}]. Never raises on a shape it doesn't know."""
    out = []
    groups = payload.get("athletes") or []
    if groups and isinstance(groups[0], dict) and "items" in groups[0]:   # grouped (football-style) pages
        groups = [a for grp in groups for a in grp.get("items") or []]
    for a in groups:
        if not isinstance(a, dict) or not a.get("id"):
            continue
        out.append({"pid": str(a.get("id")), "name": a.get("displayName") or a.get("fullName") or "?",
                    "pos": ((a.get("position") or {}).get("abbreviation") or ""),
                    "status": (((a.get("status") or {}).get("type")) or "active").lower()})
    return out


def _path(season):
    return os.path.join(DIR, f"nba_{season}.json")


def load_rosters(season):
    """The saved rosters: {"day": "YYYY-MM-DD", "teams": {tid: [players]}} or None."""
    try:
        with open(_path(season)) as f:
            d = json.load(f)
        return d if isinstance(d, dict) and d.get("teams") else None
    except (OSError, ValueError):
        return None


def team_ids(games, season):
    """The 30 NBA team ids from the schedule (this season, then last)."""
    ids = set()
    for s in (season, season - 1):
        for g in games.values():
            if g.get("league") == "nba" and season_of(g["start"]) == s and str(g.get("stype")) == "2":
                ids.update({str(g["home"]), str(g["away"])})
        if len(ids) >= 30:
            break
    return sorted(ids)


def diff_moves(old, new, day):
    """Who changed teams between two saved roster sets -> [{"player", "pid", "from", "to", "seen"}]."""
    where = {p["pid"]: (tid, p["name"]) for tid, ps in (old or {}).items() for p in ps}
    moves = []
    for tid, ps in (new or {}).items():
        for p in ps:
            prev = where.get(p["pid"])
            if prev and prev[0] != tid:
                moves.append({"player": p["name"], "pid": p["pid"], "from": prev[0], "to": tid, "seen": day})
    return moves


def record_moves(moves):
    """Append new moves to nba_moves.json (never the same move twice)."""
    if not moves:
        return 0
    try:
        with open(MOVES_PATH) as f:
            have = json.load(f)
    except (OSError, ValueError):
        have = []
    seen = {(m["pid"], m["from"], m["to"]) for m in have}
    add = [m for m in moves if (m["pid"], m["from"], m["to"]) not in seen]
    if add:
        os.makedirs(DIR, exist_ok=True)
        with open(MOVES_PATH, "w") as f:
            json.dump(have + add, f, indent=0)
    return len(add)


def refresh(games, now=None, fetch=_get, save=True):
    """Daily: every NBA team's roster from ESPN, saved for the season, diffed against the last save (moves
    recorded). Once a day; fails soft - any team that fails keeps its last saved roster; a page with fewer than
    MIN_ROSTER men is a broken read, never 'a thin team'. Returns the saved dict (or None when nothing was ever saved)."""
    now = now or datetime.now(timezone.utc)
    day = now.astimezone(sd.PT_).date().isoformat()
    season = season_of(now.strftime("%Y-%m-%dT%H:%M"))
    have = load_rosters(season) or {"day": "", "teams": {}}
    if have.get("day") == day:
        return have
    new, fails = {}, 0
    for tid in team_ids(games, season):
        try:
            ps = parse_roster(fetch(ROSTER_URL.format(tid=tid)))
            if len(ps) < MIN_ROSTER:
                raise ValueError(f"{len(ps)} players")
            new[tid] = ps
        except Exception as e:                           # noqa: BLE001 - keep the last saved roster
            fails += 1
            sd.ERRORS.append(f"nba roster {tid}: {str(e)[:60]}")
            if tid in have["teams"]:
                new[tid] = have["teams"][tid]
    if not new:
        return have if have["teams"] else None
    moves = diff_moves(have["teams"], new, day) if have["teams"] else []
    out = {"day": day, "season": season, "teams": new, "fails": fails}
    if save:
        os.makedirs(DIR, exist_ok=True)
        with open(_path(season), "w") as f:
            json.dump(out, f, indent=0)
        record_moves(moves)
    out["moves"] = moves
    return out


# ---------------------------------------------------------------- player form (the owner, 10/20: "a star in a slump
# plays like less than a star") - the 10/20 study: blending last season's value with the last 10 games' plus-minute
# rate (the prior worth G_PRIOR games) read 2022-25 games better EVERY season (0.646 -> 0.620 log loss; 20 beat 40 / 80)
G_PRIOR = 20            # last season's value counts as this many games of evidence against the recent ones
FORM_N = 10             # the recent games
FORM_MIN = 60.0         # minutes of recent play before form counts at all
HOT = 5.0               # hot / in a slump: his recent plus-minus a 48 minutes vs his own baseline, +/- this many points
FORM_TAG_MIN = 100.0    # ...and only a man with 100+ recent minutes gets the tag (a card never calls a 10-minute man cold)


def recent_rows(rows_now, before=None, n=FORM_N):
    """{pid: [(minutes, production)] - the last n games before `before` (an ISO start; None = everything)}."""
    by = {}
    for r in sorted(rows_now or [], key=lambda r: (r["start"], r["gid"])):
        if before and r["start"] >= before:
            continue
        try:
            m, pr = production(json.loads(r.get("stats") or "{}"))
        except ValueError:
            continue
        if m > 0:
            by.setdefault(r["pid"], []).append((m, pr))
    return {pid: v[-n:] for pid, v in by.items()}


def form_values(values, rows_now, before=None):
    """Last season's values blended with this season's recent form -> (values with blended rates, {pid: form}).
    form = {"name", "recent": his recent rate a 48, "usual": last season's a 48, "tag": "hot" / "slump" / ""}."""
    out = {"repl": values["repl"], "players": dict(values["players"])}
    form = {}
    for pid, rec in recent_rows(rows_now, before).items():
        mins = sum(m for m, _ in rec)
        if mins < FORM_MIN:
            continue
        rr, n = sum(pr for _, pr in rec) / mins, len(rec)
        base = values["players"].get(pid)
        base_rate = base["rate"] if base and base.get("rate") is not None else values["repl"]
        blended = (G_PRIOR * base_rate + n * rr) / (G_PRIOR + n)
        if base:
            out["players"][pid] = {**base, "rate": round(blended, 4)}
        else:
            out["players"][pid] = {"name": "?", "mpg": round(mins / n, 2), "games": n, "rate": round(blended, 4), "team": ""}
        if base and base.get("rate") is not None and (base.get("mpg") or 0) >= 20 and mins >= FORM_TAG_MIN:
            swing = 48.0 * (rr - base["rate"])
            form[pid] = {"name": base["name"], "recent": round(48.0 * rr, 1), "usual": round(48.0 * base["rate"], 1),
                         "tag": "hot" if swing >= HOT else "slump" if swing <= -HOT else ""}
    return out, form


# ---------------------------------------------------------------- the prior the engine reads
_VALUES = {}
W0 = 0.7                # the roster prior's share of the rating at game 0 (the 10/20 study: 0.7 fading by 10 games
#                         read games 1-20 best - 0.6215 vs the carried Elo's 0.6233, 3 of 4 seasons; games 1-5 0.638 vs 0.646)


def blend_weight(games_played):
    """How much of the rating the roster prior carries: W0 at game 0, 0 by BLEND_GAMES (linear)."""
    return W0 * max(0.0, 1.0 - games_played / BLEND_GAMES)


def values_for(season, rows=None):
    """Last season's player values (cached per season). rows = box-score rows to use instead of the store."""
    if season not in _VALUES:
        if rows is None:
            try:
                import sports_roster as sr
                rows = sr.load("nba", seasons=[season])
            except Exception:                            # noqa: BLE001
                rows = []
        _VALUES[season] = player_values(rows) if rows else None
    return _VALUES[season]


def _rows(season):
    try:
        import sports_roster as sr
        return sr.load("nba", seasons=[season])
    except Exception:                                    # noqa: BLE001
        return []


def prior(games, season, rosters=None, inj=None, values=None, rows_now=None, notes=None, last_rows=None):
    """Tonight's roster read for a season: {"elo": {team id: roster Elo}, "values": the blended player values, "form":
    {pid: form}, "teams": the rosters, "styles": {team id: coach style}, "bench": {team id: bench strength}, "flags":
    {team id: flags}} - from the saved rosters (or the ones passed), LAST season's values blended with this season's
    form, the scale fitted on last season. None when the rosters or the values are missing - the engine then falls back
    to early_trust's market pull. inj (today's report) takes the men who are out / doubtful / questionable / on a
    minutes limit out of tonight's strength, their minutes to the next men up."""
    teams = (rosters or load_rosters(season) or {}).get("teams") or {}
    if len(teams) < 20:                                  # (no rosters saved: nothing to read - the market pull stands)
        return None
    values = values or values_for(season - 1)
    if not values:
        return None
    last_rows = last_rows if last_rows is not None else _rows(season - 1)
    scale = scale_for(games, season - 1, values, last_rows)
    if not scale:
        return None
    rows_now = rows_now if rows_now is not None else _rows(season)
    vals, form = form_values(values, rows_now)
    names = {}
    for g in games.values():
        if g.get("league") == "nba":
            names[str(g["home"])], names[str(g["away"])] = g.get("home_name", ""), g.get("away_name", "")
    notes = notes if notes is not None else (getattr(sd, "INJ_NOTES", {}) or {}).get("nba", {})
    styles, bench, fl, strengths = {}, {}, {}, {}
    for tid, ps in teams.items():
        st = coach_style(rows_now, games, tid, season, last_n=10) if rows_now else None
        if not st or st["games"] < 5:
            st = coach_style(last_rows, games, tid, season - 1, last_n=20) if last_rows else None
        styles[tid] = st
        bench[tid] = round(bench_strength(ps, vals), 1)
        ch = tonight(inj, tid, names.get(tid, ""), ps, notes) if inj is not None else None
        fl[tid] = flags(inj, tid, names.get(tid, ""), ps, vals, notes) if inj is not None else {"game_time": [], "restricted": [], "out": []}
        strengths[tid] = team_strength(ps, vals, ch, depth=rotation_depth(st))
    return {"elo": to_elo(strengths, scale), "values": vals, "form": form, "teams": teams, "styles": styles,
            "bench": bench, "flags": fl, "scale": scale, "season": season}


_CUR = {}


def current(games, inj=None, now=None):
    """Today's prior (cached an hour at a time - the report changes through the day). None = no roster prior."""
    now = now or datetime.now(timezone.utc)
    season = season_of(now.strftime("%Y-%m-%dT%H:%M"))
    key = (season, now.strftime("%Y-%m-%dT%H"), inj is not None)
    if key not in _CUR:
        _CUR.clear()
        try:
            _CUR[key] = prior(games, season, inj=inj)
        except Exception as e:                           # noqa: BLE001 - never blocks the board
            print(f"nba roster prior failed: {str(e)[:80]}")
            _CUR[key] = None
    return _CUR[key]


def cached():
    """The last prior current() built this run (None before the first call / when there's none)."""
    return next(iter(_CUR.values()), None)


def adjust(f, g, elo, cur, n_home, n_away):
    """The game's features with the Elo rating replaced by the roster-blended one (W0 roster at game 0, the carried
    Elo by BLEND_GAMES). f as is when there's no prior for either team."""
    if not cur or not cur.get("elo"):
        return f, False
    R = cur["elo"]
    h, a = str(g["home"]), str(g["away"])
    if h not in R or a not in R or n_home is None or n_away is None:
        return f, False
    t = sm._ts(g["start"])
    bh = blend(R[h], elo.rating(h, t), n_home)
    ba = blend(R[a], elo.rating(a, t), n_away)
    neutral = str(g.get("neutral")) == "1"
    pe = sm.p_home(bh, ba, elo.hfa, neutral)
    return {**f, "p_elo": pe, "elo": sm.logit(pe), "elo_pts": bh - ba + (0 if neutral else elo.hfa)}, True


BENCH_SAY = 3.0         # the card talks about a bench only when it's clearly good or bad (+/- 3 a 48 minutes)


def card_line(g, side, cur):
    """🏀 The card's roster line for an NBA side - only facts with numbers (the owner: never vague): the bench, how deep
    the coach plays, who's hot / in a slump, a minutes limit, a game-time decision. "" = nothing to say."""
    if not cur:
        return ""
    tid = str(g[side])
    if tid not in (cur.get("teams") or {}):
        return ""
    parts = []                                           # (10/21, the owner: "men 6-10 ... a 48 minutes" was jargon)
    nm = g[side + "_name"]
    b = (cur.get("bench") or {}).get(tid)
    if b is not None and abs(b) >= BENCH_SAY:
        parts.append(f"their bench outscored teams by {b:g} per 48 minutes last season - deep squad" if b > 0 else
                     f"their bench got outscored by {-b:g} per 48 minutes last season - thin squad")
    st = (cur.get("styles") or {}).get(tid)
    if st and st.get("depth"):
        parts.append(f"the coach plays {int(round(st['depth']))} guys real minutes")
    roster_pids = {p.get("pid") for p in cur["teams"][tid]}
    fm = cur.get("form") or {}
    for pid in [k for k in fm if k in roster_pids and fm[k]["tag"]][:2]:
        f = fm[pid]
        parts.append(f"{f['name']} {'is cooking' if f['tag'] == 'hot' else 'is in a slump'} - the team's {f['recent']:+g} "
                     f"per 48 with him on the floor lately, {f['usual']:+g} last season")
    fl = (cur.get("flags") or {}).get(tid) or {}
    if fl.get("restricted"):
        parts.append(f"{', '.join(fl['restricted'][:2])} on a minutes limit (about {RESTRICTED_MIN:g} tonight)")
    if fl.get("game_time"):
        parts.append(f"{', '.join(fl['game_time'][:2])} a game-time call")
    if not parts:
        return ""
    return f"🏀 {nm}: {' · '.join(parts)}."


FULL_SEASON = 60        # last season's record / point gap only off a full season on file (82 games; 60+ = we hold it)
ADD_MPG = 20.0          # "they added X" only for a real rotation man: 20+ minutes a night last season


def last_season(games, tid, before):
    """(W-L, points a game better than the other team) for an NBA team LAST regular season (the season before the
    one `before` falls in) - from the finals we hold, or None when we don't hold a full season. (10/21, the owner: the
    opening-week cards were empty - every team 0-1 - and the one fact that's always true then is last season.)"""
    want = season_of(before) - 1
    w = l = n = 0
    diff = 0.0
    tid = str(tid)
    mine = [g for g in games.values() if g.get("league") == "nba" and g.get("status") == "final"
            and str(g.get("stype")) == "2" and tid in (str(g.get("home")), str(g.get("away")))
            and season_of(g["start"]) == want]
    # the NBA Cup final (a neutral-site game in December, after the neutral-site semifinal) doesn't count in the
    # standings - ESPN files it as a regular-season game: a Cup finalist read 83 games (the Spurs "62-21"). The
    # semifinal counts; the finalist's SECOND neutral December game is the final and is skipped.
    cup = sorted((g for g in mine if str(g.get("neutral")) == "1" and g["start"][5:7] == "12"), key=lambda g: g["start"])
    skip = {cup[-1]["id"]} if len(cup) >= 2 else set()
    seen = set()
    for g in mine:
        if g["id"] in skip:
            continue
        key = (g["start"][:10], str(g.get("home")), str(g.get("away")))   # (the same game under two ids counts once)
        if key in seen:
            continue
        seen.add(key)
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError, KeyError):
            continue
        us, them = (hs, as_) if str(g["home"]) == tid else (as_, hs)
        n += 1
        diff += us - them
        w += us > them
        l += us < them
    if n < FULL_SEASON:
        return None
    return f"{w}-{l}", round(diff / n, 1)


def additions(cur, tid, names):
    """Who this team added since last season - rotation men (ADD_MPG+ minutes a night) whose box scores last season
    were for another team: [(name, minutes a night, that team's name)]. Checkable from the box scores alone."""
    if not cur or not cur.get("values"):
        return []
    tid = str(tid)
    out = []
    for p in (cur.get("teams") or {}).get(tid) or []:
        v = _lookup(cur["values"], p)
        if not v or (v.get("mpg") or 0) < ADD_MPG or not v.get("team") or str(v["team"]) == tid:
            continue
        frm = names.get(str(v["team"]))
        if frm:
            out.append((p.get("name") or v.get("name"), int(round(v["mpg"])), frm))
    return sorted(out, key=lambda x: -x[1])


def season_facts(g, side, cur, games):
    """The opening-weeks facts for an NBA side, as a dict: {"us": (W-L, diff), "them": (W-L, diff), "added": [...]}
    - last season's record and point gap for both teams, and who our side added. Empty values when we don't hold them."""
    other = "away" if side == "home" else "home"
    names = {}
    for x in games.values():
        if x.get("league") == "nba":
            names[str(x["home"])], names[str(x["away"])] = x.get("home_name", ""), x.get("away_name", "")
    return {"us": last_season(games, g[side], g["start"]), "them": last_season(games, g[other], g["start"]),
            "added": additions(cur, g[side], names)}


def _gap(d, k=0):
    """The point gap in words - four phrasings (k), so two cards never share the same four-word run (the dashboard's
    no-repeat memory blanks the numbers: 'outscored by _ a game' on every card would read as the same line)."""
    if d == 0:
        return "broke even on points"
    a = abs(d)
    up = [f"outscored teams by {a:g} a game", f"won by {a:g} points a night on average", f"beat teams by {a:g} per game",
          f"finished +{a:g} in point margin", f"put up {a:g} more points than they gave up a game",
          f"outscored the other side by {a:g} nightly", f"ran a +{a:g} scoring edge",
          f"came out {a:g} ahead on the scoreboard most nights"]
    dn = [f"got outscored by {a:g} a game", f"lost by {a:g} points a night on average", f"got beat by {a:g} per game",
          f"finished -{a:g} in point margin", f"gave up {a:g} more points than they scored a game",
          f"got outscored by the other side by {a:g} nightly", f"ran a -{a:g} scoring edge",
          f"came out {a:g} behind on the scoreboard most nights"]
    return (up if d > 0 else dn)[k % 8]


def season_line(g, side, cur, games):
    """🏀 Last season's facts on the card, early in the year - only when they back our side (our point gap better than
    theirs), both records said, plus the biggest man we added: "" when they don't or we don't hold them."""
    f = season_facts(g, side, cur, games)
    us, them = g[side + "_name"], g[("away" if side == "home" else "home") + "_name"]
    if not f["us"] or not f["them"] or f["us"][1] <= f["them"][1]:
        return ""
    (ru, du), (rt, dt) = f["us"], f["them"]
    line = f"🏀 Last season {us} went {ru} and {_gap(du)}; {them} went {rt} and {_gap(dt)}."
    if f["added"]:
        nm, mpg, frm = f["added"][0]
        line += f" {us} added {nm} ({mpg} minutes a night for the {frm} last year)."
    return line


_SCALE = {}


def scale_for(games, season, values, rows):
    """Margin a game per unit of strength, fitted on `season` (its players at their minutes, its results)."""
    if season not in _SCALE:
        margins = season_margins(games, season)
        strengths = {t: team_strength(played_roster(rows, season, t, first_n=82), values) for t in margins}
        _SCALE[season] = fit_scale(strengths, margins)
    return _SCALE[season]


# ---------------------------------------------------------------- 5. who matters (the 10/22 favorite study)
def top_men(cur, tid, k):
    """The team's top-k men by minutes (last season's values, on tonight's roster): [(name, pid)]."""
    if not cur or str(tid) not in (cur.get("teams") or {}) or not cur.get("values"):
        return []
    ranked = []
    for p in cur["teams"][str(tid)]:
        v = _lookup(cur["values"], p)
        if v and (v.get("mpg") or 0) > 0:
            ranked.append((v["mpg"], p.get("name"), str(p.get("pid") or "")))
    return [(n, pid) for _, n, pid in sorted(ranked, reverse=True)[:k]]


def top_out(cur, tid, k=2):
    """Names of the team's top-k men out / doubtful tonight (the injury report through flags())."""
    out = set((((cur or {}).get("flags") or {}).get(str(tid)) or {}).get("out") or [])
    return [n for n, _ in top_men(cur, tid, k) if n in out]


_RECENT = {}


def returning(cur, tid, start, k=5, missed=2, rows=None):
    """Names of the team's top-k men back tonight after missing its last `missed` games this season (not in those box
    scores, not out tonight). [] when this season's box scores don't cover the team's last games."""
    season = season_of(start)
    if rows is None:
        if season not in _RECENT:
            _RECENT.clear()
            _RECENT[season] = _rows(season)
        rows = _RECENT[season]
    games = sorted({(r["start"], r["gid"]) for r in rows if r["team"] == str(tid) and r["start"] < start})[-missed:]
    if len(games) < missed:
        return []
    keep = {gid for _, gid in games}
    played = {r["pid"] for r in rows if r["gid"] in keep and r["team"] == str(tid)}
    named = {_nm(r["player"]) for r in rows if r["gid"] in keep and r["team"] == str(tid)}
    out_now = set((((cur or {}).get("flags") or {}).get(str(tid)) or {}).get("out") or [])
    return [n for n, pid in top_men(cur, tid, k) if n not in out_now and pid not in played and _nm(n) not in named]


def heavy_last(tid, start, heavy=38.0, rows=None, ot=None):
    """(10/28 NBA dog studies - a LEAD for the tracker, never a weight) True when the team's top 3 men by minutes
    averaged `heavy`+ minutes in its LAST game this season and that game was not overtime (the OT fact is the
    built weight's); None when this season's box scores don't hold the team's last game. `ot` = the last game's
    overtime flag when the caller knows it; without it a 53+ minute man marks an overtime game."""
    season = season_of(start)
    if rows is None:
        if season not in _RECENT:
            _RECENT.clear()
            _RECENT[season] = _rows(season)
        rows = _RECENT[season]
    last = max(((r["start"], r["gid"]) for r in rows if r["team"] == str(tid) and r["start"] < start), default=None)
    if last is None:
        return None
    mins = []
    for r in rows:
        if r["gid"] == last[1] and r["team"] == str(tid):
            try:
                mins.append(float(json.loads(r.get("stats") or "{}").get("minutes") or 0))
            except (ValueError, TypeError):
                continue
    mins.sort(reverse=True)
    if len(mins) < 3:
        return None
    if ot is None:
        ot = mins[0] > 52
    return (not ot) and sum(mins[:3]) / 3 >= heavy
