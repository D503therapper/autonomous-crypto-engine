"""EARLY FOOTBALL VALUE on REAL midweek prices (10/1). The owner's rules for it: the goal is an early value play that
makes money, and "a line moving our way doesn't mean they win - we have to find the WINNERS". So every study is graded
on the game result, at the price we would have bet (the median across the books at that time - not the best one, not
the close). How the line moved is shown only next to it. Ten different angles, so each one can teach something new.

Walk-forward: each season is graded by an engine trained only on the 3 seasons before it (it never saw those games).
Data: data/sports/odds_history (tools/odds_history.py) + our games. Prints a report, saves results/early_football.json."""
import gzip
import json
import os
import statistics
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd      # noqa: E402
import sports_model as sm     # noqa: E402

SPORTS = {"nfl": "americanfootball_nfl", "ncaaf": "americanfootball_ncaaf"}
SEASONS = (2020, 2021, 2022, 2023, 2024, 2025)
WINDOWS = (("5-6 days out", 4.5, 7.5), ("2-4 days out", 1.5, 4.5), ("game morning", 0.05, 1.5))
MIN_N = 40


def _t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def _am(d):
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def snapshots(sport):
    path = os.path.join(sd.DATA, "odds_history", f"{sport}.jsonl.gz")
    out = []
    if os.path.exists(path):
        with gzip.open(path, "rt") as f:
            for x in f:
                r = json.loads(x)
                if "b" in r:
                    out.append(r)
    return out


def prices(books):
    """-> (median home, median away, best home, best away) american, or None with under 2 books."""
    h = [_dec(v[0]) for v in books.values() if v and v[0] is not None]
    a = [_dec(v[1]) for v in books.values() if v and v[1] is not None]
    if len(h) < 2 or len(a) < 2:
        return None
    return _am(statistics.median(h)), _am(statistics.median(a)), _am(max(h)), _am(max(a))


def match(snaps, games):
    """-> {game id: [(days before kickoff, med home, med away, best home, best away)]}."""
    by_day = {}
    for g in games.values():
        if g.get("start"):
            by_day.setdefault(g["start"][:10], []).append(g)
    out, miss = {}, 0
    for r in snaps:
        t = _t(r["t"])
        cands = [g for d in (-1, 0, 1) for g in by_day.get((t + timedelta(days=d)).strftime("%Y-%m-%d"), [])]
        hit = None
        for g in cands:
            if abs((_t(g["start"]) - t).total_seconds()) > 14 * 3600:
                continue
            if sd._same(g.get("home_name") or "", r["h"]) and sd._same(g.get("away_name") or "", r["a"]):
                hit = (g, False)
            elif sd._same(g.get("home_name") or "", r["a"]) and sd._same(g.get("away_name") or "", r["h"]):
                hit = (g, True)
            if hit:
                break
        if not hit:
            miss += 1
            continue
        pr = prices(r["b"])
        if not pr:
            continue
        g, flip = hit
        days = (t - _t(r["snap"])).total_seconds() / 86400
        mh, ma, bh, ba = pr
        out.setdefault(g["id"], []).append((days, ma, mh, ba, bh) if flip else (days, mh, ma, bh, ba))
    return out, miss


def last_games(games, lg):
    """{game id: {side: (days since that team's last game, its margin then)}}."""
    fin = sm.finals(games, lg)
    last, out = {}, {}
    for g in fin:
        t = _t(g["start"])
        row = {}
        for side, other in (("home", "away"), ("away", "home")):
            prev = last.get(g[side])
            row[side] = ((t - prev[0]).days, prev[1]) if prev else (None, None)
        out[g["id"]] = row
        m = float(g["home_score"]) - float(g["away_score"])
        last[g["home"]], last[g["away"]] = (t, m), (t, -m)
    return out


def build(lg):
    """Every side of every graded game, with its prices at each window and the engine's reads."""
    games = sd.load_games(lg)
    pr, miss = match(snapshots(SPORTS[lg]), games)
    lastg = last_games(games, lg)
    rows = []
    for season in SEASONS:
        lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
        learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
        p = sm.tune(learn, lg)
        if not p or "w" not in p:
            continue
        _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
        for g, f, *_ in played:
            if not lo <= g["start"] < hi or g["id"] not in pr:
                continue
            try:
                hs, as_ = float(g["home_score"]), float(g["away_score"])
                ch, ca = int(float(g["ml_home"])), int(float(g["ml_away"]))
            except (KeyError, ValueError, TypeError):
                continue
            if hs == as_:
                continue
            own = sm.own_p(p, f)
            own_blind = sm.own_p(p, {**f, "inj": 0.0, "key": 0.0})      # only what's known midweek
            win = {}
            for name, dlo, dhi in WINDOWS:
                snap = [x for x in pr[g["id"]] if dlo <= x[0] < dhi]
                if snap:
                    win[name] = max(snap)                                 # the earliest look in the window
            if not win:
                continue
            for side, sign in (("home", 1), ("away", -1)):
                o = (lambda x: x) if side == "home" else (lambda x: 1 - x)
                w = {}
                for name, (_, mh, ma, bh, ba) in win.items():
                    pa, pb = 1 / _dec(mh), 1 / _dec(ma)
                    mk = pa / (pa + pb)
                    gm = {**g, "ml_home": str(mh), "ml_away": str(ma), "ml_home_open": str(mh), "ml_away_open": str(ma)}
                    w[name] = {"price": mh if side == "home" else ma, "best": bh if side == "home" else ba,
                               "mkt": o(mk), "blend": o(sm.final_p(p, f, gm))}
                rest, lm = lastg.get(g["id"], {}).get(side, (None, None))
                orest = lastg.get(g["id"], {}).get("away" if side == "home" else "home", (None, None))[0]
                rows.append({"season": season, "side": side, "won": (hs > as_) == (side == "home"),
                             "close": ch if side == "home" else ca, "own": o(own), "own_blind": o(own_blind),
                             "w": w, "rest": rest, "orest": orest, "last_margin": lm,
                             "neutral": str(g.get("neutral")) == "1", "month": int(g["start"][5:7])})
    return rows, len(pr), miss


def grade(picks):
    """picks: [(row, decimal price we bet)] -> summary graded on the RESULT at our price."""
    if not picks:
        return None
    n = len(picks)
    won = sum(r["won"] for r, _ in picks)
    roi = sum((d - 1) if r["won"] else -1 for r, d in picks) / n
    close = sum((_dec(r["close"]) - 1) if r["won"] else -1 for r, _ in picks) / n
    moved = sum(1 for r, d in picks if _dec(r["close"]) < d) / n
    by = {}
    for r, d in picks:
        by.setdefault(r["season"], []).append((d - 1) if r["won"] else -1)
    seasons = {s: [len(v), round(sum(v) / len(v), 3)] for s, v in sorted(by.items())}
    up = sum(1 for v in seasons.values() if v[1] > 0)
    return {"bets": n, "won": round(won / n, 3), "said": round(sum(1 / d for _, d in picks) / n, 3),
            "roi": round(roi, 3), "roi_close": round(close, 3), "line_our_way": round(moved, 3),
            "seasons_up": f"{up}/{len(seasons)}", "by_season": seasons}


def kind(price):
    return "dog" if 100 <= price <= 280 else "fav" if -150 <= price < 100 else None


def sel(rows, window, test, read="own", price="price"):
    out = []
    for r in rows:
        w = r["w"].get(window)
        if not w or not kind(w["price"]):
            continue
        if test(r, w, r[read] - w["mkt"] if read in ("own", "own_blind") else w[read] - w["mkt"]):
            out.append((r, _dec(w[price])))
    return out


GAP = ((0.04, 0.08), (0.08, 0.12), (0.12, 1.0))


def studies(rows):
    """The ten angles -> {study: {variant: grade}}."""
    E, M, G = "5-6 days out", "2-4 days out", "game morning"
    S = {}
    # 1. The engine's own read vs the early price - dogs, by how far it beats the price
    S["1 engine read, dogs, 5-6 days out"] = {f"+{a:.0%}..{b:.0%}": grade(sel(rows, E, lambda r, w, g, a=a, b=b:
                                              kind(w["price"]) == "dog" and a <= g < b)) for a, b in GAP}
    # 2. ...favorites (never past -150)
    S["2 engine read, favorites, 5-6 days out"] = {f"+{a:.0%}..{b:.0%}": grade(sel(rows, E, lambda r, w, g, a=a, b=b:
                                                   kind(w["price"]) == "fav" and a <= g < b)) for a, b in GAP}
    # 3. Timing: the same rule (own read 8+ over the price, any side) bet at each window
    S["3 when to bet (engine +8 or more)"] = {nm: grade(sel(rows, nm, lambda r, w, g: g >= 0.08)) for nm, *_ in WINDOWS}
    # 4. Honest midweek: no injury / starter info (nobody knows Tuesday who's out Sunday)
    S["4 midweek-only info (no injuries / starters)"] = {f"+{a:.0%}..{b:.0%}": grade(sel(
        rows, E, lambda r, w, g, a=a, b=b: a <= g < b, read="own_blind")) for a, b in GAP}
    # 5. The engine's full pick (its read blended with the market, as the board does) vs the early price
    S["5 the engine's blended pick vs the early price"] = {f"+{a:.0%}+": grade(sel(
        rows, E, lambda r, w, g, a=a: g >= a, read="blend")) for a in (0.02, 0.04, 0.06)}
    # 6. Shopping: the same picks at the best book's price instead of the middle one
    S["6 best book vs normal book (engine +8 or more)"] = {
        "normal book": grade(sel(rows, E, lambda r, w, g: g >= 0.08)),
        "best book": grade(sel(rows, E, lambda r, w, g: g >= 0.08, price="best"))}
    # 7. Overreaction: last week's blowout loser / winner, priced early, engine agreeing or not
    S["7 last week's result (early price)"] = {
        f"{lbl}{' + engine likes' if ag else ''}": grade(sel(rows, E, lambda r, w, g, t=t, ag=ag: r["last_margin"] is not None
                                                               and t(r["last_margin"]) and (not ag or g >= 0.04)))
        for lbl, t in (("lost by 17+ ", lambda m: m <= -17), ("won by 17+ ", lambda m: m >= 17),
                       ("close loss ", lambda m: -7 <= m < 0)) for ag in (False, True)}
    # 8. Rest edge: coming off a bye / long rest vs a short-week opponent
    S["8 rest (early price)"] = {
        lbl + (" + engine likes" if ag else ""): grade(sel(rows, E, lambda r, w, g, t=t, ag=ag: r["rest"] and r["orest"]
                                                            and t(r["rest"], r["orest"]) and (not ag or g >= 0.04)))
        for lbl, t in (("13+ days rest vs a normal week", lambda a, b: a >= 13 and b <= 8),
                       ("normal week vs a short week", lambda a, b: a >= 7 and b <= 5),
                       ("short week", lambda a, b: a <= 5)) for ag in (False, True)}
    # 9. Home / road / neutral early dogs the engine likes
    S["9 home vs road (engine +4 or more, early)"] = {
        f"{k} {s}": grade(sel(rows, E, lambda r, w, g, k=k, s=s: kind(w["price"]) == k and g >= 0.04 and
                              ("neutral" if r["neutral"] else r["side"]) == s))
        for k in ("dog", "fav") for s in ("home", "away", "neutral")}
    # 10. Part of the season: early (Sep), middle (Oct-Nov), late (Dec+) - when are early prices softest?
    S["10 part of the season (engine +8 or more, early)"] = {
        lbl: grade(sel(rows, E, lambda r, w, g, ms=ms: g >= 0.08 and r["month"] in ms))
        for lbl, ms in (("September", (8, 9)), ("Oct-Nov", (10, 11)), ("Dec-Feb", (12, 1, 2)))}
    return S


# ---------------------------------------------------------------- SPREADS (the owner, 10/1: "we got +9.5 and it went
# to +3.5 - we're looking at the cover: where it opened, where it ended, and if the opening number covered")
def spread_rows(lg):
    """Every side with a Tuesday spread: that number, its price, the close, did it cover the Tuesday number, and the
    engine's own margin read (trained only on the 3 seasons before)."""
    games = sd.load_games(lg)
    snaps = []
    path = os.path.join(sd.DATA, "odds_history", f"{SPORTS[lg]}_spreads.jsonl.gz")
    if os.path.exists(path):
        with gzip.open(path, "rt") as f:
            snaps = [r for r in map(json.loads, f) if "b" in r]
    tue = {}
    for r in snaps:                                   # reuse the moneyline matcher: points ride in the price slots
        pts = [v[0] for v in r["b"].values() if v and v[0] is not None]
        prs = [v[1] for v in r["b"].values() if v and v[1] is not None]
        if len(pts) < 2:
            continue
        tue_line, tue_price = statistics.median(pts), (round(statistics.median(prs)) if prs else -110)
        m, _ = match([{**r, "b": {"x": [100, 100], "y": [100, 100]}}], games)
        for gid, xs in m.items():
            flip = sd._same(games[gid].get("home_name") or "", r["a"]) and not \
                sd._same(games[gid].get("home_name") or "", r["h"])
            tue[gid] = (xs[0][0], -tue_line if flip else tue_line, tue_price)
    out = []
    for season in SEASONS:
        lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
        learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
        p = sm.tune(learn, lg)
        if not p or "sw" not in p:
            continue
        _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
        for g, f, *_ in played:
            if not lo <= g["start"] < hi or g["id"] not in tue:
                continue
            days, line, price = tue[g["id"]]
            close = sm._num(g.get("spread_home"))
            try:
                margin = float(g["home_score"]) - float(g["away_score"])
            except (KeyError, ValueError):
                continue
            if close is None or days < 2:
                continue
            ours = sum(a * b for a, b in zip(p["sw"], sm._spread_x(f)))          # the engine's own home margin
            for side, sg in (("home", 1), ("away", -1)):
                ln, cl, mg = line * sg, close * sg, margin * sg                    # (this side's number: + = getting points)
                if mg + ln == 0:
                    continue                                                       # a push
                out.append({"season": season, "side": side, "line": ln, "close": cl, "moved": ln - cl,
                            "cover": mg + ln > 0, "cover_close": mg + cl > 0 if mg + cl != 0 else None,
                            "edge": sg * ours + ln, "dec": _dec(price if -200 < price < 200 else -110)})
    return out


def sgrade(rs):
    if not rs:
        return None
    n = len(rs)
    roi = sum((r["dec"] - 1) if r["cover"] else -1 for r in rs) / n
    cc = [r["cover_close"] for r in rs if r["cover_close"] is not None]
    by = {}
    for r in rs:
        by.setdefault(r["season"], []).append((r["dec"] - 1) if r["cover"] else -1)
    seasons = {s: [len(v), round(sum(v) / len(v), 3)] for s, v in sorted(by.items())}
    return {"bets": n, "covered": round(sum(r["cover"] for r in rs) / n, 3),
            "covered_close": round(sum(cc) / len(cc), 3) if cc else None, "roi": round(roi, 3),
            "avg_move": round(sum(r["moved"] for r in rs) / n, 2),
            "seasons_up": f"{sum(1 for v in seasons.values() if v[1] > 0)}/{len(seasons)}", "by_season": seasons}


def spread_studies(rs):
    S = {}
    # S1 Did the Tuesday number cover more than the closing number? (every side - the baseline)
    S["S1 every side at the Tuesday number"] = {"all": sgrade(rs)}
    # S2 The owner's question, in hindsight: the side the line moved TOWARD - did its Tuesday number cover? (the move
    #    isn't known Tuesday; this says how much catching the move is worth - S3-S5 say if it can be called ahead)
    S["S2 hindsight: the side the line moved to (Tuesday number)"] = {
        f"moved {a}+ pts": sgrade([r for r in rs if r["moved"] >= a]) for a in (1, 2, 3, 5)}
    # S3 The engine's own margin read beating the Tuesday number
    S["S3 engine's margin read vs the Tuesday number"] = {
        f"{a}+ pts better": sgrade([r for r in rs if r["edge"] >= a]) for a in (2, 3.5, 5, 7)}
    # S4 ...as a dog getting points / a favorite laying them
    S["S4 engine 3.5+ pts better, dog or favorite"] = {
        "getting points": sgrade([r for r in rs if r["edge"] >= 3.5 and r["line"] > 0]),
        "laying points": sgrade([r for r in rs if r["edge"] >= 3.5 and r["line"] < 0])}
    # S5 Key numbers (the owner's +9.5 -> +3.5): Tuesday dogs on the far side of 7 / 3 the engine likes
    S["S5 key numbers, engine 2+ pts better"] = {
        lbl: sgrade([r for r in rs if r["edge"] >= 2 and lo_ <= r["line"] <= hi_])
        for lbl, lo_, hi_ in (("+7.5 to +10.5", 7.5, 10.5), ("+3.5 to +6.5", 3.5, 6.5), ("+1 to +3", 1, 3),
                              ("-1 to -3", -3, -1), ("-3.5 to -6.5", -6.5, -3.5), ("-7.5 to -10.5", -10.5, -7.5))}
    return S


def main():
    report = {}
    try:
        import sports_players as sp
        sm.KEY_EDGE = sp.key_edges(sd.load_games(), sp.load())
    except Exception as e:                           # noqa: BLE001
        print("no starters:", str(e)[:80])
    for lg in SPORTS:
        rows, n, miss = build(lg)
        print(f"\n===================== {lg.upper()}: {n} games with history prices, {miss} book rows unmatched, "
              f"{len(rows)} sides graded")
        S = studies(rows)
        for st, vs in S.items():
            print(f"\n-- {st}")
            for v, gr in vs.items():
                if not gr:
                    continue
                up, of = map(int, gr["seasons_up"].split("/"))
                flag = "  << HOLDS UP" if gr["bets"] >= MIN_N and gr["roi"] > 0 and up >= max(2, -(-2 * of // 3)) else ""
                print(f"   {v:40s} {gr['bets']:4d} bets  won {gr['won']:.1%} (price said {gr['said']:.1%})  "
                      f"ROI {gr['roi']:+.1%} at our price ({gr['roi_close']:+.1%} at close)  "
                      f"line our way {gr['line_our_way']:.0%}  seasons up {gr['seasons_up']} {gr['by_season']}{flag}")
        report[lg] = S
        rs = spread_rows(lg)
        print(f"\n===================== {lg.upper()} SPREADS: {len(rs)} sides with a Tuesday number")
        SS = spread_studies(rs)
        for st, vs in SS.items():
            print(f"\n-- {st}")
            for v, gr in vs.items():
                if not gr:
                    continue
                up, of = map(int, gr["seasons_up"].split("/"))
                flag = "  << HOLDS UP" if gr["bets"] >= MIN_N and gr["roi"] > 0 and up >= max(2, -(-2 * of // 3)) else ""
                cc = f"{gr['covered_close']:.1%}" if gr["covered_close"] is not None else "-"
                print(f"   {v:28s} {gr['bets']:4d} bets  covered {gr['covered']:.1%} at our number ({cc} at the close)"
                      f"  ROI {gr['roi']:+.1%}  moved {gr['avg_move']:+.1f} pts  seasons up {gr['seasons_up']} "
                      f"{gr['by_season']}{flag}")
        report[lg + "_spreads"] = SS
    os.makedirs("results", exist_ok=True)
    with open("results/early_football.json", "w") as f:
        json.dump(report, f, indent=1)


if __name__ == "__main__":
    main()
