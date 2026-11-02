"""HONEST REQUESTS (the owner's rule: "No borrowed keys or disguises to get past a site's blocks"; 11/2: "Do whatever
Fable recommends" - drop every browser disguise, find legit replacements).

Every outside read the sports engine makes goes out as itself: Python's default User-Agent, or this plain identifying
one. Never a browser's User-Agent, never a Referer or an Origin pretending the request came from the site's own page.
When a site answers an honest request with nothing (or turns it away), that feature goes quiet and says so - it is never
worked around.

source_status.json (data/sports) shows each source's last answer to a plain request on GitHub's servers - a session
reads it to see whether Bovada, BetRivers, Rotowire, Covers, Daily Faceoff, Yahoo... still answer."""
import json
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

UA = "D503-sports-engine/1.0 (personal picks dashboard)"
HDR = {"User-Agent": UA}
JSON_HDR = {"User-Agent": UA, "Accept": "application/json"}
PATH = os.path.join("data", "sports", "source_status.json")

# what a browser disguise looks like (the source scan in sports_test uses the same list)
BROWSER = re.compile(r"Mozilla/|AppleWebKit|Chrome/\d|Safari/\d|Gecko\)|Firefox/\d|Edg/\d|iPhone OS|Android \d")

SEEN = {}                     # source -> {"ok", "at", "n", "err", "how"} (this run's last answer)


def browser_like(headers):
    """True if a header set pretends to be a browser or the site's own page (a browser User-Agent, a Referer, an
    Origin)."""
    for k, v in (headers or {}).items():
        k = str(k).lower()
        if k in ("referer", "origin"):
            return True
        if k == "user-agent" and BROWSER.search(str(v)):
            return True
    return False


def note(src, ok, n=None, err=None, how=None):
    """Record one source's answer to a plain request (ok = it gave us something usable)."""
    SEEN[src] = {"ok": bool(ok), "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                 **({"n": n} if n is not None else {}), **({"err": str(err)[:100]} if err else {}),
                 **({"how": how} if how else {})}


def err_text(e):
    return f"HTTP {e.code}" if isinstance(e, urllib.error.HTTPError) else str(e)[:100]


def save(path=None, extra=None):
    """Merge this run's answers into source_status.json (a source not read this run keeps its last line)."""
    path = path or PATH
    try:
        with open(path) as f:
            cur = json.load(f)
    except (OSError, ValueError):
        cur = {}
    cur.setdefault("sources", {})
    cur["sources"].update(SEEN)
    for k, v in (extra or {}).items():
        cur["sources"][k] = v
    cur["ua"] = UA
    cur["rule"] = "plain requests only - no browser User-Agent, no Referer / Origin (the owner's no-disguise rule, 11/2)"
    cur["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(cur, f, indent=1, sort_keys=True)
    except OSError:
        pass
    return cur


# ---------------------------------------------------------------- the hourly plain-request check
# One plain read each (a few requests an hour): does the book still answer an honest request on GitHub's servers? The
# full Bovada / BetRivers league lists always carry upcoming games, so an empty answer means the book is refusing.
PROBES = {
    "bovada": "https://www.bovada.lv/services/sports/event/v2/events/A/description/basketball/nba?lang=en",
    "bovada_nfl": "https://www.bovada.lv/services/sports/event/v2/events/A/description/football/nfl?lang=en",
    "betrivers": "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/listView/basketball/nba.json"
                 "?lang=en_US&market=US",
    "betrivers_nfl": "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/listView/american_football/nfl.json"
                     "?lang=en_US&market=US",
}
ON = [True]                   # (tests turn it off - never a real request from a test)


def _count(src, data):
    if src.startswith("bovada"):
        return sum(len(g.get("events") or []) for g in data if isinstance(g, dict)) if isinstance(data, list) else 0
    return len((data or {}).get("events") or []) if isinstance(data, dict) else 0


def probe_one(src, url, get=None):
    try:
        if get:
            data = get(url)
        else:
            with urllib.request.urlopen(urllib.request.Request(url, headers=JSON_HDR), timeout=10) as r:
                data = json.load(r)
        n = _count(src, data)
        note(src, n > 0, n=n, how="plain request" + ("" if n else " - answered EMPTY (no events: refused or down)"))
    except Exception as e:                                    # noqa: BLE001 - a probe never breaks a run
        note(src, False, err=err_text(e), how="plain request")
    return SEEN[src]


def probe(get=None):
    """Every PROBES source, one plain request each, in parallel. -> {source: answer}."""
    if not ON[0] and get is None:
        return {}
    with ThreadPoolExecutor(len(PROBES)) as ex:
        list(ex.map(lambda kv: probe_one(kv[0], kv[1], get), PROBES.items()))
    return {k: SEEN[k] for k in PROBES}


def run_check(path=None, get=None):
    """The hourly run's step: probe the live books, then save every source this run read (injury pages, goalies,
    splits...) to source_status.json. Never raises."""
    t0 = time.time()
    try:
        probe(get)
        extra = {}
        try:
            import sports_books
            for k, v in sports_books.STATUS.items():          # (BetRivers pregame reads made by the early spots)
                extra[k] = {"ok": bool(v.get("ok")), "n": v.get("n"), "err": v.get("err"),
                            "at": datetime.fromtimestamp(v.get("at", t0), timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
        except Exception:                                    # noqa: BLE001
            pass
        out = save(path, extra)
        bad = sorted(k for k, v in out.get("sources", {}).items() if not v.get("ok"))
        print(f"source check ({time.time() - t0:.1f}s): plain requests answered by "
              f"{sum(1 for v in out['sources'].values() if v.get('ok'))} of {len(out['sources'])} sources"
              + (f" - quiet: {', '.join(bad)}" if bad else ""))
        return out
    except Exception as e:                                    # noqa: BLE001
        print(f"source check failed: {e}")
        return {}
