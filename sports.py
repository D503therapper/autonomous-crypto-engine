"""THE D503 SPORTS ENGINE - daily picks board (PAPER only: pretend $100 per pick, no real bets).

Every hour (GitHub Actions, .github/workflows/sports.yml):
  1. sync games, scores and odds for NFL, NBA, MLB, NHL from ESPN;
  2. grade finished picks;
  3. once a day (after PICK_HOUR_PT Pacific) retune the model on all results, pull injuries,
     and post the board: 2-leg of the day, 3-leg of the day, lock of the day, dog of the day;
  4. rebuild the phone dashboard (docs/sports/index.html).

    python sports.py            # one cycle
    python sports.py --repick   # replace today's board (e.g. after a rules change)
"""
import itertools
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_data as sd
import sports_model as sm

DATA = sd.DATA
PT = ZoneInfo("America/Los_Angeles")
START_BANKROLL = 1000.0
STAKE = 100.0
PICK_HOUR_PT = 8               # the board goes up at the first run after 8am Pacific
MIN_LEAD_MIN = 20              # only games starting at least this long after the board goes up
MIN_KNOWN = 5                  # both teams need this many rated games
MAX_FAV = -150                 # never a huge favorite: no moneyline leg shorter than this
LOCK_MAX_FAV = -120            # lock of the day: a moneyline no shorter than -120
DOG_MIN = 100                  # dog of the day: any plus-money underdog, big dogs included
TWO_LEG_MIN_DEC = 6.0          # $100 wins at least $500 (+500 or longer)
THREE_LEG_MIN_DEC = 11.0       # $100 wins at least $1,000 (+1000 or longer)
LEG_MIN_EDGE = -0.015          # a leg may be at most slightly negative on our numbers
KINDS = [("two", "2-Leg of the Day"), ("three", "3-Leg of the Day"), ("lock", "Lock of the Day"),
         ("dog", "Dog of the Day")]


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
    """Plain-English reasons for a side, strongest first."""
    s = 1 if side == "home" else -1
    out = []
    pts = f["elo_pts"] * s
    if abs(pts) >= 15:
        out.append((abs(pts) / 40, f"{'stronger' if pts > 0 else 'weaker'} team by rating ({pts:+.0f})"))
    fm = f["form"] * s
    if abs(fm) >= 0.08:
        out.append((abs(fm) * 4, "hotter recent form" if fm > 0 else "colder recent form, bounce-back spot"))
    rest = f["rest"] * 7 * s
    if abs(rest) >= 1:
        out.append((abs(rest) / 3, f"{abs(rest):.0f} more day{'s' if abs(rest) >= 2 else ''} of rest" if rest > 0
                    else f"{abs(rest):.0f} fewer rest day{'s' if abs(rest) >= 2 else ''}"))
    if f["b2b"] * s > 0:
        out.append((0.8, "opponent on a back-to-back"))
    inj = f["inj"] * 5 * s
    if abs(inj) >= 1:
        out.append((abs(inj) / 3, f"opponent has {abs(inj):.0f} more player{'s' if abs(inj) >= 2 else ''} out"
                    if inj > 0 else f"{abs(inj):.0f} more player{'s' if abs(inj) >= 2 else ''} out on our side"))
    mv = sm.line_move(g) * s
    if abs(mv) >= 0.08:
        out.append((abs(mv) * 5, "line moving our way (sharp money)" if mv > 0 else "line moving against"))
    out.sort(key=lambda r: -r[0])
    return [r[1] for r in out[:3]]


def candidates(games, model, now=None, day=None):
    """Every bettable side on today's (Pacific) slate: moneylines, plus spreads in NFL/NBA."""
    now = now or datetime.now(timezone.utc)
    day = day or now.astimezone(PT).date()
    elo = sm.ratings(games, model)
    out = []
    for g in games.values():
        if g["status"] != "pre" or g.get("ml_home", "") == "" or g["league"] not in sd.LEAGUES:
            continue
        start = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        if start.astimezone(PT).date() != day or start < now + timedelta(minutes=MIN_LEAD_MIN):
            continue
        lg = g["league"]
        params = model["params"].get(lg) or sm.default_params(lg)
        f = elo[lg].features(g)
        if f["known"] < MIN_KNOWN:
            continue
        ph = sm.final_p(params, f, g)
        mkt = sm.market_p(g)
        for side in ("home", "away"):
            team, opp = (g["home_name"], g["away_name"]) if side == "home" else (g["away_name"], g["home_name"])
            base = {"game_id": g["id"], "league": lg, "side": side, "team": team, "opp": opp,
                    "home": side == "home", "start": g["start"], "reasons": _reasons(side, f, g, lg, params)}
            odds = int(g[f"ml_{side}"])
            p = ph if side == "home" else 1 - ph
            out.append({**base, "market": "ml", "line": None, "odds": odds, "dec": sd.decimal(odds), "p": p,
                        "p_market": mkt if side == "home" else 1 - mkt, "edge": p * sd.decimal(odds) - 1})
            if lg in sm.SPREAD_LEAGUES and g.get("spread_home", "") != "":
                line = float(g["spread_home"]) * (1 if side == "home" else -1)
                sodds = sm._int(g.get(f"spread_{side}_odds")) or -110
                pc = sm.cover_p(params, f, g, side)
                if pc is not None:
                    out.append({**base, "market": "spread", "line": line, "odds": sodds, "dec": sd.decimal(sodds),
                                "p": pc, "p_market": 1 / sd.decimal(sodds), "edge": pc * sd.decimal(sodds) - 1})
    return out


def _parlay(cands, n, min_dec, top=40):
    """Best n-leg parlay: highest chance to hit among combos that pay at least min_dec, one leg per game,
    no huge favorites, every leg fair-or-better on our numbers (relaxed if nothing qualifies)."""
    for min_edge in (LEG_MIN_EDGE, -0.04, -1.0):
        pool = [c for c in cands if c["odds"] >= MAX_FAV and c["edge"] >= min_edge]
        pool.sort(key=lambda c: -c["edge"])
        pool = pool[:top]
        best = None
        for combo in itertools.combinations(pool, n):
            if len({c["game_id"] for c in combo}) < n:
                continue
            dec, p = 1.0, 1.0
            for c in combo:
                dec *= c["dec"]
                p *= c["p"]
            if dec < min_dec:
                continue
            key = (p, p * dec)
            if best is None or key > best[0]:
                best = (key, combo, dec, p)
        if best:
            _, combo, dec, p = best
            return {"legs": list(combo), "dec": dec, "p_hit": p}
    return None


def make_board(cands):
    """{kind: pick or None} following the owner's rules."""
    board = {"two": _parlay(cands, 2, TWO_LEG_MIN_DEC), "three": _parlay(cands, 3, THREE_LEG_MIN_DEC)}
    ml = [c for c in cands if c["market"] == "ml"]
    locks = [c for c in ml if c["odds"] >= LOCK_MAX_FAV]
    good = [c for c in locks if c["edge"] >= LEG_MIN_EDGE] or locks
    lock = max(good, key=lambda c: (c["p"], c["edge"])) if good else None
    board["lock"] = {"legs": [lock], "dec": lock["dec"], "p_hit": lock["p"]} if lock else None
    dogs = [c for c in ml if c["odds"] >= DOG_MIN and (not lock or c["game_id"] != lock["game_id"])]
    dog = max(dogs, key=lambda c: c["edge"]) if dogs else None
    board["dog"] = {"legs": [dog], "dec": dog["dec"], "p_hit": dog["p"]} if dog else None
    return board


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
def post_board(games, model, picks, now, day, force=False):
    todays = [p for p in picks if p["date"] == day.isoformat()]
    if todays and not force:
        return []
    if force:
        picks[:] = [p for p in picks if p["date"] != day.isoformat() or p["status"] != "open"]
    injuries = {}
    for lg in sd.LEAGUES:
        injuries[lg] = sd.fetch_injuries(lg)
    for g in games.values():
        if g["status"] != "pre" or not injuries.get(g["league"]):
            continue
        start = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        if start.astimezone(PT).date() != day:
            continue
        inj = injuries[g["league"]]
        for side in ("home", "away"):
            g[f"inj_{side}"] = len(sd.team_injuries(inj, g[side], g[f"{side}_name"]))
    board = make_board(candidates(games, model, now, day))
    new = []
    for kind, _ in KINDS:
        b = board.get(kind)
        if not b:
            continue
        for leg in b["legs"]:
            g = games[leg["game_id"]]
            other = "away" if leg["side"] == "home" else "home"
            for key, side, name in (("outs", leg["side"], leg["team"]), ("opp_outs", other, leg["opp"])):
                outs = sd.team_injuries(injuries.get(leg["league"]), g[side], name)
                leg[key] = [f"{n} ({pos})" if pos else n for n, pos, _ in outs[:4]]
        new.append({"date": day.isoformat(), "kind": kind, "posted": now.strftime("%Y-%m-%dT%H:%MZ"),
                    "legs": b["legs"], "dec": round(b["dec"], 4), "american": american(b["dec"]),
                    "p_hit": round(b["p_hit"], 4), "stake": STAKE, "status": "open", "pnl": 0.0})
    picks.extend(new)
    return new


def bankroll_series(picks):
    pts, bank = [], START_BANKROLL
    for pk in sorted((p for p in picks if p["status"] in ("won", "lost", "push")), key=lambda p: p["settled"]):
        bank += pk["pnl"]
        t = datetime.strptime(pk["settled"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).timestamp() * 1000
        pts.append((t, round(bank, 2)))
    return pts


def run(repick=False, fetch=True):
    now = datetime.now(timezone.utc)
    state = _load("state.json", {})
    model = _load("model.json", {"params": {}, "log": []})
    picks = _load("picks.json", [])
    filled = 0
    if fetch:
        t0 = time.time()
        games, calls, fails = sd.sync(state)
        print(f"sync: {len(games)} games stored, {calls} calls, {fails} failed, {time.time() - t0:.0f}s")
        t0 = time.time()
        filled, calls, fails = sd.sync_odds_history(games, state)
        print(f"odds history: {filled} games got odds, {calls} calls, {fails} failed, {time.time() - t0:.0f}s")
    else:
        games = sd.load_games()
    for pk in grade(picks, games, now):
        print(f"settled {pk['date']} {pk['kind']}: {pk['status']} {pk['pnl']:+.2f}")
    day = now.astimezone(PT).date()
    due = now.astimezone(PT).hour >= PICK_HOUR_PT
    n_final = sum(g["status"] == "final" for g in games.values())
    if (model.get("today") or {}).get("date") != day.isoformat():       # baseline for tonight's "in a nutshell"
        model["today"] = {"date": day.isoformat(), "finals": model.get("finals_seen", n_final),
                          "acc": {lg: p["accuracy"] for lg, p in model["params"].items()}}
    if n_final != model.get("finals_seen") or filled or not model["params"]:   # retrain on every new result or odds
        t0 = time.time()
        sm.tune_all(games, model)
        model["finals_seen"] = n_final
        print(f"tuned in {time.time() - t0:.0f}s: " + ", ".join(
            f"{lg} trust {p['trust']:.0%} acc {p['accuracy']:.1%}" for lg, p in model["params"].items()))
    if due or repick:
        for pk in post_board(games, model, picks, now, day, force=repick):
            legs = " + ".join(f"{leg_label(l)} ({fmt_american(l['odds'])})" for l in pk["legs"])
            print(f"posted {pk['kind']}: {legs} -> {fmt_american(pk['american'])}, hit {pk['p_hit']:.0%}")
    sd.save_games(games)
    _save("state.json", state)
    _save("model.json", model)
    _save("picks.json", picks)
    import sports_dashboard
    sports_dashboard.write(picks, model, games, bankroll_series(picks), START_BANKROLL)
    return picks


if __name__ == "__main__":
    run(repick="--repick" in sys.argv, fetch="--offline" not in sys.argv)
