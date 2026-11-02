"""STUDY 4b - the follow-up on the one strong cell of 4 / 5: the college hoops -101..-150 FAVORITE AWAY FROM HOME (true
road or a neutral site) in November-December. The 10/30 November study had games 1-3 (-18.1% / -12.1%, a tracker lead);
this asks whether it runs through December, its dose, the conference split, the mirror (the dog across), and the spread."""
import lib

R = lib.regular(lib.build())
o = lib.Out("s4b")
ND = lambda x: x["start"][5:7] in ("11", "12")      # noqa: E731
SF = [x for x in R if x.get("ml") is not None and -150 <= x["ml"] <= -101]
AW = [x for x in SF if x["venue"] != "home"]
o.h("A. Away-from-home small favorite: Nov-Dec vs Jan-Mar, by game number")
o.c("away fav -101..-150, Nov-Dec (all)", [x for x in AW if ND(x)])
o.c("away fav -101..-150, Jan-Mar", [x for x in AW if not ND(x)])
o.c("HOME fav -101..-150, Nov-Dec", [x for x in SF if x["venue"] == "home" and ND(x)])
o.c("HOME fav -101..-150, Jan-Mar", [x for x in SF if x["venue"] == "home" and not ND(x)])
for lo, hi in ((1, 3), (4, 5), (6, 8), (9, 12), (13, 40)):
    o.c(f"away fav, Nov-Dec, team game {lo}-{hi}", [x for x in AW if ND(x) and lo <= x["gn"] <= hi])
o.h("B. Dose (price) and venue")
for lo, hi in ((-125, -101), (-150, -126)):
    o.c(f"away fav {lo}..{hi}, Nov-Dec", [x for x in AW if ND(x) and lo <= x["ml"] <= hi])
    o.c(f"away fav {lo}..{hi}, Jan-Mar", [x for x in AW if not ND(x) and lo <= x["ml"] <= hi])
o.c("ROAD (true) fav, Nov-Dec", [x for x in AW if ND(x) and x["venue"] == "away"])
o.c("NEUTRAL fav, Nov-Dec", [x for x in AW if ND(x) and x["venue"] == "neutral"])
o.c("away fav -151..-250, Nov-Dec", [x for x in R if x.get("ml") is not None and -250 <= x["ml"] <= -151 and x["venue"] != "home" and ND(x)])
o.c("away fav -151..-250, Jan-Mar", [x for x in R if x.get("ml") is not None and -250 <= x["ml"] <= -151 and x["venue"] != "home" and not ND(x)])
o.h("C. Conference game or not; months")
o.c("away fav, Nov-Dec, CONFERENCE game", [x for x in AW if ND(x) and x["same_conf"]])
o.c("away fav, Nov-Dec, non-conference", [x for x in AW if ND(x) and not x["same_conf"]])
o.c("away fav, November", [x for x in AW if x["start"][5:7] == "11"])
o.c("away fav, December", [x for x in AW if x["start"][5:7] == "12"])
o.c("away fav, January", [x for x in AW if x["start"][5:7] == "01"])
o.c("away fav, February", [x for x in AW if x["start"][5:7] == "02"])
o.c("away fav, March (regular)", [x for x in AW if x["start"][5:7] == "03"])
o.h("D. The mirror and the spread")
o.c("the DOG across (+100..+200) from an away small fav, Nov-Dec", [x for x in R if x.get("ml") is not None and 100 <= x["ml"] <= 200
                                                                   and x["venue"] != "away" and ND(x) and -150 <= (x.get("oml") or 0) <= -101])
o.c("away fav -101..-150 Nov-Dec, ATS", [x for x in AW if ND(x) and x.get("cover") is not None], lib.profit_ats)
o.c("away fav -101..-150 Jan-Mar, ATS", [x for x in AW if not ND(x) and x.get("cover") is not None], lib.profit_ats)
o.h("E. Tiers (a power road favorite vs a lower-tier host and so on)")
for t in ("power", "mid", "low"):
    o.c(f"away fav Nov-Dec, fav tier {t}", [x for x in AW if ND(x) and x["tier"] == t])
o.save()
