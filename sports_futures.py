"""🏆 FUTURES PRICE LOG (the owner, 10/3: "can we set the engine up for futures ... we don't want to just take the most
likely odds"). The 10/3 study (SPORTS_FINDINGS): preseason longshots never beat their price as a group (+5000 and up:
0 for 1,278), title markets carry a 21-29% cut, and our own ratings picked WORSE than the market preseason - so nothing
is posted off this yet. What the next study needs is our own price history (the free archives stop at 2023): once a
day, every title / conference futures market ESPN carries (DraftKings), saved to data/sports/futures/<date>.json.
Report only - never a pick."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import sports_data as sd

DIR = os.path.join(sd.DATA, "futures")
PT = ZoneInfo("America/Los_Angeles")
API = "https://sports.core.api.espn.com/v2/sports/{path}/seasons/{season}/futures?limit=200"
LEAGUES = {"nba": "basketball/leagues/nba", "nhl": "hockey/leagues/nhl", "nfl": "football/leagues/nfl",
           "ncaaf": "football/leagues/college-football"}      # (MLB: ESPN's book was stale on 10/3 - eliminated teams)
SKIP = ("MVP", "Player", "Rookie", "Coach", "Trophy", "In-Season", "Most ", "FCS", "Award", "Leader")


def _get(url):
    with urllib.request.urlopen(url, timeout=20) as r:        # plain request: ESPN 403s custom user agents
        return json.loads(r.read().decode("utf-8", "replace"))


def parse(js):
    """{market name: {"book": provider, "prices": {ESPN team id: american odds}}} - team markets only, first book."""
    out = {}
    for it in (js or {}).get("items") or []:
        name = it.get("name") or ""
        if any(k in name for k in SKIP) or not it.get("futures"):
            continue
        f = it["futures"][0]
        prices = {}
        for b in f.get("books") or []:
            m = re.search(r"/teams/(\d+)", ((b.get("team") or {}).get("$ref")) or "")
            v = str(b.get("value") or "")
            if m and re.fullmatch(r"[+-]\d+", v):
                prices[m.group(1)] = int(v)
        if prices:
            out[name] = {"book": (f.get("provider") or {}).get("name"), "prices": prices}
    return out


def snapshot(now, get=_get):
    """Every league's markets now: the season that has them (an NBA / NHL season is named for the year it ends)."""
    snap = {}
    for lg, path in LEAGUES.items():
        for season in (now.year + 1, now.year):
            try:
                mk = parse(get(API.format(path=path, season=season)))
            except Exception as e:                           # noqa: BLE001 - a missing season / ESPN down: next
                print(f"futures {lg} {season}: {str(e)[:60]}")
                mk = {}
            if mk:
                snap[lg] = {"season": season, "markets": mk}
                break
    return snap


def run(now=None, path=None, get=_get):
    """Once a day (the first engine run from 6 AM PT): save today's futures prices. Never blocks the board."""
    now = now or datetime.now(timezone.utc)
    day = now.astimezone(PT)
    if day.hour < 6:
        return None
    d = path or DIR
    f = os.path.join(d, f"{day.date().isoformat()}.json")
    if os.path.exists(f):
        return None
    snap = snapshot(now, get)
    if not snap:
        return None
    os.makedirs(d, exist_ok=True)
    with open(f, "w") as fh:
        json.dump({"at": now.strftime("%Y-%m-%dT%H:%MZ"), "leagues": snap}, fh, indent=0, sort_keys=True)
    print("futures logged: " + ", ".join(f"{lg} {len(v['markets'])}" for lg, v in snap.items()))
    return f
