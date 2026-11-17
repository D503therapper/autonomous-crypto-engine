"""11/17 UNDERDOG EDGE - the shared rig. Three replay boards, closing prices, train = to 2025-06-30, held out = after
(to the live cut), live apart:
  R1  the 10/30 funnel rows through the 11/11 book study's board (sizing_1114/lib.py) - 2023-10 -> 2026-10
  R2  the 11/12 deep-program rows on the 11/12 code through the same builder - 2023-10 -> 2026-11
  R3  NEW: results/studies/dogs_1117/funnel6.py - the board re-built on TODAY's code with every 2026 date gate open (the
      code that posts a board on 11/17), the board's own picks (make_board / plays / gap / dogplay / the college hoops
      slots / NBA favorite / NBA floor / the floor), every moneyline row with the dog score's parts - 2023-10 -> 2026-11
THE BAR (the standing rule): wins more vs the price in BOTH halves, up in most seasons, a random same-size set matches it
under 5% of the time (100 of 2,000), the worst stretch does not blow out, holds a point worse than the close."""
import glob
import json
import math
import os
import random
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "sizing_1114"))
ROWS3 = os.path.expanduser("~/.cache/d503_dogs1117/rows")
HELD_FROM, LIVE_FROM = "2025-07-01", "2026-10-13"


def half(d):
    return "live" if d >= LIVE_FROM else "held" if d >= HELD_FROM else "train"


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{(y + 1) % 100:02d}" if m >= 7 else f"{y - 1}-{y % 100:02d}"


def r3(dogs_only=False):
    rows = []
    for q in sorted(glob.glob(ROWS3 + "/f[A-D]*.jsonl")):
        for ln in open(q):
            if not ln.strip():
                continue
            r = json.loads(ln)
            if r.get("result") not in ("won", "lost"):
                continue
            if dogs_only and not 100 <= r["odds"] <= 350:
                continue
            r["x"] = r.get("x") or {}
            rows.append(r)
    seen, out = set(), []
    for r in rows:                       # (a resumed chunk can repeat its last day)
        k = (r["gid"], r["side"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def flat(r, cents=0):
    """flat 1u profit; cents = the price made that many American cents worse (the 'a point worse than the close' check
    uses 10 cents ~ 1 point of win chance at these prices... see worse())."""
    if r["result"] != "won":
        return -1.0
    return worse_dec(r, cents) - 1


def worse_dec(r, pts=0.0):
    """the decimal price with `pts` points of win chance taken off it (break-even p + pts/100)."""
    if not pts:
        return r["dec"]
    return 1 / min(0.99, 1 / r["dec"] + pts / 100)


def stat(rs, pts=0.0):
    n = len(rs)
    if not n:
        return dict(n=0, w=0, roi=0.0, z=0.0, wp=0.0, bev=0.0, net=0.0)
    w = sum(r["result"] == "won" for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    net = sum(flat(r, pts) for r in rs)
    return dict(n=n, w=w, roi=100 * net / n, z=(w - bev) / math.sqrt(var) if var else 0.0, wp=100 * w / n, bev=100 * bev / n, net=net)


def cell(name, rs, say=print, live=True, w=58):
    tr = [r for r in rs if half(r["date"]) == "train"]
    he = [r for r in rs if half(r["date"]) == "held"]
    lv = [r for r in rs if half(r["date"]) == "live"]
    a, t, h, v = stat(tr + he), stat(tr), stat(he), stat(lv)
    seas = defaultdict(float)
    for r in tr + he:
        seas[season(r["date"])] += flat(r)
    up = sum(x > 0 for x in seas.values())
    w1 = stat(tr + he, 1.0)
    s = (f"  {name:{w}s} n {a['n']:5d} {a['w']:4d}-{a['n'] - a['w']:<4d} {a['wp']:4.1f}% (needs {a['bev']:4.1f}) {a['roi']:+6.1f}% z {a['z']:+5.2f}"
         f" | train {t['roi']:+6.1f}% ({t['n']:4d}) | held {h['roi']:+6.1f}% ({h['n']:4d}) | up {up}/{len(seas)} | 1pt worse {w1['roi']:+6.1f}%")
    if live:
        s += f" | live {v['w']}-{v['n'] - v['w']} {v['roi']:+.0f}%"
    say(s)
    return dict(all=a, train=t, held=h, live=v, up=up, ns=len(seas), w1=w1)


def placebo(rs, pool, draws=2000, seed=1117):
    """how many of 2,000 random same-size draws from `pool` (train + held only) did as well (flat ROI)"""
    rs = [r for r in rs if half(r["date"]) != "live"]
    pool = [r for r in pool if half(r["date"]) != "live"]
    n = len(rs)
    if n < 10 or len(pool) <= n:
        return None
    mine = sum(flat(r) for r in rs) / n
    fl = [flat(r) for r in pool]
    rnd = random.Random(seed)
    return sum(1 for _ in range(draws) if sum(rnd.sample(fl, n)) / n >= mine)


def placebo_lo(rs, pool, draws=2000, seed=1117):
    """...did as BADLY (for a fade)"""
    rs = [r for r in rs if half(r["date"]) != "live"]
    pool = [r for r in pool if half(r["date"]) != "live"]
    n = len(rs)
    if n < 10 or len(pool) <= n:
        return None
    mine = sum(flat(r) for r in rs) / n
    fl = [flat(r) for r in pool]
    rnd = random.Random(seed)
    return sum(1 for _ in range(draws) if sum(rnd.sample(fl, n)) / n <= mine)


def worst(per_day):
    cum = peak = w = 0.0
    for d in sorted(per_day):
        cum += per_day[d]
        peak = max(peak, cum)
        w = min(w, cum - peak)
    return w


def sched(name, plays, say=print):
    """plays = [(r, units)] -> units / risk / ROI by half, worst stretch (train + held), seasons up."""
    st = defaultdict(lambda: [0.0, 0.0, 0, 0])
    per, seas = defaultdict(float), defaultdict(float)
    for r, u in plays:
        if not u:
            continue
        p = u * flat(r)
        h = half(r["date"])
        st[h][0] += p
        st[h][1] += u
        st[h][2] += r["result"] == "won"
        st[h][3] += 1
        if h != "live":
            per[r["date"]] += p
            seas[season(r["date"])] += p
    net, risk = st["train"][0] + st["held"][0], st["train"][1] + st["held"][1]
    up = sum(v > 0 for v in seas.values())
    f = lambda h: f"{st[h][0]:+6.1f}u/{st[h][1]:5.1f}u {100 * st[h][0] / st[h][1] if st[h][1] else 0:+5.1f}%"   # noqa: E731
    say(f"  {name:56s} | train {f('train')} | held {f('held')} | ALL {net:+6.1f}u/{risk:6.1f}u {100 * net / risk if risk else 0:+5.1f}% worst {worst(per):+5.1f}u up {up}/{len(seas)}"
        f" | live {st['live'][2]}-{st['live'][3] - st['live'][2]} {st['live'][0]:+.1f}u")
    return dict(net=net, risk=risk, dd=worst(per), up=up, train=st["train"][0], held=st["held"][0])


def band(r):
    return "+100..+150" if r["odds"] <= 150 else "+151..+250" if r["odds"] <= 250 else "+251..+350"


BANDS = ["+100..+150", "+151..+250", "+251..+350"]
