"""S3 - NHL: THE MORNING GOALIE GUESS vs WHO ACTUALLY STARTS (the 8 AM board usually reads 'unconfirmed' and leans on
the team's LAST starter). Box scores 2016-26 (data/sports/players/nhl.csv - one goalie row a team-game = the starter).
LAST = the goalie who started the team's previous game this season; #1 = the most starts in the team's last 10 games
this season (6+ played). SWITCH = tonight's starter is not the last starter.
  (a) how often the last starter is wrong (all / on the 2nd night of a back-to-back / not);
  (b) the side whose goalie switched, at the OPEN (game file ml_*_open - the nearest thing on file to the 8 AM price,
      before most confirmations) and at the CLOSE, dogs +100..+350 / favorites -101..-200, split: #1 -> backup
      (the starter we'd have read is benched) and backup -> #1 (the #1 comes back);
  (c) the open -> close move on those sides (does the market find out after the morning?).
Train 2016-21 seasons, held out 2022 / 2023 / 2024 / 2025 / 2026 apart."""
import csv
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402

act = {(r["gid"], r["team"]): r["player"] for r in csv.DictReader(open("data/sports/players/nhl.csv"))}
fin = [g for g in lib.finals("nhl") if g["stype"] == "2"]
allf = [g for g in lib.all_finals("nhl") if g["stype"] == "2"]
tl = lib.team_log(allf)
C = lib.Cells()
freq = Counter()
moves = {}
for g in fin:
    for side, team, opp, o_close, won, home in lib.sides(g):
        me = act.get((g["id"], team))
        if not me:
            continue
        prev = lib.before(tl, team, g["start"], 10)
        prev = [x for x in prev if x["season"] == g["season"]]
        if not prev:
            continue
        last = act.get((prev[-1]["id"], team))
        if not last:
            continue
        b2b = lib.days_between(prev[-1]["start"], g["start"]) < 1.5
        n1 = None
        if len(prev) >= 6:
            cnt = Counter(act.get((x["id"], team)) for x in prev)
            n1 = cnt.most_common(1)[0][0]
        switch = me != last
        freq[("all", switch)] += 1
        freq[("b2b" if b2b else "rest", switch)] += 1
        kind = "same" if not switch else ("#1->backup" if n1 and last == n1 else
                                         "backup->#1" if n1 and me == n1 else "other switch")
        o_open = g["oh"] if side == "home" else g["oa"]
        s = g["season"]
        for tag, o in (("close", o_close), ("open", o_open)):
            if not o:
                continue
            p = lib.profit(won, lib.dec(o))
            band = "dog" if lib.dog_band(o) else "fav" if lib.fav_band(o, -200, -101) else None
            if not band:
                continue
            C.add(f"{tag} {band} {kind}", s, p)
            C.add(f"{tag} {band} {kind} {'b2b' if b2b else 'rest'}", s, p)
            if switch:
                C.add(f"{tag} {band} ANY switch", s, p)
        if o_open and o_close and (lib.dog_band(o_open) or lib.fav_band(o_open, -200, -101)):
            pc = 1 / lib.dec(o_close)
            po = 1 / lib.dec(o_open)
            moves.setdefault(kind + (" b2b" if b2b else " rest"), []).append(100 * (pc - po))
lines = ["(a) HOW OFTEN THE LAST STARTER IS WRONG (regular season, priced games, team-games with a last start this season)"]
for k in ("all", "b2b", "rest"):
    n = freq[(k, True)] + freq[(k, False)]
    lines.append(f"  {k:5s} {freq[(k, True)]:6d} of {n:6d} = {freq[(k, True)]/n*100:.1f}% switched")
lines.append("(c) the open -> close move (implied-% points, + = the market moved TOWARD the side) by kind")
for k, v in sorted(moves.items()):
    lines.append(f"  {k:24s} n {len(v):6d} mean {sum(v)/len(v):+.2f}")
print("\n".join(lines))
open(os.path.join(HERE, "s3_freq.txt"), "w").write("\n".join(lines) + "\n")
C.dump("s3", "(b) THE SIDE WHOSE GOALIE SWITCHED vs THE SAME STARTER - ML at the open / the close", (2016, 2021),
       [2022, 2023, 2024, 2025, 2026])
