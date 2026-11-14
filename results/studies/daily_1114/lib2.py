"""11/13 daily studies: one side-row table per league from the game files (every final for the state - records, the
last / next game, last season's meeting - priced finals for the bets, at ESPN's close at its own juice).
Every fact on a row is known BEFORE the game (the schedule's next game is published in advance - no result of it is
read). Train = the seasons through 2021, held out = 2022 / 2023 / 2024 / 2025 apart, now = 2026."""
import bisect
import math
import os
import pickle
import random
import statistics
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402,F401  (chdir to the repo root)
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402

TRAIN = (2000, 2021)
HELD = [2022, 2023, 2024, 2025, 2026]


def _t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


def rows(lg):
    """[side row] for every priced, finished regular-season game (both sides), sorted by start."""
    cache = os.path.join(lib.CACHE, f"_rows3_{lg}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    allg = sd.load_games(lg)
    fin = sm.finals(allg, lg)
    sched = defaultdict(list)          # team -> [start] of EVERY game on file (finals + scheduled), for the next game
    for g in allg.values():
        if g.get("league") != lg or (g.get("stype") or "?") not in sd.REAL:
            continue
        for s in ("home", "away"):
            sched[g[s]].append(g["start"])
    for v in sched.values():
        v.sort()
    hist = defaultdict(list)           # team -> [(start, opp, home, neutral, margin, won)] before now
    meet = defaultdict(list)           # frozenset pair -> [(season, start, home team, margin home)]
    out = []
    for g in fin:
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (TypeError, ValueError):
            continue
        season = lib.season(g["start"])
        mh, ma = lib.num(g.get("ml_home")), lib.num(g.get("ml_away"))
        priced = mh is not None and ma is not None and mh != 0 and ma != 0 and hs != as_
        neutral = str(g.get("neutral")) == "1"
        if priced:
            gg = {"hs": hs, "as": as_, "sp": lib.num(g.get("spread_home")), "spho": lib.num(g.get("spread_home_odds")),
                  "spao": lib.num(g.get("spread_away_odds"))}
            nvh = lib.nv(mh, ma)
            for side, team, opp, odds, won in (("home", g["home"], g["away"], mh, hs > as_),
                                                ("away", g["away"], g["home"], ma, as_ > hs)):
                h = hist[team]
                ho = hist[opp]
                sea_h = [x for x in h if lib.season(x[0]) == season]
                sea_o = [x for x in ho if lib.season(x[0]) == season]
                prev = h[-1] if h else None
                oprev = ho[-1] if ho else None
                nx = sched[team]
                i = bisect.bisect_right(nx, g["start"])
                nxt = nx[i] if i < len(nx) else None
                onx = sched[opp]
                j = bisect.bisect_right(onx, g["start"])
                onxt = onx[j] if j < len(onx) else None
                last_meet = [m for m in meet[frozenset((team, opp))] if m[0] == season - 1]
                lm = None
                if last_meet:
                    m = last_meet[-1]
                    lm = m[3] if m[2] == team else -m[3]          # this team's margin in last season's last meeting
                sp = gg["sp"]
                line = None if sp is None else (sp if side == "home" else -sp)
                out.append({
                    "id": g["id"], "start": g["start"], "season": season, "side": side, "team": team, "opp": opp,
                    "home": side == "home", "neutral": neutral, "odds": odds, "won": won,
                    "p_nv": nvh if side == "home" else 1 - nvh, "line": line,
                    "ats": lib.ats(gg, side), "total": lib.num(g.get("total")),
                    "w": sum(1 for x in sea_h if x[5]), "l": sum(1 for x in sea_h if not x[5]),
                    "ow": sum(1 for x in sea_o if x[5]), "ol": sum(1 for x in sea_o if not x[5]),
                    "prev_gap_h": (_t(g["start"]) - _t(prev[0])).total_seconds() / 3600 if prev and lib.season(prev[0]) == season else None,
                    "prev_margin": prev[4] if prev and lib.season(prev[0]) == season else None,
                    "prev_home": prev[2] if prev else None,
                    "prev_pts": prev[6] if prev and lib.season(prev[0]) == season else None,
                    "prev_opp": prev[1] if prev and lib.season(prev[0]) == season else None,
                    "oprev_gap_h": (_t(g["start"]) - _t(oprev[0])).total_seconds() / 3600 if oprev and lib.season(oprev[0]) == season else None,
                    "oprev_margin": oprev[4] if oprev and lib.season(oprev[0]) == season else None,
                    "next_gap_h": (_t(nxt) - _t(g["start"])).total_seconds() / 3600 if nxt else None,
                    "onext_gap_h": (_t(onxt) - _t(g["start"])).total_seconds() / 3600 if onxt else None,
                    "last_season_meet": lm, "stype": str(g.get("stype") or "2"),
                    "elev": lib.num(g.get("elev")),
                })
        for side, team, opp, mg in (("home", g["home"], g["away"], hs - as_), ("away", g["away"], g["home"], as_ - hs)):
            hist[team].append((g["start"], opp, side == "home", neutral, mg, mg > 0, hs if side == "home" else as_))
        meet[frozenset((g["home"], g["away"]))].append((season, g["start"], g["home"], hs - as_))
    out.sort(key=lambda r: r["start"])
    pickle.dump(out, open(cache, "wb"))
    return out


def ml_profit(r):
    return lib.profit(r["won"], lib.dec(r["odds"]))


def cell(name, rs, kind="ml", say=print):
    """One line: ALL / TRAIN (seasons up) / each held season / HELD."""
    bets = [(r["season"], ml_profit(r) if kind == "ml" else r["ats"]) for r in rs
            if (kind == "ml" or r["ats"] is not None)]
    res = lib.summ(bets, TRAIN, HELD)
    say(lib.fmt(name, res))
    return res


def placebo(rs, pool, kind="ml", n=2000, seed=7):
    """How often a random set of the same size from `pool` (the cell's own price band) does at least as well."""
    if not rs:
        return None
    f = (lambda r: ml_profit(r)) if kind == "ml" else (lambda r: r["ats"])
    rs = [r for r in rs if f(r) is not None]
    pool = [r for r in pool if f(r) is not None]
    if not rs or len(pool) < len(rs):
        return None
    got = sum(f(r) for r in rs) / len(rs)
    rnd = random.Random(seed)
    vals = [f(r) for r in pool]
    k = len(rs)
    hit = sum(1 for _ in range(n) if sum(rnd.sample(vals, k)) / k >= got)
    return hit


def winpct(w, l):
    return w / (w + l) if w + l else None
