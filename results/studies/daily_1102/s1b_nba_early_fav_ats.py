"""11/2 #1b - the one s1 cell that looked steady: the NBA favorite laying 3.5-12.5 in October-November, pooled, its DOG
side (what we could actually lean), by game number of the season, and at the 2020-23 morning number."""
from lib import *

TRAIN, HELD = (2016, 2022), [2023, 2024, 2025, 2026]
c = Cells()
fin = [g for g in finals("nba") if g["stype"] == "2"]
tl = team_log(fin)
mo = nba_morning()
for g in fin:
    if g["sp"] is None or not 3.5 <= abs(g["sp"]) <= 12.5:
        continue
    mon = int(g["start"][5:7])
    fav = "home" if g["sp"] < 0 else "away"
    dog = "away" if fav == "home" else "home"
    s = g["season"]
    gn = len([x for x in before(tl, g[fav], g["start"]) if x["season"] == s])
    win = "Oct-Nov" if mon in (10, 11) else ("Dec" if mon == 12 else "Jan+")
    pf, pd = ats(g, fav), ats(g, dog)
    c.add(f"fav 3.5-12.5 {win}", s, pf)
    c.add(f"DOG +3.5-12.5 {win}", s, pd)
    gb = "g01-10" if gn < 10 else ("g11-20" if gn < 20 else "g21+")
    c.add(f"fav 3.5-12.5 {gb}", s, pf)
    c.add(f"DOG +3.5-12.5 {gb}", s, pd)
    m = mo.get(g["id"])
    if m and m.get("pt") is not None and 3.5 <= abs(m["pt"]) <= 12.5:
        mf = "home" if m["pt"] < 0 else "away"
        r = (g["hs"] - g["as"] + m["pt"]) if mf == "home" else -(g["hs"] - g["as"] + m["pt"])
        if r != 0:
            c.add(f"morning fav 3.5-12.5 {win}", s, profit(r > 0, dec(-110)))
            c.add(f"morning DOG 3.5-12.5 {win}", s, profit(r < 0, dec(-110)))
c.dump("s1b", "NBA favorite 3.5-12.5 ATS by month / game number (train 2016-22, held 2023-26 apart)", TRAIN, HELD)
