"""Follow-up A (S9's one cell past |z| 3) - THE NHL DOG OFF A WIRE-TO-WIRE WIN vs A TEAM THAT NEVER LED AND LOST:
-19.4% on 314 at the close, 0 of 9 seasons up. Is it new, or the built weights again (the hot dog 3+ streak -2, the
dog on a back-to-back, the long dog +220, the 11/18 cheap-win lead)? Price-matched placebo (50-cent bins), the built
cells taken out, ESPN's open and the paid morning as second prices, the dose (either half of the pair alone)."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h
import lib

o = h.Out("fA_nhl_wire_dog", (2016, 2021), tuple(range(2022, 2027)))
o.p(__doc__)
fin = [g for g in lib.finals("nhl") if g["stype"] == "2"]
mo = lib.nhl_morning()
last, streak = {}, {}
rows = []
for g in fin:
    for side, tm, opp, od, won, is_home in lib.sides(g):
        pv, opv = last.get((tm, g["season"])), last.get((opp, g["season"]))
        if pv and 100 <= od <= 350 and lib.days_between(pv[0], g["start"]) <= 10:
            b2b = lib.days_between(pv[0], g["start"]) < 1.6
            oin = opv and lib.days_between(opv[0], g["start"]) <= 10
            rows.append({"g": g, "s": g["season"], "od": od, "p": lib.profit(won, lib.dec(od)), "mine": pv[1],
                         "his": opv[1] if oin else None, "b2b": b2b, "hot": streak.get((tm, g["season"]), 0) >= 3,
                         "side": side, "won": won,
                         "open": (g["oh"] if side == "home" else g["oa"])})
    qh, qa = lib.quarters(g["ls_h"]), lib.quarters(g["ls_a"])
    st = {g["home"]: None, g["away"]: None}
    if qh and qa and len(qh) >= 3 and len(qa) >= 3:
        l1, l2 = qh[0] - qa[0], qh[0] + qh[1] - qa[0] - qa[1]
        hw = g["hs"] > g["as"]
        if l1 > 0 and l2 > 0 and hw:
            st[g["home"]], st[g["away"]] = "W", "L"
        elif l1 < 0 and l2 < 0 and not hw:
            st[g["away"]], st[g["home"]] = "W", "L"
    hw = g["hs"] > g["as"]
    for tm, w in ((g["home"], hw), (g["away"], not hw)):
        last[(tm, g["season"])] = (g["start"], st[tm])
        streak[(tm, g["season"])] = streak.get((tm, g["season"]), 0) + 1 if w else 0

for r in rows:
    o.add("A0 every dog with a last game", r["s"], r["p"], r["od"])
    if r["mine"] == "W":
        o.add("A1 dog off a wire-to-wire win", r["s"], r["p"], r["od"])
    if r["his"] == "L":
        o.add("A2 dog vs a team that never led and lost", r["s"], r["p"], r["od"])
    if r["mine"] == "W" and r["his"] == "L":
        o.add("B THE PAIR", r["s"], r["p"], r["od"])
        clean = not r["hot"] and not r["b2b"] and r["od"] < 220
        o.add("B1 the pair, built cells out (no 3+ streak, rested, under +220)" if clean else "B2 the pair, inside a built cell", r["s"], r["p"], r["od"])
        if r["open"] and 100 <= r["open"] <= 350:
            o.add("B3 the pair at ESPN's open (2023-26)", r["s"], lib.profit(r["won"], lib.dec(r["open"])), r["open"])
        ms = lib.morning_side(mo, r["g"]["id"], r["side"])
        if ms and 100 <= ms[0] <= 350:
            o.add("B4 the pair at the paid morning (2021-23)", r["s"], lib.profit(r["won"], ms[1]), ms[0])
    if r["mine"] == "W" and r["his"] != "L":
        o.add("C1 off a wire win, the other side NOT off a never-led loss", r["s"], r["p"], r["od"])
    if r["mine"] != "W" and r["his"] == "L":
        o.add("C2 vs a never-led loser, the dog NOT off a wire win", r["s"], r["p"], r["od"])
    if not r["hot"] and not r["b2b"] and r["od"] < 220:
        o.add("A0c every dog, built cells out", r["s"], r["p"], r["od"])
o.show()


def matched(name, pool_name, n=2000, seed=11):
    """A placebo matched on the price: each row of the cell swapped for a random row of the pool in its 50-cent bin."""
    cellr, pool = o.c[name], o.c[pool_name]
    bins = {}
    for s, p, od in pool:
        bins.setdefault(int(od // 50), []).append(p)
    got = sum(p for _, p, _ in cellr) / len(cellr)
    rnd = random.Random(seed)
    hit = 0
    for _ in range(n):
        tot = sum(rnd.choice(bins[int(od // 50)]) for _, _, od in cellr)
        hit += tot / len(cellr) <= got
    o.p(f"  price-matched placebo {name}: {hit} of {n} random same-price sets did as badly (cell {got * 100:+.1f}%)")


matched("B THE PAIR", "A0 every dog with a last game")
matched("B1 the pair, built cells out (no 3+ streak, rested, under +220)", "A0c every dog, built cells out")
o.save()
