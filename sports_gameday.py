"""🟢 GAME DAY: who is really dressed (11/23 - the owner: "I just want to make sure we're always getting the accurate
information across lines, injuries, everything, and double checking sources always"; his friend Victor: "It's been wrong
on a lot on injuries and starters tho. It said Darren Waller was out for Panthers and he was playing").

The injury report is a FORECAST. A man it lists questionable is settled on game day - the NFL's inactives about 90
minutes before kickoff, the NBA's starting five about half an hour before the tip, and in every sport the box score the
minute the game is on. The card's injury watch re-read only the report, and ESPN's report keeps "Questionable" on a man
straight through a game he is playing in: of the 15 men the cards of 11/2-11/23 called questionable, the card never
said how one of them ended (6 played - Darren Waller and Tommy Tremble on the 11/22 Panthers card).

This module is the game-day read, two plain sources, each said only as strongly as it speaks:

  1. THE LIVE BOX SCORE (ESPN's game summary - the same page the box-score files are built from, sports_roster.parse):
     a man with minutes / a stat line in it is PLAYING; once the game is on, a hoops man flagged a starter (exactly
     five of them) is STARTING. It never says a man is out - a box score only shows who has played.
  2. THE NFL GAME-DAY ROSTER (ESPN's per-game roster list): each man active or not once the inactives are filed. Read
     ONLY when it looks like a real inactives list (ROSTER_MIN..ROSTER_MAX men, INACT_MIN..INACT_MAX of them inactive);
     any other shape says nothing. Then a questionable man is ACTIVE or INACTIVE.

No source says = no word: the card keeps him on its ❓ game-time line, never "out" and never "playing". Every request
goes out as the engine itself (sports_http.HDR); a source that refuses or answers a shape we don't know goes quiet and
says so in source_status.json ("espn_gameday_box" / "espn_gameday_roster"). Nothing here touches a pick, a price or a
size - facts on the card only.
"""
import json
import time
import urllib.request
from datetime import datetime, timezone

import sports_data as sd
import sports_http as sh

ON = [True]                   # (tests turn it off - never a real request from a test; GET feeds a fixture instead)
GET = None                    # tests: a callable url -> payload
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={eid}"
ROSTER = ("https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{lg}/events/{eid}/competitions/{eid}"
          "/competitors/{tid}/roster?limit=200")
ROSTER_LEAGUES = ("nfl",)     # the leagues whose game-day roster names the inactives
ROSTER_MIN, ROSTER_MAX = 40, 80     # a real NFL game-day list: the 53 + the practice-squad call-ups...
INACT_MIN, INACT_MAX = 2, 14        # ...with a handful inactive. Anything else = not an inactives list = no word
AHEAD_MIN = {"nfl": 110, "ncaaf": 45, "nba": 50, "ncaab": 40, "nhl": 40, "mlb": 40}   # how early before the start it's worth a read
AFTER_MIN = 150               # ...and how long after: by then the box score has every man who is going to play
TTL = 240                     # one read per game at most every 4 minutes (never hammer the feed)
_CACHE = {}                   # game id -> (read at, result)
POSITIVE = ("active", "starting", "playing")


def _get(url):
    if GET is not None:
        return GET(url)
    with urllib.request.urlopen(urllib.request.Request(url, headers=sh.JSON_HDR), timeout=12) as r:
        return json.load(r)


def same(a, b):
    """One man under two spellings ('D. Waller' = 'Darren Waller')."""
    return sd._same_man(a, b)


def parse_box(league, payload, live=True):
    """{team id: {shown name: 'starting' / 'playing'}} from a game summary's box score. Only what the box SHOWS: a man
    with minutes (hoops) / a stat line (football, hockey, baseball) is playing; a hoops starter counts only when the
    team has exactly five flagged AND the game is on (a starter flag before the tip may be last game's - never a
    claim). Never raises on a shape it doesn't know - that team just says nothing."""
    out = {}
    try:
        for team in (payload.get("boxscore") or {}).get("players") or []:
            tid = str((team.get("team") or {}).get("id") or "")
            men, starters = {}, []
            for grp in team.get("statistics") or []:
                keys = grp.get("keys") or grp.get("labels") or []
                for a in grp.get("athletes") or []:
                    nm = (a.get("athlete") or {}).get("displayName")
                    if not nm:
                        continue
                    if a.get("starter") and league in ("nba", "ncaab"):
                        starters.append(nm)
                    vals = a.get("stats") or []
                    if a.get("didNotPlay") or not vals:
                        continue
                    st = dict(zip(keys, vals))
                    if league in ("nba", "ncaab"):
                        mins = str(st.get("minutes") or st.get("MIN") or "0").split(":")[0]
                        if not mins.isdigit() or int(mins) <= 0:
                            continue
                    elif not any(str(v).strip() not in ("", "--", "0", "0:00", "0-0", "0/0", "0.0") for v in vals):
                        continue
                    men[nm] = "playing"
            if len(set(starters)) == 5 and live:
                for nm in starters:
                    men[nm] = "starting"
            if tid and men:
                out[tid] = men
    except Exception:                                        # noqa: BLE001
        return out
    return out


def parse_roster(payload, names=None):
    """{name: 'active' / 'inactive'} from ESPN's per-game NFL roster - {} unless it looks like a real inactives list
    (see ROSTER_MIN / INACT_MIN): a shape we don't know never becomes a claim. THE REAL SHAPE (11/26, read live on the
    Chiefs @ Bills list through fetch_pages): before kickoff EVERY entry has "active": false - starters too (Kelce) -
    so "active" is no inactives flag; the inactives are "didNotPlay": true (9 a team, the Chiefs' matching the report:
    Moore, Walker III, Norman-Lott ...), and "displayName" is the short name ("Walker III", "T. Smith"). The full name
    comes off our box-score rosters by playerId (names) - a short name with no full one is kept as it is, and the
    card's matcher (same) never pins a full name on a bare last name."""
    try:
        ent = [e for e in (payload.get("entries") or []) if isinstance(e, dict) and e.get("displayName")
               and isinstance(e.get("didNotPlay", False), bool)]
    except Exception:                                        # noqa: BLE001
        return {}
    if not ROSTER_MIN <= len(ent) <= ROSTER_MAX:
        return {}
    off = [e for e in ent if e.get("didNotPlay") is True]
    if not INACT_MIN <= len(off) <= INACT_MAX:              # (none flagged yet = the list isn't filed - no word)
        return {}
    names = names or {}
    return {(names.get(str(e.get("playerId"))) or e["displayName"]): ("inactive" if e.get("didNotPlay") is True else "active")
            for e in ent}


_NAMES = {}


def full_names(lg, start):
    """{playerId: full name} off our box-score rosters (data/sports/roster/<lg>_<season>.csv.gz) - the season of the
    game and the one before. {} when the files aren't there."""
    import csv
    import gzip
    import os
    yr = str(start or "")[:4]
    key = (lg, yr)
    if key in _NAMES:
        return _NAMES[key]
    out = {}
    for y in ((str(int(yr) - 1), yr) if yr.isdigit() else ()):
        f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sports", "roster", f"{lg}_{y}.csv.gz")
        try:
            with gzip.open(f, "rt", newline="") as fh:
                for r in csv.DictReader(fh):
                    if r.get("pid") and r.get("player"):
                        out[str(r["pid"])] = r["player"]
        except (OSError, ValueError, EOFError):
            continue
    _NAMES[key] = out
    return out


def due(g, now=None):
    """Is this game inside its game-day window (close enough to the start that the lists are out, or on)?"""
    now = now or datetime.now(timezone.utc)
    if not g or g.get("status") not in ("pre", "live", "in") or not g.get("start"):
        return False
    try:
        t = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    mins = (t - now).total_seconds() / 60
    return -AFTER_MIN <= mins <= AHEAD_MIN.get(g.get("league"), 40)


def started(g, now=None):
    """Past the scheduled start (by the clock - the game file may still say 'pre' for a few minutes)."""
    now = now or datetime.now(timezone.utc)
    try:
        return g.get("status") != "pre" or now >= datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    except (ValueError, KeyError, TypeError):
        return False


def read(g, now=None):
    """{"home": {name: word}, "away": {name: word}, "src": {name: source}} for one game - the game-day word on every man
    a source speaks for ('active' / 'inactive' / 'starting' / 'playing'). {} outside the window, when the read is off,
    or when no source answered. Cached TTL seconds."""
    if not due(g, now) or (not ON[0] and GET is None):
        return {}
    gid = g.get("id") or ""
    hit = _CACHE.get(gid)
    if hit and time.time() - hit[0] < TTL and GET is None:
        return hit[1]
    lg, eid = g.get("league"), gid.split(":", 1)[-1]
    out = {"home": {}, "away": {}, "src": {}}
    if lg in ROSTER_LEAGUES:
        got = 0
        sport, lg_ = sd.LEAGUES[lg][0].split("/")
        for side in ("home", "away"):
            try:
                men = parse_roster(_get(ROSTER.format(sport=sport, lg=lg_, eid=eid, tid=g[side])),
                                   full_names(lg, g.get("start")))
            except Exception as e:                           # noqa: BLE001 - quiet, and it says so
                sh.note("espn_gameday_roster", False, err=sh.err_text(e),
                        how="plain request - the NFL game-day roster (inactives); quiet = a questionable man stays on "
                            "the card's game-time line until the box score shows him")
                men = {}
            for nm, w in men.items():
                out[side][nm] = w
                out["src"][nm] = "the game-day inactives list"
            got += bool(men)
        if got:
            sh.note("espn_gameday_roster", True, n=got, how="plain request - the NFL game-day roster (inactives)")
        elif "espn_gameday_roster" not in sh.SEEN:
            sh.note("espn_gameday_roster", False, n=0,
                    how="plain request - no inactives list in the answer yet (not filed, or a shape we don't read); a "
                        "questionable man stays on the card's game-time line until the box score shows him")
    if started(g, now):                                      # (before the start a box score has nobody in it)
        try:
            box = parse_box(lg, _get(SUMMARY.format(path=sd.LEAGUES[lg][0], eid=eid)), live=True)
            for side in ("home", "away"):
                for nm, w in (box.get(str(g[side])) or {}).items():
                    if out[side].get(nm) != "inactive":     # (a man on the inactives list with a stat line: the list
                        out[side].setdefault(nm, w)         #  stays - never two words on one man)
                        out["src"].setdefault(nm, "the box score")
            sh.note("espn_gameday_box", True, n=sum(len(v) for v in box.values()),
                    how="plain request - the live box score (who is playing)")
        except Exception as e:                               # noqa: BLE001
            sh.note("espn_gameday_box", False, err=sh.err_text(e),
                    how="plain request - the live box score (who is playing)")
    if not out["home"] and not out["away"]:
        out = {}
    _CACHE[gid] = (time.time(), out)
    return out


def word(got, side, name):
    """(word, source) the game-day read has on this man for this side - (None, None) when it doesn't speak for him."""
    for nm, w in ((got or {}).get(side) or {}).items():
        if same(nm, name):
            return w, ((got or {}).get("src") or {}).get(nm)
    return None, None
