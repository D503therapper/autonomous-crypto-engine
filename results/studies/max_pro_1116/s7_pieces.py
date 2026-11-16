"""11/16 MAX PLAY HUNT - S7: WHICH PIECES CARRY THE 8+ (the 2020-23 rig, the b2b-spot Dogs of the Day). The max play is
"the b2b spot + the other angles at their cap". Is it one angle doing the work (then it is one factor in disguise) or
several? Each piece the rig can rebuild, on the 107 b2b-spot Dogs: with it / without it; and the 8+ Dogs with each
piece taken away (does the cell survive losing any single piece?).
Usage: python results/studies/max_pro_1116/s7_pieces.py > results/studies/max_pro_1116/s7_pieces.out"""
import contextlib
import importlib.util
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NH = os.path.join(os.path.dirname(HERE), "nhl_odds_1102")
sys.path.insert(0, NH)
import lib as nlib  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    spec = importlib.util.spec_from_file_location("s1h", os.path.join(NH, "s1_hockey_dog.py"))
    s1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s1)


def st(rs):
    n = len(rs)
    if not n:
        return "n   0"
    w = sum(r["won"] for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    return f"n {n:3d} {w:3d}-{n - w:<3d} {100 * w / n:4.1f}% (needs {100 * bev / n:4.1f}) {100 * sum(r['prof'] for r in rs) / n:+6.1f}% z {(w - bev) / math.sqrt(var):+4.2f}"


dogs = []
for day, xs in sorted(s1.cands("morning").items()):
    x, kind = s1.pick(xs)
    if not x or not (x["ob2b"] and not x["b2b"]):
        continue
    sc, parts = nlib.dog_score(x, drift=x["drift"], parts=True)
    parts = dict(parts)
    if nlib.OT_W.get(x["ot"], 0):
        parts["ot_" + str(x["ot"])] = nlib.OT_W[x["ot"]]
    if x["oot"] == "ot_loss":
        parts["fav_off_ot_loss"] = 2
    dogs.append(dict(dec=x["dec"], won=bool(x["won"]), prof=x["profit"], score=sc, parts=parts, gap=x["gap"], odds=x["am"]))
print(f"the b2b-spot Dogs of the Day, 2020-23, morning price: {st(dogs)}")
print(f"   at 8+: {st([r for r in dogs if r['score'] >= 8])} | under 8: {st([r for r in dogs if r['score'] < 8])}")
names = sorted({k for r in dogs for k, v in r["parts"].items() if v and k != "rested_vs_b2b"})
print("\n piece (its points)                     | Dogs WITH it                                        | 8+ Dogs with it          | 8+ Dogs WITHOUT it")
for k in names:
    for sign, lab in ((1, "+"), (-1, "-")):
        w_ = [r for r in dogs if (r["parts"].get(k) or 0) * sign > 0]
        if not w_:
            continue
        e_w = [r for r in w_ if r["score"] >= 8]
        e_wo = [r for r in dogs if r["score"] >= 8 and not (r["parts"].get(k) or 0) * sign > 0]
        v = sorted({r["parts"][k] for r in w_})
        print(f"  {k:18s} {lab} {str(v):12s} | {st(w_)} | {st(e_w)[:26]} | {st(e_wo)}")
print("\n the 8+ Dogs by how many + pieces (besides the b2b spot) agree, and by any piece against:")
e = [r for r in dogs if r["score"] >= 8]
for n in (1, 2, 3, 4):
    print(f"   {n} other + piece(s): {st([r for r in e if sum(1 for k, v in r['parts'].items() if v > 0 and k != 'rested_vs_b2b') == n])}")
print(f"   a piece against on it: {st([r for r in e if any(v < 0 for v in r['parts'].values())])} | none against: {st([r for r in e if not any(v < 0 for v in r['parts'].values())])}")
u = [r for r in dogs if r["score"] < 8]
print(f" the b2b Dogs UNDER 8: a piece against {st([r for r in u if any(v < 0 for v in r['parts'].values())])} | none against {st([r for r in u if not any(v < 0 for v in r['parts'].values())])}")
