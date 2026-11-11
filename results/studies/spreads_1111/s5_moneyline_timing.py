"""S5 - THE SAME NUMBER ON THE MONEYLINE, AT EVERY TIME WE HOLD (the paid history has spreads only early in the week,
but moneylines at the first fair look, the GAME MORNING and - from the game files - the close).
   python s5_moneyline_timing.py nfl | ncaaf
The model's margin -> a win chance (a normal curve, sd 13.3 NFL / 16.5 college); edge = that minus the books' no-vig
chance; a bet on the side with an edge of 3 / 6 / 10 points, 1 unit flat, at the median price and at the BEST book.
QB read P at the first fair look, A (who started - known by then) on game morning and at the close."""
import math, statistics, sys
from collections import defaultdict
import splib as S
import records as R

LG = sys.argv[1] if len(sys.argv) > 1 else "nfl"
o = S.Out("s5_" + LG)
B = S.B
recs = [r for r in R.records(LG) if r.get("fb")]
HELD = set(range(2020, 2027)) if LG == "nfl" else {2024, 2025, 2026}
SD = 13.3 if LG == "nfl" else 16.5
CELLS = [0]


def show(name, bets):
    CELLS[0] += 1
    if not bets:
        o.p(f"  {name:50s} -")
        return
    by = defaultdict(list)
    for s, p in bets:
        by[s].append(p)
    held = [p for s, p in bets if s in HELD]
    up = sum(1 for s in by if s in HELD and sum(by[s]) > 0)
    o.p(f"  {name:50s} ALL {S.line_stats([p for _, p in bets])} | HELD {S.line_stats(held)} up {up}/{sum(1 for s in by if s in HELD)} | "
        + " ".join(f"{str(s)[2:]}:{sum(by[s]) / len(by[s]) * 100:+.0f}({len(by[s])})" for s in sorted(by)))


def pwin(m):
    return 0.5 * (1 + math.erf(m / SD / math.sqrt(2)))


def run(tag, q, pick):
    o.p(f"\n{tag} (QB read {q[1]})")
    n = 0
    for band, ok in (("any price", lambda d: True), ("dogs +100..+350", lambda d: 2.0 <= d <= 4.5),
                     ("favourites to -150", lambda d: 1.667 <= d < 2.0), ("favourites past -150", lambda d: d < 1.667)):
        for thr in (0.03, 0.06, 0.10):
            med, best = [], []
            for r in recs:
                bk = pick(r)
                if not bk:
                    continue
                n += 1
                hd = statistics.median(S.dec(v[0]) for v in bk.values())
                ad = statistics.median(S.dec(v[1]) for v in bk.values())
                ph = (1 / hd) / (1 / hd + 1 / ad)
                e = pwin(r[q]) - ph
                if abs(e) < thr:
                    continue
                home = e > 0
                d = hd if home else ad
                if not ok(d):
                    continue
                won = (r["margin"] > 0) == home
                if r["margin"] == 0:
                    continue
                bd = max(S.dec(v[0] if home else v[1]) for v in bk.values())
                med.append((r["season"], (d - 1) if won else -1.0))
                best.append((r["season"], (bd - 1) if won else -1.0))
            show(f"{band}, edge {int(thr * 100)}+ pts, median price", med)
            show(f"{band}, edge {int(thr * 100)}+ pts, BEST book", best)


def first(r):
    x = B.first_fair(r["fb"]["ml"])
    return x[1] if x else None


def morning(r):
    x = B.last_look(r["fb"]["ml"])
    return x[1] if x and x[0] <= 0.75 else None


def close(r):
    f = r["fb"]
    if f["c_mlh"] is None or f["c_mla"] is None or f["c_mlh"] == 0 or f["c_mla"] == 0:
        return None
    return {"close": (f["c_mlh"], f["c_mla"])}


o.p(f"{LG}: {len(recs)} games with the number and a paid-history row; a first fair moneyline look "
    f"{sum(1 for r in recs if first(r))}, a game-morning look (inside 18 hours) {sum(1 for r in recs if morning(r))}, "
    f"a closing moneyline {sum(1 for r in recs if close(r))}")
run("FIRST FAIR LOOK of the week", "pP", first)
run("GAME MORNING (the last look inside 18 hours of kickoff)", "pA", morning)
run("THE CLOSE (one book - the game file)", "pA", close)
o.p(f"\ncells graded: {CELLS[0]} (about {CELLS[0] * 0.05:.0f} would clear |z| 2 by luck)")
o.save()
