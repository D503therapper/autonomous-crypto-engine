"""THE COMEBACK STUDY: when do teams actually come back? Learned from every finished game's period-by-period score.

For every stored final (10 seasons, every sport) we take a snapshot at the end of each period / half / inning:
the score, how much game is left, how strong each team was going in (the closing line) and who won the last
period (momentum). From those snapshots the engine learns, per sport:

  1. the live win-chance curve  P(home wins) = Phi((margin + w * pregame_edge * left + m * momentum)
                                                   / (s * sigma * sqrt(left)))
     s = how wild the rest of the game plays out, w = how much being the better team still matters once you're
     behind, m = whether winning the last period carries over. Fit by maximum likelihood on the snapshots.
  2. the comeback table: teams down X at that point of the game (split by pregame favorite / dog) - how many,
     how often they came back. A live play needs this history to back it: no history, no bet.

Written to data/sports/comeback.json every engine run (cheap: a few seconds); sports_live.py reads it."""
import json
import math
import os

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "comeback.json")
SIGMA = {"nfl": 13.5, "ncaaf": 16.0, "nba": 12.0, "ncaab": 11.0, "nhl": 2.3, "mlb": 4.2}   # final-margin spread
PERIODS = {"nfl": 4, "ncaaf": 4, "nba": 4, "ncaab": 2, "nhl": 3, "mlb": 9}
PNAME = {"nfl": "quarter", "ncaaf": "quarter", "nba": "quarter", "ncaab": "half", "nhl": "period", "mlb": "inning"}
# deficit buckets (lo, hi) per sport
BUCKETS = {"nfl": [(1, 3), (4, 7), (8, 10), (11, 14), (15, 21), (22, 99)],
           "ncaaf": [(1, 3), (4, 7), (8, 10), (11, 14), (15, 21), (22, 99)],
           "nba": [(1, 5), (6, 10), (11, 15), (16, 20), (21, 99)],
           "ncaab": [(1, 5), (6, 10), (11, 15), (16, 20), (21, 99)],
           "nhl": [(1, 1), (2, 2), (3, 99)],
           "mlb": [(1, 1), (2, 2), (3, 3), (4, 5), (6, 99)]}
MIN_N = 30                  # a spot needs this many past games before history can back a live bet
S_GRID = [0.6 + 0.1 * i for i in range(20)]          # 0.6 .. 2.5
W_GRID = [0.25 * i for i in range(13)]               # 0 .. 3
M_GRID = [-0.2, -0.1, 0.0, 0.1, 0.2, 0.3]            # momentum: fraction of last period's margin that carries


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def phi_inv(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    lo, hi = -6.0, 6.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if phi(mid) < p else (lo, mid)
    return (lo + hi) / 2


def bucket(league, deficit):
    for lo, hi in BUCKETS[league]:
        if lo <= deficit <= hi:
            return (str(lo) if lo == hi else f"{lo} to {hi}") if hi < 99 else f"{lo}+"
    return None


def _ints(s):
    try:
        return [int(x) for x in str(s).split(",") if x != ""]
    except ValueError:
        return []


def snapshots(games, league):
    """[(k periods done, left, margin (home), last-period margin (home), pregame home p, home won)] for every
    real final with period scores and a closing line."""
    n = PERIODS[league]
    out = []
    for g in sm.finals(games, league):
        h, a = _ints(g.get("ls_home")), _ints(g.get("ls_away"))
        p = sm.market_p(g)
        if p is None or len(h) < n or len(a) < n:
            continue
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            continue
        if hs == as_:
            continue
        won = 1 if hs > as_ else 0
        ch = ca = 0
        for k in range(1, n):
            ch += h[k - 1]
            ca += a[k - 1]
            out.append((k, (n - k) / n, ch - ca, h[k - 1] - a[k - 1], p, won))
    return out


def prob(league, fit, p_pre, margin, left, last=0.0):
    s = SIGMA[league] * fit["s"]
    mu0 = SIGMA[league] * phi_inv(p_pre)
    left = max(left, 0.02)
    return phi((margin + fit["w"] * mu0 * left + fit["m"] * last) / (s * math.sqrt(left)))


def _ll(league, fit, snaps):
    tot = 0.0
    for k, left, mg, last, p, won in snaps:
        q = min(max(prob(league, fit, p, mg, left, last), 1e-4), 1 - 1e-4)
        tot -= math.log(q if won else 1 - q)
    return tot / max(len(snaps), 1)


def fit_curve(league, snaps):
    """Coordinate search over (s, w, m) for the best log loss; also the log loss of the untuned curve."""
    base = {"s": 1.0, "w": 1.0, "m": 0.0}
    if len(snaps) < 200:
        return dict(base, n=len(snaps), ll=None, ll_base=None)
    sample = snaps[:: max(1, len(snaps) // 20000)]        # cap the work per sport
    best, best_ll = dict(base), _ll(league, base, sample)
    base_ll = best_ll
    for _ in range(3):
        for key, grid in (("s", S_GRID), ("w", W_GRID), ("m", M_GRID)):
            for v in grid:
                f = dict(best, **{key: v})
                ll = _ll(league, f, sample)
                if ll < best_ll - 1e-6:
                    best, best_ll = f, ll
    return dict(best, n=len(snaps), ll=round(best_ll, 4), ll_base=round(base_ll, 4))


def table(league, snaps):
    """{'k|bucket|fav'|'dog': [n, came back]} - the trailing team's view."""
    out = {}
    for k, left, mg, last, p, won in snaps:
        if mg == 0:
            continue
        home_trails = mg < 0
        b = bucket(league, abs(mg))
        fav = (p >= 0.5) if home_trails else (p < 0.5)             # was the trailing team the pregame favorite?
        came_back = won if home_trails else 1 - won
        for key in (f"{k}|{b}|{'fav' if fav else 'dog'}", f"{k}|{b}|all"):
            c = out.setdefault(key, [0, 0])
            c[0] += 1
            c[1] += came_back
    return out


def study(games):
    """Run the study for every sport; save it. Returns {league: {...}}."""
    out = {}
    for lg in sd.LEAGUES:
        snaps = snapshots(games, lg)
        snaps.sort(key=lambda x: x[4])                            # deterministic sample
        out[lg] = {"curve": fit_curve(lg, snaps), "table": table(lg, snaps), "games": len(snaps) // max(PERIODS[lg] - 1, 1)}
    with open(PATH + ".tmp", "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    os.replace(PATH + ".tmp", PATH)
    return out


def load():
    try:
        with open(PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def summary(st):
    parts = []
    for lg, v in st.items():
        c = v["curve"]
        if c.get("ll") is not None:
            parts.append(f"{lg} {v['games']} games s={c['s']:.1f} w={c['w']:.2f} m={c['m']:+.1f} "
                         f"loss {c['ll_base']:.3f}->{c['ll']:.3f}")
        else:
            parts.append(f"{lg} {v['games']} games (not enough yet)")
    return "comeback study: " + "; ".join(parts)


def spot(st, league, left, deficit, fav):
    """History for a trailing team right now: (n, comeback rate, k periods done, bucket) or None.
    The live clock is mapped to the nearest period break."""
    lg = st.get(league) or {}
    n = PERIODS[league]
    k = min(max(round((1 - left) * n), 1), n - 1)
    b = bucket(league, deficit)
    for key in (f"{k}|{b}|{'fav' if fav else 'dog'}", f"{k}|{b}|all"):
        c = (lg.get("table") or {}).get(key)
        if c and c[0] >= MIN_N:
            return c[0], c[1] / c[0], k, b
    return None


def lead_spot(st, league, left, lead, fav):
    """History for a team that's AHEAD: how often teams up X at that point held on."""
    r = spot(st, league, left, lead, not fav)                     # the other side is trailing
    if not r:
        return None
    n, rate, k, b = r
    return n, 1 - rate, k, b


def when(league, k):
    """'at the half', 'after 1 quarter', 'through 6 innings'..."""
    if league == "mlb":
        return f"through {k} inning{'s' if k > 1 else ''}"
    if PERIODS[league] == 4 and k == 2 or league == "ncaab" and k == 1:
        return "at the half"
    word = PNAME[league]
    return f"after {k} {word}{'s' if k > 1 else ''}"


if __name__ == "__main__":
    print(summary(study(sd.load_games())))
