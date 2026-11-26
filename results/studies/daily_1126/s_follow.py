"""11/26 daily studies - the controls on the cells that stood out in s_today.py (fixed after the first pass, every one
written down before it ran): the dose by league fifth, every season apart, PRICE-MATCHED placebos (the same number of
sides out of each 50-cent price bin of the cell's own pool), the paid football history's FIRST FAIR spread (read,
never pulled), ESPN's open (2023-26), and - for college football - the same read on FBS-vs-FBS games only.
  s2   football: the FIRST-QUARTER team (college: on the road; NFL: at home) against the spread
  s5   NHL: the dog with top-fifth SPECIAL TEAMS / a top-fifth KILL
python results/studies/daily_1126/s_follow.py [s2 s5]"""
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

    def plain(self, name, rows, pool, fade, n=2000, seed=11):
        if not rows or len(pool) < len(rows):
            return None
        got = sum(p for _, p, _ in rows) / len(rows)
        vals = [p for _, p, _ in pool]
        rnd = random.Random(seed)
        k = len(rows)
        hit = sum(1 for _ in range(n) if ((sum(rnd.sample(vals, k)) / k <= got) if fade else (sum(rnd.sample(vals, k)) / k >= got)))
        self.p(f"  placebo {name}: {hit} of {n} random same-size sets did as {'badly' if fade else 'well'}"
               f" (cell {got*100:+.1f}% on {k}, pool {sum(vals)/len(vals)*100:+.1f}% on {len(vals)})")
        return hit

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


FIFTHS = ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01))


def s2():
    for lg, where_, sidek in (("ncaaf", "ROAD", "away"), ("nfl", "HOME", "home")):
        fin, rk = st.quarter(lg, 0, "", "", 14, 4, ret=True)
        R = Rep(f"s2b_{lg}_first_quarter_controls", LT, LH)
        R.p(f"S2b - {lg.upper()}: the FIRST-QUARTER team against the spread, {where_} (true home / road fields, 2018-26)")
        pct = lambda g, t, rk=rk: (rk.get((g["id"], t)) or (None, None))[1]  # noqa: E731
        both = lambda g: pct(g, g["home"]) is not None and pct(g, g["away"]) is not None  # noqa: E731
        here = lambda g, s: both(g) and not g["neutral"] and s == sidek  # noqa: E731
        other = "home" if sidek == "away" else "away"
        pool = ats_rows(fin, lambda g, s, t, o, od: here(g, s))
        R.row(f"ATS every {where_.lower()} side", pool)
        for lo_, hi_ in FIFTHS:
            R.row(f"ATS {where_.lower()} side, first-quarter fifth {lo_:.1f}-{min(hi_, 1):.1f}",
                  ats_rows(fin, lambda g, s, t, o, od: here(g, s) and lo_ <= pct(g, t) < hi_))
        top = ats_rows(fin, lambda g, s, t, o, od: here(g, s) and pct(g, t) >= .8)
        R.plain("the top-fifth side", top, pool, fade=True)
        R.row("ATS top fifth, laying points", ats_rows(fin, lambda g, s, t, o, od: here(g, s) and pct(g, t) >= .8 and o < 0))
        R.row("ATS top fifth, getting points", ats_rows(fin, lambda g, s, t, o, od: here(g, s) and pct(g, t) >= .8 and o > 0))
        R.row("ATS the side ACROSS a top fifth", ats_rows(fin, lambda g, s, t, o, od: both(g) and not g["neutral"] and s == other and pct(g, od) >= .8))
        R.row("ML top fifth, dog +100..+350", side_rows(fin, lambda g, s, t, o, od: here(g, s) and pct(g, t) >= .8))
        R.row("ML top fifth, favorite -101..-150", side_rows(fin, lambda g, s, t, o, od: here(g, s) and pct(g, t) >= .8, band=(-150, -101)))
        R.row("ML top fifth, favorite past -150", side_rows(fin, lambda g, s, t, o, od: here(g, s) and pct(g, t) >= .8, band=(-100000, -151)))
        R.row("ML the dog ACROSS a top fifth", side_rows(fin, lambda g, s, t, o, od: both(g) and not g["neutral"] and s == other and pct(g, od) >= .8))
        R.row("ML every dog on that side of the field", side_rows(fin, lambda g, s, t, o, od: both(g) and not g["neutral"] and s == other))
        # the same team by its OTHER quarters: is it the first quarter, or just a good team laying a big number?
        for q, nm in ((1, "second"), (2, "third"), (3, "fourth")):
            _, rq = st.quarter(lg, q, "", "", 14, 4, ret=True)
            pq = lambda g, t, rq=rq: (rq.get((g["id"], t)) or (None, None))[1]  # noqa: E731
            R.row(f"ATS {where_.lower()} side, top fifth by its {nm} quarter instead",
                  ats_rows(fin, lambda g, s, t, o, od: here(g, s) and pq(g, t) is not None and pq(g, t) >= .8))
        # the paid history's first FAIR spread
        xby = {x["id"]: x for x in lib.load_football(lg)}
        early, close_same = [], []
        for g in fin:
            if g["neutral"] or not both(g):
                continue
            t = g[sidek]
            if pct(g, t) < .8:
                continue
            x = xby.get(g["id"])
            f = lib.first_fair(x["sp"]) if x else None
            if not f:
                continue
            hp, hd, ad = lib.sp_med(f[1])
            m = g["hs"] - g["as"]
            r = (m + hp) if sidek == "home" else -(m + hp)
            if r != 0:
                early.append((g["season"], lib.profit(r > 0, hd if sidek == "home" else ad), 0))
                a = lib.ats(g, sidek)
                if a is not None:
                    close_same.append((g["season"], a, 0))
        R.row("ATS top fifth at the FIRST FAIR spread (paid history)", early)
        R.row("  ... the same games at the close", close_same)
        if lg == "ncaaf":
            fin2, rk2 = st.quarter(lg, 0, "", "", 14, 4, ret=True, fbs_only=True)
            p2 = lambda g, t: (rk2.get((g["id"], t)) or (None, None))[1]  # noqa: E731
            ok2 = lambda g, s: p2(g, g["home"]) is not None and p2(g, g["away"]) is not None and not g["neutral"] and s == sidek  # noqa: E731
            R.p("THE READ ON FBS-vs-FBS GAMES ONLY (no first quarter against a lower-division school counts):")
            pool2 = ats_rows(fin2, lambda g, s, t, o, od: ok2(g, s))
            R.row("ATS every road side (both teams read)", pool2)
            for lo_, hi_ in FIFTHS:
                R.row(f"ATS road side, FBS-only fifth {lo_:.1f}-{min(hi_, 1):.1f}",
                      ats_rows(fin2, lambda g, s, t, o, od: ok2(g, s) and lo_ <= p2(g, t) < hi_))
            R.plain("the FBS-only top-fifth road side", ats_rows(fin2, lambda g, s, t, o, od: ok2(g, s) and p2(g, t) >= .8), pool2, fade=True)
        R.save()


def s5():
    fin, rk = st.s5(ret=True)
    R = Rep("s5b_nhl_special_teams_controls", BT, BH)
    R.p("S5b - NHL: the DOG by its special teams (PP% + PK%) and by its penalty kill, league fifths (2021-26)")
    v = lambda g, t, k: (rk.get((g["id"], t)) or {}).get(k, (None, None))[1]  # noqa: E731
    ok = lambda g, t: v(g, t, "net") is not None  # noqa: E731
    pool = side_rows(fin, lambda g, s, t, o, od: ok(g, t))
    R.row("EVERY dog +100..+350 with a read", pool)
    for k, nm in (("net", "special teams"), ("pk", "kill"), ("pp", "power play")):
        for lo_, hi_ in FIFTHS:
            R.row(f"dog, {nm} fifth {lo_:.1f}-{min(hi_, 1):.1f}", side_rows(fin, lambda g, s, t, o, od: ok(g, t) and lo_ <= v(g, t, k) < hi_))
        top = side_rows(fin, lambda g, s, t, o, od: ok(g, t) and v(g, t, k) >= .8)
        R.matched(f"the top-fifth {nm} dog", top, pool, fade=True)
        R.row(f"top-fifth {nm} dog at ESPN's open", side_rows(fin, lambda g, s, t, o, od: ok(g, t) and v(g, t, k) >= .8, open_=True))
        R.row(f"top-fifth {nm} dog +100..+150", side_rows(fin, lambda g, s, t, o, od: ok(g, t) and v(g, t, k) >= .8, band=(100, 150)))
        R.row(f"top-fifth {nm} dog +151..+350", side_rows(fin, lambda g, s, t, o, od: ok(g, t) and v(g, t, k) >= .8, band=(151, 350)))
        R.row(f"the favorite across a top-fifth {nm} dog", side_rows(fin, lambda g, s, t, o, od: ok(g, od) and v(g, od, k) >= .8, band=(-350, -101)))
    R.row("EVERY dog at ESPN's open", side_rows(fin, lambda g, s, t, o, od: ok(g, t), open_=True))
    R.save()


if __name__ == "__main__":
    for a in sys.argv[1:] or ["s2", "s5"]:
        {"s2": s2, "s5": s5}[a]()
