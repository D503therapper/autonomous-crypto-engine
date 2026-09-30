"""⏰ Sends this run's early-value-play pings only once the live dashboard shows the play (the owner: never a ping
for something that's not on the dashboard). Runs after the hourly push; checks the page every 20s for up to 6 min."""
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports_early as se      # noqa: E402

URL = "https://d503therapper.github.io/autonomous-crypto-engine/sports/"

if __name__ == "__main__":
    if not se.pending(datetime.now(timezone.utc)):
        print("no early-play pings this run")
        sys.exit(0)
    for i in range(18):
        try:
            req = urllib.request.Request(f"{URL}?t={int(time.time())}", headers={"User-Agent": "d503-engine",
                                                                              "Cache-Control": "no-cache"})
            page = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")
        except Exception as e:                           # noqa: BLE001
            print(f"dashboard check failed: {str(e)[:60]}")
            page = ""
        sent = se.send_queued(page, datetime.now(timezone.utc))
        if sent:
            time.sleep(6)                                # (the pushes run in threads: let them finish)
            print(f"sent {len(sent)} early-play ping(s) - the dashboard shows them")
            break
        time.sleep(20)
    else:
        print("no early-play pings to send (or the dashboard never showed them)")
