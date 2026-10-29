"""🏀 THE NBA OPENING-LINE READ (the owner OK'd it 10/23): the engine's whole-model read of every NBA side, scored at the
FIRST price the books show - the open hasn't priced the recent form and the records yet, the close has.

The 10/23 study (scratchpad nba1023, SPORTS_FINDINGS 10/23): a ridge logistic model on every side of every regular-season
game - the price, home / dog, the stage of the season, rest, back-to-backs, 3-in-4 / 4-in-6, road trips, time zones,
altitude, the last game's margin, 5- and 10-game form, this season's and last season's records, the Elo gap - fit on the
seasons BEFORE the one it's graded on (never a look-ahead) at the CLOSE, then scored at the OPEN. The best side a night
with an open score of 4+ points, opening -150..+300: 334 bets 170-164, +13.4%, +44.7u, up all three seasons it never
saw (2023 +9%, 2024 +19%, 2025 +13%), worst stretch -12.7u. The SAME picks at the close: +5%. The #2 side a night loses.
Form / records carry it (the market-only model loses -15%); it's a whole read of 37 factors, never one (the owner's
rule). The 11-game gate came off 10/29 (MIN_TEAM_GAMES - the replay of this module found no early-season hole), and the
board's NBA dog weights (the 12+ game slate, the favorite's soft next game, a cold dog) ride on the read through
best_tonight(weigh=...) - the same read the board uses on an NBA dog, never a trigger.

Pure Python (the Actions runner installs nothing): fit() is a column-wise Newton ridge fit, run once a season and
cached in data/sports/nba_open_model.json; score() is a dot product."""
import json
import math
import os
from datetime import datetime, timedelta, timezone
from operator import mul

import sports_data as sd
import sports_model as sm

MODEL_PATH = os.path.join(sd.DATA, "nba_open_model.json")
LAM = 300.0                 # the ridge on the standardized weights (chosen on the 2020-22 walk-forward log loss)
SCORE_MIN = 0.04            # the model's win chance over the open's no-vig number, in win-% points (the study's cut)
PRICE_BAND = (-150, 300)    # the side's opening price (the -150 rule; "never no damn +400")
MIN_TEAM_GAMES = 1          # both teams have PLAYED this season (a record and a last game to stand on). Was 11 (the
#                             10/23 study's "games 1-10: -3.4% on 43" - a cut that used the own-read gap input the built
#                             module doesn't have). 10/29 (the owner: "we need to jump on these NBA dogs as soon as the
#                             line opens"): THIS module replayed blind at the open 2023-25 with no games gate - teams
#                             1-5 games in 15-15 +1.6u (+5.3%), 6-10 games in 8-9 +2.5u (+14.5%), 11+ 143-139 +38.6u
#                             (+13.7%); all 166-163 +42.6u +13.0%, up all 3 seasons. The stage inputs (g1_5 / g6_10)
#                             already weigh the early weeks. 47 early bets is noise either way - no reason to sit out
#                             three weeks of the season; the spot's own record judges it (40 plays, under -5% = off).
MIN_TRAIN_SEASONS = 2       # a fit needs two full prior seasons with prices, or there's no model
MIN_SEASON_ROWS = 800       # ...a "full" season = 800+ priced regular-season sides
ELO_K, ELO_HFA = 20, 70     # the NBA Elo the study used (sports_model's defaults for the NBA)
FEATURES = ["logit_mp", "is_home", "is_dog", "home_dog", "g1_5", "g6_10", "g11_20", "g31_60", "g61", "home_dog_g6_20",
            "home_dog_g31_60", "rest_diff", "t_b2b", "o_b2b", "t_3in4", "o_3in4", "t_4in6", "o_4in6", "t_trip4", "o_trip4",
            "t_home_after4", "o_home_after4", "t_tz", "o_tz", "t_alt", "o_alt", "t_last", "o_last", "t_won20", "o_won20",
            "t_lost15", "o_lost15", "form5", "form10", "wp_diff", "wp_last_diff", "elo_gap"]


def season_of(start):
    """The NBA season a start time belongs to, by the year it began (the 2019-20 bubble ran into October 2020)."""
    y, m = int(str(start)[:4]), int(str(start)[5:7])
    if y == 2020 and m <= 10:
        return 2019
    return y if m >= 9 else y - 1


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def _t(s):
    return datetime.strptime(str(s)[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def _us_date(start):
    """The game's US date (UTC - 5h splits the nights right)."""
    return (_t(start) - timedelta(hours=5)).date()


def _dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def _mp(ml_a, ml_b):
    """Side A's no-vig win chance from the two prices, or None."""
    a, b = _int(ml_a), _int(ml_b)
    if a is None or b is None or a == 0 or b == 0:
        return None
    pa, pb = 1 / _dec(a), 1 / _dec(b)
    return pa / (pa + pb)


def table(games):
    """Every real NBA game (finals and upcoming, in order) -> {gid: row}: season, prices, the result, the Elo read and
    each team's pre-game schedule facts (h / a) - from the games BEFORE it only. An upcoming game reads the state after
    every final before it (a team's game tonight isn't in tomorrow's row until it's final)."""
    rows = []
    for g in games.values():
        if g.get("league") != "nba" or not g.get("start") or (g.get("stype") or "?") not in sd.REAL or sd.exhibition(g):
            continue
        if g.get("status") == "final" and (str(g.get("home_score", "")) == "" or str(g.get("away_score", "")) == ""):
            continue
        rows.append(g)
    rows.sort(key=lambda g: (g["start"], g["id"]))
    elo = sm.Elo(ELO_K, ELO_HFA, "nba")
    home_tz, home_elev = {}, {}
    for g in rows:                                           # each team's home time zone / altitude (its home games)
        if str(g.get("neutral")) == "1":
            continue
        tz, el = _num(g.get("tzo")), _num(g.get("elev"))
        if tz is not None:
            home_tz.setdefault(g["home"], {}).setdefault(tz, 0)
            home_tz[g["home"]][tz] += 1
        if el is not None:
            home_elev.setdefault(g["home"], {}).setdefault(el, 0)
            home_elev[g["home"]][el] += 1
    home_tz = {k: max(v, key=v.get) for k, v in home_tz.items()}
    home_elev = {k: max(v, key=v.get) for k, v in home_elev.items()}
    hist = {}        # team -> [(date, side, margin, season, regular)]
    trip = {}        # team -> consecutive away games so far
    wins = {}        # (team, season) -> [wins, games] (regular season)
    out = {}
    for g in rows:
        s = season_of(g["start"])
        d = _us_date(g["start"])
        reg = str(g.get("stype")) == "2"
        neutral = str(g.get("neutral")) == "1"
        t = sm._ts(g["start"])
        p_elo = sm.p_home(elo.rating(g["home"], t), elo.rating(g["away"], t), ELO_HFA, neutral)
        side_facts = {}
        for side in ("home", "away"):
            tm = g[side]
            prev = hist.get(tm, [])
            if prev and prev[-1][3] != s:
                trip[tm] = 0                                 # a new season: no trip carried over
            same = [h for h in prev if h[3] == s and h[4]]
            rest = (d - prev[-1][0]).days if prev else 10
            n4 = sum(1 for h in prev if (d - h[0]).days <= 3) + 1
            n6 = sum(1 for h in prev if (d - h[0]).days <= 5) + 1
            tr = trip.get(tm, 0)
            trip_game = tr + 1 if side == "away" else 0
            home_after = tr if side == "home" and prev and prev[-1][1] == "away" and prev[-1][3] == s else 0
            tzo = _num(g.get("tzo"))
            tz_cross = abs(tzo - home_tz[tm]) if side == "away" and tzo is not None and tm in home_tz else 0.0
            elev = _num(g.get("elev")) or 0.0
            alt = 1.0 if side == "away" and elev >= 1000 and (home_elev.get(tm) or 0) < 1000 else 0.0
            l5 = [h[2] for h in same[-5:]]
            l10 = [h[2] for h in same[-10:]]
            w, n = wins.get((tm, s), (0, 0))
            wl, nl = wins.get((tm, s - 1), (0, 0))
            side_facts[side] = dict(n_season=len(same), rest=rest, b2b=1.0 if rest <= 1 else 0.0, n4=n4, n6=n6,
                                    trip_game=trip_game, home_after=home_after, tz_cross=tz_cross, alt=alt,
                                    last_margin=same[-1][2] if same else None,
                                    m5=sum(l5) / len(l5) if l5 else None, m10=sum(l10) / len(l10) if l10 else None,
                                    wp_season=w / n if n else None, wp_last=wl / nl if nl else None,
                                    streak_w=w, streak_n=n)
        row = dict(gid=g["id"], season=s, start=g["start"], date=str(d), reg=reg, status=g.get("status"),
                   home=g["home"], away=g["away"], home_name=g.get("home_name"), away_name=g.get("away_name"),
                   ml_home=_int(g.get("ml_home")), ml_away=_int(g.get("ml_away")),
                   ml_home_open=_int(g.get("ml_home_open")), ml_away_open=_int(g.get("ml_away_open")),
                   p_elo=p_elo, h=side_facts["home"], a=side_facts["away"], home_win=None)
        if g.get("status") == "final":
            hs, as_ = _num(g.get("home_score")), _num(g.get("away_score"))
            if hs is not None and as_ is not None:
                row["home_win"] = 1.0 if hs > as_ else 0.0
                elo.update(g)
                for side, m in (("home", hs - as_), ("away", as_ - hs)):
                    tm = g[side]
                    hist.setdefault(tm, []).append((d, side, m, s, reg))
                    trip[tm] = trip.get(tm, 0) + 1 if side == "away" else 0
                    if reg:
                        w, n = wins.get((tm, s), (0, 0))
                        wins[(tm, s)] = (w + (1 if m > 0 else 0), n + 1)
        out[g["id"]] = row
    return out


def _f0(x):
    return float(x) if x is not None else 0.0


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def features(row, side, mp):
    """The side's 37 inputs at a price `mp` (its no-vig win chance): what's known before the game, nothing from the box."""
    t, o = (row["h"], row["a"]) if side == "home" else (row["a"], row["h"])
    is_home = 1.0 if side == "home" else 0.0
    is_dog = 1.0 if mp < 0.5 else 0.0
    g = t["n_season"] + 1
    p_elo = row["p_elo"] if side == "home" else 1 - row["p_elo"]
    f = {
        "logit_mp": sm.logit(mp), "is_home": is_home, "is_dog": is_dog, "home_dog": is_home * is_dog,
        "g1_5": 1.0 if g <= 5 else 0.0, "g6_10": 1.0 if 6 <= g <= 10 else 0.0, "g11_20": 1.0 if 11 <= g <= 20 else 0.0,
        "g31_60": 1.0 if 31 <= g <= 60 else 0.0, "g61": 1.0 if g >= 61 else 0.0,
        "home_dog_g6_20": is_home * is_dog * (1.0 if 6 <= g <= 20 else 0.0),
        "home_dog_g31_60": is_home * is_dog * (1.0 if 31 <= g <= 60 else 0.0),
        "rest_diff": _clip(_clip(_f0(t["rest"]), 0, 6) - _clip(_f0(o["rest"]), 0, 6), -3, 3),
        "t_b2b": t["b2b"], "o_b2b": o["b2b"],
        "t_3in4": 1.0 if t["n4"] >= 3 else 0.0, "o_3in4": 1.0 if o["n4"] >= 3 else 0.0,
        "t_4in6": 1.0 if t["n6"] >= 4 else 0.0, "o_4in6": 1.0 if o["n6"] >= 4 else 0.0,
        "t_trip4": 1.0 if t["trip_game"] >= 4 else 0.0, "o_trip4": 1.0 if o["trip_game"] >= 4 else 0.0,
        "t_home_after4": 1.0 if t["home_after"] >= 4 else 0.0, "o_home_after4": 1.0 if o["home_after"] >= 4 else 0.0,
        "t_tz": t["tz_cross"], "o_tz": o["tz_cross"], "t_alt": t["alt"], "o_alt": o["alt"],
        "t_last": _clip(_f0(t["last_margin"]), -30, 30) / 10, "o_last": _clip(_f0(o["last_margin"]), -30, 30) / 10,
        "t_won20": 1.0 if (t["last_margin"] or 0) >= 20 else 0.0, "o_won20": 1.0 if (o["last_margin"] or 0) >= 20 else 0.0,
        "t_lost15": 1.0 if (t["last_margin"] or 0) <= -15 else 0.0, "o_lost15": 1.0 if (o["last_margin"] or 0) <= -15 else 0.0,
        "form5": _clip(_f0(t["m5"]) - _f0(o["m5"]), -25, 25) / 10, "form10": _clip(_f0(t["m10"]) - _f0(o["m10"]), -20, 20) / 10,
        "wp_diff": _f0(t["wp_season"]) - _f0(o["wp_season"]), "wp_last_diff": _f0(t["wp_last"]) - _f0(o["wp_last"]),
        "elo_gap": sm.logit(p_elo) - sm.logit(mp),
    }
    return [f[k] for k in FEATURES]


def _fit_ridge(X, y, lam, iters=15):
    """Newton's method, L2 on every weight but the intercept - column-wise sums (C speed) so 25,000 rows x 38 fit in
    seconds without numpy. X: standardized rows (no intercept)."""
    n, k = len(X), len(X[0])
    cols = [[1.0] * n] + [list(c) for c in zip(*X)]
    d = k + 1
    w = [0.0] * d
    for _ in range(iters):
        z = [sum(map(mul, w, [1.0] + x)) for x in X]
        p = [1 / (1 + math.exp(-max(-30.0, min(30.0, v)))) for v in z]
        r = [pi - yi for pi, yi in zip(p, y)]
        s = [pi * (1 - pi) for pi in p]
        grad = [sum(map(mul, r, cols[j])) + (lam * w[j] if j else 0.0) for j in range(d)]
        H = [[0.0] * d for _ in range(d)]
        for j in range(d):
            sx = list(map(mul, s, cols[j]))
            for m in range(j, d):
                v = sum(map(mul, sx, cols[m]))
                H[j][m] = H[m][j] = v
            if j:
                H[j][j] += lam
        step = sm._solve(H, grad)
        w = [a - b for a, b in zip(w, step)]
        if max(abs(v) for v in step) < 1e-7:
            break
    return w


def train_rows(tab, before_season):
    """(features at the CLOSE, won) for every side of every priced regular-season final in the seasons before
    `before_season` - and never one from it or after it (no look-ahead)."""
    X, y, seasons = [], [], {}
    for row in tab.values():
        if row["season"] >= before_season or not row["reg"] or row["home_win"] is None:
            continue
        mp = _mp(row["ml_home"], row["ml_away"])
        if mp is None:
            continue
        for side, m, won in (("home", mp, row["home_win"]), ("away", 1 - mp, 1 - row["home_win"])):
            X.append(features(row, side, m))
            y.append(float(won))
            seasons[row["season"]] = seasons.get(row["season"], 0) + 1
    return X, y, seasons


def fit(games, season, path=None, tab=None):
    """Fit the model for `season` on the seasons BEFORE it only (at their closing prices), save it, return it - or None
    when fewer than MIN_TRAIN_SEASONS full priced seasons came before (then there's no model and no play)."""
    tab = tab if tab is not None else table(games)
    X, y, seasons = train_rows(tab, season)
    full = [s for s, n in seasons.items() if n >= MIN_SEASON_ROWS]
    if len(full) < MIN_TRAIN_SEASONS:
        return None
    k = len(FEATURES)
    mu = [sum(x[j] for x in X) / len(X) for j in range(k)]
    sdv = [math.sqrt(sum((x[j] - mu[j]) ** 2 for x in X) / len(X)) or 1.0 for j in range(k)]
    Xs = [[(x[j] - mu[j]) / sdv[j] for j in range(k)] for x in X]
    w = _fit_ridge(Xs, y, LAM)
    model = {"season": season, "features": FEATURES, "mu": mu, "sd": sdv, "w": w, "lam": LAM, "rows": len(X),
             "train_seasons": sorted(seasons), "fitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    if path is not False:
        save(model, path)
    return model


def save(model, path=None):
    path = path or MODEL_PATH
    with open(path + ".tmp", "w") as f:
        json.dump(model, f)
    os.replace(path + ".tmp", path)


def load(path=None):
    try:
        with open(path or MODEL_PATH) as f:
            m = json.load(f)
        return m if m.get("features") == FEATURES and len(m.get("w") or []) == len(FEATURES) + 1 else None
    except (OSError, ValueError):
        return None


def current(games, now=None, path=None, tab=None):
    """This season's model: the saved one when it was fit for this season, else a fresh fit (saved). None = no model."""
    now = now or datetime.now(timezone.utc)
    season = season_of(now.strftime("%Y-%m-%dT%H:%MZ"))
    m = load(path)
    if m and m.get("season") == season:
        return m
    return fit(games, season, path, tab)


def predict(model, x):
    z = model["w"][0] + sum(wj * (xj - mj) / sj for wj, xj, mj, sj in zip(model["w"][1:], x, model["mu"], model["sd"]))
    return 1 / (1 + math.exp(-max(-30.0, min(30.0, z))))


def score(model, row, side, mp):
    """The model's win chance for the side at the price `mp` minus that price's no-vig number (win-% points)."""
    return predict(model, features(row, side, mp)) - mp


def best_tonight(games, date, model, tab=None, min_team_games=None, score_min=SCORE_MIN, band=PRICE_BAND,
                 prices=None, weigh=None):
    """The ONE side the model likes best on a slate date (a PT / US date string 'YYYY-MM-DD'): upcoming regular-season
    games with a price, each side at its price now (`prices`: {gid: (ml_home, ml_away)} overrides - the open, in a
    replay), score >= score_min, the side's price in the band, both teams min_team_games+ games in (MIN_TEAM_GAMES).
    `weigh(gid, side, ml)` -> win-% points (as a fraction, +0.02 = 2 points) the board's NBA dog studies add to a side
    (sports_early.nba_open_weigh - the 12+ game slate, the favorite's soft next game, a cold dog; 10/29: the same read
    the board uses, never a trigger) - the score that ranks and clears the bar is the model's read PLUS those weights
    (c["model_score"] / c["weights"] keep the two apart). The #2 side a night loses, so only #1 ever comes back - None
    when nothing clears."""
    if model is None:
        return None
    if min_team_games is None:
        min_team_games = MIN_TEAM_GAMES
    tab = tab if tab is not None else table(games)
    best = None
    for gid, row in tab.items():
        if row["date"] != str(date) or not row["reg"] or (row["status"] not in (None, "pre") and prices is None):
            continue
        mh, ma = (prices or {}).get(gid) or (row["ml_home"], row["ml_away"])
        mp_h = _mp(mh, ma)
        if mp_h is None or row["h"]["n_season"] < min_team_games or row["a"]["n_season"] < min_team_games:
            continue
        for side, ml, mp in (("home", mh, mp_h), ("away", ma, 1 - mp_h)):
            if not band[0] <= ml <= band[1]:
                continue
            ms = score(model, row, side, mp)
            wt = float(weigh(gid, side, ml) or 0.0) if weigh else 0.0
            sc = ms + wt
            if sc < score_min:
                continue
            c = {"game_id": gid, "side": side, "odds": ml, "opp_odds": ma if side == "home" else mh, "mkt": round(mp, 4),
                 "own": round(mp + ms, 4), "score": round(sc, 4), "model_score": round(ms, 4), "weights": round(wt, 4),
                 "start": row["start"], "date": row["date"],
                 "team": row[f"{side}_name"], "opp": row["away_name" if side == "home" else "home_name"]}
            if best is None or sc > best["score"]:
                best = c
    return best


def facts(row, side):
    """The specific facts behind a pick, for its card (the owner: never vague - a record, a score, a number): this
    season's records, the last game's margin, the rest. -> {rec, opp_rec, last, rest}"""
    t, o = (row["h"], row["a"]) if side == "home" else (row["a"], row["h"])

    def rec(x):
        return f"{x['streak_w']}-{x['streak_n'] - x['streak_w']}" if x.get("streak_n") else None
    lm = t["last_margin"]
    return {"rec": rec(t), "opp_rec": rec(o),
            "last": (f"won their last by {int(lm)}" if lm and lm > 0 else f"lost their last by {int(-lm)}" if lm else None),
            "rest": int(t["rest"]) if t.get("rest") is not None else None, "opp_rest": int(o["rest"]) if o.get("rest") is not None else None}
