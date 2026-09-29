"""BACKUP SPORTSBOOKS for live prices (the owner, 9/29: "when one fails, it instantly goes to the other").

Bovada stays first. When it has no fresh price for a game or a tennis match (blocked, cached, down, or just not
offering it), these fill in, in this order:
  1. BetRivers (Kambi's public odds feed) - every price carries when it last changed, so the same 60-second freshness
     rule applies as for Bovada.
  2. FanDuel (its public sportsbook pages) - no per-price timestamp, so its prices only count when the page itself
     came back fresh (the server's own Age header), never a cached copy.

Plain public pages only: no borrowed keys, and when a book turns us away we just move to the next one - we never
disguise ourselves to get back in. Every read is logged in STATUS so the hourly bug check can say which source is down.
"""
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"}
KAMBI = "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/listView/{p}.json?lang=en_US&market=US"
KAMBI_EVENT = "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/betoffer/event/{id}.json?lang=en_US&market=US"
KAMBI_PATH = {"nfl": "american_football/nfl", "ncaaf": "american_football/ncaaf", "nba": "basketball/nba",
              "ncaab": "basketball/ncaab", "mlb": "baseball/mlb", "nhl": "ice_hockey/nhl",
              "tennis": "tennis/all/all/all/in-play"}
FANDUEL = "https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?{q}&_ak=FhMFpcPWXMeyZxOx"
FANDUEL_Q = {"nfl": "page=CUSTOM&customPageId=nfl", "ncaaf": "page=CUSTOM&customPageId=ncaaf",
             "nba": "page=CUSTOM&customPageId=nba", "ncaab": "page=CUSTOM&customPageId=ncaab",
             "mlb": "page=CUSTOM&customPageId=mlb", "nhl": "page=CUSTOM&customPageId=nhl",
             "tennis": "page=SPORT&eventTypeId=2"}
FRESH_AGE_S = 10              # a FanDuel page older than this (the server's Age header) is a cached copy: no price
EVERY_S = 3                   # each backup read at most every 3 seconds per league (never hammer a book)
STATUS = {}                   # "betrivers:mlb" -> {"ok": bool, "at": epoch, "n": prices, "err": str}
_CACHE = {}                   # url -> (fetched at, data, age)


def _get(url):
    """(json, Age header seconds or None) - one read, 8s timeout, at most every EVERY_S per url."""
    now = time.time()
    hit = _CACHE.get(url)
    if hit and now - hit[0] < EVERY_S:
        return hit[1], hit[2]
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=8) as r:
        age = r.headers.get("Age")
        data = json.load(r)
    out = (now, data, int(age) if age and str(age).isdigit() else None)
    _CACHE[url] = out
    return out[1], out[2]


def _ms(iso):
    try:
        return datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000
    except (TypeError, ValueError):
        return 0


def _am(v):
    s = str(v if v is not None else "").upper().replace("+", "")
    if s == "EVEN":
        return 100
    return int(s) if re.fullmatch(r"-?\d{3,5}", s) else None


# ---------------------------------------------------------------- BetRivers (Kambi)
def _kambi_ml(e):
    """The event's match moneyline betOffer, or None."""
    for b in e.get("betOffers") or []:
        lab = str((b.get("criterion") or {}).get("englishLabel") or "")
        if (lab.startswith("Moneyline") or lab == "Match Odds") and \
                str((b.get("betOfferType") or {}).get("englishName")) == "Match":
            return b
    return None


def kambi_team(data, live_only=True, missing=None):
    """Kambi listView (one league) -> [{home, away, ml_home, ml_away, mod, src}] - live games with both sides open.
    `missing` (a list) collects the live events whose list entry shows no moneyline (the NFL list only shows the
    spread): their own event page has it."""
    out = []
    for e in (data or {}).get("events") or []:
        ev = e.get("event") or {}
        if live_only and ev.get("state") != "STARTED":
            continue
        b = _kambi_ml(e)
        if b is None and missing is not None and ev.get("id"):
            missing.append(ev["id"])
        parts = str(ev.get("englishName") or "").split(" - ")
        if not b or len(parts) != 2:
            continue
        home, away = parts[0].strip(), parts[1].strip()        # Kambi lists the home team first ("ATL - PHI")
        px = {str(o.get("englishLabel") or o.get("participant")): (_am(o.get("oddsAmerican")), o.get("status"))
              for o in b.get("outcomes") or []}
        (h, hs), (a, as_) = px.get(home, (None, None)), px.get(away, (None, None))
        if h is None or a is None or hs != "OPEN" or as_ != "OPEN":
            continue
        mod = max((_ms(o.get("changedDate")) for o in b.get("outcomes") or []), default=0)
        out.append({"home": home, "away": away, "ml_home": h, "ml_away": a, "mod": mod, "src": "betrivers"})
    return out


def kambi_event(data):
    """Kambi betoffer/event/{id} -> the same [{home, away, ml_home, ml_away, mod, src}] (one game)."""
    evs = (data or {}).get("events") or []
    if not evs:
        return []
    return kambi_team({"events": [{"event": evs[0], "betOffers": (data or {}).get("betOffers") or []}]})


def kambi_tennis(data):
    """Kambi in-play tennis -> [{a, b, start, a_ml, b_ml, suspended, mod, event, tour, src}] - ATP / WTA singles only
    (the same shape as sports_tennis.parse_bovada(live=True))."""
    out = []
    for e in (data or {}).get("events") or []:
        ev = e.get("event") or {}
        path = [str(p.get("englishName") or "") for p in ev.get("path") or []]
        tour = "atp" if "ATP" in path[1:2] else "wta" if "WTA" in path[1:2] else None
        if ev.get("state") != "STARTED" or tour is None or "/" in str(ev.get("englishName")):
            continue
        b = _kambi_ml(e)
        oc = (b or {}).get("outcomes") or []
        if len(oc) != 2:
            continue
        a_ml, b_ml = _am(oc[0].get("oddsAmerican")), _am(oc[1].get("oddsAmerican"))
        shut = a_ml is None or b_ml is None or any(o.get("status") != "OPEN" for o in oc)
        out.append({"a": oc[0].get("englishLabel") or oc[0].get("participant"),
                    "b": oc[1].get("englishLabel") or oc[1].get("participant"),
                    "start": str(ev.get("start") or "")[:16] + "Z", "a_ml": a_ml, "b_ml": b_ml, "suspended": shut,
                    "mod": max((_ms(o.get("changedDate")) for o in oc), default=0), "event": "",
                    "tour": tour, "src": "betrivers"})
    return out


# ---------------------------------------------------------------- FanDuel
def fanduel_team(data, age=None, now_ms=None):
    """FanDuel content page -> [{home, away, ml_home, ml_away, mod, src}] - in-play moneylines. mod = now when the
    page came back fresh (Age <= FRESH_AGE_S or no cache), else 0 (a cached copy is never a live price)."""
    now_ms = now_ms if now_ms is not None else time.time() * 1000
    mod = now_ms - 1000 * (age or 0) if age is None or age <= FRESH_AGE_S else 0
    out = []
    for m in ((data or {}).get("attachments") or {}).get("markets", {}).values():
        if m.get("marketType") != "MONEY_LINE" or not m.get("inPlay") or m.get("marketStatus") != "OPEN":
            continue
        side = {}
        for r in m.get("runners") or []:
            t = ((r.get("result") or {}).get("type") or "").upper()
            odds = ((r.get("winRunnerOdds") or {}).get("americanDisplayOdds") or {}).get("americanOddsInt")
            if t in ("HOME", "AWAY") and r.get("runnerStatus") == "ACTIVE" and odds is not None:
                side[t] = (r.get("runnerName"), int(odds))
        if "HOME" in side and "AWAY" in side:
            out.append({"home": side["HOME"][0], "away": side["AWAY"][0], "ml_home": side["HOME"][1],
                        "ml_away": side["AWAY"][1], "mod": mod, "src": "fanduel"})
    return out


def fanduel_tennis(data, age=None, now_ms=None):
    """FanDuel tennis page -> tennis lines (in-play match betting, singles). Tour unknown here (None): the watcher
    matches it to ESPN's ATP / WTA match by the two last names."""
    now_ms = now_ms if now_ms is not None else time.time() * 1000
    mod = now_ms - 1000 * (age or 0) if age is None or age <= FRESH_AGE_S else 0
    out = []
    for m in ((data or {}).get("attachments") or {}).get("markets", {}).values():
        if m.get("marketType") != "MATCH_BETTING" or not m.get("inPlay"):
            continue
        rs = m.get("runners") or []
        if len(rs) != 2 or any("/" in str(r.get("runnerName")) for r in rs):
            continue
        odds = [((r.get("winRunnerOdds") or {}).get("americanDisplayOdds") or {}).get("americanOddsInt") for r in rs]
        shut = m.get("marketStatus") != "OPEN" or any(o is None for o in odds) or \
            any(r.get("runnerStatus") != "ACTIVE" for r in rs)
        out.append({"a": rs[0].get("runnerName"), "b": rs[1].get("runnerName"),
                    "start": str(m.get("marketTime") or "")[:16] + "Z",
                    "a_ml": None if odds[0] is None else int(odds[0]), "b_ml": None if odds[1] is None else int(odds[1]),
                    "suspended": shut, "mod": mod, "event": "", "tour": None, "src": "fanduel"})
    return out


# ---------------------------------------------------------------- the failover reads
def _read(src, key, url, parse):
    """One source, one league: parsed prices, or [] (and STATUS says why)."""
    k = f"{src}:{key}"
    try:
        data, age = _get(url)
        got = parse(data, age)
        STATUS[k] = {"ok": True, "at": time.time(), "n": len(got), "age": age}
        return got
    except urllib.error.HTTPError as e:
        STATUS[k] = {"ok": False, "at": time.time(), "err": f"HTTP {e.code}"}
    except Exception as e:                                    # noqa: BLE001 - a backup never breaks the watch
        STATUS[k] = {"ok": False, "at": time.time(), "err": str(e)[:80]}
    return []


def team_backup(league):
    """Backup live moneylines for one league: BetRivers, then FanDuel ([] when neither has any)."""
    got, missing = [], []
    if league in KAMBI_PATH:
        got += _read("betrivers", league, KAMBI.format(p=KAMBI_PATH[league]), lambda d, a: kambi_team(d, missing=missing))
        for eid in missing[:8]:                               # (the NFL: each live game's own page has the moneyline)
            got += _read("betrivers", f"{league}:{eid}", KAMBI_EVENT.format(id=eid), lambda d, a: kambi_event(d))
    if league in FANDUEL_Q:
        got += _read("fanduel", league, FANDUEL.format(q=FANDUEL_Q[league]), lambda d, a: fanduel_team(d, a))
    return got


def tennis_backup():
    """Backup live tennis lines: BetRivers, then FanDuel."""
    return (_read("betrivers", "tennis", KAMBI.format(p=KAMBI_PATH["tennis"]), lambda d, a: kambi_tennis(d))
            + _read("fanduel", "tennis", FANDUEL.format(q=FANDUEL_Q["tennis"]), lambda d, a: fanduel_tennis(d, a)))
