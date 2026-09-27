"""Probe weather/elevation sources and ESPN venue fields from the runner."""
import json
import urllib.request


def get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


tests = {
    "geocode Denver": "https://geocoding-api.open-meteo.com/v1/search?name=Denver&count=1&country=US",
    "archive weather": "https://archive-api.open-meteo.com/v1/archive?latitude=39.74&longitude=-104.99&start_date=2025-11-02&end_date=2025-11-02&hourly=temperature_2m,wind_speed_10m,precipitation&temperature_unit=fahrenheit&wind_speed_unit=mph",
    "forecast weather": "https://api.open-meteo.com/v1/forecast?latitude=41.86&longitude=-87.62&hourly=temperature_2m,wind_speed_10m,precipitation&temperature_unit=fahrenheit&wind_speed_unit=mph&forecast_days=3",
}
for name, url in tests.items():
    try:
        d = get(url)
        print("OK", name, json.dumps(d)[:400])
    except Exception as e:
        print("ERR", name, e)
for path, eid in (("football/nfl", "401872948"), ("baseball/mlb", "401817100"), ("hockey/nhl", "401879414")):
    try:
        d = get(f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates=20260921")
        comp = d["events"][0]["competitions"][0]
        print("VENUE", path, json.dumps(comp.get("venue"))[:300], "| weather:", json.dumps(d["events"][0].get("weather"))[:200])
        s = get(f"https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={eid}")
        gi = s.get("gameInfo") or {}
        print("GAMEINFO", path, json.dumps({k: gi.get(k) for k in ("venue", "weather", "attendance")})[:400])
    except Exception as e:
        print("ERR venue", path, e)
try:
    inj = get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries")
    reasons = set()
    for t in inj.get("injuries", [])[:30]:
        for i in t.get("injuries", []):
            reasons.add((i.get("status"), (i.get("details") or {}).get("type"), (i.get("type") or {}).get("description")))
    print("INJURY TYPES", sorted(map(str, reasons))[:40])
except Exception as e:
    print("ERR injuries", e)
