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
KINDS = [("lock", "Lock of the Day"), ("dog", "Dog of the Day"), ("two", "2-Leg of the Day"),   # posted in this order:
         ("three", "3-Leg of the Day"), ("four", "4-Leg of the Day"),
         ("solo", "Pick of the Day")]                                    # (one-game days only)    # (the 8-leg retired 2026-09-28: the 4-leg took its spot)
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


import sports_lines  # noqa: E402

LINES_ST = sports_lines.load()               # the puck line / run line study (how often teams really win by 2+)
import sports_totals  # noqa: E402
import sports_ats  # noqa: E402

import sports_dogs  # noqa: E402

DOGS_ST = sports_dogs.load()                 # the big underdog + favorite study (price check + dog spots/traps)
ATS_ST = sports_ats.load()                   # the spread-vs-moneyline study (who covers when the two disagree)

TOTALS_ST = sports_totals.load()             # the over/under study: a sport only gets over/unders once it's PROVEN
OU_STRONG = 0.58                             # ...and then only a game with a strong read (58%+ over or under)
_TOT_STATE = {}


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
        # the big study's price check: in a sport where favorites/dogs really win more/less than their price says
        # (proven on games it never saw), every read is shifted by it
        ph, ph_own = sports_dogs.adjust(DOGS_ST, lg, ph), sports_dogs.adjust(DOGS_ST, lg, ph_own)
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
            trap = odds > 0 and sports_dogs.verdict(DOGS_ST, lg, odds, side == "home") == "trap"
            out.append({**base, "market": "ml", "line": None, "odds": odds, "dec": sd.decimal(odds), "p": p, "trap": trap,
                        "p_market": mkt if side == "home" else 1 - mkt, "edge": p * sd.decimal(odds) - 1,
                        "edge_own": p_own * sd.decimal(odds) - 1})
            if lg in ("nhl", "mlb") and g.get("spread_home", "") != "" and LINES_ST:   # puck line / run line: the chance
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
                if po is not None and max(po, 1 - po) >= OU_STRONG:   # only a strong, lock-level read ever makes it
                    for ou, pp in (("over", po), ("under", 1 - po)):
                        oo = sm._int(g.get(f"{ou}_odds")) or -110
                        out.append({**base, "side": ou, "team": ou.capitalize(), "opp": f"{g['away_name']} @ {g['home_name']}",
                                    "market": "total", "line": float(g["total"]), "odds": oo, "dec": sd.decimal(oo), "p": pp,
                                    "p_market": 1 / sd.decimal(oo), "edge": pp * sd.decimal(oo) - 1,
                                    "reasons": ["the engine's scoring read"]})
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
                if pc is not None:
                    out.append({**base, "market": "spread", "line": line, "odds": sodds, "dec": sd.decimal(sodds),
                                "p": pc, "p_market": 1 / sd.decimal(sodds), "edge": pc * sd.decimal(sodds) - 1})
    return out


INTL_MIN_EDGE = 0.02           # overseas games are weird: they need twice the usual value


def good(c):
    """A real play: value on our numbers - from the engine's own read, not just the line moving - and at least one
    reason. Anything else is filler, and filler never goes up."""
    need = INTL_MIN_EDGE if c.get("intl") or c.get("our_drama") else MIN_EDGE   # overseas / our own drama: 2x value
    if c.get("trap"):                  # a dog in a spot the big study proved the books still overprice: never
        return False
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


def one_side(cands):
    """One side per game - never both teams. Value wins, unless the other side is a lock or a strong lean."""
    side, ou = {}, {}
    def rank(c):                     # value first - a popular favorite with no value never blocks the other side;
        g_ = good(c)                 # among real value plays: a lock / strong lean first; otherwise the bigger edge
        return (g_, g_ and leg_tier(c) == "lock", g_ and c["p"] >= STRONG_LEAN_P, c["edge"])
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
    if len({c["game_id"] for c in cands}) == 1:              # a one-game day: one PICK OF THE DAY, no Lock/Dog/parlays
        solo = max((c for c in cands if good(c) and c["odds"] >= MAX_FAV), key=lambda c: (round(c["p"] * 50), c["edge"]),
                   default=None)
        if solo is None:                                      # the owner wants a pick on a one-game day: the best REAL
            solo = max((c for c in cands if c["edge"] > 0 and c.get("edge_own", c["edge"]) > 0 and c["odds"] >= MAX_FAV),
                       key=lambda c: c["edge"], default=None)  # edge (positive, even if thin)
        if solo is None:                                      # still nothing: a one-game day (Monday/Thursday night) ALWAYS
            solo = max((c for c in cands if c["odds"] >= MAX_FAV), key=lambda c: c["edge"], default=None)   # gets a pick:
                                                              # the side closest to value on our numbers
        return {"lock": None, "dog": None, "two": None, "three": None, "four": None,
                "solo": fixed.get("solo") and _combo(fixed["solo"]) or (_combo([solo]) if solo else None)}
    # every leg is a real value play: the likeliest first (accuracy always comes first); when two are about as likely
    # (within 2%), the one with the most value
    good_ = sorted((c for c in cands if good(c) and c["odds"] >= MAX_FAV),        # accuracy first, then the most value
                   key=lambda c: (-round(c["p"] * 50), -c["edge"]))
    board = {}
    if fixed.get("lock"):
        lock = fixed["lock"][0]
    else:
        ml_ = [c for c in cands if c["market"] == "ml" and good(c)]
        locks = [c for c in ml_ if LOCK_MAX_FAV <= c["odds"] <= -100 or c["odds"] == 100]   # -101..-120 or a pick'em
        if not locks:                                         # nothing there: go up to -150
            locks = [c for c in ml_ if MAX_FAV <= c["odds"] < LOCK_MAX_FAV]
        lock = max(locks, key=lambda c: (c["p"], c["edge"])) if locks else None
    board["lock"] = _combo([lock]) if lock else None
    if fixed.get("dog"):
        dog = fixed["dog"][0]
    else:
        taken = {lock["game_id"]} if lock else set()
        taken |= {l["game_id"] for k in ("two", "three") for l in fixed.get(k) or []}
        dogs = [c for c in cands if c["market"] == "ml" and good(c) and c["odds"] >= DOG_MIN and c["game_id"] not in taken]
        regular = [c for c in dogs if c["odds"] < BIG_DOG]
        dog = max(regular, key=lambda c: c["edge"]) if regular else None
        big = [c for c in dogs if c["odds"] >= BIG_DOG and c["p"] >= BIG_DOG_MIN_P
               and c["edge"] >= (dog["edge"] if dog else 0) + BIG_DOG_EXTRA_EDGE]
        if big:
            dog = max(big, key=lambda c: c["edge"])
    board["dog"] = _combo([dog]) if dog else None

    def ladder(start, n):
        legs = list(start)
        for c in good_:
            if len(legs) >= n:
                break
            if c["game_id"] not in {l["game_id"] for l in legs} and \
                    (not dog or c["game_id"] != dog["game_id"] or dog["p"] >= DOG_IN_PARLAY_P):
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
STRONG_LEAN_P = 0.60                          # 60%+ to win/cover = a strong lean: it beats a value play on the other side


def leg_tier(c):
    """lock / value / lean for one leg, from the engine's numbers."""
    if not good(c):
        return "lean"
    if c.get("market") == "total":
        return "ou"                                          # over/unders: no lock/value label - their own thing
    return "value" if c["odds"] > 0 else "lock"          # owner's rule: minus money = LOCK, plus money = VALUE (favorites
                                                         # hit more, so the lock record stays the surest); no value = LEAN


def pick_tier(pk):
    """A play is only as confident as its weakest leg (older picks get it from their legs' numbers)."""
    if pk.get("lean"):
        return "lean"
    if pk.get("kind") == "lock":                              # the Lock of the Day is a LOCK - its results count as locks
        return "lock"
    if pk.get("tier"):
        return pk["tier"]
    # only a real lean play is a LEAN; a parlay's filler leg can't drag the whole card down to one
    tiers = [l.get("tier") or leg_tier({**l, "edge_own": l.get("edge_own", l.get("edge", 0))}) for l in pk.get("legs") or []]
    if tiers == ["ou"]:
        return "ou"
    return "lock" if tiers and all(t == "lock" for t in tiers) else "value"


LEAN_MIN_P = {"two": 0.58, "three": 0.58, "lock": 0.62, "dog": 0.42}   # ACCURACY FIRST: a lean is a side we expect to win
MAX_REPLACEMENTS = 0          # no afternoon replacements: our record is the start-of-day board, the engine's most
                              # confident calls. People who want more use ASK THE ENGINE (never counts toward the record)


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
        for c in sorted((c for c in cands if c["odds"] >= MAX_FAV and c["p"] >= LEAN_MIN_P[kind]), key=lambda c: -c["p"]):
            best.setdefault(c["game_id"], c)
        legs = sorted(best.values(), key=lambda c: -c["p"])[:n]          # the likeliest, not the longest
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
    c = max(pool, key=lambda c: (c["p"], c["edge"]))                  # accuracy first: the likeliest winner
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
    if leg["market"] == "total":                              # over/under: total points vs the line
        d = (hs + as_ - leg["line"]) * (1 if leg["side"] == "over" else -1)
        return "won" if d > 0 else "lost" if d < 0 else "push"
    margin = (hs - as_) if leg["side"] == "home" else (as_ - hs)
    if leg["market"] == "spread":
        margin += leg["line"]
    return "won" if margin > 0 else "lost" if margin < 0 else "push"


def grade(picks, games, now=None):
    now = now or datetime.now(timezone.utc)
    settled = []
    for pk in picks:
        if pk["status"] == "lost" and any(leg.get("result") is None for leg in pk["legs"]):
            for leg in pk["legs"]:                           # a busted parlay's other legs still get graded (show every
                if leg.get("result") is None:                # hit and miss - full transparency)
                    leg["result"] = grade_leg(leg, games.get(leg["game_id"]), now)
                    g = games.get(leg["game_id"])
                    if leg["result"] and g:
                        leg["score"] = f'{g["away_name"]} {g["away_score"]} @ {g["home_name"]} {g["home_score"]}'
            continue
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
    if not DOGS_ST:                  # no picks until the big underdog + favorite study has run
        print("holding the board: the big study hasn't run yet")
        return []
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
    ours = {}                                                # games we're already on today (any pick, graded or not):
    for p in picks:                                          # a new pick never takes the other team in them
        if p["date"] == iso and p["status"] != "waiting":
            for l in p["legs"]:
                ours.setdefault(l["game_id"], l["side"])
    cands = [c for c in cands if ours.get(c["game_id"], c["side"]) == c["side"]]
    settled = [c for c in cands if not c["waiting"]]
    elo = None
    used = {t for p in picks if p["date"] == iso for l in p["legs"] for t in l.get("bd_tags", [])}   # the board's memory
    new = []
    for kind in todo:
        lock_game = posted["lock"]["legs"][0]["game_id"] if "lock" in posted and posted["lock"]["status"] == "open" else None
        replacing = kind in posted                            # the opening board is value only; replacements may lean
        if replacing and sum(p["date"] == iso and (p.get("round") or 1) > 1 for p in picks) >= MAX_REPLACEMENTS:
            continue                                          # enough for today - accuracy over volume
        avoid = {l["game_id"] for p in picks if p["date"] == iso and p["status"] != "waiting" and p["kind"] not in ("eight", "four")
                 for l in p["legs"]}
        fixed = {k: posted[k]["legs"] for k in ("lock", "dog", "two", "three")
                 if k in posted and posted[k].get("status") != "waiting" and posted[k].get("legs")}   # build on what's up
        best = make_board(cands, lock_game, allow_lean=replacing, avoid=avoid, fixed=fixed).get(kind)
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
              "p_hit": round(b["p_hit"], 4), "stake": STAKE, "status": "open", "pnl": 0.0,
              "lean": bool(b.get("lean")) or replacing}     # a replacement (after a play's graded) is always a LEAN:
                                                            # the lock/value grades are the opening board's calls only
        for leg in pk["legs"]:
            leg["tier"] = "lean" if pk["lean"] else "lock" if kind == "lock" else leg_tier(leg)
        pk["tier"] = pick_tier({**pk, "tier": None})
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


ASK_STEEP = -300              # "ask the engine": never suggest a moneyline shorter than this - use the spread
ASK_PATH = "docs/sports/reads.json"


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
                        "sport": sd.LEAGUES[g["league"]][2], "start": g["start"],
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
        out.append({"id": gid, "league": g["league"], "emoji": sd.LEAGUES[g["league"]][3], "sport": sd.LEAGUES[g["league"]][2],
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
    sp.CACHE = sp.load()
    sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)
    add_breakdowns(games, model, picks)
    posted = post_board(games, model, picks, now, day)          # replaces any graded play (this pass or earlier)
    for pk in posted:
        print(f"posted {pk['kind']} (replacement) for {day}")
    sd.save_games(games)
    _save("picks.json", picks)
    import sports_dashboard
    try:
        engine_reads(games, model, picks)
    except Exception as e:                                             # noqa: BLE001 - never block the dashboard
        print(f"engine reads failed: {e}")
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
            import sports_totals                                        # over/unders: only once they beat the book
            print("totals study:", {k: (v.get("hit_top"), v.get("proven")) for k, v in sports_totals.study(games).items()})
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
    try:
        engine_reads(games, model, picks)
    except Exception as e:                                             # noqa: BLE001 - never block the dashboard
        print(f"engine reads failed: {e}")
    sports_dashboard.write(picks, model, games, bankroll_series(picks), START_BANKROLL)
    return picks


if __name__ == "__main__":
    run(repick="--repick" in sys.argv, fetch="--offline" not in sys.argv)
