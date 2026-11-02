"""11/2 #7 - FOOTBALL SPREAD SIZE: do big favorites cover, NFL + college? (the 10/16 college 'cover margin' and 10/8 key
numbers were other questions; 'big spreads' was one row of an early explorer.) The favorite ATS by the size of the
spread - at the paid history's FIRST FAIR spread (median book, its juice) and at the close (game file, its juice);
home / road favorite; college November (the late-season big favorite) apart. Train 2016-2022 (the paid history
2020-22), held 2023 / 2024 / 2025, now 2026."""
from lib import *

TRAIN, HELD = (2016, 2022), [2023, 2024, 2025, 2026]
BK = {"nfl": [(0.5, 2.5, "a 1-2.5"), (3, 3, "b 3"), (3.5, 6.5, "c 3.5-6.5"), (7, 7, "d 7"), (7.5, 9.5, "e 7.5-9.5"),
              (10, 13.5, "f 10-13.5"), (14, 99, "g 14+")],
      "ncaaf": [(0.5, 6.5, "a 1-6.5"), (7, 13.5, "b 7-13.5"), (14, 20.5, "c 14-20.5"), (21, 27.5, "d 21-27.5"),
                (28, 99, "e 28+")]}


def bucket(lg, x):
    for lo, hi, n in BK[lg]:
        if lo <= x <= hi:
            return n
    return None


c = Cells()
for lg in ("nfl", "ncaaf"):
    xby = {x["id"]: x for x in load_football(lg)}
    for g in finals(lg):
        if g["stype"] != "2" or g["sp"] is None or g["sp"] == 0:
            continue
        s = g["season"]
        fav = "home" if g["sp"] < 0 else "away"
        b = bucket(lg, abs(g["sp"]))
        p = ats(g, fav)
        if b is None or p is None:
            continue
        nov = int(g["start"][5:7]) >= 11 or int(g["start"][5:7]) == 1
        where = "neutral" if g["neutral"] else ("home fav" if fav == "home" else "road fav")
        c.add(f"{lg} close fav {b}", s, p)
        c.add(f"{lg} close fav {b} {where}", s, p)
        if lg == "ncaaf":
            c.add(f"{lg} close fav {b} {'Nov+' if nov else 'Sep-Oct'}", s, p)
        x = xby.get(g["id"])
        f = first_fair(x["sp"]) if x else None
        if f:
            hp, hpr, apr = sp_med(f[1])
            if hp:
                ef_fav = "home" if hp < 0 else "away"
                eb = bucket(lg, abs(hp))
                r = (g["hs"] - g["as"] + hp) if ef_fav == "home" else -(g["hs"] - g["as"] + hp)
                if eb and r != 0:
                    pe = profit(r > 0, hpr if ef_fav == "home" else apr)
                    c.add(f"{lg} first-fair fav {eb}", s, pe)
                    if lg == "ncaaf":
                        c.add(f"{lg} first-fair fav {eb} {'Nov+' if nov else 'Sep-Oct'}", s, pe)
c.dump("s7", "Football favorite ATS by spread size (close + first fair; train 2016-22, held 2023-26 apart)", TRAIN, HELD)
