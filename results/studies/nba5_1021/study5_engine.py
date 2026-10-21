"""Study 5 - ENGINE vs MARKET: the engine's own read (weights fit on the seasons before, ratings at game time,
move_w 0) against the close. Where it disagrees by X points, who wins? Moneyline value plays (-150..+300) and Locks."""
import pandas as pd
import numpy as np
from common import load, sides, grade, fmt, split, report, TRAIN, BLIND
from nba_engine import load_engine
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/wt")
import sports_model as sm

rows = load()
eng = load_engine()
df = pd.DataFrame(sides(rows))
df["own_h"] = df.gid.map(lambda g: eng.get(g, {}).get("own"))
df["fin_h"] = df.gid.map(lambda g: eng.get(g, {}).get("final"))
df = df.dropna(subset=["own_h"])
df["own"] = np.where(df.is_home == 1, df.own_h, 1 - df.own_h)
df["fin"] = np.where(df.is_home == 1, df.fin_h, 1 - df.fin_h)
df["dis"] = (df.own - df.mp) * 100          # own read minus the market, in points
df["ngames"] = df[["t_n_season", "o_n_season"]].min(axis=1)
# the engine's early-season shrink (sports.early_trust): the own read pulled to the market over games 0..10
w = (df.ngames / 10).clip(upper=1.0)
df["own_shrunk"] = 1 / (1 + np.exp(-(np.log(df.mp / (1 - df.mp)) + w * (np.log(df.own / (1 - df.own)) - np.log(df.mp / (1 - df.mp))))))
df["dis_shr"] = (df.own_shrunk - df.mp) * 100
band = df[(df.ml >= -150) & (df.ml <= 300)]

print("=== STUDY 5: engine own read vs the close (own weights fit on prior seasons; trust fitted ~0.05-0.08) ===")
# calibration: log loss own vs market vs blend, by season
for s, d in df[df.is_home == 1].groupby("season"):
    def ll(p):
        p = p.clip(1e-4, 1 - 1e-4)
        return -(d.win * np.log(p) + (1 - d.win) * np.log(1 - p)).mean()
    print(f"{s}: n={len(d)} logloss own {ll(d.own):.4f}  market {ll(d.mp):.4f}  blend {ll(d.fin):.4f}  own-shrunk {ll(d.own_shrunk):.4f}  | games1-10: own {ll(d[d.ngames<10].own):.4f} mkt {ll(d[d.ngames<10].mp):.4f} shr {ll(d[d.ngames<10].own_shrunk):.4f} (n={int((d.ngames<10).sum())})")

print("\n--- siding with the engine by disagreement band (own - market, points), all sides -150..+300 (band baseline below)")
cells = 0
for lo, hi in [(-100, -10), (-10, -5), (-5, -2), (-2, 2), (2, 5), (5, 8), (8, 12), (12, 100)]:
    cells += 1
    d = band[(band.dis >= lo) & (band.dis < hi)]
    print(report(d, f"dis {lo:+}..{hi:+}"))
print(report(band, "BASELINE all sides -150..+300"))

print("\n--- the same, by price band, own read over the price by 3+ / 5+ / 8+ (value plays)")
for plo, phi, nm in [(-150, -105, "fav -150..-105"), (100, 150, "dog +100..+150"), (150, 220, "dog +150..+220"), (220, 300, "dog +220..+300")]:
    pb = band[(band.ml >= plo) & (band.ml <= phi)]
    for th in (3, 5, 8):
        cells += 1
        print(report(pb[pb.dis >= th], f"{nm} own +{th}+ over"))
    print(report(pb, f"  baseline {nm}"))

print("\n--- the engine FIGHTING the side (own 3+ under the price) - should those sides lose?")
for plo, phi, nm in [(-150, -105, "fav"), (100, 300, "dog")]:
    pb = band[(band.ml >= plo) & (band.ml <= phi)]
    print(report(pb[pb.dis <= -3], f"{nm} fought (own 3+ under)"))
    print(report(pb[(pb.dis > -3) & (pb.dis < 3)], f"{nm} agreed within 3"))

print("\n--- LOCK test as the engine runs it: favorite -150..-105, own read >= 56% and >= the price")
fav = band[(band.ml >= -150) & (band.ml <= -105)]
lk = fav[(fav.own >= 0.56) & (fav.own >= fav.mp)]
print(report(lk, "Lock (own>=56%, beats price)", base=fav))
print(report(lk[lk.ngames < 10], "  games 1-10", base=fav[fav.ngames < 10]))
print(report(lk[lk.ngames >= 10], "  games 11+"))
for th in (0.58, 0.60):
    print(report(fav[(fav.own >= th) & (fav.own >= fav.mp)], f"Lock own>={th:.2f}"))
print(report(fav[(fav.own >= 0.56) & (fav.own >= fav.mp) & (fav.dis < 5)], "Lock, own within +5 of price"))
print(report(fav[(fav.own >= 0.56) & (fav.own >= fav.mp) & (fav.dis >= 5)], "Lock, own 5+ over price"))
print(report(fav[(fav.fin >= 0.56)], "blend (final_p) >= 56%"))
print(report(fav[(fav.own_shrunk >= 0.56) & (fav.own_shrunk >= fav.mp)], "Lock on the early-shrunk read"))
print(report(fav[(fav.own_shrunk >= 0.56) & (fav.own_shrunk >= fav.mp) & (fav.ngames < 10)], "  games 1-10 shrunk read"))

print("\n--- games 1-10 only: disagreement bands (raw own read) -150..+300")
e = band[band.ngames < 10]
for lo, hi in [(-100, -5), (-5, 5), (5, 100)]:
    cells += 1
    print(report(e[(e.dis >= lo) & (e.dis < hi)], f"g1-10 dis {lo:+}..{hi:+}"))
print(report(e, "  baseline g1-10"))
print(f"\ncells tried ~{cells + 10}; expected false positives at 5%: ~{(cells + 10) * 0.05:.1f}")
