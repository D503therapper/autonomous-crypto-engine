"""THE D503 SPORTS ENGINE - daily picks board (PAPER only: pretend $100 per pick, no real bets).

Every hour (GitHub Actions, .github/workflows/sports.yml):
  1. sync games, scores and odds for NFL, NBA, MLB, NHL from ESPN;
  2. grade finished picks;
  3. retrain on new results, pull injuries, and post the board (2-leg, 3-leg, lock, dog of the day): from 6pm
     Pacific the night before, each play goes up once its games' key news is known (3h before at the latest);
  4. rebuild the phone dashboard (docs/sports/index.html).

    python sports.py            # one cycle
    python sports.py --repick   # redo today's board (e.g. after a rules change)
    SPORTS_POST_NOW=1 python sports.py   # post every play right now
"""
import itertools
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_breakdown
import sports_data as sd
import sports_model as sm
import sports_players as sp
import sports_news
import sports_weather

DATA = sd.DATA
PT = ZoneInfo("America/Los_Angeles")
START_BANKROLL = 1000.0
STAKE = 100.0
POST_FROM_HOUR_PT = 18         # a day's plays can be posted from 6pm Pacific the night before...
DEADLINE_MIN = 180             # ...as soon as everything that matters is known; if it never is, at the latest
                               # 3 hours before the play's first game (then only from games that are settled).
                               # A posted play is final: it never changes.
MIN_LEAD_MIN = 20              # only games starting at least this long after the board goes up
MIN_KNOWN = 5                  # both teams need this many rated games
MAX_FAV = -150                 # never a huge favorite: no moneyline leg shorter than this
LOCK_MAX_FAV = -120            # lock of the day: a moneyline no shorter than -120
DOG_MIN = 100                  # dog of the day: a plus-money underdog...
BIG_DOG = 200                  # ...a big dog (+200 and up) is never declined when it triggers: a real shot and major value:
BIG_DOG_MIN_P = 0.22           #    at least a 22% win chance on our numbers,
BIG_DOG_EXTRA_EDGE = 0.05      #    and value at least 5 points better than the best regular dog on the slate
MIN_EDGE = 0.01                # NEVER a filler: every leg, lock and dog must be real value on our numbers (1%+)...
                               # ...and have at least one reason; not enough of them on the slate = no play today
MAX_EXTRA_OUT = 1              # never back the more banged-up team: at most 1 more player out than the opponent
KINDS = [("two", "2-Leg of the Day"), ("three", "3-Leg of the Day"), ("eight", "8-Leg of the Day"),
         ("lock", "Lock of the Day"), ("dog", "Dog of the Day")]
# 8-leg: moneylines and spreads, every day across all sports (no big favorite: a favorite shorter than -150 only gets
# in on the spread). Value legs first; on a slate short on value the likeliest legs fill it. Over/unders stay out
# until the engine has studied totals.


# ---------------------------------------------------------------- state files
def _load(name, default):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    with open(p) as f:
        return json.load(f)


def _save(name, obj):
    p = os.path.join(DATA, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(p + ".tmp", p)


def american(dec):
    return round((dec - 1) * 100) if dec >= 2 else round(-100 / (dec - 1))


def fmt_american(a):
    return f"+{a}" if a > 0 else str(a)


def leg_label(leg):
    return f"{leg['team']} " + ("ML" if leg["market"] == "ml" else f"{leg['line']:+g}")


# ---------------------------------------------------------------- candidates
def _reasons(side, f, g, league, params):
    """Short plain-English reasons the engine likes this side, strongest first."""
    s = 1 if side == "home" else -1
    out = []
    if f["elo_pts"] * s >= 15:
        out.append((f["elo_pts"] * s / 40, "the stronger team"))
    if f["form"] * s >= 0.08:
        out.append((f["form"] * s * 4, "hotter recent form"))
    if f["rest"] * 7 * s >= 2:                        # a real rest gap only (one extra day means nothing)
        out.append((f["rest"] * 7 * s / 3, "better rested"))
    if f["b2b"] * s > 0:
        out.append((0.8, "opponent on a back-to-back"))
    if f["inj"] * 5 * s >= 1:
        out.append((f["inj"] * 5 * s / 3, "opponent missing key players"))
    if sm.line_move(g) * s >= 0.08:
        out.append((sm.line_move(g) * s * 5, "sharp money moving this way"))
    # situational patterns: only when 10 seasons of results say the pattern helps this side
    w = (params or {}).get("weights", {})
    for name, label in (("revenge", "revenge game"), ("letdown", "letdown spot for the opponent"),
                        ("bye", "coming off a bye"), ("short", "opponent on a short week")):
        if f.get(name, 0) * s > 0 and w.get(name, 0) >= 0.1:
            out.append((0.4 + w[name], label))
    for name, label in (("alt", "altitude edge"), ("cold", "cold-weather edge"), ("weather", "nasty weather helps us"),
                        ("travel", "opponent's body clock is off")):
        if f.get(name, 0) * s > 0.05 and w.get(name, 0) >= 0.1:
            out.append((0.4 + w[name] * abs(f[name]), label))
    if w.get("letdown", 0) <= -0.1 and f.get("letdown", 0) * s < 0:      # blowout winners keep rolling (NFL/NBA)
        out.append((0.4 - w["letdown"], "rolling off a blowout win"))
    if f.get("key", 0) * s >= 0.4:
        out.append((f["key"] * s, {"mlb": "better starting pitcher", "nhl": "hotter goalie"}.get(league, "better QB play lately")))
    out.sort(key=lambda r: -r[0])
    return [r[1] for r in out[:3]]


def waiting_on(g, injuries):
    """What still isn't known for a game (empty when it's safe to post): a starting pitcher, a key player's status."""
    out = []
    if g["league"] == "mlb":
        out += [f"{g[side + '_name']} starting pitcher" for side in ("away", "home") if not g.get("sp_" + side)]
    inj = (injuries or {}).get(g["league"])
    for side in ("away", "home"):
        out += [f"{n} ({pos}) questionable" if pos else f"{n} questionable"
                for n, pos, _ in sd.team_unsure(inj, g[side], g[side + "_name"], g["league"])[:2]]
    return out


def candidates(games, model, now=None, day=None, injuries=None):
    """Every bettable side on the day's (Pacific) slate: moneylines, plus spreads in NFL/NCAAF/NBA."""
    now = now or datetime.now(timezone.utc)
    day = day or now.astimezone(PT).date()
    elo = sm.ratings(games, model)
    out = []
    for g in games.values():
        if g["status"] != "pre" or g.get("ml_home", "") == "" or g["league"] not in sd.LEAGUES \
                or (g.get("stype") or "?") not in sd.REAL:
            continue
        start = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        if start.astimezone(PT).date() != day or start < now + timedelta(minutes=MIN_LEAD_MIN):
            continue
        lg = g["league"]
        params = model["params"].get(lg) or sm.default_params(lg)
        f = elo[lg].features(g)
        if f["known"] < MIN_KNOWN:
            continue
        mkt = sm.market_p(g)
        inj = (injuries or {}).get(lg)
        key_out = {side: sd.team_key_out(inj, g[side], g[side + "_name"], lg) for side in ("home", "away")}
        n_out = {side: len(sd.team_injuries(inj, g[side], g[side + "_name"])) for side in ("home", "away")}
        # a missing starting QB / goalie is news the ratings can't see. The line prices the backup (a solid
        # one barely moves it, a bad one moves it a lot), so on this game go by the market + where sharp money goes
        ph = sm.sigmoid(sm.logit(mkt) + params.get("move_w", 0) * sm.line_move(g)) \
            if key_out["home"] or key_out["away"] else sm.final_p(params, f, g)
        # the engine's own read without the line move: sharp money alone can never carry a pick
        ph_own = mkt if key_out["home"] or key_out["away"] else sm.final_p({**params, "move_w": 0.0}, f, g)
        waiting = waiting_on(g, injuries)
        news = sports_news.load()
        drama = {side: sports_news.drama(news, lg, g[side]) for side in ("home", "away")}
        for side in ("home", "away"):
            other = "away" if side == "home" else "home"
            if n_out[side] - n_out[other] > MAX_EXTRA_OUT:
                continue                                  # never back the more banged-up team
            team, opp = (g["home_name"], g["away_name"]) if side == "home" else (g["away_name"], g["home_name"])
            base = {"game_id": g["id"], "league": lg, "side": side, "team": team, "opp": opp,
                    "home": side == "home", "start": g["start"], "reasons": _reasons(side, f, g, lg, params),
                    "waiting": waiting, "intl": str(g.get("intl")) == "1", "country": g.get("country", ""),
                    "our_drama": drama[side][:1], "their_drama": drama["away" if side == "home" else "home"][:1]}
            if base["their_drama"]:
                base["reasons"] = base["reasons"] + [f"opponent drama: {base['their_drama'][0]['kind']}"]
            odds = int(g[f"ml_{side}"])
            p = ph if side == "home" else 1 - ph
            p_own = ph_own if side == "home" else 1 - ph_own
            out.append({**base, "market": "ml", "line": None, "odds": odds, "dec": sd.decimal(odds), "p": p,
                        "p_market": mkt if side == "home" else 1 - mkt, "edge": p * sd.decimal(odds) - 1,
                        "edge_own": p_own * sd.decimal(odds) - 1})
            if lg in sm.SPREAD_LEAGUES and g.get("spread_home", "") != "":
                line = float(g["spread_home"]) * (1 if side == "home" else -1)
                sodds = sm._int(g.get(f"spread_{side}_odds")) or -110
                pc = sm.cover_p(params, f, g, side)
                if pc is not None:
                    out.append({**base, "market": "spread", "line": line, "odds": sodds, "dec": sd.decimal(sodds),
                                "p": pc, "p_market": 1 / sd.decimal(sodds), "edge": pc * sd.decimal(sodds) - 1})
    return out


INTL_MIN_EDGE = 0.02           # overseas games are weird: they need twice the usual value


def good(c):
    """A real play: value on our numbers - from the engine's own read, not just the line moving - and at least one
    reason. Anything else is filler, and filler never goes up."""
    need = INTL_MIN_EDGE if c.get("intl") or c.get("our_drama") else MIN_EDGE   # overseas / our own drama: 2x value
    return c["edge"] >= need and c.get("edge_own", c["edge"]) >= need and bool(c.get("reasons"))


def _parlay(cands, n, top=40):
    """Best n-leg parlay: good legs only, one leg per game, no huge favorites; the highest chance to hit
    (no payout chasing - a proven engine over big tickets)."""
    pool = sorted((c for c in cands if good(c) and c["odds"] >= MAX_FAV), key=lambda c: -c["edge"])[:top]
    if n > 3:                                     # big parlays: the likeliest good leg per game, then the likeliest games
        per_game = {}
        fill = sorted((c for c in cands if c["odds"] >= MAX_FAV and not good(c) and c["market"] == "ml"),   # spreads: value only
                      key=lambda c: (not c.get("reasons"), -c["p"]))            # the 8-leg always goes up: if the
        for c in pool + fill:                                                   # slate's short on value, the likeliest
            if c["game_id"] in per_game and good(per_game[c["game_id"]]) and not good(c):   # legs fill it
                continue
            if c["game_id"] not in per_game or (c["p"], c["edge"]) > (per_game[c["game_id"]]["p"], per_game[c["game_id"]]["edge"]):
                per_game[c["game_id"]] = c
        legs = sorted(per_game.values(), key=lambda c: (not good(c), -c["p"], -c["edge"]))[:n]   # value legs first
        if len(legs) < n:
            return None
        dec, p = 1.0, 1.0
        for c in legs:
            dec *= c["dec"]
            p *= c["p"]
        return {"legs": legs, "dec": dec, "p_hit": p}
    best = None
    for combo in itertools.combinations(pool, n):
        if len({c["game_id"] for c in combo}) < n:
            continue
        dec, p = 1.0, 1.0
        for c in combo:
            dec *= c["dec"]
            p *= c["p"]
        key = (p, p * dec)
        if best is None or key > best[0]:
            best = (key, combo, dec, p)
    if not best:
        return None
    _, combo, dec, p = best
    return {"legs": list(combo), "dec": dec, "p_hit": p}


def make_board(cands, lock_game=None, allow_lean=False, avoid=()):
    """{kind: pick or None} following the owner's rules (lock_game: an already-posted lock's game, kept off the dog)."""
    board = {"two": _parlay(cands, 2), "three": _parlay(cands, 3), "eight": _parlay(cands, 8, top=80)}
    ml = [c for c in cands if c["market"] == "ml" and good(c)]
    locks = [c for c in ml if c["odds"] >= LOCK_MAX_FAV]
    lock = max(locks, key=lambda c: (c["p"], c["edge"])) if locks else None
    board["lock"] = {"legs": [lock], "dec": lock["dec"], "p_hit": lock["p"]} if lock else None
    taken = lock_game or (lock["game_id"] if lock else None)
    dogs = [c for c in ml if c["odds"] >= DOG_MIN and c["game_id"] != taken]
    regular = [c for c in dogs if c["odds"] < BIG_DOG]
    dog = max(regular, key=lambda c: c["edge"]) if regular else None
    big = [c for c in dogs if c["odds"] >= BIG_DOG and c["p"] >= BIG_DOG_MIN_P
           and c["edge"] >= (dog["edge"] if dog else 0) + BIG_DOG_EXTRA_EDGE]
    if big:
        dog = max(big, key=lambda c: c["edge"])
    board["dog"] = {"legs": [dog], "dec": dog["dec"], "p_hit": dog["p"]} if dog else None
    for kind, pick in list(board.items()):                  # during the day, a graded spot never sits empty: best lean
        if pick is None and allow_lean:
            board[kind] = lean([c for c in cands if c["game_id"] not in avoid], kind, taken)   # never a game we're already on
    return board


LEAN_MIN_P = {"two": 0.45, "three": 0.45, "lock": 0.50, "dog": 0.30}


def lean(cands, kind, taken=None):
    """The best available play when nothing clears the value bar: the closest thing to value on the slate, same rules
    (no big favorites, no games underway, never the banged-up side - candidates already filter those). Tagged LEAN."""
    ml = [c for c in cands if c["market"] == "ml" and c.get("reasons")]
    if kind == "lock":
        pool = [c for c in ml if c["odds"] >= LOCK_MAX_FAV and c["p"] >= LEAN_MIN_P["lock"]]
    elif kind == "dog":
        pool = [c for c in ml if c["odds"] >= DOG_MIN and c["p"] >= LEAN_MIN_P["dog"] and c["game_id"] != taken]
    elif kind in ("two", "three"):
        n = 2 if kind == "two" else 3
        best = {}
        for c in sorted((c for c in cands if c["odds"] >= MAX_FAV and c["p"] >= LEAN_MIN_P[kind]), key=lambda c: -c["edge"]):
            best.setdefault(c["game_id"], c)
        legs = sorted(best.values(), key=lambda c: -c["edge"])[:n]
        if len(legs) < n:
            return None
        dec, p = 1.0, 1.0
        for c in legs:
            dec *= c["dec"]
            p *= c["p"]
        return {"legs": legs, "dec": dec, "p_hit": p, "lean": True}
    else:
        return None
    if not pool:
        return None
    c = max(pool, key=lambda c: (c["edge"], c["p"]))
    return {"legs": [c], "dec": c["dec"], "p_hit": c["p"], "lean": True}


# ---------------------------------------------------------------- grading
def grade_leg(leg, g, now):
    """won / lost / push / void, or None while the game isn't over."""
    if g is None:
        return None
    if g["status"] == "void":
        return "void"
    if g["status"] != "final" or g["home_score"] == "":
        start = datetime.strptime(leg["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        return "void" if now - start > timedelta(days=4) else None
    hs, as_ = int(g["home_score"]), int(g["away_score"])
    margin = (hs - as_) if leg["side"] == "home" else (as_ - hs)
    if leg["market"] == "spread":
        margin += leg["line"]
    return "won" if margin > 0 else "lost" if margin < 0 else "push"


def grade(picks, games, now=None):
    now = now or datetime.now(timezone.utc)
    settled = []
    for pk in picks:
        if pk["status"] != "open":
            continue
        for leg in pk["legs"]:
            if leg.get("result") is None:
                leg["result"] = grade_leg(leg, games.get(leg["game_id"]), now)
                g = games.get(leg["game_id"])
                if leg["result"] and g:
                    leg["score"] = f'{g["away_name"]} {g["away_score"]} @ {g["home_name"]} {g["home_score"]}'
        res = [leg.get("result") for leg in pk["legs"]]
        if "lost" in res:
            pk["status"], pk["pnl"] = "lost", -pk["stake"]
        elif all(res):
            dec = 1.0
            for leg in pk["legs"]:
                if leg["result"] == "won":
                    dec *= leg["dec"]
            pk["status"] = "won" if "won" in res else "push"
            pk["pnl"] = round(pk["stake"] * (dec - 1), 2)
        else:
            continue
        pk["settled"] = now.strftime("%Y-%m-%dT%H:%MZ")
        settled.append(pk)
    return settled


# ---------------------------------------------------------------- the cycle
def _start(leg):
    return datetime.strptime(leg["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def first_start(games, day):
    """When the day's (Pacific) first real game starts, or None."""
    starts = [datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
              for g in games.values() if g.get("start") and g["status"] != "void" and (g.get("stype") or "?") in sd.REAL
              and g["league"] in sd.LEAGUES]
    starts = [t for t in starts if t.astimezone(PT).date() == day]
    return min(starts) if starts else None


def post_board(games, model, picks, now, day, force=False):
    """Post the day's plays. A play goes up as soon as none of its games is waiting on news (a starting
    pitcher, a questionable QB/goalie...); otherwise its card says what it's waiting on, and at the latest
    DEADLINE_MIN before its first game it is posted from settled games only. force posts everything now.
    A posted play is final. Returns the plays posted by this call."""
    iso = day.isoformat()
    picks[:] = [p for p in picks if not (p["status"] == "waiting" and p["date"] <= iso)]   # rebuilt every run
    posted = {}
    for p in picks:                  # the latest play of each kind today (a graded one gets replaced below)
        if p["date"] == iso:
            posted[p["kind"]] = p
    first = first_start(games, day)
    started = first is not None and now >= first and not force
    # the opening board goes up before the day's first game. After that, whenever a play is graded (it moves to the
    # results), a fresh one of the same kind goes up from the games that haven't started yet - picks all day long.
    todo = [k for k, _ in KINDS if (k not in posted and not started) or
            (k in posted and posted[k]["status"] in ("won", "lost", "push"))]
    if not todo:
        return []
    injuries = {lg: sd.fetch_injuries(lg) for lg in sd.LEAGUES}
    for g in games.values():
        if g["status"] != "pre" or not injuries.get(g["league"]):
            continue
        start = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        if start.astimezone(PT).date() != day:
            continue
        inj = injuries[g["league"]]
        for side in ("home", "away"):
            g[f"inj_{side}"] = len(sd.team_injuries(inj, g[side], g[f"{side}_name"]))
    cands = candidates(games, model, now, day, injuries)
    settled = [c for c in cands if not c["waiting"]]
    elo = None
    used = {t for p in picks if p["date"] == iso for l in p["legs"] for t in l.get("bd_tags", [])}   # the board's memory
    new = []
    for kind in todo:
        lock_game = posted["lock"]["legs"][0]["game_id"] if "lock" in posted and posted["lock"]["status"] == "open" else None
        replacing = kind in posted                            # the opening board is value only; replacements may lean
        avoid = {l["game_id"] for p in picks if p["date"] == iso and p["status"] == "open" for l in p["legs"]}
        best = make_board(cands, lock_game, allow_lean=replacing, avoid=avoid).get(kind)
        if not best:
            continue
        deadline = min(_start(l) for l in best["legs"]) - timedelta(minutes=DEADLINE_MIN)
        if force or all(not l["waiting"] for l in best["legs"]):
            b = best
        elif now >= deadline:
            b = make_board(settled, lock_game, allow_lean=replacing, avoid=avoid).get(kind)   # out of time: settled games
            if not b:
                continue
        else:
            wait = sorted({w for l in best["legs"] for w in l["waiting"]})
            picks.append({"date": iso, "kind": kind, "status": "waiting", "legs": [], "waiting": wait[:3],
                          "deadline": deadline.strftime("%Y-%m-%dT%H:%MZ")})
            continue
        for leg in b["legs"]:
            g = games[leg["game_id"]]
            other = "away" if leg["side"] == "home" else "home"
            for key, side, name in (("outs", leg["side"], leg["team"]), ("opp_outs", other, leg["opp"])):
                outs = sd.team_injuries(injuries.get(leg["league"]), g[side], name)
                leg[key] = [f"{n} ({pos})" if pos else n for n, pos, _ in outs[:4]]
            elo = elo or sm.ratings(games, model)
            same = next((l for p in picks + new if p["date"] == iso for l in p["legs"]
                         if l.get("bv") == sports_breakdown.VERSION and _same_leg(l, leg) and l is not leg), None)
            if same:                                  # the same pick reads the same everywhere it shows up
                leg["breakdown"], leg["bd_tags"], leg["reasons"] = same["breakdown"], same.get("bd_tags", []), same.get("reasons", leg.get("reasons"))
            else:
                leg["breakdown"] = sports_breakdown.breakdown(leg, games, elo, injuries, used)
            leg["public"] = sports_breakdown.public_side(leg, g)
            leg["bv"] = sports_breakdown.VERSION
        pk = {"date": iso, "kind": kind, "posted": now.strftime("%Y-%m-%dT%H:%MZ"),
              "round": sum(p["date"] == iso and p["kind"] == kind and p["status"] != "waiting" for p in picks) + 1,
              "legs": b["legs"], "dec": round(b["dec"], 4), "american": american(b["dec"]),
              "p_hit": round(b["p_hit"], 4), "stake": STAKE, "status": "open", "pnl": 0.0, "lean": bool(b.get("lean"))}
        picks.append(pk)
        posted[kind] = pk
        new.append(pk)
    return new


def _same_leg(a, b):
    return (a["game_id"], a["side"], a["market"], a.get("line")) == (b["game_id"], b["side"], b["market"], b.get("line"))


def add_breakdowns(games, model, picks):
    """(Re)write the breakdown of posted plays whose games haven't started, when it's missing or was written by an
    older breakdown version. Only the explanation changes - the pick itself never does."""
    legs = [l for p in picks if p["status"] == "open" for l in p["legs"]
            if l.get("bv") != sports_breakdown.VERSION and l["game_id"] in games and games[l["game_id"]]["status"] == "pre"]
    if not legs:
        return
    injuries = {lg: sd.fetch_injuries(lg) for lg in {l["league"] for l in legs}}
    redo = {id(l) for l in legs}
    used = {t for p in picks for l in p["legs"] if id(l) not in redo for t in l.get("bd_tags", [])}
    elo, done = sm.ratings(games, model), []
    for leg in legs:
        same = next((l for l in done if _same_leg(l, leg)), None)
        if same:                                      # the same pick reads the same everywhere it shows up
            leg["breakdown"], leg["bd_tags"], leg["reasons"] = same["breakdown"], same.get("bd_tags", []), same.get("reasons", leg.get("reasons"))
        else:
            leg["breakdown"] = sports_breakdown.breakdown(leg, games, elo, injuries, used)
        leg["public"] = sports_breakdown.public_side(leg, games[leg["game_id"]])
        leg["bv"] = sports_breakdown.VERSION
        done.append(leg)


def bankroll_series(picks):
    pts, bank = [], START_BANKROLL
    for pk in sorted((p for p in picks if p["status"] in ("won", "lost", "push")), key=lambda p: p["settled"]):
        bank += pk["pnl"]
        t = datetime.strptime(pk["settled"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).timestamp() * 1000
        pts.append((t, round(bank, 2)))
    return pts


def quick(now=None):
    """Fast pass right when games end (the live watcher calls it): today's + yesterday's final scores from ESPN,
    grade the picks, post any replacement picks, rebuild the dashboard. No history, no retraining (that's hourly)."""
    now = now or datetime.now(timezone.utc)
    model = _load("model.json", {"params": {}, "log": []})
    picks = _load("picks.json", [])
    games = sd.load_games()
    stamp = now.strftime("%Y-%m-%dT%H:%MZ")
    day = now.astimezone(PT).date()
    for lg in sd.LEAGUES:
        for d in (day - timedelta(days=1), day):
            for r in sd.fetch_day(lg, d) or []:
                games[r["id"]] = sd.merge(games.get(r["id"]), r, stamp)
    graded = grade(picks, games, now)
    for pk in graded:
        print(f"settled {pk['date']} {pk['kind']}: {pk['status']}")
    sp.CACHE = sp.load()
    sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)
    add_breakdowns(games, model, picks)
    posted = post_board(games, model, picks, now, day)          # replaces any graded play (this pass or earlier)
    for pk in posted:
        print(f"posted {pk['kind']} (replacement) for {day}")
    sd.save_games(games)
    _save("picks.json", picks)
    import sports_dashboard
    sports_dashboard.write(picks, model, games, bankroll_series(picks), START_BANKROLL)
    return graded, posted


def run(repick=False, fetch=True):
    now = datetime.now(timezone.utc)
    state = _load("state.json", {})
    model = _load("model.json", {"params": {}, "log": []})
    picks = _load("picks.json", [])
    if fetch:
        t0 = time.time()
        games, calls, fails = sd.sync(state)
        print(f"sync: {len(games)} games stored, {calls} calls, {fails} failed, {time.time() - t0:.0f}s")
        t0 = time.time()
        filled, calls, fails = sd.sync_odds_history(games, state)
        print(f"odds history: {filled} games got odds, {calls} calls, {fails} failed, {time.time() - t0:.0f}s")
        t0 = time.time()
        got, calls, fails = sp.sync(games, state)
        print(f"player stats: {got} box scores added, {calls} to fetch, {fails} failed, {time.time() - t0:.0f}s")
        t0 = time.time()
        filled, venues = sports_weather.sync(games)
        print(f"weather: {filled} games got weather, {venues} new stadiums located, {time.time() - t0:.0f}s")
        print(f"news: {sports_news.sync()} new drama tags")
    else:
        games = sd.load_games()
    sp.CACHE = sp.load()
    sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)                     # QB / starting pitcher / goalie form per game
    n_players = sum(len(rows) for rows in sp.CACHE.values())
    for pk in grade(picks, games, now):
        print(f"settled {pk['date']} {pk['kind']}: {pk['status']} {pk['pnl']:+.2f}")
    day = now.astimezone(PT).date()
    post_now = os.environ.get("SPORTS_POST_NOW") == "1"
    n_final = sum(len(sm.finals(games, lg)) for lg in sd.LEAGUES)          # real games only (no preseason)
    if (model.get("today") or {}).get("date") != day.isoformat():       # baseline for tonight's "in a nutshell"
        model["today"] = {"date": day.isoformat(), "finals": model.get("finals_seen", n_final),
                          "acc": {lg: p["accuracy"] for lg, p in model["params"].items()}}
    n_odds = sum(g["status"] == "final" and g.get("ml_home", "") != "" for g in games.values())
    if (n_final, n_odds, n_players) != (model.get("finals_seen"), model.get("odds_seen"), model.get("players_seen")) \
            or not model["params"]:                                     # retrain on new results / odds / player stats
        t0 = time.time()
        sm.tune_all(games, model)
        model["finals_seen"], model["odds_seen"], model["players_seen"] = n_final, n_odds, n_players
        print(f"tuned in {time.time() - t0:.0f}s: " + ", ".join(
            f"{lg} trust {p['trust']:.0%} acc {p['accuracy']:.1%}" for lg, p in model["params"].items()))
        print("cover study: " + "; ".join(
            f"{lg} big favorites covered {p['big_fav_cover']:.0%} of {p['big_fav_games']} (adjust {p.get('bfav', 0):+.2f})"
            for lg, p in model["params"].items() if p.get("big_fav_cover") is not None))
    n_ls = sum(1 for g in games.values() if g.get("ls_home"))
    if n_ls != model.get("ls_seen"):                                    # the comeback + halves studies learn on new games
        try:
            import sports_comeback as sc
            print(sc.summary(sc.study(games)))
            import sports_halves
            print(sports_halves.summary(sports_halves.study(games)))
            model["ls_seen"] = n_ls
        except Exception as e:                                          # noqa: BLE001 - never block the board
            print(f"comeback study failed: {e}")
    if repick:
        picks[:] = [p for p in picks if p["date"] != day.isoformat() or p["status"] not in ("open", "waiting")]
    picks[:] = [p for p in picks if not (p["status"] == "waiting" and p["date"] < day.isoformat())]
    days = [day] + ([day + timedelta(days=1)] if now.astimezone(PT).hour >= POST_FROM_HOUR_PT else [])
    add_breakdowns(games, model, picks)
    for d in days:
        for pk in post_board(games, model, picks, now, d, force=post_now and d == day):
            legs = " + ".join(f"{leg_label(l)} ({fmt_american(l['odds'])})" for l in pk["legs"])
            print(f"posted {pk['kind']} for {d}: {legs} -> {fmt_american(pk['american'])}, hit {pk['p_hit']:.0%}")
    try:                                                                # 🎾 the tennis bonus (never blocks the main board)
        import sports_tennis
        sports_tennis.run(state, now, fetch=fetch)
    except Exception as e:                                              # noqa: BLE001
        print(f"tennis failed: {e}")
    sd.save_games(games)
    _save("state.json", state)
    _save("model.json", model)
    _save("picks.json", picks)
    import sports_dashboard
    sports_dashboard.write(picks, model, games, bankroll_series(picks), START_BANKROLL)
    return picks


if __name__ == "__main__":
    run(repick="--repick" in sys.argv, fetch="--offline" not in sys.argv)
