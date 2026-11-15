"""11/15 - IS KELLY ON THE RAW OWN READ THE RIGHT SIZE FOR THE EXAM-SCAN EARLY PLAYS?
(Minnesota +114 went up 2u on 11/15 for 11/21 with the MAIN read 0.4 over its price; Georgia St +170 1.5u lost 34-17.)
The rows: e1_exam_rows.py - the exam walk-forward, one test season at a time (the engine learns on the 3 seasons before),
every +100..+280 dog at its EARLY price (the open the scan could bet), the raw own read the scan sizes on.
The scan posts a dog in a band the exam passed (today: college football "+4..8" only) and sizes it sports.kelly_units(own,
odds) - a quarter of Kelly on the raw read, ½u..5u.
Asked: (1) the band by season; (2) inside the band, does the BIGGER Kelly size win more vs its price (the dose a size
needs - the 10/30 rule); (3) what each sizing made; (4) a placebo; (5) every league pooled (is the raw read's gap a size
signal anywhere).
Usage: python results/studies/sizing_1115/e2_exam_size.py > results/studies/sizing_1115/e2_exam_size.out"""
import json
import math
import os
import random
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402

CACHE = os.path.expanduser("~/.cache/d503_sizing1115")
LGS = ("ncaaf", "nfl", "nba", "nhl", "ncaab", "mlb")


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def load(lg):
    p = os.path.join(CACHE, f"exam_{lg}.jsonl")
    rows = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
    for r in rows:
        r["dec"] = dec(r["open"])
        r["flat"] = (r["dec"] - 1) if r["won"] else -1.0
        r["ku"] = sports.kelly_units(r["own"], r["open"])
        r["need"] = 1 / r["dec"]
    return rows


def st(rs, units=None):
    n = len(rs)
    if not n:
        return "n    0"
    w = sum(r["won"] for r in rs)
    fl = sum(r["flat"] for r in rs)
    bev = sum(r["mkt"] for r in rs)
    var = sum(r["mkt"] * (1 - r["mkt"]) for r in rs)
    z = (w - bev) / math.sqrt(var) if var else 0
    s = f"n {n:4d} {w:3d}-{n - w:<3d} flat {100 * fl / n:+6.1f}% z {z:+5.2f}"
    if units:
        net = sum(units(r) * r["flat"] for r in rs)
        risk = sum(units(r) for r in rs)
        s += f" | {net:+6.1f}u on {risk:5.1f}u ({100 * net / risk if risk else 0:+5.1f}%)"
    return s


def halves(name, rs, units=None):
    seas = sorted({r["season"] for r in rs})
    a = [r for r in rs if r["season"] <= 2024]
    b = [r for r in rs if r["season"] >= 2025]
    up = sum(sum(r["flat"] for r in rs if r["season"] == s) > 0 for s in seas)
    print(f"  {name:50s} {st(rs, units)} | 2023-24 {st(a)[:30]} | 2025-26 {st(b)[:30]} | seasons up {up}/{len(seas)}")


def worst(rs, units):
    cum = peak = w = 0.0
    for r in sorted(rs, key=lambda r: r["start"]):
        cum += units(r) * r["flat"]
        peak = max(peak, cum)
        w = min(w, cum - peak)
    return w


for lg in LGS:
    rows = load(lg)
    if not rows:
        continue
    band = [r for r in rows if 0.04 <= r["gap"] < 0.08]
    print("=" * 20, lg.upper(), f"{len(rows)} bettable early dogs +100..+280, seasons {sorted({r['season'] for r in rows})}")
    halves("every dog (the vig)", rows)
    halves("gap under 0 (the read is against the dog)", [r for r in rows if r["gap"] < 0])
    halves("gap 0..4", [r for r in rows if 0 <= r["gap"] < 0.04])
    halves("gap +4..8 (THE BAND)", band, lambda r: r["ku"])
    halves("gap +8..12", [r for r in rows if 0.08 <= r["gap"] < 0.12])
    halves("gap +12+", [r for r in rows if r["gap"] >= 0.12])
    if lg != "ncaaf":
        continue
    print("  -- inside the band (the scan's plays), by season")
    for s in sorted({r["season"] for r in band}):
        x = [r for r in band if r["season"] == s]
        print(f"     {s}: {st(x, lambda r: r['ku'])}")
    print("  -- THE DOSE: does the bigger Kelly size win more vs its price?")
    for lo, hi in ((0, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 9)):
        halves(f"   Kelly size {lo}..{hi}u", [r for r in band if lo <= r["ku"] < hi or (lo == 0 and r["ku"] == 0)])
    halves("   Kelly 1.5u+ (the Georgia St / Minnesota size)", [r for r in band if r["ku"] >= 1.5])
    halves("   Kelly under 1.5u", [r for r in band if r["ku"] < 1.5])
    for lo, hi in ((0.04, 0.05), (0.05, 0.06), (0.06, 0.07), (0.07, 0.08)):
        halves(f"   gap {lo:.2f}..{hi:.2f}", [r for r in band if lo <= r["gap"] < hi])
    for lo, hi in ((100, 129), (130, 169), (170, 219), (220, 280)):
        halves(f"   price +{lo}..+{hi}", [r for r in band if lo <= r["open"] <= hi])
    halves("   HOME dogs (true home)", [r for r in band if r["side"] == "home" and not r["neutral"]])
    halves("   ROAD dogs", [r for r in band if r["side"] == "away" and not r["neutral"]])
    halves("   the price came IN by the close (we beat it)", [r for r in band if r["close"] < r["open"]])
    halves("   the price went OUT by the close", [r for r in band if r["close"] > r["open"]])
    clv = sum(r["mkt_close"] - r["mkt"] for r in band) / len(band)
    print(f"     average no-vig move open -> close: {100 * clv:+.2f} points our way; at the CLOSING price the same dogs: "
          f"{100 * sum((dec(r['close']) - 1) if r['won'] else -1 for r in band) / len(band):+.1f}% flat")
    print("  -- WHAT EACH SIZE MADE on the band (units won / risked, worst stretch)")
    for name, fn in (("quarter-Kelly on the raw read (today)", lambda r: r["ku"]),
                     ("flat ½u", lambda r: 0.5), ("flat 1u", lambda r: 1.0),
                     ("½u, 1u at Kelly 1.5u+", lambda r: 1.0 if r["ku"] >= 1.5 else 0.5),
                     ("1u, ½u at Kelly 1.5u+ (the reverse)", lambda r: 0.5 if r["ku"] >= 1.5 else 1.0)):
        a = [r for r in band if r["season"] <= 2024]
        b = [r for r in band if r["season"] >= 2025]
        o = []
        for x in (band, a, b):
            net = sum(fn(r) * r["flat"] for r in x)
            risk = sum(fn(r) for r in x)
            o.append(f"{net:+6.1f}u/{risk:5.1f}u {100 * net / risk:+5.1f}%")
        print(f"     {name:42s} ALL {o[0]} worst {worst(band, fn):+5.1f}u | 2023-24 {o[1]} | 2025-26 {o[2]}")
    # correlation of the Kelly size with the flat result, and a placebo: Kelly's weights shuffled over the same plays
    net = sum(r["ku"] * r["flat"] for r in band)
    ks = [r["ku"] for r in band]
    rnd = random.Random(1115)
    beat = 0
    for _ in range(2000):
        sh = ks[:]
        rnd.shuffle(sh)
        beat += sum(k * r["flat"] for k, r in zip(sh, band)) >= net
    print(f"     PLACEBO: the same Kelly sizes dealt at RANDOM over the same {len(band)} plays made as much or more "
          f"{beat} of 2,000 times (Kelly's own order {net:+.1f}u)")
    mean_k = sum(ks) / len(ks)
    print(f"     the average Kelly size on the band: {mean_k:.2f}u; sizes: " +
          ", ".join(f"{u}u x{sum(1 for k in ks if k == u)}" for u in sorted(set(ks))))

print("\n" + "=" * 20, "EVERY LEAGUE POOLED: the raw read's gap as a size signal (all bettable early dogs)")
allr = [r for lg in LGS for r in load(lg)]
for lo, hi in ((-1, 0), (0, 0.04), (0.04, 0.08), (0.08, 0.12), (0.12, 1)):
    halves(f"gap {lo:+.2f}..{hi:+.2f}", [r for r in allr if lo <= r["gap"] < hi])
for lo, hi in ((0.5, 1.0), (1.0, 1.5), (1.5, 2.5), (2.5, 9)):
    halves(f"Kelly size {lo}..{hi}u (any league, gap 0+)", [r for r in allr if r["gap"] >= 0 and lo <= r["ku"] < hi])
