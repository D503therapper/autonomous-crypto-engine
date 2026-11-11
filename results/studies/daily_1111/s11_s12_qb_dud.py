"""S11 (NFL) / S12 (college football) - THE QB OFF A DUD (never studied: 'completion' appears nowhere in
SPORTS_FINDINGS; the 11/4 interception luck read the SEASON's INT margin, the 11/8 star-off-a-dud is NBA / college
hoops; the QB studies read who starts, never how the starter played).
The team's starting QB (data/sports/players/<lg>.csv - the QB row per team-game, 2016-26) had an ugly LAST game:
DUD = completed under 50% on 15+ attempts, or threw 3+ interceptions; the 'dud dose' = both, or under 40%. The public
sees the box score - is the next price too short on them (fade the dud team's opponent) or too long (buy the bounce)?
Only when the same QB is the team's last two starters (his dud, not a backup's mop-up). Control = a QB with a clean
last game (55%+ and 0-1 INT). Cells: dud team as a favorite -101..-250 / dog +100..+350 at the close, ATS, and the
first FAIR number of the paid odds history (2020-26) as the second price.
TRAIN 2016-21, HELD 2022 / 2023 / 2024 / 2025 apart, 2026 live."""
import csv
import sys
from collections import defaultdict

import lib

LG = sys.argv[1] if len(sys.argv) > 1 else "nfl"
TAG = {"nfl": "s11", "ncaaf": "s12"}[LG]
fin = [g for g in lib.finals(LG) if g["stype"] == "2"]
allf = [g for g in lib.all_finals(LG) if g["stype"] == "2"]
hist = {x["id"]: x for x in lib.load_football(LG)}
qb = {}
with open(lib.os.path.join(lib.sd.DATA, "players", f"{LG}.csv")) as f:
    for r in csv.DictReader(f):
        if r["role"] != "QB":
            continue
        att, cmp_, it = lib.num(r["att"]), lib.num(r["cmp"]), lib.num(r["int"])
        if att is None or cmp_ is None:
            continue
        k = (r["gid"], r["team"])
        if k not in qb or att > qb[k]["att"]:
            qb[k] = {"p": r["player"], "att": att, "cmp": cmp_, "int": it or 0}
tl = lib.team_log(allf)
cells = lib.Cells()
for g in fin:
    for side, team, opp, o, won, home in lib.sides(g):
        prev = lib.before(tl, team, g["start"], 2)
        if len(prev) < 2 or prev[-1]["season"] != g["season"]:
            continue
        last, prior = qb.get((prev[-1]["id"], team)), qb.get((prev[-2]["id"], team))
        if not last or not prior or last["p"] != prior["p"]:
            continue
        pct = last["cmp"] / last["att"] if last["att"] else None
        if pct is None:
            continue
        labs = []
        low = last["att"] >= 15 and pct < 0.5
        ints = last["int"] >= 3
        if low or ints:
            labs.append("DUD (under 50% on 15+ or 3+ INT)")
        if low:
            labs.append("DUD: under 50% on 15+")
        if ints:
            labs.append("DUD: 3+ INT")
        if (low and ints) or (last["att"] >= 15 and pct < 0.4):
            labs.append("DUD dose: both, or under 40%")
        if last["att"] >= 15 and pct >= 0.55 and last["int"] <= 1:
            labs.append("control: clean last game (55%+, 0-1 INT)")
        won_last = lib.won_g(prev[-1], team)
        if low or ints:
            labs.append(f"DUD and {'WON' if won_last else 'LOST'} last game")
        s = g["season"]
        pl = lib.profit(won, lib.dec(o))
        a = lib.ats(g, side)
        ep = lib.early_price(hist, g["id"], side)
        for lab in labs:
            if -250 <= o <= -101:
                cells.add(f"{lab} | FAV ML", s, pl)
                if ep and -250 <= ep[0] <= -101:
                    cells.add(f"{lab} | FAV ML first fair", s, lib.profit(won, ep[1]))
            if lib.dog_band(o):
                cells.add(f"{lab} | DOG ML", s, pl)
                if ep and lib.dog_band(ep[0]):
                    cells.add(f"{lab} | DOG ML first fair", s, lib.profit(won, ep[1]))
            cells.add(f"{lab} | ATS", s, a)
cells.dump(TAG, f"{TAG.upper()} {LG} - the starting QB off a dud (under 50% on 15+ / 3+ INT), same QB both games; close / "
           f"ATS / first fair; TRAIN 2016-21", (2016, 2021), (2022, 2023, 2024, 2025, 2026))
