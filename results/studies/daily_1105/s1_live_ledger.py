"""S1 (part A) - the live unit-play ledger since 9/27 by size x side x kind (data/sports/picks.json, read only).
For each cell: W-L, units, the wins the PRICE expected (sum of 1/decimal) and a z of the actual wins vs that -
how unlikely the record is if these plays were exactly fair bets (no edge, no leak)."""
import json, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports  # noqa: E402

p = json.load(open("data/sports/picks.json"))
rows = []
for x in p:
    if x.get("date", "") < "2026-09-27" or x.get("status") not in ("won", "lost") or x.get("lean") \
            or x.get("pulled") or x.get("void"):
        continue
    u = sports.units_for(x)
    if not u:
        continue
    lg = (x.get("legs") or [{}])[0].get("league")
    sub = "floor" if x.get("floor") else "dog_play" if x.get("dog_play") else "gap" if x.get("gap") else x["kind"]
    side = "dog" if x["american"] > 0 else "fav"
    pr = (x["dec"] - 1) * u if x["status"] == "won" else -u
    rows.append(dict(date=x["date"], u=u, side=side, sub=sub, lg=lg, am=x["american"], won=x["status"] == "won",
                     pr=pr, p_hit=x.get("p_hit"), dec=x["dec"]))


def line(name, rs):
    if not rs:
        return
    w = sum(r["won"] for r in rs)
    st = sum(r["u"] for r in rs)
    pr = sum(r["pr"] for r in rs)
    exp = sum(r["p_hit"] or 0 for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    z = (w - bev) / math.sqrt(var) if var else 0
    print(f"{name:34s} {w:3d}-{len(rs)-w:<3d} {pr:+7.2f}u on {st:6.1f}u ({pr/st*100:+6.1f}%)  wins at the price "
          f"{bev:5.1f}  z {z:+.2f}  engine p_hit sum {exp:5.1f}")


print("LIVE UNIT PLAYS 9/27 -> today (graded), by size and side")
for k in sorted({(r["u"], r["side"]) for r in rows}):
    line(f"{k[0]}u {k[1]}", [r for r in rows if (r["u"], r["side"]) == k])
print()
half_dog = [r for r in rows if r["u"] == 0.5 and r["side"] == "dog"]
for k in sorted({r["sub"] for r in half_dog}):
    line(f"½u dog - {k}", [r for r in half_dog if r["sub"] == k])
for k in sorted({r["lg"] for r in half_dog}):
    line(f"½u dog - {k}", [r for r in half_dog if r["lg"] == k])
for lo, hi in ((100, 149), (150, 199), (200, 350)):
    line(f"½u dog +{lo}..+{hi}", [r for r in half_dog if lo <= r["am"] <= hi])
line("½u dog from 10/13 (floor era)", [r for r in half_dog if r["date"] >= "2026-10-13"])
print()
for r in sorted(half_dog, key=lambda r: r["date"]):
    print(f"  {r['date']} {r['lg']:6s} {r['sub']:9s} {r['am']:+5d} {'W' if r['won'] else 'L'} p_hit {r['p_hit']}")
print()
line("ALL unit plays", rows)
line("ALL dogs", [r for r in rows if r["side"] == "dog"])
line("ALL favs", [r for r in rows if r["side"] == "fav"])
