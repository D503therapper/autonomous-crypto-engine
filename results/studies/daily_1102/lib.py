"""Shared helpers for the 11/2 daily studies (copied from daily_1101/lib.py, + venues / NBA morning looks / box points) (read-only on the repo; caches land in the scratchpad, never the repo).
Football: the paid odds history (every book's timestamped prices), oriented by team, FAIR looks only
(tools/early_football_study.ready_at / fair - posted after both teams' last games ended, no look-ahead).
Every study: TRAIN = the old seasons, HELD OUT = each newer season apart, NOW = 2026; graded on the result at the price."""
import gzip, json, math, os, pickle, statistics, sys
from datetime import timedelta

OUT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get("STUDY_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "d503_studies")
os.makedirs(CACHE, exist_ok=True)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_data as sd                      # noqa: E402
import sports_model as sm                     # noqa: E402
from tools import early_football_study as ef  # noqa: E402

SP = {"nfl": "americanfootball_nfl", "ncaaf": "americanfootball_ncaaf"}
_t = ef._t


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


def nv(h, a):
    ph, pa = 1 / dec(h), 1 / dec(a)
    return ph / (ph + pa)


def profit(won, d):
    return (d - 1) if won else -1.0


def stats(ps):
    if not ps:
        return None
    n = len(ps)
    m = sum(ps) / n
    sdv = statistics.pstdev(ps) if n > 1 else 1.0
    return {"n": n, "win": round(sum(1 for x in ps if x > 0) / n, 3), "roi": round(m, 3),
            "z": round(m / (sdv / math.sqrt(n)), 2) if sdv else 0.0}


def summ(bets, train, held):
    """bets: [(season, profit)]; train = (lo, hi) seasons; held = held-out seasons (each shown apart)."""
    if not bets:
        return None
    by = {}
    for s, p in bets:
        by.setdefault(s, []).append(p)
    out = {"all": stats([p for _, p in bets]),
           "train": stats([p for s, p in bets if train[0] <= s <= train[1]]),
           "train_up": f"{sum(1 for s, v in by.items() if train[0] <= s <= train[1] and sum(v) > 0)}/"
                       f"{sum(1 for s in by if train[0] <= s <= train[1])}"}
    for h in held:
        out[str(h)] = stats(by.get(h, []))
    out["held_all"] = stats([p for s, p in bets if s in held])
    return out


def fmt(name, r):
    if not r:
        return f"{name:58s} -"

    def f(x):
        return f"{x['n']:5d} {x['roi']*100:+6.1f}% z{x['z']:+5.2f}" if x else "    -              "
    held = [k for k in r if k.isdigit()]
    return (f"{name:58s} ALL {f(r['all'])} | TRAIN {f(r['train'])} up {r['train_up']} | "
            + " | ".join(f"{k} {f(r[k])}" for k in held) + f" | HELD {f(r['held_all'])}")


# ---------------- football odds history ----------------
def _events(path):
    ev = {}
    with gzip.open(path, "rt") as f:
        for x in f:
            r = json.loads(x)
            if "b" in r:
                ev.setdefault(r["id"], []).append(r)
    return ev


def _find(r, by_day):
    t = _t(r["t"])
    for d in (-1, 0, 1):
        for g in by_day.get((t + timedelta(days=d)).strftime("%Y-%m-%d"), []):
            if abs((_t(g["start"]) - t).total_seconds()) > 14 * 3600:
                continue
            if sd._same(g.get("home_name") or "", r["h"]) and sd._same(g.get("away_name") or "", r["a"]):
                return g, False
            if sd._same(g.get("home_name") or "", r["a"]) and sd._same(g.get("away_name") or "", r["h"]):
                return g, True
    return None, None


def load_football(lg):
    """-> games sorted by start: {id, start, season, home, away, margin, ml: [(days out, {book: (home, away)})] FAIR
    looks oldest first, sp: [(days, {book: (hpts, hpr, apts, apr)})] fair, all_ml: every look 0.03-8 days out (fair or
    not - only for which books post), closing prices from the game file}."""
    cache = os.path.join(CACHE, f"_cache_{lg}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    games = sd.load_games(lg)
    fin = {g["id"]: g for g in sm.finals(games, lg)}
    ready = ef.ready_at(games, lg)
    by_day = {}
    for g in fin.values():
        by_day.setdefault(g["start"][:10], []).append(g)
    out = {}
    for kind, path in (("ml", f"{SP[lg]}.jsonl.gz"), ("sp", f"{SP[lg]}_spreads.jsonl.gz")):
        ev = _events(os.path.join(sd.DATA, "odds_history", path))
        for eid, rs in ev.items():
            g, flip = _find(rs[0], by_day)
            if not g:
                continue
            for r in rs:
                fl = flip if r["h"] == rs[0]["h"] else (not flip)     # a feed that swaps home / away mid-week
                days = (_t(g["start"]) - _t(r["snap"])).total_seconds() / 86400
                if days < 0.03 or days > 8:
                    continue
                isfair = ef.fair(ready, g["id"], g["start"], days)
                books = {}
                for bk, v in r["b"].items():
                    if not v or any(x is None for x in v):
                        continue
                    if kind == "ml":
                        books[bk] = (v[1], v[0]) if fl else (v[0], v[1])
                    else:
                        hp, hpr, ap, apr = v
                        books[bk] = (ap, apr, hp, hpr) if fl else (hp, hpr, ap, apr)
                if len(books) >= 3:
                    d = out.setdefault(g["id"], {"ml": [], "sp": [], "all_ml": []})
                    if kind == "ml":
                        d["all_ml"].append((days, books))
                    if isfair:
                        d[kind].append((days, books))
    res = []
    for gid, d in out.items():
        g = fin[gid]
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (ValueError, KeyError):
            continue
        for k in ("ml", "sp", "all_ml"):
            d[k].sort(key=lambda x: -x[0])
        res.append({"id": gid, "start": g["start"], "season": season(g["start"]), "margin": hs - as_,
                    "home": g["home"], "away": g["away"], "ml": d["ml"], "sp": d["sp"], "all_ml": d["all_ml"],
                    "neutral": str(g.get("neutral")) == "1",
                    "c_sp": num(g.get("spread_home")), "c_sho": num(g.get("spread_home_odds")),
                    "c_sao": num(g.get("spread_away_odds")),
                    "c_mlh": num(g.get("ml_home")), "c_mla": num(g.get("ml_away")), "total": num(g.get("total"))})
    res.sort(key=lambda x: x["start"])
    pickle.dump(res, open(cache, "wb"))
    return res


def ml_med(books):
    h = statistics.median(dec(v[0]) for v in books.values())
    a = statistics.median(dec(v[1]) for v in books.values())
    return h, a, (1 / h) / (1 / h + 1 / a)


def sp_med(books):
    return (statistics.median(v[0] for v in books.values()),
            statistics.median(dec(v[1]) for v in books.values()),
            statistics.median(dec(v[3]) for v in books.values()))


def first_fair(looks):
    e = [x for x in looks if 1.5 <= x[0] < 7.5]
    return e[0] if e else None


def last_look(looks):
    lst = [x for x in looks if 0.03 <= x[0] < 1.5]
    return lst[-1] if lst else None


def side_ml(g, side, books):
    """median decimal price + no-vig % for `side` ('home'/'away') at a look."""
    h, a, p = ml_med(books)
    return (h, p) if side == "home" else (a, 1 - p)


# ---------------- game files at the close (NBA / NHL / college hoops / football) ----------------
def finals(lg):
    """Finished regular-season games with a closing moneyline, sorted by start (cached)."""
    cache = os.path.join(CACHE, f"_fin2_{lg}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    out = []
    for g in sm.finals(sd.load_games(lg), lg):
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (ValueError, KeyError, TypeError):
            continue
        h, a = num(g.get("ml_home")), num(g.get("ml_away"))
        if h is None or a is None or h == 0 or a == 0 or hs == as_:
            continue
        out.append({"id": g["id"], "start": g["start"], "season": season(g["start"]), "home": g["home"],
                    "away": g["away"], "hn": g.get("home_name"), "an": g.get("away_name"), "hs": hs, "as": as_,
                    "mlh": h, "mla": a, "oh": num(g.get("ml_home_open")), "oa": num(g.get("ml_away_open")),
                    "sp": num(g.get("spread_home")), "spho": num(g.get("spread_home_odds")),
                    "spao": num(g.get("spread_away_odds")), "total": num(g.get("total")),
                    "neutral": str(g.get("neutral")) == "1", "tzo": num(g.get("tzo")),
                    "stype": str(g.get("stype") or "2"), "ovo": num(g.get("over_odds")), "uno": num(g.get("under_odds")),
                    "ls_h": g.get("ls_home"), "ls_a": g.get("ls_away")})
    out.sort(key=lambda x: x["start"])
    pickle.dump(out, open(cache, "wb"))
    return out


def sides(g):
    """[(side, team, opp, american odds, won, is_home)] for both sides at the close."""
    hw = g["hs"] > g["as"]
    return [("home", g["home"], g["away"], g["mlh"], hw, True), ("away", g["away"], g["home"], g["mla"], not hw, False)]


def dog_band(o, lo=100, hi=350):
    return lo <= o <= hi


def ats(g, side):
    """(profit at the closing spread juice, or None) for side."""
    if g["sp"] is None:
        return None
    m = g["hs"] - g["as"]
    if side == "home":
        r, o = m + g["sp"], g["spho"] or -110
    else:
        r, o = -(m + g["sp"]), g["spao"] or -110
    if r == 0:
        return None
    return profit(r > 0, dec(o))


# ---------------- box scores (data/sports/roster/<lg>_<season>.csv.gz) ----------------
def boxes(lg, val):
    """{gid: {team id: {player id: val(stats dict, row)}}} for every saved box score of `lg` (cached per val name)."""
    import csv
    cache = os.path.join(CACHE, f"_box_{lg}_{val.__name__}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    out = {}
    d = os.path.join(sd.DATA, "roster")
    for fn in sorted(os.listdir(d)):
        if not fn.startswith(lg + "_") or not fn.endswith(".csv.gz"):
            continue
        with gzip.open(os.path.join(d, fn), "rt") as f:
            for r in csv.DictReader(f):
                try:
                    st = json.loads(r["stats"] or "{}")
                except ValueError:
                    st = {}
                v = val(st, r)
                if v is None:
                    continue
                out.setdefault(r["gid"], {}).setdefault(r["team"], {})[r["pid"]] = v
    pickle.dump(out, open(cache, "wb"))
    return out


# ---------------- 11/1 additions ----------------
def all_finals(lg):
    """Every finished game on file (priced or not), sorted by start: {id, start, season, home, away, hs, as, stype,
    neutral} - for schedules, rest and form (cached)."""
    cache = os.path.join(CACHE, f"_allfin_{lg}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    out = []
    for g in sm.finals(sd.load_games(lg), lg):
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (ValueError, KeyError, TypeError):
            continue
        out.append({"id": g["id"], "start": g["start"], "season": season(g["start"]), "home": g["home"],
                    "away": g["away"], "hs": hs, "as": as_, "stype": str(g.get("stype") or "2"),
                    "neutral": str(g.get("neutral")) == "1"})
    out.sort(key=lambda x: x["start"])
    pickle.dump(out, open(cache, "wb"))
    return out


def team_log(fin):
    """{team: [game dicts in order]} over a list of finals (sorted by start)."""
    tl = {}
    for g in fin:
        tl.setdefault(g["home"], []).append(g)
        tl.setdefault(g["away"], []).append(g)
    return tl


def _bis(lst, start):
    lo, hi = 0, len(lst)
    while lo < hi:
        m = (lo + hi) // 2
        if lst[m]["start"] < start:
            lo = m + 1
        else:
            hi = m
    return lo


def before(tl, team, start, n=None):
    """The team's finished games strictly before `start`, oldest first (the last n if given)."""
    lst = tl.get(team) or []
    i = _bis(lst, start)
    return lst[max(0, i - n):i] if n else lst[:i]


def days_between(a, b):
    return (_t(b) - _t(a)).total_seconds() / 86400


def american(d):
    return (d - 1) * 100 if d >= 2 else -100 / (d - 1)


def early_price(xby, gid, side):
    """(american, decimal) for `side` at the first FAIR look of the paid odds history (median book), or None."""
    x = xby.get(gid)
    if not x:
        return None
    f = first_fair(x["ml"])
    if not f:
        return None
    h, a, _ = ml_med(f[1])
    d = h if side == "home" else a
    return (american(d), d) if d > 1.0 else None


def tot_profit(g, over):
    """Profit of the over (over=True) / the under at the closing total and its juice; None on a push / no total."""
    if g["total"] is None:
        return None
    pts = g["hs"] + g["as"]
    if pts == g["total"]:
        return None
    o = (g["ovo"] if over else g["uno"]) or -110
    return profit((pts > g["total"]) == over, dec(o))


def won_g(g, team):
    return (g["hs"] > g["as"]) if g["home"] == team else (g["as"] > g["hs"])


def margin_g(g, team):
    return (g["hs"] - g["as"]) if g["home"] == team else (g["as"] - g["hs"])


class Cells:
    """cells[name] -> [(season, profit)]; dump() writes <tag>_out.txt / .json next to the script."""
    def __init__(self):
        from collections import defaultdict
        self.c = defaultdict(list)

    def add(self, k, s, p):
        if p is not None:
            self.c[k].append((s, p))

    def dump(self, tag, header, train, held=None):
        """train/held = one split, or train = callable(key) -> (train, held) per row (league-specific splits)."""
        sp = train if callable(train) else (lambda k: (train, held))
        res = {k: summ(v, *sp(k)) for k, v in sorted(self.c.items())}
        txt = "\n".join([header] + [fmt(k, v) for k, v in res.items()])
        print(txt)
        open(os.path.join(OUT, f"{tag}_out.txt"), "w").write(txt + "\n")
        json.dump(res, open(os.path.join(OUT, f"{tag}_out.json"), "w"), indent=1)
        return res


# ---------------- 11/2 additions ----------------
def coords(lg):
    """{gid: (lat, lon)} of each game's venue (the game file's city / state / country geocoded in venues.json)."""
    cache = os.path.join(CACHE, f"_coords_{lg}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    import sports_context as sc
    ven = sc.venues()
    out = {}
    for gid, g in sd.load_games(lg).items():
        w = sc._where(g, ven)
        if w:
            out[gid] = w
    pickle.dump(out, open(cache, "wb"))
    return out


def miles(a, b):
    import sports_context as sc
    return sc.miles(a, b)


def nba_morning():
    """{gid: {"p": no-vig home % at the game-day 15:00Z look, "dh"/"da": median decimal prices, "pt": the median home
    spread at that look (or None)}} from the paid NBA history 2020-23 (results/studies/nba_odds_1102/lib.py's parser,
    cached here in the scratch cache, never in the repo)."""
    cache = os.path.join(CACHE, "_nba_morning.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("nbaodds", os.path.join(ROOT, "results/studies/nba_odds_1102/lib.py"))
    m = importlib.util.module_from_spec(spec)
    here = os.getcwd()
    spec.loader.exec_module(m)
    os.chdir(here)
    m.OUT = CACHE                                   # its looks() cache goes to the scratch cache
    games = m.load_games()
    lk = m.looks(games)
    prev = m.prev_tips(games)
    out = {}
    for gid in lk:
        op, mo = m.pick_looks(lk, prev, gid)
        sop, smo = m.sp_looks(lk, prev, gid)
        if mo or smo:
            out[gid] = {"p": mo["p"] if mo else None, "dh": mo["dh"] if mo else None, "da": mo["da"] if mo else None,
                        "pt": smo["pt"] if smo else None}
    pickle.dump(out, open(cache, "wb"))
    return out
