"""S7b - IS THE PACE FADE REAL? The faster team (4+ possessions a game over its last 10) vs the number, re-cut:
a different window (the season to date, 20 games), the open (2023-25) and the morning (2020-22) prices, early vs late
season, home / road, by band, the dose at 3 / 4 / 5 / 6, and the price-free check (does the faster team's margin fall
short of the spread's expectation, in points)."""
import pickle
import os
from collections import defaultdict

import lib

T = lib.build()
# a season-to-date pace (every game before tonight, min 10) from the same box scores, recomputed here
box = lib._box_rows()
team_games = defaultdict(list)       # (team, season) -> [(start, gid, opp)]
for d in T:
    if d["home"]:
        team_games[(d["team"], d["season"])].append((d["start"], d["gid"], d["opp"]))
        team_games[(d["opp"], d["season"])].append((d["start"], d["gid"], d["team"]))
for k in team_games:
    team_games[k].sort()


def game_poss(gid, t, o):
    bt, bo = box.get(gid, {}).get(t), box.get(gid, {}).get(o)
    if not bt or not bo:
        return None
    try:
        return sum(p["fga"] - p["oreb"] + p["to"] + 0.44 * p["fta"] for p in bt + bo) / 2
    except TypeError:
        return None


_cache = {}


def pace_std(team, season, start, window=None):
    key = (team, season, start, window)
    if key in _cache:
        return _cache[key]
    gs = [x for x in team_games[(team, season)] if x[0] < start]
    if window:
        gs = gs[-window:]
    vals = [v for v in (game_poss(gid, team, opp) for _, gid, opp in gs) if v is not None]
    r = sum(vals) / len(vals) if len(vals) >= 10 else None
    _cache[key] = r
    return r


C = lib.Cells()
n = 0
for d in T:
    if d["g"] < 10 or d["o_g"] < 10 or d["pace"] is None or d["o_pace"] is None:
        continue
    n += 1
    s = d["season"]
    kind = "dog" if lib.dog(d) else "fav-150..-101" if lib.fav(d) else "fav big" if d["ml"] < -150 else "dog long"
    gap10 = d["pace"] - d["o_pace"]
    # dose
    for cut in (3, 4, 5, 6):
        if gap10 >= cut:
            C.add(f"1 last-10 pace {cut}+ faster: all [ML close]", s, lib.ml(d))
            C.add(f"1 last-10 pace {cut}+ faster: all [ATS]", s, lib.ats(d))
        if gap10 <= -cut:
            C.add(f"1b last-10 pace {cut}+ slower: all [ML close]", s, lib.ml(d))
    if gap10 >= 4:
        C.add(f"2 last-10 pace 4+ faster, {'early (to Dec)' if d['month'] in (10, 11, 12) else 'late (Jan+)'}: all [ML close]", s, lib.ml(d))
        C.add(f"2 last-10 pace 4+ faster, {'early (to Dec)' if d['month'] in (10, 11, 12) else 'late (Jan+)'}: all [ATS]", s, lib.ats(d))
        C.add(f"2b last-10 pace 4+ faster, {kind} [ML close]", s, lib.ml(d))
        if d.get("dec_open"):
            C.add(f"2c last-10 pace 4+ faster: {kind} [ML open]", s, lib.ml(d, "open"))
            C.add("2c last-10 pace 4+ faster: all [ML open]", s, lib.ml(d, "open"))
        if d.get("m_dec"):
            C.add("2d last-10 pace 4+ faster: all [ML morning]", s, lib.ml(d, "morning"))
        # price-free: the margin vs the spread's expectation, in points
        if d["spread"] is not None:
            C.add("2e last-10 pace 4+ faster: margin minus the market's (pts, 'roi' = points) [pts]", s, d["margin"] + d["spread"])
    if gap10 <= -4 and d["spread"] is not None:
        C.add("2e last-10 pace 4+ slower: margin minus the market's (pts) [pts]", s, d["margin"] + d["spread"])
    if abs(gap10) < 2 and d["spread"] is not None:
        C.add("2e last-10 pace within 2: margin minus the market's (pts) [pts]", s, d["margin"] + d["spread"])
    # other windows
    for w, nm in ((None, "season to date"), (20, "last 20")):
        pt, po = pace_std(d["team"], s, d["start"], w), pace_std(d["opp"], s, d["start"], w)
        if pt is None or po is None:
            continue
        gw = pt - po
        if gw >= 4:
            C.add(f"3 {nm} pace 4+ faster: all [ML close]", s, lib.ml(d))
            C.add(f"3 {nm} pace 4+ faster: all [ATS]", s, lib.ats(d))
            C.add(f"3b {nm} pace 4+ faster: {kind} [ML close]", s, lib.ml(d))
        if gw <= -4:
            C.add(f"3 {nm} pace 4+ slower: all [ML close]", s, lib.ml(d))
    # the faster team's own pace level (is it 'fast' in absolute terms, or just faster than a slow opponent?)
    if gap10 >= 4:
        C.add(f"4 4+ faster, own pace {'top (102+)' if d['pace'] >= 102 else 'not top'}: all [ML close]", s, lib.ml(d))
        C.add(f"4b 4+ faster, {'vs a .500+ opp' if (d['o_wp'] or 0) >= 0.5 else 'vs a sub-.500 opp'}: all [ML close]", s, lib.ml(d))
        C.add(f"4c 4+ faster, we are {'.500+' if (d['wp'] or 0) >= 0.5 else 'sub-.500'}: all [ML close]", s, lib.ml(d))
        C.add(f"4d 4+ faster, {'home' if d['home'] else 'road'}: all [ML close]", s, lib.ml(d))
        C.add(f"4e 4+ faster, slate {'12+' if d['slate'] >= 12 else 'under 12'}: all [ML close]", s, lib.ml(d))
C.dump("s7b", lib.header("S7b THE PACE FADE RE-CUT", n), lib.split)
