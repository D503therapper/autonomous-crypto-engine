"""📣 A one-time announcement to everybody (only when the owner asks - the automatic pings are live plus money only).
Waits until the live dashboard shows `wait_for` (e.g. the Dog of the Day card), then sends title + body to phones:
the dashboard's own alerts (Web Push through the Worker) + the ntfy channel. Usage: python tools/announce.py TITLE BODY
[WAIT_FOR]"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports_data as sd      # noqa: E402

URL = "https://d503therapper.github.io/autonomous-crypto-engine/sports/"
TOPIC = "d503-live-7b1123"


def page():
    req = urllib.request.Request(f"{URL}?t={int(time.time())}", headers={"User-Agent": "d503-engine", "Cache-Control": "no-cache"})
    return urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")


if __name__ == "__main__":
    title, body = sys.argv[1], sys.argv[2]
    wait_for = sys.argv[3] if len(sys.argv) > 3 else ""
    if wait_for:
        for i in range(40):                                  # up to ~13 minutes for the page to show it
            try:
                html = page()
                board = html[html.find('<div class="board">'):]
                board = board[:board.find('<div class="sec">')] if '<div class="sec">' in board else board
                if all(w.strip().lower() in board.lower() for w in wait_for.split("&")):   # today's board only (the
                    break                                                                   # records say these too)
            except Exception as e:                           # noqa: BLE001
                print(f"page check failed: {str(e)[:60]}")
            time.sleep(20)
        else:
            print(f"the dashboard never showed '{wait_for}' - nothing sent")
            sys.exit(1)
    raw = None
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{TOPIC}", data=body.encode(), method="POST",
                                     headers={"Title": title.encode("latin-1", "ignore").decode("latin-1"),
                                              "Tags": "loudspeaker", "Click": URL})
        raw = urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:                                   # noqa: BLE001
        print(f"ntfy failed: {str(e)[:60]}")
    t = sd.web_push(raw, title, body, ref=f"announce:{int(time.time() // 3600)}")
    if t:
        t.join(10)
    print("sent:", title, "|", body)
