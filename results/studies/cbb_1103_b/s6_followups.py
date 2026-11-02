"""Follow-ups on the cells of 1-5 that stood out (each its own dose / robustness read before anything is wired):
(a) the college hoops UPSET HANGOVER - a dog again right after winning as a +200 dog (the built hangover covers NFL /
    college football / MLB, not hoops); the dose by the upset's price and the gap since;
(b) the conference-tournament RUBBER MATCH dog (3rd meeting after a split);
(c) the rested side vs a team on 2-in-3 (ATS);
(d) the dog off beating a ranked team in Nov-Dec (study 3's small cell)."""
import lib

ALL = lib.build()
R = lib.regular(ALL)
o = lib.Out("s6")


def prev(x):
    return ALL[x["prev_i"]] if x.get("prev_i") is not None else None


D = lib.dogs(R)
o.h("(a) THE HANGOVER - a dog +100..+350 whose last game was a win as a dog")
o.c("every dog (base)", D)
o.c("dog, last game a LOSS", [x for x in D if prev(x) and not prev(x)["won"]])
o.c("dog, last game a win as a favorite", [x for x in D if prev(x) and prev(x)["won"] and (prev(x).get("ml") or -1) < 0])
for lo, hi in ((100, 149), (150, 199), (200, 299), (300, 2000)):
    o.c(f"dog, last game WON as a +{lo}..+{hi} dog", [x for x in D if prev(x) and prev(x)["won"] and lo <= (prev(x).get("ml") or 0) <= hi])
H = [x for x in D if prev(x) and prev(x)["won"] and (prev(x).get("ml") or 0) >= 200]
o.c("hangover (+200 win), within 3 nights", [x for x in H if x["night"] - prev(x)["night"] <= 3])
o.c("hangover (+200 win), 4+ nights later", [x for x in H if x["night"] - prev(x)["night"] >= 4])
o.c("hangover, Nov-Dec", [x for x in H if x["start"][5:7] in ("11", "12")])
o.c("hangover, Jan-Mar", [x for x in H if x["start"][5:7] not in ("11", "12")])
o.c("hangover, at home", [x for x in H if x["venue"] == "home"])
o.c("hangover, road / neutral", [x for x in H if x["venue"] != "home"])
o.c("hangover, a dog +100..+220 (the Dog band)", [x for x in H if x["ml"] <= 220])
o.c("hangover ATS (the same side on the spread)", [x for x in lib.spreads(R) if x["sp"] > 0 and prev(x) and prev(x)["won"]
                                                    and (prev(x).get("ml") or 0) >= 200], lib.profit_ats)
o.c("the FAVORITE across from a hangover dog (-101..-400)", [x for x in R if x.get("ml") is not None and -400 <= x["ml"] <= -101
                                                              and x.get("olast") and x["olast"]["won"] and (x["olast"].get("ml") or 0) >= 200])
o.h("(b) THE RUBBER MATCH (3rd meeting after a 1-1 split)")
TM = [x for x in R if len(x["prev_meet"]) == 2 and all(m["stype"] == "2" for m in x["prev_meet"])
      and (x["prev_meet"][0]["margin"] > 0) != (x["prev_meet"][1]["margin"] > 0)]
for lo, hi in ((100, 149), (150, 220), (221, 350)):
    o.c(f"rubber-match dog +{lo}..+{hi}", [x for x in TM if x.get("ml") is not None and lo <= x["ml"] <= hi])
o.c("rubber-match dog, neutral", [x for x in lib.dogs(TM) if x["neutral"]])
o.c("rubber-match dog, home / road", [x for x in lib.dogs(TM) if not x["neutral"]])
o.c("rubber-match dog that WON the 2nd meeting", [x for x in lib.dogs(TM) if x["prev_meet"][1]["margin"] > 0])
o.c("rubber-match dog that LOST the 2nd meeting", [x for x in lib.dogs(TM) if x["prev_meet"][1]["margin"] < 0])
o.c("every conference-tournament-time dog (March, neutral) - the base", [x for x in D if x["start"][5:7] == "03" and x["neutral"]])
o.c("March neutral dog in a FIRST meeting", [x for x in D if x["start"][5:7] == "03" and x["neutral"] and not x["prev_meet"]])
o.c("March neutral dog vs a team it swept", [x for x in D if x["start"][5:7] == "03" and x["neutral"] and len(x["prev_meet"]) == 2
                                              and all(m["margin"] > 0 for m in x["prev_meet"])])
o.h("(c) Rested 3+ nights vs a team on 2-in-3, ATS (non-neutral) - the dose")
NN = [x for x in lib.spreads(R) if not x["neutral"] and x.get("rest") and x.get("orest")]
for r_lo, r_hi in ((3, 3), (4, 5), (6, 30)):
    for o_r in (1, 2):
        o.c(f"rest {r_lo}-{r_hi} nights vs a team on {o_r} night(s), ATS",
            [x for x in NN if r_lo <= x["rest"] <= r_hi and x["orest"] == o_r], lib.profit_ats)
o.c("rested 3+ vs 2-in-3, home side, ATS", [x for x in NN if x["rest"] >= 3 and x["orest"] <= 2 and x["side"] == "home"], lib.profit_ats)
o.c("rested 3+ vs 2-in-3, road side, ATS", [x for x in NN if x["rest"] >= 3 and x["orest"] <= 2 and x["side"] == "away"], lib.profit_ats)
o.c("rested 3+ vs 2-in-3, the spread FAVORITE", [x for x in NN if x["rest"] >= 3 and x["orest"] <= 2 and x["sp"] < 0], lib.profit_ats)
o.c("rested 3+ vs 2-in-3, the spread DOG", [x for x in NN if x["rest"] >= 3 and x["orest"] <= 2 and x["sp"] > 0], lib.profit_ats)
o.h("(d) The dog off beating a ranked team as a dog, Nov-Dec vs later (study 3's cell, the price band)")
RU = [x for x in D if prev(x) and prev(x)["won"] and prev(x)["orank25"] and (prev(x).get("ml") or 0) > 0
      and x["night"] - prev(x)["night"] <= 4]
o.c("ranked-upset winner, a dog again, Nov-Dec", [x for x in RU if x["start"][5:7] in ("11", "12")])
o.c("ranked-upset winner, a dog again, Jan-Mar", [x for x in RU if x["start"][5:7] not in ("11", "12")])
o.c("ranked-upset winner, a dog again, Nov-Dec, any gap", [x for x in D if prev(x) and prev(x)["won"] and prev(x)["orank25"]
                                                          and (prev(x).get("ml") or 0) > 0 and x["start"][5:7] in ("11", "12")])
o.save()
