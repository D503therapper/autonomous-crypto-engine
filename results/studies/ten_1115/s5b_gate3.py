"""S5b - WHAT A DOG SLOT GATE OF 3 WOULD POST (the lead's own test): the slot rebuilt (cbb_profit_1114/recon.py's
rules - not a trap / fighting, both 4+ games, the read clearing the price, no Lock game, the best two a night by the
read then the efficiency gap) at a gate of 4 (today) and of 3; the ADDED plays are the bet. Then the second replay:
the 11/14 funnel5 rows (today's code with the home-dog weight and the slot's real nightly rank; the held-out seasons
2023-26 only) - every dog read 3-4 there."""
import glob
import json
import os
import pickle
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clib as C  # noqa: E402

L = C.L
R = L.load(L.OLD, markets=("ml",), keep_all=True)
K = pickle.load(open(os.path.expanduser("~/.cache/d503_studies/cbb_knowledge_b_rows.pkl"), "rb"))
eff = {(x["id"], x["side"]): x.get("eff") for x in K}
del K
DOG = [r for r in R if 100 <= r["odds"] <= 350]


def slot(gate):
    lockg = {r["gid"] for r in R if r["kind"] in ("lock", "play", "dogplay")}
    pool = defaultdict(list)
    for r in R:
        if not 100 <= r["odds"] <= 350 or r["mn"] < 4 or r["trap"] or r["fighting"]:
            continue
        if (r.get("dog_read") or -99) < gate or r["gid"] in lockg or r["kind"] in ("stackplay", "floor"):
            continue
        if min(0.95, r["p_market"] + r["dog_read"] / 100) * r["dec"] - 1 <= 0:
            continue
        e = r.get("eff_p") if r.get("eff_p") is not None else eff.get((r["gid"], r["side"]))
        r["effgap"] = None if e is None else e - r["p_market"]
        pool[r["date"]].append(r)
    out = []
    for d, v in pool.items():
        seen = set()
        for r in sorted(v, key=lambda r: (-r["dog_read"], -(r["effgap"] or 0))):
            if r["gid"] in seen:
                continue
            seen.add(r["gid"])
            if len(seen) <= 2:
                out.append(r)
    return out


s4, s3 = slot(4), slot(3)
k4 = {(r["gid"], r["side"]) for r in s4}
add = [r for r in s3 if (r["gid"], r["side"]) not in k4]
print("THE SLOT AT A GATE OF 4 (today) / 3, the best two a night (flat 1u at the close)")
L.rec("gate 4 - the slot as it is", s4, DOG)
L.rec("gate 3 - the slot it would be", s3, DOG)
L.rec("THE ADDED PLAYS (read 3-4 on a night with room)", add, DOG)
for w in ("home", "road", "neutral"):
    L.rec(f"   added, {w}", [r for r in add if r["where"] == w], DOG, min_n=5)
L.rec("   added, +100..+150", [r for r in add if r["odds"] <= 150], DOG)
L.rec("   added, +151..+350", [r for r in add if r["odds"] > 150], DOG, min_n=5)
L.rec("   added, league game", [r for r in add if r["conf"]], DOG)
L.rec("   added, non-league", [r for r in add if r["conf"] is False], DOG)
L.rec("   added, read 3-3.5", [r for r in add if r["dog_read"] < 3.5], DOG)
L.rec("   added, read 3.5-4", [r for r in add if r["dog_read"] >= 3.5], DOG)
for mm, nm in ((("11", "12"), "Nov-Dec"), (("01",), "Jan"), (("02", "03"), "Feb-Mar")):
    L.rec(f"   added, {nm}", [r for r in add if r["month"] in mm], DOG, min_n=5)
print("  price-free: the added won %.1f%% vs the no-vig %.1f%% (%d); train %.1f vs %.1f, held %.1f vs %.1f" % (
    100 * sum(r["win"] for r in add) / len(add), 100 * sum(r["p_market"] for r in add) / len(add), len(add),
    100 * sum(r["win"] for r in add if r["season"] <= 2022) / max(1, sum(1 for r in add if r["season"] <= 2022)),
    100 * sum(r["p_market"] for r in add if r["season"] <= 2022) / max(1, sum(1 for r in add if r["season"] <= 2022)),
    100 * sum(r["win"] for r in add if r["season"] >= 2023) / max(1, sum(1 for r in add if r["season"] >= 2023)),
    100 * sum(r["p_market"] for r in add if r["season"] >= 2023) / max(1, sum(1 for r in add if r["season"] >= 2023))))
print("\nEVERY DOG BY ITS READ (both teams 4+ games, nothing else asked) - the dose")
for lo, hi in ((-99, -4), (-4, -2), (-2, 0), (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 99)):
    L.rec(f"dog read {lo}..{hi}", [r for r in DOG if r.get("dog_read") is not None and lo <= r["dog_read"] < hi and r["mn"] >= 4], DOG)
x = [r for r in DOG if r.get("dog_read") is not None and 3 <= r["dog_read"] < 4 and r["mn"] >= 4]
L.rec("read 3-4: a trap or a side the own read fights", [r for r in x if r["trap"] or r["fighting"]], DOG)
L.rec("read 3-4: neither", [r for r in x if not r["trap"] and not r["fighting"]], DOG)
L.rec("read 3-4: home", [r for r in x if r["where"] == "home"], DOG)
L.rec("read 3-4: road", [r for r in x if r["where"] == "road"], DOG)
L.rec("read 3-4: neutral", [r for r in x if r["where"] == "neutral"], DOG)

print("\nTHE SECOND REPLAY - the 11/14 funnel5 rows (today's code, the held-out seasons 2023-26 only)")
N = []
for f in sorted(glob.glob(os.path.join(L.NEW, "s20*.jsonl"))):
    for line in open(f):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("market") != "ml" or r.get("result") not in ("won", "lost") or not 100 <= r["odds"] <= 350:
            continue
        if r.get("dog_read") is None or min(r.get("games_in") or 0, r.get("opp_games_in") or 0) < 4:
            continue
        y, m = int(r["date"][:4]), int(r["date"][5:7])
        N.append({"season": y if m >= 7 else y - 1, "win": r["result"] == "won", "pnl": (r["dec"] - 1) if r["result"] == "won" else -1.0,
                  "dog_read": r["dog_read"], "trap": r.get("trap"), "fighting": r.get("fighting"), "p_market": r["p_market"], "dec": r["dec"],
                  "home": r.get("home"), "neutral": str(r.get("neutral")) == "1"})
print(f"  {len(N)} dogs with a read, seasons {sorted({r['season'] for r in N})}")
for lo, hi in ((0, 2), (2, 3), (3, 4), (4, 5), (5, 99)):
    L.rec(f"funnel5 dog read {lo}..{hi}", [r for r in N if lo <= r["dog_read"] < hi], min_n=5)
y = [r for r in N if 3 <= r["dog_read"] < 4]
L.rec("funnel5 read 3-4, slot-shaped (not a trap / fighting, clears the price)",
      [r for r in y if not r["trap"] and not r["fighting"] and min(0.95, r["p_market"] + r["dog_read"] / 100) * r["dec"] > 1], min_n=5)
print(f"\ncells read: {L.CELLS[0]}")
