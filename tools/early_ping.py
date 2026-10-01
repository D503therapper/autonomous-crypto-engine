"""⏰ Sends this run's early-value-play pings only once the live dashboard shows the play (the owner: never a ping
for something that's not on the dashboard). Runs after the hourly push; checks the page every 20s for up to 6 min."""
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports_early as se      # noqa: E402
import sports_pings as spg     # noqa: E402  (💰 mid-day value plays - the same rule: only once the dashboard shows it)

URL = "https://d503therapper.github.io/autonomous-crypto-engine/sports/"

if __name__ == "__main__":
    now0 = datetime.now(timezone.utc)
    want_e, want_p = bool(se.pending(now0)), bool(spg.pending(now0))
    if not want_e and not want_p:
        print("no early-play or mid-day pings this run")
        sys.exit(0)
    for i in range(18):
        try:
            req = urllib.request.Request(f"{URL}?t={int(time.time())}", headers={"User-Agent": "d503-engine",
                                                                              "Cache-Control": "no-cache"})
            page = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")
        except Exception as e:                           # noqa: BLE001
            print(f"dashboard check failed: {str(e)[:60]}")
            page = ""
        if want_e:
            sent = se.send_queued(page, datetime.now(timezone.utc))
            if sent:
                want_e = False
                print(f"sent {len(sent)} early-play ping(s) - the dashboard shows them")
        if want_p:
            sent = spg.send_queued(page, datetime.now(timezone.utc))
            if sent:
                want_p = False
                print(f"sent {len(sent)} mid-day value play ping(s) - the dashboard shows them")
        if not want_e and not want_p:
            time.sleep(6)                                # (the pushes run in threads: let them finish)
            break
        time.sleep(20)
    else:
        print("some pings never went out: the dashboard never showed the play")
