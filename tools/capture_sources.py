"""Snapshot every backup source (books, splits, scoreboards) exactly as the engine's servers see it, so the readers can be
built and tested against real data offline. Writes samples/<name>.json.gz + samples/manifest.json."""
import gzip, json, os, time, urllib.request
from datetime import datetime, timezone
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
     "Accept": "application/json, text/plain, text/html, */*", "Accept-Language": "en-US,en;q=0.9"}
K = "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/listView/{p}.json?lang=en_US&market=US"
day = datetime.now(timezone.utc).strftime("%Y%m%d")
S = {
    # BetRivers (Kambi): pregame + in-play, every league we cover + tennis
    "kambi_tennis_inplay": K.format(p="tennis/all/all/all/in-play"),
    "kambi_tennis": K.format(p="tennis"),
    "kambi_nfl": K.format(p="american_football/nfl"), "kambi_nfl_inplay": K.format(p="american_football/nfl/all/all/in-play"),
    "kambi_ncaaf": K.format(p="american_football/ncaaf"), "kambi_mlb": K.format(p="baseball/mlb"),
    "kambi_mlb_inplay": K.format(p="baseball/mlb/all/all/in-play"), "kambi_nhl": K.format(p="ice_hockey/nhl"),
    "kambi_nba": K.format(p="basketball/nba"), "kambi_ncaab": K.format(p="basketball/ncaab"),
    "kambi_all_inplay": K.format(p="all/all/all/all/in-play"),
    # splits + lines pages
    "yahoo_nfl": "https://sports.yahoo.com/nfl/odds/", "yahoo_mlb": "https://sports.yahoo.com/mlb/odds/",
    "yahoo_nhl": "https://sports.yahoo.com/nhl/odds/", "yahoo_nba": "https://sports.yahoo.com/nba/odds/",
    "yahoo_ncaaf": "https://sports.yahoo.com/college-football/odds/",
    "vi_nfl": "https://www.vegasinsider.com/nfl/odds/las-vegas/", "covers_nfl": "https://contests.covers.com/consensus/topconsensus/nfl/overall",
    # ESPN scoreboards (the live game list backup) + odds
    "espn_nfl": "https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    "espn_mlb": f"https://site.web.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={day}",
    "espn_nhl": f"https://site.web.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates={day}",
    "an_mlb": f"https://api.actionnetwork.com/web/v1/scoreboard/mlb?period=game&date={day}",
    # who's actually playing (MLB's own public stats site): rosters, lineups, season stats - the Judge miss, 9/29
    "mlb_teams": "https://statsapi.mlb.com/api/v1/teams?sportId=1",
    "mlb_roster_nyy_active": "https://statsapi.mlb.com/api/v1/teams/147/roster?rosterType=active",
    "mlb_roster_nyy_40": "https://statsapi.mlb.com/api/v1/teams/147/roster?rosterType=40Man",
    "mlb_hitting_nyy": "https://statsapi.mlb.com/api/v1/stats?stats=season&group=hitting&season=2026&teamId=147&playerPool=ALL&limit=60",
    "mlb_sched_lineups": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=" + datetime.now(timezone.utc).strftime("%Y-%m-%d") + "&hydrate=lineups,probablePitcher",
    "mlb_sched_lineups_prev": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-09-29&endDate=2026-09-30&hydrate=lineups",
    "mlb_transactions_nyy": "https://statsapi.mlb.com/api/v1/transactions?teamId=147&startDate=2026-09-01&endDate=2026-09-30",
    "espn_roster_nyy": "https://site.web.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/10/roster",
    "espn_summary_nyy": "https://site.web.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event=401907924",
    "espn_inj_mlb": "https://site.web.api.espn.com/apis/site/v2/sports/baseball/mlb/injuries",
}
os.makedirs("samples", exist_ok=True)
man = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "sources": {}}
for name, u in S.items():
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=25)
        body = r.read()
        with gzip.open(f"samples/{name}.gz", "wb") as f:
            f.write(body)
        man["sources"][name] = {"url": u, "status": r.status, "kb": len(body) // 1024}
        print("OK ", name, r.status, len(body) // 1024, "KB")
    except Exception as e:
        man["sources"][name] = {"url": u, "error": str(e)[:120]}
        print("ERR", name, str(e)[:100])
    time.sleep(0.7)
json.dump(man, open("samples/manifest.json", "w"), indent=1)
