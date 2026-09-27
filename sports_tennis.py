"""🎾 TENNIS BONUS: men's singles (ATP) picks - a bonus section, never part of the main board or its records.

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
import sports_model as sm

PT = ZoneInfo("America/Los_Angeles")
DIR = os.path.join(sd.DATA, "tennis")
MATCHES = os.path.join(DIR, "matches.csv")
PICKS = os.path.join(DIR, "picks.json")
ODDS = os.path.join(DIR, "odds.json")
LINES = os.path.join(DIR, "lines.json")      # every price seen, the last one before the start kept (closing line)
FIELDS = ["id", "start", "event", "tourney", "round", "surface", "bo", "p1", "p1_name", "p2", "p2_name", "winner",
          "sets1", "sets2", "status", "done"]
ESPN = "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard"
BOVADA = "https://www.bovada.lv/services/sports/event/coupon/events/A/description/tennis?marketFilterId=def&lang=en"
YEARS = 10
N_PICKS = 8
PARLAY_LEGS = 3
MIN_EDGE = 0.02                # a tennis value pick: our win chance beats the price by 2%+
MIN_MATCHES = 10               # both players need this many rated matches
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
def parse_espn(payload):
    """ESPN ATP scoreboard -> [match rows] (men's singles only)."""
    out = []
    for ev in payload.get("events") or []:
        tourney = ev.get("name") or ev.get("shortName") or ""
        major = bool(ev.get("major")) or any(k in tourney.lower() for k in MAJORS)
        for gr in ev.get("groupings") or []:
            gname = ((gr.get("grouping") or {}).get("displayName") or "")
            if "Singles" not in gname or "Women" in gname:
                continue
            for c in gr.get("competitions") or []:
                comps = c.get("competitors") or []
                if len(comps) != 2:
                    continue
                st = ((c.get("status") or {}).get("type") or {})
                ids, names, sets = [], [], []
                for x in comps:
                    a = x.get("athlete") or {}
                    ids.append(str(a.get("id") or x.get("id") or ""))
                    names.append(a.get("displayName") or a.get("fullName") or "?")
                    sets.append([int(float(ls.get("value") or 0)) for ls in x.get("linescores") or []])
                if not all(ids):
                    continue
                win = 1 if comps[0].get("winner") else 2 if comps[1].get("winner") else 0
                rnd = ((c.get("round") or {}).get("displayName") or "")
                done = sum(1 for a, b in zip(*sets) if max(a, b) >= 6 and (abs(a - b) >= 2 or max(a, b) == 7))
                out.append({
                    "id": str(c.get("id")), "start": c.get("date") or ev.get("date") or "", "event": str(ev.get("id") or ""),
                    "tourney": tourney, "round": rnd, "surface": surface_of(tourney),
                    "bo": 5 if major and "qualif" not in rnd.lower() else 3,
                    "p1": ids[0], "p1_name": names[0], "p2": ids[1], "p2_name": names[1], "winner": win,
                    "sets1": " ".join(map(str, sets[0])), "sets2": " ".join(map(str, sets[1])),
                    "status": st.get("name") or "", "done": done,
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


def _espn(day):
    for i in range(2):
        try:
            with urllib.request.urlopen(f"{ESPN}?dates={day:%Y%m%d}", timeout=20) as r:
                return parse_espn(json.load(r))
        except Exception as e:                           # noqa: BLE001
            if i:
                sd.ERRORS.append(f"tennis {day:%Y-%m-%d}: {str(e)[:100]}")
                return None
            time.sleep(1.5)


def sync(state, budget_s=150):
    """This week (+ tomorrow) every run; history a year per run (weekly calls - each returns whole tournaments)."""
    ms = load_matches()
    today = datetime.now(timezone.utc).date()
    days = [today + timedelta(days=d) for d in range(-7, 2)]
    frm = datetime.strptime(state.get("tennis_from", today.isoformat()), "%Y-%m-%d").date()
    target = today - timedelta(days=365 * YEARS)
    lo = max(target, frm - timedelta(days=365))
    d = frm - timedelta(days=7)
    while d >= lo:
        days.append(d)
        d -= timedelta(days=7)
    deadline = time.time() + budget_s

    def run(day):
        return day, (_espn(day) if time.time() < deadline else None)
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(run, days))
    got = 0
    for day, rows in results:
        for r in rows or []:
            old = ms.get(r["id"])
            if old and _state(old) in ("final", "retired", "void") and _state(r) == "pre":
                continue
            ms[r["id"]] = r
            got += 1
    if all(rows is not None for day, rows in results if day < today - timedelta(days=7)):
        state["tennis_from"] = min(lo, frm).isoformat()
    save_matches(ms)
    return ms, len(days), sum(1 for _, r in results if r is None)


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
        return {"elo": sm.logit(p), "fatigue": (fatigue(p2) - fatigue(p1)) / 3, "form": form(p1) - form(p2),
                "h2h": max(-3, min(3, h)) / 3, "known": min(self.n.get(p1, 0), self.n.get(p2, 0)),
                "p_elo": p, "surface_gap": (s1 - s2) - (o1 - o2)}

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


def _x(f):
    return [1.0, f["elo"], f["fatigue"], f["form"], f["h2h"]]


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
    prior = [0.0, 1.0, 0.0, 0.0, 0.0]
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
    report = {"matches": len(rows), "rated": len(data), "weights": [round(v, 3) for v in w],
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
    """Backup: Bovada's public tennis feed (men's singles moneylines)."""
    data, _ = _get(BOVADA)
    out = []
    for grp in data or []:
        path = " ".join(str(p.get("description") or "") for p in grp.get("path") or []).lower()
        if "atp" not in path or "doubles" in path or "wta" in path or "women" in path:
            continue
        for ev in grp.get("events") or []:
            for dg in ev.get("displayGroups") or []:
                for mk in dg.get("markets") or []:
                    if "moneyline" not in str(mk.get("description", "")).lower() or not (mk.get("period") or {}).get("main", True):
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
                    out.append({"a": oc[0].get("description"), "b": oc[1].get("description"), "a_ml": a, "b_ml": b,
                                "start": start, "src": "bovada"})
    return out


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
        print(f"tennis odds: {len(lines)} men's matches priced (bovada)")
    except Exception as e:                               # noqa: BLE001
        sd.ERRORS.append(f"bovada: {str(e)[:100]}")
        print(f"tennis odds: BOVADA FAILED ({str(e)[:80]}) - tell the owner if this keeps happening")
    return [ln for ln in cache.get("lines", []) if ln.get("start", "") >= (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")]


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


def price(m, lines):
    """(p1 ml, p2 ml) for a stored match from the odds lines (same two last names, start within 36 hours)."""
    l1, l2 = _last(m["p1_name"]), _last(m["p2_name"])
    for ln in lines:
        la, lb = _last(ln["a"]), _last(ln["b"])
        if ln.get("start") and m["start"] and abs((_t(ln["start"]) - _t(m["start"])).total_seconds()) > 36 * 3600:
            continue
        if (la, lb) == (l1, l2):
            return ln["a_ml"], ln["b_ml"]
        if (la, lb) == (l2, l1):
            return ln["b_ml"], ln["a_ml"]
    return None


# ---------------------------------------------------------------- the words
SURF = {"hard": "hard court", "clay": "clay", "grass": "grass"}


def breakdown(c, rt, used):
    """Tennis breakdown in our voice: why we're on this guy."""
    import sports_breakdown as sb
    v = sb.Voice(c["id"], used)
    me, them, f = c["player"], c["opp"], c["f"]
    surf = SURF[c["surface"]]
    out = []
    if c["value"]:
        out.append(v.say("t_main", [
            f"🎾 We're on {me}. The price is too cheap for how good he is — the algorithm sees value.",
            f"🎾 {me} all day. The book's got him priced like it's close. It ain't.",
            f"🎾 Riding {me}. Our numbers got him winning this way more than the line says.",
            f"🎾 {me} is the play. Value on the favorite — easy money energy.",
            f"🎾 Hammer {me}. The algorithm likes him more than Vegas does.",
            f"🎾 {me} gets the nod. The price is wrong and we're taking it.",
            f"🎾 We're rolling with {me} — better player, and the line hasn't caught up.",
            f"🎾 {me} is on the menu. Value like this don't last.",
            f"🎾 Give me {me}. The numbers say he takes care of business.",
            f"🎾 {me}, no hesitation. The book's sleeping on him."]))
    else:
        out.append(v.say("t_fav", [
            f"🎾 {me} is the heavy favorite here and the algorithm agrees — he should handle this.",
            f"🎾 {me} is the better player by a mile. Chalk, but chalk cashes.",
            f"🎾 {me} should take care of business. Big favorite, and for good reason.",
            f"🎾 Safe spot: {me} is too much for {them}.",
            f"🎾 {me} is the class of this matchup. Lock him in.",
            f"🎾 {me} over {them}. Not a lot of drama expected.",
            f"🎾 {me} should cruise. The algorithm has him as the clear better player.",
            f"🎾 {them} is gonna have a long day. {me} is the play."]))
    if f["surface_gap"] >= 40:
        out.append(v.say("t_surf", [f"🟫 {me} is a different animal on {surf} — his {surf} game is way above his usual level.",
                                    f"🟫 On {surf}, {me} levels up. That's his surface.",
                                    f"🟫 {surf.title()} is {me}'s playground."]))
    elif f["surface_gap"] <= -40:
        out.append(v.say("t_surf_opp", [f"🟫 {them} ain't the same player on {surf}. That's our edge.",
                                        f"🟫 {surf.title()} exposes {them} — his game doesn't travel to this surface."]))
    if f["fatigue"] >= 0.66:
        out.append(v.say("t_tired", [f"😮‍💨 {them} has been grinding long matches the last few days. Tired legs.",
                                     f"😮‍💨 {them} played a ton of tennis this week. Legs gonna be heavy.",
                                     f"😮‍💨 {them}'s coming off marathon matches. {me} is fresher."]))
    if f["form"] >= 0.2:
        out.append(v.say("t_form", [f"🔥 {me} has been rolling lately — winning way more than {them}.",
                                    f"🔥 {me} is hot right now and {them} has been ice cold.",
                                    f"🔥 Form says {me}. He's been cooking."]))
    if f["h2h"] >= 0.33:
        out.append(v.say("t_h2h", [f"🆚 {me} owns this matchup — he's beaten {them} before.",
                                   f"🆚 {them} has had trouble with {me} in the past. History's on our side.",
                                   f"🆚 {me} has {them}'s number."]))
    if int(c["bo"]) == 5:
        out.append(v.say("t_bo5", ["🏆 Best of 5 at a Slam — the longer the match, the more the better player takes over.",
                                   f"🏆 Five sets gives {them} nowhere to hide. Better player wins these."]))
    return [x for x in out if x]


# ---------------------------------------------------------------- picks
def _load_picks():
    if os.path.exists(PICKS):
        with open(PICKS) as f:
            return json.load(f)
    return []


def candidates(ms, rt, w, lines, now, until):
    out = []
    for m in ms.values():
        if _state(m) != "pre" or not m["start"]:
            continue
        t = _t(m["start"])
        if not (now + timedelta(minutes=MIN_LEAD_MIN) <= t <= until):
            continue
        pr = price(m, lines)
        f = rt.features(m, when=now.strftime("%Y-%m-%dT%H:%M"))
        if not pr or f["known"] < MIN_MATCHES:
            continue
        p1 = model_p(w, f, m["bo"])
        for side, p, ml, opp_ml in ((1, p1, pr[0], pr[1]), (2, 1 - p1, pr[1], pr[0])):
            me, them = (m["p1_name"], m["p2_name"]) if side == 1 else (m["p2_name"], m["p1_name"])
            fs = f if side == 1 else {**f, "fatigue": -f["fatigue"], "form": -f["form"], "h2h": -f["h2h"],
                                      "surface_gap": -f["surface_gap"]}
            dec = sd.decimal(ml)
            out.append({"id": f"{m['id']}:{side}", "match": m["id"], "side": side, "player": me, "opp": them,
                        "odds": ml, "dec": dec, "p": p, "edge": p * dec - 1, "start": m["start"], "tourney": m["tourney"],
                        "round": m["round"], "surface": m["surface"], "bo": m["bo"], "f": fs})
    return out


def pick_slate(cands):
    """8 straights (value first, then the likeliest favorites) + the parlay (the 3 likeliest of them)."""
    for c in cands:
        c["value"] = c["edge"] >= MIN_EDGE
    best = {}
    for c in sorted(cands, key=lambda c: (not c["value"], -c["p"])):
        best.setdefault(c["match"], c)                          # one side per match
    picks = sorted(best.values(), key=lambda c: (not c["value"], -c["p"]))[:N_PICKS]
    parlay = sorted(picks, key=lambda c: -c["p"])[:PARLAY_LEGS] if len(picks) >= PARLAY_LEGS else []
    return picks, parlay


def post(ms, rt, w, lines, picks, now):
    """Post the day's tennis slate once (from 6pm PT the night before: the next 24 hours of matches)."""
    local = now.astimezone(PT)
    day = (local + timedelta(days=1)).date() if local.hour >= POST_FROM_HOUR_PT else local.date()
    iso = day.isoformat()
    if any(p["date"] == iso for p in picks):
        return None
    cands = candidates(ms, rt, w, lines, now, now + timedelta(hours=24))
    straights, parlay = pick_slate(cands)
    if not straights:
        return None
    used = set()
    legs = []
    for c in straights:
        legs.append({k: c[k] for k in ("id", "match", "side", "player", "opp", "odds", "p", "edge", "start", "tourney",
                                        "round", "surface", "bo", "value")} | {"result": None, "breakdown": breakdown(c, rt, used)})
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


def grade(ms, picks):
    for s in picks:
        for leg in s["picks"]:
            if leg["result"]:
                continue
            m = ms.get(leg["match"])
            if not m:
                continue
            st = _state(m)
            if st == "void" or (st == "retired" and int(m.get("done") or 0) < 1):
                leg["result"] = "void"
            elif st in ("final", "retired") and int(m["winner"] or 0) in (1, 2):
                leg["result"] = "won" if int(m["winner"]) == leg["side"] else "lost"
                leg["score"] = _score_txt(m)
        par = s.get("parlay")
        if par and par["status"] == "open":
            res = [next(l["result"] for l in s["picks"] if l["id"] == i) for i in par["legs"]]
            if "lost" in res:
                par["status"] = "lost"
            elif all(r in ("won", "void") for r in res):
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
    slate = post(ms, rt, w, lines, picks, now)
    if slate:
        print(f"tennis posted {slate['date']}: " + ", ".join(f"{l['player']} {l['odds']:+d}" for l in slate["picks"]))
    os.makedirs(DIR, exist_ok=True)
    with open(PICKS, "w") as f:
        json.dump(picks[-120:], f, indent=1)
    return picks
