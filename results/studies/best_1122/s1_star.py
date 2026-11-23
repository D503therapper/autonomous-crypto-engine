"""11/22 - WHY THE ⭐ HAS LOST - (1) on the replay board: (a) the ⭐ as it was chosen (kind-first) against the rest of the
board, with the placebo (a random play of the day's pool as the ⭐, 2,000 times); (b) what the ⭐'s RAISE earns; (c) the
11/22 choice (the biggest, then the bigger edge) against kind-first; (d) every other way to choose it.
Usage: python results/studies/best_1122/s1_star.py > results/studies/best_1122/s1_star.out"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blib as B  # noqa: E402

M = B.M
half = B.half
n_days = len([d for d in B.DAYS if half(d) != "live"])
n_pool = len([d for d in B.DAYS if half(d) != "live" and B.POOL.get(d)])
n_multi = len([d for d in B.DAYS if half(d) != "live" and len(B.POOL.get(d) or []) >= 2])
print(f"THE BOARD: {len(B.NL)} unit plays on {n_days} board days with a unit play (train + held); a ⭐ pool on {n_pool}; 2+ plays to choose from on {n_multi}")
print(B.line("every unit play, flat 1u", B.P))
print(B.line("every unit play, at its own size", B.P, B.u0))
print(B.line("every play the ⭐ MAY sit on (the pool), flat", [r for d in B.DAYS for r in B.POOL.get(d) or []]))


def rest(star):
    ids = {id(r) for r in star.values()}
    return [r for r in B.P if id(r) not in ids]


def show(name, sel, placebo=True, pool_of=None):
    star = B.pick(sel, pool_of)
    rs = list(star.values())
    print(B.line("⭐ " + name, rs))
    if placebo:
        hit, mine, ex = B.placebo_star(rs, pool_of=pool_of)
        n = {h: len([r for r in rs if (half(r["date"]) == h if h != "all" else half(r["date"]) != "live")]) for h in ("all", "train", "held")}
        print(f"        placebo (a random pool play each day, 2,000 deals): as good {hit['all']} all / {hit['train']} train / {hit['held']} HELD"
              f" | a random pick expects {100 * ex['all'] / n['all']:+.1f}% ({100 * ex['train'] / max(1, n['train']):+.1f}% / {100 * ex['held'] / max(1, n['held']):+.1f}%)")
    return star


print("\n===== (a) THE ⭐ AS IT WAS CHOSEN - the kind first (the Lock, the Dog, the NBA favorite ...), then the size, then the edge")
KF = show("kind-first (11/4 -> 11/21)", B.kind_first)
print(B.line("the rest of the board (every non-⭐ unit play)", rest(KF)))
multi = {d: r for d, r in KF.items() if len(B.POOL[d]) >= 2}
print(B.line("⭐ kind-first, days with 2+ in the pool", list(multi.values())))
print(B.line("   the other pool plays those days", [r for d in multi for r in B.POOL[d] if r is not multi[d]]))
print("   the ⭐ by the kind it sat on (flat):")
for k, n in Counter(r["k"].rsplit(" (", 1)[0] for r in KF.values() if half(r["date"]) != "live").most_common():
    print(B.line("     " + k, [r for r in KF.values() if r["k"].rsplit(" (", 1)[0] == k], w=52))
print("   the ⭐ dogs / favorites, and by sport:")
print(B.line("     ⭐ dogs", [r for r in KF.values() if r["odds"] >= 100]))
print(B.line("     ⭐ favorites", [r for r in KF.values() if r["odds"] < 0]))
for lg in ("nhl", "nba", "nfl", "ncaaf", "ncaab"):
    print(B.line("     ⭐ " + lg, [r for r in KF.values() if r["league"] == lg]))

print("\n===== (c) THE 11/22 CHOICE - the biggest play, then the bigger edge")
SF = show("size-first, then the edge (11/22)", B.size_first)
print(B.line("the rest of the board", rest(SF)))
diff = [d for d in SF if SF[d] is not KF[d]]
print(f"   the two choices differ on {len([d for d in diff if half(d) != 'live'])} days:")
print(B.line("     size-first's pick those days", [SF[d] for d in diff]))
print(B.line("     kind-first's pick those days", [KF[d] for d in diff]))

print("\n===== (d) EVERY OTHER WAY TO CHOOSE IT (one ⭐ a day from the same pool; flat 1u)")
SELS = [
    ("the biggest edge on the read its units ride on", lambda r: -M.margin(r)),
    ("the most confident: the weighed read over the NO-VIG price", lambda r: -B.weighed_over_nv(r)),
    ("the biggest OWN-read edge", lambda r: -B.own_edge(r)),
    ("the surest (the highest win chance by the board's read)", lambda r: -M.read_of(r)),
    ("the shortest price", lambda r: r["odds"] if r["odds"] < 0 else r["odds"] + 1000),
    ("a favorite first, then the edge", lambda r: (r["odds"] >= 100, -M.margin(r))),
    ("a dog first, then the dog score", lambda r: (r["odds"] < 100, -(r.get("dog_score") or -99))),
    ("the best dog score, else the edge", lambda r: (-(r.get("dog_score") if r.get("dog_score") is not None and r["odds"] >= 100 else -50), -M.margin(r))),
    ("size-first, then the weighed read over the no-vig", lambda r: (-r["u0"], -B.weighed_over_nv(r))),
    ("size-first, then the OWN-read edge", lambda r: (-r["u0"], -B.own_edge(r))),
    ("size-first, then the surest", lambda r: (-r["u0"], -M.read_of(r))),
    ("size-first, then the shortest price", lambda r: (-r["u0"], r["odds"] if r["odds"] < 0 else r["odds"] + 1000)),
    ("size-first, then the kind", lambda r: (-r["u0"], M.RANK.get(r["kind"], 9), -M.margin(r))),
    ("the SMALLEST play first [the mirror]", lambda r: (r["u0"], -M.margin(r))),
    ("the smallest edge [the mirror]", lambda r: M.margin(r)),
]
for nm, sel in SELS:
    show(nm, sel)

print("\n===== (d2) A ⭐ ONLY ON A DAY A PLAY CLEARS A BAR (fewer ⭐s) - the size-first choice inside the bar")


def barred(test):
    return lambda d: [r for r in B.POOL.get(d) or [] if test(r)]


BARS = [
    ("both reads over the price (own + weighed)", lambda r: B.own_edge(r) > 0 and M.margin(r) > 0),
    ("the edge 3+ points (not thin)", lambda r: M.margin(r) >= 3),
    ("the edge 5+ points", lambda r: M.margin(r) >= 5),
    ("the weighed read 4+ over the no-vig", lambda r: B.weighed_over_nv(r) >= 4),
    ("the weighed read 6+ over the no-vig", lambda r: B.weighed_over_nv(r) >= 6),
    ("the play is 1u+ by its own size", lambda r: r["u0"] >= 1),
    ("the play is 2u+ by its own size", lambda r: r["u0"] >= 2),
    ("at +150 or shorter", lambda r: r["odds"] <= 150),
    ("1u+ by its own size AND +150 or shorter", lambda r: r["u0"] >= 1 and r["odds"] <= 150),
    ("2u+ by its own size AND +150 or shorter", lambda r: r["u0"] >= 2 and r["odds"] <= 150),
    ("never a floor play / an NBA floor dog", lambda r: r["kind"] not in ("floor", "nbafloor")),
    ("a Lock / a Dog of the Day only", lambda r: r["kind"] in ("lock", "dog")),
    ("under 1u by its own size [the mirror]", lambda r: r["u0"] < 1),
    ("a dog past +150 [the mirror]", lambda r: r["odds"] > 150),
]
for nm, t in BARS:
    star = show(nm, B.size_first, pool_of=barred(t))
    left = [B.SF_ALL[d] for d in B.DAYS if d not in star and d in B.SF_ALL] if hasattr(B, "SF_ALL") else [SF[d] for d in SF if d not in star]
    print(B.line("        the size-first ⭐ on the days this bar leaves with NO ⭐", left))

print("\n===== (b) THE RAISE - what the ⭐'s extra units earn (the board's money; the raise = the units over the play's own size)")


def wired2(r):
    return 2.0 if (r["odds"] <= 150 and (r["kind"] in ("lock", "dog") or r["u0"] >= 1.0)) else 1.0


RAISES = [
    ("NO RAISE - the ⭐ is a label", lambda r: 0.0),
    ("1u at least (11/4 -> 11/16)", lambda r: 1.0),
    ("2u on a Lock / Dog / 1u+ play at +150 or shorter, else 1u (11/17 on)", wired2),
    ("2u always", lambda r: 2.0),
    ("+1u on whatever it is", lambda r: r["u0"] + 1.0),
]
base = None
for cname, star in (("kind-first", KF), ("size-first (11/22)", SF)):
    print(f"   --- the ⭐ chosen {cname}")
    for nm, rz in RAISES:
        o = B.board(star, rz)
        if base is None:
            base = o
        print(B.brow(nm, o, base))
print("\n   the raise by what it sits on (the size-first ⭐, the 11/17 rule's raise), flat on the raised plays:")
rs = [r for r in SF.values() if wired2(r) > r["u0"]]
for nm, t in (("a ½u play raised to 1u (floor / NBA floor / value play / long dog)", lambda r: wired2(r) == 1.0),
              ("  ... a floor / NBA floor dog", lambda r: wired2(r) == 1.0 and r["kind"] in ("floor", "nbafloor")),
              ("  ... a ½u favorite value play", lambda r: wired2(r) == 1.0 and r["odds"] < 0),
              ("  ... a ½u dog past +150 (Dog / runner-up / slot)", lambda r: wired2(r) == 1.0 and r["odds"] > 150 and r["kind"] not in ("floor", "nbafloor")),
              ("a 1u play raised to 2u", lambda r: wired2(r) == 2.0 and r["u0"] == 1.0),
              ("a ½u Lock / Dog raised to 2u", lambda r: wired2(r) == 2.0 and r["u0"] < 1.0)):
    print(B.line("     " + nm, [r for r in rs if t(r)], w=66))
print("\n   placebo for the raise: the same added units dealt to a random same-size set of the unit plays under 2u (2,000 deals)")
import random  # noqa: E402
pool = [r for r in B.NL if r["u0"] < 2]
fl = [B.flat(r) for r in pool]
for cname, star in (("kind-first", KF), ("size-first", SF)):
    ch = [r for r in star.values() if half(r["date"]) != "live" and wired2(r) > r["u0"]]
    mine = sum((wired2(r) - r["u0"]) * B.flat(r) for r in ch)
    adds = [wired2(r) - r["u0"] for r in ch]
    rnd = random.Random(1122)
    hit = 0
    for _ in range(2000):
        smp = rnd.sample(fl, len(ch))
        hit += sum(a * b for a, b in zip(adds, smp)) >= mine
    print(f"     {cname}: {len(ch)} raised plays, the added units {mine:+.1f}u on {sum(adds):.1f}u - as good {hit} of 2,000")
