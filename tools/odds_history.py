"""ODDS HISTORY (10/1, the owner paid one month of The Odds API to find out if the engine can beat football lines
early): moneyline snapshots for NFL + college football since the 2020 season, several per week (the midweek prices
our data never had - only the stale summer open and the close). Runs in GitHub Actions with the owner's key in the
ODDS_API_KEY secret (never in the repo). Resumable: snapshots already saved are skipped. A credit guard stops it well
before the plan runs dry.

Saves data/sports/odds_history/{sport}.jsonl.gz - one row per game per snapshot:
  {"snap": "...Z", "id": event id, "t": kickoff, "h": home, "a": away, "b": {book: [home price, away price]}}"""
import gzip
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

OUT = "data/sports/odds_history"
API = "https://api.the-odds-api.com/v4/historical/sports/{sport}/odds"
GUARD = 2500                                   # stop with this many credits left (the plan has 20,000)
# when to look, by weekday (Mon=0): NFL Tue/Thu/Sat + Sunday morning; college Tue/Thu + Saturday morning
PLAN = {"americanfootball_nfl": {"days": {1: "18:00", 3: "18:00", 5: "18:00", 6: "15:00"}, "season": ("09-01", "02-15")},
        "americanfootball_ncaaf": {"days": {1: "18:00", 3: "18:00", 5: "14:00"}, "season": ("08-20", "01-20")}}
FIRST = 2020
# SPREADS (the owner, 10/1: "we get +9.5 and it drops to +3.5"): one Tuesday look a week - the close is already in our
# games - so ~2,800 credits. Rows: "b": {book: [home points, home price, away points, away price]}.
SPREAD_PLAN = {"americanfootball_nfl": {"days": {1: "18:00"}, "season": ("09-01", "02-15")},
               "americanfootball_ncaaf": {"days": {1: "18:00"}, "season": ("08-20", "01-20")}}


def snaps(sport, today, plan=None):
    p = (plan or PLAN)[sport]
    out = []
    for y in range(FIRST, today.year + 1):
        a = date.fromisoformat(f"{y}-{p['season'][0]}")
        b = date.fromisoformat(f"{y + 1}-{p['season'][1]}")
        if y == FIRST:
            a = max(a, date(2020, 6, 7))
        d = a
        while d <= min(b, today - timedelta(days=1)):
            if d.weekday() in p["days"]:
                out.append(f"{d.isoformat()}T{p['days'][d.weekday()]}:00Z")
            d += timedelta(days=1)
    return out


def fetch(sport, snap, key, market="h2h"):
    q = urllib.parse.urlencode({"apiKey": key, "regions": "us", "markets": market, "oddsFormat": "american",
                                "date": snap})
    req = urllib.request.Request(API.format(sport=sport) + "?" + q, headers={"User-Agent": "D503-sports-engine/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        left = r.headers.get("x-requests-remaining")
        return json.load(r), (int(float(left)) if left not in (None, "") else None)


def rows(payload, snap, market="h2h"):
    out = []
    for ev in payload.get("data") or []:
        books = {}
        for bk in ev.get("bookmakers") or []:
            for mk in bk.get("markets") or []:
                if mk.get("key") != market:
                    continue
                pr = {o.get("name"): o for o in mk.get("outcomes") or []}
                h, a = pr.get(ev.get("home_team")), pr.get(ev.get("away_team"))
                if not (h and a):
                    continue
                if market == "spreads":
                    if h.get("point") is not None and a.get("point") is not None:
                        books[bk.get("key")] = [h["point"], h.get("price"), a["point"], a.get("price")]
                else:
                    books[bk.get("key")] = [h.get("price"), a.get("price")]
        if books:
            out.append({"snap": payload.get("timestamp") or snap, "id": ev.get("id"), "t": ev.get("commence_time"),
                        "h": ev.get("home_team"), "a": ev.get("away_team"), "b": books})
    return out


def main():
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        print("no ODDS_API_KEY secret - stopping")
        return 1
    os.makedirs(OUT, exist_ok=True)
    today = datetime.now(timezone.utc).date()
    budget_end = time.time() + 40 * 60
    market = os.environ.get("MARKET") or "h2h"
    plan = SPREAD_PLAN if market == "spreads" else PLAN
    for sport in plan:
        path = os.path.join(OUT, f"{sport}{'_spreads' if market == 'spreads' else ''}.jsonl.gz")
        have = set()
        if os.path.exists(path):
            with gzip.open(path, "rt") as f:
                for x in f:
                    have.add(json.loads(x).get("want"))
        todo = [s for s in snaps(sport, today, plan) if s not in have]
        print(f"{sport}: {len(todo)} snapshots to pull ({len(have)} already saved)", flush=True)
        for i, s in enumerate(todo):
            if time.time() > budget_end:
                print("out of time - the next run picks up here")
                return 0
            try:
                payload, left = fetch(sport, s, key, market)
            except Exception as e:                       # noqa: BLE001
                print(f"   {sport} {s}: {str(e)[:150]}", flush=True)
                if "401" in str(e) or "403" in str(e) or "422" in str(e):
                    print("the key / plan doesn't allow historical odds - stopping (nothing else spent)")
                    return 1
                time.sleep(3)
                continue
            got = rows(payload, s, market)
            with gzip.open(path, "at") as f:
                f.write(json.dumps({"want": s, "n": len(got)}) + "\n")
                for r in got:
                    f.write(json.dumps(r) + "\n")
            if i % 25 == 0 or i < 3:
                print(f"   {sport} {s}: {len(got)} games, credits left {left}", flush=True)
            if left is not None and left < GUARD:
                print(f"credit guard: {left} left - stopping")
                return 0
            time.sleep(0.3)
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
