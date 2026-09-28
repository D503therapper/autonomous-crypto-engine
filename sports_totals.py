"""THE OVER/UNDER STUDY: can the engine beat the closing total?

For every real final with a closing total (the book's over/under), in time order, per sport:
  - each team's scoring and allowing, weighted toward recent games (no peeking: only games before this one)
  - our predicted total = (home scoring + away allowing)/2 + (away scoring + home allowing)/2, scaled to the league
  - P(over) = sigmoid(a + b * (our total - the line)), fit on the older 2/3, graded on the newest 1/3 it never saw
A sport only gets over/under reads when, on the games it never saw, our side hit more often than the 52.4% it takes
to beat -110 - and only on the games where we lean hardest (the confidence we'd actually bet at).
Saved to data/sports/totals.json."""
import json
import math
import os

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "totals.json")
ALPHA = {"nfl": 0.15, "ncaaf": 0.15, "nba": 0.07, "ncaab": 0.07, "mlb": 0.04, "nhl": 0.05}   # how fast form moves
BREAKEVEN = 0.524


def _sig(x):
    return 1 / (1 + math.exp(-max(-30, min(30, x))))


def rows(games, league):
    """[(our total - line, went over 1/0, line, start)] in time order (pushes left out)."""
    fin = sorted(sm.finals(games, league), key=lambda g: g["start"])
    a = ALPHA[league]
    off, dfn, n = {}, {}, {}
    tot_avg, k = None, 0
    out = []
    for g in fin:
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            continue
        h, w = g["home"], g["away"]
        line = sm._num(g.get("total"))
        if tot_avg is not None and line and n.get(h, 0) >= 5 and n.get(w, 0) >= 5:
            half = tot_avg / 2
            pred = (off[h] + dfn[w]) / 2 + (off[w] + dfn[h]) / 2
            pred = pred * 0.5 + tot_avg * 0.5 * (pred / (2 * half)) if half else pred
            if hs + as_ != line:
                out.append((pred - line, 1 if hs + as_ > line else 0, line, g["start"]))
        k += 1
        tot_avg = (hs + as_) if tot_avg is None else tot_avg + (hs + as_ - tot_avg) / min(k, 500)
        for t, pf, pa in ((h, hs, as_), (w, as_, hs)):
            if t not in off:
                off[t], dfn[t] = float(pf), float(pa)
            else:
                off[t] += a * (pf - off[t])
                dfn[t] += a * (pa - dfn[t])
            n[t] = n.get(t, 0) + 1
    return out


def fit(rs, steps=400, lr=0.3):
    sx = max(1e-9, (sum(x * x for x, *_ in rs) / len(rs)) ** 0.5)
    w = [0.0, 0.0]
    for _ in range(steps):
        g0 = g1 = 0.0
        for x, y, *_ in rs:
            e = _sig(w[0] + w[1] * x / sx) - y
            g0 += e
            g1 += e * x / sx
        w = [w[0] - lr * g0 / len(rs), w[1] - lr * g1 / len(rs)]
    return {"a": w[0], "b": w[1] / sx}


def grade(rs, fw, top=0.3):
    """Hit rate of our side on these games: all of them, and the top `top` share where we lean hardest."""
    scored = sorted(((abs(_sig(fw["a"] + fw["b"] * x) - 0.5), (_sig(fw["a"] + fw["b"] * x) > 0.5) == (y == 1))
                     for x, y, *_ in rs), reverse=True)
    allr = sum(h for _, h in scored) / len(scored)
    k = max(1, int(len(scored) * top))
    return round(allr, 4), round(sum(h for _, h in scored[:k]) / k, 4), k


def study(games, path=PATH):
    out = {}
    for lg in ALPHA:
        rs = rows(games, lg)
        if len(rs) < 1000:
            out[lg] = {"games": len(rs)}
            continue
        cut = len(rs) * 2 // 3
        fw = fit(rs[:cut])
        hit_all, hit_top, n_top = grade(rs[cut:], fw)
        full = fit(rs)
        out[lg] = {"games": len(rs), "test_games": len(rs) - cut, "hit_all": hit_all, "hit_top": hit_top, "n_top": n_top,
                   "a": round(full["a"], 5), "b": round(full["b"], 5),
                   "proven": hit_top > BREAKEVEN + 0.01}      # a real edge on games it never saw, with room to spare
    with open(path + ".tmp", "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)
    return out


def state(games, league):
    """Every team's current scoring/allowing form + the league's average total (for upcoming games)."""
    a = ALPHA[league]
    off, dfn, n = {}, {}, {}
    tot_avg, k = None, 0
    for g in sorted(sm.finals(games, league), key=lambda g: g["start"]):
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            continue
        k += 1
        tot_avg = (hs + as_) if tot_avg is None else tot_avg + (hs + as_ - tot_avg) / min(k, 500)
        for t, pf, pa in ((g["home"], hs, as_), (g["away"], as_, hs)):
            if t not in off:
                off[t], dfn[t] = float(pf), float(pa)
            else:
                off[t] += a * (pf - off[t])
                dfn[t] += a * (pa - dfn[t])
            n[t] = n.get(t, 0) + 1
    return {"off": off, "dfn": dfn, "n": n, "avg": tot_avg}


def p_over(fit, st, g):
    """Chance the game goes over its line, or None (not enough on both teams / no study)."""
    line = sm._num(g.get("total"))
    h, w = g["home"], g["away"]
    if "a" not in fit or not line or st["avg"] is None or st["n"].get(h, 0) < 5 or st["n"].get(w, 0) < 5:
        return None
    half = st["avg"] / 2
    pred = (st["off"][h] + st["dfn"][w]) / 2 + (st["off"][w] + st["dfn"][h]) / 2
    pred = pred * 0.5 + st["avg"] * 0.5 * (pred / (2 * half)) if half else pred
    return _sig(fit["a"] + fit["b"] * (pred - line))


def load():
    try:
        with open(PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


if __name__ == "__main__":
    for lg, v in study(sd.load_games()).items():
        print(lg, v)
