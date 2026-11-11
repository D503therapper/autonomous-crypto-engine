"""X1 (a RE-CUT, not counted as new: the 10/14 daily run read college + NHL dogs by game total, the 10/15 run NFL dogs by total - both DEAD; found after it ran) - THE DOG BY THE CLOSING TOTAL (the
totals studies graded the over / under; the 10/x relative low total is an NBA dog-score cell; the 11/1 division
under read totals 42 or less as an UNDER).
The old saw: a low total means fewer possessions / fewer goals, more of the game left to chance - the dog's side
gets more valuable the lower the total (and the big favorite needs points to cover). Does the CLOSING price have it?
The total is read RELATIVE to the league's median closing total over its last 300 priced games before tonight (the
scoring level drifts by season - a fixed number would flag eras, not games). Cells: dog +100..+350 / favorite
-101..-250 on the moneyline at the close, ATS at the close (football), by the relative total band, and inside the
spread size (football: a 7+ point dog). Close only - the closing total is the input, so an earlier price would be a
look-ahead. TRAIN = the old seasons, HELD = each newer season apart, NOW = 2026."""
import statistics
import sys

import lib

LG = sys.argv[1] if len(sys.argv) > 1 else "nfl"
TAG = {"nfl": "x1_nfl", "ncaaf": "x1_ncaaf", "nhl": "x1_nhl"}[LG]
fin = [g for g in lib.finals(LG) if g["stype"] == "2"]
TRAIN = {"nfl": (2016, 2021), "ncaaf": (2016, 2021), "nhl": (2016, 2021)}[LG]
HELD = (2022, 2023, 2024, 2025, 2026)
cuts = {"nfl": (-4.0, -2.0, 2.0, 4.0), "ncaaf": (-8.0, -4.0, 4.0, 8.0), "nhl": (-0.5, -0.25, 0.25, 0.5)}[LG]

cells = lib.Cells()
hist = []
for g in fin:
    t = g["total"]
    if t is None:
        continue
    if len(hist) >= 300:
        med = statistics.median(hist[-300:])
        rel = t - med
        if LG == "nhl":
            band = ("LOW (0.5+ under the median)" if rel <= cuts[0] else "low (0.25-0.5 under)" if rel <= cuts[1]
                    else "HIGH (0.5+ over)" if rel >= cuts[3] else "high (0.25-0.5 over)" if rel >= cuts[2]
                    else "middle")
            raw = f"raw total {t:.1f}"
        else:
            band = (f"LOW ({-cuts[0]:.0f}+ under the median)" if rel <= cuts[0] else
                    f"low ({-cuts[1]:.0f}-{-cuts[0]:.0f} under)" if rel <= cuts[1] else
                    f"HIGH ({cuts[3]:.0f}+ over)" if rel >= cuts[3] else
                    f"high ({cuts[2]:.0f}-{cuts[3]:.0f} over)" if rel >= cuts[2] else "middle")
            raw = None
        for side, team, opp, o, won, home in lib.sides(g):
            s = g["season"]
            pl = lib.profit(won, lib.dec(o))
            labs = [band]
            if raw:
                labs.append(raw)
            if lib.dog_band(o):
                for lab in labs:
                    cells.add(f"{lab} | DOG ML", s, pl)
                    if o >= 200:
                        cells.add(f"{lab} | DOG ML +200..+350", s, pl)
            if -250 <= o <= -101:
                for lab in labs:
                    cells.add(f"{lab} | FAV ML", s, pl)
            if LG != "nhl" and g["sp"] is not None:
                spm = g["sp"] if home else -g["sp"]          # my spread (+ = I'm getting points)
                a = lib.ats(g, side)
                if spm > 0:
                    cells.add(f"{band} | ATS dog", s, a)
                    if spm >= 7:
                        cells.add(f"{band} | ATS dog 7+", s, a)
                        if lib.dog_band(o, 100, 1000):
                            cells.add(f"{band} | DOG ML, a 7+ point dog", s, pl)
                elif spm < 0:
                    cells.add(f"{band} | ATS fav", s, a)
    hist.append(t)
cells.dump(TAG, f"X1 (re-cut) {LG} - the side by the CLOSING total relative to the league's last-300 median; close only; "
           f"TRAIN {TRAIN[0]}-{TRAIN[1]}", TRAIN, HELD)
