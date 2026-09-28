"""THE BIG UNDERDOG + FAVORITE STUDY. Two questions, every sport:

1) PRICE CHECK: when the books say a team wins X% of the time, does it really? Every real final, bucketed by the
   no-juice home win chance. Learned on the older half, tested on the newer half it never saw. A sport's correction
   is kept only if it beats the plain book price on the unseen games - then the engine's read on every favorite and
   every dog in that sport is shifted by it (this is the part that changes what the engine KNOWS).
2) DOG SPOTS: where do plus-money underdogs actually beat their price?

Every real final with a closing moneyline, every sport. For each spot - sport x price range x home/road x
(the line moved toward the dog / away) x (a back-to-back / rest edge) - what a $100 bet on every dog in that spot
would have made (the real price, juice included). A spot is PROVEN only if it made money on the older half of the
games AND again on the newer half it never saw (so it's not luck), with enough games both times.
Saved to data/sports/dogs.json - the engine uses the proven spots for the Dog of the Day."""
import json
import math
import os
from datetime import datetime

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "dogs.json")
LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "mlb", "nhl")
BUCKETS = ((100, 139), (140, 179), (180, 239), (240, 399))
MIN_N = 60


def bucket(o):
    for lo, hi in BUCKETS:
        if lo <= o <= hi:
            return f"+{lo}-{hi}"
    return None


def spots(games, league):
    """[(start, spot keys, profit on $100)] for every underdog with a closing price."""
    fin = sorted(sm.finals(games, league), key=lambda g: g["start"])
    last = {}
    out = []
    for g in fin:
        t = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M")
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            continue
        rest = {s: ((t - last[g[s]]).total_seconds() / 86400 if g[s] in last else 7.0) for s in ("home", "away")}
        last[g["home"]], last[g["away"]] = t, t
        for side, other in (("home", "away"), ("away", "home")):
            o = sm._int(g.get(f"ml_{side}"))
            b = bucket(o) if o else None
            if not b or hs == as_:
                continue
            won = (hs > as_) if side == "home" else (as_ > hs)
            profit = o if won else -100
            fair = sm.market_p(g)
            fair = fair if side == "home" else 1 - fair
            op = sm._int(g.get(f"ml_{side}_open"))
            move = "any" if op is None else ("toward dog" if o < op else "away from dog" if o > op else "no move")
            r = "rest edge" if rest[other] <= 1.2 < rest[side] else "on b2b" if rest[side] <= 1.2 < rest[other] else "even rest"
            keys = [f"{b}|all", f"{b}|{side}", f"all|{side}", f"all|{r}", f"{b}|{side}|{r}", "all|all"]
            if op is not None and op != o:        # a real line move only (half the history has no opening line)
                keys += [f"all|{move}", f"{b}|{move}"]
            out.append((g["start"], keys, (profit, won - fair)))
    return out


Z_PROVEN = 1.64                 # ...and the profit has to be big enough that luck can't explain it (95% sure)
Z_TRAP = 1.64                   # a spot whose dogs win less than even the FAIR (no-juice) price says, that surely,
                                #   is a TRAP: the books still overprice them - the engine never takes a dog there
EDGES = (0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0)
SHRINK = 400                    # a bucket's correction counts fully only with plenty of games behind it


def zscore(rows):
    """How sure a spot's profit/loss isn't luck (0 = pure noise, 1.64 = 95% sure)."""
    n = len(rows)
    if n < 2:
        return 0.0
    m = sum(rows) / n
    sd_ = (sum((x - m) ** 2 for x in rows) / (n - 1)) ** 0.5
    return m / (sd_ / n ** 0.5) if sd_ else 0.0


def _pb(p):
    for i in range(len(EDGES) - 1):
        if p < EDGES[i + 1]:
            return i
    return len(EDGES) - 2


def _ll(rows, shifts):
    s = 0.0
    for p, y in rows:
        q = sm.sigmoid(sm.logit(p) + shifts.get(str(_pb(p)), 0.0))
        s -= math.log(q if y else 1 - q)
    return s / max(1, len(rows))


def price_check(games, league):
    """Do favorites/dogs win as often as their price says? Shifts learned on old games, tested on new ones."""
    rows = []
    for g in sm.finals(games, league):
        p = sm.market_p(g)
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            continue
        if p is None or hs == as_:
            continue
        rows.append((p, hs > as_))
    half = len(rows) // 2
    old, new = rows[:half], rows[half:]

    def fit(rs):
        by = {}
        for p, y in rs:
            by.setdefault(str(_pb(p)), []).append((p, y))
        out = {}
        for k, v in by.items():
            n = len(v)
            won = (sum(y for _, y in v) + 1) / (n + 2)
            said = sm.sigmoid(sum(sm.logit(p) for p, _ in v) / n)
            out[k] = round((sm.logit(won) - sm.logit(said)) * n / (n + SHRINK), 4)
        return out
    old_fit = fit(old)
    ll_book, ll_fix = _ll(new, {}), _ll(new, old_fit)
    table = {}
    for i in range(len(EDGES) - 1):
        v = [(p, y) for p, y in rows if _pb(p) == i]
        if v:
            table[f"{EDGES[i]:.0%}-{EDGES[i + 1]:.0%}"] = {
                "games": len(v), "book_said": round(sum(p for p, _ in v) / len(v), 3),
                "really_won": round(sum(y for _, y in v) / len(v), 3)}
    proven = len(new) >= 300 and ll_fix < ll_book
    return {"games": len(rows), "ll_book": round(ll_book, 5), "ll_fixed": round(ll_fix, 5), "proven": proven,
            "shifts": fit(rows) if proven else {}, "table": table}


def adjust(st, league, ph):
    """The home win chance after the price check (unchanged unless that sport's correction is proven)."""
    pc = ((st or {}).get(league) or {}).get("price") or {}
    if not pc.get("proven"):
        return ph
    return sm.sigmoid(sm.logit(ph) + pc["shifts"].get(str(_pb(ph)), 0.0))


def spot_keys(league, odds, home, rest_gap=None):
    b = bucket(odds)
    if not b:
        return []
    side = "home" if home else "away"
    r = "even rest" if rest_gap is None else rest_gap
    return [f"{b}|{side}|{r}", f"{b}|{side}", f"{b}|all", f"all|{side}", f"all|{r}", "all|all"]


def verdict(st, league, odds, home, rest_gap=None):
    """'proven' if this dog's spot has beaten its price for real, 'trap' if it surely loses, else None."""
    lg = (st or {}).get(league) or {}
    keys = spot_keys(league, odds, home, rest_gap)
    if any(k in lg.get("traps", []) for k in keys[:3]):
        return "trap"
    if any(k in lg.get("proven", []) for k in keys):
        return "proven"
    return None


def roi(rows):
    return (sum(p for p, _ in rows) / (100 * len(rows))) if rows else 0.0


def study(games, path=PATH):
    res = {}
    for lg in LEAGUES:
        rs = spots(games, lg)
        half = len(rs) // 2
        old, new = {}, {}
        for i, (_, keys, p) in enumerate(rs):
            for k in keys:
                (old if i < half else new).setdefault(k, []).append(p)
        cells = {}
        for k in sorted(set(old) | set(new)):
            a, b = old.get(k, []), new.get(k, [])
            both = len(a) >= MIN_N and len(b) >= MIN_N
            z = zscore([p for p, _ in a + b])                 # profit at the real price (juice and all)
            zf = zscore([r for _, r in a + b])                # wins vs the fair, no-juice price
            fa, fb = sum(r for _, r in a), sum(r for _, r in b)
            cells[k] = {"n_old": len(a), "roi_old": round(roi(a), 4), "n_new": len(b), "roi_new": round(roi(b), 4),
                        "win_rate": round(sum(p > 0 for p, _ in a + b) / max(1, len(a + b)), 3), "z": round(z, 2),
                        "vs_fair": round((fa + fb) / max(1, len(a + b)), 4), "z_fair": round(zf, 2),
                        "proven": both and roi(a) > 0 and roi(b) > 0 and z >= Z_PROVEN,
                        "trap": both and fa < 0 and fb < 0 and zf <= -Z_TRAP}   # wins LESS than even a fair price says
        res[lg] = {"dogs": len(rs), "cells": cells, "proven": [k for k, v in cells.items() if v["proven"]],
                   "traps": [k for k, v in cells.items() if v["trap"] and not k.startswith("all|all")],
                   "price": price_check(games, lg)}
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


if __name__ == "__main__":
    r = study(sd.load_games())
    for lg, v in r.items():
        a = v["cells"].get("all|all", {})
        pc = v["price"]
        print(f"{lg}: {v['dogs']} dogs · every dog: roi {a.get('roi_old')} then {a.get('roi_new')} · PROVEN: {v['proven']}"
              f"\n   traps: {v['traps']}\n   price check {pc['proven']} ({pc['ll_book']} -> {pc['ll_fixed']}) {pc['shifts']}"
              f"\n   {pc['table']}")
