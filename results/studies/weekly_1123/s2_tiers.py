"""11/23 - THE WEEKLY FABLE SIZING + EDGES REVIEW - S2: EVERY SIZE TIER AGAINST ITS REPLAY RECORD, AND THE DRIFT.
The rig: best_1122's board (money_1117's R3L - the board today's code builds, 2023-10 -> 2026-11 at the close, today's
sizes, the ⭐ at its honest size from 11/24) - rows in ~/.cache/d503_dogs1117 (never the repo). Train = to 6/30/2025,
held out = 7/2025 -> 10/12/2026 (the later half, not a clean blind test), the rig's own live window apart.
For every size tier / fine kind / price band: the replay record by half, and THE DRIFT - the real live record (s1,
picks.json since 10/25) against what the replay's win rate at those prices would expect: z of the live wins against the
replay's edge (the replay's flat ROI turned into a win chance at each live price). |z| under 2 = inside variance.
NOT a new sizing hunt (sizing_1117 / money_1117 / profit_1117 / best_1122 tried ~300 size cells - no repeats): this is
the standing weekly table.
Usage: python results/studies/weekly_1123/s2_tiers.py > results/studies/weekly_1123/s2_tiers.out"""
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "best_1122"))
import blib as B  # noqa: E402

half, flat, season = B.half, B.flat, B.season
P = B.P


def tier(u):
    return "½u" if u < 0.75 else "1u" if u < 1.25 else "2u" if u < 2.25 else "3u"


def band(o):
    return "fav -150..-101" if o < 100 else "+100..+150" if o <= 150 else "+151..+199" if o < 200 else "+200..+350"


def st(rs):
    n = len(rs)
    if not n:
        return None
    w = sum(r["result"] == "won" for r in rs)
    f = sum(flat(r) for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum(1 / r["dec"] * (1 - 1 / r["dec"]) for r in rs)
    return dict(n=n, w=w, roi=100 * f / n, z=(w - bev) / math.sqrt(var) if var else 0.0)


def s(o):
    return f"{o['w']:4d}-{o['n'] - o['w']:<4d} {o['roi']:+6.1f}%" if o else "   -              "


def line(name, rs, w=44):
    nl = [r for r in rs if half(r["date"]) != "live"]
    a, t, h = st(nl), st([r for r in nl if half(r["date"]) == "train"]), st([r for r in nl if half(r["date"]) == "held"])
    if not a:
        return
    seas = defaultdict(float)
    for r in nl:
        seas[season(r["date"])] += flat(r)
    print(f"  {name:{w}s} {s(a)} z {a['z']:+5.2f} | train {s(t)} | HELD {s(h)} | up {sum(v > 0 for v in seas.values())}/{len(seas)}")
    return a


print("==== THE REPLAY BOARD (today's code, today's sizes, 2023-26 at the close), flat 1u per play")
line("every unit play", P)
print(" -- by today's size")
for t in ("½u", "1u", "2u", "3u"):
    line(t, [r for r in P if tier(r["u0"]) == t])
print(" -- by the fine kind (its size in the name)")
by = defaultdict(list)
for r in P:
    by[r["k"]].append(r)
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    line(k, v)
print(" -- by sport")
for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab"):
    line(lg, [r for r in P if r["league"] == lg])
print(" -- by price")
for b in ("fav -150..-101", "+100..+150", "+151..+199", "+200..+350"):
    line(b, [r for r in P if band(r["odds"]) == b])
print(" -- the long dogs +200..+350 by kind (live they are 0-6 on the board, 0-8 in the early box)")
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    line(k, [r for r in v if r["odds"] >= 200])
print(" -- size x price")
for t in ("½u", "1u", "2u", "3u"):
    for b in ("fav -150..-101", "+100..+150", "+151..+199", "+200..+350"):
        line(f"{t} {b}", [r for r in P if tier(r["u0"]) == t and band(r["odds"]) == b])

# ---------------------------------------------------------------- the drift: live vs the replay's edge
ps = json.load(open(os.path.join(REPO, "data", "sports", "picks.json")))
live = []
for p in ps:
    if p.get("lean") or p.get("status") not in ("won", "lost") or not p.get("units") or len(p.get("legs") or []) != 1 or p["date"] < "2026-10-25":
        continue
    l = p["legs"][0]
    if (l.get("market") or "ml") != "ml":
        continue
    live.append(dict(u=float(p["units"]), dec=p["dec"], won=p["status"] == "won", odds=l.get("odds"), lg=l.get("league"),
                     kind="max" if p.get("max_play") else "floor" if p.get("floor") and not (p["floor"] or {}).get("nba") else
                     "nbafloor" if p.get("floor") else "dogplay" if p.get("dog_play") else "gap" if p.get("gap") is not None else
                     "ncaabplay" if p.get("ncaab_play") else "nbafav" if p.get("nba_fav") else p.get("kind")))


def drift(name, lv, rep):
    """live rows vs the replay rows of the same group: the replay's flat ROI r means a win chance of (1 + r) / dec at
    each live price; z = (live wins - that) / sd."""
    rep = [r for r in rep if half(r["date"]) != "live"]
    if not lv or len(rep) < 30:
        return
    roi = sum(flat(r) for r in rep) / len(rep)
    exp = sum(min(0.95, (1 + roi) / r["dec"]) for r in lv)
    var = sum(min(0.95, (1 + roi) / r["dec"]) * (1 - min(0.95, (1 + roi) / r["dec"])) for r in lv)
    w = sum(r["won"] for r in lv)
    fl = sum((r["dec"] - 1) if r["won"] else -1 for r in lv) / len(lv)
    z = (w - exp) / math.sqrt(var) if var else 0.0
    print(f"  {name:38s} live {w:3d}-{len(lv) - w:<3d} flat {100 * fl:+6.1f}% | the replay {100 * roi:+5.1f}% on {len(rep):4d} would win {exp:5.1f} of {len(lv)} "
          f"| drift z {z:+.2f} {'<-- OUTSIDE 2' if abs(z) >= 2 else ''}")


print("\n==== THE DRIFT - live moneyline unit plays since 10/25 against the replay's edge for the same group")
drift("every unit play", live, P)
for t in ("½u", "1u", "2u", "3u"):
    drift(f"size {t}", [r for r in live if tier(r["u"]) == t], [r for r in P if tier(r["u0"]) == t])
for k, nm in (("dog", "Dog of the Day"), ("max", "💎 hockey max play"), ("floor", "floor"), ("nbafloor", "NBA floor"), ("dogplay", "runner-up dog"),
              ("play", "value play (favorites)"), ("ncaabplay", "college hoops slot"), ("lock", "Lock"), ("gap", "🔍 gap play")):
    rep = [r for r in P if (r["kind"] == k if k != "max" else r["u0"] >= 3)]
    if k == "dog":
        rep = [r for r in P if r["kind"] == "dog" and r["u0"] < 3]
    drift(nm, [r for r in live if r["kind"] == k], rep)
for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab"):
    drift(f"sport {lg}", [r for r in live if r["lg"] == lg], [r for r in P if r["league"] == lg])
for b in ("fav -150..-101", "+100..+150", "+151..+199", "+200..+350"):
    drift(f"price {b}", [r for r in live if band(r["odds"]) == b], [r for r in P if band(r["odds"]) == b])
drift("hockey ½u", [r for r in live if r["lg"] == "nhl" and r["u"] < 0.75], [r for r in P if r["league"] == "nhl" and r["u0"] < 0.75])
drift("hockey 2u", [r for r in live if r["lg"] == "nhl" and tier(r["u"]) == "2u"], [r for r in P if r["league"] == "nhl" and tier(r["u0"]) == "2u"])
drift("NBA ½u", [r for r in live if r["lg"] == "nba" and r["u"] < 0.75], [r for r in P if r["league"] == "nba" and r["u0"] < 0.75])
drift("college football 1u", [r for r in live if r["lg"] == "ncaaf" and tier(r["u"]) == "1u"], [r for r in P if r["league"] == "ncaaf"])
print("  (the live college football 1u plays are 8 🔍 gap plays, paused 11/13 - no rows on this board - and the long Dog)")
