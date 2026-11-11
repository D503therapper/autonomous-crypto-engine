"""11/11 THE BOOK - the replay board every study here reads: the 10/30 funnel rows (results/studies/thin_1029/
funnel_replay.py: 1,097 board days 2023-10-01 -> 2026-10-12 + the live stretch 10/13-10/29, CLOSING prices, params re-tuned
each July, no injury reports) re-built with the 11/4 builder (plays_every_day_1104/sim_volume.build, version (c15) - the
floor v2 + the NBA floor + the hockey named reason, college hoops out of the general floor, the 10/30 sizing) PLUS the
11/11 wiring a row can carry: NBA ½u dogs only to +199, a value play needs 1 point over its price, the floor's second play
a dog score of 0+. Not replayable here (no rows for them): the ⭐ raise, the 🔍 gap play, the early spots, the college
hoops slot / stack plays, mid-day adds. Train = to 2025-06-30, held out = 2025-07-01 on (the 10/29 split), live apart.
FUNNEL=<folder with fA-fD.jsonl + fLive.jsonl> (54 MB, never committed)."""
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "plays_every_day_1104"))
import sim_volume as sv  # noqa: E402

days, half, season, pnl, gap = sv.days, sv.half, sv.season, sv.pnl, sv.gap
KW = dict(floor_on=True, hk_named=True, floor_leagues=("nhl", "mlb", "nfl"))


def own_margin(r):
    """Points of win chance the own read sits over what the price needs."""
    return None if r.get("edge_own") is None else 100 * r["edge_own"] / r["dec"]


def board(d):
    out, n_before_floor = [], 0
    for r, u, k in sv.build(d, **KW):
        if r["league"] == "nba" and u == 0.5 and r["odds"] > 199 and k in ("nbafloor", "dogplay", "dog", "floorfb", "floor"):
            continue                                         # 11/11 (2): NBA ½u dogs only at +100..+199
        if k == "play" and (own_margin(r) is None or own_margin(r) < 1.0):
            continue                                         # 11/11 (5): a value play needs 1 point over its price
        out.append((r, u, k))
    keep, floors = [], 0
    have = sum(1 for _, _, k in out if k not in ("floor", "floorfb"))
    for r, u, k in out:
        if k in ("floor", "floorfb"):
            if have + floors >= 1 and (r.get("dog_score") or 0) < 0:
                continue                                     # 11/11 (7): the floor's SECOND play needs a dog score 0+
            floors += 1
        keep.append((r, u, k))
    return keep


PLAYS = [(d, r, u, k) for d in days for r, u, k in board(d)]


def flat(r):
    return (r["dec"] - 1) if r["result"] == "won" else -1.0 if r["result"] == "lost" else 0.0


def stat(rs):
    """rs = [(d, r, u)] -> n, W, L, net, risk, flat ROI %, z vs the price."""
    n = len(rs)
    w = sum(r["result"] == "won" for _, r, _ in rs)
    l = sum(r["result"] == "lost" for _, r, _ in rs)
    net = sum(pnl(r, u) for _, r, u in rs)
    risk = sum(u for _, _, u in rs)
    fl = sum(flat(r) for _, r, _ in rs)
    bev = sum(1 / r["dec"] for _, r, _ in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for _, r, _ in rs)
    z = (w - bev) / math.sqrt(var) if var else 0.0
    return dict(n=n, w=w, l=l, net=net, risk=risk, roi=100 * fl / n if n else 0.0, z=z)


def cell(name, rs, live=True):
    """One line: ALL (train + held) then train / held / live flat-1u ROI and the seasons up."""
    tr = [x for x in rs if half(x[0]) == "train"]
    he = [x for x in rs if half(x[0]) == "held"]
    lv = [x for x in rs if half(x[0]) == "live"]
    a, t, h, v = stat(tr + he), stat(tr), stat(he), stat(lv)
    seas = defaultdict(float)
    for d, r, _ in tr + he:
        seas[season(d)] += flat(r)
    up = sum(x > 0 for x in seas.values())
    s = (f"  {name:44s} n {a['n']:4d} {a['w']:3d}-{a['l']:<3d} flat {a['roi']:+6.1f}% z {a['z']:+5.2f} | train {t['roi']:+6.1f}% ({t['n']:3d}) "
         f"| held {h['roi']:+6.1f}% ({h['n']:3d}) | seasons up {up}/{len(seas)}")
    if live:
        s += f" | live {v['w']}-{v['l']} {v['roi']:+.0f}%"
    print(s)
    return a, t, h, up, len(seas)


def worst(per_day, ds):
    cum = peak = w = 0.0
    for d in ds:
        cum += per_day.get(d, 0.0)
        peak = max(peak, cum)
        w = min(w, cum - peak)
    return w


def schedule(name, fn, quiet=False):
    """fn(kind, row, units_today) -> units. Prints train / held / all: units, ROI, worst stretch, seasons up."""
    per_day = defaultdict(float)
    st = defaultdict(lambda: [0, 0, 0.0, 0.0])
    seas = defaultdict(float)
    for d, r, u, k in PLAYS:
        nu = fn(k, r, u)
        if not nu:
            continue
        p = pnl(r, nu)
        h = half(d)
        s = st[h]
        s[0] += r["result"] == "won"
        s[1] += r["result"] == "lost"
        s[2] += p
        s[3] += nu
        if h != "live":
            per_day[d] += p
            seas[season(d)] += p
    tr = [d for d in days if half(d) == "train"]
    he = [d for d in days if half(d) == "held"]
    out = []
    for lab, ds in (("train", tr), ("held", he)):
        w, l, net, risk = st[lab]
        out.append(f"{lab} {net:+6.1f}u/{risk:4.0f}u {100 * net / risk if risk else 0:+5.1f}% worst {worst(per_day, ds):+5.1f}")
    net = st["train"][2] + st["held"][2]
    risk = st["train"][3] + st["held"][3]
    dd = worst(per_day, tr + he)
    up = sum(v > 0 for v in seas.values())
    lv = st["live"]
    if not quiet:
        print(f"  {name:62s} | " + " | ".join(out) + f" | ALL {net:+6.1f}u/{risk:4.0f}u {100 * net / risk if risk else 0:+5.1f}% worst {dd:+5.1f} "
              f"up {up}/{len(seas)} u/worst {net / -dd if dd else 0:4.1f} | live {lv[0]}-{lv[1]} {lv[2]:+5.1f}u")
    return dict(net=net, risk=risk, dd=dd, up=up, train=st["train"][2], held=st["held"][2],
                dd_tr=worst(per_day, tr), dd_he=worst(per_day, he))
