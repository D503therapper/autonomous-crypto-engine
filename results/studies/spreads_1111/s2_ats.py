"""S2 (NFL) / S4 (college) - DOES THE PRO-STYLE NUMBER WIN AGAINST THE SPREAD, AND AT WHICH PRICE?
   python s2_ats.py nfl | ncaaf
A  at the CLOSE (the QB who started), by how far the number is from the line;
B  at the FIRST FAIR NUMBER of the week (the paid history: ~5 days out NFL, ~4 college, posted after both teams' last
   games) - the median book, then the BEST book for the side (most points, then price); QB read P (last game's QB -
   no look-ahead) and A; next to it what the same sides did at the closing number (timing vs the number itself);
C  does (my number - the early line) call the line's MOVE to the close? (a pro's edge even where the close is right)
D  slices of the early bets: weeks of the season, favourite / dog, home / away, the size of the spread, QB changes;
E  key numbers (3 / 7 / 10): the model's side when the best book gets it across one;
F  no model at all: line shopping (a book a point off the market) and top-down (the sharp books vs the soft ones);
G  the model and the sharp books together.
HELD OUT = the seasons the settings never saw (NFL 2020-26, college 2024-26)."""
import math, statistics, sys
from collections import defaultdict
import numpy as np
import splib as S
import records as R

LG = sys.argv[1] if len(sys.argv) > 1 else "nfl"
o = S.Out({"nfl": "s2_nfl", "ncaaf": "s4_ncaaf"}[LG])
recs = R.records(LG)
HELD = set(range(2020, 2027)) if LG == "nfl" else {2024, 2025, 2026}
SEAS = sorted({r["season"] for r in recs})
CELLS = [0]


def show(name, bets):
    """bets: [(season, profit)] -> one line: all | held out | every season's ROI (n)."""
    CELLS[0] += 1
    if not bets:
        o.p(f"  {name:46s} -")
        return
    by = defaultdict(list)
    for s, p in bets:
        by[s].append(p)
    held = [p for s, p in bets if s in HELD]
    up = sum(1 for s in by if s in HELD and sum(by[s]) > 0)
    nh = sum(1 for s in by if s in HELD)
    o.p(f"  {name:46s} ALL {S.line_stats([p for _, p in bets])} | HELD {S.line_stats(held)} up {up}/{nh} | "
        + " ".join(f"{str(s)[2:]}:{sum(by[s]) / len(by[s]) * 100:+.0f}({len(by[s])})" for s in sorted(by)))


def side_of(e):
    return "home" if e > 0 else "away"


o.p(f"{LG}: {len(recs)} regular-season games with the number and a close, seasons {SEAS[0]}-{SEAS[-1]}; "
    f"{sum(1 for r in recs if r['look'])} with a first fair look across the books")

# ---------- A: the close ----------
o.p("\nA. AT THE CLOSE (-110 both ways; QB = who started). edge = my number vs the line, in points")
for lo, hi in ((0, 99), (1, 99), (2, 99), (3, 99), (4, 99), (6, 99), (0, 1), (1, 2), (2, 3), (3, 4), (4, 6)):
    b = []
    for r in recs:
        e = r["pA"] + r["close"]
        if lo <= abs(e) < hi and e != 0:
            b.append((r["season"], R.pay(r["margin"], r["close"], side_of(e), S.dec(-110))))
    show(f"close, edge {lo}-{hi}" if hi < 99 else f"close, edge {lo}+", b)

# ---------- B: the first fair number ----------
early = [r for r in recs if r["look"]]
o.p(f"\nB. AT THE FIRST FAIR NUMBER ({len(early)} games; days before kickoff: median "
    f"{statistics.median(r['days'] for r in early):.1f})")
gap = [abs(R.med_line(r["look"])[0] - r["close"]) for r in early]
o.p("   the early median line vs the close: mean abs move %.2f pts, moved at all %.0f%%; error vs the final margin - "
    "early line MAE %.2f, close MAE %.2f, my number (P) %.2f, (A) %.2f"
    % (statistics.mean(gap), 100 * sum(1 for x in gap if x > 0) / len(gap),
       statistics.mean(abs(r["margin"] + R.med_line(r["look"])[0]) for r in early),
       statistics.mean(abs(r["margin"] + r["close"]) for r in early),
       statistics.mean(abs(r["margin"] - r["pP"]) for r in early), statistics.mean(abs(r["margin"] - r["pA"]) for r in early)))
for q in ("pP", "pA"):
    o.p(f"   --- QB read {q[1]} ---")
    for lo in (0, 1, 2, 3, 4, 6):
        med, best, cl, clv = [], [], [], []
        for r in early:
            ml, dh, da = R.med_line(r["look"])
            e = r[q] + ml
            if abs(e) < lo or e == 0:
                continue
            sd = side_of(e)
            med.append((r["season"], R.pay(r["margin"], ml, sd, dh if sd == "home" else da)))
            bl, bd, _ = R.best_for(r["look"], sd)
            best.append((r["season"], R.pay(r["margin"], bl, sd, bd)))
            cl.append((r["season"], R.pay(r["margin"], r["close"], sd, S.dec(-110))))
            clv.append((ml - r["close"]) * (1 if sd == "home" else -1))
        show(f"early median book, edge {lo}+", med)
        show(f"early BEST book, edge {lo}+", best)
        show(f"  the same sides at the CLOSE, edge {lo}+", cl)
        if clv:
            o.p(f"      the line moved OUR way by {statistics.mean(clv):+.2f} pts on average; our way {100 * sum(1 for x in clv if x > 0) / len(clv):.0f}% / "
                f"against {100 * sum(1 for x in clv if x < 0) / len(clv):.0f}% / flat {100 * sum(1 for x in clv if x == 0) / len(clv):.0f}%")

# ---------- C: does the gap call the move? ----------
o.p("\nC. DOES (MY NUMBER - THE EARLY LINE) CALL THE LINE'S MOVE TO THE CLOSE?")
for q in ("pP", "pA"):
    for nm, ss in (("all", SEAS), ("held", sorted(HELD))):
        x = np.array([r[q] + R.med_line(r["look"])[0] for r in early if r["season"] in ss])
        y = np.array([R.med_line(r["look"])[0] - r["close"] for r in early if r["season"] in ss])   # + = moved toward home
        if len(x) < 30:
            continue
        b = float(x @ y / (x @ x))
        se = float(np.sqrt(((y - b * x) ** 2).sum() / (len(x) - 1) / (x @ x)))
        o.p(f"   QB {q[1]} {nm:5s} n {len(x):4d}: move = {b:+.3f} x gap (se {se:.3f}, t {b / se:+.1f}), corr {np.corrcoef(x, y)[0, 1]:+.3f}")

# ---------- D: slices ----------
o.p("\nD. SLICES - the early BEST book, QB read P (edge 0+ and 2+)")


def cut(name, cond):
    for lo in (0, 2):
        b = []
        for r in early:
            ml = R.med_line(r["look"])[0]
            e = r["pP"] + ml
            if abs(e) < lo or e == 0:
                continue
            sd = side_of(e)
            if not cond(r, sd, ml):
                continue
            bl, bd, _ = R.best_for(r["look"], sd)
            b.append((r["season"], R.pay(r["margin"], bl, sd, bd)))
        show(f"{name}, edge {lo}+", b)


cut("weeks 1-4", lambda r, sd, ml: r["wkn"] <= 4)
cut("weeks 5-9", lambda r, sd, ml: 5 <= r["wkn"] <= 9)
cut("weeks 10+", lambda r, sd, ml: r["wkn"] >= 10)
cut("our side the favourite", lambda r, sd, ml: (ml < 0) == (sd == "home") and ml != 0)
cut("our side the dog", lambda r, sd, ml: (ml > 0) == (sd == "home") and ml != 0)
cut("our side at home", lambda r, sd, ml: sd == "home")
cut("our side on the road", lambda r, sd, ml: sd == "away")
cut("spread 0-3", lambda r, sd, ml: abs(ml) <= 3)
cut("spread 3.5-7", lambda r, sd, ml: 3 < abs(ml) <= 7)
cut("spread 7.5-14", lambda r, sd, ml: 7 < abs(ml) <= 14)
cut("spread 14.5+", lambda r, sd, ml: abs(ml) > 14)
cut("a QB change (either team)", lambda r, sd, ml: r["qbchg"] > 0)
cut("no QB change", lambda r, sd, ml: r["qbchg"] == 0)

# ---------- E: key numbers ----------
o.p("\nE. KEY NUMBERS - the model's side (QB P, any edge) when the best book gets it across a key number")
KEYS = (3, 7, 10) if LG == "nfl" else (3, 7, 10, 14)
for k in KEYS:
    hook, flat = [], []
    for r in early:
        ml = R.med_line(r["look"])[0]
        e = r["pP"] + ml
        if e == 0:
            continue
        sd = side_of(e)
        mine = ml if sd == "home" else -ml             # our side's median number
        bl, bd, _ = R.best_for(r["look"], sd)
        bmine = bl if sd == "home" else -bl
        # a dog getting +k.5 when the market is +k (or +k when it is +k-.5); a favourite laying -(k-.5) / -k
        if bmine > mine and ((mine <= k <= bmine and mine < bmine) or (mine <= -k <= bmine)):
            hook.append((r["season"], R.pay(r["margin"], bl, sd, bd)))
        if abs(mine) == k:
            flat.append((r["season"], R.pay(r["margin"], ml, sd, S.dec(-110))))
    show(f"best book crosses / lands on {k}", hook)
    show(f"  market sits on {k}, bet at the median", flat)

# ---------- F: no model ----------
o.p("\nF. NO MODEL - LINE SHOPPING AND TOP-DOWN at the first fair look")
for thr in (0.5, 1.0, 1.5):
    b = []
    for r in early:
        ml = R.med_line(r["look"])[0]
        for sd in ("home", "away"):
            bl, bd, _ = R.best_for(r["look"], sd)
            if (bl - ml) * (1 if sd == "home" else -1) >= thr:
                b.append((r["season"], R.pay(r["margin"], bl, sd, bd)))
    show(f"a book {thr}+ pts better than the median", b)
both = [r for r in early if any(k in r["look"] for k in R.SHARP) and sum(1 for k in r["look"] if k in R.SOFT) >= 3]
o.p(f"   {len(both)} games with a sharp book (Circa / LowVig / BetOnline / Bookmaker) and 3+ soft books in the look")
for thr in (0.5, 1.0):
    bs, bm, bc = [], [], []
    for r in both:
        sh = statistics.median(v[0] for k, v in r["look"].items() if k in R.SHARP)
        so = statistics.median(v[0] for k, v in r["look"].items() if k in R.SOFT)
        if abs(sh - so) < thr:
            continue
        sd = "home" if sh < so else "away"           # the sharp books make this side the bigger favourite / smaller dog
        bl, bd, _ = R.best_for(r["look"], sd, R.SOFT)
        bs.append((r["season"], R.pay(r["margin"], bl, sd, bd)))
        bm.append((r["season"], R.pay(r["margin"], so, sd, S.dec(-110))))
        bc.append((so - r["close"]) * (1 if sd == "home" else -1))
    show(f"sharp side, {thr}+ apart, best SOFT book", bs)
    show(f"sharp side, {thr}+ apart, soft median -110", bm)
    if bc:
        o.p(f"      the close moved the sharp side's way by {statistics.mean(bc):+.2f} pts on average")

# ---------- G: the model + the sharp books ----------
o.p("\nG. THE MODEL (QB P) AND THE SHARP BOOKS TOGETHER - best soft book")
for lo in (1, 2, 3):
    ag, dis = [], []
    for r in both:
        sh = statistics.median(v[0] for k, v in r["look"].items() if k in R.SHARP)
        so = statistics.median(v[0] for k, v in r["look"].items() if k in R.SOFT)
        e = r["pP"] + so
        if abs(e) < lo:
            continue
        sd = side_of(e)
        bl, bd, _ = R.best_for(r["look"], sd, R.SOFT)
        p = (r["season"], R.pay(r["margin"], bl, sd, bd))
        lean = (so - sh) * (1 if sd == "home" else -1)       # + = the sharp books lean our side
        if lean > 0:
            ag.append(p)
        elif lean < 0:
            dis.append(p)
    show(f"model edge {lo}+, sharp books lean WITH it", ag)
    show(f"model edge {lo}+, sharp books lean AGAINST", dis)
o.p(f"\ncells graded: {CELLS[0]} (about {CELLS[0] * 0.05:.0f} would clear |z| 2 by luck)")
o.save()
