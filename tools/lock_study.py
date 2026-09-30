"""THE LOCK OF THE DAY STUDY (the owner, 9/30: "find the lock of the day with the most value, not just the biggest
favorite on the board").

Every past day, replayed with the ratings as they stood BEFORE each game (no peeking): every side the engine would
call lock grade (its win % 56%+, no favorite past -150, no plus money past +125), then one Lock picked by each rule:
  likeliest   - the highest win %                     (the rule on the board today)
  value       - the most value: win % x payout        (the best price for its chance)
  own_gap     - where the engine's OWN read beats the book by the most
  value_likely- the most value among the top-3 likeliest (a blend)
  longest     - the longest price that's still lock grade
Graded on the older seasons AND on the newest ones separately (a rule has to hold up on both), with the hit rate,
the average price and the money it made. Run: python tools/lock_study.py
"""
import json
import os
import sys
from collections import defaultdict
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports_data as sd      # noqa: E402
import sports_model as sm     # noqa: E402

PT = ZoneInfo("America/Los_Angeles")
LEAGUES = ("mlb", "nfl", "ncaaf", "nba", "ncaab", "nhl")
LOCK_P, MAX_FAV, PLUS_MAX = 0.56, -150, 125
SPLIT = "2025-07-01"          # older seasons | the newest ones


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def rows(games, model):
    out = []
    from datetime import datetime
    for lg in LEAGUES:
        p = (model.get("params") or {}).get(lg) or sm.default_params(lg)
        _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
        for g, f, *_ in played:
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
                oh, oa = int(g["ml_home"]), int(g["ml_away"])
            except (ValueError, KeyError, TypeError):
                continue
            if hs == as_:
                continue
            ph, mk = sm.final_p(p, f, g), sm.market_p(g)
            if ph is None or mk is None:
                continue
            own = sm.own_p(p, f) if "w" in p else ph
            day = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(
                tzinfo=ZoneInfo("UTC")).astimezone(PT).date().isoformat()
            for pp, m, po, o, won in ((ph, mk, own, oh, hs > as_), (1 - ph, 1 - mk, 1 - own, oa, as_ > hs)):
                if pp >= LOCK_P and MAX_FAV <= o <= PLUS_MAX:
                    out.append({"day": day, "lg": lg, "p": pp, "mkt": m, "own": po, "odds": o, "dec": dec(o), "won": won})
    return out


RULES = {
    "likeliest": lambda c: max(c, key=lambda r: r["p"]),
    "value": lambda c: max(c, key=lambda r: r["p"] * r["dec"]),
    "own_gap": lambda c: max(c, key=lambda r: r["own"] - r["mkt"]),
    "value_likely": lambda c: max(sorted(c, key=lambda r: -r["p"])[:3], key=lambda r: r["p"] * r["dec"]),
    "longest": lambda c: max(c, key=lambda r: r["dec"]),
}


def study(games, model):
    by = defaultdict(list)
    for r in rows(games, model):
        by[r["day"]].append(r)
    res = {}
    for name, pick in RULES.items():
        for part, keep in (("older", lambda d: d < SPLIT), ("newest", lambda d: d >= SPLIT)):
            picks = [pick(c) for d, c in sorted(by.items()) if keep(d)]
            n = len(picks)
            if not n:
                continue
            res[f"{name}|{part}"] = {"days": n, "hit": round(sum(r["won"] for r in picks) / n, 4),
                                     "avg_price": round(sum(r["dec"] for r in picks) / n, 3),
                                     "roi": round(sum((r["dec"] - 1) if r["won"] else -1 for r in picks) / n, 4)}
    return res


def american(d):
    return f"+{round((d - 1) * 100)}" if d >= 2 else str(round(-100 / (d - 1)))


if __name__ == "__main__":
    games = sd.load_games()
    model = json.load(open(os.path.join(sd.DATA, "model.json")))
    res = study(games, model)
    for name in RULES:
        line = []
        for part in ("older", "newest"):
            v = res.get(f"{name}|{part}")
            if v:
                line.append(f"{part}: {v['days']} days, hit {v['hit']:.0%} at {american(v['avg_price'])} avg, money {v['roi']:+.1%}")
        print(f"{name:13} " + " | ".join(line))
