"""Find how Action Network's football scoreboard pages through past weeks (the date parameter is ignored)."""
import json
import urllib.request

B = "https://api.actionnetwork.com/web/v1/scoreboard/"
for q in ["nfl?period=game&season=2025&week=10", "nfl?period=game&season=2025&week=10&seasonType=reg",
          "nfl?period=game&week=10&season=2025&date=20251109", "nfl?period=game&season=2025&week=1&seasonType=post",
          "nfl?period=game&season=2025&week=20", "nfl?period=game&date=20251109",
          "ncaaf?period=game&division=FBS&season=2025&week=10", "ncaaf?period=game&division=FBS&season=2025&week=16",
          "ncaaf?period=game&division=FBS&season=2025&week=1&seasonType=post"]:
    try:
        with urllib.request.urlopen(B + q, timeout=20) as r:
            d = json.load(r)
        gs = d.get("games") or []
        starts = sorted(g.get("start_time", "")[:10] for g in gs)
        print(f"{q}: {len(gs)} games {starts[:1]}..{starts[-1:]} types={sorted({g.get('type') for g in gs})} weeks={sorted({g.get('week') for g in gs})} odds={sum(bool(g.get('odds')) for g in gs)}")
    except Exception as e:
        print(q, "ERR", e)
