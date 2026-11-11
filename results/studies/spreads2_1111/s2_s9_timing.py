"""S2. THE BEST TIME TO BET A SPREAD + S9. THE CLOSING LINE AS THE TARGET (NFL / college football).
The paid odds history holds ONE early-week spread look a game (the first FAIR one, ~5 days out NFL / ~4 college, every
book) and the game files hold the close - so "the path" here is Tuesday -> the close.
S2: which sides gain points by the close (favorite / dog, home / road, size, league), and what betting the first
    number (the market number at the median price, and the best book) returned against the same side at the close.
S9: a ridge on the spread's MOVE (first fair -> close) from things stamped at the first fair look only - the number,
    the book disagreement, where the sharp books sit against the pack, the juice lean on the market number, the best
    book vs the pack, last week's margins, rest, days out. Walk-forward (each season fit on the seasons before).
    If the called move is half a point+, does the first number cover 52.4%+ blind?
   python s2_s9_timing.py"""
import random, statistics
from collections import defaultdict
import numpy as np
import lib2 as L

o = L.Out("s2_s9")
B = L.B
random.seed(11)


def clean(books, med):
    return {bk: v for bk, v in books.items() if abs(v[0] - med) <= 1.5 and v[0] == -v[2] and -140 <= v[1] <= 125 and -140 <= v[3] <= 125}


def table(lg):
    fin = B.all_finals(lg)
    tl = B.team_log(fin)
    rows = []
    for g in L.football(lg):
        if g["c_sp"] is None or abs(g["c_sp"] - g["med"]) > (7 if lg == "nfl" else 10):
            continue
        bk = clean(g["first"][1], g["med"])
        if len(bk) < 5:
            continue
        med = statistics.median(v[0] for v in bk.values())
        lines = [v[0] for v in bk.values()]
        at = [(L.dec(v[1]), L.dec(v[3])) for v in bk.values() if v[0] == med]
        hd = statistics.median(a for a, _ in at) if at else L.dec(-110)
        ad = statistics.median(b for _, b in at) if at else L.dec(-110)
        sh = [v[0] for b, v in bk.items() if b in L.SHARP]
        besth = max(((v[0], L.dec(v[1])) for v in bk.values()))          # the home side's best number, then price
        besta = max(((v[2], L.dec(v[3])) for v in bk.values()))
        ph = B.before(tl, g["home"], g["start"], 1)
        pa = B.before(tl, g["away"], g["start"], 1)
        if not ph or not pa:
            continue
        lh, la = ph[-1], pa[-1]
        rows.append({"g": g, "season": g["season"], "med": med, "close": g["c_sp"], "mv": med - g["c_sp"],   # + = moved to the home side
                     "hd": hd, "ad": ad, "sd": statistics.pstdev(lines), "sharp": (statistics.mean(sh) - med) if sh else 0.0,
                     "lean": (1 / hd) - (1 / ad), "besth": besth, "besta": besta, "nb": len(bk), "days": g["first"][0],
                     "lmh": B.margin_g(lh, g["home"]), "lma": B.margin_g(la, g["away"]),
                     "rh": B.days_between(lh["start"], g["start"]), "ra": B.days_between(la["start"], g["start"]),
                     "neutral": g["neutral"], "total": g["total"] or 0.0, "m": g["margin"],
                     "cho": g["c_sho"] or -110, "cao": g["c_sao"] or -110})
    return rows


def side_rows(R):
    """one row a side: line at the first look (its own sign), points gained by the close, profits."""
    out = []
    for r in R:
        for side in ("home", "away"):
            ln = r["med"] if side == "home" else -r["med"]
            cl = r["close"] if side == "home" else -r["close"]
            d0 = r["hd"] if side == "home" else r["ad"]
            bl, bd = (r["besth"] if side == "home" else r["besta"])
            out.append({"r": r, "side": side, "season": r["season"], "line": ln, "gain": ln - cl,
                        "home": side == "home" and not r["neutral"], "road": side == "away" and not r["neutral"],
                        "p_first": L.cover(r["m"], r["med"], side, B.american(d0)),
                        "p_best": L.cover(r["m"], bl if side == "home" else -bl, side, B.american(bd)),
                        "p_close": L.cover(r["m"], r["close"], side, r["cho"] if side == "home" else r["cao"]),
                        "lm": r["lmh"] if side == "home" else r["lma"], "olm": r["lma"] if side == "home" else r["lmh"],
                        "rest": r["rh"] if side == "home" else r["ra"], "orest": r["ra"] if side == "home" else r["rh"]})
    return out


def tmean(xs):
    xs = list(xs)
    if len(xs) < 2:
        return "   -"
    m = statistics.mean(xs)
    se = statistics.pstdev(xs) / len(xs) ** 0.5
    return f"{m:+.2f} (t {m / se if se else 0:+.1f})"


CELLS = (("every dog", lambda s: s["line"] > 0),
         ("every favorite", lambda s: s["line"] < 0),
         ("home dog", lambda s: s["line"] > 0 and s["home"]),
         ("road dog", lambda s: s["line"] > 0 and s["road"]),
         ("home favorite", lambda s: s["line"] < 0 and s["home"]),
         ("road favorite", lambda s: s["line"] < 0 and s["road"]),
         ("dog +1..+3", lambda s: 1 <= s["line"] <= 3),
         ("dog +3.5..+7", lambda s: 3.5 <= s["line"] <= 7),
         ("dog +7.5..+14", lambda s: 7.5 <= s["line"] <= 14),
         ("dog +14.5+", lambda s: s["line"] >= 14.5),
         ("side off a 17+ win", lambda s: s["lm"] >= 17),
         ("side off a 17+ loss", lambda s: s["lm"] <= -17),
         ("dog off a 17+ loss", lambda s: s["line"] > 0 and s["lm"] <= -17),
         ("dog off a 17+ win", lambda s: s["line"] > 0 and s["lm"] >= 17),
         ("favorite off a loss", lambda s: s["line"] < 0 and s["lm"] < 0),
         ("dog off a bye (12+ days)", lambda s: s["line"] > 0 and s["rest"] >= 12),
         ("side the sharp books sit a half point toward", lambda s: (s["r"]["sharp"] if s["side"] == "home" else -s["r"]["sharp"]) <= -0.4),
         ("side the juice leans to (3+ cents)", lambda s: (s["r"]["lean"] if s["side"] == "home" else -s["r"]["lean"]) >= 0.012))

for lg in ("nfl", "ncaaf"):
    R = table(lg)
    S = side_rows(R)
    o(f"\n== S2. {lg.upper()}: {len(R)} games, first fair look -> the close ==")
    o(f"   the line moved (abs) {statistics.mean(abs(r['mv']) for r in R):.2f} points on average; a half point or more in {sum(1 for r in R if abs(r['mv']) >= .5) / len(R) * 100:.0f}% of games, 1.5+ in {sum(1 for r in R if abs(r['mv']) >= 1.5) / len(R) * 100:.0f}%")
    o(f"   {'cell':44s} {'n':>5s}  points gained by the close: train | held        ATS first number (median price) all / HELD | best book HELD | the close HELD")
    for name, f in CELLS:
        c = [s for s in S if f(s)]
        tr = [s for s in c if not L.held(s["season"])]
        he = [s for s in c if L.held(s["season"])]
        up = L.by_season([(s["season"], s["p_first"]) for s in he])
        o(f"   {name:44s} {len(c):5d}  {tmean(s['gain'] for s in tr):>16s} | {tmean(s['gain'] for s in he):>16s}   "
          f"{L.roi([s['p_first'] for s in c]):+5.1f}% / {L.st([s['p_first'] for s in he])[6:]} ({up[0]}/{up[1]}) | {L.roi([s['p_best'] for s in he]):+5.1f}% | {L.roi([s['p_close'] for s in he]):+5.1f}%")
    # what a point of closing-line value is worth, measured (the sides that gained)
    o("   WHAT THE MOVE IS WORTH (every side, by the points it gained by the close; ATS at the first number, median price):")
    for lo, hi in ((-99, -1.5), (-1.5, -0.5), (-0.5, 0.5), (0.5, 1.5), (1.5, 2.5), (2.5, 99)):
        c = [s for s in S if lo <= s["gain"] < hi] if lo != -0.5 else [s for s in S if -0.5 < s["gain"] < 0.5]
        o(f"      gained {lo:+.1f}..{hi:+.1f}: {L.st([s['p_first'] for s in c])}")

    # ---------------- S9 ----------------
    def feats(r):
        return [1.0, r["med"], abs(r["med"]), 1.0 if r["med"] > 0 else 0.0, r["sd"], r["sharp"], r["lean"] * 100,
                r["besth"][0] - r["med"], r["besta"][0] + r["med"], r["nb"] / 10, r["days"], r["lmh"] / 10, r["lma"] / 10,
                min(r["rh"], 15) / 7, min(r["ra"], 15) / 7, 1.0 if r["neutral"] else 0.0, r["total"] / 50]
    NAMES = ["const", "home line", "abs line", "home is dog", "book sd", "sharp books - pack", "juice lean to home (pts)",
             "best home number - market", "best away number - market", "books", "days out", "home last margin/10", "away last margin/10",
             "home rest", "away rest", "neutral", "total/50"]
    seasons = sorted({r["season"] for r in R})
    preds = []
    for ys in seasons[2:] if lg == "nfl" else seasons[1:]:
        tr = [r for r in R if r["season"] < ys]
        te = [r for r in R if r["season"] == ys]
        if len(tr) < 150 or not te:
            continue
        X = np.array([feats(r) for r in tr])
        mu, sdv = X[:, 1:].mean(0), X[:, 1:].std(0) + 1e-9
        Xs = np.c_[np.ones(len(X)), (X[:, 1:] - mu) / sdv]
        y = np.array([r["mv"] for r in tr])
        P = 30.0 * np.eye(Xs.shape[1])
        P[0, 0] = 1e-6
        w = np.linalg.solve(Xs.T @ Xs + P, Xs.T @ y)
        Xt = np.array([feats(r) for r in te])
        pt = np.c_[np.ones(len(Xt)), (Xt[:, 1:] - mu) / sdv] @ w
        for r, p in zip(te, pt):
            preds.append((r, float(p)))
        last_w = w
    o(f"\n== S9. {lg.upper()}: the called move, walk-forward ({len(preds)} games, seasons {sorted({r['season'] for r, _ in preds})}) ==")
    pr = np.array([p for _, p in preds])
    mv = np.array([r["mv"] for r, _ in preds])
    cc = float(np.corrcoef(pr, mv)[0, 1])
    sh = 0
    for _ in range(500):
        sh += abs(float(np.corrcoef(pr, np.random.permutation(mv))[0, 1])) >= abs(cc)
    o(f"   correlation called vs real move {cc:+.3f} (a shuffled target did as well {sh} of 500); direction right {np.mean(np.sign(pr[mv != 0]) == np.sign(mv[mv != 0])) * 100:.1f}% of the games that moved")
    o("   the last fit's weights (per sd): " + ", ".join(f"{n} {v:+.2f}" for n, v in sorted(zip(NAMES[1:], last_w[1:]), key=lambda x: -abs(x[1]))[:8]))
    for cut in (0.25, 0.5, 0.75, 1.0):
        bets = []
        for r, p in preds:
            if abs(p) < cut:
                continue
            side = "home" if p > 0 else "away"
            bl, bd = r["besth"] if side == "home" else r["besta"]
            d0 = r["hd"] if side == "home" else r["ad"]
            bets.append((r["season"], L.cover(r["m"], r["med"], side, B.american(d0)),
                         L.cover(r["m"], bl if side == "home" else -bl, side, B.american(bd)),
                         (p if side == "home" else -p), (r["mv"] if side == "home" else -r["mv"]),
                         L.cover(r["m"], r["close"], side, r["cho"] if side == "home" else r["cao"])))
        if not bets:
            o(f"   called move {cut}+ : none")
            continue
        up = L.by_season([(b[0], b[1]) for b in bets])
        o(f"   called move {cut:.2f}+: real move toward us {statistics.mean(b[4] for b in bets):+.2f} | first number, median price {L.st([b[1] for b in bets])} ({up[0]}/{up[1]} up: {up[2]}) | best book {L.st([b[2] for b in bets])} | the same side at the close {L.roi([b[5] for b in bets]):+.1f}%")
    # the other way round: the side the move is called AGAINST, bet at the close (wait for the better number)
    bets = [(r["season"], L.cover(r["m"], r["close"], "away" if p > 0 else "home", (r["cao"] if p > 0 else r["cho"]))) for r, p in preds if abs(p) >= 0.5]
    o(f"   the OTHER side at the close (wait for the number the move gives you), called 0.5+: {L.st([b[1] for b in bets])}")
o("\ncells read: 2 leagues x (18 cells x 5 numbers + 6 move bands + 4 called-move cuts x 3 prices) = ~230")
o.save()
