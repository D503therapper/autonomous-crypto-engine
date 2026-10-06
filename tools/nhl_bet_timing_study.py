"""WHEN TO BET OUR HOCKEY PICKS (the owner, 10/6): right when the 8 AM PT board posts, or closer to puck drop?

Report only - nothing here touches a pick, a weight, units or the posting time. No network, no paid odds: only what the
repo already holds. What the repo HOLDS for hockey (an honest inventory - the paid odds history, data/sports/odds_history,
is FOOTBALL ONLY; there is no book-by-book, time-stamped hockey price history anywhere in the repo):
  1. data/sports/games/nhl/*.csv - every game's OPENING moneyline (ml_*_open) and CLOSING moneyline (ml_*) from the
     2023-24 season on (~4,100 games). The 10/6 check against our own hourly snapshots: the NHL "open" is the price up
     a day or so ahead of the game (the overnight number), NOT a stale summer look-ahead like the NFL's - so open -> close
     is a real "earlier vs puck drop" pair. The 8 AM board price sits somewhere between the two.
  2. data/sports/line_history/*.jsonl - our own hourly snapshots (one price per side, every run, saved when it changes),
     NHL from 10/1/2026 on. The only intraday hockey history we have: the 8 AM PT price vs the close, and the morning
     goalie-confirmation window (9 AM - 1 PM PT). A few dozen games so far - it grows every day.
  3. data/sports/moves.json (clv legs) - our real posted NHL picks: the price at post time vs the close.
  4. Book-by-book hockey prices: NONE in the repo. Part 4 of the question can't be answered from what we hold.

The engine's side (part 2) is a BLIND proxy: each season graded by sports_model tuned only on the 3 seasons before it,
game-day inputs (injuries / key player) zeroed, and the side is where that read beats the no-vig OPENING price - the
same walk-forward the early football study used. It is not the real board (the dog score, the gates, the 8 AM price),
so it says how prices move on the kind of side the engine likes, not what our record would have been.

Run: python tools/nhl_bet_timing_study.py  -> prints the report, saves results/nhl_bet_timing_study.json"""
import glob
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd      # noqa: E402
import sports_model as sm     # noqa: E402

PT = ZoneInfo("America/Los_Angeles")
SEASONS = (2023, 2024, 2025, 2026)      # the seasons with a real opening line in our games
EDGE = 0.03                              # the engine's blind read beats the no-vig open by this much = "its side"
PLAY_BAND = (-150, 220)                  # never past -150, dogs to +220 (the board's own limits)
BANDS = (("-101..-150", -150, -101), ("+100..+150", 100, 150), ("+150..+220", 151, 220))
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "nhl_bet_timing_study.json")


def _t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def cents(o):
    """American odds on one continuous scale (-110 -> -10, +110 -> +10, -100/+100 -> 0) so a move across even money
    counts right. A HIGHER number is a longer price = better for whoever bets that side."""
    return o - 100 if o > 0 else o + 100


def season_of(start):
    y = int(start[:4])
    return y if start[5:7] >= "08" else y - 1


def se_p(p, n):
    return math.sqrt(p * (1 - p) / n) if n else 0.0


def se_roi(rets):
    return statistics.pstdev(rets) / math.sqrt(len(rets)) if len(rets) > 1 else 0.0


def band_of(o):
    for name, lo, hi in BANDS:
        if lo <= o <= hi:
            return name
    return "other"


def summarize(sides):
    """sides: [{"open": o, "close": c, "won": bool, "season": s, ...}] -> how the price moved and what it cost."""
    if not sides:
        return None
    n = len(sides)
    mv = [cents(s["close"]) - cents(s["open"]) for s in sides]
    pts = [s["p_close"] - s["p_open"] for s in sides]
    longer = sum(1 for m in mv if m > 0) / n
    shorter = sum(1 for m in mv if m < 0) / n
    out = {"n": n, "avg_cents": round(statistics.mean(mv), 1), "se_cents": round(se_roi(mv), 1),
           "avg_pts": round(100 * statistics.mean(pts), 2),
           "got_longer": round(longer, 3), "got_shorter": round(shorter, 3), "same": round(1 - longer - shorter, 3),
           "se_pct": round(se_p(longer, n), 3)}
    if all("won" in s for s in sides):
        r_open = [(dec(s["open"]) - 1) if s["won"] else -1.0 for s in sides]
        r_close = [(dec(s["close"]) - 1) if s["won"] else -1.0 for s in sides]
        out.update({"won": round(sum(s["won"] for s in sides) / n, 3),
                    "roi_open": round(statistics.mean(r_open), 4), "se_roi": round(se_roi(r_open), 4),
                    "roi_close": round(statistics.mean(r_close), 4),
                    "wait_gain": round(statistics.mean(r_close) - statistics.mean(r_open), 4)})
    return out


def by_season(sides):
    out = {}
    for s in sorted({x["season"] for x in sides}):
        out[str(s)] = summarize([x for x in sides if x["season"] == s])
    return out


# ------------------------------------------------------------- part 1 + 2: the opener vs the close, every season
def sides_from_games(games):
    """Every priced side of every finished NHL game with a real opener -> rows with open / close / result."""
    rows = []
    for g in sm.finals(games, "nhl"):
        h, a = sm._int(g.get("ml_home")), sm._int(g.get("ml_away"))
        ho, ao = sm._int(g.get("ml_home_open")), sm._int(g.get("ml_away_open"))
        if None in (h, a, ho, ao) or season_of(g["start"]) not in SEASONS:
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (TypeError, ValueError):
            continue
        if hs == as_:
            continue
        mo, mc = sd.no_vig(ho, ao), sd.no_vig(h, a)
        if mo is None or mc is None:
            continue
        for side, o, c, po, pc, won in (("home", ho, h, mo, mc, hs > as_), ("away", ao, a, 1 - mo, 1 - mc, as_ > hs)):
            rows.append({"id": g["id"], "season": season_of(g["start"]), "side": side, "open": o, "close": c,
                         "p_open": po, "p_close": pc, "won": won, "fav": po > 0.5, "band": band_of(o)})
    return rows


def engine_sides(games, rows):
    """The blind walk-forward read: for each season, tune on the 3 seasons before it (never these games), zero the
    game-day inputs, and keep the sides where the read beats the no-vig OPENING price by EDGE inside the play band."""
    by_id = defaultdict(dict)
    for r in rows:
        by_id[r["id"]][r["side"]] = r
    fin = sm.finals(games, "nhl")
    out = []
    for season in SEASONS:
        lo = f"{season}-08-01"
        learn = {k: g for k, g in games.items() if f"{season - 3}-08-01" <= (g.get("start") or "") < lo}
        p = sm.tune(learn, "nhl")
        if not p or "w" not in p:
            continue
        _, played = sm.replay(fin, p["k"], p["hfa"], "nhl")
        for g, f, *_ in played:
            if g["id"] not in by_id or season_of(g["start"]) != season:
                continue
            own_h = sm.own_p(p, {**f, "inj": 0.0, "key": 0.0})
            for side, own in (("home", own_h), ("away", 1 - own_h)):
                r = by_id[g["id"]].get(side)
                if not r or not PLAY_BAND[0] <= r["open"] <= PLAY_BAND[1]:
                    continue
                edge = own - r["p_open"]
                if edge >= EDGE:
                    out.append({**r, "own": round(own, 3), "edge": round(edge, 3)})
    return out


# ------------------------------------------------------------- part 3: our hourly snapshots (8 AM PT vs the close)
def hourly(games):
    hist = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(sd.LINE_HIST_DIR, "*.jsonl"))):
        with open(f) as fh:
            for ln in fh:
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if r.get("g", "").startswith("nhl:") and r.get("t") and r.get("s") and r["t"] < r["s"] \
                        and sm._int(r.get("h")) is not None and sm._int(r.get("a")) is not None:
                    hist[r["g"]].append((r["t"], sm._int(r["h"]), sm._int(r["a"])))
    rows, goalie = [], []
    for gid, snaps in hist.items():
        g = games.get(gid)
        if not g or g.get("status") != "final" or (g.get("stype") or "?") not in sd.REAL:
            continue
        snaps.sort()
        start = _t(g["start"])
        day = start.astimezone(PT).date()
        at8 = datetime.combine(day, datetime.min.time(), PT).replace(hour=8).astimezone(timezone.utc)
        at9, at13 = at8 + timedelta(hours=1), at8 + timedelta(hours=5)

        def price_at(when):
            best = None
            for t, h, a in snaps:
                if _t(t) <= when:
                    best = (h, a)
            return best
        p8, p10 = price_at(at8), price_at(at8 + timedelta(hours=2))
        close = (snaps[-1][1], snaps[-1][2])
        if not p8 or start <= at8:
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (TypeError, ValueError):
            continue
        m8, mc = sd.no_vig(*p8), sd.no_vig(*close)
        for i, side in enumerate(("home", "away")):
            won = (hs > as_) if side == "home" else (as_ > hs)
            po = m8 if side == "home" else 1 - m8
            rows.append({"id": gid, "season": season_of(g["start"]), "side": side, "open": p8[i], "close": close[i],
                         "p_open": po, "p_close": mc if side == "home" else 1 - mc, "won": won, "fav": po > 0.5,
                         "band": band_of(p8[i]), "at10": p10[i] if p10 else None})
        # the goalie window: 9 AM - 1 PM PT. A move = the price at 1 PM differs from the price at 9 AM.
        p9, p13 = price_at(at9), price_at(at13)
        if p9 and p13 and start > at13:
            fav_i = 0 if sd.no_vig(*p9) > 0.5 else 1
            mv = cents(p13[fav_i]) - cents(p9[fav_i])
            pre = price_at(at9 - timedelta(hours=5))               # the 4 AM - 9 AM window, same length, for scale
            pre_mv = (cents(p9[fav_i]) - cents(pre[fav_i])) if pre else None
            goalie.append({"id": gid, "fav_move_cents": mv, "pre_window_fav_move": pre_mv})
    return rows, goalie


# ------------------------------------------------------------- part 2b: our real posted picks
def posted():
    try:
        with open(os.path.join(sd.DATA, "moves.json")) as f:
            legs = (json.load(f).get("clv") or {}).get("legs") or []
    except (OSError, ValueError):
        return []
    seen, out = set(), []
    for lg in legs:
        if lg.get("league") != "nhl" or lg.get("market") != "ml" or lg.get("kind") not in ("lock", "dog", "play", "lean", "night", "solo"):
            continue
        k = (lg["game_id"], lg["kind"], lg["team"])
        if k in seen or lg.get("close") is None or lg.get("posted") is None:
            continue
        seen.add(k)
        o, c = int(lg["posted"]), int(lg["close"])
        out.append({"id": lg["game_id"], "season": int(lg["date"][:4]) if lg["date"][5:7] >= "08" else int(lg["date"][:4]) - 1,
                    "kind": lg["kind"], "team": lg["team"], "open": o, "close": c,
                    "p_open": 1 / dec(o), "p_close": 1 / dec(c), "won": lg.get("result") == "won", "fav": o < 0,
                    "units": 0 if lg.get("lean") else 1})
    return out


def main():
    games = sd.load_games("nhl")
    rows = sides_from_games(games)
    res = {"ran": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "games_with_open_and_close": len(rows) // 2}

    # 1. every side, opener -> close
    res["all_sides"] = {"all": summarize(rows), "by_season": by_season(rows)}
    res["favorites"] = {"all": summarize([r for r in rows if r["fav"]]), "by_season": by_season([r for r in rows if r["fav"]])}
    res["dogs"] = {"all": summarize([r for r in rows if not r["fav"]]), "by_season": by_season([r for r in rows if not r["fav"]])}
    res["home_dogs"] = summarize([r for r in rows if not r["fav"] and r["side"] == "home"])
    res["away_dogs"] = summarize([r for r in rows if not r["fav"] and r["side"] == "away"])
    res["home_favs"] = summarize([r for r in rows if r["fav"] and r["side"] == "home"])
    res["away_favs"] = summarize([r for r in rows if r["fav"] and r["side"] == "away"])
    res["by_band"] = {name: summarize([r for r in rows if r["band"] == name]) for name, _, _ in BANDS}
    # how big is a move: the spread of the open->close move in cents (all sides)
    mv = sorted(abs(cents(r["close"]) - cents(r["open"])) for r in rows)
    res["move_size_cents"] = {"median": mv[len(mv) // 2], "p75": mv[len(mv) * 3 // 4], "p90": mv[len(mv) * 9 // 10],
                              "moved_10_plus": round(sum(1 for m in mv if m >= 10) / len(mv), 3),
                              "moved_20_plus": round(sum(1 for m in mv if m >= 20) / len(mv), 3)}

    # 2. the engine's (blind proxy) sides
    eng = engine_sides(games, rows)
    res["engine_sides"] = {"rule": f"blind walk-forward own read beats the no-vig OPEN by {EDGE:.0%}, price {PLAY_BAND[0]}..+{PLAY_BAND[1]}",
                           "all": summarize(eng), "by_season": by_season(eng),
                           "dogs": {"all": summarize([r for r in eng if not r["fav"]]), "by_season": by_season([r for r in eng if not r["fav"]])},
                           "favorites": {"all": summarize([r for r in eng if r["fav"]]), "by_season": by_season([r for r in eng if r["fav"]])},
                           "by_band": {name: summarize([r for r in eng if r["band"] == name]) for name, _, _ in BANDS},
                           "big_edge_6pct": summarize([r for r in eng if r["edge"] >= 0.06])}
    # the mirror: sides the market moved TOWARD (the public / sharp side) - does the engine's side get bet into?
    # 2b. our real posted picks
    pk = posted()
    res["posted_picks"] = {"all": summarize(pk), "unit_plays": summarize([r for r in pk if r["units"]]),
                           "dogs": summarize([r for r in pk if not r["fav"]]), "favorites_and_leans": summarize([r for r in pk if r["fav"]]),
                           "legs": [{k: r[k] for k in ("id", "kind", "team", "open", "close", "won")} for r in pk]}

    # 3. our hourly snapshots: 8 AM PT vs the close, and the goalie window
    h8, goalie = hourly(games)
    res["hourly_8am_vs_close"] = {"games": len(h8) // 2, "all": summarize(h8),
                                  "dogs": summarize([r for r in h8 if not r["fav"]]),
                                  "favorites": summarize([r for r in h8 if r["fav"]]),
                                  "dogs_8am_to_10am_cents": round(statistics.mean(cents(r["at10"]) - cents(r["open"]) for r in h8
                                                                  if not r["fav"] and r["at10"] is not None), 1) if any(
                                      not r["fav"] and r["at10"] is not None for r in h8) else None}
    if goalie:
        mv = [x["fav_move_cents"] for x in goalie]
        pre = [x["pre_window_fav_move"] for x in goalie if x["pre_window_fav_move"] is not None]
        res["goalie_window_9am_1pm"] = {
            "games": len(goalie), "moved": round(sum(1 for m in mv if m != 0) / len(mv), 3),
            "moved_5_plus": round(sum(1 for m in mv if abs(m) >= 5) / len(mv), 3),
            "toward_favorite": sum(1 for m in mv if m < 0), "toward_dog": sum(1 for m in mv if m > 0),
            "avg_fav_move_cents": round(statistics.mean(mv), 1),
            "same_length_window_before_9am": {"games": len(pre), "moved": round(sum(1 for m in pre if m != 0) / len(pre), 3) if pre else None,
                                              "moved_5_plus": round(sum(1 for m in pre if abs(m) >= 5) / len(pre), 3) if pre else None}}
    res["best_book"] = "no book-by-book hockey prices in the repo (the paid odds history is NFL / college football only)"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1)
    report(res)
    return res


def _line(name, s):
    if not s:
        return f"  {name}: no games"
    out = (f"  {name}: n {s['n']}, open->close {s['avg_cents']:+.1f} cents (SE {s['se_cents']:.1f}) / {s['avg_pts']:+.2f} pts; "
           f"got longer {s['got_longer']:.0%} / shorter {s['got_shorter']:.0%} / same {s['same']:.0%}")
    if "roi_open" in s:
        out += f"; won {s['won']:.1%}, ROI at open {s['roi_open']:+.1%} (SE {s['se_roi']:.1%}) vs at close {s['roi_close']:+.1%} -> waiting {s['wait_gain']:+.1%}"
    return out


def report(res):
    print(f"NHL BET TIMING STUDY ({res['ran']}) - {res['games_with_open_and_close']} games with an opener and a close")
    print("1. EVERY SIDE, the opener (a day or so ahead) -> the close. + cents = the side got LONGER (better to wait).")
    for k in ("all_sides", "favorites", "dogs"):
        print(_line(k, res[k]["all"]))
        for s, v in res[k]["by_season"].items():
            print(_line(f"   {s}", v))
    for k in ("home_dogs", "away_dogs", "home_favs", "away_favs"):
        print(_line(k, res[k]))
    for k, v in res["by_band"].items():
        print(_line(f"band {k}", v))
    print(f"  move size (cents, every side): median {res['move_size_cents']['median']}, 75th {res['move_size_cents']['p75']}, "
          f"90th {res['move_size_cents']['p90']}; 10+ cents {res['move_size_cents']['moved_10_plus']:.0%}, 20+ {res['move_size_cents']['moved_20_plus']:.0%}")
    e = res["engine_sides"]
    print(f"2. THE ENGINE'S SIDES (blind proxy: {e['rule']})")
    print(_line("all", e["all"]))
    for s, v in e["by_season"].items():
        print(_line(f"   {s}", v))
    print(_line("dogs", e["dogs"]["all"]))
    for s, v in e["dogs"]["by_season"].items():
        print(_line(f"   {s}", v))
    print(_line("favorites", e["favorites"]["all"]))
    for s, v in e["favorites"]["by_season"].items():
        print(_line(f"   {s}", v))
    for k, v in e["by_band"].items():
        print(_line(f"band {k}", v))
    print(_line("edge 6%+", e["big_edge_6pct"]))
    p = res["posted_picks"]
    print("2b. OUR REAL POSTED NHL PICKS (post time ~8 AM PT -> the close)")
    for k in ("all", "unit_plays", "dogs", "favorites_and_leans"):
        print(_line(k, p[k]))
    h = res["hourly_8am_vs_close"]
    print(f"3. OUR HOURLY SNAPSHOTS (since 10/1/2026): the 8 AM PT price -> the close, {h['games']} games")
    for k in ("all", "dogs", "favorites"):
        print(_line(k, h[k]))
    print(f"  dogs 8 AM -> 10 AM: {h['dogs_8am_to_10am_cents']} cents")
    gw = res.get("goalie_window_9am_1pm")
    if gw:
        print(f"  goalie window 9 AM - 1 PM PT: {gw['games']} games, price moved in {gw['moved']:.0%} (5+ cents {gw['moved_5_plus']:.0%}), "
              f"toward the favorite {gw['toward_favorite']} / toward the dog {gw['toward_dog']}, favorite avg {gw['avg_fav_move_cents']:+.1f} cents; "
              f"the 5 hours before 9 AM: moved {gw['same_length_window_before_9am']['moved']}, 5+ {gw['same_length_window_before_9am']['moved_5_plus']}")
    print(f"4. BEST BOOK ON HOCKEY DOGS: {res['best_book']}")


if __name__ == "__main__":
    main()
