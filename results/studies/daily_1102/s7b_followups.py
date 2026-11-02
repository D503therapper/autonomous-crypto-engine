"""11/2 #7b - the two s7 cells that looked steady, from the side we could actually lean:
(a) the NFL DOG getting 7.5-9.5 (ATS at the close / first fair, and its moneyline +100..+350);
(b) the college small favorite (1-6.5) in November: its moneyline -101..-250 by month (Sep-Oct vs Nov+), and the dog
across it."""
from lib import *

TRAIN, HELD = (2016, 2022), [2023, 2024, 2025, 2026]
c = Cells()
for lg in ("nfl", "ncaaf"):
    xby = {x["id"]: x for x in load_football(lg)}
    for g in finals(lg):
        if g["stype"] != "2" or g["sp"] is None or g["sp"] == 0:
            continue
        s = g["season"]
        fav = "home" if g["sp"] < 0 else "away"
        dog = "away" if fav == "home" else "home"
        a = abs(g["sp"])
        nov = int(g["start"][5:7]) >= 11 or int(g["start"][5:7]) == 1
        fo = g["mlh"] if fav == "home" else g["mla"]
        do = g["mla"] if fav == "home" else g["mlh"]
        fw = (g["hs"] > g["as"]) == (fav == "home")
        if lg == "nfl" and 7.5 <= a <= 9.5:
            c.add("nfl DOG +7.5..+9.5 ATS close", s, ats(g, dog))
            if dog_band(do):
                c.add("nfl DOG +7.5..+9.5 moneyline", s, profit(not fw, dec(do)))
        if lg == "nfl" and (a in (7.0,) or 3.5 <= a <= 6.5 or 10 <= a <= 13.5):
            c.add(f"nfl DOG ATS close {'+7' if a == 7 else '+3.5..+6.5' if a < 7 else '+10..+13.5'}", s, ats(g, dog))
        if lg == "nfl":
            x = xby.get(g["id"])
            f = first_fair(x["sp"]) if x else None
            if f:
                hp, hpr, apr = sp_med(f[1])
                if hp and 7.5 <= abs(hp) <= 9.5:
                    ed = "away" if hp < 0 else "home"
                    r = -(g["hs"] - g["as"] + hp) if ed == "away" else (g["hs"] - g["as"] + hp)
                    if r != 0:
                        c.add("nfl first-fair DOG +7.5..+9.5 ATS", s, profit(r > 0, apr if ed == "away" else hpr))
        if lg == "ncaaf" and 1 <= a <= 6.5:
            k = "Nov+" if nov else "Sep-Oct"
            if -150 <= fo <= -101:
                c.add(f"ncaaf small fav ML -101..-150 {k}", s, profit(fw, dec(fo)))
            elif -250 <= fo <= -151:
                c.add(f"ncaaf small fav ML -151..-250 {k}", s, profit(fw, dec(fo)))
            if dog_band(do):
                c.add(f"ncaaf DOG across a small fav {k}", s, profit(not fw, dec(do)))
            c.add(f"ncaaf DOG +1..+6.5 ATS {k}", s, ats(g, dog))
c.dump("s7b", "s7 follow-ups: NFL +7.5..+9.5 dogs, college small favorites by month", TRAIN, HELD)
