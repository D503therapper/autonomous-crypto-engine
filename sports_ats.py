"""THE SPREAD vs MONEYLINE STUDY: when the book's moneyline and its spread disagree, who covers?

The moneyline implies a winning margin (a -198 favorite ~ by 5.5 in the NFL). When that's bigger than the spread
(-3.5), history says the UNDERDOG covers more than half the time (the favorite/longshot lean in the moneyline).
Per sport: P(home covers) = sigmoid(b * gap), gap = margin the moneyline implies - the spread's margin (home view),
fit on the older half and graded on the newer half it never saw. A sport only uses it once it's PROVEN (the side it
points to covered 52.4%+ on unseen games where the gap was 1+ point). Saved to data/sports/ats.json."""
import json
import math
import os

import sports_comeback as sc
import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "ats.json")
LEAGUES = ("nfl", "ncaaf", "nba", "ncaab")


def gap(g, league):
    p, line = sm.market_p(g), sm._num(g.get("spread_home"))
    if p is None or line is None:
        return None
    return sc.SIGMA[league] * sc.phi_inv(p) - (-line)


def rows(games, league):
    out = []
    for g in sm.finals(games, league):
        x = gap(g, league)
        try:
            m = int(g["home_score"]) - int(g["away_score"])
        except (TypeError, ValueError):
            continue
        line = sm._num(g.get("spread_home"))
        if x is None or m + line == 0:
            continue
        out.append((g["start"], x, 1 if m + line > 0 else 0))
    return sorted(out)


def _sig(z):
    return 1 / (1 + math.exp(-max(-30, min(30, z))))


def fit(rs):
    b = 0.0
    for _ in range(300):
        grad = sum((_sig(b * x) - y) * x for _, x, y in rs) / len(rs)
        b -= 0.05 * grad
    return b


def study(games, path=PATH):
    out = {}
    for lg in LEAGUES:
        rs = rows(games, lg)
        if len(rs) < 400:
            out[lg] = {"games": len(rs)}
            continue
        half = len(rs) // 2
        b = fit(rs[:half])
        test = [(x, y) for _, x, y in rs[half:] if abs(x) >= 1]
        hits = [y if _sig(b * x) > 0.5 else 1 - y for x, y in test]
        hit = sum(hits) / len(hits) if hits else 0.0
        out[lg] = {"games": len(rs), "test_games": len(test), "hit": round(hit, 4), "b": round(fit(rs), 5),
                   "proven": hit >= 0.524 and len(test) >= 100}
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


def adjust(st, league, g, p_home_cover):
    """The engine's home-cover chance, nudged by the moneyline/spread disagreement (proven sports only)."""
    s = st.get(league) or {}
    x = gap(g, league)
    if not s.get("proven") or x is None:
        return p_home_cover
    z = math.log(max(1e-6, p_home_cover) / max(1e-6, 1 - p_home_cover)) + s["b"] * x
    return _sig(z)


if __name__ == "__main__":
    for lg, v in study(sd.load_games()).items():
        print(lg, v)
