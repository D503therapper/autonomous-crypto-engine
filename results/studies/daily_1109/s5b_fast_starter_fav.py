"""S5b - the one S5 cell: the NHL FAVORITE -101..-250 that wins first periods more than its whole goal differential
says (1st-period excess +0.25+ a game, 10+ games) - the dose (+0.15 / +0.25 / +0.35), the OPEN (ESPN, 2023-26), the
paid MORNING look (2021-23), -101..-150 vs -151..-250, home / road. TRAIN to 2022, HELD 2023-25."""
import importlib.util, os
import lib

spec = importlib.util.spec_from_file_location("s5", os.path.join(lib.OUT, "s5_s6_s8_periods.py"))
src = open(os.path.join(lib.OUT, "s5_s6_s8_periods.py")).read().split("cells = lib.Cells()")[0]
ns = {}
exec(compile(src, "s5_head", "exec"), ns)
fin, pre = ns["run"]("nhl", 3)
mo = lib.nhl_morning()
cells = lib.Cells()
for g in fin:
    s = g["season"]
    for side, team, opp, o, won, home in lib.sides(g):
        r = pre.get((g["id"], side))
        if not r or r["n"] < 10 or not -250 <= o <= -101:
            continue
        ex1 = r["p1"] / r["n"] - r["tot"] / r["n"] / 3
        pl = lib.profit(won, lib.dec(o))
        oo = g["oh"] if home else g["oa"]
        m = lib.morning_side(mo, g["id"], side)
        for thr in (0.15, 0.25, 0.35):
            if ex1 >= thr:
                cells.add(f"fast starter fav, excess +{thr}+ | close", s, pl)
                if oo and -250 <= oo <= -101:
                    cells.add(f"fast starter fav, excess +{thr}+ | open", s, lib.profit(won, lib.dec(oo)))
                if m:
                    cells.add(f"fast starter fav, excess +{thr}+ | paid morning", s, lib.profit(won, m[1]))
        if ex1 >= 0.25:
            cells.add(f"fast starter fav +0.25 | {'-101..-150' if o >= -150 else '-151..-250'}", s, pl)
            cells.add(f"fast starter fav +0.25 | {'home' if home else 'road'}", s, pl)
        if -0.1 <= ex1 <= 0.1:
            cells.add("control fav, excess within 0.1 | close", s, pl)
            if oo and -250 <= oo <= -101:
                cells.add("control fav, excess within 0.1 | open", s, lib.profit(won, lib.dec(oo)))
cells.dump("s5b", "S5b - the NHL fast-starter favorite: dose, open, morning", (2010, 2022), (2023, 2024, 2025, 2026))
