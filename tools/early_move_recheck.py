"""📈 THE MOVE MODEL, RE-CHECKED BLIND (10/7, the owner: "we need to be on these lines before they move - that's the
edge"). The 10/1 finding (tools/early_dog_studies.py, study 1): a small model trained on past seasons picks the dogs
the money then comes to by kickoff - NFL top 20% 75% moved, +6.0% at the first fair price; college 74% moved, +5.8%.
Before it could go live as an early spot this re-check held it to the five checks, honestly:
  1. FAIR prices only: the first look posted after BOTH teams' last games ended (early_football_study.ready_at / fair).
  2. BLIND: the engine's own read with the game-day facts zeroed (injuries, key starters, weather - nobody knows them
     Tuesday); the engine tuned only on the 3 seasons before; the model fit only on seasons BEFORE the graded one; the
     cutoff fixed from the training seasons (a live scan can't know a season's top 20% ahead of time); and NO
     look-ahead features - the 10/1 study's "early_move" feature used the SECOND look of the week (a later price) to
     pick a bet at the FIRST price, and its book-spread features need every book's price (the engine sees one).
  3. Most seasons up.  4. This season (2026, never seen).  5. A second look: the live line_history replay
     (tools/early_move_live.py).
Graded on WINS at the first fair price (the price a spot would post at), in the spot band +100..+220, NFL and college
separately. THE VERDICT (SPORTS_FINDINGS 10/7): DEAD - the whole 10/1 edge was the look-ahead feature; without it the
model loses in both leagues and barely calls the move better than any dog. Nothing built. Saves
results/early_move_recheck.json. No network, no paid re-pull."""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import early_dog_studies as eds     # noqa: E402
import early_football_study as ef   # noqa: E402
import sports_data as sd            # noqa: E402
import sports_early as se           # noqa: E402
import sports_model as sm           # noqa: E402

SEASONS = ef.SEASONS + (2026,)      # 2026: the season being played - never seen by any fit
BLIND = {"inj": 0.0, "key": 0.0, "weather": 0.0, "cold": 0.0}
MOVED = 10                          # the target: the dog's price came in 10+ cents by kickoff
BAND = se.SPOT_DOG                  # the spot band: +100..+220
TOP = 0.2                           # the cutoff: the top 20% of the training seasons' band dogs
MIN_TRAIN = 150
OUT = "results/early_move_recheck.json"
MOVE_FEATS = ("gap", "logodds", "home", "neutral", "me_last", "them_last", "restd", "pctd", "sept", "first3")
#   everything a live scan could see at the first fair number - nothing from a later price, nothing from game day


def cents(a, b):
    """How far a dog's price came IN from a to b, in cents (+ = toward the dog): +160 -> +140 = 20, and across the
    line +105 -> -110 = 15 (+100 and -100 are the same point - a plain a - b counted that as 215)."""
    if a is None or b is None:
        return None
    pos = lambda o: (o - 100) if o > 0 else (o + 100)      # noqa: E731
    return pos(a) - pos(b)


def move_x(f):
    """The model's inputs from a game's facts (move_facts)."""
    pct = lambda v: v if v is not None else 0.5            # noqa: E731
    x = {"gap": (f.get("gap") or 0.0) * 10, "logodds": math.log(ef._dec(f["odds"])),
         "home": 1.0 if f.get("home") else 0.0, "neutral": 1.0 if f.get("neutral") else 0.0,
         "me_last": max(-35, min(35, f.get("me_last") or 0)) / 14, "them_last": max(-35, min(35, f.get("them_last") or 0)) / 14,
         "restd": max(-7, min(7, (f.get("rest") or 7) - (f.get("orest") or 7))) / 7,
         "pctd": pct(f.get("me_pct")) - pct(f.get("them_pct")),
         "sept": 1.0 if f.get("month") in (8, 9) else 0.0, "first3": 1.0 if (f.get("games") or 0) < 3 else 0.0}
    return [1.0] + [x[k] for k in MOVE_FEATS]


def move_facts(sched, g, side, other, lg, own, mk, odds):
    """What the model sees about one side, from the schedule the engine holds (sports_early._schedule): the engine's
    blind read over the price, the price, home / neutral, both teams' last margins and rest, the records so far, the
    month - the live shape, so the line_history replay scores games exactly as a scan would."""
    start = g["start"]
    season_lo = f"{int(start[:4]) if int(start[5:7]) >= 7 else int(start[:4]) - 1}-07-01"

    def last_and_rec(team):
        prev, margin, w, l_ = None, None, 0, 0
        for st, x in sched.get((lg, team), []):
            if st >= start:
                break
            if x.get("status") != "final":
                continue
            try:
                m = float(x["home_score"]) - float(x["away_score"])
            except (KeyError, ValueError, TypeError):
                continue
            m = m if x["home"] == team else -m
            prev, margin = x, m
            if st >= season_lo:
                w, l_ = (w + 1, l_) if m > 0 else (w, l_ + 1)
        rest = (se._t(start) - se._t(prev["start"])).days if prev else None
        return margin, rest, ((w / (w + l_)) if w + l_ >= 2 else None), w + l_
    me_last, rest, me_pct, games = last_and_rec(g[side])
    them_last, orest, them_pct, _ = last_and_rec(g[other])
    return {"gap": (own - mk) if own is not None else 0.0, "odds": odds, "home": side == "home" and str(g.get("neutral")) != "1",
            "neutral": str(g.get("neutral")) == "1", "me_last": me_last, "them_last": them_last, "rest": rest,
            "orest": orest, "me_pct": me_pct, "them_pct": them_pct, "games": games, "month": int(start[5:7])}


def money_coming(lg, f, model):
    """-> (the model's say-so that the money comes to this dog, True if it clears the league's cutoff) or (None, False)
    for a league with no model."""
    m = (model or {}).get(lg)
    if not m or not m.get("w"):
        return None, False
    z = sum(a * b for a, b in zip(m["w"], move_x(f)))
    p = 1 / (1 + math.exp(-max(-30, min(30, z))))
    return round(p, 4), p >= m["cut"]


def build(lg):
    """Every dog +100..+600 at its first fair look: the price then, the close, a BLIND own read, and the facts a live
    scan could see - plus the 10/1 study's book / second-look features for comparison."""
    games = sd.load_games(lg)
    looks = eds.match_all(lg, games)
    ctx = eds.team_context(games, lg)
    lastg = ef.last_games(games, lg)
    ready = ef.ready_at(games, lg)
    rows = []
    for season in SEASONS:
        lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
        learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
        sm.KEY_EDGE = {}
        p = sm.tune(learn, lg)
        if not p or "w" not in p:
            continue
        _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
        for g, f, *_ in played:
            if not lo <= g["start"] < hi or g["id"] not in looks:
                continue
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
                ch, ca = int(float(g["ml_home"])), int(float(g["ml_away"]))
            except (KeyError, ValueError, TypeError):
                continue
            if hs == as_:
                continue
            lk = sorted((x for x in looks[g["id"]] if ef.fair(ready, g["id"], g["start"], x[0])), key=lambda x: -x[0])
            if not lk or lk[0][0] < 1.5:
                continue
            first = lk[0]
            second = next((x for x in lk[1:] if x[0] >= 1.5), None)
            own = sm.own_p(p, {**f, **BLIND})
            for side in ("home", "away"):
                i = 1 if side == "home" else 2
                o_first = first[i]
                if not eds.DOG_LO <= o_first <= eds.DOG_HI:
                    continue
                other = "away" if side == "home" else "home"
                pa, pb = eds._imp(first[1]), eds._imp(first[2])
                mk = (pa / (pa + pb)) if side == "home" else (pb / (pa + pb))
                c = ctx.get(g["id"], {})
                me, them = c.get(g[side], {}), c.get(g[other], {})
                lm = lastg.get(g["id"], {})
                rows.append({
                    "season": season, "gid": g["id"], "team": g.get(f"{side}_name"), "won": (hs > as_) == (side == "home"),
                    "side": side, "neutral": str(g.get("neutral")) == "1", "month": int(g["start"][5:7]),
                    "first": o_first, "first_best": first[i + 2], "n_books": first[5], "disp": first[6 if side == "home" else 7],
                    "second": second[i] if second else None, "close": ch if side == "home" else ca,
                    "mkt": mk, "gap": (own if side == "home" else 1 - own) - mk,
                    "me_pct": me.get("pct"), "them_pct": them.get("pct"), "games": me.get("games", 0),
                    "me_last": lm.get(side, (None, None))[1], "them_last": lm.get(other, (None, None))[1],
                    "rest": lm.get(side, (None, None))[0], "orest": lm.get(other, (None, None))[0]})
    return rows


def facts(r):
    return {"gap": r["gap"], "odds": r["first"], "home": r["side"] == "home" and not r["neutral"], "neutral": r["neutral"],
            "me_last": r["me_last"], "them_last": r["them_last"], "rest": r["rest"], "orest": r["orest"],
            "me_pct": r["me_pct"], "them_pct": r["them_pct"], "games": r["games"], "month": r["month"]}


def x_honest(r):
    return move_x(facts(r))


def x_orig(r):
    """The 10/1 study's features (early_dog_studies.feats) - with the second look and the book spread: NOT live-able."""
    return eds.feats(r)


def x_second_only(r):
    """Just the second look's move - to show where the 10/1 edge came from."""
    return [1.0, (cents(r["first"], r["second"]) or 0) / 30]


def target(r):
    return (cents(r["first"], r["close"]) or 0) >= MOVED


def grade(picks):
    if not picks:
        return None
    n = len(picks)
    dec = lambda r: ef._dec(r["first"])                     # noqa: E731
    by = {}
    for r in picks:
        by.setdefault(r["season"], []).append((dec(r) - 1) if r["won"] else -1)
    seasons = {s: [len(v), round(sum(v) / len(v), 3)] for s, v in sorted(by.items())}
    return {"bets": n, "won": round(sum(r["won"] for r in picks) / n, 3),
            "said": round(sum(1 / dec(r) for r in picks) / n, 3),
            "roi": round(sum((dec(r) - 1) if r["won"] else -1 for r in picks) / n, 3),
            "roi_close": round(sum((ef._dec(r["close"]) - 1) if r["won"] else -1 for r in picks) / n, 3),
            "moved_to_dog": round(sum(1 for r in picks if (cents(r["first"], r["close"]) or 0) > 0) / n, 3),
            "moved_10": round(sum(1 for r in picks if target(r)) / n, 3),
            "avg_cents_in": round(sum(cents(r["first"], r["close"]) or 0 for r in picks) / n, 1),
            "seasons_up": f"{sum(1 for v in seasons.values() if v[1] > 0)}/{len(seasons)}", "by_season": seasons}


def walk(rows, X, fixed_cut=True, seasons=SEASONS, top=TOP, min_train=MIN_TRAIN):
    """Train on the seasons before, bet this season's band dogs the model scores past the cutoff. fixed_cut: the
    cutoff is the training seasons' top-20% line (what a live scan would do); else the season's own top 20% (the 10/1
    study's way - it needs the whole season to rank, so it can't be bet live). -> (picks, {season: cutoff})."""
    picks, cuts = [], {}
    band = lambda r: BAND[0] <= r["first"] <= BAND[1]      # noqa: E731
    for s in seasons:
        tr = [r for r in rows if r["season"] < s]
        te = [r for r in rows if r["season"] == s and band(r)]
        if len(tr) < min_train or not te:
            continue
        w = eds.fit([X(r) for r in tr], [1.0 if target(r) else 0.0 for r in tr])
        if fixed_cut:
            sc_tr = sorted((eds.predict(w, X(r)) for r in tr if band(r)), reverse=True)
            cut = sc_tr[max(0, int(len(sc_tr) * top) - 1)]
            cuts[s] = round(cut, 4)
            picks += [r for r in te if eds.predict(w, X(r)) >= cut]
        else:
            sc = sorted(((eds.predict(w, X(r)), r) for r in te), key=lambda x: -x[0])
            picks += [r for _, r in sc[:max(1, int(len(sc) * top))]]
    return picks, cuts


def fit_live(rows, through=2025):
    """What the live model WOULD be: fit on every season through `through`, cutoff = those seasons' top-20% line (the
    line_history replay scores this season's games with it)."""
    tr = [r for r in rows if r["season"] <= through]
    w = eds.fit([x_honest(r) for r in tr], [1.0 if target(r) else 0.0 for r in tr])
    sc = sorted((eds.predict(w, x_honest(r)) for r in tr if BAND[0] <= r["first"] <= BAND[1]), reverse=True)
    cut = sc[max(0, int(len(sc) * TOP) - 1)]
    return {"w": [round(v, 4) for v in w], "cut": round(cut, 4), "feats": list(MOVE_FEATS), "fit_through": through,
            "rows": len(tr)}


def checks(g, live):
    """The five checks on a league's honest, fixed-cutoff result. live: the line_history replay's verdict, or None."""
    if not g:
        return {"pass": False, "why": "no picks"}
    past = {s: v for s, v in g["by_season"].items() if int(s) < 2026}
    this = g["by_season"].get("2026") or g["by_season"].get(2026)
    out = {"1 fair prices": True, "2 blind, no look-ahead": True,
           "3 most seasons up": sum(1 for v in past.values() if v[1] > 0) >= -(-2 * len(past) // 3) and g["roi"] > 0,
           "4 this season": (this[1] > 0) if this and this[0] >= 10 else None,
           "5 live line_history agrees": live}
    out["pass"] = bool(out["3 most seasons up"]) and out["4 this season"] is not False and live is not False
    return out


def main():
    rep = {}
    live = {}
    try:
        with open("results/early_move_live.json") as f:
            live = json.load(f)
    except (OSError, ValueError):
        pass
    for lg in ("nfl", "ncaaf"):
        rows = build(lg)
        n_band = sum(1 for r in rows if BAND[0] <= r["first"] <= BAND[1])
        print(f"\n===================== {lg.upper()}: {len(rows)} dogs at a fair first look, {n_band} in +{BAND[0]}..+{BAND[1]}")
        res = {"every band dog": grade([r for r in rows if BAND[0] <= r["first"] <= BAND[1]])}
        for name, X, fixed in (("honest features, fixed cutoff (the live rule)", x_honest, True),
                               ("honest features, season's top 20%", x_honest, False),
                               ("10/1 study features (second look + books: look-ahead)", x_orig, False),
                               ("the second look's move alone (look-ahead)", x_second_only, False)):
            picks, cuts = walk(rows, X, fixed)
            res[name] = grade(picks)
            if cuts and res[name]:
                res[name]["cutoffs"] = cuts
        for k, v in res.items():
            if not v:
                continue
            print(f"   {k:56s} {v['bets']:4d}  won {v['won']:.1%} (price said {v['said']:.1%})  ROI {v['roi']:+.1%} "
                  f"(close {v['roi_close']:+.1%})  moved to dog {v['moved_to_dog']:.0%} / 10+ {v['moved_10']:.0%} "
                  f"(avg {v['avg_cents_in']:+.0f}c)  up {v['seasons_up']} {v['by_season']}")
        ck = checks(res["honest features, fixed cutoff (the live rule)"], live.get(lg, {}).get("agrees"))
        print(f"   FIVE CHECKS: {ck}")
        res["checks"] = ck
        res["live_model"] = fit_live(rows)
        rep[lg] = res
    os.makedirs("results", exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rep, f, indent=1)
    return rep


if __name__ == "__main__":
    main()
