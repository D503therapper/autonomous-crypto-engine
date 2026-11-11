"""S3 / S5 / S6 on the paid football odds history (NFL + college, 2020-25 + Sept 2026; FAIR looks only; the median
book's price at each look; TRAIN 2020-22, HELD OUT 2023-26).
S3 - THE PRICE PATH: from the week's first fair number to the close - where the dog's no-vig win % sits at each later
     look (days out), by league and by spot. + = the money came TO the dog (its price got shorter = an early bet beat
     the close).
S5 - WAIT OR BET NOW: the same dogs bet at the first fair number, at each later look, at the close - ROI and the
     price, by spot.
S6 - THE MONEY-LEFT RULE: at a later early look (what a scan that posts a day or two after the first number sees), how
     far the price has ALREADY moved since the first fair number - and what the bet does from there (the move still to
     come, the ROI at that look's price). Also the opener -> first fair move (what the money did before we could bet)."""
import base
import elib as E

out = E.Tee("s3_s5_s6_out.txt")
BUCK = (("5-7d", 4.5, 7.5), ("3-4d", 2.5, 4.5), ("2d", 1.5, 2.5), ("1d", 0.5, 1.5), ("game day", 0.03, 0.5))
ROWS = {lg: base.build(lg) for lg in ("nfl", "ncaaf")}


def at(r, lo, hi):
    e = [k for k in r["looks"] if lo <= k[0] < hi]
    return e[-1] if e else None


def pl(r, o):
    return (E.dec(o) - 1) if r["won"] else -1.0


def split(rs, f):
    """f(r) -> value or None; -> (all, train, held) lists."""
    a = [(r["season"], f(r)) for r in rs]
    a = [(s, v) for s, v in a if v is not None]
    return ([v for _, v in a], [v for s, v in a if s <= 2022], [v for s, v in a if s >= 2023])


def mv(xs):
    return f"{E.mean(xs):+5.2f} (n {len(xs):4d}, t {E.tstat(xs):+5.1f})" if xs else "      -              "


out("=" * 30, "S3 - THE PRICE PATH (points of no-vig win % the side gained since its first fair number)")
for lg in ("nfl", "ncaaf"):
    rs = [r for r in ROWS[lg] if base.first_fair(r)]
    for nm, sel in (("dogs +100..+350 at the first fair number", lambda r, f: 100 <= f[2] <= 350),
                    ("  dogs +100..+149", lambda r, f: 100 <= f[2] <= 149),
                    ("  dogs +150..+350", lambda r, f: 150 <= f[2] <= 350),
                    ("  home dogs", lambda r, f: 100 <= f[2] <= 350 and r["home"]),
                    ("  road dogs", lambda r, f: 100 <= f[2] <= 350 and not r["home"]),
                    ("favorites -150..-101", lambda r, f: -150 <= f[2] <= -101),
                    ("spot: bye dog", lambda r, f: "bye" in base.spots(r, f)),
                    ("spot: Monday night dog", lambda r, f: "mnf" in base.spots(r, f)),
                    ("spot: East-West dog", lambda r, f: "eastwest" in base.spots(r, f)),
                    ("spot: blew somebody out dog", lambda r, f: "blowout" in base.spots(r, f)),
                    ("read 4+ pts over the price (dog)", lambda r, f: 100 <= f[2] <= 350 and r["own"] is not None
                     and r["own"] - f[3] >= 0.04),
                    ("read 2+ pts UNDER the price (dog)", lambda r, f: 100 <= f[2] <= 350 and r["own"] is not None
                     and r["own"] - f[3] <= -0.02)):
        pop = [r for r in rs if sel(r, base.first_fair(r))]
        if len(pop) < 15:
            continue
        out(f"\n {lg} | {nm}: {len(pop)} sides (first fair look on average {E.mean(base.first_fair(r)[0] for r in pop):.1f} days out)")
        for bn, lo, hi in BUCK:
            def f(r, lo=lo, hi=hi):
                ff = base.first_fair(r)
                k = at(r, lo, hi)
                return (k[3] - ff[3]) * 100 if k and k is not ff and k[0] < ff[0] else None
            a, tr, he = split(pop, f)
            if len(a) >= 15:
                out(f"   by the {bn:8s} look   ALL {mv(a)} | TRAIN {mv(tr)} | HELD {mv(he)}")
        a, tr, he = split(pop, lambda r: (r["close_p"] - base.first_fair(r)[3]) * 100)
        out(f"   by the CLOSE          ALL {mv(a)} | TRAIN {mv(tr)} | HELD {mv(he)}")
        to = sum(1 for x in a if x >= 1)
        aw = sum(1 for x in a if x <= -1)
        out(f"   the close vs the first fair number: came to it 1+ pt {to / len(a) * 100:.0f}% / within a point "
            f"{(len(a) - to - aw) / len(a) * 100:.0f}% / ran away 1+ {aw / len(a) * 100:.0f}%;  3+ pts to it "
            f"{sum(1 for x in a if x >= 3) / len(a) * 100:.0f}% / 3+ away {sum(1 for x in a if x <= -3) / len(a) * 100:.0f}%")
        bys = {}
        for r in pop:
            bys.setdefault(r["season"], []).append((r["close_p"] - base.first_fair(r)[3]) * 100)
        out("   by season: " + "  ".join(f"{s} {E.mean(v):+.2f}" for s, v in sorted(bys.items())))

out("\n" + "=" * 30, "S5 - WAIT OR BET NOW (flat 1u at the median book's price at each time; the same side all the way)")
for lg in ("nfl", "ncaaf"):
    rs = [r for r in ROWS[lg] if base.first_fair(r)]
    for nm, sel in (("every dog +100..+350", lambda r, f: 100 <= f[2] <= 350),
                    ("bye dog", lambda r, f: "bye" in base.spots(r, f)),
                    ("Monday night dog", lambda r, f: "mnf" in base.spots(r, f)),
                    ("East-West dog", lambda r, f: "eastwest" in base.spots(r, f)),
                    ("blew somebody out dog", lambda r, f: "blowout" in base.spots(r, f)),
                    ("ANY spot dog", lambda r, f: bool(base.spots(r, f))),
                    ("ANY spot dog, read not fighting", lambda r, f: bool(base.spots(r, f)) and r["own"] is not None
                     and r["own"] >= f[3] - 0.01),
                    ("dog, read 4+ over the price", lambda r, f: 100 <= f[2] <= 350 and r["own"] is not None
                     and r["own"] - f[3] >= 0.04)):
        pop = [r for r in rs if sel(r, base.first_fair(r))]
        if len(pop) < 20:
            continue
        out(f"\n {lg} | {nm}: {len(pop)}")
        a, tr, he = split(pop, lambda r: pl(r, base.first_fair(r)[2]))
        out(f"   at the FIRST FAIR number   ALL {E.roi(a)} | TRAIN {E.roi(tr)} | HELD {E.roi(he)}")
        a, tr, he = split(pop, lambda r: pl(r, base.first_fair(r)[4]))
        out(f"   (first fair, BEST book)    ALL {E.roi(a)} | TRAIN {E.roi(tr)} | HELD {E.roi(he)}")
        for bn, lo, hi in BUCK[1:]:
            def f(r, lo=lo, hi=hi):
                ff = base.first_fair(r)
                k = at(r, lo, hi)
                return pl(r, k[2]) if k and k is not ff and k[0] < ff[0] else None
            a, tr, he = split(pop, f)
            if len(a) >= 20:
                out(f"   at the {bn:8s} look       ALL {E.roi(a)} | TRAIN {E.roi(tr)} | HELD {E.roi(he)}")
        a, tr, he = split(pop, lambda r: pl(r, r["close_o"]))
        out(f"   at the CLOSE               ALL {E.roi(a)} | TRAIN {E.roi(tr)} | HELD {E.roi(he)}")
        # paired: the same games at the first fair number and at the close
        d = [pl(r, base.first_fair(r)[2]) - pl(r, r["close_o"]) for r in pop]
        out(f"   first fair minus the close, the same bets: {E.mean(d) * 100:+.1f}% a bet (t {E.tstat(d):+.1f}); "
            f"held {E.mean([x for r, x in zip(pop, d) if r['season'] >= 2023]) * 100:+.1f}%")

out("\n" + "=" * 30, "S6 - THE MONEY-LEFT RULE (a dog +100..+350 at a LATER early look, 1.5+ days out: what the price "
    "already did since the first fair number -> the move still to come by the close, and the ROI at that look's price)")
BK = (("ran AWAY 4+ pts", -99, -4), ("ran away 2-4", -4, -2), ("ran away 1-2", -2, -1), ("flat (inside 1)", -1, 1),
      ("came to it 1-2", 1, 2), ("came to it 2-4", 2, 4), ("came to it 4+ (hammered)", 4, 99))
for lg in ("nfl", "ncaaf"):
    for spot in (None, "anyspot", "bye", "blowout"):
        cells = {b[0]: [] for b in BK}
        for r in ROWS[lg]:
            ff = base.first_fair(r)
            if not ff:
                continue
            later = [k for k in base.early_looks(r) if k[0] < ff[0]]
            if not later:
                continue
            k = later[0]                                  # the next early look after the first fair number
            if not 100 <= k[2] <= 350:
                continue
            sp = [s for s in base.spots(r, k, ff) if s != "hammered"]
            if spot == "anyspot" and not sp:
                continue
            if spot not in (None, "anyspot") and spot not in sp:
                continue
            m = (k[3] - ff[3]) * 100
            for bn, lo, hi in BK:
                if lo <= m < hi:
                    cells[bn].append((r, k))
        if sum(len(v) for v in cells.values()) < 60:
            continue
        out(f"\n {lg} | {spot or 'every dog'} (the second early look, on average "
            f"{E.mean(k[0] for v in cells.values() for _, k in v):.1f} days out)")
        for bn, _, _ in BK:
            v = cells[bn]
            if len(v) < 8:
                continue
            fw = [(r["close_p"] - k[3]) * 100 for r, k in v]
            a = [pl(r, k[2]) for r, k in v]
            he = [pl(r, k[2]) for r, k in v if r["season"] >= 2023]
            tr = [pl(r, k[2]) for r, k in v if r["season"] <= 2022]
            ff_roi = [pl(r, base.first_fair(r)[2]) for r, k in v]
            out(f"   {bn:26s} still to come {mv(fw)} | ROI at this look ALL {E.roi(a)} | TRAIN {E.roi(tr)} | "
                f"HELD {E.roi(he)} | (had we bet the first fair: {E.mean(ff_roi) * 100:+.1f}%)")

out("\n S6b - the game file's OPENER -> the first fair number (what the money did before we could bet), dogs "
    "+100..+350 at the first fair number")
for lg in ("nfl", "ncaaf"):
    cells = {b[0]: [] for b in BK}
    for r in ROWS[lg]:
        ff = base.first_fair(r)
        if not ff or r["open_p"] is None or not 100 <= ff[2] <= 350:
            continue
        m = (ff[3] - r["open_p"]) * 100
        for bn, lo, hi in BK:
            if lo <= m < hi:
                cells[bn].append(r)
    out(f" {lg}")
    for bn, _, _ in BK:
        v = cells[bn]
        if len(v) < 8:
            continue
        fw = [(r["close_p"] - base.first_fair(r)[3]) * 100 for r in v]
        a = [pl(r, base.first_fair(r)[2]) for r in v]
        he = [pl(r, base.first_fair(r)[2]) for r in v if r["season"] >= 2023]
        tr = [pl(r, base.first_fair(r)[2]) for r in v if r["season"] <= 2022]
        out(f"   {bn:26s} still to come {mv(fw)} | ROI at the first fair ALL {E.roi(a)} | TRAIN {E.roi(tr)} | HELD {E.roi(he)}")
