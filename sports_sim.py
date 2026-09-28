"""THE SIMULATOR: a walk-forward game simulator per league, graded against the closing line - and it's strict about it.

1) THE SIM. Before each past final, using ONLY games that started 6+ hours earlier, every team carries a margin
   rating and a pace (points-in-the-game) rating, i.e. offense = (margin + pace) / 2, defense = (pace - margin) / 2,
   updated after every final at a learned speed and pulled back toward average over the off-season. The league's
   scoring level, its home edge (0 at neutral sites), the spread of results and a rest effect are all learned from
   the past games too. Then the game is played out with a score model that fits the sport:
     nhl  - Poisson / negative-binomial goals per team; a regulation tie goes to OT/shootout (+1 goal for the winner)
     mlb  - negative-binomial runs per team; a tie goes to extra innings, inning by inning (runner-on-2nd era from
            2020, walk-offs end it by 1)
     nfl / ncaaf - a normal margin reshaped by LEARNED key numbers (3, 7, 10, 6, 14... and ties), normal total
     nba / ncaab - normal margin + normal total on whole points; a tie after regulation goes to overtime
   Every market we have a line for is priced from the sims: moneyline, spread / puck line / run line and the total
   (the data has no alt lines; today's slate also prints a fair-price ladder of alt spreads/totals).
   today() runs a real seeded Monte Carlo (10,000 sims a game). The history study prices each game EXACTLY from the
   same score model (the 10,000-sim answer with the sampling noise taken out: noise would only fake disagreements).
2) THE STUDY (per league x market, older half / newer half by time):
     - blend: logit p = logit(market) + w * (logit(sim) - logit(market)), w fit on the OLDER half only, graded on
       the NEWER half by log loss vs the market alone (paired z). The real test: does the sim know anything Vegas
       doesn't?
     - disagreement bets: bet the side the sim likes whenever it disagrees with the no-vig price by >= 2/4/6/8/10
       points: ROI at the real price and z of the edge over the no-vig price, in both halves.
     - calibration: sim-only log loss / Brier vs the market's, and a small reliability table.
   A cell becomes a SUSPECT only with n >= 300 bets, a profit in BOTH halves and z >= 3.5 (luck odds ~1 in 4,300; the
   report says how many suspects luck alone would give for the number of tests run). Then it must CONFIRM on games
   that finish after it was flagged: 100+ forward bets in profit with an edge z >= 1 -> PROVEN; 100+ forward bets
   that lose -> KILLED. Proven cells are re-checked every run and demoted the moment they stop making money.
3) IT LEARNS NEW THINGS EVERY RUN: each run also tries simulator variants it has NEVER tried (rating speed,
   off-season pull, home-edge treatment, score distribution / dispersion, key numbers, rest, pace weighting,
   recent-form weighting). Every tried config is fingerprinted in the registry and never retried. A variant that
   beats the league's current best sim (log loss, both halves) is a config suspect; it becomes the new best only if
   it beats it again on forward games. Every variant's own disagreement / blend cells go through the same
   suspect -> forward -> proven / killed gate.
4) Engine hooks: proven / load / adjust_side / adjust_total nudge a probability toward the sim ONLY for a proven
   league x market, by the proven FORWARD edge shrunk by n / (n + 400).
Saved to data/sports/sim.json (registry, results, proven, log) and data/sports/sim_today.json (today's slate)."""
import base64
import bisect
import hashlib
import json
import math
import os
import random
import time
import zlib
from collections import deque
from datetime import datetime, timezone

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "sim.json")
TODAY_PATH = os.path.join(sd.DATA, "sim_today.json")
LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "mlb", "nhl")
FOOTBALL, HOOPS, COUNT = ("nfl", "ncaaf"), ("nba", "ncaab"), ("mlb", "nhl")
MARKETS = ("ml", "spread", "total")
THRESHOLDS = (0.02, 0.04, 0.06, 0.08, 0.10)
MIN_N = 300                 # bets a cell needs to be judged at all
Z_PROVEN = 3.5              # discovery bar on the edge z (Bonferroni-style for the many tests)
P_LUCK = 0.5 * math.erfc(Z_PROVEN / math.sqrt(2))
FWD_N, FWD_Z = 100, 1.0     # forward bets needed to promote / kill; forward edge z needed to promote
FWD_GAMES = 150             # forward games before a config suspect is judged
MIN_GAIN = 0.0005           # log loss a variant must beat the best sim by, in both halves, to be a config suspect
MAX_CFG_SUSPECTS = 3        # per league
SHRINK = 400
SIMS = 10000
BATCH, BUDGET_S = 120, 400  # new variants per run (all leagues) / seconds (a run stays under ~8 min on Actions)
EARLIER_H = 6               # an earlier game counts only if it started this many hours before
SEASON_GAP_D = 60           # a team gap longer than this = a new season (ratings pulled toward average)
HASH_B = 5
LAST_TESTED = []            # the (league|config) keys the latest run tested as NEW (tests look at it)

# rating update speed (per game) and everything's starting point per league
BASE_GAIN = {"nfl": 0.14, "ncaaf": 0.24, "nba": 0.08, "ncaab": 0.16, "mlb": 0.015, "nhl": 0.025}
PACE0 = {"nfl": 0.5, "ncaaf": 0.5, "nba": 1.0, "ncaab": 1.0, "mlb": 0.5, "nhl": 0.5}   # total-rating speed vs margin
PARK_GAIN = 0.01            # the "park" knob: each home building's own scoring level, learned this fast
AVG_ALPHA = {"nfl": 0.01, "ncaaf": 0.004, "nba": 0.002, "ncaab": 0.001, "mlb": 0.001, "nhl": 0.002}
VAR_ALPHA = {"nfl": 0.01, "ncaaf": 0.004, "nba": 0.003, "ncaab": 0.002, "mlb": 0.002, "nhl": 0.002}
HFA0 = {"nfl": 1.8, "ncaaf": 3.0, "nba": 2.5, "ncaab": 3.5, "mlb": 0.15, "nhl": 0.2}
SIG0 = {"nfl": (13.5, 13.5), "ncaaf": (17.0, 16.0), "nba": (12.5, 18.0), "ncaab": (11.0, 15.0),
        "mlb": (4.3, 4.3), "nhl": (2.4, 2.4)}
MIN_TEAM = {"nfl": 3, "ncaaf": 3, "nba": 8, "ncaab": 6, "mlb": 15, "nhl": 10}   # games before a team is priced
WARM = 200                  # league games before anything is priced
FAST = 3.0                  # the "recent form" ratings move this many times faster
KMAX = 60                   # football key numbers learned for margins 0..KMAX-1
KEY_PRIOR = 8.0             # pseudo-games behind every key-number weight
OT_M = 3                    # basketball: a game tied after regulation is won by about this many in OT
NHL_OT_GOAL = 0.11          # of each team's final-score goals per game, about this many are the OT / shootout goal
MLB_XTRA = (0.5, 1.0)       # runs per half inning in extras: before 2020 / runner on 2nd from 2020
GHOST_FROM = "2020-07-01"

GRID = {"gain": (1.0, 0.5, 0.75, 1.5, 2.0, 3.0),   # rating speed (x the league base) - the rating half-life
        "pace": (1.0, 0.33, 0.5, 1.5, 2.0),         # how fast the pace / total ratings move vs the margin ratings
        "form": (0.0, 0.25, 0.5),                   # weight on the fast (recent-form) ratings
        "regress": (0.4, 0.1, 0.2, 0.6),            # off-season pull toward average
        "hfa": ("learned", "team", "none"),         # league-wide learned home edge / + each team's own / none
        "rest": (1, 0),                             # learned rest / back-to-back effect on the margin
        "park": (0, 1)}                             # each home building's own scoring level (totals)
DISP = {"nhl": (0.0, 25.0, 10.0), "mlb": (3.5, 2.5, 5.0, 7.0)}   # negative-binomial r (0 = Poisson)
SCALE = (1.0, 0.94, 1.06, 1.12)                     # normal leagues: x the learned spread of results
KEYS = (1, 0)                                       # football: learned key numbers on / off
DEFAULTS = {"ncaaf": {"regress": 0.2}, "nba": {"form": 0.25}, "mlb": {"park": 1}}   # the first "best" sim, before any variant won


def grid(league):
    g = dict(GRID)
    g["disp"] = DISP.get(league, SCALE)
    if league in FOOTBALL:
        g["keys"] = KEYS
    return g


def default_cfg(league):
    return {**{k: v[0] for k, v in grid(league).items()}, **DEFAULTS.get(league, {})}


def cfg_key(league, cfg):
    return league + "|" + "|".join(f"{k}={cfg[k]}" for k in sorted(cfg))


def cfg_of(key):
    lg, *parts = key.split("|")
    out = {}
    for p in parts:
        k, v = p.split("=", 1)
        try:
            out[k] = int(v) if k in ("rest", "keys", "park") else float(v)
        except ValueError:
            out[k] = v
    return lg, out


# ---------------------------------------------------------------- small helpers
def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _odds(x):
    return sd.parse_american(x)


def units(odds, won):
    return (odds / 100 if odds > 0 else 100 / -odds) if won else -1.0


def zscore(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m / math.sqrt(v / n) if v > 0 else 0.0


def _ll(p, y):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -math.log(p) if y else -math.log(1 - p)


def fair_american(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def _h(key):
    return hashlib.blake2b(key.encode(), digest_size=HASH_B).digest()


_SQ2 = math.sqrt(2)


def _phi(x):
    return 0.5 * (1 + math.erf(x / _SQ2))


# ---------------------------------------------------------------- score distributions (exact pricing)
class NormalInt:
    """A whole-number score quantity (margin or total) ~ normal on the integers, with an optional overtime rule:
    a tie (margin 0) is won in OT by +OT_M (prob q) or -OT_M."""

    def __init__(self, mu, sd_, ot_q=None):
        self.mu, self.sd, self.q = mu, max(sd_, 0.5), ot_q
        self.t0 = self._beq(0) if ot_q is not None else 0.0

    def _bgt(self, d):                       # base P(X > d)
        return 1 - _phi((math.floor(d) + 0.5 - self.mu) / self.sd)

    def _beq(self, k):
        return _phi((k + 0.5 - self.mu) / self.sd) - _phi((k - 0.5 - self.mu) / self.sd)

    def gt(self, d):
        v = self._bgt(d)
        if self.q is not None:
            v += self.t0 * (-(0 > d) + self.q * (OT_M > d) + (1 - self.q) * (-OT_M > d))
        return min(1.0, max(0.0, v))

    def eq(self, d):
        if d != int(d):
            return 0.0
        k = int(d)
        v = self._beq(k)
        if self.q is not None:
            v += self.t0 * (-(k == 0) + self.q * (k == OT_M) + (1 - self.q) * (k == -OT_M))
        return max(0.0, v)

    def sample(self, rnd):
        x = round(rnd.gauss(self.mu, self.sd))
        if x == 0 and self.q is not None:
            x = OT_M if rnd.random() < self.q else -OT_M
        return x


class Pmf:
    """An explicit distribution on the integers lo..lo+len-1 (football margins with key numbers)."""

    def __init__(self, lo, p):
        s = sum(p) or 1.0
        self.lo, self.p = lo, [x / s for x in p]
        self.cum, c = [], 0.0
        for x in self.p:
            c += x
            self.cum.append(c)

    def le(self, k):
        i = k - self.lo
        return 0.0 if i < 0 else 1.0 if i >= len(self.p) else self.cum[i]

    def gt(self, d):
        return 1 - self.le(math.floor(d))

    def eq(self, d):
        if d != int(d):
            return 0.0
        i = int(d) - self.lo
        return self.p[i] if 0 <= i < len(self.p) else 0.0

    def sample(self, rnd):
        return self.lo + min(len(self.p) - 1, bisect.bisect_left(self.cum, rnd.random() * self.cum[-1]))


def count_pmf(lam, r):
    """Goals / runs: Poisson (r = 0) or negative binomial with size r, truncated where the tail is ~0."""
    lam = max(lam, 0.05)
    if r and r > 0:
        q = lam / (r + lam)
        p0 = (r / (r + lam)) ** r
        out, c, k = [p0], p0, 0
        while c < 1 - 1e-9 and k < 40:
            out.append(out[-1] * (k + r) / (k + 1) * q)
            c += out[-1]
            k += 1
    else:
        p0 = math.exp(-lam)
        out, c, k = [p0], p0, 0
        while c < 1 - 1e-9 and k < 40:
            out.append(out[-1] * lam / (k + 1))
            c += out[-1]
            k += 1
    s = sum(out)
    return [x / s for x in out]


def _cum(p):
    out, c = [], 0.0
    for x in p:
        c += x
        out.append(c)
    return out


_XTRA = {}


def mlb_extras(mu):
    """Extra innings from a tie, both teams mu runs per half inning (Poisson): {margin: p}, [p(added runs = x)]."""
    if mu in _XTRA:
        return _XTRA[mu]
    pr = count_pmf(mu, 0)[:12]
    marg, added = {}, [0.0] * 60
    carry = {0: 1.0}                                          # still tied, runs added so far
    for inning in range(8):
        nxt = {}
        for add, pc in carry.items():
            for a, pa in enumerate(pr):
                for h, ph in enumerate(pr):
                    p = pc * pa * ph
                    if h > a:                                 # walk-off: home wins by 1
                        marg[1] = marg.get(1, 0.0) + p
                        added[min(59, add + 2 * a + 1)] += p
                    elif h < a:
                        marg[h - a] = marg.get(h - a, 0.0) + p
                        added[min(59, add + a + h)] += p
                    else:
                        nxt[min(58, add + 2 * a)] = nxt.get(min(58, add + 2 * a), 0.0) + p
        carry = nxt
    left = sum(carry.values())                                # (a 9th extra inning: call it a coin flip by 1)
    for add, pc in carry.items():
        marg[1] = marg.get(1, 0.0) + pc / 2
        marg[-1] = marg.get(-1, 0.0) + pc / 2
        added[min(59, add + 1)] += pc
    s = sum(marg.values()) or 1.0
    marg = {k: v / s for k, v in marg.items()}
    tot = sum(added) or 1.0
    added = [x / tot for x in added]
    _XTRA[mu] = (marg, added, _cum(added), left)
    return _XTRA[mu]


class CountGame:
    """Home / away goals (runs) independent per team; a regulation tie is settled by `ext`: {margin: p} and the
    distribution of goals (runs) it adds."""

    def __init__(self, lh, la, r, ext_marg, ext_add):
        self.ph, self.pa = count_pmf(lh, r), count_pmf(la, r)
        self.ch, self.ca = _cum(self.ph), _cum(self.pa)
        self.ext, self.add = ext_marg, ext_add
        self.addc = _cum(ext_add)
        n = min(len(self.ph), len(self.pa))
        self.ties = [self.ph[k] * self.pa[k] for k in range(n)]
        self.tie = sum(self.ties)
        self.M, self.T = _View(self, "m"), _View(self, "t")

    def _ca(self, j):
        return 0.0 if j < 0 else self.ca[min(j, len(self.ca) - 1)]

    def _chh(self, j):
        return 0.0 if j < 0 else self.ch[min(j, len(self.ch) - 1)]

    # margin
    def m_ge(self, k):                                        # P(final margin >= k)
        if k >= 1:
            reg = sum(p * self._ca(i - k) for i, p in enumerate(self.ph) if i >= k)
            return reg + self.tie * sum(v for d, v in self.ext.items() if d >= k)
        return 1 - self.m_le(k - 1)

    def m_le(self, k):                                        # P(final margin <= k), k <= -1
        if k >= 0:
            return 1 - self.m_ge(k + 1)
        d = -k
        reg = sum(p * self._chh(j - d) for j, p in enumerate(self.pa) if j >= d)
        return reg + self.tie * sum(v for m, v in self.ext.items() if m <= k)

    def m_gt(self, d):
        return self.m_ge(math.floor(d) + 1)

    def m_eq(self, d):
        if d != int(d) or d == 0:
            return 0.0
        k = int(d)
        return self.m_ge(k) - self.m_ge(k + 1)

    # total
    def t_le(self, n):
        if n < 0:
            return 0.0
        reg = sum(p * self._ca(n - i) for i, p in enumerate(self.ph) if i <= n)
        tie_in = sum(t for k, t in enumerate(self.ties) if 2 * k <= n)
        ext = sum(t * self.addc[min(n - 2 * k, len(self.addc) - 1)] for k, t in enumerate(self.ties) if 2 * k <= n)
        return reg - tie_in + ext

    def t_gt(self, L):
        return 1 - self.t_le(math.floor(L))

    def t_eq(self, L):
        if L != int(L):
            return 0.0
        return self.t_le(int(L)) - self.t_le(int(L) - 1)

    def sample(self, rnd, extras):
        h = min(len(self.ph) - 1, bisect.bisect_left(self.ch, rnd.random() * self.ch[-1]))
        a = min(len(self.pa) - 1, bisect.bisect_left(self.ca, rnd.random() * self.ca[-1]))
        if h == a:
            h, a = extras(rnd, h, a)
        return h, a


class _View:
    def __init__(self, g, kind):
        self.g, self.kind = g, kind

    def gt(self, d):
        return self.g.m_gt(d) if self.kind == "m" else self.g.t_gt(d)

    def eq(self, d):
        return self.g.m_eq(d) if self.kind == "m" else self.g.t_eq(d)


def _poisson(rnd, lam):
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rnd.random()
        if p <= L:
            return k
        k += 1


def p_home_win(M):
    w, t = M.gt(0), M.eq(0)
    lose = max(1e-9, 1 - w - t)
    return w / max(1e-9, w + lose)


def p_cover(M, line):
    """Home covers `line` (home spread): margin + line > 0; pushes don't count."""
    d = -line
    return M.gt(d) / max(1e-9, 1 - M.eq(d))


def p_over(T, line):
    return T.gt(line) / max(1e-9, 1 - T.eq(line))


# ---------------------------------------------------------------- the ratings (walked forward)
class Model:
    """One league's ratings under one config. predict(g) reads; apply(g) learns a final."""

    def __init__(self, league, cfg):
        self.lg, self.cfg = league, cfg
        self.gain = BASE_GAIN[league] * cfg["gain"]
        self.s, self.c, self.sf, self.cf, self.n, self.last, self.th = {}, {}, {}, {}, {}, {}, {}
        self.park = {}
        self.avg, self.avg_n = 0.0, 0
        self.hfa = HFA0[league] if cfg["hfa"] != "none" else 0.0
        self.var_m, self.var_t = SIG0[league][0] ** 2, SIG0[league][1] ** 2
        self.sxx, self.sxy, self.beta = 0.0, 0.0, 0.0
        self.games = 0
        self.k_obs, self.k_exp, self.kw = [0.0] * KMAX, [0.0] * KMAX, [1.0] * KMAX

    def _team(self, tm, t):
        last = self.last.get(tm)
        if last is not None and t - last > SEASON_GAP_D * 86400:
            k = 1 - self.cfg["regress"]
            for d in (self.s, self.c, self.sf, self.cf, self.th):
                if tm in d:
                    d[tm] *= k
            self.last[tm] = None                            # (pulled once per break)
        f = self.cfg["form"]
        s = (1 - f) * self.s.get(tm, 0.0) + f * self.sf.get(tm, 0.0)
        c = (1 - f) * self.c.get(tm, 0.0) + f * self.cf.get(tm, 0.0)
        return s, c

    def _rest(self, g, t):
        def days(tm):
            v = self.last.get(tm)
            return 10.0 if v is None else min(10.0, (t - v) / 86400)
        dh, da = days(g["home"]), days(g["away"])
        if self.lg in FOOTBALL:
            return (dh - da) / 7
        return float(da <= 1.2) - float(dh <= 1.2)          # + when only the away team played yesterday

    def ready(self, g):
        return self.games >= WARM and self.n.get(g["home"], 0) >= MIN_TEAM[self.lg] \
            and self.n.get(g["away"], 0) >= MIN_TEAM[self.lg]

    def predict(self, g, t):
        """(expected home score, expected away score, expected margin, expected total, rest input)."""
        sh, ch = self._team(g["home"], t)
        sa, ca = self._team(g["away"], t)
        neutral = str(g.get("neutral")) == "1"
        hf = 0.0 if neutral or self.cfg["hfa"] == "none" else self.hfa + self.th.get(g["home"], 0.0)
        x = self._rest(g, t)
        margin = sh - sa + hf + (self.beta * x if self.cfg["rest"] else 0.0)
        total = 2 * self.avg + ch + ca
        if self.cfg.get("park") and not neutral:
            total += self.park.get(g["home"], 0.0)
        if self.lg in COUNT:
            total = max(total, 1.0)
        return (total + margin) / 2, (total - margin) / 2, margin, total, x

    def apply(self, g):
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            return
        t = sm._ts(g["start"])
        h, a = g["home"], g["away"]
        _, _, mp, tp, x = self.predict(g, t)
        known = self.n.get(h, 0) >= MIN_TEAM[self.lg] and self.n.get(a, 0) >= MIN_TEAM[self.lg]
        if self.lg in FOOTBALL and self.games >= WARM and known:
            self._keys(mp, abs(hs - as_))
        em, et = (hs - as_) - mp, (hs + as_) - tp
        gm, gt = self.gain, self.gain * self.cfg["pace"] * PACE0[self.lg]
        for d, gg in ((self.s, gm), (self.sf, gm * FAST)):
            d[h] = d.get(h, 0.0) + gg * em / 2
            d[a] = d.get(a, 0.0) - gg * em / 2
        for d, gg in ((self.c, gt), (self.cf, gt * FAST)):
            d[h] = d.get(h, 0.0) + gg * et / 2
            d[a] = d.get(a, 0.0) + gg * et / 2
        self.avg_n += 1
        pts = (hs + as_) / 2
        self.avg += (pts - self.avg) * max(AVG_ALPHA[self.lg], 1 / self.avg_n)
        if known:                                  # league-wide things: only from games between established teams
            if self.cfg.get("park") and str(g.get("neutral")) != "1":
                self.park[h] = self.park.get(h, 0.0) + PARK_GAIN * et
            if str(g.get("neutral")) != "1" and self.cfg["hfa"] != "none":
                self.hfa += AVG_ALPHA[self.lg] * em
                if self.cfg["hfa"] == "team":
                    self.th[h] = self.th.get(h, 0.0) + 0.02 * em
            va = VAR_ALPHA[self.lg]
            self.var_m += va * (em * em - self.var_m)
            self.var_t += va * (et * et - self.var_t)
            r = em + (self.beta * x if self.cfg["rest"] else 0.0)     # the margin miss without the rest effect
            self.sxx = 0.999 * self.sxx + x * x
            self.sxy = 0.999 * self.sxy + x * r
            self.beta = self.sxy / (self.sxx + 50.0)
        for tm in (h, a):
            self.n[tm] = self.n.get(tm, 0) + 1
            self.last[tm] = t
        self.games += 1

    # football key numbers: how often each final margin happens vs what the plain normal curve says
    def _keys(self, mu, m):
        sd_ = math.sqrt(self.var_m)
        prev = _phi((-0.5 - mu) / sd_)
        base = [0.0] * KMAX
        cdf = [prev]
        for k in range(-KMAX + 1, KMAX):
            cdf.append(_phi((k + 0.5 - mu) / sd_))
        for i, k in enumerate(range(-KMAX + 1, KMAX)):
            base[abs(k)] += cdf[i + 1] - cdf[i]
        for k in range(KMAX):
            self.k_exp[k] += base[k]
        if m < KMAX:
            self.k_obs[m] += 1
        if self.games % 50 == 0:
            self.kw = [(o + KEY_PRIOR) / (e + KEY_PRIOR) for o, e in zip(self.k_obs, self.k_exp)]

    def dists(self, g, mu_h, mu_a, margin, total):
        """(margin distribution, total distribution, count game or None) for this game."""
        lg, disp = self.lg, self.cfg["disp"]
        if lg in COUNT:
            if lg == "nhl":
                lh, la = max(0.2, mu_h - NHL_OT_GOAL), max(0.2, mu_a - NHL_OT_GOAL)
                q = lh / (lh + la)
                cg = CountGame(lh, la, disp, {1: q, -1: 1 - q}, [0.0, 1.0])
            else:
                marg, add, _, _ = mlb_extras(MLB_XTRA[g["start"][:10] >= GHOST_FROM])
                cg = CountGame(max(0.3, mu_h), max(0.3, mu_a), disp, marg, add)
            return cg.M, cg.T, cg
        sdm, sdt = math.sqrt(self.var_m) * disp, math.sqrt(self.var_t) * disp
        T = NormalInt(total, sdt)
        if lg in HOOPS:
            q = _phi(margin / (sdm * math.sqrt(10)))                 # OT is ~1/10 of a game
            return NormalInt(margin, sdm, q), T, None
        if self.cfg.get("keys", 0):
            lo, hi = math.floor(margin - 5 * sdm), math.ceil(margin + 5 * sdm)
            prev = _phi((lo - 0.5 - margin) / sdm)
            p = []
            for k in range(lo, hi + 1):
                c = _phi((k + 0.5 - margin) / sdm)
                p.append((c - prev) * (self.kw[abs(k)] if abs(k) < KMAX else 1.0))
                prev = c
            return Pmf(lo, p), T, None
        return NormalInt(margin, sdm), T, None


def _extras_mc(league, start):
    if league == "nhl":
        return None
    mu = MLB_XTRA[start[:10] >= GHOST_FROM]

    def run(rnd, h, a):
        for _ in range(20):
            x, y = _poisson(rnd, mu), _poisson(rnd, mu)
            if y > x:
                return h + x + 1, a + x
            if y < x:
                return h + y, a + x
            h, a = h + x, a + x
        return h + 1, a
    return run


def simulate(model, g, sims=SIMS, seed=0):
    """Monte Carlo one game: sims seeded draws from its score model -> (home scores, away scores)."""
    t = sm._ts(g["start"])
    mu_h, mu_a, margin, total, _ = model.predict(g, t)
    M, T, cg = model.dists(g, mu_h, mu_a, margin, total)
    rnd = random.Random(seed ^ zlib.crc32(str(g["id"]).encode()))
    hs, as_ = [], []
    if cg is not None:
        if model.lg == "nhl":
            q = cg.ext.get(1, 0.5)

            def ext(r, h, a):
                return (h + 1, a) if r.random() < q else (h, a + 1)
        else:
            ext = _extras_mc(model.lg, g["start"])
        for _ in range(sims):
            h, a = cg.sample(rnd, ext)
            hs.append(h)
            as_.append(a)
        return hs, as_
    for _ in range(sims):
        m, tt = M.sample(rnd), T.sample(rnd)
        if (tt - m) % 2:
            tt += 1 if rnd.random() < 0.5 else -1
        tt = max(tt, abs(m))
        hs.append((tt + m) // 2)
        as_.append((tt - m) // 2)
    return hs, as_


def mc_prices(hs, as_, line=None, tot=None):
    """Win / cover / over chances from simulated scores (ties and pushes left out)."""
    n = len(hs)
    w = sum(1 for h, a in zip(hs, as_) if h > a)
    lo = sum(1 for h, a in zip(hs, as_) if h < a)
    out = {"ml": w / max(1, w + lo), "home": round(sum(hs) / n, 2), "away": round(sum(as_) / n, 2)}
    if line is not None:
        c = sum(1 for h, a in zip(hs, as_) if h - a + line > 0)
        nc = sum(1 for h, a in zip(hs, as_) if h - a + line < 0)
        out["spread"] = c / max(1, c + nc)
    if tot is not None:
        o = sum(1 for h, a in zip(hs, as_) if h + a > tot)
        u = sum(1 for h, a in zip(hs, as_) if h + a < tot)
        out["total"] = o / max(1, o + u)
    return out


# ---------------------------------------------------------------- the walk: every final priced before it happened
def _lines(g, league):
    """The markets this game had lines for: {market: (line, odds_a, odds_b, market fair chance of side a)}."""
    out = {}
    oh, oa = _odds(g.get("ml_home")), _odds(g.get("ml_away"))
    if oh and oa:
        out["ml"] = (None, oh, oa, sd.no_vig(oh, oa))
    line = _num(g.get("spread_home"))
    if line is not None and abs(line) < 60 and not (league in COUNT and line == 0):
        sh, sa = _odds(g.get("spread_home_odds")) or -110, _odds(g.get("spread_away_odds")) or -110
        out["spread"] = (line, sh, sa, sd.no_vig(sh, sa))
    tot = _num(g.get("total"))
    if tot is not None and tot > 0:
        oo, uo = _odds(g.get("over_odds")) or -110, _odds(g.get("under_odds")) or -110
        out["total"] = (tot, oo, uo, sd.no_vig(oo, uo))
    return out


def price(model, g, t, lines):
    """{market: sim chance of side a (home win / home cover / over)} for the lines given."""
    mu_h, mu_a, margin, total, _ = model.predict(g, t)
    M, T, _ = model.dists(g, mu_h, mu_a, margin, total)
    out = {}
    for mk, (line, *_rest) in lines.items():
        if mk == "ml":
            out[mk] = p_home_win(M)
        elif mk == "spread":
            out[mk] = p_cover(M, line)
        else:
            out[mk] = p_over(T, line)
    return out, (mu_h, mu_a)


def walk(fin, league, cfg):
    """Walk the finals in time order -> (model after all of them, {market: rows}).
    row = (start, game id, sim chance of side a, market no-vig chance of side a, side a hit (1/0), odds a, odds b)."""
    model = Model(league, cfg)
    pending = deque()
    rows = {m: [] for m in MARKETS}
    for g in fin:
        t = sm._ts(g["start"])
        while pending and pending[0][0] <= t - EARLIER_H * 3600:
            model.apply(pending.popleft()[1])
        if model.ready(g):
            lines = _lines(g, league)
            if lines:
                hs, as_ = int(g["home_score"]), int(g["away_score"])
                ps, _ = price(model, g, t, lines)
                for mk, (line, oa, ob, fair) in lines.items():
                    if mk == "ml":
                        y = None if hs == as_ else int(hs > as_)
                    elif mk == "spread":
                        v = hs - as_ + line
                        y = None if v == 0 else int(v > 0)
                    else:
                        v = hs + as_ - line
                        y = None if v == 0 else int(v > 0)
                    if y is not None:
                        rows[mk].append((g["start"], g["id"], min(1 - 1e-6, max(1e-6, ps[mk])), fair, y, oa, ob))
        pending.append((t, g))
    while pending:
        model.apply(pending.popleft()[1])
    return model, rows


# ---------------------------------------------------------------- 2) the study on one market's rows
def fit_blend(rows, iters=30, lam=1.0):
    """w in logit p = logit(m) + w * (logit(s) - logit(m)), by Newton, clamped to [0, 1]."""
    xs = [(sm.logit(s) - sm.logit(m), sm.logit(m), y) for _, _, s, m, y, _, _ in rows]
    w = 0.0
    for _ in range(iters):
        g, H = lam * w, lam
        for x, o, y in xs:
            p = sm.sigmoid(o + w * x)
            g += (p - y) * x
            H += p * (1 - p) * x * x
        step = g / H
        w -= step
        if abs(step) < 1e-7:
            break
    return min(1.0, max(0.0, w))


def blend_p(s, m, w):
    return sm.sigmoid(sm.logit(m) + w * (sm.logit(s) - sm.logit(m)))


def bets(rows, thr):
    """Back the side the sim likes when it disagrees with the no-vig price by >= thr: [(row index, won, fair, units)]."""
    out = []
    for i, (_, _, s, m, y, oa, ob) in enumerate(rows):
        d = s - m
        if d >= thr:
            out.append((i, y == 1, m, units(oa, y == 1)))
        elif d <= -thr:
            out.append((i, y == 0, 1 - m, units(ob, y == 0)))
    return out


def bet_stats(bs, half):
    n = len(bs)
    if not n:
        return {"n": 0}
    P = [u for _, _, _, u in bs]
    E = [(1.0 if w else 0.0) - f for _, w, f, _ in bs]
    a = [u for i, _, _, u in bs if i < half]
    b = [u for i, _, _, u in bs if i >= half]
    return {"n": n, "roi": round(sum(P) / n, 4), "z": round(zscore(P), 2), "edge": round(sum(E) / n, 4),
            "z_edge": round(zscore(E), 2), "win": round(sum(1 for _, w, _, _ in bs if w) / n, 4),
            "fair": round(sum(f for _, _, f, _ in bs) / n, 4),
            "n_old": len(a), "roi_old": round(sum(a) / len(a), 4) if a else 0.0,
            "n_new": len(b), "roi_new": round(sum(b) / len(b), 4) if b else 0.0}


def is_suspect(s):
    return s.get("n", 0) >= MIN_N and s["roi_old"] > 0 and s["roi_new"] > 0 and s["z_edge"] >= Z_PROVEN


def study_market(rows):
    """Everything the study says about one league x market for one config."""
    n = len(rows)
    if n < 40:
        return {"n": n}
    h = n // 2
    old, new = rows[:h], rows[h:]
    w = fit_blend(old)
    d = [_ll(blend_p(s, m, w), y) - _ll(m, y) for _, _, s, m, y, _, _ in new]
    mean_d = sum(d) / len(d)
    zb = -zscore(d) if any(d) else 0.0

    def ll(rs, k):
        return round(sum(_ll(r[k], r[4]) for r in rs) / len(rs), 4)

    def brier(rs, k):
        return round(sum((r[k] - r[4]) ** 2 for r in rs) / len(rs), 4)
    cal = []
    for lo in (0.0, 0.2, 0.4, 0.6, 0.8):
        b = [r for r in new if lo <= r[2] < lo + 0.2 or (lo == 0.8 and r[2] >= 1.0)]
        if b:
            cal.append({"bin": f"{lo:.1f}-{lo + 0.2:.1f}", "n": len(b), "sim": round(sum(r[2] for r in b) / len(b), 3),
                        "market": round(sum(r[3] for r in b) / len(b), 3), "hit": round(sum(r[4] for r in b) / len(b), 3)})
    thr = {f"{t:.2f}": bet_stats(bets(rows, t), h) for t in THRESHOLDS}
    return {"n": n, "n_old": h, "n_new": n - h, "split": new[0][0][:10],
            "ll_sim_old": ll(old, 2), "ll_mkt_old": ll(old, 3), "ll_sim_new": ll(new, 2), "ll_mkt_new": ll(new, 3),
            "brier_sim_new": brier(new, 2), "brier_mkt_new": brier(new, 3),
            "blend": {"w": round(w, 4), "ll_new": round(ll(new, 3) + mean_d, 4), "gain_new": round(-mean_d, 5),
                      "z": round(zb, 2), "n_new": n - h},
            "thr": thr, "cal_new": cal}


def study_config(fin, league, cfg):
    model, rows = walk(fin, league, cfg)
    return model, rows, {mk: study_market(rs) for mk, rs in rows.items() if rs}


def cells(league, key, res):
    """Every (cell key, stats, passes) the study of one config produced: blend + each threshold, per market."""
    out = []
    for mk, r in res.items():
        if r.get("n", 0) < 40:
            continue
        b = r["blend"]
        bs = {"n": b["n_new"], "w": b["w"], "gain_new": b["gain_new"], "z": b["z"]}
        out.append((f"{league}|{mk}|blend|{key}", bs,
                    b["n_new"] >= MIN_N and b["w"] > 0 and b["gain_new"] > 0 and b["z"] >= Z_PROVEN))
        for t, s in r["thr"].items():
            out.append((f"{league}|{mk}|thr:{t}|{key}", s, is_suspect(s)))
    return out


def sim_ll(rows):
    """{(market, game id): sim log loss} for comparing two configs on the very same games."""
    return {(mk, r[1]): (r[0], _ll(r[2], r[4])) for mk, rs in rows.items() for r in rs}


def compare(var, inc, split=None, after=None):
    """Mean log loss (variant - incumbent) per market, averaged over markets, on matched games.
    split -> (older half, newer half) at that start; after -> only games that started after it."""
    by = {}
    for k, (st, llv) in var.items():
        if k not in inc or (after and st <= after):
            continue
        part = 0 if split is None or st < split else 1
        by.setdefault((part, k[0]), []).append(llv - inc[k][1])
    parts = {}
    for (part, mk), ds in by.items():
        parts.setdefault(part, []).append((sum(ds) / len(ds), len(ds), ds))
    out = {}
    for part, xs in parts.items():
        allds = [d for _, _, ds in xs for d in ds]
        out[part] = {"diff": round(sum(m for m, _, _ in xs) / len(xs), 5), "n": sum(n for _, n, _ in xs),
                     "z": round(-zscore(allds), 2)}
    return out


# ---------------------------------------------------------------- forward checks
def fwd_cell(ckey, e, rows):
    """A suspect / proven cell graded on games that started after its cutoff only."""
    lg, mk, kind = ckey.split("|")[:3]
    rs = [r for r in rows.get(mk, []) if r[0] > e["cutoff"]]
    if kind == "blend":
        w = e["w"]
        d = [_ll(blend_p(s, m, w), y) - _ll(m, y) for _, _, s, m, y, _, _ in rs]
        bs = bets(rs, 0.0)
        n = len(d)
        out = {"n": n, "gain": round(-sum(d) / n, 5) if n else 0.0, "z": round(-zscore(d), 2) if n else 0.0}
        st = bet_stats(bs, len(rs))
        out.update({"bets": st.get("n", 0), "roi": st.get("roi", 0.0), "edge": st.get("edge"), "fair": st.get("fair"),
                    "z_edge": st.get("z_edge", 0.0)})
        return out
    thr = float(kind.split(":")[1])
    return bet_stats(bets(rs, thr), len(rs))


def shift_of(fwd):
    """The logit nudge a proven threshold cell earns: its FORWARD edge only, shrunk by n / (n + 400)."""
    n, f, e = fwd.get("n", 0), fwd.get("fair"), fwd.get("edge")
    if not n or f is None or e is None:
        return 0.0
    return round((sm.logit(min(0.99, max(0.01, f + e))) - sm.logit(f)) * n / (n + SHRINK), 4)


# ---------------------------------------------------------------- registry
def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def load(path=None, today_path=None):
    """The registry (sim.json) with today's slate (sim_today.json) under 'today' - for the engine hooks."""
    st = _load(path or PATH)
    td = _load(today_path or (TODAY_PATH if path is None else os.path.join(os.path.dirname(path), "sim_today.json")))
    if td:
        st["today"] = td
    return st


def _seen(st):
    raw = base64.b64decode(st.get("seen", "") or b"")
    return {raw[i:i + HASH_B] for i in range(0, len(raw), HASH_B)}


def _save(st, seen, path):
    st["seen"] = base64.b64encode(b"".join(sorted(seen))).decode()
    st.pop("today", None)
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)


def candidates(league, inc, seen):
    """Untried configs for a league: one-knob changes of the current best first, then the rest of the grid in a
    fixed hashed order."""
    gr = grid(league)
    names = sorted(gr)
    out, keys = [], set()
    for k in names:
        for v in gr[k]:
            if v != inc.get(k):
                c = dict(inc, **{k: v})
                key = cfg_key(league, c)
                if key not in keys and _h(key) not in seen:
                    keys.add(key)
                    out.append((key, c))
    yield from out

    def every(i, cur):
        if i == len(names):
            yield dict(cur)
            return
        for v in gr[names[i]]:
            cur[names[i]] = v
            yield from every(i + 1, cur)
    rest = []
    for c in every(0, {}):
        key = cfg_key(league, c)
        if key not in keys and _h(key) not in seen:
            rest.append((hashlib.blake2b(key.encode(), digest_size=8).digest(), key, c))
    rest.sort()
    for _, key, c in rest:
        yield key, c


def _brief(key, e):
    d, f = e.get("disc", {}), e.get("fwd", {})
    if "|blend|" in key:
        return (f"{key}: found w={d.get('w')} newer-half gain {d.get('gain_new', 0):+.5f} z={d.get('z')}"
                f" | forward n={f.get('n', 0)} gain {f.get('gain', 0):+.5f} z={f.get('z', 0)}")
    return (f"{key}: found n={d.get('n')} roi {d.get('roi_old', 0):+.3f} then {d.get('roi_new', 0):+.3f}"
            f" edge z={d.get('z_edge')} | forward n={f.get('n', 0)} roi {f.get('roi', 0):+.3f} edge z={f.get('z_edge', 0)}")


def _summ_market(r):
    """The short per-league x market line for the results table."""
    if r.get("n", 0) < 40:
        return {"n": r.get("n", 0)}
    best = max(r["thr"].items(), key=lambda kv: (kv[1].get("n", 0) >= MIN_N, kv[1].get("z_edge", -99)))
    return {"n": r["n"], "split": r["split"], "ll_sim_new": r["ll_sim_new"], "ll_mkt_new": r["ll_mkt_new"],
            "ll_blend_new": r["blend"]["ll_new"], "blend_w": r["blend"]["w"], "blend_z": r["blend"]["z"],
            "brier_sim_new": r["brier_sim_new"], "brier_mkt_new": r["brier_mkt_new"],
            "best_thr": best[0], "best_bet": best[1], "thr": r["thr"], "cal_new": r["cal_new"]}


# ---------------------------------------------------------------- 3) the run
def run(games, path=PATH, batch=BATCH, budget_s=BUDGET_S, leagues=LEAGUES, verbose=True):
    """One sim run: re-grade the best sims + every suspect / proven cell on forward games, then try NEW variants."""
    t0 = time.time()
    st = _load(path)
    st.pop("today", None)
    seen = _seen(st)
    for k in ("suspects", "proven", "killed", "best", "cfg_suspects", "cfg_killed", "results"):
        st.setdefault(k, {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    fins, newest = {}, {}
    for lg in leagues:
        f = sm.finals(games, lg)
        if len(f) > WARM:
            fins[lg], newest[lg] = f, f[-1]["start"]
    cache, secs = {}, {}

    def evaluate(lg, key):
        if (lg, key) not in cache:
            t1 = time.time()
            _, cfg = cfg_of(key)
            _, rows, res = study_config(fins[lg], lg, cfg)
            cache[(lg, key)] = (rows, res, sim_ll(rows))
            secs[lg] = max(secs.get(lg, 0.0), time.time() - t1)
        return cache[(lg, key)]

    tests, found, near, near_cfg = 0, [], [], []
    promoted, killed, demoted, cfg_new, cfg_prom, cfg_kill = [], [], [], [], [], []
    taken = {"|".join(k.split("|")[:3]) for s in ("suspects", "proven") for k in st[s]}

    def discover(lg, key, res):
        nonlocal tests
        for ck, s, ok in cells(lg, key, res):
            tests += 1
            base = "|".join(ck.split("|")[:3])
            if ok and base not in taken:
                taken.add(base)
                e = {"league": lg, "market": ck.split("|")[1], "kind": ck.split("|")[2], "cfg": key,
                     "cutoff": newest[lg], "found": now, "disc": s, "fwd": {}}
                if "|blend|" in ck:
                    e["w"] = s["w"]
                st["suspects"][ck] = e
                found.append(ck)
            elif not ok and s.get("n", 0) >= MIN_N and ("|blend|" in ck and s.get("gain_new", 0) > 0 or
                                                          s.get("roi_old", 0) > 0 and s.get("roi_new", 0) > 0):
                near.append((s.get("z_edge", s.get("z", 0)), ck, s))

    # -- the current best sim per league (the first run: the default config, tested as new)
    del LAST_TESTED[:]
    for lg in fins:
        b = st["best"].get(lg)
        key = b["key"] if b else cfg_key(lg, default_cfg(lg))
        if not b:
            st["best"][lg] = {"key": key, "since": now}
        rows, res, _ = evaluate(lg, key)
        if _h(key) not in seen:
            seen.add(_h(key))
            LAST_TESTED.append(key)
            discover(lg, key, res)
        st["results"][lg] = {"cfg": key, "games": len(fins[lg]), "markets": {mk: _summ_market(r) for mk, r in res.items()}}
    # -- every suspect / proven cell on its FORWARD games
    for status in ("suspects", "proven"):
        for ck, e in list(st[status].items()):
            if e["league"] not in fins or time.time() - t0 > budget_s * 0.6:
                continue
            rows, _, _ = evaluate(e["league"], e["cfg"])
            f = fwd_cell(ck, e, rows)
            e["fwd"], e["checked"] = f, now
            if f.get("n", 0) < FWD_N:
                continue
            bad = f.get("gain", 0) <= 0 if e["kind"] == "blend" else f.get("roi", 0) <= 0
            good = f.get("gain", 0) > 0 and f.get("z", 0) >= FWD_Z if e["kind"] == "blend" else f.get("z_edge", 0) >= FWD_Z
            if bad:
                e["why"] = "forward games lost" if status == "suspects" else "turned negative after being proven"
                e["killed"] = now
                st["killed"][ck] = st[status].pop(ck)
                (killed if status == "suspects" else demoted).append(ck)
            elif status == "suspects" and good:
                e["promoted"] = now
                st["proven"][ck] = st[status].pop(ck)
                promoted.append(ck)
            if ck in st["proven"]:
                e["shift"] = round(e["w"] * f["n"] / (f["n"] + SHRINK), 4) if e["kind"] == "blend" else shift_of(f)
    # -- config suspects: better than the best sim again on forward games?
    for key, e in list(st["cfg_suspects"].items()):
        lg = e["league"]
        if lg not in fins:
            continue
        var = evaluate(lg, key)[2]
        inc = evaluate(lg, st["best"][lg]["key"])[2]
        f = compare(var, inc, after=e["cutoff"]).get(0, {"n": 0})
        e["fwd"], e["checked"] = f, now
        if f["n"] < FWD_GAMES:
            continue
        if f["diff"] < 0 and f["z"] >= FWD_Z:
            st["best"][lg] = {"key": key, "since": now, "prev": st["best"][lg]["key"], "fwd": f}
            e["promoted"] = now
            st["cfg_suspects"].pop(key)
            cfg_prom.append(key)
        elif f["diff"] >= 0:
            e["killed"] = now
            st["cfg_killed"][key] = st["cfg_suspects"].pop(key)
            cfg_kill.append(key)
    for lg in fins:                                          # (a newly promoted best: refresh the results table)
        key = st["best"][lg]["key"]
        if st["results"][lg]["cfg"] != key:
            _, res, _ = evaluate(lg, key)
            st["results"][lg] = {"cfg": key, "games": len(fins[lg]), "markets": {mk: _summ_market(r) for mk, r in res.items()}}
    # -- NEW variants, round robin over the leagues, within the budget
    gens = {lg: candidates(lg, cfg_of(st["best"][lg]["key"])[1], seen) for lg in fins}
    tested = 0
    exhausted = False
    while gens and tested < batch:
        for lg in list(gens):
            if tested >= batch:
                break
            if time.time() - t0 + secs.get(lg, 1.0) * 1.2 > budget_s:
                gens.pop(lg)
                continue
            nxt = next(gens[lg], None)
            if nxt is None:
                gens.pop(lg)
                exhausted = True
                continue
            key, _ = nxt
            rows, res, sl = evaluate(lg, key)
            seen.add(_h(key))
            LAST_TESTED.append(key)
            tested += 1
            discover(lg, key, res)
            inc_key = st["best"][lg]["key"]
            split = min((r["split"] for r in res.values() if r.get("n", 0) >= 40), default=None)
            cmp_ = compare(sl, evaluate(lg, inc_key)[2], split=split)
            o, nw = cmp_.get(0, {}), cmp_.get(1, {})
            better = o.get("diff", 0) <= -MIN_GAIN and nw.get("diff", 0) <= -MIN_GAIN
            gain = -(o.get("diff", 0) + nw.get("diff", 0))
            mine = sorted((e.get("gain", 0.0), k) for k, e in st["cfg_suspects"].items() if e["league"] == lg)
            if better and len(mine) >= MAX_CFG_SUSPECTS and mine[0][0] < gain:
                out_ = st["cfg_suspects"].pop(mine[0][1])      # the weakest waiting suspect makes room
                out_.update(killed=now, why="crowded out by a stronger variant before its forward test")
                st["cfg_killed"][mine[0][1]] = out_
                if mine[0][1] in cfg_new:
                    cfg_new.remove(mine[0][1])
                mine = mine[1:]
            if better and len(mine) < MAX_CFG_SUSPECTS:
                st["cfg_suspects"][key] = {"league": lg, "cutoff": newest[lg], "found": now, "vs": inc_key,
                                           "disc": {"old": o, "new": nw}, "gain": round(gain, 5), "fwd": {}}
                cfg_new.append(key)
            elif o and nw:
                near_cfg.append((-(o["diff"] + nw["diff"]), key, {"old": o, "new": nw}))
        if not gens:
            break
    near.sort(key=lambda x: -x[0])
    near_cfg.sort(key=lambda x: -x[0])
    run_ = {"at": now, "tested_configs": len(LAST_TESTED), "cell_tests": tests, "expected_by_luck": round(tests * P_LUCK, 3),
            "suspects_found": len(found), "promoted": len(promoted), "killed": len(killed), "demoted": len(demoted),
            "cfg_suspects_found": len(cfg_new), "cfg_promoted": len(cfg_prom), "cfg_killed": len(cfg_kill),
            "secs": round(time.time() - t0, 1), "eval_secs": {k: round(v, 1) for k, v in secs.items()}}
    st["tested"] = st.get("tested", 0) + len(LAST_TESTED)
    st["cell_tests"] = st.get("cell_tests", 0) + tests
    st["runs"] = st.get("runs", 0) + 1
    st["closest"] = [{"key": k, "z": z, **{x: s.get(x) for x in ("n", "roi_old", "roi_new", "gain_new", "w") if x in s}}
                     for z, k, s in near[:10]] or st.get("closest", [])
    st["closest_cfg"] = [{"key": k, "gain": round(g, 5), **d} for g, k, d in near_cfg[:5]] or st.get("closest_cfg", [])
    st["log"] = [run_] + st.get("log", [])[:59]
    st["updated"] = now
    st["exhausted"] = exhausted
    _save(st, seen, path)
    res = {**run_, "tested_total": st["tested"], "suspects": sorted(st["suspects"]), "proven": sorted(st["proven"]),
           "new_suspects": found, "new_proven": promoted, "new_killed": killed + demoted,
           "cfg_new_suspects": cfg_new, "cfg_promoted": cfg_prom, "cfg_killed": cfg_kill,
           "best": {lg: b["key"] for lg, b in st["best"].items()}}
    if verbose:
        print(report(res, st))
    return res


def report(res, st):
    lines = [f"THE SIMULATOR: tried {res['tested_configs']} NEW sim configs ({res['tested_total']} ever) in {res['secs']}s"
             f" · {res['cell_tests']} cell tests (luck alone would give ~{res['expected_by_luck']} suspects)",
             f"   new suspects: {res['suspects_found']} · promoted to PROVEN: {res['promoted']} · killed: {res['killed']}"
             f" · proven demoted: {res['demoted']} · better-sim suspects: {res['cfg_suspects_found']}"
             f" (promoted {res['cfg_promoted']}, killed {res['cfg_killed']})",
             f"   now watching {len(st['suspects'])} suspects · {len(st['proven'])} proven · {len(st['killed'])} killed"]
    for lg, r in sorted(st.get("results", {}).items()):
        parts = []
        for mk in MARKETS:
            m = r["markets"].get(mk)
            if not m or m.get("n", 0) < 40:
                continue
            b = m["best_bet"]
            parts.append(f"{mk} LL sim {m['ll_sim_new']:.4f} / mkt {m['ll_mkt_new']:.4f} / blend {m['ll_blend_new']:.4f}"
                         f" (w {m['blend_w']:.2f}) · bets@{m['best_thr']} n={b.get('n', 0)} roi {b.get('roi', 0):+.3f}"
                         f" z {b.get('z_edge', 0):+.1f}")
        lines.append(f"   {lg}: " + " | ".join(parts))
    for k in res["new_suspects"]:
        lines.append("   NEW SUSPECT " + _brief(k, st["suspects"][k]))
    for k in res["new_proven"]:
        lines.append("   PROVEN " + _brief(k, st["proven"][k]))
    for k in res["new_killed"]:
        lines.append("   KILLED " + _brief(k, st["killed"][k]))
    for k in res["cfg_promoted"]:
        lines.append("   NEW BEST SIM " + k)
    for k in res["cfg_new_suspects"][:6]:
        e = st["cfg_suspects"].get(k, {})
        d = e.get("disc", {})
        lines.append(f"   better-sim suspect {k}: log loss {d.get('old', {}).get('diff', 0):+.4f} (older half)"
                     f" {d.get('new', {}).get('diff', 0):+.4f} (newer) vs the best - needs forward games")
    for c in st.get("closest", [])[:3]:
        lines.append(f"   closest miss: {c['key']} z={c['z']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- 4) today's slate
def _alt(M, T, line, tot, league):
    out = {}
    if line is not None:
        step = 1.0
        out["spreads"] = [[line + k * step, round(p_cover(M, line + k * step), 4)] for k in range(-3, 4) if k]
    if tot is not None:
        step = 1.0
        out["totals"] = [[tot + k * step, round(p_over(T, tot + k * step), 4)] for k in range(-3, 4) if k]
    return out


def today(games, path=PATH, out_path=None, sims=SIMS, leagues=LEAGUES, seed=7, verbose=True):
    """Simulate every upcoming game on the board with each league's best sim -> data/sports/sim_today.json."""
    t0 = time.time()
    st = _load(path)
    out_path = out_path or (TODAY_PATH if path == PATH else os.path.join(os.path.dirname(path), "sim_today.json"))
    need = {}
    for lg in leagues:
        b = (st.get("best") or {}).get(lg)
        need.setdefault(lg, []).append(b["key"] if b else cfg_key(lg, default_cfg(lg)))
    for e in (st.get("proven") or {}).values():
        if e["league"] in need and e["cfg"] not in need[e["league"]]:
            need[e["league"]].append(e["cfg"])
    out = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "sims": sims, "games": {}, "by_cfg": {}}
    for lg, keys in need.items():
        up = sorted((g for g in games.values() if g.get("league") == lg and g.get("status") == "pre"
                     and (g.get("stype") or "?") in sd.REAL), key=lambda g: (g["start"], g["id"]))
        if not up:
            continue
        fin = sm.finals(games, lg)
        for i, key in enumerate(keys):
            _, cfg = cfg_of(key)
            model, _ = walk(fin, lg, cfg)
            ex = out["by_cfg"].setdefault(key, {})
            if model.games < WARM:
                continue
            for g in up:
                t = sm._ts(g["start"])
                lines = _lines(g, lg)
                line = lines.get("spread", (None,))[0]
                tot = lines.get("total", (None,))[0]
                mu_h, mu_a, margin, total, _ = model.predict(g, t)
                M, T, _ = model.dists(g, mu_h, mu_a, margin, total)
                exact = {"ml": round(p_home_win(M), 4)}
                if line is not None:
                    exact["spread"], exact["line"] = round(p_cover(M, line), 4), line
                if tot is not None:
                    exact["total"], exact["tline"] = round(p_over(T, tot), 4), tot
                ex[g["id"]] = exact
                if i:
                    continue
                hs, as_ = simulate(model, g, sims, seed)
                mc = mc_prices(hs, as_, line, tot)
                row = {"league": lg, "start": g["start"], "home": g.get("home_name") or g["home"],
                       "away": g.get("away_name") or g["away"], "cfg": key, "known": model.ready(g),
                       "proj": {"home": mc["home"], "away": mc["away"], "margin": round(margin, 2), "total": round(total, 2)},
                       "ml": {"home": round(mc["ml"], 4), "away": round(1 - mc["ml"], 4),
                              "fair_home": fair_american(mc["ml"]), "fair_away": fair_american(1 - mc["ml"])},
                       "exact": exact, **_alt(M, T, line, tot, lg)}
                if "ml" in lines:
                    row["ml"]["market_home"] = round(lines["ml"][3], 4)
                if line is not None:
                    p = mc["spread"]
                    row["spread"] = {"line": line, "home": round(p, 4), "away": round(1 - p, 4),
                                     "fair_home": fair_american(p), "fair_away": fair_american(1 - p),
                                     "market_home": round(lines["spread"][3], 4)}
                if tot is not None:
                    p = mc["total"]
                    row["total"] = {"line": tot, "over": round(p, 4), "under": round(1 - p, 4),
                                    "fair_over": fair_american(p), "fair_under": fair_american(1 - p),
                                    "market_over": round(lines["total"][3], 4)}
                out["games"][g["id"]] = row
    out["secs"] = round(time.time() - t0, 1)
    d = os.path.dirname(out_path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out_path + ".tmp", "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    os.replace(out_path + ".tmp", out_path)
    if verbose:
        print(f"TODAY'S SIMS: {len(out['games'])} upcoming games x {sims} sims in {out['secs']}s -> {out_path}")
    return out


# ---------------------------------------------------------------- 5) hooks for the engine
def proven(st):
    """Every proven cell: [{key, league, market, kind, cfg, shift, fwd...}]."""
    return [{"key": k, **e} for k, e in sorted(((st or {}).get("proven") or {}).items())]


def _nudge(st, league, market, g, p, sim_key, fair):
    """p nudged toward the sim by the strongest proven cell for this league x market (else p unchanged)."""
    best = None
    for e in ((st or {}).get("proven") or {}).values():
        if e.get("league") != league or e.get("market") != market:
            continue
        sim = ((((st or {}).get("today") or {}).get("by_cfg") or {}).get(e.get("cfg")) or {}).get(g.get("id"))
        if not sim or sim.get(sim_key[0]) is None:
            continue
        if sim_key[1] and sim.get(sim_key[1]) != _num(g.get("spread_home" if market == "spread" else "total")):
            continue                                             # the line moved since the sim priced it
        s = sim[sim_key[0]]
        s = s if sim_key[2] else 1 - s
        m = fair if fair is not None else p
        gap = sm.logit(s) - sm.logit(p)
        if e.get("kind") == "blend":
            z = e.get("shift", 0.0) * gap
        else:
            thr = float(e["kind"].split(":")[1])
            if abs(s - m) < thr:
                continue
            z = math.copysign(min(abs(e.get("shift", 0.0)), abs(gap)), s - m)
        if best is None or abs(z) > abs(best):
            best = z
    return p if not best else sm.sigmoid(sm.logit(p) + best)


def adjust_side(st, league, g, side, p, market="ml"):
    """The win (market='ml') or cover (market='spread') chance of `side` ('home'/'away'), nudged toward the sim
    only when that league x market is proven."""
    home = side == "home"
    fair = None
    lines = _lines(g, league) if g else {}
    if market in lines:
        fair = lines[market][3] if home else 1 - lines[market][3]
    return _nudge(st, league, market, g or {}, p, (market, "line" if market == "spread" else None, home), fair)


def adjust_total(st, league, g, p_over):
    lines = _lines(g, league) if g else {}
    fair = lines["total"][3] if "total" in lines else None
    return _nudge(st, league, "total", g or {}, p_over, ("total", "tline", True), fair)


if __name__ == "__main__":
    gs = sd.load_games()
    run(gs)
    today(gs)
