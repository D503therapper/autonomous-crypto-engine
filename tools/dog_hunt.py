"""THE DOG HUNT (the owner, 9/30: "we gotta find how to pick these underdogs - and the big ones").

Every past moneyline underdog (+100 .. +280), replayed with what was known BEFORE the game (ratings as they stood,
rest, back-to-backs, form, travel, revenge, the opening vs closing line, the engine's own read vs the book). Each dog
gets yes/no facts; every fact and every pair of facts is a candidate angle, per sport.

  LEARN on the older seasons (before SPLIT): an angle needs MIN_N+ dogs and a profit in BOTH halves of those seasons.
  EXAM on the newest seasons (never looked at while learning): it has to make money there too, on EXAM_N+ dogs.
Only angles that pass the exam count. The report says how many angles were tried, so luck can be judged.
Run: python tools/dog_hunt.py
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sports_data as sd      # noqa: E402
import sports_model as sm     # noqa: E402

LEAGUES = ("mlb", "nfl", "ncaaf", "nba", "ncaab", "nhl")
SPLIT = "2025-07-01"
MIN_N, EXAM_N = 150, 40
DOG_MIN, DOG_MAX = 100, 280


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def price_bucket(o):
    return "+100-139" if o < 140 else "+140-179" if o < 180 else "+180-239" if o < 240 else "+240-280"


def facts(g, f, side, own, mkt):
    """Yes/no facts about the DOG, from its side (f is from the home team's side)."""
    s = 1 if side == "home" else -1
    out = {side, price_bucket(_int(g[f"ml_{side}"]))}
    r = s * (f.get("rest") or 0)
    out.add("more rest" if r > 0 else "less rest" if r < 0 else "even rest")
    b = s * (f.get("b2b") or 0)
    if b < 0:
        out.add("fav on b2b")
    elif b > 0:
        out.add("dog on b2b")
    fm = s * (f.get("form") or 0)
    out.add("hotter form" if fm > 0.05 else "colder form" if fm < -0.05 else "even form")
    if s * (f.get("revenge") or 0) > 0:
        out.add("revenge")
    if s * (f.get("travel") or 0) > 0:
        out.add("fav traveled more")
    gap = own - mkt
    out.add("own +8" if gap >= 0.08 else "own +4" if gap >= 0.04 else "own +0" if gap >= 0 else "own below")
    o, c = _int(g.get(f"ml_{side}_open")), _int(g.get(f"ml_{side}"))
    if o is not None and c is not None and o != c:
        out.add("money on dog" if c < o else "money on fav")     # the dog's price got shorter = money came in on it
    m = int(g["start"][5:7])
    out.add("early" if m in (9, 10, 4) else "late" if m in (2, 3, 6, 7, 8) else "mid")
    return out


def dogs(games, model):
    rows = []
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
            mk = sm.market_p(g)
            if mk is None:
                continue
            own = sm.own_p(p, f) if "w" in p else sm.final_p(p, f, g)
            for side, o, won, m, ow in (("home", oh, hs > as_, mk, own), ("away", oa, as_ > hs, 1 - mk, 1 - own)):
                if DOG_MIN <= o <= DOG_MAX:
                    rows.append((g["start"][:10], lg, facts(g, f, side, ow, m), won, dec(o)))
    rows.sort(key=lambda r: r[0])
    return rows


def roi(rs):
    return sum((r[4] - 1) if r[3] else -1 for r in rs) / len(rs) if rs else 0.0


def hunt(rows):
    learn = [r for r in rows if r[0] < SPLIT]
    exam = [r for r in rows if r[0] >= SPLIT]
    by_lg = defaultdict(list)
    for r in learn:
        by_lg[r[1]].append(r)
    tried, passed_learn, found = 0, [], []
    for lg, rs in by_lg.items():
        keys = sorted({k for r in rs for k in r[2]})
        angles = [(k,) for k in keys] + list(combinations(keys, 2))
        half = len(rs) // 2
        for a in angles:
            hit = [r for r in rs if all(k in r[2] for k in a)]
            if len(hit) < MIN_N:
                continue
            tried += 1
            h1 = [r for r in hit if r in rs[:half]] if False else [r for r in hit if r[0] < rs[half][0]]
            h2 = [r for r in hit if r[0] >= rs[half][0]]
            if len(h1) < MIN_N // 3 or len(h2) < MIN_N // 3 or roi(h1) <= 0 or roi(h2) <= 0:
                continue
            ex = [r for r in exam if r[1] == lg and all(k in r[2] for k in a)]
            passed_learn.append((lg, a, len(hit), roi(h1), roi(h2), len(ex), roi(ex),
                                 sum(r[3] for r in ex) / len(ex) if ex else 0))
            if len(ex) >= EXAM_N and roi(ex) > 0:
                found.append(passed_learn[-1])
    return tried, passed_learn, found


def main():
    games = sd.load_games()
    model = json.load(open(os.path.join(sd.DATA, "model.json")))
    rows = dogs(games, model)
    tried, learned, found = hunt(rows)
    print(f"dogs +{DOG_MIN}..+{DOG_MAX}: {len(rows)} ({sum(r[0] < SPLIT for r in rows)} learn / "
          f"{sum(r[0] >= SPLIT for r in rows)} exam) | angles tried: {tried} | made money in both learning halves: "
          f"{len(learned)} | ALSO made money on the exam: {len(found)}")
    print(f"  (luck check: of the {len(learned)} that passed learning, a coin flip would pass ~half the exam: "
          f"~{len(learned) // 2})")
    for lg, a, n, r1, r2, ne, re, hit in sorted(found, key=lambda x: -x[6] * min(1, x[5] / 100)):
        print(f"  {lg:5} {' + '.join(a):40} learn {n} dogs ({r1:+.0%} / {r2:+.0%}) | exam {ne} dogs won {hit:.0%}, money {re:+.0%}")
    out = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "tried": tried, "learned": len(learned),
           "found": [{"league": lg, "angle": list(a), "learn_n": n, "learn_roi": [round(r1, 4), round(r2, 4)],
                      "exam_n": ne, "exam_roi": round(re, 4), "exam_hit": round(hit, 4)}
                     for lg, a, n, r1, r2, ne, re, hit in found]}
    with open(os.path.join(sd.DATA, "dog_hunt.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
