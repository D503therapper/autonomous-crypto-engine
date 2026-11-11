"""S6-S10 - the rest of the over / under list.
S6  neutral-site college hoops unders (the brother's watch: 54% last season)
S7  college football totals at altitude (4,600 ft+ home fields) - sides were dead, the total never asked
S8  NHL totals at altitude (Denver, Salt Lake City) + NFL totals in Denver
S9  MLB Coors Field totals (out of season - for the file)
S10 is the altitude floor special, or does ANY college floor's over / under history carry over? (walk-forward:
    a home floor's over record in all earlier seasons -> this season's over / under)"""
import random
import statistics
from collections import defaultdict

import lib

NC = [r for r in lib.load("ncaab") if r["tot"] is not None and r["hs"] is not None]
print("== S6 NEUTRAL-SITE COLLEGE HOOPS UNDERS")
neu = [r for r in NC if r["neu"]]
reg = [r for r in neu if (r.get("stype") or "2") == "2"]
lib.line("every neutral-site game UNDER", neu, "under")
lib.line("every neutral-site game OVER", neu, "over")
lib.line("regular season neutral UNDER", reg, "under")
lib.line("  Nov-Dec (the holiday events) UNDER", [r for r in reg if r["start"][5:7] in ("11", "12")], "under")
lib.line("  March (conference tournaments) UNDER", [r for r in reg if r["start"][5:7] == "03"], "under")
lib.line("postseason (NCAA / NIT...) UNDER", [r for r in neu if (r.get("stype") or "2") == "3"], "under")
for lo, hi in ((0, 135), (135, 145), (145, 155), (155, 999)):
    lib.line(f"  neutral, total {lo}-{hi} UNDER", [r for r in neu if lo <= r["tot"] < hi], "under")
lib.line("  2025-26 alone (the brother's 'last season')", [r for r in neu if r["season"] == 2025], "under")
home = [r for r in NC if not r["neu"]]
lib.line("the base: every home-floor game UNDER", home, "under")

print("\n== S7 COLLEGE FOOTBALL TOTALS AT ALTITUDE")
CF = [r for r in lib.load("ncaaf") if r["tot"] is not None and r["hs"] is not None and not r["neu"]]
he = lib.home_elev(CF)
for lo, hi in ((1400, 9999), (1220, 1400), (900, 1220), (0, 600)):
    rows = [r for r in CF if r["el"] is not None and lo <= r["el"] < hi]
    lib.line(f"home field {lo}-{hi} m OVER", rows, "over")
    lib.line(f"home field {lo}-{hi} m UNDER", rows, "under")
hi_ = [r for r in CF if (r["el"] or 0) >= 1400]
lib.line("1,400 m+, visitor from under 600 m OVER", [r for r in hi_ if he.get(r["away"], 9999) < 600], "over")
lib.line("1,400 m+, visitor a mountain team OVER", [r for r in hi_ if 1220 <= he.get(r["away"], 0)], "over")
nm = {}
for r in hi_:
    nm[r["home"]] = r["home_name"]
print("   by field:", "; ".join(
    f"{nm[t]} {sum(1 for r in hi_ if r['home'] == t)} "
    f"{100 * lib.stats([lib.bet(r, 'over') for r in hi_ if r['home'] == t])['roi']:+.0f}%" for t in nm
    if sum(1 for r in hi_ if r["home"] == t) >= 20))
print(f"   mean miss at 1,400 m+: {statistics.mean([r['hs'] + r['as'] - r['tot'] for r in hi_]):+.2f} pts "
      f"(every game {statistics.mean([r['hs'] + r['as'] - r['tot'] for r in CF]):+.2f})")

print("\n== S8 NHL / NFL TOTALS AT ALTITUDE")
for lg in ("nhl", "nfl"):
    X = [r for r in lib.load(lg) if r["tot"] is not None and r["hs"] is not None and not r["neu"]]
    for lo, hi in ((1220, 9999), (0, 600)):
        rows = [r for r in X if r["el"] is not None and lo <= r["el"] < hi]
        lib.line(f"{lg} home {lo}-{hi} m OVER", rows, "over")
        lib.line(f"{lg} home {lo}-{hi} m UNDER", rows, "under")
    a = [r for r in X if (r["el"] or 0) >= 1220]
    names = defaultdict(int)
    for r in a:
        names[r["home_name"]] += 1
    print(f"   {lg} altitude homes: {dict(names)}; mean miss "
          f"{statistics.mean([r['hs'] + r['as'] - r['tot'] for r in a]):+.2f} vs "
          f"{statistics.mean([r['hs'] + r['as'] - r['tot'] for r in X]):+.2f} everywhere")

print("\n== S9 MLB COORS FIELD TOTALS")
ML = [r for r in lib.load("mlb") if r["tot"] is not None and r["hs"] is not None and not r["neu"]]
co = [r for r in ML if (r["el"] or 0) >= 1400]
lib.line("Coors OVER", co, "over")
lib.line("Coors UNDER", co, "under")
for lab, f in (("Apr-May", ("04", "05")), ("Jun-Aug", ("06", "07", "08")), ("Sep-Oct", ("09", "10"))):
    lib.line(f"  Coors {lab} UNDER", [r for r in co if r["start"][5:7] in f], "under")
for lo, hi in ((0, 10.5), (10.5, 11.5), (11.5, 99)):
    lib.line(f"  Coors total {lo}-{hi} UNDER", [r for r in co if lo <= r["tot"] < hi], "under")
lib.line("the base: every other park OVER", [r for r in ML if (r["el"] or 0) < 1400], "over")

print("\n== S10 DOES ANY COLLEGE FLOOR'S OVER HISTORY CARRY OVER? (walk-forward, regular season home games)")
H = [r for r in home if (r.get("stype") or "2") == "2"]
hist = defaultdict(lambda: [0, 0, 0.0])               # floor -> overs, unders, sum of misses  (earlier seasons only)
cur = defaultdict(lambda: [0, 0, 0.0])
season = None
tagged = []
for r in H:
    if r["season"] != season:
        for t, v in cur.items():
            h = hist[t]
            h[0] += v[0]; h[1] += v[1]; h[2] += v[2]
        cur.clear()
        season = r["season"]
    h = hist[r["home"]]
    n = h[0] + h[1]
    if n >= 30:
        tagged.append((r, h[0] / n, h[2] / n, n))
    pts = r["hs"] + r["as"]
    c = cur[r["home"]]
    c[0] += pts > r["tot"]; c[1] += pts < r["tot"]; c[2] += pts - r["tot"]
print(f"   home games on a floor with 30+ priced games in earlier seasons: {len(tagged)}")
for lab, f in (("floor went over 58%+ before", lambda p, m: p >= 0.58), ("over 54-58%", lambda p, m: 0.54 <= p < 0.58),
               ("46-54%", lambda p, m: 0.46 <= p < 0.54), ("under 46% (an under floor)", lambda p, m: p < 0.46),
               ("mean miss +2.5 or more before", lambda p, m: m >= 2.5), ("mean miss -2.5 or less", lambda p, m: m <= -2.5)):
    rows = [r for r, p, m, n in tagged if f(p, m)]
    lib.line(f"{lab} OVER", rows, "over", train_to=2022)
    if "under" in lab or "-2.5" in lab:
        lib.line(f"{lab} UNDER", rows, "under", train_to=2022)
lo_ = [(r, p, m, n) for r, p, m, n in tagged if (r["el"] or 0) < 1220]
lib.line("LOW-GROUND floors only, over 58%+ before OVER", [r for r, p, m, n in lo_ if p >= 0.58], "over", train_to=2022)
lib.line("LOW-GROUND floors only, mean miss +2.5 before OVER", [r for r, p, m, n in lo_ if m >= 2.5], "over", train_to=2022)
lib.line("4,600 ft+ floors (whatever their history) OVER", [r for r, p, m, n in tagged if (r["el"] or 0) >= 1400], "over",
         train_to=2022)
lib.line("4,600 ft+ floors that ran UNDER 50% before OVER",
         [r for r, p, m, n in tagged if (r["el"] or 0) >= 1400 and p < 0.5], "over", train_to=2022)

print("\n== PLACEBO FOR THE 4,600 ft RULE: 500 random sets of home floors with the same number of floors (16+ games each)")
random.seed(1111)
real = [r for r in H if (r["el"] or 0) >= 1400]
floors = defaultdict(list)
for r in H:
    floors[r["home"]].append(r)
k = len({r["home"] for r in real if len(floors[r["home"]]) >= 16})
pool = [t for t, v in floors.items() if len(v) >= 60]
rs_all = lib.stats([lib.bet(r, "over") for r in real])
tr0 = lib.stats([lib.bet(r, "over") for r in real if r["season"] <= lib.TRAIN_TO])
bl0 = lib.stats([lib.bet(r, "over") for r in real if r["season"] > lib.TRAIN_TO])
hit = four = 0
best = -9
for _ in range(500):
    ts = random.sample(pool, k)
    bs = [(r["season"], lib.bet(r, "over")) for t in ts for r in floors[t]]
    a = lib.stats([p for _, p in bs])
    tr = lib.stats([p for s, p in bs if s <= lib.TRAIN_TO])
    bl = lib.stats([p for s, p in bs if s > lib.TRAIN_TO])
    best = max(best, a["roi"])
    hit += a["roi"] >= rs_all["roi"]
    four += tr["roi"] > 0 and bl["roi"] > 0 and bl["z"] >= 1.65
print(f"   the real {k} floors: all {100 * rs_all['roi']:+.1f}% z{rs_all['z']:+.1f}, train {100 * tr0['roi']:+.1f}%, blind "
      f"{100 * bl0['roi']:+.1f}% z{bl0['z']:+.1f}")
print(f"   random sets as good overall: {hit} of 500 (the best random set {100 * best:+.1f}%); random sets passing "
      f"train > 0 + blind > 0 + blind z 1.65: {four} of 500")
