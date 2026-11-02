"""11/3 DEEP: WHERE BASKETBALL BOOKS ARE WEAK - shared helpers (read-only on the repo; the cache lands in
~/.cache/d503_studies, never the repo).

College hoops: one row per team side from the 11/3 (B) table (results/studies/cbb_1103_b/lib.build - no look-ahead,
inferred conferences + tiers, rest, Elo, closes + ESPN opens), joined with the game-file fields this study needs that
the (B) table drops: the 1st-half spread / moneyline and their odds, the half scores (ls_home / ls_away), the total's
over / under odds, the tip hour (ET), the venue's elevation, whether Action Network splits exist for the game.
NBA: one row per game from the game files (closes, ESPN opens 2023-25, 1st-half lines, quarter scores, totals).

Seasons are named by the year they start. College hoops: TRAIN 2018-2022, HELD OUT 2023 / 2024 / 2025 apart. ESPN's
OPEN exists only for 2023-25 (one source's opening number), so open studies walk forward inside those three seasons."""
import csv
import glob
import json
import math
import os
import pickle
import statistics
import sys
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
CACHE = os.environ.get("STUDY_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "d503_studies")
os.makedirs(CACHE, exist_ok=True)
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("cbb_b_lib", os.path.join(ROOT, "results", "studies", "cbb_1103_b", "lib.py"))
B = importlib.util.module_from_spec(_spec)  # the 11/3 (B) side table
_spec.loader.exec_module(B)

TRAIN = (2018, 2019, 2020, 2021, 2022)
HELD = (2023, 2024, 2025)
OPEN_SEASONS = (2023, 2024, 2025)


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def nv(a, b):
    pa, pb = 1 / dec(a), 1 / dec(b)
    return pa / (pa + pb)


def season(start, lg="ncaab"):
    y, m = int(start[:4]), int(start[5:7])
    if lg == "nba" and y == 2020 and m <= 10:
        return 2019
    return y if m >= 8 else y - 1


def et_hour(start):
    """Tip hour Eastern (EST, UTC-5; the season is Nov-Mar), as a float; 0-4 AM reads as 24-28 (a late West tip)."""
    h = int(start[11:13]) + int(start[14:16]) / 60 - 5
    if h < 5:
        h += 24
    return h


def halves(ls):
    if not ls:
        return None
    try:
        v = [int(p) for p in str(ls).split(",")]
    except ValueError:
        return None
    return v


def raw_games(lg):
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, f"data/sports/games/{lg}/*.csv"))):
        for r in csv.DictReader(open(f)):
            if r["status"] != "final":
                continue
            out[r["id"]] = r
    return out


def public_ids():
    try:
        d = json.load(open(os.path.join(ROOT, "data/sports/public.json")))["games"]
    except (OSError, ValueError, KeyError):
        return {}
    return d


def nc_sides():
    """The (B) side rows + the extra game fields. Cached."""
    pk = os.path.join(CACHE, "deepbb_nc_sides.pkl")
    if os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(__file__):
        return pickle.load(open(pk, "rb"))
    rows = B.build()
    G = raw_games("ncaab")
    pub = public_ids()
    for x in rows:
        r = G.get(x["id"])
        if not r:
            continue
        home = x["side"] == "home"
        x["et"] = et_hour(r["start"])
        x["elev"] = num(r.get("elev"))
        x["month"] = int(r["start"][5:7])
        x["has_pub"] = x["id"] in pub
        h1s = num(r.get("h1_spread_home"))
        x["has_h1"] = h1s is not None
        if h1s is not None:
            x["h1sp"] = h1s if home else -h1s
            o = num(r.get("h1_spread_home_odds") if home else r.get("h1_spread_away_odds"))
            x["h1odds"] = o or -110
        a, b = num(r.get("h1_ml_home")), num(r.get("h1_ml_away"))
        if a and b:
            x["h1ml"], x["h1oml"] = (a, b) if home else (b, a)
        lh, la = halves(r.get("ls_home")), halves(r.get("ls_away"))
        if lh and la and len(lh) >= 2 and len(la) >= 2:
            me, op = (lh, la) if home else (la, lh)
            x["h1m"] = me[0] - op[0]
            x["h1pts"] = me[0] + op[0]
            x["ot"] = len(lh) > 2
        ov, un = num(r.get("over_odds")), num(r.get("under_odds"))
        x["over_odds"], x["under_odds"] = ov or -110, un or -110
        if pub.get(x["id"]):
            p = pub[x["id"]]
            k = "home" if home else "away"
            x["pub_t"] = p.get(f"ml_{k}_t")
            x["pub_m"] = p.get(f"ml_{k}_m")
            x["pub_sp_t"] = p.get(f"sp_{k}_t")
            x["pub_sp_m"] = p.get(f"sp_{k}_m")
            x["pub_over_t"] = p.get("tot_over_t")
            x["pub_over_m"] = p.get("tot_over_m")
    pickle.dump(rows, open(pk, "wb"))
    return rows


def nba_games():
    """One dict per NBA regular-season final with closes / opens / 1H lines / quarters / totals. Cached."""
    pk = os.path.join(CACHE, "deepbb_nba_games.pkl")
    if os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(__file__):
        return pickle.load(open(pk, "rb"))
    G = raw_games("nba")
    pub = public_ids()
    out = []
    for gid, r in G.items():
        if (r.get("stype") or "2") != "2":
            continue
        hs, as_ = num(r["home_score"]), num(r["away_score"])
        if hs is None or as_ is None:
            continue
        g = {"id": gid, "start": r["start"], "season": season(r["start"], "nba"), "home": r["home"], "away": r["away"],
             "hname": r["home_name"], "aname": r["away_name"], "hs": hs, "as": as_, "margin": hs - as_,
             "pts": hs + as_, "mlh": num(r["ml_home"]), "mla": num(r["ml_away"]), "mloh": num(r["ml_home_open"]),
             "mloa": num(r["ml_away_open"]), "sp": num(r["spread_home"]),
             "sph_o": num(r["spread_home_odds"]) or -110, "spa_o": num(r["spread_away_odds"]) or -110,
             "total": num(r["total"]), "over_o": num(r["over_odds"]) or -110, "under_o": num(r["under_odds"]) or -110,
             "h1sp": num(r.get("h1_spread_home")), "h1sph_o": num(r.get("h1_spread_home_odds")) or -110,
             "h1spa_o": num(r.get("h1_spread_away_odds")) or -110, "h1mlh": num(r.get("h1_ml_home")),
             "h1mla": num(r.get("h1_ml_away")), "elev": num(r.get("elev")), "et": et_hour(r["start"]),
             "has_pub": gid in pub}
        lh, la = halves(r.get("ls_home")), halves(r.get("ls_away"))
        if lh and la and len(lh) >= 4 and len(la) >= 4:
            g["h1m"] = lh[0] + lh[1] - la[0] - la[1]
            g["h1pts"] = lh[0] + lh[1] + la[0] + la[1]
            g["ot"] = len(lh) > 4
        out.append(g)
    out.sort(key=lambda g: (g["start"], g["id"]))
    pickle.dump(out, open(pk, "wb"))
    return out


def ml_pl(odds, won):
    return (dec(odds) - 1) if won else -1.0


def ats_pl(cm, odds=-110):
    """cm = the side's margin + its spread; push = 0."""
    if cm == 0:
        return 0.0
    return (dec(odds) - 1) if cm > 0 else -1.0


def st(ps):
    ps = [p for p in ps if p is not None]
    if not ps:
        return None
    n = len(ps)
    m = sum(ps) / n
    sd = statistics.pstdev(ps) if n > 1 else 1.0
    return {"n": n, "roi": m, "z": (m / (sd / math.sqrt(n))) if sd else 0.0}


class Out:
    """Collects lines to print + save (<name>_out.txt), counts cells, and grades a list of (season, profit) bets:
    ALL / TRAIN (seasons up) / HELD OUT (seasons up) / each season."""
    def __init__(self, name, train=TRAIN, held=HELD):
        self.name, self.lines, self.cells, self.train, self.held = name, [], 0, train, held

    def h(self, t):
        self.lines.append("")
        self.lines.append("== " + t)
        print("\n== " + t, flush=True)

    def note(self, t):
        self.lines.append(t)
        print(t, flush=True)

    def bets(self, label, bets, count=True):
        """bets: list of (season, profit)."""
        bets = [(s, p) for s, p in bets if p is not None]
        if count:
            self.cells += 1
        if not bets:
            self.note(f"{label:60s} n 0")
            return None
        by = defaultdict(list)
        for s, p in bets:
            by[s].append(p)
        a = st([p for _, p in bets])
        tr = st([p for s, p in bets if s in self.train])
        ho = st([p for s, p in bets if s in self.held])
        tu = sum(1 for s in self.train if s in by and sum(by[s]) > 0)
        tn = sum(1 for s in self.train if s in by)
        hu = sum(1 for s in self.held if s in by and sum(by[s]) > 0)
        hn = sum(1 for s in self.held if s in by)

        def f(x):
            return f"{x['roi']*100:+6.1f}% n{x['n']:<5d}" if x else "   -          "
        yrs = " ".join(f"{str(s)[2:]}:{sum(v)/len(v)*100:+.0f}/{len(v)}" for s, v in sorted(by.items()))
        self.note(f"{label:60s} ALL {f(a)} z{a['z']:+.1f} | TR {f(tr)} {tu}/{tn} | HO {f(ho)} {hu}/{hn} | {yrs}")
        return {"all": a, "train": tr, "held": ho, "tr_up": tu, "tr_n": tn, "ho_up": hu, "ho_n": hn,
                "by": {s: st(v) for s, v in by.items()}}

    def save(self):
        self.lines.append(f"\ncells looked at: {self.cells}")
        open(os.path.join(OUT, self.name + "_out.txt"), "w").write("\n".join(self.lines) + "\n")


def h1_ok(sp, h1sp, k=0.55):
    """A 1st-half line we trust: same sign as the full spread (61 college rows carry a flipped sign - a data error that
    reads as a 7-point 'edge') and within 2.5 points of k x the full spread (beyond that it's a bad row, not a price)."""
    if sp is None or h1sp is None:
        return False
    if abs(sp) >= 2 and sp * h1sp < 0:
        return False
    return abs(h1sp - k * sp) <= 2.5
