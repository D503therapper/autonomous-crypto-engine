"""Shared pieces of the 10/28 hot-3-point-night study (study.py and players.py): the pre-tip inputs, the plain OLS,
the ROI cell at the closing price."""
import math
from collections import defaultdict

TRAIN = {2018, 2019, 2020, 2021, 2022, 2023}
HOLD = [2024, 2025, 2026]
HOME = []            # study.py sets these before fit_eval
pred = {}
CELLS = 0


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def corr(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x) / n)
    sy = math.sqrt(sum((b - my) ** 2 for b in y) / n)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / n / (sx * sy) if sx and sy else 0.0


def blend(v, g, prior, lg, n0=10.0):
    """season-to-date value v over g games, pulled toward last season's number (or the league's) early on."""
    base = prior if prior is not None else lg
    if v is None:
        return base
    return (v * g + base * n0) / (g + n0)


def feats(d, lookahead=False):
    """None when the inputs aren't there (both teams 5+ games with box scores)."""
    if d["g"] < 5 or d["o_g"] < 5 or d["opp_g"] < 5 or d["o_opp_g"] < 5:
        return None
    lg_tpm = d["lg_pct"] * 34.0

    def side(p):
        pr = d[p + "prior"]
        tpm_s = blend(d[p + "s_tpm"], d[p + "g"], pr[0] * pr[1] if pr else None, lg_tpm)
        tpa_s = blend(d[p + "s_tpa"], d[p + "g"], pr[0] if pr else None, 34.0)
        pct_s = d[p + "s_pct_reg"]
        oa_tpm = blend(d[p + "oa_s_tpm"], d[p + "opp_g"], None, lg_tpm)
        oa_tpa = blend(d[p + "oa_s_tpa"], d[p + "opp_g"], None, 34.0)
        oa_pct = d[p + "oa_s_pct_reg"]
        pace = blend(d[p + "s_pace"], d[p + "g"], pr[2] if pr else None, d["lg_pace"])
        return dict(tpm_s=tpm_s, tpa_s=tpa_s, pct_s=pct_s, oa_tpm=oa_tpm, oa_tpa=oa_tpa, oa_pct=oa_pct, pace=pace,
                    l5_tpm=d[p + "l5_tpm"], l10_tpm=d[p + "l10_tpm"], l5_pct=d[p + "l5_pct"] or pct_s,
                    l10_pct=d[p + "l10_pct"] or pct_s, oa_l10_tpm=d[p + "oa_l10_tpm"] or oa_tpm,
                    rest=min(d[p + "rest"] or 3, 4), b2b=1.0 if (d[p + "rest"] or 3) <= 1 else 0.0,
                    tz=d[p + "tz_jump"] or 0.0, in4=d[p + "in4"],
                    sat=d[p + "top3_sat_last"] or 0, out=d[p + "top3_out_tonight"] or 0)
    m, o = side(""), side("o_")
    # the hand-built expected threes: attempts = half ours / half what the opponent allows, scaled by pace; % = half
    # ours (regressed) / half what the opponent allows (regressed)
    pace_g = (m["pace"] + o["pace"]) / 2
    exp_m = ((m["tpa_s"] + o["oa_tpa"]) / 2) * (pace_g / ((m["pace"] + o["pace"]) / 2)) * ((m["pct_s"] + o["oa_pct"]) / 2)
    exp_o = ((o["tpa_s"] + m["oa_tpa"]) / 2) * ((o["pct_s"] + m["oa_pct"]) / 2)
    f = [1.0,
         m["tpm_s"] - o["tpm_s"],                  # season makes a game
         o["oa_tpm"] - m["oa_tpm"],                # threes allowed (theirs minus ours - good for us)
         m["l5_tpm"] - o["l5_tpm"],
         m["l10_tpm"] - o["l10_tpm"],
         (m["pct_s"] - o["pct_s"]) * 100,
         (o["oa_pct"] - m["oa_pct"]) * 100,
         (m["l10_pct"] - o["l10_pct"]) * 100,
         m["tpa_s"] - o["tpa_s"],
         o["oa_tpa"] - m["oa_tpa"],
         o["oa_l10_tpm"] - m["oa_l10_tpm"],
         m["pace"] + o["pace"] - 2 * d["lg_pace"],
         m["rest"] - o["rest"],
         m["b2b"] - o["b2b"],
         m["tz"] - o["tz"],
         m["in4"] - o["in4"],
         (d["elev"] or 0) / 1000.0,
         m["sat"] - o["sat"],
         d["elo"] - d["opp_elo"],
         ]
    if lookahead:
        f.append(m["out"] - o["out"])
    return f, exp_m - exp_o


NAMES = ["const", "season 3PM/g", "opp 3PM allowed", "last-5 3PM", "last-10 3PM", "season 3P% (reg)", "opp 3P% allowed (reg)",
         "last-10 3P%", "season 3PA/g", "opp 3PA allowed", "opp last-10 3PM allowed", "pace (both)", "rest days", "b2b",
         "time-zone jump", "games in 4 days", "altitude (k ft)", "top-3 shooter sat last game", "Elo gap", "top-3 shooter OUT tonight (look-ahead)"]


def solve(A, b):
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12:
            continue
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(n)]


def ols(X, y, ridge=1e-3):
    k = len(X[0])
    A = [[sum(x[i] * x[j] for x in X) for j in range(k)] for i in range(k)]
    for i in range(1, k):
        A[i][i] += ridge * len(X)
    b = [sum(x[i] * yy for x, yy in zip(X, y)) for i in range(k)]
    return solve(A, b)


def predict(beta, x):
    return sum(b * v for b, v in zip(beta, x))


def r2(pred, y):
    my = sum(y) / len(y)
    ss = sum((a - my) ** 2 for a in y)
    sr = sum((a - b) ** 2 for a, b in zip(y, pred))
    return 1 - sr / ss if ss else 0.0


def fit_eval(lookahead=False, label=""):
    HOME = globals()['HOME']
    rows = []
    for d in HOME:
        fx = feats(d, lookahead)
        if fx:
            rows.append((d, fx[0], fx[1]))
    tr = [r for r in rows if r[0]["season"] in TRAIN]
    beta = ols([r[1] for r in tr], [r[0]["tpm"] - r[0]["o_tpm"] for r in tr])
    out = {}
    for lab, S in (("train", TRAIN), ("2024-25", {2024}), ("2025-26", {2025}), ("2026-27", {2026})):
        rs = [r for r in rows if r[0]["season"] in S]
        if not rs:
            continue
        y = [r[0]["tpm"] - r[0]["o_tpm"] for r in rs]
        p = [predict(beta, r[1]) for r in rs]
        h = [r[2] for r in rs]
        right = sum(1 for a, b in zip(p, y) if b and (a > 0) == (b > 0)) / max(1, sum(1 for b in y if b))
        out[lab] = (len(rs), corr(p, y), r2(p, y), corr(h, y), right)
    print(f"  {label}")
    for lab, (n, c, rr, ch, right) in out.items():
        print(f"    {lab:8s} n {n:5d}  OLS: corr {c:.3f} R² {rr:.3f} | hand-built expected threes: corr {ch:.3f} | "
              f"the predicted 3PM leader really made more threes {right * 100:.1f}% of the time")
    return beta, rows



def roi(bets):
    """bets: list of (won, dec, nv)."""
    if not bets:
        return 0, 0, 0.0, 0.0, 0.0, 0.0
    n = len(bets)
    w = sum(1 for b in bets if b[0])
    pnl = sum((b[1] - 1) if b[0] else -1 for b in bets)
    imp = sum(b[2] for b in bets) / n
    var = sum(b[2] * (1 - b[2]) for b in bets)
    z = (w - sum(b[2] for b in bets)) / math.sqrt(var) if var else 0.0
    return n, w, pnl / n * 100, w / n * 100, imp * 100, z


def seasons_up(by_season):
    ups = [s for s, b in by_season.items() if len(b) >= 10 and roi(b)[2] > 0]
    return len(ups), len([s for s in by_season if len(by_season[s]) >= 10])


def cell(name, pick, HOME=None):
    HOME = HOME if HOME is not None else globals()['HOME']
    """pick(d, p) -> (won, dec, nv) or None for the home-row game with prediction p (home minus away)."""
    global CELLS
    CELLS += 1
    out = []
    by_s = defaultdict(list)
    for d in HOME:
        p = pred.get(d["gid"])
        if p is None:
            continue
        b = pick(d, p)
        if b:
            by_s[d["season"]].append(b)
    tr = [b for s in TRAIN for b in by_s.get(s, [])]
    n, w, ro, wp, imp, z = roi(tr)
    u, t = seasons_up({s: by_s[s] for s in TRAIN if s in by_s})
    out.append(f"train {w}-{n - w} {ro:+.1f}% ({wp:.1f} vs {imp:.1f}, z {z:+.1f}, {u}/{t} up)")
    for s in HOLD:
        n, w, ro, wp, imp, z = roi(by_s.get(s, []))
        out.append(f"{s} {w}-{n - w} {ro:+.1f}% (z {z:+.1f})")
    print(f"  {name:58s} | " + " | ".join(out))


def ml_pick(thr, band):
    lo, hi = band

    def pick(d, p):
        if abs(p) < thr:
            return None
        side_home = p > 0
        ml = d["ml"] if side_home else d["opp_ml"]
        nv = d["nv"] if side_home else 1 - d["nv"]
        won = d["won"] if side_home else not d["won"]
        if lo <= ml <= hi:
            return (won, dec(ml), nv)
        return None
    return pick


def ats_pick(thr):
    def pick(d, p):
        if abs(p) < thr or d["spread"] is None:
            return None
        side_home = p > 0
        sp = d["spread"] if side_home else -d["spread"]
        mg = d["margin"] if side_home else -d["margin"]
        if mg + sp == 0:
            return None
        return (mg + sp > 0, dec(-110), 0.5)
    return pick


