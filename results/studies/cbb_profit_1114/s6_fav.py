"""11/14 STUDY 6 - THE MONEYLINE FAVORITE -150..-101 BY THE EFFICIENCY READ (priority 4). Every college hoops
regular-season favorite -150..-101 with both teams 4+ games in, on the 11/13 funnel rows (today's code, the close)
joined to the walk-forward EFFICIENCY read (eff_p, sports_cbb_eff with last season carried in - the 11/3 KNOWLEDGE (B)
table, 2018-25) - by the efficiency read's edge over the no-vig market, and against the owner's value bar (the own read
1+ point over what the price needs, sports.VALUE_EDGE_MIN) and the weighed read (w_p). The question: is there a
favorite cell that wins in both halves AND that the engine's own read can say yes to (a ½u value play)?"""
import os, pickle, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
import tlib

F = pickle.load(open(os.path.expanduser("~/.cache/d503_early1113/rows.pkl"), "rb"))
G = {r["id"]: r for r in tlib.build()}
R = []
for r in F:
    if r["market"] != "ml" or not -150 <= r["odds"] <= -101 or r["mn"] < 4 or r.get("eff_p") is None:
        continue
    g = G.get(r["gid"]) or {}
    x = {k: r.get(k) for k in ("date", "gid", "side", "odds", "dec", "p", "p_market", "edge_own", "w_p", "eff_p", "trap",
                               "fighting", "kind", "lean_any_new", "home", "result", "season", "win", "pnl", "mn")}
    x["month"] = r["date"][5:7]
    x["neu"] = bool(g.get("neu"))
    x["where"] = "neutral" if x["neu"] else ("home" if r.get("home") else "road")
    x["conf"] = g.get("conf")
    x["need"] = 1 / r["dec"]
    x["own"] = (r["edge_own"] + 1) / r["dec"] if r.get("edge_own") is not None else None
    x["effgap"] = r["eff_p"] - r["p_market"]
    x["pnl"] = 0.0 if r["result"] == "push" else x["pnl"]
    R.append(x)
del F
print(f"favorites -150..-101, both 4+ games, with an efficiency read: {len(R)}")
L.rec("every favorite", R, R)
for lo, hi in ((-150, -130), (-129, -101)):
    L.rec(f"every favorite {lo}..{hi}", [r for r in R if lo <= r["odds"] <= hi], R)

print("\nA. BY THE EFFICIENCY READ OVER THE NO-VIG MARKET")
for lo, hi in ((-1, -0.05), (-0.05, -0.03), (-0.03, 0), (0, 0.03), (0.03, 0.05), (0.05, 0.08), (0.08, 0.12), (0.12, 1)):
    L.rec(f"eff gap {100 * lo:+.0f}..{100 * hi:+.0f}", [r for r in R if lo <= r["effgap"] < hi], R)
for cut in (0.03, 0.05, 0.08):
    rows = [r for r in R if r["effgap"] >= cut]
    L.rec(f"eff gap +{100 * cut:.0f}+", rows, R)
    for nm, f in (("home", lambda r: r["where"] == "home"), ("road", lambda r: r["where"] == "road"), ("neutral", lambda r: r["where"] == "neutral"),
                  ("conference", lambda r: r["conf"]), ("non-conference", lambda r: r["conf"] is False),
                  ("Nov-Dec", lambda r: r["month"] in ("11", "12")), ("Jan-Mar", lambda r: r["month"] in ("01", "02", "03")),
                  ("-150..-130", lambda r: r["odds"] <= -130), ("-129..-101", lambda r: r["odds"] > -130)):
        L.rec(f"   eff gap +{100 * cut:.0f}+ | {nm}", [r for r in rows if f(r)], R)

print("\nB. WITH THE ENGINE'S OWN READ (the owner's value bar: the own read 1+ point over what the price needs)")
own_ok = [r for r in R if r["own"] is not None and r["own"] - r["need"] >= 0.01]
L.rec("own read 1+ over the price (any eff)", own_ok, R)
L.rec("own read over the price at all", [r for r in R if r["own"] is not None and r["own"] > r["need"]], R)
for cut in (0.0, 0.03, 0.05):
    L.rec(f"own 1+ over AND eff gap +{100 * cut:.0f}+", [r for r in own_ok if r["effgap"] >= cut], R)
wp_ok = [r for r in R if r.get("w_p") is not None and r["w_p"] - r["need"] >= 0.01]
L.rec("weighed read 1+ over the price", wp_ok, R)
for cut in (0.03, 0.05, 0.08):
    L.rec(f"weighed 1+ over AND eff gap +{100 * cut:.0f}+", [r for r in wp_ok if r["effgap"] >= cut], R)
print("   how far the own read sits from the price (eff gap +5+):")
d = defaultdict(int)
for r in R:
    if r["effgap"] >= 0.05 and r["own"] is not None:
        d[round(100 * (r["own"] - r["need"]))] += 1
print("   ", sorted(d.items()))

print("\nC. WHAT THE BOARD ALREADY TAKES (kind) among eff gap +5+")
k = defaultdict(list)
for r in R:
    if r["effgap"] >= 0.05:
        k[r["kind"]].append(r)
for kk, v in sorted(k.items(), key=lambda t: str(t[0])):
    L.rec(f"kind {kk}", v, R)
L.rec("eff gap +5+, not already a unit play", [r for r in R if r["effgap"] >= 0.05 and not r["kind"]], R)
L.rec("eff gap +5+, not a unit play, not trap / fighting", [r for r in R if r["effgap"] >= 0.05 and not r["kind"] and not r["trap"] and not r["fighting"]], R)
print(f"\ncells read: {L.CELLS[0]}")
