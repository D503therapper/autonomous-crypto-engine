"""🕐 THE PRE-TIP 1ST-HALF LINE LOG (11/3 - DATA ONLY: no picks, no units, nothing on the board).

SPORTS_FINDINGS "11/3 - DEEP: WHERE BASKETBALL BOOKS ARE WEAK", Q2: the college hoops 1st-half spread looks cheap next
to 0.549 x the full closing spread (+5.5% on 2,140) - but our 1H numbers are Action Network's boxscore 'latest_odds',
filled in AFTER the game (one number, its time unknown), so the edge may be AN's snapshot timing, not a book's 1H line
that really lags. The only honest test is the real pre-tip numbers: every hourly sports.py run logs the 1st-half spread
next to the full-game spread, with timestamps, for every NBA and college hoops game tipping in the next ~24 hours.
After 3-4 weeks of logs, re-test the lead on these numbers. Putting a 1H market on the board stays the owner's call.

Source: Action Network's public scoreboard (the same game list sports_data / sports_live already read) - period=firsthalf
for the 1H lines, period=game for the full-game lines, today's and tomorrow's Pacific dates. Plain requests with the
engine's own name (sports_http.JSON_HDR) - no disguise. If AN answers with no 1H lines, the log says so (rows carry an
empty "h1") and source_status.json shows "actionnetwork_h1" quiet - never worked around.

data/sports/h1_lines.jsonl.gz - append-only (one gzip member per run), one row per game per hour:
  {"t": logged at, "hr": the UTC hour, "lg": nba / ncaab, "an": AN game id, "g": our game id (or null), "s": tip,
   "home", "away", "st": AN status,
   "fg": {"b": book, "sp": home spread, "spo": [home juice, away juice], "ml": [home, away], "tot": total, "at": when the
          book's line was stamped},
   "h1": same shape for the 1st half, "esp": our own (ESPN) home spread for the game}
Books: AN's consensus (15) when it carries the number, else the first book that does. h1_lines_seen.json keeps the
(game, hour) keys of the last 2 days so a re-run inside the hour adds nothing."""
import gzip
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

import sports_http as sh

try:
    from zoneinfo import ZoneInfo
    PT = ZoneInfo("America/Los_Angeles")
except Exception:                                            # noqa: BLE001
    PT = timezone(timedelta(hours=-8))

LEAGUES = ("nba", "ncaab")
AN_URL = "https://api.actionnetwork.com/web/v1/scoreboard/{lg}?period={period}&date={day}{extra}"
AN_EXTRA = {"ncaab": "&division=D1"}
PERIODS = {"game": "fg", "firsthalf": "h1"}
CONSENSUS = 15                                               # AN's market consensus (the study's close)
AHEAD_H = 24                                                 # games tipping in the next ~24 hours
PATH = os.path.join("data", "sports", "h1_lines.jsonl.gz")
SEEN_PATH = os.path.join("data", "sports", "h1_lines_seen.json")
LIVE_ST = ("inprogress", "in_progress", "live", "halftime", "complete", "closed", "final", "cancelled", "canceled",
           "postponed")


def _num(x):
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _am(x):
    v = _num(x)
    return int(v) if v is not None else None


def _line(o):
    """One AN odds entry -> our compact line (None if it carries no spread and no moneyline)."""
    sp, mlh, mla = _num(o.get("spread_home")), _am(o.get("ml_home")), _am(o.get("ml_away"))
    if sp is None and mlh is None and mla is None:
        return None
    return {"b": o.get("book_id"), "sp": sp, "spo": [_am(o.get("spread_home_line")), _am(o.get("spread_away_line"))],
            "ml": [mlh, mla], "tot": _num(o.get("total")),
            "at": o.get("inserted") or o.get("updated_at") or o.get("updated") or None}


def pick_line(odds, typ):
    """The consensus line of one type (game / firsthalf) from a game's odds list, else the first book with a spread,
    else the first with anything."""
    ls = [o for o in odds or [] if isinstance(o, dict) and str(o.get("type") or "game") == typ]
    for want in (lambda o: o.get("book_id") == CONSENSUS and _line(o),
                 lambda o: _num(o.get("spread_home")) is not None, _line):
        for o in ls:
            if want(o):
                return _line(o)
    return None


def parse(payload, period):
    """One scoreboard payload -> {an id: {"meta": ..., "fg"/"h1": line}}. A game-period payload can carry 1H entries
    too (and a boxscore's latest_odds.firsthalf) - all of it is read."""
    out = {}
    for g in (payload or {}).get("games") or []:
        teams = {t.get("id"): t for t in g.get("teams") or []}
        home, away = teams.get(g.get("home_team_id")), teams.get(g.get("away_team_id"))
        if not home or not away or not g.get("start_time") or g.get("id") is None:
            continue
        x = {"meta": {"s": str(g["start_time"])[:16] + "Z", "home": home.get("full_name") or "",
                      "away": away.get("full_name") or "", "st": str(g.get("status") or "")}}
        odds = g.get("odds") or []
        if period == "firsthalf":                         # (every entry on the 1H page is a 1H line, labelled or not)
            fg = None
            h1 = pick_line(odds, "firsthalf") or pick_line([dict(o, type="firsthalf") for o in odds
                                                            if isinstance(o, dict)], "firsthalf")
        else:
            fg, h1 = pick_line(odds, "game"), pick_line(odds, "firsthalf")
        lo = ((g.get("boxscore") or {}).get("latest_odds") or {}).get("firsthalf")
        if not h1 and isinstance(lo, dict):
            h1 = _line(lo)
        if fg:
            x["fg"] = fg
        if h1:
            x["h1"] = h1
        out[g["id"]] = x
    return out


def _get(url):
    req = urllib.request.Request(url, headers=sh.JSON_HDR)          # the engine's own name, never a browser's
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def fetch(now, get=None):
    """{league: {an id: game}} for today's and tomorrow's Pacific dates, both periods merged. Errors -> notes."""
    get = get or _get
    days = sorted({(now.astimezone(PT) + timedelta(days=k)).strftime("%Y%m%d") for k in (0, 1)})
    res, errs = {}, []
    for lg in LEAGUES:
        games = res.setdefault(lg, {})
        for period in PERIODS:
            for day in days:
                url = AN_URL.format(lg=lg, period=period, day=day, extra=AN_EXTRA.get(lg, ""))
                try:
                    got = parse(get(url), period)
                except Exception as e:                      # noqa: BLE001 - a log never breaks a run
                    errs.append(f"{lg} {period} {day}: {sh.err_text(e)}")
                    continue
                for gid, x in got.items():
                    cur = games.setdefault(gid, {"meta": x["meta"]})
                    for k in ("fg", "h1"):
                        if x.get(k) and not cur.get(k):
                            cur[k] = x[k]
    return res, errs


def _match(games, lg, meta):
    """Our game (id, ESPN home spread) for an AN game: same league, both names, tip within 3 hours."""
    import sports_data as sd
    try:
        t = datetime.strptime(meta["s"], "%Y-%m-%dT%H:%MZ")
    except (KeyError, ValueError):
        return None, None
    for g in (games or {}).values():
        if g.get("league") != lg or not g.get("start"):
            continue
        try:
            gt = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M")
        except ValueError:
            continue
        if abs((gt - t).total_seconds()) <= 3 * 3600 and sd._same(g.get("home_name"), meta["home"]) \
                and sd._same(g.get("away_name"), meta["away"]):
            return g.get("id"), _num(g.get("spread_home"))
    return None, None


def log(games=None, now=None, get=None, path=None, seen_path=None):
    """The hourly step: fetch, keep the pre-tip games in the next AHEAD_H hours, append one row per game per hour.
    Returns how many rows were added. Never raises."""
    now = now or datetime.now(timezone.utc)
    path, seen_path = path or PATH, seen_path or SEEN_PATH
    if get is None and not sh.ON[0]:                         # (tests: never a real request)
        return 0
    try:
        got, errs = fetch(now, get)
        stamp, hr = now.strftime("%Y-%m-%dT%H:%MZ"), now.strftime("%Y-%m-%dT%H")
        hi = (now + timedelta(hours=AHEAD_H)).strftime("%Y-%m-%dT%H:%MZ")
        try:
            with open(seen_path) as f:
                seen = json.load(f)
        except (OSError, ValueError):
            seen = {}
        rows, n_h1 = [], 0
        for lg, gs in got.items():
            for gid, x in sorted(gs.items(), key=lambda kv: str(kv[0])):
                m = x["meta"]
                if not (stamp < m["s"] <= hi) or m["st"].lower() in LIVE_ST:
                    continue
                if not x.get("fg") and not x.get("h1"):
                    continue
                key = f"{lg}:{gid}"
                if seen.get(key) == hr:
                    continue
                seen[key] = hr
                our, esp = _match(games, lg, m)
                rows.append({"t": stamp, "hr": hr, "lg": lg, "an": gid, "g": our, "s": m["s"], "home": m["home"],
                             "away": m["away"], "st": m["st"], "fg": x.get("fg"), "h1": x.get("h1"), "esp": esp})
                n_h1 += bool(x.get("h1"))
        if rows:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with gzip.open(path, "at") as f:                 # append-only: one gzip member per run
                for r in rows:
                    f.write(json.dumps(r, separators=(",", ":")) + "\n")
        keep = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H")
        seen = {k: v for k, v in seen.items() if v >= keep}
        os.makedirs(os.path.dirname(seen_path) or ".", exist_ok=True)
        with open(seen_path, "w") as f:
            json.dump(seen, f, sort_keys=True)
        n_games = sum(len(v) for v in got.values())
        sh.note("actionnetwork_h1", n_h1 > 0 or (not errs and not rows), n=n_h1, err="; ".join(errs[:2]) or None,
                how="plain request" + ("" if n_h1 or not rows else " - games listed but NO pre-tip 1st-half line"))
        print(f"1H line log: {len(rows)} rows ({n_h1} with a 1st-half line) from {n_games} AN games"
              + (f" - errors: {'; '.join(errs[:3])}" if errs else ""))
        return len(rows)
    except Exception as e:                                   # noqa: BLE001
        print(f"1H line log failed: {e}")
        return 0


def read(path=None):
    """Every logged row (the re-test reads this)."""
    out = []
    try:
        with gzip.open(path or PATH, "rt") as f:
            for line in f:
                if line.strip():
                    out.append(json.loads(line))
    except OSError:
        pass
    return out
