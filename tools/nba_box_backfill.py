"""🏀 THE FULL NBA BOX SCORE (10/23 - the player-rating study died on 6 stats: "the box holds no threes / steals /
blocks / turnovers"). sports_roster.KEEP["nba"] now keeps threes, free throws, offensive / defensive rebounds, steals,
blocks, turnovers and fouls from every NEW download. This job (nba_box_backfill.yml) fills the past: (1) this season's
games stored with the old 6 stats are fetched again and their rows REPLACED; (2) the seasons before our box scores
start (2016-17 .. 2020-21 - the games file holds them, sports_roster.sync only reaches back to 2021) are downloaded;
(3) then 2021-22 .. 2025-26 are fetched again for the new stats. Newest first inside each step, ~36 minutes a run until
it's caught up, then it finds nothing to do. ESPN's public summary endpoint, the same one the rosters job uses - no
paid API. State: data/sports/roster/_nba_backfill.json (games ESPN has no box for).

    python tools/nba_box_backfill.py [minutes]
"""
import csv
import gzip
import io
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.getcwd())
import sports_data as sd                  # noqa: E402
import sports_roster as sr                # noqa: E402

STATE = os.path.join(sr.DIR, "_nba_backfill.json")
NEW_KEY = "steals"                        # a stored game whose rows hold no 'steals' was saved with the old 6 stats
SINCE = "2016-07-01"                      # the games file's first NBA season
WORKERS = 4


def stored_keys(league="nba"):
    """{gid: True if its rows already hold the new stats}."""
    out = {}
    for r in sr.load(league):
        if r["gid"] in out and out[r["gid"]]:
            continue
        try:
            out[r["gid"]] = NEW_KEY in json.loads(r.get("stats") or "{}")
        except ValueError:
            out[r["gid"]] = False
    return out


def replace(league, rows, gids):
    """Drop the stored rows of these games and add the fresh ones (sports_roster.add keeps the FIRST copy, so the
    old rows have to go first)."""
    by_season = defaultdict(set)
    for g in gids:
        by_season[g.split(":", 1)[0]].add(g)
    seasons = {sr._season(r["start"], league) for r in rows}
    for season in seasons:
        p = sr._path(league, season)
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rt", newline="") as fh:
            old = [r for r in csv.DictReader(fh) if r["gid"] not in gids]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=sr.FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(old)
        with gzip.open(p + ".tmp", "wt", newline="") as fh:
            fh.write(buf.getvalue())
        os.replace(p + ".tmp", p)
    sr.add(league, rows)


def jobs_for(games, have, none, now_season):
    """The games to fetch, in order: this season's old-stat games, the seasons before our box scores (oldest first),
    then the stored seasons again for the new stats (newest first)."""
    import sports_model as sm
    fin = [g for g in sm.finals(games, "nba") if g["start"] >= SINCE and g["id"] not in none]
    def season(g):
        return int(sr._season(g["start"], "nba"))
    this = sorted((g for g in fin if season(g) == now_season and have.get(g["id"]) is False), key=lambda g: g["start"], reverse=True)
    missing = sorted((g for g in fin if g["id"] not in have and season(g) < now_season), key=lambda g: g["start"])
    old = sorted((g for g in fin if have.get(g["id"]) is False and season(g) < now_season), key=lambda g: g["start"], reverse=True)
    return [(g["id"], g["start"]) for g in this + missing + old]


def main(minutes=36):
    games = sd.load_games("nba")
    try:
        with open(STATE) as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    none = set(state.get("none", []))
    have = stored_keys()
    now_season = int(sr._season(max(g["start"] for g in games.values()), "nba")) if games else 2026
    jobs = jobs_for(games, have, none, now_season)
    print(f"nba box backfill: {len(jobs)} games to fetch ({sum(1 for g, _ in jobs if g not in have)} never stored, "
          f"{sum(1 for g, _ in jobs if g in have)} stored with the old 6 stats); {len(none)} known to have no box")
    if not jobs:
        print("caught up - nothing to do")
        return
    deadline = time.time() + minutes * 60
    got, refetched, new_none, fails = [], set(), set(), 0

    def run(job):
        gid, start = job
        if time.time() >= deadline:
            return job, None
        return job, sr.fetch("nba", gid, start)
    with ThreadPoolExecutor(WORKERS) as ex:
        for (gid, _), rows in ex.map(run, jobs):
            if rows is None:
                fails += 1
                continue
            if not rows:
                new_none.add(gid)
                continue
            got.extend(rows)
            if gid in have:
                refetched.add(gid)
    if got:
        replace("nba", got, refetched)
    none |= new_none
    state["none"] = sorted(none)[-20000:]
    os.makedirs(sr.DIR, exist_ok=True)
    with open(STATE, "w") as f:
        json.dump(state, f)
    n_games = len({r["gid"] for r in got})
    with_new = sum(1 for r in got if NEW_KEY in json.loads(r["stats"]))
    print(f"saved {n_games} games ({len(refetched)} replaced), {with_new} of {len(got)} rows carry the new stats; "
          f"{len(new_none)} with no box score; {fails} not reached / out of time; "
          f"{len(jobs) - n_games - len(new_none)} still to go")
    for e in sd.ERRORS[:3]:
        print(f"   e.g. {e}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 36)
