"""11/14 - THE ⭐ STUDY (the owner, 11/13: "The engine likes best picks suck ass, so that makes me nervous" - live 3-5).
How today's code picks the ⭐ (sports.best_pool / best_rank / BEST_KIND_RANK: open single unit plays -150..+350, never
fighting, the read its units ride on beats the price (BEST_OVER_FROM), no forced ⭐ (NO_FORCED_BEST_FROM); the kind the
replay trusts, then the bigger size, then the bigger edge on that read; raised to 1u at least) replayed on both boards,
against rankings NAMED BEFORE LOOKING. A better ⭐ has to win more vs its price than today's in BOTH halves on BOTH boards
and beat a placebo (a random eligible play a day, 2,000 times).
Usage: python results/studies/sizing_1114/s1_star.py > results/studies/sizing_1114/s1_star.out"""
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L  # noqa: E402

KR = {"lock": 0, "dog": 1, "nbafav": 2, "dogplay": 3, "nbafloor": 4, "solo": 5, "floor": 6, "floorfb": 6, "play": 7, "backup": 8}


def edge(r, k):
    return L.read_of(r, k) * r["dec"] - 1


def eligible(r, u, k):
    return -150 <= r["odds"] <= 350 and not r["fighting"] and L.beats(r, k) and u > 0


def today(r, u, k):
    return (KR.get(k, 9), -u, -edge(r, k))


def om(r):
    m = L.own_margin(r)
    return -99 if m is None else m


RANKS = {
    "S0 TODAY (kind trust, size, read edge)": today,
    "S1 the biggest edge on the read its units ride on": lambda r, u, k: (-edge(r, k),),
    "S2 the biggest OWN-read margin over the price": lambda r, u, k: (-om(r), today(r, u, k)),
    "S3 the Dog first, then the NBA fav play, the Lock ...": lambda r, u, k: ({"dog": 0, "nbafav": 1, "lock": 2}.get(k, 3 + KR.get(k, 9)), -u, -edge(r, k)),
    "S4 a price -150..+150 first, then today's": lambda r, u, k: (0 if r["odds"] <= 150 else 1,) + today(r, u, k),
    "S5 hockey first, then today's": lambda r, u, k: (0 if r["league"] == "nhl" else 1,) + today(r, u, k),
    "S6 the biggest dog score (dogs), else today's": lambda r, u, k: ((0, -(r.get("dog_score") or -99)) if r["odds"] > 0 and r.get("dog_score") is not None else (1, 0)) + today(r, u, k),
    "S7 the surest (rank_p)": lambda r, u, k: (-(r.get("rank_p") or r["p"]),),
    "S8 favorites first, then today's": lambda r, u, k: (0 if r["odds"] < 0 else 1,) + today(r, u, k),
    "S9 the biggest size first, then the read edge": lambda r, u, k: (-u, -edge(r, k)),
    "S10 both reads over the price (own + its read) first": lambda r, u, k: (0 if om(r) > 0 else 1,) + today(r, u, k),
}


def stars(board, key, elig=eligible):
    out = []
    for d in sorted(board):
        pool = [(r, u, k) for r, u, k in board[d] if elig(r, u, k)]
        if pool:
            r, u, k = min(pool, key=lambda x: key(*x))
            out.append((d, r, u, k))
    return out


def board_with(board, st):
    """the board's units with the ⭐ raise (1u at least) on the given stars."""
    mark = {(d, r["team"], k) for d, r, u, k in st}
    return lambda d, r, u, k, ps: max(1.0, u) if (d, r["team"], k) in mark else u


def main():
    for name, (board, _by) in L.boards().items():
        n_days = len(board)
        print("=" * 30, f"BOARD {name}: {n_days} board days, {sum(1 for d in board if board[d])} with a unit play, "
              f"{sum(len(v) for v in board.values())} unit plays")
        base = L.schedule("the board with NO ⭐ (no raise)", board, lambda d, r, u, k, ps: u)
        st0 = stars(board, today)
        print(f"  days with a ⭐ under today's rule: {len(st0)}; kinds {dict(Counter(k for *_, k in st0).most_common())}; "
              f"leagues {dict(Counter(r['league'] for _, r, _, _ in st0).most_common())}")
        print("-- the ⭐ PICK itself, flat 1u (is it the board's best play?)")
        allp = [(d, r, u) for d in board for r, u, k in board[d] if eligible(r, u, k)]
        L.line("every ELIGIBLE unit play (the ⭐ pool)", allp)
        L.line("every unit play on the board", [(d, r, u) for d in board for r, u, k in board[d]])
        res = {}
        for nm, key in RANKS.items():
            st = stars(board, key)
            c = L.line(nm, [(d, r, 1.0) for d, r, u, k in st])
            res[nm] = (c, st)
        print("-- the ⭐ at the units it posts at (raised to 1u+), and the board with that ⭐")
        for nm, (c, st) in res.items():
            L.line(nm + " [units]", [(d, r, max(1.0, u)) for d, r, u, k in st], units=True)
            L.schedule("   the board with this ⭐", board, board_with(board, st))
        print("-- the PLACEBO: a random eligible play a day as the ⭐, 2,000 times (flat ROI, train / held)")
        rnd = random.Random(1114)
        days = [d for d in sorted(board) if any(eligible(*x) for x in board[d])]
        pools = {d: [x for x in board[d] if eligible(*x)] for d in days}
        draws = defaultdict(list)
        for _ in range(2000):
            acc = {"train": [0.0, 0], "held": [0.0, 0]}
            for d in days:
                h = L.half(d)
                if h == "live":
                    continue
                r, u, k = rnd.choice(pools[d])
                acc[h][0] += L.flat(r)
                acc[h][1] += 1
            for h in acc:
                draws[h].append(100 * acc[h][0] / max(1, acc[h][1]))
        for h in ("train", "held"):
            v = sorted(draws[h])
            print(f"   random ⭐ {h}: median {v[1000]:+.1f}%, 5th-95th {v[100]:+.1f}% .. {v[1900]:+.1f}%")
        for nm, (c, st) in res.items():
            tr, he = c["train"]["roi"], c["held"]["roi"]
            btr = sum(1 for x in draws["train"] if x >= tr)
            bhe = sum(1 for x in draws["held"] if x >= he)
            print(f"   {nm:52s} train {tr:+6.1f}% (random did as well {btr:4d}/2000) | held {he:+6.1f}% ({bhe:4d}/2000)")
        print("-- the ⭐ by kind under today's rule (flat)")
        for kk in sorted({k for *_, k in st0}):
            L.line(f"   ⭐ on a {kk}", [(d, r, 1.0) for d, r, u, k in st0 if k == kk])
        print("-- the ⭐ by league / price under today's rule (flat)")
        for lg in sorted({r["league"] for _, r, _, _ in st0}):
            L.line(f"   ⭐ in {lg}", [(d, r, 1.0) for d, r, u, k in st0 if r["league"] == lg])
        for lo, hi in ((-150, -101), (100, 150), (151, 350)):
            L.line(f"   ⭐ at {lo:+d}..{hi:+d}", [(d, r, 1.0) for d, r, u, k in st0 if lo <= r["odds"] <= hi])
        print("-- what the ⭐ raise ADDS (the extra units on plays raised from ½u to 1u) under today's rule")
        L.line("   the extra ½u (raised plays only)", [(d, r, 1.0 - u) for d, r, u, k in st0 if u < 1.0], units=True)
        L.line("   the ⭐ on a play already 1u+ (no extra units)", [(d, r, u) for d, r, u, k in st0 if u >= 1.0], units=True)
        print()


if __name__ == "__main__":
    main()
