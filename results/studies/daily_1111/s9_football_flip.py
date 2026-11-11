"""S9 (NFL + college football, the paid odds history) - THE LINE FLIP (never studied: the hammered spot / the
money-left fade / the overnight move / book first-mover read the SIZE of a move; nobody read the side the market moved
THROUGH pick'em - a favorite at the first fair number that closes as the dog, or the reverse).
FLIPPED TO DOG = the side's median no-vig was over 50% at the first FAIR look (ready_at / fair, 1.5-7.5 days out) and
it closes as a moneyline dog. Bet at the close (the flip is known by then - no look-ahead), and at the last look of
the history (0.03-1.5 days out) as the second price. Control = the dogs in the SAME closing band +100..+150 that were
dogs all week. The mirror: FLIPPED TO FAVORITE (a dog at the first fair number that closes -101..-150), against the
favorites -101..-150 that were favorites all week. ATS at the close for the same sides.
TRAIN 2020-22, HELD 2023 / 2024 / 2025 apart, 2026 live (the history starts 2020)."""
import sys

import lib

cells = lib.Cells()
for LG in ("nfl", "ncaaf"):
    fin = {g["id"]: g for g in lib.finals(LG)}
    for x in lib.load_football(LG):
        g = fin.get(x["id"])
        if not g or g["stype"] != "2":
            continue
        f = lib.first_fair(x["ml"])
        ll = lib.last_look(x["all_ml"])
        if not f:
            continue
        _, _, p0 = lib.ml_med(f[1])
        for side, team, opp, o, won, home in lib.sides(g):
            pf = p0 if home else 1 - p0
            s = g["season"]
            pl = lib.profit(won, lib.dec(o))
            a = lib.ats(g, side)
            lp = None
            if ll:
                h, aa, _ = lib.ml_med(ll[1])
                lp = h if home else aa
            labs = []
            if 100 <= o <= 150:
                if pf > 0.5:
                    labs.append("FLIPPED TO DOG (fav at the first fair, +100..+150 at the close)")
                    if pf > 0.55:
                        labs.append("FLIPPED TO DOG from a 55%+ favorite")
                else:
                    labs.append("control: dog all week, +100..+150 at the close")
            if -150 <= o <= -101:
                if pf < 0.5:
                    labs.append("FLIPPED TO FAV (dog at the first fair, -101..-150 at the close)")
                    if pf < 0.45:
                        labs.append("FLIPPED TO FAV from a 45%- dog")
                else:
                    labs.append("control: fav all week, -101..-150 at the close")
            for lab in labs:
                for lgl in (LG, "both"):
                    cells.add(f"{lgl} | {lab} | ML close", s, pl)
                    if lp and lp > 1:
                        cells.add(f"{lgl} | {lab} | ML last look", s, lib.profit(won, lp))
                    cells.add(f"{lgl} | {lab} | ATS close", s, a)
cells.dump("s9", "S9 NFL + college football - the line flip through pick'em (paid odds history first fair -> the close); "
           "TRAIN 2020-22", (2020, 2022), (2023, 2024, 2025, 2026))
