"""Do finished games keep their first-half / first-5-innings lines on Action Network? (for backtesting 1H / F5 bets)"""
import json
import urllib.request


def get(url):
    with urllib.request.urlopen(url, timeout=25) as r:
        return json.load(r)


for lg, q in (("nfl", "&season=2025&week=6&seasonType=reg"), ("nba", "&date=20260115"), ("ncaab", "&division=D1&date=20260115"),
              ("mlb", "&date=20250715"), ("mlb", "&date=20230715"), ("nfl", "&season=2021&week=6&seasonType=reg")):
    try:
        d = get(f"https://api.actionnetwork.com/web/v1/scoreboard/{lg}?period=game{q}")
        gs = d.get("games") or []
        g = next((x for x in gs if (x.get("boxscore") or {}).get("latest_odds")), gs[0] if gs else {})
        lo = (g.get("boxscore") or {}).get("latest_odds") or {}
        print(lg, q, len(gs), "games; latest_odds keys:", sorted(lo.keys()))
        for k in lo:
            if k != "game":
                print("    ", k, json.dumps(lo[k])[:220])
                break
    except Exception as e:                                   # noqa: BLE001
        print(lg, q, "ERR", e)
