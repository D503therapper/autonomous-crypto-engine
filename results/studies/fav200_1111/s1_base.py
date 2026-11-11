"""11/11 THE -150 RULE (Victor's question) - S1 THE BASE: every favorite at the CLOSE, flat 1u, by price band / league /
train (2018-21) vs blind (2022 on) / seasons up. Is the market fair at -151..-250? Read-only (game files via
results/studies/daily_1110/lib.py; caches in ~/.cache). Also the closing-spread cover of the same favorites (S3's base).
Usage: python results/studies/fav200_1111/s1_base.py > results/studies/fav200_1111/s1_base.out"""
import importlib.util, math, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
_s = importlib.util.spec_from_file_location("b1110", os.path.join(ROOT, "results", "studies", "daily_1110", "lib.py"))
B = importlib.util.module_from_spec(_s)
_s.loader.exec_module(B)

BANDS = [("-101..-150 (today's band)", -150, -101), ("-151..-175", -175, -151), ("-176..-200", -200, -176),
         ("-201..-250", -250, -201), ("-151..-250 (all)", -250, -151)]
TRAIN = (2018, 2021)
LEAGUES = ["nfl", "ncaaf", "nhl", "nba", "ncaab", "mlb"]


def st(bs):
    """bs: [(season, won, decimal price)] -> n, won %, price needs %, flat ROI %, z vs the price."""
    if not bs:
        return None
    n = len(bs)
    w = sum(b[1] for b in bs)
    net = sum((b[2] - 1) if b[1] else -1 for b in bs)
    be = sum(1 / b[2] for b in bs)
    var = sum((1 / b[2]) * (1 - 1 / b[2]) for b in bs)
    return n, 100 * w / n, 100 * be / n, 100 * net / n, (w - be) / math.sqrt(var) if var else 0.0


def line(name, bets):
    a = st(bets)
    if not a:
        return f"  {name:34s} -"
    t = st([b for b in bets if TRAIN[0] <= b[0] <= TRAIN[1]])
    h = st([b for b in bets if b[0] > TRAIN[1]])
    seas = defaultdict(list)
    for b in bets:
        seas[b[0]].append(b)
    up = sum(st(v)[3] > 0 for v in seas.values())
    f = lambda x: f"{x[3]:+6.1f}% ({x[0]:5d})" if x else "    -         "  # noqa: E731
    per = " ".join(f"{s % 100:02d}:{st(v)[3]:+.0f}" for s, v in sorted(seas.items()))
    return (f"  {name:34s} n {a[0]:5d} won {a[1]:5.1f}% (price needs {a[2]:5.1f}%) flat {a[3]:+6.1f}% z {a[4]:+5.2f} | "
            f"train {f(t)} | blind {f(h)} | seasons up {up}/{len(seas)} | {per}")


def ats_bet(g, side):
    """(won, decimal juice) laying / taking the closing spread, None on no spread or a push."""
    if g["sp"] is None:
        return None
    m = g["hs"] - g["as"]
    r = m + g["sp"] if side == "home" else -(m + g["sp"])
    o = (g["spho"] if side == "home" else g["spao"]) or -110
    if r == 0:
        return None
    return r > 0, B.dec(o)


def main():
    allb = defaultdict(list)
    ats = defaultdict(list)
    for lg in LEAGUES:
        try:
            fin = B.finals(lg)
        except Exception as e:  # noqa: BLE001
            print(lg, "no finals:", str(e)[:80])
            continue
        fin = [g for g in fin if g["season"] >= 2018 and g["stype"] == "2"]
        print(f"\n== {lg.upper()} (regular season, closing moneyline, {len(fin)} games, seasons {fin[0]['season']}-{fin[-1]['season']})")
        for g in fin:
            for side, team, opp, odds, won, home in B.sides(g):
                if odds is None or odds > -101:
                    continue
                d = B.dec(odds)
                for nm, lo, hi in BANDS:
                    if lo <= odds <= hi:
                        allb[(lg, nm)].append((g["season"], won, d))
                        if lg != "mlb":
                            allb[("ALL5", nm)].append((g["season"], won, d))
                        a = ats_bet(g, side)
                        if a is not None and lg in ("nfl", "ncaaf", "nba", "ncaab"):
                            ats[(lg, nm)].append((g["season"], a[0], a[1]))
        for nm, _, _ in BANDS:
            print(line(nm, allb[(lg, nm)]))
    print("\n== THE FIVE LEAGUES WE PICK, TOGETHER (NFL, college football, NHL, NBA, college hoops)")
    for nm, _, _ in BANDS:
        print(line(nm, allb[("ALL5", nm)]))
    print("\n== THE SAME FAVORITES LAYING THE CLOSING SPREAD (real juice, -110 when missing; pushes out)")
    for lg in ("nfl", "ncaaf", "nba", "ncaab"):
        for nm, _, _ in BANDS:
            if ats[(lg, nm)]:
                print(line(f"{lg} ATS {nm}", ats[(lg, nm)]))


if __name__ == "__main__":
    main()
