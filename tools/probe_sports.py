"""Probe: LIVE tennis payloads for the live plus money feature (run it while ATP / WTA matches are being played).
Saves the raw feeds to results/ so the parsers (sports_tennis.parse_espn / parse_bovada(live=True)) can be checked
against the real thing, and prints what matters: live matches, which fields carry the points / the server, and
Bovada's live tennis markets (status, prices)."""
import gzip
import json
import time
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard"
BOVADA = ["https://www.bovada.lv/services/sports/event/v2/events/A/description/tennis?marketFilterId=def&liveOnly=true&lang=en",
          "https://www.bovada.lv/services/sports/event/coupon/events/A/description/tennis?marketFilterId=def&liveOnly=true&lang=en",
          "https://www.bovada.lv/services/sports/event/v2/events/A/description/tennis?marketFilterId=def&lang=en"]


def get(url, browser):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"} if browser else {})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    print(f"== {url}\n{r.status} {len(body)}B {time.time() - t0:.1f}s")
    return json.loads(body)


def save(name, data):
    with gzip.open(f"results/{name}.json.gz", "wt") as f:
        json.dump(data, f)
    print(f"saved results/{name}.json.gz")


for tour in ("atp", "wta"):
    try:
        d = get(ESPN.format(tour=tour), False)
    except Exception as e:                                   # noqa: BLE001
        print(f"ERR espn {tour}: {e}")
        continue
    save(f"tennis_live_espn_{tour}", d)
    n = 0
    for ev in d.get("events") or []:
        for gr in ev.get("groupings") or []:
            for c in gr.get("competitions") or []:
                st = ((c.get("status") or {}).get("type") or {})
                if st.get("state") != "in":
                    continue
                n += 1
                if n <= 3:                                   # the first few live matches, every field they carry
                    print(f"LIVE {tour} {ev.get('name')} | {(gr.get('grouping') or {}).get('displayName')} | status {st}")
                    print("  competition keys:", sorted(c))
                    for x in c.get("competitors") or []:
                        print("  competitor keys:", sorted(x), "| linescores:", x.get("linescores"))
                        print("   ", {k: x[k] for k in x if k not in ("athlete", "linescores", "statistics", "records")})
                    print("  situation:", c.get("situation"), "| status:", c.get("status"))
    print(f"{tour}: {n} matches in progress")

for url in BOVADA:
    try:
        d = get(url, True)
    except Exception as e:                                   # noqa: BLE001
        print(f"ERR bovada: {e}")
        continue
    live = [(g, e) for g in d if isinstance(g, dict) for e in g.get("events") or [] if e.get("live")]
    print(f"{len(d)} groups, {len(live)} live events")
    if not live:
        continue
    save("tennis_live_bovada", d)
    for g, e in live[:3]:
        print("PATH", [p.get("description") for p in g.get("path") or []], "| event keys:", sorted(e))
        print("  competitors:", e.get("competitors"))
        for dg in e.get("displayGroups") or []:
            for mk in dg.get("markets") or []:
                print("  market:", mk.get("description"), "| status", mk.get("status"), "| period", mk.get("period"),
                      "|", [(o.get("description"), o.get("status"), (o.get("price") or {}).get("american")) for o in mk.get("outcomes") or []])
    eid = live[0][1].get("id")
    for su in (f"https://services.bovada.lv/services/sports/results/api/v1/scores/{eid}",      # Bovada's own live score
               f"https://www.bovada.lv/services/sports/results/api/v1/scores/{eid}"):          # (if it has one for tennis)
        try:
            s = get(su, True)
            save("tennis_live_bovada_score", s)
            print(json.dumps(s)[:1500])
            break
        except Exception as e:                               # noqa: BLE001
            print(f"ERR {su}: {e}")
    break
