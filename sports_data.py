"""Sports data: games, final scores and moneyline odds from ESPN's public scoreboard API (no key).
Games are kept in data/sports/games/<league>/<YYYY-MM>.csv so an hourly commit only rewrites the
current month's file."""
import csv
import glob
import json
import os
import threading
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
    "ncaab": ("basketball/mens-college-basketball", "&groups=50", "College Basketball", "🏀"),   # men's D1 only
}

ERRORS = []      # failed calls this run (only the first few are printed)
FIELDS = ["id", "league", "start", "status", "home", "away", "home_name", "away_name",
          "home_score", "away_score", "ml_home", "ml_away", "odds_time", "neutral",
          "ml_home_open", "ml_away_open", "spread_home", "spread_home_odds", "spread_away_odds",
          "inj_home", "inj_away", "sp_home", "sp_away", "stype", "country", "intl", "city", "state", "indoor",
          "elev", "wx_temp", "wx_wind", "wx_rain", "tzo", "ls_home", "ls_away",
          "h1_ml_home", "h1_ml_away", "h1_spread_home", "h1_spread_home_odds", "h1_spread_away_odds",
          "total", "over_odds", "under_odds"]
REAL = ("2", "3", "?")          # regular season + playoffs; preseason / spring training / all-star games don't count
ODDS = ["ml_home", "ml_away", "spread_home", "spread_home_odds", "spread_away_odds"]


# ---------------------------------------------------------------- 🔔 live bet alerts
def _push_key():
    """The engine's key for the Worker's /push (both sides make it from the Cloudflare secrets the repo already has;
    never printed, never stored)."""
    import hashlib
    a, t = os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), os.environ.get("CLOUDFLARE_API_TOKEN", "")
    return hashlib.sha256(f"d503-push|{a}|{t}".encode()).hexdigest() if a and t else ""


def web_push(ntfy_raw, title=None, body=None):
    """After an ntfy post: hand its message id to the Worker's /push (from ask_url.txt) so the dashboard's native
    Web Push alerts ring too. The Worker looks the id up on ntfy itself, so no secret is needed. Runs in its own
    thread with a 5s timeout: never blocks, never raises (errors are logged). Returns the thread (tests join it)."""
    key = _push_key()
    try:
        nid = json.loads(ntfy_raw or b"{}").get("id") if ntfy_raw else None
        with open(os.path.join(DATA, "ask_url.txt")) as f:
            url = f.read().strip().rstrip("/")
    except Exception as e:                                   # noqa: BLE001 - no id / no Worker: ntfy still went out
        print(f"   web push skipped: {str(e)[:60]}")
        return None
    if not url.startswith("https://") or not (nid or (key and title)):
        return None
    # straight to the Worker with the engine's key (no ntfy lookup - Cloudflare can be blocked from ntfy); else the id
    payload = {"key": key, "title": title, "body": body or ""} if key and title else {"ntfy_id": nid}

    def go():
        req = urllib.request.Request(f"{url}/push", data=json.dumps(payload).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": "d503-engine"})
        try:
            urllib.request.urlopen(req, timeout=5).read()
        except Exception as e:                               # noqa: BLE001
            ERRORS.append(f"web push: {str(e)[:60]}")
            print(f"   web push failed: {str(e)[:60]}")

    t = threading.Thread(target=go, name="web-push")
    t.start()
    return t


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


US = ("USA", "United States", "US", "U.S.A.")


def _international(league, country, neutral):
    """A game played outside the US (London, Germany, Mexico City, Paris...). Canadian teams' normal home games
    don't count; a neutral-site game in Canada does."""
    if not country or country in US:
        return False
    if country == "Canada" and league in ("nba", "nhl", "mlb", "ncaab") and not neutral:
        return False
    return True


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
        def lines(side):                                 # period-by-period points (the comeback study)
            out = []
            for x in teams[side].get("linescores") or []:
                v = x.get("value", x.get("displayValue")) if isinstance(x, dict) else x
                try:
                    out.append(str(int(float(v))))
                except (TypeError, ValueError):
                    return ""
            return ",".join(out)
        (hid, hname), (aid, aname) = team("home"), team("away")
        od = _odds(comp)
        venue = comp.get("venue") or {}
        addr = venue.get("address") or {}
        country = addr.get("country") or ""

        def probable(side):
            for pr in teams[side].get("probables") or []:
                a = pr.get("athlete") or {}
                if a.get("displayName") or a.get("fullName"):
                    return a.get("displayName") or a.get("fullName")
            return ""
        out.append({
            "id": f"{league}:{ev.get('id')}", "league": league, "start": ev.get("date") or comp.get("date", ""),
            "status": status, "home": hid, "away": aid, "home_name": hname, "away_name": aname,
            "home_score": score("home") if status == "final" else "", "away_score": score("away") if status == "final" else "",
            "odds_time": "", "neutral": 1 if comp.get("neutralSite") else 0, "inj_home": "", "inj_away": "",
            "country": country, "intl": 1 if _international(league, country, comp.get("neutralSite")) else 0,
            "city": addr.get("city") or "", "state": addr.get("state") or "",
            "indoor": 1 if venue.get("indoor") or league in ("nba", "nhl", "ncaab") else 0,
            "sp_home": probable("home"), "sp_away": probable("away"),
            "stype": str((ev.get("season") or {}).get("type") or "?"),     # 1 preseason, 2 regular, 3 playoffs
            "ls_home": lines("home") if status == "final" else "", "ls_away": lines("away") if status == "final" else "",
            **{k: ("" if v is None else v) for k, v in od.items()},
        })
    return out


def fetch_day(league, day, retries=2):
    path, extra, _, _ = LEAGUES[league]
    url = ESPN.format(path=path, day=day.strftime("%Y%m%d"), extra=extra)
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=12) as r:     # plain request: ESPN 403s custom user agents
                return parse_scoreboard(league, json.load(r))
        except Exception as e:                       # noqa: BLE001 - network: retry, then give up on this day
            if i == retries - 1:
                ERRORS.append(f"{league} {day:%Y-%m-%d}: {str(e)[:120]}")
                if len(ERRORS) <= 5:
                    print(f"   {ERRORS[-1]}", flush=True)
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


def _real_team(tid):
    """A real team id (ESPN's placeholders for a not-yet-known team are -1 / -2 / 0 / empty)."""
    try:
        return int(str(tid)) > 0
    except ValueError:
        return bool(str(tid or "").strip())


def merge(old, new, now_iso):
    """Update a stored game with a fresh read. Pre-game odds are kept once the game starts (ESPN often
    drops them), so the last odds seen before the start serve as the closing line. The first odds
    ever seen stand in for the opening line when ESPN doesn't give one (for line movement)."""
    g = dict(old or new)
    if old is not None:
        for k in ("start", "status", "home_name", "away_name", "home_score", "away_score", "neutral", "sp_home", "sp_away",
                  "stype", "country", "intl", "city", "state", "indoor"):
            g[k] = new[k]
        for k in ("ls_home", "ls_away"):
            if new.get(k):
                g[k] = new[k]
        for k in ("home", "away"):                           # a playoff game gets posted with "TBD" teams (id -1 / -2):
            if _real_team(new.get(k)) and str(new.get(k)) != str(g.get(k)):
                g[k] = new[k]                                # once ESPN fills them in, take the real team (9/29: the
                #                                              Astros stayed "-1", the engine knew 0 games for them and
                #                                              skipped White Sox +102 @ Astros entirely)
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


DEEP_DAYS = 3650          # how far back the engine studies: 10 full seasons in every sport
DEEP_CHUNK = 365          # history pulled per league per hourly run (a season at a time)
SEASONS_BACK = 10


def sync(state, backfill_days=550, ahead_days=2, max_days=600, workers=8, budget_s=540):
    """Refresh every league: re-read the last few days + next few, and backfill history on first run.
    Stops starting new calls after budget_s; unfinished days count as failed, so the next run resumes there.
    Returns (games dict, number of API calls, number of failures)."""
    today = datetime.now(timezone.utc).date()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    games = load_games()
    jobs = []
    for lg in LEAGUES:
        synced = state.setdefault("synced", {}).get(lg)
        if any(not g.get("stype") or g.get("intl", "") == "" or g.get("indoor", "") == ""
               for g in games.values() if g["league"] == lg) or lg not in state.setdefault("ls_walk", []):
            synced = None                                # stored before season types / venues were kept: re-read everything
            state.setdefault("from", {}).pop(lg, None)
        start = (datetime.strptime(synced, "%Y-%m-%d").date() - timedelta(days=3)) if synced \
            else today - timedelta(days=backfill_days)
        start = max(start, today - timedelta(days=max_days))
        d = start
        while d <= today + timedelta(days=ahead_days):
            jobs.append((lg, d))
            d += timedelta(days=1)
    deep = {}                                            # older history: 120 days per league per run, back to DEEP_DAYS
    for lg in LEAGUES:
        frm = datetime.strptime(state.setdefault("from", {}).get(lg, (today - timedelta(days=backfill_days)).isoformat()),
                                "%Y-%m-%d").date()
        target = today - timedelta(days=DEEP_DAYS)
        if frm > target:
            lo = max(target, frm - timedelta(days=DEEP_CHUNK))
            deep[lg] = lo
            d = lo
            while d < frm:
                jobs.append((lg, d))
                d += timedelta(days=1)
    fails = {}
    deadline = time.time() + budget_s
    done = [0]

    def run(job):
        if time.time() > deadline:
            return job, None
        rows = fetch_day(*job)
        done[0] += 1
        if done[0] % 250 == 0:
            print(f"   synced {done[0]}/{len(jobs)} league-days", flush=True)
        return job, rows
    if jobs and fetch_day("nfl", today) is None and fetch_day("mlb", today) is None:
        print("   ESPN unreachable - keeping stored games", flush=True)
        return games, 2, 2
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(run, jobs))
    for (lg, d), rows in results:
        if rows is None:
            if not (lg in deep and d < deep[lg] + timedelta(days=DEEP_CHUNK + 1)):   # old-history misses don't reset the cursor
                fails[lg] = min(fails.get(lg, d), d)
            continue
        for r in rows:
            games[r["id"]] = merge(games.get(r["id"]), r, now_iso)
    for lg, lo in deep.items():
        if not any(lo <= d < datetime.strptime(state["from"].get(lg, today.isoformat()), "%Y-%m-%d").date()
                   for (l2, d), r in results if l2 == lg and r is None):
            state["from"][lg] = lo.isoformat()
    for lg in LEAGUES:
        # next run starts from the first failed day, else from today
        upto = fails.get(lg, today + timedelta(days=1)) - timedelta(days=1)
        if upto >= today - timedelta(days=max_days):
            state["synced"][lg] = min(upto, today).strftime("%Y-%m-%d")
    for lg in LEAGUES:                                   # history re-walk started for the quarter-by-quarter scores
        if lg not in state["ls_walk"]:
            state["ls_walk"].append(lg)
    save_games(games)
    return games, len(jobs), sum(1 for _, r in results if r is None)


# ---------------------------------------------------------------- injuries
# every status a player can be off the roster with - baseball too (9/29: ESPN had Aaron Judge as "10-Day-IL" and the
# reader dropped it, so every MLB injured-list player was invisible). Short stints count as missing; long ones are
# already priced into the team's results.
SHORT_TERM = ("out", "doubtful", "7-day", "10-day", "15-day", "paternity", "bereavement", "restricted",
              "not with team", "personal")
UNSURE = ("questionable", "game-time", "game time", "day-to-day", "day to day")   # not known yet: wait for news
LONG_OUT = ("reserve", "suspen", "season", "60-day")   # injured reserve / suspended / out for the season / 60-day IL
INJ_LEAGUES = ("nfl", "ncaaf", "nhl", "nba", "mlb")   # leagues where a missing report means we can't know who plays
KEY_POS = {"nfl": {"QB"}, "ncaaf": {"QB"}, "nhl": {"G"}, "nba": None, "mlb": "stars", "ncaab": set()}
# None = any player; "stars" = the team's best bats by name (mlb_stars: MLB's own season stats)


def fetch_injuries(league):
    """{team id or name: [(player, position, status)]} for players listed Out / Doubtful."""
    path = LEAGUES[league][0]
    url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/injuries"
    for i in range(3):                               # the injury report matters too much to give up on one hiccup
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return parse_injuries(json.load(r))
        except Exception as e:                       # noqa: BLE001
            print(f"   {league} injuries (try {i + 1}): {str(e)[:120]}")
            if i < 2:
                time.sleep(2 * (i + 1))
    return None                                      # None = we DON'T KNOW who's hurt (the board waits on it)


def parse_injuries(payload):
    out = {}
    for t in payload.get("injuries") or []:
        rows = []
        for i in t.get("injuries") or []:
            status = str(i.get("status") or (i.get("type") or {}).get("description") or "").lower()
            if not any(s in status for s in SHORT_TERM + UNSURE + LONG_OUT):
                continue
            a = i.get("athlete") or {}
            rows.append((a.get("displayName") or "?", (a.get("position") or {}).get("abbreviation") or "",
                         status.title().replace("-Il", "-IL").replace(" Il", " IL")))
        for key in (str(t.get("id") or ""), t.get("displayName") or ""):
            if key:
                out[key] = rows
    return out


def _team_rows(inj, team_id, team_name):
    if not inj:
        return []
    if team_id in inj:
        return inj[team_id]
    for k, v in inj.items():
        if team_name and not k.isdigit() and (k.endswith(" " + team_name) or k == team_name):
            return v
    return []


def team_injuries(inj, team_id, team_name):
    """Players ruled Out / Doubtful: (name, position, status)."""
    return [r for r in _team_rows(inj, team_id, team_name) if any(s in r[2].lower() for s in SHORT_TERM)]


def _is_key(r, league, team_name):
    keys = KEY_POS.get(league, set())
    if keys == "stars":                                  # baseball: the team's best bats, by name
        return r[0] in team_stars(team_name)
    return keys is None or r[1] in (keys or set())


def team_key_out(inj, team_id, team_name, league):
    """Key players (QB, goalie, a team's best bats) who are out - short or long term. The ratings can't see these."""
    return [r for r in _team_rows(inj, team_id, team_name)
            if KEY_POS.get(league) is not None and _is_key(r, league, team_name)
            and any(s in r[2].lower() for s in SHORT_TERM + LONG_OUT)]


def team_unsure(inj, team_id, team_name, league):
    """Key players whose status is still up in the air (e.g. a questionable QB, a day-to-day slugger)."""
    return [r for r in _team_rows(inj, team_id, team_name)
            if any(s in r[2].lower() for s in UNSURE) and _is_key(r, league, team_name)]


# ---------------------------------------------------------------- baseball: who the stars are, who's in the lineup
MLB_API = "https://statsapi.mlb.com/api/v1"
STARS_PATH = os.path.join(DATA, "mlb_stars.json")
STARS_N, STARS_SHARE = 3, 0.4          # a team's 3 best bats by OPS among real regulars: 40%+ of the trips to the
#                                        plate its busiest hitter has (a star who missed time still counts - Judge,
#                                        285 of Rice's 667; a hot part-timer doesn't - works in April and September)
_STARS = {}
_STARS_TRY = [0.0]
STARS_V = 2                            # bump when the rule changes: today's saved list gets rebuilt


def _mlb_get(path):
    with urllib.request.urlopen(urllib.request.Request(MLB_API + path, headers={"User-Agent": "Mozilla/5.0"}),
                                timeout=20) as r:
        return json.load(r)


def parse_stars(payload, n=STARS_N, share=STARS_SHARE):
    """MLB's season hitting stats (every player) -> {team name: [its best bats]}. Each team's hitters, as that team
    (a traded player counts where he played); regulars only (share of the team's most trips to the plate)."""
    teams = {}
    for sp in ((payload.get("stats") or [{}])[0].get("splits") or []):
        st, who, team = sp.get("stat") or {}, (sp.get("player") or {}).get("fullName"), (sp.get("team") or {}).get("name")
        try:
            pa, ops = int(st.get("plateAppearances") or 0), float(st.get("ops") or 0)
        except (TypeError, ValueError):
            continue
        if who and team:
            teams.setdefault(team, []).append((pa, ops, who))
    out = {}
    for team, rows in teams.items():
        floor = max(30, share * max(r[0] for r in rows))
        out[team] = [w for _, _, w in sorted(((o, p, w) for p, o, w in rows if p >= floor), reverse=True)[:n]]
    return out


def mlb_stars(refresh=False):
    """{team: [best bats]} - refreshed once a day from MLB's own stats site, else the saved copy."""
    if (_STARS or time.time() - _STARS_TRY[0] < 600) and not refresh:
        return _STARS                                        # (a failed read waits 10 min - never a hang per check)
    _STARS_TRY[0] = time.time()
    old = {}
    try:
        old = json.load(open(STARS_PATH))
    except (OSError, ValueError):
        pass
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if old.get("day") == day and old.get("v") == STARS_V and old.get("teams") and not refresh:
        _STARS.update(old["teams"])
        return _STARS
    try:
        yr = datetime.now(timezone.utc).year
        teams = parse_stars(_mlb_get(f"/stats?stats=season&group=hitting&season={yr}&sportId=1&playerPool=ALL&limit=3000"))
        if teams:
            json.dump({"day": day, "v": STARS_V, "teams": teams}, open(STARS_PATH, "w"), indent=1)
            _STARS.clear()
            _STARS.update(teams)
            return _STARS
    except Exception as e:                                   # noqa: BLE001 - the saved copy still works
        print(f"   mlb stars: {str(e)[:100]}")
    _STARS.update(old.get("teams") or {})
    return _STARS


def team_stars(team_name):
    """A team's best bats ('Yankees' finds 'New York Yankees')."""
    st = mlb_stars()
    for t, v in st.items():
        if team_name and (t == team_name or t.endswith(" " + team_name)):
            return v
    return []


def parse_lineups(payload):
    """MLB's schedule (hydrate=lineups) -> {(away team, home team, start): {"away": [...], "home": [...]}} for every
    game whose confirmed lineups are out (a few hours before first pitch)."""
    out = {}
    for d in payload.get("dates") or []:
        for g in d.get("games") or []:
            lu = g.get("lineups") or {}
            if not lu.get("homePlayers") and not lu.get("awayPlayers"):
                continue
            t = g.get("teams") or {}
            key = ((t.get("away") or {}).get("team", {}).get("name"), (t.get("home") or {}).get("team", {}).get("name"),
                   str(g.get("gameDate") or "")[:16])
            out[key] = {"away": [p.get("fullName") for p in lu.get("awayPlayers") or []],
                        "home": [p.get("fullName") for p in lu.get("homePlayers") or []]}
    return out


def mlb_lineups(day):
    """Today's confirmed lineups ({} when none are out yet or the site's down)."""
    try:
        return parse_lineups(_mlb_get(f"/schedule?sportId=1&date={day}&hydrate=lineups"))
    except Exception as e:                                   # noqa: BLE001
        print(f"   mlb lineups: {str(e)[:100]}")
        return {}


def lineup_for(lineups, g, side):
    """The confirmed lineup for one side of our game, or None (not posted yet). Same two teams within 3 hours of our
    start time (a doubleheader's other game never counts)."""
    same = lambda full, short: bool(full) and bool(short) and (full == short or full.endswith(" " + str(short)))
    try:
        ours = datetime.strptime(str(g.get("start"))[:16], "%Y-%m-%dT%H:%M")
    except ValueError:
        return None
    for (a, h, st), lu in lineups.items():
        try:
            gap = abs((datetime.strptime(st[:16], "%Y-%m-%dT%H:%M") - ours).total_seconds())
        except ValueError:
            continue
        if same(a, g.get("away_name")) and same(h, g.get("home_name")) and gap <= 3 * 3600:
            return lu.get(side) or None
    return None


# ---------------------------------------------------------------- Action Network: odds history
# ESPN drops the odds once a game is over. Action Network's public scoreboard keeps them for finished
# games: book 15 = market consensus (used as the closing line), book 30 = the opening line.
AN = "https://api.actionnetwork.com/web/v1/scoreboard/{lg}?period=game&date={day}{extra}"
AN_EXTRA = {"ncaaf": "&division=FBS", "ncaab": "&division=D1"}
AN_CLOSE, AN_OPEN = 15, 30


def parse_an(payload):
    out = []
    for g in payload.get("games") or []:
        teams = {t.get("id"): t for t in g.get("teams") or []}
        home, away = teams.get(g.get("home_team_id")), teams.get(g.get("away_team_id"))
        if not home or not away or not g.get("start_time"):
            continue
        books = {o.get("book_id"): o for o in g.get("odds") or [] if o.get("type", "game") == "game"}
        close, open_ = books.get(AN_CLOSE) or {}, books.get(AN_OPEN) or {}
        row = {"start": g["start_time"][:16] + "Z", "home_full": home.get("full_name") or "", "away_full": away.get("full_name") or "",
               "ml_home": parse_american(close.get("ml_home")), "ml_away": parse_american(close.get("ml_away")),
               "ml_home_open": parse_american(open_.get("ml_home")), "ml_away_open": parse_american(open_.get("ml_away")),
               "spread_home": _num(close.get("spread_home")),
               "spread_home_odds": parse_american(close.get("spread_home_line")), "spread_away_odds": parse_american(close.get("spread_away_line")),
               "total": _num(close.get("total")), "over_odds": parse_american(close.get("over")),
               "under_odds": parse_american(close.get("under")),
               "ls_home": ",".join(str(p.get("home_points") or 0) for p in (g.get("boxscore") or {}).get("linescore") or []),
               "ls_away": ",".join(str(p.get("away_points") or 0) for p in (g.get("boxscore") or {}).get("linescore") or [])}
        lo = (g.get("boxscore") or {}).get("latest_odds") or {}
        part = lo.get("firstfiveinnings") or lo.get("firsthalf") or {}      # first half / MLB first 5 innings (backtests)
        row.update({"h1_ml_home": parse_american(part.get("ml_home")), "h1_ml_away": parse_american(part.get("ml_away")),
                    "h1_spread_home": _num(part.get("spread_home")),
                    "h1_spread_home_odds": parse_american(part.get("spread_home_line")),
                    "h1_spread_away_odds": parse_american(part.get("spread_away_line"))})
        if row["ml_home"] is not None and row["ml_away"] is not None:
            out.append(row)
    return out


AN_WEEKS = {"nfl": (("reg", 18), ("post", 5)), "ncaaf": (("reg", 15), ("post", 1))}   # football pages by week


def fetch_an_day(league, day):
    """One day's games (baseball, basketball, hockey) or, for football, day = (season, type, week)."""
    if league in AN_WEEKS:
        season, typ, week = day
        url = (f"https://api.actionnetwork.com/web/v1/scoreboard/{league}?period=game&season={season}&week={week}"
               f"&seasonType={typ}{AN_EXTRA.get(league, '')}")
        day = datetime(season, 1, 1)                  # only for the error message
    else:
        url = AN.format(lg=league, day=day.strftime("%Y%m%d"), extra=AN_EXTRA.get(league, ""))
    for i in range(2):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return parse_an(json.load(r))
        except Exception as e:                       # noqa: BLE001
            if i == 1:
                ERRORS.append(f"AN {league} {day:%Y-%m-%d}: {str(e)[:120]}")
                if len(ERRORS) <= 5:
                    print(f"   {ERRORS[-1]}", flush=True)
                return None
            time.sleep(2)


def _same(short, full):
    short, full = short.lower().strip(), full.lower()
    return bool(short) and (short in full or full.startswith(short.split(" ")[0] + " "))


H1 = ("h1_ml_home", "h1_ml_away", "h1_spread_home", "h1_spread_home_odds", "h1_spread_away_odds")
TOT = ("total", "over_odds", "under_odds")          # over/unders: kept for the totals study + ASK THE ENGINE


def attach_an(games, league, rows):
    """Fill odds on stored games from Action Network rows (same teams, start within 3 hours).
    Returns how many games got odds they didn't have."""
    idx = {}
    for g in games.values():
        if g["league"] == league and g.get("start"):
            idx.setdefault(g["start"][:10], []).append(g)
    filled = 0
    for r in rows:
        t = datetime.strptime(r["start"], "%Y-%m-%dT%H:%MZ")
        cands = [g for d in {(t + timedelta(days=k)).strftime("%Y-%m-%d") for k in (-1, 0, 1)} for g in idx.get(d, [])]
        for g in cands:
            gt = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M")
            if abs((gt - t).total_seconds()) > 3 * 3600:
                continue
            if not (_same(g["home_name"], r["home_full"]) and _same(g["away_name"], r["away_full"])):
                continue
            if g.get("ml_home", "") == "":
                filled += 1
                for k in ("ml_home", "ml_away", "spread_home", "spread_home_odds", "spread_away_odds"):
                    if r[k] is not None:
                        g[k] = r[k]
            if r["ml_home_open"] is not None and r["ml_away_open"] is not None:
                g["ml_home_open"], g["ml_away_open"] = r["ml_home_open"], r["ml_away_open"]
            for k in H1:
                if r.get(k) is not None and g.get(k, "") == "":
                    g[k] = r[k]
            if r.get("total") is not None and (g.get("total", "") == "" or g.get("status") == "pre"):
                for k in TOT:                                # the latest before the start = the closing total
                    if r.get(k) is not None:
                        g[k] = r[k]
            if r.get("ls_home") and g.get("status") == "final" and not g.get("ls_home"):
                g["ls_home"], g["ls_away"] = r["ls_home"], r["ls_away"]
            break
    return filled


def _flag(lg, back):
    """State key marking a past football season as fully loaded (keeps the old names for 1-2 seasons back)."""
    return f"{lg}_past" if back == 1 else f"{lg}_past{back}"


def sync_odds_history(games, state, backfill_days=550, workers=6, budget_s=420):
    """Backfill closing + opening odds for finished games, a stretch per run until caught up."""
    today = datetime.now(timezone.utc).date()
    if not state.get("an_h1"):                           # re-walk the odds history once to keep first-half / F5 lines
        state["an_synced"], state["an_from"], state["an_h1"] = {}, {}, True
    if not state.get("an_tot"):                          # ...and once more to keep over/under totals
        state["an_synced"], state["an_from"], state["an_tot"] = {}, {}, True
    cur = state.setdefault("an_synced", {})
    jobs = []
    weeks = []
    for lg, parts in AN_WEEKS.items():                # last season once, this season every run (cheap)
        seasons = [today.year] + [today.year - b for b in range(1, SEASONS_BACK + 1) if not cur.get(_flag(lg, b))]
        weeks += [(lg, (y, typ, w)) for y in seasons for typ, n in parts for w in range(1, n + 1)]
    for lg in LEAGUES:
        if lg in AN_WEEKS:
            continue
        start = datetime.strptime(cur[lg], "%Y-%m-%d").date() - timedelta(days=2) if lg in cur \
            else today - timedelta(days=backfill_days)
        d = start
        while d <= today + timedelta(days=1):
            jobs.append((lg, d))
            d += timedelta(days=1)
    deep = {}
    for lg in LEAGUES:
        if lg in AN_WEEKS:
            continue
        frm = datetime.strptime(state.setdefault("an_from", {}).get(lg, (today - timedelta(days=backfill_days)).isoformat()),
                                "%Y-%m-%d").date()
        target = today - timedelta(days=DEEP_DAYS)
        if frm > target:
            lo = max(target, frm - timedelta(days=DEEP_CHUNK))
            deep[lg] = (lo, frm)
            d = lo
            while d < frm:
                jobs.append((lg, d))
                d += timedelta(days=1)
    deadline = time.time() + budget_s

    def run(job):
        return job, (fetch_an_day(*job) if time.time() < deadline else None)
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(run, jobs))
        wres = list(ex.map(run, weeks))
    filled = 0
    for lg in AN_WEEKS:
        for back in range(1, SEASONS_BACK + 1):
            past = [r for (l2, (y, _, _)), r in wres if l2 == lg and y == today.year - back]
            if past and all(r is not None for r in past):
                cur[_flag(lg, back)] = True
    for (lg, _), rows in wres:
        if rows is not None:
            filled += attach_an(games, lg, rows)
    fails = {}
    for (lg, d), rows in results:
        if rows is None:
            if not (lg in deep and d < deep[lg][1]):
                fails[lg] = min(fails.get(lg, d), d)
            continue
        filled += attach_an(games, lg, rows)
    for lg, (lo, hi) in deep.items():
        if all(r is not None for (l2, d), r in results if l2 == lg and lo <= d < hi):
            state["an_from"][lg] = lo.isoformat()
    for lg in LEAGUES:
        if lg in AN_WEEKS:
            continue
        upto = fails.get(lg, today + timedelta(days=1)) - timedelta(days=1)
        if lg in cur or upto >= today - timedelta(days=backfill_days):
            cur[lg] = min(upto, today).strftime("%Y-%m-%d")
    return filled, len(jobs) + len(weeks), sum(1 for _, r in results + wres if r is None)


def merge_live_logs(a, b):
    """Two copies of the live-bet log -> one with every bet in either (9/29: the watcher's saves to main failed for an
    hour and that night's live bets never reached the page). Per bet: a graded copy beats an ungraded one, else the
    fuller copy."""
    out = {"plays": dict((a or {}).get("plays") or {})}
    for pid, e in ((b or {}).get("plays") or {}).items():
        mine = out["plays"].get(pid)
        if mine is None or (e.get("result") and not mine.get("result")) or \
                (bool(e.get("result")) == bool(mine.get("result")) and len(e) > len(mine)):
            out["plays"][pid] = e
    for k, v in ((a or {}).items()):
        if k != "plays":
            out[k] = v
    return out


def live_log_from_branch():
    """The live-bet log the watcher ships with every board push (the live-data branch), or {}."""
    import subprocess
    try:
        subprocess.run(["git", "fetch", "-q", "origin", "live-data"], capture_output=True, timeout=30)
        r = subprocess.run(["git", "show", "origin/live-data:live_log.json"], capture_output=True, text=True, timeout=30)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    except Exception:                                         # noqa: BLE001
        return {}
