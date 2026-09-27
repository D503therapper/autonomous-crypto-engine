"""Live NFL right now: where are the real live moneylines in Action Network's scoreboard?"""
import json
import urllib.request

d = json.load(urllib.request.urlopen("https://api.actionnetwork.com/web/v1/scoreboard/nfl?period=game", timeout=25))
games = [g for g in d.get("games") or [] if str(g.get("status")) in ("inprogress", "in_progress", "live") or
         (g.get("boxscore") or {}).get("period")]
print(len(d.get("games") or []), "games,", len(games), "live")
for g in games[:3]:
    teams = {t["id"]: t.get("full_name") for t in g.get("teams") or []}
    b = g.get("boxscore") or {}
    print("\n", teams.get(g.get("away_team_id")), "@", teams.get(g.get("home_team_id")), "status", g.get("status"),
          "real_status", g.get("real_status"), "period", b.get("period"), "clock", b.get("clock"),
          "score", b.get("total_away_points"), "-", b.get("total_home_points"))
    print("  latest_odds:", json.dumps(b.get("latest_odds"))[:500])
    for o in (g.get("odds") or [])[:12]:
        print("  odds:", {k: o.get(k) for k in ("book_id", "type", "ml_home", "ml_away", "spread_home", "inserted", "is_live")})
    print("  top keys:", sorted(g.keys()))
for extra in ("&bookIds=15,30,68,69,71,75,79,972,974", ""):
    try:
        d2 = json.load(urllib.request.urlopen(f"https://api.actionnetwork.com/web/v2/scoreboard/nfl?periods=event{extra}", timeout=25))
        g2 = [g for g in d2.get("games") or [] if (g.get("boxscore") or {}).get("period")][:1]
        for g in g2:
            print("\nv2", extra, json.dumps(g.get("markets") or g.get("odds"))[:1500])
    except Exception as e:                                   # noqa: BLE001
        print("v2 ERR", extra, e)
