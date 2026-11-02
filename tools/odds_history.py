"""ODDS HISTORY (10/1, the owner paid one month of The Odds API to find out if the engine can beat football lines
early): moneyline snapshots for NFL + college football since the 2020 season, several per week (the midweek prices
our data never had - only the stale summer open and the close). Runs in GitHub Actions with the owner's key in the
ODDS_API_KEY secret (never in the repo). Resumable: snapshots already saved are skipped. A credit guard stops it well
before the plan runs dry.

Saves data/sports/odds_history/{sport}.jsonl.gz - one row per game per snapshot:
  {"snap": "...Z", "id": event id, "t": kickoff, "h": home, "a": away, "b": {book: [home price, away price]}}

11/1 (the owner OK'd spending the refilled 20,000-credit plan): NBA + NHL too (DAILY_PLAN / DAILY_SPREAD_PLAN) - the
seasons our game files have only the ESPN close for (the ESPN open starts 2023-24). MARKET=estimate prints the snapshot
count and the credit cost of every plan WITHOUT calling the API (no key needed)."""
import csv
import glob
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
GUARD = int(os.environ.get("GUARD") or 2500)   # stop with this many credits left (the plan has 20,000)
# when to look, by weekday (Mon=0): NFL Tue/Thu/Sat + Sunday morning; college Tue/Thu + Saturday morning
PLAN = {"americanfootball_nfl": {"days": {1: "18:00", 3: "18:00", 5: "18:00", 6: "15:00"}, "season": ("09-01", "02-15")},
        "americanfootball_ncaaf": {"days": {1: "18:00", 3: "18:00", 5: "14:00"}, "season": ("08-20", "01-20")}}
FIRST = 2020
# SPREADS (the owner, 10/1: "we get +9.5 and it drops to +3.5"): one Tuesday look a week - the close is already in our
# games - so ~2,800 credits. Rows: "b": {book: [home points, home price, away points, away price]}.
SPREAD_PLAN = {"americanfootball_nfl": {"days": {1: "18:00"}, "season": ("09-01", "02-15")},
               "americanfootball_ncaaf": {"days": {1: "18:00"}, "season": ("08-20", "01-20")}}

# NBA / NHL (11/1): ONE look a day at 15:00Z (7-8 AM PT - the 8 AM board's hour), every day that has a regular-season or
# playoff game that day or the next. Each look holds that day's games (the game-day morning number - after every team's
# last game ended, so always FAIR) AND the next day's games the books already opened (~28 hours out - the overnight
# opener, like ESPN's open: teams that play tonight get no next-day line yet, so that look stays fair too). The close is
# already in our game files (ESPN, 2018 on: moneyline + spread). Seasons 2020-21..2022-23 = the held-out seasons the
# 10/30 NBA opening-line studies (ESPN open, 2023-26 only) never had; the 2020 bubble is skipped (one neutral site).
# The game days come from data/sports/games/{league}/*.csv, so no snapshot is spent on a dark day.
DAILY_PLAN = {"basketball_nba": {"league": "nba", "at": "15:00", "from": "2020-12-01", "to": "2023-07-01",
                                 "stypes": ("2", "3")},
              "icehockey_nhl": {"league": "nhl", "at": "15:00", "from": "2021-01-01", "to": "2023-07-01",
                                "stypes": ("2",)}}
# NBA spreads and the NHL: the regular season only (the hockey Dog / the NBA spread studies are regular-season bets;
# the NHL playoffs would cost ~1,500 more and push the plan past the guard). 11/1 estimate: NBA h2h 658 + NBA spreads
# 489 + NHL h2h 515 snapshots = 16,620 credits of the 17,500 over the guard.
DAILY_SPREAD_PLAN = {"basketball_nba": dict(DAILY_PLAN["basketball_nba"], stypes=("2",))}
GAMES = "data/sports/games"
COST = 10              # The Odds API historical odds: 10 credits per snapshot per market per region (regions=us = 1)
# the order to spend the 11/1 refill in (study value, NBA first): (market, sport, newest_first)
BUDGET_ORDER = [("h2h", "basketball_nba", False), ("spreads", "basketball_nba", True), ("h2h", "icehockey_nhl", False)]


def plan_for(market):
    return {**SPREAD_PLAN, **DAILY_SPREAD_PLAN} if market == "spreads" else {**PLAN, **DAILY_PLAN}


def game_days(league, stypes=("2", "3"), games_dir=None):
    """Every US-evening game date (start - 9h, so a 7 PM ET tip at 00:00Z counts the day before) in the game files."""
    out = set()
    for f in glob.glob(os.path.join(games_dir or GAMES, league, "*.csv")):
        with open(f, newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("stype") in stypes and r.get("start"):
                    t = datetime.fromisoformat(r["start"].replace("Z", "+00:00"))
                    out.add((t - timedelta(hours=9)).date())
    return out


def daily_snaps(p, today, games_dir=None):
    a, b = date.fromisoformat(p["from"]), date.fromisoformat(p["to"])
    days = set()
    for d in game_days(p["league"], p.get("stypes", ("2", "3")), games_dir):
        if a <= d < b:
            days.update((d, d - timedelta(days=1)))          # (the day before: the next-day opener look)
    return [f"{d.isoformat()}T{p['at']}:00Z" for d in sorted(days) if a <= d < min(b, today)]


def snaps(sport, today, plan=None, games_dir=None):
    p = (plan or PLAN)[sport]
    if "league" in p:
        return daily_snaps(p, today, games_dir)
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


def saved(path):
    have = set()
    if os.path.exists(path):
        with gzip.open(path, "rt") as f:
            for x in f:
                have.add(json.loads(x).get("want"))
    return have


def out_path(sport, market):
    return os.path.join(OUT, f"{sport}{'_spreads' if market == 'spreads' else ''}.jsonl.gz")


def estimate(today, sports=None, guard=None, left=20000, games_dir=None):
    """DRY RUN (no API call): [{market, sport, todo, have, credits, fits, ...}] in BUDGET_ORDER, then every other plan,
    and how many of each fit in the credits we can spend (left - guard) taken in that order."""
    guard = GUARD if guard is None else guard
    order = [(m, s) for m, s, _ in BUDGET_ORDER]
    order += [(m, s) for m in ("h2h", "spreads") for s in plan_for(m) if (m, s) not in order]
    out, room = [], max(0, left - guard)
    for m, s in order:
        if sports and s not in sports:
            continue
        have = saved(out_path(s, m))
        todo = [x for x in snaps(s, today, plan_for(m), games_dir) if x not in have]
        fits = min(len(todo), room // COST)
        room -= fits * COST
        out.append({"market": m, "sport": s, "todo": len(todo), "have": len(have), "credits": len(todo) * COST,
                    "fits": fits, "first": todo[0] if todo else None, "last": todo[-1] if todo else None})
    return out


def credits_left(key):
    """The plan's credits left - from the FREE sports list (costs 0)."""
    req = urllib.request.Request("https://api.the-odds-api.com/v4/sports?" + urllib.parse.urlencode({"apiKey": key}),
                                 headers={"User-Agent": "D503-sports-engine/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.headers.get("x-requests-remaining"), r.headers.get("x-requests-used")


def main():
    only = os.environ.get("SPORTS")                          # e.g. "basketball_nba" - one sport only
    if os.environ.get("MARKET") == "estimate":               # DRY RUN: never calls the API, needs no key
        left = int(os.environ.get("LEFT") or 20000)
        est = estimate(datetime.now(timezone.utc).date(), only.split(",") if only else None, GUARD, left)
        print(f"DRY RUN - no API call. {COST} credits a snapshot per market; {left} credits - guard {GUARD} "
              f"= {max(0, left - GUARD)} to spend, in this order:")
        for r in est:
            print(f"  {r['market']:8s} {r['sport']:24s} {r['todo']:5d} snapshots ({r['have']} saved) = "
                  f"{r['credits']:6d} credits, {r['fits']} fit  [{r['first']} .. {r['last']}]")
        print(f"  total {sum(r['credits'] for r in est)} credits for everything listed")
        return 0
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        print("no ODDS_API_KEY secret - stopping")
        return 1
    left, used = credits_left(key)
    print(f"credits left {left}, used {used}", flush=True)
    if os.environ.get("MARKET") == "check":
        return 0
    if left is not None and int(float(left)) < GUARD + 100:
        print("not enough credits for a pull - stopping")
        return 0
    os.makedirs(OUT, exist_ok=True)
    today = datetime.now(timezone.utc).date()
    budget_end = time.time() + 40 * 60
    market = os.environ.get("MARKET") or "h2h"
    if market not in ("h2h", "spreads"):
        print(f"unknown market {market!r} - check / estimate / h2h / spreads")
        return 1
    plan = plan_for(market)
    for sport in plan:
        if only and sport not in only.split(","):
            continue
        path = out_path(sport, market)
        have = saved(path)
        todo = [s for s in snaps(sport, today, plan) if s not in have]
        if os.environ.get("NEWEST_FIRST"):
            todo.reverse()                                   # (few credits left: the latest seasons first)
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
