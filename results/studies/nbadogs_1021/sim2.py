import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/nba5")
from common import grade, TRAIN, BLIND
import pandas as pd
D = pd.read_pickle("/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/nbadogs/dogs2.pkl")
b = lambda x: pd.Series(x, index=D.index).fillna(False).astype(int)
s1 = (b(D.total >= 235) + b(D.pm_margin <= -15) - b((D.is_home == 1) & D.t_n_season.between(30, 59)) - b(D.t_last_margin >= 15)
      - b(D.total <= 215) - b(D.o_trip_game >= 4) - b((D.is_home == 1) & (D.t_home_after >= 4)) - b(D.o_last_margin >= 20))
s2 = (b(D.f_prev_ot == True) - b(D.d_prev_blew == True) - b(D.d_prev_ot == True) - b(D.d_prev_pts >= 130) - b(D.f_prev_pts <= 95)
      - b(D.d_streak >= 3) - b((D.elo_pts >= -30) & (D.ml >= 200)) - b((D.o_rest - D.t_rest) >= 2) - b((D.t_n_season < 15) & (D.t_wp_last >= 0.55)))
def show(sc, nm):
    print("==", nm)
    for lo, hi, lab in ((2, 99, ">=+2"), (1, 1, "+1"), (0, 0, "0"), (-1, -1, "-1"), (-2, -2, "-2"), (-99, -3, "<=-3")):
        sub = D[(sc >= lo) & (sc <= hi)]
        out = []
        for k, ss in (("TRAIN", TRAIN), ("BLIND", BLIND)):
            x = sub[sub.season.isin(ss)]
            if len(x) == 0: out.append(f"{k} n=0"); continue
            r = grade(x, k); up = sum(v[1] > 0 for v in r["seasons"].values())
            out.append(f"{k} n={r['n']} win {r['win']}% vs {r['imp']}% ROI {r['roi']:+.1f}% ({up}/{len(r['seasons'])})")
        print(f"  {lab:5s} " + " | ".join(out))
show(s1, "batch 1 score (live now)"); show(s2, "batch 2 score alone"); show(s1 + s2, "batch 1 + 2 together")
