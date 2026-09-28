"""Probe: Action Network's public splits (bet_info: % of tickets / % of money) - does history go back far enough
for a 'fade the public' study, and what are tonight's Bears-Eagles splits?"""
import json
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Accept": "application/json"}
AN2 = "https://api.actionnetwork.com/web/v2/scoreboard/{lg}?bookIds=15,30&date={day}{extra}"
EXTRA = {"ncaaf": "&division=FBS", "ncaab": "&division=D1"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return json.load(r)


def splits(g):
    ev = (((g.get("markets") or {}).get("15") or {}).get("event") or {})
    out = {}
    for mk in ("moneyline", "spread", "total"):
        for o in ev.get(mk) or []:
            bi = o.get("bet_info") or {}
            out[f"{mk}:{o.get('side')}"] = (o.get("odds"), o.get("value"), (bi.get("tickets") or {}).get("percent"),
                                            (bi.get("money") or {}).get("percent"))
    return out


def names(g):
    t = {x.get("id"): x.get("display_name") or x.get("full_name") for x in g.get("teams") or []}
    return f"{t.get(g.get('away_team_id'))} @ {t.get(g.get('home_team_id'))}"


d = get(AN2.format(lg="nfl", day="20260928", extra=""))
for g in d.get("games") or []:
    if "Bears" in names(g) or "Eagles" in names(g):
        print("MNF:", names(g), g.get("status"), json.dumps(splits(g)))
        print("   num_bets:", g.get("num_bets"), "| full game keys:", list(g.keys()))
        print("   sample:", json.dumps(g)[:1500])

for lg, days in {"nfl": ["20260921", "20251019", "20241020", "20231015", "20221016", "20211017", "20201018", "20191020"],
                 "nba": ["20260315", "20250115", "20240115", "20230115", "20220115", "20200115"],
                 "mlb": ["20260915", "20250615", "20240615", "20230615", "20220615", "20190615"],
                 "nhl": ["20260115", "20250115", "20240115", "20220115"],
                 "ncaaf": ["20260919", "20251018", "20231014", "20211016"],
                 "ncaab": ["20260115", "20250115", "20230115", "20210115"]}.items():
    for day in days:
        try:
            gs = get(AN2.format(lg=lg, day=day, extra=EXTRA.get(lg, ""))).get("games") or []
            have = [g for g in gs if any((v[2] or 0) > 0 for v in splits(g).values())]
            ex = splits(have[0]) if have else {}
            print(f"{lg} {day}: {len(gs)} games, {len(have)} with public splits"
                  + (f" | e.g. {names(have[0])} {ex.get('moneyline:home')} {ex.get('spread:home')}" if have else ""))
        except Exception as e:                               # noqa: BLE001
            print(f"{lg} {day}: ERR {e}")
