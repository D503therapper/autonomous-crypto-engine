"""11/11 - THE OVER/UNDER STUDIES (the owner's brother's engine): shared helpers. Read-only on the repo.

Seasons are named by the year they start (hoops / hockey: Aug-Jul; football / baseball: the calendar year).
TRAIN = 2018-2021, BLIND = 2022 on (the brother's engine's own split - and ours has no totals before 2018).
Every bet is graded at the CLOSING total and its real over / under price (-110 when the price is missing); a push
is a bet that returns 0. z = the mean profit a bet over its standard error."""
import csv
import glob
import math
import os
import statistics
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
TRAIN_TO = 2021
FT = 3.281


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
    if lg in ("nfl", "ncaaf"):
        return y if m >= 3 else y - 1
    return y


def load(lg, finals=True):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, f"data/sports/games/{lg}/*.csv"))):
        for r in csv.DictReader(open(f)):
            if finals and r["status"] != "final":
                continue
            r["season"] = season(r["start"], lg)
            r["tot"] = num(r.get("total"))
            r["hs"], r["as"] = num(r.get("home_score")), num(r.get("away_score"))
            r["el"] = num(r.get("elev"))
            r["neu"] = str(r.get("neutral") or "0") in ("1", "True", "true")
            out.append(r)
    out.sort(key=lambda r: r["start"])
    return out


def pay(odds):
    o = num(odds) or -110
    return o / 100 if o > 0 else 100 / -o


def bet(r, side):
    """Profit on 1 unit staked on the over / under at the close (None = no total / no score)."""
    if r["tot"] is None or r["hs"] is None or r["as"] is None:
        return None
    pts = r["hs"] + r["as"]
    if pts == r["tot"]:
        return 0.0
    won = (pts > r["tot"]) == (side == "over")
    return pay(r.get(f"{side}_odds")) if won else -1.0


def stats(ps):
    n = len(ps)
    if not n:
        return dict(n=0, roi=0.0, z=0.0, w=0, l=0)
    m = sum(ps) / n
    sd = statistics.pstdev(ps) if n > 1 else 0
    z = m / (sd / math.sqrt(n)) if sd else 0.0
    return dict(n=n, roi=m, z=z, w=sum(1 for p in ps if p > 0), l=sum(1 for p in ps if p < 0))


def line(label, rows, side, key=lambda r: r["season"], train_to=TRAIN_TO):
    """One printed cell: all / train / blind + the seasons. rows = games; side = 'over' / 'under'."""
    bs = [(key(r), bet(r, side)) for r in rows]
    bs = [(s, p) for s, p in bs if p is not None]
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
    print(f"{label:<58} ALL {a['w']}-{a['l']} {100 * a['roi']:+6.1f}% n{a['n']:<5} z{a['z']:+.1f} | "
          f"TR {100 * tr['roi']:+6.1f}% n{tr['n']:<4} {up_tr}/{n_tr} | BL {100 * bl['roi']:+6.1f}% n{bl['n']:<4} "
          f"z{bl['z']:+.1f} {up_bl}/{n_bl} | {ss}")
    return dict(all=a, train=tr, blind=bl, up_tr=up_tr, n_tr=n_tr, up_bl=up_bl, n_bl=n_bl)


def home_elev(games):
    """team -> its home floor's elevation (the median elev of its non-neutral home games)."""
    acc = defaultdict(list)
    for r in games:
        if not r["neu"] and r["el"] is not None:
            acc[r["home"]].append(r["el"])
    return {t: statistics.median(v) for t, v in acc.items()}
