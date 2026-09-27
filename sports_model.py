"""The sports engine's brain. Retuned every day from real results.

1. Team strength: an Elo rating per team (margin of victory counts; ratings drift back toward
   average over the off-season). K (reaction speed) and home advantage are re-picked daily by the
   lowest log loss on recent games.
2. Our own view: a logistic model on the Elo edge + recent form (last 10 games vs expectation) +
   rest days + back-to-backs + injuries (players Out/Doubtful). Its weights are refit daily.
3. Market blend: the betting market is sharp, so the final probability starts from the market's
   no-vig odds and moves toward our view by a learned "trust", plus a learned weight on line
   movement (the open -> current move is where sharp money shows up in free data):
       logit p = logit(market) + trust * (logit(ours) - logit(market)) + move_w * line_move
   If our view adds nothing, trust falls toward 0 by itself.
4. Spreads (NFL, NBA): expected margin from the same inputs (least squares), blended with the
   market's line the same way; cover chance from a normal curve with the learned spread of results.
Every tune is logged so the dashboard can show what the engine learned and what changed."""
import math
from datetime import datetime, timezone

from zoneinfo import ZoneInfo

import sports_data as sd

PT = ZoneInfo("America/Los_Angeles")

BASE_K = {"nfl": 20, "ncaaf": 25, "nba": 20, "mlb": 4, "nhl": 6}
DEFAULT_HFA = {"nfl": 48, "ncaaf": 60, "nba": 70, "mlb": 24, "nhl": 30}
SPREAD_LEAGUES = ("nfl", "ncaaf", "nba")   # no run lines (MLB) or puck lines (NHL)
K_MULTS = [0.5, 0.75, 1.0, 1.5, 2.0]
HFA_GRID = [0, 20, 40, 60, 80, 100]
MIN_ODDS_GAMES = 80        # below this many games with odds, trust stays cautious
TRUST_CAUTIOUS = 0.15
EVAL_GAMES = 900           # tune on (at most) the most recent this many finished games
REGRESS, BREAK_DAYS = 1 / 3, 75
FORM_N = 10
FEATURES = ["elo", "form", "rest", "b2b", "inj"]          # our own view (besides an intercept)


def _ts(iso):
    try:
        return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0.0


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sigmoid(z):
    return 1 / (1 + math.exp(-max(-30.0, min(30.0, z))))


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def market_p(g, open_line=False):
    h, a = (_int(g.get("ml_home_open")), _int(g.get("ml_away_open"))) if open_line else \
        (_int(g.get("ml_home")), _int(g.get("ml_away")))
    if h is None or a is None:
        return None
    return sd.no_vig(h, a)


def line_move(g):
    now, op = market_p(g), market_p(g, open_line=True)
    return 0.0 if now is None or op is None else logit(now) - logit(op)


def finals(games, league):
    out = [g for g in games.values() if g["league"] == league and g["status"] == "final"
           and g["home_score"] != "" and g["away_score"] != ""]
    out.sort(key=lambda g: (g["start"], g["id"]))
    return out


def p_home(r_home, r_away, hfa, neutral=False):
    return 1 / (1 + 10 ** (-((r_home - r_away) + (0 if neutral else hfa)) / 400))


class Elo:
    """Ratings + everything the features need about each team's recent games."""

    def __init__(self, k, hfa):
        self.k, self.hfa = k, hfa
        self.r, self.last, self.n, self.form = {}, {}, {}, {}

    def rating(self, team, t):
        r = self.r.get(team, 1500.0)
        if team in self.last and t - self.last[team] > BREAK_DAYS * 86400:
            r = 1500 + (r - 1500) * (1 - REGRESS)
            self.r[team] = r
            self.form[team] = []
        return r

    def features(self, g):
        """Pre-game inputs for a game (finished or upcoming), home minus away."""
        t = _ts(g["start"])
        rh, ra = self.rating(g["home"], t), self.rating(g["away"], t)
        neutral = str(g.get("neutral")) == "1"
        pe = p_home(rh, ra, self.hfa, neutral)

        def form(tm):
            f = self.form.get(tm, [])[-FORM_N:]
            return sum(f) / len(f) if f else 0.0

        def rest(tm):
            return min(10.0, (t - self.last[tm]) / 86400) if tm in self.last else 10.0
        rh_d, ra_d = rest(g["home"]), rest(g["away"])
        ih, ia = _int(g.get("inj_home")) or 0, _int(g.get("inj_away")) or 0
        return {
            "p_elo": pe, "elo": logit(pe), "elo_pts": (rh - ra + (0 if neutral else self.hfa)),
            "form": form(g["home"]) - form(g["away"]),
            "rest": (rh_d - ra_d) / 7,
            "b2b": float(ra_d <= 1.2) - float(rh_d <= 1.2),     # + when only the away team is on a back-to-back
            "inj": (ia - ih) / 5,
            "known": min(self.n.get(g["home"], 0), self.n.get(g["away"], 0)),
        }

    def update(self, g):
        f = self.features(g)
        t = _ts(g["start"])
        rh, ra = self.r.get(g["home"], 1500.0), self.r.get(g["away"], 1500.0)
        hs, as_ = int(g["home_score"]), int(g["away_score"])
        res = 1.0 if hs > as_ else 0.0 if hs < as_ else 0.5
        p = f["p_elo"]
        margin = abs(hs - as_)
        diff_w = f["elo_pts"] * (1 if res >= 0.5 else -1)
        mult = math.log(margin + 1) * 2.2 / (diff_w * 0.001 + 2.2) if margin else 1.0
        d = self.k * mult * (res - p)
        self.r[g["home"]], self.r[g["away"]] = rh + d, ra - d
        for tm, s in ((g["home"], res - p), (g["away"], p - res)):
            self.form.setdefault(tm, []).append(s)
            self.form[tm] = self.form[tm][-FORM_N:]
            self.last[tm] = t
            self.n[tm] = self.n.get(tm, 0) + 1
        return f, res, hs - as_


def replay(fin, k, hfa):
    """Run the ratings through finished games in order -> (Elo, [(game, features, result, home margin)])."""
    e = Elo(k, hfa)
    return e, [(g, *e.update(g)) for g in fin]


def logloss(pairs):
    s = 0.0
    for p, y in pairs:
        p = min(max(p, 1e-6), 1 - 1e-6)
        s -= y * math.log(p) + (1 - y) * math.log(1 - p)
    return s / max(1, len(pairs))


# ---------------------------------------------------------------- tiny linear algebra
def _solve(A, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            continue
        M[c], M[piv] = M[piv], M[c]
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c] / M[c][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(n)]


def fit_logistic(X, y, prior, lam=5.0, iters=25):
    """Newton's method for logistic regression, L2-pulled toward `prior` (so thin data changes little)."""
    w = list(prior)
    d = len(w)
    for _ in range(iters):
        g = [lam * (w[j] - prior[j]) for j in range(d)]
        H = [[lam if i == j else 0.0 for j in range(d)] for i in range(d)]
        for x, t in zip(X, y):
            p = sigmoid(sum(a * b for a, b in zip(w, x)))
            r, s = p - t, p * (1 - p)
            for i in range(d):
                g[i] += r * x[i]
                xi = s * x[i]
                for j in range(d):
                    H[i][j] += xi * x[j]
        step = _solve(H, g)
        w = [a - b for a, b in zip(w, step)]
        if max(abs(s) for s in step) < 1e-6:
            break
    return w


def fit_linear(X, y, lam=1.0):
    d = len(X[0])
    A = [[sum(x[i] * x[j] for x in X) + (lam if i == j and i else 0.0) for j in range(d)] for i in range(d)]
    b = [sum(x[i] * t for x, t in zip(X, y)) for i in range(d)]
    return _solve(A, b)


def _own_x(f):
    return [1.0] + [f[k] for k in FEATURES]


def _spread_x(f):
    return [1.0, f["elo_pts"] / 25, f["form"], f["rest"], f["b2b"], f["inj"]]


def own_p(params, f):
    return sigmoid(sum(a * b for a, b in zip(params["w"], _own_x(f))))


def final_p(params, f, g):
    """Home win probability: market, moved toward our own view by the learned trust."""
    ours = own_p(params, f)
    m = market_p(g)
    if m is None:
        return ours
    return sigmoid(logit(m) + params["trust"] * (logit(ours) - logit(m)) + params["move_w"] * line_move(g))


def margin_mu(params, f, g):
    """Expected home margin: the market's line moved toward ours by the learned spread trust."""
    ours = sum(a * b for a, b in zip(params["sw"], _spread_x(f)))
    line = _num(g.get("spread_home"))
    return ours if line is None else -line + params["strust"] * (ours - (-line))


def cover_p(params, f, g, side):
    """Chance the side covers its spread (pushes count as half)."""
    line = _num(g.get("spread_home"))
    if line is None:
        return None
    mu, sd_ = margin_mu(params, f, g), params["sigma"]
    z = (mu + line) / sd_                               # home covers when margin + line > 0
    p = phi(z)
    return p if side == "home" else 1 - p


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- daily tune
def tune(games, league, prev=None):
    """Re-pick every setting for one league from its finished games. Returns a params dict."""
    fin = finals(games, league)
    if len(fin) < 60:
        return prev
    warm = max(30, len(fin) // 4)
    ev_from = max(warm, len(fin) - EVAL_GAMES)
    best = None
    for km in K_MULTS:
        k = BASE_K[league] * km
        for hfa in HFA_GRID:
            _, rows = replay(fin, k, hfa)
            ll = logloss([(f["p_elo"], y) for _, f, y, _ in rows[ev_from:] if y != 0.5])
            if best is None or ll < best[0]:
                best = (ll, k, hfa, rows)
    ll_elo, k, hfa, rows = best
    train = [(g, f, y, m) for g, f, y, m in rows[warm:] if y != 0.5]
    ev = [r for r in rows[ev_from:] if r[2] != 0.5]
    # 2. our own view
    w = fit_logistic([_own_x(f) for _, f, _, _ in train], [y for _, _, y, _ in train],
                     prior=[0.0, 1.0] + [0.0] * (len(FEATURES) - 1))
    params = {"w": w, "trust": TRUST_CAUTIOUS, "move_w": 0.0}
    ll_own = logloss([(own_p(params, f), y) for _, f, y, _ in ev])
    # 3. market blend (trust + line movement), fit on recent games that had odds
    odds = [(g, f, y) for g, f, y, _ in ev if market_p(g) is not None]
    ll_mkt = logloss([(market_p(g), y) for g, _, y in odds]) if odds else None
    ll_final = None
    if len(odds) >= MIN_ODDS_GAMES:
        X = [[logit(own_p(params, f)) - logit(market_p(g)), line_move(g)] for g, f, _ in odds]
        off = [logit(market_p(g)) for g, _, _ in odds]
        # logistic with a fixed offset (the market): fit on x with offset folded in via a grid on trust
        best_t = None
        for t in [i / 20 for i in range(21)]:
            for mw in [-0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]:
                ll = logloss([(sigmoid(o + t * x[0] + mw * x[1]), y) for o, x, (_, _, y) in zip(off, X, odds)])
                if best_t is None or ll < best_t[0]:
                    best_t = (ll, t, mw)
        ll_final, params["trust"], params["move_w"] = best_t
    # 4. spreads: expected margin
    sp = {}
    if league in SPREAD_LEAGUES:
        sw = fit_linear([_spread_x(f) for _, f, _, _ in train], [m for _, _, _, m in train])
        res = [m - sum(a * b for a, b in zip(sw, _spread_x(f))) for _, f, _, m in train]
        sigma = max(6.0, math.sqrt(sum(r * r for r in res) / max(1, len(res))))
        lined = [(g, f, m) for g, f, _, m in rows[ev_from:] if _num(g.get("spread_home")) is not None]
        strust = 0.2
        if len(lined) >= MIN_ODDS_GAMES:
            def err(t):
                return sum((m - (-_num(g["spread_home"]) + t * (sum(a * b for a, b in zip(sw, _spread_x(f)))
                                                                 + _num(g["spread_home"])))) ** 2 for g, f, m in lined)
            strust = min([i / 20 for i in range(21)], key=err)
        sp = {"sw": sw, "sigma": sigma, "strust": strust, "spread_games": len(lined)}
    acc = sum((own_p(params, f) > 0.5) == (y == 1.0) for _, f, y, _ in ev) / max(1, len(ev))
    mkt_acc = sum((market_p(g) > 0.5) == (y == 1.0) for g, _, y in odds) / len(odds) if odds else None
    return {
        "k": k, "hfa": hfa, **params, **sp,
        "weights": {name: round(v, 3) for name, v in zip(FEATURES, w[1:])},
        "games": len(fin), "eval_games": len(ev), "odds_games": len(odds),
        "logloss_elo": round(ll_elo, 4), "logloss_own": round(ll_own, 4),
        "logloss_market": round(ll_mkt, 4) if ll_mkt is not None else None,
        "logloss_final": round(ll_final, 4) if ll_final is not None else None,
        "accuracy": round(acc, 4), "market_accuracy": round(mkt_acc, 4) if mkt_acc is not None else None,
        "tuned": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    }


def tune_all(games, model):
    """Self-tune: refresh every league's params and append what changed to the learning log."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for lg in sd.LEAGUES:
        prev = model["params"].get(lg)
        new = tune(games, lg, prev)
        if not new or new is prev:
            continue
        change = []
        if prev:
            if new["k"] != prev["k"]:
                change.append(f"reaction speed {prev['k']:g} → {new['k']:g}")
            if new["hfa"] != prev["hfa"]:
                change.append(f"home edge {prev['hfa']} → {new['hfa']}")
            if abs(new["trust"] - prev["trust"]) > 1e-9:
                change.append(f"trust {prev['trust']:.0%} → {new['trust']:.0%}")
            for name in FEATURES[1:]:
                a, b = prev.get("weights", {}).get(name, 0), new["weights"][name]
                if abs(b - a) >= 0.05:
                    change.append(f"{name} weight {a:+.2f} → {b:+.2f}")
        model["params"][lg] = new
        if not change and prev and any(e["date"] == today and e["league"] == lg for e in model["log"][-50:]):
            continue                                   # retrained, nothing moved: one log line per day is enough
        model["log"].append({"date": today, "league": lg, **{k: new[k] for k in (
            "k", "hfa", "trust", "move_w", "games", "odds_games", "logloss_own", "logloss_market",
            "logloss_final", "accuracy", "market_accuracy")},
            "change": "; ".join(change) or ("first tune" if not prev else "no change")})
    model["log"] = model["log"][-3000:]
    model["tuned_on"] = datetime.now(timezone.utc).astimezone(PT).strftime("%b %-d, %-I:%M %p PT")
    return model


def default_params(league):
    return {"k": BASE_K[league], "hfa": DEFAULT_HFA[league], "w": [0.0, 1.0] + [0.0] * (len(FEATURES) - 1),
            "trust": TRUST_CAUTIOUS, "move_w": 0.0, "sw": [0.0, 1.0, 0, 0, 0, 0], "sigma": 13.0, "strust": 0.2}


def ratings(games, model):
    """Current ratings per league with today's params -> {league: Elo}."""
    out = {}
    for lg in sd.LEAGUES:
        p = model["params"].get(lg) or default_params(lg)
        out[lg], _ = replay(finals(games, lg), p["k"], p["hfa"])
    return out
