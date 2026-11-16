"""H49-H50 - THE 💎 MAX PLAY AS WIRED (sports.max_play_ok): a college hoops moneyline favorite -150..-101 the engine
gives 56%+ (the Lock's bar), both teams 3+ games, not a trap / fighting, its WEIGHED read (the own read moved by the
studies on the dog across and on itself) over the no-vig market and over the real price - the best one a night (the
bigger weighed edge). 3u; 1.5u while either team has played under 10 games (the early-Lock rule). NO lift cut: "the
studies lift it 2+ points" read 17-4 on one replay and 11-6 on the other (h8) - a knife-edge, not a dose.
H49 on the 11/13 funnel4 rows (2018-26) - the list, the units, the worst stretch.
H50 the second replay: the 11/14 funnel5 rows (today's code with the home-dog weight, 2023-26)."""
import glob
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M

rec = M.rec


def ok(r):
    if r["market"] != "ml" or not -150 <= r["odds"] <= -101 or r.get("w_p") is None or r.get("edge_own") is None:
        return False
    own = (r["edge_own"] + 1) / r["dec"]
    return (r["p"] >= 0.56 and min(r.get("games_in") or 0, r.get("opp_games_in") or 0) >= 3 and not r.get("trap") and not r.get("fighting")
            and r["w_p"] >= r["p_market"] and r["w_p"] * r["dec"] > 1)


def nightly(pool):
    b = defaultdict(list)
    for r in pool:
        b[r["date"]].append(r)
    return sorted((max(v, key=lambda r: (r["w_p"] * r["dec"], r["w_p"] - (r["edge_own"] + 1) / r["dec"])) for v in b.values()), key=lambda r: r["date"])


def units(r):
    return 1.5 if min(r.get("games_in") or 0, r.get("opp_games_in") or 0) < 10 else 3.0


def report(S, FAV, tag):
    rec(f"{tag}: the max play, the best one a night", S, FAV, kelly=True)
    rec("   both teams 10+ games (3u)", [r for r in S if units(r) == 3.0], FAV)
    rec("   a team in games 3-9 (1.5u)", [r for r in S if units(r) == 1.5], FAV, min_n=1)
    eq = pk = dd = risk = 0.0
    bys = defaultdict(float)
    for r in S:
        u = units(r)
        eq += u * r["pnl"]
        risk += u
        bys[r["season"]] += u * r["pnl"]
        pk = max(pk, eq)
        dd = min(dd, eq - pk)
    print(f"   at its units: {eq:+.1f}u on {risk:.1f}u risked ({100 * eq / max(risk, 1):+.1f}%), the worst losing stretch {dd:.1f}u; by season "
          + " ".join(f"{s % 100}:{v:+.1f}u" for s, v in sorted(bys.items())) + f"; {len(S) / max(1, len(bys)):.1f} plays a season")
    he = [r for r in S if r["season"] >= 2023]
    w, l_ = sum(r["win"] for r in he), sum(r["pnl"] < 0 for r in he)
    if w + l_:
        p = w / (w + l_)
        lo = p - 1.645 * math.sqrt(p * (1 - p) / (w + l_))
        d = sum(r["dec"] for r in he) / len(he)
        print(f"   THE SIZE (the 11/12 altitude study's way): held out {w}-{l_} = {100 * p:.1f}% at {d:.3f}; the 5% low end {100 * lo:.1f}% -> "
              f"quarter-Kelly {M.qkelly(lo, d):.1f}u (Wilson's low end {100 * M.wilson_lo(w, w + l_, 1.645):.1f}% -> {M.qkelly(M.wilson_lo(w, w + l_, 1.645), d):.1f}u)")


R = M.rows()
ML = [r for r in R if r["market"] == "ml"]
FAV = [r for r in ML if -150 <= r["odds"] <= -101 and r["mn"] >= 3]
S = nightly([r for r in ML if ok(r)])
print("H49 THE 11/13 ROWS (2018-26)")
report(S, FAV, "H49")
for r in S:
    print(f"      {r['date']} {r['team'][:22]:22s} {r['odds']:5d} vs {r['opp'][:22]:22s} {r['where']:7s} read {100 * r['p']:.1f} weighed {100 * r['w_p']:.1f} "
          f"own {100 * (r['edge_own'] + 1) / r['dec']:.1f} needs {100 / r['dec']:.1f} games {r['mn']:2d} {'LOCK' if r['kind'] == 'lock' else '    '} {r['result']} {r['hs']}-{r['as']}")

print("\nH50 THE SECOND REPLAY - THE 11/14 FUNNEL5 ROWS (2023-26, today's code)")
N = []
for f in sorted(glob.glob(os.path.expanduser("~/.cache/d503_cbb1114/rows/s20*.jsonl"))):
    for line in open(f):
        r = json.loads(line)
        if r["market"] != "ml" or r.get("result") not in ("won", "lost", "push"):
            continue
        y, m = int(r["date"][:4]), int(r["date"][5:7])
        r["season"] = y if m >= 7 else y - 1
        r["win"] = r["result"] == "won"
        r["pnl"] = 0.0 if r["result"] == "push" else ((r["dec"] - 1) if r["win"] else -1.0)
        r["mn"] = min(r.get("games_in") or 0, r.get("opp_games_in") or 0)
        N.append(r)
FAV2 = [r for r in N if -150 <= r["odds"] <= -101 and r["mn"] >= 3]
S2 = nightly([r for r in N if ok(r)])
report(S2, FAV2, "H50")
a = {(r["gid"], r["side"]) for r in S if r["season"] >= 2023}
b = {(r["gid"], r["side"]) for r in S2}
print(f"   the same play on both replays: {len(a & b)} of {len(a)} (11/13 rows) / {len(b)} (11/14 rows)")
run = worst = 0
for r in S:
    run = run + 1 if r["pnl"] < 0 else 0
    worst = max(worst, run)
nights = len({r["date"] for r in ML if ok(r)})
print(f"   the longest run of losses on the 11/13 rows: {worst}; qualifying favorites {sum(1 for r in ML if ok(r))} on {nights} nights")
for c in (5, 10, 15, 20):
    print(f"   the 11/13 rows at a price {c} cents worse: ROI {100 * sum(M.worse(r, c) for r in S) / len(S):+.1f}%")
for mo in ("11", "12", "01", "02", "03"):
    rec(f"   month {mo}", [r for r in S if r["month"] == mo], FAV, min_n=1)
rec("   league game", [r for r in S if r["conf"]], FAV)
rec("   non-league", [r for r in S if not r["conf"]], FAV, min_n=1)
for w in ("home", "road", "neutral"):
    rec(f"   {w}", [r for r in S if r["where"] == w], FAV, min_n=1)
print("   2026-27 so far (through the rows' last day): " + (", ".join(f"{r['date']} {r['team']} {r['odds']} {r['result']}" for r in S2 if r["season"] == 2026) or "none yet (it needs league-play fades - the first ones come in December)"))
