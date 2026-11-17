"""11/17 UNDERDOG EDGE - (5b) THE ROAD DOG AT A READ OF 3 ON THE SECOND REPLAY (R3 - funnel6.py: today's code, the engine's
own slot / fade / reason flags, the 2023-24 -> 2025-26 seasons only - the same GAMES as s5_cbb's held-out half, a
different build of the rows). What s5_cbb's cached rows could not say: how many read-3 road dogs carry one of the slot's
dog FADES (the slot never takes those) and how the ones without a fade did.
Usage: python results/studies/dogs_1117/s5b_cbb_r3.py > results/studies/dogs_1117/s5b_cbb_r3.out"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dlib as D  # noqa: E402

DOGS = [r for r in D.r3(dogs_only=True) if r["league"] == "ncaab"]
for r in DOGS:
    r["_t"] = "train"            # (every R3 college hoops season is a held-out season of the dog read's build)


def cell(name, rs):
    """R3's college hoops rows are all 2023-26: one line, by season"""
    from collections import defaultdict
    if not rs:
        print(f"  {name:64s} n    0")
        return
    seas = defaultdict(list)
    for r in rs:
        seas[D.season(r["date"])].append(D.flat(r))
    a = D.stat(rs)
    w1 = D.stat(rs, 1.0)
    print(f"  {name:64s} n {a['n']:4d} {a['w']:3d}-{a['n'] - a['w']:<4d} {a['wp']:4.1f}% (needs {a['bev']:4.1f}) {a['roi']:+6.1f}% z {a['z']:+5.2f}"
          f" | 1pt worse {w1['roi']:+6.1f}% | " + " ".join(f"{s}:{len(v)}/{100 * sum(v) / len(v):+.0f}%" for s, v in sorted(seas.items())))


def fade(r):
    x = r["x"]
    return bool(x.get("rubber_dog") or x.get("top_out") or x.get("ranked_road") or (x.get("ncaab_skid") or 0) >= 5)


road = lambda r: not r["home"] and not r.get("neutral")       # noqa: E731
home = lambda r: bool(r["home"]) and not r.get("neutral")     # noqa: E731
ok = lambda r: bool((r.get("read_parts") or {}).get("games_ok")) and r.get("dog_read") is not None   # noqa: E731
clears = lambda r: min(0.95, r["p_market"] + r["dog_read"] / 100) * r["dec"] - 1 > 0                 # noqa: E731
RD = [r for r in DOGS if ok(r) and r.get("p_market") is not None and clears(r)]
print(f"R3 college hoops dogs +100..+350: {len(DOGS)}; with a read, both teams 4+ games, the read clears the price: {len(RD)}; "
      f"{min(r['date'] for r in DOGS)} -> {max(r['date'] for r in DOGS)}")
cell("every college hoops dog (the vig)", DOGS)
print("-- the read x where grid (the home-dog -1 is IN the read on today's code)")
for lo, hi in ((2, 3), (3, 4), (4, 5), (5, 99)):
    for nm, fn in (("road", road), ("home", home), ("neutral", lambda r: bool(r.get("neutral")))):
        cell(f"read {lo}{'-' + str(hi) if hi < 99 else '+'} {nm}", [r for r in RD if lo <= r["dog_read"] < hi and fn(r)])
R3 = [r for r in RD if 3 <= r["dog_read"] < 4 and road(r)]
print("-- THE ROAD DOG AT A READ OF 3")
cell("every one", R3)
cell("   carries a dog fade (rubber match / top scorer out / top-25 road / 5+ skid) - never posts", [r for r in R3 if fade(r)])
cell("   NO fade (what the slot can take)", [r for r in R3 if not fade(r)])
cell("   no fade, waiting on news (never posts while it waits)", [r for r in R3 if not fade(r) and r.get("waiting")])
cell("   no fade, +100..+150", [r for r in R3 if not fade(r) and r["odds"] <= 150])
cell("   no fade, +151..+250", [r for r in R3 if not fade(r) and 150 < r["odds"] <= 250])
cell("   no fade, +251..+350", [r for r in R3 if not fade(r) and r["odds"] > 250])
cell("   no fade, a trap / a fought side", [r for r in R3 if not fade(r) and (r.get("trap") or r.get("fighting"))])
cell("   no fade, neither", [r for r in R3 if not fade(r) and not (r.get("trap") or r.get("fighting"))])
print("-- the slot's real picks on R3 (kind = ncaabplay; the road gate was OFF in this replay) and the read-4+ dogs")
cell("the dog slot's picks", [r for r in DOGS if r.get("kind") == "ncaabplay"])
cell("every read-4+ dog, no fade", [r for r in RD if r["dog_read"] >= 4 and not fade(r)])
cell("every read-4+ dog with a fade", [r for r in RD if r["dog_read"] >= 4 and fade(r)])
print(f"-- placebo: the no-fade road read-3 dogs vs a random same-size set of R3's road dogs: "
      f"{D.placebo([r for r in R3 if not fade(r)], [r for r in DOGS if road(r)])} of 2,000")
