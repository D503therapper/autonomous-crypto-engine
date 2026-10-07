"""15 EARLY DOG STUDIES (10/1, the owner: "so many dogs win - train the engine to spot them, and predict the line
movements to find the value winners"). Every study here needs the MIDWEEK prices (The Odds API history), so none of
them repeats the closing-price dog studies (SPORTS_FINDINGS: rounds 1-2). Graded on the RESULT at the price we would
have bet (median book unless the study is about a book). Walk-forward where anything is learned: each season only
learns from the seasons before it. NFL + college football, 2020-26.

Prints a report, saves results/early_dogs.json."""
import gzip
import json
import math
import os
import statistics
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import early_football_study as ef   # noqa: E402
import sports_data as sd            # noqa: E402
import sports_model as sm           # noqa: E402

DOG_LO, DOG_HI = 100, 600
MIN_N = 40


def _imp(o):
    return 1 / ef._dec(o)


def books_info(books):
    """(median h, median a, best h, best a, n books, spread of the dog-side implied % across books)."""
    pr = ef.prices(books)
    if not pr:
        return None
    hs = [_imp(v[0]) for v in books.values() if v and v[0] is not None]
    as_ = [_imp(v[1]) for v in books.values() if v and v[1] is not None]
    return pr + (len(hs), statistics.pstdev(hs) if len(hs) > 1 else 0.0, statistics.pstdev(as_) if len(as_) > 1 else 0.0)


def match_all(lg, games):
    """{game id: [(days out, info...)]} - every look, home first."""
    by_day = {}
    for g in games.values():
        if g.get("start"):
            by_day.setdefault(g["start"][:10], []).append(g)
    out = {}
    for r in ef.snapshots(ef.SPORTS[lg]):
        t = ef._t(r["t"])
        days = (t - ef._t(r["snap"])).total_seconds() / 86400
        if not 0.05 <= days < 7.5:
            continue
        hit = None
        for d in (-1, 0, 1):
            for g in by_day.get((t + timedelta(days=d)).strftime("%Y-%m-%d"), []):
                if abs((ef._t(g["start"]) - t).total_seconds()) > 14 * 3600:
                    continue
                if sd._same(g.get("home_name") or "", r["h"]) and sd._same(g.get("away_name") or "", r["a"]):
                    hit = (g, False)
                elif sd._same(g.get("home_name") or "", r["a"]) and sd._same(g.get("away_name") or "", r["h"]):
                    hit = (g, True)
                if hit:
                    break
            if hit:
                break
        if not hit:
            continue
        info = books_info(r["b"])
        if not info:
            continue
        g, flip = hit
        mh, ma, bh, ba, n, sh, sa = info
        out.setdefault(g["id"], []).append((days, ma, mh, ba, bh, n, sa, sh) if flip else (days, mh, ma, bh, ba, n, sh, sa))
    return out


def team_context(games, lg):
    """{game id: {team: dict}} - season record before the game, last / next opponent's record, last margin."""
    fin = sm.finals(games, lg)
    allg = sorted((g for g in games.values() if g.get("start") and (g.get("stype") or "?") in sd.REAL),
                  key=lambda g: g["start"])
    season = lambda s: s[:4] if s[5:7] >= "07" else str(int(s[:4]) - 1)
    rec = {}                                             # (season, team) -> [w, l]
    before = {}
    for g in fin:
        s = season(g["start"])
        before[g["id"]] = {t: tuple(rec.get((s, t), [0, 0])) for t in (g["home"], g["away"])}
        hw = float(g["home_score"]) > float(g["away_score"])
        for t, w in ((g["home"], hw), (g["away"], not hw)):
            r = rec.setdefault((s, t), [0, 0])
            r[0 if w else 1] += 1
    sched = {}
    for g in allg:
        for t, o in ((g["home"], g["away"]), (g["away"], g["home"])):
            sched.setdefault(t, []).append((g["start"], o, g["id"]))
    pct = lambda wl: (wl[0] / (wl[0] + wl[1])) if wl and wl[0] + wl[1] >= 2 else None
    out = {}
    for g in fin:
        s = season(g["start"])
        row = {}
        for t in (g["home"], g["away"]):
            lst = sched.get(t, [])
            i = next((k for k, x in enumerate(lst) if x[2] == g["id"]), None)
            prev = lst[i - 1] if i else None
            nxt = lst[i + 1] if i is not None and i + 1 < len(lst) else None
            row[t] = {"pct": pct(before[g["id"]][t]), "games": sum(before[g["id"]][t]),
                      "prev_opp": pct(before.get(prev[2], {}).get(prev[1])) if prev and season(prev[0]) == s else None,
                      "next_opp": pct(tuple(rec.get((s, nxt[1]), [0, 0]))) if nxt and season(nxt[0]) == s else None}
            # (next opponent: its record at season end - a stand-in for "a big game next week"; known to the books
            #  roughly midweek. prev opponent: its record before that game.)
        out[g["id"]] = row
    return out


def build(lg):
    games = sd.load_games(lg)
    looks = match_all(lg, games)
    ctx = team_context(games, lg)
    lastg = ef.last_games(games, lg)
    ready = ef.ready_at(games, lg)
    rows = []
    for season in ef.SEASONS:
        lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
        learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
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
                continue                                                   # no fair look before game day
            first = lk[0]                                                  # (the first look AFTER both teams' last
            second = next((x for x in lk[1:] if x[0] >= 1.5), None)        #  games were over - 10/1 audit)
            own = sm.own_p(p, f)
            for side in ("home", "away"):
                i = 1 if side == "home" else 2
                o_first = first[i]
                if not DOG_LO <= o_first <= DOG_HI:
                    continue
                other = "away" if side == "home" else "home"
                pa, pb = _imp(first[1]), _imp(first[2])
                mk = (pa / (pa + pb)) if side == "home" else (pb / (pa + pb))
                c = ctx.get(g["id"], {})
                me, them = c.get(g[side], {}), c.get(g[other], {})
                lm = lastg.get(g["id"], {})
                rows.append({
                    "season": season, "won": (hs > as_) == (side == "home"), "side": side,
                    "neutral": str(g.get("neutral")) == "1", "month": int(g["start"][5:7]),
                    "first": o_first, "first_best": first[i + 2], "n_books": first[5], "disp": first[6 if side == "home" else 7],
                    "second": second[i] if second else None, "close": ch if side == "home" else ca,
                    "mkt": mk, "gap": (own if side == "home" else 1 - own) - mk,
                    "me_pct": me.get("pct"), "them_pct": them.get("pct"), "games": me.get("games", 0),
                    "fav_next": them.get("next_opp"), "fav_prev": them.get("prev_opp"),
                    "me_last": lm.get(side, (None, None))[1], "them_last": lm.get(other, (None, None))[1],
                    "rest": lm.get(side, (None, None))[0], "orest": lm.get(other, (None, None))[0]})
    return rows


def cents(a, b):
    """How far a dog's price came IN from a to b (+ = toward the dog: +160 -> +140 = 20)."""
    return (a - b) if a is not None and b is not None else None


def g(picks, price="first"):
    """Grade [(row)] at a price key -> summary (vs every dog at the same first-look price band that season)."""
    if not picks:
        return None
    dec = lambda r: ef._dec(r[price] if isinstance(price, str) else price(r))
    n = len(picks)
    roi = sum((dec(r) - 1) if r["won"] else -1 for r in picks) / n
    by = {}
    for r in picks:
        by.setdefault(r["season"], []).append((dec(r) - 1) if r["won"] else -1)
    seasons = {s: [len(v), round(sum(v) / len(v), 3)] for s, v in sorted(by.items())}
    moved = sum(1 for r in picks if (cents(r["first"], r["close"]) or 0) > 0) / n
    return {"bets": n, "won": round(sum(r["won"] for r in picks) / n, 3),
            "said": round(sum(1 / dec(r) for r in picks) / n, 3), "roi": round(roi, 3),
            "roi_close": round(sum((ef._dec(r["close"]) - 1) if r["won"] else -1 for r in picks) / n, 3),
            "moved_to_dog": round(moved, 3),
            "seasons_up": f"{sum(1 for v in seasons.values() if v[1] > 0)}/{len(seasons)}", "by_season": seasons}


# ---------------------------------------------------------------- a tiny walk-forward logistic
FEATS = ("gap", "logodds", "home", "neutral", "me_last", "them_last", "restd", "disp", "bestgap", "nb", "early_move",
         "pctd", "sept")


def feats(r):
    x = {"gap": r["gap"] * 10, "logodds": math.log(ef._dec(r["first"])), "home": 1.0 if r["side"] == "home" else 0.0,
         "neutral": 1.0 if r["neutral"] else 0.0, "me_last": (r["me_last"] or 0) / 14, "them_last": (r["them_last"] or 0) / 14,
         "restd": max(-7, min(7, (r["rest"] or 7) - (r["orest"] or 7))) / 7, "disp": r["disp"] * 20,
         "bestgap": (ef._dec(r["first_best"]) - ef._dec(r["first"])) * 5, "nb": min(r["n_books"], 12) / 12,
         "early_move": (cents(r["first"], r["second"]) or 0) / 30,
         "pctd": ((r["me_pct"] if r["me_pct"] is not None else .5) - (r["them_pct"] if r["them_pct"] is not None else .5)),
         "sept": 1.0 if r["month"] in (8, 9) else 0.0}
    return [1.0] + [x[k] for k in FEATS]


def fit(X, y, lam=3.0, iters=300, lr=0.05):
    w = [0.0] * len(X[0])
    for _ in range(iters):
        grad = [lam * wi / len(X) for wi in w]
        grad[0] = 0.0
        for xi, yi in zip(X, y):
            p = 1 / (1 + math.exp(-max(-30, min(30, sum(a * b for a, b in zip(w, xi))))))
            for j, v in enumerate(xi):
                grad[j] += (p - yi) * v / len(X)
        w = [wi - lr * 10 * gi for wi, gi in zip(w, grad)]
    return w


def predict(w, x):
    return 1 / (1 + math.exp(-max(-30, min(30, sum(a * b for a, b in zip(w, x))))))


def walk(rows, target, use_price="first", top=0.2, offset=False):
    """Train on past seasons, score this season, bet the top `top` share (by predicted edge) at `use_price`."""
    picks = []
    for s in ef.SEASONS:
        tr = [r for r in rows if r["season"] < s and target(r) is not None]
        te = [r for r in rows if r["season"] == s]
        if len(tr) < 150 or not te:
            continue
        w = fit([feats(r) for r in tr], [1.0 if target(r) else 0.0 for r in tr])
        sc = sorted(((predict(w, feats(r)) - (1 / ef._dec(r["first"]) if offset else 0), r) for r in te),
                    key=lambda x: -x[0])
        picks += [r for _, r in sc[:max(1, int(len(sc) * top))]]
    return picks


def studies(rows):
    S = {}
    has2 = [r for r in rows if r["second"] is not None]
    # 1. A move predictor: learn (from past seasons) which dogs the money comes to by kickoff, bet them at the first look
    #    ⚠️ 10/7 RE-CHECK (tools/early_move_recheck.py): LOOK-AHEAD. feats() carries "early_move" - the move from the
    #    first look to the SECOND (a later price) - and the bet is graded at the FIRST price. That one feature is the
    #    whole +6%: without it (and the book-spread features one price feed can't see) the picks lose in both leagues.
    #    Its honest version is the 'hammered early' spot (study 4: bet at the 2nd look), already live. DEAD as a model.
    S["1 engine learns which dogs the line moves to"] = {
        f"top {int(t * 100)}%": g(walk(rows, lambda r: (cents(r["first"], r["close"]) or 0) >= 10, top=t)) for t in (.1, .2, .33)}
    # 2. A win-value predictor: learn which dogs WIN more than their price says, bet the top ones at the first look
    S["2 engine learns which dogs win more than the price says"] = {
        f"top {int(t * 100)}%": g(walk(rows, lambda r: r["won"], top=t, offset=True)) for t in (.1, .2, .33)}
    # 3. Stale book: one book well above the middle one at the first look - bet that book
    S["3 one book way above the rest (bet that book)"] = {
        f"best {c}+ cents over the middle": g([r for r in rows if r["first_best"] - r["first"] >= c], "first_best")
        for c in (10, 20, 35)}
    # 4. Early momentum: the price already came in toward the dog between the first and second look
    S["4 already moving to the dog early (bet at the 2nd look)"] = {
        f"in {c}+ cents": g([r for r in has2 if (cents(r["first"], r["second"]) or 0) >= c], "second") for c in (5, 10, 20)}
    # 5. Early drift out: the dog got LONGER early - an overreaction to buy?
    S["5 dog drifted out early (bet the longer 2nd look)"] = {
        f"out {c}+ cents": g([r for r in has2 if (cents(r["first"], r["second"]) or 0) <= -c], "second") for c in (5, 10, 20)}
    # 6. Price bands at the first look vs the close - where the early number is juiciest (the owner's +160)
    S["6 price bands (first look vs close)"] = {
        f"+{a}..+{b}": g([r for r in rows if a <= r["first"] <= b]) for a, b in ((100, 129), (130, 159), (160, 219),
                                                                               (220, 299), (300, 600))}
    # 7. Books disagree (a split market early) / few books posted yet (a thin early market)
    S["7 books disagree / few books up"] = {
        "books split (top quarter)": g(_top(rows, "disp", .25)),
        "books agree (bottom quarter)": g(_top(rows, "disp", .25, low=True)),
        "6 or fewer books posted": g([r for r in rows if r["n_books"] <= 6])}
    # 8. The engine likes it AND it's already moving its way early
    S["8 engine likes + already moving early (2nd look)"] = {
        f"engine +{int(a * 100)} & in 5+": g([r for r in has2 if r["gap"] >= a and (cents(r["first"], r["second"]) or 0) >= 5],
                                            "second") for a in (.02, .04, .08)}
    # 9. Look-ahead: the favorite has a big game NEXT week (its next opponent is good)
    S["9 favorite looking ahead to a good team next week"] = {
        f"next opp {lbl}": g([r for r in rows if r["fav_next"] is not None and t(r["fav_next"])])
        for lbl, t in (("wins 70%+", lambda x: x >= .7), ("wins 60%+", lambda x: x >= .6), ("under 40%", lambda x: x < .4))}
    # 10. Letdown: the favorite just beat a good team
    S["10 favorite just beat a good team (letdown)"] = {
        lbl: g([r for r in rows if r["fav_prev"] is not None and r["them_last"] is not None and r["them_last"] > 0
                and r["fav_prev"] >= c]) for lbl, c in (("beat a 60%+ team", .6), ("beat a 70%+ team", .7))}
    # 11. The dog's record is as good or better, but it's still the dog (early in the week)
    S["11 dog with the better record (3+ games in)"] = {
        lbl: g([r for r in rows if r["games"] >= 3 and r["me_pct"] is not None and r["them_pct"] is not None
                and t(r["me_pct"] - r["them_pct"])]) for lbl, t in (("better record", lambda d: d > 0),
                                                                    ("same record", lambda d: d == 0),
                                                                    ("much worse (-0.4)", lambda d: d <= -.4))}
    # 12. Early season: prices built on LAST year (weeks 1-3) - which dogs?
    S["12 first 3 weeks (last year's prices)"] = {
        "every dog": g([r for r in rows if r["games"] < 3]),
        "engine likes 4+": g([r for r in rows if r["games"] < 3 and r["gap"] >= .04]),
        "+160 and up": g([r for r in rows if r["games"] < 3 and r["first"] >= 160])}
    # 13. Steam on the favorite all week (dog drifted out 20+ by the close) - buy the dog LATE at the long close
    S["13 money hammered the favorite all week (bet the dog at the close)"] = {
        f"dog out {c}+ by kickoff": g([r for r in rows if (cents(r["first"], r["close"]) or 0) <= -c], "close") for c in (15, 30, 50)}
    # 14. Big early favorites: the +250 and up dogs the engine thinks are live
    S["14 big dogs the engine thinks are live (+250 and up)"] = {
        f"engine +{int(a * 100)}": g([r for r in rows if r["first"] >= 250 and r["gap"] >= a]) for a in (0.0, .04, .08)}
    # 15. Everything at once: the learned win-value model + the engine's read must both agree
    wv = walk(rows, lambda r: r["won"], top=.33, offset=True)
    S["15 learned model + engine read agree"] = {
        f"engine +{int(a * 100)}": g([r for r in wv if r["gap"] >= a]) for a in (0.0, .04, .08)}
    S["baseline: every dog at the first look"] = {"all": g(rows)}
    return S


def _top(rows, k, q, low=False):
    v = sorted(r[k] for r in rows)
    if not v:
        return []
    cut = v[int(len(v) * (q if low else 1 - q))]
    return [r for r in rows if (r[k] <= cut if low else r[k] >= cut)]


def main():
    try:
        import sports_players as sp
        sm.KEY_EDGE = sp.key_edges(sd.load_games(), sp.load())
    except Exception as e:                           # noqa: BLE001
        print("no starters:", str(e)[:80])
    rep = {}
    for lg in ("nfl", "ncaaf"):
        rows = build(lg)
        print(f"\n===================== {lg.upper()}: {len(rows)} dogs with a price before game day")
        S = studies(rows)
        for st, vs in S.items():
            print(f"\n-- {st}")
            for v, gr in vs.items():
                if not gr:
                    continue
                up, of = map(int, gr["seasons_up"].split("/"))
                flag = "  << HOLDS UP" if gr["bets"] >= MIN_N and gr["roi"] > 0 and up >= max(2, -(-2 * of // 3)) else ""
                print(f"   {v:34s} {gr['bets']:4d} bets  won {gr['won']:.1%} (price said {gr['said']:.1%})  "
                      f"ROI {gr['roi']:+.1%} ({gr['roi_close']:+.1%} at close)  moved to dog {gr['moved_to_dog']:.0%}  "
                      f"up {gr['seasons_up']} {gr['by_season']}{flag}")
        rep[lg] = S
    os.makedirs("results", exist_ok=True)
    with open("results/early_dogs.json", "w") as f:
        json.dump(rep, f, indent=1)


if __name__ == "__main__":
    main()
