"""11/15 - THE EARLY SPOTS' SIZES on the paid odds history (the 11/11 early-line studies' base table, football 2020-26,
~/.cache/d503_early1111/base_<lg>.pkl - every side with its FAIR looks and the spots the live engine would tag).
The live sizes: the bye-week dog 1u; Monday night NFL dog / East-flying-West / hammered early ½u; the blowout spot paused.
Each spot's dogs +100..+350 at the first fair look a day or more out: flat 1u vs the price, 2020-22 / 2023-26, seasons.
Is the 1u bye the only one that earns more than ½u - and does any ½u spot earn 1u?
Usage: python results/studies/sizing_1115/e4_spots_paid.py > results/studies/sizing_1115/e4_spots_paid.out"""
import math
import os
import pickle

CACHE = os.path.expanduser("~/.cache/d503_early1111")


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def load(lg):
    p = os.path.join(CACHE, f"base_{lg}.pkl")
    if not os.path.exists(p):
        return []
    out = []
    for r in pickle.load(open(p, "rb")):
        looks = [k for k in (r.get("looks") or []) if k[0] >= 1]
        if not looks:
            continue
        o = looks[0][2]
        if o is None or not 100 <= o <= 350:
            continue
        d = dec(o)
        out.append({**{k: v for k, v in r.items() if k != "looks"}, "odds": o, "dec": d, "mkt": looks[0][3],
                    "flat": (d - 1) if r["won"] else -1.0})
    return out


def st(rs):
    n = len(rs)
    if not n:
        return "n    0"
    w = sum(bool(r["won"]) for r in rs)
    fl = sum(r["flat"] for r in rs)
    bev = sum(r["mkt"] for r in rs)
    var = sum(r["mkt"] * (1 - r["mkt"]) for r in rs)
    return f"n {n:4d} {w:3d}-{n - w:<3d} flat {100 * fl / n:+6.1f}% z {(w - bev) / math.sqrt(var):+5.2f}"


def halves(name, rs):
    a = [r for r in rs if r["season"] <= 2022]
    b = [r for r in rs if r["season"] >= 2023]
    seas = sorted({r["season"] for r in rs})
    up = sum(sum(r["flat"] for r in rs if r["season"] == s) > 0 for s in seas)
    print(f"  {name:46s} {st(rs)} | 2020-22 {st(a)} | 2023-26 {st(b)} | seasons up {up}/{len(seas)}")


for lg in ("nfl", "ncaaf"):
    rows = load(lg)
    if not rows:
        print(lg, "no base table on this machine")
        continue
    print("=" * 20, lg.upper(), f"{len(rows)} dogs +100..+350 at the first fair look; row keys: {sorted(k for k in rows[0] if k not in ('flat', 'dec', 'mkt', 'odds'))}")
    halves("every dog (the vig)", rows)
    r0 = rows[0]
    if "rest" in r0 and "orest" in r0:
        halves("BYE-WEEK DOG (rest 13+ days, the other side not) - 1u live",
               [r for r in rows if (r.get("rest") or 0) >= 13 and (r.get("orest") or 0) < 13])
        halves("   both off a bye", [r for r in rows if (r.get("rest") or 0) >= 13 and (r.get("orest") or 0) >= 13])
    if "mnf" in r0:
        halves("MONDAY NIGHT dog - ½u live", [r for r in rows if r.get("mnf")])
    if "eastwest" in r0:
        halves("EAST COAST team flying West - ½u live", [r for r in rows if r.get("eastwest")])
    if "last_margin" in r0:
        halves("BLEW SOMEBODY OUT (won by 21+ last game) - paused", [r for r in rows if (r.get("last_margin") or 0) >= 21])
        halves("HAMMERED (lost by 21+ last game) - ½u live", [r for r in rows if (r.get("last_margin") or 0) <= -21])
    for k in ("spots", "tags"):
        if k in r0:
            names = sorted({s for r in rows for s in (r.get(k) or [])})
            for s in names:
                halves(f"tagged {s}", [r for r in rows if s in (r.get(k) or [])])
