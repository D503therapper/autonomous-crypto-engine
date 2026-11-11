"""STUDIES 3 / 7 / 9 - THE LEAKS, measured honestly.
(a) every live kind against what its REPLAY says it should earn (the replay's flat ROI from s1_cells.out, train + held):
    z = (live wins - the wins the replay rate predicts at these prices) / sd. A kind is 'leaking' only when the live
    record is unlikely EVEN IF the replay is right; small samples say little either way.
(b) the early spots against the blind numbers they were built on.
(c) SATURDAY: the college football dog pile - how many college dog unit plays each Saturday carried, by kind, and what
    the 11/11 wiring (the 🔍 road-only / 35 cap / QB change, the paused engine spot) leaves of it.
(d) late adds (posted 2 PM PT on) - what they were.
Reads p1_rows.json (p1_book.py) + data/sports/early.json.   Usage: python s7_leaks.py > s7_leaks.out"""
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402
import sports_early  # noqa: E402

rows = json.load(open(os.path.join(HERE, "p1_rows.json")))
REPLAY = {"dog": (17.2, 286, "the Dog of the Day"), "lock": (4.8, 154, "the Lock"), "value play": (1.6, 328, "value plays (favorites)"),
          "floor": (8.0, 918, "the floor"), "nbafloor": (24.7, 128, "the NBA floor"), "dogplay": (18.3, 90, "the runner-up dog"),
          "nbafav": (22.7, 76, "the NBA favorite play"), "gap": (0.0, 0, "the 🔍 gap play (no replay row - judged against the price)")}


def zline(name, rs, roi, note=""):
    w = sum(r["won"] for r in rs)
    n = len(rs)
    k = 1 + roi / 100
    ps = [min(0.97, k / r["dec"]) for r in rs]
    e = sum(ps)
    sd_ = math.sqrt(sum(p * (1 - p) for p in ps))
    net = sum(r["net"] for r in rs)
    print(f"  {name:44s} live {w}-{n - w} {net:+6.2f}u | the replay rate ({roi:+.1f}%) predicts {e:4.1f} wins | z {(w - e) / sd_ if sd_ else 0:+.2f} {note}")


print("(a) LIVE vs THE REPLAY'S EXPECTATION, by kind")
for k, (roi, n, name) in REPLAY.items():
    rs = [r for r in rows if r["kind"] == k]
    if rs:
        zline(name, rs, roi, f"(replay n {n})" if n else "")
zline("ALL board unit plays vs the replay's +10.3% flat", [r for r in rows if not r["kind"].startswith("early")], 10.3)
zline("   ...favorites vs +5.6%", [r for r in rows if not r["kind"].startswith("early") and r["am"] < 0], 5.6)
zline("   ...dogs vs +12.1%", [r for r in rows if not r["kind"].startswith("early") and r["am"] > 0], 12.1)
zline("   ...½u dogs vs the replay's ½u +9.0%", [r for r in rows if not r["kind"].startswith("early") and r["am"] > 0 and r["u"] == 0.5], 9.0)
zline("   ...NBA unit plays vs +20%", [r for r in rows if r["lg"] == "nba" and not r["kind"].startswith("early")], 20.0)
zline("   ...hockey Dogs vs +15.6%", [r for r in rows if r["lg"] == "nhl" and r["kind"] == "dog"], 15.6)
zline("   ...college football board dogs vs the price", [r for r in rows if r["lg"] == "ncaaf" and r["am"] > 0 and not r["kind"].startswith("early")], 0.0)

print("\n(b) THE EARLY SPOTS vs the blind numbers they were built on")
early = json.load(open("data/sports/early.json"))["picks"]
BLIND = {"blowout": (4.4, "+4.4% on 610 blind (college; the NFL -12.5% on 94 - off there)"), "bye": (16.0, "+16% college / +29% NFL at the first fair price"),
         "hammered": (5.0, "the honest move model, ~+5%"), "engine": (0.0, "PAUSED 10/24"), "nba_open": (10.0, "+13% blind 2023-27 at the open; -6.9% on the 2020-23 mornings"),
         "euro_under": (20.0, "17-9 since 2018; the quit rule: under 50% after 15")}
by = defaultdict(list)
for e in early:
    if e.get("result") in ("won", "lost") and not e.get("pulled"):
        d = sports._dec(e["odds"])
        u = sports_early.units(e)
        by[e.get("spot") or "exam band / owner"].append(dict(won=e["result"] == "won", dec=d, net=u * (d - 1) if e["result"] == "won" else -u, posted=e.get("posted") or ""))
for k, rs in sorted(by.items(), key=lambda kv: sum(r["net"] for r in kv[1])):
    roi, note = BLIND.get(k, (0.0, ""))
    zline(f"early: {k}", rs, roi, note)
bl = [r for r in by["blowout"] if r["posted"] >= "2026-10-25"]
zline("   blowout since the 10/24 FBS-only fix", bl, 4.4)
print("   a quit rule in the Europe under's style for blowout: off under 35% won after 25 graded (the price expects ~40% at these prices) - "
      f"today {sum(r['won'] for r in by['blowout'])}-{len(by['blowout']) - sum(r['won'] for r in by['blowout'])}: it needs 6 of the next 11 to stay on")

print("\n(c) SATURDAYS - the college football dog pile (every college dog unit play, board + early, by its game day)")
sat = defaultdict(list)
for r in rows:
    if r["lg"] == "ncaaf" and r["am"] > 0 and r["dow"] == "Sat":
        sat[r["date"]].append(r)
tw = tl = 0
tn = 0.0
for d in sorted(sat):
    rs = sat[d]
    w = sum(r["won"] for r in rs)
    kinds = defaultdict(lambda: [0, 0])
    for r in rs:
        kinds[r["kind"]][0 if r["won"] else 1] += 1
    tw += w
    tl += len(rs) - w
    tn += sum(r["net"] for r in rs)
    print(f"  {d}: {len(rs):2d} college dog unit plays {w}-{len(rs) - w} {sum(r['net'] for r in rs):+6.2f}u on {sum(r['u'] for r in rs):4.1f}u   " + ", ".join(f"{k} {a}-{b}" for k, (a, b) in sorted(kinds.items())))
print(f"  ALL Saturdays: {tw}-{tl} {tn:+.2f}u")
allc = [r for r in rows if r["lg"] == "ncaaf" and r["am"] > 0]
left = [r for r in allc if r["kind"] not in ("gap", "early:engine")]
print(f"  every college dog unit play: {sum(r['won'] for r in allc)}-{len(allc) - sum(r['won'] for r in allc)} {sum(r['net'] for r in allc):+.2f}u; "
      f"without the 🔍 gap plays (now road-only: live road 1-4, home 3-9) and the paused engine spot: {sum(r['won'] for r in left)}-{len(left) - sum(r['won'] for r in left)} {sum(r['net'] for r in left):+.2f}u")
zline("  the Saturday college dog pile vs the price", [r for d in sat for r in sat[d]], 0.0)

print("\n(d) LATE ADDS (posted 2 PM PT on)")
for r in rows:
    if r["slot"].startswith("late"):
        print(f"  {r['date']} {r['lg']:6s} {r['kind']:11s} {str(r['team']):20s} {r['am']:+5d} {r['u']}u {'W' if r['won'] else 'L'} {r['net']:+.2f}u  posted {r['lead']:.1f}h before the start")
