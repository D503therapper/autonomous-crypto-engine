"""🎾 THE TENNIS EDGE STUDY: are the books really softer on tennis - and if so, where, and can we get the price?

Data: data/sports/tennis/hist_odds.csv.gz (tools/fetch_tennis_odds.py): every ATP + WTA tour-level match since 2012
with the closing prices from Pinnacle (the sharpest book), Bet365, and the average / best price across books.
Walkovers are void; a retirement stands for the player who advanced once a set was finished (void before that).
Every chance is NO-VIG (the book's margin taken out). Every test is split by time at one fixed date (the median date
the first time the study ran, saved so it never moves): the OLDER half and the NEWER half.
PROVEN = 300+ bets, a profit at the real price in BOTH halves, and a z of 3.5+ on the edge over the no-vig price of
the book the bet is placed at (the result minus that book's fair chance - for a Pinnacle bet that's Pinnacle's
fair price; for a Bet365 bet it's Bet365's own fair price, so a soft book that's too generous shows up as an edge).
One extra guard: the profit itself must have a z of 2+ (a soft book's fair price can be wrong by less than its
margin - a big edge z with no real money in it).

1) IS TENNIS SOFTER? The market's accuracy by segment: ATP vs WTA, Slams / 1000s / 500s / 250s, round, surface,
   early / mid / late season, ranking gap, price bucket (the favorite-longshot bias). Log loss of Pinnacle vs Bet365
   vs the average (same matches), the margin each book charges, how far Bet365 strays from Pinnacle, and whether a
   recalibration learned on the older half makes the newer half more accurate (= a bias that lasted).
2) LINE SHOPPING: how often Bet365 / the average / the best price beats Pinnacle's fair price, and the money from
   betting only those (at THAT book's price). Plus our own Bovada closing lines (few, reported as they are).
3) MODEL VS MARKET: a walk-forward surface-blended Elo (only earlier matches), with fatigue (games played the last
   3 days - minutes aren't in the data), retirement / withdrawal history, a mid-season layoff, and best-of-5 handled
   through the per-set chance. Does blending it into Pinnacle's fair price beat Pinnacle alone on the newer half?
   (weights are cross-fit: learned on one half, graded on the other.) Bets where they disagree by 2-12%.
4) ANGLES - a registry like the explorer: facts known before the match (price bucket, level, round, surface, indoor,
   season, best-of-5, rank buckets, qualifier/wildcard proxy, home country, big server on the tiebreak proxy,
   retirement risk, long layoff, just won a title / deep run, first clay/grass match of the year, fatigue, form,
   model disagreement, and the soft-book-vs-Pinnacle price gap) in combos of 1-3, per tour, bet at Pinnacle,
   Bet365 or the average. Every run tests only angles NEVER tested before (fingerprints saved), on the OLDER half
   only: a winner there (150+ bets, profit, edge z 3.5+) becomes a SUSPECT, and must FORWARD-CONFIRM on the newer
   half (100+ bets, profit, edge z 2.0+, and the full proven bar overall) to be PROVEN; a forward loss KILLS it.
   Proven angles are re-checked every run on their forward matches (the newer half keeps growing) and demoted the
   moment they stop making money.
   Plus: 3-set / 5-set frequency vs what the price implies, and game-handicap cover rates by price (for Bovada's
   game spreads).
5) Everything goes to data/sports/tennis/edge.json (runs log capped at 60).

Hooks for sports_tennis: load(), proven(st), adjust(st, match_features, p)."""
import base64
import bisect
import csv
import gzip
import hashlib
import json
import math
import os
import time
import zlib
from collections import Counter, deque
from datetime import date, datetime, timezone

import sports_data as sd
import sports_explorer as ex
import sports_model as sm
import sports_tennis as stn

DIR = os.path.join(sd.DATA, "tennis")
HIST = os.path.join(DIR, "hist_odds.csv.gz")
PATH = os.path.join(DIR, "edge.json")
MATCHES = stn.MATCHES
LINES = stn.LINES

MIN_N, Z_PROVEN = 300, 3.5          # the proof bar
P_LUCK = 0.5 * math.erfc(Z_PROVEN / math.sqrt(2))
Z_MONEY = 2.0                       # ...and the profit at the real price must not be luck either (a soft book's own
                                    # fair price can be off by more than its margin: a big edge z, but tiny money)
DISC_N = 150                        # an angle needs this many older-half bets to be tested at all
FWD_N, FWD_Z = 100, 2.0             # forward (newer half) bets to promote / kill; forward edge z to promote
P_FWD = 0.5 * math.erfc(FWD_Z / math.sqrt(2))
SHRINK = 400
BATCH, BUDGET_S = 4000, 150
MAX_LEVEL = 3
LOG_CAP = 60
KNOWN = 10                          # both players need this many earlier rated matches for the model
BETS = ("pin", "b365", "avg")       # registry: where the bet is placed
BOOKS = ("pin", "b365", "avg", "max")
COLS = {"pin": ("psw", "psl"), "b365": ("b365w", "b365l"), "avg": ("avgw", "avgl"), "max": ("maxw", "maxl")}
OVERROUND = {"pin": (0.99, 1.12), "b365": (0.99, 1.20), "avg": (0.99, 1.20), "max": (0.85, 1.10)}
MAX_GAP = 0.5                       # a "best price" 50%+ above Pinnacle's fair price is a data error, not a price
GETTABLE = {"pin": "Pinnacle closing - the sharp price; not open to US bettors and not Bovada",
            "b365": "Bet365 closing - a real single book (limits winners fast; not open in the US)",
            "avg": "the average across books - NOT a price any book offers (a stand-in for a typical soft book)",
            "max": "the best price across ~40 books - NOT gettable in practice (stale / error quotes, exchanges "
                   "before commission, many accounts needed)"}
PRICE = ((0.80, "p:80+"), (0.65, "p:65-80"), (0.50, "p:50-65"), (0.35, "p:35-50"), (0.20, "p:20-35"), (0.0, "p:<20"))
RND = {"1st Round": ("early", 1), "2nd Round": ("early", 2), "3rd Round": ("mid", 3), "4th Round": ("mid", 4),
       "Quarterfinals": ("qf", 5), "Semifinals": ("sf+", 6), "The Final": ("sf+", 7), "Round Robin": ("rr", 5)}
OUT_CUT = {"slam": 104, "1000": 60, "500": 45, "250": 80}      # ranked beyond the usual direct-entry cut (proxy)
SRV = {"atp": 0.22, "wta": 0.14}    # tiebreak share of a player's recent sets: the big-server proxy
LAYOFF_D, RET_D, FAT_D = 42, 180, 3
LAST_TESTED = []                    # the keys the latest run tested (tests look at it)


# ---------------------------------------------------------------- reading the history
MIN_SEASONS = 24          # of the 30 ATP + WTA season files since 2012 - the first run waits for the history to be in

def _f(x):
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _rank(x):
    v = _f(x)
    return int(v) if v else None


def level(series):
    s = str(series or "").lower()
    if "grand slam" in s:
        return "slam"
    if "masters cup" in s or "championship" in s or "finals" in s:
        return "other"
    if "masters" in s or "1000" in s or "mandatory" in s or "premier 5" in s:
        return "1000"
    if "500" in s or s.strip() == "premier" or "gold" in s:
        return "500"
    if "250" in s or "international" in s:
        return "250"
    return "other"


def _done(a, b):
    return max(a, b) >= 6 and (abs(a - b) >= 2 or max(a, b) == 7)


def _pair(r, book):
    kw, kl = COLS[book]
    a, b = _f(r.get(kw)), _f(r.get(kl))
    if not a or not b or a <= 1.0 or b <= 1.0:
        return None
    lo, hi = OVERROUND[book]
    return (a, b) if lo <= 1 / a + 1 / b <= hi else None


def _nv(a, b):
    ia, ib = 1 / a, 1 / b
    return ia / (ia + ib)


class M:
    """One match (W = the winner, L = the loser)."""
    __slots__ = ("tour", "d", "dn", "tkey", "tourney", "loc", "lvl", "court", "surf", "rnd", "bo", "W", "L", "wr",
                 "lr", "sets", "status", "odds", "fw", "fx")


def read_hist(path=HIST):
    """Every match in the history file, oldest first (walkovers kept - flagged void - for the injury history)."""
    if not os.path.exists(path):
        return []
    with gzip.open(path, "rt", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for i, r in enumerate(rows):
        d = (r.get("date") or "")[:10]
        if len(d) != 10 or not r.get("winner") or not r.get("loser"):
            continue
        m = M()
        m.tour = (r.get("tour") or "atp").lower()
        m.d, m.dn = d, date.fromisoformat(d).toordinal()
        m.tourney, m.loc = r.get("tourney") or "", r.get("location") or ""
        m.tkey = f"{m.tour}|{m.tourney}|{m.loc}"
        m.lvl = level(r.get("series"))
        m.court = "indoor" if str(r.get("court")).lower().startswith("indoor") else "outdoor"
        s = str(r.get("surface") or "hard").lower()
        m.surf = "clay" if "clay" in s else "grass" if "grass" in s else "hard"
        m.rnd = r.get("round") or ""
        bo = _f(r.get("bo"))
        m.bo = 5 if bo == 5 else 3
        m.W, m.L = r["winner"].strip(), r["loser"].strip()
        m.wr, m.lr = _rank(r.get("wrank")), _rank(r.get("lrank"))
        sets = []
        for n in range(1, 6):
            a, b = _f(r.get(f"w{n}")) or 0, _f(r.get(f"l{n}")) or 0
            if r.get(f"w{n}", "") != "" and r.get(f"l{n}", "") != "":
                sets.append((int(a), int(b)))
        m.sets = sets
        c = str(r.get("comment") or "").lower()
        if "walkover" in c or "w/o" in c:
            m.status = "void"
        elif c.startswith("completed") or c == "":
            m.status = "done"
        else:                                             # retired / disqualified / awarded
            m.status = "ret" if any(_done(a, b) for a, b in sets) else "void"
        m.odds = {}
        for b in BOOKS:
            p = _pair(r, b)
            if p:
                m.odds[b] = p
        pin = m.odds.get("pin")
        if "max" in m.odds and pin:                       # a best price way above fair = a data error
            fw = _nv(*pin)
            mw, ml = m.odds["max"]
            if mw * fw - 1 > MAX_GAP or ml * (1 - fw) - 1 > MAX_GAP or mw < pin[0] * 0.95 or ml < pin[1] * 0.95:
                del m.odds["max"]
        m.fw = _nv(*pin) if pin else None
        m.fx = None
        out.append((m.dn, m.tour, i, m))
    out.sort(key=lambda t: t[:3])
    return [t[3] for t in out]


# ---------------------------------------------------------------- countries (home players), from ESPN's history
def _norm(s):
    return stn._norm(s)


def countries(path=MATCHES):
    """({(surname, first initial): country}, {city: venue}) from ESPN's results (only unambiguous names)."""
    if not path or not os.path.exists(path):
        return {}, {}
    names, city = {}, {}
    with open(path) as f:
        for r in csv.DictReader(f):
            for nm, cc in ((r.get("p1_name"), r.get("cc1")), (r.get("p2_name"), r.get("cc2"))):
                t = _norm(nm)
                if not cc or len(t) < 2:
                    continue
                for k in range(1, len(t)):
                    names.setdefault((" ".join(t[k:]), t[0][0]), set()).add(cc)
            v = r.get("venue") or ""
            if "," in v:
                city.setdefault(" ".join(_norm(v.split(",")[0])), Counter())[v] += 1
    return ({k: next(iter(v)) for k, v in names.items() if len(v) == 1},
            {k: c.most_common(1)[0][0] for k, c in city.items()})


def _td_key(name):
    """'Del Potro J.M.' -> ('del potro', 'j')."""
    parts = str(name).split()
    if len(parts) < 2:
        return None
    ini = _norm(parts[-1])
    sur = " ".join(_norm(" ".join(parts[:-1])))
    return (sur, ini[0][0]) if ini and sur else None


def _td_last(name):
    k = _td_key(name)
    return k[0].split()[-1] if k else ""


# ---------------------------------------------------------------- walk-forward player state
class Player:
    __slots__ = ("n", "last", "cur_t", "cur_best", "cur_title", "cur_end", "rets", "last_ret", "recent", "res",
                 "tb", "year", "surfs", "n_year")

    def __init__(self):
        self.n, self.last, self.cur_t, self.cur_best, self.cur_title, self.cur_end = 0, None, None, 0, False, None
        self.rets, self.last_ret = deque(maxlen=12), False
        self.recent, self.res, self.tb = deque(maxlen=6), deque(maxlen=10), deque(maxlen=60)
        self.year, self.surfs, self.n_year = None, set(), 0


class Walk:
    """Surface-blended Elo + everything else a player carries into a match, updated a day at a time."""

    def __init__(self, cc=None, venues=None):
        self.p, self.r = {}, {}
        self.cc, self.venues = cc or {}, venues or {}

    def pl(self, tour, name):
        k = (tour, name)
        if k not in self.p:
            self.p[k] = Player()
        return self.p[k]

    def elo(self, m, a, b):
        """a's win chance vs b: overall + surface Elo blended, converted to best-of-5 when it is."""
        oa, ob = self.r.get((m.tour, a, None), 1500.0), self.r.get((m.tour, b, None), 1500.0)
        sa, sb = self.r.get((m.tour, a, m.surf), 1500.0), self.r.get((m.tour, b, m.surf), 1500.0)
        p = min(max((stn.elo_p(oa, ob) + stn.elo_p(sa, sb)) / 2, 0.01), 0.99)
        return stn.to_bo5(p) if m.bo == 5 else p

    def facts(self, m, name, opp):
        """The facts one player carries into this match (numbers + atoms), from earlier days only."""
        P = self.pl(m.tour, name)
        out = {"n": P.n, "games3": 0, "ret": 0, "lay": 0, "atoms": []}
        A = out["atoms"]
        if P.last is not None:
            gap = m.dn - P.last
            if gap >= LAYOFF_D and date.fromordinal(P.last).year == int(m.d[:4]):
                A.append("lay:long")
                out["lay"] = 1
            g3 = sum(g for dn, g, _ in P.recent if m.dn - FAT_D <= dn < m.dn)
            out["games3"] = g3
            last = P.recent[-1] if P.recent else None
            if g3 >= (60 if m.bo == 5 else 40):
                A.append("fat:heavy")
            elif last and m.dn - last[0] <= 2 and last[2]:
                A.append("fat:dist")
        recent_rets = sum(1 for dn in P.rets if m.dn - dn <= RET_D)
        out["ret"] = min(recent_rets, 2)
        if P.last_ret:
            A.append("ret:last")
        elif recent_rets:
            A.append("ret:recent")
        if P.cur_t is not None and P.cur_t != m.tkey and P.cur_end is not None and m.dn - P.cur_end <= 14:
            if P.cur_title:
                A.append("post:title")
            elif P.cur_best >= 6:
                A.append("post:deep")
        if m.surf in ("clay", "grass") and P.year == int(m.d[:4]) and P.n_year >= 3 and m.surf not in P.surfs:
            A.append("sw:first")
        if len(P.res) == 10:
            w = sum(P.res)
            if w >= 8:
                A.append("form:hot")
            elif w <= 3:
                A.append("form:cold")
        if len(P.tb) >= 30 and sum(P.tb) / len(P.tb) >= SRV.get(m.tour, 0.2):
            A.append("srv:big")
        k = _td_key(name)
        cc = self.cc.get(k) if k else None
        venue = self.venues.get(" ".join(_norm(m.loc)))
        if cc and venue and stn.is_home(cc, venue, m.tourney):
            A.append("home")
        return out

    def update_day(self, day):
        for m in day:
            if m.status == "void":                        # a walkover: the loser pulled out (injury history only)
                P = self.pl(m.tour, m.L)
                P.rets.append(m.dn)
                P.last_ret = True
                continue
            games = sum(a + b for a, b in m.sets)
            dist = len(m.sets) >= m.bo and m.status == "done"
            tb = [1 if max(a, b) == 7 and min(a, b) == 6 else 0 for a, b in m.sets if _done(a, b)]
            info = RND.get(m.rnd, ("?", 1))
            for name, won in ((m.W, 1), (m.L, 0)):
                P = self.pl(m.tour, name)
                if P.cur_t != m.tkey:
                    P.cur_t, P.cur_best, P.cur_title = m.tkey, 0, False
                P.cur_best = max(P.cur_best, info[1])
                P.cur_end = m.dn
                if won and m.rnd == "The Final":
                    P.cur_title = True
                y = int(m.d[:4])
                if P.year != y:
                    P.year, P.surfs, P.n_year = y, set(), 0
                P.surfs.add(m.surf)
                P.n_year += 1
                P.recent.append((m.dn, games, dist))
                P.res.append(won)
                P.tb.extend(tb)
                P.last = m.dn
                P.last_ret = False
                if m.status == "done":
                    P.n += 1
            if m.status == "ret":
                P = self.pl(m.tour, m.L)
                P.rets.append(m.dn)
                P.last_ret = True
            if m.status == "done":                        # Elo learns from finished matches only
                for key in (None, m.surf):
                    a = self.r.get((m.tour, m.W, key), 1500.0)
                    b = self.r.get((m.tour, m.L, key), 1500.0)
                    e = stn.elo_p(a, b)
                    e = stn.to_bo5(e) if m.bo == 5 else e
                    nw, nl = self.p[(m.tour, m.W)].n, self.p[(m.tour, m.L)].n
                    self.r[(m.tour, m.W, key)] = a + stn._k(nw) * (1 - e)
                    self.r[(m.tour, m.L, key)] = b - stn._k(nl) * (1 - e)


def _pbucket(p):
    return next(name for lo, name in PRICE if p >= lo)


def _rk(r):
    return None if not r else "1-10" if r <= 10 else "11-30" if r <= 30 else "31-100" if r <= 100 else "100+"


def side_atoms(m, me, them, rme, rthem, p_me, elo_me, soft):
    """Every fact about betting one side (me) of the match."""
    A = [f"lvl:{m.lvl}", f"surf:{m.surf}", f"court:{m.court}", f"ssn:{_season(m)}"]
    rg = RND.get(m.rnd, (None,))[0]
    if rg:
        A.append(f"rd:{rg}")
    if m.bo == 5:
        A.append("bo5")
    if p_me != 0.5:
        A.append("fav" if p_me > 0.5 else "dog")
    A.append(_pbucket(p_me))
    if _rk(rme):
        A.append("rk:" + _rk(rme))
    if _rk(rthem):
        A.append("ork:" + _rk(rthem))
    if rme and rthem and rme < rthem and p_me < 0.5:
        A.append("rkdog")                                  # better ranked, priced as the underdog
    if rme and m.lvl in OUT_CUT and rme > OUT_CUT[m.lvl]:
        A.append("q:out")
    A += me["atoms"]
    A += ["o" + a for a in them["atoms"]]
    if elo_me is not None:
        d = elo_me - p_me
        if d >= 0.05:
            A.append("mdl:+5")
        elif d <= -0.05:
            A.append("mdl:-5")
    for book, g in soft.items():
        if g is not None:
            A.append(f"g{book}:{'3+' if g >= 0.03 else '0-3' if g > 0 else 'under'}")
    return sorted(set(A))


def _season(m):
    mo = int(m.d[5:7])
    return "early" if mo <= 3 else "mid" if mo <= 7 else "late"


# ---------------------------------------------------------------- stats
class Acc:
    """Running sums for bets, split into the older (0) and newer (1) half."""
    __slots__ = ("s",)

    def __init__(self):
        self.s = [[0.0] * 11 for _ in range(2)]

    def add(self, won, fair_b, profit, fair_pin, new):
        s = self.s[1 if new else 0]
        e, q = won - fair_b, won - fair_pin
        s[0] += 1
        s[1] += profit
        s[2] += profit * profit
        s[3] += e
        s[4] += e * e
        s[5] += q
        s[6] += q * q
        s[7] += won
        s[8] += fair_b
        s[9] += fair_pin

    def out(self, which=None):
        """Stats over both halves (or just 0 / 1)."""
        if which is None:
            s = [a + b for a, b in zip(*self.s)]
        else:
            s = self.s[which]
        n = int(s[0])
        if not n:
            return {"n": 0}

        def z(t, tt):
            if n < 2:
                return 0.0
            mu = t / n
            v = (tt - n * mu * mu) / (n - 1)
            return round(mu / math.sqrt(v / n), 2) if v > 1e-12 else 0.0
        o, w = self.s[0], self.s[1]
        return {"n": n, "roi": round(s[1] / n, 4), "z": z(s[1], s[2]), "win": round(s[7] / n, 4),
                "fair": round(s[8] / n, 4), "edge": round(s[3] / n, 4), "z_edge": z(s[3], s[4]),
                "fair_pin": round(s[9] / n, 4), "edge_pin": round(s[5] / n, 4), "z_pin": z(s[5], s[6]),
                "n_old": int(o[0]), "roi_old": round(o[1] / o[0], 4) if o[0] else 0.0,
                "n_new": int(w[0]), "roi_new": round(w[1] / w[0], 4) if w[0] else 0.0}


def passes(s):
    """The proof bar: 300+ bets, a profit in both halves, edge z 3.5+ - and the money itself not luck (z 2+)."""
    return (s.get("n", 0) >= MIN_N and s.get("n_old", 0) > 0 and s.get("n_new", 0) > 0 and s["roi_old"] > 0
            and s["roi_new"] > 0 and s["z_edge"] >= Z_PROVEN and s["z"] >= Z_MONEY)


def _ll(p, y):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -math.log(p if y else 1 - p)


def _fit2(xs, ys, iters=8):
    """y ~ sigmoid(a + b x): a quick 2-parameter Newton fit (b pulled gently toward 1, a toward 0)."""
    a, b = 0.0, 1.0
    lam = 1.0
    for _ in range(iters):
        ga, gb, haa, hab, hbb = lam * a, lam * (b - 1), lam, 0.0, lam
        for x, y in zip(xs, ys):
            p = sm.sigmoid(a + b * x)
            r, w = p - y, p * (1 - p)
            ga += r
            gb += r * x
            haa += w
            hab += w * x
            hbb += w * x * x
        det = haa * hbb - hab * hab
        if det <= 1e-12:
            break
        da, db = (hbb * ga - hab * gb) / det, (haa * gb - hab * ga) / det
        a, b = a - da, b - db
        if max(abs(da), abs(db)) < 1e-7:
            break
    return a, b


def _zmean(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    mu = sum(xs) / n
    v = sum((x - mu) ** 2 for x in xs) / (n - 1)
    return round(mu / math.sqrt(v / n), 2) if v > 0 else 0.0


# ---------------------------------------------------------------- building everything in one walk
def build(ms, cc=None, venues=None):
    """Walk every match in time: per-side atoms + bet values (the registry tables) and per-match facts for the fixed
    studies. Returns (tables {tour: Table}, facts list)."""
    W = Walk(cc, venues)
    tables = {t: ex.Table(BETS) for t in ("atp", "wta")}
    facts = []
    i = 0
    while i < len(ms):
        j = i
        while j < len(ms) and ms[j].dn == ms[i].dn:
            j += 1
        day = ms[i:j]
        for m in day:
            if m.status == "void" or m.fw is None or m.tour not in tables:
                continue
            fW, fL = W.facts(m, m.W, m.L), W.facts(m, m.L, m.W)
            known = min(fW["n"], fL["n"]) >= KNOWN
            eW = W.elo(m, m.W, m.L) if known else None
            m.fx = {"eW": eW, "known": known, "gW": fW["games3"], "gL": fL["games3"], "rW": fW["ret"],
                    "rL": fL["ret"], "lW": fW["lay"], "lL": fL["lay"]}
            facts.append(m)
            for side in (0, 1):
                me, them = (fW, fL) if side == 0 else (fL, fW)
                p_me = m.fw if side == 0 else 1 - m.fw
                won = 1 if side == 0 else 0
                soft = {}
                for book in ("365", "avg"):
                    o = m.odds.get("b365" if book == "365" else "avg")
                    soft[book] = (o[side] * p_me - 1) if o else None
                atoms = side_atoms(m, me, them, m.wr if side == 0 else m.lr, m.lr if side == 0 else m.wr, p_me,
                                   None if eW is None else (eW if side == 0 else 1 - eW), soft)
                vals = {}
                for b in BETS:
                    o = m.odds.get(b)
                    if not o:
                        vals[b] = None
                        continue
                    fb = _nv(*o) if side == 0 else 1 - _nv(*o)
                    vals[b] = (won, fb, (o[side] - 1) if won else -1.0, p_me)
                tables[m.tour].add(m.d, atoms, vals)
        W.update_day(day)
        i = j
    return {t: tb.seal() for t, tb in tables.items()}, facts


# ---------------------------------------------------------------- 1) is tennis softer? (the market by segment)
def _rgap(m):
    if not m.wr or not m.lr:
        return None
    x = max(m.wr, m.lr) / min(m.wr, m.lr)
    return "rank x<1.5" if x < 1.5 else "rank x1.5-3" if x < 3 else "rank x3-10" if x < 10 else "rank x10+"


def segments_of(m):
    t = m.tour.upper()
    out = [f"{t}", f"{t} {m.lvl}", f"{t} round {RND.get(m.rnd, ('other',))[0]}", f"{t} {m.surf}",
           f"{t} {m.court}", f"{t} season {_season(m)}"]
    g = _rgap(m)
    if g:
        out.append(f"{t} {g}")
    if m.bo == 5:
        out.append(f"{t} best-of-5")
    return out


def _fav(m):
    """(fav won, fav's fair chance, fav index 0=W/1=L)."""
    return (1, m.fw, 0) if m.fw >= 0.5 else (0, 1 - m.fw, 1)


def _bet(acc, m, side, book, new):
    o = m.odds.get(book)
    if not o:
        return
    won = 1 if side == 0 else 0
    fb = _nv(*o) if side == 0 else 1 - _nv(*o)
    acc.add(won, fb, (o[side] - 1) if won else -1.0, m.fw if side == 0 else 1 - m.fw, new)


def market_study(facts, split, tests):
    """Accuracy, margin and bias of the closing prices, segment by segment."""
    seg = {}
    for m in facts:
        new = m.d >= split
        for s in segments_of(m):
            seg.setdefault(s, []).append((m, new))
    out = {}
    for name, rows in sorted(seg.items()):
        if len(rows) < 300:
            continue
        common = [(m, new) for m, new in rows if "b365" in m.odds and "avg" in m.odds]
        ll = {b: 0.0 for b in ("pin", "b365", "avg")}
        for m, _ in common:
            for b in ll:
                ll[b] += -math.log(max(1e-6, _nv(*m.odds[b])))
        marg = {b: [1 / m.odds[b][0] + 1 / m.odds[b][1] - 1 for m, _ in rows if b in m.odds] for b in ("pin", "b365", "avg")}
        stray = [abs(_nv(*m.odds["b365"]) - m.fw) for m, _ in rows if "b365" in m.odds]
        fav_edge = [(_fav(m)[0] - _fav(m)[1]) for m, _ in rows]
        # a bias that lasts: recalibrate the favorite's chance on the older half, grade on the newer half
        old = [(sm.logit(_fav(m)[1]), _fav(m)[0]) for m, new in rows if not new]
        nw = [(sm.logit(_fav(m)[1]), _fav(m)[0]) for m, new in rows if new]
        gain = None
        if len(old) >= 200 and len(nw) >= 200:
            a, b = _fit2([x for x, _ in old], [y for _, y in old])
            gain = round(1000 * sum(_ll(sm.sigmoid(x), y) - _ll(sm.sigmoid(a + b * x), y) for x, y in nw) / len(nw), 2)
        r = {"n": len(rows), "n_common": len(common),
             "logloss": {b: round(v / len(common), 4) for b, v in ll.items()} if common else None,
             "margin": {b: round(sum(v) / len(v), 4) for b, v in marg.items() if v},
             "b365_vs_pin": round(sum(stray) / len(stray), 4) if stray else None,
             "fav_edge": round(sum(fav_edge) / len(fav_edge), 4), "fav_edge_z": _zmean(fav_edge),
             "recal_gain_mnats": gain, "bets": {}}
        for side_name in ("fav", "dog"):
            for book in ("pin", "b365", "avg"):
                acc = Acc()
                for m, new in rows:
                    fi = _fav(m)[2]
                    _bet(acc, m, fi if side_name == "fav" else 1 - fi, book, new)
                s = acc.out()
                if s["n"]:
                    r["bets"][f"{side_name}@{book}"] = s
                    tests.append((f"segment {name}: every {side_name} at {book}", book, s))
        out[name] = r
    return out


def flb_study(facts, split, tests):
    """The favorite-longshot bias: every side by its fair-price bucket, win rate vs price, money at each book."""
    out = {}
    for tour in ("atp", "wta", "all"):
        buckets = {}
        for m in facts:
            if tour != "all" and m.tour != tour:
                continue
            new = m.d >= split
            for side in (0, 1):
                p = m.fw if side == 0 else 1 - m.fw
                k = min(9, int(p * 10))
                buckets.setdefault(k, {b: Acc() for b in BOOKS})
                for b in BOOKS:
                    _bet(buckets[k][b], m, side, b, new)
        rows = {}
        for k in sorted(buckets):
            name = f"{k * 10}-{k * 10 + 10}%"
            rows[name] = {}
            for b, acc in buckets[k].items():
                s = acc.out()
                if s["n"]:
                    rows[name][b] = s
                    tests.append((f"price {name} {tour} at {b}", b, s))
        out[tour] = rows
    return out


# ---------------------------------------------------------------- 2) line shopping
SHOP_X = (0.0, 0.02, 0.04, 0.06, 0.10)


def shop_study(facts, split, tests):
    """Betting only the side where a soft book's price beats Pinnacle's fair price by X% - at the soft book's price."""
    out = {}
    for book in ("b365", "avg", "max"):
        have = [m for m in facts if book in m.odds]
        if not have:
            continue
        beats = sum(1 for m in have if any(m.odds[book][s] * (m.fw if s == 0 else 1 - m.fw) > 1 for s in (0, 1)))
        r = {"matches": len(have), "share_beating_fair": round(beats / len(have), 4), "gettable": GETTABLE[book],
             "by_x": {}}
        for tour in ("all", "atp", "wta"):
            for fd in ("all", "fav", "dog"):
                for x in SHOP_X:
                    acc, ev = Acc(), []
                    for m in have:
                        if tour != "all" and m.tour != tour:
                            continue
                        for s in (0, 1):
                            p = m.fw if s == 0 else 1 - m.fw
                            if fd != "all" and (p >= 0.5) != (fd == "fav"):
                                continue
                            g = m.odds[book][s] * p - 1
                            if g > x:
                                _bet(acc, m, s, book, m.d >= split)
                                ev.append(g)
                    s_ = acc.out()
                    if not s_["n"]:
                        continue
                    s_["expected_roi"] = round(sum(ev) / len(ev), 4)
                    key = f"{tour} {fd} gap>{int(x * 100)}%"
                    r["by_x"][key] = s_
                    tests.append((f"line shop {book} {key}", book, s_))
        out[book] = r
    return out


def bovada_study(facts, lines_path=LINES, matches_path=MATCHES):
    """Our own Bovada closing lines (few): the margin they charge, vs Pinnacle's fair price when the same match is in
    the history, the result when ESPN has it, and each game spread vs the historical cover rate at that price."""
    try:
        with open(lines_path) as f:
            lines = json.load(f)
    except (OSError, ValueError, TypeError):
        return {"n": 0}
    res = {}
    if matches_path and os.path.exists(matches_path):
        with open(matches_path) as f:
            for r in csv.DictReader(f):
                if r.get("status") in ("STATUS_FINAL", "STATUS_RETIRED") and r.get("winner") in ("1", "2"):
                    res[(stn._last(r["p1_name"]), stn._last(r["p2_name"]), r["start"][:10])] = r
    hist = {}
    for m in facts[-8000:]:
        hist.setdefault((_td_last(m.W), _td_last(m.L)), []).append((m, 0))
        hist.setdefault((_td_last(m.L), _td_last(m.W)), []).append((m, 1))
    cover = handicap_table(facts)
    rows, marg, gaps, pl = [], [], [], []
    for key, ln in sorted(lines.items()):
        a, b = sd.parse_american(ln.get("a_ml")), sd.parse_american(ln.get("b_ml"))
        if not a or not b:
            continue
        da, db = sd.decimal(a), sd.decimal(b)
        marg.append(1 / da + 1 / db - 1)
        pa = _nv(da, db)
        row = {"match": f"{ln['a']} vs {ln['b']}", "start": ln.get("start"), "a_ml": a, "b_ml": b,
               "margin": round(1 / da + 1 / db - 1, 4), "a_fair_bovada": round(pa, 3)}
        la, lb = stn._last(ln["a"]), stn._last(ln["b"])
        d0 = (ln.get("start") or "")[:10]
        for mm, side in hist.get((la, lb), []):
            if d0 and abs(mm.dn - date.fromisoformat(d0).toordinal()) <= 2:
                pin_a = mm.fw if side == 0 else 1 - mm.fw
                row["a_fair_pinnacle"] = round(pin_a, 3)
                gaps += [da * pin_a - 1, db * (1 - pin_a) - 1]
                break
        r = res.get((la, lb, d0)) or res.get((lb, la, d0))
        if r:
            a_won = (r["winner"] == "1") == (stn._last(r["p1_name"]) == la)
            row["a_won"] = a_won
            pl += [(da - 1) if a_won else -1.0, (db - 1) if not a_won else -1.0]
        if ln.get("a_hcp") is not None and ln.get("a_sp") is not None and cover:
            fav_a = pa >= 0.5
            hcp = float(ln["a_hcp"] if fav_a else ln["b_hcp"])
            sp = sd.parse_american(ln["a_sp"] if fav_a else ln["b_sp"])
            est = cover_est(cover, max(pa, 1 - pa), hcp)
            if est is not None and sp:
                row["fav_spread"] = {"hcp": hcp, "odds": sp, "hist_cover": round(est, 3),
                                     "ev_at_bovada": round(est * sd.decimal(sp) - 1, 3)}
        rows.append(row)
    return {"n": len(rows), "avg_margin": round(sum(marg) / len(marg), 4) if marg else None,
            "matched_to_pinnacle": len(gaps) // 2,
            "share_beating_pinnacle_fair": round(sum(g > 0 for g in gaps) / len(gaps), 3) if gaps else None,
            "graded": len(pl) // 2, "roi_both_sides": round(sum(pl) / len(pl), 4) if pl else None, "lines": rows}


# ---------------------------------------------------------------- 3) model vs market
def model_study(facts, split, tests):
    """Walk-forward Elo (+ fatigue / retirements / layoff) alone and blended into Pinnacle's fair price."""
    rows = []
    for m in facts:
        f = m.fx
        if not f or not f["known"] or f["eW"] is None:
            continue
        flip = zlib.crc32(f"{m.d}{m.W}{m.L}".encode()) & 1          # which player is "A" (so y isn't always 1)
        sgn = -1 if flip else 1
        pa = 1 - m.fw if flip else m.fw
        ea = 1 - f["eW"] if flip else f["eW"]
        x = [sm.logit(pa), sm.logit(ea), sgn * (f["gL"] - f["gW"]) / 30, sgn * (f["rL"] - f["rW"]),
             sgn * (f["lL"] - f["lW"])]
        rows.append((m, flip, x, 0 if flip else 1, m.d >= split))
    halves = [[r for r in rows if not r[4]], [r for r in rows if r[4]]]
    if min(len(h) for h in halves) < 500:
        return {"n": len(rows), "note": "not enough rated matches yet"}
    fits = {}
    for h in (0, 1):
        tr = halves[h]
        fits[("model", h)] = sm.fit_logistic_offset([r[2][1:] for r in tr], [r[3] for r in tr], [0.0] * len(tr),
                                                    prior=[1.0, 0.0, 0.0, 0.0], lam=5.0, iters=8)
        fits[("blend", h)] = sm.fit_logistic_offset([r[2] for r in tr], [r[3] for r in tr], [0.0] * len(tr),
                                                    prior=[1.0, 0.0, 0.0, 0.0, 0.0], lam=5.0, iters=8)

    def _pred(kind, h, x):                        # rows of half h are predicted with weights fit on the OTHER half
        w = fits[(kind, 1 - h)]
        return sm.sigmoid(sum(a * b for a, b in zip(w, x[1:] if kind == "model" else x)))
    cache = {}
    for h in (0, 1):
        for r in halves[h]:
            for kind in ("model", "blend"):
                cache[(kind, id(r))] = _pred(kind, h, r[2])

    def pred(kind, h, x, r=None):
        return cache[(kind, id(r))] if r is not None else _pred(kind, h, x)
    ll = {}
    for h, name in ((0, "older"), (1, "newer")):
        hs = halves[h]
        d = {"n": len(hs)}
        d["pinnacle"] = round(sum(_ll(sm.sigmoid(r[2][0]), r[3]) for r in hs) / len(hs), 4)
        d["elo_raw"] = round(sum(_ll(sm.sigmoid(r[2][1]), r[3]) for r in hs) / len(hs), 4)
        d["model"] = round(sum(_ll(pred("model", h, r[2], r), r[3]) for r in hs) / len(hs), 4)
        d["blend"] = round(sum(_ll(pred("blend", h, r[2], r), r[3]) for r in hs) / len(hs), 4)
        diffs = [_ll(sm.sigmoid(r[2][0]), r[3]) - _ll(pred("blend", h, r[2], r), r[3]) for r in hs]
        d["blend_gain_mnats"] = round(1000 * sum(diffs) / len(diffs), 3)
        d["blend_gain_z"] = _zmean(diffs)
        bk = [r[0] for r in hs if "b365" in r[0].odds and "avg" in r[0].odds]
        if bk:
            d["books_same_matches"] = {b: round(sum(-math.log(max(1e-6, _nv(*m.odds[b]))) for m in bk) / len(bk), 4)
                                    for b in ("pin", "b365", "avg")}
        ll[name] = d
    bets = {}
    for kind in ("blend", "model"):
        for t in (0.02, 0.04, 0.06, 0.08, 0.12):
            for book in BOOKS:
                acc = Acc()
                for h in (0, 1):
                    for r in halves[h]:
                        m, flip, x, y, new = r
                        q = pred(kind, h, x, r)
                        pa = sm.sigmoid(x[0])
                        for side_a, dq in ((True, q - pa), (False, pa - q)):
                            if dq >= t:
                                side = (0 if not flip else 1) if side_a else (1 if not flip else 0)
                                _bet(acc, m, side, book, new)
                s = acc.out()
                if s["n"]:
                    key = f"{kind} beats pinnacle fair by {int(t * 100)}%+ at {book}"
                    bets[key] = s
                    tests.append((key, book, s))
    return {"n": len(rows), "logloss": ll, "weights_older": [round(v, 3) for v in fits[("blend", 0)]],
            "weights_newer": [round(v, 3) for v in fits[("blend", 1)]],
            "weights_note": "blend = [pinnacle logit, elo logit, fatigue, retirements, layoff]; each half is graded "
                            "with the weights learned on the OTHER half", "bets": bets}


# ---------------------------------------------------------------- 4b) sets + game handicaps
def _per_set(p):
    lo, hi = 0.0, 1.0
    for _ in range(40):
        s = (lo + hi) / 2
        lo, hi = (s, hi) if s * s * (3 - 2 * s) < p else (lo, s)
    return (lo + hi) / 2


def _per_set5(p):
    lo, hi = 0.0, 1.0
    for _ in range(40):
        s = (lo + hi) / 2
        lo, hi = (s, hi) if s ** 3 * (10 - 15 * s + 6 * s * s) < p else (lo, s)
    return (lo + hi) / 2


def sets_study(facts, split):
    """How often a match goes the distance vs what the price implies if sets were independent coin flips."""
    out = {}
    for tour, bo in (("atp", 3), ("wta", 3), ("atp", 5)):
        by = {}
        for m in facts:
            if m.tour != tour or m.bo != bo or m.status != "done" or len(m.sets) < (2 if bo == 3 else 3):
                continue
            pf = max(m.fw, 1 - m.fw)
            s = _per_set(pf) if bo == 3 else _per_set5(pf)
            imp = 2 * s * (1 - s) if bo == 3 else 6 * s * s * (1 - s) ** 2
            k = "50-60%" if pf < 0.6 else "60-70%" if pf < 0.7 else "70-80%" if pf < 0.8 else "80-90%" if pf < 0.9 else "90%+"
            by.setdefault(k, []).append((1 if len(m.sets) == bo else 0, imp, m.d >= split))
        rows = {}
        for k in sorted(by):
            v = by[k]
            d = [a - b for a, b, _ in v]
            old = [a - b for a, b, nw in v if not nw]
            nw = [a - b for a, b, x in v if x]
            rows[k] = {"n": len(v), "went_distance": round(sum(a for a, _, _ in v) / len(v), 4),
                       "implied": round(sum(b for _, b, _ in v) / len(v), 4), "diff": round(sum(d) / len(d), 4),
                       "z": _zmean(d), "diff_old": round(sum(old) / len(old), 4) if old else None,
                       "diff_new": round(sum(nw) / len(nw), 4) if nw else None}
        out[f"{tour} best-of-{bo}"] = rows
    return out


HCPS = (1.5, 2.5, 3.5, 4.5, 5.5, 6.5)


def handicap_table(facts):
    """Best-of-3 finished matches: how often the favorite wins by more than N games, by fair-price bucket."""
    by = {}
    for m in facts:
        if m.bo != 3 or m.status != "done" or not m.sets:
            continue
        gw = sum(a for a, _ in m.sets) - sum(b for _, b in m.sets)
        fav_w = m.fw >= 0.5
        mg = gw if fav_w else -gw
        k = min(9, int(max(m.fw, 1 - m.fw) * 20)) * 5          # 5% buckets
        by.setdefault(k, []).append(mg)
    out = {}
    for k, v in sorted(by.items()):
        if len(v) >= 100:
            out[str(k)] = {"n": len(v), "median": sorted(v)[len(v) // 2],
                           **{f"-{h:g}": round(sum(1 for x in v if x > h) / len(v), 4) for h in HCPS}}
    return out


def cover_est(tab, p_fav, hcp):
    k = str(min(9, int(p_fav * 20)) * 5)
    row = tab.get(k)
    if not row:
        return None
    if hcp < 0:
        return row.get(f"-{-hcp:g}")
    c = row.get(f"-{hcp:g}")                       # dog +h covers when the fav doesn't win by more than h
    return None if c is None else 1 - c


# ---------------------------------------------------------------- 4) the registry
def load(path=None):
    try:
        with open(path or PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _seen(st):
    raw = base64.b64decode(st.get("seen", "") or b"")
    return {raw[i:i + ex.HASH_B] for i in range(0, len(raw), ex.HASH_B)}


def _save(st, seen, path):
    st["seen"] = base64.b64encode(b"".join(sorted(seen))).decode()
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)


def grade(tbl, bet, mask, split_i):
    acc = Acc()
    vals = tbl.vals[bet]
    for i in ex._ones(mask):
        won, fb, pr, fp = vals[i]
        acc.add(won, fb, pr, fp, i >= split_i)
    return acc


def shift_of(fwd):
    """The logit nudge a proven angle earns: its FORWARD edge over Pinnacle's fair price, shrunk by n/(n+400)."""
    n, f, e = fwd.get("n", 0), fwd.get("fair_pin"), fwd.get("edge_pin")
    if not n or f is None or e is None:
        return 0.0
    return round((sm.logit(min(0.99, max(0.01, f + e))) - sm.logit(f)) * n / (n + SHRINK), 4)


def _brief(key, e):
    d, f = e.get("disc", {}), e.get("fwd", {})
    return (f"{key}: older half n={d.get('n')} roi {d.get('roi', 0):+.3f} edge z={d.get('z_edge')} | "
            f"newer half n={f.get('n_new', 0)} roi {f.get('roi_new', 0):+.3f} edge z={f.get('z_edge_new', 0)}")


def _recheck(st, key, e, groups, now, promoted, killed, demoted, status):
    grp = groups.get((e["tour"], e["bet"]))
    if not grp:
        return
    tbl, si = grp.tbl, grp.split_i
    acc = grade(tbl, e["bet"], tbl.mask(e["atoms"], e["bet"]), si)
    full, fwd = acc.out(), acc.out(1)
    f = {**full, "z_edge_new": fwd.get("z_edge", 0.0), "edge_pin_new": fwd.get("edge_pin"),
         "fair_pin_new": fwd.get("fair_pin")}
    e["fwd"], e["checked"] = f, now
    if f.get("n_new", 0) < FWD_N:
        return
    if f["roi_new"] <= 0:
        e["why"] = "the newer half lost money" if status == "suspects" else "turned negative after being proven"
        e["killed"] = now
        st["killed"][key] = st[status].pop(key)
        (killed if status == "suspects" else demoted).append(key)
    else:
        fw = {"n": fwd["n"], "fair_pin": fwd["fair_pin"], "edge_pin": fwd["edge_pin"]}
        if status == "suspects" and passes(full) and f["z_edge_new"] >= FWD_Z:
            e["promoted"], e["shift"] = now, shift_of(fw)
            st["proven"][key] = st[status].pop(key)
            promoted.append(key)
        elif status == "proven":
            e["shift"] = shift_of(fw)


def registry(st, tables, split, batch, budget_s, t0, now):
    seen = _seen(st)
    for k in ("suspects", "proven", "killed"):
        st.setdefault(k, {})
    groups = {}
    for tour, tbl in sorted(tables.items()):
        si = bisect.bisect_left(tbl.starts, split)
        old_bits = (1 << si) - 1
        for bet in BETS:
            if tbl.valid.get(bet, 0):
                g = ex.Group(tour, bet, tbl)
                g.split_i, g.old = si, old_bits
                groups[(tour, bet)] = g
    promoted, killed, demoted = [], [], []
    for key, e in list(st["proven"].items()):                    # proven: still making money going forward?
        _recheck(st, key, e, groups, now, promoted, killed, demoted, "proven")
    del LAST_TESTED[:]
    found, near, tested, graded = [], [], 0, 0
    exhausted = True
    for lvl in range(1, MAX_LEVEL + 1):
        gens = (g.cands(lvl, seen) for _, g in sorted(groups.items()))
        for key, atoms, mask in ex._round_robin(gens):
            if tested >= batch or time.time() - t0 > budget_s:
                exhausted = False
                break
            tour, bet = key.split("|")[:2]
            g = groups[(tour, bet)]
            seen.add(ex._h(key))
            LAST_TESTED.append(key)
            tested += 1
            om = mask & g.old
            if om.bit_count() < DISC_N:                          # too few older-half bets: can never be tested
                continue
            graded += 1
            s = grade(g.tbl, bet, om, g.split_i).out()           # the OLDER half only - the newer half is unseen
            if s["roi"] > 0 and s["z_edge"] >= Z_PROVEN:
                st["suspects"][key] = {"tour": tour, "bet": bet, "atoms": list(atoms), "split": split, "found": now,
                                       "disc": s, "fwd": {}}
                found.append(key)
            elif s["roi"] > 0:
                near.append((s["z_edge"], key, atoms, g))
        else:
            continue
        break
    for key, e in list(st["suspects"].items()):                  # suspects: forward-confirm on the newer half
        _recheck(st, key, e, groups, now, promoted, killed, demoted, "suspects")
    near.sort(key=lambda t: -t[0])
    closest = []
    for z, key, atoms, g in near[:10]:
        full = grade(g.tbl, key.split("|")[1], g.tbl.mask(list(atoms), key.split("|")[1]), g.split_i).out()
        closest.append({"key": key, "z_edge_older": z, "n": full["n"], "roi_old": full["roi_old"],
                        "roi_new": full["roi_new"], "z_edge_all": full["z_edge"], "n_new": full["n_new"]})
    st["seen_n"] = len(seen)
    return seen, {"tested": tested, "graded": graded, "exhausted": exhausted, "new_suspects": found,
                  "new_proven": promoted, "new_killed": killed + demoted, "closest": closest}


# ---------------------------------------------------------------- the run
def _fp(ms):
    h = hashlib.blake2b(digest_size=8)
    h.update(f"{len(ms)}|{ms[0].d if ms else ''}|{ms[-1].d if ms else ''}".encode())
    for m in ms[-500:]:
        h.update(f"{m.d}{m.W}{m.L}{m.odds.get('pin')}".encode())
    return h.hexdigest()


def _median_date(ms):
    ds = sorted(m.d for m in ms if m.fw is not None and m.status != "void")
    return ds[len(ds) // 2] if ds else "2000-01-01"


def study(path=PATH, hist=HIST, matches=MATCHES, lines=LINES, batch=BATCH, budget_s=BUDGET_S, split=None,
          verbose=True):
    """One study run. Returns {proven: [...], ...} and saves everything to edge.json."""
    t0 = time.time()
    ms = read_hist(hist)
    if not ms:
        if verbose:
            print(f"tennis edge: no odds history yet ({hist}) - skipped")
        return {"proven": [], "skipped": "no odds history yet"}
    seasons = Counter((m.tour, m.d[:4]) for m in ms)
    have = sum(1 for n in seasons.values() if n >= 1000)
    if have < MIN_SEASONS and not os.path.exists(path):
        # the time split and the "never retest" list are fixed on the first run, so wait for the whole history
        if verbose:
            print(f"tennis edge: odds history still loading ({have} of {MIN_SEASONS}+ seasons) - skipped")
        return {"proven": [], "skipped": f"odds history still loading ({have} seasons)"}
    st = load(path)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    st["split"] = st.get("split") or split or _median_date(ms)
    split = st["split"]
    cc, venues = countries(matches)
    tables, facts = build(ms, cc, venues)
    t_build = time.time() - t0
    fp = _fp(ms)
    new_data = fp != st.get("data_fp")
    tests = []
    res = {"data": {"matches": len(ms), "priced": len(facts), "from": ms[0].d, "to": ms[-1].d, "split": split,
                    "older": sum(1 for m in facts if m.d < split), "newer": sum(1 for m in facts if m.d >= split),
                    "void_walkovers": sum(1 for m in ms if m.status == "void"),
                    "retired_graded": sum(1 for m in facts if m.status == "ret"),
                    "with_b365": sum(1 for m in facts if "b365" in m.odds),
                    "with_max": sum(1 for m in facts if "max" in m.odds)}}
    res["segments"] = market_study(facts, split, tests)
    res["price_buckets"] = flb_study(facts, split, tests)
    res["line_shopping"] = shop_study(facts, split, tests)
    res["bovada"] = bovada_study(facts, lines, matches)
    res["model"] = model_study(facts, split, tests)
    res["sets"] = sets_study(facts, split)
    res["handicaps"] = handicap_table(facts)
    if new_data:                                     # the fixed tests count once per version of the data
        st["fixed_tests_total"] = st.get("fixed_tests_total", 0) + len(tests)
        st["data_fp"] = fp
    fixed_pass = [{"test": n, "book": b, "gettable": b in ("pin", "b365"), **s} for n, b, s in tests if passes(s)]
    fixed_near = sorted(({"test": n, "book": b, **s} for n, b, s in tests
                         if not passes(s) and s.get("n", 0) >= MIN_N and s["roi_old"] > 0 and s["roi_new"] > 0),
                        key=lambda r: -r["z_edge"])[:12]
    seen, reg = registry(st, tables, split, batch, budget_s, t0, now)
    st["tested"] = st.get("tested", 0) + reg["graded"]
    st["runs"] = st.get("runs", 0) + 1
    tot_fixed = st.get("fixed_tests_total", 0)
    fpos = {"registry_angles_tested": st["tested"], "fixed_tests_run": tot_fixed,
            "suspects_by_luck": round(st["tested"] * P_LUCK, 2),
            "proven_by_luck_registry": round(st["tested"] * P_LUCK * P_FWD, 4),
            "proven_by_luck_fixed": round(tot_fixed * P_LUCK, 3),
            "note": "one-sided luck odds of z 3.5 are ~1 in 4,300; a registry angle then needs an independent newer-"
                    "half z of 2.0+ (~1 in 44). Fixed tests overlap heavily, so their count overstates the luck."}
    proven_list = sorted(st["proven"]) + [f"fixed: {r['test']}" for r in fixed_pass if r["gettable"]]
    run = {"at": now, "tested": reg["tested"], "graded": reg["graded"], "suspects_found": len(reg["new_suspects"]),
           "promoted": len(reg["new_proven"]), "killed": len(reg["new_killed"]), "fixed_tests": len(tests),
           "fixed_pass": len(fixed_pass), "new_data": new_data, "exhausted": reg["exhausted"],
           "secs": round(time.time() - t0, 1), "build_secs": round(t_build, 1)}
    st["log"] = ([run] + st.get("log", []))[:LOG_CAP]
    st["closest"] = reg["closest"] or st.get("closest", [])
    st["updated"] = now
    st["results"] = res
    st["fixed_pass"] = fixed_pass
    st["fixed_closest"] = fixed_near
    st["false_positives"] = fpos
    st["proven_list"] = proven_list
    _save(st, seen, path)
    out = {**run, "proven": proven_list, "suspects": sorted(st["suspects"]), "new_suspects": reg["new_suspects"],
           "new_proven": reg["new_proven"], "new_killed": reg["new_killed"], "false_positives": fpos}
    if verbose:
        print(report(st, out))
    return out


def report(st, out):
    r = st.get("results", {})
    d = r.get("data", {})
    L = [f"THE TENNIS EDGE STUDY: {d.get('priced')} priced matches {d.get('from')} -> {d.get('to')} "
         f"(older half < {d.get('split')} <= newer half) in {out['secs']}s"]
    seg = r.get("segments", {})
    soft = sorted(((v["recal_gain_mnats"], k) for k, v in seg.items() if v.get("recal_gain_mnats") is not None),
                  reverse=True)[:4]
    if soft:
        L.append("   softest segments (a bias learned on the older half that still helps on the newer, mnats/match): "
                 + ", ".join(f"{k} {g:+.2f}" for g, k in soft))
    for t in ("ATP", "WTA"):
        v = seg.get(t)
        if v and v.get("logloss"):
            L.append(f"   {t}: log loss pin {v['logloss']['pin']} / b365 {v['logloss']['b365']} / avg "
                     f"{v['logloss']['avg']} · margin pin {v['margin'].get('pin')} b365 {v['margin'].get('b365')}")
    ls = r.get("line_shopping", {})
    for b in ("b365", "avg", "max"):
        x = (ls.get(b) or {}).get("by_x", {})
        s = x.get("all all gap>2%")
        if s:
            L.append(f"   line shop {b} >2% over pinnacle fair: n={s['n']} roi {s['roi_old']:+.3f} / {s['roi_new']:+.3f}"
                     f" (expected {s['expected_roi']:+.3f}) edge z={s['z_edge']} · beats fair in "
                     f"{ls[b]['share_beating_fair']:.0%} of matches")
    mo = (r.get("model") or {}).get("logloss", {}).get("newer")
    if mo:
        L.append(f"   model vs market, newer half: pinnacle {mo['pinnacle']} · elo {mo['elo_raw']} · model {mo['model']}"
                 f" · blend {mo['blend']} ({mo['blend_gain_mnats']:+.3f} mnats, z {mo['blend_gain_z']})")
    bv = r.get("bovada", {})
    if bv.get("n"):
        L.append(f"   bovada: {bv['n']} closing lines, margin {bv['avg_margin']}, {bv['matched_to_pinnacle']} matched "
                 f"to pinnacle, {bv['graded']} graded")
    fp = out["false_positives"]
    L.append(f"   registry: tested {out['graded']} new angles ({fp['registry_angles_tested']} ever) · new suspects "
             f"{out['suspects_found']} · promoted {out['promoted']} · killed {out['killed']} · "
             f"luck would give ~{fp['suspects_by_luck']} suspects / {fp['proven_by_luck_registry']} proven ever")
    L.append(f"   fixed tests: {out['fixed_tests']} this run, {out['fixed_pass']} pass the bar "
             f"(luck ~{fp['proven_by_luck_fixed']})")
    for k in out["new_suspects"]:
        e = st["suspects"].get(k) or st["proven"].get(k) or st["killed"].get(k) or {}
        L.append("   NEW SUSPECT " + _brief(k, e))
    for k in out["new_proven"]:
        L.append("   PROVEN " + _brief(k, st["proven"][k]))
    for k in out["new_killed"]:
        L.append("   KILLED " + _brief(k, st["killed"][k]))
    for p in st.get("fixed_pass", [])[:8]:
        L.append(f"   PASSES {p['test']}: n={p['n']} roi {p['roi_old']:+.3f} / {p['roi_new']:+.3f} z={p['z_edge']}"
                 f"{'' if p['gettable'] else ' (NOT a gettable price)'}")
    for c in st.get("closest", [])[:3]:
        L.append(f"   closest angle: {c['key']} n={c['n']} roi {c['roi_old']:+.3f} / {c['roi_new']:+.3f} "
                 f"z older {c['z_edge_older']} all {c['z_edge_all']}")
    for c in st.get("fixed_closest", [])[:3]:
        L.append(f"   closest fixed: {c['test']} n={c['n']} roi {c['roi_old']:+.3f} / {c['roi_new']:+.3f} z={c['z_edge']}")
    L.append(f"   PROVEN: {out['proven'] or 'nothing'}")
    return "\n".join(L)


# ---------------------------------------------------------------- hooks for sports_tennis
def proven(st):
    """Every proven registry angle: [{key, tour, bet, atoms, shift, fwd...}] (fixed tests aren't match nudges)."""
    return [{"key": k, **e} for k, e in sorted(((st or {}).get("proven") or {}).items())]


def atoms_of(match_features):
    """The atoms of one side: match_features = {"tour", "atoms": [...]} (or the raw facts: tour, series/level,
    round, surface, court, date, bo, p (this side's no-vig chance), rank, opp_rank - plus any atoms already known)."""
    f = match_features or {}
    A = set(f.get("atoms") or [])
    if f.get("level") or f.get("series"):
        A.add(f"lvl:{f.get('level') or level(f.get('series'))}")
    if f.get("surface"):
        A.add(f"surf:{str(f['surface']).lower()}")
    if f.get("court"):
        A.add(f"court:{'indoor' if str(f['court']).lower().startswith('indoor') else 'outdoor'}")
    if f.get("round") in RND:
        A.add(f"rd:{RND[f['round']][0]}")
    if str(f.get("date") or "")[5:7]:
        mo = int(str(f["date"])[5:7])
        A.add(f"ssn:{'early' if mo <= 3 else 'mid' if mo <= 7 else 'late'}")
    if int(f.get("bo") or 3) == 5:
        A.add("bo5")
    p = f.get("p")
    if p is not None:
        if p != 0.5:
            A.add("fav" if p > 0.5 else "dog")
        A.add(_pbucket(p))
    if _rk(f.get("rank")):
        A.add("rk:" + _rk(f["rank"]))
    if _rk(f.get("opp_rank")):
        A.add("ork:" + _rk(f["opp_rank"]))
    return A


def adjust(st, match_features, p):
    """A side's win chance, nudged by its single strongest matching proven angle (forward edge, shrunk); p unchanged
    when nothing proven matches."""
    pv = (st or {}).get("proven") or {}
    if not pv:
        return p
    tour = str((match_features or {}).get("tour") or "").lower()
    have = atoms_of(match_features)
    best = 0.0
    for e in pv.values():
        if e.get("tour") == tour and set(e.get("atoms", [])) <= have:
            s = e.get("shift", 0.0) or 0.0
            best = s if abs(s) > abs(best) else best
    return p if not best else sm.sigmoid(sm.logit(p) + best)


if __name__ == "__main__":
    study()
