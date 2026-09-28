"""LINE MOVEMENT, SHARP MONEY and CLOSING LINE VALUE. Three questions:

1) STEAM: when a line moves between the open and the close, does the side it moved TOWARD win more than even the
   CLOSING price says? (Following the move = betting with the money that moved it; fading = betting the other side.)
   Per sport, the move is sized in logit points of the no-juice home win chance (small < 0.10, medium 0.10-0.30,
   large 0.30+ - roughly 2.5 / 2.5-7.5 / 7.5+ percentage points near a coin flip). For every game whose line really
   moved: did the side it moved toward win (moneyline) / cover the closing spread, compared with the closing
   no-juice price? The closing line already contains the move, so the honest expectation is "no edge left" - a
   spot is PROVEN only if its edge has the same (positive) sign on the older half of the games AND the newer half,
   with 150+ bets in each, a profit at the real closing price in both halves, and a pooled z of 1.96+ (95% sure,
   two-sided) on BOTH the edge over the fair price and the profit at the real price (a spot that beats the fair
   price but not the juice isn't a bet). ~200 spots are tested, so one or two near-misses are expected from luck.
   Games whose opening line equals the close are skipped: part of the history had the open backfilled from the
   close, so "no move" there means "no information", not "the line held".
2) REVERSE LINE MOVEMENT (2024+, where the public splits exist): 65%+ of the bets on one side, but the line moved
   the OTHER way (toward the side the public isn't betting - "the books moved against the crowd", the classic sharp
   money tell). Does the less-bet side beat the closing price? Same grading; the splits only go back to 2024, so the
   time split is short and a spot with fewer than 150 bets in either half is "watch only", never proven.
3) CLOSING LINE VALUE for OUR picks: for every posted leg whose game has started, the price we posted vs the price at
   the close for the same side and market (spreads/totals only when the closing line is the same number). Beating
   the close is the best early sign that picks are sharp, long before the win/loss record means anything. CLV is
   shown in implied-probability points (closing implied chance minus the posted implied chance: positive = we got a
   better price than the market settled on) and in cents (-110 -> -105 is 5 cents; +110 -> -110 is 20 cents).

Saved to data/sports/moves.json. Nothing here changes a pick unless a spot is PROVEN."""
import json
import math
import os

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "moves.json")
PICKS = os.path.join(sd.DATA, "picks.json")
LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "mlb", "nhl")
SIZES = ((0.01, 0.10, "small"), (0.10, 0.30, "medium"), (0.30, 99.0, "large"))   # |logit move| - below 0.01 is rounding
MIN_N, Z = 150, 1.96
RLM_PUBLIC = 65                          # "the public is on it" = 65%+ of the tickets
SHARP_GAP = 10                           # the less-bet side also draws 10+ points more of the money than of the bets


# ---------------------------------------------------------------- helpers
def zscore(xs):
    """How sure an average isn't luck (0 = pure noise, 1.96 = 95% sure either way)."""
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m / math.sqrt(v / n) if v else 0.0


def profit(odds, won):
    """What $100 at these American odds made."""
    return (odds if odds > 0 else 10000 / -odds) if won else -100.0


def size(d):
    a = abs(d)
    for lo, hi, name in SIZES:
        if lo <= a < hi:
            return name
    return None


def moved(g):
    """The logit move of the home win chance open -> close, or None when there's no real opening line."""
    oh, oa = sm._int(g.get("ml_home_open")), sm._int(g.get("ml_away_open"))
    ch, ca = sm._int(g.get("ml_home")), sm._int(g.get("ml_away"))
    if None in (oh, oa, ch, ca) or (oh, oa) == (ch, ca):
        return None                                  # no open, or an open backfilled from the close: no information
    return sm.line_move(g)


def _grade(g, side):
    """[(market, won, fair closing chance, closing odds)] for betting `side` of this final (ml + closing spread)."""
    try:
        hs, as_ = int(g["home_score"]), int(g["away_score"])
    except (TypeError, ValueError):
        return []
    out = []
    p, o = sm.market_p(g), sm._int(g.get(f"ml_{side}"))
    if p is not None and o and hs != as_:
        out.append(("ml", (hs > as_) == (side == "home"), p if side == "home" else 1 - p, o))
    line = sm._num(g.get("spread_home"))
    if g["league"] in sm.SPREAD_LEAGUES and line is not None:
        margin = (hs - as_ if side == "home" else as_ - hs) + (line if side == "home" else -line)
        oh, oa = sm._int(g.get("spread_home_odds")) or -110, sm._int(g.get("spread_away_odds")) or -110
        if margin != 0:
            fh = sd.no_vig(oh, oa)
            out.append(("spread", margin > 0, fh if side == "home" else 1 - fh, oh if side == "home" else oa))
    return out


def grade_cells(events):
    """events: [(start, key, won, fair, odds)] -> {key: graded cell}, older/newer halves split at the median date."""
    starts = sorted(e[0] for e in events)
    half = starts[len(starts) // 2] if starts else ""
    cells = {}
    for start, key, won, fair, odds in events:
        c = cells.setdefault(key, {"old": [], "new": []})
        (c["old"] if start < half else c["new"]).append((won, won - fair, profit(odds, won), start))
    out = {}
    for k, c in sorted(cells.items()):
        a, b = c["old"], c["new"]
        both = a + b
        ea = sum(r for _, r, _, _ in a) / len(a) if a else 0.0
        eb = sum(r for _, r, _, _ in b) / len(b) if b else 0.0
        pa = sum(p for _, _, p, _ in a) / (100 * len(a)) if a else 0.0
        pb = sum(p for _, _, p, _ in b) / (100 * len(b)) if b else 0.0
        z = zscore([r for _, r, _, _ in both])                 # the edge over the closing no-juice price
        zp = zscore([p for _, _, p, _ in both])                # the profit at the real closing price
        enough = len(a) >= MIN_N and len(b) >= MIN_N
        out[k] = {"n_old": len(a), "n_new": len(b), "win": round(sum(w for w, _, _, _ in both) / max(1, len(both)), 4),
                  "edge_old": round(ea, 4), "edge_new": round(eb, 4), "roi_old": round(pa, 4), "roi_new": round(pb, 4),
                  "z": round(z, 2), "z_profit": round(zp, 2),
                  "from": min((s for *_, s in both), default="")[:10], "to": max((s for *_, s in both), default="")[:10],
                  "watch_only": not enough,
                  "proven": enough and ea > 0 and eb > 0 and pa > 0 and pb > 0 and z >= Z and zp >= Z}
    return out


# ---------------------------------------------------------------- 1) steam
def steam_events(games, league):
    """For every final whose line really moved: follow / fade the move, by size and by favorite/dog."""
    out = []
    for g in sm.finals(games, league):
        d = moved(g)
        sz = size(d) if d is not None else None
        if not sz:
            continue
        to = "home" if d > 0 else "away"
        p = sm.market_p(g)
        fav = "home" if p >= 0.5 else "away"
        for how, side in (("follow", to), ("fade", "away" if to == "home" else "home")):
            where = "toward the favorite" if to == fav else "toward the dog"
            for mk, won, fair, odds in _grade(g, side):
                for s in (sz, "any size"):
                    for w in ("all", where):
                        out.append((g["start"], f"{mk}|{how}|{s}|{w}", won, fair, odds))
    return out


# ---------------------------------------------------------------- 2) reverse line movement
def _pub():
    try:
        with open(os.path.join(sd.DATA, "public.json")) as f:
            return json.load(f).get("games") or {}
    except (OSError, ValueError):
        return {}


def rlm_events(games, pub):
    """[(start, league, key, won, fair, odds)]: the LESS-bet side when the line moved against 65%+ of the tickets."""
    out = []
    for gid, s in pub.items():
        g = games.get(gid)
        if not g or g.get("status") != "final" or (g.get("stype") or "?") not in sd.REAL:
            continue
        d = moved(g)
        if d is None or abs(d) < SIZES[0][0]:
            continue
        to = "home" if d > 0 else "away"
        for mk, key in (("ml", "ml"), ("spread", "sp")):
            t = {x: s.get(f"{key}_{x}_t") for x in ("home", "away")}
            m = {x: s.get(f"{key}_{x}_m") for x in ("home", "away")}
            if any(v is None for v in t.values()):
                continue
            heavy = [x for x in ("home", "away") if t[x] >= RLM_PUBLIC]
            if not heavy or heavy[0] == to:
                continue                                        # nobody's piling on, or the line went WITH the crowd
            side = to                                           # the less-bet side the line moved toward
            spots = ["reverse move"]
            if m[side] is not None and m[side] - t[side] >= SHARP_GAP:
                spots.append("reverse move + big-bettor money")
            for gmk, won, fair, odds in _grade(g, side):
                if gmk != mk:
                    continue
                for sp_ in spots:
                    out.append((g["start"], g["league"], f"{mk}|{sp_}", won, fair, odds))
    return out


# ---------------------------------------------------------------- 3) closing line value
def cents(o):
    """American odds on a straight 'cents' scale: -110 -> -10, +110 -> +10, -100/+100 -> 0."""
    return o - 100 if o > 0 else o + 100


def closing(g, market, side, line):
    """The closing American price for this side/market, or None (a moved spread/total number = not comparable)."""
    if market == "ml":
        return sm._int(g.get(f"ml_{side}"))
    if market == "spread":
        sh = sm._num(g.get("spread_home"))
        if sh is None or line is None or side not in ("home", "away"):
            return None
        if abs((sh if side == "home" else -sh) - float(line)) > 1e-9:
            return None
        return sm._int(g.get(f"spread_{side}_odds"))
    if market == "total":
        t = sm._num(g.get("total"))
        if t is None or line is None or side not in ("over", "under") or abs(t - float(line)) > 1e-9:
            return None
        return sm._int(g.get(f"{side}_odds"))
    return None


def clv(picks, games):
    """Every posted leg whose game has closed (kicked off / final): posted price vs closing price, same side/market.
    Returns {"legs": [...], "summary": {"all": ..., "by_sport": {...}, "by_kind": {...}}, "skipped": {...}}."""
    legs, skipped = [], {}
    for card in picks or []:
        for leg in card.get("legs") or []:
            g = games.get(leg.get("game_id"))
            why = None
            if not g:
                why = "game not found"
            elif g.get("status") not in ("in", "final"):
                why = "not closed yet" if g.get("status") == "pre" else f"game {g.get('status')}"
            posted = sm._int(leg.get("odds"))
            close = None
            if not why:
                close = closing(g, leg.get("market"), leg.get("side"), leg.get("line"))
                if posted is None or close is None:
                    why = "line moved / no closing price"
            if why:
                skipped[why] = skipped.get(why, 0) + 1
                continue
            pp, pc = sd.implied(posted), sd.implied(close)
            legs.append({"date": card.get("date"), "kind": card.get("kind"), "lean": bool(card.get("lean")),
                         "game_id": leg["game_id"], "league": leg.get("league") or g["league"],
                         "team": leg.get("team"), "market": leg["market"], "side": leg["side"], "line": leg.get("line"),
                         "posted": posted, "close": close, "clv_pts": round(100 * (pc - pp), 2),
                         "clv_cents": cents(posted) - cents(close), "result": leg.get("result")})

    def summ(rows):
        if not rows:
            return {"legs": 0}
        n = len(rows)
        return {"legs": n, "avg_pts": round(sum(r["clv_pts"] for r in rows) / n, 2),
                "avg_cents": round(sum(r["clv_cents"] for r in rows) / n, 1),
                "beat": round(sum(r["clv_pts"] > 0 for r in rows) / n, 3),
                "tied": round(sum(r["clv_pts"] == 0 for r in rows) / n, 3),
                "unique_bets": len({(r["game_id"], r["market"], r["side"], r["posted"]) for r in rows})}
    by = lambda f: {k: summ([r for r in legs if f(r) == k]) for k in sorted({f(r) for r in legs})}
    return {"legs": legs, "skipped": skipped,
            "summary": {"all": summ(legs), "by_sport": by(lambda r: r["league"]), "by_kind": by(lambda r: r["kind"])}}


def clv_summary(picks=None, games=None, res=None):
    """Plain-English CLV lines (pass picks+games, or an already computed clv() result)."""
    if res is None:
        res = clv(picks, games)
    s = res["summary"]
    a = s["all"]
    sk = ", ".join(f"{v} {k}" for k, v in sorted(res["skipped"].items())) or "none"
    if not a.get("legs"):
        return [f"closing line value: no graded legs yet (skipped: {sk})"]

    def one(name, v):
        return (f"{name}: {v['legs']} legs ({v['unique_bets']} different bets) - average CLV {v['avg_pts']:+.2f} pts "
                f"({v['avg_cents']:+.1f} cents), beat the close {v['beat']:.0%}, matched it {v['tied']:.0%}")
    lines = ["closing line value - " + one("our picks", a), f"  skipped legs: {sk}"]
    lines += ["  " + one(k, v) for k, v in s["by_sport"].items()]
    lines += ["  " + one(f"{k} cards", v) for k, v in s["by_kind"].items()]
    if a["legs"] < 100:
        lines.append(f"  (only {a['legs']} legs so far - far too few to say whether we beat the market; keep watching)")
    return lines


def _picks():
    try:
        with open(PICKS) as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


# ---------------------------------------------------------------- the study
def study(games, path=PATH, pub=None, picks=None):
    res = {"steam": {}, "rlm": {}}
    for lg in LEAGUES:
        ev = steam_events(games, lg)
        cells = grade_cells(ev)
        n = sum(1 for g in sm.finals(games, lg) if size(moved(g) or 0))
        res["steam"][lg] = {"moved_games": n, "cells": cells,
                            "proven": [k for k, v in cells.items() if v["proven"]]}
    ev = rlm_events(games, _pub() if pub is None else pub)
    for lg in ("all",) + LEAGUES:
        rows = [(s, k, w, f, o) for s, league, k, w, f, o in ev if lg in ("all", league)]
        cells = grade_cells(rows)
        res["rlm"][lg] = {"cells": cells, "proven": [k for k, v in cells.items() if v["proven"]]}
    c = clv(_picks() if picks is None else picks, games)
    res["clv"] = {"summary": c["summary"], "skipped": c["skipped"], "legs": c["legs"]}
    res["proven"] = [f"steam|{lg}|{k}" for lg, v in res["steam"].items() for k in v["proven"]] + \
                    [f"rlm|{lg}|{k}" for lg, v in res["rlm"].items() for k in v["proven"]]
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


def _row(name, v):
    return (f"  {name:<44} n {v['n_old']:>5}/{v['n_new']:<5} edge {v['edge_old']:+.3f}/{v['edge_new']:+.3f} "
            f"profit {v['roi_old']:+.1%}/{v['roi_new']:+.1%} z {v['z']:+.2f}"
            f"{'  PROVEN' if v['proven'] else '  (watch only)' if v['watch_only'] else ''}")


if __name__ == "__main__":
    games = sd.load_games()
    r = study(games)
    print("STEAM - follow the open->close move, graded vs the CLOSING no-juice price (older/newer half)")
    for lg, v in r["steam"].items():
        print(f"{lg}: {v['moved_games']} finals whose line really moved")
        for k in ("ml|follow|any size|all", "ml|follow|small|all", "ml|follow|medium|all", "ml|follow|large|all",
                  "spread|follow|any size|all", "spread|follow|large|all"):
            if k in v["cells"]:
                print(_row(k, v["cells"][k]))
        print(f"  proven: {v['proven'] or 'none'}")
    print("\nREVERSE LINE MOVEMENT - 65%+ of the bets on one side, the line moved to the other (splits 2024+)")
    for lg, v in r["rlm"].items():
        for k, c in v["cells"].items():
            print(_row(f"{lg} {k} ({c['from']}..{c['to']})", c))
    print()
    print("\n".join(clv_summary(res=r["clv"])))
    tested = sum(1 for part in ("steam", "rlm") for v in r[part].values() for c in v["cells"].values()
                 if not c["watch_only"])
    print(f"\nPROVEN ({tested} spots with enough games tested):", r["proven"] or "none")
