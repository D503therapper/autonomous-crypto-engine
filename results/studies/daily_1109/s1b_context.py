"""S1b - is the 2026-27 early road dog's run its own, or the whole slate's? Every college hoops side in games 1-3
(by the side's own game number) on a true road / home floor, 2026-27 vs 2018-25: road dogs, home dogs, road favorites,
home favorites, ML at the close and ATS; plus the neutral-floor dogs. And the early road dog by the HOME team's game
number (a home team in its opener vs later)."""
from collections import defaultdict
import lib

fin = lib.finals("ncaab")
allf = [g for g in lib.all_finals("ncaab") if g["stype"] == "2"]
gn, cnt = {}, defaultdict(int)
for g in allf:
    for side in ("home", "away"):
        cnt[(g["season"], g[side])] += 1
        gn[(g["id"], side)] = cnt[(g["season"], g[side])]
cells = lib.Cells()
for g in fin:
    if g["stype"] != "2":
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        n = gn.get((g["id"], side))
        if n is None or n > 3:
            continue
        floor = "neutral" if g["neutral"] else ("home" if home else "road")
        kind = "dog +100..+350" if lib.dog_band(o) else ("fav -101..-250" if -250 <= o <= -101 else None)
        if not kind:
            continue
        s = g["season"]
        cells.add(f"games 1-3 {floor:7s} {kind} ML", s, lib.profit(won, lib.dec(o)))
        cells.add(f"games 1-3 {floor:7s} {kind} ATS", s, lib.ats(g, side))
        if floor == "road" and kind.startswith("dog"):
            hn = gn.get((g["id"], "home"))
            cells.add(f"early road dog, the HOME team's game {'1' if hn == 1 else '2-3' if hn <= 3 else '4+'} ML", s,
                      lib.profit(won, lib.dec(o)))
cells.dump("s1b", "S1b - every games 1-3 side by floor, 2018-25 vs 2026-27 live", (2018, 2022), (2023, 2024, 2025, 2026))
