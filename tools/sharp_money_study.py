"""HOW OFTEN IS SHARP MONEY ACTUALLY RIGHT? (the owner, 10/7 - he bet New Mexico St +200 after FIU went -218 -> -240:
our early value play went against the money). Report only - nothing here touches a pick, a weight or units. No
network, no paid odds re-pull: only what the repo already holds.

Three questions:
  1. THE LINE MOVE = the market's sharp signal. For every game with a real opener and a close (the game files 2023-26,
     all six sports; the paid time-stamped football moneyline + spread history 2020-26): the side the line moved
     TOWARD - how often it wins straight up, what betting it at the OPEN made (the price before the move - hindsight,
     what the sharp bettor got), what betting it at the CLOSE made (betting WITH the money after the move - what a
     viewer can actually do), and what the OTHER side made at the close (fading the move). By sport, move size,
     favorite vs dog, season.
  2. THE SPLIT SIGNALS we hold (Action Network money % vs tickets %, 2024+): money over tickets, 70%+ of the tickets,
     reverse line move, the 'sharp dog' - graded at the close (the splits are the kickoff snapshot) and at the open
     (hindsight). Plus the live lead tracker's grades at the prices it logged.
  3. OUR SPOT: the engine's side (the BLIND proxy - sports_model tuned only on the 3 seasons before, game-day inputs
     zeroed, side = own read beats the no-vig price by 3%+ inside -150..+220) when the line then ran AGAINST it by
     15+ cents before the game (like NMSU) - at the price we got vs the close; our real early / posted picks the same
     way; and the 10/6 night-vs-morning finding (college dogs the money ran 20+ cents against overnight won) re-checked
     on every season, all dogs and the engine's dogs.

Run: python tools/sharp_money_study.py  -> prints the report, saves results/sharp_money_study.json"""
import gzip
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd                  # noqa: E402
import sports_model as sm                 # noqa: E402
import early_football_study as ef         # noqa: E402
import night_vs_morning_study as nvm      # noqa: E402

LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "nhl", "mlb")
nvm.SEASON_START.setdefault("ncaab", "08-01")      # college hoops season = the year it tips off
SEASONS = (2023, 2024, 2025, 2026)        # the game files' openers are real from 2023 (MLB's 2019-22 were backfilled)
EDGE, BAND = nvm.EDGE, nvm.PLAY_BAND
AGAINST = 15                              # NMSU: the line ran 15+ cents against our side
CENT_BANDS = ((1, 10, "under 10 cents"), (10, 20, "10-19 cents"), (20, 9999, "20+ cents"))
PT_BANDS = ((0.5, 1.0, "half a point"), (1.0, 2.0, "1-1.5 points"), (2.0, 3.0, "2-2.5 points"), (3.0, 99.0, "3+ points"))
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sharp_money_study.json")

_t, dec, cents, season_of = nvm._t, nvm.dec, nvm.cents, nvm.season_of


def se(xs):
    return statistics.pstdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0


def ret(odds, won):
    return (dec(odds) - 1) if won else -1.0


def cell(rows, keys=("open", "close", "fade_close")):
    """rows: dicts with won + prices -> n, straight-up win %, ROI (and SE) at each price, seasons up at the close."""
    if not rows:
        return None
    n = len(rows)
    out = {"n": n, "won": round(sum(r["won"] for r in rows) / n, 3)}
    for k in keys:
        if k == "fade_close":
            rs = [ret(r["fade_close"], not r["won"]) for r in rows if r.get("fade_close") is not None]
        else:
            rs = [ret(r[k], r["won"]) for r in rows if r.get(k) is not None]
        if rs:
            out[f"roi_{k}"] = round(statistics.mean(rs), 4)
            out[f"se_{k}"] = round(se(rs), 4)
    by = defaultdict(list)
    for r in rows:
        by[r["season"]].append(ret(r["close"], r["won"]) if r.get("close") is not None else ret(r["open"], r["won"]))
    out["by_season"] = {str(s): [len(v), round(statistics.mean(v), 3)] for s, v in sorted(by.items())}
    out["seasons_up"] = f"{sum(1 for v in by.values() if statistics.mean(v) > 0)}/{len(by)}"
    return out


def band(x, bands):
    for lo, hi, name in bands:
        if lo <= x < hi:
            return name
    return None


def scores(g):
    try:
        hs, as_ = float(g["home_score"]), float(g["away_score"])
    except (KeyError, TypeError, ValueError):
        return None
    return None if hs == as_ else (hs, as_)


# ------------------------------------------------------------------ 1a. the game files: the opener vs the close
def file_moves(lg, games, reads):
    """One row per game whose moneyline really moved: the side the line moved TOWARD, its prices and sizes."""
    rows = []
    for g in sm.finals(games, lg):
        s = season_of(lg, g["start"])
        if s not in SEASONS:
            continue
        sc = scores(g)
        h, a, ho, ao = (sm._int(g.get(k)) for k in ("ml_home", "ml_away", "ml_home_open", "ml_away_open"))
        if not sc or None in (h, a, ho, ao) or (ho, ao) == (h, a):
            continue                                   # no real opener (part of the history was backfilled from the close)
        po, pc = sd.no_vig(ho, ao), sd.no_vig(h, a)
        if abs(pc - po) < 0.005:
            continue
        to = "home" if pc > po else "away"
        o_to, c_to = (ho, h) if to == "home" else (ao, a)
        o_ot, c_ot = (ao, a) if to == "home" else (ho, h)
        move = cents(o_to) - cents(c_to)              # how many cents shorter the moved-to side got
        p_to_open = po if to == "home" else 1 - po
        own = reads.get(g["id"])
        rows.append({"id": g["id"], "lg": lg, "season": s, "to": to, "won": (sc[0] > sc[1]) == (to == "home"),
                     "open": o_to, "close": c_to, "fade_close": c_ot, "fade_open": o_ot,
                     "cents": move, "band": band(move, CENT_BANDS), "fav": p_to_open > 0.5,
                     "pts": round((pc - po) * 100 * (1 if to == "home" else -1), 1),
                     "own_to": None if own is None else (own if to == "home" else 1 - own), "p_open": p_to_open,
                     "p_close": pc if to == "home" else 1 - pc})
    return rows


def move_tables(rows):
    out = {"all": cell(rows), "favorite_moved_to": cell([r for r in rows if r["fav"]]),
           "dog_moved_to": cell([r for r in rows if not r["fav"]]), "by_size": {}, "favorites_by_size": {}, "dogs_by_size": {}}
    for _, _, name in CENT_BANDS:
        out["by_size"][name] = cell([r for r in rows if r["band"] == name])
        out["favorites_by_size"][name] = cell([r for r in rows if r["band"] == name and r["fav"]])
        out["dogs_by_size"][name] = cell([r for r in rows if r["band"] == name and not r["fav"]])
    return out


# ------------------------------------------------------------------ 1b. football paid history: first look vs the close
def first_and_last(snaps, start, ready, gid):
    """(first FAIR look, game-day look) from the time-stamped history, each (days, med home, med away, ...)."""
    fair = [x for x in snaps if x[0] >= 0.5 and ef.fair(ready, gid, start, x[0])]
    if not fair:
        return None, None
    first = max(fair, key=lambda x: x[0])
    st = _t(start)
    last = [x for x in snaps if 0.02 <= x[0] and nvm.pt_date(st - timedelta(days=x[0])) == nvm.pt_date(st)]
    return first, (min(last, key=lambda x: x[0]) if last else None)


def paid_moves(lg, games, reads):
    pr, _ = ef.match(ef.snapshots(nvm.FOOTBALL[lg]), games)
    ready = ef.ready_at(games, lg)
    rows = []
    for g in sm.finals(games, lg):
        if g["id"] not in pr:
            continue
        sc = scores(g)
        h, a = sm._int(g.get("ml_home")), sm._int(g.get("ml_away"))
        if not sc or None in (h, a):
            continue
        first, _ = first_and_last(pr[g["id"]], g["start"], ready, g["id"])
        if not first:
            continue
        po, pc = sd.no_vig(first[1], first[2]), sd.no_vig(h, a)
        if abs(pc - po) < 0.005:
            continue
        to = "home" if pc > po else "away"
        o_to, c_to = (first[1], h) if to == "home" else (first[2], a)
        c_ot = a if to == "home" else h
        move = cents(o_to) - cents(c_to)
        p_to = po if to == "home" else 1 - po
        own = reads.get(g["id"])
        rows.append({"id": g["id"], "lg": lg, "season": season_of(lg, g["start"]), "to": to,
                     "won": (sc[0] > sc[1]) == (to == "home"), "open": o_to, "close": c_to, "fade_close": c_ot,
                     "cents": move, "band": band(move, CENT_BANDS), "fav": p_to > 0.5, "days_ahead": round(first[0], 1),
                     "own_to": None if own is None else (own if to == "home" else 1 - own), "p_open": p_to})
    return rows


# ------------------------------------------------------------------ 1c. football paid history: the SPREAD move
def spread_snaps(lg, games, ready):
    """{game id: [(days before kickoff, median home line, median home juice, median away juice)]} - fair looks only."""
    by_day = defaultdict(list)
    for g in games.values():
        if g.get("start"):
            by_day[g["start"][:10]].append(g)
    path = os.path.join(sd.DATA, "odds_history", f"{nvm.FOOTBALL[lg]}_spreads.jsonl.gz")
    out = defaultdict(list)
    if not os.path.exists(path):
        return out
    with gzip.open(path, "rt") as f:
        for r in map(json.loads, f):
            if "b" not in r:
                continue
            t = _t(r["t"])
            days = (t - _t(r["snap"])).total_seconds() / 86400
            if days < 0.5:
                continue
            hit = None
            for d in (-1, 0, 1):
                for g in by_day.get((t + timedelta(days=d)).strftime("%Y-%m-%d"), []):
                    if abs((_t(g["start"]) - t).total_seconds()) > 14 * 3600:
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
            g, flip = hit
            if not ef.fair(ready, g["id"], g["start"], days):
                continue
            lines = [v for v in r["b"].values() if v and len(v) == 4 and all(x is not None for x in v) and abs(v[1]) >= 100 and abs(v[3]) >= 100]
            if len(lines) < 2:
                continue
            hl = statistics.median(v[2] if flip else v[0] for v in lines)
            hj = ef._am(statistics.median(ef._dec(v[3] if flip else v[1]) for v in lines))
            aj = ef._am(statistics.median(ef._dec(v[1] if flip else v[3]) for v in lines))
            if abs(hj) < 100 or abs(aj) < 100:
                continue
            out[g["id"]].append((days, hl, hj, aj))
    return out


def spread_moves(lg, games):
    ready = ef.ready_at(games, lg)
    snaps = spread_snaps(lg, games, ready)
    rows = []
    for g in sm.finals(games, lg):
        if g["id"] not in snaps:
            continue
        sc = scores(g)
        cl = sm._num(g.get("spread_home"))
        if sc is None or cl is None:
            continue
        first = max(snaps[g["id"]], key=lambda x: x[0])
        el = first[1]
        move = el - cl                                   # home line fell = the line moved toward HOME
        if abs(move) < 0.5:
            continue
        to = "home" if move > 0 else "away"
        ch, ca = sm._int(g.get("spread_home_odds")) or -110, sm._int(g.get("spread_away_odds")) or -110
        hs, as_ = sc
        margin_to = (hs - as_) if to == "home" else (as_ - hs)
        line_to_e = el if to == "home" else -el
        line_to_c = cl if to == "home" else -cl
        cov_e, cov_c = margin_to + line_to_e, margin_to + line_to_c
        cov_ot_c = -margin_to - line_to_c
        rows.append({"id": g["id"], "lg": lg, "season": season_of(lg, g["start"]), "to": to, "pts": abs(move),
                     "band": band(abs(move), PT_BANDS), "fav": line_to_e < 0,
                     "cov_early": None if cov_e == 0 else cov_e > 0, "cov_close": None if cov_c == 0 else cov_c > 0,
                     "cov_other_close": None if cov_ot_c == 0 else cov_ot_c > 0,
                     "juice_early": first[2] if to == "home" else first[3], "juice_close": ch if to == "home" else ca,
                     "juice_other_close": ca if to == "home" else ch})
    return rows


def spread_cell(rows):
    if not rows:
        return None
    out = {"n": len(rows)}
    for k, jk in (("early", "juice_early"), ("close", "juice_close"), ("other_close", "juice_other_close")):
        ck = f"cov_{k}"
        dec_rows = [r for r in rows if r[ck] is not None]
        if not dec_rows:
            continue
        rs = [ret(r[jk], r[ck]) for r in dec_rows]
        out[f"cover_{k}"] = round(sum(r[ck] for r in dec_rows) / len(dec_rows), 3)
        out[f"roi_{k}"] = round(statistics.mean(rs), 4)
        out[f"se_{k}"] = round(se(rs), 4)
    by = defaultdict(list)
    for r in rows:
        if r["cov_early"] is not None:
            by[r["season"]].append(ret(r["juice_early"], r["cov_early"]))
    out["by_season_early"] = {str(s): [len(v), round(statistics.mean(v), 3)] for s, v in sorted(by.items())}
    out["seasons_up_early"] = f"{sum(1 for v in by.values() if statistics.mean(v) > 0)}/{len(by)}"
    return out


def spread_tables(rows):
    out = {"all": spread_cell(rows), "favorite_moved_to": spread_cell([r for r in rows if r["fav"]]),
           "dog_moved_to": spread_cell([r for r in rows if not r["fav"]]), "by_size": {}}
    for _, _, name in PT_BANDS:
        out["by_size"][name] = spread_cell([r for r in rows if r["band"] == name])
    return out


# ------------------------------------------------------------------ 2. the split signals (money % vs tickets %)
def split_rows(games, reads_by_lg):
    try:
        with open(os.path.join(sd.DATA, "public.json")) as f:
            pub = json.load(f).get("games") or {}
    except (OSError, ValueError):
        pub = {}
    rows = []
    for gid, s in pub.items():
        g = games.get(gid)
        if not g or g.get("status") != "final" or (g.get("stype") or "?") not in sd.REAL or sd.exhibition(g):
            continue
        sc = scores(g)
        h, a, ho, ao = (sm._int(g.get(k)) for k in ("ml_home", "ml_away", "ml_home_open", "ml_away_open"))
        if not sc or None in (h, a):
            continue
        lg = g["league"]
        has_open = None not in (ho, ao) and (ho, ao) != (h, a)
        pc = sd.no_vig(h, a)
        po = sd.no_vig(ho, ao) if has_open else None
        t = {x: s.get(f"ml_{x}_t") for x in ("home", "away")}
        m = {x: s.get(f"ml_{x}_m") for x in ("home", "away")}
        if any(v is None for v in t.values()) or any(v is None for v in m.values()):
            continue
        if t["home"] + t["away"] < 90 or m["home"] + m["away"] < 90:
            continue                                   # an empty / broken split
        own_h = (reads_by_lg.get(lg) or {}).get(gid)
        for side, other in (("home", "away"), ("away", "home")):
            price_c = h if side == "home" else a
            price_o = (ho if side == "home" else ao) if has_open else None
            p_side_c = pc if side == "home" else 1 - pc
            drift = None if po is None else (p_side_c - (po if side == "home" else 1 - po))
            tags = []
            if m[side] - t[side] >= 10:
                tags.append("money 10+ over tickets")
            if m[side] - t[side] >= 20:
                tags.append("money 20+ over tickets")
            if t[side] >= 70:
                tags.append("70%+ of tickets (ride the public)")
            if t[other] >= 70:
                tags.append("fade the 70%+ public side")
            if drift is not None and drift >= 0.02:
                tags.append("line moved to it 2+ pts")
                if t[side] < 50:
                    tags.append("reverse line move (moved to it, under half the tickets)")
                if t[other] >= 65 and m[side] - t[side] >= 10:
                    tags.append("reverse move vs 65%+ public + money 10+ over")
                if price_c >= 100 and t[side] < 50 and m[side] - t[side] >= 10:
                    tags.append("sharp dog (dog, line to it 2+, money 10+ over tickets)")
            if drift is not None and drift <= -0.02 and m[side] - t[side] >= 10:
                tags.append("money 10+ over tickets but the line ran AWAY from it")
            if not tags:
                continue
            rows.append({"id": gid, "lg": lg, "season": season_of(lg, g["start"]), "side": side, "tags": tags,
                         "won": (sc[0] > sc[1]) == (side == "home"), "close": price_c, "open": price_o,
                         "fade_close": a if side == "home" else h, "fav": p_side_c > 0.5,
                         "own": None if own_h is None else (own_h if side == "home" else 1 - own_h), "p_close": p_side_c})
    return rows


def split_tables(rows):
    names = sorted({t for r in rows for t in r["tags"]})
    out = {}
    for name in names:
        rs = [r for r in rows if name in r["tags"]]
        out[name] = {"all": cell(rs), "by_sport": {lg: cell([r for r in rs if r["lg"] == lg]) for lg in LEAGUES},
                     "favorites": cell([r for r in rs if r["fav"]]), "dogs": cell([r for r in rs if not r["fav"]])}
    return out


def lead_tracker_grades(games):
    """The live lead tracker's sharp tags, re-graded at the prices it logged (1u each)."""
    try:
        with open(os.path.join(sd.DATA, "lead_tracker.json")) as f:
            rows = json.load(f)
    except (OSError, ValueError):
        rows = []
    want = ("money 10+ over tickets", "70%+ of tickets", "reverse line move to it", "sharp dog: line to it + money over tickets")
    out = {}
    for r in rows:
        g = games.get(r["game_id"]) or {}
        sc = scores(g) if g.get("status") == "final" else None
        if not sc:
            continue
        won = (sc[0] > sc[1]) == (r["side"] == "home")
        for t in r["tags"]:
            if t in want:
                x = out.setdefault(t, {"w": 0, "l": 0, "units": 0.0, "from": r["day"], "to": r["day"]})
                x["w" if won else "l"] += 1
                x["units"] = round(x["units"] + ret(r.get("odds") or 100, won), 2)
                x["to"] = max(x["to"], r["day"])
    for x in out.values():
        n = x["w"] + x["l"]
        x["roi"] = round(x["units"] / n, 3) if n else 0.0
    return out


def rigged_summary():
    try:
        with open(os.path.join(sd.DATA, "rigged.json")) as f:
            cells = json.load(f).get("cells") or {}
    except (OSError, ValueError):
        return {}
    return {k: {"n": v["n"], "won": v.get("win_rate"), "roi_old": v.get("roi_old"), "roi_new": v.get("roi_new"), "z": v.get("z")}
            for k, v in cells.items() if k.startswith("all|ml|")}


# ------------------------------------------------------------------ 3. our spot: the engine's side, the line runs against it
def engine_sides(rows_by_lg):
    """From the open->close rows: every side the blind proxy would take at the open (both the moved-to side and the
    other one), with how the close moved for it. cents_vs: + = it ran against us (we got the better price)."""
    out = []
    for lg, rows in rows_by_lg.items():
        for r in rows:
            if r["own_to"] is None:
                continue
            for mine, o, c, fade_c, p_open, own in ((True, r["open"], r["close"], r["fade_close"], r["p_open"], r["own_to"]),
                                                    (False, r["fade_open"], r["fade_close"], r["close"], 1 - r["p_open"], 1 - r["own_to"])):
                if own - p_open < EDGE or not BAND[0] <= o <= BAND[1]:
                    continue
                won = r["won"] if mine else not r["won"]
                out.append({"lg": lg, "season": r["season"], "won": won, "open": o, "close": c, "fade_close": fade_c,
                            "fav": p_open > 0.5, "cents_vs": cents(c) - cents(o), "edge": own - p_open, "with_move": mine})
    return out


def against_tables(sides):
    def grp(f):
        return [s for s in sides if f(s)]
    out = {"all_engine_sides": cell(sides),
           f"ran_against_{AGAINST}_plus": cell(grp(lambda s: s["cents_vs"] >= AGAINST)),
           f"ran_against_1_to_{AGAINST - 1}": cell(grp(lambda s: 1 <= s["cents_vs"] < AGAINST)),
           "held": cell(grp(lambda s: s["cents_vs"] == 0)),
           f"came_to_us_1_to_{AGAINST - 1}": cell(grp(lambda s: -AGAINST < s["cents_vs"] <= -1)),
           f"came_to_us_{AGAINST}_plus": cell(grp(lambda s: s["cents_vs"] <= -AGAINST)),
           "ran_against_30_plus": cell(grp(lambda s: s["cents_vs"] >= 30)),
           f"ran_against_{AGAINST}_plus_dogs": cell(grp(lambda s: s["cents_vs"] >= AGAINST and not s["fav"])),
           f"ran_against_{AGAINST}_plus_favorites": cell(grp(lambda s: s["cents_vs"] >= AGAINST and s["fav"])),
           f"came_to_us_{AGAINST}_plus_dogs": cell(grp(lambda s: s["cents_vs"] <= -AGAINST and not s["fav"])),
           "by_sport": {}}
    for lg in LEAGUES:
        a = grp(lambda s, lg=lg: s["lg"] == lg and s["cents_vs"] >= AGAINST)
        out["by_sport"][lg] = {"all": cell(grp(lambda s, lg=lg: s["lg"] == lg)), f"ran_against_{AGAINST}_plus": cell(a),
                               "ran_against_dogs": cell([s for s in a if not s["fav"]]),
                               "ran_against_favorites": cell([s for s in a if s["fav"]]),
                               f"came_to_us_{AGAINST}_plus": cell(grp(lambda s, lg=lg: s["lg"] == lg and s["cents_vs"] <= -AGAINST))}
    return out


def paid_engine_sides(lg, games, reads):
    """Football, the paid history: the engine's side at the FIRST fair look (the real early-play moment), the move to
    the game-day look and to the close."""
    pr, _ = ef.match(ef.snapshots(nvm.FOOTBALL[lg]), games)
    ready = ef.ready_at(games, lg)
    out = []
    for g in sm.finals(games, lg):
        if g["id"] not in pr or g["id"] not in reads:
            continue
        sc = scores(g)
        h, a = sm._int(g.get("ml_home")), sm._int(g.get("ml_away"))
        if not sc or None in (h, a):
            continue
        first, last = first_and_last(pr[g["id"]], g["start"], ready, g["id"])
        if not first or not last:
            continue
        po = sd.no_vig(first[1], first[2])
        for side in ("home", "away"):
            own = reads[g["id"]] if side == "home" else 1 - reads[g["id"]]
            p_side = po if side == "home" else 1 - po
            o = first[1] if side == "home" else first[2]
            if own - p_side < EDGE or not BAND[0] <= o <= BAND[1]:
                continue
            c = h if side == "home" else a
            morn = last[1] if side == "home" else last[2]
            out.append({"lg": lg, "season": season_of(lg, g["start"]), "won": (sc[0] > sc[1]) == (side == "home"),
                        "open": o, "morning": morn, "close": c, "fade_close": a if side == "home" else h,
                        "fav": p_side > 0.5, "cents_vs": cents(c) - cents(o), "cents_vs_morning": cents(morn) - cents(o),
                        "days_ahead": round(first[0], 1)})
    return out


def overnight_dogs(lg, games, reads_all):
    """The 10/6 finding re-checked: dogs (every dog, and the engine's dogs) at the night look whose price ran 15+ /
    20+ cents AGAINST them by the morning look - graded at the night price, the morning price and the close."""
    pr, _ = ef.match(ef.snapshots(nvm.FOOTBALL[lg]), games)
    ready = ef.ready_at(games, lg)
    rows = []
    for g in sm.finals(games, lg):
        if g["id"] not in pr:
            continue
        sc = scores(g)
        h, a = sm._int(g.get("ml_home")), sm._int(g.get("ml_away"))
        if not sc or None in (h, a):
            continue
        m, n = nvm.pick_windows(pr[g["id"]], g["start"], fair=lambda d, gid=g["id"], st=g["start"]: ef.fair(ready, gid, st, d))
        if not m or not n:
            continue
        pn = sd.no_vig(n[1], n[2])
        own_h = reads_all.get(g["id"])
        for side in ("home", "away"):
            p_side = pn if side == "home" else 1 - pn
            if p_side > 0.5:
                continue
            night = n[1] if side == "home" else n[2]
            morning = m[1] if side == "home" else m[2]
            close = h if side == "home" else a
            if not 100 <= night <= 220:
                continue
            own = None if own_h is None else (own_h if side == "home" else 1 - own_h)
            rows.append({"lg": lg, "season": season_of(lg, g["start"]), "won": (sc[0] > sc[1]) == (side == "home"),
                         "open": night, "morning": morning, "close": close, "fade_close": a if side == "home" else h,
                         "overnight": cents(morning) - cents(night), "engine": own is not None and own - p_side >= EDGE})
    out = {}
    for who, rs in (("every dog", rows), ("the engine's dogs", [r for r in rows if r["engine"]])):
        out[who] = {"all": cell(rs, keys=("open", "morning", "close", "fade_close")),
                    "ran_against_20_plus_overnight": cell([r for r in rs if r["overnight"] >= 20], keys=("open", "morning", "close", "fade_close")),
                    "ran_against_15_plus_overnight": cell([r for r in rs if r["overnight"] >= 15], keys=("open", "morning", "close", "fade_close")),
                    "money_came_to_it_20_plus_overnight": cell([r for r in rs if r["overnight"] <= -20], keys=("open", "morning", "close", "fade_close")),
                    "flat_under_15": cell([r for r in rs if abs(r["overnight"]) < 15], keys=("open", "morning", "close", "fade_close"))}
    return out


def real_picks(games):
    """Our real posted picks (early.json + the pick journal via the CLV legs): posted price vs the close, and the ones
    the line ran 15+ cents against."""
    out = []
    try:
        with open(os.path.join(sd.DATA, "early.json")) as f:
            early = json.load(f).get("picks") or []
    except (OSError, ValueError):
        early = []
    try:
        with open(os.path.join(sd.DATA, "moves.json")) as f:
            legs = (json.load(f).get("clv") or {}).get("legs") or []
    except (OSError, ValueError):
        legs = []
    hist = nvm.line_history()
    for p in early:
        g = games.get(p["game_id"]) or {}
        snaps = hist.get(p["game_id"]) or []
        i = 0 if p["side"] == "home" else 1
        now = snaps[-1][1 + i] if snaps else None
        close = sm._int(g.get(f"ml_{p['side']}")) if g.get("status") == "final" else None
        out.append({"what": "early play", "date": (p.get("posted") or "")[:10], "league": p["league"], "team": p["team"],
                    "posted": p["odds"], "latest_or_close": close if close is not None else now,
                    "cents_vs": None if (close or now) is None else cents(close if close is not None else now) - cents(p["odds"]),
                    "result": p.get("result"), "final": close is not None})
    for lg_ in legs:
        if lg_.get("market") != "ml" or lg_.get("close") is None or lg_.get("result") not in ("won", "lost"):
            continue
        out.append({"what": f"board {lg_.get('kind')}" + (" (lean)" if lg_.get("lean") else ""), "date": lg_["date"], "league": lg_["league"],
                    "team": lg_["team"], "posted": lg_["posted"], "latest_or_close": lg_["close"],
                    "cents_vs": cents(lg_["close"]) - cents(lg_["posted"]), "result": lg_["result"], "final": True})
    graded = [x for x in out if x["final"] and x["result"] in ("won", "lost")]
    def summ(rs):
        if not rs:
            return None
        rp = [ret(x["posted"], x["result"] == "won") for x in rs]
        rc = [ret(x["latest_or_close"], x["result"] == "won") for x in rs]
        return {"n": len(rs), "won": sum(1 for x in rs if x["result"] == "won"), "roi_posted": round(statistics.mean(rp), 3),
                "roi_close": round(statistics.mean(rc), 3), "avg_cents_vs": round(statistics.mean(x["cents_vs"] for x in rs), 1)}
    return {"graded": summ(graded), f"ran_against_{AGAINST}_plus": summ([x for x in graded if x["cents_vs"] >= AGAINST]),
            "came_to_us_or_held": summ([x for x in graded if x["cents_vs"] <= 0]), "picks": out}


# ------------------------------------------------------------------ run
def main():
    res = {"ran": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "line_move_game_files": {}, "line_move_paid_football": {},
           "spread_move_paid_football": {}, "splits": {}, "our_spot": {}}
    all_games, reads_by_lg, rows_by_lg = {}, {}, {}
    for lg in LEAGUES:
        games = sd.load_games(lg)
        all_games.update(games)
        reads = {}
        for s in SEASONS:
            reads.update(nvm.blind_reads(games, lg, s))
        reads_by_lg[lg] = reads
        rows = file_moves(lg, games, reads)
        rows_by_lg[lg] = rows
        res["line_move_game_files"][lg] = move_tables(rows)
        if lg in nvm.FOOTBALL:
            for s in ef.SEASONS:
                if s not in SEASONS:
                    reads.update(nvm.blind_reads(games, lg, s))
            res["line_move_paid_football"][lg] = move_tables(paid_moves(lg, games, reads))
            res["spread_move_paid_football"][lg] = spread_tables(spread_moves(lg, games))
            res["our_spot"][f"{lg}_paid_first_look"] = against_tables(paid_engine_sides(lg, games, reads))
            res["our_spot"][f"{lg}_overnight_dogs"] = overnight_dogs(lg, games, reads)
    allrows = [r for rows in rows_by_lg.values() for r in rows]
    res["line_move_game_files"]["all_sports"] = move_tables(allrows)
    sr = split_rows(all_games, reads_by_lg)
    res["splits"] = {"signals_at_the_close": split_tables(sr), "live_lead_tracker": lead_tracker_grades(all_games),
                     "rigged_study_cells": rigged_summary()}
    res["our_spot"]["open_to_close_blind_proxy"] = against_tables(engine_sides(rows_by_lg))
    res["our_spot"]["real_posted_picks"] = real_picks(all_games)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1)
    report(res)
    return res


def _c(name, c, keys=("open", "close", "fade_close")):
    if not c:
        return f"    {name}: none"
    s = f"    {name}: n {c['n']}, won {c['won']:.1%}"
    labels = {"open": "at the open", "close": "at the close", "fade_close": "the OTHER side at the close", "morning": "at the morning price"}
    for k in keys:
        if f"roi_{k}" in c:
            s += f"; {labels[k]} {c[f'roi_{k}']:+.1%} (SE {c[f'se_{k}']:.1%})"
    return s + f"; seasons up (close) {c['seasons_up']} {c['by_season']}"


def _sc(name, c):
    if not c:
        return f"    {name}: none"
    s = f"    {name}: n {c['n']}"
    for k, lab in (("early", "covered at the early number"), ("close", "at the close"), ("other_close", "the OTHER side at the close")):
        if f"cover_{k}" in c:
            s += f"; {lab} {c[f'cover_{k}']:.1%} / ROI {c[f'roi_{k}']:+.1%} (SE {c[f'se_{k}']:.1%})"
    return s + f"; seasons up (early) {c['seasons_up_early']} {c['by_season_early']}"


def _mt(t):
    for k in ("all", "favorite_moved_to", "dog_moved_to"):
        print(_c(k, t[k]))
    for grp in ("by_size", "favorites_by_size", "dogs_by_size"):
        for name, c in t.get(grp, {}).items():
            print(_c(f"{grp} / {name}", c))


def report(res):
    print(f"HOW OFTEN IS SHARP MONEY RIGHT? ({res['ran']})  - the side the line moved TOWARD, open -> close")
    print("\n1a. THE GAME FILES 2023-26 (one opener, one close per game; MLB openers before 2023 were backfilled - skipped):")
    for lg, t in res["line_move_game_files"].items():
        print(f"  {lg.upper()}:")
        _mt(t)
    print("\n1b. FOOTBALL, the paid time-stamped history 2020-26: the FIRST fair look of the week (median book) -> the close:")
    for lg, t in res["line_move_paid_football"].items():
        print(f"  {lg.upper()}:")
        _mt(t)
    print("\n1c. FOOTBALL SPREADS, the paid history: the first fair look -> the closing spread (the side the number moved toward):")
    for lg, t in res["spread_move_paid_football"].items():
        print(f"  {lg.upper()}:")
        for k in ("all", "favorite_moved_to", "dog_moved_to"):
            print(_sc(k, t[k]))
        for name, c in t["by_size"].items():
            print(_sc(f"by size / {name}", c))
    print("\n2. THE SPLIT SIGNALS (Action Network money % vs tickets %, the kickoff snapshot, 2024+), graded at the close (and at the open = hindsight):")
    for name, t in res["splits"]["signals_at_the_close"].items():
        print(f"  {name}:")
        print(_c("all", t["all"]))
        print(_c("favorites", t["favorites"]))
        print(_c("dogs", t["dogs"]))
        for lg, c in t["by_sport"].items():
            if c:
                print(_c(f"  {lg}", c))
    print("  the live lead tracker (since 10/1, 1u at the logged price):")
    for k, v in res["splits"]["live_lead_tracker"].items():
        print(f"    {k}: {v['w']}-{v['l']}, {v['units']:+.2f}u, ROI {v['roi']:+.1%} ({v['from']} .. {v['to']})")
    print("  the rigged-study cells (data/sports/rigged.json, moneylines, all sports):")
    for k, v in res["splits"]["rigged_study_cells"].items():
        print(f"    {k}: n {v['n']}, won {v['won']:.1%}, ROI older half {v['roi_old']:+.1%} / newer half {v['roi_new']:+.1%}, z {v['z']}")
    print(f"\n3. OUR SPOT - the engine's side (blind proxy) and where the line went next (cents_vs + = it ran AGAINST us, we hold the better price):")
    o = res["our_spot"]["open_to_close_blind_proxy"]
    print("  3a. every sport, the opener -> the close (2023-26):")
    for k, c in o.items():
        if k != "by_sport":
            print(_c(k, c))
    for lg, t in o["by_sport"].items():
        print(f"    {lg}:")
        for k, c in t.items():
            print(_c("  " + k, c))
    for lg in ("nfl", "ncaaf"):
        print(f"  3b. {lg.upper()} - the first fair look of the week (the early-play moment) -> the close (2020-26):")
        t = res["our_spot"][f"{lg}_paid_first_look"]
        for k, c in t.items():
            if k != "by_sport":
                print(_c(k, c))
        print(f"  3c. {lg.upper()} - dogs at the night look whose price ran against them overnight (the 10/6 finding, all seasons):")
        for who, t in res["our_spot"][f"{lg}_overnight_dogs"].items():
            print(f"    {who}:")
            for k, c in t.items():
                print(_c("  " + k, c, keys=("open", "morning", "close", "fade_close")))
    rp = res["our_spot"]["real_posted_picks"]
    print(f"  3d. OUR REAL PICKS: graded {rp['graded']}; ran against 15+ {rp[f'ran_against_{AGAINST}_plus']}; came to us / held {rp['came_to_us_or_held']}")
    for x in rp["picks"]:
        print(f"    {x['date']} {x['league']:5} {x['what']:18} {x['team']:16} posted {x['posted']:+5} -> {'close' if x['final'] else 'now  '} "
              f"{x['latest_or_close'] if x['latest_or_close'] is not None else '?':>5}  ({x['cents_vs'] if x['cents_vs'] is not None else '?'} cents)  {x['result'] or 'pending'}")


if __name__ == "__main__":
    main()
