"""Dump the shape of ESPN's game summary box score (player stats) for one finished game per league."""
import json
import urllib.request

GAMES = {"football/nfl": "401872948", "baseball/mlb": "401817100", "hockey/nhl": "401879414",
         "basketball/nba": "401859967", "football/college-football": "401858241"}
for path, eid in GAMES.items():
    try:
        with urllib.request.urlopen(f"https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={eid}", timeout=20) as r:
            d = json.load(r)
    except Exception as e:
        print(path, "ERR", e)
        continue
    print("=====", path, "top keys", list(d)[:20])
    for team in (d.get("boxscore") or {}).get("players") or []:
        t = team.get("team") or {}
        print(" team", t.get("id"), t.get("displayName"))
        for grp in team.get("statistics") or []:
            ath = grp.get("athletes") or []
            print("   group", grp.get("name"), "labels", grp.get("labels"), "keys", grp.get("keys"), "n", len(ath))
            for a in ath[:2]:
                print("      ", (a.get("athlete") or {}).get("displayName"), (a.get("athlete") or {}).get("position", {}).get("abbreviation"),
                      a.get("starter"), a.get("stats"))
        break
