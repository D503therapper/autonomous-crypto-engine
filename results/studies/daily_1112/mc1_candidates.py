"""11/12 DAILY - MC1: FOOTBALL'S MONEY CHECK AT THE CANDIDATE LEVEL (the deep program's open item (c)).
Every football moneyline side on the replay board days 2023-10 -> 2026-11-10 at its CLOSING price (the deep program's
funnel rows: NEW = the honest dials, OLD = the tune as it was, held-out days only). Which check picks winners?
  dogs +100..+350 (never a trap): the OLD own read over the price / the dog score (gate) / the weighed dog read
  (dog_p = the no-vig close + the score) over the real price / combos
  favorites -150..-101: the OLD own read over the price / the weighed read (w_p) over the price / the blended win %
train = to 2025-06-30, held = after; flat 1u at the close.
Usage: python results/studies/daily_1112/mc1_candidates.py > results/studies/daily_1112/mc1_candidates.out"""
import os
import mclib as M
D = M.D

NEW = M.load(os.path.join(M.DEEP, "funnel_new"))
OLD = {M.key(r): r for r in M.load(os.path.join(M.DEEP, "funnel_old"), "CD")}
print(f"NEW football ml sides {len(NEW)}; OLD (held days) {len(OLD)}")
GATE = {"nfl": 8.0, "ncaaf": 4.0}


def wd(r):
    return (r["p_market"] + r["dog_score"] / 100) * r["dec"] > 1


for lg in M.FB + ("both",):
    rs = [r for r in NEW if lg == "both" or r["league"] == lg]
    dogs = [r for r in rs if 100 <= r["odds"] <= 350 and not r["trap"] and r.get("dog_score") is not None]
    print(f"\n== {lg.upper()} DOGS +100..+350 (not a trap): {len(dogs)}")
    D.cell("every dog", dogs)
    for lo, hi in ((-99, -2), (-2, 0), (0, 2), (2, 4), (4, 6), (6, 99)):
        D.cell(f"dog score {lo}..{hi}", [r for r in dogs if lo <= r["dog_score"] < hi])
    D.cell("weighed dog read over the real price (dog_p x dec > 1)", [r for r in dogs if wd(r)])
    D.cell("  ...and score 2+", [r for r in dogs if wd(r) and r["dog_score"] >= 2])
    D.cell("  ...and score 4+", [r for r in dogs if wd(r) and r["dog_score"] >= 4])
    D.cell("score at the league's gate (NFL 8 / college 4)", [r for r in dogs if r["dog_score"] >= GATE[r["league"]]])
    D.cell("score 3+", [r for r in dogs if r["dog_score"] >= 3])
    od = [r for r in dogs if M.key(r) in OLD]
    print(f"  -- the held-out days, OLD vs NEW reads on the same dogs ({len(od)})")
    D.cell("OLD own read over the real price", [r for r in od if (OLD[M.key(r)].get("edge_own") or -1) > 0])
    D.cell("OLD dog gate (score + own read, old reads)", [r for r in od if OLD[M.key(r)].get("dog_gate") is True])
    D.cell("OLD dog score at the gate (old reads)", [r for r in od if (OLD[M.key(r)].get("dog_score") or -99) >= GATE[r["league"]]])
    D.cell("NEW weighed dog read over the price + score 4+", [r for r in od if wd(r) and r["dog_score"] >= 4])
    D.cell("NEW score at the gate", [r for r in od if r["dog_score"] >= GATE[r["league"]]])
    favs = [r for r in rs if -150 <= r["odds"] <= -101 and not r["trap"]]
    print(f"\n== {lg.upper()} FAVORITES -150..-101 (not a trap): {len(favs)}")
    D.cell("every favorite", favs)
    wf = [r for r in favs if r.get("w_p") is not None]
    D.cell("has a weighed read", wf)
    D.cell("weighed read over the real price", [r for r in wf if r["w_p"] * r["dec"] > 1])
    D.cell("weighed read over the no-vig close", [r for r in wf if r["w_p"] > r["p_market"] + 1e-6])
    D.cell("weighed read = the close", [r for r in wf if abs(r["w_p"] - r["p_market"]) <= 1e-6])
    D.cell("weighed read under the no-vig close", [r for r in wf if r["w_p"] < r["p_market"] - 1e-6])
    D.cell("weighed read 1+ pts under the close", [r for r in wf if r["w_p"] < r["p_market"] - 0.01])
    D.cell("blended 56%+ (the Lock's bar)", [r for r in favs if r["p"] >= 0.56])
    D.cell("blended 56%+ and weighed over the price", [r for r in wf if r["p"] >= 0.56 and r["w_p"] * r["dec"] > 1])
    D.cell("good() under the honest dials", [r for r in favs if r["good"] is True])
    of = [r for r in favs if M.key(r) in OLD]
    print(f"  -- the held-out days, OLD vs NEW reads on the same favorites ({len(of)})")
    D.cell("OLD own read over the real price", [r for r in of if (OLD[M.key(r)].get("edge_own") or -1) > 0])
    D.cell("OLD own_beats + good", [r for r in of if OLD[M.key(r)].get("own_beats") is True and OLD[M.key(r)].get("good") is True])
    D.cell("NEW weighed read over the price", [r for r in of if r.get("w_p") is not None and r["w_p"] * r["dec"] > 1])
print("\ncells:", D.CELLS[0])
