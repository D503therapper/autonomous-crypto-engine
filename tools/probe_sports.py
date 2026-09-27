"""Bovada live lines right now (NFL + others): structure, live flag, moneylines."""
import json
import urllib.request

for path in ("football/nfl", "football/college-football", "basketball/nba", "hockey/nhl", "baseball/mlb"):
    url = f"https://www.bovada.lv/services/sports/event/coupon/events/A/description/{path}?marketFilterId=def&liveOnly=true&lang=en"
    try:
        data = json.load(urllib.request.urlopen(url, timeout=25))
    except Exception as e:                                   # noqa: BLE001
        print(path, "ERR", e)
        continue
    evs = [e for g in data for e in g.get("events") or []]
    print(f"\n{path}: {len(evs)} live events")
    for e in evs[:3]:
        print("  ", e.get("description"), "live", e.get("live"), "keys", sorted(e.keys())[:25])
        print("   competitors", [(c.get("name"), c.get("home")) for c in e.get("competitors") or []])
        for dg in (e.get("displayGroups") or [])[:1]:
            for m in dg.get("markets") or []:
                if "moneyline" in str(m.get("description", "")).lower():
                    print("   ML", m.get("period"), [(o.get("description"), (o.get("price") or {}).get("american")) for o in m.get("outcomes") or []])
