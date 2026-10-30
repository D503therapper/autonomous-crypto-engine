"""Shared helpers for the 10/30 daily studies (read-only on the repo; caches land in this folder as _cache_*.pkl).
Football: the paid odds history (every book's timestamped prices), oriented by team, FAIR looks only
(tools/early_football_study.ready_at / fair - posted after both teams' last games ended, no look-ahead).
Every study: TRAIN = the old seasons, HELD OUT = each newer season apart, NOW = 2026; graded on the result at the price."""
import gzip, json, math, os, pickle, statistics, sys
from datetime import timedelta

OUT = os.path.dirname(os.path.abspath(__file__))
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
    cache = os.path.join(OUT, f"_cache_{lg}.pkl")
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
