"""Sports data: games, final scores and moneyline odds from ESPN's public scoreboard API (no key).
Games are kept in data/sports/games/<league>/<YYYY-MM>.csv so an hourly commit only rewrites the
current month's file."""
import csv
import glob
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

ESPN = "https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={day}&limit=1000{extra}"
DATA = "data/sports"

# league key -> ESPN path, extra query, display name, emoji
LEAGUES = {
    "nfl": ("football/nfl", "", "NFL", "🏈"),
    "ncaaf": ("football/college-football", "&groups=80", "College Football", "🏈"),
    "nba": ("basketball/nba", "", "NBA", "🏀"),
    "mlb": ("baseball/mlb", "", "MLB", "⚾"),
    "nhl": ("hockey/nhl", "", "NHL", "🏒"),
}

FIELDS = ["id", "league", "start", "status", "home", "away", "home_name", "away_name",
          "home_score", "away_score", "ml_home", "ml_away", "odds_time", "neutral",
          "ml_home_open", "ml_away_open", "spread_home", "spread_home_odds", "spread_away_odds",
          "inj_home", "inj_away"]
ODDS = ["ml_home", "ml_away", "spread_home", "spread_home_odds", "spread_away_odds"]


# ---------------------------------------------------------------- odds helpers
def parse_american(x):
    """'+150' / '-175' / 150 / 'EVEN' -> int american odds, or None."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return int(x) if abs(x) >= 100 else None
    s = str(x).strip().upper().replace("−", "-")
    if s in ("EVEN", "EV", "PK"):
        return 100
    try:
        v = int(float(s))
    except ValueError:
        return None
    return v if abs(v) >= 100 else None


def decimal(american):
    return 1 + (american / 100 if american > 0 else 100 / -american)


def implied(american):
    return 1 / decimal(american)


def no_vig(ml_home, ml_away):
    """Market's fair home-win probability with the bookmaker margin removed."""
    ph, pa = implied(ml_home), implied(ml_away)
    return ph / (ph + pa)


# ---------------------------------------------------------------- ESPN parsing
def _num(x):
    try:
        return float(str(x).replace("−", "-").replace("+", ""))
    except (TypeError, ValueError):
        return None


def _odds(comp):
    """Moneylines (current + opening), home spread line and its prices from a competition's odds.
    ESPN has shipped two shapes: flat homeTeamOdds.moneyLine / spread, and nested
    moneyline|pointSpread.{home,away}.{open,close,current}."""
    out = {"ml_home": None, "ml_away": None, "ml_home_open": None, "ml_away_open": None,
           "spread_home": None, "spread_home_odds": None, "spread_away_odds": None}
    for o in comp.get("odds") or []:
        ho, ao = o.get("homeTeamOdds") or {}, o.get("awayTeamOdds") or {}
        ml, ps = o.get("moneyline") or {}, o.get("pointSpread") or {}

        def nested(block, side, key, keys=("close", "current", "open"), parse=parse_american):
            d = block.get(side) or {}
            for k in keys:
                v = parse((d.get(k) or {}).get(key))
                if v is not None:
                    return v
            return None
        h = parse_american(ho.get("moneyLine"))
        a = parse_american(ao.get("moneyLine"))
        if h is None or a is None:
            h, a = nested(ml, "home", "odds"), nested(ml, "away", "odds")
        if h is None or a is None:
            continue
        out["ml_home"], out["ml_away"] = h, a
        out["ml_home_open"] = parse_american((ho.get("open") or {}).get("moneyLine")) or nested(ml, "home", "odds", ("open",))
        out["ml_away_open"] = parse_american((ao.get("open") or {}).get("moneyLine")) or nested(ml, "away", "odds", ("open",))
        line = nested(ps, "home", "line", parse=_num)
        if line is None:
            line = _num(o.get("spread"))
        if line is not None and abs(line) < 60:
            out["spread_home"] = line
            out["spread_home_odds"] = parse_american(ho.get("spreadOdds")) or nested(ps, "home", "odds") or -110
            out["spread_away_odds"] = parse_american(ao.get("spreadOdds")) or nested(ps, "away", "odds") or -110
        return out
    return out


def parse_scoreboard(league, payload):
    """ESPN scoreboard JSON -> list of game dicts (FIELDS)."""
    out = []
    for ev in payload.get("events") or []:
        comps = ev.get("competitions") or []
        if not comps:
            continue
        comp = comps[0]
        teams = {c.get("homeAway"): c for c in comp.get("competitors") or []}
        if "home" not in teams or "away" not in teams:
            continue
        st = ((comp.get("status") or ev.get("status") or {}).get("type") or {})
        state, name = st.get("state", ""), st.get("name", "")
        if name in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED", "STATUS_FORFEIT"):
            status = "void"
        elif st.get("completed") or state == "post":
            status = "final"
        elif state == "in":
            status = "live"
        else:
            status = "pre"

        def team(side):
            t = teams[side].get("team") or {}
            return (str(t.get("id") or t.get("abbreviation") or t.get("displayName")),
                    t.get("shortDisplayName") or t.get("displayName") or t.get("abbreviation") or "?")

        def score(side):
            s = teams[side].get("score")
            if isinstance(s, dict):
                s = s.get("value", s.get("displayValue"))
            try:
                return int(float(s))
            except (TypeError, ValueError):
                return ""
        (hid, hname), (aid, aname) = team("home"), team("away")
        od = _odds(comp)
        out.append({
            "id": f"{league}:{ev.get('id')}", "league": league, "start": ev.get("date") or comp.get("date", ""),
            "status": status, "home": hid, "away": aid, "home_name": hname, "away_name": aname,
            "home_score": score("home") if status == "final" else "", "away_score": score("away") if status == "final" else "",
            "odds_time": "", "neutral": 1 if comp.get("neutralSite") else 0, "inj_home": "", "inj_away": "",
            **{k: ("" if v is None else v) for k, v in od.items()},
        })
    return out


def fetch_day(league, day, retries=3):
    path, extra, _, _ = LEAGUES[league]
    url = ESPN.format(path=path, day=day.strftime("%Y%m%d"), extra=extra)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (d503-sports-engine)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return parse_scoreboard(league, json.load(r))
        except Exception as e:                       # noqa: BLE001 - network: retry, then give up on this day
            if i == retries - 1:
                print(f"   {league} {day:%Y-%m-%d}: {str(e)[:120]}")
                return None
            time.sleep(1.5 * (i + 1))


# ---------------------------------------------------------------- storage
def _month_file(league, start):
    return os.path.join(DATA, "games", league, f"{start[:7]}.csv")


def load_games(league=None):
    """{game id: game} for one league (or all)."""
    games = {}
    pattern = os.path.join(DATA, "games", league or "*", "*.csv")
    for p in sorted(glob.glob(pattern)):
        with open(p) as f:
            for row in csv.DictReader(f):
                games[row["id"]] = row
    return games


def save_games(games):
    """Write every month file that holds these games (other months untouched)."""
    by_file = {}
    for g in games.values():
        if g.get("start"):
            by_file.setdefault(_month_file(g["league"], g["start"]), []).append(g)
    for p, rows in by_file.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        rows.sort(key=lambda r: (r["start"], r["id"]))
        tmp = p + ".tmp"
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, p)


def merge(old, new, now_iso):
    """Update a stored game with a fresh read. Pre-game odds are kept once the game starts (ESPN often
    drops them), so the last odds seen before the start serve as the closing line. The first odds
    ever seen stand in for the opening line when ESPN doesn't give one (for line movement)."""
    g = dict(old or new)
    if old is not None:
        for k in ("start", "status", "home_name", "away_name", "home_score", "away_score", "neutral"):
            g[k] = new[k]
    has = new["ml_home"] != "" and new["ml_away"] != ""
    if has and (new["status"] == "pre" or old is None or old.get("ml_home", "") == ""):
        for k in ODDS:
            if new.get(k, "") != "" or k == "spread_home":
                g[k] = new.get(k, "")
        if new["status"] == "pre":
            g["odds_time"] = now_iso
    for side in ("home", "away"):
        if g.get(f"ml_{side}_open", "") == "":
            g[f"ml_{side}_open"] = new.get(f"ml_{side}_open", "") or g.get(f"ml_{side}", "")
    return g


def sync(state, backfill_days=550, ahead_days=2, max_days=600, workers=8):
    """Refresh every league: re-read the last few days + next few, and backfill history on first run.
    Returns (games dict, number of API calls, number of failures)."""
    today = datetime.now(timezone.utc).date()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    games = load_games()
    jobs = []
    for lg in LEAGUES:
        synced = state.setdefault("synced", {}).get(lg)
        start = (datetime.strptime(synced, "%Y-%m-%d").date() - timedelta(days=3)) if synced \
            else today - timedelta(days=backfill_days)
        start = max(start, today - timedelta(days=max_days))
        d = start
        while d <= today + timedelta(days=ahead_days):
            jobs.append((lg, d))
            d += timedelta(days=1)
    fails = {}
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(lambda j: (j, fetch_day(*j)), jobs))
    for (lg, d), rows in results:
        if rows is None:
            fails[lg] = min(fails.get(lg, d), d)
            continue
        for r in rows:
            games[r["id"]] = merge(games.get(r["id"]), r, now_iso)
    for lg in LEAGUES:
        # next run starts from the first failed day, else from today
        upto = fails.get(lg, today + timedelta(days=1)) - timedelta(days=1)
        if upto >= today - timedelta(days=max_days):
            state["synced"][lg] = min(upto, today).strftime("%Y-%m-%d")
    save_games(games)
    return games, len(jobs), sum(1 for _, r in results if r is None)


# ---------------------------------------------------------------- injuries
SHORT_TERM = ("out", "doubtful")       # long-term IR is already priced into the ratings


def fetch_injuries(league):
    """{team id or name: [(player, position, status)]} for players listed Out / Doubtful."""
    path = LEAGUES[league][0]
    url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/injuries"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (d503-sports-engine)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return parse_injuries(json.load(r))
    except Exception as e:                           # noqa: BLE001
        print(f"   {league} injuries: {str(e)[:120]}")
        return None


def parse_injuries(payload):
    out = {}
    for t in payload.get("injuries") or []:
        rows = []
        for i in t.get("injuries") or []:
            status = str(i.get("status") or (i.get("type") or {}).get("description") or "").lower()
            if not any(s in status for s in SHORT_TERM):
                continue
            a = i.get("athlete") or {}
            rows.append((a.get("displayName") or "?", (a.get("position") or {}).get("abbreviation") or "",
                         status.title()))
        for key in (str(t.get("id") or ""), t.get("displayName") or ""):
            if key:
                out[key] = rows
    return out


def team_injuries(inj, team_id, team_name):
    if not inj:
        return []
    if team_id in inj:
        return inj[team_id]
    for k, v in inj.items():
        if team_name and not k.isdigit() and (k.endswith(" " + team_name) or k == team_name):
            return v
    return []
