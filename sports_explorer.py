"""THE EXPLORER: every study run it asks NEW betting questions it has never asked before - and it's strict about it.

1) ATOMS: simple yes/no facts about a team (or a game) known BEFORE the game starts: home or road, favorite or dog,
   the price range, days of rest for the team and its opponent, a 3+ game win/losing streak, a blowout in its last
   game, revenge (it lost the last meeting), early/middle/late season, playoffs, the day of the week, a night or day
   start (Eastern time), time zones crossed to get there, altitude, cold / wind / rain outdoors, the spread size, a
   low or high total for that sport, which way the line moved (only when a real opening line exists - part of the
   history had the open backfilled from the close, and open == close there means "no information"), a 3rd+ straight
   road game, coming home after 3+ road games. Only games that started 6+ hours earlier count as "before".
   Plus the context study's facts (sports_context, same no-peeking walk): division / conference / non-conference
   game (cx:), a named rivalry, travel miles into the game (mi:1-2k / mi:2k+), which way (east1000 / west1000),
   3,000+ miles in a week, a 3rd road game in 6 nights, a dome team outdoors (and in the cold) or an outdoor team in
   a dome, the playoff race (stk:race / stk:clinched / stk:elim), a must-win, a tank, rest-the-starters, a college
   team going for bowl-eligible 6, a hot seat - for the team and ("o"...) its opponent - and the officials' lean
   (refh: / refo:) once data/sports/officials.json exists. New atoms only ever make NEW angles: every angle already
   in the registry keeps its key (and fingerprint), so nothing is retested.
   Plus TEAM TRENDS bettors quote ("the Eagles failed to cover their last 6", "bad on the road ATS", "lost 4 of 5 on
   Monday night", "take the Bears first quarter"), same no-peeking walk, each with an opponent version ("o"...):
     ats:w3 / ats:w5 / ats:l3 / ats:l5  covered (w) / failed to cover (l) its last 3+ / 5+ (pushes skipped; spread sports)
     atsr:hi / atsr:lo    season-to-date ATS 65%+ / 35%- over 6+ games
     rats:hi / rats:lo    on the road today, and its road ATS over the last 12 months is 65%+ / 35%- over 5+ road games
     pt:strong / pt:poor  a prime-time football game (TNF / SNF / MNF - sports_trends' slots) and the team's straight-up
                          record in prime-time games this season + last is 70%+ / 30%- over 5+
     divr:hi / divr:lo    a division game (sports_context) and its record vs the division this season + last 70%+ / 30%-
                          over 5+ (pro leagues only - college has conferences, not divisions)
     q1:won / q1:lost     won / lost the 1st quarter (1st period, 1st inning, college hoops' 1st half) in 5+ of its
                          last 7 games that have period scores
     ou:o4 / ou:u4        its last 4+ games went over / under the closing total (pushes skipped)
   FIRST-PART MARKETS: p1ml / p1spread grade the first part of the game at its REAL closing price, only where the data
   has both the period scores and that line: college hoops' 1st half and baseball's first 5 innings (a tie = no bet on
   the moneyline). There are no 1st-quarter lines (football / NBA have first-HALF lines only) and the NHL's few
   first-period prices are an unclear 3-way format, so the q1 atoms there are graded on full-game sides and totals.
   The run report also pools each team-trend family across sports (follow vs fade, both halves) - see family_tests.
2) ANGLES (hypotheses): sport x bet x a combination of 1-3 atoms, e.g. "NBA / moneyline / road + on a back-to-back
   + the opponent rested 2-3 days". Bets: the moneyline (at the closing price, graded against the no-juice closing
   chance), the spread (football + basketball), the over and the under (real odds, -110 when missing). Listed in a
   fixed order from simple to complex; impossible combos, combos that are just a copy of a simpler one, and combos
   with fewer than 300 games are skipped.
3) EVERY RUN: the next ~2000 angles it has NEVER tested are graded on the games so far (the "discovery" games,
   up to the newest final at that moment = the angle's cutoff). One becomes a SUSPECT only with 300+ bets, a profit
   at the real price in BOTH the older and the newer half of those games, and a z of 3.5+ (very strict, because
   thousands get tested - the report says how many suspects luck alone would produce). Every tested angle goes in
   the registry, so nothing is ever retested as "new". Then every suspect is re-checked on FORWARD games only -
   games that finished after its cutoff, which it could not have been fitted to: 100+ forward bets with a profit and
   an edge over the fair price at z 1.0+ -> PROVEN; 100+ forward bets and no profit -> KILLED. Proven angles are
   re-checked every run on all their forward games and demoted the moment they stop making money.
4) The engine can use proven angles (proven / atoms_for / adjust_side / adjust_total): a matching angle nudges the
   win / cover / over chance by its FORWARD edge only, shrunk by n / (n + 400).

Saved to data/sports/explorer.json (rejects are stored as tiny 5-byte fingerprints, not full records)."""
import base64
import bisect
import hashlib
import json
import math
import os
import time
from collections import deque
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import sports_context as scx
import sports_data as sd
import sports_model as sm
import sports_trends as strn

PATH = os.path.join(sd.DATA, "explorer.json")
LEAGUES = ("nfl", "ncaaf", "nba", "ncaab", "mlb", "nhl")
FOOTBALL = ("nfl", "ncaaf")
ET = ZoneInfo("America/New_York")
MIN_N = 300                 # bets an angle needs (in its discovery games) to be tested at all
Z_SUSPECT = 3.5             # how sure the discovery profit has to be (one-sided luck odds ~ 1 in 4,300)
P_LUCK = 0.5 * math.erfc(Z_SUSPECT / math.sqrt(2))
FWD_N, FWD_Z = 100, 1.0     # forward bets needed to promote / kill; forward edge z needed to promote
SHRINK = 400
BATCH, BUDGET_S = 6000, 480
DOG_BATCH = 3000            # 🐶 each run's underdog lane: never-tested moneyline angles on a dog, tested first
DOG_ATOMS = ("dog", "p:40-50", "p:25-40", "p:<25")   # the team is the underdog / priced as one
MAX_LEVEL = 3
EARLIER_H = 6               # an earlier game counts only if it started this many hours before
SEASON_GAP_D = 60           # a league gap longer than this starts a new season (a team gap: its history resets)
MEET_D = 400                # revenge only for a meeting within this many days
HASH_B = 5
SPREAD_CUTS = {"nfl": (3, 7), "ncaaf": (7, 14), "nba": (4.5, 9.5), "ncaab": (5.5, 11.5)}   # pick'em / fav / big fav
PRICE = ((0.75, "p:75+"), (0.60, "p:60-75"), (0.50, "p:50-60"), (0.40, "p:40-50"), (0.25, "p:25-40"), (0.0, "p:<25"))
DOW = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
FAMILY = {"home": "loc", "road": "loc", "neutral": "loc", "fav": "fd", "dog": "fd", "w3": "streak", "l3": "streak",
          "ow3": "ostreak", "ol3": "ostreak", "blowW": "blow", "blowL": "blow", "oblowW": "oblow", "oblowL": "oblow",
          "revenge": "meet", "orevenge": "meet", "early": "phase", "mid": "phase", "late": "phase", "night": "clock",
          "day": "clock", "road3": "trip", "homecoming": "trip", **{d: "dow" for d in DOW},
          # the context study's atoms (sports_context): mutually exclusive ones share a family
          "east1000": "dir", "west1000": "dir", "dome_out": "stadium", "out_dome": "stadium", "odome_out": "ostadium",
          "oout_dome": "ostadium"}
CX_OPP = ("stk:", "mi:", "tank", "mustwin", "rest", "hotseat", "dome_out", "out_dome", "dome_cold", "week3000")
LAST_TESTED = []            # the keys the latest run tested (tests look at it)
# team trends (walk-forward, see the top)
ATS_SHORT, ATS_LONG = 3, 5
RATE_HI, RATE_LO = 0.65, 0.35
ATS_RATE_N, ROAD_ATS_N, ROAD_ATS_D = 6, 5, 365
REC_HI, REC_LO, REC_N = 0.70, 0.30, 5          # prime-time / division records (this season + last)
PRIME = ("thursday night", "sunday night", "monday night")
DIV_LEAGUES = ("nfl", "nba", "mlb", "nhl")
Q1_LAST, Q1_NEED = 7, 5
OU_STREAK = 4
P1 = {"ncaab": 1, "mlb": 5}                     # first-part markets with real closing lines: periods in that part
VIG_OK = (1.0, 1.15)                            # a first-part price pair must add up to a real book's margin


def family(atom):
    """Atoms of one family can't both be true (home/road, rest buckets...), so they're never combined."""
    if atom[:2] in ("h.", "a."):
        return atom[:2] + family(atom[2:])
    if ":" in atom:
        return atom.split(":")[0]
    return FAMILY.get(atom, atom)


# ---------------------------------------------------------------- helpers
def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _odds(x):
    return sd.parse_american(x)


def _ints(x):
    """'7,3,0,14' -> [7, 3, 0, 14] (period scores); [] when missing or broken."""
    try:
        return [int(v) for v in str(x or "").split(",") if v != ""]
    except ValueError:
        return []


def units(odds, won):
    """What 1 unit at these American odds made."""
    return (odds / 100 if odds > 0 else 100 / -odds) if won else -1.0


def zscore(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m / math.sqrt(v / n) if v > 0 else 0.0


def _bits(idx, n):
    ba = bytearray((n + 7) // 8)
    for i in idx:
        ba[i >> 3] |= 1 << (i & 7)
    return int.from_bytes(ba, "little")


_BYTE = [tuple(k for k in range(8) if b >> k & 1) for b in range(256)]


def _ones(x):
    """Row numbers of the set bits, ascending."""
    out = []
    for j, b in enumerate(x.to_bytes((x.bit_length() + 7) // 8, "little")):
        if b:
            base = j * 8
            out.extend(base + k for k in _BYTE[b])
    return out


def _h(key):
    return hashlib.blake2b(key.encode(), digest_size=HASH_B).digest()


def _std_tz(tzo, t):
    """The UTC offset on standard time (summer offsets are an hour ahead - that's not a time zone crossed)."""
    return tzo - 1 if datetime.fromtimestamp(t, ET).dst() else tzo


def key_of(league, outcome, atoms):
    return f"{league}|{outcome}|{'&'.join(sorted(atoms))}"


# ---------------------------------------------------------------- 1) atoms
class League:
    """One league's pre-game knowledge, walked forward in time (finals only become known 6h after they start)."""

    def __init__(self, league, games):
        self.lg = league
        self.cx_facts, self.cx_index = None, None        # the context study's facts (set by build / index)
        self.big = sm.BIG_WIN.get(league, 10 ** 9)
        self.teams, self.tz, self.pending = {}, {}, deque()
        self.tt = {}                                          # team trends: team -> its running records
        self.tot, self.tsum, self.tsq = deque(), 0.0, 0.0
        ts = sorted(sm._ts(g["start"]) for g in games.values() if g.get("league") == league and g.get("start")
                    and (g.get("stype") or "?") in sd.REAL)
        self.s_start, self.s_len = [], []
        prev = None
        for t in ts:                                          # seasons = runs of games without a 60-day gap
            if prev is None or t - prev > SEASON_GAP_D * 86400:
                self.s_start.append(t)
                self.s_len.append(0.0)
            self.s_len[-1] = t - self.s_start[-1]
            prev = t
        if len(self.s_len) > 1:                               # the current season isn't over: assume a usual length
            done = sorted(self.s_len[:-1])
            self.s_len[-1] = max(self.s_len[-1], done[len(done) // 2])

    # -- learning from a final
    def advance(self, t):
        while self.pending and self.pending[0][0] <= t - EARLIER_H * 3600:
            self.apply(self.pending.popleft()[1])

    def flush(self):
        while self.pending:
            self.apply(self.pending.popleft()[1])

    def apply(self, g):
        t = sm._ts(g["start"])
        try:
            hs, as_ = int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            return
        neutral = str(g.get("neutral")) == "1"
        for side, opp in (("home", "away"), ("away", "home")):
            r = self.teams.setdefault(g[side], {"last": None, "streak": 0, "blow": None, "road": 0, "vs": {}})
            if r["last"] is not None and t - r["last"] > SEASON_GAP_D * 86400:
                r["streak"], r["blow"], r["road"] = 0, None, 0
            m = hs - as_ if side == "home" else as_ - hs
            r["streak"] = (max(0, r["streak"]) + 1) if m > 0 else (min(0, r["streak"]) - 1) if m < 0 else 0
            r["blow"] = "W" if m >= self.big else "L" if m <= -self.big else None
            if not neutral:
                r["road"] = r["road"] + 1 if side == "away" else 0
            if m:
                r["vs"][g[opp]] = (t, m > 0)
            r["last"] = t
        self.learn_trends(g, t, hs, as_, neutral)
        tzo = _num(g.get("tzo"))
        if tzo is not None and not neutral and str(g.get("intl")) != "1":
            self.tz[g["home"]] = _std_tz(tzo, t)
        tot = _num(g.get("total"))
        if tot is not None and tot > 0:
            self.tot.append(tot)
            self.tsum += tot
            self.tsq += tot * tot
            if len(self.tot) > 400:
                x = self.tot.popleft()
                self.tsum -= x
                self.tsq -= x * x

    # -- team trends
    def rel(self, g):
        """'div' / 'conf' / 'nonconf' / None: the context study's schedule call for this pair."""
        f = self.cx_facts.get(g.get("id")) if self.cx_facts else None
        if f is not None:
            return f.get("rel")
        W = self.cx_index.w.get(self.lg) if self.cx_index is not None else None
        if W is not None and g.get("home") and g.get("start"):
            return W.sched.rel(g["home"], g["away"], scx.season(self.lg, g["start"]))
        return None

    def prime(self, g):
        """A prime-time football slot (Thursday / Sunday / Monday night) by sports_trends' slot rules."""
        return self.lg in FOOTBALL and strn.tags(g, self.lg)[0] in PRIME

    def learn_trends(self, g, t, hs, as_, neutral):
        """A final's result goes into both teams' running trend records (called 6h+ after its start, like apply)."""
        se = scx.season(self.lg, g["start"])
        line, tot = _num(g.get("spread_home")), _num(g.get("total"))
        lh, la = _ints(g.get("ls_home")), _ints(g.get("ls_away"))
        prime, div = self.prime(g), self.lg in DIV_LEAGUES and self.rel(g) == "div"
        for side in ("home", "away"):
            r = self.tt.setdefault(g[side], {"last": None, "ats": 0, "ats_s": (None, 0, 0), "road": deque(),
                                             "pt": deque(), "div": deque(), "q1": deque(maxlen=Q1_LAST), "ou": 0})
            if r["last"] is not None and t - r["last"] > SEASON_GAP_D * 86400:
                r["ats"], r["ou"] = 0, 0                  # a new season: streaks and recent form start over
                r["q1"].clear()
            r["last"] = t
            m = hs - as_ if side == "home" else as_ - hs
            if self.lg in SPREAD_CUTS and line is not None:
                c = m + (line if side == "home" else -line)
                if c:                                     # (a push neither extends nor breaks anything)
                    cov = c > 0
                    r["ats"] = (max(0, r["ats"]) + 1) if cov else (min(0, r["ats"]) - 1)
                    s0, w0, n0 = r["ats_s"]
                    r["ats_s"] = (se, w0 + cov, n0 + 1) if s0 == se else (se, int(cov), 1)
                    if side == "away" and not neutral:
                        r["road"].append((t, cov))
                    while r["road"] and r["road"][0][0] < t - ROAD_ATS_D * 86400:
                        r["road"].popleft()
            if m and prime:
                r["pt"].append((se, m > 0))
            if m and div:
                r["div"].append((se, m > 0))
            for key in ("pt", "div"):
                while r[key] and r[key][0][0] < se - 1:
                    r[key].popleft()
            if lh and la:
                d = lh[0] - la[0] if side == "home" else la[0] - lh[0]
                r["q1"].append((d > 0) - (d < 0))
            if tot is not None and tot > 0 and hs + as_ != tot:
                ov = hs + as_ > tot
                r["ou"] = (max(0, r["ou"]) + 1) if ov else (min(0, r["ou"]) - 1)

    def team_trends(self, g, side, t):
        """The team-trend atoms for one team going into this game (see the top). Only finals learned so far count."""
        r = self.tt.get(g[side])
        if not r:
            return []
        out = []
        se = scx.season(self.lg, g["start"])
        fresh = r["last"] is not None and t - r["last"] <= SEASON_GAP_D * 86400
        if self.lg in SPREAD_CUTS:
            a = r["ats"] if fresh else 0
            if a >= ATS_SHORT:
                out += ["ats:w3"] + (["ats:w5"] if a >= ATS_LONG else [])
            elif a <= -ATS_SHORT:
                out += ["ats:l3"] + (["ats:l5"] if a <= -ATS_LONG else [])
            s0, w0, n0 = r["ats_s"]
            if s0 == se and n0 >= ATS_RATE_N:
                out += ["atsr:hi"] if w0 / n0 >= RATE_HI else ["atsr:lo"] if w0 / n0 <= RATE_LO else []
            if side == "away" and str(g.get("neutral")) != "1":
                rd = [c for x, c in r["road"] if x >= t - ROAD_ATS_D * 86400]
                if len(rd) >= ROAD_ATS_N:
                    x = sum(rd) / len(rd)
                    out += ["rats:hi"] if x >= RATE_HI else ["rats:lo"] if x <= RATE_LO else []
        for key, hi, lo, on in (("pt", "pt:strong", "pt:poor", self.prime(g)),
                                ("div", "divr:hi", "divr:lo", self.lg in DIV_LEAGUES and self.rel(g) == "div")):
            if not on:
                continue
            rec = [w for s_, w in r[key] if se - 1 <= s_ <= se]
            if len(rec) >= REC_N:
                x = sum(rec) / len(rec)
                out += [hi] if x >= REC_HI else [lo] if x <= REC_LO else []
        if fresh and len(r["q1"]) == Q1_LAST:
            if sum(1 for x in r["q1"] if x > 0) >= Q1_NEED:
                out.append("q1:won")
            elif sum(1 for x in r["q1"] if x < 0) >= Q1_NEED:
                out.append("q1:lost")
        if fresh and r["ou"] >= OU_STREAK:
            out.append("ou:o4")
        elif fresh and r["ou"] <= -OU_STREAK:
            out.append("ou:u4")
        return out

    # -- atoms
    def game_level(self, g, t):
        """Facts about the game itself (both teams share them)."""
        out = []
        et = datetime.fromtimestamp(t, ET)
        out.append(DOW[et.weekday()])
        if et.hour >= 18:
            out.append("night")
        elif et.hour < 17:
            out.append("day")
        i = bisect.bisect_right(self.s_start, t) - 1
        if i >= 0 and self.s_len[i] > 0:
            f = (t - self.s_start[i]) / self.s_len[i]
            out.append("early" if f < 0.10 else "late" if f >= 0.80 else "mid")
        if str(g.get("stype")) == "3":
            out.append("playoff")
        elev = _num(g.get("elev"))
        if elev is not None and elev >= sm.THIN_AIR_M:
            out.append("alt")
        temp = _num(g.get("wx_temp"))
        if str(g.get("indoor")) == "0" and temp is not None:
            if temp < 40:
                out.append("cold")
            if (_num(g.get("wx_wind")) or 0) >= 15:
                out.append("wind")
            if (_num(g.get("wx_rain")) or 0) >= 0.2:
                out.append("rain")
        tot, n = _num(g.get("total")), len(self.tot)
        if tot is not None and tot > 0 and n >= 100:
            mu = self.tsum / n
            sd_ = math.sqrt(max(1e-9, self.tsq / n - mu * mu))
            if tot <= mu - 0.67 * sd_:
                out.append("tot:low")
            elif tot >= mu + 0.67 * sd_:
                out.append("tot:high")
        return out

    def team(self, g, side, t):
        """Facts about one team going in: rest, streak, last game, revenge, road trip, time zones crossed."""
        tm, opp = g[side], g["away" if side == "home" else "home"]
        r = self.teams.get(tm)
        neutral = str(g.get("neutral")) == "1"
        out = []
        if r and r["last"] is not None and t - r["last"] <= SEASON_GAP_D * 86400:
            gap = (t - r["last"]) / 86400
            if self.lg in FOOTBALL:
                out.append("rest:short" if gap < 5.5 else "rest:7" if gap < 9.5 else "rest:long")
            else:
                out.append("rest:b2b" if gap < 1.5 else "rest:1" if gap < 2.5 else "rest:2-3" if gap < 4.5 else "rest:4+")
            if r["streak"] >= 3:
                out.append("w3")
            elif r["streak"] <= -3:
                out.append("l3")
            if r["blow"]:
                out.append("blow" + r["blow"])
            if not neutral and side == "away" and r["road"] >= 2:
                out.append("road3")
            if not neutral and side == "home" and r["road"] >= 3:
                out.append("homecoming")
        if r:
            vs = r["vs"].get(opp)
            if vs and t - vs[0] <= MEET_D * 86400 and not vs[1]:
                out.append("revenge")
        tzo, home_tz = _num(g.get("tzo")), self.tz.get(tm)
        if tzo is not None and home_tz is not None:
            d = _std_tz(tzo, t) - home_tz
            out.append("tz:0" if abs(d) < 0.5 else "tz:1" if abs(d) < 1.5 else "tz:2+E" if d > 0 else "tz:2+W")
        return out

    def cx(self, g):
        """The context study's facts for this game (walked forward in build, or from the index for upcoming games)."""
        f = self.cx_facts.get(g.get("id")) if self.cx_facts else None
        if f is None and self.cx_index is not None:
            f = self.cx_index.facts(g)
        return f or {}

    def side_atoms(self, g, side, t, base=None):
        """Everything true for betting `side` of this game (the moneyline / spread table)."""
        other = "away" if side == "home" else "home"
        out = list(self.game_level(g, t) if base is None else base)
        ga, mine, theirs = scx.atoms(self.cx(g), side)
        out += ga + mine + ["o" + a for a in theirs if a.startswith(CX_OPP)]
        out.append("neutral" if str(g.get("neutral")) == "1" else side.replace("away", "road"))
        mine = self.team(g, side, t)
        out += mine
        out += self.team_trends(g, side, t) + ["o" + a for a in self.team_trends(g, other, t)]
        for a in self.team(g, other, t):
            if a.startswith(("rest:", "w3", "l3", "blow")):
                out.append("o" + a)
            elif a == "revenge":
                out.append("orevenge")
        p = sm.market_p(g)
        if p is not None:
            ps = p if side == "home" else 1 - p
            if ps != 0.5:
                out.append("fav" if ps > 0.5 else "dog")
            out.append(next(name for lo, name in PRICE if ps >= lo))
            po = sm.market_p(g, open_line=True)
            opened = (_odds(g.get("ml_home_open")), _odds(g.get("ml_away_open")))
            if po is not None and opened != (_odds(g.get("ml_home")), _odds(g.get("ml_away"))):
                d = sm.logit(p) - sm.logit(po)
                d = d if side == "home" else -d
                if abs(d) >= 0.01:
                    out.append("mv:to" if d > 0 else "mv:away")
        line = _num(g.get("spread_home"))
        if self.lg in SPREAD_CUTS and line is not None:
            lo, hi = SPREAD_CUTS[self.lg]
            L = line if side == "home" else -line
            out.append("sp:bigfav" if L <= -hi else "sp:fav" if L <= -lo else "sp:pk" if L < lo
                       else "sp:dog" if L < hi else "sp:bigdog")
        return sorted(set(out))

    def game_atoms(self, g, t, base=None):
        """Everything true about the game (the over/under table): game facts + each team's facts (h. / a.)."""
        out = list(self.game_level(g, t) if base is None else base)
        if str(g.get("neutral")) == "1":
            out.append("neutral")
        ga, hx, ax = scx.atoms(self.cx(g), "home")
        out += ga + ["h." + a for a in hx] + ["a." + a for a in ax]
        out += ["h." + a for a in self.team(g, "home", t)]
        out += ["a." + a for a in self.team(g, "away", t)]
        out += ["h." + a for a in self.team_trends(g, "home", t)]
        out += ["a." + a for a in self.team_trends(g, "away", t)]
        p = sm.market_p(g)
        if p is not None and p != 0.5:
            out.append("h.fav" if p > 0.5 else "h.dog")
        line = _num(g.get("spread_home"))
        if self.lg in SPREAD_CUTS and line is not None:
            lo, hi = SPREAD_CUTS[self.lg]
            if abs(line) >= hi:
                out.append("sp:big")
            elif abs(line) < lo:
                out.append("sp:close")
        return sorted(set(out))


# ---------------------------------------------------------------- tables (one pass per league)
class Table:
    """Rows sorted by start; each atom and each bet's 'gradable' rows are bitsets over those rows."""

    def __init__(self, outcomes):
        self.starts, self.rows_atoms = [], []
        self.vals = {o: [] for o in outcomes}

    def add(self, start, atoms, vals):
        self.starts.append(start)
        self.rows_atoms.append(atoms)
        for o, v in vals.items():
            self.vals[o].append(v)

    def seal(self):
        n = len(self.starts)
        idx = {}
        for i, atoms in enumerate(self.rows_atoms):
            for a in atoms:
                idx.setdefault(a, []).append(i)
        self.atoms = {a: _bits(v, n) for a, v in idx.items()}
        self.valid = {o: _bits([i for i, v in enumerate(vs) if v is not None], n) for o, vs in self.vals.items()}
        del self.rows_atoms
        return self

    def mask(self, atoms, outcome):
        m = self.valid.get(outcome, 0)
        for a in atoms:
            m &= self.atoms.get(a, 0)
        return m

    def upto(self, cutoff):
        """Bits of the rows that started at or before the cutoff."""
        return (1 << bisect.bisect_right(self.starts, cutoff)) - 1


def _grade_side(g, side, league):
    hs, as_ = int(g["home_score"]), int(g["away_score"])
    out = {"ml": None, "spread": None}
    oh, oa = _odds(g.get("ml_home")), _odds(g.get("ml_away"))
    if oh and oa and hs != as_:
        won = (hs > as_) == (side == "home")
        fh = sd.no_vig(oh, oa)
        out["ml"] = (won, fh if side == "home" else 1 - fh, units(oh if side == "home" else oa, won))
    line = _num(g.get("spread_home"))
    if league in SPREAD_CUTS and line is not None:
        margin = (hs - as_ + line) if side == "home" else (as_ - hs - line)
        if margin != 0:
            sh, sa = _odds(g.get("spread_home_odds")) or -110, _odds(g.get("spread_away_odds")) or -110
            fh = sd.no_vig(sh, sa)
            out["spread"] = (margin > 0, fh if side == "home" else 1 - fh, units(sh if side == "home" else sa, margin > 0))
    return out


def _two_sided(a, b):
    """Two prices that can be the two sides of one real market: the book's margin between 0 and 15%. Part of the
    stored first-part history (most of MLB 2025) pairs prices of DIFFERENT lines (e.g. +310 / +175 on a -1.5) -
    grading those would be grading made-up prices, so they're no bet."""
    return VIG_OK[0] <= sd.implied(a) + sd.implied(b) <= VIG_OK[1]


def _grade_p1(g, side, league):
    """The first-part bets (college hoops' 1st half, baseball's first 5 innings) at their REAL closing prices - None
    when the data lacks the period scores or the line (no price is ever made up). A tie is no bet on the moneyline."""
    out = {"p1ml": None, "p1spread": None}
    k = P1.get(league)
    lh, la = _ints(g.get("ls_home")), _ints(g.get("ls_away"))
    if not k or len(lh) < k or len(la) < k:
        return out
    m = sum(lh[:k]) - sum(la[:k])
    oh, oa = _odds(g.get("h1_ml_home")), _odds(g.get("h1_ml_away"))
    if oh and oa and m and _two_sided(oh, oa):
        won = (m > 0) == (side == "home")
        fh = sd.no_vig(oh, oa)
        out["p1ml"] = (won, fh if side == "home" else 1 - fh, units(oh if side == "home" else oa, won))
    line = _num(g.get("h1_spread_home"))
    sh, sa = _odds(g.get("h1_spread_home_odds")), _odds(g.get("h1_spread_away_odds"))
    if line is not None and sh and sa and _two_sided(sh, sa):
        c = (m + line) if side == "home" else (-m - line)
        if c:
            fh = sd.no_vig(sh, sa)
            out["p1spread"] = (c > 0, fh if side == "home" else 1 - fh, units(sh if side == "home" else sa, c > 0))
    return out


def _grade_total(g):
    tot = _num(g.get("total"))
    if tot is None or tot <= 0:
        return {"over": None, "under": None}
    pts = int(g["home_score"]) + int(g["away_score"])
    if pts == tot:
        return {"over": None, "under": None}
    oo, uo = _odds(g.get("over_odds")) or -110, _odds(g.get("under_odds")) or -110
    fo = sd.no_vig(oo, uo)
    over = pts > tot
    return {"over": (over, fo, units(oo, over)), "under": (not over, 1 - fo, units(uo, not over))}


def build(games, league):
    """(League state after every final, side table, game table) for one league."""
    L = League(league, games)
    L.cx_facts = scx.facts_table(games, league, scx.load_officials())
    side, game = Table(("ml", "spread", "p1ml", "p1spread")), Table(("over", "under"))
    for g in sm.finals(games, league):
        t = sm._ts(g["start"])
        L.advance(t)
        try:
            int(g["home_score"]), int(g["away_score"])
        except (TypeError, ValueError):
            continue
        base = L.game_level(g, t)
        for s in ("home", "away"):
            side.add(g["start"], L.side_atoms(g, s, t, base), {**_grade_side(g, s, league), **_grade_p1(g, s, league)})
        game.add(g["start"], L.game_atoms(g, t, base), _grade_total(g))
        L.pending.append((t, g))
    return L, side.seal(), game.seal()


def index(games):
    """{league: what the engine knows going into the next game} - feed it to atoms_for / game_atoms_for."""
    out = {}
    cx = scx.Index(games)
    for lg in LEAGUES:
        L = League(lg, games)
        L.cx_index = cx
        for g in sm.finals(games, lg):
            L.advance(sm._ts(g["start"]))
            L.pending.append((sm._ts(g["start"]), g))
        L.flush()
        out[lg] = L
    return out


def atoms_for(games, g, side, idx=None):
    """The atoms for betting `side` ('home'/'away') of a game (upcoming or not) - for adjust_side."""
    L = (idx or index(games)).get(g["league"])
    return L.side_atoms(g, side, sm._ts(g["start"])) if L else []


def game_atoms_for(games, g, idx=None):
    """The game atoms of a game - for adjust_total."""
    L = (idx or index(games)).get(g["league"])
    return L.game_atoms(g, sm._ts(g["start"])) if L else []


# ---------------------------------------------------------------- 2) grading
def grade(tbl, outcome, mask):
    """Stats for the rows in the mask: bets, profit, roi, z of the profit, edge over the fair price, halves."""
    rows = [tbl.vals[outcome][i] for i in _ones(mask)]
    n = len(rows)
    if not n:
        return {"n": 0}
    P = [u for _, _, u in rows]
    E = [w - f for w, f, _ in rows]
    h = n // 2
    a, b = P[:h], P[h:]
    return {"n": n, "profit": round(sum(P), 2), "roi": round(sum(P) / n, 4), "z": round(zscore(P), 2),
            "win": round(sum(w for w, _, _ in rows) / n, 4), "fair": round(sum(f for _, f, _ in rows) / n, 4),
            "edge": round(sum(E) / n, 4), "z_edge": round(zscore(E), 2),
            "n_old": len(a), "roi_old": round(sum(a) / len(a), 4) if a else 0.0,
            "n_new": len(b), "roi_new": round(sum(b) / len(b), 4) if b else 0.0,
            "from": tbl.starts[_ones(mask & -mask)[0]][:10] if mask else ""}


def is_suspect(s):
    return s.get("n", 0) >= MIN_N and s["roi_old"] > 0 and s["roi_new"] > 0 and s["z"] >= Z_SUSPECT


def shift_of(fwd):
    """The logit nudge a proven angle earns: its FORWARD edge only, shrunk by n / (n + 400)."""
    n, f, e = fwd.get("n", 0), fwd.get("fair"), fwd.get("edge")
    if not n or f is None or e is None:
        return 0.0
    return round((sm.logit(min(0.99, max(0.01, f + e))) - sm.logit(f)) * n / (n + SHRINK), 4)


# ---------------------------------------------------------------- the team-trend families, pooled (the direct answer)
FAMILIES = (   # (name, atom that says "back this team", atom that says "fade this team", markets)
    ("team ATS streak 3+", "ats:w3", "ats:l3", ("spread",)),
    ("team ATS streak 5+", "ats:w5", "ats:l5", ("spread",)),
    ("season ATS rate", "atsr:hi", "atsr:lo", ("spread",)),
    ("road ATS rate", "rats:hi", "rats:lo", ("spread",)),
    ("prime-time record", "pt:strong", "pt:poor", ("ml", "spread")),
    ("division record", "divr:hi", "divr:lo", ("ml", "spread")),
    ("1st-quarter form", "q1:won", "q1:lost", ("p1ml", "p1spread", "ml", "spread")),
)


def _follow_side(tbl, out, up, down):
    """[(start, follow bet, fade bet)]: following = backing a team flagged `up` / betting against one flagged `down`.
    Side rows come in pairs (home 2k, away 2k+1); a game where the trend points both ways is dropped, one where both
    teams point the same way counts once."""
    bets = set(_ones(tbl.atoms.get(up, 0))) | {i ^ 1 for i in _ones(tbl.atoms.get(down, 0))}
    vs = tbl.vals[out]
    return [(tbl.starts[i], vs[i], vs[i ^ 1]) for i in sorted(bets)
            if i ^ 1 not in bets and vs[i] is not None and vs[i ^ 1] is not None]


def _follow_total(tbl):
    """[(start, follow bet, fade bet)]: either team's 4+ overs in a row says over, 4+ unders says under."""
    o = _ones(tbl.atoms.get("h.ou:o4", 0) | tbl.atoms.get("a.ou:o4", 0))
    u = _ones(tbl.atoms.get("h.ou:u4", 0) | tbl.atoms.get("a.ou:u4", 0))
    both = set(o) & set(u)
    out = []
    for rows, a, b in ((o, "over", "under"), (u, "under", "over")):
        for i in rows:
            if i not in both and tbl.vals[a][i] is not None:
                out.append((tbl.starts[i], tbl.vals[a][i], tbl.vals[b][i]))
    return out


def family_cell(rows):
    """Follow vs fade on the same bets: hit rate, the price's fair chance, ROI at the real price, both time halves,
    the explorer's z (on the profit) and the edge z (hit minus the no-vig chance). Pass = the explorer's bar."""
    rows = sorted(rows, key=lambda r: r[0])
    n = len(rows)
    out = {"n": n, "from": rows[0][0][:10] if rows else None, "to": rows[-1][0][:10] if rows else None}
    if not n:
        return out
    h = n // 2
    for name, k in (("follow", 1), ("fade", 2)):
        bets = [r[k] for r in rows]

        def part(bs):
            m = len(bs)
            return {"n": m, "hit": round(sum(w for w, _, _ in bs) / m, 4) if m else 0.0,
                    "roi": round(sum(u for _, _, u in bs) / m, 4) if m else 0.0}
        var = sum(f * (1 - f) for _, f, _ in bets)
        c = {**part(bets), "fair": round(sum(f for _, f, _ in bets) / n, 4), "z": round(zscore([u for _, _, u in bets]), 2),
             "z_edge": round(sum(w - f for w, f, _ in bets) / math.sqrt(var), 2) if var else 0.0,
             "old": part(bets[:h]), "new": part(bets[h:])}
        c["passes"] = n >= MIN_N and c["old"]["roi"] > 0 and c["new"]["roi"] > 0 and c["z"] >= Z_SUSPECT
        out[name] = c
    return out


def family_tests(tables):
    """tables = {league: (side table, game table)} -> {family|market: pooled cell, family|market|league: cell}."""
    pools = {}
    for lg, (side, game) in tables.items():
        for name, up, down, markets in FAMILIES:
            for out in markets:
                if side.valid.get(out):
                    rows = _follow_side(side, out, up, down)
                    if rows:
                        pools.setdefault(f"{name}|{out}", []).extend(rows)
                        pools.setdefault(f"{name}|{out}|{lg}", []).extend(rows)
        rows = _follow_total(game)
        if rows:
            pools.setdefault("O/U streak 4+|total", []).extend(rows)
            pools.setdefault(f"O/U streak 4+|total|{lg}", []).extend(rows)
    return {k: family_cell(v) for k, v in sorted(pools.items())}


def family_lines(fams):
    lines = ["   TEAM TRENDS pooled across sports (all games so far; 'follow' = ride the trend, 'fade' = bet against it;"
             f" the bar: {MIN_N}+ bets, profit in both halves, z {Z_SUSPECT}+):"]
    for k, c in fams.items():
        if k.count("|") != 1 or not c.get("n"):
            continue
        f, d = c["follow"], c["fade"]
        verdict = "FOLLOW passes the bar" if f["passes"] else "FADE passes the bar" if d["passes"] else "no edge"
        lines.append(f"   {k}: n={c['n']} ({c['from']}..{c['to']}) follow hit {f['old']['hit']:.1%} older / "
                     f"{f['new']['hit']:.1%} newer (fair {f['fair']:.1%}, roi {f['old']['roi']:+.3f} / {f['new']['roi']:+.3f},"
                     f" z {f['z']}, edge z {f['z_edge']}) · fade hit {d['old']['hit']:.1%} / {d['new']['hit']:.1%}"
                     f" (roi {d['old']['roi']:+.3f} / {d['new']['roi']:+.3f}, z {d['z']}) -> {verdict}")
    return lines


# ---------------------------------------------------------------- 3) enumeration (simple -> complex)
class Group:
    """One league x bet: its atoms (sorted, with 300+ gradable rows) and the combos worth testing."""

    def __init__(self, league, outcome, tbl):
        self.lg, self.out, self.tbl = league, outcome, tbl
        self.V = tbl.valid.get(outcome, 0)
        self.names, self.bits, self.n, self.fam = [], [], [], []
        for a in sorted(tbl.atoms):
            m = tbl.atoms[a] & self.V
            c = m.bit_count()
            if c >= MIN_N and c < self.V.bit_count():        # an atom true for every row says nothing
                self.names.append(a)
                self.bits.append(m)
                self.n.append(c)
                self.fam.append(family(a))
        self._pairs = None

    def key(self, ii):
        return key_of(self.lg, self.out, [self.names[i] for i in ii])

    def pairs(self):
        if self._pairs is None:
            self._pairs = {}
            k = len(self.names)
            for i in range(k):
                for j in range(i + 1, k):
                    if self.fam[i] == self.fam[j]:
                        continue
                    c = (self.bits[i] & self.bits[j]).bit_count()
                    if c >= MIN_N and c != self.n[i] and c != self.n[j]:
                        self._pairs[(i, j)] = c
        return self._pairs

    def cands(self, level, seen):
        """(key, atoms, mask) of every untested combo of `level` atoms, in a fixed order."""
        k = len(self.names)
        if level == 1:
            for i in range(k):
                key = self.key((i,))
                if _h(key) not in seen:
                    yield key, (self.names[i],), self.bits[i]
        elif level == 2:
            for (i, j) in sorted(self.pairs()):
                key = self.key((i, j))
                if _h(key) not in seen:
                    yield key, (self.names[i], self.names[j]), self.bits[i] & self.bits[j]
        else:
            pc = self.pairs()
            for (i, j) in sorted(pc):
                for m in range(j + 1, k):
                    if (i, m) not in pc or (j, m) not in pc:
                        continue
                    key = self.key((i, j, m))
                    if _h(key) in seen:
                        continue
                    mask = self.bits[i] & self.bits[j] & self.bits[m]
                    c = mask.bit_count()
                    if c < MIN_N or c in (pc[(i, j)], pc[(i, m)], pc[(j, m)]):
                        continue
                    yield key, (self.names[i], self.names[j], self.names[m]), mask


def _round_robin(gens):
    gens = list(gens)
    while gens:
        alive = []
        for g in gens:
            try:
                yield next(g)
                alive.append(g)
            except StopIteration:
                pass
        gens = alive


# ---------------------------------------------------------------- registry
def load(path=None):
    try:
        with open(path or PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _seen(st):
    raw = base64.b64decode(st.get("seen", "") or b"")
    return {raw[i:i + HASH_B] for i in range(0, len(raw), HASH_B)}


def _save(st, seen, path):
    st["seen"] = base64.b64encode(b"".join(sorted(seen))).decode()
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)


def _brief(key, e):
    d, f = e.get("disc", {}), e.get("fwd", {})
    return (f"{key}: found n={d.get('n')} roi {d.get('roi_old', 0):+.3f} then {d.get('roi_new', 0):+.3f} z={d.get('z')}"
            f" | forward n={f.get('n', 0)} roi {f.get('roi', 0):+.3f} edge z={f.get('z_edge', 0)}")


# ---------------------------------------------------------------- the run
def explore(games, path=PATH, batch=BATCH, budget_s=BUDGET_S, leagues=LEAGUES, verbose=True, dog_batch=None):
    """One study run: re-check the suspects + proven angles on forward games, then test the next batch of new ones."""
    t0 = time.time()
    dog_batch = DOG_BATCH if dog_batch is None else dog_batch
    st = load(path)
    seen = _seen(st)
    for k in ("suspects", "proven", "killed"):
        st.setdefault(k, {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    groups, newest, tables = {}, {}, {}
    for lg in leagues:
        _, side, game = build(games, lg)
        tables[lg] = (side, game)
        if side.starts:
            newest[lg] = side.starts[-1]
        for out, tbl in (("ml", side), ("spread", side), ("p1ml", side), ("p1spread", side), ("over", game),
                         ("under", game)):
            if tbl.valid.get(out, 0):
                groups[(lg, out)] = Group(lg, out, tbl)
    # -- re-check every suspect and proven angle on its FORWARD games only
    promoted, killed, demoted = [], [], []
    for status in ("suspects", "proven"):
        for key, e in list(st[status].items()):
            grp = groups.get((e["league"], e["outcome"]))
            if not grp:
                continue
            tbl = grp.tbl
            f = grade(tbl, e["outcome"], tbl.mask(e["atoms"], e["outcome"]) & ~tbl.upto(e["cutoff"]))
            e["fwd"], e["checked"] = f, now
            if f.get("n", 0) < FWD_N:
                continue
            if f["profit"] <= 0:
                e["why"] = "forward games lost money" if status == "suspects" else "turned negative after being proven"
                e["killed"] = now
                st["killed"][key] = st[status].pop(key)
                (killed if status == "suspects" else demoted).append(key)
            elif status == "suspects" and f["z_edge"] >= FWD_Z:
                e["promoted"], e["shift"] = now, shift_of(f)
                st["proven"][key] = st[status].pop(key)
                promoted.append(key)
            elif status == "proven":
                e["shift"] = shift_of(f)
    # -- test the next batch of never-tested angles on the games so far (the discovery games)
    del LAST_TESTED[:]
    found, tested, near = [], 0, []
    exhausted = True

    def test(key, atoms, mask):
        lg, out = key.split("|")[:2]
        s = grade(groups[(lg, out)].tbl, out, mask)
        seen.add(_h(key))
        LAST_TESTED.append(key)
        if is_suspect(s):
            st["suspects"][key] = {"league": lg, "outcome": out, "atoms": list(atoms), "cutoff": newest[lg],
                                   "found": now, "disc": s, "fwd": {}}
            found.append(key)
        elif s["n"] >= MIN_N and s["roi_old"] > 0 and s["roi_new"] > 0:
            near.append((s["z"], key, s))
    # 🐶 the underdog lane first (the owner, 9/30: "we gotta find a way for the engine to pick out these underdogs"):
    # up to DOG_BATCH never-tested MONEYLINE angles where the team is the dog - same strict proof as everything else
    dogs = 0
    for level in range(1, MAX_LEVEL + 1):
        gens = (grp.cands(level, seen) for (lg_, out_), grp in sorted(groups.items()) if out_ == "ml")
        for key, atoms, mask in _round_robin(gens):
            if dogs >= dog_batch or time.time() - t0 > budget_s / 2:
                break
            if not any(a in DOG_ATOMS for a in atoms):
                continue
            test(key, atoms, mask)
            dogs += 1
            tested += 1
        else:
            continue
        break
    for level in range(1, MAX_LEVEL + 1):
        gens = (grp.cands(level, seen) for _, grp in sorted(groups.items()))
        for key, atoms, mask in _round_robin(gens):
            if tested >= batch + dogs or time.time() - t0 > budget_s:
                exhausted = False
                break
            test(key, atoms, mask)
            tested += 1
        else:
            continue
        break
    near.sort(reverse=True)
    run = {"at": now, "tested": tested, "dog_angles": dogs, "suspects_found": len(found), "promoted": len(promoted),
           "killed": len(killed), "demoted": len(demoted), "expected_by_luck": round(tested * P_LUCK, 2),
           "secs": round(time.time() - t0, 1), "exhausted": exhausted}
    st["tested"] = st.get("tested", 0) + tested
    st["runs"] = st.get("runs", 0) + 1
    st["closest"] = [{"key": k, "z": z, "n": s["n"], "roi_old": s["roi_old"], "roi_new": s["roi_new"]}
                     for z, k, s in near[:10]] or st.get("closest", [])
    st["log"] = [run] + st.get("log", [])[:29]
    st["updated"] = now
    st["team_trends"] = family_tests(tables)
    _save(st, seen, path)
    res = {**run, "tested_total": st["tested"], "suspects": sorted(st["suspects"]), "proven": sorted(st["proven"]),
           "new_suspects": found, "new_proven": promoted, "new_killed": killed + demoted,
           "team_trends": st["team_trends"]}
    if verbose:
        print(report(res, st))
    return res


def report(res, st):
    lines = [f"THE EXPLORER: tested {res['tested']} NEW angles ({res['tested_total']} ever) in {res['secs']}s"
             f"{' - every angle there is has been tested' if res['exhausted'] else ''}",
             f"   new suspects: {res['suspects_found']} (luck alone would give ~{res['expected_by_luck']})"
             f" · promoted to PROVEN: {res['promoted']} · killed: {res['killed']} · proven demoted: {res['demoted']}",
             f"   now watching {len(st['suspects'])} suspects · {len(st['proven'])} proven · {len(st['killed'])} killed"]
    for k in res["new_suspects"]:
        lines.append("   NEW SUSPECT " + _brief(k, st["suspects"][k]))
    for k in res["new_proven"]:
        lines.append("   PROVEN " + _brief(k, st["proven"][k]))
    for k in res["new_killed"]:
        lines.append("   KILLED " + _brief(k, st["killed"][k]))
    lines += family_lines(res.get("team_trends") or {})
    return "\n".join(lines)


# ---------------------------------------------------------------- 4) hooks for the engine
def proven(st):
    """Every proven angle: [{key, league, outcome, atoms, shift, fwd...}]."""
    return [{"key": k, **e} for k, e in sorted(((st or {}).get("proven") or {}).items())]


def _best(st, league, outcome, atoms):
    have = set(atoms)
    best = 0.0
    for e in ((st or {}).get("proven") or {}).values():
        if e.get("league") == league and e.get("outcome") == outcome and set(e.get("atoms", [])) <= have:
            s = e.get("shift", 0.0)
            best = s if abs(s) > abs(best) else best         # the strongest match only (angles overlap)
    return best


def adjust_side(st, league, atoms, p, market="ml"):
    """The win (market='ml') or cover (market='spread') chance for a side, nudged by its best-matching proven angle."""
    s = _best(st, league, market, atoms)
    return p if not s else sm.sigmoid(sm.logit(p) + s)


def adjust_total(st, league, game_atoms, p_over):
    """The over chance, nudged up by the best proven over angle and down by the best proven under angle."""
    s = _best(st, league, "over", game_atoms) - _best(st, league, "under", game_atoms)
    return p_over if not s else sm.sigmoid(sm.logit(p_over) + s)


if __name__ == "__main__":
    r = explore(sd.load_games())
    st = load()
    for k, e in sorted(st.get("suspects", {}).items()):
        print("   suspect", _brief(k, e))
    for k, e in sorted(st.get("proven", {}).items()):
        print("   proven ", _brief(k, e), "shift", e.get("shift"))
    for c in st.get("closest", [])[:5]:
        print("   closest miss this run:", c)
