"""11/17 MAX PROFIT - (2) THE BUNDLES, together on the same rows (the pieces interact through the ⭐). For each: units a
year, ROI, both halves, the worst stretch (x today's), the worst season, seasons up. THE RULE: the most units won, subject
to - up in both halves and every season, the worst stretch within today's x1.5, no bigger size on a group whose held-out
ROI is negative, and inside a bundle no piece whose ADDED units lose in the held-out half.
Usage: python results/studies/profit_1117/s2_bundles.py > results/studies/profit_1117/s2_bundles.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plib as L  # noqa: E402

M = L.M
t0 = L.sizes()
base = L.summ(t0)
NOFLOOR = [p for p in L.HALF_ALL if p != "floor"]
CLEAN = ["cfb_thin"]                                   # the ½u pieces that pass s1 on their own group + added units


def nofloor(r):
    return r["kind"] != "floor"


def star_dog_or_1u(r):                                 # THE WIRED ⭐ RULE: 2u on a play that is 1u+ by its own size
    return L.today0(r) >= 1.0


BUNDLES = [
    ("TODAY", dict()),
    ("A  every ½u at 1u (floor in)", dict(pieces=L.HALF_ALL)),
    ("B  every ½u at 1u but the floor", dict(pieces=NOFLOOR)),
    ("C  the runner-up 2u", dict(pieces=["ru2"])),
    ("D  the ⭐ 2u", dict(star=2.0)),
    ("E  the college football thin Lock 1u", dict(pieces=["cfb_thin"])),
    ("C+E", dict(pieces=["ru2", "cfb_thin"])),
    ("B+C", dict(pieces=NOFLOOR + ["ru2"])),
    ("B+C+D", dict(pieces=NOFLOOR + ["ru2"], star=2.0)),
    ("A+C+D  (everything)", dict(pieces=L.HALF_ALL + ["ru2"], star=2.0)),
    ("C+D", dict(pieces=["ru2"], star=2.0)),
    ("C+D+E", dict(pieces=["ru2", "cfb_thin"], star=2.0)),
    ("C+E + the ⭐ 2u, never on a floor play", dict(pieces=["ru2", "cfb_thin"], star=2.0, star_ok=nofloor)),
    ("C+E + the ⭐ 2u only on a play 1u+ by its own size", dict(pieces=["ru2", "cfb_thin"], star=2.0, star_from=1.0)),
    ("C+E + the ⭐ 1.5u", dict(pieces=["ru2", "cfb_thin"], star=1.5)),
    ("C+E + the NBA floor 1u", dict(pieces=["ru2", "cfb_thin", "nbafloor"])),
    ("C+E + the NBA floor 1u + the ⭐ 2u", dict(pieces=["ru2", "cfb_thin", "nbafloor"], star=2.0)),
    ("C+D+E + the NBA favorite play 2u + the read-4 slot dog 2u", dict(pieces=["ru2", "cfb_thin", "nbafav2", "cbb4_2"], star=2.0)),
]
print("===== THE BUNDLES (train + held; the live stretch apart)")
res = {}
for nm, kw in BUNDLES:
    sz = L.sizes(**kw)
    o = L.summ(sz)
    res[nm] = (sz, o, kw)
    ok = o["tr"] > 0 and o["he"] > 0 and o["up"] == o["ns"] and o["dd"] / base["dd"] <= 1.5
    print(L.row(nm, o, base if nm != "TODAY" else None) + (" | BAR ok" if ok else " | BAR FAILS"))
    print("        by season:", M.seas_str(o))


def pieces_of(nm, parts):
    """inside bundle nm: what each piece's ADDED units earn (the bundle vs the bundle without the piece)."""
    sz, o, kw = res[nm]
    print(f"\n===== INSIDE '{nm}': each piece's added units (the bundle vs the bundle without it)")
    for label, kw2 in parts:
        sz2 = L.sizes(**kw2)
        o2 = L.summ(sz2)
        print(f"   - {label:52s} " + L.added_str(L.added(sz2, sz)) + f" | the worst stretch without it {o2['dd']:+.1f}u")


pieces_of("B+C+D", [(L.PIECES[p][0][:52], dict(pieces=[q for q in NOFLOOR + ["ru2"] if q != p], star=2.0)) for p in NOFLOOR + ["ru2"]]
          + [("the ⭐ at 2u", dict(pieces=NOFLOOR + ["ru2"]))])
pieces_of("C+D+E", [("the runner-up 2u", dict(pieces=["cfb_thin"], star=2.0)), ("the college football thin Lock 1u", dict(pieces=["ru2"], star=2.0)),
                    ("the ⭐ at 2u", dict(pieces=["ru2", "cfb_thin"]))])

print("\n===== THE ⭐ AT 2u INSIDE C+D+E, BY THE KIND IT SITS ON (the added units; a group that loses held out gets no 2u)")
sz, o, kw = res["C+D+E"]
sz0 = L.sizes(pieces=["ru2", "cfb_thin"])
c = defaultdict(list)
for r in L.NL:
    if abs(sz[id(r)][1] - sz0[id(r)][1]) > 1e-9:
        c[L.k(r)].append(r)
for kk, x in sorted(c.items(), key=lambda kv: -len(kv[1])):
    a = L.added(sz0, sz, lambda r, kk=kk: L.k(r) == kk)
    print(f"   ⭐ on {kk:42s} " + L.added_str(a))
for label, test in (("⭐ on a FLOOR play", lambda r: r["kind"] == "floor"), ("⭐ on a play ½u by its own size", lambda r: L.today0(r) < 1.0),
                    ("⭐ on a play 1u+ by its own size", lambda r: L.today0(r) >= 1.0), ("⭐ on a favorite", lambda r: r["odds"] < 0), ("⭐ on a dog", lambda r: r["odds"] >= 100)):
    print(f"   {label:45s} " + L.added_str(L.added(sz0, sz, test)))

print("\n===== THE NBA FLOOR after the train half (held + the live-replay weeks): is a bigger size on a losing group?")
nf = [r for r in L.P if r["kind"] == "nbafloor"]
for label, rs in (("train", [r for r in nf if M.half(r["date"]) == "train"]), ("held", [r for r in nf if M.half(r["date"]) == "held"]),
                  ("live-replay (10/13 on)", [r for r in nf if M.half(r["date"]) == "live"]), ("held + live-replay", [r for r in nf if M.half(r["date"]) != "train"])):
    w = sum(r["result"] == "won" for r in rs)
    print(f"   {label:24s} {w}-{len(rs) - w} {100 * sum(M.flat(r) for r in rs) / max(1, len(rs)):+.1f}%")
for s in sorted({M.season(r["date"]) for r in nf}):
    rs = [r for r in nf if M.season(r["date"]) == s]
    w = sum(r["result"] == "won" for r in rs)
    print(f"      {s}: {w}-{len(rs) - w} {sum(M.flat(r) for r in rs):+.1f}u flat")
