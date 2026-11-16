"""11/16 FABLE - WHY WE LOSE, Q4b's second check: the NFL Monday / Thursday spread FAVORITE on nflverse's schedule
file (closing spreads 2006-26, regular season) - the side the night LEAN takes when it reads the favorite. Graded at
the file's own spread prices when it has them, else -110. Train 2006-16 / held 2017-26."""
import csv, os, random
from collections import defaultdict

P = os.path.join(os.path.expanduser("~"), ".cache", "d503_spreads2_1111", "dl", "games.csv")


def f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


rows = []
for r in csv.DictReader(open(P)):
    hs, as_, sl = f(r["home_score"]), f(r["away_score"]), f(r["spread_line"])
    if hs is None or as_ is None or sl is None or r["game_type"] != "REG" or sl == 0:
        continue
    m = hs - as_
    ho, ao = f(r.get("home_spread_odds")) or -110, f(r.get("away_spread_odds")) or -110
    home_fav = sl > 0                                  # nflverse: + = the home team lays the points
    cover_home = m - sl                                # > 0 the home side covers
    if cover_home == 0:
        continue
    for side, fav, won, odds in (("home", home_fav, cover_home > 0, ho), ("away", not home_fav, cover_home < 0, ao)):
        rows.append({"season": int(r["season"]), "wd": r["weekday"], "side": side, "fav": fav, "won": won, "dec": dec(odds),
                     "pts": abs(sl), "div": r["div_game"] == "1"})


def cell(n, x):
    if len(x) < 20:
        print(f"  {n:56s} n {len(x)}")
        return
    roi = lambda y: sum((r["dec"] - 1) if r["won"] else -1 for r in y) / max(1, len(y))
    tr = [r for r in x if r["season"] <= 2016]
    he = [r for r in x if r["season"] >= 2017]
    l3 = [r for r in x if r["season"] >= 2023]
    by = defaultdict(list)
    for r in x:
        by[r["season"]].append(r)
    w = sum(r["won"] for r in x)
    z = (w - len(x) / 2) / (len(x) / 4) ** 0.5
    print(f"  {n:56s} {w:4d}-{len(x) - w:<4d} {w / len(x):5.1%} {roi(x):+6.1%} z {z:+5.2f} | 2006-16 {roi(tr):+6.1%} on {len(tr):4d} | 2017-26 {roi(he):+6.1%} on {len(he):4d} "
          f"| 2023-26 {roi(l3):+6.1%} on {len(l3):3d} | seasons up {sum(roi(v) > 0 for v in by.values())}/{len(by)}")
    return roi(x)


fav = [r for r in rows if r["fav"]]
print("the spread FAVORITE, regular season 2006-26")
cell("every game", fav)
for wd in ("Sunday", "Monday", "Thursday", "Saturday"):
    cell(wd, [r for r in fav if r["wd"] == wd])
night = [r for r in fav if r["wd"] in ("Monday", "Thursday")]
cell("Monday + Thursday", night)
cell("   laying under 3.5", [r for r in night if r["pts"] < 3.5])
cell("   laying 3.5-6.5", [r for r in night if 3.5 <= r["pts"] < 7])
cell("   laying 7+", [r for r in night if r["pts"] >= 7])
cell("   home favorite", [r for r in night if r["side"] == "home"])
cell("   road favorite", [r for r in night if r["side"] == "away"])
cell("   division game", [r for r in night if r["div"]])
cell("   not a division game", [r for r in night if not r["div"]])
random.seed(3)
roi = lambda y: sum((r["dec"] - 1) if r["won"] else -1 for r in y) / len(y)
t = roi(night)
hit = sum(roi(random.sample(fav, len(night))) <= t for _ in range(2000))
print(f"  placebo: a random {len(night)} spread favorites did as badly as the Monday / Thursday ones {hit} of 2000 (cell {t:+.1%}, every favorite {roi(fav):+.1%})")
