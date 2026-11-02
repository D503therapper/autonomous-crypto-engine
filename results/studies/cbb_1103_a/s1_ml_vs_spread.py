"""STUDY 1 - MONEYLINE vs SPREAD in college hoops: do the two markets agree, and is one softer?
(a) The map spread -> win chance is fit on TRAIN results only (logistic on the closing home spread + a neutral flag);
    each game's moneyline no-vig is set against it. Bet the side whose MONEYLINE is cheap next to its own spread
    (the ML says it wins less often than the spread does) by 2-4 / 4+ points, at the moneyline close.
(b) Softness: the same favorite / dog read two ways - its ML vs its spread at -110ish - which loses less, early
    (each team's games 1-5 / November) vs later. Spreads 1-9.5 only (where both markets are real bets).
Train 2018-22, held out 2023 / 24 / 25 apart."""
import math
import lib
from collections import defaultdict

rows = [r for r in lib.annotate(lib.load()) if r["season"] >= 2018]


def fit(train):
    # logistic: P(home wins) = sigmoid(a * (-spread) + b * neutral + c); plain gradient descent
    a, b, c = 0.1, 0.0, 0.0
    for _ in range(300):
        ga = gb = gc = 0.0
        for x, nt, y in train:
            p = 1 / (1 + math.exp(-(a * x + b * nt + c)))
            ga += (y - p) * x; gb += (y - p) * nt; gc += (y - p)
        n = len(train)
        a += 0.002 * ga / n; b += 0.5 * gb / n; c += 0.5 * gc / n
    return a, b, c


data = []
for r in rows:
    try:
        sp, mh, ma = float(r["spread_home"]), float(r["ml_home"]), float(r["ml_away"])
    except (TypeError, ValueError):
        continue
    if abs(mh) < 100 or abs(ma) < 100 or sp == 0:
        continue
    data.append((r, sp, mh, ma))
train = [(-sp, 1.0 if str(r["neutral"]) == "1" else 0.0, 1.0 if r["hs"] > r["as_"] else 0.0)
         for r, sp, mh, ma in data if r["season"] in lib.TRAIN and abs(sp) <= 25]
A, B, C = fit(train)
print(__doc__)
print(f"fit on {len(train)} train games: P(home) = sigmoid({A:.4f} * -spread + {B:.3f} * neutral + {C:.3f})")
cells = defaultdict(lib.Cell)
gaps = defaultdict(list)
for r, sp, mh, ma in data:
    s = r["season"]
    nt = 1.0 if str(r["neutral"]) == "1" else 0.0
    p_sp = 1 / (1 + math.exp(-(A * -sp + B * nt + C)))
    p_ml = lib.novig(mh, ma)
    early = max(r["gn_home"], r["gn_away"]) <= 5
    nov = r["dt"].month == 11
    ph = "g1-5" if early else ("Nov" if nov else "Dec+")
    gaps[ph].append(p_ml - p_sp)
    hw = r["hs"] > r["as_"]
    for side, odds, gap, won, sline in (("home", mh, p_ml - p_sp, hw, sp), ("away", ma, (1 - p_ml) - (1 - p_sp), not hw, -sp)):
        # gap < 0: the ML prices this side to win LESS than its spread says -> its ML is cheap
        if abs(sline) > 15 or not (-400 <= odds <= 350):
            continue
        band = "ML cheap 4+" if gap <= -0.04 else ("ML cheap 2-4" if gap <= -0.02 else ("ML dear 2+" if gap >= 0.02 else None))
        if band:
            kind = "dog" if odds > 0 else "fav"
            cells[f"(a) {band} {kind} | {ph}"].add(s, lib.ml_profit(odds, won), won)
        # (b) softness, spreads 1-9.5
        if 1 <= abs(sline) <= 9.5:
            kind = "fav" if sline < 0 else "dog"
            so = r[f"spread_{side}_odds"]
            try:
                so = float(so) if so else -110.0
            except ValueError:
                so = -110.0
            margin = (r["hs"] - r["as_"]) * (1 if side == "home" else -1)
            cells[f"(b) {kind} sp 1-9.5 ML | {ph}"].add(s, lib.ml_profit(odds, won), won)
            cells[f"(b) {kind} sp 1-9.5 ATS | {ph}"].add(s, lib.ats_profit(margin + sline, so))
for k in sorted(cells):
    print(cells[k].line(k))
print("\nML no-vig minus the spread's win chance (home side): mean / spread of the gap")
for ph, xs in gaps.items():
    m = sum(xs) / len(xs)
    sd = (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5
    print(f"  {ph:5} n={len(xs)} mean {m:+.4f} sd {sd:.4f} share |gap|>=2pts {sum(abs(x) >= 0.02 for x in xs) / len(xs):.1%}")
