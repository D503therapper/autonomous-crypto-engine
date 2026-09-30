"""BACKUP SPORTSBOOKS for live prices (the owner, 9/29: "when one fails, it instantly goes to the other").

Bovada stays first. When it has no fresh price for a game or a tennis match (blocked, cached, down, or just not
offering it), BetRivers (Kambi's public odds feed) fills in - every price carries when it last changed, so the same
60-second freshness rule applies as for Bovada.

Plain public pages only: no borrowed keys or access codes (that's why FanDuel was dropped 9/29 - its feed wants one),
and when a book turns us away we just move on - we never disguise ourselves to get back in. Every read is logged in STATUS so the hourly bug check can say which source is down.
"""
import json
import re
import time
import urllib.error
import urllib.request

import sports_data as sd
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"}
KAMBI = "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/listView/{p}.json?lang=en_US&market=US"
KAMBI_EVENT = "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/betoffer/event/{id}.json?lang=en_US&market=US"
KAMBI_PATH = {"nfl": "american_football/nfl", "ncaaf": "american_football/ncaaf", "nba": "basketball/nba",
              "ncaab": "basketball/ncaab", "mlb": "baseball/mlb", "nhl": "ice_hockey/nhl",
              "tennis": "tennis/all/all/all/in-play"}
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


def kambi_pregame(data, missing=None):
    """Kambi listView -> upcoming games' moneylines: [{home, away, ml_home, ml_away, start, src}] (the early lines:
    BetRivers posts football a week out). Full team names (homeName / awayName) so they match ours. `missing`
    collects the events whose list entry has no moneyline (the NFL list shows the spread only)."""
    out = []
    for e in (data or {}).get("events") or []:
        ev = e.get("event") or {}
        if ev.get("state") not in (None, "NOT_STARTED"):
            continue
        home, away = str(ev.get("homeName") or ""), str(ev.get("awayName") or "")
        b = _kambi_ml(e)
        if b is None:
            if missing is not None and ev.get("id"):
                missing.append(ev["id"])
            continue
        if not home or not away:
            continue
        px = {}
        for o in b.get("outcomes") or []:
            px[str(o.get("participant") or o.get("englishLabel") or "")] = (_am(o.get("oddsAmerican")), o.get("status"))
        h = next((v for k, v in px.items() if k and (k == home or sd._same(k, home))), (None, None))
        a = next((v for k, v in px.items() if k and (k == away or sd._same(k, away))), (None, None))
        if h[0] is None or a[0] is None or h[1] != "OPEN" or a[1] != "OPEN":
            continue
        out.append({"home": home, "away": away, "ml_home": h[0], "ml_away": a[0], "start": str(ev.get("start") or ""),
                    "src": "betrivers"})
    return out


def pregame(league, max_events=25):
    """BetRivers' moneylines for a league's upcoming games ([] when it has none or it's down)."""
    if league not in KAMBI_PATH:
        return []
    missing = []
    got = _read("betrivers", f"pre:{league}", KAMBI.format(p=KAMBI_PATH[league]), lambda d, a: kambi_pregame(d, missing))
    for eid in missing[:max_events]:
        got += _read("betrivers", f"pre:{league}:{eid}", KAMBI_EVENT.format(id=eid),
                     lambda d, a: kambi_pregame({"events": [{"event": (d.get("events") or [{}])[0],
                                                             "betOffers": d.get("betOffers") or []}]}))
    return got


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
                    "tour": tour, "src": "betrivers", "live": kambi_live(e)})
    return out


def kambi_live(e):
    """The book's own live score for a tennis match: {home, sets: [[home, away], ...] (the last one is being played),
    pts: [home, away] ('15', '30', 'AD' / tiebreak points), home_serves} - or None. (The owner, 9/29: always show who's
    serving, and 15-0 / 30-0 if it's accurate - the book posts every point.)"""
    ld = e.get("liveData") or {}
    st = ((ld.get("statistics") or {}).get("sets")) or {}
    h, a = st.get("home") or [], st.get("away") or []
    if not h or len(h) != len(a):
        return None
    sc = ld.get("score") or {}
    pts = [str(sc.get("home")), str(sc.get("away"))] if sc.get("home") is not None and sc.get("away") is not None else None
    hs = st.get("homeServe")
    return {"home": (e.get("event") or {}).get("homeName") or "", "sets": [[int(x), int(y)] for x, y in zip(h, a)],
            "pts": pts, "home_serves": hs if isinstance(hs, bool) else None}


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
    """Backup live moneylines for one league from BetRivers ([] when it has none)."""
    got, missing = [], []
    if league in KAMBI_PATH:
        got += _read("betrivers", league, KAMBI.format(p=KAMBI_PATH[league]), lambda d, a: kambi_team(d, missing=missing))
        for eid in missing[:8]:                               # (the NFL: each live game's own page has the moneyline)
            got += _read("betrivers", f"{league}:{eid}", KAMBI_EVENT.format(id=eid), lambda d, a: kambi_event(d))
    return got


def tennis_backup():
    """Backup live tennis lines from BetRivers."""
    return _read("betrivers", "tennis", KAMBI.format(p=KAMBI_PATH["tennis"]), lambda d, a: kambi_tennis(d))
