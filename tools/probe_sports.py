"""Dump the shape of Action Network's public scoreboard (odds + public betting / money %) from the runner."""
import json
import urllib.request


def get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


for lg, extra in (("nfl", ""), ("mlb", ""), ("ncaaf", "&division=FBS"), ("nhl", ""), ("nba", "")):
    for date in ("20260926", "20260928"):
        try:
            d = get(f"https://api.actionnetwork.com/web/v1/scoreboard/{lg}?period=game&date={date}{extra}")
        except Exception as e:
            print(lg, date, "ERR", e)
            continue
        games = d.get("games") or []
        print(f"== {lg} {date}: {len(games)} games; top keys {list(d)[:10]}")
        if games:
            g = games[0]
            print("game keys:", list(g))
            print("teams:", [(t.get("id"), t.get("full_name"), t.get("abbr")) for t in g.get("teams", [])],
                  "home_team_id", g.get("home_team_id"), "status", g.get("status"), "start", g.get("start_time"))
            for o in (g.get("odds") or [])[:3]:
                print("odds:", json.dumps(o)[:900])
            if date == "20260928" and lg == "nfl":
                print("FULL GAME:", json.dumps(g)[:4000])
