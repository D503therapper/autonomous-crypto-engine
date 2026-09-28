"""THE OVER/UNDER STUDY 2.0: can the engine beat the closing total - and with what?

For every real final with a closing total (the book's over/under), in time order, per sport, the engine writes down
what it knew BEFORE the game (only games before this one - no peeking):
  form         - our scoring read: each team's recent scoring/allowing vs the league -> our total minus the line
  ou_home      - the home team's recent over/under record at home (actual total minus the line, recent games count more)
  ou_away      - the same for the road team on the road
  park         - the building: the home team's long-run home residual, pulled toward 0 until it has plenty of games
  lg_trend     - the whole league's recent residual (the books are slow after rule changes, juiced balls, ...)
  wind / cold / rain - weather at outdoor football and baseball games (0 indoors)
  thin_air     - elevation above 1000 m (Denver, Salt Lake City, Mexico City)
  b2b / rest   - teams on a back-to-back, and the average days of rest
  travel       - time zones the road team is from home (body clock)
  starter      - MLB starting pitchers / NHL goalies: runs (goals) their team allowed in their last 5 starts vs half
                 those games' lines, pulled toward 0 (a new or unknown starter = 0)
  public       - the big bettors on the total: money % minus bets % on the over (2024+ only, 0 when missing)
  inj / inj_vs_usual - players listed out/doubtful on both teams, and vs each team's usual count (0 when missing)
  drama        - teams with news drama (coach fired, suspension, ...) in the few days before (sports_news; short history)
Model: P(over) = logistic regression on these (each one scaled to the league's spread of values).
The games are split by time: learn on the oldest half, try each factor on the next sixth (the validation slice) -
a factor is KEPT only if it makes the over/under chances more accurate there (log loss), added one at a time.
Then the keepers are refit on the oldest 2/3 and graded ONCE on the newest 1/3 the engine never saw: our side's hit
rate on the 10/20/30% of games where we lean hardest, and the money at the real over/under prices (-110 if missing).
A sport is PROVEN only if, on those unseen games, the top-30% side hit 52.4%+ (what beating -110 takes) on 150+
games, made money, and the low end of an 80% range around that hit rate is still above 50% (so it isn't luck).
Saved to data/sports/totals.json (weights + scaling per sport, fit on every game, for today's reads)."""
import json
import math
import os
from datetime import datetime, timedelta

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "totals.json")
ALPHA = {"nfl": 0.15, "ncaaf": 0.15, "nba": 0.07, "ncaab": 0.07, "mlb": 0.04, "nhl": 0.05}   # how fast form moves
FEATURES = ("form", "ou_home", "ou_away", "park", "lg_trend", "wind", "cold", "rain", "thin_air", "b2b", "rest",
            "travel", "starter", "public", "inj", "inj_vs_usual", "drama")
WEATHER = ("mlb", "nfl", "ncaaf")
PARK_K = 40            # park: act like 40 games of "no effect" on top of what the building has shown
STARTER_K = 3          # starter: act like 3 average starts on top of his last 5
STARTS = 5
DRAMA_DAYS = 5
GAP_H = 6              # a game only counts as "before" once it started 6+ hours earlier (it's over by then)
BREAKEVEN = 0.524
Z80 = 1.2816           # one-sided 80%: the low end of the range around the hit rate
MIN_TOP, MIN_ROWS = 150, 1000
MIN_GAIN = 1e-4        # a factor must cut validation log loss by at least this much to stay
L2 = 1.0               # a little shrink on every weight: no wild weights


def _sig(x):
    return 1 / (1 + math.exp(-max(-30, min(30, x))))


def _f(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


class Tracker:
    """Everything the features need, built one final at a time. features(g) only reads; update(g) learns the game."""

    def __init__(self, league, public=None, news=None):
        self.lg, self.a = league, ALPHA[league]
        self.public, self.news = public or {}, news or {}
        self.off, self.dfn, self.n = {}, {}, {}
        self.avg, self.k = None, 0
        self.res_home, self.res_away = {}, {}         # team -> recent residual at home / on the road
        self.park = {}                                # home team -> [sum of residuals, games]
        self.lg_res = 0.0
        self.last, self.home_tz = {}, {}              # team -> last game time; team -> its home time zone
        self.starts = {}                              # starter -> his last STARTS residuals
        self.inj_usual = {}                           # team -> usual injury count

    # ------------------------------------------------------------ reading
    def ready(self, g):
        return (self.avg is not None and sm._num(g.get("total")) and self.n.get(g["home"], 0) >= 5
                and self.n.get(g["away"], 0) >= 5)

    def _pred(self, h, w):
        half = self.avg / 2
        pred = (self.off[h] + self.dfn[w]) / 2 + (self.off[w] + self.dfn[h]) / 2
        return pred * 0.5 + self.avg * 0.5 * (pred / (2 * half)) if half else pred

    def _starter(self, name):
        xs = self.starts.get(name) or []
        return sum(xs) / (len(xs) + STARTER_K) if name else 0.0

    def _drama(self, team, day):
        n = 0
        for it in self.news.get(f"{self.lg}:{team}") or []:
            d = it.get("date") or ""
            if (day - timedelta(days=DRAMA_DAYS)).isoformat() <= d < day.isoformat():
                n = 1
        return n

    def features(self, g):
        h, w = g["home"], g["away"]
        line = sm._num(g.get("total"))
        t = _t(g["start"])
        neutral = str(g.get("neutral") or "0") == "1"
        outdoor = self.lg in WEATHER and str(g.get("indoor") or "0") != "1"
        temp, wind, rain = _f(g.get("wx_temp")), _f(g.get("wx_wind")), _f(g.get("wx_rain"))
        pk = self.park.get(h, (0.0, 0))
        rest = {s: min(7.0, (t - self.last[s]).total_seconds() / 86400) if s in self.last else 7.0 for s in (h, w)}
        tzo = _f(g.get("tzo"))
        travel = abs(tzo - self.home_tz[w]) if tzo is not None and w in self.home_tz else 0.0
        pub = self.public.get(g.get("id")) or {}
        pm, pt = pub.get("tot_over_m"), pub.get("tot_over_t")
        ih, ia = _f(g.get("inj_home")), _f(g.get("inj_away"))
        usual = sum((i - self.inj_usual[s]) for i, s in ((ih, h), (ia, w)) if i is not None and s in self.inj_usual)
        return {"form": self._pred(h, w) - line,
                "ou_home": self.res_home.get(h, 0.0),
                "ou_away": self.res_away.get(w, 0.0),
                "park": 0.0 if neutral else pk[0] / (pk[1] + PARK_K),
                "lg_trend": self.lg_res,
                "wind": wind if outdoor and wind is not None else 0.0,
                "cold": max(0.0, 50 - temp) / 10 if outdoor and temp is not None else 0.0,
                "rain": rain if outdoor and rain is not None else 0.0,
                "thin_air": max(0.0, (_f(g.get("elev")) or 0) - 1000) / 1000,
                "b2b": float(rest[h] <= 1.2) + float(rest[w] <= 1.2),
                "rest": (rest[h] + rest[w]) / 2,
                "travel": travel,
                "starter": self._starter(g.get("sp_home")) + self._starter(g.get("sp_away")),
                "public": float(pm - pt) if pm is not None and pt is not None else 0.0,
                "inj": (ih or 0.0) + (ia or 0.0),
                "inj_vs_usual": usual,
                "drama": float(self._drama(h, t.date()) + self._drama(w, t.date()))}

    # ------------------------------------------------------------ learning
    def update(self, g):
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            return
        h, w = g["home"], g["away"]
        line = sm._num(g.get("total"))
        tot = hs + as_
        if line:
            r = tot - line
            self.res_home[h] = self.res_home.get(h, r) + self.a * (r - self.res_home.get(h, r))
            self.res_away[w] = self.res_away.get(w, r) + self.a * (r - self.res_away.get(w, r))
            if str(g.get("neutral") or "0") != "1":
                s, n = self.park.get(h, (0.0, 0))
                self.park[h] = (s + r, n + 1)
            self.lg_res += 0.01 * (r - self.lg_res)
            for name, allowed in ((g.get("sp_home"), as_), (g.get("sp_away"), hs)):
                if name:
                    self.starts[name] = (self.starts.get(name, []) + [allowed - line / 2])[-STARTS:]
        self.k += 1
        self.avg = tot if self.avg is None else self.avg + (tot - self.avg) / min(self.k, 500)
        for t, pf, pa in ((h, hs, as_), (w, as_, hs)):
            if t not in self.off:
                self.off[t], self.dfn[t] = float(pf), float(pa)
            else:
                self.off[t] += self.a * (pf - self.off[t])
                self.dfn[t] += self.a * (pa - self.dfn[t])
            self.n[t] = self.n.get(t, 0) + 1
        for s, key in ((h, "inj_home"), (w, "inj_away")):
            i = _f(g.get(key))
            if i is not None:
                self.inj_usual[s] = self.inj_usual.get(s, i) + 0.2 * (i - self.inj_usual.get(s, i))
        t = _t(g["start"])
        self.last[h], self.last[w] = t, t
        tzo = _f(g.get("tzo"))
        if tzo is not None and str(g.get("neutral") or "0") != "1":
            self.home_tz[h] = tzo


def _public():
    try:
        import sports_public
        hist = sports_public._load(sports_public.PATH).get("games") or {}
        return {**hist, **sports_public._load(sports_public.LIVE)}
    except Exception:                                    # noqa: BLE001 - splits are optional
        return {}


def _news():
    try:
        import sports_news
        return sports_news.load() or {}
    except Exception:                                    # noqa: BLE001 - news is optional
        return {}


def rows(games, league, public=None, news=None):
    """[(features, went over 1/0, over odds, under odds, start)] in time order (pushes left out)."""
    tr = Tracker(league, public, news)
    out, pending = [], []
    for g in sm.finals(games, league):
        try:
            tot = int(g["home_score"]) + int(g["away_score"])
        except (TypeError, ValueError):
            continue
        t = _t(g["start"])
        while pending and _t(pending[0]["start"]) <= t - timedelta(hours=GAP_H):   # only games already OVER count
            tr.update(pending.pop(0))
        if tr.ready(g):
            line = sm._num(g.get("total"))
            if tot != line:
                x = tr.features(g)
                out.append(([x[k] for k in FEATURES], 1 if tot > line else 0,
                             sm._int(g.get("over_odds")) or -110, sm._int(g.get("under_odds")) or -110, g["start"]))
        pending.append(g)
    return out


# ---------------------------------------------------------------- the model
def norm(rs):
    """Per feature (mean, spread) on these rows; a feature with no spread (no data) gets None."""
    out = []
    n = len(rs)
    for j in range(len(FEATURES)):
        m = sum(r[0][j] for r in rs) / n
        sd_ = (sum((r[0][j] - m) ** 2 for r in rs) / n) ** 0.5
        out.append((m, sd_) if sd_ > 1e-9 else None)
    return out


def _design(rs, nz, idx):
    return [[1.0] + [max(-5.0, min(5.0, (r[0][j] - nz[j][0]) / nz[j][1])) for j in idx] for r in rs]


def _solve(A, b):
    n = len(b)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12:
            return [0.0] * n
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                if f:
                    M[r] = [a - f * b_ for a, b_ in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def fit(X, ys, iters=8):
    """Logistic regression by Newton's method (intercept first), with a little L2 shrink on the factor weights."""
    d = len(X[0])
    w = [0.0] * d
    for _ in range(iters):
        g = [0.0] * d
        H = [[0.0] * d for _ in range(d)]
        for x, y in zip(X, ys):
            p = _sig(sum(a * b for a, b in zip(w, x)))
            e, v = p - y, p * (1 - p)
            for i in range(d):
                g[i] += e * x[i]
                vi = v * x[i]
                Hi = H[i]
                for j in range(i + 1):
                    Hi[j] += vi * x[j]
        for i in range(d):
            for j in range(i):
                H[j][i] = H[i][j]
            if i:
                H[i][i] += L2
                g[i] += L2 * w[i]
        step = _solve(H, g)
        w = [a - s for a, s in zip(w, step)]
        if max(abs(s) for s in step) < 1e-6:
            break
    return w


def logloss(X, ys, w):
    tot = 0.0
    for x, y in zip(X, ys):
        q = min(max(_sig(sum(a * b for a, b in zip(w, x))), 1e-9), 1 - 1e-9)
        tot -= math.log(q if y else 1 - q)
    return tot / len(ys)


def select(learn, val):
    """Forward selection: try each factor alone on the validation slice, then add the helpful ones best-first,
    keeping each only if it still cuts validation log loss. Returns (kept names, per-factor screen, base, final ll)."""
    nz = norm(learn)
    yl, yv = [r[1] for r in learn], [r[1] for r in val]
    base = logloss(_design(val, nz, []), yv, fit(_design(learn, nz, []), yl))
    screen = {}
    for j, k in enumerate(FEATURES):
        if nz[j] is None:
            screen[k] = {"ll": None, "note": "no data"}
            continue
        w = fit(_design(learn, nz, [j]), yl)
        ll = logloss(_design(val, nz, [j]), yv, w)
        screen[k] = {"ll": round(ll, 5), "gain": round(base - ll, 5)}
    order = sorted((j for j, k in enumerate(FEATURES) if screen[k].get("gain", 0) > MIN_GAIN),
                   key=lambda j: -screen[FEATURES[j]]["gain"])
    kept, cur = [], base
    for j in order:
        idx = kept + [j]
        w = fit(_design(learn, nz, idx), yl)
        ll = logloss(_design(val, nz, idx), yv, w)
        if ll < cur - MIN_GAIN:
            kept, cur = idx, ll
    return [FEATURES[j] for j in kept], screen, base, cur


def _profit(odds, won):
    return (odds / 100 if odds > 0 else 100 / -odds) if won else -1.0


def grade(rs, nz, idx, w, tops=(0.1, 0.2, 0.3)):
    """Our side (over if P(over) > 50%) on these games: hit rate + ROI on all of them and on the top shares."""
    X = _design(rs, nz, idx)
    scored = []
    for x, r in zip(X, rs):
        p = _sig(sum(a * b for a, b in zip(w, x)))
        over = p > 0.5
        won = (r[1] == 1) == over
        scored.append((abs(p - 0.5), won, _profit(r[2] if over else r[3], won)))
    scored.sort(key=lambda s: -s[0])
    out = {}
    for name, share in [("all", 1.0)] + [(f"top{int(t * 100)}", t) for t in tops]:
        k = max(1, int(len(scored) * share))
        hit = sum(s[1] for s in scored[:k]) / k
        out[name] = {"n": k, "hit": round(hit, 4), "roi": round(sum(s[2] for s in scored[:k]) / k, 4),
                     "low80": round(hit - Z80 * math.sqrt(hit * (1 - hit) / k), 4)}
    return out


def proven(gr, kept):
    t = gr["top30"]
    return bool(kept) and t["n"] >= MIN_TOP and t["hit"] >= BREAKEVEN and t["low80"] > 0.5 and t["roi"] > 0


def study_league(rs):
    cut = len(rs) * 2 // 3
    learn, val, train, test = rs[:cut * 3 // 4], rs[cut * 3 // 4:cut], rs[:cut], rs[cut:]
    kept, screen, base, ll_val = select(learn, val)
    idx = [FEATURES.index(k) for k in kept]
    nz = norm(train)
    w = fit(_design(train, nz, idx), [r[1] for r in train])
    gr = grade(test, nz, idx, w)
    base_test = logloss(_design(test, nz, []), [r[1] for r in test], fit(_design(train, nz, []), [r[1] for r in train]))
    ll_test = logloss(_design(test, nz, idx), [r[1] for r in test], w)
    nz_all = norm(rs)                                   # today's reads: the same factors, learned on every game
    w_all = fit(_design(rs, nz_all, idx), [r[1] for r in rs])
    return {"games": len(rs), "test_games": len(test), "test_from": test[0][4][:10], "kept": kept,
            "screen": screen, "ll_val_base": round(base, 5), "ll_val_kept": round(ll_val, 5),
            "ll_test_base": round(base_test, 5), "ll_test_kept": round(ll_test, 5), "grade": gr,
            "hit_all": gr["all"]["hit"], "hit_top": gr["top30"]["hit"], "n_top": gr["top30"]["n"],
            "roi_top": gr["top30"]["roi"], "proven": proven(gr, kept),
            "intercept": round(w_all[0], 5),
            "weights": {k: round(v, 5) for k, v in zip(kept, w_all[1:])},
            "norm": {k: [round(nz_all[j][0], 5), round(nz_all[j][1], 5)] for k, j in zip(kept, idx)}}


def study(games, path=PATH, leagues=None, public=None, news=None):
    public = _public() if public is None else public
    news = _news() if news is None else news
    out = {}
    for lg in leagues or ALPHA:
        rs = rows(games, lg, public, news)
        out[lg] = study_league(rs) if len(rs) >= MIN_ROWS else {"games": len(rs), "proven": False, "kept": []}
    with open(path + ".tmp", "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)
    return out


# ---------------------------------------------------------------- today's games
def state(games, league):
    """Every team's (and starter's, and building's) form after the last final - for upcoming games."""
    tr = Tracker(league, _public(), _news())
    for g in sm.finals(games, league):
        tr.update(g)
    return tr


def p_over(fit, st, g):
    """Chance the game goes over its line, or None (not enough on both teams / no study)."""
    if "weights" not in fit or not st.ready(g):
        return None
    x = st.features(g)
    z = fit.get("intercept", 0.0)
    for k, wk in fit["weights"].items():
        m, s = fit["norm"][k]
        z += wk * max(-5.0, min(5.0, (x[k] - m) / s))
    return _sig(z)


def load():
    try:
        with open(PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def summary(st):
    lines = [f"{'sport':6} {'games':>6} {'test':>5} {'top30 hit':>9} {'n':>5} {'low80':>6} {'ROI':>7} {'top20':>6} "
             f"{'top10':>6} {'proven':>6}  kept"]
    for lg, v in st.items():
        if "grade" not in v:
            lines.append(f"{lg:6} {v['games']:>6}  (too few games)")
            continue
        g = v["grade"]
        lines.append(f"{lg:6} {v['games']:>6} {v['test_games']:>5} {g['top30']['hit']:>9.3f} {g['top30']['n']:>5} "
                     f"{g['top30']['low80']:>6.3f} {g['top30']['roi']:>+7.3f} {g['top20']['hit']:>6.3f} "
                     f"{g['top10']['hit']:>6.3f} {str(v['proven']):>6}  {', '.join(v['kept']) or '-'}")
    return lines


if __name__ == "__main__":
    print("\n".join(summary(study(sd.load_games()))))
