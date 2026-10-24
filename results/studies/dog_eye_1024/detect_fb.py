"""Football dog-eye detectors: NFL and college dogs +100..+350 at the close (regular season + bowls as held). Train
2018-24, holdout 2025, 'now' 2026."""
import os
import pickle
import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
S = pd.DataFrame(pickle.load(open(os.path.join(HERE, "fb_sides.pkl"), "rb")))
S["dec"] = np.where(S.ml > 0, 1 + S.ml / 100, 1 + 100 / (-S.ml))
S["pnl"] = np.where(S.won, S.dec - 1, -1.0)
HOLD, NOW = 2025, 2026
CELLS = []


def grade(x, label, cell=True):
    tr, ho, nw = x[x.season < HOLD], x[x.season == HOLD], x[x.season == NOW]
    if len(tr) == 0:
        print(f"{label:62s} n=0")
        return
    by = tr.groupby("season").pnl.agg(["sum", "count"])
    up, tot = int((by["sum"] > 0).sum()), len(by)
    hz = f"{len(ho):4d} {ho.won.mean()*100:5.1f}% vs {ho.mp.mean()*100:5.1f}% ROI {ho.pnl.mean()*100:+6.1f}%" if len(ho) else "   0"
    nz = f"now n={len(nw)} {nw.won.mean()*100:.0f}% vs {nw.mp.mean()*100:.0f}% {nw.pnl.mean()*100:+.1f}%" if len(nw) else ""
    z = tr.pnl.mean() / (tr.pnl.std() / np.sqrt(len(tr))) if len(tr) > 1 and tr.pnl.std() > 0 else 0
    print(f"{label:62s} TRAIN n={len(tr):5d} win {tr.won.mean()*100:5.1f}% vs {tr.mp.mean()*100:5.1f}% ROI {tr.pnl.mean()*100:+6.1f}% z{z:+.1f} ({up}/{tot} up) | HOLD {hz} | {nz}")
    if cell:
        CELLS.append((label, len(tr), tr.pnl.mean(), up, tot, len(ho), ho.pnl.mean() if len(ho) else None, len(nw), nw.pnl.mean() if len(nw) else None))


for lg in ("nfl", "ncaaf"):
    print(f"\n===== {lg.upper()}")
    L = S[S.league == lg]
    D = L[(L.ml >= 100) & (L.ml <= 350)].copy()
    D["elo_gap"] = D.elo_p - D.mp
    grade(D, f"{lg} baseline: all dogs +100..+350", cell=False)
    for lo, hi in ((100, 150), (150, 200), (200, 250), (250, 351)):
        grade(D[(D.ml >= lo) & (D.ml < hi)], f"  band +{lo}..+{hi}", cell=False)
    p = lg + ": "
    for t in (0.05, 0.10, 0.15):
        grade(D[D.elo_gap >= t], p + f"Elo read {int(t*100)}+ pts over the price")
    grade(D[D.elo_p >= 0.5], p + "Elo says the dog is the better team")
    grade(D[(D.elo_p >= 0.5) & (D.ml >= 150)], p + "Elo says better, still +150 or longer")
    B = D[D.last_won.notna() & (D.last_same_season == True)]
    grade(B[(B.last_won == True) & (B.last_as_dog == True)], p + "won last game as a dog (an upset)")
    grade(B[(B.last_won == True) & (B.last_as_dog == True) & (B.ml >= 180)], p + "upset last game, still +180 or longer")
    grade(B[(B.last_won == True) & (B.last_opp_wp.fillna(0) >= 0.65) & (B.last_opp_g >= 4)], p + "beat a .650+ team (4+ games) last game")
    grade(B[(B.last_won == True) & (B.last_opp_elo >= 1600)], p + "beat an Elo 1600+ team last game")
    grade(B[(B.last_won == True) & (B.last_margin >= 14)], p + "won last game by 14+")
    grade(B[(B.last_won == True) & (B.last_margin >= 14) & (B.o_last_won == False)], p + "won by 14+ last game, favorite off a loss")
    grade(D[(D.o_last_won == False) & (D.o_last_same_season == True)], p + "favorite off a loss (control, built)")
    # records
    R = D[(D.g >= 4) & (D.o_g >= 4)]
    grade(R[(R.wp - R.o_wp) >= 0.2], p + "dog's record 20+ pts better than the favorite's (4+ games)")
    grade(R[(R.o_wp <= 0.4)], p + "the favorite has a losing record (.400-)")
    grade(R[(R.o_wp <= 0.4) & (R.wp >= 0.5)], p + "favorite .400- and the dog .500+")
    grade(R[(R.wp >= 0.75) & (R.ml >= 150)], p + "dog .750+ record, still +150 or longer")
    # last season, early
    Cx = D[(D.g <= 3) & D.ly_wp.notna() & D.o_ly_wp.notna()]
    grade(Cx, p + "early (g1-3) dogs with last-season records", cell=False)
    grade(Cx[(Cx.ly_wp - Cx.o_ly_wp) >= 0.15], p + "early: dog 15+ pts better LAST season")
    grade(Cx[(Cx.ly_wp - Cx.o_ly_wp) <= -0.3], p + "early: favorite 30+ pts better LAST season (brand)")
    grade(Cx[(Cx.ly_wp >= 0.6) & (Cx.o_ly_wp <= 0.45)], p + "early: dog .600+ last year, fav .450- last year")
    # rest
    grade(D[(D.rest >= 10) & (D.o_rest <= 7) & (D.rest.notna())], p + "dog off a bye vs a fav that played last week")
    grade(D[(D.rest <= 6) & (D.o_rest >= 7)], p + "dog on a short week")
    # the owner's eye score
    D2 = D.copy()
    D2["eye"] = (D2.elo_gap >= 0.08).astype(int) + ((D2.last_won == True) & (D2.last_as_dog == True)).astype(int) \
        + ((D2.g >= 4) & (D2.o_g >= 4) & ((D2.wp - D2.o_wp) >= 0.2)).astype(int) + ((D2.o_last_won == False) & (D2.o_last_same_season == True)).astype(int) \
        + ((D2.rest >= 10) & (D2.o_rest <= 7)).astype(int) + ((D2.g <= 3) & ((D2.ly_wp.fillna(0) - D2.o_ly_wp.fillna(0)) >= 0.15)).astype(int)
    for k in (1, 2, 3):
        grade(D2[D2.eye >= k], p + f"eye score {k}+")
    # the open (2023+): the same two best eyes at the open price - bet at the open
    O = L[L.op_mp.notna() & (L.ml >= 100)].copy()
    if len(O):
        O = O[(O.op_mp > 0) & (O.op_mp < 0.5)].copy()
        O["odec"] = 1 / O.op_mp * 0.98   # no-vig open price less ~2% vig (we hold no per-side open price with vig)
        print(f"  (open bets 2023+: {len(O)} dog sides at the open, graded at the no-vig open less 2% - a proxy)")

print(f"\nCELLS tried: {len(CELLS)} (~{len(CELLS)*0.05:.1f} chance hits at 5%)")
print("cells up in train AND holdout:")
for c in CELLS:
    if c[2] > 0 and c[6] is not None and c[6] > 0:
        print(f"  {c[0]}: train n={c[1]} {c[2]*100:+.1f}% {c[3]}/{c[4]} | hold n={c[5]} {c[6]*100:+.1f}% | now n={c[7]} {(c[8] or 0)*100:+.1f}%")
