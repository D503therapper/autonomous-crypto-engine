"""S10 - COLLEGE FOOTBALL 'AFTER DARK': the EASTERN-zone team (home longitude east of -86.5) playing in a Pacific-zone
venue (west of -114) at a LATE kickoff (9:30 PM ET or later - its body says it's past 10 PM) vs the same trip at an
earlier kickoff; and the Pacific-zone team going East for an EARLY kickoff (noon ET or earlier - its body says 9 AM).
Never cut before (the NFL East-West early spot is the NFL's Sunday trip; S3 is the NFL night slot). Cells: the
traveler's ML as a dog +100..+350 / favorite -101..-250 at the close and at the paid history's FIRST FAIR number, and
ATS. Both teams FBS-ish (20+ games on file over the seasons? no - every game with a close). TRAIN 2018-22, HELD 2023 /
2024 / 2025, 2026 live."""
from datetime import datetime, timedelta
import lib

LG = "ncaaf"
fin = [g for g in lib.finals(LG) if g["stype"] == "2"]
co = lib.coords(LG)
hc = lib.home_coords(LG, fin, co)
xs = {x["id"]: x for x in lib.load_football(LG)}


def et(start):
    t = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
    dst = (3 <= t.month <= 10) or (t.month == 11 and t.day <= 7)
    return t - timedelta(hours=4 if dst else 5)


def zone_lon(lon):
    return "P" if lon < -114 else ("E" if lon > -86.5 else "M/C")


cells = lib.Cells()
for g in fin:
    if g["neutral"]:
        continue
    v = co.get(g["id"])
    if not v:
        continue
    s = g["season"]
    t = et(g["start"])
    hr = t.hour + t.minute / 60 + (24 if t.hour < 5 else 0)
    vz = zone_lon(v[1])
    for side, team, opp, o, won, home in lib.sides(g):
        if home:
            continue
        h = hc.get((s, team))
        if not h:
            continue
        tz = zone_lon(h[1])
        lab = None
        if tz == "E" and vz == "P":
            lab = "East team in the West, kick 9:30 PM ET+" if hr >= 21.5 else "East team in the West, earlier kick"
        elif tz == "P" and vz == "E":
            lab = "West team in the East, kick noon ET or earlier" if hr <= 12.5 else "West team in the East, later kick"
        if not lab:
            continue
        pl = lib.profit(won, lib.dec(o))
        if lib.dog_band(o):
            cells.add(f"{lab} | DOG", s, pl)
        elif -250 <= o <= -101:
            cells.add(f"{lab} | FAV", s, pl)
        cells.add(f"{lab} | ML any price", s, pl)
        cells.add(f"{lab} | ATS", s, lib.ats(g, side))
        ep = lib.early_price(xs, g["id"], side)
        if ep and 100 <= ep[0] <= 350:
            cells.add(f"{lab} | DOG first fair", s, lib.profit(won, ep[1]))
cells.dump("s10", "S10 - college football body clock: the cross-country traveler by kickoff time (ET)",
           (2018, 2022), (2023, 2024, 2025, 2026))
