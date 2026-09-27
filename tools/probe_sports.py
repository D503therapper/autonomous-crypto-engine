"""Probe: does ESPN send ATP rankings / seeds with each tennis match? (competitor fields)"""
import json
import urllib.request

d = json.load(urllib.request.urlopen("https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20250615", timeout=25))
for ev in (d.get("events") or [])[:1]:
    for gr in ev.get("groupings") or []:
        for c in (gr.get("competitions") or [])[:1]:
            for x in c.get("competitors") or []:
                print("competitor keys:", sorted(x.keys()))
                print("   ", json.dumps({k: v for k, v in x.items() if k not in ("linescores", "statistics")})[:600])
        break
try:
    r = json.load(urllib.request.urlopen("https://site.api.espn.com/apis/site/v2/sports/tennis/atp/rankings", timeout=25))
    rk = (r.get("rankings") or [{}])[0].get("ranks") or []
    print("rankings endpoint:", len(rk), json.dumps(rk[:2])[:400])
except Exception as e:                                       # noqa: BLE001
    print("rankings ERR", e)
