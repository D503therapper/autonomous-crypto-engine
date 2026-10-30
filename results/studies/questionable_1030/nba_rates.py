"""10/30 QUESTIONABLE PLAYERS - STEP 3: the engine's table. Every man questionable on the 1:30 PM ET report in the
regular season (nba_listings.csv.gz, 2018-19..2025-26) -> data/sports/nba_questionable.json {normalized name:
[times questionable, times played]} (3+ listings only). Read by sports_questionable. Re-run after nba_build.py."""
import csv
import gzip
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
import sports_absences as sa  # noqa: E402
import sports_questionable as sq  # noqa: E402

tot = defaultdict(lambda: [0, 0])
last = {}
for r in csv.DictReader(gzip.open(os.path.join(HERE, "nba_listings.csv.gz"), "rt")):
    if r["stype"] != "2" or r["morning"] != "Questionable":
        continue
    k = sa._nm(r["player"])
    tot[k][0] += 1
    tot[k][1] += int(r["played"])
    last[k] = r["date"]
players = {k: [n, p, last[k]] for k, (n, p) in sorted(tot.items()) if n >= 3}
out = {"_why": "10/30 (Ricky's ask): NBA men questionable on the official 1:30 PM ET report, regular seasons 2018-19.."
               "2025-26, joined to our box scores - [times questionable, times he played, last listed]. "
               f"Usually plays = {sq.USUALLY_N}+ listings and {sq.USUALLY_RATE:.0%}+ played (sports_questionable).",
       "built": "2026-10-30", "players": players}
with open(sq.PATH, "w") as f:
    json.dump(out, f, separators=(",", ":"))
up = sorted((v[1] / v[0], k, v) for k, v in players.items() if v[0] >= sq.USUALLY_N and v[1] / v[0] >= sq.USUALLY_RATE)
print(len(players), "men saved;", len(up), "usually play through it:")
for r, k, v in sorted(up, key=lambda x: -x[2][0]):
    print(f"   {k:28s} {v[1]}/{v[0]} = {r * 100:.0f}%  (last listed {v[2]})")
