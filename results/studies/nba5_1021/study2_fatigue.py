"""Study 2 - FATIGUE / SCHEDULE: back-to-backs, 3-in-4, 4-in-6, long trips, time zones, altitude, coming home.
Which spots does the close under-price, by side (dog / favorite)? Train 2018-22, blind 2023-26, baseline = the band."""
import pandas as pd
import numpy as np
from common import load, sides, grade, fmt, split, report, TRAIN, BLIND

rows = load()
df = pd.DataFrame(sides(rows))
df = df[(df.ml >= -150) & (df.ml <= 300)].copy()
df["kind"] = np.where(df.ml < 100, "fav", "dog")
df["ngames"] = df[["t_n_season", "o_n_season"]].min(axis=1)

spots = {
    # the side itself in the spot
    "me b2b": lambda d: d.t_b2b == 1,
    "opp b2b": lambda d: d.o_b2b == 1,
    "me rested(2+) vs opp b2b": lambda d: (d.o_b2b == 1) & (d.t_rest >= 2),
    "me b2b, opp rested 2+": lambda d: (d.t_b2b == 1) & (d.o_rest >= 2),
    "me 3-in-4": lambda d: d.t_n4 >= 3,
    "opp 3-in-4": lambda d: d.o_n4 >= 3,
    "me 4-in-6": lambda d: d.t_n6 >= 4,
    "opp 4-in-6": lambda d: d.o_n6 >= 4,
    "me 5-in-8": lambda d: d.t_n8 >= 5,
    "opp 5-in-8": lambda d: d.o_n8 >= 5,
    "me trip game 4+": lambda d: d.t_trip_game >= 4,
    "me trip game 5+": lambda d: d.t_trip_game >= 5,
    "opp trip game 4+": lambda d: d.o_trip_game >= 4,
    "opp trip game 5+": lambda d: d.o_trip_game >= 5,
    "me home after 4+ trip": lambda d: d.t_home_after >= 4,
    "opp home after 4+ trip": lambda d: d.o_home_after >= 4,
    "me home after 3+ trip": lambda d: d.t_home_after >= 3,
    "me away 2+ zones": lambda d: d.t_tz_cross >= 2,
    "me away 3 zones": lambda d: d.t_tz_cross >= 3,
    "opp away 2+ zones": lambda d: d.o_tz_cross >= 2,
    "opp away 3 zones": lambda d: d.o_tz_cross >= 3,
    "me east->west 2+ zones": lambda d: d.t_tz_dir <= -2,
    "me west->east 2+ zones": lambda d: d.t_tz_dir >= 2,
    "me moved 2+ zones since last game": lambda d: d.t_tz_move >= 2,
    "opp moved 2+ zones since last game": lambda d: d.o_tz_move >= 2,
    "me moved 2+ zones + b2b": lambda d: (d.t_tz_move >= 2) & (d.t_b2b == 1),
    "opp moved 2+ zones + b2b": lambda d: (d.o_tz_move >= 2) & (d.o_b2b == 1),
    "me in thin air (DEN/UTA away)": lambda d: d.t_alt == 1,
    "opp in thin air (I'm DEN/UTA home)": lambda d: d.o_alt == 1,
    "opp thin air + b2b": lambda d: (d.o_alt == 1) & (d.o_b2b == 1),
    "me rest 3+ vs opp rest 1": lambda d: (d.t_rest >= 3) & (d.o_rest <= 1),
    "me rest 1 vs opp rest 3+": lambda d: (d.t_rest <= 1) & (d.o_rest >= 3),
    "me rest 4+ (long layoff)": lambda d: d.t_rest >= 4,
    "me b2b both halves road (prev away, now away)": lambda d: (d.t_b2b == 1) & (d.t_prev_side == "away") & (d.is_home == 0),
    "me b2b second night at home after road": lambda d: (d.t_b2b == 1) & (d.t_prev_side == "away") & (d.is_home == 1),
    "opp b2b both road": lambda d: (d.o_b2b == 1) & (d.o_prev_side == "away") & (d.is_home == 1),
}
print("=== STUDY 2: fatigue / schedule spots, sides -150..+300, flat 1u at the close ===")
cells = 0
hits = []
for kind in ("dog", "fav"):
    base = df[df.kind == kind]
    btr, bbl = split(base)
    print(f"\n##### {kind.upper()}S  baseline TRAIN {fmt(grade(btr))}\n#####       baseline BLIND {fmt(grade(bbl))}")
    for name, fn in spots.items():
        cells += 1
        d = base[fn(base)]
        tr, bl = split(d)
        ga, gb = grade(tr, f"{kind} {name} TRAIN"), grade(bl, "BLIND")
        if ga.get("n", 0) < 60:
            continue
        mark = ""
        if ga["roi"] - grade(btr)["roi"] >= 4 and gb.get("n", 0) >= 50 and gb["roi"] - grade(bbl)["roi"] >= 4:
            mark = "  <== train AND blind beat the band"
            hits.append((kind, name))
        print(f"{fmt(ga)}\n   {fmt(gb)}{mark}")
print(f"\ncells: {cells}; expected false positives at 5%: ~{cells*0.05:.1f}; train+blind hits: {hits}")

print("\n--- games 1-10 cut (both teams under 10 games) for the main spots")
e = df[df.ngames < 10]
for kind in ("dog", "fav"):
    base = e[e.kind == kind]
    print(f"\n{kind} g1-10 baseline: " + report(base, "all"))
    for name in ("me b2b", "opp b2b", "me rested(2+) vs opp b2b", "me 3-in-4", "opp 3-in-4", "me trip game 4+", "opp trip game 4+",
                 "me away 2+ zones", "opp away 2+ zones", "me in thin air (DEN/UTA away)", "opp in thin air (I'm DEN/UTA home)",
                 "me home after 3+ trip", "opp home after 4+ trip"):
        d = base[spots[name](base)]
        if len(d) >= 30:
            print(report(d, f"{kind} g1-10 {name}"))

print("\n--- the 10/20 LEAD re-checked: favorite whose opponent is on its 5th+ road game or first home game after a 4+ trip")
fv = df[df.kind == "fav"]
lead = fv[(fv.o_trip_game >= 5) | (fv.o_home_after >= 4)]
print(report(lead, "LEAD fav", base=fv))
print(report(lead[lead.ngames < 10], "  g1-10"))
