"""S3 / S4 / S9 - NFL NIGHT GAMES (the Monday / Thursday night pick posts every week). Untested here before: the 10/9
study read the game AFTER a Thursday game, 10/19 the game after / before a Monday or Thursday, 10/? 'primetime splits'
the night slot by itself (flips) - none cut the body clock, the short-week trip, or the night TOTAL.
 S3 THE BODY CLOCK AT NIGHT: a Pacific-zone team (home longitude west of -114) vs an Eastern-zone team (east of -86.5)
    at a kickoff 7 PM ET or later (the West team's body says 4-5 PM) - the West side's ML (dog / favorite) and ATS, at
    the close and at the paid history's FIRST FAIR number; the control = the same pairing in a day game.
 S4 THE SHORT-WEEK TRIP: the Thursday night ROAD team by the miles from its home to tonight's venue (under 800 /
    800-1,500 / 1,500+), and the road team that was ALSO on the road the Sunday before (two trips in 5 days).
 S9 THE NIGHT TOTAL: the under (and over) at the closing total in Thursday / Monday / Sunday night games vs day games,
    and the Thursday under when both teams played on the road last week / the total is 47+.
Regular season 2018-26; TRAIN 2018-22, HELD 2023 / 2024 / 2025, 2026 live. ET = UTC-4 Mar-first week of Nov, else UTC-5."""
from datetime import datetime, timedelta
import lib

LG = "nfl"
fin = [g for g in lib.finals(LG) if g["stype"] == "2"]
co = lib.coords(LG)
hc = lib.home_coords(LG, fin, co)
xs = {x["id"]: x for x in lib.load_football(LG)}
tl = lib.team_log(fin)


def et(start):
    t = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
    dst = (3 <= t.month <= 10) or (t.month == 11 and t.day <= 7)
    return t - timedelta(hours=4 if dst else 5)


def zone(season, team):
    w = hc.get((season, team))
    if not w:
        return None
    lon = w[1]
    return "P" if lon < -114 else ("E" if lon > -86.5 else "M/C")


cells = lib.Cells()
for g in fin:
    s = g["season"]
    t = et(g["start"])
    night = t.hour >= 19 or t.hour < 4
    wd = t.weekday()            # Mon 0 .. Sun 6
    slot = ("THU night" if wd == 3 else "MON night" if wd == 0 else "SUN night" if wd == 6 else "other night") if night else "day"
    # ---- S9 totals
    for over in (False, True):
        p = lib.tot_profit(g, over)
        nm = "OVER" if over else "UNDER"
        cells.add(f"S9 {nm} | {slot}", s, p)
        if night and wd in (0, 3):
            cells.add(f"S9 {nm} | MON+THU night", s, p)
            if g["total"] is not None and g["total"] >= 47:
                cells.add(f"S9 {nm} | MON+THU night, total 47+", s, p)
            elif g["total"] is not None and g["total"] <= 41:
                cells.add(f"S9 {nm} | MON+THU night, total 41-", s, p)
    if night and wd == 3:
        ph = lib.before(tl, g["home"], g["start"], 1)
        pa = lib.before(tl, g["away"], g["start"], 1)
        if ph and pa and ph[0]["away"] == g["home"] and pa[0]["away"] == g["away"]:
            cells.add("S9 UNDER | THU night, both on the road last week", s, lib.tot_profit(g, False))
    # ---- S3 body clock
    zh, za = zone(s, g["home"]), zone(s, g["away"])
    if {zh, za} == {"P", "E"}:
        for side, team, opp, o, won, home in lib.sides(g):
            if zone(s, team) != "P":
                continue
            lab = "NIGHT 7PM+ ET" if night else "DAY"
            where = "home" if home else "road"
            kind = "dog" if o >= 100 else "fav"
            pl = lib.profit(won, lib.dec(o))
            cells.add(f"S3 West team vs East team | {lab} | ML all", s, pl)
            cells.add(f"S3 West team vs East team | {lab} | ML {kind}", s, pl)
            cells.add(f"S3 West team vs East team | {lab} | {where} ML", s, pl)
            cells.add(f"S3 West team vs East team | {lab} | ATS", s, lib.ats(g, side))
            ep = lib.early_price(xs, g["id"], side)
            if ep:
                cells.add(f"S3 West team vs East team | {lab} | ML first fair", s, lib.profit(won, ep[1]))
    # ---- S4 the Thursday road team's trip
    if night and wd == 3 and not g["neutral"]:
        v = co.get(g["id"])
        h = hc.get((s, g["away"]))
        if v and h:
            mi = lib.miles(h, v)
            band = "under 800 mi" if mi < 800 else ("800-1,500 mi" if mi < 1500 else "1,500+ mi")
            o = g["mla"]
            won = g["as"] > g["hs"]
            pl = lib.profit(won, lib.dec(o))
            kind = "dog" if o >= 100 else "fav"
            cells.add(f"S4 THU road team | {band} | ATS", s, lib.ats(g, "away"))
            cells.add(f"S4 THU road team | {band} | ML {kind}", s, pl)
            ep = lib.early_price(xs, g["id"], "away")
            if ep:
                cells.add(f"S4 THU road team | {band} | ML first fair", s, lib.profit(won, ep[1]))
            pa = lib.before(tl, g["away"], g["start"], 1)
            if pa and pa[0]["away"] == g["away"] and lib.days_between(pa[0]["start"], g["start"]) <= 5:
                cells.add("S4 THU road team, ALSO on the road last Sunday | ATS", s, lib.ats(g, "away"))
                cells.add(f"S4 THU road team, ALSO on the road last Sunday | ML {kind}", s, pl)
                cells.add("S4 THU HOME team vs a road-road visitor | ATS", s, lib.ats(g, "home"))
            elif pa:
                cells.add("S4 THU road team, home last Sunday | ATS", s, lib.ats(g, "away"))
                cells.add(f"S4 THU road team, home last Sunday | ML {kind}", s, pl)
cells.dump("s3_s4_s9", "S3 / S4 / S9 - NFL night games: the body clock, the Thursday trip, the night total",
           (2018, 2022), (2023, 2024, 2025, 2026))
