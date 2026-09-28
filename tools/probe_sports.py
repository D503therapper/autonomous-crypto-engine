"""Probe: ask the AI question box one real question through the live relay (the way the dashboard does)."""
import json
import time
import urllib.request

URL = open("data/sports/ask_url.txt").read().strip()
for q in ("why we on the Bears tonight?", "what's our record?"):
    t0 = time.time()
    req = urllib.request.Request(URL, data=json.dumps({"q": q}).encode(), method="POST",
                                 headers={"Origin": "https://d503therapper.github.io", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            print(f"Q: {q}\nHTTP {r.status} in {time.time() - t0:.1f}s\nA: {json.load(r).get('answer') or '(no answer)'}\n")
    except urllib.error.HTTPError as e:
        print(f"Q: {q}\nHTTP {e.code}: {e.read()[:300]}\n")
    except Exception as e:                                   # noqa: BLE001
        print(f"Q: {q}\nERR {e}\n")
