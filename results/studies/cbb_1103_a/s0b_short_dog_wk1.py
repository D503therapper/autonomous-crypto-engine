"""s0 follow-up: the one s0 cell over |z| 2 that pays - college hoops SHORT dogs (+100..+150) in OPENING WEEK
(+14.6% on 273, train +12.2% 3/5 up, held +21.0% 3/3 up). Robustness: the window (days 0-3 / 0-7 / 0-10 / 0-14),
the band edges, the site, D1 vs D1 only, and the OPEN price (2023-25, the second check). ~50 s0 cells -> 2-3 clear
|z| 2 by luck; this one has to hold its neighbours to be more than that."""
import lib
from collections import defaultdict

rows = lib.annotate(lib.load())
cells = defaultdict(lib.Cell)
for r in rows:
    if r["season"] < 2018 or not r["ml_home"] or not r["ml_away"]:
        continue
    try:
        mh, ma = float(r["ml_home"]), float(r["ml_away"])
    except ValueError:
        continue
    neutral = str(r["neutral"]) == "1"
    d = r["day_in_season"]
    for side, odds, won in (("home", mh, r["hs"] > r["as_"]), ("away", ma, r["as_"] > r["hs"])):
        s = r["season"]
        site = "neutral" if neutral else side
        both_d1 = r["d1_home"] and r["d1_away"]
        for lo, hi in ((100, 130), (100, 150), (100, 175), (131, 175), (151, 200)):
            if lo <= odds <= hi:
                for wlab, wmax in (("days 0-3", 3), ("days 0-7", 7), ("days 0-10", 10), ("days 0-14", 14), ("days 15-30", 30)):
                    if (wmax == 30 and 15 <= d <= 30) or (wmax != 30 and d <= wmax):
                        cells[f"+{lo}..+{hi} {wlab}"].add(s, lib.ml_profit(odds, won), won)
                        if lo == 100 and hi == 150 and wmax == 7:
                            cells[f"+100..+150 days 0-7 {site}"].add(s, lib.ml_profit(odds, won), won)
                            cells[f"+100..+150 days 0-7 both D1={both_d1}"].add(s, lib.ml_profit(odds, won), won)
        oo = r.get(f"ml_{side}_open")
        if oo and d <= 7:
            try:
                oo = float(oo)
            except ValueError:
                oo = None
            if oo and 100 <= oo <= 150:
                cells["OPEN +100..+150 days 0-7 (bet at the open)"].add(s, lib.ml_profit(oo, won), won)
                cells["OPEN +100..+150 days 0-7 (same sides, at the close)"].add(s, lib.ml_profit(odds, won), won)
print(__doc__)
for k in sorted(cells):
    print(cells[k].line(k))
