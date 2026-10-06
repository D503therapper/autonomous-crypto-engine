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
import copy
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_breakdown
import sports_data as sd
import sports_model as sm
import sports_players as sp
import sports_form
import sports_goalies
import sports_news
import sports_weather

DATA = sd.DATA
PT = ZoneInfo("America/Los_Angeles")
START_BANKROLL = 1000.0
STAKE = 100.0
HOLD_DAYS = set()                   # boards on hold (none): used 9/28 while the new lock/lean rules (tools/tier_study.py) shipped - never
                               # post under rules the study showed are weak (the owner, 9/28)
FORCE_LOCK = False             # the owner, 10/2 ("there doesn't always have to be a lock ... you make the call"): a Lock
#                                only when the engine's read really beats the price (the full Lock test or backup_lock);
#                                the forced backup (near_lock - its read under the price) lost 17% flat over 78 replay
#                                days. No Lock = the board says so; the Dog and the leans still go up.
BOARD_EARLY_MIN = 40          # a run that starts 7:40+ PT pulls everything, then waits and posts at 8:00 sharp
POST_FROM_HOUR_PT = 8          # a day's plays go up from 8am Pacific ON GAME DAY (the owner, 9/28, after the line study:
                               # closing lines pick more winners - NFL 68% vs 61% early - so the engine watches the lines
                               # and the news overnight and posts off the sharpest numbers; tennis posts at 8am too, since 9/29)...
DEADLINE_MIN = 180             # ...as soon as everything that matters is known; if it never is, at the latest
                               # 3 hours before the play's first game (then only from games that are settled).
                               # A posted play is final: it never changes.
MIN_LEAD_MIN = 20              # only games starting at least this long after the board goes up
MIN_KNOWN = 5                  # both teams need this many rated games
MAX_FAV = -150                 # never a huge favorite: no moneyline leg shorter than this
LOCK_MAX_FAV = -120            # lock of the day: a moneyline no shorter than -120
LOTD_MAX_ML = MAX_FAV            # the Lock of the Day: the engine's most confident pick on the whole board, same -150 cap
                               # as every other pick (the owner, 9/28: -150s hit more often than -135s, so it has to match)
PLUS_LOCK_MAX = 125            # a lock is never plus money past +125 (over that = VALUE)


LOTD_P = 0.60                  # a one-game day's lone pick is only called the Lock of the Day at 60%+ to win
DOG_MIN = 100                  # dog of the day: a plus-money underdog...
BIG_DOG = 200                  # ...a big dog (+200 and up) is never declined when it triggers: a real shot and major value:
BIG_DOG_MIN_P = 0.22           #    at least a 22% win chance on our numbers,
BIG_DOG_EXTRA_EDGE = 0.05      #    and value at least 5 points better than the best regular dog on the slate
MIN_EDGE = 0.01                # NEVER a filler: every leg, lock and dog must be real value on our numbers (1%+)...
                               # ...and have at least one reason; not enough of them on the slate = no play today
MAX_EXTRA_OUT = 1              # never back the more banged-up team: at most 1 more player out than the opponent
KINDS = [("lock", "Lock of the Day"), ("dog", "Dog of the Day"),     # posted in this order (then the unit plays
         ("solo", "One-Game Pick")]                                      # and the leans - post_board); one-game days: solo
# THE OWNER, 10/1: "post straight bets with our units - the viewer builds his own parlay." No more 2-/3-/4-leg parlays
# (the ladder went 1 for 8 - its legs shared, one loss sank them all; the same legs straight went 11-6). Every real
# value play goes up STRAIGHT with its units (kind "play", MAX_PLAYS a day), and leans for the viewers (kind "lean", no
# units, in the record as 🟡). The parlays already posted stay in the history. (the 8-leg retired 2026-09-28)
MAX_PLAYS = 10 ** 6            # unit plays a day besides the Lock and the Dog: NO CAP (the owner, 10/4: "if the engine
#                                finds more picks, however many is fine") - every one still has to beat its price, never a filler
BOARD_TARGET = 5               # the owner, 10/1: "we need five picks" - the unit plays first, then leans fill the board
MAX_LEANS = BOARD_TARGET       #   to 5 (no units, in the record), the engine's best side in the biggest games
LEAN_PICK_P = 0.50             # a viewer lean: the side the engine leans to (never one its own read is fighting)
LEAN_PER_SPORT = 2             #   - at most 2 leans from one sport ("not five hockey games")
NHL_FAV_BAND = (-150, -130)    # the owner, 10/1 (the Red Wings at -142, after the Astros / Flyers): a hockey favorite
NHL_FAV_EDGE = 0.03            #   -130..-150 needs the engine's own read 3%+ over the price to be the Lock or a lean
# 8-leg: moneylines and spreads, every day across all sports (no big favorite: a favorite shorter than -150 only gets
# in on the spread). Value legs first; on a slate short on value the likeliest legs fill it. Over/unders stay out
# until the engine has studied totals.


# ---------------------------------------------------------------- state files
def _load(name, default):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    with open(p) as f:
        data = json.load(f)
    if name == "picks.json":                                 # a parlay never carries the same game twice
        for pk in data:
            seen, legs = set(), []
            for leg in pk.get("legs") or []:
                if leg.get("game_id") not in seen:
                    seen.add(leg.get("game_id"))
                    legs.append(leg)
            pk["legs"] = legs
    return data


def _save(name, obj):
    p = os.path.join(DATA, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(p + ".tmp", p)


def american(dec):
    return round((dec - 1) * 100) if dec >= 2 else round(-100 / (dec - 1))


ANNOUNCE_PINGS = False     # the owner, 9/30: "the only notifications should be the live plus money. That's it."


def announce_pick(pk):
    """🔔 A pick added after the day's board is already up (a replacement, a late add): a push to everyone with the
    dashboard's alerts on (the owner, 9/29). The 8 AM board itself doesn't ping anybody."""
    try:
        name = dict(KINDS).get(pk["kind"], "Pick")
        legs = pk.get("legs") or []
        what = f"{leg_label(legs[0])} ({fmt_american(legs[0]['odds'])})" if len(legs) == 1 else \
            f"{len(legs)}-leg parlay ({fmt_american(pk['american'])})"
        title = f"🆕 NEW PICK: {what}"
        body = f"{name} just went up on the board. Tap in." if len(legs) == 1 else \
            f"{name}: " + ", ".join(leg_label(l) for l in legs)[:180]
        if ANNOUNCE_PINGS:
            sd.web_push(None, title, body)
        print(f"   announced: {title}" + ("" if ANNOUNCE_PINGS else " (no ping: only live plus money pings)"))
    except Exception as e:                                           # noqa: BLE001 - an alert never breaks the board
        print(f"   announce failed: {str(e)[:80]}")


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


def home_opener(games, g):
    """The home team's first regular-season home game of the season."""
    if (g.get("stype") or "") != "2":
        return False
    y, m = int(g["start"][:4]), int(g["start"][5:7])
    season0 = f"{y if m >= 7 else y - 1}-07-01"
    return not any(x.get("league") == g.get("league") and x.get("home") == g["home"] and x.get("stype") == "2"
                   and season0 <= x.get("start", "") < g["start"] for x in games.values())


def lost_last_in_series(games, g, side):
    """Playoffs: did this side lose the last game of this series (same two teams, the week before)?"""
    if (g.get("stype") or "") != "3":
        return False
    pair = {g["home"], g["away"]}
    prev = [x for x in games.values() if x.get("league") == g.get("league") and x.get("status") == "final"
            and {x.get("home"), x.get("away")} == pair and x.get("start", "") < g["start"]
            and x["start"][:10] >= (datetime.strptime(g["start"][:10], "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")]
    if not prev:
        return False
    last = max(prev, key=lambda x: x["start"])
    try:
        hs, as_ = float(last["home_score"]), float(last["away_score"])
    except (KeyError, ValueError):
        return False
    winner = last["home"] if hs > as_ else last["away"]
    return winner != g[side]


HURT_OUT, HURT_UNSURE = 2, 4   # unweighed absences that take the money off a side (until every position is weighed)
# 🚑 FOOTBALL: BANGED UP IS A WEIGHT, NOT A BLOCK (the owner, 10/3: "just because a QB or a star is out or a team is too
# banged up doesn't necessarily mean no units. It all just depends."). The 10/4 study (our box scores 2021-26, a
# 'regular' by sports_absences.regulars on the team's prior games, missing = not in the game's box): a football side
# with 2+ regulars missing does NOT lose against its price (NFL -0.4 pts on 2,035, college +0.1 on 4,900 - the market
# has it), and the engine's own read isn't fooled by the non-key bodies (NFL +2.6, college +0.5 - the QB / RB / WR
# effect is already sports_absences.penalty). The one thing left: the NFL side with 2+ MORE regulars missing than its
# opponent ran -2.5 pts vs the price (667, 4 of 6 seasons - a lead, under 2 SE). So in football, with box scores to say
# who plays, the 2+ out / 4+ questionable block is OFF; the depth gap is a small, capped weight on the OWN read
# (never one factor decides): NFL ½ a point of win chance per regular more missing than the opponent, capped at 3;
# college 0 (nothing there). The card still names who's out (injury_line). No box scores = the old block (can't tell
# who plays). Hockey / hoops / baseball keep the block until their own study.
DEPTH_PTS = {"nfl": 0.005, "ncaaf": 0.0}    # win chance off the own read per regular more missing than the opponent
DEPTH_CAP = 0.03                             # ...at most 3 points, like the study angles' caps (STUDY_CAP / FAV_CAP)


def depth_weighed(g, side):
    """Is this side's depth WEIGHED (football, box scores say who plays) rather than blocked (every other case)?"""
    if g["league"] not in DEPTH_PTS:
        return False
    import sports_absences
    return bool(sports_absences.regulars(None, g["league"], g[side], g.get("start") or "9"))


def depth_penalty(lg, n_me, n_opp):
    """Points of win chance off a football side's OWN read for being the more banged-up team (regulars out beyond the
    opponent's): DEPTH_PTS a head, capped at DEPTH_CAP; 0 in any other sport or when the opponent is just as thin."""
    if lg not in DEPTH_PTS:
        return 0.0
    return min(DEPTH_CAP, DEPTH_PTS[lg] * max(0, (n_me or 0) - (n_opp or 0)))


def hurt(g, side, injuries):
    """Players out / doubtful (2+) or questionable (4+) the engine doesn't weigh yet (10/2, the owner: "if the running
    backs are out and the wide receivers are out and they got a bunch of backups, that changes everything"): a side like
    that never carries units - a lean at most, and its card names who's out. Season-long absences are already in the
    team's results, so they don't count. FOOTBALL (10/4): with box scores to say who plays, this is no block at all -
    the depth gap is weighed (depth_penalty), the key players by sports_absences.penalty - so it returns []."""
    inj = (injuries or {}).get(g["league"])
    rows = sd._team_rows(inj, g[side], g[side + "_name"])
    if g["league"] != "nba":                                 # (key players are weighed already - hoops has no key
        rows = [r for r in rows if not sd._is_key(r, g["league"], g[side + "_name"])]   # position: the 10/3 sweep found
    #   _is_key read EVERY NBA player as key, so an NBA side with 3 out and 4 day-to-day never lost its units)
    import sports_absences
    reg = sports_absences.regulars(None, g["league"], g[side], g.get("start") or "9")
    if reg and g["league"] in DEPTH_PTS:                     # football, who plays known: weighed, never a block (10/4)
        return []
    if reg:                                                  # football / hoops: only players who actually play count
        rows = [r for r in rows if sports_absences.match(r[0], reg)]   # (10/3 - a college report lists walk-ons and
        #   redshirts); a regular ruled out long-term (injured reserve, out for the season) just PLAYED - a fresh hole
        gone = [r[0] for r in rows if any(x in r[2].lower() for x in sd.SHORT_TERM + sd.LONG_OUT)]
    else:
        gone = [r[0] for r in rows if any(x in r[2].lower() for x in sd.SHORT_TERM) and "season" not in r[2].lower()]
    unsure = [r[0] for r in rows if any(x in r[2].lower() for x in sd.UNSURE)]
    return gone + unsure if len(gone) >= HURT_OUT or len(unsure) >= HURT_UNSURE else []


def out_count(g, side, injuries):
    """How many players out / doubtful count against a side in the banged-up test (MAX_EXTRA_OUT): the same list hurt()
    reads - football only players who actually play (sports_absences.regulars), never a season-long absence (already in
    the team's results). (10/3 sweep: the raw count still read every walk-on and redshirt on a college availability
    report - 13 college sides on one Saturday lost their units as 'the more banged-up team' right after the regulars
    rule had cleared them.)"""
    inj = (injuries or {}).get(g["league"])
    rows = [r for r in sd.team_injuries(inj, g[side], g[side + "_name"]) if "season" not in r[2].lower()]
    import sports_absences
    reg = sports_absences.regulars(None, g["league"], g[side], g.get("start") or "9")
    if reg:                                                  # who plays is known: a regular who just PLAYED and is now
        rows = [r for r in sd._team_rows(inj, g[side], g[side + "_name"])   # on injured reserve is a fresh hole too
                if any(x in r[2].lower() for x in sd.SHORT_TERM + sd.LONG_OUT) and sports_absences.match(r[0], reg)]
    return len(rows)


def waiting_on(g, injuries, maybe=True):
    """What still isn't known for a game (empty when it's safe to post): a starting pitcher, a key player's status.
    maybe=False (a lean - no money on it; the owner, 10/2: "it's not a starting goalie ... it doesn't change the
    game"): only a VERIFIED starter's status holds it, never a player our box scores don't show starting."""
    out = []
    if g["league"] == "mlb":
        out += [f"{g[side + '_name']} starting pitcher" for side in ("away", "home") if not g.get("sp_" + side)]
    if injuries is not None and g["league"] in injuries and injuries[g["league"]] is None \
            and g["league"] in sd.INJ_LEAGUES:           # the injury report didn't load: we don't know who's playing,
        out.append("the injury report")                  # so the game waits (never a pick made blind)
    inj = (injuries or {}).get(g["league"])
    if injuries is not None and g["league"] in injuries and inj is not None:
        for side in ("away", "home"):                    # (10/2: never a pick made blind - a team the injury data
            if not sd.covered(inj, g["league"], g[side], g[side + "_name"]):   # doesn't cover is UNKNOWN)
                out.append(f"{g[side + '_name']} injury report (not in our data)")
    for side in ("away", "home"):
        out += [f"{n} ({pos}) questionable" if pos else f"{n} questionable"
                for n, pos, _ in sd.team_unsure(inj, g[side], g[side + "_name"], g["league"], maybe=maybe)[:2]]
    return out


import sports_absences  # noqa: E402
import sports_lines  # noqa: E402

LINES_ST = sports_lines.load()               # the puck line / run line study (how often teams really win by 2+)
import sports_totals  # noqa: E402
import sports_ats  # noqa: E402

import sports_dogs  # noqa: E402

DOGS_ST = sports_dogs.load()                 # the big underdog + favorite study (price check + dog spots/traps)
import sports_trends  # noqa: E402
import sports_selfcheck  # noqa: E402

TRENDS_ST = sports_trends.load()             # in-season trends (Thursday-night unders...): bet only if history proves them
SELF_ST = sports_selfcheck.load()            # the self-check on our own graded picks (extra edge where we keep missing)
ATS_ST = sports_ats.load()                   # the spread-vs-moneyline study (who covers when the two disagree)

TOTALS_ST = sports_totals.load()             # the over/under study: a sport only gets over/unders once it's PROVEN
OU_STRONG = 0.58                             # ...and then only a game with a strong read (58%+ over or under)
_TOT_STATE = {}

import sports_context  # noqa: E402
import sports_explorer  # noqa: E402
import sports_spots  # noqa: E402

CONTEXT_ST = sports_context.load()           # rivalries, travel, domes, stakes, refs: PROVEN factors move numbers
SPOTS_ST = sports_spots.load()               # situational spots (revenge, blowouts, road trips...): PROVEN ones only
EXPLORER_ST = sports_explorer.load()         # the explorer's forward-confirmed angles
_IDX = {}


def _index(games, kind):
    """The context / spots / explorer indexes for this games dict (built once, only when needed)."""
    key = (id(games), len(games), kind)
    if key not in _IDX:
        for k in [k for k in _IDX if k[2] == kind]:
            del _IDX[k]
        _IDX[key] = {"context": sports_context.Index, "spots": sports_spots.index,
                     "explorer": sports_explorer.index}[kind](games)
    return _IDX[key]


def study_shift(games, g, market, facts=None):
    """(logit shift, name) for the HOME side's win/cover chance (market 'ml'/'spread') or the OVER's (market 'total'):
    the single strongest PROVEN angle across the context study, the situational spots and the explorer. Angles
    overlap (a road trip is also travel miles), so they never add up - only the strongest one counts."""
    lg = g["league"]
    cands = []
    if facts:
        s, k = (sports_context.total_shift(CONTEXT_ST, lg, facts) if market == "total" else
                sports_context.home_shift(CONTEXT_ST, lg, facts, market, sm.market_p(g)))
        if k:
            cands.append((s, "context:" + k))
    sh = (((SPOTS_ST or {}).get(lg) or {}).get("shifts") or {}).get(market) or {}
    if sh:
        idx = _index(games, "spots")
        fh, fa = sports_spots.flags(idx, g, "home"), sports_spots.flags(idx, g, "away")
        cands += [(sh[s], "spot:" + s) for s in fh if s in sh] + [(-sh[s], "spot:" + s) for s in fa if s in sh]
    if any(e.get("league") == lg for e in (EXPLORER_ST.get("proven") or {}).values()):
        idx = _index(games, "explorer")
        if market == "total":
            atoms = sports_explorer.game_atoms_for(games, g, idx)
            cands += [(sports_explorer._best(EXPLORER_ST, lg, "over", atoms), "explorer:over"),
                      (-sports_explorer._best(EXPLORER_ST, lg, "under", atoms), "explorer:under")]
        else:
            cands += [(sports_explorer._best(EXPLORER_ST, lg, market, sports_explorer.atoms_for(games, g, "home", idx)),
                       "explorer:home"),
                      (-sports_explorer._best(EXPLORER_ST, lg, market, sports_explorer.atoms_for(games, g, "away", idx)),
                       "explorer:away")]
    s, name = sports_context.best([c for c in cands if c[0]])
    return (s, name) if name else (0.0, None)


def _shifted(p, s):
    return p if not s or p is None else sm.sigmoid(sm.logit(p) + s)


def _proven_reason(name, side_home_shift):
    """A pick reason for the proven angle that moved this side's number (only when it moved it UP)."""
    if not name or side_home_shift <= 0:
        return []
    src, key = name.split(":", 1)
    if src == "context":
        return [f"proven spot: {sports_context.LABELS.get(key.split('|')[0], key.split('|')[0])}"]
    if src == "spot":
        return [f"proven spot: {sports_spots.SPOTS.get(key, key)}"]
    return ["a proven angle the explorer confirmed"]


import sports_strength  # noqa: E402

PARLAY_LEG_MIN_P = 0.56        # a parlay only when EVERY leg is lock grade, 56%+ (the owner, 9/29: don't look like clowns;
                               # 9/30: 57% left a 3-lock slate at 56.1-56.5% with no parlays at all - "we want parlays").
                               # 3+ seasons replayed: 55% vs 57% legs hit parlays at the same rate for the same payout
                               # (2-leg 34%, +190); the engine's % holds up (it said 55-57%, those won 55%; 57-60%, 57%).
                               # Nights nothing clears it: the Lock (+ Dog), no filler.
SEASON_START = {}              # {league: first regular-season day this season} - early-season hockey (season_w)
FIRED = {}                     # {(league, team): date of a mid-season coaching change} - sports_coach_changes
FIRST_TIMER = set()            # {(league, team)}: a first-time head coach's first season (sports_coach_changes)
DOG_ST = {}                    # {(league, team): {won, rs, ss}} - the 10/1 dog studies (sports_form.dog_states)
COACH = {}                     # {(league, team): (coach's years, new with the team)} - sports_coaches.states
ATS = ({}, {})                 # (cover streaks, last meetings) - sports_form.ats_states
PDO = {}                       # {nhl team: PDO last 10} - puck luck (sports_form)
LAST_STARTS = {}               # {(league, team): [starts]} - the back-to-back check (sports_form)
TEAM_STATE = {}                # {(league, team): (last margin, streak)} - the overreaction angle (sports_form)
HOT_KEY = {}                   # {game id: 'home'/'away'} - that side's goalie (NHL) / stars (NBA) are much hotter
HOT_W = 0.03                   # (sports_form: the books over-rate a hot key player - NHL 5 of 5 seasons, NBA 3 of 4):
                               # a pick riding a hot goalie / hot stars goes toward the back of the Lock / parlay line
SERIES_LOST_W = 0.05           # 9/30: Wild Card Game 1 losers won Game 2 in 7 of 24; playoff favorites that just lost
                               # won 50% (-14%) - weighed in when parlay legs fill (the owner: "the Astros are the
                               # only one going opposite yesterday's result")
PARLAY_FILL_MIN_P = 0.52       # the owner, 9/30: a 2-, 3- and 4-leg every day - short of 56%+ legs, the surest plays
                               # 52%+ fill it (the 56% legs always go first)
NO_PUCK_RUN_LINES = True       # hockey + baseball: moneylines only on the board (football / basketball spreads stay)


def candidates(games, model, now=None, day=None, injuries=None):
    """Every bettable side on the day's (Pacific) slate: moneylines, plus spreads in NFL/NCAAF/NBA."""
    now = now or datetime.now(timezone.utc)
    day = day or now.astimezone(PT).date()
    elo = sm.ratings(games, model)
    out = []
    for g in games.values():
        if g["status"] != "pre" or g.get("ml_home", "") == "" or g["league"] not in sd.LEAGUES \
                or (g.get("stype") or "?") not in sd.REAL or g.get("tbd") == "1" or sd.exhibition(g):   # (no time set:
            continue                                                                # date is a placeholder - 10/1 audit)
        start = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        if start.astimezone(PT).date() != day or start < now + timedelta(minutes=MIN_LEAD_MIN):
            continue
        lg = g["league"]
        params = model["params"].get(lg) or sm.default_params(lg)
        f = elo[lg].features(g)
        if f["known"] < MIN_KNOWN:
            continue
        mkt = sm.market_p(g)
        mkt_open = sm.market_p(g, open_line=True)
        if lg in STALE_OPEN:                         # (10/1 audit) a football "open" is the summer look-ahead line, so
            mkt_open = fair_open(games, g)           # the drift runs from our own first fair price (after both
            #                                          teams' last games) - none yet = no drift, never a false one
        inj = (injuries or {}).get(lg)
        key_out = {side: sd.team_key_out(inj, g[side], g[side + "_name"], lg) for side in ("home", "away")}
        n_out = {side: out_count(g, side, injuries) for side in ("home", "away")}   # (who really plays - out_count)
        # a missing starting QB / goalie is news the ratings can't see. The line prices the backup (a solid
        # one barely moves it, a bad one moves it a lot), so on this game go by the market + where sharp money goes
        ph = sm.sigmoid(sm.logit(mkt) + params.get("move_w", 0) * sm.line_move(g)) \
            if key_out["home"] or key_out["away"] else sm.final_p(params, f, g)
        # the engine's own read without the line move: sharp money alone can never carry a pick
        ph_own = mkt if key_out["home"] or key_out["away"] else sm.final_p({**params, "move_w": 0.0}, f, g)
        # the big study's price check: in a sport where favorites/dogs really win more/less than their price says
        # (proven on games it never saw), every read is shifted by it
        ph, ph_own = sports_dogs.adjust(DOGS_ST, lg, ph), sports_dogs.adjust(DOGS_ST, lg, ph_own)
        # 🚑 a missing key player moves the engine's OWN read (the 10/2 absence studies - sports_absences: NFL QB -8 /
        # RB -3 / WR -3 / two+ -10, college QB -3 / two+ -5, NHL top scorer -6, NBA top scorer -9; MLB none)
        absent = {s_: sports_absences.penalty(games, g, s_, injuries, skip_qb=bool(key_out[s_])) if injuries else (0.0, [])
                  for s_ in ("home", "away")}
        if absent["home"][0] or absent["away"][0]:
            ph_own = min(0.99, max(0.01, ph_own - absent["home"][0] + absent["away"][0]))
        # 🚑 the more banged-up football side (regulars out beyond the opponent's): a small, capped weight on the OWN
        # read (10/4 - DEPTH_PTS), never a block; only when box scores say who plays (depth_weighed)
        weighed = {s_: depth_weighed(g, s_) for s_ in ("home", "away")}
        depth = {s_: depth_penalty(lg, n_out[s_], n_out["away" if s_ == "home" else "home"]) if weighed[s_] else 0.0
                 for s_ in ("home", "away")}
        if depth["home"] or depth["away"]:
            ph_own = min(0.99, max(0.01, ph_own - depth["home"] + depth["away"]))
        # the studies' PROVEN angles (context factors, situational spots, the explorer): the single strongest one
        try:
            cx = _index(games, "context").facts(g)
        except Exception as e:                        # noqa: BLE001 - context is extra: never block the board
            print(f"context facts failed: {e}")
            cx = {}
        s_ml, n_ml = study_shift(games, g, "ml", cx)
        ph, ph_own = _shifted(ph, s_ml), _shifted(ph_own, s_ml)
        waiting = waiting_on(g, injuries)
        hurt_ = {sd_: hurt(g, sd_, injuries) for sd_ in ("home", "away")}
        news = sports_news.load()
        drama = {side: sports_news.drama(news, lg, g[side]) for side in ("home", "away")}
        talk = {side: sports_news.talk(news, lg, g[side]) for side in ("home", "away")}
        try:                                          # 🥅 hockey: is each side's known (confirmed / likely) starter
            g_roles = sports_goalies.roles(sp.CACHE.get("nhl") or [], g, now) if lg == "nhl" else {}   # its #1?
        except Exception as e:                        # noqa: BLE001 - unknown = no weight, never a blocked board
            print(f"goalie roles failed: {str(e)[:60]}")
            g_roles = {}
        for side in ("home", "away"):
            other = "away" if side == "home" else "home"
            if n_out[side] - n_out[other] > MAX_EXTRA_OUT and not hurt_[side] and not weighed[side]:   # the more banged-up team: never
                hurt_[side] = [f"{n_out[side]} players out ({n_out[other]} for {g[other + '_name']})"]   # units (10/2:
                #                                    a lean still fills the board - its card names who's out)
            team, opp = (g["home_name"], g["away_name"]) if side == "home" else (g["away_name"], g["home_name"])
            base = {"game_id": g["id"], "league": lg, "side": side, "team": team, "opp": opp, "stype": g.get("stype") or "",
                    "team_id": g[side],
                    "home": side == "home", "start": g["start"], "reasons": _reasons(side, f, g, lg, params),
                    "waiting": waiting, "hurt": hurt_[side], "intl": str(g.get("intl")) == "1", "country": g.get("country", ""),
                    "lost_last": lost_last_in_series(games, g, side),
                    "opp_lost_last": lost_last_in_series(games, g, "away" if side == "home" else "home"),
                    "road_opener": side == "away" and home_opener(games, g),
                    "key_edge": (sm.KEY_EDGE[g["id"]] * (1 if side == "home" else -1)) if g["id"] in sm.KEY_EDGE else None,
                    "key_out_me": bool(key_out[side]),
                    "hot_key": HOT_KEY.get(g["id"]) == side,
                    "form_state": TEAM_STATE.get((lg, g[side])),     # (last margin, streak) - the overreaction angle
                    "pdo": PDO.get(g[side]) if lg == "nhl" else None,
                    "g_role_me": g_roles.get(side), "g_role_opp": g_roles.get(other),   # (sports_goalies.roles)
                    "coach": COACH.get((lg, str(g[side]))),
                    "fired_on": FIRED.get((lg, str(g[side]))),
                    "first_timer": (lg, str(g[side])) in FIRST_TIMER,
                    "ats_run": ATS[0].get((lg, g[side]), 0),
                    "revenge": lg in sports_form.REVENGE and ATS[1].get((lg, g[side], g[other]), 0) <= -sports_form.REVENGE[lg],
                    "rested_vs_b2b": lg in sports_form.B2B_LEAGUES and sports_form.played_yesterday(LAST_STARTS, lg, g[other], g["start"])
                    and not sports_form.played_yesterday(LAST_STARTS, lg, g[side], g["start"]),
                    "tired_vs_rested": lg in sports_form.B2B_LEAGUES and sports_form.played_yesterday(LAST_STARTS, lg, g[side], g["start"])
                    and not sports_form.played_yesterday(LAST_STARTS, lg, g[other], g["start"]),
                    "dog_ctx": _dog_ctx(lg, g[side], g[other]),
                    "dog_more": _dog_more(games, g, side, other, lg),
                    "our_drama": drama[side][:1], "their_drama": drama["away" if side == "home" else "home"][:1],
                    # display only (the breakdown + the self-check's report-only groups): context facts, pregame talk
                    "ctx": sports_context.display(cx, side), "ctx_tags": sports_context.tags(cx, side),
                    "talk_ours": [{"kind": e["kind"], "headline": e.get("headline", "")} for e in talk[side][:2]],
                    "talk_theirs": [{"kind": e["kind"], "headline": e.get("headline", "")} for e in talk[other][:2]]}
            if base["their_drama"]:
                base["reasons"] = base["reasons"] + [f"opponent drama: {base['their_drama'][0]['kind']}"]
            # how far the money has run AWAY from this side since the open (no-vig points; + = against it)
            if absent[side][1]:                           # (who's missing, for the card / the journal)
                base["absent"] = absent[side][1]
            if depth[side]:                               # (the depth weight that moved the read, for the journal)
                base["depth_pts"] = round(depth[side] * 100, 1)
            base["drift"] = round(((mkt_open - mkt) if side == "home" else (mkt - mkt_open)), 4) \
                if mkt is not None and mkt_open is not None else 0.0
            odds = int(g[f"ml_{side}"])
            p = ph if side == "home" else 1 - ph
            if not (key_out["home"] or key_out["away"]):  # honest: the engine's own read, corrected by its record in
                p = sports_strength.calibrate(lg, p)      # this sport (a starter-out game goes by the market as is)
                if mkt is not None:                       # 10/1: the correction only takes back what the engine said
                    m_side = mkt if side == "home" else 1 - mkt   # OVER the line - never below the line's own number
                    if p < m_side <= (ph if side == "home" else 1 - ph):   # (college football's -6 put every favorite
                        p = m_side                        # 6-8 points under the line: "overpriced" across the board)
            p_own = ph_own if side == "home" else 1 - ph_own
            vd = VALUE_DOG.get(lg)                        # 🐶 a proven value dog: our own read 10-15 pts over the price
            p_mk = mkt if side == "home" else 1 - mkt
            value_dog = bool(vd and mkt is not None and 100 <= odds <= VALUE_DOG_MAX and vd[0] <= p_own - p_mk < vd[1])
            if value_dog:
                p = max(p, p_mk + vd[2])                  # credited only the lift it really won (the smaller half)
            trap = odds > 0 and sports_dogs.verdict(DOGS_ST, lg, odds, side == "home") == "trap"
            out.append({**base, "market": "ml", "line": None, "odds": odds, "dec": sd.decimal(odds), "p": p, "trap": trap,
                        "p_market": mkt if side == "home" else 1 - mkt, "edge": p * sd.decimal(odds) - 1,
                        "edge_own": p_own * sd.decimal(odds) - 1,
                        "reasons": base["reasons"] + _proven_reason(n_ml, s_ml if side == "home" else -s_ml)
                        + (["proven value dog: our read 10+ pts over the price - these won more than the book said, "
                            "3+ seasons"] if value_dog else [])})
            if lg in ("nhl", "mlb") and NO_PUCK_RUN_LINES:
                pass                                      # the owner, 9/29: no puck lines, no run lines on our board
            elif lg in ("nhl", "mlb") and g.get("spread_home", "") != "" and LINES_ST:   # puck line / run line: the chance
                line = float(g["spread_home"]) * (1 if side == "home" else -1)          # of winning by 2+, from the study
                sodds = sm._int(g.get(f"spread_{side}_odds"))
                pc = sports_lines.cover(LINES_ST, lg, ph, side, line)
                if pc is not None and sodds:
                    out.append({**base, "market": "spread", "line": line, "odds": sodds, "dec": sd.decimal(sodds),
                                "p": pc, "p_market": 1 / sd.decimal(sodds), "edge": pc * sd.decimal(sodds) - 1})
            if side == "home" and (TOTALS_ST.get(lg) or {}).get("proven") and g.get("total", "") != "":   # over/unders:
                key_ = (id(games), lg)                                                    # only in proven sports
                if key_ not in _TOT_STATE:
                    _TOT_STATE[key_] = sports_totals.state(games, lg)
                po = sports_totals.p_over(TOTALS_ST[lg], _TOT_STATE[key_], g)
                s_t, n_t = study_shift(games, g, "total", cx) if po is not None else (0.0, None)
                po = _shifted(po, s_t)                      # the strongest proven over/under angle (if any)
                if po is not None and max(po, 1 - po) >= OU_STRONG:   # only a strong, lock-level read ever makes it
                    for ou, pp in (("over", po), ("under", 1 - po)):
                        oo = sm._int(g.get(f"{ou}_odds")) or -110
                        out.append({**base, "side": ou, "team": ou.capitalize(), "opp": f"{g['away_name']} @ {g['home_name']}",
                                    "market": "total", "line": float(g["total"]), "odds": oo, "dec": sd.decimal(oo), "p": pp,
                                    "p_market": 1 / sd.decimal(oo), "edge": pp * sd.decimal(oo) - 1,
                                    "reasons": ["the engine's scoring read"] + _proven_reason(n_t, s_t if ou == "over" else -s_t),
                                    "ctx": sports_context.display(cx, ou, "total"),
                                    "ctx_tags": sports_context.tags(cx, ou, "total")})
            if lg in sm.SPREAD_LEAGUES and g.get("spread_home", "") != "":
                line = float(g["spread_home"]) * (1 if side == "home" else -1)
                sodds = sm._int(g.get(f"spread_{side}_odds")) or -110
                pc = sm.cover_p(params, f, g, side)
                if key_out["home"] or key_out["away"]:    # a starting QB out: our ratings still think the starter plays,
                    ho = sm._int(g.get("spread_home_odds")) or -110   # the book already moved for the backup - so the
                    ao = sm._int(g.get("spread_away_odds")) or -110   # spread read is the book's own line + the proven
                    pc = sd.no_vig(ho, ao) if side == "home" else 1 - sd.no_vig(ho, ao)   # spread/moneyline study only
                if pc is not None and ATS_ST:                 # moneyline vs spread disagreement (proven sports only)
                    ph_c = pc if side == "home" else 1 - pc
                    ph_c = sports_ats.adjust(ATS_ST, lg, g, ph_c)
                    pc = ph_c if side == "home" else 1 - ph_c
                s_sp, n_sp = study_shift(games, g, "spread", cx) if pc is not None else (0.0, None)
                if pc is not None:                            # the strongest proven cover angle (if any)
                    pc = _shifted(pc, s_sp if side == "home" else -s_sp)
                    out.append({**base, "market": "spread", "line": line, "odds": sodds, "dec": sd.decimal(sodds),
                                "p": pc, "p_market": 1 / sd.decimal(sodds), "edge": pc * sd.decimal(sodds) - 1,
                                "reasons": base["reasons"] + _proven_reason(n_sp, s_sp if side == "home" else -s_sp)})
    mark_hockey_favorites(out)
    weigh_mlb_drought(out)
    weigh_west_coast_road_fav(games, out)
    weigh_hoops_inside(games, out, now)
    mark_doubleheader_game2(games, out)
    weigh_favorites(out)                              # every sport's favorite weighed by the dog across from it (10/2)
    for c in out:                                     # a PROVEN in-season trend backing this side: one more reason
        for market, side_, note, vd in sports_trends.lean(TRENDS_ST, c["league"], games.get(c["game_id"], {})):
            if vd in ("ride", "fade") and market == c["market"] and side_ == c["side"]:
                c["reasons"] = c["reasons"] + [f"trend: {note}"]
    return out


INTL_MIN_EDGE = 0.02           # overseas games are weird: they need twice the usual value


PLAY_MIN_P = 0.53              # THE LABEL STUDY (tools/tier_study.py, ~21k games the engine never saw, 9/28): the engine's
LOCK_P = 0.56                  # WIN % is honest (it hits what it says) but its disagreement with Vegas isn't (picks chosen
FIGHT_MAX = 0.03               # for "edge" hit 48% when it said 56%). So a play is picked by how likely it WINS:
                               #   53%+ = a real play (STRONG LEAN), 56%+ = a LOCK, the day's likeliest lock = Lock of the Day;
                               #   an underdog only as VALUE when a PROVEN angle backs it - never just the engine vs Vegas;
                               #   and never a side our own read says Vegas is overrating by 3+ points (fighting the line).


VALUE_DOG = {}                 # 🐶 proven value dogs: (lo, hi, lift) per league - a +100..+280 dog our OWN read has lo..hi
#                                points over the price. EMPTY on purpose (9/30 night): the engine retrained on seasons
#                                before 7/2024 and graded on the two since shows its dog edge exists only at the MORNING
#                                price (NFL own +8 dogs +20% there, -8% at game time; NHL +10% vs -12%) - the money follows
#                                its read and takes the value by game time. The board posts at 8 AM game day, at prices
#                                near the close, so no league qualifies there. (The earlier NHL / NCAAB 10-15 pt rule came
#                                from an engine tuned on all seasons - it flattered itself; the honest exam failed it.)
VALUE_DOG_MAX = 280            # (lo, hi, lift). Never longer than +280 (the owner: "+400 is crazy")


def proven(c):
    """A study-proven angle (it passed the out-of-sample proof bar) is behind this side."""
    return any(str(r).startswith(("proven", "trend:")) for r in c.get("reasons") or [])


DRIFT_MAX = 0.03               # the money has run 3+ no-vig points away from a side since the open: never the Lock,
                               # the Dog or a leg (9/29, the Astros: opened -143, the money ran to the White Sox all day,
                               # they lost. 10 seasons: a favorite the money runs from wins what the CLOSE says - 49-54%
                               # where the open said 56-64%, every league, old and new seasons). Our engine may go
                               # against the move only where the study proves it beats the pros (sports_sharps).


STALE_OPEN = ("nfl", "ncaaf")   # (10/1 bug hunt) a football "open" is the summer look-ahead line: 75-80% of NFL games
#                                 move 3+ points from it by kickoff - that's the season happening, not money running away


def fair_open(games, g):
    """Football's real open: the first price our line history holds after both teams' last games (sports_early.ready /
    first_fair), as the home side's no-vig chance - or None."""
    try:
        import sports_early as se
        ff = se.first_fair(g["id"], se.ready(se._schedule(games), g))
    except Exception:                                        # noqa: BLE001
        return None
    if not ff:
        return None
    ih, ia = (100 / (ff[0] + 100) if ff[0] > 0 else -ff[0] / (-ff[0] + 100)), \
        (100 / (ff[1] + 100) if ff[1] > 0 else -ff[1] / (-ff[1] + 100))
    return ih / (ih + ia)


def money_against(c):
    """The money's running away from this side - and our engine hasn't proven it knows better in this sport."""
    if c.get("drift", 0.0) < DRIFT_MAX or c.get("league") in STALE_OPEN:
        return False
    try:
        import sports_sharps
        return not sports_sharps.beats_the_move(c.get("league"))
    except Exception:                                    # noqa: BLE001 - no study yet: respect the move
        return True


def fighting(c):
    """Our own read (no line move) has this side 3+ points under what the price says: the engine is fighting Vegas.
    Or the money's running away from it (money_against): the pros already said no. Or the sport's proven weak for the
    engine (sports_strength: its picks below the price and losing, old and new games) - no Lock / Dog / leg there."""
    own = (c.get("edge_own", c["edge"]) + 1) / c["dec"]
    return own < 1 / c["dec"] - FIGHT_MAX or money_against(c) or sports_strength.weak(c.get("league"))


DOG_GATE = 8.0                 # the owner, 10/1 ("the engine should use everything we learned about dogs"): a football
#                                dog qualifies when its DOG SCORE - the engine's read over the price + every spot and
#                                fade (dog_spots / dog_more) - is 8+ points. Backtest (game-day prices, 2020-26): the
#                                spots added ROI at every level; NFL 8+ +10.0% on 212, last 3 + now +2.2% (2024 -24%,
#                                2025 +45%). College football didn't hold the last 3 seasons (-9.7%) - NFL only
DOG_SCORE_MAX_U = 2.0          # the owner, 10/1: "4 units on a +215 seems like a lot" - a dog picked by the dog score
#                                (dog_p) carries 2u at most until the score proves itself live
NHL_DOG_GATE = 6.0             # hockey (10/1 per-sport backtest, every dog +100..+220, 2018-26, the live read + every
#                                spot and fade): score 6+ won 48.7%, +12.8% on 542 (7 of 7 seasons up; 2023+ +18%,
#                                this season +11%) - the own read alone LOST; it's the weighed factors (a LEAD: the
#                                spots came from these seasons - graded live from here)
NCAAF_DOG_GATE = 4.0           # college football (the same 10/1 per-sport backtest, the live read + every spot and fade):
#                                4+ won 48.7%, +18.9% on 228 (7 of 8 seasons up, 2023+ +17%) - but this season's first
#                                9 went -46% and a narrower game-day test was -9.7% since 2023: a LEAD, graded live
#                                (the owner, 10/1: "only one way to prove it - you do it"; UConn +210)
NHL_BEST_DOG_MIN = 0.0         # ...and the best hockey dog of the day (score over 0): 2023+ +11.7%, this season +17%
NCAAB_DOG_EDGE = 0.04          # college hoops dogs the engine's own read likes over the price: +4% to +8% across the
#                                cutoffs, up every one of the last 3 seasons (the 10/1 confidence backtest)


def dog_gate(c):
    """A dog the engine's WEIGHED read says is underpriced (never one factor alone - the whole dog score)."""
    if c.get("market") != "ml" or not 100 <= c.get("odds", 0) <= DAILY_DOG_MAX or c.get("trap") or fighting(c):
        return False
    lg = c.get("league")
    if lg in ("nfl", "nhl", "ncaaf"):
        sc = round(dog_score(c), 2)
        if sc >= {"nfl": DOG_GATE, "nhl": NHL_DOG_GATE, "ncaaf": NCAAF_DOG_GATE}[lg]:
            c["dog_p"] = round(min(0.95, (c.get("p_market") or 1 / c["dec"]) + sc / 100), 4)   # (its units: the
            return True                                                                       # weighed read)
        return False
    if lg == "ncaab" and c.get("edge_own") is not None:
        own = (c["edge_own"] + 1) / c["dec"]
        if own - (c.get("p_market") or 1 / c["dec"]) >= NCAAB_DOG_EDGE:
            c["dog_p"] = round(own, 4)
            return True
    return False


def best_hockey_dog(cands, taken=()):
    """The owner, 10/1: "every day there's dogs that smack - the engine has to find the one with the most value." No
    real-value dog anywhere = the hockey dog the whole dog score likes best (over 0, +100..+220, never a trap, never one
    its own read fights), only when that weighed read still beats its price (backtest: the best one a day, 2023+ +11.7%,
    this season +17%)."""
    best = None
    for c in cands:
        if c.get("league") != "nhl" or c.get("market") != "ml" or not 100 <= c.get("odds", 0) <= DAILY_DOG_MAX \
                or c["game_id"] in taken or c.get("trap") or c.get("waiting") or fighting(c):
            continue
        sc = round(dog_score(c), 2)
        dp = min(0.95, (c.get("p_market") or 1 / c["dec"]) + sc / 100)
        if sc > NHL_BEST_DOG_MIN and dp * c["dec"] - 1 >= MIN_EDGE and (best is None or sc > best[0]):   # (10/3 sweep:
            #   the Jets +105 went up as the Dog, 1u, on a weighed read 0.04 points over the price - MIN_EDGE holds for
            #   the Dog like every other unit play: real value, 1%+)
            best = (sc, c, dp)
    if best:
        best[1]["dog_p"] = round(best[2], 4)
        return best[1]
    return None


def good(c):
    """A real play: likely to win by the engine's (honest) win %, a real reason behind it, and no red flags.
    Over/unders keep their own value rule (their study proves them separately). Anything else is filler."""
    if c.get("trap") or not c.get("reasons"):          # a dog the big study proved books overprice / no reason: never
        return False
    if c.get("market") == "total":
        need = MIN_EDGE + sports_selfcheck.extra_edge(SELF_ST, c)
        return c["edge"] >= need and c.get("edge_own", c["edge"]) >= need
    if fighting(c) or hockey_fav_bad(c):
        return False
    if c["odds"] >= 100:                               # an underdog: VALUE only when a proven angle says it's underpriced
        if c["odds"] > DOG_DAY_MAX:                    # (10/3 sweep: the owner's "no dog past +280" only lived on the
            return False                               #  Dog of the Day - a +400 with a proven trend was a ½u value play)
        return (proven(c) and c["edge"] >= MIN_EDGE) or dog_gate(c)   # ...or the whole dog score does (10/1)
    need = PLAY_MIN_P + (0.02 if c.get("intl") or c.get("our_drama") else 0.0)   # overseas / our own drama: a higher bar
    need += sports_selfcheck.extra_edge(SELF_ST, c)     # the self-check (every graded pick, leans too): where a kind of
    return c["p"] >= need                               # pick hits below what we said, it needs a higher win % to go up


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


def one_side(cands):
    """One side per game - never both teams. Value wins, unless the other side is a lock or a strong lean."""
    side, ou = {}, {}
    def rank(c):                     # value first - a popular favorite with no value never blocks the other side;
        g_ = good(c) and c["odds"] >= MAX_FAV   # (10/1 bug hunt: a -162 we can't post hid the +136 dog)
        #                              among real value plays: a lock / strong lean first; otherwise the bigger edge
        return (c["odds"] >= MAX_FAV, g_, g_ and leg_tier(c) == "lock", g_ and c["p"] >= STRONG_LEAN_P, c["edge"])
    for c in sorted(cands, key=rank, reverse=True):
        (ou if c.get("market") == "total" else side).setdefault(c["game_id"], c["side"])   # one side / one total each
    return [c for c in cands if c["side"] == (ou if c.get("market") == "total" else side).get(c["game_id"])]


DOG_IN_PARLAY_P = 0.50       # the Dog only rides in the parlays when the engine's confident in it: it thinks the
                             # underdog actually wins (50%+)


def _combo(legs, lean=False):
    dec, p = 1.0, 1.0
    for c in legs:
        dec *= c["dec"]
        p *= c["p"]
    return {"legs": list(legs), "dec": dec, "p_hit": p}


def make_board(cands, lock_game=None, allow_lean=False, avoid=(), core=None, fixed=None):
    """{kind: pick or None} - the owner's ladder (option A, accuracy first):
      Lock   = the engine's surest call
      2-leg  = the Lock + the next surest call
      3-leg  = the 2-leg + one more
      Dog    = its own pick, never in the parlays, on a game none of them use
      8-leg  = every call above + the next surest real plays to make 8 (locks and value only - every leg counts);
               not 8 real plays = no 8-leg that day.
    fixed: {kind: [legs]} already posted today (a pick posted earlier is built on, never rebuilt)."""
    cands = one_side(cands)
    fixed = fixed or {}
    slate_games = {c["game_id"] for c in cands}               # (10/2 audit: decided on the WHOLE slate - after `avoid`,
    if avoid:                                                # (10/1 bug check: a later Lock / Dog landed on a game
        cands = [c for c in cands if c["game_id"] not in avoid]   # that was already a unit play - double units)
    if len(slate_games) == 1 and len({c["game_id"] for c in cands}) == 1:   # a one-game day: one PICK OF THE DAY
    #                                                   the last unpicked game of a 3-game day read as a "one-game day")
        solo = max((c for c in cands if good(c) and c["odds"] >= MAX_FAV), key=lambda c: (round(c["p"] * 50), c["edge"]),
                   default=None)
        if solo is None:                                      # a one-game day (Monday/Thursday night) ALWAYS gets a pick:
            solo = max((c for c in cands if c["odds"] >= MAX_FAV and not c.get("trap") and not fighting(c)
                        and not (c["market"] == "spread" and c.get("edge_own") is None and abs(c["p"] - 0.5) < 0.005)),
                       key=lambda c: (c["p"], c["edge"]), default=None)   # the side likeliest to win (a lean)
        if fixed.get("lock") or fixed.get("dog") or fixed.get("solo"):   # already posted today: build on it
            return {"lock": fixed.get("lock") and _combo(fixed["lock"]), "dog": fixed.get("dog") and _combo(fixed["dog"]),
                    "two": None, "three": None, "four": None, "solo": fixed.get("solo") and _combo(fixed["solo"])}
        # the owner: that one pick is only the LOCK OF THE DAY when it's as strong as one - a real-value moneyline in the
        # lock range the engine gives 60%+. A plus-money real-value dog is the Dog of the Day. Anything else (a coin
        # flip) is just that game's pick: a LOCK or VALUE call by its price, never titled Lock/Dog of the Day.
        one = _combo([solo]) if solo else None
        kind = "solo"
        if solo and solo["market"] in ("ml", "spread") and good(solo) and lock_ok(solo) and \
                (solo["market"] != "ml" or solo["odds"] >= LOTD_MAX_ML) and own_agrees(solo) and real_value(solo):
            kind = "lock"
        elif solo and solo["market"] == "ml" and good(solo) and DOG_MIN <= solo["odds"] <= DAILY_DOG_MAX and \
                not solo.get("trap") and dog_score(solo) > 0 and beats_price(solo):   # (10/1 audit: a Dog that fails
            kind = "dog"                                     # the money check got 0u, was pulled, and left a Monday /
            #                                                  Thursday game with no pick - it stays the game's pick)
        return {"lock": None, "dog": None, "two": None, "three": None, "four": None, "solo": None, kind: one}
    # every leg is a real value play: the likeliest first (accuracy always comes first); when two are about as likely
    # (within 2%), the one with the most value
    good_ = sorted((c for c in cands if good(c) and c["odds"] >= MAX_FAV),        # accuracy first, then the most value
                   key=lambda c: (-round(c["p"] * 50), -c["edge"]))
    board = {}
    if fixed.get("lock"):
        lock = fixed["lock"][0]
    else:
        # the owner's rule: the Lock of the Day is the ONE pick the engine is most confident in, across the whole board -
        # every sport, moneyline or spread, favorite or dog - as long as a moneyline is no shorter than -135
        # ...and it has to be a LOCK: 52%+, no longer than +125 (the owner, 9/28: a +156 at 40% is no lock of anything)
        locks = [c for c in cands if good(c) and c["market"] in ("ml", "spread") and c["odds"] >= MAX_FAV
                 and (c["market"] != "ml" or c["odds"] >= LOTD_MAX_ML) and lock_ok(c)]
        # the owner, 9/30: "any moron could take the biggest favorite closest to -150." The Lock has to be a pick the
        # engine's OWN read (its ratings, not the line) says is worth its price; among those, the one whose win % holds
        # up best (p is already corrected by the engine's real record in that sport). 1,808 days, 2020-25, one Lock a
        # day, each season's engine trained on the 3 before it: 58.1% hit, +0.4% vs the old rule's 56.8%, -2.5%
        # (last 3 seasons 55.6% vs 54.7%). A day nothing agrees: the best lock-grade pick, as before.
        agree = [c for c in locks if own_agrees(c) and real_value(c) and not nhl_pricey(c)]   # (10/1 bug check: it
        #   fell back to a lock its own read disagreed with - the Flyers again)
        # 10/1, the owner (the Astros, then the Red Wings at -142): ranked by the highest WIN % the Lock was always the
        # priciest favorite allowed, right at -150. Now it's the most VALUE - the engine's own read over the price -
        # among the likely winners (lock_ok: 56%+), the win % (with the proven nudges) breaking ties. None = no Lock
        # today, and the board says so - never a fake one.
        lock = max(agree, key=lambda c: (round(rank_p(c), 3), lock_value(c))) if agree else None   # (the owner, 10/1:
        #   "the Lock should be the most confident win" - among the picks worth their price, the likeliest winner)
        if lock is None:
            lock = backup_lock(cands)
        if lock is None and FORCE_LOCK:
            lock = near_lock(cands)                          # (off since 10/2 - FORCE_LOCK)
    board["lock"] = _combo([lock]) if lock else None
    if fixed.get("dog"):
        dog = fixed["dog"][0]
    else:
        taken = {lock["game_id"]} if lock else set()
        taken |= {l["game_id"] for k in ("two", "three") for l in fixed.get(k) or []}
        # the owner, 10/1: "if it's the Dog of the Day we're confident in it - it's a UNIT play, like the Lock. We don't
        # force a dog: a forced one takes our ROI down." Only a REAL-value dog (good(): the price really beats it, a
        # proven reason behind it), the one the dog analysis (dog_score: the studies' spots and fades) likes best - and
        # never one the analysis flags as a trap (score under 0). None = no Dog of the Day, and the board says so.
        dogs = [c for c in cands if c["market"] == "ml" and good(c) and beats_price(c) and DOG_MIN <= c["odds"] <= DAILY_DOG_MAX
                and c["game_id"] not in taken and not c.get("trap") and dog_score(c) > 0]
        regular = [c for c in dogs if c["odds"] < BIG_DOG]
        dog = max(regular, key=lambda c: (dog_score(c), c["edge"])) if regular else None
        big = [c for c in dogs if c["odds"] >= BIG_DOG and c["p"] >= BIG_DOG_MIN_P
               and c["edge"] >= (dog["edge"] if dog else 0) + BIG_DOG_EXTRA_EDGE]
        if big:
            dog = max(big, key=lambda c: (dog_score(c), c["edge"]))
        if dog is None:
            dog = best_hockey_dog(cands, taken)
    board["dog"] = _combo([dog]) if dog else None

    def ladder(start, n):
        legs = [l for l in start if l["p"] >= PARLAY_FILL_MIN_P]     # every leg earns it (9/30: a posted 3-leg's 52%+
        #                                   leg can't be dropped - the 4-leg builds on the 3-leg as posted)
        for c in good_:
            if len(legs) >= n:
                break
            if c["p"] < PARLAY_LEG_MIN_P:
                continue
            if c["game_id"] not in {l["game_id"] for l in legs} and \
                    (not dog or c["game_id"] != dog["game_id"] or dog["p"] >= DOG_IN_PARLAY_P):
                legs.append(c)
        # the owner, 9/30: "we need a two leg, a three leg and a four leg" - every day. Short of 56%+ legs, the next
        # surest plays fill it (never past -150, never one the engine's own read is fighting, never a trap)
        fill = sorted((c for c in cands if c["market"] in ("ml", "spread") and c["odds"] >= MAX_FAV
                       and c["p"] >= PARLAY_FILL_MIN_P and not c.get("trap") and not c.get("waiting")
                       and not fighting(c) and (not dog or c["game_id"] != dog["game_id"])),
                      key=lambda c: (-(c["p"] - (SERIES_LOST_W if c.get("lost_last") and c["odds"] < 0 else 0)
                                       - (HOT_W if c.get("hot_key") else 0) + (HOT_W if overreact(c) else 0)
                                       + cover_run_w(c) + coach_w(c) + season_w(c)),
                                     -c["edge"]))                 # a playoff favorite that just lost the last game goes
        for c in fill:                                             # to the back (weighed, never banned - the owner)
            if len(legs) >= n:
                break
            if c["game_id"] not in {l["game_id"] for l in legs}:
                legs.append(c)
        return legs if len(legs) >= n else None
    two = fixed.get("two") or ladder([lock] if lock else [], 2)
    board["two"] = _combo(two) if two else None
    three = fixed.get("three") or ladder(two or ([lock] if lock else []), 3)
    board["three"] = _combo(three) if three else None
    if core is None:
        core = [c for k in ("lock", "two", "three", "dog") for c in ((board.get(k) or {}).get("legs") or [])]
    four = fixed.get("four") or ladder(three or [], 4) if three else None
    board["four"] = _combo(four) if four else None             # the 4-leg: the 3-leg + one more (never the Dog)
    board["solo"] = None
    return board


TIERS = ("lean", "value", "lock")
STRONG_LEAN_P = PLAY_MIN_P                    # 53%+ = STRONG LEAN, under that = SLIGHT LEAN (a lean on the board = 🟡)


DOG_DAY_MAX = 280            # the owner: no dog past +280
DAILY_DOG_MAX = 220          # ...and the every-day Dog (and the dog gate) +100..+220 (the owner, 10/1: "never no +400")


LAST_RAW = []


def dog_score(c):
    """How much the analysis likes a dog (points of win chance over its price, give or take what 9/30's studies found):
    the engine's own read vs the price, then - playoffs: facing a favorite that just lost the last game of the series
    (baseball 50% / -14%; NBA / NHL desperate favorites -15% / -19%), or we just lost it; hockey: the money ran away
    from the dog (lost every season since 2023, -6%) or came in on it (+6% / +15% 2 of 3); the books overprice a
    better goalie (the dog WITH the better goalie -9% to -12%, the dog facing it +2%)."""
    own = (c.get("edge_own", c["edge"]) + 1) / c["dec"]
    sc = (own - (c.get("p_market") or own)) * 100
    if sc > OWN_CAP:
        sc = 0.0 if c.get("league") in OWN_TRAP else OWN_CAP
    base = sc                                            # the engine's own read - everything below is the studies
    sc += dog_spots(c)
    if c.get("opp_lost_last"):
        sc += 3
    if c.get("lost_last"):                               # lost the last game of the series: baseball, Game 2 is the
        sc += 3 if c.get("league") in ("nba", "nhl") else -3   # pitcher (-); hoops / hockey bounce back as a dog
                                                         # (NBA +28.2%, NHL +28.7%)
    # (an NHL road dog in the other team's home opener was +1.5 - the 10/2 point-system study, walk-forward on 41,497
    #  dogs: -7.3 points vs its price inside own-read buckets, the wrong sign. Off.)
    d = c.get("drift") or 0.0                            # + = the money ran away from this side since the open:
    if c.get("league") in ("nhl", "nfl", "ncaaf", "nba") and d >= 0.02:   # those dogs lost - NFL -40%, college
        sc -= 4                                          # football -9%, NBA -8%, hockey -6% every season (baseball: even)
    pdo = c.get("pdo")                                   # hockey puck luck (last 10): the books over-rate a lucky
    if pdo is not None:                                  # team - an unlucky dog -0.9% vs a lucky one -10.3% (sports_form)
        sc += 2 if pdo <= sports_form.PDO_BAD else -3 if pdo >= sports_form.PDO_GOOD else 0
    if c.get("rested_vs_b2b"):                           # rested, and they played last night: NBA dogs +6.5%, NHL
        sc += 3                                          # +1.9% (4 of 5 seasons each) vs -6% for every dog
    if c.get("fired_on"):                                # the firing study: a dog that just fired its coach keeps
        import sports_coach_changes as scc               # losing in football / hoops (-10% to -30%); hockey teams
        lg_ = c.get("league")                            # beat their price after a change
        sc += -3 if lg_ in scc.FADE_AFTER and c.get("odds", 0) >= 100 else 2 if lg_ in scc.BUMP_AFTER else 0
    if c.get("first_timer") and c.get("odds", 0) >= sports_coach_changes_dog(c.get("league")):
        sc -= 4                                          # a first-time head coach's first year, a +200 dog: -40% / -72%
    k = c.get("coach")                                   # the coaching study: an NFL dog with a 10+ year head coach
    if k and c.get("league") in sports_coaches_vet() and (k[0] or 0) >= sports_coaches_vet()[c["league"]]:
        sc += 3
    if c.get("revenge") and c.get("market") == "ml":     # college football: a dog facing the team that blew it out
        sc += 3                                          # last meeting - +15.7% (6 of 7 seasons)
    if hangover(c):                                      # a dog again after its big upset win: the hangover
        sc -= 3
    if overreact(c):                                     # a football dog off a blowout loss: the market overreacts
        sc += 5 if c.get("league") == "nba" else 3       # (10/2 study: NBA +11 pts, 7 of 7 seasons, passes the
        #                                                   false-discovery check - +5)
        #                                           (college +11.6%, NFL +7.9% vs -3.6% for every dog)
    if c.get("hot_key"):                                 # its goalie / stars are much hotter: the books already
        sc -= 3                                          # over-rate that (NHL 5 of 5 seasons, NBA 3 of 4 - sports_form)
    if c.get("league") == "nhl":
        sc += 2 if d <= -0.02 else 0                     # hockey: the money came IN on the dog
        k = c.get("key_edge")
        if k is not None and not c.get("hot_key"):       # (10/2 study: 93% of hot_key dogs got this too - -5 stacked,
            #                                              the data says ~-2 in all: one or the other, never both)
            sc += -2 if k >= 0.4 else 1 if k <= -0.4 else 0
    return base + max(-STUDY_CAP, min(STUDY_CAP, sc - base))   # (the owner, 10/2: "I don't want the engine to
    #                                                             overweight these" - the angles overlap; their sum is capped)


STUDY_CAP = 6     # all the study angles on one dog together count at most ±6 points (6 points of win chance): a stack of
#                   overlapping spots (a rested bye-week dog off a blowout on Monday night...) never outweighs the read


_SCHED = {}


def _sched(games):
    """The schedule + each team's home time zone, built once per games dict (sports_early's helpers)."""
    if _SCHED.get("ref") is not games:                   # (10/1: keyed by id() alone, a new dict at a freed
        import sports_early                              # address read the old schedule - hold the dict itself)
        _SCHED.update(ref=games, k=id(games), s=sports_early._schedule(games), tz=sports_early._home_tz(games))
    return _SCHED["s"], _SCHED["tz"]


CFB_CONSERVATIVE_4TH = 1.3      # 4th-down tries a game - the bottom quarter of college teams (10/1 round 3)
CFB_FAST_PLAYS = 71.6           # plays a game - the top quarter
_STYLE = {}


def _cfb_style():
    """{team id: (4th-down tries / game, plays / game)} this college season (3+ games), from the box scores."""
    if "v" in _STYLE:
        return _STYLE["v"]
    out, acc = {}, {}
    now = datetime.now(timezone.utc)
    season = now.year if now.month >= 7 else now.year - 1
    try:
        with open(os.path.join(DATA, "teamstats", "ncaaf.jsonl")) as f:
            for x in f:
                try:
                    r = json.loads(x)
                except ValueError:
                    continue
                if (r.get("start") or "") < f"{season}-07-01":
                    continue
                for tid, st in (r.get("teams") or {}).items():
                    try:
                        fourth = float(str(st.get("fourthDownEff", "")).split("-")[1])
                        plays = float(str(st.get("completionAttempts", "")).split("/")[1]) + float(st.get("rushingAttempts"))
                    except (IndexError, ValueError, TypeError):
                        continue
                    a = acc.setdefault(tid, [0, 0.0, 0.0])
                    a[0] += 1
                    a[1] += fourth
                    a[2] += plays
    except OSError:
        pass
    for tid, (n, fo, pl) in acc.items():
        if n >= 3:
            out[tid] = (fo / n, pl / n)
    _STYLE["v"] = out
    return out


def _dog_more(games, g, side, other, lg):
    """The 10/1 dog findings the owner OK'd to WEIGH (never to pick off alone - "the engine weighs every factor"),
    each held at game-day prices and at the early number: football fades (ice cold, an NFL coach's first season, a
    college losing streak), an NFL East Coast team out West, a college team off a 17+ win, college
    coaching style (conservative 4th downs, fast pace), and the MLB playoff dog that just got blown out by this team."""
    if lg not in ("nfl", "ncaaf", "mlb", "nba"):
        return {}
    import sports_early as se
    try:
        sched, htz = _sched(games)
        start = se._t(g["start"])
        out = {}
        prev = se._prev(sched, lg, g[side], g["start"])
        margin = last_pts = None
        if prev and prev.get("status") == "final" and (start - se._t(prev["start"])).days <= 21:
            m = float(prev["home_score"]) - float(prev["away_score"])
            margin = m if prev["home"] == g[side] else -m
            try:
                last_pts = float(prev["home_score"] if prev["home"] == g[side] else prev["away_score"])
            except (TypeError, ValueError, KeyError):
                last_pts = None
        if lg in ("nfl", "ncaaf"):
            out["fades"] = se._fades(sched, g, side, lg, start.astimezone(ZoneInfo("America/New_York")))
            op_prev = se._prev(sched, lg, g[other], g["start"])  # (10/1 wiring audit: the early studies' game-day spots)
            if prev and op_prev and se.REST_BYE <= (start - se._t(prev["start"])).days <= 30 \
                    and (start - se._t(op_prev["start"])).days <= se.REST_NORMAL:
                out["bye"] = True                               # off a bye vs a team that played
            if lg == "nfl" and start.astimezone(ZoneInfo("America/New_York")).weekday() == 0:
                out["mnf"] = True                               # Monday night
            mine = [x for st_, x in sched.get((lg, g[side]), []) if st_ < g["start"] and x.get("status") == "final"]
            season0 = f"{int(g['start'][:4]) if int(g['start'][5:7]) >= 7 else int(g['start'][:4]) - 1}-07-01"
            res = []
            for x in mine:
                if x["start"] >= season0:
                    try:
                        m_ = float(x["home_score"]) - float(x["away_score"])
                    except (TypeError, ValueError):
                        continue
                    res.append((m_ if x["home"] == g[side] else -m_) > 0)
            if len(res) >= 4:
                out["win_pct"] = round(sum(res) / len(res), 3)    # this season's record (the .700+ dog)
            streak = 0
            for w in reversed(res):
                if not w:
                    break
                streak += 1
            out["win_streak"] = streak
            out["neutral"] = str(g.get("neutral")) == "1"
            if lg == "nfl":
                import sports_go4
                out["go4_gap"] = sports_go4.gap(g.get(side + "_name"), g.get(other + "_name"))   # 4th-down nerve
            if lg == "nfl" and "coach's first season" in out["fades"]:
                season = int(g["start"][:4]) if int(g["start"][5:7]) >= 7 else int(g["start"][:4]) - 1
                if se._first_season_coach(lg, g.get(other + "_name"), season):   # (10/1, the owner: Monken AND
                    out["fades"] = [f for f in out["fades"] if f != "coach's first season"]   # McCarthy are both new -
                    #                                     the same spot on both sides cancels, never just the dog's)
            out["last_margin"] = margin
            out["last_pts"] = last_pts if margin is not None else None
            if lg == "nfl" and side == "away" and str(g.get("neutral")) != "1":
                mine = htz.get((lg, g[side]))
                try:
                    gtz = float(g.get("tzo"))
                except (TypeError, ValueError):
                    gtz = None
                out["east_west"] = mine is not None and gtz is not None and mine >= -5 and gtz <= -7
            if lg == "ncaaf":
                stl = _cfb_style().get(str(g[side]))
                if stl:
                    out["conservative"] = stl[0] <= CFB_CONSERVATIVE_4TH
                    out["fast"] = stl[1] >= CFB_FAST_PLAYS
        elif lg == "nba":                               # the 10/2 momentum study (checked twice, from scratch): a team
            op_prev = se._prev(sched, lg, g[other], g["start"])   # off a COMEBACK win is overpriced next game
            fresh = lambda x: x and x.get("status") == "final" and (start - se._t(x["start"])).days <= 7   # noqa: E731
            out["comeback"] = bool(fresh(prev) and comeback_win(prev, g[side]))
            out["opp_comeback"] = bool(fresh(op_prev) and comeback_win(op_prev, g[other]))
        else:
            if str(g.get("stype")) == "3" and prev and margin is not None and margin <= -5 and \
                    g[other] in (prev.get("home"), prev.get("away")):
                out["series_blowout"] = True            # MLB playoffs: lost to THIS team by 5+ last game
            if prev and prev.get("status") == "final" and margin is not None and margin < 0 and \
                    (start - se._t(prev["start"])).days <= 3:
                out["late_rally"] = late_rally(prev, g[side])   # lost, but won the last 3 innings by 4+
        return out
    except Exception:                                   # noqa: BLE001 - extra facts never block the board
        return {}


def _ls(x, team):
    """(our line score, theirs) for a final as lists of numbers, or (None, None) when it's missing / broken."""
    try:
        h = [float(v) for v in str(x.get("ls_home") or "").split(",") if v.strip() != ""]
        a = [float(v) for v in str(x.get("ls_away") or "").split(",") if v.strip() != ""]
        if h and len(h) == len(a) - 1 and sum(h) > sum(a):   # (10/2 audit: the home team won without batting in
            h = h + [0.0]                                    #  the bottom of the last inning - ESPN lists one fewer)
        if not h or len(h) != len(a) or sum(h) != float(x["home_score"]) or sum(a) != float(x["away_score"]):
            return None, None
    except (TypeError, ValueError, KeyError):
        return None, None
    return (h, a) if x.get("home") == team else (a, h)


def comeback_win(x, team):
    """NBA: trailed going into the 4th, won by 3 or less (overtime counts) - the 10/2 momentum study: fading that team
    next game covered 58.3% (+11.2% ATS, +8.5% ML on 574, up 6 of 8 seasons, 2023-25 all up; it fades smoothly as the
    win gets less close and grows with the deficit - a LEAD: one sport, the NBA season not started)."""
    me, them = _ls(x, team)
    if not me or len(me) < 4:
        return False
    return sum(me[:3]) < sum(them[:3]) and 0 < sum(me) - sum(them) <= 3


def late_rally(x, team):
    """MLB: lost, but won the last 3 innings by 4+ - the 10/2 momentum study: next game as a +100..+220 dog +12.0% vs
    -4.7% for the same prices (411, z 2.6), 3+ / 4+ / 5+ runs all +14..16% (it held in baseball only - a LEAD)."""
    me, them = _ls(x, team)
    if not me or len(me) < 3 or sum(me) >= sum(them):
        return False
    return sum(me[-3:]) - sum(them[-3:]) >= 4


def _dog_ctx(lg, me, them):
    """The 10/1 dog studies' facts for one side: our / their last result, run share gap (MLB), shot share gap (NHL)."""
    a, b = DOG_ST.get((lg, me)) or {}, DOG_ST.get((lg, them)) or {}
    out = {"won": a.get("won"), "opp_won": b.get("won")}
    for k in ("rs", "ss", "luck"):
        if a.get(k) is not None and b.get(k) is not None:
            out[k + "_gap"] = round(a[k] - b[k], 4)
    out["cw5"], out["hits_top"] = a.get("cw5") or 0, bool(a.get("hits_top"))
    return out


def sharp_dog(c):
    """The pros-not-joes dog: the line moved to it 2+ no-vig points since the open while it has under half the tickets,
    and its share of the money is 10+ points over its share of the tickets (the real splits)."""
    if c.get("market") != "ml" or (c.get("drift") or 0.0) > -0.02 or not c.get("game_id"):
        return False
    try:
        import sports_breakdown
        sp_ = sports_breakdown.public_split(c)
    except Exception:                                        # noqa: BLE001
        return False
    if not sp_ or sp_[0] is None or sp_[1] is None:
        return False
    return sp_[0] < 50 and sp_[1] - sp_[0] >= 10


def dog_spots(c):
    """Points the 10/1 dog studies add to the Dog's score (every one vs all dogs at the same price, steady season to
    season and again on 2024-26). See sports_form.dog_states."""
    lg, odds, x = c.get("league"), c.get("odds", 0), c.get("dog_ctx") or {}
    sc = 0.0
    if lg == "nhl" and c.get("tired_vs_rested"):
        sc -= 3                    # NHL: the dog played last night, the favorite didn't - -17.4% vs -4.8%, worse 7 of 8
    won, opp_won = x.get("won"), x.get("opp_won")
    if lg in ("nfl", "ncaaf", "ncaab"):
        if opp_won is False:
            sc += 2                # the favorite lost its last: -1.0% vs -5.5% (7 of 9)
        elif won is False and opp_won is True and not overreact(c):
            sc -= 3                # we lost ours, they won theirs: -11.3% vs -6.2% (worse 7 of 8)
    elif lg == "nhl" and won is False and opp_won is False:
        sc += 3.5                  # (10/2 study: +4.3 pts, 6 of 7 seasons, passes the false-discovery check)
        #                     both lost their last: +1.6% vs -4.7% (7 of 8)
    elif lg == "nba" and won is True and opp_won is False:
        sc -= 2                    # we won, they lost: -10.0% vs -4.4% (worse 7 of 8)
    if (lg == "mlb" and 200 <= odds <= 249) or (lg == "nhl" and odds >= 200):
        sc -= 4 if lg == "mlb" else 2   # (10/2 study: MLB -5.3 pts, passes the false-discovery check - -4)
        #                     the price: MLB +200..+249 -14.9% (1 of 9 seasons up), NHL +200 and up -11..-14%
    if lg == "mlb" and (x.get("rs_gap") or 0) >= 0.02:
        sc += 1.5                  # out-scoring the favorite lately (small - 5 of 9 seasons at +130..+199)
    if lg == "nba" and (x.get("cw5") or 0) >= 2:
        sc -= 3                    # won 2+ close games lately: -20.0% vs -3.4% (worse 7 of 8) - over-rated
    elif lg == "ncaab" and (x.get("cw5") or 0) >= 2:
        sc -= 1                    # (college hoops: the same, weaker - worse 5 of 8)
    if lg == "nhl" and x.get("hits_top"):
        sc += 2                    # out-hitting people (top quarter, last 10): +2.2% vs -6.1% (5 of 5)
    if lg == "mlb" and (x.get("luck_gap") or 0) <= -0.10:
        sc += 1                    # much unluckier than the favorite this season: +2.7% vs -3.5% (6 of 9) - watch
    ss = x.get("ss_gap")
    if lg == "nhl" and ss is not None:
        sc += 3 if ss > 0 else -3 if ss <= -0.03 else 0   # out-shooting them: +1.0% vs -5.7% (5 of 5); out-shot -10.5%
    # 10/1, the owner: "wire in what you believe in - the engine WEIGHS it with everything else, never picks off it"
    # (each held at game-day prices AND the early number, dogs +100..+220, 2020-26):
    mo = c.get("dog_more") or {}
    if lg == "nfl" and mo.get("east_west"):
        sc += 3                    # an East Coast team as a road dog out West: +20% game day (5 of 6), +17% early
    if lg in ("ncaaf", "nfl") and (mo.get("last_margin") or 0) >= 17:
        sc += 2                    # a college dog off a 17+ win: +9% on 327 (all college dogs ~even), +9% early; an NFL
        #                            dog that blew someone out: +7.9%, the engine agreeing +13%, 5 of 6 (10/1 audit)
    if mo.get("bye"):
        sc += 3 if lg == "nfl" else 2   # off a bye vs a team that played: NFL +26.7% on 49 (5 of 6), college +7.5% on
        #                            242 (4 of 6) at fair prices - discounted: the line moves to them 60-65% by kickoff
    if mo.get("mnf"):
        sc += 1                    # a Monday night NFL dog: +21.4% on 119 overall, but only +3.3% on 80 inside the
        #                            +100..+220 band at the first fair price (10/1 daily study) - halved
    if lg == "mlb" and c.get("dh_game2"):
        sc += 1                    # the doubleheader game-2 dog: +9.5% on 327, 2026 +31% on 25 (10/1 - a watch lead)
    if lg == "nfl" and mo.get("last_pts") is not None and mo["last_pts"] <= 10:
        sc += 1                    # an NFL dog whose offense scored 10 or fewer last game: +7%, 2023+ +21% (a lead)
    if lg == "nhl" and c.get("opp_sv_slump"):
        sc -= 2                    # the dog facing a favorite whose goalie is slumping: -8.0 pts, 0 of 5 seasons (10/1)
    if lg == "nhl":
        sc += sports_goalies.role_points(c)   # 🥅 the dog's confirmed / likely starter is its #1 and the favorite's isn't:
        #                            +1.5% vs -4.0% for every dog, better 7 of 8 seasons, 2023-26 +10% (the 10/6 re-check
        #                            of the 10/1 'goalie roles' finding) +2; the reverse was noise - 0 (sports_goalies)
    if lg == "nhl" and sharp_dog(c):
        sc += 1                    # an NHL dog the line moved TO (2+ pts) against the tickets, with 10+ pts more of the
        #                            money than the tickets: +14.3% on 190, beat the close by 8 pts, 2 of 2 seasons (10/1
        #                            sharp-money study - a LEAD; every other "sharp" cut was dead across 24,301 games)
    if c.get("west_trip_dog"):
        sc -= 2                    # the Eastern home dog vs a West Coast favorite: -23.5% (10/1 study)
    if lg in ("nfl", "ncaaf") and c.get("key_out_me"):
        sc -= 3                    # a football dog playing without its key player (QB): QB-out-again dogs -54% on 57,
        #                            covered 33% (10/1 injury timing study); a QB-out-last-week dog -17.5% (early studies)
    # the believed-but-unproven early-round leads (the owner, 10/1: "the engine needs all the good things we found,
    # weighed against the numbers") - small weights, smaller samples:
    if lg == "ncaaf" and (mo.get("win_pct") or 0) >= 0.70:
        sc += 1.5                  # a .700+ college team as the dog: +11% (4 of 6)
    if lg in ("nfl", "ncaaf") and mo.get("neutral"):
        own = (c.get("edge_own", c.get("edge", 0)) + 1) / c["dec"] if c.get("dec") else None
        if own is not None and own > (c.get("p_market") or 1):
            sc += 1.5              # a neutral-site dog the engine likes: +15.7% on 106 (5 of 6)
    if lg == "nfl" and (mo.get("win_streak") or 0) >= 3:
        sc += 1                    # an NFL dog on a 3+ game win streak: +6.7% (4 of 6)
    if lg == "nfl" and mo.get("go4_gap") is not None:
        import sports_go4          # the NFL style study's one lead (sports_go4): a dog whose coach goes for it on 4th
        if mo["go4_gap"] <= sports_go4.GAP_LO:   # down clearly less than the other coach - covered 48.4%, 0 of 9
            sc -= 1                # seasons; the most aggressive quarter covered 53.9% (6 of 9). A weight, a lead.
        elif mo["go4_gap"] >= sports_go4.GAP_HI:
            sc += 1
    fd = mo.get("fades") or []
    if lg == "ncaaf" and "ice cold" in fd and "losing streak" in fd:
        sc += 2                    # (10/2 study: 61% overlap, -6 stacked - the pair counts -4 together)
    for f in fd:
        sc -= {"ice cold": 3,                # last 3 games 7+ worse than its season: NFL -15%, college -13% (1 of 6)
               "coach's first season": 3,    # an NFL dog in its coach's first season with the team: -16% (-26% last 3)
               "losing streak": 3,           # a college dog on a 3+ game losing streak: -15% (-21% early)
               }.get(f, 0)    # (Thursday night: no fade - the owner, 10/1; a small, noisy sample)
    if lg == "ncaaf" and (mo.get("conservative") or mo.get("fast")):
        sc -= 2                    # college coaching style: conservative 4th downs / fast pace dogs -11%, 0 of 5
    if lg == "mlb" and mo.get("series_blowout"):
        sc += 3                    # MLB playoffs: lost to THIS team by 5+ last game: +27.5% on 37 (6 of 8) - thin
    if lg == "nba" and mo.get("opp_comeback"):
        sc += 2                    # the favorite is off a comeback win (down after 3, won by 3 or less): fading it +11%
    if lg == "nba" and mo.get("comeback"):
        sc -= 2                    # ...and the dog off one is overpriced the same way (10/2 momentum study - a lead)
    if lg == "mlb" and mo.get("late_rally") and 100 <= odds <= 220:
        sc += 1.5                  # lost, but won the last 3 innings by 4+: +12% vs -4.7% (10/2 - a lead, baseball only)
    return sc


OWN_CAP = 12                       # 10/1 study 11 (walk-forward, 43k dogs): big own reads are traps - the score counts
OWN_TRAP = ("nfl", "nba")          # at most +12 points of it, and none at all past +12 in the NFL / NBA (2 of 8 seasons)


def sports_coaches_vet():
    """{league: years} for the vet-coach dog bump - OFF until it's re-tested on real coach history (sports_coaches)."""
    import sports_coaches
    return sports_coaches.VET_DOG


def sports_coach_changes_dog(league):
    """The price a first-time head coach's team has to be a dog at for the fade (sports_coach_changes)."""
    import sports_coach_changes
    return sports_coach_changes.FIRST_TIMER_DOG.get(league, 10 ** 6)


def overreact(c):
    """The market overreacts against this side (sports_form: a football dog off a blowout loss, a college hoops
    favorite on a long losing streak, a baseball favorite that hasn't scored in 12+ innings) - moneyline only."""
    import sports_form
    st = c.get("form_state")
    if not st or c.get("market") != "ml":
        return False
    return sports_form.overreaction(c.get("league"), None, c["odds"], {(c.get("league"), None): tuple(st)}) > 0


def hangover(c):
    """A dog again right after its big upset win - the market's too high on it (sports_form: NFL -30%, college -28%,
    MLB -14% vs about -3% for every dog)."""
    import sports_form
    st = c.get("form_state")
    if not st or c.get("market") != "ml":
        return False
    return sports_form.overreaction(c.get("league"), None, c["odds"], {(c.get("league"), None): tuple(st)}) < 0


def cover_run_w(c):
    """Spread picks: the public chases a cover streak (sports_form) - a team that failed to cover 4+ straight moves up
    the line (+HOT_W), one that covered 4+ straight moves back."""
    import sports_form
    if c.get("market") != "spread" or c.get("league") not in sports_form.ATS_LEAGUES:
        return 0.0
    k = c.get("ats_run") or 0
    return HOT_W if k <= -sports_form.ATS_RUN else -HOT_W if k >= sports_form.ATS_RUN else 0.0


EARLY_NHL_D = 14               # 9/30 (the owner: "we gotta tighten up hockey"): NHL favorites in the FIRST 2 WEEKS of a
                               # season won 55%, -4.3% (3 of 7 seasons up) - last year's ratings are stale; weeks 3-4: 65%,
                               # +11.7% (6 of 7). So early on, a hockey favorite moves back the Lock / parlay line.


def season_w(c):
    """Early-season hockey favorites move back the line (EARLY_NHL_D)."""
    st = SEASON_START.get(c.get("league"))
    if c.get("league") != "nhl" or not st or c.get("odds", 0) >= 0 or not c.get("start"):
        return 0.0
    try:
        days = (datetime.strptime(c["start"][:10], "%Y-%m-%d") - datetime.strptime(st, "%Y-%m-%d")).days
    except ValueError:
        return 0.0
    return -HOT_W if 0 <= days < EARLY_NHL_D else 0.0


def season_starts(games, now):
    """{league: first regular-season game day of the season going on now} - the first game after the offseason (the
    last 30+ day gap), never last season's games (9/30: a 200-day look-back picked last March)."""
    days = {}
    today = now.strftime("%Y-%m-%d")
    for g in games.values():
        if (g.get("stype") or "") == "2" and g.get("start") and g["start"][:10] <= today:
            days.setdefault(g.get("league"), set()).add(g["start"][:10])
    out = {}
    for lg, ds in days.items():
        ds = sorted(ds)
        start = ds[0]
        for a_, b_ in zip(ds, ds[1:]):
            if (datetime.strptime(b_, "%Y-%m-%d") - datetime.strptime(a_, "%Y-%m-%d")).days > 30:
                start = b_
        out[lg] = start
    return out


def coach_w(c):
    """The coaching study (sports_coaches): a NEW coach's team as a favorite (NBA / college hoops) moves back the Lock /
    parlay line - the market over-rates the new-coach bump."""
    import sports_coaches
    k = c.get("coach")
    if not k or c.get("league") not in sports_coaches.NEW_FAV or c.get("odds", 0) >= 0:
        return 0.0
    return -HOT_W if k[1] else 0.0


def own_agrees(c):
    """The engine's own read (its ratings - no line, no sharp money) says this side is worth at least its price."""
    if c.get("edge_own") is None or not c.get("dec") or c.get("p_market") is None:
        return False
    if c.get("w_p") is not None:
        return c["w_p"] >= c["p_market"]                     # (hockey: the weighed read)
    return (c["edge_own"] + 1) / c["dec"] >= c["p_market"]


def lock_ok(c):
    """A LOCK: a real play the engine gives 56%+ to win (the study: those hit ~56-60%), never plus money past +125."""
    return c["odds"] <= PLUS_LOCK_MAX and (c.get("p") or 0) >= LOCK_P


def leg_tier(c):
    """lock / value / lean for one leg (a lean shows STRONG at 53%+, SLIGHT under)."""
    if c.get("market") == "total":
        return "ou" if good(c) else "lean"                   # over/unders: no lock/value label - their own thing
    if not good(c):
        return "lean"
    if c["odds"] >= 100 and not lock_ok(c):
        return "value"                                       # a proven underdog
    read = c.get("edge_own") is not None and c.get("dec") and c.get("p_market") is not None
    if lock_ok(c) and read and not own_agrees(c):
        return "lean"                                        # 10/1, the owner: the Flyers said 🔒 LOCK (56% - the
        #                                                      price's own number) while the engine's own read was
        #                                                      against the price, and got blown out. The Lock rule
        #                                                      holds for the label too: no own read, no LOCK.
    return "lock" if lock_ok(c) else "lean"                  # 53-56% = a strong lean (a real play, counts)


LEANS_COUNT_FROM = "2026-09-29"   # the owner, 9/28: leans hit about like value - from this board on they count in OUR record


def in_record(p):
    """Does this pick count in our record? Everything we post - leans too, from 9/29 on (the owner, 10/1: "we put
    leans in our daily picks - leans have to go in our record"; they still carry no units, so never in the bankroll).
    Leans also keep their own record line."""
    return not p.get("lean") or (p.get("date") or "") >= LEANS_COUNT_FROM


def pick_tier(pk):
    """A play is only as sure as its weakest leg: all locks = LOCK; any value leg = VALUE; otherwise a LEAN."""
    if pk.get("kind") == "lock" and not pk.get("lean"):       # the Lock of the Day is a LOCK
        return "lock"
    if pk.get("lean"):
        return "lean"
    if pk.get("tier"):
        return pk["tier"]
    tiers = [l.get("tier") or leg_tier({**l, "edge_own": l.get("edge_own", l.get("edge", 0))}) for l in pk.get("legs") or []]
    if tiers == ["ou"]:
        return "ou"
    if tiers and all(t == "lock" for t in tiers):
        return "lock"
    return "value" if "value" in tiers else "lean"


# THE ENGINE SIZES EVERY PLAY (the owner, 9/30 - "however the engine makes the most money"; the sizing study, replayed
# on 2,034 Lock days and 2,385 Dog days it never saw): a quarter of the Kelly stake, 1u = 1% of the bankroll, ½u-10u.
#   Lock / a lock: by the engine's OWN read vs the price (+141u vs -2u flat, 5 of 7 seasons up)
#   Dog of the Day / a value play: by the engine's final read vs the price (+121u, +5.6%, 6 of 7 seasons up)
#   Early value plays: by the engine's own read vs the price we got (sports_early.units) - the real money-maker
#   Leans, parlays, live plus money, tennis: no units (no proof they make money - "just a lean")
UNIT_MAX = 10                  # 10u max play (1u = 1% of the bankroll, so the max play is 10% of it)
PARLAY_KINDS = ("two", "three", "four", "eight")   # the owner, 9/30: a parlay is for fun - no units on it; each PICK in it
                                                   # carries its own units, as a straight bet
BANKROLL_START = 1000.0        # the owner, 9/30: an open bankroll - it starts at $1,000; a unit is 1% of it (grows with it)
UNIT_PCT = 0.01


def _dec(odds):
    return 1 + (odds / 100 if odds > 0 else 100 / -odds)


def day_pending(picks, early, day):
    """Is anything with units still to be graded on this (PT) day? Our straight picks and parlay legs, and the early
    value plays playing that day - the day's recap only goes up once it's all in (the owner, 10/1)."""
    for p in picks:
        if p.get("date") != day or not in_record(p):
            continue
        for n, l in enumerate(p.get("legs") or []):
            res = l.get("result") or (p.get("status") if len(p["legs"]) == 1 else None)
            if res not in ("won", "lost", "push", "void", "canceled") and leg_units(p, l):
                return True
    for e in early or ():
        if e.get("result") is None and e.get("start"):
            when = datetime.strptime(e["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(PT)
            if when.strftime("%Y-%m-%d") == day:
                return True
    return False


def units_ledger(picks, early=()):
    """The open bankroll (the owner, 9/30: 'everything completely transparent'): every graded STRAIGHT pick in our
    record, once each, in the order it settled, at its units and real price. A parlay itself carries no units (the
    owner, 9/30: 'parlays are just for entertainment') - each pick in it counts as its own straight bet, and a pick
    that's both the Lock and a parlay leg counts once (as the Lock). Each day's unit = 1% of that morning's bankroll.
    -> {"bankroll", "unit_today", "by_date": {date: unit $}, "rows": [(pick, units, net_units, net_$)]}"""
    calls = {}
    for p in sorted((p for p in picks if in_record(p) and p.get("legs")),
                    key=lambda p: (p["date"], p.get("settled") or p.get("posted") or "")):
        parlay = p.get("kind") in PARLAY_KINDS
        for n, l in enumerate(p["legs"]):
            res = l.get("result") or (p.get("status") if len(p["legs"]) == 1 else None)
            if res not in ("won", "lost", "push"):
                continue
            key = (p["date"], l.get("game_id") or id(p), l.get("side") or n)
            if key in calls and (parlay or not calls[key][0]):
                continue                                     # a straight pick wins over the same pick in a parlay
            dec = _dec(l["odds"]) if l.get("odds") else p.get("dec") or 2.0
            if not leg_units(p, l):
                continue                                     # a lean: no units, not in the bankroll
            calls[key] = (parlay, {**p, "kind": "pick" if parlay else p.get("kind"), "units_tier": units_tier(p, l),
                                   **({"legs": [l], "american": l.get("odds")} if parlay else {})},   # (a parlay leg's row
                          leg_units(p, l), res, dec,                                  # is THAT pick: its team, its price)
                          p.get("settled") or p.get("posted") or "")
    import sports_early                                  # ⏰ early value plays: the price we got in at, sized by the engine's
    for e in early or ():                                # edge - its OWN bet: when the board takes the same side on game
        if e.get("result") not in ("won", "lost", "push") or not e.get("odds"):   # day, both count, each with its units
            continue                                     # (the owner, 10/4: "Jaguars can be both" - ½u early + 1u Dog;
        day = datetime.strptime(e["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(PT).strftime("%Y-%m-%d")
        calls[(day, e["game_id"], e["side"], "early")] = (False, {"date": day, "kind": "early", "units_tier": "early",   # the 10/4 audit: the
        #                                                  early row overwrote the Dog's and the unit record lost its 1u)
                                                         "legs": [{"team": e["team"], "odds": e["odds"]}]},   # (10/5 sweep: the
        #                                   brain's green-day line read the leg's price - an early play came out "(None)")
                                                 sports_early.units(e), e["result"], _dec(e["odds"]), e.get("graded_at") or "")
    rows_in = sorted(calls.values(), key=lambda c: (c[1]["date"], c[5]))
    bank, rows, by_date = BANKROLL_START, [], {}
    for day in sorted({c[1]["date"] for c in rows_in}):
        unit = round(bank * UNIT_PCT, 2)
        by_date[day] = unit
        for _, p, u, res, dec, _s in (c for c in rows_in if c[1]["date"] == day):
            net_u = u * (dec - 1) if res == "won" else -u if res == "lost" else 0.0
            rows.append((p, u, net_u, net_u * unit))
            bank += net_u * unit
    return {"bankroll": round(bank, 2), "unit_today": round(bank * UNIT_PCT, 2), "by_date": by_date, "rows": rows}


def kelly_units(p, odds, legacy=False):
    """A quarter of the Kelly stake in units (1u = 1% of the bankroll), rounded to ½u, ½u-10u (½u when the edge is thin).
    legacy: a pick posted before MONEY_CHECK_FROM keeps the rule it was posted under (no edge = ½u) - a posted, graded
    pick's units never change after the fact (10/1 audit: the 'no edge = 0u' change re-sized 9 graded rows)."""
    d = _dec(odds)
    k = ((p or 0) * d - 1) / (d - 1)
    if k <= 0 and not legacy:
        return 0.0                                                                   # no edge = no units (10/1)
    return min(UNIT_MAX, max(0.5, round(0.25 * k / 0.01 * 2) / 2))


def _sized(t, leg, legacy=False):
    """Units for one pick of tier t - the engine's call (see the sizing notes up top)."""
    if t == "lock":
        dec = leg.get("dec") or _dec(leg.get("odds") or -110)
        own = leg.get("w_p") or ((leg["edge_own"] + 1) / dec if leg.get("edge_own") is not None else leg.get("p"))   # edge_own is value per
        #                                         $1 (own x dec - 1), the same read own_agrees() uses - not a win % gap
        return kelly_units(own, leg.get("odds") or -110, legacy)
    if t == "value":
        u = kelly_units(leg.get("dog_p") or leg.get("p"), leg.get("odds") or 100, legacy)   # (a gated dog: the weighed read)
        if leg.get("dog_p") is not None:
            u = min(u, DOG_SCORE_MAX_U)                    # the dog score's points rank dogs - they aren't proven win
        return u                                           # % - so a score-picked dog is a lead-sized bet (10/1, UConn)
    return 0                                                 # a lean is just a lean: no units


def read_of(c):
    """The read a pick's units ride on: a gated dog's weighed read, a hockey favorite's weighed read, else the engine's
    own read (no line move), else its win %."""
    if c.get("dog_p") is not None and c.get("odds", 0) >= 100:
        return c["dog_p"]
    if c.get("w_p") is not None:
        return c["w_p"]
    if c.get("edge_own") is not None and c.get("dec"):
        return (c["edge_own"] + 1) / c["dec"]
    return c.get("p")


SOLO_UNITS_FROM = "2026-10-02"   # one-game days: the pick always carries units (the owner, 10/1) - from tomorrow on
MONEY_CHECK_FROM = "2026-10-01"   # picks posted from here on (a posted, graded pick's units never change after the fact)


def beats_price(c):
    """💰 THE MONEY CHECK (the owner, 10/1 - after the Steelers ½u at -148): a pick only carries units when its read
    beats the REAL price we pay (the juice in). Every unit pick - Lock, Dog, plays, leans - passes it or goes 0."""
    r, dec = read_of(c), c.get("dec") or (_dec(c["odds"]) if c.get("odds") else None)
    return r is not None and dec is not None and r * dec > 1   # (no price on it = nothing to check = no units)


def units_for(pk):
    """How many units a pick gets - the ENGINE decides, by its edge (the sizing study). A lean or a parlay: 0 (the
    picks in a parlay carry their own - leg_units)."""
    kind, legs = pk.get("kind"), pk.get("legs") or []
    if kind in PARLAY_KINDS or not legs:
        return 0
    if pk.get("units") is not None and pk.get("status") in ("won", "lost", "push", "void"):
        return pk["units"]                                   # graded: the units it was graded at, forever (10/1 audit)
    if kind == "solo" and (pk.get("date") or "") >= SOLO_UNITS_FROM:   # (the owner, 10/1: "on a one-game day we always
        t_ = pick_tier({**pk, "lean": False})                #  put units on" - a Lock or a value play, never a lean)
        u_ = _sized("lock" if t_ == "lock" else "value", legs[0]) or 0.5
        return 0.5 if (pk.get("date") or "") >= THIN_FROM and thin_edge(legs[0]) else u_   # (10/2 audit: a small edge
        #                                                                                   is a small bet here too)
    if pk.get("lean") and (pk.get("date") or "") >= THIN_FROM:
        return 0                                             # (the owner, 10/1 later: "the only thing that doesn't get
        #                                                      units is leans" - a lean we like is still just a lean)
    if pk.get("lean"):
        u = pk.get("lean_units") or 0                        # a lean: none - or ½u on a lean we like (the owner, 10/1)
        return u if u and ((pk.get("date") or "9999") < MONEY_CHECK_FROM or beats_price(legs[0])) else 0   # (the money check)
    t = "value" if kind == "dog" else pick_tier(pk)
    if kind == "lock" and legs[0].get("near_price"):        # the always-a-Lock backup (the owner, 10/1): ½u floor
        if (pk.get("date") or "") >= SIZING_FROM:            # (the unit system, 10/2: the backup Lock ½u - it lost -17%
            return 0.5                                       #  flat in the replay; the sizing check caught it at more)
        return _sized("lock", legs[0]) or 0.5
    u = _sized(t, legs[0], legacy=(pk.get("date") or "9999") < MONEY_CHECK_FROM)
    if (pk.get("date") or "") >= SIZING_FROM:              # 💰 THE UNIT SYSTEM (the 10/2 sizing replay - 712 board days,
        if kind == "dog":                                    # walk-forward): the Dog flat 1u (+8.9% flat, up 3 of 5),
            return DOG_UNITS                                 # every value play ½u (they lose at any size - sizing up on
        if kind == "play":                                   # edge lost more), the Lock by its own read (below). Since
            return PLAY_UNITS                                # 7/2023 +10.5u vs today's sizing -57u overall
    if (pk.get("date") or "") >= THIN_FROM:                 # (the owner, 10/1: "we do need units on value plays - the
        if not u or thin_edge(legs[0]):                      # only thing that doesn't get units is leans") - ½u
            return 0.5                                       # floor; a small edge is a small bet
        return u
    if u and (pk.get("date") or "9999") >= MONEY_CHECK_FROM and not beats_price(legs[0]):
        print(f"   money check: {legs[0].get('team')} {legs[0].get('odds')} - its read doesn't beat the real price, 0 units")
        return 0                                             # (the owner, 10/1: "build the money check")
    if u > 0.5 and (pk.get("date") or "") >= THIN_FROM and thin_edge(legs[0]):
        return 0.5                                           # a small edge is a small bet (the owner, 10/1: Western KY)
    return u


SIZING_FROM = "2026-10-02"     # the unit system below, from the 10/2 board on (posted picks keep their units)
DOG_UNITS = 1.0                # the Dog of the Day: flat 1u (the replay: sizing it by edge lost; flat +8.9%)
PLAY_UNITS = 0.5               # a value play: ½u (they lost at every size: -6.7% flat, -10.5% sized up)
THIN_FROM = "2026-10-02"         # the owner, 10/1 (Western KY +110 at 1u, its own read ~1 point over the price): "a small
THIN_EDGE = 0.03                 # value like that - probably should've been a half a unit." The engine's OWN read under 3%
#                                  over the price (per dollar) = ½u, whatever the sizing read says. Posted picks keep theirs.
#   THE EDGE STUDY (10/2, 11,941 bets, each season graded blind by a model trained on the 3 before it, closing prices):
#   the bare own read loses under 8% at every cut (<3% -3.3%, 3-8% -3.8%); dogs 8%+ +6.7% on 1,506 (8-12% up 7 of 8,
#   last 3 +5.3%, 3 of 3); FAVORITES 8%+ -4.3% (last 3 -9.7%, 0 of 3) - so a favorite never sizes up on its edge.
#   Sizing sim (units won): today's rule -125u / last 3 -139u / 2026 -4.5u; ½u under 8% -9u / -105u / +16.8u; plus
#   favorites ½u +73u / -59u / +6.2u. A lead (bare read, no dog gates). NOT built that far (the owner, 10/2: "we can't
#   be having half units all across the board" - 8% put ~80% of plays at ½u and every favorite Lock at ½u forever):
#   3% stays the line, the Lock sizes by its own read. Re-check on a full-board replay.


def thin_edge(leg):
    """The engine's own read beats the price by under THIN_EDGE per dollar (the smaller of its own read and the read
    the units ride on - a small edge is a small bet)."""
    dec = leg.get("dec") or _dec(leg.get("odds") or 100)
    eds = [leg["edge_own"]] if leg.get("edge_own") is not None else []
    r = read_of(leg)
    if r is not None:
        eds.append(r * dec - 1)
    return bool(eds) and min(eds) < THIN_EDGE


def units_tier(pk, leg):
    """lock / value / strong / slight for one pick - the bankroll's rows (the owner, 9/30: the Dog of the Day is a value
    play; leans split strong and slight)."""
    if pk.get("kind") in PARLAY_KINDS:
        t = leg.get("tier") or leg_tier({**leg, "edge_own": leg.get("edge_own", leg.get("edge", 0))})
    else:
        t = "value" if pk.get("kind") == "dog" else pick_tier(pk)
    if t in ("lock", "value"):
        return t
    return "strong" if (leg.get("p") or 0) >= STRONG_LEAN_P else "slight"


def leg_units(pk, leg):
    """Units on one pick: a straight pick's own, or a parlay leg sized as the straight bet it is (its own tier)."""
    if pk.get("kind") not in PARLAY_KINDS:
        return units_for(pk)
    if leg.get("units") is not None and leg.get("result") in ("won", "lost", "push", "void"):
        return leg["units"]                                  # graded: frozen (10/1 audit)
    t = leg.get("tier") or leg_tier({**leg, "edge_own": leg.get("edge_own", leg.get("edge", 0))})
    return _sized(t, leg, legacy=(pk.get("date") or "9999") < MONEY_CHECK_FROM)


LEAN_MIN_P = {"two": 0.58, "three": 0.58, "four": 0.58, "lock": 0.62, "dog": 0.42}   # a replacement lean (after a pick's graded): a sure side only
LEAN_DAY_MIN_P = 0.50          # the opening board on a leans-only day (nothing 53%+): the likeliest sides, still favored
MAX_REPLACEMENTS = 10         # 🟡 LEANS through the day: when a daily pick is graded, a fresh LEAN of the same kind goes
                              # up from the games that haven't started (keeps picks flowing till night). Leans keep their
                              # own record - never ours. Our record stays the start-of-day board.


PRO = ("nfl", "nba", "nhl", "mlb")


def importance(c):
    """How big a game is, for LEANS (the engine has no strong play, so the games people care about go first):
    playoffs (wild card on up) > NFL prime time (Thursday / Sunday / Monday night) > the pros > college."""
    if str(c.get("stype")) == "3":
        return 3
    if c["league"] == "nfl":
        et = datetime.strptime(c["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(ZoneInfo("America/New_York"))
        if et.weekday() in (0, 3) or (et.weekday() == 6 and et.hour * 60 + et.minute >= 19 * 60 + 30):
            return 2
    return 1 if c["league"] in PRO else 0


def rank_p(c):
    """The win % every straight pick is ranked by - the engine's honest %, with the proven nudges: a hot key player
    (over-rated), an overreaction (under-rated), cover runs, coaches, the season phase, and a playoff FAVORITE that just
    lost the last game of the series (10/1 bug check: the Astros Lock - SERIES_LOST_W only lived in the old parlay
    ladder, so the Lock and the unit plays never saw it)."""
    return (c["p"] - (HOT_W if c.get("hot_key") else 0) + (HOT_W if overreact(c) and not c.get("drought_w") else 0)
            + cover_run_w(c) + coach_w(c) + season_w(c)        # (10/1 audit: the MLB drought was in p AND here - twice)
            - (SERIES_LOST_W if c.get("lost_last") and c.get("odds", 0) < 0 else 0))


def real_value(c):
    """A UNIT play has to beat its real price by the engine's OWN read (10/1 bug check: a -150 the engine's own read
    gives 58.5% went up with ½u - the bet loses money by the engine's own numbers)."""
    if c.get("dog_p") is not None and c.get("odds", 0) >= 100:
        return c["dog_p"] * c["dec"] > 1                     # (a gated dog: everything weighed beats its real price)
    if c.get("w_p") is not None:
        return c["w_p"] * c["dec"] > 1                       # (a hockey favorite facing a bad dog: the weighed read)
    return (c.get("edge_own") if c.get("edge_own") is not None else c.get("edge", -1)) > 0   # (units are sized by
    #                                                          the engine's own read - it has to beat the real price)


LOCK_BACKUP_OWN = 0.56
NEAR_LOCK_GAP = 0.01     # the owner, 10/1 ("yes" - there's always a Lock): a day nothing clears the Lock test, the best
#                          own read (56%+) within 1 point of its price - ½u floor, marked near_price (the audit: 30 of 65
#                          days had none, mostly -135..-150 baseball favorites 1 point short)


def near_lock(cands, raw=False):
    """The last-resort Lock: the engine's own read 56%+ and within NEAR_LOCK_GAP of what the price needs - never past
    +125 / -150, never a trap, never the engine fighting it, never the pricey hockey favorite. The likeliest first."""
    pool = []
    for c in cands:
        if c.get("market") != "ml" or not MAX_FAV <= c.get("odds", 0) <= PLUS_LOCK_MAX or c.get("edge_own") is None \
                or not c.get("reasons") or c.get("trap") or c.get("waiting") or nhl_pricey(c) or hockey_fav_bad(c):
            continue
        own = read_of(c) if not raw else (c["edge_own"] + 1) / c["dec"]
        if own is None or own < LOCK_BACKUP_OWN or own < 1 / c["dec"] - NEAR_LOCK_GAP:
            continue
        if own < 1 / c["dec"] - FIGHT_MAX or money_against(c) or sports_strength.weak(c.get("league")):
            continue                                         # (fighting() minus its own-read test, which is this one)
        pool.append((round(own, 3), c))
    if not pool:                                             # (10/2: the favorites' weighed read can leave no one;
        return near_lock(cands, raw=True) if not raw else None   # the owner, 10/2: "how many times I gotta tell you,
    best = max(pool, key=lambda x: x[0])[1]                  #  yes, there's ALWAYS a Lock of the Day" - permanent)
    best["near_price"] = True                                # (sized ½u+, never pulled by the money check)
    return best


LOCK_MISS_PATH = os.path.join(sd.DATA, "lock_miss.json")


def lock_miss(cands, all_cands=None):
    """(the owner, 10/2: "can someone ask the question box what it would have been ... Virginia Tech, but it didn't quite
    meet the criteria") A day with no Lock: the pick that came closest (the old forced-Lock pick, near_lock) and why it
    fell short - for the question box only. Never a pick, never units, never in the record."""
    c = near_lock([dict(x) for x in cands])                  # the same pick the forced Lock made (10/2: Virginia
    if not c:                                                 # Tech all morning) - the healthy pool first, then any
        b = last_lock([dict(x) for x in (all_cands or cands)])   # side the board could still post
        c = b["legs"][0] if b else None
    if not c or not c.get("dec") or read_of(c) is None:
        return None
    own, need = read_of(c), 1 / c["dec"]
    gap = round((own - need) * 100, 1)
    return {"team": c.get("team"), "opp": c.get("opp"), "league": c.get("league"), "odds": c.get("odds"),
            "game_id": c.get("game_id"), "start": c.get("start"), "engine's own read %": round(own * 100),
            "the price needs %": round(need * 100, 1),
            "why it's not the Lock": (f"our read only beats the price by {gap} points - not enough for the Lock" if gap > 0
                                      else f"our read is {abs(gap)} points under what the price needs - no value at that price")}


def save_lock_miss(iso, miss, path=None):
    """Keeps the last 7 days' near-misses (data/sports/lock_miss.json) - the opening board's, never overwritten later
    in the day by whatever games are left."""
    path = path or LOCK_MISS_PATH
    try:
        st = json.load(open(path))
    except (OSError, ValueError):
        st = {}
    if iso in st:
        return
    st[iso] = miss
    st = {k: st[k] for k in sorted(st)[-7:]}
    with open(path, "w") as f:
        json.dump(st, f, indent=1, sort_keys=True)


def backup_lock(cands):
    """The owner (CLAUDE.md, again 10/1): "There's always a Lock." When nothing clears the full Lock test, the pick the
    engine's OWN read has winning 56%+ that still beats its price - the most value first - never past -150, never the
    pricey hockey favorite, never a trap, never one the engine is fighting. A unit play (sized by that read)."""
    pool = [c for c in cands if c["market"] == "ml" and MAX_FAV <= c["odds"] <= PLUS_LOCK_MAX and c.get("edge_own") is not None
            and c.get("reasons") and not c.get("trap") and not c.get("waiting") and not fighting(c) and not nhl_pricey(c)
            and not hockey_fav_bad(c) and (c["edge_own"] + 1) / c["dec"] >= LOCK_BACKUP_OWN and c["edge_own"] > 0]
    return max(pool, key=lambda c: (round((c["edge_own"] + 1) / c["dec"], 3), c["edge_own"])) if pool else None


def lock_value(c):
    """The Lock's value with every proven nudge in (rank_p's): the engine's own read, moved as rank_p moves the win %,
    over the price (10/1: ranked by raw value, the Astros - a playoff favorite that just lost the last game - got back
    in)."""
    if c.get("w_p") is not None:                             # (10/1 audit) a hockey favorite's weighed read already
        return (c["w_p"] + rank_p(c) - c["p"] - season_w(c)) * c["dec"] - 1   # holds the early-season weight - once
    own = (c["edge_own"] + 1) / c["dec"]
    return (own + rank_p(c) - c["p"]) * c["dec"] - 1


NHL_FAV_PER_PT = 0.005   # the hockey favorite study (10/1, 2019-26, -150 or better): the dog across from it, scored with
NHL_FAV_CAP = 0.04       # every spot and fade, WEIGHS the favorite's read - half a point of win % per point of the dog's
#                          score the other way (dog -4 or lower: the favorite won 58.9%, +2.6% on 671, 2023+ +1.9%;
#                          dog 0 or higher: 53.5%, -6.2%, 2023+ -11..-12%). The 1-8 hockey run (the owner, 10/1).
NHL_EARLY_FAV = -0.03    # ...and the season's first 2 weeks weigh every hockey favorite down (55% won, -4.3%; the owner:
#                          "opening week the dogs are winning") - weights, never a rule (the owner, 10/1)


def mark_hockey_favorites(cands):
    """Every hockey moneyline favorite gets its WEIGHED read (w_p): the no-vig line, moved by the dog score of the team
    across from it (opp_dog) and the early-season weight. It's a pick only if that whole read beats its price."""
    ml = {}
    for c in cands:
        if c.get("league") == "nhl" and c.get("market") == "ml":
            ml.setdefault(c["game_id"], []).append(c)
    for pair in ml.values():
        if len(pair) != 2:
            continue
        fav, dog = sorted(pair, key=lambda c: c["odds"])
        if fav["odds"] >= 0 or not 100 <= dog["odds"] <= DAILY_DOG_MAX:
            continue
        fav["opp_dog"] = round(dog_score(dog), 2)
        if fav.get("p_market") is not None:
            lift = max(-NHL_FAV_CAP, min(NHL_FAV_CAP, -NHL_FAV_PER_PT * fav["opp_dog"]))
            early = NHL_EARLY_FAV if season_w(fav) < 0 else 0.0
            tired = NHL_3IN4_FAV if third_in_four(fav, dog) and not dog.get("tired_vs_rested") else 0.0   # (10/1
            #         audit: a dog that played last night is already -3 in its score, which lifts the favorite - once)
            slump = NHL_SV_SLUMP_FAV if str(fav.get("team_id")) in SV_SLUMP else 0.0
            if slump:
                dog["opp_sv_slump"] = True
            fav["w_p"] = round(min(0.95, max(0.05, fav["p_market"] + lift + early + tired + slump)), 4)


FAV_PER_PT = 0.005       # the owner, 10/2: "make sure the engine weighs everything making its picks." Hockey already
FAV_CAP = 0.04           # weighed the favorite by the dog across from it; every other sport's favorite only had its own
#                          read - the studies (dog_spots: fades, spots, momentum, injuries, prices) moved the DOG's score
#                          and never the favorite's. Now each favorite's read moves the other way, half a point per point
#                          of the dog's study score (capped 4) - hockey's tested size, a weight, never a trigger.


def weigh_favorites(cands):
    """Every non-hockey moneyline favorite gets its WEIGHED read (w_p): its own read, moved the other way by the study
    points on the dog across from it (dog_spots - not the dog's own-read gap, that's the same ratings counted twice)."""
    ml = {}
    for c in cands:
        if c.get("league") != "nhl" and c.get("market") == "ml":
            ml.setdefault(c["game_id"], []).append(c)
    for pair in ml.values():
        if len(pair) != 2:
            continue
        fav, dog = sorted(pair, key=lambda c: c["odds"])
        if fav["odds"] >= 0 or dog["odds"] < 100 or fav.get("w_p") is not None or fav.get("edge_own") is None:
            continue
        pts = dog_spots(dog)
        if not pts:
            continue
        lift = max(-FAV_CAP, min(FAV_CAP, -FAV_PER_PT * pts))
        fav["opp_dog_pts"] = round(pts, 2)
        fav["w_p"] = round(min(0.95, max(0.05, (fav["edge_own"] + 1) / fav["dec"] + lift)), 4)


MLB_DROUGHT_W = 0.03     # a baseball favorite that hasn't scored in 12+ innings: +10.2% on 217 at -150..-101, 7 of 9
#                          seasons (sports_form) - the books overreact. Was a ranking nudge only; now it moves the read
#                          (the 10/1 wiring audit; the owner: "everything we studied has to be wired in")


def weigh_mlb_drought(cands):
    """The scoring-drought favorite's read moves up by MLB_DROUGHT_W (its win %, and its own read with it)."""
    for c in cands:
        if c.get("league") == "mlb" and c.get("market") == "ml" and -150 <= c.get("odds", 0) < 0 and overreact(c):
            c["p"] = min(0.95, c["p"] + MLB_DROUGHT_W)
            c["edge"] = c["p"] * c["dec"] - 1
            if c.get("edge_own") is not None:
                c["edge_own"] = min(0.95, (c["edge_own"] + 1) / c["dec"] + MLB_DROUGHT_W) * c["dec"] - 1
            c["reasons"] = c["reasons"] + ["hasn't scored in 12+ innings - the books overreact (+10.2%, 7 of 9 seasons)"]
            c["drought_w"] = True                            # (already in its read: rank_p never adds it twice)


NHL_SV_SLUMP_FAV = 0.015   # 10/1 study: a favorite whose goalie is slumping (last-10 save % bottom quarter) beat its
#                            price 5 of 5 seasons by ~8 pts - half of it on the favorite's weighed read (a lead)
SV_SLUMP = set()           # {nhl team id} with a slumping goalie (sports_form.sv_slump, refreshed each run)
NHL_3IN4_FAV = 0.015     # 10/1 study: a rested hockey favorite vs a team on its 3rd game in 4 nights (the favorite not on a
#                          back-to-back) beat its price 8 of 8 seasons (+5.2 pts vs the same price, 2023+ 3 of 3) - half of
#                          that as a weight on the favorite's read (a lead: it doesn't clear the multiple-testing bar)


def third_in_four(fav, dog):
    """The dog side is on its 3rd game in 4 nights and the favorite didn't play yesterday."""
    import sports_form
    st = fav.get("start")
    if not st:
        return False
    try:
        t0 = datetime.strptime(st[:10], "%Y-%m-%d")
    except ValueError:
        return False
    def n_recent(team):
        out = 0
        for s_ in LAST_STARTS.get(("nhl", team), []):
            try:
                d = (t0 - datetime.strptime(s_[:10], "%Y-%m-%d")).days
            except ValueError:
                continue
            out += 1 <= d <= 3
        return out
    tid_fav, tid_dog = fav.get("team_id"), dog.get("team_id")
    if tid_fav is None or tid_dog is None:
        return False
    return n_recent(tid_dog) >= 2 and not sports_form.played_yesterday(LAST_STARTS, "nhl", tid_fav, st)


NFL_WEST_FAV_W = 0.02   # 10/1 study: a West Coast NFL team FAVORED on the road in an Eastern-time city won 76%, +20.6% at
#                         the close (+12.8% at the early fair number), 7 of 8 seasons, 3 of 3 recent; the Eastern home
#                         dog in those games -23.5% - the market over-penalizes the traveler (same as the East->West dog).
#                         A lead (no 2026 games yet): +2 win-% points on the favorite's read, -2 on that home dog's score


def weigh_west_coast_road_fav(games, cands):
    """The West Coast road favorite in an Eastern city: its read moves up NFL_WEST_FAV_W; the home dog gets marked."""
    try:
        _, htz = _sched(games)
    except Exception:                                        # noqa: BLE001 - extra facts never block the board
        return
    for c in cands:
        if c.get("league") != "nfl" or c.get("market") != "ml" or c.get("home") or not -150 <= c.get("odds", 0) < 0:
            continue
        g = games.get(c["game_id"]) or {}
        try:
            gtz = float(g.get("tzo"))
        except (TypeError, ValueError):
            continue
        if str(g.get("neutral")) == "1" or (htz.get(("nfl", g.get("away"))) or 0) > -7 or gtz < -5:
            continue
        c["p"] = min(0.95, c["p"] + NFL_WEST_FAV_W)
        c["edge"] = c["p"] * c["dec"] - 1
        if c.get("edge_own") is not None:
            c["edge_own"] = min(0.95, (c["edge_own"] + 1) / c["dec"] + NFL_WEST_FAV_W) * c["dec"] - 1
        c["reasons"] = c["reasons"] + ["a West Coast favorite in the East - the market over-penalizes the trip (7 of 8 seasons)"]
        for d in cands:
            if d["game_id"] == c["game_id"] and d is not c and d.get("market") == "ml":
                d["west_trip_dog"] = True


HOOPS_INSIDE_W = 0.01


def weigh_hoops_inside(games, cands, now):
    """🏀 A hoops favorite that wins inside: +1 win-% point on its read (sports_hoops_style - a lead)."""
    hoops = [c for c in cands if c.get("league") in ("nba", "ncaab") and c.get("market") == "ml" and -300 <= c.get("odds", 0) < 0]
    if not hoops:
        return
    try:
        import sports_hoops_style as hs
        sts = {lg: hs.states(lg, now.strftime("%Y-%m-%dT%H:%MZ")) for lg in {c["league"] for c in hoops}}
    except Exception as e:                                   # noqa: BLE001 - extra facts never block the board
        print(f"hoops style failed: {str(e)[:60]}")
        return
    for c in hoops:
        g = games.get(c["game_id"]) or {}
        other = "away" if c["side"] == "home" else "home"
        if hs.inside(sts[c["league"]], c["league"], g.get(c["side"]), g.get(other)):
            c["p"] = min(0.95, c["p"] + HOOPS_INSIDE_W)
            c["edge"] = c["p"] * c["dec"] - 1
            if c.get("edge_own") is not None:
                c["edge_own"] = min(0.95, (c["edge_own"] + 1) / c["dec"] + HOOPS_INSIDE_W) * c["dec"] - 1
            c["hoops_inside"] = True
            c["reasons"] = c["reasons"] + ["wins inside - the glass / few 3s (beat its price 3 of 3 seasons)"]


def mark_doubleheader_game2(games, cands):
    """⚾ The second game of a doubleheader (the same two teams already played / play earlier the same day)."""
    for c in cands:
        if c.get("league") != "mlb" or c.get("market") != "ml":
            continue
        g = games.get(c["game_id"]) or {}
        day = (g.get("start") or "")[:10]
        for x in games.values():
            if x is g or x.get("league") != "mlb" or (x.get("start") or "")[:10] != day:
                continue
            if {x.get("home"), x.get("away")} == {g.get("home"), g.get("away")} and x.get("start", "") < g.get("start", ""):
                c["dh_game2"] = True
                break


def hockey_fav_bad(c):
    """A hockey favorite whose WEIGHED read (w_p) doesn't beat its price - everything weighed says no."""
    return c.get("league") == "nhl" and c.get("w_p") is not None and c.get("odds", 0) < 0 and c["w_p"] * c["dec"] <= 1


def nhl_pricey(c):
    """A hockey moneyline favorite at -130..-150 the engine's own read doesn't beat by NHL_FAV_EDGE (the owner, 10/1:
    "the biggest hockey favorite close to -150 - they keep losing")."""
    if c.get("w_p") is not None:
        return False                                         # (the weighed read backs it - the dog across is a bad one)
    return (c.get("league") == "nhl" and c.get("market") == "ml" and NHL_FAV_BAND[0] <= c.get("odds", 0) <= NHL_FAV_BAND[1]
            and (c.get("edge_own") if c.get("edge_own") is not None else c.get("edge", -1)) < NHL_FAV_EDGE)


def plays(cands, avoid):
    """💰 Every real UNIT play on the slate (the owner, 10/1: straight bets with units - the viewer builds his own
    parlay): real value (good()), a LOCK or VALUE grade (a strong lean carries no units - it's a lean), never past -150,
    never one the engine's own read is fighting, never a trap; one per game, never a game in `avoid`; surest first
    (the order the parlay legs used: win % with the proven nudges, then value)."""
    pool = sorted((c for c in cands if c["market"] in ("ml", "spread") and good(c) and c["odds"] >= MAX_FAV
                   and leg_tier(c) in ("lock", "value") and not fighting(c) and not c.get("trap") and real_value(c)),
                  key=lambda c: (-rank_p(c), -c["edge"]))
    out, seen = [], set(avoid)
    for c in pool:
        if c["game_id"] not in seen:
            seen.add(c["game_id"])
            out.append(c)
    return out


LEAN_WINNER_OWN = 0.55
CONF_LEAN_P = 0.55       # the owner, 10/1: "we can put money on leans we're confident about - it might not be a lock, but
CONF_LEAN_UNITS = 0.5    # we're comfortable enough to put money on it" (both leans won today). ½u on a lean the engine has
#                          winning 55%+ (its weighed read for hockey favorites), its own read beating the real price,
#                          never past -150, never one its read is fighting. Graded in the bankroll like any unit play.


def lean_units(c):
    """A lean we like is sized like every other pick - by how far its read beats the price (quarter-Kelly, ½u up;
    the owner, 10/1: "why does a lean have to be a half a unit? It depends on the lean")."""
    return max(CONF_LEAN_UNITS, kelly_units(read_of(c), c.get("odds") or -110))


def confident_lean(c):
    """A lean we like enough for ½ unit."""
    if c.get("market") not in ("ml", "spread") or c.get("odds", -999) < MAX_FAV or c.get("trap") or fighting(c) \
            or hockey_fav_bad(c) or nhl_pricey(c):
        return False
    p = min(c["p"], c["w_p"]) if c.get("w_p") is not None else c["p"]
    if p < CONF_LEAN_P:
        return False
    if c.get("edge_own") is None or c.get("p_market") is None:
        return False
    own = c["w_p"] if c.get("w_p") is not None else (c["edge_own"] + 1) / c["dec"]
    return own * c["dec"] > 1                                # (the owner, 10/1: "Steelers -148 at ½u - don't we lose
    #                                                          money in the long run?" Units only when the read beats
    #                                                          the REAL price we pay, never just the no-vig line)


# 📌 A LEAN STAYS PUT (the owner, 10/5: the Falcons +1.5 lean the night before turned into the Saints -1.5 lean at 8 AM
# because the Falcons moved +105 -> even on a game the engine called a coin flip all day - "the engine looks stupid").
# The first time the engine names a lean side on a game (the night-before preview, the pre-board check, the board), it's
# remembered; later it only switches sides if the engine's OWN read of that side drops LEAN_FLIP or more (a real change -
# a QB ruled out), never on a price tick.
LEAN_SIDES_PATH = os.path.join(sd.DATA, "lean_sides.json")
LEAN_FLIP = 0.03


def _lean_mem():
    try:
        with open(LEAN_SIDES_PATH) as f:
            return json.load(f)
    except Exception:                                        # noqa: BLE001
        return {}


def stick(c, pool):
    """The lean for c's game: the side remembered from earlier unless the engine's own read of it fell LEAN_FLIP+ (then
    the new side, remembered from here). pool = the game's other eligible candidates."""
    if not c.get("game_id") or not c.get("side"):
        return c
    mem = _lean_mem()
    gid, was = c["game_id"], mem.get(c["game_id"])
    out = c
    if was and was.get("side") != c["side"]:
        same = [x for x in pool if x.get("game_id") == gid and x.get("side") == was["side"]]
        same.sort(key=lambda x: (x.get("market") != was.get("market"), -(read_of(x) or 0)))
        if same and (read_of(same[0]) or 0) >= (was.get("own") or 0) - LEAN_FLIP:
            out = same[0]                                    # held: the read didn't really move
    if not was or was.get("side") != out["side"]:
        mem[gid] = {"side": out["side"], "market": out.get("market"), "team": out.get("team"),
                    "own": round(read_of(out) or 0, 4), "start": out.get("start") or ""}
        cut = (datetime.now(timezone.utc) - timedelta(days=4)).strftime("%Y-%m-%d")
        mem = {k: v for k, v in mem.items() if (v.get("start") or "9") >= cut}
        try:
            os.makedirs(os.path.dirname(LEAN_SIDES_PATH), exist_ok=True)
            with open(LEAN_SIDES_PATH, "w") as f:
                json.dump(mem, f, indent=1, sort_keys=True)
        except Exception as e:                               # noqa: BLE001 - never blocks the board
            print(f"lean memory not saved: {str(e)[:80]}")
    return out


def viewer_leans(cands, avoid):
    """🟡 The viewers' leans (no units, in the record): the side the engine has winning, or a dog its own read says is
    underpriced - never past -150, never fighting its own read, never a trap, never a spread it has no read on, never
    the pricey hockey favorite - on games we're not playing; the big games first, 2 a sport."""
    def ok(c):
        if c["market"] not in ("ml", "spread") or c["odds"] < MAX_FAV or c.get("trap") or nhl_pricey(c) \
                or hockey_fav_bad(c) or c["game_id"] in avoid:
            return False
        if fighting(c) and not (c["market"] == "ml" and c.get("edge_own") is not None
                                and (c["edge_own"] + 1) / c["dec"] >= LEAN_WINNER_OWN):
            return False                                     # a lean is a WHO-WINS call (no units): a favorite the
            #                                                  engine's own read still has winning 55%+ is a lean even
            #                                                  when the price is a bit high (10/1: two picks on 9 games)
        if c["market"] == "spread" and c.get("edge_own") is None and abs(c["p"] - 0.5) < 0.005:
            return False                                     # (10/1: no read of its own on that spread - a coin flip)
        if c["p"] >= LEAN_PICK_P:
            return True                                      # the side the engine has winning
        return 100 <= c["odds"] <= DAILY_DOG_MAX and (c.get("edge_own") or -1) >= 0.02   # or a dog its own read says is
        #                                                      underpriced (the owner, 10/1: "we need value plays")
    best = {}
    okc = [c for c in cands if ok(c)]
    for c in sorted(okc, key=lambda c: -rank_p(c)):
        best.setdefault(c["game_id"], c)
    best = {g: stick(c, okc) for g, c in best.items()}       # 📌 (10/5: a lean never flips on a price tick)
    out, per = [], {}
    for c in sorted(best.values(), key=lambda c: (-importance(c), -rank_p(c))):
        if per.get(c["league"], 0) < LEAN_PER_SPORT:        # (spread across the sports - "not five hockey games")
            per[c["league"]] = per.get(c["league"], 0) + 1
            out.append(c)
    # 🟡 THE FILL (the owner, 10/2: "we need five picks so we can have two more leans"): a lean is a WHO-WINS call with
    # no units, so a side the engine has winning whose PRICE isn't value (a hockey favorite) can still be a lean - after
    # the regular leans, the likeliest winners. Never past -150, never fighting its own read, never a trap, never a
    # read-less spread, never a game we're on.
    def fill_ok(c):
        return (c["market"] == "ml" and c["odds"] >= MAX_FAV and not c.get("trap") and c["game_id"] not in avoid
                and c["game_id"] not in best and not fighting(c) and c["p"] >= LEAN_PICK_P)
    extra = {}
    fillc = [c for c in cands if fill_ok(c)]
    for c in sorted(fillc, key=lambda c: -c["p"]):
        extra.setdefault(c["game_id"], c)
    extra = {g: stick(c, fillc) for g, c in extra.items()}
    for c in sorted(extra.values(), key=lambda c: -c["p"]):
        if per.get(c["league"], 0) < LEAN_PER_SPORT:
            per[c["league"]] = per.get(c["league"], 0) + 1
            out.append({**c, "fill": True})
    return out


def last_lock(cands, avoid=()):
    """The Lock when nothing else is left (10/2: Virginia Tech moved -135 -> -130, fell under the backup Lock's floor,
    and the board went up with NO Lock - "there's ALWAYS a Lock"): the engine's likeliest winner on a moneyline - never
    past -150, never a side its own read is fighting, never a trap, never a game we can't see (blind / a key player
    unknown). Posted as the backup Lock (½u, under the 'nothing met the standard' box)."""
    pool = [c for c in cands if c.get("market") == "ml" and c["odds"] >= MAX_FAV and not c.get("trap")
            and not fighting(c) and c["game_id"] not in avoid and c.get("p", 0) >= 0.5
            and not any("injury report" in w for w in c.get("waiting") or [])]
    if not pool:
        return None
    c = max(pool, key=lambda c: (c["p"], c.get("edge") or 0))
    return {"legs": [{**c, "near_price": True}], "dec": c["dec"], "p_hit": c["p"]}


def injury_line(g, side, injuries):
    """🚑 The card's injury line for a side that's missing players (10/2, the owner: "a lock, a dog and three leans, no
    matter what" - a banged-up side can still be on the board, and the card says who's missing): names, positions."""
    inj = (injuries or {}).get(g["league"])
    rows = sd._team_rows(inj, g[side], g[side + "_name"])
    gone = [f"{r[1]} {r[0]}".strip() for r in rows if any(x in r[2].lower() for x in sd.SHORT_TERM)
            and "season" not in r[2].lower()]
    unsure = [f"{r[1]} {r[0]}".strip() for r in rows if any(x in r[2].lower() for x in sd.UNSURE)]
    if len(gone) + len(unsure) < 2 and not any("suspen" in r[2].lower() for r in rows):
        return ""
    gone += [f"{r[1]} {r[0]} (suspended)".strip() for r in rows if "suspen" in r[2].lower()]
    parts = []
    if gone:
        parts.append(f"out: {', '.join(gone[:4])}" + (f" +{len(gone) - 4} more" if len(gone) > 4 else ""))
    if unsure:
        parts.append(f"questionable: {', '.join(unsure[:3])}" + (f" +{len(unsure) - 3} more" if len(unsure) > 3 else ""))
    return f"🚑 {g[side + '_name']} {' · '.join(parts)}."


def fill_hurt(g, side, injuries):
    """A fill lean's team missing somebody the engine doesn't weigh (10/2: the Red Wings lean with Dylan Larkin OUT,
    the Jets lean with Connor Hellebuyck suspended): anyone ruled out / doubtful, or a key player (goalie / QB) on a
    suspension. The fill leans are the engine's thinnest calls - one of those and it isn't a lean."""
    inj = (injuries or {}).get(g["league"])
    rows = sd._team_rows(inj, g[side], g[side + "_name"])
    return [r[0] for r in rows if any(x in r[2].lower() for x in sd.SHORT_TERM)
            or ("suspen" in r[2].lower() and sd._is_key(r, g["league"], g[side + "_name"]))]


def lean(cands, kind, taken=None, floor=None):
    """The best available play when nothing clears the value bar: the closest thing to value on the slate, same rules
    (no big favorites, no games underway, never the banged-up side - candidates already filter those). Tagged LEAN."""
    ml = [c for c in cands if c["market"] == "ml" and c.get("reasons") and not fighting(c) and not c.get("trap")]
    if kind == "lock":
        pool = [c for c in ml if c["odds"] >= (MAX_FAV if floor else LOCK_MAX_FAV) and c["p"] >= (floor or LEAN_MIN_P["lock"])]
    elif kind == "dog":
        pool = [c for c in ml if c["odds"] >= DOG_MIN and c["p"] >= LEAN_MIN_P["dog"] and c["game_id"] != taken]
    elif kind in ("two", "three", "four"):
        n = {"two": 2, "three": 3, "four": 4}[kind]
        best = {}
        for c in sorted((c for c in cands if c["odds"] >= MAX_FAV and c["p"] >= max(floor or LEAN_MIN_P[kind], PARLAY_LEG_MIN_P) and not fighting(c)
                         and not c.get("trap")), key=lambda c: -c["p"]):
            best.setdefault(c["game_id"], c)
        legs = sorted(best.values(), key=lambda c: (-importance(c), -c["p"]))[:n]   # the big games first, then the likeliest
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
    c = max(pool, key=lambda c: (importance(c), rank_p(c), c["edge"]))   # the big games first, then the likeliest
    return {"legs": [c], "dec": c["dec"], "p_hit": c["p"], "lean": True}


# ---------------------------------------------------------------- grading
def grade_leg(leg, g, now):
    """won / lost / push / void, or None while the game isn't over."""
    def stale():                                             # 4 days past the start and still no final: void
        if not leg.get("start"):
            return None
        start = datetime.strptime(leg["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        return "void" if now - start > timedelta(days=4) else None
    if g is None:                                            # the game's gone from our data (an id change, a wiped file):
        return stale()                                       # 4 days, then void - never open forever (10/3 sweep: it kept
        #                                                      TODAY'S RESULTS and the board day stuck on it)
    if g["status"] == "void":
        return "void"
    if g["status"] != "final" or g["home_score"] == "":
        return stale()
    hs, as_ = int(g["home_score"]), int(g["away_score"])
    if leg["market"] == "total":                              # over/under: total points vs the line
        d = (hs + as_ - leg["line"]) * (1 if leg["side"] == "over" else -1)
        return "won" if d > 0 else "lost" if d < 0 else "push"
    margin = (hs - as_) if leg["side"] == "home" else (as_ - hs)
    if leg["market"] == "spread":
        margin += leg["line"]
    return "won" if margin > 0 else "lost" if margin < 0 else "push"


def deciders(picks, budget_s=45):
    """🎯 How each newly graded game was decided (a last-second kick, overtime, a pick-six...) - for its review. One
    ESPN summary per game, kept; never blocks grading (sports_decider)."""
    try:
        import sports_decider
        sports_decider.fill(picks, budget_s=budget_s)
    except Exception as e:                                   # noqa: BLE001
        print(f"deciders failed: {str(e)[:80]}")


def _final_at():
    """When the live watcher saw each game go final ({game id: 'YYYY-MM-DDTHH:MMZ'})."""
    try:
        return json.load(open(os.path.join(sd.DATA, "final_at.json")))
    except (OSError, ValueError):
        return {}


def grade(picks, games, now=None):
    now = now or datetime.now(timezone.utc)
    settled = []
    stamp = now.strftime("%Y-%m-%dT%H:%MZ")
    ended = _final_at()

    def leg_done(leg):                                       # a graded leg: when its game ended (the grader can lag)
        leg["settled"] = min(ended.get(leg.get("game_id")) or stamp, stamp)
    for pk in picks[-40:]:                                   # graded legs from before the flow was kept: fill it in
        for leg in pk["legs"]:
            g = games.get(leg.get("game_id"))
            if leg.get("result") and not (leg.get("flow") or {}).get("h") and g and g.get("ls_home"):
                leg["flow"] = {"a": g.get("ls_away", ""), "h": g.get("ls_home", "")}
    for pk in picks:
        if pk["status"] == "lost" and any(leg.get("result") is None for leg in pk["legs"]):
            for leg in pk["legs"]:                           # a busted parlay's other legs still get graded (show every
                if leg.get("result") is None:                # hit and miss - full transparency)
                    leg["result"] = grade_leg(leg, games.get(leg["game_id"]), now)
                    g = games.get(leg["game_id"])
                    if leg["result"]:
                        leg_done(leg)
                    if leg["result"] and g:
                        leg["score"] = f'{g["away_name"]} {g["away_score"]} @ {g["home_name"]} {g["home_score"]}'
                        leg["flow"] = {"a": g.get("ls_away", ""), "h": g.get("ls_home", "")}   # period by period: the review tells how it went
            continue
        if pk["status"] != "open":
            continue
        for leg in pk["legs"]:
            if leg.get("result") is None:
                leg["result"] = grade_leg(leg, games.get(leg["game_id"]), now)
                g = games.get(leg["game_id"])
                if leg["result"]:
                    leg_done(leg)
                if leg["result"] and g:
                    leg["score"] = f'{g["away_name"]} {g["away_score"]} @ {g["home_name"]} {g["home_score"]}'
                    leg["flow"] = {"a": g.get("ls_away", ""), "h": g.get("ls_home", "")}   # period by period: the review tells how it went
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
            if all(r == "void" for r in res):
                pk["void"] = True                            # (10/2 audit: a called-off game read PUSH - it's a VOID)
        else:
            continue
        # settled = when it was decided: a lost one the moment its first leg lost (its 3 hours on the board count from
        # there - the owner, 9/29), a won / pushed one when its last game ended
        lost_t = [l.get("settled") or stamp for l in pk["legs"] if l.get("result") == "lost"]
        pk["settled"] = min(lost_t) if lost_t else max(l.get("settled") or stamp for l in pk["legs"])
        try:                                                 # (10/1 audit) the units it was graded at, frozen on the pick:
            if pk.get("kind") in PARLAY_KINDS:               # a later code change never re-sizes a graded pick
                for l in pk["legs"]:
                    if l.get("result") and l.get("units") is None:
                        l["units"] = leg_units(pk, l)
            elif pk.get("units") is None:
                pk["units"] = units_for(pk)
        except Exception as e:                               # noqa: BLE001 - grading never fails over the freeze
            print(f"units freeze failed: {str(e)[:80]}")
        settled.append(pk)
    freeze_units(picks)
    return settled


def freeze_units(picks):
    """Every graded pick (and every graded leg of a parlay) carries the units it was graded at, forever - whether it was
    graded before the freeze existed (9/27-9/30) or on a busted parlay's other legs (graded after the ticket lost, which
    the freeze above never reached). 10/3 sweep: those rows were still re-sized by every code change (the 10/1 audit had
    already seen 9 graded rows move once). Silent on any failure - grading never waits on it."""
    for pk in picks:
        try:
            if pk.get("kind") in PARLAY_KINDS:
                for l in pk.get("legs") or []:
                    if l.get("result") in ("won", "lost", "push", "void") and l.get("units") is None:
                        l["units"] = leg_units(pk, l)
            elif pk.get("status") in ("won", "lost", "push", "void") and pk.get("units") is None and pk.get("legs"):
                pk["units"] = units_for(pk)
        except Exception as e:                               # noqa: BLE001
            print(f"units freeze failed: {str(e)[:80]}")


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


SLATE_PATH = os.path.join(sd.DATA, "slate_check.json")
SLATE_LAST_TRY = (8, 30)       # the 8 AM post holds while the slate check finds a problem (the engine re-pulls at
                               # 8:12 and 8:32); from 8:30 PT it posts what checks out and flags the rest loudly


_ELO = {}


def skipped_why(g, now, games, model):
    """Why candidates() left a priced game out ON PURPOSE ('' = it shouldn't have: a real miss that holds the board):
    it starts too soon to post, or the model knows too little about a team (an FCS / Ivy school with few games)."""
    st = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    if st < now + timedelta(minutes=MIN_LEAD_MIN):
        return "starts too soon to post"
    if sd.exhibition(g):                                     # (an all-star / Pro Bowl side: candidates() skips it)
        return "an all-star / exhibition game - skipped on purpose"
    if model is None:
        return ""
    if _ELO.get("ref") is not games:
        _ELO.update(ref=games, elo=sm.ratings(games, model))
    try:
        if _ELO["elo"][g["league"]].features(g)["known"] < MIN_KNOWN:
            return "the engine knows too little about a team (few games in our data) - skipped on purpose"
    except Exception:                                        # noqa: BLE001 - unknown = a real miss, it holds
        return ""
    return ""


def slate_check(games, cands, day, now, errors=None, model=None):
    """🔎 Before the board goes up (the owner, 9/30: "it can't be missing no games and no bugs"): every real game on
    the day's slate has both teams named (9/29: a 'TBD' playoff placeholder hid White Sox @ Astros), a price, and was
    looked at by the engine; and the run's data pulls didn't fail. Writes data/sports/slate_check.json.
    Returns the problems (plain words)."""
    todays = [g for g in games.values() if g.get("league") in sd.LEAGUES and (g.get("stype") or "?") in sd.REAL
              and g.get("status") == "pre" and g.get("start") and g.get("tbd") != "1"
              and datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).astimezone(PT).date() == day]
    seen = {c["game_id"] for c in cands}
    probs = []
    for g in sorted(todays, key=lambda g: g["start"]):
        name = f'{g.get("away_name") or "?"} @ {g.get("home_name") or "?"} ({g["league"].upper()})'
        if any(not n or "TBD" in str(n).upper() or str(n).strip() in ("?", "-") for n in (g.get("away_name"), g.get("home_name"))):
            probs.append(f"{name}: a team isn't named yet")
        elif sm._int(g.get("ml_home")) is None or sm._int(g.get("ml_away")) is None:
            if str(g.get("stype")) == "3":           # (10/1 audit: three "if necessary" playoff games that were never
                print(f"SLATE CHECK (not held): {name}: no price - an 'if necessary' playoff game?", flush=True)
                continue                             # played held the 8 AM board till 8:38)
            if g.get("league") in ("ncaaf", "ncaab"):    # (10/2 audit: ~25 unpriced small-school games held every
                print(f"SLATE CHECK (not held): {name}: no price - a small-school game the books skip", flush=True)
                continue                                 # college Saturday's 8 AM board till 8:30)
            probs.append(f"{name}: no price from the books")
        elif g["id"] not in seen:
            why = skipped_why(g, now, games, model)      # (10/3: ten FCS / Ivy games the model barely knows - skipped on
            if why:                                      # purpose - held Saturday's 8 AM board till 8:47)
                print(f"SLATE CHECK (not held): {name}: {why}", flush=True)
                continue
            probs.append(f"{name}: priced but the engine never looked at it")
    days = (day.isoformat(), (day - timedelta(days=1)).isoformat())   # (10/1 audit: the real messages are "nfl
    bad = [e for e in (errors if errors is not None else sd.ERRORS)   # 2026-10-01: HTTP Error 500" - the old word
           if any(d in str(e) for d in days)                         # filter never matched one: today's / last
           or any(k in str(e).lower() for k in ("odds", "scoreboard", "schedule", "action network", "espn"))]   # night's
    probs += [f"data pull failed: {str(e)[:80]}" for e in bad[:5]]
    out = {"at": now.strftime("%Y-%m-%dT%H:%MZ"), "day": day.isoformat(), "games": len(todays),
           "looked_at": len([g for g in todays if g["id"] in seen]), "problems": probs}
    try:
        with open(SLATE_PATH + ".tmp", "w") as f:
            json.dump(out, f, indent=1)
        os.replace(SLATE_PATH + ".tmp", SLATE_PATH)
    except OSError:
        pass
    for x in probs:
        print(f"SLATE CHECK: {x}", flush=True)
    return probs


def data_gaps(games, cands, now):
    """🔎 NEVER FALSE INFO (the owner, 10/1: "North Texas is not 0-1, they're 2-2 ... we always have to have updated
    data"): every team on the slate, every sport - a college team we don't hold every game for this season, or a game of
    theirs from the last 10 days whose result never came in. {(league, team id): what's missing}. A team with a gap holds
    the board (the engine re-pulls) and never gets a pick: its read would run on half the picture."""
    import sports_breakdown_v24 as v24
    _t = v24._t
    fin, out = {}, {}
    for c in cands:
        g = games.get(c["game_id"]) or {}
        lg = c["league"]
        for side in ("home", "away"):
            tid = g.get(side)
            if not tid or (lg, tid) in out:
                continue
            if lg in ("ncaaf", "ncaab"):
                if lg not in fin:
                    fin[lg] = [x for x in sm.finals(games, lg) if _t(x["start"]) < now]
                if not v24.seen_all(fin[lg], tid, _t(g["start"]), lg):
                    out[(lg, tid)] = f"{g.get(side + '_name')}: we don't hold all their games this season"
                    continue
            for x in games.values():
                if x.get("league") == lg and tid in (x.get("home"), x.get("away")) and x.get("status") == "pre" \
                        and now - timedelta(days=10) < _t(x["start"]) < now - timedelta(hours=8) \
                        and x.get("ml_home") not in ("", None):      # (10/1: an "if necessary" playoff game that never
                    #                                                  got played never had a price - not a missing result)
                    out[(lg, tid)] = f"{g.get(side + '_name')}: no result for their {x['start'][:10]} game"
                    break
    return out


STATE_FAILS = []   # (10/1 audit) the inputs that failed to load this run - each loads on its own and the double
#                    check reports them (one failure used to leave every input after it empty, silently)


STALE_OPEN_PTS = 0.04   # the stored open vs the first price we saw that week: 4+ points of win % apart = a stale open
OPEN_FIXED = []         # this run's corrected opens (the factor check reports them)


def fix_opens(games, hist=None):
    """📈 THE REAL OPEN (10/2, the owner caught it: "how could Penn State open at -278?"). ESPN's college "open" can be
    a lookahead line from the summer (Penn State -278, now -142 - but -142 since the first price we saw 10/1, it never
    moved). Every upcoming game our line history tracked from at least 12 hours out gets its open set to the first
    price we saw that week when the stored one is 4+ points of win % off it - so no card, reason, dog angle or early
    play reads a summer line as 'sharp money moving'. Past games (the model's training) are never touched."""
    import sports_clv
    hist = sports_clv._hist() if hist is None else hist
    del OPEN_FIXED[:]
    for gid, rows in hist.items():
        g = games.get(gid)
        if not g or g.get("status") != "pre" or not rows:
            continue
        t0, h, a = rows[0][0], sm._int(rows[0][1]), sm._int(rows[0][2])
        if h is None or a is None:
            continue
        try:
            lead = (datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M") - datetime.strptime(t0[:16], "%Y-%m-%dT%H:%M"))
        except (KeyError, ValueError):
            continue
        if lead < timedelta(hours=12):
            continue                                         # we only saw it late: the stored open may be the better one
        first = sm.market_p({"ml_home": h, "ml_away": a})
        cur = sm.market_p(g, open_line=True)
        if first is not None and (cur is None or abs(cur - first) >= STALE_OPEN_PTS):
            OPEN_FIXED.append(f"{g.get('away_name')} @ {g.get('home_name')}: open {g.get('ml_home_open') or '-'} -> {h}")
            g["ml_home_open"], g["ml_away_open"] = str(h), str(a)
    return OPEN_FIXED


def load_states(games):
    """Load every state the engine weighs, each on its own (a failure never blanks the rest); STATE_FAILS lists them."""
    try:
        fix_opens(games)                                     # (10/2: the real open before anything reads a line move)
    except Exception as e:                                   # noqa: BLE001
        print(f"open fix failed: {str(e)[:80]}")
    import sports_form
    import sports_coaches
    import sports_coach_changes
    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    del STATE_FAILS[:]

    def ats():
        a_, m_ = sports_form.ats_states(games)
        ATS[0].clear(), ATS[0].update(a_), ATS[1].clear(), ATS[1].update(m_)
    steps = [("hot players", HOT_KEY, lambda: sports_form.hot_sides(games, sp.CACHE, iso)),
             ("team form", TEAM_STATE, lambda: sports_form.team_states(games, iso)),
             ("rest / back-to-backs", LAST_STARTS, lambda: sports_form.last_starts(games)),
             ("cover streaks", None, ats),
             ("season starts", SEASON_START, lambda: season_starts(games, datetime.now(timezone.utc))),
             ("coaches", COACH, lambda: sports_coaches.states(iso)),
             ("coach firings", FIRED, lambda: sports_coach_changes.recent(iso)),
             ("first-time coaches", FIRST_TIMER, lambda: sports_coach_changes.first_timers(games, iso)),
             ("dog studies' form", DOG_ST, lambda: sports_form.dog_states(games, iso)),
             ("hockey puck luck", PDO, lambda: sports_form.pdo_states(games, iso)),
             ("goalie save % slumps", SV_SLUMP, lambda: (str(t) for t in sports_form.sv_slump()))]
    for name, box, fn in steps:                          # (same order as before: PDO fills LAST_SV before sv_slump)
        try:
            if box is None:
                fn()
                continue
            box.clear()
            box.update(fn())
        except Exception as e:                               # noqa: BLE001 - one input failing never blanks the rest
            STATE_FAILS.append(name)
            print(f"{name} failed to load: {str(e)[:80]}", flush=True)


def _ts(x):
    try:
        return datetime.strptime(str(x)[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def factor_check(games, cands, injuries, day, now, model=None):
    """🔎 THE DOUBLE CHECK, part 1 (the owner, 10/1: "every day before the engine posts there needs to be a check - make
    sure it's weighing every factor, every study"): every study's data actually loaded for the sports on today's slate.
    A missing piece holds the board (the engine re-pulls) until SLATE_LAST_TRY, then it posts and the log says what
    was missing. Adds the result to slate_check.json."""
    lgs = {c["league"] for c in cands}
    probs = [f"the {x} data failed to load" for x in STATE_FAILS]
    for lg in sorted(lgs):
        if lg in ("nfl", "ncaaf", "ncaab", "nba", "nhl", "mlb") and not any(k[0] == lg for k in DOG_ST):
            probs.append(f"{lg.upper()}: the last-result / form data (dog studies) didn't load")
        if lg in sports_form.B2B_LEAGUES and not any(k[0] == lg for k in LAST_STARTS):   # (rest data: hockey / hoops)
            probs.append(f"{lg.upper()}: the rest / back-to-back data didn't load")
        inj_lg = (injuries or {}).get(lg)
        if inj_lg is None or (not inj_lg and lg in sd.PRO):   # None = the pull failed; an EMPTY pro feed is one too (ESPN's
            probs.append(f"{lg.upper()}: the injury report didn't load")   # pro feeds always list somebody). An empty
        #                                                  college feed is real (ESPN carries ~3 college football teams and
        #                                                  no college hoops): those teams are UNKNOWN and get no pick anyway -
        #                                                  never a 30-minute hold on every college day (10/3 sweep)
    fb = [c for c in cands if c["league"] in ("nfl", "ncaaf") and c.get("market") == "ml"]
    if fb and not any("win_streak" in (c.get("dog_more") or {}) for c in fb):
        probs.append("football: the dog findings (bye, Monday night, streaks, coaches) didn't load")
    if any(c["league"] == "nfl" for c in cands):
        import sports_go4
        up = sports_go4.load().get("updated")
        try:
            stale = (now - datetime.strptime(up, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)).days > 3
        except (TypeError, ValueError):
            stale = True
        if stale:
            probs.append("NFL: the 4th-down rates are missing or 3+ days old")
    # (the owner, 10/2: "did the engine have all the accurate, updated daily data across every aspect?")
    gids = {c["game_id"] for c in cands}
    stale = []
    for gid in gids & set(games):                           # the prices: every game priced by the books lately
        g = games[gid]
        try:
            t = datetime.strptime(str(g.get("odds_time"))[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
            if now - t > timedelta(hours=12):
                stale.append(g.get("home_name") or gid)
        except ValueError:
            stale.append(g.get("home_name") or gid)
    if stale and len(stale) * 2 > len(gids & set(games)):                 # most of the slate unpriced = the odds pull failed: hold
        probs.append(f"{len(stale)} of {len(gids)} games without a fresh price (12h+): {', '.join(sorted(stale)[:4])}")
    elif stale:                                              # a few the books stopped listing: say so, never hold
        print(f"FACTOR NOTE: {len(stale)} game(s) priced 12h+ ago: {', '.join(sorted(stale)[:4])}", flush=True)
    late = [g for g in games.values() if g.get("league") in lgs and g.get("status") not in ("final", "void", "post")
            and g.get("ml_home") not in ("", None) and g.get("tbd") != "1"   # (10/3: three MLB "if necessary" Game 3s -
            and timedelta(hours=8) < now - _ts(g.get("start")) < timedelta(days=3)]   # never played, never priced - held
    #                                                      Saturday's board as 'recent games with no final score')
    if len(late) > 2:                                        # the scores: recent games still without a final
        probs.append(f"{len(late)} recent games have no final score yet (the form / rest / streak data is behind)")
    for lg in sorted(lgs & set(sp.ROLE)):                     # the players: QB / pitcher / goalie numbers loaded
        if not sp.CACHE.get(lg):
            probs.append(f"{lg.upper()}: the player stats (QB / pitcher / goalie) didn't load")
    out_ = [games[g] for g in gids if (games.get(g) or {}).get("league") in ("nfl", "ncaaf", "mlb")
            and str(games[g].get("indoor")) != "1"]
    if out_ and sum(str(g.get("wx_temp", "")) == "" for g in out_) > len(out_) / 2:   # the weather: outdoor games
        probs.append(f"the weather is missing for {sum(str(g.get('wx_temp', '')) == '' for g in out_)} of "
                     f"{len(out_)} outdoor games")
    priced = [games[g] for g in gids if g in games and games[g].get("ml_home")]
    if priced and sum(1 for g in priced if not g.get("ml_home_open")) * 2 > len(priced):
        probs.append(f"the opening lines are missing for {sum(1 for g in priced if not g.get('ml_home_open'))} of "
                     f"{len(priced)} games (the line movement can't be weighed)")
    if model is not None:                                    # the engine's own read: every sport's model loaded
        for lg in sorted(lgs):
            if not (model.get("params") or {}).get(lg):
                probs.append(f"{lg.upper()}: the engine's model for this sport didn't load")
    try:                                                     # the public splits: card lines only (nothing proven, so
        import sports_public                                 # they don't move a pick) - a note when they're old
        live = sports_public._load(sports_public.LIVE)
        have = [g for g in gids if g in live and sports_public.fresh(live[g], now)]
        if gids and games and len(have) * 2 < len(gids & set(games)):
            print(f"FACTOR NOTE: public splits fresh for only {len(have)} of {len(gids)} games - the cards skip the "
                  f"old ones", flush=True)
    except Exception:                                        # noqa: BLE001
        pass
    blind = sorted({g_.get(s_ + "_name") or g_[s_] for g_ in (games.get(x) for x in gids) if g_ for s_ in ("home", "away")
                    if g_.get(s_) and (injuries or {}).get(g_.get("league")) is not None
                    and not sd.covered(injuries[g_["league"]], g_["league"], g_[s_], g_.get(s_ + "_name", ""))})
    if blind:                                                # (10/2: ESPN's college feed listed 3 teams - the engine
        print(f"FACTOR NOTE: no injury report for {len(blind)} team(s) - no pick on their games: "   # never picks blind)
              f"{', '.join(blind[:8])}", flush=True)
    if OPEN_FIXED:                                           # (10/2: stale summer opens, fixed before the read)
        print(f"FACTOR NOTE: {len(OPEN_FIXED)} stale opening line(s) replaced by the first price we saw that week: "
              f"{'; '.join(OPEN_FIXED[:3])}", flush=True)
    nhl_ml = {}
    for c in cands:
        if c["league"] == "nhl" and c.get("market") == "ml":
            nhl_ml.setdefault(c["game_id"], []).append(c)
    hk = [min(pair, key=lambda c: c["odds"]) for pair in nhl_ml.values() if len(pair) == 2   # the favorites the weighing
          and min(c["odds"] for c in pair) < 0 and 100 <= max(c["odds"] for c in pair) <= DAILY_DOG_MAX]   # covers: a dog
    if hk and not any(c.get("w_p") is not None for c in hk):   # +100..+220 across (10/3 sweep: a lone -280 favorite had
        #                                                       no w_p by design and would have held the board)
        probs.append("NHL: the hockey favorites weren't weighed against the dog across the ice")
    try:
        cur = json.load(open(SLATE_PATH)) if os.path.exists(SLATE_PATH) else {}
        cur["factors"] = probs
        with open(SLATE_PATH + ".tmp", "w") as f:
            json.dump(cur, f, indent=1)
        os.replace(SLATE_PATH + ".tmp", SLATE_PATH)
    except (OSError, ValueError):
        pass
    for x in probs:
        print(f"FACTOR CHECK: {x}", flush=True)
    return probs


def rule_check(picks, new, iso, games=None, day=None, now=None):
    """🔎 THE DOUBLE CHECK, part 2: every pick about to go up obeys the owner's rules - never past -150, no puck / run
    lines, one pick per game, a Lock / Dog always carries units, the Dog never past its cap, units only when the read
    beats the real price. A pick that breaks one is pulled before it posts (and the log says why). Also flags a
    Monday / Thursday NFL game left without its pick. Returns the problems."""
    probs, seen = [], {}
    for p in picks:
        if p["date"] == iso and p["status"] != "waiting" and p not in new and p.get("kind") not in PARLAY_KINDS:
            for l in p["legs"]:
                seen[l["game_id"]] = p
    for pk in list(new):
        l = (pk.get("legs") or [{}])[0]
        why = None
        if l.get("market") == "ml" and (l.get("odds") or 0) < MAX_FAV:
            why = "past -150"
        elif l.get("league") in ("nhl", "mlb") and l.get("market") not in ("ml", "total"):
            why = "a puck line / run line"
        elif l.get("game_id") in seen:
            why = "a second pick on a game we're already on"
        elif pk.get("kind") in ("lock", "dog") and not pk.get("lean") and not units_for(pk):
            why = f"a {pk['kind']} with no units"
        elif pk.get("kind") == "dog" and (l.get("odds") or 0) > DAILY_DOG_MAX:   # (10/2 audit: +220, the owner's 10/1
            why = "a Dog past its cap"
        elif units_for(pk) and not beats_price(l) and (pk.get("date") or "") >= MONEY_CHECK_FROM \
                and pk.get("kind") != "solo" and not l.get("near_price"):   # (a one-game day's pick / the always-a-
            #                                                  Lock backup always carry units - the owner)
            why = "units on a price its read doesn't beat"
        if why:
            probs.append(f"pulled {pk.get('kind')} {l.get('team')} {l.get('odds')}: {why}")
            new.remove(pk)
            if pk in picks:
                picks.remove(pk)
        else:
            seen[l.get("game_id")] = pk
    probs += sizing_check(new)
    if games is not None and day is not None and day.weekday() in (0, 3):
        for gid in night_games(games, day, picks, now or datetime.now(timezone.utc)):
            if gid not in _straight_games(picks, iso):
                probs.append(f"Monday/Thursday NFL game {gid} has no pick yet")
    for x in probs:
        print(f"RULE CHECK: {x}", flush=True)
    return probs


def sizing_check(new):
    """🔎 THE SIZING CHECK (the owner, 10/2: "is our sizing system checked properly?"): every pick about to post carries
    the units the unit system says - a lean 0, a value play ½u, the Dog 1u, the backup Lock ½u, a Lock ½u-10u (½u on a
    thin edge), a one-game day's pick ½u+. Reports only (a Lock is never pulled - there's always a Lock)."""
    out = []
    for pk in new:
        if (pk.get("date") or "") < SIZING_FROM or pk.get("kind") in PARLAY_KINDS or not pk.get("legs"):
            continue
        l, u, k = pk["legs"][0], units_for(pk), pk.get("kind")
        want = None
        if pk.get("lean"):
            want = (0, 0) if k != "solo" else (0.5, 10)
        elif k == "play":
            want = (PLAY_UNITS, PLAY_UNITS)
        elif k == "dog":
            want = (DOG_UNITS, DOG_UNITS)
        elif k == "lock" and l.get("near_price"):
            want = (0.5, 0.5)
        elif k == "lock":
            want = (0.5, 0.5) if thin_edge(l) else (0.5, 10)
        elif k in ("solo", "night"):
            want = (0.5, 10) if not pk.get("lean") else (0, 0)
        if want and not want[0] <= u <= want[1]:
            out.append(f"sizing: {k} {l.get('team')} {l.get('odds')} at {u:g}u - the unit system says "
                       f"{want[0]:g}u" + (f"-{want[1]:g}u" if want[1] != want[0] else ""))
    return out


def checker_selftest():
    """🧪 THE CHECKER CHECKS ITSELF (the owner, 10/2: "make sure our checker is working properly"): before every
    opening board it feeds the factor check and the sizing check made-up broken data, one problem at a time, and makes
    sure each one gets caught. A check that misses its problem is reported (and holds the board like any other).
    Never touches a real pick or a real file."""
    from datetime import date as _date
    now = datetime(2026, 10, 2, 15, tzinfo=timezone.utc)
    d = _date(2026, 10, 2)
    keep = (dict(DOG_ST), dict(LAST_STARTS), list(STATE_FAILS), sp.CACHE, SLATE_PATH)
    import tempfile
    globals()["SLATE_PATH"] = os.path.join(tempfile.mkdtemp(), "selftest.json")
    missed = []
    try:
        DOG_ST.clear(); LAST_STARTS.clear(); del STATE_FAILS[:]
        DOG_ST[("nba", "1")] = {"won": True}; LAST_STARTS[("nba", "1")] = ["x"]
        sp.CACHE = {"mlb": [{"player": "x"}]}
        G = {f"t{i}": {"league": "nba", "status": "pre", "start": "2026-10-02T23:00Z", "home_name": f"T{i}",
                       "odds_time": "2026-10-02T14:30Z", "ml_home": "-120", "ml_home_open": "-120"} for i in range(3)}
        cs = [{"league": "nba", "game_id": f"t{i}", "market": "ml", "odds": -120} for i in range(3)]
        inj = {"nba": {"1": []}, "mlb": {"1": []}}
        M = {"params": {"nba": {"trust": 1}, "mlb": {"trust": 1}}}
        quiet = lambda *a, **k: None                                       # noqa: E731
        import builtins
        pr, builtins.print = builtins.print, quiet
        try:
            if factor_check(G, cs, inj, d, now, model=M):
                missed.append("it flagged good data")
            cases = {
                ("a stale price", "fresh price"): lambda g, c, i, m: [x.update(odds_time="2026-10-01T10:00Z") for x in g.values()],
                ("a missing final score", "final score"): lambda g, c, i, m: g.update({f"y{k}": {"league": "nba", "status": "pre",
                                                                     "start": "2026-10-02T01:00Z", "ml_home": "-120"} for k in range(3)}),
                ("a missing injury report", "injury report"): lambda g, c, i, m: i.pop("nba"),
                ("missing form data", "dog studies"): lambda g, c, i, m: DOG_ST.clear(),
                ("missing rest data", "back-to-back"): lambda g, c, i, m: LAST_STARTS.clear(),
                ("a data load failure", "failed to load"): lambda g, c, i, m: STATE_FAILS.append("coaches"),
                ("no opening line (line movement)", "opening lines"): lambda g, c, i, m: [x.pop("ml_home_open") for x in g.values()],
                ("a sport's model missing", "model for this sport"): lambda g, c, i, m: m["params"].pop("nba"),
                ("missing player stats", "player stats"): lambda g, c, i, m: (c.append({"league": "mlb", "game_id": "m1", "market": "ml",
                                                                      "odds": -110}), DOG_ST.update({("mlb", "1"): 1}),
                                                            sp.CACHE.clear()),
            }
            for (name, word), breakit in cases.items():
                g2, c2, i2, m2 = copy.deepcopy(G), copy.deepcopy(cs), copy.deepcopy(inj), copy.deepcopy(M)
                DOG_ST.clear(); DOG_ST[("nba", "1")] = {"won": True}
                LAST_STARTS.clear(); LAST_STARTS[("nba", "1")] = ["x"]; del STATE_FAILS[:]
                sp.CACHE = {"mlb": [{"player": "x"}]}
                breakit(g2, c2, i2, m2)
                if not any(word in x for x in factor_check(g2, c2, i2, d, now, model=m2)):
                    missed.append(f"it missed {name}")
            leg = {"league": "nba", "game_id": "s", "market": "ml", "odds": 120, "team": "X", "p": 0.5, "own_p": 0.5}
            bad = [{"date": "2026-10-02", "kind": "play", "status": "open", "units": 3, "legs": [leg]}]
            real_units = globals()["units_for"]
            globals()["units_for"] = lambda pk: pk.get("units", 0)
            try:
                if not sizing_check(bad):
                    missed.append("it missed a value play at 3u")
                bad[0].update(kind="lean", lean=True, units=1)
                if not sizing_check(bad):
                    missed.append("it missed a lean with units")
            finally:
                globals()["units_for"] = real_units
        finally:
            builtins.print = pr
    except Exception as e:                                   # noqa: BLE001 - the self-test breaking is itself a problem
        missed.append(f"the self-test crashed: {str(e)[:80]}")
    finally:
        DOG_ST.clear(); DOG_ST.update(keep[0]); LAST_STARTS.clear(); LAST_STARTS.update(keep[1])
        STATE_FAILS[:] = keep[2]; sp.CACHE = keep[3]; globals()["SLATE_PATH"] = keep[4]
    out = [f"the checker is broken: {m}" for m in missed]
    for x in out:
        print(f"CHECKER SELF-TEST: {x}", flush=True)
    if not out:
        print(f"CHECKER SELF-TEST: all {len(cases) + 3} checks caught their problem", flush=True)
    return out


def note_board_crash(iso, err, now, path=None):
    """The board builder crashed: say so in slate_check.json (the hourly bug check reads it) - never silently."""
    path = path or SLATE_PATH
    print(f"BOARD CRASHED for {iso}: {type(err).__name__}: {str(err)[:160]} - the rest of the run still saves", flush=True)
    try:
        cur = json.load(open(path)) if os.path.exists(path) else {}
    except (OSError, ValueError):
        cur = {}
    cur["crash"] = {"day": iso, "at": now.strftime("%Y-%m-%dT%H:%MZ"), "error": f"{type(err).__name__}: {str(err)[:160]}"}
    try:
        with open(path + ".tmp", "w") as f:
            json.dump(cur, f, indent=1)
        os.replace(path + ".tmp", path)
    except OSError:
        pass


def preflight(games, model, now):
    """The 7 AM PT run: the same slate check an hour before the board, so a problem gets caught (and the hourly bug
    check flags it) before 8."""
    day = now.astimezone(PT).date()
    try:
        return slate_check(games, candidates(games, model, now, day, {}), day, now, model=model)
    except Exception as e:                                   # noqa: BLE001 - the check itself breaking is a problem
        return [f"the slate check crashed: {str(e)[:80]}"]


def post_board(games, model, picks, now, day, force=False):
    """Post the day's plays. A play goes up as soon as none of its games is waiting on news (a starting
    pitcher, a questionable QB/goalie...); otherwise its card says what it's waiting on, and at the latest
    DEADLINE_MIN before its first game it is posted from settled games only. force posts everything now.
    A posted play is final. Returns the plays posted by this call."""
    iso = day.isoformat()
    local = now.astimezone(PT)
    if day != local.date() or local.hour < POST_FROM_HOUR_PT or iso in HOLD_DAYS:
        return []                    # game day only, from 8am PT - whoever calls (9/29: the quick grader posted the
    #                                  day's board at 12:21 AM when a game ended; the rule lives here now, for everyone)
    if not DOGS_ST:                  # no picks until the big underdog + favorite study has run
        print("holding the board: the big study hasn't run yet")
        return []
    pending = {p["kind"] for p in picks if p["status"] == "waiting" and p["date"] == iso}
    picks[:] = [p for p in picks if not (p["status"] == "waiting" and p["date"] <= iso)]   # rebuilt every run
    posted = {}
    for p in picks:                  # the latest play of each kind today (a graded one gets replaced below)
        if p["date"] == iso:
            posted[p["kind"]] = p
    first = first_start(games, day)
    started = first is not None and now >= first and not force and \
        any(p["date"] == iso and p["status"] != "waiting" for p in picks)   # (10/1 bug hunt: a 6:30 AM London NFL game
    #                                     or an 8:05 first pitch wiped out the whole opening board - Lock, Dog, leans)
    # the opening board goes up before the day's first game. After that, whenever a play is graded (it moves to the
    # results), a fresh one of the same kind goes up from the games that haven't started yet - picks all day long.
    todo = [k for k, _ in KINDS if (k not in posted and (not started or k in pending or k == "lock")) or   # (10/3, the
            #   owner: "if there's a Lock with games that haven't started yet, the 8 AM logic is irrelevant" - no Lock up
            #   yet = the engine keeps looking all day, games not started only; never forced. 10/1 bug check: a Lock
            (k in posted and posted[k]["status"] in ("won", "lost", "push"))]   # waiting on news vanished once the
    #                                                                             day's first game started)
    nights = night_games(games, day, picks, now)             # 🏈 Monday / Thursday football: a pick on every game
    full = all(sum(p["date"] == iso and p["kind"] == k and p["status"] != "waiting" for p in picks) >= cap
               for k, cap in (("play", MAX_PLAYS), ("lean", MAX_LEANS)))
    if not todo and not nights and full:
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
    raw_cands = candidates(games, model, now, day, injuries)   # (the checks read every side the engine looked at)
    global LAST_RAW
    LAST_RAW = raw_cands                                     # (the dry-run preview's every-dog list - 10/5)
    all_cands = [c for c in raw_cands                        # (10/2: a game we have no injury report for
                 if not any("(not in our data)" in w for w in c.get("waiting") or [])]   # is off the table - never a
    #                                                  blind pick, and never a Lock / Dog left 'waiting' on a report that
    #                                                  never comes (Cal @ UNLV: Cal doesn't publish for non-conference)
    cands = [c for c in all_cands if not c.get("hurt")]      # (10/2: a side missing players the engine doesn't weigh
    for c in all_cands:                                      #  never carries units - a lean at most)
        if c.get("hurt") and c.get("market") == "ml":
            print(f"   no units on {c['team']}: missing {', '.join(c['hurt'][:4])}")
    try:                                                     # 🧪 the lead tracker (for Claude, not the dashboard)
        import sports_leads
        sports_leads.log(iso, cands, sys.modules[__name__])
        sports_leads.grade(games)
    except Exception as e:                                   # noqa: BLE001 - the tracker never blocks the board
        print(f"lead tracker failed: {str(e)[:80]}")
    opening = not any(p["date"] == iso and p["status"] != "waiting" for p in picks)
    if opening and not force:                                # 🔎 the opening board: nothing missed, nothing broken
        gaps = data_gaps(games, all_cands, now)               # (10/2: the checks read every side we looked at -
        probs = slate_check(games, raw_cands, day, now, model=model) + factor_check(games, raw_cands, injuries, day, now, model) + \
            checker_selftest() + \
            [f"data gap - {x}" for x in gaps.values() if "no result" in x]   # (a re-pull fixes a missing result;
                                                                                 # a small school's gap just gets no pick)
        if probs and (local.hour, local.minute) < SLATE_LAST_TRY:
            print(f"holding the board: the slate check found {len(probs)} problem(s) - the engine re-pulls and tries "
                  f"again (last try 8:30 PT)")
            return []
    gaps = data_gaps(games, all_cands, now)                  # never a pick off half the picture (the owner, 10/1)
    if gaps:
        for x in gaps.values():
            print(f"DATA GAP (no pick on this game): {x}", flush=True)
        no_gap = lambda c: not any((c["league"], (games.get(c["game_id"]) or {}).get(s_)) in gaps   # noqa: E731
                                   for s_ in ("home", "away"))
        cands = [c for c in cands if no_gap(c)]
        all_cands = [c for c in all_cands if no_gap(c)]      # (10/2: the leans / backup Lock pool gets every filter too)
    ours = {}                                                # games we're already on today (any pick, graded or not):
    for p in picks:                                          # a new pick never takes the other team in them
        if p["date"] == iso and p["status"] != "waiting":
            for l in p["legs"]:
                ours.setdefault(l["game_id"], l["side"])
    try:                                                     # ⏰ ...or in a game we got in EARLY on (the owner, 9/30:
        import sports_early                                  # an early play can be a daily pick too - never against it)
        for gid, side in early_sides(sports_early.load().get("picks") or []).items():
            ours.setdefault(gid, side)
    except Exception as e:                                   # noqa: BLE001
        print(f"early plays (board side check) failed: {e}")
    cands = [c for c in cands if ours.get(c["game_id"], c["side"]) == c["side"]]
    all_cands = [c for c in all_cands if ours.get(c["game_id"], c["side"]) == c["side"]]
    settled = [c for c in cands if not c["waiting"]]
    elo = None
    used = {t for p in picks if p["date"] == iso for l in p["legs"] for t in l.get("bd_tags", [])}   # the board's memory
    used |= sports_breakdown.memory(picks, since=(day - timedelta(days=1)).isoformat())   # no phrase repeats on the
    #                                                     dashboard, and no 4-word run from today's or yesterday's write-ups
    new = []

    def dress(b):                                            # the posted legs: who's out, the write-up, the read
        nonlocal elo
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
                leg["why_line"] = same.get("why_line", "")
            else:
                leg["breakdown"] = sports_breakdown.breakdown(leg, games, elo, injuries, used)
            leg["public"] = sports_breakdown.public_side(leg, g)
            leg["bv"] = sports_breakdown.VERSION
            leg["key_seen"] = key_status(injuries.get(leg["league"]), g)       # who's in/out when we posted it
            line = injury_line(g, leg["side"], injuries)        # (10/2: a banged-up side on the board says who's out)
            if line and not any(str(x).startswith("🚑") for x in leg.get("breakdown") or []):
                leg["breakdown"] = [line] + list(leg.get("breakdown") or [])
            try:                                                # 🥅 hockey: who's CONFIRMED in net (never a guess)
                net = sports_goalies.card_line(g, leg["side"], sp.CACHE.get("nhl") or [])
            except Exception:                                   # noqa: BLE001
                net = ""
            if net and not any(str(x).startswith("🥅 In net") for x in leg.get("breakdown") or []):   # (10/6 sweep: the
                leg["breakdown"] = list(leg.get("breakdown") or []) + [net]   # slumping-goalie line starts with 🥅 too)
            print(f"   injuries seen for {leg['team']} vs {leg['opp']}: {leg['key_seen'] or 'no key players listed'}"
                  f" · ours out: {leg['outs'] or '-'} · theirs out: {leg['opp_outs'] or '-'}")

    # the owner: a day where NOTHING on the slate clears the value bar gets LEANS ONLY (own record, never ours) with a
    # note up top - we don't force picks just to have picks. Decided on the opening board, before anything's posted.
    lean_day = not any(p["date"] == iso and p["status"] != "waiting" for p in picks) and bool(cands) and \
        not any(make_board(all_cands).get(k) for k in ("lock", "dog", "solo")) and not plays(cands, ())
    if lean_day:
        print(f"{iso}: nothing clears the value bar - leans only today")
    for kind in todo:
        lock_game = posted["lock"]["legs"][0]["game_id"] if "lock" in posted and posted["lock"]["status"] == "open" else None
        replacing = kind in posted or lean_day                # the opening board is value only; replacements may lean
        if kind in ("dog", "lock") and replacing:
            continue                                          # never a lean / replacement Lock or Dog of the Day (the
            #                                                   owner, 10/1: "if it's a lean, it's just a lean") - the
            #                                                   leans fill the board to BOARD_TARGET instead
        if replacing and sum(p["date"] == iso and (p.get("round") or 1) > 1 for p in picks) >= MAX_REPLACEMENTS:
            continue                                          # enough for today - accuracy over volume
        avoid = {l["game_id"] for p in picks if p["date"] == iso and p["status"] != "waiting" and p["kind"] not in ("eight", "four")
                 for l in p["legs"]}
        fixed = {k: posted[k]["legs"] for k in ("lock", "dog", "two", "three")          # build on what's still up
                 if k in posted and posted[k].get("status") == "open" and posted[k].get("legs")}   # (never a graded one)
        best = make_board(cands, lock_game, allow_lean=replacing, avoid=avoid, fixed=fixed).get(kind)
        if not best and kind == "lock" and not replacing and FORCE_LOCK:   # (off since 10/2 - FORCE_LOCK) when
            best = make_board(all_cands, lock_game, avoid=avoid, fixed=fixed).get(kind) or last_lock(all_cands, avoid)   # every healthy side falls
            #                                                  short, the backup Lock can be a banged-up side - ½u,
            #                                                  its card names who's out (never a blind one)
        if replacing:                                         # a lean never repeats a game we're already on today
            if best and any(l["game_id"] in avoid for l in best["legs"]):
                best = None
            if not best and kind != "dog":                    # nothing clears the value bar: the likeliest LEAN instead
                best = lean([c for c in cands if c["game_id"] not in avoid], kind, taken=lock_game,   # (never a lean
                            floor=LEAN_DAY_MIN_P if lean_day and kind not in posted else None)        #  Dog - 10/1)
        if not best:
            continue
        deadline = min(_start(l) for l in best["legs"]) - timedelta(minutes=DEADLINE_MIN)
        if force or all(not l["waiting"] for l in best["legs"]):
            b = best
        elif now >= deadline:
            b = make_board(settled, lock_game, allow_lean=replacing, avoid=avoid, fixed=fixed).get(kind)   # out of time: settled
            if not b:
                continue
        else:
            wait = sorted({w for l in best["legs"] for w in l["waiting"]})
            picks.append({"date": iso, "kind": kind, "status": "waiting", "legs": [], "waiting": wait[:3],
                          "deadline": deadline.strftime("%Y-%m-%dT%H:%MZ")})
            continue
        dress(b)
        pk = {"date": iso, "kind": kind, "posted": now.strftime("%Y-%m-%dT%H:%MZ"),
              "round": sum(p["date"] == iso and p["kind"] == kind and p["status"] != "waiting" for p in picks) + 1,
              "legs": b["legs"], "dec": round(b["dec"], 4), "american": american(b["dec"]),
              "p_hit": round(b["p_hit"], 4), "stake": STAKE, "status": "open", "pnl": 0.0,
              "lean": bool(b.get("lean")) or replacing}     # a replacement (after a play's graded) is always a LEAN:
                                                            # the lock/value grades are the opening board's calls only
        for leg in pk["legs"]:
            leg["tier"] = "lean" if pk["lean"] else "lock" if kind == "lock" else leg_tier(leg)
            if pk["lean"]:                                    # no edge = no hype: an honest lean read
                leg["breakdown"] = sports_breakdown.lean_tone(leg.get("breakdown"), leg, f"{iso}{kind}")
        pk["tier"] = pick_tier({**pk, "tier": None})
        picks.append(pk)
        posted[kind] = pk
        new.append(pk)
    if "lock" in todo and not started and not any(p["date"] == iso and p["kind"] == "lock" and p["status"] != "waiting" for p in picks):
        try:                                                  # no Lock today: what it would have been, and why not
            miss = lock_miss(cands, all_cands)                # (the question box answers "what would the Lock have been")
            if miss:
                save_lock_miss(iso, miss)
        except Exception as e:                               # noqa: BLE001 - never blocks the board
            print(f"lock miss not saved: {str(e)[:80]}")
    # 💰 THE UNIT PLAYS, STRAIGHT (the owner, 10/1) - then 🟡 the viewer leans. Each its own pick, one per game, never a
    # game we're already on today; a play waiting on news (a starter, a QB) goes up on a later run once it's settled.
    for kind, pool, cap in (("play", plays, MAX_PLAYS), ("lean", viewer_leans, MAX_LEANS)):
        today_ = [p for p in picks if p["date"] == iso and p["status"] != "waiting"]
        room = cap - sum(p["kind"] == kind for p in today_)
        if kind == "lean":                                    # leans only fill the board up to BOARD_TARGET picks
            room = min(room, BOARD_TARGET - sum(p["kind"] in STRAIGHT_KINDS for p in today_))
        if kind == "lean" and started:
            room = 0                                          # (10/1: leans go up with the opening board only - the
        #                                                       record is the start-of-day board, never topped up later)
        used = {l["game_id"] for p in today_ for l in p["legs"]}
        for c in pool(all_cands if kind == "lean" else cands, used):
            if room <= 0:
                break
            if c["waiting"] and not force and not (kind == "lean" and not waiting_on(games[c["game_id"]], injuries, maybe=False)):
                continue                                     # (a lean waits only on a verified starter - 10/2)
            if c.get("fill") and fill_hurt(games[c["game_id"]], c["side"], injuries):   # (10/2, the owner: "a lock,
                print(f"   fill lean on {c['team']} - missing {', '.join(fill_hurt(games[c['game_id']], c['side'], injuries)[:3])}")
                #                                      a dog and three leans, no matter what" - it goes up, named)
            b = {"legs": [c], "dec": c["dec"], "p_hit": c["p"], "lean": kind == "lean"}
            dress(b)
            pk = {"date": iso, "kind": kind, "posted": now.strftime("%Y-%m-%dT%H:%MZ"), "round": 1, "legs": b["legs"],
                  "dec": round(b["dec"], 4), "american": american(b["dec"]), "p_hit": round(b["p_hit"], 4),
                  "stake": STAKE, "status": "open", "pnl": 0.0, "lean": kind == "lean"}
            if kind == "lean" and confident_lean(c):
                pk["lean_units"] = lean_units(c)
            leg = pk["legs"][0]
            leg["tier"] = "lean" if pk["lean"] else leg_tier(leg)
            if pk["lean"]:
                leg["breakdown"] = sports_breakdown.lean_tone(leg.get("breakdown"), leg, f"{iso}lean{c['game_id']}")
            pk["tier"] = pick_tier({**pk, "tier": None})
            picks.append(pk)
            new.append(pk)
            room -= 1
    for gid in nights:                                       # 🏈 the owner, 9/30: Monday and Thursday football ALWAYS
        if gid in _straight_games(picks, iso):               # get a pick - every game (two games = two picks); the
            continue                                         # engine's call, a lean is fine
        b = night_pick([c for c in all_cands if c["game_id"] == gid])   # (every NFL night game gets its pick - a
        #                                                  banged-up side can be its lean; night_pick sizes it)
        if not b:
            continue
        deadline = _start(b["legs"][0]) - timedelta(minutes=DEADLINE_MIN)
        if b["legs"][0]["waiting"] and now < deadline and not force:
            continue                                         # waiting on news (a QB...): the next run looks again
        dress(b)
        leg = b["legs"][0]
        pk = {"date": iso, "kind": "night", "posted": now.strftime("%Y-%m-%dT%H:%MZ"), "round": 1,
              "legs": b["legs"], "dec": round(b["dec"], 4), "american": american(b["dec"]), "p_hit": round(b["p_hit"], 4),
              "stake": STAKE, "status": "open", "pnl": 0.0, "lean": bool(b.get("lean"))}
        if pk["lean"] and confident_lean(leg):
            pk["lean_units"] = lean_units(leg)
        leg["tier"] = "lean" if pk["lean"] else leg_tier(leg)
        if pk["lean"]:
            leg["breakdown"] = sports_breakdown.lean_tone(leg.get("breakdown"), leg, f"{iso}night{gid}")
        pk["tier"] = pick_tier({**pk, "tier": None})
        picks.append(pk)
        new.append(pk)
    if not opening:                                          # 💰 a unit play added after the board went up (the owner,
        for pk in new:                                       # 10/1: the engine keeps checking the lines all day) - ONE
            if not pk.get("lean") and pk["kind"] in MIDDAY_KINDS:   # ping, once the dashboard shows it (sports_pings);
                pk["midday"] = True                          # leans never ping
    rule_check(picks, new, iso, games, day, now)
    return new


MIDDAY_KINDS = ("play", "lock", "dog", "solo", "night")      # the unit plays a mid-day ping can be for


NIGHT_DAYS = (0, 3)            # 🏈 Monday, Thursday (Pacific) - every NFL game those days gets a pick (the owner, 9/30)
STRAIGHT_KINDS = ("lock", "dog", "solo", "night", "play", "lean")


def _straight_games(picks, iso):
    """Games already carrying a straight pick today (the Lock, the Dog, a one-game pick, a night pick)."""
    return {l["game_id"] for p in picks if p["date"] == iso and p["kind"] in STRAIGHT_KINDS and p["status"] != "waiting"
            for l in p.get("legs") or []}


def early_sides(early):
    """{game id: side} of our OPEN early value plays - a daily pick never takes the other side of one (the owner, 9/30).
    The 🌍 Europe under (side "under") took no side, so it never locks a game: both teams stay open to the board
    (10/5 sweep: it read as a side, and every pick on the London game would have been dropped)."""
    return {e["game_id"]: e["side"] for e in early
            if e.get("result") is None and e.get("side") in ("home", "away") and e.get("game_id")}


def night_games(games, day, picks, now):
    """NFL games on a Monday / Thursday (Pacific) not started yet with no straight pick on them yet."""
    if day.weekday() not in NIGHT_DAYS:
        return []
    have = _straight_games(picks, day.isoformat())
    out = []
    for g in games.values():
        if g.get("league") != "nfl" or g.get("status") != "pre" or (g.get("stype") or "2") not in sd.REAL:
            continue
        t = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        if t.astimezone(PT).date() == day and t > now and g["id"] not in have:
            out.append(g["id"])
    return sorted(out, key=lambda k: games[k]["start"])


def night_pick(pool):
    """The engine's pick for one Monday / Thursday game: its best real play (value, likeliest first); none clears the
    bar - the likeliest side it isn't fighting, as a LEAN. Moneyline or spread, never past -150, never a trap."""
    pool = [c for c in pool if c["market"] in ("ml", "spread") and c["odds"] >= MAX_FAV and not c.get("trap")]
    real = [c for c in pool if good(c) and real_value(c) and leg_tier(c) in ("lock", "value") and not c.get("hurt")]   # (10/2 audit: a strong
    #   lean posted as a ½u unit play labeled LEAN) (10/1 bug hunt: the Steelers at -148 - 0.4 short of the
    if real:                                                 # price - went up labeled LOCK with 0 units)
        c = max(real, key=lambda c: (round(c["p"] * 50), c["edge"]))
        return {"legs": [c], "dec": c["dec"], "p_hit": c["p"]}
    pool = [c for c in pool if not fighting(c)] or pool
    if not pool:
        return None
    c = stick(max(pool, key=lambda c: (c["p"], c["edge"])), pool)   # 📌 (10/5: the Falcons -> Saints flip)
    return {"legs": [c], "dec": c["dec"], "p_hit": c["p"], "lean": True}


def key_status(inj, g, lineups=None):
    """{player: status} for every key player (QB / goalie / NBA rotation / a team's best bats) listed out or
    questionable in this game - and, once baseball's confirmed lineups are out, a star who isn't in his (9/29: the
    engine never knew Aaron Judge wasn't playing)."""
    out = {}
    for side in ("home", "away"):
        for n, pos, st in sd.team_key_out(inj, g[side], g[side + "_name"], g["league"]) + \
                sd.team_unsure(inj, g[side], g[side + "_name"], g["league"]):
            out[f"{n} ({g[side + '_name']}{' ' + pos if pos else ''})"] = st
        if g["league"] == "mlb" and lineups:
            lu = sd.lineup_for(lineups, g, side)
            listed = {k.split(" (")[0] for k in out}
            for n in (sd.team_stars(g[side + "_name"]) if lu else []):
                if n not in lu and n not in listed:
                    out[f"{n} ({g[side + '_name']})"] = "Not in the lineup"
    try:                                                     # 🥅 hockey: a CONFIRMED starter counts as a status too -
        out.update(sports_goalies.watch_status(g))           # confirmed after we posted = an alert on the card
    except Exception:                                        # noqa: BLE001 - unknown stays unknown
        pass
    return out


def goalie_role_words(g, who):
    """' — their #1, 9 of their last 10 starts' (or ' — not their usual #1...') for a confirmed goalie named the way
    key_status names him: 'Name (Team G)'. '' when our box scores can't say."""
    try:
        name, team = who.rsplit(" (", 1)
        side = next(s for s in ("home", "away") if f"{g[s + '_name']} G)" == team)
        n1 = sports_goalies.number_one(sp.CACHE.get("nhl") or [], g[side], g.get("start") or "9")
        return sports_goalies._role_words(name, n1)
    except Exception:                                        # noqa: BLE001 - no fact = no words
        return ""


NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "d503-live-7b1123")
DASH_URL = "https://d503therapper.github.io/autonomous-crypto-engine/sports/"


def _push(title, body, tag="ambulance"):
    """📲 A heads-up to phones: the dashboard's own 🔔 alerts (straight to our Worker) + the ntfy channel. Never blocks."""
    raw = None
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=body.encode(), method="POST", headers={
            "Title": title.encode("latin-1", "ignore").decode("latin-1"), "Tags": tag, "Click": DASH_URL,
            "Priority": "high"})
        raw = urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:                                   # noqa: BLE001
        print(f"   ntfy push failed: {str(e)[:60]}")
    return sd.web_push(raw, title, body)                     # 🔔 the dashboard's alerts - even if ntfy is down


LINE_ALERT = 0.03             # the money ran 3+ no-vig points away from our side since we posted it


def line_watch(games, picks):
    """After a pick is up, keep watching its line every run (the owner's rule: the engine watches the line all day).
    If the money runs away from our side (the Astros, 9/29: -143 at the open, -123 by first pitch - they lost), say
    it loud on the card: where it was, where it is. The pick itself never changes on its own - the owner decides."""
    out = []
    for p in picks:
        if p["status"] != "open":
            continue
        for leg in p["legs"]:
            g = games.get(leg["game_id"])
            if not g or g["status"] != "pre" or leg.get("market") != "ml" or leg.get("p_market") is None:
                continue
            now = sm.market_p(g)
            if now is None:
                continue
            now_side = now if leg["side"] == "home" else 1 - now
            odds_now = sm._int(g.get(f"ml_{leg['side']}"))
            if leg["p_market"] - now_side >= LINE_ALERT and odds_now is not None:
                msg = (f"The money's running away from {leg['team']}: {fmt_american(leg['odds'])} when we posted, "
                       f"{fmt_american(odds_now)} now. We still riding — your call.")
                if not any(a.startswith(f"The money's running away from {leg['team']}") for a in leg.get("line_alerts", [])):
                    leg.setdefault("line_alerts", []).append(msg)
                    out.append(msg)
                    print(f"💸 line alert: {msg}")
    return out


def injury_watch(games, picks, push=True):
    """After a pick is up, keep checking its game's injury report every run. If a key player's status changes (a
    questionable QB ruled out, a star goalie scratched...), push an alert and put it on the card. The pick itself
    never changes on its own - the owner decides."""
    legs = [l for p in picks if p["status"] == "open" for l in p["legs"]
            if l["game_id"] in games and games[l["game_id"]]["status"] == "pre" and l["league"] in sd.INJ_LEAGUES]
    if not legs:
        return []
    injuries = {lg: sd.fetch_injuries(lg) for lg in {l["league"] for l in legs}}
    days = {games[l["game_id"]]["start"][:10] for l in legs if l["league"] == "mlb"}
    lineups = {}                                             # baseball's confirmed lineups (hours before first pitch)
    for d in days:
        lineups.update(sd.mlb_lineups(d))
    alerts = []
    for leg in legs:
        inj = injuries.get(leg["league"])
        if inj is None:
            continue                                         # no report this run: check again next run
        now_ = key_status(inj, games[leg["game_id"]], lineups)
        if "key_seen" not in leg:                            # posted before the watch existed: start from here
            leg["key_seen"] = now_
            continue
        for who, st in now_.items():
            if leg["key_seen"].get(who) != st:
                msg = f"{who} is now {st.lower()} — our pick: {leg_label(leg)}"
                if st == "Confirmed in net":                 # 🥅 a goalie confirmed after we posted: his role too
                    msg = f"{who} is now confirmed in net{goalie_role_words(games[leg['game_id']], who)} — our pick: {leg_label(leg)}"
                if msg not in leg.setdefault("injury_alerts", []):
                    leg["injury_alerts"].append(msg)
                    alerts.append(msg)
                    if push:
                        pass   # (on the card; no phone alert - the only alerts are live plus money bets)
        for who in set(leg["key_seen"]) - set(now_):
            if leg["key_seen"].get(who) == "Confirmed in net":
                continue                                     # (the page went stale / changed its mind: unknown again is
            #                                                  never "off the injury report"; a new starter gets his own line)
            msg = f"{who} is off the injury report — our pick: {leg_label(leg)}"
            if msg not in leg.setdefault("injury_alerts", []):
                leg["injury_alerts"].append(msg)
                alerts.append(msg)
                if push:
                    pass   # (on the card; no phone alert)
        leg["key_seen"] = now_
    for a in alerts:
        print(f"🚑 injury alert: {a}")
    return alerts


def _same_leg(a, b):
    return (a["game_id"], a["side"], a["market"], a.get("line")) == (b["game_id"], b["side"], b["market"], b.get("line"))


def add_breakdowns(games, model, picks):
    """(Re)write the breakdown of posted plays whose games haven't started, when it's missing or was written by an
    older breakdown version. Only the explanation changes - the pick itself never does."""
    legs = [l for p in picks if p["status"] == "open" for l in p["legs"]
            if l.get("bv") != sports_breakdown.VERSION and l["game_id"] in games and games[l["game_id"]]["status"] == "pre"]
    if not legs:
        return
    leans = {id(l): f"{p['date']}{p['kind']}{l['game_id']}" for p in picks if p["status"] == "open" and p.get("lean")
             for l in p["legs"]}             # (10/1, the owner - the Kraken lean: a rewrite kept a lean in its lean voice;
    #                                          it came back with a unit play's "not at this price" bottom line)
    injuries = {lg: sd.fetch_injuries(lg) for lg in {l["league"] for l in legs}}
    redo = {id(l) for l in legs}
    used = {t for p in picks for l in p["legs"] if id(l) not in redo for t in l.get("bd_tags", [])}
    used |= sports_breakdown.memory(picks, skip={(l.get("game_id"), l.get("side"), l.get("market")) for l in legs})
    elo, done = sm.ratings(games, model), []
    for leg in legs:
        same = next((l for l in done if _same_leg(l, leg)), None)
        if same:                                      # the same pick reads the same everywhere it shows up
            leg["breakdown"], leg["bd_tags"], leg["reasons"] = same["breakdown"], same.get("bd_tags", []), same.get("reasons", leg.get("reasons"))
            leg["why_line"] = same.get("why_line", "")
        else:
            leg["breakdown"] = sports_breakdown.breakdown(leg, games, elo, injuries, used)
            if id(leg) in leans:
                leg["breakdown"] = sports_breakdown.lean_tone(leg["breakdown"], leg, leans[id(leg)])
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


ASK_STEEP = -300              # "ask the engine": never suggest a moneyline shorter than this - use the spread
ASK_PATH = "docs/sports/reads.json"
SEASON = {"1": "preseason", "2": "regular season", "3": "playoffs"}   # ESPN's season type - the question box says it
#                                                    from THIS, never guesses from records (9/29: 0-0-0 on opening night
#                                                    read as 'preseason')


def engine_reads(games, model, picks, now=None):
    """ASK THE ENGINE: our read on every game today (and tomorrow, once the evening board is up) that isn't on our
    board. People can still get a lean on any game - but it's NOT a pick and never counts toward our results."""
    now = now or datetime.now(timezone.utc)
    ours = {l["game_id"]: pk["kind"] for pk in picks if pk.get("status") in ("open", "waiting") for l in pk.get("legs") or []}
    local = now.astimezone(PT).date()
    out = []
    try:
        import sports_halves
        import sports_lines
        halves, lines_st = sports_halves.load(), sports_lines.load()
    except Exception:                                                  # noqa: BLE001
        halves, lines_st = {}, {}
    for day in (local, local + timedelta(days=1)):
        by_game = {}
        for c in candidates(games, model, now, day):
            by_game.setdefault(c["game_id"], []).append(c)
        for gid, cs in by_game.items():
            g = games[gid]
            if g["league"] in ("nhl", "mlb") and g.get("spread_home", "") != "" and lines_st \
                    and not any(c["market"] == "spread" for c in cs):          # puck line / run line (if not in already)
                ph_ = next((c["p"] for c in cs if c["market"] == "ml" and c["side"] == "home"), None)
                for c in [c for c in cs if c["market"] == "ml"]:
                    line = float(g["spread_home"]) * (1 if c["side"] == "home" else -1)
                    odds = sm._int(g.get(f"spread_{c['side']}_odds"))
                    pc = sports_lines.cover(lines_st, g["league"], ph_, c["side"], line) if ph_ is not None else None
                    if pc is not None and odds:
                        cs.append({**c, "market": "spread", "line": line, "odds": odds, "dec": sd.decimal(odds),
                                   "p": pc, "edge": pc * sd.decimal(odds) - 1})
            ok = [c for c in cs if (c["market"] == "spread" or c["odds"] >= ASK_STEEP) and c["odds"] >= ASK_STEEP]
            lean_ = max(ok or cs, key=lambda c: (c["p"], c["edge"]))          # accuracy first: the likelier side
            ml_p = {c["side"]: c["p"] for c in cs if c["market"] == "ml"}
            if gid in ours:
                why = "on_board"
            elif lean_["market"] == "ml" and lean_["odds"] < ASK_STEEP:
                why = "steep"
            elif lean_["p"] < 0.55:
                why = "coin_flip"
            elif good(lean_):
                why = "tight"
            else:
                why = "no_value"
            h1 = None
            hv = halves.get(g["league"]) or {}
            if "share_1h" in hv and "home" in ml_p:            # who leads at the half (first 5 innings in baseball)
                import sports_comeback as sc
                mu1 = hv["share_1h"] * sc.SIGMA[g["league"]] * sc.phi_inv(ml_p["home"])
                lead_h = sc.phi((mu1 - 0.5) / hv["sd_1h"])
                lead_a = sc.phi((-mu1 - 0.5) / hv["sd_1h"])
                home_ = lead_h >= lead_a
                h1 = {"team": g["home_name"] if home_ else g["away_name"], "p": round(max(lead_h, lead_a), 3),
                      "tie": round(max(0.0, 1 - lead_h - lead_a), 3), "name": sports_halves.NAME.get(g["league"], "1st half")}
            out.append({"id": gid, "league": g["league"], "emoji": sd.LEAGUES[g["league"]][3], "h1": h1,
                        "sport": sd.LEAGUES[g["league"]][2], "season": SEASON.get(str(g.get("stype") or ""), "regular season"), "start": g["start"],
                        "away": g["away_name"], "home": g["home_name"], "why": why, "board": ours.get(gid),
                        "lean": {"team": lean_["team"], "opp": lean_["opp"], "market": lean_["market"],
                                 "line": lean_["line"], "odds": lean_["odds"], "p": round(lean_["p"], 3),
                                 "win_p": round(ml_p.get(lean_["side"], lean_["p"]), 3),
                                 "reasons": (lean_.get("reasons") or [])[:3]}})
    # games already going (or on our board) still get an answer: our side if we're on it, else "already kicked off"
    have = {r["id"] for r in out}
    legs = {l["game_id"]: (pk, l) for pk in picks if pk.get("date") == local.isoformat() and pk.get("status") != "waiting"
            for l in pk.get("legs") or []}
    for gid, g in games.items():
        if gid in have or g.get("league") not in sd.LEAGUES or not g.get("start"):
            continue
        st = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        if st.astimezone(PT).date() != local or (g.get("status") == "pre" and gid not in legs):
            continue
        pk, l = legs.get(gid, (None, None))
        out.append({"id": gid, "league": g["league"], "emoji": sd.LEAGUES[g["league"]][3], "sport": sd.LEAGUES[g["league"]][2], "season": SEASON.get(str(g.get("stype") or ""), "regular season"),
                    "start": g["start"], "away": g["away_name"], "home": g["home_name"], "h1": None,
                    "why": "on_board" if l else ("final" if g.get("status") == "final" else "started"),
                    "done": g.get("status") == "final",
                    "board": pk["kind"] if pk else None,
                    "lean": {"team": l["team"], "opp": l["opp"], "market": l["market"], "line": l.get("line"), "odds": l["odds"],
                             "p": round(l.get("p") or 0, 3), "win_p": round(l.get("p") or 0, 3), "reasons": (l.get("reasons") or [])[:3],
                             "result": l.get("result")}
                    if l else None})
    out.sort(key=lambda r: (r["start"], r["away"]))
    os.makedirs(os.path.dirname(ASK_PATH), exist_ok=True)
    with open(ASK_PATH, "w") as f:
        json.dump({"updated": now.strftime("%Y-%m-%dT%H:%MZ"), "games": out}, f, indent=1)
    return out


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
    deciders(picks, budget_s=12)                             # (the live watcher calls this: keep it quick)
    sp.CACHE = sp.load()
    sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)
    load_states(games)                                       # 🔥 every input the engine weighs, each on its own
    add_breakdowns(games, model, picks)
    had = {p["kind"] for p in picks if p["date"] == day.isoformat()}
    posted = post_board(games, model, picks, now, day)          # replaces any graded play (this pass or earlier)
    for pk in posted:
        print(f"posted {pk['kind']} (replacement) for {day}")
        if had:
            announce_pick(pk)                                   # added after the board was up: everybody gets a ping
    sd.save_games(games)
    _save("picks.json", picks)
    import sports_dashboard
    try:
        engine_reads(games, model, picks)
    except Exception as e:                                             # noqa: BLE001 - never block the dashboard
        print(f"engine reads failed: {e}")
    sports_dashboard.write(picks, model, games, bankroll_series(picks), START_BANKROLL)
    return graded, posted


def dedupe_picks(picks):
    """9/30: two engine runs at once both posted the Dog of the Day (the saves merged) - it would count twice. The same
    day + kind + round + legs is one pick: the first one posted stays."""
    seen, out = set(), []
    for p in picks:
        k = (p.get("date"), p.get("kind"), p.get("round") or 1,
             tuple((l.get("game_id"), l.get("side"), l.get("market"), l.get("line")) for l in p.get("legs") or []))
        if p.get("legs") and k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out


def run(repick=False, fetch=True):
    now = datetime.now(timezone.utc)
    state = _load("state.json", {})
    model = _load("model.json", {"params": {}, "log": []})
    picks = dedupe_picks(_load("picks.json", []))
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
        # (every player, every sport: its own GitHub job - .github/workflows/rosters.yml)
        t0 = time.time()
        filled, venues = sports_weather.sync(games)
        print(f"weather: {filled} games got weather, {venues} new stadiums located, {time.time() - t0:.0f}s")
        try:
            import sports_go4
            print(f"4th-down rates: {len(sports_go4.refresh().get('teams') or {})} NFL teams")
        except Exception as e:                           # noqa: BLE001 - never blocks the board
            print(f"4th-down rates failed: {str(e)[:60]}")
        print(f"news: {sports_news.sync()} new drama tags")
        try:                                             # 🥅 tonight's confirmed / likely starting goalies (Daily
            sports_goalies.sync(games, now)              # Faceoff, a public page) - fails soft: unknown = no weight
        except Exception as e:                           # noqa: BLE001 - never blocks the board
            print(f"goalies failed: {str(e)[:60]}")
    else:
        games = sd.load_games()
    sp.CACHE = sp.load()
    sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)
    load_states(games)                                       # 🔥 every input the engine weighs, each on its own
    n_players = sum(len(rows) for rows in sp.CACHE.values())
    for pk in grade(picks, games, now):
        print(f"settled {pk['date']} {pk['kind']}: {pk['status']} {pk['pnl']:+.2f}")
    try:                                                     # 🔎 the daily pick audit (the owner, 10/2): did every
        import sports_audit                                  # graded pick use the right data and the right size?
        d0 = now.astimezone(PT).date()
        sports_audit.run(picks, games, [(d0 - timedelta(days=k)).isoformat() for k in (2, 1, 0)])
    except Exception as e:                                   # noqa: BLE001 - the audit never blocks the board
        print(f"pick audit failed: {str(e)[:80]}")
    try:                                                     # 📈📓 beat the close + the pick journal (the owner, 10/2:
        import sports_clv                                    # "a record of everything ... every week we go back")
        sports_clv.run(picks, games)
    except Exception as e:                                   # noqa: BLE001 - the record never blocks the board
        print(f"close record failed: {str(e)[:80]}")
    if fetch:
        try:                                                 # 🎓 the capper benchmark (the owner, 10/2): Dr. Bob's free
            import sports_capper                             # NFL leans logged + graded next to ours - never copied
            sports_capper.run(games, picks, now)
        except Exception as e:                               # noqa: BLE001 - never blocks the board
            print(f"capper record failed: {str(e)[:80]}")
        try:                                                 # 🏆 today's futures prices, once a day (the owner, 10/3) -
            import sports_futures                            # our own price history for the futures study
            sports_futures.run(now)
        except Exception as e:                               # noqa: BLE001 - never blocks the board
            print(f"futures log failed: {str(e)[:80]}")
        try:                                                 # 🔒 the question box out of API credit? (the owner, 10/5:
            import sports_dashboard                          # "when it's gone, that's it") - the page drops the box
            sports_dashboard.refresh_ask_status()
        except Exception as e:                               # noqa: BLE001 - never blocks the board
            print(f"question box status failed: {str(e)[:80]}")
        try:                                                 # 🌍 the Europe morning NFL under - tracked, no units
            import sports_intl                               # (the owner, 10/4: "track it and see")
            sports_intl.run(games, now)
        except Exception as e:                               # noqa: BLE001 - never blocks the board
            print(f"intl under log failed: {str(e)[:80]}")
    if fetch:
        deciders(picks)
    day = now.astimezone(PT).date()
    if now.astimezone(PT).hour == 7:                         # 🔎 an hour before the board: the slate check
        preflight(games, model, now)
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
    if n_ls != model.get("ls_seen") or not DOGS_ST:                                    # the comeback + halves studies learn on new games
        try:
            import sports_comeback as sc
            print(sc.summary(sc.study(games)))
            import sports_halves
            print(sports_halves.summary(sports_halves.study(games)))
            import sports_lines
            print(sports_lines.summary(sports_lines.study(games)))
            import sports_ats as _ats                                   # moneyline vs spread: who covers
            print("spread/moneyline study:", {k: (v.get("hit"), v.get("proven")) for k, v in _ats.study(games).items()})
            import sports_hockey                                        # hockey: the line + only what beats it
            hk = sports_hockey.study(games)
            print("hockey study:", hk.get("kept"), hk.get("ll_kept"), "vs line", hk.get("ll_market"))
            TRENDS_ST.clear()                                           # in-season trends + whether history says ride them
            TRENDS_ST.update(sports_trends.study(games))
            print("\n".join(sports_trends.summary(TRENDS_ST, top=8)))
            import sports_totals                                        # over/unders: only once they beat the book
            print("totals study:", {k: (v.get("hit_top"), v.get("proven")) for k, v in sports_totals.study(games).items()})
            model["ls_seen"] = n_ls
        except Exception as e:                                          # noqa: BLE001 - never block the board
            print(f"comeback study failed: {e}")
    if repick:
        picks[:] = [p for p in picks if p["date"] != day.isoformat() or p["status"] not in ("open", "waiting")]
    picks[:] = [p for p in picks if not (p["status"] == "waiting" and p["date"] < day.isoformat())]
    local = datetime.now(timezone.utc).astimezone(PT)        # ⏰ ON TIME (10/2, the owner's friend: "the board doesn't
    if (local.hour == POST_FROM_HOUR_PT - 1 and local.minute >= BOARD_EARLY_MIN and local.date() == day  # usually go up
            and not any(p["date"] == day.isoformat() and p["status"] != "waiting" for p in picks)):   # till 9"): the
        wait = (local.replace(hour=POST_FROM_HOUR_PT, minute=0, second=5, microsecond=0) - local).total_seconds()
        print(f"everything's pulled and checked - the board goes up at 8:00 sharp (waiting {wait:.0f}s)", flush=True)
        time.sleep(max(0.0, wait))                           # 7:45 run does the pulling, then posts right at 8:00
        now = datetime.now(timezone.utc)
    days = [day] if now.astimezone(PT).hour >= POST_FROM_HOUR_PT else []      # game day only, from 8am PT
    days = [d for d in days if d.isoformat() not in HOLD_DAYS]         # a board on hold never posts (owner's call)
    try:                                                                # 📊 who's betting who on today's games
        import sports_public
        n_pub = len(sports_public.refresh_today(games))
        print(f"public splits: {n_pub} upcoming games")
    except Exception as e:                                              # noqa: BLE001
        print(f"public splits failed: {e}")
    add_breakdowns(games, model, picks)
    n_graded = sum(1 for p in picks for l in p["legs"] if l.get("result") in ("won", "lost"))
    if n_graded != model.get("graded_seen"):                            # 🪞 the self-check: every graded pick (and the
        try:                                                            # live plus money) vs the chance we said
            SELF_ST.clear()
            SELF_ST.update(sports_selfcheck.study())
            print("\n".join(sports_selfcheck.summary(SELF_ST)))
            model["graded_seen"] = n_graded
        except Exception as e:                                          # noqa: BLE001
            print(f"self-check failed: {e}")
    try:
        injury_watch(games, picks)                                      # 🚑 posted picks: did anybody's status change?
    except Exception as e:                                              # noqa: BLE001
        print(f"injury watch failed: {e}")
    try:
        line_watch(games, picks)                                        # 💸 ...or is the money running away from us?
    except Exception as e:                                              # noqa: BLE001
        print(f"line watch failed: {e}")
    try:                                                                # 📈 every line, every run (line_history):
        sd.record_lines(games, now)                                     # the midweek price, kept for the early exam
    except Exception as e:                                              # noqa: BLE001
        print(f"line history failed: {e}")
    try:                                                                # ⏰ early value plays: posted the second the
        import sports_early                                             # engine finds one, before the line moves
        inj = {lg: sd.fetch_injuries(lg) for lg in set(sports_early.passed()) | {"nfl", "ncaaf"}} \
            if sports_early.ON else None                 # (10/1 audit: the spots are football - with injuries only
        #                                                  for the exam's leagues, a dog whose QB is out could post)
        queue = []                                                      # (pinged only once the dashboard shows them:
        for c in sports_early.post(games, model, now, inj, ping=queue.append if sports_early.PINGS else None,
                                   trap=lambda lg, o, h: sports_dogs.verdict(DOGS_ST, lg, o, h) == "trap"):
            print(f"early value play: {c['team']} +{c['odds']} ({c['league']}, own {c['own']:.0%} vs price {c['mkt']:.0%})")
        sports_early.queue_pings(queue, now)
    except Exception as e:                                              # noqa: BLE001 - never blocks the board
        print(f"early value plays failed: {e}")
    for d in days:
        had = {p["kind"] for p in picks if p["date"] == d.isoformat()}
        try:
            new = post_board(games, model, picks, now, d, force=post_now and d == day)
        except Exception as e:                                          # noqa: BLE001 - (10/3 sweep) a crash in the board
            import traceback                                            # builder never loses the hour's grades, saves,
            traceback.print_exc()                                       # tennis slate and dashboard: it's logged loudly,
            new = []                                                    # written where the bug check reads it (and flags
            note_board_crash(d.isoformat(), e, now)                     # it), and the next run tries again
        for pk in new:
            if had:
                announce_pick(pk)                                # added after the board was up: everybody gets a ping
            legs = " + ".join(f"{leg_label(l)} ({fmt_american(l['odds'])})" for l in pk["legs"])
            print(f"posted {pk['kind']} for {d}: {legs} -> {fmt_american(pk['american'])}, hit {pk['p_hit']:.0%}")
    try:                                                                # 💰 mid-day value plays: one ping each, sent
        import sports_pings                                             # once the dashboard shows it (tools/early_ping)
        for q in sports_pings.queue(picks, now):
            print(f"mid-day value play ping queued: {q['title']}")
    except Exception as e:                                              # noqa: BLE001 - never blocks the board
        print(f"mid-day pings failed: {e}")
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
    try:
        engine_reads(games, model, picks)
    except Exception as e:                                             # noqa: BLE001 - never block the dashboard
        print(f"engine reads failed: {e}")
    sports_dashboard.write(picks, model, games, bankroll_series(picks), START_BANKROLL)
    return picks


if __name__ == "__main__":
    run(repick="--repick" in sys.argv, fetch="--offline" not in sys.argv)
