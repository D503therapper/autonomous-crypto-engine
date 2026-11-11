"""S9b - is THE FLIP about crossing pick'em, or only about the size of the move? Every football side that closes
-101..-150, by how far the market moved TO it from the first fair number (no-vig points), split by whether it crossed
50% (a dog at the first fair) or was a favorite all week; the same for the +100..+150 closing dogs by how far the
market moved AWAY. Also a placebo: 500 random draws of 309 favorites from the all-week favorites with the same
move-size mix - how often do they lose as much as the crossers?"""
import random

import lib

rows = []
for LG in ("nfl", "ncaaf"):
    fin = {g["id"]: g for g in lib.finals(LG)}
    for x in lib.load_football(LG):
        g = fin.get(x["id"])
        if not g or g["stype"] != "2":
            continue
        f = lib.first_fair(x["ml"])
        if not f:
            continue
        _, _, p0 = lib.ml_med(f[1])
        hc, ac = lib.dec(g["mlh"]), lib.dec(g["mla"])
        pc = (1 / hc) / (1 / hc + 1 / ac)
        for side, team, opp, o, won, home in lib.sides(g):
            pf = p0 if home else 1 - p0
            pcl = pc if home else 1 - pc
            rows.append(dict(lg=LG, s=g["season"], o=o, won=won, pf=pf, pc=pcl, mv=(pcl - pf) * 100,
                             pl=lib.profit(won, lib.dec(o)), a=lib.ats(g, side)))

cells = lib.Cells()


def mvband(m):
    return "toward 6+" if m >= 6 else "toward 4-6" if m >= 4 else "toward 2-4" if m >= 2 else \
        "toward 0-2" if m >= 0 else "away 0-2" if m > -2 else "away 2-4" if m > -4 else "away 4+"


for r in rows:
    if -150 <= r["o"] <= -101:
        cr = "CROSSED (dog at the first fair)" if r["pf"] < 0.5 else "fav all week"
        cells.add(f"close fav -101..-150 | {cr} | {mvband(r['mv'])} | ML", r["s"], r["pl"])
        cells.add(f"close fav -101..-150 | {cr} | ALL | ML", r["s"], r["pl"])
    if 100 <= r["o"] <= 150:
        cr = "CROSSED (fav at the first fair)" if r["pf"] > 0.5 else "dog all week"
        cells.add(f"close dog +100..+150 | {cr} | {mvband(r['mv'])} | ML", r["s"], r["pl"])
res = cells.dump("s9b", "S9b - the flip vs the move size (close favorites -101..-150 / dogs +100..+150); TRAIN 2020-22",
                 (2020, 2022), (2023, 2024, 2025, 2026))

# placebo: match the crossers' move-size mix from the all-week favorites
cross = [r for r in rows if -150 <= r["o"] <= -101 and r["pf"] < 0.5]
stay = [r for r in rows if -150 <= r["o"] <= -101 and r["pf"] >= 0.5]
roi = sum(r["pl"] for r in cross) / len(cross)
by = {}
for r in stay:
    by.setdefault(mvband(r["mv"]), []).append(r)
need = {}
for r in cross:
    need[mvband(r["mv"])] = need.get(mvband(r["mv"]), 0) + 1
random.seed(1111)
worse, sims = 0, 500
for _ in range(sims):
    pick = []
    for b, n in need.items():
        pool = by.get(b) or stay
        pick += [random.choice(pool) for _ in range(n)]
    if sum(r["pl"] for r in pick) / len(pick) <= roi:
        worse += 1
print(f"crossers {len(cross)} ROI {roi*100:+.1f}%; move-size mix {need}; placebo draws as bad: {worse}/{sims}")
open(lib.os.path.join(lib.OUT, "s9b_out.txt"), "a").write(
    f"\nPLACEBO: crossers {len(cross)} ROI {roi*100:+.1f}%; move-size mix {need}; all-week favorites matched on the move "
    f"size, {sims} draws: {worse} as bad\n")
