"""LIVE VALUE: watch every live game, find in-game bets where the engine's number beats the live line.

Every 10 seconds (.github/workflows/sports-live.yml) - live lines move every second, so we stay on the ball:
  1. Action Network's live scoreboard: score, period, clock, (football) who has the ball and where, live odds.
  2. The engine's live win chance, on the curve the comeback study (sports_comeback.py) learned from 10 seasons of
     period-by-period scores: the pregame strength still to come + the scoreboard + the ball + momentum.
  3. A side goes up only when ALL of this holds:
       - plus money (live plays are plus money only), and a 5%+ edge on the live price;
       - substantial reasons: history backs it (teams in this exact spot came back / held on more often than the
         price needs) plus at least one more (better team coming in, the algorithm liked them pregame, the ball in
         scoring range, momentum where the study says it carries). A better team alone is never enough.
     At most MAX_PLAYS on the board; a play comes off the moment its value's gone. Each gets a short line and a
     tap-to-open Full breakdown. Every play that went up is logged and graded (its own record).
  4. 🎾 Tennis (ATP + WTA) rides the same rules: the score from ESPN's tennis scoreboards (sets, games, points when
     the feed has them), the live price from Bovada's tennis feed, and a point-by-point Markov model started from
     the pre-match chance (sports_tennis_live). Reasons: the engine liked the player pregame (our pick, or a strong
     favorite on our numbers) AND the score isn't as bad as the price says. On one of OUR pregame picks who's
     trailing and now plus money, it's a DOUBLE DOWN. ESPN's tennis score runs behind: a suspended market, a score
     that hasn't moved in too long, or a price miles from what the score says = no play. Tennis live plays count in
     the LIVE PLUS MONEY record only - never the tennis pregame records or our main record.
Writes docs/sports/live.json (phones check it every 10 seconds) and data/sports/live_log.json."""
import json
import math
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_comeback as sc
import sports_data as sd
import sports_model as sm
import sports_players as sp
import sports_tennis as stn
import sports_tennis_live as stl

PT = ZoneInfo("America/Los_Angeles")
LIVE_JSON = "docs/sports/live.json"
LOG = os.path.join(sd.DATA, "live_log.json")
LIVE_MIN_EDGE = 0.05          # live lines move fast and carry more juice: we want a real 5%+ edge
DOG_MIN = 100                 # live plays are plus money only
LATE = 0.06                   # the last ~3.5 minutes of a football game: who has the ball decides it
MAX_GAP = 0.20                # our live chance (score, clock, who has the ball and where) vs the confirmed price: a
                              # bigger gap means the book knows something the scoreboard can't show (injury, ejection)
STAY_MAX_ODDS = 500              # ...and comes down if the price blows out past +500 (a prayer, not a live bet)
STAY_EDGE, STAY_P = 0.0, 0.15    # never count a live dog out: a play that's up stays while there's ANY value left;
                                 # it only comes down when the value's gone or it's shitting the bed (under a 15% chance)
PAUSE_HOLD_S = 180            # the book pauses its line (drive in the red zone, review): hold the card up to 3 minutes
LATE_REAL = 1 / 3             # the last third of a game: a trailing team's chance is pulled halfway to the real history
LIVE_MIN_P = 0.40             # ACCURACY FIRST: a new live bet is one we think has a real shot (40%+)...
LIVE_MAX_ODDS = 250           # ...and never longer than +250 when it goes up (the +270..+425 ones kept losing)
MAX_PLAYS = 4                 # up to 4 on the board at once, best value first (no limit per day)
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


KICK = {}                     # espn game id -> the team that took the opening kickoff (the other one gets the 2nd half)
HALF_BALL = 0.6               # receiving the 2nd-half kickoff: a drive from about its own 25 (~0.6 expected points)


def halftime(league, ang, box):
    if league not in ("nfl", "ncaaf"):
        return False
    clock = str(box.get("clock") or "")
    return "half" in str(ang.get("status_display") or ang.get("status") or "").lower() or \
        (int(box.get("period") or 0) == 2 and clock.replace("0", "").replace(":", "") == "")


def second_half_ball(league, g):
    """'home' / 'away': who receives to start the 2nd half (the team that didn't take the opening kickoff)."""
    eid = g["id"].split(":", 1)[1]
    if eid not in KICK:
        try:
            s = _get(f"https://site.api.espn.com/apis/site/v2/sports/{sd.LEAGUES[league][0]}/summary?event={eid}")
            drives = (s.get("drives") or {}).get("previous") or []
            KICK[eid] = str(((drives[0].get("team") or {}).get("id")) or "") if drives else ""
        except Exception as e:                               # noqa: BLE001
            sd.ERRORS.append(f"kickoff {eid}: {str(e)[:60]}")
            return None
    first = KICK[eid]
    if not first:
        return None
    return "away" if first == str(g["home"]) else "home" if first == str(g["away"]) else None


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
def reasons(st, league, side_p_pre, my, their, left, ml, has_ball, ball_txt, last_mine, last_theirs, pre_value, fit,
            home=None):
    """Concrete reasons this live price is wrong. [(kind, facts)]. History is the backbone: a trailing team needs
    past teams in the same spot to have come back more often than this price needs."""
    out = []
    be = 1 / sd.decimal(ml)                                   # how often it has to hit to break even
    fav = side_p_pre >= 0.5
    if my != their:
        h = (sc.spot(st, league, left, their - my, fav, home) if my < their else sc.lead_spot(st, league, left, my - their, fav))
        if h and h[1] >= be + 0.02:
            out.append(("history", {"n": h[0], "rate": h[1], "be": be, "k": h[2], "b": h[3], "trail": my < their, "fav": fav,
                                    "d": abs(their - my)}))
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
    kinds = {k for k, _ in rs} - {"half"}            # the 2nd-half kickoff is in the numbers, not a reason on its own
    if tied:
        return len(kinds) >= 2
    return "history" in kinds and len(kinds) >= 2


# ---------------------------------------------------------------- the words (our lingo, rotating)
def _say(k, options):
    return options[k % len(options)]


ICON = {"nfl": "🏈", "ncaaf": "🏈", "nba": "🏀", "ncaab": "🏀", "nhl": "🏒", "mlb": "⚾"}


def blurb(league, us, them, trail, margin_txt, rs, k):
    """The short line: why we see the value - in our lingo, never the same way twice in a row."""
    i = ICON[league]
    kinds = {kk for kk, _ in rs}
    Us, Them = us[:1].upper() + us[1:], them[:1].upper() + them[1:]
    m = margin_txt
    if trail and "ball" in kinds:
        return _say(k, [f"{i} {Us} down {m} but they got the rock and they're marching. About to go to work — hammer it.",
                        f"{i} Down {m}? Who cares. {Us} got the ball and {them} can't stop nobody. We cooking.",
                        f"{i} {Us} down {m} with the ball in their hands. The book's sleeping — wake up and hammer {us}.",
                        f"{i} {Them} up {m} and the dummies think it's over. {Us} got the ball. Don't be a sheep."])
    if trail and "better" in kinds:
        return _say(k, [f"{i} {Us} down {m}? Rough start, but they're the better team and we get 'em at plus money. Hammer it.",
                        f"{i} Everybody and their mama jumping off {us} down {m}. Not us. Better team, plus money — let's eat.",
                        f"{i} {Us} been booty cheeks so far, down {m}. That don't last. Way better team — they about to go to work.",
                        f"{i} Down {m} ain't done. {Us} got way too much for {them}, and the book's handing us plus money. Trust the algorithm.",
                        f"{i} {Them} up {m} and they must think they're good. They ain't. {Us} about to smack that ass."])
    if trail and "momentum" in kinds:
        return _say(k, [f"{i} {Us} down {m} but they just took the last {sc.PNAME[league]}. The comeback's loading — get in.",
                        f"{i} {Us} been climbing back and the price still says they're dead. They're not. Hammer it."])
    if trail:
        if league == "nhl":
            return _say(k, [f"{i} {Them} might've got the first goal, but {us} are about to bounce back and smack that ass.",
                            f"{i} {Us} down {m}, plenty of hockey left and the price is too juicy. Get in."])
        return _say(k, [f"{i} {Us} down {m}. Teams in this spot come back way more than this price thinks. Buy the dip.",
                        f"{i} The dummies are about to sell {us} down {m}. We buying. Trust the algorithm."])
    if m != "0":
        return _say(k, [f"{i} {Us} up {m} and STILL plus money? Books are sleeping — take it before it moves.",
                        f"{i} {Us} up {m} and the book's got them as the dog. That's a gift. Hammer it.",
                        f"{i} Up {m} at plus money? {Us} all day. The book's cooked on this one."])
    return _say(k, [f"{i} All tied up and {us} are still plus money. The book's got this wrong — get in.",
                    f"{i} Dead even and the live line's got {us} as the dog. The numbers don't. Hammer it."])


UNIT = {"nfl": "points", "ncaaf": "points", "nba": "points", "ncaab": "points", "nhl": "goals", "mlb": "runs"}


def full_breakdown(league, us, them, rs, k, rate_mine=None):
    """Tap-to-open: every reason we trust it, in our lingo, one line each, rotating."""
    out = []
    Us, Them = us[:1].upper() + us[1:], them[:1].upper() + them[1:]
    for kind, f in rs:
        if kind == "history":
            spot, d = sc.when(league, f["k"]), f["d"]
            who = ("favorites" if f["fav"] else "teams") if f["trail"] else ("favorites" if f["fav"] else "dogs")
            if f["trail"]:
                out.append(_say(k, [
                    f"📚 We did our homework: {f['n']:,} games where {who} were down about {d} {spot} — {f['rate']:.0%} of 'em "
                    f"came back and won. This price only needs {f['be']:.0%}. That's free money energy.",
                    f"📚 Down {d} ain't dead. In {f['n']:,} games like this, {who} came back {f['rate']:.0%} of the time. "
                    f"The book's pricing it like {f['be']:.0%} — they scared, we're not.",
                    f"📚 History don't lie: {f['rate']:.0%} of {who} down {d} {spot} still won ({f['n']:,} games). "
                    f"At this number you only need {f['be']:.0%}. Hammer it.",
                    f"📚 The comeback study says {who} in this spot win {f['rate']:.0%} of the time ({f['n']:,} games). "
                    f"The price needs {f['be']:.0%}. Do the math — we eating."]))
            else:
                out.append(_say(k, [
                    f"📚 {f['n']:,} games like this: {who} up about {d} {spot} closed it out {f['rate']:.0%} of the time. "
                    f"This price only needs {f['be']:.0%}. Easy money.",
                    f"📚 {Us} up {d} and still plus money? {who.capitalize()} in this spot finish the job {f['rate']:.0%} of the time "
                    f"({f['n']:,} games). The book's tripping.",
                    f"📚 History says {who} up {d} {spot} hold on {f['rate']:.0%} of the time ({f['n']:,} games). "
                    f"We only need {f['be']:.0%}. Hammer it."]))
        elif kind == "better":
            out.append(_say(k + 1, [f"💪 {Us} were the favorite before this thing started. One bad stretch don't make 'em trash.",
                                    f"💪 {Us} are the better squad, period. The scoreboard's just late to the party.",
                                    f"💪 {Them} got lucky early. {Us} are the better team and they about to go to work.",
                                    f"💪 Real ones know {us} are better than {them}. The book's panicking over a few plays."]))
        elif kind == "pre":
            out.append(_say(k + 2, [f"🧠 The algorithm was already on {us} before the game. Now we get 'em on sale.",
                                    f"🧠 We liked {us} pregame — the live price just made it juicier. Double dip.",
                                    f"🧠 The engine had value on {us} before the game even started. Now it's even better."]))
        elif kind == "half":
            out.append(_say(k + 6, [f"🏈 And {us} get the ball to start the 2nd half. That's a free possession.",
                                    f"🏈 {Us} receive the 2nd-half kickoff — first crack at it after the break.",
                                    "🏈 Ball's theirs coming out of halftime. The algorithm counted that."]))
        elif kind == "ball":
            out.append(_say(k + 3, [f"🏈 They got the rock ({f['txt']}). Points are coming.",
                                    f"🏈 Ball's in their hands at {f['txt']}. Next score is theirs to take.",
                                    f"🏈 {Us} got the ball ({f['txt']}) and {them} can't stop nobody."]))
        elif kind == "momentum":
            out.append(_say(k + 4, [f"🔥 {Us} took the last {sc.PNAME[league]} {f['won']}-{f['lost']}. They cooking now.",
                                    f"🔥 {Us} won the last {sc.PNAME[league]} {f['won']}-{f['lost']}. They woke up — {them} in trouble."]))
    out.append(_say(k + 5, ["🎯 The numbers are on our side and the book's asleep. Trust the algorithm.",
                            "🎯 This is the spot. Get in before the line catches up. Let's fucking go.",
                            "🎯 Value like this don't last — the book's gonna wake up. We're on it. Let's go.",
                            "🎯 Don't be a sheep. The dummies are selling, we buying. Trust the algorithm."]))
    return out


# ---------------------------------------------------------------- one watch cycle
def _get(url, tries=2):
    """GET json; one quick retry (feeds hiccup - a connection reset shouldn't cost a check)."""
    for i in range(tries):
        try:
            return _get1(url)
        except Exception:                                    # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(0.5)


def _get1(url):
    hdr = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"} if "bovada" in url else {}   # Bovada sends an empty
    req = urllib.request.Request(url, headers=hdr)                            # list to a bare client; ESPN 403s a browser one
    with urllib.request.urlopen(req, timeout=20) as r:
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
        return list({g.get("id"): g for g in out}.values())       # a game can be on both days' lists
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


def evaluate(league, g, box, mlh, mla, st, pre_model_p, pre_market_p, ball, ball_txt, key, checked=False, hold=(),
             half_ball=None):
    """Both sides of one live game -> plays that clear every bar (plus money, 5%+ edge, substantial reasons)."""
    fit = ((st.get(league) or {}).get("curve") or {})
    if fit.get("ll") is None or pre_market_p is None:
        return []                                             # no study for this sport yet: no history, no bet
    hs, as_ = _score(box, "home"), _score(box, "away")
    left = time_left(league, box.get("period"), box.get("clock"), box.get("inning_half") or box.get("half"))
    sit = box.get("situation") or {}
    blind = league in ("nfl", "ncaaf") and left < LATE and (sit.get("possession") is None or sit.get("yards_to_endzone") is None)
    lh, la = _last_period(box)
    ph = live_prob(league, pre_market_p, hs - as_, left, ball, lh - la, fit)
    out = []
    book_h = sd.no_vig(mlh, mla)
    for side, p, ml in (("home", ph, mlh), ("away", 1 - ph, mla)):
        my, their = (hs, as_) if side == "home" else (as_, hs)
        if my < their and left <= LATE_REAL:                 # late and behind: lean on what really happened to teams
            h = sc.spot(st, league, left, their - my, (pre_market_p >= 0.5) == (side == "home"), side == "home")   # in this exact spot (home/away split -
            if h:                                            # in baseball the home team bats last)
                p = (p + h[1]) / 2
        edge = p * sd.decimal(ml) - 1
        up = f"{g['id']}:{side}" in hold                    # already on the board: it stays while value's still there
        if not up and blind:
            continue                                         # late in a football game and we can't see who has the ball
        if ml < DOG_MIN or edge < (STAY_EDGE if up else LIVE_MIN_EDGE) or p < (STAY_P if up else min_p()) \
                or (up and ml > STAY_MAX_ODDS) or (not up and ml > LIVE_MAX_ODDS):
            continue                                         # plus money, real value, a real chance
        if not checked and p - (book_h if side == "home" else 1 - book_h) > MAX_GAP:
            continue       # only one source and the price is miles from what the score says: can't tell a real
                           # price from a glitch, so no play. Two sources agreeing = a real price = it plays.
        us, them = (g["home_name"], g["away_name"]) if side == "home" else (g["away_name"], g["home_name"])
        side_pre = pre_market_p if side == "home" else 1 - pre_market_p
        pre_value = pre_model_p is not None and ((pre_model_p - pre_market_p) if side == "home" else (pre_market_p - pre_model_p)) >= 0.02
        has_ball = ball_txt and (ball > 0 if side == "home" else ball < 0) and abs(ball) >= 2.2   # ball near scoring range
        lm, lt = (lh, la) if side == "home" else (la, lh)
        rs = reasons(st, league, side_pre, my, their, left, ml, has_ball, ball_txt, lm, lt, pre_value, fit, side == "home")
        if half_ball == side:                               # counted in the numbers above; said in the breakdown
            rs.append(("half", {}))
        if not up and not substantial(rs, my == their):       # the reasons get it up; value keeps it up
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
FINALS = set()                # games seen final (a new one = grade the board right away)
WATCHING = [0]
PRICED = [0]                  # live games with a sportsbook price this cycle                # live games seen in the last cycle (the dashboard says whether games are going)


BOVADA = "https://www.bovada.lv/services/sports/event/v2/events/A/description/{path}?marketFilterId=def&liveOnly=true&lang=en"
BOVADA_OLD = "https://www.bovada.lv/services/sports/event/coupon/events/A/description/{path}?marketFilterId=def&liveOnly=true&lang=en"
BOVADA_ALL = "https://www.bovada.lv/services/sports/event/v2/events/A/description/{path}?marketFilterId=def&lang=en"
BOVADA_SPORT = "https://www.bovada.lv/services/sports/event/v2/events/A/description/{sport}?marketFilterId=def&liveOnly=true&lang=en"
# (the liveOnly feed went empty on 2026-09-27 while games were live: the full feed still flags each event live=True)
ESPN_ODDS = "https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/events/{eid}/competitions/{eid}/odds"
BOVADA_PATH = {"nfl": "football/nfl", "ncaaf": "football/college-football", "nba": "basketball/nba",
               "ncaab": "basketball/college-basketball", "nhl": "hockey/nhl", "mlb": "baseball/mlb"}
AGREE = 0.08                  # the sportsbook (Bovada) and Action Network must agree within 8 points of win chance


def _clean(name):
    return re.sub(r"\s*\(#?\d+\)\s*", " ", str(name or "")).strip()


def bovada_live(league):
    """[{home, away, ml_home, ml_away}] - the sportsbook's LIVE moneylines right now."""
    data = []
    path = BOVADA_PATH[league]
    for url in (BOVADA, BOVADA_OLD, BOVADA_ALL, BOVADA_SPORT):   # live feed, older address, full feed, whole sport
        try:
            data = _get(url.format(path=path, sport=path.split("/")[0]))
        except Exception as e:                               # noqa: BLE001
            sd.ERRORS.append(f"bovada live {league}: {str(e)[:100]}")
            BOOKS[league] = f"error {str(e)[:60]}"
            continue
        data = [{**g, "events": [e for e in g.get("events") or [] if e.get("live")]}
                for g in (data if isinstance(data, list) else []) if isinstance(g, dict)
                and path in str(((g.get("path") or [{}])[0] or {}).get("link", path))]     # only this league's group
        if any(g.get("events") for g in data):
            break
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


ESPN_SB = "https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard"
_ELO = {}
SEEN = set()                  # plays that qualified last cycle: a play only shows once it qualifies twice in a row


def espn_scores(league):
    """{espn event id: (home score, away score)} for games going right now - a second source for the score."""
    try:
        d = _get(ESPN_SB.format(path=sd.LEAGUES[league][0]) + "?limit=300" + (sd.LEAGUES[league][1] or ""))
    except Exception as e:                                   # noqa: BLE001
        sd.ERRORS.append(f"espn scores {league}: {str(e)[:80]}")
        return {}
    out = {}
    for ev in d.get("events") or []:
        c = (ev.get("competitions") or [{}])[0]
        t = {x.get("homeAway"): x for x in c.get("competitors") or []}
        try:
            out[str(ev.get("id"))] = (int(float(t["home"]["score"])), int(float(t["away"]["score"])))
        except (KeyError, TypeError, ValueError):
            pass
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


def _ok(ml):
    """A real moneyline: +100 or longer, -100 or shorter (books list 0 while a line's pulled)."""
    return isinstance(ml, int) and (ml >= 100 or ml <= -100)


def two_books(dk, bov):
    """The live price: Bovada's line (a real sportsbook - enough on its own); DraftKings' (via ESPN) when Bovada has
    none. confirmed = the other book roughly agrees, which also switches off the too-far-off filter."""
    ok = [_ok(x[0]) and _ok(x[1]) for x in (dk, bov)]
    if ok[1]:
        return bov[0], bov[1], ok[0] and abs(sd.no_vig(*bov) - sd.no_vig(*dk)) <= AGREE
    if ok[0]:
        return dk[0], dk[1], False
    return None, None, False


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


def locked_sides(log, now):
    """{game id: side} we're already on today - a live play (or today's pregame pick) locks the game in: we never go
    back and back the other team in the same game."""
    today = now.astimezone(PT).date().isoformat()
    out = {}
    try:
        with open(os.path.join(sd.DATA, "picks.json")) as f:
            for pk in json.load(f):
                if pk.get("date") == today and pk.get("status") != "waiting":
                    for leg in pk.get("legs") or []:
                        if leg.get("market") != "total":     # (an over/under isn't a side)
                            out.setdefault(leg["game_id"], leg["side"])
    except (OSError, ValueError, KeyError):
        pass
    for mid, side in stl.our_picks().items():               # 🎾 our pregame tennis picks lock their match too
        out.setdefault(f"tennis:{mid}", str(side))
    for pid, e in log.get("plays", {}).items():
        if e.get("date") == today and e.get("result") != "void":
            out[pid.rsplit(":", 1)[0]] = pid.rsplit(":", 1)[1]
    return out


def board(plays, showing=()):
    """Max 2 at once: plays already up keep their slot while they still qualify; open slots go to the best edge."""
    return sorted(plays, key=lambda x: (x["id"] not in showing, -x["edge"]))[:MAX_PLAYS]


def _judge(lg, ang, box, g, dk_f, scores_f, books_f, model, elo, st, now, showing, judged):
    """One live game -> its plays (marked judged when it had a real price)."""
    plays = []
    es = scores_f[lg].result().get(g["id"].split(":", 1)[1]) if lg in scores_f else None
    if es is not None and es != (_score(box, "home"), _score(box, "away")):
        return plays                                       # the two score feeds disagree (a few seconds apart): wait
    mlh, mla, checked = two_books(dk_f.result(), book_line(books_f[lg].result() if lg in books_f else [], g))
    PRICED[0] += mlh is not None and mla is not None
    if mlh is None or mla is None:
        return plays                                       # the book paused its line: wait
    judged.add(g["id"])
    params = model["params"].get(lg) or sm.default_params(lg)
    f = elo[lg].features(g)
    mkt = sm.market_p(g)
    p_model = sm.final_p(params, f, g) if mkt is not None else None
    ball = ball_value(lg, ang, box)
    ball_txt = (box.get("situation") or {}).get("display_short") or "" if ball else ""
    rec = None
    if lg in ("nfl", "ncaaf") and int(box.get("period") or 0) == 2:
        rec = second_half_ball(lg, g)            # who gets the ball to start the 2nd half
        if rec:
            if not ball and halftime(lg, ang, box):  # halftime: they have the ball next
                ball = HALF_BALL if rec == "home" else -HALF_BALL
                ball_txt = ""                        # not a scoring-range drive: no "they got the ball" reason
            elif not halftime(lg, ang, box):         # 2nd quarter: it counts more as the half runs out
                mins = _clock_min(box.get("clock"))
                ball += (HALF_BALL if rec == "home" else -HALF_BALL) * (1 - (mins if mins is not None else 15) / 15)
    for pl in evaluate(lg, g, box, mlh, mla, st, p_model, mkt, ball, ball_txt, now.hour, checked, showing, rec):
        pl["an_id"] = ang.get("id")
        plays.append(pl)
    return plays


NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "d503-live-7b1123")     # subscribe in the free ntfy app to get the pushes
DASH_URL = "https://d503therapper.github.io/autonomous-crypto-engine/sports/"
NOTIFY = [True]               # (tests turn it off)


def notify(pl, back=False):
    """📲 Push a new live bet to phones through ntfy (free, no account): the team, the price, the score. Never blocks."""
    if not NOTIFY[0] or not NTFY_TOPIC:
        return
    o = f"+{pl['odds']}" if pl["odds"] > 0 else str(pl["odds"])
    body = f"{pl['team']} ML {o} — {pl.get('score', '')}, {pl.get('clock', '')}. {pl.get('line', '')}".strip()
    req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=body.encode(), method="POST", headers={
        "Title": f"{'BACK ON: ' if back else ''}LIVE PLUS MONEY: {pl['team']} {o}".encode("latin-1", "ignore").decode("latin-1"),
        "Tags": "rotating_light", "Click": DASH_URL, "Priority": "high"})
    try:
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:                                   # noqa: BLE001 - a push failing never stops the watch
        sd.ERRORS.append(f"notify: {str(e)[:60]}")


def cycle(games, model, log, now=None, st=None, showing=(), prev=None):
    """Scan every live game -> the plays on the board right now. Max 2 at a time, no limit per day: a play that's
    up stays up while its value's still there (`showing`); a new one only takes a slot that's open."""
    now = now or datetime.now(timezone.utc)
    st = sc.load() if st is None else st
    key = (id(games), len(games))
    if _ELO.get("key") != key:                                   # ratings replay once per games reload, not every cycle
        _ELO.update(key=key, elo=sm.ratings(games, model))
    elo = _ELO["elo"]
    plays = []
    judged = set()                # games priced and judged this check (the rest were paused / out of sync)
    WATCHING[0] = PRICED[0] = 0
    BOOKS.clear()
    with ThreadPoolExecutor(12) as ex:                          # everything in parallel: live lines move fast
        angs_by = dict(zip(sd.LEAGUES, ex.map(fetch_live, sd.LEAGUES)))
        live_lgs = [lg for lg, angs in angs_by.items()
                    if any((a.get("boxscore") or {}).get("period") and str(a.get("status") or "").lower() not in DONE
                           for a in angs)]
        scores_f = {lg: ex.submit(espn_scores, lg) for lg in live_lgs}
        books_f = {lg: ex.submit(bovada_live, lg) for lg in live_lgs}
        todo = []
        for lg, angs in angs_by.items():
            for ang in angs:
                status = str(ang.get("status") or ang.get("real_status") or "").lower()
                box = ang.get("boxscore") or {}
                if status in DONE or not box.get("period"):
                    _grade(log, ang)
                    if status in ("complete", "closed", "final") and ang.get("id"):
                        FINALS.add(ang.get("id"))
                    continue
                WATCHING[0] += 1                               # a game going right now
                g = _match(games, lg, ang)
                if g:
                    todo.append((lg, ang, box, g, ex.submit(dk_live, lg, g)))
        for lg, ang, box, g, dk_f in todo:
            try:
                plays += _judge(lg, ang, box, g, dk_f, scores_f, books_f, model, elo, st, now, showing, judged)
            except Exception as e:                           # noqa: BLE001 - one bad game never sinks the whole check
                sd.ERRORS.append(f"live {g['id']}: {type(e).__name__} {str(e)[:80]}")
    if TENNIS_ON[0]:
        try:                                                 # 🎾 tennis: same board, same rules
            plays += tennis_plays(log, now, showing, judged, plays)
        except Exception as e:                               # noqa: BLE001 - tennis never sinks the whole check
            sd.ERRORS.append(f"live tennis: {type(e).__name__} {str(e)[:80]}")
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    for p in plays:
        p["seen"], p["paused"] = stamp, False
    have = {p["id"] for p in plays}
    for pid, old in (prev or {}).items():                    # a play that's up, on a game the book paused this check:
        if pid in have or pid not in showing or pid.rsplit(":", 1)[0] in judged:
            continue                                         # (judged and no longer value = it comes down)
        seen = datetime.strptime(old.get("seen", stamp)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        if (now - seen).total_seconds() <= PAUSE_HOLD_S:
            plays.append({**old, "paused": True})            # hold it - the line's coming back
    uniq = {}
    for p in plays:                                          # one play per game side (a game can be on two days' lists)
        if p["id"] not in uniq or (uniq[p["id"]].get("paused") and not p.get("paused")):
            uniq[p["id"]] = p
    plays = list(uniq.values())
    locked = locked_sides(log, now)
    plays = [p for p in plays if locked.get(p["id"].rsplit(":", 1)[0], p["id"].rsplit(":", 1)[1]) == p["id"].rsplit(":", 1)[1]]
    fresh = {p["id"] for p in plays}
    plays = [p for p in plays if p["id"] in SEEN or p["id"] in showing]   # held two checks in a row (no blips)
    SEEN.clear()
    SEEN.update(fresh)
    plays = board(plays, showing)
    for pl in plays:                                          # log the first time each play goes up (graded later)
        if pl["id"] not in log["plays"]:
            log["plays"][pl["id"]] = {"posted": now.strftime("%Y-%m-%dT%H:%MZ"), "team": pl["team"], "odds": pl["odds"],
                                      "league": pl["league"], "score_at_post": pl["score"], "clock_at_post": pl["clock"],
                                      "side": pl["id"].rsplit(":", 1)[1], "an_id": pl["an_id"], "result": None,
                                      "reasons": pl["reasons"], "date": now.astimezone(PT).date().isoformat(),
                                      "p": pl["p"]}
            log["plays"][pl["id"]].update({k: pl[k] for k in ("tour", "match", "double_down", "tennis", "sport", "opp")
                                           if k in pl and pl["league"] == "tennis"})
            notify(pl)                                        # a new live bet: push it to everybody's phone
        elif log["plays"][pl["id"]].get("down") and log["plays"][pl["id"]].get("result") is None:
            log["plays"][pl["id"]].pop("down", None)          # it came down, now it's value again: back on top + a push
            notify(pl, back=True)
        pl["posted"] = log["plays"][pl["id"]]["posted"]
        e = log["plays"][pl["id"]]
        if not pl.get("paused") and e.get("result") is None:     # the longest the line got while the play was up
            e["best_odds"] = max(e.get("best_odds", e["odds"]), pl["odds"])
    for pid in showing:                                       # came down this check: remember, in case it comes back
        if pid not in {p["id"] for p in plays} and pid in log["plays"]:
            log["plays"][pid]["down"] = True
    return plays


# ---------------------------------------------------------------- 🎾 tennis
TENNIS_STALE_S = 600          # ESPN's tennis score runs behind: a score that hasn't moved in 10 minutes (a game takes
                              # ~4) can't be trusted against a live price - no new play, a play that's up holds paused
TENNIS_STRONG_PRE = 0.60      # "the engine liked this player pregame": one of our picks, or 60%+ on our own numbers
TENNIS_MAX_DOWN = 2           # the score isn't as bad as the price says: at most a break (2 games) down in this set
SCORE_SEEN = {}               # match id -> (score, first time we saw it): how long the score has sat still
TENNIS = {"watching": 0, "priced": 0, "stale": 0, "suspended": 0, "books": ""}
TENNIS_ON = [True]
_TN_CSV = [0.0]               # last time ungraded tennis plays were checked against matches.csv


def tennis_feeds():
    """(live match rows from ESPN's ATP + WTA scoreboards, all their rows (for grading), Bovada live tennis lines)."""
    rows = []
    for tour in stn.TOURS:
        try:
            rows += stn.parse_espn(_get(stn.ESPN.format(tour=tour)), tour)
        except Exception as e:                               # noqa: BLE001
            sd.ERRORS.append(f"espn tennis {tour}: {str(e)[:80]}")
    lines, ok = [], False
    for url in (BOVADA, BOVADA_OLD, BOVADA_ALL):             # live feed, older address, full feed (live=True flag)
        try:
            lines = stn.parse_bovada(_get(url.format(path="tennis", sport="tennis")), live=True)
            ok = True
        except Exception as e:                               # noqa: BLE001
            sd.ERRORS.append(f"bovada live tennis: {str(e)[:80]}")
            TENNIS["books"] = f"error {str(e)[:60]}"
            continue
        if lines:
            break
    if ok:
        TENNIS["books"] = f"{len(lines)} live lines"
    return [r for r in rows if stn._state(r) == "live"], rows, lines


def tennis_stale(m, now_s):
    """ESPN's score is behind: it hasn't moved in TENNIS_STALE_S, or the feed says the match is held up."""
    key = (m.get("sets1"), m.get("sets2"), m.get("pts1"), m.get("pts2"))
    old = SCORE_SEEN.get(m["id"])
    if not old or old[0] != key:
        SCORE_SEEN[m["id"]] = (key, now_s)
        old = SCORE_SEEN[m["id"]]
    held = any(k in str(m.get("detail") or "").lower() for k in ("delay", "suspend", "rain", "interrupt"))
    return held or now_s - old[1] > TENNIS_STALE_S


def _ord(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _on_serve(s, side):
    """Is the current set on serve from `side`'s view? True / False / None (the feed doesn't say who's serving)."""
    ga, gb = s["games"] if side == 1 else s["games"][::-1]
    if ga == gb:
        return True
    if s["server"] not in (1, 2) or abs(ga - gb) > 1:
        return False if abs(ga - gb) > 1 else None
    nxt = s["server"] if side == 1 else 3 - s["server"]     # 1 = our player serves next
    first = nxt if (ga + gb) % 2 == 0 else 3 - nxt          # who served the set's first game
    leader = 1 if ga > gb else 2
    return leader == first                                  # the set's first server one game up = on serve


def tennis_situation(s, side, he):
    """'dropped the first set, but it's on serve in the 2nd' - the score from our player's side, in plain words."""
    sm_, st_ = s["sets"] if side == 1 else s["sets"][::-1]
    gm, gt = s["games"] if side == 1 else s["games"][::-1]
    n, os_ = s["set_no"], _on_serve(s, side)
    if sm_ < st_:
        first = "dropped the first set" if len(s["done"]) == 1 else f"is down {sm_}-{st_} in sets"
        if (gm, gt) == (0, 0):
            return first + f" and the {_ord(n)} is just starting"
        if gm > gt:
            return first + f", but {he}'s up {gm}-{gt} in the {_ord(n)}"
        if os_:
            return first + f", but the {_ord(n)} is on serve ({gm}-{gt})"
        return first + f" and trails {gm}-{gt} in the {_ord(n)}"
    if sm_ > st_:
        return f"is up {sm_}-{st_} in sets" + (f" and {gm}-{gt} in the {_ord(n)}" if (gm, gt) != (0, 0) else "")
    if gm < gt:
        return f"is down {gm}-{gt} in the {_ord(n)} set" + (" (on serve)" if os_ else "")
    if gm > gt:
        return f"is up {gm}-{gt} in the {_ord(n)} set"
    return f"is level at {gm}-{gt} in the {_ord(n)} set" if n > 1 or gm else "is level"


def tennis_reasons(s, side, p, ml, ours, model_pre):
    """The substantial reasons, tennis: the engine liked this player pregame (our pick, or a strong favorite on our
    numbers) AND the score state isn't as bad as the price implies."""
    out = []
    if ours:
        out.append(("ours", {}))
    if model_pre is not None and model_pre >= TENNIS_STRONG_PRE:
        out.append(("strong", {"p": model_pre}))
    gm, gt = s["games"] if side == 1 else s["games"][::-1]
    be = 1 / sd.decimal(ml)
    if gt - gm <= TENNIS_MAX_DOWN and p >= be + 0.02:
        out.append(("state", {"be": be, "p": p, "on_serve": _on_serve(s, side)}))
    return out


def tennis_substantial(rs):
    kinds = {k for k, _ in rs}
    return "state" in kinds and bool(kinds & {"ours", "strong"})


def _trailing(s, side):
    sm_, st_ = s["sets"] if side == 1 else s["sets"][::-1]
    gm, gt = s["games"] if side == 1 else s["games"][::-1]
    return sm_ < st_ or (sm_ == st_ and gm < gt)


def tennis_words(pl, s, side, rs, used, hold):
    """(the short line, the breakdown) in our voice - he/she by tour, fresh wording, no repeats on the board."""
    import sports_breakdown as sb
    v = sb.Voice(pl["id"], used)
    wta = pl["tour"] == "wta"
    he, him, his = ("she", "her", "her") if wta else ("he", "him", "his")
    He = he.capitalize()
    me = stn._say_name(pl["team"])
    o = f"+{pl['odds']}"
    sit = tennis_situation(s, side, he)
    kinds = dict(rs)
    pct, be = round(100 * pl["p"]), round(100 * kinds["state"]["be"]) if "state" in kinds else None
    if pl["double_down"]:
        line = v.say("tl_dd", [
            f"🔁 Double down — we had {him} pregame, {he} {sit}, now {he}'s {o} and the math says that's too long.",
            f"🔁 Double down. {me} was our pick before the first serve. {He} {sit} and the book let {him} drift to {o} — we're going back in.",
            f"🔁 Double down on {me}: {he} {sit}, the price went to {o}, and the numbers still like {him} way more than that.",
            f"🔁 We had {me} pregame and we're not jumping off. {He} {sit} — {o} is too long for a player this good."], must=True)
    elif _trailing(s, side):
        line = v.say("tl_trail", [
            f"🎾 {me} {sit}, and the book overreacted: {o} for a player we had as the favorite.",
            f"🎾 {me} came in as the better player on our numbers. {He} {sit} — {o} is too big a price for that.",
            f"🎾 The book's pricing {me} like it's over at {o}. {He} {sit}. It ain't over.",
            f"🎾 {me} {sit}. Everybody's jumping off — we're jumping on at {o}.",
            f"🎾 {me} at {o}? {He} {sit}, but {he}'s still the better player out there. Get in."], must=True)
    else:
        line = v.say("tl_level", [
            f"🎾 {me} {sit} and still plus money at {o}? We'll take that all day.",
            f"🎾 {me} {sit} and the book's still got {him} as the dog ({o}). The numbers say otherwise.",
            f"🎾 {o} on {me}, who {sit}? The price is behind the match. Hammer it."], must=True)
    bd = []
    if "ours" in kinds:
        bd.append(v.say("tl_ours", [f"🧠 {me} was one of our tennis picks today — the engine liked {him} before the first ball.",
                                    f"🧠 We posted {me} pregame. Same player, way better price now.",
                                    f"🧠 {me} was already on our tennis card. Now the live price is doing us a favor."]))
    if "strong" in kinds:
        sp_ = round(100 * kinds["strong"]["p"])
        bd.append(v.say("tl_strong", [f"💪 On our numbers {me} came in at {sp_}% to win this match.",
                                      f"💪 Before the first serve the engine had {me} winning this {sp_}% of the time.",
                                      f"💪 {me} was the better player coming in — {sp_}% on our numbers."]))
    if "state" in kinds:
        hp = round(100 * hold)
        serve = {True: " and it's on serve", False: "", None: ""}[kinds["state"]["on_serve"]]
        bd.append(v.say("tl_state", [f"🎾 Score check: {me} {sit}{serve}. {He} holds serve {hp}% of the time on our numbers — far from over.",
                                     f"🎾 {me} {sit}{serve}. A player who holds {hp}% of {his} service games is still very much in this.",
                                     f"🎾 Where it stands: {me} {sit}{serve}. {He} holds {hp}% of the time — one break changes everything."]))
        bd.append(v.say("tl_math", [f"📐 The point-by-point model (sets, games, points, who's serving) gives {him} {pct}% from here. {o} only needs {be}%.",
                                    f"📐 Run every point from this score: {me} wins it {pct}% of the time. The price needs {be}%.",
                                    f"📐 Our tennis model plays it out point by point from right here: {pct}% for {me}. Break-even at {o} is {be}%."]))
    bd.append(v.say("tl_bottom", ["🎯 The numbers are ahead of the book on this one. We're on it.",
                                  "🎯 The price hasn't caught up to the match. Get in before it does.",
                                  "🎯 Live tennis swings fast — this is the window. We're in."], must=True))
    return line, [x for x in bd if x]


def evaluate_tennis(m, line, flip, pre, ours_side, hold=(), used=None):
    """Both players of one live match -> plays that clear every bar (plus money, LIVE_MIN_EDGE, the tuned min p,
    the MAX_GAP guard vs the price, the substantial reasons). line: Bovada's live line (not suspended)."""
    pre_p1 = pre.get("mkt_p1") if pre.get("mkt_p1") is not None else pre.get("model_p1")
    if pre_p1 is None:
        return []                                             # no pre-match number: no bet
    ml1, ml2 = (line["b_ml"], line["a_ml"]) if flip else (line["a_ml"], line["b_ml"])
    if not (_ok(ml1) and _ok(ml2)):
        return []
    p1, (pa, pb), s = stl.p1_live(m, pre_p1)
    book1 = sd.no_vig(ml1, ml2)
    if abs(p1 - book1) > MAX_GAP:
        return []                  # the price and the score don't agree (a stale score, or the book knows something)
    out = []
    used = set() if used is None else used
    for side, p, ml in ((1, p1, ml1), (2, 1 - p1, ml2)):
        pid = f"tennis:{m['id']}:{side}"
        up = pid in hold
        edge = p * sd.decimal(ml) - 1
        if ml < DOG_MIN or edge < (STAY_EDGE if up else LIVE_MIN_EDGE) or p < (STAY_P if up else min_p()) \
                or (up and ml > STAY_MAX_ODDS) or (not up and ml > LIVE_MAX_ODDS):
            continue
        mp = pre.get("model_p1")
        model_pre = None if mp is None else (mp if side == 1 else 1 - mp)
        ours = ours_side == side
        rs = tennis_reasons(s, side, p, ml, ours, model_pre)
        if not up and not tennis_substantial(rs):
            continue
        me, them = (m["p1_name"], m["p2_name"]) if side == 1 else (m["p2_name"], m["p1_name"])
        tour = stn.tour_of(m)
        pl = {"id": pid, "league": "tennis", "tour": tour, "emoji": "🎾",
              "sport": "Women's Tennis" if tour == "wta" else "Men's Tennis", "team": me, "opp": them, "odds": ml,
              "edge": round(edge, 4), "p": round(p, 3), "score": stl.score_text(m, s), "clock": stl.clock_text(m, s),
              "ball": "", "an_id": None, "reasons": [k for k, _ in rs], "match": m["id"], "double_down": bool(ours and _trailing(s, side)),
              "tennis": {"sets": list(s["sets"]), "games": list(s["games"]), "done": [list(x) for x in s["done"]],
                         "pts": list(s["pts"]) if s["pts"] else None, "set_no": s["set_no"], "side": side}}
        pl["line"], pl["breakdown"] = tennis_words(pl, s, side, rs, used, stl.hold_p(pa if side == 1 else pb))
        out.append(pl)
    return out


def _tennis_result(m, side):
    st_ = stn._state(m)
    if st_ == "void" or (st_ == "retired" and int(m.get("done") or 0) < 1):
        return "void"
    if st_ in ("final", "retired") and int(m.get("winner") or 0) in (1, 2):
        return "won" if int(m["winner"]) == int(side) else "lost"
    return None


def grade_tennis(log, rows):
    """Grade logged tennis live plays once their match is over (retired before a set was done / walkover = void)."""
    by = {r["id"]: r for r in rows}
    for e in log["plays"].values():
        if e.get("league") == "tennis" and e.get("result") is None and e.get("match") in by:
            e["result"] = _tennis_result(by[e["match"]], e["side"])


def _grade_tennis_csv(log, now_s):
    """Plays whose match already left the live scoreboard: check the engine's stored results (every 10 minutes)."""
    if now_s - _TN_CSV[0] < 600 or not any(e.get("league") == "tennis" and e.get("result") is None for e in log["plays"].values()):
        return
    _TN_CSV[0] = now_s
    grade_tennis(log, list(stn.load_matches().values()))


def tennis_plays(log, now, showing=(), judged=None, taken=()):
    """Every live ATP / WTA match -> tennis plays (graded plays settle here too)."""
    judged = set() if judged is None else judged
    live, rows, lines = tennis_feeds()
    grade_tennis(log, rows)
    _grade_tennis_csv(log, time.time())
    pre = stl.load_prematch()
    ours = stl.our_picks()
    TENNIS.update(watching=len(live), priced=0, stale=0, suspended=0)
    import sports_breakdown as sb
    used = sb.slang_in([x for p in taken for x in [p.get("line", "")] + list(p.get("breakdown") or [])])
    out = []
    now_s = time.time()
    for m in sorted(live, key=lambda r: r["id"]):
        stale = tennis_stale(m, now_s)
        ln, flip = stn.match_line(m, lines, hours=12)
        if ln is None or m["id"] not in pre:
            continue
        if ln.get("suspended"):
            TENNIS["suspended"] += 1
            continue                                         # the book suspended it: wait (a play that's up holds)
        TENNIS["priced"] += 1
        if stale:
            TENNIS["stale"] += 1
            continue                                         # the score's behind: never act on it
        judged.add(f"tennis:{m['id']}")
        out += evaluate_tennis(m, ln, flip, pre[m["id"]], ours.get(m["id"]), showing, used)
    return out


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


_DATA = {}


def _data(reload=False):
    """Games, model and key-player edges: loaded once, refreshed every ~10 minutes (not every 10-second check)."""
    if reload or not _DATA or time.time() - _DATA["t"] > 600:
        games = sd.load_games()
        sp.CACHE = sp.load()
        sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)
        _DATA.update(t=time.time(), games=games, model=json.load(open(os.path.join(sd.DATA, "model.json"))))
    return _DATA["games"], _DATA["model"]


def run():
    t0 = time.time()
    games, model = _data()
    log = json.load(open(LOG)) if os.path.exists(LOG) else {"plays": {}}
    try:
        prev = {p["id"]: p for p in json.load(open(LIVE_JSON)).get("plays") or []}
    except (OSError, ValueError):
        prev = {}
    _TUNED.update(self_tune(log))
    plays = cycle(games, model, log, showing=list(prev), prev=prev)
    health = health_check()
    out = {"updated": int(time.time() * 1000), "plays": plays, "record": record(log),
           "live_games": WATCHING[0] + TENNIS["watching"], "tennis": dict(TENNIS),
           "health": health,
           "priced": PRICED[0], "errors": sd.ERRORS[-3:], "books": dict(BOOKS),
           "took_s": round(time.time() - t0, 1)}
    del sd.ERRORS[:]
    os.makedirs(os.path.dirname(LIVE_JSON), exist_ok=True)
    with open(LIVE_JSON, "w") as f:
        json.dump(out, f, indent=1)
    with open(LOG, "w") as f:
        json.dump(log, f, indent=1, sort_keys=True)
    print(f"{datetime.now(timezone.utc):%H:%M:%S} live ({time.time() - t0:.1f}s): {WATCHING[0]} games live, {PRICED[0]} priced by a sportsbook, {len(plays)} plays on the board" + "".join(f"\n   {p['team']} {p['odds']:+d} ({p['score']}, {p['clock']}) edge {p['edge']:.1%}" for p in plays))
    return plays


TUNE = os.path.join(sd.DATA, "live_tune.json")
TUNE_N = 10                   # graded live bets (with the chance we gave them) before the engine grades itself


def self_tune(log):
    """The live feature grades itself: the chance we gave our last 30 live bets vs how often they actually hit.
    Hitting less than we said (by 8%+) = raise the bar for new bets; hitting more = ease it back toward the floor."""
    rows = sorted((e for e in log["plays"].values() if e.get("result") in ("won", "lost") and e.get("p")),
                  key=lambda e: e["posted"])[-30:]
    try:
        with open(TUNE) as f:
            t = json.load(f)
    except (OSError, ValueError):
        t = {"min_p": LIVE_MIN_P}
    if len(rows) < TUNE_N or t.get("n_seen") == len(rows) and t.get("last") == rows[-1]["posted"]:
        return t
    said = sum(e["p"] for e in rows) / len(rows)
    hit = sum(e["result"] == "won" for e in rows) / len(rows)
    mp = t.get("min_p", LIVE_MIN_P)
    if hit < said - 0.08:
        mp = min(0.55, mp + 0.03)
    elif hit > said + 0.05:
        mp = max(LIVE_MIN_P, mp - 0.02)
    t = {"min_p": round(mp, 3), "said": round(said, 3), "hit": round(hit, 3), "n": len(rows), "n_seen": len(rows),
         "last": rows[-1]["posted"], "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    with open(TUNE, "w") as f:
        json.dump(t, f, indent=1)
    print(f"LIVE SELF-CHECK: said {said:.0%}, hit {hit:.0%} over {len(rows)} -> new bets need {mp:.0%}+", flush=True)
    return t


_TUNED = {}


def min_p():
    return max(LIVE_MIN_P, _TUNED.get("min_p", LIVE_MIN_P))


def health_check():
    """The live feature checks itself every cycle: games going but few or no sportsbook prices = something's broken.
    Problems go into live.json ("health") and the log, loud."""
    issues = []
    if WATCHING[0] >= 3 and PRICED[0] < WATCHING[0] / 2:
        issues.append(f"only {PRICED[0]} of {WATCHING[0]} live games have a sportsbook price")
    empty = [lg for lg, v in BOOKS.items() if v.startswith("0 groups") or v.startswith("error") or " 0 events" in v]
    if empty and WATCHING[0]:
        issues.append("Bovada has no live lines for " + ", ".join(sorted(empty)))
    for x in issues:
        print(f"HEALTH: {x}", flush=True)
    return issues


def any_live_soon(games, within_min=45):
    """Is anything live now or starting soon? (else the watcher can rest) - 🎾 a priced tennis match counts too."""
    now = datetime.now(timezone.utc)
    if TENNIS_ON[0] and stl.any_live_soon(now, within_min):
        return True
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


GRADER = [None]              # the background grading job (a game ended): the live board never waits on it


def grade_in_background(msg):
    """Grade + rebuild the page in a separate process - it can take minutes on the runner, and the live board must keep
    updating every few seconds meanwhile. One at a time."""
    import subprocess
    if GRADER[0] is not None and GRADER[0].poll() is None:
        return False
    GRADER[0] = subprocess.Popen([sys.executable, "-u", "-c", f"import sports_live; sports_live.publish_results({msg!r})"])
    print(f"{datetime.now(timezone.utc):%H:%M:%S} grading in the background", flush=True)
    return True


def grading():
    return GRADER[0] is not None and GRADER[0].poll() is None


def publish_results(msg):
    """Grade the picks the moment games end and rebuild the dashboard (sports.quick), then push picks + page to main."""
    import importlib
    import sports
    import sports_dashboard
    try:
        importlib.reload(sports_dashboard)                   # the watcher runs for 50 min: always rebuild the page
        importlib.reload(sports)                             # with the newest pulled code, never an older look
        _git("pull", "-q", "--rebase", "--autostash", "-X", "theirs")   # grade the latest picks, never a stale copy
        graded, posted = sports.quick()
    except Exception as e:                                   # noqa: BLE001 - never stop watching over this
        print(f"quick grade failed: {e}", flush=True)
        return
    paths = [LOG, TUNE, os.path.join(sd.DATA, "picks.json"), "docs/sports/index.html", "docs/sports/reads.json",
             os.path.join(sd.DATA, "games")]
    _git("add", *[p for p in paths if os.path.exists(p)])
    if _git("diff", "--cached", "--quiet").returncode == 0:
        return
    _git("commit", "-qm", f"{msg}: {len(graded)} graded, {len(posted)} new")
    for _ in range(4):
        _git("pull", "-q", "--rebase", "--autostash", "-X", "theirs")
        if _git("push", "-q").returncode == 0:
            return
        time.sleep(3)


def publish(msg):
    """Commit + push the live log to main - only when a play is first logged or graded. (live.json itself only
    goes out on the live-data branch; phones read it there.)"""
    _git("add", *[p for p in (LOG, TUNE) if os.path.exists(p)])
    if _git("diff", "--cached", "--quiet").returncode == 0:
        return
    _git("commit", "-qm", msg)
    for _ in range(4):
        _git("pull", "-q", "--rebase", "--autostash", "-X", "theirs")
        if _git("push", "-q").returncode == 0:
            return
        time.sleep(3)


def _board_key():
    try:
        d = json.load(open(LIVE_JSON))
    except (OSError, ValueError):
        return None
    return json.dumps([{k: v for k, v in p.items() if k not in ("posted", "seen")} for p in d.get("plays") or []], sort_keys=True) \
        + str(d.get("live_games"))


def _log_key():
    try:
        return open(LOG).read()
    except OSError:
        return None


CODE = ("sports_live.py", "sports_comeback.py", "sports_data.py", "sports_model.py", "sports_tennis.py",
        "sports_tennis_live.py")


def _code_hash():
    import hashlib
    h = hashlib.sha1()
    for p in CODE:
        try:
            with open(p, "rb") as f:
                h.update(f.read())
        except OSError:
            pass
    return h.hexdigest()


def queue_next():
    """Queue the next watch right behind this one (GitHub's 30-minute schedule can skip runs - a skipped run once left
    the live board stale). Needs GH_TOKEN (the workflow passes its own token). True if queued."""
    if not os.environ.get("GH_TOKEN"):
        return False
    import subprocess
    r = subprocess.run(["gh", "workflow", "run", "sports-live.yml", "--ref", "main"], capture_output=True, text=True)
    print(f"{datetime.now(timezone.utc):%H:%M:%S} next watch queued: {r.returncode == 0} {r.stderr.strip()[:100]}", flush=True)
    return r.returncode == 0


def loop(minutes, every_s=5):
    """Watch live games every `every_s` seconds for `minutes`. Phones see every change right away (live-data
    branch, plus a heartbeat every minute); the graded log goes to main when it changes. Rests when nothing's live."""
    end = time.time() + minutes * 60
    code = _code_hash()
    queued = False
    games, idle_since, started, last_board, last_log, last_push = None, None, False, None, _log_key(), 0.0
    finals_seen = None
    print(f"{datetime.now(timezone.utc):%H:%M:%S} watch starting", flush=True)
    _git("fetch", "-q", "origin", LIVE_BRANCH)                  # pick up where the last watch left off: plays that
    board = _git("show", f"origin/{LIVE_BRANCH}:live.json")      # are up stay up (they don't have to re-qualify)
    if board.returncode == 0 and board.stdout.strip():
        with open(LIVE_JSON, "w") as f:
            f.write(board.stdout)
    while time.time() < end:
        if games is None or int(time.time()) % 600 < every_s:          # pull the latest games/model every ~10 min
            print(f"{datetime.now(timezone.utc):%H:%M:%S} pulling", flush=True)
            if not grading():                                # (the grader has git busy - pull next time)
                _git("pull", "-q", "--rebase", "--autostash", "-X", "theirs")
            if _code_hash() != code and not grading():      # new live code landed: restart on it right now, so a fix
                left = max(1.0, (end - time.time()) / 60)   # never waits behind a watch running the old code
                print(f"{datetime.now(timezone.utc):%H:%M:%S} new code - restarting on it ({left:.0f} min left)", flush=True)
                os.execv(sys.executable, [sys.executable, "-u", "sports_live.py", "--loop", f"{left:.1f}"])
            print(f"{datetime.now(timezone.utc):%H:%M:%S} loading data", flush=True)
            games, _ = _data(reload=True)
        if any_live_soon(games) and not queued:
            queued = queue_next()
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
        except Exception as e:                                      # noqa: BLE001 - keep watching, and say why
            import traceback
            print(f"live cycle error: {e}", flush=True)
            traceback.print_exc()
            try:
                out = json.load(open(LIVE_JSON))
                out["crash"] = traceback.format_exc()[-800:]
                with open(LIVE_JSON, "w") as f:
                    json.dump(out, f, indent=1)
            except (OSError, ValueError):
                pass
        board = _board_key()
        if board != last_board or time.time() - last_push > 60:
            print(f"{datetime.now(timezone.utc):%H:%M:%S} pushing the board", flush=True)
            if push_live():
                last_board, last_push = board, time.time()
        if _log_key() != last_log and not grading():            # (git one job at a time)
            publish(f"live log {datetime.now(timezone.utc):%H:%M}")
            last_log = _log_key()
        if finals_seen is None:                                   # a watch starts: grade whatever ended meanwhile
            finals_seen = set(FINALS)
            grade_in_background(f"results {datetime.now(timezone.utc):%H:%M}")
        elif FINALS - finals_seen:                                # a game just ended: grade it and post results now
            print(f"{datetime.now(timezone.utc):%H:%M:%S} games ended: grading", flush=True)
            finals_seen = set(FINALS)
            grade_in_background(f"results {datetime.now(timezone.utc):%H:%M}")
        time.sleep(every_s)
    if grading():                                                 # let a background grade finish before the job ends
        try:
            GRADER[0].wait(timeout=420)
        except Exception:                                         # noqa: BLE001
            pass
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
