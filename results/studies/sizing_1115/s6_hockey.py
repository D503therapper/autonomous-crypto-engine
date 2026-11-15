"""11/15 - THE GATE THAT IS TOO TIGHT: THE NEXT HOCKEY DOG. The funnel (s3 / s4) found one kept-off cell up in both halves
on both boards with a dose and a placebo: a hockey dog with a NAMED REASON, clean (no trap / not fighting / not waiting),
THIN (the floor's kind), a dog score under the Dog gate (6) - kept off only because the board already had its FLOOR_MIN (2)
unit plays or a better-scored dog took the slot. The exact rule tested here, the way the engine would post it:
   one a day - the best-scored hockey dog +100..+350 that passes the floor's own checks, NOT on a game the board is on,
   dog score S or more - a ½u play ON TOP of the board (the floor's cap of 2 does not count it).
S = 2 / 3 / 4 / 5; a price cap; with / without the gated-but-not-posted hockey dogs. Five checks + the board before / after.
Usage: python results/studies/sizing_1115/s6_hockey.py > results/studies/sizing_1115/s6_hockey.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sizing_1114"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L  # noqa: E402
import s1_star as S  # noqa: E402
import s4_candidates as C  # noqa: E402

G = L.sv.GAMES


def pool_day(board, by, d, gated=True, thin=True):
    on = {(r["team"], r["opp"]) for r, u, k in board.get(d, [])}
    games = {G(r) for r, u, k in board.get(d, [])}
    out = []
    for r in by[d]:
        if r.get("market", "ml") != "ml" or r["league"] != "nhl" or r["result"] not in ("won", "lost"):
            continue
        if (r["team"], r["opp"]) in on or G(r) in games or not L.sv.floor_ok(r):
            continue
        if r.get("dog_gate"):
            if not gated or not r["dog_own_ok"]:
                continue
        elif thin and not r.get("thin"):
            continue
        out.append(r)
    return out


def picks(board, by, smin, omax=350, gated=True, thin=True, n=1):
    out = []
    for d in sorted(by):
        p = [r for r in pool_day(board, by, d, gated, thin) if r["dog_score"] >= smin and r["odds"] <= omax]
        p.sort(key=lambda r: (-r["dog_score"], -r["edge"]))
        out += [(d, r, 1) for r in p[:n]]
    return out


def run(name, board, by):
    print("=" * 30, f"BOARD {name}")
    st = {(d, r["team"], k) for d, r, u, k in S.stars(board, S.today)}
    T = lambda d, r, u, k, ps: max(1.0, u) if (d, r["team"], k) in st else u   # noqa: E731
    off = C.kept_off(board, by)
    nhl_dogs = [(d, r, 1) for d, r, w in off if r["league"] == "nhl" and r["odds"] >= 100]
    clean = [(d, r, 1) for d in sorted(by) for r in pool_day(board, by, d)]
    posted_hk = [(d, r, 1) for d in sorted(board) for r, u, k in board[d] if r["league"] == "nhl" and r["odds"] >= 100]
    L.line("the board's POSTED hockey dogs (every kind)", posted_hk)
    for k in ("dog", "dogplay", "floor"):
        L.line(f"   posted hockey {k}", [(d, r, 1) for d in sorted(board) for r, u, kk in board[d] if r["league"] == "nhl" and kk == k and r["odds"] >= 100])
    L.line("every kept-off hockey dog (the vig)", nhl_dogs)
    L.line("the pool: kept-off, passes the floor's checks", clean)
    print("  THE RULE, one a day (the best score first):")
    base = L.schedule("the board today", board, T)
    for smin in (0, 2, 3, 4, 5):
        for omax in (350, 199, 159):
            ex = picks(board, by, smin, omax)
            if not ex:
                continue
            nm = f"score {smin}+{'' if omax == 350 else f', to +{omax}'}"
            o = L.line(f"   {nm}", ex)
            if omax == 350 or smin == 4:
                print(f"        seasons: {C.seasons(ex)} | a random same-size draw of kept-off hockey dogs did as well "
                      f"{L.placebo(ex, nhl_dogs)} of 2,000; of the POOL {L.placebo(ex, clean)}; of the posted hockey dogs {L.placebo(ex, posted_hk)}")
                L.schedule(f"   board + {nm} at ½u", C.with_extra(board, ex), T)
    print("  WITHOUT the gated-not-posted dogs (under the gate only):")
    for smin in (2, 4):
        L.line(f"   score {smin}+ under the gate", picks(board, by, smin, gated=False))
    print("  TWO a day:")
    ex2 = picks(board, by, 4, n=2)
    L.line("   score 4+, up to two a day", ex2)
    L.line("   ... the second one alone", [t for t in ex2 if t not in picks(board, by, 4)])
    print("  THE DOSE inside the pool (every kept-off pool dog, not one a day):")
    for lo, hi in ((-99, 0), (0, 2), (2, 4), (4, 6), (6, 99)):
        L.line(f"   dog score {lo}..{hi}", [t for t in clean if lo <= t[1]["dog_score"] < hi])
    print("  WHAT KIND OF DAY (score 4+, one a day):")
    ex = picks(board, by, 4)
    nu = lambda d: len(board.get(d, []))   # noqa: E731
    for lo, hi in ((0, 1), (2, 2), (3, 9)):
        L.line(f"   the board already has {lo}..{hi} unit plays", [t for t in ex if lo <= nu(t[0]) <= hi])
    hk = lambda d: sum(1 for r, u, k in board.get(d, []) if r["league"] == "nhl")   # noqa: E731
    L.line("   the board has a hockey unit play", [t for t in ex if hk(t[0])])
    L.line("   the board has no hockey unit play", [t for t in ex if not hk(t[0])])
    L.line("   home", [t for t in ex if t[1]["home"]])
    L.line("   road", [t for t in ex if not t[1]["home"]])
    for lo, hi in ((100, 129), (130, 159), (160, 199), (200, 350)):
        L.line(f"   +{lo}..+{hi}", [t for t in ex if lo <= t[1]["odds"] <= hi])
    L.line("   hot dog (3+ win streak)", [t for t in ex if t[1].get("hot_dog")])
    L.line("   gated (6+), not posted", [t for t in ex if t[1].get("dog_gate")])
    L.line("   under the gate (4-6)", [t for t in ex if not t[1].get("dog_gate")])
    by_m = defaultdict(list)
    for t in ex:
        by_m[t[0][5:7]].append(t)
    print("   by month: " + "  ".join(f"{m} {sum(r['result'] == 'won' for _, r, _ in v)}-{sum(r['result'] == 'lost' for _, r, _ in v)} "
                                      f"{100 * sum(L.flat(r) for _, r, _ in v) / len(v):+.0f}%" for m, v in sorted(by_m.items())))
    print("   the live window rows: " + "; ".join(f"{d} {r['team']} {r['odds']:+d} {r['result']}" for d, r, _ in ex if L.half(d) == "live"))
    for u in (0.5, 1.0):
        L.schedule(f"   BOARD + the next hockey dog (score 4+) at {u:g}u", C.with_extra(board, ex, u), T)


if __name__ == "__main__":
    for name, (board, by) in L.boards().items():
        run(name, board, by)
