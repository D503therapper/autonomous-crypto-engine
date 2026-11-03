"""S6 - FOLLOW-UPS on what S1-S5 raised: (A) the ranked (top-25 by our Elo) side on the ROAD, ATS -9.7% on 2,112 (0/5,
0/3) - dose by spread, phase, the opponent, whether it's the public-name effect or the big-favorite fact; (B) the public
name on Saturday ATS -7.6% on 2,046 (0/5, 0/3) - venue, favorite / dog, the opponent's side, the 12 blue bloods alone;
(C) in-season ATS mean reversion: a team whose cover margin so far beats the opponent's by 3+ ATS -7.8% on 5,136
(0/5, 0/3) - is it new next to the cover-run weight already built (ats_run 4+)? dose, phase, by games; (D) the rebound
margin gap 8+ dog ML +10% on 397 / the gap -8 side ATS -7.8% - the cover margin by bucket, controlling for the spread."""
import lib
from collections import defaultdict

R = lib.regular(lib.build())
o = lib.Out("s6")
SP, DG, FV = lib.spreads(R), lib.dogs(R), lib.favs(R)
PUB = {"Duke", "Kentucky", "Kansas", "North Carolina", "UCLA", "Michigan St", "Indiana", "Syracuse", "Gonzaga", "Arizona",
       "Louisville", "Villanova", "UConn", "Michigan", "Ohio St", "Purdue", "Alabama", "Auburn", "Tennessee", "Houston",
       "Baylor", "Texas", "Florida", "LSU", "Memphis", "Georgetown", "Marquette", "Illinois", "Iowa St", "Creighton"}
BLUE = {"Duke", "Kentucky", "Kansas", "North Carolina", "UCLA", "Michigan St", "Indiana", "Syracuse", "Gonzaga", "Arizona", "Louisville", "Villanova"}


def cm(rows):
    rows = [x for x in rows if x.get("sp") is not None]
    return (sum(x["margin"] + x["sp"] for x in rows) / len(rows)) if rows else None


o.h("A. The ranked side on the road (true road, not neutral), ATS")
RR = [x for x in SP if x["rank25"] and x["venue"] == "away"]
o.c("ATS ranked road side", RR, lib.profit_ats)
o.c("ATS ranked road side, NOT a public name", [x for x in RR if x["name"] not in PUB], lib.profit_ats)
o.c("ATS ranked road side, a public name", [x for x in RR if x["name"] in PUB], lib.profit_ats)
for lo, hi in ((-99, -10), (-10, -5), (-5, 0), (0, 5), (5, 99)):
    o.c(f"ATS ranked road side, spread {lo}..{hi}", [x for x in RR if lo <= x["sp"] < hi], lib.profit_ats)
o.c("ATS ranked road side, Nov-Dec", [x for x in RR if x["start"][5:7] in ("11", "12")], lib.profit_ats)
o.c("ATS ranked road side, Jan", [x for x in RR if x["start"][5:7] == "01"], lib.profit_ats)
o.c("ATS ranked road side, Feb-Mar", [x for x in RR if x["start"][5:7] in ("02", "03")], lib.profit_ats)
o.c("ATS ranked road side, vs a ranked team", [x for x in RR if x["orank25"]], lib.profit_ats)
o.c("ATS ranked road side, vs an unranked team", [x for x in RR if not x["orank25"]], lib.profit_ats)
o.c("ATS ranked road side, same conference", [x for x in RR if x["same_conf"]], lib.profit_ats)
o.c("ATS ranked road side, non-conference", [x for x in RR if not x["same_conf"]], lib.profit_ats)
o.c("ATS ranked road side, Saturday", [x for x in RR if x["dow"] == 5], lib.profit_ats)
o.c("ATS ranked road side, Mon-Thu", [x for x in RR if x["dow"] <= 3], lib.profit_ats)
o.c("ATS ranked road side, power tier", [x for x in RR if x["tier"] == "power"], lib.profit_ats)
o.c("ATS ranked road side, mid / low tier", [x for x in RR if x["tier"] != "power"], lib.profit_ats)
o.c("ML ranked road favorite -101..-150", [x for x in RR if x.get("ml") is not None and -150 <= x["ml"] <= -101])
o.c("ML ranked road favorite -151..-300", [x for x in RR if x.get("ml") is not None and -300 <= x["ml"] <= -151])
o.c("ML ranked road dog +100..+350", [x for x in RR if x.get("ml") is not None and 100 <= x["ml"] <= 350])
o.c("ML the HOME dog +100..+350 vs a ranked road team", [x for x in DG if x["venue"] == "home" and x["orank25"]])
o.c("ML the HOME dog +100..+200 vs a ranked road team", [x for x in DG if x["venue"] == "home" and x["orank25"] and x["ml"] <= 200])
o.c("ATS the HOME side vs a ranked road team", [x for x in SP if x["venue"] == "home" and x["orank25"]], lib.profit_ats)
o.c("ATS ranked side at a neutral site", [x for x in SP if x["rank25"] and x["venue"] == "neutral"], lib.profit_ats)
o.c("ATS ranked side at home (the mirror check)", [x for x in SP if x["rank25"] and x["venue"] == "home"], lib.profit_ats)
o.note(f"mean cover margin: ranked road {cm(RR):+.2f} | ranked home {cm([x for x in SP if x['rank25'] and x['venue']=='home']):+.2f} | "
       f"all road {cm([x for x in SP if x['venue']=='away']):+.2f} | all home {cm([x for x in SP if x['venue']=='home']):+.2f}")
o.h("A2. Top-10 / 11-25 by Elo on the road (the dose), and the Elo gap itself")
cut = defaultdict(list)
for x in SP:
    if x.get("cut25") is not None:
        cut[(x["season"], x["night"])].append(x)
# a stricter rank: top 10 = elo among the top 10 that night - approximate with elo >= cut25 + 40
o.c("ATS road, elo 40+ over the top-25 cut (~top 10)", [x for x in RR if x["elo"] >= x["cut25"] + 40], lib.profit_ats)
o.c("ATS road, ranked but under cut + 40 (~11-25)", [x for x in RR if x["elo"] < x["cut25"] + 40], lib.profit_ats)
o.c("ATS road, elo just UNDER the cut (26-40ish: cut-40..cut)", [x for x in SP if x["venue"] == "away" and x.get("cut25") is not None
                                                                 and x["cut25"] - 40 <= x["elo"] < x["cut25"]], lib.profit_ats)
o.c("ATS road, elo cut-100..cut-40", [x for x in SP if x["venue"] == "away" and x.get("cut25") is not None
                                       and x["cut25"] - 100 <= x["elo"] < x["cut25"] - 40], lib.profit_ats)
o.c("ATS road, elo under cut-100", [x for x in SP if x["venue"] == "away" and x.get("cut25") is not None and x["elo"] < x["cut25"] - 100], lib.profit_ats)
o.h("A3. The ranked road side by the Elo GAP to the opponent (is it 'the better team on the road' or 'ranked'?)")
for lo, hi in ((-999, 0), (0, 50), (50, 100), (100, 150), (150, 999)):
    o.c(f"ATS road side, elo gap {lo}..{hi}, UNRANKED", [x for x in SP if x["venue"] == "away" and not x["rank25"] and lo <= x["elo"] - x["oelo"] < hi], lib.profit_ats)
    o.c(f"ATS road side, elo gap {lo}..{hi}, RANKED", [x for x in RR if lo <= x["elo"] - x["oelo"] < hi], lib.profit_ats)
o.h("B. The public name on Saturday")
PS = [x for x in SP if x["name"] in PUB and x["dow"] == 5]
o.c("ATS public name, Saturday", PS, lib.profit_ats)
o.c("ATS public name, Saturday, home", [x for x in PS if x["venue"] == "home"], lib.profit_ats)
o.c("ATS public name, Saturday, road", [x for x in PS if x["venue"] == "away"], lib.profit_ats)
o.c("ATS public name, Saturday, favorite", [x for x in PS if x["sp"] < 0], lib.profit_ats)
o.c("ATS public name, Saturday, dog", [x for x in PS if x["sp"] > 0], lib.profit_ats)
o.c("ATS public name, Saturday, vs a NON-public name", [x for x in PS if x["oname"] not in PUB], lib.profit_ats)
o.c("ATS the NON-public side vs a public name, Saturday", [x for x in SP if x["oname"] in PUB and x["name"] not in PUB and x["dow"] == 5], lib.profit_ats)
o.c("ATS the 12 blue bloods, Saturday", [x for x in PS if x["name"] in BLUE], lib.profit_ats)
o.c("ATS the 12 blue bloods, Mon-Thu", [x for x in SP if x["name"] in BLUE and x["dow"] <= 3], lib.profit_ats)
o.c("ATS public name, Saturday, ranked", [x for x in PS if x["rank25"]], lib.profit_ats)
o.c("ATS public name, Saturday, UNRANKED", [x for x in PS if not x["rank25"]], lib.profit_ats)
o.c("ATS public name, Sunday", [x for x in SP if x["name"] in PUB and x["dow"] == 6], lib.profit_ats)
o.c("ATS public name, Friday", [x for x in SP if x["name"] in PUB and x["dow"] == 4], lib.profit_ats)
o.c("ML public favorite -101..-150, Saturday", [x for x in FV if x["name"] in PUB and x["dow"] == 5])
o.c("ML public favorite -151..-300, Saturday", [x for x in lib.favs(R, -300, -151) if x["name"] in PUB and x["dow"] == 5])
o.c("ML the dog vs a public name, Saturday", [x for x in DG if x["oname"] in PUB and x["name"] not in PUB and x["dow"] == 5])
o.c("ATS ANY ranked side Saturday (public or not)", [x for x in SP if x["rank25"] and x["dow"] == 5], lib.profit_ats)
o.c("ATS ANY ranked side Mon-Thu", [x for x in SP if x["rank25"] and x["dow"] <= 3], lib.profit_ats)
o.h("C. In-season ATS mean reversion - the side whose cover margin so far beats the opponent's by 3+ (both 10+ spread games)")
CS = [x for x in SP if x.get("cm_mean") is not None and x.get("n_cm", 0) >= 10 and x.get("o_cm_mean") is not None]
HOT = [x for x in CS if x["cm_mean"] - x["o_cm_mean"] >= 3]
COLD = [x for x in CS if x["cm_mean"] - x["o_cm_mean"] <= -3]
o.c("ATS hot-vs-cold side (gap 3+)", HOT, lib.profit_ats)
o.c("ATS ... with NO 4+ cover run (new next to cover_run_w)", [x for x in HOT if abs(x["ats"]) < 4], lib.profit_ats)
o.c("ATS ... with a 4+ cover run", [x for x in HOT if x["ats"] >= 4], lib.profit_ats)
o.c("ATS cold-vs-hot side (gap -3)", COLD, lib.profit_ats)
o.c("ATS ... with NO 4+ failed run", [x for x in COLD if abs(x["ats"]) < 4], lib.profit_ats)
for lo, hi in ((3, 5), (5, 8), (8, 99)):
    o.c(f"ATS hot side, gap {lo}..{hi}", [x for x in HOT if lo <= x["cm_mean"] - x["o_cm_mean"] < hi], lib.profit_ats)
for lo, hi in ((10, 15), (16, 22), (23, 99)):
    o.c(f"ATS hot side, {lo}-{hi} spread games in", [x for x in HOT if lo <= x["n_cm"] <= hi], lib.profit_ats)
o.c("ATS hot side, as the favorite", [x for x in HOT if x["sp"] < 0], lib.profit_ats)
o.c("ATS hot side, as the dog", [x for x in HOT if x["sp"] > 0], lib.profit_ats)
o.c("ATS hot side, home", [x for x in HOT if x["venue"] == "home"], lib.profit_ats)
o.c("ATS hot side, road", [x for x in HOT if x["venue"] == "away"], lib.profit_ats)
o.c("ATS hot side, Jan", [x for x in HOT if x["start"][5:7] == "01"], lib.profit_ats)
o.c("ATS hot side, Feb-Mar", [x for x in HOT if x["start"][5:7] in ("02", "03")], lib.profit_ats)
o.c("ATS hot side, same conference", [x for x in HOT if x["same_conf"]], lib.profit_ats)
o.c("ML hot side as a dog +100..+350", [x for x in HOT if x.get("ml") is not None and 100 <= x["ml"] <= 350])
o.c("ML hot side as a favorite -101..-150", [x for x in HOT if x.get("ml") is not None and -150 <= x["ml"] <= -101])
o.c("ML cold side as a dog +100..+350", [x for x in COLD if x.get("ml") is not None and 100 <= x["ml"] <= 350])
o.c("ML cold side as a favorite -101..-150", [x for x in COLD if x.get("ml") is not None and -150 <= x["ml"] <= -101])
o.note(f"mean cover margin hot {cm(HOT):+.2f} (n {len(HOT)}) | cold {cm(COLD):+.2f} | all {cm(CS):+.2f}")
o.h("C2. The OWN season residual alone (not the gap): hot team 3+ / cold team -3, by games in")
for lo, hi in ((10, 15), (16, 22), (23, 99)):
    o.c(f"ATS own resid 3+, {lo}-{hi} games", [x for x in CS if x["cm_mean"] >= 3 and lo <= x["n_cm"] <= hi], lib.profit_ats)
    o.c(f"ATS own resid -3 or less, {lo}-{hi} games", [x for x in CS if x["cm_mean"] <= -3 and lo <= x["n_cm"] <= hi], lib.profit_ats)
o.h("D. Rebounding (box scores 2021-26): the cover margin by rebound-margin gap, and the dose")
RB = [x for x in SP if x.get("rebm") is not None and x.get("o_rebm") is not None]
for lo, hi in ((-99, -10), (-10, -6), (-6, -3), (-3, 3), (3, 6), (6, 10), (10, 99)):
    rows = [x for x in RB if lo <= x["rebm"] - x["o_rebm"] < hi]
    o.c(f"ATS reb gap {lo}..{hi}", rows, lib.profit_ats)
    o.note(f"   mean cover margin {cm(rows):+.2f} | as fav {cm([x for x in rows if x['sp'] < 0]) or 0:+.2f} | as dog {cm([x for x in rows if x['sp'] > 0]) or 0:+.2f}")
o.c("dog ML reb gap 6+", [x for x in DG if x.get("rebm") is not None and x.get("o_rebm") is not None and x["rebm"] - x["o_rebm"] >= 6])
o.c("dog ML reb gap 8+", [x for x in DG if x.get("rebm") is not None and x.get("o_rebm") is not None and x["rebm"] - x["o_rebm"] >= 8])
o.c("dog ML reb gap 8+, home", [x for x in DG if x.get("rebm") is not None and x.get("o_rebm") is not None and x["rebm"] - x["o_rebm"] >= 8 and x["venue"] == "home"])
o.c("fav ML -101..-200 reb gap -8 or less", [x for x in lib.favs(R, -200, -101) if x.get("rebm") is not None and x.get("o_rebm") is not None and x["rebm"] - x["o_rebm"] <= -8])
o.c("ATS fav, reb gap -6 or less", [x for x in RB if x["sp"] < 0 and x["rebm"] - x["o_rebm"] <= -6], lib.profit_ats)
o.c("ATS dog, reb gap 6+", [x for x in RB if x["sp"] > 0 and x["rebm"] - x["o_rebm"] >= 6], lib.profit_ats)
o.save()
