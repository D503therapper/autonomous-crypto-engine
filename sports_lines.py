"""THE PUCK LINE / RUN LINE STUDY: how often a team wins by 2+ (covers -1.5), learned from every past NHL / MLB final
with a closing line. Per sport: P(win by 2+) = sigmoid(a + b * logit(win chance) + c * home). The +1.5 side covers
unless the other team wins by 2+. Saved to data/sports/lines.json every engine run; ASK THE ENGINE reads it."""
import json
import math
import os

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "lines.json")
LEAGUES = ("nhl", "mlb")


def _logit(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _sig(x):
    return 1 / (1 + math.exp(-x))


def rows(games, league):
    """[(logit(win chance), home 1/0, won by 2+ 1/0)] - both teams of every real final with a closing line."""
    out = []
    for g in sm.finals(games, league):
        p = sm.market_p(g)
        try:
            m = int(g["home_score"]) - int(g["away_score"])
        except (TypeError, ValueError):
            continue
        if p is None:
            continue
        out.append((_logit(p), 1, 1 if m >= 2 else 0))
        out.append((_logit(1 - p), 0, 1 if m <= -2 else 0))
    return out


def fit(rs, steps=300, lr=0.5):
    """Logistic regression by gradient descent (small, 3 weights). Returns weights + log loss vs the base rate."""
    w = [0.0, 1.0, 0.0]
    n = len(rs)
    for _ in range(steps):
        g = [0.0, 0.0, 0.0]
        for x, h, y in rs:
            e = _sig(w[0] + w[1] * x + w[2] * h) - y
            g[0] += e
            g[1] += e * x
            g[2] += e * h
        w = [wi - lr * gi / n for wi, gi in zip(w, g)]
    base = sum(y for _, _, y in rs) / n

    def ll(f):
        return -sum(math.log(max(1e-9, f(x, h) if y else 1 - f(x, h))) for x, h, y in rs) / n
    return {"a": round(w[0], 4), "b": round(w[1], 4), "c": round(w[2], 4), "n": n,
            "ll": round(ll(lambda x, h: _sig(w[0] + w[1] * x + w[2] * h)), 4), "ll_base": round(ll(lambda x, h: base), 4)}


def study(games, path=PATH):
    out = {}
    for lg in LEAGUES:
        rs = rows(games, lg)
        out[lg] = fit(rs) if len(rs) >= 1000 else {"n": len(rs)}
    with open(path + ".tmp", "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)
    return out


def load():
    try:
        with open(PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def by_two(st, league, p_win, home):
    """Chance this team wins by 2+ (covers -1.5), or None when the study isn't in yet."""
    w = st.get(league) or {}
    if "a" not in w:
        return None
    return _sig(w["a"] + w["b"] * _logit(p_win) + w["c"] * (1 if home else 0))


def cover(st, league, p_home, side, line):
    """Chance `side` covers its puck/run line (line -1.5 or +1.5)."""
    home = side == "home"
    p_me = p_home if home else 1 - p_home
    if line < 0:
        return by_two(st, league, p_me, home)
    them = by_two(st, league, 1 - p_me, not home)
    return None if them is None else 1 - them


def summary(st):
    return "lines study: " + "; ".join(
        f"{lg} {v['n']} team-games, loss {v['ll_base']:.3f}->{v['ll']:.3f}" if "a" in v else f"{lg} {v.get('n', 0)} (not enough)"
        for lg, v in st.items())


if __name__ == "__main__":
    print(summary(study(sd.load_games())))
