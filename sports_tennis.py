"""🎾 TENNIS BONUS: men's (ATP) and women's (WTA) singles picks - a bonus section, never part of the main board or its records.

Every engine run:
  1. Results from ESPN's ATP scoreboard (each call returns whole tournaments, so history is walked a week at a
     time: 10 seasons, a year per run until caught up). Stored in data/sports/tennis/matches.csv.
  2. The study: surface ratings (overall + hard / clay / grass, blended - the proven way to rate tennis players),
     plus learned weights for fatigue (sets played the last 3 days), recent form and head-to-head. Best-of-5 at
     the Slams is handled from the per-set strength. Fit on the history, graded on the latest matches.
  3. Odds: Bovada's public feed (current men's singles moneylines), refreshed every run.
  4. Once a day (from 6pm Pacific the night before, the next 24 hours of matches): 8 straight picks - value first
     (our win chance beats the price by 2%+; big favorites are fine in tennis), then the likeliest favorites fill
     it - and a Tennis Parlay of the Day (the 3 likeliest of them). Posted picks are final. Retirements: void if
     no set was finished, otherwise the player who advances wins it; walkovers are void.
Picks, results and records live in data/sports/tennis/picks.json."""
import csv
import json
import math
import os
import re
import time
import unicodedata
import urllib.request
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
RANKS = os.path.join(DIR, "rankings.json")   # the ATP ranking, saved daily (ESPN only has today's): {date: {id: rank}}
LINES = os.path.join(DIR, "lines.json")      # every price seen, the last one before the start kept (closing line)
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
N_PICKS = 8
PARLAY_LEGS = 3
MIN_EDGE = 0.02                # a tennis value pick: our win chance beats the price by 2%+
MIN_P = 0.55                   # ACCURACY FIRST: a tennis pick is one we expect to WIN (55%+) - no coin-flip dogs.
                               # Fewer than 8 qualify = fewer picks; never filler to reach 8
MAX_FAV = -300                 # no tennis moneyline shorter than -300: heavier favorites go on the game spread,
                               # and only when the engine expects them to win by more than the number
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
                ids, names, sets, ccs = [], [], [], []
                for x in comps:
                    a = x.get("athlete") or {}
                    ids.append(str(a.get("id") or x.get("id") or ""))
                    names.append(a.get("displayName") or a.get("fullName") or "?")
                    ccs.append(((a.get("flag") or {}).get("alt") or "").strip())
                    sets.append([int(float(ls.get("value") or 0)) for ls in x.get("linescores") or []])
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
                })
    return out


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

    def __init__(self):
        self.r, self.n, self.hist, self.h2h = {}, {}, {}, {}

    def _get(self, pid, surf):
        return self.r.get((pid, None), 1500.0), self.r.get((pid, surf), 1500.0)

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
                "clash_elo": clash * sm.logit(p)}

    def update(self, m):
        st = _state(m)
        if st not in ("final", "retired") or int(m["winner"] or 0) not in (1, 2):
            return
        w1 = 1.0 if int(m["winner"]) == 1 else 0.0
        sets = len([x for x in str(m["sets1"]).split() if x])
        for key in (None, m["surface"]):
            a, b = self.r.get((m["p1"], key), 1500.0), self.r.get((m["p2"], key), 1500.0)
            e = elo_p(a, b)
            self.r[(m["p1"], key)] = a + _k(self.n.get(m["p1"], 0)) * (w1 - e)
            self.r[(m["p2"], key)] = b + _k(self.n.get(m["p2"], 0)) * ((1 - w1) - (1 - e))
        for pid, won in ((m["p1"], w1), (m["p2"], 1 - w1)):
            self.n[pid] = self.n.get(pid, 0) + 1
            self.hist.setdefault(pid, []).append((m["start"], won, sets))
        winner, loser = (m["p1"], m["p2"]) if w1 else (m["p2"], m["p1"])
        self.h2h[(winner, loser)] = self.h2h.get((winner, loser), 0) + 1


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


def _x(f):
    # clash_elo: in a conflict matchup, does the favorite hold up or tighten up? (learned, can go either way)
    return [1.0, f["elo"], f["fatigue"], f["form"], f["h2h"], f.get("home", 0), f.get("clash_elo", 0)]


def model_p(w, f, bo=3):
    p = sm.sigmoid(sum(a * b for a, b in zip(w, _x(f))))
    return to_bo5(p) if int(bo or 3) == 5 else p


def study(ms, eval_n=2000):
    """Replay every finished match: ratings + the learned weights. Returns (ratings, weights, report)."""
    rows = sorted((m for m in ms.values() if _state(m) in ("final", "retired")), key=lambda m: (m["start"], m["id"]))
    rt = Ratings()
    data = []
    for m in rows:
        f = rt.features(m)
        if f["known"] >= MIN_MATCHES and int(m["winner"] or 0) in (1, 2) and _state(m) == "final":
            data.append((f, 1.0 if int(m["winner"]) == 1 else 0.0, m))
        rt.update(m)
    prior = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    fit_on, ev = data[:-eval_n], data[-eval_n:]
    w = sm.fit_logistic_offset([_x(f) for f, _, _ in fit_on], [y for _, y, _ in fit_on], [0.0] * len(fit_on),
                               prior=prior, lam=20.0) if len(fit_on) >= 500 else prior

    def score(ws):
        if not ev:
            return None, None
        ll = acc = 0.0
        for f, y, m in ev:
            p = min(max(model_p(ws, f, m["bo"]), 1e-4), 1 - 1e-4)
            ll -= math.log(p if y else 1 - p)
            acc += (p > 0.5) == (y == 1.0)
        return ll / len(ev), acc / len(ev)
    ll, acc = score(w)
    ll0, acc0 = score(prior)
    gm = {}
    for bo in (3, 5):                   # games won by: margin = slope * logit(win chance) (+ noise), per format
        pts = [(sm.logit(min(max(model_p(w, f, bo), 0.01), 0.99)), margin(m)) for f, _, m in fit_on or data
               if int(m["bo"] or 3) == bo and margin(m) is not None]
        if len(pts) >= 300:
            slope = sum(x * y for x, y in pts) / max(1e-9, sum(x * x for x, _ in pts))
            sig = math.sqrt(sum((y - slope * x) ** 2 for x, y in pts) / len(pts))
            gm[str(bo)] = [round(slope, 3), round(sig, 3)]
    report = {"matches": len(rows), "rated": len(data), "weights": [round(v, 3) for v in w], "games": gm,
              "acc": round(acc, 4) if acc is not None else None, "logloss": round(ll, 4) if ll is not None else None,
              "acc_elo": round(acc0, 4) if acc0 is not None else None,
              "logloss_elo": round(ll0, 4) if ll0 is not None else None}
    return rt, w, report


# ---------------------------------------------------------------- odds
def _get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r), r.headers.get("x-requests-remaining")


def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def bovada():
    """Bovada's public tennis feed: ATP + WTA singles moneylines."""
    data, _ = _get(BOVADA)
    rows = {}
    for grp in data or []:
        path = " ".join(str(p.get("description") or "") for p in grp.get("path") or []).lower()
        if not re.search(r"\b(atp|wta)\b", path) or any(k in path for k in ("doubles", "challenger", "itf", "exhibition", "utr", "125")):
            continue
        for ev in grp.get("events") or []:
            for dg in ev.get("displayGroups") or []:
                for mk in dg.get("markets") or []:
                    desc = str(mk.get("description", "")).lower()
                    if not (mk.get("period") or {}).get("main", True) or ("moneyline" not in desc and "game spread" not in desc):
                        continue
                    oc = mk.get("outcomes") or []
                    if len(oc) != 2:
                        continue

                    def am(o):
                        v = str((o.get("price") or {}).get("american") or "").upper()
                        return 100 if v == "EVEN" else int(v) if re.match(r"^[+-]?\d+$", v) else None
                    a, b = am(oc[0]), am(oc[1])
                    if a is None or b is None:
                        continue
                    start = datetime.fromtimestamp(int(ev.get("startTime", 0)) / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
                    key = (oc[0].get("description"), oc[1].get("description"), start)
                    row = rows.setdefault(key, {"a": key[0], "b": key[1], "start": start, "src": "bovada"})
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
    except Exception as e:                               # noqa: BLE001
        sd.ERRORS.append(f"bovada: {str(e)[:100]}")
        print(f"tennis odds: BOVADA FAILED ({str(e)[:80]}) - tell the owner if this keeps happening")
    return [ln for ln in cache.get("lines", []) if ln.get("start", "") >= (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")]


def rankings(now):
    """Today's ATP + WTA rankings {player id: rank}; saved once a day so the engine builds its own ranking history."""
    hist = {}
    if os.path.exists(RANKS):
        with open(RANKS) as f:
            hist = json.load(f)
    day = now.astimezone(PT).date().isoformat()
    if day not in hist:
        try:
            hist[day] = {}
            for tour in TOURS:
                with urllib.request.urlopen(ESPN.format(tour=tour).replace("scoreboard", "rankings"), timeout=20) as r:
                    ranks = (json.load(r).get("rankings") or [{}])[0].get("ranks") or []
                hist[day].update({str((x.get("athlete") or {}).get("id")): int(x.get("current")) for x in ranks if x.get("current")})
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
                    tags = data.setdefault(str(pid), [])
                    if all(t["id"] != str(a.get("id")) for t in tags):
                        tags.append({"id": str(a.get("id")), "kind": kinds[0], "date": (a.get("published") or now.isoformat())[:10],
                                     "headline": (a.get("headline") or "")[:140]})
    cut = (now - timedelta(days=sports_news.DRAMA_DAYS)).date().isoformat()
    data = {k: [t for t in v if t["date"] >= cut] for k, v in data.items()}
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
    l1, l2 = _last(m["p1_name"]), _last(m["p2_name"])
    n1, n2 = set(_norm(m["p1_name"])), set(_norm(m["p2_name"]))

    def same(line_name, last, names):                        # same last name, or the same name in the other order
        return _last(line_name) == last or (len(names) >= 2 and set(_norm(line_name)) == names)   # ("Ma Yexin" = "Yexin Ma")
    for ln in lines:
        if ln.get("start") and m["start"] and abs((_t(ln["start"]) - _t(m["start"])).total_seconds()) > 36 * 3600:
            continue
        for flip, (x, y) in ((False, (ln["a"], ln["b"])), (True, (ln["b"], ln["a"]))):
            if not (same(x, l1, n1) and same(y, l2, n2)):
                continue
            a, b = ("b", "a") if flip else ("a", "b")
            ml = (ln[f"{a}_ml"], ln[f"{b}_ml"])
            if not full:
                return ml
            sp = ((ln[f"{a}_hcp"], ln[f"{a}_sp"]), (ln[f"{b}_hcp"], ln[f"{b}_sp"])) if f"{a}_hcp" in ln else None
            return {"ml": ml, "sp": sp}
    return None


# ---------------------------------------------------------------- the words
SURF = {"hard": "hard court", "clay": "clay", "grass": "grass"}


def _used(skip=()):
    """Our big phrases already on the dashboard (main board + tennis), so a new write-up doesn't repeat them."""
    import sports_breakdown as sb
    return sb.slang_in(sb.dashboard_texts(skip=skip))


TENNIS_BV = 14                                   # breakdown version (older ones get rewritten before the match)


def _say_name(name):
    """'Botic Van De Zandschulp' -> 'Van De Zandschulp', 'Marco Trungelliti' -> 'Trungelliti' (how people say it)."""
    parts = str(name or "").split()
    for i, w in enumerate(parts[1:], 1):
        if w.lower() in ("van", "de", "da", "del", "der", "di", "le", "la", "von", "dos", "du"):
            return " ".join(parts[i:])
    return parts[-1] if parts else str(name or "")


def breakdown(c, rt, used):
    """Tennis breakdown in OUR voice (he/she by tour, last names, never the same wording twice on a board)."""
    import sports_breakdown as sb
    v = sb.Voice(c["id"], used)
    me, them, f = _say_name(c["player"]), _say_name(c["opp"]), c["f"]
    wta = c.get("tour") == "wta"
    he, him, his = ("she", "her", "her") if wta else ("he", "him", "his")
    He = he.capitalize()
    ours = "our girl" if wta else "our guy"
    surf = SURF[c["surface"]].lower()
    out = []
    if c.get("market") == "spread" and c["hcp"] > 0:
        out.append(v.say("t_spread_dog", [
            f"🎯 {me} +{c['hcp']:g} games. Even if {he} drops the match, we still cash as long as it's close. That's the value.",
            f"🎯 Book thinks {me} gets blown out. Nah. {me} +{c['hcp']:g} games — {he} keeps it close and we eat.",
            f"🎯 Taking the games with {me} (+{c['hcp']:g}). Even if {he} loses, it stays close — and close still cashes for us.",
            f"🎯 {me} getting {c['hcp']:g} games? Free money energy. {He}'s way more dangerous than this number says.",
            f"🎯 {me} +{c['hcp']:g} games. {He} can lose the match and we still cash — long as {he} don't lose by more than {c['hcp']:g} games."], must=True))
    elif c.get("market") == "spread":
        n = abs(c["hcp"])
        out.append(v.say("t_spread", [
            f"🎯 Why lay {c['ml']:+d}? We take {me} {c['hcp']:+g} games — {he}'s about to smack that ass by more than {n:g}.",
            f"🎯 {me} {c['hcp']:+g} games. No {c['ml']:+d} nonsense — {he} should roll this by more than {n:g} games.",
            f"🎯 {me} on the game spread ({c['hcp']:+g}). The engine's got {him} cooking — covering that is light work.",
            f"🎯 Skipping the {c['ml']:+d} tax. {me} {c['hcp']:+g} games — {he} wins big and we get paid better for it.",
            f"🎯 {me} {c['hcp']:+g} games. This ain't a match, it's a clinic. {He} should run away with it."], must=True))
    else:
        o = c.get("odds") or c.get("ml") or -110
        if o <= -150:                                             # a clear favorite: say it plain
            pct_ = round(100 * c["p"])
            lines_ = [f"🎾 {me} is the big favorite for a reason — {he}'s about to smack that ass.",
                      f"🎾 {me} is way better than {them}. The engine gives {him} a {pct_}% chance — {he} takes care of business.",
                      f"🎾 Everybody knows {me} is winning this one. The engine does too — {pct_}% chance.",
                      f"🎾 {me} all day. {He}'s the better player by a mile.",
                      f"🎾 {them} is about to get {his} cheeks clapped. {me} runs this.",
                      f"🎾 Give me {me}. Big price, but {he} wins this way more often than not.",
                      ] + [f"🎾 {x}" for x in sports_lingo.good(me, them, c["id"], he=he)]
        elif o < 0:                                               # a small favorite: the book has it closer than it is
            lines_ = [f"🎾 We riding {me}. The book's got this priced kinda close — it ain't.",
                      f"🎾 {me} is nice — the book don't respect it at {o}. {He} about to go off.",
                      f"🎾 {me} is only {o}? The algorithm has {him} winning this way more than that.",
                      f"🎾 Hammer {me}. The algorithm likes {him} way more than Vegas does.",
                      f"🎾 Give me {me}. {He}'s about to take care of business.",
                      f"🎾 {me}, no hesitation. The book's sleeping on {him}.",
                      f"🎾 {me} is about to smack that ass. The price is too cheap for how good {he} is."]
        else:                                                     # an underdog price the engine doesn't buy
            lines_ = [f"🎾 {me} is the dog at {o:+d}? Nah. The engine's got {him} as the better player.",
                      f"🎾 Book's got {me} as the underdog — the algorithm says {he}'s the one about to win.",
                      f"🎾 {me} at {o:+d} is a gift. {He}'s about to cook.",
                      f"🎾 We'll take {me} plus money all day. The book got this one backwards.",
                      f"🎾 {me} gets the nod. The price is wrong and we're taking it — let's eat."]
        out.append(v.say("t_main" + ("f" if o <= -150 else "m" if o < 0 else "d"), lines_, must=True))
    rk_me, rk_them = c.get("rank"), c.get("opp_rank")
    if rk_me and (not rk_them or rk_them - rk_me >= 20):
        out.append(v.say("t_rank", [f"📈 {me} is #{rk_me} in the world" + (f" — {them} is #{rk_them}. Levels to this." if rk_them else f" — {them} ain't even top 150."),
                                    f"📈 World #{rk_me} vs " + (f"#{rk_them}. Levels to this shit." if rk_them else "somebody outside the top 150. Levels to this shit."),
                                    f"📈 {He}'s #{rk_me} in the world for a reason" + (f" — {them} is sitting at #{rk_them}." if rk_them else "."),
                                    f"📈 Ranking gap is real: #{rk_me}" + (f" vs #{rk_them}." if rk_them else " vs outside the top 150.") + " Not the same tier.",
                                    f"📈 #{rk_me} vs " + (f"#{rk_them}" if rk_them else "outside the top 150") + f" — {them}'s about to get {his} cheeks clapped."]))
    if f.get("home", 0) > 0:
        out.append(v.say("t_home", [f"🏟️ {me} is playing at home — the whole crowd's got {his} back.",
                                    f"🏟️ Home soil for {ours}. That crowd's gonna carry {him}.",
                                    f"🏟️ Home cookin'. {He}'s got the whole building behind {him}."]))
    if c.get("their_drama"):
        k = c["their_drama"][0]["kind"]
        out.append(v.say("t_drama", [f"🍿 {them} got stuff going on off the court ({k}). Head ain't gonna be right.",
                                     f"🍿 Off-court noise for {them} ({k}). That follows you onto the court.",
                                     f"🍿 {them} dealing with {k}. Distracted players lose — period."]))
    if f.get("clash"):
        out.append(v.say("t_clash", ["🔥 Bad blood between these countries — no handshake energy. Pressure match.",
                                     "🔥 This one's personal between their countries. Heat on every point."]))
    if f["surface_gap"] >= 40:
        out.append(v.say("t_surf", [f"🟫 {He}'s a different animal on {surf}. That's {his} surface.",
                                    f"🟫 On {surf}, {me} is on a whole nother caliber. There's levels to this shit.",
                                    f"🟫 {surf.capitalize()} is {his} playground. {He} lives here.",
                                    f"🟫 Put {him} on {surf} and {he} turns into a problem."]))
    elif f["surface_gap"] <= -40:
        out.append(v.say("t_surf_opp", [f"🟫 {them} ain't the same player on {surf}. That's our edge.",
                                        f"🟫 {surf.capitalize()} exposes {them} — that game don't travel.",
                                        f"🟫 {them} on {surf}? Booty cheeks. We're taking advantage.",
                                        f"🟫 {them} is complete ass on {surf}. We're eating."]))
    if f["fatigue"] >= 0.66:
        out.append(v.say("t_tired", [f"😮‍💨 {them} has been grinding long matches all week. Tired legs.",
                                     f"😮‍💨 {them} played a ton of tennis lately. Legs gonna be heavy.",
                                     f"😮‍💨 {them}'s coming off marathon matches. {ours.capitalize()} is fresher.",
                                     f"😮‍💨 {them} is running on fumes. {ours.capitalize()}'s about to make {them} work every point.",
                                     f"😮‍💨 Tired legs + a better player across the net? {them}'s about to get {his} cheeks clapped."]))
    if f["form"] >= 0.2:
        out.append(v.say("t_form", [f"🔥 {He}'s been rolling lately and {them} has been ice cold.",
                                    f"🔥 Form says {me}. {He}'s been cooking.",
                                    f"🔥 {me} is hot right now — stacking W's while {them} keeps taking L's.",
                                    f"🔥 {He}'s on a heater. Don't fade the heater."]))
    if f["h2h"] >= 0.33:
        out.append(v.say("t_h2h", [f"🆚 {me} owns this matchup — {he}'s beaten {them} before.",
                                   f"🆚 {them} has had trouble with {me} in the past. History's on our side.",
                                   f"🆚 {me} got {them}'s number.",
                                   f"🆚 Been here before — {them} couldn't handle {him} last time either.",
                                   f"🆚 {them} already got {his} cheeks clapped by {me} before. Run it back."]))
    if int(c["bo"]) == 5:
        out.append(v.say("t_bo5", ["🏆 Best of 5 at a Slam — the longer it goes, the more the better player takes over.",
                                   f"🏆 Five sets gives {them} nowhere to hide. Better player wins these."]))
    if not c.get("odds"):
        return [x for x in out if x]
    book = round(100 / sd.decimal(c["odds"]))
    pct = round(100 * c["p"])
    bet = f"{me} {c['hcp']:+g} games" if c.get("market") == "spread" else f"{me} ML"
    out.append(v.say("t_bottom", [f"✅ Bottom line: book says {book}%, we say {pct}%. We ride {bet} ({c['odds']:+d}).",
                                  f"✅ Bottom line: book's got it at {book}% — the engine sees {pct}%. {bet} ({c['odds']:+d}). Trust the algorithm.",
                                  f"✅ Bottom line: {pct}% for us, {book}% for the book. That's the value — {bet} ({c['odds']:+d}). Let's eat.",
                                  f"✅ Bottom line: Vegas {book}%, us {pct}%. {bet} ({c['odds']:+d}) — tail it.",
                                  f"✅ Bottom line: the book's at {book}%, we're at {pct}%. {bet} ({c['odds']:+d}). That gap is the money.",
                                  f"✅ Bottom line: {pct}% vs the book's {book}%. {bet} ({c['odds']:+d}). We eat.",
                                  f"✅ Bottom line: engine {pct}%, Vegas {book}%. {bet} ({c['odds']:+d}) — lock it in.",
                                  f"✅ Bottom line: {book}% says the book, {pct}% says the algorithm. {bet} ({c['odds']:+d}). Trust it."], must=True))
    return [x for x in out if x]


# ---------------------------------------------------------------- picks
def _load_picks():
    if os.path.exists(PICKS):
        with open(PICKS) as f:
            return json.load(f)
    return []


def candidates(ms, rt, w, lines, now, until, ranks=None, news=None, gm=None):
    out = []
    gm = gm or {}
    ranks, news = ranks or {}, news or {}
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
        p1 = model_p(w, f, m["bo"])
        for side, p, ml, opp_ml in ((1, p1, pr[0], pr[1]), (2, 1 - p1, pr[1], pr[0])):
            me, them = (m["p1_name"], m["p2_name"]) if side == 1 else (m["p2_name"], m["p1_name"])
            fs = f if side == 1 else {**f, "fatigue": -f["fatigue"], "form": -f["form"], "h2h": -f["h2h"],
                                      "surface_gap": -f["surface_gap"], "home": -f["home"]}
            dec = sd.decimal(ml)
            mine, theirs = (m["p1"], m["p2"]) if side == 1 else (m["p2"], m["p1"])
            out.append({"id": f"{m['id']}:{side}", "match": m["id"], "side": side, "player": me, "opp": them,
                        "tour": m.get("tour", "atp"),
                        "rank": ranks.get(mine), "opp_rank": ranks.get(theirs),
                        "our_drama": (news.get(mine) or [])[:1], "their_drama": (news.get(theirs) or [])[:1],
                        "odds": ml, "dec": dec, "p": p, "edge": p * dec - 1, "start": m["start"], "tourney": m["tourney"],
                        "round": m["round"], "surface": m["surface"], "bo": m["bo"], "f": fs, "market": "ml", "hcp": None,
                        "ml": ml, "win_p": p})
            if sp and gm:
                hcp, sodds = sp[side - 1]
                pc = cover_p(gm, p, hcp, m["bo"])
                if pc is not None:
                    sdec = sd.decimal(sodds)
                    out.append({**out[-1], "id": f"{m['id']}:{side}:sp", "market": "spread", "hcp": hcp, "odds": sodds,
                                "dec": sdec, "p": pc, "edge": pc * sdec - 1})
    return out


def pick_slate(cands):
    """Up to 8 straights we expect to win (55%+) with real value, likeliest first + the parlay (the 3 likeliest)."""
    for c in cands:
        c["value"] = c["edge"] >= (2 * MIN_EDGE if c.get("our_drama") else MIN_EDGE)
    cands = [c for c in cands if c["p"] >= MIN_P and c["value"]                  # likely to win AND real value
             and (c["value"] or not c.get("our_drama"))       # drama on our side: never a filler
             and (c.get("market", "ml") != "ml" or c["odds"] >= MAX_FAV)        # no moneyline shorter than -300
             and (c.get("market", "ml") == "ml" or c["value"])]                  # a game spread only as real value
    best = {}
    for c in sorted(cands, key=lambda c: -c["p"]):
        best.setdefault(c["match"], c)                          # one side per match (the likelier bet: ML or spread)
    ranked = sorted(best.values(), key=lambda c: -c["p"])
    men = [c for c in ranked if c.get("tour", "atp") != "wta"]      # the owner wants men's and women's even:
    women = [c for c in ranked if c.get("tour") == "wta"]             # half and half, the likeliest of each...
    half = N_PICKS // 2
    picks = men[:half] + women[:half]
    rest = [c for c in ranked if c not in picks]                       # ...and if one side's short on real picks,
    picks = sorted(picks + rest[:N_PICKS - len(picks)], key=lambda c: -c["p"])   # the other side fills (never filler)
    parlay = sorted(picks, key=lambda c: -c["p"])[:PARLAY_LEGS] if len(picks) >= PARLAY_LEGS else []
    return picks, parlay


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
    straights, parlay = pick_slate(cands)
    if not straights:
        return None
    used = _used()   # no phrase repeats anywhere on the dashboard
    legs = []
    for c in straights:
        legs.append({k: c.get(k) for k in ("id", "match", "side", "player", "opp", "tour", "odds", "p", "edge", "start", "tourney",
                                            "market", "hcp", "ml",
                                        "round", "surface", "bo", "value")} | {"result": None, "breakdown": breakdown(c, rt, used), "bv": TENNIS_BV})
    par = None
    if parlay:
        dec = 1.0
        for c in parlay:
            dec *= c["dec"]
        par = {"legs": [c["id"] for c in parlay], "dec": round(dec, 4), "american": round((dec - 1) * 100) if dec >= 2
               else round(-100 / (dec - 1)), "status": "open"}
    slate = {"date": iso, "posted": now.strftime("%Y-%m-%dT%H:%MZ"), "picks": legs, "parlay": par}
    picks.append(slate)
    return slate


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
                l["breakdown"], l["bv"] = breakdown(by_id[l["id"]], rt, used), TENNIS_BV
    ours = {l["match"] for s in picks[-3:] for l in s.get("picks") or [] if not l.get("result")}
    by = {}
    for c in cands:
        by.setdefault(c["match"], []).append(c)
    out = []
    for mid, cs in by.items():
        ok = [c for c in cs if c["odds"] >= ASK_STEEP] or cs
        c = max(ok, key=lambda c: (c["p"], c["edge"]))                 # accuracy first: the likelier bet
        why = ("on_board" if mid in ours else "steep" if c["odds"] < ASK_STEEP else "coin_flip" if c["p"] < 0.55
               else "tight" if c["edge"] >= MIN_EDGE else "no_value")
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
    straights, parlay = pick_slate(cands)
    used = _used()   # no phrase repeats anywhere on the dashboard
    new = [{k: c.get(k) for k in ("id", "match", "side", "player", "opp", "tour", "odds", "p", "edge", "start", "tourney",
                                  "market", "hcp", "ml", "round", "surface", "bo", "value")}
           | {"result": None, "breakdown": breakdown(c, rt, used), "bv": TENNIS_BV} for c in straights[:max(0, N_PICKS - len(keep))]]
    old = [l["player"] for l in slate["picks"]]
    slate["picks"] = keep + new
    par = slate.get("parlay")
    if not par or all(_t(l["start"]) > soon for l in slate["picks"] if l["id"] in (par or {}).get("legs", [])):
        if parlay and all(c["id"] in {l["id"] for l in new} for c in parlay):
            dec = 1.0
            for c in parlay:
                dec *= c["dec"]
            slate["parlay"] = {"legs": [c["id"] for c in parlay], "dec": round(dec, 4),
                               "american": round((dec - 1) * 100) if dec >= 2 else round(-100 / (dec - 1)), "status": "open"}
        else:
            slate["parlay"] = None
    slate["repicked"] = now.strftime("%Y-%m-%dT%H:%MZ")
    os.remove(REPICK)
    print(f"tennis re-pick {want}: {old} -> {[l['player'] for l in slate['picks']]}")
    return slate


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
        par = s.get("parlay")
        if par and par["status"] == "open":
            res = [next(l["result"] for l in s["picks"] if l["id"] == i) for i in par["legs"]]
            if "lost" in res:
                par["status"] = "lost"
            elif all(r in ("won", "void", "push") for r in res):
                par["status"] = "won" if "won" in res else "void"


def _score_txt(m):
    a, b = str(m["sets1"]).split(), str(m["sets2"]).split()
    return ", ".join(f"{x}-{y}" for x, y in zip(a, b))


def record(picks):
    legs = [l for s in picks for l in s["picks"]]
    pars = [s["parlay"] for s in picks if s.get("parlay")]
    return {"won": sum(l["result"] == "won" for l in legs), "lost": sum(l["result"] == "lost" for l in legs),
            "p_won": sum(p["status"] == "won" for p in pars), "p_lost": sum(p["status"] == "lost" for p in pars)}


def run(state, now=None, fetch=True):
    """One tennis cycle; never lets tennis break the main engine (the caller wraps it)."""
    now = now or datetime.now(timezone.utc)
    if fetch:
        ms, calls, fails = sync(state)
        print(f"tennis sync: {len(ms)} matches stored, {calls} calls, {fails} failed")
    else:
        ms = load_matches()
    rt, w, rep = study(ms)
    state["tennis_study"] = rep
    print(f"tennis study: {rep['rated']} rated matches, acc {rep['acc']} (surface ratings alone {rep['acc_elo']}), "
          f"loss {rep['logloss']} vs {rep['logloss_elo']}, weights {rep['weights']}")
    picks = _load_picks()
    grade(ms, picks)
    lines = refresh_odds(state, now) if fetch else []
    slate = post(ms, rt, w, lines, picks, now, rep.get("games")) if rep["rated"] >= MIN_RATED and rep["weights"] != [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0] \
        else None
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
