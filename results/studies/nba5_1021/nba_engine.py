"""The engine's NBA own read, replayed honestly: for each season S the own-view weights are fit (sports_model
fit_logistic on the engine's FEATURES) on every finished game BEFORE season S, the market blend (trust / cal / hdog,
move_w = 0) likewise on the prior seasons that had odds. Ratings as of game time (Elo replayed in order)."""
import os
import pickle
import sys
from common import load, OUT, WT, season_of
sys.path.insert(0, WT)
import sports_model as sm   # noqa: E402
import sports_data as sd    # noqa: E402


def build():
    games = sd.load_games("nba")
    fin = sm.finals(games, "nba")
    elo = sm.Elo(20, 70, "nba")
    allrows = []            # (season, g, f, y) for every final incl. playoffs - what the weights are fit on
    for g in fin:
        f = elo.features(g)
        hs, as_ = int(g["home_score"]), int(g["away_score"])
        y = 1.0 if hs > as_ else 0.0
        allrows.append((season_of(g["start"]), g, f, y))
        elo.update(g)
    out = {}
    seasons = sorted({s for s, *_ in allrows})
    for S in seasons:
        if S < 2018:
            continue
        prior = [(g, f, y) for s, g, f, y in allrows if s < S]
        train = prior[-sm.TRAIN_GAMES:]
        w = sm.fit_logistic([sm._own_x(f) for _, f, _ in train], [y for _, _, y in train],
                            prior=[0.0, 1.0] + [0.0] * (len(sm.FEATURES) - 1))
        params = {"w": w, "trust": sm.TRUST_CAUTIOUS, "move_w": 0.0, "cal": 0.0, "hdog": 0.0}
        odds = [(g, f, y) for g, f, y in prior[-sm.EVAL_GAMES * 3:] if sm.market_p(g) is not None]
        if len(odds) >= sm.MIN_ODDS_GAMES:
            X = [[sm.logit(sm.own_p(params, f)) - sm.logit(sm.market_p(g)), sm.logit(sm.market_p(g)),
                  sm.home_dog(sm.market_p(g), g)] for g, f, _ in odds]
            off = [sm.logit(sm.market_p(g)) for g, _, _ in odds]
            w3 = sm.fit_logistic_offset(X, [y for _, _, y in odds], off, prior=[sm.TRUST_CAUTIOUS, 0.0, 0.0], lam=8.0)
            w3[0] = min(1.0, max(0.0, w3[0]))
            params["trust"], params["cal"], params["hdog"] = w3
        print(S, "fit on", len(train), "odds", len(odds), "trust %.3f cal %.3f hdog %.3f" % (params["trust"], params["cal"], params["hdog"]),
              {k: round(v, 2) for k, v in zip(sm.FEATURES, w[1:])})
        for s, g, f, y in allrows:
            if s != S:
                continue
            m = sm.market_p(g)
            own = sm.own_p(params, f)
            fin_p = None
            if m is not None:
                fin_p = sm.sigmoid(sm.logit(m) + params["trust"] * (sm.logit(own) - sm.logit(m))
                                   + params["cal"] * sm.logit(m) + params["hdog"] * sm.home_dog(m, g))
            out[g["id"]] = dict(own=own, final=fin_p, trust=params["trust"])
    return out


def load_engine(force=False):
    p = os.path.join(OUT, "engine.pkl")
    if not force and os.path.exists(p):
        with open(p, "rb") as fh:
            return pickle.load(fh)
    e = build()
    with open(p, "wb") as fh:
        pickle.dump(e, fh)
    return e


if __name__ == "__main__":
    e = load_engine(force=True)
    print(len(e))
