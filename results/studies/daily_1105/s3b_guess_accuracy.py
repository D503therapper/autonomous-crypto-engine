"""S3 (part B) - which morning guess names tonight's goalie more often: the LAST starter (what the engine reads when
the starter is unconfirmed - sports_players.starter_for falls back to it) or the team's #1 (most starts in its last
10 games this season)? And on the 2nd night of a back-to-back, 'the one who did NOT start last night'?
Box scores 2016-26, regular season, every team-game with 3+ prior games this season."""
import csv
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402

act = {(r["gid"], r["team"]): r["player"] for r in csv.DictReader(open("data/sports/players/nhl.csv"))}
allf = [g for g in lib.all_finals("nhl") if g["stype"] == "2"]
tl = lib.team_log(allf)
res = Counter()
for g in allf:
    for team in (g["home"], g["away"]):
        me = act.get((g["id"], team))
        if not me:
            continue
        prev = [x for x in lib.before(tl, team, g["start"], 10) if x["season"] == g["season"]]
        if len(prev) < 3:
            continue
        seq = [act.get((x["id"], team)) for x in prev]
        if None in seq:
            continue
        last = seq[-1]
        n1 = Counter(seq).most_common(1)[0][0]
        b2b = lib.days_between(prev[-1]["start"], g["start"]) < 1.5
        others = [p for p, _ in Counter(seq).most_common() if p != last]
        alt = others[0] if others else last
        k = ("b2b" if b2b else "rest", g["season"] >= 2023)
        res[k + ("n",)] += 1
        res[k + ("last",)] += me == last
        res[k + ("n1",)] += me == n1
        res[k + ("rule",)] += me == (alt if b2b else n1)
lines = ["WHO STARTS TONIGHT - the share each morning guess gets right (era: 2016-22 / 2023-26)"]
for night in ("rest", "b2b"):
    for era in (False, True):
        k = (night, era)
        n = res[k + ("n",)]
        lines.append(f"  {night:4s} {'2023-26' if era else '2016-22'} n {n:6d}  last starter {res[k + ('last',)]/n*100:5.1f}%  "
                     f"#1 (last 10) {res[k + ('n1',)]/n*100:5.1f}%  rule (#1 rested, the other on a b2b) "
                     f"{res[k + ('rule',)]/n*100:5.1f}%")
print("\n".join(lines))
open(os.path.join(HERE, "s3b_out.txt"), "w").write("\n".join(lines) + "\n")
