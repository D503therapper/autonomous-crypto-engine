"""11/17 UNDERDOG EDGE - (2) WHERE THE DOG EDGE LIVES AND WHERE IT BLEEDS, on R3 (funnel6.py: the board re-built on
TODAY's code, every 2026 date gate open, 2023-10 -> 2026-11, closing prices; train = to 2025-06-30, held out = after to
the live cut 10/13, live apart).
  A  every dog +100..+350 (the vig) by sport x price band x home / road
  B  the board's dog plays by path x sport, at today's sizes; by price band; home / road
  C  the dog score: bands, the own read vs the no-vig close, the honest weighed read (the study part over the price)
  D  the line: the money left the dog / came to it (open -> close no-vig drift)
  E  the early-season gates (the team's games in)
Usage: python results/studies/dogs_1117/s2_edge.py > results/studies/dogs_1117/s2_edge.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dlib as D  # noqa: E402

R = D.r3()
DOGS = [r for r in R if 100 <= r["odds"] <= 350]
LGS = ("nhl", "nba", "nfl", "ncaaf", "ncaab")
print(f"R3: {len(R)} moneyline rows, {len(DOGS)} dogs +100..+350, {min(r['date'] for r in R)} -> {max(r['date'] for r in R)}")
home = lambda r: bool(r["home"]) and not r.get("neutral")     # noqa: E731
road = lambda r: not r["home"] and not r.get("neutral")       # noqa: E731
sc = lambda r: r["dog_score"] if r.get("dog_score") is not None else -99   # noqa: E731
own = lambda r: None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]   # noqa: E731


def own_gap(r):
    o = own(r)
    return None if o is None or r.get("p_market") is None else 100 * (o - r["p_market"])


def own_edge(r):
    o = own(r)
    return None if o is None else 100 * (o - 1 / r["dec"])


print("\n===== A. EVERY DOG (the vig) - sport x price band x home / road")
for lg in LGS:
    d = [r for r in DOGS if r["league"] == lg]
    D.cell(f"{lg}: every dog", d)
    for b in D.BANDS:
        D.cell(f"   {b}", [r for r in d if D.band(r) == b])
    D.cell("   home", [r for r in d if home(r)])
    D.cell("   road", [r for r in d if road(r)])
    D.cell("   neutral", [r for r in d if r.get("neutral")])
    for b in D.BANDS:
        D.cell(f"   home {b}", [r for r in d if home(r) and D.band(r) == b])
        D.cell(f"   road {b}", [r for r in d if road(r) and D.band(r) == b])

print("\n===== B. THE BOARD'S DOG PLAYS (kind x sport), flat 1u and at today's units")
POSTED = [r for r in DOGS if r.get("kind")]
by = defaultdict(list)
for r in POSTED:
    by[(r["kind"], r["league"])].append(r)
for (k, lg), rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
    pool = [r for r in DOGS if r["league"] == lg]
    c = D.cell(f"{k} / {lg}", rs)
    print(f"        placebo vs every {lg} dog: {D.placebo(rs, pool)} of 2,000")
    D.sched(f"        at today's units ({sorted({r.get('units') for r in rs if r.get('units')})})", [(r, r.get("units") or 0) for r in rs])
    if len(rs) >= 30:
        for b in D.BANDS:
            D.cell(f"      {b}", [r for r in rs if D.band(r) == b])
        D.cell("      home", [r for r in rs if home(r)])
        D.cell("      road", [r for r in rs if road(r)])
D.cell("EVERY POSTED DOG PLAY", POSTED)
D.sched("EVERY POSTED DOG PLAY at today's units", [(r, r.get("units") or 0) for r in POSTED])
for lg in LGS:
    D.sched(f"   {lg}", [(r, r.get("units") or 0) for r in POSTED if r["league"] == lg])
for b in D.BANDS:
    D.cell(f"   posted {b}", [r for r in POSTED if D.band(r) == b])
    D.sched(f"   posted {b} at today's units", [(r, r.get("units") or 0) for r in POSTED if D.band(r) == b])
D.cell("   posted home", [r for r in POSTED if home(r)])
D.cell("   posted road", [r for r in POSTED if road(r)])
for lg in LGS:
    D.cell(f"   posted {lg} home", [r for r in POSTED if home(r) and r["league"] == lg])
    D.cell(f"   posted {lg} road", [r for r in POSTED if road(r) and r["league"] == lg])

print("\n===== C. THE DOG SCORE, THE OWN READ, THE HONEST WEIGHED READ - every dog, by sport")
for lg in ("nhl", "nba", "nfl", "ncaaf"):
    d = [r for r in DOGS if r["league"] == lg]
    print(f"-- {lg}")
    for lo, hi in ((-99, -4), (-4, -2), (-2, 0), (0, 2), (2, 4), (4, 6), (6, 8), (8, 10), (10, 99)):
        rs = [r for r in d if lo <= sc(r) < hi]
        D.cell(f"   dog score {lo}..{hi}", rs)
    print("   the STUDY part alone (score - its own-read term)")
    for lo, hi in ((-99, -4), (-4, -2), (-2, 0), (0, 0.01), (0.01, 2), (2, 4), (4, 6), (6, 7)):
        rs = [r for r in d if r.get("dog_base") is not None and lo <= sc(r) - r["dog_base"] < hi]
        D.cell(f"   study part {lo}..{hi}", rs)
    print("   the OWN read over the no-vig close (points)")
    for lo, hi in ((-99, -3), (-3, -1), (-1, 0), (0, 1), (1, 2), (2, 4), (4, 8), (8, 99)):
        rs = [r for r in d if own_gap(r) is not None and lo <= own_gap(r) < hi]
        D.cell(f"   own - market {lo}..{hi}", rs)
    print("   the OWN read over the PRICE (cents on the dollar: under / thin 0-3 / 3+)")
    D.cell("   own read under the price", [r for r in d if own_edge(r) is not None and own_edge(r) < 0])
    D.cell("   own read 0-3 over (thin)", [r for r in d if own_edge(r) is not None and 0 <= own_edge(r) < 3 * 1])
    D.cell("   own read 3+ over", [r for r in d if own_edge(r) is not None and own_edge(r) >= 3])
    D.cell("   studies beat the price (weighed_dog_beats)", [r for r in d if r.get("wdb")])
    D.cell("   studies do NOT beat the price", [r for r in d if not r.get("wdb")])
    D.cell("   studies beat the price, home", [r for r in d if r.get("wdb") and home(r)])
    D.cell("   studies beat the price, road", [r for r in d if r.get("wdb") and road(r)])
    for b in D.BANDS:
        D.cell(f"   studies beat the price, {b}", [r for r in d if r.get("wdb") and D.band(r) == b])
    D.cell("   passes the Dog gate (dog_gate)", [r for r in d if r.get("dog_gate")])
    D.cell("   fighting", [r for r in d if r.get("fighting")])
    D.cell("   trap", [r for r in d if r.get("trap")])
    D.cell("   a named reason (after score_reason)", [r for r in d if r.get("n_reasons2")])
    D.cell("   no named reason", [r for r in d if not r.get("n_reasons2")])

print("\n===== D. THE LINE: the money left the dog (+) / came to it (-), open -> close no-vig points")
for lg in LGS:
    d = [r for r in DOGS if r["league"] == lg and r.get("drift") is not None]
    print(f"-- {lg} ({len(d)} dogs with an opener)")
    for lo, hi in ((-1, -.04), (-.04, -.02), (-.02, -.005), (-.005, .005), (.005, .02), (.02, .04), (.04, 1)):
        D.cell(f"   drift {100 * lo:+.1f}..{100 * hi:+.1f}", [r for r in d if lo <= r["drift"] < hi])

print("\n===== E. EARLY-SEASON: the dog team's games in (NBA: season_games; hockey / NBA from the parts' context)")
for lg in ("nba", "nhl", "ncaab"):
    d = [r for r in DOGS if r["league"] == lg]
    key = (lambda r: r["x"].get("season_games")) if lg == "nba" else (lambda r: r.get("games_in")) if lg == "ncaab" else (lambda r: r["x"].get("games_in", r["x"].get("season_games")))
    dd = [r for r in d if key(r) is not None]
    print(f"-- {lg} ({len(dd)} with a games count)")
    for lo, hi in ((0, 3), (3, 6), (6, 11), (11, 21), (21, 41), (41, 99)):
        D.cell(f"   games in {lo}..{hi - 1}", [r for r in dd if lo <= key(r) < hi])
        D.cell(f"      posted", [r for r in dd if lo <= key(r) < hi and r.get("kind")])
print("\n===== F. BY MONTH (the posted dog plays)")
for lg in LGS:
    for m in ("10", "11", "12", "01", "02", "03", "04"):
        rs = [r for r in POSTED if r["league"] == lg and r["date"][5:7] == m]
        if len(rs) >= 8:
            D.cell(f"   {lg} month {m}", rs)
