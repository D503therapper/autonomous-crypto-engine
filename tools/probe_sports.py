"""Which live-line sources answer from this runner? Bovada (plain + browser headers), ESPN odds for live games."""
import json
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
      "Accept": "application/json", "Accept-Language": "en-US,en;q=0.9"}


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


B = "https://www.bovada.lv/services/sports/event/coupon/events/A/description/football/nfl?marketFilterId=def&liveOnly=true&lang=en"
for name, h in (("plain", None), ("browser", UA)):
    try:
        d = get(B, h)
        print(f"bovada {name}: {len(d)} groups, {sum(len(g.get('events') or []) for g in d)} events")
    except Exception as e:                                   # noqa: BLE001
        print(f"bovada {name}: ERR {e}")
try:
    d = get("https://www.bovada.lv/services/sports/event/v2/events/A/description/football/nfl?marketFilterId=def&liveOnly=true&lang=en", UA)
    print(f"bovada v2: {len(d)} groups, {sum(len(g.get('events') or []) for g in d)} events")
except Exception as e:                                       # noqa: BLE001
    print("bovada v2 ERR", e)
sb = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard")
for ev in sb.get("events") or []:
    c = ev["competitions"][0]
    if (c.get("status") or {}).get("type", {}).get("state") != "in":
        continue
    print("\nESPN", ev.get("shortName"), "scoreboard odds:", json.dumps(c.get("odds"))[:600])
    try:
        o = get(f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{ev['id']}/competitions/{c['id']}/odds")
        for it in (o.get("items") or [])[:3]:
            print("  core:", (it.get("provider") or {}).get("name"), "home", json.dumps((it.get("homeTeamOdds") or {}).get("current") or
                  (it.get("homeTeamOdds") or {}).get("moneyLine"))[:300], "| moneyline", (it.get("homeTeamOdds") or {}).get("moneyLine"),
                  (it.get("awayTeamOdds") or {}).get("moneyLine"))
    except Exception as e:                                   # noqa: BLE001
        print("  core ERR", e)
    try:
        s = get(f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={ev['id']}")
        print("  pickcenter:", json.dumps([{k: p.get(k) for k in ("provider", "homeTeamOdds", "awayTeamOdds", "details")} for p in s.get("pickcenter") or []])[:700])
    except Exception as e:                                   # noqa: BLE001
        print("  summary ERR", e)
    break
