"""A live watch that's "running" but froze (9/29: its board sat on a dead +125 while the real line went -150, and
the backstops saw "already running" and left it). Prints the run ids to cancel: in progress 5+ minutes while the
live board hasn't moved in 5+ minutes. Nothing printed = all good."""
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone

REPO = os.environ.get("GITHUB_REPOSITORY", "D503therapper/autonomous-crypto-engine")
STUCK_S = 5 * 60


def board_age():
    try:
        raw = urllib.request.urlopen(f"https://raw.githubusercontent.com/{REPO}/live-data/live.json?t={int(time.time())}",
                                     timeout=20).read()
        return time.time() - json.loads(raw)["updated"] / 1000
    except Exception:                                    # noqa: BLE001
        return None


def stuck_runs(age=None, runs=None, now=None):
    age = board_age() if age is None else age
    if age is None or age < STUCK_S:
        return []
    if runs is None:
        out = subprocess.run(["gh", "run", "list", "--workflow", "sports-live.yml", "--limit", "10", "--json",
                              "databaseId,status,startedAt"], capture_output=True, text=True, timeout=60).stdout
        runs = json.loads(out or "[]")
    now = now or datetime.now(timezone.utc)
    return [r["databaseId"] for r in runs if r.get("status") == "in_progress" and r.get("startedAt")
            and (now - datetime.fromisoformat(r["startedAt"].replace("Z", "+00:00"))).total_seconds() > STUCK_S]


if __name__ == "__main__":
    for rid in stuck_runs():
        print(rid)
