"""H27-H29 - WHAT MAKES THE COLLEGE HOOPS LOCK WIN: the lift (the weighed read minus the own read = the study points
on the dog across), its dose on every favorite -150..-101, the dog across by its own dog score / dog read, and - on the
11/14 funnel5 rows (2023-25, which carry the reasons) - which facts sit on the dog across a Lock."""
import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M

R = M.rows()
ML = [r for r in R if r["market"] == "ml"]
mlk = {(r["gid"], r["side"]): r for r in ML}
other = lambda r: "away" if r["side"] == "home" else "home"
FAV = [r for r in ML if -150 <= r["odds"] <= -101 and r["mn"] >= 3]
rec = M.rec
for r in FAV:
    r["lift"] = None if (r["w_p"] is None or r["edge_own"] is None) else r["w_p"] - (r["edge_own"] + 1) / r["dec"]
    d = mlk.get((r["gid"], other(r))) or {}
    r["odr"], r["ods"] = d.get("dog_read"), d.get("dog_score")
print("THE DOSE - every favorite -150..-101 (both 3+ games) by the LIFT the studies on the dog across give it")
for a, b in ((-1, -0.02), (-0.02, -0.01), (-0.01, 0), (0, 0.0001), (0.0001, 0.01), (0.01, 0.02), (0.02, 0.03), (0.03, 0.0399), (0.0399, 1)):
    rec(f"lift {100 * a:+.1f}..{100 * b:+.1f} pts", [r for r in FAV if r["lift"] is not None and a <= r["lift"] < b], FAV)
print("\n... the same at 56%+ (the Lock's own bar) and under it")
for a, b in ((-1, 0), (0.0001, 0.02), (0.02, 0.03), (0.03, 1)):
    rec(f"p 56%+, lift {100 * a:+.1f}..{100 * b:+.1f}", [r for r in FAV if r["p"] >= 0.56 and r["lift"] is not None and a <= r["lift"] < b], FAV)
    rec(f"p under 56%, lift {100 * a:+.1f}..{100 * b:+.1f}", [r for r in FAV if r["p"] < 0.56 and r["lift"] is not None and a <= r["lift"] < b], FAV)
print("\n... by the price band, lift 2+ pts")
for a, b in ((-150, -140), (-139, -130), (-129, -120), (-119, -101)):
    rec(f"{a}..{b}, lift 2+", [r for r in FAV if a <= r["odds"] <= b and (r["lift"] or 0) >= 0.02], FAV)
    rec(f"{a}..{b}, weighed read over the price", [r for r in FAV if a <= r["odds"] <= b and r["w_p"] is not None and r["w_p"] * r["dec"] >= 1], FAV)
print("\nBIGGER FAVORITES (the -150 rule's other side, for the record): lift 2+ pts")
for a, b in ((-250, -201), (-200, -151)):
    rec(f"{a}..{b}, weighed 2+ over the no-vig", [r for r in ML if a <= r["odds"] <= b and r["mn"] >= 3 and r["w_p"] is not None and r["w_p"] - r["p_market"] >= 0.02], None)
print("\nTHE FACTS ON THE DOG ACROSS A LOCK (funnel5 rows 2023-25)")
C = Counter()
n = 0
rows = {}
for f in sorted(glob.glob(os.path.expanduser("~/.cache/d503_cbb1114/rows/s20*.jsonl"))):
    for line in open(f):
        r = json.loads(line)
        if r["market"] == "ml":
            rows[(r["gid"], r["side"])] = r
for k, r in rows.items():
    if r.get("kind") != "lock":
        continue
    d = rows.get((k[0], "away" if k[1] == "home" else "home")) or {}
    n += 1
    if n <= 6:
        print("  ", r["date"], r["team"], r["odds"], "p", r["p"], "w_p", r["w_p"], "own", round((r["edge_own"] + 1) / r["dec"], 4), r["result"], "| reasons", r.get("reasons"),
              "| dog", d.get("team"), "score", d.get("dog_score"), "read", d.get("dog_read"), "fade", d.get("dog_fade"), "parts", d.get("dog_read_parts"), "dogreasons", d.get("reasons"))
    for x in (d.get("dog_fade") or []) if isinstance(d.get("dog_fade"), list) else [d.get("dog_fade")]:
        C[str(x)] += 1
    for x in (d.get("dog_read_parts") or {}) if isinstance(d.get("dog_read_parts"), dict) else []:
        C["part:" + str(x)] += 1
print(n, C.most_common(40))
