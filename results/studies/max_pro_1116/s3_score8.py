"""11/16 MAX PLAY HUNT - S3: THE HOCKEY DOG AT A DOG SCORE OF 8+ - THE FIVE CHECKS.
S2 found one cell: the hockey Dog of the Day whose dog score is 8 or more (the favorite's back-to-back + its own read +
three more points of study angles agreeing - the confluence the brief asks about). It has been a tracker LEAD since
10/30 on the 2023-26 board rows (20-11; placebo 314-437 of 2,000 inside the 2u Dogs, too thin to act on). The NEW
evidence: the 11/2 NHL paid-odds rig, 2020-23, three seasons the 8+ cut was never chosen on.
Here: (1) the dose (score bands, every neighbouring cutoff) on each rig; (2) every season apart; (3) the placebo;
(4) the open / morning / close price and a few cents worse; (5) the price bands; (6) what the 8+ is made of; (7) live;
(8) the size by the brief's formula and what each size does to the Dog's own worst stretch.
Usage: python results/studies/max_pro_1116/s3_score8.py > results/studies/max_pro_1116/s3_score8.out"""
import contextlib
import importlib.util
import io
import json
import math
import os
import random
import sys
from collections import defaultdict, Counter

import mp

HERE = os.path.dirname(os.path.abspath(__file__))
STUD = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(STUD))
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


def st(rs, key="prof"):
    n = len(rs)
    if not n:
        return "n   0"
    w = sum(r["won"] for r in rs)
    bev = sum(1 / r["dec"] for r in rs)
    var = sum((1 / r["dec"]) * (1 - 1 / r["dec"]) for r in rs)
    return f"n {n:3d} {w:3d}-{n - w:<3d} {100 * w / n:4.1f}% (needs {100 * bev / n:4.1f}) {100 * sum(r[key] for r in rs) / n:+6.1f}% z {(w - bev) / math.sqrt(var):+4.2f}"


def seasons(rs):
    s = defaultdict(list)
    for r in rs:
        s[r["season"]].append(r)
    return " ".join(f"{k}:{sum(x['won'] for x in v)}-{len(v) - sum(x['won'] for x in v)}/{100 * sum(x['prof'] for x in v) / len(v):+.0f}%" for k, v in sorted(s.items()))


def plc(sel, pool, n=2000, seed=7):
    rnd = random.Random(seed)
    ps = [r["prof"] for r in pool]
    tgt = sum(r["prof"] for r in sel)
    return sum(1 for _ in range(n) if sum(rnd.sample(ps, len(sel))) >= tgt)


# ------------------------------------------------------------ the rigs
def oos(at="morning"):
    """(the day's Dog picks, every dog that passes the Dog's checks) on the 2020-23 rig at a price point"""
    bd = s1.cands(at)
    dogs, allc = [], []
    for day, xs in sorted(bd.items()):
        x, kind = s1.pick(xs)
        for y in xs:
            if s1.fighting(y) or y["own"] < y["pm"]:
                continue
            sc, parts = nlib.dog_score(y, drift=y["drift"], parts=True)
            row = dict(src="OOS", date=day, season=y["r"]["season"], odds=y["am"], dec=y["dec"], won=bool(y["won"]),
                       prof=y["profit"], cprof=s1.close_profit(y), score=y["score"], gap=y["gap"], home=y["home"],
                       rb=y["ob2b"] and not y["b2b"], parts=parts, kind=kind if y is x else None, team=y["team"])
            allc.append(row)
            if y is x:
                dogs.append(row)
    return dogs, allc


def board(name):
    bd, by = BO[name]
    dogs, allc = [], []
    for d in sorted(bd):
        hf = L.half(d)
        posted = {id(r) for r, u, k in bd[d] if k == "dog"}
        for r in by.get(d, []):
            if r["league"] != "nhl" or r["result"] not in ("won", "lost") or not 100 <= r["odds"] <= 350 or r.get("dog_score") is None:
                continue
            row = dict(src=name, date=d, season=L.season(d), odds=r["odds"], dec=r["dec"], won=r["result"] == "won",
                       prof=(r["dec"] - 1) if r["result"] == "won" else -1.0, score=r["dog_score"], gap=r["own_gap"],
                       home=r["home"], half=hf, kind="dog" if id(r) in posted else None, team=r["team"],
                       ok=bool(r.get("dog_gate")) and not r.get("fighting") and not r.get("trap") and bool(r.get("dog_own_ok")))
            row["cprof"] = row["prof"]
            if id(r) in posted:
                dogs.append(row)
            if row["ok"]:
                allc.append(row)
    return dogs, allc


O_DOGS, O_ALL = oos("morning")
R = {n: board(n) for n in ("R1", "R2")}
BANDS = ((-99, 3), (3, 6), (6, 7), (7, 8), (8, 9), (9, 99))

print("================ (1) THE DOSE - the Dog of the Day by its dog score, each rig ================")
for nm, dogs in (("OOS 2020-23 (morning price)", O_DOGS), ("R1 2023-26 (the 10/30 rows)", [r for r in R["R1"][0] if r["half"] != "live"]),
                 ("R2 2023-26 (today's code)", [r for r in R["R2"][0] if r["half"] != "live"])):
    print(f" {nm}: every Dog {st(dogs)}")
    for lo, hi in BANDS:
        print(f"    score {lo:>3}..{hi:<3} {st([r for r in dogs if lo <= r['score'] < hi])}")
    for c in (6.5, 7, 7.5, 8, 8.5, 9):
        sel = [r for r in dogs if r["score"] >= c]
        rest = [r for r in dogs if r["score"] < c]
        print(f"    score {c}+     {st(sel)} | under it {st(rest)[:60]}")
print("\n================ (1b) EVERY hockey dog that passes the Dog's checks (not only the day's one), by score ================")
for nm, allc in (("OOS 2020-23", O_ALL), ("R1 2023-26", [r for r in R["R1"][1] if r["half"] != "live"]), ("R2 2023-26", [r for r in R["R2"][1] if r["half"] != "live"])):
    print(f" {nm}:")
    for lo, hi in ((6, 7), (7, 8), (8, 9), (9, 99)) if nm != "OOS 2020-23" else BANDS:
        print(f"    score {lo:>3}..{hi:<3} {st([r for r in allc if lo <= r['score'] < hi])}")
    x8 = [r for r in allc if r["score"] >= 8]
    print(f"    every 8+ {st(x8)} | the day's Dog among them {sum(1 for r in x8 if r['kind'])} | not the Dog {st([r for r in x8 if not r['kind']])}")

print("\n================ (2) EVERY SEASON APART - the Dog at 8+ ================")
o8 = [r for r in O_DOGS if r["score"] >= 8]
for nm in ("R1", "R2"):
    b8 = [r for r in R[nm][0] if r["score"] >= 8 and r["half"] != "live"]
    lv = [r for r in R[nm][0] if r["score"] >= 8 and r["half"] == "live"]
    print(f" OOS + {nm}: {st(o8 + b8)}")
    print(f"    OOS  {st(o8)} | {seasons(o8)}")
    print(f"    {nm}   {st(b8)} | {seasons(b8)} | train {st([r for r in b8 if r['half'] == 'train'])[:36]} | held {st([r for r in b8 if r['half'] == 'held'])[:36]}")
    print(f"    the board's live window (10/13 on): {st(lv)}")

print("\n================ (3) THE PLACEBO - 2,000 same-size draws ================")
for nm in ("R1", "R2"):
    bd_ = [r for r in R[nm][0] if r["half"] != "live"]
    b8 = [r for r in bd_ if r["score"] >= 8]
    print(f" {nm}: 8+ vs every Dog on that board {plc(b8, bd_)} of 2,000 | OOS: 8+ vs every OOS Dog {plc(o8, O_DOGS)} of 2,000 | pooled {plc(o8 + b8, O_DOGS + bd_)} of 2,000")
    rb_o = [r for r in O_DOGS if r["rb"]]
    print(f"    OOS, inside the rested-vs-b2b Dogs only ({st(rb_o)[:40]}): 8+ {st([r for r in rb_o if r['score'] >= 8])[:44]} vs under 8 {st([r for r in rb_o if r['score'] < 8])[:44]}"
          f" | placebo {plc([r for r in rb_o if r['score'] >= 8], rb_o)} of 2,000")
    short = [r for r in O_DOGS + bd_ if r["odds"] <= 150]
    print(f"    inside the short Dogs (+100..+150): 8+ {st([r for r in short if r['score'] >= 8])} | placebo {plc([r for r in short if r['score'] >= 8], short)} of 2,000")
    # the most honest draw: random hockey dogs at the same prices (every dog +100..+350 of the raw rig, 2020-26)
RAW = [r for r in mp.build("nhl") if 100 <= r["odds"] <= 350 and r["season"] >= 2020]
allp = o8 + [r for r in R["R1"][0] if r["score"] >= 8 and r["half"] != "live"]
print(f" against EVERY hockey dog +100..+350 at the close 2020-26 ({len(RAW)}, {100 * sum(r['prof'] for r in RAW) / len(RAW):+.1f}%): {plc(allp, RAW)} of 2,000")

print("\n================ (4) THE PRICE POINT (OOS rig) and a few cents worse ================")
for at in ("open", "morning"):
    d_, _ = oos(at)
    x = [r for r in d_ if r["score"] >= 8]
    print(f" the Dog at 8+, picked and graded at the {at:8s} {st(x)} | {seasons(x)}")
    if at == "morning":
        print(f"    the same picks graded at the CLOSE   {st(x, 'cprof')}")
allb = o8 + [r for r in R["R1"][0] if r["score"] >= 8 and r["half"] != "live"]
for c in (5, 10, 15):
    w = mp.worse(allb, c)
    print(f" pooled (OOS + R1) at {c} cents worse: {st(w)}")

print("\n================ (5) THE PRICE BANDS inside the 8+ Dog (pooled OOS + R1 | OOS + R2) ================")
for nm in ("R1", "R2"):
    p8 = o8 + [r for r in R[nm][0] if r["score"] >= 8 and r["half"] != "live"]
    for lo, hi in ((100, 119), (120, 150), (100, 150), (151, 199), (200, 350), (151, 350)):
        x = [r for r in p8 if lo <= r["odds"] <= hi]
        print(f"  {nm} +{lo}..+{hi}: {st(x)} | OOS {st([r for r in x if r['src'] == 'OOS'])[:36]} | board {st([r for r in x if r['src'] != 'OOS'])[:36]}")
    print(f"  {nm} at home {st([r for r in p8 if r['home']])} | on the road {st([r for r in p8 if not r['home']])}")

print("\n================ (6) WHAT THE 8+ IS MADE OF (OOS rig - the score's pieces) ================")
print(f"  rested vs a b2b favorite: {sum(1 for r in o8 if r['rb'])} of {len(o8)}; own gap avg {sum(r['gap'] for r in o8) / len(o8):.2f}")
cnt = Counter(k for r in o8 for k in r["parts"])
print("  pieces on the 8+ Dogs: " + ", ".join(f"{k} {v}" for k, v in cnt.most_common()))
npos = Counter(sum(1 for k, v in r["parts"].items() if v > 0) for r in o8)
print("  how many + pieces agree: " + ", ".join(f"{k}: {v}" for k, v in sorted(npos.items())))
for k in (2, 3, 4):
    x = [r for r in O_DOGS if r["rb"] and sum(1 for kk, v in r["parts"].items() if v > 0) >= k and not any(v < 0 for v in r["parts"].values())]
    print(f"  OOS b2b-edge Dogs with {k}+ pieces agreeing and none against: {st(x)}")
x = [r for r in O_DOGS if r["rb"] and any(v < 0 for v in r["parts"].values())]
print(f"  OOS b2b-edge Dogs with ANY piece against: {st(x)}")

print("\n================ (7) LIVE - the posted hockey Dogs with a dog score on file (10/19 on) ================")
pk = json.load(open(os.path.join(ROOT, "data/sports/picks.json")))
lv = []
for q in pk:
    lg = (q.get("legs") or [{}])[0]
    if lg.get("league") == "nhl" and q.get("kind") == "dog" and lg.get("dog_score") is not None and q.get("status") in ("won", "lost") and not q.get("pulled"):
        lv.append(dict(date=q["date"], team=lg.get("team"), odds=q["american"], dec=q["dec"], won=q["status"] == "won",
                       prof=(q["dec"] - 1) if q["status"] == "won" else -1.0, score=lg["dog_score"], units=q.get("units"), season="live"))
for r in lv:
    print(f"   {r['date']} {r['team']:14s} {r['odds']:+5d} {r['units']}u score {r['score']:5.2f} {'WON' if r['won'] else 'lost'}")
print(f"  live 8+ {st([r for r in lv if r['score'] >= 8])} | live under 8 {st([r for r in lv if r['score'] < 8])}")

print("\n================ (8) THE SIZE (a quarter of Kelly on the LOW end of the win rate; 1u = 1% of the roll; cap 4u) ================")
for nm, h in (("OOS 2020-23 (the seasons the 8+ cut never saw - the held-out half)", o8),
              ("R1 2023-26", [r for r in R["R1"][0] if r["score"] >= 8 and r["half"] != "live"]),
              ("R2 2023-26", [r for r in R["R2"][0] if r["score"] >= 8 and r["half"] != "live"]),
              ("pooled OOS + R1", allb), ("pooled OOS + R1 + live", allb + [r for r in lv if r["score"] >= 8])):
    n = len(h)
    wp = sum(r["won"] for r in h) / n
    se = math.sqrt(wp * (1 - wp) / n)
    d = n / sum(1 / r["dec"] for r in h)
    print(f"  {nm}: {wp * 100:.1f}% on {n} (se {se * 100:.1f}) at avg dec {d:.2f} -> -1 se {mp.kelly_units(wp, se, d, cap=99):.2f}u | -1.5 se {mp.kelly_units(wp, 1.5 * se, d, cap=99):.2f}u | -2 se {mp.kelly_units(wp, 2 * se, d, cap=99):.2f}u")


def worst(rs, fn):
    per = defaultdict(float)
    for r in rs:
        per[r["date"]] += fn(r) * r["prof"]
    cum = peak = w = 0.0
    for d in sorted(per):
        cum += per[d]
        peak = max(peak, cum)
        w = min(w, cum - peak)
    return w


today = lambda r: 2.0 if r["odds"] <= 150 else 0.5   # noqa: E731
print("  THE DOG OF THE DAY's units under each max-play size (8+ = the max play; the other Dogs keep today's 2u / ½u):")
for nm, dogs in (("OOS 2020-23", O_DOGS), ("R1 2023-26", [r for r in R["R1"][0] if r["half"] != "live"]), ("R2 2023-26", [r for r in R["R2"][0] if r["half"] != "live"])):
    for lab, fn in (("today (2u / ½u)", today), ("8+ at 2u any price", lambda r: 2.0 if r["score"] >= 8 else today(r)),
                    ("8+ at 3u", lambda r: 3.0 if r["score"] >= 8 else today(r)), ("8+ at 4u", lambda r: 4.0 if r["score"] >= 8 else today(r)),
                    ("8+ at 3u only at +100..+150", lambda r: 3.0 if r["score"] >= 8 and r["odds"] <= 150 else today(r))):
        net = sum(fn(r) * r["prof"] for r in dogs)
        risk = sum(fn(r) for r in dogs)
        print(f"    {nm:12s} {lab:30s} {net:+7.1f}u on {risk:6.1f}u ({100 * net / risk:+5.1f}%) worst stretch {worst(dogs, fn):+6.1f}u")
print("\n  how often: " + ", ".join(f"{nm} {len(x)} in {len(set(r['season'] for r in x))} seasons" for nm, x in (("OOS", o8), ("R1", [r for r in R['R1'][0] if r['score'] >= 8]), ("R2", [r for r in R['R2'][0] if r['score'] >= 8]))))

print("\n================ (9) THE RULE AS WIRED: the hockey Dog of the Day, dog score 8+, rested against a favorite that played last night ================")
RAWK = {(r["date"], r["team"]): r for r in mp.build("nhl")}
for nm in ("R1", "R2"):
    b8 = []
    for r in R[nm][0]:
        if r["score"] >= 8 and r["half"] != "live":
            w = RAWK.get((r["date"], r["team"]))
            if w and w["o_b2b"] and not w["b2b"]:
                b8.append(r)
    o8b = [r for r in o8 if r["rb"]]
    print(f"  OOS {st(o8b)} | {nm} {st(b8)} | pooled {st(o8b + b8)}")
    h = o8b + b8
    wp = sum(r["won"] for r in h) / len(h)
    se = math.sqrt(wp * (1 - wp) / len(h))
    d = len(h) / sum(1 / r["dec"] for r in h)
    print(f"     pooled {wp * 100:.1f}% on {len(h)} at avg dec {d:.2f} (about {round((d - 1) * 100):+d}): quarter-Kelly -1 se {mp.kelly_units(wp, se, d, cap=99):.2f}u | -1.5 se {mp.kelly_units(wp, 1.5 * se, d, cap=99):.2f}u | -2 se {mp.kelly_units(wp, 2 * se, d, cap=99):.2f}u")
    print(f"     at 3u: {sum(3 * r['prof'] for r in h):+.1f}u on {3 * len(h)}u; worst stretch {worst(h, lambda r: 3.0):+.1f}u; the longest losing run {max((len(x) for x in ''.join('W' if r['won'] else 'L' for r in sorted(h, key=lambda r: r['date'])).split('W')), default=0)}")
