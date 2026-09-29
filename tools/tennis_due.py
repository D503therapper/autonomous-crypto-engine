"""Backstop for the tennis slate: prints "yes" when the day's slate should be up (from 8am Pacific on game day)
and isn't, while the book has lines on the board. The workflows that run it then start the engine right away -
GitHub skips scheduled runs, and once left the slate waiting past its time."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_tennis as st     # noqa: E402


def due(now=None):
    now = now or datetime.now(timezone.utc)
    local = now.astimezone(st.PT)
    if local.hour < st.POST_FROM_HOUR_PT:
        return False
    day = local.date().isoformat()
    if any(p.get("date") == day for p in st._load_picks()):
        return False
    try:
        lines = json.load(open(st.ODDS)).get("lines") or []
    except (OSError, ValueError):
        lines = []
    soon = (now + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M")
    return any(now.strftime("%Y-%m-%dT%H:%M") <= (ln.get("start") or "") <= soon for ln in lines)


if __name__ == "__main__":
    print("yes" if due() else "no")
