"""When is ESPN's college hoops OPEN on the board? Our own hourly line history (data/sports/line_history, 2026-10/11):
first time we saw each ncaab game's moneyline vs its tip, and whether that first price = the games file's ml_*_open."""
import csv
import glob
import json
import os
from datetime import datetime

import lib


def ts(x):
    return datetime.strptime(x[:16], "%Y-%m-%dT%H:%M")


first = {}
for fn in sorted(glob.glob(os.path.join(lib.ROOT, "data/sports/line_history/*.jsonl"))):
    for line in open(fn):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not d.get("g", "").startswith("ncaab:") or d.get("h") is None:
            continue
        if d["g"] not in first or d["t"] < first[d["g"]]["t"]:
            first[d["g"]] = d
opens = {}
for fn in sorted(glob.glob(os.path.join(lib.ROOT, "data/sports/games/ncaab/2026-*.csv"))):
    for r in csv.DictReader(open(fn)):
        opens[r["id"]] = (r["ml_home_open"], r["ml_away_open"], r["ml_home"], r["ml_away"], r["start"])
lead = []
same = 0
n = 0
for gid, d in first.items():
    h = (ts(d["s"]) - ts(d["t"])).total_seconds() / 3600
    lead.append(h)
    o = opens.get(gid)
    if o and o[0]:
        n += 1
        same += str(d["h"]) == str(int(float(o[0])))
lead.sort()
print(f"ncaab games in our line history: {len(first)}; hours from our FIRST look to tip: "
      f"min {lead[0]:.0f} / 25% {lead[len(lead) // 4]:.0f} / median {lead[len(lead) // 2]:.0f} / 75% {lead[3 * len(lead) // 4]:.0f}")
print(f"first look = the file's ESPN open on {same} of {n} games with an open on file")
