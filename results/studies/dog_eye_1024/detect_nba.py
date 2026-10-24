"""The dog-eye detectors on NBA dogs +100..+350 at the close. Train = every season before the holdout (2025-26);
2026-27 reported as 'now'. Flat 1u at the close."""
import os
import pickle
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
S = pd.DataFrame(pickle.load(open(os.path.join(HERE, "nba_sides.pkl"), "rb")))
S = S[S.ml.notna()].copy()
S["dec"] = np.where(S.ml > 0, 1 + S.ml / 100, 1 + 100 / (-S.ml))
S["pnl"] = np.where(S.won, S.dec - 1, -1.0)
HOLD = 2025
NOW = 2026
CELLS = []


def grade(x, label, cell=True):
    """n, win%, implied%, ROI, seasons up (train), holdout, now."""
    tr = x[x.season < HOLD]
    ho = x[x.season == HOLD]
    nw = x[x.season == NOW]
    if len(tr) == 0:
        print(f"{label:60s} n=0")
        return
    by = tr.groupby("season").pnl.agg(["sum", "count"])
    up = int((by["sum"] > 0).sum())
    tot = len(by)
    hz = f"{len(ho):4d} {ho.won.mean()*100:5.1f}% vs {ho.mp.mean()*100:5.1f}% ROI {ho.pnl.mean()*100:+6.1f}%" if len(ho) else "   0"
    nz = f"now n={len(nw)} {nw.pnl.mean()*100:+.1f}%" if len(nw) else ""
    z = tr.pnl.mean() / (tr.pnl.std() / np.sqrt(len(tr))) if len(tr) > 1 and tr.pnl.std() > 0 else 0
    print(f"{label:60s} TRAIN n={len(tr):5d} win {tr.won.mean()*100:5.1f}% vs {tr.mp.mean()*100:5.1f}% ROI {tr.pnl.mean()*100:+6.1f}% z{z:+.1f} ({up}/{tot} up) | HOLD {hz} | {nz}")
    if cell:
        CELLS.append((label, len(tr), tr.pnl.mean(), up, tot, len(ho), ho.pnl.mean() if len(ho) else None))


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


D = S[(S.ml >= 100) & (S.ml <= 350)].copy()
print("DOGS +100..+350", len(D), "seasons", sorted(D.season.unique()))
grade(D, "baseline: all dogs", cell=False)
for lo, hi in ((100, 150), (150, 200), (200, 250), (250, 350)):
    grade(D[(D.ml >= lo) & (D.ml < hi)], f"  band +{lo}..+{hi}", cell=False)

# ---- D: Elo gap by size (control - known dead)
D["elo_gap"] = D.elo_p - D.mp
for t in (0.05, 0.08, 0.10):
    grade(D[D.elo_gap >= t], f"Elo read {int(t*100)}+ pts over the price")

# ---- A: the roster talent vs the price (roster so far, last season's values; walk-forward scale per season)
T = D[D.talent.notna() & D.o_talent.notna()].copy()
T["tgap"] = T.talent - T.o_talent
# fit beta on seasons before each (logit of win on tgap + home), apply
T["talent_p"] = np.nan
for s in sorted(T.season.unique()):
    tr_ = S[(S.season < s) & S.talent.notna() & S.o_talent.notna()]
    if len(tr_) < 500:
        continue
    X = np.c_[np.ones(len(tr_)), (tr_.talent - tr_.o_talent).values, tr_.is_home.astype(float).values]
    y = tr_.won.astype(float).values
    w = np.zeros(3)
    for _ in range(25):
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (p - y)
        H = (X * (p * (1 - p))[:, None]).T @ X + 1e-3 * np.eye(3)
        w -= np.linalg.solve(H, g)
    m = T.season == s
    Xs = np.c_[np.ones(m.sum()), T.loc[m, "tgap"].values, T.loc[m, "is_home"].astype(float).values]
    T.loc[m, "talent_p"] = 1 / (1 + np.exp(-Xs @ w))
    print(f"  talent fit for {s}: beta {w[1]:.4f} home {w[2]:.3f} on {len(tr_)}")
T = T[T.talent_p.notna()]
T["tal_gap"] = T.talent_p - T.mp
print("talent-covered dogs", len(T), sorted(T.season.unique()))
grade(T, "talent set baseline", cell=False)
for t in (0.03, 0.05, 0.08, 0.10):
    grade(T[T.tal_gap >= t], f"talent read {int(t*100)}+ pts over the price (roster so far)")
grade(T[T.tal_gap <= -0.08], "talent read 8+ UNDER the price (fade?)")
# the owner's words: the dog's talent at least the favorite's
grade(T[T.tgap >= 0], "dog's roster talent >= the favorite's")
grade(T[T.tgap >= 0.05 * T.talent.abs().median()], "dog's talent clearly more (median+)")
# with tonight's box (game-day look-ahead; flagged)
TB = T[T.box_talent.notna() & T.o_box_talent.notna()].copy()
grade(TB[(TB.box_talent - TB.o_box_talent) >= 0], "[look-ahead] tonight's men: dog talent >= fav's")

# ---- stars gap
ST = D[D.stars.notna() & D.o_stars.notna()].copy()
ST["sgap"] = ST.stars - ST.o_stars
grade(ST, "stars set baseline", cell=False)
grade(ST[ST.sgap >= 1], "dog has 1+ more star points (rotation, honors before)")
grade(ST[ST.sgap >= 2], "dog has 2+ more star points")
grade(ST[(ST.sgap >= 1) & (ST.ml >= 150)], "  ...and +150 or longer")

# ---- B: just beat a good team and still a dog
B = D[D.last_won.notna()].copy()
good = (B.last_opp_wp.fillna(0) >= 0.6) & (B.o_g >= 0)
grade(B[(B.last_won == True) & (B.last_opp_wp >= 0.6) & (B.g >= 10)], "won last game vs a .600+ team (10+ games in)")
grade(B[(B.last_won == True) & (B.last_opp_elo >= 1560)], "won last game vs an Elo 1560+ team")
grade(B[(B.last_won == True) & (B.last_as_dog == True)], "won last game AS A DOG (an upset)")
grade(B[(B.last_won == True) & (B.last_as_dog == True) & (B.last_opp_elo >= 1560)], "upset an Elo 1560+ team last game")
grade(B[(B.last_won == True) & (B.last_as_dog == True) & (B.ml >= 180)], "upset last game, still +180 or longer")
grade(B[(B.last_won == True) & (B.last_margin >= 10) & (B.last_opp_elo >= 1540)], "beat an Elo 1540+ team by 10+ last game")
grade(B[(B.last_won == True) & (B.last_opp_same == True)], "beat THIS opponent last game (rematch, we won)")
grade(B[(B.last_won == False) & (B.last_opp_same == True)], "lost to THIS opponent last game (rematch, we lost)")

# ---- C: opening weeks vs last season
C = D[(D.g <= 15) & D.ly_wp.notna() & D.o_ly_wp.notna()].copy()
grade(C, "opening weeks (g1-15) dogs with both last-season records", cell=False)
grade(C[(C.ly_wp - C.o_ly_wp) >= 0.10], "g1-15: dog was 10+ pts better than the fav LAST season")
grade(C[(C.ly_wp - C.o_ly_wp) >= 0.0], "g1-15: dog was at least as good last season")
grade(C[(C.ly_wp - C.o_ly_wp) <= -0.25], "g1-15: fav was 25+ pts better last season (brand price?)")
grade(C[(C.o_ly_wp >= 0.6) & (C.o_wp.fillna(1) <= 0.4) & (C.o_g >= 5)], "g6-15: fav .600+ last year, under .400 now")
grade(C[(C.ly_wp <= 0.4) & (C.wp.fillna(0) >= 0.6) & (C.g >= 5)], "g6-15: dog .400- last year, .600+ now")
# the favorite's roster talent fell from last season's level (its men now vs the team's wp last year)
CT = C[C.o_talent.notna()].copy()
if len(CT):
    med = CT.o_talent.median()
    grade(CT[(CT.o_ly_wp >= 0.55) & (CT.o_talent <= med)], "g1-15: fav .550+ last year but its roster talent now is below median")

# ---- E: favorite missing starters (box - a game-day fact; the report would say most of it)
E = D[D.o_box_starters_out.notna()].copy()
grade(E, "box set baseline", cell=False)
grade(E[E.o_box_starters_out >= 1], "[game-day] fav missing 1+ usual starters")
grade(E[E.o_box_starters_out >= 2], "[game-day] fav missing 2+ usual starters")
grade(E[E.o_box_rot_out >= 2], "[game-day] fav missing 2+ of its top-8 by minutes")
E2 = E[E.op_mp.notna()].copy()
E2["move_to_dog"] = E2.mp - E2.op_mp
grade(E2[(E2.o_box_starters_out >= 2) & (E2.move_to_dog < 0.02)], "[game-day] fav missing 2+ starters, line moved <2 pts to the dog")
grade(E2[(E2.o_box_starters_out >= 2) & (E2.move_to_dog >= 0.02)], "[game-day] fav missing 2+ starters, line moved 2+ to the dog")
grade(E[(E.o_box_starters_out >= 2) & (E.box_starters_out == 0)], "[game-day] fav missing 2+ starters, dog whole")
# the Hawks angle: the favorite when the DOG is missing 2+ starters (favorites -100..-200)
F = S[(S.ml <= -100) & (S.ml >= -200) & S.o_box_starters_out.notna()].copy()
grade(F, "favorites -100..-200 (box set)", cell=False)
grade(F[F.o_box_starters_out >= 2], "[game-day] favorite -100..-200 vs a dog missing 2+ starters")
grade(F[(F.o_box_starters_out >= 2) & (F.box_starters_out == 0)], "[game-day] ...and the favorite whole")

# ---- F: rest (control)
grade(D[(D.rest >= 2) & (D.o_rest == 1)], "rested dog vs a favorite on a back-to-back (built +3)")
grade(D[(D.rest >= 3) & (D.o_rest == 1)], "dog 3+ days rest vs fav on a b2b")

# ---- G: a combined 'talent-adjusted fair line' walk-forward
G = D[D.talent.notna() & D.o_talent.notna() & D.stars.notna() & D.o_stars.notna()].copy()
G["fair"] = np.nan
feats = lambda x: np.c_[np.ones(len(x)), logit(x.elo_p.values), (x.talent - x.o_talent).values, (x.stars - x.o_stars).values,  # noqa: E731
                        x.is_home.astype(float).values, (x.rest.fillna(2).clip(0, 5) - x.o_rest.fillna(2).clip(0, 5)).values,
                        ((x.wp.fillna(0.5) - x.o_wp.fillna(0.5)) * np.minimum(x.g, 20) / 20).values]
for s in sorted(G.season.unique()):
    tr_ = S[(S.season < s) & S.talent.notna() & S.o_talent.notna() & S.stars.notna() & S.o_stars.notna()]
    if len(tr_) < 800:
        continue
    X, y = feats(tr_), tr_.won.astype(float).values
    w = np.zeros(X.shape[1])
    for _ in range(25):
        p = 1 / (1 + np.exp(-X @ w))
        H = (X * (p * (1 - p))[:, None]).T @ X + 1.0 * np.eye(X.shape[1])
        w -= np.linalg.solve(H, X.T @ (p - y) + 1.0 * w)
    m = G.season == s
    G.loc[m, "fair"] = 1 / (1 + np.exp(-feats(G[m]) @ w))
    print(f"  fair-line fit {s} on {len(tr_)}: w={np.round(w, 3)}")
G = G[G.fair.notna()]
G["fgap"] = G.fair - G.mp
grade(G, "fair-line set baseline", cell=False)
for t in (0.03, 0.05, 0.08):
    grade(G[G.fgap >= t], f"talent-adjusted fair line {int(t*100)}+ pts over the price")
grade(G[G.fgap <= -0.05], "fair line 5+ UNDER the price")

# ---- H: the owner's eye as a point score
H = D.copy()
H["eye"] = 0
tal_gap = T.set_index(["gid", "side"]).tal_gap
H = H.set_index(["gid", "side"])
H["tal_gap"] = tal_gap
H["sgap"] = ST.set_index(["gid", "side"]).sgap
H = H.reset_index()
H["eye"] += (H.tal_gap.fillna(0) >= 0.03).astype(int)
H["eye"] += (H.sgap.fillna(0) >= 1).astype(int)
H["eye"] += ((H.last_won == True) & (H.last_opp_elo.fillna(0) >= 1560)).astype(int)
H["eye"] += ((H.rest >= 2) & (H.o_rest == 1)).astype(int)
H["eye"] += ((H.g <= 15) & ((H.ly_wp.fillna(0) - H.o_ly_wp.fillna(0)) >= 0.10)).astype(int)
H["eye"] += (H.elo_gap >= 0.05).astype(int)
HH = H[H.tal_gap.notna()]
grade(HH, "eye-score set baseline", cell=False)
for k in (1, 2, 3):
    grade(HH[HH.eye >= k], f"eye score {k}+ (talent / stars / beat a good team / rest / last year / Elo)")
grade(HH[HH.eye == 0], "eye score 0")

# ---- the money-ran-away interplay (2023+ opens): does any eye rescue a drifted dog?
M = HH[HH.op_mp.notna()].copy()
M["drift_out"] = M.op_mp - M.mp
grade(M[M.drift_out >= 0.03], "dog drifted out 3+ pts open->close (the Mavs case)", cell=False)
grade(M[(M.drift_out >= 0.03) & (M.eye >= 2)], "  ...with eye score 2+")
grade(M[(M.drift_out >= 0.03) & (M.tal_gap >= 0.05)], "  ...with talent read 5+ over")
grade(M[(M.drift_out <= -0.03)], "dog the money came TO (3+ pts)", cell=False)
grade(M[(M.drift_out <= -0.03) & (M.eye >= 2)], "  ...with eye score 2+")

print(f"\nCELLS tried: {len(CELLS)} (~{len(CELLS)*0.05:.1f} chance hits at 5%)")
print("cells up in train (ROI>0) AND holdout (ROI>0):")
for c in CELLS:
    if c[2] > 0 and c[6] is not None and c[6] > 0:
        print(f"  {c[0]}: train n={c[1]} {c[2]*100:+.1f}% {c[3]}/{c[4]} | hold n={c[5]} {c[6]*100:+.1f}%")
