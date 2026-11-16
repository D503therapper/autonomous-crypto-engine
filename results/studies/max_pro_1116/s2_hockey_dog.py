"""11/16 MAX PLAY HUNT - S2: THE HOCKEY DOG OF THE DAY, EVERY ONE ON FILE (2020-26), AND WHAT STACKS ON IT.
The hockey Dog is the engine's best-holding kind (+13.6% on the 2020-23 paid-odds rig, +15.6% / +10.8% on the boards).
Is there a sub-spot of it - several things agreeing - that wins enough MORE to carry 3-4u?
  OOS   the 11/2 NHL odds-history rig, 2020-23, the live Dog one a day at the MORNING price (nhl_odds_1102)
  R1/R2 the two replay boards 2023-26 (sizing_1114/lib), the schedule facts joined from the raw rig (mp.build)
"Old" half = 2020-23 (OOS), "new" half = 2023-26 (the board). A cell has to win more than the other Dogs in BOTH.
Usage: python results/studies/max_pro_1116/s2_hockey_dog.py > results/studies/max_pro_1116/s2_hockey_dog.out"""
import contextlib
import importlib.util
import io
import math
import os
import random
import sys
from collections import defaultdict

import mp

HERE = os.path.dirname(os.path.abspath(__file__))
STUD = os.path.dirname(HERE)
RAW = {(r["date"], r["team"]): r for r in mp.build("nhl")}

sys.path.insert(0, os.path.join(STUD, "sizing_1114"))
_d = sys.modules.pop("lib")                    # daily_1114's lib (mp's) - sizing_1114 has its own lib.py
import lib as L  # noqa: E402
BO = L.boards()
sys.modules.pop("lib")
NH = os.path.join(STUD, "nhl_odds_1102")
sys.path.insert(0, NH)
with contextlib.redirect_stdout(io.StringIO()):
    spec = importlib.util.spec_from_file_location("s1h", os.path.join(NH, "s1_hockey_dog.py"))
    s1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s1)
sys.modules["lib"] = _d


def raw_of(date, team):
    for dd in (date,):
        r = RAW.get((dd, team))
        if r:
            return r
    return None


def from_board(name, kinds=("dog",)):
    out = []
    bd, _ = BO[name]
    miss = 0
    for d in sorted(bd):
        if L.half(d) == "live":
            continue
        for r, u, k in bd[d]:
            if k not in kinds or r["league"] != "nhl" or r["result"] not in ("won", "lost"):
                continue
            w = raw_of(d, r["team"])
            if not w:
                miss += 1
                continue
            out.append(dict(src=name, date=d, season=L.season(d), odds=r["odds"], dec=r["dec"], won=r["result"] == "won",
                            prof=(r["dec"] - 1) if r["result"] == "won" else -1.0, score=r["dog_score"], gap=r["own_gap"],
                            home=r["home"], rb=w["o_b2b"] and not w["b2b"], o_road=w["o_prev_home"] is False,
                            stk=w["streak"], ostk=w["o_streak"], rest=w["rest"], o_n4=w["o_n4"], luck=w["luck"],
                            kind=k, half="new"))
    return out, miss


def from_oos():
    out = []
    bd = s1.cands("morning")
    for day, xs in sorted(bd.items()):
        x, kind = s1.pick(xs)
        if not x:
            continue
        w = raw_of(day, x["team"]) or raw_of(day, x["r"].get("home_name") if x["home"] else x["r"].get("away_name"))
        out.append(dict(src="OOS", date=day, season=x["r"]["season"], odds=x["am"], dec=x["dec"], won=bool(x["won"]),
                        prof=x["profit"], score=x["score"], gap=x["gap"], home=x["home"], rb=x["ob2b"] and not x["b2b"],
                        o_road=(w["o_prev_home"] is False) if w else None, stk=x["stk"], ostk=x["ostk"], rest=x["rest"],
                        o_n4=w["o_n4"] if w else None, luck=w["luck"] if w else None, kind=kind, half="old"))
    return out


def st(rs):
    n = len(rs)
    if not n:
        return "n   0"
    w = sum(r["won"] for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    return f"n {n:3d} {w:3d}-{n - w:<3d} {100 * w / n:4.1f}% (needs {100 * bev / n:4.1f}) {100 * sum(r['prof'] for r in rs) / n:+6.1f}% z {(w - bev) / math.sqrt(var):+4.2f}"


NCELL = [0]


def cell(name, pool, f):
    NCELL[0] += 1
    sel = [r for r in pool if f(r)]
    rest = [r for r in pool if not f(r)]
    o, n = [r for r in sel if r["half"] == "old"], [r for r in sel if r["half"] == "new"]
    seas = defaultdict(float)
    for r in sel:
        seas[r["season"]] += r["prof"]
    up = sum(v > 0 for v in seas.values())
    rnd = random.Random(7)
    ps = [r["prof"] for r in pool]
    tgt = sum(r["prof"] for r in sel)
    pl = sum(1 for _ in range(2000) if sum(rnd.sample(ps, len(sel))) >= tgt) if 0 < len(sel) < len(pool) else -1
    print(f"  {name:58s} {st(sel)} | 2020-23 {st(o)[:40]} | 2023-26 {st(n)[:40]} | up {up}/{len(seas)} | placebo {pl}/2000 | the rest {st(rest)[36:]}")
    return sel


oos = from_oos()
for bname in ("R1", "R2"):
    b, miss = from_board(bname)
    pool = oos + b
    print(f"\n================ EVERY HOCKEY DOG OF THE DAY: OOS 2020-23 ({len(oos)}) + board {bname} 2023-26 ({len(b)}; {miss} unmatched) ================")
    print(f"  ALL                                                        {st(pool)} | 2020-23 {st(oos)[:40]} | 2023-26 {st(b)[:40]}")
    short = [r for r in pool if r["odds"] <= 150]
    print(f"  short +100..+150 (the 2u Dog)                              {st(short)}")
    print(" -- on EVERY Dog")
    cell("H5 dog score 8+", pool, lambda r: r["score"] >= 8)
    cell("H5 dog score 10+", pool, lambda r: r["score"] >= 10)
    cell("H6 rested vs a favorite on a b2b", pool, lambda r: r["rb"])
    cell("H7 at home", pool, lambda r: r["home"])
    cell("H8 +120..+150", pool, lambda r: 120 <= r["odds"] <= 150)
    cell("H9 own read 1+ over the market", pool, lambda r: r["gap"] >= 1)
    print(" -- inside the SHORT Dog (+100..+150, today's 2u): does anything earn 3-4u")
    cell("H5s dog score 8+", short, lambda r: r["score"] >= 8)
    cell("H6s rested vs a b2b favorite", short, lambda r: r["rb"])
    cell("H6s ... the favorite on the ROAD last night", short, lambda r: r["rb"] and r["o_road"])
    cell("H6s ... and the dog at home", short, lambda r: r["rb"] and r["home"])
    cell("H7s at home", short, lambda r: r["home"])
    cell("H10s the dog NOT on a b2b edge (no schedule spot)", short, lambda r: not r["rb"])
    cell("H11s the favorite hot (3+ straight wins)", short, lambda r: r["ostk"] >= 3)
    cell("H12s the dog cold (2+ straight losses)", short, lambda r: r["stk"] <= -2)
    cell("H13s the dog rested 2+ days", short, lambda r: r["rest"] >= 2)

    def cnt(r):
        return (r["score"] >= 8) + bool(r["rb"]) + bool(r["home"]) + (r["odds"] >= 120) + (r["stk"] <= -1) + (r["ostk"] >= 2)
    print(" -- H14s THE CONFLUENCE COUNT on the short Dog (score 8+, b2b edge, home, +120 up, dog off a loss, favorite off 2+ wins)")
    for k in range(0, 6):
        cell(f"H14s count == {k}", short, lambda r, k=k: cnt(r) == k)
    for k in (3, 4):
        sel = cell(f"H14s count >= {k}", short, lambda r, k=k: cnt(r) >= k)
        new = [r for r in sel if r["half"] == "new"]
        old = [r for r in sel if r["half"] == "old"]
        for nm, h in (("2020-23", old), ("2023-26", new)):
            if len(h) > 5:
                wp = sum(r["won"] for r in h) / len(h)
                se = math.sqrt(wp * (1 - wp) / len(h))
                d = len(h) / sum(1 / r["dec"] for r in h)
                print(f"       {nm}: {wp * 100:.1f}% on {len(h)} at avg dec {d:.2f} -> quarter-Kelly on the low end (-1 se) {mp.kelly_units(wp, se, d):.2f}u, (-2 se) {mp.kelly_units(wp, 2 * se, d):.2f}u")
    # the size the plain short Dog earns by the brief's formula (the scale for everything above)
    for nm, h in (("2020-23", [r for r in short if r["half"] == "old"]), ("2023-26", [r for r in short if r["half"] == "new"]), ("all", short)):
        wp = sum(r["won"] for r in h) / len(h)
        se = math.sqrt(wp * (1 - wp) / len(h))
        d = len(h) / sum(1 / r["dec"] for r in h)
        print(f"  THE PLAIN SHORT DOG's size by the brief's formula, {nm}: {wp * 100:.1f}% on {len(h)} at avg dec {d:.2f} -> (-1 se) {mp.kelly_units(wp, se, d):.2f}u, (-2 se) {mp.kelly_units(wp, 2 * se, d):.2f}u")
print(f"\ncells: {NCELL[0]}")
