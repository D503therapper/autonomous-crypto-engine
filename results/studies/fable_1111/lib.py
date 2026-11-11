"""Shared helpers for the 11/11 FABLE studies (college hoops profit + spreads like the pros).
Read-only on the repo; caches in ~/.cache (never the repo). Builds on results/studies/daily_1110/lib.py (finals at
the close, the paid football odds history's FAIR looks, box rows) - loaded as `B`.
Seasons are start years (2025 = 2025-26). Every study: TRAIN = the old seasons, HELD OUT = each newer season apart."""
import importlib.util, json, math, os, pickle, statistics, sys
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
os.environ.setdefault("STUDY_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "d503_1110"))
_spec = importlib.util.spec_from_file_location("base1110", os.path.join(ROOT, "results", "studies", "daily_1110", "lib.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)
B.OUT = OUT
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "d503_1111")
os.makedirs(CACHE, exist_ok=True)
sd, sm = B.sd, B.sm
dec, num, profit, stats, summ, fmt, Cells = B.dec, B.num, B.profit, B.stats, B.summ, B.fmt, B.Cells


def cached(name, fn):
    p = os.path.join(CACHE, name + ".pkl")
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    v = fn()
    pickle.dump(v, open(p, "wb"))
    return v


def nv(h, a):
    ph, pa = 1 / dec(h), 1 / dec(a)
    return ph / (ph + pa)


def cover(g, side):
    """The side's cover margin at the closing spread (None without a spread)."""
    if g["sp"] is None:
        return None
    m = g["hs"] - g["as"] + g["sp"]
    return m if side == "home" else -m


def teambox(lg):
    """{gid: {team id: {stat: raw string}}} - ESPN's TEAM box (data/sports/teamstats), 2021-26."""
    import sports_roster as sr

    def mk():
        return {r["gid"]: r["teams"] for r in sr.team_rows(lg) if r.get("teams")}
    return cached(f"teambox_{lg}", mk)


def pair(s, sep="-"):
    try:
        a, b = str(s).split(sep)[:2]
        return float(a), float(b)
    except (ValueError, AttributeError):
        return None


class Out:
    """Collects printed lines and writes <tag>_out.txt next to the scripts."""
    def __init__(self, tag):
        self.tag, self.lines = tag, []

    def p(self, *a):
        s = " ".join(str(x) for x in a)
        print(s)
        self.lines.append(s)

    def cells(self, cells, train, held, minn=0, zshow=0.0, w=58):
        """Every cell goes to the file; the terminal shows only |z| >= zshow (or a name starting with BASE / KEY)."""
        res = {k: summ(v, train, held) for k, v in sorted(cells.c.items())}
        for k, v in res.items():
            if v and v["all"]["n"] >= minn:
                line = fmt(k, v) if len(k) <= w else fmt(k[:w], v).replace(k[:w], k, 1)
                self.lines.append(line)
                if abs(v["all"]["z"]) >= zshow or k.startswith(("BASE", "KEY")):
                    print(line)
        return res

    def save(self):
        open(os.path.join(OUT, self.tag + "_out.txt"), "w").write("\n".join(self.lines) + "\n")


def ridge(X, y, lam):
    import numpy as np
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    A = X.T @ X + lam * np.eye(X.shape[1])
    return np.linalg.solve(A, X.T @ y)
