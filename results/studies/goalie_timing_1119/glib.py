"""11/19 - HOCKEY GOALIES x WHEN THE PRICE IS BEST: the shared rig (read-only on the repo; caches in ~/.cache/d503_goalie1119).

THE GOALIE TABLE (goalies()): every NHL team-game in our box scores 2016-26 (data/sports/players/nhl.csv - one goalie
row a team-game, the man who faced the most shots = the starter on all but the rare early pull), each with what the
engine could know at 8 AM and what happened:
  actual  the goalie who started          last   the team's previous starter (this season)
  n1      the team's #1 (sports_goalies.number_one: most starts in its last 10 this season, 6+ on file, a clear leader)
  proj    the engine's own 8 AM projection (sports_players.projected_starter - the #1 rested, the other man on a b2b)
  b2b     the 2nd night of a back-to-back (within 36 hours)
  sv      {name: shrunk save % over his last 5 starts in the form window - sports_players.score} for actual / proj
  form    {name: sports_form.goalie_form} (last 5 minus his prior 20, x100) for actual / proj
THE GAME TABLE (games()): every regular-season NHL final with a sane close, + ESPN's open (2023+), + the paid
odds-history MORNING look (15:00Z, 2021-01..2023-04 - the 8 AM board's hour; nhl_odds_1102/lib.py's consensus).
Halves: train = seasons to 2022-23, held = 2023-24 on. R3 = the dogs_1117 replay rows (2023-10 -> 2026-11, today's
code, the close): train to 2025-06-30, held after, live from 2026-10-13 (dlib.half)."""
import csv
import glob
import math
import os
import pickle
import random
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "results", "studies", "dogs_1117"))
os.chdir(ROOT)
CACHE = os.path.expanduser("~/.cache/d503_goalie1119")
os.makedirs(CACHE, exist_ok=True)


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def am(d):
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def nv(h, a):
    ph, pa = 1 / dec(h), 1 / dec(a)
    return ph / (ph + pa)


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y}-{(y + 1) % 100:02d}" if m >= 8 else f"{y - 1}-{y % 100:02d}"


def half(d):
    return "train" if season(d) <= "2022-23" else "held"


def sane(h, a):
    try:
        h, a = float(h), float(a)
    except (TypeError, ValueError):
        return False
    return abs(h) >= 100 and abs(a) >= 100 and 0.99 <= 1 / dec(h) + 1 / dec(a) <= 1.12


def goalies(force=False):
    """{(gid, team id): dict} - see the module doc."""
    p = os.path.join(CACHE, "goalies.pkl")
    if os.path.exists(p) and not force:
        return pickle.load(open(p, "rb"))
    import sports_players as sp
    import sports_goalies as sg
    import sports_form as sf
    rows = [r for r in csv.DictReader(open("data/sports/players/nhl.csv")) if r.get("role", "G") == "G"]
    rows.sort(key=lambda r: r["start"])
    by_team, by_player = defaultdict(list), defaultdict(list)
    out = {}
    for r in rows:
        t, st_ = r["team"], r["start"]
        mine = by_team[t]
        if mine and mine[-1]["gid"] == r["gid"]:
            continue
        last = sp.last_starter(mine, t, st_)
        n1 = sg.number_one(mine, t, st_)
        proj = sp.projected_starter(mine, t, st_) if mine else None
        b2b = bool(mine) and sp._hours(mine[-1]["start"], st_) < sp.PROJ_B2B_DAYS * 24
        lo = sp.recent_floor("nhl", st_)
        sv, form, n10 = {}, {}, {}
        floor = sg.season_start(st_)
        ssn = [x for x in mine if x["start"] >= floor]
        for nm in {r["player"], proj, last} - {None}:
            his = by_player[nm]
            sv[nm] = sp.score("G", [x for x in his if lo <= x["start"] < st_][-sp.RECENT["G"]:])
            form[nm] = sf.goalie_form(his, nm, st_)
            n10[nm] = sum(1 for x in ssn[-10:] if x["player"] == nm)
        out[(r["gid"], t)] = dict(actual=r["player"], last=last, n1=n1[0] if n1 else None,
                                  n1_share=(n1[1] / n1[2]) if n1 else None, proj=proj, b2b=b2b, sv=sv, form=form,
                                  n10=n10, gp=len(ssn), sa=r["sa"], ga=r["ga"])
        mine.append(r)
        by_player[r["player"]].append(r)
    pickle.dump(out, open(p, "wb"))
    return out


def morning():
    """{gid: nhl_odds_1102 row} (the paid 15:00Z look: r['morning'] / r['open'] = dict(p, dh, da, hrs) or None)."""
    p = os.path.join(CACHE, "morning.pkl")
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("lib1102", os.path.join(ROOT, "results", "studies", "nhl_odds_1102", "lib.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.OUT = CACHE
    rows = m.build()["rows"]
    out = {r["id"]: r for r in rows}
    pickle.dump(out, open(p, "wb"))
    return out


def games():
    """[side dicts] - two a game: regular season finals 2016-26 with a sane close. Prices: close (dec_c / p_c no-vig),
    ESPN open (dec_o / p_o), the paid morning (dec_m / p_m). Goalie facts for me / the other side (g_me / g_op)."""
    p = os.path.join(CACHE, "sides.pkl")
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    G = goalies()
    M = morning()
    out = []
    for f in sorted(glob.glob("data/sports/games/nhl/*.csv")):
        for g in csv.DictReader(open(f)):
            if g["status"] != "final" or g.get("stype") != "2" or g["home_score"] == "" or not sane(g["ml_home"], g["ml_away"]):
                continue
            hs, as_ = int(g["home_score"]), int(g["away_score"])
            if hs == as_:
                continue
            gh, ga = G.get((g["id"], g["home"])), G.get((g["id"], g["away"]))
            if not gh or not ga:
                continue
            pc = nv(g["ml_home"], g["ml_away"])
            op = sane(g.get("ml_home_open"), g.get("ml_away_open"))
            po = nv(g["ml_home_open"], g["ml_away_open"]) if op else None
            mr = M.get(g["id"]) or {}
            m = mr.get("morning")
            for s, o in (("home", "away"), ("away", "home")):
                me, ot = (gh, ga) if s == "home" else (ga, gh)
                out.append(dict(
                    gid=g["id"], date=g["start"][:10], start=g["start"], side=s, team=g[s], name=g[s + "_name"],
                    opp=g[o + "_name"], home=s == "home", won=(hs > as_) == (s == "home"),
                    dec_c=dec(g["ml_" + s]), odds_c=int(float(g["ml_" + s])), p_c=pc if s == "home" else 1 - pc,
                    dec_o=dec(g["ml_" + s + "_open"]) if op else None, p_o=(po if s == "home" else 1 - po) if op else None,
                    dec_m=(m["dh"] if s == "home" else m["da"]) if m else None,
                    p_m=(m["p"] if s == "home" else 1 - m["p"]) if m else None, hrs_m=m["hrs"] if m else None,
                    g_me=me, g_op=ot, season=season(g["start"])))
    pickle.dump(out, open(p, "wb"))
    return out


# ------------------------------------------------------------------ the bar's arithmetic
def st(rs, key="dec_c", pts=0.0):
    """rs = side dicts (won + a decimal price under `key`). pts = points of win chance taken off the price."""
    rs = [r for r in rs if r.get(key)]
    n = len(rs)
    if not n:
        return dict(n=0, w=0, roi=0.0, z=0.0, net=0.0, need=0.0, wp=0.0)
    net = var = bev = 0.0
    w = 0
    for r in rs:
        d = r[key] if not pts else 1 / min(0.99, 1 / r[key] + pts / 100)
        w += bool(r["won"])
        net += (d - 1) if r["won"] else -1.0
        bev += 1 / r[key]
        var += (1 / r[key]) * (1 - 1 / r[key])
    return dict(n=n, w=w, roi=100 * net / n, z=(w - bev) / math.sqrt(var) if var else 0.0, net=net, need=100 * bev / n,
                wp=100 * w / n)


def line(name, rs, key="dec_c", say=print, hf=half, w=52):
    rs = [r for r in rs if r.get(key)]
    a = st(rs, key)
    t = st([r for r in rs if hf(r["date"]) == "train"], key)
    h = st([r for r in rs if hf(r["date"]) == "held"], key)
    seas = defaultdict(list)
    for r in rs:
        if hf(r["date"]) in ("train", "held"):
            seas[season(r["date"])].append(r)
    up = sum(st(v, key)["roi"] > 0 for v in seas.values())
    w1 = st(rs, key, 1.0)
    if not a["n"]:
        say(f"  {name:{w}s} n     0")
        return a
    say(f"  {name:{w}s} n {a['n']:5d} {a['w']:4d}-{a['n'] - a['w']:<4d} {a['wp']:4.1f}% (needs {a['need']:4.1f}) {a['roi']:+6.1f}% z {a['z']:+5.2f}"
        f" | train {t['roi']:+6.1f}% ({t['n']:4d}) | held {h['roi']:+6.1f}% ({h['n']:4d}) | up {up}/{len(seas)} | 1pt worse {w1['roi']:+6.1f}%")
    return dict(a, train=t, held=h, up=up, ns=len(seas))


def placebo(rs, pool, key="dec_c", draws=2000, seed=1119, lo=False):
    """how many of 2,000 random same-size sets from `pool` did as well (lo: as badly) flat"""
    def f(r):
        return (r[key] - 1) if r["won"] else -1.0
    rs = [r for r in rs if r.get(key)]
    pool = [f(r) for r in pool if r.get(key)]
    n = len(rs)
    if n < 10 or len(pool) <= n:
        return None
    mine = sum(f(r) for r in rs) / n
    rnd = random.Random(seed)
    if lo:
        return sum(1 for _ in range(draws) if sum(rnd.sample(pool, n)) / n <= mine)
    return sum(1 for _ in range(draws) if sum(rnd.sample(pool, n)) / n >= mine)


class Tee:
    def __init__(self, path):
        self.f = open(path, "w")

    def __call__(self, *a):
        s = " ".join(str(x) for x in a)
        print(s)
        self.f.write(s + "\n")
        self.f.flush()
