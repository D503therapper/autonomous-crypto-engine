"""S2 - COLLEGE HOOPS WEEK 2: EARLY THREE-POINT LUCK (never cut on its own - the 11/4 shooting study read a team's OWN
last-5 form vs its season, 5+ boxed games; the efficiency model pulls 3P% toward the D1 average inside its read).
Week 2 is where a team's record first separates from its number: 2-4 games in, a hot or cold night from three moves
the results the market sees most. Per side, from the team box (sports_ncaab_box.load_box - ESPN's team box, 2021-26),
over every boxed regular-season game this season BEFORE tonight:
  OWN 3P% (its made / attempted threes), OPP 3P% (what its opponents shot from three against it), on 30+ attempts,
  NET = own - opp (the 'three-point luck' gap).
Tonight's side in its games 3-5 (2-4 boxed games before). Cells: as a dog +100..+350 / favorite -101..-250 at the
close, and ATS on every side; the same cuts in games 8-20 = the control (does the market catch up later anyway?).
TRAIN 2021-22, HELD 2023 / 2024 / 2025 apart, 2026 = live. Prices: the game file's close; ESPN's open as the 2nd check."""
from collections import defaultdict
import lib
import sports_ncaab_box as nb

box = nb.load_box()
fin = lib.finals("ncaab")
allf = [g for g in lib.all_finals("ncaab") if g["stype"] == "2"]
run = defaultdict(lambda: [0, 0, 0, 0, 0])        # (season, team) -> [games, 3pm, 3pa, opp 3pm, opp 3pa]
pre = {}
for g in allf:
    b = box.get(g["id"])
    for side, opp in (("home", "away"), ("away", "home")):
        r = run[(g["season"], g[side])]
        pre[(g["id"], side)] = tuple(r)
    if not b or g["home"] not in b or g["away"] not in b:
        for side in ("home", "away"):
            run[(g["season"], g[side])][0] += 0   # unboxed: the game does not count toward the shooting
        continue
    for side, opp in (("home", "away"), ("away", "home")):
        r = run[(g["season"], g[side])]
        r[0] += 1
        r[1] += b[g[side]]["tpm"]; r[2] += b[g[side]]["tpa"]
        r[3] += b[g[opp]]["tpm"]; r[4] += b[g[opp]]["tpa"]

cells = lib.Cells()
n_rows = 0
for g in fin:
    if g["stype"] != "2" or g["season"] < 2021:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        p = pre.get((g["id"], side))
        if not p:
            continue
        ng, tpm, tpa, otpm, otpa = p
        if 2 <= ng <= 4:
            ph = "games 3-5"
        elif 7 <= ng <= 19:
            ph = "games 8-20"
        else:
            continue
        if tpa < 30 or otpa < 30:
            continue
        n_rows += 1
        own, oppp = tpm / tpa, otpm / otpa
        net = own - oppp
        labs = []
        if oppp >= 0.40:
            labs.append("OPP shot 40%+ from 3 vs it (unlucky D)")
        if oppp <= 0.28:
            labs.append("OPP shot 28%- from 3 vs it (lucky D)")
        if own >= 0.40:
            labs.append("OWN 40%+ from 3 (hot)")
        if own <= 0.28:
            labs.append("OWN 28%- from 3 (cold)")
        if net <= -0.08:
            labs.append("NET 3P luck -8 pts or worse")
        if net >= 0.08:
            labs.append("NET 3P luck +8 pts or better")
        if -0.03 <= net <= 0.03:
            labs.append("NET within 3 pts (control)")
        s = g["season"]
        pl = lib.profit(won, lib.dec(o))
        oo = g["oh"] if home else g["oa"]
        a = lib.ats(g, side)
        for lab in labs:
            if lib.dog_band(o):
                cells.add(f"{ph} | {lab} | DOG ML", s, pl)
                if oo and lib.dog_band(oo):
                    cells.add(f"{ph} | {lab} | DOG ML open", s, lib.profit(won, lib.dec(oo)))
            if -250 <= o <= -101:
                cells.add(f"{ph} | {lab} | FAV ML", s, pl)
            cells.add(f"{ph} | {lab} | ATS", s, a)
print("rows", n_rows)
cells.dump("s2", "S2 - college hoops early three-point luck (own / opponents' 3P% over the games before tonight, 30+ "
           "attempts each)", (2021, 2022), (2023, 2024, 2025, 2026))
