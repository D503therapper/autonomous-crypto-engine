"""THE LABEL STUDY: which way of labeling picks (lock / strong lean / value / slight lean, Lock of the Day) actually
sorts them by how often they hit - tested on games the engine never saw.

Every past game with a moneyline is replayed with only what was known before it (the ratings replay in order).
The engine's blend (how far to trust our read vs the line) is learned on the OLDER 2/3 of the lined games and graded
on the NEWEST 1/3. On those unseen games, the engine's side of each game gets a label under each rule set, and we
count: how many, how often they hit, profit per $100, picks per day, and how the Lock of the Day did.

Core engine only (ratings + the blend with the line); the extras (injury news, proven study angles) are left out, so
the real board should do a bit better, never worse by design. Saves data/sports/tier_study.json."""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd          # noqa: E402
import sports_model as sm         # noqa: E402

PT = ZoneInfo("America/Los_Angeles")
OUT = os.path.join(sd.DATA, "tier_study.json")
MAX_FAV, MAX_DOG = -150, 400
EDGES = (1, 2, 3, 4, 5)           # edge lines to try (points our number beats the book's)


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def league_rows(games, lg, model):
    """[(day, side row...)] for the unseen third: the engine's number for both sides of every lined game."""
    p = model["params"].get(lg) or sm.default_params(lg)
    fin = sm.finals(games, lg)
    if len(fin) < 300:
        return []
    _, rows = sm.replay(fin, p.get("k", sm.BASE_K[lg]), p.get("hfa", 50), lg)
    warm = max(30, len(rows) // 5)
    rows = [r for r in rows[warm:] if r[2] != 0.5]
    lined = [(g, f, y) for g, f, y, _ in rows if sm.market_p(g) is not None
             and str(g.get("ml_home", "")).lstrip("-").isdigit() and str(g.get("ml_away", "")).lstrip("-").isdigit()]
    if len(lined) < 300:
        return []
    cut = len(lined) * 2 // 3
    train, test = lined[:cut], lined[cut:]
    w = sm.fit_logistic([sm._own_x(f) for _, f, _ in train], [y for _, _, y in train],
                        prior=[0.0, 1.0] + [0.0] * (len(sm.FEATURES) - 1))
    par = {"w": w, "trust": sm.TRUST_CAUTIOUS, "move_w": 0.0}
    X = [[sm.logit(sm.own_p(par, f)) - sm.logit(sm.market_p(g)), sm.line_move(g), sm.logit(sm.market_p(g)),
          sm.home_dog(sm.market_p(g), g)] for g, f, _ in train]
    off = [sm.logit(sm.market_p(g)) for g, _, _ in train]
    w4 = sm.fit_logistic_offset(X, [y for _, _, y in train], off, prior=[sm.TRUST_CAUTIOUS, 0.0, 0.0, 0.0], lam=8.0)
    w4[0] = min(1.0, max(0.0, w4[0]))
    out = []
    for g, f, y in test:
        m = sm.market_p(g)
        x = [sm.logit(sm.own_p(par, f)) - sm.logit(m), sm.line_move(g), sm.logit(m), sm.home_dog(m, g)]
        ph = sm.sigmoid(sm.logit(m) + sum(a * b for a, b in zip(w4, x)))
        day = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(PT).date()
        sides = []
        for side, pw, won in (("home", ph, y == 1.0), ("away", 1 - ph, y == 0.0)):
            o = int(g[f"ml_{side}"])
            sides.append({"lg": lg, "day": day.isoformat(), "odds": o, "p": pw, "won": won,
                          "edge": 100 * (pw - 1 / dec(o)), "ev": pw * dec(o) - 1})
        out.append(sides)
    return out, {"train": len(train), "test": len(test), "trust": round(w4[0], 3),
                 "from": test[0][0]["start"][:10], "to": test[-1][0]["start"][:10]}


def summarize(rows):
    n = len(rows)
    if not n:
        return {"n": 0}
    won = sum(r["won"] for r in rows)
    profit = sum((dec(r["odds"]) - 1) if r["won"] else -1 for r in rows)
    return {"n": n, "hit": round(won / n, 3), "roi": round(profit / n, 3), "avg_odds": round(sum(r["odds"] for r in rows) / n),
            "avg_p": round(sum(r["p"] for r in rows) / n, 3)}


def main():
    games = sd.load_games()
    model = json.load(open(os.path.join(sd.DATA, "model.json")))
    games_rows, meta = [], {}
    for lg in sd.LEAGUES:
        got = league_rows(games, lg, model)
        if got:
            r, meta[lg] = got
            games_rows += r
            print(lg, meta[lg], flush=True)
    # the engine's side of each game: the side with the bigger edge, inside our price limits
    picks = []
    for sides in games_rows:
        ok = [s for s in sides if MAX_FAV <= s["odds"] <= MAX_DOG]
        if ok:
            picks.append(max(ok, key=lambda s: s["edge"]))
    days = sorted({p["day"] for p in picks})
    report = {"meta": meta, "games": len(picks), "days": len(days), "all_engine_sides": summarize(picks), "rules": {}}
    for T in EDGES:
        tiers = defaultdict(list)
        for p in picks:
            fav = p["odds"] < 0
            if p["edge"] >= T:
                tiers["lock" if fav else "value"].append(p)
            elif p["edge"] > 0:
                tiers["strong_lean" if fav else "slight_lean"].append(p)
            else:
                tiers["no_edge"].append(p)
        by_day = defaultdict(list)
        for p in tiers["lock"]:
            by_day[p["day"]].append(p)
        lotd = [max(v, key=lambda p: (p["p"], p["edge"])) for v in by_day.values()]
        report["rules"][f"edge {T}+"] = {
            **{k: summarize(v) for k, v in tiers.items()},
            "lock_of_the_day": summarize(lotd), "days_with_a_lock": round(len(by_day) / max(1, len(days)), 3),
            "locks_per_day": round(len(tiers["lock"]) / max(1, len(days)), 2)}
    # the old way for comparison: win % alone (58%+ = lock), no matter the edge
    old = [p for p in picks if p["p"] >= 0.58]
    report["win_pct_only_58"] = summarize(old)
    with open(OUT, "w") as f:
        json.dump(report, f, indent=1, default=str)
    print(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    main()
