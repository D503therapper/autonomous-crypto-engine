"""S3 - NFL QB MATCHUPS BY RECENT FORM (data/sports/players/nfl.csv 2016-26: every QB line; tonight's starter = the
man with the most attempts in tonight's box - known by kickoff; his form = adjusted yards an attempt
(yds + 20 TD - 45 INT) / att over his LAST 3 games, 60+ attempts, against his own longer run (the 12 before) and
against the QB across). ESPN's close at its own juice, engine bands. Train 2016-21 / held 2022-26."""
import csv
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import lib2  # noqa: E402
import h  # noqa: E402

O = h.Out("s3_nfl_qb", lib2.TRAIN, lib2.HELD)
rows = lib2.rows("nfl")
qb = defaultdict(list)          # gid -> [(team, player, att, yds, td, int)]
for r in csv.DictReader(open(os.path.join(lib.ROOT, "data", "sports", "players", "nfl.csv"))):
    if r["role"] != "QB":
        continue
    try:
        qb[r["gid"]].append((r["team"], r["player"], float(r["att"] or 0), float(r["yds"] or 0), float(r["td"] or 0), float(r["int"] or 0), r["start"]))
    except ValueError:
        continue
plog = defaultdict(list)        # player -> [(start, att, yds, td, int)]
for gid, v in qb.items():
    for t, p, a, y, td, it, st in v:
        plog[p].append((st, a, y, td, it))
for p in plog:
    plog[p].sort()


def aya(games):
    a = sum(g[1] for g in games)
    return None if a < 1 else (sum(g[2] for g in games) + 20 * sum(g[3] for g in games) - 45 * sum(g[4] for g in games)) / a


def form(player, start):
    lg = [g for g in plog[player] if g[0] < start]
    l3, base = lg[-3:], lg[-15:-3]
    f3 = aya(l3) if sum(g[1] for g in l3) >= 60 and len(l3) == 3 else None
    fb = aya(base) if sum(g[1] for g in base) >= 150 else None
    return f3, fb, len(lg)


def starter(gid, team):
    v = [x for x in qb.get(gid, []) if str(x[0]) == str(team)]
    return max(v, key=lambda x: x[2])[1] if v else None


byg = defaultdict(dict)
for r in rows:
    byg[r["id"]][r["side"]] = r
n = 0
for gid, d in byg.items():
    if len(d) != 2:
        continue
    for side, other in (("home", "away"), ("away", "home")):
        r, o = d[side], d[other]
        me, op = starter(gid, r["team"]), starter(gid, o["team"])
        if not me or not op:
            continue
        f3, fb, ng = form(me, r["start"])
        o3, ob, ong = form(op, r["start"])
        b = h.band(r["odds"])
        if not b:
            continue
        n += 1
        pr = lib2.ml_profit(r)
        s = r["season"]
        O.add(f"{b} ALL", s, pr)
        O.add(f"{b} {'home' if r['home'] else 'road'}", s, pr)
        if f3 is not None and o3 is not None:
            d3 = f3 - o3
            k = "QB form 2+ better" if d3 >= 2 else "QB form 0..2 better" if d3 >= 0 else "QB form 0..2 worse" if d3 > -2 else "QB form 2+ worse"
            O.add(f"{b} {k}", s, pr)
            if d3 >= 3.5:
                O.add(f"{b} QB form 3.5+ better", s, pr)
            if d3 <= -3.5:
                O.add(f"{b} QB form 3.5+ worse", s, pr)
        if f3 is not None:
            k = "own QB hot (L3 9+)" if f3 >= 9 else "own QB cold (L3 under 5.5)" if f3 < 5.5 else "own QB middle"
            O.add(f"{b} {k}", s, pr)
            if fb is not None:
                dd = f3 - fb
                k = "own QB 2+ over his run" if dd >= 2 else "own QB 2+ under his run" if dd <= -2 else "own QB at his run"
                O.add(f"{b} {k}", s, pr)
        if o3 is not None:
            k = "opp QB hot (L3 9+)" if o3 >= 9 else "opp QB cold (L3 under 5.5)" if o3 < 5.5 else "opp QB middle"
            O.add(f"{b} {k}", s, pr)
            if ob is not None:
                dd = o3 - ob
                k = "opp QB 2+ over his run" if dd >= 2 else "opp QB 2+ under his run" if dd <= -2 else "opp QB at his run"
                O.add(f"{b} {k}", s, pr)
        if fb is not None and ob is not None:
            db = fb - ob
            k = "QB long run 1.5+ better" if db >= 1.5 else "QB long run 1.5+ worse" if db <= -1.5 else "QB long run close"
            O.add(f"{b} {k}", s, pr)
        if ng < 4:
            O.add(f"{b} own QB green (under 4 games on file)", s, pr)
        if ong < 4:
            O.add(f"{b} opp QB green (under 4 games on file)", s, pr)
O.p(f"band sides with both starters named: {n}")
O.show()
for nm, pool in (("dog QB form 2+ better", "dog ALL"), ("dog QB form 2+ worse", "dog ALL"), ("dog opp QB 2+ over his run", "dog ALL"),
                 ("dog own QB 2+ under his run", "dog ALL"), ("fav own QB 2+ over his run", "fav ALL"), ("fav QB form 2+ better", "fav ALL")):
    O.placebo(nm, pool)
O.save()
