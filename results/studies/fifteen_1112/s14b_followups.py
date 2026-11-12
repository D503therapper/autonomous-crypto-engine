"""S14b - the three college hoops total cells of s14 that stood out, each taken apart before anything is believed:
(1) THE HOT START UNDER - a team 2-4 games in whose games are running 8+ points over its LAST season's;
(2) THE RATED READ 6+ UNDER the total;
(3) THE JUICE LEAN - the plus-price side of a total when the book juices the other side (every league - study 15).
Low ground only (altitude floors are the built play's)."""
import math, random
from collections import defaultdict

import lib as L
import s14_hoops_totals as S    # (re-runs s14's prints into this run's log - read below the 'S14b' line)

print("\n\n" + "#" * 40, "S14b")
L.CELLS[0] = 0
P, ov, un, R2, br, plain, bp = S.P, S.ov, S.un, S.R2, S.br, S.plain, S.bp


# ---------------------------------------------------------------- (1)
def hot(g, lo=2, hi=4, need=15):
    """The biggest (this season's game total - last season's) among the two teams, for a team lo..hi games in."""
    best = None
    for side in ("H", "A"):
        f = g[side]
        pv = f.get("prev")
        if lo <= f["n"] <= hi and pv and pv["n"] >= need:
            d = (f["pf"] + f["pa"]) - (pv["pf"] + pv["pa"])
            best = d if best is None else max(best, d)
    return best


def cold(g, lo=2, hi=4, need=15):
    best = None
    for side in ("H", "A"):
        f = g[side]
        pv = f.get("prev")
        if lo <= f["n"] <= hi and pv and pv["n"] >= need:
            d = (f["pf"] + f["pa"]) - (pv["pf"] + pv["pa"])
            best = d if best is None else min(best, d)
    return best


print("=" * 30, "(1) THE HOT START UNDER (one row a game)")
E = [(g, hot(g)) for g in P]
E = [(g, d) for g, d in E if d is not None]
base = L.cell("every game with a team 2-4 games in (last season on file) UNDER", un([g for g, d in E]))
L.cell("   OVER", ov([g for g, d in E]))
for lo, hi in ((-99, 0), (0, 4), (4, 8), (8, 12), (12, 16), (16, 22), (22, 99)):
    L.cell(f"hottest team's games {lo}..{hi} over last season's -> UNDER", un([g for g, d in E if lo <= d < hi]))
for k in (6, 8, 10, 12):
    L.cell(f"{k}+ over last season's -> UNDER", un([g for g, d in E if d >= k]))
    L.cell(f"{k}+ -> OVER (the mirror)", ov([g for g, d in E if d >= k]))
H8 = [g for g, d in E if d >= 8]
x = L.cell("THE CELL: 8+ over last season's -> UNDER", un(H8))
L.cell("  the under, the close 1 point against us", un(H8, -1))
L.cell("  the under, the close 1.5 against us", un(H8, -1.5))
L.cell("  under priced -112 or cheaper", un([g for g in H8 if (g["uno"] or -110) >= -112]))
L.cell("  under priced worse than -112", un([g for g in H8 if (g["uno"] or -110) < -112]))
L.cell("  BOTH teams 8+ over their last season", un([g for g in H8 if all(
    2 <= g[s]["n"] <= 4 and g[s].get("prev") and g[s]["prev"]["n"] >= 15
    and (g[s]["pf"] + g[s]["pa"]) - (g[s]["prev"]["pf"] + g[s]["prev"]["pa"]) >= 8 for s in "HA")]))
L.cell("  the hot team at home", un([g for g in H8 if not g["neutral"] and g["H"].get("prev") and 2 <= g["H"]["n"] <= 4
                                     and (g["H"]["pf"] + g["H"]["pa"]) - (g["H"]["prev"]["pf"] + g["H"]["prev"]["pa"]) >= 8]))
L.cell("  neutral floor", un([g for g in H8 if g["neutral"]]))
L.cell("  total under 140", un([g for g in H8 if g["tot"] < 140]))
L.cell("  total 140-150", un([g for g in H8 if 140 <= g["tot"] < 150]))
L.cell("  total 150+", un([g for g in H8 if g["tot"] >= 150]))
L.cell("  spread 0-7.5", un([g for g in H8 if g["sp"] is not None and abs(g["sp"]) <= 7.5]))
L.cell("  spread 8-15.5", un([g for g in H8 if g["sp"] is not None and 8 <= abs(g["sp"]) <= 15.5]))
L.cell("  spread 16+", un([g for g in H8 if g["sp"] is not None and abs(g["sp"]) >= 16]))
for lo, hi in ((1, 1), (2, 2), (3, 3), (4, 4), (5, 6), (7, 9), (10, 14)):
    Ex = [(g, hot(g, lo, hi)) for g in P]
    L.cell(f"  the window: a team {lo}-{hi} games in, 8+ over -> UNDER", un([g for g, d in Ex if d is not None and d >= 8]))
# the total itself against last season's read: has the book already chased the hot start?
def prevtot(g):
    h, a = g["H"].get("prev"), g["A"].get("prev")
    if not h or not a or h["n"] < 15 or a["n"] < 15:
        return None
    return (h["pf"] + a["pa"] + a["pf"] + h["pa"]) / 2
L.cell("  the total 4+ OVER last season's two-team read (the book chased it)",
       un([g for g in H8 if prevtot(g) is not None and g["tot"] - prevtot(g) >= 4]))
L.cell("  the total within 4 of last season's read", un([g for g in H8 if prevtot(g) is not None and abs(g["tot"] - prevtot(g)) < 4]))
L.cell("  the total 4+ UNDER last season's read", un([g for g in H8 if prevtot(g) is not None and g["tot"] - prevtot(g) <= -4]))
L.cell("  the plain read this season (both teams' scoring) 3+ OVER the total",
       un([g for g in H8 if all(g[s]["n"] >= 2 for s in "HA")
           and (g["H"]["pf"] + g["A"]["pa"] + g["A"]["pf"] + g["H"]["pa"]) / 2 - g["tot"] >= 3]))
L.cell("  the plain read this season 3+ UNDER the total",
       un([g for g in H8 if all(g[s]["n"] >= 2 for s in "HA")
           and (g["H"]["pf"] + g["A"]["pa"] + g["A"]["pf"] + g["H"]["pa"]) / 2 - g["tot"] <= -3]))
ps = [p for _, p in x["bets"]]
pool = [p for _, p in base["bets"]]
print(f"   placebo: random {len(ps)} unders from the same pool (a team 2-4 games in) as good: "
      f"{L.placebo(pool, len(ps), sum(ps) / len(ps))} of 2000")
tr = [p for s, p in x["bets"] if s <= 2021]
bl = [p for s, p in x["bets"] if s > 2021]
ptr = [p for s, p in base["bets"] if s <= 2021]
pbl = [p for s, p in base["bets"] if s > 2021]
rnd = random.Random(11)
both_ok = sum(1 for _ in range(2000) if sum(rnd.sample(ptr, len(tr))) / len(tr) >= sum(tr) / len(tr)
              and sum(rnd.sample(pbl, len(bl))) / len(bl) >= sum(bl) / len(bl))
print(f"   ... as good in BOTH halves at once: {both_ok} of 2000")
print(f"   at 1/2u a play: {0.5 * sum(ps):+.1f}u on {len(ps)}, worst stretch {0.5 * L.worst(ps):.1f}u; about {len(ps) / 9:.0f} a season")
# the mirror: cold starts
Cc = [(g, cold(g)) for g in P]
Cc = [(g, d) for g, d in Cc if d is not None]
for k in (8, 12):
    L.cell(f"the COLD start: a team's games {k}+ UNDER last season's -> OVER", ov([g for g, d in Cc if d <= -k]))
    L.cell("   -> UNDER", un([g for g, d in Cc if d <= -k]))

# ---------------------------------------------------------------- (2)
print("\n" + "=" * 30, "(2) THE RATED READ UNDER THE TOTAL")
RR = [(g, R2[g["id"]] - g["tot"] - br) for g in P if g["id"] in R2]
for lo, hi in ((4, 5), (5, 6), (6, 7), (7, 8), (8, 10), (10, 12), (12, 99)):
    L.cell(f"rated read {lo}..{hi} under -> UNDER", un([g for g, d in RR if lo <= -d < hi]))
for k in (5, 6, 7):
    L.cell(f"rated read {k}+ under -> UNDER", un([g for g, d in RR if d <= -k]))
R6 = [g for g, d in RR if d <= -6]
y = L.cell("THE CELL: rated read 6+ under -> UNDER", un(R6))
for mm, nm in ((("11",), "November"), (("12",), "December"), (("01",), "January"), (("02", "03"), "Feb-Mar")):
    L.cell(f"  {nm}", un([g for g in R6 if g["start"][5:7] in mm]))
L.cell("  the close 1 point against us", un(R6, -1))
L.cell("  a team under 5 games in", un([g for g in R6 if min(g["H"]["n"], g["A"]["n"]) < 5]))
L.cell("  both 5+ games in", un([g for g in R6 if min(g["H"]["n"], g["A"]["n"]) >= 5]))
L.cell("  both 10+ games in", un([g for g in R6 if min(g["H"]["n"], g["A"]["n"]) >= 10]))
L.cell("  NOT a hot-start game (cell 1 out)", un([g for g in R6 if (hot(g) or 0) < 8]))
L.cell("  hot-start games only", un([g for g in R6 if (hot(g) or 0) >= 8]))
h8 = {g["id"] for g in H8}
L.cell("hot start 8+ AND the rated read not 6+ under", un([g for g, d in RR if g["id"] in h8 and d > -6]))
pool2 = [L.tot(g, "under") for g, d in RR]
ps2 = [p for _, p in y["bets"]]
print(f"   placebo: random {len(ps2)} unders as good: {L.placebo(pool2, len(ps2), sum(ps2) / len(ps2))} of 2000")
# a second build of the rating (a different step) - does the cell survive?
for k in (0.10, 0.14):
    Rk, _ = S.rated(k)
    bk = sum(Rk[g["id"]] - g["tot"] for g in P if g["id"] in Rk and g["season"] <= 2021) / sum(1 for g in P if g["id"] in Rk and g["season"] <= 2021)
    L.cell(f"  the rating at step {k}: 6+ under -> UNDER", un([g for g in P if g["id"] in Rk and Rk[g["id"]] - g["tot"] - bk <= -6]))

# ---------------------------------------------------------------- (3)
print("\n" + "=" * 30, "(3) THE JUICE LEAN ON A TOTAL, EVERY LEAGUE (study 15)")
for lg in ("ncaab", "nba", "nfl", "ncaaf", "nhl"):
    Gx = [g for g in L.table(lg) if L.reg(g) and g["tot"] is not None and g["ovo"] and g["uno"]
          and 100 <= abs(g["ovo"]) <= 170 and 100 <= abs(g["uno"]) <= 170]
    n_all = len(Gx)
    lean_u = [g for g in Gx if g["uno"] <= -115 and g["ovo"] >= -105]
    lean_o = [g for g in Gx if g["ovo"] <= -115 and g["uno"] >= -105]
    print(f"{lg}: {n_all} priced totals; the under juiced {len(lean_u)}, the over juiced {len(lean_o)}")
    L.cell(f"{lg} under juiced -> the OVER (plus-price side)", [(g["season"], L.tot(g, "over")) for g in lean_u])
    L.cell(f"{lg} under juiced -> the UNDER", [(g["season"], L.tot(g, "under")) for g in lean_u])
    L.cell(f"{lg} over juiced -> the UNDER (plus-price side)", [(g["season"], L.tot(g, "under")) for g in lean_o])
    L.cell(f"{lg} over juiced -> the OVER", [(g["season"], L.tot(g, "over")) for g in lean_o])
    L.cell(f"{lg} the cheap side, both ways", [(g["season"], L.tot(g, "over")) for g in lean_u] + [(g["season"], L.tot(g, "under")) for g in lean_o])
    # win rate of the cheap side - the price-free read
    w = sum(1 for g in lean_u if g["hs"] + g["as"] > g["tot"]) + sum(1 for g in lean_o if g["hs"] + g["as"] < g["tot"])
    l_ = sum(1 for g in lean_u if g["hs"] + g["as"] < g["tot"]) + sum(1 for g in lean_o if g["hs"] + g["as"] > g["tot"])
    if w + l_:
        print(f"   the cheap side won {w}-{l_} = {100 * w / (w + l_):.1f}% (a coin = 50%; z {(w - l_) / math.sqrt(w + l_):+.1f})")
    by = defaultdict(lambda: [0, 0])
    for g in lean_u + lean_o:
        cheap_over = g in lean_u
        pts = g["hs"] + g["as"]
        if pts != g["tot"]:
            by[g["season"]][0 if (pts > g["tot"]) == cheap_over else 1] += 1
    print("   by season: " + " ".join(f"{s}:{a}-{b}" for s, (a, b) in sorted(by.items())))
    for lo, hi in ((10, 14), (15, 24), (25, 99)):
        rows = [(g["season"], L.tot(g, "over")) for g in Gx if g["uno"] < 0 and lo <= (-g["uno"]) - (-g["ovo"] if g["ovo"] < 0 else 200 - g["ovo"]) <= hi] + \
               [(g["season"], L.tot(g, "under")) for g in Gx if g["ovo"] < 0 and lo <= (-g["ovo"]) - (-g["uno"] if g["uno"] < 0 else 200 - g["uno"]) <= hi]
        L.cell(f"{lg} the cheap side, a juice gap of {lo}..{hi} cents", rows)
L.done()
