"""STUDY 4c - the cold college hoops dog (study 4: a dog on a 5+ losing streak in Jan-Mar -22.6% on 970, 0 of 5 / 0 of 3):
the dose by streak length, by price band (a long skid = a long price - same-band comparison), by record, and Nov-Dec."""
import lib

R = lib.regular(lib.build())
o = lib.Out("s4c")
JM = [x for x in lib.dogs(R) if x["start"][5:7] not in ("11", "12")]
o.h("A. Jan-Mar dogs +100..+350 by this season's streak (- = losing)")
for lo, hi in ((1, 99), (-2, -1), (-3, -3), (-4, -4), (-5, -5), (-7, -6), (-99, -8)):
    o.c(f"streak {lo}..{hi}", [x for x in JM if lo <= x["streak"] <= hi])
o.c("ALL SEASON: 5+ skid dog", [x for x in lib.dogs(R) if x["streak"] <= -5])
o.c("Nov-Dec: 5+ skid dog", [x for x in lib.dogs(R) if x["streak"] <= -5 and x["start"][5:7] in ("11", "12")])
o.h("B. Same price band: 5+ skid vs not")
for lo, hi in ((100, 159), (160, 249), (250, 350)):
    o.c(f"+{lo}..+{hi}, 5+ skid", [x for x in JM if lo <= x["ml"] <= hi and x["streak"] <= -5])
    o.c(f"+{lo}..+{hi}, no 5+ skid", [x for x in JM if lo <= x["ml"] <= hi and x["streak"] > -5])
o.h("C. Record (win % this season, 8+ games) - Jan-Mar dogs")
for lo, hi in ((0, 0.3), (0.3, 0.45), (0.45, 1.01)):
    o.c(f"win % {lo}-{hi}, 8+ games", [x for x in JM if x["gn"] >= 9 and lo <= (x["wpct"] or 0) < hi])
o.c("under .300 AND a 5+ skid", [x for x in JM if x["gn"] >= 9 and (x["wpct"] or 0) < 0.3 and x["streak"] <= -5])
o.c("5+ skid, .300 or better", [x for x in JM if x["gn"] >= 9 and (x["wpct"] or 0) >= 0.3 and x["streak"] <= -5])
o.h("D. Home / road, and the favorite across")
o.c("5+ skid dog at home", [x for x in JM if x["streak"] <= -5 and x["venue"] == "home"])
o.c("5+ skid dog on the road / neutral", [x for x in JM if x["streak"] <= -5 and x["venue"] != "home"])
o.c("the FAVORITE across a 5+ skid dog (-101..-400), Jan-Mar", [x for x in R if x["start"][5:7] not in ("11", "12")
                                                                  and x.get("ml") is not None and -400 <= x["ml"] <= -101
                                                                  and x["ostreak"] <= -5])
o.c("5+ skid dog, ATS (Jan-Mar)", [x for x in lib.spreads(R) if x["start"][5:7] not in ("11", "12") and x["streak"] <= -5
                                   and x["sp"] > 0], lib.profit_ats)
o.save()
