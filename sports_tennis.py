"""🎾 TENNIS BONUS: men's (ATP) and women's (WTA) singles picks - a bonus section, never part of the main board or its records.

Every engine run:
  1. Results from ESPN's ATP scoreboard (each call returns whole tournaments, so history is walked a week at a
     time: 10 seasons, a year per run until caught up). Stored in data/sports/tennis/matches.csv.
  2. The study: surface ratings (overall + hard / clay / grass, blended - the proven way to rate tennis players),
     plus learned weights for fatigue (sets played the last 3 days), recent form and head-to-head. Best-of-5 at
     the Slams is handled from the per-set strength. Fit on the history, graded on the latest matches.
     Then the "life" factors (age + experience from ESPN bios, the last match, streaks, first-set record, injuries,
     travel) are each tested against that model on the same holdout - a factor joins a tour's model only with a
     real gain (paired log-loss z 2+); otherwise its weights stay 0.
  3. Odds: Bovada's public feed (current men's singles moneylines), refreshed every run.
  4. Once a day (from 6pm Pacific the night before, the next 24 hours of matches): up to 6 men's and 6 women's
     straight picks (55%+ and real value - fewer qualify = fewer picks, never filler), a Men's Tennis Parlay and a
     Women's Tennis Parlay (the 3 likeliest of that tour - never a mixed parlay). Posted picks are final.
     Retirements: void if no set was finished, otherwise the player who advances wins it; walkovers are void.
Men's and women's tennis are different worlds: separate ratings pools (ESPN's player ids are per tour - the same
number is two different people), weights learned and graded per tour, separate records.
Picks, results and records live in data/sports/tennis/picks.json."""
import csv
import json
import math
import os
import re
import time
import unicodedata
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sports_data as sd
import sports_lingo
import sports_model as sm

PT = ZoneInfo("America/Los_Angeles")
DIR = os.path.join(sd.DATA, "tennis")
MATCHES = os.path.join(DIR, "matches.csv")
PICKS = os.path.join(DIR, "picks.json")
ODDS = os.path.join(DIR, "odds.json")
RANKS = os.path.join(DIR, "rankings.json")   # ATP + WTA rankings, saved daily (ESPN only has today's): {date: {"tour:id": rank}}
LINES = os.path.join(DIR, "lines.json")      # every price seen, the last one before the start kept (closing line)
SET1_LINES = os.path.join(DIR, "set1_lines.json")   # RESEARCH ONLY: Bovada's first-set markets, the last price before the
                                                    # start (sports_tennis_set1 studies them; nothing picks from them)
FIELDS = ["id", "tour", "start", "event", "tourney", "round", "surface", "bo", "p1", "p1_name", "p2", "p2_name", "winner",
          "sets1", "sets2", "status", "done", "cc1", "cc2", "venue"]
NEWS = os.path.join(DIR, "news.json")
# matchups between countries in conflict: the engine learns from the results whether they play differently
CONFLICT = [("ukraine", "russia"), ("ukraine", "belarus"), ("serbia", "croatia"), ("serbia", "bosnia"),
            ("serbia", "kosovo"), ("georgia", "russia"), ("armenia", "azerbaijan"), ("china", "taiwan"),
            ("china", "chinese taipei"), ("india", "pakistan"), ("greece", "turkey"), ("israel", "iran"),
            ("israel", "lebanon"), ("israel", "palestine"), ("poland", "russia"), ("poland", "belarus")]
ALIASES = {"china pr": "china", "usa": "united states", "great britain": "united kingdom", "gbr": "united kingdom",
           "czechia": "czech republic", "korea republic": "south korea", "türkiye": "turkey", "turkiye": "turkey"}
ESPN = "https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard"
TOURS = ("atp", "wta")
BOVADA = "https://www.bovada.lv/services/sports/event/coupon/events/A/description/tennis?marketFilterId=def&lang=en"
YEARS = 10
N_PER_TOUR = 6                 # up to 6 men's + 6 women's straights a slate (never filler)
N_PICKS = 2 * N_PER_TOUR
PARLAY_LEGS = 3                # one parlay per tour (the 3 likeliest of that tour) - never a mixed parlay
TOUR_MIN_RATED = 3000          # a tour learns its own weights once it has this many rated matches; before that it
                               # borrows the shared weights (and the log says so)
PRIOR = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
STUDY = os.path.join(DIR, "study.json")        # the per-tour weights + accuracy from the last study
PREMATCH = os.path.join(DIR, "prematch.json")  # the last pre-match numbers per match (live tennis starts from them)
MIN_EDGE = 0.02                # an underdog needs a PROVEN angle AND 2%+ value (none proven today = no tennis dogs)
MIN_P = 0.55                   # ACCURACY FIRST: a tennis pick is one we expect to WIN (55%+) - no coin-flip dogs.
                               # Fewer qualify = fewer picks; never filler
TIER = os.path.join(DIR, "tier_study.json")    # THE TENNIS LABEL STUDY (tools/tennis_tier_study.py, 9/29): on ~17k
TRUST = 0.0                    # priced matches the engine never saw (2022-26), the market's no-vig price beat our own
FIGHT_MAX = 0.03               # number on both tours, and the more the engine disagreed, the WORSE its side did
                               # (ATP: sides it liked 10-15 pts more than the market hit 40%; WTA 20+ pts: 26%).
                               # So the win % is ANCHORED to the book: p = market + trust * (engine - market), the trust
                               # learned on the older half and kept only if it beat the market on the newer half
                               # (0 for both tours today). A pick = how likely it WINS (55%+), never a side our own
                               # read has 3+ points under the book (fighting the line), no dogs without a proven angle.
MAX_FAV = -300                 # no tennis moneyline shorter than -300: heavier favorites go on the game spread,
                               # and only when that bet itself is a 55%+ play (anchored to the SPREAD's own price)
MIN_MATCHES = 10               # both players need this many rated matches
MIN_RATED = 8000               # no tennis picks until the study has real history (several seasons) and learned weights
POST_FROM_HOUR_PT = 18
MIN_LEAD_MIN = 20
CLAY = ("roland garros", "french open", "monte carlo", "monte-carlo", "madrid", "rome", "internazionali", "italian open",
        "barcelona", "hamburg", "umag", "croatia open", "kitzbuhel", "kitzbühel", "gstaad", "swiss open", "bastad",
        "båstad", "nordea", "estoril", "munich", "bmw open", "geneva", "lyon", "houston", "clay court", "marrakech",
        "grand prix hassan", "buenos aires", "argentina open", "rio open", "rio de janeiro", "santiago", "chile open",
        "cordoba", "córdoba", "bucharest", "cagliari", "parma", "belgrade", "serbia open", "sardegna", "budapest",
        "istanbul", "quito", "sao paulo", "são paulo", "bogota", "düsseldorf", "dusseldorf", "nice", "gstaad")
GRASS = ("wimbledon", "queen's", "queens", "halle", "terra wortmann", "stuttgart", "boss open", "mercedes cup",
         "hertogenbosch", "libema", "rosmalen", "eastbourne", "rothesay", "mallorca", "newport", "hall of fame",
         "antalya", "nottingham")
MAJORS = ("australian open", "roland garros", "french open", "wimbledon", "us open")
# 🧓 the "life" factors: age + experience, the last match, streaks, first-set record, injuries, travel. Bios come from
# ESPN (tools/fetch_tennis_players.py -> players.json, keyed "tour:id"). Every feature is p1 minus p2 and uses only
# what was known before the match; a missing bio is a neutral 0 plus the bio_miss flag. Each factor is tested ALONE
# against the current model on the newer half (the same holdout), paired log loss per match: a factor joins a
# tour's model ONLY with a gain at z >= Z_KEEP; otherwise its weights stay 0 (never shipped as noise).
# (Serve stats / backhand: not in ESPN's scoreboard feed or matches.csv - not available for free, so not here.)
PLAYERS = os.path.join(DIR, "players.json")
FACTORS = {
    "experience": ("exp", "big"),                                         # earlier matches; Slam / QF+ matches
    "age": ("age_gap", "age_curve", "teen_rise", "vet_bo5", "bio_miss"),
    "young_vs_aging": ("teen_vs_vet", "young_hot"),                       # a teen vs a 30+; a young player on a heater
    "last_match": ("last_sets", "last_dist", "last_long", "rest"),        # (within 7 days) + days since
    "streaks": ("lost2", "won3"),
    "first_set": ("fs_rate", "f2_rate"),                                  # first set / first two sets, last 20
    "injury": ("inj_recent", "inj_12m"),                                  # retirements + walkovers
    "travel": ("travel",),                                                # new continent / 5+ time zones in 7 days
}
LIFE = tuple(k for ks in FACTORS.values() for k in ks)
LIFE_USE = False     # the crew (9/28): age / experience / first-set etc. stay RESEARCH ONLY - they never touch the picks
                     # or the breakdowns until the owner says so (the study still runs and reports what it finds)
LIFE_SWAP = (("age1", "age2"), ("exp_n1", "exp_n2"), ("big_n1", "big_n2"))
Z_KEEP = 2.0
YOUNG = 23.0                    # "young" for the young-vs-aging terms (22 and under)
LAST_D, LONG_GAMES = 7, 25      # the last match counts when it was within 7 days; a long one = 25+ games (bo3)
FS_N, FS_K = 20, 4              # first-set record: the last 20 matches, shrunk by 4 phantom 50/50 matches
INJ_TAU = 45                    # a retirement / walkover fades with a 45-day time constant
# where tournaments are: country -> (continent, UTC offset, standard time) - for the travel factor
PLACES = {"usa": ("na", -5), "united states": ("na", -5), "canada": ("na", -5), "mexico": ("na", -6),
          "argentina": ("sa", -3), "brazil": ("sa", -3), "uruguay": ("sa", -3), "chile": ("sa", -4),
          "bolivia": ("sa", -4), "colombia": ("sa", -5), "ecuador": ("sa", -5), "peru": ("sa", -5),
          "australia": ("oc", 10), "new zealand": ("oc", 12),
          "france": ("eu", 1), "great britain": ("eu", 0), "uk": ("eu", 0), "united kingdom": ("eu", 0),
          "england": ("eu", 0), "scotland": ("eu", 0), "ireland": ("eu", 0), "portugal": ("eu", 0),
          "spain": ("eu", 1), "italy": ("eu", 1), "germany": ("eu", 1), "switzerland": ("eu", 1),
          "austria": ("eu", 1), "sweden": ("eu", 1), "netherlands": ("eu", 1), "the netherlands": ("eu", 1),
          "monaco": ("eu", 1), "croatia": ("eu", 1), "hungary": ("eu", 1), "czech republic": ("eu", 1),
          "czechia": ("eu", 1), "belgium": ("eu", 1), "poland": ("eu", 1), "slovenia": ("eu", 1),
          "serbia": ("eu", 1), "luxembourg": ("eu", 1), "andorra": ("eu", 1), "slovakia": ("eu", 1),
          "denmark": ("eu", 1), "norway": ("eu", 1), "bosnia and herzegovina": ("eu", 1), "romania": ("eu", 2),
          "bulgaria": ("eu", 2), "greece": ("eu", 2), "estonia": ("eu", 2), "latvia": ("eu", 2),
          "finland": ("eu", 2), "ukraine": ("eu", 2), "russia": ("eu", 3), "turkey": ("eu", 3),
          "türkiye": ("eu", 3), "morocco": ("af", 1), "tunisia": ("af", 1), "egypt": ("af", 2),
          "south africa": ("af", 2), "israel": ("as", 2), "qatar": ("as", 3), "saudi arabia": ("as", 3),
          "united arab emirates": ("as", 4), "uae": ("as", 4), "kazakhstan": ("as", 5), "uzbekistan": ("as", 5),
          "india": ("as", 5.5), "thailand": ("as", 7), "china": ("as", 8), "china pr": ("as", 8),
          "hong kong": ("as", 8), "singapore": ("as", 8), "malaysia": ("as", 8), "philippines": ("as", 8),
          "chinese taipei": ("as", 8), "taiwan": ("as", 8), "japan": ("as", 9), "korea republic": ("as", 9),
          "south korea": ("as", 9)}
US_WEST = ("california", ", ca", "indian wells", "los angeles", "san diego", "san jose", "stanford", "carlsbad",
           "san francisco")
TEEN, VET = 20.0, 30.0          # a teenager; a veteran (the bo5 term grows a notch per 3 years past 30)
DEBUT_AGE = 18                  # no turned-pro year: a career is assumed to start at 18 (for the censoring fix)
CENSOR_DAYS = 60                # first seen this close to the start of our history = his earlier career is unseen
PRE_YEARS_MAX, RATE_MAX = 15, 80   # the censoring fix never adds more than 15 unseen years, at <= 80 matches a year
CURVE_SHRINK, CURVE_MIN = 150, 100  # the age curve: residuals by 2-year band, shrunk; the peak band needs 100+ sides


def _norm(name):
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", " ", s).split()


def _last(name):
    w = _norm(name)
    return w[-1] if w else ""


def surface_of(tourney):
    t = str(tourney or "").lower()
    if any(k in t for k in GRASS):
        return "grass"
    if any(k in t for k in CLAY):
        return "clay"
    return "hard"


def _t(iso):
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- player bios (age + experience)
def load_players(path=None):
    """{"tour:id": {"dob": "YYYY-MM-DD", "height_cm", "hand", "pro"} or {"none": True}} ({} when not fetched yet)."""
    try:
        with open(path or PLAYERS) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def bios_for(players, tour):
    """One tour's bios {espn id: bio} (ids are per tour: ATP 2980 is not WTA 2980)."""
    pre = f"{tour_of(tour)}:"
    return {k[len(pre):]: v for k, v in (players or {}).items() if k.startswith(pre) and isinstance(v, dict)
            and not v.get("none")}


def _ymd(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def age_at(dob, when):
    """Age in years (float) on the day of `when` (ISO), from a 'YYYY-MM-DD' birth date; None when unknown."""
    d, w = _ymd(dob), _ymd(when)
    return None if not d or not w else (w - d).days / 365.25


def career_start(bio):
    """The year a career started (float): turned-pro year, else birth + DEBUT_AGE; None when neither is known."""
    pro = (bio or {}).get("pro")
    if pro:
        try:
            return float(pro)
        except (TypeError, ValueError):
            pass
    d = _ymd((bio or {}).get("dob"))
    return d.year + (d.timetuple().tm_yday - 1) / 365.25 + DEBUT_AGE if d else None


def _year(iso):
    t = _t(iso)
    return t.year + (t.timetuple().tm_yday - 1) / 365.25


def is_big(m):
    """A big match: a Slam main-draw match or a quarterfinal-or-later (never qualifying)."""
    r = str(m.get("round") or "").lower()
    if "qualif" in r:
        return False
    return any(k in str(m.get("tourney") or "").lower() for k in MAJORS) or r in (
        "quarterfinal", "quarterfinals", "semifinal", "semifinals", "final", "the final") or "medal" in r


def _band(age):
    return min(11, max(0, int((age - 16) // 2)))                  # 16-17, 18-19, ..., 38+


def band_label(b):
    b = int(b)
    return f"{16 + 2 * b}-{17 + 2 * b}" if b < 11 else "38+"


def _teen(a):
    return 1.0 if a is not None and a < TEEN else 0.0


def _vet(a):
    return max(0.0, a - VET) / 3 if a is not None else 0.0


def place_of(venue):
    """(continent, UTC offset) of a venue like 'Wuhan, China' / 'Cincinnati, Ohio, USA'; None when unknown."""
    v = str(venue or "").strip().lower()
    if not v:
        return None
    last = v.replace(".", ",").split(",")[-1].strip()
    hit = PLACES.get(last)
    if hit is None:
        hit = next((PLACES[k] for k in sorted(PLACES, key=len, reverse=True) if re.search(rf"\b{re.escape(k)}\b", v)),
                   None)
    if hit and hit[0] == "na" and hit[1] == -5 and any(k in v for k in US_WEST):
        return ("na", -8)
    if hit and hit[0] == "oc" and "perth" in v:
        return ("oc", 8)
    return hit


def far(a, b):
    """A long trip: another continent, or 5+ time zones."""
    return bool(a and b) and (a[0] != b[0] or abs(a[1] - b[1]) >= 5)


def first_sets(m, side):
    """(won the first set, won the first two sets) for side 1/2 of a finished match; None when not played."""
    try:
        a = [int(x) for x in str(m.get("sets1") or "").split()]
        b = [int(x) for x in str(m.get("sets2") or "").split()]
    except ValueError:
        return None
    if not a or len(a) != len(b) or max(a[0], b[0]) < 6:
        return None
    mine, theirs = (a, b) if side == 1 else (b, a)
    two = len(a) >= 2 and max(a[1], b[1]) >= 6 and mine[0] > theirs[0] and mine[1] > theirs[1]
    return mine[0] > theirs[0], two


def _rate(xs, k=FS_K):
    return (sum(xs) + 0.5 * k) / (len(xs) + k) - 0.5


def flip_features(f):
    """The same features from p2's side (p1-minus-p2 numbers negated, the per-player numbers swapped)."""
    out = {**f, "fatigue": -f["fatigue"], "form": -f["form"], "h2h": -f["h2h"], "surface_gap": -f["surface_gap"],
           "home": -f.get("home", 0)}
    for k in LIFE:
        if k in f:
            out[k] = -f[k]
    for a, b in LIFE_SWAP:
        if a in f or b in f:
            out[a], out[b] = f.get(b), f.get(a)
    return out


# ---------------------------------------------------------------- results (ESPN)
def parse_espn(payload, tour="atp"):
    """ESPN ATP / WTA scoreboard -> [match rows] (singles only)."""
    out = []
    for ev in payload.get("events") or []:
        tourney = ev.get("name") or ev.get("shortName") or ""
        major = bool(ev.get("major")) or any(k in tourney.lower() for k in MAJORS)
        for gr in ev.get("groupings") or []:
            gname = ((gr.get("grouping") or {}).get("displayName") or "")
            if "Singles" not in gname or ("Women" in gname) != (tour == "wta"):
                continue
            for c in gr.get("competitions") or []:
                comps = c.get("competitors") or []
                if len(comps) != 2:
                    continue
                st = ((c.get("status") or {}).get("type") or {})
                ids, names, sets, ccs, pts, serving = [], [], [], [], [], []
                for x in comps:
                    a = x.get("athlete") or {}
                    ids.append(str(a.get("id") or x.get("id") or ""))
                    names.append(a.get("displayName") or a.get("fullName") or "?")
                    ccs.append(((a.get("flag") or {}).get("alt") or "").strip())
                    sets.append([int(float(ls.get("value") or 0)) for ls in x.get("linescores") or []])
                    pts.append(_live_points(x))
                    serving.append(_serving(x))
                if not all(ids):
                    continue
                win = 1 if comps[0].get("winner") else 2 if comps[1].get("winner") else 0
                rnd = ((c.get("round") or {}).get("displayName") or "")
                done = sum(1 for a, b in zip(*sets) if max(a, b) >= 6 and (abs(a - b) >= 2 or max(a, b) == 7))
                out.append({
                    "id": f"{tour}:{c.get('id')}", "tour": tour, "start": c.get("date") or ev.get("date") or "", "event": str(ev.get("id") or ""),
                    "tourney": tourney, "round": rnd, "surface": surface_of(tourney),
                    "bo": 5 if tour == "atp" and major and "qualif" not in rnd.lower() else 3,
                    "p1": ids[0], "p1_name": names[0], "p2": ids[1], "p2_name": names[1], "winner": win,
                    "sets1": " ".join(map(str, sets[0])), "sets2": " ".join(map(str, sets[1])),
                    "status": st.get("name") or "", "done": done, "cc1": ccs[0], "cc2": ccs[1],
                    "venue": ((c.get("venue") or {}).get("fullName") or ""),
                    # live extras (not stored in matches.csv): the game score and who's serving, when ESPN has them
                    "pts1": pts[0], "pts2": pts[1],
                    "server": 1 if serving[0] and not serving[1] else 2 if serving[1] and not serving[0] else None,
                    "detail": str(st.get("detail") or st.get("shortDetail") or (c.get("status") or {}).get("detail") or ""),
                })
    return out


def _live_points(x):
    """The current game's points for one competitor ('0', '15', '30', '40', 'AD', or a tiebreak number) - ESPN's
    tennis feed doesn't always carry them, so every place they've been seen is tried. None = not in the feed."""
    for k in ("points", "currentPoints", "gameScore", "currentGameScore", "point"):
        v = x.get(k)
        if v not in (None, ""):
            return str(v.get("displayValue") or v.get("value") or "") if isinstance(v, dict) else str(v)
    ls = x.get("linescores") or []
    if ls and isinstance(ls[-1], dict):
        for k in ("points", "currentPoints", "gamePoints"):
            if ls[-1].get(k) not in (None, ""):
                return str(ls[-1][k])
    return None


def _serving(x):
    for k in ("possession", "serving", "isServing", "server", "serve"):
        if x.get(k) is not None:
            return bool(x.get(k))
    return False


def _state(row):
    s = row["status"].upper()
    if "WALKOVER" in s or "CANCEL" in s or "POSTPONED" in s:
        return "void"
    if "RETIRED" in s or "ABANDON" in s or "DEFAULT" in s:
        return "retired"
    if "FINAL" in s or "COMPLETE" in s:
        return "final"
    if "IN_PROGRESS" in s or "PLAY" in s:
        return "live"
    if ("DELAY" in s or "SUSPEND" in s or "RAIN" in s) and any(int(v) for v in str(row.get("sets1") or "").split() + str(row.get("sets2") or "").split()):
        return "live"                                    # a delay mid-match: it's underway (the score stays up)
    return "pre"


def load_matches():
    if not os.path.exists(MATCHES):
        return {}
    with open(MATCHES) as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def save_matches(ms):
    os.makedirs(DIR, exist_ok=True)
    rows = sorted(ms.values(), key=lambda r: (r["start"], r["id"]))
    with open(MATCHES + ".tmp", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(MATCHES + ".tmp", MATCHES)


def _espn(day, tour="atp"):
    for i in range(2):
        try:
            with urllib.request.urlopen(f"{ESPN.format(tour=tour)}?dates={day:%Y%m%d}", timeout=20) as r:
                return parse_espn(json.load(r), tour)
        except Exception as e:                           # noqa: BLE001
            if i:
                sd.ERRORS.append(f"tennis {day:%Y-%m-%d}: {str(e)[:100]}")
                return None
            time.sleep(1.5)


def sync(state, budget_s=150):
    """This week (+ tomorrow) every run; history a year per run (weekly calls - each returns whole tournaments)."""
    ms = load_matches()
    today = datetime.now(timezone.utc).date()
    if state.get("tennis_v", 1) < 3:                     # countries, venues + the WTA added: rebuild the history once
        state["tennis_v"], state["tennis_from"], ms = 3, today.isoformat(), {}
    days = [today + timedelta(days=d) for d in range(-7, 2)]
    frm = datetime.strptime(state.get("tennis_from", today.isoformat()), "%Y-%m-%d").date()
    target = today - timedelta(days=365 * YEARS)
    lo = max(target, frm - timedelta(days=365))
    d = frm - timedelta(days=7)
    while d >= lo:
        days.append(d)
        d -= timedelta(days=7)
    deadline = time.time() + budget_s

    def run(job):
        day, tour = job
        return day, (_espn(day, tour) if time.time() < deadline else None)
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(run, [(d, t) for d in days for t in TOURS]))
    got = 0
    rank = {"pre": 0, "live": 1}                       # a match only moves forward: scheduled -> playing -> final
    def _adv(m):                                       # (several days' pages carry the same match - an older copy
        return (rank.get(_state(m), 2), len(str(m.get("sets1") or "").split()))   # never knocks a newer one back)
    for day, rows in results:
        for r in rows or []:
            old = ms.get(r["id"])
            if old and _adv(old) > _adv(r):
                continue
            ms[r["id"]] = r
            got += 1
    if all(rows is not None for day, rows in results if day < today - timedelta(days=7)):
        state["tennis_from"] = min(lo, frm).isoformat()
    save_matches(ms)
    return ms, len(results), sum(1 for _, r in results if r is None)


# ---------------------------------------------------------------- the study
def _k(n):
    return 250 / (n + 5) ** 0.4                         # new players move fast, veterans slow (538's tennis K)


def elo_p(a, b):
    return 1 / (1 + 10 ** ((b - a) / 400))


def to_bo5(p3):
    """Best-of-3 match chance -> best-of-5, through the per-set chance (the better player wins more often in bo5)."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        s = (lo + hi) / 2
        lo, hi = (s, hi) if s * s * (3 - 2 * s) < p3 else (lo, s)
    s = (lo + hi) / 2
    return s ** 3 * (10 - 15 * s + 6 * s * s)


class Ratings:
    """Overall + surface Elo, recent form, fatigue and head-to-head, updated match by match."""

    def __init__(self, bios=None):
        self.r, self.n, self.hist, self.h2h = {}, {}, {}, {}
        self.bios = bios or {}                           # {espn id: bio} of this tour
        self.big, self.first, self.trend = {}, {}, {}    # big matches played, first match seen, recent ratings
        self.start = None                                # the first match of our history (left-censoring)
        self.curve = None                                # {band: deviation from the peak band} once learned
        self.lastm, self.fs, self.inj = {}, {}, {}       # last match; first-set record; retirements + walkovers

    def _get(self, pid, surf):
        return self.r.get((pid, None), 1500.0), self.r.get((pid, surf), 1500.0)

    def age(self, pid, when):
        return age_at((self.bios.get(pid) or {}).get("dob"), when)

    def exp_n(self, pid, when):
        """Earlier tour-level matches. Our history is left-censored (it starts in 2016), so a player first seen at the
        very start of it gets his unseen years added: (start of our history - turned-pro year, or birth + 18), capped
        at 15 years, times his OWN rate so far (matches / years seen, capped at 80) - earlier matches only."""
        n = self.n.get(pid, 0)
        bio, first = self.bios.get(pid), self.first.get(pid)
        if not n or not bio or not first or not self.start or (_t(first) - _t(self.start)).days > CENSOR_DAYS:
            return n
        cs = career_start(bio)
        if cs is None:
            return n
        pre = min(max(0.0, _year(self.start) - cs), PRE_YEARS_MAX)
        yrs = max(1.0, (_t(when) - _t(first)).days / 365.25)
        return n + pre * min(n / yrs, RATE_MAX)

    def rise(self, pid):
        """How far his overall rating climbed over his last 10 matches (per 100 points, capped at +-2)."""
        tr = self.trend.get(pid)
        return max(-2.0, min(2.0, (tr[-1] - tr[0]) / 100)) if tr and len(tr) >= 2 else 0.0

    def curve_at(self, a):
        return (self.curve or {}).get(str(_band(a)), 0.0) if a is not None else 0.0

    def one(self, pid, m, when):
        """One player's side of the life factors (from earlier matches only)."""
        a = self.age(pid, when)
        res = [w for t, w, _ in self.hist.get(pid, [])[-6:] if t < when][-3:]
        won3 = float(len(res) == 3 and all(res))
        lost2 = float(len(res) >= 2 and not any(res[-2:]))
        last = self.lastm.get(pid)                       # (start, sets, went the distance, games, bo, tourney, place)
        days = max(0.0, (_t(when) - _t(last[0])).total_seconds() / 86400) if last else None
        fresh = last is not None and days <= LAST_D
        long_ = fresh and last[3] >= (LONG_GAMES if last[4] == 3 else 2 * LONG_GAMES - 10)
        inj = [d for d in self.inj.get(pid, []) if d < when]
        inj_d = (_t(when) - _t(inj[-1])).total_seconds() / 86400 if inj else None
        cut = (_t(when) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M")
        here = place_of(m.get("venue"))
        trav = fresh and last[5] != (m.get("tourney") or "") and far(last[6], here)
        fs = self.fs.get(pid) or ()
        return {"age": a, "won3": won3, "lost2": lost2, "rest": math.log1p(min(days, 30.0)) if last else math.log1p(30.0),
                "last_sets": last[1] / 3 if fresh else 0.0, "last_dist": float(bool(fresh and last[2])),
                "last_long": float(bool(long_)), "inj_recent": math.exp(-inj_d / INJ_TAU) if inj else 0.0,
                "inj_12m": min(3, sum(1 for d in inj if d >= cut)) / 3, "travel": float(bool(trav)),
                "fs_rate": _rate([x for x, _ in fs]), "f2_rate": _rate([y for _, y in fs])}

    def life(self, m, when):
        """The life factors, p1 minus p2 (age terms 0 when a bio is missing, flagged by bio_miss)."""
        p1, p2 = m["p1"], m["p2"]
        s1, s2 = self.one(p1, m, when), self.one(p2, m, when)
        a1, a2 = s1["age"], s2["age"]
        e1, e2 = self.exp_n(p1, when), self.exp_n(p2, when)
        b1, b2 = self.big.get(p1, 0), self.big.get(p2, 0)
        both = a1 is not None and a2 is not None
        bo5 = int(m.get("bo") or 3) == 5

        def tvv(a, b):                                   # a teen against a 30+
            return float(a is not None and b is not None and a < TEEN and b >= VET)

        def yhot(a, s):                                  # a young player (22 and under) who won his last 3
            return float(a is not None and a < YOUNG and s["won3"] > 0)
        return {"age1": a1, "age2": a2, "exp_n1": e1, "exp_n2": e2, "big_n1": b1, "big_n2": b2,
                "age_gap": (a1 - a2) / 5 if both else 0.0,
                "age_curve": self.curve_at(a1) - self.curve_at(a2) if both else 0.0,
                "exp": math.log1p(e1) - math.log1p(e2), "big": math.log1p(b1) - math.log1p(b2),
                "teen_rise": _teen(a1) * self.rise(p1) - _teen(a2) * self.rise(p2),
                "vet_bo5": _vet(a1) - _vet(a2) if bo5 else 0.0,
                "bio_miss": float(a1 is None) - float(a2 is None),
                "teen_vs_vet": tvv(a1, a2) - tvv(a2, a1), "young_hot": yhot(a1, s1) - yhot(a2, s2),
                **{k: s1[k] - s2[k] for k in ("last_sets", "last_dist", "last_long", "rest", "lost2", "won3",
                                              "fs_rate", "f2_rate", "inj_recent", "inj_12m", "travel")}}

    def features(self, m, when=None):
        when = when or m["start"]
        p1, p2, surf = m["p1"], m["p2"], m["surface"]
        o1, s1 = self._get(p1, surf)
        o2, s2 = self._get(p2, surf)
        p = (elo_p(o1, o2) + elo_p(s1, s2)) / 2
        p = min(max(p, 0.01), 0.99)

        def fatigue(pid):
            cut = (_t(when) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
            return sum(sets for t, _, sets in self.hist.get(pid, []) if cut <= t < when)

        def form(pid):
            h = [w for t, w, _ in self.hist.get(pid, []) if t < when][-10:]
            return (sum(h) / len(h) - 0.5) if h else 0.0
        h = self.h2h.get((p1, p2), 0) - self.h2h.get((p2, p1), 0)
        home = is_home(m.get("cc1"), m.get("venue"), m.get("tourney")) - is_home(m.get("cc2"), m.get("venue"), m.get("tourney"))
        clash = 1.0 if conflict(m.get("cc1"), m.get("cc2")) else 0.0
        return {"elo": sm.logit(p), "fatigue": (fatigue(p2) - fatigue(p1)) / 3, "form": form(p1) - form(p2),
                "h2h": max(-3, min(3, h)) / 3, "known": min(self.n.get(p1, 0), self.n.get(p2, 0)),
                "p_elo": p, "surface_gap": (s1 - s2) - (o1 - o2), "home": home, "clash": clash,
                "clash_elo": clash * sm.logit(p), **self.life(m, when)}

    def update(self, m):
        st = _state(m)
        if int(m["winner"] or 0) in (1, 2) and ("WALKOVER" in str(m.get("status")).upper() or st == "retired"):
            quit_ = m["p2"] if int(m["winner"]) == 1 else m["p1"]      # retired or withdrew (injury history)
            self.inj.setdefault(quit_, []).append(m["start"])
        if st not in ("final", "retired") or int(m["winner"] or 0) not in (1, 2):
            return
        w1 = 1.0 if int(m["winner"]) == 1 else 0.0
        sets = len([x for x in str(m["sets1"]).split() if x])
        for key in (None, m["surface"]):
            a, b = self.r.get((m["p1"], key), 1500.0), self.r.get((m["p2"], key), 1500.0)
            e = elo_p(a, b)
            self.r[(m["p1"], key)] = a + _k(self.n.get(m["p1"], 0)) * (w1 - e)
            self.r[(m["p2"], key)] = b + _k(self.n.get(m["p2"], 0)) * ((1 - w1) - (1 - e))
        self.start = self.start or m["start"]
        big = is_big(m)
        bo = int(m.get("bo") or 3)
        try:
            games = sum(int(x) for x in str(m["sets1"]).split()) + sum(int(x) for x in str(m["sets2"]).split())
        except ValueError:
            games = 0
        last = (m["start"], sets, sets >= bo and st == "final", games, bo, m.get("tourney") or "", place_of(m.get("venue")))
        for side, (pid, won) in enumerate(((m["p1"], w1), (m["p2"], 1 - w1)), 1):
            self.n[pid] = self.n.get(pid, 0) + 1
            self.hist.setdefault(pid, []).append((m["start"], won, sets))
            self.first.setdefault(pid, m["start"])
            self.big[pid] = self.big.get(pid, 0) + big
            self.trend.setdefault(pid, deque(maxlen=11)).append(self.r[(pid, None)])
            self.lastm[pid] = last
            fs = first_sets(m, side)
            if fs:
                self.fs.setdefault(pid, deque(maxlen=FS_N)).append(fs)
        winner, loser = (m["p1"], m["p2"]) if w1 else (m["p2"], m["p1"])
        self.h2h[(winner, loser)] = self.h2h.get((winner, loser), 0) + 1


def tour_of(x):
    """'atp' / 'wta' for a match row, a pick, a candidate or a plain tour string (old rows: from the id prefix)."""
    if isinstance(x, dict):
        t = str(x.get("tour") or "").lower()
        if t not in TOURS:
            t = "wta" if str(x.get("match") or x.get("id") or "").startswith("wta:") else "atp"
        return t
    return "wta" if str(x or "").lower() == "wta" else "atp"


class Pools:
    """One ratings pool per tour. ESPN's player ids are numbered per tour (ATP 2980 and WTA 2980 are two different
    people), so an ATP result must never move a WTA rating, form, fatigue or head-to-head - or the other way round."""

    def __init__(self, players=None):
        self.pools = {t: Ratings(bios_for(players, t)) for t in TOURS}   # players.json: {"tour:id": bio}

    def pool(self, tour):
        return self.pools[tour_of(tour)]

    def features(self, m, when=None):
        return self.pool(tour_of(m)).features(m, when)

    def update(self, m):
        self.pool(tour_of(m)).update(m)


def weights_for(w, tour):
    """The tour's own weights ({'atp': [...], 'wta': [...], 'shared': [...]}); a plain list = one set for both."""
    if isinstance(w, dict):
        return w.get(tour_of(tour)) or w.get("shared") or PRIOR
    return w


def games_for(gm, tour):
    """The tour's game-margin model ({'atp': {'3': [slope, sig]}, ...}); a flat {'3': ...} = one for both."""
    gm = gm or {}
    if any(k in gm for k in TOURS):
        return gm.get(tour_of(tour)) or {}
    return gm


def _cc(x):
    x = str(x or "").strip().lower()
    return ALIASES.get(x, x)


def conflict(a, b):
    a, b = _cc(a), _cc(b)
    return bool(a and b) and ((a, b) in CONFLICT or (b, a) in CONFLICT)


def is_home(cc, venue, tourney):
    """1 when the player is playing in his own country (the crowd's behind him)."""
    c = _cc(cc)
    if not c:
        return 0
    where = f"{venue} {tourney}".lower().replace("china pr", "china")
    names = {c} | {k for k, v in ALIASES.items() if v == c}
    return 1 if any(re.search(rf"\b{re.escape(n)}\b", where) for n in names) else 0


def margin(m):
    """p1's games won minus p2's (finished matches only)."""
    try:
        a = [int(x) for x in str(m["sets1"]).split()]
        b = [int(x) for x in str(m["sets2"]).split()]
    except ValueError:
        return None
    return sum(a) - sum(b) if a and len(a) == len(b) and _state(m) == "final" else None


def cover_p(gm, p, hcp, bo):
    """Chance a player with win chance p covers a game handicap (e.g. -5.5)."""
    slope, sig = gm.get(str(int(bo or 3))) or gm.get("3") or (None, None)
    if not slope:
        return None
    mu = slope * sm.logit(min(max(p, 0.01), 0.99))
    return sm.phi((mu + hcp) / max(sig, 1.0))


def _x(f, mask=None):
    # clash_elo: in a conflict matchup, does the favorite hold up or tighten up? (learned, can go either way)
    # then the LIFE features (age + experience); a weight list of the old length simply ignores them (zip)
    life = [float(f.get(k) or 0.0) for k in LIFE]
    if mask is not None:
        life = [v if keep else 0.0 for v, keep in zip(life, mask)]
    return [1.0, f["elo"], f["fatigue"], f["form"], f["h2h"], f.get("home", 0), f.get("clash_elo", 0)] + life


def model_p(w, f, bo=3, tour=None):
    """p1's match win chance with the tour's own weights (w: per-tour dict or one list)."""
    ws = weights_for(w, tour)
    p = sm.sigmoid(sum(a * b for a, b in zip(ws, _x(f))))
    return to_bo5(p) if int(bo or 3) == 5 else p


def _fit(rows):
    return sm.fit_logistic_offset([_x(f)[:len(PRIOR)] for f, _, _ in rows], [y for _, y, _ in rows], [0.0] * len(rows),
                                  prior=PRIOR, lam=20.0) if len(rows) >= 500 else list(PRIOR)


def _lls(ws, ev):
    """Each graded row's log loss under weights ws."""
    out = []
    for f, y, m in ev:
        p = min(max(model_p(ws, f, m["bo"]), 1e-4), 1 - 1e-4)
        out.append(-math.log(p if y else 1 - p))
    return out


def _score(ws, ev):
    """(log loss, accuracy) of weights ws on graded rows [(features, y, match)]."""
    if not ev:
        return None, None
    acc = sum((model_p(ws, f, m["bo"]) > 0.5) == (y == 1.0) for f, y, m in ev)
    return sum(_lls(ws, ev)) / len(ev), acc / len(ev)


def _zmean(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    mu = sum(xs) / n
    v = sum((x - mu) ** 2 for x in xs) / (n - 1)
    return round(mu / math.sqrt(v / n), 2) if v > 0 else 0.0


def age_curve(ws, rows):
    """The tour's age curve, learned on the older (fit) rows only: each side's result minus the current model's
    chance, averaged by 2-year age band (shrunk toward 0), as the deviation from the best-performing band (<= 0).
    Returns ({band: deviation}, {band: sides}) - ({}, {}) with no bios."""
    s, n = {}, {}
    for f, y, m in rows:
        if f.get("age1") is None or f.get("age2") is None:
            continue
        r = y - model_p(ws, f, m["bo"])
        for a, x in ((f["age1"], r), (f["age2"], -r)):
            b = str(_band(a))
            s[b], n[b] = s.get(b, 0.0) + x, n.get(b, 0) + 1
    val = {b: s[b] / (n[b] + CURVE_SHRINK) for b in s}
    ok = [v for b, v in val.items() if n[b] >= CURVE_MIN]
    if not ok:
        return {}, n
    peak = max(ok)
    return {b: round(v - peak, 5) for b, v in val.items()}, n


def _fit_keys(fit_on, keys):
    """The model refit with these life features added (the rest of the life weights 0)."""
    cols = [LIFE.index(k) for k in keys]
    X = [(lambda x: x[:len(PRIOR)] + [x[len(PRIOR) + c] for c in cols])(_x(f)) for f, _, _ in fit_on]
    wv = sm.fit_logistic_offset(X, [y for _, y, _ in fit_on], [0.0] * len(fit_on),
                                prior=list(PRIOR) + [0.0] * len(cols), lam=20.0)
    out = list(wv[:len(PRIOR)]) + [0.0] * len(LIFE)
    for c, v in zip(cols, wv[len(PRIOR):]):
        out[len(PRIOR) + c] = v
    return out


def _vs(ll0, ws, ev, keys):
    """A variant vs the current model on the holdout: n, active matches, log loss, accuracy, paired gain + z."""
    ll1 = _lls(ws, ev)
    d = [a - b for a, b in zip(ll0, ll1)]                # > 0 = the new features made that match's loss smaller
    ll, acc = _score(ws, ev)
    return {"n": len(ev), "active": sum(1 for f, _, _ in ev if any(f.get(k) for k in keys)), "logloss": _r(ll),
            "acc": _r(acc), "gain_mnats": round(1000 * sum(d) / len(d), 3), "z": _zmean(d),
            "weights": {k: round(ws[len(PRIOR) + LIFE.index(k)], 4) for k in keys}}


def life_study(pool, base, fit_on, ev):
    """Do the life factors (age, experience, last match, streaks, first sets, injuries, travel...) earn a place in
    this tour's model? The age curve is learned on the older rows; then EACH factor alone is fit on the older rows
    and graded on the SAME newer-half holdout as the current model: the paired log-loss difference per match and its
    z. Factors with a gain at z >= Z_KEEP are refit together, and that combination is kept only if it passes the same
    bar (else the single best passing factor; else nothing - the life weights stay 0). Returns (weights, report)."""
    curve, band_n = age_curve(base, fit_on)
    pool.curve = curve
    for f, _, _ in fit_on + ev:                          # the curve term, now that the curve is known
        if f.get("age1") is not None and f.get("age2") is not None:
            f["age_curve"] = pool.curve_at(f["age1"]) - pool.curve_at(f["age2"])
    ll_b, acc_b = _score(base, ev)
    bio = sum(1 for f, _, _ in ev if f.get("age1") is not None and f.get("age2") is not None)
    rep = {"base": {"logloss": _r(ll_b), "acc": _r(acc_b)}, "graded": len(ev), "graded_with_both_ages": bio,
           "curve": {band_label(b): v for b, v in sorted(curve.items(), key=lambda t: int(t[0]))},
           "curve_sides": {band_label(b): v for b, v in sorted(band_n.items(), key=lambda t: int(t[0]))},
           "peak_band": next((band_label(b) for b, v in curve.items() if v == 0.0), None), "factors": {},
           "kept": [], "z_keep": Z_KEEP}
    best = list(base) + [0.0] * len(LIFE)
    if len(fit_on) < 500 or not ev:
        return best, rep
    ll0 = _lls(base, ev)
    passed = []
    for name, keys in FACTORS.items():
        if not any(f.get(k) for f, _, _ in fit_on for k in keys):
            rep["factors"][name] = {"n": len(ev), "active": 0, "note": "no data for it yet (all neutral)"}
            continue
        wv = _fit_keys(fit_on, keys)
        r = rep["factors"][name] = _vs(ll0, wv, ev, keys)
        if r["gain_mnats"] > 0 and r["z"] >= Z_KEEP:
            passed.append((r["gain_mnats"], name, wv))
    if not passed:
        return best, rep
    passed.sort(reverse=True)
    best, rep["kept"] = passed[0][2], [passed[0][1]]
    if len(passed) > 1:
        names = [n for _, n, _ in passed]
        keys = [k for n in names for k in FACTORS[n]]
        wv = _fit_keys(fit_on, keys)
        r = rep["combined"] = {**_vs(ll0, wv, ev, keys), "factors": names}
        if r["gain_mnats"] > passed[0][0] and r["z"] >= Z_KEEP:
            best, rep["kept"] = wv, names
    return best, rep


def _games_model(ws, rows):
    gm = {}
    for bo in (3, 5):                   # games won by: margin = slope * logit(win chance) (+ noise), per format
        pts = [(sm.logit(min(max(model_p(ws, f, bo), 0.01), 0.99)), margin(m)) for f, _, m in rows
               if int(m["bo"] or 3) == bo and margin(m) is not None]
        if len(pts) >= 300:
            slope = sum(x * y for x, y in pts) / max(1e-9, sum(x * x for x, _ in pts))
            sig = math.sqrt(sum((y - slope * x) ** 2 for x, y in pts) / len(pts))
            gm[str(bo)] = [round(slope, 3), round(sig, 3)]
    return gm


def _r(x):
    return round(x, 4) if x is not None else None


def study(ms, eval_n=2000, log=print, players=None):
    """Replay every finished match through its own tour's ratings pool, then learn and grade the weights PER TOUR
    (men's and women's tennis are different worlds). A tour with too few rated matches borrows the shared weights
    (fit on both tours) and the log says so. A tour with its own weights then tests age + experience (life_study:
    kept only when they beat the current model on the newer half). players = the bios ({"tour:id": bio}; None = none).
    Returns (ratings pools, {'atp','wta','shared'} weights, report)."""
    rows = sorted((m for m in ms.values() if _state(m) in ("final", "retired")), key=lambda m: (m["start"], m["id"]))
    wo = [m for m in ms.values() if "WALKOVER" in str(m.get("status")).upper()]   # walkovers: injury history only
    rt = Pools(players)
    data = {t: [] for t in TOURS}
    for m in sorted(rows + wo, key=lambda m: (m["start"], m["id"])):
        if _state(m) == "void":
            rt.update(m)
            continue
        f = rt.features(m)
        if f["known"] >= MIN_MATCHES and int(m["winner"] or 0) in (1, 2) and _state(m) == "final":
            data[tour_of(m)].append((f, 1.0 if int(m["winner"]) == 1 else 0.0, m))
        rt.update(m)
    split = {}
    for t, d in data.items():                          # each tour graded on its own latest matches
        n_ev = min(eval_n, len(d) // 4)
        split[t] = (d[:len(d) - n_ev], d[len(d) - n_ev:])
    fit_all = sorted((r for t in TOURS for r in split[t][0]), key=lambda r: (r[2]["start"], r[2]["id"]))
    shared = _fit(fit_all)
    gm_shared = _games_model(shared, fit_all)
    w = {"shared": shared}
    tours, gm = {}, {}
    for t in TOURS:
        fit_on, ev = split[t]
        own = len(data[t]) >= TOUR_MIN_RATED and len(fit_on) >= 500
        life = None
        if own:
            base = _fit(fit_on)
            w[t], life = life_study(rt.pool(t), base, fit_on, ev)
            if not LIFE_USE:                               # research only (the crew's call): the picks use the model
                w[t] = base                                # exactly as it was, whatever the study found
                life["used_in_picks"] = False
        else:
            w[t] = shared
            log(f"tennis study: {t.upper()} has only {len(data[t])} rated matches (< {TOUR_MIN_RATED}) - "
                f"using the shared weights for it")
        gm[t] = (_games_model(w[t], fit_on) if own else {}) or gm_shared
        ll, acc = _score(w[t], ev)
        ll0, acc0 = _score(PRIOR, ev)
        tours[t] = {"rated": len(data[t]), "fit": len(fit_on), "graded": len(ev), "own_weights": own,
                    "weights": [round(v, 3) for v in w[t]], "games": gm[t], "acc": _r(acc), "logloss": _r(ll),
                    "acc_elo": _r(acc0), "logloss_elo": _r(ll0), "life": life}
    ev_all = [r for t in TOURS for r in split[t][1]]
    both = [(tours[t]["acc"], tours[t]["logloss"], tours[t]["acc_elo"], tours[t]["logloss_elo"], tours[t]["graded"])
            for t in TOURS if tours[t]["graded"]]

    def avg(i):
        return _r(sum(b[i] * b[4] for b in both) / len(ev_all)) if ev_all else None
    report = {"matches": len(rows), "rated": sum(len(d) for d in data.values()), "weights": [round(v, 3) for v in shared],
              "games": gm, "tours": tours, "acc": avg(0), "logloss": avg(1), "acc_elo": avg(2), "logloss_elo": avg(3)}
    return rt, w, report


def save_study(rep, now):
    """The per-tour weights and accuracy, saved (data/sports/tennis/study.json)."""
    os.makedirs(DIR, exist_ok=True)
    with open(STUDY + ".tmp", "w") as f:
        json.dump({**rep, "updated": now.strftime("%Y-%m-%dT%H:%MZ")}, f, indent=1)
    os.replace(STUDY + ".tmp", STUDY)


# ---------------------------------------------------------------- odds
def _get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r), r.headers.get("x-requests-remaining")


def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


_BOV_RAW = [None]                 # the last raw Bovada payload (the first-set capture reads it; research only)


def bovada():
    """Bovada's public tennis feed: ATP + WTA singles moneylines."""
    data, _ = _get(BOVADA)
    _BOV_RAW[0] = data
    return parse_bovada(data)


def _bov_tour(path):
    """'atp' / 'wta' from Bovada's group path; None when it names both (a combined event: names decide)."""
    a, w = bool(re.search(r"\batp\b", path)), bool(re.search(r"\bwta\b", path))
    return None if a == w else "wta" if w else "atp"


def parse_bovada(data, live=False):
    """Bovada tennis groups -> [{a, b, start, a_ml, b_ml, (a_hcp, a_sp, ...), tour}] (ATP + WTA singles).
    live=True: only events being played and their LIVE match moneyline; a line the book has suspended (market or
    a side not open, or no price) comes back with suspended=True - never a price to act on."""
    rows = {}
    for grp in data if isinstance(data, list) else []:
        if not isinstance(grp, dict):
            continue
        path = " ".join(str(p.get("description") or "") for p in grp.get("path") or []).lower()
        if not re.search(r"\b(atp|wta)\b", path) or any(k in path for k in ("doubles", "challenger", "itf", "exhibition", "utr", "125")):
            continue
        for ev in grp.get("events") or []:
            if live and not ev.get("live"):
                continue
            for dg in ev.get("displayGroups") or []:
                for mk in dg.get("markets") or []:
                    desc = str(mk.get("description", "")).lower()
                    per = mk.get("period") or {}
                    if not per.get("main", True) or ("moneyline" not in desc and "game spread" not in desc):
                        continue
                    if live and ("moneyline" not in desc or not per.get("live")):
                        continue
                    oc = mk.get("outcomes") or []
                    if len(oc) != 2:
                        continue

                    def am(o):
                        v = str((o.get("price") or {}).get("american") or "").upper()
                        return 100 if v == "EVEN" else int(v) if re.match(r"^[+-]?\d+$", v) else None
                    a, b = am(oc[0]), am(oc[1])
                    start = datetime.fromtimestamp(int(ev.get("startTime", 0)) / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
                    key = (oc[0].get("description"), oc[1].get("description"), start)
                    if live:
                        shut = (str(mk.get("status") or "O").upper() != "O" or a is None or b is None
                                or any(str(o.get("status") or "O").upper() != "O" for o in oc))
                        rows[key] = {"a": key[0], "b": key[1], "start": start, "src": "bovada", "tour": _bov_tour(path),
                                     "a_ml": a, "b_ml": b, "suspended": shut, "event": str(ev.get("id") or ""),
                                     "mod": ev.get("lastModified")}   # (when the book last touched it: stale = no price)
                        continue
                    if a is None or b is None:
                        continue
                    row = rows.setdefault(key, {"a": key[0], "b": key[1], "start": start, "src": "bovada", "tour": _bov_tour(path)})
                    if "moneyline" in desc:
                        row["a_ml"], row["b_ml"] = a, b
                    else:
                        try:
                            row["a_hcp"] = float((oc[0].get("price") or {}).get("handicap"))
                            row["b_hcp"] = float((oc[1].get("price") or {}).get("handicap"))
                            row["a_sp"], row["b_sp"] = a, b
                        except (TypeError, ValueError):
                            pass
    return [r for r in rows.values() if "a_ml" in r]


# ---------------------------------------------------------------- first-set markets (RESEARCH ONLY)
SET1_RX = re.compile(r"\b(1st|first)\s+set\b|\bset\s*(1|one)\b")
SET_BET_RX = re.compile(r"set betting|correct score|exact (set )?score|set score")
SET1_SKIP = ("total", "tiebreak", "tie break", "tie-break", "correct", "score", "odd", "even", "race", "break",
             "exact", "game ")


def is_set1(text):
    """'1st Set Winner' / 'Set 1 Winner' / 'First Set - Moneyline' / a market in a '1st Set' period -> True."""
    return bool(SET1_RX.search(str(text or "").lower()))


def _bov_am(o):
    v = str((o.get("price") or {}).get("american") or "").upper()
    return 100 if v == "EVEN" else int(v) if re.match(r"^[+-]?\d+$", v) else None


def parse_bovada_set1(data):
    """Bovada tennis groups -> [{a, b, start, tour, event, (a_ml, b_ml), (a_s1, b_s1), (a_s1_hcp, a_s1_sp, b_s1_hcp,
    b_s1_sp), (set_betting: {outcome: american})}] for PRE-MATCH ATP + WTA singles events that carry a first-set
    winner, a first-set game handicap or a set-betting market. Players are named as in the match moneyline (a = its
    first outcome) when there is one. Matching is loose: the market's own description and its period's are read
    ('1st Set Winner', 'Set 1 Winner', 'First Set Moneyline', 'Moneyline' in a '1st Set' period...). Research only:
    parse_bovada (the picks' prices) is untouched."""
    out = []
    for grp in data if isinstance(data, list) else []:
        if not isinstance(grp, dict) or not isinstance(grp.get("path") or [], list):
            continue
        path = " ".join(str(p.get("description") or "") for p in grp.get("path") or [] if isinstance(p, dict)).lower()
        if not re.search(r"\b(atp|wta)\b", path) or any(k in path for k in ("doubles", "challenger", "itf", "exhibition", "utr", "125")):
            continue
        for ev in grp.get("events") or []:
            if ev.get("live"):
                continue
            start = datetime.fromtimestamp(int(ev.get("startTime", 0)) / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
            ml = win = hcp = sb = None
            for dg in ev.get("displayGroups") or []:
                for mk in dg.get("markets") or []:
                    per = mk.get("period") or {}
                    desc = str(mk.get("description") or "").lower()
                    label = f"{desc} {per.get('description') or ''} {per.get('abbreviation') or ''}".lower()
                    oc = mk.get("outcomes") or []
                    if per.get("live") or str(mk.get("status") or "O").upper() != "O":
                        continue
                    if is_set1(label):
                        if "spread" in desc or "handicap" in desc:
                            if len(oc) == 2:
                                hcp = oc                     # the first-set game handicap
                        elif len(oc) == 2 and not any(k in f"{desc} " for k in SET1_SKIP):
                            win = oc                         # the first-set winner
                    elif "moneyline" in desc and per.get("main", True) and len(oc) == 2:
                        ml = oc
                    elif SET_BET_RX.search(desc) and len(oc) >= 2:
                        sb = oc                              # set betting (the match's exact score in sets)
            names = ml or win or hcp
            if not (win or hcp or sb) or not names:
                continue
            a, b = names[0].get("description"), names[1].get("description")
            row = {"a": a, "b": b, "start": start, "src": "bovada", "tour": _bov_tour(path), "event": str(ev.get("id") or "")}

            def side(o):                                     # which player an outcome names (None: neither / both)
                n = _norm(o.get("description"))
                hits = [s for s, nm in (("a", a), ("b", b)) if _last(nm) and _last(nm) in n]
                return hits[0] if len(hits) == 1 else None
            if ml:
                x, y = _bov_am(ml[0]), _bov_am(ml[1])
                if x is not None and y is not None:
                    row["a_ml"], row["b_ml"] = x, y
            if win:
                got = {side(o): _bov_am(o) for o in win}
                if set(got) == {"a", "b"} and None not in got.values():
                    row["a_s1"], row["b_s1"] = got["a"], got["b"]
            for o in hcp or []:
                s, pr = side(o), _bov_am(o)
                try:
                    h = float((o.get("price") or {}).get("handicap"))
                except (TypeError, ValueError):
                    continue
                if s and pr is not None:
                    row[f"{s}_s1_hcp"], row[f"{s}_s1_sp"] = h, pr
            sbd = {str(o.get("description")): _bov_am(o) for o in sb or [] if _bov_am(o) is not None}
            if sbd:
                row["set_betting"] = sbd
            if any(k in row for k in ("a_s1", "a_s1_hcp", "b_s1_hcp", "set_betting")):
                out.append(row)
    return out


def save_set1_lines(rows, now, path=None):
    """Our own first-set line history (research only): the last first-set price seen before each start, keyed like
    lines.json (the same way save_lines keeps closing lines)."""
    path = path or SET1_LINES
    hist = {}
    if os.path.exists(path):
        with open(path) as f:
            hist = json.load(f)
    for ln in rows:
        if ln.get("start") and _t(ln["start"]) > now:
            hist[f"{_last(ln['a'])}|{_last(ln['b'])}|{ln['start'][:10]}"] = {**ln, "seen": now.strftime("%Y-%m-%dT%H:%MZ")}
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(hist, f, indent=0, sort_keys=True)
    os.replace(path + ".tmp", path)


def refresh_odds(state, now):
    """Prices for upcoming matches from Bovada (kept from the last good read if the feed fails)."""
    cache = {}
    if os.path.exists(ODDS):
        with open(ODDS) as f:
            cache = json.load(f)
    try:
        lines = bovada()
        if lines:
            cache = {"fetched": now.strftime("%Y-%m-%dT%H:%MZ"), "src": "bovada", "lines": lines}
            os.makedirs(DIR, exist_ok=True)
            with open(ODDS, "w") as f:
                json.dump(cache, f, indent=1)
        save_lines(lines, now)
        print(f"tennis odds: {len(lines)} singles matches priced (bovada)")
        try:                                             # research only: never touches the lines above
            s1 = parse_bovada_set1(_BOV_RAW[0])
            save_set1_lines(s1, now)
            print(f"tennis first-set lines: {sum('a_s1' in r for r in s1)} first-set winner markets seen "
                  f"({len(s1)} matches with any set market)")
        except Exception as e:                           # noqa: BLE001
            print(f"tennis first-set capture failed: {str(e)[:80]}")
    except Exception as e:                               # noqa: BLE001
        sd.ERRORS.append(f"bovada: {str(e)[:100]}")
        print(f"tennis odds: BOVADA FAILED ({str(e)[:80]}) - tell the owner if this keeps happening")
    return [ln for ln in cache.get("lines", []) if ln.get("start", "") >= (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")]


def rankings(now):
    """Today's ATP + WTA rankings {"tour:player id": rank} (ids are per tour: ATP 2980 is not WTA 2980); saved once a
    day so the engine builds its own ranking history. A day saved the old way (bare ids, tours mixed) is re-read."""
    hist = {}
    if os.path.exists(RANKS):
        with open(RANKS) as f:
            hist = json.load(f)
    day = now.astimezone(PT).date().isoformat()
    if day not in hist or (hist[day] and not any(":" in k for k in hist[day])):
        try:
            hist[day] = {}
            for tour in TOURS:
                with urllib.request.urlopen(ESPN.format(tour=tour).replace("scoreboard", "rankings"), timeout=20) as r:
                    ranks = (json.load(r).get("rankings") or [{}])[0].get("ranks") or []
                hist[day].update({f"{tour}:{(x.get('athlete') or {}).get('id')}": int(x.get("current")) for x in ranks if x.get("current")})
            os.makedirs(DIR, exist_ok=True)
            with open(RANKS, "w") as f:
                json.dump(hist, f, indent=0, sort_keys=True)
        except Exception as e:                           # noqa: BLE001
            sd.ERRORS.append(f"tennis rankings: {str(e)[:100]}")
    return hist[max(hist)] if hist else {}


def news_sync(now):
    """Tennis drama from ESPN's ATP/WTA news (relationship drama, family, illness, suspensions...): {player id: [tags]}.
    Drama on the other side is a reason for our pick; drama on our side needs twice the value and is never a filler."""
    import sports_news
    data = {}
    if os.path.exists(NEWS):
        with open(NEWS) as f:
            data = json.load(f)
    for tour in TOURS:
        try:
            with urllib.request.urlopen(f"https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/news?limit=100", timeout=20) as r:
                arts = json.load(r).get("articles") or []
        except Exception as e:                           # noqa: BLE001
            sd.ERRORS.append(f"tennis news {tour}: {str(e)[:100]}")
            continue
        for a in arts:
            kinds = sports_news.classify(f"{a.get('headline', '')} {a.get('description', '')}")
            if not kinds:
                continue
            for c in a.get("categories") or []:
                pid = c.get("athleteId") or (c.get("athlete") or {}).get("id")
                if pid:
                    tags = data.setdefault(f"{tour}:{pid}", [])          # ids are per tour
                    if all(t["id"] != str(a.get("id")) for t in tags):
                        tags.append({"id": str(a.get("id")), "kind": kinds[0], "date": (a.get("published") or now.isoformat())[:10],
                                     "headline": (a.get("headline") or "")[:140]})
    cut = (now - timedelta(days=sports_news.DRAMA_DAYS)).date().isoformat()
    data = {k: [t for t in v if t["date"] >= cut] for k, v in data.items() if ":" in k}   # (bare ids: tour unknown)
    data = {k: v for k, v in data.items() if v}
    os.makedirs(DIR, exist_ok=True)
    with open(NEWS, "w") as f:
        json.dump(data, f, indent=1)
    return data


def save_lines(lines, now):
    """Build our own tennis line history (no free source has one): the last price seen before each start."""
    hist = {}
    if os.path.exists(LINES):
        with open(LINES) as f:
            hist = json.load(f)
    for ln in lines:
        if ln.get("start") and _t(ln["start"]) > now:
            hist[f"{_last(ln['a'])}|{_last(ln['b'])}|{ln['start'][:10]}"] = {**ln, "seen": now.strftime("%Y-%m-%dT%H:%MZ")}
    with open(LINES, "w") as f:
        json.dump(hist, f, indent=0, sort_keys=True)


def price(m, lines, full=False):
    """(p1 ml, p2 ml) for a stored match from the odds lines (same two last names, start within 36 hours);
    full=True: {ml: (p1, p2), sp: ((p1 handicap, odds), (p2 handicap, odds)) or None}."""
    ln, flip = match_line(m, lines)
    if ln is None:
        return None
    a, b = ("b", "a") if flip else ("a", "b")
    ml = (ln[f"{a}_ml"], ln[f"{b}_ml"])
    if not full:
        return ml
    sp = ((ln[f"{a}_hcp"], ln[f"{a}_sp"]), (ln[f"{b}_hcp"], ln[f"{b}_sp"])) if f"{a}_hcp" in ln else None
    return {"ml": ml, "sp": sp}


def match_line(m, lines, hours=36):
    """(the odds line for this match, flipped?) - same two last names (either order), start within `hours`."""
    l1, l2 = _last(m["p1_name"]), _last(m["p2_name"])
    n1, n2 = set(_norm(m["p1_name"])), set(_norm(m["p2_name"]))

    def same(line_name, last, names):                        # same last name, or the same name in the other order
        return _last(line_name) == last or (len(names) >= 2 and set(_norm(line_name)) == names)   # ("Ma Yexin" = "Yexin Ma")
    for ln in lines:
        if ln.get("start") and m["start"] and abs((_t(ln["start"]) - _t(m["start"])).total_seconds()) > hours * 3600:
            continue
        if ln.get("tour") and m.get("tour") and ln["tour"] != tour_of(m):
            continue                                             # never a men's line on a women's match
        for flip, (x, y) in ((False, (ln["a"], ln["b"])), (True, (ln["b"], ln["a"]))):
            if same(x, l1, n1) and same(y, l2, n2):
                return ln, flip
    return None, False


# ---------------------------------------------------------------- the words
SURF = {"hard": "hard court", "clay": "clay", "grass": "grass"}


def _used(skip=()):
    """Our big phrases already on the dashboard (main board + tennis), plus every wording part the last two tennis
    slates used - so a new write-up repeats neither today's board nor yesterday's."""
    import sports_breakdown as sb
    out = sb.slang_in(sb.dashboard_texts(skip=skip))
    for sl_ in _load_picks()[-2:]:
        for l in sl_.get("picks") or []:
            if (l.get("id"), l.get("side"), l.get("market")) not in skip:
                out |= sb.recent_grams((x, (_say_name(l.get("player")), _say_name(l.get("opp"))))
                                       for x in l.get("breakdown") or [])
    return out


TENNIS_BV = 15                                   # breakdown version (older ones get rewritten before the match)


CN_FAMILY = {"Wang", "Zhang", "Zheng", "Cui", "Ma", "Wu", "Zhu", "Yuan", "Bai", "Gao", "Shang", "Xu", "Li", "Liu",
             "Yang", "Zhou", "Guo", "Bu", "Wei", "Sun", "Chen", "Lin", "Huang", "Zhao", "Hu", "Tang", "Han", "Duan",
             "Jiang", "Lu", "Yao", "Xin", "Te", "Zhong", "Fang", "Peng", "You", "Ye", "Feng", "Dang"}


def _say_name(name):
    """'Botic Van De Zandschulp' -> 'Van De Zandschulp', 'Marco Trungelliti' -> 'Trungelliti' (how people say it)."""
    parts = str(name or "").split()
    if len(parts) == 2 and parts[0] in CN_FAMILY:        # Chinese names go family name first: Cui Jie is "Cui Jie"
        return " ".join(parts)
    for i, w in enumerate(parts[1:], 1):
        if w.lower() in ("van", "de", "da", "del", "der", "di", "le", "la", "von", "dos", "du"):
            return " ".join(parts[i:])
    return parts[-1] if parts else str(name or "")


def life_line(v, c, me, them, he, He, his):
    """At most ONE age / experience line, only when it's on our side and big enough to say out loud (a vet in a
    best-of-5, a big-match experience gap, a teenager, a big experience gap, a big age gap). Display only: it moves
    no number unless the study kept that factor. "" when nothing applies (or every wording is taken on the board)."""
    if not LIFE_USE:
        return ""
    f = c.get("f") or {}
    a_me, a_them = f.get("age1"), f.get("age2")
    x_me, x_them = int(f.get("exp_n1") or 0), int(f.get("exp_n2") or 0)
    b_me, b_them = int(f.get("big_n1") or 0), int(f.get("big_n2") or 0)
    bo5 = int(c.get("bo") or 3) == 5
    if bo5 and a_me is not None and a_me >= VET and (a_them is None or a_them < a_me):
        age = int(a_me)
        return v.say("t_life_vet5", [
            f"🧓 {age} years old in a best-of-5? That's {his} whole game — {he}'s been in these marathons before.",
            f"🧓 Vet in a five-setter. {me}'s {age} and knows how to pace a long one.",
            f"🧓 Best of 5 is a grown folks' match. {me} has seen every version of this.",
            f"🧓 Five sets rewards patience, and {me}'s got {age} years of it."])
    if b_me >= 10 and b_me >= 3 * (b_them + 1):
        return v.say("t_life_big", [
            f"🧓 Vet move — {he}'s been in {b_me} of these big matches, {them}'s been in {b_them}.",
            f"🧓 {me} has played {b_me} Slam / late-round matches. {them}? {b_them}. The moment won't be too big.",
            f"🧓 Big-stage reps: {me} {b_me}, {them} {b_them}. {He}'s been here, done this.",
            f"🧓 {b_me} big matches on {his} résumé vs {b_them} for {them}. Experience shows up when it's tight."])
    if a_me is not None and a_me < TEEN:
        age = int(a_me)
        return v.say("t_life_teen", [
            f"🔥 {age} years old and hungry.",
            f"🔥 {me} is {age} and playing with zero fear.",
            f"🔥 A {age}-year-old with nothing to lose. {He} swings free.",
            f"🔥 {age} and still getting better every week. The price hasn't caught up."])
    if x_me >= 100 and x_me >= 3 * max(x_them, 1):
        return v.say("t_life_exp", [
            f"🧓 {me} has {x_me} tour matches under {his} belt, {them} has {x_them}. Experience matters.",
            f"🧓 {x_me} tour matches vs {x_them}. {me} has seen every trick {them} is about to try.",
            f"🧓 Mileage: {me} {x_me} matches, {them} {x_them}. That gap is real."])
    if a_me is not None and a_them is not None and a_them - a_me >= 8:
        return v.say("t_life_young", [
            f"⚡ Fresh legs — {me} is {int(a_them - a_me)} years younger than {them}.",
            f"⚡ {me} is {int(a_me)}, {them} is {int(a_them)}. Youth gets to every ball.",
            f"⚡ The younger legs win the long rallies. {me} has {int(a_them - a_me)} years on {them}."])
    return ""


# every tennis line as skeletons + slots (sports_vocab): thousands of ways to say each one
T_SPREAD_DOG = [
    "{me} +{h} games. [Even if {he} drops the match, we still cash as long as it's close.|{He} can lose and we still cash, long as it stays within {h}.|{Book} thinks {he} gets blown out. Nah.] {kick}",
    "Taking the games with {me} (+{h}). [{them} ain't blowing {him} out.|{He} only needs to hang around.|Close still cashes for us.] {kick}",
    "{me} getting {h} games? [That's {cheap}.|{Book} got this one {cheap}.|We'll take that all day.] {kick}",
    "Game spread: {me} +{h}. {Algo} has {him} covering {pct}% of the time. {kick}",
    "We want {me} with the cushion (+{h}). [{He}'s way more dangerous than this number says.|{them} is priced like it's a walkover. It's not.] {kick}",
    "{h} games of cushion with {me}? [Yes please.|Say less.|Sign us up.] {kick}",
    "Give us {me} and the {h} games. [{He} steals a set and this is basically over.|This stays tight and tight pays us.] {kick}",
    "{me} +{h} is the angle. [{Algo} has {him} hanging around way more than {book} thinks.|The cushion does the heavy lifting.] {kick}",
    "Plus {h} games with {me}. [{them} has to win big to beat us, and we don't see it.|A {pct}% cover in our numbers.] {kick}",
    "[Cushion play|Games play|Spread play]: {me} +{h}. [{He} keeps it close, we eat.|Lose close, still cash.|Tight match, paid ticket.] ",
    "{Book} is giving {me} {h} games and {algo} says {he} barely needs them. {kick}",
    "We're on {me} +{h}. [Blowout? Not in our numbers.|{them} winning by {h}+? We don't see it.] {kick}",
]
T_SPREAD_FAV = [
    "{me} {hc} games. [{He} should roll this by more than {gn}.|{gn} games is nothing for {him} in this spot.] {kick}",
    "Why lay {ml}? We take {me} {hc} games. [{He} wins big and we get paid better for it.|Better price, same result.] {kick}",
    "Skipping the {ml} tax — {me} {hc} games. {kick}",
    "{me} on the game spread ({hc}). [{Algo} has {him} cooking.|This ain't a match, it's a clinic.] {kick}",
    "Better price: {me} {hc} games instead of {ml}. [{them} is about to get run off the court.|We expect a beatdown.] ",
    "No {ml} nonsense. {me} {hc} games, covering {pct}% of the time in our numbers. {kick}",
    "We'd rather have {me} {hc} games than pay {ml}. [{He}'s about to smack that ass by more than {gn}.|Blowout loading.] ",
    "{me} {hc}. [The moneyline's too pricey, the games ain't.|Laying games beats laying juice here.] {kick}",
    "Games over juice: {me} {hc}. {He} {wins} by a bunch, [we think|{algo} says]. {kick}",
    "{me} {hc} games — [{them} doesn't keep this close.|{gn} ain't enough cushion for {them}.] {kick}",
]
T_FAV = [
    "{me} is {better} and it ain't close. [{kick}|Big price, but {he} {wins} {more}.]",
    "{me} runs this. [{Algo} gives {him} {pct}%.|The price is steep for a reason.] {kick}",
    "{me}, {sure}. [{He}'s about to smack that ass.|Nothing fancy — the better player wins.] {kick}",
    "{me} is on a different level than {them}. [Pay the price, collect.|We ain't overthinking this one.] {kick}",
    "This is {me}'s match to lose. {Algo} has {him} at {pct}%. {kick}",
    "{me} should {beat} {them}. [{them}'s about to get {his} cheeks clapped.|Simple as that.] {kick}",
    "Give me {me}. [{He} {wins} {more}.|Big number, bigger gap.] {kick}",
    "{me} takes care of business here. [{Algo} ain't scared of the price.|{pct}% in our numbers.] {kick}",
    "{them} doesn't have the tools for {me}. {kick}",
    "Levels to this — {me} is a tier above {them}. {kick}",
    "[Favorite for a reason|Heavy favorite, earned it]: {me}. {He} should {beat} {them}. {kick}",
    "{me} over {them}. [We're paying up because {he}'s {better}.|Steep price, steeper gap.] {kick}",
    "Not much to it: {me} {wins}. [{Algo} has it {pct}%.|{sure}.] {kick}",
    "{me} is too much for {them}. [{kick}|The better player {wins} {more}.]",
]
T_SMALLFAV = [
    "We [riding|rolling with|backing] {me}. [{Book}'s got this priced kinda close — it ain't.|The price is {cheap}.] {kick}",
    "{me}, {sure}. [{Book}'s sleeping on {him}.|{Algo} likes {him} way more than {book} does.] {kick}",
    "Give me {me}. [{He}'s about to take care of business.|It's {his} world, {them} just living in it.] {kick}",
    "{me} is the pick. Only {o}? [{Algo} has {him} winning way more than that.|That's {cheap}.] {kick}",
    "Hammer {me}. [{Book} don't respect {him} at {o}.|{o} is a discount for this matchup.] {kick}",
    "{me} nice nice. [{He}'s about to go off.|The number should be way bigger.] {kick}",
    "Siding with {me} here. [{Algo} has {him} at {pct}%. The price doesn't.|This line is off and we're taking it.] {kick}",
    "{me} gets the W. [{o} is {cheap}.|{Book} made this a coin flip. It's not.] {kick}",
    "Put us down for {me}. [{He} {wins} {more}.|{pct}% in our numbers at {o}.] {kick}",
    "{me} is the play in this one. [{Book} has it close, {algo} doesn't.|{them} is getting too much respect.] {kick}",
    "We like {me} a lot here. {o} is [{cheap}|a gift for how good {he} is]. {kick}",
    "{me} over {them} at {o}. [That price should be steeper.|{Algo} doesn't see a close match.] {kick}",
    "[Small favorite|Light favorite], big gap: {me}. {kick}",
    "{Book} barely has {me} favored. {Algo} has {him} well clear. {kick}",
]
T_DOG = [
    "{me} is the dog at {o}? Nah. [{Algo}'s got {him} as {better}.|The price is wrong and we're taking it.] {kick}",
    "{me} at {o} is a gift. [{He}'s about to cook.|{He} {wins} {more}.] {kick}",
    "We'll take {me} plus money all day. [{Book} got this one backwards.|{them} is getting too much respect.] {kick}",
    "{me} gets the nod. [{Algo} says {he}'s the one about to win.|Our number has {him} winning {pct}%.] {kick}",
    "Plus money on {me}? Say less. {kick}",
    "Underdog on paper, not in our numbers — {me}. {kick}",
    "{me} plus money, we're in. [{Book} has the wrong favorite.|{pct}% for {him} in our numbers.] {kick}",
    "{Book} made {me} the dog. {Algo} disagrees. {kick}",
    "Getting paid to take {better}? {me} at {o}. {kick}",
    "{me} {o}. [Dog price, favorite game.|The upset ain't an upset to us.] {kick}",
]
T_RANK = [
    "{me} is #{rk} in the world, {them} is {vs}. [Levels to this.|Not the same tier.|]",
    "World #{rk} vs {vs}. [Different weight class.|That gap shows up on the big points.|]",
    "Ranking gap: #{rk} vs {vs}. [{them} is punching up.|Those numbers ain't an accident.|]",
    "{He}'s #{rk} for a reason — {them} is {vs}.",
    "#{rk} against {vs}. [{them}'s about to get {his} cheeks clapped.|Not close on paper.|]",
    "On paper it's #{rk} vs {vs}. [The paper's right.|]",
    "The rankings say #{rk} vs {vs}. [That's a real gap.|Levels.|]",
    "{me} sits at #{rk}. {them}? {Vs}.",
    "Tour ranking: {me} #{rk}, {them} {vs}. [Big gap.|]",
]
T_HOME = [
    "{me} is playing at home. [The whole building got {his} back.|Everybody in there is with {him}.|]",
    "Home soil for {ours}. [{Crowd} gonna carry {him}.|]",
    "Home cookin'. [{He}'s got {crowd} behind {him}.|]",
    "{me} gets the home crowd. [Every big point gets louder for our side.|]",
    "{me}'s in front of {his} own people. [{them} is playing {crowd} too.|]",
    "Home match for {me}. [That's worth a few points.|]",
]
T_DRAMA = [
    "{them} got stuff going on off the court ({k}). [Head ain't gonna be right.|]",
    "Off-court noise for {them} ({k}). [That follows you onto the court.|]",
    "{them} dealing with {k}. [Distracted players lose — period.|Hard to lock in with that going on.]",
    "{them} has {k} hanging over {him}. [Tough to focus through that.|]",
]
T_CLASH = [
    "Bad blood between these countries. [No handshake energy.|Pressure match.]",
    "This one's personal between their countries. [Heat on every point.|]",
    "There's history between these flags. [Nerves are gonna show.|]",
    "Country beef on the court tonight. [Pressure on every point.|]",
]
T_SURF = [
    "{He}'s a different animal on {surf}. [That's {his} surface.|]",
    "On {surf}, {me} is on a whole nother caliber. [There's levels to this shit.|]",
    "{Surf} is {his} playground. [{He} lives here.|]",
    "Put {him} on {surf} and {he} turns into a problem.",
    "{me}'s game was built for {surf}. [The results back it up.|]",
    "{me} on {surf} hits different. [{them} doesn't see this version of {him} anywhere else.|]",
    "{Surf} suits {me} perfect. [{His} numbers jump on it.|]",
]
T_SURF_OPP = [
    "{them} ain't the same player on {surf}. [That's our edge.|]",
    "{Surf} exposes {them}. [That game don't travel.|]",
    "{them} on {surf}? Booty cheeks. [We're taking advantage.|]",
    "{them} is complete ass on {surf}. [We're eating.|]",
    "{them}'s game falls off on {surf}. [The numbers show it.|]",
    "{Surf} ain't {them}'s thing. [Wrong surface, wrong matchup.|]",
    "{them} has never figured out {surf}.",
]
T_TIRED = [
    "{them} has been grinding long matches all week. [{Tired}.|]",
    "{them} played a ton of tennis lately. [{Tired} incoming.|]",
    "{them}'s coming off marathon matches. [{Ours} is fresher.|]",
    "{them} is running on fumes. [{Ours}'s about to make {them} work every point.|]",
    "Heavy mileage on {them} this week. [That catches up by the third set.|]",
    "{them} has logged way more court time than {me}. [{Tired} + a better player across the net? {them}'s about to get {his} cheeks clapped.|]",
    "{them} hasn't had an easy match in days. [{Tired}.|]",
]
T_FORM = [
    "{He}'s been {hot} lately and {them} has been {cold}.",
    "Form says {me}. [{He}'s been cooking.|]",
    "{me} is {hot} right now. [{them} can't say the same.|]",
    "{He}'s on a heater. [Don't fade the heater.|]",
    "{me}'s been stacking W's while {them} keeps taking L's.",
    "Recent results are all {me}. [Momentum is real in this sport.|]",
    "{me} came in playing {his} best tennis. [{them} has been {cold}.|]",
]
T_H2H = [
    "{me} owns this matchup. [History's on our side.|]",
    "{them} has had trouble with {me} in the past. [Same script tonight.|]",
    "{me} got {them}'s number.",
    "{them} couldn't handle {him} last time either. [Run it back.|]",
    "Head to head leans {me}. [Matchups matter.|]",
    "{me} has already beaten {them}. [{them} already got {his} cheeks clapped by {me} before.|]",
    "{them} has seen this movie before. [It ends the same.|]",
]
T_BO5 = [
    "Best of 5 at a Slam. [The longer it goes, the more the better player takes over.|]",
    "Five sets. [{them} has nowhere to hide.|Better player wins these.]",
    "Slam rules — best of 5. [Upsets get a lot harder over five.|]",
    "Long format tonight. [Three sets to win means the better player gets there.|]",
]
T_BOTTOM = [
    "[Bottom line|The play|Where we land|The numbers|Final word|The bet|How we see it|Sum it up|The math|Net-net]: {book} says {bk}%, we say {pct}%. {bet} ({od}). [{kick}|{gap}]",
    "[Bottom line|The play|The math|The bet]: {Book} {bk}%, us {pct}%. {bet} ({od}). {kick}",
    "[Where we land|Final word|Net-net]: {pct}% for us, {bk}% for {book}. {bet} ({od}). [{gap}|{kick}]",
    "[The play|The bet|Bottom line]: {bet} ({od}). We got it at {pct}%, the price only implies {bk}%. {kick}",
    "[The numbers|The math|How we see it]: {bet} ({od}) — {pct}% vs {book}'s {bk}%. [{gap}|{kick}]",
    "[Sum it up|Final word]: {bet} at {od}. {pct}% on our side of the ledger, {bk}% on theirs. {kick}",
    "[Bottom line|Net-net]: {algo} {pct}%, {book} {bk}%. {bet} ({od}). [{gap}|{kick}]",
    "[The play|Where we land]: {bk}% says {book}, {pct}% says {algo}. {bet} ({od}). {kick}",
    "[The bet|The math]: {book} wants {bk}%, {algo} sees {pct}%. {bet} ({od}). [{gap}|{kick}]",
    "[How we see it|Bottom line]: {bet} ({od}). {Book} implies {bk}%. We're at {pct}%. {kick}",
    "[Final word|The play]: {pct} vs {bk}. {bet} ({od}). [{gap}|{kick}]",
    "[Net-net|Sum it up]: we make it {pct}%, the price makes it {bk}%. {bet}, {od}. {kick}",
    "[The numbers|The bet]: {bet} {od}. Implied {bk}%, ours {pct}%. {kick}",
    "[Where we land|The math]: {bet} ({od}), {pct}% in {algo} against a {bk}% price. [{gap}|{kick}]",
]
T_BOTTOM_AGREE = [                               # the book and our number land together (the anchored win %)
    "[Bottom line|The play|Where we land|The bet]: {book} has it at {bk}% and we're right there. {bet} ({od}). {kick}",
    "[Bottom line|Net-net|The math]: {pct}% to cash, {book} agrees. {bet} ({od}). {kick}",
    "[The numbers|How we see it]: {bet} ({od}). {Book} and {algo} both land near {pct}%. {kick}",
    "[Final word|Sum it up]: {bet} at {od}. {pct}% to hit, and we ain't fighting the line. {kick}",
    "[The play|The bet]: {bet} ({od}), {pct}% in our numbers, same story as the price. {kick}",
    "[Where we land|The math]: {bet} ({od}). No fighting {book} here, {pct}% to cash. {kick}",
]
BRAG = re.compile(r"sleeping|price doesn't|line is off|cheap|discount|coin flip|steeper\.|big gap|well clear|respect|"
                  r"kinda close|way more|has it close|barely|backwards|wrong favorite|disagrees|price is wrong|gift")


CAP = {"t_sd": 105, "t_sf": 105, "t_mf": 90, "t_mm": 90, "t_md": 90, "t_bl": 105}   # max chars per line (names as 4)


def breakdown(c, rt, used):
    """Tennis breakdown in OUR voice (he/she by tour, last names). Every line is rolled from skeletons + our
    vocabulary (sports_vocab), and no 4-word run repeats on the board or from yesterday's slate."""
    import sports_breakdown as sb
    import sports_vocab as vb
    me, them, f = _say_name(c["player"]), _say_name(c["opp"]), c["f"]
    v = sb.Voice(c["id"], used, names=(me, them))
    wta = c.get("tour") == "wta"
    he, him, his = ("she", "her", "her") if wta else ("he", "him", "his")
    ours = "our girl" if wta else "our guy"
    surf = SURF[c["surface"]].lower()
    kw = dict(me=me, them=them, he=he, him=him, his=his, He=he.capitalize(), His=his.capitalize(), ours=ours,
              Ours=ours.capitalize(), surf=surf, Surf=surf.capitalize(), pct=round(100 * (c.get("p") or 0.5)))

    def roll(key, emoji, templates, must=False, **more):
        cap = CAP.get(key, 90)                          # never longer than the old write-ups: new words, same size
        opts = [x for x in vb.variants(templates, f"{c['id']}|{key}", 80, **kw, **more)
                if len(x.replace(me, "Name").replace(them, "Name")) <= cap]
        x = v.say(key, opts, must=must)
        return f"{emoji} {x}" if x else ""

    # the book's % = its NO-VIG chance when we have both prices (else the plain implied %); our % = the anchored
    # win % (c["p"]) - when they land together (new slates) the write-up says so instead of bragging about a gap
    bk = round(100 * c["mkt"]) if c.get("mkt") is not None else round(100 / sd.decimal(c["odds"])) if c.get("odds") else 0
    agree = c.get("mkt") is not None and kw["pct"] - bk < 3
    out = []
    if c.get("market") == "spread" and c["hcp"] > 0:
        out.append(roll("t_sd", "🎯", T_SPREAD_DOG, must=True, h=f"{c['hcp']:g}"))
    elif c.get("market") == "spread":
        out.append(roll("t_sf", "🎯", T_SPREAD_FAV, must=True, hc=f"{c['hcp']:+g}", gn=f"{abs(c['hcp']):g}",
                        ml=f"{c['ml']:+d}"))
    else:
        o = c.get("odds") or c.get("ml") or -110
        calm = (lambda ts: [x for x in ts if not BRAG.search(x)] or ts) if agree else (lambda ts: ts)
        if o <= -150:
            out.append(roll("t_mf", "🎾", T_FAV, must=True, o=f"{o:+d}"))
        elif o < 0:
            out.append(roll("t_mm", "🎾", calm(T_SMALLFAV), must=True, o=f"{o:+d}"))
        else:
            out.append(roll("t_md", "🎾", calm(T_DOG), must=True, o=f"{o:+d}"))
    rk_me, rk_them = c.get("rank"), c.get("opp_rank")
    if rk_me and (not rk_them or rk_them - rk_me >= 20):
        vs = f"#{rk_them}" if rk_them else "outside the top 150"
        out.append(roll("t_rank", "📈", T_RANK, rk=rk_me, vs=vs, Vs=vs[:1].upper() + vs[1:]))
    if f.get("home", 0) > 0:
        out.append(roll("t_home", "🏟️", T_HOME))
    if c.get("their_drama"):
        out.append(roll("t_drama", "🍿", T_DRAMA, k=c["their_drama"][0]["kind"]))
    if f.get("clash"):
        out.append(roll("t_clash", "🔥", T_CLASH))
    if f["surface_gap"] >= 40:
        out.append(roll("t_surf", "🟫", T_SURF))
    elif f["surface_gap"] <= -40:
        out.append(roll("t_surf_opp", "🟫", T_SURF_OPP))
    if f["fatigue"] >= 0.66:
        out.append(roll("t_tired", "😮‍💨", T_TIRED))
    if f["form"] >= 0.2:
        out.append(roll("t_form", "🔥", T_FORM))
    if f["h2h"] >= 0.33:
        out.append(roll("t_h2h", "🆚", T_H2H))
    if int(c["bo"]) == 5:
        out.append(roll("t_bo5", "🏆", T_BO5))
    out.append(life_line(v, c, me, them, he, he.capitalize(), his))
    if c.get("odds"):
        bet = f"{me} {c['hcp']:+g} games" if c.get("market") == "spread" else f"{me} ML"
        out.append(roll("t_bl", "✅", T_BOTTOM_AGREE if agree else T_BOTTOM, must=True, bk=bk, bet=bet,
                        od=f"{c['odds']:+d}"))
    c["_vk"] = list(v.mine)
    return [x for x in out if x]


# ---------------------------------------------------------------- picks
def _load_picks():
    if os.path.exists(PICKS):
        with open(PICKS) as f:
            return json.load(f)
    return []


_TRUST = {}


def trust(tour, path=None):
    """How far the tour's win % may lean from the book's no-vig price toward our own number (0 = the book's)."""
    path = path or TIER
    if path not in _TRUST:
        try:
            with open(path) as f:
                _TRUST[path] = json.load(f).get("trust") or {}
        except (OSError, ValueError):
            _TRUST[path] = {}
    try:
        return min(1.0, max(0.0, float(_TRUST[path].get(tour_of(tour), TRUST))))
    except (TypeError, ValueError):
        return TRUST


def fair(ml, other):
    """This side's NO-VIG chance from the two prices (the book's margin taken out)."""
    a, b = 1 / sd.decimal(ml), 1 / sd.decimal(other)
    return a / (a + b)


def anchor(mkt, own, t):
    """The win % we post: the book's no-vig chance, nudged toward our own number by the learned trust."""
    return min(max(mkt + t * (own - mkt), 0.01), 0.99)


def _angle(c, st=None):
    """(win %, proven?) - a study-PROVEN angle (sports_tennis_edge) nudges the anchored number; none proven = as is."""
    try:
        import sports_tennis_edge as ste
        st = ste.load() if st is None else st
        if not ste.proven(st):
            return c["p"], False
        q = ste.adjust(st, {"tour": c["tour"], "surface": c.get("surface"), "round": c.get("round"), "bo": c.get("bo"),
                            "date": (c.get("start") or "")[:10], "p": c.get("mkt"), "rank": c.get("rank"),
                            "opp_rank": c.get("opp_rank")}, c["p"])
        return q, q > c["p"]
    except Exception:                                                    # noqa: BLE001 - never block tennis
        return c["p"], False


def mkt_of(c):
    """The book's chance for this bet: the no-vig price (candidates carry it), else the plain implied chance."""
    return c["mkt"] if c.get("mkt") is not None else 1 / c["dec"]


def fighting(c):
    """Our own read has this side 3+ points UNDER what the book says: the engine is fighting the line - never a pick."""
    own = c.get("own", c["p"])
    return own < mkt_of(c) - FIGHT_MAX


OVERHYPE_MAX = 0.06            # the study (newer half): favorites the engine liked 6+ points MORE than the book hit 2-3
                               # points BELOW the book's own number - the engine overhyping; skip those too (owner: tighten up)


def overhyped(c):
    """Our own read has this side 6+ points OVER the book's number: the engine's overhyping it - never a pick."""
    return c.get("own", c["p"]) > mkt_of(c) + OVERHYPE_MAX


def good(c):
    """A real tennis play: likely to WIN by the anchored win % (55%+; our own drama on it: 57%+), never fighting the
    line, no moneyline shorter than -300, and an underdog (the book has it under 50%) only with a PROVEN angle and
    real value. The engine's disagreement with the book is never a reason by itself."""
    if fighting(c) or overhyped(c):
        return False
    if c.get("market", "ml") == "ml" and c["odds"] < MAX_FAV:
        return False
    if c["odds"] >= 100 or mkt_of(c) < 0.5:
        return bool(c.get("angle")) and c["edge"] >= MIN_EDGE
    return c["p"] >= MIN_P + (0.02 if c.get("our_drama") else 0.0)


def candidates(ms, rt, w, lines, now, until, ranks=None, news=None, gm=None):
    out = []
    gm = gm or {}
    ranks, news = ranks or {}, news or {}
    try:
        import sports_tennis_edge as ste
        st_edge = ste.load()
    except Exception:                                                    # noqa: BLE001 - never block tennis
        st_edge = {}
    for m in ms.values():
        if _state(m) != "pre" or not m["start"]:
            continue
        t = _t(m["start"])
        if not (now + timedelta(minutes=MIN_LEAD_MIN) <= t <= until):
            continue
        full = price(m, lines, full=True)
        f = rt.features(m, when=now.strftime("%Y-%m-%dT%H:%M"))
        if not full or f["known"] < MIN_MATCHES:
            continue
        pr, sp = full["ml"], full["sp"]
        tour = tour_of(m)
        t = trust(tour)
        e1 = model_p(w, f, m["bo"], tour)                       # our own number (the tour's own weights)
        for side, own, ml, opp_ml in ((1, e1, pr[0], pr[1]), (2, 1 - e1, pr[1], pr[0])):
            mkt = fair(ml, opp_ml)
            p = anchor(mkt, own, t)                             # the win % we post: anchored to the book
            me, them = (m["p1_name"], m["p2_name"]) if side == 1 else (m["p2_name"], m["p1_name"])
            fs = f if side == 1 else flip_features(f)
            dec = sd.decimal(ml)
            mine, theirs = (m["p1"], m["p2"]) if side == 1 else (m["p2"], m["p1"])
            mine, theirs = f"{tour}:{mine}", f"{tour}:{theirs}"          # ranks + news are keyed per tour
            out.append({"id": f"{m['id']}:{side}", "match": m["id"], "side": side, "player": me, "opp": them,
                        "tour": tour,
                        "rank": ranks.get(mine), "opp_rank": ranks.get(theirs),
                        "our_drama": (news.get(mine) or [])[:1], "their_drama": (news.get(theirs) or [])[:1],
                        "odds": ml, "dec": dec, "p": p, "edge": p * dec - 1, "start": m["start"], "tourney": m["tourney"],
                        "round": m["round"], "surface": m["surface"], "bo": m["bo"], "f": fs, "market": "ml", "hcp": None,
                        "ml": ml, "win_p": p, "mkt": mkt, "own": own})
            c = out[-1]
            c["p"], c["angle"] = _angle(c, st_edge)
            c["edge"] = c["p"] * dec - 1
            c["win_p"] = c["p"]
            if sp and games_for(gm, tour):
                hcp, sodds = sp[side - 1]
                g = games_for(gm, tour)
                pc_own = cover_p(g, own, hcp, m["bo"])          # our own cover chance (from our own win %)
                if pc_own is not None and sp[2 - side][1]:
                    sdec = sd.decimal(sodds)
                    smkt = fair(sodds, sp[2 - side][1])         # the book's no-vig cover chance
                    pc = anchor(smkt, pc_own, t)                # anchored to the spread's own price
                    out.append({**c, "id": f"{m['id']}:{side}:sp", "market": "spread", "hcp": hcp, "odds": sodds,
                                "dec": sdec, "p": pc, "edge": pc * sdec - 1, "mkt": smkt, "own": pc_own,
                                "angle": False})
    return out


def pick_slate(cands):
    """Up to 6 men's + 6 women's straights we expect to WIN (good(): the anchored win % 55%+, never fighting the line,
    no dogs without a proven angle), likeliest first, and one parlay per tour (the 3 likeliest of that tour; a tour
    with fewer than 3 picks gets none). Never a mixed parlay, never filler. Returns (picks, {"atp": [...], "wta": [...]})."""
    for c in cands:
        c["value"] = c["edge"] >= MIN_EDGE                      # shown, never the reason
    cands = [c for c in cands if good(c)]
    best = {}
    for c in sorted(cands, key=lambda c: -c["p"]):
        best.setdefault(c["match"], c)                          # one side per match (the likelier bet: ML or spread)
    ranked = sorted(best.values(), key=lambda c: -c["p"])
    by = {t: [c for c in ranked if tour_of(c) == t][:N_PER_TOUR] for t in TOURS}   # each tour on its own: up to 6
    picks = sorted(by["atp"] + by["wta"], key=lambda c: -c["p"])                 # (one tour short = fewer picks)
    parlays = {t: (by[t][:PARLAY_LEGS] if len(by[t]) >= PARLAY_LEGS else []) for t in TOURS}
    return picks, parlays


def _parlay(legs):
    dec = 1.0
    for c in legs:
        dec *= c["dec"]
    return {"legs": [c["id"] for c in legs], "dec": round(dec, 4), "american": round((dec - 1) * 100) if dec >= 2
            else round(-100 / (dec - 1)), "status": "open", "tour": tour_of(legs[0])}


def parlays_of(slate):
    """[(key, parlay)] of a slate: 'atp' / 'wta' (new slates, one per tour) and 'mixed' (an old slate's single parlay
    of both tours - it keeps its own label and never counts in a tour's record)."""
    out = [("mixed", slate["parlay"])] if slate.get("parlay") else []
    return out + [(t, p) for t, p in (slate.get("parlays") or {}).items() if p]


def post(ms, rt, w, lines, picks, now, gm=None):
    """Post the day's tennis slate once (from 6pm PT the night before: the next 24 hours of matches)."""
    local = now.astimezone(PT)
    day = (local + timedelta(days=1)).date() if local.hour >= POST_FROM_HOUR_PT else local.date()
    iso = day.isoformat()
    if any(p["date"] == iso for p in picks):
        return None
    cands = candidates(ms, rt, w, lines, now, now + timedelta(hours=24), rankings(now) if lines else {},
                       news_sync(now) if lines else {}, gm)
    already = {l.get("match") or l["id"] for p in picks for l in p.get("picks") or []}   # a MATCH already on a slate
    cands = [c for c in cands if (c.get("match") or c["id"]) not in already]            # never goes up twice (any bet)
    straights, parlays = pick_slate(cands)
    if not straights:
        return None
    used = _used()   # no phrase repeats anywhere on the dashboard
    legs = [_leg(c, rt, used) for c in straights]
    slate = {"date": iso, "posted": now.strftime("%Y-%m-%dT%H:%MZ"), "picks": legs,
             "parlays": {t: (_parlay(ls) if ls else None) for t, ls in parlays.items()}}   # one per tour, never mixed
    picks.append(slate)
    return slate


LEG_KEYS = ("id", "match", "side", "player", "opp", "tour", "odds", "p", "edge", "start", "tourney", "market", "hcp", "ml",
            "round", "surface", "bo", "value", "mkt", "own", "angle")


def _leg(c, rt, used):
    bd = breakdown(c, rt, used)
    return {k: c.get(k) for k in LEG_KEYS} | {"result": None, "breakdown": bd, "bv": TENNIS_BV, "vk": c.get("_vk") or []}


ASK_PATH = "docs/sports/reads_tennis.json"
ASK_STEEP = -300


def reads(ms, rt, w, lines, picks, now, gm=None):
    """The question box for tennis: our read on every match in the next 24 hours (not our picks, never in the record)."""
    cands = candidates(ms, rt, w, lines, now, now + timedelta(hours=24), gm=gm)
    by_id = {c["id"]: c for c in cands}
    redo = {(l["id"], l.get("side"), l.get("market")) for sl_ in picks[-2:] for l in sl_.get("picks") or []
            if l.get("bv") != TENNIS_BV and not l.get("result") and l["id"] in by_id}
    used = _used(redo)   # no phrase repeats anywhere on the dashboard
    for sl_ in picks[-2:]:                                   # older breakdowns get rewritten before the match
        for l in sl_.get("picks") or []:
            if l.get("bv") != TENNIS_BV and not l.get("result") and l["id"] in by_id:
                # a posted pick keeps its posted numbers (win %, book %): only the words get rewritten
                c = {**by_id[l["id"]], **{k: l.get(k) for k in ("p", "edge", "odds", "hcp", "market", "mkt")}}
                l["breakdown"], l["bv"] = breakdown(c, rt, used), TENNIS_BV
                l["vk"] = c.get("_vk") or []
    ours = {l["match"] for s in picks[-3:] for l in s.get("picks") or [] if not l.get("result")}
    by = {}
    for c in cands:
        by.setdefault(c["match"], []).append(c)
    out = []
    for mid, cs in by.items():
        ok = [c for c in cs if c["odds"] >= ASK_STEEP] or cs
        c = max(ok, key=lambda c: (c["p"], c["edge"]))                 # accuracy first: the likelier bet
        why = ("on_board" if mid in ours else "steep" if c["odds"] < ASK_STEEP else "coin_flip" if c["p"] < 0.55
               else "tight" if good(c) else "no_value")
        out.append({"id": f"tennis:{mid}", "league": "tennis", "emoji": "🎾",
                    "sport": "Women's Tennis" if c.get("tour") == "wta" else "Men's Tennis", "start": c["start"],
                    "away": c["player"], "home": c["opp"], "vs": True, "why": why, "board": None, "h1": None,
                    "lean": {"team": c["player"], "opp": c["opp"], "market": c.get("market", "ml"), "line": c.get("hcp"),
                             "odds": c["odds"], "p": round(c["p"], 3), "win_p": round(c.get("win_p", c["p"]), 3),
                             "reasons": [x for x in (c.get("surface") and f"on {SURF.get(c['surface'], c['surface'])}",
                                                     c.get("tourney")) if x]}})
    out.sort(key=lambda r: r["start"])
    os.makedirs(os.path.dirname(ASK_PATH), exist_ok=True)
    with open(ASK_PATH, "w") as f:
        json.dump({"updated": now.strftime("%Y-%m-%dT%H:%MZ"), "games": out}, f, indent=1)
    return out


REPICK = os.path.join(DIR, "repick.json")      # {"date": ...}: re-pick that slate once under the current rules (owner's OK)


def repick(ms, rt, w, lines, picks, now, gm=None):
    """Re-pick a posted slate under the current rules - only matches that haven't started; started/graded picks stay."""
    try:
        with open(REPICK) as f:
            want = json.load(f).get("date")
    except (OSError, ValueError):
        return None
    slate = next((sl for sl in picks if sl["date"] == want), None)
    if not slate or not lines:
        return None
    soon = now + timedelta(minutes=MIN_LEAD_MIN)
    keep = [l for l in slate["picks"] if l.get("result") or _t(l["start"]) <= soon]
    cands = [c for c in candidates(ms, rt, w, lines, now, now + timedelta(hours=24), gm=gm)
             if c["match"] not in {l["match"] for l in keep}]
    straights, parlays = pick_slate(cands)
    used = _used()   # no phrase repeats anywhere on the dashboard
    new = []
    for t in TOURS:                                         # each tour tops up to its own 6
        room = max(0, N_PER_TOUR - sum(tour_of(l) == t for l in keep))
        new += [_leg(c, rt, used) for c in straights if tour_of(c) == t][:room]
    old = [l["player"] for l in slate["picks"]]
    slate["picks"] = keep + new
    new_ids = {l["id"] for l in new}

    def untouched(par):                                     # no leg of it has started yet
        return all(_t(l["start"]) > soon for l in slate["picks"] if l["id"] in (par or {}).get("legs", []))
    if slate.get("parlay") and not untouched(slate["parlay"]):
        pass                                                # an old mixed parlay already going: it stays as posted
    else:
        slate.pop("parlay", None)
        pars = slate.setdefault("parlays", {})
        for t in TOURS:
            if not pars.get(t) or untouched(pars[t]):
                ls = parlays.get(t) or []
                pars[t] = _parlay(ls) if ls and all(c["id"] in new_ids for c in ls) else None
    slate["repicked"] = now.strftime("%Y-%m-%dT%H:%MZ")
    os.remove(REPICK)
    print(f"tennis re-pick {want}: {old} -> {[l['player'] for l in slate['picks']]}")
    return slate


def quick_grade(rows=None):
    """Grade the posted tennis picks right now from ESPN's scoreboards (yesterday / today / tomorrow - Asia's matches
    sit on the next day's) without running the whole tennis engine. The live watcher calls it the moment one of our
    matches finishes, so a finished match never sits ungraded. Returns how many legs got graded."""
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    picks = _load_picks()
    if rows is None:
        rows, now = [], _dt.now(_tz.utc)
        for tour in TOURS:
            for d in (-1, 0, 1):
                try:
                    data, _ = _get(ESPN.format(tour=tour) + f"?dates={(now + _td(days=d)):%Y%m%d}")
                    rows += parse_espn(data, tour)
                except Exception as e:                   # noqa: BLE001
                    print(f"tennis quick grade: espn {tour} {d}: {str(e)[:60]}")
    ms = {r["id"]: r for r in rows}
    before = sum(1 for s_ in picks for l in s_.get("picks") or [] if l.get("result"))
    grade(ms, picks)
    after = sum(1 for s_ in picks for l in s_.get("picks") or [] if l.get("result"))
    if after != before:
        with open(PICKS, "w") as f:
            json.dump(picks[-120:], f, indent=1)
    return after - before


def grade(ms, picks):
    for s in picks:
        for leg in s["picks"]:
            if leg["result"]:
                continue
            m = ms.get(leg["match"]) or ms.get(f"atp:{leg['match']}")         # ids before the WTA came in
            if not m:
                continue
            st = _state(m)
            leg["state"] = st                                  # (the dashboard: LIVE only once it's really being played)
            if st == "void" or (st == "retired" and int(m.get("done") or 0) < 1):
                leg["result"] = "void"
            elif leg.get("market") == "spread" and st == "retired":
                leg["result"] = "void"                              # books void game spreads on a retirement
            elif leg.get("market") == "spread" and st == "final" and margin(m) is not None:
                mg = margin(m) if leg["side"] == 1 else -margin(m)
                leg["result"] = "won" if mg + leg["hcp"] > 0 else "lost" if mg + leg["hcp"] < 0 else "push"
                leg["score"] = _score_txt(m)
            elif st in ("final", "retired") and int(m["winner"] or 0) in (1, 2):
                leg["result"] = "won" if int(m["winner"]) == leg["side"] else "lost"
                leg["score"] = _score_txt(m)
        for _, par in parlays_of(s):                       # old slates: one mixed parlay; new: one per tour
            if par["status"] != "open":
                continue
            res = [next((l["result"] for l in s["picks"] if l["id"] == i), None) for i in par["legs"]]
            if "lost" in res:
                par["status"] = "lost"
            elif all(r in ("won", "void", "push") for r in res):
                par["status"] = "won" if "won" in res else "void"


def _score_txt(m):
    a, b = str(m["sets1"]).split(), str(m["sets2"]).split()
    return ", ".join(f"{x}-{y}" for x, y in zip(a, b))


def record(picks):
    """Men's and women's tennis records, apart (a match counts once, even if two slates carry it). Parlays per tour;
    an old slate's mixed parlay only counts under 'mixed'."""
    out = {t: {"won": 0, "lost": 0, "p_won": 0, "p_lost": 0} for t in (*TOURS, "mixed")}
    seen = {}
    for s in picks:
        for l in s["picks"]:
            seen[l.get("match") or l["id"]] = l
        for key, par in parlays_of(s):
            out[key]["p_won"] += par["status"] == "won"
            out[key]["p_lost"] += par["status"] == "lost"
    for l in seen.values():
        out[tour_of(l)]["won"] += l["result"] == "won"
        out[tour_of(l)]["lost"] += l["result"] == "lost"
    return out


def save_prematch(ms, rt, w, lines, now):
    """The last pre-match numbers for every match in the next 36 hours: our win chance (the tour's own weights) and
    the book's no-vig chance. Once a match starts it's no longer 'pre' here, so its entry freezes at the last read
    before the first serve - live tennis starts from these (sports_live)."""
    try:
        with open(PREMATCH) as f:
            snap = json.load(f)
    except (OSError, ValueError):
        snap = {}
    stamp = now.strftime("%Y-%m-%dT%H:%M")
    for m in ms.values():
        if _state(m) != "pre" or not m.get("start"):
            continue
        t = _t(m["start"])
        if not (now - timedelta(hours=2) <= t <= now + timedelta(hours=36)):
            continue
        row = {"tour": tour_of(m), "bo": int(m.get("bo") or 3), "p1": m["p1"], "p2": m["p2"], "p1_name": m["p1_name"],
               "p2_name": m["p2_name"], "start": m["start"], "tourney": m.get("tourney", ""), "seen": stamp}
        f = rt.features(m, when=stamp)
        if w is not None and f["known"] >= MIN_MATCHES:
            row["model_p1"] = round(model_p(w, f, m["bo"], tour_of(m)), 4)
        pr = price(m, lines) if lines else None
        if pr:
            row["mkt_p1"], row["ml"] = round(sd.no_vig(*pr), 4), list(pr)
        snap[m["id"]] = {**snap.get(m["id"], {}), **row}     # (the last price seen stays when the feed has none now)
    cut = (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    snap = {k: v for k, v in snap.items() if v.get("start", "") >= cut}
    os.makedirs(DIR, exist_ok=True)
    with open(PREMATCH + ".tmp", "w") as f:
        json.dump(snap, f, indent=0, sort_keys=True)
    os.replace(PREMATCH + ".tmp", PREMATCH)
    return snap


def run(state, now=None, fetch=True):
    """One tennis cycle; never lets tennis break the main engine (the caller wraps it)."""
    now = now or datetime.now(timezone.utc)
    if fetch:
        ms, calls, fails = sync(state)
        print(f"tennis sync: {len(ms)} matches stored, {calls} calls, {fails} failed")
    else:
        ms = load_matches()
    rt, w, rep = study(ms, players=load_players())
    state["tennis_study"] = rep
    save_study(rep, now)
    for t, r in rep["tours"].items():
        print(f"tennis study {t.upper()}: {r['rated']} rated matches, acc {r['acc']} (surface ratings alone {r['acc_elo']}), "
              f"loss {r['logloss']} vs {r['logloss_elo']}, {'own' if r['own_weights'] else 'SHARED'} weights {r['weights']}")
        lf = r.get("life")
        if lf:
            print(f"tennis study {t.upper()} life factors vs current loss {lf['base']['logloss']}: " + (", ".join(
                f"{k} {v['logloss']} ({v['gain_mnats']:+.2f} mnats, z {v['z']})" if "z" in v else f"{k} (no data)"
                for k, v in lf["factors"].items()) or "not tested") + " -> " + (f"KEPT {'+'.join(lf['kept'])}"
                if lf["kept"] else "none kept (weights 0)") + f" · {lf['graded_with_both_ages']}/{lf['graded']} graded "
                "matches have both ages")
    picks = _load_picks()
    grade(ms, picks)
    lines = refresh_odds(state, now) if fetch else []
    learned = rep["rated"] >= MIN_RATED and rep["weights"] != PRIOR
    try:
        save_prematch(ms, rt, w if learned else None, lines, now)
    except Exception as e:                                              # noqa: BLE001 - never block tennis
        print(f"tennis pre-match snapshot failed: {e}")
    slate = post(ms, rt, w, lines, picks, now, rep.get("games")) if learned else None
    if rep["rated"] < MIN_RATED:
        print(f"tennis: still studying ({rep['rated']}/{MIN_RATED} rated matches) - no picks yet")
    if lines and rep["rated"] >= MIN_RATED:
        try:
            repick(ms, rt, w, lines, picks, now, rep.get("games"))
        except Exception as e:                                          # noqa: BLE001 - never block tennis
            print(f"tennis re-pick failed: {e}")
        try:
            print(f"tennis reads: {len(reads(ms, rt, w, lines, picks, now, rep.get('games')))} matches")
        except Exception as e:                                          # noqa: BLE001 - never block tennis
            print(f"tennis reads failed: {e}")
    if slate:
        print(f"tennis posted {slate['date']}: " + ", ".join(f"{l['player']} {l['odds']:+d}" for l in slate["picks"]))
    os.makedirs(DIR, exist_ok=True)
    with open(PICKS, "w") as f:
        json.dump(picks[-120:], f, indent=1)
    return picks
