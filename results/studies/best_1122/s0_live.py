"""11/22 - WHY THE ⭐ HAS LOST - (0) THE LIVE RECORD from data/sports/picks.json: every graded ⭐ since 11/4 against every
other graded unit play of the same days - the units as graded, flat 1u, the wins the prices expect, z; and the ⭐'s raise
(the units over the play's own size) apart.
Usage: python results/studies/best_1122/s0_live.py > results/studies/best_1122/s0_live.out"""
import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(REPO)
sys.path.insert(0, REPO)
import sports  # noqa: E402

P = json.load(open("data/sports/picks.json"))
P = P if isinstance(P, list) else P.get("picks")
star, oth = [], []
for p in P:
    if (p.get("date") or "") < "2026-11-04" or p.get("lean") or p.get("status") not in ("won", "lost"):
        continue
    if len(p.get("legs") or []) != 1 or not p.get("units") or p.get("kind") not in ("lock", "dog", "solo", "night", "play"):
        continue
    (star if p.get("best") else oth).append(p)


def fl(p):
    return (p["dec"] - 1) if p["status"] == "won" else -1.0


def rep(name, x, units=lambda p: p["units"]):
    if not x:
        print(f"  {name:44s} none")
        return
    w = sum(p["status"] == "won" for p in x)
    u = sum(units(p) for p in x)
    net = sum(units(p) * fl(p) for p in x)
    ex = sum(1 / p["dec"] for p in x)
    var = sum(1 / p["dec"] * (1 - 1 / p["dec"]) for p in x)
    print(f"  {name:44s} {w}-{len(x) - w}  {net:+6.2f}u on {u:5.1f}u ({100 * net / u if u else 0:+6.1f}%) | flat 1u {sum(map(fl, x)):+6.2f}u"
          f" | the prices expect {ex:4.1f} wins, z {(w - ex) / math.sqrt(var):+.2f}")


def own(p):
    """the play's own size - the ⭐ raise off (the engine's sizing on the graded pick, the star taken away)."""
    q = dict(p)
    q.pop("best", None)
    q.pop("best_2u", None)
    q["status"] = "open"
    q.pop("units", None)
    try:
        return sports._units_base(q) or 0.5
    except Exception:
        return p["units"]


print("THE ⭐ LIVE, 11/4 on (graded)")
for p in star:
    l = p["legs"][0]
    k = sports.posted_kind(p)
    print(f"   {p['date']} {k:10s} {l.get('league'):6s} {str(l.get('team'))[:22]:22s} {l.get('odds'):+5d} {p['units']:g}u (own size {own(p):g}u) {p['status']:5s}"
          f" | dog score {l.get('dog_score')} read {sports.read_of(l)} needs {round(1 / p['dec'], 3)}")
print()
rep("the ⭐ (as graded)", star)
rep("the ⭐ at its OWN size (no raise)", star, own)
rep("the ⭐'s raise alone (the added units)", [p for p in star if p["units"] > own(p)], lambda p: p["units"] - own(p))
rep("every other unit play", oth)
print()
for nm, t in (("⭐ dogs", lambda p: p["legs"][0]["odds"] >= 100), ("⭐ favorites", lambda p: p["legs"][0]["odds"] < 0),
              ("⭐ hockey", lambda p: p["legs"][0]["league"] == "nhl"), ("⭐ college", lambda p: p["legs"][0]["league"] in ("ncaaf", "ncaab")),
              ("⭐ NBA / NFL", lambda p: p["legs"][0]["league"] in ("nba", "nfl"))):
    rep(nm, [p for p in star if t(p)])
for nm, t in (("other dogs", lambda p: p["legs"][0]["odds"] >= 100), ("other favorites", lambda p: p["legs"][0]["odds"] < 0)):
    rep(nm, [p for p in oth if t(p)])
print("\nby the kind the ⭐ sat on")
for k in sorted({sports.posted_kind(p) for p in star}):
    rep("⭐ on " + k, [p for p in star if sports.posted_kind(p) == k])
print("\nthe graded unit plays of each ⭐ day (own size = the raise off)")
days = sorted({p["date"] for p in star})
for d in days:
    ps = [p for p in star + oth if p["date"] == d]
    s = " ; ".join(f"{'⭐' if p.get('best') else ''}{str(p['legs'][0].get('team'))[:14]} {p['legs'][0].get('odds'):+d} {own(p):g}u {p['status'][0].upper()}" for p in ps)
    print(f"   {d}: {s}")
