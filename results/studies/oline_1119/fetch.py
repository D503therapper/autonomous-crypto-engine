"""Download nflverse's public season files (plain public release downloads - no key, no login, our own name) into
~/.cache/d503_oline1119/dl (never the repo): the schedules (results + closing moneylines / spreads), snap counts,
injury reports and the weekly team stats (sacks made / allowed, passing yards).   python fetch.py"""
import os
import shutil
import urllib.request

DL = os.path.join(os.path.expanduser("~"), ".cache", "d503_oline1119", "dl")
OLD = os.path.join(os.path.expanduser("~"), ".cache", "d503_book1111", "dl")
os.makedirs(DL, exist_ok=True)
HOST = "https://" + "github.com/nflverse/nflverse-data/releases/download/"
UA = {"User-Agent": "D503-sports-engine/1.0 (personal picks dashboard)"}
want = [("schedules/games.csv", "games.csv", True)]
for y in range(2015, 2027):
    want += [(f"snap_counts/snap_counts_{y}.csv", f"snap_counts_{y}.csv", y == 2026),
             (f"injuries/injuries_{y}.csv", f"injuries_{y}.csv", y == 2026),
             (f"stats_team/stats_team_week_{y}.csv", f"stw_{y}.csv", y == 2026)]
for src, name, fresh in want:
    p = os.path.join(DL, name)
    if not fresh and not os.path.exists(p) and os.path.exists(os.path.join(OLD, name)):
        shutil.copy(os.path.join(OLD, name), p)
    if os.path.exists(p) and not fresh and os.path.getsize(p) > 10_000:
        continue
    try:
        with urllib.request.urlopen(urllib.request.Request(HOST + src, headers=UA), timeout=120) as r:
            b = r.read()
        open(p, "wb").write(b)
        print(name, len(b))
    except Exception as e:                                   # noqa: BLE001
        print(name, "FAILED", str(e)[:100])
