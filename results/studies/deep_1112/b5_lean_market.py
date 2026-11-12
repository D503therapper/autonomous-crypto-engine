"""11/12 DEEP PROGRAM - B5: WHICH MARKET SHOULD A LEAN USE? A lean carries no units - it is a WHO-WINS (or who-covers)
call that lives in the 🟡 record (W-L) and in the viewers' pockets (the flat ROI). Today: a game whose favorite sits at
-150 or cheaper leans the moneyline side the engine has winning; a game with a bigger favorite can only lean a SPREAD
side, and the side comes from the cover read (the close + a 'big favorite' dial fit on past covers).
Every close 2018-26 (the fifteen-studies tables), train to 2021 / blind 2022 on, the close at its juice:
  A  games with a favorite at -101..-150: the favorite's moneyline vs the SAME side's spread vs the dog + the points
  B  games with a favorite past -150: the favorite laying the points vs the dog getting them, by the size of the number
     and by who's home - the only two leans the board can post there
  C  the cover read's 'big favorite' dial (sports_model 'bfav') walked forward: the side it picks on every 7.5+ spread
Usage: python results/studies/deep_1112/b5_lean_market.py > results/studies/deep_1112/b5_lean_market.out"""
import math
import dlib as D
import lib as L


def rec(name, bets):
    """bets = [(season, profit)] -> W-L, win %, ROI, train / blind"""
    bs = [(s, p) for s, p in bets if p is not None]
    if len(bs) < 30:
        return
    D.CELLS[0] += 1
    w = sum(p > 0 for _, p in bs)
    l = sum(p < 0 for _, p in bs)
    tr = [p for s, p in bs if s <= 2021]
    bl = [p for s, p in bs if s >= 2022]
    m = sum(p for _, p in bs) / len(bs)
    sd = math.sqrt(sum((p - m) ** 2 for _, p in bs) / len(bs))
    by = {}
    for s, p in bs:
        by.setdefault(s, []).append(p)
    up = sum(sum(v) > 0 for v in by.values())
    print(f"   {name:52s} {w:5d}-{l:<5d} won {100 * w / max(1, w + l):4.1f}%  flat {100 * m:+5.1f}% z {m / (sd / math.sqrt(len(bs))):+4.1f} | train {100 * sum(tr) / max(1, len(tr)):+5.1f}% | blind {100 * sum(bl) / max(1, len(bl)):+5.1f}% | seasons up {up}/{len(by)}")


for lg in ("nfl", "ncaaf", "nba", "ncaab"):
    T = [g for g in L.table(lg) if L.fav(g) and g["sp"] is not None and L.reg(g)]
    print(f"\n==== {lg.upper()} ({len(T)} games with a moneyline and a spread)")
    A = [g for g in T if -150 <= L.odds(g, L.fav(g)) <= -101]
    print(f" A. a favorite at -101..-150 ({len(A)} games)")
    rec("the favorite's MONEYLINE", [(g["season"], L.ml(g, L.fav(g))) for g in A])
    rec("the favorite laying the points", [(g["season"], L.ats(g, L.fav(g))) for g in A])
    rec("the dog + the points", [(g["season"], L.ats(g, L.other(L.fav(g)))) for g in A])
    rec("the dog's moneyline", [(g["season"], L.ml(g, L.other(L.fav(g)))) for g in A])
    rec("HOME favorite's moneyline", [(g["season"], L.ml(g, "H")) for g in A if L.fav(g) == "H"])
    rec("ROAD favorite's moneyline", [(g["season"], L.ml(g, "A")) for g in A if L.fav(g) == "A"])
    B = [g for g in T if L.odds(g, L.fav(g)) < -150]
    print(f" B. a favorite past -150 ({len(B)} games) - the spread is the only lean")
    rec("the favorite laying the points", [(g["season"], L.ats(g, L.fav(g))) for g in B])
    rec("the dog + the points", [(g["season"], L.ats(g, L.other(L.fav(g)))) for g in B])
    bands = ((0, 5.5), (6, 9.5), (10, 13.5), (14, 99)) if lg in ("nba", "ncaab") else ((0, 6.5), (7, 9.5), (10, 16.5), (17, 99))
    for lo, hi in bands:
        S = [g for g in B if lo <= abs(g["sp"]) <= hi]
        rec(f"  laying {lo:g}-{hi if hi < 99 else '+'}: the favorite", [(g["season"], L.ats(g, L.fav(g))) for g in S])
        rec(f"  getting {lo:g}-{hi if hi < 99 else '+'}: the dog", [(g["season"], L.ats(g, L.other(L.fav(g)))) for g in S])
    rec("  the HOME dog + the points", [(g["season"], L.ats(g, "H")) for g in B if L.fav(g) == "A" and not g["neutral"]])
    rec("  the ROAD dog + the points", [(g["season"], L.ats(g, "A")) for g in B if L.fav(g) == "H" and not g["neutral"]])
    # C: the big-favorite dial, walked forward (fit on every earlier season's covers, as sports_model.tune does)
    print(" C. the cover read's big-favorite dial, walked forward (each season fit on the seasons before)")
    seasons = sorted({g["season"] for g in T})
    picks, dials = [], []
    for s in seasons[2:]:
        tr = [g for g in T if g["season"] < s and abs(g["sp"]) > 7 and g["hs"] - g["as"] + g["sp"] != 0]
        if len(tr) < 100:
            continue
        X = [[(-g["sp"] - 7) / 7 if g["sp"] < 0 else (g["sp"] - 7) / -7] for g in tr]
        y = [1.0 if g["hs"] - g["as"] + g["sp"] > 0 else 0.0 for g in tr]
        w, se = D.fit_offset(X, y, [0.0] * len(tr), lam=4.0)
        dials.append((s, w[0], se[0]))
        for g in T:
            if g["season"] == s and abs(g["sp"]) > 7:
                side = L.fav(g) if w[0] > 0 else L.other(L.fav(g))
                picks.append((g["season"], L.ats(g, side)))
    print("   the dial by season (+ = big favorites cover more): " + "  ".join(f"{s}: {w:+.3f} (se {se:.3f})" for s, w, se in dials))
    rec("the side the dial picks on every 7.5+ spread", picks)
print("\ncells:", D.CELLS[0])
