"""S9 - THE ONE COLLEGE SLICE THAT SHOWED GREEN, PUT THROUGH THE FIVE CHECKS: the model's side in games with a spread of
14.5+ (S4-D: +3.7% on 533 at the early best book, held out +8.2%, 3 of 3) and its cousin 'my number 6+ off the early
line' (+3.0% on 715). One of 92 cells - so: (1) the dose (edge size), (2) every season, (3) a second price (the
median book, the close - and the close on EVERY game 2023-26, not only the ones with an early look), (4) which side
it is (the big favourite or the big dog) and whether the blind side alone does the same, (5) the neighbours (10.5-14,
14.5-20.5, 21+)."""
from collections import defaultdict
import splib as S
import records as R

o = S.Out("s9")
recs = R.records("ncaaf")
early = [r for r in recs if r["look"]]
HELD = {2024, 2025, 2026}


def show(name, bets):
    if not bets:
        o.p(f"  {name:58s} -")
        return
    by = defaultdict(list)
    for s, p in bets:
        by[s].append(p)
    held = [p for s, p in bets if s in HELD]
    o.p(f"  {name:58s} ALL {S.line_stats([p for _, p in bets])} | HELD {S.line_stats(held)} | "
        + " ".join(f"{str(s)[2:]}:{sum(by[s]) / len(by[s]) * 100:+.0f}({len(by[s])})" for s in sorted(by)))


def bets(rows, q, price, lo_sp, hi_sp, lo_e=0, hi_e=99, side=None, blind=None):
    out = []
    for r in rows:
        ml = R.med_line(r["look"])[0] if price != "closeall" else r["close"]
        if not (lo_sp <= abs(ml) < hi_sp):
            continue
        e = r[q] + ml
        if blind:
            sd = ("home" if ml < 0 else "away") if blind == "fav" else ("home" if ml > 0 else "away")
        else:
            if not (lo_e <= abs(e) < hi_e) or e == 0:
                continue
            sd = "home" if e > 0 else "away"
        isfav = (ml < 0) == (sd == "home")
        if side == "fav" and not isfav or side == "dog" and isfav:
            continue
        if price == "best":
            bl, bd, _ = R.best_for(r["look"], sd)
            out.append((r["season"], R.pay(r["margin"], bl, sd, bd)))
        elif price == "median":
            _, dh, da = R.med_line(r["look"])
            out.append((r["season"], R.pay(r["margin"], ml, sd, dh if sd == "home" else da)))
        else:
            out.append((r["season"], R.pay(r["margin"], r["close"], sd, S.dec(-110))))
    return out


o.p("(1) THE DOSE - spread 14.5+, QB read P, the early best book, by the size of the edge")
for lo, hi in ((0, 2), (2, 4), (4, 6), (6, 9), (9, 99)):
    show(f"edge {lo}-{hi}", bets(early, "pP", "best", 14.5, 99, lo, hi))
o.p("(3) A SECOND PRICE - the same bets (edge 2+)")
show("early best book", bets(early, "pP", "best", 14.5, 99, 2))
show("early median book", bets(early, "pP", "median", 14.5, 99, 2))
show("the same sides at the close", bets(early, "pP", "close", 14.5, 99, 2))
show("AT THE CLOSE, every game 2023-26 (QB A), edge 2+", bets(recs, "pA", "closeall", 14.5, 99, 2))
show("AT THE CLOSE, every game 2023-26 (QB A), edge 6+", bets(recs, "pA", "closeall", 14.5, 99, 6))
o.p("(4) WHICH SIDE - spread 14.5+, early best book")
show("the model's side is the big favourite, edge 2+", bets(early, "pP", "best", 14.5, 99, 2, side="fav"))
show("the model's side is the big dog, edge 2+", bets(early, "pP", "best", 14.5, 99, 2, side="dog"))
show("BLIND: every big favourite (no model)", bets(early, "pP", "best", 14.5, 99, blind="fav"))
show("BLIND: every big dog (no model)", bets(early, "pP", "best", 14.5, 99, blind="dog"))
show("BLIND at the close, every game: big favourite", bets(recs, "pA", "closeall", 14.5, 99, blind="fav"))
show("BLIND at the close, every game: big dog", bets(recs, "pA", "closeall", 14.5, 99, blind="dog"))
o.p("(5) THE NEIGHBOURS - the model's side, edge 2+, early best book")
for lo, hi in ((7.5, 10.5), (10.5, 14.5), (14.5, 21), (21, 28.5), (28.5, 99)):
    show(f"spread {lo}-{hi}", bets(early, "pP", "best", lo, hi, 2))
o.p("AND 'MY NUMBER 6+ OFF THE EARLY LINE' (any spread), early best book - by the spread")
for lo, hi in ((0, 7.5), (7.5, 14.5), (14.5, 99)):
    show(f"edge 6+, spread {lo}-{hi}", bets(early, "pP", "best", lo, hi, 6))
o.save()
