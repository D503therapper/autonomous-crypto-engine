"""THE COLLEGE FOOTBALL PRO-STYLE NUMBER. No public keyless play-by-play for college, so the pieces come from our
own box scores (2021-26): yards per pass (per QUARTERBACK, from the player box) and yards per carry, offence and
defence apart, each compensated for the opponents faced (a weighted ridge re-fit before every week on earlier games,
last season still in at a fading discount = the preseason prior), first downs per play (the success-rate stand-in),
an opponent-adjusted points rating, rest. Stage 2 (the margin on the matchup pieces) re-fit before every season on the
seasons before it. 2021 = the prior only; 2022 = stage 2's first fit; test 2023-26."""
import json, math
from collections import defaultdict
from datetime import date
import numpy as np
import splib as S

B, L = S.B, S.L
GREEN = 120          # pass attempts


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def games():
    """Finished college games 2021-26 with a team box: [{id, start, date, season, wk, home, away, hs, as, neutral,
    stype, box: {team: {pa, py, ra, ry, fd, pl}}, qb: {team: [(pid, name, att, yds)] most attempts first}}]."""
    def mk():
        import sports_roster as sr
        tb = L.teambox("ncaaf")
        qbs = defaultdict(lambda: defaultdict(list))
        for r in sr.load("ncaaf"):
            if r.get("group") != "passing":
                continue
            try:
                st = json.loads(r["stats"] or "{}")
                ca = L.pair(st.get("completions/passingAttempts"), "/")
                yd = _f(st.get("passingYards"))
            except ValueError:
                continue
            if ca and yd is not None and ca[1] >= 1:
                qbs[r["gid"]][r["team"]].append((r["pid"], r["player"], ca[1], yd))
        out = []
        for g in B.all_finals("ncaaf"):
            if g["season"] < 2021 or g["id"] not in tb:
                continue
            box = {}
            for t in (g["home"], g["away"]):
                x = tb[g["id"]].get(t) or {}
                ca = L.pair(x.get("completionAttempts"), "/")
                v = {"pa": ca[1] if ca else None, "py": _f(x.get("netPassingYards")), "ra": _f(x.get("rushingAttempts")),
                     "ry": _f(x.get("rushingYards")), "fd": _f(x.get("firstDowns"))}
                if any(z is None for z in v.values()) or v["pa"] + v["ra"] < 20:
                    box = None
                    break
                box[t] = v
            if not box:
                continue
            d = date.fromisoformat(g["start"][:10])
            out.append(dict(g, date=d.isoformat(), wk=(d.toordinal() - 2) // 7, box=box,
                            qb={t: sorted(qbs[g["id"]].get(t, []), key=lambda q: -q[2]) for t in (g["home"], g["away"])}))
        out.sort(key=lambda g: g["start"])
        return out
    return S.cached("ncaaf_games", mk)


def age(now_g, g, offw):
    """age in weeks of game g seen from week `now_g` (wk ordinal, season): an off-season (~33 weeks) counts offw."""
    wk, season = now_g
    a = wk - g["wk"]
    gap = season - g["season"]
    return max(a - 33 * gap + offw * gap, offw * gap) if gap else a


def fit(prior, now, tau, offw, lam, kind, fbs=None):
    """One weighted ridge system. `fbs` (the FBS teams in force, walk-forward) gives the lower-division teams their own
    unpenalised level - without it a ridge pulls an FCS team to the FBS average and a 45-point tune-up reads like a
    45-point win over a real team."""
    rows, teams, qbs = [], {}, {}

    def low(t):
        return 1.0 if (fbs is not None and t not in fbs) else 0.0

    def ti(t):
        return teams.setdefault(t, len(teams))

    def qi(q):
        return qbs.setdefault(q, len(qbs))
    for g in prior:
        a = age(now, g, offw)
        if a > 40 + offw:
            continue
        dw = math.exp(-a / tau)
        hf = 0.0 if g["neutral"] else 1.0
        if kind == "pts":
            rows.append((ti(g["home"]), ti(g["away"]), None, hf, 0.0, max(-35.0, min(35.0, g["hs"] - g["as"])), dw))
            continue
        for t, opp, h in ((g["home"], g["away"], hf), (g["away"], g["home"], -hf)):
            x = g["box"][t]
            if kind == "py":
                qs = g["qb"][t]
                if qs:
                    for q in qs:
                        rows.append((ti(t), ti(opp), qi(q[0]), h, 1.0 if g["_car"].get(q[0], 0) < GREEN else 0.0,
                                     max(-2.0, min(20.0, q[3] / q[2])), dw * q[2]))
                elif x["pa"] >= 1:
                    rows.append((ti(t), ti(opp), None, h, 0.0, x["py"] / x["pa"], dw * x["pa"]))
            elif kind == "ry":
                if x["ra"] >= 1:
                    rows.append((ti(t), ti(opp), None, h, 0.0, x["ry"] / x["ra"], dw * x["ra"]))
            else:   # fd: first downs per play
                n = x["pa"] + x["ra"]
                rows.append((ti(t), ti(opp), None, h, 0.0, x["fd"] / n, dw * n))
    nt, nq = len(teams), len(qbs)
    if kind == "pts":
        X = np.zeros((len(rows), nt + 2))
        inv = {i: t for t, i in teams.items()}
        for i, r in enumerate(rows):
            X[i, r[0]] = 1
            X[i, r[1]] = -1
            X[i, nt] = r[3]
            X[i, nt + 1] = low(inv[r[0]]) - low(inv[r[1]])
        b = S.ridge_w(X, [r[5] for r in rows], [r[6] for r in rows], lam, free=(nt, nt + 1))
        return {"team": {t: b[i] + low(t) * b[nt + 1] for t, i in teams.items()}, "home": b[nt], "low": b[nt + 1]}
    base = 2 * nt + nq
    X = np.zeros((len(rows), base + 5))
    inv = {i: t for t, i in teams.items()}
    for i, r in enumerate(rows):
        X[i, r[0]] = 1
        X[i, nt + r[1]] = -1
        if r[2] is not None:
            X[i, 2 * nt + r[2]] = 1
        X[i, base] = 1
        X[i, base + 1] = r[3]
        X[i, base + 2] = low(inv[r[0]])
        X[i, base + 3] = -low(inv[r[1]])
        X[i, base + 4] = r[4]
    if kind != "py":
        X = X[:, :base + 4]
    b = S.ridge_w(X, [r[5] for r in rows], [r[6] for r in rows], lam,
                  free=tuple(range(base, base + (5 if kind == "py" else 4))))
    return {"off": {t: b[i] + low(t) * b[base + 2] for t, i in teams.items()},
            "def": {t: b[nt + i] + low(t) * b[base + 3] for t, i in teams.items()},
            "qb": {q: b[2 * nt + i] for q, i in qbs.items()}, "mu": b[base], "home": b[base + 1],
            "green": b[base + 4] if kind == "py" else 0.0}


def features(gs, tau=10.0, offw=8.0, lam_y=150.0, lam_f=400.0, lam_p=8.0, first=2022):
    import sports_data as sd
    import sports_players as sp
    allgames = sd.load_games("ncaaf")
    car = defaultdict(int)
    for g in gs:
        g["_car"] = {q[0]: car[q[0]] for qs in g["qb"].values() for q in qs}
        for qs in g["qb"].values():
            for q in qs:
                car[q[0]] += q[2]
    weeks = defaultdict(list)
    for g in gs:
        weeks[(g["season"], g["wk"])].append(g)
    out, lastg, done, ngames = {}, {}, [], defaultdict(int)
    run = defaultdict(int)
    for key in sorted(weeks):
        season, wk = key
        if season >= first and done:
            fbs = sp.fbs_set(allgames, min(g["start"] for g in weeks[key]))
            f = {k: fit(done, (wk, season), tau, offw, lam, k, fbs)
                 for k, lam in (("py", lam_y), ("ry", lam_y), ("fd", lam_f), ("pts", lam_p))}
            for g in weeks[key]:
                h, a = g["home"], g["away"]
                hf = 0.0 if g["neutral"] else 1.0
                row = {"home": hf}
                m = f["py"]
                for tag in ("A", "P"):
                    v = []
                    for t, opp in ((h, a), (a, h)):
                        q = (g["qb"][t][0][0] if g["qb"][t] else None) if tag == "A" else (lastg.get(t) or (None, None))[1]
                        c = g["_car"].get(q, run.get(q, 0))
                        v.append(m["qb"].get(q, 0.0) + (m["green"] if c < GREEN else 0.0) + m["off"].get(t, 0.0) - m["def"].get(opp, 0.0))
                    row["dP" + tag] = v[0] - v[1] + 2 * hf * m["home"]
                for k, nm in (("ry", "dR"), ("fd", "dS")):
                    m2 = f[k]
                    row[nm] = ((m2["off"].get(h, 0.0) - m2["def"].get(a, 0.0)) - (m2["off"].get(a, 0.0) - m2["def"].get(h, 0.0))
                               + 2 * hf * m2["home"])
                row["dPts"] = f["pts"]["team"].get(h, 0.0) - f["pts"]["team"].get(a, 0.0)
                d0 = date.fromisoformat(g["date"])
                rst = []
                for t in (h, a):
                    lg_ = lastg.get(t)
                    dd = (d0 - date.fromisoformat(lg_[0])).days if lg_ else 7
                    rst.append(min(14, dd) if dd < 60 else 7)
                row["rest"] = rst[0] - rst[1]
                qa = [g["qb"][t][0][0] if g["qb"][t] else None for t in (h, a)]
                row["qbchg_h"] = int(bool(lastg.get(h)) and lastg[h][1] is not None and lastg[h][1] != qa[0])
                row["qbchg_a"] = int(bool(lastg.get(a)) and lastg[a][1] is not None and lastg[a][1] != qa[1])
                row["n_h"], row["n_a"] = ngames[(season, h)], ngames[(season, a)]
                row["seen_h"], row["seen_a"] = int(h in f["pts"]["team"]), int(a in f["pts"]["team"])
                out[g["id"]] = row
        for g in weeks[key]:
            for t in (g["home"], g["away"]):
                lastg[t] = (g["date"], g["qb"][t][0][0] if g["qb"][t] else None)
                ngames[(season, t)] += 1
            for qs in g["qb"].values():
                for q in qs:
                    run[q[0]] += q[2]
        done.extend(weeks[key])
    return out


NAMES = ["dP", "dR", "dS", "dPts", "rest", "home"]


def stage2(gs, feats, qb="A", first_test=2023, lam=1.0, names=NAMES):
    def vec(r):
        return [r[n + qb] if n == "dP" else r[n] for n in names]
    by = defaultdict(list)
    for g in gs:
        if g["id"] in feats and feats[g["id"]]["seen_h"] and feats[g["id"]]["seen_a"]:
            by[g["season"]].append(g)
    pred, wts = {}, None
    for s in sorted(by):
        if s < first_test:
            continue
        tr = [g for y in by if y < s for g in by[y]]
        X = np.array([vec(feats[g["id"]]) for g in tr])
        y = np.array([g["hs"] - g["as"] for g in tr])
        sdv = X.std(axis=0)
        sdv[sdv == 0] = 1.0
        b = S.ridge_w(X / sdv, y, np.ones(len(y)), lam) / sdv
        wts = dict(zip(names, b))
        for g in by[s]:
            pred[g["id"]] = float(np.dot(vec(feats[g["id"]]), b))
    return pred, wts
