"""SITUATIONAL SPOTS: does the schedule / last-game situation a team is in beat the closing price?

The old betting "angles" - revenge games, teams off a blowout, long road trips, the 3rd game in 4 nights, road
favorites, a big favorite off a loss - checked against every real final in all six sports (nfl, ncaaf, nba, ncaab,
mlb, nhl). For every game and each side we work out which spots the team is in using ONLY its earlier games (a game
counts as earlier only if it started 6+ hours before this one - no peeking), then ask two questions:

  A) MONEYLINE: did teams in the spot win more often than the no-juice closing price said? (won - fair chance)
  B) SPREAD (nfl, ncaaf, nba, ncaab): did they cover more than half the time? (pushes skipped)

Each spot is graded two ways: backing the team in the spot, and FADING it (betting its opponent). Games where BOTH
teams are in the same spot are left out (they cancel). The games are split by date into an older and a newer half.
A spot is PROVEN only if, with 150+ games in EACH half: the edge points the same way in both halves, a $100 bet at
the real closing price (juice included) made money in both halves, and the pooled z-score clears the Bonferroni bar
for how many spots we tested (family-wise 5%). Spots that clear the usual 1.96 bar but not the Bonferroni one are
listed as CANDIDATES only - with ~500 tests, about a dozen would clear 1.96 by pure luck. A "trap" is a spot whose
FADE is proven (the team in the spot is surely overpriced). To size the luck, the whole grading is re-run on fake
results drawn from the fair price itself (no edge anywhere) and we report how many spots passed there.

Saved to data/sports/spots.json. adjust() nudges a side's win (or cover) chance by the proven spots only (fit on all
the data, shrunk by n/(n+400)); flags()/index() give the spots for an upcoming game from the games before it."""
import bisect
import json
import math
import os
import random
from datetime import datetime, timezone

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "spots.json")
LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "mlb", "nhl")
SPREAD_LEAGUES = sm.SPREAD_LEAGUES
NIGHTLY = ("nba", "nhl", "ncaab")            # sports where back-to-backs and 3-in-4s happen
FOOTBALL = ("nfl", "ncaaf")
EARLIER = 6 * 3600                            # a game is "earlier" only if it started 6+ hours before
GAP_DAYS = 75                                 # a layoff this long starts a new season (lockouts, covid restarts)
MIN_N = 150                                   # games needed in EACH half
Z_NOMINAL = 1.96
ALPHA = 0.05                                  # family-wise error for the Bonferroni bar
SHRINK = 400
MAX_SHIFT = 0.5                               # the most all spots together can move a side (logit)
SIMS = 20                                     # null re-runs (fake results drawn from the fair price)

SPOTS = {
    "off_blowout_loss": "lost its last game by a blowout",
    "off_blowout_win": "won its last game by a blowout",
    "off_upset_loss": "lost its last game as a 70%+ favorite",
    "off_upset_win": "won its last game as a 30%-or-less dog",
    "revenge": "lost the last meeting with this opponent (this season or last)",
    "win_streak4": "won its last 4+ (this season)",
    "lose_streak4": "lost its last 4+ (this season)",
    "3in4": "3rd game in 4 nights (nba/nhl/ncaab)",
    "b2b": "played yesterday (nba/nhl/ncaab)",
    "b2b_road": "played yesterday and is on the road today (nba/nhl/ncaab)",
    "rest_edge": "rested while the opponent played yesterday (nba/nhl/ncaab)",
    "road_trip": "3rd+ straight road game (mlb: 7th+)",
    "home_after_trip": "first home game after 3+ road games (mlb: 6+)",
    "early_season": "one of the team's first 3 games of the season (mlb: first 10)",
    "off_bye": "off a bye - 10+ days since its last game, mid-season (nfl/ncaaf)",
    "short_week": "5 or fewer days since its last game (nfl)",
    "road_fav": "road favorite",
    "home_dog": "home underdog",
    "big_fav_off_loss": "a 75%+ favorite coming off a loss",
}


def _ts(iso):
    try:
        return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0.0


def season(league, iso):
    y, m = int(iso[:4]), int(iso[5:7])
    return y if league == "mlb" or m >= 8 else y - 1


def _day(ts):
    return int((ts - 8 * 3600) // 86400)          # ~the US calendar day (a 00:30Z tip is the evening before)


def _loc(g, side):
    if str(g.get("neutral")) == "1":
        return "n"
    return "h" if side == "home" else "a"


def _p_side(g, side):
    p = sm.market_p(g)
    return None if p is None else (p if side == "home" else 1 - p)


class Index:
    """Each team's finished games in time order (and each pair's meetings), built once per call site."""

    def __init__(self, games):
        self.teams, self.ts, self.pairs, self.pair_ts = {}, {}, {}, {}
        for lg in LEAGUES:
            for g in sm.finals(games, lg):
                try:
                    hs, as_ = int(g["home_score"]), int(g["away_score"])
                except (TypeError, ValueError):
                    continue
                t = _ts(g["start"])
                sn = season(lg, g["start"])
                for side, other, m in (("home", "away", hs - as_), ("away", "home", as_ - hs)):
                    rec = (t, _day(t), _loc(g, side), m, _p_side(g, side), g[other], sn)
                    self.teams.setdefault((lg, g[side]), []).append(rec)
                    self.pairs.setdefault((lg, g[side], g[other]), []).append((t, m, sn))
        for d, td in ((self.teams, self.ts), (self.pairs, self.pair_ts)):
            for k, v in d.items():
                v.sort(key=lambda r: r[0])
                td[k] = [r[0] for r in v]

    def prior(self, league, team, t):
        """(records, how many) of the team's games that started 6+ hours before t."""
        k = (league, team)
        return self.teams.get(k, []), bisect.bisect_right(self.ts.get(k, []), t - EARLIER)

    def last_meeting(self, league, team, opp, t):
        k = (league, team, opp)
        i = bisect.bisect_right(self.pair_ts.get(k, []), t - EARLIER)
        return self.pairs[k][i - 1] if i else None


def index(games):
    return Index(games)


def _team_flags(idx, league, g, side):
    """The spots one team is in, from its earlier games only (the rest_edge spot needs both teams: see flags)."""
    t = _ts(g["start"])
    day, loc, sn = _day(t), _loc(g, side), season(league, g["start"])
    recs, n = idx.prior(league, g[side], t)
    out = set()
    run = 0                                       # earlier games in this season (no 75-day layoff in between)
    prev = t
    early_n = 10 if league == "mlb" else 3
    for i in range(n - 1, -1, -1):
        r = recs[i]
        if r[6] != sn or prev - r[0] > GAP_DAYS * 86400:
            break
        run += 1
        prev = r[0]
        if run >= 12:
            break
    if run < early_n:
        out.add("early_season")
    p = _p_side(g, side)
    if p is not None and loc == "a" and p > 0.5:
        out.add("road_fav")
    if p is not None and loc == "h" and p < 0.5:
        out.add("home_dog")
    if run:
        last = recs[n - 1]
        big = sm.BIG_WIN[league]
        if last[3] <= -big:
            out.add("off_blowout_loss")
        if last[3] >= big:
            out.add("off_blowout_win")
        if last[3] < 0 and last[4] is not None and last[4] >= 0.70:
            out.add("off_upset_loss")
        if last[3] > 0 and last[4] is not None and last[4] <= 0.30:
            out.add("off_upset_win")
        if last[3] < 0 and p is not None and p >= 0.75:
            out.add("big_fav_off_loss")
        for s, name in ((1, "win_streak4"), (-1, "lose_streak4")):
            k = 0
            for i in range(n - 1, max(-1, n - 1 - min(run, 4)), -1):
                if recs[i][3] * s > 0:
                    k += 1
                else:
                    break
            if k >= 4:
                out.add(name)
        rest = (t - last[0]) / 86400
        if league in NIGHTLY:
            if last[1] == day - 1:
                out.add("b2b")
                if loc == "a":
                    out.add("b2b_road")
            if run >= 2 and recs[n - 2][1] >= day - 3:
                out.add("3in4")
        if league in FOOTBALL and rest >= 10:
            out.add("off_bye")
        if league == "nfl" and rest <= 5:
            out.add("short_week")
        trip = 7 if league == "mlb" else 3
        k = 0
        for i in range(n - 1, n - 1 - min(run, trip), -1):
            if recs[i][2] == "a":
                k += 1
            else:
                break
        if loc == "a" and k >= trip - 1:
            out.add("road_trip")
        if loc == "h" and k >= trip - (1 if league == "mlb" else 0):
            out.add("home_after_trip")
    lm = idx.last_meeting(league, g[side], g["home" if side == "away" else "away"], t)
    if lm and lm[1] < 0 and 0 <= sn - lm[2] <= 1:
        out.add("revenge")
    return out


def _both(idx, league, g):
    fh, fa = _team_flags(idx, league, g, "home"), _team_flags(idx, league, g, "away")
    if "b2b" in fa and "b2b" not in fh:
        fh.add("rest_edge")
    if "b2b" in fh and "b2b" not in fa:
        fa.add("rest_edge")
    return fh, fa


def flags(idx, g, side):
    """Sorted spot names for one side of a game (upcoming or not), from games that started 6+ hours earlier.
    idx is index(games) - build it once and reuse it; a plain games dict also works (slower: indexes every call)."""
    if not isinstance(idx, Index):
        idx = Index(idx)
    fh, fa = _both(idx, g["league"], g)
    return sorted(fh if side == "home" else fa)


# ---------------------------------------------------------------- grading

def _payout(odds):
    """Profit on a $100 winner at American odds."""
    return odds if odds > 0 else 10000 / -odds


def _game_row(g):
    """(p home, ml home, ml away, home won 1/0 or None, spread home, odds h, odds a, home covered 1/0 or None)."""
    hs, as_ = int(g["home_score"]), int(g["away_score"])
    p = sm.market_p(g)
    won = None if hs == as_ else int(hs > as_)
    line = sm._num(g.get("spread_home")) if g["league"] in SPREAD_LEAGUES else None
    cov = None
    if line is not None and hs - as_ + line != 0:
        cov = int(hs - as_ + line > 0)
    oh, oa = sm._int(g.get("spread_home_odds")) or -110, sm._int(g.get("spread_away_odds")) or -110
    return (p, sm._int(g.get("ml_home")), sm._int(g.get("ml_away")), won, line, oh, oa, cov)


def rows(games, league, idx=None):
    """[(start, game row, home flags, away flags)] for every real final, oldest first."""
    idx = idx or Index(games)
    out = []
    for g in sm.finals(games, league):
        try:
            gr = _game_row(g)
        except (TypeError, ValueError):
            continue
        fh, fa = _both(idx, league, g)
        out.append((g["start"], gr, fh, fa))
    return out


def _ml_ok(gr):
    return gr[3] is not None and gr[0] is not None and gr[1] is not None and gr[2] is not None


def _cells(rs):
    """{(spot, 'team'|'fade'): [(game i, bet on home?)]} - games where both sides share a spot are skipped."""
    cells = {}
    for i, (_, _, fh, fa) in enumerate(rs):
        for s in fh ^ fa:
            home_in = s in fh
            cells.setdefault((s, "team"), []).append((i, home_in))
            cells.setdefault((s, "fade"), []).append((i, not home_in))
    return cells


def _grade(members, rs, half_i, outcome, won_h, cov_h):
    """Per half [n, sum resid, sum var, sum profit, hits] + pooled numbers."""
    h = [[0, 0.0, 0.0, 0.0, 0], [0, 0.0, 0.0, 0.0, 0]]
    for i, home in members:
        gr = rs[i][1]
        if outcome == "ml":
            y, p = won_h[i], gr[0]
            if y is None or not _ml_ok(gr):
                continue
            odds = gr[1] if home else gr[2]
            fair = p if home else 1 - p
            y = y if home else 1 - y
        else:
            y = cov_h[i]
            if y is None:
                continue
            odds = gr[5] if home else gr[6]
            fair = 0.5
            y = y if home else 1 - y
        c = h[1 if i >= half_i else 0]
        c[0] += 1
        c[1] += y - fair
        c[2] += fair * (1 - fair)
        c[3] += _payout(odds) if y else -100
        c[4] += y
    return h


def _summ(h, outcome):
    (na, ra, va, pa, wa), (nb, rb, vb, pb, wb) = h
    z = (ra + rb) / math.sqrt(va + vb) if va + vb > 0 else 0.0
    return {"n_old": na, "n_new": nb, "edge_old": round(ra / na, 4) if na else 0.0,
            "edge_new": round(rb / nb, 4) if nb else 0.0, "hit_old": round(wa / na, 4) if na else 0.0,
            "hit_new": round(wb / nb, 4) if nb else 0.0, "profit_old": round(pa / na, 2) if na else 0.0,
            "profit_new": round(pb / nb, 2) if nb else 0.0, "z": round(z, 2)}


def _passes(c, zbar):
    return (c["n_old"] >= MIN_N and c["n_new"] >= MIN_N and c["edge_old"] > 0 and c["edge_new"] > 0
            and c["profit_old"] > 0 and c["profit_new"] > 0 and c["z"] >= zbar)


def _z_bonf(tests):
    """One-sided z for a family-wise ALPHA over this many tests."""
    q = ALPHA / max(1, tests)
    lo, hi = 0.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if 1 - sm.phi(mid) > q:
            lo = mid
        else:
            hi = mid
    return hi


def _shift(members, rs, outcome, sign):
    """Logit shift for the TEAM in the spot, fit on all games, shrunk by n/(n+SHRINK)."""
    n = w = 0
    fs = 0.0
    for i, home in members:
        gr = rs[i][1]
        y = gr[3] if outcome == "ml" else gr[7]
        if y is None or (outcome == "ml" and not _ml_ok(gr)):
            continue
        y = y if home else 1 - y
        n += 1
        w += y
        fs += (gr[0] if home else 1 - gr[0]) if outcome == "ml" else 0.5
    if not n:
        return 0.0
    s = sm.logit((w + 1) / (n + 2)) - sm.logit(fs / n)
    return round(sign * s * n / (n + SHRINK), 4)


def study(games, path=PATH, sims=SIMS, seed=1):
    idx = Index(games)
    per, tested = {}, 0
    for lg in LEAGUES:
        rs = rows(games, lg, idx)
        if not rs:
            continue
        won_h, cov_h = [r[1][3] for r in rs], [r[1][7] for r in rs]
        half_i = {}                                 # older half / newer half by date, among games with that price
        for o in ("ml", "spread"):
            have = [i for i, r in enumerate(rs) if (_ml_ok(r[1]) if o == "ml" else r[1][7] is not None)]
            half_i[o] = have[len(have) // 2] if have else 0
        members = _cells(rs)
        outs = ("ml", "spread") if lg in SPREAD_LEAGUES else ("ml",)
        cells, seen = {}, {}
        for (s, sk), mem in sorted(members.items()):
            for o in outs:
                c = _summ(_grade(mem, rs, half_i[o], o, won_h, cov_h), o)
                c["tested"] = c["n_old"] >= MIN_N and c["n_new"] >= MIN_N
                sig = (o, tuple(mem))               # the very same bets under another name (b2b fade = rest_edge
                if sig in seen:                     #   team, home_dog fade = road_fav team) is not a new test
                    c["same_as"] = seen[sig]
                else:
                    seen[sig] = f"{s}|{o}|{sk}"
                    tested += c["tested"]
                cells[f"{s}|{o}|{sk}"] = c
        per[lg] = {"games": len(rs), "cut": {o: rs[i][0][:10] for o, i in half_i.items() if o in outs},
                   "cells": cells, "rs": rs, "members": members, "outs": outs, "half_i": half_i}
    zb = max(Z_NOMINAL, _z_bonf(tested))
    # the null: fake results drawn from the fair price (spreads: a coin flip) - how many spots pass by luck?
    rnd = random.Random(seed)
    null_nom, null_bonf = [], []
    for _ in range(sims):
        a = b = 0
        for lg, v in per.items():
            rs = v["rs"]
            won_h = [None if r[1][3] is None or r[1][0] is None else int(rnd.random() < r[1][0]) for r in rs]
            cov_h = [None if r[1][7] is None else int(rnd.random() < 0.5) for r in rs]
            for (s, sk), mem in v["members"].items():
                for o in v["outs"]:
                    cc = v["cells"][f"{s}|{o}|{sk}"]
                    if not cc["tested"] or "same_as" in cc:
                        continue
                    c = _summ(_grade(mem, rs, v["half_i"][o], o, won_h, cov_h), o)
                    a += _passes(c, Z_NOMINAL)
                    b += _passes(c, zb)
        null_nom.append(a)
        null_bonf.append(b)
    res = {"_meta": {"tested": tested, "z_bonferroni": round(zb, 3), "z_nominal": Z_NOMINAL,
                     "expected_luck_nominal_max": round(0.025 * tested, 1),
                     "null_sims": sims,
                     "null_nominal_avg": round(sum(null_nom) / sims, 2) if sims else None,
                     "null_bonferroni_avg": round(sum(null_bonf) / sims, 2) if sims else None,
                     "min_n_each_half": MIN_N, "spots": SPOTS}}
    for lg, v in per.items():
        proven, traps, cands = [], [], []
        shifts = {"ml": {}, "spread": {}}
        for k, c in v["cells"].items():
            c["candidate"] = _passes(c, Z_NOMINAL)
            c["proven"] = _passes(c, zb)
            if c["candidate"] and not c["proven"]:
                cands.append(k)
            if c["proven"]:
                s, o, sk = k.split("|")
                (traps if sk == "fade" else proven).append(f"{s}|{o}")
                if "same_as" in c:                    # the same bets under another name: shift counted once
                    continue
                shifts[o][s] = shifts[o].get(s, 0.0) + _shift(v["members"][(s, sk)], v["rs"], o, 1 if sk == "team" else -1)
        res[lg] = {"games": v["games"], "cut": v["cut"], "cells": v["cells"], "proven": sorted(proven),
                   "traps": sorted(traps), "candidates": sorted(cands), "shifts": shifts}
    with open(path + ".tmp", "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)
    return res


def load():
    try:
        with open(PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def adjust(st, league, flags_side, p_side, flags_opp=(), outcome="ml"):
    """A side's win chance (outcome='ml') or cover chance ('spread') moved by the PROVEN spots only: up for a proven
    spot the side is in, down for a trap it is in, and the other way round for the opponent's spots (flags_opp).
    Pass flags_opp too: a spot that is the same bets as another (home_dog fade = road_fav) is shifted under one name."""
    sh = (((st or {}).get(league) or {}).get("shifts") or {}).get(outcome) or {}
    if not sh or p_side is None:
        return p_side
    z = sum(sh.get(s, 0.0) for s in flags_side) - sum(sh.get(s, 0.0) for s in flags_opp or ())
    if not z:
        return p_side
    return sm.sigmoid(sm.logit(p_side) + max(-MAX_SHIFT, min(MAX_SHIFT, z)))


def summary(st):
    m = st.get("_meta") or {}
    lines = [f"situational spots: {m.get('tested')} spot tests with {MIN_N}+ games in each half; Bonferroni bar "
             f"z >= {m.get('z_bonferroni')} (a 1.96 bar would pass ~{m.get('null_nominal_avg')} by pure luck on "
             f"fake no-edge results, at most ~{m.get('expected_luck_nominal_max')}; the Bonferroni bar "
             f"~{m.get('null_bonferroni_avg')})"]
    hdr = f"{'league':6} {'spot':17} {'bet':6} {'side':4} {'hit old':>7} {'hit new':>7} {'edge old':>8} {'edge new':>8} " \
          f"{'$ old':>6} {'$ new':>6} {'n old':>6} {'n new':>6} {'z':>5}  verdict"
    lines.append(hdr)
    for lg in LEAGUES:
        v = st.get(lg)
        if not v:
            continue
        for k, c in sorted(v["cells"].items(), key=lambda kv: -kv[1]["z"]):
            if not c.get("candidate"):
                continue
            s, o, sk = k.split("|")
            verdict = ("PROVEN" if sk == "team" else "TRAP (fade proven)") if c["proven"] else "candidate (1.96 only)"
            if c.get("same_as"):
                verdict += f" = same bets as {c['same_as']}"
            lines.append(f"{lg:6} {s:17} {o:6} {sk:4} {c['hit_old']:7.3f} {c['hit_new']:7.3f} {c['edge_old']:+8.4f} "
                         f"{c['edge_new']:+8.4f} {c['profit_old']:+6.1f} {c['profit_new']:+6.1f} {c['n_old']:6d} "
                         f"{c['n_new']:6d} {c['z']:5.2f}  {verdict}")
    for lg in LEAGUES:
        v = st.get(lg)
        if v:
            lines.append(f"{lg}: {v['games']} games (halves split {v['cut']}) proven {v['proven']} traps {v['traps']}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary(study(sd.load_games())))
