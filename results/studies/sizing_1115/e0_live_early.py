"""11/15 - the LIVE early plays: every row of data/sports/early.json by spot (the exam-scan plays = no spot), its units,
its own read vs the price, the result. The sanity check, never the judge."""
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
e = json.load(open(os.path.join(ROOT, "data/sports/early.json")))
ps = e["picks"]
ps = list(ps.values()) if isinstance(ps, dict) else ps


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


print(len(ps), "early rows;", len(e.get("pulled") or []), "pulled")
by = defaultdict(list)
for p in ps:
    by[p.get("spot") or "exam"].append(p)
for k, rs in sorted(by.items()):
    w = sum(p.get("result") == "won" for p in rs)
    l = sum(p.get("result") == "lost" for p in rs)
    net = sum((p.get("units") or 0) * (dec(p["odds"]) - 1) if p.get("result") == "won" else -(p.get("units") or 0)
              if p.get("result") == "lost" else 0 for p in rs)
    fl = sum((dec(p["odds"]) - 1) if p.get("result") == "won" else -1 if p.get("result") == "lost" else 0 for p in rs)
    risk = sum((p.get("units") or 0) for p in rs if p.get("result") in ("won", "lost"))
    print(f"{k:14s} n {len(rs):3d} {w}-{l} units {net:+.2f} on {risk:.1f} flat1u {fl:+.2f} open {sum(p.get('result') is None for p in rs)}")
print()
for p in sorted(by["exam"], key=lambda p: p.get("posted") or ""):
    d = dec(p["odds"])
    own = p.get("own")
    print((p.get("posted") or "")[:16], (p.get("start") or "")[:10], p["league"], f"{p['team'][:22]:22s}", f"{p['odds']:+d}",
          "own", own, "mkt", p.get("mkt"), "need", round(1 / d, 3), "u", p.get("units"), p.get("result"),
          "| keys:" if p is by["exam"][0] else "", sorted(p) if p is by["exam"][0] else "")
x = json.load(open(os.path.join(ROOT, "data/sports/early_exam.json")))
print()
for lg, v in x["leagues"].items():
    print(lg, "passed:", v.get("passed"))
    for k, b in v["bands"].items():
        print("   ", k, b["dogs"], b["won"], round(b["money"], 3), b.get("season1"), b.get("season2"))
