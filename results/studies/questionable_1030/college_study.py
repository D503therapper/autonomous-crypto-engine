"""10/30 QUESTIONABLE PLAYERS - college football, from what's on disk: every version of data/sports/injuries_official.json
in git (the official availability reports we've kept since 10/2) joined to our ESPN college box scores
(data/sports/roster/ncaaf_2026.csv.gz). Only the skill men a box score can see (QB / RB / WR / TE: a man in the box =
he played; a QB in the box with a pass attempt); a man must be in one of his team's box scores before the game
(a regular) or he's dropped. The LAST status we hold for the game day counts. A small sample - a first look only."""
import csv
import gzip
import json
import os
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
import sports_absences as sa  # noqa: E402

P = "data/sports/injuries_official.json"
revs = subprocess.run(["git", "log", "--format=%h %cI", "--", P], cwd=REPO, capture_output=True, text=True).stdout.split("\n")
last = {}                                        # (day, team id, player) -> (commit time, status, pos)
for line in reversed([x for x in revs if x]):
    h, t = line.split()
    try:
        d = json.loads(subprocess.run(["git", "show", f"{h}:{P}"], cwd=REPO, capture_output=True, text=True).stdout)
    except ValueError:
        continue
    for day, lg in d.items():
        if day.startswith("_") or not isinstance(lg, dict):
            continue
        for tid, tm in (lg.get("ncaaf") or {}).items():
            for p in tm.get("players") or []:
                if len(p) >= 3:
                    last[(day, tid, p[0])] = (t, p[2], p[1])

box = defaultdict(lambda: defaultdict(dict))    # team -> date (ET) -> {name: pass attempts}
from datetime import datetime, timedelta  # noqa: E402
for r in csv.DictReader(gzip.open(os.path.join(REPO, "data/sports/roster/ncaaf_2026.csv.gz"), "rt")):
    d = (datetime.strptime(r["start"][:16], "%Y-%m-%dT%H:%M") - timedelta(hours=7)).date().isoformat()
    try:
        st = json.loads(r["stats"] or "{}")
    except ValueError:
        st = {}
    n = sa._nm(r["player"])                     # (one row per stat group: passing / rushing / receiving - keep the max)
    box[r["team"]][d][n] = max(box[r["team"]][d].get(n, 0.0), sa._num(st.get("completions/passingAttempts")))

rows = []
for (day, tid, name), (_, status, pos) in last.items():
    s = status.lower()
    if pos not in ("QB", "RB", "WR", "TE") or not any(k in s for k in ("questionable", "doubtful", "probable", "out", "game")):
        continue
    games = box.get(str(tid)) or {}
    gd = [d for d in games if day <= d <= (datetime.fromisoformat(day) + timedelta(days=1)).date().isoformat()]
    if not gd:
        continue
    before = set().union(*[set(v) for d, v in games.items() if d < gd[0]] or [set()])
    if not sa.match(name, before):
        continue
    here = games[gd[0]]
    hit = [n for n in here if sa.match(name, {n})]
    played = bool(hit) and (pos != "QB" or here[hit[0]] > 0)
    rows.append((day, tid, name, pos, status, played))
print(len(rows), "college skill-player listings we can check")
for st in ("Probable", "Questionable", "Doubtful", "Out"):
    v = [r for r in rows if r[4].lower().startswith(st.lower())]
    if v:
        print(f"  {st:13s} played {sum(r[5] for r in v)}/{len(v)} = {sum(r[5] for r in v) / len(v) * 100:.0f}%"
              f"   QBs {sum(r[5] for r in v if r[3] == 'QB')}/{sum(1 for r in v if r[3] == 'QB')}")
for r in sorted(rows):
    if r[4].lower().startswith("questionable") and r[3] == "QB":
        print("   ", r)
