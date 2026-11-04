"""11/3 FABLE: COLLEGE HOOPS KNOWLEDGE (A) - shared loaders (read-only on the repo; caches in ~/.cache/d503_studies).

The side table is the 11/3 (B) one (results/studies/cbb_1103_b/lib.py - one row per team side 2016-27, no
look-ahead: prices, Elo, the inferred conference / tier, streaks, rest, game numbers). On top of it:
  teambox()   - the full TEAM box (data/sports/teamstats - threes / free throws / turnovers / steals / rebounds),
                2021-22 .. now, {gid: {team: {...}}}
  playerbox() - every player's line (data/sports/roster/ncaab_*.csv.gz) {gid: {team: {pid: (min, pts, fga, reb, ast,
                starter, name)}}}
  coaches     - the reconstructed college hoops coach table (sports_ncaab_coaches - built by s1_coaches.py)
Prices: ESPN's close 2018-26, ESPN's ML open 2023-25 (the second check). TRAIN 2018-22, HELD 2023 / 2024 / 2025
apart for the price-only studies; the box-score studies start in 2021 (train 2021-22, held 2023-25)."""
import csv, glob, gzip, importlib.util, json, math, os, pickle, statistics, sys
from collections import defaultdict, Counter

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location("cbb_b_lib", os.path.join(ROOT, "results/studies/cbb_1103_b/lib.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)
CACHE = B.CACHE
TRAIN, HELD, NOW = B.TRAIN, B.HELD, B.NOW
BOX_TRAIN = (2021, 2022)
dec, num, season, night, nv = B.dec, B.num, B.season, B.night, B.nv
profit_ml, profit_ats, profit_open, st, cell, fmt = B.profit_ml, B.profit_ats, B.profit_open, B.st, B.cell, B.fmt
regular, dogs, favs, spreads = B.regular, B.dogs, B.favs, B.spreads


def rows():
    return B.build()


def _split(s):
    a, b = str(s).split("-")
    return int(a), int(b)


def teambox():
    """{gid: {team id: dict(fgm, fga, tpm, tpa, ftm, fta, oreb, dreb, reb, ast, stl, blk, to, fouls, poss)}}."""
    pk = os.path.join(CACHE, "cbbk_teambox.pkl")
    if os.path.exists(pk):
        return pickle.load(open(pk, "rb"))
    out = {}
    files = [os.path.join(ROOT, "data/sports/teamstats/ncaab.jsonl")] + \
        sorted(glob.glob(os.path.join(ROOT, "data/sports/teamstats/ncaab/*.jsonl")))
    for fn in files:
        for line in open(fn):
            try:
                d = json.loads(line)
                tm = {}
                for tid, t in d["teams"].items():
                    fgm, fga = _split(t["fieldGoalsMade-fieldGoalsAttempted"])
                    tpm, tpa = _split(t["threePointFieldGoalsMade-threePointFieldGoalsAttempted"])
                    ftm, fta = _split(t["freeThrowsMade-freeThrowsAttempted"])
                    oreb, dreb = int(t["offensiveRebounds"]), int(t["defensiveRebounds"])
                    to = int(t.get("totalTurnovers") or t.get("turnovers") or 0)
                    tm[tid] = dict(fgm=fgm, fga=fga, tpm=tpm, tpa=tpa, ftm=ftm, fta=fta, oreb=oreb, dreb=dreb,
                                   reb=int(t.get("totalRebounds") or oreb + dreb), ast=int(t.get("assists") or 0),
                                   stl=int(t.get("steals") or 0), blk=int(t.get("blocks") or 0), to=to,
                                   fouls=int(t.get("fouls") or 0), poss=fga - oreb + to + 0.475 * fta)
                if len(tm) == 2:
                    out[d["gid"]] = tm
            except (KeyError, ValueError, TypeError):
                continue
    pickle.dump(out, open(pk, "wb"))
    return out


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def playerbox():
    """{gid: {team: {pid: (min, pts, fga, reb, ast, starter, name)}}} for every saved college hoops box."""
    pk = os.path.join(CACHE, "cbbk_playerbox.pkl")
    if os.path.exists(pk):
        return pickle.load(open(pk, "rb"))
    box = {}
    for fn in sorted(glob.glob(os.path.join(ROOT, "data/sports/roster/ncaab_*.csv.gz"))):
        with gzip.open(fn, "rt") as f:
            for r in csv.DictReader(f):
                try:
                    stt = json.loads(r["stats"] or "{}")
                except ValueError:
                    continue
                fg = str(stt.get("fieldGoalsMade-fieldGoalsAttempted") or "0-0").split("-")
                box.setdefault(r["gid"], {}).setdefault(r["team"], {})[r["pid"]] = (
                    _int(stt.get("minutes")), _int(stt.get("points")), _int(fg[1]) if len(fg) > 1 else 0,
                    _int(stt.get("rebounds")), _int(stt.get("assists")), r.get("starter") == "1", r.get("player") or "")
    pickle.dump(box, open(pk, "wb"))
    return box


def coaches():
    import sports_ncaab_coaches as nc
    return nc.load()


class Out(B.Out):
    def __init__(self, name):
        super().__init__(name)

    def save(self):
        self.lines.append(f"\ncells looked at: {self.cells}")
        open(os.path.join(OUT, self.name + "_out.txt"), "w").write("\n".join(self.lines) + "\n")


def ncdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def q(v, cuts):
    """Bucket index of v against ascending cuts."""
    for i, c in enumerate(cuts):
        if v < c:
            return i
    return len(cuts)


def by_season_ats(rows_, label, out):
    """Short helper: ATS + ML cells for a set of sides, the dogs and the small favorites inside it."""
    out.c(f"{label} ATS", spreads(rows_), profit_ats)
    out.c(f"{label} dog +100..+350 ML", dogs(rows_))
    out.c(f"{label} fav -101..-150 ML", favs(rows_))
