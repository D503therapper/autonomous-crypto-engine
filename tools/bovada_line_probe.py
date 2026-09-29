"""Which Bovada address variations dodge its 10-minute cache? For each: HTTP status, the CDN's Age, and how old the
newest live tennis price in it is (now - the event's lastModified). Two rounds."""
import json, time, urllib.request
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
     "Accept": "application/json, text/plain, */*", "Referer": "https://www.bovada.lv/sports/tennis", "Origin": "https://www.bovada.lv"}
W = "https://www.bovada.lv/services/sports/event/v2/events/A/description/tennis?"
R = int(time.time())
V = [f"liveOnly=true&eventsLimit={n}&lang=en" for n in (5, 50, 100, 250, 500, R % 500 + 1)] + \
    [f"liveOnly=true&lang=en&eventsLimit={R % 97 + 3}", "liveOnly=1&lang=en", "liveOnly=TRUE&lang=en", "liveOnly=true&lang=EN",
     "liveOnly=true&lang=en-us", "liveOnly=true&lang=en&marketFilterId=all", "liveOnly=true&lang=en&marketFilterId=",
     f"liveOnly=true&lang=en&startTimeTo={(R + 86400) * 1000}", f"liveOnly=true&lang=en&startTimeFrom={(R - 86400 * 2) * 1000}",
     f"liveOnly=true&lang=en&preMatchOnly=false&eventsLimit={R % 200 + 10}", "liveOnly=true&lang=en&_=1",
     "liveOnly=true&lang=en&t=" + str(R), f"liveOnly=true&lang=en&periodFilter=live", "liveOnly=true&lang=en&marketFilterId=rank"]
EXTRA = ["https://www.bovada.lv/services/sports/event/v2/events/A/description/tennis/wta?liveOnly=true&lang=en",
         "https://www.bovada.lv/services/sports/event/v2/events/A/description/tennis/atp?liveOnly=true&lang=en",
         "https://www.bovada.lv/services/sports/event/v2/nav/A/description/tennis?lang=en",
         "https://www.bovada.lv/services/sports/event/v2/events/L/description/tennis?liveOnly=true&lang=en",
         "https://www.bovada.lv/services/sports/event/v2/events/A/description/tennis?liveOnly=true&lang=en&coupon=true"]


def newest(d):
    mods = [e.get("lastModified") or 0 for g in (d if isinstance(d, list) else []) for e in g.get("events") or [] if e.get("live")]
    return (round(time.time() - max(mods) / 1000), len(mods)) if mods else (None, 0)


for rnd in range(3):
    print(f"==== round {rnd} {time.strftime('%H:%M:%S', time.gmtime())}")
    for u in [W + q for q in V] + EXTRA:
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=15)
            d = json.load(r)
            print(f"{r.status} Age={r.headers.get('Age')} newest_s,events={newest(d)} | {u[60:]}")
        except Exception as ex:
            print(f"ERR {str(ex)[:40]} | {u[60:]}")
    time.sleep(20)
