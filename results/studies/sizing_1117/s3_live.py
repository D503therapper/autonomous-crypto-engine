"""11/17 - SIZING: THE LIVE RECORD BY SIZE since 10/25 (data/sports/picks.json + early.json) - the sanity check, never the
judge. Every graded unit play by the size it was posted at, by kind, and the ½u plays by the own read's edge over the
price (under it / 0-3c thin / 3c+). "What if every ½u play had been 1u / 2u" in units, next to what luck alone is.
Usage: python results/studies/sizing_1117/s3_live.py > results/studies/sizing_1117/s3_live.out"""
import json
import math
import os
from collections import defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
FROM = "2026-10-25"
ps = json.load(open(os.path.join(REPO, "data", "sports", "picks.json")))
rows = []
for p in ps:
    if p.get("lean") or p.get("status") not in ("won", "lost") or not p.get("units") or len(p.get("legs") or []) != 1:
        continue
    if p["date"] < FROM:
        continue
    l = p["legs"][0]
    dec = p.get("dec") or l.get("dec")
    if not dec:
        continue
    kind = p.get("kind")
    if p.get("floor"):
        kind = "NBA floor" if (p["floor"] or {}).get("nba") else ("floor (fallback)" if (p["floor"] or {}).get("fallback") else "floor")
    elif p.get("dog_play"):
        kind = "runner-up dog"
    elif p.get("gap") is not None:
        kind = "🔍 gap play"
    elif p.get("stack_play"):
        kind = "college hoops stack (spread)"
    elif p.get("ncaab_play"):
        kind = "college hoops slot"
    elif p.get("nba_fav"):
        kind = "NBA favorite play"
    elif kind == "play":
        kind = "value play"
    eo = l.get("edge_own")
    rows.append(dict(date=p["date"], kind=kind, u=float(p["units"]), dec=dec, won=p["status"] == "won", best=bool(p.get("best")),
                     lg=l.get("league"), team=l.get("team"), odds=l.get("odds"), eo=eo, market=l.get("market"),
                     dog_read=l.get("dog_read"), dog_score=(p.get("floor") or {}).get("dog_score")))


def show(name, rs):
    if not rs:
        return
    n = len(rs)
    w = sum(r["won"] for r in rs)
    net = sum(r["u"] * (r["dec"] - 1) if r["won"] else -r["u"] for r in rs)
    fl = sum((r["dec"] - 1) if r["won"] else -1 for r in rs)
    risk = sum(r["u"] for r in rs)
    exp = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    print(f"  {name:44s} {w:3d}-{n - w:<3d} {net:+6.1f}u on {risk:5.1f}u ({100 * net / risk:+6.1f}%) | flat 1u {fl:+6.1f}u ({100 * fl / n:+6.1f}%) "
          f"| the prices expected {exp:5.1f} wins, z {(w - exp) / math.sqrt(var) if var else 0:+.2f}")


def band(r):
    if r["eo"] is None:
        return "no own read on the card"
    return "own read UNDER the price" if r["eo"] < 0 else "own read 0-3c over (thin)" if r["eo"] < 0.03 else "own read 3c+ over"


print(f"graded board unit plays {min(r['date'] for r in rows)} -> {max(r['date'] for r in rows)}: {len(rows)}")
show("every board unit play", rows)
print("-- BY THE SIZE POSTED")
for lo, hi, nm in ((0, 0.75, "½u"), (0.75, 1.25, "1u"), (1.25, 1.75, "1.5u"), (1.75, 2.25, "2u"), (2.25, 99, "2.5u+")):
    show(nm, [r for r in rows if lo <= r["u"] < hi])
print("-- THE ½u PLAYS BY KIND")
by = defaultdict(list)
for r in rows:
    if r["u"] < 0.75:
        by[r["kind"]].append(r)
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    show(str(k), v)
print("-- THE ½u PLAYS BY THE OWN READ'S EDGE (the owner: 'a lot of the times when the engine has a thin edge ... it loses')")
half = [r for r in rows if r["u"] < 0.75]
for b in ("own read UNDER the price", "own read 0-3c over (thin)", "own read 3c+ over", "no own read on the card"):
    show(b, [r for r in half if band(r) == b])
lost = sum(r["u"] for r in half if not r["won"])
for b in ("own read UNDER the price", "own read 0-3c over (thin)", "own read 3c+ over", "no own read on the card"):
    x = sum(r["u"] for r in half if not r["won"] and band(r) == b)
    print(f"     {b}: {100 * x / lost if lost else 0:.0f}% of the ½u plays' lost units")
print("-- THE ½u PLAYS: dogs / favorites, by sport")
show("½u dogs", [r for r in half if (r["odds"] or 0) >= 100])
show("½u favorites", [r for r in half if (r["odds"] or 0) < 100])
for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab"):
    show("½u " + lg, [r for r in half if r["lg"] == lg])
print("-- THE 1u+ PLAYS BY KIND")
by = defaultdict(list)
for r in rows:
    if r["u"] >= 0.75:
        by[r["kind"]].append(r)
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    show(str(k), v)
show("the ⭐", [r for r in rows if r["best"]])
print("-- WHAT IF (the same live plays)")
for nm, f in (("as posted", lambda r: r["u"]), ("every ½u play at 1u", lambda r: max(1.0, r["u"])), ("every ½u play at 2u", lambda r: max(2.0, r["u"])),
              ("every ½u play OFF", lambda r: r["u"] if r["u"] >= 0.75 else 0.0), ("every play one step up", lambda r: {0.5: 1.0, 1.0: 2.0, 2.0: 3.0}.get(r["u"], r["u"]))):
    net = sum(f(r) * (r["dec"] - 1) if r["won"] else -f(r) for r in rows)
    risk = sum(f(r) for r in rows)
    per = defaultdict(float)
    for r in rows:
        per[r["date"]] += f(r) * (r["dec"] - 1) if r["won"] else -f(r)
    cum = peak = dd = 0.0
    for d in sorted(per):
        cum += per[d]
        peak = max(peak, cum)
        dd = min(dd, cum - peak)
    print(f"  {nm:26s} {net:+6.1f}u on {risk:5.1f}u ({100 * net / risk:+5.1f}%), worst stretch {dd:+.1f}u")
print("-- THE COLLEGE HOOPS PLAYS (every unit play, any kind), one line each")
for r in rows:
    if r["lg"] == "ncaab":
        print(f"  {r['date']} {str(r['team'])[:20]:20s} {r['odds']:+5d} {r['market'] or '':6s} {r['u']:g}u {'W' if r['won'] else 'L'} {r['kind']} read {r['dog_read']} own edge {r['eo']}")

e = json.load(open(os.path.join(REPO, "data", "sports", "early.json")))
ep = e["picks"]
ep = list(ep.values()) if isinstance(ep, dict) else ep


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


print("-- THE EARLY PLAYS since 10/25 by the game's day (early.json; units as posted - rows with no stamped units count ½u)")
er = []
for p in ep:
    if p.get("result") not in ("won", "lost") or (p.get("start") or "")[:10] < FROM:
        continue
    er.append(dict(u=float(p.get("units") or 0.5), dec=dec(p["odds"]), won=p["result"] == "won", spot=p.get("spot") or "exam scan"))
show("every early play", er)
for lo, hi, nm in ((0, 0.75, "½u"), (0.75, 1.25, "1u"), (1.25, 2.25, "1.5-2u"), (2.25, 99, "2.5u+")):
    show("early " + nm, [r for r in er if lo <= r["u"] < hi])
eb = defaultdict(list)
for r in er:
    eb[r["spot"]].append(r)
for k, v in sorted(eb.items(), key=lambda kv: -len(kv[1])):
    show("early spot: " + k, v)
