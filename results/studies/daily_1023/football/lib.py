"""Shared loader for the 10/23 football studies. Read-only on the repo worktree.
Per game: every FAIR look (posted after both teams' last games ended - early_football_study.fair) of the
moneyline books and the spread books, oriented home/away, plus the closing game-file prices and the result."""
import gzip, json, os, statistics, sys, math, pickle
from datetime import timedelta

WT = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/wt"
OUT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WT)
os.chdir(WT)
import sports_data as sd                      # noqa: E402
import sports_model as sm                     # noqa: E402
from tools import early_football_study as ef  # noqa: E402

SP = {"nfl": "americanfootball_nfl", "ncaaf": "americanfootball_ncaaf"}
_t, dec = ef._t, ef._dec


def season(start):
    y = int(start[:4])
    return y if int(start[5:7]) >= 7 else y - 1


def nv(h, a):
    ph, pa = 1 / dec(h), 1 / dec(a)
    return ph / (ph + pa)


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


def load(lg):
    cache = os.path.join(OUT, f"cache_{lg}.pkl")
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
                fl = flip if r["h"] == rs[0]["h"] else (not flip)   # a book list that swaps home/away mid-week
                days = (_t(g["start"]) - _t(r["snap"])).total_seconds() / 86400
                if days < 0.03 or days > 8 or not ef.fair(ready, g["id"], g["start"], days):
                    continue
                books = {}
                for bk, v in r["b"].items():
                    if not v or any(x is None for x in v):
                        continue
                    if kind == "ml":
                        h, a = v[0], v[1]
                        books[bk] = (a, h) if fl else (h, a)
                    else:
                        hp, hpr, ap, apr = v
                        books[bk] = (ap, apr, hp, hpr) if fl else (hp, hpr, ap, apr)
                if len(books) >= 3:
                    out.setdefault(g["id"], {"ml": [], "sp": []})[kind].append((days, books))
    res = []
    for gid, d in out.items():
        g = fin[gid]
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except ValueError:
            continue
        d["ml"].sort(key=lambda x: -x[0])
        d["sp"].sort(key=lambda x: -x[0])
        res.append({"id": gid, "start": g["start"], "season": season(g["start"]), "margin": hs - as_,
                    "home": g["home"], "away": g["away"], "ml": d["ml"], "sp": d["sp"],
                    "neutral": str(g.get("neutral")) == "1",
                    "c_sp": g.get("spread_home"), "c_sho": g.get("spread_home_odds"), "c_sao": g.get("spread_away_odds"),
                    "c_mlh": g.get("ml_home"), "c_mla": g.get("ml_away")})
    pickle.dump(res, open(cache, "wb"))
    return res


def ml_med(books):
    """-> (median home american, median away american, no-vig home %)."""
    h = statistics.median(dec(v[0]) for v in books.values())
    a = statistics.median(dec(v[1]) for v in books.values())
    return h, a, (1 / h) / (1 / h + 1 / a)


def sp_med(books):
    """-> (median home points, median home price dec, median away price dec)."""
    return (statistics.median(v[0] for v in books.values()),
            statistics.median(dec(v[1]) for v in books.values()),
            statistics.median(dec(v[3]) for v in books.values()))


def first_last(looks):
    """first FAIR look 1.5..7.5 days out, last look before kickoff (0.03..1.5 days). None if missing."""
    early = [x for x in looks if 1.5 <= x[0] < 7.5]
    late = [x for x in looks if 0.03 <= x[0] < 1.5]
    if not early or not late:
        return None
    return early[0], late[-1]


def summ(bets, train=(2020, 2024)):
    """bets: [(season, profit)] -> dict"""
    if not bets:
        return None
    def s(bs):
        if not bs:
            return None
        n = len(bs); p = [b[1] for b in bs]
        m = sum(p) / n
        sdv = statistics.pstdev(p) if n > 1 else 1
        return {"n": n, "win": round(sum(1 for x in p if x > 0) / n, 3), "roi": round(m, 3),
                "z": round(m / (sdv / math.sqrt(n)), 2) if sdv else 0}
    by = {}
    for se, pr in bets:
        by.setdefault(se, []).append((se, pr))
    seas = {k: s(v) for k, v in sorted(by.items())}
    return {"all": s(bets), "train": s([b for b in bets if train[0] <= b[0] <= train[1]]),
            "hold2025": s([b for b in bets if b[0] == 2025]), "cur2026": s([b for b in bets if b[0] == 2026]),
            "seasons": {k: (v["n"], v["roi"]) for k, v in seas.items()},
            "up": f"{sum(1 for v in seas.values() if v['roi'] > 0)}/{len(seas)}"}


def line(name, r):
    if not r:
        return f"  {name:55s} -"
    a, t, h, c = r["all"], r["train"], r["hold2025"], r["cur2026"]
    f = lambda x: f"{x['n']}/{x['roi']:+.1%}" if x else "-"
    return (f"  {name:55s} n {a['n']:4d} win {a['win']:.1%} ROI {a['roi']:+.1%} z {a['z']:+.1f} | train {f(t)} "
            f"| hold25 {f(h)} | 2026 {f(c)} | up {r['up']} {r['seasons']}")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def sp_dec(o):
    o = num(o)
    return dec(o) if o is not None and (o <= -100 or o >= 100) and -200 < o < 200 else dec(-110)


def cover(r, side, pts, price_dec):
    """side 'h'/'a'; pts = that side's points. -> profit or None on a push."""
    m = r["margin"] if side == "h" else -r["margin"]
    x = m + pts
    if x == 0:
        return None
    return price_dec - 1 if x > 0 else -1.0


def mlp(r, side, price_dec):
    won = r["margin"] > 0 if side == "h" else r["margin"] < 0
    if r["margin"] == 0:
        return None
    return price_dec - 1 if won else -1.0
