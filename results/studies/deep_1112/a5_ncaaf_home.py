"""11/12 DEEP PROGRAM - A5: THE COLLEGE FOOTBALL RAW READ'S HOME EDGE, REFIT ON FBS-vs-FBS (the 11/11-11/12 open lead:
the raw ratings read tilts ~11 points to the home team and waves every home dog through 'own read over the price').
The raw read (sports_model.own_p) is a logistic fit on EVERY college game - a third of them an FBS team hosting a
lower-division school (the home side wins 9 in 10 of those; the visitor sits near 1500 with almost no games).
  1. by matchup: how often the home side wins vs what the raw read / the ratings alone / the close said;
  2. the home edge that fits each matchup best (Elo points on top of the ratings; log loss by hfa);
  3. the read re-fit on FBS-vs-FBS games only (walk-forward, each August on the games before) vs today's all-games
     fit, graded on FBS-vs-FBS games: log loss, the home-dog / road-dog miss, and whether its gap to the close knows
     anything (b = 0: no);
  4. the same for a read with NO game-day features (ratings + home edge only).
Usage: python results/studies/deep_1112/a5_ncaaf_home.py > results/studies/deep_1112/a5_ncaaf_home.out"""
import json, math, os, sys
import numpy as np
import dlib as D

sys.path.insert(0, D.ROOT)
os.chdir(D.ROOT)
import sports_data as sd         # noqa: E402
import sports_model as sm        # noqa: E402
import sports_players as sp      # noqa: E402
from a4_trust import irls, season_of   # noqa: E402

LG = sys.argv[1] if len(sys.argv) > 1 else "ncaaf"
MODEL = json.load(open("data/sports/model.json"))
games = sd.load_games(LG)
p0 = MODEL["params"][LG]
_, rows = sm.replay(sm.finals(games, LG), p0["k"], p0["hfa"], LG)
rows = [r for r in rows if r[2] != 0.5]
print(f"{LG}: {len(rows)} finals; today's reaction speed {p0['k']}, home edge {p0['hfa']} Elo points, the raw read's intercept {p0['w'][0]:+.3f} "
      f"(= {100 * (sm.sigmoid(p0['w'][0]) - 0.5):+.1f} points of win chance at even ratings, ON TOP of the {p0['hfa']})")


def kind(g):
    if LG != "ncaaf":
        return "all"
    fbs = sp.fbs_set(games, g["start"])
    if fbs is None:
        return "?"
    h, a = g["home"] in fbs, g["away"] in fbs
    return "FBS v FBS" if h and a else "FBS hosts lower" if h else "lower hosts FBS" if a else "lower v lower"


K = [kind(r[0]) for r in rows]
X = np.array([sm._own_x(f) for _, f, _, _ in rows])
Y = np.array([r[2] for r in rows])
S = np.array([season_of(r[0]["start"]) for r in rows])
NEU = np.array([str(r[0].get("neutral")) == "1" for r in rows])
MK = np.array([sm.market_p(r[0]) if sm.market_p(r[0]) is not None else np.nan for r in rows])
ELO_RAW = np.array([r[1]["elo_raw"] for r in rows])
prior = [0.0, 1.0] + [0.0] * (len(sm.FEATURES) - 1)
FB = np.array([k in ("FBS v FBS", "all") for k in K])


def walk(train_sel, cols=None):
    own = np.full(len(rows), np.nan)
    ws = {}
    for s in sorted(set(S)):
        before = np.where((S < s) & train_sel)[0]
        if len(before) < 500:
            continue
        tr = before[-sm.TRAIN_GAMES:]
        Xt = X if cols is None else X[:, cols]
        pr = prior if cols is None else [prior[c] for c in cols]
        w = irls(Xt[tr], Y[tr], np.zeros(len(tr)), pr, 5.0)
        idx = np.where(S == s)[0]
        own[idx] = 1 / (1 + np.exp(-np.clip(Xt[idx] @ w, -30, 30)))
        ws[s] = w
    return own, ws


own_all, w_all = walk(np.ones(len(rows), bool))
own_fbs, w_fbs = walk(FB)
own_elo_fbs, w_elo = walk(FB, [0, 1])
print("\n1. BY MATCHUP (non-neutral games, a walk-forward raw read): n / home won / raw read said / the close said")
for k in sorted(set(K)):
    ix = np.array([kk == k for kk in K]) & ~NEU & ~np.isnan(own_all)
    if ix.sum() < 50:
        continue
    mk = ix & ~np.isnan(MK)
    print(f"   {k:16s} n {ix.sum():5d} home won {100 * Y[ix].mean():5.1f}%  raw read said {100 * own_all[ix].mean():5.1f}%"
          f"  | with a close (n {mk.sum()}): won {100 * Y[mk].mean():5.1f}% raw {100 * own_all[mk].mean():5.1f}% close {100 * MK[mk].mean():5.1f}%")
    D.CELLS[0] += 1
print("\n2. THE HOME EDGE THAT FITS (the ratings + h Elo points; log loss; non-neutral)")
for k in sorted(set(K)):
    ix = np.array([kk == k for kk in K]) & ~NEU
    if ix.sum() < 300:
        continue
    res = []
    for h in (0, 20, 40, 60, 80, 100, 120):
        p = 1 / (1 + 10 ** (-(ELO_RAW[ix] + h) / 400))
        res.append((h, float(-(Y[ix] * np.log(p) + (1 - Y[ix]) * np.log(1 - p)).mean())))
        D.CELLS[0] += 1
    best = min(res, key=lambda t: t[1])
    print(f"   {k:16s} n {ix.sum():5d}: " + "  ".join(f"{h}: {v:.4f}" for h, v in res) + f"   -> best {best[0]}")
    # one-parameter fit of the leftover home edge in Elo points
    lo, hi = -100.0, 300.0
    for _ in range(40):
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        f1 = -(Y[ix] * np.log(1 / (1 + 10 ** (-(ELO_RAW[ix] + m1) / 400))) + (1 - Y[ix]) * np.log(1 - 1 / (1 + 10 ** (-(ELO_RAW[ix] + m1) / 400)))).mean()
        f2 = -(Y[ix] * np.log(1 / (1 + 10 ** (-(ELO_RAW[ix] + m2) / 400))) + (1 - Y[ix]) * np.log(1 - 1 / (1 + 10 ** (-(ELO_RAW[ix] + m2) / 400)))).mean()
        if f1 < f2:
            hi = m2
        else:
            lo = m1
    print(f"   {'':16s} the home edge that fits best: {0.5 * (lo + hi):.0f} Elo points")
print("\n3. THE READ ON FBS-vs-FBS GAMES: today's fit (every game) vs re-fit on FBS-vs-FBS only vs ratings + home edge only")
last = max(w_all)
print(f"   the fitted intercept (extra home edge, logit): every game {w_all[last][0]:+.3f} | FBS-vs-FBS only {w_fbs[last][0]:+.3f} | ratings-only {w_elo[last][0]:+.3f}"
      f"   (the Elo slope: {w_all[last][1]:.3f} / {w_fbs[last][1]:.3f} / {w_elo[last][1]:.3f})")
for nm, own in (("today's fit (every game)", own_all), ("re-fit on FBS v FBS", own_fbs), ("ratings + home edge only, FBS v FBS", own_elo_fbs)):
    ix = FB & ~np.isnan(own) & ~np.isnan(MK) & (MK > 0.005) & (MK < 0.995)
    y, o, m = Y[ix], own[ix], MK[ix]
    neu = NEU[ix]
    sea = S[ix]
    ll = float(-(y * np.log(o) + (1 - y) * np.log(1 - o)).mean())
    llm = float(-(y * np.log(m) + (1 - y) * np.log(1 - m)).mean())
    print(f" -- {nm}: n {ix.sum()} log loss {ll:.4f} (the close {llm:.4f}); home said {100 * o[~neu].mean():.1f}% won {100 * y[~neu].mean():.1f}% (the close {100 * m[~neu].mean():.1f}%)")
    for lab, sel, flip in (("home dog", (m < 0.5) & ~neu, False), ("road dog", (m > 0.5) & ~neu, True), ("home dog 23-50%", (m < 0.5) & (m > 0.23) & ~neu, False),
                           ("road dog 23-50%", (m > 0.5) & (m < 0.77) & ~neu, True)):
        for hf, hs in (("to 2021", sea <= 2021), ("2022 on", sea >= 2022)):
            q = sel & hs
            if q.sum() < 30:
                continue
            said = (1 - o[q]).mean() if flip else o[q].mean()
            mkt = (1 - m[q]).mean() if flip else m[q].mean()
            won = (1 - y[q]).mean() if flip else y[q].mean()
            se = math.sqrt(won * (1 - won) / q.sum())
            D.CELLS[0] += 1
            print(f"      {lab:16s} {hf}: n {q.sum():4d} said {100 * said:5.1f}% close {100 * mkt:5.1f}% won {100 * won:5.1f}%  miss {100 * (said - won):+5.1f} (z {(said - won) / se:+.1f})")
    for hf, hs in (("to 2021", sea <= 2021), ("2022 on", sea >= 2022)):
        q = hs & (o > 0.02) & (o < 0.98)
        Xi = np.array([np.log(o[q] / (1 - o[q])) - np.log(m[q] / (1 - m[q])), np.ones(q.sum())]).T
        w = irls(Xi, y[q], np.log(m[q] / (1 - m[q])), [0, 0], 1e-6)
        pp = 1 / (1 + np.exp(-(np.log(m[q] / (1 - m[q])) + Xi @ w)))
        se = np.sqrt(np.diag(np.linalg.inv((Xi * (pp * (1 - pp))[:, None]).T @ Xi)))
        D.CELLS[0] += 1
        print(f"      INFO {hf}: b(read - close) {w[0]:+.3f} (se {se[0]:.3f}), home shift {w[1]:+.3f} (se {se[1]:.3f}); avg |read - close| {100 * np.abs(o[q] - m[q]).mean():.1f} pts")
    # the gates that ride on the raw read: dogs +100..+350 with the read 15+ over the close (the gap play), 5+ over
    for cut in (0.05, 0.10, 0.15):
        for lab, home in (("home", True), ("road", False)):
            sel = []
            for i in np.where(ix)[0]:
                g = rows[i][0]
                od = sm._int(g["ml_home" if home else "ml_away"])
                if od is None or not 100 <= od <= 350 or NEU[i]:
                    continue
                pr = own[i] if home else 1 - own[i]
                mk_ = MK[i] if home else 1 - MK[i]
                if pr - mk_ >= cut:
                    sel.append({"dec": D.dec(od), "y": Y[i] if home else 1 - Y[i], "season": int(S[i]), "half": "train" if S[i] <= 2021 else "held"})
            D.cell(f"{lab} dog +100..+350, the read {int(cut * 100)}+ over the close", sel)
print("\n5. THE SAME GAMES, THREE FITS (FBS v FBS, every game all three reads exist): log loss, home said vs won")
ix = FB & ~np.isnan(own_all) & ~np.isnan(own_fbs) & ~np.isnan(own_elo_fbs)
for hf, hs in (("all", np.ones(len(rows), bool)), ("to 2021", S <= 2021), ("2022 on", S >= 2022)):
    q = ix & hs
    out = []
    for nm, own in (("every game", own_all), ("FBS v FBS", own_fbs), ("ratings only", own_elo_fbs)):
        ll = -(Y[q] * np.log(own[q]) + (1 - Y[q]) * np.log(1 - own[q]))
        out.append(f"{nm}: {ll.mean():.4f} (home said {100 * own[q & ~NEU].mean():.1f}%)")
    d = (-(Y[q] * np.log(own_fbs[q]) + (1 - Y[q]) * np.log(1 - own_fbs[q]))) - (-(Y[q] * np.log(own_all[q]) + (1 - Y[q]) * np.log(1 - own_all[q])))
    D.CELLS[0] += 3
    print(f"   {hf:8s} n {q.sum():5d} home won {100 * Y[q & ~NEU].mean():.1f}% | " + " | ".join(out) + f" | re-fit minus today's {d.mean():+.5f} (z {d.mean() / (d.std() / math.sqrt(q.sum())):+.1f})")
print("\ncells:", D.CELLS[0])
