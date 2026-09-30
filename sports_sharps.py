"""OUR ENGINE vs THE MOVE (the owner, 9/29, after the Astros opened -143, the money ran to the
White Sox all day, and they got smacked): can our engine beat the pros?

What 10 seasons say (9/29): a favorite the money runs away from (its no-vig price drops 4+ points from the open) wins
about what the CLOSING price says - far less than the opening price said - in every league, old seasons and new.
So the pros are right on average. The owner: we don't just follow them - the engine should know when they're wrong.

So this study asks it straight, every run: in each league, when the money moved against a side and OUR OWN read (the
ratings, no market in it) still had that side at or above its opening price, did it win more than the closing price
said? Learned on the older half, graded on the newer half it never saw. Only a league where BOTH halves beat the
closing price (and the profit holds betting at the close) is proven - and only there may a pick go against the move.
Until then the engine respects the move (sports.fighting). (sports_moves asks the other question - does FOLLOWING
the move beat the close? No: the closing price is right.)"""
import json
import os
import statistics as st

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "sharps.json")
DRIFT = 0.04          # the study's "the money moved": 4+ points of no-vig price
MIN_N = 60            # games per half before a cell can prove anything
BEAT = 0.03           # won 3+ points more than the closing price said, in both halves
LEAGUES = ("mlb", "nhl", "nba", "nfl", "ncaab", "ncaaf")


def _imp(ml):
    ml = float(ml)
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def _nv(a, b):
    x, y = _imp(a), _imp(b)
    return x / (x + y)


def rows(games, model, lg):
    """(season, p_open, p_close, our own read, won, close price implied) for every side the money moved against."""
    p = (model.get("params") or {}).get(lg) or sm.default_params(lg)
    _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
    out = []
    for g, f, *_ in played:
        try:
            ho, ao, hc, ac = (float(g[k]) for k in ("ml_home_open", "ml_away_open", "ml_home", "ml_away"))
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (ValueError, KeyError, TypeError):
            continue
        if hs == as_:
            continue
        po, pc, own = _nv(ho, ao), _nv(hc, ac), sm.own_p(p, f)
        for p_o, p_c, o, won, cl in ((po, pc, own, hs > as_, hc), (1 - po, 1 - pc, 1 - own, as_ > hs, ac)):
            if p_o - p_c >= DRIFT:
                out.append((g["start"][:4], p_o, p_c, o, won, _imp(cl)))
    return out


def _half(S):
    if len(S) < MIN_N:
        return None
    return {"n": len(S), "won": round(sum(r[4] for r in S) / len(S), 4), "close": round(st.mean(r[2] for r in S), 4),
            "roi_close": round(sum(((1 / r[5] - 1) if r[4] else -1) for r in S) / len(S), 4)}


def study(games, model=None):
    if model is None:
        try:
            model = json.load(open(os.path.join(sd.DATA, "model.json")))
        except (OSError, ValueError):
            model = {}
    res, proven = {}, []
    for lg in LEAGUES:
        R = [r for r in rows(games, model, lg) if r[3] >= r[1]]        # our read still at/above the opening price
        if not R:
            continue
        yrs = sorted({r[0] for r in R})
        mid = yrs[len(yrs) // 2]
        old, new = _half([r for r in R if r[0] < mid]), _half([r for r in R if r[0] >= mid])
        ok = bool(old and new and all(h["won"] - h["close"] >= BEAT and h["roi_close"] > 0 for h in (old, new)))
        res[lg] = {"old": old, "new": new, "proven": ok}
        if ok:
            proven.append(lg)
    out = {"leagues": res, "proven": proven}
    with open(PATH + ".tmp", "w") as f:
        json.dump(out, f, indent=1)
    os.replace(PATH + ".tmp", PATH)
    return out


_CACHE = {}


def beats_the_move(league):
    """True only where the study proved our engine beats the pros after the money moves (none yet, 9/29)."""
    if "p" not in _CACHE:
        try:
            _CACHE["p"] = set(json.load(open(PATH)).get("proven") or [])
        except (OSError, ValueError):
            _CACHE["p"] = set()
    return league in _CACHE["p"]
