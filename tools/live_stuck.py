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


COOL_S = 15 * 60     # 11/15 FABLE AUDIT: one cancel, then the fresh watch gets this long before another. The pacer runs
#                      the backstop every 5 minutes: on 11/14 night (a 25-game Saturday, every live check slower than the
#                      watch's own watchdog) the board never got pushed, so EVERY backstop pass saw "running 5+ min, board
#                      5+ min old" and cancelled the watch that had just started - a cancel kills the background grader
#                      mid-run too. A watch that can't push within 15 minutes of a cancel is cancelled again; never a
#                      cancel every pass.


def _age_s(iso, now):
    try:
        return (now - datetime.fromisoformat(str(iso).replace("Z", "+00:00"))).total_seconds()
    except (TypeError, ValueError):
        return None


def stuck_runs(age=None, runs=None, now=None):
    age = board_age() if age is None else age
    if age is None or age < STUCK_S:
        return []
    if runs is None:
        out = subprocess.run(["gh", "run", "list", "--workflow", "sports-live.yml", "--limit", "10", "--json",
                              "databaseId,status,startedAt,conclusion,updatedAt"], capture_output=True, text=True,
                             timeout=60).stdout
        runs = json.loads(out or "[]")
    now = now or datetime.now(timezone.utc)
    for r in runs:                                       # a watch was cancelled minutes ago: its replacement gets time
        a = _age_s(r.get("updatedAt"), now) if r.get("conclusion") == "cancelled" else None
        if a is not None and 0 <= a < COOL_S:
            return []
    return [r["databaseId"] for r in runs if r.get("status") == "in_progress" and r.get("startedAt")
            and (_age_s(r["startedAt"], now) or 0) > STUCK_S]


if __name__ == "__main__":
    for rid in stuck_runs():
        print(rid)
