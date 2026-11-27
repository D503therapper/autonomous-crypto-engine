"""11/27 daily studies - the controls on the cells that stood out in s_today.py (fixed after the first pass, every one
written down before it ran): the dose, every season apart, PRICE-MATCHED placebos (the same number of sides out of
each 50-cent price bin of the cell's own pool), ESPN's open (2023-26), the cell's OWN base (a neutral floor's sides
against neutral-floor sides), and whether a built read already says it.
  s1   NHL: the small favorite CARRIED by its top line / the dog whose top pair is winning its minutes
  s2   college hoops: beat up on the glass in the last game, on a NEUTRAL floor, against the spread
  s9   college hoops: the dog off a HOT NIGHT from three
python results/studies/daily_1127/s_follow.py [s1 s2 s9]"""
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import s_today as st  # noqa: E402
from core import teambox, BT, BH  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


class Rep:
    def __init__(self, tag, train, held):
        self.tag, self.train, self.held, self.lines = tag, train, held, []

    def p(self, *a):
        s = " ".join(str(x) for x in a)
        print(s, flush=True)
        self.lines.append(s)

    def row(self, name, rows):
        """rows: [(season, profit, american odds)]"""
        r = lib.summ([(s, p) for s, p, _ in rows if p is not None], self.train, self.held)
        self.p(lib.fmt(name, r))
        return r

    def matched(self, name, rows, pool, fade, n=2000, seed=11, price=True):
        """Placebo: random same-size sets from `pool` - the same count out of each 50-cent price bin when price=True."""
        rows = [r for r in rows if r[1] is not None]
        pool = [r for r in pool if r[1] is not None]
        if not rows or len(pool) < len(rows):
            return None

        def b(o):
            return int(o // 50) if price else 0
        need, byb = defaultdict(int), defaultdict(list)
        for _, _, o in rows:
            need[b(o)] += 1
        for _, p, o in pool:
            byb[b(o)].append(p)
        got = sum(p for _, p, _ in rows) / len(rows)
        rnd = random.Random(seed)
        hit = 0
        for _ in range(n):
            tot = 0.0
            for k, c in need.items():
                tot += sum(rnd.sample(byb[k], c)) if len(byb[k]) >= c else sum(rnd.choices(byb[k], k=c))
            v = tot / len(rows)
            hit += (v <= got) if fade else (v >= got)
        pm = sum(p for _, p, _ in pool) / len(pool)
        self.p(f"  {'price-matched ' if price else ''}placebo {name}: {hit} of {n} random sets did as {'badly' if fade else 'well'}"
               f" (cell {got*100:+.1f}% on {len(rows)}, pool {pm*100:+.1f}% on {len(pool)})")
        return hit

    def save(self):
        open(os.path.join(HERE, self.tag + "_out.txt"), "w").write("\n".join(self.lines) + "\n")


def side_rows(fin, rk, need_both=True):
    """One row a priced side: (g, side, me, them, american odds, ML profit, ATS profit, open odds)."""
    out = []
    for g in fin:
        a, b = rk.get((g["id"], g["home"])), rk.get((g["id"], g["away"]))
        if need_both and (not a or not b):
            continue
        for side, team, opp, o, won, _ in lib.sides(g):
            me, th = (a, b) if side == "home" else (b, a)
            op = g["oh"] if side == "home" else g["oa"]
            out.append({"g": g, "side": side, "me": me, "th": th, "o": o, "pr": lib.profit(won, lib.dec(o)), "at": lib.ats(g, side),
                        "op": op, "opr": lib.profit(won, lib.dec(op)) if op else None, "s": g["season"]})
    return out


def ml(rows, key="pr"):
    return [(r["s"], r[key], r["o"]) for r in rows]


def s1():
    fin, rk = st.s1(ret=True)
    R = Rep("s1b_nhl_top_line_controls", BT, BH)
    rows = side_rows(fin, rk)
    R.p("S1b - NHL, THE TOP LINE'S PLUS-MINUS - the controls")
    fav = [r for r in rows if -150 <= r["o"] <= -101]
    dog = [r for r in rows if 100 <= r["o"] <= 350]
    R.p("THE SMALL FAVORITE -150..-101 by its CARRIED fifth (the top line's plus-minus minus the other forwards'):")
    for lo_, hi_ in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
        R.row(f"  carried fifth {lo_:.1f}-{min(hi_, 1):.1f}", ml([r for r in fav if lo_ <= r["me"]["carry"][1] < hi_]))
    cell = [r for r in fav if r["me"]["carry"][1] >= .8]
    R.row("  top tenth", ml([r for r in fav if r["me"]["carry"][1] >= .9]))
    R.row("  top fifth, at home", ml([r for r in cell if r["side"] == "home"]))
    R.row("  top fifth, on the road", ml([r for r in cell if r["side"] == "away"]))
    R.row("  top fifth AND its top line winning (top fifth f)", ml([r for r in cell if r["me"]["f"][1] >= .8]))
    R.row("  top fifth, its top line NOT in the top fifth", ml([r for r in cell if r["me"]["f"][1] < .8]))
    R.row("  top fifth at ESPN's OPEN (-150..-101 there)", [(r["s"], r["opr"], r["op"]) for r in rows if r["op"] and -150 <= r["op"] <= -101 and r["me"]["carry"][1] >= .8])
    R.row("  every small favorite at ESPN's open", [(r["s"], r["opr"], r["op"]) for r in rows if r["op"] and -150 <= r["op"] <= -101])
    R.row("  the dog across a carried small favorite", ml([r for r in dog if r["th"]["carry"][1] >= .8 and -150 <= -100 * 0 + (r["g"]["mlh"] if r["side"] == "away" else r["g"]["mla"]) <= -101]))
    R.row("  every small favorite", ml(fav))
    R.matched("the carried small favorite", ml(cell), ml(fav), True)
    R.p("THE DOG +100..+350 by its TOP PAIR's fifth (the top two defensemen's plus-minus a game, last 10):")
    for lo_, hi_ in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
        R.row(f"  top-pair fifth {lo_:.1f}-{min(hi_, 1):.1f}", ml([r for r in dog if lo_ <= r["me"]["d"][1] < hi_]))
    cell = [r for r in dog if r["me"]["d"][1] >= .8]
    R.row("  top fifth at ESPN's OPEN (+100..+350 there)", [(r["s"], r["opr"], r["op"]) for r in rows if r["op"] and 100 <= r["op"] <= 350 and r["me"]["d"][1] >= .8])
    R.row("  every dog at ESPN's open", [(r["s"], r["opr"], r["op"]) for r in rows if r["op"] and 100 <= r["op"] <= 350])
    R.row("  top fifth, +100..+150", ml([r for r in cell if r["o"] <= 150]))
    R.row("  top fifth, +151..+350", ml([r for r in cell if r["o"] > 150]))
    R.row("  every dog", ml(dog))
    R.matched("the dog with a top-fifth top pair", ml(cell), ml(dog), True)
    R.save()


def s2():
    fin, rk = st.s2(ret=True)
    R = Rep("s2b_ncaab_glass_controls", BT, BH)
    rows = [r for r in side_rows(fin, rk, need_both=False) if r["me"]]
    R.p("S2b - COLLEGE HOOPS, BEAT UP ON THE GLASS LAST GAME - the controls (the cell's own base: NEUTRAL-floor sides with a")
    R.p("  last-game D1 box inside 8 days)")
    for site in ("neutral", "home", "road"):
        pool = [r for r in rows if st.where(r["g"], r["side"]) == site]
        R.p(f"ON A {site.upper()} FLOOR, against the spread, by the last game's rebound margin:")
        for name, f in (("-18 or worse", lambda v: v <= -18), ("-12..-17", lambda v: -17 <= v <= -12), ("-6..-11", lambda v: -11 <= v <= -6),
                        ("-5..+5", lambda v: -5 <= v <= 5), ("+6..+11", lambda v: 6 <= v <= 11), ("+12 or more", lambda v: v >= 12)):
            R.row(f"  {name}", ml([r for r in pool if f(r["me"]["gap"])], "at"))
        R.row(f"  every {site} side with a last-game box", ml(pool, "at"))
    neu = [r for r in rows if r["g"]["neutral"]]
    cell = [r for r in neu if r["me"]["gap"] <= -12]
    R.row("neutral, -12 or worse, back within 2 days", ml([r for r in cell if r["me"]["days"] <= 2.5], "at"))
    R.row("neutral, every side back within 2 days", ml([r for r in neu if r["me"]["days"] <= 2.5], "at"))
    R.row("neutral, -12 or worse, 3+ days later", ml([r for r in cell if r["me"]["days"] > 2.5], "at"))
    R.row("neutral, -12 or worse, LOST that game", ml([r for r in cell if not r["me"]["won"]], "at"))
    R.row("neutral, every side that LOST its last game", ml([r for r in neu if not r["me"]["won"]], "at"))
    R.row("neutral, -12 or worse, WON that game", ml([r for r in cell if r["me"]["won"]], "at"))
    R.row("neutral, the side ACROSS a -12 team (itself not one)", ml([r for r in neu if r["th"] and r["th"]["gap"] <= -12 and r["me"]["gap"] > -12], "at"))
    R.matched("neutral, -12 or worse (against neutral sides)", ml(cell, "at"), ml(neu, "at"), True, price=False)
    R.matched("neutral, -12 or worse and lost (against neutral sides that lost)", ml([r for r in cell if not r["me"]["won"]], "at"),
              ml([r for r in neu if not r["me"]["won"]], "at"), True, price=False)
    R.save()


def s9():
    fin, rk = st.threes("ncaab", "", "", 14, 18, d1_only=True, ret=True)
    # the team's season three-point shooting BEFORE tonight (every boxed game) - is a hot night just a shooting team?
    tb = teambox("ncaab")
    allf = [g for g in lib.all_finals("ncaab") if g["season"] >= 2021]
    acc, seas3 = defaultdict(lambda: [0.0, 0.0]), {}
    for g in allf:
        for t in (g["home"], g["away"]):
            a = acc[(g["season"], t)]
            if a[1] >= 60:
                seas3[(g["id"], t)] = a[0] / a[1]
        for t in (g["home"], g["away"]):
            x = st.pair(((tb.get(g["id"]) or {}).get(str(t)) or {}).get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
            if x:
                acc[(g["season"], t)][0] += x[0]
                acc[(g["season"], t)][1] += x[1]
    R = Rep("s9b_ncaab_hot_night_controls", BT, BH)
    rows = [r for r in side_rows(fin, rk, need_both=False) if r["me"]]
    dog = [r for r in rows if 100 <= r["o"] <= 350]

    def pct(r):
        return r["me"]["m"] / r["me"]["a"] if r["me"]["a"] >= 18 else None
    R.p("S9b - COLLEGE HOOPS, THE DOG OFF A HOT NIGHT FROM THREE - the controls")
    R.p("THE DOG +100..+350 by its last game's three-point % (18+ attempts, D1 game, within 8 days):")
    for lo_, hi_ in ((0, .22), (.22, .30), (.30, .40), (.40, .50), (.50, .60), (.60, 1.01)):
        R.row(f"  {lo_*100:.0f}%-{min(hi_, 1)*100:.0f}%", ml([r for r in dog if pct(r) is not None and lo_ <= pct(r) < hi_]))
    cell = [r for r in dog if pct(r) is not None and pct(r) >= .5]
    for site in ("home", "road", "neutral"):
        R.row(f"  hot night, {site}", ml([r for r in cell if st.where(r["g"], r["side"]) == site]))
        R.row(f"  every dog, {site}", ml([r for r in dog if st.where(r["g"], r["side"]) == site]))
    R.row("  hot night, +100..+150", ml([r for r in cell if r["o"] <= 150]))
    R.row("  hot night, +151..+350", ml([r for r in cell if r["o"] > 150]))
    R.row("  hot night, back within 2 days", ml([r for r in cell if r["me"]["gap"] <= 2.5]))
    R.row("  hot night, 3-8 days later", ml([r for r in cell if r["me"]["gap"] > 2.5]))
    sh = [r for r in cell if seas3.get((r["g"]["id"], r["g"][r["side"]])) is not None]
    R.row("  hot night, a 36%+ shooting team on the year", ml([r for r in sh if seas3[(r["g"]["id"], r["g"][r["side"]])] >= .36]))
    R.row("  hot night, under 36% on the year", ml([r for r in sh if seas3[(r["g"]["id"], r["g"][r["side"]])] < .36]))
    R.row("  every dog, a 36%+ shooting team on the year (no hot night)", ml([r for r in dog if (pct(r) is None or pct(r) < .5)
                                                                           and (seas3.get((r["g"]["id"], r["g"][r["side"]])) or 0) >= .36]))
    R.row("  hot night at ESPN's OPEN (+100..+350 there)", [(r["s"], r["opr"], r["op"]) for r in rows if r["op"] and 100 <= r["op"] <= 350
                                                             and pct(r) is not None and pct(r) >= .5])
    R.row("  every dog at ESPN's open", [(r["s"], r["opr"], r["op"]) for r in rows if r["op"] and 100 <= r["op"] <= 350])
    R.row("  the favorite across a hot-night dog", ml([r for r in rows if r["o"] < 0 and r["th"] and r["th"]["a"] >= 18 and r["th"]["m"] / r["th"]["a"] >= .5
                                                       and 100 <= (r["g"]["mla"] if r["side"] == "home" else r["g"]["mlh"]) <= 350]))
    R.row("  hot night, against the spread (every price)", ml([r for r in rows if pct(r) is not None and pct(r) >= .5], "at"))
    R.row("  every dog with a last-game box", ml(dog))
    R.matched("the dog off a hot night", ml(cell), ml(dog), True)
    R.save()


if __name__ == "__main__":
    RUN = {"s1": s1, "s2": s2, "s9": s9}
    for a in sys.argv[1:] or list(RUN):
        RUN[a]()
