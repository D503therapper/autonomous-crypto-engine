"""Shared helpers for the 11/11 early-play line studies (read-only on the repo; caches in ~/.cache, never the repo).
Reuses the 11/11 daily-study helpers (results/studies/daily_1111/lib.py: the paid odds history oriented by team,
FAIR looks only - tools/early_football_study.ready_at / fair, no look-ahead)."""
import importlib.util
import json
import math
import os
import pickle
import statistics
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "d503_early1111")
os.makedirs(CACHE, exist_ok=True)
os.environ.setdefault("STUDY_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "d503_1111"))
_spec = importlib.util.spec_from_file_location("dlib", os.path.join(ROOT, "results/studies/daily_1111/lib.py"))
lib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lib)                      # (it chdirs to ROOT and puts ROOT on sys.path)
import sports_data as sd                           # noqa: E402
import sports_early as se                          # noqa: E402
import sports_model as sm                          # noqa: E402

PT = ZoneInfo("America/Los_Angeles")
ET = ZoneInfo("America/New_York")
TRAIN = (2020, 2022)
HELD = (2023, 2024, 2025, 2026)


def t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=timezone.utc) if "+" not in s and \
        not s.endswith("Z") else datetime.fromisoformat(s.replace("Z", "+00:00"))


def imp(o):
    o = float(o)
    return 100 / (o + 100) if o > 0 else -o / (-o + 100)


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def am(d):
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def nv(o, opp):
    """no-vig win % of the side priced `o` against `opp` (american)."""
    a, b = imp(o), imp(opp)
    return a / (a + b)


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def tstat(xs):
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    s = statistics.pstdev(xs)
    return mean(xs) / (s / math.sqrt(len(xs))) if s else 0.0


def roi(ps):
    """ps: flat 1u profits -> 'n W-L roi z'."""
    if not ps:
        return "n 0"
    n = len(ps)
    w = sum(1 for p in ps if p > 0)
    return f"n {n:4d} {w}-{n - w} {mean(ps) * 100:+6.1f}% z{tstat(ps):+5.2f}"


def zwin(rows):
    """rows: [(won, no-vig p)] -> z of the wins against what the price expects."""
    e = sum(p for _, p in rows)
    v = sum(p * (1 - p) for _, p in rows)
    return (sum(1 for w, _ in rows if w) - e) / math.sqrt(v) if v else 0.0


class Tee:
    def __init__(self, name):
        self.f = open(os.path.join(OUT, name), "w")

    def __call__(self, *a):
        s = " ".join(str(x) for x in a)
        print(s)
        self.f.write(s + "\n")
        self.f.flush()


def line_tape():
    """{game id: [(time, home ml, away ml, total or None)]} oldest first - the engine's own hourly line history
    (data/sports/line_history, since 10/1)."""
    cache = os.path.join(CACHE, "tape.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    out = {}
    d = sd.LINE_HIST_DIR
    for fn in sorted(f for f in os.listdir(d) if f.endswith(".jsonl")):
        with open(os.path.join(d, fn)) as f:
            for x in f:
                try:
                    r = json.loads(x)
                except ValueError:
                    continue
                h, a = se._int(r.get("h")), se._int(r.get("a"))
                if h is None or a is None or h == 0 or a == 0:
                    continue
                out.setdefault(r["g"], []).append((r["t"], h, a, r.get("tot")))
    for v in out.values():
        v.sort()
    pickle.dump(out, open(cache, "wb"))
    return out


_GAMES = {}


def games(lg):
    if lg not in _GAMES:
        _GAMES[lg] = sd.load_games(lg)
    return _GAMES[lg]


def cents(a, b):
    """cents from american price a to b, across the line counted right (+105 -> -110 = 15)."""
    def u(o):
        return o - 100 if o > 0 else o + 100
    return u(b) - u(a)
