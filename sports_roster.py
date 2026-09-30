"""EVERY PLAYER, EVERY SPORT (the owner, 9/30: "the engine needs to know all aspects - the players, the stars, how's
the bench, how's the backup, the coaches - absolutely everything").

sports_players keeps only the starting QB / pitcher / goalie. This keeps EVERYBODY in the same ESPN box score (no
extra calls: the same download), in every sport - NFL, college football, NBA, college hoops, NHL, MLB - one row per
player per game: who, what position, did he start, minutes / time on ice / snaps-ish volume, and the few numbers
that say how much he mattered. From it (sports_roster.stars / bench) the engine learns who the stars are, how deep a
bench is, and how good a backup is. Nothing here touches a pick until a study proves it on seasons it never saw.

Stored gzip'd, one file per league per season: data/sports/roster/{league}_{season}.csv.gz.
"""
import csv
import gzip
import io
import json
import os
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import sports_data as sd

DIR = os.path.join(sd.DATA, "roster")
LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "nhl", "mlb")
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={eid}"
# the few numbers per stat group that say how much a player mattered (ESPN's own key names; unknown keys are skipped)
KEEP = {
    "nba": ("minutes", "points", "rebounds", "assists", "plusMinus", "fieldGoalsMade-fieldGoalsAttempted"),
    "ncaab": ("minutes", "points", "rebounds", "assists", "fieldGoalsMade-fieldGoalsAttempted"),
    "nfl": ("completions/passingAttempts", "passingYards", "passingTouchdowns", "interceptions", "rushingAttempts",
            "rushingYards", "rushingTouchdowns", "receptions", "receivingYards", "receivingTouchdowns",
            "totalTackles", "sacks", "passesDefended"),
    "nhl": ("timeOnIce", "goals", "assists", "plusMinus", "shotsTotal", "saves", "shotsAgainst", "goalsAgainst"),
    "mlb": ("atBats", "hits", "homeRuns", "RBIs", "walks", "strikeouts", "fullInnings.partInnings", "earnedRuns"),
}
KEEP["ncaaf"] = KEEP["nfl"]
FIELDS = ["gid", "start", "team", "pid", "player", "pos", "group", "starter", "stats"]


def _season(start, league):
    y, m = int(start[:4]), int(start[5:7])
    return str(y) if league == "mlb" else str(y if m >= 7 else y - 1)       # a fall-to-spring season = its first year


def parse(league, gid, start, payload):
    """Every player with stats in an ESPN summary's box score -> rows. Never raises on a shape it doesn't know."""
    out = []
    keep = KEEP.get(league, ())
    for team in (payload.get("boxscore") or {}).get("players") or []:
        tid = str((team.get("team") or {}).get("id") or "")
        for grp in team.get("statistics") or []:
            keys = grp.get("keys") or grp.get("labels") or []
            for a in grp.get("athletes") or []:
                vals = a.get("stats") or []
                if not vals or a.get("didNotPlay"):
                    continue
                ath = a.get("athlete") or {}
                st = {k: v for k, v in zip(keys, vals) if k in keep and v not in ("", "--", None)}
                if not st:
                    continue
                out.append({"gid": gid, "start": start, "team": tid, "pid": str(ath.get("id") or ""),
                            "player": ath.get("displayName") or "?",
                            "pos": ((ath.get("position") or {}).get("abbreviation") or ""),
                            "group": grp.get("name") or grp.get("type") or "", "starter": "1" if a.get("starter") else "0",
                            "stats": json.dumps(st, separators=(",", ":"))})
    return out


def _path(league, season):
    return os.path.join(DIR, f"{league}_{season}.csv.gz")


def have_ids(league):
    """Game ids already stored for a league (every season file)."""
    ids = set()
    if not os.path.isdir(DIR):
        return ids
    for f in os.listdir(DIR):
        if f.startswith(league + "_") and f.endswith(".csv.gz"):
            with gzip.open(os.path.join(DIR, f), "rt", newline="") as fh:
                ids.update(r["gid"] for r in csv.DictReader(fh))
    return ids


def add(league, rows):
    """Append rows to their season files (sorted, deduped by game + player)."""
    by = defaultdict(list)
    for r in rows:
        by[_season(r["start"], league)].append(r)
    os.makedirs(DIR, exist_ok=True)
    for season, new in by.items():
        p = _path(league, season)
        old = []
        if os.path.exists(p):
            with gzip.open(p, "rt", newline="") as fh:
                old = list(csv.DictReader(fh))
        seen, allr = set(), []
        for r in old + new:
            k = (r["gid"], r["pid"] or r["player"], r["group"])
            if k not in seen:
                seen.add(k)
                allr.append(r)
        allr.sort(key=lambda r: (r["start"], r["gid"]))
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(allr)
        with gzip.open(p + ".tmp", "wt", newline="") as fh:
            fh.write(buf.getvalue())
        os.replace(p + ".tmp", p)


def load(league, seasons=None):
    """Rows for a league (optionally only some seasons), sorted by start."""
    rows = []
    if not os.path.isdir(DIR):
        return rows
    for f in sorted(os.listdir(DIR)):
        if f.startswith(league + "_") and f.endswith(".csv.gz"):
            if seasons and f[len(league) + 1:-7] not in {str(s) for s in seasons}:
                continue
            with gzip.open(os.path.join(DIR, f), "rt", newline="") as fh:
                rows.extend(csv.DictReader(fh))
    rows.sort(key=lambda r: (r["start"], r["gid"]))
    return rows


def fetch(league, gid, start):
    url = SUMMARY.format(path=sd.LEAGUES[league][0], eid=gid.split(":", 1)[1])
    for i in range(2):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:   # (exactly like sports_players' box scores, which work)
                payload = json.load(r)
            rows = parse(league, gid, start, payload)
            if not rows and (payload.get("boxscore") or {}).get("players"):
                sd.ERRORS.append(f"roster {gid}: a box score we couldn't read")   # a shape we don't know: retry
                return None                                  # later, never mark it 'no box score' for good
            return rows
        except Exception as e:                           # noqa: BLE001
            if i == 1:
                sd.ERRORS.append(f"roster {gid}: {str(e)[:80]}")
                return None
            time.sleep(1.5)


NONE_PATH = os.path.join(DIR, "_no_box.json")


def run_backfill(minutes=38):
    """The download job (rosters.yml): football first (in season), then hockey, hoops, baseball - until time's up."""
    import sports_data as _sd
    games = _sd.load_games()
    try:
        with open(NONE_PATH) as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    end = time.time() + minutes * 60
    import sports_model as sm                            # a quick probe first: 3 recent games, say what came back
    probe = sorted((g for lg in ("nfl", "nba", "nhl") for g in sm.finals(games, lg)), key=lambda g: g["start"])[-3:]
    ok = 0
    for g in probe:
        n_err = len(_sd.ERRORS)
        rows = fetch(g["league"], g["id"], g["start"])
        print(f"probe {g['id']}: " + (f"{len(rows)} players" if rows is not None else f"failed - {_sd.ERRORS[n_err:][:1]}"))
        ok += rows is not None
    if not ok:
        print("every probe failed: stopping (nothing to gain hammering ESPN)")
        return
    for group in (("nfl", "ncaaf"), ("nhl",), ("nba", "ncaab"), ("mlb",)):
        left = end - time.time()
        if left < 30:
            break
        n_err = len(_sd.ERRORS)
        got, todo, fails = sync(games, state, budget_s=left, leagues=group)
        print(f"rosters {'+'.join(group)}: {got} games added, {todo - got} still to go, {fails} not reached")
        for e in _sd.ERRORS[n_err:n_err + 3]:
            print(f"   e.g. {e}")                        # (the first run failed silently: say why)
        os.makedirs(DIR, exist_ok=True)
        with open(NONE_PATH, "w") as f:
            json.dump(state, f)


def sync(games, state, workers=6, budget_s=300, leagues=LEAGUES, since="2021-07-01"):
    """Box scores for finished real games we don't have yet: newest first (they matter most), back to `since` (the
    recent seasons - the owner, 9/30: the sports have changed, the old ones hurt more than they help)."""
    import sports_model as sm
    none = set(state.get("roster_none", []))
    jobs = []
    for lg in leagues:
        have = have_ids(lg)
        jobs += [(lg, g["id"], g["start"]) for g in sm.finals(games, lg)
                 if g["start"] >= since and g["id"] not in have and g["id"] not in none]
    jobs.sort(key=lambda j: j[2], reverse=True)
    deadline = time.time() + budget_s

    def run(job):
        return job, (fetch(*job) if time.time() < deadline else None)
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(run, jobs))
    got = defaultdict(list)
    for (lg, gid, _), rows in results:
        if rows is None:
            continue
        if rows:
            got[lg].extend(rows)
        else:
            none.add(gid)                                # ESPN has no box score for it: don't ask again
    for lg, rows in got.items():
        add(lg, rows)
    state["roster_none"] = sorted(none)[-50000:]
    n_games = sum(len({r["gid"] for r in rows}) for rows in got.values())
    return n_games, len(jobs), sum(1 for _, r in results if r is None)


def _num(v):
    try:
        return float(str(v).split("-")[0].split("/")[0].split(":")[0])
    except ValueError:
        return 0.0


def volume(league, st):
    """How much a player was on the floor / field / ice in one game (the basis of 'who's a regular')."""
    if league in ("nba", "ncaab"):
        return _num(st.get("minutes"))
    if league == "nhl":
        t = str(st.get("timeOnIce") or "0")
        m, _, s = t.partition(":")
        return _num(m) + (_num(s) / 60 if s else 0)
    if league == "mlb":
        return _num(st.get("atBats")) + 3 * _num(st.get("fullInnings.partInnings"))
    return (_num(st.get("completions/passingAttempts", "0/0").split("/")[-1]) + _num(st.get("rushingAttempts"))
            + 2 * _num(st.get("receptions")) + _num(st.get("totalTackles")))


if __name__ == "__main__":
    import sys
    run_backfill(float(sys.argv[1]) if len(sys.argv) > 1 else 38)
