"""11/3 DEEP: COLLEGE HOOPS EFFICIENCY MODEL - shared data + the walk-forward tempo-free adjusted-efficiency model.

Data (read-only on the repo; caches go to ~/.cache/d503_studies, never the repo):
  - every college hoops final on disk (data/sports/games/ncaab/*.csv, 2016-11 .. now) with ESPN's close (ML / spread /
    total) 2018-25 and ESPN's OPEN moneyline 2023-25 (no spread / total opens on disk);
  - team box scores (data/sports/teamstats/ncaab.jsonl + ncaab/*.jsonl): 30,920 games, the 2021-22 .. 2025-26 seasons,
    ~100% of finals; possessions = FGA - OREB + TO + 0.475 x FTA (each side), the game's = the mean of the two.
    Seasons 2016-20 have scores only: possessions there = the model's own tempo prediction (points-space fallback).
Seasons are named by the year they START (2018 = 2018-19). TRAIN = 2018-2022 starts, HELD OUT = 2023 / 2024 / 2025.

THE MODEL (walk-forward - each night's games are predicted only from games finished before that night):
  offensive efficiency of side A vs B = mu + O_A - D_B + hfa * venue   (venue +1 home, -1 road, 0 neutral)
  possessions                         = T0 + t_A + t_B
  solved each night by weighted ridge least squares over this season's earlier games (weight = 0.5 ** (age / halflife)),
  each team's O / D / t pulled toward a PRESEASON PRIOR (last season's final rating shrunk toward its conference mean)
  with the strength of `prior_games` games. margin = poss x (eff_A - eff_B) / 100, total = poss x (eff_A + eff_B) / 100.
"""
import csv
import glob
import json
import math
import os
import pickle
from collections import defaultdict

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
CACHE = os.environ.get("STUDY_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "d503_studies")
os.makedirs(CACHE, exist_ok=True)
TRAIN = (2018, 2019, 2020, 2021, 2022)
HELD = (2023, 2024, 2025)


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def nv(a, b):
    pa, pb = 1 / dec(a), 1 / dec(b)
    return pa / (pa + pb)


def season_of(start):
    y = int(start[:4])
    return y if int(start[5:7]) >= 7 else y - 1


def night_of(start):
    """US night index (UTC - 8h) so a 10 PM PT tip sits with its own day's games."""
    from datetime import datetime
    t = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
    return (t.toordinal() * 24 + t.hour - 8) // 24


def _split(s):
    a, b = s.split("-")
    return int(a), int(b)


def load_box():
    """{gid: {team id: dict(fgm, fga, tpm, tpa, ftm, fta, oreb, dreb, to, poss)}}"""
    out = {}
    files = [os.path.join(ROOT, "data/sports/teamstats/ncaab.jsonl")] + \
        sorted(glob.glob(os.path.join(ROOT, "data/sports/teamstats/ncaab/*.jsonl")))
    for fn in files:
        for line in open(fn):
            try:
                d = json.loads(line)
                tm = {}
                for tid, t in d["teams"].items():
                    fgm, fga = _split(t["fieldGoalsMade-fieldGoalsAttempted"])
                    tpm, tpa = _split(t["threePointFieldGoalsMade-threePointFieldGoalsAttempted"])
                    ftm, fta = _split(t["freeThrowsMade-freeThrowsAttempted"])
                    oreb, dreb = int(t["offensiveRebounds"]), int(t["defensiveRebounds"])
                    to = int(t.get("totalTurnovers") or t.get("turnovers") or 0)
                    tm[tid] = dict(fgm=fgm, fga=fga, tpm=tpm, tpa=tpa, ftm=ftm, fta=fta, oreb=oreb, dreb=dreb, to=to,
                                   poss=fga - oreb + to + 0.475 * fta)
                if len(tm) == 2:
                    out[d["gid"]] = tm
            except (KeyError, ValueError, TypeError):
                continue
    return out


def _first(ls):
    """First-half points from a line score "35,34" (None if missing)."""
    try:
        return int(str(ls).split(",")[0])
    except (TypeError, ValueError):
        return None


def load_games():
    rows = []
    for fn in sorted(glob.glob(os.path.join(ROOT, "data/sports/games/ncaab/*.csv"))):
        for r in csv.DictReader(open(fn)):
            if r["status"] != "final":
                continue
            hs, as_ = num(r["home_score"]), num(r["away_score"])
            if hs is None or as_ is None or (r.get("stype") or "2") not in ("2", "3"):
                continue
            if r["home_name"] in ("", None) or r["home"] == r["away"]:
                continue
            g = dict(id=r["id"], start=r["start"], season=season_of(r["start"]), night=night_of(r["start"]),
                     home=r["home"], away=r["away"], hn=r["home_name"], an=r["away_name"], hs=hs, as_=as_,
                     neutral=str(r.get("neutral")) == "1", stype=r.get("stype") or "2",
                     ml_h=num(r["ml_home"]), ml_a=num(r["ml_away"]), mlo_h=num(r["ml_home_open"]),
                     mlo_a=num(r["ml_away_open"]), spread=num(r["spread_home"]), sp_h_odds=num(r["spread_home_odds"]),
                     sp_a_odds=num(r["spread_away_odds"]), total=num(r["total"]), o_odds=num(r["over_odds"]),
                     u_odds=num(r["under_odds"]), h1_sp=num(r.get("h1_spread_home")),
                     h1_sp_h_odds=num(r.get("h1_spread_home_odds")), h1_sp_a_odds=num(r.get("h1_spread_away_odds")),
                     h1_ml_h=num(r.get("h1_ml_home")), h1_ml_a=num(r.get("h1_ml_away")),
                     h1_h=_first(r.get("ls_home")), h1_a=_first(r.get("ls_away")))
            rows.append(g)
    rows.sort(key=lambda g: (g["start"], g["id"]))
    seen, out = set(), []
    for g in rows:
        if g["id"] not in seen:
            seen.add(g["id"])
            out.append(g)
    return out


def data():
    """(games, box) cached."""
    fn = os.path.join(CACHE, "deep_cbb_data.pkl")
    if os.path.exists(fn):
        return pickle.load(open(fn, "rb"))
    gs, bx = load_games(), load_box()
    for g in gs:
        b = bx.get(g["id"])
        if b and g["home"] in b and g["away"] in b:
            h, a = b[g["home"]], b[g["away"]]
            g["poss"] = (h["poss"] + a["poss"]) / 2
            g["bh"], g["ba"] = h, a
        else:
            g["poss"] = None
    pickle.dump((gs, None), open(fn, "wb"))
    return gs, None


# ---------------------------------------------------------------- conferences (inferred from the schedule)
def conferences(gs):
    """{season: {team: conf key}} - teams that met home / road Jan 3 - Mar 1 and share 3+ opponents -> components.
    Known before the NEXT season (the prior uses last season's map only)."""
    by = defaultdict(lambda: defaultdict(set))
    for g in gs:
        md = g["start"][5:10]
        if g["stype"] != "2" or g["neutral"] or not ("01-03" <= md <= "03-01"):
            continue
        by[g["season"]][g["home"]].add(g["away"])
        by[g["season"]][g["away"]].add(g["home"])
    out = {}
    for s, adj in by.items():
        par = {t: t for t in adj}

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for a in adj:
            for b in adj[a]:
                if a < b and len(adj[a] & adj[b]) >= 3:
                    par[find(a)] = find(b)
        comp = defaultdict(set)
        for t in adj:
            comp[find(t)].add(t)
        out[s] = {t: (k if len(mem) >= 5 else None) for k, mem in comp.items() for t in mem}
    return out


# ---------------------------------------------------------------- the model
DEFAULT = dict(halflife=120.0, prior_games=6.0, prior_fade=0.5, shrink=0.70, conf_w=1.0, hfa=3.2, hfa_prior=2000.0,
               tempo_prior=6.0, tempo_shrink=0.75, poss_weight=False, luck3=0.3, mu0=104.0, t0=68.0,
               blow_cap=30.0, d1_min=10, nond1_w=1.0, prev2_w=0.2, lag=0, luckft=0.5)   # tuned on TRAIN (tune_log.txt)


_X0 = {}


def _spd(A, b):
    """Conjugate gradient warm-started from the last solve of the same size (the nightly systems barely change);
    falls back to a direct solve if it does not converge."""
    import scipy.linalg as sl
    from scipy.sparse.linalg import cg
    x0 = _X0.get(len(b))
    if x0 is not None:
        d = np.sqrt(np.diag(A))
        x, info = cg(A / d[:, None] / d[None, :], b / d, x0=x0 * d, rtol=1e-10, maxiter=400)
        if info == 0:
            x = x / d
            _X0[len(b)] = x
            return x
    x = sl.solve(A, b, assume_a='pos', check_finite=False)
    _X0[len(b)] = x
    return x


def _solve_eff(rows, nteam, prior_o, prior_d, lam_o, lam_d, hfa0, hfa_lam, mu_guess):
    """rows: arrays (off_idx, def_idx, venue, y, w). Params: [mu, hfa, O_0..O_n-1, D_0..D_n-1].
    y = mu + hfa*v + O_off - D_def. Ridge on O/D toward their priors, on hfa toward hfa0."""
    oi, di, v, y, w = rows
    P = 2 + 2 * nteam
    A = np.zeros((P, P))
    b = np.zeros(P)
    if len(y):
        cols = np.stack([np.zeros_like(oi), np.ones_like(oi), 2 + oi, 2 + nteam + di], axis=1)
        vals = np.stack([np.ones_like(v), v, np.ones_like(v), -np.ones_like(v)], axis=1)
        flat = (cols[:, :, None] * P + cols[:, None, :]).ravel()
        wv = (w[:, None, None] * vals[:, :, None] * vals[:, None, :]).ravel()
        A += np.bincount(flat, wv, P * P).reshape(P, P)
        b += np.bincount(cols.ravel(), (w[:, None] * vals * y[:, None]).ravel(), P)
    idx_o = np.arange(nteam) + 2
    idx_d = np.arange(nteam) + 2 + nteam
    A[idx_o, idx_o] += lam_o
    A[idx_d, idx_d] += lam_d
    b[idx_o] += lam_o * prior_o
    b[idx_d] += lam_d * prior_d
    A[1, 1] += hfa_lam
    b[1] += hfa_lam * hfa0
    A[0, 0] += 1e-3
    b[0] += 1e-3 * mu_guess
    x = _spd(A, b)
    return x[0], x[1], x[idx_o], x[idx_d]


def _solve_tempo(rows, nteam, prior_t, lam_t, t_guess):
    """poss = T0 + t_a + t_b."""
    ai, bi, y, w = rows
    P = 1 + nteam
    A = np.zeros((P, P))
    b = np.zeros(P)
    if len(y):
        cols = np.stack([np.zeros_like(ai), 1 + ai, 1 + bi], axis=1)
        flat = (cols[:, :, None] * P + cols[:, None, :]).ravel()
        A += np.bincount(flat, np.repeat(w, 9), P * P).reshape(P, P)
        b += np.bincount(cols.ravel(), np.repeat(w * y, 3), P)
    idx = np.arange(nteam) + 1
    A[idx, idx] += lam_t
    b[idx] += lam_t * prior_t
    A[0, 0] += 1e-3
    b[0] += 1e-3 * t_guess
    x = _spd(A, b)
    return x[0], x[idx]


def run(gs, conf, prm=None, seasons=None, keep_final=False, use_box=True):
    """Walk the seasons in order. Returns ({game id: prediction dict}, {season: final ratings}).
    prediction: mh (home margin), tot, poss, eh / ea (efficiencies), gn_h / gn_a (games played before), conf ids."""
    p = dict(DEFAULT)
    p.update(prm or {})
    by_season = defaultdict(list)
    for g in gs:
        by_season[g["season"]].append(g)
    preds = {}
    finals = {}
    prev = None          # last season's final: dict team -> (O, D, t), plus mu, T0, hfa
    prev2 = None         # two seasons ago
    for s in sorted(by_season):
        games = by_season[s]
        teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
        ix = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        # ------------------------------------------------ preseason prior
        po, pd_, pt = np.zeros(n), np.zeros(n), np.zeros(n)
        known = np.zeros(n, bool)
        hfa0 = p["hfa"]
        if prev is not None:
            cmap = conf.get(s - 1, {})
            cm = defaultdict(list)
            for t, (o, d, tt, ng) in prev["teams"].items():
                if cmap.get(t) is not None and ng >= p["d1_min"]:
                    cm[cmap[t]].append((o, d, tt))
            cmean = {k: tuple(np.mean([x[i] for x in v]) for i in range(3)) for k, v in cm.items()}
            small = [(o, d, tt) for t, (o, d, tt, ng) in prev["teams"].items() if ng < p["d1_min"]]
            sm = tuple(np.mean([x[i] for x in small]) for i in range(3)) if small else (-15.0, -10.0, 0.0)
            for t in teams:
                i = ix[t]
                if t in prev["teams"] and prev["teams"][t][3] >= p["d1_min"]:
                    o, d, tt, _ = prev["teams"][t]
                    if p["prev2_w"] and prev2 is not None and t in prev2["teams"] and prev2["teams"][t][3] >= p["d1_min"]:
                        o2, d2_, _, _ = prev2["teams"][t]
                        o = (1 - p["prev2_w"]) * o + p["prev2_w"] * o2
                        d = (1 - p["prev2_w"]) * d + p["prev2_w"] * d2_
                    c = cmean.get(cmap.get(t))
                    if c is None:
                        c = (0.0, 0.0, 0.0)
                    co = p["conf_w"] * c[0]
                    cd = p["conf_w"] * c[1]
                    po[i] = p["shrink"] * o + (1 - p["shrink"]) * co
                    pd_[i] = p["shrink"] * d + (1 - p["shrink"]) * cd
                    pt[i] = p["tempo_shrink"] * tt
                    known[i] = True
                else:
                    po[i], pd_[i], pt[i] = sm[0], sm[1], sm[2] * p["tempo_shrink"]
            hfa0 = prev["hfa"]
            mu_g, t_g = prev["mu"], prev["T0"]
        else:
            mu_g, t_g = p["mu0"], p["t0"]
        lam = np.where(known, p["prior_games"], 2.0)          # an unknown team's prior is weak
        lam_t = np.where(known, p["tempo_prior"], 2.0)
        # ------------------------------------------------ nights
        nights = sorted({g["night"] for g in games})
        by_night = defaultdict(list)
        for g in games:
            by_night[g["night"]].append(g)
        done = []                 # finished games this season
        gcount = np.zeros(n)
        mu, hfa, O, D = mu_g, hfa0, po.copy(), pd_.copy()
        T0, tt = t_g, pt.copy()
        hist = []
        for k_, nt in enumerate(nights):
            if done:
                ages = nt - np.array([g["night"] for g in done], float)
                w = 0.5 ** (ages / p["halflife"]) if p["halflife"] else np.ones(len(done))
                # rows
                hi = np.array([ix[g["home"]] for g in done])
                ai = np.array([ix[g["away"]] for g in done])
                v = np.array([0.0 if g["neutral"] else 1.0 for g in done])
                # possessions: observed, else the model's own tempo prediction at that time
                poss = np.array([g["poss"] if (use_box and g.get("poss")) else g["_poss_hat"] for g in done], float)
                ph = np.array([g["hs"] for g in done], float)
                pa = np.array([g["as_"] for g in done], float)
                if (p["luck3"] or p["luckft"]) and use_box:
                    ph = np.array([_luck(g, "h", p) for g in done])
                    pa = np.array([_luck(g, "a", p) for g in done])
                yh, ya = 100 * ph / poss, 100 * pa / poss
                if p["blow_cap"]:
                    # cap the efficiency margin's influence (blowout garbage time)
                    mid = (yh + ya) / 2
                    half = np.clip((yh - ya) / 2, -p["blow_cap"], p["blow_cap"])
                    yh, ya = mid + half, mid - half
                ww = w * (poss / 70.0 if p["poss_weight"] else 1.0)
                if p["nond1_w"] != 1.0:                       # games vs a team we had no D1 season for
                    nk = np.array([not (known[ix[g["home"]]] and known[ix[g["away"]]]) for g in done])
                    ww = np.where(nk, ww * p["nond1_w"], ww)
                lam_eff = lam * np.maximum(0.0, 1 - p["prior_fade"] * gcount / 30.0) if p["prior_fade"] else lam
                rows = (np.concatenate([hi, ai]), np.concatenate([ai, hi]), np.concatenate([v, -v]),
                        np.concatenate([yh, ya]), np.concatenate([ww, ww]))
                mu, hfa, O, D = _solve_eff(rows, n, po, pd_, lam_eff, lam_eff, hfa0, p["hfa_prior"], mu)
                tb = [j for j, g in enumerate(done) if use_box and g.get("poss")]
                if tb:
                    tb = np.array(tb)
                    T0, tt = _solve_tempo((hi[tb], ai[tb], poss[tb], w[tb]), n, pt, lam_t, T0)
            hist.append((nt, mu, hfa, O.copy(), D.copy(), T0, tt.copy()))
            if p["lag"]:
                # predict from the ratings as they stood after games up to night nt - 1 - lag (an OPEN posted before
                # the last `lag` nights' games could not see them)
                cand = [x for x in hist if x[0] <= nt - p["lag"]]
                _, mu_l, hfa_l, O_l, D_l, T0_l, tt_l = cand[-1] if cand else (None, mu_g, hfa0, po, pd_, t_g, pt)
            else:
                mu_l, hfa_l, O_l, D_l, T0_l, tt_l = mu, hfa, O, D, T0, tt
            for g in by_night[nt]:
                h, a = ix[g["home"]], ix[g["away"]]
                v = 0.0 if g["neutral"] else 1.0
                eh = mu_l + O_l[h] - D_l[a] + hfa_l * v
                ea = mu_l + O_l[a] - D_l[h] - hfa_l * v
                ps = T0_l + tt_l[h] + tt_l[a]
                g["_poss_hat"] = ps
                preds[g["id"]] = dict(mh=ps * (eh - ea) / 100, tot=ps * (eh + ea) / 100, poss=ps, eh=eh, ea=ea,
                                      gn_h=int(gcount[h]), gn_a=int(gcount[a]), em_h=O_l[h] + D_l[h], em_a=O_l[a] + D_l[a],
                                      hfa=hfa_l, kh=bool(known[h]), ka=bool(known[a]))
            for g in by_night[nt]:
                done.append(g)
                gcount[ix[g["home"]]] += 1
                gcount[ix[g["away"]]] += 1
        # ------------------------------------------------ the season's final ratings (for next year's prior)
        if done:
            ages = nights[-1] + 1 - np.array([g["night"] for g in done], float)
            w = 0.5 ** (ages / max(p["halflife"], 90.0)) if p["halflife"] else np.ones(len(done))
            hi = np.array([ix[g["home"]] for g in done])
            ai = np.array([ix[g["away"]] for g in done])
            v = np.array([0.0 if g["neutral"] else 1.0 for g in done])
            poss = np.array([g["poss"] if (use_box and g.get("poss")) else g["_poss_hat"] for g in done], float)
            lk = (p["luck3"] or p["luckft"]) and use_box
            yh = 100 * np.array([_luck(g, "h", p) if lk else g["hs"] for g in done]) / poss
            ya = 100 * np.array([_luck(g, "a", p) if lk else g["as_"] for g in done]) / poss
            rows = (np.concatenate([hi, ai]), np.concatenate([ai, hi]), np.concatenate([v, -v]),
                    np.concatenate([yh, ya]), np.concatenate([w, w]))
            mu, hfa, O, D = _solve_eff(rows, n, po, pd_, np.full(n, 1.0), np.full(n, 1.0), hfa0, p["hfa_prior"], mu)
            tb = np.array([j for j, g in enumerate(done) if use_box and g.get("poss")], int)
            if len(tb):
                T0, tt = _solve_tempo((hi[tb], ai[tb], poss[tb], w[tb]), n, pt, np.full(n, 1.0), T0)
            prev2 = prev
            prev = dict(teams={t: (O[ix[t]], D[ix[t]], tt[ix[t]], int(gcount[ix[t]])) for t in teams},
                        mu=mu, T0=T0, hfa=hfa)
            finals[s] = prev
    return preds, finals


LG3, LGFT = 0.338, 0.715      # D1 3-point / free-throw percentages (steady 2021-25: 33.6-34.0% / 71.4-72.2%)


def _luck(g, side, p):
    """Points with the shooting luck taken out: the 3-point percentage pulled luck3 of the way to the league's, the
    free-throw percentage luckft of the way (opponents can't defend free throws - pure luck for the defense)."""
    b = g.get("bh" if side == "h" else "ba")
    pts = g["hs"] if side == "h" else g["as_"]
    if not b:
        return pts
    if b["tpa"]:
        pts += 3 * p["luck3"] * (LG3 * b["tpa"] - b["tpm"])
    if b["fta"] and p["luckft"]:
        pts += p["luckft"] * (LGFT * b["fta"] - b["ftm"])
    return pts


# ---------------------------------------------------------------- market helpers
def ml_profit(odds, won):
    return (dec(odds) - 1) if won else -1.0


def ats_profit(x, odds=-110):
    if x == 0:
        return 0.0
    return (dec(odds) - 1) if x > 0 else -1.0


def logloss(p, y):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def phase(g):
    md = g["start"][5:10]
    if g["stype"] == "3" or md >= "03-01" and md < "07-01":
        return "march"
    if md >= "01-01" and md < "03-01":
        return "janfeb"
    return "novdec"
