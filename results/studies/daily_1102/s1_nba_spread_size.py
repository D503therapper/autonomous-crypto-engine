"""11/2 #1 - NBA SPREAD SIZE: do big NBA favorites cover? Closing spread (game files) by bucket, the favorite side ATS at
its closing juice; home / road favorite; October-November vs later. Second check: the paid history's game-day MORNING
spread 2020-23 (median book, graded at -110). Train 2016-2022 seasons, held 2023 / 2024 / 2025 apart, now 2026."""
from lib import *

TRAIN, HELD = (2016, 2022), [2023, 2024, 2025, 2026]
B = [(0.5, 3.0, "01-3"), (3.5, 6.5, "03.5-6.5"), (7.0, 9.5, "07-9.5"), (10.0, 12.5, "10-12.5"), (13.0, 99, "13+")]


def bucket(x):
    for lo, hi, n in B:
        if lo <= x <= hi:
            return n
    return None


c = Cells()
fin = [g for g in finals("nba") if g["stype"] == "2"]
mo = nba_morning()
for g in fin:
    if g["sp"] is None or g["sp"] == 0:
        continue
    fav = "home" if g["sp"] < 0 else "away"
    b = bucket(abs(g["sp"]))
    p = ats(g, fav)
    if b is None or p is None:
        continue
    s = g["season"]
    where = "home fav" if fav == "home" else "road fav"
    early = "Oct-Nov" if int(g["start"][5:7]) in (10, 11) else "Dec+"
    c.add(f"close fav {b}", s, p)
    c.add(f"close fav {b} {where}", s, p)
    c.add(f"close fav {b} {early}", s, p)
    c.add("close fav ALL", s, p)
    m = mo.get(g["id"])
    if m and m.get("pt") is not None and m["pt"] != 0:
        mf = "home" if m["pt"] < 0 else "away"
        mb = bucket(abs(m["pt"]))
        r = (g["hs"] - g["as"] + m["pt"]) if mf == "home" else -(g["hs"] - g["as"] + m["pt"])
        if mb and r != 0:
            pm = profit(r > 0, dec(-110))
            c.add(f"morning fav {mb}", s, pm)
            c.add(f"morning fav {mb} {early}", s, pm)
            c.add(f"morning fav {mb} {'home fav' if mf == 'home' else 'road fav'}", s, pm)
c.dump("s1", "NBA favorite ATS by closing spread size (train 2016-22, held 2023/24/25/26 apart)", TRAIN, HELD)
