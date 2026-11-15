"""11/15 - THE EXAM SCAN ON THE PAID ODDS HISTORY (college football 2020-26, NFL too): the 11/11 early-line studies' base
table (results/studies/early_1111/base.py -> ~/.cache/d503_early1111/base_<lg>.pkl: every side, every FAIR look - a price
posted after both teams' last games ended - the close, the engine's own read walk-forward, tuned on the 3 seasons before).
The scan's play: a dog +100..+280 whose raw own read is 4-8 points over the no-vig price at the FIRST fair look at least
a day before the game (never game day - the scan's rule), sized sports.kelly_units(own, price).
Seven seasons instead of e2's four, and a price a bettor could really take. Asked: the band; the Kelly dose; what each
size made; home vs road; did we beat the close.
Usage: python results/studies/sizing_1115/e3_exam_paid.py > results/studies/sizing_1115/e3_exam_paid.out"""
import math
import os
import pickle
import random
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402

CACHE = os.path.expanduser("~/.cache/d503_early1111")


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def load(lg):
    p = os.path.join(CACHE, f"base_{lg}.pkl")
    if not os.path.exists(p):
        return []
    out = []
    for r in pickle.load(open(p, "rb")):
        if r.get("own") is None or not r.get("looks"):
            continue
        own = r["own"]                                           # (already this side's read)
        looks = [k for k in r["looks"] if k[0] >= 1]              # (days out, hours since ready, median american, no-vig p, ...)
        if not looks:
            continue
        k = looks[0]                                             # the first fair look, a day or more out
        o = k[2]
        if o is None or not 100 <= o <= 280:
            continue
        d = dec(o)
        out.append(dict(lg=lg, season=r["season"], start=r["start"], home=r["home"], neutral=r.get("neutral"), odds=o, dec=d,
                        own=own, mkt=k[3], gap=own - k[3], won=bool(r["won"]), flat=(d - 1) if r["won"] else -1.0,
                        close_p=r.get("close_p"), close_o=r.get("close_o"), ku=sports.kelly_units(own, o), days=k[0]))
    return out


def st(rs, units=None):
    n = len(rs)
    if not n:
        return "n    0"
    w = sum(r["won"] for r in rs)
    fl = sum(r["flat"] for r in rs)
    bev = sum(r["mkt"] for r in rs)
    var = sum(r["mkt"] * (1 - r["mkt"]) for r in rs)
    s = f"n {n:4d} {w:3d}-{n - w:<3d} flat {100 * fl / n:+6.1f}% z {(w - bev) / math.sqrt(var):+5.2f}"
    if units:
        net = sum(units(r) * r["flat"] for r in rs)
        risk = sum(units(r) for r in rs)
        s += f" | {net:+6.1f}u on {risk:5.1f}u ({100 * net / risk if risk else 0:+5.1f}%)"
    return s


def halves(name, rs, units=None):
    a = [r for r in rs if r["season"] <= 2022]
    b = [r for r in rs if r["season"] >= 2023]
    seas = sorted({r["season"] for r in rs})
    up = sum(sum(r["flat"] for r in rs if r["season"] == s) > 0 for s in seas)
    print(f"  {name:48s} {st(rs, units)} | 2020-22 {st(a)[:30]} | 2023-26 {st(b)[:30]} | seasons up {up}/{len(seas)}")


def worst(rs, fn):
    cum = peak = w = 0.0
    for r in sorted(rs, key=lambda r: r["start"]):
        cum += fn(r) * r["flat"]
        peak = max(peak, cum)
        w = min(w, cum - peak)
    return w


for lg in ("ncaaf", "nfl"):
    rows = load(lg)
    if not rows:
        print(lg, "no base table on this machine")
        continue
    print("=" * 20, lg.upper(), f"{len(rows)} dogs +100..+280 at the first fair look a day or more out, seasons {sorted({r['season'] for r in rows})}")
    halves("every dog (the vig)", rows)
    for lo, hi in ((-1, 0), (0, 0.04), (0.04, 0.08), (0.08, 0.12), (0.12, 1)):
        halves(f"gap {lo:+.2f}..{hi:+.2f}" + (" (THE BAND)" if lo == 0.04 else ""), [r for r in rows if lo <= r["gap"] < hi],
               (lambda r: r["ku"]) if lo == 0.04 else None)
    band = [r for r in rows if 0.04 <= r["gap"] < 0.08]
    if lg != "ncaaf" or not band:
        continue
    print("  -- the band by season")
    for s in sorted({r["season"] for r in band}):
        print(f"     {s}: {st([r for r in band if r['season'] == s], lambda r: r['ku'])}")
    print("  -- THE DOSE: the Kelly size vs what happened")
    for lo, hi in ((0, 1.5), (1.5, 2.0), (2.0, 2.5), (2.5, 9)):
        halves(f"   Kelly size {lo}..{hi}u", [r for r in band if lo <= r["ku"] < hi])
    for lo, hi in ((0.04, 0.06), (0.06, 0.08)):
        halves(f"   gap {lo:.2f}..{hi:.2f}", [r for r in band if lo <= r["gap"] < hi])
    for lo, hi in ((100, 149), (150, 199), (200, 280)):
        halves(f"   price +{lo}..+{hi}", [r for r in band if lo <= r["odds"] <= hi])
    halves("   HOME dogs", [r for r in band if r["home"] and not r.get("neutral")])
    halves("   ROAD dogs", [r for r in band if not r["home"] and not r.get("neutral")])
    cl = [r for r in band if r.get("close_p") is not None]
    if cl:
        mv = sum(r["close_p"] - r["mkt"] for r in cl) / len(cl)
        halves("   the close moved OUR way", [r for r in cl if r["close_p"] > r["mkt"]])
        halves("   the close moved AGAINST us", [r for r in cl if r["close_p"] < r["mkt"]])
        print(f"     the average no-vig move to the close: {100 * mv:+.2f} points our way ({sum(r['close_p'] > r['mkt'] for r in cl)} of {len(cl)} moved our way)")
    print("  -- WHAT EACH SIZE MADE on the band")
    for nm, fn in (("quarter-Kelly on the raw read (today)", lambda r: r["ku"]), ("flat ½u", lambda r: 0.5), ("flat 1u", lambda r: 1.0)):
        o = []
        for x in (band, [r for r in band if r["season"] <= 2022], [r for r in band if r["season"] >= 2023]):
            net = sum(fn(r) * r["flat"] for r in x)
            risk = sum(fn(r) for r in x)
            o.append(f"{net:+6.1f}u/{risk:5.1f}u {100 * net / risk if risk else 0:+5.1f}%")
        print(f"     {nm:40s} ALL {o[0]} worst {worst(band, fn):+5.1f}u | 2020-22 {o[1]} | 2023-26 {o[2]}")
    ks = [r["ku"] for r in band]
    net = sum(r["ku"] * r["flat"] for r in band)
    rnd = random.Random(1115)
    beat = 0
    for _ in range(2000):
        sh = ks[:]
        rnd.shuffle(sh)
        beat += sum(k * r["flat"] for k, r in zip(sh, band)) >= net
    print(f"     PLACEBO: the same Kelly sizes dealt at RANDOM over the same {len(band)} plays made as much or more {beat} of 2,000 "
          f"(Kelly's own order {net:+.1f}u); the average Kelly size {sum(ks) / len(ks):.2f}u")
