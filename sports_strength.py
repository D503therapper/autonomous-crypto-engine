"""THE ENGINE'S STRENGTHS, SPORT BY SPORT (the owner, 9/29: "train the algorithm on its strengths").

Judged on thousands of games, never a bad night: for every sport, every side the engine would really have picked (its
win % 55%+, no favorite shorter than -150), replayed with the ratings as they stood BEFORE each game - what it said vs
how often those sides actually won, and vs the price.

Two things come out of it, both used by the picks:
  1. HONEST NUMBERS: a sport whose "58%" really wins 55% gets its percentages corrected by that gap (only with 200+
     picks behind it, capped at -6 / +2 points) - so an overconfident sport stops outranking the others.
  2. THE STRENGTHS GATE: a sport PROVEN weak - 200+ picks in EACH half, below the price AND losing money in both the
     older and the newer half of the games - can't be the Lock, the Dog or a parlay leg. A sport with too few games to judge is
     never barred (it has to be proven weak first).
Reruns with the studies (three times a day), so a sport that gets better earns its spot back on its own."""
import json
import os

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "strength.json")
LEAGUES = ("mlb", "nfl", "ncaaf", "nba", "ncaab", "nhl")
PICK_P, MAX_FAV = 0.55, -150
MIN_N = 200
BIAS_LO, BIAS_HI = -0.06, 0.02


def _dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def rows(games, model, lg):
    """(start, engine %, market %, won, decimal odds) for every side the engine would have picked."""
    p = (model.get("params") or {}).get(lg) or sm.default_params(lg)
    _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
    out = []
    for g, f, *_ in played:
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
            oh, oa = int(g["ml_home"]), int(g["ml_away"])
        except (ValueError, KeyError, TypeError):
            continue
        if hs == as_:
            continue
        ph, mk = sm.final_p(p, f, g), sm.market_p(g)
        if ph is None or mk is None:
            continue
        for pp, m, o, won in ((ph, mk, oh, hs > as_), (1 - ph, 1 - mk, oa, as_ > hs)):
            if pp >= PICK_P and o >= MAX_FAV:
                out.append((g["start"], pp, m, won, _dec(o)))
    out.sort()
    return out


def _sum(R):
    n = len(R)
    return {"n": n, "said": round(sum(r[1] for r in R) / n, 4), "won": round(sum(r[3] for r in R) / n, 4),
            "price": round(sum(r[2] for r in R) / n, 4),
            "roi": round(sum((r[4] - 1) if r[3] else -1 for r in R) / n, 4)} if n else {"n": 0}


def study(games, model=None):
    if model is None:
        try:
            model = json.load(open(os.path.join(sd.DATA, "model.json")))
        except (OSError, ValueError):
            model = {}
    out = {}
    for lg in LEAGUES:
        R = rows(games, model, lg)
        if not R:
            continue
        half = len(R) // 2
        allr, old, new = _sum(R), _sum(R[:half]), _sum(R[half:])
        bias = max(BIAS_LO, min(BIAS_HI, allr["won"] - allr["said"])) if allr["n"] >= MIN_N else 0.0
        weak = bool(all(h["n"] >= MIN_N and h["won"] < h["price"] and h["roi"] < 0 for h in (old, new)))   # 200+ EACH half
        out[lg] = {**allr, "old": old, "new": new, "bias": round(bias, 4), "weak": weak}
    with open(PATH + ".tmp", "w") as f:
        json.dump(out, f, indent=1)
    os.replace(PATH + ".tmp", PATH)
    _CACHE.clear()
    return {"proven": [lg for lg, v in out.items() if v["weak"]], "leagues": out}


_CACHE = {}


def _load():
    if "s" not in _CACHE:
        try:
            _CACHE["s"] = json.load(open(PATH))
        except (OSError, ValueError):
            _CACHE["s"] = {}
    return _CACHE["s"]


def calibrate(league, p):
    """The engine's win % for a side, corrected by its real track record in this sport. Phased in above a coin flip
    (a 50/50 read isn't moved; a 57%+ read gets the full correction)."""
    b = (_load().get(league) or {}).get("bias") or 0.0
    if not b or p is None or p <= 0.5:
        return p
    return min(0.99, max(0.01, p + b * min(1.0, (p - 0.5) / 0.07)))


def weak(league):
    """A sport proven weak (the engine's picks below the price and losing, old AND new games): no Lock / Dog / leg."""
    return bool((_load().get(league) or {}).get("weak"))
