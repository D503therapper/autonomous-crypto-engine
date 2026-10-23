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

PT = ZoneInfo("America/Los_Angeles")
VERSION = 24          # bump when the wording changes: posted plays get their breakdown rewritten (never the pick)


@functools.lru_cache(maxsize=400000)
def _t(iso):
    """(10/16 hoops readiness: cached - data_gaps ran seen_all for 488 college hoops sides over 56,000 finals, 27 million
    strptime calls, 8 minutes a board; the same date string parses once.)"""
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


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


NBA_EARLY_GAMES = 5    # the first weeks of hoops: last season's facts carry the card until this many games are in
REC_GAP = 3            # 10/23, the owner: "Army 4-2, Tulsa 4-3 ... we know which side we want - they both have 4 wins":
#                        a record is a 'better team' line only 3+ games better (wins minus losses: 4-2 vs 4-3 is 1;
#                        93-68 vs 87-75 is 13)
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
    return len(mine) >= weeks - 1


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
    return abs(pct(a) - pct(b)) <= 0.15 and abs(a[0] - b[0]) <= max(2, round(CLOSE_WIN_SHARE * n))


CLOSE_WIN_SHARE = 0.03


def _record(gs, tid):
    w = sum(1 for g in gs if _line(g, tid).startswith("W"))
    lo = sum(1 for g in gs if _line(g, tid).startswith("L"))
    t = len(gs) - w - lo
    return f"{w}-{lo}" + (f"-{t}" if t else "")


def _site_rec(gs, tid, side):
    """('home' / 'road', games, wins, '3-0') - the team's record at this game's site this season, or None."""
    at = [x for x in gs or [] if x.get("home" if side == "home" else "away") == tid]
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
    "eat": r"\b(let's eat|we eat|we're eating|we eating|eat)\b", "tap in": r"tap in", "we gon see": r"gon' see|finna see",
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
    "bulletin board": r"bulletin[- ]board", "circled": r"circled", "fishbowl": r"fishbowl", "thermostat": r"thermostat"}


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


SHORT_L = ["Lock it in.", "Easy money.", "Trust the algorithm.", "Free money.", "We eating.", "Book it.", "Stamp it.",
           "Say less.", "We locked in.", "All day.", "Bank it.", "Cash it."]
SHORT_S = ["Tap in.", "Let's eat.", "Trust the algorithm.", "We finna see.", "We gon' see.", "Get in.", "Right side.",
           "Good number.", "Say less.", "Ride it.", "Let it ride.", "Smart side."]


def _read(leg):
    """The read a leg's own number comes from: the weighed read (Lock / plays), the dog read, else the own read."""
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


def OWNER_LOCK(price, us, leg):
    """The Lock's closer in the owner's own words (10/18, the owner: "it's not really the lingo I trained you with") -
    one of his phrases per card, each family once a board (SLANG), a plain line only once they're all taken."""
    f = fair_am(leg.get("_read")) if isinstance(leg, dict) else None
    if f:                                                # (10/22: our number next to the book's - a fact, every time)
        out = [f"✅ Bottom line: {price}. We make {us} {f} - the book's at {_am(leg.get('odds'))}. Lock it in.",
               f"✅ Bottom line: {price}. Our number on {us} is {f}. Free money at this price.",
               f"✅ Bottom line: {price}. We'd lay {f} on {us} - getting {_am(leg.get('odds'))}. Easy money.",
               f"✅ Bottom line: {price}. {f} on our sheet, {_am(leg.get('odds'))} at the book. Trust the algorithm.",
               f"✅ Bottom line: {price}. We price {us} at {f}. We eating.",
               f"✅ Bottom line: {price}. Fair on {us} is {f} to us - let's eat."]
    else:
        out = [f"✅ Bottom line: {price}. The engine likes {us} more than the books do. Lock it in.",
               f"✅ Bottom line: {price}. Our top play today. Trust the algorithm.",
               f"✅ Bottom line: {price}. {us} on top today. We eating."]
    if (leg.get("odds") or 0) > 0:                       # "super value" = a Lock at plus money (sports_owner_lingo)
        out = [f"✅ Bottom line: {price}. A Lock at plus money - super value. Tap in.",
               f"✅ Bottom line: {price}. Plus money on our Lock? Super value."] + out
    return out


def OWNER_PLAY(price, us, fair=None, odds=None):
    """A value play's closer in the owner's words (10/18) - see OWNER_LOCK. fair: our read as a price (10/22) - then
    every closer says our number next to the book's."""
    if fair and odds is not None:
        o = _am(odds)
        return [f"✅ Bottom line: {price}. We make {us} {fair} - the book's paying {o}. Tap in.",
                f"✅ Bottom line: {price}. Our number's {fair}; they're giving us {o}. We eating.",
                f"✅ Bottom line: {price}. We'd play {us} down to {fair}. At {o}, let's eat.",
                f"✅ Bottom line: {price}. {fair} on our sheet, {o} at the book. Trust the algorithm.",
                f"✅ Bottom line: {price}. We price {us} at {fair} - {o} is extra money. That's just facts.",
                f"✅ Bottom line: {price}. Fair on {us} is {fair} to us. The homies riding at {o}.",
                f"✅ Bottom line: {price}. We got {us} at {fair}, the book says {o}. We finna see."]
    return [f"✅ Bottom line: {price}. The books are sleeping on {us}. Tap in.",
            f"✅ Bottom line: {price}. Our read beats the number. Tap in.",
            f"✅ Bottom line: {price} pays more than it should. We eating.",
            f"✅ Bottom line: {price}. Good number, right side - let's eat.",
            f"✅ Bottom line: {price}. Our read's better than the price. Trust the algorithm.",
            f"✅ Bottom line: {price}. The engine found this one. Trust the algorithm.",
            f"✅ Bottom line: {price}. {us} are better than this price says - that's just facts.",
            f"✅ Bottom line: {price}. The number's too big for what {us} bring - that's just facts.",
            f"✅ Bottom line: {price}. Value on {us} - the homies riding with us.",
            f"✅ Bottom line: {price}. The homies riding {us} at this price.",
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
    """'the Canucks' -> "The Canucks'", 'Duke' -> "Duke's" (whose goalie it is)."""
    t = team[:1].upper() + team[1:]
    return t + "'" if t.endswith("s") else t + "'s"


class Voice:
    """Picks a way to say each line: different wording from game to game and day to day, and never the same
    wording twice on one board (share one `used` set across a board's breakdowns)."""

    def __init__(self, seed, used=None):
        self.seed, self.used, self.mine = seed, used if used is not None else set(), []
        self.names = ()

    def say(self, key, options, must=False, names=(), tags=None):
        """A fresh way to say it, or "" (the line is dropped) when every way is already taken on this board.
        must=True: a line the card can't go without (the pick, the bottom line) - reuse a wording rather than drop it.
        Our big phrases ("cheeks clapped", "smack that ass"...) show up once a board, never on two cards in a row.
        tags: per option, extra once-a-board marks (10/23: a one-liner's kicker - "We riding X" - once a board)."""
        if not options:
            return ""
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


HYPE = re.compile(r"trust the algorithm|lock it in|free money|easy money|hammer it|hammer time|smash it|we eating|real edge|"
                  r"tips it our way|let'?s eat|bag|money energy|can'?t lose|guaranteed", re.I)


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


def breakdown(leg, games, elo, injuries, used=None):
    """A plain-talk case for one leg: a list of short bullets ending with the bottom line."""
    g = games[leg["game_id"]]
    lg, side = leg["league"], leg["side"]
    other = "away" if side == "home" else "home"
    tid, oid = g[side], g[other]
    us, them = leg["team"], leg["opp"]
    start = _t(g["start"])
    fin = [x for x in sm.finals(games, lg) if _t(x["start"]) < start]
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
    if ours and theirs and (start - _t(ours[-1]["start"])).days - (start - _t(theirs[-1]["start"])).days < 2:
        leg["reasons"] = [r for r in leg.get("reasons") or [] if r != "better rested"]
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
    n_cold = 0

    # form
    rec_u = _record(r_ours, tid) if r_ours else None
    heat = _streak(s_ours, tid)
    n_hot = int(heat.split()[1]) if heat.startswith("won") else 0
    heat_t = _streak(s_theirs, oid)                 # (10/2, the owner: "Virginia Tech, four straight W's, we don't go
    their_hot = int(heat_t.split()[1]) if heat_t.startswith("won") else 0   # against a heater - well, the other team
    if n_hot >= 2 and their_hot >= n_hot:                                    # has four straight W's"): both hot = say
        said.add("hotter recent form")                                       # both, never "the heater's ours"
        out.append(v.say("bothhot", [f"🔥 Both teams are rolling: {us} have won {n_hot} straight, {them} {their_hot}.",
                                      f"🔥 Heater vs heater - {us} {n_hot} straight W's, {them} {their_hot}.",
                                      f"🔥 Neither team has lost lately: {us} {n_hot} in a row, {them} {their_hot}."]))
        n_hot = 0                                                             # (no 'hot hand' line in the why either)
    elif rec_u and n_hot >= 2:
        said.add("hotter recent form")
        out.append(v.say("hot", [f"🔥 {us} are {rec_u} and on a {n_hot}-game heater.",
                                  f"🔥 {us} ({rec_u}) have won {n_hot} straight and they're rolling.",
                                  f"🔥 {us} are rolling — {n_hot} wins in a row, {rec_u} on the year.",
                                  f"🔥 {us} can't stop winning: {n_hot} straight, {rec_u} overall.",
            f"🔥 {us} are cooking — {n_hot} straight W's, {rec_u} overall.",
            f"🔥 Heat check: {us} have won {n_hot} in a row ({rec_u})."]))
    rec_line = bool(rec_u) and n_hot < 2 and len(r_ours) >= MIN_REC_GAMES   # (10/21, the owner: a record with a tag-line
    #                                                  after it says nothing - the record line waits to see if the
    #                                                  records get compared below; if not, it says the record WITH
    #                                                  something: the other side's record, or the last game's score)
    if r_theirs:
        rec_t = _record(r_theirs, oid)
        cold = _streak(s_theirs, oid)
        n_cold = int(cold.split()[1]) if cold.startswith("lost") else 0
        w_t = sum(1 for x in r_theirs if _line(x, oid).startswith("W"))
        rating_t = elo[lg].r.get(oid, 1500.0) if elo.get(lg) is not None else 1500.0
        trash = (len(r_theirs) >= 3 and w_t / len(r_theirs) < 0.35) or n_cold >= 3 or rating_t < 1420
        if elo.get(lg) is not None and elo[lg].r.get(tid, 1500.0) <= rating_t:
            trash = False                                # (no 'cold' dig either when the ratings don't have us better)
            n_cold = n_cold if n_cold < 2 else 0
        if n_cold >= 2 and not trash:                   # the trash-talk line below covers the really bad ones
            out.append(v.say("cold", [f"🧊 {them} are {rec_t} and ice cold — {n_cold} straight L's.",
                                       f"🧊 {them} have dropped {n_cold} in a row ({rec_t}).",
                                       f"🧊 {n_cold} straight losses for {them}. Not a good look.",
                                       f"🧊 {them} ({rec_t}) keep taking L's — {n_cold} straight.",
            f"🧊 {them} ({rec_t}) are in a slump — {n_cold} straight.",
            f"🧊 {them} forgot how to win: {n_cold} straight L's."]))

    # strength
    e = elo.get(lg)
    if e is not None:
        home_edge = 0 if str(g.get("neutral")) == "1" else (e.hfa if side == "home" else -e.hfa)
        gap = e.r.get(tid, 1500.0) - e.r.get(oid, 1500.0) + home_edge      # same yardstick as the card's reasons
        said.add("the stronger team")                   # said here either way (better / even / worse): not again later
        _ru = _record(r_ours, tid) if len(r_ours) >= 2 else None    # (10/21: 1-0 vs 0-1 compares nothing; two games in,
        _rt = _record(r_theirs, oid) if len(r_theirs) >= 2 else None   #  football's schedule line is already a real fact)
        if _ru and _rt:                                  # (10/1, the owner: "they're just better" says nothing -
            _w = lambda r: (lambda a: a[0] / max(1, a[0] + a[1]))([int(x) for x in r.split("-")[:2]])
            if gap > 15 and _w(_ru) > _w(_rt):           # the records do)
                out.append(v.say("better", [f"💪 {us} ({_ru}) vs {them} ({_rt}) — the better team is on our side.",
                                             f"💪 {_ru} against {_rt}: {us} been the better team.",
                                             f"💪 Records say it: {us} {_ru}, {them} {_rt}.",
                                             f"💪 {us} {_ru}, {them} {_rt}. Better squad on our side."]))
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
                                               f"⚖️ Same kind of record, tougher schedule: {us} lost to {nm}.",
                                               f"⚖️ Don't let {_ru} fool you — {us} took {one} from {nm}."]))
            elif close_records(_ru, _rt) and abs(gap) <= 15:   # records AND ratings close: a coin-flip game
                out.append(v.say("even", [f"⚖️ Even on paper: {us} {_ru}, {them} {_rt}.",
                                           f"⚖️ {us} {_ru}, {them} {_rt} — no separation on the records.",
                                           f"⚖️ Records are close: {us} {_ru}, {them} {_rt}."]))

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
    # the record, when nothing above compared it: with the other side's record, or with the last game's score
    if rec_line and not any(x and x[:1] in "💪🐺⚖" for x in out):
        last_said = _said(s_ours[-1], tid, pro) if s_ours else ""
        if rec_t and len(r_theirs) >= MIN_REC_GAMES:
            out.append(v.say("rec", [f"📋 {us} {rec_u}, {them} {rec_t}.",
                                      f"📋 Records: {us} {rec_u}, {them} {rec_t}.",
                                      f"📋 {us} come in {rec_u}; {them} are {rec_t}.",
                                      f"📋 {us} are {rec_u} on the year, {them} {rec_t}."]))
        elif last_said:
            out.append(v.say("rec", [f"📋 {us} are {rec_u} after a {last_said}.",
                                      f"📋 {us} {rec_u} on the year - last time out, a {last_said}.",
                                      f"📋 {us} sit {rec_u}; their last one was a {last_said}.",
                                      f"📋 {rec_u} for {us}, fresh off a {last_said}."]))
        else:
            out.append(v.say("rec", [f"📋 {us} are {rec_u} on the year.", f"📋 {us} sit {rec_u} so far."]))

    # talk our talk when the other side's been bad (only when the numbers back it up)
    if r_theirs:
        w = sum(1 for x in r_theirs if _line(x, oid).startswith("W"))
        rating_them = e.r.get(oid, 1500.0) if e is not None else 1500.0
        n_cold = int(_streak(s_theirs, oid).split()[1]) if _streak(s_theirs, oid).startswith("lost") else 0
        better = e is None or e.r.get(tid, 1500.0) > rating_them   # (10/1, the owner: a record doesn't show who they
        losing = len(r_theirs) >= 3 and w < len(r_theirs) - w       # (10/15: "Canucks ... a JV squad (1-1)", "Guardians are
        #   trash right now (85-77)" - trash talk needs a LOSING record too, not just a rating or a 3-game skid)
        _ours_worse = bool(r_ours) and rec_u and (lambda a, b: a[0] / max(1, sum(a)) < b[0] / max(1, sum(b)))(
            [int(x) for x in rec_u.split("-")[:2]], [w, len(r_theirs) - w])
        #   (10/21: a 0-3 Texans card called the 1-2 Cowboys trash - no trash talk from the side with the worse record)
        if better and losing and not _ours_worse and ((w / len(r_theirs) < 0.35) or n_cold >= 3 or rating_them < 1420):
            #   played - trash talk only when the engine's ratings, which count the schedule, have us better)
            rec = _record(r_theirs, oid)
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
            f"🗑️ {rec} lately — they ass. {them} straight ass right now."]))

    # last games: just the latest scores - and only when they back the pick (the owner, 9/30: "Kings L 1-5 vs Avalanche"
    # in the Kings' breakdown makes no sense - we won our last one, and they lost theirs or had none)
    if s_ours and _line(s_ours[-1], tid).startswith("W") and (not s_theirs or _line(s_theirs[-1], oid).startswith("L")):
        last_us = _line(s_ours[-1], tid)                  # (this season's last game - never last year's)
        both = f"{us} {last_us}" + (f" · {them} {_line(s_theirs[-1], oid)}" if s_theirs else "")
        out.append(v.say("latest", [f"📅 Latest: {both}.", f"📅 Last time out: {both}.", f"📅 Most recent games: {both}.",
                                     f"📅 Where they're coming from: {both}.", f"📅 Last week's tape: {both}." if lg in ("nfl", "ncaaf")
                                     else f"📅 Last outing: {both}.", f"📅 Previous game: {both}.", f"📅 Fresh off: {both}."]))

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
            return sp.last_starter(rows, tid_, g["start"])

        def known(team_side):                                 # 10/16 NHL checkup: is tonight's goalie KNOWN (confirmed /
            if role != "G":                                   # likely - sports_goalies)? The last starter is tonight's
                return True                                   # starter only 45% of the time (2023-26 box scores), and 5 of
            try:                                              # the season's 7 🥅 lines named a goalie who didn't play -
                import sports_goalies                         # an unknown starter is said as what he is: in net LAST time
                return sports_goalies.starter(g.get("id"), team_side) is not None
            except Exception:                                 # noqa: BLE001
                return False
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
                          f"🥅 Pucks keep getting past {_poss(the_them)} goalie, {name} — {txt}."] if kn else
                         [f"🥅 {name}, in net last time out for {the_them}, can't keep the puck out lately: {txt}.",
                          f"🥅 {name} — {_poss(the_them)} last starter in net — has been giving up a lot of goals: {txt}.",
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
                          f"🧱 Good luck scoring on {name} — {txt}."] if kn else
                         [f"🧱 {name}, in net last time out for {the_us}, has been a brick wall — {txt}.",
                          f"🧱 {name} — {_poss(the_us)} last starter in net — is standing on his head: {txt}.",
                          f"🧱 Good luck scoring on {name} if he goes again for {the_us} — {txt}."]}[role]))

    # situational spots the engine learned from 10 seasons of games
    rsn = leg.get("reasons") or []
    # (10/21, the owner: "very vague" - every spot line carries the game it's about: the score of the last meeting, of
    #  the blowout, the days off. No score on file = no line; the weight still counts, the words don't guess.)
    if "revenge game" in rsn and last_vs and _line(last_vs[-1], tid).startswith("L"):
        sc = _said(last_vs[-1], tid, pro)                 # "27-20 loss to the Lions"
        out.append(v.say("revenge", [f"😤 Revenge game — {us} took a {sc} last time these two met. They haven't forgotten.",
                                      f"😤 {us} owe {them} one: a {sc} last meeting. Payback's coming.",
                                      f"😤 Get-back game for {us} after that {sc} to these guys.",
                                      f"😤 {us} been waiting on this rematch since the {sc}."]))
        said.add("revenge game")
    if "letdown spot for the opponent" in rsn and s_theirs and _line(s_theirs[-1], oid).startswith("W"):
        o2, _, sc = _last_parts(s_theirs[-1], oid, pro)   # ("the Jets", "W", "41-10")
        out.append(v.say("letdown", [f"🪤 Letdown spot for {them} — fresh off a {sc} win over {o2}, teams come out flat after that.",
                                      f"🪤 {them} just beat the brakes off {o2}, {sc}. Classic letdown game.",
                                      f"🪤 {them} are riding high off that {sc} over {o2}. That's when teams slip.",
                                      f"🪤 Trap game for {them} after beating {o2} {sc}."]))
        said.add("letdown spot for the opponent")
    if "rolling off a blowout win" in rsn and s_ours and _line(s_ours[-1], tid).startswith("W"):
        o2, _, sc = _last_parts(s_ours[-1], tid, pro)
        out.append(v.say("momentum", [f"🚀 {us} just beat the brakes off {o2}, {sc}.",
                                       f"🚀 {us} smacked {o2} {sc} last time out.",
                                       f"🚀 Fresh off a {sc} win over {o2}.",
                                       f"🚀 {_cap(o2)} got their cheeks clapped by {us} last time out, {sc}."]))
        said.add("rolling off a blowout win")
    temp, wind, rain = g.get("wx_temp", ""), g.get("wx_wind", ""), g.get("wx_rain", "")
    if "altitude edge" in rsn and (sm._num(g.get("elev")) or 0) >= sm.THIN_AIR_M:
        out.append(v.say("alt", [f"🏔️ Thin air — {g.get('elev')} meters up. {_cap(the_them)} gonna be sucking wind by the second half.",
                                  f"🏔️ Altitude game. {_cap(the_them)} ain't used to breathing up there.",
                                  f"🏔️ Mile-high problems for {the_them}. Legs get heavy fast at that elevation."]))
        said.add("altitude edge")
    if "cold-weather edge" in rsn:
        out.append(v.say("cold_w", [f"🥶 {temp}°F at kickoff. {_cap(the_them)} are a warm-weather squad walking into a freezer.",
                                     f"🥶 It's gonna be {temp}°F. {_cap(the_them)} don't play in this — {the_us} do.",
                                     f"🥶 Cold one ({temp}°F). Welcome to real weather, {the_them}."]))
        said.add("cold-weather edge")
    if "nasty weather helps us" in rsn:
        what = f"{wind} mph winds" if str(wind) not in ("", "0") and float(wind or 0) >= 15 else f"{rain} mm of rain"
        out.append(v.say("wx", [f"🌧️ {what} in the forecast. Sloppy game, fewer big plays — that's how dogs eat.",
                                 f"🌬️ {what}. Ugly weather drags everybody down to the same level.",
                                 f"🌧️ Weather's nasty ({what}). Anything can happen in the slop."]))
        said.add("nasty weather helps us")
    if "opponent's body clock is off" in rsn:
        out.append(v.say("jetlag", [f"🕐 {_cap(the_them)} crossed a few time zones for this one. Body clock's all messed up.",
                                     f"🕐 Jet-lag game for {the_them} — their bodies think it's a different time.",
                                     f"🕐 Long trip for {the_them}, time zones and all. Legs gonna be heavy."]))
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
        if lines:
            out.append(v.say("drama_" + kind.replace("/", "_").replace(" ", "_"), lines))
        said.add(drama_r)
    out += context_lines(leg, v, us, them, the_us, the_them, g, games)
    if "coming off a bye" in rsn:
        out.append(v.say("bye", [f"🛌 {us} are fresh off a bye — rested and game-planned up.",
                                  f"🛌 Extra week to prep for {us}. That matters.",
                                  f"🛌 Bye week in the rearview for {us}. Fresh legs, full playbook."]))
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
    if str(g.get("intl")) == "1":
        pass                                            # no real home crowd overseas
    elif side == "home":
        _hm = [x for x in r_ours if x.get("home") == tid]
        if len(_hm) >= 2:                                # (10/1: never vague - the home record, or nothing)
            _hr = _record(_hm, tid)
            out.append(v.say("home", [f"🏟️ {us} are {_hr} at home this year.",
                                       f"🏟️ Home game for {us} — {_hr} in their building so far.",
                                       f"🏟️ {us} at home: {_hr} this season.",
                                       f"🏟️ {_hr} at home for {us} this year."]))
    else:
        _rd = [x for x in r_ours if x.get("away") == tid]
        if len(_rd) >= 2:                                # (10/1: "they travel just fine" said nothing - the record does)
            _rr = _record(_rd, tid)
            out.append(v.say("road", [f"🧳 {us} are {_rr} on the road this year.",
                                       f"🧳 Road game for {us} — {_rr} away from home so far.",
                                       f"🧳 {us} away from home: {_rr} this season.",
                                       f"🧳 {_rr} on the road for {us} this year."]))

    # rest
    if ours and theirs:
        d_us, d_them = (start - _t(ours[-1]["start"])).days, (start - _t(theirs[-1]["start"])).days
        h_us, h_them = [(start - _t(x[-1]["start"])).total_seconds() / 3600 for x in (ours, theirs)]
        if h_them <= B2B_HOURS < h_us:                       # (10/15 truth audit: "Short rest for the Bruins" with two
            #   nights off - a 47-hour gap truncated to 1 "day"; a back-to-back is the next night, by the clock)
            out.append(v.say("b2b", [f"😴 {them} played last night; {us} had {d_us} day{'s' if d_us != 1 else ''} off.",
                                      f"😴 Second night of a back-to-back for {them}. {us} are rested.",
                                      f"😴 {them} on a back-to-back, {us} on {d_us} day{'s' if d_us != 1 else ''} of rest."]))
        elif d_us - d_them >= 2 and d_us <= 10:              # (a season-opener gap isn't "rest")
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
        key_them = sd.team_key_out(inj, oid, them, lg)
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
        elif key_them and not both:
            pos, nm = _posname(key_them[0][1], lg), key_them[0][0]
            out.append(v.say("keyout", [f"🚑 {them} are rolling without their starting {pos} ({nm}).",
                                         f"🚑 No {nm} for {them} — that's their starting {pos}.",
                                         f"🚑 {them} are down their starting {pos}, {nm}."]))
        # (the owner, 10/1: one depth guy out is no edge - "is he even a star?" - but "if a team's hella banged up and
        #  got a bunch of injured players, that line is totally good": 3+ out, and 2+ more than us)
        starters_out = sd.team_key_out(inj, oid, them, lg)    # (the owner, 10/1: "hella banged up" means STARTERS -
        if len(starters_out) >= 3 and len(theirs_out) - len(ours_out) >= 2:   # only players we KNOW are key count;
            #                                                       a depth guy on the report never does)
            out.append(v.say("banged", [f"🚑 {them} are hella banged up ({_names(theirs_out)}).",
                                         f"🚑 {_pos(them)} injury list is stacking up: {_names(theirs_out)}.",
                                         f"🚑 {them} are missing bodies — {_names(theirs_out)}.",
            f"🚑 {them} are dealing with injuries: {_names(theirs_out)}.",
            f"🚑 {them} are short-handed ({_names(theirs_out)})."]))
        elif not ours_out and not theirs_out and not team_unsure(inj, tid, us):
            # (10/16 truth audit: "Wild questionable: D Zach Bogosian, LW Marcus Foligno" and "Wild have everybody
            #  available" sat on the same card - a side with anyone questionable is never 'full squad')
            out.append(v.say("healthy", [f"✅ {us} are healthy — nobody important sitting.",
                                          f"✅ Full squad for {us}.", f"✅ {us} have everybody available.",
            f"✅ {us} are at full strength.",
            f"✅ Nobody big missing for {us}."]))

    # every "because" on the card is a FACT (10/21, the owner: "very vague and not our lingo" - "they're the better
    # team" / "they're banged up" said nothing): the reasons mapped to what we can show, and the one top fact the
    # card's one-liner and a lean's bottom line hang on
    _kt = sd.team_key_out(inj, oid, them, lg) if inj else []
    _ku = sd.team_key_out(inj, tid, us, lg) if inj else []
    _b2b = bool(ours and theirs) and (start - _t(theirs[-1]["start"])).total_seconds() / 3600 <= B2B_HOURS \
        < (start - _t(ours[-1]["start"])).total_seconds() / 3600
    _gap_d = ((start - _t(ours[-1]["start"])).days - (start - _t(theirs[-1]["start"])).days) if ours and theirs else 0
    _bench = None
    if lg == "nba":                                       # (the roster read's bench numbers - a fact for a thin card)
        try:
            import sports_nba_roster as _nr
            _bn = (_nr.cached() or {}).get("bench") or {}
            _bench = (_bn.get(str(tid)), _bn.get(str(oid)))
        except Exception:                                 # noqa: BLE001
            _bench = None
    _pub = public_split(leg)                              # (10/23: the real split is a fact the one-liner can open with)
    _site = _site_rec(r_ours, tid, side)                  # our home / road record, theirs
    _tsite = _site_rec(r_theirs, oid, other)
    whyf = why_map(lg, us, them, the_us, the_them, pro, rec_u=rec_u, rec_t=rec_t, n_hot=n_hot, their_hot=their_hot,
                   n_cold=n_cold, key_them=_kt, key_us=_ku, b2b=_b2b, gap_d=_gap_d if 2 <= _gap_d <= 10 else 0,
                   last_vs=[x for x in last_vs if (start - _t(x["start"])).days <= REVENGE_DAYS],   # (never a 2023 game)
                   tid=tid, oid=oid, s_ours=s_ours, s_theirs=s_theirs, nba_f=nba_f, form=FORM,
                   sp_us=g.get("sp_" + side) if lg == "mlb" else None, g=g, bench=_bench,
                   pub=_pub, site=_site, their_site=_tsite)
    leg["facts"] = top_facts(whyf, rsn)[:3]               # [[ways to say fact 1], [fact 2]...] best first
    leg["fact"] = leg["facts"][0][0] if leg["facts"] else ""
    # the line under the pick is written HERE, before the money / public lines pick their "because" - it gets first
    # call on the wording, and whatever reason it says is `said` (the 💸 / 🤡 lines name a different fact, never the same)
    leg["why_line"] = why_line(leg, v, g, us, them, the_us, the_them, rec_u=rec_u, n_hot=n_hot, rec_t=rec_t,
                               n_cold=n_cold, gap=gap, form=FORM, key_them=_kt, key_us=_ku,
                               whyf=whyf, fact=leg["fact"], nba_f=nba_f, facts=leg["facts"][0] if leg["facts"] else ())
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
    if key_us and key_them2 and lg == "mlb":
        nm, nm2 = key_us[0][0], key_them2[0][0]
        out.append(v.say("keyout_both_bat", [
            f"🚑 Both lineups are missing a big bat — no {nm} for {the_us}, no {nm2} for {the_them}. Still our side.",
            f"🚑 Both sides are missing someone: {nm} ({the_us}) and {nm2} ({the_them}). The price already has it - we still like {the_us}."],
            must=True))
    elif key_us and key_them2:                            # both teams down a starter: one plain line, not two
        pos, nm, nm2 = _posname(key_us[0][1], lg), key_us[0][0], key_them2[0][0]
        mv = f" The line already moved for it ({_am(op)} → {_am(now)})." if op is not None and now is not None and op != now else ""
        out.append(v.say("keyout_both", [
            f"🚑 Both teams are down their starting {pos} — {nm} is out for {the_us}, {nm2} for {the_them}.{mv} We still riding with the algorithm.",
            f"🚑 Backups on both sides tonight: no {nm} for {the_us}, no {nm2} for {the_them}.{mv} The numbers still say this the side.",
            f"🚑 Neither team has its starting {pos} — {nm} ({the_us}) and {nm2} ({the_them}) are both out.{mv} We still like {the_us}."],
            must=True))
    elif key_us and lg == "mlb":                          # our best bat is out: say it, and say why we still ride
        nm = key_us[0][0]                                 # (the owner, 9/29: like the Caleb Williams one - it's out,
        mv = ""                                           # it don't change our call. A bat on the IL has been out a
        #                                                   while - today's line move isn't "for it")
        out.append(v.say("keyout_us_bat", [
            f"🚑 Yeah, {nm} is out for {the_us}. We know.{mv} The price already knows it too, and the numbers still say this the side.",
            f"🚑 No {nm} tonight — that's a big bat missing for {the_us}.{mv} Doesn't change our call. We riding with the algorithm.",
            f"🚑 {nm} ain't playing. Everybody's scared off {the_us} because of it.{mv} We ain't — the rest of this lineup still gets it done."],
            must=True))
    elif key_us:
        pos, nm = _posname(key_us[0][1], lg), key_us[0][0]
        mv = f" The line already moved for it ({_am(op)} → {_am(now)})." if op is not None and now is not None and op != now else ""
        pts = leg.get("line") if leg.get("market") == "spread" else None
        need = f" {_cap(the_them)} gotta win by {int(pts) + 1}+ to beat us. Win by {int(pts)}, win by 1, or lose — we cash." \
            if pts and pts > 0 and pts != int(pts) else ""
        out.append(v.say("keyout_us", [
            f"🚑 {nm} is out, {the_us} rolling with the backup {pos}.{mv} We know. We still riding with the algorithm.{need}",
            f"🚑 No {nm} tonight — backup {pos} gets the keys for {the_us}.{mv} Vegas already baked that in, and the numbers still say this the side.{need}",
            f"🚑 Yeah, {nm} is out. Everybody and they mama jumped off {the_us}.{mv} We ain't scared — teams always be coming back.{need}"],
            must=True))
    if not key_any and op is not None and now is not None and op != now and sd.implied(now) > sd.implied(op):
        # the price moving our way: the market catching up to US - never "we're with the sharps" (the owner, 9/29: we're
        # our own engine, not a sharp-money follower)
        out.append(v.say("sharp", [f"💰 {us} opened {_am(op)}, now {_am(now)} — money's coming in on 'em.",   # (10/22:
                                    f"💰 {us} went from {_am(op)} to {_am(now)} since the open.",          #  the move,
                                    f"💰 The line moved toward {us}: {_am(op)} → {_am(now)}.",             #  no claims
                                    f"💰 {_am(op)} at the open, {_am(now)} now. The money's on {us} too.",  #  about it)
            f"💰 {us} been getting bet: {_am(op)} → {_am(now)}.",
            f"💰 {us} moved {_am(op)} → {_am(now)}. We rocking with the sharps on this one."]))

    # sharp money going the other way and we still like our side: say it our way, with a quick reason
    op_o, now_o = sm._int(g.get(f"ml_{other}_open")), sm._int(g.get(f"ml_{other}"))
    if lg in ("nfl", "ncaaf"):
        op_o = op_o_fb
    if not key_any and op is not None and now is not None and sm.logit(sd.implied(op)) - sm.logit(sd.implied(now)) >= 0.08:
        if op_o is not None and now_o is not None and op_o != now_o:
            move = f" ({_am(op_o)} → {_am(now_o)})"
        else:                                             # (10/16 hoops readiness: Wake Forest "-4500 → -4500" - the
            move = f" ({us} {_am(op)} → {_am(now)})"       # book's cap never moved; the move that fired is OUR side's
        #                                                   price, so that's the one the card shows - never a non-move)
        hot_ok = _streak(s_ours, tid).startswith("won") and not _streak(s_theirs, oid).startswith("won")
        #   (10/16 truth audit: "we're on the Titans, they're the hotter team" - a 0-4 side on a 4-game skid; the
        #    'hotter team' why needs a winning streak on our side and none on theirs, or it's another reason / none)
        why_r = next((r for r in leg.get("reasons") or []
                      if r in whyf and r not in said and (r != "hotter recent form" or hot_ok)), None)
        whys = _lst(whyf[why_r]) if why_r else [NO_WHY]
        if why_r:
            said.add(why_r)
        out.append(_nowhy(v.say("fade", _fx(whys,   # (10/21, the owner: "very vague" - the old pool
            #                                         bragged about money going AGAINST us; it's a warning - say so)
            lambda w: f"💸 Heads up: the line moved toward {the_them}{move}. We still got {the_us} — {w}.",
            lambda w: f"💸 The money went toward {the_them}{move}. The engine still has {the_us} — {w}.",
            lambda w: f"💸 {_cap(the_them)} got bet up{move}. We're still on {the_us} — {w}.",
            lambda w: f"💸 Line's moving toward {the_them}{move}. Not our favorite sign, but we still like {the_us} — {w}.",
            lambda w: f"💸 Somebody's betting {the_them}{move}. The engine didn't budge off {the_us} — {w}."))))

    # who's betting who: the real splits (the same numbers Google shows) - unless the one-liner already said them
    sp_ = None if ("public fade" in said or "public ride" in said) else public_split(leg)
    if sp_ and sp_[1] is None:                            # bets % only (Yahoo's backup has no money %): say that plain
        t = sp_[0]
        crowd = the_us if t >= 50 else the_them
        out.append(v.say("splits_y", [
            f"📊 {max(t, 100 - t)}% of the bets are on {crowd}." + (" We with 'em on this one." if t >= 50 else " We on the other side."),
            f"📊 The public's got {max(t, 100 - t)}% of the tickets on {crowd}." + (" Same side as us." if t >= 50 else " Not us."),
            f"📊 {crowd} got {max(t, 100 - t)}% of the bets." + (" Popular pick, right pick." if t >= 50 else " We fading that.")]))
        sp_ = None
    if sp_:
        t, m = sp_
        mk = {"ml": "the moneyline", "spread": "the spread", "total": "the total"}[leg["market"]]
        # (10/21, the owner: the splits lines were filler - "public's usually wrong, not this time", "for once the
        #  the crowd lines". The splits don't pick winners (the 10/7 study, dead), so the card just says who's on
        #  who when it's lopsided - a 40-60 split says nothing and is dropped)
        if t <= 35:
            out.append(v.say("splits_f", [
                f"📊 {100 - t}% of the bets and {100 - m}% of the money on {the_them} on {mk}. We on the other side.",
                f"📊 The public's on {the_them}: {100 - t}% of the bets, {100 - m}% of the money. Not us.",
                f"📊 {_cap(the_them)} got {100 - t}% of the tickets ({100 - m}% of the money). We got {the_us}.",
                f"📊 Everybody and they mama on {the_them} ({100 - t}% of the bets). We riding {the_us} anyway."]))
        elif t >= 65:
            out.append(v.say("splits_w", [
                f"📊 {t}% of the bets and {m}% of the money on {the_us}. Same side as the public on this one.",
                f"📊 The public's with us: {t}% of the bets, {m}% of the money on {the_us}.",
                f"📊 {_cap(the_us)} got {t}% of the tickets ({m}% of the money). Popular side.",
                f"📊 Everybody and they mama on {the_us}: {t}% of the bets, {m}% of the money."]))

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
    if leg.get("near_price"):                                            # the always-a-Lock backup (the owner, 10/1):
        out.append(v.say("bottom_near", [                                # the likeliest winner, priced about right -
            f"✅ Bottom line: {price}. Our Lock today, priced about right - a small bet, not a big one.",
            f"✅ Bottom line: {price}. We like {us} to win; the price is close to fair, so we keep it small.",
            f"✅ Bottom line: {price}. Fair price on a side we trust - small bet.",
            f"✅ Bottom line: {us} to win, {price}. The number's about even with our read - we ride it light."]) or
                   _short(v, price, True, ""))                           # (small, honest - never "value")
    elif _need and _own <= _need and _own < 0.56 and leg.get("market") == "ml":   # (10/1, the owner: "we like the Kraken,
        out.append(v.say("bottom_c", [                                   # just not at this price" at -108 makes no
            f"✅ Bottom line: {price}. We've got this one close to a coin flip - {us} by a hair. No units.",   # sense:
            f"✅ Bottom line: {price}. Close to 50-50 on our read, {us} a hair better. Just a lean.",          # the real
            f"✅ Bottom line: {price}. Near a coin flip to us - {us} is the side, not a bet we put money on.",  # reason is
            f"✅ Bottom line: {price}. Our read has it close to even. {us} by a hair - a lean."]) or         # a coin flip)
                   _short(v, price, False, "Close to a coin flip on our read."))
    elif _need and _own <= _need:                                        # read beat the price or not; ONE % only
        _f = fair_am(_own)                                               # (10/22: our number vs theirs - the reason)
        out.append(v.say("bottom_n", ([f"✅ Bottom line: {price}. We make {us} {_f}; the book wants {_am(leg['odds'])}. Lean only.",
                                       f"✅ Bottom line: {price}. Our number's {_f} - at {_am(leg['odds'])} there's no money in it. A lean."]
                                      if _f and leg.get("market") == "ml" else []) + [   # when it's over 55. Never "value" on a read
            f"✅ Bottom line: {price}. Right side, but the price is too steep for units - just a lean.",   # under it)
            f"✅ Bottom line: we like {us}, not the price. A lean, no money on it.",
            f"✅ Bottom line: {price} costs too much for what we see. Lean only.",
            f"✅ Bottom line: {us} is the side - the odds just don't beat the price. A lean.",
            f"✅ Bottom line: good side, bad number. {price} is a lean, no units.",
            f"✅ Bottom line: {price}. We'd ride {us}, but not with money at this price.",
            f"✅ Bottom line: {us} is our side; {price} is too rich for units. Lean it."]) or _short(v, price, False, _fact))
    elif leg.get("tier") == "lock":                                      # a lock: our whole chest, never a hedge
        out.append(v.say("bottom_lo", OWNER_LOCK(price, us, {**leg, "_read": _own})) or v.say("bottom_l", [
            f"✅ Bottom line: {price}. The engine likes {us} more than the books do. Lock it in.",
            f"✅ Bottom line: {price} — this price is cheaper than it should be. We're all in.",
            f"✅ Bottom line: {price}. The books got this one priced wrong. Stamp it.",
            f"✅ Bottom line: {price}. Our read beats this number. Say less.",
            f"✅ Bottom line: {price} — the value's on our side.{pos} Locked in.",
            f"✅ Bottom line: {price}.{pos} The price didn't catch up to our read. Tap in.",
            f"✅ Bottom line: {price}. We'd lay this all day - the number's in our favor.",
            f"✅ Bottom line: {price}. The side we trust most today, at a price that pays. That's money."]) or _short(v, price, True, _fact))
    else:
        out.append(v.say("bottom_so", OWNER_PLAY(price, us, fair_am(_own), leg.get("odds"))) or v.say("bottom_s", [
            f"✅ Bottom line: {price}. The engine gives {us} a better shot than this price does. That's the bet.",
            f"✅ Bottom line: {price} pays more than it should. Tap in.",
            f"✅ Bottom line: {price}. The books are sleeping on {us}. We finna see.",
            f"✅ Bottom line: {price}. Our read beats the number. Riding {us}.",
            f"✅ Bottom line: {price} — the price is the value. Get in.",
            f"✅ Bottom line: {price}. {us} are better than this number says. Quiet play, right play.",
            f"✅ Bottom line: {price}.{pos} The books undersold 'em.",
            f"✅ Bottom line: {price}. The number's in our favor - that's why we're on {us}."]) or _short(v, price, False, _fact))
    import sports_card_guard                              # 🛡️ every line passes the owner's checks before it posts
    leg["why_line"] = sports_card_guard.one(leg["why_line"], lg, us)
    lines = sports_card_guard.clean([x for x in out if x], lg, us)
    _wl = str(leg.get("why_line") or "")
    for em, body_em in SAME_STORY:                        # (10/3: the record said twice - the headline already has it;
        if _wl.startswith(em):                            #  10/21: the same for the streak, the blowout, the rest, the
            lines = [x for x in lines if not str(x).startswith(body_em)]   # last meeting - said once, under the pick)
    if rec_u and rec_u in _wl:                            # (the why line carries the record: no 📋 line too)
        lines = [x for x in lines if not str(x).startswith("📋")]
    if day_game(start):                                   # (10/4, the owner's queue: "tonight" on a 10 AM game)
        leg["why_line"] = not_tonight(leg["why_line"])
        lines = [not_tonight(x) for x in lines]
    if len(lines) > 2:
        import random
        rnd = random.Random(f"{g['id']}|{start:%Y-%m-%d}|{side}|shape")
        body, bottom = lines[:-1], lines[-1]
        keep = max(4, len(body) - rnd.randint(0, 2))          # not every pick gets every line
        must = {i for i, x in enumerate(body) if x[:1] in "🤡🤝💸🚑⚾🏀" or x.startswith("🗑️")}   # the spicy stuff stays
        #   (10/21: and the fact lines - the pitching matchup, last season's hoops facts - never shaped out)
        drop = [i for i in range(len(body)) if i not in must]
        rnd.shuffle(drop)
        gone = set(drop[:max(0, len(body) - keep)])
        body = [x for i, x in enumerate(body) if i not in gone]
        rnd.shuffle(body)
        lines = body + [bottom]
    return lines


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


def _tl(t):
    """A tail after a comma: 'We lean X.' -> 'we lean X.' (a team name up front stays capitalized)."""
    first = t.split(" ")[0]
    return (t[:1].lower() + t[1:]) if first in ("We", "That's", "Tap", "Say", "Let's", "Lean", "Good", "They") else t


def _score_gap(way):
    """'... 38-10 ...' -> 28; the margin in a fact wording's score (0 when there's none)."""
    m = re.search(r"\b(\d{1,3})-(\d{1,3})\b", way or "")
    return abs(int(m.group(1)) - int(m.group(2))) if m else 0


def _tails(lean, us, them, trash=False, beat=False):
    """What the one-liner says after the fact (the owner, 10/23: "throw out cuss words and use our lingo ... talk about
    the team itself getting their cheeks clapped or spanked"). lean: no hype, no units talk (the units line has it).
    trash: a fact says the other side's been bad (a skid, a blowout loss) - "trash ass team" is fair. beat: a beatdown
    read (a big record gap, the public heavy on a side we're fading) - "cheeks clapped" and the like are fair."""
    if lean:
        return [f"We lean {us}.", f"{us} the side here.", f"We tilt {us}.", f"{us} if you're playing it.",
                f"Lean {us}, keep it light.", f"Good parlay piece: {us}.", f"We got {us} here.",
                f"{them} don't scare us. {us} lean.", f"{us} by a little on our read.", f"Lean {us}."]
    out = [f"Tap in.", f"{us} all day.", f"We eating.", f"We riding {us}.", f"Say less.", f"{us} is the side, that's just facts.",
           f"{them} ain't ready for this shit.", f"That's a shit spot for {them}.", f"{us} fin to handle that.",
           f"Let's eat.", f"{them} fin to get spanked.", f"{us} about to spank 'em.", f"{them} about to get their ass beat.",
           f"We got {us}.", f"{us} gets it done.", f"Ride {us}.", f"Not us. We got {us}.", f"{us} take this one."]
    if beat:
        out += [f"{them} about to get their cheeks clapped.", f"{us} fin to smack that ass.",
                f"{them} fin to get their cheeks clapped.", f"{us} about to beat the brakes off 'em."]
    if trash:
        out += [f"{them} a trash ass team right now.", f"{them} straight ass right now.", f"{them} been trash as fuck.",
                f"They ass. {us} all day.", f"{them} super trash right now. We talking shit, but the tape says it."]
    return out


def _spin(key, ways, lean, us, them, em, trash=False, beat=False, names=()):
    """Every way to say a fact x every tail, in a few shapes (the owner, 10/23: never 'Team fact. Kicker.' every time)."""
    tails = _tails(lean, us, them, trash=trash, beat=beat)
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
                opts.append(f"{em} {W.rstrip('.')}, {_tl(t)}")
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
    S = lambda key, ways, em, **kw: (key, _spin(key, ways, lean, us, them, em, names=names, **kw))
    pools = []
    # ---- the other side's hole first: their key man out, a back-to-back, a heavy public we're fading ----
    if "opponent missing key players" in whyf and (not key_us):
        pools.append(S("w_hurt", whyf["opponent missing key players"], "🚑", beat=True))
    if "opponent on a back-to-back" in whyf:
        pools.append(S("w_rest", whyf["opponent on a back-to-back"], "😮‍💨"))
    if "public fade" in whyf:                             # (the owner, 10/23: "Air Force - they're about to get their
        pools.append(S("w_public", whyf["public fade"], "📊", beat=True))   # cheeks clapped. Shit like that")
    # ---- the engine's own reasons, each with the fact behind it ----
    for r in rsn:
        if r == "the stronger team":
            if rec_u and rec_t and _net(rec_u) - _net(rec_t) >= REC_GAP and min(_ng(rec_u), _ng(rec_t)) >= MIN_REC_GAMES:
                pools.append(("w_better", _ok([               # (10/23, the owner: 4-2 vs 4-3 is never "the better team" -
                    f"💪 {us} are {rec_u}, {them} are {rec_t}. Better team, better price — that's just facts.",   # REC_GAP)
                    f"💪 {rec_u} vs {rec_t}. {us} been the better squad all year and {them} know it.",
                    f"💪 {us} walk in {rec_u}; {them} walk in {rec_t}. Levels to this shit.",
                    f"💪 {us} {rec_u}, {them} {rec_t}. " + (f"We lean {us}." if lean else f"{them} about to get their ass beat."),
                    f"💪 {us} sit {rec_u} to {_pos(them)} {rec_t}. Ain't close on paper.",
                    f"💪 {us} ({rec_u}) over {them} ({rec_t}) on the record — the better team. That's just facts.",
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
                elif lean and fair_am(_read(leg)) and (_read(leg) or 0) * (leg.get("dec") or 0) > 1:
                    fa = fair_am(_read(leg))                  # (a lean's units line has no number; a unit play's does -
                    pools.append(("w_close_rec", _ok([        #  never said twice on one card)
                        f"🧠 The records look even ({us} {rec_u}, {them} {rec_t}); our ratings make {us} {fa} — the book's at {_am(leg['odds'])}.",
                        f"🧠 {rec_u} vs {rec_t} on paper, but we price {us} at {fa} and the book hangs {_am(leg['odds'])}."])))
            elif nba_f and nba_f.get("us") and nba_f.get("them") and nba_f["us"][1] > nba_f["them"][1]:
                (ru, du), (rt, dt) = nba_f["us"], nba_f["them"]     # (10/21: opening week - last season's facts)
                import sports_nba_roster as _nr
                big = _net(ru) - _net(rt) >= 10
                pools.append(("w_better_ls", _ok([         # (10/23: the 🏀 body line carries the point gaps - the
                    f"💪 {us} were {ru} last year, {them} {rt}. " + (f"We lean {us}." if lean else f"{us} all day."),   # one-liner
                    f"💪 {ru} to {rt} last season. {us} the better squad walking in — that's just facts.",           # stays short)
                    f"💪 {them} went {rt} last year. {us} went {ru}. " + (f"{us} the side here." if lean else
                                                                      (f"{them} fin to get spanked." if big else "Tap in.")),
                    f"💪 A {ru} team last year against a {rt} one. " + (f"We tilt {us}." if lean else f"Levels to this shit."),
                    f"💪 Last season: {us} {ru}, {them} {rt}. " + (f"{us} if you're playing it." if lean else f"Say less."),
                    f"💪 {us} won {ru.split('-')[0]} games last year to {_pos(them)} {rt.split('-')[0]}. " + (f"Lean {us}." if lean else f"We eating.")])))
        elif r == "hotter recent form" and n_hot >= 2 and "hotter recent form" in whyf:
            pools.append(("w_hot", _ok([
                f"🔥 {us} are rolling — {n_hot} straight W's{f', {rec_u} on the year' if rec_u else ''}. Ride the heater.",
                f"🔥 {us} are cooking right now ({n_hot} straight) and {them} ain't matching that energy.",
                f"🔥 Hot hand goes to {us} — {n_hot} straight. We don't bet against a heater.",
                f"🔥 {n_hot} straight for {us}. " + (f"We lean {us}." if lean else f"{them} fin to get spanked."),
                f"🔥 {us} haven't lost in {n_hot} — a {n_hot}-game heater{f' ({rec_u})' if rec_u else ''}. " + (f"{us} the side here." if lean else f"Let's eat."),
                f"🔥 Nobody's beaten {us} in {n_hot} games, {n_hot} straight W's. " + (f"We tilt {us}." if lean else f"{them} ain't ready for this shit.")])))
        elif r == "better starting pitcher" and sp_us and "better starting pitcher" in whyf:
            pools.append(S("w_arm", whyf["better starting pitcher"], "⚾"))
        elif r == "hotter goalie" and "hotter goalie" in whyf:
            hot = form.get((True, "hot"))
            if hot and len(hot) > 2 and not hot[2]:           # (10/16: the starter isn't confirmed - he was in net LAST time)
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
        if key in whyf and not any(k == "w_" + key.split()[0] for k, _ in pools):
            pools.append(S("w_" + key.split()[0], whyf[key], em, beat=(key == "rolling off a blowout win")))
    # ---- the top fact + the read, the way it used to close (a fact first, always) ----
    Fs = [f.strip() for f in (facts or ([fact] if fact else [])) if f and f.strip()]
    if not Fs:
        nums = ("w_num", [])
    elif round(100 * own) > 55:
        nums = ("w_num", _ok(_fx(Fs, *((lambda F: f"🔒 {F} Lock it in.", lambda F: f"🔒 {F} {us} all day.",
                                        lambda F: f"🔒 {F} {them} fin to get spanked.") if leg.get("tier") == "lock" else
                                       (lambda F: f"🧠 {F} We lean {us}.", lambda F: f"🧠 {F} {us} the side here.") if lean else
                                       (lambda F: f"🧠 {F} That's why we got {us}.", lambda F: f"🧠 {F} We riding {us}.",
                                        lambda F: f"🧠 {F} {us} is the side — that's just facts.", lambda F: f"🧠 {F} {us} all day.",
                                        lambda F: f"🧠 {F} {them} ain't ready for this shit."))), names))
    elif leg.get("near_price"):
        nums = ("w_num", _ok(_fx(Fs, lambda F: f"🔒 {F} We trust {us} to win this one - priced about right, so it's a small bet.",
                                 lambda F: f"🔒 {F} {us} to win at a fair price. A light bet, not a big one."), names))
    elif need and own <= need and own < 0.56 and leg.get("market") == "ml":   # (10/1, the owner: the Kraken at -108 - a near coin flip
        nums = ("w_num", _ok(_fx(Fs, lambda F: f"🧠 {F} Still, we've got {us} close to a coin flip - a hair better, not enough for units.",
                                 lambda F: f"🧠 {F} Even so it's close to 50-50 on our read, {us} by a hair.",
                                 lambda F: f"🧠 {F} Close to 50-50 for us, {us} by a nose."), names))   # is the reason)
    elif need and own <= need:
        nums = ("w_num", _ok(_fx(Fs, lambda F: f"🧠 {F} {us} is the side, but the price is too steep for units.",
                                 lambda F: f"🧠 {F} We like {us} - just not at this price."), names))
    elif need and lean:                                   # (a unit play's units line already shows our number)
        _fa = fair_am(own)
        nums = ("w_num", _ok(_fx(Fs, *((lambda F: f"🧠 {F} We make {us} {_fa}.", lambda F: f"🧠 {F} Our number on {us}: {_fa}.")
                                       if _fa else (lambda F: f"🧠 {F} We lean {us}.",))), names))
    elif need:
        nums = ("w_num", _ok(_fx(Fs, lambda F: f"🧠 {F} That's value on {us} — tap in.", lambda F: f"🧠 {F} {us} all day.",
                                 lambda F: f"🧠 {F} We eating."), names))
    else:
        nums = ("w_num", [])
    line = ""
    _un = lambda x: (list(x[0]), list(x[1])) if isinstance(x, tuple) else (list(x), [None] * len(x))
    for key, opts in pools + [nums]:                      # the top fact first; every wording used on the board? the next
        o, tg = _un(opts)
        line = v.say(key, o, tags=tg)
        if line:
            break
    if not line:                                          # any fresh wording left - else no line
        allo, allt = [], []
        for _, opts in pools + [nums]:
            o, tg = _un(opts)
            allo += o
            allt += tg
        line = v.say("w_any", allo, tags=allt)
    if line and (LINE_MOVE.search(line) or not _has_fact(line, names)):
        line = ""                                         # (belt and braces: the rules hold whatever the pool said)
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
BLOWOUT = 14           # a win / loss by this many is a blowout ("beat the brakes off", "cheeks clapped") - never by 3
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
                                   f"{U} are on a {n_hot}-game winning streak", f"{U} haven't lost in {n_hot}"]
    if n_cold >= 2:
        m["cold opponent"] = [f"{T} have lost {n_cold} straight", f"{n_cold} straight losses for {T}",
                              f"{T} are on a {n_cold}-game skid", f"{T} haven't won in {n_cold}"]
    if s_ours and _line(s_ours[-1], tid).startswith("W") and (not s_theirs or _line(s_theirs[-1], oid).startswith("L")):
        o2, _, sc = _last_parts(s_ours[-1], tid, pro)
        m["last game"] = [f"{U} are fresh off a {sc} win over {o2}", f"{U} just beat {o2} {sc}",
                          f"last time out {U} took {o2} {sc}", f"{U} handled {o2} {sc} last time out"]
    if gap_d >= 2:
        m["better rested"] = [f"{U} had {gap_d} more days off than {T}", f"{gap_d} extra days of rest for {U}",
                              f"{U} got {gap_d} more days to rest than {T} did", f"{T} had {gap_d} fewer days off than {U}"]
    if last_vs and _line(last_vs[-1], tid).startswith("L"):
        o2, _, sc = _last_parts(last_vs[-1], tid, pro)
        m["revenge game"] = [f"{U} took a {sc} loss to {T} the last time these two met", f"{T} beat {U} {sc} last time out",
                             f"last meeting: {T} {sc} over {U}", f"{U} dropped the last one to {T}, {sc}"]
    if s_ours and _line(s_ours[-1], tid).startswith("W") and _score_gap(_last_parts(s_ours[-1], tid, pro)[2]) >= BLOWOUT:
        o2, _, sc = _last_parts(s_ours[-1], tid, pro)      # (10/23: "blew out" only when the score says so - 14+)
        m["rolling off a blowout win"] = [f"{U} just rolled to a {sc} win over {o2}", f"{U} blew out {o2} {sc} last time out",
                                          f"{sc} over {o2} last time out for {U}", f"{U} beat the brakes off {o2}, {sc}",
                                          f"{U} smacked {o2} {sc} last time out", f"{o2} got their cheeks clapped {sc} by {U} last time out"]
    # facts about THEM (the owner, 10/23: "talk about the team itself getting their cheeks clapped or spanked")
    if s_theirs and _line(s_theirs[-1], oid).startswith("L"):
        o2, _, sc = _last_parts(s_theirs[-1], oid, pro)
        pts = sc.split("-")[0]
        m["their last loss"] = [f"{T} just lost to {o2} {sc}", f"{T} gave up {pts} to {o2} last time out",
                                f"{T} are coming off a {sc} loss to {o2}", f"{o2} beat {T} {sc} last time out",
                                f"last time out {T} took a {sc} L to {o2}", f"{o2} hung {pts} on {T} last time out"]
    if pub and pub[0] is not None:                        # the real public split (never a guess from the price)
        t, mo = pub
        n = 100 - t
        if t <= 100 - PUBLIC_HEAVY:                       # (a dozen wordings, no 4-word run shared between any two - a
            m["public fade"] = [f"{n}% of the bets are on {T}",    # board of fades never reads the same twice)
                                f"the public's got {n}% of the tickets on {T}",
                                f"{n}% of tickets are on {T}",
                                f"{n} in every 100 bets on {T}",
                                f"{n}% of the crowd is on {T}",
                                f"{T} are holding {n}% of the action",
                                f"the public side is {T}, {n}% of all bets",
                                f"only {t}% of the public is on {U}",
                                f"{T} is the public's team tonight, {n}% of bets",
                                f"the public is all over {T}, {n}% of bets"] + \
                               ([f"everybody and they mama on {T} with {100 - mo}% of the money",
                                 f"{100 - mo}% of the cash is on {T}"] if mo is not None else [])
        elif t >= PUBLIC_HEAVY:
            m["public ride"] = [f"{t}% of the bets are on {U}", f"the public's got {t}% of the tickets on {U}",
                                f"{t}% of tickets are on {U} - same side as us", f"{t} in every 100 bets on {U}, same as us",
                                f"the public side is {U}, {t}% of all bets"] + \
                               ([f"{mo}% of the cash is on {U} with us"] if mo is not None else [])
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
        m["deeper bench"] = [f"{_pos(U)} bench was {bench[0]:+g} per 48 minutes last season, {_pos(T)} {bench[1]:+g}",
                             f"last season {_pos(U)} bench ran {bench[0]:+g} a 48 minutes, {_pos(T)} {bench[1]:+g}",
                             f"bench numbers from last year: {U} {bench[0]:+g} per 48, {T} {bench[1]:+g}"]
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
    m["opponent's body clock is off"] = [f"{T} crossed time zones to get here", f"{T} are playing on a body clock a few hours off"]
    if (sm._num(g.get("elev")) or 0) >= sm.THIN_AIR_M:
        m["altitude edge"] = [f"{T} are playing {g.get('elev')} meters up", f"{g.get('elev')} meters of altitude for {T} to breathe"]
    wind, rain = g.get("wx_wind", ""), g.get("wx_rain", "")
    if str(wind) not in ("", "0") and float(wind or 0) >= 15:
        m["nasty weather helps us"] = [f"{wind} mph winds keep it sloppy", f"a {wind} mph wind drags the game down"]
    elif str(rain) not in ("", "0"):
        m["nasty weather helps us"] = [f"{rain} mm of rain keeps it sloppy", f"{rain} mm of rain in the forecast"]
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


def _cap(x):
    return x[:1].upper() + x[1:]


def _mi(n):
    return f"{int(round(n or 0, -1)):,}"


def _nth(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


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
                                         f"🧳 {_cap(the_them)} put in the miles to get here ({fact})."]))
        elif k == "dome_cold":
            temp, wind = g.get("wx_temp", ""), g.get("wx_wind", "")
            wx = (f"{temp}°" if str(temp) != "" else "cold") + (f" with {wind} mph wind" if str(wind) not in ("", "0")
                                                                and float(wind or 0) >= 15 else "")
            who = the_them if not total else ("the home dome team" if c.get("who") == "home" else "the road dome team")
            out.append(v.say("cx_domecold", [f"🏟️ Dome team outside in {wx} — {who} usually play with the thermostat set.",
                                             f"🏟️ {_cap(who)} play indoors at home. Tonight: {wx} outside.",
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
            out.append(v.say("cx_hotseat", [f"🔥 {_cap(the_them)} have lost {n} straight — that coach is on the hot seat.",
                                            f"🔥 {n} losses in a row for {the_them}. Coaching staff feeling the heat.",
                                            f"🔥 {_cap(the_them)} ({n} straight L's) are in a fishbowl right now.",
                                            f"🔥 Losing streak at {n} for {the_them}. Jobs on the line over there."]))
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
            if TALK_LINES.get(t.get("kind")) and not total and hl:
                out.append(v.say("talk_q", [f"📣 Out of {who}'s camp this week: \"{hl}\"",
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
