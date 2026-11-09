"""S2c - is the S2b three-point NET fade NEW, or the built hot-ATS fade (sports.mark_ncaab_ats_gap, both teams 10+
priced finals, gap 3+) / the built glass weight wearing another coat? The NET +5+ side (games 6+, 60+ attempts each)
split by: the built hot-ATS flag (the side's season average cover margin minus the opponent's, 10+ priced games each:
>= 3 = the built weight fires; < 3 or under 10 games = it doesn't), the side's own season cover margin, and the 'pure'
luck part - OPP 3P% alone (the defense's luck) vs OWN 3P% alone. ATS and the favorite's ML at the close.
TRAIN 2021-22, HELD 2023-25."""
from collections import defaultdict
import lib
import sports_ncaab_box as nb

box = nb.load_box()
fin = lib.finals("ncaab")
allf = [g for g in lib.all_finals("ncaab") if g["stype"] == "2"]
run = defaultdict(lambda: [0, 0, 0, 0, 0])
pre = {}
for g in allf:
    b = box.get(g["id"])
    for side in ("home", "away"):
        pre[(g["id"], side)] = tuple(run[(g["season"], g[side])])
    if not b or g["home"] not in b or g["away"] not in b:
        continue
    for side, opp in (("home", "away"), ("away", "home")):
        r = run[(g["season"], g[side])]
        r[0] += 1
        r[1] += b[g[side]]["tpm"]; r[2] += b[g[side]]["tpa"]
        r[3] += b[g[opp]]["tpm"]; r[4] += b[g[opp]]["tpa"]
cov = defaultdict(list)       # (season, team) -> cover margins, priced finals in order
precov = {}
for g in fin:
    if g["stype"] != "2":
        continue
    for side in ("home", "away"):
        v = cov[(g["season"], g[side])]
        precov[(g["id"], side)] = (sum(v) / len(v), len(v)) if v else (None, 0)
    if g["sp"] is not None:
        m = g["hs"] - g["as"]
        cov[(g["season"], g["home"])].append(m + g["sp"])
        cov[(g["season"], g["away"])].append(-m - g["sp"])

cells = lib.Cells()
for g in fin:
    if g["stype"] != "2" or g["season"] < 2021:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        p = pre.get((g["id"], side))
        if not p:
            continue
        ng, tpm, tpa, otpm, otpa = p
        if ng < 5 or tpa < 60 or otpa < 60:
            continue
        own, oppp = tpm / tpa, otpm / otpa
        net = own - oppp
        mc, mn = precov[(g["id"], side)]
        tc, tn = precov[(g["id"], "away" if side == "home" else "home")]
        hot = (mn >= 10 and tn >= 10 and mc - tc >= 3)
        s = g["season"]
        a = lib.ats(g, side)
        pl = lib.profit(won, lib.dec(o))
        fav = -250 <= o <= -101

        def add(k):
            cells.add(f"{k} | ATS", s, a)
            if fav:
                cells.add(f"{k} | FAV ML", s, pl)
        if net >= 0.05:
            add("NET +5+, the built hot-ATS flag ON")if hot else add("NET +5+, hot-ATS flag OFF")
            if mc is not None and mc < 0:
                add("NET +5+, own season cover margin < 0 (the market isn't chasing it)")
            if mc is not None and mn >= 5 and abs(mc) < 2:
                add("NET +5+, own season cover margin within 2")
        elif -0.02 <= net <= 0.02 and not hot:
            add("control NET +-2, hot-ATS flag OFF")
        if ng >= 5 and oppp <= 0.30 and own < 0.36:
            add("OPP 3P% <= 30 (lucky D), own under 36")
        if ng >= 5 and own >= 0.38 and oppp > 0.32:
            add("OWN 3P% >= 38 (hot), opp over 32")
cells.dump("s2c", "S2c - the 3P NET fade vs the built hot-ATS weight (games 6+, 60+ attempts each)",
           (2021, 2022), (2023, 2024, 2025, 2026))
