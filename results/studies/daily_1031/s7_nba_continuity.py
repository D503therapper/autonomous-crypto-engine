"""Study 7 (10/31): NBA - ROSTER CONTINUITY, THE FIRST 20 GAMES. Never run (the 10/20 roster prior rates WHO is on a
team; this asks whether a team that's mostly NEW - a different rotation from last season - is mispriced early).
Continuity before tonight = the share of the team's minutes so far this season (its finished games, box scores) played
by men who logged minutes for the SAME team last season. Games 3-20 of the team's season (2+ games in), closing
moneylines: dogs +100..+350 and favorites -101..-150, by continuity third (cut points from the train seasons), and the
gap between the two teams (the new-look team vs the same-old team). Train 2017-21 (box scores from 2016), held out
2022 / 2023 / 2024 / 2025 apart, 2026 = now."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

TRAIN, HELD = (2017, 2021), (2022, 2023, 2024, 2025, 2026)


def minutes(st, r):
    try:
        m = float(st.get("minutes") or 0)
    except ValueError:
        return None
    return m if m > 0 else None


box = lib.boxes("nba", minutes)
games = lib.finals("nba")
season_players = defaultdict(set)      # (season, team) -> players with minutes (filled as the season goes)
team_min = defaultdict(lambda: [0.0, 0.0, 0])   # (season, team) -> [returning minutes, all minutes, games]
rows = []
for g in games:
    s = g["season"]
    b = box.get(g["id"])
    st = {}
    for t in (g["home"], g["away"]):
        tm = team_min[(s, t)]
        st[t] = (tm[0] / tm[1] if tm[1] else None, tm[2])
    rows.append((g, st))
    if not b:
        continue
    for t in (g["home"], g["away"]):
        pl = b.get(str(t)) or b.get(t)
        if not pl:
            continue
        last = season_players.get((s - 1, t), set())
        tm = team_min[(s, t)]
        if not last:                                  # no box scores last season -> can't judge (2016 = the first)
            tm[2] += 1
            season_players[(s, t)].update(pl)
            continue
        for pid, m in pl.items():
            tm[1] += m
            if pid in last:
                tm[0] += m
        tm[2] += 1
        season_players[(s, t)].update(pl)

vals = sorted(c for g, st in rows if TRAIN[0] <= g["season"] <= TRAIN[1]
              for t, (c, n) in st.items() if c is not None and 2 <= n <= 19)
lo, hi = vals[len(vals) // 3], vals[2 * len(vals) // 3]
cells = defaultdict(list)
for g, st in rows:
    s = g["season"]
    for side, team, opp, o, won, home in lib.sides(g):
        c, n = st[team]
        oc, on = st[opp]
        if c is None or not (2 <= n <= 19):
            continue
        pr = lib.profit(won, lib.dec(o))
        band = "dog +100..+350" if lib.dog_band(o) else "fav -101..-150" if -150 <= o <= -101 else None
        if not band:
            continue
        cells[f"{band} | games 3-20 (base)"].append((s, pr))
        tag = "LOW continuity (new-look team)" if c <= lo else "HIGH continuity" if c >= hi else "middle"
        cells[f"{band} | {tag}"].append((s, pr))
        if oc is not None and 2 <= on <= 19:
            if c - oc >= 0.25:
                cells[f"{band} | 25+ pts MORE continuity than the opponent"].append((s, pr))
            if oc - c >= 0.25:
                cells[f"{band} | 25+ pts LESS continuity than the opponent"].append((s, pr))
        if n <= 9:
            cells[f"{band} | {tag}, games 3-10"].append((s, pr))
res = {k: lib.summ(v, TRAIN, HELD) for k, v in sorted(cells.items())}
lines = [f"NBA ROSTER CONTINUITY, games 3-20 (cuts from train: low <= {lo:.3f}, high >= {hi:.3f})"]
lines += [lib.fmt(k, v) for k, v in res.items()]
txt = "\n".join(lines)
print(txt)
open(os.path.join(lib.OUT, "s7_out.txt"), "w").write(txt + "\n")
json.dump({"cuts": [lo, hi], "cells": res}, open(os.path.join(lib.OUT, "s7_out.json"), "w"), indent=1)
