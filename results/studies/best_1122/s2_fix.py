"""11/22 - WHY THE ⭐ HAS LOST - (2) what to wire: (i) the tie-break between plays of the same biggest size; (ii) the raise
cut by what it sits on, each with its placebo and the price a point worse; (iii) how often the ⭐ ends up SMALLER than
another play on the board (the owner's rule: never) and what those ⭐s did; (iv) the whole board under each plan.
Usage: python results/studies/best_1122/s2_fix.py > results/studies/best_1122/s2_fix.out"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blib as B  # noqa: E402

M = B.M
half = B.half


def wired2(r):
    return 2.0 if (r["odds"] <= 150 and (r["kind"] in ("lock", "dog") or r["u0"] >= 1.0)) else 1.0


def star_u(r):
    return max(r["u0"], wired2(r))


print("===== (i) THE TIE-BREAK - days the pool holds 2+ plays of the SAME biggest size (the only days it decides anything)")
ties = {}
for d in B.DAYS:
    pl = B.POOL.get(d) or []
    if not pl:
        continue
    top = max(r["u0"] for r in pl)
    t = [r for r in pl if r["u0"] == top]
    if len(t) >= 2:
        ties[d] = t
print(f"   {len([d for d in ties if half(d) != 'live'])} such days (train + held), {len([d for d in ties if half(d) == 'live'])} live")
TB = [
    ("the bigger edge on the read its units ride on (11/22)", lambda r: -M.margin(r)),
    ("the weighed read over the NO-VIG price", lambda r: -B.weighed_over_nv(r)),
    ("the bigger OWN-read edge", lambda r: -B.own_edge(r)),
    ("the surest (the highest win chance)", lambda r: -M.read_of(r)),
    ("the shortest price", lambda r: r["odds"] if r["odds"] < 0 else r["odds"] + 1000),
    ("the kind the replay trusts, then the edge", lambda r: (M.RANK.get(r["kind"], 9), -M.margin(r))),
    ("the smaller edge [the mirror]", lambda r: M.margin(r)),
    ("the longest price [the mirror]", lambda r: -(r["odds"] if r["odds"] > 0 else r["odds"] - 1000)),
]
allt = [r for d in ties for r in ties[d]]
print(B.line("every tied play, flat", allt))
for nm, sel in TB:
    rs = [min(ties[d], key=sel) for d in ties]
    print(B.line(nm, rs))
    hit, mine, ex = B.placebo_star(rs, pool_of=ties.get)
    print(f"        placebo (a random one of the tied plays): as good {hit['all']} all / {hit['train']} train / {hit['held']} HELD of 2,000")

print("\n===== (ii) THE RAISE, CUT BY WHAT IT SITS ON (the size-first ⭐; the 11/17 rule's raise) - the ADDED units")
SF = B.pick(B.size_first)
raised = [r for r in SF.values() if star_u(r) > r["u0"]]
sub2 = [r for r in B.NL if r["u0"] < 2]
half_plays = [r for r in B.NL if r["u0"] < 1]


def add_line(nm, rs, pool):
    rs_nl = [r for r in rs if half(r["date"]) != "live"]
    adds = [star_u(r) - r["u0"] for r in rs_nl]
    o = {}
    for h in ("train", "held"):
        x = [(r, a) for r, a in zip(rs_nl, adds) if half(r["date"]) == h]
        o[h] = (sum(a * B.flat(r) for r, a in x), sum(a for _, a in x), len(x), sum(r["result"] == "won" for r, _ in x))
    w1 = sum(a * B.D.flat(r, 1.0) for r, a in zip(rs_nl, adds))
    mine = o["train"][0] + o["held"][0]
    fl = [B.flat(r) for r in pool]
    rnd = random.Random(1122)
    hit = sum(1 for _ in range(2000) if sum(a * b for a, b in zip(adds, rnd.sample(fl, len(adds)))) >= mine) if len(pool) > len(adds) else -1
    seas = {}
    for r, a in zip(rs_nl, adds):
        seas[B.season(r["date"])] = seas.get(B.season(r["date"]), 0.0) + a * B.flat(r)
    lv = [r for r in rs if half(r["date"]) == "live"]
    print(f"  {nm:60s} {len(rs_nl):3d} plays | the added units {mine:+6.1f}u on {sum(adds):5.1f}u ({M.roi(mine, sum(adds)):+5.1f}%)"
          f" | train {o['train'][3]}-{o['train'][2] - o['train'][3]} {o['train'][0]:+5.1f}u ({M.roi(o['train'][0], o['train'][1]):+5.1f}%)"
          f" | HELD {o['held'][3]}-{o['held'][2] - o['held'][3]} {o['held'][0]:+5.1f}u ({M.roi(o['held'][0], o['held'][1]):+5.1f}%)"
          f" | 1pt worse {M.roi(w1, sum(adds)):+5.1f}% | seasons up {sum(v > 0 for v in seas.values())}/{len(seas)}"
          f" | placebo {hit} of 2,000 | replay-live {sum(r['result'] == 'won' for r in lv)}-{sum(r['result'] != 'won' for r in lv)}")


add_line("THE WHOLE RAISE", raised, sub2)
add_line("a ½u play raised to 1u (vs a random ½u play)", [r for r in raised if star_u(r) == 1.0], half_plays)
add_line("   ... a ½u FAVORITE value play", [r for r in raised if star_u(r) == 1.0 and r["odds"] < 0], half_plays)
add_line("   ... a ½u hockey favorite value play", [r for r in raised if star_u(r) == 1.0 and r["odds"] < 0 and r["league"] == "nhl"], half_plays)
add_line("   ... a ½u dog (floor / NBA floor / long Dog / runner-up)", [r for r in raised if star_u(r) == 1.0 and r["odds"] >= 100], half_plays)
add_line("   ... the edge under 3 points (thin)", [r for r in raised if star_u(r) == 1.0 and M.margin(r) < 3], half_plays)
add_line("   ... the edge 3+ points", [r for r in raised if star_u(r) == 1.0 and M.margin(r) >= 3], half_plays)
add_line("a play raised to 2u (the 11/17 rule; vs a random play under 2u)", [r for r in raised if star_u(r) == 2.0], sub2)
add_line("   ... a 1u play to 2u", [r for r in raised if star_u(r) == 2.0 and r["u0"] == 1.0], sub2)
add_line("   ... a ½u Lock / Dog to 2u", [r for r in raised if star_u(r) == 2.0 and r["u0"] < 1.0], sub2)
print("   (kind-first, as it ran 11/4 -> 11/21:)")
KF = B.pick(B.kind_first)
rk = [r for r in KF.values() if star_u(r) > r["u0"]]
add_line("THE WHOLE RAISE, kind-first", rk, sub2)
add_line("a ½u play raised to 1u, kind-first", [r for r in rk if star_u(r) == 1.0], half_plays)
add_line("a play raised to 2u, kind-first", [r for r in rk if star_u(r) == 2.0], sub2)

print("\n===== (iii) THE ⭐ SMALLER THAN ANOTHER PLAY ON THE BOARD (the owner: never)")
for cname, star in (("kind-first, the raise in", KF), ("size-first, the raise in (11/22)", SF)):
    bad = [d for d, r in star.items() if len(B.ALL[d]) > 1 and max(x["u0"] for x in B.ALL[d] if x is not r) > star_u(r) + 1e-9]
    nl = [d for d in bad if half(d) != "live"]
    print(f"   {cname}: {len(nl)} of {len([d for d in star if half(d) != 'live'])} ⭐ days (train + held), {len(bad) - len(nl)} live")
    print(B.line("      those ⭐s", [star[d] for d in bad]))
    print(B.line("      the bigger play beside them", [max((x for x in B.ALL[d] if x is not star[d]), key=lambda x: x["u0"]) for d in bad]))
sfl = {d: r for d, r in SF.items()}
bad = [d for d, r in sfl.items() if len(B.ALL[d]) > 1 and max(x["u0"] for x in B.ALL[d] if x is not r) > r["u0"] + 1e-9]
print(f"   size-first, NO raise (a label): {len([d for d in bad if half(d) != 'live'])} ⭐ days smaller than another play (the biggest play is outside the pool)")
why = {}
for d in bad:
    big = max((x for x in B.ALL[d] if x is not sfl[d]), key=lambda x: x["u0"])
    k = ("fighting" if big.get("fighting") else "the read under the price" if M.margin(big) <= 0 else "the NFL Lock" if big["kind"] == "lock" else "past -150 / +350")
    why[k] = why.get(k, 0) + 1
print("      why the biggest play can't carry the ⭐:", why)

print("\n===== (iv) THE BOARD UNDER EACH PLAN (units a year, the worst stretch)")


def never_smaller(star, raise_of):
    """drop the ⭐ on a day another play on the board is bigger than the ⭐ would be"""
    return {d: r for d, r in star.items() if not (len(B.ALL[d]) > 1 and max(x["u0"] for x in B.ALL[d] if x is not r) > max(r["u0"], raise_of(r)) + 1e-9)}


def R2(r):
    return 2.0 if wired2(r) == 2.0 else 0.0


PLANS = [
    ("kind-first + the 11/17 raise (11/17 -> 11/21)", KF, wired2),
    ("size-first + the 11/17 raise (11/22, as wired)", SF, wired2),
    ("size-first + the 11/17 raise, no ⭐ under a bigger play", never_smaller(SF, wired2), wired2),
    ("size-first, 1u at least (no 2u raise)", SF, lambda r: 1.0),
    ("size-first, the 2u raise only (a ½u ⭐ stays ½u)", SF, lambda r: 2.0 if wired2(r) == 2.0 else 0.0),
    ("size-first, 1u at least on a DOG only + the 2u raise", SF, lambda r: wired2(r) if (wired2(r) == 2.0 or r["odds"] >= 100) else 0.0),
    ("size-first, A LABEL (no raise)", SF, lambda r: 0.0),
    ("size-first, A LABEL, no ⭐ under a bigger play", never_smaller(SF, lambda r: 0.0), lambda r: 0.0),
    ("WIRED 11/24: size-first, the 2u raise only, no ⭐ under a bigger play", never_smaller(SF, R2), R2),
]
base = B.board(SF, lambda r: 0.0)
for nm, star, rz in PLANS:
    o = B.board(star, rz)
    print(B.brow(nm, o, base, w=58))
    print(B.line("      its ⭐s at the units they carry", list(star.values()), lambda r, rz=rz: max(r["u0"], rz(r))) + f" | ⭐ days {len([d for d in star if half(d) != 'live'])}")
print("\n   what the ⭐ looks like (size-first, train + held): its own size before the raise")
from collections import Counter  # noqa: E402
c = Counter(r["u0"] for r in SF.values() if half(r["date"]) != "live")
print("     ", ", ".join(f"{u:g}u: {n} days" for u, n in sorted(c.items())))
c2 = Counter(len(B.ALL[d]) for d in SF if half(d) != "live")
print("      unit plays on a ⭐ day:", ", ".join(f"{k}: {n}" for k, n in sorted(c2.items())))

print("\n===== (v) THE WIRED PLAN'S ⭐ (11/24): the biggest play, the 2u raise only where the 11/17 cell earns it, none under a bigger play")
W = never_smaller(SF, R2)
gone = [SF[d] for d in SF if d not in W]
print(B.line("the ⭐ days it drops (a bigger play the ⭐ can't sit on is on the board): those ⭐s", gone, w=84))
print(B.line("   ... and the bigger play beside them", [max((x for x in B.ALL[r["date"]] if x is not r), key=lambda x: x["u0"]) for r in gone], w=84))
for nm, t in (("the ⭐ at 3u (the 💎 max play)", lambda r: max(r["u0"], R2(r)) >= 3), ("the ⭐ at 2u by its own size", lambda r: r["u0"] == 2),
              ("the ⭐ raised to 2u", lambda r: r["u0"] < 2 and R2(r) == 2), ("the ⭐ at 1u (its own size, no raise)", lambda r: r["u0"] == 1 and R2(r) < 2),
              ("the ⭐ at ½u (its own size - a thin day, no lift)", lambda r: r["u0"] < 1 and R2(r) < 2)):
    print(B.line(nm, [r for r in W.values() if t(r)], w=84))
