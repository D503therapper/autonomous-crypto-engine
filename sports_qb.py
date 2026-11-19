"""🏈 WHO STARTS AT QUARTERBACK (11/16 FABLE - EVERY FACT TRUE; the owner, 11/15: "These fucking mistakes ... false
information and outdated bullshit is costing people a lot of money").

The 11/15 Packers Lock named Carson Wentz as the Vikings' quarterback off his one fill-in start - Kirk Cousins started.
The same day's Cardinals card gave Gardner Minshew II's numbers as the Cardinals' QB and, two lines down, said he was
out - Carson Beck started. The engine's quarterback was always "the top passer of the last box score". The 11/15 night
fix (sports_players.qb_settled) made a QB CHANGE unknown. This is the rest of it: a second source for who starts.

THE SOURCE: ESPN's own team depth chart (site.api.espn.com .../teams/{id}/depthcharts - the same public API the
scores, box scores and injury feed come from). A plain request under our own name (sports_http.UA), never a disguise;
when it answers empty or refuses, it goes QUIET in source_status.json ("espn_depth_nfl" / "espn_depth_ncaaf") and the
engine falls back to the box-score rule - never worked around.

THE CALL (call() - one function for the card, the key-player weight and the injury report):
  a quarterback is NAMED only when two things agree -
    * the depth chart's first quarterback who isn't ruled out (the injury report), AND
    * the box scores: he started the team's last game.
      - the same man started the last 2 (settled) and the chart has him first       -> named ("chart + box")
      - a NEW man started the last game and the chart has him first now             -> named ("chart + last start":
        the change is confirmed - before today a change was only ever silence)
  anything else is UNKNOWN - no QB line, no QB edge in the read, never a guess:
    * the chart's man is not the man who started last (a benching, a trade, a starter coming back)   "chart disagrees"
    * the man is on the report as out / doubtful                                                     "out"
    * the man is questionable / a game-time call                                                     "questionable"
    * the last two starters differ and there's no chart to settle it                                 "change"
  No chart on file (the source is quiet, a college team ESPN keeps no chart for): the 11/15 rule - the same man in the
  last 2 box scores, not on the out list.

THE CHART ALONE never names a man yet (QB_CHART_ALONE = False): a quarterback the chart lists first who did NOT start
the last game (Cousins the week he arrived) stays unknown until the chart has a record. Every call is logged with what
the chart said and, once the game is played, who started (data/sports/qb_calls.json - record()); grade() reads how
often the chart's first healthy man was the starter. Judge it at 50 graded sides: 90%+ right = it can name a man alone
(the owner's / the next session's call).

"9999" in QB_CHART_FROM = the 11/15 rule only."""
import json
import os
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import sports_data as sd
import sports_http as sh

QB_CHART_FROM = "2026-11-16"     # games from this date read the chart (sports_players.qb_for)
QB_CHART_ALONE = False           # the chart's man with no box score behind him is never named (see the top)
DEPTH = "https://site.api.espn.com/apis/site/v2/sports/{path}/teams/{tid}/depthcharts"
PATH = os.path.join(sd.DATA, "qb_depth.json")
CALLS = os.path.join(sd.DATA, "qb_calls.json")
LEAGUES = ("nfl", "ncaaf")
FRESH_H = 36                     # a chart older than this is no chart (back to the box-score rule)
REFRESH_H = 5                    # a team's chart is re-read at most this often
AHEAD_DAYS = {"nfl": 8, "ncaaf": 3}   # whose charts to read: teams with a game inside this many days
QUIET_AFTER = 6                  # this many reads in a row with no chart in them: the source is quiet for this run
#                                  (ESPN keeps no chart for most college teams - never hammer it)
ON = [True]                      # (tests turn it off - never a real request from a test)
INJ = {}                         # {league: the injury dict of this run} - set by note_injuries (sports.post_board)
_CACHE = {}


def _nm(x):
    import sports_absences
    return sports_absences._nm(x)


def same(a, b):
    """Two spellings of one man ('J. Knuth' ~ 'Jacob Knuth', 'Gardner Minshew II' ~ 'Gardner Minshew')."""
    a, b = _nm(a), _nm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    wa, wb = a.split(), b.split()
    if len(wa) < 2 or len(wb) < 2 or wa[-1] != wb[-1]:
        return False
    k = 1 if min(len(wa[0]), len(wb[0])) == 1 else 2
    return wa[0][:k] == wb[0][:k]


# ---------------------------------------------------------------- the depth chart
def _ath_name(a):
    if not isinstance(a, dict):
        return None
    inner = a.get("athlete") if isinstance(a.get("athlete"), dict) else {}
    return a.get("displayName") or a.get("fullName") or inner.get("displayName") or inner.get("fullName") or None


def _rank(a, i):
    for k in ("rank", "slot", "depth", "order"):
        try:
            return int(a.get(k))
        except (TypeError, ValueError, AttributeError):
            continue
    return i + 1


def parse_depth(payload):
    """ESPN's depth chart -> the quarterbacks in chart order (['Kirk Cousins', 'Carson Wentz', ...]), [] when the
    payload carries no QB list. Reads the shapes ESPN serves: {'depthchart': [{'positions': {'qb': {'athletes': [...]}}}]}
    (the site API) and {'items': [...]} with the same positions block. Anything else = [] (unknown, never a guess)."""
    if not isinstance(payload, dict):
        return []
    charts = payload.get("depthchart") or payload.get("depthCharts") or payload.get("items") or []
    if isinstance(charts, dict):
        charts = [charts]
    for ch in charts:
        pos = (ch or {}).get("positions") if isinstance(ch, dict) else None
        if isinstance(pos, list):                            # ([{position: {abbreviation: 'QB'}, athletes: [...]}])
            pos = {str(((p.get("position") or {}).get("abbreviation") or p.get("abbreviation") or "")).lower(): p
                   for p in pos if isinstance(p, dict)}
        if not isinstance(pos, dict):
            continue
        qb = next((v for k, v in pos.items() if str(k).lower() == "qb"), None)
        if not isinstance(qb, dict):
            continue
        aths = [a for a in qb.get("athletes") or [] if _ath_name(a)]
        aths = [a for _, _, a in sorted((_rank(a, i), i, a) for i, a in enumerate(aths))]
        names = []
        for a in aths:
            n = _ath_name(a)
            if n and n not in names:
                names.append(n)
        if names:
            return names
    return []


FIRST_SPOTS = ("lt", "lg", "c", "rg", "rt", "te", "lcb", "rcb", "ss", "fs", "lde", "rde", "ldt", "rdt", "nt", "de", "dt",
               "wlb", "mlb", "slb", "lilb", "rilb", "lolb", "rolb")
_FIRST = {}                      # (league, team id) -> {spot: the first-string man} off the chart just read


def parse_first(payload):
    """🧱 11/19 (sports_starters - the men a box score can't show): ESPN's depth chart -> {spot: the FIRST man listed}
    for the lines, the secondary and the front seven ({'lt': 'Bernhard Raimann', 'lcb': ...}). Reads the same shapes as
    parse_depth, every formation block; {} when the payload carries none (unknown, never a guess)."""
    if not isinstance(payload, dict):
        return {}
    charts = payload.get("depthchart") or payload.get("depthCharts") or payload.get("items") or []
    if isinstance(charts, dict):
        charts = [charts]
    out = {}
    for ch in charts:
        pos = (ch or {}).get("positions") if isinstance(ch, dict) else None
        if isinstance(pos, list):
            pos = {str(((p.get("position") or {}).get("abbreviation") or p.get("abbreviation") or "")).lower(): p
                   for p in pos if isinstance(p, dict)}
        if not isinstance(pos, dict):
            continue
        for k, v in pos.items():
            k = str(k).lower()
            if k not in FIRST_SPOTS or k in out or not isinstance(v, dict):
                continue
            aths = [a for a in v.get("athletes") or [] if _ath_name(a)]
            aths = [a for _, _, a in sorted((_rank(a, i), i, a) for i, a in enumerate(aths))]
            if aths:
                out[k] = _ath_name(aths[0])
    return out


def fetch_depth(league, tid, get=None):
    """One team's chart: [quarterbacks in order], [] = ESPN has no QB chart for it; raises on a failed read. The same
    payload's first string at the other spots is kept in _FIRST (sync saves it as "first")."""
    url = DEPTH.format(path=sd.LEAGUES[league][0], tid=tid)
    if get is not None:
        payload = get(url)
    else:
        with urllib.request.urlopen(urllib.request.Request(url, headers=sh.JSON_HDR), timeout=12) as r:
            payload = json.load(r)
    try:
        _FIRST[(league, str(tid))] = parse_first(payload)
    except Exception:                                        # noqa: BLE001 - the QB read never fails on it
        _FIRST.pop((league, str(tid)), None)
    return parse_depth(payload)


def load():
    if "d" not in _CACHE:
        try:
            with open(PATH) as f:
                _CACHE["d"] = json.load(f)
        except (OSError, ValueError):
            _CACHE["d"] = {}
    return _CACHE["d"]


def _iso(t):
    return t.strftime("%Y-%m-%dT%H:%MZ")


def _t(iso):
    return datetime.strptime(str(iso)[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def sync(games, now=None, get=None, budget_s=40, workers=6):
    """Read the depth chart of every NFL / college team with a game coming (AHEAD_DAYS), a team at most every REFRESH_H
    hours, and save qb_depth.json. Fails soft: a failed or empty read leaves the last chart to go stale on its own
    (FRESH_H) and says so in source_status.json. -> {league: charts read this run}."""
    now = now or datetime.now(timezone.utc)
    if not ON[0] and get is None:
        return {}
    d = load()
    got = {}
    deadline = time.time() + budget_s
    for lg in LEAGUES:
        box = d.setdefault(lg, {})
        want = []
        for g in games.values():
            if g.get("league") != lg or g.get("status") != "pre" or not g.get("start"):
                continue
            try:
                ahead = (_t(g["start"]) - now).total_seconds() / 86400
            except ValueError:
                continue
            if not -0.2 <= ahead <= AHEAD_DAYS[lg]:
                continue
            if lg == "ncaaf" and str(g.get("ml_home", "")) == "" and str(g.get("spread_home", "")) == "":
                continue                                     # (college: priced games only - the ones the board can pick)
            for side in ("home", "away"):
                tid = str(g[side])
                at = (box.get(tid) or {}).get("at")
                if tid not in want and (not at or (now - _t(at)).total_seconds() > REFRESH_H * 3600):
                    want.append(tid)
        if not want:
            continue
        state = {"empty_run": 0, "ok": 0, "empty": 0, "err": None, "quiet": False}
        lock = threading.Lock()

        def one(tid, lg=lg, state=state, lock=lock):
            if state["quiet"] or time.time() > deadline:
                return tid, None
            try:
                names = fetch_depth(lg, tid, get)
            except Exception as e:                           # noqa: BLE001 - a failed read is unknown, never a guess
                state["err"] = sh.err_text(e)
                names = None
            with lock:
                if names:
                    state["ok"] += 1
                    state["empty_run"] = 0
                else:
                    state["empty"] += names is not None
                    state["empty_run"] += 1
                    if state["empty_run"] >= QUIET_AFTER and not state["ok"]:
                        state["quiet"] = True                # (nothing but empties: stop asking this run)
            return tid, names
        with ThreadPoolExecutor(1 if get is not None else workers) as ex:
            for tid, names in ex.map(one, want):
                if names:
                    box[tid] = {"qbs": names[:4], "at": _iso(now)}
                elif names is not None:                      # ESPN answered with no chart: remember we asked
                    box[tid] = {"qbs": [], "at": _iso(now)}
                if names is not None and _FIRST.get((lg, str(tid))):   # 🧱 11/19: the first string at the other spots
                    box[tid]["first"] = _FIRST[(lg, str(tid))]         # (sports_starters' fallback - no extra request)
        got[lg] = state["ok"]
        sh.note(f"espn_depth_{lg}", state["ok"] > 0, n=state["ok"], err=state["err"],
                how="plain request - the team depth charts (who starts at QB)"
                + ("" if state["ok"] else f"; no chart came back ({state['empty']} empty) - the QB falls back to the "
                                          "box-score rule, never a guess"))
    d["seen"] = _iso(now)
    try:
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        with open(PATH + ".tmp", "w") as f:
            json.dump(d, f, indent=1, sort_keys=True)
        os.replace(PATH + ".tmp", PATH)
    except OSError:
        pass
    _CACHE["d"] = d
    return got


def chart(league, tid, now=None):
    """The team's quarterbacks in depth-chart order when we hold a FRESH chart (FRESH_H), else None (no chart)."""
    v = (load().get(league) or {}).get(str(tid))
    if not v or not v.get("qbs") or not v.get("at"):
        return None
    now = now or datetime.now(timezone.utc)
    try:
        if (now - _t(v["at"])).total_seconds() > FRESH_H * 3600:
            return None
    except ValueError:
        return None
    return list(v["qbs"])


# ---------------------------------------------------------------- the injury report's word on a man
def note_injuries(injuries):
    """This run's injury reports ({league: {team: [(name, pos, status)]}}) - call() reads who's out / questionable. A
    league whose report isn't in hand (missing / None - it didn't load) is UNKNOWN again, never yesterday's list."""
    for lg in LEAGUES:
        if injuries and injuries.get(lg) is not None:
            INJ[lg] = injuries[lg]
        else:
            INJ.pop(lg, None)


def status_of(league, tid, name, team_name=""):
    """'out' / 'unsure' / '' (not listed) / None (no report this run) for one man."""
    inj = INJ.get(league)
    if inj is None:
        return None
    for r in sd._team_rows(inj, str(tid), team_name):
        if same(r[0], name):
            s = str(r[2]).lower()
            if any(w in s for w in sd.SHORT_TERM + sd.LONG_OUT):
                return "out"
            if any(w in s for w in sd.UNSURE):
                return "unsure"
    return ""


# ---------------------------------------------------------------- the call
def _last_starters(rows, team, before, n=2):
    names, seen = [], set()
    for r in reversed(rows):
        if str(r["team"]) == str(team) and r["start"] < before and r.get("gid") not in seen:
            seen.add(r.get("gid"))
            names.append(r["player"])
            if len(names) >= n:
                break
    return names


def call(rows, league, team, before, depth="auto", now=None, team_name="", status=None):
    """Who starts at QB for `team` in a game starting `before`: {"name": the man or None, "how": why, "box": the last
    starters (newest first), "chart": the chart's QBs or None}. `depth`: the chart's list, None (no chart) or "auto" (the
    saved one). `status`: name -> 'out' / 'unsure' / '' / None (default: this run's injury report)."""
    last = _last_starters(rows, team, before)
    ch = chart(league, team, now) if depth == "auto" else (list(depth) if depth else None)
    st = status or (lambda nm: status_of(league, team, nm, team_name))
    out = {"name": None, "how": "", "box": last, "chart": ch}
    if not last:
        out["how"] = "no box score"
        return out
    settled = last[0] if len(set(last)) == 1 else None
    if ch:
        top = next((q for q in ch if st(q) != "out"), None)
        out["chart_top"] = top
        if top is None:
            out["how"] = "out"                               # every chart QB is ruled out: unknown
            return out
        if st(top) == "unsure":
            out["how"] = "questionable"
            return out
        if same(top, last[0]):                               # the chart's man started the last game
            out["name"], out["how"] = last[0], "chart + box" if settled else "chart + last start"
            return out
        out["how"] = "chart disagrees"                       # a benching, a trade, a starter back: unknown until he
        if QB_CHART_ALONE:                                   # has a start behind him (QB_CHART_ALONE - not yet)
            out["name"], out["how"] = top, "chart alone"
        return out
    if not settled:
        out["how"] = "change"
        return out
    s = st(settled)
    if s == "out":
        out["how"] = "out"
    elif s == "unsure":
        out["how"] = "questionable"
    else:
        out["name"], out["how"] = settled, "box"
    return out


def qb_for(rows, league, team, before, team_name=""):
    """The name the card / the key-player weight may use, or None (unknown)."""
    return call(rows, league, team, before, team_name=team_name)["name"]


def role(rows, league, team, name, before, n=5, need=3):
    """What a QB on the injury report IS to his team, for the report's KEY tag: 'starter' (he started the last game),
    'regular starter' (he sat the last game but started `need`+ of the last `n` - Kyler Murray the week Wentz filled in,
    tagged a 'backup'), 'chart starter' (the depth chart lists him first), else 'backup'. None = no box scores."""
    names, seen = [], set()
    for r in reversed(rows):
        if str(r["team"]) == str(team) and r["start"] < before and r.get("gid") not in seen:
            seen.add(r.get("gid"))
            names.append(r["player"])
            if len(names) >= n:
                break
    if not names:
        return None
    if same(names[0], name):
        return "starter"
    if sum(same(x, name) for x in names) >= need:
        return "regular starter"
    ch = chart(league, team)
    if ch and same(ch[0], name):
        return "chart starter"
    return "backup"


# ---------------------------------------------------------------- the record: was the call right?
def record(games, rows_by_league, now=None, keep=600):
    """Log today's calls (qb_calls.json: per game and side - the last starters, the chart, the call) and fill in who
    actually started once the box score is in. The chart earns trust here before it ever names a man alone."""
    now = now or datetime.now(timezone.utc)
    try:
        with open(CALLS) as f:
            log = json.load(f)
    except (OSError, ValueError):
        log = {}
    changed = False
    for g in games.values():
        lg = g.get("league")
        if lg not in LEAGUES or not g.get("start"):
            continue
        rows = rows_by_league.get(lg) or []
        if g.get("status") == "pre":
            try:
                ahead = (_t(g["start"]) - now).total_seconds() / 3600
            except ValueError:
                continue
            if not 0 <= ahead <= 30:
                continue
            for side in ("home", "away"):
                c = call(rows, lg, g[side], g["start"], now=now, team_name=g.get(side + "_name") or "")
                if c["chart"] is None and c["how"] in ("box", "change", "no box score"):
                    continue                                 # (no chart: nothing new to judge)
                cur = {"team": g.get(side + "_name"), "start": g["start"], "box": c["box"], "chart": c["chart"],
                       "chart_top": c.get("chart_top"), "called": c["name"], "how": c["how"], "at": _iso(now)}
                if (log.get(g["id"]) or {}).get(side, {}).get("called") != cur["called"] \
                        or (log.get(g["id"]) or {}).get(side, {}).get("chart") != cur["chart"] or side not in (log.get(g["id"]) or {}):
                    log.setdefault(g["id"], {})[side] = cur
                    changed = True
        elif g.get("status") == "final" and g["id"] in log:
            for side, v in log[g["id"]].items():
                if v.get("actual"):
                    continue
                act = next((r["player"] for r in reversed(rows) if r.get("gid") == g["id"] and str(r["team"]) == str(g[side])), None)
                if act:
                    v["actual"] = act
                    changed = True
    if changed:
        log = dict(sorted(log.items(), key=lambda kv: min(v.get("start", "") for v in kv[1].values()))[-keep:])
        try:
            with open(CALLS + ".tmp", "w") as f:
                json.dump(log, f, indent=1, sort_keys=True)
            os.replace(CALLS + ".tmp", CALLS)
        except OSError:
            pass
    return log


def grade(log=None):
    """{"called": [right, n], "chart_top": [right, n], "last_starter": [right, n]} over the graded sides."""
    if log is None:
        try:
            with open(CALLS) as f:
                log = json.load(f)
        except (OSError, ValueError):
            log = {}
    out = {"called": [0, 0], "chart_top": [0, 0], "last_starter": [0, 0]}
    for v in log.values():
        for s in v.values():
            act = s.get("actual")
            if not act:
                continue
            for k, nm in (("called", s.get("called")), ("chart_top", s.get("chart_top")),
                          ("last_starter", (s.get("box") or [None])[0])):
                if nm:
                    out[k][0] += same(nm, act)
                    out[k][1] += 1
    return out


def stale_days(now=None):
    """How old the saved charts are, for the hourly bug check: (charts held, the oldest 'seen' in hours) or None."""
    d = load()
    if not d.get("seen"):
        return None
    now = now or datetime.now(timezone.utc)
    return (sum(1 for lg in LEAGUES for v in (d.get(lg) or {}).values() if v.get("qbs")),
            round((now - _t(d["seen"])).total_seconds() / 3600, 1))

