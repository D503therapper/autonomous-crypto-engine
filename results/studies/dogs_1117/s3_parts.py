"""11/17 UNDERDOG EDGE - (3) THE DOG SCORE'S PARTS: which weights still earn, which are dead (R3, funnel6.py).
For every dog the funnel wrote what each fact on the candidate is WORTH in its dog score (the score with the fact taken
off, the cap lifted) -> r["parts"] = {fact: points}. For every (sport, fact, sign):
  the dogs the weight ADDS points to should beat the sport's other dogs; the dogs it TAKES points from should lose more.
  'earns' = the right way against the sport's dogs in BOTH halves; 'DEAD' = the wrong way in both; 'flips' = one each.
  placebo = how many of 2,000 random same-size sets of that sport's dogs did as well (a + weight) / as badly (a fade).
HONEST LIMIT, said once: nearly every weight was fit with these seasons seen (2018-26 studies) - 'earns' here is no
proof, it is the weight not having died; 'DEAD in both halves on today's code' is the finding.
Usage: python results/studies/dogs_1117/s3_parts.py > results/studies/dogs_1117/s3_parts.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dlib as D  # noqa: E402

DOGS = D.r3(dogs_only=True)
MIN_N = 40
out = []
for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab"):
    d = [r for r in DOGS if r["league"] == lg and r.get("parts")]
    base = D.stat([r for r in d if D.half(r["date"]) != "live"])
    bt = D.stat([r for r in d if D.half(r["date"]) == "train"])["roi"]
    bh = D.stat([r for r in d if D.half(r["date"]) == "held"])["roi"]
    print(f"\n===== {lg}: {len(d)} dogs with parts; every dog {base['roi']:+.1f}% (train {bt:+.1f}% / held {bh:+.1f}%)")
    cells = defaultdict(list)
    for r in d:
        for k, v in r["parts"].items():
            if k.startswith("_"):
                continue
            cells[(k, "+" if v > 0 else "-", v)].append(r)
    merged = defaultdict(list)
    for (k, s, v), rs in cells.items():
        merged[(k, s)].extend(rs)
    for (k, s), rs in sorted(merged.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        n = len([r for r in rs if D.half(r["date"]) != "live"])
        if n < MIN_N:
            continue
        vals = sorted({v for (k2, s2, v), _ in cells.items() if k2 == k and s2 == s})
        c = D.cell(f"{k} [{s}] pts {vals}", rs, w=44)
        t, h = c["train"]["roi"] - bt, c["held"]["roi"] - bh
        good = (t > 0 and h > 0) if s == "+" else (t < 0 and h < 0)
        bad = (t < 0 and h < 0) if s == "+" else (t > 0 and h > 0)
        pb = D.placebo(rs, d) if s == "+" else D.placebo_lo(rs, d)
        verdict = "earns" if good else "DEAD (wrong way both halves)" if bad else "flips"
        print(f"        vs the sport's dogs: train {t:+.1f} / held {h:+.1f} pts -> {verdict}; placebo {pb} of 2,000")
        out.append((lg, k, s, vals, c["all"]["n"], c["all"]["roi"], t, h, verdict, pb))
print("\n===== VERDICTS (n 40+): the weights that are the WRONG WAY in both halves")
for o in out:
    if o[8].startswith("DEAD"):
        print(f"  {o[0]:6s} {o[1]:28s} [{o[2]}] {str(o[3]):18s} n {o[4]:5d} {o[5]:+6.1f}% | vs the sport's dogs train {o[6]:+.1f} / held {o[7]:+.1f} | placebo {o[9]}")
print("\n===== the weights that earn their sign in both halves AND beat the placebo (under 100 of 2,000)")
for o in out:
    if o[8] == "earns" and o[9] is not None and o[9] < 100:
        print(f"  {o[0]:6s} {o[1]:28s} [{o[2]}] {str(o[3]):18s} n {o[4]:5d} {o[5]:+6.1f}% | train {o[6]:+.1f} / held {o[7]:+.1f} | placebo {o[9]}")
print("\n===== flips (one half each way)")
for o in out:
    if o[8] == "flips":
        print(f"  {o[0]:6s} {o[1]:28s} [{o[2]}] {str(o[3]):18s} n {o[4]:5d} {o[5]:+6.1f}% | train {o[6]:+.1f} / held {o[7]:+.1f} | placebo {o[9]}")
