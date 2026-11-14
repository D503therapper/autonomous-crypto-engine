"""11/14 - THE WHOLE BOARD under today's sizing (+ the ⭐ raise) vs the size-ups the owner asked about, both replay boards:
units won / risked, ROI, the worst losing stretch (peak to trough, by day), seasons up. None of the size-ups passed the
cell test (s2_sizing.out) - this shows what each would do to the money and the drawdown anyway.
Usage: python results/studies/sizing_1114/s3_board.py > results/studies/sizing_1114/s3_board.out"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L  # noqa: E402
import s1_star as S  # noqa: E402,F401  (prints its own tables - silenced below)

KR = S.KR


def star_of(board):
    return {(d, r["team"], k) for d, r, u, k in S.stars(board, S.today)}


def run(board):
    st = star_of(board)
    star = lambda d, r, u, k: max(1.0, u) if (d, r["team"], k) in st else u   # noqa: E731
    FH = lambda r, k: k in ("floor", "floorfb") and r["league"] == "nhl"   # noqa: E731
    ds = lambda r: -99 if r.get("dog_score") is None else r["dog_score"]   # noqa: E731
    V = [
        ("TODAY: today's sizes + the ⭐ raise (1u at least)", lambda d, r, u, k, ps: star(d, r, u, k)),
        ("   today's sizes, no ⭐ raise", lambda d, r, u, k, ps: u),
        ("   the ⭐ at 2u (instead of 1u at least)", lambda d, r, u, k, ps: max(2.0, u) if (d, r["team"], k) in st else u),
        ("THE PREDATORS IDEA: every floor hockey dog at 2u", lambda d, r, u, k, ps: 2.0 if FH(r, k) else star(d, r, u, k)),
        ("   every floor hockey dog at 1u", lambda d, r, u, k, ps: max(1.0, u) if FH(r, k) else star(d, r, u, k)),
        ("   floor hockey dogs at a dog score under 0 at 2u", lambda d, r, u, k, ps: 2.0 if FH(r, k) and ds(r) < 0 else star(d, r, u, k)),
        ("   every floor play (any league) at 1u", lambda d, r, u, k, ps: max(1.0, u) if k in ("floor", "floorfb") else star(d, r, u, k)),
        ("THE 3u DOG: the 2u Dog at a dog score 8+ at 3u", lambda d, r, u, k, ps: 3.0 if k == "dog" and u == 2.0 and ds(r) >= 8 else star(d, r, u, k)),
        ("   the 2u Dog at +130..+150 at 3u", lambda d, r, u, k, ps: 3.0 if k == "dog" and u == 2.0 and r["odds"] >= 130 else star(d, r, u, k)),
        ("   every 2u Dog at 3u", lambda d, r, u, k, ps: 3.0 if k == "dog" and u == 2.0 else star(d, r, u, k)),
        ("THE OWN EDGE: plays whose own read is 3+ over the price at 2x", lambda d, r, u, k, ps: 2 * star(d, r, u, k) if (L.own_margin(r) or -99) >= 3 else star(d, r, u, k)),
        ("THE NBA FLOOR at 1u", lambda d, r, u, k, ps: 1.0 if k == "nbafloor" else star(d, r, u, k)),
        ("EVERYTHING DOUBLED (the chase: the same bets, twice the size)", lambda d, r, u, k, ps: 2 * star(d, r, u, k)),
    ]
    for name, fn in V:
        L.schedule(name, board, fn)


if __name__ == "__main__":
    for name, (board, _by) in L.boards().items():
        print("=" * 30, f"BOARD {name}")
        run(board)
