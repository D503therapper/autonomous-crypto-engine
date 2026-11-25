"""11/25 daily studies - the controls on the cells that stood out in s_today.py (fixed after the first pass, every one
written down before it ran): PRICE-MATCHED placebos (the same number of sides out of each 50-cent price bin of the
cell's own pool), the dose by league fifth, every season apart, ESPN's open (2023-26) as a second price.
  s9   college hoops: the SECOND-HALF team as a road favorite past -150 -> the home dog across it
  s10  college hoops: the GUARD-HEAVY road dog / the BIG road small favorite
  s5   NFL: the COMMITTEE backfield's dog
  s4   NFL: the passing game that spreads it / runs through one man, as a dog
python results/studies/daily_1125/s_follow.py [s9 s10 s5 s4]"""
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import s_today as st  # noqa: E402
from core import BT, BH, LT, LH  # noqa: E402

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
        r = lib.summ([(s, p) for s, p, _ in rows], self.train, self.held)
        self.p(lib.fmt(name, r))
        return r

    def matched(self, name, rows, pool, fade, n=2000, seed=11):
        """Price-matched placebo: random sets from `pool` with the same count out of each 50-cent price bin."""
        if not rows:
            return None

        def b(o):
            return int(o // 50)
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
        self.p(f"  price-matched placebo {name}: {hit} of {n} random same-price sets did as {'badly' if fade else 'well'}"
               f" (cell {got*100:+.1f}% on {len(rows)}, pool {pm*100:+.1f}% on {len(pool)})")
        return hit

    def save(self):
        open(os.path.join(HERE, self.tag + "_out.txt"), "w").write("\n".join(self.lines) + "\n")


def side_rows(fin, cond, band=(100, 350), open_=False):
    """[(season, profit, odds)] of every side cond(g, side, team, opp, odds) is true for, inside the price band."""
    out = []
    for g in fin:
        for side, team, opp, o, won, _ in lib.sides(g):
            if open_:
                o = g["oh"] if side == "home" else g["oa"]
                if o is None:
                    continue
            if not band[0] <= o <= band[1]:
                continue
            if cond(g, side, team, o, opp):
                out.append((g["season"], lib.profit(won, lib.dec(o)), o))
    return out


def ats_rows(fin, cond):
    out = []
    for g in fin:
        for side, team, opp, o, won, _ in lib.sides(g):
            if cond(g, side, team, o, opp):
                a = lib.ats(g, side)
                if a is not None:
                    out.append((g["season"], a, 0))
    return out


def s9():
    fin, rk = st.s9(ret=True)
    R = Rep("s9b_ncaab_second_half_controls", LT, LH)
    R.p("S9b - the SECOND-HALF team as a ROAD FAVORITE past -150, and the HOME DOG across it (true home floors, 2018-26)")

    def pct(g, t):
        v = rk.get((g["id"], t))
        return v[1] if v else None

    def road(g, side):
        return side == "away" and not g["neutral"]

    def home(g, side):
        return side == "home" and not g["neutral"]
    both = lambda g: pct(g, g["home"]) is not None and pct(g, g["away"]) is not None  # noqa: E731
    R.p("-- the road favorite past -150, by the league fifth of its second-half read")
    pool = side_rows(fin, lambda g, s, t, o, od: road(g, s) and both(g), band=(-100000, -151))
    R.row("EVERY road favorite past -150", pool)
    for lo_, hi_ in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
        R.row(f"road favorite past -150, read fifth {lo_:.1f}-{min(hi_, 1):.1f}",
              side_rows(fin, lambda g, s, t, o, od: road(g, s) and both(g) and lo_ <= pct(g, t) < hi_, band=(-100000, -151)))
    cell = side_rows(fin, lambda g, s, t, o, od: road(g, s) and both(g) and pct(g, t) >= .8, band=(-100000, -151))
    R.matched("the second-half road favorite past -150", cell, pool, fade=True)
    for lo_, hi_ in ((-100000, -401), (-400, -251), (-250, -151)):
        R.row(f"second-half road favorite {lo_ if lo_ > -100000 else 'past'}..{hi_}",
              side_rows(fin, lambda g, s, t, o, od: road(g, s) and both(g) and pct(g, t) >= .8, band=(lo_, hi_)))
        R.row(f"   every road favorite in that band",
              side_rows(fin, lambda g, s, t, o, od: road(g, s) and both(g), band=(lo_, hi_)))
    R.p("-- the HOME DOG +100..+350 across it (the bet the engine could make)")
    dpool = side_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g))
    R.row("EVERY home dog +100..+350", dpool)
    for lo_, hi_ in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
        R.row(f"home dog, the road favorite's read fifth {lo_:.1f}-{min(hi_, 1):.1f}",
              side_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and lo_ <= pct(g, od) < hi_))
    dcell = side_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and pct(g, od) >= .8)
    R.matched("the home dog across a second-half road favorite", dcell, dpool, fade=False)
    R.row("home dog +100..+199 across a second-half road favorite",
          side_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and pct(g, od) >= .8, band=(100, 199)))
    R.row("home dog +200..+350 across a second-half road favorite",
          side_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and pct(g, od) >= .8, band=(200, 350)))
    R.row("home dog across a TOP-TENTH second-half road favorite",
          side_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and pct(g, od) >= .9))
    R.row("home dog across it, Nov-Dec",
          side_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and pct(g, od) >= .8 and g["start"][5:7] in ("11", "12")))
    R.row("home dog across it, Jan-Mar",
          side_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and pct(g, od) >= .8 and g["start"][5:7] in ("01", "02", "03")))
    R.row("home dog across it, the dog NOT a first-half team (its own read over the bottom fifth)",
          side_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and pct(g, od) >= .8 and pct(g, t) > .2))
    R.p("-- ESPN's open (2023-26)")
    R.row("OPEN: every home dog +100..+350", side_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g), open_=True))
    R.row("OPEN: home dog across a second-half road favorite",
          side_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and pct(g, od) >= .8, open_=True))
    R.p("-- the spread: the home side across a second-half road team / the neutral twin")
    R.row("ATS every home side", ats_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g)))
    R.row("ATS home side across a second-half road team", ats_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and pct(g, od) >= .8))
    R.row("ATS home side getting points across a second-half road team",
          ats_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and pct(g, od) >= .8 and (g["sp"] or 0) > 0))
    R.row("ATS home side getting 3.5+ across a second-half road team",
          ats_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and pct(g, od) >= .8 and (g["sp"] or 0) >= 3.5))
    R.row("ATS every home side getting 3.5+", ats_rows(fin, lambda g, s, t, o, od: home(g, s) and both(g) and (g["sp"] or 0) >= 3.5))
    R.save()


def s10():
    fin, rk = st.s10("ncaab", ret=True)
    R = Rep("s10b_ncaab_guard_heavy_controls", BT, BH)
    R.p("S10b - college hoops: the GUARD-HEAVY road dog / the BIG road small favorite (true road games, the box 2021-26)")

    def pct(g, t):
        v = rk.get((g["id"], t))
        return v[1] if v else None
    both = lambda g: pct(g, g["home"]) is not None and pct(g, g["away"]) is not None  # noqa: E731

    def road(g, side):
        return side == "away" and not g["neutral"] and both(g)

    def home(g, side):
        return side == "home" and not g["neutral"] and both(g)
    pool = side_rows(fin, lambda g, s, t, o, od: road(g, s))
    R.row("EVERY road dog +100..+350", pool)
    for lo_, hi_ in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
        R.row(f"road dog, guard-minutes fifth {lo_:.1f}-{min(hi_, 1):.1f}",
              side_rows(fin, lambda g, s, t, o, od: road(g, s) and lo_ <= pct(g, t) < hi_))
    cell = side_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) >= .8)
    R.matched("the guard-heavy road dog", cell, pool, fade=False)
    big = side_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) < .2)
    R.matched("the big road dog", big, pool, fade=True)
    R.row("guard-heavy road dog +100..+199", side_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) >= .8, band=(100, 199)))
    R.row("guard-heavy road dog +200..+350", side_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) >= .8, band=(200, 350)))
    R.row("guard-heavy road dog, Nov-Dec", side_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) >= .8 and g["start"][5:7] in ("11", "12")))
    R.row("guard-heavy road dog, Jan-Mar", side_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) >= .8 and g["start"][5:7] in ("01", "02", "03")))
    R.row("guard-heavy road dog at a BIG team", side_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) >= .8 and pct(g, od) < .2))
    R.row("TOP-TENTH guard-heavy road dog", side_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) >= .9))
    R.row("OPEN: every road dog", side_rows(fin, lambda g, s, t, o, od: road(g, s), open_=True))
    R.row("OPEN: guard-heavy road dog", side_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) >= .8, open_=True))
    R.p("-- home dogs (the control: is it the team or the trip)")
    hp = side_rows(fin, lambda g, s, t, o, od: home(g, s))
    R.row("EVERY home dog", hp)
    R.row("guard-heavy home dog", side_rows(fin, lambda g, s, t, o, od: home(g, s) and pct(g, t) >= .8))
    R.row("big home dog", side_rows(fin, lambda g, s, t, o, od: home(g, s) and pct(g, t) < .2))
    R.p("-- the road small favorite -150..-101")
    fp = side_rows(fin, lambda g, s, t, o, od: road(g, s), band=(-150, -101))
    R.row("EVERY road small favorite", fp)
    for lo_, hi_ in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
        R.row(f"road small favorite, guard-minutes fifth {lo_:.1f}-{min(hi_, 1):.1f}",
              side_rows(fin, lambda g, s, t, o, od: road(g, s) and lo_ <= pct(g, t) < hi_, band=(-150, -101)))
    fc = side_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) < .2, band=(-150, -101))
    R.matched("the big road small favorite", fc, fp, fade=True)
    R.row("home dog +100..+150 across a BIG road small favorite",
          side_rows(fin, lambda g, s, t, o, od: home(g, s) and pct(g, od) < .2 and -150 <= (g["mla"] or 0) <= -101, band=(100, 150)))
    R.p("-- the spread")
    R.row("ATS every road side", ats_rows(fin, lambda g, s, t, o, od: road(g, s)))
    R.row("ATS guard-heavy road side", ats_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) >= .8))
    R.row("ATS guard-heavy road side getting points", ats_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) >= .8 and (g["sp"] or 0) < 0))
    R.row("ATS big road side", ats_rows(fin, lambda g, s, t, o, od: road(g, s) and pct(g, t) < .2))
    R.save()


def nfl(which):
    fin, rk = (st.s5 if which == "s5" else st.s4)("nfl", ret=True)
    R = Rep(f"{which}b_nfl_controls", BT, BH)
    xby = {x["id"]: x for x in lib.load_football("nfl")}
    if which == "s5":
        R.p("S5b - NFL: the COMMITTEE backfield's dog (the top back's share of the season's carries, league fifths; 2021-26)")
        pct = lambda g, t: ((rk.get((g["id"], t)) or {}).get("share") or (None, None))[1]  # noqa: E731
    else:
        R.p("S4b - NFL: the top receiver's share of the receiving yards, league fifths, as a dog (2021-26)")
        pct = lambda g, t: (rk.get((g["id"], t)) or (None, None))[1]  # noqa: E731
    ok = lambda g, t: pct(g, t) is not None  # noqa: E731
    pool = side_rows(fin, lambda g, s, t, o, od: ok(g, t))
    R.row("EVERY dog +100..+350 with a read", pool)
    for lo_, hi_ in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
        R.row(f"dog, share fifth {lo_:.1f}-{min(hi_, 1):.1f}", side_rows(fin, lambda g, s, t, o, od: ok(g, t) and lo_ <= pct(g, t) < hi_))
    lowc = side_rows(fin, lambda g, s, t, o, od: ok(g, t) and pct(g, t) <= .2)
    hic = side_rows(fin, lambda g, s, t, o, od: ok(g, t) and pct(g, t) >= .8)
    R.matched("the bottom-fifth dog", lowc, pool, fade=sum(p for _, p, _ in lowc) < 0)
    R.matched("the top-fifth dog", hic, pool, fade=sum(p for _, p, _ in hic) < 0)
    for nm, cnd in (("bottom fifth", lambda p: p <= .2), ("top fifth", lambda p: p >= .8)):
        R.row(f"{nm} dog, home", side_rows(fin, lambda g, s, t, o, od: ok(g, t) and cnd(pct(g, t)) and s == "home"))
        R.row(f"{nm} dog, road", side_rows(fin, lambda g, s, t, o, od: ok(g, t) and cnd(pct(g, t)) and s == "away"))
        R.row(f"{nm} dog +100..+199", side_rows(fin, lambda g, s, t, o, od: ok(g, t) and cnd(pct(g, t)), band=(100, 199)))
        R.row(f"{nm} dog +200..+350", side_rows(fin, lambda g, s, t, o, od: ok(g, t) and cnd(pct(g, t)), band=(200, 350)))
        R.row(f"{nm} ATS", ats_rows(fin, lambda g, s, t, o, od: ok(g, t) and cnd(pct(g, t))))
        R.row(f"{nm} favorite -101..-100000", side_rows(fin, lambda g, s, t, o, od: ok(g, t) and cnd(pct(g, t)), band=(-100000, -101)))
        # the first fair look of the paid history (no look-ahead price)
        early = []
        for g in fin:
            for side, team, opp, o, won, _ in lib.sides(g):
                if not ok(g, team) or not cnd(pct(g, team)):
                    continue
                e = lib.early_price(xby, g["id"], side)
                if e and 100 <= e[0] <= 350:
                    early.append((g["season"], lib.profit(won, e[1]), e[0]))
        R.row(f"{nm} dog at the FIRST FAIR look (paid history)", early)
    R.save()


if __name__ == "__main__":
    for a in [x for x in sys.argv[1:] if x != "s9c"] or ([] if "s9c" in sys.argv else ["s9", "s10", "s5", "s4"]):
        if a == "s9":
            s9()
        elif a == "s10":
            s10()
        else:
            nfl(a)


def s9c():
    """The SPREAD side of S9: the home side GETTING POINTS across a second-half road team - the dose, a random-set
    placebo, the points band, the months, a last-10-games read (a second definition), the mirrors."""
    from collections import deque
    import bisect
    import sports_data as sd
    fin, rk = st.s9(ret=True)
    R = Rep("s9c_ncaab_second_half_spread", LT, LH)
    R.p("S9c - the home side GETTING POINTS across a SECOND-HALF road team (true home floors, the close at its own juice, 2018-26)")

    def pct(g, t, src=rk):
        v = src.get((g["id"], t))
        return v[1] if v else None

    def ok(g, src=rk):
        return (not g["neutral"]) and pct(g, g["home"], src) is not None and pct(g, g["away"], src) is not None and (g["sp"] or 0) > 0
    pool = ats_rows(fin, lambda g, s, t, o, od: s == "home" and ok(g))
    R.row("EVERY home side getting points", pool)
    for lo_, hi_ in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, .9), (.9, 1.01)):
        R.row(f"home side getting points, the road team's read {lo_:.1f}-{min(hi_, 1):.1f}",
              ats_rows(fin, lambda g, s, t, o, od: s == "home" and ok(g) and lo_ <= pct(g, od) < hi_))
    cell = ats_rows(fin, lambda g, s, t, o, od: s == "home" and ok(g) and pct(g, od) >= .8)
    R.matched("the home side getting points across a second-half road team", cell, pool, fade=False)
    for nm, f in (("1-3", lambda x: x <= 3), ("3.5-7", lambda x: 3.5 <= x <= 7), ("7.5-12", lambda x: 7.5 <= x <= 12), ("12.5+", lambda x: x >= 12.5)):
        R.row(f"   getting {nm}", ats_rows(fin, lambda g, s, t, o, od: s == "home" and ok(g) and pct(g, od) >= .8 and f(g["sp"])))
        R.row(f"   every home side getting {nm}", ats_rows(fin, lambda g, s, t, o, od: s == "home" and ok(g) and f(g["sp"])))
    R.row("   Nov-Dec", ats_rows(fin, lambda g, s, t, o, od: s == "home" and ok(g) and pct(g, od) >= .8 and g["start"][5:7] in ("11", "12")))
    R.row("   Jan-Mar", ats_rows(fin, lambda g, s, t, o, od: s == "home" and ok(g) and pct(g, od) >= .8 and g["start"][5:7] in ("01", "02", "03")))
    R.row("   the home side NOT a second-half team itself", ats_rows(fin, lambda g, s, t, o, od: s == "home" and ok(g) and pct(g, od) >= .8 and pct(g, t) < .8))
    R.row("   the home side a second-half team too", ats_rows(fin, lambda g, s, t, o, od: s == "home" and ok(g) and pct(g, od) >= .8 and pct(g, t) >= .8))
    R.p("-- the mirrors")
    R.row("the second-half road team LAYING points (the same games)", ats_rows(fin, lambda g, s, t, o, od: s == "away" and ok(g) and pct(g, t) >= .8))

    def known(g):
        return pct(g, g["home"]) is not None and pct(g, g["away"]) is not None
    R.row("a second-half HOME team laying points", ats_rows(fin, lambda g, s, t, o, od: s == "home" and (not g["neutral"]) and known(g)
                                                             and pct(g, t) >= .8 and (g["sp"] or 0) < 0))
    R.row("   every home team laying points", ats_rows(fin, lambda g, s, t, o, od: s == "home" and (not g["neutral"]) and known(g) and (g["sp"] or 0) < 0))
    R.row("a second-half team laying points on a NEUTRAL floor", ats_rows(fin, lambda g, s, t, o, od: g["neutral"] and known(g) and pct(g, t) >= .8
                                                                           and (g["sp"] or 0) != 0 and ((g["sp"] or 0) < 0) == (s == "home")))
    R.row("a second-half road team GETTING points", ats_rows(fin, lambda g, s, t, o, od: s == "away" and (not g["neutral"]) and known(g)
                                                              and pct(g, t) >= .8 and (g["sp"] or 0) < 0))
    # a second definition: the LAST 10 games only
    allf = [g for g in lib.all_finals("ncaab") if g["season"] >= 2018]
    G = sd.load_games("ncaab")
    hist, latest, rk10 = defaultdict(lambda: deque(maxlen=10)), defaultdict(dict), {}
    for g in allf:
        s = g["season"]
        cur = {}
        for t in (g["home"], g["away"]):
            hq = hist[(s, t)]
            if len(hq) >= 5:
                cur[t] = sum(hq) / len(hq)
                latest[s][t] = cur[t]
        if len(latest[s]) >= 100:
            srt = sorted(latest[s].values())
            for t, v in cur.items():
                rk10[(g["id"], t)] = (v, bisect.bisect_left(srt, v) / (len(srt) - 1))
        gg = G.get(g["id"]) or {}
        a, b = lib.quarters(gg.get("ls_home")), lib.quarters(gg.get("ls_away"))
        if a and b and len(a) >= 2 and len(b) >= 2:
            m1, m2 = max(-20, min(20, a[0] - b[0])), max(-20, min(20, a[1] - b[1]))
            hist[(s, g["home"])].append(m2 - m1)
            hist[(s, g["away"])].append(m1 - m2)
    R.p("-- a second definition: the read over the team's LAST 10 games")
    R.row("LAST 10: home side getting points across a second-half road team",
          ats_rows(fin, lambda g, s, t, o, od: s == "home" and ok(g, rk10) and pct(g, od, rk10) >= .8))
    R.row("LAST 10: home dog +100..+350 across a second-half road favorite",
          side_rows(fin, lambda g, s, t, o, od: s == "home" and ok(g, rk10) and pct(g, od, rk10) >= .8))
    R.row("LAST 10: the second-half road favorite past -150",
          side_rows(fin, lambda g, s, t, o, od: s == "away" and ok(g, rk10) and pct(g, t, rk10) >= .8, band=(-100000, -151)))
    R.save()


if __name__ == "__main__" and "s9c" in sys.argv[1:]:
    s9c()
