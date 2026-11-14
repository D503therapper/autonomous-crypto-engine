"""11/14 - SIZING + THE ⭐ STUDY: the two replay boards every script here reads.

R1  the 10/30 funnel rows (results/studies/thin_1029/funnel_replay.py on the 10/30 code: 1,097 board days 2023-10-01 ->
    2026-10-12 + the live stretch 10/13-10/29, CLOSING prices, params re-tuned each July, no injury reports) through
    the 11/11 book study's board (book_1111/blib.board - the floor v2, the NBA floor, the hockey named reason, the 10/30
    sizing, the 11/11 wiring) - the board the 11/11 and 11/12 sizing studies judged on.
R2  the 11/12 deep program's rows on TODAY's code (results/studies/deep_1112/funnel2.py ARM=new: the honest blend dials,
    the FBS fit; 2023-10-01 -> 2026-11-10, closing prices) through the SAME board builder (the floor / NBA floor are
    built here from the rows, like R1). Football's dials differ from live (live keeps the old ones) - R2's football is
    thin (15 unit plays); R1 carries football.
Both: + the 11/12 sweep's cut (the runner-up dog hockey / NFL only, from the 11/13 games). Not replayable (no rows): the
🔍 gap plays, the college hoops slots / stack, the early spots, mid-day adds.
A finding has to hold on BOTH boards, in BOTH halves (train = to 2025-06-30, held out = 2025-07-01 on), and beat a
placebo. Live (10/13 on) is reported apart, never the judge."""
import json
import math
import os
import random
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
STUD = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(STUD, "plays_every_day_1104"))
sys.path.insert(0, os.path.join(STUD, "book_1111"))
import sim_volume as sv  # noqa: E402
import blib as B  # noqa: E402

DEEP = os.path.expanduser("~/.cache/d503_deep1112/funnel_new")
half, season, pnl = sv.half, sv.season, sv.pnl


def own_margin(r):
    """points the OWN read sits over what the price needs (None = no own read)"""
    return B.own_margin(r)


def read_of(r, k):
    """the read a play's units ride on (sports.read_of): a gated dog's weighed dog read, else the weighed read, else the
    own read, else the blend."""
    if k in ("dog", "dogplay") and r["odds"] >= 100 and r.get("dog_score") is not None:
        return min(0.95, (r["p_market"] if r.get("p_market") is not None else 1 / r["dec"]) + r["dog_score"] / 100)
    if r.get("w_p") is not None:
        return r["w_p"]
    if r.get("edge_own") is not None:
        return (r["edge_own"] + 1) / r["dec"]
    return r["p"]


def read_margin(r, k):
    return 100 * (read_of(r, k) - 1 / r["dec"])


def beats(r, k):
    return read_of(r, k) * r["dec"] > 1


def flat(r):
    return (r["dec"] - 1) if r["result"] == "won" else -1.0 if r["result"] == "lost" else 0.0


def _cut_1113(plays):
    return [(r, u, k) for r, u, k in plays if not (k == "dogplay" and r["league"] not in ("nhl", "nfl"))]


def _r1():
    return {d: _cut_1113(B.board(d)) for d in sv.days}


def _r2():
    rows = []
    for p in "ABCD":
        for ln in open(os.path.join(DEEP, f"f{p}.jsonl")):
            r = json.loads(ln)
            if r.get("market") != "ml" or r.get("result") not in ("won", "lost", "push"):
                continue
            rows.append(r)
    by = defaultdict(list)
    for r in rows:
        by[r["date"]].append(r)
    old_by, old_days = sv.by_day, sv.days
    sv.by_day = by                                         # the same builder, R2's rows
    try:
        out = {d: _cut_1113(B.board(d)) for d in sorted(by)}
    finally:
        sv.by_day = old_by
    return out, by


BOARDS = {}


def boards():
    if not BOARDS:
        BOARDS["R1"] = (_r1(), sv.by_day)
        BOARDS["R2"] = _r2()
    return BOARDS


def stat(rs):
    """rs = [(d, r, u)] -> dict n, w, l, net units, risk, flat ROI %, units ROI %, z vs the price."""
    n = len(rs)
    w = sum(r["result"] == "won" for _, r, _ in rs)
    l = sum(r["result"] == "lost" for _, r, _ in rs)
    net = sum(pnl(r, u) for _, r, u in rs)
    risk = sum(u for _, _, u in rs)
    fl = sum(flat(r) for _, r, _ in rs)
    bev = sum(1 / r["dec"] for _, r, _ in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for _, r, _ in rs)
    return dict(n=n, w=w, l=l, net=net, risk=risk, roi=100 * fl / n if n else 0.0,
                uroi=100 * net / risk if risk else 0.0, z=(w - bev) / math.sqrt(var) if var else 0.0)


def line(name, rs, units=False):
    """ALL (train + held) then train / held / live, flat 1u ROI (or units ROI) and the seasons up."""
    tr = [x for x in rs if half(x[0]) == "train"]
    he = [x for x in rs if half(x[0]) == "held"]
    lv = [x for x in rs if half(x[0]) == "live"]
    a, t, h, v = stat(tr + he), stat(tr), stat(he), stat(lv)
    key = "uroi" if units else "roi"
    seas = defaultdict(float)
    for d, r, u in tr + he:
        seas[season(d)] += pnl(r, u) if units else flat(r)
    up = sum(x > 0 for x in seas.values())
    s = (f"  {name:52s} n {a['n']:4d} {a['w']:3d}-{a['l']:<3d} {'units' if units else 'flat'} {a[key]:+6.1f}% z {a['z']:+5.2f}"
         f" | train {t[key]:+6.1f}% ({t['n']:3d}) | held {h[key]:+6.1f}% ({h['n']:3d}) | up {up}/{len(seas)}"
         f" | live {v['w']}-{v['l']} {v[key]:+.0f}%")
    if units:
        s += f" | {a['net']:+.1f}u on {a['risk']:.0f}u"
    print(s)
    return dict(all=a, train=t, held=h, live=v, up=up, ns=len(seas))


def worst(per_day, ds):
    cum = peak = w = 0.0
    for d in ds:
        cum += per_day.get(d, 0.0)
        peak = max(peak, cum)
        w = min(w, cum - peak)
    return w


def schedule(name, board, fn, quiet=False):
    """board: {d: [(r, u, k)]}; fn(d, r, u, k, day_plays) -> units. Units won / risked by half, worst stretch, seasons."""
    per_day = defaultdict(float)
    st = defaultdict(lambda: [0, 0, 0.0, 0.0])
    seas = defaultdict(float)
    for d, ps in board.items():
        for r, u, k in ps:
            nu = fn(d, r, u, k, ps)
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
    ds = sorted(board)
    tr = [d for d in ds if half(d) == "train"]
    he = [d for d in ds if half(d) == "held"]
    out = []
    for lab, dd in (("train", tr), ("held", he)):
        w, l, net, risk = st[lab]
        out.append(f"{lab} {net:+6.1f}u/{risk:4.0f}u {100 * net / risk if risk else 0:+5.1f}% worst {worst(per_day, dd):+5.1f}")
    net = st["train"][2] + st["held"][2]
    risk = st["train"][3] + st["held"][3]
    dd = worst(per_day, tr + he)
    up = sum(v > 0 for v in seas.values())
    lv = st["live"]
    if not quiet:
        print(f"  {name:58s} | " + " | ".join(out) + f" | ALL {net:+6.1f}u/{risk:4.0f}u {100 * net / risk if risk else 0:+5.1f}% "
              f"worst {dd:+5.1f} up {up}/{len(seas)} | live {lv[0]}-{lv[1]} {lv[2]:+5.1f}u")
    return dict(net=net, risk=risk, dd=dd, up=up, train=st["train"][2], held=st["held"][2],
                rtr=st["train"][3], rhe=st["held"][3])


def placebo(rs, pool, draws=2000, seed=1114):
    """How often a random draw of len(rs) from pool (same kind of plays) does as well (flat ROI), train + held only."""
    rs = [x for x in rs if half(x[0]) != "live"]
    pool = [x for x in pool if half(x[0]) != "live"]
    n = len(rs)
    if n < 10 or len(pool) <= n:
        return None
    mine = sum(flat(r) for _, r, _ in rs) / n
    rnd = random.Random(seed)
    return sum(1 for _ in range(draws) if sum(flat(r) for _, r, _ in rnd.sample(pool, n)) / n >= mine)
