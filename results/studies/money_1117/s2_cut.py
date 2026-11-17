"""11/17 MOST MONEY - (2) CUT THE LOSERS. The board (mlib.board, R3L) with each kind of unit play taken off: units won,
ROI, the worst stretch, both halves, the seasons, and the share of board days that still carry a unit play (the owner,
11/4: plays every day). Then the honest test of "cut what loses": pick the losers on the TRAIN half only, take them off,
and judge the board on the HELD half - and the mirror (pick on held, judge on train).
A removed play is simply gone (the floor would refill some days live - the day share here is the low end).
Usage: python results/studies/money_1117/s2_cut.py > results/studies/money_1117/s2_cut.out"""
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M  # noqa: E402

P, DAYS = M.board()
base = M.summ(P, DAYS)
print(M.line("TODAY'S BOARD", base))
PATH = {"lock": "the Lock", "dog": "the Dog of the Day", "dogplay": "runner-up dog", "floor": "the floor", "nbafloor": "NBA floor",
        "nbafav": "NBA favorite play", "ncaabplay": "college hoops slots", "gap": "college hoops gap play", "play": "value plays", "solo": "one-game day"}


def cut_table(title, key):
    print(f"\n===== {title}")
    ks = defaultdict(int)
    for r in P:
        ks[key(r)] += M.half(r["date"]) != "live"
    for k, n in sorted(ks.items(), key=lambda kv: -kv[1]):
        if n < 9:
            continue
        o = M.summ([r for r in P if key(r) != k], DAYS)
        print(M.line(f"without: {k} ({n})", o, base, w=58))


cut_table("THE BOARD WITHOUT ONE PATH", lambda r: PATH.get(r["kind"], r["kind"]))
cut_table("THE BOARD WITHOUT ONE FINE KIND (9+ plays)", lambda r: r["k"])
cut_table("THE BOARD WITHOUT ONE SPORT", lambda r: M.LG[r["league"]])
cut_table("THE BOARD WITHOUT ONE SIZE (the kind's own size)", lambda r: f"{r['u0']:g}u plays")
print(M.line("without the ⭐ raise", M.summ(P, DAYS, lambda r: r["u0"]), base, w=58))


def kind_roi(h):
    st = defaultdict(lambda: [0, 0.0])
    for r in P:
        if M.half(r["date"]) == h:
            st[r["k"]][0] += 1
            st[r["k"]][1] += M.flat(r)
    return {k: (n, 100 * s / n) for k, (n, s) in st.items()}


print("\n===== THE HONEST TEST: pick the losers on one half, judge the cut on the OTHER half")
for pick, judge in (("train", "held"), ("held", "train")):
    kr = kind_roi(pick)
    for minn, thr in ((10, 0.0), (20, 0.0), (10, 5.0), (30, 0.0)):
        losers = sorted(k for k, (n, r_) in kr.items() if n >= minn and r_ < thr)
        on = [r for r in P if M.half(r["date"]) == judge]
        off = [r for r in on if r["k"] not in losers]
        gone = [r for r in on if r["k"] in losers]
        a, b, g = M.summ(on, DAYS), M.summ(off, DAYS), M.summ(gone)
        dd = [d for d in DAYS if M.half(d) == judge]
        sh = lambda rs: 100 * len({r["date"] for r in rs}) / len(dd)    # noqa: E731
        # placebo: take the same NUMBER of random plays off the judged half
        rnd = random.Random(1117)
        fl = [M.pnl(r, r["u"]) for r in on]
        mine = b["net"]
        hit = sum(1 for _ in range(2000) if sum(rnd.sample(fl, len(off))) >= mine) if 0 < len(off) < len(on) else None
        print(f"  losers by {pick} ({minn}+ plays, flat ROI under {thr:+.0f}%): {len(losers)} kinds, {len(gone)} plays on {judge}")
        for k in losers:
            print(f"        - {k}: {pick} {kr[k][1]:+.1f}% on {kr[k][0]}")
        print(f"      {judge}: the board {a['net']:+.1f}u on {a['risk']:.0f}u ({a['roi']:+.1f}%), worst {a['dd']:+.1f}u, days {sh(on):.0f}%"
              f"  ->  cut {b['net']:+.1f}u on {b['risk']:.0f}u ({b['roi']:+.1f}%), worst {b['dd']:+.1f}u, days {sh(off):.0f}%"
              f"   | the plays cut made {g['net']:+.1f}u on {g['risk']:.0f}u ({g['roi']:+.1f}%) | as good by removing random plays: {hit} of 2,000")

print("\n===== KINDS DOWN IN BOTH HALVES (10+ plays in each)")
kt, kh = kind_roi("train"), kind_roi("held")
both = [k for k in kt if k in kh and kt[k][0] >= 10 and kh[k][0] >= 10 and kt[k][1] < 0 and kh[k][1] < 0]
print("  ", both or "NONE")
print("\n===== THE FLOOR, by what the board would be without it on days it is the ONLY unit play")
by = defaultdict(list)
for r in P:
    by[r["date"]].append(r)
only = [r for d, ps in by.items() for r in ps if all(q["kind"] == "floor" for q in ps)]
rest = [r for r in P if r["kind"] == "floor" and r not in only]
print(M.line("floor plays on days with NO other unit play", M.summ(only)))
print(M.line("floor plays beside another unit play", M.summ(rest)))
o = M.summ([r for r in P if r not in rest], DAYS)
print(M.line("the board, the floor only when nothing else is up", o, base))
