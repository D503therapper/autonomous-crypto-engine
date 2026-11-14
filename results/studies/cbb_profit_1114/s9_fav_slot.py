"""11/14 STUDY 9 - THE FAVORITE SLOT IS ALMOST NEVER ON (3 plays in eight replay seasons on today's code): since the
11/12 honest dials the own read of a college hoops favorite sits at the price, so the slot's "own read over the price"
bar shuts it. Would a slot re-based on the WEIGHED read alone (the football 11/12 answer) pay? Every -150..-101 favorite,
both teams 4+ games (the slot needs 3), not a trap / fighting, no Lock on the game, by the weighed read's points over
what the price needs, the band, home / road / neutral."""
import os, pickle, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
import tlib

F = pickle.load(open(os.path.expanduser("~/.cache/d503_early1113/rows.pkl"), "rb"))
G = {r["id"]: r for r in tlib.build()}
lockg = {r["gid"] for r in F if r["kind"] in ("lock", "play")}
R, POOL = [], []
for r in F:
    if r["market"] != "ml" or not -150 <= r["odds"] <= -101 or r["mn"] < 4:
        continue
    x = {k: r.get(k) for k in ("date", "gid", "side", "odds", "dec", "p_market", "edge_own", "w_p", "trap", "fighting", "kind",
                               "result", "season", "win", "pnl", "home")}
    x["pnl"] = 0.0 if r["result"] == "push" else x["pnl"]
    g = G.get(r["gid"]) or {}
    x["where"] = "neutral" if g.get("neu") else ("home" if r.get("home") else "road")
    x["pts"] = None if r.get("w_p") is None else r["w_p"] - 1 / r["dec"]
    POOL.append(x)
    if not r["trap"] and not r["fighting"] and r["gid"] not in lockg and x["pts"] is not None:
        R.append(x)
del F
L.rec("every -150..-101 favorite, 4+ games", POOL)
L.rec("not a trap / fighting / a Lock game, with a weighed read", R, POOL)
for lo, hi in ((-1, -0.02), (-0.02, 0), (0, 0.01), (0.01, 0.03), (0.03, 0.05), (0.05, 1)):
    L.rec(f"weighed read {100 * lo:+.0f}..{100 * hi:+.0f} over the price", [r for r in R if lo <= r["pts"] < hi], POOL)
S = [r for r in R if 0.01 <= r["pts"] <= 0.05]
L.rec("THE RE-BASED SLOT: weighed 1-5 over (any band)", S, POOL)
L.rec("   -150..-120 (the slot's band)", [r for r in S if r["odds"] <= -120], POOL)
L.rec("   -150..-120, weighed 56%+", [r for r in S if r["odds"] <= -120 and r["w_p"] >= 0.56], POOL)
L.rec("   -119..-101", [r for r in S if r["odds"] > -120], POOL)
for w in ("home", "road", "neutral"):
    L.rec(f"   {w}", [r for r in S if r["where"] == w], POOL)
# one a night, the best weighed edge (the slot's cap)
best = {}
for r in S:
    if r["odds"] <= -120 and r["w_p"] >= 0.56:
        k = r["date"]
        if k not in best or r["pts"] * r["dec"] > best[k]["pts"] * best[k]["dec"]:
            best[k] = r
L.rec("   ONE A NIGHT, -150..-120, weighed 56%+ 1-5 over", list(best.values()), POOL)
print(f"cells read: {L.CELLS[0]}")
