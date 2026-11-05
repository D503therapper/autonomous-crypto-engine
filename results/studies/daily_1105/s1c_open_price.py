"""S1 (part C) - the second check on the replay's ½u dogs: the replay grades at the CLOSE, the live board bets at the
8 AM price. Re-grade the same (c15) ½u dog plays at the game file's OPENING price (ml_home_open / ml_away_open - the
earliest number, the far side of the 8 AM look from the close) where it exists. If the replay's profit only lives at
the close, the live board (which bets earlier) can't have it."""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402  (chdir to ROOT)
sys.path.insert(0, os.path.join(lib.ROOT, "results/studies/plays_every_day_1104"))
import sim_volume as sv  # noqa: E402

KW = dict(floor_on=True, hk_named=True, floor_leagues=("nhl", "mlb", "nfl"))
idx = {}
for lg in ("nhl", "nba", "nfl", "ncaaf"):
    for g in lib.finals(lg):
        for dd in (0, -1):
            day = (lib._t(g["start"]) + lib.timedelta(hours=-8, days=dd)).strftime("%Y-%m-%d")
            idx.setdefault((lg, day, g["hn"]), (g, "home"))
            idx.setdefault((lg, day, g["an"]), (g, "away"))
res = defaultdict(lambda: [0, 0.0, 0.0, 0])
for d in sv.days:
    for r, u, k in sv.build(d, **KW):
        if u != 0.5 or r["odds"] <= 0 or r["league"] not in ("nhl", "nba", "nfl", "ncaaf"):
            continue
        hit = None
        for nm in (r["team"],):
            for key in ((r["league"], d, nm),):
                if key in idx:
                    hit = idx[key]
        if not hit:
            # names in the rows are short ("Rangers"); the game files carry the full name - match on the tail
            for (lg, day, nm), v in idx.items():
                pass
            continue
        g, side = hit
        o = g["oh"] if side == "home" else g["oa"]
        c = g["mlh"] if side == "home" else g["mla"]
        if not o:
            continue
        won = r["result"] == "won"
        for tag, price in (("close", c), ("open", o), ("rows' price", r["odds"])):
            x = res[(r["league"], sv.half(d), tag)]
            x[0] += 1
            x[1] += lib.profit(won, lib.dec(price))
            x[3] += won
print("½u dogs of the (c15) board re-graded at the open vs the close (rows matched to the game files by date + name)")
for k in sorted(res):
    n, p, _, w = res[k]
    print(f"  {k[0]:6s} {k[1]:6s} {k[2]:12s} {w:3d}-{n-w:<3d} {p/n*100:+6.1f}%")
tot = defaultdict(lambda: [0, 0.0])
for (lg, h, tag), (n, p, _, w) in res.items():
    tot[(h, tag)][0] += n
    tot[(h, tag)][1] += p
for k in sorted(tot):
    print(f"  ALL {k[0]:6s} {k[1]:12s} n {tot[k][0]:4d} {tot[k][1]/tot[k][0]*100:+6.1f}%")
