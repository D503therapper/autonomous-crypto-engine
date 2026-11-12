"""11/12 DEEP PROGRAM - A4: THE WHOLE BLEND, WALKED FORWARD (sports_model.tune step 3: trust in the ratings read, the
line move, the favorite / longshot dial 'cal', the home-dog dial 'hdog'). The live tune fits the four on the LAST 900
games with odds, lam 8, the trust pulled to 0.15. Here every game is priced by dials fit ONLY on earlier games (the
ratings at today's reaction speed / home edge; the ratings read's weights re-fit each August on the 8,000 games
before), re-fit every 150 games, six ways - and the question is which way of fitting gives a read that says what happens.
  live        = last 900, lam 8, trust prior 0.15                 (today's code)
  all8        = every earlier game, lam 8, priors 0
  all80       = every earlier game, lam 80, priors 0
  all400      = every earlier game, lam 400, priors 0
  win400      = last 900, lam 400, priors 0
  market      = the no-vig close as is
Printed: log loss against the close (z of the per-game difference), the dials' swing, the calibration of the cells the
board leans on, and what the 'own read over the price' gate picks under each fit.
Usage: python results/studies/deep_1112/a4_trust.py [league ...] > results/studies/deep_1112/a4_trust.out"""
import math, os, sys
import numpy as np
import dlib as D

sys.path.insert(0, D.ROOT)
os.chdir(D.ROOT)             # (sports_data reads data/sports relative to the repo root)
import json                      # noqa: E402
import sports_data as sd         # noqa: E402
import sports_model as sm        # noqa: E402

MODEL = json.load(open(os.path.join(D.ROOT, "data/sports/model.json")))


def irls(X, y, off, prior, lam, iters=40):
    w = np.array(prior, float)
    pr = np.array(prior, float)
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(off + X @ w, -30, 30)))
        g = X.T @ (p - y) + lam * (w - pr)
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(len(w))
        step = np.linalg.solve(H, g)
        w = w - step
        if np.max(np.abs(step)) < 1e-8:
            break
    return w


def season_of(start):
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 8 else y - 1


def run(lg):
    games = sd.load_games(lg)
    p0 = MODEL["params"][lg]
    _, rows = sm.replay(sm.finals(games, lg), p0["k"], p0["hfa"], lg)
    rows = [r for r in rows if r[2] != 0.5]
    X = np.array([sm._own_x(f) for _, f, _, _ in rows])
    y = np.array([r[2] for r in rows])
    seas = np.array([season_of(r[0]["start"]) for r in rows])
    own = np.full(len(rows), np.nan)
    prior = [0.0, 1.0] + [0.0] * (len(sm.FEATURES) - 1)
    for s in sorted(set(seas)):
        idx = np.where(seas == s)[0]
        before = np.where(seas < s)[0]
        if len(before) < 500:
            continue
        tr = before[-sm.TRAIN_GAMES:]
        w = irls(X[tr], y[tr], np.zeros(len(tr)), prior, 5.0)
        own[idx] = 1 / (1 + np.exp(-np.clip(X[idx] @ w, -30, 30)))
    # rows with odds and an own read
    R = []
    for i, (g, f, yy, m) in enumerate(rows):
        mk = sm.market_p(g)
        if mk is None or np.isnan(own[i]) or not 0.005 < mk < 0.995:
            continue
        R.append({"g": g, "m": mk, "lm": sm.logit(mk), "own": float(own[i]), "do": sm.logit(float(own[i])) - sm.logit(mk),
                  "mv": sm.line_move(g), "hd": sm.home_dog(mk, g), "y": yy, "season": int(seas[i])})
    print(f"\n==== {lg.upper()}: {len(R)} games with a close and a walk-forward ratings read ({R[0]['g']['start'][:10]} -> {R[-1]['g']['start'][:10]}); "
          f"today's dials: trust {p0['trust']:.3f} move {p0['move_w']:+.3f} cal {p0.get('cal', 0):+.3f} hdog {p0.get('hdog', 0):+.3f}")
    XX = np.array([[r["do"], r["mv"], r["lm"], r["hd"]] for r in R])
    Y = np.array([r["y"] for r in R])
    OFF = np.array([r["lm"] for r in R])
    wl, _ = None, None
    full = irls(XX, Y, OFF, [0, 0, 0, 0], 1e-6)
    H = (XX * ((1 / (1 + np.exp(-(OFF + XX @ full)))) * (1 - 1 / (1 + np.exp(-(OFF + XX @ full)))))[:, None]).T @ XX
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    print("  the LONG-RUN dials (every game, no pull): " + "  ".join(f"{n} {v:+.3f} (se {s:.3f})" for n, v, s in zip(("trust", "move_w", "cal", "hdog"), full, se)))
    for nm, sel in (("to 2021", lambda r: r["season"] <= 2021), ("2022 on", lambda r: r["season"] >= 2022)):
        ix = [i for i, r in enumerate(R) if sel(r)]
        if len(ix) > 300:
            wv = irls(XX[ix], Y[ix], OFF[ix], [0, 0, 0, 0], 1e-6)
            print(f"     {nm}: " + "  ".join(f"{n} {v:+.3f}" for n, v in zip(("trust", "move_w", "cal", "hdog"), wv)) + f"  (n {len(ix)})")
    FITS = {"live": (900, 8.0, [0.15, 0, 0, 0]), "all8": (None, 8.0, [0, 0, 0, 0]), "all80": (None, 80.0, [0, 0, 0, 0]),
            "all400": (None, 400.0, [0, 0, 0, 0]), "win400": (900, 400.0, [0, 0, 0, 0])}
    P = {k: np.full(len(R), np.nan) for k in FITS}
    POWN = {k: np.full(len(R), np.nan) for k in FITS}        # the read without the line move (the 'own read')
    W = {k: [] for k in FITS}
    for i in range(900, len(R), 150):
        j = min(len(R), i + 150)
        for k, (win, lam, pr) in FITS.items():
            lo = i - win if win else 0
            w = irls(XX[lo:i], Y[lo:i], OFF[lo:i], pr, lam)
            w[0] = min(1.0, max(0.0, w[0]))
            W[k].append(w)
            P[k][i:j] = 1 / (1 + np.exp(-(OFF[i:j] + XX[i:j] @ w)))
            w2 = w.copy()
            w2[1] = 0.0
            POWN[k][i:j] = 1 / (1 + np.exp(-(OFF[i:j] + XX[i:j] @ w2)))
    ok = ~np.isnan(P["live"])
    M = np.array([r["m"] for r in R])

    def lls(p):
        return -(Y * np.log(p) + (1 - Y) * np.log(1 - p))
    base = lls(M)[ok]
    print(f"  the honest test on {ok.sum()} games:")
    for k in FITS:
        D.CELLS[0] += 1
        d = lls(P[k])[ok] - base
        z = d.mean() / (d.std() / math.sqrt(len(d)))
        ws = np.array(W[k])
        print(f"    {k:7s} logloss {lls(P[k])[ok].mean():.5f} ({d.mean():+.5f} vs the close, z {z:+.1f}) | dials mean (sd): "
              + "  ".join(f"{n} {ws[:, c].mean():+.3f} ({ws[:, c].std():.3f})" for c, n in enumerate(("trust", "move", "cal", "hdog")))
              + f" | last fit: " + " ".join(f"{v:+.3f}" for v in ws[-1]))
    print(f"    market  logloss {base.mean():.5f}")
    # the own-read gate under each fit
    for k in ("live", "all8", "all80", "all400"):
        for lab, side in (("home", 1), ("road", 0)):
            for band, f in (("fav -150..-101", lambda o: -150 <= o <= -101), ("dog +100..+350", lambda o: 100 <= o <= 350)):
                sel = []
                for i, r in enumerate(R):
                    if not ok[i]:
                        continue
                    o = sm._int(r["g"]["ml_home" if side else "ml_away"])
                    if o is None or not f(o):
                        continue
                    pp = POWN[k][i] if side else 1 - POWN[k][i]
                    if pp > 1 / D.dec(o):
                        sel.append({"dec": D.dec(o), "y": r["y"] if side else 1 - r["y"], "season": r["season"], "half": "train" if r["season"] <= 2021 else "held"})
                D.cell(f"{k}: {lab} {band}, own read OVER the price", sel)
    for lab, side in (("home", 1), ("road", 0)):
        for band, f in (("fav -150..-101", lambda o: -150 <= o <= -101), ("dog +100..+350", lambda o: 100 <= o <= 350)):
            al = []
            for i, r in enumerate(R):
                o = sm._int(r["g"]["ml_home" if side else "ml_away"])
                if ok[i] and o is not None and f(o):
                    al.append({"dec": D.dec(o), "y": r["y"] if side else 1 - r["y"], "season": r["season"], "half": "train" if r["season"] <= 2021 else "held"})
            D.cell(f"BASE: every {lab} {band}", al)
    # the 56% Lock line: favorites -150..-101 the blended read has at 56%+ vs under
    for k in ("live", "all80"):
        for nm, f in (("56%+", lambda p: p >= 0.56), ("under 56%", lambda p: p < 0.56)):
            sel = []
            for i, r in enumerate(R):
                if not ok[i]:
                    continue
                for side in (1, 0):
                    o = sm._int(r["g"]["ml_home" if side else "ml_away"])
                    if o is None or not -150 <= o <= -101:
                        continue
                    pp = P[k][i] if side else 1 - P[k][i]
                    if f(pp):
                        sel.append({"dec": D.dec(o), "y": r["y"] if side else 1 - r["y"], "season": r["season"], "half": "train" if r["season"] <= 2021 else "held", "p": pp})
            c = D.cell(f"{k}: favorites -150..-101 read at {nm}", sel)
            if sel:
                print(f"        said {100 * sum(x['p'] for x in sel) / len(sel):.1f}% won {100 * sum(x['y'] for x in sel) / len(sel):.1f}%")


if __name__ == "__main__":
    for lg in (sys.argv[1:] or ("nfl", "ncaaf", "nba", "ncaab", "nhl", "mlb")):
        run(lg)
    print("\ncells:", D.CELLS[0])
