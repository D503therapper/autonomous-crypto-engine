"""11/12 - FABLE: 15 STUDIES - BIG FAVORITES, SPREADS, TOTALS: the shared table. Read-only on the repo; caches in
~/.cache/d503_fifteen1112 (never the repo).

One walk-forward table a league from data/sports/games/<lg>/*.csv: every final, with each side's facts stamped BEFORE
the game (rest, back-to-back, 3 in 4, games played, scoring for / against, how its games have run against the total and
the spread) - only this season's earlier games, plus last season's averages. Seasons are named by the year they start.
TRAIN = to 2021, BLIND = 2022 on (the totals studies' split; our closes start in 2018). Every bet is graded at the CLOSE
at its own juice (-110 when the price is missing); a push returns 0. z = the mean profit a bet over its standard error.
CELLS counts every printed cell (the multiple-testing count)."""
import csv, glob, math, os, pickle, random, statistics
from collections import defaultdict
from datetime import datetime, timedelta

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "d503_fifteen1112")
os.makedirs(CACHE, exist_ok=True)
TRAIN_TO = 2021
CELLS = [0]
OT_AT = {"nba": 4, "nfl": 4, "ncaaf": 4, "ncaab": 2, "nhl": 3}


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def season(start, lg):
    y, m = int(start[:4]), int(start[5:7])
    if lg in ("ncaab", "nba", "nhl"):
        if lg in ("nba", "nhl") and y == 2020 and m <= 10:
            return 2019
        return y if m >= 8 else y - 1
    return y if m >= 3 else y - 1


def day(start):
    """The US game day (UTC - 6h)."""
    return (datetime.strptime(start[:16], "%Y-%m-%dT%H:%M") - timedelta(hours=6)).date()


def dec(o):
    o = o or -110
    return 1 + (o / 100 if o > 0 else 100 / -o)


def ls(v):
    try:
        x = [float(t) for t in str(v).split(",") if t != ""]
        return x or None
    except ValueError:
        return None


_MEMO = {}


def table(lg, fresh=False):
    """(memoized: every caller in a run gets the same row objects)"""
    if lg not in _MEMO or fresh:
        _MEMO[lg] = _table(lg, fresh)
    return _MEMO[lg]


def _table(lg, fresh=False):
    p = os.path.join(CACHE, f"t_{lg}.pkl")
    if os.path.exists(p) and not fresh:
        return pickle.load(open(p, "rb"))
    raw = []
    for f in sorted(glob.glob(os.path.join(ROOT, f"data/sports/games/{lg}/*.csv"))):
        for r in csv.DictReader(open(f)):
            if r["status"] == "final" and num(r["home_score"]) is not None:
                raw.append(r)
    raw.sort(key=lambda r: r["start"])
    hist = defaultdict(list)
    prev = {}                                    # (season, team) -> that season's averages (read as s - 1 only)
    rows = []
    for r in raw:
        s = season(r["start"], lg)
        d = day(r["start"])
        hs, as_ = num(r["home_score"]), num(r["away_score"])
        g = {"id": r["id"], "lg": lg, "start": r["start"], "season": s, "day": d, "home": r["home"], "away": r["away"],
             "hn": r["home_name"], "an": r["away_name"], "hs": hs, "as": as_, "neutral": str(r["neutral"]) == "1",
             "stype": r["stype"], "mlh": num(r["ml_home"]) or None, "mla": num(r["ml_away"]) or None,
             "oh": num(r["ml_home_open"]) or None, "oa": num(r["ml_away_open"]) or None, "sp": num(r["spread_home"]),
             "spho": num(r["spread_home_odds"]), "spao": num(r["spread_away_odds"]), "tot": num(r["total"]),
             "ovo": num(r["over_odds"]), "uno": num(r["under_odds"]), "h1sp": num(r["h1_spread_home"]),
             "h1ho": num(r["h1_spread_home_odds"]), "h1ao": num(r["h1_spread_away_odds"]), "lsh": ls(r["ls_home"]),
             "lsa": ls(r["ls_away"]), "elev": num(r["elev"]), "indoor": r.get("indoor"), "wind": num(r.get("wx_wind")),
             "temp": num(r.get("wx_temp")), "rain": num(r.get("wx_rain")), "gh": r.get("sp_home") or "",
             "ga": r.get("sp_away") or "", "tzo": num(r.get("tzo")), "city": r.get("city"), "intl": r.get("intl")}
        for side, t in (("H", r["home"]), ("A", r["away"])):
            Hh = hist[(s, t)]
            f = {"n": len(Hh), "prev": prev.get((s - 1, t))}
            if Hh:
                L = Hh[-1]
                f["rest"] = (d - L["day"]).days
                f["b2b"] = f["rest"] == 1
                f["g4"] = sum(1 for x in Hh if (d - x["day"]).days <= 3)        # games in the 3 days before
                f["g6"] = sum(1 for x in Hh if (d - x["day"]).days <= 5)
                f["pf"] = sum(x["pf"] for x in Hh) / len(Hh)
                f["pa"] = sum(x["pa"] for x in Hh) / len(Hh)
                f["w"] = sum(1 for x in Hh if x["m"] > 0)
                tms = [x["tm"] for x in Hh if x["tm"] is not None]
                f["tm"], f["tmn"] = (sum(tms) / len(tms) if tms else None), len(tms)
                cms = [x["cm"] for x in Hh if x["cm"] is not None]
                f["cm"], f["cmn"] = (sum(cms) / len(cms) if cms else None), len(cms)
                f["last"] = L
                f["l5pf"] = sum(x["pf"] for x in Hh[-5:]) / len(Hh[-5:])
                f["l5pa"] = sum(x["pa"] for x in Hh[-5:]) / len(Hh[-5:])
                k = 0
                for x in reversed(Hh):
                    if x["ven"] != "A":
                        break
                    k += 1
                f["road_run"] = k
            g[side] = f
        rows.append(g)
        m, pts = hs - as_, hs + as_
        tot, sp = g["tot"], g["sp"]
        ot = bool(g["lsh"]) and len(g["lsh"]) > OT_AT.get(lg, 9)
        for t, o, ven, mt, pf, pa, spx, gl in ((r["home"], r["away"], "N" if g["neutral"] else "H", m, hs, as_, sp, g["gh"]),
                                               (r["away"], r["home"], "N" if g["neutral"] else "A", -m, as_, hs,
                                                -sp if sp is not None else None, g["ga"])):
            hist[(s, t)].append({"day": d, "ven": ven, "m": mt, "pf": pf, "pa": pa, "opp": o, "id": r["id"], "g": gl,
                                 "tm": (pts - tot) if tot is not None else None, "tot": tot, "sp": spx,
                                 "cm": (mt + spx) if spx is not None else None, "stype": r["stype"], "ot": ot})
            Hh = hist[(s, t)]
            prev[(s, t)] = {"n": len(Hh), "pf": sum(x["pf"] for x in Hh) / len(Hh), "pa": sum(x["pa"] for x in Hh) / len(Hh),
                            "w": sum(1 for x in Hh if x["m"] > 0) / len(Hh)}
    pickle.dump(rows, open(p, "wb"))
    return rows


def reg(g):
    return g["stype"] == "2"


# ---------------- bets (profit on 1 unit; None = no price) ----------------
def ml(g, side, opn=False):
    o = (g["oh"] if side == "H" else g["oa"]) if opn else (g["mlh"] if side == "H" else g["mla"])
    if o is None or g["hs"] == g["as"]:
        return None
    won = (g["hs"] > g["as"]) == (side == "H")
    return dec(o) - 1 if won else -1.0


def odds(g, side, opn=False):
    if opn:
        return g["oh"] if side == "H" else g["oa"]
    return g["mlh"] if side == "H" else g["mla"]


def fav(g):
    """The closing favorite's side ('H' / 'A') or None."""
    if g["mlh"] is None or g["mla"] is None or g["mlh"] == g["mla"]:
        return None
    return "H" if g["mlh"] < g["mla"] else "A"


def ats(g, side, shift=0.0):
    """side at the closing spread (+ shift points its way), its own juice."""
    if g["sp"] is None:
        return None
    r = g["hs"] - g["as"] + g["sp"]
    if side == "A":
        r = -r
    r += shift
    o = g["spho"] if side == "H" else g["spao"]
    if o is None or abs(o) < 100 or abs(o) > 160:
        o = -110
    return 0.0 if r == 0 else (dec(o) - 1 if r > 0 else -1.0)


def spread(g, side):
    return None if g["sp"] is None else (g["sp"] if side == "H" else -g["sp"])


def tot(g, side, shift=0.0):
    """'over' / 'under' at the closing total (+ shift points OUR way), its own juice."""
    if g["tot"] is None:
        return None
    pts = g["hs"] + g["as"]
    line = g["tot"] + (-shift if side == "over" else shift)
    o = g["ovo"] if side == "over" else g["uno"]
    if o is None or abs(o) < 100 or abs(o) > 170:
        o = -110
    if pts == line:
        return 0.0
    return dec(o) - 1 if (pts > line) == (side == "over") else -1.0


def other(side):
    return "A" if side == "H" else "H"


# ---------------- cells ----------------
def stats(ps):
    n = len(ps)
    if not n:
        return dict(n=0, roi=0.0, z=0.0, w=0, l=0)
    m = sum(ps) / n
    sd = statistics.pstdev(ps) if n > 1 else 0
    return dict(n=n, roi=m, z=(m / (sd / math.sqrt(n)) if sd else 0.0), w=sum(1 for p in ps if p > 0),
                l=sum(1 for p in ps if p < 0))


def cell(label, bets, train_to=TRAIN_TO, show=True):
    """bets = [(season, profit or None)] -> one printed line: all / train / blind + the seasons."""
    CELLS[0] += 1
    bs = [(s, p) for s, p in bets if p is not None]
    a = stats([p for _, p in bs])
    tr = stats([p for s, p in bs if s <= train_to])
    bl = stats([p for s, p in bs if s > train_to])
    by = defaultdict(list)
    for s, p in bs:
        by[s].append(p)
    up_tr = sum(1 for s in by if s <= train_to and sum(by[s]) > 0)
    n_tr = sum(1 for s in by if s <= train_to)
    up_bl = sum(1 for s in by if s > train_to and sum(by[s]) > 0)
    n_bl = sum(1 for s in by if s > train_to)
    ss = " ".join(f"{str(s)[2:]}:{100 * sum(v) / len(v):+.0f}/{len(v)}" for s, v in sorted(by.items()))
    if show:
        print(f"{label[:60]:<60} {a['w']}-{a['l']} {100 * a['roi']:+6.1f}% n{a['n']:<5} z{a['z']:+.1f} | "
              f"TR {100 * tr['roi']:+6.1f}% n{tr['n']:<4} {up_tr}/{n_tr} | BL {100 * bl['roi']:+6.1f}% n{bl['n']:<4} "
              f"z{bl['z']:+.1f} {up_bl}/{n_bl} | {ss}")
    return dict(all=a, train=tr, blind=bl, up_tr=up_tr, n_tr=n_tr, up_bl=up_bl, n_bl=n_bl, bets=bs)


def placebo(pool, n, target, k=2000, seed=7):
    """How many of k random n-bet draws from pool (profits) do as well as target (a mean profit)."""
    rnd = random.Random(seed)
    pool = [p for p in pool if p is not None]
    if len(pool) < n or not n:
        return None
    return sum(1 for _ in range(k) if sum(rnd.sample(pool, n)) / n >= target)


def worst(ps):
    """The worst peak-to-trough run of a profit list in order."""
    peak = run = dd = 0.0
    for p in ps:
        run += p
        peak = max(peak, run)
        dd = min(dd, run - peak)
    return dd


def done():
    print(f"\ncells printed: {CELLS[0]}")
