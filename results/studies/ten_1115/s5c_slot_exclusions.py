"""S5c - WHAT THE DOG SLOT LEAVES OUT AT A READ OF 4+ (the slot posts ~36 a season; the 11/3 dog expert's cell was
every dog at a read of 4+ with both teams 4+ games, +16.5% on 600 - the live slot adds 'never a trap, never a side
the own read is fighting, the read clears the price, one pick a game, never a Lock game'). Which of those rules cost
money? Rows: the 11/13 funnel (2018-26, ESPN's close). TRAIN 2018-22 / HELD 2023-26."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clib as C  # noqa: E402

L = C.L
R = L.load(L.OLD, markets=("ml",), keep_all=True)
DOG = [r for r in R if 100 <= r["odds"] <= 350]
A = [r for r in DOG if (r.get("dog_read") or -99) >= 4 and r["mn"] >= 4]
clears = lambda r: min(0.95, r["p_market"] + r["dog_read"] / 100) * r["dec"] - 1 > 0      # noqa: E731
print("EVERY DOG AT A READ OF 4+ (both teams 4+ games)")
L.rec("all", A, DOG)
L.rec("  not a trap, not fighting, clears the price (the slot's pool)", [r for r in A if not r["trap"] and not r["fighting"] and clears(r)], DOG)
L.rec("  LEFT OUT by those three", [r for r in A if r["trap"] or r["fighting"] or not clears(r)], DOG)
L.rec("  a TRAP", [r for r in A if r["trap"]], DOG)
L.rec("  FIGHTING (the own read fights the side), not a trap", [r for r in A if r["fighting"] and not r["trap"]], DOG)
L.rec("  not clearing the price only", [r for r in A if not r["trap"] and not r["fighting"] and not clears(r)], DOG, min_n=5)
f = [r for r in A if r["fighting"] and not r["trap"]]
for w in ("home", "road", "neutral"):
    L.rec(f"     fighting, {w}", [r for r in f if r["where"] == w], DOG, min_n=5)
L.rec("     fighting, +100..+150", [r for r in f if r["odds"] <= 150], DOG)
L.rec("     fighting, +151..+350", [r for r in f if r["odds"] > 150], DOG)
L.rec("     fighting, read 4-5", [r for r in f if r["dog_read"] < 5], DOG)
L.rec("     fighting, read 5+", [r for r in f if r["dog_read"] >= 5], DOG)
L.rec("     fighting, league game", [r for r in f if r["conf"]], DOG)
L.rec("     fighting, non-league", [r for r in f if r["conf"] is False], DOG)
if f:
    print("  price-free: the fighting dogs won %.1f%% vs the no-vig %.1f%% (%d); own read %.1f%%" % (
        100 * sum(r["win"] for r in f) / len(f), 100 * sum(r["p_market"] for r in f) / len(f), len(f),
        100 * sum((r["edge_own"] + 1) / r["dec"] for r in f if r["edge_own"] is not None) / max(1, sum(1 for r in f if r["edge_own"] is not None))))
    ee = [r["edge_own"] for r in f if r["edge_own"] is not None]
    print("  the fighting dogs' own edge: min %.3f median %.3f max %.3f" % (min(ee), sorted(ee)[len(ee) // 2], max(ee)))
print("\nBY THE OWN READ'S EDGE (read 4+, not a trap)")
nt = [r for r in A if not r["trap"] and r["edge_own"] is not None]
for lo, hi in ((-9, -0.10), (-0.10, -0.06), (-0.06, -0.03), (-0.03, 0.0), (0.0, 9)):
    L.rec(f"own edge {lo:+.2f}..{hi:+.2f}", [r for r in nt if lo <= r["edge_own"] < hi], DOG)
print("\nTHE 'FIGHTING' DOGS APART (read 4+, not a trap): the own read 3+ points under what the price needs, or the money ran from it")
ownf = lambda r: r["edge_own"] is not None and (r["edge_own"] + 1) / r["dec"] < 1 / r["dec"] - 0.03      # noqa: E731
L.rec("fighting by the OWN READ (3+ points under the price)", [r for r in f if ownf(r)], DOG)
L.rec("fighting by the money only (own read inside 3)", [r for r in f if not ownf(r)], DOG, min_n=5)
nv = lambda r: (r["edge_own"] + 1) / r["dec"] - r["p_market"]            # noqa: E731
g = [r for r in f if ownf(r)]
L.rec("  own-read fighters, own read within 2 points of the NO-VIG market", [r for r in g if nv(r) >= -0.02], DOG, min_n=5)
L.rec("  own-read fighters, own read 2+ under the no-vig market", [r for r in g if nv(r) < -0.02], DOG, min_n=5)
print("\nTHE TRAPS APART (read 4+)")
t = [r for r in A if r["trap"]]
for w in ("home", "road", "neutral"):
    L.rec(f"trap, {w}", [r for r in t if r["where"] == w], DOG, min_n=5)
L.rec("trap, +100..+150", [r for r in t if r["odds"] <= 150], DOG, min_n=5)
L.rec("trap, +151..+250", [r for r in t if 150 < r["odds"] <= 250], DOG, min_n=5)
L.rec("trap, +251..+350", [r for r in t if r["odds"] > 250], DOG, min_n=5)
L.rec("trap, read 4-5", [r for r in t if r["dog_read"] < 5], DOG, min_n=5)
L.rec("trap, read 5+", [r for r in t if r["dog_read"] >= 5], DOG, min_n=5)
L.rec("trap and not fighting", [r for r in t if not r["fighting"]], DOG, min_n=5)
L.rec("EVERY trap dog (any read, both 4+ games)", [r for r in DOG if r["trap"] and r["mn"] >= 4], DOG)
L.rec("EVERY non-trap dog (any read, both 4+ games)", [r for r in DOG if not r["trap"] and r["mn"] >= 4], DOG)
print("  price-free: the read-4+ traps won %.1f%% vs the no-vig %.1f%% (%d)" % (
    100 * sum(r["win"] for r in t) / len(t), 100 * sum(r["p_market"] for r in t) / len(t), len(t)))
# the slot with the two rules off: the best two a night
from collections import defaultdict  # noqa: E402
import pickle  # noqa: E402
K = pickle.load(open(os.path.expanduser("~/.cache/d503_studies/cbb_knowledge_b_rows.pkl"), "rb"))
eff = {(x["id"], x["side"]): x.get("eff") for x in K}
del K


def slot(use_trap, use_fight, cap=2):
    lockg = {r["gid"] for r in R if r["kind"] in ("lock", "play", "dogplay")}
    pool = defaultdict(list)
    for r in A:
        if (use_trap and r["trap"]) or (use_fight and r["fighting"]) or r["gid"] in lockg or r["kind"] in ("stackplay", "floor") or not clears(r):
            continue
        e = r.get("eff_p") if r.get("eff_p") is not None else eff.get((r["gid"], r["side"]))
        r["effgap"] = None if e is None else e - r["p_market"]
        pool[r["date"]].append(r)
    out = []
    for d, v in pool.items():
        seen = set()
        for r in sorted(v, key=lambda r: (-r["dog_read"], -(r["effgap"] or 0))):
            if r["gid"] not in seen:
                seen.add(r["gid"])
                if len(seen) <= cap:
                    out.append(dict(r, u=2.0 if r["dog_read"] >= 6 else 1.0))
    return out


print("\nTHE SLOT (the best two a night, 1u / 2u at a read of 6+) WITH AND WITHOUT THE TWO RULES")
base = slot(True, True)
kb = {(r["gid"], r["side"]) for r in base}
for nm, a, b in (("today: never a trap, never fighting", True, True), ("fighting allowed (trap still out)", True, False),
                 ("traps allowed (fighting still out)", False, True), ("both allowed - the 11/3 study's own rule", False, False)):
    s = slot(a, b)
    L.rec(nm, s, DOG, units=True)
    add = [r for r in s if (r["gid"], r["side"]) not in kb]
    if add:
        L.rec("     the plays it adds", add, DOG, units=True, min_n=5)
print(f"\ncells read: {L.CELLS[0]}")
