"""Probe sports data sources from the GitHub runner (ESPN answered 403 to every call from Actions).
Prints HTTP status, content type and a snippet for each source/header combination."""
import urllib.request

BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
D = "20260926"
HEADERS = {
    "none": {},
    "browser": {"User-Agent": BROWSER, "Accept": "application/json,text/plain,*/*", "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.espn.com/", "Origin": "https://www.espn.com"},
    "iphone": {"User-Agent": IPHONE, "Accept": "*/*"},
}
CANDIDATES = [
    ("espn site", f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={D}"),
    ("espn site web", f"https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={D}"),
    ("espn v2 web", f"https://site.web.api.espn.com/apis/v2/scoreboard/header?sport=football&league=nfl&dates={D}"),
    ("espn core", f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events?dates={D}"),
    ("espn cdn", f"https://cdn.espn.com/core/nfl/scoreboard?xhr=1&dates={D}"),
    ("espn ncaaf", f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates={D}&groups=80"),
    ("action network nfl", "https://api.actionnetwork.com/web/v1/scoreboard/nfl?period=game&bookIds=15,30,68,69,75,71,79,247,123,76,1968&date=20260928"),
    ("action network mlb", f"https://api.actionnetwork.com/web/v1/scoreboard/mlb?period=game&date={D}"),
    ("action network ncaaf", f"https://api.actionnetwork.com/web/v1/scoreboard/ncaaf?period=game&division=FBS&date={D}"),
    ("mlb statsapi", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-09-26"),
    ("nhl api-web", "https://api-web.nhle.com/v1/score/2026-09-26"),
    ("nba cdn scoreboard", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"),
    ("nba cdn odds", "https://cdn.nba.com/static/json/liveData/odds/odds_todaysGames.json"),
    ("draftkings nash", "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnj/v1/leagues/88808"),
    ("fanduel", "https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=nfl&_ak=FhMFpcPWXMeyZxOx"),
    ("covers", "https://www.covers.com/sports/nfl/matchups"),
]
for name, url in CANDIDATES:
    for hname, h in HEADERS.items():
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=15) as r:
                body = r.read(400).decode("utf-8", "replace")
                print(f"{r.status} {name} [{hname}] type={r.headers.get('Content-Type')}\n    {body[:160]!r}")
            break
        except Exception as e:
            print(f"ERR {name} [{hname}] {str(e)[:100]}")
    print(f"    {url}")
