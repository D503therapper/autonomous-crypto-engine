"""THE HOURLY BUG CHECK (free: runs on GitHub, no Claude). Looks for the bugs we've actually hit, fixes what it can
on its own, and writes the rest to data/sports/health.json - the check-in reads it first.

Checks:
  1. the live watcher: running + its board fresh whenever a game's live or close (else: start it)
  2. grading: no pick (main board or tennis) sitting ungraded 20+ minutes after its game ended (else: re-grade now)
  3. live scores: our server's /scores answers (else: flagged)
  4. workflows: any failed run in the last 2 hours (flagged, with the workflow's name)
Prints a summary; FIX lines are actions it took, PROBLEM lines are for the check-in."""
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd          # noqa: E402

OUT = os.path.join(sd.DATA, "health.json")
REPO = os.environ.get("GITHUB_REPOSITORY", "D503therapper/autonomous-crypto-engine")
now = datetime.now(timezone.utc)
fixes, problems, ok = [], [], []


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    return r.stdout.strip() if r.returncode == 0 else ""


def busy(wf):
    out = gh("run", "list", "--workflow", wf, "--limit", "10", "--json", "status")
    try:
        return sum(1 for r in json.loads(out or "[]") if r.get("status") != "completed")
    except ValueError:
        return 1


def dispatch(wf, why):
    if busy(wf):
        fixes.append(f"{why} - {wf} already running")
        return
    gh("workflow", "run", wf, "--ref", "main")
    fixes.append(f"{why} - started {wf}")


def _t(iso):
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


# 1. the live watcher
try:
    import sports_live as sl
    games = sd.load_games()
    needed = sl.any_live_soon(games, sl.STAY_MIN)
except Exception as e:                                   # noqa: BLE001
    games, needed = {}, False
    problems.append(f"couldn't load games: {str(e)[:80]}")
if needed:
    age = None
    try:
        raw = urllib.request.urlopen(f"https://raw.githubusercontent.com/{REPO}/live-data/live.json?t={int(time.time())}",
                                     timeout=20).read()
        age = time.time() - json.loads(raw)["updated"] / 1000
    except Exception as e:                               # noqa: BLE001
        problems.append(f"live board unreadable: {str(e)[:60]}")
    if age is not None and age > 8 * 60:
        dispatch("sports-live.yml", f"live board {age / 60:.0f} min stale with games on")
    elif age is not None:
        ok.append(f"live watcher fresh ({age:.0f}s)")

# 2. grading: finished games whose picks still sit open
late = []
try:
    picks = json.load(open(os.path.join(sd.DATA, "picks.json")))
    for p in picks[-30:]:
        for l in p.get("legs") or []:
            g = games.get(l.get("game_id"))
            if l.get("result") is None and g and g.get("status") == "final" and g.get("start") and \
                    now - _t(g["start"]) > timedelta(hours=5):
                late.append(f"{p['date']} {p['kind']} {l.get('team')}")
except Exception as e:                                   # noqa: BLE001
    problems.append(f"picks unreadable: {str(e)[:60]}")
try:
    import sports_tennis as st
    rows = []
    for tour in st.TOURS:
        for d in (-1, 0):
            try:
                data = json.load(urllib.request.urlopen(st.ESPN.format(tour=tour) + f"?dates={(now + timedelta(days=d)):%Y%m%d}",
                                                         timeout=20))
                rows += st.parse_espn(data, tour)
            except Exception:                            # noqa: BLE001
                pass
    fin = {r["id"] for r in rows if st._state(r) in ("final", "retired", "void")}
    for s in st._load_picks()[-3:]:
        for l in s.get("picks") or []:
            if l.get("result") is None and l.get("match") in fin:
                late.append(f"tennis {s['date']} {l.get('player')}")
except Exception as e:                                   # noqa: BLE001
    problems.append(f"tennis check failed: {str(e)[:60]}")
if late:
    dispatch("sports.yml", f"{len(late)} finished pick(s) not graded ({', '.join(late[:4])})")
else:
    ok.append("every finished pick graded")

# 3. live scores route
try:
    api = open(os.path.join(sd.DATA, "ask_url.txt")).read().strip().rstrip("/")
    r = urllib.request.urlopen(urllib.request.Request(f"{api}/scores?ids=nfl:0", headers={"Origin": "https://d503therapper.github.io"}),
                               timeout=20)
    ok.append(f"scores route up ({r.status})")
except Exception as e:                                   # noqa: BLE001
    problems.append(f"scores route down: {str(e)[:60]}")

# 4. failed workflows (last 2 hours)
try:
    runs = json.loads(gh("run", "list", "--limit", "60", "--json", "name,conclusion,createdAt,url") or "[]")
    bad = [r for r in runs if r.get("conclusion") == "failure" and now - datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00"))
           < timedelta(hours=2) and r.get("name") != "pages build and deployment"]
    for r in bad[:5]:
        problems.append(f"workflow failed: {r['name']} {r['createdAt'][:16]} {r['url']}")
    if not bad:
        ok.append("no failed workflows")
except Exception as e:                                   # noqa: BLE001
    problems.append(f"workflow list failed: {str(e)[:60]}")

report = {"at": now.strftime("%Y-%m-%dT%H:%MZ"), "fixes": fixes, "problems": problems, "ok": ok}
try:
    hist = json.load(open(OUT)).get("history", [])
except (OSError, ValueError):
    hist = []
report["history"] = ([{k: report[k] for k in ("at", "fixes", "problems")}] + hist)[:72]   # the last 3 days
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(report, f, indent=1)
for x in fixes:
    print("FIX", x)
for x in problems:
    print("PROBLEM", x)
for x in ok:
    print("OK", x)
