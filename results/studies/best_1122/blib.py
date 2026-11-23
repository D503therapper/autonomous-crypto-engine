"""11/22 - WHY THE ⭐ HAS LOST - the shared rig. profit_1117's board (money_1117's R3L: the board today's code builds,
every board day 2023-10 -> 2026-11 at the closing price, the live post's shape) with the 11/17 max-profit sizes in (the
short hockey runner-up 2u, the college football thin Lock 1u) - the sizes the board carries today, the ⭐ OFF. Here the ⭐
is a switchable CHOICE (a selector over the day's pool) and a switchable RAISE.
  u0(r)     the play's own size, no ⭐
  POOL[d]   the day's plays the ⭐ may sit on (sports.best_pool: -150..+350, not fighting, the read over the price, never
            the NFL Lock)
  ALL[d]    every unit play of the day
Train = to 2025-06-30, held out = 2025-07-01 -> 2026-10-12, the live weeks apart (the dog score's weights were fit with
these seasons seen - "held out" is the later half, not a clean blind test)."""
import math
import os
import random
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "profit_1117"))
import plib as L  # noqa: E402

M = L.M
D = M.D
half, season, flat = M.half, M.season, M.flat
P = L.P
SZ0 = L.sizes(pieces=["ru2", "cfb_thin"])          # (u0, u with the 11/17 kind-first ⭐ at 1u, star?)
ALL = defaultdict(list)
for _r in P:
    _r["u0"] = SZ0[id(_r)][0]
    ALL[_r["date"]].append(_r)
POOL = {d: [r for r in ps if -150 <= r["odds"] <= 350 and not r.get("fighting") and M.margin(r) > 0
            and not (r["kind"] == "lock" and r["league"] == "nfl")] for d, ps in ALL.items()}
DAYS = sorted(ALL)
NL = [r for r in P if half(r["date"]) != "live"]


def u0(r):
    return r["u0"]


def nv(r):
    """the books' no-vig chance for the side"""
    return r["p_market"] if r.get("p_market") is not None else 1 / r["dec"]


def own_edge(r):
    """the engine's OWN read over the real price, points (edge_own is the read x the price - 1)"""
    e = r.get("edge_own")
    return 100 * ((e + 1) / r["dec"] - 1 / r["dec"]) if e is not None else -99.0


def weighed_over_nv(r):
    """the honest weighed read over the no-vig price, points: a dog = its dog score (the study stack on the no-vig close),
    a favorite = its weighed read minus the no-vig chance"""
    if r["odds"] >= 100 and r.get("dog_score") is not None:
        return r["dog_score"]
    if r.get("w_p") is not None:
        return 100 * (r["w_p"] - nv(r))
    return 100 * (M.read_of(r) - nv(r))


def kind_first(r):
    return (-1 if r["u0"] >= 3 else M.RANK.get(r["kind"], 9), -r["u0"], -M.margin(r))


def size_first(r):
    return (-r["u0"], -M.margin(r), M.RANK.get(r["kind"], 9))


def pick(sel, pool_of=None):
    """-> {date: the ⭐ row} for a selector key (the smallest wins)"""
    out = {}
    for d in DAYS:
        pl = (pool_of or POOL.get)(d)
        if pl:
            out[d] = min(pl, key=sel)
    return out


def st(rs, units=None, pts=0.0):
    """rows -> stats (flat unless units given)"""
    o = {}
    for h in ("train", "held", "live", "all"):
        x = [r for r in rs if (half(r["date"]) == h if h != "all" else half(r["date"]) != "live")]
        n = len(x)
        w = sum(r["result"] == "won" for r in x)
        us = [(units(r) if units else 1.0) for r in x]
        net = sum(u * D.flat(r, pts) for r, u in zip(x, us))
        risk = sum(us)
        bev = sum(1 / r["dec"] for r in x)
        var = sum(1 / r["dec"] * (1 - 1 / r["dec"]) for r in x)
        o[h] = dict(n=n, w=w, net=net, risk=risk, roi=100 * net / risk if risk else 0.0, z=(w - bev) / math.sqrt(var) if var else 0.0)
    seas = defaultdict(float)
    for r in rs:
        if half(r["date"]) != "live":
            seas[season(r["date"])] += (units(r) if units else 1.0) * flat(r)
    o["up"], o["ns"] = sum(v > 0 for v in seas.values()), len(seas)
    o["seas"] = dict(seas)
    return o


def s1(o, h):
    a = o[h]
    return f"{a['w']:3d}-{a['n'] - a['w']:<3d} {a['roi']:+6.1f}%"


def line(name, rs, units=None, w=54):
    o = st(rs, units)
    o1 = st(rs, units, 1.0)
    a = o["all"]
    return (f"  {name:{w}s} {a['w']:4d}-{a['n'] - a['w']:<4d} {a['net']:+7.1f}u on {a['risk']:6.1f}u {a['roi']:+6.1f}% z {a['z']:+5.2f}"
            f" | train {s1(o, 'train')} | HELD {s1(o, 'held')} | up {o['up']}/{o['ns']} | 1pt worse {o1['all']['roi']:+5.1f}%"
            f" | live {o['live']['w']}-{o['live']['n'] - o['live']['w']} {o['live']['net']:+.1f}u")


def placebo_star(mine_rows, draws=2000, seed=1122, pool_of=None, same_days=True):
    """THE PLACEBO: a random play of the day's pool as the ⭐, `draws` times -> how many deals do as well (flat ROI) as the
    ⭐s given, all / train / held. same_days: only the days the ⭐ sat on."""
    days = sorted({r["date"] for r in mine_rows if half(r["date"]) != "live"})
    rnd = random.Random(seed)
    mine = {h: 0.0 for h in ("all", "train", "held")}
    for r in mine_rows:
        h = half(r["date"])
        if h == "live":
            continue
        mine[h] += flat(r)
        mine["all"] += flat(r)
    hit = {h: 0 for h in mine}
    pools = [((pool_of or POOL.get)(d), half(d)) for d in days]
    pools = [([flat(r) for r in pl], h) for pl, h in pools if pl]
    tot_exp = {h: 0.0 for h in mine}
    for fl, h in pools:
        tot_exp[h] += sum(fl) / len(fl)
        tot_exp["all"] += sum(fl) / len(fl)
    for _ in range(draws):
        t = {"all": 0.0, "train": 0.0, "held": 0.0}
        for fl, h in pools:
            v = fl[rnd.randrange(len(fl))]
            t[h] += v
            t["all"] += v
        for h in t:
            hit[h] += t[h] >= mine[h] - 1e-9
    return hit, mine, tot_exp


def worst(per):
    return D.worst(per)


def board(star_of, raise_of):
    """the whole board's money with a ⭐ choice and a raise: star_of = {date: row}, raise_of(r) -> the ⭐'s units (>= its
    own). -> dict net / risk / roi / halves / worst stretch / seasons / the added units' earnings by half."""
    per, seas = defaultdict(float), defaultdict(float)
    t = defaultdict(lambda: [0.0, 0.0])
    add = defaultdict(lambda: [0.0, 0.0, 0])
    stars = set(id(r) for r in star_of.values())
    for r in P:
        u = r["u0"]
        if id(r) in stars:
            u2 = max(u, raise_of(r))
            h = half(r["date"])
            if u2 > u + 1e-9:
                add[h][0] += (u2 - u) * flat(r)
                add[h][1] += u2 - u
                add[h][2] += 1
            u = u2
        h = half(r["date"])
        t[h][0] += u * flat(r)
        t[h][1] += u
        if h != "live":
            per[r["date"]] += u * flat(r)
            seas[season(r["date"])] += u * flat(r)
    net, risk = t["train"][0] + t["held"][0], t["train"][1] + t["held"][1]
    return dict(net=net, risk=risk, roi=100 * net / risk, tr=t["train"], he=t["held"], lv=t["live"], dd=worst(per), seas=dict(seas),
                up=sum(v > 0 for v in seas.values()), ns=len(seas), add=dict(add))


def brow(name, o, base=None, w=54):
    a = o["add"]
    at, ah = a.get("train", [0, 0, 0]), a.get("held", [0, 0, 0])
    s = (f"  {name:{w}s} {o['net'] / L.YEARS:+6.1f}u/yr ROI {o['roi']:+5.1f}% | train {o['tr'][0]:+6.1f}u {M.roi(*o['tr']):+5.1f}%"
         f" | held {o['he'][0]:+6.1f}u {M.roi(*o['he']):+5.1f}% | worst {o['dd']:+6.1f}u | up {o['up']}/{o['ns']}"
         f" | THE RAISE: {at[2] + ah[2]:3d} plays, train {at[0]:+5.1f}u on {at[1]:5.1f}u ({M.roi(at[0], at[1]):+5.1f}%), HELD {ah[0]:+5.1f}u on {ah[1]:5.1f}u ({M.roi(ah[0], ah[1]):+5.1f}%)")
    if base:
        s += f" | worst x{o['dd'] / base['dd']:.2f}"
    return s
