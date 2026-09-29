"""Which public sites give us who's-betting-who (and lines) as a backup to Action Network? Fetch each candidate the
way a browser would; print status, size, and whether bet/money percentages are in it."""
import re, urllib.request, json, time
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
     "Accept": "text/html,application/json;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}
C = {
    "yahoo nfl odds page": "https://sports.yahoo.com/nfl/odds/",
    "yahoo mlb odds page": "https://sports.yahoo.com/mlb/odds/",
    "yahoo nhl odds page": "https://sports.yahoo.com/nhl/odds/",
    "covers nfl consensus": "https://contests.covers.com/consensus/topconsensus/nfl/overall",
    "covers mlb consensus": "https://contests.covers.com/consensus/topconsensus/mlb/overall",
    "vegasinsider nfl odds": "https://www.vegasinsider.com/nfl/odds/las-vegas/",
    "vegasinsider mlb odds": "https://www.vegasinsider.com/mlb/odds/las-vegas/",
    "scoresandodds nfl": "https://www.scoresandodds.com/nfl",
    "scoresandodds mlb": "https://www.scoresandodds.com/mlb",
    "espn nfl odds api (dk)": "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events?limit=5",
}
for name, u in C.items():
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20)
        body = r.read().decode("utf-8", "ignore")
        pcts = re.findall(r"\b\d{1,2}%", body)
        keys = [k for k in ("betPercent", "moneyPercent", "bet_percent", "money_percent", "Bets", "Handle", "consensus",
                            "spreadBets", "public", "Picks") if k in body]
        print(f"OK  {name}: HTTP {r.status}, {len(body)//1024} KB, % signs: {len(pcts)} e.g. {pcts[:6]}, keys: {keys[:6]}")
        for m in re.finditer(r"(?i)(bets|money|handle|tickets)[^<]{0,60}?\d{1,2}%", body):
            print("     sample:", re.sub(r"\s+", " ", m.group(0))[:120]); break
    except Exception as e:
        print(f"ERR {name}: {str(e)[:80]}")
    time.sleep(1)
