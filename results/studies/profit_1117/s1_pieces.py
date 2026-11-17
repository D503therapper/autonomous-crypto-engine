"""11/17 MAX PROFIT - (1) every piece ALONE on today's board: the group's own record (flat, both halves), what the added
units earn, the board with it. A piece is OUT when its group's held-out ROI is negative (the owner: a bigger number never
sits on a losing group) or it breaks a standing rule.
Usage: python results/studies/profit_1117/s1_pieces.py > results/studies/profit_1117/s1_pieces.out"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plib as L  # noqa: E402

M = L.M
t0 = L.sizes()
base = L.summ(t0)
print(L.row("TODAY (the 11/17 code, the short runner-up 1u in)", base))
print("     by season:", M.seas_str(base), f"| a unit play on {base['dayshare']:.1f}% of board days\n")


def f(x):
    w = sum(r["result"] == "won" for r in x)
    return w, len(x) - w, 100 * sum(M.flat(r) for r in x) / len(x) if x else 0.0


for key, (name, test, nu) in L.PIECES.items():
    g = [r for r in L.NL if test(r)]
    tr = [r for r in g if M.half(r["date"]) == "train"]
    he = [r for r in g if M.half(r["date"]) == "held"]
    lv = [r for r in L.P if test(r) and M.half(r["date"]) == "live"]
    sz = L.sizes([key])
    o = L.summ(sz)
    print(f"[{key}] {name}")
    print(f"     the group flat: {len(g)} plays {f(g)[0]}-{f(g)[1]} {f(g)[2]:+.1f}% | train {f(tr)[0]}-{f(tr)[1]} {f(tr)[2]:+.1f}% | HELD OUT {f(he)[0]}-{f(he)[1]} {f(he)[2]:+.1f}% | live-replay {f(lv)[0]}-{f(lv)[1]}")
    print("     " + L.added_str(L.added(t0, sz)))
    print(L.row("   the board with it", o, base))
for nm, kw in (("the ⭐ at 2u at least", dict(star=2.0)), ("the ⭐ at 2u, only on a play already 1u+", dict(star=2.0, star_from=1.0)),
               ("the ⭐ at 1.5u at least", dict(star=1.5))):
    sz = L.sizes(**kw)
    o = L.summ(sz)
    print(f"[star] {nm}")
    print("     " + L.added_str(L.added(t0, sz)))
    print(L.row("   the board with it", o, base))
print("\n===== THE ⭐ BY THE KIND IT SITS ON (today's sizes; flat, both halves) - where would a 2u ⭐ sit on a losing group?")
st = [r for r in L.NL if t0[id(r)][2]]
c = {}
for r in st:
    c.setdefault(L.k(r), []).append(r)
for kk, x in sorted(c.items(), key=lambda kv: -len(kv[1])):
    tr = [r for r in x if M.half(r["date"]) == "train"]
    he = [r for r in x if M.half(r["date"]) == "held"]
    print(f"   ⭐ on {kk:44s} {len(x):4d} {f(x)[0]}-{f(x)[1]} {f(x)[2]:+6.1f}% | train {f(tr)[0]}-{f(tr)[1]} {f(tr)[2]:+6.1f}% | HELD OUT {f(he)[0]}-{f(he)[1]} {f(he)[2]:+6.1f}%")
