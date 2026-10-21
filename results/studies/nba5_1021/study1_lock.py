"""Study 1 - NBA LOCK PROFILE: favorites -150..-105 at the close. Which engine-style cuts beat the no-vig price,
chosen on 2018-22, graded blind 2023-26? Plus the games 1-10 cut for everything."""
import itertools
import pandas as pd
import numpy as np
from common import load, sides, grade, fmt, split, report, TRAIN, BLIND

rows = load()
df = pd.DataFrame(sides(rows))
fav = df[(df.ml >= -150) & (df.ml <= -105)].copy()
fav["gap"] = fav.p_elo - fav.mp                   # Elo read minus the market, in win-chance points
fav["rest_d"] = fav.t_rest.clip(upper=5) - fav.o_rest.clip(upper=5)
fav["stage"] = pd.cut(fav[["t_n_season", "o_n_season"]].min(axis=1), [-1, 9, 19, 40, 60, 100], labels=["1-10", "11-20", "21-41", "42-61", "62+"])
fav["m5b"] = pd.cut(fav.t_m5.fillna(0), [-99, -5, 0, 5, 99], labels=["<-5", "-5..0", "0..5", "5+"])
fav["om5b"] = pd.cut(fav.o_m5.fillna(0), [-99, -5, 0, 5, 99], labels=["<-5", "-5..0", "0..5", "5+"])
fav["gapb"] = pd.cut(fav.gap, [-1, -0.10, -0.05, -0.02, 0.02, 0.05, 0.10, 1], labels=["<-10", "-10..-5", "-5..-2", "-2..2", "2..5", "5..10", "10+"])
fav["restb"] = pd.cut(fav.rest_d, [-9, -1.5, -0.5, 0.5, 1.5, 9], labels=["-2+", "-1", "0", "+1", "+2+"])
fav["band"] = pd.cut(fav.ml, [-151, -135, -120, -104], labels=["-150..-136", "-135..-121", "-120..-105"])

print("=== STUDY 1: favorites -150..-105, closing price ===")
print(report(fav, "ALL favs -150..-105"))
print(report(fav[fav.t_n_season < 10], "  games 1-10 (team's)"))

cuts = {
    "gapb": sorted(fav.gapb.dropna().unique(), key=str),
    "home": [0, 1],
    "opp_b2b": [0, 1],
    "own_b2b": [0, 1],
    "restb": sorted(fav.restb.dropna().unique(), key=str),
    "stage": sorted(fav.stage.dropna().unique(), key=str),
    "m5b": sorted(fav.m5b.dropna().unique(), key=str),
    "om5b": sorted(fav.om5b.dropna().unique(), key=str),
    "band": sorted(fav.band.dropna().unique(), key=str),
    "opp_trip5": [0, 1],
    "opp_home_after4": [0, 1],
}
fav["home"] = fav.is_home
fav["opp_b2b"] = fav.o_b2b
fav["own_b2b"] = fav.t_b2b
fav["opp_trip5"] = (fav.o_trip_game >= 5).astype(int)
fav["opp_home_after4"] = (fav.o_home_after >= 4).astype(int)

tr, bl = split(fav)
cells = 0
res = []
for k, vals in cuts.items():
    for v in vals:
        cells += 1
        a, b = tr[tr[k] == v], bl[bl[k] == v]
        ga, gb = grade(a, f"{k}={v} TRAIN"), grade(b, f"{k}={v} BLIND")
        res.append((k, v, ga, gb))
print(f"\n--- single cuts ({cells} cells); baseline TRAIN ROI {grade(tr)['roi']:+.1f}% BLIND {grade(bl)['roi']:+.1f}%")
for k, v, ga, gb in res:
    if ga.get("n", 0) >= 80:
        flag = " <== train+" if ga["roi"] > 2 else ""
        print(f"{fmt(ga)}\n   {fmt(gb)}{flag}")

# two-way combos among the cuts that were positive in train (chosen on train only)
print("\n--- two-way combos chosen on TRAIN (ROI > +3%, n >= 150), graded blind")
pos = [(k, v) for k, v, ga, gb in res if ga.get("n", 0) >= 150 and ga["roi"] > 1.0]
combo_cells = 0
for (k1, v1), (k2, v2) in itertools.combinations(pos, 2):
    if k1 == k2:
        continue
    combo_cells += 1
    a = tr[(tr[k1] == v1) & (tr[k2] == v2)]
    b = bl[(bl[k1] == v1) & (bl[k2] == v2)]
    if len(a) >= 150:
        ga, gb = grade(a, f"{k1}={v1} & {k2}={v2} TRAIN"), grade(b, "BLIND")
        if ga["roi"] > 3:
            print(f"{fmt(ga)}\n   {fmt(gb)}")
print(f"combo cells tried: {combo_cells}; total cells {cells + combo_cells}; expected false positives at 5%: ~{(cells + combo_cells) * 0.05:.1f}")

# the engine's own Lock logic proxy: Elo own read >= 56% and beats the price (own_agrees), no injuries in history
print("\n--- the engine's Lock proxy: Elo read >= 56% and read >= price (own_agrees)")
lk = fav[(fav.p_elo >= 0.56) & (fav.p_elo >= fav.mp)]
print(report(lk, "Elo-lock proxy", base=fav))
print(report(lk[lk.t_n_season < 10], "  games 1-10", base=fav[fav.t_n_season < 10]))
for lo in (0.58, 0.60, 0.62):
    print(report(fav[(fav.p_elo >= lo) & (fav.p_elo >= fav.mp)], f"Elo read >= {lo:.2f} & beats price"))
print("\n--- games 1-10 by Elo gap band (the window we're in)")
e = fav[fav.t_n_season < 10]
for v in cuts["gapb"]:
    print(report(e[e.gapb == v], f"games1-10 gap {v}"))
