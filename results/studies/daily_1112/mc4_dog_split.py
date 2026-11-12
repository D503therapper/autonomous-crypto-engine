"""11/12 DAILY - MC4: WHERE TODAY'S FOOTBALL CHECK LEAKS - FAVORITES vs DOGS, AND THE DOG HALF RE-BASED.
Rows: funnel3.py (old / new arms, every football board day 2023-10 -> 2026-11-10, closes, the whole board).
  1  every arm's football unit plays by side and half, flat AND at their own units (11/14 rules)
  2  what the honest dials drop / add, favorites and dogs apart
  3  THE WIRED RE-BASE: among the football dogs +100..+350 today's own-read rule passes (OLD reads), the HONEST weighed
     read - the close + the dog score's STUDY part (the old score minus its own-read term, as sports.weighed_dog_beats
     reads it live) - over the real price: keeps vs drops; the same on the board's Dogs; agreement with the new rows'
     honest score
train = to 2025-06-30, held = after; 2026 = the current season.
Usage: python results/studies/daily_1112/mc4_dog_split.py > results/studies/daily_1112/mc4_dog_split.out"""
import os
import mclib as M
D = M.D

NEW = {M.key(r): r for r in M.load(os.path.join(M.MINE, "new"))}
OLD = {M.key(r): r for r in M.load(os.path.join(M.MINE, "old"))}
OWN_CAP, OWN_TRAP = 12, ("nfl", "nba")


def on(r, arm):
    k = r.get("k_" + arm)
    return bool(k) and not (k == "dogplay" and r["league"] == "ncaaf")       # (11/13: no college runner-up dog)


def line(name, rs, arm):
    n, w, roi, z = D.bet(rs)
    uw = sum((r.get("u_" + arm) or 0) * ((r["dec"] - 1) if r["y"] else -1) for r in rs)
    uk = sum(r.get("u_" + arm) or 0 for r in rs)
    tr = D.bet([r for r in rs if r["half"] == "train"])
    he = D.bet([r for r in rs if r["half"] == "held"])
    nw = D.bet([r for r in rs if r["date"] >= "2026-07-01"])
    print(f"  {name:50s} {w:3d}-{n - w:<3d} flat {roi:+6.1f}% z {z:+5.2f} | units {uw:+5.1f}u on {uk:5.1f}u | train {tr[1]}-{tr[0] - tr[1]} {tr[2]:+6.1f}% "
          f"| held {he[1]}-{he[0] - he[1]} {he[2]:+6.1f}% | 2026 {nw[1]}-{nw[0] - nw[1]} {nw[2]:+6.1f}%")


print("1. EVERY ARM BY SIDE (football unit plays, the 11/14 rules)")
for arm, src in (("old", OLD), ("hon", NEW), ("wt", NEW), ("wtf", NEW), ("wtd", NEW)):
    rs = [r for r in src.values() if on(r, arm)]
    print(f" -- {arm}")
    line("all", rs, arm)
    line("favorites", [r for r in rs if r["odds"] < 0], arm)
    line("dogs", [r for r in rs if r["odds"] > 0], arm)

print("\n2. WHAT THE HONEST DIALS DROP / ADD (against today's arm)")
for arm in ("hon", "wt"):
    for side, sel in (("favorites", lambda r: r["odds"] < 0), ("dogs", lambda r: r["odds"] > 0)):
        o = {k for k, r in OLD.items() if on(r, "old") and sel(r)}
        n = {k for k, r in NEW.items() if on(r, arm) and sel(r)}
        print(f" -- {arm} {side}")
        line("today's only (dropped)", [OLD[k] for k in o - n], "old")
        line("both", [NEW[k] for k in o & n], arm)
        line("honest only (added)", [NEW[k] for k in n - o], arm)


def base(o):
    sc = (((o["edge_own"] + 1) / o["dec"]) - o["p_market"]) * 100
    if sc > OWN_CAP:
        sc = 0.0 if o["league"] in OWN_TRAP else OWN_CAP
    return sc


def honest_old(o):
    """sports.weighed_dog_beats on the OLD row: the close + (the whole score - its own-read term) over the price."""
    return (o["p_market"] + (o["dog_score"] - base(o)) / 100) * o["dec"] > 1


def honest_new(n):
    return (n["p_market"] + n["dog_score"] / 100) * n["dec"] > 1


print("\n3. THE WIRED RE-BASE - the dogs today's own-read rule passes, split by the honest weighed read")
GATE = {"nfl": 8.0, "ncaaf": 4.0}
dogs = [o for o in OLD.values() if 100 <= o["odds"] <= 350 and not o["trap"] and o.get("edge_own") is not None
        and o["edge_own"] > 0 and o.get("dog_score") is not None]
both = [o for o in dogs if M.key(o) in NEW and NEW[M.key(o)].get("dog_score") is not None]
print(f"  {len(dogs)} dogs; the old-row version agrees with the new rows' honest score on {sum(honest_old(o) == honest_new(NEW[M.key(o)]) for o in both)} of {len(both)}")
for lg in ("ncaaf", "nfl", None):
    x = [o for o in dogs if lg is None or o["league"] == lg]
    print(f" -- {(lg or 'both').upper()}")
    line("own read over the price (today's rule)", x, "old")
    line("  + the studies over the price: KEEPS", [o for o in x if honest_old(o)], "old")
    line("  + the studies under the price: DROPS", [o for o in x if not honest_old(o)], "old")
    g = [o for o in x if o["dog_score"] >= GATE[o["league"]]]
    line("  at the Dog gate (today's Dog pool)", g, "old")
    line("    KEEPS", [o for o in g if honest_old(o)], "old")
    line("    DROPS", [o for o in g if not honest_old(o)], "old")
    for lo, hi in ((0, 2), (2, 4), (4, 99)):
        line(f"  KEEPS with the study part {lo}..{hi} over the vig line", [o for o in x if honest_old(o) and lo <= (o["p_market"] + (o["dog_score"] - base(o)) / 100 - 1 / o["dec"]) * 100 < hi], "old")
bd = [o for o in OLD.values() if on(o, "old") and o["odds"] > 0]
print(" -- the board's football dogs (today's arm)")
line("KEEPS", [o for o in bd if honest_old(o)], "old")
line("DROPS", [o for o in bd if not honest_old(o)], "old")
print("\n4. PLACEBO for the split: the same 416 dogs, the KEEP label shuffled within each season (2,000 draws) - how often"
      " does a random keep / drop split open a gap as wide as the real one?")
import random  # noqa: E402
random.seed(1112)
lab = [honest_old(o) for o in dogs]
real = D.bet([o for o, k in zip(dogs, lab) if k])[2] - D.bet([o for o, k in zip(dogs, lab) if not k])[2]
by = {}
for i, o in enumerate(dogs):
    by.setdefault(o["season"], []).append(i)
hits = 0
for _ in range(2000):
    sh = lab[:]
    for idx in by.values():
        v = [lab[i] for i in idx]
        random.shuffle(v)
        for i, x in zip(idx, v):
            sh[i] = x
    gap = D.bet([o for o, k in zip(dogs, sh) if k])[2] - D.bet([o for o, k in zip(dogs, sh) if not k])[2]
    hits += gap >= real
print(f"  the real gap {real:+.1f} points; a random split matched it {hits} of 2000 (p {hits / 2000:.3f})")
print("~100 cells in this file (sections 1-3); ~350 across mc1-mc4 - about 18 would clear |z| 2 by luck.")
