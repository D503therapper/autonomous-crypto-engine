"""11/17 UNDERDOG EDGE - (8) WHICH GATED DOG IS THE DOG? (R3 - funnel6.py, today's code, 2023-10 -> 2026-11)
The Dog of the Day is the gated dog with the BEST dog score; the runner-up dog play (hockey / NFL) is the next one. The
score = the own read's term (the own read over the no-vig close, points, capped) + the study part (the weighed angles,
capped at 6). Four studies now say a bigger own-read margin is not a better bet. So: among the day's gated dogs, does
the top score win more than the second? Is it the own-read term or the study part that sorts them? What would the Dog
have done picked another way (the best study part; the smallest own-read term; the shortest price)?
Usage: python results/studies/dogs_1117/s8_rank.py > results/studies/dogs_1117/s8_rank.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dlib as D  # noqa: E402

DOGS = D.r3(dogs_only=True)
sc = lambda r: r["dog_score"] if r.get("dog_score") is not None else -99   # noqa: E731
base = lambda r: r.get("dog_base") or 0.0                                   # noqa: E731
study = lambda r: sc(r) - base(r)                                           # noqa: E731

for lg in ("nhl", "nba", "ncaaf", "nfl"):
    d = [r for r in DOGS if r["league"] == lg]
    gated = [r for r in d if r.get("dog_gate") and r.get("n_reasons2") and not r.get("waiting")]
    print(f"\n===== {lg}: {len(gated)} gated dogs (the Dog gate, a named reason, not waiting) of {len(d)}")
    if len(gated) < 30:
        continue
    D.cell("every gated dog", gated)
    print(f"        placebo vs every {lg} dog: {D.placebo(gated, d)}")
    D.cell("   posted as the Dog of the Day", [r for r in gated if r.get("kind") == "dog"])
    D.cell("   posted as the runner-up dog play", [r for r in gated if r.get("kind") == "dogplay"])
    D.cell("   posted as anything else", [r for r in gated if r.get("kind") not in (None, "dog", "dogplay")])
    D.cell("   not posted", [r for r in gated if not r.get("kind")])
    print("   -- by the whole score")
    qs = sorted(sc(r) for r in gated)
    for lo, hi in ((0, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (10, 99)):
        D.cell(f"   score {lo}..{hi}", [r for r in gated if lo <= sc(r) < hi])
    print("   -- by the OWN-READ term (the own read over the no-vig close, points)")
    for lo, hi in ((-99, 0), (0, 1), (1, 2), (2, 3), (3, 5), (5, 99)):
        c = [r for r in gated if lo <= base(r) < hi]
        D.cell(f"   own-read term {lo}..{hi}", c)
        if 15 <= len(c) < len(gated):
            print(f"        placebo vs the gated: as good {D.placebo(c, gated)} / as bad {D.placebo_lo(c, gated)}")
    print("   -- by the STUDY part")
    for lo, hi in ((-99, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7)):
        c = [r for r in gated if lo <= study(r) < hi]
        D.cell(f"   study part {lo}..{hi}", c)
        if 15 <= len(c) < len(gated):
            print(f"        placebo vs the gated: as good {D.placebo(c, gated)} / as bad {D.placebo_lo(c, gated)}")
    print("   -- the day's gated dogs, ranked (one game each)")
    by = defaultdict(list)
    for r in gated:
        by[r["date"]].append(r)
    for k in (1, 2, 3):
        D.cell(f"   #{k} by the whole score", [sorted(v, key=lambda r: -sc(r))[k - 1] for v in by.values() if len(v) >= k])
    multi = {dd: v for dd, v in by.items() if len(v) >= 2}
    print(f"   -- days with 2+ gated dogs ({len(multi)}): which one should be the Dog?")
    for nm, key in (("the best whole score (today)", lambda r: -sc(r)), ("the best STUDY part", lambda r: (-study(r), -sc(r))),
                    ("the SMALLEST own-read term", lambda r: (base(r), -sc(r))), ("the biggest own-read term", lambda r: (-base(r), -sc(r))),
                    ("the shortest price", lambda r: r["odds"]), ("the longest price", lambda r: -r["odds"])):
        pick = [sorted(v, key=key)[0] for v in multi.values()]
        rest = [x for v in multi.values() for x in sorted(v, key=key)[1:]]
        D.cell(f"   pick: {nm}", pick)
        D.cell("       ... the rest that day", rest)
    print("   -- the Dog as posted vs the runner-up as posted, the days BOTH posted")
    both = [dd for dd in by if any(r.get("kind") == "dog" for r in by[dd]) and any(r.get("kind") == "dogplay" for r in by[dd])]
    D.cell("   the Dog (days with a runner-up)", [r for dd in both for r in by[dd] if r.get("kind") == "dog"])
    D.cell("   the runner-up (same days)", [r for dd in both for r in by[dd] if r.get("kind") == "dogplay"])
    dg = [r for r in gated if r.get("kind") == "dog"]
    rp = [r for r in gated if r.get("kind") == "dogplay"]
    if dg and rp:
        av = lambda rs, f: sum(f(r) for r in rs) / len(rs)   # noqa: E731
        print(f"        the Dog: avg score {av(dg, sc):.2f}, own-read term {av(dg, base):.2f}, study {av(dg, study):.2f}, price {av(dg, lambda r: r['odds']):.0f}, home {100 * av(dg, lambda r: bool(r['home'])):.0f}%")
        print(f"        the runner-up: avg score {av(rp, sc):.2f}, own-read term {av(rp, base):.2f}, study {av(rp, study):.2f}, price {av(rp, lambda r: r['odds']):.0f}, home {100 * av(rp, lambda r: bool(r['home'])):.0f}%")
        print(f"        placebo: the runner-up plays vs a random same-size set of the gated: {D.placebo(rp, gated)}; the Dogs as BAD as a random set: {D.placebo_lo(dg, gated)}")
    if lg == "nhl":
        print("   -- hockey: the b2b spot (rested vs a favorite that played last night) inside the gated")
        b = [r for r in gated if r["x"].get("rested_vs_b2b")]
        D.cell("   gated, on the b2b spot", b)
        D.cell("   gated, not on it", [r for r in gated if not r["x"].get("rested_vs_b2b")])
        D.cell("   gated, the b2b spot, 8+", [r for r in b if sc(r) >= 8])
        D.cell("   gated, home", [r for r in gated if r["home"]])
        D.cell("   gated, road", [r for r in gated if not r["home"]])
        for bnd in D.BANDS:
            D.cell(f"   gated, {bnd}", [r for r in gated if D.band(r) == bnd])
