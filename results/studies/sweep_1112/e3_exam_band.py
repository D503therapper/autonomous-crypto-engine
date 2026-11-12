"""11/12 SWEEP (a) - THE COLLEGE EXAM BAND (the scan that posted Georgia St +170 at 1.5u on 11/11): the walk-forward
own read (tuned on the 3 seasons before - the early study's cached base table) 4-8 points over the no-vig FIRST FAIR
price on a dog +100..+280, 2020-26, by season; other gap bands beside it; and the live record of every early play the
exam scan posted (no spot). Usage: python results/studies/sweep_1112/e3_exam_band.py > .../e3_exam_band.out"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "early_1111"))
import base            # noqa: E402
import elib as E       # noqa: E402

se = E.se
for lg in ("ncaaf", "nfl"):
    rows = base.build(lg)
    print(f"\n{lg}: dogs +100..+280 at the first fair number, by the own read's gap over the no-vig price")
    for lo, hi in ((-1, 0), (0, .04), (.04, .08), (.08, .12), (.12, 1)):
        v = []
        for r in rows:
            f = base.first_fair(r)
            if not f or not 100 <= f[2] <= 280 or r["own"] is None or not lo <= r["own"] - f[3] < hi:
                continue
            v.append((r, f))
        pl = lambda r, o: (E.dec(o) - 1) if r["won"] else -1.0    # noqa: E731
        tr = [x for x in v if x[0]["season"] <= 2022]
        he = [x for x in v if x[0]["season"] >= 2023]
        bys = {}
        for r, f in v:
            bys.setdefault(r["season"], []).append(pl(r, f[2]))
        print(f"  gap {lo * 100:+4.0f}..{hi * 100:+4.0f}: all {E.roi([pl(r, f[2]) for r, f in v])} | 2020-22 {E.roi([pl(r, f[2]) for r, f in tr])} | 2023-26 {E.roi([pl(r, f[2]) for r, f in he])}"
              f" | at the close {E.mean([pl(r, r['close_o']) for r, f in v]) * 100:+.1f}%")
        print("      " + "  ".join(f"{s} {sum(1 for x in p if x > 0)}-{sum(1 for x in p if x < 0)} {E.mean(p) * 100:+.0f}%" for s, p in sorted(bys.items())))
st = json.load(open(se.PATH))
print("\nLIVE - every early play the exam scan posted (no spot, a side)")
w = l = 0
net = 0.0
for p in st["picks"]:
    if p.get("spot") or p.get("market") == "total":
        continue
    u = se.units(p)
    res = p.get("result")
    if res == "won":
        w += 1
        net += u * (E.dec(p["odds"]) - 1)
    elif res == "lost":
        l += 1
        net -= u
    print(f"  {p['start'][:10]} {p['league']:5s} {p['team']:16s} {p['odds']:+5d} {u}u own {p.get('own')} mkt {p.get('mkt')} -> {res}")
print(f"  graded {w}-{l} {net:+.2f}u")
for p in st.get("pulled") or []:
    if not p.get("spot"):
        print(f"  PULLED {p['start'][:10]} {p['league']} {p['team']} {p['odds']:+d}")
