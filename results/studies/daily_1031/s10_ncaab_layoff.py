"""Study 10 (10/31, college hoops prep - the season opens ~11/3): THE EXAM-BREAK LAYOFF. Every December college teams
stop for finals - some sit 7-12 days, some keep playing. Never run for college hoops (NHL rest / rust was hockey only;
the 10/30 November study was the first 3 games / road favorites).
A side whose last game was 7+ days ago (rust) vs an opponent that played within the last 4 days (in rhythm), and the
reverse; December (12/5-1/5) is the exam window, the rest of the season (games 4+) the control. Closing moneylines:
dogs +100..+350, favorites -101..-150, and ATS. Every day count from the game files (a team's games on file - D-I vs
D-I; a non-D-I game in between would hide, so the layoff is an upper bound). Train 2018-21, held out 2022 / 2023 /
2024 / 2025 apart."""
import json, os, sys
from collections import defaultdict
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2018, 2021), (2022, 2023, 2024, 2025)


def day(start):
    return (datetime.fromisoformat(start.replace("Z", "+00:00")) - timedelta(hours=5)).date()


last, ngames = {}, defaultdict(int)
cells = defaultdict(list)
for g in lib.finals("ncaab"):
    d = day(g["start"])
    s = g["season"]
    rest = {}
    for t in (g["home"], g["away"]):
        rest[t] = (d - last[(s, t)]).days if (s, t) in last else None
    md = (d.month, d.day)
    dec = (md >= (12, 5)) or (md <= (1, 5))
    for side, team, opp, o, won, home in lib.sides(g):
        r, ro = rest[team], rest[opp]
        if r is None or ro is None or ngames[(s, team)] < 3 or ngames[(s, opp)] < 3:
            continue
        band = "dog +100..+350" if lib.dog_band(o) else "fav -101..-150" if -150 <= o <= -101 else None
        win = "Dec exam window" if dec else "rest of season"
        tags = ["base"]
        if r >= 7 and ro <= 4:
            tags.append("7+ days off vs a team that played within 4")
        if r >= 10 and ro <= 4:
            tags.append("10+ days off vs a team that played within 4")
        if r <= 4 and ro >= 7:
            tags.append("in rhythm (<=4) vs a team off 7+")
        if r >= 7 and ro >= 7:
            tags.append("both off 7+")
        pr = lib.profit(won, lib.dec(o))
        a = lib.ats(g, side)
        for tg in tags:
            if band:
                cells[f"{win} | {band} | {tg}"].append((s, pr))
            if a is not None:
                cells[f"{win} | ATS | {tg}"].append((s, a))
    for t in (g["home"], g["away"]):
        last[(s, t)] = d
        ngames[(s, t)] += 1
res = {k: lib.summ(v, TRAIN, HELD) for k, v in sorted(cells.items())}
lines = ["COLLEGE HOOPS - THE LAYOFF (exam break), games 4+ for both teams"]
lines += [lib.fmt(k, v) for k, v in res.items()]
txt = "\n".join(lines)
print(txt)
open(os.path.join(lib.OUT, "s10_out.txt"), "w").write(txt + "\n")
json.dump(res, open(os.path.join(lib.OUT, "s10_out.json"), "w"), indent=1)
