"""Is the watcher's Bovada live tennis line stale? Fetch it the watcher's way vs cache-busted / browser headers /
other endpoints, a few times, and print each live match's moneyline + timestamps side by side."""
import json, time, urllib.request
B = "https://www.bovada.lv/services/sports/event/{v}/events/A/description/tennis?marketFilterId=def&{q}lang=en"
URLS = {"watcher v2 live": B.format(v="v2", q="liveOnly=true&"), "coupon live": B.format(v="coupon", q="liveOnly=true&"),
        "v2 all": B.format(v="v2", q="")}
H_W = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
H_B = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
       "Accept": "*/*", "Referer": "https://www.bovada.lv/", "Origin": "https://www.bovada.lv", "Cache-Control": "no-cache",
       "Pragma": "no-cache"}


def get(u, h):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=20)
    return json.load(r), {k: r.headers.get(k) for k in ("Age", "Cache-Control", "X-Cache", "Date", "Last-Modified", "ETag")}


def lines(data):
    out = {}
    for g in data if isinstance(data, list) else []:
        for e in g.get("events") or []:
            if not e.get("live"):
                continue
            for dg in e.get("displayGroups") or []:
                for mk in dg.get("markets") or []:
                    d = str(mk.get("description", "")).lower()
                    if "moneyline" in d:
                        oc = mk.get("outcomes") or []
                        out.setdefault(e.get("description"), []).append(
                            (dg.get("description"), mk.get("description"), (mk.get("period") or {}).get("description"),
                             (mk.get("period") or {}).get("main"), (mk.get("period") or {}).get("live"), mk.get("status"),
                             [(o.get("description"), (o.get("price") or {}).get("american"), o.get("status")) for o in oc],
                             e.get("lastModified")))
    return out


for rnd in range(4):
    print(f"==== round {rnd} {time.strftime('%H:%M:%S', time.gmtime())}")
    for name, u in URLS.items():
        for hn, h in (("watcher hdr", H_W), ("browser hdr", H_B)):
            for bust in ("", f"&_={int(time.time()*1000)}"):
                try:
                    d, hd = get(u + bust, h)
                    print(f"-- {name} | {hn} | bust={bool(bust)} | {hd}")
                    for ev, ms in lines(d).items():
                        for x in ms:
                            print("   ", ev, "|", x)
                except Exception as e:
                    print(f"-- {name} | {hn} | bust={bool(bust)} | ERR {e}")
    time.sleep(20)
