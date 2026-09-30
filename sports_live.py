"""LIVE VALUE: watch every live game, find in-game bets where the engine's number beats the live line.

Every second (.github/workflows/sports-live.yml) - live lines move every second, so we stay on the ball:
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
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_comeback as sc
import sports_lingo
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
PAUSE_HOLD_S = 90             # the book pauses its line (drive in the red zone, review) or we can't confirm the price:
                              # the card holds, marked LINE PAUSED, up to 90s - then it comes down
LATE_REAL = 1 / 3             # the last third of a game: a trailing team's chance is pulled halfway to the real history
LIVE_MIN_P = 0.40             # ACCURACY FIRST: a new live bet is one we think has a real shot (40%+)...
LINE_MAX_AGE_S = 60           # a live price the book last touched 60+ seconds ago is no price (its feeds sit in a
                              # cache): no new play, no alert; one that's up shows "line paused", then comes down
MOVE_TOL = 0.03               # the price may lag the score a bit, never go the other way (against_the_score)
HEARTBEAT_S = 15              # live.json goes out at least this often (the page drops a play not re-checked in 45s)
WATCHDOG_S = 90               # one check stuck this long (a feed or git call hung): the watch restarts itself
LIVE_MAX_ODDS = 250           # ...and never longer than +250 when it goes up (the +270..+425 ones kept losing)
MAX_PLAYS = 2                 # NEVER more than 2 on the board at once (the owner, 9/28): one's value goes, the next can take its slot
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


# ---------------------------------------------------------------- the words (our lingo - sports_lingo rolls them)
# Every line is rolled from the play's own seed (its id), so a play reads the same every second it's up (the facts in
# it - the score, the price - update; the wording doesn't flicker), and different plays / days read differently.
# No 4-word run twice inside one play; cycle() keeps the plays on the board from sharing one either.
ICON = {"nfl": "🏈", "ncaaf": "🏈", "nba": "🏀", "ncaab": "🏀", "nhl": "🏒", "mlb": "⚾"}


def blurb(league, us, them, trail, margin_txt, rs, seed, used=None):
    """The short line: why we see the value - in our lingo, rolled by the play's seed."""
    kinds = {kk for kk, _ in rs}
    used = set() if used is None else used
    kw = dict(i=ICON[league], us=us, them=them, m=margin_txt)
    if trail and "ball" in kinds:
        return sports_lingo.say("lv:ball", seed, used, **kw)
    if trail and "better" in kinds:
        return sports_lingo.say("lv:better", seed, used, **kw)
    if trail and "momentum" in kinds:
        return sports_lingo.say("lv:momentum", seed, used, per=sc.PNAME[league], **kw)
    if trail:
        return sports_lingo.say("lv:trail_nhl" if league == "nhl" else "lv:trail", seed, used, **kw)
    if margin_txt != "0":
        return sports_lingo.say("lv:up", seed, used, **kw)
    return sports_lingo.say("lv:tied", seed, used, **kw)


UNIT = {"nfl": "points", "ncaaf": "points", "nba": "points", "ncaab": "points", "nhl": "goals", "mlb": "runs"}


def full_breakdown(league, us, them, rs, seed, rate_mine=None, used=None):
    """Tap-to-open: every reason we trust it, in our lingo, one line each (rolled by the play's seed)."""
    out = []
    used = set() if used is None else used
    say = lambda key, **kw: sports_lingo.say(key, f"{seed}|{key}", used, **kw)
    for kind, f in rs:
        if kind == "history":
            spot, d = sc.when(league, f["k"]), f["d"]
            who = ("favorites" if f["fav"] else "teams") if f["trail"] else ("favorites" if f["fav"] else "dogs")
            kw = dict(ng=f"{f['n']:,}", who=who, d=d, spot=spot, rate=f"{f['rate']:.0%}", be=f"{f['be']:.0%}")
            out.append(say("bd:hist_trail", **kw) if f["trail"] else say("bd:hist_up", us=us, **kw))
        elif kind == "better":
            out.append(say("bd:better", us=us, them=them))
        elif kind == "pre":
            out.append(say("bd:pre", us=us))
        elif kind == "half":
            out.append(say("bd:half", us=us))
        elif kind == "ball":
            out.append(say("bd:ball", us=us, them=them, txt=f["txt"]))
        elif kind == "momentum":
            out.append(say("bd:momentum", us=us, them=them, per=sc.PNAME[league], w=f["won"], l=f["lost"]))
    out.append(say("bd:bottom"))
    return [x for x in out if x]


# ---------------------------------------------------------------- one watch cycle
def fresh_url(url):
    """ESPN's servers hand out older copies (a tennis score flipped 1-3, 1-2, 1-3; Kalieva's stuck at 5-4 after the match
    ended - 9/29): a new address every second gets a fresh one."""
    return f"{url}{'&' if '?' in url else '?'}_={int(time.time())}"


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


AN_DOWN = {}                  # league -> when Action Network last failed (the watcher's on ESPN's game list meanwhile)


def fetch_live_any(league):
    """Which games are live: Action Network's list, or ESPN's scoreboard (in the same shape) the moment Action
    Network fails - the owner, 9/29: when one source goes down, the next one takes over."""
    n = len(sd.ERRORS)
    got = fetch_live(league)
    failed = any(str(x).startswith(f"live {league}:") for x in sd.ERRORS[n:])
    if got or not failed:
        AN_DOWN.pop(league, None)
        return got
    AN_DOWN[league] = time.time()
    try:
        path = sd.LEAGUES[league][0]
        extra = sd.LEAGUES[league][1] or ""
        day = datetime.now(PT)
        evs = []
        for d in (day - timedelta(days=1), day):
            url = ESPN_SB.format(path=path) + f"?dates={d:%Y%m%d}&limit=300{extra}"
            evs += (_get(fresh_url(url)) or {}).get("events") or []
        return [x for x in (espn_as_an(league, e) for e in {e.get("id"): e for e in evs}.values()) if x]
    except Exception as e:                                   # noqa: BLE001
        sd.ERRORS.append(f"espn live list {league}: {str(e)[:80]}")
        return []


def espn_as_an(league, ev):
    """One ESPN scoreboard event in Action Network's shape (what the watcher reads): status, teams, start, and a
    boxscore with the period, clock, score by period, inning half, and - football - who has the ball and where."""
    comp = (ev.get("competitions") or [{}])[0]
    st = comp.get("status") or ev.get("status") or {}
    ty = st.get("type") or {}
    side = {c.get("homeAway"): c for c in comp.get("competitors") or []}
    if "home" not in side or "away" not in side:
        return None
    team = lambda c: {"id": str((c.get("team") or {}).get("id")), "full_name": (c.get("team") or {}).get("displayName"),
                      "abbr": (c.get("team") or {}).get("abbreviation")}
    h, a = team(side["home"]), team(side["away"])
    state = ty.get("state")
    status = "inprogress" if state == "in" else "complete" if state == "post" or ty.get("completed") else "scheduled"
    lh = [float(x.get("value") or 0) for x in side["home"].get("linescores") or []]
    la = [float(x.get("value") or 0) for x in side["away"].get("linescores") or []]
    box = {"period": st.get("period"), "clock": st.get("displayClock"),
           "total_home_points": int(float(side["home"].get("score") or 0)),
           "total_away_points": int(float(side["away"].get("score") or 0)),
           "linescore": [{"home_points": x, "away_points": y} for x, y in zip(lh, la)], "latest_odds": {}}
    short = str(ty.get("shortDetail") or "")
    if league == "mlb":
        box["inning_half"] = "top" if short.lower().startswith(("top", "mid")) else "bottom"
    sit = comp.get("situation") or {}
    if league in ("nfl", "ncaaf") and sit.get("possession"):
        pos = str(sit["possession"])
        spot = re.match(r"([A-Z]+)\s+(\d+)", str(sit.get("possessionText") or ""))
        ours = h if pos == h["id"] else a
        ytg = None
        if spot:
            ytg = 100 - int(spot.group(2)) if spot.group(1) == ours.get("abbr") else int(spot.group(2))
        elif str(sit.get("possessionText") or "").strip().endswith(" 50"):
            ytg = 50
        box["situation"] = {"possession": pos, "yards_to_endzone": ytg, "display_short": sit.get("downDistanceText") or ""}
    win = next((c for c in (side["home"], side["away"]) if c.get("winner")), None)
    return {"id": f"espn:{ev.get('id')}", "status": status, "real_status": status, "start_time": ev.get("date"),
            "teams": [h, a], "home_team_id": h["id"], "away_team_id": a["id"], "boxscore": box, "src": "espn",
            "winning_team_id": team(win)["id"] if win else None}


def grade_from_games(log, games):
    """Live bets graded from our own stored finals too (not just Action Network's list), so a bet posted while the
    watcher ran on ESPN's list - or whose game dropped off a feed - still grades."""
    for pid, e in log["plays"].items():
        if e.get("result") is not None or e.get("league") == "tennis" or pid.count(":") < 2:
            continue
        gid, side = pid.rsplit(":", 1)
        g = (games or {}).get(gid)
        if not g or g.get("status") != "final":
            continue
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (KeyError, TypeError, ValueError):
            continue
        if hs != as_:
            e["result"] = "won" if (hs > as_) == (side == "home") else "lost"


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


def _team_words(league, us, them, trail, m, rs, pid):
    """words(n) -> (line, breakdown) for a play. n=0: its own wording (seeded by its id); 1, 2, 3: other ways to say
    the same thing, for when a play already on the board says it that way (cycle picks n once and keeps it)."""
    def words(n=0):
        seed, used = (pid if not n else f"{pid}|{n}"), set()
        return blurb(league, us, them, trail, m, rs, seed, used), full_breakdown(league, us, them, rs, seed, used=used)
    return words


def _runs(pl):
    """The 4-word runs in a play's words (its names and numbers don't count)."""
    return sports_lingo._grams(" ".join([pl.get("line") or ""] + list(pl.get("breakdown") or [])),
                               [x for x in (pl.get("team"), pl.get("opp")) if x])


def settle_words(plays, prev, log):
    """Pin each play's wording: a play that's up keeps the wording it went up with (its `words` number - only the
    facts in it move), and a new one takes the first wording that shares no 4-word run with the rest of the board."""
    taken = set()
    for pl in sorted(plays, key=lambda p: p["id"] not in prev):      # plays already up keep theirs first
        words = pl.pop("_words", None)
        if words is None:
            taken |= _runs(pl)
            continue
        n = (prev.get(pl["id"]) or {}).get("words")
        if n is None:
            n = (log.get("plays", {}).get(pl["id"]) or {}).get("words")
        if n is None:
            n = 0
            for i in range(4):
                ln, bd = words(i) if i else (pl["line"], pl["breakdown"])
                if not _runs({**pl, "line": ln, "breakdown": bd}) & taken:
                    n = i
                    break
        if n:
            pl["line"], pl["breakdown"] = words(n)
        pl["words"] = n
        taken |= _runs(pl)
    return plays


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
        pro = league in ("nfl", "nba", "mlb", "nhl")
        the_us, the_them = (f"the {us}", f"the {them}") if pro else (us, them)
        words = _team_words(league, the_us, the_them, my < their, f"{abs(my - their)}", rs, pid)
        out.append({
            "id": pid, "league": league, "emoji": sd.LEAGUES[league][3], "sport": sd.LEAGUES[league][2],
            "team": us, "opp": them, "odds": ml, "edge": round(edge, 4), "p": round(p, 3),
            "score": f"{g['away_name']} {as_} @ {g['home_name']} {hs}", "clock": _clock_txt(league, box),
            "ball": ball_txt or "", "reasons": [kk for kk, _ in rs],
            "line": words(0)[0], "breakdown": words(0)[1], "_words": words,
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
# 9/29: the book serves these feeds from a cache (10 minutes per address) - our +125 on Garcia came out of it (the real
# line: -150). An address nobody asked for yet comes back fresh (prices 0-1s old), and eventsLimit=N (N <= 50) makes a
# new address for each N. So every check reads a never-used-lately address (N x the order of the parameters: 600+ of
# them, more than 10 minutes' worth at one a second), and per match we keep the NEWEST version seen (lastModified).
import itertools as _it
_BOV_KEYS = []
for _n in range(30, 51):                                   # (at least 30: never cut off a busy league's live games)
    for _ps in (["liveOnly=true", "lang=en", f"eventsLimit={_n}"],
                ["liveOnly=true", "lang=en", f"eventsLimit={_n}", "marketFilterId=all"]):
        _BOV_KEYS += ["&".join(o) for o in _it.permutations(_ps)]
BOV_BASE = "https://www.bovada.lv/services/sports/event/v2/events/A/description/{path}?"
BOV_SPLIT = {"tennis": ("tennis/atp", "tennis/wta")}       # tennis: tour by tour (a few live matches each, never 50+)
BOV_EV = {}                   # (path, event id) -> (lastModified, its group without events, the event): the newest seen
BOV_TURN = {}                 # sub-path -> where its rotation is (one address a check each: 630 checks to come around)
BOV_BAD = set()               # addresses the book turned away (a 400/404): out of the rotation


def bovada_fresh(path):
    """Bovada's live events for `path`, each the newest version any address has shown us (see above).
    Same shape as the feed (groups with events), one event per group."""
    subs = BOV_SPLIT.get(path, (path,))
    urls = []
    for sub in subs:
        for _ in range(len(_BOV_KEYS)):
            BOV_TURN[sub] = (BOV_TURN.get(sub, -1) + 1) % len(_BOV_KEYS)
            if _BOV_KEYS[BOV_TURN[sub]] not in BOV_BAD:
                break
        urls.append(BOV_BASE.format(path=sub) + _BOV_KEYS[BOV_TURN[sub]])
    with ThreadPoolExecutor(len(urls)) as ex:
        got = list(ex.map(_safe_get, urls))
    if all(g is None for g in got) and not any(k[0] == path for k in BOV_EV):
        raise RuntimeError("no Bovada address answered")
    for data in got:
        remember_events(path, data)
    now_ms = time.time() * 1000
    for k in [k for k, v in BOV_EV.items() if now_ms - v[0] > 15 * 60 * 1000]:
        del BOV_EV[k]                                         # (over, or gone from the board)
    return [{**grp, "events": [ev]} for (pth, _), (_, grp, ev) in BOV_EV.items() if pth == path]


def remember_events(path, data):
    for grp in data if isinstance(data, list) else []:
        if not isinstance(grp, dict):
            continue
        meta = {k: v for k, v in grp.items() if k != "events"}
        for ev in grp.get("events") or []:
            mod = ev.get("lastModified") or 0
            k = (path, str(ev.get("id")))
            if k not in BOV_EV or mod > BOV_EV[k][0]:
                BOV_EV[k] = (mod, meta, ev)


def _safe_get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={**BOV_HDR, "Accept": "application/json, text/plain, */*",
                                                                         "Referer": "https://www.bovada.lv/sports"}), timeout=8) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (400, 404) and "?" in url:
            BOV_BAD.add(url.split("?", 1)[1])                 # that address shape isn't one the book takes
        return None
    except Exception:                                         # noqa: BLE001
        return None
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
    try:
        data = bovada_fresh(path)
    except Exception as e:                                   # noqa: BLE001
        sd.ERRORS.append(f"bovada live {league}: {str(e)[:100]}")
        BOOKS[league] = f"error {str(e)[:60]}"
        data = []
    now_ms = time.time() * 1000
    data = [{**g, "events": [e for e in g.get("events") or [] if e.get("live")
                             and now_ms - (e.get("lastModified") or 0) <= LINE_MAX_AGE_S * 1000]}   # fresh prices only
            for g in (data if isinstance(data, list) else []) if isinstance(g, dict)
            and path in str(((g.get("path") or [{}])[0] or {}).get("link", path))]     # only this league's group
    BOOKS[league] = f"{len(data or [])} groups, {sum(len(g.get('events') or []) for g in data or [])} fresh events"
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
                        out.append({"home": comps["home"], "away": comps["away"], "ml_home": h, "ml_away": a,
                                    "src": "bovada"})
    return with_backups(out, backup_team(league))


def backup_team(league):
    """BetRivers live moneylines for one league (sports_books) - [] if they fail (never breaks the watch)."""
    try:
        import sports_books
        return sports_books.team_backup(league)
    except Exception as e:                                   # noqa: BLE001
        sd.ERRORS.append(f"backup books {league}: {str(e)[:80]}")
        return []


def with_backups(first, backups, now_ms=None):
    """Bovada's fresh prices first; a backup book fills in any game Bovada has no fresh price for (blocked, cached,
    down, or not offering it) - only when the backup's own price is fresh too. book_line() takes the first match."""
    now_ms = now_ms if now_ms is not None else time.time() * 1000
    out = list(first)
    for x in backups:
        if now_ms - (x.get("mod") or 0) > LINE_MAX_AGE_S * 1000:
            continue                                         # a stale backup price is no price either
        if any(sd._same(x["home"], y["home"]) and sd._same(x["away"], y["away"]) for y in first):
            continue                                         # Bovada has this game: Bovada's price stands
        out.append(x)
    return out


ESPN_SB = "https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard"
_ELO = {}
SEEN = set()                  # plays that qualified last cycle: a play only shows once it qualifies twice in a row


def espn_scores(league):
    """{espn event id: (home score, away score)} for games going right now - a second source for the score."""
    try:
        d = _get(fresh_url(ESPN_SB.format(path=sd.LEAGUES[league][0]) + "?limit=300" + (sd.LEAGUES[league][1] or "")))
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
    days = {today, (now.astimezone(PT) - timedelta(days=1)).date().isoformat()}   # (a game still going past midnight)
    out = {}
    try:
        with open(os.path.join(sd.DATA, "picks.json")) as f:
            for pk in json.load(f):
                if pk.get("date") in days and pk.get("status") != "waiting":
                    for leg in pk.get("legs") or []:
                        if leg.get("market") != "total":     # (an over/under isn't a side)
                            out.setdefault(leg["game_id"], leg["side"])
    except (OSError, ValueError, KeyError):
        pass
    for mid, side in stl.our_picks().items():               # 🎾 our pregame tennis picks lock their match too
        out.setdefault(f"tennis:{mid}", str(side))
    for pid, e in log.get("plays", {}).items():
        if e.get("date") in days and e.get("result") != "void":
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
    title = f"{'BACK ON: ' if back else ''}🔥 LIVE PLUS MONEY: {pl['team']} {o}"
    return alert(title, body, "rotating_light")


def alert(title, body, tag="rotating_light"):
    """📲 One alert to everybody: the dashboard's own 🔔 alerts (straight to our Worker) + the ntfy channel. Never blocks."""
    raw = None
    req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=body.encode(), method="POST", headers={
        "Title": title.encode("latin-1", "ignore").decode("latin-1"), "Tags": tag, "Click": DASH_URL, "Priority": "high"})
    try:
        raw = urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:                                   # noqa: BLE001 - a push failing never stops the watch
        sd.ERRORS.append(f"notify: {str(e)[:60]}")
    return sd.web_push(raw, title, body)                     # 🔔 the dashboard's alerts - even if ntfy is down


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
    SCORES.clear()                # rebuilt every check (finals stay while the feed still lists them)
    judged = set()                # games priced and judged this check (the rest were paused / out of sync)
    WATCHING[0] = PRICED[0] = 0
    BOOKS.clear()
    with ThreadPoolExecutor(12) as ex:                          # everything in parallel: live lines move fast
        angs_by = dict(zip(sd.LEAGUES, ex.map(fetch_live_any, sd.LEAGUES)))
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
                _keep_score(games, lg, ang, box, status)
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
    plays = settle_words(board(plays, showing), prev or {}, log)   # the wording stays put while a play is up
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
        if "words" in pl:
            log["plays"][pl["id"]].setdefault("words", pl["words"])   # (back up later = the same wording)
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
    rows, seen = [], set()
    nxt = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y%m%d")
    for tour in stn.TOURS:
        for q in ("", f"?dates={nxt}"):                     # Asia's matches sit on the next day's scoreboard
            try:
                for r in stn.parse_espn(_get(fresh_url(stn.ESPN.format(tour=tour) + q)), tour):
                    if r["id"] not in seen:
                        seen.add(r["id"])
                        rows.append(r)
            except Exception as e:                           # noqa: BLE001
                sd.ERRORS.append(f"espn tennis {tour}: {str(e)[:80]}")
    lines, ok = [], False
    for _ in (1,):
        try:
            raw_ = bovada_fresh("tennis")
            lines = stn.parse_bovada(raw_, live=True)
            for g_ in raw_ if isinstance(raw_, list) else []:          # event id -> the home player (for its scores)
                for e_ in g_.get("events") or []:
                    for c_ in e_.get("competitors") or []:
                        if c_.get("home"):
                            BOV_HOME[str(e_.get("id"))] = c_.get("name") or ""
            ok = True
        except Exception as e:                               # noqa: BLE001
            sd.ERRORS.append(f"bovada live tennis: {str(e)[:80]}")
            TENNIS["books"] = f"error {str(e)[:60]}"
            continue
    now_ms = time.time() * 1000
    lines = [{**ln, "stale": True} if not ln.get("mod") or now_ms - ln["mod"] > LINE_MAX_AGE_S * 1000 else ln
             for ln in lines]                                 # a price the book hasn't touched in 60s: not a live price
    lines = tennis_with_backups(lines, backup_tennis(), now_ms)
    if ok:
        by = {}
        for x in lines:
            if not x.get("stale"):
                by[x.get("src", "bovada")] = by.get(x.get("src", "bovada"), 0) + 1
        TENNIS["books"] = f"{len(lines)} live lines, {sum(by.values())} fresh" + \
            (" (" + ", ".join(f"{k} {v}" for k, v in sorted(by.items())) + ")" if by else "")
    return [r for r in rows if stn._state(r) == "live"], rows, lines


def backup_tennis():
    try:
        import sports_books
        return sports_books.tennis_backup()
    except Exception as e:                                   # noqa: BLE001
        sd.ERRORS.append(f"backup books tennis: {str(e)[:80]}")
        return []


def tennis_with_backups(lines, backups, now_ms):
    """Bovada's tennis lines + BetRivers for any match Bovada has no fresh price on. Fresh prices sort
    first (match_line takes the first line that fits a match), so a stale Bovada line never beats a fresh backup."""
    fresh_bov = [ln for ln in lines if not ln.get("stale")]
    out = list(lines)
    for x in backups:
        if now_ms - (x.get("mod") or 0) > LINE_MAX_AGE_S * 1000:
            x = {**x, "stale": True}
        if any(stn._last(x["a"]) in (stn._last(y["a"]), stn._last(y["b"])) and
               stn._last(x["b"]) in (stn._last(y["a"]), stn._last(y["b"])) for y in fresh_bov):
            continue                                         # Bovada has a fresh price on it: Bovada's stands
        out.append(x)
    return sorted(out, key=lambda ln: bool(ln.get("stale")))


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


def tennis_words(pl, s, side, rs, used, hold, n=0):
    """(the short line, the breakdown) in our voice - he/she by tour, rolled by the play's id (n: another wording, see
    settle_words), no 4-word run twice inside the play. `used` (the board's phrases) only collects ours: picking by
    it would make a play's words flicker as other plays come and go - settle_words keeps the board apart instead."""
    wta = pl["tour"] == "wta"
    he, him, his = ("she", "her", "her") if wta else ("he", "him", "his")
    me = stn._say_name(pl["team"])
    o = f"+{pl['odds']}"
    sit = tennis_situation(s, side, he)
    kinds = dict(rs)
    pct, be = round(100 * pl["p"]), round(100 * kinds["state"]["be"]) if "state" in kinds else None
    seed, mine = (pl["id"] if not n else f"{pl['id']}|{n}"), set()
    say = lambda key, **kw: sports_lingo.say(key, f"{seed}|{key}", mine, **kw)
    if pl["double_down"]:
        line = say("tl:dd", me=me, he=he, him=him, o=o, sit=sit)
    elif _trailing(s, side):
        line = say("tl:trail", me=me, he=he, him=him, o=o, sit=sit)
    else:
        line = say("tl:level", me=me, he=he, him=him, o=o, sit=sit)
    bd = []
    if "ours" in kinds:
        bd.append(say("tl:ours", me=me, he=he, him=him))
    if "strong" in kinds:
        bd.append(say("tl:strong", me=me, sp=round(100 * kinds["strong"]["p"])))
    if "state" in kinds:
        serve = {True: " and it's on serve", False: "", None: ""}[kinds["state"]["on_serve"]]
        bd.append(say("tl:state", me=me, sit=sit, serve=serve, he=he, his=his, hp=round(100 * hold)))
        bd.append(say("tl:math", me=me, him=him, pct=pct, o=o, be=be))
    bd.append(say("tl:bottom"))
    if used is not None:
        used |= mine
    return line, [x for x in bd if x]


def against_the_score(pre_p1, live_p1, book_p1, tol=MOVE_TOL):
    """The live price moved AGAINST the score (9/29: Garcia -115 pregame, up a break, and our line said +125 - the
    book's feed was minutes old, the real price was -150). A player the score helped since the first ball can't be
    longer than before it, and the other way round. True = don't trust this price."""
    helped = live_p1 - pre_p1
    moved = book_p1 - pre_p1
    return (helped > tol and moved < -tol) or (helped < -tol and moved > tol)


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
    if against_the_score(pre_p1, p1, book1):
        return []                  # the score moved one way and the price the other: an old or wrong line, never value
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
        if ours and _trailing(s, side) and tour != "wta" and not up:
            continue                   # DOUBLE DOWN is women's tennis only (the crew's call): no chasing a men's pick that's down
        pl = {"id": pid, "league": "tennis", "tour": tour, "emoji": "🎾",
              "sport": "Women's Tennis" if tour == "wta" else "Men's Tennis", "team": me, "opp": them, "odds": ml,
              "edge": round(edge, 4), "p": round(p, 3), "score": stl.score_text(m, s), "clock": stl.clock_text(m, s),
              "ball": "", "an_id": None, "reasons": [k for k, _ in rs], "match": m["id"], "double_down": bool(ours and _trailing(s, side)),
              "tennis": {"sets": list(s["sets"]), "games": list(s["games"]), "done": [list(x) for x in s["done"]],
                         "pts": list(s["pts"]) if s["pts"] else None, "set_no": s["set_no"], "side": side}}
        hp = stl.hold_p(pa if side == 1 else pb)
        pl["line"], pl["breakdown"] = tennis_words(pl, s, side, rs, used, hp)
        pl["_words"] = lambda n, pl=pl, s=s, side=side, rs=rs, hp=hp: tennis_words(pl, s, side, rs, None, hp, n)
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
    live_pending = {e.get("match") for e in log["plays"].values() if e.get("league") == "tennis" and e.get("result") is None}
    grade_tennis(log, rows)                                  # (graded here first, so the page rebuild has the result)
    TENNIS.update(watching=len(live), priced=0, stale=0, suspended=0)
    for m in rows:                                           # sets + games next to our pending tennis picks
        try:
            state = stn._state(m)
            if m["id"] in live_pending and state in ("final", "retired", "void"):
                FINALS.add(f"tennis:{m['id']}")                 # a live bet's match is over: its review goes up now
            if m["id"] in ours and state in ("final", "retired", "void"):
                FINALS.add(f"tennis:{m['id']}")                 # one of our matches is over: grade it right now
            if state == "live" or (state != "pre" and m["id"] in ours):
                SCORES[f"tennis:{m['id']}"] = {**_tennis_score(m, ours.get(m["id"])), "tennis": True, "live": state == "live",
                                               "delayed": any(k in str(m.get("status", "")).upper() for k in ("DELAY", "SUSPEND", "RAIN"))}
                mine = ours.get(m["id"]) or next((int(x.rsplit(":", 1)[1]) for x in showing
                                                  if x.startswith(f"tennis:{m['id']}:")), None)
                if state == "live" and mine:                    # ours / a live play up: Bovada's faster score
                    ln_, _ = stn.match_line(m, lines, hours=12)
                    k_ = f"tennis:{m['id']}"
                    SCORES[k_] = faster_score(SCORES[k_], _bovada_score(m, ln_, mine))
                k_ = f"tennis:{m['id']}"
                SCORES[k_] = BEST.setdefault(k_, SCORES[k_]) if SCORES[k_].get("live") and \
                    _games(SCORES[k_]) < _games(BEST.get(k_, SCORES[k_])) else SCORES[k_]
                BEST[k_] = SCORES[k_]                        # a score never goes backwards (ESPN's servers disagree)
        except Exception:                                    # noqa: BLE001
            pass
    import sports_breakdown as sb
    used = sb.slang_in([x for p in taken for x in [p.get("line", "")] + list(p.get("breakdown") or [])])
    out = []
    now_s = time.time()
    for m in sorted(live, key=lambda r: r["id"]):
        stale = tennis_stale(m, now_s)
        ln, flip = stn.match_line(m, lines, hours=12)
        if ln is None or m["id"] not in pre:
            continue
        if ln.get("stale"):
            TENNIS["stale_line"] = TENNIS.get("stale_line", 0) + 1
            continue                                         # no confirmed price: nothing new; one that's up shows
                                                             # "line paused" and comes down after PAUSE_HOLD_S
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


SCORES = {}                   # {game id: live score + clock} for the dashboard's pending picks (every sport + tennis)


def _keep_score(games, lg, ang, box, status):
    """The score and time left of one game (live, or final) - shown next to our pending picks with the LIVE tag."""
    try:
        if not box.get("period"):
            return
        g = _match(games, lg, ang)
        if not g:
            return
        if status in ("scheduled", "created"):
            return                                            # not started yet - never "Final" (9/29: the Blackhawks
        #                                                       read "FINAL 0-0" ten minutes after puck drop: the odds feed
        #                                                       still said "scheduled", and that sat in DONE)
        if status in ("cancelled", "canceled", "postponed"):
            SCORES[g["id"]] = {"away": g["away_name"], "home": g["home_name"], "a": _score(box, "away"),
                               "h": _score(box, "home"), "clock": "Postponed", "live": False, "delayed": True}
            return
        final = status in ("complete", "closed", "final")
        SCORES[g["id"]] = {"away": g["away_name"], "home": g["home_name"], "a": _score(box, "away"),
                           "h": _score(box, "home"), "clock": "Final" if final else _clock_txt(lg, box), "live": not final}
    except Exception:                                         # noqa: BLE001 - a score never breaks the watch
        pass


BOV_HOME = {}                 # Bovada live tennis event id -> its home player
BOV_SCORE = {}                # event id -> (fetched at, score json)
BOV_SCORE_URL = "https://services.bovada.lv/services/sports/results/api/v1/scores/{eid}"
BOV_HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
           "Accept": "*/*", "Referer": "https://www.bovada.lv/", "Origin": "https://www.bovada.lv"}


def _bovada_score(m, ln, side):
    """🎾 Bovada's live score for one of our matches (games per set, who's serving - it posts each game within
    seconds; ESPN can lag a game or more). Same shape as _tennis_score, from OUR player's side. None if no luck."""
    eid = str((ln or {}).get("event") or "")
    if not eid:
        return None
    now_s = time.time()
    got = BOV_SCORE.get(eid)
    if not got or now_s - got[0] >= 3:                    # (at most every 3s a match - never hammer the book)
        try:
            with urllib.request.urlopen(urllib.request.Request(BOV_SCORE_URL.format(eid=eid), headers=BOV_HDR), timeout=5) as r:
                BOV_SCORE[eid] = got = (now_s, json.load(r))
        except Exception:                                 # noqa: BLE001
            BOV_SCORE[eid] = got = (now_s, (got or (0, None))[1])
    j = got[1]
    if not j:
        return None
    home = BOV_HOME.get(eid, "")
    same = lambda a, b: stn._last(a) == stn._last(b) or set(stn._norm(a)) == set(stn._norm(b))
    p1_home = bool(home) and same(home, m["p1_name"])
    if not p1_home and not (home and same(home, m["p2_name"])):
        return None                                       # can't tell who's who: leave it to ESPN
    hv = lambda d: (d.get("home", 0), d.get("visitor", 0)) if p1_home else (d.get("visitor", 0), d.get("home", 0))
    sets = [list(hv(x)) for x in j.get("previousPeriodsScore") or []]
    cur = j.get("currentPeriodScore")
    final = str((j.get("clock") or {}).get("period") or "").upper() == "FINAL"
    if cur and not final:
        sets.append(list(hv(cur)))
    elif cur and final and (not sets or list(hv(cur)) != sets[-1]):
        sets.append(list(hv(cur)))
    srv_ = ((j.get("sportDetails") or {}).get("tennis") or {}).get("server")
    srv = None if srv_ not in ("home", "visitor") else (0 if (srv_ == "home") == p1_home else 1)
    names = [stn._say_name(m["p1_name"]), stn._say_name(m["p2_name"])]
    done = len(j.get("previousPeriodsScore") or []) + (1 if final else 0)
    if side == 2:                                         # our player first
        names, sets = names[::-1], [x[::-1] for x in sets]
        srv = None if srv is None else 1 - srv
    return {"n": names, "sets": sets, "pts": None, "srv": srv, "done": done, "tennis": True, "live": not final,
            "src": "bovada"}


BEST = {}                     # match -> the furthest-along score seen (ESPN's servers hand out older copies)


def _games(sc):
    return sum(a + b for a, b in (sc or {}).get("sets") or [])


def faster_score(espn, bov):
    """ESPN's tennis score vs Bovada's: whichever is further along wins (Bovada usually posts each game first).
    ESPN's points only stay when both are on the same game - points from the last game would be wrong."""
    if not bov:
        return espn
    tot = lambda x: sum(a + b for a, b in x.get("sets") or [])
    if tot(bov) < tot(espn):
        return espn
    out = {**espn, **bov}
    out["pts"] = espn.get("pts") if tot(bov) == tot(espn) else None
    if out["pts"] is not None:
        out["srv"] = espn.get("srv", bov.get("srv"))
    return out


def _tennis_score(m, side=None):
    """A scoreboard like on TV, from OUR player's side when we're on the match: names, games per set, the current
    game's points, who's serving. {"n": [us, them], "sets": [[6, 4], [3, 2]], "pts": ["30", "15"], "srv": 0}"""
    s = stl.score_state(m)
    flip = side == 2
    sw = (lambda t: (t[1], t[0]) if t else t) if flip else (lambda t: t)
    names = [stn._say_name(m["p2_name"]), stn._say_name(m["p1_name"])] if flip else \
        [stn._say_name(m["p1_name"]), stn._say_name(m["p2_name"])]
    sets = [list(sw(x)) for x in s["done"]]
    g = sw(s["games"])
    if g and (g != (0, 0) or s.get("pts") or not sets):
        sets.append(list(g))
    pts = None
    if s.get("pts"):
        a, b = sw(s["pts"])
        name = {0: "0", 1: "15", 2: "30", 3: "40", 4: "AD"}
        pts = [str(a), str(b)] if s["games"] == (6, 6) else [name.get(a, str(a)), name.get(b, str(b))]
    srv = {1: 0, 2: 1}.get(s.get("server"))
    if flip and srv is not None:
        srv = 1 - srv
    return {"n": names, "sets": sets, "pts": pts, "srv": srv, "done": len(s["done"])}


def _score(box, side):
    for k in (f"total_{side}_points", f"{side}_score", f"{side}_points"):
        if box.get(k) is not None:
            return int(box[k])
    ls = box.get("linescore") or []
    return int(sum((p.get(f"{side}_points") or 0) for p in ls))


def _ord(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _clock_txt(league, box):
    """The game clock said plain, same way ESPN says it (the owner, 9/29: the time, the period, and whether it's an
    intermission or halftime): '6:12 - 2nd', '1st Intermission', 'Halftime', 'End of 3rd', 'OT', 'Top 5th'."""
    try:
        per = int(box.get("period") or 0)
    except (TypeError, ValueError):
        per = 0
    if league == "mlb":
        half = str(box.get("inning_half") or box.get("half") or "")
        side = "Top" if half.lower().startswith("t") else "Bot" if half.lower().startswith("b") else "Inning"
        return f"{side} {_ord(per)}" if per else side
    clk = str(box.get("clock") or "").strip()
    zero = clk in ("0:00", "00:00", "0.0", "0")                       # (an empty clock is no clock, not a break)
    if not per:
        return clk
    if league == "nhl":
        if per == 4:
            return f"{clk} - OT" if clk and not zero else "OT"
        if per > 4:                                                   # a shootout (no clock) or playoff 2OT, 3OT...
            return f"{clk} - {per - 3}OT" if clk and not zero else "SO"
        if zero:
            return f"{_ord(per)} Intermission" if per < 3 else "End of 3rd"
        return f"{clk} - {_ord(per)}" if clk else _ord(per)
    halves = league == "ncaab"
    last = 2 if halves else 4
    if per > last:
        return f"{clk} - OT" if clk and not zero else "OT"
    if zero:
        return "Halftime" if per == (1 if halves else 2) else f"End of {_ord(per)}{' Half' if halves else ''}"
    unit = " Half" if halves else ""
    return f"{clk} - {_ord(per)}{unit}" if clk else f"{_ord(per)}{unit}"


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


def _live_days():
    import sports_dashboard as sdb
    return sdb.live_days(datetime.now(PT))


def sources_status():
    """Each backup book's last read (for the hourly bug check): {"betrivers:mlb": "ok 3" | "down HTTP 403"}."""
    try:
        import sports_books
        now = time.time()
        out = {k: (f"ok {v.get('n', 0)}" if v.get("ok") else f"down {v.get('err', '')}")
               for k, v in sports_books.STATUS.items() if now - v.get("at", 0) < 600}
        out.update({f"actionnetwork:{lg}": "down - on ESPN's game list" for lg, t in AN_DOWN.items() if now - t < 600})
        return out
    except Exception:                                         # noqa: BLE001
        return {}


def today_bets(log):
    """Today's live bets (pending ones too) for the page's LIVE PLUS MONEY list - it adds any the built page
    doesn't have yet, so a bet shows the moment it's logged, not at the next page rebuild. Newest last."""
    import sports_dashboard as sdb
    days = sdb.live_days(datetime.now(PT))                   # (till the next board drops at 8 AM PT)
    out = []
    for pid, e in sorted(log.get("plays", {}).items(), key=lambda kv: kv[1].get("posted", "")):
        if e.get("date") not in days:
            continue
        lg = e.get("league", "")
        tennis = lg == "tennis"
        out.append({"pid": pid, "team": e.get("team", ""), "odds": e.get("odds"), "result": e.get("result"),
                    "start": e.get("posted", ""),
                    "icon": "🎾" if tennis else sd.LEAGUES.get(lg, ("", "", "", "🏟️"))[3],
                    "sport": ("Women's Tennis" if e.get("tour") == "wta" else "Men's Tennis") if tennis
                    else sd.LEAGUES.get(lg, ("", "", lg.upper()))[2], "dd": bool(e.get("double_down"))})
    return out


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
    grade_from_games(log, games)
    health = health_check()
    out = {"updated": int(time.time() * 1000), "plays": plays, "record": record(log),
           "live_games": WATCHING[0] + TENNIS["watching"], "tennis": dict(TENNIS), "scores": dict(SCORES),
           "done": {pid: e["result"] for pid, e in log["plays"].items()          # today's graded live bets: a page
                    if e.get("date") in _live_days() and e.get("result")},   # still showing one
                                                                                                      # pending refreshes
           "today": today_bets(log),
           "sources": sources_status(),
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


def _git(*args, timeout=60):
    """git, never hanging the watch (9/29: one stuck git call froze the live board on a dead +125 for minutes)."""
    import subprocess
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        sd.ERRORS.append(f"git {args[0]} timed out")
        return subprocess.CompletedProcess(["git", *args], 124, "", "timeout")


LIVE_BRANCH = "live-data"      # live.json goes out on its own branch (one tiny commit, force-pushed) the moment it
                               # changes; phones read it from there. The graded log still lives on main.


def sync_log():
    """Every live bet any watch logged: main's copy + the one shipped with the board (live-data), merged."""
    try:
        mine = json.load(open(LOG)) if os.path.exists(LOG) else {"plays": {}}
        merged = sd.merge_live_logs(mine, sd.live_log_from_branch())
        if merged != mine:
            with open(LOG, "w") as f:
                json.dump(merged, f, indent=1, sort_keys=True)
    except Exception as e:                                    # noqa: BLE001
        sd.ERRORS.append(f"log sync: {str(e)[:80]}")


def unstick():
    """A pull that stopped mid-rebase leaves git refusing every later commit and push - silently (9/29: an hour of live
    bets never reached main). Clear it."""
    g = os.path.join(".git")
    if os.path.isdir(os.path.join(g, "rebase-merge")) or os.path.isdir(os.path.join(g, "rebase-apply")):
        _git("rebase", "--abort")
        sd.ERRORS.append("cleared a stuck rebase")
    if os.path.exists(os.path.join(g, "MERGE_HEAD")):
        _git("merge", "--abort")


def pull():
    """Pull main safely: clear a stuck rebase first, and put back any live bet a conflicting pull dropped from the log."""
    unstick()
    r = _git("pull", "-q", "--rebase", "--autostash", "-X", "theirs")
    sync_log()
    return r


def push_live():
    """Force-push docs/sports/live.json as the only file of the live-data branch (seconds, no history pile-up)."""
    blob = _git("hash-object", "-w", LIVE_JSON).stdout.strip()
    entries = f"100644 blob {blob}\tlive.json\n"
    if os.path.exists(LOG):                                  # the live-bet log rides along: it never depends on main
        entries += f"100644 blob {_git('hash-object', '-w', LOG).stdout.strip()}\tlive_log.json\n"
    import subprocess
    tree = subprocess.run(["git", "mktree"], input=entries, capture_output=True, text=True,
                          timeout=30).stdout.strip()
    commit = _git("commit-tree", tree, "-m", f"live {datetime.now(timezone.utc):%H:%M:%S}").stdout.strip()
    for _ in range(3):
        if _git("push", "-q", "-f", "origin", f"{commit}:refs/heads/{LIVE_BRANCH}", timeout=20).returncode == 0:
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
        pull()   # grade the latest picks, never a stale copy
        tn = 0
        try:                                                 # 🎾 our tennis picks first (the page below shows them)
            import sports_tennis
            tn = sports_tennis.quick_grade()
        except Exception as e:                               # noqa: BLE001
            print(f"tennis quick grade failed: {e}", flush=True)
        graded, posted = sports.quick()                      # grades the board + rebuilds the page
    except Exception as e:                                   # noqa: BLE001 - never stop watching over this
        print(f"quick grade failed: {e}", flush=True)
        return
    paths = [LOG, TUNE, os.path.join(sd.DATA, "picks.json"), "docs/sports/index.html", "docs/sports/reads.json",
             os.path.join(sd.DATA, "games"), os.path.join(sd.DATA, "tennis", "picks.json")]
    _git("add", *[p for p in paths if os.path.exists(p)])
    if _git("diff", "--cached", "--quiet").returncode == 0:
        return
    _git("commit", "-qm", f"{msg}: {len(graded)} graded, {len(posted)} new, {tn} tennis")
    for _ in range(4):
        pull()
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
        pull()
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


def _scores_key():
    try:
        return json.dumps(json.load(open(LIVE_JSON)).get("scores"), sort_keys=True)
    except (OSError, ValueError):
        return None


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


def backstop():
    """Every ~10 min while watching: if the tennis slate is due and not up, start the engine (GitHub skips schedules)."""
    if not os.environ.get("GH_TOKEN"):
        return
    import subprocess
    try:
        r = subprocess.run(["bash", "tools/backstop.sh"], capture_output=True, text=True, timeout=90,
                           env={**os.environ, "SKIP_LIVE": "1"})
        if r.stdout.strip():
            print(f"{datetime.now(timezone.utc):%H:%M:%S} {r.stdout.strip()[:200]}", flush=True)
    except Exception as e:                                        # noqa: BLE001 - never stops the watch
        print(f"backstop skipped: {e}", flush=True)


def queue_next():
    """Queue the next watch right behind this one (GitHub's 30-minute schedule can skip runs - a skipped run once left
    the live board stale). Needs GH_TOKEN (the workflow passes its own token). True if queued."""
    if not os.environ.get("GH_TOKEN"):
        return False
    import subprocess
    try:
        r = subprocess.run(["gh", "workflow", "run", "sports-live.yml", "--ref", "main"], capture_output=True, text=True,
                           timeout=60)
    except subprocess.TimeoutExpired:
        return False
    print(f"{datetime.now(timezone.utc):%H:%M:%S} next watch queued: {r.returncode == 0} {r.stderr.strip()[:100]}", flush=True)
    return r.returncode == 0


REGRADE_S = 20 * 60   # after a game ends: re-grade every 2 min for this long (the results feed lags the live one)
STAY_MIN = 120     # a game within 2 hours keeps the watch up (idling) - it never shuts off right before kickoff again


BEAT = [0.0]      # when the watch last started a check (the watchdog reads it)


def watchdog(limit=None):
    """A check stuck past WATCHDOG_S (a feed or git call hung - 9/29 the board froze on a dead +125): exit, and the
    workflow starts a fresh watch right away. Never a frozen board with games on."""
    import threading

    def run():
        while True:
            time.sleep(5)
            if BEAT[0] and time.time() - BEAT[0] > (limit or WATCHDOG_S):
                print(f"{datetime.now(timezone.utc):%H:%M:%S} watchdog: a check hung {time.time() - BEAT[0]:.0f}s - restarting",
                      flush=True)
                os._exit(75)
    threading.Thread(target=run, daemon=True).start()


def loop(minutes, every_s=1):
    """Watch live games every `every_s` seconds for `minutes`. Phones see every change right away (live-data
    branch, plus a heartbeat every minute); the graded log goes to main when it changes. Rests when nothing's live."""
    end = time.time() + minutes * 60
    code = _code_hash()
    queued = False
    games, idle_since, started, last_board, last_log, last_push = None, None, False, None, _log_key(), 0.0
    last_pull, last_scores, last_grade, regrade_until = 0.0, None, 0.0, 0.0
    finals_seen = None
    print(f"{datetime.now(timezone.utc):%H:%M:%S} watch starting", flush=True)
    BEAT[0] = time.time() + 120                                 # (startup gets 2 extra minutes)
    watchdog()
    _git("fetch", "-q", "origin", LIVE_BRANCH)                  # pick up where the last watch left off: plays that
    board = _git("show", f"origin/{LIVE_BRANCH}:live.json")      # are up stay up (they don't have to re-qualify)
    sync_log()
    if board.returncode == 0 and board.stdout.strip():
        with open(LIVE_JSON, "w") as f:
            f.write(board.stdout)
    while time.time() < end:
        t0 = time.time()
        BEAT[0] = t0
        if games is None or t0 - last_pull > 600:                      # pull the latest games/model every ~10 min
            last_pull = t0
            print(f"{datetime.now(timezone.utc):%H:%M:%S} pulling", flush=True)
            if not grading():                                # (the grader has git busy - pull next time)
                pull()
            if _code_hash() != code and not grading():      # new live code landed: restart on it right now, so a fix
                left = max(1.0, (end - time.time()) / 60)   # never waits behind a watch running the old code
                print(f"{datetime.now(timezone.utc):%H:%M:%S} new code - restarting on it ({left:.0f} min left)", flush=True)
                os.execv(sys.executable, [sys.executable, "-u", "sports_live.py", "--loop", f"{left:.1f}"])
            print(f"{datetime.now(timezone.utc):%H:%M:%S} loading data", flush=True)
            games, _ = _data(reload=True)
            backstop()
        if any_live_soon(games, STAY_MIN) and not queued:       # the next watch lines up behind this one
            queued = queue_next()
        if not any_live_soon(games, STAY_MIN):
            idle_since = idle_since or time.time()
            if (not started or time.time() - idle_since > 5 * 60) and time.time() >= regrade_until:   # nothing on (and
                #                                              nothing left to grade): don't burn the clock
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
        scores = _scores_key()
        if board != last_board or (scores != last_scores and time.time() - last_push > 5) or time.time() - last_push > HEARTBEAT_S:
            print(f"{datetime.now(timezone.utc):%H:%M:%S} pushing the board", flush=True)
            if push_live():
                last_board, last_scores, last_push = board, scores, time.time()
        if _log_key() != last_log and not grading():            # (git one job at a time)
            publish(f"live log {datetime.now(timezone.utc):%H:%M}")
            last_log = _log_key()
        if finals_seen is None:                                   # a watch starts: grade whatever ended meanwhile
            if grade_in_background(f"results {datetime.now(timezone.utc):%H:%M}"):
                finals_seen, last_grade = set(FINALS), time.time()
        elif FINALS - finals_seen:                                # a game just ended: grade it and post results now
            print(f"{datetime.now(timezone.utc):%H:%M:%S} games ended: grading", flush=True)
            if grade_in_background(f"results {datetime.now(timezone.utc):%H:%M}"):   # (busy? it stays queued)
                finals_seen, last_grade, regrade_until = set(FINALS), time.time(), time.time() + REGRADE_S
        elif time.time() < regrade_until and time.time() - last_grade > 120 and not grading():
            # the results feed can lag the live feed by a few minutes: keep grading every 2 min for 20 min after a
            # game ends, so a pick never sits ungraded (the owner, 9/28: graded right away)
            if grade_in_background(f"results {datetime.now(timezone.utc):%H:%M}"):
                last_grade = time.time()
        time.sleep(max(0.2, every_s - (time.time() - t0)))    # as tight as the feeds allow: a fresh look every second
    BEAT[0] = 0.0                                                 # (the wind-down isn't a hung check)
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
