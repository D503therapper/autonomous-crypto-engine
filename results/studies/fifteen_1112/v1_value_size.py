"""V1 - VALUE-PLAY SIZING (the owner's buddy, 11/12: "½u on a -150 favorite is stupid"): is there a value-play subset
that earns 1u blind? And S2 of the brief - BOTH READS AGREE BIG - on the same replay rows.

The rows: results/studies/book_1111/blib.py - today's board replayed day by day 2023-10 -> 2026-10 at the CLOSE (the
10/30 funnel rows + the 11/11 wiring), train to 2025-06-30, held out after, live apart. kind 'play' = the ½u value
plays (favorites -101..-150, moneyline). The margins: own = points of win chance the own read sits over what the price
needs (blib.own_margin); weighed = 100 x (p - 1 / dec).
FUNNEL=<folder with the funnel rows> python v1_value_size.py"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "book_1111"))
import blib as b  # noqa: E402

N = [0]


def cell(name, rs):
    N[0] += 1
    return b.cell(name, rs)


def wm(r):
    return 100 * (r["p"] - 1 / r["dec"])


V = [(d, r, u) for d, r, u, k in b.PLAYS if k == "play"]
print(f"VALUE PLAYS IN THE REPLAY ({len(V)}; ½u today)")
cell("every value play", V)
print(" by league")
for lg in ("nfl", "ncaaf", "nhl", "nba", "ncaab", "mlb"):
    cell(f"  {lg}", [x for x in V if x[1]["league"] == lg])
print(" by price")
for lo, hi in ((-150, -141), (-140, -131), (-130, -120), (-119, -101), (-150, -131), (-130, -101), (100, 400)):
    cell(f"  {lo}..{hi}", [x for x in V if lo <= x[1]["odds"] <= hi])
print(" by the own read over the price (points)")
for lo, hi in ((1, 2), (2, 3), (3, 5), (5, 8), (8, 99), (3, 99), (5, 99)):
    cell(f"  own {lo}..{hi} over", [x for x in V if b.own_margin(x[1]) is not None and lo <= b.own_margin(x[1]) < hi])
print(" by the weighed read over the price (points)")
for lo, hi in ((-99, 0), (0, 2), (2, 4), (4, 99)):
    cell(f"  weighed {lo}..{hi} over", [x for x in V if lo <= wm(x[1]) < hi])
print(" both reads agree")
for k in (2, 3, 4, 5):
    cell(f"  own AND weighed both {k}+ over", [x for x in V if (b.own_margin(x[1]) or -9) >= k and wm(x[1]) >= k])
print(" home / road, reasons, the ratings gap")
cell("  home", [x for x in V if x[1]["home"]])
cell("  road", [x for x in V if not x[1]["home"]])
for k in (3, 4, 5):
    cell(f"  {k}+ reasons", [x for x in V if (x[1].get("n_reasons2") or x[1].get("n_reasons") or 0) >= k])
cell("  not thin", [x for x in V if not x[1].get("thin")])
print(" league x price (the cells a 1u rule could be)")
for lg in ("nhl", "nba", "ncaab", "nfl", "ncaaf"):
    for lo, hi in ((-150, -131), (-130, -101)):
        cell(f"  {lg} {lo}..{hi}", [x for x in V if x[1]["league"] == lg and lo <= x[1]["odds"] <= hi])
    cell(f"  {lg} own 3+ over", [x for x in V if x[1]["league"] == lg and (b.own_margin(x[1]) or -9) >= 3])

print("\nTHE SAME CUTS ON EVERY FAVORITE UNIT PLAY (-101..-150: locks, value plays, NBA favorites)")
F = [(d, r, u) for d, r, u, k in b.PLAYS if r["odds"] < 0]
cell("every favorite unit play", F)
for k in ("lock", "play", "nbafav"):
    cell(f"  kind {k}", [(d, r, u) for d, r, u, kk in b.PLAYS if kk == k and r["odds"] < 0])
for k in (3, 5):
    cell(f"  own AND weighed both {k}+ over", [x for x in F if (b.own_margin(x[1]) or -9) >= k and wm(x[1]) >= k])

print("\nPLACEBO: the best-looking value-play cell above against random same-size sets of value plays (held-out half)")
he = [x for x in V if b.half(x[0]) == "held"]
rnd = random.Random(7)


def roi(rs):
    return sum(b.flat(r) for _, r, _ in rs) / len(rs) if rs else 0.0


for name, f in (("own 3+ over", lambda r: (b.own_margin(r) or -9) >= 3), ("-150..-131", lambda r: -150 <= r["odds"] <= -131),
                ("nhl", lambda r: r["league"] == "nhl"), ("both 3+", lambda r: (b.own_margin(r) or -9) >= 3 and wm(r) >= 3)):
    sub = [x for x in he if f(x[1])]
    if len(sub) < 5:
        continue
    t = roi(sub)
    k = sum(1 for _ in range(2000) if roi(rnd.sample(he, len(sub))) >= t)
    print(f"  {name}: held {100 * t:+.1f}% on {len(sub)}; random sets as good {k} of 2000")
print(f"\ncells printed: {N[0]}")
