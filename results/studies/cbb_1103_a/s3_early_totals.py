"""STUDY 3 - TOTALS IN THE FIRST MONTH (pace unknown): is the early-season college hoops total mispriced? ESPN's closing
total + over / under odds 2018-25. The over and the under by phase (opening week / both teams' games 1-3 / 1-5 /
the rest of November / December+), by total size (under 135 / 135-150 / 150+), neutral floors, and the mean miss
(points scored minus the total) - a biased early number shows up there before it shows in ROI.
Train 2018-22, held out 2023 / 24 / 25 apart."""
import lib
from collections import defaultdict

rows = [r for r in lib.annotate(lib.load()) if r["season"] >= 2018]
cells = defaultdict(lib.Cell)
miss = defaultdict(list)
for r in rows:
    try:
        t = float(r["total"])
    except (TypeError, ValueError):
        continue
    oo = lib.fnum(r.get("over_odds")) or -110.0
    uo = lib.fnum(r.get("under_odds")) or -110.0
    if abs(oo) < 100 or abs(uo) < 100:
        oo = uo = -110.0
    pts = r["hs"] + r["as_"]
    s = r["season"]
    d = r["day_in_season"]
    g = max(r["gn_home"], r["gn_away"])
    phases = []
    if d <= 7:
        phases.append("opening week")
    if g <= 3:
        phases.append("games 1-3")
    if g <= 5:
        phases.append("games 1-5")
    if g > 5 and r["dt"].month == 11:
        phases.append("Nov, games 6+")
    if r["dt"].month not in (11,):
        phases.append("Dec+")
    size = "total <135" if t < 135 else ("total 135-150" if t <= 150 else "total 150+")
    neutral = str(r["neutral"]) == "1"
    for ph in phases:
        miss[(ph, "held" if s in lib.HELD else "train")].append(pts - t)
        for lab in (ph, f"{ph} | {size}") + ((f"{ph} | neutral",) if neutral else ()):
            cells[f"OVER  {lab}"].add(s, lib.ats_profit(pts - t, oo))
            cells[f"UNDER {lab}"].add(s, lib.ats_profit(t - pts, uo))
print(__doc__)
print("mean miss (points scored - total):")
for k in sorted(miss):
    xs = miss[k]
    print(f"  {k[0]:15} {k[1]:5} n={len(xs):6} mean {sum(xs) / len(xs):+.2f}  over share {sum(x > 0 for x in xs) / len(xs):.3f}")
for k in sorted(cells):
    print(cells[k].line(k))
