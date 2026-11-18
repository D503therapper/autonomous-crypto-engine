"""11/18 follow-up B2 - THE NHL DOG OFF A CHEAP WIN, the cut that would be wired: the dog's last game this season was a
WIN over a team under .450 (8+ games, its record BEFORE that game). Against dogs off ANY win (the engine already gives a
dog off a LOSS +3 - lost_last), with the overlaps the engine already weighs taken out one at a time: the hot dog (a 3+
game win streak, -2 built), the dog on a back-to-back (rested_vs_b2b / tired_vs_rested built), the long dog (+220, -3
built). Every season apart, ESPN's open (2023-26) and the paid morning (2021-23) as the second prices, a price-matched
placebo, and the NBA / college hoops twins (the same cut) as the second sport."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from h import Out  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("s", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s1_s10.py"))
S = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], "none"]
spec.loader.exec_module(S)
spec2 = importlib.util.spec_from_file_location("f", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s_followups.py"))
os.environ["WHICH"] = "none"
F = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(F)

o = Out("fB2_cheap_win_dog", S.TRAIN, S.HELD)
for lg in ("nhl", "nba", "ncaab"):
    mo = lib.nhl_morning() if lg == "nhl" else (lib.nba_morning() if lg == "nba" else {})
    streak, lastday = {}, {}
    pool_any, pool_all = [], []
    for g, raw, st in S.walk(lg):
        s = g["season"]
        for side, t, opp in S.sides(g):
            r = st[(s, t)]
            od, pr = S.ml(g, side)
            if S.band(od) != "dog" or r["gp"] < 8 or not r["last"] or r["last"]["opp_wp"] is None:
                continue
            won = (g["hs"] > g["as"]) == (side == "home")
            L = r["last"]
            k = (s, t)
            stk = streak.get(k, 0)
            b2b = k in lastday and lib.days_between(lastday[k], g["start"]) < 1.6
            pool_all.append((s, pr, od))
            if L["margin"] <= 0:
                continue
            pool_any.append((s, pr, od))
            o.add(f"{lg} dog off ANY win", s, pr, od)
            if L["opp_wp"] >= 0.45:
                o.add(f"{lg} dog off a win over .450+", s, pr, od)
                if stk < 3 and not b2b and od < 220:
                    o.add(f"{lg} dog off a win over .450+ none of the built", s, pr, od)
                continue
            nm = f"{lg} CHEAP WIN (over a sub-.450 team)"
            o.add(f"{nm} ALL", s, pr, od)
            if stk < 3:
                o.add(f"{nm} not on a 3+ streak", s, pr, od)
            if not b2b:
                o.add(f"{nm} rested", s, pr, od)
            if od < 220:
                o.add(f"{nm} under +220", s, pr, od)
            if stk < 3 and not b2b and od < 220:
                o.add(f"{nm} none of the built (no 3+ streak, rested, under +220)", s, pr, od)
                op = g["oh"] if side == "home" else g["oa"]
                if op and 100 <= op <= 400:
                    o.add(f"{nm} none of the built @ESPN open", s, lib.profit(won, lib.dec(op)), od)
                m = mo.get(g["id"])
                if m and m.get("dh"):
                    o.add(f"{nm} none of the built @morning", s, lib.profit(won, m["dh"] if side == "home" else m["da"]), od)
            if lg == "nhl":
                o.add(f"{nm} {'home' if side == 'home' else 'road'}", s, pr, od)
        # update the streak / last day AFTER the yield (the walk updates its own state after this loop)
        for side, t, opp in S.sides(g):
            k = (g["season"], t)
            w = (g["hs"] > g["as"]) == (side == "home")
            streak[k] = (streak.get(k, 0) + 1) if w else 0
            lastday[k] = g["start"]
    o.p(f"--- {lg}")
    o.show(prefix=lg, minn=20)
    for cell in (f"{lg} CHEAP WIN (over a sub-.450 team) ALL",
                 f"{lg} CHEAP WIN (over a sub-.450 team) none of the built (no 3+ streak, rested, under +220)"):
        if cell in o.c:
            o.p("  vs dogs off ANY win:")
            F.matched_placebo(o, cell, pool_any)
            o.p("  vs every dog:")
            F.matched_placebo(o, cell, pool_all)
o.save()
