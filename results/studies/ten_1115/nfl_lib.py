"""11/15 ten studies - NFL: nflverse's public schedule file (the 11/11 download in ~/.cache/d503_spreads2_1111/dl,
closing moneylines 2006-26, rest days, the division flag, the starting QBs) -> one row a SIDE, with what was known
before kickoff (record, last game, earlier meeting this season). Train 2006-16 / held out 2017-26 (each season apart)."""
import csv
import math
import os
import random
from collections import defaultdict

P = os.path.join(os.path.expanduser("~"), ".cache", "d503_spreads2_1111", "dl", "games.csv")
TRAIN = (2006, 2016)
HELD = list(range(2017, 2027))


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def sides(reg_only=True):
    gs = []
    for r in csv.DictReader(open(P)):
        hs, as_ = _f(r["home_score"]), _f(r["away_score"])
        if hs is None or as_ is None:
            continue
        gs.append(r)
    gs.sort(key=lambda r: (r["gameday"], r["game_id"]))
    hist = defaultdict(list)       # (season, team) -> [(week, opp, margin, home, date, was_dog, odds, div, qb)]
    out = []
    for r in gs:
        season, wk = int(r["season"]), int(r["week"])
        hs, as_ = float(r["home_score"]), float(r["away_score"])
        hml, aml = _f(r["home_moneyline"]), _f(r["away_moneyline"])
        reg = r["game_type"] == "REG"
        sl = _f(r["spread_line"])
        for side, team, opp, odds, oo, m, rest, orest, qb, oqb in (
                ("home", r["home_team"], r["away_team"], hml, aml, hs - as_, _f(r["home_rest"]), _f(r["away_rest"]), r["home_qb_id"], r["away_qb_id"]),
                ("away", r["away_team"], r["home_team"], aml, hml, as_ - hs, _f(r["away_rest"]), _f(r["home_rest"]), r["away_qb_id"], r["home_qb_id"])):
            h, ho = hist[(season, team)], hist[(season, opp)]
            if reg and odds and oo and m != 0:
                pa, pb = 1 / dec(odds), 1 / dec(oo)
                meet = [x for x in h if x[1] == opp]
                out.append({
                    "gid": r["game_id"], "season": season, "week": wk, "date": r["gameday"], "side": side, "team": team, "opp": opp,
                    "home": side == "home", "neutral": r["location"] == "Neutral", "odds": odds, "won": m > 0,
                    "prof": (dec(odds) - 1) if m > 0 else -1.0, "p_nv": pa / (pa + pb), "div": r["div_game"] == "1",
                    "rest": rest, "orest": orest, "wd": r["weekday"], "qb": qb, "oqb": oqb,
                    "line": None if sl is None else (-sl if side == "home" else sl),
                    "w": sum(1 for x in h if x[2] > 0), "l": sum(1 for x in h if x[2] < 0),
                    "ow": sum(1 for x in ho if x[2] > 0), "ol": sum(1 for x in ho if x[2] < 0),
                    "prev_m": h[-1][2] if h else None, "oprev_m": ho[-1][2] if ho else None,
                    "prev_dog": h[-1][5] if h else None, "prev_odds": h[-1][6] if h else None,
                    "prev_home": h[-1][3] if h else None, "prev_div": h[-1][7] if h else None,
                    "prev_qb": h[-1][8] if h else None, "oprev_qb": ho[-1][8] if ho else None,
                    "meet_m": meet[-1][2] if meet else None, "meet_home": meet[-1][3] if meet else None,
                    "streak": _streak(h), "ostreak": _streak(ho),
                    "margin": m, "total": _f(r["total_line"]),
                })
        for side, team, opp, odds, m, qb in (("home", r["home_team"], r["away_team"], hml, hs - as_, r["home_qb_id"]),
                                             ("away", r["away_team"], r["home_team"], aml, as_ - hs, r["away_qb_id"])):
            if reg:
                hist[(season, team)].append((wk, opp, m, side == "home", r["gameday"], (odds or 0) >= 100, odds, r["div_game"] == "1", qb))
    return out


def _streak(h):
    s = 0
    for x in reversed(h):
        if x[2] > 0:
            if s < 0:
                break
            s += 1
        elif x[2] < 0:
            if s > 0:
                break
            s -= 1
        else:
            break
    return s


def dog(r, lo=100, hi=350):
    return lo <= r["odds"] <= hi


def fav(r, lo=-150, hi=-101):
    return lo <= r["odds"] <= hi


def stat(ps):
    n = len(ps)
    if not n:
        return None
    m = sum(ps) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in ps) / (n - 1)) if n > 1 else 0
    return n, sum(1 for x in ps if x > 0), m, (m / (sd / math.sqrt(n)) if sd else 0)


def cell(name, rs, key="prof", say=print, train=TRAIN, held=HELD):
    rs = [r for r in rs if r.get(key) is not None]
    a = stat([r[key] for r in rs])
    if not a:
        say(f"  {name:58s} n 0")
        return None
    tr = [r for r in rs if train[0] <= r["season"] <= train[1]]
    he = [r for r in rs if r["season"] in held]
    t, h = stat([r[key] for r in tr]), stat([r[key] for r in he])
    by = defaultdict(list)
    for r in rs:
        by[r["season"]].append(r[key])
    upt = sum(1 for s, v in by.items() if train[0] <= s <= train[1] and sum(v) > 0)
    nt = sum(1 for s in by if train[0] <= s <= train[1])
    uph = sum(1 for s, v in by.items() if s in held and sum(v) > 0)
    nh = sum(1 for s in by if s in held)
    f = lambda x: f"{x[2]*100:+6.1f}% ({x[0]:4d})" if x else "    -         "
    say(f"  {name:58s} n {a[0]:5d} {a[1]:4d}-{a[0]-a[1]:<4d} {a[2]*100:+6.1f}% z {a[3]:+5.2f} | train {f(t)} up {upt}/{nt} | held {f(h)} up {uph}/{nh}")
    return dict(n=a[0], roi=a[2], z=a[3], train=t, held=h, upt=upt, nt=nt, uph=uph, nh=nh)


def placebo(rs, pool, key="prof", n=2000, seed=7, fade=False):
    rs = [r[key] for r in rs if r.get(key) is not None]
    pool = [r[key] for r in pool if r.get(key) is not None]
    if not rs or len(pool) < len(rs):
        return None
    got = sum(rs) / len(rs)
    rnd = random.Random(seed)
    k = len(rs)
    if fade:
        return sum(1 for _ in range(n) if sum(rnd.sample(pool, k)) / k <= got)
    return sum(1 for _ in range(n) if sum(rnd.sample(pool, k)) / k >= got)
