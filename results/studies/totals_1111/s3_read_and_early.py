"""S3 - THE BUILT PLAY vs THE BROTHER'S: does our points read earn its place at 4,600 ft, and what about the games
before both teams have 5 finals (November - where the built play can't fire and the brother's engine is betting now)?

The plain read = (home for + away against + away for + home against) / 2 on this season's finals before the tip
(what sports_early.alt_read uses, before its altitude bump). The EARLY read fills a team short of 5 games with last
season's scoring, shrunk: (n * this season + (5 - n) * last season) / 5 - last season alone at game 1."""
import statistics
from collections import defaultdict

import lib

G = [r for r in lib.load("ncaab") if (r.get("stype") or "2") in ("2", "3")]
acc = defaultdict(lambda: [0.0, 0.0, 0])          # (season, team) -> for, against, n  (walk-forward)
rows = []
for r in G:
    if r["hs"] is None:
        continue
    s = r["season"]
    h, a = acc[(s, r["home"])], acc[(s, r["away"])]
    hp, ap = acc.get((s - 1, r["home"])), acc.get((s - 1, r["away"]))

    def blend(cur, prev):
        if cur[2] >= 5:
            return cur[0] / cur[2], cur[1] / cur[2]
        if not prev or prev[2] < 10:
            return None
        k = cur[2]
        return ((cur[0] + (5 - k) * prev[0] / prev[2]) / 5, (cur[1] + (5 - k) * prev[1] / prev[2]) / 5)
    r["gp"] = (h[2], a[2])
    r["plain"] = ((h[0] / h[2] + a[1] / a[2] + a[0] / a[2] + h[1] / h[2]) / 2) if h[2] >= 5 and a[2] >= 5 else None
    bh, ba = blend(h, hp), blend(a, ap)
    r["early"] = (bh[0] + ba[1] + ba[0] + bh[1]) / 2 if bh and ba else None
    rows.append(r)
    h[0] += r["hs"]; h[1] += r["as"]; h[2] += 1
    a[0] += r["as"]; a[1] += r["hs"]; a[2] += 1
R = [r for r in rows if (r.get("stype") or "2") == "2" and not r["neu"] and r["el"] is not None]
P = [r for r in R if r["tot"] is not None]

print("== (a) PRICE-FREE: points scored minus the plain read (both 5+ games), TRAIN 2016-21 / BLIND 2022+, every final")
for lo, hi in ((0, 600), (600, 900), (900, 1220), (1220, 1400), (1400, 1600), (1600, 2000), (2000, 9999), (1400, 9999)):
    c = [r for r in R if r["plain"] is not None and lo <= r["el"] < hi]
    tr = [r["hs"] + r["as"] - r["plain"] for r in c if r["season"] <= lib.TRAIN_TO]
    bl = [r["hs"] + r["as"] - r["plain"] for r in c if r["season"] > lib.TRAIN_TO]
    cl = [r["tot"] - r["plain"] for r in c if r["tot"] is not None]
    print(f"   {lo:>4}-{hi:<5} m  train {statistics.mean(tr):+5.2f} (n{len(tr)})  blind {statistics.mean(bl):+5.2f} "
          f"(n{len(bl)})  | the closing total sits {statistics.mean(cl):+5.2f} vs the read (n{len(cl)})")
print("   the same for the EARLY read (a team under 5 games in, last season filling in):")
for lo, hi in ((0, 600), (1220, 1400), (1400, 9999)):
    c = [r for r in R if r["plain"] is None and r["early"] is not None and lo <= r["el"] < hi]
    tr = [r["hs"] + r["as"] - r["early"] for r in c if r["season"] <= lib.TRAIN_TO]
    bl = [r["hs"] + r["as"] - r["early"] for r in c if r["season"] > lib.TRAIN_TO]
    cl = [r["tot"] - r["early"] for r in c if r["tot"] is not None]
    print(f"   {lo:>4}-{hi:<5} m  train {statistics.mean(tr):+5.2f} (n{len(tr)})  blind {statistics.mean(bl):+5.2f} "
          f"(n{len(bl)})  | the closing total sits {statistics.mean(cl):+5.2f} vs the read (n{len(cl)})")

BUILT_ADJ = 1.46
print("\n== (b) THE BUILT PLAY (1,220 m+, both 5+, read + 1.46 two over the total) on this split")
built = [r for r in P if r["el"] >= 1220 and r["plain"] is not None and r["plain"] + BUILT_ADJ - r["tot"] >= 2]
lib.line("built rule OVER", built, "over")
lib.line("  ... of those, floor 1,220-1,399 m", [r for r in built if r["el"] < 1400], "over")
lib.line("  ... of those, floor 1,400 m+", [r for r in built if r["el"] >= 1400], "over")
miss_b = [r for r in P if r["el"] >= 1220 and r["plain"] is not None and r["plain"] + BUILT_ADJ - r["tot"] < 2]
lib.line("the built rule SKIPS (read short), 1,220-1,399 m", [r for r in miss_b if r["el"] < 1400], "over")
lib.line("the built rule SKIPS (read short), 1,400 m+", [r for r in miss_b if r["el"] >= 1400], "over")

print("\n== (c) 1,400 m+ (4,600 ft), both 5+ games: the over by the plain read's gap to the total")
hi = [r for r in P if r["el"] >= 1400 and r["plain"] is not None]
for lo, up in ((-99, -6), (-6, -3), (-3, 0), (0, 3), (3, 6), (6, 99), (-99, -3), (-3, 99), (-99, 0), (0, 99)):
    lib.line(f"read minus total {lo:+d}..{up:+d}", [r for r in hi if lo <= r["plain"] - r["tot"] < up], "over")
print("   the same on 1,220-1,399 m floors")
mid = [r for r in P if 1220 <= r["el"] < 1400 and r["plain"] is not None]
for lo, up in ((-99, -3), (-3, 0), (0, 3), (3, 99)):
    lib.line(f"read minus total {lo:+d}..{up:+d}", [r for r in mid if lo <= r["plain"] - r["tot"] < up], "over")

print("\n== (d) BEFORE BOTH TEAMS HAVE 5 FINALS (the November games), 1,400 m+")
ea = [r for r in P if r["el"] >= 1400 and r["plain"] is None]
lib.line("every such game OVER", ea, "over")
lib.line("  with an early read", [r for r in ea if r["early"] is not None], "over")
for lo, up in ((-99, -3), (-3, 0), (0, 3), (3, 99), (-3, 99), (0, 99)):
    lib.line(f"  early read minus total {lo:+d}..{up:+d}",
             [r for r in ea if r["early"] is not None and lo <= r["early"] - r["tot"] < up], "over")
lib.line("  opening week (both teams' games 1-2)", [r for r in ea if max(r["gp"]) < 2], "over")
lib.line("  games 3-5", [r for r in ea if max(r["gp"]) >= 2], "over")
lib.line("  every such game, 1,220-1,399 m", [r for r in P if 1220 <= r["el"] < 1400 and r["plain"] is None], "over")
lib.line("  every such game, LOW ground <600 m (the base)", [r for r in P if r["el"] < 600 and r["plain"] is None], "over")

print("\n== (e) THE CANDIDATE: 4,600 ft+ and the read (plain, or the early one) no worse than 3 under the total")
for cut in (-99, -6, -3, 0):
    c = [r for r in P if r["el"] >= 1400 and (r["plain"] if r["plain"] is not None else r["early"]) is not None
         and (r["plain"] if r["plain"] is not None else r["early"]) - r["tot"] >= cut]
    lib.line(f"1,400 m+, read >= total {cut:+d}", c, "over")
c = [r for r in P if r["el"] >= 1400 and (r["plain"] if r["plain"] is not None else r["early"]) is not None
     and (r["plain"] if r["plain"] is not None else r["early"]) - r["tot"] >= -3]
by = defaultdict(int)
for r in c:
    by[r["season"]] += 1
print("   bets a season:", dict(by))
for lab, f in (("Nov", ("11",)), ("Dec", ("12",)), ("Jan-Mar", ("01", "02", "03"))):
    lib.line(f"   candidate, {lab}", [r for r in c if r["start"][5:7] in f], "over")
new = [r for r in c if not (r["plain"] is not None and r["plain"] + BUILT_ADJ - r["tot"] >= 2)]
lib.line("   candidate games the BUILT play doesn't already take", new, "over")
