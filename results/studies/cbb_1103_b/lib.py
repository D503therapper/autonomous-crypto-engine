"""11/3 COLLEGE HOOPS (B) - shared table for the five situational studies (read-only on the repo; the cache lands in
~/.cache/d503_studies, never the repo).

One row per team side of every college hoops game 2016-27 (data/sports/games/ncaab), built in date order with NO
look-ahead: everything on a row is known before tip (earlier results, this game's closing / opening prices, the
schedule itself).
Prices: ESPN's close (ml_home / ml_away, spread_home + its odds); ESPN's OPEN (ml_*_open) for 2023-25 = the second check.
Seasons: TRAIN 2018-2022 (2018-19 .. 2022-23), HELD OUT 2023 / 2024 / 2025 each apart, NOW 2026 (a handful of games).
Conference = inferred from the schedule (no conference field on file): teams that play each other Jan 3 - Mar 1
(home / road regular-season games) and share 3+ common opponents in that window -> connected components.
Tier: POWER = the component holding Duke / Kansas / Kentucky / Michigan / Villanova (+ UCLA / Arizona's Pac-12 to 2023);
HIGH-MID = Gonzaga / San Diego St / Dayton / Memphis / Saint Mary's; the rest LOW."""
import csv, glob, json, math, os, pickle, statistics
from collections import defaultdict, Counter
from datetime import datetime

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
CACHE = os.environ.get("STUDY_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "d503_studies")
os.makedirs(CACHE, exist_ok=True)
TRAIN = (2018, 2022)
HELD = (2023, 2024, 2025)
NOW = 2026


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def season(start):
    y = int(start[:4])
    return y if int(start[5:7]) >= 7 else y - 1


def night(start):
    t = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
    return int((t.timestamp() - 5 * 3600) // 86400)


def nv(a, b):
    pa, pb = 1 / dec(a), 1 / dec(b)
    return pa / (pa + pb)


def hav(a, b):
    la, lo, lb, lob = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lb - la) / 2) ** 2 + math.cos(la) * math.cos(lb) * math.sin((lob - lo) / 2) ** 2
    return 3959 * 2 * math.asin(math.sqrt(h))


def load_games():
    gs = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/sports/games/ncaab/*.csv"))):
        for r in csv.DictReader(open(f)):
            if r["status"] != "final":
                continue
            hs, as_ = num(r["home_score"]), num(r["away_score"])
            if hs is None or as_ is None:
                continue
            r["hs"], r["as"] = hs, as_
            r["season"] = season(r["start"])
            r["night"] = night(r["start"])
            gs.append(r)
    gs.sort(key=lambda r: (r["start"], r["id"]))
    seen, out = set(), []
    for r in gs:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        out.append(r)
    return out


ANCH_POWER = {"Duke", "Kansas", "Kentucky", "Michigan", "Villanova"}
ANCH_MID = {"Gonzaga", "San Diego St", "Dayton", "Memphis", "Saint Mary's"}


def conferences(gs):
    """{season: {team id: (conf key, tier, size)}} inferred from the Jan 3 - Mar 1 home / road schedule."""
    names = {}
    by = defaultdict(lambda: defaultdict(set))
    for r in gs:
        names[r["home"]], names[r["away"]] = r["home_name"], r["away_name"]
        md = r["start"][5:10]
        if r["stype"] != "2" or str(r["neutral"]) == "1" or not ("01-03" <= md <= "03-01"):
            continue
        by[r["season"]][r["home"]].add(r["away"])
        by[r["season"]][r["away"]].add(r["home"])
    out = {}
    for s, adj in by.items():
        par = {t: t for t in adj}

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for a in adj:
            for b in adj[a]:
                if a < b and len(adj[a] & adj[b]) >= 3:
                    par[find(a)] = find(b)
        comp = defaultdict(set)
        for t in adj:
            comp[find(t)].add(t)
        m = {}
        for k, mem in comp.items():
            nm = {names.get(t) for t in mem}
            if nm & ANCH_POWER or (s <= 2023 and "UCLA" in nm) or (s >= 2024 and "Arizona" in nm):
                tier = "power"
            elif nm & ANCH_MID:
                tier = "mid"
            else:
                tier = "low"
            if len(mem) < 5:
                tier = "none"
            for t in mem:
                m[t] = (k, tier, len(mem))
        out[s] = m
    return out, names


def _streak(H, key):
    st = 0
    for h in reversed(H):
        v = h.get(key)
        if v is None:
            break
        if st >= 0 and v:
            st += 1
        elif st <= 0 and not v:
            st -= 1
        else:
            break
    return st


def build():
    pk = os.path.join(CACHE, "cbb1103b_rows.pkl")
    if os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(__file__):
        return pickle.load(open(pk, "rb"))
    gs = load_games()
    conf, names = conferences(gs)
    ven = json.load(open(os.path.join(ROOT, "data/sports/venues.json")))
    hv = defaultdict(Counter)
    for r in gs:
        if str(r["neutral"]) != "1":
            hv[(r["season"], r["home"])][f"{r['city']}|{r['state']}|"] += 1

    def loc(key):
        for k in (key, key[:-1] + "|USA", key + "USA"):
            if k in ven:
                return ven[k]
        return None

    def home_loc(s, t):
        c = hv.get((s, t)) or hv.get((s - 1, t)) or hv.get((s + 1, t))
        return loc(c.most_common(1)[0][0]) if c else None

    from zoneinfo import ZoneInfo
    tzc = {}

    def tzoff(v):
        if not v or len(v) < 4 or not v[3]:
            return None
        if v[3] not in tzc:
            try:
                tzc[v[3]] = ZoneInfo(v[3]).utcoffset(datetime(2025, 1, 15)).total_seconds() / 3600
            except Exception:  # noqa: BLE001
                tzc[v[3]] = None
        return tzc[v[3]]

    elo = defaultdict(lambda: 1500.0)
    last_season = {}
    hist = defaultdict(list)
    meet = defaultdict(list)
    rows = []
    for r in gs:
        s = r["season"]
        for t in (r["home"], r["away"]):
            if last_season.get(t) is not None and last_season[t] != s:
                elo[t] = 1500 + (elo[t] - 1500) * 2 / 3
            last_season[t] = s
        neutral = str(r["neutral"]) == "1"
        mlh, mla = num(r["ml_home"]), num(r["ml_away"])
        mloh, mloa = num(r["ml_home_open"]), num(r["ml_away_open"])
        sp = num(r["spread_home"])
        spo_h, spo_a = num(r["spread_home_odds"]) or -110, num(r["spread_away_odds"]) or -110
        venue = loc(f"{r['city']}|{r['state']}|")
        pair = []
        for side in ("home", "away"):
            o = "away" if side == "home" else "home"
            t, ot = r[side], r[o]
            me_s, op_s = (r["hs"], r["as"]) if side == "home" else (r["as"], r["hs"])
            H, OH = hist[(s, t)], hist[(s, ot)]
            x = {"id": r["id"], "season": s, "start": r["start"], "night": r["night"], "stype": r["stype"],
                 "team": t, "opp": ot, "name": names.get(t), "oname": names.get(ot),
                 "side": side, "neutral": neutral, "venue": "neutral" if neutral else side,
                 "won": me_s > op_s, "margin": me_s - op_s, "gn": len(H) + 1, "ogn": len(OH) + 1,
                 "elo": elo[t], "oelo": elo[ot], "total": num(r["total"]), "pts": me_s + op_s}
            ml, oml = (mlh, mla) if side == "home" else (mla, mlh)
            if ml and oml:
                x["ml"], x["oml"], x["p"] = ml, oml, nv(ml, oml)
            mo, omo = (mloh, mloa) if side == "home" else (mloa, mloh)
            if mo and omo:
                x["mlo"], x["po"] = mo, nv(mo, omo)
            if sp is not None:
                x["sp"] = sp if side == "home" else -sp
                x["spodds"] = spo_h if side == "home" else spo_a
                cm = x["margin"] + x["sp"]
                x["cover"] = None if cm == 0 else cm > 0
            if H:
                x["rest"] = r["night"] - H[-1]["night"]
                x["g3"] = sum(1 for h in H if r["night"] - h["night"] <= 2)
                x["g5"] = sum(1 for h in H if r["night"] - h["night"] <= 4)
                x["last"] = H[-1]
            if OH:
                x["orest"] = r["night"] - OH[-1]["night"]
                x["og3"] = sum(1 for h in OH if r["night"] - h["night"] <= 2)
                x["og5"] = sum(1 for h in OH if r["night"] - h["night"] <= 4)
                x["olast"] = OH[-1]
            trip = 0
            if not neutral and side == "away":
                trip = 1
                for h in reversed(H):
                    if h["venue"] == "away":
                        trip += 1
                    else:
                        break
            x["trip"] = trip
            hl = home_loc(s, t)
            if venue and hl:
                x["miles"] = hav(hl, venue)
                a, b = tzoff(hl), tzoff(venue)
                x["tzd"] = (b - a) if a is not None and b is not None else None
            x["streak"] = _streak(H, "won")
            x["ostreak"] = _streak(OH, "won")
            x["ats"] = _streak(H, "cover")
            x["wpct"] = (sum(h["won"] for h in H) / len(H)) if H else None
            x["owpct"] = (sum(h["won"] for h in OH) / len(OH)) if OH else None
            x["prev_meet"] = [{"margin": (m["margin"] if m["team"] == t else -m["margin"]),
                               "venue": (m["venue"] if m["team"] == t else
                                         {"home": "away", "away": "home"}.get(m["venue"], "neutral")),
                               "stype": m["stype"], "night": m["night"]}
                              for m in meet[(s, frozenset((t, ot)))]]
            cf = conf.get(s, {})
            c1, c2 = cf.get(t, (None, "none", 0)), cf.get(ot, (None, "none", 0))
            x["conf"], x["tier"], x["otier"] = c1[0], c1[1], c2[1]
            x["same_conf"] = c1[0] is not None and c1[0] == c2[0]
            pair.append(x)
        rows.extend(pair)
        for x in pair:
            hist[(s, x["team"])].append({"night": x["night"], "won": x["won"], "margin": x["margin"],
                                         "venue": x["venue"], "cover": x.get("cover"), "p": x.get("p"),
                                         "ml": x.get("ml"), "opp": x["opp"], "oelo": x["oelo"], "elo": x["elo"],
                                         "id": x["id"], "stype": x["stype"], "same_conf": x["same_conf"]})
        a = pair[0]
        meet[(s, frozenset((a["team"], a["opp"])))].append({"team": a["team"], "margin": a["margin"],
                                                            "venue": a["venue"], "stype": a["stype"], "night": a["night"]})
        eh, ea = elo[r["home"]], elo[r["away"]]
        hadv = 0 if neutral else 75
        exp = 1 / (1 + 10 ** (-(eh + hadv - ea) / 400))
        res = 1.0 if r["hs"] > r["as"] else 0.0
        mov = math.log(abs(r["hs"] - r["as"]) + 1) * 2.2 / ((abs(eh - ea) * 0.001) + 2.2)
        d = 20 * mov * (res - exp)
        elo[r["home"]] += d
        elo[r["away"]] -= d
    # Elo rank snapshot by season-night ('ranked' proxy = top 25 by Elo among teams with 3+ games this season)
    cur = {}
    by_n = defaultdict(list)
    for i, x in enumerate(rows):
        by_n[(x["season"], x["night"])].append(i)
    gp = Counter()
    for key in sorted(by_n):
        ii = by_n[key]
        s = key[0]
        pool = sorted((e for (ss, t), (e, n) in cur.items() if ss == s and n >= 3), reverse=True)
        cut25 = pool[24] if len(pool) >= 25 else None
        for i in ii:
            x = rows[i]
            x["orank25"] = cut25 is not None and x["oelo"] >= cut25
            x["rank25"] = cut25 is not None and x["elo"] >= cut25
            x["cut25"] = cut25
        for i in ii:
            x = rows[i]
            gp[(s, x["team"])] += 1
        # post-night Elo isn't stored per row; approximate with the pre-game Elo of each team's latest row
        for i in ii:
            x = rows[i]
            cur[(s, x["team"])] = (x["elo"], gp[(s, x["team"])])
    idx = defaultdict(list)
    for i, x in enumerate(rows):
        idx[(x["season"], x["team"])].append(i)
    for ii in idx.values():
        for j, i in enumerate(ii):
            rows[i]["next_i"] = ii[j + 1] if j + 1 < len(ii) else None
            rows[i]["prev_i"] = ii[j - 1] if j > 0 else None
    pickle.dump(rows, open(pk, "wb"))
    return rows


def profit_ml(x):
    return (dec(x["ml"]) - 1) if x["won"] else -1.0


def profit_ats(x):
    if x.get("cover") is None:
        return None
    return (dec(x["spodds"]) - 1) if x["cover"] else -1.0


def profit_open(x):
    if not x.get("mlo"):
        return None
    return (dec(x["mlo"]) - 1) if x["won"] else -1.0


def st(ps):
    if not ps:
        return None
    n = len(ps)
    m = sum(ps) / n
    sd = statistics.pstdev(ps) if n > 1 else 1.0
    return {"n": n, "roi": m, "z": (m / (sd / math.sqrt(n))) if sd else 0.0}


def cell(name, rows, fn=profit_ml):
    """all / train (seasons up) / held seasons / the OPEN price on the held seasons (the 2nd check)."""
    bets = [(x["season"], fn(x)) for x in rows]
    bets = [(s, p) for s, p in bets if p is not None]
    if not bets:
        return {"name": name, "all": None}
    by = defaultdict(list)
    for s, p in bets:
        by[s].append(p)
    o = {"name": name, "all": st([p for _, p in bets]),
         "train": st([p for s, p in bets if TRAIN[0] <= s <= TRAIN[1]]),
         "held": st([p for s, p in bets if s in HELD]),
         "tr_up": sum(1 for s, v in by.items() if TRAIN[0] <= s <= TRAIN[1] and sum(v) > 0),
         "tr_n": sum(1 for s in by if TRAIN[0] <= s <= TRAIN[1]),
         "ho_up": sum(1 for s, v in by.items() if s in HELD and sum(v) > 0),
         "ho_n": sum(1 for s in by if s in HELD),
         "by": {s: st(v) for s, v in sorted(by.items())}}
    if fn is profit_ml:
        op = [profit_open(x) for x in rows if x["season"] in HELD]
        o["open"] = st([p for p in op if p is not None])
    return o


def fmt(o):
    if not o.get("all"):
        return f"{o['name']:64s} n 0"

    def f(s):
        return f"{s['roi']*100:+6.1f}% n{s['n']:<5d}" if s else "    -         "
    by = " ".join(f"{str(s)[2:]}:{v['roi']*100:+.0f}" for s, v in o["by"].items() if v)
    extra = f" | open(held) {f(o['open'])}" if o.get("open") else ""
    return (f"{o['name']:64s} ALL {f(o['all'])} z{o['all']['z']:+.1f} | TR {f(o['train'])} {o['tr_up']}/{o['tr_n']} up"
            f" | HELD {f(o['held'])} {o['ho_up']}/{o['ho_n']} up{extra} | {by}")


def regular(rows):
    return [x for x in rows if x["stype"] == "2" and x["season"] >= 2018]


def dogs(rows, lo=100, hi=350):
    return [x for x in rows if x.get("ml") is not None and lo <= x["ml"] <= hi]


def favs(rows, lo=-150, hi=-101):
    return [x for x in rows if x.get("ml") is not None and lo <= x["ml"] <= hi]


def spreads(rows):
    return [x for x in rows if x.get("cover") is not None]


class Out:
    """Collects lines to print + save (sN_out.txt) and a count of cells looked at."""
    def __init__(self, name):
        self.name, self.lines, self.cells = name, [], 0

    def h(self, t):
        self.lines.append("")
        self.lines.append("== " + t)
        print("\n== " + t)

    def c(self, name, rows, fn=profit_ml):
        o = cell(name, rows, fn)
        self.cells += 1
        s = fmt(o)
        self.lines.append(s)
        print(s)
        return o

    def note(self, t):
        self.lines.append(t)
        print(t)

    def save(self):
        self.lines.append(f"\ncells looked at: {self.cells}")
        open(os.path.join(OUT, self.name + "_out.txt"), "w").write("\n".join(self.lines) + "\n")
