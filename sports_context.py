"""THE CONTEXT STUDY: everything around a game that "should" move it - does any of it beat the closing line?

For every real final in all six sports, walked forward in time (a result only counts once its game started 6+ hours
earlier; schedules, venues and weather are known before the game), the engine writes down:

1) RIVALRY / DIVISION - derived from the schedule itself (the game data has no division field):
   - pro leagues: a DIVISION pair meets the most every season. For season S the engine looks at the regular-season
     schedules of S (once it's complete) and up to 3 complete seasons before it, takes each pair's MEDIAN meetings per
     season (one odd season - covid, a realignment year - can't fool a median), keeps opponents at the division
     level (nfl 2+, nba 4, nhl 3.5, mlb 10+), and only calls it a division when both teams' lists agree (they share
     most of their division mates - one-off rotations never do). A CONFERENCE (league in MLB) is two divisions that
     play each other more than the rest (average meetings between the two groups).
   - college: conference mates share most of their opponents in a season (the rest of the conference); a
     non-conference game shares almost none. Common-opponent overlap >= 25% (and 3+ shared) = same conference.
   - classic named rivalries: a hand list per sport (NCAAB: the top ones).
2) TRAVEL - great-circle miles from the team's previous game venue (or from home after a 10+ day break / a new
   season) to this venue, which way it went (east / west), road-trip miles over the last 7 days, and road games in the
   last 6 days. (Time zones crossed are already in the model; this adds distance and direction.) Venue coordinates:
   data/sports/venues.json.
3) STADIUM (nfl, ncaaf, mlb) - a dome team (half+ of its home games indoors) playing outdoors, an outdoor team in a
   dome, and a dome team outside in the cold (< 40F) or wind (15+ mph) when the game has weather. The data has no
   turf/grass field, so that one isn't studied.
4) STAKES - standings rebuilt from results: late season (70%+ of the schedule played) the engine works out who has
   CLINCHED a playoff spot and who is ELIMINATED (safe checks: nobody can pass / can't pass enough teams, per
   conference when the conferences come out clean, else league-wide), who is in the RACE (neither, and within a
   few games of the cut line), a MUST-WIN for one side only (in the race vs a team that isn't), a TANK spot
   (eliminated and under .400), REST-THE-STARTERS (clinched, final few games), a college football team at 5 wins
   going for bowl-eligible 6, and a HOT SEAT (a long losing streak + a bad record; sports_news coach items are
   shown going forward - there's no news archive to test them on).
5) REFS / UMPS - from data/sports/officials.json (ESPN game summaries, backfilled by `python3 sports_context.py
   refs-backfill` on GitHub Actions - ESPN blocks this container). The NFL/NCAAF referee, the MLB home-plate umpire,
   the NBA/NCAAB/NHL referees: each official's earlier games only, home-win rate and over rate vs the no-vig close,
   shrunk toward 0 (as if 50 average games more). Skipped cleanly until the file exists.

THE PROOF: each factor x sport x bet (moneyline and spread: back the team in the spot / fade it, or for a game-level
factor the home / road / favorite / underdog side; totals: over / under) is graded at the REAL closing price (ROI per
unit) and against the no-vig closing chance (edge). Its bets are split by time into an older and a newer half. PROVEN
= 300+ bets, a profit in BOTH halves, and z >= 3.5 on the profit (the explorer's bar: ~1 in 4,300 by luck; the report
counts the tests and the false positives luck alone would give, and re-runs the grading on fake no-edge results).
Forward confirmation: a factor is remembered from the day it's proven; once it has 100+ bets on games AFTER that day
it's CONFIRMED (profit + edge z >= 1) or KILLED for good (no profit).

The engine uses proven factors only (adjust_side / adjust_total / home_shift): the strongest single one, shrunk by
n / (n + 400) - sports.py takes the single strongest proven angle across this study, the spots and the explorer so
nothing counts twice. Every factor (proven or not) can be shown in the breakdown; unproven ones never touch a number.
Saved to data/sports/context.json."""
import bisect
import json
import math
import os
import random
import sys
import time
import urllib.request
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import sports_data as sd
import sports_model as sm

PATH = os.path.join(sd.DATA, "context.json")
OFFICIALS = os.path.join(sd.DATA, "officials.json")
VENUES = os.path.join(sd.DATA, "venues.json")
LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "mlb", "nhl")
SPREAD_LEAGUES = sm.SPREAD_LEAGUES
PRO = ("nfl", "nba", "nhl", "mlb")
OUTDOOR = ("nfl", "ncaaf", "mlb")           # sports with outdoor venues (stadium factors)
EARLIER_H = 6
MIN_N = 300
Z_PROOF = 3.5
P_LUCK = 0.5 * math.erfc(Z_PROOF / math.sqrt(2))
FWD_N, FWD_Z = 100, 1.0
SHRINK = 400
SIMS = 3
REF_K = 50                                    # shrink each official toward 0 as if 50 average games more
REF_MIN_N = 30
REF_LEAN = 0.03                               # a crew leaning 3+ points (after shrinking) gets flagged

# ---------------------------------------------------------------- the factors
TEAM_FLAGS = {
    "trip1000": "traveled 1,000+ miles for this game",
    "trip2000": "traveled 2,000+ miles for this game",
    "week3000": "3,000+ travel miles over the last 7 days",
    "east1000": "flew 1,000+ miles EAST",
    "west1000": "flew 1,000+ miles WEST",
    "road3in6": "3rd road game in 6 days",
    "dome_out": "dome team playing outdoors (nfl/ncaaf/mlb)",
    "out_dome": "outdoor team playing in a dome",
    "dome_cold": "dome team outdoors in the cold (<40F) or wind (15+ mph)",
    "race": "late season, in the playoff race (neither clinched nor eliminated, near the cut line)",
    "clinched": "late season, playoff spot clinched",
    "elim": "late season, eliminated",
    "mustwin": "in the race while the opponent isn't (a must-win for one side only)",
    "tank": "eliminated and under .400",
    "rest": "clinched with the final games left (rest-the-starters spot)",
    "bowl5": "college football team at 5 wins going for bowl-eligible 6",
    "hotseat": "long losing streak + a bad record (hot seat)",
}
GAME_FLAGS = {
    "div": "division game",
    "conf": "same conference, not the division",
    "nonconf": "non-conference game",
    "rival": "classic named rivalry",
    "ref_home+": "officials whose earlier games leaned to the home team",
    "ref_home-": "officials whose earlier games leaned to the road team",
    "ref_over": "officials whose earlier games went over",
    "ref_under": "officials whose earlier games went under",
}
DIV_MIN = {"nfl": 1.5, "nba": 3.75, "nhl": 3.5, "mlb": 9.0}       # median meetings a season: division level
CONF_MIN = {"nfl": 0.38, "nba": 2.6, "nhl": 2.5, "mlb": 4.8}      # mean meetings between two divisions: same conference
COLLEGE_OVERLAP = 0.25
WINDOW = {"nba": 5}                           # complete seasons looked back (others: 3)
SPOTS = {"nfl": lambda s: 7 if s >= 2020 else 6, "nba": lambda s: 10 if s >= 2020 else 8,
         "nhl": lambda s: 8, "mlb": lambda s: 8 if s == 2020 else 6 if s >= 2022 else 5}   # playoff spots per conference
RACE_PCT = {"nfl": 0.12, "nba": 0.06, "nhl": 0.06, "mlb": 0.035}    # within this win% of the cut line = in the race
REST_LEFT = {"nfl": 2, "nba": 4, "nhl": 4, "mlb": 6}                 # games left (this one included) = final stretch
HOT_STREAK = {"nfl": 3, "ncaaf": 3, "nba": 6, "ncaab": 5, "mlb": 7, "nhl": 6}
LATE = 0.70
HOME_BASED = ("nfl", "ncaaf", "ncaab")
NIGHTLY = ("nba", "nhl", "ncaab")             # a 3rd road game in 6 days only means something here        # teams fly home between games
STAY_D = 3.5                                  # pro teams on a trip stay on the road when games are this close

RIVALS = {   # classic named rivalries (ESPN short names; older names too)
    "nfl": [("Bears", "Packers"), ("Cowboys", "Eagles"), ("Cowboys", "Commanders"), ("Cowboys", "Redskins"),
            ("Cowboys", "Washington"), ("Giants", "Eagles"), ("Giants", "Cowboys"), ("Steelers", "Ravens"),
            ("Steelers", "Browns"), ("Steelers", "Bengals"), ("49ers", "Seahawks"), ("49ers", "Rams"), ("49ers", "Cowboys"),
            ("Chiefs", "Raiders"), ("Broncos", "Raiders"), ("Chiefs", "Broncos"), ("Patriots", "Jets"),
            ("Bills", "Dolphins"), ("Patriots", "Colts"), ("Packers", "Vikings"), ("Bears", "Vikings"), ("Lions", "Packers"),
            ("Saints", "Falcons"), ("Eagles", "Commanders")],
    "nba": [("Celtics", "Lakers"), ("Celtics", "76ers"), ("Knicks", "Celtics"), ("Knicks", "Nets"), ("Lakers", "Clippers"),
            ("Pistons", "Bulls"), ("Knicks", "Heat"), ("Pacers", "Knicks"), ("Celtics", "Pistons"), ("Mavericks", "Spurs"),
            ("Rockets", "Spurs"), ("Lakers", "Warriors"), ("Celtics", "Heat"), ("Bulls", "Cavaliers")],
    "mlb": [("Yankees", "Red Sox"), ("Dodgers", "Giants"), ("Cubs", "Cardinals"), ("Yankees", "Mets"), ("Cubs", "White Sox"),
            ("Dodgers", "Angels"), ("Giants", "Athletics"), ("Orioles", "Nationals"), ("Phillies", "Mets"),
            ("Astros", "Rangers"), ("Royals", "Cardinals"), ("Reds", "Guardians"), ("Reds", "Indians"),
            ("Dodgers", "Padres"), ("Braves", "Mets")],
    "nhl": [("Bruins", "Canadiens"), ("Maple Leafs", "Canadiens"), ("Maple Leafs", "Senators"), ("Rangers", "Islanders"),
            ("Rangers", "Devils"), ("Flyers", "Penguins"), ("Oilers", "Flames"), ("Blackhawks", "Red Wings"),
            ("Capitals", "Penguins"), ("Avalanche", "Red Wings"), ("Kings", "Ducks"), ("Bruins", "Maple Leafs"),
            ("Blues", "Blackhawks"), ("Flyers", "Rangers"), ("Canucks", "Flames"), ("Canucks", "Oilers")],
    "ncaaf": [("Michigan", "Ohio State"), ("Alabama", "Auburn"), ("Army", "Navy"), ("Oklahoma", "Texas"),
              ("USC", "Notre Dame"), ("USC", "UCLA"), ("Florida", "Georgia"), ("Florida", "Florida St"),
              ("Georgia", "Georgia Tech"), ("Clemson", "South Carolina"), ("Ole Miss", "Mississippi St"),
              ("Oregon", "Oregon St"), ("Washington", "Washington St"), ("Stanford", "California"),
              ("Arizona", "Arizona St"), ("Minnesota", "Wisconsin"), ("Iowa", "Iowa State"), ("Kansas", "Kansas St"),
              ("Texas", "Texas A&M"), ("Oklahoma", "Oklahoma St"), ("Michigan", "Michigan St"), ("Notre Dame", "Michigan"),
              ("Auburn", "Georgia"), ("Alabama", "Tennessee"), ("Alabama", "LSU"), ("Florida", "Tennessee"),
              ("Pitt", "West Virginia"), ("Virginia", "Virginia Tech"), ("North Carolina", "NC State"),
              ("North Carolina", "Duke"), ("BYU", "Utah"), ("Louisville", "Kentucky"), ("Miami", "Florida St"),
              ("Colorado", "Nebraska"), ("Indiana", "Purdue"), ("Oregon", "Washington"), ("Army", "Air Force"),
              ("Navy", "Air Force"), ("Texas", "Arkansas"), ("Penn State", "Ohio State"), ("Iowa", "Minnesota"),
              ("Illinois", "Northwestern"), ("Utah", "Utah State"), ("Tennessee", "Vanderbilt"), ("Cincinnati", "Louisville"),
              ("Baylor", "TCU"), ("Boise St", "Fresno St"), ("App State", "GA Southern"), ("Navy", "Notre Dame")],
    "ncaab": [("Duke", "North Carolina"), ("Kentucky", "Louisville"), ("Kansas", "Missouri"), ("Kansas", "Kansas St"),
              ("Indiana", "Purdue"), ("Michigan", "Michigan St"), ("Arizona", "Arizona St"), ("UCLA", "USC"),
              ("Syracuse", "Georgetown"), ("Villanova", "Georgetown"), ("Cincinnati", "Xavier"), ("Gonzaga", "Saint Mary's"),
              ("Kentucky", "Tennessee"), ("Kentucky", "Florida"), ("Duke", "Maryland"), ("Ohio State", "Michigan"),
              ("Kentucky", "Indiana"), ("UConn", "Syracuse"), ("Villanova", "Saint Joseph's"), ("Iowa", "Iowa State"),
              ("BYU", "Utah"), ("Oklahoma", "Oklahoma St"), ("Texas", "Texas A&M"), ("Alabama", "Auburn"),
              ("Virginia", "Virginia Tech"), ("NC State", "North Carolina"), ("Louisville", "Memphis"),
              ("Marquette", "Wisconsin"), ("Pitt", "West Virginia"), ("UConn", "Villanova"), ("Butler", "Xavier"),
              ("Arizona", "UCLA"), ("Houston", "Memphis"), ("Kansas", "Baylor"), ("Georgetown", "St John's")],
}
_RIV = {lg: {frozenset(p) for p in ps} for lg, ps in RIVALS.items()}

REF_POS = {   # which officials count: position names from ESPN's summary (lower-case "contains")
    "nfl": ("referee",), "ncaaf": ("referee",), "mlb": ("home plate",),
    "nba": ("referee", "crew chief", "umpire"), "ncaab": ("referee", "official", "umpire"), "nhl": ("referee",),
}


# ---------------------------------------------------------------- helpers
def _ts(iso):
    return sm._ts(iso)


def season(league, iso):
    """The season a date belongs to (the year it started). Basketball/hockey roll over in September (the 2020 bubble's
    August games belong to 2019-20), football in August (week 0), baseball on the calendar."""
    y, m = int(iso[:4]), int(iso[5:7])
    return y if league == "mlb" or m >= (8 if league in ("nfl", "ncaaf") else 9) else y - 1


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def miles(a, b):
    """Great-circle miles between two (lat, lon)."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 3958.8 * math.asin(min(1.0, math.sqrt(h)))


_VEN = {}


def venues(path=None):
    p = path or VENUES
    if p not in _VEN:
        try:
            with open(p) as f:
                _VEN[p] = json.load(f)
        except (OSError, ValueError):
            _VEN[p] = {}
    return _VEN[p]


def _where(g, ven):
    v = ven.get(f'{g.get("city", "")}|{g.get("state", "")}|{g.get("country", "")}')
    return (v[0], v[1]) if v else None


def _odds(x):
    return sd.parse_american(x)


def units(odds, won):
    return (odds / 100 if odds > 0 else 100 / -odds) if won else -1.0


def load_officials(path=None):
    """{game id: [[position, name], ...]} or None when the backfill hasn't produced the file yet."""
    try:
        with open(path or OFFICIALS) as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    return d.get("games", d) if isinstance(d, dict) else None


def key_officials(league, offs):
    """The officials who count for this sport (names)."""
    keys = REF_POS.get(league, ())
    out = []
    for pos, name in offs or []:
        p = (pos or "").lower()
        if name and any(k in p for k in keys) and "linesm" not in p and "line judge" not in p:
            out.append(name)
    return out


# ---------------------------------------------------------------- the schedule: divisions + conferences
class Schedule:
    """Regular-season schedules per season (known before the season starts) -> who's in whose division/conference."""

    def __init__(self, league, games):
        self.lg = league
        self.pairs, self.teams, self.opps = {}, {}, {}
        for g in games:
            if str(g.get("stype")) != "2":
                continue
            s = season(league, g["start"])
            h, a = g["home"], g["away"]
            self.pairs.setdefault(s, Counter())[(h, a) if h < a else (a, h)] += 1
            t = self.teams.setdefault(s, Counter())
            t[h] += 1
            t[a] += 1
            o = self.opps.setdefault(s, {})
            o.setdefault(h, set()).add(a)
            o.setdefault(a, set()).add(h)
        self.seasons = sorted(self.teams)
        self.complete = set(self.seasons[:-1])        # the latest season may still be going
        med = {x: sorted(v for v in self.teams[x].values() if v >= 5) for x in self.seasons}
        med = {x: v[len(v) // 2] if v else 0 for x, v in med.items()}
        top = max(med.values(), default=0)
        self.short = {x for x, m in med.items() if m < 0.9 * top}
        self._rel, self._cc, self._conf_part = {}, {}, {}

    def _window(self, s):
        """Complete, full-length seasons: this one (once it's complete) and up to 3 (NBA 5) before it. Short seasons
        (a lockout, covid) are left out - their schedules were made up on the fly."""
        back = WINDOW.get(self.lg, 3)
        ok = [x for x in self.seasons if x in self.complete and x not in self.short]
        win = [x for x in ok if x < s][-back:] + ([s] if s in ok else [])
        return win or ([s] if s in self.teams else [])

    def _counts(self, a, b, win):
        k = (a, b) if a < b else (b, a)
        out = []
        for x in win:
            t = self.teams[x]
            if t.get(a, 0) >= 5 and t.get(b, 0) >= 5:
                out.append(self.pairs[x].get(k, 0))
        return out

    def _cand(self, a, s):
        key = (a, s)
        if key not in self._cc:
            win = self._window(s)
            opp = set()
            for x in win:
                opp |= self.opps[x].get(a, set())
            c = set()
            for b in opp:
                n = sorted(self._counts(a, b, win))
                if not n:
                    continue
                if self.lg == "nba":                  # conference rotations hit 4 games in some years, never in 5 straight
                    if n[0] >= DIV_MIN["nba"] and len(win) >= 2:
                        c.add(b)
                elif (n[(len(n) - 1) // 2] + n[len(n) // 2]) / 2 >= DIV_MIN[self.lg]:     # the median
                    c.add(b)
            self._cc[key] = c
        return self._cc[key]

    def _div(self, a, b, s):
        ca, cb = self._cand(a, s), self._cand(b, s)
        if b not in ca or a not in cb:
            return False
        A, B = ca | {a}, cb | {b}
        return len(A & B) / min(len(A), len(B)) >= 0.6

    def group(self, a, s):
        return {a} | {b for b in self._cand(a, s) if self._div(a, b, s)}

    def _conf_pro(self, a, b, s):
        win = self._window(s)
        if self.lg == "nfl" and len(win) < 2:
            return None                               # one season can't tell NFL conferences apart
        ga, gb = self.group(a, s), self.group(b, s)
        if len(ga) < 2 or len(gb) < 2:
            return None
        tot = n = 0
        for x in ga:
            for y in gb:
                if x != y:
                    c = self._counts(x, y, win)
                    if c:
                        tot += sum(c) / len(c)
                        n += 1
        return tot / n >= CONF_MIN[self.lg] if n else None

    def _opp_set(self, a, s):
        if s in self.complete:
            return self.opps.get(s, {}).get(a, set())
        return self.opps.get(s, {}).get(a, set()) | self.opps.get(s - 1, {}).get(a, set())

    def rel(self, a, b, s):
        """'div' / 'conf' / 'nonconf', or None when the schedule can't tell."""
        key = (a, b, s) if a < b else (b, a, s)
        if key in self._rel:
            return self._rel[key]
        if s not in self.teams:
            r = None
        elif self.lg in PRO:
            if self._div(a, b, s):
                r = "div"
            else:
                c = self._conf_pro(a, b, s)
                r = None if c is None else "conf" if c else "nonconf"
        else:
            oa, ob = self._opp_set(a, s) - {b}, self._opp_set(b, s) - {a}
            if min(len(oa), len(ob)) < 4:
                r = "nonconf" if max(len(oa), len(ob)) >= 6 and min(len(oa), len(ob)) < 3 else None   # FCS visitor
            else:
                common = len(oa & ob)
                r = "conf" if common >= 2 and common / min(len(oa), len(ob)) >= COLLEGE_OVERLAP else "nonconf"
        self._rel[key] = r
        return r

    def conferences(self, s):
        """{team: conference number} for season s when the conferences come out clean (2 groups, ~even), else None."""
        if s in self._conf_part:
            return self._conf_part[s]
        teams = [t for t, n in (self.teams.get(s) or {}).items() if n >= 10]
        parent = {t: t for t in teams}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for i, a in enumerate(teams):
            for b in teams[i + 1:]:
                if self.rel(a, b, s) in ("div", "conf"):
                    parent[find(a)] = find(b)
        comps = Counter(find(t) for t in teams)
        out = None
        if len(comps) == 2 and min(comps.values()) >= 0.4 * len(teams):
            ids = {c: i for i, c in enumerate(sorted(comps))}
            out = {t: ids[find(t)] for t in teams}
        self._conf_part[s] = out
        return out

    def season_len(self, team, s):
        n = (self.teams.get(s) or {}).get(team, 0)
        if s in self.complete:
            return n
        prev = [x for x in self.seasons if x < s and x in self.complete]
        if prev:
            c = sorted(v for v in self.teams[prev[-1]].values() if v >= 5)
            if c:
                return max(n, c[len(c) // 2])
        return n


# ---------------------------------------------------------------- the walk
class Walker:
    """One league's pre-game knowledge, walked forward in time: schedule-based facts (travel, venues) come from the
    schedule; standings, streaks and officials' tendencies only from games that started 6+ hours earlier."""

    def __init__(self, league, games, officials=None, ven=None):
        self.lg = league
        allg = [g for g in games.values() if g.get("league") == league and g.get("start")
                and (g.get("stype") or "?") in sd.REAL and g.get("status") != "void"]
        allg.sort(key=lambda g: (g["start"], g["id"]))
        self.sched = Schedule(league, allg)
        self.ven = ven if ven is not None else venues()
        self.offs = officials
        self.tg, self.tts = {}, {}                     # team -> its scheduled games (start order) + their times
        for g in allg:
            for side in ("home", "away"):
                self.tg.setdefault(g[side], []).append(g)
        for t, gs in self.tg.items():
            self.tts[t] = [_ts(x["start"]) for x in gs]
        self.homeloc, self.dome = {}, {}               # team -> [(time, (lat, lon))] / [(time, indoor 0|1)] at home
        for t, gs in self.tg.items():
            for x in gs:
                if x["home"] == t and str(x.get("neutral")) != "1" and str(x.get("intl")) != "1":
                    w = _where(x, self.ven)
                    if w:
                        self.homeloc.setdefault(t, []).append((_ts(x["start"]), w))
                    if x.get("indoor", "") != "":
                        self.dome.setdefault(t, []).append((_ts(x["start"]), 1 if str(x["indoor"]) == "1" else 0))
        self.hl_t = {t: [x[0] for x in v] for t, v in self.homeloc.items()}
        self.dm_t = {t: [x[0] for x in v] for t, v in self.dome.items()}
        self.st = {}                                   # (season, team) -> [points (W=2), games, wins, streak]
        self.refs = {}                                 # official -> [n home, sum home resid, n tot, sum over resid]
        self.pending = deque()
        self._legs = {}

    # -- learning from a final
    def advance(self, t):
        while self.pending and self.pending[0][0] <= t - EARLIER_H * 3600:
            self.apply(self.pending.popleft()[1])

    def flush(self):
        while self.pending:
            self.apply(self.pending.popleft()[1])

    def learn(self, g):
        self.pending.append((_ts(g["start"]), g))

    def apply(self, g):
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            return
        if str(g.get("stype")) == "2":
            s = season(self.lg, g["start"])
            ot = self.lg == "nhl" and len([x for x in str(g.get("ls_home") or "").split(",") if x != ""]) > 3
            for side, m in (("home", hs - as_), ("away", as_ - hs)):
                r = self.st.setdefault((s, g[side]), [0, 0, 0, 0])
                r[0] += 2 if m > 0 else 1 if (m == 0 or ot) else 0
                r[1] += 1
                r[2] += m > 0
                r[3] = (max(0, r[3]) + 1) if m > 0 else (min(0, r[3]) - 1) if m < 0 else 0
        if self.offs is not None:
            names = key_officials(self.lg, self.offs.get(g["id"]))
            if names:
                p = sm.market_p(g)
                hr = None if p is None or hs == as_ else (1.0 if hs > as_ else 0.0) - p
                tot = _num(g.get("total"))
                orr = None
                if tot and hs + as_ != tot:
                    oo, uo = _odds(g.get("over_odds")) or -110, _odds(g.get("under_odds")) or -110
                    orr = (1.0 if hs + as_ > tot else 0.0) - sd.no_vig(oo, uo)
                for nm in names:
                    r = self.refs.setdefault(nm, [0, 0.0, 0, 0.0])
                    if hr is not None:
                        r[0] += 1
                        r[1] += hr
                    if orr is not None:
                        r[2] += 1
                        r[3] += orr

    # -- facts
    def _prev(self, team, t):
        i = bisect.bisect_left(self.tts.get(team, []), t)       # games that started before this one
        return self.tg.get(team, [])[:i]

    def _home_at(self, team, t):
        hl = self.homeloc.get(team)
        if not hl:
            return None
        i = bisect.bisect_left(self.hl_t[team], t)
        return hl[i - 1][1] if i else hl[0][1]

    def _dome(self, team, t):
        d = self.dome.get(team)
        if not d:
            return None
        i = bisect.bisect_left(self.dm_t[team], t)
        recent = d[max(0, i - 12):i] or d[:12]
        return sum(x[1] for x in recent) / len(recent) >= 0.5

    def _leg(self, team, x, prev):
        """(miles into game x, where the team came from): from the previous game's venue when the team stayed on the
        road (pro leagues, 3.5 days or less between games), else from home (football + college hoops fly home)."""
        k = (team, x["id"])
        if k in self._legs:
            return self._legs[k]
        here, xt = _where(x, self.ven), _ts(x["start"])
        o = None
        if here is not None:
            if prev is not None and self.lg not in HOME_BASED and xt - _ts(prev["start"]) <= STAY_D * 86400:
                o = _where(prev, self.ven)
            if o is None:
                o = self._home_at(team, xt)
        r = (miles(o, here), o) if o is not None and here is not None else (None, None)
        self._legs[k] = r
        return r

    def _travel(self, g, side, t):
        team = g[side]
        prev = self._prev(team, t)
        out = {}
        neutral = str(g.get("neutral")) == "1"
        road6 = int(side == "away" and not neutral)
        for x in reversed(prev[-6:]):
            if t - _ts(x["start"]) > 6 * 86400:
                break
            road6 += x["away"] == team and str(x.get("neutral")) != "1"
        if road6:
            out["road6"] = road6
        m, o = self._leg(team, g, prev[-1] if prev else None)
        if m is None:
            return out
        here = _where(g, self.ven)
        out["mi"] = round(m)
        if m >= 300:
            out["dir"] = "E" if here[1] > o[1] else "W"
        wk = m
        for k in range(len(prev) - 1, max(-1, len(prev) - 9), -1):
            if t - _ts(prev[k]["start"]) > 7 * 86400:
                break
            mk, _ = self._leg(team, prev[k], prev[k - 1] if k else None)
            wk += mk or 0.0
        out["wk"] = round(wk)
        return out

    def _stakes(self, g, side, t):
        lg = self.lg
        if str(g.get("stype")) != "2" or lg == "ncaab":
            return {}
        s = season(lg, g["start"])
        team = g[side]
        me = self.st.get((s, team), [0, 0, 0, 0])
        L = self.sched.season_len(team, s)
        out = {"w": me[2], "l": me[1] - me[2], "gp": me[1], "left": max(0, L - me[1]), "streak": me[3]}
        pct = me[0] / (2 * me[1]) if me[1] else 0.5
        if lg == "ncaaf":
            if me[2] == 5 and me[1] >= 8:                      # late in the year, one win from a bowl
                out["bowl5"] = True
        if me[3] <= -HOT_STREAK[lg] and me[1] >= 0.25 * max(L, 1) and pct <= 0.4:
            out["hotseat"] = True
        if lg not in SPOTS or not L or me[1] < LATE * L:
            return out
        conf = self.sched.conferences(s)
        K = SPOTS[lg](s)
        if conf and team in conf:
            grp = [u for u, c in conf.items() if c == conf[team]]
        else:
            grp = [u for u in (self.sched.teams.get(s) or {}) if (self.sched.teams[s][u] >= 10)]
            K *= 2
        rows = []
        for u in grp:
            r = self.st.get((s, u), [0, 0, 0, 0])
            left = max(0, self.sched.season_len(u, s) - r[1])
            rows.append((u, r[0], r[0] + 2 * left, r[0] / (2 * r[1]) if r[1] else 0.5))
        mx = me[0] + 2 * out["left"]
        elim = sum(1 for u, p, _, _ in rows if u != team and p > mx) >= K
        clin = sum(1 for u, _, m, _ in rows if u != team and m >= me[0]) < K
        if len(rows) > K:
            cut = sorted((r[3] for r in rows), reverse=True)[K - 1]
        else:
            cut = 0.0
        out["stk"] = "clinched" if clin else "elim" if elim else \
            "race" if abs(pct - cut) <= RACE_PCT[lg] else "out" if pct < cut else "safe"
        if elim and pct < 0.4:
            out["tank"] = True
        if clin and out["left"] <= REST_LEFT[lg] and pct >= 0.55:
            out["rest"] = True
        return out

    def facts(self, g):
        """Everything this study knows about a game before it starts (call advance(t) first on a walk)."""
        t = _ts(g["start"])
        h, a = g["home"], g["away"]
        s = season(self.lg, g["start"])
        f = {"lg": self.lg, "rel": self.sched.rel(h, a, s),
             "rival": frozenset((g.get("home_name", ""), g.get("away_name", ""))) in _RIV.get(self.lg, set())}
        for side, k in (("home", "h"), ("away", "a")):
            tf = self._travel(g, side, t)
            if self.lg in OUTDOOR:
                dome = self._dome(g[side], t)
                indoor = str(g.get("indoor")) == "1"
                if dome is not None:
                    tf["dome"] = dome
                    if dome and not indoor and g.get("indoor", "") != "":
                        tf["dome_out"] = True
                        temp, wind = _num(g.get("wx_temp")), _num(g.get("wx_wind"))
                        if (temp is not None and temp < 40) or (wind is not None and wind >= 15):
                            tf["dome_cold"] = True
                    if not dome and indoor:
                        tf["out_dome"] = True
            tf.update(self._stakes(g, side, t))
            f[k] = tf
        for k, o in (("h", "a"), ("a", "h")):
            if f[k].get("stk") == "race" and f[o].get("stk") in ("clinched", "elim", "out", "safe"):
                f[k]["mustwin"] = True
        if self.offs is not None:
            names = key_officials(self.lg, self.offs.get(g["id"]))
            if names:
                hs = [self.refs.get(nm, [0, 0.0, 0, 0.0]) for nm in names]
                nh, no = sum(r[0] for r in hs), sum(r[2] for r in hs)
                f["ref"] = {"names": names, "n": nh,
                            "home": round(sum(r[1] / (r[0] + REF_K) for r in hs) / len(hs), 4),
                            "over": round(sum(r[3] / (r[2] + REF_K) for r in hs) / len(hs), 4), "n_tot": no}
        return f


def flags(f):
    """(home team flags, away team flags, game flags) from a game's facts."""
    out = []
    for k in ("h", "a"):
        tf = f.get(k) or {}
        s = set()
        mi = tf.get("mi") or 0
        if mi >= 1000:
            s.add("trip1000")
            s.add("east1000" if tf.get("dir") == "E" else "west1000")
        if mi >= 2000:
            s.add("trip2000")
        if (tf.get("wk") or 0) >= 3000:
            s.add("week3000")
        if (tf.get("road6") or 0) >= 3 and f.get("lg") in NIGHTLY:
            s.add("road3in6")
        for x in ("dome_out", "out_dome", "dome_cold", "mustwin", "tank", "rest", "bowl5", "hotseat"):
            if tf.get(x):
                s.add(x)
        if tf.get("stk") in ("race", "clinched", "elim"):
            s.add(tf["stk"])
        out.append(s)
    gf = set()
    if f.get("rel"):
        gf.add(f["rel"])
    if f.get("rival"):
        gf.add("rival")
    r = f.get("ref")
    if r and r.get("n", 0) >= REF_MIN_N:
        if r["home"] >= REF_LEAN:
            gf.add("ref_home+")
        elif r["home"] <= -REF_LEAN:
            gf.add("ref_home-")
    if r and r.get("n_tot", 0) >= REF_MIN_N:
        if r["over"] >= REF_LEAN:
            gf.add("ref_over")
        elif r["over"] <= -REF_LEAN:
            gf.add("ref_under")
    return out[0], out[1], gf


def atoms(f, side):
    """Explorer atoms for betting `side` of the game: (game atoms, this team's atoms, the opponent's atoms)."""
    hf, af, gf = flags(f)
    ref = {"ref_home+": "refh:+", "ref_home-": "refh:-", "ref_over": "refo:over", "ref_under": "refo:under"}
    ga = sorted("cx:" + x if x in ("div", "conf", "nonconf") else ref.get(x, x) for x in gf)
    mine, theirs = (hf, af) if side == "home" else (af, hf)

    def team(s):
        out = []
        for x in s:
            if x in ("race", "clinched", "elim"):
                out.append("stk:" + x)
            elif x in ("trip1000", "trip2000"):
                continue
            else:
                out.append(x)
        if "trip2000" in s:
            out.append("mi:2k+")
        elif "trip1000" in s:
            out.append("mi:1-2k")
        return sorted(out)
    return ga, team(mine), team(theirs)


# ---------------------------------------------------------------- facts for every game (cached per games dict)
_CACHE = {}


def facts_table(games, league, officials=None):
    """{game id: facts} for every real final of a league, walked forward (no peeking)."""
    key = (id(games), len(games), league, officials is not None)
    if key in _CACHE:
        return _CACHE[key][0]
    W = Walker(league, games, officials)
    out = {}
    for g in sm.finals(games, league):
        W.advance(_ts(g["start"]))
        out[g["id"]] = W.facts(g)
        W.learn(g)
    W.flush()
    _CACHE[key] = (out, W)
    return out


class Index:
    """What the engine knows going into upcoming games: each league's walker after every final (no per-game facts
    are computed for the history, so this is quick)."""

    def __init__(self, games, officials=False):
        offs = load_officials() if officials is False else officials
        self.w = {}
        for lg in LEAGUES:
            hit = _CACHE.get((id(games), len(games), lg, offs is not None))
            if hit:
                self.w[lg] = hit[1]
                continue
            W = Walker(lg, games, offs)
            for g in sm.finals(games, lg):
                W.learn(g)
            W.flush()
            self.w[lg] = W

    def facts(self, g):
        W = self.w.get(g.get("league"))
        return W.facts(g) if W is not None and g.get("home") and g.get("start") else {}


def index(games):
    return Index(games)


# ---------------------------------------------------------------- grading
def _rows(games, league, table):
    """[(start, facts flags, ml, spread, total)] - each bet (fair chance of home/over, odds home, odds away, 1/0)."""
    out = []
    for g in sm.finals(games, league):
        f = table.get(g["id"])
        if f is None:
            continue
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            continue
        ml = sp = tot = None
        oh, oa = _odds(g.get("ml_home")), _odds(g.get("ml_away"))
        if oh and oa and hs != as_:
            ml = (sd.no_vig(oh, oa), oh, oa, 1 if hs > as_ else 0)
        line = _num(g.get("spread_home"))
        if league in SPREAD_LEAGUES and line is not None and hs - as_ + line != 0:
            sh, sa = _odds(g.get("spread_home_odds")) or -110, _odds(g.get("spread_away_odds")) or -110
            sp = (sd.no_vig(sh, sa), sh, sa, 1 if hs - as_ + line > 0 else 0)
        t = _num(g.get("total"))
        if t and t > 0 and hs + as_ != t:
            oo, uo = _odds(g.get("over_odds")) or -110, _odds(g.get("under_odds")) or -110
            tot = (sd.no_vig(oo, uo), oo, uo, 1 if hs + as_ > t else 0)
        hp = ml[0] if ml else sm.market_p(g)
        out.append((g["start"], flags(f), ml, sp, tot, hp))
    return out


def _cells(rows, league):
    """{cell key: [(row, bet on home / over?)]}. Team flags: back the team in the spot or fade it (both sides in the
    spot = skipped). Game flags: the home / road / favorite / dog side. Totals: over / under on game flags and on
    'any:' team flags (either team in the spot)."""
    cells = {}
    outs = ("ml", "spread") if league in SPREAD_LEAGUES else ("ml",)
    for i, (_, (hf, af, gf), _, _, _, hp) in enumerate(rows):
        for fl in hf ^ af:
            home_in = fl in hf
            for o in outs:
                cells.setdefault(f"{fl}|{o}|team", []).append((i, home_in))
                cells.setdefault(f"{fl}|{o}|fade", []).append((i, not home_in))
        for fl in gf:
            for o in outs:
                cells.setdefault(f"{fl}|{o}|home", []).append((i, True))
                cells.setdefault(f"{fl}|{o}|road", []).append((i, False))
                if hp is not None and hp != 0.5:
                    cells.setdefault(f"{fl}|{o}|fav", []).append((i, hp > 0.5))
                    cells.setdefault(f"{fl}|{o}|dog", []).append((i, hp < 0.5))
        for fl in gf | {"any:" + x for x in hf | af}:
            cells.setdefault(f"{fl}|total|over", []).append((i, True))
            cells.setdefault(f"{fl}|total|under", []).append((i, False))
    return cells


_OI = {"ml": 2, "spread": 3, "total": 4}


def _bets(rows, mem, outcome, fake=None):
    """[(units, won - fair)] in time order for a cell's bets at the real prices."""
    j = _OI[outcome]
    out = []
    for i, home in mem:
        b = rows[i][j]
        if b is None:
            continue
        fair, oh, oa, y = b
        if fake is not None:
            y = fake[j][i]
        won = y if home else 1 - y
        out.append((units(oh if home else oa, won), won - (fair if home else 1 - fair)))
    return out


def _z(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m / math.sqrt(v / n) if v > 0 else 0.0


def grade(bets):
    n = len(bets)
    if not n:
        return {"n": 0}
    P = [u for u, _ in bets]
    E = [e for _, e in bets]
    h = n // 2
    a, b = P[:h], P[h:]
    return {"n": n, "roi": round(sum(P) / n, 4), "z": round(_z(P), 2), "edge": round(sum(E) / n, 4),
            "z_edge": round(_z(E), 2), "n_old": len(a), "roi_old": round(sum(a) / len(a), 4) if a else 0.0,
            "n_new": len(b), "roi_new": round(sum(b) / len(b), 4) if b else 0.0}


def passes(s):
    return s.get("n", 0) >= MIN_N and s["roi_old"] > 0 and s["roi_new"] > 0 and s["z"] >= Z_PROOF


def _shift(rows, mem, outcome):
    """Logit nudge for the cell's bet, fit on all its games, shrunk by n / (n + 400)."""
    j = _OI[outcome]
    n = w = 0
    fs = 0.0
    for i, home in mem:
        b = rows[i][j]
        if b is None:
            continue
        n += 1
        w += b[3] if home else 1 - b[3]
        fs += b[0] if home else 1 - b[0]
    if not n:
        return 0.0
    return round((sm.logit((w + 1) / (n + 2)) - sm.logit(fs / n)) * n / (n + SHRINK), 4)


def load(path=None):
    try:
        with open(path or PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def study(games, path=PATH, officials=False, sims=SIMS, seed=7, leagues=LEAGUES, verbose=True):
    """Grade every factor x sport x bet; prove, confirm going forward, or kill. Returns (and saves) the result."""
    t0 = time.time()
    offs = load_officials() if officials is False else officials
    prev = load(path)
    reg = prev.get("registry") or {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    per, tested = {}, 0
    for lg in leagues:
        table = facts_table(games, lg, offs)
        rows = _rows(games, lg, table)
        if not rows:
            continue
        cells = _cells(rows, lg)
        res = {}
        for key, mem in cells.items():
            o = key.split("|")[1]
            s = grade(_bets(rows, mem, o))
            s["tested"] = s.get("n", 0) >= MIN_N
            tested += s["tested"]
            res[key] = s
        per[lg] = {"rows": rows, "cells": cells, "res": res}
    # the null: fake results drawn from the fair price itself (no edge anywhere) - how many pass by luck?
    rnd = random.Random(seed)
    null = []
    for _ in range(sims):
        k = 0
        for lg, v in per.items():
            rows = v["rows"]
            fake = {j: [None if r[j] is None else int(rnd.random() < r[j][0]) for r in rows] for j in (2, 3, 4)}
            for key, mem in v["cells"].items():
                if v["res"][key]["tested"]:
                    k += passes(grade(_bets(rows, mem, key.split("|")[1], fake)))
        null.append(k)
    out = {"_meta": {"tested": tested, "z_bar": Z_PROOF, "min_n": MIN_N, "p_luck": P_LUCK,
                     "expected_false_positives": round(tested * P_LUCK, 3),
                     "null_sims": sims, "null_passed_avg": round(sum(null) / sims, 3) if sims else None,
                     "refs": "officials.json loaded" if offs is not None else "skipped: no data/sports/officials.json yet",
                     "team_flags": TEAM_FLAGS, "game_flags": GAME_FLAGS, "at": now}}
    for lg, v in per.items():
        rows, res = v["rows"], v["res"]
        newest = rows[-1][0]
        proven, confirmed, killed, shifts, near = [], [], [], {}, []
        for key, s in res.items():
            rk = f"{lg}|{key}"
            e = reg.get(rk)
            o = key.split("|")[1]
            if e and e.get("status") == "killed":           # killed for good: never used again
                s["killed"] = True
                killed.append(key)
                continue
            if e:                                            # forward check: only games after the day it was proven
                fwd = grade(_bets(rows, [(i, hb) for i, hb in v["cells"][key] if rows[i][0] > e["since"]], o))
                e["fwd"], e["checked"] = fwd, now
                if fwd.get("n", 0) >= FWD_N and fwd["roi"] <= 0:
                    e["status"], e["killed"] = "killed", now
                    s["killed"] = True
                    killed.append(key)
                    continue
                if fwd.get("n", 0) >= FWD_N and fwd["z_edge"] >= FWD_Z and e.get("status") != "confirmed":
                    e["status"], e["confirmed"] = "confirmed", now
            if passes(s) and not e:
                e = reg[rk] = {"since": newest, "found": now, "status": "proven", "disc": dict(s)}
            if passes(s) or (e and e.get("status") == "confirmed"):
                s["proven"] = True
                proven.append(key)
                if e.get("status") == "confirmed":
                    confirmed.append(key)
                shifts[key] = _shift(rows, v["cells"][key], o)
            elif s.get("tested") and s["roi_old"] > 0 and s["roi_new"] > 0:
                near.append((s["z"], key))
        near.sort(reverse=True)
        out[lg] = {"games": len(rows), "cells": res, "proven": sorted(proven), "confirmed": sorted(confirmed),
                   "killed": sorted(killed), "shifts": shifts, "closest": [k for _, k in near[:8]]}
    out["registry"] = reg
    out["_meta"]["secs"] = round(time.time() - t0, 1)
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)
    if verbose:
        print("\n".join(summary(out)))
    return out


def summary(st, top=6):
    m = st.get("_meta") or {}
    lines = [f"THE CONTEXT STUDY: {m.get('tested')} tests with {MIN_N}+ bets; bar z >= {Z_PROOF} + profit in both halves. "
             f"Luck alone: ~{m.get('expected_false_positives')} false positives expected "
             f"(fake no-edge results passed {m.get('null_passed_avg')} on average); refs: {m.get('refs')}"]
    for lg in LEAGUES:
        v = st.get(lg)
        if not v:
            continue
        lines.append(f"{lg}: {v['games']} games · proven {v['proven'] or '-'} · confirmed {v['confirmed'] or '-'}"
                     f" · killed {v['killed'] or '-'}")
        best = sorted(((c["z"], k, c) for k, c in v["cells"].items() if c.get("tested")), key=lambda x: -x[0])[:top]
        for z, k, c in best:
            lines.append(f"   {k:28} n={c['n']:6d} roi old {c['roi_old']:+.3f} new {c['roi_new']:+.3f} "
                         f"edge {c['edge']:+.4f} z={c['z']:+.2f}{'  PROVEN' if c.get('proven') else ''}")
    return lines


# ---------------------------------------------------------------- hooks for the engine
def _cands(st, league, f, market):
    """Every proven cell's logit shift from the HOME side's point of view (moneyline / spread) or the OVER's (total)."""
    v = (st or {}).get(league) or {}
    sh = v.get("shifts") or {}
    if not sh or not f:
        return []
    hf, af, gf = flags(f)
    out = []
    for key, s in sh.items():
        fl, o, how = key.split("|")
        if o != market:
            continue
        if market == "total":
            on = fl in gf or (fl.startswith("any:") and (fl[4:] in hf or fl[4:] in af))
            if on:
                out.append((s if how == "over" else -s, key))
            continue
        if how in ("team", "fade") and (fl in hf) != (fl in af):
            sign = 1 if fl in hf else -1
            out.append((sign * (s if how == "team" else -s), key))
        elif how in ("home", "road", "fav", "dog") and fl in gf:
            hp = f.get("_hp")
            if how == "home":
                out.append((s, key))
            elif how == "road":
                out.append((-s, key))
            elif hp is not None and hp != 0.5:
                home_fav = hp > 0.5
                out.append((s if (how == "fav") == home_fav else -s, key))
    return out


def best(cands):
    """The single strongest (largest |shift|) of [(shift, name)] - angles overlap, so they never add up."""
    return max(cands, key=lambda c: abs(c[0]), default=(0.0, None))


def home_shift(st, league, f, market="ml", hp=None):
    """(logit shift for the home side, cell) - the strongest proven context factor in this game, or (0, None)."""
    if f and hp is not None:
        f = {**f, "_hp": hp}
    return best(_cands(st, league, f, market))


def total_shift(st, league, f):
    return best(_cands(st, league, f, "total"))


def adjust_side(st, league, f, side, p, market="ml", hp=None):
    """A side's win (ml) / cover (spread) chance nudged by the strongest proven context factor."""
    s, _ = home_shift(st, league, f, market, hp)
    s = s if side == "home" else -s
    return p if not s or p is None else sm.sigmoid(sm.logit(p) + s)


def adjust_total(st, league, f, p_over):
    s, _ = total_shift(st, league, f)
    return p_over if not s or p_over is None else sm.sigmoid(sm.logit(p_over) + s)


LABELS = {"trip1000": "opponent's long trip", "trip2000": "opponent's cross-country trip",
          "week3000": "opponent's heavy travel week", "road3in6": "opponent's road grind", "dome_out": "dome team outdoors",
          "dome_cold": "dome team in the cold", "out_dome": "outdoor team in a dome", "mustwin": "must-win spot",
          "tank": "tank spot", "rest": "rest-the-starters spot", "bowl5": "bowl-eligibility push", "hotseat": "hot-seat spot",
          "race": "playoff race", "clinched": "clinched team", "elim": "eliminated team", "div": "division game",
          "conf": "conference game", "nonconf": "non-conference game", "rival": "rivalry game",
          "ref_home+": "the officiating crew", "ref_home-": "the officiating crew", "ref_over": "the officiating crew",
          "ref_under": "the officiating crew", "west1000": "opponent flew west", "east1000": "opponent flew east"}


def reasons(st, league, f, side, market="ml", hp=None):
    """A short reason when a PROVEN context factor backs this side (for the pick's reasons list), else []."""
    s, key = home_shift(st, league, f, market, hp)
    if not key or (s > 0) != (side == "home"):
        return []
    return [f"proven spot: {LABELS.get(key.split('|')[0], key.split('|')[0])}"]


# ---------------------------------------------------------------- display (the breakdown), proven or not
def display(f, side, market="ml"):
    """The context facts worth a line in the breakdown, from the side we're on: [{"k": kind, ...}]. Display only."""
    if not f:
        return []
    out = []
    if market == "total":
        if f.get("rival"):
            out.append({"k": "rival"})
        elif f.get("rel") == "div":
            out.append({"k": "div"})
        r = f.get("ref")
        if r and r.get("n_tot", 0) >= REF_MIN_N and abs(r.get("over", 0)) >= REF_LEAN and \
                (r["over"] > 0) == (side == "over"):
            out.append({"k": "ref_total", "names": r["names"][:1], "lean": side})
        for k in ("h", "a"):
            if (f.get(k) or {}).get("dome_cold"):
                out.append({"k": "dome_cold", "who": "home" if k == "h" else "away"})
                break
        return out
    us, them = (f.get("h") or {}, f.get("a") or {}) if side == "home" else (f.get("a") or {}, f.get("h") or {})
    if f.get("rival"):
        out.append({"k": "rival"})
    elif f.get("rel") == "div":
        out.append({"k": "div"})
    far = (them.get("mi") or 0) >= 1000 and (them.get("mi") or 0) - (us.get("mi") or 0) >= 1000   # (10/5: "Braves are
    #   coming off a 1,930-mile trip" - the Dodgers made the same flight; a trip is only a fact for us when it's theirs alone)
    if far or ((them.get("road6") or 0) >= 3 and f.get("lg") in NIGHTLY):
        out.append({"k": "trip", "who": "them", "mi": them.get("mi") if far else 0, "road6": them.get("road6") or 0,
                    "dir": them.get("dir"), "wk": them.get("wk")})
    if them.get("dome_cold"):
        out.append({"k": "dome_cold", "who": "them"})
    elif them.get("dome_out"):
        out.append({"k": "dome_out", "who": "them"})
    if us.get("mustwin"):
        out.append({"k": "mustwin", "who": "us", "rec": f"{us.get('w', 0)}-{us.get('l', 0)}"})
    if them.get("rest"):
        out.append({"k": "rest", "who": "them"})
    elif them.get("tank"):
        out.append({"k": "tank", "who": "them", "rec": f"{them.get('w', 0)}-{them.get('l', 0)}"})
    elif them.get("stk") == "elim" and us.get("stk") == "race":
        out.append({"k": "elim", "who": "them"})
    if us.get("bowl5"):
        out.append({"k": "bowl5", "who": "us"})
    if them.get("hotseat"):
        out.append({"k": "hotseat", "who": "them", "n": -them.get("streak", 0)})
    r = f.get("ref")
    if r and r.get("n", 0) >= REF_MIN_N and abs(r.get("home", 0)) >= REF_LEAN and (r["home"] > 0) == (side == "home"):
        out.append({"k": "ref_side", "names": r["names"][:1], "lean": "home" if r["home"] > 0 else "road"})
    return out


def tags(f, side, market="ml"):
    """Flag names for the self-check's report-only groups: us:<flag>, them:<flag>, game:<flag>."""
    if not f:
        return []
    hf, af, gf = flags(f)
    if market == "total":
        return sorted({f"game:{x}" for x in gf} | {f"any:{x}" for x in hf | af})
    us, them = (hf, af) if side == "home" else (af, hf)
    return sorted({f"us:{x}" for x in us} | {f"them:{x}" for x in them} | {f"game:{x}" for x in gf})


# ---------------------------------------------------------------- officials backfill (runs on GitHub Actions)
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={eid}"
REF_ORDER = ("nfl", "mlb", "nba", "nhl", "ncaaf", "ncaab")     # the refs that matter most first


def parse_officials(payload):
    """[[position, name], ...] from an ESPN summary (gameInfo.officials)."""
    out = []
    for o in ((payload or {}).get("gameInfo") or {}).get("officials") or []:
        name = o.get("displayName") or o.get("fullName")
        pos = (o.get("position") or {}).get("displayName") or (o.get("position") or {}).get("name") or ""
        if name:
            out.append([pos, name])
    return out


def _save_officials(data, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:                  # one game per line: small git diffs
        f.write('{"games": {\n')
        items = sorted(data.items())
        f.write(",\n".join(f"{json.dumps(k)}: {json.dumps(v, separators=(',', ':'))}" for k, v in items))
        f.write("\n}}\n")
    os.replace(tmp, path)


def fetch_officials(league, eid):
    url = SUMMARY.format(path=sd.LEAGUES[league][0], eid=eid)
    for i in range(2):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:     # plain request: ESPN 403s custom user agents
                return parse_officials(json.load(r))
        except Exception as e:                                    # noqa: BLE001
            if i == 1:
                sd.ERRORS.append(f"summary {league} {eid}: {str(e)[:100]}")
                return None
            time.sleep(1.5)


def refs_backfill(budget_s=1700, workers=8, path=None, games=None, fetch=None, chunk=400):
    """Walk our finished games a chunk at a time (the last 3 days of every sport first, then the history, the
    sports whose refs matter most first, newest first) and save their officials. Stops starting new calls after
    budget_s; the next run picks up where this one stopped. A game with no officials listed (after 3 days) is saved
    as [] so it isn't asked again. Returns (fetched, still to do)."""
    path = path or OFFICIALS
    games = sd.load_games() if games is None else games
    fetch = fetch or fetch_officials
    try:
        with open(path) as f:
            data = json.load(f).get("games") or {}
    except (OSError, ValueError):
        data = {}
    now = time.time()
    fin = [g for g in games.values() if g.get("status") == "final" and (g.get("stype") or "?") in sd.REAL
           and g["id"] not in data and g.get("league") in REF_ORDER]
    recent = sorted((g for g in fin if now - _ts(g["start"]) < 3 * 86400), key=lambda g: g["start"], reverse=True)
    old = sorted((g for g in fin if now - _ts(g["start"]) >= 3 * 86400),
                 key=lambda g: (REF_ORDER.index(g["league"]), -_ts(g["start"])))
    todo = recent + old
    deadline = time.time() + budget_s
    got = 0
    errors = 0
    for i in range(0, len(todo), chunk):
        if time.time() > deadline:
            break
        part = todo[i:i + chunk]

        def run(g):
            if time.time() > deadline:
                return g, None
            return g, fetch(g["league"], g["id"].split(":", 1)[1])
        with ThreadPoolExecutor(workers) as ex:
            res = list(ex.map(run, part))
        for g, offs in res:
            if offs is None:
                errors += 1
                continue
            if offs or now - _ts(g["start"]) >= 3 * 86400:
                data[g["id"]] = offs
                got += 1
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        if got:                                       # nothing fetched yet: no file (the study keeps skipping refs)
            _save_officials(data, path)
        print(f"   officials: {got} saved this run, {len(data)} total, {max(0, len(todo) - i - len(part))} to go"
              f" ({errors} errors)", flush=True)
        if errors > 50 and got == 0:
            print("   ESPN unreachable - stopping", flush=True)
            break
    left = len(todo) - got
    return got, left


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "refs-backfill":
        t = time.time()
        n, left = refs_backfill(int(os.environ.get("REFS_BUDGET_S", "1700")))
        print(f"refs backfill: {n} games saved, ~{left} left, {time.time() - t:.0f}s")
        if load_officials() is not None:
            study(sd.load_games())
    else:
        study(sd.load_games())
