"""THE HOURLY BUG CHECK (free: runs on GitHub, no Claude). Looks for the bugs we've actually hit, fixes what it can
on its own, and writes the rest to data/sports/health.json - the check-in reads it first.

Checks:
  1. the live watcher: running + its board fresh whenever a game's live or close (else: start it)
  2. grading: no pick (main board or tennis) sitting ungraded 20+ minutes after its game ended (else: re-grade now)
  3. live scores: our server's /scores answers (else: flagged)
  4. workflows: any failed run in the last 2 hours (flagged, with the workflow's name)
  5. alerts: the engine's key still opens the 🔔 push (a dry run - nobody gets pinged)
  6. the live board, while games are on: scores flowing, the book's live prices fresh (not its 10-minute cache),
     every live bet today saved (none only on the board), and which sources are down (the backups took over)
  7. posting: the tennis slate and the main board are up from 8am PT (else: run the engine now)
Prints a summary; FIX lines are actions it took, PROBLEM lines are for the check-in."""
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
    if age is not None and age > 5 * 60:
        import live_stuck                                # "running" but frozen: cancel it first (else "already running")
        for rid in live_stuck.stuck_runs(age):
            gh("run", "cancel", str(rid))
            fixes.append(f"live watch {rid} froze ({age / 60:.0f} min) - cancelled")
            time.sleep(5)
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
    r = urllib.request.urlopen(urllib.request.Request(f"{api}/scores?ids=nfl:0", headers={"Origin": "https://d503therapper.github.io",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"}),
                               timeout=20)
    ok.append(f"scores route up ({r.status})")
except Exception as e:                                   # noqa: BLE001
    problems.append(f"scores route down: {str(e)[:60]}")

# 3b. the question box answers (9/29: it went to "the AI's taking a breather" and nobody knew why)
try:
    api = open(os.path.join(sd.DATA, "ask_url.txt")).read().strip().rstrip("/")
    req = urllib.request.Request(api, data=json.dumps({"q": "health check: what's the Lock of the Day? one line"}).encode(),
                                 headers={"Content-Type": "application/json", "Origin": "https://d503therapper.github.io",
                                          "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) Mobile/15E148"})
    try:
        got = json.load(urllib.request.urlopen(req, timeout=90))
        (ok if got.get("answer") else problems).append("question box " + ("answers" if got.get("answer") else f"empty: {got}"[:120]))
    except urllib.error.HTTPError as e:
        problems.append(f"question box down ({e.code}): {e.read()[:160].decode('utf-8', 'ignore')}")
except Exception as e:                                   # noqa: BLE001
    problems.append(f"question box check failed: {str(e)[:60]}")

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

# 5. alerts: the key still opens the push (dry run)
try:
    api = open(os.path.join(sd.DATA, "ask_url.txt")).read().strip().rstrip("/")
    key = sd._push_key()
    if not key:
        problems.append("alert key missing (CLOUDFLARE_* not in this run's env)")
    else:
        req = urllib.request.Request(f"{api}/push", data=json.dumps({"key": key, "dry": True}).encode(),
                                     headers={"Content-Type": "application/json", "Origin": "https://d503therapper.github.io",
                                              "User-Agent": "Mozilla/5.0"})
        got = json.load(urllib.request.urlopen(req, timeout=20))
        (ok if got.get("dry") else problems).append("alerts: engine key " + ("works" if got.get("dry") else f"refused {got}"))
except Exception as e:                                   # noqa: BLE001
    problems.append(f"alerts check failed: {str(e)[:60]}")

# 6. the live board's insides while games are on
if needed:
    try:
        board = json.loads(urllib.request.urlopen(urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/contents/live.json?ref=live-data",
            headers={"Accept": "application/vnd.github.raw"}), timeout=20).read())
        books = str((board.get("tennis") or {}).get("books") or "")
        if " 0 fresh" in books and not books.startswith("0 "):
            problems.append(f"tennis live prices all stale ({books}) - no live tennis plays can go up")
        elif books:
            ok.append(f"tennis live prices: {books}")
        if (board.get("live_games") or 0) > 0 and not board.get("scores"):
            problems.append("games on but no live scores on the board")
        down = {k: v for k, v in (board.get("sources") or {}).items() if str(v).startswith("down")}
        if down:                                         # a source failed - the next one took over (the owner, 9/29)
            problems.append("sources down (the backups took over): " + ", ".join(f"{k} {v[5:]}" for k, v in list(down.items())[:6]))
        elif board.get("sources"):
            ok.append(f"all {len(board['sources'])} backup sources answering")
        saved = set((json.load(open(os.path.join(sd.DATA, "live_log.json"))).get("plays") or {}))
        lost = [t["team"] for t in board.get("today") or [] if t["pid"] not in saved]
        if lost:
            problems.append(f"live bets on the board but not saved on main: {', '.join(lost)} (the next page build merges them)")
        else:
            ok.append("every live bet today saved")
    except Exception as e:                               # noqa: BLE001
        problems.append(f"live board check failed: {str(e)[:60]}")

# 6b. no game coming up that the engine can't see (9/29: a playoff game kept a "TBD" team id and was skipped)
try:
    soon = (now + timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M")
    blind = [g for g in (games or {}).values() if g.get("status") == "pre" and now.strftime("%Y-%m-%dT%H:%M") <= (g.get("start") or "")[:16] <= soon
             and not (sd._real_team(g.get("home")) and sd._real_team(g.get("away"))) and "TBD" not in (g.get("home_name", "") + g.get("away_name", ""))]
    if blind:
        problems.append("games the engine can't see (placeholder team): " + ", ".join(f"{g['away_name']} @ {g['home_name']}" for g in blind[:5]))
        dispatch("sports.yml", "re-sync games with placeholder teams")
    else:
        ok.append("every upcoming game has its real teams")
except Exception as e:                                   # noqa: BLE001
    problems.append(f"placeholder-team check failed: {str(e)[:60]}")

# 6c. the engine knows who's playing baseball (9/29: Aaron Judge on the IL and the engine never knew)
try:
    mlb_soon = [g for g in (games or {}).values() if g.get("league") == "mlb" and g.get("status") == "pre"
                and now.strftime("%Y-%m-%dT%H:%M") <= (g.get("start") or "")[:16] <= soon]
    if mlb_soon:
        st = sd.mlb_stars()
        age = None
        try:
            age = (now.date() - datetime.strptime(json.load(open(sd.STARS_PATH))["day"], "%Y-%m-%d").date()).days
        except Exception:                                # noqa: BLE001
            pass
        if len(st) < 25 or age is None or age > 2:
            problems.append(f"baseball star list stale or missing ({len(st)} teams, {age} days old) - lineups not watched")
        else:
            ok.append(f"baseball star list fresh ({len(st)} teams)")
except Exception as e:                                   # noqa: BLE001
    problems.append(f"baseball star check failed: {str(e)[:60]}")

# 6d. the studies + the simulator run three times a day (9/29: GitHub's schedule ran them 5-6 hours late and skipped
#     one - the owner wants three a day). Older than 9 hours: kick one off.
for name, wf, log in (("studies", "sports_studies.yml", "studies_log.json"), ("simulator", "sports_sims.yml", "sims_log.json")):
    try:
        L = json.load(open(os.path.join(sd.DATA, log)))
        at = max(r["at"] for r in L) if isinstance(L, list) and L else ""
        age_h = (now - datetime.strptime(at, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)).total_seconds() / 3600
        if age_h > 9:
            problems.append(f"{name} last ran {age_h:.0f}h ago - restarted")
            if not busy(wf):
                dispatch(wf, f"{name} overdue ({age_h:.0f}h)")
        else:
            ok.append(f"{name} ran {age_h:.0f}h ago")
    except Exception as e:                               # noqa: BLE001
        problems.append(f"{name} check failed: {str(e)[:60]}")

# 7. posting on time
try:
    import tennis_due
    if tennis_due.due(now):
        dispatch("sports.yml", "tennis slate due (8am PT) and not up")
    else:
        ok.append("tennis slate on time")
except Exception as e:                                   # noqa: BLE001
    problems.append(f"tennis slate check failed: {str(e)[:60]}")
try:
    from zoneinfo import ZoneInfo
    pt = now.astimezone(ZoneInfo("America/Los_Angeles"))
    today = pt.date().isoformat()
    games_today = [g for g in (games or {}).values() if g.get("start") and
                   _t(g["start"]).astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat() == today]
    posted = any(p.get("date") == today for p in json.load(open(os.path.join(sd.DATA, "picks.json"))))
    if pt.hour >= 9 and games_today and not posted:
        dispatch("sports.yml", f"main board not up at {pt:%-I:%M %p} PT with {len(games_today)} games today")
    elif pt.hour >= 9 and games_today:
        ok.append("main board up")
except Exception as e:                                   # noqa: BLE001
    problems.append(f"main board check failed: {str(e)[:60]}")

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
