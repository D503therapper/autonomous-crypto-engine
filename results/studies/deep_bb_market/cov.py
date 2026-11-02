"""Coverage of the fields each deep_bb_market study leans on, per league and season."""
import csv
import glob
import collections
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
for lg in ("ncaab", "nba"):
    c = collections.defaultdict(collections.Counter)
    for f in sorted(glob.glob(os.path.join(ROOT, f"data/sports/games/{lg}/*.csv"))):
        for r in csv.DictReader(open(f)):
            if r["status"] != "final":
                continue
            y, m = int(r["start"][:4]), int(r["start"][5:7])
            s = y if m >= 8 else y - 1
            k = c[s]
            k["n"] += 1
            for fld in ("ml_home", "ml_home_open", "spread_home", "total", "h1_ml_home", "h1_spread_home", "ls_home"):
                if r.get(fld):
                    k[fld] += 1
    print(lg)
    for s in sorted(c):
        print(s, dict(c[s]))
