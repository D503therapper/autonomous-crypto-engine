"""11/17 MAX PROFIT - (3) THE ⭐ AT 2u, cut the a-priori ways (standing rules, not records picked off this board): never
on a floor play (the floor is never sized up), never on a dog past +150 (the 10/30 price split: the long dog is the ½u
dog), never on a thin edge (the read under 3 points over the price - the owner's 10/23 thin-edge rule). All on top of
C+E (the runner-up 2u, the college football thin Lock 1u). Then the placebo for the wired rule: the same 1u dealt to a
random same-size set of the day-best candidates.
Usage: python results/studies/profit_1117/s3_star.py > results/studies/profit_1117/s3_star.out"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plib as L  # noqa: E402

M = L.M
t0 = L.sizes()
base = L.summ(t0)
CE = ["ru2", "cfb_thin"]
sz0 = L.sizes(pieces=CE)
o0 = L.summ(sz0)
print(L.row("TODAY", base))
print(L.row("C+E, the ⭐ 1u at least (as today)", o0, base))


def nofloor(r):
    return r["kind"] != "floor"


def short(r):
    return r["odds"] <= 150


def real(r):
    return M.margin(r) >= 3.0


VARS = [
    ("⭐ 2u always", None),
    ("⭐ 2u, never a floor play", nofloor),
    ("⭐ 2u, never a floor play / a dog past +150", lambda r: nofloor(r) and short(r)),
    ("⭐ 2u, never floor / past +150 / a thin edge (<3)", lambda r: nofloor(r) and short(r) and real(r)),
    ("⭐ 2u, never a thin edge (<3)", real),
    ("⭐ 2u, only a thin edge (<3)  [the mirror]", lambda r: not real(r)),
    ("⭐ 2u, only a dog past +150  [the mirror]", lambda r: not short(r)),
    ("⭐ 2u, favorites only", lambda r: r["odds"] < 0),
    ("⭐ 2u, never a hockey favorite value play", lambda r: not (r["kind"] == "play" and r["league"] == "nhl")),
    ("⭐ 2u, never floor / past +150 / hockey fav value play", lambda r: nofloor(r) and short(r) and not (r["kind"] == "play" and r["league"] == "nhl")),
]
out = {}
for nm, ok in VARS:
    sz = L.sizes(pieces=CE, star=2.0, star_ok=ok)
    o = L.summ(sz)
    out[nm] = sz
    print(L.row(nm, o, base))
    print("        " + L.added_str(L.added(sz0, sz)) + " | by season: " + M.seas_str(o))

print("\n===== the thin / real split of the ⭐ (flat, every ⭐ whose own size is under 2u)")
st = [r for r in L.NL if sz0[id(r)][2] and sz0[id(r)][1] < 2]


def f(x):
    w = sum(r["result"] == "won" for r in x)
    return f"{len(x):4d} {w}-{len(x) - w} {100 * sum(M.flat(r) for r in x) / max(1, len(x)):+6.1f}%"


for label, t in (("edge under 3", lambda r: not real(r)), ("edge 3-6", lambda r: 3 <= M.margin(r) < 6), ("edge 6+", lambda r: M.margin(r) >= 6),
                 ("dog past +150", lambda r: not short(r)), ("+150 or shorter", short), ("floor play", lambda r: not nofloor(r))):
    x = [r for r in st if t(r)]
    print(f"   {label:18s} {f(x)} | train {f([r for r in x if M.half(r['date']) == 'train'])} | HELD OUT {f([r for r in x if M.half(r['date']) == 'held'])}")

print("\n===== THE PLACEBO: the ⭐'s extra unit dealt to a random same-size set of every unit play under 2u (2,000 deals, five seeds)")
pool = [r for r in L.NL if sz0[id(r)][1] < 2]
fl = [M.flat(r) for r in pool]
for nm in ("⭐ 2u always", "⭐ 2u, never a floor play / a dog past +150", "⭐ 2u, never floor / past +150 / a thin edge (<3)"):
    sz = out[nm]
    ch = [r for r in L.NL if abs(sz[id(r)][1] - sz0[id(r)][1]) > 1e-9]
    mine = sum((sz[id(r)][1] - sz0[id(r)][1]) * M.flat(r) for r in ch)
    hits = []
    for seed in (1117, 1, 2, 3, 4):
        rnd = random.Random(seed)
        hits.append(sum(1 for _ in range(2000) if sum(rnd.sample(fl, len(ch))) >= mine))
    print(f"   {nm:52s} {len(ch)} plays {mine:+.1f}u: as good {hits} of 2,000")

print("\n===== THE WIRED ⭐ RULE (sports.best_2u_ok): 2u on a Lock / a Dog of the Day / a play 1u+ by its own size, at +150 or shorter")
print("      (so never on a ½u value play, a floor play, the college hoops favorite slot, a dog past +150 - those stay 1u at least)")


def wired(r):
    return r["odds"] <= 150 and (r["kind"] in ("lock", "dog") or sz0[id(r)][0] >= 1.0)


sz = L.sizes(pieces=CE, star=2.0, star_ok=wired)
o = L.summ(sz)
print(L.row("C+E + the ⭐ 2u (wired rule)", o, base))
print("        " + L.added_str(L.added(sz0, sz)) + " | by season: " + M.seas_str(o))
c = {}
for r in L.NL:
    if abs(sz[id(r)][1] - sz0[id(r)][1]) > 1e-9:
        c.setdefault(L.k(r), []).append(r)
for kk, x in sorted(c.items(), key=lambda kv: -len(kv[1])):
    print(f"   ⭐ 2u on {kk:42s} " + L.added_str(L.added(sz0, sz, lambda r, kk=kk: L.k(r) == kk)))
ch = [r for r in L.NL if abs(sz[id(r)][1] - sz0[id(r)][1]) > 1e-9]
mine = sum((sz[id(r)][1] - sz0[id(r)][1]) * M.flat(r) for r in ch)
for pname, pl in (("every unit play under 2u", pool), ("every ⭐ under 2u", st)):
    fl2 = [M.flat(r) for r in pl]
    hits = []
    for seed in (1117, 1, 2, 3, 4):
        rnd = random.Random(seed)
        hits.append(sum(1 for _ in range(2000) if sum(rnd.sample(fl2, len(ch))) >= mine))
    print(f"   placebo - the extra unit dealt to a random {len(ch)} of {pname} ({len(pl)}): as good {hits} of 2,000")
left = [r for r in st if not wired(r)]
print(f"   LEFT AT 1u (the ⭐ on a ½u value play / floor play / long dog): {f(left)} | train {f([r for r in left if M.half(r['date']) == 'train'])} | HELD OUT {f([r for r in left if M.half(r['date']) == 'held'])}")
