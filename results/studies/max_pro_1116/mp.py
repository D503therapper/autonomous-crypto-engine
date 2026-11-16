"""11/16 - FABLE: THE MAX PLAY HUNT (PROS) - the shared rig.

RAW rigs (no board, nothing fit): every NHL / NBA regular-season side at the CLOSING moneyline 2018-26 (the game files),
with what the schedule and the scores said BEFORE the game (rest, back-to-backs, 3 in 4, streaks, form, goal luck, a
walk-forward Elo); the NFL from nflverse's schedule file 2006-26 (ten_1115/nfl_lib). TRAIN = the older half of the
seasons, HELD OUT = the newer half, every season shown apart.

THE BAR for a 2-4u play (the brief): held-out win rate well over the price AND most seasons, a dose, a placebo (2,000
same-size draws from the cell's own pool), a few cents worse, and the count of cells tried. SIZE = a quarter of Kelly on
the LOW end (one standard error under) of the HELD-OUT win rate at the cell's average price, cap 4u (1u = 1% of the roll).
Caches: ~/.cache/d503_maxpro1116 (never the repo)."""
import math
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.expanduser("~/.cache/d503_maxpro1116")
os.makedirs(CACHE, exist_ok=True)
os.environ.setdefault("STUDY_CACHE", CACHE)
sys.path.insert(0, os.path.join(HERE, "..", "daily_1114"))
import lib as D  # noqa: E402

TRIED = []        # every cell printed - the multiple-testing count


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def lday(start):
    """the local (US) calendar day of a start time: UTC - 6h"""
    return (datetime.strptime(start[:16], "%Y-%m-%dT%H:%M") - timedelta(hours=6)).date()


def build(lg):
    """one row a SIDE for every priced regular-season game: the close + the schedule facts known before the game."""
    fin = [g for g in D.finals(lg) if g["stype"] == "2" and not g["neutral"]]
    allf = D.all_finals(lg)
    elo = D.elo_walk(allf, k=6 if lg == "nhl" else 12, hfa=35 if lg == "nhl" else 70)
    tl = defaultdict(list)                     # team -> [(day, gid, home?, gf, ga, season, ot)]
    for g in allf:
        d = lday(g["start"])
        tl[g["home"]].append((d, g["id"], True, g["hs"], g["as"], g["season"], g))
        tl[g["away"]].append((d, g["id"], False, g["as"], g["hs"], g["season"], g))
    idx = {t: {x[1]: i for i, x in enumerate(v)} for t, v in tl.items()}
    ot_of = {}
    for g in fin:
        ls = (g.get("ls_h") or "").split(",")
        ot_of[g["id"]] = len(ls) > (3 if lg == "nhl" else 4)
    rows = []
    for g in fin:
        d = lday(g["start"])
        hw = g["hs"] > g["as"]
        eh, ea = elo.get(g["id"], (1500, 1500))
        f = {}
        for side, team in (("h", g["home"]), ("a", g["away"])):
            i = idx[team].get(g["id"])
            past = [x for x in tl[team][:i] if x[5] == g["season"]] if i is not None else []
            prev = tl[team][i - 1] if i else None
            rest = (d - prev[0]).days if prev else 9
            n4 = sum(1 for x in past if 0 < (d - x[0]).days <= 3)          # games in the 3 nights before
            n6 = sum(1 for x in past if 0 < (d - x[0]).days <= 5)
            st = 0
            for x in reversed(past):
                w = x[3] > x[4]
                if st == 0:
                    st = 1 if w else -1
                elif (st > 0) == w:
                    st += 1 if w else -1
                else:
                    break
            l10 = past[-10:]
            gf, ga = sum(x[3] for x in past), sum(x[4] for x in past)
            wp = sum(x[3] > x[4] for x in past) / len(past) if past else None
            ex = 2.05 if lg == "nhl" else 14
            pyth = gf ** ex / (gf ** ex + ga ** ex) if past and gf + ga > 0 else None
            trip = 0                                                       # straight road games before this one
            for x in reversed(past):
                if x[2]:
                    break
                trip += 1
            stand = 0
            for x in reversed(past):
                if not x[2]:
                    break
                stand += 1
            f[side] = dict(rest=rest, b2b=rest == 1, n4=n4, n6=n6, streak=st, gp=len(past),
                           l10=sum(x[3] > x[4] for x in l10) / len(l10) if len(l10) >= 5 else None,
                           wp=wp, luck=(wp - pyth) if (pyth is not None and len(past) >= 15) else None,
                           prev_m=(prev[3] - prev[4]) if prev and prev[5] == g["season"] else None,
                           prev_home=prev[2] if prev else None, trip=trip, stand=stand,
                           prev_ot=ot_of.get(prev[1]) if prev else None,
                           l5m=sum(x[3] - x[4] for x in past[-5:]) / 5 if len(past) >= 5 else None)
        ph, pa = 1 / dec(g["mlh"]), 1 / dec(g["mla"])
        pe = 1 / (1 + 10 ** (-((eh - ea) + (35 if lg == "nhl" else 70)) / 400))
        for side, o, won, me, op, pnv, pel in (("h", g["mlh"], hw, f["h"], f["a"], ph / (ph + pa), pe),
                                               ("a", g["mla"], not hw, f["a"], f["h"], pa / (ph + pa), 1 - pe)):
            r = dict(lg=lg, gid=g["id"], date=str(d), season=g["season"], home=side == "h", odds=o, dec=dec(o), won=won,
                     prof=(dec(o) - 1) if won else -1.0, p_nv=pnv, p_elo=pel, total=g["total"],
                     team=g["hn"] if side == "h" else g["an"], opp=g["an"] if side == "h" else g["hn"],
                     oo=g["oh"] if side == "h" else g["oa"])
            r.update(me)
            r.update({"o_" + k: v for k, v in op.items()})
            rows.append(r)
    return rows


def split(lg):
    """(train seasons, held seasons)"""
    return ((2018, 2021), (2022, 2026)) if lg in ("nhl", "nba") else ((2006, 2016), (2017, 2026))


def stat(rs, key="prof"):
    n = len(rs)
    if not n:
        return dict(n=0, w=0, roi=0.0, z=0.0, wp=0.0, bev=0.0)
    w = sum(1 for r in rs if r["won"])
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    return dict(n=n, w=w, roi=100 * sum(r[key] for r in rs) / n, z=(w - bev) / math.sqrt(var) if var else 0.0,
                wp=100 * w / n, bev=100 * bev / n)


def cell(name, rs, lg, say=print, key="prof"):
    """ALL / train / held, the seasons up, the win % against the price's break-even."""
    (t0, t1), (h0, h1) = split(lg)
    tr = [r for r in rs if t0 <= r["season"] <= t1]
    he = [r for r in rs if h0 <= r["season"] <= h1]
    a, t, h = stat(tr + he, key), stat(tr, key), stat(he, key)
    seas = defaultdict(list)
    for r in tr + he:
        seas[r["season"]].append(r[key])
    up = sum(1 for v in seas.values() if sum(v) > 0)
    hup = sum(1 for s, v in seas.items() if s >= h0 and sum(v) > 0)
    hn = sum(1 for s in seas if s >= h0)
    TRIED.append(name)
    say(f"  {name:66s} n {a['n']:5d} {a['w']:4d}-{a['n'] - a['w']:<4d} {a['wp']:5.1f}% (needs {a['bev']:4.1f}) {a['roi']:+6.1f}% z {a['z']:+5.2f}"
        f" | train {t['roi']:+6.1f}% ({t['n']:4d}) | held {h['roi']:+6.1f}% ({h['n']:4d}) {h['wp']:4.1f}% z {h['z']:+4.2f}"
        f" | up {up}/{len(seas)} (held {hup}/{hn})")
    return dict(all=a, train=t, held=h, up=up, ns=len(seas), hup=hup, hn=hn)


def placebo(rs, pool, n=2000, seed=7, key="prof"):
    """how many of n random same-size draws from `pool` made as much as rs"""
    if not rs or len(pool) < len(rs):
        return None
    rnd = random.Random(seed)
    tgt = sum(r[key] for r in rs)
    ps = [r[key] for r in pool]
    k = len(rs)
    return sum(1 for _ in range(n) if sum(rnd.sample(ps, k)) >= tgt)


def kelly_units(wp, se, d, cap=4.0):
    """a quarter of Kelly on (wp - se) at decimal price d, in units (1u = 1% of the roll)"""
    p = wp - se
    f = (p * d - 1) / (d - 1)
    return max(0.0, min(cap, 25 * f))


def size_line(rs_held, say=print):
    """the brief's size for a held-out cell"""
    n = len(rs_held)
    if n < 2:
        return 0.0
    wp = sum(r["won"] for r in rs_held) / n
    se = math.sqrt(wp * (1 - wp) / n)
    d = n / sum(1 / r["dec"] for r in rs_held)            # the price whose break-even is the cell's average
    u = kelly_units(wp, se, d)
    u2 = kelly_units(wp, 2 * se, d)
    say(f"      size: held {wp * 100:.1f}% on {n} (se {se * 100:.1f}) at avg dec {d:.3f} -> quarter-Kelly on the low end"
        f" (-1 se) {u:.2f}u, (-2 se) {u2:.2f}u")
    return u


def worse(rs, cents=5):
    """the same rows at a price `cents` worse (american), as [dict] with prof re-graded"""
    out = []
    for r in rs:
        o = r["odds"]
        o2 = o - cents
        if o > 0 and o2 < 100:
            o2 = -100 - (100 - o2)
        d = dec(o2)
        x = dict(r)
        x["dec"], x["prof"] = d, (d - 1) if r["won"] else -1.0
        out.append(x)
    return out
