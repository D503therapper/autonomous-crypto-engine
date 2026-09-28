"""THE HOCKEY STUDY: what the betting line misses in the NHL, tested on games the engine never saw.

For every regular-season / playoff final with a closing line and both starting goalies, in time order:
  goalie   - each goalie's goals allowed per start (shrunk toward league average; only starts BEFORE this game)
  backup   - a team starting its backup (a goalie with under 40% of the team's last 20 starts)
  b2b/rest - back-to-backs and rest days
  travel   - time zones the road team crossed since its last game
Each factor is fit on the older 2/3 against the market (the closing line as the starting point) and graded on the
newest 1/3: a factor is only KEPT if it makes the win chances more accurate than the line alone on those unseen games.
Saved to data/sports/hockey.json."""
import json
import math
import os
from datetime import datetime

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "hockey.json")
SHRINK = 10          # goalie numbers: act like 10 league-average starts on top of what we've seen
FACTORS = ("goalie", "backup", "b2b", "rest", "travel")


def _t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


def rows(games):
    fin = sorted((g for g in sm.finals(games, "nhl") if g.get("sp_home") and g.get("sp_away")), key=lambda g: g["start"])
    ga, gs = {}, {}                      # goalie -> goals allowed, starts
    team_starts = {}                     # team -> last 20 starting goalies
    last = {}                            # team -> (time, tz)
    lg_ga, lg_n = 0.0, 0
    out = []
    for g in fin:
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            continue
        h, a, gh, gaw = g["home"], g["away"], g["sp_home"], g["sp_away"]
        t = _t(g["start"])
        tz = float(g.get("tzo") or 0)
        avg = lg_ga / lg_n if lg_n else 3.0

        def gstat(k):
            return (ga.get(k, 0.0) + SHRINK * avg) / (gs.get(k, 0) + SHRINK)

        def backup(team, k):
            xs = team_starts.get(team, [])
            return 1.0 if len(xs) >= 10 and xs.count(k) / len(xs) < 0.4 else 0.0

        def rest(team):
            return min(7.0, (t - last[team][0]).total_seconds() / 86400) if team in last else 7.0
        p = sm.market_p(g)
        if p is not None and lg_n > 500 and hs != as_:
            rh, ra = rest(h), rest(a)
            travel = abs(tz - last[a][1]) if a in last else 0.0
            x = {"goalie": gstat(gaw) - gstat(gh),                       # + = home goalie better
                 "backup": backup(a, gaw) - backup(h, gh),               # + = only the away team on its backup
                 "b2b": float(ra <= 1.2) - float(rh <= 1.2),
                 "rest": (rh - ra) / 7,
                 "travel": travel / 3}
            out.append((p, x, 1 if hs > as_ else 0))
        for k, allowed in ((gh, as_), (gaw, hs)):
            ga[k] = ga.get(k, 0.0) + allowed
            gs[k] = gs.get(k, 0) + 1
        for team, k in ((h, gh), (a, gaw)):
            team_starts[team] = (team_starts.get(team, []) + [k])[-20:]
        last[h], last[a] = (t, tz), (t, tz)
        lg_ga += hs + as_
        lg_n += 2
    return out


def _ll(rs, w, keys):
    tot = 0.0
    for p, x, y in rs:
        z = sm.logit(p) + sum(w[k] * x[k] for k in keys)
        q = min(max(1 / (1 + math.exp(-z)), 1e-6), 1 - 1e-6)
        tot -= math.log(q if y else 1 - q)
    return tot / len(rs)


def _fit(rs, keys, steps=300, lr=0.5):
    w = {k: 0.0 for k in keys}
    for _ in range(steps):
        grad = {k: 0.0 for k in keys}
        for p, x, y in rs:
            z = sm.logit(p) + sum(w[k] * x[k] for k in keys)
            e = 1 / (1 + math.exp(-z)) - y
            for k in keys:
                grad[k] += e * x[k]
        for k in keys:
            w[k] -= lr * (grad[k] / len(rs) + 0.002 * w[k])      # a little shrink: no wild weights
    return w


def study(games, path=PATH):
    rs = rows(games)
    cut = len(rs) * 2 // 3
    train, test = rs[:cut], rs[cut:]
    base = _ll(test, {}, ())
    res = {"games": len(rs), "test_games": len(test), "ll_market": round(base, 5), "factors": {}}
    keep = []
    for k in FACTORS:                                   # each factor alone, on top of the line
        w = _fit(train, (k,))
        ll = _ll(test, w, (k,))
        res["factors"][k] = {"w": round(w[k], 4), "ll": round(ll, 5), "better": ll < base - 1e-5}
        if ll < base - 1e-5:
            keep.append(k)
    if keep:                                            # the keepers together, graded once more on unseen games
        w = _fit(train, tuple(keep))
        ll = _ll(test, w, tuple(keep))
        acc = sum(((sm.logit(p) + sum(w[k] * x[k] for k in keep)) > 0) == (y == 1) for p, x, y in test) / len(test)
        acc_m = sum((p > 0.5) == (y == 1) for p, _, y in test) / len(test)
        res.update({"kept": keep if ll < base else [], "ll_kept": round(ll, 5), "acc": round(acc, 4), "acc_market": round(acc_m, 4),
                    "weights": {k: round(v, 4) for k, v in _fit(rs, tuple(keep)).items()} if ll < base else {}})
    else:
        res.update({"kept": [], "weights": {}})
    with open(path + ".tmp", "w") as f:
        json.dump(res, f, indent=1)
    os.replace(path + ".tmp", path)
    return res


if __name__ == "__main__":
    print(json.dumps(study(sd.load_games()), indent=1))
