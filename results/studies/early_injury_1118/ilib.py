"""Shared helpers for the 11/18 early-play x injury-news study. Reuses the 11/11 early-line study's base table
(results/studies/early_1111/elib.py + base.py: every side of every NFL / college game in the paid odds history, FAIR
looks only - tools/early_football_study.ready_at / fair, no look-ahead) and the nflverse files the 11/11 book study
fetched (~/.cache/d503_book1111/dl - injuries_<y>.csv, snap_counts_<y>.csv, games.csv; nothing written to the repo)."""
import os
import random
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "early_1111"))
import elib as E          # noqa: E402
import base               # noqa: E402

DL = os.path.join(os.path.expanduser("~"), ".cache", "d503_book1111", "dl")
TRAIN_TO = 2022           # train 2020-22, held out 2023-26 (the 11/11 split)


class Tee:
    def __init__(self, name):
        self.f = open(os.path.join(HERE, name), "w")

    def __call__(self, *a):
        s = " ".join(str(x) for x in a)
        print(s)
        self.f.write(s + "\n")
        self.f.flush()


def pl(r, o):
    return (E.dec(o) - 1) if r["won"] else -1.0


def look_time(r, k):
    return E.t(r["start"]) - timedelta(days=k[0])


def report_times(r):
    """NFL: (first practice report, final statuses) for this game, as moments. The league's schedule: a Sunday game's
    reports come Wed / Thu / Fri about 4 PM ET (game day - 4 / - 3 / - 2), Monday's Thu / Fri / Sat, Saturday's
    Tue / Wed / Thu, Thursday's Mon / Tue / Wed (- 3 / - 2 / - 1). The final statuses ride the last one."""
    et = E.t(r["start"]).astimezone(E.ET)
    d = et.date()
    first_back, final_back = (3, 1) if et.weekday() == 3 else (4, 2)
    mk = lambda back: datetime(d.year, d.month, d.day, 16, 30, tzinfo=E.ET) - timedelta(days=back)   # noqa: E731
    return mk(first_back), mk(final_back)


def phase(r, k):
    """'pre' = the look is before the week's first practice report, 'mid' = after it and before the final statuses,
    'final' = after the final statuses."""
    a, b = report_times(r)
    t = look_time(r, k)
    return "pre" if t < a else "mid" if t < b else "final"


def live_bar(r, k, se=E.se):
    """The spots this dog has at look k that clear the live bar (the read not fighting, the weighed total 5+) - the
    11/11 s5b cut (no fades / lead weights / injuries: not in the history). [] = no play."""
    if r["own"] is None or not 100 <= k[2] <= 350:
        return []
    hit = base.spots(r, k, base.first_fair(r))
    if not hit or r["own"] < k[3] - se.SPOT_FIGHT:
        return []
    tot = se.spot_gap(r["lg"], r["own"], k[3]) + sum(se.SPOT_WEIGHT[h] for h in hit)
    return hit if tot >= se.SPOT_MIN_TOTAL else []


def halves(v, f):
    """v: rows with ['r']; f: row -> profit. -> 'all | train | held | seasons up'."""
    a = [f(x) for x in v]
    tr = [f(x) for x in v if x["r"]["season"] <= TRAIN_TO]
    he = [f(x) for x in v if x["r"]["season"] > TRAIN_TO]
    by = {}
    for x in v:
        by.setdefault(x["r"]["season"], []).append(f(x))
    up = sum(1 for p in by.values() if sum(p) > 0)
    return f"{E.roi(a)} | train {E.roi(tr)} | held {E.roi(he)} | seasons up {up}/{len(by)}"


def placebo(pool, n, target, f, worse=True, runs=2000, seed=18):
    """How many of `runs` random draws of n rows from pool have a mean of f as low (worse) / as high as target."""
    rnd = random.Random(seed)
    vals = [f(x) for x in pool]
    if n > len(vals) or not n:
        return None
    hit = 0
    for _ in range(runs):
        m = sum(rnd.sample(vals, n)) / n
        hit += (m <= target) if worse else (m >= target)
    return hit
