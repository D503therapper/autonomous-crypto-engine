"""THE NFL PRO-STYLE NUMBER (the way Bob Stoll describes his): opponent-adjusted play-by-play efficiency, offence and
defence apart, pass and run apart, the QUARTERBACK his own piece of the passing game, a prior from the seasons before
that fades, small situational pieces on top - all WALK-FORWARD.

STAGE 1 (re-fit before every week, on games of EARLIER weeks only): four weighted ridge systems
    pass EPA / dropback   = mean + home + QB[q] + pass offence[team] - pass defence[opp]     (a row per QB per game)
    run  EPA / carry      = mean + home + run offence[team] - run defence[opp]
    pass / run SUCCESS rate, the same shape
    points margin         = home + team[t] - team[opp]
  each row weighted by its plays x exp(-age in weeks / TAU); an off-season counts OFFW weeks (the preseason prior:
  last season's games are still in the fit, at a discount that fades as this season's pile up); a QB with under 200
  career dropbacks also carries the 'green QB' column (backups / rookies are below average before they play).
STAGE 2 (re-fit before every season, on the seasons before it): the final margin on the matchup pieces
    pass matchup (home QB + offence vs away pass defence, minus the same for the away side), run matchup, the two
    success-rate matchups, the points-rating gap, the rest gap (days, capped), home field.
  -> the model's line. Tuned on 2016-19 only (TAU / OFFW / the ridge strength by the stage-2 error); 2020-26 held out.
Two QB reads: 'A' = the QB who actually started (a pro knows it by kickoff; a small look-ahead early in the week),
'P' = the QB of the team's last game (no look-ahead at all - the honest early-week number)."""
import math
from collections import defaultdict
import numpy as np
import splib as S

GREEN = 200


def _idx(pg):
    """week index: weeks run 1..22 inside a season; (season, week) -> ordinal used for ages (off-season added later)."""
    return {g["gid"]: (g["season"], g["week"]) for g in pg}


def age(now, then, offw):
    (s1, w1), (s0, w0) = now, then
    return (w1 - w0) if s1 == s0 else (w1 + (22 - w0) + offw + 30 * (s1 - s0 - 1))


def starters(pg):
    """per game: {team: (starter id - first to drop back with 5+ dropbacks or the first one, name)}"""
    out = {}
    for g in pg:
        d = {}
        for t, qs in g["qb"].items():
            big = [q for q in qs if q[2] >= 5]
            q = (big or qs or [(None, None)])[0]
            d[t] = (q[0], q[1])
        out[g["gid"]] = d
    return out


def fit_week(prior, now, tau, offw, lam, kind):
    """One stage-1 system on `prior` games. kind: 'pe' / 'ps' (pass EPA / success), 're' / 'rs', 'pts'.
    -> dict of pieces."""
    rows = []      # (cols..., y, w)
    teams, qbs = {}, {}

    def ti(t):
        return teams.setdefault(t, len(teams))

    def qi(q):
        return qbs.setdefault(q, len(qbs))
    for g in prior:
        a = age(now, (g["season"], g["week"]), offw)
        if a > 75:
            continue
        dw = math.exp(-a / tau)
        hf = 0.0 if g["neutral"] else 1.0
        if kind == "pts":
            m = max(-28.0, min(28.0, g["hs"] - g["as"]))
            rows.append((ti(g["home"]), ti(g["away"]), None, hf, 0.0, m, dw))
            continue
        for t, opp, h in ((g["home"], g["away"], hf), (g["away"], g["home"], -hf)):
            d = g["teams"][t]
            if kind[0] == "p":
                for q in g["qb"][t]:
                    n = q[2]
                    if n < 1:
                        continue
                    # the QB's own dropbacks: EPA from his rows; success split by his share of the team's
                    y = q[3] / n if kind == "pe" else d.get("ps", 0.0) / max(1.0, d.get("pn", 1.0))
                    rows.append((ti(t), ti(opp), qi(q[0]), h, 1.0 if g["_car"].get(q[0], 0) < GREEN else 0.0, y, dw * n))
            else:
                n = d.get("rn", 0.0)
                if n < 1:
                    continue
                y = d.get("re", 0.0) / n if kind == "re" else d.get("rs", 0.0) / n
                rows.append((ti(t), ti(opp), None, h, 0.0, y, dw * n))
    nt, nq = len(teams), len(qbs)
    if kind == "pts":
        X = np.zeros((len(rows), nt + 1))
        for i, r in enumerate(rows):
            X[i, r[0]] = 1
            X[i, r[1]] = -1
            X[i, nt] = r[3]
        b = S.ridge_w(X, [r[5] for r in rows], [r[6] for r in rows], lam, free=(nt,))
        return {"team": {t: b[i] for t, i in teams.items()}, "home": b[nt]}
    base = 2 * nt + nq
    X = np.zeros((len(rows), base + 3))
    for i, r in enumerate(rows):
        X[i, r[0]] = 1
        X[i, nt + r[1]] = -1
        if r[2] is not None:
            X[i, 2 * nt + r[2]] = 1
        X[i, base] = 1
        X[i, base + 1] = r[3]
        X[i, base + 2] = r[4]
    free = (base, base + 1, base + 2) if kind[0] == "p" else (base, base + 1)
    if kind[0] != "p":
        X = X[:, :base + 2]
    b = S.ridge_w(X, [r[5] for r in rows], [r[6] for r in rows], lam, free=free)
    return {"off": {t: b[i] for t, i in teams.items()}, "def": {t: b[nt + i] for t, i in teams.items()},
            "qb": {q: b[2 * nt + i] for q, i in qbs.items()}, "mu": b[base], "home": b[base + 1],
            "green": b[base + 2] if kind[0] == "p" else 0.0}


def features(pg, tau=14.0, offw=10.0, lam_e=200.0, lam_s=300.0, lam_p=6.0, first=2016):
    """-> {gid: {dPA, dPP (pass matchup with the actual / the previous starter), dR, dSA, dSP, dSR, dPts, rest,
    home, qbchg_h, qbchg_a, n_prior}} for every game from `first` on."""
    st = starters(pg)
    car_snapshot.clear()
    car = defaultdict(int)
    for g in pg:                       # career dropbacks BEFORE each game (from 2015 on)
        g["_car"] = {q[0]: car[q[0]] for qs in g["qb"].values() for q in qs}
        for qs in g["qb"].values():
            for q in qs:
                car[q[0]] += q[2]
    weeks = defaultdict(list)
    for g in pg:
        weeks[(g["season"], g["week"])].append(g)
    order = sorted(weeks)
    out = {}
    lastg = {}                          # team -> (date, starter id)
    done = []
    from datetime import date
    for wk in order:
        if wk[0] >= first and done:
            f = {k: fit_week(done, wk, tau, offw, lam, k)
                 for k, lam in (("pe", lam_e), ("re", lam_e), ("ps", lam_s), ("rs", lam_s), ("pts", lam_p))}
            for g in weeks[wk]:
                h, a = g["home"], g["away"]
                hf = 0.0 if g["neutral"] else 1.0
                row = {"home": hf}

                def passx(k, t, opp, q, c):
                    m = f[k]
                    return (m["qb"].get(q, 0.0) + (m["green"] if c < GREEN else 0.0)
                            + m["off"].get(t, 0.0) - m["def"].get(opp, 0.0))
                for tag, pick in (("A", lambda t: st[g["gid"]][t][0]), ("P", lambda t: (lastg.get(t) or (None, st[g["gid"]][t][0]))[1])):
                    qh, qa = pick(h), pick(a)
                    ch, ca = car_before(g, qh, car_snapshot), car_before(g, qa, car_snapshot)
                    row["dP" + tag] = passx("pe", h, a, qh, ch) - passx("pe", a, h, qa, ca) + 2 * hf * f["pe"]["home"]
                    row["dS" + tag] = passx("ps", h, a, qh, ch) - passx("ps", a, h, qa, ca) + 2 * hf * f["ps"]["home"]
                for k, nm in (("re", "dR"), ("rs", "dSR")):
                    m = f[k]
                    row[nm] = ((m["off"].get(h, 0.0) - m["def"].get(a, 0.0)) - (m["off"].get(a, 0.0) - m["def"].get(h, 0.0))
                               + 2 * hf * m["home"])
                row["dPts"] = f["pts"]["team"].get(h, 0.0) - f["pts"]["team"].get(a, 0.0)
                d0 = date.fromisoformat(g["date"])
                rst = []
                for t in (h, a):
                    lg_ = lastg.get(t)
                    dd = (d0 - date.fromisoformat(lg_[0])).days if lg_ else 7
                    rst.append(min(14, dd) if dd < 60 else 7)
                row["rest"] = rst[0] - rst[1]
                row["bye"] = (1 if rst[0] >= 13 else 0) - (1 if rst[1] >= 13 else 0)
                row["short"] = (1 if rst[0] <= 5 else 0) - (1 if rst[1] <= 5 else 0)
                row["qbchg_h"] = int(bool(lastg.get(h)) and lastg[h][1] != st[g["gid"]][h][0])
                row["qbchg_a"] = int(bool(lastg.get(a)) and lastg[a][1] != st[g["gid"]][a][0])
                row["green_h"] = int(g["_car"].get(st[g["gid"]][h][0], 0) < GREEN)
                row["green_a"] = int(g["_car"].get(st[g["gid"]][a][0], 0) < GREEN)
                out[g["gid"]] = row
        for g in weeks[wk]:
            for t in (g["home"], g["away"]):
                lastg[t] = (g["date"], st[g["gid"]][t][0])
            for qs in g["qb"].values():
                for q in qs:
                    car_snapshot[q[0]] += q[2]
        done.extend(weeks[wk])
    return out


car_snapshot = defaultdict(int)


def car_before(g, q, snap):
    """career dropbacks of q before game g (the actual passers' counts are stored on the game; anyone else = the
    running count)."""
    return g["_car"].get(q, snap.get(q, 0))


FEATS = {"full": ["dP", "dR", "dS", "dSR", "dPts", "rest", "home"],
         "epa": ["dP", "dR", "home"],
         "pts": ["dPts", "home"]}


def stage2(pg, feats, qb="A", cols="full", first_test=2018, lam=1.0):
    """Walk-forward by season: the margin on the matchup pieces, fit on the seasons before -> {gid: model home
    margin}; also the weights of the last fit."""
    names = FEATS[cols]

    def vec(r):
        return [r[n + qb] if n in ("dP", "dS") else r[n] for n in names]
    by = defaultdict(list)
    for g in pg:
        if g["gid"] in feats and g["reg"]:
            by[g["season"]].append(g)
    allg = defaultdict(list)
    for g in pg:
        if g["gid"] in feats:
            allg[g["season"]].append(g)
    pred, wts = {}, None
    for s in sorted(allg):
        if s < first_test:
            continue
        tr = [g for y in by if y < s for g in by[y]]
        X = np.array([vec(feats[g["gid"]]) for g in tr])
        y = np.array([g["hs"] - g["as"] for g in tr])
        sdv = X.std(axis=0)
        sdv[sdv == 0] = 1.0
        b = S.ridge_w(X / sdv, y, np.ones(len(y)), lam) / sdv
        wts = dict(zip(names, b))
        for g in allg[s]:
            pred[g["gid"]] = float(np.dot(vec(feats[g["gid"]]), b))
    return pred, wts
