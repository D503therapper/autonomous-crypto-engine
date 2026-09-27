"""Probe tennis sources from the runner: ESPN ATP scoreboard, Action Network tennis odds, match history, odds history."""
import json
import urllib.request
from datetime import datetime, timedelta, timezone


def get(url, raw=False):
    with urllib.request.urlopen(url, timeout=25) as r:
        body = r.read()
        return body if raw else json.loads(body)


def show(name, fn):
    try:
        print("OK ", name, fn())
    except Exception as e:                                  # noqa: BLE001
        print("ERR", name, str(e)[:200])


today = datetime.now(timezone.utc)
day = today.strftime("%Y%m%d")


def espn(path):
    def f():
        d = get(f"https://site.api.espn.com/apis/site/v2/sports/tennis/{path}")
        evs = d.get("events") or []
        out = [f"{len(evs)} events"]
        for ev in evs[:2]:
            out.append(ev.get("name"))
            for gr in (ev.get("groupings") or [])[:3]:
                comps = gr.get("competitions") or []
                out.append(f"  grouping {(gr.get('grouping') or {}).get('displayName')}: {len(comps)} matches")
                for c in comps[:2]:
                    out.append("    " + json.dumps({k: c.get(k) for k in ("date", "status", "odds", "venue", "round", "format")})[:400])
                    out.append("    competitors " + json.dumps([{"name": (x.get("athlete") or {}).get("displayName"), "winner": x.get("winner"),
                                                                "score": [l.get("value") for l in x.get("linescores") or []]}
                                                               for x in c.get("competitors") or []])[:300])
        return "\n".join(out)
    return f


show("espn atp scoreboard", espn("atp/scoreboard"))
show("espn atp scoreboard dates", espn(f"atp/scoreboard?dates={(today - timedelta(days=1)).strftime('%Y%m%d')}"))

for lg in ("atp", "tennis"):
    def an(lg=lg):
        d = get(f"https://api.actionnetwork.com/web/v1/scoreboard/{lg}?period=game&date={day}")
        gs = d.get("games") or d.get("competitions") or []
        keys = list(d.keys())
        s = json.dumps(gs[0])[:700] if gs else ""
        return f"keys {keys} {len(gs)} games {s}"
    show(f"action network {lg}", an)

for yr in (2016, 2024, 2025, 2026):
    def sack(yr=yr):
        b = get(f"https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{yr}.csv", raw=True)
        lines = b.decode("utf-8", "replace").splitlines()
        return f"{len(lines)} rows; header {lines[0][:200]}; last {lines[-1][:160]}"
    show(f"sackmann {yr}", sack)

for url in ("http://www.tennis-data.co.uk/2025/2025.xlsx", "http://www.tennis-data.co.uk/2024/2024.xlsx",
            "http://www.tennis-data.co.uk/2016/2016.xlsx", "http://www.tennis-data.co.uk/alldata.php"):
    show(url, lambda url=url: f"{len(get(url, raw=True))} bytes")
