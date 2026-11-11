"""Download nflverse's public play-by-play season files (plain public release downloads - no key, no login, the
default client) into ~/.cache/d503_spreads1111/dl (never the repo).   python fetch_pbp.py [first] [last]"""
import os
import subprocess
import sys

DL = os.path.join(os.path.expanduser("~"), ".cache", "d503_spreads1111", "dl")
os.makedirs(DL, exist_ok=True)
lo = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
hi = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
HOST = "https://" + "github.com/nflverse/nflverse-data/releases/download/pbp/"
for y in range(lo, hi + 1):
    p = os.path.join(DL, f"pbp_{y}.csv.gz")
    if os.path.exists(p) and os.path.getsize(p) > 1_000_000:
        print(y, "have", os.path.getsize(p))
        continue
    r = subprocess.run(["curl", "-sSL", "-o", p, "-w", "%{http_code} %{size_download}",
                        HOST + "play_by_play_%d.csv.gz" % y], capture_output=True, text=True)
    print(y, r.stdout, r.stderr[:200])
