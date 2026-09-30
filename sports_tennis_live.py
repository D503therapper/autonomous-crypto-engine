"""🎾 LIVE TENNIS for LIVE PLUS MONEY: the score, the live price and a proper tennis Markov model.

The model (pure Python, cached):
  - Every point is an independent coin: the server wins it with a fixed chance (iid-points model). The tour's
    average share of service points won is the anchor (ATP ~64%, WTA ~56%).
  - From the pre-match win chance we back out the two players' serve-point chances: base + d for the player and
    base - d for the opponent, with d solved so the model's 0-0 match chance is exactly the pre-match chance
    (best of 3 or 5). Each player's hold chance on serve follows from that.
  - From any score - sets, games, the current game's points (or tiebreak points), who's serving (averaged over
    both when the feed doesn't say) - the model runs the exact recursion: game -> tiebreak -> set -> match, with
    deuce/advantage, 7-point tiebreaks at 6-6 and a 10-point tiebreak in the final set of a Slam.
The feed side (ESPN tennis scoreboards for the score, Bovada's tennis feed for the live price) is parsed with the
same code sports_tennis uses pregame; sports_live applies the live rules."""
import math
import json
from datetime import timedelta
from functools import lru_cache

import sports_tennis as st

SERVE = {"atp": 0.645, "wta": 0.565}      # tour-average share of service points won (the iid-points anchor)
POINTS = {"0": 0, "00": 0, "love": 0, "15": 1, "30": 2, "40": 3, "a": 4, "ad": 4, "adv": 4}


# ---------------------------------------------------------------- the Markov model
@lru_cache(maxsize=200000)
def game_p(p, a=0, b=0):
    """The server wins the game from points (a, b) (0/1/2/3 = 0/15/30/40; 4 = advantage), serve-point chance p."""
    q = 1 - p
    if a >= 3 and b >= 3:                                   # deuce territory
        deuce = p * p / (p * p + q * q)
        if a == b:
            return deuce
        return p + q * deuce if a > b else p * deuce
    if a >= 4:
        return 1.0
    if b >= 4:
        return 0.0
    return p * game_p(p, a + 1, b) + q * game_p(p, a, b + 1)


def _tb_server_a(n, a_first):
    """Does A serve point n (0-based) of a tiebreak? First point by the first server, then two each."""
    first = ((n + 1) // 2) % 2 == 0
    return a_first if first else not a_first


@lru_cache(maxsize=200000)
def tb_p(pa, pb, i=0, j=0, a_first=True, n=7):
    """A wins the tiebreak (first to n, win by 2) from points (i, j). pa / pb = A's / B's serve-point chance."""
    if i >= n and i - j >= 2:
        return 1.0
    if j >= n and j - i >= 2:
        return 0.0
    if i >= n - 1 and j >= n - 1 and i == j:                # level at the end: two points, one served by each
        x, y = pa, 1 - pb                                    # (A wins on A's serve, A wins on B's serve)
        return x * y / (x * y + (1 - x) * (1 - y))
    w = pa if _tb_server_a(i + j, a_first) else 1 - pb
    return w * tb_p(pa, pb, i + 1, j, a_first, n) + (1 - w) * tb_p(pa, pb, i, j + 1, a_first, n)


@lru_cache(maxsize=200000)
def set_dist(pa, pb, ga=0, gb=0, a_serves=True, tb=7):
    """From games (ga, gb) with A serving the next game: (A wins & A serves first next set, A wins & B serves first,
    B wins & A serves first, B wins & B serves first). The service order runs on through sets (a tiebreak counts as
    one game)."""
    if (ga >= 6 and ga - gb >= 2) or ga == 7:
        return (1.0, 0.0, 0.0, 0.0) if a_serves else (0.0, 1.0, 0.0, 0.0)
    if (gb >= 6 and gb - ga >= 2) or gb == 7:
        return (0.0, 0.0, 1.0, 0.0) if a_serves else (0.0, 0.0, 0.0, 1.0)
    if ga == 6 and gb == 6:
        w = tb_p(pa, pb, 0, 0, a_serves, tb)
        return (0.0, w, 0.0, 1 - w) if a_serves else (w, 0.0, 1 - w, 0.0)   # the other player serves first next set
    h = game_p(pa) if a_serves else 1 - game_p(pb)
    win, lose = set_dist(pa, pb, ga + 1, gb, not a_serves, tb), set_dist(pa, pb, ga, gb + 1, not a_serves, tb)
    return tuple(h * x + (1 - h) * y for x, y in zip(win, lose))


@lru_cache(maxsize=200000)
def match_from_set(pa, pb, sa, sb, a_serves, need, final_tb):
    """A wins the match from sets (sa, sb) with a new set about to start, A serving its first game."""
    if sa >= need:
        return 1.0
    if sb >= need:
        return 0.0
    tb = final_tb if sa == sb == need - 1 else 7
    d = set_dist(pa, pb, 0, 0, a_serves, tb)
    return (d[0] * match_from_set(pa, pb, sa + 1, sb, True, need, final_tb)
            + d[1] * match_from_set(pa, pb, sa + 1, sb, False, need, final_tb)
            + d[2] * match_from_set(pa, pb, sa, sb + 1, True, need, final_tb)
            + d[3] * match_from_set(pa, pb, sa, sb + 1, False, need, final_tb))


def _after_set(pa, pb, d, sa, sb, need, final_tb):
    return (d[0] * match_from_set(pa, pb, sa + 1, sb, True, need, final_tb)
            + d[1] * match_from_set(pa, pb, sa + 1, sb, False, need, final_tb)
            + d[2] * match_from_set(pa, pb, sa, sb + 1, True, need, final_tb)
            + d[3] * match_from_set(pa, pb, sa, sb + 1, False, need, final_tb))


def _live_known(pa, pb, sa, sb, ga, gb, pts, a_serving, need, final_tb):
    """A's match chance with the server known. pts = (A's points, B's points) in the current game/tiebreak or None."""
    tb = final_tb if sa == sb == need - 1 else 7
    if ga == 6 and gb == 6:                                  # in the tiebreak
        i, j = pts or (0, 0)
        n = i + j
        a_first = a_serving if _tb_server_a(n, True) else not a_serving   # who served the tiebreak's first point
        w = tb_p(pa, pb, i, j, a_first, tb)
        d = (0.0, w, 0.0, 1 - w) if a_first else (w, 0.0, 1 - w, 0.0)   # (the tiebreak's first receiver serves next)
        return _after_set(pa, pb, d, sa, sb, need, final_tb)
    a, b = pts or (0, 0)
    h = game_p(pa, a, b) if a_serving else 1 - game_p(pb, b, a)
    win = set_dist(pa, pb, ga + 1, gb, not a_serving, tb)
    lose = set_dist(pa, pb, ga, gb + 1, not a_serving, tb)
    d = tuple(h * x + (1 - h) * y for x, y in zip(win, lose))
    return _after_set(pa, pb, d, sa, sb, need, final_tb)


def live_p(pa, pb, sets=(0, 0), games=(0, 0), pts=None, a_serving=None, bo=3, final_tb=7):
    """A's match win chance from the score: sets won, games in the current set, points in the current game (A's, B's;
    tiebreak points at 6-6), who's serving (True = A, False = B, None = unknown: both, half and half)."""
    need = 3 if int(bo or 3) == 5 else 2
    pa, pb = round(min(max(pa, 0.2), 0.95), 5), round(min(max(pb, 0.2), 0.95), 5)
    sa, sb = sets
    if sa >= need:
        return 1.0
    if sb >= need:
        return 0.0
    ga, gb = games
    if a_serving is None:
        return 0.5 * (_live_known(pa, pb, sa, sb, ga, gb, pts, True, need, final_tb)
                      + _live_known(pa, pb, sa, sb, ga, gb, pts, False, need, final_tb))
    return _live_known(pa, pb, sa, sb, ga, gb, pts, a_serving, need, final_tb)


@lru_cache(maxsize=20000)
def serve_split(p_pre, tour="atp", bo=3, final_tb=7):
    """Back out (A's, B's) serve-point chances from A's pre-match win chance: tour average +/- d, with d solved so the
    model's 0-0 match chance (server unknown) equals p_pre."""
    base = SERVE[st.tour_of(tour)]
    p_pre = min(max(p_pre, 0.01), 0.99)
    lo, hi = -0.25, 0.25
    for _ in range(50):
        d = (lo + hi) / 2
        if live_p(base + d, base - d, bo=bo, final_tb=final_tb) < p_pre:
            lo = d
        else:
            hi = d
    d = (lo + hi) / 2
    return round(base + d, 5), round(base - d, 5)


def hold_p(serve_point_p):
    """Chance to hold serve from 0-0 in a game."""
    return game_p(round(serve_point_p, 5))


def final_tb_of(tourney):
    """Slams play a 10-point tiebreak at 6-6 in the final set; everything else a regular 7-point one."""
    return 10 if any(k in str(tourney or "").lower() for k in st.MAJORS) else 7


# ---------------------------------------------------------------- the score from ESPN's feed
def _pts(x):
    """'15' / '40' / 'AD' / tiebreak '5' -> an int, None if unreadable."""
    s = str(x if x is not None else "").strip().lower()
    if s in POINTS:
        return POINTS[s]
    try:
        return int(float(s))
    except ValueError:
        return None


def score_state(m):
    """A live match row (sports_tennis.parse_espn) -> {sets: (p1, p2), games: (p1, p2) in the current set,
    done: [(g1, g2)...] finished sets, pts: (p1, p2) or None, server: 1/2/None, set_no}."""
    s1 = [int(x) for x in str(m.get("sets1") or "").split()]
    s2 = [int(x) for x in str(m.get("sets2") or "").split()]
    pairs = list(zip(s1, s2))

    def finished(a, b):
        return max(a, b) >= 6 and (abs(a - b) >= 2 or max(a, b) == 7)
    done = [(a, b) for a, b in pairs if finished(a, b)]
    cur = pairs[len(done)] if len(pairs) > len(done) else (0, 0)
    sets = (sum(a > b for a, b in done), sum(b > a for a, b in done))
    tb = cur == (6, 6)
    p1, p2 = m.get("pts1"), m.get("pts2")
    pts = None
    if p1 is not None and p2 is not None:
        a, b = _pts(p1), _pts(p2)
        if a is not None and b is not None:
            pts = (a, b)                                     # (advantage = 4 vs 3)
            if not tb and (max(pts) > 4 or (max(pts) == 4 and min(pts) != 3)):
                pts = None                                   # not a game score we understand: leave it out
    return {"sets": sets, "games": cur, "done": done, "pts": pts, "server": m.get("server"), "set_no": len(done) + 1}


# THE SET CORRECTION (9/30 study, ~69,000 tour matches since 2012 at Pinnacle's closing price, fit on 2012-20, graded
# on 2021+ it never saw): the point-by-point model under-rates what winning a set means. A player DOWN a set wins less
# than it said - women's 57% said, 50% real; men's 57% said, 52% real - and up a set, more. Live plus money is almost
# always the player behind, so the engine kept betting on players it over-rated (tennis live: 3-6). The fix, per tour:
# logit(p) x SET_FIX[0] + (sets up - sets down) x SET_FIX[1] - it lands on the real rate in every bucket (2021+).
SET_FIX = {"atp": (1.052, 0.149), "wta": (0.982, 0.306)}


def set_fixed(p, tour, sets):
    """The model's live win % corrected for the set score (SET_FIX)."""
    a, b = SET_FIX.get(tour, SET_FIX["atp"])
    p = min(1 - 1e-6, max(1e-6, p))
    z = a * math.log(p / (1 - p)) + b * (sets[0] - sets[1])
    return 1 / (1 + math.exp(-z))


def p1_live(m, pre_p1):
    """p1's live win chance for a live match row, from p1's pre-match chance (set-corrected - SET_FIX)."""
    tour, bo, ftb = st.tour_of(m), int(m.get("bo") or 3), final_tb_of(m.get("tourney"))
    pa, pb = serve_split(round(pre_p1, 4), tour, bo, ftb)
    s = score_state(m)
    serving = None if s["server"] not in (1, 2) else s["server"] == 1
    p = live_p(pa, pb, s["sets"], s["games"], s["pts"], serving, bo, ftb)
    return set_fixed(p, tour, s["sets"]), (pa, pb), s


def score_text(m, s=None):
    """'Sinner vs Alcaraz · 6-4, 3-2 (30-15)' - the set/game score from player 1's side."""
    s = s or score_state(m)
    parts = [f"{a}-{b}" for a, b in s["done"]]
    if s["games"] != (0, 0) or not parts or s["pts"]:
        parts.append(f"{s['games'][0]}-{s['games'][1]}")
    txt = ", ".join(parts)
    if s["pts"]:
        name = {0: "0", 1: "15", 2: "30", 3: "40", 4: "AD"}
        a, b = s["pts"]
        txt += f" ({a}-{b})" if s["games"] == (6, 6) else f" ({name.get(a, a)}-{name.get(b, b)})"
    return f"{st._say_name(m['p1_name'])} vs {st._say_name(m['p2_name'])} · {txt}"


def clock_text(m, s=None):
    s = s or score_state(m)
    who = {1: m["p1_name"], 2: m["p2_name"]}.get(s["server"])
    return f"Set {s['set_no']}" + (f" · {st._say_name(who)} serving" if who else "")


# ---------------------------------------------------------------- pre-match numbers
def load_prematch(path=None):
    try:
        with open(path or st.PREMATCH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def our_picks(path=None):
    """{match id: side} of our posted pregame tennis picks (the latest slates)."""
    try:
        with open(path or st.PICKS) as f:
            slates = json.load(f)
    except (OSError, ValueError):
        return {}
    return {l["match"]: int(l["side"]) for s in slates[-4:] for l in s.get("picks") or [] if l.get("match") and l.get("side")}


def any_live_soon(now, within_min=45, path=None):
    """A priced tour match (one with a pre-match number) going now or starting soon: keep the live watch up."""
    lo = (now - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")
    hi = (now + timedelta(minutes=within_min)).strftime("%Y-%m-%dT%H:%M")
    return any(lo <= v.get("start", "")[:16] <= hi and (v.get("mkt_p1") or v.get("model_p1"))
               for v in load_prematch(path).values())
