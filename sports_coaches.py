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
SEASONS = range(2016, 2029)                   # (ESPN names NBA / NHL / college hoops seasons by the year they end)


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


# THE COACHING STUDY, round 1 (9/30, closing prices 2018-26, season by season - SPORTS_FINDINGS.md):
#   NFL dogs with a 10+ year head coach: +10.6% (7 of 8 seasons) vs -3.5% for every dog; ATS +2.0% (6 of 8)
#   a NEW coach's team as a favorite (1st year with the team): NBA -6.2% (worse 7 of 8), college hoops -8.5% (7 of 8)
VET_DOG = {"nfl": 10}
NEW_FAV = ("nba", "ncaab")


def espn_season(league, iso):
    y, m = int(iso[:4]), int(iso[5:7])
    if league in ("nba", "nhl", "ncaab"):
        return y + 1 if m >= 7 else y
    if league in ("nfl", "ncaaf"):
        return y - 1 if m < 7 else y
    return y


def states(now_iso, path=PATH):
    """{(league, team id): (years as a head coach, new with this team this season)} for this season."""
    try:
        with open(path) as f:
            c = json.load(f)
    except (OSError, ValueError):
        return {}
    out = {}
    for lg, seasons in c.items():
        s = espn_season(lg, now_iso)
        cur, prev = seasons.get(str(s)) or {}, seasons.get(str(s - 1)) or {}
        for t, cs in cur.items():
            if not cs:
                continue
            p = (prev.get(t) or [{}])[0].get("id")
            out[(lg, t)] = (cs[0].get("exp"), bool(p) and p != cs[0].get("id"))
    return out
