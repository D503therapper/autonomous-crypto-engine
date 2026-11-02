"""11/3 DEEP - COLLEGE HOOPS ROSTERS: the shared table (read-only on the repo; caches in ~/.cache/d503_studies).

Rows = the 11/3 (B) team-side table (results/studies/cbb_1103_b/lib.py: every college hoops game 2016-27, no look-ahead,
ESPN close + 2023-25 open, gn = the team's game number, tier from the inferred conferences) + ROSTER features from the
ESPN box scores (data/sports/roster/ncaab_<season>.csv.gz: every player every game, 2021-22 .. now - minutes, points,
FG made-attempted, rebounds, assists; no free throws / turnovers, so 'possessions used' = FGA, the usage proxy).

PLAYERS are matched by ESPN's athlete id (pid), which survives a transfer (1,225 players changed D1 teams 2023 -> 2024 on
the same id). Names are NOT used to join (243 'same name, new id' pairs 2023 -> 2024 are mostly namesakes / non-D1 shells).

Two roster views per team-season S:
  PRE (preseason, the cleanest the books could know): the men who log a minute for the team anywhere in season S. The
      roster is public in October; the leak is a man hurt all season (counted as 'gone') - mild, and it errs toward the
      market knowing it.
  SO-FAR (strict, no look-ahead): the men in the team's box scores BEFORE tonight - the minutes they're playing now.
Last season's production (S-1) per player: minutes, points, FGA, games, his team.
TRAIN = 2022, 2023 (2022-23, 2023-24 seasons); HELD OUT = 2024, 2025 apart; NOW = 2026 (a few games). Box scores start
2021, so 2021 has no 'last season'."""
import csv, gzip, importlib.util, json, math, os, pickle, statistics, sys
from collections import defaultdict, Counter

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
CACHE = os.environ.get("STUDY_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "d503_studies")
os.makedirs(CACHE, exist_ok=True)
TRAIN = (2022, 2023)
HELD = (2024, 2025)

_spec = importlib.util.spec_from_file_location("cbbB", os.path.join(ROOT, "results/studies/cbb_1103_b/lib.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)
dec, nv, profit_ml, profit_ats, profit_open = B.dec, B.nv, B.profit_ml, B.profit_ats, B.profit_open


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def load_box():
    """{gid: {team: {pid: (min, pts, fga, starter)}}}, {pid: name}, {gid: start} for every saved college hoops box."""
    pk = os.path.join(CACHE, "deep_cbb_box.pkl")
    if os.path.exists(pk):
        return pickle.load(open(pk, "rb"))
    box, names, starts = {}, {}, {}
    d = os.path.join(ROOT, "data/sports/roster")
    for fn in sorted(os.listdir(d)):
        if not (fn.startswith("ncaab_") and fn.endswith(".csv.gz")):
            continue
        with gzip.open(os.path.join(d, fn), "rt") as f:
            for r in csv.DictReader(f):
                try:
                    st = json.loads(r["stats"] or "{}")
                except ValueError:
                    continue
                m = _int(st.get("minutes"))
                fg = str(st.get("fieldGoalsMade-fieldGoalsAttempted") or "0-0").split("-")
                fga = _int(fg[1]) if len(fg) > 1 else 0
                box.setdefault(r["gid"], {}).setdefault(r["team"], {})[r["pid"]] = (
                    m, _int(st.get("points")), fga, r.get("starter") == "1")
                names[r["pid"]] = r["player"]
                starts[r["gid"]] = r["start"]
    out = (box, names, starts)
    pickle.dump(out, open(pk, "wb"))
    return out


def rows():
    return B.build()


def season_lines(box, starts, rws):
    """{season: {pid: {team: [min, pts, fga, games]}}} and {season: {team: [min, pts, fga, games]}} (regular season +
    postseason - every game we hold)."""
    sea = {x["id"]: x["season"] for x in rws}
    P = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0])))
    T = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
    for gid, tms in box.items():
        s = sea.get(gid)
        if s is None:
            st = starts.get(gid) or ""
            s = B.season(st) if st else None
        if s is None:
            continue
        for tm, ps in tms.items():
            t = T[s][tm]
            t[3] += 1
            for pid, (m, pts, fga, _) in ps.items():
                if m <= 0:
                    continue
                a = P[s][pid][tm]
                a[0] += m; a[1] += pts; a[2] += fga; a[3] += 1
                t[0] += m; t[1] += pts; t[2] += fga
    return P, T


def stats(ps):
    if not ps:
        return None
    n = len(ps)
    m = sum(ps) / n
    sd = statistics.pstdev(ps) if n > 1 else 1.0
    return {"n": n, "roi": m, "z": (m / (sd / math.sqrt(n))) if sd else 0.0,
            "win": sum(1 for p in ps if p > 0) / n}


def cell(name, xs, fn, out=None):
    """One line: ALL | TRAIN (seasons up) | each held season | HELD | 2026, for the bets fn(x) over rows xs."""
    by = defaultdict(list)
    for x in xs:
        p = fn(x)
        if p is not None:
            by[x["season"]].append(p)
    allp = [p for v in by.values() for p in v]
    tr = [p for s, v in by.items() if TRAIN[0] <= s <= TRAIN[1] for p in v]
    he = [p for s in HELD for p in by.get(s, [])]
    up = f"{sum(1 for s in range(TRAIN[0], TRAIN[1] + 1) if by.get(s) and sum(by[s]) > 0)}/" \
         f"{sum(1 for s in range(TRAIN[0], TRAIN[1] + 1) if by.get(s))}"
    hup = f"{sum(1 for s in HELD if by.get(s) and sum(by[s]) > 0)}/{sum(1 for s in HELD if by.get(s))}"

    def f(v):
        s = stats(v)
        return f"{s['n']:5d} {s['roi']*100:+6.1f}%" + (f" z{s['z']:+5.2f}" if s else "") if s else "    -        "
    line = (f"{name:62s} ALL {f(allp)} | TRAIN {f(tr)} up {up} | " +
            " | ".join(f"{s} {f(by.get(s, []))}" for s in HELD) + f" | HELD {f(he)} up {hup} | 2026 {f(by.get(2026, []))}")
    if out is not None:
        out.append(line)
    print(line)
    return {"all": stats(allp), "train": stats(tr), "held": stats(he), "train_up": up, "held_up": hup,
            **{str(s): stats(by.get(s, [])) for s in HELD}}


def ats_resid(x):
    """the side's margin + its closing spread (points it beat the number by), or None."""
    if x.get("sp") is None:
        return None
    return x["margin"] + x["sp"]
