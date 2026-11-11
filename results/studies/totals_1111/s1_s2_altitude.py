"""S1 + S2 - THE COLLEGE HOOPS ALTITUDE OVER the way the brother's engine bets it: the road team at one of seven home
floors 4,600+ ft up, the OVER at the close, every game, no other read. Then the dose / who / when cuts and a placebo."""
import random
import statistics
from collections import defaultdict

import lib

G = [r for r in lib.load("ncaab") if (r.get("stype") or "2") == "2"]
HE = lib.home_elev(G)
NAME = {}
for r in G:
    NAME[r["home"]] = r["home_name"]
P = [r for r in G if r["tot"] is not None and r["hs"] is not None]
GRIM = ("Air Force", "Colorado", "Colorado St", "New Mexico", "Wyoming", "Montana St", "Utah State")
print(f"priced regular-season finals: {len(P)}  seasons {P[0]['season']}-{P[-1]['season']}")
print("the seven floors (m / ft):", ", ".join(
    f"{n} {HE[t]:.0f}/{HE[t] * lib.FT:.0f}" for t, n in NAME.items() if n in GRIM))
home = [r for r in P if not r["neu"]]

print("\n== S1 THE BROTHER'S RULE: the seven floors, every home game, the over at the close")
g7 = [r for r in home if r["home_name"] in GRIM]
res = lib.line("7 floors OVER", g7, "over")
lib.line("7 floors UNDER", g7, "under")
miss = [r["hs"] + r["as"] - r["tot"] for r in g7]
print(f"   mean miss {statistics.mean(miss):+.2f} pts, median {statistics.median(miss):+.1f}; every priced home game "
      f"{statistics.mean([r['hs'] + r['as'] - r['tot'] for r in home]):+.2f}")
lib.line("every home game OVER (the base)", home, "over")

print("\n== PLACEBO: 500 random sets of 7 home floors (each 60+ priced home games), the same test")
cnt = defaultdict(int)
for r in home:
    cnt[r["home"]] += 1
pool = [t for t, n in cnt.items() if n >= 60]
byh = defaultdict(list)
for r in home:
    byh[r["home"]].append(r)
random.seed(1111)
real_bl, real_all = res["blind"], res["all"]
hit_all = hit_bl = hit_four = 0
rois = []
for _ in range(500):
    ts = random.sample(pool, 7)
    bs = [(r["season"], lib.bet(r, "over")) for t in ts for r in byh[t]]
    tr = lib.stats([p for s, p in bs if s <= lib.TRAIN_TO])
    bl = lib.stats([p for s, p in bs if s > lib.TRAIN_TO])
    rois.append(bl["roi"])
    hit_bl += bl["roi"] >= real_bl["roi"]
    hit_four += tr["roi"] > 0 and bl["roi"] > 0 and bl["z"] >= 1.65
    hit_all += lib.stats([p for _, p in bs])["z"] >= real_all["z"]
print(f"   pool {len(pool)} floors; random blind ROI mean {100 * statistics.mean(rois):+.1f}% sd "
      f"{100 * statistics.pstdev(rois):.1f}%, best {100 * max(rois):+.1f}%")
print(f"   random sets with blind ROI >= the real {100 * real_bl['roi']:+.1f}%: {hit_bl} of 500; with all-seasons z >= "
      f"{real_all['z']:.1f}: {hit_all} of 500; passing train>0 + blind>0 + blind z 1.65: {hit_four} of 500")

print("\n== S2a BY ELEVATION (every home floor, not just the seven)")
for lo, hi in ((1200, 99999), (1400, 99999), (1600, 99999), (1200, 1400), (1400, 1600), (1600, 2000), (2000, 99999),
               (900, 1200), (600, 900), (0, 600)):
    rows = [r for r in home if r["el"] is not None and lo <= r["el"] < hi]
    lib.line(f"home floor {lo}-{hi if hi < 9999 else ''} m OVER", rows, "over")

print("\n== S2b BY ARENA (home floors 1,200 m+, 40+ priced games)")
alt = [r for r in home if r["el"] is not None and r["el"] >= 1200]
for t in sorted({r["home"] for r in alt}, key=lambda t: -HE.get(t, 0)):
    rows = [r for r in alt if r["home"] == t]
    if len(rows) >= 40:
        lib.line(f"{NAME[t]} ({HE[t] * lib.FT:,.0f} ft){' *' if NAME[t] in GRIM else ''}", rows, "over")
not7 = [r for r in alt if r["home_name"] not in GRIM and HE.get(r["home"], 0) >= 1200]
lib.line("1,200 m+ floors NOT in the seven", not7, "over")
lib.line("1,400 m+ floors NOT in the seven", [r for r in not7 if r["el"] >= 1400], "over")

print("\n== S2c BY THE VISITOR'S OWN HOME (the seven floors / every 1,220 m+ floor)")
for nm, base in (("7", g7), ("1220+", [r for r in home if (r["el"] or 0) >= 1220])):
    for lab, f in (("visitor from under 300 m", lambda e: e < 300), ("visitor 300-900 m", lambda e: 300 <= e < 900),
                   ("visitor from under 900 m", lambda e: e < 900), ("visitor 900-1,219 m", lambda e: 900 <= e < 1220),
                   ("visitor a mountain team 1,220 m+", lambda e: e >= 1220)):
        lib.line(f"[{nm}] {lab} OVER", [r for r in base if r["away"] in HE and f(HE[r["away"]])], "over")
    lib.line(f"[{nm}] visitor's home unknown (non-D1) OVER", [r for r in base if r["away"] not in HE], "over")

print("\n== S2d BY THE TOTAL (the seven / 1,220 m+)")
for nm, base in (("7", g7), ("1220+", [r for r in home if (r["el"] or 0) >= 1220])):
    for lo, hi in ((0, 135), (135, 145), (145, 155), (155, 999), (0, 145), (145, 999)):
        lib.line(f"[{nm}] total {lo}-{hi} OVER", [r for r in base if lo <= r["tot"] < hi], "over")

print("\n== S2e EARLY vs LATE (the seven / 1,220 m+): the month, and how many games both teams have played")
played = defaultdict(int)
gp = {}
for r in G:                                   # every final, in time order: games played BEFORE this one
    if r["hs"] is None:
        continue
    gp[r["id"]] = (played[(r["season"], r["home"])], played[(r["season"], r["away"])])
    played[(r["season"], r["home"])] += 1
    played[(r["season"], r["away"])] += 1
for nm, base in (("7", g7), ("1220+", [r for r in home if (r["el"] or 0) >= 1220])):
    for lab, f in (("November", lambda r: r["start"][5:7] == "11"), ("December", lambda r: r["start"][5:7] == "12"),
                   ("Jan-Mar", lambda r: r["start"][5:7] in ("01", "02", "03")),
                   ("a team under 5 games in (our built play can't fire)", lambda r: min(gp[r["id"]]) < 5),
                   ("both 5+ games in", lambda r: min(gp[r["id"]]) >= 5),
                   ("the home team's games 1-3", lambda r: gp[r["id"]][0] < 3),
                   ("November, both 5+ in", lambda r: r["start"][5:7] == "11" and min(gp[r["id"]]) >= 5)):
        lib.line(f"[{nm}] {lab} OVER", [r for r in base if f(r)], "over")

print("\n== S2f BY THE OVER'S PRICE (1,220 m+): is the juice already leaning?")
a1220 = [r for r in home if (r["el"] or 0) >= 1220]
for lab, f in (("over -105 or better", lambda o: o > -106), ("over -106..-112", lambda o: -112 <= o <= -106),
               ("over -113..-125", lambda o: -125 <= o <= -113), ("over worse than -125", lambda o: o < -125)):
    lib.line(f"{lab}", [r for r in a1220 if f(lib.num(r.get("over_odds")) or -110)], "over")
