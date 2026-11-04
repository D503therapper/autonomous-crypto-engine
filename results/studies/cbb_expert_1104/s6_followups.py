"""S6 - FOLLOW-UPS on what s1-s5 raised (the five checks: the dose, the venue, the price band, the month, the open, the
other market, the overlap with the weights already built - the 5+ skid, the early road dog, the top scorer out)."""
import lib

rows = lib.regular(lib.build())
pr = [x for x in rows if x.get("ml")]
out = lib.Out("s6", train=lib.TRAIN_PRICE)


def no_skid(x):
    return x["streak"] > -5


def not_early_road(x):
    return x["gn"] > 3


def band(x):
    m = x["ml"]
    return "+100..+150" if m <= 150 else "+151..+250" if m <= 250 else "+251..+350"


out.h("A. THE ROAD-COLD DOG: a road dog whose road cover margin this season is -6 or worse (3+ true road games)")
rc = [x for x in pr if x["venue"] == "away" and x.get("road_cm") is not None]
cold = [x for x in rc if x["road_cm"] <= -6]
lib.three("road_cm -6- (all)", cold, out)
lib.three("road_cm -6-, no 5+ skid, past game 3", [x for x in cold if no_skid(x) and not_early_road(x)], out)
lib.three("road_cm -6-, no 5+ skid, past game 3, 5+ road games", [x for x in cold if no_skid(x) and not_early_road(x) and x["road_w"] + x["road_l"] >= 5], out)
for lo, hi, nm in ((-99, -10, "-10-"), (-10, -8, "-10..-8"), (-8, -6, "-8..-6"), (-6, -4, "-6..-4"), (-4, -2, "-4..-2")):
    out.c(f"road dog, road_cm {nm}, no skid, past g3", lib.dogs([x for x in rc if lo <= x["road_cm"] < hi and no_skid(x) and not_early_road(x)]))
clean = [x for x in cold if no_skid(x) and not_early_road(x)]
for b in ("+100..+150", "+151..+250", "+251..+350"):
    out.c(f"road-cold dog {b} (clean)", [x for x in lib.dogs(clean) if band(x) == b])
for ph, ms in (("Nov-Dec", ("11", "12")), ("Jan-Mar", ("01", "02", "03"))):
    out.c(f"road-cold dog {ph} (clean)", [x for x in lib.dogs(clean) if lib.month(x) in ms])
out.c("road-cold dog, road record under .250 (clean)", [x for x in lib.dogs(clean) if x["road_w"] / (x["road_w"] + x["road_l"]) < 0.25])
out.c("road-cold dog, road record .250+ (clean)", [x for x in lib.dogs(clean) if x["road_w"] / (x["road_w"] + x["road_l"]) >= 0.25])
out.c("road-cold dog AND a home-floor team (home_cm - away_cm 6+) (clean)", [x for x in lib.dogs(clean) if (x.get("home_edge") or 0) >= 6])
out.c("road-cold dog, NOT a home-floor team (clean)", [x for x in lib.dogs(clean) if x.get("home_edge") is None or x["home_edge"] < 6])
out.c("home-floor team (edge 6+) as a road dog, road_cm better than -6 (the other half)", [x for x in lib.dogs(rc) if (x.get("home_edge") or 0) >= 6 and x["road_cm"] > -6 and no_skid(x) and not_early_road(x)])
out.c("road-cold dog, the season's cover margin overall under -3 (a cold-ATS team everywhere)", [x for x in lib.dogs(clean) if x.get("cm5") is not None and x["cm5"] < -3])
out.c("road-cold dog, cm5 -3 or better (cold on the road only)", [x for x in lib.dogs(clean) if x.get("cm5") is not None and x["cm5"] >= -3])
out.c("road-cold dog by tier: low", [x for x in lib.dogs(clean) if x["tier"] == "low"])
out.c("road-cold dog by tier: mid / power", [x for x in lib.dogs(clean) if x["tier"] in ("mid", "power")])
out.c("road-cold dog, same conference", [x for x in lib.dogs(clean) if x["same_conf"]])
out.c("road-cold dog, non-conference", [x for x in lib.dogs(clean) if not x["same_conf"]])
# the favorite across it (the home favorite)
hf = [x for x in pr if x["venue"] == "home" and x.get("opp_road_cm") is not None and x["opp_road_cm"] <= -6 and x["ostreak"] > -5 and x["ogn"] > 3]
out.c("home fav -101..-150 vs a road-cold dog", lib.favs(hf))
out.c("home fav -151..-250 vs a road-cold dog", lib.favs(hf, -250, -151))
out.c("home side vs a road-cold dog ATS", lib.spreads(hf), lib.profit_ats)
# the mirror: the HOT road dog (road_cm +6+) - priced (s3) - restated clean
out.c("road dog, road_cm +6+, no skid, past g3", lib.dogs([x for x in rc if x["road_cm"] >= 6 and no_skid(x) and not_early_road(x)]))

out.h("B. THE COLD-SHOOTING DOG (eFG last 5 at least 4 points under its season), Jan-Mar - overlap with the 5+ skid")
bx = [x for x in lib.boxed(rows) if x.get("efg5") is not None and x.get("ml")]
cs = [x for x in bx if x["efg5"] - x["efg_s"] <= -0.04]
jm = [x for x in cs if lib.month(x) in ("01", "02", "03")]
out.c("cold-shooting dog Jan-Mar (all)", lib.dogs(jm), train=lib.TRAIN_BOX)
out.c("cold-shooting dog Jan-Mar, no 5+ skid", lib.dogs([x for x in jm if no_skid(x)]), train=lib.TRAIN_BOX)
out.c("cold-shooting dog Jan-Mar, no 5+ skid, top scorer in", lib.dogs([x for x in jm if no_skid(x) and x.get("top_out") is False]), train=lib.TRAIN_BOX)
out.c("cold-shooting dog Jan-Mar, no skid, adjm5 -4 or better (cold shooting, not cold results)", lib.dogs([x for x in jm if no_skid(x) and (x.get("adjm5") if x.get("adjm5") is not None else 0) >= -4]), train=lib.TRAIN_BOX)
out.c("cold-shooting dog Jan-Mar, no skid, adjm5 under -4 (cold both ways)", lib.dogs([x for x in jm if no_skid(x) and (x.get("adjm5") if x.get("adjm5") is not None else 0) < -4]), train=lib.TRAIN_BOX)
for lo, hi, nm in ((-1, -0.07, "-7-"), (-0.07, -0.05, "-7..-5"), (-0.05, -0.04, "-5..-4"), (-0.04, -0.03, "-4..-3")):
    out.c(f"cold-shooting dog Jan-Mar, no skid, eFG gap {nm}", lib.dogs([x for x in bx if lib.month(x) in ("01", "02", "03") and no_skid(x) and lo <= x["efg5"] - x["efg_s"] < hi]), train=lib.TRAIN_BOX)
for b in ("+100..+150", "+151..+250", "+251..+350"):
    out.c(f"cold-shooting dog Jan-Mar, no skid, {b}", [x for x in lib.dogs(jm) if no_skid(x) and band(x) == b], train=lib.TRAIN_BOX)
out.c("cold-shooting dog Jan-Mar, no skid, at home", [x for x in lib.dogs(jm) if no_skid(x) and x["venue"] == "home"], train=lib.TRAIN_BOX)
out.c("cold-shooting dog Jan-Mar, no skid, on the road", [x for x in lib.dogs(jm) if no_skid(x) and x["venue"] == "away"], train=lib.TRAIN_BOX)
out.c("cold-shooting dog Nov-Dec, no skid", lib.dogs([x for x in cs if lib.month(x) in ("11", "12") and no_skid(x)]), train=lib.TRAIN_BOX)
out.c("cold-shooting side Jan-Mar, no skid, ATS", lib.spreads([x for x in jm if no_skid(x)]), lib.profit_ats, train=lib.TRAIN_BOX)
out.c("cold-shooting fav -101..-150 Jan-Mar, no skid", lib.favs([x for x in jm if no_skid(x)]), train=lib.TRAIN_BOX)
out.c("the favorite across a cold-shooting dog Jan-Mar -101..-150", lib.favs([x for x in bx if lib.month(x) in ("01", "02", "03") and x.get("opp_efg5") is not None and x["opp_efg5"] - x["opp_efg_s"] <= -0.04 and x["ostreak"] > -5]), train=lib.TRAIN_BOX)
out.c("cold from deep only (3P -6, 2P not cold) dog Jan-Mar, no skid", lib.dogs([x for x in bx if lib.month(x) in ("01", "02", "03") and no_skid(x) and x.get("tp5") is not None and x["tp5"] - x["tp_s"] <= -0.06 and (x.get("two5") or 0) - (x.get("two_s") or 0) > -0.03]), train=lib.TRAIN_BOX)

out.h("C. THE STAR'S 2ND GAME BACK (the top scorer missed 2+, played the last game) - every cut")
pb = [x for x in lib.boxed(rows) if x.get("top_fga") is not None and x.get("ml")]
b2 = [x for x in pb if x.get("back2")]
out.c("back2 dog (all)", lib.dogs(b2), train=lib.TRAIN_BOX)
out.c("back2 dog, at home", [x for x in lib.dogs(b2) if x["venue"] == "home"], train=lib.TRAIN_BOX)
out.c("back2 dog, on the road / neutral", [x for x in lib.dogs(b2) if x["venue"] != "home"], train=lib.TRAIN_BOX)
out.c("back2 dog, +100..+200", [x for x in lib.dogs(b2) if x["ml"] <= 200], train=lib.TRAIN_BOX)
out.c("back2 dog, +201..+350", [x for x in lib.dogs(b2) if x["ml"] > 200], train=lib.TRAIN_BOX)
out.c("back2 dog, Nov-Dec", [x for x in lib.dogs(b2) if lib.month(x) in ("11", "12")], train=lib.TRAIN_BOX)
out.c("back2 dog, Jan-Mar", [x for x in lib.dogs(b2) if lib.month(x) in ("01", "02", "03")], train=lib.TRAIN_BOX)
out.c("back2 dog, no 5+ skid", [x for x in lib.dogs(b2) if no_skid(x)], train=lib.TRAIN_BOX)
out.c("back2 fav -101..-150", lib.favs(b2), train=lib.TRAIN_BOX)
out.c("back2 fav -151..-250", lib.favs(b2, -250, -151), train=lib.TRAIN_BOX)
out.c("back2 fav -101..-250", lib.favs(b2, -250, -101), train=lib.TRAIN_BOX)
out.c("back2 side ATS (all)", lib.spreads(b2), lib.profit_ats, train=lib.TRAIN_BOX)
out.c("back2 side ATS, as the favorite", lib.spreads([x for x in b2 if x.get("sp") is not None and x["sp"] < 0]), lib.profit_ats, train=lib.TRAIN_BOX)
out.c("back2 side ATS, as the dog", lib.spreads([x for x in b2 if x.get("sp") is not None and x["sp"] > 0]), lib.profit_ats, train=lib.TRAIN_BOX)
out.c("back2 side ATS, the star's share of shots 20%+", lib.spreads([x for x in b2 if x["top_fga"] >= 0.20]), lib.profit_ats, train=lib.TRAIN_BOX)
out.c("back2 side ATS, the star's share under 20%", lib.spreads([x for x in b2 if x["top_fga"] < 0.20]), lib.profit_ats, train=lib.TRAIN_BOX)
ob2 = [x for x in pb if x.get("opp_back2")]
out.c("the side ACROSS a back2 team: dog +100..+350", lib.dogs(ob2), train=lib.TRAIN_BOX)
out.c("the side ACROSS a back2 team: fav -101..-150", lib.favs(ob2), train=lib.TRAIN_BOX)
out.c("the side ACROSS a back2 team: fav -151..-250", lib.favs(ob2, -250, -151), train=lib.TRAIN_BOX)
out.c("the side ACROSS a back2 team: ATS", lib.spreads(ob2), lib.profit_ats, train=lib.TRAIN_BOX)
out.c("the side ACROSS a back2 team: ATS at home", lib.spreads([x for x in ob2 if x["venue"] == "home"]), lib.profit_ats, train=lib.TRAIN_BOX)
out.c("the side ACROSS a back2 team: ATS on the road", lib.spreads([x for x in ob2 if x["venue"] == "away"]), lib.profit_ats, train=lib.TRAIN_BOX)
# the 3rd game back (he missed 2+, played the last TWO) - does it fade out?
out.c("CONTROL: the top scorer played the last 2 after missing 2+ (3rd game back) - side ATS",
      lib.spreads([x for x in pb if not x.get("back2") and x.get("miss_run") == 0 and x.get("back3")]), lib.profit_ats, train=lib.TRAIN_BOX)
out.c("CONTROL: back1 ex post (his first game back) - side ATS", lib.spreads([x for x in pb if x.get("back1")]), lib.profit_ats, train=lib.TRAIN_BOX)

out.h("D. THE TOP SCORER OUT 5+ GAMES RUNNING (the built -2's long tail)")
to = [x for x in pb if x.get("top_out")]
out.c("top_out dog, missed 5+", [x for x in lib.dogs(to) if (x.get("miss_run") or 0) >= 5], train=lib.TRAIN_BOX)
out.c("top_out dog, missed 5+, no 5+ skid", [x for x in lib.dogs(to) if (x.get("miss_run") or 0) >= 5 and no_skid(x)], train=lib.TRAIN_BOX)
out.c("top_out dog, missed 5+, at home", [x for x in lib.dogs(to) if (x.get("miss_run") or 0) >= 5 and x["venue"] == "home"], train=lib.TRAIN_BOX)
out.c("top_out dog, missed 5+, on the road", [x for x in lib.dogs(to) if (x.get("miss_run") or 0) >= 5 and x["venue"] == "away"], train=lib.TRAIN_BOX)
out.c("top_out dog, missed 5+, +100..+200", [x for x in lib.dogs(to) if (x.get("miss_run") or 0) >= 5 and x["ml"] <= 200], train=lib.TRAIN_BOX)
out.c("top_out dog, missed 5+, +201..+350", [x for x in lib.dogs(to) if (x.get("miss_run") or 0) >= 5 and x["ml"] > 200], train=lib.TRAIN_BOX)
out.c("top_out dog, missed 1-4 (the rest)", [x for x in lib.dogs(to) if (x.get("miss_run") or 0) < 5], train=lib.TRAIN_BOX)
out.c("top_out fav -101..-250, missed 5+", lib.favs([x for x in to if (x.get("miss_run") or 0) >= 5], -250, -101), train=lib.TRAIN_BOX)
out.c("top_out side ATS, missed 5+", lib.spreads([x for x in to if (x.get("miss_run") or 0) >= 5]), lib.profit_ats, train=lib.TRAIN_BOX)
out.c("the side across a top_out 5+ team: dog", lib.dogs([x for x in pb if x.get("opp_top_out") and (x.get("opp_miss_run") or 0) >= 5]), train=lib.TRAIN_BOX)

out.h("E. LEADS: the upset winner (beat a top-25 team as a dog) as a dog again; the 3P-hot road dog")
up = [x for x in pr if x.get("beat_good") and x.get("upset_last")]
out.c("upset winner, a dog again (all)", lib.dogs(up))
out.c("upset winner, a dog again, Nov-Dec", [x for x in lib.dogs(up) if lib.month(x) in ("11", "12")])
out.c("upset winner, a dog again, Jan-Mar", [x for x in lib.dogs(up) if lib.month(x) in ("01", "02", "03")])
out.c("upset winner, a dog again, at home", [x for x in lib.dogs(up) if x["venue"] == "home"])
out.c("upset winner, a dog again, on the road", [x for x in lib.dogs(up) if x["venue"] == "away"])
out.c("upset winner, a dog again, +100..+200", [x for x in lib.dogs(up) if x["ml"] <= 200])
out.c("upset winner, a dog again, +201..+350", [x for x in lib.dogs(up) if x["ml"] > 200])
out.c("CONTROL: beat a top-25 team as the FAVORITE, a dog now", lib.dogs([x for x in pr if x.get("beat_good") and not x.get("upset_last")]))
out.c("CONTROL: won as a +150 dog vs a NON-top-25 team, a dog again", lib.dogs([x for x in pr if x.get("upset_last") and not x.get("beat_good")]))
tp = [x for x in bx if x.get("tp5") is not None and x["tp5"] - x["tp_s"] >= 0.06 and (x.get("two5") or 0) - (x.get("two_s") or 0) < 0.02]
out.c("3P-hot (not inside) road dog", [x for x in lib.dogs(tp) if x["venue"] == "away"], train=lib.TRAIN_BOX)
out.c("3P-hot (not inside) road dog, no skid, past g3", [x for x in lib.dogs(tp) if x["venue"] == "away" and no_skid(x) and not_early_road(x)], train=lib.TRAIN_BOX)
out.c("3P-hot (not inside) home dog", [x for x in lib.dogs(tp) if x["venue"] == "home"], train=lib.TRAIN_BOX)
out.save()
