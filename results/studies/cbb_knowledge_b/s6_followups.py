"""S6 - FOLLOW-UPS on what S1-S5 left standing: (a) MARCH FAVORITES (S4 E: favorites won 63.8% vs 61.3% priced in March
on 2,432 games) - by venue / band / season, with and without the known rubber-match / neutral-site dog fades;
(b) the HOME DOG vs A FAVORITE THAT FLEW 1,000+ MILES (S1 B: +15.2% on 152) - the full band, by season, the open, the
spread; (c) the LOCK CELL (S5 D: -120..-150, the weighed read 56%+ over the price, the own read over it) - by season at
the engine's own cuts (the thin-edge ½u line at 3 points, the early-lock rule, 3u-grade edges), the open, how many a
season; (d) DECEMBER favorites (S4 E: won 59.0% vs 61.2%) - is it the built away-Nov-Dec weight or more?"""
import lib

rows = lib.regular(lib.build())
S = [x for x in rows if x.get("ml") is not None and x.get("own") is not None and -350 <= x["ml"] <= 350]
o = lib.Out("s6")
BANDS = ["-251 and up", "-151..-250", "-101..-150"]

o.h("(a) MARCH FAVORITES -350..-101 (regular season, the conference tournaments in it)")
M = [x for x in S if x["ml"] < 0 and x.get("month") == "03"]
o.c("every March favorite", M)
lib.cuts(o, "March favorite by venue", M, lambda x: x["venue"], ["home", "away", "neutral"])
lib.cuts(o, "March favorite by price band", M, lambda x: lib.band(x["ml"]), BANDS)
o.c("March favorite, NOT a rubber match (the built fade's mirror out)", [x for x in M if not x.get("o_rubber")])
o.c("March favorite at HOME, not a rubber match", [x for x in M if x["venue"] == "home" and not x.get("o_rubber")])
o.c("March favorite on the ROAD", [x for x in M if x["venue"] == "away"])
o.c("March favorite at a NEUTRAL site, not a rubber match", [x for x in M if x["venue"] == "neutral" and not x.get("o_rubber")])
o.c("March favorite -101..-150 at home", [x for x in M if x["venue"] == "home" and x["ml"] >= -150])
o.c("March favorite -151..-250 at home", [x for x in M if x["venue"] == "home" and -250 <= x["ml"] <= -151])
o.c("March favorite, the dog across on a 5+ skid (the built fade)", [x for x in M if (x.get("o_streak") or 0) <= -5])
o.c("March favorite, the dog across NOT on a 5+ skid, not a rubber match", [x for x in M if (x.get("o_streak") or 0) > -5 and not x.get("o_rubber")])
o.c("...and at home", [x for x in M if (x.get("o_streak") or 0) > -5 and not x.get("o_rubber") and x["venue"] == "home"])
o.c("FEBRUARY favorite at home (the neighbor month)", [x for x in S if x["ml"] < 0 and x.get("month") == "02" and x["venue"] == "home"])
o.c("March favorite, the weighed read over the price", [x for x in M if x.get("fav_read") is not None and x["fav_read"] > x["p"]])
o.c("March favorite, the weighed read UNDER the price", [x for x in M if x.get("fav_read") is not None and x["fav_read"] <= x["p"]])
o.c("March DOG +100..+350 at home, not a rubber match, not on a skid", [x for x in S if x["ml"] >= 100 and x.get("month") == "03" and x["venue"] == "home" and not x.get("rubber") and (x.get("streak") or 0) > -5])
o.c("March spread favorite (ATS)", [x for x in rows if x.get("cover") is not None and x["sp"] < 0 and x.get("month") == "03"], lib.profit_ats)
o.c("March spread favorite at home (ATS)", [x for x in rows if x.get("cover") is not None and x["sp"] < 0 and x.get("month") == "03" and x["venue"] == "home"], lib.profit_ats)

o.h("(b) THE HOME DOG vs A FAVORITE THAT FLEW 1,000+ MILES (true home floor)")
far = lambda x, k=1000: x["venue"] == "home" and x.get("o_miles") is not None and x["o_miles"] >= k
D = [x for x in S if x["ml"] >= 100 and far(x)]
o.c("home dog +100..+350, the favorite flew 1,000+ miles", D)
o.c("home dog +100..+150, 1,000+ miles", [x for x in D if x["ml"] <= 150])
o.c("home dog +151..+350, 1,000+ miles", [x for x in D if x["ml"] > 150])
o.c("home dog +100..+350, the favorite flew 1,500+ miles", [x for x in S if x["ml"] >= 100 and far(x, 1500)])
o.c("home dog +100..+350, the favorite flew 500-999 miles (the dose check)", [x for x in S if x["ml"] >= 100 and x["venue"] == "home" and x.get("o_miles") is not None and 500 <= x["o_miles"] < 1000])
o.c("home dog +100..+350, the favorite flew under 500 miles", [x for x in S if x["ml"] >= 100 and x["venue"] == "home" and x.get("o_miles") is not None and x["o_miles"] < 500])
lib.cuts(o, "home dog, favorite 1,000+ miles, by month", D, lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"])
lib.cuts(o, "home dog, favorite 1,000+ miles, by tier", D, lib.tier_of, ["P", "M", "L"])
o.c("home dog, favorite 1,000+ miles, conference game", [x for x in D if x.get("same_conf")])
o.c("home dog, favorite 1,000+ miles, non-conference", [x for x in D if not x.get("same_conf")])
o.c("the SPREAD side: home dog getting points, favorite flew 1,000+ (ATS)", [x for x in rows if x.get("cover") is not None and x["sp"] > 0 and far(x)], lib.profit_ats)
o.c("the favorite ACROSS (flew 1,000+ to a dog's floor)", [x for x in S if x["ml"] < 0 and x["venue"] == "away" and x.get("miles") is not None and x["miles"] >= 1000])
o.c("home dog, the favorite's 2nd+ road game of a trip, 1,000+ miles", [x for x in D if (x.get("o_trip") or 0) >= 2])
o.c("home dog, the favorite's 1st road game, 1,000+ miles", [x for x in D if (x.get("o_trip") or 0) <= 1])

o.h("(c) THE LOCK CELL - a -120..-150 favorite, the weighed read 56%+ and over the price, the own read over it")
L = [x for x in S if -150 <= x["ml"] <= -120 and x.get("fav_read") is not None and x["fav_read"] >= 0.56
     and x["fav_read"] > x["p"] and x["own"] > x["p"]]
o.c("the Lock cell (every game)", L)
o.c("the Lock cell with the early-lock rule (both teams 3+ games)", [x for x in L if min(x["gn"], x.get("ogn") or 99) > 3])
o.c("the Lock cell, games 4-10 (the ½u window)", [x for x in L if 3 < min(x["gn"], x.get("ogn") or 99) <= 10])
o.c("the Lock cell, both teams 11+ games (the full-unit window)", [x for x in L if min(x["gn"], x.get("ogn") or 99) > 10])
o.c("the Lock cell, THIN (own read under 3 points over the price - ½u by the engine's rule)", [x for x in L if x["own"] - x["p"] < 0.03])
o.c("the Lock cell, a REAL edge (own read 3+ over the price)", [x for x in L if x["own"] - x["p"] >= 0.03])
o.c("the Lock cell, the weighed read 1+ over the price", [x for x in L if x["fav_read"] - x["p"] >= 0.01])
o.c("the Lock cell, the weighed read 2+ over", [x for x in L if x["fav_read"] - x["p"] >= 0.02])
o.c("the Lock cell, the weighed read 3+ over (the 10/23 plan's 3u grade - weighed AND own both beat it)", [x for x in L if x["fav_read"] - x["p"] >= 0.03 and x["own"] - x["p"] >= 0.03])
o.c("the Lock cell with NO favorite weight on it (own read only, no dog points either way)", [x for x in L if not x.get("fav_w")])
o.c("the Lock cell WITH a positive weight (the dog across has negative study points)", [x for x in L if (x.get("fav_w") or {}).get("opp_dog_pts", 0) > 0])
o.c("the Lock cell WITH a fade weight on it that it survived", [x for x in L if any(k in (x.get("fav_w") or {}) for k in ("away_nd", "eff_under", "top_out"))])
lib.cuts(o, "the Lock cell by venue", L, lambda x: x["venue"], ["home", "away", "neutral"])
lib.cuts(o, "the Lock cell by month", L, lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"])
lib.cuts(o, "the Lock cell by tier", L, lib.tier_of, ["P", "M", "L"])
o.c("the Lock cell, the efficiency read agrees (3+ over the price)", [x for x in L if x.get("eff") is not None and x["eff"] - x["p"] >= 0.03])
o.c("the Lock cell, the efficiency read is against it (3+ under)", [x for x in L if x.get("eff") is not None and x["eff"] - x["p"] <= -0.03])
o.c("the Lock cell, conference game", [x for x in L if x.get("same_conf")])
o.c("the Lock cell, non-conference", [x for x in L if not x.get("same_conf")])
o.c("CONTROL: the same band -120..-150 with the weighed read 56%+ but the OWN read UNDER the price", [x for x in S if -150 <= x["ml"] <= -120 and x.get("fav_read") is not None and x["fav_read"] >= 0.56 and x["fav_read"] > x["p"] and x["own"] <= x["p"]])
o.c("CONTROL: -120..-150, own over the price, weighed read UNDER 56% or under the price", [x for x in S if -150 <= x["ml"] <= -120 and x["own"] > x["p"] and x.get("fav_read") is not None and (x["fav_read"] < 0.56 or x["fav_read"] <= x["p"])])
o.c("CONTROL: -101..-119 (the S6 skip band), weighed 56%+ over, own over", [x for x in S if -119 <= x["ml"] <= -101 and x.get("fav_read") is not None and x["fav_read"] >= 0.56 and x["fav_read"] > x["p"] and x["own"] > x["p"]])
o.c("CONTROL: -151..-200, weighed 56%+ over, own over", [x for x in S if -200 <= x["ml"] <= -151 and x.get("fav_read") is not None and x["fav_read"] >= 0.56 and x["fav_read"] > x["p"] and x["own"] > x["p"]])
by = {}
for x in L:
    by.setdefault(x["season"], 0)
    by[x["season"]] += 1
o.note("Lock-cell games a season: " + ", ".join(f"{s}: {n}" for s, n in sorted(by.items())))
o.note("(caveat: the own read is sports_model's current ncaab params on every season - a slight look-ahead in its favour)")

o.h("(d) DECEMBER FAVORITES (won 59.0% vs 61.2% priced)")
Dc = [x for x in S if x["ml"] < 0 and x.get("month") == "12"]
lib.cuts(o, "December favorite by venue", Dc, lambda x: x["venue"], ["home", "away", "neutral"])
lib.cuts(o, "December favorite by band", Dc, lambda x: lib.band(x["ml"]), BANDS)
o.c("December favorite at HOME -151..-350", [x for x in Dc if x["venue"] == "home" and x["ml"] <= -151])
o.c("December favorite at home -101..-150", [x for x in Dc if x["venue"] == "home" and x["ml"] >= -150])
o.c("December favorite away / neutral -151..-350 (outside the built -101..-150 weight)", [x for x in Dc if x["venue"] != "home" and x["ml"] <= -151])
o.c("November favorite away / neutral -151..-350", [x for x in S if x["ml"] <= -151 and x.get("month") == "11" and x["venue"] != "home"])
o.c("Nov-Dec favorite away / neutral -151..-250, non-conference", [x for x in S if -250 <= x["ml"] <= -151 and x["nd"] and x["venue"] != "home" and not x.get("same_conf")])
o.c("Nov-Dec favorite away / neutral -151..-250, the DOG across +100..+200 at home / neutral", [x for x in S if 100 <= x["ml"] <= 200 and x["nd"] and x["venue"] != "away" and not x.get("same_conf") and x.get("oml") is not None and -250 <= x["oml"] <= -151])
o.save()
