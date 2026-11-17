"""11/17 MOST MONEY - (3) SIZE BY THE KIND'S PROVEN EDGE, NOT THE PICK'S READ. Each fine kind of unit play gets ONE size
from its own record on one half (a shrunk quarter of Kelly: the kind's win rate pulled toward what its prices need by
PRIOR phantom bets at break-even; 1u = 1% of the roll; rounded to ½u, capped 3u; under ¼u = ½u, the floor size, so a
day never loses its play) - and is JUDGED on the other half, against today's sizes on the same plays. Both directions.
Also: a plain ROI ladder (the same idea, no Kelly), "cut instead of ½u", and the placebo - the scheme's sizes dealt at
random across the judged half's plays (does knowing the KIND beat not knowing it?).
Usage: python results/studies/money_1117/s3_kind_size.py > results/studies/money_1117/s3_kind_size.out"""
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M  # noqa: E402

P, DAYS = M.board()
base = M.summ(P, DAYS, lambda r: r["u0"])
print(M.line("TODAY'S SIZES (the ⭐ raise left off - the kind's own size)", base, w=60))
PRIOR = 60


def rec(h):
    st = defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0])     # n, w, sum 1/dec, sum dec, flat
    for r in P:
        if M.half(r["date"]) == h:
            s = st[r["k"]]
            s[0] += 1
            s[1] += r["result"] == "won"
            s[2] += 1 / r["dec"]
            s[3] += r["dec"]
            s[4] += M.flat(r)
    return st


def kelly_size(s, prior=PRIOR, frac=0.25, cap=3.0, lo=0.5):
    n, w, bev, dec, _ = s
    q, d = bev / n, dec / n
    p = (w + prior * q) / (n + prior)
    f = (p * d - 1) / (d - 1)
    u = round(2 * 100 * frac * f) / 2
    return max(lo, min(cap, u)), p, q, d


def ladder_size(s):
    n, _, _, _, fl = s
    r_ = 100 * fl / n
    if n < 30:
        return None
    return 0.5 if r_ < 5 else 1.0 if r_ < 15 else 2.0 if r_ < 30 else 3.0


def today(r):
    return r["u0"]


def run(fit, judge, mode, show=True):
    st = rec(fit)
    sz = {}
    for k, s in st.items():
        cur = next(r["u0"] for r in P if r["k"] == k)
        if s[0] < 15:
            sz[k] = cur                                   # too few to size: today's size
            continue
        if mode == "kelly":
            sz[k] = kelly_size(s)[0]
        elif mode == "kelly_cut":
            sz[k] = kelly_size(s, lo=0.0)[0]
        elif mode == "ladder":
            sz[k] = ladder_size(s) or cur
        elif mode == "up_only":                           # never smaller than today, bigger only where the kind earned it
            sz[k] = max(cur, kelly_size(s)[0])
        elif mode == "down_only":
            sz[k] = min(cur, kelly_size(s)[0])
    f = lambda r: sz.get(r["k"], r["u0"])                 # noqa: E731
    J = [r for r in P if M.half(r["date"]) == judge]
    a, b = M.summ(J, None, today), M.summ(J, None, f)
    scale = a["risk"] / b["risk"] if b["risk"] else 0
    rnd = random.Random(1117)
    fl = [M.flat(r) for r in J]
    us = [f(r) for r in J]
    hit = 0
    for _ in range(2000):
        u2 = us[:]
        rnd.shuffle(u2)
        hit += sum(x * y for x, y in zip(fl, u2)) >= b["net"]
    if show:
        print(f"\n  -- {mode}: sized on {fit}, judged on {judge}")
        for k in sorted(sz, key=lambda k: -st[k][0]):
            s = st[k]
            cur = next(r["u0"] for r in P if r["k"] == k)
            if sz[k] != cur:
                jr = [r for r in J if r["k"] == k]
                jn = len(jr)
                print(f"       {k:44s} {fit} {s[1]}-{s[0] - s[1]} {100 * s[4] / s[0]:+6.1f}% -> {cur:g}u becomes {sz[k]:g}u"
                      f" | on {judge}: {sum(r['result'] == 'won' for r in jr)}-{jn - sum(r['result'] == 'won' for r in jr)} {100 * sum(M.flat(r) for r in jr) / jn if jn else 0:+6.1f}%")
    print(f"     {judge}: TODAY {a['net']:+6.1f}u on {a['risk']:5.0f}u ({a['roi']:+5.1f}%) worst {a['dd']:+5.1f}u  ->  {mode:10s} {b['net']:+6.1f}u on {b['risk']:5.0f}u ({b['roi']:+5.1f}%) worst {b['dd']:+5.1f}u"
          f" | at today's total risk {b['net'] * scale:+6.1f}u worst {b['dd'] * scale:+5.1f}u | the same sizes dealt at random as good {hit} of 2,000")
    return sz


print("\n===== A. A SHRUNK QUARTER OF KELLY ON THE KIND'S OWN RECORD (½u floor, 3u cap)")
run("train", "held", "kelly")
run("held", "train", "kelly")
print("\n===== B. THE SAME, A KIND THAT EARNS UNDER ¼u IS CUT")
run("train", "held", "kelly_cut")
run("held", "train", "kelly_cut")
print("\n===== C. THE PLAIN ROI LADDER (30+ plays: under +5% ½u, +5..15% 1u, +15..30% 2u, 30%+ 3u)")
run("train", "held", "ladder")
run("held", "train", "ladder")
print("\n===== D. ONLY UP (today's size, bigger only where the kind's Kelly says so)")
run("train", "held", "up_only")
run("held", "train", "up_only")
print("\n===== E. ONLY DOWN (today's size, smaller where the kind's Kelly says so)")
run("train", "held", "down_only")
run("held", "train", "down_only")

print("\n===== F. HOW STABLE IS A KIND'S ROI FROM ONE HALF TO THE NEXT? (kinds with 15+ plays in each half)")
t, h = rec("train"), rec("held")
xs = [(100 * t[k][4] / t[k][0], 100 * h[k][4] / h[k][0], k) for k in t if k in h and t[k][0] >= 15 and h[k][0] >= 15]
n = len(xs)
mx, my = sum(x for x, _, _ in xs) / n, sum(y for _, y, _ in xs) / n
cov = sum((x - mx) * (y - my) for x, y, _ in xs)
vx, vy = sum((x - mx) ** 2 for x, _, _ in xs), sum((y - my) ** 2 for _, y, _ in xs)
print(f"  {n} kinds; the correlation of train ROI and held ROI across kinds: {cov / (vx * vy) ** 0.5:+.2f}")
for x, y, k in sorted(xs, key=lambda t_: -t_[0]):
    print(f"     {k:44s} train {x:+6.1f}% ({t[k][0]:3d}) | held {y:+6.1f}% ({h[k][0]:3d})")
rx = {k: i for i, (_, _, k) in enumerate(sorted(xs, key=lambda t_: -t_[0]))}
ry = {k: i for i, (_, _, k) in enumerate(sorted(xs, key=lambda t_: -t_[1]))}
d2 = sum((rx[k] - ry[k]) ** 2 for k in rx)
print(f"  rank correlation: {1 - 6 * d2 / (n * (n * n - 1)):+.2f}")
