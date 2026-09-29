"""How fast do live tennis scores move at each source? Polls every 3s for 4 minutes and prints each change with its
time: ESPN's scoreboard (what we use now) and Bovada's live tennis feed + its per-event score API. Run by hand."""
import json, time, urllib.request
from datetime import datetime, timezone
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
      "Accept": "*/*", "Referer": "https://www.bovada.lv/", "Origin": "https://www.bovada.lv", "Accept-Language": "en-US,en;q=0.9"}
def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=15))
BOV = "https://www.bovada.lv/services/sports/event/coupon/events/A/description/tennis?marketFilterId=def&liveOnly=true&lang=en"
evs = []
try:
    d = get(BOV)
    for g in d:
        for e in g.get("events") or []:
            if e.get("live"):
                evs.append((e["id"], e.get("description")))
except Exception as e:
    print("bovada feed err", str(e)[:120])
print("bovada live tennis:", evs[:6])
if evs:
    eid = evs[0][0]
    for u in (f"https://services.bovada.lv/services/sports/results/api/v1/scores/{eid}",
              f"https://www.bovada.lv/services/sports/results/api/v1/scores/{eid}"):
        try:
            print("SCORE API", u, json.dumps(get(u))[:1500])
            break
        except Exception as e:
            print("score api err", u, str(e)[:100])
# the live feed itself: does each event carry a score (and how fast does it move)?
try:
    d = get(BOV)
    e0 = next(e for g in d for e in g.get("events") or [] if e.get("live"))
    print("EVENT KEYS", sorted(e0), json.dumps({k: e0[k] for k in e0 if "score" in k.lower() or k in ("competitors",)})[:800])
except Exception as e:
    print("feed keys err", str(e)[:100])
last, t_end = {}, time.time() + 240
while time.time() < t_end and evs:
    for eid, name in evs[:4]:
        try:
            s = get(f"https://services.bovada.lv/services/sports/results/api/v1/scores/{eid}?t={int(time.time())}")
            key = json.dumps(s.get("latestScore") or s.get("scores") or s)[:160]
            if last.get(eid) != key:
                last[eid] = key
                print(f"{datetime.now(timezone.utc):%H:%M:%S} bovada {name[:30]:30} {key}", flush=True)
        except Exception as e:
            print("err", eid, str(e)[:80]); break
    time.sleep(3)
