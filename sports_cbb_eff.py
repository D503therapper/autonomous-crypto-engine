"""🏀 The college hoops EFFICIENCY read (11/3 DEEP study - results/studies/deep_cbb_model/, SPORTS_FINDINGS "11/3 - DEEP:
COLLEGE HOOPS EFFICIENCY MODEL"). Tempo-free, opponent- and venue-adjusted points per 100 possessions, built only from
our own files: data/sports/games/ncaab (scores) + data/sports/teamstats/ncaab*.jsonl (team box scores - possessions
= FGA - OREB + TO + 0.475 x FTA; shooting luck partly taken out: 3-point % pulled 30% and free-throw % 50% toward
the D1 average). Each team's offense / defense / tempo is solved by weighted ridge least squares over this season's
finished games (half-life 120 days), pulled toward a PRESEASON PRIOR (last season's final rating, 20% of the season
before, shrunk 30% toward its conference's mean - conferences inferred from last season's Jan-Feb schedule) with the
strength of 6 games (fading to 3 by game 30). Settings tuned on 2018-22 margins only; graded on 2023-25 held out.

WHAT IT IS FOR (the study's verdict): it is NOT a better read than the close - the market already knows what it knows
(log loss held out 0.5294 vs the close 0.5229; blended with the close it adds nothing, 0.5228; betting its
disagreements with the close loses on spreads, moneylines and totals). What it does carry is a FAVORITE FILTER: a
college hoops -101..-150 moneyline favorite whose efficiency read sits 3+ points UNDER the close's no-vig lost -9.6%
on 2,338 (train 2018-22 -9.5%, 0 of 5 seasons up; held out 2023-25 -9.7%, 0 of 3; every season 2018-25 down; the open
-5.1%, 0 of 3; ratings two nights stale -8.3%) vs -0.6% when the read agrees within 3 - wired as a WEIGHT on the
favorite's read (sports.weigh_ncaab_eff_fav), never a trigger. Pure Python (the runner has no numpy)."""
import glob
import json
import math
import os
from collections import defaultdict
from datetime import datetime

import sports_data as sd

PRM = dict(halflife=120.0, prior_games=6.0, prior_fade=0.5, shrink=0.70, conf_w=1.0, hfa=2.0, hfa_prior=2000.0,
           tempo_prior=6.0, tempo_shrink=0.75, luck3=0.3, luckft=0.5, mu0=104.0, t0=68.0, blow_cap=30.0, d1_min=10,
           prev2_w=0.2, unknown_prior=2.0)
CAL = (-0.001, 0.1537)        # P(home wins) = sigmoid(CAL[0] + CAL[1] x model margin) - fit on 2018-22 results
LG3, LGFT = 0.338, 0.715      # D1 3-point / free-throw % (steady 2021-25: 33.6-34.0% / 71.4-72.2%)
SEASONS_BACK = 6              # the prior chain: seasons s-6 .. s-1 solved to their finals, then this season (6 back reproduces
#                               the study's 2016-start chain to 0.07 points a game - check_live_out.txt; 3 back was 0.7)
_CACHE = {}
_BOX = {}


def season_of(start):
    y = int(start[:4])
    return y if int(start[5:7]) >= 7 else y - 1


def night_of(start):
    """The US night (UTC - 8h) a game belongs to, as a day number."""
    t = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
    return (t.toordinal() * 24 + t.hour - 8) // 24


def _split(s):
    a, b = str(s).split("-")
    return int(a), int(b)


def load_box(data=None):
    """{game id: {team id: dict(tpm, tpa, ftm, fta, poss)}} from the team box scores on disk (missing = {})."""
    data = data or sd.DATA
    files = [os.path.join(data, "teamstats", "ncaab.jsonl")] + sorted(glob.glob(os.path.join(data, "teamstats", "ncaab", "*.jsonl")))
    stamp = tuple((f, os.path.getsize(f)) for f in files if os.path.exists(f))
    if _BOX.get("stamp") == stamp:
        return _BOX["box"]
    out = {}
    for fn in files:
        try:
            fh = open(fn)
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    d = json.loads(line)
                    tm = {}
                    for tid, t in d["teams"].items():
                        fgm, fga = _split(t["fieldGoalsMade-fieldGoalsAttempted"])
                        tpm, tpa = _split(t["threePointFieldGoalsMade-threePointFieldGoalsAttempted"])
                        ftm, fta = _split(t["freeThrowsMade-freeThrowsAttempted"])
                        oreb = int(t["offensiveRebounds"])
                        to = int(t.get("totalTurnovers") or t.get("turnovers") or 0)
                        tm[str(tid)] = dict(tpm=tpm, tpa=tpa, ftm=ftm, fta=fta, poss=fga - oreb + to + 0.475 * fta)
                    if len(tm) == 2:
                        out[d["gid"]] = tm
                except (KeyError, ValueError, TypeError, AttributeError):
                    continue
    _BOX.clear()
    _BOX.update(stamp=stamp, box=out)
    return out


_FIN = {}


def _finals(games):
    """This league's finals as light rows (memoized per games dict + its size - one pass a board, not one a side)."""
    key = (id(games), len(games), sum(1 for g in games.values() if g.get("status") == "final"
                                      and g.get("league") == "ncaab"))
    if key not in _FIN:
        _FIN.clear()
        _FIN[key] = _finals_rows(games)
    return _FIN[key]


def _finals_rows(games):
    out = []
    for g in games.values():
        if g.get("league") != "ncaab" or g.get("status") != "final" or (g.get("stype") or "?") not in ("2", "3"):
            continue
        if sd.exhibition(g) or g.get("home") == g.get("away"):
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append({"id": g["id"], "start": g["start"], "season": season_of(g["start"]), "night": night_of(g["start"]),
                    "home": str(g["home"]), "away": str(g["away"]), "hs": hs, "as_": as_,
                    "neutral": str(g.get("neutral")) == "1", "stype": str(g.get("stype")),
                    "md": g["start"][5:10]})
    out.sort(key=lambda r: (r["start"], r["id"]))
    return out


def conferences(rows):
    """{team: conference key} from one season's Jan 3 - Mar 1 home / road regular-season games (3+ shared opponents)."""
    adj = defaultdict(set)
    for r in rows:
        if r["stype"] != "2" or r["neutral"] or not ("01-03" <= r["md"] <= "03-01"):
            continue
        adj[r["home"]].add(r["away"])
        adj[r["away"]].add(r["home"])
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
    return {t: (k if len(mem) >= 5 else None) for k, mem in comp.items() for t in mem}


def _luck_pts(r, side, box):
    b = (box.get(r["id"]) or {}).get(r[side])
    pts = r["hs"] if side == "home" else r["as_"]
    if not b:
        return pts
    if b["tpa"]:
        pts += 3 * PRM["luck3"] * (LG3 * b["tpa"] - b["tpm"])
    if b["fta"]:
        pts += PRM["luckft"] * (LGFT * b["fta"] - b["ftm"])
    return pts


def _poss(r, box):
    b = box.get(r["id"]) or {}
    h, a = b.get(r["home"]), b.get(r["away"])
    return (h["poss"] + a["poss"]) / 2 if h and a else None


def _pcg(matvec, b, diag, x0, tol=1e-10, iters=500):
    """Preconditioned conjugate gradient for the (symmetric, positive definite) ridge normal equations."""
    x = list(x0)
    ax = matvec(x)
    r = [bi - ai for bi, ai in zip(b, ax)]
    z = [ri / di for ri, di in zip(r, diag)]
    p = list(z)
    rz = sum(ri * zi for ri, zi in zip(r, z))
    bn = sum(bi * bi for bi in b) or 1.0
    for _ in range(iters):
        if sum(ri * ri for ri in r) <= tol * bn:
            break
        ap = matvec(p)
        alpha = rz / (sum(pi * qi for pi, qi in zip(p, ap)) or 1e-300)
        x = [xi + alpha * pi for xi, pi in zip(x, p)]
        r = [ri - alpha * qi for ri, qi in zip(r, ap)]
        z = [ri / di for ri, di in zip(r, diag)]
        rz2 = sum(ri * zi for ri, zi in zip(r, z))
        beta = rz2 / (rz or 1e-300)
        rz = rz2
        p = [zi + beta * pi for zi, pi in zip(z, p)]
    return x


def _solve(rows, teams, po, pd, lam, hfa0, mu_g):
    """Weighted ridge least squares: y = mu + hfa x v + O[off] - D[def], O / D pulled to their priors (lam), hfa to hfa0.
    rows: (off, def, v, y, w). Unknowns [mu, hfa, O..., D...]."""
    n = len(teams)
    ix = {t: i for i, t in enumerate(teams)}
    R = [(2 + ix[o], 2 + n + ix[d], v, y, w) for o, d, v, y, w in rows]
    prior = [1e-3, PRM["hfa_prior"]] + [lam[t] for t in teams] * 2
    b = [1e-3 * mu_g, PRM["hfa_prior"] * hfa0] + [lam[t] * po[t] for t in teams] + [lam[t] * pd[t] for t in teams]
    diag = list(prior)
    for oi, di, v, y, w in R:
        b[0] += w * y
        b[1] += w * v * y
        b[oi] += w * y
        b[di] -= w * y
        diag[0] += w
        diag[1] += w * v * v
        diag[oi] += w
        diag[di] += w

    def mv(x):
        out = [a * c for a, c in zip(prior, x)]
        for oi, di, v, y, w in R:
            s_ = w * (x[0] + v * x[1] + x[oi] - x[di])
            out[0] += s_
            out[1] += v * s_
            out[oi] += s_
            out[di] -= s_
        return out
    x = _pcg(mv, b, diag, [mu_g, hfa0] + [po[t] for t in teams] + [pd[t] for t in teams])
    return x[0], x[1], {t: x[2 + i] for i, t in enumerate(teams)}, {t: x[2 + n + i] for i, t in enumerate(teams)}


def _solve_tempo(rows, teams, pt, lam, t_g):
    """poss = T0 + t[a] + t[b], t pulled to its prior. rows: (a, b, poss, w)."""
    ix = {t: i for i, t in enumerate(teams)}
    R = [(1 + ix[a], 1 + ix[b_], y, w) for a, b_, y, w in rows]
    prior = [1e-3] + [lam[t] for t in teams]
    b = [1e-3 * t_g] + [lam[t] * pt[t] for t in teams]
    diag = list(prior)
    for ai, bi, y, w in R:
        b[0] += w * y
        b[ai] += w * y
        b[bi] += w * y
        diag[0] += w
        diag[ai] += w
        diag[bi] += w

    def mv(x):
        out = [a * c for a, c in zip(prior, x)]
        for ai, bi, y, w in R:
            s_ = w * (x[0] + x[ai] + x[bi])
            out[0] += s_
            out[ai] += s_
            out[bi] += s_
        return out
    x = _pcg(mv, b, diag, [t_g] + [pt[t] for t in teams])
    return x[0], {t: x[1 + i] for i, t in enumerate(teams)}


def _prior(prev, prev2, cmap, teams):
    """Each team's preseason (O, D, tempo) + whether it had a D1 season last year."""
    po, pd, pt, known = {}, {}, {}, {}
    if prev is None:
        for t in teams:
            po[t], pd[t], pt[t], known[t] = 0.0, 0.0, 0.0, False
        return po, pd, pt, known, PRM["hfa"], PRM["mu0"], PRM["t0"]
    cm = defaultdict(list)
    small = []
    for t, (o, d, tt, n) in prev["teams"].items():
        if n >= PRM["d1_min"] and cmap.get(t) is not None:
            cm[cmap[t]].append((o, d))
        if n < PRM["d1_min"]:
            small.append((o, d, tt))
    cmean = {k: (sum(x[0] for x in v) / len(v), sum(x[1] for x in v) / len(v)) for k, v in cm.items()}
    sm_ = tuple(sum(x[i] for x in small) / len(small) for i in range(3)) if small else (-15.0, -10.0, 0.0)
    for t in teams:
        rec = prev["teams"].get(t)
        if rec and rec[3] >= PRM["d1_min"]:
            o, d, tt, _ = rec
            r2 = (prev2 or {}).get("teams", {}).get(t)
            if PRM["prev2_w"] and r2 and r2[3] >= PRM["d1_min"]:
                o = (1 - PRM["prev2_w"]) * o + PRM["prev2_w"] * r2[0]
                d = (1 - PRM["prev2_w"]) * d + PRM["prev2_w"] * r2[1]
            c = cmean.get(cmap.get(t), (0.0, 0.0))
            po[t] = PRM["shrink"] * o + (1 - PRM["shrink"]) * PRM["conf_w"] * c[0]
            pd[t] = PRM["shrink"] * d + (1 - PRM["shrink"]) * PRM["conf_w"] * c[1]
            pt[t] = PRM["tempo_shrink"] * tt
            known[t] = True
        else:
            po[t], pd[t], pt[t], known[t] = sm_[0], sm_[1], sm_[2] * PRM["tempo_shrink"], False
    return po, pd, pt, known, prev["hfa"], prev["mu"], prev["T0"]


def _fit(rows_s, teams, po, pd, pt, known, hfa0, mu_g, t_g, at_night, box, final=False):
    """Solve one season's ratings from its games before `at_night` (final=True: the season's end, weak prior)."""
    done = [r for r in rows_s if r["night"] < at_night]
    gcount = defaultdict(int)
    for r in done:
        gcount[r["home"]] += 1
        gcount[r["away"]] += 1
    hl = max(PRM["halflife"], 90.0) if final else PRM["halflife"]
    if final:
        lam = {t: 1.0 for t in teams}
    else:
        base = {t: PRM["prior_games"] if known[t] else PRM["unknown_prior"] for t in teams}
        lam = {t: base[t] * max(0.0, 1 - PRM["prior_fade"] * gcount[t] / 30.0) for t in teams}
    lam_t = {t: (1.0 if final else (PRM["tempo_prior"] if known[t] else PRM["unknown_prior"])) for t in teams}
    # tempo first (possessions from the box scores), then efficiencies
    trows = []
    for r in done:
        ps = _poss(r, box)
        if ps:
            trows.append((r["home"], r["away"], ps, 0.5 ** ((at_night - r["night"]) / hl)))
    T0, tt = _solve_tempo(trows, teams, pt, lam_t, t_g) if trows else (t_g, dict(pt))
    rows = []
    for r in done:
        ps = _poss(r, box) or (T0 + tt[r["home"]] + tt[r["away"]])
        yh, ya = 100 * _luck_pts(r, "home", box) / ps, 100 * _luck_pts(r, "away", box) / ps
        if PRM["blow_cap"] and not final:                     # (the season-end solve for next year's prior keeps every point)
            mid, half = (yh + ya) / 2, max(-PRM["blow_cap"], min(PRM["blow_cap"], (yh - ya) / 2))
            yh, ya = mid + half, mid - half
        w = 0.5 ** ((at_night - r["night"]) / hl)
        v = 0.0 if r["neutral"] else 1.0
        rows.append((r["home"], r["away"], v, yh, w))
        rows.append((r["away"], r["home"], -v, ya, w))
    mu, hfa, O, D = _solve(rows, teams, po, pd, lam, hfa0, mu_g) if rows else (mu_g, hfa0, dict(po), dict(pd))
    return dict(mu=mu, hfa=hfa, O=O, D=D, T0=T0, tt=tt, n=dict(gcount))


def ratings(games, start, box=None, fin=None):
    """This season's ratings as of the US night of `start` (only games finished on earlier nights), with the prior
    chain from SEASONS_BACK seasons before. Cached per (season, night, number of finals)."""
    fin = _finals(games) if fin is None else fin
    s, nt = season_of(start), night_of(start)
    key = (s, nt, len(fin), id(fin))
    if key in _CACHE:
        return _CACHE[key]
    box = load_box() if box is None else box
    by = defaultdict(list)
    for r in fin:
        by[r["season"]].append(r)
    sched = set()                                            # this season's teams incl. the ones yet to play (names only)
    for g in games.values():
        if g.get("league") == "ncaab" and str(g.get("start", ""))[:4].isdigit() and season_of(g["start"]) == s:
            sched |= {str(g.get("home")), str(g.get("away"))}
    prev = prev2 = None
    for ss in range(s - SEASONS_BACK, s + 1):
        rows_s = by.get(ss, [])
        teams = sorted({r["home"] for r in rows_s} | {r["away"] for r in rows_s} | (sched if ss == s else set()))
        cmap = conferences(by.get(ss - 1, []))
        po, pd, pt, known, hfa0, mu_g, t_g = _prior(prev, prev2, cmap, teams)
        if ss < s:
            if not rows_s:
                prev2, prev = prev, None
                continue
            last = max(r["night"] for r in rows_s) + 1
            f = _fit(rows_s, teams, po, pd, pt, known, hfa0, mu_g, t_g, last, box, final=True)
            prev2, prev = prev, dict(teams={t: (f["O"][t], f["D"][t], f["tt"][t], f["n"].get(t, 0)) for t in teams},
                                     mu=f["mu"], T0=f["T0"], hfa=f["hfa"])
        else:
            f = _fit(rows_s, teams, po, pd, pt, known, hfa0, mu_g, t_g, nt, box) if rows_s else \
                dict(mu=mu_g, hfa=hfa0, O=dict(po), D=dict(pd), T0=t_g, tt=dict(pt), n={})
            f["prior"], f["_fin"] = (prev, po, pd, pt), fin   # (holds fin so its id stays unique while cached)
            _CACHE.clear()
            _CACHE[key] = f
            return f
    return None


def _team(f, t):
    """(O, D, tempo) for a team - one not on this season's books yet gets its prior (or the non-D1 default)."""
    if t in f["O"]:
        return f["O"][t], f["D"][t], f["tt"][t]
    prev = (f.get("prior") or (None,))[0]
    if prev and t in prev["teams"] and prev["teams"][t][3] >= PRM["d1_min"]:
        o, d, tt, _ = prev["teams"][t]
        return PRM["shrink"] * o, PRM["shrink"] * d, PRM["tempo_shrink"] * tt
    return -15.0, -10.0, 0.0


def read_many(games, gids, box=None):
    """{game id: predict(...)} for several games of one board (box scores read once)."""
    box = load_box() if box is None else box
    fin = _finals(games)
    return {gid: predict(games, games[gid], box, fin) for gid in gids if gid in games}


def predict(games, g, box=None, fin=None):
    """{'margin': home margin, 'total', 'poss', 'p_home'} for a college hoops game (None if it can't be read)."""
    try:
        f = ratings(games, g["start"], box, fin)
        if f is None:
            return None
        h, a = str(g["home"]), str(g["away"])
        oh, dh, th = _team(f, h)
        oa, da, ta = _team(f, a)
        v = 0.0 if str(g.get("neutral")) == "1" else 1.0
        eh = f["mu"] + oh - da + f["hfa"] * v
        ea = f["mu"] + oa - dh - f["hfa"] * v
        ps = f["T0"] + th + ta
        m = ps * (eh - ea) / 100
        return {"margin": round(m, 2), "total": round(ps * (eh + ea) / 100, 1), "poss": round(ps, 1),
                "p_home": 1 / (1 + math.exp(-(CAL[0] + CAL[1] * m)))}
    except Exception as e:                                   # noqa: BLE001 - a read error = no read, never a crash
        print(f"cbb efficiency read failed: {str(e)[:80]}")
        return None
