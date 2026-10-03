"""⏱ THE PACER - the clock GitHub's schedule isn't (10/3). GitHub skips scheduled runs for hours at a time: 10/2 the
engine's hourly runs went missing 10:54 AM - 2:03 PM PT; 10/3 not one of the 7:44 / 7:47 / 8 AM board crons fired (only
one in ~25 due engine crons ran), and the board went up at 8:01 only because a live watch's backstop happened to see the
tennis slate due. The hourly bug check (health.yml) that restarts a skipped engine is itself a cron that gets skipped the
same way (10/3: one scheduled health run in 17 hours). Every cron in this repo is a hope, not a clock.

The pacer is the clock: ONE job always running (pacer.yml, ~50 minutes a leg, then it queues the next leg - dispatches
never skip). Every minute it checks what should have started and starts it:
  - the engine: a run every hour (HOURLY_MIN since the last one started), a run at 7:40 PT so the board posts at 8:00
    sharp (sports.BOARD_EARLY_MIN: the run pulls everything, then waits for 8:00), and from 8:00 on a run every
    BOARD_RETRY_MIN minutes until today's board is up (games today, not posted yet)
  - everything tools/backstop.sh covers (every 5th minute): the tennis slate, the live watch, the hourly bug check
If the chain breaks (a runner dies, a bad deploy), the engine's and the live watch's backstop, the bug check and the
pacer's own cron all start it again - any one of them running is enough.

Usage: python tools/pacer.py            one pass (the workflow loops it every minute)
       python tools/pacer.py --next     queue the next leg unless one's already waiting
Needs GH_TOKEN (the workflow's own token). Never fails the job."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PT = ZoneInfo("America/Los_Angeles")
HOURLY_MIN = 65              # the engine's hourly cron (:23) is skipped: 65+ minutes since its last run started -> start one
BOARD_PULL = (7, 40)         # = sports.BOARD_EARLY_MIN: a run from 7:40 PT pulls + checks everything, posts at 8:00 sharp
BOARD_RETRY_MIN = 9          # 8 AM hour, board not up: a fresh try every ~10 minutes (what the :02/:12/:32/:42/:52 crons meant)
ENGINE = "sports.yml"
SELF = "pacer.yml"


def gh(*args, timeout=60):
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def runs(wf, limit=10):
    out = gh("run", "list", "--workflow", wf, "--limit", str(limit), "--json", "status,createdAt,databaseId")
    try:
        return json.loads(out or "[]")
    except ValueError:
        return []


def busy(rows, skip_id=None):
    """Runs not finished (queued, waiting, in progress) - never counting this job itself."""
    return sum(1 for r in rows if r.get("status") != "completed" and str(r.get("databaseId")) != str(skip_id))


def _t(iso):
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def engine_due(now, last_started, posted, games_today, engine_busy):
    """Why the engine should start right now ('' = it shouldn't). `last_started`: when its newest run was created
    (None = never seen); `posted`: today's board (Pacific) has a posted pick; `games_today`: real games today."""
    if engine_busy:
        return ""
    pt = now.astimezone(PT)
    age = (now - last_started).total_seconds() / 60 if last_started else 1e9
    if age > HOURLY_MIN:
        return f"hourly run skipped - {age:.0f} min since the engine last started" if last_started else "no engine run on record"
    pull_at = pt.replace(hour=BOARD_PULL[0], minute=BOARD_PULL[1], second=0, microsecond=0)
    if pt.hour == BOARD_PULL[0] and pt.minute >= BOARD_PULL[1] and last_started < pull_at:
        return "7:40 PT run: pull + check everything, post the board at 8:00 sharp"
    if pt.hour == 8 and games_today and not posted and age >= BOARD_RETRY_MIN:
        return f"8 AM board not up at {pt:%-I:%M %p} PT ({age:.0f} min since the engine last started)"
    return ""


def posted_today(now, path=None):
    import sports_data as sd
    today = now.astimezone(PT).date().isoformat()
    try:
        picks = json.load(open(path or os.path.join(sd.DATA, "picks.json")))
    except (OSError, ValueError):
        return False
    return any(p.get("date") == today and p.get("status") != "waiting" for p in picks)


def games_today(now):
    """Real games today (Pacific) - only loaded when it matters (the 8 AM hour, board not up)."""
    import sports_data as sd
    today = now.astimezone(PT).date()
    try:
        G = sd.load_games()
    except Exception:                                    # noqa: BLE001 - unreadable games never stop the board
        return True
    return any(g.get("start") and g.get("status") != "void" and (g.get("stype") or "?") in sd.REAL and g.get("league") in sd.LEAGUES
               and _t(g["start"]).astimezone(PT).date() == today for g in G.values())


def tick(now=None, backstop=False):
    now = now or datetime.now(timezone.utc)
    rows = runs(ENGINE)
    last = _t(rows[0]["createdAt"]) if rows else None
    pt = now.astimezone(PT)
    posted = posted_today(now) if pt.hour == 8 else False
    g_today = games_today(now) if pt.hour == 8 and not posted else False
    why = engine_due(now, last, posted, g_today, busy(rows))
    if why:
        gh("workflow", "run", ENGINE, "--ref", "main")
        print(f"pacer {pt:%H:%M} PT: {why} - engine started", flush=True)
    else:
        print(f"pacer {pt:%H:%M} PT: engine ran {((now - last).total_seconds() / 60) if last else 1e9:.0f} min ago - fine", flush=True)
    if backstop:
        try:
            r = subprocess.run(["bash", "tools/backstop.sh"], capture_output=True, text=True, timeout=120)
            if r.stdout.strip():
                print(r.stdout.strip()[:400], flush=True)
        except Exception as e:                           # noqa: BLE001
            print(f"backstop skipped: {e}", flush=True)
    return why


def queue_next():
    """The next leg of the chain - unless a pacer run is already waiting / running besides this one."""
    me = os.environ.get("GITHUB_RUN_ID")
    if busy(runs(SELF), skip_id=me):
        print("pacer: the next leg is already queued", flush=True)
        return False
    gh("workflow", "run", SELF, "--ref", "main")
    print("pacer: next leg queued", flush=True)
    return True


if __name__ == "__main__":
    if not os.environ.get("GH_TOKEN"):
        print("pacer: no GH_TOKEN - nothing started")
    elif "--next" in sys.argv:
        queue_next()
    else:
        tick(backstop="--backstop" in sys.argv)
    sys.exit(0)
