"""S1 (part B) - which version of the projected-goalie rule names tonight's starter most often (rested nights / b2b),
2016-22 vs 2023-26. The wired rule (sports_players.projected_starter) vs: the last starter; the #1 unless he sat the
team's last K games in a row (K 2 / 3 / 4 - an injured or benched #1 -> the last starter)."""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402,F401
import sports_players as sp  # noqa: E402

rows = [r for r in sp.load()["nhl"] if r.get("role") == "G"]
act = {(r["gid"], r["team"]): r["player"] for r in rows}
by_team = defaultdict(list)
for r in rows:
    by_team[r["team"]].append(r)
fin = [g for g in lib.finals("nhl") if g["stype"] == "2"]
res = Counter()
for g in fin:
    for side in ("home", "away"):
        team = g[side]
        a = act.get((g["id"], team))
        if not a:
            continue
        trows = [r for r in by_team[team] if r["start"] < g["start"]]
        last = sp.last_starter(trows, team, g["start"])
        rule = sp.projected_starter(trows, team, g["start"])
        if not last:
            continue
        seq = [r["player"] for r in trows if r["start"] >= f"{g['season']}-09-01"][::-1][:10]
        b2b = bool(trows) and sp._hours(trows[-1]["start"], g["start"]) < 36
        k = ("b2b" if b2b else "rest", "2023-26" if g["season"] >= 2023 else "2016-22")
        res[k + ("n",)] += 1
        res[k + ("LAST",)] += last == a
        res[k + ("RULE",)] += rule == a
        for K in (2, 3, 4):
            v = rule
            if not b2b and rule != last and len(seq) >= K and rule not in seq[:K]:
                v = last
            res[k + (f"RULE unless the #1 sat the last {K}",)] += v == a
lines = ["WHO STARTS - the share each version names right (priced regular-season games 2016-26)"]
for night in ("rest", "b2b"):
    for era in ("2016-22", "2023-26"):
        k = (night, era)
        n = res[k + ("n",)]
        lines.append(f"  {night:4s} {era} n {n:5d} " + "  ".join(
            f"{m} {res[k + (m,)] / n * 100:5.1f}%" for m in ("LAST", "RULE", "RULE unless the #1 sat the last 2",
                                                            "RULE unless the #1 sat the last 3", "RULE unless the #1 sat the last 4")))
print("\n".join(lines))
open(os.path.join(HERE, "s1b_out.txt"), "w").write("\n".join(lines) + "\n")
