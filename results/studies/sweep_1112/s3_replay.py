"""11/12 FULL SWEEP, parts 2-5 on the REPLAY BOARD (the 11/11 book study's blib.py: the 10/30 funnel rows, 1,097 board
days 2023-10 -> 2026-10 + the live stretch, closing prices, today's builder and sizing; train = to 2025-06, held out =
2025-07 on). NOT repeated: the 21 sizing schedules of 11/11 (s1_sizing) and the 10/30 top-tier cells. New here:
  (A) MAX PLAY candidates named before looking (the list in the sweep's brief), each with train / held / seasons / z,
      a placebo (the same number of plays of the same kind drawn at random, 2,000 times) and the 3u schedule's worst stretch;
  (B) FEWER, BETTER BETS - a stricter own-read bar on every unit play, and a cap on the unit plays a day;
  (C) THE LEAKS on the replay - NBA dogs by kind and by season, college football dogs, the runner-up dog by league;
  (D) SATURDAYS - college football dog unit plays a day, and what a cap / a stricter bar does.
FUNNEL rows live in the scratchpad (54 MB, never committed).
Usage: python results/studies/sweep_1112/s3_replay.py > results/studies/sweep_1112/s3_replay.out"""
import math
import os
import random
import sys
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "book_1111"))
import blib as B  # noqa: E402

PLAYS, half, season, pnl, flat, stat = B.PLAYS, B.half, B.season, B.pnl, B.flat, B.stat
rnd = random.Random(1112)


def om(r):
    """points the OWN read sits over what the price needs"""
    return B.own_margin(r)


def wm(r):
    """points the WEIGHED read sits over what the price needs (None with no weighed read)"""
    return None if r.get("w_p") is None else 100 * (r["w_p"] - 1 / r["dec"])


def bm(r):
    """points the BLENDED win % sits over what the price needs"""
    return 100 * (r["p"] - 1 / r["dec"])


def cell(name, sel, pool_sel=None, placebo=True):
    rs = [(d, r, u) for d, r, u, k in PLAYS if sel(d, r, u, k)]
    a, t, h, up, ns = B.cell(name, rs)
    if placebo and pool_sel and a["n"] >= 15:
        pool = [(d, r, u) for d, r, u, k in PLAYS if pool_sel(d, r, u, k) and half(d) != "live"]
        mine = sum(flat(r) for d, r, u in rs if half(d) != "live") / max(1, a["n"])
        if len(pool) > a["n"]:
            beat = sum(1 for _ in range(2000) if sum(flat(r) for _, r, _ in rnd.sample(pool, a["n"])) / a["n"] >= mine)
            print(f"      placebo: a random {a['n']} of the {len(pool)} plays of its kind did as well {beat} of 2,000 times")
    return a, t, h, up, ns


print("=" * 20, "(A) MAX PLAY CANDIDATES (flat 1u ROI; z = wins vs what the price expects)")
print("-- the base kinds")
for k in ("lock", "dog", "play", "floor", "nbafloor", "dogplay", "nbafav"):
    cell(f"kind {k}", lambda d, r, u, kk, k=k: kk == k, placebo=False)
print("-- today's sizes")
for uu in (2.0, 1.0, 0.5):
    cell(f"today's {uu}u plays", lambda d, r, u, kk, uu=uu: u == uu, placebo=False)

isk = lambda *ks: (lambda d, r, u, k: k in ks)    # noqa: E731
print("-- 1. BOTH READS BEAT THE PRICE BY A LOT (own read AND weighed read, points over what the price needs)")
for x in (2, 3, 5):
    cell(f"any unit play: own {x}+ AND weighed {x}+", lambda d, r, u, k, x=x: om(r) is not None and wm(r) is not None and om(r) >= x and wm(r) >= x, lambda d, r, u, k: True)
    cell(f"   favorites only", lambda d, r, u, k, x=x: r["odds"] < 0 and om(r) is not None and wm(r) is not None and om(r) >= x and wm(r) >= x, lambda d, r, u, k: r["odds"] < 0)
    cell(f"   dogs only", lambda d, r, u, k, x=x: r["odds"] > 0 and om(r) is not None and wm(r) is not None and om(r) >= x and wm(r) >= x, lambda d, r, u, k: r["odds"] > 0)
print("-- 2. THE LOCK: own read 56%+ AND the weighed read over the price")
cell("Lock, own read 56%+ and weighed over", lambda d, r, u, k: k == "lock" and r.get("edge_own") is not None and (r["edge_own"] + 1) / r["dec"] >= 0.56 and wm(r) is not None and wm(r) > 0, isk("lock"))
cell("Lock, own read 60%+ and weighed over", lambda d, r, u, k: k == "lock" and r.get("edge_own") is not None and (r["edge_own"] + 1) / r["dec"] >= 0.60 and wm(r) is not None and wm(r) > 0, isk("lock"))
cell("Lock, own 5+ over and weighed 2+ over", lambda d, r, u, k: k == "lock" and om(r) is not None and om(r) >= 5 and wm(r) is not None and wm(r) >= 2, isk("lock"))
cell("Lock, today's 2u", lambda d, r, u, k: k == "lock" and u == 2.0, isk("lock"))
cell("Lock, not college hoops", lambda d, r, u, k: k == "lock" and r["league"] != "ncaab", isk("lock"))
print("-- 3. AGREEMENT: the blend, the own read and the weighed read ALL over the price by 2+")
cell("all three reads 2+ over", lambda d, r, u, k: om(r) is not None and wm(r) is not None and min(om(r), wm(r), bm(r)) >= 2, lambda d, r, u, k: True)
cell("all three reads 3+ over, price -150..+150", lambda d, r, u, k: om(r) is not None and wm(r) is not None and min(om(r), wm(r), bm(r)) >= 3 and r["odds"] <= 150, lambda d, r, u, k: r["odds"] <= 150)
print("-- 4. THE DOG OF THE DAY (today 2u to +150)")
D2 = lambda d, r, u, k: k == "dog" and u == 2.0    # noqa: E731
cell("the 2u Dog (all)", D2, placebo=False)
for x in (1, 2, 3, 5):
    cell(f"2u Dog, own read {x}+ points over", lambda d, r, u, k, x=x: D2(d, r, u, k) and om(r) is not None and om(r) >= x, D2)
for x in (6, 8, 10):
    cell(f"2u Dog, dog score {x}+", lambda d, r, u, k, x=x: D2(d, r, u, k) and (r.get("dog_score") or -99) >= x, D2)
cell("2u Dog, dog score 8+ AND own 1+ over", lambda d, r, u, k: D2(d, r, u, k) and (r.get("dog_score") or -99) >= 8 and om(r) is not None and om(r) >= 1, D2)
cell("2u Dog, +130..+150", lambda d, r, u, k: D2(d, r, u, k) and r["odds"] >= 130, D2)
cell("2u Dog at home", lambda d, r, u, k: D2(d, r, u, k) and r["home"], D2)
print("-- 5. THE HOCKEY DOG WITH A BIG OWN EDGE (the live read is the line + the back-to-back / rest)")
HD = lambda d, r, u, k: k == "dog" and r["league"] == "nhl"    # noqa: E731
cell("hockey Dog (all)", HD, placebo=False)
for x in (0, 1, 2, 3):
    cell(f"hockey Dog, own read {x}+ over, to +150", lambda d, r, u, k, x=x: HD(d, r, u, k) and r["odds"] <= 150 and om(r) is not None and om(r) >= x, HD)
cell("hockey Dog, own read UNDER the price, to +150", lambda d, r, u, k: HD(d, r, u, k) and r["odds"] <= 150 and om(r) is not None and om(r) < 0, HD)
cell("hockey Dog, own gap over the no-vig market 3+", lambda d, r, u, k: HD(d, r, u, k) and r["odds"] <= 150 and (B.gap(r) or -99) >= 3, HD)
print("-- 6. FAVORITES (value plays + Locks + the NBA favorite play) by the weighed read")
FV = lambda d, r, u, k: r["odds"] < 0    # noqa: E731
for x in (2, 4):
    cell(f"favorite unit play, weighed {x}+ over the no-vig market", lambda d, r, u, k, x=x: FV(d, r, u, k) and r.get("w_p") is not None and 100 * (r["w_p"] - r["p_market"]) >= x, FV)
cell("NBA favorite play", lambda d, r, u, k: k == "nbafav", placebo=False)

print("\n-- THE 3u SCHEDULES for the cells above that came closest (units, worst stretch; today's sizing first)")
base = B.schedule("TODAY'S SIZING", lambda k, r, u: u)
B.schedule("3u: Lock with own 56%+ and weighed over", lambda k, r, u: 3.0 if k == "lock" and u == 2.0 and r.get("edge_own") is not None and (r["edge_own"] + 1) / r["dec"] >= 0.56 and wm(r) is not None and wm(r) > 0 else u)
B.schedule("3u: all three reads 3+ over, to +150", lambda k, r, u: 3.0 if om(r) is not None and wm(r) is not None and min(om(r), wm(r), bm(r)) >= 3 and r["odds"] <= 150 and k in ("lock", "dog") else u)
B.schedule("3u: the 2u Dog with a dog score 8+", lambda k, r, u: 3.0 if k == "dog" and u == 2.0 and (r.get("dog_score") or -99) >= 8 else u)
B.schedule("3u: the 2u Dog with own 2+ over", lambda k, r, u: 3.0 if k == "dog" and u == 2.0 and om(r) is not None and om(r) >= 2 else u)
B.schedule("3u: the hockey Dog to +150 with own 1+ over", lambda k, r, u: 3.0 if k == "dog" and r["league"] == "nhl" and r["odds"] <= 150 and om(r) is not None and om(r) >= 1 else u)
B.schedule("3u: every 2u play (the chase: more size, the same bets)", lambda k, r, u: 3.0 if u == 2.0 else u)

print("\n" + "=" * 20, "(B) FEWER, BETTER BETS")
print("-- a stricter OWN-READ bar on every unit play (own read X+ points over what the price needs; no own read = out)")
for x in (None, -3, -1, 0, 1, 2, 3, 5):
    B.schedule("no bar (today)" if x is None else f"own read {x:+d}+ over the price", lambda k, r, u, x=x: u if x is None or (om(r) is not None and om(r) >= x) else 0)
print("-- the same bar on DOGS only")
for x in (-3, -1, 0, 1, 2, 3):
    B.schedule(f"dogs need own {x:+d}+", lambda k, r, u, x=x: u if r["odds"] < 0 or (om(r) is not None and om(r) >= x) else 0)
print("-- the same bar on the ½u plays only (floor / NBA floor / runner-up / value plays)")
for x in (-3, -1, 0, 1, 2):
    B.schedule(f"½u plays need own {x:+d}+", lambda k, r, u, x=x: u if u > 0.5 or (om(r) is not None and om(r) >= x) else 0)
print("-- a CAP on the unit plays a day (kept in the board's own order: the Lock, the Dog, plays, the floor)")
by_d = defaultdict(list)
for d, r, u, k in PLAYS:
    by_d[d].append((r, u, k))
ORDER = {"lock": 0, "dog": 1, "nbafav": 2, "solo": 3, "play": 4, "dogplay": 5, "nbafloor": 6, "floor": 7, "floorfb": 8}
for cap in (None, 6, 5, 4, 3, 2, 1):
    keep = set()
    for d, v in by_d.items():
        v2 = sorted(v, key=lambda x: ORDER.get(x[2], 9))
        for r, u, k in (v2 if cap is None else v2[:cap]):
            keep.add((d, r["team"], k))
    B.schedule("no cap (today)" if cap is None else f"at most {cap} unit plays a day", lambda k, r, u, keep=keep: u if (r["date"], r["team"], k) in keep else 0)
n_by = defaultdict(list)
for d, v in by_d.items():
    if half(d) != "live":
        n_by[min(len(v), 6)].append(sum(pnl(r, u) for r, u, k in v))
print("   a day's result by how many unit plays it carried: " + " | ".join(f"{n}{'+' if n == 6 else ''}: {len(x)} days {sum(x):+.1f}u ({sum(x) / len(x):+.2f}u a day)" for n, x in sorted(n_by.items())))

print("\n" + "=" * 20, "(C) THE LEAKS ON THE REPLAY")
for lg in ("nba", "ncaaf", "nhl", "nfl", "mlb", "ncaab"):
    cell(f"{lg} dogs, every kind", lambda d, r, u, k, lg=lg: r["league"] == lg and r["odds"] > 0, placebo=False)
    for kk in ("dog", "dogplay", "nbafloor", "floor", "floorfb"):
        if any(k == kk and r["league"] == lg for d, r, u, k in PLAYS):
            cell(f"   {lg} {kk}", lambda d, r, u, k, lg=lg, kk=kk: r["league"] == lg and k == kk, placebo=False)
print("-- NBA dogs by month (the live leak is Oct-Nov)")
for m, name in (((10, 11), "Oct-Nov"), ((12, 1), "Dec-Jan"), ((2, 3, 4), "Feb-Apr")):
    cell(f"NBA dogs every kind, {name}", lambda d, r, u, k, m=m: r["league"] == "nba" and r["odds"] > 0 and int(d[5:7]) in m, placebo=False)
    cell(f"   NBA floor, {name}", lambda d, r, u, k, m=m: k == "nbafloor" and int(d[5:7]) in m, placebo=False)
cell("NBA dogs, own read UNDER the price", lambda d, r, u, k: r["league"] == "nba" and r["odds"] > 0 and om(r) is not None and om(r) < 0, placebo=False)
cell("NBA dogs, own read over the price", lambda d, r, u, k: r["league"] == "nba" and r["odds"] > 0 and om(r) is not None and om(r) >= 0, placebo=False)
cell("NBA dogs +100..+150", lambda d, r, u, k: r["league"] == "nba" and 100 <= r["odds"] <= 150, placebo=False)
cell("NBA dogs +151..+199", lambda d, r, u, k: r["league"] == "nba" and 151 <= r["odds"] <= 199, placebo=False)
print("-- the runner-up dog play by league")
for lg in ("nhl", "nba", "ncaaf", "nfl", "mlb"):
    cell(f"runner-up dog, {lg}", lambda d, r, u, k, lg=lg: k == "dogplay" and r["league"] == lg, placebo=False)
B.schedule("no runner-up dog play at all", lambda k, r, u: 0 if k == "dogplay" else u)
B.schedule("no NBA runner-up dog", lambda k, r, u: 0 if k == "dogplay" and r["league"] == "nba" else u)
B.schedule("no NBA floor", lambda k, r, u: 0 if k == "nbafloor" else u)
B.schedule("no NBA floor in Oct-Nov", lambda k, r, u: 0 if k == "nbafloor" and int(r["date"][5:7]) in (10, 11) else u)
B.schedule("no NBA dog of any kind in Oct-Nov", lambda k, r, u: 0 if r["league"] == "nba" and r["odds"] > 0 and int(r["date"][5:7]) in (10, 11) else u)
B.schedule("no NBA dog with the own read under the price", lambda k, r, u: 0 if r["league"] == "nba" and r["odds"] > 0 and (om(r) is None or om(r) < 0) else u)

print("\n" + "=" * 20, "(D) SATURDAYS AND THE COLLEGE FOOTBALL DOGS (the replay has no 🔍 / early plays: the Dog, the runner-up, the floor)")
CF = lambda d, r, u, k: r["league"] == "ncaaf" and r["odds"] > 0    # noqa: E731
cell("college football dog unit plays", CF, placebo=False)
cell("   on a Saturday", lambda d, r, u, k: CF(d, r, u, k) and datetime.strptime(d, "%Y-%m-%d").weekday() == 5, placebo=False)
cell("   not a Saturday", lambda d, r, u, k: CF(d, r, u, k) and datetime.strptime(d, "%Y-%m-%d").weekday() != 5, placebo=False)
cell("   home dogs", lambda d, r, u, k: CF(d, r, u, k) and r["home"], placebo=False)
cell("   road dogs", lambda d, r, u, k: CF(d, r, u, k) and not r["home"], placebo=False)
cell("   +100..+150", lambda d, r, u, k: CF(d, r, u, k) and r["odds"] <= 150, placebo=False)
cell("   +151..+350", lambda d, r, u, k: CF(d, r, u, k) and r["odds"] > 150, placebo=False)
for x in (0, 2, 5, 10):
    cell(f"   own read {x}+ over the price", lambda d, r, u, k, x=x: CF(d, r, u, k) and om(r) is not None and om(r) >= x, placebo=False)
cell("   own read 10+ over the no-vig market (the read's home tilt)", lambda d, r, u, k: CF(d, r, u, k) and (B.gap(r) or -99) >= 10, placebo=False)
cell("   own read under 10 over the no-vig market", lambda d, r, u, k: CF(d, r, u, k) and (B.gap(r) or -99) < 10, placebo=False)
cnt = defaultdict(list)
for d, v in by_d.items():
    c = [(r, u, k) for r, u, k in v if r["league"] == "ncaaf" and r["odds"] > 0]
    if c and half(d) != "live":
        cnt[min(len(c), 3)].append(sum(flat(r) for r, u, k in c) / len(c))
print("   college dog unit plays a day in the replay: " + " | ".join(f"{n}{'+' if n == 3 else ''}: {len(x)} days, flat {100 * sum(x) / len(x):+.1f}% a day" for n, x in sorted(cnt.items())))
cell("every football dog unit play (NFL + college)", lambda d, r, u, k: r["league"] in ("nfl", "ncaaf") and r["odds"] > 0, placebo=False)
cell("Saturday unit plays, every sport", lambda d, r, u, k: datetime.strptime(d, "%Y-%m-%d").weekday() == 5, placebo=False)
cell("   Saturday dogs", lambda d, r, u, k: datetime.strptime(d, "%Y-%m-%d").weekday() == 5 and r["odds"] > 0, placebo=False)
cell("   Saturday favorites", lambda d, r, u, k: datetime.strptime(d, "%Y-%m-%d").weekday() == 5 and r["odds"] < 0, placebo=False)
