"""Probe tennis depth from the runner: Action Network ATP odds + history depth + surface; ESPN ATP history depth."""
import json
import urllib.request


def get(url):
    with urllib.request.urlopen(url, timeout=25) as r:
        return json.load(r)


def show(name, fn):
    try:
        print("OK ", name, fn())
    except Exception as e:                                  # noqa: BLE001
        print("ERR", name, str(e)[:200])


def an(day):
    d = get(f"https://api.actionnetwork.com/web/v1/scoreboard/atp?period=game&date={day}")
    gs = d.get("competitions") or []
    if not gs:
        return "0 games"
    g = gs[0]
    keys = sorted(g.keys())
    odds = g.get("odds") or []
    o15 = [o for o in odds if o.get("book_id") in (15, 30)]
    return (f"{len(gs)} games; keys {keys}; odds books {len(odds)} "
            f"sample {json.dumps(o15[:2] or odds[:1])[:500]}; "
            f"tournament {json.dumps({k: g.get(k) for k in keys if 'tour' in k or 'surface' in k or 'round' in k or 'event' in k})[:400]}")


for day in ("20260926", "20250615", "20230720", "20210520", "20190320", "20170620"):
    show(f"AN atp {day}", lambda day=day: an(day))


def espn(day):
    d = get(f"https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates={day}")
    evs = d.get("events") or []
    n = sum(len(gr.get("competitions") or []) for ev in evs for gr in ev.get("groupings") or []
            if "Singles" in ((gr.get("grouping") or {}).get("displayName") or ""))
    ev = evs[0] if evs else {}
    return f"{len(evs)} events, {n} singles matches; event keys {sorted(ev.keys())[:30]}; name {ev.get('name')}"


for day in ("20250615", "20210520", "20170620", "20160620"):
    show(f"ESPN atp {day}", lambda day=day: espn(day))
show("ESPN atp calendar", lambda: json.dumps(get("https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard").get("leagues", [{}])[0].get("calendar", [])[:3])[:600])
