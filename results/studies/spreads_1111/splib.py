"""Shared helpers for the 11/11 PRO-STYLE SPREAD MODEL studies (results/studies/spreads_1111).
Read-only on the repo; caches in ~/.cache/d503_spreads1111 (never the repo). Builds on fable_1111/lib.py (`L`) and
daily_1110/lib.py (`B`: finals at the close, the paid football odds history's FAIR looks).
NFL play-by-play: nflverse's public season files (fetch_pbp.py), boiled down to one line per team per game."""
import csv, gzip, importlib.util, math, os, pickle, statistics, sys
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
_spec = importlib.util.spec_from_file_location("fable1111", os.path.join(ROOT, "results", "studies", "fable_1111", "lib.py"))
L = importlib.util.module_from_spec(_spec)
sys.path.insert(0, os.path.join(ROOT, "results", "studies", "fable_1111"))
_spec.loader.exec_module(L)
B = L.B
L.OUT = B.OUT = OUT
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "d503_spreads1111")
DL = os.path.join(CACHE, "dl")
os.makedirs(DL, exist_ok=True)
dec, num, profit, stats = B.dec, B.num, B.profit, B.stats
csv.field_size_limit(10 ** 9)


def cached(name, fn):
    p = os.path.join(CACHE, name + ".pkl")
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    v = fn()
    pickle.dump(v, open(p, "wb"))
    return v


class Out(L.Out):
    def save(self):
        open(os.path.join(OUT, self.tag + "_out.txt"), "w").write("\n".join(self.lines) + "\n")


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def pbp_games():
    """-> [{gid, season, week, date, home, away, hs, as, close (home spread, minus = home favored, nflverse's),
    reg, teams: {abbr: {pn, pe, ps, py (dropbacks, EPA, successes, yards), rn, re, rs, ry (runs), the same with a
    leading 'c' = competitive plays only (win chance 5-95%), to (turnovers), qb: [(passer id, name, dropbacks,
    EPA)] in order of first dropback}}}] sorted by date - every game 2015-26 (cached)."""
    def mk():
        out = []
        for y in range(2015, 2027):
            p = os.path.join(DL, f"pbp_{y}.csv.gz")
            if not os.path.exists(p):
                continue
            gs = {}
            with gzip.open(p, "rt") as fh:
                for r in csv.DictReader(fh):
                    g = gs.get(r["game_id"])
                    if g is None:
                        sl = _f(r["spread_line"])
                        g = gs[r["game_id"]] = {
                            "gid": r["game_id"], "season": y, "week": int(r["week"]), "date": r["game_date"],
                            "home": r["home_team"], "away": r["away_team"], "hs": _f(r["home_score"]),
                            "as": _f(r["away_score"]), "close": -sl if sl is not None else None,
                            "reg": r["season_type"] == "REG", "neutral": r["location"] == "Neutral",
                            "teams": {r["home_team"]: defaultdict(float), r["away_team"]: defaultdict(float)},
                            "qb": {r["home_team"]: {}, r["away_team"]: {}}}
                    t = r["posteam"]
                    e = _f(r["epa"])
                    if t not in g["teams"] or e is None or r["two_point_attempt"] == "1":
                        continue
                    if r["qb_kneel"] == "1" or r["qb_spike"] == "1":
                        continue
                    ip, ir = r["pass"] == "1", r["rush"] == "1"
                    if not (ip or ir):
                        continue
                    d = g["teams"][t]
                    k = "p" if ip else "r"
                    wp = _f(r["wp"])
                    comp = wp is not None and 0.05 <= wp <= 0.95
                    yd = _f(r["yards_gained"]) or 0.0
                    su = 1.0 if r["success"] == "1" else 0.0
                    for pre in (("", "c") if comp else ("",)):
                        d[pre + k + "n"] += 1
                        d[pre + k + "e"] += e
                        d[pre + k + "s"] += su
                        d[pre + k + "y"] += yd
                    if r["interception"] == "1" or r["fumble_lost"] == "1":
                        d["to"] += 1
                    if ip and r["passer_player_id"]:
                        q = g["qb"][t].setdefault(r["passer_player_id"], [r["passer_player_name"], 0, 0.0, 0, 0.0])
                        q[1] += 1
                        q[2] += e
                        if comp:
                            q[3] += 1
                            q[4] += e
            for g in gs.values():
                g["teams"] = {t: dict(d) for t, d in g["teams"].items()}
                g["qb"] = {t: [(pid, v[0], v[1], v[2], v[3], v[4]) for pid, v in d.items()] for t, d in g["qb"].items()}
                if g["hs"] is not None and all(d.get("pn", 0) + d.get("rn", 0) >= 20 for d in g["teams"].values()):
                    out.append(g)
        out.sort(key=lambda g: (g["date"], g["gid"]))
        return out
    return cached("pbp_games", mk)


def link_repo(pg):
    """{nflverse game id: our game dict (B.load_football row or a game-file final)} - matched on the date (+-1 day,
    our starts are UTC) and the final score, home / away by the score."""
    fin = B.all_finals("nfl")
    by = defaultdict(list)
    for g in fin:
        by[g["start"][:10]].append(g)
    from datetime import date, timedelta
    out = {}
    for g in pg:
        d0 = date.fromisoformat(g["date"])
        for dd in (0, 1):
            hit = [x for x in by.get((d0 + timedelta(days=dd)).isoformat(), []) if x["hs"] == g["hs"] and x["as"] == g["as"]]
            if len(hit) == 1:
                out[g["gid"]] = hit[0]
                break
    return out


def ridge_w(X, y, w, lam, free=()):
    """Weighted ridge; columns in `free` are not penalised (the mean, the home field)."""
    import numpy as np
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    w = np.asarray(w, float)
    P = lam * np.eye(X.shape[1])
    for j in free:
        P[j, j] = 1e-6
    Xw = X * w[:, None]
    return np.linalg.solve(X.T @ Xw + P, Xw.T @ y)


def ats_profit(margin_home, line_home, side, price=-110):
    """Profit on 1 at `price` for `side` laying / taking `line_home` (the home team's spread, its own sign for the
    away side is -line_home). A push pays 0."""
    r = margin_home + line_home
    if side == "away":
        r = -r
    if r == 0:
        return 0.0
    d = dec(price)
    return (d - 1) if r > 0 else -1.0


def line_stats(ps):
    """n, win % (pushes out), ROI, z for a list of profits."""
    if not ps:
        return "    0      -       -"
    n = len(ps)
    w = sum(1 for x in ps if x > 0)
    l = sum(1 for x in ps if x < 0)
    m = sum(ps) / n
    sdv = statistics.pstdev(ps) if n > 1 else 1.0
    z = m / (sdv / math.sqrt(n)) if sdv else 0.0
    return f"{n:5d} {w / max(1, w + l) * 100:5.1f}% {m * 100:+6.1f}% z{z:+5.2f}"
