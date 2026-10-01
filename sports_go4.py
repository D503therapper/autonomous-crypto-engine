"""NFL 4TH-DOWN AGGRESSIVENESS (10/1 - the owner: "everything needs to be wired in - coaches, how they play").

The NFL style study (nflverse play-by-play 2016-26, 2,258 games at the close, blind walk-forward): every matchup and
coaching factor was already in the price - except one LEAD: a dog whose coach goes for it on 4th down clearly LESS than
the other coach covered 48.4% (0 of 9 seasons over breakeven), ML -13.4%; the most aggressive quarter of dogs covered
53.9% (6 of 9). Same direction as college football's conservative-coach fade. So it's a small WEIGHT on the dog's read
(sports.dog_spots), never a trigger.

A team's go rate: "go-able" 4th downs (4th and 1-3, between its own 40 and the other 30, game still in doubt - win
chance 10-90%), went for it (run / pass) vs punted / kicked; each older game counts 7% less, last season carries in at
35%, small samples pulled toward the league rate (6 tries). From nflverse's free public play-by-play (no key), refreshed
at most once a day. Saved to data/sports/nfl_go4.json: {"updated", "league", "teams": {"Browns": rate, ...}}."""
import csv
import gzip
import io
import json
import os
import urllib.request
from datetime import datetime, timezone

import sports_data as sd

URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{y}.csv.gz"
PATH = os.path.join(sd.DATA, "nfl_go4.json")
GAME_DECAY = 0.93
SEASON_CARRY = 0.35
PSEUDO = 6
REFRESH_H = 20
GAP_LO, GAP_HI = -0.071, 0.074     # the study's quarters of the dog-minus-favorite go-rate gap

NICK = {"ARI": "Cardinals", "ATL": "Falcons", "BAL": "Ravens", "BUF": "Bills", "CAR": "Panthers", "CHI": "Bears",
        "CIN": "Bengals", "CLE": "Browns", "DAL": "Cowboys", "DEN": "Broncos", "DET": "Lions", "GB": "Packers",
        "HOU": "Texans", "IND": "Colts", "JAX": "Jaguars", "KC": "Chiefs", "LV": "Raiders", "LAC": "Chargers",
        "LA": "Rams", "LAR": "Rams", "MIA": "Dolphins", "MIN": "Vikings", "NE": "Patriots", "NO": "Saints",
        "NYG": "Giants", "NYJ": "Jets", "PHI": "Eagles", "PIT": "Steelers", "SF": "49ers", "SEA": "Seahawks",
        "TB": "Buccaneers", "TEN": "Titans", "WAS": "Commanders"}


def _season_now(now):
    return now.year if now.month >= 7 else now.year - 1


def _fetch(y):
    req = urllib.request.Request(URL.format(y=y), headers={"User-Agent": "D503-sports-engine/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = gzip.decompress(r.read()).decode("utf-8")
    return csv.DictReader(io.StringIO(raw))


def tries(rows):
    """[(team, game order key, went for it)] for every go-able 4th down, regular season."""
    out = []
    for r in rows:
        try:
            if r.get("season_type") != "REG" or r.get("down") != "4" or float(r.get("ydstogo") or 99) > 3:
                continue
            yl, wp = float(r.get("yardline_100") or -1), float(r.get("wp") or -1)
        except ValueError:
            continue
        if not (30 <= yl <= 60 and 0.1 <= wp <= 0.9) or r.get("play_type") not in ("pass", "run", "punt", "field_goal"):
            continue
        out.append((r.get("posteam"), r.get("game_date") or "", r.get("play_type") in ("pass", "run")))
    return out


def rates(cur, prev=()):
    """{team abbr: go rate} from this season's tries (decayed by game) + last season's at SEASON_CARRY."""
    tot = {}
    for t, _, g in list(cur) + list(prev):
        a = tot.setdefault(t, [0.0, 0.0])
        a[0] += g
        a[1] += 1
    league = sum(a[0] for a in tot.values()) / max(1.0, sum(a[1] for a in tot.values()))
    out = {}
    teams = {t for t, _, _ in list(cur) + list(prev) if t}
    for t in teams:
        go = n = 0.0
        days = sorted({d for tt, d, _ in cur if tt == t}, reverse=True)
        for t_, d, g in cur:
            if t_ == t:
                w = GAME_DECAY ** days.index(d)
                go, n = go + w * g, n + w
        for t_, _, g in prev:
            if t_ == t:
                go, n = go + SEASON_CARRY * g, n + SEASON_CARRY
        out[t] = (go + PSEUDO * league) / (n + PSEUDO)
    return out, league


def refresh(now=None, force=False):
    """Pull the current (and last) season's play-by-play and save every team's go rate - at most once a day."""
    now = now or datetime.now(timezone.utc)
    old = load()
    if not force and old.get("updated"):
        try:
            age = (now - datetime.strptime(old["updated"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)).total_seconds()
            if age < REFRESH_H * 3600:
                return old
        except ValueError:
            pass
    y = _season_now(now)
    try:
        cur = tries(_fetch(y))
        prev = tries(_fetch(y - 1))
    except Exception as e:                                   # noqa: BLE001 - extra data never blocks the board
        print(f"4th-down rates: download failed ({str(e)[:60]})")
        return old
    r, league = rates(cur, prev)
    data = {"updated": now.strftime("%Y-%m-%dT%H:%MZ"), "season": y, "league": round(league, 4),
            "teams": {NICK.get(t, t): round(v, 4) for t, v in r.items()}}
    with open(PATH + ".tmp", "w") as f:
        json.dump(data, f, indent=1)
    os.replace(PATH + ".tmp", PATH)
    _CACHE.clear()
    return data


_CACHE = {}


def load():
    if "d" not in _CACHE:
        try:
            _CACHE["d"] = json.load(open(PATH))
        except (OSError, ValueError):
            _CACHE["d"] = {}
    return _CACHE["d"]


def rate(team_name):
    """A team's go rate by its name (the engine's short names: 'Browns')."""
    teams = load().get("teams") or {}
    for nick, v in teams.items():
        if team_name and (sd._same(nick, team_name) or sd._same(team_name, nick)):
            return v
    return None


def gap(me, them):
    """This team's go rate minus the other's (None when either is unknown)."""
    a, b = rate(me), rate(them)
    return None if a is None or b is None else round(a - b, 4)
