"""11/14 FOOTBALL PROFIT STUDIES - shared helpers (read-only on the repo; caches in ~/.cache/d503_fb1114).
SIDES: one row a side of every priced, finished regular-season NFL / college football game 2018-26 at ESPN's close
(its own juice), with the state known BEFORE kickoff, built from every final on file (priced or not):
  season-to-date record, points for / against, one-score record (decided by 8 or fewer), the Pythagorean win share,
  the last game (its closing moneyline / spread, the result, the margin), FBS membership (walk-forward,
  sports_players.fbs_set), a same-conference flag (lib.football_conferences, inferred from the schedule), the week.
REPLAY: the 11/14 football replay board on today's code (funnel5.py rows, ~/.cache/d503_fb1114/rows).
Train = seasons 2018-21, held out = 2022 / 2023 / 2024 / 2025 apart, 2026 = now (a held-out season too).
The replay's train / held split: train 2018-2022 seasons (to 2023-06-30), held out after (2023-26) - 5 / 4 seasons."""
import json, math, os, pickle, random, sys
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "daily_1113"))
import lib  # noqa: E402  (chdir to the repo root)
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402
import sports_players as sp  # noqa: E402

CACHE = os.path.join(os.path.expanduser("~"), ".cache", "d503_fb1114")
os.makedirs(CACHE, exist_ok=True)
TRAIN = (2018, 2021)
HELD = [2022, 2023, 2024, 2025, 2026]
dec, num, profit = lib.dec, lib.num, lib.profit


def _t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


def sides(lg):
    cache = os.path.join(CACHE, f"_sides_{lg}.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    allg = sd.load_games(lg)
    fin = sm.finals(allg, lg)
    hist = defaultdict(list)     # team -> [dict] before now
    conf = {}
    out = []
    first_start = {}
    for g in fin:
        s = lib.season(g["start"])
        first_start.setdefault(s, g["start"])
    for g in fin:
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
        except (TypeError, ValueError):
            continue
        season = lib.season(g["start"])
        stype = str(g.get("stype") or "2")
        mh, ma = num(g.get("ml_home")), num(g.get("ml_away"))
        sp_h = num(g.get("spread_home"))
        neutral = str(g.get("neutral")) == "1"
        fbs = None
        if lg == "ncaaf":
            fbs = sp.fbs_set(allg, g["start"])
            if season not in conf:
                af = [{"season": lib.season(x["start"]), "neutral": str(x.get("neutral")) == "1", "stype": str(x.get("stype") or "2"),
                       "start": x["start"], "home": x["home"], "away": x["away"]} for x in fin]
                conf[season] = lib.football_conferences(af, season, sp.fbs_set(allg, f"{season}-12-15") or set())
        priced = mh is not None and ma is not None and mh != 0 and ma != 0 and hs != as_ and stype == "2"
        if priced:
            nvh = lib.nv(mh, ma)
            gg = {"hs": hs, "as": as_, "sp": sp_h, "spho": num(g.get("spread_home_odds")), "spao": num(g.get("spread_away_odds"))}
            for side, team, opp, odds, won in (("home", g["home"], g["away"], mh, hs > as_), ("away", g["away"], g["home"], ma, as_ > hs)):
                def st(t):
                    h = [x for x in hist[t] if x["season"] == season]
                    n = len(h)
                    pf, pa = sum(x["pf"] for x in h), sum(x["pa"] for x in h)
                    one = [x for x in h if abs(x["pf"] - x["pa"]) <= 8]
                    w = sum(x["pf"] > x["pa"] for x in h)
                    py = (pf ** 2.37 / (pf ** 2.37 + pa ** 2.37)) if pf + pa > 0 else 0.5
                    return {"n": n, "w": w, "pf": pf, "pa": pa, "one_n": len(one), "one_w": sum(x["pf"] > x["pa"] for x in one),
                            "py": py, "last": h[-1] if h else None}
                me, op = st(team), st(opp)
                line = None if sp_h is None else (sp_h if side == "home" else -sp_h)
                cf = conf.get(season) or {}
                out.append({
                    "id": g["id"], "start": g["start"], "season": season, "side": side, "team": team, "opp": opp,
                    "home": side == "home", "neutral": neutral, "odds": odds, "won": won, "p_nv": nvh if side == "home" else 1 - nvh,
                    "line": line, "ats": lib.ats(gg, side), "total": num(g.get("total")),
                    "ovo": num(g.get("over_odds")), "uno": num(g.get("under_odds")), "pts": hs + as_,
                    "me": me, "op": op,
                    "fbs": None if fbs is None else team in fbs, "ofbs": None if fbs is None else opp in fbs,
                    "conf_game": bool(cf.get(team) and cf.get(team) == cf.get(opp)),
                    "week": int((_t(g["start"]) - _t(first_start[season])).days // 7) + 1,
                    "month": int(g["start"][5:7]), "dow": _t(g["start"]).weekday(),
                })
        for side, team, opp in (("home", g["home"], g["away"]), ("away", g["away"], g["home"])):
            pf, pa = (hs, as_) if side == "home" else (as_, hs)
            o = mh if side == "home" else ma
            lt = None if sp_h is None else (sp_h if side == "home" else -sp_h)
            hist[team].append({"season": season, "start": g["start"], "pf": pf, "pa": pa, "odds": o, "line": lt,
                               "home": side == "home", "neutral": neutral, "opp": opp, "stype": stype})
    out.sort(key=lambda r: r["start"])
    pickle.dump(out, open(cache, "wb"))
    return out


def ml(r):
    return profit(r["won"], dec(r["odds"]))


def cell(name, rs, kind="ml", say=print):
    f = ml if kind == "ml" else (lambda r: r["ats"])
    bets = [(r["season"], f(r)) for r in rs if f(r) is not None]
    res = lib.summ(bets, TRAIN, HELD)
    say(lib.fmt(name, res))
    return res


def placebo(rs, pool, kind="ml", n=2000, seed=1114, worse=False):
    f = ml if kind == "ml" else (lambda r: r["ats"])
    rs = [r for r in rs if f(r) is not None]
    pool = [r for r in pool if f(r) is not None]
    if not rs or len(pool) < len(rs):
        return None
    got = sum(f(r) for r in rs) / len(rs)
    rnd = random.Random(seed)
    vals = [f(r) for r in pool]
    k = len(rs)
    if worse:
        return sum(1 for _ in range(n) if sum(rnd.sample(vals, k)) / k <= got)
    return sum(1 for _ in range(n) if sum(rnd.sample(vals, k)) / k >= got)


# ---------------- the replay board rows ----------------
RDIR = os.path.join(CACHE, "rows")


def replay(leagues=("nfl", "ncaaf"), markets=("ml",)):
    rows, seen = [], set()
    import glob
    for fp in sorted(glob.glob(os.path.join(RDIR, "f*.jsonl"))):
        for ln in open(fp):
            try:
                r = json.loads(ln)
            except ValueError:          # (a chunk still being written)
                continue
            if r["league"] not in leagues or r["market"] not in markets or r.get("result") not in ("won", "lost", "push"):
                continue
            k = (r["date"], r["gid"], r["side"], r["market"])
            if k in seen:
                continue
            seen.add(k)
            r["y"] = 1.0 if r["result"] == "won" else (0.0 if r["result"] == "lost" else 0.5)
            y, m = int(r["date"][:4]), int(r["date"][5:7])
            r["season"] = y if m >= 7 else y - 1
            r["half"] = "train" if r["season"] <= 2022 else "held"
            r["own"] = None if r.get("edge_own") is None else (r["edge_own"] + 1) / r["dec"]
            rows.append(r)
    return rows


def bet(rs, units=None):
    """(n, wins, flat roi %, z, units won, units risked)"""
    pr, uw, uk = [], 0.0, 0.0
    for r in rs:
        p = (r["dec"] - 1) if r["y"] == 1 else (-1.0 if r["y"] == 0 else 0.0)
        pr.append(p)
        u = (r.get("units") or 0) if units is None else units
        uw += u * p
        uk += u
    n = len(pr)
    if not n:
        return 0, 0, 0.0, 0.0, 0.0, 0.0
    m = sum(pr) / n
    s = math.sqrt(sum((x - m) ** 2 for x in pr) / max(1, n - 1))
    return n, sum(r["y"] == 1 for r in rs), 100 * m, (m / (s / math.sqrt(n)) if s else 0.0), uw, uk


def rline(name, rs, say=print):
    n, w, roi, z, uw, uk = bet(rs)
    tr = bet([r for r in rs if r["half"] == "train"])
    he = bet([r for r in rs if r["half"] == "held"])
    ss = defaultdict(list)
    for r in rs:
        ss[r["season"]].append(r)
    up = sum(bet(v)[2] > 0 for v in ss.values())
    now = bet([r for r in rs if r["season"] == 2026])
    say(f"  {name:56s} {w:4d}-{n - w:<4d} flat {roi:+6.1f}% z {z:+5.2f} | {uw:+6.1f}u on {uk:5.1f}u | train {tr[1]}-{tr[0] - tr[1]} {tr[2]:+6.1f}% "
        f"| held {he[1]}-{he[0] - he[1]} {he[2]:+6.1f}% | up {up}/{len(ss)} | 2026 {now[1]}-{now[0] - now[1]} {now[4]:+.1f}u")
    return dict(n=n, w=w, roi=roi, z=z, uw=uw, uk=uk, train=tr[2], held=he[2], up=up, ns=len(ss))


def rplacebo(rs, pool, n=2000, seed=1114, worse=False):
    """How often a random same-size set from `pool` (drawn season by season in the same counts) does at least as well
    (or as badly, worse=True) on flat ROI."""
    def roi(x):
        return sum(((r["dec"] - 1) if r["y"] == 1 else (-1.0 if r["y"] == 0 else 0.0)) for r in x) / max(1, len(x))
    got = roi(rs)
    by = defaultdict(list)
    for r in pool:
        by[r["season"]].append(r)
    need = defaultdict(int)
    for r in rs:
        need[r["season"]] += 1
    rnd = random.Random(seed)
    hit = 0
    for _ in range(n):
        s = []
        for se, k in need.items():
            s += rnd.sample(by[se], min(k, len(by[se])))
        v = roi(s)
        hit += (v <= got) if worse else (v >= got)
    return hit
