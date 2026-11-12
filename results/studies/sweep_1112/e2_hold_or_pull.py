"""11/12 SWEEP (a) - HOLD OR PULL: a football early dog we already hold at the first fair number, by what the money has
done by the SECOND look (the mid-week number - known today, so no look-ahead for a hold / pull call): the ticket's ROI
at the first fair price. College spot dogs under the live bar (the spot, the read not fighting, the weighed total 5+),
by spot; every college dog as the base. Train 2020-22 / held 2023-26. Reads the 11/11 early study's cached base table.
Usage: python results/studies/sweep_1112/e2_hold_or_pull.py > results/studies/sweep_1112/e2_hold_or_pull.out"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "early_1111"))
import base            # noqa: E402
import elib as E       # noqa: E402

se = E.se


def pl(r, o):
    return (E.dec(o) - 1) if r["won"] else -1.0


def bar(lg, r, f):
    if r["own"] is None or r["own"] < f[3] - se.SPOT_FIGHT:
        return False
    return se.spot_gap(lg, r["own"], f[3]) + sum(se.SPOT_WEIGHT[h] for h in base.spots(r, f)) >= se.SPOT_MIN_TOTAL


BK = (("came 4+ to the dog", lambda m: m >= 4), ("came 2-4", lambda m: 2 <= m < 4), ("inside 2 either way", lambda m: -2 < m < 2),
      ("ran 1+ away", lambda m: m <= -1), ("ran 2+ away", lambda m: m <= -2), ("ran 3+ away", lambda m: m <= -3))
for lg in ("ncaaf", "nfl"):
    rows = base.build(lg)
    for name, want in (("every dog +100..+350", None), ("blowout", "blowout"), ("bye", "bye"), ("any spot under the live bar", "any")):
        v = []
        for r in rows:
            f = base.first_fair(r)
            if not f or not 100 <= f[2] <= 350:
                continue
            sp = base.spots(r, f)
            if want == "any" and not (sp and bar(lg, r, f)):
                continue
            if want not in (None, "any") and not (want in sp and bar(lg, r, f)):
                continue
            later = [k for k in r["looks"] if k[0] < f[0]]
            if not later:
                continue
            k = later[0] if len(later) == 1 else later[len(later) // 2 - (0 if len(later) % 2 else 1)]   # the mid-week look
            v.append((r, f, (k[3] - f[3]) * 100, k))
        print(f"\n{lg} | {name}: {len(v)} tickets at the first fair price; the move by the next look")
        for bn, sel in BK:
            w = [(r, f, m, k) for r, f, m, k in v if sel(m)]
            if not w:
                continue
            tr = [x for x in w if x[0]["season"] <= 2022]
            he = [x for x in w if x[0]["season"] >= 2023]
            print(f"   {bn:22s} ticket {E.roi([pl(r, f[2]) for r, f, m, k in w])} | train {E.roi([pl(r, f[2]) for r, f, m, k in tr])} | held {E.roi([pl(r, f[2]) for r, f, m, k in he])}"
                  f" | the same side at the new number {E.mean([pl(r, k[2]) for r, f, m, k in w]) * 100:+6.1f}% | z wins vs the NEW price {E.zwin([(r['won'], k[3]) for r, f, m, k in w]):+.2f}")
