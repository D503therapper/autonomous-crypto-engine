"""STUDY 3 - THE DOG MODEL (the owner, 9/30: "show the engine everything it considers, let it pick, grade it on
thousands of games").

For every past underdog (+100 .. +280) the engine sees what it knew BEFORE the game: the book's price, its own rating
gap vs the book, rest, back-to-backs, form, travel, revenge, cold / altitude / weather, and which way the line moved.
It LEARNS (a small logistic model on top of the book's price) on the older seasons only, then PICKS dogs on the newest
seasons it never saw: a dog goes up only when the learned chance beats the price by EDGE+. Every pick is graded.
Run: python tools/dog_model.py
"""
import json
import math
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports_data as sd      # noqa: E402
import sports_model as sm     # noqa: E402

LEAGUES = ("mlb", "nfl", "ncaaf", "nba", "ncaab", "nhl")
SPLIT = "2025-07-01"
DOG_MIN, DOG_MAX = 100, 280
EDGES = (0.02, 0.04, 0.06)
FEATS = ("gap", "rest", "b2b", "form", "revenge", "travel", "cold", "alt", "weather", "move", "home")


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sig(x):
    return 1 / (1 + math.exp(-x))


def rows_for(games, model, lg):
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
        mk = sm.market_p(g)
        if mk is None:
            continue
        own = sm.own_p(p, f) if "w" in p else sm.final_p(p, f, g)
        for side, o, won, m, ow, s in (("home", oh, hs > as_, mk, own, 1), ("away", oa, as_ > hs, 1 - mk, 1 - own, -1)):
            if not DOG_MIN <= o <= DOG_MAX:
                continue
            op, cl = _int(g.get(f"ml_{side}_open")), _int(g.get(f"ml_{side}"))
            move = 0.0 if op is None or cl is None or op == cl else (1.0 if cl < op else -1.0)
            x = {"gap": logit(ow) - logit(m), "rest": s * (f.get("rest") or 0), "b2b": s * (f.get("b2b") or 0),
                 "form": s * (f.get("form") or 0), "revenge": s * (f.get("revenge") or 0),
                 "travel": s * (f.get("travel") or 0), "cold": s * (f.get("cold") or 0), "alt": s * (f.get("alt") or 0),
                 "weather": s * (f.get("weather") or 0), "move": move, "home": 1.0 if side == "home" else 0.0}
            out.append((g["start"][:10], m, x, won, dec(o)))
    out.sort(key=lambda r: r[0])
    return out


def fit(rows, l2=2.0, iters=300, lr=0.05):
    """logit P(win) = logit(book) + b + sum w_k x_k - learned on `rows` (gradient descent, L2-shrunk)."""
    w = {k: 0.0 for k in FEATS}
    b = 0.0
    n = len(rows)
    sc = {k: (sum(abs(r[2][k]) for r in rows) / n) or 1.0 for k in FEATS}   # (features on one scale)
    for _ in range(iters):
        gw = {k: 0.0 for k in FEATS}
        gb = 0.0
        for _, m, x, won, _ in rows:
            p = sig(logit(m) + b + sum(w[k] * x[k] / sc[k] for k in FEATS))
            e = p - (1.0 if won else 0.0)
            gb += e
            for k in FEATS:
                gw[k] += e * x[k] / sc[k]
        b -= lr * gb / n
        for k in FEATS:
            w[k] -= lr * (gw[k] / n + l2 * w[k] / n)
    return w, b, sc


def predict(w, b, sc, m, x):
    return sig(logit(m) + b + sum(w[k] * x[k] / sc[k] for k in FEATS))


def run(games, model):
    res = {}
    for lg in LEAGUES:
        rs = rows_for(games, model, lg)
        learn = [r for r in rs if r[0] < SPLIT]
        exam = [r for r in rs if r[0] >= SPLIT]
        if len(learn) < 500 or len(exam) < 100:
            continue
        w, b, sc = fit(learn)
        out = {"learn": len(learn), "exam": len(exam), "weights": {k: round(v, 3) for k, v in w.items()}, "bias": round(b, 3)}
        base = sum((r[4] - 1) if r[3] else -1 for r in exam) / len(exam)
        out["every_dog_exam_roi"] = round(base, 4)
        for e in EDGES:
            picks = [r for r in exam if predict(w, b, sc, r[1], r[2]) * r[4] - 1 >= e]
            lp = [r for r in learn if predict(w, b, sc, r[1], r[2]) * r[4] - 1 >= e]
            out[f"edge{int(e * 100)}"] = {
                "learn_n": len(lp), "learn_roi": round(sum((r[4] - 1) if r[3] else -1 for r in lp) / len(lp), 4) if lp else None,
                "exam_n": len(picks), "exam_hit": round(sum(r[3] for r in picks) / len(picks), 4) if picks else None,
                "exam_roi": round(sum((r[4] - 1) if r[3] else -1 for r in picks) / len(picks), 4) if picks else None,
                "exam_avg_price": round(sum(r[4] for r in picks) / len(picks), 3) if picks else None}
        res[lg] = out
    return res


if __name__ == "__main__":
    games = sd.load_games()
    model = json.load(open(os.path.join(sd.DATA, "model.json")))
    res = run(games, model)
    for lg, v in res.items():
        print(f"{lg.upper():6} learned on {v['learn']} dogs, exam {v['exam']} dogs (backing EVERY exam dog: {v['every_dog_exam_roi']:+.1%})")
        for e in EDGES:
            x = v[f"edge{int(e * 100)}"]
            if x["exam_n"]:
                print(f"   picks where it sees {int(e * 100)}%+ value: learn {x['learn_n']} ({x['learn_roi']:+.1%}) | "
                      f"EXAM {x['exam_n']} dogs, won {x['exam_hit']:.0%} at +{round((x['exam_avg_price'] - 1) * 100)} avg, money {x['exam_roi']:+.1%}")
        print("   what it leans on:", {k: w for k, w in v["weights"].items() if abs(w) >= 0.03})
    with open(os.path.join(sd.DATA, "dog_model.json"), "w") as f:
        json.dump({"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "leagues": res}, f, indent=1)
