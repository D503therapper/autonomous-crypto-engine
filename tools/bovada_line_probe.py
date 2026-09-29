"""Which Bovada address gives a FRESH live tennis line? (its main feed sits in a CDN cache up to 10 min).
Prints each variant's Age header + a few live moneylines, a few rounds apart."""
import json, time, urllib.request
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
     "Accept": "application/json, text/plain, */*", "Referer": "https://www.bovada.lv/sports/tennis",
     "Origin": "https://www.bovada.lv"}


def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20)
    return json.load(r), r.headers.get("Age"), r.headers.get("Cache-Control")


def mls(d, only=None):
    out = []
    evs = [e for g in (d if isinstance(d, list) else []) for e in g.get("events") or []]
    for e in evs:
        if only and e.get("id") != only:
            continue
        for dg in e.get("displayGroups") or []:
            for mk in dg.get("markets") or []:
                if mk.get("description") == "Moneyline" and (mk.get("period") or {}).get("live"):
                    out.append((e.get("description")[:40], [(o.get("price") or {}).get("american") for o in mk.get("outcomes") or []],
                                e.get("lastModified")))
    return out


W = "https://www.bovada.lv/services/sports/event/v2/events/A/description"
S = "https://services.bovada.lv/services/sports/event/v2/events/A/description"
base, _, _ = get(W + "/tennis?marketFilterId=def&liveOnly=true&lang=en")
evs = [e for g in base for e in g.get("events") or [] if e.get("live")][:3]
print("events:", [(e.get("id"), e.get("link")) for e in evs])
V = {
    "www live": W + "/tennis?marketFilterId=def&liveOnly=true&lang=en",
    "www live reordered": W + "/tennis?lang=en&liveOnly=true&marketFilterId=def",
    "www live no filter": W + "/tennis?liveOnly=true&lang=en",
    "www live eventsLimit": W + "/tennis?marketFilterId=def&liveOnly=true&eventsLimit={n}&lang=en",
    "services live": S + "/tennis?marketFilterId=def&liveOnly=true&lang=en",
    "www live preMatchOnly": W + "/tennis?marketFilterId=def&liveOnly=true&preMatchOnly=false&lang=en",
}
for e in evs:
    V[f"www event {e['id']}"] = W + e["link"] + "?lang=en"
    V[f"services event {e['id']}"] = S + e["link"] + "?lang=en"
    V[f"www event {e['id']} def"] = W + e["link"] + "?marketFilterId=def&lang=en"
for rnd in range(4):
    print(f"==== round {rnd} {time.strftime('%H:%M:%S', time.gmtime())}")
    for name, u in V.items():
        try:
            d, age, cc = get(u.replace("{n}", str(1000 + rnd)))
            print(f"-- {name} | Age={age} | {cc} | {mls(d)[:3]}")
        except Exception as ex:
            print(f"-- {name} | ERR {ex}")
    time.sleep(15)
