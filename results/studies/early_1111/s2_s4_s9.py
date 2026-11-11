"""S2 / S4 / S9 on the paid football odds history (fair looks only; every input is stamped at or before the decision
look; TRAIN 2020-22, HELD OUT 2023-26).
S2 - WHO MOVES FIRST: for every pair of back-to-back fair looks, does the rest of the market move TOWARD where a book
     already was? beta = (the other books' median move to the next look) per point this book sat off their median now.
     A high beta = the book leads. Ranked on the train seasons, re-measured held out. Then the dog's "lead-book gap"
     at the first fair number (the train-ranked lead books minus the median): does it call the move, and does it pay?
S4 - PREDICTING THE MOVE: a ridge fit of the dog's move (first fair number -> the close, points) on what's known at
     the first fair number - our read vs the price, the price, home / neutral, the spots, both teams' last margins,
     rest, how far the books disagree, the lead-book gap, the best book vs the median, books posted, days out, hours
     since the number was fair, last season's win % (how public the team is), and (2023+ only) the opener -> first
     fair move. Fit on the train seasons, graded blind: the hit rate on direction, the move by predicted fifth, the
     ROI by predicted fifth, a shuffled-target placebo, and 'bet now if the move is called toward us, else wait'.
S9 - SIZING BY THE EXPECTED MOVE: the blind ROI at the first fair price by the predicted move - does the top of the
     model pay more than the bottom?
NOT IN HERE (said plainly): the public split and injury news. The public file holds one final split a game (no time
stamp - using it at the first fair number would be look-ahead); the injury file is live-only (S7 reads the NFL's)."""
import random
import statistics

import numpy as np

import base
import elib as E

out = E.Tee("s2_s4_s9_out.txt")
ROWS = {lg: base.build(lg) for lg in ("nfl", "ncaaf")}

# ------------------------------------------------------------------ S2
out("=" * 30, "S2 - WHO MOVES FIRST (beta: points the OTHER books move by the next look per point this book sits off "
    "them now; home side of every game, back-to-back fair looks)")
LEAD = {}
for lg in ("nfl", "ncaaf"):
    acc = {}
    for r in ROWS[lg]:
        if not r["home"]:
            continue
        lk = r["looks"]
        for a, b in zip(lk, lk[1:]):
            if a[0] - b[0] > 3.5 or len(a[5]) < 5:
                continue
            for bk, pb in a[5].items():
                oth_a = [p for k, p in a[5].items() if k != bk]
                oth_b = [p for k, p in b[5].items() if k != bk]
                if len(oth_a) < 4 or len(oth_b) < 4:
                    continue
                dev = (pb - statistics.median(oth_a)) * 100
                mvv = (statistics.median(oth_b) - statistics.median(oth_a)) * 100
                own_mv = (b[5][bk] - pb) * 100 if bk in b[5] else None
                acc.setdefault(bk, []).append((r["season"], dev, mvv, own_mv))
    res = []
    for bk, v in acc.items():
        def beta(vs):
            if len(vs) < 150:
                return None
            x = np.array([a[1] for a in vs])
            y = np.array([a[2] for a in vs])
            return float((x * y).sum() / (x * x).sum()) if (x * x).sum() else None

        def back(vs):                                  # how much of its own gap the book gives back (it FOLLOWS)
            vs = [a for a in vs if a[3] is not None]
            if len(vs) < 150:
                return None
            x = np.array([a[1] for a in vs])
            y = np.array([a[3] for a in vs])
            return float(-(x * y).sum() / (x * x).sum())
        tr = [a for a in v if a[0] <= 2022]
        he = [a for a in v if a[0] >= 2023]
        res.append((bk, len(v), beta(tr), beta(he), back(v), statistics.pstdev([a[1] for a in v])))
    res.sort(key=lambda x: -(x[2] if x[2] is not None else -9))
    out(f"\n {lg}: book, looks, beta TRAIN, beta HELD, share of its own gap it gives back, how far it usually sits off (pts)")
    for bk, n, bt, bh, bb, sdv in res:
        out(f"   {bk:16s} n {n:5d}  lead TRAIN {('%+.2f' % bt) if bt is not None else '  -  '}  HELD "
            f"{('%+.2f' % bh) if bh is not None else '  -  '}  gives back {('%.2f' % bb) if bb is not None else ' - '}  off by {sdv:.2f}")
    LEAD[lg] = [bk for bk, n, bt, bh, bb, sdv in res if bt is not None][:4]
    out(f"   -> the lead books by the train seasons: {LEAD[lg]}")


def lead_gap(lg, look):
    """the train-ranked lead books' no-vig % for this side minus the median of every book, points (None under 2)."""
    v = [look[5][b] for b in LEAD[lg] if b in look[5]]
    if len(v) < 2:
        return None
    return (statistics.mean(v) - statistics.median(look[5].values())) * 100


def pl(r, o):
    return (E.dec(o) - 1) if r["won"] else -1.0


out("\n S2b - the dog's LEAD-BOOK GAP at the first fair number (lead books minus the median, + = the lead books like "
    "the dog MORE than the pack) -> the move to the close, and the ROI at the median price")
for lg in ("nfl", "ncaaf"):
    pop = [(r, base.first_fair(r)) for r in ROWS[lg] if base.first_fair(r) and 100 <= base.first_fair(r)[2] <= 350]
    pop = [(r, f, lead_gap(lg, f)) for r, f in pop]
    pop = [x for x in pop if x[2] is not None]
    for nm, lo, hi in (("lead books 1+ pt HIGHER on the dog", 1, 99), ("0.4 to 1 higher", 0.4, 1), ("inside 0.4", -0.4, 0.4),
                       ("0.4 to 1 lower", -1, -0.4), ("lead books 1+ pt LOWER on the dog", -99, -1)):
        for tag, sel in (("TRAIN", lambda s: s <= 2022), ("HELD", lambda s: s >= 2023)):
            v = [(r, f) for r, f, g in pop if lo <= g < hi and sel(r["season"])]
            if len(v) < 10:
                continue
            m = [(r["close_p"] - f[3]) * 100 for r, f in v]
            gd = [(base.game_day(r)[3] - f[3]) * 100 for r, f in v if base.game_day(r)]
            out(f"   {lg} {nm:36s} {tag:5s} move to the close {E.mean(m):+5.2f} (t {E.tstat(m):+4.1f}), to the game-day "
                f"look {E.mean(gd):+5.2f} | ROI at the median {E.roi([pl(r, f[2]) for r, f in v])} | at the BEST book "
                f"{E.mean([pl(r, f[4]) for r, f in v]) * 100:+.1f}%")

# ------------------------------------------------------------------ S4
out("\n" + "=" * 30, "S4 - PREDICTING THE MOVE (dogs +100..+350 at the first fair number; target = the close's no-vig % "
    "minus the first fair number's, points; + = toward the dog)")
PUBLIC_NFL = None


def prior_win(rows):
    """{(team, season): last season's win share} from the base rows themselves (results before the season)."""
    w = {}
    for r in rows:
        k = (r["team"], r["season"] + 1)
        a = w.setdefault(k, [0, 0])
        a[0] += 1 if r["won"] else 0
        a[1] += 1
    return {k: a[0] / a[1] for k, a in w.items() if a[1] >= 6}


NAMES = ["gap", "price", "home", "neutral", "bye", "mnf", "eastwest", "blowout", "last_margin", "opp_last_margin",
         "rest_diff", "disp", "lead_gap", "best_gap", "nbooks", "days_out", "hrs_fair", "prior_win", "opp_prior_win"]


def feats(lg, r, f, pw, opp_lm, with_open=False):
    sp = base.spots(r, f)
    g = lead_gap(lg, f)
    x = [((r["own"] - f[3]) * 100) if r["own"] is not None else 0.0,
         f[3] * 100, 1.0 if r["home"] else 0.0, 1.0 if r["neutral"] else 0.0,
         1.0 if "bye" in sp else 0.0, 1.0 if "mnf" in sp else 0.0, 1.0 if "eastwest" in sp else 0.0,
         1.0 if "blowout" in sp else 0.0,
         max(-30, min(30, r["last_margin"] or 0.0)), max(-30, min(30, opp_lm or 0.0)),
         max(-7, min(7, (r["rest"] or 7) - (r["orest"] or 7))),
         statistics.pstdev(f[5].values()) * 100, g if g is not None else 0.0,
         (1 / E.dec(f[2]) - 1 / E.dec(f[4])) * 100, float(len(f[5])), f[0], min(120.0, f[1] if f[1] is not None else 60.0),
         pw.get((r["team"], r["season"]), 0.5), pw.get((r["opp"], r["season"]), 0.5)]
    if with_open:
        x.append((f[3] - r["open_p"]) * 100 if r["open_p"] is not None else 0.0)
    return x


def ridge(X, y, lam=10.0):
    mu, sd_ = X.mean(0), X.std(0)
    sd_[sd_ == 0] = 1.0
    Z = (X - mu) / sd_
    w = np.linalg.solve(Z.T @ Z + lam * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return lambda Xn: ((Xn - mu) / sd_) @ w + y.mean(), w


PRED = {}
for lg in ("nfl", "ncaaf"):
    rows = ROWS[lg]
    pw = prior_win(rows)
    byg = {}
    for r in rows:
        byg[(r["id"], r["side"])] = r
    data = []
    for r in rows:
        f = base.first_fair(r)
        if not f or not 100 <= f[2] <= 350:
            continue
        o = byg.get((r["id"], "away" if r["home"] else "home"))
        data.append((r, f, o["last_margin"] if o else None))
    for label, with_open, tr_sel, te_sel in (
            ("A: no opener (train 2020-22 -> blind 2023-26)", False, lambda s: s <= 2022, lambda s: s >= 2023),
            ("B: + the opener -> first fair move (train 2023-24 -> blind 2025-26)", True,
             lambda s: s in (2023, 2024), lambda s: s >= 2025)):
        d = [x for x in data if (not with_open) or x[0]["open_p"] is not None]
        tr = [x for x in d if tr_sel(x[0]["season"])]
        te = [x for x in d if te_sel(x[0]["season"])]
        if len(tr) < 150 or len(te) < 100:
            out(f"\n {lg} {label}: too few ({len(tr)} / {len(te)})")
            continue
        names = NAMES + (["open_move"] if with_open else [])
        Xtr = np.array([feats(lg, r, f, pw, ol, with_open) for r, f, ol in tr])
        ytr = np.array([(r["close_p"] - f[3]) * 100 for r, f, ol in tr])
        Xte = np.array([feats(lg, r, f, pw, ol, with_open) for r, f, ol in te])
        yte = np.array([(r["close_p"] - f[3]) * 100 for r, f, ol in te])
        model, w = ridge(Xtr, ytr)
        p = model(Xte)
        corr = float(np.corrcoef(p, yte)[0, 1])
        corr_tr = float(np.corrcoef(model(Xtr), ytr)[0, 1])
        out(f"\n {lg} {label}: train {len(tr)}, blind {len(te)}")
        out(f"   fit: train corr {corr_tr:+.3f}; BLIND corr {corr:+.3f} (t {corr * (len(te) - 2) ** 0.5 / (1 - corr * corr) ** 0.5:+.1f}); "
            f"the move's own spread {yte.std():.2f} pts, the model's {p.std():.2f}")
        out("   weights (per 1 sd of the input, points of move): " + ", ".join(
            f"{n} {x:+.2f}" for n, x in sorted(zip(names, w), key=lambda t: -abs(t[1]))[:10]))
        # placebo: shuffle the train target
        rnd = random.Random(7)
        pc = []
        for _ in range(300):
            ys = ytr.copy()
            rnd.shuffle(ys)
            m2, _ = ridge(Xtr, ys)
            pc.append(float(np.corrcoef(m2(Xte), yte)[0, 1]))
        out(f"   placebo (the train moves shuffled, 300 fits): blind corr beats ours {sum(1 for c in pc if c >= corr)} of 300 "
            f"(the shuffles' 95th pct {sorted(pc)[284]:+.3f})")
        order = np.argsort(p)
        n5 = len(te) // 5
        out("   by the predicted fifth (blind): predicted / actual move to the close / share that came 1+ toward / "
            "ROI at the first fair price / ROI at the close")
        for q in range(5):
            idx = order[q * n5:(q + 1) * n5 if q < 4 else len(te)]
            act = [yte[i] for i in idx]
            a = [pl(te[i][0], te[i][1][2]) for i in idx]
            c = [pl(te[i][0], te[i][0]["close_o"]) for i in idx]
            out(f"     fifth {q + 1}: predicted {np.mean([p[i] for i in idx]):+5.2f} | actual {E.mean(act):+5.2f} (t {E.tstat(act):+4.1f}) | "
                f"toward 1+ {sum(1 for x in act if x >= 1) / len(act) * 100:3.0f}% / away 1+ {sum(1 for x in act if x <= -1) / len(act) * 100:3.0f}% | "
                f"first fair {E.roi(a)} | close {E.mean(c) * 100:+6.1f}%")
        big = [i for i in range(len(te)) if abs(yte[i]) >= 1]
        hit = sum(1 for i in big if (p[i] - np.median(p) > 0) == (yte[i] > 0))
        out(f"   direction (games that moved 1+ pt): the model's side of its own median called {hit} of {len(big)} "
            f"({hit / len(big) * 100:.1f}%)")
        # act on it: bet now when the move is called toward (top 40%), wait for the game-day look when called away (bottom 40%)
        now_, wait_, mix = [], [], []
        hi_cut, lo_cut = np.quantile(p, 0.6), np.quantile(p, 0.4)
        for i, (r, f, ol) in enumerate(te):
            gd = base.game_day(r)
            if not gd:
                continue
            a, b = pl(r, f[2]), pl(r, gd[2])
            now_.append(a)
            wait_.append(b)
            mix.append(a if p[i] >= hi_cut else b if p[i] <= lo_cut else a)
        out(f"   WAIT OR BET NOW on the model (blind, the same {len(now_)} dogs): always at the first fair {E.mean(now_) * 100:+.2f}% | "
            f"always at the game-day look {E.mean(wait_) * 100:+.2f}% | the model picks {E.mean(mix) * 100:+.2f}% "
            f"(vs always-now {E.mean([m - n for m, n in zip(mix, now_)]) * 100:+.2f}% a bet, t {E.tstat([m - n for m, n in zip(mix, now_)]):+.1f})")
        if not with_open:
            PRED[lg] = (te, p, yte)

out("\n" + "=" * 30, "S9 - SIZING BY THE EXPECTED MOVE (blind 2023-26, model A; the SPOT dogs only - what the engine posts)")
for lg in ("nfl", "ncaaf"):
    te, p, yte = PRED[lg]
    sp = [(i, r, f) for i, (r, f, ol) in enumerate(te) if base.spots(r, f)]
    cut_hi, cut_lo = np.quantile(p, 2 / 3), np.quantile(p, 1 / 3)
    for nm, sel in (("move called TOWARD us (top third)", lambda v: v >= cut_hi),
                    ("middle third", lambda v: cut_lo < v < cut_hi),
                    ("move called AWAY (bottom third)", lambda v: v <= cut_lo)):
        v = [(r, f, yte[i]) for i, r, f in sp if sel(p[i])]
        if not v:
            continue
        out(f"   {lg} spot dogs | {nm:36s} actual move {E.mean(x[2] for x in v):+5.2f} | first fair "
            f"{E.roi([pl(r, f[2]) for r, f, _ in v])} | z vs the price {E.zwin([(r['won'], f[3]) for r, f, _ in v]):+.2f}")
    allv = [(r, f, yte[i]) for i, (r, f, ol) in enumerate(te)]
    for nm, sel in (("every dog: top third", lambda v: v >= cut_hi), ("every dog: bottom third", lambda v: v <= cut_lo)):
        v = [(te[i][0], te[i][1]) for i in range(len(te)) if sel(p[i])]
        out(f"   {lg} {nm:47s} first fair {E.roi([pl(r, f[2]) for r, f in v])} | z vs the price "
            f"{E.zwin([(r['won'], f[3]) for r, f in v]):+.2f}")
