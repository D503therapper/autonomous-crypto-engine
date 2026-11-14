"""11/14 COLLEGE HOOPS PROFIT STUDIES - the game table for the TOTALS studies (read-only on the repo).
Every college hoops regular-season final 2016-26 from data/sports/games/ncaab, with what is known before the tip:
rest days (each team's previous game of ANY kind on file), the visitor's trip in time zones (its home floor's tzo vs
tonight's), the conference game flag (sports_ncaab_knowledge.conferences - the schedule-inferred leagues, the same
season's league; the league is the one the season's schedule shows, which a team knows before November), the game's
place in the team's season, both teams' season scoring (points for + against a game, prior finals), the meeting
number this season, the last meeting's points. Graded at the CLOSING total and its own over / under price (-110 when
missing); a push returns 0. TRAIN = seasons 2018-22, HELD OUT = 2023-26 (the funnel split - totals start in 2018).
Never cut on the over / under juice (the 11/12 study 15 warning: some 2024-26 archive juice is post-tip)."""
import math, os, pickle, random, statistics, sys
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "d503_cbb1114")
os.makedirs(CACHE, exist_ok=True)
random.seed(1114)


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def season_of(start):
    y, m = int(start[:4]), int(start[5:7])
    return y if m >= 7 else y - 1


def pay(odds):
    o = num(odds) or -110
    return o / 100 if o > 0 else 100 / -o


def build():
    pk = os.path.join(CACHE, "totals_table.pkl")
    if os.path.exists(pk):
        return pickle.load(open(pk, "rb"))
    import sports_data as sd
    import sports_ncaab_knowledge as nk
    games = sd.load_games()
    allg = sorted((g for g in games.values() if g.get("league") == "ncaab" and g.get("status") == "final"
                   and num(g.get("home_score")) is not None), key=lambda g: g["start"])
    confs = {}
    for s in range(2016, 2027):
        try:
            win = {k: v for k, v in games.items() if v.get("league") == "ncaab"      # (the season's own window only:
                   and f"{s - 1}-01-01" <= str(v.get("start") or "")[:10] < f"{s + 1}-07-01"}   # the live call sees no later season)
            confs[s] = nk.conferences(win, s)
        except Exception as e:                              # noqa: BLE001
            print("conferences failed", s, e)
            confs[s] = {}
    home_tz = defaultdict(list)
    for g in allg:
        if str(g.get("neutral")) != "1" and num(g.get("tzo")) is not None:
            home_tz[g["home"]].append(num(g["tzo"]))
    home_tz = {t: statistics.median(v) for t, v in home_tz.items()}
    last = {}                         # team -> (start, season)
    sc = defaultdict(lambda: [0, 0.0, 0.0])   # (team, season) -> [games, pts for, pts against]
    meet = defaultdict(list)          # (season, pair) -> [total points of earlier meetings]
    gi = defaultdict(int)             # (team, season) -> games played
    rows = []
    for g in allg:
        s = season_of(g["start"])
        h, a = g["home"], g["away"]
        hs, as_ = num(g["home_score"]), num(g["away_score"])
        t = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M")

        def rest(team):
            x = last.get(team)
            if not x or x[1] != s:
                return None
            return (t - x[0]).total_seconds() / 86400.0
        ch, ca = confs.get(s, {}).get(h), confs.get(s, {}).get(a)
        r = {"id": g["id"], "start": g["start"], "season": s, "month": g["start"][5:7], "home": h, "away": a,
             "hn": g.get("home_name"), "an": g.get("away_name"), "neu": str(g.get("neutral")) == "1",
             "stype": str(g.get("stype") or ""), "tot": num(g.get("total")), "oo": g.get("over_odds"), "uo": g.get("under_odds"),
             "sp": num(g.get("spread_home")), "spo_h": num(g.get("spread_home_odds")), "spo_a": num(g.get("spread_away_odds")), "mlh": num(g.get("ml_home")), "mla": num(g.get("ml_away")),
             "pts": hs + as_, "margin": hs - as_, "el": num(g.get("elev")),
             "rh": rest(h), "ra": rest(a), "gh": gi[(h, s)], "ga": gi[(a, s)],
             "conf": bool(ch and ca and ch[0] is not None and ch[0] == ca[0]), "pow_h": bool(ch and ch[1]), "pow_a": bool(ca and ca[1]),
             "tz_trip": (None if num(g.get("tzo")) is None or a not in home_tz else num(g["tzo"]) - home_tz[a]),
             "tz_trip_h": (None if num(g.get("tzo")) is None or h not in home_tz else num(g["tzo"]) - home_tz[h]),
             "local_hr": None, "meet_n": len(meet[(s, frozenset((h, a)))]),
             "meet_last": (meet[(s, frozenset((h, a)))] or [None])[-1]}
        tz = num(g.get("tzo"))
        if tz is not None:
            r["local_hr"] = (t.hour + tz) % 24
        for side, team in (("h", h), ("a", a)):
            n, pf, pa = sc[(team, s)]
            r[f"pf_{side}"] = pf / n if n else None
            r[f"pa_{side}"] = pa / n if n else None
        rows.append(r)
        last[h] = (t, s)
        last[a] = (t, s)
        gi[(h, s)] += 1
        gi[(a, s)] += 1
        sc[(h, s)][0] += 1; sc[(h, s)][1] += hs; sc[(h, s)][2] += as_
        sc[(a, s)][0] += 1; sc[(a, s)][1] += as_; sc[(a, s)][2] += hs
        meet[(s, frozenset((h, a)))].append(hs + as_)
    pickle.dump(rows, open(pk, "wb"))
    return rows


def bet(r, side):
    if r["tot"] is None:
        return None
    if r["pts"] == r["tot"]:
        return 0.0
    won = (r["pts"] > r["tot"]) == (side == "over")
    return pay(r["oo"] if side == "over" else r["uo"]) if won else -1.0


CELLS = [0]


def placebo(ps_cell, pool, n=2000):
    """How many of n random sets of the same size and season mix from `pool` [(season, pnl)] do as well."""
    if len(ps_cell) < 30:
        return None
    by = defaultdict(list)
    for s, p in pool:
        by[s].append(p)
    need = defaultdict(int)
    for s, _ in ps_cell:
        need[s] += 1
    mine = sum(p for _, p in ps_cell)
    hit = 0
    for _ in range(n):
        tot = 0.0
        for s, c in need.items():
            if by[s]:
                tot += sum(random.sample(by[s], c)) if c <= len(by[s]) else sum(random.choices(by[s], k=c))
        hit += tot >= mine
    return hit


def cell(label, rows, side, pool=None, min_n=40):
    """One printed totals cell: W-L, ROI at the close, z, train 2018-22 / held 2023-26, seasons up, the placebo."""
    bs = [(r["season"], bet(r, side)) for r in rows]
    bs = [(s, p) for s, p in bs if p is not None]
    if len(bs) < min_n:
        if bs:
            print(f"   {label:62s} {side:5s} only {len(bs)}")
        return None
    CELLS[0] += 1
    ps = [p for _, p in bs]
    m = sum(ps) / len(ps)
    sd = statistics.pstdev(ps) or 1
    z = m / (sd / math.sqrt(len(ps)))
    tr = [p for s, p in bs if s <= 2022]
    he = [p for s, p in bs if s >= 2023]
    by = defaultdict(list)
    for s, p in bs:
        by[s].append(p)
    up = sum(sum(v) > 0 for v in by.values())
    pb = None
    if pool is not None and abs(z) >= 1.5:
        pp = [(r["season"], bet(r, side)) for r in pool]
        pb = placebo(bs, [(s, p) for s, p in pp if p is not None])
    w = sum(p > 0 for p in ps)
    l_ = sum(p < 0 for p in ps)
    f = lambda v: (100 * sum(v) / len(v)) if v else float("nan")
    print(f"   {label:62s} {side:5s} {w:4d}-{l_:<4d} ROI {100 * m:+6.1f}% n{len(ps):<5d} z {z:+4.1f} | train {f(tr):+6.1f}% n{len(tr):<4d}"
          f" | held {f(he):+6.1f}% n{len(he):<4d} | up {up}/{len(by)}" + (f" | placebo {pb}/2000" if pb is not None else "")
          + " | " + " ".join(f"{s % 100}:{f(v):+.0f}" for s, v in sorted(by.items())))
    return {"n": len(ps), "roi": m, "z": z, "tr": f(tr), "he": f(he), "up": up, "ns": len(by), "pb": pb}
