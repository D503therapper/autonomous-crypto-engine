"""S2b - the one S2 cell that showed (NOT week 2): the college hoops side whose season three-point NET (own 3P% minus
what its opponents shot from three) is +8 points or better, games 8-20, ATS -13.6% on 1,027 / as a favorite -16.7%.
The dose (NET +5 / +8 / +12), the season stage (games 6-10 / 11-20 / 21+), home / road, the favorite at the OPEN, the
favorite -101..-150 vs -151..-250, and the side across it (the 'unlucky' team) as a dog. Also: the 3P attempt-weighted
version (made-threes per game over expectation) to be sure it isn't a three-heavy style. TRAIN 2021-22, HELD 2023-25."""
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

cells = lib.Cells()
for g in fin:
    if g["stype"] != "2" or g["season"] < 2021:
        continue
    for side, team, opp, o, won, home in lib.sides(g):
        p = pre.get((g["id"], side))
        q = pre.get((g["id"], "away" if side == "home" else "home"))
        if not p or not q:
            continue
        ng, tpm, tpa, otpm, otpa = p
        if ng < 5 or tpa < 60 or otpa < 60:
            continue
        net = tpm / tpa - otpm / otpa
        qn = (q[1] / q[2] - q[3] / q[4]) if q[2] >= 60 and q[4] >= 60 else None
        ph = "g6-10" if ng <= 9 else ("g11-20" if ng <= 19 else "g21+")
        s = g["season"]
        a = lib.ats(g, side)
        pl = lib.profit(won, lib.dec(o))
        oo = g["oh"] if home else g["oa"]
        for lo, nm in ((0.05, "NET +5+"), (0.08, "NET +8+"), (0.12, "NET +12+")):
            if net < lo:
                continue
            for k in (f"{nm} all games 6+", f"{nm} {ph}"):
                cells.add(f"{k} | ATS", s, a)
                if -250 <= o <= -101:
                    cells.add(f"{k} | FAV ML", s, pl)
                    if oo and -250 <= oo <= -101:
                        cells.add(f"{k} | FAV ML open", s, lib.profit(won, lib.dec(oo)))
                if lib.dog_band(o):
                    cells.add(f"{k} | DOG ML", s, pl)
            if nm == "NET +8+":
                cells.add(f"NET +8+ {'home' if home else 'away/neutral'} | ATS", s, a)
                if -150 <= o <= -101:
                    cells.add("NET +8+ | FAV -101..-150 ML", s, pl)
                elif -250 <= o <= -151:
                    cells.add("NET +8+ | FAV -151..-250 ML", s, pl)
                if qn is not None and qn <= 0:
                    cells.add("NET +8+ vs a team NET <= 0 | ATS", s, a)
                    if -250 <= o <= -101:
                        cells.add("NET +8+ vs a team NET <= 0 | FAV ML", s, pl)
        if -0.02 <= net <= 0.02:
            cells.add("control NET +-2 all games 6+ | ATS", s, a)
            if -250 <= o <= -101:
                cells.add("control NET +-2 all games 6+ | FAV ML", s, pl)
                if oo and -250 <= oo <= -101:
                    cells.add("control NET +-2 all games 6+ | FAV ML open", s, lib.profit(won, lib.dec(oo)))
        if net <= -0.08 and lib.dog_band(o):
            cells.add("NET -8 or worse (unlucky) | DOG ML", s, pl)
cells.dump("s2b", "S2b - college hoops season 3P NET (own 3P% - opponents' 3P%, 60+ attempts each, games 6+)",
           (2021, 2022), (2023, 2024, 2025, 2026))
