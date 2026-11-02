"""11/3 college hoops (A) - shared helpers: every ncaab game on disk (ESPN closes, ESPN opens where they exist),
each team's game number in its season, last season's final Elo-ish rating (a simple margin Elo run on our own files,
carried over with regression), and the profit helpers. Seasons: a season is named by the year it STARTS
(2018 = 2018-19). Train = 2018-2022 starts, held out = 2023 / 2024 / 2025 apart (the last three, the owner's bar)."""
import csv
import glob
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
TRAIN = (2018, 2019, 2020, 2021, 2022)
HELD = (2023, 2024, 2025)


def season_of(dt):
    return dt.year if dt.month >= 8 else dt.year - 1


def dec(odds):
    o = float(odds)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def implied(odds):
    return 1 / dec(odds)


def novig(a, b):
    pa, pb = implied(a), implied(b)
    return pa / (pa + pb)


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load():
    rows = []
    for fn in sorted(glob.glob(os.path.join(ROOT, "data/sports/games/ncaab/*.csv"))):
        for r in csv.DictReader(open(fn)):
            if r["status"] != "final":
                continue
            try:
                r["dt"] = datetime.strptime(r["start"][:16], "%Y-%m-%dT%H:%M")
                r["hs"], r["as_"] = int(r["home_score"]), int(r["away_score"])
            except (ValueError, KeyError):
                continue
            if (r.get("stype") or "2") not in ("2", "3", "?", ""):
                continue
            r["season"] = season_of(r["dt"] - timedelta(hours=8))
            rows.append(r)
    rows.sort(key=lambda r: r["dt"])
    seen = set()
    out = []
    for r in rows:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        out.append(r)
    return out


def annotate(rows):
    """Each row gets: gn_home / gn_away (the team's game number this season, 1 = opener), days into season,
    Elo before the game (carried from last season, regressed 1/3 to the mean), d1 flags (a team with 20+ games
    on file in that season = D1), last-season win%."""
    gcount = defaultdict(int)
    elo = {}
    last_season_of = {}
    season_start = {}
    wins = defaultdict(lambda: [0, 0])
    nseason = defaultdict(int)
    for r in rows:
        nseason[(r["season"], r["home"])] += 1
        nseason[(r["season"], r["away"])] += 1
    for r in rows:
        s = r["season"]
        season_start.setdefault(s, r["dt"])
        for side in ("home", "away"):
            t = r[side]
            if last_season_of.get(t) is not None and last_season_of[t] != s:
                elo[t] = 1500 + (elo.get(t, 1500) - 1500) * (2 / 3)
            last_season_of[t] = s
            gcount[(s, t)] += 1
            r["gn_" + side] = gcount[(s, t)]
            r["d1_" + side] = nseason[(s, t)] >= 20
            prev = wins.get((s - 1, t))
            r["lastwp_" + side] = (prev[0] / prev[1]) if prev and prev[1] >= 10 else None
            r["prevd1_" + side] = nseason.get((s - 1, t), 0) >= 20
        neutral = str(r.get("neutral")) == "1"
        eh, ea = elo.get(r["home"], 1500), elo.get(r["away"], 1500)
        r["elo_home"], r["elo_away"] = eh, ea
        hfa = 0 if neutral else 70
        exp = 1 / (1 + 10 ** (-(eh + hfa - ea) / 400))
        r["elo_p_home"] = exp
        mov = r["hs"] - r["as_"]
        res = 1.0 if mov > 0 else 0.0
        k = 20 * math.log(abs(mov) + 1) * (2.2 / ((abs(eh + hfa - ea) * 0.001) + 2.2))
        elo[r["home"]] = eh + k * (res - exp)
        elo[r["away"]] = ea - k * (res - exp)
        r["day_in_season"] = (r["dt"] - season_start[s]).days
        w = wins[(s, r["home"])]; w[0] += mov > 0; w[1] += 1
        w = wins[(s, r["away"])]; w[0] += mov < 0; w[1] += 1
    return rows


def ml_profit(odds, won):
    return (dec(odds) - 1) if won else -1.0


def ats_profit(margin_vs_line, odds=-110):
    """margin_vs_line = side's margin + side's spread; push = 0."""
    if margin_vs_line == 0:
        return 0.0
    return (dec(odds) - 1) if margin_vs_line > 0 else -1.0


class Cell:
    def __init__(self):
        self.n = 0; self.pl = 0.0; self.sq = 0.0; self.w = 0
        self.by = defaultdict(lambda: [0, 0.0])

    def add(self, season, pl, won=None):
        self.n += 1; self.pl += pl; self.sq += pl * pl
        if won:
            self.w += 1
        b = self.by[season]; b[0] += 1; b[1] += pl

    def roi(self):
        return self.pl / self.n if self.n else 0.0

    def z(self):
        if self.n < 2:
            return 0.0
        m = self.pl / self.n
        v = self.sq / self.n - m * m
        return m / math.sqrt(v / self.n) if v > 0 else 0.0

    def line(self, label):
        tr = [self.by[s] for s in TRAIN if s in self.by]
        tn, tp = sum(b[0] for b in tr), sum(b[1] for b in tr)
        up = sum(1 for b in tr if b[1] > 0)
        held = " ".join(f"{s}:{self.by[s][1] / self.by[s][0]:+.1%}/{self.by[s][0]}" for s in HELD if self.by.get(s) and self.by[s][0])
        hn = sum(self.by[s][0] for s in HELD if s in self.by)
        hp = sum(self.by[s][1] for s in HELD if s in self.by)
        cur = self.by.get(2026)
        cur_s = f" | 2026 {cur[1] / cur[0]:+.1%}/{cur[0]}" if cur and cur[0] else ""
        return (f"{label:58} n={self.n:5} roi={self.roi():+6.1%} z={self.z():+5.2f} | train {tp / tn if tn else 0:+6.1%}/{tn} "
                f"({up}/{len(tr)} up) | held {hp / hn if hn else 0:+6.1%}/{hn} [{held}]{cur_s}")
