"""S7 - WHAT IT WOULD TAKE.   python s7_what_it_takes.py nfl | ncaaf
(1) How much of our number is NEWS to each line: the weight the final score puts on (my number - the line), for the
    first fair line and for the close (0 = the line already holds everything in my number, 1 = mine is right).
(2) What LINE SHOPPING alone is worth: every side of every game at the median book vs at the best book.
(3) How much a point of closing-line value is worth: the same early bets split by how far the line then moved their
    way - and how many points our number's bets actually got.
(4) The size of the job: the win % needed at each price, and what our number hit."""
import statistics, sys
from collections import defaultdict
import numpy as np
import splib as S
import records as R

LG = sys.argv[1] if len(sys.argv) > 1 else "nfl"
o = S.Out("s7_" + LG)
recs = R.records(LG)
early = [r for r in recs if r["look"]]


def weight(xs, ys):
    x, y = np.array(xs), np.array(ys)
    b = float(x @ y / (x @ x))
    se = float(np.sqrt(((y - b * x) ** 2).sum() / (len(x) - 1) / (x @ x)))
    return b, se


o.p(f"{LG}: {len(early)} games with a first fair look")
o.p("(1) THE WEIGHT THE RESULT PUTS ON (MY NUMBER - THE LINE)")
for q in ("pP", "pA"):
    b, se = weight([r[q] + R.med_line(r["look"])[0] for r in early], [r["margin"] + R.med_line(r["look"])[0] for r in early])
    b2, se2 = weight([r[q] + r["close"] for r in early], [r["margin"] + r["close"] for r in early])
    o.p(f"   QB read {q[1]}: vs the first fair line {b:+.3f} (se {se:.3f}); vs the close {b2:+.3f} (se {se2:.3f})")
b, se = weight([R.med_line(r["look"])[0] - r["close"] for r in early], [r["margin"] + R.med_line(r["look"])[0] for r in early])
o.p(f"   and the CLOSE itself against the first fair line: {b:+.3f} (se {se:.3f}) - the week's betting is worth this much")

o.p("\n(2) LINE SHOPPING ALONE - every side of every game at the first fair look")
med, best, bestpts = [], [], []
for r in early:
    ml, dh, da = R.med_line(r["look"])
    for sd, d in (("home", dh), ("away", da)):
        med.append(R.pay(r["margin"], ml, sd, d))
        bl, bd, _ = R.best_for(r["look"], sd)
        best.append(R.pay(r["margin"], bl, sd, bd))
        bestpts.append((bl - ml) * (1 if sd == "home" else -1))
o.p(f"   median book {S.line_stats(med)}")
o.p(f"   best book   {S.line_stats(best)}   (the best book is {statistics.mean(bestpts):.2f} pts better on average; "
    f"a half point or more better {100 * sum(1 for x in bestpts if x >= 0.5) / len(bestpts):.0f}% of the time)")

o.p("\n(3) WHAT A POINT OF CLOSING-LINE VALUE IS WORTH - every side at the early median, by the line's later move its way")
cut = defaultdict(list)
for r in early:
    ml, dh, da = R.med_line(r["look"])
    for sd, d, sg in (("home", dh, 1), ("away", da, -1)):
        mv = (ml - r["close"]) * sg
        k = "against 1.5+" if mv <= -1.5 else "against 0.5-1" if mv <= -0.5 else "flat" if mv < 0.5 else "our way 0.5-1" if mv < 1.5 else "our way 1.5-2.5" if mv < 3 else "our way 3+"
        cut[k].append(R.pay(r["margin"], ml, sd, d))
for k in ("against 1.5+", "against 0.5-1", "flat", "our way 0.5-1", "our way 1.5-2.5", "our way 3+"):
    o.p(f"   {k:16s} {S.line_stats(cut[k])}")
for lo in (0, 2, 4):
    v = []
    for r in early:
        ml = R.med_line(r["look"])[0]
        e = r["pP"] + ml
        if abs(e) >= lo and e != 0:
            v.append((ml - r["close"]) * (1 if e > 0 else -1))
    o.p(f"   our number's bets (QB P, edge {lo}+): {len(v)} bets, the line moved our way {statistics.mean(v):+.2f} pts on average; "
        f"1.5+ our way {100 * sum(1 for x in v if x >= 1.5) / len(v):.0f}%, 1.5+ against {100 * sum(1 for x in v if x <= -1.5) / len(v):.0f}%")

o.p("\n(4) THE SIZE OF THE JOB")
o.p("   to break even you must win 52.4% at -110, 51.2% at -105 (a reduced-juice book), 50% at +100;")
o.p("   to make +3% on the money at -110 you must win 54.0% - 1 more game in every 62 than a coin that already pays the juice.")
o.save()
