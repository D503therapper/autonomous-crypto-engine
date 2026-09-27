"""Run one full live check the way the watcher does, and print any error with its traceback."""
import subprocess
import sys
import traceback

sys.path.insert(0, ".")
import sports_live as sl  # noqa: E402

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
