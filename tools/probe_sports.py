"""Run one full live check the way the watcher does, and print any error with its traceback."""
import subprocess
import sys
import traceback

sys.path.insert(0, ".")
import sports_live as sl  # noqa: E402

import json, urllib.request  # noqa: E401,E402
for url in [sl.BOVADA.format(path="baseball/mlb"), sl.BOVADA_OLD.format(path="baseball/mlb"),
            sl.BOVADA.format(path="baseball/mlb").replace("&liveOnly=true", ""),
            sl.BOVADA.format(path="football/nfl").replace("&liveOnly=true", ""),
            "https://www.bovada.lv/services/sports/event/v2/events/A/description/baseball?marketFilterId=def&liveOnly=true&lang=en",
            "https://www.bovada.lv/services/sports/event/v2/events/A/description?marketFilterId=def&liveOnly=true&lang=en"]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read()
        try:
            d = json.loads(body)
            info = f"{len(d)} groups, {sum(len(g.get('events') or []) for g in d)} events, live={sum(bool(e.get('live')) for g in d for e in g.get('events') or [])}, paths={[g.get('path', [{}])[0].get('link') for g in d][:4]}"
        except ValueError:
            info = f"not json: {body[:200]!r}"
        print("BOVADA", r.status, url[60:140], info)
    except Exception as e:                                   # noqa: BLE001
        print("BOVADA ERR", url[60:140], e)
board = subprocess.run(["git", "fetch", "-q", "origin", sl.LIVE_BRANCH], capture_output=True)
b = subprocess.run(["git", "show", f"origin/{sl.LIVE_BRANCH}:live.json"], capture_output=True, text=True)
if b.returncode == 0:
    open(sl.LIVE_JSON, "w").write(b.stdout)
for i in range(2):
    try:
        plays = sl.run()
        print("run ok:", [(p["team"], p["odds"]) for p in plays])
    except Exception:                                        # noqa: BLE001
        traceback.print_exc(file=sys.stdout)
subprocess.run(["git", "checkout", "--", sl.LIVE_JSON, sl.LOG])
