"""Probe tennis ODDS sources from the runner (Action Network with book ids, ESPN core odds, a few public feeds)."""
import json
import urllib.request
from datetime import datetime, timedelta, timezone


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def show(name, fn):
    try:
        print("OK ", name, str(fn())[:900])
    except Exception as e:                                  # noqa: BLE001
        print("ERR", name, str(e)[:200])


now = datetime.now(timezone.utc)
days = [(now + timedelta(days=i)).strftime("%Y%m%d") for i in (0, 1)] + ["20250615"]


def an(day, extra):
    d = get(f"https://api.actionnetwork.com/web/v1/scoreboard/atp?period=game&date={day}{extra}")
    gs = d.get("competitions") or []
    with_odds = [g for g in gs if g.get("odds")]
    g = (with_odds or gs or [{}])[0]
    return (f"{len(gs)} matches, {len(with_odds)} with odds; status {g.get('status')}; "
            f"odds {json.dumps((g.get('odds') or [])[:2])[:500]}; meta {json.dumps(g.get('meta'))[:200]}")


for day in days:
    for extra in ("", "&bookIds=15,30,68,69,71,75,79"):
        show(f"AN atp {day} {extra}", lambda day=day, extra=extra: an(day, extra))
show("AN tennis today bookIds", lambda: an(days[0], "&bookIds=15,30").replace("atp", "atp"))


def espn_core():
    d = get("https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard")
    out = []
    for ev in d.get("events") or []:
        for gr in ev.get("groupings") or []:
            for c in gr.get("competitions") or []:
                if (c.get("status") or {}).get("type", {}).get("state") == "pre":
                    url = f"https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/{ev['id']}/competitions/{c['id']}/odds"
                    try:
                        o = get(url)
                        out.append(f"{c['id']}: {json.dumps(o)[:400]}")
                    except Exception as e:                  # noqa: BLE001
                        out.append(f"{c['id']}: ERR {str(e)[:80]}")
                    if len(out) >= 2:
                        return out
    return out or "no upcoming matches"


show("ESPN core odds", espn_core)
show("DraftKings tennis", lambda: list(get("https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnj/v1/leagues/84003",
                                            {"User-Agent": "Mozilla/5.0"}).keys()))
show("Bovada tennis", lambda: len(get("https://www.bovada.lv/services/sports/event/coupon/events/A/description/tennis?marketFilterId=def&lang=en")))
