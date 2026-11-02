"""THE OWNER'S QUESTION (11/3: "especially opening week ... so many upsets ... huge edges to be had"): do college hoops
underdogs win against their price in OPENING WEEK and in each team's games 1-5, vs later? Every priced ncaab moneyline
dog +100..+350 (our band) and the long ones +351..+1000 (read only - never a pick), at ESPN's CLOSE (2018-25) and at
ESPN's OPEN (2023-25 only). Also the upset RATE vs the price's no-vig expectation (calibration), and favorites.
Train 2018-22, held out 2023 / 2024 / 2025 apart."""
import lib
from collections import defaultdict

rows = lib.annotate(lib.load())
cells = defaultdict(lib.Cell)
calib = defaultdict(lambda: [0, 0.0, 0])        # n, sum of no-vig p, wins
for r in rows:
    if r["season"] < 2018 or not r["ml_home"] or not r["ml_away"]:
        continue
    try:
        mh, ma = float(r["ml_home"]), float(r["ml_away"])
    except ValueError:
        continue
    if abs(mh) < 100 or abs(ma) < 100:
        continue
    nh = lib.novig(mh, ma)
    neutral = str(r["neutral"]) == "1"
    for side, odds, p, won, gn, ogn in (("home", mh, nh, r["hs"] > r["as_"], r["gn_home"], r["gn_away"]),
                                        ("away", ma, 1 - nh, r["as_"] > r["hs"], r["gn_away"], r["gn_home"])):
        s = r["season"]
        nov = r["dt"].month == 11
        wk1 = r["day_in_season"] <= 7
        early = max(gn, ogn) <= 5          # both teams in their first 5 games
        phase = "wk1" if wk1 else ("g1-5" if early else ("Nov-rest" if nov else "Dec+"))
        site = "neutral" if neutral else side
        if 100 <= odds <= 350:
            band = "dog +100..+150" if odds <= 150 else ("dog +151..+250" if odds <= 250 else "dog +251..+350")
            pl = lib.ml_profit(odds, won)
            for k in (f"ALL dogs +100..+350 | {phase}", f"{band} | {phase}", f"dogs {site} | {phase}"):
                cells[k].add(s, pl, won)
            # open price (2023-25)
            o_open = r.get(f"ml_{side}_open")
            if o_open:
                try:
                    oo = float(o_open)
                    if 100 <= oo <= 350:
                        cells[f"AT THE OPEN dogs +100..+350 | {phase}"].add(s, lib.ml_profit(oo, won), won)
                except ValueError:
                    pass
        elif 351 <= odds <= 1000:
            cells[f"long dog +351..+1000 (read only) | {phase}"].add(s, lib.ml_profit(odds, won), won)
        elif -150 <= odds <= -101:
            cells[f"fav -101..-150 | {phase}"].add(s, lib.ml_profit(odds, won), won)
            cells[f"fav -101..-150 {site} | {phase}"].add(s, lib.ml_profit(odds, won), won)
        elif -400 <= odds < -150:
            cells[f"fav -151..-400 | {phase}"].add(s, lib.ml_profit(odds, won), won)
        if odds > 0:
            c = calib[(phase, "held" if s in lib.HELD else "train")]
            c[0] += 1; c[1] += p; c[2] += won

print(__doc__)
for k in sorted(cells):
    print(cells[k].line(k))
print("\nUPSET RATE (every plus-money side): wins vs the no-vig price's expectation")
for k in sorted(calib):
    n, ps, w = calib[k]
    print(f"  {k[0]:9} {k[1]:5} n={n:5} won {w / n:.3f} vs priced {ps / n:.3f} ({(w - ps) / n:+.3f})")
