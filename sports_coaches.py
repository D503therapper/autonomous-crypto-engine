"""COACHES (the owner, 9/30: "a coaching study - there's something to it"). Every team's head coach(es), season by
season, every sport, from ESPN's own API (the same place the games come from - no borrowed keys, no disguises):
  sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/seasons/{year}/teams/{id}/coaches
A season with two coaches = a change during it (a firing / an interim). Saved to data/sports/coaches.json:
  {league: {season: {team id: [{"id", "name", "exp", ...whatever ESPN adds}]}}}
Runs in GitHub Actions (coaches.yml) - this sandbox can't reach ESPN. The first run also saves raw samples
(data/sports/coaches_probe.json) so the parsing can be checked."""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import sports_data as sd

PATH = os.path.join(sd.DATA, "coaches.json")
PROBE = os.path.join(sd.DATA, "coaches_probe.json")
CORE = "https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/seasons/{year}/teams/{team}/coaches?limit=50"
SEASONS = range(2016, 2027)


def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return json.load(r)
        except Exception as e:                               # noqa: BLE001
            if i == 2:
                return {"_error": str(e)[:120]}
            time.sleep(1.5)


def coach(ref):
    """One coach entry (ESPN's fields, trimmed): id, name, experience, and any record summary it carries."""
    d = get(ref.replace("http://", "https://"))
    if not isinstance(d, dict) or d.get("_error"):
        return None
    out = {"id": str(d.get("id") or ""), "name": " ".join(x for x in (d.get("firstName"), d.get("lastName")) if x),
           "exp": d.get("experience")}
    for k in ("records", "record", "careerRecords", "startDate", "endDate", "dateOfBirth"):
        if k in d:
            out[k] = d[k] if not isinstance(d[k], dict) or "$ref" not in d[k] else d[k]["$ref"]
    return out


def teams_by_season(games, league):
    """{season: {team ids that played}} from our own games file."""
    out = {}
    for g in games.values():
        if g.get("league") != league or not g.get("start"):
            continue
        y, m = int(g["start"][:4]), int(g["start"][5:7])
        season = y
        if league in ("nba", "nhl", "ncaab") and m >= 7:
            season = y + 1                               # ESPN names these seasons by the year they END (2024-25 = 2025)
        elif league in ("nba", "nhl", "ncaab"):
            season = y
        elif league in ("nfl", "ncaaf") and m < 7:
            season = y - 1                               # football: a January playoff game is last season's
        out.setdefault(season, set()).update({g["home"], g["away"]})
    return out


def run(minutes=38, leagues=("nfl", "nba", "nhl", "mlb", "ncaaf", "ncaab")):
    try:
        with open(PATH) as f:
            have = json.load(f)
    except (OSError, ValueError):
        have = {}
    games = sd.load_games()
    end = time.time() + minutes * 60
    probe = {}
    for lg in leagues:
        sport, league = sd.LEAGUES[lg][0].split("/")
        jobs = [(season, t) for season, ts in sorted(teams_by_season(games, lg).items(), reverse=True) if season in SEASONS
                for t in sorted(ts) if t and str(t) not in (have.get(lg, {}).get(str(season)) or {})]

        def one(job):
            season, t = job
            if time.time() > end:
                return job, None
            d = get(CORE.format(sport=sport, league=league, year=season, team=t))
            if not isinstance(d, dict) or d.get("_error"):
                return job, None
            if lg not in probe:
                probe[lg] = {"list": d}
            cs = [coach(it["$ref"]) for it in d.get("items") or [] if isinstance(it, dict) and it.get("$ref")]
            if lg in probe and "coach" not in probe[lg] and d.get("items"):
                probe[lg]["coach"] = get(d["items"][0]["$ref"].replace("http://", "https://"))
            return job, [c for c in cs if c]
        with ThreadPoolExecutor(6) as ex:
            res = list(ex.map(one, jobs))
        got = 0
        for (season, t), cs in res:
            if cs is None:
                continue
            have.setdefault(lg, {}).setdefault(str(season), {})[str(t)] = cs
            got += 1
        print(f"coaches {lg}: {got} team-seasons added, {len(jobs) - got} still to go", flush=True)
        with open(PATH, "w") as f:
            json.dump(have, f, separators=(",", ":"))
        if time.time() > end:
            break
    if probe:
        with open(PROBE, "w") as f:
            json.dump(probe, f, indent=1)


if __name__ == "__main__":
    run(float(sys.argv[1]) if len(sys.argv) > 1 else 38)
