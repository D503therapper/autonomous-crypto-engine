"""S5b - EACH SPOT UNDER THE LIVE BAR, in the paid history (first fair number, the median book): the dog has the spot,
the engine's read isn't fighting it (own >= price - 1), and the read's gap (capped at 5 in college, a 12+ gap counts
nothing in the NFL - sports_early.spot_gap) plus the spot's weight clears SPOT_MIN_TOTAL. No fades / lead weights /
injuries (not in the history) - said plainly. ROI at the first fair number and at the close, the move, every season.
S6c - THE MONEY-LEFT WEIGHT, tested the way it would be wired: a dog +100..+350 at the second early look whose price
has run 2+ points AWAY since the first fair number, against the dogs that stayed inside a point. Every season, both
leagues, and a placebo: the same number of second-look dogs drawn at random 2,000 times (how often does a random set
lose as much). Then the same for the spot dogs, and the first 24 hours on our own tape this season."""
import random

import base
import elib as E

out = E.Tee("s5b_s6c_out.txt")
se = E.se
ROWS = {lg: base.build(lg) for lg in ("nfl", "ncaaf")}


def pl(r, o):
    return (E.dec(o) - 1) if r["won"] else -1.0


out("=" * 30, "S5b - EACH SPOT UNDER THE LIVE BAR (first fair number)")
for lg in ("nfl", "ncaaf"):
    for spot in ("bye", "mnf", "eastwest", "blowout"):
        if lg not in se.SPOTS[spot][2]:
            continue
        v = []
        for r in ROWS[lg]:
            f = base.first_fair(r)
            if not f or r["own"] is None or spot not in base.spots(r, f):
                continue
            if r["own"] < f[3] - se.SPOT_FIGHT:
                continue
            tot = se.spot_gap(lg, r["own"], f[3]) + sum(se.SPOT_WEIGHT[h] for h in base.spots(r, f))
            if tot < se.SPOT_MIN_TOTAL:
                continue
            v.append((r, f))
        if len(v) < 10:
            out(f" {lg} {spot}: n {len(v)}")
            continue
        m = [(r["close_p"] - f[3]) * 100 for r, f in v]
        out(f"\n {lg} | {spot}: {len(v)} dogs clear the live bar | the move to the close {E.mean(m):+.2f} pts (t {E.tstat(m):+.1f})")
        for tag, sel in (("ALL", lambda s: True), ("TRAIN 2020-22", lambda s: s <= 2022), ("HELD 2023-26", lambda s: s >= 2023)):
            w = [(r, f) for r, f in v if sel(r["season"])]
            if w:
                out(f"   {tag:14s} first fair {E.roi([pl(r, f[2]) for r, f in w])} | close "
                    f"{E.mean([pl(r, r['close_o']) for r, f in w]) * 100:+6.1f}% | z vs the price "
                    f"{E.zwin([(r['won'], f[3]) for r, f in w]):+.2f}")
        bys = {}
        for r, f in v:
            bys.setdefault(r["season"], []).append(pl(r, f[2]))
        out("   by season: " + "  ".join(f"{s} {sum(1 for x in p if x > 0)}-{sum(1 for x in p if x < 0)} {E.mean(p) * 100:+.0f}%"
                                         for s, p in sorted(bys.items())))

out("\n" + "=" * 30, "S6c - THE MONEY-LEFT WEIGHT (the second early look, 1.5+ days out; dog +100..+350 there)")
rnd = random.Random(11)
pool_all = {}
for lg in ("nfl", "ncaaf", "both"):
    for nm, spot_only in (("every dog", False), ("spot dogs (bye / Monday night / East-West / blowout)", True)):
        pop = []
        for l2 in (("nfl", "ncaaf") if lg == "both" else (lg,)):
            for r in ROWS[l2]:
                ff = base.first_fair(r)
                if not ff:
                    continue
                later = [k for k in base.early_looks(r) if k[0] < ff[0]]
                if not later or not 100 <= later[0][2] <= 350:
                    continue
                k = later[0]
                if spot_only and not [s for s in base.spots(r, k, ff) if s != "hammered"]:
                    continue
                pop.append((r, k, (k[3] - ff[3]) * 100))
        away = [(r, k) for r, k, m in pop if m <= -2]
        flat = [(r, k) for r, k, m in pop if -1 < m < 1]
        a = [pl(r, k[2]) for r, k in away]
        fl = [pl(r, k[2]) for r, k in flat]
        if len(a) < 15:
            continue
        out(f"\n {lg} | {nm}: {len(pop)} second-look dogs")
        out(f"   ran AWAY 2+ pts since the first fair number: {E.roi(a)} | z vs the price "
            f"{E.zwin([(r['won'], k[3]) for r, k in away]):+.2f} | TRAIN {E.roi([pl(r, k[2]) for r, k in away if r['season'] <= 2022])} | "
            f"HELD {E.roi([pl(r, k[2]) for r, k in away if r['season'] >= 2023])}")
        out(f"   stayed inside a point:                      {E.roi(fl)} | z vs the price "
            f"{E.zwin([(r['won'], k[3]) for r, k in flat]):+.2f} | TRAIN {E.roi([pl(r, k[2]) for r, k in flat if r['season'] <= 2022])} | "
            f"HELD {E.roi([pl(r, k[2]) for r, k in flat if r['season'] >= 2023])}")
        bys = {}
        for r, k in away:
            bys.setdefault(r["season"], []).append(pl(r, k[2]))
        out("   ran-away by season: " + "  ".join(f"{s} {sum(1 for x in p if x > 0)}-{sum(1 for x in p if x < 0)} {E.mean(p) * 100:+.0f}%"
                                                  for s, p in sorted(bys.items()))
            + f"   (seasons down {sum(1 for p in bys.values() if sum(p) < 0)} of {len(bys)})")
        allp = [pl(r, k[2]) for r, k, m in pop]
        tgt = E.mean(a)
        worse = sum(1 for _ in range(2000) if E.mean(rnd.sample(allp, len(a))) <= tgt)
        out(f"   placebo: a random {len(a)} of these dogs loses this much or more in {worse} of 2,000 draws "
            f"(every second-look dog: {E.mean(allp) * 100:+.1f}%)")
        won_a = sum(1 for r, k in away if r["won"]) / len(away)
        out(f"   the ran-away dogs won {won_a * 100:.1f}%; their price at that look said "
            f"{E.mean(k[3] for r, k in away) * 100:.1f}%, the close {E.mean(r['close_p'] for r, k in away) * 100:.1f}% "
            f"-> short by {(E.mean(k[3] for r, k in away) - won_a) * 100:+.1f} pts of win %")
        for lo, hi, tag in ((-99, -4, "4+"), (-4, -3, "3-4"), (-3, -2, "2-3"), (-2, -1, "1-2")):
            w = [(r, k) for r, k, m in pop if lo < m <= hi] if lo > -99 else [(r, k) for r, k, m in pop if m <= hi]
            if w:
                out(f"     ran away {tag:4s}: {E.roi([pl(r, k[2]) for r, k in w])} | won "
                    f"{sum(1 for r, k in w if r['won']) / len(w) * 100:.1f}% vs priced {E.mean(k[3] for r, k in w) * 100:.1f}%")
