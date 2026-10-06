"""POST THE UNIT PLAYS THE NIGHT BEFORE (8 PM PT) OR AT 8 AM PT ON GAME DAY? (the owner, 10/6: "we want the best lines
and accurate picks"). Report only - nothing here touches a pick, a weight, units or the posting time. No network, no
paid odds re-pull: only what the repo already holds.

Two questions, per sport, favorites and dogs apart:
  A. PRICE - for the sides the engine would take, is the price at ~8 PM the night before better than at ~8 AM on game
     day (and than the close)? Cents of line and the ROI difference (graded on the real result at each price).
  B. ACCURACY / OVERNIGHT NEWS - how often does something happen between the night look and the morning look that would
     have changed or killed the pick (the side's price running 20+ cents against it = news, a QB ruled out overnight
     in the NFL injury history, the read no longer beating the morning price), and what did those picks do? Does the
     night board (the sides the engine would post at 8 PM) win less than the morning board (the sides at 8 AM)?

What the repo holds (honest inventory):
  1. FOOTBALL (NFL + college, 2020-26): the paid, time-stamped, book-by-book moneyline history
     (data/sports/odds_history). It was pulled at fixed hours - NFL Tue / Thu / Sat ~17:00Z (10 AM PT) and Sunday
     ~14:00Z (7 AM PT); college Tue / Thu ~17:00Z and Saturday ~13:00Z (6 AM PT). So the "morning" look IS the 8 AM
     board (give or take an hour), but there is NO 8 PM-the-night-before look: the nearest earlier snapshot is Saturday
     10 AM PT for a Sunday NFL game (~21 hours before the morning look) and Thursday 10 AM PT for a Saturday college
     game (~44 hours). The study uses that nearest look as "the night before" and says so - it is EARLIER than 8 PM,
     so it holds more overnight-news risk than a real 8 PM post would, not less.
  2. Our own hourly snapshots (data/sports/line_history, since 10/1/2026 - NHL / MLB / NFL / college): a real 8 PM PT
     the-night-before price vs the 8 AM PT price vs the close, a few dozen games per sport.
  3. NHL + MLB game files, 2023-26: every game's OPENING line (NHL: up ~38 hours ahead; MLB: checked here against our
     hourly snapshots) and its CLOSE - the overnight number vs puck drop / first pitch over thousands of games.
  4. Our real posted picks (data/sports/pick_journal.json + moves.json) where our hourly history holds a night price.
  5. NFL injury reports with a time stamp (data/sports/injuries/nfl.csv.gz, nflverse): a QB ruled Out between the
     night look and the morning look.

The engine's side is the same BLIND proxy the early-football and hockey timing studies use: each season graded by
sports_model tuned only on the 3 seasons before it, game-day inputs (injuries / key player) zeroed, and the side is
where that read beats the no-vig price at that moment by 3%+ inside the board's play band (-150..+220). It is not the
real board (the dog score, the gates), so it says what happens to the KIND of side the engine likes.

Run: python tools/night_vs_morning_study.py  -> prints the report, saves results/night_vs_morning_study.json"""
import csv
import glob
import gzip
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd                  # noqa: E402
import sports_model as sm                 # noqa: E402
import early_football_study as ef         # noqa: E402

PT = ZoneInfo("America/Los_Angeles")
ET = ZoneInfo("America/New_York")
EDGE = 0.03                               # the blind read beats the no-vig price by this much = "the engine's side"
PLAY_BAND = (-150, 220)
NEWS_CENTS = 20                           # a 20+ cent overnight move against the side = something happened
FOOTBALL = {"nfl": "americanfootball_nfl", "ncaaf": "americanfootball_ncaaf"}
SEASON_START = {"nfl": "07-01", "ncaaf": "07-01", "nhl": "08-01", "mlb": "01-01", "nba": "08-01"}
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "night_vs_morning_study.json")
NFL_ABBR = {"ARI": "22", "ATL": "1", "BAL": "33", "BUF": "2", "CAR": "29", "CHI": "3", "CIN": "4", "CLE": "5", "DAL": "6",
            "DEN": "7", "DET": "8", "GB": "9", "HOU": "34", "IND": "11", "JAX": "30", "KC": "12", "LA": "14", "LAR": "14",
            "LAC": "24", "LV": "13", "OAK": "13", "MIA": "15", "MIN": "16", "NE": "17", "NO": "18", "NYG": "19", "NYJ": "20",
            "PHI": "21", "PIT": "23", "SEA": "26", "SF": "25", "TB": "27", "TEN": "10", "WAS": "28"}


def _t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def cents(o):
    """American odds on one scale (-110 -> -10, +110 -> +10) so a move across even money counts right. Higher = longer."""
    return o - 100 if o > 0 else o + 100


def season_of(lg, start):
    y = int(start[:4])
    return y if start[5:10] >= SEASON_START[lg] else y - 1


def se_mean(xs):
    return statistics.pstdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0


def side_p(h, a, side):
    """The no-vig win chance of one side from a home / away price pair."""
    m = sd.no_vig(h, a)
    return m if side == "home" else 1 - m


def in_band(o):
    return PLAY_BAND[0] <= o <= PLAY_BAND[1]


def pt_date(dt):
    return dt.astimezone(PT).date()


def at_pt(day, hour):
    """The UTC moment of `hour` o'clock PT on `day`."""
    return datetime.combine(day, datetime.min.time(), PT).replace(hour=hour).astimezone(timezone.utc)


def pick_windows(snaps, start, min_gap_h=8.0, max_ahead_h=60.0, fair=lambda days: True):
    """snaps: [(days before kickoff, ...)] -> (morning snapshot, night snapshot) or (None, None).
    The MORNING look = the latest snapshot on the game's own Pacific calendar date, before kickoff. The NIGHT look =
    the latest earlier snapshot at least `min_gap_h` hours before the morning one, inside `max_ahead_h` of kickoff and
    posted after both teams' last games ended (fair)."""
    st = _t(start)
    day = pt_date(st)
    morning = [x for x in snaps if 0.02 <= x[0] and pt_date(st - timedelta(days=x[0])) == day]
    if not morning:
        return None, None
    m = min(morning, key=lambda x: x[0])
    night = [x for x in snaps if x[0] * 24 >= m[0] * 24 + min_gap_h and x[0] * 24 <= max_ahead_h and fair(x[0])]
    if not night:
        return m, None
    return m, min(night, key=lambda x: x[0])


def returns(rows, key):
    return [(dec(r[key]) - 1) if r["won"] else -1.0 for r in rows]


def summarize(rows):
    """rows with night / morning / close prices + won -> the price moves and the ROI at each moment."""
    if not rows:
        return None
    n = len(rows)
    nm = [cents(r["morning"]) - cents(r["night"]) for r in rows]
    nc = [cents(r["close"]) - cents(r["night"]) for r in rows]
    mc = [cents(r["close"]) - cents(r["morning"]) for r in rows]
    rn, rm, rc = returns(rows, "night"), returns(rows, "morning"), returns(rows, "close")
    gain = [a - b for a, b in zip(rn, rm)]                      # what the night price was worth vs the morning one
    by = defaultdict(list)
    for r, g in zip(rows, gain):
        by[r["season"]].append(g)
    seasons = {str(s): [len(v), round(statistics.mean(v), 4)] for s, v in sorted(by.items())}
    up = sum(1 for v in seasons.values() if v[1] > 0)
    return {"n": n, "won": round(sum(r["won"] for r in rows) / n, 3),
            "night_to_morning_cents": round(statistics.mean(nm), 1), "se_cents": round(se_mean(nm), 1),
            "night_to_close_cents": round(statistics.mean(nc), 1), "morning_to_close_cents": round(statistics.mean(mc), 1),
            "morning_longer": round(sum(1 for x in nm if x > 0) / n, 3), "morning_shorter": round(sum(1 for x in nm if x < 0) / n, 3),
            "against_20_plus": round(sum(1 for x in nm if x <= -NEWS_CENTS) / n, 3),
            "toward_20_plus": round(sum(1 for x in nm if x >= NEWS_CENTS) / n, 3),
            "roi_night": round(statistics.mean(rn), 4), "se_roi": round(se_mean(rn), 4),
            "roi_morning": round(statistics.mean(rm), 4), "roi_close": round(statistics.mean(rc), 4),
            "night_vs_morning_roi": round(statistics.mean(gain), 4), "se_gain": round(se_mean(gain), 4),
            "seasons_up": f"{up}/{len(seasons)}", "by_season": seasons}


def grade_at(rows, key):
    """A board graded at one moment only (the morning board at the morning price, a night-only pick at its night price)."""
    if not rows:
        return None
    r = returns(rows, key)
    return {"n": len(rows), "won": round(sum(x["won"] for x in rows) / len(rows), 3), "roi": round(statistics.mean(r), 4),
            "se": round(se_mean(r), 4), "roi_close": round(statistics.mean(returns(rows, "close")), 4)}


def boards(rows):
    """From every side with a night and a morning price + the blind read: the NIGHT board (the engine's side at the night
    price), the MORNING board (its side at the morning price), what overnight news did to the night picks, and the
    picks that exist at only one of the two times."""
    night = [r for r in rows if r["edge_n"] >= EDGE and in_band(r["night"])]
    morning = [r for r in rows if r["edge_m"] >= EDGE and in_band(r["morning"])]
    both_ids = {(r["id"], r["side"]) for r in morning}
    only_night = [r for r in night if (r["id"], r["side"]) not in both_ids]
    night_ids = {(r["id"], r["side"]) for r in night}
    only_morning = [r for r in morning if (r["id"], r["side"]) not in night_ids]
    mkt = [r for r in rows if in_band(r["night"])]        # (a -2400 favorite moving to -1200 is 1,200 'cents' of nothing)
    out = {"all_sides": {"what": f"every side priced {PLAY_BAND[0]}..+{PLAY_BAND[1]} at the night look",
                         "all": summarize(mkt), "favorites": summarize([r for r in mkt if r["fav"]]),
                         "dogs": summarize([r for r in mkt if not r["fav"]])},
           "night_board": {"rule": f"blind read beats the no-vig NIGHT price by {EDGE:.0%}, price {PLAY_BAND[0]}..+{PLAY_BAND[1]}",
                           "all": summarize(night), "favorites": summarize([r for r in night if r["fav"]]),
                           "dogs": summarize([r for r in night if not r["fav"]]),
                           "big_edge_6pct": summarize([r for r in night if r["edge_n"] >= 0.06])},
           "morning_board": {"rule": f"blind read beats the no-vig MORNING price by {EDGE:.0%}",
                             "all": grade_at(morning, "morning"), "favorites": grade_at([r for r in morning if r["fav"]], "morning"),
                             "dogs": grade_at([r for r in morning if not r["fav"]], "morning")},
           "only_at_night": {"what": "a night pick the morning price no longer justifies (the read's edge fell under 3% or the price left the band)",
                             "all": grade_at(only_night, "night"), "favorites": grade_at([r for r in only_night if r["fav"]], "night"),
                             "dogs": grade_at([r for r in only_night if not r["fav"]], "night")},
           "only_in_morning": {"what": "a side the engine would take only at the morning price (it drifted into value overnight)",
                               "all": grade_at(only_morning, "morning"), "favorites": grade_at([r for r in only_morning if r["fav"]], "morning"),
                               "dogs": grade_at([r for r in only_morning if not r["fav"]], "morning")},
           "overnight_news": {}}
    nw = out["overnight_news"]
    against = [r for r in night if cents(r["morning"]) - cents(r["night"]) <= -NEWS_CENTS]
    toward = [r for r in night if cents(r["morning"]) - cents(r["night"]) >= NEWS_CENTS]
    flat = [r for r in night if abs(cents(r["morning"]) - cents(r["night"])) < NEWS_CENTS]
    nw["ran_against_20_plus"] = {"share": round(len(against) / len(night), 3) if night else None, **(grade_at(against, "night") or {})}
    nw["ran_toward_20_plus"] = {"share": round(len(toward) / len(night), 3) if night else None, **(grade_at(toward, "night") or {})}
    nw["under_20"] = grade_at(flat, "night")
    nw["read_dead_by_morning"] = {"share": round(sum(1 for r in night if r["edge_m"] < 0) / len(night), 3) if night else None,
                                  **(grade_at([r for r in night if r["edge_m"] < 0], "night") or {})}
    if any("qb_out" in r for r in night):
        q = [r for r in night if r.get("qb_out")]
        them = [r for r in night if r.get("opp_qb_out")]
        nw["qb_ruled_out_overnight_our_side"] = {"share": round(len(q) / len(night), 3), **(grade_at(q, "night") or {})}
        nw["qb_ruled_out_overnight_their_side"] = {"share": round(len(them) / len(night), 3), **(grade_at(them, "night") or {})}
        anyo = [r for r in night if r.get("outs_overnight")]
        nw["any_player_ruled_out_overnight_our_side"] = {"share": round(len(anyo) / len(night), 3), **(grade_at(anyo, "night") or {})}
    return out


# ------------------------------------------------------------------ 1. football: the paid time-stamped history
def nfl_injury_index():
    """{(season, team id): [(date_modified, position, status)]} for Out / Doubtful rows of the NFL injury history."""
    path = os.path.join(sd.DATA, "injuries", "nfl.csv.gz")
    idx = defaultdict(list)
    if not os.path.exists(path):
        return idx
    with gzip.open(path, "rt") as f:
        for r in csv.DictReader(f):
            if r.get("game_type") != "REG" or r.get("team") not in NFL_ABBR or r.get("report_status") not in ("Out", "Doubtful"):
                continue
            try:
                when = _t(r["date_modified"])
            except (KeyError, ValueError):
                continue
            idx[(int(r["season"]), NFL_ABBR[r["team"]])].append((when, r.get("position"), r["report_status"]))
    for v in idx.values():
        v.sort()
    return idx


def football(lg):
    games = sd.load_games(lg)
    pr, _ = ef.match(ef.snapshots(FOOTBALL[lg]), games)
    ready = ef.ready_at(games, lg)
    inj = nfl_injury_index() if lg == "nfl" else {}
    rows, gaps, covered = [], [], defaultdict(int)
    for season in ef.SEASONS + (2026,):
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
            m, n = pick_windows(pr[g["id"]], g["start"], fair=lambda d, gid=g["id"], st=g["start"]: ef.fair(ready, gid, st, d))
            if not m or not n:
                continue
            gap = (n[0] - m[0]) * 24
            gaps.append(gap)
            covered[_t(g["start"]).astimezone(PT).strftime("%a")] += 1
            own_h = sm.own_p(p, {**f, "inj": 0.0, "key": 0.0})
            t_night, t_morn = _t(g["start"]) - timedelta(days=n[0]), _t(g["start"]) - timedelta(days=m[0])
            for side, opp in (("home", "away"), ("away", "home")):
                own = own_h if side == "home" else 1 - own_h
                pn = n[1] if side == "home" else n[2]
                pm = m[1] if side == "home" else m[2]
                pc = ch if side == "home" else ca
                row = {"id": g["id"], "lg": lg, "season": season, "side": side, "won": (hs > as_) == (side == "home"),
                       "night": pn, "morning": pm, "close": pc, "fav": side_p(n[1], n[2], side) > 0.5,
                       "own": round(own, 3), "edge_n": own - side_p(n[1], n[2], side), "edge_m": own - side_p(m[1], m[2], side),
                       "gap_h": round(gap, 1)}
                if lg == "nfl":
                    mine = [x for x in inj.get((season, g[side]), []) if t_night < x[0] <= t_morn]
                    theirs = [x for x in inj.get((season, g[opp]), []) if t_night < x[0] <= t_morn]
                    row["qb_out"] = any(x[1] == "QB" for x in mine)
                    row["opp_qb_out"] = any(x[1] == "QB" for x in theirs)
                    row["outs_overnight"] = len(mine)
                rows.append(row)
    res = boards(rows)
    res["games"] = len(rows) // 2
    res["night_look_hours_before_morning_look"] = {"avg": round(statistics.mean(gaps), 1), "min": round(min(gaps), 1),
                                                   "max": round(max(gaps), 1)} if gaps else None
    res["games_by_kickoff_day"] = dict(covered)
    res["note"] = ("the paid pull has no 8 PM-the-night-before look: the 'night' price here is the nearest earlier snapshot "
                   "(NFL Sunday games: Saturday ~10 AM PT; Thursday games: Tuesday; college Saturday games: Thursday ~10 AM PT), "
                   "the 'morning' price is the game-day snapshot (NFL Sunday ~7 AM PT, college Saturday ~6 AM PT)")
    return res


# ------------------------------------------------------------------ 2. our own hourly snapshots (since 10/1/2026)
def line_history():
    hist = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(sd.LINE_HIST_DIR, "*.jsonl"))):
        with open(f) as fh:
            for ln in fh:
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if r.get("t") and r.get("s") and r["t"] < r["s"] and sm._int(r.get("h")) is not None and sm._int(r.get("a")) is not None:
                    hist[r["g"]].append((r["t"], sm._int(r["h"]), sm._int(r["a"])))
    for v in hist.values():
        v.sort()
    return hist


def price_at(snaps, when):
    best = None
    for t, h, a in snaps:
        if _t(t) <= when:
            best = (h, a)
    return best


def blind_reads(games, lg, season):
    """{game id: blind home read} for one season's games, from a model tuned on the 3 seasons before it."""
    lo = f"{season}-{SEASON_START[lg]}"
    learn = {k: g for k, g in games.items() if f"{season - 3}-{SEASON_START[lg]}" <= (g.get("start") or "") < lo}
    p = sm.tune(learn, lg)
    if not p or "w" not in p:
        return {}
    _, played = sm.replay(sm.finals(games, lg), p["k"], p["hfa"], lg)
    return {g["id"]: sm.own_p(p, {**f, "inj": 0.0, "key": 0.0}) for g, f, *_ in played if g["start"] >= lo}


def hourly(lg, hist, games, reads):
    rows, legs, opens = [], [], []
    for gid, snaps in hist.items():
        if not gid.startswith(lg + ":"):
            continue
        g = games.get(gid)
        if not g or g.get("status") != "final" or (g.get("stype") or "?") not in sd.REAL or gid not in reads:
            continue
        start = _t(g["start"])
        day = pt_date(start)
        night, morn = at_pt(day - timedelta(days=1), 20), at_pt(day, 8)
        if start <= morn + timedelta(hours=1):
            continue
        pn, pm = price_at(snaps, night), price_at(snaps, morn)
        if not pn or not pm:
            continue
        close = (snaps[-1][1], snaps[-1][2])
        first = (snaps[0][1], snaps[0][2])
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (TypeError, ValueError):
            continue
        if hs == as_:
            continue
        ho, ao = sm._int(g.get("ml_home_open")), sm._int(g.get("ml_away_open"))
        if ho is not None and ao is not None:
            opens.append({"open_is_first_snap": (ho, ao) == first, "first_snap_hours_ahead": round((start - _t(snaps[0][0])).total_seconds() / 3600, 1)})
        fav_i = 0 if sd.no_vig(*pn) > 0.5 else 1
        if pn[fav_i] >= -250:                                  # (a board-sized game; a -2400 favorite's cents mean nothing)
            legs.append({"first_to_night": cents(pn[fav_i]) - cents(first[fav_i]), "night_to_morning": cents(pm[fav_i]) - cents(pn[fav_i]),
                         "morning_to_close": cents(close[fav_i]) - cents(pm[fav_i])})
        own_h = reads[gid]
        for i, side in enumerate(("home", "away")):
            own = own_h if side == "home" else 1 - own_h
            rows.append({"id": gid, "lg": lg, "season": season_of(lg, g["start"]), "side": side,
                         "won": (hs > as_) == (side == "home"), "night": pn[i], "morning": pm[i], "close": close[i],
                         "fav": side_p(*pn, side) > 0.5, "own": round(own, 3),
                         "edge_n": own - side_p(*pn, side), "edge_m": own - side_p(*pm, side)})
    res = boards(rows) if rows else {}
    res["games"] = len(rows) // 2
    if legs:
        res["favorite_move_by_leg_cents_abs"] = {k: round(statistics.mean(abs(x[k]) for x in legs), 1) for k in legs[0]}
        res["favorite_move_by_leg_cents_signed"] = {k: round(statistics.mean(x[k] for x in legs), 1) for k in legs[0]}
        res["overnight_moves_20_plus_share"] = round(sum(1 for x in legs if abs(x["night_to_morning"]) >= NEWS_CENTS) / len(legs), 3)
    if opens:
        res["game_file_open_vs_our_first_snapshot"] = {"games": len(opens), "same": sum(1 for o in opens if o["open_is_first_snap"]),
                                                       "first_snap_hours_ahead_median": statistics.median(o["first_snap_hours_ahead"] for o in opens)}
    return res


# ------------------------------------------------------------------ 3. NHL / MLB: the opener vs the close, 2023-26
def open_close(lg, games, seasons):
    rows = []
    reads = {}
    for s in seasons:
        reads.update(blind_reads(games, lg, s))
    for g in sm.finals(games, lg):
        if g["id"] not in reads or season_of(lg, g["start"]) not in seasons:
            continue
        h, a, ho, ao = (sm._int(g.get(k)) for k in ("ml_home", "ml_away", "ml_home_open", "ml_away_open"))
        if None in (h, a, ho, ao):
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (TypeError, ValueError):
            continue
        if hs == as_:
            continue
        own_h = reads[g["id"]]
        for side, o, c in (("home", ho, h), ("away", ao, a)):
            own = own_h if side == "home" else 1 - own_h
            # "night" = the opener, "morning" = the close here (no 8 AM mark in the game files): one leg only
            rows.append({"id": g["id"], "lg": lg, "season": season_of(lg, g["start"]), "side": side,
                         "won": (hs > as_) == (side == "home"), "night": o, "morning": c, "close": c,
                         "fav": side_p(ho, ao, side) > 0.5, "own": round(own, 3),
                         "edge_n": own - side_p(ho, ao, side), "edge_m": own - side_p(h, a, side)})
    res = boards(rows)
    res["games"] = len(rows) // 2
    res["note"] = "night = the game file's OPENING line, morning = the CLOSE (the game files hold no 8 AM mark); the hourly part says how much of that move is overnight"
    return res


# ------------------------------------------------------------------ 4. our real posted picks
def posted(hist, games):
    try:
        with open(os.path.join(sd.DATA, "pick_journal.json")) as f:
            journal = json.load(f)
    except (OSError, ValueError):
        journal = []
    try:
        with open(os.path.join(sd.DATA, "moves.json")) as f:
            legs = (json.load(f).get("clv") or {}).get("legs") or []
    except (OSError, ValueError):
        legs = []
    closes = {(lg["game_id"], lg["team"]): lg.get("close") for lg in legs if lg.get("market") == "ml"}
    out = []
    for r in journal:
        if r.get("market") != "ml" or r.get("odds") is None or r.get("result") not in ("won", "lost"):
            continue
        g = games.get(r["game_id"])
        snaps = hist.get(r["game_id"])
        if not g or not snaps:
            continue
        start = _t(g["start"])
        night = at_pt(pt_date(start) - timedelta(days=1), 20)
        pn = price_at(snaps, night)
        i = 0 if r.get("home") else 1
        pc = closes.get((r["game_id"], r["team"]))
        if pc is None:
            pc = snaps[-1][1 + i]
        out.append({"date": r["date"], "league": r["league"], "kind": r["kind"], "units": r.get("units"), "team": r["team"],
                    "night_8pm": pn[i] if pn else None, "posted": int(r["odds"]), "close": int(pc), "won": r["result"] == "won",
                    "night_snap_hours_before_start": round((start - _t(snaps[0][0])).total_seconds() / 3600, 1) if not pn else None})
    with_night = [x for x in out if x["night_8pm"] is not None]
    summ = None
    if with_night:
        mv = [cents(x["posted"]) - cents(x["night_8pm"]) for x in with_night]
        rn = [(dec(x["night_8pm"]) - 1) if x["won"] else -1.0 for x in with_night]
        rp = [(dec(x["posted"]) - 1) if x["won"] else -1.0 for x in with_night]
        units = [x for x in with_night if x["units"]]
        summ = {"n": len(with_night), "night_to_posted_cents": round(statistics.mean(mv), 1),
                "posted_longer": sum(1 for m in mv if m > 0), "posted_shorter": sum(1 for m in mv if m < 0),
                "roi_at_night": round(statistics.mean(rn), 4), "roi_at_posted": round(statistics.mean(rp), 4),
                "unit_plays": {"n": len(units), "night_to_posted_cents": round(statistics.mean(cents(x["posted"]) - cents(x["night_8pm"]) for x in units), 1)} if units else None}
    return {"summary": summ, "picks": out}


def main():
    res = {"ran": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "football_paid_history": {}, "hourly_since_oct_1": {},
           "open_vs_close_2023_26": {}}
    for lg in ("nfl", "ncaaf"):
        res["football_paid_history"][lg] = football(lg)
    hist = line_history()
    all_games = {}
    for lg in ("nhl", "mlb", "nfl", "ncaaf"):
        games = sd.load_games(lg)
        all_games.update(games)
        reads = blind_reads(games, lg, 2026)
        res["hourly_since_oct_1"][lg] = hourly(lg, hist, games, reads)
        if lg in ("nhl", "mlb"):
            res["open_vs_close_2023_26"][lg] = open_close(lg, games, (2023, 2024, 2025, 2026))
    res["posted_picks"] = posted(hist, all_games)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1)
    report(res)
    return res


def _s(name, s):
    if not s:
        return f"    {name}: none"
    if "night_to_morning_cents" in s:
        return (f"    {name}: n {s['n']}, won {s['won']:.1%}; night->morning {s['night_to_morning_cents']:+.1f} cents (SE {s['se_cents']:.1f}; "
                f"morning longer {s['morning_longer']:.0%} / shorter {s['morning_shorter']:.0%}; ran against 20+ {s['against_20_plus']:.0%}, "
                f"toward 20+ {s['toward_20_plus']:.0%}), night->close {s['night_to_close_cents']:+.1f}, morning->close {s['morning_to_close_cents']:+.1f}; "
                f"ROI at night {s['roi_night']:+.1%} (SE {s['se_roi']:.1%}) / morning {s['roi_morning']:+.1%} / close {s['roi_close']:+.1%} "
                f"-> night worth {s['night_vs_morning_roi']:+.1%} (SE {s['se_gain']:.1%}), seasons up {s['seasons_up']}")
    share = f" share {s['share']:.0%}," if s.get("share") is not None else ""
    if "n" not in s:
        return f"    {name}:{share} none"
    return f"    {name}:{share} n {s['n']}, won {s['won']:.1%}, ROI {s['roi']:+.1%} (SE {s['se']:.1%}), the same bets at the close {s['roi_close']:+.1%}"


def _boards(b):
    print(f"  the market ({b['all_sides']['what']}):")
    for k in ("all", "favorites", "dogs"):
        print(_s(k, b["all_sides"][k]))
    print(f"  THE NIGHT BOARD ({b['night_board']['rule']}):")
    for k in ("all", "favorites", "dogs", "big_edge_6pct"):
        print(_s(k, b["night_board"][k]))
    print(f"  THE MORNING BOARD ({b['morning_board']['rule']}), graded at the morning price:")
    for k in ("all", "favorites", "dogs"):
        print(_s(k, b["morning_board"][k]))
    print(f"  only at night ({b['only_at_night']['what']}):")
    for k in ("all", "favorites", "dogs"):
        print(_s(k, b["only_at_night"][k]))
    print(f"  only in the morning ({b['only_in_morning']['what']}):")
    for k in ("all", "favorites", "dogs"):
        print(_s(k, b["only_in_morning"][k]))
    print("  overnight news on the night picks:")
    for k, v in b["overnight_news"].items():
        print(_s(k, v))


def report(res):
    print(f"NIGHT (8 PM PT) vs MORNING (8 AM PT) POSTING STUDY ({res['ran']})")
    for lg, b in res["football_paid_history"].items():
        g = b.get("night_look_hours_before_morning_look")
        print(f"\n1. {lg.upper()} - the paid time-stamped history, 2020-26: {b['games']} games with a night look and a game-day look; "
              f"the night look is {g['avg'] if g else '?'} hours before the morning look on average ({b['note']}); by kickoff day {b['games_by_kickoff_day']}")
        _boards(b)
    for lg, b in res["hourly_since_oct_1"].items():
        print(f"\n2. {lg.upper()} - our own hourly snapshots since 10/1/2026: {b.get('games', 0)} finished games with a real 8 PM PT night-before price and an 8 AM PT price")
        if b.get("games"):
            _boards(b)
            print(f"  favorite's move by leg, avg |cents|: {b['favorite_move_by_leg_cents_abs']}, signed {b['favorite_move_by_leg_cents_signed']}; "
                  f"overnight moves of 20+ cents in {b['overnight_moves_20_plus_share']:.0%} of games")
            if b.get("game_file_open_vs_our_first_snapshot"):
                print(f"  the game file's opener vs our first hourly snapshot: {b['game_file_open_vs_our_first_snapshot']}")
    for lg, b in res["open_vs_close_2023_26"].items():
        print(f"\n3. {lg.upper()} - the opener vs the close, 2023-26 ({b['games']} games; {b['note']})")
        _boards(b)
    p = res["posted_picks"]
    print(f"\n4. OUR REAL POSTED PICKS with an 8 PM night-before price in our hourly history: {p['summary']}")
    for x in p["picks"]:
        print(f"    {x['date']} {x['league']} {x['kind']:5} {x['units']}u {x['team']:14} 8 PM {x['night_8pm']}  posted {x['posted']}  close {x['close']}  {'won' if x['won'] else 'lost'}")


if __name__ == "__main__":
    main()
