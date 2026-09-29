"""How fast do live tennis scores move at each source? Polls every 3s for 4 minutes and prints each change with its
time: ESPN's scoreboard (what we use now) and ESPN's per-match core feed. Run by hand while matches are live."""
import json, time, urllib.request
from datetime import datetime, timezone
UA = {"User-Agent": "Mozilla/5.0"}
def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=10))
last, t_end = {}, time.time() + 240
live = []
for tour in ("atp", "wta"):
    d = get(f"https://site.web.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard")
    for ev in d.get("events") or []:
        for g in ev.get("groupings") or []:
            for c in g.get("competitions") or []:
                if ((c.get("status") or {}).get("type") or {}).get("state") == "in":
                    live.append((tour, ev["id"], c["id"]))
print("live matches:", live[:6])
while time.time() < t_end and live:
    for tour, eid, cid in live[:4]:
        for name, u in (("scoreboard", f"https://site.web.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard"),
                        ("core", f"https://sports.core.api.espn.com/v2/sports/tennis/leagues/{tour}/events/{eid}/competitions/{cid}")):
            try:
                d = get(u + ("?t=%d" % time.time()))
                if name == "scoreboard":
                    c = next(c for ev in d["events"] for g in ev.get("groupings") or [] for c in g.get("competitions") or [] if c["id"] == cid)
                    key = json.dumps([[x.get("value") for x in p.get("linescores") or []] for p in c["competitors"]])
                else:
                    key = json.dumps([p.get("linescores", {}).get("$ref", "") for p in d.get("competitors", [])])[:200] + str(d.get("status", {}).get("$ref"))
                if last.get((name, cid)) != key:
                    last[(name, cid)] = key
                    print(f"{datetime.now(timezone.utc):%H:%M:%S} {name:10} {cid} {key[:120]}", flush=True)
            except Exception as e:
                print("err", name, str(e)[:80])
    time.sleep(3)
