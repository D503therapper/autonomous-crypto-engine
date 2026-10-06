"""🥅 WHO'S IN NET (the owner OK'd it, 10/6): each NHL game's CONFIRMED (or likely) starting goalies, from Daily Faceoff's
public starting-goalies page (https://www.dailyfaceoff.com/starting-goalies - a plain request on GitHub's servers, read
only). ESPN's game summary has no probable-goalie field and the NHL schedule feed only names the winning goalie after
the game, so Daily Faceoff is the source; ESPN's scoreboard 'probable' (sp_home / sp_away) is a guess that fills in
days ahead - it is never read as a confirmation.

What it's for - a WEIGHT, never a trigger (CLAUDE.md):
  (a) the goalie-roles finding (SPORTS_FINDINGS 10/1 "found, not built"): a dog starting its #1 goalie while the
      favorite doesn't. Re-checked blind (tools/goalie_roles_study.py - our box scores 2018-27, closing prices, dogs +100..+220,
      '#1' = most starts in the team's previous 10 games): -4.0% for every dog; the dog with its #1 vs a favorite
      without its #1: +1.5% on 1,098, better than all dogs 7 of 8 seasons, 2023-26 +10% on 439 (3 of 3). A 12-game
      window made it +2.3 pts (5 of 8), 15 games +1.8 (4 of 8) - the role is a recent thing. t about 0.3 overall, so a
      lead-sized weight: ROLE_W = +2 on the Dog's score (inside STUDY_CAP; the favorite across from it is weighed down
      through sports.mark_hockey_favorites, inside NHL_FAV_CAP). The reverse (favorite with its #1, dog without): -4.8%
      vs -4.0%, 4-5 of 8 - noise, no weight (ROLE_W_REV = 0).
  (b) the goalie weights that already exist (hot / slumping goalie, the goalie rating) use the confirmed or likely
      starter when one is known instead of guessing from the last start (sports_players.starter_for).
  (c) the card names the starters only when CONFIRMED (never an unconfirmed starter as fact); a goalie confirmed after a
      hockey pick is posted shows on the card like an injury alert (sports.key_status) - no phone ping, the pick never
      changes on its own.
Fail soft: the page down / changed = unknown = no weight and no line, never a guess, never a blocked board."""
import html
import json
import os
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone

import sports_data as sd

URL = "https://www.dailyfaceoff.com/starting-goalies"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
PATH = os.path.join(sd.DATA, "nhl_goalies.json")
STATUSES = ("confirmed", "likely", "expected", "projected", "unconfirmed")   # the page's words, surest first
KNOWN = ("confirmed", "likely", "expected")   # known enough to weigh / to pick the goalie the form weights look at
FRESH_H = 8                                   # a page older than this is stale: back to unknown (no weight, no line)
N1_GAMES = 10                                 # '#1' = most starts in the team's previous 10 games (our box scores)
N1_MIN = 6                                    # ...when we hold at least 6 of them, and there's a clear leader
ROLE_W = 2.0                                  # the dog starts its #1 and the favorite doesn't: +2 on the Dog's score
ROLE_W_REV = 0.0                              # the reverse: nothing (noise in the re-check)

_CACHE = {}
_GAME = re.compile(r"^(.{3,40}?) at (.{3,40})$")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
_COUNT = re.compile(r"^of (\d+) confirmed$", re.I)


def text_of(body):
    """HTML -> its readable lines (the same read tools/fetch_pages gives)."""
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", body)
    body = re.sub(r"(?s)<!--.*?-->", " ", body)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", body))
    lines = [re.sub(r"\s+", " ", x).strip() for x in t.split("\n")]
    return [x for x in lines if x]


def _nm(x):
    return " ".join(str(x or "").lower().replace(".", "").replace(" jr", "").replace(" sr", "").split())


def parse(lines):
    """The page's lines -> [{'away', 'home', 'start', 'goalies': {'away': {...}, 'home': {...}}}]. Each game is
    'Away Team at Home Team' then its start time; its two goalie blocks follow, the away team's first - a name, a status
    word, then (when there's news) the news line and its source. Anything the page doesn't say stays out."""
    games, cur, i = [], None, 0
    while i < len(lines):
        ln = lines[i]
        m = _GAME.match(ln)
        if m and i + 1 < len(lines) and _ISO.match(lines[i + 1]):
            cur = {"away": m.group(1).strip(), "home": m.group(2).strip(), "start": lines[i + 1][:16] + "Z", "goalies": {}}
            games.append(cur)
            i += 2
            continue
        if cur is not None and len(cur["goalies"]) < 2 and i + 1 < len(lines) and lines[i + 1].lower() in STATUSES \
                and 2 <= len(ln.split()) <= 4 and not _ISO.match(ln) and not ln.endswith(":"):
            side = "away" if "away" not in cur["goalies"] else "home"
            goalie = {"name": ln, "status": lines[i + 1].lower(), "news": "", "source": "", "at": ""}
            j = i + 2
            while j < len(lines) and lines[j] != "Line Combos" and not _GAME.match(lines[j]) and j < i + 40:
                if _ISO.match(lines[j]) and not goalie["at"]:
                    goalie["at"] = lines[j][:16] + "Z"
                if lines[j] == "Source:" and j + 1 < len(lines):
                    goalie["news"], goalie["source"] = lines[j - 1], lines[j + 1]
                j += 1
            cur["goalies"][side] = goalie
            i = j
            continue
        i += 1
    return games


def _same_team(page_name, our_name):
    """'Toronto Maple Leafs' is our 'Maple Leafs'; 'St Louis Blues' our 'Blues'; 'Utah Mammoth' our 'Mammoth'."""
    a, b = _nm(page_name), _nm(our_name)
    return bool(a and b) and (a == b or a.endswith(" " + b) or b.endswith(" " + a))


def match(parsed, games):
    """{our game id: {'home': goalie, 'away': goalie}} - each page game matched to our NHL game by its two teams and
    the day (the page's time is the real start; ours agrees to the minute, or at worst the same UTC day)."""
    ours = [g for g in games.values() if g.get("league") == "nhl" and g.get("status") in ("pre", "live")]
    out = {}
    for pg in parsed:
        hit = None
        for g in ours:
            if _same_team(pg["home"], g.get("home_name", "")) and _same_team(pg["away"], g.get("away_name", "")):
                if g["start"][:16] == pg["start"][:16]:
                    hit = g
                    break
                if g["start"][:10] == pg["start"][:10] and hit is None:
                    hit = g
        if hit is not None and pg["goalies"]:
            out[hit["id"]] = {s: dict(v) for s, v in pg["goalies"].items()}
    return out


def fetch(get=None):
    """The page's lines (a plain public request). Raises on any trouble - sync() catches it."""
    if get is not None:
        return text_of(get(URL))
    with urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=30) as r:
        return text_of(r.read().decode("utf-8", "replace"))


def sync(games, now=None, get=None):
    """Fetch, parse, match to our games and save nhl_goalies.json (status + the time we saw it). Any failure leaves the
    last saved file alone (it goes stale on its own after FRESH_H) and returns None - the board never waits on it."""
    now = now or datetime.now(timezone.utc)
    try:
        lines = fetch(get)
        parsed = parse(lines)
        if not parsed and not any("starting goalies" in x.lower() for x in lines[:40]):
            raise ValueError("not the starting-goalies page")
        got = match(parsed, games)
        n_conf = next((int(_COUNT.match(x).group(1)) for x in lines if _COUNT.match(x)), None)
        box = {"seen": now.strftime("%Y-%m-%dT%H:%MZ"), "source": URL, "page_games": len(parsed), "page_slots": n_conf,
               "games": got,
               "unmatched": [f"{p['away']} at {p['home']} {p['start']}" for p in parsed if not _matched(p, games, got)][:20]}
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        with open(PATH, "w") as f:
            json.dump(box, f, indent=1, sort_keys=True)
        _CACHE.clear()
        print(f"goalies: {len(parsed)} games on the page, {len(got)} matched, "
              f"{sum(1 for g in got.values() for v in g.values() if v.get('status') == 'confirmed')} confirmed")
        return len(got)
    except Exception as e:                                   # noqa: BLE001 - unknown is unknown, never a guess
        print(f"goalies failed to load: {str(e)[:80]}")
        return None


def _matched(p, games, got):
    return any(_same_team(p["home"], games[k].get("home_name", "")) and _same_team(p["away"], games[k].get("away_name", ""))
               for k in got if k in games)


def load(now=None):
    """The saved page, or {} when there is none or it's stale (older than FRESH_H hours)."""
    now = now or datetime.now(timezone.utc)
    if "box" not in _CACHE:
        try:
            with open(PATH) as f:
                _CACHE["box"] = json.load(f)
        except (OSError, ValueError):
            _CACHE["box"] = {}
    box = _CACHE["box"]
    try:
        seen = datetime.strptime(box.get("seen", "")[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return {}
    return box if (now - seen).total_seconds() <= FRESH_H * 3600 else {}


def starter(gid, side, now=None):
    """The known (confirmed / likely) starter for a side: {'name', 'status', 'news', ...} or None (unknown)."""
    v = ((load(now).get("games") or {}).get(gid) or {}).get(side)
    return v if v and v.get("status") in KNOWN and v.get("name") else None


def confirmed(gid, side, now=None):
    v = starter(gid, side, now)
    return v if v and v["status"] == "confirmed" else None


# ---------------------------------------------------------------- who's the #1 (our box scores)
def season_start(iso):
    """The NHL season an ISO date falls in starts September 1 (an October date: this September; May: last September)."""
    try:
        y, m = int(iso[:4]), int(iso[5:7])
    except (TypeError, ValueError):
        return "0"
    return f"{y if m >= 9 else y - 1}-09-01"


def number_one(rows, team_id, before, n=N1_GAMES):
    """(name, his starts, games we hold) for the team's #1 goalie - most starts in its previous n games before `before`
    (box scores: one goalie row a team-game, the starter). None when we hold under N1_MIN of them or two are tied."""
    seen, starts = [], []
    floor = season_start(before)                             # this season only (the re-check was season by season; last
    for r in reversed(rows or []):                           # spring's playoff starts say nothing about October's roles)
        if str(r.get("team")) != str(team_id) or not floor <= r.get("start", "") < before or r.get("role", "G") != "G":
            continue
        if r["gid"] in seen:
            continue
        seen.append(r["gid"])
        starts.append(r["player"])
        if len(seen) >= n:
            break
    if len(starts) < N1_MIN:
        return None
    top = Counter(starts).most_common(2)
    if len(top) > 1 and top[0][1] == top[1][1]:
        return None
    return top[0][0], top[0][1], len(starts)


def roles(rows, g, now=None):
    """{side: True (the known starter is the team's #1) / False (he isn't) / None (unknown - no starter known, or no #1
    to compare him to)} for an NHL game, plus 'n1': {side: (name, starts, games)}."""
    out = {"n1": {}}
    for side in ("home", "away"):
        n1 = number_one(rows, g.get(side), g.get("start") or "9")
        st = starter(g.get("id"), side, now)
        out["n1"][side] = n1
        out[side] = None if not st or not n1 else _nm(st["name"]) == _nm(n1[0])
    return out


def role_points(c):
    """The Dog's-score points for a candidate (sports.dog_spots): its known starter is its #1 and the favorite's isn't
    -> +ROLE_W; the reverse -> -ROLE_W_REV; anything unknown -> 0."""
    me, opp = c.get("g_role_me"), c.get("g_role_opp")
    if me is True and opp is False:
        return ROLE_W
    if me is False and opp is True:
        return -ROLE_W_REV
    return 0.0


# ---------------------------------------------------------------- the card
def _role_words(name, n1):
    if not n1:
        return ""
    if _nm(n1[0]) == _nm(name):
        return f" — their #1, {n1[1]} of their last {n1[2]} starts"
    return f" — not their usual #1, that's {n1[0]} with {n1[1]} of the last {n1[2]} starts"


def card_line(g, side, rows, now=None):
    """🥅 Who's confirmed in net, our side first - CONFIRMED only (a likely starter is never stated as fact), with his
    role from our box scores. '' when neither is confirmed."""
    if g.get("league") != "nhl":
        return ""
    parts = []
    for s in (side, "away" if side == "home" else "home"):
        v = confirmed(g.get("id"), s, now)
        if v:
            n1 = number_one(rows, g.get(s), g.get("start") or "9")
            parts.append(f"{v['name']} confirmed for the {g.get(s + '_name', '')}{_role_words(v['name'], n1)}")
    return f"🥅 In net: {'; '.join(parts)}." if parts else ""


def watch_status(g, now=None):
    """{'Name (Team G)': 'Confirmed in net'} for each confirmed starter - folded into sports.key_status so a goalie
    confirmed after a hockey pick is posted shows on the card the way an injury change does."""
    out = {}
    if g.get("league") != "nhl":
        return out
    for s in ("home", "away"):
        v = confirmed(g.get("id"), s, now)
        if v:
            out[f"{v['name']} ({g.get(s + '_name', '')} G)"] = "Confirmed in net"
    return out
