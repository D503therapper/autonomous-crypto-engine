"""Run one full live check the way the watcher does, and print any error with its traceback."""
import subprocess
import sys
import traceback

sys.path.insert(0, ".")
import sports_live as sl  # noqa: E402
import sports_data as sd_  # noqa: E402

# Bovada through the watcher's own code
for lg in ("mlb", "nfl"):
    path = sl.BOVADA_PATH[lg]
    for url in (sl.BOVADA, sl.BOVADA_OLD, sl.BOVADA_ALL, sl.BOVADA_SPORT):
        u = url.format(path=path, sport=path.split("/")[0])
        try:
            d = sl._get(u)
            print("BOVADA", lg, u[60:150], type(d).__name__, len(d) if isinstance(d, list) else str(d)[:200],
                  sum(len(g.get("events") or []) for g in d) if isinstance(d, list) else "",
                  sum(bool(e.get("live")) for g in d for e in g.get("events") or []) if isinstance(d, list) else "")
        except Exception as e:                               # noqa: BLE001
            print("BOVADA ERR", lg, u[60:150], e)
    print("bovada_live", lg, len(sl.bovada_live(lg)), sl.BOOKS.get(lg))
g_ = sd_.load_games().get("nfl:401872962")
if g_:
    print("SECOND HALF BALL (Rams @ Broncos):", sl.second_half_ball("nfl", g_), "| first drive team id:",
          sl.KICK.get("401872962"), "| home", g_["home"], g_["home_name"], "| away", g_["away"], g_["away_name"], sd_.ERRORS[-2:])
sl.notify({"team": "Test", "odds": 150, "score": "D503 1 @ Books 0", "clock": "Q1",
           "line": "If you see this, live plus money alerts are working. Let's eat."})
print("TEST PUSH sent to ntfy topic", sl.NTFY_TOPIC, sd_.ERRORS[-1:])
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
