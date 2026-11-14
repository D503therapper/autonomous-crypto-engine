"""11/14 - follow-up to s1: on the days the ⭐ had BOTH an eligible Lock and an eligible Dog (today's rank takes the Lock),
which one won more vs its price? (flat 1u, both boards)
Usage: python results/studies/sizing_1114/s5_lock_vs_dog.py > results/studies/sizing_1114/s5_lock_vs_dog.out"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L  # noqa: E402
import s1_star as S  # noqa: E402

for name, (board, _by) in L.boards().items():
    lk, dg = [], []
    for d in sorted(board):
        el = [x for x in board[d] if S.eligible(*x)]
        l_ = [x for x in el if x[2] == "lock"]
        g_ = [x for x in el if x[2] == "dog"]
        if l_ and g_:
            lk.append((d, l_[0][0], 1.0))
            dg.append((d, g_[0][0], 1.0))
    print(f"-- {name}: {len(lk)} days with both")
    L.line("the Lock (today's ⭐)", lk)
    L.line("the Dog (the other choice)", dg)
