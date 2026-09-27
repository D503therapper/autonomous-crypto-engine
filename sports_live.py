"""LIVE VALUE: watch every live game, find in-game bets where the engine's number beats the live line.

Every 15 seconds (.github/workflows/sports-live.yml) - live lines move every second, so we stay on the ball:
  1. Action Network's live scoreboard: score, period, clock, (football) who has the ball and where, live odds.
  2. The engine's live win chance, on the curve the comeback study (sports_comeback.py) learned from 10 seasons of
     period-by-period scores: the pregame strength still to come + the scoreboard + the ball + momentum.
  3. A side goes up only when ALL of this holds:
       - plus money (live plays are plus money only), and a 5%+ edge on the live price;
       - substantial reasons: history backs it (teams in this exact spot came back / held on more often than the
         price needs) plus at least one more (better team coming in, the algorithm liked them pregame, the ball in
         scoring range, momentum where the study says it carries). A better team alone is never enough.
     At most 2 on the board; a play comes off the moment its value's gone. Each gets a short line and a
     tap-to-open Full breakdown. Every play that went up is logged and graded (its own record).
Writes docs/sports/live.json (phones check it every 15 seconds) and data/sports/live_log.json."""
import json
import math
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_comeback as sc
import sports_data as sd
import sports_model as sm
import sports_players as sp

PT = ZoneInfo("America/Los_Angeles")
LIVE_JSON = "docs/sports/live.json"
LOG = os.path.join(sd.DATA, "live_log.json")
LIVE_MIN_EDGE = 0.05          # live lines move fast and carry more juice: we want a real 5%+ edge
DOG_MIN = 100                 # live plays are plus money only
MAX_GAP = 0.20                # our live chance (score, clock, who has the ball and where) vs the confirmed price: a
                              # bigger gap means the book knows something the scoreboard can't show (injury, ejection)
LIVE_MIN_P = 0.25             # value, not lottery tickets: +300/+400 is fine when it's real, never a +900 prayer
MAX_PLAYS = 2                 # at most 2 on the board at once (no limit per day: a slot opens when a play's value is gone)
SIGMA = sc.SIGMA            # final-margin spread per sport (the study scales it)
LENGTH = {"nfl": (4, 15), "ncaaf": (4, 15), "nba": (4, 12), "ncaab": (2, 20), "nhl": (3, 20), "mlb": (9, None)}
AN = "https://api.actionnetwork.com/web/v1/scoreboard/{lg}?period=game{extra}"
DONE = ("complete", "closed", "final", "cancelled", "canceled", "postponed", "scheduled", "created")


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def phi_inv(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    lo, hi = -6.0, 6.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if phi(mid) < p else (lo, mid)
    return (lo + hi) / 2


def _clock_min(clock):
    m = re.match(r"(\d+):(\d+)", str(clock or ""))
    return int(m.group(1)) + int(m.group(2)) / 60 if m else None


def time_left(league, period, clock, half=None):
    """Fraction of the game still to play (0..1)."""
    periods, mins = LENGTH[league]
    period = max(1, int(period or 1))
    if league == "mlb":
        done = period - 1 + (0.5 if str(half or "").lower().startswith("b") else 0.0)
        return max(0.02, (9 - done) / 9)
    left_in = _clock_min(clock)
    left_in = mins if left_in is None else left_in
    if period > periods:                                  # overtime
        return max(0.02, left_in / (periods * mins) / 2)
    return max(0.02, ((periods - period) * mins + left_in) / (periods * mins))


def ball_value(league, g, box):
    """Football: expected points for the team with the ball, from home's side (+ = home has it)."""
    if league not in ("nfl", "ncaaf"):
        return 0.0
    sit = box.get("situation") or {}
    pos, ytg = sit.get("possession"), sit.get("yards_to_endzone")
    if pos is None or ytg is None:
        return 0.0
    ep = max(-0.5, 5.5 - 0.065 * float(ytg))
    return ep if str(pos) == str(g.get("home_team_id")) else -ep


def live_prob(league, p_pre, margin, left, ball=0.0, last=0.0, fit=None):
    """Home win chance now: the pregame edge still to come + the scoreboard + the ball (+ momentum), on the curve
    the comeback study learned for this sport (untuned curve if there's no study yet)."""
    fit = fit or {"s": 1.0, "w": 1.0, "m": 0.0}
    s = SIGMA[league] * fit["s"]
    mu0 = SIGMA[league] * phi_inv(p_pre)                  # pregame expected final margin
    return phi((margin + fit["w"] * mu0 * left + fit["m"] * last + ball) / (s * math.sqrt(left)))


# ---------------------------------------------------------------- why we see the value (substantial reasons only)
def reasons(st, league, side_p_pre, my, their, left, ml, has_ball, ball_txt, last_mine, last_theirs, pre_value, fit):
    """Concrete reasons this live price is wrong. [(kind, facts)]. History is the backbone: a trailing team needs
    past teams in the same spot to have come back more often than this price needs."""
    out = []
    be = 1 / sd.decimal(ml)                                   # how often it has to hit to break even
    fav = side_p_pre >= 0.5
    if my != their:
        h = (sc.spot(st, league, left, their - my, fav) if my < their else sc.lead_spot(st, league, left, my - their, fav))
        if h and h[1] >= be + 0.02:
            out.append(("history", {"n": h[0], "rate": h[1], "be": be, "k": h[2], "b": h[3], "trail": my < their, "fav": fav}))
    if fav:
        out.append(("better", {"p": side_p_pre}))
    if pre_value:
        out.append(("pre", {}))
    if has_ball:
        out.append(("ball", {"txt": ball_txt}))
    if fit and fit.get("m", 0) > 0 and last_mine > last_theirs:
        out.append(("momentum", {"won": last_mine, "lost": last_theirs}))
    return out


def substantial(rs, tied):
    """History has to back it (a tie has no history bucket, so it needs two other reasons), plus at least one more."""
    kinds = {k for k, _ in rs}
    if tied:
        return len(kinds) >= 2
    return "history" in kinds and len(kinds) >= 2


# ---------------------------------------------------------------- the words (our lingo, rotating)
def _say(k, options):
    return options[k % len(options)]


ICON = {"nfl": "🏈", "ncaaf": "🏈", "nba": "🏀", "ncaab": "🏀", "nhl": "🏒", "mlb": "⚾"}


def blurb(league, us, them, trail, margin_txt, rs, k):
    """The short line: why we see the value, in our voice."""
    i = ICON[league]
    kinds = {kk for kk, _ in rs}
    Us = us[:1].upper() + us[1:]
    if trail and "ball" in kinds:
        return _say(k, [f"{i} {Us} down {margin_txt}, but they got the ball and they're marching. Plus money on a team about to go to work.",
                        f"{i} Rough start, {us} down {margin_txt}. They got the rock though — value's on {us}.",
                        f"{i} {Us} trailing {margin_txt} with the ball in their hands. This is the spot."])
    if trail and "better" in kinds:
        return _say(k, [f"{i} Rough start, {us} down {margin_txt}. Way better team and plus money — they're about to go to work.",
                        f"{i} {Us} down {margin_txt} and the book's panicking. We're not. Better team at plus money.",
                        f"{i} Down {margin_txt} ain't done. {Us} got too much for {them} — and now we get 'em at plus money."])
    if trail and "momentum" in kinds:
        return _say(k, [f"{i} {Us} down {margin_txt}, but they just won the last {sc.PNAME[league]}. The comeback's loading.",
                        f"{i} {Us} been climbing back and the price still says they're dead. They're not."])
    if trail:
        if league == "nhl":
            return _say(k, [f"{i} {them[:1].upper() + them[1:]} might've got the first goal, but {us} are about to bounce back and smack that ass.",
                            f"{i} {Us} down {margin_txt}, plenty of hockey left and the price is too good."])
        return _say(k, [f"{i} {Us} down {margin_txt}. Teams in this spot come back more than this price thinks.",
                        f"{i} Buy the dip: {us} trailing {margin_txt}, history says this one ain't over."])
    if margin_txt != "0":
        return _say(k, [f"{i} {Us} are up {margin_txt} and still plus money. Books are sleeping — take it before it moves.",
                        f"{i} {Us} up {margin_txt} and the book still has them as the dog. The numbers don't. Get in.",
                        f"{i} Up {margin_txt} at plus money? {Us} all day. Trust the algorithm."])
    return _say(k, [f"{i} All tied up and {us} are still plus money. The book's got this wrong — get in.",
                    f"{i} Dead even and the live line's got {us} as the dog. The numbers don't. Get in."])


UNIT = {"nfl": "points", "ncaaf": "points", "nba": "points", "ncaab": "points", "nhl": "goals", "mlb": "runs"}


def full_breakdown(league, us, them, rs, k, rate_mine=None):
    """Tap-to-open: every reason we trust it, one line each, never the same words twice in a row."""
    out = []
    Us = us[:1].upper() + us[1:]
    for kind, f in rs:
        if kind == "history":
            spot = f"{sc.when(league, f['k'])}"
            who = ("teams that were favored coming in" if f["fav"] else "teams") if f["trail"] else \
                ("favorites" if f["fav"] else "underdogs")
            if f["trail"]:
                out.append(_say(k, [
                    f"📚 We studied {f['n']:,} games: {who} down {f['b']} {UNIT[league]} {spot} came back and won {f['rate']:.0%} of the time. "
                    f"This price only needs {f['be']:.0%}. That's the value.",
                    f"📚 The comeback study: {f['n']:,} times a team was down {f['b']} {UNIT[league]} {spot}, {f['rate']:.0%} of them won anyway. "
                    f"At this number you only need {f['be']:.0%} — the book's too scared.",
                    f"📚 Did our homework: down {f['b']} {UNIT[league]} {spot}, {who} still pulled it off {f['rate']:.0%} of the time "
                    f"({f['n']:,} games). The book's pricing it like {f['be']:.0%}. Free money energy.",
                    f"📚 History don't lie: {f['rate']:.0%} of {who} down {f['b']} {UNIT[league]} {spot} came back to win ({f['n']:,} games). "
                    f"This price only needs {f['be']:.0%}."]))
            else:
                out.append(_say(k, [
                    f"📚 We studied {f['n']:,} games: {who} up {f['b']} {UNIT[league]} {spot} held on {f['rate']:.0%} of the time. "
                    f"This price only needs {f['be']:.0%}.",
                    f"📚 {f['n']:,} past games say {who} up {f['b']} {UNIT[league]} {spot} close it out {f['rate']:.0%} of the time — and we're getting plus money.",
                    f"📚 Up {f['b']} {UNIT[league]} {spot} and still plus money? {who.capitalize()} in this spot finish the job {f['rate']:.0%} of the time ({f['n']:,} games)."]))
        elif kind == "better":
            out.append(_say(k + 1, [f"💪 {Us} were the better team coming in — the book had them favored before the game. Better teams don't stay down.",
                                    f"💪 Before the game {us} were the favorite. One bad stretch didn't turn them into a bad team.",
                                    f"💪 {Us} are the better squad, period. The scoreboard's just late to the party."]))
        elif kind == "pre":
            out.append(_say(k + 2, [f"🧠 The algorithm was already on {us} before the game. Now we get 'em cheaper.",
                                    f"🧠 We had value on {us} pregame — the live price just made it juicier.",
                                    f"🧠 The algorithm liked {us} before the game. Now they're on sale."]))
        elif kind == "ball":
            out.append(_say(k + 3, [f"🏈 They got the ball ({f['txt']}) — points are coming.",
                                    f"🏈 Ball's in their hands at {f['txt']}. Next score is theirs to take."]))
        elif kind == "momentum":
            out.append(_say(k + 4, [f"🔥 They won the last {sc.PNAME[league]} {f['won']}-{f['lost']}. The study says momentum carries in this sport.",
                                    f"🔥 {Us} took the last {sc.PNAME[league]} {f['won']}-{f['lost']} — they're rolling.",
                                    f"🔥 {Us} won the last {sc.PNAME[league]} {f['won']}-{f['lost']}. They woke up."]))
    out.append(_say(k + 5, ["🎯 The numbers are on our side and the book's asleep. Trust the algorithm.",
                            "🎯 This is the spot. Get in before the line catches up. Trust the algorithm.",
                            "🎯 Value like this don't last — the book's gonna wake up. We're on it. Let's go.",
                            "🎯 We did the homework, the price is wrong, and we're taking it. Trust the algorithm."]))
    return out


# ---------------------------------------------------------------- one watch cycle
def _get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def fetch_live(league):
    extra = sd.AN_EXTRA.get(league, "")
    if league not in sd.AN_WEEKS:                          # day-based leagues: today's (and last night's late) games
        day = datetime.now(PT)
        out = []
        for d in (day - timedelta(days=1), day):
            try:
                out += _get(AN.format(lg=league, extra=extra) + "&date=" + d.strftime("%Y%m%d")).get("games") or []
            except Exception as e:                           # noqa: BLE001
                sd.ERRORS.append(f"live {league}: {str(e)[:100]}")
        return out
    try:
        return _get(AN.format(lg=league, extra=extra)).get("games") or []    # football: the current week
    except Exception as e:                                   # noqa: BLE001
        sd.ERRORS.append(f"live {league}: {str(e)[:100]}")
        return []


def _match(games, league, ang):
    """Our stored game for an Action Network game (same teams, start within 3 hours)."""
    teams = {t.get("id"): t for t in ang.get("teams") or []}
    home, away = teams.get(ang.get("home_team_id")), teams.get(ang.get("away_team_id"))
    if not home or not away or not ang.get("start_time"):
        return None
    t = datetime.strptime(ang["start_time"][:16], "%Y-%m-%dT%H:%M")
    for g in games.values():
        if g["league"] != league or not g.get("start"):
            continue
        gt = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M")
        if abs((gt - t).total_seconds()) <= 3 * 3600 and sd._same(g["home_name"], home.get("full_name") or "") \
                and sd._same(g["away_name"], away.get("full_name") or ""):
            return g
    return None


def _last_period(box):
    """(home, away) points in the last completed period."""
    ls = box.get("linescore") or []
    done = max(0, int(box.get("period") or 1) - 1)
    if not done or len(ls) < done:
        return 0, 0
    p = ls[done - 1]
    return int(p.get("home_points") or 0), int(p.get("away_points") or 0)


def evaluate(league, g, box, mlh, mla, st, pre_model_p, pre_market_p, ball, ball_txt, key, checked=False):
    """Both sides of one live game -> plays that clear every bar (plus money, 5%+ edge, substantial reasons)."""
    fit = ((st.get(league) or {}).get("curve") or {})
    if fit.get("ll") is None or pre_market_p is None:
        return []                                             # no study for this sport yet: no history, no bet
    hs, as_ = _score(box, "home"), _score(box, "away")
    left = time_left(league, box.get("period"), box.get("clock"), box.get("inning_half") or box.get("half"))
    lh, la = _last_period(box)
    ph = live_prob(league, pre_market_p, hs - as_, left, ball, lh - la, fit)
    out = []
    book_h = sd.no_vig(mlh, mla)
    for side, p, ml in (("home", ph, mlh), ("away", 1 - ph, mla)):
        edge = p * sd.decimal(ml) - 1
        if ml < DOG_MIN or edge < LIVE_MIN_EDGE or p < LIVE_MIN_P:   # plus money, real value, a real chance
            continue
        if not checked and p - (book_h if side == "home" else 1 - book_h) > MAX_GAP:
            continue       # only one source and the price is miles from what the score says: can't tell a real
                           # price from a glitch, so no play. Two sources agreeing = a real price = it plays.
        us, them = (g["home_name"], g["away_name"]) if side == "home" else (g["away_name"], g["home_name"])
        my, their = (hs, as_) if side == "home" else (as_, hs)
        side_pre = pre_market_p if side == "home" else 1 - pre_market_p
        pre_value = pre_model_p is not None and ((pre_model_p - pre_market_p) if side == "home" else (pre_market_p - pre_model_p)) >= 0.02
        has_ball = ball_txt and (ball > 0 if side == "home" else ball < 0) and abs(ball) >= 2.2   # ball near scoring range
        lm, lt = (lh, la) if side == "home" else (la, lh)
        rs = reasons(st, league, side_pre, my, their, left, ml, has_ball, ball_txt, lm, lt, pre_value, fit)
        if not substantial(rs, my == their):
            continue
        pid = f"{g['id']}:{side}"
        k = sum(map(ord, pid)) + key
        pro = league in ("nfl", "nba", "mlb", "nhl")
        the_us, the_them = (f"the {us}", f"the {them}") if pro else (us, them)
        out.append({
            "id": pid, "league": league, "emoji": sd.LEAGUES[league][3], "sport": sd.LEAGUES[league][2],
            "team": us, "opp": them, "odds": ml, "edge": round(edge, 4), "p": round(p, 3),
            "score": f"{g['away_name']} {as_} @ {g['home_name']} {hs}", "clock": _clock_txt(league, box),
            "ball": ball_txt or "", "reasons": [kk for kk, _ in rs],
            "line": blurb(league, the_us, the_them, my < their, f"{abs(my - their)}", rs, k),
            "breakdown": full_breakdown(league, the_us, the_them, rs, k),
        })
    return out


BOOKS = {}                    # what the sportsbook feed returned this cycle, per league (diagnostics)
WATCHING = [0]
PRICED = [0]                  # live games with a sportsbook price this cycle                # live games seen in the last cycle (the dashboard says whether games are going)


BOVADA = "https://www.bovada.lv/services/sports/event/v2/events/A/description/{path}?marketFilterId=def&liveOnly=true&lang=en"
ESPN_ODDS = "https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/events/{eid}/competitions/{eid}/odds"
BOVADA_PATH = {"nfl": "football/nfl", "ncaaf": "football/college-football", "nba": "basketball/nba",
               "ncaab": "basketball/college-basketball", "nhl": "hockey/nhl", "mlb": "baseball/mlb"}
AGREE = 0.08                  # the sportsbook (Bovada) and Action Network must agree within 8 points of win chance


def _clean(name):
    return re.sub(r"\s*\(#?\d+\)\s*", " ", str(name or "")).strip()


def bovada_live(league):
    """[{home, away, ml_home, ml_away}] - the sportsbook's LIVE moneylines right now."""
    try:
        data = _get(BOVADA.format(path=BOVADA_PATH[league]))
    except Exception as e:                                   # noqa: BLE001
        sd.ERRORS.append(f"bovada live {league}: {str(e)[:100]}")
        BOOKS[league] = f"error {str(e)[:60]}"
        return []
    BOOKS[league] = f"{len(data or [])} groups, {sum(len(g.get('events') or []) for g in data or [])} events"
    out = []
    for grp in data or []:
        for ev in grp.get("events") or []:
            comps = {("home" if c.get("home") else "away"): _clean(c.get("name")) for c in ev.get("competitors") or []}
            if len(comps) != 2:
                continue
            for dg in ev.get("displayGroups") or []:
                for mk in dg.get("markets") or []:
                    per = mk.get("period") or {}
                    if "moneyline" not in str(mk.get("description", "")).lower() or not per.get("live") or not per.get("main"):
                        continue
                    px = {}
                    for o in mk.get("outcomes") or []:
                        v = str((o.get("price") or {}).get("american") or "").upper()
                        px[_clean(o.get("description"))] = 100 if v == "EVEN" else int(v) if re.match(r"^[+-]?\d+$", v) else None
                    h, a = px.get(comps["home"]), px.get(comps["away"])
                    if h is not None and a is not None:
                        out.append({"home": comps["home"], "away": comps["away"], "ml_home": h, "ml_away": a})
    return out


def dk_live(league, g):
    """DraftKings' LIVE moneyline for our game, through ESPN's odds feed: (home ml, away ml) or (None, None)."""
    sport, lg = sd.LEAGUES[league][0].split("/")
    try:
        items = _get(ESPN_ODDS.format(sport=sport, league=lg, eid=g["id"].split(":", 1)[1])).get("items") or []
    except Exception as e:                                   # noqa: BLE001
        sd.ERRORS.append(f"dk live {g['id']}: {str(e)[:80]}")
        return None, None
    for it in items:
        if "live" not in str((it.get("provider") or {}).get("name", "")).lower():
            continue
        h, a = (it.get("homeTeamOdds") or {}).get("moneyLine"), (it.get("awayTeamOdds") or {}).get("moneyLine")
        try:
            return int(h), int(a)
        except (TypeError, ValueError):
            return None, None
    return None, None


def two_books(dk, bov):
    """The live price from two real sportsbooks (DraftKings via ESPN, Bovada): (home, away, confirmed).
    Both agree = confirmed; only one = used, unconfirmed; far apart = something's glitched = no price."""
    have = [x for x in (dk, bov) if x[0] is not None and x[1] is not None]
    if not have:
        return None, None, False
    if len(have) == 2:
        if abs(sd.no_vig(*have[0]) - sd.no_vig(*have[1])) > AGREE:
            return None, None, False
        return have[0][0], have[0][1], True
    return have[0][0], have[0][1], False


def book_line(lines, g):
    """(home ml, away ml) for our game from the sportsbook's live lines, or (None, None)."""
    for ln in lines:
        if sd._same(g["home_name"], ln["home"]) and sd._same(g["away_name"], ln["away"]):
            return ln["ml_home"], ln["ml_away"]
    return None, None


def confirmed_line(book, an, both=False):
    """The live price we trust: the sportsbook's line, cross-checked with Action Network's when it has one.
    Far apart = one of them is glitched = no price. both=True also says whether the two sources agreed."""
    if book[0] is None or book[1] is None:
        return (None, None, False) if both else (None, None)
    two = an[0] is not None and an[1] is not None
    if two and abs(sd.no_vig(*book) - sd.no_vig(*an)) > AGREE:
        return (None, None, False) if both else (None, None)
    return (book[0], book[1], two) if both else book


def live_line(box):
    """(home ml, away ml) from the LIVE line only. Action Network's "game" line is the pregame price - using it
    once made a 7-0 lead look like +272 value. No live line = no play."""
    odds = ((box.get("latest_odds") or {}).get("live")) or {}
    return sd.parse_american(odds.get("ml_home")), sd.parse_american(odds.get("ml_away"))


def board(plays, showing=()):
    """Max 2 at once: plays already up keep their slot while they still qualify; open slots go to the best edge."""
    return sorted(plays, key=lambda x: (x["id"] not in showing, -x["edge"]))[:MAX_PLAYS]


def cycle(games, model, log, now=None, st=None, showing=()):
    """Scan every live game -> the plays on the board right now. Max 2 at a time, no limit per day: a play that's
    up stays up while its value's still there (`showing`); a new one only takes a slot that's open."""
    now = now or datetime.now(timezone.utc)
    st = sc.load() if st is None else st
    elo = sm.ratings(games, model)
    plays = []
    WATCHING[0] = PRICED[0] = 0
    for lg in sd.LEAGUES:
        params = model["params"].get(lg) or sm.default_params(lg)
        angs = fetch_live(lg)
        books = bovada_live(lg) if any((a.get("boxscore") or {}).get("period") and str(a.get("status") or "").lower()
                                       not in DONE for a in angs) else []
        for ang in angs:
            status = str(ang.get("status") or ang.get("real_status") or "").lower()
            box = ang.get("boxscore") or {}
            if status in DONE or not box.get("period"):
                _grade(log, ang)
                continue
            WATCHING[0] += 1                                   # a game going right now
            g = _match(games, lg, ang)
            if not g:
                continue
            mlh, mla, checked = two_books(dk_live(lg, g), book_line(books, g))
            PRICED[0] += mlh is not None and mla is not None
            if mlh is None or mla is None:
                continue
            f = elo[lg].features(g)
            mkt = sm.market_p(g)
            p_model = sm.final_p(params, f, g) if mkt is not None else None
            ball = ball_value(lg, ang, box)
            ball_txt = (box.get("situation") or {}).get("display_short") or "" if ball else ""
            for pl in evaluate(lg, g, box, mlh, mla, st, p_model, mkt, ball, ball_txt, now.hour, checked):
                pl["an_id"] = ang.get("id")
                plays.append(pl)
    plays = board(plays, showing)
    for pl in plays:                                          # log the first time each play goes up (graded later)
        if pl["id"] not in log["plays"]:
            log["plays"][pl["id"]] = {"posted": now.strftime("%Y-%m-%dT%H:%MZ"), "team": pl["team"], "odds": pl["odds"],
                                      "league": pl["league"], "score_at_post": pl["score"], "clock_at_post": pl["clock"],
                                      "side": pl["id"].rsplit(":", 1)[1], "an_id": pl["an_id"], "result": None,
                                      "reasons": pl["reasons"], "date": now.astimezone(PT).date().isoformat()}
        pl["posted"] = log["plays"][pl["id"]]["posted"]
    return plays


def _score(box, side):
    for k in (f"total_{side}_points", f"{side}_score", f"{side}_points"):
        if box.get(k) is not None:
            return int(box[k])
    ls = box.get("linescore") or []
    return int(sum((p.get(f"{side}_points") or 0) for p in ls))


def _clock_txt(league, box):
    per = box.get("period")
    if league == "mlb":
        half = str(box.get("inning_half") or box.get("half") or "")
        return f"{'Top' if half.lower().startswith('t') else 'Bot' if half.lower().startswith('b') else 'Inning'} {per}"
    name = {"nhl": "P", "ncaab": "H"}.get(league, "Q")
    return f"{name}{per} {box.get('clock') or ''}".strip()


def _grade(log, ang):
    """Grade logged plays once their game is final."""
    status = str(ang.get("status") or "").lower()
    if status not in ("complete", "closed", "final"):
        return
    win = ang.get("winning_team_id")
    for pid, e in log["plays"].items():
        if e["result"] is None and e.get("an_id") == ang.get("id"):
            e["result"] = "won" if (win == (ang.get("home_team_id") if e["side"] == "home" else ang.get("away_team_id"))) else "lost"


def record(log):
    w = sum(e["result"] == "won" for e in log["plays"].values())
    lo = sum(e["result"] == "lost" for e in log["plays"].values())
    return {"won": w, "lost": lo}


def run():
    games = sd.load_games()
    model = json.load(open(os.path.join(sd.DATA, "model.json")))
    sp.CACHE = sp.load()
    sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)
    log = json.load(open(LOG)) if os.path.exists(LOG) else {"plays": {}}
    try:
        showing = [p["id"] for p in json.load(open(LIVE_JSON)).get("plays") or []]
    except (OSError, ValueError):
        showing = []
    plays = cycle(games, model, log, showing=showing)
    out = {"updated": int(time.time() * 1000), "plays": plays, "record": record(log), "live_games": WATCHING[0],
           "priced": PRICED[0], "errors": sd.ERRORS[-3:], "books": dict(BOOKS)}
    del sd.ERRORS[:]
    os.makedirs(os.path.dirname(LIVE_JSON), exist_ok=True)
    with open(LIVE_JSON, "w") as f:
        json.dump(out, f, indent=1)
    with open(LOG, "w") as f:
        json.dump(log, f, indent=1, sort_keys=True)
    print(f"live: {WATCHING[0]} games live, {PRICED[0]} with a confirmed sportsbook price, {len(plays)} plays on the board" + "".join(f"\n   {p['team']} {p['odds']:+d} ({p['score']}, {p['clock']}) edge {p['edge']:.1%}" for p in plays))
    return plays


def any_live_soon(games, within_min=45):
    """Is anything live now or starting soon? (else the watcher can rest)"""
    now = datetime.now(timezone.utc)
    for g in games.values():
        if not g.get("start"):
            continue
        t = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        if g["status"] == "live" or (g["status"] == "pre" and now - timedelta(hours=4) <= t <= now + timedelta(minutes=within_min)):
            return True
    return False


def _git(*args):
    import subprocess
    return subprocess.run(["git", *args], capture_output=True, text=True)


LIVE_BRANCH = "live-data"      # live.json goes out on its own branch (one tiny commit, force-pushed) the moment it
                               # changes; phones read it from there. The graded log still lives on main.


def push_live():
    """Force-push docs/sports/live.json as the only file of the live-data branch (seconds, no history pile-up)."""
    blob = _git("hash-object", "-w", LIVE_JSON).stdout.strip()
    import subprocess
    tree = subprocess.run(["git", "mktree"], input=f"100644 blob {blob}\tlive.json\n", capture_output=True, text=True).stdout.strip()
    commit = _git("commit-tree", tree, "-m", f"live {datetime.now(timezone.utc):%H:%M:%S}").stdout.strip()
    for _ in range(3):
        if _git("push", "-q", "-f", "origin", f"{commit}:refs/heads/{LIVE_BRANCH}").returncode == 0:
            return True
        time.sleep(2)
    return False


def publish(msg):
    """Commit + push the live log to main - only when a play is first logged or graded. (live.json itself only
    goes out on the live-data branch; phones read it there.)"""
    _git("add", LOG)
    if _git("diff", "--cached", "--quiet").returncode == 0:
        return
    _git("commit", "-qm", msg)
    for _ in range(4):
        _git("pull", "-q", "--rebase", "-X", "theirs")
        if _git("push", "-q").returncode == 0:
            return
        time.sleep(3)


def _board_key():
    try:
        d = json.load(open(LIVE_JSON))
    except (OSError, ValueError):
        return None
    return json.dumps([{k: v for k, v in p.items() if k != "posted"} for p in d.get("plays") or []], sort_keys=True) \
        + str(d.get("live_games"))


def _log_key():
    try:
        return open(LOG).read()
    except OSError:
        return None


def loop(minutes, every_s=15):
    """Watch live games every `every_s` seconds for `minutes`. Phones see every change right away (live-data
    branch, plus a heartbeat every minute); the graded log goes to main when it changes. Rests when nothing's live."""
    end = time.time() + minutes * 60
    games, idle_since, started, last_board, last_log, last_push = None, None, False, None, _log_key(), 0.0
    while time.time() < end:
        if games is None or int(time.time()) % 600 < every_s:          # reload games/model every ~10 min
            _git("pull", "-q", "--rebase", "-X", "theirs")
            games = sd.load_games()
        if not any_live_soon(games):
            idle_since = idle_since or time.time()
            if not started or time.time() - idle_since > 5 * 60:        # nothing on: don't burn the clock
                print("live: nothing on - resting")
                break
        else:
            idle_since = None
        started = True
        try:
            run()
        except Exception as e:                                      # noqa: BLE001 - keep watching
            print(f"live cycle error: {e}")
        board = _board_key()
        if board != last_board or time.time() - last_push > 60:
            if push_live():
                last_board, last_push = board, time.time()
        if _log_key() != last_log:
            publish(f"live log {datetime.now(timezone.utc):%H:%M}")
            last_log = _log_key()
        time.sleep(every_s)
    if os.path.exists(LIVE_JSON):                                 # end of watch: an empty board if nothing's on
        out = json.load(open(LIVE_JSON))
        if not started:
            out.update(plays=[], live_games=0)
        out["updated"] = int(time.time() * 1000)
        with open(LIVE_JSON, "w") as f:
            json.dump(out, f, indent=1)
        push_live()
    if _log_key() != last_log:
        publish("live: end of watch")


if __name__ == "__main__":
    if "--loop" in sys.argv:
        loop(float(sys.argv[sys.argv.index("--loop") + 1]))
    else:
        run()
    sys.exit(0)
