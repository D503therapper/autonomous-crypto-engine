"""S1b - the other raw-clock read on the board: THE WEST COAST ROAD FAVORITE IN AN EASTERN CITY (sports.weigh_west_coast_road_fav,
+2 points on the favorite's read, -2 on the home dog's score). Live: the road team's home offset (mode of the raw tzo)
<= -7 and the venue's raw offset >= -5 - before the clocks change that is a Pacific / Arizona team at an Eastern OR A
CENTRAL venue, after it an Eastern venue only. nflverse's closes 2006-26, the road favorite -150..-101 (the band the
weight reads) and every road favorite."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h
import nflv

G = nflv.games()
o = h.Out("s1b_west_fav", (2006, 2016), tuple(range(2017, 2027)))
o.p(__doc__)
WEST = ("SEA", "SF", "LA", "LAC", "SD", "OAK", "LV", "ARI")        # the live rule's -7 teams (the Broncos read -6)
for g in G:
    if g["neutral"] or g["hs"] == g["as"]:
        continue
    oa = g["mla"]
    if oa >= 0:
        continue
    pr, s = nflv.ml_profit(g, "away"), g["season"]
    vz = nflv.ZONE[g["home"]]
    rawv = nflv.raw(g["home"], g["day"])
    live = g["away"] in WEST and rawv >= -5
    for nm, ok in (("fav -150..-101", -150 <= oa <= -101), ("any road favorite", True)):
        if not ok:
            continue
        o.add(f"{nm}: every one", s, pr, oa)
        if live:
            o.add(f"{nm}: THE LIVE RULE", s, pr, oa)
        if g["away"] in WEST and vz == -5:
            o.add(f"{nm}: West team at an EASTERN venue", s, pr, oa)
        if g["away"] in WEST and vz == -6:
            o.add(f"{nm}: West team at a CENTRAL venue", s, pr, oa)
        if g["away"] in WEST and vz == -6 and live:
            o.add(f"{nm}: West at Central, live (before the clocks change)", s, pr, oa)
        if g["away"] in WEST and vz == -5 and g["et"] is not None and g["et"] < 14:
            o.add(f"{nm}: West team at an Eastern venue, 1 PM ET kick", s, pr, oa)
    # the home dog across it
    oh = g["mlh"]
    if 100 <= oh <= 350:
        ph = nflv.ml_profit(g, "home")
        o.add("home dog +100..+350: every one", s, ph, oh)
        if g["away"] in WEST and vz == -5:
            o.add("home dog +100..+350: vs a West team, EASTERN venue", s, ph, oh)
        if g["away"] in WEST and vz == -6:
            o.add("home dog +100..+350: vs a West team, CENTRAL venue", s, ph, oh)
o.show()
o.placebo("fav -150..-101: West team at an EASTERN venue", "fav -150..-101: every one")
o.placebo("any road favorite: West team at an EASTERN venue", "any road favorite: every one")
o.placebo("any road favorite: West team at a CENTRAL venue", "any road favorite: every one")
o.save()
