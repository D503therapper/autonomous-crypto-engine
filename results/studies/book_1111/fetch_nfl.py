"""Download nflverse's public snap-count and injury-report season files (plain public GitHub release downloads - no key,
no login, the default client) into ~/.cache/d503_book1111/dl (never the repo).   python fetch_nfl.py [first] [last]"""
import os
import subprocess
import sys

DL = os.path.join(os.path.expanduser("~"), ".cache", "d503_book1111", "dl")
os.makedirs(DL, exist_ok=True)
lo = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
hi = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
HOST = "https://" + "github.com/nflverse/nflverse-data/releases/download/"
p = os.path.join(DL, "games.csv")                            # every game's result + closing moneylines (the schedules release)
if not (os.path.exists(p) and os.path.getsize(p) > 1_000_000):
    r = subprocess.run(["curl", "-sSL", "-o", p, "-w", "%{http_code} %{size_download}", HOST + "schedules/games.csv"],
                       capture_output=True, text=True)
    print("games", r.stdout, r.stderr[:200])
for kind in ("snap_counts", "injuries"):
    for y in range(lo, hi + 1):
        p = os.path.join(DL, f"{kind}_{y}.csv")
        if os.path.exists(p) and os.path.getsize(p) > 100_000:
            print(kind, y, "have", os.path.getsize(p))
            continue
        r = subprocess.run(["curl", "-sSL", "-o", p, "-w", "%{http_code} %{size_download}", HOST + f"{kind}/{kind}_{y}.csv"],
                           capture_output=True, text=True)
        print(kind, y, r.stdout, r.stderr[:200])
        if not r.stdout.startswith("200"):
            os.remove(p)
