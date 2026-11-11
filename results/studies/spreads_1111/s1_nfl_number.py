"""S1 - THE NFL NUMBER: tune on 2017-19 only, then how good is it, season by season, next to the closing spread?
Error vs the final margin (mean absolute / RMSE), and the weight the result puts on (my number - the line)."""
import math
import numpy as np
import splib as S
import nfl_model as M

o = S.Out("s1")
pg = S.pbp_games()
GRID = [(tau, offw, le) for tau in (8.0, 14.0, 24.0) for offw in (6.0, 14.0) for le in (120.0, 300.0)]


def feats_for(cfg):
    tau, offw, le = cfg
    return S.cached("nflfeat_%g_%g_%g" % cfg, lambda: M.features(pg, tau=tau, offw=offw, lam_e=le, lam_s=le * 1.5))


def err(pred, seasons):
    e = [(g["hs"] - g["as"]) - pred[g["gid"]] for g in pg if g["gid"] in pred and g["season"] in seasons and g["reg"]]
    return sum(abs(x) for x in e) / len(e), math.sqrt(sum(x * x for x in e) / len(e)), len(e)


def row(nm, m, p, c):
    x = p - c
    b = float(x @ (m - c) / (x @ x))
    se = float(np.sqrt(((m - c - b * x) ** 2).sum() / (len(m) - 1) / (x @ x)))
    o.p("  %-17s %4d | %6.2f  %6.2f | %6.2f  %6.2f | %+.3f  %.3f | %.3f  %.2f"
        % (nm, len(m), np.abs(m - p).mean(), np.abs(m - c).mean(), np.sqrt(((m - p) ** 2).mean()),
           np.sqrt(((m - c) ** 2).mean()), b, se, np.corrcoef(p, c)[0, 1], np.abs(x).mean()))


if __name__ == "__main__":
    o.p("TUNING on 2017-19 only (stage 2 fit on the seasons before each): (TAU weeks, off-season weeks, ridge) -> MAE / RMSE")
    best = None
    for cfg in GRID:
        f = feats_for(cfg)
        pred, _ = M.stage2(pg, f, qb="A", cols="full", first_test=2017)
        mae, rmse, n = err(pred, (2017, 2018, 2019))
        o.p("  ", cfg, "MAE %.3f RMSE %.3f n %d" % (mae, rmse, n))
        if best is None or rmse < best[0]:
            best = (rmse, cfg)
    cfg = best[1]
    o.p("PICKED (by 2017-19 RMSE):", cfg)
    import os
    import pickle
    pickle.dump(cfg, open(os.path.join(S.CACHE, "nfl_cfg.pkl"), "wb"))
    f = feats_for(cfg)
    for cols in ("full", "epa", "pts"):
        for qb in ("A", "P"):
            pred, w = M.stage2(pg, f, qb=qb, cols=cols, first_test=2018)
            o.p("\nMODEL %s / QB read %s - last fit's weights: %s" % (cols, qb, {k: round(v, 2) for k, v in w.items()}))
            o.p("  season             n   | MAE model  close | RMSE model  close | weight on (model - close), se | corr | mean gap")
            tot = {}
            for s in range(2018, 2027):
                gs = [g for g in pg if g["season"] == s and g["gid"] in pred and g["close"] is not None]
                tot[s] = (np.array([g["hs"] - g["as"] for g in gs]), np.array([pred[g["gid"]] for g in gs]),
                          np.array([-g["close"] for g in gs]))
                row(str(s), *tot[s])
            for nm, ss in (("2018-19 (tuned)", (2018, 2019)), ("2020-26 HELD OUT", range(2020, 2027))):
                row(nm, *[np.concatenate([tot[s][i] for s in ss]) for i in range(3)])
    o.save()
