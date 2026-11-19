"""THE 11/19 STUDY, PART 2 - the one family part 1 turned up (2+ starting offensive linemen out / 2+ MORE out than the
other side), pushed on every way it could be luck or a look-ahead:
  1. weeks 1-16 only (the last weeks hold teams RESTING healthy starters - nobody on an injury report)
  2. the men the report alone names (Out / Doubtful) vs the injured-reserve kind
  3. season by season
  4. the dose (the gap 0 / 1 / 2 / 3+), favorites and dogs apart
  5. the dog with 2+ more starting OL out: the bet on it, the favorite across at the close / a point worse / the first
     fair price, a placebo against random DOGS (not random games)
  6. both tackles, a tackle + an inside man, two inside men
  7. is it just the old 'more banged-up side' count? - the OL gap among games where the skill / defense count is level
Usage: python s2_ol_gap.py > s2_ol_gap.out"""
import random
from collections import defaultdict

import numpy as np

import olib

rows = olib.build()
N = [0]


def line(name, sel, fade=True):
    N[0] += 1
    if len(sel) < 15:
        print(f"  {name:62s} {len(sel)} - too few")
        return
    print(f"  {name:62s} {olib.vs_price(sel)}")
    print(f"  {'':62s}   {'FADE' if fade else 'BACK'} ML  {olib.cell(olib.ml(sel, fade=fade))[0]}")
    print(f"  {'':62s}   {'FADE' if fade else 'BACK'} ATS {olib.cell(olib.ats(sel, fade=fade))[0]}")


gap = lambda r: r["ol"] - r["o_ol"]                          # noqa: E731
print("=== 1. WEEKS 1-16 ONLY (no rested starters)")
early = [r for r in rows if r["week"] <= 16]
line("2+ starting OL out", [r for r in early if r["ol"] >= 2])
line("2+ MORE starting OL out than the other side", [r for r in early if gap(r) >= 2])
line("...weeks 17-18 only", [r for r in rows if r["week"] > 16 and gap(r) >= 2])

print("\n=== 2. WHO SAYS HE'S OUT")
line("2+ OL out, all named Out / Doubtful on the report", [r for r in rows if r["r_ol"] >= 2])
line("2+ OL out, at least one of them the injured-reserve kind", [r for r in rows if r["ol"] >= 2 and r["r_ol"] < r["ol"]])
line("2+ MORE out, counting the report's men only", [r for r in rows if r["r_ol"] - r["r_o_ol"] >= 2])

print("\n=== 3. SEASON BY SEASON - 2+ MORE starting OL out than the other side (the side with the hole)")
by = defaultdict(list)
for r in rows:
    if gap(r) >= 2:
        by[r["season"]].append(r)
for y in sorted(by):
    s = by[y]
    m = olib.roi(olib.ml(s))
    a = olib.roi(olib.ats(s))
    print(f"  {y}: {len(s):3d} games, the side won {100 * np.mean([r['win'] for r in s]):5.1f}% vs the close's {100 * np.mean([r['p'] for r in s]):5.1f}%"
          f" | fade ML {m['roi']:+6.1f}% | fade ATS {a['roi']:+6.1f}%")

print("\n=== 4. THE DOSE - the gap in starting OL out (ours minus theirs)")
for name, pred in (("-2 or less (THEY are the thin line)", lambda g: g <= -2), ("-1", lambda g: g == -1), ("0", lambda g: g == 0), ("+1", lambda g: g == 1),
                   ("+2", lambda g: g == 2), ("+3 or more", lambda g: g >= 3)):
    sel = [r for r in rows if pred(gap(r))]
    sp = [r["margin"] - r["sp"] for r in sel if r["sp"] is not None]
    print(f"  gap {name:36s} {olib.vs_price(sel)}   margin vs the spread {np.mean(sp):+.2f}")
print("  ...favorites (priced under even) with the gap +2 or more:")
line("favorite, 2+ more OL out", [r for r in rows if gap(r) >= 2 and r["d"] < 2.0])
print("  ...dogs +100..+350:")
dogs = [r for r in rows if 2.0 <= r["d"] <= 4.5]
line("dog, 2+ more OL out (the bet ON the dog)", [r for r in dogs if gap(r) >= 2], fade=False)
line("dog, 1 more OL out (the bet ON the dog)", [r for r in dogs if gap(r) == 1], fade=False)
line("dog, level (the bet ON the dog)", [r for r in dogs if gap(r) == 0], fade=False)
line("dog, the FAVORITE has 1+ more OL out (the bet ON the dog)", [r for r in dogs if gap(r) <= -1], fade=False)

print("\n=== 5. THE DOG WITH 2+ MORE STARTING OL OUT - every price")
sel = [r for r in dogs if gap(r) >= 2]
back = olib.ml(sel, fade=False)
c = olib.roi(back)
pool = [x[1] for x in olib.ml(dogs, fade=False)]
rnd = random.Random(11)
k = sum(1 for _ in range(2000) if 100 * np.mean(rnd.sample(pool, c["n"])) <= c["roi"])
print(f"  the bet ON it at the close: {olib.cell(back)[0]} | {k}/2000 random sets of {c['n']} DOGS did as badly")
print(f"  the FAVORITE across, ML at the close:   {olib.cell(olib.ml(sel))[0]}")
print(f"  the FAVORITE across, a point worse:     {olib.cell(olib.ml(sel, worse=0.01))[0]}")
print(f"  the FAVORITE across, the spread:        {olib.cell(olib.ats(sel))[0]}")
print(f"  the FAVORITE across, a point worse ATS: {olib.cell(olib.ats(sel, worse=1.0))[0]}")
ff = [r for r in sel if r["ff_d"]]
print(f"  the bet ON it at the FIRST FAIR price:  {olib.cell(olib.ml(ff, fade=False, key=('ff_d', 'ff_d_opp')))[0]}")
if ff:
    mv = [1 / r["d"] / (1 / r["d"] + 1 / r["d_opp"]) - 1 / r["ff_d"] / (1 / r["ff_d"] + 1 / r["ff_d_opp"]) for r in ff]
    print(f"     (2020-26: the dog's price moved {100 * np.mean(mv):+.1f} points of win chance from the first fair price to the close - the market moves AGAINST it, not far enough)")
allg = [r for r in rows if gap(r) >= 2]
pool = [x[1] for x in olib.ats(rows)]
c = olib.roi(olib.ats(allg))
print(f"  every side with 2+ more OL out, fade ATS: placebo {olib.placebo(pool, c['n'], c['roi'])}/2000;  a point worse: {olib.cell(olib.ats(allg, worse=1.0))[0]}")
print(f"  ...fade ATS a HALF point worse:  {olib.cell(olib.ats(allg, worse=0.5))[0]}")
ffs = [r for r in allg if r["ff_sp"] is not None]
print(f"  ...fade at the FIRST FAIR spread: {olib.cell(olib.ats(ffs, key='ff_sp'))[0]}   (the number moved {np.mean([r['sp'] - r['ff_sp'] for r in ffs if r['sp'] is not None]):+.2f} pts against the thin line by the close)")

print("\n=== 6. WHICH MEN")
line("BOTH starting tackles out", [r for r in rows if r["t"] >= 2])
line("a tackle + an inside man (G / C) out", [r for r in rows if r["t"] == 1 and r["int"] >= 1])
line("two inside men out, both tackles in", [r for r in rows if r["t"] == 0 and r["int"] >= 2])
line("exactly 1 tackle out, the inside whole", [r for r in rows if r["t"] == 1 and r["int"] == 0])
line("exactly 1 inside man out, tackles whole", [r for r in rows if r["t"] == 0 and r["int"] == 1])

print("\n=== 7. IS IT JUST 'THE MORE BANGED-UP SIDE'? - 2+ more OL out, split by the rest of the unseen starters (DB + DL + LB + TE)")
rest = lambda r: (r["db"] + r["dl"] + r["lb"] + r["te"]) - (r["o_db"] + r["o_dl"] + r.get("o_lb", 0) + r.get("o_te", 0))   # noqa: E731
line("2+ more OL out, the rest level or better for us", [r for r in rows if gap(r) >= 2 and (r["db"] + r["dl"]) - (r["o_db"] + r["o_dl"]) <= 0])
line("2+ more OL out, the rest worse for us too", [r for r in rows if gap(r) >= 2 and (r["db"] + r["dl"]) - (r["o_db"] + r["o_dl"]) >= 1])
line("OL level, 2+ more DB / DL out", [r for r in rows if gap(r) == 0 and (r["db"] + r["dl"]) - (r["o_db"] + r["o_dl"]) >= 2])
print(f"\n{N[0]} more cells looked at")
