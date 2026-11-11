"""PROBE (branch probe/an-v2 only): what Action Network's v1 / v2 scoreboards answer now (v1 404s since 11/11).
Plain requests with the engine's own name - no browser disguise."""
import json, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
H = {"User-Agent": "D503-sports-engine/1.0 (personal picks dashboard)", "Accept": "application/json"}
now = datetime.now(timezone.utc) - timedelta(hours=8)
TD, YD = now.strftime("%Y%m%d"), (now - timedelta(days=1)).strftime("%Y%m%d")
B1 = "https://api.actionnetwork.com/web/v1/scoreboard/"
B2 = "https://api.actionnetwork.com/web/v2/scoreboard/"
U = [
    ("v1 nba game today", B1 + f"nba?period=game&date={TD}"),
    ("v1 nba no params", B1 + "nba"),
    ("v1 nba bookIds", B1 + f"nba?bookIds=15,30&date={TD}"),
    ("v1 nfl week", B1 + "nfl?period=game&season=2026&week=10&seasonType=reg"),
    ("v1 scores", "https://api.actionnetwork.com/web/v1/scores/nba"),
    ("v2 nba 15 today", B2 + f"nba?bookIds=15&date={TD}"),
    ("v2 nba 15,30 yday", B2 + f"nba?bookIds=15,30&date={YD}"),
    ("v2 nba no bookIds", B2 + f"nba?date={TD}"),
    ("v2 nba 15,30 period=game", B2 + f"nba?bookIds=15,30&period=game&date={TD}"),
    ("v2 nba 15,30 periods", B2 + f"nba?bookIds=15,30&periods=event,firsthalf&date={TD}"),
    ("v2 nba 15,30 period=firsthalf", B2 + f"nba?bookIds=15,30&period=firsthalf&date={TD}"),
    ("v2 ncaab 15,30 D1", B2 + f"ncaab?bookIds=15,30&division=D1&date={TD}"),
    ("v2 nhl 15,30 yday", B2 + f"nhl?bookIds=15,30&date={YD}"),
    ("v2 nfl week", B2 + "nfl?bookIds=15,30&season=2026&week=10&seasonType=reg"),
    ("v2 nfl now", B2 + "nfl?bookIds=15,30"),
    ("v2 ncaaf week FBS", B2 + "ncaaf?bookIds=15,30&season=2026&week=11&seasonType=reg&division=FBS"),
    ("v2 nfl old week", B2 + "nfl?bookIds=15,30&season=2024&week=3&seasonType=reg"),
    ("v2 nba old day", B2 + "nba?bookIds=15,30&date=20250115"),
]


def shape(x, d=0):
    if isinstance(x, dict):
        return {k: shape(v, d + 1) for k, v in list(x.items())[:40]} if d < 3 else "{...}"
    if isinstance(x, list):
        return [shape(x[0], d + 1), f"len={len(x)}"] if x else []
    return type(x).__name__


full = 0
for name, u in U:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=25)
        body = r.read()
        d = json.loads(body)
        gs = d.get("games") or []
        print(f"OK  {name}: HTTP {r.status} {len(body)//1024} KB, top keys {list(d)[:10]}, games {len(gs)}")
        if gs:
            g = gs[0]
            print("    game keys:", list(g))
            print("    markets books:", list((g.get("markets") or {}).keys()), "odds" in g and f"odds len {len(g['odds'])}")
            for bk, m in (g.get("markets") or {}).items():
                print(f"    markets[{bk}] keys:", list(m) if isinstance(m, dict) else type(m).__name__)
                for per, mm in (m.items() if isinstance(m, dict) else []):
                    if isinstance(mm, dict):
                        print(f"      {per}: {list(mm)}", {k: len(v) for k, v in mm.items() if isinstance(v, list)})
            st = {(x.get("status"), x.get("real_status")) for x in gs}
            print("    statuses:", sorted(map(str, st))[:8], "start:", g.get("start_time"), "season/week:", g.get("season"), g.get("week"))
            print("    boxscore shape:", json.dumps(shape(g.get("boxscore")))[:1500])
            if full < 7:
                full += 1
                done = next((x for x in gs if str(x.get("status")) in ("complete", "closed", "final")), None)
                live = next((x for x in gs if str(x.get("status")) in ("inprogress", "in_progress", "halftime")), None)
                for tag, x in (("FIRST", g), ("FINAL", done), ("LIVE", live)):
                    if x is not None:
                        print(f"    ---- {tag} GAME JSON (cut at 9000) ----")
                        print("    " + json.dumps(x, separators=(",", ":"))[:9000])
    except urllib.error.HTTPError as e:
        print(f"ERR {name}: HTTP {e.code} {e.read()[:200]!r}")
    except Exception as e:
        print(f"ERR {name}: {str(e)[:150]}")
    time.sleep(1)
