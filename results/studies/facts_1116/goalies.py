"""11/16 FABLE - EVERY FACT TRUE, item 5: the goalie the card names vs who started, 11/1-11/15.
For every NHL side: the goalie page's name + status (data/sports/nhl_goalies.json from this repo's history) at the 8 AM PT
board (16:00Z) and at the last snapshot before the puck, our own box-score projection (sports_players.projected_starter),
and the truth (the box score's goalie row). Right / sides by the page's status word.
python results/studies/facts_1116/goalies.py -> goalies_out.txt"""
import csv
import json
import os
import subprocess
import sys
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import sports_data as sd            # noqa: E402
import sports_players as sp         # noqa: E402

SINCE, UNTIL = "2026-11-01", "2026-11-16"
rows = sorted(csv.DictReader(open("data/sports/players/nhl.csv")), key=lambda r: r["start"])
truth = {(r["gid"], r["team"]): r["player"] for r in rows}
games = {k: g for k, g in sd.load_games().items() if g["league"] == "nhl" and SINCE <= g["start"][:10] <= UNTIL
         and g.get("status") == "final"}
log = subprocess.run(["git", "log", "--format=%H %cI", "--since=2026-10-31T00:00:00Z", "--until=2026-11-16T12:00:00Z", "--",
                      "data/sports/nhl_goalies.json"], capture_output=True, text=True).stdout.split("\n")
snaps = sorted((ln.split()[1][:16].replace("+00:00", ""), ln.split()[0]) for ln in log if ln.strip())
print(len(snaps), "snapshots of the goalie page,", len(games), "finished NHL games")
_C = {}


def snap(h):
    if h not in _C:
        try:
            _C[h] = json.loads(subprocess.run(["git", "show", f"{h}:data/sports/nhl_goalies.json"], capture_output=True,
                                              text=True).stdout).get("games") or {}
        except ValueError:
            _C[h] = {}
        if len(_C) > 400:
            _C.pop(next(iter(_C)))
    return _C[h]


def at(gid, side, cut):
    """The page's (name, status) for a side at the last snapshot at or before `cut` that carries the game."""
    for t, h in reversed([s for s in snaps if s[0] <= cut]):
        if t < cut[:10] + "T00:00" and t < cut[:8] + f"{int(cut[8:10]) - 1:02d}T12:00":
            break
        v = (snap(h).get(gid) or {}).get(side)
        if v and v.get("name"):
            return v["name"], v.get("status") or "?"
    return None, "nothing on the page"


def nm(x):
    return sp._nm(x)


res = defaultdict(lambda: [0, 0])
wrong = []
for gid, g in sorted(games.items(), key=lambda kv: kv[1]["start"]):
    from datetime import datetime, timedelta
    st = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M")
    pt_day = (st - timedelta(hours=8)).strftime("%Y-%m-%d")
    board = f"{pt_day}T16:00"
    for side in ("home", "away"):
        real = truth.get((gid, g[side]))
        if not real:
            continue
        ours = sp.projected_starter(rows, g[side], g["start"])
        last = sp.last_starter(rows, g[side], g["start"])
        for label, cut in (("8 AM board", board), ("last look before the puck", g["start"][:16])):
            name, status = at(gid, side, cut)
            hit = bool(name) and nm(name) == nm(real)
            if name:
                res[f"{label}: the page says '{status}'"][0] += hit
                res[f"{label}: the page says '{status}'"][1] += 1
                if not hit and status in ("confirmed", "likely", "expected"):
                    wrong.append(f"  {g['start'][:10]} {g[side + '_name']}: the page '{status}' {name} at {label} - {real} started")
            else:
                res[f"{label}: nothing on the page"][1] += 1
        res["our projection (box scores)"][0] += bool(ours) and nm(ours) == nm(real)
        res["our projection (box scores)"][1] += 1
        res["the last starter goes again"][0] += bool(last) and nm(last) == nm(real)
        res["the last starter goes again"][1] += 1
out = [f"THE GOALIE NAMED vs WHO STARTED, NHL {SINCE}..{UNTIL} ({len(games)} games)"]
for k in sorted(res):
    a, n = res[k]
    out.append(f"  {k:55s} {a:4d}/{n:4d}" + (f" = {a / n:.1%}" if n else ""))
out.append("A 'known' (confirmed / likely / expected) name that did NOT start:")
out += wrong or ["  none"]
txt = "\n".join(out)
print(txt)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "goalies_out.txt"), "w").write(txt + "\n")
