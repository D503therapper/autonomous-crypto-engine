"""Which sportsbooks' public odds feeds can the engine read (backups for Bovada)? NFL + tennis for each; print status,
size, and a sample of what's in it."""
import json, re, time, urllib.request
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
     "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"}
C = {
    "draftkings nfl": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnj/v1/leagues/88808",
    "draftkings tennis (atp)": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnj/v1/leagues/2585",
    "draftkings old api nfl": "https://sportsbook.draftkings.com/sites/US-SB/api/v5/eventgroups/88808?format=json",
    "fanduel nfl": "https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=nfl&_ak=FhMFpcPWXMeyZxOx",
    "fanduel tennis": "https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=SPORT&eventTypeId=2&_ak=FhMFpcPWXMeyZxOx",
    "caesars/william hill nfl": "https://api.americanwagering.com/regions/us/locations/nj/brands/czr/sb/v3/sports/americanfootball/events/schedule",
    "caesars/william hill tennis": "https://api.americanwagering.com/regions/us/locations/nj/brands/czr/sb/v3/sports/tennis/events/schedule",
    "betrivers (kambi) nfl": "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/listView/american_football/nfl.json?lang=en_US&market=US",
    "betrivers (kambi) tennis": "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/listView/tennis.json?lang=en_US&market=US",
    "betrivers live tennis": "https://eu-offering-api.kambicdn.com/offering/v2018/rsiusnj/listView/tennis/all/all/all/in-play.json?lang=en_US&market=US",
    "unibet (kambi) tennis": "https://eu-offering-api.kambicdn.com/offering/v2018/ubusnj/listView/tennis.json?lang=en_US&market=US",
    "pinnacle nfl": "https://guest.api.arcadia.pinnacle.com/0.1/leagues/889/matchups",
    "pinnacle tennis sports": "https://guest.api.arcadia.pinnacle.com/0.1/sports/33/matchups?withSpecials=false",
    "betmgm nfl": "https://sports.nj.betmgm.com/en/sports/api/widget/widgetdata?layoutSize=Large&page=CompetitionLobby&sportId=11&regionId=9&competitionId=35",
}
PH = {**H, "X-API-Key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R", "Referer": "https://www.pinnacle.com/"}
for name, u in C.items():
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=PH if "pinnacle" in name else H), timeout=20)
        body = r.read().decode("utf-8", "ignore")
        am = re.findall(r'"(?:american|americanOdds|oddsAmerican|price)"\s*:\s*"?([+-]?\d{3,4})', body)
        live = body.count('"live":true') + body.count('"isLive":true') + body.count('"state":"STARTED"') + body.count('"inPlay":true')
        names = re.findall(r'"(?:name|participant|description|englishName)"\s*:\s*"([A-Z][a-z]+ [A-Z][a-zA-Z\-]+)"', body)[:4]
        print(f"OK  {name}: HTTP {r.status}, {len(body)//1024} KB, prices seen: {len(am)} e.g. {am[:4]}, live flags: {live}, names: {names}")
    except Exception as e:
        print(f"ERR {name}: {str(e)[:90]}")
    time.sleep(1)
