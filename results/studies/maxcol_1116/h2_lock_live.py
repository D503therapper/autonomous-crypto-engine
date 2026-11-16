"""H26 - WOULD THE REPLAY'S COLLEGE HOOPS LOCKS POST LIVE? post_board's no-thin-Lock rule (the own read under 3c over
the price = no Lock) is not in the replay's make_board. The Locks by the own read's edge (edge_own = own read x the
price - 1) and by the weighed read's edge; then the open -> close move on the 2023+ rows."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M

R = M.rows()
ML = [r for r in R if r["market"] == "ml"]
FAV = [r for r in ML if -150 <= r["odds"] <= -101 and r["mn"] >= 3]
LOCK = [r for r in ML if r["kind"] == "lock"]
rec = M.rec
print("THE REPLAY'S COLLEGE HOOPS LOCKS BY THE OWN READ'S EDGE (live: under +3c = thin = no Lock at all)")
for a, b in ((-1, -0.03), (-0.03, 0), (0, 0.01), (0.01, 0.03), (0.03, 0.08), (0.08, 9)):
    rec(f"own edge {a:+.2f}..{b:+.2f}", [r for r in LOCK if r["edge_own"] is not None and a <= r["edge_own"] < b], FAV, min_n=1)
thin = lambda r: min(r["edge_own"], (r["w_p"] if r["w_p"] is not None else r["p"]) * r["dec"] - 1) < 0.03
rec("THIN by the live rule (min of own / weighed edge under 3c)", [r for r in LOCK if thin(r)], FAV, kelly=True)
rec("NOT thin - the Locks that would be titled the Lock live", [r for r in LOCK if not thin(r)], FAV, kelly=True)
rec("   weighed edge 3c+ (any own edge)", [r for r in LOCK if r["w_p"] is not None and r["w_p"] * r["dec"] - 1 >= 0.03], FAV)
rec("   weighed edge under 3c", [r for r in LOCK if r["w_p"] is not None and r["w_p"] * r["dec"] - 1 < 0.03], FAV)
print("\nEVERY FAVORITE -150..-101 (both 3+ games) BY THE SAME CUTS (is the Lock more than 'weighed over')")
F = [r for r in FAV if r["w_p"] is not None and r["edge_own"] is not None]
for nm, f in (("own edge under 0, weighed read over the price", lambda r: r["edge_own"] < 0 and r["w_p"] * r["dec"] >= 1),
              ("own edge 0..3c, weighed over", lambda r: 0 <= r["edge_own"] < 0.03 and r["w_p"] * r["dec"] >= 1),
              ("own edge 3c+, weighed over", lambda r: r["edge_own"] >= 0.03 and r["w_p"] * r["dec"] >= 1),
              ("weighed read UNDER the price", lambda r: r["w_p"] * r["dec"] < 1),
              ("p 56%+ and weighed over", lambda r: r["p"] >= 0.56 and r["w_p"] * r["dec"] >= 1),
              ("p under 56% and weighed over", lambda r: r["p"] < 0.56 and r["w_p"] * r["dec"] >= 1)):
    rec(nm, [r for r in F if f(r)], FAV)
rec("no weighed read at all (no study point on the dog)", [r for r in FAV if r["w_p"] is None], FAV)
print("\nOPEN -> CLOSE on the Locks (2023+ rows carry the open)")
import glob, json
op = {}
for f in sorted(glob.glob(os.path.expanduser("~/.cache/d503_leans1113/rows/s20*.jsonl"))):
    for line in open(f):
        if '"lock"' not in line:
            continue
        r = json.loads(line)
        if r.get("kind") == "lock" and r["market"] == "ml":
            op[(r["gid"], r["side"])] = r.get("ml_home_open") if r["side"] == "home" else r.get("ml_away_open")
n = w = 0
tot = 0.0
mv = []
for r in LOCK:
    o = op.get((r["gid"], r["side"]))
    try:
        o = float(o)
    except (TypeError, ValueError):
        continue
    if not (-400 < o < 400) or abs(o) < 100:
        continue
    n += 1
    d = L_dec = 1 + (o / 100 if o > 0 else 100 / -o)
    mv.append((1 / d) - (1 / r["dec"]))
    if r["win"]:
        tot += d - 1
        w += 1
    elif r["pnl"] < 0:
        tot -= 1
if n:
    print(f"   Locks with an open: {n}, at the OPEN {w}-{n - w} ROI {100 * tot / n:+.1f}% ; the price moved (implied, open minus close) "
          f"{100 * sum(mv) / n:+.2f} pts on average ; toward the Lock in {sum(m < 0 for m in mv)} of {n}")
