"""Shared helpers for the 11/2 NBA odds-history studies (read-only on the repo; a cache lands here as _cache_looks.pkl).

THE DATA (the owner's paid odds history, 11/1): data/sports/odds_history/basketball_nba.jsonl.gz (moneylines, every US
book) and basketball_nba_spreads.jsonl.gz - ONE 15:00Z look a day, 2020-12 .. 2023-06 (spreads to 2023-04). Each look
holds that day's games (the GAME-DAY MORNING price, ~4-13h before tip - the 8 AM board's hour) and the next day's games
the books already opened (~28-37h out - the NEXT-DAY LINE, an opening-style number). ESPN's close is in the game files.

Every look here: snap BEFORE tip (a row at / after tip-off is dropped), the exchange (betfair) and any pair with an
impossible hold dropped, the consensus = the MEDIAN book (median decimal price per side; no-vig from those). An OPEN look is
FAIR only when both teams' previous games (any game type) tipped 3h+ before the snapshot - a team that plays between the
look and this game has a result the look couldn't know (the live early rule's 'ready')."""
import gzip
import json
import math
import os
import pickle
import statistics
import sys
from datetime import datetime, timedelta, timezone

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_data as sd       # noqa: E402

ML_PATH = os.path.join(ROOT, "data/sports/odds_history/basketball_nba.jsonl.gz")
SP_PATH = os.path.join(ROOT, "data/sports/odds_history/basketball_nba_spreads.jsonl.gz")
EXCHANGES = {"betfair"}
OPEN_MIN_H = 20.0       # a look 20h+ before tip = the next-day line; under = the game-day morning look
FAIR_GAP_H = 3.0        # both teams' previous games tipped this long before the look


def t(s):
    return datetime.strptime(str(s)[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def amer(d):
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def nv(h, a):
    ph, pa = 1 / dec(h), 1 / dec(a)
    return ph / (ph + pa)


def season(start):
    y, m = int(str(start)[:4]), int(str(start)[5:7])
    if y == 2020 and m <= 10:
        return 2019
    return y if m >= 9 else y - 1


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _key(full):
    return full.split()[-1] if not full.endswith("Trail Blazers") else "Trail Blazers"


def load_games():
    return sd.load_games("nba")


def _index(games):
    by = {}
    for gid, g in games.items():
        if not g.get("start") or g.get("home_name") is None:
            continue
        by.setdefault((g["home_name"], g["away_name"]), []).append((t(g["start"]), gid))
    return by


def _match(by, h, a, tip):
    best = None
    for st, gid in by.get((_key(h), _key(a)), []):
        dh = abs((st - tip).total_seconds()) / 3600
        if dh <= 8 and (best is None or dh < best[0]):
            best = (dh, gid)
    return best[1] if best else None


def _ml_consensus(b):
    hs, as_, per = [], [], {}
    for bk, pr in b.items():
        if bk in EXCHANGES or not pr or pr[0] is None or pr[1] is None:
            continue
        try:
            dh, da = dec(pr[0]), dec(pr[1])
        except (ValueError, ZeroDivisionError):
            continue
        hold = 1 / dh + 1 / da
        if not 1.0 <= hold <= 1.10:
            continue
        hs.append(dh); as_.append(da); per[bk] = (int(pr[0]), int(pr[1]))
    if len(hs) < 2:
        return None
    dh, da = statistics.median(hs), statistics.median(as_)
    ph, pa = 1 / dh, 1 / da
    return {"dh": dh, "da": da, "mh": amer(dh), "ma": amer(da), "p": ph / (ph + pa), "n": len(hs), "books": per}


def _sp_consensus(b):
    pts, per = [], {}
    for bk, pr in b.items():
        if bk in EXCHANGES or not pr or pr[0] is None:
            continue
        pts.append(float(pr[0])); per[bk] = float(pr[0])
    if len(pts) < 2:
        return None
    return {"pt": statistics.median(pts), "n": len(pts), "books": per}


def looks(games=None, refresh=False):
    """{gid: {"ml": [look...], "sp": [look...]}} sorted by snap; each look {snap, h_before, ...consensus}."""
    cache = os.path.join(OUT, "_cache_looks.pkl")
    if not refresh and os.path.exists(cache):
        with open(cache, "rb") as f:
            return pickle.load(f)
    games = games or load_games()
    by = _index(games)
    out = {}
    miss = 0
    for path, kind in ((ML_PATH, "ml"), (SP_PATH, "sp")):
        with gzip.open(path, "rt") as f:
            for line in f:
                r = json.loads(line)
                if "h" not in r:
                    continue
                tip, snap = t(r["t"]), t(r["snap"])
                if snap >= tip:
                    continue                                 # at / after tip-off: never a pre-game price
                gid = _match(by, r["h"], r["a"], tip)
                if gid is None:
                    miss += 1
                    continue
                c = _ml_consensus(r["b"]) if kind == "ml" else _sp_consensus(r["b"])
                if c is None:
                    continue
                c["snap"] = r["snap"][:16]
                c["h_before"] = (tip - snap).total_seconds() / 3600
                out.setdefault(gid, {"ml": [], "sp": []})[kind].append(c)
    for v in out.values():
        for k in ("ml", "sp"):
            v[k].sort(key=lambda c: c["snap"])
            ded, seen = [], set()
            for c in v[k]:
                if c["snap"] not in seen:
                    seen.add(c["snap"]); ded.append(c)
            v[k] = ded
    print(f"looks: {len(out)} games matched, {miss} rows unmatched", file=sys.stderr)
    with open(cache, "wb") as f:
        pickle.dump(out, f)
    return out


def prev_tips(games):
    """{gid: (home team's previous tip, away team's previous tip)} over every game (any type)."""
    sched = {}
    for gid, g in games.items():
        if g.get("start"):
            for side in ("home", "away"):
                sched.setdefault(g[side], []).append((g["start"], gid))
    out = {}
    for tm, rows in sched.items():
        rows.sort()
        for i, (st, gid) in enumerate(rows):
            g = games[gid]
            side = "home" if g["home"] == tm else "away"
            out.setdefault(gid, {})[side] = t(rows[i - 1][0]) if i else None
    return out


def fair(prev, gid, snap):
    p = prev.get(gid, {})
    s = t(snap)
    return all(p.get(side) is None or p[side] <= s - timedelta(hours=FAIR_GAP_H) for side in ("home", "away"))


def pick_looks(lk, prev, gid):
    """-> (open, morning) ML looks: open = the earliest FAIR look 20h+ before tip (the next-day line); morning = the
    last look under 20h before tip (the game-day 15:00Z number). Either may be None."""
    ml = lk.get(gid, {}).get("ml", [])
    op = next((c for c in ml if c["h_before"] >= OPEN_MIN_H and fair(prev, gid, c["snap"])), None)
    mo = None
    for c in ml:
        if c["h_before"] < OPEN_MIN_H:
            mo = c
    return op, mo


def sp_looks(lk, prev, gid):
    sp = lk.get(gid, {}).get("sp", [])
    op = next((c for c in sp if c["h_before"] >= OPEN_MIN_H and fair(prev, gid, c["snap"])), None)
    mo = None
    for c in sp:
        if c["h_before"] < OPEN_MIN_H:
            mo = c
    return op, mo


def profit(won, d):
    return (d - 1) if won else -1.0


class Cells:
    """Collect (season, profit) per named cell; print W-L, ROI, units and the seasons up, split TRAIN / HELD seasons."""

    def __init__(self, title, groups):
        self.title, self.groups, self.cells = title, groups, {}

    def add(self, name, s, pnl):
        self.cells.setdefault(name, []).append((s, pnl))

    @staticmethod
    def agg(rows):
        n = len(rows)
        if not n:
            return "-"
        w = sum(1 for _, p in rows if p > 0)
        u = sum(p for _, p in rows)
        by = {}
        for s, p in rows:
            by[s] = by.get(s, 0.0) + p
        up = sum(1 for v in by.values() if v > 0)
        sdv = statistics.pstdev([p for _, p in rows]) if n > 1 else 1.0
        z = (u / n) / (sdv / math.sqrt(n)) if sdv else 0.0
        return f"{w}-{n - w} {u / n * 100:+6.1f}% {u:+7.1f}u z{z:+.1f} ({up}/{len(by)} up)"

    def line(self, name):
        rows = self.cells.get(name, [])
        parts = []
        for gname, seasons in self.groups:
            parts.append(f"{gname} {self.agg([r for r in rows if r[0] in seasons])}")
        by = {}
        for s, p in rows:
            o = by.setdefault(s, [0, 0, 0.0])
            o[0 if p > 0 else 1] += 1; o[2] += p
        per = "  ".join(f"{s}:{v[0]}-{v[1]} {v[2] / (v[0] + v[1]) * 100:+.0f}%" for s, v in sorted(by.items()))
        return f"  {name:52s} " + " | ".join(parts) + f"   [{per}]"

    def dump(self, names=None):
        print(f"\n{self.title}")
        for k in (names or self.cells):
            if k in self.cells:
                print(self.line(k))

    def as_dict(self):
        out = {}
        for k, rows in self.cells.items():
            out[k] = {gname: self.agg([r for r in rows if r[0] in seasons]) for gname, seasons in self.groups}
        return out
