"""11/15 - THE BOARD UNDER THE SIZE CHANGES THE UNSEEN SEASONS POINTED AT, both replay boards - NONE WIRED: the long hockey /
college football Dog of the Day at 1u instead of ½u (s8_dog_price.out), every league's long Dog at 1u, the long Dog at 2u,
the NBA Dog whose own read is under the price at 1u (the owner's thin-edge rule), the NBA favorite play at 2u.
Why the long Dog moves the board so little: since 11/4 the ⭐ already raises the Dog to 1u unless a Lock is up.
Usage: python results/studies/sizing_1115/s10_after.py > results/studies/sizing_1115/s10_after.out"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sizing_1114"))
import lib as L  # noqa: E402
import s1_star as S  # noqa: E402

for name, (board, _by) in L.boards().items():
    print("=" * 30, f"BOARD {name}")
    st = {(d, r["team"], k) for d, r, u, k in S.stars(board, S.today)}
    star = lambda d, r, u, k: max(1.0, u) if (d, r["team"], k) in st else u   # noqa: E731
    long_ = lambda r, k: k == "dog" and r["league"] != "nba" and r["odds"] > 150   # noqa: E731
    V = [("TODAY: today's sizes (+ the ⭐ raise) - unchanged", lambda d, r, u, k, ps: star(d, r, u, k)),
         ("   not wired: the long hockey / college football Dog 1u", lambda d, r, u, k, ps: max(1.0, star(d, r, u, k)) if long_(r, k) and r["league"] in ("nhl", "ncaaf") else star(d, r, u, k)),
         ("   not wired: every league's long Dog 1u (the NFL too)", lambda d, r, u, k, ps: max(1.0, star(d, r, u, k)) if long_(r, k) else star(d, r, u, k)),
         ("   not wired: the long hockey / college Dog 2u", lambda d, r, u, k, ps: 2.0 if long_(r, k) and r["league"] in ("nhl", "ncaaf") else star(d, r, u, k)),
         ("   not wired (the owner's call): that + the ½u NBA Dog at 1u", lambda d, r, u, k, ps: max(1.0, star(d, r, u, k)) if (long_(r, k) and r["league"] in ("nhl", "ncaaf")) or (k == "dog" and r["league"] == "nba") else star(d, r, u, k)),
         ("   not wired: that + the NBA favorite play 2u", lambda d, r, u, k, ps: 2.0 if k == "nbafav" else (max(1.0, star(d, r, u, k)) if long_(r, k) and r["league"] in ("nhl", "ncaaf") else star(d, r, u, k))),
         ]
    for nm, fn in V:
        L.schedule(nm, board, fn)
    lg = [(d, r, 1) for d in sorted(board) for r, u, k in board[d] if long_(r, k)]
    for l in ("nhl", "ncaaf", "nfl"):
        L.line(f"the long Dog, {l}", [t for t in lg if t[1]["league"] == l])
    L.line("the NBA Dog at ½u (own read under the price)", [(d, r, 1) for d in sorted(board) for r, u, k in board[d] if k == "dog" and r["league"] == "nba" and u == 0.5])
    L.line("the NBA Dog at 1u (own read over)", [(d, r, 1) for d in sorted(board) for r, u, k in board[d] if k == "dog" and r["league"] == "nba" and u == 1.0])
