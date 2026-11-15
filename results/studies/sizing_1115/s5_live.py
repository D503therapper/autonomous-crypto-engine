"""11/15 - THE LIVE RECORD BY KIND (data/sports/picks.json + early.json, 9/27 -> 11/15) NEXT TO WHAT THE REPLAY PREDICTS
for that kind (the kind's flat ROI on boards R1 / R2, train + held - s1_kinds.out). Never the judge: for each kind the
wins the prices expected, the z, and whether the live record is inside what luck allows around the replay's rate.
Usage: python results/studies/sizing_1115/s5_live.py > results/studies/sizing_1115/s5_live.out"""
import json
import math
import os
from collections import defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
ps = json.load(open(os.path.join(REPO, "data", "sports", "picks.json")))
# the replay's flat ROI by kind, R1 / R2 (s1_kinds.out, train + held); None = not replayable on the boards
REPLAY = {"lock": (5.0, None), "dog": (17.2, 12.7), "floor": (8.0, 5.6), "nbafloor": (24.7, 22.3), "nbafav": (22.7, 34.1),
          "dogplay": (11.3, 22.1), "play": (1.6, 21.6)}
rows = []
for p in ps:
    if p.get("lean") or p.get("status") not in ("won", "lost") or not p.get("units") or len(p.get("legs") or []) != 1:
        continue
    if p.get("kind") not in ("lock", "dog", "play", "solo", "night"):
        continue
    l = p["legs"][0]
    dec = p.get("dec") or l.get("dec")
    if not dec:
        continue
    kind = p["kind"]
    if p.get("floor"):
        kind = "nbafloor" if (p["floor"] or {}).get("nba") else "floor"
    elif p.get("dog_play"):
        kind = "dogplay"
    elif p.get("gap") is not None:
        kind = "gap (🔍)"
    elif p.get("stack_play"):
        kind = "ncaab stack (spread)"
    elif p.get("ncaab_play"):
        kind = "ncaab slot"
    elif p.get("nba_fav"):
        kind = "nbafav"
    rows.append(dict(date=p["date"], kind=kind, u=float(p["units"]), dec=dec, won=p["status"] == "won", best=bool(p.get("best")),
                     lg=l.get("league"), team=l.get("team"), odds=l.get("odds")))


def show(name, rs, rep=None):
    if not rs:
        return
    n = len(rs)
    w = sum(r["won"] for r in rs)
    net = sum(r["u"] * (r["dec"] - 1) if r["won"] else -r["u"] for r in rs)
    fl = sum((r["dec"] - 1) if r["won"] else -1 for r in rs)
    risk = sum(r["u"] for r in rs)
    exp = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    sd = math.sqrt(sum(((r["dec"] - 1) ** 2) / r["dec"] + (1 - 1 / r["dec"]) for r in rs)) / n * 100   # ~ the luck in a flat ROI
    s = (f"  {name:26s} {w:3d}-{n - w:<3d} {net:+6.1f}u on {risk:5.1f}u ({100 * net / risk:+6.1f}%) flat {100 * fl / n:+6.1f}% "
         f"| the prices expected {exp:5.1f} wins, z {(w - exp) / math.sqrt(var) if var else 0:+.2f} | luck ±{sd:.0f}% a side")
    if rep:
        a, b = rep
        s += f" | replay R1 {a:+.1f}%" + (f" / R2 {b:+.1f}%" if b is not None else "")
        lo = min(x for x in rep if x is not None)
        s += " -> " + ("inside luck" if 100 * fl / n >= lo - 2 * sd else "UNDER the replay by more than luck")
    print(s)


print(f"graded board unit plays {min(r['date'] for r in rows)} -> {max(r['date'] for r in rows)}: {len(rows)}")
show("every board unit play", rows, (9.5, 9.5))
print("-- by kind")
by = defaultdict(list)
for r in rows:
    by[r["kind"]].append(r)
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    show(k, v, REPLAY.get(k))
print("-- by kind since the 10/31 sizing")
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    show(k, [r for r in v if r["date"] >= "2026-10-31"], REPLAY.get(k))
print("-- by size")
for lo, hi, nm in ((0, 0.75, "½u"), (0.75, 1.25, "1u"), (1.25, 2.25, "1.5-2u"), (2.25, 99, "3u+ (the old Kelly sizes)")):
    show(nm, [r for r in rows if lo <= r["u"] < hi])
print("-- by sport")
for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab", "mlb"):
    show(lg, [r for r in rows if r["lg"] == lg])
print("-- dogs / favorites")
show("dogs +100 and up", [r for r in rows if (r["odds"] or 0) >= 100])
show("favorites", [r for r in rows if (r["odds"] or 0) < 100])
show("the ⭐", [r for r in rows if r["best"]])

e = json.load(open(os.path.join(REPO, "data", "sports", "early.json")))
ep = e["picks"]
ep = list(ep.values()) if isinstance(ep, dict) else ep


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


print("-- THE EARLY PLAYS (early.json; units as posted - older rows with no stamped units count ½u)")
eb = defaultdict(list)
for p in ep:
    if p.get("result") not in ("won", "lost"):
        continue
    eb[p.get("spot") or "exam scan"].append(dict(u=float(p.get("units") or 0.5), dec=dec(p["odds"]), won=p["result"] == "won"))
for k, v in sorted(eb.items(), key=lambda kv: -len(kv[1])):
    show(k, v)
show("every early play", [x for v in eb.values() for x in v])
