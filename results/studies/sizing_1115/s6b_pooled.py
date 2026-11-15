"""11/15 - the next hockey dog, the SELECTION check: is "score 4+" a fact about the dog or about being kept off? Every
hockey dog that passes the floor's checks (named reason, clean, thin, a dog score, under the gate) - POSTED by the floor
or KEPT OFF - pooled, by dog score band; and the floor's own posted hockey dogs by the same bands.
Usage: python results/studies/sizing_1115/s6b_pooled.py > results/studies/sizing_1115/s6b_pooled.out"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sizing_1114"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L  # noqa: E402

G = L.sv.GAMES
for name, (board, by) in L.boards().items():
    print("=" * 30, f"BOARD {name}")
    pooled, posted, off = [], [], []
    for d in sorted(by):
        kind = {(r["team"], r["opp"]): k for r, u, k in board.get(d, [])}
        games = {G(r) for r, u, k in board.get(d, [])}
        for r in by[d]:
            if r.get("market", "ml") != "ml" or r["league"] != "nhl" or r["result"] not in ("won", "lost"):
                continue
            if not L.sv.floor_ok(r) or r.get("dog_gate") or not r.get("thin"):
                continue
            k = kind.get((r["team"], r["opp"]))
            if k in ("floor", "floorfb"):
                posted.append((d, r, 1))
            elif k is None and G(r) not in games:
                off.append((d, r, 1))
            else:
                continue
            pooled.append((d, r, 1))
    for nm, rs in (("POOLED (the floor's + kept off)", pooled), ("the floor's POSTED hockey dogs", posted), ("KEPT OFF", off)):
        print(" ", nm)
        L.line("   all", rs)
        for lo, hi in ((-99, 0), (0, 2), (2, 4), (4, 6)):
            L.line(f"   dog score {lo}..{hi}", [t for t in rs if lo <= t[1]["dog_score"] < hi])
        L.line("   dog score 3+", [t for t in rs if t[1]["dog_score"] >= 3])
        L.line("   dog score 4+", [t for t in rs if t[1]["dog_score"] >= 4])
