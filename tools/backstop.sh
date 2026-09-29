#!/usr/bin/env bash
# Backstops (GitHub skips scheduled runs): any workflow that runs this starts what's missing.
#  - the tennis slate is due and not up -> run the engine now
#  - a game is live / within 2 hours and no live watch is running -> start one
# Never fails the job that calls it.
busy() { gh run list --workflow "$1" --limit 10 --json status -q '[.[] | select(.status != "completed")] | length' 2>/dev/null || echo 1; }
if [ "$(python tools/tennis_due.py 2>/dev/null | tail -1)" = "yes" ]; then
  if [ "$(busy sports.yml)" = "0" ]; then gh workflow run sports.yml --ref main && echo "backstop: tennis slate due - engine started"; else echo "backstop: tennis slate due - engine already running"; fi
fi
if [ "${SKIP_LIVE:-}" != "1" ] && [ "$(python tools/live_needed.py 2>/dev/null | tail -1)" = "yes" ]; then
  if [ "$(busy sports-live.yml)" = "0" ]; then gh workflow run sports-live.yml --ref main && echo "backstop: live watch started"; else echo "backstop: live watch already on"; fi
fi
exit 0
