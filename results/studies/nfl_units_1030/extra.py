"""Extra cells: the live NFL unit-play record, the dog across the early engine Lock (a fade?), the Lock by part of season."""
import json, pickle, math, statistics, os
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))   # the repo root
from collections import defaultdict
R = REPO
pk = json.load(open(os.path.join(R, "data/sports/picks.json")))
print("LIVE NFL unit plays:")
for p in pk:
    l = p["legs"][0]
    if l.get("league") == "nfl" and p["kind"] in ("lock", "dog", "play") and p.get("status") in ("won", "lost"):
        print(" ", p["date"], p["kind"], l.get("team"), l.get("odds"), p["units"], p["status"], round(p.get("pnl") or 0, 2))
rows = pickle.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rows.pkl"), "rb"))
dec = lambda o: 1 + (o / 100 if o > 0 else 100 / -o)


def g(xs, lbl):
    n = len(xs)
    if not n:
        print(lbl, "n0"); return
    rets = [(dec(o) - 1) if r["won"] else -1 for r, o in xs]
    roi = sum(rets) / n
    z = roi / (statistics.pstdev(rets) / math.sqrt(n)) if n > 1 and statistics.pstdev(rets) else 0
    by = defaultdict(list)
    for (r, o), x in zip(xs, rets):
        by[r["season"]].append(x)
    print(f"{lbl:60} n {n} won {sum(r['won'] for r, _ in xs) / n:.1%} ROI {roi:+.1%} z {z:+.1f} | " +
          " ".join(f"{s % 100}:{sum(v) / len(v):+.0%}/{len(v)}" for s, v in sorted(by.items())))


opp = {(r["gid"], r["team"]): r for r in rows}
fade = []
for r in rows:
    w = r["w"].get("E")
    if w and -150 <= w["price"] <= -101 and w["blend"] >= 0.56 and r["own_blind"] >= w["mkt"]:
        d = opp.get((r["gid"], r["opp"]))
        if d and d["w"].get("E"):
            fade.append((d, d["w"]["E"]["price"]))
g([x for x in fade if x[0]["season"] <= 2023], "FADE: dog across the early engine Lock @E [train]")
g([x for x in fade if x[0]["season"] >= 2024], "FADE: dog across the early engine Lock @E [hold]")
g([(d, d["close"]) for d, _ in fade if d["season"] <= 2023], "  ...same dogs at the close [train]")
g([(d, d["close"]) for d, _ in fade if d["season"] >= 2024], "  ...same dogs at the close [hold]")
L = [(r, r["close"]) for r in rows if -150 <= r["close"] <= -101 and r["blend"] >= 0.56 and r["mkt_close"] is not None
     and r["own"] >= r["mkt_close"]]
g([x for x in L if x[0]["month"] in (12, 1, 2)], "NFL Lock Dec+ pooled")
g([x for x in L if x[0]["month"] in (10, 11)], "NFL Lock Oct-Nov pooled")
g([x for x in L if x[0]["month"] in (9,)], "NFL Lock Sep pooled")
F = [(r, r["close"]) for r in rows if -150 <= r["close"] <= -101]
for m, lbl in (((9,), "Sep"), ((10, 11), "Oct-Nov"), ((12, 1, 2), "Dec+")):
    g([x for x in F if x[0]["month"] in m], "every -101..-150 favorite " + lbl)
for lo, hi in ((-150, -101), (-250, -151), (-400, -251)):
    g([(r, r["close"]) for r in rows if lo <= r["close"] <= hi and r["month"] in (12, 1, 2)], f"Dec+ favorites {lo}..{hi}")
    g([(r, r["close"]) for r in rows if lo <= r["close"] <= hi and r["month"] in (12, 1, 2) and r["mkt_close"] is not None
       and r["own"] >= r["mkt_close"]], "  ...own over")
    g([(r, r["close"]) for r in rows if lo <= r["close"] <= hi and r["month"] in (10, 11)], f"Oct-Nov favorites {lo}..{hi}")
    g([(r, r["close"]) for r in rows if lo <= r["close"] <= hi and r["month"] in (10, 11) and r["mkt_close"] is not None
       and r["own"] >= r["mkt_close"]], "  ...own over")
    g([(r, r["close"]) for r in rows if lo <= r["close"] <= hi and r["month"] in (10, 11) and r["mkt_close"] is not None
       and r["own"] >= r["mkt_close"] and r["blend"] >= 0.56], "  ...own over, blend 56%+")
