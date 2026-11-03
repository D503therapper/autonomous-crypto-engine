"""(a)-(d): does the efficiency model add to the close, and can it be bet? Usage: python analyze.py PREDS.pkl [label]
Every fit (calibration, blend weights, thresholds) is made on TRAIN (2018-22 starts) and read on the held-out
seasons 2023 / 2024 / 2025 apart."""
import math
import os
import pickle
import sys
from collections import defaultdict

import numpy as np

import lib

TR, HE = lib.TRAIN, lib.HELD


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def sig(z):
    return 1 / (1 + np.exp(-z))


def fit_logit(X, y, off=None, lam=1e-3, iters=50):
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    off = np.zeros(len(y)) if off is None else np.asarray(off, float)
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = sig(off + X @ w)
        g = X.T @ (p - y) + lam * w
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(len(w))
        st = np.linalg.solve(H, g)
        w -= st
        if np.max(np.abs(st)) < 1e-9:
            break
    return w


def tiers(gs, finals):
    """{(season, team): tier} from LAST season's final ratings: conferences (inferred from last season's schedule) ranked
    by their mean rating - top 7 'P' (power), next 8 'H' (high-mid), the bottom 4 'B' (SWAC / MEAC type), rest 'L'."""
    conf = lib.conferences(gs)
    out = {}
    for s in sorted(conf):
        if s not in finals:
            continue
        cm = defaultdict(list)
        for t, c in conf[s].items():
            if c is not None and t in finals[s]["teams"]:
                o, d, _, n = finals[s]["teams"][t]
                cm[c].append(o + d)
        ranked = sorted(cm, key=lambda c: -np.mean(cm[c]))
        lab = {}
        for i, c in enumerate(ranked):
            lab[c] = "P" if i < 7 else "H" if i < 15 else "B" if i >= len(ranked) - 4 else "L"
        for t, c in conf[s].items():
            if c is not None:
                out[(s + 1, t)] = lab[c]
    return out


def game_tier(tr, g):
    a, b = tr.get((g["season"], g["home"])), tr.get((g["season"], g["away"]))
    if a is None or b is None:
        return "nonD1"
    if a == b:
        return {"P": "power", "H": "highmid", "L": "low", "B": "bottom"}[a]
    if "P" in (a, b):
        return "power-vs-other"
    if "B" in (a, b):
        return "low/bottom-mix" if {"L", "B"} == {a, b} else "mid-vs-bottom"
    return "mid-vs-low"


def stage(g, p, season_start):
    d = g["night"] - season_start[g["season"]]
    if d <= 7:
        return "openwk"
    ph = lib.phase(g)
    return ph


class Cell:
    def __init__(self):
        self.by = defaultdict(list)

    def add(self, s, pl):
        self.by[s].append(pl)

    def line(self, name):
        def agg(ss):
            v = [x for s in ss for x in self.by.get(s, [])]
            return (len(v), (sum(v) / len(v)) if v else 0.0, v)
        tn, tr, tv = agg(TR)
        hn, hr, hv = agg(HE)
        up_t = sum(1 for s in TR if self.by.get(s) and sum(self.by[s]) > 0)
        nt = sum(1 for s in TR if self.by.get(s))
        up_h = sum(1 for s in HE if self.by.get(s) and sum(self.by[s]) > 0)
        nh = sum(1 for s in HE if self.by.get(s))
        z = 0.0
        if hn > 2:
            sd = np.std(hv)
            z = hr / (sd / math.sqrt(hn)) if sd > 0 else 0.0
        per = " ".join(f"{s}:{np.mean(self.by[s]):+.1%}/{len(self.by[s])}" for s in HE if self.by.get(s))
        return (f"{name:<46} TRAIN {tr:+6.1%} on {tn:5d} ({up_t}/{nt} up) | HELD {hr:+6.1%} on {hn:5d} ({up_h}/{nh} up, "
                f"z {z:+.1f}) [{per}]")


def main(path, label):
    gs, _ = lib.data()
    preds = pickle.load(open(path, "rb"))
    finals = pickle.load(open(path.replace(".pkl", "_finals.pkl"), "rb")) if os.path.exists(
        path.replace(".pkl", "_finals.pkl")) else None
    old = pickle.load(open(os.path.join(lib.CACHE, "deep_old_read.pkl"), "rb"))
    tr = tiers(gs, finals) if finals else {}
    season_start = {}
    for g in gs:
        season_start.setdefault(g["season"], g["night"])
    out = []
    P = lambda *a: out.append(" ".join(str(x) for x in a))  # noqa: E731
    P(f"=== {label}: {path}")
    rows = [g for g in gs if g["id"] in preds and g["season"] in TR + HE]
    # ---------------------------------------------------------------- calibration (fit on TRAIN)
    cal = [g for g in rows if g["season"] in TR and g["hs"] != g["as_"]]
    X = np.array([[preds[g["id"]]["mh"]] for g in cal])
    y = np.array([1.0 if g["hs"] > g["as_"] else 0.0 for g in cal])
    w_cal = fit_logit(np.hstack([np.ones((len(X), 1)), X]), y)
    P(f"calibration (TRAIN, every game incl. unpriced): P(home) = sig({w_cal[0]:+.3f} + {w_cal[1]:.4f} x margin)"
      f"  (= a normal sd of {1.7 / w_cal[1]:.1f} points)")

    def pmod(g):
        return float(sig(w_cal[0] + w_cal[1] * preds[g["id"]]["mh"]))

    # ---------------------------------------------------------------- (a) information beyond the close
    P("\n(a) DOES THE MODEL ADD TO THE CLOSE?")
    pr = [g for g in rows if g["ml_h"] is not None and g["ml_a"] is not None and g["hs"] != g["as_"]]
    for g in pr:
        g["_mk"] = lib.nv(g["ml_h"], g["ml_a"])
        g["_pm"] = pmod(g)
    def ll_block(sel, tag):
        trn = [g for g in sel if g["season"] in TR]
        Xt = np.array([[logit(g["_pm"]) - logit(g["_mk"])] for g in trn])
        yt = np.array([1.0 if g["hs"] > g["as_"] else 0.0 for g in trn])
        wb = fit_logit(Xt, yt, off=[logit(g["_mk"]) for g in trn])[0] if len(trn) > 50 else 0.0
        P(f"  [{tag}] TRAIN blend weight on (model - market) logit: {wb:+.3f} on {len(trn)}")
        for s in HE + ("all held",):
            hs = [g for g in sel if (g["season"] == s if s != "all held" else g["season"] in HE)]
            if not hs:
                continue
            yy = [1.0 if g["hs"] > g["as_"] else 0.0 for g in hs]
            mk = [g["_mk"] for g in hs]
            md = [g["_pm"] for g in hs]
            bl = [float(sig(logit(g["_mk"]) + wb * (logit(g["_pm"]) - logit(g["_mk"])))) for g in hs]
            od = [old[g["id"]][0] if old.get(g["id"]) and old[g["id"]][0] is not None else g["_mk"] for g in hs]
            oraw = [old[g["id"]][1] for g in hs]
            # the season's own best weight (diagnostic only - not usable)
            Xs = np.array([[logit(g["_pm"]) - logit(g["_mk"])] for g in hs])
            ws = fit_logit(Xs, yy, off=[logit(g["_mk"]) for g in hs])[0]
            P(f"  [{tag}] {s}: n {len(hs)} logloss market {lib.logloss(mk, yy):.4f} | model {lib.logloss(md, yy):.4f} "
              f"| old Elo raw {lib.logloss(oraw, yy):.4f} | OLD READ (Elo+early_trust) {lib.logloss(od, yy):.4f} | "
              f"market+model(w train) {lib.logloss(bl, yy):.4f} | season-own w {ws:+.3f}")
    ll_block(pr, "all games")
    for lo, hi in ((0, 3), (3, 6), (6, 10), (10, 20), (20, 99)):
        ll_block([g for g in pr if lo <= min(preds[g["id"]]["gn_h"], preds[g["id"]]["gn_a"]) < hi], f"games {lo}-{hi - 1}")
    # margin
    sp = [g for g in rows if g["spread"] is not None]
    trn = [g for g in sp if g["season"] in TR]
    d = np.array([preds[g["id"]]["mh"] + g["spread"] for g in trn])
    r = np.array([g["hs"] - g["as_"] + g["spread"] for g in trn])
    wm = float(np.sum(d * r) / np.sum(d * d))
    P(f"\n  margin: TRAIN OLS weight of (model - close spread) on (result - spread): {wm:+.3f} on {len(trn)}")
    for s in TR + HE:
        hs = [g for g in sp if g["season"] == s]
        d = np.array([preds[g["id"]]["mh"] + g["spread"] for g in hs])
        r = np.array([g["hs"] - g["as_"] + g["spread"] for g in hs])
        ws = float(np.sum(d * r) / np.sum(d * d))
        se = float(np.sqrt(np.mean((r - ws * d) ** 2) / np.sum(d * d)))
        P(f"  {s}: n {len(hs)} rmse close {np.sqrt(np.mean(r ** 2)):.3f} model {np.sqrt(np.mean((r - d) ** 2)):.3f} "
          f"close+{wm:.2f}x(model-close) {np.sqrt(np.mean((r - wm * d) ** 2)):.3f} | season weight {ws:+.3f} +/- {se:.3f}")
    tt = [g for g in rows if g["total"] is not None]
    trn = [g for g in tt if g["season"] in TR]
    d = np.array([preds[g["id"]]["tot"] - g["total"] for g in trn])
    r = np.array([g["hs"] + g["as_"] - g["total"] for g in trn])
    wt = float(np.sum(d * r) / np.sum(d * d))
    P(f"\n  totals: TRAIN weight of (model - close total): {wt:+.3f}")
    for s in TR + HE:
        hs = [g for g in tt if g["season"] == s]
        d = np.array([preds[g["id"]]["tot"] - g["total"] for g in hs])
        r = np.array([g["hs"] + g["as_"] - g["total"] for g in hs])
        ws = float(np.sum(d * r) / np.sum(d * d))
        se = float(np.sqrt(np.mean((r - ws * d) ** 2) / np.sum(d * d)))
        P(f"  {s}: n {len(hs)} rmse close {np.sqrt(np.mean(r ** 2)):.3f} model {np.sqrt(np.mean((r - d) ** 2)):.3f} "
          f"| season weight {ws:+.3f} +/- {se:.3f} | model bias {np.mean(d - r):+.2f}")
    # ---------------------------------------------------------------- (b) betting where the model disagrees
    P("\n(b) BETTING WHERE THE MODEL DISAGREES (flat 1u; ATS at the listed spread odds; ML at the close / open)")
    cells = defaultdict(Cell)
    for g in rows:
        p = preds[g["id"]]
        st = stage(g, p, season_start)
        ti = game_tier(tr, g)
        cuts = {"all": True, "st:" + st: True, "tier:" + ti: True,
                "early(<6g)": min(p["gn_h"], p["gn_a"]) < 6}
        if g["spread"] is not None and g["sp_h_odds"] and g["sp_a_odds"]:
            dd = p["mh"] + g["spread"]           # + = model likes home vs the number
            side_home = dd > 0
            res = (g["hs"] - g["as_"] + g["spread"]) * (1 if side_home else -1)
            pl = lib.ats_profit(res, g["sp_h_odds"] if side_home else g["sp_a_odds"])
            for n in (2, 3, 4, 5, 6, 8):
                if abs(dd) >= n:
                    for k, ok in cuts.items():
                        if ok:
                            cells[f"ATS |diff|>={n} {k}"].add(g["season"], pl)
            # dog / fav split at 4+
            if abs(dd) >= 4:
                fav = (g["spread"] < 0) == side_home
                cells[f"ATS |diff|>=4 model on the {'FAV' if fav else 'DOG'}"].add(g["season"], pl)
        if g["ml_h"] is not None and g["ml_a"] is not None and g["hs"] != g["as_"]:
            pm = pmod(g)
            mk = lib.nv(g["ml_h"], g["ml_a"])
            for side, pp, mm, odds, won in (("h", pm, mk, g["ml_h"], g["hs"] > g["as_"]),
                                             ("a", 1 - pm, 1 - mk, g["ml_a"], g["as_"] > g["hs"])):
                e = pp - mm
                band = "dog" if odds > 0 else "fav"
                if odds > 350 or odds < -400:
                    continue
                for E in (0.03, 0.05, 0.08, 0.12):
                    if e >= E:
                        for k, ok in cuts.items():
                            if ok:
                                cells[f"ML edge>={E:.2f} {band} {k}"].add(g["season"], lib.ml_profit(odds, won))
                if g["mlo_h"] is not None and g["mlo_a"] is not None:
                    mo = lib.nv(g["mlo_h"], g["mlo_a"]) if side == "h" else 1 - lib.nv(g["mlo_h"], g["mlo_a"])
                    oo = g["mlo_h"] if side == "h" else g["mlo_a"]
                    for E in (0.03, 0.05, 0.08):
                        if pp - mo >= E and -400 <= oo <= 350:
                            cells[f"OPEN ML edge>={E:.2f} {band} {'st:' + st}"].add(g["season"], lib.ml_profit(oo, won))
                            cells[f"OPEN ML edge>={E:.2f} {band} all"].add(g["season"], lib.ml_profit(oo, won))
        if g["total"] is not None and g["o_odds"] and g["u_odds"]:
            dt = p["tot"] - g["total"]
            over = dt > 0
            res = (g["hs"] + g["as_"] - g["total"]) * (1 if over else -1)
            pl = lib.ats_profit(res, g["o_odds"] if over else g["u_odds"])
            for n in (3, 5, 7, 10):
                if abs(dt) >= n:
                    for k, ok in cuts.items():
                        if ok:
                            cells[f"TOT |diff|>={n} {'OVER' if over else 'UNDER'} {k}"].add(g["season"], pl)
    for k in sorted(cells):
        c = cells[k]
        if sum(len(v) for v in c.by.values()) >= 60:
            P(cells[k].line(k))
    P(f"\n{len(cells)} cells looked at")
    txt = "\n".join(out)
    print(txt)
    return txt


if __name__ == "__main__":
    path = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(path)
    txt = main(path, label)
    if len(sys.argv) > 3:
        open(sys.argv[3], "w").write(txt + "\n")
