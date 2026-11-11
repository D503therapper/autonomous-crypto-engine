"""S3 - THE COLLEGE NUMBER: opponent-adjusted yards per pass (by QB) / per carry / first downs per play / points,
re-fit weekly, the lower-division teams on their own level (sports_players.fbs_set, walk-forward); tuned on 2023
only (3 settings), 2024-26 held out. Error next to the closing spread, season by season."""
import os, pickle
import numpy as np
import splib as S
import ncaaf_model as M

o = S.Out("s3")
gs = M.games()
fin = {x["id"]: x for x in S.B.finals("ncaaf")}
GRID = [(12.0, 8.0, 150.0), (20.0, 8.0, 150.0), (30.0, 8.0, 150.0)]


def feats_for(cfg):
    return S.cached("ncaaffeat2_%g_%g_%g" % cfg, lambda: M.features(gs, tau=cfg[0], offw=cfg[1], lam_y=cfg[2]))


def row(nm, m, p, c):
    x = p - c
    b = float(x @ (m - c) / (x @ x))
    se = float(np.sqrt(((m - c - b * x) ** 2).sum() / (len(m) - 1) / (x @ x)))
    o.p("  %-17s %4d | %6.2f  %6.2f | %6.2f  %6.2f | %+.3f  %.3f | %.3f  %.2f"
        % (nm, len(m), np.abs(m - p).mean(), np.abs(m - c).mean(), np.sqrt(((m - p) ** 2).mean()),
           np.sqrt(((m - c) ** 2).mean()), b, se, np.corrcoef(p, c)[0, 1], np.abs(x).mean()))


o.p("games with a box 2021-26:", len(gs))
best = None
for cfg in GRID:
    f = feats_for(cfg)
    pred, _ = M.stage2(gs, f, qb="A")
    e = [(g["hs"] - g["as"]) - pred[g["id"]] for g in gs if g["id"] in pred and g["season"] == 2023 and g["id"] in fin and fin[g["id"]]["sp"] is not None]
    rm = float(np.sqrt(np.mean(np.square(e))))
    o.p("  tune (TAU weeks, off-season weeks, ridge)", cfg, "2023 RMSE %.3f n %d" % (rm, len(e)))
    if best is None or rm < best[0]:
        best = (rm, cfg)
cfg = best[1]
o.p("PICKED (2023 only):", cfg)
pickle.dump(cfg, open(os.path.join(S.CACHE, "ncaaf_cfg.pkl"), "wb"))
f = feats_for(cfg)
for qb in ("A", "P"):
    pred, w = M.stage2(gs, f, qb=qb)
    o.p("\nQB read %s - last fit's weights: %s" % (qb, {k: round(float(v), 2) for k, v in w.items()}))
    o.p("  season             n   | MAE model  close | RMSE model  close | weight on (model - close), se | corr | mean gap")
    tot = {}
    for s in range(2023, 2027):
        g2 = [g for g in gs if g["season"] == s and g["id"] in pred and g["id"] in fin and fin[g["id"]]["sp"] is not None]
        tot[s] = (np.array([g["hs"] - g["as"] for g in g2]), np.array([pred[g["id"]] for g in g2]),
                  np.array([-fin[g["id"]]["sp"] for g in g2]))
        row(str(s), *tot[s])
    row("2024-26 HELD OUT", *[np.concatenate([tot[s][i] for s in (2024, 2025, 2026)]) for i in range(3)])
o.save()
