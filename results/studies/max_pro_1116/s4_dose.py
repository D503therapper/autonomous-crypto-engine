"""11/16 MAX PLAY HUNT - S4: IS THE 8+ A DOSE OR A LUCKY CUT? The score clusters (6-7 = the gate, 8-9 = the b2b spot with the
studies at their cap), so the score bands alone can't show a dose. Here the pieces are taken apart on the 2020-23 rig:
  every dog +100..+350 that passes the Dog's checks, split by (a) the b2b spot or not, (b) the OTHER study points on it
  (the capped study sum minus the +3 the b2b spot itself adds) - does MORE agreement win MORE, with and without the spot?
and on the boards (2023-26): the same two axes from the row's dog score minus its own-read gap (the capped study part).
Usage: python results/studies/max_pro_1116/s4_dose.py > results/studies/max_pro_1116/s4_dose.out"""
import contextlib
import importlib.util
import io
import math
import os
import sys

import mp

HERE = os.path.dirname(os.path.abspath(__file__))
STUD = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(STUD, "sizing_1114"))
_d = sys.modules.pop("lib")
import lib as L  # noqa: E402
BO = L.boards()
sys.modules.pop("lib")
NH = os.path.join(STUD, "nhl_odds_1102")
sys.path.insert(0, NH)
with contextlib.redirect_stdout(io.StringIO()):
    spec = importlib.util.spec_from_file_location("s1h", os.path.join(NH, "s1_hockey_dog.py"))
    s1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s1)
nlib = sys.modules["lib"]
sys.modules["lib"] = _d
RAW = {(r["date"], r["team"]): r for r in mp.build("nhl")}


def st(rs):
    n = len(rs)
    if not n:
        return "n   0"
    w = sum(r["won"] for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    return f"n {n:4d} {w:3d}-{n - w:<4d} {100 * w / n:4.1f}% (needs {100 * bev / n:4.1f}) {100 * sum(r['prof'] for r in rs) / n:+6.1f}% z {(w - bev) / math.sqrt(var):+4.2f}"


rows = []
for day, xs in sorted(s1.cands("morning").items()):
    for y in xs:
        if s1.fighting(y) or y["own"] < y["pm"]:
            continue
        sc, parts = nlib.dog_score(y, drift=y["drift"], parts=True)
        raw = sum(parts.values()) + nlib.OT_W.get(y["ot"], 0) + (2 if y["oot"] == "ot_loss" else 0)
        rb = bool(y["ob2b"] and not y["b2b"])
        rows.append(dict(season=y["r"]["season"], odds=y["am"], dec=y["dec"], won=bool(y["won"]), prof=y["profit"], rb=rb,
                         study=max(-6, min(6, raw)), other=raw - (3 if rb else 0), score=sc, gap=y["gap"]))
print("================ OOS 2020-23 (morning price): every dog +100..+350 that passes the Dog's checks ================")
print(f"  all {st(rows)}")
for rb in (True, False):
    x = [r for r in rows if r["rb"] == rb]
    print(f" {'THE B2B SPOT (rested dog, the favorite played last night)' if rb else 'NO b2b spot'}: {st(x)}")
    for lo, hi in ((-99, -2), (-2, 0), (0, 2), (2, 3.5), (3.5, 5), (5, 99)):
        print(f"    the OTHER study points {lo:>5}..{hi:<4} {st([r for r in x if lo <= r['other'] < hi])}")
    for c in (0, 1, 2, 3, 4):
        print(f"    other points {c}+ {st([r for r in x if r['other'] >= c])} | under {st([r for r in x if r['other'] < c])[:58]}")
print("  (the 8+ Dog = the b2b spot with 2.1+ other points; the dose to read: the b2b rows above)")
print("  the b2b spot at +100..+150 only:")
x = [r for r in rows if r["rb"] and r["odds"] <= 150]
for c in (0, 1, 2, 3, 4):
    print(f"    other points {c}+ {st([r for r in x if r['other'] >= c])} | under {st([r for r in x if r['other'] < c])[:58]}")

for name in ("R1", "R2"):
    bd, by = BO[name]
    rs = []
    for d in sorted(by):
        if L.half(d) == "live":
            continue
        for r in by[d]:
            if r["league"] != "nhl" or r["result"] not in ("won", "lost") or not 100 <= r["odds"] <= 350 or r.get("dog_score") is None:
                continue
            if r.get("fighting") or r.get("trap") or not r.get("dog_own_ok"):
                continue
            w = RAW.get((d, r["team"]))
            if not w:
                continue
            rb = bool(w["o_b2b"] and not w["b2b"])
            study = r["dog_score"] - min(r["own_gap"], 12)          # the capped study part (dog_score_base's cap is OWN_CAP)
            rs.append(dict(season=L.season(d), odds=r["odds"], dec=r["dec"], won=r["result"] == "won",
                           prof=(r["dec"] - 1) if r["result"] == "won" else -1.0, rb=rb, study=study, other=study - (3 if rb else 0),
                           score=r["dog_score"], gap=r["own_gap"]))
    print(f"\n================ BOARD {name} 2023-26: every hockey dog that passes the Dog's checks (any score) ================")
    print(f"  all {st(rs)}")
    for rb in (True, False):
        x = [r for r in rs if r["rb"] == rb]
        print(f" {'THE B2B SPOT' if rb else 'NO b2b spot'}: {st(x)} | own gap avg {sum(r['gap'] for r in x) / max(1, len(x)):.2f}")
        for lo, hi in ((-99, 0), (0, 3), (3, 5), (5, 5.99), (5.99, 99)):
            print(f"    the study part of the score {lo:>5}..{hi:<5} {st([r for r in x if lo <= r['study'] < hi])}")
        for c in (6, 7, 8, 8.5):
            print(f"    score {c}+ {st([r for r in x if r['score'] >= c])}")
    print(f"  THE STRUCTURAL CUT on {name} (the b2b spot + the study part at its cap, whatever the own-read gap), every season:")
    x = [r for r in rs if r["rb"] and r["study"] >= 5.99]
    se = {}
    for r in x:
        se.setdefault(r["season"], []).append(r)
    for k, v in sorted(se.items()):
        print(f"    {k}: {st(v)} | own gap avg {sum(r['gap'] for r in v) / len(v):.2f} | score 8+ {sum(1 for r in v if r['score'] >= 8)}")
    print(f"    own gap 2+ (score 8+): {st([r for r in x if r['score'] >= 8])} | own gap under 2 (score under 8): {st([r for r in x if r['score'] < 8])}")
