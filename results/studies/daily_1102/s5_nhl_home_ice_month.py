"""11/2 #5 - NHL HOME ICE BY MONTH (never cut by month: the 10/9 / 10/12 hockey studies did start times, day of the week,
homestands). Is the home side mispriced in some part of the season (October fresh legs, the December-January grind,
the March-April race)? The home side at the close by month: home dogs +100..+350, home favorites -101..-150 /
-151..-250, all home sides. Second check: the paid history's game-day MORNING price 2021-23 (median book). Train
2016-2021 seasons, held 2022 / 2023 / 2024 / 2025, now 2026."""
import importlib.util
from lib import *

TRAIN, HELD = (2016, 2021), [2022, 2023, 2024, 2025, 2026]
MON = {10: "1 Oct", 11: "2 Nov", 12: "3 Dec", 1: "4 Jan", 2: "5 Feb", 3: "6 Mar", 4: "7 Apr"}


def morning():
    cache = os.path.join(CACHE, "_nhl_morning.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    spec = importlib.util.spec_from_file_location("nhlodds", os.path.join(ROOT, "results/studies/nhl_odds_1102/lib.py"))
    m = importlib.util.module_from_spec(spec)
    here = os.getcwd()
    spec.loader.exec_module(m)
    os.chdir(here)
    looks = m.odds_by_game()
    fin = finals("nhl")
    names = {g["hn"] for g in fin if g["hn"]}
    by = {}
    for g in fin:
        by.setdefault((g["hn"], g["an"], g["start"][:10]), []).append(g)
    out = {}
    for (h, a, tip), ls in looks.items():
        hn, an = m.nick(h, names), m.nick(a, names)
        mor = [c for hb, c in ls if hb < 20]
        if not hn or not an or not mor:
            continue
        for g in by.get((hn, an, tip[:10]), []):
            out[g["id"]] = mor[-1]
    pickle.dump(out, open(cache, "wb"))
    return out


c = Cells()
mo = morning()
print("morning-matched games:", len(mo))
for g in finals("nhl"):
    if g["stype"] != "2" or g["neutral"]:
        continue
    mon = int(g["start"][5:7])
    if mon not in MON:
        continue
    s = g["season"]
    m = MON[mon]
    o = g["mlh"]
    won = g["hs"] > g["as"]
    p = profit(won, dec(o))
    band = ("home DOG" if dog_band(o) else "home FAV -101..-150" if -150 <= o <= -101 else
            "home FAV -151..-250" if -250 <= o <= -151 else None)
    c.add(f"{m} home ALL", s, p)
    if band:
        c.add(f"{m} {band}", s, p)
    c.add(f"{m} road ALL", s, profit(not won, dec(g["mla"])))
    x = mo.get(g["id"])
    if x:
        c.add(f"{m} morning home ALL", s, profit(won, x["dh"]))
        c.add(f"{m} morning road ALL", s, profit(not won, x["da"]))
c.dump("s5", "NHL home side by month at the close (train 2016-21, held 2022-26 apart) + the 2021-23 morning", TRAIN, HELD)
