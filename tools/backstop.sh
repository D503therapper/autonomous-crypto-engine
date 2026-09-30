#!/usr/bin/env bash
# Backstops (GitHub skips scheduled runs): any workflow that runs this starts what's missing.
#  - the tennis slate is due and not up -> run the engine now
#  - a game is live / within 2 hours and no live watch is running -> start one
#  - the hourly bug check (health.yml) is 90+ minutes old -> run it
# Never fails the job that calls it.
busy() { gh run list --workflow "$1" --limit 10 --json status -q '[.[] | select(.status != "completed")] | length' 2>/dev/null || echo 1; }
if [ "$(python tools/tennis_due.py 2>/dev/null | tail -1)" = "yes" ]; then
  if [ "$(busy sports.yml)" = "0" ]; then gh workflow run sports.yml --ref main && echo "backstop: tennis slate due - engine started"; else echo "backstop: tennis slate due - engine already running"; fi
fi
if [ "${SKIP_LIVE:-}" != "1" ] && [ "$(python tools/live_needed.py 2>/dev/null | tail -1)" = "yes" ]; then
  for id in $(python tools/live_stuck.py 2>/dev/null); do    # "running" but its board froze: cancel it, start fresh
    gh run cancel "$id" && echo "backstop: live watch $id froze - cancelled"; sleep 5
  done
  if [ "$(busy sports-live.yml)" = "0" ]; then gh workflow run sports-live.yml --ref main && echo "backstop: live watch started"; else echo "backstop: live watch already on"; fi
fi
# the hourly bug check itself (9/29: GitHub's schedule left 3-hour gaps): older than 90 minutes -> run it now
age=$(python -c "
import json, datetime as d
try:
    at = json.load(open('data/sports/health.json'))['at']
    print(int((d.datetime.now(d.timezone.utc) - d.datetime.strptime(at, '%Y-%m-%dT%H:%MZ').replace(tzinfo=d.timezone.utc)).total_seconds() // 60))
except Exception:
    print(999)" 2>/dev/null)
if [ "${age:-999}" -gt 90 ] && [ "$(busy health.yml)" = "0" ]; then gh workflow run health.yml --ref main && echo "backstop: bug check ${age}m old - started"; fi
exit 0
