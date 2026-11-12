"""11/12 DEEP PROGRAM - E3: MIDDLES (bet a side early, the other side at the close when the number has moved, win both
when the game lands between). The paid odds history's first FAIR spread look (NFL 2020-26, college 2021-26: one early-
week look a game, every book - results/studies/spreads2_1111/lib2.football) against our closing spread at its juice.
  1. how often a game LANDS in the gap, by the size of the move and by whether it crosses the 3 / 7 (the oracle: the
     side the number moved to, bet early at -110, hedged at the close);
  2. hold vs hedge: the early ticket alone vs the two-ticket middle, per unit staked;
  3. THE HONEST VERSION: a rule known on Tuesday (the sides the 11/11 timing study found gain - NFL short dogs, home
     dogs; college short dogs, dogs off a 17+ win) bet early at the market number, hedged at the close only when the
     number came 1.5+ / 2+ our way - the whole book of early bets, moves and non-moves together.
TRAIN 2020-22 / HELD 2023-26. Not known: whether a book would still hang the early number at size (the tape has one
look), and no early number exists for the NBA / hoops / hockey.
Usage: python results/studies/deep_1112/e3_middles.py > results/studies/deep_1112/e3_middles.out"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "spreads2_1111"))
import lib2 as L          # noqa: E402

CELLS = [0]


def pay(r, price=-110):
    return 0.0 if r == 0 else ((L.dec(price) - 1) if r > 0 else -1.0)


def line(name, rows):
    """rows = [(season, profit, staked)] -> ROI on the money staked."""
    CELLS[0] += 1
    if not rows:
        print(f"  {name:70s} none")
        return
    def roi(rs):
        st = sum(s for _, _, s in rs)
        return 100 * sum(p for _, p, _ in rs) / st if st else float("nan")
    tr = [r for r in rows if not L.held(r[0])]
    he = [r for r in rows if L.held(r[0])]
    by = {}
    for r in he:
        by.setdefault(r[0], []).append(r)
    up = sum(1 for v in by.values() if sum(p for _, p, _ in v) > 0)
    ps = [p / s for _, p, s in rows]
    m = sum(ps) / len(ps)
    sd = (sum((x - m) ** 2 for x in ps) / len(ps)) ** 0.5
    print(f"  {name:70s} n {len(rows):5d} {roi(rows):+6.1f}% z {m / (sd / len(ps) ** 0.5) if sd else 0:+5.2f} | train {roi(tr):+6.1f}% ({len(tr):4d}) | held {roi(he):+6.1f}% ({len(he):4d}) {up}/{len(by)} up")


for lg in ("nfl", "ncaaf"):
    G = [g for g in L.football(lg) if g.get("c_sp") is not None and abs(g["c_sp"] - g["med"]) <= 10]
    print(f"\n==== {lg.upper()}: {len(G)} games with a first fair spread look and a close")
    print(" 1. THE ORACLE: the side the number moved TO, bet at the first number (-110), hedged at the close (its juice)")
    for lo, hi in ((0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 10.0)):
        hold, mid, hits, n, cross = [], [], 0, 0, []
        for g in G:
            d = g["c_sp"] - g["med"]                    # < 0: the home side got dearer (the number moved TO home)
            if not lo <= abs(d) < hi:
                continue
            side = "home" if d < 0 else "away"
            early = L.cover(g["margin"], g["med"], side)
            hedge = L.cover(g["margin"], g["c_sp"], "away" if side == "home" else "home", (g["c_sao"] if side == "home" else g["c_sho"]) or -110)
            n += 1
            both = early > 0 and hedge > 0
            hits += both
            hold.append((g["season"], early, 1.0))
            mid.append((g["season"], early + hedge, 2.0))
            a, b = sorted((abs(g["med"]), abs(g["c_sp"])))
            if (g["med"] * g["c_sp"] > 0) and any(a < k <= b or a <= k < b for k in (3, 7)):
                cross.append((g["season"], early + hedge, 2.0, both))
        if n:
            print(f"   the number moved {lo:g}-{hi:g}: {n} games ({100 * n / len(G):.0f}%), landed in the middle {hits} ({100 * hits / n:.1f}%)")
            line("      hold the early ticket", hold)
            line("      hedge it at the close (the middle)", mid)
            if cross:
                line(f"      ... the move crossed the 3 or the 7 (middle hit {100 * sum(c[3] for c in cross) / len(cross):.1f}%)", [c[:3] for c in cross])
    print(" 2. THE HONEST VERSION: a side picked on Tuesday by rule, hedged only when the number came our way")

    def last_margin(g, side):
        return g.get("h_last" if side == "home" else "a_last")
    rules = [("every dog", lambda g, s: (g["med"] > 0) == (s == "home") and g["med"] != 0),
             ("short dog +1..+3", lambda g, s: 1 <= (g["med"] if s == "home" else -g["med"]) <= 3),
             ("home dog", lambda g, s: s == "home" and g["med"] > 0),
             ("dog +3.5..+7", lambda g, s: 3.5 <= (g["med"] if s == "home" else -g["med"]) <= 7),
             ("every favorite", lambda g, s: (g["med"] < 0) == (s == "home") and g["med"] != 0)]
    for nm, rule in rules:
        for cut in (None, 1.5, 2.0):
            rows, hedged, hit = [], 0, 0
            for g in G:
                for s in ("home", "away"):
                    if not rule(g, s):
                        continue
                    early = L.cover(g["margin"], g["med"], s)
                    gain = (g["med"] - g["c_sp"]) if s == "home" else (g["c_sp"] - g["med"])      # points the close is worse than our ticket
                    if cut is not None and gain >= cut:
                        hedge = L.cover(g["margin"], g["c_sp"], "away" if s == "home" else "home", (g["c_sao"] if s == "home" else g["c_sho"]) or -110)
                        rows.append((g["season"], early + hedge, 2.0))
                        hedged += 1
                        hit += early > 0 and hedge > 0
                    else:
                        rows.append((g["season"], early, 1.0))
            lab = f"{nm}: " + ("hold every ticket" if cut is None else f"hedge when the number came {cut:g}+ our way ({hedged} hedged, {hit} middles)")
            line(lab, rows)
print(f"\ncells: {CELLS[0]}")
