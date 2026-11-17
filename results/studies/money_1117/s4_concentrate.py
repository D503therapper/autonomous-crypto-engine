"""11/17 MOST MONEY - (4) CONCENTRATION: do fewer, bigger bets beat more, smaller ones? On the board (mlib.board, R3L):
  A  only the day's top 1 / 2 / 3 plays by the ⭐'s own order (sports.BEST_KIND_RANK, the bigger size, the bigger edge -
     nothing fit here), flat 1u / 2u / 3u and at today's size, against the full board
  B  the same with the order FIT on the train half (the kinds by their train ROI) and judged on the held half - and the mirror
  C  the plays the top-N rule leaves OFF: do they lose? (if they win, concentration only throws money away)
  D  the ⭐ by the kind it lands on
Usage: python results/studies/money_1117/s4_concentrate.py > results/studies/money_1117/s4_concentrate.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M  # noqa: E402

P, DAYS = M.board()
base = M.summ(P, DAYS)
print(M.line("TODAY'S BOARD", base, w=58))
by = defaultdict(list)
for r in P:
    by[r["date"]].append(r)
print("  plays a day (days with a play): " + ", ".join(f"{n}: {sum(len(v) == n for v in by.values())}" for n in range(1, 8)))


def order_best(r):
    return (-1 if r["u0"] >= 3 else M.RANK.get(r["kind"], 9), -r["u0"], -M.margin(r))


def top(n, key):
    keep = set()
    for d, ps in by.items():
        for r in sorted(ps, key=key)[:n]:
            keep.add(id(r))
    return keep


print("\n===== A. THE DAY'S TOP N BY THE ⭐'S OWN ORDER (nothing fit)")
for n in (1, 2, 3):
    keep = top(n, order_best)
    K = [r for r in P if id(r) in keep]
    for nm, f in (("today's size", lambda r: r["u"]), ("flat 1u", lambda r: 1.0), ("flat 2u", lambda r: 2.0), ("flat 3u", lambda r: 3.0),
                  ("today's size x2 (cap 5u)", lambda r: min(5.0, 2 * r["u"]))):
        print(M.line(f"top {n} a day, {nm}", M.summ(K, DAYS, f), base, w=58))
    L = [r for r in P if id(r) not in keep]
    if L:
        print(M.line(f"   C. the plays top-{n} leaves OFF (today's size)", M.summ(L, None), w=58))
        print(M.line(f"   C. ... flat 1u", M.summ(L, None, lambda r: 1.0), w=58))
print("\n  the day's top play at 2u / 3u AND the rest of the board as it is")
k1 = top(1, order_best)
for s in (2.0, 3.0):
    print(M.line(f"the top play {s:g}u at least, the rest today's size", M.summ(P, DAYS, lambda r: max(s, r["u"]) if id(r) in k1 else r["u"]), base, w=58))

print("\n===== B. THE ORDER FIT ON ONE HALF (kinds by their flat ROI there, 15+ plays; others by the ⭐'s order after), judged on the other")
for fit, judge in (("train", "held"), ("held", "train")):
    st = defaultdict(lambda: [0, 0.0])
    for r in P:
        if M.half(r["date"]) == fit:
            st[r["k"]][0] += 1
            st[r["k"]][1] += M.flat(r)
    kr = {k: s / n for k, (n, s) in st.items() if n >= 15}
    key = lambda r: (-kr.get(r["k"], -9), order_best(r))      # noqa: E731
    J = [r for r in P if M.half(r["date"]) == judge]
    jb = M.summ(J, DAYS)
    print(f"  fit on {fit}, judged on {judge}: the full board {jb['net']:+.1f}u on {jb['risk']:.0f}u ({jb['roi']:+.1f}%), worst {jb['dd']:+.1f}u")
    for n in (1, 2, 3):
        keep = top(n, key)
        K = [r for r in J if id(r) in keep]
        for nm, f in (("today's size", lambda r: r["u"]), ("flat 1u", lambda r: 1.0), ("flat 2u", lambda r: 2.0)):
            o = M.summ(K, None, f)
            print(f"      top {n} by the {fit} order, {nm:14s}: {o['w']}-{o['l']} {o['net']:+6.1f}u on {o['risk']:5.0f}u ({o['roi']:+5.1f}%), worst {o['dd']:+5.1f}u, u/worst {(-o['net'] / o['dd']) if o['dd'] else 0:.1f}")
        L = [r for r in J if id(r) not in keep]
        o = M.summ(L, None, lambda r: 1.0)
        print(f"         ... the plays left off, flat 1u: {o['w']}-{o['l']} {o['roi']:+.1f}%")

print("\n===== D. THE ⭐ BY THE KIND IT LANDS ON (flat 1u ROI of the starred plays; the raise = the extra units over the kind's size)")
st = defaultdict(list)
for r in P:
    if r["star"]:
        st[r["k"]].append(r)
for k, rs in sorted(st.items(), key=lambda kv: -len(kv[1])):
    o = M.summ(rs, None, lambda r: 1.0)
    e = M.summ(rs, None, lambda r: r["u"] - r["u0"])
    print(f"  {k:44s} {o['w']:3d}-{o['l']:<3d} flat {o['roi']:+6.1f}% | train {M.roi(o['tr'], o['trr']):+6.1f}% ({int(o['trr'])}) | held {M.roi(o['he'], o['her']):+6.1f}% ({int(o['her'])}) | up {o['up']}/{o['ns']}"
          f" | the raise {e['net']:+5.1f}u on {e['risk']:4.1f}u")
fl = [r for r in P if r["star"] and r["kind"] == "floor"]
solo_floor = [r for r in fl if all(q["kind"] == "floor" for q in by[r["date"]])]
print(M.line("the ⭐ on a floor play (flat 1u)", M.summ(fl, None, lambda r: 1.0), w=58))
print(M.line("   ... on a day with only floor plays", M.summ(solo_floor, None, lambda r: 1.0), w=58))
print(M.line("the ⭐ on any ½u DOG (floor / NBA floor / runner-up / long Dog)", M.summ([r for r in P if r["star"] and r["u0"] < 1 and r["odds"] >= 100], None, lambda r: 1.0), w=58))
print(M.line("the ⭐ on a ½u FAVORITE", M.summ([r for r in P if r["star"] and r["u0"] < 1 and r["odds"] < 0], None, lambda r: 1.0), w=58))
print(M.line("THE BOARD, the ⭐ never raises a floor play", M.summ(P, DAYS, lambda r: r["u0"] if r["kind"] == "floor" else r["u"]), base, w=58))
print(M.line("THE BOARD, no ⭐ raise at all", M.summ(P, DAYS, lambda r: r["u0"]), base, w=58))
