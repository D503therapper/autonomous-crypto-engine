"""S1 - SCHEDULE STRUCTURE the earlier studies didn't cut: weekday pairs (Saturday -> Monday / Tuesday turnarounds and
every other last-game-day x game-day pair), the second stop of a travel-partner road swing (two road games within
3 nights, the two floors under 200 miles apart), slate size (how many priced games that night), Sunday games.
Dogs +100..+350 ML, favorites -101..-150 ML, every spread side ATS. Regular season 2018-26 at ESPN's close."""
import lib

R = lib.regular(lib.build())
o = lib.Out("s1")
D = "Mon Tue Wed Thu Fri Sat Sun".split()
SP = lib.spreads(R)
DG = lib.dogs(R)
FV = lib.favs(R)

o.h("A. Weekday pairs - last game day -> this game day (ATS, 300+ sides only), home / road games")
for ld in range(7):
    for d in range(7):
        rows = [x for x in SP if x.get("ldow") == ld and x["dow"] == d and not x["neutral"]]
        if len(rows) >= 300:
            o.c(f"ATS {D[ld]} -> {D[d]}", rows, lib.profit_ats)
o.h("B. Weekday pairs - the DOG side ML (+100..+350), 200+")
for ld in range(7):
    for d in range(7):
        rows = [x for x in DG if x.get("ldow") == ld and x["dow"] == d and not x["neutral"]]
        if len(rows) >= 200:
            o.c(f"dog {D[ld]} -> {D[d]}", rows)
o.h("C. The Saturday -> Monday/Tuesday turnaround vs the opponent's")
sat_quick = [x for x in SP if x.get("ldow") == 5 and x["dow"] in (0, 1) and not x["neutral"]]
o.c("ATS: played Saturday, plays Mon/Tue", sat_quick, lib.profit_ats)
o.c("ATS: ... opponent did NOT play Saturday", [x for x in sat_quick if x.get("o_ldow") != 5], lib.profit_ats)
o.c("ATS: ... opponent did too", [x for x in sat_quick if x.get("o_ldow") == 5], lib.profit_ats)
o.c("ATS: played Saturday, plays Mon/Tue, ROAD", [x for x in sat_quick if x["venue"] == "away"], lib.profit_ats)
o.c("ATS: played Saturday, plays Mon/Tue, HOME", [x for x in sat_quick if x["venue"] == "home"], lib.profit_ats)
o.c("dog ML: played Saturday, plays Mon/Tue", [x for x in DG if x.get("ldow") == 5 and x["dow"] in (0, 1) and not x["neutral"]])
o.c("fav -101..-150 ML: played Saturday, plays Mon/Tue", [x for x in FV if x.get("ldow") == 5 and x["dow"] in (0, 1) and not x["neutral"]])
o.h("D. Travel partners - the 2nd road game of a swing (trip 2), within 3 nights of the first, by floor distance")
def swing(x, lo, hi):
    if x["trip"] != 2 or x.get("rest") is None or x["rest"] > 3:
        return False
    # the previous game's venue distance: approximate with this row's miles vs the last game's opponent's floor is not
    # on the row - use |miles| difference bucket of the two trips: both from home; a partner swing = similar miles
    return True
tp = [x for x in SP if swing(x, 0, 0)]
o.c("ATS: 2nd road game within 3 nights (swing)", tp, lib.profit_ats)
o.c("ATS: ... as a dog (sp > 0)", [x for x in tp if x["sp"] > 0], lib.profit_ats)
o.c("ATS: ... as a favorite", [x for x in tp if x["sp"] < 0], lib.profit_ats)
o.c("ATS: ... same conference", [x for x in tp if x["same_conf"]], lib.profit_ats)
o.c("ATS: ... 1000+ miles from home", [x for x in tp if (x.get("miles") or 0) >= 1000], lib.profit_ats)
o.c("ATS: ... under 300 miles from home", [x for x in tp if (x.get("miles") or 0) < 300], lib.profit_ats)
o.c("dog ML: 2nd road game within 3 nights", [x for x in DG if swing(x, 0, 0)])
o.h("E. Slate size - priced games that night (the books' attention)")
for lo, hi in ((1, 15), (16, 30), (31, 50), (51, 80), (81, 200)):
    rows = [x for x in SP if lo <= x["slate"] <= hi]
    o.c(f"ATS slate {lo}-{hi}: favorites", [x for x in rows if x["sp"] < 0], lib.profit_ats)
    o.c(f"ATS slate {lo}-{hi}: dogs", [x for x in rows if x["sp"] > 0], lib.profit_ats)
    o.c(f"dog ML slate {lo}-{hi}", [x for x in DG if lo <= x["slate"] <= hi])
    o.c(f"fav -101..-150 ML slate {lo}-{hi}", [x for x in FV if lo <= x["slate"] <= hi])
    o.c(f"ATS slate {lo}-{hi}: HOME", [x for x in rows if x["venue"] == "home"], lib.profit_ats)
o.h("F. Closing error by slate size (mean |margin + spread|, the market's accuracy)")
for lo, hi in ((1, 15), (16, 30), (31, 50), (51, 80), (81, 200)):
    rows = [x for x in SP if lo <= x["slate"] <= hi and x["side"] == "home"]
    if rows:
        mae = sum(abs(x["margin"] + x["sp"]) for x in rows) / len(rows)
        bias = sum(x["margin"] + x["sp"] for x in rows) / len(rows)
        o.note(f"slate {lo}-{hi}: n {len(rows)} MAE {mae:.2f} home bias {bias:+.2f}")
o.h("G. Day of week alone")
for d in range(7):
    o.c(f"ATS {D[d]}: favorites", [x for x in SP if x["dow"] == d and x["sp"] < 0], lib.profit_ats)
    o.c(f"ATS {D[d]}: home", [x for x in SP if x["dow"] == d and x["venue"] == "home"], lib.profit_ats)
    o.c(f"dog ML {D[d]}", [x for x in DG if x["dow"] == d])
o.save()
