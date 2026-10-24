"""The same eyes at the OPEN (2023-25 hold a real open): bet the dog at its opening price, graded at that price.
Train 2023-24, holdout 2025, now 2026."""
import os
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import sports_data as sd      # noqa: E402

HERE = os.path.dirname(__file__)
S = pd.DataFrame(pickle.load(open(os.path.join(HERE, "nba_sides.pkl"), "rb")))
games = sd.load_games("nba")
S = S[S.op_mp.notna()].copy()
S["oml"] = [int(games[g]["ml_home_open"] if s == "home" else games[g]["ml_away_open"]) for g, s in zip(S.gid, S.side)]
S["odec"] = np.where(S.oml > 0, 1 + S.oml / 100, 1 + 100 / (-S.oml))
S["pnl"] = np.where(S.won, S.odec - 1, -1.0)
HOLD, NOW = 2025, 2026
CELLS = []


def grade(x, label, cell=True):
    tr, ho, nw = x[x.season < HOLD], x[x.season == HOLD], x[x.season == NOW]
    if len(tr) == 0:
        print(f"{label:60s} n=0"); return
    by = tr.groupby("season").pnl.agg(["sum"])
    up, tot = int((by["sum"] > 0).sum()), len(by)
    hz = f"{len(ho):4d} {ho.won.mean()*100:5.1f}% vs {ho.op_mp.mean()*100:5.1f}% ROI {ho.pnl.mean()*100:+6.1f}%" if len(ho) else "   0"
    nz = f"now n={len(nw)} {nw.pnl.mean()*100:+.1f}%" if len(nw) else ""
    z = tr.pnl.mean() / (tr.pnl.std() / np.sqrt(len(tr))) if len(tr) > 1 else 0
    print(f"{label:60s} TRAIN n={len(tr):5d} win {tr.won.mean()*100:5.1f}% vs {tr.op_mp.mean()*100:5.1f}% ROI {tr.pnl.mean()*100:+6.1f}% z{z:+.1f} ({up}/{tot} up) | HOLD {hz} | {nz}")
    if cell:
        CELLS.append((label, len(tr), tr.pnl.mean(), up, tot, len(ho), ho.pnl.mean() if len(ho) else None))


D = S[(S.oml >= 100) & (S.oml <= 350)].copy()
D["elo_gap"] = D.elo_p - D.op_mp
grade(D, "OPEN baseline: dogs +100..+350 at the open", cell=False)
for t in (0.05, 0.08, 0.10):
    grade(D[D.elo_gap >= t], f"open: Elo read {int(t*100)}+ over the open")
T = D[D.talent.notna() & D.o_talent.notna()].copy()
T["tgap"] = T.talent - T.o_talent
# talent p with the same beta family (fit on seasons before - reuse ~0.025, home 0.5 - the walk-forward fits above)
T["talent_p"] = 1 / (1 + np.exp(-(-0.05 + 0.025 * T.tgap + 0.5 * T.is_home.astype(float))))
T["tal_gap"] = T.talent_p - T.op_mp
for t in (0.05, 0.08, 0.10):
    grade(T[T.tal_gap >= t], f"open: talent read {int(t*100)}+ over the open (roster so far)")
grade(T[T.tgap >= 0], "open: dog's roster talent >= the favorite's")
ST = D[D.stars.notna() & D.o_stars.notna()].copy()
ST["sgap"] = ST.stars - ST.o_stars
grade(ST[ST.sgap >= 1], "open: dog 1+ more star points (rotation)")
grade(ST[ST.sgap >= 2], "open: dog 2+ more star points")
grade(ST[ST.sgap >= 4], "open: dog 4+ more star points")
B = D[D.last_won.notna()]
grade(B[(B.last_won == True) & (B.last_as_dog == True)], "open: won last game as a dog")
grade(B[(B.last_won == True) & (B.last_as_dog == True) & (B.oml >= 180)], "open: upset last game, opened +180 or longer")
grade(B[(B.last_won == True) & (B.last_opp_elo >= 1560)], "open: beat an Elo 1560+ team last game")
C = D[(D.g <= 15) & D.ly_wp.notna() & D.o_ly_wp.notna()]
grade(C[(C.ly_wp - C.o_ly_wp) >= 0.10], "open: g1-15 dog 10+ better last season")
grade(D[(D.rest >= 2) & (D.o_rest == 1)], "open: rested dog vs fav on a b2b")
H = T.copy()
H["sgap"] = ST.set_index(["gid", "side"]).sgap.reindex(pd.MultiIndex.from_arrays([H.gid, H.side])).values
H["eye"] = (H.tal_gap >= 0.03).astype(int) + (H.sgap.fillna(0) >= 1).astype(int) + ((H.last_won == True) & (H.last_opp_elo.fillna(0) >= 1560)).astype(int) \
    + ((H.rest >= 2) & (H.o_rest == 1)).astype(int) + ((H.g <= 15) & ((H.ly_wp.fillna(0) - H.o_ly_wp.fillna(0)) >= 0.10)).astype(int) + (H.elo_gap >= 0.05).astype(int)
for k in (1, 2, 3):
    grade(H[H.eye >= k], f"open: eye score {k}+")
print(f"\nCELLS tried: {len(CELLS)} (~{len(CELLS)*0.05:.1f} chance hits)")
for c in CELLS:
    if c[2] > 0 and c[6] is not None and c[6] > 0:
        print(f"  up both: {c[0]}: train n={c[1]} {c[2]*100:+.1f}% {c[3]}/{c[4]} | hold n={c[5]} {c[6]*100:+.1f}%")
