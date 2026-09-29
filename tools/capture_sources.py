"""Snapshot every backup source (books, splits, scoreboards) exactly as the engine's servers see it, so the readers can be
built and tested against real data offline. Writes samples/<name>.json.gz + samples/manifest.json."""
import gzip, json, os, time, urllib.request
from datetime import datetime, timezone
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
     "Accept": "application/json, text/plain, text/html, */*", "Accept-Language": "en-US,en;q=0.9"}
PIN = {**H, "X-API-Key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R", "Referer": "https://www.pinnacle.com/"}
K = "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/listView/{p}.json?lang=en_US&market=US"
P = "https://guest.api.arcadia.pinnacle.com/0.1/"
FD = "https://sbapi.nj.sportsbook.fanduel.com/api/{p}&_ak=FhMFpcPWXMeyZxOx"
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
    # Pinnacle: matchups + straight markets (tennis sport 33, NFL 889, MLB 246, NHL 1456, NBA 487, NCAAF 880, NCAAB 493)
    "pin_tennis_matchups": P + "sports/33/matchups?withSpecials=false", "pin_tennis_markets": P + "sports/33/markets/straight?primaryOnly=true",
    "pin_nfl_matchups": P + "leagues/889/matchups", "pin_nfl_markets": P + "leagues/889/markets/straight",
    "pin_mlb_matchups": P + "leagues/246/matchups", "pin_mlb_markets": P + "leagues/246/markets/straight",
    "pin_nhl_matchups": P + "leagues/1456/matchups", "pin_nhl_markets": P + "leagues/1456/markets/straight",
    "pin_live_tennis": P + "sports/33/matchups/live", "pin_live_markets_tennis": P + "sports/33/markets/live/straight",
    # FanDuel
    "fd_nfl": FD.format(p="content-managed-page?page=CUSTOM&customPageId=nfl"),
    "fd_mlb": FD.format(p="content-managed-page?page=CUSTOM&customPageId=mlb"),
    "fd_tennis": FD.format(p="content-managed-page?page=SPORT&eventTypeId=2"),
    "fd_live": FD.format(p="in-play?eventTypeId=0&timezone=America%2FLos_Angeles"),
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
}
os.makedirs("samples", exist_ok=True)
man = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "sources": {}}
for name, u in S.items():
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=PIN if name.startswith("pin") else H), timeout=25)
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
