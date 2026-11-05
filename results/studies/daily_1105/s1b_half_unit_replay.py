"""S1 (part B) - THE ½u LONGSHOT LEAK in the replay: the 11/4 (c15) board (results/studies/plays_every_day_1104/
sim_volume.py - the WIRED floor: floor v2 + NBA floor + hockey named reason, college hoops out of the general floor)
re-built day by day from the 10/30 funnel rows (1,097 board days 2023-26 + live 10/13-10/29, closing prices).
Every ½u DOG play it makes (floor / NBA floor / runner-up dog / ½u Dog / value play) broken down by price, league,
dog score, the own read over the market (gap), thin; train (to 2025-06-30) vs held out (2025-07-01 on).
Then: how likely is the live ½u-dog record (sum of plays) if the replay's ROI is the truth (a bootstrap of 23 plays).
Then the coordinator's ask: hockey dogs by dog score band - all NHL dogs +100..+350 clean, and the floor's own picks."""
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, "results/studies/plays_every_day_1104")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "results/studies/plays_every_day_1104"))
import sim_volume as sv  # noqa: E402

KW = dict(floor_on=True, hk_named=True, floor_leagues=("nhl", "mlb", "nfl"))
plays = []
for d in sv.days:
    for r, u, k in sv.build(d, **KW):
        plays.append((d, r, u, k))

IN_SEASON = ("nhl", "nba", "nfl", "ncaaf", "ncaab")


def row(name, ps):
    if not ps:
        print(f"{name:52s} -")
        return
    out = {}
    for h in ("train", "held", "live"):
        q = [x for x in ps if sv.half(x[0]) == h]
        st = sum(u for _, _, u, _ in q)
        pr = sum(sv.pnl(r, u) for _, r, u, _ in q)
        w = sum(r["result"] == "won" for _, r, _, _ in q)
        out[h] = (len(q), w, pr, st)
    st = sum(u for _, _, u, _ in ps)
    pr = sum(sv.pnl(r, u) for _, r, u, _ in ps)
    w = sum(r["result"] == "won" for _, r, _, _ in ps)
    seas = defaultdict(float)
    for d, r, u, _ in ps:
        seas[sv.season(d)] += sv.pnl(r, u)
    up = f"{sum(v > 0 for v in seas.values())}/{len(seas)}"

    def f(t):
        n, w_, p_, s_ = t
        return f"{w_:3d}-{n-w_:<3d} {p_/s_*100 if s_ else 0:+6.1f}%" if n else "   -          "
    print(f"{name:52s} {w:4d}-{len(ps)-w:<4d} {pr:+7.1f}u {pr/st*100:+6.1f}% | train {f(out['train'])} | held "
          f"{f(out['held'])} | live {f(out['live'])} | seasons up {up}")


half_dogs = [x for x in plays if x[2] == 0.5 and x[1]["odds"] > 0]
half_dogs_in = [x for x in half_dogs if x[1]["league"] in IN_SEASON]
print("THE (c15) BOARD - every ½u DOG unit play (all sports incl. MLB) and the in-season sports only")
row("½u dogs, all", half_dogs)
row("½u dogs, NFL/NCAAF/NHL/NBA/NCAAB", half_dogs_in)
row("½u favorites, all", [x for x in plays if x[2] == 0.5 and x[1]["odds"] < 0])
row("2u dogs", [x for x in plays if x[2] == 2.0 and x[1]["odds"] > 0])
print("\nby kind (½u dogs, in-season)")
for k in sorted({x[3] for x in half_dogs_in}):
    row(f"  kind {k}", [x for x in half_dogs_in if x[3] == k])
print("by league")
for lg in IN_SEASON + ("mlb",):
    row(f"  {lg}", [x for x in half_dogs if x[1]["league"] == lg])
print("by price (in-season)")
for lo, hi in ((100, 129), (130, 159), (160, 199), (200, 249), (250, 350)):
    row(f"  +{lo}..+{hi}", [x for x in half_dogs_in if lo <= x[1]["odds"] <= hi])
print("by dog score (in-season)")
for lo, hi in ((-99, 0), (0, 2), (2, 4), (4, 6), (6, 99)):
    row(f"  score {lo}..{hi}", [x for x in half_dogs_in if x[1].get("dog_score") is not None and lo <= x[1]["dog_score"] < hi])
print("by the own read over the no-vig market (gap, points, in-season)")
for lo, hi in ((-99, 0), (0, 1), (1, 2), (2, 4), (4, 99)):
    row(f"  gap {lo}..{hi}", [x for x in half_dogs_in if sv.gap(x[1]) is not None and lo <= sv.gap(x[1]) < hi])
print("thin / not thin (in-season)")
row("  thin", [x for x in half_dogs_in if x[1].get("thin")])
row("  not thin", [x for x in half_dogs_in if not x[1].get("thin")])
print("home / road (in-season)")
row("  home", [x for x in half_dogs_in if x[1]["home"]])
row("  road", [x for x in half_dogs_in if not x[1]["home"]])

# ---------------- is the live record out of line? bootstrap from the replay's in-season ½u dogs (train + held)
pool = [sv.pnl(r, 1.0) for d, r, u, k in half_dogs_in if sv.half(d) != "live"]
random.seed(1105)
for n, live_roi, label in ((30, -0.24, "live ½u dogs 9/27-11/4: 10-20 -24.0%"),
                           (23, -0.39, "live ½u dogs 10/13-11/4 (floor era): 6-17 -39.0%"),
                           (18, -0.63, "the owner's '3-15' (-5.7u on 9u)")):
    sims = [sum(random.choice(pool) for _ in range(n)) / n for _ in range(20000)]
    pr = sum(s <= live_roi for s in sims) / len(sims)
    print(f"\nBOOTSTRAP {label}: replay pool {len(pool)} plays at {sum(pool)/len(pool)*100:+.1f}%; "
          f"P(a {n}-play stretch at {live_roi*100:+.0f}% or worse) = {pr*100:.1f}%")
# the worst 23-play running stretch inside the replay itself
seq = [sv.pnl(r, 1.0) for d, r, u, k in sorted(half_dogs_in, key=lambda x: x[0]) if sv.half(d) != "live"]
worst = min(sum(seq[i:i + 23]) / 23 for i in range(len(seq) - 23))
print(f"the replay's own worst 23-play stretch of ½u dogs (in-season): {worst*100:+.1f}%")
cnt = sum(1 for i in range(len(seq) - 23) if sum(seq[i:i + 23]) / 23 <= -0.39)
print(f"23-play windows at -39% or worse inside the replay: {cnt} of {len(seq) - 23}")

# ---------------- the coordinator's ask: hockey dogs by dog score
print("\nHOCKEY DOGS +100..+350, every clean side in the rows (not just the board), by dog score")
allh = [(r["date"], r, 1.0, "side") for d in sv.days for r in sv.by_day[d]
        if r["league"] == "nhl" and 100 <= r["odds"] <= 350 and sv.clean(r) and r.get("dog_score") is not None]
allh_any = [(r["date"], r, 1.0, "side") for d in sv.days for r in sv.by_day[d]
            if r["league"] == "nhl" and 100 <= r["odds"] <= 350 and r.get("dog_score") is not None
            and not r["trap"] and not r["fighting"]]
for lo, hi in ((-99, 0), (0, 3), (3, 6), (0, 6), (6, 99)):
    row(f"  clean NHL dog, score {lo}..{hi}", [x for x in allh if lo <= x[1]["dog_score"] < hi])
for lo, hi in ((-99, 0), (0, 3), (3, 6), (0, 6), (6, 99)):
    row(f"  NHL dog (no trap / not fighting), score {lo}..{hi}", [x for x in allh_any if lo <= x[1]["dog_score"] < hi])
print("the board's hockey ½u dog plays, by dog score")
hk = [x for x in half_dogs if x[1]["league"] == "nhl"]
for lo, hi in ((-99, 0), (0, 3), (3, 6), (0, 6), (6, 99)):
    row(f"  board NHL ½u dog, score {lo}..{hi}", [x for x in hk if x[1].get("dog_score") is not None and lo <= x[1]["dog_score"] < hi])
print("the board's hockey floor plays only, by dog score")
hkf = [x for x in hk if x[3] in ("floor", "floorfb")]
for lo, hi in ((-99, 0), (0, 3), (3, 6), (0, 6), (6, 99)):
    row(f"  NHL floor, score {lo}..{hi}", [x for x in hkf if lo <= x[1]["dog_score"] < hi])
print("the board's hockey floor plays by price")
for lo, hi in ((100, 129), (130, 159), (160, 350)):
    row(f"  NHL floor +{lo}..+{hi}", [x for x in hkf if lo <= x[1]["odds"] <= hi])
