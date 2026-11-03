"""Scoring helpers: how close the model's margin / total get vs the close, and whether the model adds to the close."""
import numpy as np

import lib


def table(gs, preds, seasons, need_spread=True):
    rows = []
    for g in gs:
        if g["season"] not in seasons or g["id"] not in preds:
            continue
        if need_spread and g["spread"] is None:
            continue
        p = preds[g["id"]]
        rows.append((g, p))
    return rows


def margin_stats(rows):
    if not rows:
        return {}
    m = np.array([g["hs"] - g["as_"] for g, _ in rows])
    sp = np.array([-g["spread"] for g, _ in rows])
    md = np.array([p["mh"] for _, p in rows])
    X = np.stack([sp, md - sp], 1)
    b, *_ = np.linalg.lstsq(X, m, rcond=None)
    return dict(n=len(rows), rmse_mkt=float(np.sqrt(np.mean((m - sp) ** 2))),
                rmse_mod=float(np.sqrt(np.mean((m - md) ** 2))), w_mod=float(b[1]), w_mkt=float(b[0]),
                corr=float(np.corrcoef(md - sp, m - sp)[0, 1]))


def fit_w(rows):
    """OLS weight of (model - spread) on (result - spread)."""
    m = np.array([g["hs"] - g["as_"] for g, _ in rows])
    sp = np.array([-g["spread"] for g, _ in rows])
    d = np.array([p["mh"] for _, p in rows]) - sp
    return float(np.sum(d * (m - sp)) / np.sum(d * d))


def blended_rmse(rows, w):
    m = np.array([g["hs"] - g["as_"] for g, _ in rows])
    sp = np.array([-g["spread"] for g, _ in rows])
    d = np.array([p["mh"] for _, p in rows]) - sp
    return float(np.sqrt(np.mean((m - sp - w * d) ** 2))), float(np.sqrt(np.mean((m - sp) ** 2)))


def total_stats(rows):
    rows = [(g, p) for g, p in rows if g["total"] is not None]
    if not rows:
        return {}
    t = np.array([g["hs"] + g["as_"] for g, _ in rows])
    mk = np.array([g["total"] for g, _ in rows])
    md = np.array([p["tot"] for _, p in rows])
    d = md - mk
    w = float(np.sum(d * (t - mk)) / np.sum(d * d))
    return dict(n=len(rows), rmse_mkt=float(np.sqrt(np.mean((t - mk) ** 2))),
                rmse_mod=float(np.sqrt(np.mean((t - md) ** 2))), w_mod=w, bias_mod=float(np.mean(md - t)))


def report(gs, preds, label=""):
    out = []
    for s in list(lib.TRAIN) + list(lib.HELD):
        r = table(gs, preds, (s,))
        ms, ts = margin_stats(r), total_stats(r)
        if ms:
            out.append(f"{label} {s}: n {ms['n']} margin rmse mkt {ms['rmse_mkt']:.2f} model {ms['rmse_mod']:.2f} "
                       f"w_model {ms['w_mod']:+.3f} | total rmse mkt {ts.get('rmse_mkt', 0):.2f} model "
                       f"{ts.get('rmse_mod', 0):.2f} w {ts.get('w_mod', 0):+.3f} bias {ts.get('bias_mod', 0):+.2f}")
    return "\n".join(out)
