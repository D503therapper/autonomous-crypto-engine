"""The table's coverage by season (a sanity print, no cells)."""
import collections, time
import lib

t = time.time()
R = lib.build()
print(len(R), "games", round(time.time() - t, 1), "s")
c = collections.Counter()
for g in R:
    s = g["season"]
    c[(s, "n")] += 1
    c[(s, "ml")] += bool(g["mlh"])
    c[(s, "sp")] += g["sp"] is not None
    c[(s, "tot")] += g["total"] is not None
    c[(s, "bx")] += bool("bx" in g["H"] and "bx" in g["A"] and g["mlh"])
    c[(s, "ls")] += bool(g["lsh"])
    c[(s, "conf")] += g["conf"]
    c[(s, "pf")] += bool("bx" in g["H"] and g["H"]["bx"]["pf"] and g["mlh"])
    c[(s, "lead")] += bool("bx" in g["H"] and g["H"]["bx"]["lead"] is not None and g["mlh"])
print("season [games, ml, spread, total, box both, halves, conf, fouls, lead]")
for s in range(2016, 2027):
    print(s, [c[(s, k)] for k in ("n", "ml", "sp", "tot", "bx", "ls", "conf", "pf", "lead")])
g = [x for x in R if x["season"] == 2025 and "bx" in x["H"] and x["H"]["bx"]["n"] > 15][100]
print(g["hn"], g["H"]["tier"], {k: round(v, 3) if isinstance(v, float) else v for k, v in g["H"]["bx"].items()})
