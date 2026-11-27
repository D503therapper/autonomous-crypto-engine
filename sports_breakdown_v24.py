"""THE MAIN-BOARD BREAKDOWN VOICE (restored 9/29 - the owner: the vocabulary rewrite came out vague and not our lingo).
The full breakdown behind a pick: the facts the engine weighed, in plain words, frozen at posting time.
Shown on the dashboard behind a "Full breakdown" tap."""
import functools
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_owner_lingo
import re
import sports_data as sd
import sports_lingo
import sports_model as sm
import sports_players as sp
import sports_breakdown as _sb_mod                       # (11/13: coin_side - sports_breakdown imports us only inside functions)

PT = ZoneInfo("America/Los_Angeles")
VERSION = 24          # bump when the wording changes: posted plays get their breakdown rewritten (never the pick)


@functools.lru_cache(maxsize=400000)
def _t(iso):
    """(10/16 hoops readiness: cached - data_gaps ran seen_all for 488 college hoops sides over 56,000 finals, 27 million
    strptime calls, 8 minutes a board; the same date string parses once.)"""
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def _days(start, then):
    """Days between two games by the CALENDAR (Pacific dates), never the clock floored (10/30 daily review: the Blue
    Jackets 10/29 card said "2 days off to Hurricanes' 1 day" - both played 10/27, Columbus at 7 PM ET and Carolina at
    8 PM ET, so the clock gave 48 hours = 2 and 47 hours = 1. A false rest edge on a unit play)."""
    return (start.astimezone(PT).date() - then.astimezone(PT).date()).days


_SEASON_MEMO = {}       # the season's game counts for one (finals list, cut) - computed once a board, not once a side


def _season_counts(fin, cut):
    """({team: games this season}, the 97th-percentile count, {team: games in the 365 days before the season}) for the
    finals before `cut` - memoized on the list itself (10/16: 488 sides x 56k finals was 8 minutes on one hoops day)."""
    key = (id(fin), len(fin), fin[0]["start"] if fin else None, fin[-1]["start"] if fin else None, cut)
    hit = _SEASON_MEMO.get(key)
    if hit is not None:
        return hit
    n, last = {}, {}
    prev = cut - timedelta(days=365)
    for g in fin:
        t = _t(g["start"])
        if t > cut:
            for x in (g["home"], g["away"]):
                n[x] = n.get(x, 0) + 1
        elif t > prev:
            for x in (g["home"], g["away"]):
                last[x] = last.get(x, 0) + 1
    ref = sorted(n.values())[int(0.97 * (len(n) - 1))] if n else 0   # (10/2 audit: the 90th percentile sank with the
    #                                                  missing games themselves - 4 instead of 5 - and let 0-4 Mercyhurst through)
    if len(_SEASON_MEMO) > 8:
        _SEASON_MEMO.clear()
    _SEASON_MEMO[key] = (n, ref, last)
    return _SEASON_MEMO[key]


def _am(a):
    return f"+{a}" if a > 0 else str(a)


REVENGE_DAYS = 400     # (10/15 truth audit) a "revenge game" needs a meeting this season or last - never a 2023 game
H2H_DAYS = 730         # "2 of the last 3 meetings" counts meetings within two years - never 2018-2024 (Texans-Cowboys)
SCHED_MAX_L = 6        # "their L's came against X, Y" names EVERY loss, so only a short season (football) - never 78 L's
B2B_HOURS = 29         # a back-to-back is the next night (the model's 1.2 days) - two nights off is NOT "short rest"
REST_B2B_ONLY = ("nba", "ncaab", "nhl", "mlb")   # (11/15, the owner's crew - Victor: "If 2 teams off 2+ days of rest, and
#   one of them is 4+ days of rest. That's not an advantage 99% of the time ... Both teams rested"): in the leagues that
#   play every other night, the card talks rest ONLY when one side is on a back-to-back (the next night, B2B_HOURS) - the
#   studies agree: the NBA's rested favorite LOSES against its price (the books over-move for rest), hockey's edge is the
#   back-to-back. "3 days off to their 2" is no edge - no line, no knock, no "better rested" reason. Football keeps its
#   lines (the bye is a studied spot; a short week is a real gap).


def b2b_only(lg):
    """Rest talk only on a back-to-back in this league (REST_B2B_ONLY)."""
    return lg in REST_B2B_ONLY
COIN_FLIP = (0.45, 0.55)  # "coin flip" / "close to even" on a card only for a read inside this band (10/30 daily review: the
#                          Panthers +164 floor play 10/29 read "our read says coin flip" at a 36.6% read - the floor
#                          closers meant the PRICE was about fair; a 37% team is no coin flip). The floor closers say "the
#                          price about fair"; the bottom_c lean closer ("close to a coin flip") needs a read in the band.


def _team_games(fin, tid):
    return [g for g in fin if tid in (g["home"], g["away"])]


def _line(g, tid):
    """'W 27-20 vs Lions' from tid's point of view."""
    home = g["home"] == tid
    us, them = (int(g["home_score"]), int(g["away_score"])) if home else (int(g["away_score"]), int(g["home_score"]))
    opp = g["away_name"] if home else g["home_name"]
    res = "W" if us > them else "L" if us < them else "T"
    return f"{res} {us}-{them} {'vs' if home else '@'} {opp}"


def _said(g, tid, pro=True):
    """The last game said plain, for a sentence: '4-2 win over the Flames' / '3-1 loss to the Flyers' / '2-2 tie with
    Duke' (10/21: the record line says the record WITH what just happened, never a tag-line after the record)."""
    home = g["home"] == tid
    us, them = (int(g["home_score"]), int(g["away_score"])) if home else (int(g["away_score"]), int(g["home_score"]))
    opp = g["away_name"] if home else g["home_name"]
    opp = f"the {opp}" if pro else opp
    if us > them:
        return f"{us}-{them} win over {opp}"
    if us < them:
        return f"{them}-{us} loss to {opp}"
    return f"{us}-{them} tie with {opp}"


def _last_parts(g, tid, pro=True):
    """(the opponent, 'W'/'L'/'T', '35-6') of a game from tid's side - the score read winner-first."""
    home = g["home"] == tid
    us, them = (int(g["home_score"]), int(g["away_score"])) if home else (int(g["away_score"]), int(g["home_score"]))
    opp = g["away_name"] if home else g["home_name"]
    res = "W" if us > them else "L" if us < them else "T"
    return (f"the {opp}" if pro else opp), res, f"{max(us, them)}-{min(us, them)}"


_D1 = {}               # 🏀 11/4: the slate's D1 set (sports_model.ncaab_d1), read once a breakdown


def _d1_set(fin):
    key = (id(fin), len(fin))
    if _D1.get("key") != key:
        try:
            _D1["key"], _D1["set"] = key, sm.ncaab_d1(fin)
        except Exception:                                     # noqa: BLE001 - can't tell = every team counts
            _D1["key"], _D1["set"] = key, None
    return _D1.get("set")


def non_d1(lg, tid):
    """🏀 11/4 (the owner: "Mount Marty, a no-name non-D1 team, that doesn't mean much"): is this college hoops team a
    non-D1 school (after breakdown() read the slate)? The card says so next to its name, and a win over one is never
    a 'blowout win' line."""
    return lg == "ncaab" and _D1.get("set") is not None and str(tid) not in _D1["set"]


def _opp_id(g, tid):
    return g["away"] if g["home"] == tid else g["home"]


SCHEDULE_FAIR = ("ncaab", "ncaaf")   # (11/15, the owner's crew - Victor on the Northern Iowa card: "Said Oakland was 🗑️ word
#   for word, Oakland just played 4 of 5 opening games against power 5 schools ... they're a tiny D1 school. No angle there
#   but that was its whole write up, essentially say Oakland trash cuz 0-5"; the owner: "We can't be looking like some
#   clowns"): in college, where the early schedule is buy games on the road, a loss to a team rated ABOVE us says nothing
#   about this game - the opponent's record for trash talk, its "last 5" slide and the 🥊 beatdown line count only games
#   against teams NOT rated above us (sports Elo, which counts the schedule).


def _tougher(x, tid, our_id, e):
    """In game x, was tid's opponent rated above our team (our_id)? No ratings = no (the old reading)."""
    if e is None:
        return False
    return e.r.get(_opp_id(x, tid), 1500.0) > e.r.get(our_id, 1500.0)


def _fair_games(games_, tid, our_id, e, lg):
    """tid's games that say something about this matchup: in SCHEDULE_FAIR leagues, never one against a team rated above
    us; elsewhere all of them."""
    if lg not in SCHEDULE_FAIR:
        return list(games_ or [])
    return [x for x in games_ or [] if not _tougher(x, tid, our_id, e)]


def unfair_losses(games_, tid, our_id, e, lg):
    """(11/16 EVERY FACT TRUE - the rest of the Oakland 0-5 class) tid's LOSSES to teams rated above us, in SCHEDULE_FAIR
    leagues: with any of these in it, its record / losing streak is no yardstick against OUR team - the 💪 / 📋 'better
    record' lines, "the stronger team" said by the records and the 🧊 losing-streak line all go quiet (the 11/14 Northern
    Iowa card also read "💪 2-2 to 0-5. Oakland about to get their ass beat."). Elsewhere, or with no ratings: []."""
    if lg not in SCHEDULE_FAIR or e is None:
        return []
    return [x for x in games_ or [] if _line(x, tid).startswith("L") and _tougher(x, tid, our_id, e)]


def _said_d1(g, tid, pro, lg):
    """_said, with '(a non-D1 school)' after a non-D1 college hoops opponent - never a tune-up dressed as a result."""
    s = _said(g, tid, pro)
    return s + " (a no-name non-D1 school)" if non_d1(lg, _opp_id(g, tid)) else s


FLOOR_ANGLES = 1.0     # 💰 11/4: a floor dog's closer says "the dog angles back it" only when the dog score sits this
#                        far over the price AND the studies' angles added something (dog_angles > 0). South Dakota +124
#                        (11/4): floor score 0.43 = the own read's 0.4 points over the price, NO dog angle at all - the
#                        card said "the dog angles back it". Under that it says what it is: the best dog left, a wash.


def dog_angles(leg):
    """The studies' part of a floor dog's score: the dog score minus the own read's points over the price (0 = the
    score is the own read alone, no angle fired)."""
    try:
        import sports as _sp
        own = (leg.get("edge_own", leg["edge"]) + 1) / leg["dec"]
        base = (own - (leg.get("p_market") or own)) * 100                  # (sports.dog_score's own-read part, capped)
        if base > _sp.OWN_CAP:
            base = 0.0 if leg.get("league") in _sp.OWN_TRAP else _sp.OWN_CAP
        return round((leg.get("floor_score") or 0) - base, 2)
    except (KeyError, TypeError, ZeroDivisionError):
        return 0.0


NBA_EARLY_GAMES = 5    # the first weeks of hoops: last season's facts carry the card until this many games are in
NCAAB_EARLY_GAMES = 5  # college hoops too (11/3) - a FULL D1 season only (NCAAB_D1_GAMES+ games; a non-D1 school or
#                        a team we don't hold whole gets nothing - never a guessed record)
_NCAAB_LAST = {}


def ncaab_last_season(fin, tid, before):
    """(W-L, points a game better than the other team) for a college hoops team LAST season - every game we hold
    (regular season + conference tournament + NCAA / NIT: the official record - 2024-25 Duke 35-4, Florida 36-4,
    American 22-13 checked), or None when it played under NCAAB_D1_GAMES (not a full D1 season - never a guess)."""
    want = (before.year if before.month >= 8 else before.year - 1) - 1
    key = (id(fin), len(fin), str(tid), want)
    if key in _NCAAB_LAST:
        return _NCAAB_LAST[key]
    w = l = n = 0
    diff = 0
    seen = set()
    for g in fin:
        if str(tid) not in (str(g.get("home")), str(g.get("away"))) or str(g.get("stype") or "2") not in ("2", "3"):
            continue
        t = _t(g["start"]).astimezone(PT)
        if (t.year if t.month >= 8 else t.year - 1) != want:
            continue
        k = (g["start"][:10], str(g.get("home")), str(g.get("away")))
        if k in seen:
            continue
        seen.add(k)
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError, KeyError):
            continue
        us, them = (hs, as_) if str(g["home"]) == str(tid) else (as_, hs)
        n += 1
        diff += us - them
        w += us > them
        l += us < them
    out = (f"{w}-{l}", round(diff / n, 1)) if n >= NCAAB_D1_GAMES else None
    if len(_NCAAB_LAST) > 4000:
        _NCAAB_LAST.clear()
    _NCAAB_LAST[key] = out
    return out
REC_GAP = 3            # 10/23, the owner: "Army 4-2, Tulsa 4-3 ... we know which side we want - they both have 4 wins":
#                        a record is a 'better team' line only 3+ games better (wins minus losses: 4-2 vs 4-3 is 1;
#                        93-68 vs 87-75 is 13)
GOOD_REC = 0.6         # a record said by itself ("Nuggets sit 9-4 so far") is a line only at 60%+ won
MIN_REC_GAMES = 3      # a record line / a record "because" needs this many games (0-1 vs 0-1 says nothing - 10/21)


def seen_all(fin, tid, before, lg):
    """Do we hold every game this team has played this season? Pro leagues: yes. College: only when its game count this
    season is near the most-covered teams' (the feed misses games between small schools) - else its record is a guess."""
    if lg not in ("ncaaf", "ncaab"):
        return True
    cut = before - timedelta(days=sm.BREAK_DAYS)
    n, ref, last_year = _season_counts(fin, cut)          # (10/16: once a board, not once a side)
    if not n:
        return True
    need = ref - 1 if lg == "ncaaf" else 0.8 * ref
    if n.get(tid, 0) >= need:
        return True
    if lg == "ncaab":                                    # (10/10 college hoops readiness check) ESPN's D1 feed (groups=50)
        #   holds every Division I team's games - all 365 D1 teams ended 2025-26 with 25+ games in our files; the only
        #   short records are the non-D1 opponents (348 teams, 1-3 games). Hoops schedules run 4-5 games apart by
        #   January (multi-team events), so the pace test alone read 11 of 11 priced games on 11/4/25, 39 of 39 on 11/7,
        #   26 of 33 on 11/26 and 21 D1 teams on 1/15 as 'a game missing'. A team that played a full D1 season last year
        #   (NCAAB_D1_GAMES in the 365 days before this season) is complete; a newcomer earns it by the pace test.
        return last_year.get(tid, 0) >= NCAAB_D1_GAMES
    if lg != "ncaaf" or not n.get(tid):                  # (10/2, the owner: the check blocked Penn State-Northwestern -
        return False                                     #  a Big Ten team that started a week late + had a bye: 3
    season = [g for g in fin if _t(g["start"]) > cut]
    mine = sorted(_t(g["start"]) for g in season if tid in (g["home"], g["away"]))   # games, all of them) - judged by
    first0 = min(_t(g["start"]) for g in season)         # its OWN calendar: one game a week since its first, one bye
    if _week(mine[0]) - _week(first0) > 1:               # allowed - only when its opener is in our data (never a team
        return False                                     # whose first games might be the missing ones)
    weeks = _week(before) - _week(mine[0])               # football weeks it could have played before this game's week
    return len(mine) >= weeks - byes_ok(weeks)


NCAAF_BYES = ((6, 1), (99, 2))     # byes a complete college schedule can show by its Nth week: one through week 6, two
#                                    after. (10/28: New Mexico St and Jax State - week-0 openers, byes 9/19 and 10/17, all 7
#                                    games on file - read as 'we don't hold all their games' and got no pick: the one-bye
#                                    rule is wrong past midseason - 12 games in 14-15 weeks means every team shows two)


def byes_ok(weeks):
    """How many gaps a team's own calendar may show over `weeks` football weeks and still be complete (NCAAF_BYES)."""
    for upto, n in NCAAF_BYES:
        if weeks <= upto:
            return n
    return NCAAF_BYES[-1][1]


NCAAB_D1_GAMES = 20                                      # a full Division I hoops season last year (D1 teams play 28-35;
#                                                          a non-D1 opponent shows up in 1-3 of our games)
_TUESDAY = datetime(2024, 1, 2, tzinfo=PT).date()        # a Tuesday: college football's week runs Tuesday to Monday


def _week(when):
    """The football week (Tuesday-Monday, Pacific dates) this kickoff falls in, counted from a fixed Tuesday. (10/9
    audit: counting 7-day slots from a team's own opener date read Georgia Tech / Utah / Kansas - a Thursday 9/3 opener,
    one bye, playing Saturday 10/10 = 37 days = 'six weeks' - as missing a game, and Ole Miss's Labor Day SUNDAY opener
    as 'too late' (10 days after the season's Thursday kickoff); both sides of Duke-Georgia Tech and Kansas-Utah lost
    their pick for nothing. A Thursday and the Saturday 37 days later are five football weeks apart, not six.)"""
    return (when.astimezone(PT).date() - _TUESDAY).days // 7


def _pos(name):
    """'UNLV' -> "UNLV's", 'Steelers' -> "Steelers'" (10/1 audit: "went UNLV' way")."""
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def _season(games_of_team, before):
    """This season's games: walk back until a break of 75+ days (the off-season)."""
    out = []
    last = before
    for g in reversed(games_of_team):
        t = _t(g["start"])
        if (last - t).days > sm.BREAK_DAYS:
            break
        out.append(g)
        last = t
    return list(reversed(out))


def goalie_known(g, team_side):
    """True when the side's starting goalie is confirmed / likely (sports_goalies). Unknown at post time, the card says
    the goalie it talks about is the LAST starter, never 'the Sharks' goalie' as if he's in tonight (10/16 truth audit:
    Askarov, Dobes and Dostal were each written up on 10/8-10/10 and a different goalie started)."""
    if g.get("league") != "nhl":
        return True
    try:
        import sports_goalies
        return bool(sports_goalies.starter(g.get("id"), team_side))
    except Exception:                                        # noqa: BLE001
        return False


def team_unsure(inj, team_id, team_name):
    """Players listed questionable / game-time / day-to-day for a side (name, position, status) - the 🚑 line names them,
    so the card never also calls that side 'full squad' (10/16 truth audit)."""
    return [r for r in sd._team_rows(inj, team_id, team_name) if any(s in str(r[2]).lower() for s in sd.UNSURE)]


def names_in(hl, names):
    """The league team names (nicknames, case-sensitive whole words) a headline mentions, in the order they appear."""
    hits = []
    for n in names:
        m = re.search(r"(?<![A-Za-z])" + re.escape(str(n)) + r"(?![a-z])", str(hl or ""))
        if m:
            hits.append((m.start(), n))
    return [n for _, n in sorted(hits)]


def sports_news_camp(hl, kind, mine):
    """sports_news.camp_talk for a card line (True when the module can't be read - the older checks still run)."""
    try:
        import sports_news
        return sports_news.camp_talk(hl, kind, mine, need_name=False)   # (the loop's own check names the camp)
    except Exception:                                        # noqa: BLE001
        return True


def someone_elses_story(hl, mine, games, lg, need_mine=False):
    """A headline ESPN tagged on `mine` that is really another team's story: it names another team of the league and
    not ours (10/16 truth audit: "The Sabres dealing with some personal stuff: 'Blackhawks' Bowen Byram to miss Buffalo
    return'" - a Blackhawk's news, pinned on the Sabres twice). need_mine=True: the headline has to name our team at all
    (a league round-up - "15 NFL players, coaches on the hot seat entering Week 6" - is nobody's camp talk)."""
    names = set()
    for g in (games or {}).values():
        if g.get("league") == lg:
            names.update(x for x in (g.get("home_name"), g.get("away_name")) if x)
    hits = names_in(hl, names)
    mine_in = bool(names_in(hl, [mine])) if mine else False
    if need_mine and not mine_in:
        return True
    return any(n != mine for n in hits) and not mine_in


def _best_win_line(us, them, ru, rt, r_ours, r_theirs, tid, oid, e, pro):
    """11/19 sweep (the owner, 10/1: never vague): "4-0 vs 3-1 looks even. Who they've played says Charleston." named
    nobody. The line names the win: the best team we beat (by the ratings), with the score - only when that team is
    rated above everybody THEY beat. [] = no such win = no line."""
    try:
        rt_ = lambda o: e.r.get(o, 1500.0)                   # noqa: E731
        ours = [x for x in r_ours or [] if _line(x, tid).startswith("W")]
        theirs = [x for x in r_theirs or [] if _line(x, oid).startswith("W")]
        if not ours:
            return []
        bw = max(ours, key=lambda x: rt_(_opp_id(x, tid)))
        if rt_(_opp_id(bw, tid)) < 1500.0 or any(rt_(_opp_id(x, oid)) >= rt_(_opp_id(bw, tid)) for x in theirs):
            return []
        o2, _, sc = _last_parts(bw, tid, pro)
        return [f"💪 {ru} vs {rt} looks even - but {us} beat {o2} {sc}, a better team than anybody {them} beat."]
    except Exception:                                        # noqa: BLE001
        return []


def close_records(ru, rt):
    """Two records are 'close' (same kind of record) when the win % gap is small AND the win gap is small: 85-77 vs
    98-64 (10/16 truth audit: "Records are close") is 13 wins apart - never close. The win gap allowed grows with the
    season: 2 wins in a short football / early season, ~3% of the games later (5 over a 162-game year)."""
    try:
        a = [int(x) for x in str(ru).split("-")[:2]]
        b = [int(x) for x in str(rt).split("-")[:2]]
    except ValueError:
        return False
    n = max(sum(a), sum(b), 1)
    pct = lambda r: r[0] / max(1, r[0] + r[1])
    net = lambda r: r[0] - r[1]
    return abs(pct(a) - pct(b)) <= 0.15 and abs(a[0] - b[0]) <= max(2, round(CLOSE_WIN_SHARE * n)) \
        and abs(net(a) - net(b)) < max(REC_GAP, round(2 * CLOSE_WIN_SHARE * n))   # (10/27, the owner: Panthers 6-6 vs
    #   Jets 4-7 "Records are close" - 3 games apart on the net is the owner's 10/23 "better team" line, never close)


CLOSE_WIN_SHARE = 0.03


def _record(gs, tid):
    w = sum(1 for g in gs if _line(g, tid).startswith("W"))
    lo = sum(1 for g in gs if _line(g, tid).startswith("L"))
    t = len(gs) - w - lo
    return f"{w}-{lo}" + (f"-{t}" if t else "")


def _site_side(g, side):
    """The side for a home / road record line - None at a NEUTRAL site (11/4 audit: E Michigan vs C Michigan at Ford
    Field, Detroit read "E Michigan is 2-2 at home" - the 'home' team on a neutral floor is not at home)."""
    return None if str((g or {}).get("neutral")) in ("1", "True", "true") else side


def _neutral(g):
    """A game played at a neutral site (no home crowd for either side)."""
    return str((g or {}).get("neutral")) in ("1", "True", "true")


def _site_rec(gs, tid, side):
    """('home' / 'road', games, wins, '3-0') - the team's record at this game's site this season, or None."""
    if side is None:
        return None
    at = [x for x in gs or [] if x.get("home" if side == "home" else "away") == tid and not _neutral(x)]
    #   (11/13 card audit: a NEUTRAL-site game is no home or road game - Ole Miss "5-0 in their own building" counted the
    #    Louisville game in Atlanta, Michigan "1-1 at home" the UConn game, the 49ers "2-0 on the road" the neutral Rams
    #    game, the Commanders "1-1-1 at home" the neutral Colts game)
    if not at:
        return None
    w = sum(1 for x in at if _line(x, tid).startswith("W"))
    return ("home" if side == "home" else "road", len(at), w, _record(at, tid))


def _streak(gs, tid):
    """'won 5 straight' / 'lost 3 straight' / ''."""
    if not gs:
        return ""
    last = _line(gs[-1], tid)[0]
    n = 0
    for x in reversed(gs):
        if _line(x, tid)[0] != last:
            break
        n += 1
    if n < 2 or last == "T":
        return ""
    return f"{'won' if last == 'W' else 'lost'} {n} straight"


def _names(rows, k=3):
    names = [n for n, _, _ in rows[:k]]
    more = len(rows) - len(names)
    return ", ".join(names) + (f" +{more} more" if more > 0 else "")


SLANG = {                        # our big phrases: each FAMILY shows up once on a board (any wording of it)
    "cheeks": r"cheeks", "complete ass": r"complete ass", "smack": r"smack that ass", "cook": r"\bcook(ing)?\b",
    "hood": r"whole hood", "tap in": r"tap in", "we gon see": r"gon' see|finna see",
    "trust": r"trust (the algorithm|it)", "let y'all down": r"let y'all down", "levels": r"levels to this|whole nother caliber",
    "trippin": r"trippin", "business": r"go to work|handle business|take care of business", "sheep": r"sheep",
    "clowns": r"clown", "run it back": r"run it back", "coming back": r"always be coming back", "gift": r"a gift",
    "free money": r"free money", "lock it in": r"lock it in", "tail it": r"tail it", "heater": r"heater",
    "easy money": r"easy money", "facts": r"just facts", "homies": r"homies", "super value": r"super value",
    "trash": r"super trash|trash as fuck|trash ass team", "straight ass": r"straight ass|they ass", "beast": r"a beast",
    "spank": r"spank", "ass beat": r"ass beat|beat the brakes off", "fin to": r"\bfin to\b", "talking shit": r"talking shit",
    "shit spot": r"shit spot", "say less": r"say less", "all day": r"all day",
    "filthy": r"filthy", "cant miss": r"can't miss",
    "nice": r"\bnice\b", "go off": r"go(ing)? off", "no answer": r"no answer", "watch": r"watch (him|her)|just watch",
    "problem": r"a problem", "different": r"different|built for|another level|ain't regular", "him": r"\bis (him|her)\b",
    "light": r"light work|easy work|handle .* light", "long day": r"long (day|night)", "ready": r"ain't ready",
    "pray": r"better pray", "mark it": r"mark it", "show": r"put on a show", "silly": r"look silly",
    "sleep": r"in their sleep|don't sleep", "trouble": r"in trouble", "on one": r"been on one|feeling it",
    # the context lines (rivalries, travel, domes, stakes, refs, pregame talk)
    "bad blood": r"bad blood", "no love lost": r"no love lost", "frequent flyer": r"frequent flyer",
    "suitcase": r"out of a suitcase", "backs to the wall": r"backs? (are )?(to|against) the wall",
    "nothing to play for": r"nothing to play for", "zebras": r"zebra", "hot seat": r"hot seat",
    "bulletin board": r"bulletin[- ]board", "circled": r"circled", "fishbowl": r"fishbowl", "thermostat": r"thermostat",
    # (11/4 lingo pass) his newer phrases, once a board too
    "lame": r"lame ass", "shambles": r"shambles", "no respect": r"no respect", "burn us": r"burn us",
    "fuck it": r"fuck (it|this)", "pissed": r"pissed", "crib": r"\bcrib\b", "grown men": r"grown men"}


def slang_in(texts):
    """The phrase families already used in these write-ups (so nothing else on the dashboard repeats them)."""
    return {f"slang:{k}" for t in texts for k, pat in SLANG.items() if re.search(pat, (t or "").lower())}


def dashboard_texts(skip=()):
    """Every write-up on the dashboard right now - open main-board picks and pending tennis picks - except the legs in
    `skip` (the ones being rewritten)."""
    import json
    import os
    out = []
    for path, key in ((os.path.join(sd.DATA, "picks.json"), "legs"), (os.path.join(sd.DATA, "tennis", "picks.json"), "picks")):
        try:
            with open(path) as f:
                cards = json.load(f)
        except (OSError, ValueError):
            continue
        for c in cards[-12:]:
            for l in c.get(key) or []:
                if l.get("result") is None and (l.get("id") or l.get("game_id"), l.get("side"), l.get("market")) not in skip:
                    out += l.get("breakdown") or []
    return out


SHORT_L = ["Lock it in.", "Easy money.", "Trust the algorithm.", "Free money.", "We on it.", "We locked in.", "All day.",
           "Bank it.", "Cash it."]
SHORT_S = ["Tap in.", "Give me that.", "Trust the algorithm.", "Get in.", "Ride it.", "Let it ride.", "Smart side."]
#   (11/13 card audit: "Book it." / "Stamp it." / "Say less." / "We finna see." are made-up slang (sports_lingo.MADE_UP)
#    and "Right side." / "Good number." a canned tail with no fact - sports_card_check.TAILS strips them off posted cards)


def _read(leg):
    """The read a leg's own number comes from: the weighed read (Lock / plays), the dog read, else the own read.
    (11/4 audit: a SPREAD or TOTAL leg carries the side's moneyline raw_own from candidates' base - the SMU -6 lean
    read "our ratings make SMU -362 — the book's at -110", a win chance set against the spread's juice. Off the
    moneyline, the leg's own cover / total read is the only number.)"""
    if leg.get("market") not in (None, "ml"):
        return leg.get("p")
    for k in ("w_p", "dog_p", "raw_own", "p"):
        if leg.get(k) is not None:
            return leg[k]
    return None


def fair_am(p):
    """Our read as a price (10/22, the owner: "these breakdowns suck" - a bottom line says OUR number next to the
    book's, never "our read beats the number"): 0.502 -> '-101', 0.45 -> '+122'. None when there's no read."""
    try:
        p = float(p)
    except (TypeError, ValueError):
        return None
    if not 0.02 < p < 0.98:
        return None
    a = round(100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)
    return f"-{a}" if p >= 0.5 else f"+{a}"


FAIR_MAX_GAP = 0.15    # 🔎 11/11 SWEEP: "our number" on a card is never more than this far from what the price needs


def card_fair(leg, own, beat=False):
    """OUR NUMBER as a card may print it (11/11 sweep - the owner: never false information). The Tulane +124 🔍 card of
    11/7 closed "We got Tulane at -446, the book says +124": the RAW ratings read (82%), the one the gap rule fires on
    and the 11/7 study found over-confident at every size (gap dogs read 74%, won 35%), printed as a fair price. A 🔍
    play's card number is the engine's FULL read (leg["p"] - Tulane 48% = +109); any read more than FAIR_MAX_GAP from
    what the price needs is no fair price at all (None = the closer says no number); beat=True (a value closer -
    "they're giving us X") only when the number really is better than the price, never the same number
    (the Bruins -142 card of 11/8: "We price Bruins at -142 - -142 is extra money")."""
    dec = leg.get("dec")
    if leg.get("gap") is not None and leg.get("p") is not None:
        own = leg["p"]
    if own is None or not dec or abs(own - 1 / dec) > FAIR_MAX_GAP:
        return None
    f = fair_am(own)
    if beat and f is not None and (own * dec <= 1 or f == _am(leg.get("odds") or 0)):
        return None
    return f


def fair_same(leg, own):
    """The read and the price are the SAME number once written as a price (-142 / -142): the card says so."""
    if leg.get("gap") is not None and leg.get("p") is not None:
        own = leg["p"]
    f = fair_am(own) if own is not None else None
    return f is not None and leg.get("odds") is not None and f == _am(leg["odds"])


def OWNER_LOCK(price, us, leg):
    """The Lock's closer in the owner's own words (10/18, the owner: "it's not really the lingo I trained you with") -
    one of his phrases per card, each family once a board (SLANG), a plain line only once they're all taken."""
    f = fair_am(leg.get("_read")) if isinstance(leg, dict) else None
    if NO_OUR_NUMBER:                                    # (11/19: never our number against the line makers')
        out = [f"✅ Bottom line: {price}. Our top play today. Lock it in.",
               f"✅ Bottom line: {price}. Our top play today. Trust the algorithm.",
               f"✅ Bottom line: {price}. {us} on top today. Easy money.",
               f"✅ Bottom line: {price}. The side we trust most today. Tap in.",
               f"✅ Bottom line: {price}. Strongest favorite on the slate. Free money."]
    elif f:                                              # (10/22: our number next to the book's - a fact, every time)
        out = [f"✅ Bottom line: {price}. We make {us} {f} - the book's at {_am(leg.get('odds'))}. Lock it in.",
               f"✅ Bottom line: {price}. Our number on {us} is {f}. Free money at this price.",
               f"✅ Bottom line: {price}. We'd lay {f} on {us} - getting {_am(leg.get('odds'))}. Easy money.",
               f"✅ Bottom line: {price}. {f} on our sheet, {_am(leg.get('odds'))} at the book. Trust the algorithm.",
               f"✅ Bottom line: {price}. We price {us} at {f}, the book's at {_am(leg.get('odds'))}. The whole hood eating with this one.",
               f"✅ Bottom line: {price}. Fair on {us} is {f} to us. Tap in."]
    else:
        out = [f"✅ Bottom line: {price}. The engine likes {us} more than the books do. Lock it in.",
               f"✅ Bottom line: {price}. Our top play today. Trust the algorithm.",
               f"✅ Bottom line: {price}. {us} on top today. Easy money."]
    if (leg.get("odds") or 0) > 0:                       # "super value" = a Lock at plus money (sports_owner_lingo)
        out = [f"✅ Bottom line: {price}. A Lock at plus money - super value. Tap in.",
               f"✅ Bottom line: {price}. Plus money on our Lock? Super value."] + out
    return out


def OWNER_PLAY(price, us, fair=None, odds=None):
    """A value play's closer in the owner's words (10/18) - see OWNER_LOCK. fair: our read as a price (10/22) - then
    every closer says our number next to the book's."""
    if NO_OUR_NUMBER:                                    # (11/19: the pick, the price, his closer - never our number)
        return [f"✅ Bottom line: {price}. Tap in.", f"✅ Bottom line: {price}. Easy money.",
                f"✅ Bottom line: {price}. Trust the algorithm.", f"✅ Bottom line: {price}. Tell the homies.",
                f"✅ Bottom line: {price}. Put the homies on {us}.", f"✅ Bottom line: {price}. We finna see.",
                f"✅ Bottom line: {price}. The whole hood eating with this one."]
    if fair and odds is not None:
        o = _am(odds)
        return [f"✅ Bottom line: {price}. We make {us} {fair} - the book's paying {o}. Tap in.",
                f"✅ Bottom line: {price}. Our number's {fair}; they're giving us {o}.",
                f"✅ Bottom line: {price}. We'd play {us} down to {fair} and they're paying {o}. The whole hood eating with this one.",
                f"✅ Bottom line: {price}. {fair} on our sheet, {o} at the book. Trust the algorithm.",
                f"✅ Bottom line: {price}. We price {us} at {fair}, the book's at {o}.",
                f"✅ Bottom line: {price}. Fair on {us} is {fair} to us and the book's hanging {o}. Give me {us}.",
                f"✅ Bottom line: {price}. We make {us} {fair}, the book says {o}."] + \
               ([f"✅ Bottom line: {price}. Line makers ain't showing no respect to {us} at {o} - we make 'em {fair}.",
                 f"✅ Bottom line: {price}. Fishy line - {us} at {o} when we make 'em {fair}."]   # (11/4, the
                #                                              owner's D503 Call on the Cavs: 'a very fishy line')
                if (odds or 0) > 0 else [])
    return [f"✅ Bottom line: {price}. The books are sleeping on {us}. Tap in.",
            f"✅ Bottom line: {price}. Our read beats the number. Tap in.",
            f"✅ Bottom line: {price} pays more than it should. The whole hood eating with this one.",
            f"✅ Bottom line: {price}. Good number, right side. Easy money.",
            f"✅ Bottom line: {price}. Our read's better than the price. Trust the algorithm.",
            f"✅ Bottom line: {price}. The engine found this one. Trust the algorithm.",
            f"✅ Bottom line: {price}. {us} are better than this price says.",
            f"✅ Bottom line: {price}. The number's too big for what {us} bring.",
            f"✅ Bottom line: {price}. Value on {us} - tell the homies.",
            f"✅ Bottom line: {price}. Put the homies on {us} at this price.",
            f"✅ Bottom line: {price}. The books undersold {us}. We finna see."]


def _short(v, price, lock, fact=""):
    """Every full bottom line is used on this board or yesterday's: the pick + a short closer (too short to repeat a
    phrase), a closer not used yet on this board."""
    pool = SHORT_L if lock else SHORT_S
    for i in range(len(pool)):
        c = pool[(sum(map(ord, v.seed)) + i) % len(pool)]
        if f"short:{c}" not in v.used:
            v.used.add(f"short:{c}")
            return f"✅ Bottom line: {price}. {fact} {c}".replace("  ", " ")
    return f"✅ Bottom line: {price}. {fact}".rstrip()


POSNAME = {"G": "goalie", "QB": "quarterback", "SP": "starting pitcher", "LW": "left wing", "RW": "right wing",
           "C": "center", "D": "defenseman", "PG": "point guard", "SG": "shooting guard", "SF": "small forward",
           "PF": "power forward", "RB": "running back", "WR": "receiver", "TE": "tight end", "K": "kicker"}


POSNAME_LG = {   # (10/1, the owner: "the Browns are playing without the goalie?" - a football G is a GUARD) by sport
    "nfl": {"G": "guard", "C": "center", "T": "tackle", "OT": "tackle", "OG": "guard", "OL": "lineman", "DE": "defensive end",
            "DT": "defensive tackle", "DL": "defensive lineman", "LB": "linebacker", "CB": "cornerback", "S": "safety",
            "FS": "safety", "SS": "safety", "P": "punter", "LS": "long snapper", "FB": "fullback"},
    "nba": {"G": "guard", "F": "forward", "C": "center"},
    "nhl": {"G": "goalie", "C": "center", "D": "defenseman"},
    "mlb": {"C": "catcher", "RP": "reliever", "1B": "first baseman", "2B": "second baseman", "3B": "third baseman",
            "SS": "shortstop", "LF": "left fielder", "CF": "center fielder", "RF": "right fielder", "DH": "designated hitter"}}
POSNAME_LG["ncaaf"], POSNAME_LG["ncaab"] = POSNAME_LG["nfl"], POSNAME_LG["nba"]


def _posname(pos, lg=None):
    """'G' -> 'goalie' in hockey, 'guard' in football / hoops - a sentence never says just the letters (the owner, 9/29:
    'the backup G' confused everybody), and never the wrong sport's word (10/1: a Browns guard became a 'goalie')."""
    k = str(pos or "").upper()
    if lg in POSNAME_LG and k in POSNAME_LG[lg]:
        return POSNAME_LG[lg][k]
    if lg is not None and lg != "nhl" and k == "G":
        return "guard"
    return POSNAME.get(k, str(pos or ""))


def _poss(team):
    """'the Canucks' -> "The Canucks'", 'Duke' -> "Duke's" (whose goalie it is) - at the START of a sentence."""
    t = team[:1].upper() + team[1:]
    return t + "'" if t.endswith("s") else t + "'s"


def _possm(team):
    """The same possessive in the MIDDLE of a sentence: 'the Canucks' -> "the Canucks'" (10/29: a card said "Cam Talbot
    — The Blue Jackets' last starter in net —" with a capital The mid-line)."""
    t = str(team or "")
    return t + "'" if t.endswith("s") else t + "'s"


FACT_KEYS = {   # (10/25) the lines that carry a fact - a score, a record, who's out, days off, miles - never dropped
    "b2b", "rest", "home", "road", "latest", "h2h", "h2h1", "rec", "cold", "hot", "bothhot", "even", "better", "sched",
    "keyout", "banged", "healthy", "splits_f", "splits_w", "splits_y", "bump", "revenge", "letdown", "momentum",
    "nba_last", "cx_trip", "cx_trip_home", "trash", "G_cold", "G_hot", "QB_cold", "QB_hot", "SP_cold", "SP_hot",
    "QB_washed", "f_last", "f_skid", "f_heat", "f_site", "f_rest", "f_b2b", "f_trip", "f_outs", "f_net", "f_qb",
    "f_pts", "f_pdo", "f_pyth", "f_shots", "f_go4", "f_h2h", "f_bye", "f_short", "f_ot", "f_last5", "f_gpg", "f_wall",
    "f_theirL", "risk"}


class Voice:
    """Picks a way to say each line: different wording from game to game and day to day, and never the same
    wording twice on one board (share one `used` set across a board's breakdowns)."""

    def __init__(self, seed, used=None):
        self.seed, self.used, self.mine = seed, used if used is not None else set(), []
        self.names = ()
        self.dirs = {}          # (10/27) line -> "us" / "neutral": which side a body line argues for (unset = ours)
        self.fill = set()       # (11/18) the refill lines of this card (fill_facts) - a first-hand line leads before one
        self.knocks = []        # (10/27) (priority, fact) - the facts that favor the OTHER side; one, the biggest, posts
        #                         as the ⚠️ risk line at the end of the card. Never a body line (the owner, 10/27: "a lot
        #                         of facts that support the opposing team")

    def tag(self, line, d):
        """Mark a line's direction ("us" / "neutral") and hand it back."""
        if line:
            self.dirs[line] = d
        return line

    def knock(self, pr, fact):
        """A fact that favors the other side: kept for the one ⚠️ risk line, never a body line."""
        if fact:
            self.knocks.append((pr, fact))
        return ""

    def say(self, key, options, must=False, names=(), tags=None, fact=False):
        """A fresh way to say it, or "" (the line is dropped) when every way is already taken on this board.
        must=True: a line the card can't go without (the pick, the bottom line) - reuse a wording rather than drop it.
        fact=True (10/25, the owner: "we need it to be thorough ... this goes for every pick"): a FACT line - a score,
        a record, who's out, the rest days - is never dropped for its wording; when every fresh wording is taken it takes
        the least-repeated one. The names and numbers in it make it its own line anyway. Before this the anti-repeat
        memory starved a card (the Canucks Dog, 10/25: 3 lines - its rest, trip and record lines all dropped).
        Our big phrases ("cheeks clapped", "smack that ass"...) show up once a board, never on two cards in a row.
        tags: per option, extra once-a-board marks (10/23: a one-liner's kicker - "We riding X" - once a board)."""
        if not options:
            return ""
        must = must or fact or key in FACT_KEYS
        start = sum(map(ord, f"{self.seed}|{key}")) % len(options)
        order = [(start + i) % len(options) for i in range(len(options))]
        def slang(x):
            out = [f"slang:{k}" for k, pat in SLANG.items() if re.search(pat, x.lower())]
            if tags:
                out += list(tags[options.index(x)] or [])
            if names:                                         # mixer lines: every opener / ending once a board
                t = x
                for nm in names:
                    t = t.replace(nm, "_").replace(nm[:1].upper() + nm[1:], "_")
                out += [f"piece:{p.strip().lower()}" for p in re.split(r"(?<=[.!?])\s+", re.sub(r"^\W+", "", t)) if p.strip()]
            return out
        import sports_breakdown as _sb                        # no 4-word run from this board or the last days' boards
        runs = lambda x: _sb.grams(x, tuple(names) + tuple(self.names))   # (the same memory the vocabulary uses)
        unused = [n for n in order if f"{key}:{n}" not in self.used]
        fresh = [n for n in unused if not any(s in self.used for s in slang(options[n]))
                 and not (runs(options[n]) & self.used)]
        if fresh:
            n = fresh[0]
        elif not must:
            return ""                                         # every fresh way repeats a phrase: drop the line
        else:                                                 # must say it: the wording that repeats the fewest phrases
            n = min(unused or order, key=lambda i: sum(s in self.used for s in slang(options[i]))
                    + len(runs(options[i]) & self.used))
        self.used.add(f"{key}:{n}")
        self.used.update(slang(options[n]))
        self.used.update(runs(options[n]))
        self.mine.append(f"{key}:{n}")
        return re.sub(r"(?<!\.)\.\.(?!\.)", ".", options[n])   # "Bain Jr.." -> "Bain Jr."


HYPE = re.compile(r"trust the algorithm|lock it in|free money|easy money|hammer it|hammer time|smash it|whole hood|real edge|"
                  r"tips it our way|\beat(s|ing|in')?\b|\bate\b|bag|money energy|can'?t lose|guaranteed", re.I)


VET_STARTS = {"QB": 100, "SP": 200, "G": 350}   # "washed" (the owner, 10/1) only for a long-time starter: this many
#                                                  starts in our box scores (2016 on - a QB's 100 = 6+ full seasons)
OLD_PID = 20000     # ...AND old: ESPN's player id under 20,000 = in the league by 2012 (Rodgers 8439, Stafford 12483 -
#                     Mahomes 3139477, Goff 3046779). The 10/2 audit: starts alone called a cold prime-age star "washed".
#                     No age for pitchers / goalies on file - so "washed" is QBs only (never false information).
_PIDS = {}


def old_qb(name):
    """A QB whose career started by 2012 (ESPN id under OLD_PID, from our NFL rosters)."""
    if "m" not in _PIDS:
        import csv
        import glob
        import gzip
        import os
        m = {}
        for f in sorted(glob.glob(os.path.join(sd.DATA, "roster", "nfl_*.csv.gz")))[-2:]:
            try:
                with gzip.open(f, "rt", newline="") as fh:
                    for r in csv.DictReader(fh):
                        if r.get("group") == "passing" and r.get("player") and str(r.get("pid") or "").isdigit():
                            m[r["player"]] = int(r["pid"])
            except (OSError, EOFError, ValueError):
                continue
        _PIDS["m"] = m
    pid = _PIDS["m"].get(name)
    return pid is not None and pid < OLD_PID


def lean_tone(lines, leg, seed=""):
    """A LEAN has no edge on our numbers - so no hype: sentences that sell it hard come out, and the bottom line says
    straight that it's a lean, not a lock (the owner: never 'trust the algorithm' when there's zero edge)."""
    out = []
    for ln in lines or []:
        if ln.lstrip("✅ ").lower().startswith("bottom line"):
            continue
        keep = [s for s in re.split(r"(?<=[.!?])\s+", ln) if s and not HYPE.search(s)]
        if keep and not (len(keep) == 1 and len(keep[0]) <= 3):
            out.append(" ".join(keep))
    import sports_breakdown as _sb
    team = leg.get("team", "")
    ends = _sb.lean_ends(leg, said=out)             # (10/1, the owner: the real reason - a coin flip or the price)
    out.append(ends[sum(map(ord, str(seed) + team)) % len(ends)])
    return out


def _stale(games, lg, team, name, before):
    """A football key player who sat the team's last 2 games (the box scores say so) - old news, never a fresh edge."""
    if lg not in ("nfl", "ncaaf"):
        return False
    try:
        import sports_absences as _sa
        return _sa.missed_lately(games, lg, team, name, before)
    except Exception:                                        # noqa: BLE001
        return False


def breakdown(leg, games, elo, injuries, used=None):
    """A plain-talk case for one leg: a list of short bullets ending with the bottom line."""
    try:                                                 # (11/16: the QB call reads the report this card is built on)
        import sports_qb
        sports_qb.note_injuries(injuries)
    except Exception:                                    # noqa: BLE001
        pass
    g = games[leg["game_id"]]
    lg, side = leg["league"], leg["side"]
    other = "away" if side == "home" else "home"
    tid, oid = g[side], g[other]
    us, them = leg["team"], leg["opp"]
    start = _t(g["start"])
    leg["inj_ok"] = inj_ok(leg, games, g)                # 🧩 11/19: may this card argue "they're short-handed"? (below)
    fin = [x for x in sm.finals(games, lg) if _t(x["start"]) < start]
    if lg == "ncaab":
        _d1_set(fin)                                   # (11/4: who's D1 on this slate - the non-D1 note on the card)
    ours, theirs = _team_games(fin, tid), _team_games(fin, oid)
    if not seen_all(fin, tid, start, lg):            # (10/1, the owner: never false info) we don't hold all of a college
        ours = []                                    # team's games this year: no record, streak, last game or series
    if not seen_all(fin, oid, start, lg):            # from half the picture ("North Texas 0-1" when we had 1 game)
        theirs = []
    s_ours, s_theirs = _season(ours, start), _season(theirs, start)
    # (10/1 audit) a RECORD is regular-season games only ("Yankees 95-68" counted 2 playoff wins - really 93-68), and a
    # streak / last game is this season's, never last year's ("Vikings 3-0 ... won 8 straight")
    r_ours = [x for x in s_ours if str(x.get("stype") or "2") == "2"]
    r_theirs = [x for x in s_theirs if str(x.get("stype") or "2") == "2"]
    v = Voice(f"{g['id']}|{start:%Y-%m-%d}|{side}", used)
    v.names = (us, them)                                  # team names blanked when comparing wordings to yesterday's
    pro = lg in ("nfl", "nba", "mlb", "nhl")
    the_us, the_them = (f"the {us}", f"the {them}") if pro else (us, them)
    if ours and theirs and (_days(start, _t(ours[-1]["start"])) - _days(start, _t(theirs[-1]["start"])) < 2
                            or b2b_only(lg) and not ((start - _t(theirs[-1]["start"])).total_seconds() / 3600 <= B2B_HOURS
                                                     < (start - _t(ours[-1]["start"])).total_seconds() / 3600)):
        leg["reasons"] = [r for r in leg.get("reasons") or [] if r != "better rested"]   # (11/15: no b2b = no rest edge)
    # (10/15 truth audit) "revenge game" only means something when the last meeting was recent: the Cardinals' card said
    # "Giants won the last meeting ... they haven't forgotten" about a 2023 game, the Panthers' about a 2023 Lions game.
    # The weight is the model's; the WORDS need a meeting this season or last (REVENGE_DAYS) - else the label goes
    last_vs = [x for x in ours if oid in (x["home"], x["away"])]
    if "revenge game" in (leg.get("reasons") or []) and \
            (not last_vs or (start - _t(last_vs[-1]["start"])).days > REVENGE_DAYS):
        leg["reasons"] = [r for r in leg["reasons"] if r != "revenge game"]
    if (sm._num(g.get("elev")) or 0) < sm.THIN_AIR_M:  # "altitude edge" only means something up in real thin air
        leg["reasons"] = [r for r in leg.get("reasons") or [] if r != "altitude edge"]
    out, said = [], set()          # said: reasons already used as a "because", so no line repeats another
    leg["bd_tags"] = v.mine        # which wordings this breakdown used (so the rest of the board avoids them)
    FORM = {}                      # (ours?, "hot"/"cold") -> (starter, his numbers) for the card's "why"
    rec_t = gap = None
    rec_t_cmp = None               # (11/16) their record as a yardstick against us - None in college when its losses
    n_cold = 0                     #  include one to a team rated above us (unfair_losses)

    # form
    rec_u = _record(r_ours, tid) if r_ours else None
    heat = _streak(s_ours, tid)
    n_hot = int(heat.split()[1]) if heat.startswith("won") else 0
    heat_t = _streak(s_theirs, oid)                 # (10/2, the owner: "Virginia Tech, four straight W's, we don't go
    their_hot = int(heat_t.split()[1]) if heat_t.startswith("won") else 0   # against a heater - well, the other team
    if n_hot >= HOT_MIN and their_hot >= n_hot:                              # has four straight W's"): both hot = say
        #                                           (10/29: "rolling" at 2 straight was false - 3+ is a heater)
        said.add("hotter recent form")                                       # both, never "the heater's ours"
        #   (11/18, cards_1118: "Both teams are rolling: Ducks have won 5 straight, Predators 5" argued their side in our
        #    body - our streak is the body line, THEIR heater is a knock for the one ⚠️ line; the one-liner still never
        #    sells "the heater's ours")
        out.append(v.say("bothhot", [f"🔥 {us} have won {n_hot} straight" + (f" ({rec_u})." if rec_u else "."),
                                      f"🔥 {n_hot} straight W's for {us}" + (f", {rec_u} on the year." if rec_u else "."),
                                      f"🔥 {us} haven't lost in {n_hot}" + (f" - {rec_u} overall." if rec_u else ".")]))
        v.knock(5, f"{them} come in on {_an(their_hot)} {their_hot}-game heater")
        n_hot = 0                                                             # (no 'hot hand' line in the why either)
    elif rec_u and n_hot >= HOT_MIN:                                          # (10/29: a "heater" is 3+ straight, never 2)
        said.add("hotter recent form")
        out.append(v.say("hot", [f"🔥 {us} are {rec_u} and on {_an(n_hot)} {n_hot}-game heater.",
                                  f"🔥 {us} ({rec_u}) have won {n_hot} straight and they're rolling.",
                                  f"🔥 {us} are rolling — {n_hot} wins in a row, {rec_u} on the year.",
                                  f"🔥 {us} can't stop winning: {n_hot} straight, {rec_u} overall.",
            f"🔥 {us} are cooking — {n_hot} straight W's, {rec_u} overall.",
            f"🔥 Heat check: {us} have won {n_hot} in a row ({rec_u}).",
            f"🔥 {n_hot} straight for {us} ({rec_u}). {them} fin to catch that heat.",
            f"🔥 {us} ({rec_u}) won {n_hot} in a row and they ain't done. Say less.",
            f"🔥 {us} are on a heater - {n_hot} straight, {rec_u} on the year."]))
    rec_line = bool(rec_u) and n_hot < HOT_MIN and len(r_ours) >= MIN_REC_GAMES   # (10/21, the owner: a record with a tag-line
    #                                                  after it says nothing - the record line waits to see if the
    #                                                  records get compared below; if not, it says the record WITH
    #                                                  something: the other side's record, or the last game's score)
    if r_theirs:
        rec_t = _record(r_theirs, oid)
        cold = _streak(s_theirs, oid)
        n_cold = int(cold.split()[1]) if cold.startswith("lost") else 0
        _unfair = unfair_losses(r_theirs, oid, tid, elo.get(lg), lg)
        rec_t_cmp = None if _unfair else rec_t
        if n_cold and unfair_losses((s_theirs or [])[-n_cold:], oid, tid, elo.get(lg), lg):
            n_cold = 0                                   # (11/16: a skid through teams rated above us says nothing)
        w_t = sum(1 for x in r_theirs if _line(x, oid).startswith("W"))
        rating_t = elo[lg].r.get(oid, 1500.0) if elo.get(lg) is not None else 1500.0
        trash = (len(r_theirs) >= 3 and w_t / len(r_theirs) < 0.35) or n_cold >= 3 or rating_t < 1420
        if elo.get(lg) is not None and elo[lg].r.get(tid, 1500.0) <= rating_t:
            trash = False                                # (no 'cold' dig either when the ratings don't have us better)
            n_cold = n_cold if n_cold < 2 else 0
        if n_cold >= 2 and not trash:                   # the trash-talk line below covers the really bad ones
            out.append(v.say("cold", [f"🧊 {them} are {rec_t} and ice cold — {n_cold} straight L's.",
                                       f"🧊 {them} have dropped {n_cold} in a row ({rec_t}).",
                                       f"🧊 {n_cold} straight losses for {them}. They can't buy a W.",
                                       f"🧊 {them} ({rec_t}) keep taking L's — {n_cold} straight.",
            f"🧊 {them} ({rec_t}) are in a slump — {n_cold} straight.",
            f"🧊 {them} forgot how to win: {n_cold} straight L's.",
            f"🧊 {them} dropped {n_cold} in a row ({rec_t}). They fin to make it {n_cold + 1}.",   # (10/23: his lingo,
            f"🧊 {n_cold} straight L's for {them}. That's a shit stretch, and {us} ain't the cure.",   #  the skid is the fact)
            f"🧊 {them} ({rec_t}) lost {n_cold} straight — {us} fin to spank 'em."]))

    # strength
    e = elo.get(lg)
    if e is not None:
        home_edge = 0 if str(g.get("neutral")) == "1" else (e.hfa if side == "home" else -e.hfa)
        gap = e.r.get(tid, 1500.0) - e.r.get(oid, 1500.0) + home_edge      # same yardstick as the card's reasons
        raw_gap = e.r.get(tid, 1500.0) - e.r.get(oid, 1500.0)   # (11/4: the home edge never makes the lower-rated team
        said.add("the stronger team")                   # said here either way (better / even / worse): not again later
        _ru = _record(r_ours, tid) if len(r_ours) >= 2 else None    # (10/21: 1-0 vs 0-1 compares nothing; two games in,
        _rt = _record(r_theirs, oid) if len(r_theirs) >= 2 else None   #  football's schedule line is already a real fact)
        if lg in SCHEDULE_FAIR and rec_t and not rec_t_cmp and _ru and _rt and \
                (lambda a, b: a[0] * (b[0] + b[1]) > b[0] * (a[0] + a[1]))(
                    [int(x) for x in _ru.split("-")[:2]], [int(x) for x in _rt.split("-")[:2]]):
            _rt = None                                   # (11/16: our better record vs a record full of buy-game losses)
        if _ru and _rt:                                  # (10/1, the owner: "they're just better" says nothing -
            _w = lambda r: (lambda a: a[0] / max(1, a[0] + a[1]))([int(x) for x in r.split("-")[:2]])
            if gap > 15 and raw_gap > 0 and _w(_ru) > _w(_rt):   # the records do)  "the better team" - South Dakota 11/4)
                _nt = lambda r: (lambda a: a[0] - a[1])([int(x) for x in r.split("-")[:2]])
                big = _nt(_ru) - _nt(_rt) >= REC_GAP     # (10/23: the trash talk needs a real gap - 4-2 vs 4-3 is none)
                out.append(v.say("better", ([f"💪 {us} ({_ru}) vs {them} ({_rt}) — the better team is on our side.",
                                             f"💪 {_ru} against {_rt}: {us} been the better team.",
                                             f"💪 Records say it: {us} {_ru}, {them} {_rt}.",
                                             f"💪 {us} {_ru}, {them} {_rt}. Better squad on our side.",
                                             f"💪 {us} {_ru} against {_pos(them)} {_rt}. Levels to this shit.",
                                             f"💪 {_ru} to {_rt}. {them} about to get their ass beat."] if big else [
                                             #   (🗣️ 11/22: "close on paper, but our ratings have X ahead" / "the ratings
                                             #    like X" said no fact - a card never says "our ratings say"; the
                                             #    win that separates them is the line, or there is none)
                                             *_best_win_line(us, them, _ru, _rt, r_ours, r_theirs, tid, oid, e, pro)])))
                #   (10/23, the owner on Army 4-2 vs Tulsa 4-3: "they both have 4 wins" - a 'better team' claim needs
                #    a 3+ game record gap; close records say close, and the ratings carry it)
            elif gap < -15 and _w(_rt) > _w(_ru):
                pass                                     # (10/22, the owner: the old 'their record's better, we get the
                #                                          price' line said nothing - a record against us is no reason)
            elif close_records(_ru, _rt) and gap > 15:        # same-ish records, but the ratings (who they PLAYED)
                tough = [x for x in r_ours if _line(x, tid).startswith("L")]   # say we're better - name who beat us
                # (10/15 truth audit: "Don't let 84-78 fool you - White Sox took those L's from Tigers, Royals and
                # Rockies" named 3 of 78 losses; "Western KY's L's came against Georgia, Indiana and New Mexico St"
                # dropped Nevada and called 1-3 New Mexico St a tough loss). The line says the schedule explains the
                # record, so it names EVERY loss, only in a short season, and only when every one came against a team
                # the ratings have above us - one L to a weaker team and the story's false: no line.
                beat_us = [x.get("away") if x.get("home") == tid else x.get("home") for x in tough]
                names = [x.get("away_name") if x.get("home") == tid else x.get("home_name") for x in tough]
                if names and len(names) <= SCHED_MAX_L and all(e.r.get(o, 1500.0) > e.r.get(tid, 1500.0) for o in beat_us):
                    nm = ", ".join(names[:-1]) + (" and " if len(names) > 1 else "") + names[-1]
                    ls = "L's" if len(names) > 1 else "L"
                    one = "that L" if len(names) == 1 else "those L's"
                    out.append(v.say("sched", [f"⚖️ {us} {_ru}, {them} {_rt} — but {_pos(us)} {ls} came against {nm}.",
                                               f"⚖️ Same kind of record, tougher schedule: {_pos(us)} {ls} came against {nm}.",
                                               #   (11/19 sweep: "... tougher schedule: Panthers lost to Bears, Browns ..."
                                               #    read as a knock on our own side and the page's check cut it every time)
                                               f"⚖️ Don't let {_ru} fool you — {us} took {one} from {nm}."]))
            elif close_records(_ru, _rt) and abs(gap) <= 15:   # records AND ratings close: a coin-flip game
                plus = (leg.get("odds") or 0) > 0 and leg.get("market") == "ml"   # (10/27: said FOR us - a wash on
                #   paper at plus money is the whole point of a dog; never "even" as a shrug. 11/18, cards_1118: on a
                #   favorite "A wash on the records" / "nothing in it on paper" said nothing for our side - no line)
                if plus:
                    out.append(v.say("even", [
                        f"⚖️ {us} {_ru}, {them} {_rt} - a wash on paper, and the book's paying us plus money to take {us}.",
                        f"⚖️ Nothing between these two on the records ({us} {_ru}, {them} {_rt}) - so we take the plus money side.",
                        f"⚖️ {_ru} vs {_rt}. Dead even on paper, which is exactly why plus money on {us} is the play."]))

    # 🏀 the opening weeks of hoops: every team is 0-1 and the cards came out empty (10/21) - the one fact that's always
    # true then is LAST season (both records, the point gap, who we added), from the box scores we hold
    nba_f = None
    if lg == "nba" and len(r_ours) < NBA_EARLY_GAMES:
        try:
            import sports_nba_roster as _nr
            nba_f = _nr.season_facts(g, side, _nr.cached(), games)
        except Exception:                                 # noqa: BLE001
            nba_f = None
        if not (nba_f and nba_f.get("us") and nba_f.get("them") and nba_f["us"][1] > nba_f["them"][1]):
            nba_f = None                                  # (only when last season backs OUR side; the line comes
        #                                                    after the one under the pick - see nba_lines)
    if lg == "ncaab" and len(r_ours) < NCAAB_EARLY_GAMES:     # 🏀 11/3 opening night: every college card came out 1-3
        try:                                              # lines (0 games on file) - last season's full record and
            nba_f = {"us": ncaab_last_season(fin, tid, start), "them": ncaab_last_season(fin, oid, start), "added": []}
        except Exception:                                 # noqa: BLE001 - point gap, both sides, same rule as the NBA
            nba_f = None
        _wp = lambda r_: (lambda a: a[0] / max(1, a[0] + a[1]))([int(x) for x in r_.split("-")[:2]])   # noqa: E731
        if not (nba_f and nba_f.get("us") and nba_f.get("them") and nba_f["us"][1] > nba_f["them"][1]
                and _wp(nba_f["us"][0]) > _wp(nba_f["them"][0])):   # (the 'better squad' wording needs the RECORD
            nba_f = None                                  #  better too - Indiana St 11-21 'better' than 17-17 Charlotte
            #                                               on a 0.2-point margin read false)
    # the record, when nothing above compared it: with the other side's record, or with the last game's score
    if rec_line and not any(x and x[:1] in "💪🐺⚖" for x in out):
        last_said = _said_d1(s_ours[-1], tid, pro, lg) if s_ours else ""
        # 👍 11/18 (cards_1118 - the owner on the Nuggets card's "Nuggets are 7-5 after a 117-105 loss to the Suns": "a
        # few things in the breakdown where it doesn't make the Nuggets look good"): the record line never carries OUR
        # loss (the last game rides only when we won it) and a LOSING record of ours is never a body line at all; two
        # records that say nothing ("Dead even on the record", "Same record apiece") are not lines.
        if not _line(s_ours[-1], tid).startswith("W") if s_ours else True:
            last_said = ""
        _winning = (lambda a: a[0] > a[1])([int(x) for x in rec_u.split("-")[:2]])
        _wsh = lambda r: (lambda a: a[0] / max(1, a[0] + a[1]))([int(x) for x in r.split("-")[:2]])
        _plain_rec = [f"📋 {us} are {rec_u} on the year.", f"📋 {us} sit {rec_u} so far."]
        _won_rec = [f"📋 {us} are {rec_u} after a {last_said}.",
                    f"📋 {us} {rec_u} on the year - last time out, a {last_said}.",
                    f"📋 {us} sit {rec_u}; their last one was a {last_said}.",
                    f"📋 {rec_u} for {us}, fresh off a {last_said}."]
        _rec_edge = bool(rec_t) and len(r_theirs) >= MIN_REC_GAMES and _wsh(rec_u) > _wsh(rec_t)   # (ours beats theirs)
        if not _winning and not _rec_edge and not last_said:
            pass                                         # (a losing / .500 record with no win behind it: no body line)
        elif not _winning and not _rec_edge:             # (not a winning record, but we won the last one: the win)
            out.append(v.say("f_last", [f"📅 {us} come off a {last_said}.", f"📅 Last time out, {us} got a {last_said}.",
                                        f"📅 Fresh off a {last_said} for {us}."]))
        elif rec_t and len(r_theirs) >= MIN_REC_GAMES and _wsh(rec_u) > _wsh(rec_t) and lg in SCHEDULE_FAIR and not rec_t_cmp:
            out.append(v.say("rec", _plain_rec) if _winning else "")   # (a losing record of ours alone: no line)
        elif rec_t and len(r_theirs) >= MIN_REC_GAMES and _wsh(rec_u) > _wsh(rec_t):
            out.append(v.say("rec", [f"📋 {us} sit {rec_u}; {them} are {rec_t}. Better record's on our side.",
                                      f"📋 {rec_u} for {us}, {rec_t} for {them}. We got the better squad on paper.",
                                      f"📋 {us} come in {rec_u}, {them} {rec_t}.",
                                      f"📋 {us} {rec_u}, {them} {rec_t}. Our side's been winning more.",
                                      f"📋 {them} are {rec_t}. {us} are {rec_u}."]))
        elif rec_t and len(r_theirs) >= MIN_REC_GAMES and _wsh(rec_u) < _wsh(rec_t):   # (10/27: their better record
            v.knock(3, f"{them} come in {rec_t} to {_pos(us)} {rec_u}")                  #  is a knock, never a reason)
            #   (11/19, the Nuggets card: "📋 Nuggets sit 7-5 so far." over "⚠️ ... Celtics come in 11-3 to Nuggets'
            #    7-5" - the record the ⚠️ line already uses, arguing for nobody. With THEIR record the better one our
            #    record is no body line; the win behind it still is.)
            if last_said:
                out.append(v.say("f_last", [f"📅 {us} come off a {last_said}.", f"📅 Last time out, {us} got a {last_said}.",
                                            f"📅 Fresh off a {last_said} for {us}."]))
        elif last_said:
            out.append(v.say("rec", _won_rec))
        elif _wsh(rec_u) >= GOOD_REC:                    # (a plain record line only for a GOOD record - or one that
            out.append(v.say("rec", _plain_rec))         #  beats theirs, above)

    # talk our talk when the other side's been bad (only when the numbers back it up)
    r_theirs_all = r_theirs
    r_theirs = _fair_games(r_theirs, oid, tid, e, lg)                 # (11/15: college - games vs teams not rated above us)
    if r_theirs:
        w = sum(1 for x in r_theirs if _line(x, oid).startswith("W"))
        rating_them = e.r.get(oid, 1500.0) if e is not None else 1500.0
        n_cold = int(_streak(s_theirs, oid).split()[1]) if _streak(s_theirs, oid).startswith("lost") else 0
        if n_cold and unfair_losses((s_theirs or [])[-n_cold:], oid, tid, e, lg):
            n_cold = 0                                   # (11/16: a skid through teams rated above us says nothing)
        better = e is None or e.r.get(tid, 1500.0) > rating_them   # (10/1, the owner: a record doesn't show who they
        losing = len(r_theirs) >= 3 and w < len(r_theirs) - w       # (10/15: "Canucks ... a JV squad (1-1)", "Guardians are
        #   trash right now (85-77)" - trash talk needs a LOSING record too, not just a rating or a 3-game skid)
        _ours_worse = bool(r_ours) and rec_u and (lambda a, b: a[0] / max(1, sum(a)) < b[0] / max(1, sum(b)))(
            [int(x) for x in rec_u.split("-")[:2]], [w, len(r_theirs) - w])
        #   (10/21: a 0-3 Texans card called the 1-2 Cowboys trash - no trash talk from the side with the worse record)
        if better and losing and not _ours_worse and ((w / len(r_theirs) < 0.35) or n_cold >= 3 or rating_them < 1420):
            #   played - trash talk only when the engine's ratings, which count the schedule, have us better)
            rec = _record(r_theirs, oid)
            if len(r_theirs) != len(r_theirs_all):       # (11/16 EVERY FACT TRUE: the record of the FAIR games is never
                out.append(v.say("trash", [               #  shown as their season record - the line says what it counts)
                    f"🗑️ Take away the teams rated above {us} and {them} are still {rec}. Straight ass.",
                    f"🗑️ {them} are {rec} against teams that ain't rated above {us}. Trash right now.",
                    f"🗑️ {rec} for {them} against everybody not rated above {us}. They been ass."]))
            else:
              out.append(v.say("trash", [f"🗑️ {them} have been complete ass lately — {rec} and it ain't getting prettier.",
                                        f"🗑️ Straight up, {them} are trash right now ({rec}).",
                                        f"🗑️ {them} can't get out of their own way ({rec}).",
                                        f"🗑️ {them} are a mess right now. {rec} says it all.",
                                        f"🗑️ Nothing about {them} scares us ({rec}).",
            f"🗑️ {them} been looking like a JV squad ({rec}).",
            f"🗑️ {them} are straight garbage right now ({rec}).",
            f"🗑️ Watching {them} lately hurts ({rec}).",
            f"🗑️ {them} are about to get their cheeks clapped. {rec} — they been complete ass.",
            f"🗑️ {rec} lately. {them} are complete ass and it shows.",
            f"🗑️ {them} are super trash right now ({rec}).",
            f"🗑️ {them} been trash as fuck lately — {rec}.",
            f"🗑️ {rec}. {them} been straight cheeks.",
            f"🗑️ {them} are butt cheeks right now ({rec}).",
            f"🗑️ {rec} lately — they ass. {them} straight ass right now.",
            f"🗑️ {them} are a trash ass team right now ({rec}). We talking shit, but the record says it.",   # (10/23: "we're
            f"🗑️ {rec}. {them} fin to get spanked.",                                                   #  just talking shit
            f"🗑️ A {rec} team. {them} about to get their ass beat.",                                   #  here" - with the
            f"🗑️ {them} ({rec}) fin to get their cheeks clapped.",
            f"🗑️ {rec}. Lame ass team right now, that's {them}.",
            f"🗑️ {them} are in shambles - {rec}."]))                                   #  record right there)
    r_theirs = r_theirs_all                                           # (the rest of the card reads every game)

    # last games: just the latest scores - and only when they back the pick (the owner, 9/30: "Kings L 1-5 vs Avalanche"
    # in the Kings' breakdown makes no sense - we won our last one, and they lost theirs or had none)
    if s_ours and _line(s_ours[-1], tid).startswith("W") and (not s_theirs or _line(s_theirs[-1], oid).startswith("L")):
        _nd = lambda g_, t_: " (a non-D1 school)" if non_d1(lg, _opp_id(g_, t_)) else ""   # (11/13: "Idaho W 108-69
        #   (11/19 sweep, the owner: plain words, never robotic - "Charleston So W 92-68 vs West Georgia · Wofford L
        #    92-97 @ Queens" was a box-score line, the loser's score first; said the way people say it)
        _pl = lambda g_, t_, verb: (lambda sd_: f"{verb} {_an(sd_.split('-')[0])} {sd_}")(_said(g_, t_, pro))   # noqa: E731
        last_us = _pl(s_ours[-1], tid, "got") + _nd(s_ours[-1], tid)   # vs Lincoln (CA)" never said it was a tune-up)
        _same = bool(s_theirs) and (s_ours[-1] is s_theirs[-1] or (s_ours[-1].get("id") is not None
                                                                   and s_ours[-1].get("id") == s_theirs[-1].get("id")))
        #   (11/19: these two just played each other - "Stars got a 4-3 win over the Golden Knights · Golden Knights
        #    took a 4-3 loss to the Stars" said one game twice)
        both = f"{us} {last_us}" + (f" · {them} {_pl(s_theirs[-1], oid, 'took')}{_nd(s_theirs[-1], oid)}"
                                    if s_theirs and not _same else "")
        out.append(v.say("latest", [f"📅 Latest: {both}.", f"📅 Last time out: {both}.", f"📅 Last game for each: {both}.",
                                     f"📅 Where they're coming from: {both}.", f"📅 Last week's tape: {both}." if lg in ("nfl", "ncaaf")
                                     else f"📅 Last outing: {both}.", f"📅 How they came in: {both}.", f"📅 Fresh off: {both}."]))

    # head to head
    h2h = [x for x in ours if oid in (x["home"], x["away"]) and (start - _t(x["start"])).days <= H2H_DAYS]
    #   (10/15 truth audit: "Cowboys can't figure Texans out: 2 of 3 to Texans" counted 2018 and 2022 - two years, max)
    if h2h:
        last3 = h2h[-3:]
        w = sum(1 for x in last3 if _line(x, tid).startswith("W"))
        if 2 * w > len(last3) and len(last3) > 1:          # (10/1 audit: 1 of 2 isn't "owning" anybody)
            out.append(v.say("h2h", [f"🆚 {us} own this matchup — won {w} of the last {len(last3)}.",
                                      f"🆚 {us} have had {them}'s number: {w} of the last {len(last3)}.",
                                      f"🆚 History's on our side — {w} of the last {len(last3)} meetings went {_pos(us)} way.",
            f"🆚 {us} been owning {them} lately — {w} of the last {len(last3)}.",
            f"🆚 {them} can't figure {us} out: {w} of {len(last3)} to {us}."]))
        elif w == 1 and len(last3) == 1:
            out.append(v.say("h2h1", [f"🆚 {us} got 'em last time: {_line(h2h[-1], tid)}.",
                                       f"🆚 Last meeting went {_pos(us)} way ({_line(h2h[-1], tid)}).",
            f"🆚 {us} handled {them} last time ({_line(h2h[-1], tid)}).",
            f"🆚 Last time these two met, {us} took it ({_line(h2h[-1], tid)})."]))

    # the key players: QB / starting pitcher / goalie (the fun part)
    rows = sp.CACHE.get(lg) or []
    role = sp.ROLE.get(lg)
    if rows and role:
        def who(team_side, tid_):
            if role == "SP":
                return g.get("sp_" + team_side) or None
            if role == "G":                                   # (10/15: the card talks about the goalie the WEIGHT used -
                return sp.starter_for(rows, g, team_side)     #  the confirmed / likely starter, not whoever started last)
            name_ = sp.qb_for(rows, tid_, g["start"], lg, us if tid_ == tid else them)   # (11/15: the Carson Wentz card - a QB change is
            outs_ = leg.get("outs" if tid_ == tid else "opp_outs") or []   # unknown, and a man on the out list
            if name_ and (g["start"] or "")[:10] >= sp.QB_SETTLED_FROM and any(      # never plays on the card)
                    str(x).split(" (")[0].strip().lower() == name_.lower() for x in outs_):
                return None
            return name_

        def known(team_side):                                 # 10/16 NHL checkup: is tonight's goalie KNOWN (confirmed /
            if role != "G":                                   # likely - sports_goalies)? The last starter is tonight's
                return True                                   # starter only 45% of the time (2023-26 box scores), and 5 of
            try:                                              # the season's 7 🥅 lines named a goalie who didn't play -
                import sports_goalies                         # an unknown starter is said as what he is: in net LAST time
                if sports_goalies.confirmed(g.get("id"), team_side) is not None:
                    return True
                if sports_goalies.starter(g.get("id"), team_side) is not None:
                    return "likely"                           # (11/16: 'likely' / 'expected' is the page's word, not a
            except Exception:                                 #  fact - the Kraken's 'likely' Joey Daccord sat 11/14;
                pass                                          #  only a CONFIRMED goalie is said as tonight's man)
            # 11/6: unknown -> the weights read the PROJECTED starter (sports_players.projected_starter - the #1 rested,
            # the other goalie on a b2b). Named and NOT the last starter = "projected", never "in net last time out"
            # (that would be false) and never stated as tonight's man; the last starter himself stays "in net last time out".
            return "projected" if sp.starter_for(rows, g, team_side) != sp.last_starter(rows, g.get(team_side), g["start"]) \
                else False
        for team_side, t_id, ours_ in ((other, oid, False), (side, tid, True)):
            name = who(team_side, t_id)
            if not name:
                continue
            txt, mood = sp.form_line(lg, name, rows, g["start"], games)
            if not txt:
                continue
            kn = known(team_side)
            FORM[(ours_, mood)] = (name, txt, kn)             # (the card's one-line "why" can use it)
            vet = role == "QB" and old_qb(name) and \
                sum(r["player"] == name and r["start"] < g["start"] for r in rows) >= VET_STARTS["QB"]
            if not ours_ and mood == "cold" and vet:          # (the owner, 10/1: "this dude is washed - old, out of his
                out.append(v.say(role + "_washed", [          #  prime") - only a long-time starter who's cold NOW
                    f"🧓 {name} is washed — {txt}.",
                    f"🧓 {name} looks washed: {txt}.",
                    f"🧓 Father Time is catching {name} — {txt}. Washed."]))
            elif not ours_ and mood == "cold":
                out.append(v.say(role + "_cold", {
                    "QB": [f"🗑️ {name} has been complete booty cheeks — {txt}.",
                           f"🗑️ {name} has been straight ass — {txt}.",
                           f"🗑️ {name} has been throwing it to the other team — {txt}.",
                           f"🗑️ {name} looks lost out there: {txt}."],
                    "SP": [f"💣 {name} has been getting shelled — {txt}.",
                           f"💣 {name} has been getting lit up: {txt}.",
                           f"💣 Hitters are teeing off on {name} — {txt}."],
                    "G": [f"🥅 {_poss(the_them)} goalie {name} has been giving up a lot of goals — {txt}.",
                          f"🥅 {_poss(the_them)} goalie {name} can't keep the puck out lately: {txt}.",
                          f"🥅 Pucks keep getting past {_possm(the_them)} goalie, {name} — {txt}."] if kn is True else
                         [f"🥅 {name}, expected in net for {the_them} (not confirmed yet), can't keep the puck out lately: {txt}.",
                          f"🥅 {name} — expected to start for {the_them}, not confirmed yet — has been giving up a lot of goals: {txt}."]
                         if kn == "likely" else
                         [f"🥅 {name}, projected to start for {the_them} (not confirmed yet), can't keep the puck out lately: {txt}.",
                          f"🥅 {name} — {_possm(the_them)} projected starter, nobody's confirmed yet — has been giving up a lot of goals: {txt}."]
                         if kn == "projected" else
                         [f"🥅 {name}, in net last time out for {the_them}, can't keep the puck out lately: {txt}.",
                          f"🥅 {name} — {_possm(the_them)} last starter in net — has been giving up a lot of goals: {txt}.",
                          f"🥅 Pucks keep getting past {name}, who was in net last time out for {the_them} — {txt}."]}[role]))
            elif ours_ and mood == "hot":
                out.append(v.say(role + "_hot", {
                    "QB": [f"🎯 {name} has been cooking — {txt}.",
                           f"🎯 {name} can't miss lately — {txt}.",
                           f"🎯 {name} is a beast right now: {txt}.",
                           f"🎯 {name} has been filthy — {txt}.",
                           f"🎯 {name} is locked in: {txt}.",
                           f"🎯 {name} is slinging it — {txt}."],
                    "SP": [f"🔥 {name} has been dealing — {txt}.",
                           f"🔥 {name} has been filthy — {txt}.",
                           f"🔥 {name} is on a roll: {txt}.",
                           f"🔥 Nobody's touching {name} lately — {txt}."],
                    "G": [f"🧱 {_poss(the_us)} goalie {name} has been a brick wall — {txt}.",
                          f"🧱 {name} is standing on his head: {txt}.",
                          f"🧱 Good luck scoring on {name} — {txt}."] if kn is True else
                         [f"🧱 {name}, expected in net for {the_us} (not confirmed yet), has been a brick wall — {txt}.",
                          f"🧱 {name} — expected to start for {the_us}, not confirmed yet — is standing on his head: {txt}."]
                         if kn == "likely" else
                         [f"🧱 {name}, projected to start for {the_us} (not confirmed yet), has been a brick wall — {txt}.",
                          f"🧱 {name} — {_possm(the_us)} projected starter, nobody's confirmed yet — is standing on his head: {txt}."]
                         if kn == "projected" else
                         [f"🧱 {name}, in net last time out for {the_us}, has been a brick wall — {txt}.",
                          f"🧱 {name} — {_possm(the_us)} last starter in net — is standing on his head: {txt}.",
                          f"🧱 Good luck scoring on {name} if he goes again for {the_us} — {txt}."]}[role]))

    # situational spots the engine learned from 10 seasons of games
    rsn = leg.get("reasons") or []
    # (10/21, the owner: "very vague" - every spot line carries the game it's about: the score of the last meeting, of
    #  the blowout, the days off. No score on file = no line; the weight still counts, the words don't guess.)
    if "revenge game" in rsn and last_vs and _line(last_vs[-1], tid).startswith("L"):
        sc = _last_parts(last_vs[-1], tid, pro)[2]        # "27-20"
        #   (11/18, cards_1118: "Revenge game — {us} took a 27-20 loss ..." is the spot said as a knock on OUR side (the
        #    render cut it). The same fact, said as what THEY did and what we owe them.)
        out.append(v.say("revenge", [f"😤 Revenge game — {them} got {us} {sc} the last time these two met. {us} haven't forgotten.",
                                      f"😤 {us} owe {them} one: {them} got {us} {sc} the last time these two met. Payback's coming.",
                                      f"😤 Get-back game for {us} - {them} got {us} {sc} the last time these two met.",
                                      f"😤 {them} got {us} {sc} the last time these two met. {us} been waiting on this rematch."]))
        said.add("revenge game")
    if "letdown spot for the opponent" in rsn and s_theirs and _line(s_theirs[-1], oid).startswith("W"):
        o2, _, sc = _last_parts(s_theirs[-1], oid, pro)   # ("the Jets", "W", "41-10")
        out.append(v.say("letdown", [f"🪤 Letdown spot for {them} — fresh off a {sc} win over {o2}, teams come out flat after that.",
                                      f"🪤 {them} just beat the brakes off {o2}, {sc}. Classic letdown game.",
                                      f"🪤 {them} are riding high off that {sc} over {o2}. That's when teams slip.",
                                      f"🪤 Trap game for {them} after beating {o2} {sc}."]))
        said.add("letdown spot for the opponent")
    if "rolling off a blowout win" in rsn and s_ours and _line(s_ours[-1], tid).startswith("W") \
            and not non_d1(lg, _opp_id(s_ours[-1], tid)):   # (11/4: a non-D1 tune-up is never a 'blowout win' line)
        o2, _, sc = _last_parts(s_ours[-1], tid, pro)
        out.append(v.say("momentum", [f"🚀 {us} just beat the brakes off {o2}, {sc}.",
                                       f"🚀 {us} smacked {o2} {sc} last time out.",
                                       f"🚀 Fresh off a {sc} win over {o2}.",
                                       f"🚀 {_cap(o2)} got their cheeks clapped by {us} last time out, {sc}."]))
        said.add("rolling off a blowout win")
    temp, wind, rain = g.get("wx_temp", ""), g.get("wx_wind", ""), g.get("wx_rain", "")
    if "altitude edge" in rsn and (sm._num(g.get("elev")) or 0) >= sm.THIN_AIR_M:
        out.append(v.say("alt", [f"🏔️ Thin air — {feet(g.get('elev'))} up. {_cap(the_them)} gonna be sucking wind by the second half.",
                                  f"🏔️ Altitude game. {_cap(the_them)} ain't used to breathing up there.",
                                  f"🏔️ Mile-high problems for {the_them}. Legs get heavy fast at that elevation."]))
        said.add("altitude edge")
    if "cold-weather edge" in rsn:
        out.append(v.say("cold_w", [f"🥶 {temp}°F at kickoff. {_cap(the_them)} are a warm-weather squad walking into a freezer.",
                                     f"🥶 It's gonna be {temp}°F. {_cap(the_them)} don't play in this — {the_us} do.",
                                     f"🥶 Cold one ({temp}°F). Welcome to real weather, {the_them}."]))
        said.add("cold-weather edge")
    if "nasty weather helps us" in rsn:
        what = f"{wind} mph winds" if str(wind) not in ("", "0") and float(wind or 0) >= 15 else f"{inches(rain)} of rain"
        out.append(v.say("wx", [f"🌧️ {what} in the forecast. Sloppy game, fewer big plays — that's how a dog steals one.",
                                 f"🌬️ {what}. Ugly weather drags everybody down to the same level.",
                                 f"🌧️ Weather's nasty ({what}). Anything can happen in the slop."]))
        said.add("nasty weather helps us")
    if "opponent's body clock is off" in rsn:
        out.append(v.say("jetlag", [f"🕐 {_cap(the_them)} are playing off their home time zone. Body clock's off.",   # (11/12
                                     f"🕐 {_cap(the_them)} crossed a time zone for this one. Their body clock's off.",   # audit:
                                     f"🕐 Body-clock problems for {the_them} — they're off their home time zone."]))   # one zone)
        said.add("opponent's body clock is off")
    drama_r = next((r for r in rsn if r.startswith("opponent drama:")), None)
    if drama_r and leg.get("their_drama"):
        ev = leg["their_drama"][0]
        kind = ev["kind"]
        hl = str(ev.get("headline") or "").strip()      # (10/15 truth audit: "got a guy wanting out. Locker room's
        #   split" / "Heavy week off the field" said nothing anyone could check - every drama line carries the headline)
        lines = {"coach fired": [f"🧯 {_cap(the_them)} just fired their coach: \"{hl}\"",
                                 f"🧯 Coaching change for {the_them} — \"{hl}\""],
                 "suspension": [f"🧯 {_cap(the_them)} got a suspension hanging over them: \"{hl}\"",
                                f"🧯 Suspension news for {the_them}: \"{hl}\""],
                 "legal trouble": [f"🧯 {_cap(the_them)} got off-field drama going on: \"{hl}\"",
                                   f"🧯 Legal mess around {the_them} this week: \"{hl}\""],
                 "family/personal": [f"🧯 {_cap(the_them)} dealing with some personal stuff: \"{hl}\"",
                                     f"🧯 Heavy week for {the_them} off the field: \"{hl}\""],
                 "illness": [f"🤒 Sickness going around {the_them}: \"{hl}\"",
                             f"🤒 {_cap(the_them)} got guys under the weather: \"{hl}\""],
                 "trade drama": [f"🧯 Trade drama in {the_them}' locker room: \"{hl}\"",
                                 f"🧯 {_cap(the_them)} got a guy wanting out: \"{hl}\""]}.get(kind) if hl else None
        named = [str(n).split(" (")[0] for n in (leg.get("opp_outs") or []) + list((leg.get("key_seen") or {}).keys())]
        if kind == "suspension" and any(n and n.split(" (")[0] in ev.get("headline", "") for n in named):
            lines = None                                 # (10/3: Dylan Stewart's suspension was already in the 🚑 line)
        if lines and someone_elses_story(hl, them, games, lg):
            lines = None                                 # (10/16: another team's player in the headline, not theirs)
        if lines and GOOD_NEWS.search(hl):
            lines = None                                 # (11/18, cards_1118: the Jets card quoted "Back on home ice
            #   after trade request, Kucherov has two assists in Lightning wins" as THEIR drama - a headline about them
            #   winning argues for them; a story that reads like good news for them is never our body line)
        if lines:
            out.append(v.say("drama_" + kind.replace("/", "_").replace(" ", "_"), lines))
        said.add(drama_r)
    out += context_lines(leg, v, us, them, the_us, the_them, g, games)
    if "coming off a bye" in rsn:
        out.append(v.say("bye", [f"🛌 {us} are fresh off a bye — rested and game-planned up.",
                                  f"🛌 {us} had the bye last week. Two weeks to cook up a plan.",
                                  f"🛌 Bye week in the rearview for {us}."]))
        said.add("coming off a bye")
    if "opponent on a short week" in rsn:
        out.append(v.say("short", [f"⏱️ {them} are on a short week. Not much time to prep.",
                                    f"⏱️ Short week for {them} — tired bodies, rushed game plan.",
                                    f"⏱️ {them} barely had time to recover. Short week."]))
        said.add("opponent on a short week")

    # overseas games are always weird
    if str(g.get("intl")) == "1":
        where = g.get("country") or "overseas"
        out.append(v.say("intl", [f"🌍 Game's overseas in {where}. These are always weird — the engine needed extra value to take it.",
                                   f"🌍 International game ({where}). Nobody's really home, everybody's jet-lagged — we only play these with a bigger edge.",
                                   f"🌍 {where} game. Weird spot, so the engine made sure the number's extra juicy."]))

    # home / road
    if str(g.get("intl")) == "1" or _site_side(g, side) is None:
        pass                                            # no real home crowd overseas / at a neutral site (11/4 audit)
    elif side == "home":
        _hm = [x for x in r_ours if x.get("home") == tid and not _neutral(x)]   # (11/13: a neutral site is no home game)
        if len(_hm) >= 2:                                # (10/1: never vague - the home record, or nothing)
            _hr = _record(_hm, tid)
            _w = sum(1 for x in _hm if _line(x, tid).startswith("W"))
            if 2 * _w > len(_hm):                        # (10/27: a losing home record is a knock, not a reason)
                out.append(v.say("home", [f"🏟️ {us} are {_hr} at home this year. Tough out in their own house.",
                                           f"🏟️ {us} take care of home: {_hr} in their building so far.",
                                           f"🏟️ {_hr} at home for {us}. They handle business in their own building.",
                                           f"🏟️ Home cooking for {us} - {_hr} in their own building this season.",
                                           f"🏟️ {us} {vb(us, 'protect', 'protects')} the crib: {_hr} at home.",
                                           f"🏟️ {_hr} in their own building - {us} {vb(us, 'win', 'wins')} more than {vb(us, 'they', 'it')} {vb(us, 'lose', 'loses')} there.",
                                           f"🏟️ At home {us} {vb(us, 'are', 'is')} {_hr}. Ask the teams that came through."]))
            elif 2 * _w < len(_hm):
                v.knock(3, f"{us} are {_hr} at home this year")
            #   (11/18, cards_1118: "1-1 at home this year for Suns" says nothing for our side - a .500 site record is
            #    no line)
    else:
        _rd = [x for x in r_ours if x.get("away") == tid and not _neutral(x)]
        if len(_rd) >= 2:                                # (10/1: "they travel just fine" said nothing - the record does)
            _rr = _record(_rd, tid)
            _w = sum(1 for x in _rd if _line(x, tid).startswith("W"))
            if 2 * _w > len(_rd):
                out.append(v.say("road", [f"🧳 {us} are {_rr} on the road this year. They win in other people's houses.",
                                           f"🧳 Road game, no problem: {us} are {_rr} away from home this season.",
                                           f"🧳 {_rr} on the road for {us}.",
                                           f"🧳 {us} been winning on the road: {_rr}.",
                                           f"🧳 Hostile crowd? {us} {vb(us, 'are', 'is')} {_rr} away from home. They don't care."]))
            elif 2 * _w < len(_rd):                      # (10/27: an 0-3 road record is the knock, never a body line)
                v.knock(3, f"{us} are {_rr} on the road this year")

    # rest
    if ours and theirs:
        d_us, d_them = _days(start, _t(ours[-1]["start"])), _days(start, _t(theirs[-1]["start"]))
        h_us, h_them = [(start - _t(x[-1]["start"])).total_seconds() / 3600 for x in (ours, theirs)]
        if h_them <= B2B_HOURS < h_us:                       # (10/15 truth audit: "Short rest for the Bruins" with two
            #   nights off - a 47-hour gap truncated to 1 "day"; a back-to-back is the next night, by the clock)
            out.append(v.say("b2b", [f"😴 {them} played last night; {us} had {d_us} day{'s' if d_us != 1 else ''} off.",
                                      f"😴 Second night of a back-to-back for {them}. {us} are rested.",
                                      f"😴 {them} on a back-to-back, {us} on {d_us} day{'s' if d_us != 1 else ''} of rest."]))
        elif d_us - d_them >= 2 and d_us <= 10 and not b2b_only(lg):   # (a season-opener gap isn't "rest"; 11/15:
            #   in the every-other-night leagues 4 days off to 2 is no edge - REST_B2B_ONLY)
            gap_d = d_us - d_them
            out.append(v.say("rest", [f"🛌 {us} had {gap_d} more days off than {them}.",   # (10/21: every wording
                                       f"🛌 Rest edge: {us} got {gap_d} extra days to recover.",   # carries the number -
                                       f"🛌 {us} come in with {gap_d} more days of rest.",          # "the more rested
                                       f"🛌 {gap_d} more days off for {us} than {them} — fresh legs.",   # squad" said
                                       f"🛌 {them} had {gap_d} fewer days to get right than {us}.",      # nothing)
                                       f"🛌 {us} got {gap_d} extra days in the tank; {them} didn't."]))

    # pitchers
    if lg == "mlb" and g.get("sp_home") and g.get("sp_away"):   # (10/1 audit: "TBA gets the ball" - both named or no line)
        ps, po = g.get("sp_" + side) or "TBA", g.get("sp_" + other) or "TBA"
        sp_txt = next((t for (o_, m_), (n_, t, *_) in FORM.items() if o_ and m_ is None and n_ == ps and t), None)
        #   (a HOT arm already got his 🔥 line with the numbers; a COLD one gets no hype at all)
        nice = [f"⚾ {x} {sports_lingo.cap1(sp_txt)}." for x in sports_lingo.good(ps, the_them, f"{g['id']}|sp")] \
            if "better starting pitcher" in (leg.get("reasons") or []) and ps != "TBA" and sp_txt else []   # our arm's
        #   the better one - said with his numbers (10/16 truth audit: "Say what you want, Freddy Peralta is HIM. He lives
        #   for spots like this." was the card's whole case for him - no fact = no hype line)
        out.append(v.say("bump", names=(ps, the_them), options=nice + [f"⚾ On the bump: {ps} for {us}, {po} for {them}.",
                                   f"⚾ Pitching matchup: {ps} ({us}) vs {po} ({them}).",
                                   f"⚾ {ps} takes the ball for {us}; {them} go with {po}.",
            f"⚾ {ps} gets the ball for {us} against {po}.",
            f"⚾ It's {ps} for {us}, {po} for {them}."]))

    # injuries
    inj = (injuries or {}).get(lg)
    if inj:
        ours_out, theirs_out = sd.team_injuries(inj, tid, us), sd.team_injuries(inj, oid, them)
        key_them = sd.team_key_out(inj, oid, them, lg) if leg["inj_ok"] else []   # (🧩 11/19: no injury argument when
        #                                                    our side is as short-handed - the Warriors card)
        both = key_them and sd.team_key_out(inj, tid, us, lg)
        if key_them and not both and lg == "mlb":         # baseball: one of their best bats is out (9/29, Judge)
            nm = key_them[0][0]
            out.append(v.say("keyout_bat", [f"🚑 {them} are without {nm} — one of their best bats is on the shelf.",
                                            f"🚑 No {nm} in {_pos(them)} lineup. That's a big bat gone.",
                                            f"🚑 {them} gotta score without {nm}. Their lineup just got a lot less scary."]))
        elif key_them and not both and any(w in str(key_them[0][2]).lower() for w in sd.LONG_OUT):
            pos, nm = _posname(key_them[0][1], lg), key_them[0][0]   # (10/4: Dart on IR read like fresh news -
            out.append(v.say("keyout", [                              #  Winston had started their last two games)
                f"🚑 {nm} is on IR — {them} are still on their backup {pos}.",
                f"🚑 {them} are still without {nm} (IR) — the backup {pos} keeps the job.",
                f"🚑 Still no {nm} for {them} — he's on IR, the backup {pos} goes again."]))
        elif key_them and not both and _stale(games, lg, oid, key_them[0][0], leg["start"]):
            pos, nm = _posname(key_them[0][1], lg), key_them[0][0]   # (10/23: sat their last 2 - old news, not an edge)
            out.append(v.say("keyout", [
                f"🚑 {them} still don't have {nm} — the backup {pos} has started their last 2.",
                f"🚑 No {nm} again for {them}; the backup {pos} gets another start.",
                f"🚑 {nm} has missed {_pos(them)} last 2 — the backup {pos} keeps going."]))
        elif key_them and not both:
            pos, nm = _posname(key_them[0][1], lg), key_them[0][0]
            out.append(v.say("keyout", [f"🚑 {them} are rolling without their starting {pos} ({nm}).",
                                         f"🚑 No {nm} for {them} — that's their starting {pos}.",
                                         f"🚑 {them} are down their starting {pos}, {nm}."]))
        # (the owner, 10/1: one depth guy out is no edge - "is he even a star?" - but "if a team's hella banged up and
        #  got a bunch of injured players, that line is totally good": 3+ out, and 2+ more than us)
        starters_out = sd.team_key_out(inj, oid, them, lg) if leg["inj_ok"] else []   # (the owner, 10/1: "hella banged up" means STARTERS -
        if len(starters_out) >= 3 and len(theirs_out) - len(ours_out) >= 2:   # only players we KNOW are key count;
            #                                                       a depth guy on the report never does)
            out.append(v.say("banged", [f"🚑 {them} are hella banged up ({_names(starters_out)}).",
                                         f"🚑 {_pos(them)} injury list is stacking up: {_names(starters_out)}.",
                                         f"🚑 {them} are missing bodies — {_names(starters_out)}.",
            f"🚑 {them} are dealing with injuries: {_names(starters_out)}.",
            f"🚑 {them} are short-handed ({_names(starters_out)}).",
            f"🚑 {_pos(them)} trainer's room is packed: {_names(starters_out)}."]))
        elif not STORY and not ours_out and not theirs_out and not team_unsure(inj, tid, us) and sd.covered(inj, lg, tid, us):
            # (11/19, the Flyers card: "at full strength" with nobody out on either side says nothing about the game)
            # (11/17: a team the injury data doesn't cover is UNKNOWN, never 'healthy' - no "full squad" line for it)
            # (10/16 truth audit: "Wild questionable: D Zach Bogosian, LW Marcus Foligno" and "Wild have everybody
            #  available" sat on the same card - a side with anyone questionable is never 'full squad')
            out.append(v.say("healthy", [f"✅ {us} are healthy — nobody important sitting.",
                                          f"✅ Full squad for {us}.", f"✅ {us} have everybody available.",
            f"✅ {us} are at full strength.",
            f"✅ Nobody big missing for {us}.",
            f"✅ Nobody on {_pos(us)} injury report. Whole squad's suiting up."]))

    # every "because" on the card is a FACT (10/21, the owner: "very vague and not our lingo" - "they're the better
    # team" / "they're banged up" said nothing): the reasons mapped to what we can show, and the one top fact the
    # card's one-liner and a lean's bottom line hang on
    _kt = [r for r in (sd.team_key_out(inj, oid, them, lg) if inj and leg["inj_ok"] else [])   # (10/23: a key man who sat their last 2
           if not _stale(games, lg, oid, r[0], leg["start"])]                   #  games is never the one-liner's edge)
    _ku = sd.team_key_out(inj, tid, us, lg) if inj else []
    _b2b = bool(ours and theirs) and (start - _t(theirs[-1]["start"])).total_seconds() / 3600 <= B2B_HOURS \
        < (start - _t(ours[-1]["start"])).total_seconds() / 3600
    _gap_d = (_days(start, _t(ours[-1]["start"])) - _days(start, _t(theirs[-1]["start"]))) if ours and theirs else 0
    _bench = None
    if lg == "nba":                                       # (the roster read's bench numbers - a fact for a thin card)
        try:
            import sports_nba_roster as _nr
            _bn = (_nr.cached() or {}).get("bench") or {}
            _bench = (_bn.get(str(tid)), _bn.get(str(oid)))
        except Exception:                                 # noqa: BLE001
            _bench = None
    _pub = public_split(leg)                              # (10/23: the real split is a fact the one-liner can open with)
    _site = _site_rec(r_ours, tid, _site_side(g, side))                  # our home / road record, theirs
    _tsite = _site_rec(r_theirs, oid, _site_side(g, other))
    _rt_w = rec_t if (lg not in SCHEDULE_FAIR or rec_t_cmp or not (rec_u and rec_t)) else (   # (11/16: the one-liner
        rec_t if (lambda a, b: a[0] * (b[0] + b[1]) <= b[0] * (a[0] + a[1]))(                    #  never sells our record
            [int(x) for x in rec_u.split("-")[:2]], [int(x) for x in rec_t.split("-")[:2]]) else None)   # over buy-game L's)
    whyf = why_map(lg, us, them, the_us, the_them, pro, rec_u=rec_u, rec_t=_rt_w, n_hot=n_hot, their_hot=their_hot,
                   n_cold=n_cold, key_them=_kt, key_us=_ku, b2b=_b2b, gap_d=_gap_d if 2 <= _gap_d <= 10 else 0,
                   last_vs=[x for x in last_vs if (start - _t(x["start"])).days <= REVENGE_DAYS],   # (never a 2023 game)
                   tid=tid, oid=oid, s_ours=s_ours, s_theirs=s_theirs, nba_f=nba_f, form=FORM,
                   sp_us=g.get("sp_" + side) if lg == "mlb" else None, g=g, bench=_bench,
                   pub=_pub, site=_site, their_site=_tsite)
    leg["facts"] = top_facts(whyf, rsn)[:3]               # [[ways to say fact 1], [fact 2]...] best first
    leg["fact"] = leg["facts"][0][0] if leg["facts"] else ""
    # the line under the pick is written HERE, before the money / public lines pick their "because" - it gets first
    # call on the wording, and whatever reason it says is `said` (the 💸 / 🤡 lines name a different fact, never the same)
    leg["why_line"] = why_line(leg, v, g, us, them, the_us, the_them, rec_u=rec_u, n_hot=n_hot, rec_t=_rt_w,
                               n_cold=n_cold, gap=gap, form=FORM, key_them=_kt, key_us=_ku,
                               whyf=whyf, fact=leg["fact"], nba_f=nba_f, facts=leg["facts"][0] if leg["facts"] else ())
    # 🗣️ 11/22 THE CARD SELLS THE PICK (the owner: "The breakdowns are short and vague ... the breakdowns basically need
    # to sell our picks why we taking them"): the matchup on the floor off both teams' box scores (sports_card_sell) -
    # the reasons the leg carries said as checkable facts for our side. The strongest one leads the card when the
    # line under the pick was only the fallback fact (a 2-game streak, a last game), the rest open the body.
    sold = []
    try:
        import sports_card_sell as _cs
        if sell_on(g) and leg.get("market") in ("ml", "spread"):   # (a side - never a total's card)
            sold = _cs.sell_facts(leg, v, g, us, them, tid, oid, lg, s_ours, s_theirs,
                                  real=lambda gs_, t_: _real(gs_, t_, lg), e=e, fair=lg in SCHEDULE_FAIR,
                                  fin=fin, nond1=lambda t_: non_d1(lg, t_))
            up = lead_upgrade(leg, sold, us, them, g, side, body=None)
            if up:
                sold = [s_ for s_ in sold if s_[0] != up[1]]
                leg["why_line"], leg["why_key"] = up[0], "w_sell"
    except Exception:                                     # noqa: BLE001 - the sell lines never break a card
        sold = []
    leg["sold"] = [_cs_sig(s_[0]) for s_ in sold if s_[1]] + ([_cs_sig(leg["why_line"])] if leg.get("why_key") == "w_sell" else [])
    _wl = str(leg["why_line"] or "").lower()
    said.update(r for r, ways in whyf.items() if any(c.lower() in _wl for c in _lst(ways)))
    said.update(r for r, em in WHY_EMOJI.items() if _wl.startswith(em))
    if nba_f:                                             # 🏀 last season's facts (after the why line: it has first call)
        out.append(v.say("nba_last", nba_lines(us, them, nba_f, _wl)))
        said.add("the stronger team")

    # a starting QB/goalie out: the line moved for the INJURY, not sharp money - say that, never "sharps"/"clowns"
    op, now = sm._int(g.get(f"ml_{side}_open")), sm._int(g.get(f"ml_{side}"))
    op_o_fb = None
    if lg in ("nfl", "ncaaf"):                            # (10/1: a football "open" is the summer look-ahead line - a
        try:                                              # move from it is the season, not money. The move is from our
            import sports_early as _se                    # own first fair price this week, or there's no move line)
            ff = _se.first_fair(g["id"], _se.ready(_se._schedule(games), g))
        except Exception:                                 # noqa: BLE001
            ff = None
        op = (ff[0] if side == "home" else ff[1]) if ff else None
        op_o_fb = (ff[1] if side == "home" else ff[0]) if ff else None
    key_us = sd.team_key_out(inj, tid, us, lg)
    key_any = key_us or sd.team_key_out(inj, oid, them, lg)
    key_them2 = sd.team_key_out(inj, oid, them, lg) if inj else None
    if coherent_on(g):                                   # 🧩 11/19: our own man out is said once, in the card's 🚑
        key_them2 = None                                 #  header - never "both teams are down their starting QB" in
        #                                                   the write-up (the owner: "I don't want bad shit in the breakdowns")
    if key_us and key_them2 and lg == "mlb":
        nm, nm2 = key_us[0][0], key_them2[0][0]
        out.append(v.tag(v.say("keyout_both_bat", [
            f"🚑 Both lineups are missing a big bat — no {nm} for {the_us}, no {nm2} for {the_them}. Still our side.",
            f"🚑 Both sides are missing someone: {nm} ({the_us}) and {nm2} ({the_them}). The price already has it - we still like {the_us}."],
            must=True), "neutral"))
    elif key_us and key_them2:                            # both teams down a starter: one plain line, not two
        pos, nm, nm2 = _posname(key_us[0][1], lg), key_us[0][0], key_them2[0][0]
        mv = ""                                           # (10/23, the owner: no line-move talk in the write-up)
        out.append(v.tag(v.say("keyout_both", [
            f"🚑 Both teams are down their starting {pos} — {nm} is out for {the_us}, {nm2} for {the_them}.{mv} We still riding with the algorithm.",
            f"🚑 Backups on both sides tonight: no {nm} for {the_us}, no {nm2} for {the_them}.{mv} The numbers still say this the side.",
            f"🚑 Neither team has its starting {pos} — {nm} ({the_us}) and {nm2} ({the_them}) are both out.{mv} We still like {the_us}."],
            must=True), "neutral"))
    elif key_us and lg == "mlb":                          # our best bat is out: the card's ONE risk line (10/27)
        v.knock(10, f"{key_us[0][0]}, one of {_pos(the_us)} best bats, is out")
    elif key_us:                                          # our starter out: the biggest knock there is - it posts as the
        pos, nm = _posname(key_us[0][1], lg), key_us[0][0]   # ⚠️ line, never as a body line (10/27)
        if not _stale(games, lg, tid, nm, leg["start"]):   # (11/18: a starter who sat our last 2 is old news - the
            v.knock(10, f"{nm} is out and {the_us} roll with the backup {pos}")   #  results already hold it; no knock)
    # (10/23, the owner: "we don't need to talk about the line moving. We've proved that when the line moves, it doesn't
    #  even really matter." The 💰 money lines ('+200 → +180') and the 💸 'the line moved toward them' warning are GONE
    #  from the write-up - the move stays a weight in the engine, the card never talks about it.
    #  The 💸 LINE ALERT on a posted card (sports.py) is a separate warning and stays.)

    # who's betting who: the real splits (the same numbers Google shows) - unless the one-liner already said them
    sp_ = public_split(leg) if PUBLIC_CARD else None     # (10/25: a fact - said unless the one-liner has the number;
    #                                                      11/12: never on the card - PUBLIC_CARD)
    if sp_ and (f"{sp_[0]}%" in str(leg.get("why_line") or "") or f"{100 - sp_[0]}%" in str(leg.get("why_line") or "")):
        sp_ = None
    mk = {"ml": "the moneyline", "spread": "the spread", "total": "the total"}.get(leg.get("market"), "the moneyline")
    #   (11/10: a friend read "the public ate this time on the Lions" when 61% of the SPREAD bets were on the Vikings -
    #    the card's split was the MONEYLINE's (68% Lions). Every splits line now names which bets it means.)
    if sp_ and sp_[1] is None:                            # bets % only (Yahoo's backup has no money %): say that plain
        t = sp_[0]
        crowd = the_us if t >= 50 else the_them
        out.append(v.tag(v.say("splits_y", [
            f"📊 {max(t, 100 - t)}% of the bets on {mk} are on {crowd}." + (" We with 'em on this one." if t >= 50 else " We on the other side."),
            f"📊 The public's got {max(t, 100 - t)}% of the tickets on {crowd} on {mk}." + (" Same side as us." if t >= 50 else " Not us."),
            f"📊 {crowd} got {max(t, 100 - t)}% of the bets on {mk}." + (" Popular pick, right pick." if t >= 50 else " We fading that.")]), "neutral"))
        sp_ = None
    if sp_:
        t, m = sp_
        # (10/21, the owner: the splits lines were filler - "public's usually wrong, not this time", "for once the
        #  the crowd lines". The splits don't pick winners (the 10/7 study, dead), so the card just says who's on
        #  who when it's lopsided - a 40-60 split says nothing and is dropped)
        if t <= 35:
            out.append(v.tag(v.say("splits_f", [
                f"📊 {100 - t}% of the bets and {100 - m}% of the money on {the_them} on {mk}. We on the other side.",
                f"📊 The public's on {the_them} on {mk}: {100 - t}% of the bets, {100 - m}% of the money. Not us.",
                f"📊 {_cap(the_them)} got {100 - t}% of the tickets on {mk} ({100 - m}% of the money). We got {the_us}.",
                f"📊 Everybody and they mama on {the_them} on {mk} ({100 - t}% of the bets). We riding {the_us} anyway.",
                f"📊 {100 - t}% of the {mk[4:]} bets on {the_them}. Let the public have 'em."]), "neutral"))
        elif t >= 65:
            out.append(v.tag(v.say("splits_w", [
                f"📊 {t}% of the bets and {m}% of the money on {the_us} on {mk}. Same side as the public on this one.",
                f"📊 The public's with us on {mk}: {t}% of the bets, {m}% of the money on {the_us}.",
                f"📊 {_cap(the_us)} got {t}% of the tickets on {mk} ({m}% of the money). The whole hood eating with this one.",
                f"📊 Everybody and they mama on {the_us} on {mk}: {t}% of the bets, {m}% of the money."]), "neutral"))

    # the public: fading them or riding with them
    pub = public_side(leg, g)
    pub_r = next((r for r in leg.get("reasons") or [] if r in whyf and r not in said), None)
    whys_pub = _lst(whyf[pub_r]) if pub_r else [NO_WHY]
    _po = sm._int(g.get(f"ml_{other}"))
    _pu = sm._int(g.get(f"ml_{side}"))
    if sp_ or public_split(leg):
        pass                                          # the real splits already said it (with the numbers)
    # (10/22, the owner: "these breakdowns suck" - with no split data the 🤡 / 🤝 lines only guessed at the public
    #  from the price (sheep / casuals lines): no data, no line)

    # 📚 THE REST OF THE FACTS (10/25, the owner on the 3-line Canucks card: "very vague ... we need it to be thorough, in
    # our lingo ... this goes for every pick"): everything the engine computed for the leg that the lines above didn't
    # say - both last games with the scores, the skids, both home / road records, the rest days, the trip, who's out on
    # BOTH sides, the goalies / QBs with their numbers, the points lately, puck luck. Each only from real data.
    added = more_facts(leg, v, g, us, them, the_us, the_them, pro, tid, oid, start, s_ours, s_theirs, r_ours, r_theirs,
                       ours, theirs, FORM, inj, lg, side, other, out, heat, heat_t, last_vs, e=e)
    out += added
    try:                                                  # (11/23: the night they were a big favorite and lost is one
        _sc = lambda s_: re.search(r"lost (\d+-\d+)", s_[0]) if s_[2] == "sched_fav" else None   # noqa: E731  game -
        sold = [s_ for s_ in sold if not (_sc(s_) and any(   # never said again when the body already has that score)
            _sc(s_).group(1) in str(x) or "-".join(reversed(_sc(s_).group(1).split("-"))) in str(x)
            for x in out + [str(leg.get("why_line") or "")]))]
    except Exception:                                     # noqa: BLE001
        pass
    if sold or sell_on(g):                                # 🗣️ 11/22: the reason-backed lines open the body
        try:                                              # (and a fallback line under the pick gives way to the game
            up = lead_upgrade(leg, sold, us, them, g, side, body=out) if leg.get("why_key") != "w_sell" else None
            if up:                                        #  these two already played / the best matchup stat)
                sold = [s_ for s_ in sold if s_[0] != up[1]]
                out = [x for x in out if x != up[1]]
                added = [x for x in added if x != up[1]]
                leg["why_line"], leg["why_key"] = up[0], "w_up"
        except Exception:                                 # noqa: BLE001
            pass
        if any(s_[2] == "sched_l" for s_ in sold) or (str(leg.get("why_line") or "").startswith("🧭") and re.search(rf"(?:beat|got) {re.escape(us)}", str(leg.get("why_line")))):
            out = [x for x in out if not str(x).startswith("⚖️")]   # (11/23: the 🧭 line names who beat us - once)
        out[0:0] = [s_[0] for s_ in sold]
        added += [s_[0] for s_ in sold]                   # (fact lines: never shaped out)
    # ⚠️ THE ONE RISK LINE (10/27, the owner: "there's a lot of facts that support the opposing team"): every fact that
    # favors the other side went into v.knocks instead of the body; the single biggest posts here, framed as the risk,
    # right before the bottom line. Nothing else on the card argues for them.
    #   🚫 11/19 (the owner: "I don't want bad shit in the breakdowns"): from NO_KNOCK_FROM no card carries the risk line -
    #   the facts against our side still weigh in the read and stay out of the write-up (v.knocks is kept for the checks).
    risk = risk_line(v, us, them, the_us) if (g.get("start") or "")[:10] < NO_KNOCK_FROM else ""
    if risk:
        out.append(risk)

    # bottom line - in our lingo, never the book-vs-us odds talk (the owner, 9/29: that don't make sense), and never the
    # same wording twice on a board (a big pool per kind; the Voice skips any wording already used)
    bet = f"{us} {leg['line']:+g}" if leg["market"] == "spread" else us
    price = f"{bet} ({_am(leg['odds'])})"
    pct = round(100 * leg["p"])                                          # ONE number, ours, said plain - that's fine
    _need = 1 / leg["dec"] if leg.get("dec") else None                    # (10/1, the owner: never vague - the bottom
    try:                                                                 # line says the real numbers: the engine's
        import sports as _sp                                             # own read vs what the price needs)
        _own = _sp.read_of(leg) or leg["p"]
    except Exception:                                                    # noqa: BLE001
        _own = leg["p"]
    import sports_owner_lingo as _ol                                    # (10/17: Rice's card said "Rice at 61%" -
    wp = f"{round(100 * _own)}%" if _own > _ol.SHOW_PCT_OVER / 100 else ""   # the owner 10/7: NO win % ever)                 # (10/1, the owner: "50 out of 100, the price
    pos = f" {us} at {wp}." if wp else ""                                # needs 48" is jargon - plain words: does our
    _fact = "Our read beats this price." if not _need or _own > _need else "The price is too steep for units."
    if leg.get("floor_score") is not None and not leg.get("is_lean") and leg.get("tier") != "lock" \
            and _need and _own > _need + 0.03:                  # (10/28, the Bucks +270: the read clears the price by
        #   (10/29, the owner: "the lingo still sucks" - no "dog check" / "dog score" on a card: plain words for what it
        #    is - every angle we grade a dog on - and the closers don't all end "thin edge, half a unit, tread light")
        out.append(v.say("bottom_floor_over", [                 #  5+ points - "close to even" was false)
            f"✅ Bottom line: {price}. The book's selling {us} short - that price pays like they got no shot, and our read says they live. Half a unit on it.",
            f"✅ Bottom line: {price}. Too much plus money for a team this live. Half a unit on the upset.",
            f"✅ Bottom line: {bet} at {_am(leg['odds'])}. That number's too big and {us} {vb(us, 'grade', 'grades')} out best of every dog on the slate. Half a unit.",
            f"✅ Bottom line: {price}. The books got {us} priced like a team that can't win - we don't see that. Half a unit, scared money don't make no money."]) or
                   _short(v, price, False, "Our read beats the price."))
    elif leg.get("floor_score") is not None and not leg.get("is_lean") and leg.get("tier") != "lock" \
            and ((leg.get("floor_score") or 0) < FLOOR_ANGLES or dog_angles(leg) <= 0):   # 💰 10/30 weekend sweep: a floor dog the dog score has UNDER
        #   zero (the Dolphins +260 at -1.9 on the 11/01 preview) is just the best dog LEFT on a thin slate - "the dog
        #   angles back it" / "every angle likes them" was false there. The closer says what it is.
        out.append(v.say("bottom_floor_low", [
            # 🧩 11/19 (the owner on the Warriors card, whose closer ran the pick down - sports_card_check.SELF_KNOCK has
            #  the words): the bottom line never knocks our own pick - a ½u says it's a smaller bet in plain words
            f"✅ Bottom line: {price}. Half a unit on {us}.",
            f"✅ Bottom line: {price}. Plus money on {us} - half a unit.",
            f"✅ Bottom line: {bet} at {_am(leg['odds'])}. Half a unit.",
            f"✅ Bottom line: {price}. Half-unit play on {us}."]) or
                   _short(v, price, False, "Half a unit."))
    elif leg.get("floor_score") is not None and not leg.get("is_lean") and leg.get("tier") != "lock":   # 💰 10/27: a floor
        out.append(v.say("bottom_floor", [                                # play - the dog angles put it up, not the price
            #   (11/22, the owner on the Wizards +170 ½u: "We can't say best dog on the slate but it's a half unit makes no
            #    sense. Half unit is a thin edge tread lightly" - a ½u play says it's a thin edge, never "the best dog")
            f"✅ Bottom line: {price}. Thin edge - half a unit. Tread lightly.",
            f"✅ Bottom line: {price}. Half a unit on {us}. Thin edge, tread lightly.",
            f"✅ Bottom line: {bet} at {_am(leg['odds'])}. Thin edge - go light, half a unit.",
            f"✅ Bottom line: {price}. Small edge, small bet - half a unit."]) or
                   _short(v, price, False, "The dog angles like it."))
    elif leg.get("near_price"):                                          # the always-a-Lock backup (the owner, 10/1):
        out.append(v.say("bottom_near", [                                # the likeliest winner, priced about right -
            f"✅ Bottom line: {price}. Our Lock today, priced about right - small bet, not a big one.",
            f"✅ Bottom line: {price}. We like {us} to win; the price is close to fair, so we keep it small.",
            f"✅ Bottom line: {price}. Fair price on a side we trust - small bet.",
            f"✅ Bottom line: {us} to win, {price}. Price is about where we got it - ride it light."]) or
                   _short(v, price, True, ""))                           # (small, honest - never "value")
    elif _need and _own <= _need and leg.get("is_lean") is False and leg.get("tier") in ("value", "lock"):
        #   (11/11 sweep: a UNIT play whose read sits at / under its price - the NBA favorite play rides its study weights
        #    on a read that starts at the books' number, the forced ⭐ too. The Celtics -124 1u card of 11/10 closed
        #    "Could go either way. Celtics by a nose - a lean." - "a lean" / "No units" on a play with a unit on it.)
        out.append(v.say("bottom_unit_fair", [
            f"✅ Bottom line: {price}. {us} the side tonight.",      # (11/20, the Niagara +2.5 card: "because of
            f"✅ Bottom line: {price}. We on {us}.",                 #  the spot, and the units say how much" said nothing,
            f"✅ Bottom line: {bet} at {_am(leg['odds'])}. That's the bet."]) or   # "fair price" ran it down)
                   _short(v, price, False, ""))
    elif _need and _own <= _need and COIN_FLIP[0] <= _own < 0.56 and leg.get("market") == "ml" \
            and _sb_mod.coin_side(leg, _own):                                # (11/13: never at a -148 price / a 60% win %)
        #   (10/1, the owner: "we like the Kraken,
        out.append(v.say("bottom_c", [                                   # just not at this price" at -108 makes no
            f"✅ Bottom line: {price}. Coin flip game - {us} by a hair. No units.",                               # sense:
            f"✅ Bottom line: {price}. Close to 50-50 for us, {us} a hair better. Just a lean.",                  # the real
            f"✅ Bottom line: {price}. Near a coin flip - {us} {vb(us, 'are', 'is')} the side, but we ain't putting money on it.",  # reason is
            f"✅ Bottom line: {price}. Could go either way. {us} by a nose - a lean."]) or                       # a coin flip)
                   _short(v, price, False, "Close to a coin flip on our read."))
    elif _need and _own <= _need:                                        # read beat the price or not; ONE % only
        _f = card_fair(leg, _own)                                        # (10/22: our number vs theirs - the reason)
        out.append(v.say("bottom_n", ([f"✅ Bottom line: {price}. We make {us} {_f}; the book wants {_am(leg['odds'])}. Lean only.",
                                       f"✅ Bottom line: {price}. Our number's {_f} - at {_am(leg['odds'])} there's no money in it. A lean."]
                                      if _f and leg.get("market") == "ml" else []) + [   # when it's over 55. Never "value" on a read
            f"✅ Bottom line: {price}. Right side, but the price is too steep for units - just a lean.",   # under it)
            f"✅ Bottom line: we like {us}, not the price. A lean, no money on it.",
            f"✅ Bottom line: {price} costs too much for what we see. Lean only.",
            f"✅ Bottom line: {us} {vb(us, 'are', 'is')} the side - the payout just ain't worth the juice. A lean.",
            f"✅ Bottom line: good side, bad number. {price} is a lean, no units.",
            f"✅ Bottom line: {price}. We'd ride {us}, but not with money at this price.",
            f"✅ Bottom line: {us} {vb(us, 'are', 'is')} our side; {price} is too rich for units. Lean it."]) or _short(v, price, False, _fact))
    elif leg.get("tier") == "lock":                                      # a lock: our whole chest, never a hedge
        out.append(v.say("bottom_lo", OWNER_LOCK(price, us, {**leg, "_read": _own if card_fair(leg, _own, beat=True) else None})) or v.say("bottom_l", [
            f"✅ Bottom line: {price}. The engine likes {us} more than the books do. Lock it in.",
            f"✅ Bottom line: {price} — this price is cheaper than it should be. We're all in.",
            f"✅ Bottom line: {price}. The books got this one priced wrong. Stamp it.",
            f"✅ Bottom line: {price}. Our read beats this number. Say less.",
            f"✅ Bottom line: {price} — the value's on our side.{pos} Locked in.",
            f"✅ Bottom line: {price}.{pos} The price didn't catch up to our read. Tap in.",
            f"✅ Bottom line: {price}. We'd lay this all day - the number's in our favor.",
            f"✅ Bottom line: {price}. The side we trust most today, at a price that pays. That's money."]) or _short(v, price, True, _fact))
    elif fair_same(leg, _own):                                           # (11/11 sweep: the Bruins -142 / -142 card said
        out.append(v.say("bottom_even", [                                # "-142 is extra money" - the same number is no gift)
            f"✅ Bottom line: {price}. A fair price on the side we like. Small bet.",                        # (11/19: never
            f"✅ Bottom line: {price}. The side we like at a fair price - keep it light.",                   #  our number)
            f"✅ Bottom line: {price}. Fair price. Small bet on the side we trust."]) or
                   _short(v, price, False, "A fair price on our side."))
    else:
        out.append(v.say("bottom_so", OWNER_PLAY(price, us, card_fair(leg, _own, beat=True), leg.get("odds"))) or v.say("bottom_s", [
            f"✅ Bottom line: {price}. The engine gives {us} a better shot than this price does. That's the bet.",
            f"✅ Bottom line: {price} pays more than it should. Tap in.",
            f"✅ Bottom line: {price}. The books are sleeping on {us}. We finna see.",
            f"✅ Bottom line: {price}. Our read beats the number. Riding {us}.",
            f"✅ Bottom line: {price}. That number's too generous. Get in.",
            f"✅ Bottom line: {price}. {us} {vb(us, 'are', 'is')} better than this number says. Ride it.",
            f"✅ Bottom line: {price}.{pos} The books are giving us a gift on {us}.",
            f"✅ Bottom line: {price}. Books got this one wrong. We on {us}."]) or _short(v, price, False, _fact))
    import sports_card_guard                              # 🛡️ every line passes the owner's checks before it posts
    leg["why_line"] = sports_card_guard.one(leg["why_line"], lg, us, them)   # (10/30: the verbs agree with both names)
    lines = sports_card_guard.clean([x for x in out if x], lg, us, them)
    _wl = str(leg.get("why_line") or "")
    _scores = lambda t: set(re.findall(r"\b\d{1,3}-\d{1,3}\b", str(t)))
    for em, body_em in SAME_STORY:                        # (10/3: the record said twice - the headline already has it;
        if _wl.startswith(em):                            #  10/21: the same for the streak, the blowout, the rest, the
            lines = [x for x in lines if not (str(x).startswith(body_em) and   # last meeting - said once, under the pick;
                                              (body_em != "📅" or _scores(x) & _scores(_wl) or not _scores(x)))]
            #   (10/25: a 📅 line that carries a score the one-liner didn't - our last game - stays: the owner wants both)
    try:                                                  # 🚑 11/19: the named men the body left to the line under
        _ld = (named_out_ways(leg, g, them, them) or (None, []))[1]   # the pick - if that line didn't say them, the body does
        if _ld and not all(w in _wl for w in _ld):
            lines.insert(0, f"🚑 {them} are without {_and(_ld)}.")
    except Exception:                                     # noqa: BLE001
        pass
    if rec_u and rec_u in _wl:                            # (the why line carries the record: no 📋 line too)
        lines = [x for x in lines if not str(x).startswith("📋")]
    try:                                                  # 👍 11/18 (cards_1118): nothing said twice - see no_repeats
        _known = set()
        for x in list((s_ours or [])[-5:]) + list((s_theirs or [])[-5:]) + list(last_vs or []):
            try:
                _known.add(tuple(sorted((int(x["home_score"]), int(x["away_score"])), reverse=True)))
            except (KeyError, TypeError, ValueError):
                pass
        lines = no_repeats(lines, _wl, _known, [r for r in (rec_u, rec_t) if r], us)
    except Exception:                                     # noqa: BLE001 - the write-up never breaks on its own tidy-up
        pass
    # 🧱 11/18 THE REFILL (the owner, on the Nuggets card after the knocks were cut: "Now you just took out the lines that I
    # said were trash, and it's just short and fucking vague ... a permanent bug"): a cut is never the end of it. A card
    # under its floor (FLOOR_UNIT / FLOOR_LEAN) is refilled with REAL facts for our side the engine holds and the card
    # hasn't said - our top scorer with his numbers, our scoreboard lately and on the year, theirs when it's bad, the
    # price in plain words. Never filler, never a knock; when the files have nothing more, the card stays short and
    # the log says so.
    try:
        _fl = FLOOR_LEAN if (leg.get("tier") == "lean" or leg.get("is_lean")) else FLOOR_UNIT
        _fl += REFILL_PAST                                # (one past the floor: 6-9 is the owner's range, and a cut on the
        if not str(leg.get("why_line") or "").strip():    #  page lands on a card with room; the card's best line becomes
            _fl += 1                                      #  the one-liner below and leaves the body)
        _nf = lambda ls: counted(ls, leg)                 # noqa: E731 (what the page counts - never the 🚑 chip's names)
        _pool = fill_facts(leg, v, g, us, them, tid, oid, lg, s_ours, s_theirs, r_ours, r_theirs,
                           " ".join(str(y) for y in lines) + " " + _wl, _own, fin, elo.get(lg))
        _spare = []
        _at = next((i for i, x in enumerate(lines) if str(x).startswith(("⚠️", "✅ Bottom", "🟡", "🔒"))), len(lines))
        for x in _pool:
            if not x or x in lines:
                continue
            if _nf(lines) >= _fl:
                _spare.append(x)                          # (not needed today: it rides along - a cut on the page later
                continue                                  #  pulls it in, sports_card_check.refill)
            lines.insert(_at, x)
            _at += 1
            added.append(x)                               # (a fact line: never shaped out below)
            v.fill.add(x)                                 # (and never the one-liner while a first-hand line can lead)
        leg["spare"] = _spare[:SPARE_MAX]
    except Exception:                                     # noqa: BLE001
        pass
    if day_game(start):                                   # (10/4, the owner's queue: "tonight" on a 10 AM game)
        leg["why_line"] = not_tonight(leg["why_line"])
        lines = [not_tonight(x) for x in lines]
    if len(lines) > 2:
        import random
        rnd = random.Random(f"{g['id']}|{start:%Y-%m-%d}|{side}|shape")
        body, bottom = lines[:-1], lines[-1]
        floor = FLOOR_LEAN if (leg.get("tier") == "lean" or leg.get("is_lean")) else FLOOR_UNIT
        keep = max(floor, len(body) - rnd.randint(0, 2))      # (10/25: thorough - a card only loses a line or two past
        #                                                         the floor; the floor is the owner's, never padded to)
        must = {i for i, x in enumerate(body) if x[:1] not in SHAPEABLE or x in added}   # (10/25) every FACT line stays
        #   - the owner wants the whole picture, not a sample of it; only the talk (news, drama, weather) gets shaped
        #   (10/21: and the fact lines - the pitching matchup, last season's hoops facts - never shaped out)
        drop = [i for i in range(len(body)) if i not in must]
        rnd.shuffle(drop)
        gone = set(drop[:max(0, len(body) - keep)])
        body = [x for i, x in enumerate(body) if i not in gone]
        rnd.shuffle(body)
        # (10/27) the card is OUR case: the lines for our side first, the even-handed context after, the one ⚠️ risk
        # line last - right before the bottom line
        rank = {"us": 0, "neutral": 1, "risk": 2}
        body.sort(key=lambda x: rank.get("risk" if str(x).startswith("⚠️") else v.dirs.get(x, "us"), 0))
        lines = body + [bottom]
    short_floor = FLOOR_LEAN if (leg.get("tier") == "lean" or leg.get("is_lean")) else FLOOR_UNIT
    if not str(leg.get("why_line") or "").strip():        # (10/27: the Blues lean posted with NO line under the pick -
        lean_ = (leg.get("is_lean") or leg.get("tier") in ("lean", "strong")) and not _no_leans()   # no reason matched a fact; the card's
        top = lead_line(lines, v, us, lg)                 #  best line FOR US leads instead (10/29: never a line that
        if top:                                           #  argues for the other side - the Hawks lean led with "2-3 for
            _tails_ = [f"We lean {us}.", f"Lean {us}.", f"{us} if you're playing it."] if lean_ else \
                [f"{us} the side.", f"We on {us}.", f"Give me {us}.", f"Riding {us}."]   # (11/4: one tail on every card)
            leg["why_line"] = f"{str(top).rstrip()} " + _tails_[sum(map(ord, f"{g['id']}|{side}")) % len(_tails_)]   # Hawks,
            if True:                                      #  (11/18, cards_1118: the line is the one-liner now - it never
                lines = [x for x in lines if x is not top]   #  sits in the body too, however short the card runs)
    try:                                                  # 🚫 11/19: no line claims our price; the bottom line says the
        lines = story_close(lines, leg, us, them, g, side)   #  pick, the price and the matchup reason
    except Exception:                                     # noqa: BLE001
        pass
    try:                                                  # 🧩 11/19 EVERY CARD MAKES SENSE AS A WHOLE (cards_1119b)
        lines = whole_card(lines, leg, v, us, lg, g, side, games)
    except Exception:                                     # noqa: BLE001 - the write-up never breaks on its own tidy-up
        pass
    if len(lines) - 1 < short_floor:                      # (never padded with filler: the log says the facts ran out)
        print(f"BREAKDOWN SHORT: {us} vs {them} ({lg}) has {len(lines) - 1} fact lines, floor {short_floor} - "
              f"games on file: ours {len(s_ours)}, theirs {len(s_theirs)}", flush=True)
    return lines


SINGULAR = {"Wild", "Heat", "Magic", "Jazz", "Thunder", "Lightning", "Avalanche", "Kraken", "Mammoth", "Fire", "Sky",
            "Fever", "Storm", "Mercury", "Liberty", "Dream", "Sun", "Lynx", "Galaxy", "Crew", "Union", "Fury",
            "Texas", "Kansas", "Arkansas", "Illinois", "Miss", "UMass", "Mass", "Massachusetts", "Athletics"}
#   (10/30: the school names that end in an s - Texas, Kansas, Arkansas, Illinois, Ole Miss, UMass - read as plurals
#    and got "Texas are"; they take the singular like every school)


def vb(team, plural, singular):
    """The verb for a team name: 'the Wild holds', 'the Bruins hold' (the owner, 10/27: "it says Wild hold teams to
    this - it should say holds with an S"). A one-word mascot that isn't a plural (Wild, Heat, Jazz ...) or a school /
    city name (Delaware, Western KY) takes the singular."""
    t = str(team or "").strip()
    last = t.split()[-1] if t else ""
    if t in SINGULAR or last in SINGULAR or (last and not last.endswith("s")):
        return singular
    return plural


SHAPEABLE = "📣🧯🤒🪤😤🚀🏔🥶🌧🌬🦓🪑🚨🌍"   # the talk lines a card may skip; a fact line never (10/25)
HOT_MIN = 3                      # (10/29) a "heater" / "rolling" line needs 3+ straight wins - the 10/29 Blue Jackets card
#                                  called two teams on 2 straight "rolling"; at 2 the record line says the last score instead
FLOOR_UNIT, FLOOR_LEAN = 6, 5    # (10/25, the owner) fact lines a unit pick / a lean posts with, when the facts exist


def _real(gs, tid, lg):
    """🏀 11/22 board check: a team's games WITHOUT its non-D1 tune-ups (college hoops; every other league as is). The
    Robert Morris +102 card said "Over their last 3 Robert Morris win by 6 a game (74 for, 68 against)" - a 94-45 win
    over Capital (a non-D1 school) and two double-digit losses; against D1 teams they'd lost every game. A scoreboard
    "lately" line is read on real games only - a tune-up is never dressed as form (the owner, 11/4: Mount Marty)."""
    if lg != "ncaab":
        return gs
    return [x for x in gs or [] if not non_d1(lg, _opp_id(x, tid))]


FORM_D1 = True               # 🏀 11/24 board check (the ⭐ Illinois St +100 card: "80+ points for Illinois St in 3 of their last 5" and
#   "outscored teams 207 to 167 in the first half over their last 5" - one of the five was a 123-48 win over Eureka, a
#   non-D1 school, 65 of the 207 first-half points): from breakdown VERSION 87 a college hoops team's big nights and
#   its halves are counted on Division I games only, like every other "lately" line (_real, 11/22). False = as before.


def _form(gs, tid, lg):
    """The games a college hoops form count reads: no non-D1 tune-ups (FORM_D1; every other league as is)."""
    return _real(gs, tid, lg) if FORM_D1 else gs


def _pts3(gs, tid, n=3, dec=0):
    """(scored, allowed) a game over the team's last n games on file, rounded - or None. dec=1: one decimal (hockey /
    baseball - 11/17: whole goals said "Stars average 4 for / 4 against ... Blue Jackets 3 for / 3 against", nothing)."""
    last = (gs or [])[-n:]
    if len(last) < 2:
        return None
    f = a = 0
    for x in last:
        home = x["home"] == tid
        f += int(x["home_score"] if home else x["away_score"])
        a += int(x["away_score"] if home else x["home_score"])
    if dec:
        return round(f / len(last), dec), round(a / len(last), dec), len(last)
    return round(f / len(last)), round(a / len(last)), len(last)


def _body(out):
    return " ".join(str(x) for x in out if x).lower()


def _sv(txt):
    """The save % in a goalie's form line ('a 0.868 save % ...') -> 0.868, or None."""
    m = re.search(r"(0\.\d{3}) save", str(txt or ""))
    return float(m.group(1)) if m else None


def _qb_nums(txt):
    """(TDs, picks, yards) from a QB's form line ('8 TDs, 3 picks and 709 yards ...'), or None."""
    m = re.search(r"(\d+) TDs?, (\d+) picks? and ([\d,]+) yards", str(txt or ""))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3).replace(",", ""))) if m else None


def _last_n(gs, tid, n=5):
    """(wins, losses) over the team's last n games on file - only with the full n."""
    last = (gs or [])[-n:]
    if len(last) < n:
        return None
    w = sum(1 for x in last if _line(x, tid).startswith("W"))
    lo = sum(1 for x in last if _line(x, tid).startswith("L"))
    return w, lo


def _per_game(gs, tid):
    """(scored, allowed) a game over a season's games, one decimal (hockey) or whole (the rest)."""
    if not gs:
        return None
    f = a = 0
    for x in gs:
        home = x["home"] == tid
        f += int(x["home_score"] if home else x["away_score"])
        a += int(x["away_score"] if home else x["home_score"])
    return f / len(gs), a / len(gs)


SEASON_NOW_GAMES = 3       # 🧊 11/27 (the 11/26 Chiefs +130 card: "Bills are leaking 21 points a game this season" - the Bills
SEASON_NOW_MIN = 6         #   had given up 6, 12 and 9 in their last three and the game ended 13-10): a season scoreboard
SEASON_NOW_GAP = {"nhl": 1.0, "mlb": 1.0}   # comparison argues for us only while it is still who THEY are - when their
SEASON_NOW_PTS = 6.0       #   last SEASON_NOW_GAMES games (of SEASON_NOW_MIN+) run this much BETTER than their own season
#                              number (points; goals / runs in hockey / baseball) the line is not written. Ours is untouched.


def season_still(gs, tid, idx, lg):
    """Is the other team's season number (idx 0 = scored, 1 = allowed) still what it has been doing? False = its last
    SEASON_NOW_GAMES games are better than the season by the league's gap (it allows that much less / scores that
    much more) - the season line would sell a team that isn't there any more. Under SEASON_NOW_MIN games = True."""
    if not gs or len(gs) < SEASON_NOW_MIN:
        return True
    yr, now = _per_game(gs, tid), _per_game(gs[-SEASON_NOW_GAMES:], tid)
    gap = SEASON_NOW_GAP.get(lg, SEASON_NOW_PTS)
    return (yr[1] - now[1] < gap) if idx == 1 else (now[0] - yr[0] < gap)


def nba_who_matters(names, team_id, before):
    """🏀 11/18: an NBA out list cut to the men who MATTER - a top-3 scorer over the last 10 box scores or a verified
    starter (sports.nba_key_man's test). A bench man, or one out so long the box scores no longer carry him, is never a
    card's knock or reason. No box scores: the list as it is."""
    try:
        import sports_absences
        import sports_data as sd_
        top = (sports_absences.key_players({}, "nba", team_id, before) or {}).get("top") or []
    except Exception:                                     # noqa: BLE001
        return names
    if not top:
        return names
    keys = {sports_absences._nm(p) for p in top}
    out = []
    for x in names:
        nm = str(x).split(" (")[0]
        try:
            starter = sd_.STARTER_OF is not None and sd_.STARTER_OF("nba", team_id, nm) is True
        except Exception:                                 # noqa: BLE001
            starter = False
        if sports_absences.match(nm, keys) or starter:
            out.append(x)
    return out


def who_plays_only(names, lg, team_id, before):
    """Football: the out list ("Name (POS)") cut to the men the team's box scores say PLAY (sports_absences.regulars -
    the QB, top backs / catchers / tacklers of the last 3 games). 10/31 college sweep: the Kansas St card's risk line
    read "goes without D. Duff (QB), G. Oakley (TE), A. Morrell (TE), W. Anciaux (TE)" - four men who never show up in
    its box scores, a backup QB first - and "That's real depth gone" can say the same of walk-ons. No box scores / not
    football: the list as it is. The 🚑 list on the card keeps everyone (who_plays_first only orders it)."""
    try:
        import sports_absences
    except Exception:                                        # noqa: BLE001
        return names

    def fresh(xs):                                        # 🚑 11/18 (cards_1118): never a man out long-term - he sat the
        try:                                              # team's last 5 box scores (2 in football): old news, in every
            return [x for x in xs if not sports_absences.gone_long(None, lg, team_id, str(x).split(" (")[0], before)]
        except Exception:                                 # noqa: BLE001
            return xs
    if lg == "nba":                                       # 🏀 11/18 (the owner on the Nuggets card's "Biggest knock: Nuggets
        return fresh(nba_who_matters(names, team_id, before))   # go without Julian Strawther": "Strawther's been out for
    if lg in ("nhl", "ncaab"):                            #  a hot minute, and he's not even a key player")
        try:                                              # 🏒 / 🏀 11/18: the same idea in every league - hockey: a top-6
            pool = sports_absences.who_matters(None, lg, team_id, before)   # forward / top-4 D by ice time or the #1
        except Exception:                                 # noqa: BLE001      goalie; college hoops: the top-5 minutes men
            pool = None
        if not pool:
            return names
        return fresh([x for x in names if sports_absences.match(str(x).split(" (")[0], pool)])
    if lg not in ("nfl", "ncaaf"):
        return names
    try:                                                     # 🧱 11/19: plays() - the box score's regulars AND the
        reg = sports_absences.plays(None, lg, team_id, before)   # starters it can't show (the offensive line, corners,
    except Exception:                                        # noqa: BLE001  the men up front - the snap counts)
        return names
    if not reg:
        return names
    return fresh([x for x in names if sports_absences.match(str(x).split(" (")[0], reg)])


# 👍 11/18 (cards_1118 - the owner on the Nuggets card: the one-liner said the 5,300 feet and the 1,760 miles, then the body
# said both again; the Packers Lock said the 45-27 win over the Patriots three times - 🚀, 📅 and 📋): NOTHING IS SAID TWICE.
# A body line goes when (a) it is the one-liner's sentence again, (b) every game score in it is already on the card (the
# one-liner or a line that says that game better), (c) its only big numbers - miles, feet - are the one-liner's, or (d) it
# is a 🚑 line naming only men the one-liner named. A two-game 📅 line keeps the half that is news; a 📋 line whose last
# game was said keeps its record. The ⚠️ line, the bottom line and the update lines are never touched.
_SCORE_RX = re.compile(r"(?<![\d.+-])(\d{1,3})-(\d{1,3})(?![\d%-])")
_BIG_RX = re.compile(r"(?<![\d.-])\d{1,3}(?:,\d{3})+|(?<![\d.,-])\d{3,}(?![\d-])")
_NAME_RX = re.compile(r"[A-Z][\w.'’-]*(?: (?:[A-Z][\w.'’-]*|II|III|IV|Jr\.?|Sr\.?))+")
RECORD_LINES = ("🗓", "🧳", "🏟", "⚖", "💪", "🔥", "🧊", "🗑")   # an N-N in these is a record, never a game's score
NEVER_CUT = ("⚠️", "✅", "🟡", "🔒", "💎", "🌟", "🔄")
_SAY_FIRST = ("🚀", "🥊", "🪤", "😤", "🏒", "⏳", "😴", "😮")       # the line that tells a game best keeps it


def line_scores(t, known, recs=()):
    """The finished games a line carries: its N-N pairs that are real scores of the two teams' recent games (`known`,
    (high, low) pairs) - a record ("6-3 on the year") is never one."""
    s = str(t or "")
    if s.startswith(RECORD_LINES):
        return set()
    for r in recs or ():
        s = re.sub(rf"(?<!\d){re.escape(str(r))}(?!\d)", " ", s)
    return {p for p in (tuple(sorted((int(a), int(b)), reverse=True)) for a, b in _SCORE_RX.findall(s)) if p in known}


def _big_nums(t):
    return {n.replace(",", "") for n in _BIG_RX.findall(_SCORE_RX.sub(" ", str(t or "")))}


def _words(t):
    return " ".join(re.findall(r"[a-z0-9]+", str(t or "").lower()))


_STREAK_RX = re.compile(r"(\d+)(?:-game)? (?:straight|in a row|skid|heater|winning streak|losing streak)|"
                        r"(\d+) (?:wins|losses|L'?s|W'?s) in a row|(?:streak|skid) at (\d+)|"
                        r"haven'?t (?:won|lost) in (\d+)|hasn'?t (?:won|lost) in (\d+)", re.I)


def _streaks(t):
    """The streak lengths a line states ('5 straight', '5 losses in a row', 'haven't won in 5') -> {5}."""
    return {int(n) for m in _STREAK_RX.finditer(str(t or "")) for n in m.groups() if n}


_OPP_RX = re.compile(r"\b(?:over|to|at|by|against|vs\.?) (?:the )?([A-Z][\w.'&-]*(?: (?:[A-Z][\w.'&-]*|St|State))*)")


def _opps_named(t):
    """The opponents a line names after "over / to / at / by" ('a 4-3 win over the Sabres' -> {'Sabres'})."""
    return {m.rstrip(".,'") for m in _OPP_RX.findall(str(t or "")) if len(m) > 2}


def no_repeats(lines, why, known, recs=(), us=""):
    wl = str(why or "")
    said, wbig, wplain = line_scores(wl, known, recs), _big_nums(wl), _words(wl)
    pri = lambda x: 0 if str(x).startswith(_SAY_FIRST) else 2 if str(x).startswith("📋") else 1   # noqa: E731
    keep = {}
    carriers = [wl]
    streaks_said = _streaks(wl)
    for i in sorted(range(len(lines)), key=lambda j: (pri(lines[j]), j)):
        x = lines[i]
        if not isinstance(x, str) or x.startswith(NEVER_CUT) or "non-D1" in x:   # (the tune-up note is never lost)
            keep[i] = x
            continue
        p = _words(x)
        if len(p) > 12 and p in wplain:
            continue                                         # (a) the one-liner's sentence again
        sc = line_scores(x, known, recs)
        opp_ = _opps_named(x)                                # (11/19: "a 4-3 win over the Sabres" is not the "4-3 win at the
        if sc and sc <= said and opp_ and not any(n in c for n in opp_ for c in carriers):   # Blue Jackets" another line
            said |= sc                                       #  carries - the same score, a different game: it stays)
            keep[i] = x
            carriers.append(x)
            continue
        if sc and sc <= said:                                # (b) every game in it is already on the card
            rec = next((r for r in recs or () if re.search(rf"(?<!\d){re.escape(str(r))}(?!\d)", x)), None)
            if x.startswith("📋") and rec and us and us in x and rec not in wl:
                keep[i] = f"📋 {us} {vb(us, 'are', 'is')} {rec} on the year."
            continue
        if x.startswith("📅") and " · " in x and sc & said:   # (a two-game line: the half that is news)
            fresh = [q.strip(" .") for q in x.partition(": ")[2].split(" · ")
                     if not (line_scores(q, known, recs) and line_scores(q, known, recs) <= said)]
            if len(fresh) == 1:
                x = f"📅 {fresh[0]} last time out."
        big = _big_nums(x)
        if not sc and big and big <= wbig:
            continue                                         # (c) the one-liner's miles / feet again
        if x.startswith("🚑"):
            names = [n for n in (m_.rstrip(".,'’") for m_ in _NAME_RX.findall(x[1:])) if not any(w in n for w in (us,) if w)]
            names = [n for n in names if len(n.split()) >= 2]
            if names and all(n in wl for n in names):
                continue                                     # (d) the men the one-liner already named
        if x.startswith(("🏟", "🧳")) and re.search(r"at home|on the road|away from home|own building|the crib", wl, re.I):
            rr = [f"{a}-{b}" for a, b in _SCORE_RX.findall(x)]
            if rr and all(re.search(rf"(?<![\d-]){re.escape(r)}(?![\d-])", wl) for r in rr):
                continue                                     # (e) the home / road record the one-liner already said
        if x.startswith(("🔥", "🧊")) and not sc:            # (f) 11/19 sweep: the same streak twice - "🧊 5 straight
            stx = _streaks(x)                                #  losses for the Ravens" under the pick and "🔥 The Ravens
            if stx and stx <= streaks_said:                  #  have lost 5 straight" in the body
                continue
            streaks_said |= stx
        said |= sc
        keep[i] = x
        carriers.append(x)
    return [keep[i] for i in sorted(keep)]


STAR_WINDOW = {"nba": 10, "ncaab": 5, "nhl": 10}    # our top scorer: the team's last N box scores
STAR_MIN = {"nba": 18.0, "ncaab": 14.0, "nhl": 0.8}  # ...worth a line at this many points a game (hockey: points = G + A)


FB_STAT_MIN = {"rushingYards": 70.0, "receivingYards": 70.0}   # football: a back / a catcher worth a line (yards a game)


def top_scorer(lg, team_id, before, skip=(), rank=0, stat=None):
    """(name, points a game, games) - the team's top scorer over its last box scores, a man who played its LAST game
    and isn't on the card's out / questionable lists. None when the box scores can't say. Football (stat =
    'rushingYards' / 'receivingYards'): the leader in yards a game over the last 3 box scores."""
    fb = lg in ("nfl", "ncaaf")
    n = 3 if fb else STAR_WINDOW.get(lg)
    if not n or (fb and stat not in FB_STAT_MIN):
        return None
    try:
        import json as _json
        import sports_absences as _sa
        last = _sa._real(None, lg, team_id, before)[-n:]
    except Exception:                                     # noqa: BLE001
        return None
    if len(last) < 3:
        return None
    tot = {}
    for _, _, rs in last:
        for r in rs:
            try:
                st = _json.loads(r.get("stats") or "{}")
            except ValueError:
                continue
            if fb and stat not in st:
                continue
            p = _sa._num(st.get(stat)) if fb else _sa._num(st.get("points")) if lg != "nhl" \
                else _sa._num(st.get("goals")) + _sa._num(st.get("assists"))
            t = tot.setdefault(r["player"], [0.0, 0])
            t[0] += p
            t[1] += 1
    in_last = {r["player"] for r in last[-1][2]}
    gone = {_sa._nm(str(x).split(" (")[0]) for x in skip if x}
    ok = sorted(((name, pts / gp, gp) for name, (pts, gp) in tot.items()
                 if gp >= (2 if fb else 3) and name in in_last and _sa._nm(name) not in gone), key=lambda x: -x[1])
    best = ok[rank] if len(ok) > rank else None
    floor_ = FB_STAT_MIN[stat] if fb else STAR_MIN[lg] * (1 if rank == 0 else 0.8)
    return best if best and best[1] >= floor_ else None


def counted(lines, leg=None):
    """How many of a card's lines the page counts as FACT lines (sports_card_check.fact_lines) - and never a 🚑 line
    that only repeats the card's 'missing' chip (the page cuts it)."""
    import sports_card_check as _cc
    return _cc.fact_lines([x for x in lines or [] if not (leg and _cc.chip_repeat(x, leg))])


# 🧱 11/18 (night) THE DEEP REFILL (the owner, after the first refill: "it's just short and fucking vague and a real shitty
# fucking breakdown. This is a fucking permanent bug" / "this needs to be permanent fix for everything going forward"):
# after the first refill 22 of the 49 board cards 11/1-11/18 still showed under 6 fact lines. The files hold a lot more
# for our side than the card ever said - every one below is a COUNT off the game files / the box scores, said the way a
# bettor says it (never a rate, never a formula), and only when it argues for US:
#   their missing man's numbers (and their record without him) · how each side does as the favorite / the dog · the
#   close of games (the 4th quarter, the third period, after halftime) · who each side beats (teams with a winning
#   record) · the box-score edges (rebounds, threes, turnovers, shots on net, rushing yards, sacks) · the spread covers.
LATE_PART = {"nba": (4, (3,), "the 4th quarter", 10), "nhl": (3, (2,), "the third period", 10),
             "nfl": (4, (2, 3), "the second half", 5), "ncaaf": (4, (2, 3), "the second half", 5),
             "ncaab": (2, (1,), "the second half", 5)}    # league -> (regulation parts, the closing ones, its name, games)
LATE_MIN = {"nba": 6, "nhl": 3, "nfl": 14, "ncaaf": 17, "ncaab": 15}   # the closing stretch is a line at this gap (NBA:
#                                                                         quarters won of the 10; the rest: goals / points)
LATE_GAMES_MIN = 4     # a "last N games" count needs this many games (early in a season it says the 4+ there are)
ROMP_BY = {"nba": 10, "ncaab": 10, "nhl": 3, "nfl": 14, "ncaaf": 14}   # a comfortable win / a bad loss: by this many or more
DEPTH_MIN = {"nba": (6, 10.0, 10), "ncaab": (5, 10.0, 5)}   # hoops depth: this many men at 10+ points a game (box games)
DEEP_FILL = True       # the deep refill's switch (False = the first refill only)
ROLE_MIN = 4           # a record as the favorite / the dog needs this many games
WIN_TEAM_GAMES = 5     # "a team with a winning record" has played this many
BOX_EDGE = {"nba": (("rebounds", 4.0, 5), ("threes", 2.5, 5), ("turnovers", 2.5, 5)),
            "ncaab": (("rebounds", 5.0, 4),),
            "nhl": (("shotsTotal", 3.0, 5),),
            "nfl": (("rushingYards", 35.0, 3), ("sacks", 1.0, 3)),
            "ncaaf": (("rushingYards", 45.0, 3), ("sacks", 1.0, 3))}   # league -> (stat, the gap worth a line, box games)
GONE_MIN = {"nba": 14.0, "ncaab": 12.0, "nhl": 0.6}   # their missing man is worth his own line at this many points a game
COVER_GAMES = {"nba": 10, "ncaab": 8, "nfl": 6, "ncaaf": 6}
BIG_NIGHT = {"nba": (120, 5), "nhl": (4, 5), "nfl": (28, 5), "ncaaf": (31, 5), "ncaab": (80, 5)}   # a big number on the
#   scoreboard (points / goals) and the games looked at: "gave up 120+ in 4 of their last 5" is a line at 3+ of the 5
CLOSE_BY = {"nba": 5, "ncaab": 5, "nhl": 1, "nfl": 7, "ncaaf": 7}   # a close game: decided by this many or fewer
START_MIN = {"nba": 6, "nhl": 3, "nfl": 14, "ncaaf": 17, "ncaab": 15}   # the START of games (1st quarter / 1st period / 1st half)
REFILL_PAST = 1        # the write-up refills a short card to its floor + this
SPARE_MAX = 8          # the refill facts a card didn't need ride along on the leg (leg["spare"]) - see sports_card_check.refill


def _fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def ml_role(x, tid):
    """'fav' / 'dog' / None - what the closing moneyline made this team in a finished game."""
    home = x.get("home") == tid
    a, b = _fnum(x.get("ml_home" if home else "ml_away")), _fnum(x.get("ml_away" if home else "ml_home"))
    if a is None or b is None or a == b:
        return None
    return "fav" if a < b else "dog"


def role_record(gs, tid, role):
    """(wins, losses) in the season's games where the close made this team the favorite / the dog."""
    w = lo = 0
    for x in gs or []:
        if ml_role(x, tid) == role:
            r = _line(x, tid)[0]
            w, lo = w + (r == "W"), lo + (r == "L")
    return w, lo


def covers(gs, tid, n):
    """(covered, didn't, games) against the closing spread over the team's last n lined games - or None."""
    last = [x for x in gs or [] if _fnum(x.get("spread_home")) is not None][-n:]
    if len(last) < n:
        return None
    c = miss = 0
    for x in last:
        home = x["home"] == tid
        line = _fnum(x["spread_home"]) * (1 if home else -1)
        m = (int(x["home_score"]) - int(x["away_score"])) * (1 if home else -1) + line
        c, miss = c + (m > 0), miss + (m < 0)
    return c, miss, n


def late_score(gs, tid, lg):
    """(scored, allowed, stretches won, lost, games) in the closing stretch of the team's last games - the NBA's 4th
    quarter, hockey's third period, football's / college hoops' second half - off the line scores. None when a line
    score is missing (never a guess)."""
    cfg = LATE_PART.get(lg)
    if not cfg:
        return None
    parts, idx, _, n = cfg
    last = (gs or [])[-n:]
    if len(last) < min(n, LATE_GAMES_MIN):                # (early in a season: the 5+ games there are, said as that many)
        return None
    n = len(last)
    f = a = won = lost = 0
    for x in last:
        try:
            hs = [int(v) for v in str(x.get("ls_home") or "").split(",")]
            aw = [int(v) for v in str(x.get("ls_away") or "").split(",")]
        except ValueError:
            return None
        if len(hs) < parts or len(aw) < parts:
            return None
        if sum(hs) != int(x["home_score"]) or sum(aw) != int(x["away_score"]):
            return None                                   # (a line score that doesn't add up to the final: no line)
        home = x["home"] == tid
        mine, his = (hs, aw) if home else (aw, hs)
        pf, pa = sum(mine[i] for i in idx), sum(his[i] for i in idx)
        f, a, won, lost = f + pf, a + pa, won + (pf > pa), lost + (pf < pa)
    return f, a, won, lost, n


def big_nights(gs, tid, lg, allowed):
    """(games at the big number, games) - how often the team scored (allowed=False) or gave up (True) the league's big
    number over its last games. None without the full window."""
    cfg = BIG_NIGHT.get(lg)
    if not cfg:
        return None
    big, n = cfg
    last = (gs or [])[-n:]
    if len(last) < min(n, LATE_GAMES_MIN):
        return None
    n = len(last)
    c = 0
    for x in last:
        home = x["home"] == tid
        mine, his = (int(x["home_score"]), int(x["away_score"])) if home else (int(x["away_score"]), int(x["home_score"]))
        c += (his if allowed else mine) >= big
    return c, n


def romps(gs, tid, lg, lost=False):
    """(games, of the last n) the team WON by ROMP_BY or more - or, lost=True, LOST by that many."""
    by = ROMP_BY.get(lg)
    last = (gs or [])[-5:]
    if not by or len(last) < LATE_GAMES_MIN:
        return None
    c = 0
    for x in last:
        d = (int(x["home_score"]) - int(x["away_score"])) * (1 if x["home"] == tid else -1)
        c += (-d if lost else d) >= by
    return c, len(last)


def double_figures(lg, team_id, before, skip=()):
    """Hoops depth off the box scores: the men at 10+ points a game over the team's last box scores (3+ games each, in
    the last one, not on the card's out / questionable lists) -> (how many, box games) or None."""
    cfg = DEPTH_MIN.get(lg)
    if not cfg:
        return None
    try:
        import json as _json
        import sports_absences as _sa
        last = _sa._real(None, lg, team_id, before)[-cfg[2]:]
    except Exception:                                     # noqa: BLE001
        return None
    if len(last) < LATE_GAMES_MIN:
        return None
    tot = {}
    for _, _, rs in last:
        for r in rs:
            try:
                st = _json.loads(r.get("stats") or "{}")
            except ValueError:
                continue
            if _sa._num(st.get("minutes")) <= 0:
                continue
            t = tot.setdefault(r["player"], [0.0, 0])
            t[0] += _sa._num(st.get("points"))
            t[1] += 1
    in_last = {r["player"] for r in last[-1][2]}
    gone = {_sa._nm(str(x).split(" (")[0]) for x in skip if x}
    n = sum(1 for nm, (pts, gp) in tot.items() if gp >= 3 and nm in in_last and _sa._nm(nm) not in gone and pts / gp >= cfg[1])
    return n, len(last)


def close_games(gs, tid, lg):
    """(wins, losses) in the season's games decided by CLOSE_BY or fewer (hockey: one goal)."""
    by = CLOSE_BY.get(lg)
    w = lo = 0
    for x in gs or [] if by else []:
        d = int(x["home_score"]) - int(x["away_score"])
        if d and abs(d) <= by:
            won = (d > 0) == (x["home"] == tid)
            w, lo = w + won, lo + (not won)
    return w, lo


def early_score(gs, tid, lg):
    """late_score for the START of games: the NBA's 1st quarter, hockey's first period, the first half elsewhere."""
    cfg = LATE_PART.get(lg)
    if not cfg:
        return None
    keep = LATE_PART[lg]
    try:
        LATE_PART[lg] = (cfg[0], (0, 1) if lg in ("nfl", "ncaaf") else (0,), "", cfg[3])
        return late_score(gs, tid, lg)
    finally:
        LATE_PART[lg] = keep


_REC_NOW = {}


def records_now(fin, since, lg):
    """{team id: (wins, losses)} - every team's regular-season record since `since` (an ISO start), one pass."""
    key = (lg, since, len(fin))
    if key not in _REC_NOW:
        if len(_REC_NOW) > 40:
            _REC_NOW.clear()
        rec = {}
        for x in fin:
            if str(x.get("start") or "") < since or str(x.get("stype") or "2") != "2":
                continue
            try:
                h, a = int(x["home_score"]), int(x["away_score"])
            except (KeyError, TypeError, ValueError):
                continue
            for t_, won, lost in ((x["home"], h > a, h < a), (x["away"], a > h, a < h)):
                r = rec.setdefault(t_, [0, 0])
                r[0] += won
                r[1] += lost
        _REC_NOW[key] = rec
    return _REC_NOW[key]


def vs_winners(gs, tid, rec):
    """(wins, losses) against teams that have a winning record today (WIN_TEAM_GAMES+ played)."""
    w = lo = 0
    for x in gs or []:
        o = x["away"] if x["home"] == tid else x["home"]
        ow, ol = rec.get(o, (0, 0))
        if ow + ol >= WIN_TEAM_GAMES and ow > ol:
            r = _line(x, tid)[0]
            w, lo = w + (r == "W"), lo + (r == "L")
    return w, lo


def _box_stat(st, stat):
    if stat == "threes":
        v = str(st.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted") or "")
        return float(v.split("-")[0]) if v.split("-")[0].isdigit() else None
    return _fnum(st.get(stat))


def box_avg(lg, team_id, before, stat, n):
    """The team's total a game in one box-score stat over its last n box scores (every man's line added up) - or None
    when a box score doesn't carry the stat."""
    try:
        import json as _json
        import sports_absences as _sa
        last = _sa._real(None, lg, team_id, before)[-n:]
    except Exception:                                     # noqa: BLE001
        return None
    if len(last) < n:
        return None
    tot = 0.0
    for _, _, rs in last:
        got = False
        for r in rs:
            try:
                val = _box_stat(_json.loads(r.get("stats") or "{}"), stat)
            except ValueError:
                val = None
            if val is not None:
                tot, got = tot + val, True
        if not got:
            return None
    return tot / n


def gone_man(lg, team_id, before, name, season_games):
    """Their man who's out, off the box scores: (points a game, games he played, the team's wins, losses without him
    this season) - None when the box scores can't say. Hockey: points = goals + assists."""
    if lg not in GONE_MIN or not season_games:
        return None
    try:
        import json as _json
        import sports_absences as _sa
        since = str(season_games[0].get("start") or "")
        rows = [r for r in _sa._real(None, lg, team_id, before) if r[0] >= since]
    except Exception:                                     # noqa: BLE001
        return None
    want = _sa._nm(str(name).split(" (")[0])
    res = {x.get("id"): _line(x, team_id)[0] for x in season_games}
    pts, gp, w, lo = 0.0, 0, 0, 0
    for _, gid, rs in rows:
        mine = [r for r in rs if _sa._nm(r.get("player")) == want]
        if mine:
            try:
                st = _json.loads(mine[0].get("stats") or "{}")
            except ValueError:
                continue
            if lg != "nhl" and _sa._num(st.get("minutes")) <= 0:
                continue
            pts += _sa._num(st.get("points")) if lg != "nhl" else _sa._num(st.get("goals")) + _sa._num(st.get("assists"))
            gp += 1
        elif gid in res:
            w, lo = w + (res[gid] == "W"), lo + (res[gid] == "L")
    if gp < 3:
        return None
    return pts / gp, gp, w, lo


_ALL_RX = re.compile(r"\b(\d+) of (their|the) last \1\b")


def _every(line):
    """'in 5 of their last 5 games' -> 'in every one of their last 5 games' (all of them is said as all of them)."""
    t = _ALL_RX.sub(lambda m: f"every one of {m.group(2)} last {m.group(1)}", str(line or ""))
    return re.sub(r"^(\W+)every one", r"\1Every one", t)


def _of(c, n):
    """'3 of 5' - or 'all 5' when it's every one ("lost 6 of 6" reads wrong)."""
    return f"all {n}" if c == n else f"{c} of {n}"


def one_half():
    """11/23: is the one-half-a-team rule on? (sports_card_sell.REASONS_1123)"""
    try:
        import sports_card_sell as _cs
        return bool(_cs.REASONS_1123)
    except Exception:                                     # noqa: BLE001
        return False


def deep_facts(leg, v, g, us, them, tid, oid, lg, s_ours, s_theirs, r_ours, r_theirs, said, fin=None, e=None):
    """🧱 The deep refill: more real facts FOR our side off the game files and the box scores - each one a count, each
    said only when it argues for us. -> {key: line}; fill_facts puts them in order."""
    out = {}
    low = str(said or "").lower()
    before = g.get("start") or "9"
    nhl = lg == "nhl"
    dog = (leg.get("odds") or 0) > 0 if leg.get("market") == "ml" else (_fnum(leg.get("line")) or 0) > 0
    say = lambda k, ways: out.__setitem__(k, _every(v.say("deep_" + k, ways, fact=True)))   # noqa: E731
    # (SCHEDULE_FAIR, 11/15 - "We can't be looking like some clowns"): in college a stretch of THEIR games that holds one
    # against a team rated above us says nothing about this game - no "they fold late" off a week of buy games
    fair = lambda n: lg not in SCHEDULE_FAIR or not any(_tougher(x, oid, tid, e) for x in (s_theirs or [])[-n:])   # noqa: E731

    # 1. their missing man: what he was giving them, and how they've done without him
    try:
        named = who_plays_only([str(x) for x in (leg.get("opp_outs") or []) if x], lg, oid, before)
        if leg.get("inj_ok") is False:                    # 🧩 11/19: never "their man is out" when ours are as bad
            named = []
        best = None
        for x in named[:4]:
            nm = x.split(" (")[0]
            gm = gone_man(lg, oid, before, nm, r_theirs)
            if gm and gm[0] >= GONE_MIN[lg] and (best is None or gm[0] > best[1][0]):
                best = (nm, gm)
        if best:
            nm, (ppg, gp, w, lo) = best
            tail = f" {them} {vb(them, 'are', 'is')} {w} and {lo} in the games he missed this year." if w + lo >= 3 and w < lo else ""
            if nhl:
                say("gone", [f"📉 {nm} had {round(ppg * gp)} points in {gp} games for {them} this year, and he's out.{tail}",
                             f"📉 {them} lose {nm} - {round(ppg * gp)} points in his {gp} games this year.{tail}"])
            else:
                say("gone", [f"📉 {nm} was giving {them} {ppg:.0f} points a night ({gp} games) and he's out.{tail}",
                             f"📉 No {nm} means {ppg:.0f} points a night gone for {them}.{tail}",
                             f"📉 {them} gotta find {nm}'s {ppg:.0f} points a night somewhere else.{tail}"])
    except Exception:                                     # noqa: BLE001
        pass

    # 2. the favorite / the dog: how each side has done in this spot (the closing moneylines)
    try:
        if "as the dog" not in low and "as the favorite" not in low and "as the underdog" not in low:
            mine, his = ("dog", "fav") if dog else ("fav", "dog")
            w, lo = role_record(r_ours, tid, mine)
            if w + lo >= ROLE_MIN and (w >= lo if dog else w >= 2 * lo):
                say("role", [f"🐶 {us} won {_of(w, w + lo)} as the underdog this year. They cash plus money.",
                             f"🐶 As the dog this year {us} won {_of(w, w + lo)}.",
                             f"🐶 {w} wins in {w + lo} games as the underdog for {us} this season."] if dog else
                    [f"🏦 {us} won {_of(w, w + lo)} as the favorite this year. They handle business when they're supposed to.",
                     f"🏦 When the book makes {us} the favorite they won {_of(w, w + lo)} this year.",
                     f"🏦 {w} wins in {w + lo} games as the favorite for {us} this season."])
            w, lo = role_record(r_theirs, oid, his)
            if w + lo >= ROLE_MIN and (lo >= 3 and lo * 20 >= (w + lo) * 9 if dog else lo >= 3 and lo >= 2 * w):   # (a favorite that loses 45%+)
                say("role_t", [f"💸 {them} lost {_of(lo, w + lo)} as the favorite this year. That's a favorite that loses.",
                               f"💸 When the book makes {them} the favorite, they lost {_of(lo, w + lo)} this year.",
                               f"💸 {lo} losses in {w + lo} games as the favorite for {them} this season."] if dog else
                    [f"💸 {them} lost {_of(lo, w + lo)} as the underdog this year.",
                     f"💸 As the dog this year {them} lost {_of(lo, w + lo)}. They don't sneak up on people.",
                     f"💸 {lo} losses in {w + lo} games as the underdog for {them} this season."])
    except Exception:                                     # noqa: BLE001
        pass

    # 3. the close of games (line scores): ours when we own it, theirs when they give it away
    try:
        cfg = LATE_PART.get(lg)
        if cfg and cfg[2] not in low and "4th" not in low and "third" not in low:
            what, n = cfg[2], cfg[3]
            lu, lt = late_score(s_ours, tid, lg), late_score(s_theirs, oid, lg)
            if lg == "nba":
                if lu and lu[2] * 10 >= lu[4] * LATE_MIN[lg] and lu[0] > lu[1]:
                    say("late", [f"⏱️ {us} won {what} in {lu[2]} of their last {lu[4]} games. They close.",
                                 f"⏱️ Closing time: {us} took {what} in {lu[2]} of their last {lu[4]}.",
                                 f"⏱️ {lu[2]} of the last {lu[4]} times out, {us} won {what}."])
                if lt and lt[3] * 10 >= lt[4] * LATE_MIN[lg] and lt[0] < lt[1] and fair(lt[4]):
                    say("late_t", [f"⏱️ {them} lost {what} in {lt[3]} of their last {lt[4]} games. They fold late.",
                                   f"⏱️ {them} got outscored in {what} in {lt[3]} of their last {lt[4]}.",
                                   f"⏱️ {lt[3]} of the last {lt[4]} times out, {them} lost {what}."])
            else:
                unit = "goals" if nhl else "points"
                if "half" in str(what) and one_half():      # (11/23, the Indiana St card: the two halves are the whole
                    eu_, et_ = early_score(s_ours, tid, lg), early_score(s_theirs, oid, lg)   # scoreboard - one fact; the
                    if lu and eu_ and eu_[0] - eu_[1] >= START_MIN.get(lg, 99) and eu_[0] - eu_[1] > lu[0] - lu[1]:
                        lu = None                         #  better half is the one said)
                    if lt and et_ and et_[1] - et_[0] >= START_MIN.get(lg, 99) and et_[1] - et_[0] > lt[1] - lt[0]:
                        lt = None
                if lu and lu[0] - lu[1] >= LATE_MIN[lg]:
                    say("late", [f"⏱️ {us} outscored teams {lu[0]} to {lu[1]} in {what} over their last {lu[4]} games. They close.",
                                 f"⏱️ {what.capitalize()}, last {lu[4]} games: {lu[0]} {unit} for {us}, {lu[1]} against.",
                                 f"⏱️ {us} put up {lu[0]} {unit} in {what} over their last {lu[4]} and gave up {lu[1]}."])
                if lt and lt[1] - lt[0] >= LATE_MIN[lg] and fair(lt[4]):
                    say("late_t", [f"⏱️ {them} got outscored {lt[1]} to {lt[0]} in {what} over their last {lt[4]} games. They fold late.",
                                   f"⏱️ {what.capitalize()}, last {lt[4]} games: {them} gave up {lt[1]} {unit} and scored {lt[0]}.",
                                   f"⏱️ {them} gave up {lt[1]} {unit} in {what} over their last {lt[4]} and only got {lt[0]} back."])
    except Exception:                                     # noqa: BLE001
        pass

    # 4. who each side beats: the record against teams with a winning record (the pros - a full schedule on file)
    try:
        if lg in ("nba", "nhl", "nfl", "mlb") and fin and r_ours and r_theirs and "winning record" not in low:
            rec = records_now(fin, min(str(r_ours[0]["start"]), str(r_theirs[0]["start"])), lg)
            w, lo = vs_winners(r_theirs, oid, rec)
            if w + lo >= 4 and w == 0:
                say("win_t", [f"🧾 {them} haven't beaten a team with a winning record this year - {lo} tries, {lo} losses.",
                              f"🧾 {lo} games against teams with a winning record this year for {them}, {lo} losses."])
            elif w + lo >= 4 and lo >= 2 * w + 1:
                say("win_t", [f"🧾 {them} won {_of(w, w + lo)} against teams with a winning record this year.",
                              f"🧾 Against teams with a winning record {them} won just {_of(w, w + lo)} this year.",
                              f"🧾 {them} only got {w} win{'s' if w != 1 else ''} in {w + lo} games against winning teams this year."])
            w, lo = vs_winners(r_ours, tid, rec)
            ow, ol = rec.get(oid, (0, 0))
            if w + lo >= 4 and w >= lo and ow > ol:
                say("win", [f"🧾 {us} won {_of(w, w + lo)} against teams with a winning record this year.",
                            f"🧾 Against teams with a winning record {us} won {_of(w, w + lo)} this year. Good teams don't scare 'em.",
                            f"🧾 {w} wins in {w + lo} games against winning teams for {us} this year."])
    except Exception:                                     # noqa: BLE001
        pass

    # 5. the box-score edges: both teams' totals a game over their last box scores - only a real gap, only ours
    try:
        seen = lg in ("nba", "nhl", "nfl") or bool(s_ours and s_theirs)
        for stat, gap, n in BOX_EDGE.get(lg, ()) if seen else ():
            a, b = box_avg(lg, tid, before, stat, n), box_avg(lg, oid, before, stat, n)
            if a is None or b is None:
                continue
            if stat == "turnovers":
                if b - a >= gap and "turn" not in low:
                    say("box_to", [f"🧤 {us} take care of the ball: {a:.0f} turnovers a night over their last {n}, {them} {b:.0f}.",
                                   f"🧤 {them} been coughing it up {b:.0f} times a night over their last {n}. {us}: {a:.0f}.",
                                   f"🧤 Turnovers a night, last {n} games: {us} {a:.0f}, {them} {b:.0f}."])
                continue
            if a - b < gap:
                continue
            if stat == "rebounds" and "rebound" not in low and "glass" not in low:
                say("box_reb", [f"🧲 {us} been owning the glass: {a:.0f} rebounds a night over their last {n}, {them} {b:.0f}.",
                                f"🧲 Rebounds a night over the last {n}: {us} {a:.0f}, {them} {b:.0f}. Second chances are ours.",
                                f"🧲 {a:.0f} rebounds a night for {us} over their last {n}. {them} get {b:.0f}."])
            elif stat == "threes" and "threes" not in low:
                say("box_3", [f"👌 {us} been hitting {a:.0f} threes a night over their last {n}. {them}: {b:.0f}.",
                              f"👌 Threes a night, last {n} games: {us} {a:.0f}, {them} {b:.0f}.",
                              f"👌 {a:.0f} threes a night for {us} over their last {n} to {_pos(them)} {b:.0f}."])
            elif stat == "shotsTotal" and "shots" not in low:
                say("box_sh", [f"🏹 {us} been putting {a:.0f} shots on net a night over their last {n}. {them}: {b:.0f}.",
                               f"🏹 Shots on net a night, last {n} games: {us} {a:.0f}, {them} {b:.0f}.",
                               f"🏹 {a:.0f} shots a night for {us} over their last {n} to {_pos(them)} {b:.0f}. We get more looks."])
            elif stat == "rushingYards" and "on the ground" not in low and "ran for" not in low:
                say("box_run", [f"🏃 {us} ran for {a:.0f} yards a game over their last {n}. {them}: {b:.0f}.",
                                f"🏃 On the ground the last {n} games: {us} {a:.0f} yards a game, {them} {b:.0f}.",
                                f"🏃 {a:.0f} rushing yards a game for {us} over their last {n} to {_pos(them)} {b:.0f}."])
            elif stat == "sacks" and "sack" not in low and round(a * n) >= 6:
                say("box_sack", [f"💥 {us} got to the quarterback {round(a * n)} times in their last {n} games. {them}: {round(b * n)}.",
                                 f"💥 {round(a * n)} sacks in the last {n} games for {us}, {round(b * n)} for {them}.",
                                 f"💥 Sacks over the last {n}: {us} {round(a * n)}, {them} {round(b * n)}. Our front gets home."])
    except Exception:                                     # noqa: BLE001
        pass

    # 7. big nights on the scoreboard: how often they give it up, how often we put it up
    try:
        cfg = BIG_NIGHT.get(lg)
        if cfg and f"{cfg[0]}+" not in low and f"{cfg[0]} or more" not in low:
            big, n = cfg
            unit = "goals" if nhl else "points"
            bt, bu = big_nights(_form(s_theirs, oid, lg), oid, lg, True), big_nights(_form(s_ours, tid, lg), tid, lg, False)
            if bt and bt[0] >= 3 and fair(bt[1]):
                n = bt[1]
                say("big_t", [f"🚪 {them} gave up {big} or more {unit} in every one of their last {n} games.",
                              f"🚪 {big}+ {unit} allowed {n} games running by {them}. That defense is giving it away."] if bt[0] == n else
                    [f"🚪 {them} gave up {big} or more {unit} in {bt[0]} of their last {n} games.",
                              f"🚪 {bt[0]} of the last {n} teams to play {them} put up {big} or more.",
                              f"🚪 {big}+ {unit} allowed in {bt[0]} of the last {n} for {them}. That defense is giving it away."])
            if bu and bu[0] >= 3:
                n = bu[1]
                say("big", [f"💣 {us} scored {big} or more in every one of their last {n} games.",
                            f"💣 {big}+ {unit} for {us} {n} games running. They can score."] if bu[0] == n else
                    [f"💣 {us} scored {big} or more in {bu[0]} of their last {n} games.",
                     f"💣 {big}+ {unit} for {us} in {bu[0]} of their last {n}. They can score.",
                     f"💣 {bu[0]} of the last {n} times out, {us} put up {big} or more."])
    except Exception:                                     # noqa: BLE001
        pass

    # 8. the start of games (line scores)
    try:
        if "1st quarter" not in low and "first period" not in low and "first half" not in low and "halftime" not in low:
            what = {"nba": "the 1st quarter", "nhl": "the first period"}.get(lg, "the first half")
            n = (LATE_PART.get(lg) or (0, 0, 0, 0))[3]
            eu, et = early_score(_form(s_ours, tid, lg), tid, lg), early_score(_form(s_theirs, oid, lg), oid, lg)
            unit = "goals" if nhl else "points"
            if lg == "nba":
                if eu and eu[2] * 10 >= eu[4] * START_MIN[lg] and eu[0] > eu[1]:
                    say("start", [f"🏁 {us} won {what} in {eu[2]} of their last {eu[4]} games. They come out ready.",
                                  f"🏁 {eu[2]} of the last {eu[4]} times out, {us} took {what}."])
                if et and et[3] * 10 >= et[4] * START_MIN[lg] and et[0] < et[1] and fair(et[4]):
                    say("start_t", [f"🏁 {them} lost {what} in {et[3]} of their last {et[4]} games. Slow starters.",
                                    f"🏁 {et[3]} of the last {et[4]} times out, {them} were behind after {what}."])
            else:
                if "half" in what and one_half() and LATE_PART.get(lg):   # (11/23: ... and never both halves)
                    lu_, lt_ = late_score(_form(s_ours, tid, lg), tid, lg), late_score(_form(s_theirs, oid, lg), oid, lg)
                    if eu and lu_ and lu_[0] - lu_[1] >= LATE_MIN[lg] and lu_[0] - lu_[1] >= eu[0] - eu[1]:
                        eu = None
                    if et and lt_ and lt_[1] - lt_[0] >= LATE_MIN[lg] and lt_[1] - lt_[0] >= et[1] - et[0] and fair(lt_[4]):
                        et = None
                if eu and eu[0] - eu[1] >= START_MIN.get(lg, 99):
                    say("start", [f"🏁 {us} outscored teams {eu[0]} to {eu[1]} in {what} over their last {eu[4]} games. They come out ready.",
                                  f"🏁 {what.capitalize()}, last {eu[4]} games: {eu[0]} {unit} for {us}, {eu[1]} against."])
                if et and et[1] - et[0] >= START_MIN.get(lg, 99) and fair(et[4]):
                    say("start_t", [f"🏁 {them} got outscored {et[1]} to {et[0]} in {what} over their last {et[4]} games. Slow starters.",
                                    f"🏁 {what.capitalize()}, last {et[4]} games: {them} gave up {et[1]} {unit} and scored {et[0]}."])
    except Exception:                                     # noqa: BLE001
        pass

    # 9. the close ones: who wins the games that come down to the end
    try:
        by = CLOSE_BY.get(lg)
        if by and "close" not in low and "one-goal" not in low:
            how = "one-goal games" if nhl else f"games decided by {by} or less"
            w, lo = close_games(r_ours, tid, lg)
            if w + lo >= 4 and w >= 2 * lo:
                say("close", [f"🎬 {us} won {w} of their {w + lo} {how} this year. They finish.",
                              f"🎬 In {how} this year {us} won {_of(w, w + lo)}."])
            w, lo = close_games(r_theirs, oid, lg)
            if w + lo >= 4 and lo >= 2 * w and fair(len(s_theirs or [])):
                say("close_t", [f"🎬 {them} lost {lo} of their {w + lo} {how} this year. They don't finish.",
                                f"🎬 In {how} this year {them} lost {_of(lo, w + lo)}."])
    except Exception:                                     # noqa: BLE001
        pass

    # 10. comfortable wins / bad losses, counted (the 🥊 line is one game; this is how often)
    try:
        by = ROMP_BY.get(lg)
        unit = "goals" if nhl else "points"
        if by and f"by {by}" not in low:
            ru, rt = romps(s_ours, tid, lg), romps(s_theirs, oid, lg, lost=True)
            if ru and ru[0] >= 3:
                say("romp", [f"🧹 {us} won every one of their last {ru[1]} games by {by} or more {unit}.",
                             f"🧹 {us} ain't squeaking by: {ru[1]} straight wins by {by}+."] if ru[0] == ru[1] else
                    [f"🧹 {us} won by {by} or more {unit} in {ru[0]} of their last {ru[1]} games.",
                     f"🧹 {us} won {ru[0]} of their last {ru[1]} games by {by} or more.",
                     f"🧹 {us} ain't squeaking by: {ru[0]} wins by {by}+ in their last {ru[1]} games."])
            if rt and rt[0] >= 3 and fair(rt[1]):
                say("romp_t", [f"🧹 {them} lost by {by} or more {unit} in {_of(rt[0], rt[1])} of their last {rt[1]} games."
                               if rt[0] != rt[1] else f"🧹 {them} lost every one of their last {rt[1]} games by {by} or more {unit}.",
                               f"🧹 {them} lost {_of(rt[0], rt[1])} of their last {rt[1]} games by {by} or more."
                               if rt[0] != rt[1] else f"🧹 {rt[1]} straight losses by {by} or more for {them}.",
                               f"🧹 {them} been getting run: {rt[0]} losses by {by}+ in their last {rt[1]} games."])
    except Exception:                                     # noqa: BLE001
        pass

    # 11. hoops depth: how many of ours score in double figures (the box scores)
    try:
        cfg = DEPTH_MIN.get(lg)
        if cfg and "double figures" not in low:
            skip = list(leg.get("outs") or []) + list(leg.get("absent") or []) + list(leg.get("on_report") or []) \
                + list(leg.get("waiting") or []) + list((leg.get("rep_status") or {}).keys())
            du, dt = double_figures(lg, tid, before, skip), double_figures(lg, oid, before, leg.get("opp_outs") or [])
            if du and du[0] >= cfg[0] and (not dt or du[0] > dt[0]):
                say("depth", [f"🖐️ {us} got {du[0]} guys scoring in double figures over their last {du[1]} games. You can't just guard one.",
                              f"🖐️ {du[0]} different {us} players are putting up 10 or more a night over their last {du[1]}.",
                              f"🖐️ Depth: {du[0]} guys in double figures for {us} over their last {du[1]} games."])
    except Exception:                                     # noqa: BLE001
        pass

    # 6. the spread covers (hoops / football - hockey and baseball are moneyline sports here)
    try:
        n = COVER_GAMES.get(lg)
        if n and "cover" not in low:
            cu, ct = covers(s_ours, tid, n), covers(s_theirs, oid, n)
            if cu and cu[0] * 10 >= n * 6:
                say("cover", [f"🎟️ {us} covered the spread in {cu[0]} of their last {n} games.",
                              f"🎟️ {cu[0]} covers in the last {n} for {us}. They been better than the book thinks.",
                              f"🎟️ {us} beat the spread {cu[0]} times in their last {n}."])
            if ct and ct[1] * 10 >= n * 6:
                say("cover_t", [f"🎟️ {them} failed to cover in {ct[1]} of their last {n} games.",
                                f"🎟️ {them} didn't cover the spread in {ct[1]} of their last {n}. The book keeps asking too much of 'em.",
                                f"🎟️ {ct[1]} of the last {n} times out, {them} didn't cover."])
    except Exception:                                     # noqa: BLE001
        pass
    return {k: x for k, x in out.items() if x}


# 📖 11/19 THE STORY OF THE GAME (the owner, on the Flyers +150 2u card: "It's like, oh, this guy's in gold and this guy's
# in gold. Don't tell us shit. It's like, oh, we price flyers at this. Don't tell us shit. Like, the breakdowns are just
# trash" / "permanently fix these fucking breakdowns"). The card had a scorer's points twice, the price said twice in
# price math ("we price Flyers at +123", "winning about 4 times in 10 is all we need"), "at full strength" and "3 of
# their last 5" - true, and none of it says why THIS team wins THIS game. A card tells the matchup: what happened when
# these two met, how the other side has really been winning (by one goal), where it got run, what we've done in this
# kind of building lately, who both of us played and how it went. Every one below is a real game or a count off the
# game files, said only when it argues for us. Price math and a second scorer line are gone from the pools; the page's
# check cuts them off any older card (sports_card_check.filler).
STORY = True           # the switch (False = the 11/18 card)
THIN_WINS_MIN = 4      # "N of their M wins came by one goal" needs this many wins, half or more of them that close
THIN_WINS_CLOSE = 3    # ... and this many close ones
SITE_LAST = 3          # our last N games at tonight's kind of site (home / road) - a line when we won 2+ of them
SITE_ROUT_MIN = 2      # their beatdown losses at tonight's kind of site this year - a line at this many
COMMON_DAYS = 45       # a common opponent counts when both games were inside this many days
OUTSHOT_MIN = 15       # hockey: we outshot teams by this many over the last 10 while the puck luck ran against us
NO_OUR_NUMBER = True   # 🚫 11/19 (the owner: "we can't say that we're better at pricing the lines than the fucking line
#                        makers"): no line says our fair price or that the book has it wrong (sports_owner_lingo.PRICE_CLAIM)
CARD_MAX = 9           # the owner's range is 6-9 fact lines: past it the weakest lines ride along as spares
STAR_ONE = True        # one 💯 scorer line a card, the last resort of the refill - never two, never the price math


def _md(x):
    """'10/17' - the day a game was played, Pacific."""
    d = _t(x["start"]).astimezone(PT)
    return f"{d.month}/{d.day}"


def _margin(x, tid):
    d = int(x["home_score"]) - int(x["away_score"])
    return d if x["home"] == tid else -d


def _game_said(x, tid, pro, won=True):
    """'a 3-1 win at the Canucks' / 'a 4-3 win over the Sabres' / 'a 7-2 loss to the Blues' from tid's side."""
    opp, res, sc = _last_parts(x, tid, pro)
    if won:
        return f"{_an(sc.split('-')[0])} {sc} win {'at' if x['away'] == tid and not _neutral(x) else 'over'} {opp}"
    return f"{_an(sc.split('-')[0])} {sc} loss to {opp}"


def matchup_facts(leg, v, g, us, them, the_us, the_them, pro, tid, oid, lg, side, other, r_ours, r_theirs, body="", e=None):
    """📖 The matchup facts (see STORY): [line] - each a real game with its score or a count off the season's game
    files, each only when it argues for our side. Nothing here reads a price or a player's points."""
    out = []
    if not STORY:
        return out
    low = str(body or "").lower()

    def say(key, ways):
        x = v.say("m_" + key, ways, fact=True)
        if x:
            out.append(x)
    won_ = lambda x, t: _line(x, t).startswith("W")       # noqa: E731
    lost_ = lambda x, t: _line(x, t).startswith("L")      # noqa: E731

    # 1. these two already met this season, and the last one was ours - the game, the score, the day
    try:
        met = [x for x in r_ours or [] if oid in (x["home"], x["away"])]
        if met and won_(met[-1], tid):
            where = lambda x: "at a neutral site" if _neutral(x) else "at home" if x["home"] == tid else "on the road"   # noqa: E731
            sc = lambda x: _last_parts(x, tid, pro)[2]    # noqa: E731
            m = met[-1]
            if all(won_(x, tid) for x in met) and len(met) >= 2:
                how = "both times" if len(met) == 2 else f"all {len(met)} times"
                games_ = _and([f"{_an(sc(x).split('-')[0])} {sc(x)} win on {_md(x)}" for x in met[-3:]])
                say("h2h", [f"🆚 {us} beat {the_them} {how} they met this year: {games_}.",
                            f"🆚 These two met {len(met)} times this year and {us} won {how}: {games_}."])
            elif len(met) == 1:
                say("h2h", [f"🆚 {us} already beat {the_them} this year - a {sc(m)} win {where(m)} on {_md(m)}.",
                            f"🆚 These two met this year and {us} got a {sc(m)} win {where(m)} on {_md(m)}.",   # (11/22: the
                            #   old order - the day before "this year" - failed the guard's THIS_YEAR_GAME and was dropped)
                            f"🆚 {_cap(the_them)} already saw {us} this year and took the L - a {sc(m)} win for {us} {where(m)} on {_md(m)}."])
            else:
                say("h2h", [f"🆚 The last time these two met this year {us} got a {sc(m)} win {where(m)}, on {_md(m)}.",
                            f"🆚 {us} took the last one from {the_them} this year - a {sc(m)} win {where(m)} on {_md(m)}."])
    except Exception:                                     # noqa: BLE001 - a fact the files can't give is no line
        pass

    # 2. how THEY have been winning: half or more of their wins by the thinnest margin
    try:
        by = CLOSE_BY.get(lg)
        wins = [x for x in r_theirs or [] if won_(x, oid)]
        thin = [x for x in wins if by and _margin(x, oid) <= by]
        if len(wins) >= THIN_WINS_MIN and len(thin) >= THIN_WINS_CLOSE and 2 * len(thin) >= len(wins) \
                and "one goal" not in low and "squeak" not in low:
            how = {"nhl": "one goal", "mlb": "one run", "nfl": "one score", "ncaaf": "one score"}.get(lg, f"{by} points or less")
            last2 = _and([f"{_last_parts(x, oid, pro)[2]} over {_last_parts(x, oid, pro)[0]}" for x in thin[-2:]])
            say("thin", [f"🎬 {len(thin)} of {_pos(the_them)} {len(wins)} wins this year came by {how} - the last two {last2}. They been squeaking by.",
                         f"🎬 {_cap(the_them)} keep winning by {how}: {len(thin)} of their {len(wins)} wins this year, the last two {last2}.",
                         f"🎬 {len(thin)} of {len(wins)} wins by {how} for {the_them} this year (the last two: {last2}). That's a team living on the edge."])
    except Exception:                                     # noqa: BLE001
        pass

    # 3. what WE have done lately in tonight's kind of building
    try:
        ss = _site_side(g, side)
        at = [x for x in r_ours or [] if ss and x.get(ss) == tid and not _neutral(x)][-SITE_LAST:]
        w = [x for x in at if won_(x, tid)]
        _sr = _site_rec(r_ours, tid, ss) if ss else None
        if len(at) == SITE_LAST and len(w) >= 2 and not (_sr and 2 * _sr[2] > _sr[1]):   # (a winning record there is its own line)
            where = "at home" if ss == "home" else "on the road"
            named = _and([_game_said(x, tid, pro) for x in w[-2:]])
            if not all(_last_parts(x, tid, pro)[2] in low for x in w[-2:]):
                say("site", [f"🏟️ {us} won {'all 3' if len(w) == 3 else '2'} of their last 3 {where} - {named}." if ss == "home" else
                             f"🧳 {us} won {'all 3' if len(w) == 3 else '2'} of their last 3 {where} - {named}.",
                             f"🏟️ Last 3 {where} for {us}: {len(w)} wins, {named}." if ss == "home" else
                             f"🧳 Last 3 {where} for {us}: {len(w)} wins, {named}."])
    except Exception:                                     # noqa: BLE001
        pass

    # 4. where THEY got run this year, in tonight's kind of building
    try:
        ts = _site_side(g, other)
        big = BIG_L.get(lg, 15)
        bad = [x for x in r_theirs or [] if ts and x.get(ts) == oid and not _neutral(x) and lost_(x, oid)
               and -_margin(x, oid) >= big and not (lg in SCHEDULE_FAIR and _tougher(x, oid, tid, e))]
        if len(bad) >= SITE_ROUT_MIN:
            where = "in their own building" if ts == "home" else "on the road"
            named = _and([f"{_last_parts(x, oid, pro)[2]} by {_last_parts(x, oid, pro)[0]}" for x in bad[-2:]])
            n = "twice" if len(bad) == 2 else f"{len(bad)} times"
            say("rout", [f"🥊 {_cap(the_them)} got run {where} {n} already this year - {named}.",
                         f"🥊 {n.capitalize()} this year {the_them} got blown out {where}: {named}."])
    except Exception:                                     # noqa: BLE001
        pass

    # 5. somebody both of us played lately: we beat them, they lost to them
    try:
        now = _t(g["start"])
        recent = lambda x: (now - _t(x["start"])).days <= COMMON_DAYS   # noqa: E731
        ours_w = {_opp_id(x, tid): x for x in r_ours or [] if recent(x) and won_(x, tid) and _opp_id(x, tid) != oid}
        pick = None
        for x in reversed(r_theirs or []):
            o = _opp_id(x, oid)
            if recent(x) and lost_(x, oid) and o in ours_w and not any(
                    won_(y, oid) and _opp_id(y, oid) == o and y["start"] > x["start"] for y in r_theirs):
                pick = (ours_w[o], x)
                break
        if pick and not any(lost_(y, tid) and _opp_id(y, tid) == _opp_id(pick[0], tid) and y["start"] > pick[0]["start"]
                            for y in r_ours):
            a, b = pick
            opp = _last_parts(a, tid, pro)[0]
            sa, sb_ = _last_parts(a, tid, pro)[2], _last_parts(b, oid, pro)[2]
            if not (sa in low and sb_ in low):
                say("common", [f"🔁 They both saw {opp} lately: {us} got a {sa} win on {_md(a)}, {them} took a {sb_} loss on {_md(b)}.",
                               f"🔁 Same opponent, two results - {us} got a {sa} win over {opp} ({_md(a)}); {them} took a {sb_} loss to 'em ({_md(b)})."])
    except Exception:                                     # noqa: BLE001
        pass
    return out


BOTTOM_WHY = (   # the bottom line's matchup reason, by what the line under the pick opened with - no number said twice
    (("🚑", "📉"), lambda us, them: f"{them} {vb(them, 'are', 'is')} short-handed."),
    (("😴", "⏳", "😮"), lambda us, them: f"{them} played last night."),
    (("🆚",), lambda us, them: "Already beat 'em once this year."),
    (("🧹",), lambda us, them: f"{them} been getting run."),
    (("🎬",), lambda us, them: f"{them} been squeaking by."),
    (("🧊", "🗑"), lambda us, them: f"{them} can't buy a win right now."),
    (("🔥",), lambda us, them: f"{us} {vb(us, 'are', 'is')} rolling."),
    (("🏹", "🍀"), lambda us, them: "Been getting the better looks lately."),
    (("🔁",), lambda us, them: f"{us} handled a team that beat {them}."),
)
BOTTOM_CLOSE = ("That's the bet.", "We on {us}.", "Give me {us}.", "Riding {us}.", "{us} the side.")


def story_close(lines, leg, us, them, g, side):
    """🚫 11/19: every line and the one-liner without a price claim (sports_card_guard.scrub); the bottom line = the pick
    and its price + the matchup reason (BOTTOM_WHY, read off the line under the pick) + what the pool said about the
    size, or a short closer when nothing is left."""
    if not NO_OUR_NUMBER or not lines:
        return lines
    import sports_card_guard as _gd
    wl = str(leg.get("why_line") or "")
    if wl:
        leg["why_line"] = _gd.scrub(wl)[0]
    out = []
    try:
        import sports_card_check as _cc
        _fill = _cc.filler
    except Exception:                                     # noqa: BLE001
        _fill = lambda y, l=None: ""                      # noqa: E731
    for x in lines[:-1]:
        y = _gd.scrub(x)[0] if isinstance(x, str) else x
        if y and not (STORY and isinstance(y, str) and _fill(y, leg)):   # (never a line the page's check calls filler)
            out.append(y)
    is_fact = lambda y: isinstance(y, str) and not y.startswith(("⚠️", "🔄", "✅", "🌟", "🟡", "🔒", "💎"))   # noqa: E731
    _sold = set(leg.get("sold") or [])                    # (🗣️ 11/22: the lines the engine's own reasons point at open
    _rk = lambda y: (0 if _sold and _cs_sig(y) in _sold else 1, lead_rank(y))   # noqa: E731  the body, never cut)
    try:                                                  # 🗣️ 11/22 NO REPEATS: the same stat about the same team once
        import sports_card_sell as _cs                    #  (the season's points and the last 3's points are one fact)
        _srt = sorted((y for y in out if is_fact(y)), key=_rk) if STORY else [y for y in out if is_fact(y)]
        _kept, _gone = _cs.dedupe(_srt, us, them, str(leg.get("why_line") or "")) if sell_on(g) else (_srt, [])
        if _gone:
            out = [y for y in out if y not in _gone]
    except Exception:                                     # noqa: BLE001
        pass
    if STORY:                                             # (the matchup first, a scorer's points last - the card reads as
        out = sorted((y for y in out if is_fact(y)), key=_rk) + [y for y in out if not is_fact(y)]   # the case)
    extra = sum(1 for y in out if is_fact(y)) - CARD_MAX
    if extra > 0:                                         # (6-9 fact lines, the owner's range: the weakest ride as spares)
        cut = sorted((y for y in out if is_fact(y)), key=_rk)[-extra:]
        out = [y for y in out if y not in cut]
        leg["spare"] = (cut + list(leg.get("spare") or []))[:SPARE_MAX]
    b = _gd.scrub(lines[-1])[0]
    m = _gd._PICK_HEAD.match(b)
    if m:
        head, rest = m.group(1) + ".", b[m.end():].strip()
        why = next((f(us, them) for ems, f in BOTTOM_WHY if wl.startswith(ems)), "")
        if why and "short-handed" in why and leg.get("inj_ok") is False:
            why = ""                                      # (🧩 11/19: never "they're short-handed" when we are as short)
        if why and why.lower().rstrip(".") in (wl + " " + rest).lower():
            why = ""
        if not rest:
            tail = wl.rstrip().rsplit(". ", 1)[-1] if wl else ""
            opts = [c.format(us=us) for c in BOTTOM_CLOSE if c.format(us=us) != tail]
            rest = opts[sum(map(ord, f"{g.get('id')}|{side}|close")) % len(opts)]
        b = " ".join(y for y in (head, why, rest) if y)
    return out + [b]


LEAD_RANK = ("😴", "⏳", "😮", "🚑", "📉", "🆚", "🥊", "🧲", "🧤", "🥷", "🛡", "🪣", "👌", "🏹", "⚡", "🏃", "🎈", "💥", "🔗", "🏆", "🧭", "🎨",
             "🎁", "💨", "🤝", "📏", "🧊", "🗑", "🔥", "🎬", "🔁", "🍀", "🧹", "🚪", "💪", "🧳", "🏟", "📊")
#   (11/22 THE CARD SELLS THE PICK: the matchup on the floor - the glass, turnovers, the shooting, shots on net, the
#    ground game, off both teams' box scores (sports_card_sell) - ranks right behind the men out / the game they played)
SELL_FROM = "2026-11-22"   # 🗣️ the sell lines + the lead upgrade from this game day ("9999" = the 11/19 card)
WEAK_LEAD = ("", "w_num", "w_any", "w_last", "w_home", "w_deeper", "w_their_road", "w_close_rec", "w_public", "w_rolling")
#   the pools that are only a fallback line under the pick (a 2-game streak, a last game, a home record): a
#   reason-backed matchup line, or the game these two already played, leads instead (lead_upgrade)
REASON_OVER = ("w_their_loss", "w_hot", "w_cold", "w_better", "w_better_ls", "w_p")   # ... and their last loss / a
#   streak / the records give way to a line the engine's own reasons point at (11/23: the line under the pick says the
#   biggest reason we're on the side - a named absence, a back-to-back, a goalie, a quarterback still lead over it)


def sell_on(g):
    """Is the 11/22 sell layer on for this game? (sports_card_sell.SELL, from the SELL_FROM game day)"""
    try:
        import sports_card_sell as _cs
        return bool(_cs.SELL) and str((g or {}).get("start") or "")[:10] >= SELL_FROM
    except Exception:                                     # noqa: BLE001
        return False


def _cs_sig(line):
    import sports_card_sell as _cs
    return _cs.sig(line)


NO_LEAD = ("sched_l", "sched_c")   # ❌ 11/24 (Victor: "he said Illinois state good becuz it lost to st Mary's and Santa
#   Clara"): who beat us / how close we lost never takes the line under the pick


def lead_upgrade(leg, sold, us, them, g, side, body=()):
    """🗣️ 11/22 (the owner: "the breakdowns basically need to sell our picks why we taking them" - the Wizards +170 card
    led with "The Wizards are on a 2-game winning streak" while its body held a 103-94 win over this same team; Robert
    Morris and Nicholls led with the other team's last game). The line under the pick is the single biggest reason
    we're on the side: when it came out of a fallback pool (WEAK_LEAD), a reason-backed sell line leads, else the
    meeting we already won this year (🆚), else the best matchup stat. -> (the new line, the body line it came from)
    or None (the line stands). Never over a named absence / a back-to-back / a goalie / a quarterback reason."""
    import sports_card_sell as _cs
    key = str(leg.get("why_key") or "") if str(leg.get("why_line") or "").strip() else ""
    lean = bool(leg.get("is_lean")) and not _no_leans()
    seed = f"{g.get('id')}|{side}|lead"
    reason = next((s_ for s_ in sold or [] if s_[1]), None)
    if reason and (key in WEAK_LEAD or key in (REASON_OVER if _cs.REASONS_1123 else REASON_OVER[:1])):
        t = _cs.lead_from(reason, us, lean, seed)
        if t:
            return t, reason[0]
    if key not in WEAK_LEAD:
        return None
    h2h = next((x for x in body or [] if str(x).startswith("🆚")), None)
    if h2h:
        t = _cs.lead_of(h2h, us, lean, seed)
        if t:
            return t, h2h
    if body is not None and sold and not reason:          # (the second pass: no reason line, no meeting - the best stat)
        best = next((s_ for s_ in sold if s_[2] not in NO_LEAD), None)   # (11/24: never a line about our own losses)
        t = _cs.lead_from(best, us, lean, seed) if best else None
        if t:
            return t, best[0]
    return None
#   the line under the pick when no reason matched a fact: the strongest MATCHUP fact first - their tired legs, their
#   men out, the game these two already played, where they got run - then form, then the scoreboard


def lead_rank(x):
    t = str(x or "")
    return next((i for i, em in enumerate(LEAD_RANK) if t.startswith(em)), len(LEAD_RANK))


def fill_facts(leg, v, g, us, them, tid, oid, lg, s_ours, s_theirs, r_ours, r_theirs, said, own=None, fin=None, e=None):
    """🧱 The refill (11/18): real facts FOR our side the card hasn't said, best first - used only while a card sits under
    its floor. Each is a number from the box scores / the game files / the price; a fact already on the card (its
    number is there) is skipped."""
    out = []
    low = str(said or "").lower()
    keys = {}                                             # line -> its fact, for the order below

    def say(key, ways, **kw):
        x = v.say(key, ways, **kw)
        if x:
            keys[x] = key
        return x
    nhl = lg == "nhl"
    unit = "goals" if nhl else "points"
    try:                                                  # 1. our top scorer, with his numbers
        skip = list(leg.get("outs") or []) + list(leg.get("absent") or []) + list(leg.get("on_report") or []) \
            + list(leg.get("waiting") or []) + list((leg.get("rep_status") or {}).keys())
        ts = top_scorer(lg, tid, g.get("start") or "9", skip)
        if ts and ts[0].lower() not in low:
            nm, ppg, gp = ts
            if nhl:
                pts = round(ppg * gp)
                out.append(say("fill_star", [f"💯 {nm} has {pts} points in {_pos(us)} last {gp} games.",
                                               f"💯 {_pos(us)} top scorer lately is {nm} - {pts} points in the last {gp} games.",
                                               f"💯 {nm} been producing for {us}: {pts} points over the last {gp}."], fact=True))
            else:
                out.append(say("fill_star", [f"💯 {nm} is giving {us} {ppg:.0f} a night over the last {gp} games he's played.",
                                               f"💯 {_pos(us)} top scorer {nm} is putting up {ppg:.0f} a night lately ({gp} games).",
                                               f"💯 {nm} been cooking for {us} - {ppg:.0f} a night over his last {gp}."], fact=True))
        if lg in ("nfl", "ncaaf"):                        # football: our back and our top catcher, the yards they got
            for stat_, ways in (("rushingYards", ("💯 {nm} has run for {y} yards over {pu} last {gp} games.",
                                                  "💯 {y} yards on the ground for {nm} in {pu} last {gp} games.")),
                                ("receivingYards", ("💯 {nm} has {y} receiving yards over {pu} last {gp} games.",
                                                    "💯 {nm} caught {y} yards' worth in {pu} last {gp} games."))):
                fs = top_scorer(lg, tid, g.get("start") or "9", skip, stat=stat_)
                if fs and fs[0].lower() not in low:
                    out.append(say("fill_" + stat_, [w.format(nm=fs[0], y=round(fs[1] * fs[2]), pu=_possm(us), gp=fs[2])
                                                       for w in ways], fact=True))
    except Exception:                                     # noqa: BLE001
        pass
    dec = 1 if nhl or lg == "mlb" else 0
    pu, pt = _pts3(_real(s_ours, tid, lg), tid, dec=dec), _pts3(_real(s_theirs, oid, lg), oid, dec=dec)   # (11/22: no tune-ups)
    lately = "over their last" in low or "last 3" in low or "last 2" in low or "lately" in low
    _gap = 0.3 if nhl or lg == "mlb" else 2                # (a 1-point edge on the scoreboard says nothing)
    if pu and pu[0] - pu[1] >= _gap and not lately:             # 2. our scoreboard lately, when we're winning it
        net = round(pu[0] - pu[1], 1)
        out.append(say("fill_pts", [f"📊 {us} {vb(us, 'are', 'is')} winning by {net:g} a game over their last {pu[2]} ({pu[0]:g} scored, {pu[1]:g} allowed).",
                                      f"📊 Last {pu[2]} for {us}: {pu[0]:g} scored a game, {pu[1]:g} allowed.",
                                      f"📊 {us} put up {pu[0]:g} a game over their last {pu[2]} and gave up {pu[1]:g}."], fact=True))
    elif pt and pt[1] - pt[0] >= _gap and not lately:           # ... or theirs, when they're losing it
        out.append(say("fill_pts", [f"📊 {them} have been outscored {pt[1]:g} to {pt[0]:g} a game over their last {pt[2]}.",
                                      f"📊 Last {pt[2]} for {them}: {pt[0]:g} scored a game, {pt[1]:g} given up."], fact=True))
    year = bool(re.search(r"(?:📊|🛡)[^📊🛡⚠✅]*?(?:this year|on the year|this season|against D1 teams)", str(said)))
    fmt = (lambda x: f"{x:.1f}") if nhl or lg == "mlb" else (lambda x: f"{round(x)}")
    # 🗣️ 11/22 (the Robert Morris card: "New Mexico St this season: 78 points a game allowed, 66 scored" right above
    # "outscored 72 to 63 a game over their last 3" - the same stat twice; and the season number counted a win over a
    # non-D1 school): (a) college hoops form reads D1 games only - the season line too, and it says so; (b) ONE
    # scoreboard line a team - the season's, unless the last 3 are a different story (a lot worse than the year).
    _sell = sell_on(g)
    d1_u, d1_t = (_real(r_ours, tid, lg), _real(r_theirs, oid, lg)) if _sell else (r_ours, r_theirs)
    yr_u = ("against D1 teams", "against D1 teams", "against D1 teams") if len(d1_u) != len(r_ours) else ("On the year", "this season", "this year")
    yr_t = ("against D1 teams", "against D1 teams", "against D1 teams") if len(d1_t) != len(r_theirs) else ("On the year", "this season", "this year")
    need_y = 5 if lg != "ncaab" or not _sell else 3
    if not _sell:
        need_y = 0                                        # (the 11/19 card: the season lines needed 5 games in all)
    _big3 = 0.8 if nhl or lg == "mlb" else 6
    if len(r_ours) >= 5 and len(d1_u) >= need_y and not year:   # 3. our season on the scoreboard, when it's in the black
        pg = _per_game(d1_u, tid)
        if pg and pg[0] - pg[1] >= (0.3 if nhl or lg == "mlb" else 2):
            _l3 = next((x for x in out if x and keys.get(x) == "fill_pts" and them not in str(x)), None)
            if pu and _l3 and _sell:
                if (pu[0] - pu[1]) - (pg[0] - pg[1]) >= _big3:
                    pg = None                              # (hotter lately than on the year: the last 3 say it)
                else:
                    out.remove(_l3)
            if pg:
                out.append(say("fill_year", [f"📊 {yr_u[0][:1].upper() + yr_u[0][1:]} {us} {vb(us, 'score', 'scores')} {fmt(pg[0])} {unit} a game and {vb(us, 'give', 'gives')} up {fmt(pg[1])}.",
                                               f"📊 {us} {yr_u[1]}: {fmt(pg[0])} {unit} a game scored, {fmt(pg[1])} allowed.",
                                               f"📊 {fmt(pg[0])} a game for {us} {yr_u[2]}, {fmt(pg[1])} against. They outscore people."], fact=True))
    if len(r_theirs) >= 5 and len(d1_t) >= need_y and not year:   # 4. their season, when it's in the red
        pg = _per_game(d1_t, oid)
        if pg and pg[1] - pg[0] >= (0.3 if nhl or lg == "mlb" else 2):
            _l3 = next((x for x in out if x and keys.get(x) == "fill_pts" and them in str(x)), None)
            if pt and _l3 and _sell:
                if (pt[1] - pt[0]) - (pg[1] - pg[0]) >= _big3:
                    pg = None                              # (a lot worse lately than on the year: the last 3 say it)
                else:
                    out.remove(_l3)
            if pg:
                out.append(say("fill_year_t", [f"📊 {yr_t[0][:1].upper() + yr_t[0][1:]} {them} {vb(them, 'give', 'gives')} up {fmt(pg[1])} {unit} a game and {vb(them, 'score', 'scores')} {fmt(pg[0])}.",
                                                 f"📊 {them} {yr_t[1]}: {fmt(pg[1])} {unit} a game allowed, {fmt(pg[0])} scored. They get outscored."], fact=True))
    if len(r_ours) >= 5 and len(r_theirs) >= 5 and not year and not any(str(x).startswith("📊") and "year" in str(x) or
                                                                        "this season" in str(x) for x in out):
        #   (11/22, the UT Rio Grande card: "On the year UT Rio Grande allows 62 a game, Austin Peay 66" - two blowouts of
        #    non-D1 schools in ours, three in theirs: college hoops reads D1 games only, 3+ of them a side, and says so)
        _both = len(d1_u) >= need_y and len(d1_t) >= need_y
        _cut = len(d1_u) != len(r_ours) or len(d1_t) != len(r_theirs)
        pu_, pt_ = (_per_game(d1_u, tid), _per_game(d1_t, oid)) if _both else (None, None)   # 4b. the matchup on the year
        _ty, _oy = ("against D1 teams", "Against D1 teams") if _cut else ("this year", "On the year")
        step = 0.1 if nhl or lg == "mlb" else 3 if _sell and lg in ("nba", "ncaab") else 1   # (75 against 76 says nothing)
        try:                                              # 🏫 11/24: THEIR schedule clearly tougher (the SCHED_EDGE guard) -
            import sports_card_sell as _cs2               # never "we score more / allow less" off season averages that
            if lg in SCHEDULE_FAIR and e is not None and not _cs2.fair_cmp(d1_u, d1_t, tid, oid, e):   # don't know who
                pu_ = pt_ = None                          # each team played
        except Exception:                                 # noqa: BLE001
            pass
        if pu_ and pt_ and pt_[1] - pu_[1] >= step:
            out.append(say("fill_d", [f"🛡️ {them} {vb(them, 'give', 'gives')} up {fmt(pt_[1])} {unit} a game {_ty}. {us} {vb(us, 'give', 'gives')} up {fmt(pu_[1])}.",
                                        f"🛡️ {_oy} {us} {vb(us, 'allow', 'allows')} {fmt(pu_[1])} a game, {them} {fmt(pt_[1])}."], fact=True)
                       if fmt(pt_[1]) != fmt(pu_[1]) else "")
        elif pu_ and pt_ and pu_[0] - pt_[0] >= step and fmt(pu_[0]) != fmt(pt_[0]):
            out.append(say("fill_o", [f"📊 {us} {vb(us, 'score', 'scores')} {fmt(pu_[0])} {unit} a game {_ty}; {them} {vb(them, 'score', 'scores')} {fmt(pt_[0])}.",
                                        f"📊 {_oy} {us} put up {fmt(pu_[0])} a game, {them} {fmt(pt_[0])}."], fact=True))
    for gs, t_id, nm_, ours_ in ((s_ours, tid, us, True), (s_theirs, oid, them, False)):   # 6. the last 10
        l10 = _last_n(gs, t_id, 10)
        if any(nm_ in seg for seg in re.findall(r"🗓[^🗓⚠✅📋📅💯📊🏟🧳🥊]*", str(said))):
            continue                                      # (11/19, the Nuggets card: "won 6 of their last 10" next to
            #                                               "3-2 over their last 5" - one form line a team on a card)
        if l10 and "last 10" not in low and ((ours_ and l10[0] >= 6) or (not ours_ and l10[0] <= 4)):
            out.append(say("fill_l10" + ("" if ours_ else "_t"),
                             [f"🗓️ {nm_} won {l10[0]} of their last 10.", f"🗓️ {l10[0]} wins in the last 10 for {nm_}."] if ours_ else
                             [f"🗓️ {nm_} won only {l10[0]} of their last 10.", f"🗓️ Just {l10[0]} wins in the last 10 for {nm_}."],
                             fact=True))
    try:                                                  # 7. our second scorer
        ts2 = None if STORY and STAR_ONE else top_scorer(lg, tid, g.get("start") or "9", skip, rank=1)
        if ts2 and ts2[0].lower() not in low:
            nm, ppg, gp = ts2
            out.append(say("fill_star2", [f"💯 {nm} has {round(ppg * gp)} points in his last {gp} games for {us}."] if nhl else
                             [f"💯 {nm}: {ppg:.0f} a night for {us} over his last {gp} games.",
                              f"💯 {nm} is putting up {ppg:.0f} a night for {us} too ({gp} games)."], fact=True))
    except Exception:                                     # noqa: BLE001
        pass
    try:                                                  # 5. the price in plain words (when the bottom line didn't)
        f = card_fair(leg, own, beat=True) if own is not None and leg.get("market") == "ml" else None
        if f and f not in said and not STORY:             # (11/19: the price is the units line's and the bottom line's)
            o = _am(leg["odds"])
            out.append(say("fill_price", [f"💵 We price {us} at {f}. The book's paying {o}.",
                                            f"💵 Our number on {us} is {f} and the book's hanging {o}.",
                                            f"💵 {o} at the book on a side we make {f}."], fact=True))
    except Exception:                                     # noqa: BLE001
        pass
    o_ = leg.get("odds") or 0                             # 8. what a real dog price asks of us, the way a bettor says it
    if leg.get("market") == "ml" and o_ >= 150 and "times in" not in low and "time in" not in low and not STORY:
        #   (never rounded in our favor: +150 breaks even at 4 in 10, +200 at 1 in 3, +234 at 3 in 10, +300 at 1 in 4)
        how = "4 times in 10" if o_ < 200 else "1 time in 3" if o_ < 234 else "3 times in 10" if o_ < 300 else "1 time in 4"
        out.append(say("fill_need", [f"💵 At {_am(o_)} {us} only gotta win this about {how} for the bet to pay.",
                                       f"💵 {_am(o_)} on {us}: about {how} is all it takes for this bet to pay.",
                                       f"💵 Plus money: at {_am(o_)}, {us} winning about {how} is all we need."], fact=True))
    # 🏀 11/20 (the board check - the Niagara +2.5 ½u stack play posted with NO fact line: a winless side on a spread, so
    # every "we're winning" fact was empty and the two facts the files did hold for the bet had no line): a SPREAD
    # play's own facts - our covers running, and a record of theirs built on non-D1 schools.
    try:
        if leg.get("market") == "spread" and "cover" not in low and "spread" not in low:
            lined = [x for x in s_ours or [] if _fnum(x.get("spread_home")) is not None
                     and str(x.get("home_score") or "") != "" and str(x.get("away_score") or "") != ""]
            run, last = 0, None
            for x in reversed(lined):
                home_ = x["home"] == tid
                ln = _fnum(x["spread_home"]) * (1 if home_ else -1)
                mg = (int(x["home_score"]) - int(x["away_score"])) * (1 if home_ else -1)
                if mg + ln <= 0:
                    break
                run += 1
                if last is None:
                    last = (ln, mg, x["away_name"] if home_ else x["home_name"], home_)
            if run >= 2 and last:
                ln, mg, opp_, home_ = last
                where = f"against {opp_}" if home_ else f"at {opp_}"
                how = (f"they won it by {mg}" if mg > 0 else f"the game ended {abs(mg)} apart") if ln > 0 else f"they won by {mg}"
                got = f"getting {ln:g} {where}" if ln > 0 else f"laying {abs(ln):g} {where}"
                out.append(say("fill_cov", [f"🎟️ {us} beat the spread in their last {run} games - the last one {got}, {how}.",
                                              f"🎟️ {run} straight covers for {us}. Last time out, {got}, {how}."], fact=True))
    except Exception:                                     # noqa: BLE001
        pass
    try:
        if lg == "ncaab" and r_theirs and _D1.get("set") is not None and "non-d" not in low and "division i" not in low:
            wins = [x for x in r_theirs if (int(x["home_score"]) > int(x["away_score"])) == (x["home"] == oid)]
            soft = [x for x in wins if non_d1(lg, _opp_id(x, oid))]
            if len(wins) == 1 and len(soft) == 1 and len(r_theirs) >= 4 and _sell:   # (11/22: New Mexico St, 1-4 - the 1 a 73-66
                x = soft[0]                                                 #  home win over Western NM, a non-D1 school)
                nm1 = x["away_name"] if x["home"] == oid else x["home_name"]
                sc = _line(x, oid).split()[1]
                out.append(say("fill_nond1", [f"📋 {_pos(them)} only win this year is a {sc} game with {nm1}, a school that ain't even Division I.",
                                                f"📋 The one win {them} got this year came in a {sc} game with {nm1}, and that ain't a Division I school."], fact=True))
            if len(wins) >= 2 and len(soft) == len(wins):
                nm_ = [x["away_name"] if x["home"] == oid else x["home_name"] for x in soft]
                n_ = len(wins)
                cnt = "Both" if n_ == 2 else f"All {n_}"
                out.append(say("fill_nond1", [f"📋 {cnt} of {_pos(them)} wins came over schools that aren't Division I ({_and(nm_[:3])}).",
                                                f"📋 {them} got {'both' if n_ == 2 else f'all {n_}'} of their wins off non-Division I schools - {_and(nm_[:3])}."], fact=True))
    except Exception:                                     # noqa: BLE001
        pass
    try:                                                  # 9. the deep refill (deep_facts), each fact in its place
        deep = {} if not DEEP_FILL else deep_facts(leg, v, g, us, them, tid, oid, lg, s_ours, s_theirs, r_ours, r_theirs, said, fin, e)
    except Exception:                                     # noqa: BLE001
        deep = {}
    for k, x in deep.items():
        keys[x] = "deep_" + k
        out.append(x)
    rank = lambda x: next((r for pre, r in FILL_ORDER if keys.get(x, "").startswith(pre)), 5.0)   # noqa: E731
    if STORY:                                             # (11/19: a scorer's points are the last thing a card reaches for)
        rank = lambda x, r_=rank: 8.5 if keys.get(x, "").startswith(("fill_star", "fill_rushingYards", "fill_receivingYards")) else r_(x)   # noqa: E731
    got = sorted((x for x in out if x), key=rank)         # (a stable sort: ties keep the order they were found in)
    if STORY and STAR_ONE:                                # (one 💯 line a card - football's back and catcher included)
        first = next((x for x in got if str(x).startswith("💯")), None)
        got = [x for x in got if not str(x).startswith("💯") or x is first]
    return got


FILL_ORDER = (   # the refill, best first: a name with numbers, then how the two sides really play, the price last
    ("fill_star2", 7.0), ("fill_star", 0.0), ("fill_rushingYards", 0.5), ("fill_receivingYards", 0.6),
    ("deep_gone", 1.0), ("fill_pts", 1.5), ("deep_role", 2.0), ("deep_late", 3.0), ("deep_box", 4.0),
    ("fill_year", 4.5), ("fill_d", 4.7), ("fill_o", 4.7), ("deep_win", 5.0), ("deep_big", 3.5), ("deep_close", 5.5),
    ("deep_romp", 3.7), ("deep_depth", 4.2),
    ("deep_start", 6.5), ("fill_l10", 6.0), ("deep_cover", 8.0),
    ("fill_cov", 1.2), ("fill_nond1", 1.3),
    ("fill_price", 9.0), ("fill_need", 10.0))


def more_facts(leg, v, g, us, them, the_us, the_them, pro, tid, oid, start, s_ours, s_theirs, r_ours, r_theirs,
               ours, theirs, FORM, inj, lg, side, other, out, heat, heat_t, last_vs, e=None):
    """The facts the card hasn't said yet (10/25) - every line a score, a record, a name or a count from the leg or the
    game data; nothing here guesses. A fact the lines above already carry (its number is in the body) isn't repeated.
    (10/27, the owner: "a lot of facts that support the opposing team") Every fact here knows which side it favors: the
    ones for us are body lines in his voice, the even ones carry a number or they're gone, and the ones for THEM go to
    v.knock - the single biggest posts as the ⚠️ risk line, the rest never make the card."""
    add = []
    body = _body(out) + " " + str(leg.get("why_line") or "").lower()
    D = lambda d: f"{d} day{'s' if d != 1 else ''}"
    N = lambda d: f"{d} night{'s' if d != 1 else ''}"
    unit = "goals" if lg == "nhl" else "runs" if lg == "mlb" else "points"
    nhl = lg == "nhl"

    # 📖 11/19 THE STORY OF THE GAME: the matchup facts first (matchup_facts) - the game these two already played, how
    # they've been winning, where they got run, what we did in this kind of building, a common opponent
    try:
        story = matchup_facts(leg, v, g, us, them, the_us, the_them, pro, tid, oid, lg, side, other, r_ours, r_theirs,
                              body, e)
    except Exception:                                     # noqa: BLE001 - the story never breaks a card
        story = []
    add += story
    body += " " + _body(story)

    # both last games, with the scores (the 📅 line above only prints when ours was a W and theirs an L)
    if s_ours and not any(str(x).startswith("📅") for x in out):
        a = _said_d1(s_ours[-1], tid, pro, lg)           # (11/4: "95-57 win over Mount Marty (a non-D1 school)")
        wu = _line(s_ours[-1], tid).startswith("W")
        # 👍 11/18 (cards_1118, the owner on the Nuggets card: "the Celtics come in off a 115-105 loss to the Magic; the
        # Nuggets off a 117-105 loss to the Suns" - "doesn't make the Nuggets look good"): each last game is said only
        # when it argues for us - OUR win, THEIR loss. Our loss and their win are knocks for the one ⚠️ line ("The Kraken
        # won their last one too", "so they feeling themselves too", "Both won last time" are gone), and a score the
        # card already carries is never said again.
        sc_a = _last_parts(s_ours[-1], tid, pro)[2]
        said_a = sc_a in body or "-".join(reversed(sc_a.split("-"))) in body
        if "non-D1" in a and "non-d1" not in body:        # (11/4: a tune-up is always named for what it is, even when
            said_a = False                                #  the one-liner already gave its score)
        us_ways = [f"📅 {us} come off a {a}.", f"📅 Last time out, {us} got a {a}.",
                   f"📅 Fresh off a {a} for {us}.", f"📅 {_cap(the_us)} handled business last time, a {a}."]
        if s_theirs:
            b = _said_d1(s_theirs[-1], oid, pro, lg)
            wt = _line(s_theirs[-1], oid).startswith("W")
            sc_b = _last_parts(s_theirs[-1], oid, pro)[2]
            said_b = sc_b in body or "-".join(reversed(sc_b.split("-"))) in body
            same = s_ours[-1].get("id") is not None and s_ours[-1].get("id") == s_theirs[-1].get("id")
            them_ways = [f"📅 {_cap(the_them)} come in off a {b}.", f"📅 Last time out {the_them} took a {b}.",
                         f"📅 {_cap(the_them)} are fresh off a {b}.", f"📅 {them} off a {b} last time out."]
            if same and wu and not said_a:                # (these two just played each other: one game, said once)
                add.append(v.say("f_last", [f"📅 These two just played - {us} took it, a {a}.",
                                            f"📅 {us} beat {them} last time out, a {a}."]))
            elif same and not wu:
                v.knock(4, f"{them} beat {us} {sc_b} last time out")
            elif same:
                pass
            elif wu and not wt:
                if not (said_a and said_b):
                    add.append(v.say("f_last", [f"📅 {us} come off a {a}; {them} come off a {b}.",
                                                f"📅 Last time out: {us} took a {a}, {them} took a {b}."]
                                     if not said_a and not said_b else us_ways if not said_a else them_ways))
            elif wu and wt:
                if not said_a:
                    add.append(v.say("f_last", us_ways))
                v.knock(2, f"{them} come off a {b}")
            elif not wu and not wt:
                if not said_b:
                    add.append(v.say("f_last", them_ways))
                v.knock(2, f"{us} come off a {a}")
            else:                                         # (we lost, they won: the knock, never a reason)
                v.knock(4, f"{us} come off a {a} while {them} just took a {b}")
        elif wu:
            if not said_a:
                add.append(v.say("f_last", us_ways))
        else:
            v.knock(2, f"{us} come off a {a}")

    # our own skid is a knock; their heater is a knock (10/27 - neither is a reason to bet us)
    if heat.startswith("lost"):
        n = int(heat.split()[1])
        if f"{n} straight" not in body and f"{n} in a row" not in body:
            v.knock(6, f"{us} have dropped {n} straight")
    if heat_t.startswith("won"):
        n = int(heat_t.split()[1])
        if f"{n} straight" not in body and f"{n} in a row" not in body and f"{them} {n}" not in body:
            v.knock(5, f"{them} come in on {_an(n)} {n}-game heater" if n >= HOT_MIN else f"{them} have won {n} straight")   # (11/11: a heater is 3+)

    # home / road records, both sides (the 🏟️ / 🧳 line above is ours only)
    ts = _site_rec(r_theirs, oid, _site_side(g, other))
    if ts and ts[1] >= 2 and f"{ts[3]} " not in body and f"{them} are {ts[3]}" not in body:
        where = "at home" if ts[0] == "home" else "on the road"
        if 2 * ts[2] < ts[1]:                              # their bad record at this site: a fact for us
            add.append(v.say("f_site", [f"🏟️ {them} are {ts[3]} {where} this year. That ain't a fortress." if ts[0] == "home"
                                        else f"🧳 {them} are {ts[3]} {where} this year. They don't travel.",
                                        f"🏟️ {ts[3]} {where} for {them}. {_cap(_pos(them))} own building ain't saving them." if ts[0] == "home"
                                        else f"🧳 {ts[3]} {where} for {them} this season. They hate leaving the house.",
                                        f"🏟️ {them} {where} this season: {ts[3]}. Their own crowd's been watching 'em lose." if ts[0] == "home"
                                        else f"🧳 {them} {where} this season: {ts[3]}. Road trips ain't their thing.",
                                        f"🏟️ {ts[3]} {where} for {them}." if ts[0] == "home"
                                        else f"🧳 {ts[3]} {where} for {them}. Road trips been rough on 'em."]))
        elif 2 * ts[2] > ts[1]:                            # their good record at this site: the knock
            v.knock(3, f"{them} are {ts[3]} {where} this year")
    us_site = _site_rec(r_ours, tid, _site_side(g, side))
    if us_site and us_site[1] >= 2 and not any(str(x)[:1] in "🏟🧳" and us in str(x) for x in out) \
            and not any(us in k for _, k in v.knocks if us_site[3] in k):
        where = "at home" if us_site[0] == "home" else "on the road"
        if 2 * us_site[2] > us_site[1]:
            add.append(v.say("f_site", [f"🏟️ {us} are {us_site[3]} {where} this year." if us_site[0] == "home"
                                        else f"🧳 {us} are {us_site[3]} {where} this year.",
                                        f"🏟️ {us} {where}: {us_site[3]}. They handle their business there." if us_site[0] == "home"
                                        else f"🧳 {us} {where}: {us_site[3]}. Hostile crowds don't bother 'em.",
                                        f"🏟️ {us_site[3]} {where} for {us} this year." if us_site[0] == "home"
                                        else f"🧳 {us_site[3]} {where} for {us} this year."]))
        elif 2 * us_site[2] < us_site[1]:
            v.knock(3, f"{us} are {us_site[3]} {where} this year")

    # rest: a back-to-back WITH the score of the game they played last night; an extra day said for us, or the knock
    if ours and theirs:
        d_us, d_them = _days(start, _t(ours[-1]["start"])), _days(start, _t(theirs[-1]["start"]))
        h_them = (start - _t(theirs[-1]["start"])).total_seconds() / 3600
        h_us = (start - _t(ours[-1]["start"])).total_seconds() / 3600
        rested = any(str(x)[:1] in "🛌😴" for x in out) or "days off" in body or "days of rest" in body or "more days" in body
        if h_them <= B2B_HOURS < h_us and not rested:
            b = _said(theirs[-1], oid, pro)
            add.append(v.say("f_b2b", [f"⏳ {them} played last night - a {b} - and {us} had {D(d_us)} off. Tired legs vs fresh ones.",
                                       f"⏳ Second night in a row for {them}, fresh off a {b}. {us} sat {D(d_us)} and watched.",
                                       f"⏳ {them} were on the ice last night ({b}); {us} come in on {D(d_us)} rest. That matters late." if nhl
                                       else f"⏳ {them} played last night ({b}); {us} come in on {D(d_us)} rest. That matters late.",
                                       f"⏳ {them} played yesterday, a {b}, and now they gotta do it again. {us} had {D(d_us)} off."]))
        elif h_us <= B2B_HOURS < h_them:
            a = _said(ours[-1], tid, pro)
            v.knock(7, f"{us} played last night (a {a}) and {them} sat {D(d_them)}")
        elif not rested and d_us <= 12 and d_them <= 12 and not b2b_only(lg):   # (11/15: REST_B2B_ONLY)
            #   (11/18, cards_1118: "Packers come in on 7 days rest; Vikings are on 6 days" - one day more in a football
            #    week is no argument a bettor cares about; a rest line needs 2+ days, either way)
            if d_us - d_them >= 2:
                add.append(v.say("f_rest", [f"⏳ {us} got the extra day: {D(d_us)} off to {_pos(them)} {D(d_them)}.",
                                            f"⏳ Fresher legs on our side - {us} had {D(d_us)} off, {them} {D(d_them)}.",
                                            f"⏳ {us} come in on {D(d_us)} rest; {them} are on {D(d_them)}."]))
            elif d_them - d_us >= 2:
                v.knock(2, f"{them} had {D(d_them)} off to {_pos(us)} {D(d_us)}")
            #   (even rest: no line - "both sides had 2 days between games" told the owner nothing, 10/27)

    # the trip in miles (the 🧳 line above needs 1,000+)
    for c in leg.get("ctx") or []:
        mi = c.get("mi") or 0
        if c.get("k") == "trip" and 300 <= mi < 1000 and "-mile" not in body and str(g.get("neutral")) != "1":
            if leg.get("side") == "home":
                add.append(v.say("f_trip", [f"🧳 {_cap(the_them)} traveled {_mi(mi)} miles for this one. Long way to come for an L.",
                                            f"🧳 {_mi(mi)} miles on the road for {the_them}, and {the_us} slept in their own beds.",
                                            f"🧳 {_cap(the_them)} made a {_mi(mi)}-mile trip for this one. We didn't go anywhere."]))
            else:
                v.knock(1, f"{the_us} traveled {_mi(mi)} miles for this one")

    # who's out on THEIR side, named (the 🚑 card line is ours; the key-man lines name one player); ours is the knock
    _who_plays = lambda names, team_id: who_plays_only(names, lg, team_id, g.get("start") or "9")   # noqa: E731
    theirs_out = [str(x) for x in (leg.get("opp_outs") or []) if x]
    theirs_out = _who_plays([x for x in theirs_out if x.split(" (")[0].lower() not in body], oid)[:4]
    if leg.get("inj_ok") is False:                        # 🧩 11/19 (the Warriors card): no "they're missing X, Y" line
        theirs_out = []                                   #  while our side is as short-handed - the 🚑 header has both
    #   🚑 11/19: the men the line under the pick names (named_out_ways) are said there, once - this line takes the rest
    _lead = (named_out_ways(leg, g, them, them) or (None, []))[1]
    _ln = lambda x: re.sub(r"[^a-z]", "", str(x).split(" (")[0].lower())   # noqa: E731
    _also = bool(_lead) and any(_ln(x) in {_ln(w) for w in _lead} for x in theirs_out)
    if _lead:
        theirs_out = [x for x in theirs_out if _ln(x) not in {_ln(w) for w in _lead}]
    # 🧱 11/19 (the owner on the Colts' two tackles: "there's no pass protection ... backups ... teams could get eat
    # up"): a lineup more than one starter short at one spot is SAID in plain words with the names - "Both starting
    # tackles out - backups protecting the QB." Theirs rides the 🚑 line; ours is only ever the ⚠️ knock.
    _hole = lambda k: (lambda h: f" {h[0].upper()}{h[1:]}." if h else "")(str(leg.get(k) or "").strip())   # noqa: E731
    if theirs_out and coherent_on(g) and not _hole("opp_holes"):
        # 🚑 11/24 board check (the Magic +114 card: "CARD CHECK (render): the 🚑 chip's names again: 🚑 Pistons are
        # without Duncan Robinson (F)." on every run of the day): the card's 🚑 header already names who's out on both
        # teams - a body line that is only those names again was written, counted toward the card's floor and then cut
        # on every render. Not written; a line that says what the absence DOES (a spot two starters short) still is.
        theirs_out = []
    if theirs_out and _also:
        add.append(v.say("f_outs_also", [f"🚑 Also out for {them}: {', '.join(theirs_out)}.{_hole('opp_holes')}",
                                         f"🚑 {them} are down {', '.join(theirs_out)} too.{_hole('opp_holes')}"]))
    elif theirs_out:
        nm = ", ".join(theirs_out)
        hw = _hole("opp_holes")
        add.append(v.say("f_outs", [f"🚑 {them} are without {nm}.{hw}",
                                    f"🚑 Out for {them}: {nm}.{hw}",
                                    f"🚑 No {nm} for {them}.{hw}",
                                    f"🚑 {nm} won't suit up for {them}.{hw}",
                                    f"🚑 {them} gotta play without {nm}.{hw}",
                                    f"🚑 {them} are down {nm} tonight.{hw}"]))
    ours_out = [str(x) for x in (leg.get("outs") or []) if x]
    ours_out = _who_plays([x for x in ours_out if x.split(" (")[0].lower() not in body], tid)[:4]
    if ours_out and not any(str(x).startswith("🚑") and us in str(x) for x in out) \
            and not any(ours_out[0].split(" (")[0] in k for _, k in v.knocks):
        if leg.get("holes"):                              # (11/19: our own thin line is the knock, said straight)
            v.knock(9, f"{us} go without {', '.join(ours_out)} - {leg['holes']}")
        else:
            v.knock(8 if len(ours_out) >= 3 else 5, f"{us} go without {', '.join(ours_out)}")

    # the goalies / QBs with their numbers - said FOR us when ours has the better numbers, the knock when theirs does
    role = sp.ROLE.get(lg)
    mine, his = next(((n, t, k) for (o_, m_), (n, t, k) in FORM.items() if o_), None), \
        next(((n, t, k) for (o_, m_), (n, t, k) in FORM.items() if not o_), None)
    #   (11/16 EVERY FACT TRUE: "Goalies - Bruins: Jeremy Swayman ..." (DiPietro started), "Golden Knights' goalie Carter
    #    Hart has ..." (Adin Hill started) - three of these lines carried no tag, so a guess read as tonight's starter.
    #    Every goalie line now says what he is: confirmed, expected (the page's 'likely'), projected, or last time out.)
    tag = lambda k: ("confirmed in net" if k is True else "expected in net, not confirmed" if k == "likely"
                     else "projected, not confirmed" if k == "projected" else "in net last time out")
    note = lambda k: ("" if k is True else ", expected in net, not confirmed" if k == "likely"
                      else ", projected, not confirmed" if k == "projected" else ", in net last time out")
    #   🥅 11/19 (the owner on the Ducks card: "talk about ... goalie" - Blackwood was in net for the Avalanche in Utah
    #   the night before, so tonight's net goes to the other man): THEIR goalie in net last night on a back-to-back and a
    #   different man projected / expected tonight is said plainly, the man's tag kept (never stated as confirmed).
    try:
        if role == "G" and his and his[2] is not True and (g.get("start") or "")[:10] >= GOALIE_B2B_FROM:
            _rows = sp.CACHE.get(lg) or []
            _oside = "away" if leg.get("side") == "home" else "home"
            _prev = [r for r in _rows if str(r["team"]) == str(g.get(_oside)) and r["start"] < g["start"]
                     and r.get("role", "G") == "G"]
            if _prev and _prev[-1]["player"] != his[0] and sp._hours(_prev[-1]["start"], g["start"]) < 30:
                _l = _prev[-1]["player"]
                add.append(v.say("f_net_b2b", [
                    f"🥅 {_l} was in net for {them} last night, so it's {his[0]} ({tag(his[2])}) tonight.",
                    f"🥅 {them} used {_l} last night - {his[0]} ({tag(his[2])}) gets this one.",
                    f"🥅 {_l} played last night for {them}; {his[0]} ({tag(his[2])}) is the next man up."]))
    except Exception:                                     # noqa: BLE001 - no box scores: no line
        pass
    if role == "G" and mine and his and mine[0].lower() not in body and his[0].lower() not in body:
        sm_, sh_ = _sv(mine[1]), _sv(his[1])
        if sm_ is not None and sh_ is not None and sm_ > sh_ + 0.005:
            add.append(v.say("f_net", [f"🥅 Goalie edge is ours: {mine[0]} ({tag(mine[2])} for {us}) has {mine[1]}; {his[0]} ({tag(his[2])} for {them}) has {his[1]}.",
                                       f"🥅 {mine[0]} ({tag(mine[2])} for {us}) has been the better goalie - {mine[1]}. {his[0]} ({tag(his[2])} for {them}): {his[1]}.",
                                       f"🥅 {his[0]} ({them}{note(his[2])}) has {his[1]}; {mine[0]} ({us}{note(mine[2])}) has {mine[1]}. We like our goalie more."]))
        elif sm_ is not None and sh_ is not None and sh_ > sm_ + 0.005 and not (
                hot_overpay(leg) and (g.get("start") or "")[:10] >= HOT_RUN_LINE_FROM):   # (11/19: his hot run IS our
            v.knock(6, f"{his[0]} ({them}{note(his[2])}) is at a {sh_:.3f} save % over his last 3 starts to {mine[0]}'s "
                       f"{sm_:.3f}{'' if mine[2] is True else ' (our guy expected in net, not confirmed)' if mine[2] == 'likely' else ' (our projected guy, not confirmed)' if mine[2] == 'projected' else ' (our guy in net last time out)'}")   # (11/5 pre-board
            #   check: an unconfirmed starter is the LAST starter - the Ducks card named Brossoit while the goalie page had
            #   Dostal projected; the line says whose numbers they are, never that he's in net tonight)
        #   (11/18, cards_1118: two goalies with the same numbers - "A wash in net" - and the other goalie's fine numbers
        #    alone are no argument for our side: no line. The same for two quarterbacks even on the numbers, and for our
        #    quarterback's so-so line by itself.)
    elif role == "QB" and mine and his and mine[0].lower() not in body and his[0].lower() not in body:
        qm, qh = _qb_nums(mine[1]), _qb_nums(his[1])
        ours_better = qm and qh and (qm[0] - qm[1], qm[2]) > (qh[0] - qh[1], qh[2]) and qm[2] >= qh[2]
        theirs_better = qm and qh and (qh[0] - qh[1], qh[2]) > (qm[0] - qm[1], qm[2]) and qh[2] >= qm[2]
        if ours_better:
            add.append(v.say("f_qb", [f"🎯 Our quarterback's been better: {mine[0]} has {mine[1]} for {us}; {his[0]} has {his[1]} for {them}.",
                                      f"🎯 {mine[0]} ({us}) is cooking - {mine[1]}. {his[0]} ({them}): {his[1]}. Not close.",
                                      f"🎯 Under center, {us} got the hot hand: {mine[0]}, {mine[1]}. {them}'s {his[0]} has {his[1]}.",
                                      f"🎯 {mine[0]} has {mine[1]}. {his[0]} has {his[1]}. That's a quarterback edge for {us}."]))
        elif theirs_better:
            v.knock(5, f"{his[0]} ({them}) has {his[1]} to {mine[0]}'s {mine[1]}")

    # points lately, both sides - for us when we've been the better side on the scoreboard, the knock when they have
    #   (11/17 THE BREAKDOWN SWEEP: hockey / baseball say one decimal - whole goals read "Stars average 4 for / 4 against;
    #    Blue Jackets 3 for / 3 against" - and a margin of zero is never said as "+0 a game": the plain numbers instead)
    _dec = 1 if nhl or lg == "mlb" else 0
    pu, pt = _pts3(_real(s_ours, tid, lg), tid, dec=_dec), _pts3(_real(s_theirs, oid, lg), oid, dec=_dec)   # (11/22: no tune-ups)
    if pu and pt:
        pu, pt = (f"{pu[0]:g}", f"{pu[1]:g}", pu[2], round(pu[0] - pu[1], 1)), (f"{pt[0]:g}", f"{pt[1]:g}", pt[2], round(pt[0] - pt[1], 1))
    if pu and pt and f"{pu[0]} and " not in body:
        net_u, net_t = pu[3], pt[3]
        _net = net_u != 0 and net_t != 0                # (both margins say something)
        if net_u > net_t and net_u <= 0:                # (11/1: the Kansas St card said "outscoring teams 23 to 29 a
            #   game" - 23 scored, 29 allowed is getting OUTSCORED. A side under water lately but less than the other
            #   one says the plain numbers - never "outscoring", never "scoreboard says us")
            #   (11/18, cards_1118: "Flyers score 3.3 and give up 4 a game" / "E Michigan is -7 a game (20 for, 27
            #    against)" put OUR bad numbers in the body. Under water ourselves, the body says only THEIR numbers.)
            add.append(v.say("f_pts", [f"📊 {them} have been outscored {pt[1]} to {pt[0]} a game over their last {pt[2]}.",
                                       f"📊 Last {pt[2]} for {them}: {pt[0]} scored a game, {pt[1]} given up.",
                                       f"📊 {them} are giving up {pt[1]} a game and scoring {pt[0]} over their last {pt[2]}."]))
        elif net_u > net_t and net_t < 0:
            add.append(v.say("f_pts", [f"📊 Last {pu[2]}: {us} are outscoring teams {pu[0]} to {pu[1]} a game; {them} are getting outscored {pt[1]} to {pt[0]}.",
                                       f"📊 {us} put up {pu[0]} a game and give up {pu[1]} over their last {pu[2]}. {them}: {pt[0]} and {pt[1]}. Scoreboard says us.",
                                       f"📊 Scoreboard lately - {us}: {pu[0]} scored, {pu[1]} allowed a game (last {pu[2]}). {them}: {pt[0]} and {pt[1]}. We been better.",
                                       f"📊 Over their last {pu[2]} {us} win by {net_u:g} a game ({pu[0]} for, {pu[1]} against). {them} lose by {-net_t:g} ({pt[0]} for, {pt[1]} against)."]))
        elif net_u > net_t + (0.5 if nhl or lg == "mlb" else 3):   # (both winning lately: a real gap, or it's no line)
            add.append(v.say("f_pts", [f"📊 Last {pu[2]}: {us} are outscoring teams {pu[0]} to {pu[1]} a game; {them} sit at {pt[0]} for, {pt[1]} against.",
                                       f"📊 {us} put up {pu[0]} a game and give up {pu[1]} over their last {pu[2]}. {them}: {pt[0]} and {pt[1]}. Scoreboard says us.",
                                       f"📊 Scoreboard lately - {us}: {pu[0]} scored, {pu[1]} allowed a game (last {pu[2]}). {them}: {pt[0]} and {pt[1]}. We been better.",
                                       f"📊 Over their last {pu[2]} {us} win by {net_u:g} a game ({pu[0]} for, {pu[1]} against); {them} by {net_t:g} ({pt[0]} for, {pt[1]} against)." if _net else
                                       f"📊 Lately {us} score {pu[0]} and allow {pu[1]} a game; {them} score {pt[0]} and allow {pt[1]}."]))
        elif net_t > net_u:
            v.knock(3, f"{them} have outscored teams {pt[0]} to {pt[1]} a game over their last {pt[2]}; {us} sit {pu[0]} for, {pu[1]} against"
                    if net_t > 0 else f"{them} have been the better side on the scoreboard lately - {pt[0]} for, {pt[1]} against "
                    f"a game over their last {pt[2]}; {us} sit {pu[0]} for, {pu[1]} against")
        #   (two sides even on the scoreboard lately say nothing for us: no line - 11/18)

    # the last 5 (ours when we've won more than we lost, theirs when they've lost more) - fresh facts for a thin card
    l5u, l5t = _last_n(s_ours, tid), _last_n(s_theirs, oid)
    if lg in SCHEDULE_FAIR and l5t and any(_tougher(x, oid, tid, e) for x in (s_theirs or [])[-5:]
                                          if _line(x, oid).startswith("L")):
        l5t = None                                   # (11/15: a college slide that includes losses to better teams - no line)
    _up = 2 if STORY else 1                              # (11/19: "3-2 over their last 5" is a record up by one - no line)
    if l5u and l5u[0] - l5u[1] >= _up and f"{l5u[0]}-{l5u[1]}" not in body and not heat.startswith("won"):
        add.append(v.say("f_last5", [f"🗓️ {us} are {l5u[0]}-{l5u[1]} over their last 5.",
                                     f"🗓️ Last 5 for {us}: {l5u[0]}-{l5u[1]}. They been getting it done.",
                                     f"🗓️ {us} won {l5u[0]} of their last 5.",
                                     f"🗓️ {l5u[0]} of the last 5 went {_pos(us)} way."]))
    if l5t and l5t[1] - l5t[0] >= _up and f"{l5t[0]}-{l5t[1]}" not in body and not heat_t.startswith("lost") \
            and not any(str(x).startswith("🗑️") for x in out):
        add.append(v.say("f_last5", [f"🗓️ {them} are {l5t[0]}-{l5t[1]} over their last 5.",
                                     f"🗓️ Last 5 for {them}: {l5t[0]}-{l5t[1]}. They been losing more than winning.",
                                     f"🗓️ {them} dropped {l5t[1]} of their last 5.",
                                     f"🗓️ {l5t[0]}-{l5t[1]} in their last 5 - {them} been sliding."]))

    # their worst recent loss - a beatdown inside their last 5 (the owner's lingo lives here, with the score)
    big = BIG_L.get(lg, 15)
    for x in reversed((s_theirs or [])[-5:]):
        o2, res, sc = _last_parts(x, oid, pro)
        hi, lo = [int(y) for y in sc.split("-")]
        if res == "L" and hi - lo >= big and sc not in body and not any(str(y).startswith("🥊") for y in add) \
                and not (lg in SCHEDULE_FAIR and _tougher(x, oid, tid, e)):   # (11/15: Alabama 109-68 says nothing)
            add.append(v.say("f_theirL", [f"🥊 {_cap(the_them)} got their cheeks clapped {sc} by {o2} inside their last 5.",
                                          f"🥊 {_cap(o2)} put {sc} on {the_them} in one of their last 5.",
                                          f"🥊 {_cap(the_them)} got smacked {sc} by {o2} inside their last 5. That's who we're going against.",
                                          f"🥊 {_cap(o2)} spanked {the_them} {sc} within their last 5 games.",
                                          f"🥊 {sc}. That's what {o2} did to {the_them} inside their last 5.",
                                          f"🥊 {_cap(the_them)} got embarrassed {sc} by {o2} in one of their last 5."]))
            break

    # season scoring: our offense or our defense better than theirs on the year (10+ games pro, 4+ college)
    need = 4 if lg in ("ncaaf",) else 8
    if len(r_ours) >= need and len(r_theirs) >= need:
        pg_u, pg_t = _per_game(r_ours, tid), _per_game(r_theirs, oid)
        fmt = (lambda x: f"{x:.1f}") if nhl or lg == "mlb" else (lambda x: f"{round(x)}")
        if pg_u[1] < pg_t[1] - (0.3 if nhl or lg == "mlb" else 3) and fmt(pg_u[1]) not in body \
                and season_still(r_theirs, oid, 1, lg):      # (🧊 11/27: never "leaking 21" off a defense that stopped leaking)
            add.append(v.say("f_wall", [f"🛡️ {us} {vb(us, 'give', 'gives')} up {fmt(pg_u[1])} {unit} a game this year; {them} {vb(them, 'give', 'gives')} up {fmt(pg_t[1])}. Our D is the better one.",
                                        f"🛡️ On the year {us} {vb(us, 'allow', 'allows')} {fmt(pg_u[1])} a game, {them} {fmt(pg_t[1])}. Our D shows up.",
                                        f"🛡️ {them} {vb(them, 'are', 'is')} leaking {fmt(pg_t[1])} {unit} a game this season. {us} {vb(us, 'hold', 'holds')} teams to {fmt(pg_u[1])}."]))
        if pg_u[0] > pg_t[0] + (0.3 if nhl or lg == "mlb" else 3) and fmt(pg_u[0]) not in body \
                and season_still(r_theirs, oid, 0, lg):      # (11/18: both when
            #   both are true - the offense AND the defense better on the year are two facts for our side)
            add.append(v.say("f_gpg", [f"📊 {us} {vb(us, 'score', 'scores')} {fmt(pg_u[0])} {unit} a game this year; {them} {vb(them, 'manage', 'manages')} {fmt(pg_t[0])}.",
                                       f"📊 Offense: {us} {vb(us, 'are', 'is')} putting up {fmt(pg_u[0])} a game on the season, {them} {fmt(pg_t[0])}.",
                                       f"📊 {us} at {fmt(pg_u[0])} {unit} a game this year. {them} at {fmt(pg_t[0])}. Ours scores more.",
                                       f"📊 {us} put up {fmt(pg_u[0])} a game on the year; {them} can only find {fmt(pg_t[0])}."]))

    # hockey: puck luck, the unlucky record, the 40-shot night
    if nhl:
        pdo = leg.get("pdo")
        parts = leg.get("pdo_parts")
        if pdo is not None and "pdo" not in body and parts and len(parts) >= 6 and parts[3] and parts[5]:
            import sports_form as _sf
            #   (10/29, the owner: "the lingo still sucks" - no "PDO". 11/17, the owner on the Capitals card's combined-number
            #    line: "don't make no sense ... layman's terms" - never a formula, a rate or per-hundred talk: just the real
            #    counts, shots and goals, the way you'd say it, and nothing claimed that the counts don't show)
            sh, sv, gf, sf_, ga, sa = parts[:6]
            sc, st = round(sh * 100), round(sv * 100)     # (11/17, the owner: no rates, no per-hundred talk - the real counts)
            #   (11/18, cards_1118 - the owner: "we can't be saying nothing bad about the Capitals when we're picking them"
            #    / "doesn't make the Nuggets look good": "been snakebit ... only 21 went in, and their goalie's let in 30"
            #    is the bounce-back angle said as a knock on OUR team. Said for us it is the shots - the real count - and
            #    nothing about what went wrong; a goalie who's been getting beat has no good way to say it: no line.)
            if pdo <= _sf.PDO_BAD and sc <= 10 and sf_:
                add.append(v.say("f_pdo", [f"🍀 {us} are getting their looks - {sf_} shots on net their last 10 games. Keep shooting like that and the goals come.",
                                           f"🍀 {sf_} shots on net for {us} their last 10 games. That many pucks at the net, the goals are coming.",
                                           f"🍀 {us} been putting the puck on net - {sf_} shots their last 10. A team shooting that much is due."]))
            elif STORY and pdo <= _sf.PDO_BAD and sf_ and sa and sf_ - sa >= OUTSHOT_MIN and "outshot" not in body:
                #   (11/19, the Flyers card: the engine's reason was the puck luck and the card never said it. In plain
                #    counts, for us: we put more pucks on net than the teams we played.)
                add.append(v.say("f_pdo", [f"🏹 {us} outshot teams {sf_} to {sa} over their last 10 games. They been carrying the play - keep that up and the wins come.",
                                           f"🏹 Shots on net the last 10 games: {sf_} for {us}, {sa} against. That's a team getting the better of it.",
                                           f"🏹 {us} put {sf_} shots on net their last 10 and gave up {sa}. More looks than the other guys, night after night."]))
            elif pdo >= _sf.PDO_GOOD:
                v.knock(1, f"{us} have been getting the bounces: {gf} goals on {sf_} shots their last 10 games, and only {ga} let in")
        pl = leg.get("pyth_luck")
        if pl is not None and pl <= -0.05:
            #   (11/18, cards_1118 - layman's terms: "By goals scored and allowed, Canucks should be about 13 points better
            #    than their record" is a formula's answer nobody can check. The real counts instead - the goals they've
            #    scored and allowed this year - and only when they've scored at least as many as they've given up.)
            _pg = _per_game(r_ours, tid) if r_ours else None
            _gf, _ga = (round(_pg[0] * len(r_ours)), round(_pg[1] * len(r_ours))) if _pg else (0, 0)
            if _gf and _gf >= _ga and f"{_gf}-{_ga}" not in body:
                add.append(v.say("f_pyth", [f"🎲 {us} have scored {_gf} and given up {_ga} this year. That's a better team than the standings show.",
                                            f"🎲 {_gf} goals scored and {_ga} allowed on the year by {us} - they been playing better than their record.",
                                            f"🎲 On the year {us} have scored {_gf} goals and allowed {_ga}. The record ain't caught up to that yet."]
                                 if _gf > _ga else
                                 [f"🎲 {us} have scored {_gf} and given up {_ga} this year - dead even. That's a better team than the standings show."]))
        if leg.get("outshot_opp") and s_theirs:
            b = _said(s_theirs[-1], oid, pro)
            add.append(v.say("f_shots", [f"🏒 {them} gave up 40+ shots in their last game (a {b}) and play again inside 2 days. Gassed.",
                                         f"🏒 {them} got outshot bad last time - 40 or more shots against in that {b} - on a short turnaround."]))
        if leg.get("outshot_me") and s_ours:
            a = _said(s_ours[-1], tid, pro)
            v.knock(2, f"{us} gave up 40+ shots in that {a} and play again inside 2 days")
        ot = leg.get("ot_last")
        if ot and s_ours and "overtime" not in body and "shootout" not in body:
            a = _said(s_ours[-1], tid, pro)
            how = "a shootout" if "so" in str(ot) else "overtime"
            v.knock(1, f"{_pos(us)} last game, a {a}, went to {how}")

    # football: the 4th-down coach tendency
    mo = leg.get("dog_more") or {}
    if lg == "nfl" and mo.get("go4_gap") is not None:
        import sports_go4 as _g4
        gg = mo["go4_gap"]
        if gg >= _g4.GAP_HI:
            g4 = _g4.card_line(us, them)                  # (11/12: the real plays, never a bare "way more" -
            if g4:                                        #  no count on file / too few plays = no line)
                add.append(g4)
        elif gg <= _g4.GAP_LO:
            g4 = _g4.card_line(them, us)
            if g4:                                        # (11/12: the knock says the plays too, or nothing)
                v.knock(1, g4[2:].strip().rstrip("."))

    # head to head this season, when the 🆚 line above didn't print (we lost it, or split)
    if last_vs and not any(str(x).startswith("🆚") for x in out):
        a = _said(last_vs[-1], tid, pro)
        n = len(last_vs)
        w = sum(1 for x in last_vs if _line(x, tid).startswith("W"))
        if _line(last_vs[-1], tid).startswith("W") and STORY:
            pass                                          # (11/19: matchup_facts says the meeting, score and day)
        elif _line(last_vs[-1], tid).startswith("W"):
            add.append(v.say("f_h2h", [f"🆚 {us} got {them} last time, a {a}.",
                                       f"🆚 These two already met - {us} took a {a}.",
                                       f"🆚 Head to head: {us} are {w}-{n - w} against {them} this year, the last one a {a}."]))
        elif _line(last_vs[-1], tid).startswith("L"):
            _sc = _last_parts(last_vs[-1], tid, pro)[2]    # (11/17: it read "Islanders got Devils last time these two
            v.knock(3, f"{them} beat {us} {_sc} the last time these two met")   # met, a 6-0 loss to the Islanders")
        else:
            add.append(v.tag(v.say("f_h2h", [f"🆚 Last meeting: a {a} for {us}.",
                                             f"🆚 These two already played to a {a}."]), "neutral"))

    # football: the bye / short week with the day counts
    if lg in ("nfl", "ncaaf") and ours and theirs and "bye" not in body and "short week" not in body:
        d_us, d_them = _days(start, _t(ours[-1]["start"])), _days(start, _t(theirs[-1]["start"]))
        if d_us >= 13 and d_them <= 8:
            add.append(v.say("f_bye", [f"🛌 {us} are off a bye ({D(d_us)} since their last game); {them} played {D(d_them)} ago.",
                                       f"🛌 {D(d_us)} between games for {us}, {D(d_them)} for {them}. Rest is on our side."]))
        elif d_them <= 5 < d_us:
            add.append(v.say("f_short", [f"⏱️ {them} are on a short week - {D(d_them)} since their last game. {us} had {D(d_us)}.",
                                         f"⏱️ Short week for {them}: {D(d_them)} off against {us}' {D(d_us)}. Tired team, rushed plan."]))

    # 👍 11/18 (cards_1118): the lines that argued for the other side are gone, so a card can run short - it fills with
    # REAL facts for our side the files hold and the card hasn't said: their losing record, and the season's scoring
    # margin when ours is in the black and theirs is in the red. Never filler; nothing here guesses.
    said_now = body + " " + _body(add)
    if r_theirs and len(r_theirs) >= MIN_REC_GAMES:
        rt = _record(r_theirs, oid)
        wt_ = sum(1 for x in r_theirs if _line(x, oid).startswith("W"))
        if 2 * wt_ < len(r_theirs) and rt not in said_now and not unfair_losses(r_theirs, oid, tid, e, lg):
            add.append(v.say("f_theirrec", [f"📋 {them} come in {rt} on the year.",
                                            f"📋 {rt} for {them} this season - more L's than W's.",
                                            f"📋 {them} sit {rt}. Losing record."], fact=True))
    if len(r_ours) >= need and len(r_theirs) >= need and not any(str(x)[:1] in "🛡📊" and "this year" in str(x) or
                                                                 "on the year" in str(x) or "this season" in str(x)
                                                                 for x in add if str(x)[:1] in "🛡📊"):
        pg_u, pg_t = _per_game(r_ours, tid), _per_game(r_theirs, oid)
        mu, mt = pg_u[0] - pg_u[1], pg_t[0] - pg_t[1]
        fm = (lambda x: f"{abs(x):.1f}") if nhl or lg == "mlb" else (lambda x: f"{round(abs(x))}")
        if mu >= (0.3 if nhl or lg == "mlb" else 2) and mt <= -(0.2 if nhl or lg == "mlb" else 1):
            add.append(v.say("f_margin", [f"📊 On the year {us} win by {fm(mu)} a game on average; {them} lose by {fm(mt)}.",
                                          f"📊 {us} outscore teams by {fm(mu)} a game this year. {them} get outscored by {fm(mt)}.",
                                          f"📊 This season: {us} plus {fm(mu)} a game on the scoreboard, {them} minus {fm(mt)}."], fact=True))
    return [x for x in add if x]


BIG_L = {"nhl": 3, "mlb": 5, "nba": 15, "ncaab": 15, "nfl": 14, "ncaaf": 17}   # (10/27) their recent loss worth a
#   "cheeks clapped" line - a real beatdown, never an 11-point hoops game


def risk_line(v, us, them, the_us):
    """(10/27) The ONE honest risk line: the biggest fact that favors the other side, said as the risk - never as a
    reason. Everything else that favored them stays off the card."""
    if not v.knocks:
        return ""
    pr, fact = max(v.knocks, key=lambda k: k[0])
    fact = fact.rstrip(".")
    F = _cap(fact)
    #   (11/4, the owner: "I have not liked the damn lingo" - the old frames ("We weighed it, and X are still the side",
    #    "Priced in. We still riding", "The rest of this card outweighs it", "Don't get it twisted ... We saw it") were
    #    the same corporate shrug on every card. One fact, said like a dude who bets: short, a different frame each card.)
    return v.say("risk", [f"⚠️ Biggest knock on {us}: {fact}.",
                          f"⚠️ {F}.",
                          f"⚠️ Gotta keep it honest - {fact}.",
                          f"⚠️ What could fuck this up: {fact}.",
                          f"⚠️ {F}. We see it. Ain't scared of it.",
                          f"⚠️ What scares us a little: {fact}.",
                          f"⚠️ Not perfect - {fact}. We'll take our chances.",
                          f"⚠️ Heads up: {fact}. Still {us}.",
                          f"⚠️ {F}. That part don't help us, not gonna lie.",
                          f"⚠️ The other side's best argument: {fact}."], fact=True)


def day_game(start):
    """A game that starts before 3 PM PT (6 PM ET) is a day game - never 'tonight' on its card."""
    try:
        return start.astimezone(PT).hour < 15
    except (AttributeError, ValueError, TypeError):
        return False


def not_tonight(x):
    if not isinstance(x, str):
        return x
    x = re.sub(r"\bTonight\b", "Today", x)
    return re.sub(r"\btonight\b", "today", x)


LINE_MOVE = re.compile(r"line'?s? (?:been |keeps? )?mov|\bmoved\b|since the open|\bopened\b|\bthe open\b|shorten|"
                       r"money'?s? (?:coming|on 'em|followed|went|is on|came)|got bet|been bet|getting bet|bet up|"
                       r"\bsteam\b|\bsharps?\b|\bbettors\b|→|price (?:keeps|dropped|fell|rose|came)|hammered early",
                       re.I)
#   (10/23, the owner: "we don't need to talk about the line moving ... it doesn't even really matter" - a one-liner
#    never says the open, the move, the money coming in or the price shortening; every wording is checked here)
LINE_MAX = 150         # a one-liner never runs past today's lines (the owner: never lengthen)


REST_FACT = re.compile(r"last night|back-to-back|yesterday|night off|second night", re.I)   # a real rest fact, no number


def _has_fact(line, names=()):
    """A one-liner rides on a fact we hold (the owner, 10/23): a number in it, a player we named, or the one fact that
    carries no number - who played last night."""
    return bool(re.search(r"\d", line or "")) or any(n and n in (line or "") for n in names) or bool(REST_FACT.search(line or ""))


def _mid(s):
    """A fact sentence in the middle of a line: no period, 'The Pistons' -> 'the Pistons'."""
    s = str(s or "").strip().rstrip(".")
    first = s.split(" ")[0] if s else ""
    if first in ("The", "It's", "Last", "No", "Second", "Fresh", "Everybody", "Bench", "A", "Nobody"):
        s = s[:1].lower() + s[1:]
    return s


def _tl(t, names=()):
    """A tail after a comma: 'We lean X.' -> 'we lean X.' - every opener lowercased but a team / player name up front
    (11/4: "72% of the bets are on N Kentucky, Give me South Dakota." posted with the capital G)."""
    if any(n and t.startswith(n) for n in names):
        return t
    return t[:1].lower() + t[1:]


def _score_gap(way):
    """'... 38-10 ...' -> 28; the margin in a fact wording's score (0 when there's none)."""
    m = re.search(r"\b(\d{1,3})-(\d{1,3})\b", way or "")
    return abs(int(m.group(1)) - int(m.group(2))) if m else 0


LONG_DOG_ODDS = 150    # 11/17 sweep (the dry run's Ball State +350, a 23% read, two straight losses: "Ball State about to beat
LONG_DOG_SAFE = 0.45   # (11/21) a +150 dog read under 45% is a price play too
LONG_DOG_READ = 0.40   # the brakes off 'em"): a moneyline dog at +150 or longer that the engine's own read has winning under
#   40% of the time is a price play - its line never calls a blowout or a sure thing ("beat the brakes off", "cheeks
#   clapped", "easy call", "ain't a question", "all day"). The owner's lingo the way he uses it: "beat the brakes off" is
#   "a mismatch we see coming" - never said of a side we have losing 3 times in 4. sports_card_check.SURE is the last stop.


def long_dog(leg, read=None):
    """A long dog by the price AND the read: a moneyline side +LONG_DOG_ODDS or longer the engine has under LONG_DOG_READ."""
    try:
        if leg.get("market") != "ml" or (leg.get("odds") or 0) <= 0:
            return False
        r = read if read is not None else leg.get("p")
        own = leg.get("own_p")
        if own is None and leg.get("edge_own") is not None and leg.get("dec"):
            own = (leg["edge_own"] + 1) / leg["dec"]
        if (leg.get("odds") or 0) < LONG_DOG_ODDS:        # (11/23 pre-board: "East Carolina fin to get spanked" on Indiana
            return (own is not None and own < LONG_DOG_SAFE) or (r is not None and r < LONG_DOG_SAFE)   # St +130, own 41%)
        #   (11/21 pre-board: "South Alabama fin to get spanked" on Southern Miss +164 - a weighed read of 44%, its own
        #    read 39%: a dog either read has under 45% never calls a beatdown)
        return (r is not None and r < LONG_DOG_READ) or (own is not None and own < LONG_DOG_READ) \
            or (r is not None and r < LONG_DOG_SAFE)
    except (TypeError, AttributeError):
        return False


def _tails(lean, us, them, trash=False, beat=False, long=False):
    """What the one-liner says after the fact (the owner, 10/23: "throw out cuss words and use our lingo ... talk about
    the team itself getting their cheeks clapped or spanked"). lean: no hype, no units talk (the units line has it).
    trash: a fact says the other side's been bad (a skid, a blowout loss) - "trash ass team" is fair. beat: a beatdown
    read (a big record gap, the public heavy on a side we're fading) - "cheeks clapped" and the like are fair.
    long: a long dog (long_dog) - a price play: never a blowout call, never a sure thing."""
    if lean:
        return [f"We lean {us}.", f"{us} the side here.", f"We tilt {us}.", f"{us} if you're playing it.",
                f"Lean {us}, keep it light.", f"Good parlay piece: {us}.", f"We got {us} here.",
                f"{them} don't scare us. {us} lean.", f"{us} by a little on our read.", f"Lean {us}.",
                f"If you gotta pick one, {us}.", f"Slight lean {us}."]
    if long:
        out = [f"We'll take the plus money on {us}.", f"{us} can steal this one.", f"Live dog. We got {us}.",
               f"Give me {us} at that price.", f"We on {us}.", f"We got {us}.", f"Fuck it, {us}.", f"Ride {us}.",
               f"That's a shit spot for {them}.", f"Not touching {them}.", f"{us} got a real shot at that price.",
               f"Plus money on {us}, we'll take our shot."]
        if trash:
            out += [f"{them} a trash ass team right now.", f"{them} straight ass right now.", f"{them} been trash as fuck.",
                    f"{them} are in shambles."]
        return out
    out = [f"Tap in.", f"{us} all day.", f"We on {us}.", f"We riding {us}.", f"Say less.", f"{us} {vb(us, 'are', 'is')} the side.",
           f"{them} ain't ready for this shit.", f"That's a shit spot for {them}.", f"{us} fin to handle that.",
           f"We like {us} a lot.", f"{them} fin to get spanked.", f"{us} about to spank 'em.", f"{them} about to get their ass beat.",
           f"We got {us}.", f"{us} {vb(us, 'get', 'gets')} it done.", f"Ride {us}.", f"{us} {vb(us, 'take', 'takes')} this one.",
           f"We on {us}, no hesitation.", f"{us}, and it ain't a question.", f"Give me {us}.", f"{us}. Done talking.",
           f"Fuck it, {us}.", f"{us}, easy call.", f"Not touching {them}."]
    if beat:
        out += [f"{them} about to get their cheeks clapped.", f"{us} fin to smack that ass.",
                f"{them} fin to get their cheeks clapped.", f"{us} about to beat the brakes off 'em."]
    if trash:
        out += [f"{them} a trash ass team right now.", f"{them} straight ass right now.", f"{them} been trash as fuck.",
                f"They ass. {us} all day.", f"{them} super trash right now. We talking shit, but the tape says it.",
                f"{them} are in shambles."]
    return out


def _spin(key, ways, lean, us, them, em, trash=False, beat=False, names=(), long=False):
    """Every way to say a fact x every tail, in a few shapes (the owner, 10/23: never 'Team fact. Kicker.' every time)."""
    tails = _tails(lean, us, them, trash=trash, beat=beat, long=long)
    opts, tags = [], []
    for i, w in enumerate(ways):
        W = w.strip().rstrip(".") + "."
        W = W[:1].upper() + W[1:]
        for j, t in enumerate(tails):
            shape = (i + j) % 3 if ":" not in t else 0
            if shape == 0:
                opts.append(f"{em} {W} {t}")
            elif shape == 1:
                opts.append(f"{em} {t.rstrip('.')} — {_mid(w)}.")
            else:
                opts.append(f"{em} {W.rstrip('.')}, {_tl(t, (us, them) + tuple(names))}")
            tags.append([_tail_tag(t, us, them)])
    return _ok(opts, names, tags)


def _tail_tag(t, us, them):
    """'We riding Army.' -> 'tail:we riding _' - the kicker, team names blanked, so it shows up once a board."""
    x = t.lower()
    for nm in (us, them):
        if nm:
            x = x.replace(nm.lower(), "_")
    return "tail:" + re.sub(r"[^a-z_' ]", "", x).strip()


def _ok(opts, names=(), tags=None):
    """The one-liner's hard rules (10/23): no line-move talk, a fact in every line, never longer than LINE_MAX.
    -> the options (and, with tags, (options, tags))."""
    tags = tags or [None] * len(opts)
    good = [(o, t) for o, t in zip(opts, tags) if not LINE_MOVE.search(o) and _has_fact(o, names)]
    short = [(o, t) for o, t in good if len(o) <= LINE_MAX] or good[:3]
    if any(t for _, t in short):
        return [o for o, _ in short], [t for _, t in short]
    return [o for o, _ in short]


def knocks_us(line, us):
    """(10/29) Does this line lead with a fact AGAINST our side - our loss, our skid, our losing record? "2-3 for Hawks,
    last time out a 129-117 loss to the Heat" does; "Heat lost 129-117 to the Hawks" (their loss) doesn't - the loss word
    has to come AFTER our name in the sentence, or the line to carry a losing record of ours ("Hawks are 2-5")."""
    t = str(line or "")
    if not t or not us:
        return False
    U = re.escape(us)
    if re.search(rf"\b{U}\b[^.!?]*\b(loss|lost|losses|skid|losing|dropped|fell|swept)\b", t, re.I):
        return True
    for m in re.finditer(rf"(\b\d{{1,2}}-\d{{1,2}}\b)[^.!?]{{0,12}}\bfor {U}\b|\b{U}\b[^.!?]{{0,12}}(\b\d{{1,2}}-\d{{1,2}}\b)", t):
        w, l = (int(x) for x in (m.group(1) or m.group(2)).split("-"))
        if w < l and w + l <= 90:                           # a losing record of ours (never a 129-117 score)
            return True
    return False


def lead_line(lines, v, us, lg=None):
    """(10/29, the Hawks lean: "📋 2-3 for Hawks, last time out a 129-117 loss to the Heat. We lean Hawks." - the line under
    the pick argued for the other side) The fallback line under the pick when no fact matched: the card's best body line
    FOR US - never a line the Voice tagged "neutral" (the record-after-a-loss line, 10/27's direction tagging), never one
    that knocks us (knocks_us), never the risk / bottom lines. None = no line (no pro-us fact = no line)."""
    body = [x for x in (lines or [])[:-1] if x and not str(x).startswith(("⚠️", "✅", "🟡", "🔒"))]
    def _meh(x):                                          # 🗓️ 11/19 (the Flyers card: "3-2 over their last 5" led):
        m_ = re.search(r"\b(\d)-(\d)\b", str(x))       # a record up by one is no reason - it never leads the card
        if str(x).startswith("📅") and lg in REAL_LOSS and m_ is None:
            return False
        if str(x).startswith("📅") and lg in REAL_LOSS:   # (a close last game - 4-3 - leads only after everything else)
            return 0 < _score_gap(str(x)) < REAL_LOSS[lg]
        return str(x).startswith("🗓️") and (not m_ or int(m_.group(1)) - int(m_.group(2)) < 2)
    ok = lambda x: (v.dirs.get(x, "us") if v is not None else "us") == "us" and not knocks_us(x, us)   # noqa: E731
    if STORY:
        # 📖 11/19 (the owner: "this guy's in gold ... Don't tell us shit"): the strongest MATCHUP fact leads (lead_rank) -
        # never the price, never a close last result or a record up by one, and a scorer's points only when the card
        # holds no team-level fact at all
        team = sorted((x for x in body if not str(x).startswith(("💯", "💵")) and not _meh(x) and ok(x)), key=lead_rank)
        if team:
            return team[0]
        return next((x for x in body if str(x).startswith("💯") and ok(x)), None)
    body = [x for x in body if not str(x).startswith("💵")] + [x for x in body if str(x).startswith("💵")]
    for fill in (False, True, None):
        for x in body:
            if (fill is None) != _meh(x):
                continue
            if fill is not None and (str(x).startswith(("💯", "💵")) or x in getattr(v, "fill", ())) != fill:
                continue
            if ok(x):
                return x
    return None


def why_line(leg, v, g, us, them, the_us, the_them, rec_u=None, n_hot=0, rec_t=None, n_cold=0, gap=None, form=None,
             key_them=(), key_us=(), whyf=None, fact="", nba_f=None, facts=()):
    """The line right under the pick (the owner, 10/23: "solid one-liner breakdowns in our lingo ... throw out cuss
    words"). It opens with a FACT the engine holds - a score, a streak, who's out by name, last season's record, the
    public split, a home record, the rest days, the arm or the goalie - said raw, in his voice, trash-talking the other
    side when a fact about THEM backs it. Never the line moving (LINE_MOVE), never a line without a number or a name
    (_has_fact), never longer than today's (LINE_MAX), never the same wording twice on a board or from the days before
    (the Voice + sports_breakdown.memory). A lean keeps its no-units tone (no hype tails). No fact = no line."""
    form = form or {}
    lg = leg["league"]
    lean = leg.get("is_lean")
    if lean is None:                                      # (an old pick / the question box: the tier stands in)
        lean = leg.get("tier") in ("lean", "strong")
    if lean and _no_leans():                              # (11/21 pre-board: "Lean LSU N Orleans" on a 1u play - leans are
        lean = False                                      #  gone, the owner 11/16; no card says "lean" again)
    if whyf is None:                                      # called on its own (an old pick, the question box): the fact
        pub = None                                        # map from what it was handed
        try:
            pub = public_split(leg)
        except Exception:                                 # noqa: BLE001
            pub = None
        whyf = why_map(lg, us, them, the_us, the_them, lg in ("nfl", "nba", "mlb", "nhl"), rec_u=rec_u, rec_t=rec_t,
                       n_hot=n_hot, n_cold=n_cold, key_them=key_them, key_us=key_us, form=form,
                       sp_us=g.get("sp_" + leg["side"]) if lg == "mlb" else None, g=g, nba_f=nba_f, pub=pub)
    if not facts and not fact:                            # (no fact handed in: the map's best one)
        tf = top_facts(whyf, [r for r in leg.get("reasons") or []])
        facts = tf[0] if tf else ()
    rsn = [r for r in leg.get("reasons") or [] if not str(r).startswith(("proven", "trend:", "opponent drama"))
           and r != "sharp money moving this way"]       # (10/23: the move is a weight, never the one-liner)
    sp_us, sp_them = g.get("sp_" + leg["side"]), g.get("sp_" + ("away" if leg["side"] == "home" else "home"))
    trip = next((c for c in leg.get("ctx") or [] if c.get("k") == "trip" and c.get("who") == "them" and (c.get("mi") or 0) >= 1000), None)
    _hot = form.get((True, "hot"))
    names = tuple(x for x in ([key_them[0][0]] if key_them else []) + [sp_us or "", sp_them or ""]
                  + ([_hot[0]] if _hot else []) if x)
    _ng = lambda r_: sum(int(x) for x in str(r_).split("-")[:2])
    _net = lambda r_: (lambda a: a[0] - a[1])([int(x) for x in str(r_).split("-")[:2]])
    try:
        import sports as _sp
        own = _sp.read_of(leg) or leg["p"]
    except Exception:                                     # noqa: BLE001
        own = leg.get("p") or 0.5
    need = 1 / leg["dec"] if leg.get("dec") else None
    _long = long_dog(leg, own)                            # (11/17 sweep: a long dog's line never calls a blowout)
    S = lambda key, ways, em, **kw: (key, _spin(key, ways, lean, us, them, em, names=names, long=_long, **kw))
    pools = []
    # ---- the other side's hole first: their key man out, a back-to-back, a heavy public we're fading ----
    #   🚑 11/19 (the owner on the Ducks 3u card, MacKinnon AND Makar out for the Avalanche while the line under the pick
    #   said only "the Avalanche played last night": "The breakdown should say the Avalanche has their best two players
    #   out in the main line" / "Get the breakdowns right permanently"): the NAMED absence the engine's own read counts
    #   (sports.absence_reasons - "opponent missing key players: A, B (their read -7)") is the biggest fact a card holds
    #   and leads the line under the pick, with who they are ("their top two scorers") and the back-to-back folded in.
    named = named_out_ways(leg, g, them, the_them, "opponent on a back-to-back" in whyf) if not key_us else None
    if named:
        names = names + tuple(named[1])
        pools.append(S("w_hurt_named", named[0], "🚑", beat=True))
    if "opponent missing key players" in whyf and (not key_us):
        pools.append(S("w_hurt", whyf["opponent missing key players"], "🚑", beat=True))
    #   🧱 11/19 (the owner on the Flyers card): the other goalie's hot run the books overpay for is a WEIGHT, never a
    #   line - "the goalie is great but we like Flyers" doesn't make sense to anybody reading it, and it praises them.
    if "opponent on a back-to-back" in whyf:
        pools.append(S("w_rest", whyf["opponent on a back-to-back"], "😮‍💨"))
    if PUBLIC_CARD and "public fade" in whyf:             # (the owner, 10/23: "Air Force - they're about to get their
        pools.append(S("w_public", whyf["public fade"], "📊", beat=True))   # cheeks clapped. Shit like that")
    # ---- the engine's own reasons, each with the fact behind it ----
    for r in rsn:
        if r == "the stronger team":
            if rec_u and rec_t and _net(rec_u) - _net(rec_t) >= REC_GAP and min(_ng(rec_u), _ng(rec_t)) >= MIN_REC_GAMES:
                pools.append(("w_better", _ok([               # (10/23, the owner: 4-2 vs 4-3 is never "the better team" -
                    f"💪 {us} are {rec_u}, {them} are {rec_t}. Better team, better price.",   # REC_GAP)
                    f"💪 {rec_u} vs {rec_t}. {us} been the better squad this year.",
                    f"💪 {us} walk in {rec_u}; {them} walk in {rec_t}. Levels to this shit.",
                    f"💪 {us} {rec_u}, {them} {rec_t}. " + (f"We lean {us}." if lean else f"{them} about to get their ass beat."),
                    f"💪 {us} sit {rec_u} to {_pos(them)} {rec_t}. Records don't lie.",
                    f"💪 {us} ({rec_u}) over {them} ({rec_t}) on the record — the better team..",
                    f"💪 {them} are {rec_t}. {us} are {rec_u}. " + (f"{us} the side here." if lean else f"{them} fin to get spanked."),
                    f"💪 A {rec_u} team against a {rec_t} team. " + (f"We tilt {us}." if lean else f"{us} all day.")])))
            elif rec_u and rec_t and min(_ng(rec_u), _ng(rec_t)) >= MIN_REC_GAMES and lg != "nba":
                dm = leg.get("dog_more") or {}                # (10/23, the owner on Army 4-2 vs Tulsa 4-3 "we know which
                ws, mg = dm.get("win_streak") or 0, dm.get("last_margin") or 0   # side we want": a close record is
                if ws >= 2 and mg >= 14:                      #  never "the better team" - say what separates them)
                    pools.append(("w_close_rec", _ok([
                        f"🧠 The records look even ({us} {rec_u}, {them} {rec_t}), but {us} have won {ws} straight — the last one by {int(mg)}.",
                        f"🧠 {rec_u} vs {rec_t} on paper. {us} have won {ws} in a row, the last by {int(mg)} — they're rolling.",
                        f"🧠 Don't let {rec_u} vs {rec_t} fool you — {us} have won {ws} straight, the last by {int(mg)}.",
                        f"🧠 {us} won their last {ws}, the last one by {int(mg)}. {them} at {rec_t} ain't seen that shit yet.",
                        f"🧠 {ws} straight for {us}, the last by {int(mg)} points — {rec_u} and rolling into a {rec_t} {them} team."])))
                elif lean and card_fair(leg, _read(leg), beat=True):   # (11/11: never the raw read 15+ points off the price)
                    fa = card_fair(leg, _read(leg), beat=True)   # (a lean's units line has no number; a unit play's does -
                    pools.append(("w_close_rec", _ok([        #  never said twice on one card)
                        f"🧠 The records look even ({us} {rec_u}, {them} {rec_t}); our ratings make {us} {fa} — the book's at {_am(leg['odds'])}.",
                        f"🧠 {rec_u} vs {rec_t} on paper, but we price {us} at {fa} and the book hangs {_am(leg['odds'])}."])))
            elif nba_f and nba_f.get("us") and nba_f.get("them") and nba_f["us"][1] > nba_f["them"][1]:
                (ru, du), (rt, dt) = nba_f["us"], nba_f["them"]     # (10/21: opening week - last season's facts)
                import sports_nba_roster as _nr
                big = _net(ru) - _net(rt) >= 10
                pools.append(("w_better_ls", _ok([         # (10/23: the 🏀 body line carries the point gaps - the
                    f"💪 {us} were {ru} last year, {them} {rt}. " + (f"We lean {us}." if lean else f"{us} all day."),   # one-liner
                    f"💪 {ru} to {rt} last season. {us} the better squad walking in.",           # stays short)
                    f"💪 {them} went {rt} last year. {us} went {ru}. " + (f"{us} the side here." if lean else
                                                                      (f"{them} fin to get spanked." if big else "Tap in.")),
                    f"💪 A {ru} team last year against a {rt} one. " + (f"We tilt {us}." if lean else f"Levels to this shit."),
                    f"💪 Last season: {us} {ru}, {them} {rt}. " + (f"{us} if you're playing it." if lean else f"Say less."),
                    f"💪 {us} won {ru.split('-')[0]} games last year to {_pos(them)} {rt.split('-')[0]}. " + (f"Lean {us}." if lean else f"Tap in.")])))
        elif r == "hotter recent form" and n_hot >= 2 and "hotter recent form" in whyf:
            pools.append(("w_hot", _ok([
                f"🔥 {us} are rolling — {n_hot} straight W's{f', {rec_u} on the year' if rec_u else ''}. Ride the heater." if n_hot >= HOT_MIN else   # (11/11: a heater is 3+)
                f"🔥 {n_hot} straight W's for {us}{f', {rec_u} on the year' if rec_u else ''}. " + (f"Lean {us}." if lean else f"Give me {us}."),
                f"🔥 {us} are cooking right now ({n_hot} straight) and {them} ain't matching that energy.",
                f"🔥 Hot hand goes to {us} — {n_hot} straight. " + ("We don't bet against a heater." if n_hot >= HOT_MIN else f"{us} been winning."),
                f"🔥 {n_hot} straight for {us}. " + (f"We lean {us}." if lean else f"{them} fin to get spanked."),
                f"🔥 {us} haven't lost in {n_hot}{f' — {_an(n_hot)} {n_hot}-game heater' if n_hot >= HOT_MIN else ''}{f' ({rec_u})' if rec_u else ''}. " + (f"{us} the side here." if lean else f"Ride {us}."),
                f"🔥 Nobody's beaten {us} in {n_hot} games, {n_hot} straight W's. " + (f"We tilt {us}." if lean else f"{them} ain't ready for this shit.")])))
        elif r == "better starting pitcher" and sp_us and "better starting pitcher" in whyf:
            pools.append(S("w_arm", whyf["better starting pitcher"], "⚾"))
        elif r == "hotter goalie" and "hotter goalie" in whyf:
            hot = form.get((True, "hot"))
            if hot and len(hot) > 2 and hot[2] == "projected":   # (11/6: the projected starter - never stated as tonight's man)
                pools.append(("w_goalie", _ok([
                    f"🧱 {hot[0]}, projected to start for {us} (not confirmed yet), has been a brick wall — {hot[1]}.",
                    f"🧱 {hot[0]} ({_pos(us)} projected starter, not confirmed) has been a brick wall — {hot[1]}."], names)))
            elif hot and len(hot) > 2 and hot[2] == "likely":    # (11/16: the page's 'likely' is not 'confirmed')
                pools.append(("w_goalie", _ok([
                    f"🧱 {hot[0]}, expected in net for {us} (not confirmed yet), has been a brick wall — {hot[1]}.",
                    f"🧱 {hot[0]} ({_pos(us)} expected starter, not confirmed) has been a brick wall — {hot[1]}."], names)))
            elif hot and len(hot) > 2 and not hot[2]:         # (10/16: the starter isn't confirmed - he was in net LAST time)
                pools.append(("w_goalie", _ok([
                    f"🧱 {hot[0]}, in net last time out for {us}, has been a brick wall — {hot[1]}.",
                    f"🧱 {hot[0]} ({_pos(us)} last starter in net) has been a brick wall — {hot[1]}."], names)))
            else:
                pools.append(S("w_goalie", whyf["hotter goalie"], "🧱"))
        elif r == "better QB play lately" and "better QB play lately" in whyf:
            pools.append(S("w_qb", whyf["better QB play lately"], "🎯"))
        elif r == "better rested":
            if r not in whyf:
                continue                                  # (10/21: the rest edge says the days, or nothing)
            pools.append(S("w_rest", whyf[r], "🛌"))
        elif r == "revenge game" and r in whyf:
            pools.append(S("w_revenge", whyf[r], "😤"))
        elif r == "the engine's scoring read":
            continue                                      # (no number to show = no line)
        elif r in whyf and r not in ("opponent missing key players", "opponent on a back-to-back", "the stronger team"):
            pools.append(S("w_" + r.split()[0], whyf[r], "🧠"))
    # ---- facts about THEM (the owner, 10/23: "talk about the team itself getting their cheeks clapped or spanked") ----
    if "their last loss" in whyf:
        ways = whyf["their last loss"]
        blow = any(_score_gap(w) >= 14 for w in ways)
        pools.append(S("w_their_loss", ways, "🥊", trash=blow, beat=blow))
    if "cold opponent" in whyf:
        pools.append(S("w_cold", whyf["cold opponent"], "🧊", trash=True))
    if "their road record" in whyf:
        pools.append(S("w_their_road", whyf["their road record"], "🧳", trash=True))
    # ---- standalone facts about us ----
    for key, em in (("last game", "📅"), ("rolling off a blowout win", "🚀"), ("home record", "🏟️"), ("deeper bench", "🏀"),
                    ("public ride", "📊")):
        if key.startswith("public") and not PUBLIC_CARD:
            continue                                         # (11/12: no splits on the card)
        if key == "last game" and lg in REAL_LOSS and (g.get("start") or "")[:10] >= CLOSE_WIN_FROM and whyf.get(key) \
                and _score_gap(whyf[key][0]) < REAL_LOSS[lg]:
            continue                                         # (11/19, the Flyers card: a 4-3 win is a coin flip - never
            #                                                  the line under the pick; it stays in the body)
        if key in whyf and not any(k == "w_" + key.split()[0] for k, _ in pools):
            pools.append(S("w_" + key.split()[0], whyf[key], em, beat=(key == "rolling off a blowout win")))
    # ---- the top fact + the read, the way it used to close (a fact first, always) ----
    Fs = [f.strip() for f in (facts or ([fact] if fact else [])) if f and f.strip()]
    if lg in REAL_LOSS and (g.get("start") or "")[:10] >= CLOSE_WIN_FROM:   # (11/19: a 4-3 game never leads the line)
        Fs = [f for f in Fs if not 0 < _score_gap(f) < REAL_LOSS[lg]]
    if (g.get("start") or "")[:10] >= CLOSE_WIN_FROM:     # (11/20, the Niagara card: "Niagara went 8-22 last season,
        Fs = [f for f in Fs if not even_records(f)]       #  Delaware St 8-23" - two records about the same say nothing)
    if not Fs:
        nums = ("w_num", [])
    elif round(100 * own) > 55:
        nums = ("w_num", _ok(_fx(Fs, *((lambda F: f"🔒 {F} Lock it in.", lambda F: f"🔒 {F} {us} all day.",
                                        lambda F: f"🔒 {F} {them} fin to get spanked.") if leg.get("tier") == "lock" else
                                       (lambda F: f"🧠 {F} We lean {us}.", lambda F: f"🧠 {F} {us} the side here.") if lean else
                                       (lambda F: f"🧠 {F} That's why we got {us}.", lambda F: f"🧠 {F} We riding {us}.",
                                        lambda F: f"🧠 {F} {us} is the side.", lambda F: f"🧠 {F} {us} all day.",
                                        lambda F: f"🧠 {F} {them} ain't ready for this shit."))), names))
    elif leg.get("near_price"):
        nums = ("w_num", _ok(_fx(Fs, lambda F: f"🔒 {F} We trust {us} to win this one - priced about right, so it's a small bet.",
                                 lambda F: f"🔒 {F} {us} to win at a fair price. A light bet, not a big one."), names))
    elif need and own <= need and COIN_FLIP[0] <= own < 0.56 and leg.get("market") == "ml" and _sb_mod.coin_side(leg, own):   # (10/1, the owner: the Kraken at -108 - a near coin flip
        nums = ("w_num", _ok(_fx(Fs, lambda F: f"🧠 {F} Still, we've got {us} close to a coin flip - a hair better, not enough for units.",
                                 lambda F: f"🧠 {F} Even so it's close to 50-50 on our read, {us} by a hair.",
                                 lambda F: f"🧠 {F} Close to 50-50 for us, {us} by a nose."), names))   # is the reason)
    elif need and own <= need and not lean:               # (11/13, the owner on the Predators ½u floor play: "we like
        nums = ("w_num", _ok(_fx(Fs, lambda F: f"🧠 {F} {us} the side tonight.",   # (11/20: the old "fair price" tail ran our   Predators
                                 lambda F: f"🧠 {F} We on {us}."), names))         #  own play down - the owner: no bad shit)  just not at
        #   this price makes zero sense" - a play WITH units never says the price is wrong for units)
    elif need and own <= need:
        nums = ("w_num", _ok(_fx(Fs, lambda F: f"🧠 {F} {us} is the side, but the price is too steep for units.",
                                 lambda F: f"🧠 {F} We like {us} - just not at this price."), names))
    elif need and lean:                                   # (a unit play's units line already shows our number)
        _fa = None if NO_OUR_NUMBER else card_fair(leg, own)
        nums = ("w_num", _ok(_fx(Fs, *((lambda F: f"🧠 {F} We make {us} {_fa}.", lambda F: f"🧠 {F} Our number on {us}: {_fa}.")
                                       if _fa else (lambda F: f"🧠 {F} We lean {us}.",))), names))
    elif need:
        nums = ("w_num", _ok(_fx(Fs, lambda F: f"🧠 {F} That's value on {us} — tap in.", lambda F: f"🧠 {F} {us} all day.",
                                 lambda F: f"🧠 {F} Give me {us}."), names))
    else:
        nums = ("w_num", [])
    line = ""
    _un = lambda x: (list(x[0]), list(x[1])) if isinstance(x, tuple) else (list(x), [None] * len(x))
    leg["why_key"] = ""                                   # 🗣️ 11/22: which pool said the line (lead_upgrade reads it)
    for key, opts in pools + [nums]:                      # the top fact first; every wording used on the board? the next
        o, tg = _un(opts)
        line = v.say(key, o, tags=tg)
        if line:
            leg["why_key"] = key
            break
    if not line:                                          # any fresh wording left - else no line
        allo, allt = [], []
        for _, opts in pools + [nums]:
            o, tg = _un(opts)
            allo += o
            allt += tg
        line = v.say("w_any", allo, tags=allt)
        leg["why_key"] = "w_any" if line else ""
    if line and (LINE_MOVE.search(line) or not _has_fact(line, names)):
        line = ""                                         # (belt and braces: the rules hold whatever the pool said)
        leg["why_key"] = ""
    kick = []
    if trip and rsn and "opponent's body clock is off" not in rsn:
        kick.append(("k_trip", [f" Plus {them} flew {_mi(trip['mi'])} miles for this.",
                                f" And {them} are coming off a {_mi(trip['mi'])}-mile trip."]))
    for key, opts in kick[:1]:
        k = v.say(key, opts)
        if line and k and len(line) + len(k) <= LINE_MAX:
            line += k
    return line

WHY = {   # the pick's reasons, said as a quick "because"
    "the stronger team": "they're the better team",
    "hotter recent form": "they're the hotter team",
    "better rested": "they got extra days of rest",
    "opponent on a back-to-back": "{them} are on tired legs",
    "opponent missing key players": "{them} are banged up",
    "revenge game": "they owe these guys one",
    "altitude edge": "{them} gonna be sucking wind up there",
    "opponent's body clock is off": "{them} are playing on jet lag",
    "cold-weather edge": "{them} aren't built for the cold",
    "nasty weather helps us": "sloppy weather keeps it close",
    "rolling off a blowout win": "they're rolling off a blowout",
    "letdown spot for the opponent": "{them} are due for a letdown",
    "coming off a bye": "they're fresh off a bye",
    "opponent on a short week": "{them} are on a short week",
    "better starting pitcher": "we've got the better arm on the mound",
    "better QB play lately": "our QB's been playing better",
    "hotter goalie": "our goalie's been hotter",
}


WHY_EMOJI = {   # the line under the pick opens with this -> that reason is said (the body picks another "because")
    "the stronger team": "💪", "hotter recent form": "🔥", "opponent missing key players": "🚑",
    "better starting pitcher": "⚾", "hotter goalie": "🧱", "better QB play lately": "🎯",
    "opponent on a back-to-back": "😮‍💨", "better rested": "🛌", "revenge game": "😤", "sharp money moving this way": "💸",
    "public fade": "📊", "public ride": "📊", "cold opponent": "🧊", "their last loss": "🥊", "home record": "🏟️",
    "their road record": "🧳", "last game": "📅", "rolling off a blowout win": "🚀"}
SAME_STORY = (("💪", "💪"), ("💪", "📋"), ("🔥", "🔥"), ("😤", "😤"), ("🛌", "🛌"), ("😮‍💨", "😴"), ("🚀", "🚀"),
              ("📊", "📊"), ("🧊", "🧊"), ("🧊", "🗑️"), ("🥊", "📅"), ("🏟️", "🏟️"), ("🧳", "🧳"), ("📅", "📅"), ("🚀", "📅"))
#   (the why line's emoji, the body line it already says) - the body line comes out

FACT_ORDER = ("opponent missing key players", "opponent on a back-to-back", "public fade", "the stronger team",
              "hotter recent form", "cold opponent", "their last loss", "last game", "rolling off a blowout win",
              "better rested", "revenge game", "home record", "their road record",
              "letdown spot for the opponent", "better starting pitcher", "hotter goalie", "better QB play lately",
              "deeper bench", "public ride", "coming off a bye", "opponent on a short week", "cold-weather edge",
              "nasty weather helps us", "opponent's body clock is off", "altitude edge")
BENCH_GAP = 3.0        # hoops: our bench this much better than theirs (per 48, last season) is a fact worth a line
REAL_LOSS = {"nhl": 3, "mlb": 4, "nba": 10, "ncaab": 10, "nfl": 10, "ncaaf": 14}   # their last L backs our side only by
#   this much (10/27: a 2-1 / 5-4 loss is a coin flip, never a reason - the one-liner said "Canadiens beat the Jets 2-1")
BLOWOUT = 14           # a win / loss by this many is a blowout ("beat the brakes off", "cheeks clapped") - never by 3
PUBLIC_CARD = False    # the owner, 11/12: "the breakdowns are terrible ... one says 97% the action is on whatever - that's
#                        absolutely retarded and doesn't tell you anything." The betting splits pick no winners (10/7 study
#                        dead; 11/11 spreads part 2: following the public loses 4-7%, fading it loses 2-4%, every league)
#                        and the engine's read never uses them - so no splits line, no "public fade" one-liner, no "public
#                        ride" fact on any card. The splits stay in the data (the tracker, the sharp-money weight).
PUBLIC_HEAVY = 70      # the public is "all over" a side at 70%+ of the bets (sports_public.HEAVY) - under that, no line
SITE_GOOD = 0.75       # a home / road record worth a line: 3+ games, 75%+ won (ours) ...
SITE_BAD = 0.34        # ... or 34% or less (theirs) - 2-2 says nothing


def why_map(lg, us, them, the_us, the_them, pro, rec_u=None, rec_t=None, n_hot=0, their_hot=0, n_cold=0, key_them=(),
            key_us=(), b2b=False, gap_d=0, last_vs=(), tid=None, oid=None, s_ours=(), s_theirs=(), nba_f=None,
            form=None, sp_us=None, g=None, bench=None, pub=None, site=None, their_site=None):
    """Every "because" the card can say, keyed by the engine's reason name, each one a FACT we hold (10/21, the owner:
    "they're the better team" / "they're banged up" / a bare verdict say nothing). A reason with no
    fact behind it isn't in the map - the weight still counts, the words don't guess. Two extra keys the one-liner can
    fall back on: "cold opponent" (their losing streak) and "last game" (our last score)."""
    form = form or {}
    m = {}                       # reason -> [ways to say the fact] (several, so two cards never share a 4-word run)
    U, T = the_us, the_them
    if key_them and not key_us:
        nm, pos = key_them[0][0], key_them[0][1]
        if lg == "mlb":
            m["opponent missing key players"] = [f"{T} are without {nm}, one of their best bats",
                                                 f"no {nm} in {_pos(T)} lineup tonight - one of their best bats",
                                                 f"{nm}, one of {_pos(T)} best bats, is out"]
        else:
            p = _posname(pos, lg)
            m["opponent missing key players"] = [f"{T} are without their starting {p} {nm}",
                                                 f"{nm}, {_pos(T)} starting {p}, is out",
                                                 f"no {nm} for {T} - that's their starting {p}",
                                                 f"{_pos(T)} starting {p} {nm} isn't playing"]
    if b2b:
        m["opponent on a back-to-back"] = [f"{T} played last night and {U} didn't",
                                           f"{T} are on a back-to-back; {U} had the night off",
                                           f"second night in a row for {T}, a night off for {U}",
                                           f"{T} played yesterday, {U} rested"]
    _w = lambda r_: (lambda a: a[0] / max(1, a[0] + a[1]))([int(x) for x in str(r_).split("-")[:2]])
    _n = lambda r_: sum(int(x) for x in str(r_).split("-")[:2])
    if rec_u and rec_t and _w(rec_u) > _w(rec_t) and min(_n(rec_u), _n(rec_t)) >= MIN_REC_GAMES:
        m["the stronger team"] = [f"{U} are {rec_u}, {T} {rec_t}", f"{U} {rec_u} on the year, {T} {rec_t}",
                                  f"it's {rec_u} ({U}) against {rec_t} ({T})", f"{U} sit {rec_u}; {T} sit {rec_t}"]
    elif nba_f and nba_f.get("us") and nba_f.get("them") and nba_f["us"][1] > nba_f["them"][1]:
        ru, rt = nba_f["us"][0], nba_f["them"][0]
        m["the stronger team"] = [f"{U} went {ru} last season, {T} {rt}", f"last year it was {ru} for {U}, {rt} for {T}",
                                  f"{U} finished {ru} a year ago; {T} {rt}", f"{ru} ({U}) against {rt} ({T}) last season"]
    if n_hot >= 2 and their_hot < n_hot:
        m["hotter recent form"] = [f"{U} have won {n_hot} straight", f"{n_hot} straight wins for {U}",
                                   f"{U} are on {_an(n_hot)} {n_hot}-game winning streak", f"{U} haven't lost in {n_hot}"]
    if n_cold >= 2:
        m["cold opponent"] = [f"{T} have lost {n_cold} straight", f"{n_cold} straight losses for {T}",
                              f"{T} are on a {n_cold}-game skid", f"{T} haven't won in {n_cold}"]
    if s_ours and _line(s_ours[-1], tid).startswith("W") and (not s_theirs or _line(s_theirs[-1], oid).startswith("L")) \
            and not non_d1(lg, _opp_id(s_ours[-1], tid)):   # (11/22: "William & Mary just beat Averett 85-39" led a card -
        o2, _, sc = _last_parts(s_ours[-1], tid, pro)      #  a non-D1 tune-up is never the reason under a pick)
        m["last game"] = [f"{U} are fresh off a {sc} win over {o2}", f"{U} just beat {o2} {sc}",
                          f"last time out {U} took {o2} {sc}", f"{U} handled {o2} {sc} last time out"]
    if gap_d >= 2 and not b2b_only(lg):                   # (11/19 sweep: REST TALK ONLY ON A BACK-TO-BACK - the map still
        #   handed the one-liner "Tulane got 3 more days to rest than Louisiana Tech did" in college hoops / hockey)
        m["better rested"] = [f"{U} had {gap_d} more days off than {T}", f"{gap_d} extra days of rest for {U}",
                              f"{U} got {gap_d} more days to rest than {T} did", f"{T} had {gap_d} fewer days off than {U}"]
    if last_vs and _line(last_vs[-1], tid).startswith("L"):
        o2, _, sc = _last_parts(last_vs[-1], tid, pro)
        #   (11/18, cards_1118: the revenge spot under a pick read "{U} took a 27-20 loss ..." / "{U} dropped the last
        #    one" - a knock on our own side as the one-liner. Said as what THEY did and what we owe them.)
        m["revenge game"] = [f"{U} owe {T} one - {T} got {U} {sc} the last time these two met",
                             f"payback spot: {T} got {U} {sc} the last time these two met",
                             f"{T} got {U} {sc} the last time these two met, and {U} been waiting on this one"]
    if s_ours and _line(s_ours[-1], tid).startswith("W") and _score_gap(_last_parts(s_ours[-1], tid, pro)[2]) >= BLOWOUT \
            and not non_d1(lg, _opp_id(s_ours[-1], tid)):   # (11/4: a non-D1 tune-up - Mount Marty 95-57 - is no blowout)
        o2, _, sc = _last_parts(s_ours[-1], tid, pro)      # (10/23: "blew out" only when the score says so - 14+)
        m["rolling off a blowout win"] = [f"{U} just rolled to a {sc} win over {o2}", f"{U} blew out {o2} {sc} last time out",
                                          f"{sc} over {o2} last time out for {U}", f"{U} beat the brakes off {o2}, {sc}",
                                          f"{U} smacked {o2} {sc} last time out", f"{o2} got their cheeks clapped {sc} by {U} last time out"]
    # facts about THEM (the owner, 10/23: "talk about the team itself getting their cheeks clapped or spanked")
    if s_theirs and _line(s_theirs[-1], oid).startswith("L") \
            and _score_gap(_last_parts(s_theirs[-1], oid, pro)[2]) >= REAL_LOSS.get(lg, BLOWOUT):
        o2, _, sc = _last_parts(s_theirs[-1], oid, pro)    # (10/27, the owner: "The Canadiens beat the Jets 2-1 last
        pts = sc.split("-")[0]                             #  time out. We lean Panthers - what the fuck is that?" - a
        m["their last loss"] = [f"{T} just got beat {sc} by {o2}",   # one-goal L says nothing about this game: only a
                                f"{T} are coming off a {sc} beating from {o2}",   # real beating, said about THEM, never
                                f"last time out {T} took a {sc} L to {o2}",   # with a third team as the subject)
                                f"{T} got handled {sc} by {o2} last time out"]
    if PUBLIC_CARD and pub and pub[0] is not None:        # the real public split (never a guess from the price; 11/12 off)
        t, mo = pub
        n = 100 - t
        if t <= 100 - PUBLIC_HEAVY:                       # (a dozen wordings, no 4-word run shared between any two - a
            m["public fade"] = [f"{n}% of the bets are on {T}",    # board of fades never reads the same twice)
                                f"the public's got {n}% of the tickets on {T}",
                                f"{n}% of tickets are on {T}",
                                f"{n}% of the crowd is on {T}",
                                f"{T} {vb(them, 'are', 'is')} holding {n}% of the action",
                                f"the public side is {T}, {n}% of all bets",
                                f"only {t}% of the public is on {U}",
                                f"{T} {vb(them, 'are', 'is')} the public's team tonight, {n}% of bets",
                                f"the public is all over {T}, {n}% of bets"] + \
                               ([f"everybody and they mama on {T} with {100 - mo}% of the money",
                                 f"{100 - mo}% of the cash is on {T}"] if mo is not None else [])
        #   (10/23: the public WITH us is never the line under the pick - "71% of the cash is on the Avalanche with
        #    us" said nothing; only a fade of the public is a fact worth leading with)
    if site and site[1] >= MIN_REC_GAMES and site[2] / site[1] >= SITE_GOOD:   # ('home'/'road', games, wins, '3-0')
        where, rec = site[0], site[3]
        at = "at home" if where == "home" else "on the road"
        m["home record"] = [f"{U} are {rec} {at} this year", f"{rec} {at} for {U} this season",
                            f"{U} haven't lost {at} this year ({rec})" if site[2] == site[1] else f"{U} are {rec} {at}",
                            f"{U} {at} this year: {rec}"]
    if their_site and their_site[1] >= MIN_REC_GAMES and their_site[2] / their_site[1] <= SITE_BAD:
        where, rec = their_site[0], their_site[3]
        at = "at home" if where == "home" else "on the road"
        m["their road record"] = [f"{T} are {rec} {at} this year", f"{rec} {at} for {T} this season",
                                  f"{T} haven't won {at} this year ({rec})" if their_site[2] == 0 else f"{T} {at}: {rec}",
                                  f"{T} {at} this season: {rec}"]
    if s_theirs and _line(s_theirs[-1], oid).startswith("W"):
        o2, _, sc = _last_parts(s_theirs[-1], oid, pro)
        m["letdown spot for the opponent"] = [f"{T} are coming off a {sc} win over {o2} - a letdown spot",
                                              f"{T} just beat {o2} {sc}; letdowns follow that",
                                              f"fresh off beating {o2} {sc}, {T} walk into a letdown spot"]
    if bench and bench[0] is not None and bench[1] is not None and bench[0] - bench[1] >= BENCH_GAP:
        #   (11/18, cards_1118 - layman's terms: "+5.7 per 48 minutes" is a stat sheet's unit; 48 minutes is a full game)
        _bn = lambda x: f"outscored teams by {x:g}" if x >= 0 else f"got outscored by {-x:g}"   # noqa: E731
        m["deeper bench"] = [f"last season {_pos(U)} bench {_bn(bench[0])} a game; {_pos(T)} {_bn(bench[1])}",
                             f"{_pos(U)} bench {_bn(bench[0])} a game last season, {_pos(T)} {_bn(bench[1])}",
                             f"the benches last season: {_pos(U)} {_bn(bench[0])} a game, {_pos(T)} {_bn(bench[1])}"]
    #   (the roster read, 10/20 - numbers from the box scores)
    hot = form.get((True, "hot"))
    if sp_us:
        tail = f" - {hot[1]}" if hot and hot[0] == sp_us else ""
        m["better starting pitcher"] = [f"{sp_us} is on the mound for {U}{tail}", f"{U} hand the ball to {sp_us}{tail}",
                                        f"{sp_us} starts for {U}{tail}"]
    if hot and lg == "nhl":
        m["hotter goalie"] = [f"{hot[0]} has {hot[1]}", f"{hot[0]}: {hot[1]}", f"{hot[1]} for {hot[0]}"]
    if hot and lg in ("nfl", "ncaaf"):
        m["better QB play lately"] = [f"{hot[0]} has {hot[1]}", f"{hot[0]}: {hot[1]}", f"{hot[1]} for {hot[0]}"]
    g = g or {}
    m["coming off a bye"] = [f"{U} are coming off a bye week", f"{U} had the bye week to get right", f"a bye week for {U} last week"]
    m["opponent on a short week"] = [f"{T} are on a short week", f"short week for {T}", f"{T} had a short week to get ready"]
    if str(g.get("wx_temp", "")) != "":
        m["cold-weather edge"] = [f"it's {g['wx_temp']}\u00b0F at kickoff and {T} aren't built for it",
                                  f"{g['wx_temp']}\u00b0F at kickoff - a warm-weather team in a freezer"]
    m["opponent's body clock is off"] = [f"{T} crossed time zones to get here", f"{T} are playing off their home time zone"]
    #   (11/11 pre-board check: the old "hours off" line said it of Marquette at Michigan - ONE hour; the travel
    #   factor fires at one zone, so no line claims more than "crossed time zones")
    if (sm._num(g.get("elev")) or 0) >= sm.THIN_AIR_M:
        m["altitude edge"] = [f"{T} are playing {feet(g.get('elev'))} up", f"{T} gotta breathe {feet(g.get('elev'))} up"]
    wind, rain = g.get("wx_wind", ""), g.get("wx_rain", "")
    if str(wind) not in ("", "0") and float(wind or 0) >= 15:
        m["nasty weather helps us"] = [f"{wind} mph winds keep it sloppy", f"a {wind} mph wind drags the game down"]
    elif str(rain) not in ("", "0"):
        m["nasty weather helps us"] = [f"{inches(rain)} of rain keeps it sloppy", f"{inches(rain)} of rain in the forecast"]
    return m


def _fx(fs, *fmts):
    """Every way to say a fact-bearing line: each fact wording x each line wording (the Voice picks a fresh one)."""
    fs = [fs] if isinstance(fs, str) else list(fs or [])
    return [f(c) for c in fs for f in fmts]


STANDALONE = {"opponent missing key players", "opponent on a back-to-back", "the stronger team", "hotter recent form",
              "cold opponent", "last game", "better rested", "better starting pitcher", "hotter goalie",
              "better QB play lately", "deeper bench", "public fade", "public ride", "their last loss", "home record",
              "their road record", "rolling off a blowout win"}   # facts true on their own; the rest (a bye, the weather, the last meeting we
#                                          lost...) only as the engine's reason


def nba_lines(us, them, nba_f, why_low=""):
    """🏀 Last season's facts for an opening-weeks hoops card (both records, the point gap, who we added) - four
    wordings; when the line under the pick already carries the record, only the man we added (or nothing)."""
    import sports_nba_roster as _nr
    (ru, du), (rt, dt) = nba_f["us"], nba_f["them"]
    add = nba_f.get("added") or []
    adds = [""] * 4
    if add and add[0][0].lower() not in why_low:          # (the line under the pick may already name him)
        nm, mpg, frm = add[0]                             # four tails too - the same tail on every card is a repeat
        adds = [f" {us} added {nm} ({mpg} minutes a night for the {frm} last year).",
                f" New this year: {nm}, a {mpg}-minute man for the {frm} last season.",
                f" {nm} came over from the {frm}, where he averaged {mpg} minutes.",
                f" {us} picked up {nm} - {mpg} minutes per game with the {frm} a year ago."]
    if ru.lower() in why_low:
        return [f"🏀{a}" for a in adds if a]
    try:                                                  # (11/20, the Niagara +2.5 card: "Niagara got outscored by the
        w_, l_ = (int(x) for x in str(ru).split("-")[:2])   #  other side by 7.4 nightly" - our side's losing year is a
        if (du is not None and float(du) < 0) or w_ < l_:   #  knock, never a line; the man we added can still be said)
            return [f"🏀{a}" for a in adds if a]
    except (ValueError, TypeError):
        pass
    G = _nr._gap
    return [f"🏀 Last season {us} went {ru} and {G(du, 0)}; {them} went {rt} and {G(dt, 1)}.{adds[0]}",
            f"🏀 {us} were {ru} last year ({G(du, 2)}), {them} {rt} ({G(dt, 3)}).{adds[1]}",
            f"🏀 A year ago it was {us} {ru}, {them} {rt} — {us} {G(du, 5)}, {them} {G(dt, 6)}.{adds[2]}",
            f"🏀 {them} finished {rt} last season and {G(dt, 4)}; {us} finished {ru} and {G(du, 7)}.{adds[3]}"]


def top_facts(whyf, reasons):
    """The facts the card's one-liner and a lean's bottom line hang on, best first: the engine's own reasons in
    FACT_ORDER, then the standalone facts we hold - each a sentence. [] when there's none."""
    rs = [r for r in FACT_ORDER if r in whyf and r in (reasons or [])] + \
         [r for r in FACT_ORDER if r in whyf and r not in (reasons or []) and r in STANDALONE]
    return [[c.strip()[:1].upper() + c.strip()[1:] + "." for c in _lst(whyf[r])] for r in rs]   # [[ways], [ways]...]


def _lst(x):
    return [x] if isinstance(x, str) else list(x or [])


def top_fact(whyf, reasons):
    f = top_facts(whyf, reasons)
    return f[0][0] if f and f[0] else ""


NO_WHY = "\u00a7"     # placeholder: no fresh reason left, so the line ends on our side instead of a filler "because"


def _nowhy(line):
    import re
    return re.sub(r"[\s\u2014:.,]*\u00a7\.?$", ".", line) if NO_WHY in line else line


GOOD_NEWS = re.compile(r"\bwins?\b|\bwon\b|\bvictory\b|\bbeats?\b|\btops?\b|\brout|\bassists?\b|\bscores?\b|\bgoals?\b|"
                       r"\bhat trick|\btouchdowns?\b|\bleads?\b|\bshines?\b|\bstars?\b|\breturns?\b|\bback (?:on|in|at)\b|"
                       r"\bcleared\b|\breinstated\b|\bextension\b|\bcomeback\b|\bcareer[- ]high", re.I)


def _cap(x):
    return x[:1].upper() + x[1:]


def _an(n):
    """'an' before a number that starts with a vowel sound ("an 8-game heater", "an 11-5 team"), else 'a'."""
    s = str(n)
    return "an" if s.startswith("8") or s in ("11", "18") or (s.startswith(("11", "18")) and len(s) in (2, 5)) else "a"


def _mi(n):
    return f"{int(round(n or 0, -1)):,}"


def _nth(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


TALK_KNOCKS_US = ("unhappy", "hot seat")   # talk kinds that are bad news about the team they're about


TALK_LINES = {   # pregame talk (sports_news TALK_KINDS): display only - forward-only tags, never a number
    "contract year": lambda who: [f"📣 Contract-year energy around {who} — somebody's playing for a bag.",
                                  f"📣 {_cap(who)} got money on the line this year. Contract talk all week.",
                                  f"📣 Payday season for {who}: the contract chatter is loud.",
                                  f"📣 Incentives on the line for {who}. Expect some extra effort."],
    "unhappy": lambda who: [f"📣 Not everybody's happy over there — {who} got some public frustration going.",
                            f"📣 Grumbling in {who}' camp this week, and it's out in the open.",
                            f"📣 Somebody in {who}' building is venting to the press. Vibes are off.",
                            f"📣 {_cap(who)} got a frustrated voice or two talking publicly."],
    "trash talk": lambda who: [f"📣 {_cap(who)} been running their mouth this week. Bulletin-board stuff.",
                               f"📣 Trash talk out of {who}'s side. Somebody gotta back it up now.",
                               f"📣 {_cap(who)} talked a big game all week — receipts get checked tonight.",
                               f"📣 Guarantees flying around {who}. Talk is cheap till kickoff."],
    "must-win": lambda who: [f"📣 {_cap(who)} already calling it a must-win out loud.",
                             f"📣 \"Must-win\" is the word around {who} this week. Backs to the wall.",
                             f"📣 {_cap(who)} say their season rides on this one.",
                             f"📣 Win-or-else talk coming out of {who}."],
    "rivalry week": lambda who: [f"📣 Rivalry week talk is loud around {who}. Bad blood energy.",
                                 f"📣 {_cap(who)} been hyping the rivalry all week.",
                                 f"📣 Bragging rights on the line, and {who} know it.",
                                 f"📣 {_cap(who)} been waiting on this one. No love lost here."],
    "hot seat": lambda who: [f"📣 Coach's job is a hot topic around {who}. Hot seat talk everywhere.",
                             f"📣 Job-security questions around {who}'s coach this week.",
                             f"📣 {_cap(who)}' coach is feeling the heat in the papers.",
                             f"📣 The coach over at {who} is under the microscope right now."],
}


def context_lines(leg, v, us, them, the_us, the_them, g, games=None):
    """Breakdown lines for the context study's facts (rivalry, travel, domes, stakes, refs) and pregame talk.
    Proven or not, these are just what's around the game - the numbers only move for PROVEN factors."""
    out = []
    total = leg.get("market") == "total"
    for c in leg.get("ctx") or []:
        k = c.get("k")
        if k == "rival":
            pass                                         # (10/1: never vague - the head-to-head line has the facts)
        elif k == "div":
            pass                                         # (10/1: never vague - the head-to-head line has the facts)
        elif k == "trip":
            mi, r6, d = c.get("mi") or 0, c.get("road6") or 0, c.get("dir")
            bits = []
            if mi >= 1000:
                bits.append(f"{_mi(mi)}-mile trip{' east' if d == 'E' else ' west' if d == 'W' else ''}")
            them_home = leg.get("side") == "away" and str(g.get("neutral")) != "1"
            if them_home:                                # (10/22, the owner's Predators card: "The Bruins: 3rd road game
                if r6 >= 3 and leg.get("league") in ("nba", "nhl", "ncaab"):   # in 6 days" - Boston was HOME, back
                    out.append(v.say("cx_trip_home", [                         # from a 4-game trip)
                        f"🧳 {_cap(the_them)} just got home - {r6} road games in the last 6 days.",
                        f"🧳 {_cap(the_them)} back home tonight after {r6} road games in 6 days.",
                        f"🧳 First game back for {the_them} after {r6} road games in 6 days."]))
                continue
            if r6 >= 3 and leg.get("league") in ("nba", "nhl", "ncaab"):   # (a baseball series always is)
                bits.append(f"{_nth(r6)} road game in 6 days")
            if not bits:
                continue
            fact = ", ".join(bits)
            out.append(v.say("cx_trip", [f"🧳 {_cap(the_them)}: {fact}.",
                                         f"🧳 Travel check on {the_them}: {fact}.",
                                         f"🧳 {_cap(the_them)} put in the miles to get here ({fact})."], fact=True))
        elif k == "dome_cold":
            temp, wind = g.get("wx_temp", ""), g.get("wx_wind", "")
            wx = (f"{temp}°" if str(temp) != "" else "cold") + (f" with {wind} mph wind" if str(wind) not in ("", "0")
                                                                and float(wind or 0) >= 15 else "")
            who = the_them if not total else ("the home dome team" if c.get("who") == "home" else "the road dome team")
            out.append(v.say("cx_domecold", [f"🏟️ Dome team outside in {wx} — {who} usually play with the thermostat set.",
                                             f"🏟️ {_cap(who)} play their home games under a roof. This one's outdoors in {wx}.",
                                             f"🏟️ No roof tonight for {who}. {wx.capitalize()} in the forecast.",
                                             f"🏟️ Indoor squad in the elements: {wx} for {who}."]))
        elif k == "dome_out":
            out.append(v.say("cx_domeout", [f"🏟️ {_cap(the_them)} are a dome team playing outside today.",
                                            f"🏟️ No roof for {the_them} this time — they're used to playing inside.",
                                            f"🏟️ {_cap(the_them)} leave the dome for an open-air building.",
                                            f"🏟️ Open air for an indoor team: {the_them} out of their element."]))
        elif k == "mustwin":
            out.append(v.say("cx_mustwin", [f"🚨 Must-win for {the_us} ({c.get('rec')}) — right in the playoff race.",
                                            f"🚨 {_cap(the_us)} ({c.get('rec')}) are fighting for a playoff spot. Backs against the wall.",
                                            f"🚨 Playoff race: {the_us} need this one, {the_them} don't.",
                                            f"🚨 Every game counts for {the_us} ({c.get('rec')}) right now. {_cap(the_them)}? Not so much."]))
        elif k == "rest":
            out.append(v.say("cx_rest", [f"🪑 {_cap(the_them)} already clinched — rest-the-starters territory.",
                                         f"🪑 Playoff spot locked for {the_them}. Don't be shocked if the stars sit.",
                                         f"🪑 {_cap(the_them)} got their ticket punched already. Nothing to play for tonight.",
                                         f"🪑 Clinched and coasting: {the_them} could rest guys."]))
        elif k == "tank":
            out.append(v.say("cx_tank", [f"📉 {_cap(the_them)} ({c.get('rec')}) are out of it. Draft-pick season over there.",
                                         f"📉 Eliminated and {c.get('rec')} — {the_them} are playing for ping-pong balls.",
                                         f"📉 {_cap(the_them)} ({c.get('rec')}) got nothing to play for but next year.",
                                         f"📉 Season's over for {the_them} ({c.get('rec')}), they just haven't gone home yet."]))
        elif k == "elim":
            out.append(v.say("cx_elim", [f"📉 {_cap(the_them)} are eliminated; {the_us} are still in the race.",
                                         "📉 One team's playing for a spot, the other's playing out the string.",
                                         f"📉 {_cap(the_them)} are out of the playoff picture. {_cap(the_us)} ain't.",
                                         f"📉 Playoff hopes: {the_us} alive, {the_them} done."]))
        elif k == "bowl5":
            out.append(v.say("cx_bowl", [f"🏈 {us} sit at 5 wins — one more and they're bowl eligible.",
                                         f"🏈 Bowl eligibility on the line: {us} need win number 6.",
                                         f"🏈 {us} are one W from a bowl game. Extra motivation.",
                                         f"🏈 Win 6 means a bowl trip for {us}."]))
        elif k == "hotseat":
            n = c.get("n") or 0
            #   (11/19 sweep, "never false information": the engine holds a losing streak and a bad record - it wrote
            #    "that coach is on the hot seat" / "Jobs on the line over there" / "are in a fishbowl right now", a
            #    claim about a job nobody told it and a saying nobody uses. The streak is the fact; it says the streak.)
            if n >= 3:
                out.append(v.say("cx_hotseat", [f"🧊 {_cap(the_them)} have lost {n} straight.",
                                                f"🧊 {n} losses in a row for {the_them}.",
                                                f"🧊 {_cap(the_them)} haven't won in {n} games.",
                                                f"🧊 Losing streak at {n} for {the_them}."]))
        elif k in ("ref_side", "ref_total"):
            nm = (c.get("names") or ["the crew"])[0]
            lean = c.get("lean")
            what = {"home": "the home team", "road": "the road team", "over": "the over", "under": "the under"}.get(lean, lean)
            out.append(v.say("cx_ref", [f"🦓 {nm} on the whistle tonight — his games have leaned toward {what}.",
                                        f"🦓 Zebra check: {nm}'s crew has tilted to {what} over his earlier games.",
                                        f"🦓 {nm} officiating. His track record leans {what}.",
                                        f"🦓 Officials matter: {nm}'s games have gone {what}'s way more than the book expected."]))
    for key, who, mine, other_nm in (("talk_theirs", the_them, them, us), ("talk_ours", the_us, us, them)):
        for t in (leg.get(key) or [])[:1]:                 # (10/3, the owner: "season rides on this one" says
            hl = str(t.get("headline") or "").strip()        # nothing - a talk line only with the actual quote)
            if other_nm and other_nm.lower() in hl.lower() and mine.lower() not in hl.lower():
                continue      # (10/15 truth audit: "Out of the White Sox's camp: 'Ramirez does it all as Guardians stay
                #   alive'" - ESPN tags a game story with both teams; a headline about the OTHER side isn't this camp's talk)
            if someone_elses_story(hl, mine, games, leg.get("league"), need_mine=True):
                continue      # (10/16: a league round-up that never names the team is nobody's camp talk)
            if not sports_news_camp(hl, t.get("kind"), mine):
                continue      # (11/22 board check: "Out of the Ravens' camp this week: 'Carmelo Anthony calls out Ravens'
                #   Humphrey over Baltimore 'criminals' remark'" - an outsider's words AT a Raven, off the field; the
                #   kind has to read off the headline, the team can't be the target - sports_news.camp_talk)
            if key == "talk_ours" and t.get("kind") in TALK_KNOCKS_US:
                continue      # (11/19 sweep: "📣 The Ravens in the papers: 'Flowers super frustrated by latest late-game
                #   fumble'" on a RAVENS card - our own side's bad press is a knock on our pick, never a body line)
            if TALK_LINES.get(t.get("kind")) and not total and hl:
                out.append(v.say("talk_q", [f"📣 Out of {_pos(who)} camp this week: \"{hl}\"",   # (11/19: "the Ravens's")
                                            f"📣 {_cap(who)} in the papers: \"{hl}\""]))
    return [x for x in out if x]


def public_split(leg):
    """(our % of the bets, our % of the money) on this leg's market, from the real public splits, or None."""
    import sports_public
    s = sports_public.splits_for(leg["game_id"])
    mk = {"ml": "ml", "spread": "sp", "total": "tot"}.get(leg["market"])
    if not s or not mk:
        return None
    t, m = s.get(f"{mk}_{leg['side']}_t"), s.get(f"{mk}_{leg['side']}_m")
    return (t, m) if t is not None else None


def public_side(leg, g):
    """'fade' when the public is on the other side, 'ride' when it's with us - from the real splits (% of bets) when
    we have them; otherwise the favorite stands in for the public on moneylines."""
    sp_ = public_split(leg)
    if sp_:
        return "fade" if sp_[0] <= 35 else "ride" if sp_[0] >= 65 else None
    if leg["market"] != "ml":
        return None
    other = "away" if leg["side"] == "home" else "home"
    ours, theirs = sm._int(g.get(f"ml_{leg['side']}")), sm._int(g.get(f"ml_{other}"))
    if ours is None or theirs is None:
        return None
    if ours >= 105 and theirs <= -125:
        return "fade"
    if ours <= -125:
        return "ride"
    return None


def _odds_words(p):
    """0.5 -> 'a coin flip', 0.62 -> 'about 6 in 10', 0.3 -> 'about 3 in 10'."""
    if abs(p - 0.5) < 0.03:
        return "a coin flip"
    n = round(p * 10)
    if n <= 1:
        return f"about 1 in {round(1 / p)}"
    return f"about {n} in 10"


def feet(elev_m):
    """🏔️ 11/18 (the pre-board check: the Nuggets card's altitude line was in meters - layman's terms, 11/17): a floor's
    height in feet, the way people here say it - '5,300 feet'."""
    try:
        return f"{int(round(float(elev_m) * 3.281 / 100.0) * 100):,} feet"
    except (TypeError, ValueError):
        return ""


def inches(rain_mm):
    """🌧️ rain in inches ('0.4 inches') - never metric on a card."""
    try:
        x = float(rain_mm) / 25.4
    except (TypeError, ValueError):
        return ""
    return f"{x:.1f} inches" if x >= 0.1 else "a little"


NAMED_OUT_FROM = "2026-11-19"
GOALIE_B2B_FROM = "2026-11-19"   # 🥅 their goalie on a back-to-back said plainly (more_facts) from this game day   # 🚑 the named-absence line leads the one-liner (see why_line) from this game day


def _and(xs):
    xs = [str(x) for x in xs if x]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1] if xs else ""


def named_out_ways(leg, g, them, the_them, b2b=False):
    """🚑 11/19: (ways to say it, [names]) for the opponent's key men the engine's OWN read takes off (the named reason
    "opponent missing key players: A, B (their read -N)"), or None. Hockey / the NBA say WHO they are by this team's
    box scores (the top 3 in points over its last 10 games - sports_absences.key_players): "their top two scorers",
    "their leading scorer", "two of their top three scorers". Football names carry the spot ("QB X"). Never a man the
    read doesn't count, never a guess about rank (no box scores = names only)."""
    if not g or (str(g.get("start") or "")[:10] or "9") < NAMED_OUT_FROM:
        return None
    if leg.get("inj_ok") is False:                        # 🧩 11/19: only when they are clearly more short-handed than us
        return None
    rs = next((str(r) for r in (leg.get("reasons") or []) if str(r).startswith("opponent missing key players:")), None)
    if not rs:
        return None
    body = re.sub(r"\s*\(their read[^)]*\)\s*$", "", rs.split(":", 1)[1]).strip()
    who = [x.strip() for x in body.split(",") if x.strip()][:3]
    if not who:
        return None
    lg = leg.get("league")
    lbl = ""
    if lg in ("nhl", "nba"):
        try:
            import sports_absences as sa
            oside = "away" if leg.get("side") == "home" else "home"
            top = (sa.key_players({}, lg, g.get(oside), g.get("start") or "9") or {}).get("top") or []
            nm = lambda x: re.sub(r"[^a-z]", "", str(x).lower())          # noqa: E731
            rank = sorted(i for i, p in enumerate(top) if any(nm(p) == nm(w) for w in who))
            nba = lg == "nba"                             # (the owner's words: "their best two players")
            n_ = {1: "", 2: "two ", 3: "three "}
            if len(rank) == len(who):
                if rank == list(range(len(rank))):
                    lbl = (f"their leading scorer" if len(rank) == 1 else f"their top {n_[len(rank)]}scorers") if nba \
                        else (f"their best player" if len(rank) == 1 else f"their {n_[len(rank)]}best players")
                else:
                    k = {1: "one", 2: "two", 3: "three"}[len(rank)]
                    lbl = f"{k} of their top three scorers" if nba else f"{k} of their three best players"
        except Exception:                                 # noqa: BLE001 - no rank = the names alone
            lbl = ""
    W = _and(who)
    T = the_them
    cut = lambda x: x                                     # noqa: E731
    tail = [", and they played last night", " - and on a back-to-back"] if b2b else ["", ""]
    ways = [f"{T} are without {W}" + (f", {lbl}" if lbl else "") + tail[0],
            f"no {W} for {T}" + (f" - {lbl}" if lbl else "") + tail[1],
            f"{T} gotta play without {W}" + (f", {lbl}" if lbl else "") + tail[0]]
    return [cut(w) for w in ways], [re.sub(r"^(QB|RB|WR|TE|FB|HB) ", "", w) for w in who]


HOT_RUN_LINE_FROM = "2026-11-19"
NO_KNOCK_FROM = "2026-11-19"
CLOSE_WIN_FROM = "2026-11-19"   # 📅 a close last win (under REAL_LOSS) never leads the one-liner   # 🚫 no ⚠️ risk line on a card from this game day (the owner, 11/19)   # 🧱 the other goalie's hot run (the dog score's angle) said as the reason (why_line)


def hot_overpay(leg):
    """Does the pick stand on 'the books overpay for the other goalie's hot run' (sports._dog_reasons, alone or inside
    the hockey dog score's reason)?"""
    return any("overpay for the other goalie's hot run" in str(r) for r in (leg.get("reasons") or []))


# ---- 🧩 11/19 EVERY CARD MAKES SENSE AS A WHOLE (results/studies/cards_1119b) --------------------------------------------
# The owner on the Warriors +180 card (the Grizzlies' men out sold as the reason while Curry, Green and Butler sat for
# us; "Stephen Curry is cooking" on the same card that listed him out): "Makes no fucking sense. Fucking fix this shit."
# The rules live in sports_card_check (hurt / inj_ok / coherent - the page runs them on every render); the write-up asks
# the same questions BEFORE it writes, so the bad line is never written:
#   - an injury argument (the 🚑 lines about them, 📉 their missing man, the named-absence lead, "short-handed" in the
#     bottom line) only when the other side is clearly more short-handed than ours by the box scores (leg["inj_ok"])
#   - our own men out are never a write-up line - the card's 🚑 header says both teams' lists once, plain
#   - the line under the pick says OUR side first (sports_card_check.side_first)
def coherent_on(g):
    try:
        import sports_card_check as _cc
        return _cc.coherent_on({"start": (g or {}).get("start")})
    except Exception:                                     # noqa: BLE001
        return False


def inj_ok(leg, games, g=None):
    """May this card argue the other side is short-handed? (True before COHERENT_FROM - the old card.)"""
    try:
        import sports_card_check as _cc
        if not _cc.coherent_on({"start": (g or {}).get("start") or leg.get("start")}):
            return True
        return bool(_cc.inj_ok(leg, games))
    except Exception:                                     # noqa: BLE001
        return True


def whole_card(lines, leg, v, us, lg, g, side, games):
    """The write-up's last step: the card through the coherence rules (sports_card_check.coherent). A line under the
    pick that can't stand (an injury argument we can't make, a man who is out) gives way to the card's next best fact
    for our side; the line that leads says our side first."""
    import sports_card_check as _cc
    day = str((g or {}).get("start") or "")[:10]
    if not lines or not _cc.coherent_on(leg, day):
        return lines
    lean_ = bool(leg.get("is_lean") or leg.get("tier") in ("lean", "strong")) and not _no_leans()   # (11/21: no "Lean X:")
    cx = {"lean": lean_, "thin": leg.get("floor_score") is not None and not lean_, "market": leg.get("market")}
    why, lines, _ = _cc.coherent(leg, str(leg.get("why_line") or ""), lines, games, day, cx)
    st = _cc.card_state(leg, games)
    tries = 0
    while not str(why or "").strip() and tries < 6:
        tries += 1
        top = lead_line(lines, v, us, lg)
        if not top:
            break
        _tails_ = [f"We lean {us}.", f"Lean {us}."] if lean_ else [f"{us} the side.", f"We on {us}.", f"Give me {us}.", f"Riding {us}."]
        cand = f"{str(top).rstrip()} " + _tails_[sum(map(ord, f"{g.get('id')}|{side}")) % len(_tails_)]
        lines = [x for x in lines if x is not top]
        why = _cc.one_coherent(cand, leg, cx, st, lean_)[0]
    leg["why_line"] = why or ""
    return lines


def even_records(text, gap=0.10):
    """True when a line's two W-L records are within `gap` of each other in win rate (8-22 vs 8-23) - no argument."""
    recs = [(int(a), int(b)) for a, b in re.findall(r"\b(\d{1,2})-(\d{1,2})\b", str(text or ""))
            if int(a) + int(b) >= 3 and int(a) + int(b) <= 90]
    if len(recs) < 2:
        return False
    (a1, b1), (a2, b2) = recs[:2]
    return abs(a1 / (a1 + b1) - a2 / (a2 + b2)) < gap


def _no_leans():
    """True once the owner's 11/16 'no leans' is in force (sports.LEANS_GONE) - no card says 'lean' after that."""
    try:
        import sports
        return bool(getattr(sports, "LEANS_GONE", True))
    except Exception:                                     # noqa: BLE001
        return True
