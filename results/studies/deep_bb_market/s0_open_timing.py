"""S0 - WHEN does a college hoops / NBA price first show in OUR feed (data/sports/line_history, 2026), and does
ESPN's recorded open match that first look? (The open studies assume we can bet near ESPN's open.)"""
import json
import os
from collections import defaultdict
from datetime import datetime

import lib

out = lib.Out("s0_open_timing")
first = {}
for fn in ("2026-10.jsonl", "2026-11.jsonl"):
    p = os.path.join(lib.ROOT, "data/sports/line_history", fn)
    for line in open(p):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        g = d.get("g", "")
        if not (g.startswith("ncaab") or g.startswith("nba")):
            continue
        if g not in first or d["t"] < first[g]["t"]:
            first[g] = d


def t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


G = {**lib.raw_games("ncaab"), **lib.raw_games("nba")}
for lg in ("ncaab", "nba"):
    hrs, match = [], []
    for g, d in first.items():
        if not g.startswith(lg):
            continue
        hrs.append((t(d["s"]) - t(d["t"])).total_seconds() / 3600)
        r = G.get(g)
        if r and r.get("ml_home_open") and d.get("h"):
            match.append(abs(lib.nv(float(r["ml_home_open"]), float(r["ml_away_open"])) - lib.nv(d["h"], d["a"])))
    hrs.sort()
    if hrs:
        q = lambda f: hrs[int(f * (len(hrs) - 1))]
        out.note(f"{lg}: {len(hrs)} games first seen; hours before tip: min {hrs[0]:.1f} p25 {q(.25):.1f} median {q(.5):.1f}"
                 f" p75 {q(.75):.1f} max {hrs[-1]:.1f}")
    if match:
        match.sort()
        out.note(f"{lg}: our first look vs ESPN's recorded open, |no-vig gap|: median {match[len(match)//2]*100:.1f} pts, "
                 f"under 1 pt {sum(m < .01 for m in match)/len(match):.0%} of {len(match)}")
out.save()
