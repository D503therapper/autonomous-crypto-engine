"""11/14 FOOTBALL - S5 COLLEGE (and NFL) TOTALS NOT YET STUDIED: the service academies, the calendar, conference vs
non-conference, the weeknight game, and a points read (both teams' season scoring) against the closing total.
Done before and NOT re-run: college weather (10/10, 10/15), altitude (11/11), NFL wind (11/11), NFL division unders
(11/1), NFL night totals (11/7 lead), early totals (11/3). One row a GAME (the home side's row), FBS vs FBS for college.
Graded at -110 both ways (the 11/12 warning: the 2024-26 archive's over / under juice can't be trusted for a cut) and,
as a check, at the game file's own juice. Train 2018-21 / held 2022-26.
Usage: python results/studies/football_1114/s5_totals.py > results/studies/football_1114/s5_out.txt"""
import flib as F
import lib

ACAD = {"2005", "2426", "349"}      # Air Force, Navy, Army
N = [0]


def tot(r, over, own=False):
    if r["total"] is None or r["pts"] == r["total"]:
        return None
    o = (r["ovo"] if over else r["uno"]) if own else None
    won = r["pts"] > r["total"] if over else r["pts"] < r["total"]
    return lib.profit(won, lib.dec(o or -110))


def c(name, rs, over, pool=None):
    N[0] += 1
    bets = [(r["season"], tot(r, over)) for r in rs if tot(r, over) is not None]
    res = lib.summ(bets, F.TRAIN, F.HELD)
    print(lib.fmt(name + (" OVER" if over else " UNDER"), res))
    own = [tot(r, over, True) for r in rs if tot(r, over, True) is not None]
    if own and res and res["all"]["n"] >= 30:
        msg = f"      at its own juice {100 * sum(own) / len(own):+.1f}%"
        if pool is not None:
            import random
            rnd = random.Random(1114)
            vals = [tot(r, over) for r in pool if tot(r, over) is not None]
            got = sum(b for _, b in bets) / len(bets)
            hit = sum(1 for _ in range(2000) if sum(rnd.sample(vals, len(bets))) / len(bets) >= got)
            msg += f"; placebo {hit} of 2000 as well"
        print(msg)
    return res


for lg in ("ncaaf", "nfl"):
    rows = [r for r in F.sides(lg) if r["side"] == "home" and r["total"] is not None]
    if lg == "ncaaf":
        rows = [r for r in rows if r["fbs"] and r["ofbs"]]
    print(f"\n=================== {lg.upper()} totals ({len(rows)} games) ===================")
    for ov in (True, False):
        c("every game", rows, ov)
    if lg == "ncaaf":
        print("-- the service academies (Army / Navy / Air Force)")
        A = [r for r in rows if r["team"] in ACAD or r["opp"] in ACAD]
        for ov in (True, False):
            c("an academy plays", A, ov, pool=rows)
        c("two academies meet", [r for r in A if r["team"] in ACAD and r["opp"] in ACAD], False)
        c("an academy vs a non-academy", [r for r in A if not (r["team"] in ACAD and r["opp"] in ACAD)], False, pool=rows)
        c("an academy plays, total under 45", [r for r in A if r["total"] < 45], False)
        c("an academy plays, total 45+", [r for r in A if r["total"] >= 45], False)
    print("-- the calendar")
    for nm, ms in (("Aug-Sep", (8, 9)), ("Oct", (10,)), ("Nov", (11,)), ("Dec-Jan", (12, 1))):
        for ov in (True, False):
            c(nm, [r for r in rows if r["month"] in ms], ov, pool=rows)
    if lg == "ncaaf":
        print("-- conference vs non-conference")
        for nm, f in (("conference game", lambda r: r["conf_game"]), ("non-conference", lambda r: not r["conf_game"])):
            for ov in (True, False):
                c(nm, [r for r in rows if f(r)], ov, pool=rows)
        c("conference game in November", [r for r in rows if r["conf_game"] and r["month"] == 11], False, pool=rows)
        print("-- the weeknight game (Tue-Fri)")
        for ov in (True, False):
            c("weeknight", [r for r in rows if r["dow"] in (1, 2, 3, 4)], ov, pool=rows)
        c("weeknight in November", [r for r in rows if r["dow"] in (1, 2, 3, 4) and r["month"] == 11], False, pool=rows)
    print("-- a points read: both teams' season scoring and allowing (4+ games) against the closing total")
    q = [r for r in rows if r["me"]["n"] >= 4 and r["op"]["n"] >= 4]

    def read(r):
        a, b = r["me"], r["op"]
        return (a["pf"] / a["n"] + b["pa"] / b["n"] + b["pf"] / b["n"] + a["pa"] / a["n"]) / 2
    for lo, hi in ((-99, -10), (-10, -6), (-6, -3), (-3, 3), (3, 6), (6, 10), (10, 99)):
        s = [r for r in q if lo <= read(r) - r["total"] < hi]
        c(f"read - total {lo}..{hi}", s, lo >= 0)
    for lo, hi in ((-99, -6), (6, 99)):
        s = [r for r in q if lo <= read(r) - r["total"] < hi]
        c(f"read - total {lo}..{hi} (the other side)", s, lo < 0)
print(f"\n{N[0]} cells - about {N[0] * 3 // 20} lines (x3 halves) would clear |z| 2 by luck.")
