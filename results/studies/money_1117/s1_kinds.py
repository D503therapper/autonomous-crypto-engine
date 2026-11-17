"""11/17 MOST MONEY - (1) EVERY KIND OF UNIT PLAY, RANKED. The live-shaped board on today's code (mlib.board, R3L):
each kind's record, flat ROI vs its price by half, its units at today's size, its own worst stretch, the seasons up, the
replay of the live stretch. Sorted by the held-out half's flat ROI. Then the same by SIZE TIER (½u / 1u / 2u / 3u) - the
owner, 11/17: "when I see a play that has more units on it, that means I'll put more money on it".
Usage: python results/studies/money_1117/s1_kinds.py > results/studies/money_1117/s1_kinds.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M  # noqa: E402

P, DAYS = M.board()
nd = [d for d in DAYS if M.half(d) != "live"]
print(f"R3L: {len(P)} unit plays on {len(DAYS)} board days ({DAYS[0]} -> {DAYS[-1]}); train {sum(M.half(d) == 'train' for d in DAYS)} days, "
      f"held {sum(M.half(d) == 'held' for d in DAYS)}, live {sum(M.half(d) == 'live' for d in DAYS)}")
base = M.summ(P, DAYS)
print(M.line("TODAY'S BOARD (the ⭐ raise in)", base))
print("     by season:", M.seas_str(base))
print(M.line("  ... without the ⭐ raise", M.summ(P, DAYS, lambda r: r["u0"])))
print(M.line("  ... flat 1u on every play", M.summ(P, DAYS, lambda r: 1.0)))


def fl(rs, h=None):
    rs = [r for r in rs if (M.half(r["date"]) == h if h else M.half(r["date"]) != "live")]
    n = len(rs)
    if not n:
        return 0, 0, 0.0
    return n, sum(r["result"] == "won" for r in rs), 100 * sum(M.flat(r) for r in rs) / n


def table(groups, title):
    print(f"\n===== {title}")
    print(f"  {'kind':44s} {'n':>4s} {'W-L':>9s} {'flat':>7s} | {'train':>14s} | {'held':>14s} | {'units today':>18s} | {'worst':>6s} | up  | verdict")
    rows = []
    for k, rs in groups.items():
        n, w, r_ = fl(rs)
        nt, wt, rt = fl(rs, "train")
        nh, wh, rh = fl(rs, "held")
        o = M.summ(rs, None, lambda r: r["u0"])
        v = ("LOSES both halves" if nt >= 10 and nh >= 10 and rt < 0 and rh < 0 else
             "loses held out" if nh >= 10 and rh < 0 else "loses in train" if nt >= 10 and rt < 0 else
             "thin sample" if n < 30 else "up both halves")
        rows.append((rh if nh else -999, k, n, w, r_, nt, wt, rt, nh, wh, rh, o, v))
    for rh, k, n, w, r_, nt, wt, rt, nh, wh, rh2, o, v in sorted(rows, key=lambda t: -t[0]):
        lv = o["live"]
        print(f"  {k:44s} {n:4d} {w:4d}-{n - w:<4d} {r_:+6.1f}% | {wt:3d}-{nt - wt:<3d} {rt:+6.1f}% | {wh:3d}-{nh - wh:<3d} {rh2:+6.1f}% |"
              f" {o['net']:+6.1f}u on {o['risk']:5.1f}u | {o['dd']:+6.1f} | {o['up']}/{o['ns']} | {v} | live-replay {lv[0]}-{lv[1]} {lv[2]:+.1f}u")
    return rows


by = defaultdict(list)
for r in P:
    by[r["k"]].append(r)
table(by, "EVERY FINE KIND (sorted by the held-out flat ROI; units = today's size, the ⭐ raise left off)")

coarse = defaultdict(list)
for r in P:
    coarse[{"lock": "the Lock", "dog": "the Dog of the Day", "dogplay": "runner-up dog", "floor": "the floor", "nbafloor": "NBA floor",
            "nbafav": "NBA favorite play", "ncaabplay": "college hoops slots", "gap": "college hoops gap play", "play": "value plays",
            "solo": "one-game day"}.get(r["kind"], r["kind"])].append(r)
table(coarse, "BY PATH")

sp = defaultdict(list)
for r in P:
    sp[M.LG[r["league"]]].append(r)
table(sp, "BY SPORT (every unit play)")

tiers = defaultdict(list)
for r in P:
    tiers[f"posted at {r['u']:g}u (the ⭐ raise in)"].append(r)
table(tiers, "BY THE SIZE THE BOARD SHOWS (the ⭐ raise in) - does a bigger size win more?")
tiers0 = defaultdict(list)
for r in P:
    tiers0[f"its kind's size {r['u0']:g}u"].append(r)
table(tiers0, "BY THE KIND'S OWN SIZE (the ⭐ raise left off)")
print("\n  what is in each size (the ⭐ raise left off):")
for u in sorted({r["u0"] for r in P}):
    c = defaultdict(int)
    for r in P:
        if r["u0"] == u and M.half(r["date"]) != "live":
            c[r["k"]] += 1
    print(f"   {u:g}u: " + ", ".join(f"{k} x{n}" for k, n in sorted(c.items(), key=lambda kv: -kv[1])))

st = [r for r in P if r["star"]]
table({"the ⭐ (every one)": st, "the ⭐ on a play it RAISED (½u -> 1u)": [r for r in st if r["u0"] < 1],
       "the ⭐ on a play already 1u+": [r for r in st if r["u0"] >= 1],
       "the ½u plays the ⭐ did NOT raise": [r for r in P if r["u0"] < 1 and not r["star"]]}, "THE ⭐")
print(M.line("the ⭐'s raise alone (the extra ½u)", M.summ([r for r in st if r["u0"] < 1], None, lambda r: r["u"] - r["u0"])))
