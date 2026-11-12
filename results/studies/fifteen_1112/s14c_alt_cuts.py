"""S14c - THE ⛰️ ALTITUDE OVER against this run's fades (does one belong on the built play as a guard?): a hot-start
game (a team 2-4 games in running 8+ over last season's game totals - every low-ground over there lost 14%), the
total's size, the price, a big spread."""
import lib as L
import s14a_alt_size as A   # (prints s14a again above the line)

print("\n" + "#" * 40, "S14c")
L.CELLS[0] = 0


def hot(g, lo=2, hi=4):
    best = None
    for side in ("H", "A"):
        f = g[side]
        pv = f.get("prev")
        if lo <= f["n"] <= hi and pv and pv["n"] >= 15:
            d = (f["pf"] + f["pa"]) - (pv["pf"] + pv["pa"])
            best = d if best is None else max(best, d)
    return best


R = A.rule
ov = lambda rows: [(g["season"], L.tot(g, "over")) for g in rows]   # noqa: E731
L.cell("altitude rule, every play", ov(R))
L.cell("  a hot-start game (8+ over last season's, 2-4 games in)", ov([g for g in R if (hot(g) or 0) >= 8]))
L.cell("  a team 2-4 games in, NOT hot", ov([g for g in R if hot(g) is not None and hot(g) < 8]))
L.cell("  a team 1-5 games in, 12+ over last season's", ov([g for g in R if (hot(g, 1, 5) or 0) >= 12]))
L.cell("  the read 3+ OVER the total", ov([g for g in R if A.read(g) - g["tot"] >= 3]))
L.cell("  the read within 3", ov([g for g in R if abs(A.read(g) - g["tot"]) < 3]))
L.cell("  total 160+", ov([g for g in R if g["tot"] >= 160]))
L.cell("  total 150-160", ov([g for g in R if 150 <= g["tot"] < 160]))
L.cell("  total under 150", ov([g for g in R if g["tot"] < 150]))
L.cell("  over priced -115..-130", ov([g for g in R if (g["ovo"] or -110) <= -115]))
L.cell("  spread 15+", ov([g for g in R if g["sp"] is not None and abs(g["sp"]) >= 15]))
L.done()
