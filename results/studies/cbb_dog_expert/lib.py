"""11/3 - FABLE: COLLEGE HOOPS DOG EXPERT - the shared table + helpers (read-only on the repo; caches in $STUDY_CACHE or
~/.cache/d503_studies, never the repo).

Rows = the 11/3 KNOWLEDGE (B) side table (results/studies/cbb_knowledge_b/lib.py): one row per team side of every
college hoops game 2016-27 at ESPN's close (ML / spread), the 2023-25 ML open, and - with NO look-ahead - the engine's
OLD read (own = Elo + features blended into the market by the learned trust and early_trust; raw = the raw Elo chance;
em = the Elo margin), the EFFICIENCY read (eff = sports_cbb_eff's walk-forward chance, eff_m = its margin), rest /
trips / miles / streaks / ranks / tiers / conferences, the top scorer out, the glass, the hot-ATS gap, the engine's
replayed dog points (dog_pts) and favorite read (fav_read).

THE DOG READ in these studies: the RATINGS read = the efficiency model (the 11/3 DEEP verdict: "if a raw college hoops
read is ever needed (a gap-play twin), use sports_cbb_eff, not the Elo" - the raw Elo loses 0.5552 vs 0.5294 log loss).
'Ratings-backed' = the efficiency margin has the dog the better side on this floor (eff_m > 0), the college football
gap play's rule (elo_edge >= 0).
TRAIN 2018-22, HELD OUT 2023 / 2024 / 2025 apart; the ESPN open (2023-25) is the second price."""
import importlib.util
import math
import os
import pickle
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
_spec = importlib.util.spec_from_file_location("cbbk_lib", os.path.join(ROOT, "results/studies/cbb_knowledge_b/lib.py"))
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)
CACHE = K.CACHE
TRAIN, HELD = (2018, 2022), (2023, 2024, 2025)
DOG_BAND = (100, 350)


class Out:
    def __init__(self, name):
        self.name, self.lines, self.cells = name, [], 0

    def p(self, s=""):
        self.lines.append(s)
        print(s)

    def c(self, name, rows, prof=None, note=""):
        """One cell: ROI all / train / held out, seasons up, the open's ROI where it exists."""
        self.cells += 1
        o = cell(name, rows, prof or profit_ml)
        self.p(fmt(o) + (f"  {note}" if note else ""))
        return o

    def save(self):
        self.lines.append(f"\ncells looked at: {self.cells}")
        open(os.path.join(OUT, self.name + "_out.txt"), "w").write("\n".join(self.lines) + "\n")


def dec(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def profit_ml(x):
    return (dec(x["ml"]) - 1) if x["won"] else -1.0


def profit_open(x):
    if x.get("mlo") is None:
        return None
    return (dec(x["mlo"]) - 1) if x["won"] else -1.0


def st(ps):
    ps = [p for p in ps if p is not None]
    n = len(ps)
    if not n:
        return None
    m = sum(ps) / n
    sd = math.sqrt(sum((p - m) ** 2 for p in ps) / n) if n > 1 else 0.0
    return {"n": n, "roi": m, "z": (m / (sd / math.sqrt(n))) if sd else 0.0, "w": sum(1 for p in ps if p > 0)}


def cell(name, rows, prof=profit_ml):
    bets = [(x["season"], prof(x)) for x in rows]
    bets = [(s, p) for s, p in bets if p is not None]
    if not bets:
        return {"name": name, "all": None}
    by = defaultdict(list)
    for s, p in bets:
        by[s].append(p)
    o = {"name": name, "all": st([p for _, p in bets]),
         "train": st([p for s, p in bets if TRAIN[0] <= s <= TRAIN[1]]),
         "held": st([p for s, p in bets if s in HELD]),
         "tr_up": sum(1 for s, v in by.items() if TRAIN[0] <= s <= TRAIN[1] and sum(v) > 0),
         "tr_n": sum(1 for s in by if TRAIN[0] <= s <= TRAIN[1]),
         "ho_up": sum(1 for s, v in by.items() if s in HELD and sum(v) > 0),
         "ho_n": sum(1 for s in by if s in HELD),
         "by": {s: st(v) for s, v in sorted(by.items())}}
    op = [profit_open(x) for x in rows if x["season"] in HELD]
    o["open"] = st(op)
    return o


def _s(o):
    return f"{o['roi'] * 100:+.1f}% n{o['n']} z{o['z']:+.1f}" if o else "-"


def fmt(o):
    if not o.get("all"):
        return f"{o['name']}: (none)"
    a = o["all"]
    s = f"{o['name']}: {a['w']}-{a['n'] - a['w']} {_s(a)} | train {_s(o['train'])} {o['tr_up']}/{o['tr_n']} up | held {_s(o['held'])} {o['ho_up']}/{o['ho_n']} up"
    if o.get("open"):
        s += f" | open {_s(o['open'])}"
    s += " | " + " ".join(f"{k}:{v['roi'] * 100:+.0f}" for k, v in o["by"].items())
    return s


def load():
    pk = os.path.join(CACHE, "cbb_knowledge_b_rows.pkl")
    rows = pickle.load(open(pk, "rb")) if os.path.exists(pk) else K.build()
    return rows


def regular(rows):
    return [x for x in rows if x.get("stype") == "2" and x.get("ml") is not None and x.get("p") is not None
            and x["season"] >= 2018]


def dogs(rows, lo=DOG_BAND[0], hi=DOG_BAND[1]):
    return [x for x in regular(rows) if lo <= x["ml"] <= hi]


def gap(x):
    """The efficiency read's gap over the no-vig close, in points (None = no read)."""
    return (x["eff"] - x["p"]) * 100 if x.get("eff") is not None else None


def backed(x):
    """The ratings have the dog the better side on this floor (the CFB gap play's 'Elo + home edge back the dog')."""
    return x.get("eff_m") is not None and x["eff_m"] > 0


def tier_of(x):
    return K.tier_of(x)


def band(ml):
    return K.band(ml)


def phase(x):
    return K.phase(x)


def bk(v, edges):
    return K.bk(v, edges)


def bk_labels(edges):
    return K.bk_labels(edges)


def cuts(o, name, rows, fn, labels, prof=None):
    out = {}
    byb = defaultdict(list)
    for x in rows:
        b = fn(x)
        if b is not None:
            byb[b].append(x)
    for lab in labels:
        if byb.get(lab):
            out[lab] = o.c(f"{name} | {lab}", byb[lab], prof)
    return out


def win_vs_price(rows):
    if not rows:
        return None
    n = len(rows)
    return sum(x["won"] for x in rows) / n, sum(x["p"] for x in rows) / n, n


def best_per_night(rows, key):
    """The one row a night (US night) with the biggest key(x)."""
    byn = defaultdict(list)
    for x in rows:
        byn[(x["season"], x["night"])].append(x)
    return [max(v, key=key) for v in byn.values()]
