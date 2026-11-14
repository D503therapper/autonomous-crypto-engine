"""11/14 - THE LIVE CHECK (never the judge): every graded board unit play in data/sports/picks.json since 9/27, by size,
by kind and the ⭐ - won / lost, units, ROI, and the wins the prices expected (z).
Usage: python results/studies/sizing_1114/s4_live.py > results/studies/sizing_1114/s4_live.out"""
import json
import math
import os
from collections import defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
ps = json.load(open(os.path.join(REPO, "data", "sports", "picks.json")))
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
        kind = "gap"
    elif p.get("ncaab_play"):
        kind = "ncaabplay"
    elif p.get("nba_fav"):
        kind = "nbafav"
    rows.append(dict(date=p["date"], kind=kind, u=float(p["units"]), dec=dec, won=p["status"] == "won", best=bool(p.get("best")),
                     lg=l.get("league"), team=l.get("team"), odds=l.get("odds")))


def show(name, rs):
    if not rs:
        return
    w = sum(r["won"] for r in rs)
    net = sum(r["u"] * (r["dec"] - 1) if r["won"] else -r["u"] for r in rs)
    risk = sum(r["u"] for r in rs)
    exp = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    print(f"  {name:34s} {w:3d}-{len(rs) - w:<3d} {net:+6.1f}u on {risk:5.1f}u ({100 * net / risk:+6.1f}%) | wins the prices expected "
          f"{exp:5.1f}, z {(w - exp) / math.sqrt(var) if var else 0:+.2f}")


print(f"graded board unit plays {min(r['date'] for r in rows)} -> {max(r['date'] for r in rows)}: {len(rows)}")
show("every unit play", rows)
print("-- by size")
for lo, hi, nm in ((0, 0.75, "½u"), (0.75, 1.25, "1u"), (1.25, 2.25, "2u"), (2.25, 99, "3u+")):
    show(nm, [r for r in rows if lo <= r["u"] < hi])
print("-- by kind")
by = defaultdict(list)
for r in rows:
    by[r["kind"]].append(r)
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    show(k, v)
print("-- the ⭐ (from 11/4)")
show("the ⭐", [r for r in rows if r["best"]])
for r in rows:
    if r["best"]:
        print(f"     {r['date']} {r['kind']:8s} {r['lg']:5s} {r['team']:16s} {r['odds']:+5d} {r['u']:g}u {'W' if r['won'] else 'L'}")
show("unit plays from 11/4 that were NOT the ⭐", [r for r in rows if not r["best"] and r["date"] >= "2026-11-04"])
print("-- the floor's hockey dogs live")
show("floor, hockey", [r for r in rows if r["kind"] == "floor" and r["lg"] == "nhl"])
show("the Dog of the Day, hockey", [r for r in rows if r["kind"] == "dog" and r["lg"] == "nhl"])
