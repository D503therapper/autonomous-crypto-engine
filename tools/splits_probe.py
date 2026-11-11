"""PROBE (branch probe/an-v2 only): real Action Network v2 scoreboard payloads, trimmed, gzip+base64 into the log so the
engine's v2 readers can be tested offline. Plain requests with the engine's own name - no browser disguise."""
import base64, gzip, json, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
H = {"User-Agent": "D503-sports-engine/1.0 (personal picks dashboard)", "Accept": "application/json"}
now = datetime.now(timezone.utc) - timedelta(hours=8)
TD, YD = now.strftime("%Y%m%d"), (now - timedelta(days=1)).strftime("%Y%m%d")
B2 = "https://api.actionnetwork.com/web/v2/scoreboard/"
U = [
    ("nba_yday", B2 + f"nba?bookIds=15,30&date={YD}"),
    ("nba_today_h1", B2 + f"nba?bookIds=15,30&periods=event,firsthalf&date={TD}"),
    ("ncaab_today_h1", B2 + f"ncaab?bookIds=15,30&periods=event,firsthalf&division=D1&date={TD}"),
    ("nhl_yday", B2 + f"nhl?bookIds=15,30&date={YD}"),
    ("nfl_2024_w3", B2 + "nfl?bookIds=15,30&season=2024&week=3&seasonType=reg"),
    ("ncaaf_w11", B2 + "ncaaf?bookIds=15,30&season=2026&week=11&seasonType=reg&division=FBS"),
    ("nfl_now", B2 + "nfl?bookIds=15"),
    ("mlb_2026_0930", B2 + "mlb?bookIds=15,30&periods=event,firstfiveinnings&date=20260930"),
]
for name, u in U:
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=25))
        gs = d.get("games") or []
        live = [g for g in gs if g.get("status") in ("inprogress", "in_progress", "halftime")]
        fin = [g for g in gs if g.get("status") in ("complete", "closed")]
        sch = [g for g in gs if g.get("status") == "scheduled"]
        keep = (fin[:2] + live[:2] + sch[:2]) or gs[:3]
        for g in keep:
            for bk in (g.get("markets") or {}).values():
                for per in bk.values():
                    per.pop("core_bet_type_6_team_score", None)
            for t in g.get("teams") or []:
                for k in ("logo", "primary_color", "secondary_color", "url_slug", "standings"):
                    t.pop(k, None)
        periods = sorted({p for g in gs for bk in (g.get("markets") or {}).values() for p in bk})
        types = sorted({t for g in gs for bk in (g.get("markets") or {}).values() for p in bk.values() for t in p})
        blob = base64.b64encode(gzip.compress(json.dumps({"games": keep}).encode())).decode()
        print(f"OK {name}: {len(gs)} games ({len(fin)} final, {len(live)} live, {len(sch)} scheduled) periods {periods} types {types}")
        print(f"BLOB {name} {blob}")
    except urllib.error.HTTPError as e:
        print(f"ERR {name}: HTTP {e.code}")
    except Exception as e:
        print(f"ERR {name}: {str(e)[:150]}")
    time.sleep(1)
