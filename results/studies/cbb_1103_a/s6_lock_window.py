"""THE OPEN DECISION (10/16): "college hoops Locks small the first 2 weeks". What a college hoops Lock can be: a
moneyline favorite -120..-150 (no Lock at -119..-101, never past -150). How that band does at the close by the
season window (days 0-7 / 8-14 / 15-28 / later) and by the FAVORITE's own game number (1-3 / 4-6 / 7-10 / 11+),
by site, and the wider -101..-150 band. Also -151..-250 (never a Lock - context). Read with s4 (b): in the first 5
games the carried ratings add NOTHING to the close (best weight -0.14, held-out +1.3 mnats only by going AGAINST them)
- so an early Lock can only stand on study weights. Train 2018-22, held out 2023 / 24 / 25 apart."""
import lib
from collections import defaultdict

rows = [r for r in lib.annotate(lib.load()) if r["season"] >= 2018]
cells = defaultdict(lib.Cell)
for r in rows:
    try:
        mh, ma = float(r["ml_home"]), float(r["ml_away"])
    except (TypeError, ValueError):
        continue
    if abs(mh) < 100 or abs(ma) < 100:
        continue
    d = r["day_in_season"]
    win = "days 0-7" if d <= 7 else ("days 8-14" if d <= 14 else ("days 15-28" if d <= 28 else "day 29+"))
    neutral = str(r["neutral"]) == "1"
    for side, odds, won in (("home", mh, r["hs"] > r["as_"]), ("away", ma, r["as_"] > r["hs"])):
        gn = r["gn_" + side]
        gb = "fav game 1-3" if gn <= 3 else ("fav game 4-6" if gn <= 6 else ("fav game 7-10" if gn <= 10 else "fav game 11+"))
        site = "neutral" if neutral else side
        s = r["season"]
        pl = lib.ml_profit(odds, won)
        if -150 <= odds <= -120:
            for lab in (win, gb, f"{win} {site}", "days 0-14" if d <= 14 else "day 15+"):
                cells[f"LOCK BAND -120..-150 | {lab}"].add(s, pl, won)
        if -150 <= odds <= -101:
            for lab in (win, "days 0-14" if d <= 14 else "day 15+", f"{'days 0-14' if d <= 14 else 'day 15+'} {site}"):
                cells[f"-101..-150 | {lab}"].add(s, pl, won)
        if -250 <= odds < -150:
            cells[f"-151..-250 (never a Lock) | {'days 0-14' if d <= 14 else 'day 15+'}"].add(s, pl, won)
print(__doc__)
for k in sorted(cells):
    print(cells[k].line(k))
