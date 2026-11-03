"""S5 - THE ENGINE'S OWN COLLEGE HOOPS READ WITH ALL THE 11/3 WEIGHTS STACKED, replayed 2018-25 walk-forward: where does
it beat the price - tiers, months, price bands, venues, games played? The reads (lib.dog_pts / lib.fav_read replay
sports.dog_spots / dog_score and weigh_favorites + weigh_ncaab_away_fav / eff_fav / top_out): the OWN read = the old
read (sports_model's Elo + features blended with the market by the learned trust, pulled to the market by early_trust -
today's ncaab params, a slight look-ahead in the read's favour); a FAVORITE's weighed read = own + the dog's study points
the other way (capped FAV_CAP) + the three favorite weights (floor own - FAV_CAP); a DOG's read = the market + its dog
score / 100 (the own-read gap capped at OWN_CAP + the study points capped at STUDY_CAP). A 'bet' = the weighed read over
the no-vig close by the cut; the OWN-BEATS rule (the owner, 10/18) = the own read over the price too. Every cell is
read train 2018-22 / held out 2023 / 2024 / 2025 apart, the ESPN open the second check. This is where college hoops
units should go - or not."""
import lib

rows = lib.regular(lib.build())
S = [x for x in rows if x.get("ml") is not None and x.get("own") is not None and -350 <= x["ml"] <= 350]
o = lib.Out("s5")
BANDS = ["-251 and up", "-151..-250", "-101..-150", "+100..+150", "+151..+250", "+251..+350"]
MONTHS = ["Nov", "Dec", "Jan", "Feb", "Mar"]


def weighed(x):
    return x.get("fav_read") if x["ml"] < 0 else x.get("dog_read")


def edge(x):
    w = weighed(x)
    return (w - x["p"]) if w is not None else None


def own_over(x):
    return x["own"] > x["p"]


o.note(f"priced sides -350..+350 with an engine read: {len(S)} (train {sum(1 for x in S if x['season'] <= 2022)}, held {sum(1 for x in S if x['season'] in lib.HELD)})")
o.note("the weights that fired on favorites: " + str({k: sum(1 for x in S if k in (x.get('fav_w') or {})) for k in ('opp_dog_pts', 'away_nd', 'eff_under', 'top_out')}))

o.h("A. WHAT THE WEIGHTS DO - every side by how far the weighed read sits from the own read")
lib.cuts(o, "weighed - own (points)", S, lambda x: lib.bk(round((weighed(x) - x["own"]) * 100, 1) if weighed(x) is not None else None, [-4, -2, -0.5, 0.5, 2, 4]), lib.bk_labels([-4, -2, -0.5, 0.5, 2, 4]))
o.c("favorites the weights move DOWN 2+ points (the fades)", [x for x in S if x["ml"] < 0 and weighed(x) is not None and weighed(x) - x["own"] <= -0.02])
o.c("favorites the weights move UP 2+ points", [x for x in S if x["ml"] < 0 and weighed(x) is not None and weighed(x) - x["own"] >= 0.02])
o.c("dogs with study points -3 or worse (the fades)", [x for x in S if x["ml"] >= 100 and (x.get("dog_pts") or 0) <= -3])
o.c("dogs with study points +2 or better", [x for x in S if x["ml"] >= 100 and (x.get("dog_pts") or 0) >= 2])

o.h("B. THE WEIGHED READ OVER THE PRICE - every side, by the cut (0+ / 2+ / 3+ / 5+ points over the no-vig close)")
for cut in (0.0, 0.02, 0.03, 0.05):
    o.c(f"weighed read {cut * 100:.0f}+ over the price - ALL", [x for x in S if (edge(x) or -9) >= cut])
    o.c(f"weighed read {cut * 100:.0f}+ over, favorites", [x for x in S if (edge(x) or -9) >= cut and x["ml"] < 0])
    o.c(f"weighed read {cut * 100:.0f}+ over, dogs", [x for x in S if (edge(x) or -9) >= cut and x["ml"] >= 100])
    o.c(f"weighed read {cut * 100:.0f}+ over AND the own read over the price (own-beats), favorites", [x for x in S if (edge(x) or -9) >= cut and x["ml"] < 0 and own_over(x)])
    o.c(f"weighed read {cut * 100:.0f}+ over AND own-beats, dogs", [x for x in S if (edge(x) or -9) >= cut and x["ml"] >= 100 and own_over(x)])
o.c("the OWN read alone 2+ over the price (no weights), favorites", [x for x in S if x["own"] - x["p"] >= 0.02 and x["ml"] < 0])
o.c("the OWN read alone 2+ over the price (no weights), dogs", [x for x in S if x["own"] - x["p"] >= 0.02 and x["ml"] >= 100])
o.c("the own read 2+ over but the weights take it UNDER the price (the weights say no)", [x for x in S if x["own"] - x["p"] >= 0.02 and (edge(x) or 9) < 0])
o.c("the own read UNDER the price but the weights take it 2+ OVER (the weights say yes)", [x for x in S if x["own"] < x["p"] and (edge(x) or -9) >= 0.02])

o.h("C. WHERE - the weighed read 2+ over AND own-beats, by price band / tier / month / venue / games played")
P = [x for x in S if (edge(x) or -9) >= 0.02 and own_over(x)]
lib.cuts(o, "by price band", P, lambda x: lib.band(x["ml"]), BANDS)
lib.cuts(o, "by tier", P, lib.tier_of, ["P", "M", "L"])
lib.cuts(o, "by month", P, lib.phase, MONTHS)
lib.cuts(o, "by venue", P, lambda x: x["venue"], ["home", "away", "neutral"])
lib.cuts(o, "by games played (the side's)", P, lambda x: lib.bk(x["gn"], [4, 11, 16, 21, 26]), lib.bk_labels([4, 11, 16, 21, 26]))
lib.cuts(o, "by conference game", P, lambda x: "yes" if x.get("same_conf") else "no", ["yes", "no"])
o.c("favorites -101..-150 (the Lock band), home", [x for x in P if -150 <= x["ml"] <= -101 and x["venue"] == "home"])
o.c("favorites -101..-150, road / neutral", [x for x in P if -150 <= x["ml"] <= -101 and x["venue"] != "home"])
o.c("favorites -151..-250, home", [x for x in P if -250 <= x["ml"] <= -151 and x["venue"] == "home"])
o.c("favorites -151..-250, road / neutral", [x for x in P if -250 <= x["ml"] <= -151 and x["venue"] != "home"])
o.c("favorites, Jan-Mar conference, both teams 10+ games", [x for x in P if x["ml"] < 0 and not x["nd"] and x.get("same_conf") and x["gn"] >= 10 and (x.get("ogn") or 0) >= 10])
o.c("favorites, Jan-Mar conference, home", [x for x in P if x["ml"] < 0 and not x["nd"] and x.get("same_conf") and x["venue"] == "home"])
o.c("favorites, Nov-Dec", [x for x in P if x["ml"] < 0 and x["nd"]])
o.c("dogs +100..+150, home", [x for x in P if 100 <= x["ml"] <= 150 and x["venue"] == "home"])
o.c("dogs +100..+150, road", [x for x in P if 100 <= x["ml"] <= 150 and x["venue"] == "away"])
o.c("dogs +151..+350, home", [x for x in P if 151 <= x["ml"] <= 350 and x["venue"] == "home"])
o.c("dogs +151..+350, road", [x for x in P if 151 <= x["ml"] <= 350 and x["venue"] == "away"])
o.c("dogs, Jan-Mar conference", [x for x in P if x["ml"] >= 100 and not x["nd"] and x.get("same_conf")])
lib.cuts(o, "FAVORITES by tier", [x for x in P if x["ml"] < 0], lib.tier_of, ["P", "M", "L"])
lib.cuts(o, "DOGS by tier", [x for x in P if x["ml"] >= 100], lib.tier_of, ["P", "M", "L"])
lib.cuts(o, "FAVORITES by month", [x for x in P if x["ml"] < 0], lib.phase, MONTHS)
lib.cuts(o, "DOGS by month", [x for x in P if x["ml"] >= 100], lib.phase, MONTHS)

o.h("D. THE LOCK TEST as the engine runs it - a favorite whose weighed read is 56%+ AND beats the price, with the "
    "early-lock rule (no Lock before both teams have 3 games, half through 10)")
L = [x for x in S if x["ml"] < 0 and weighed(x) is not None and weighed(x) >= 0.56 and weighed(x) > x["p"]]
o.c("Lock-grade favorites (weighed 56%+ over the price), any price", L)
o.c("...and -101..-150 only (the band the Lock lives in)", [x for x in L if x["ml"] >= -150])
o.c("...-101..-150, own-beats too", [x for x in L if x["ml"] >= -150 and own_over(x)])
o.c("...-101..-150, own-beats, not -101..-119 (the S6 skip band)", [x for x in L if -150 <= x["ml"] <= -120 and own_over(x)])
o.c("...-120..-150, own-beats, both teams 10+ games", [x for x in L if -150 <= x["ml"] <= -120 and own_over(x) and x["gn"] >= 10 and (x.get("ogn") or 0) >= 10])
o.c("...-120..-150, own-beats, both 10+, home", [x for x in L if -150 <= x["ml"] <= -120 and own_over(x) and x["gn"] >= 10 and (x.get("ogn") or 0) >= 10 and x["venue"] == "home"])
o.c("...-120..-150, own-beats, both 10+, Jan-Mar", [x for x in L if -150 <= x["ml"] <= -120 and own_over(x) and x["gn"] >= 10 and (x.get("ogn") or 0) >= 10 and not x["nd"]])
o.c("...-120..-150, own-beats, games 3-9 (the half-unit window)", [x for x in L if -150 <= x["ml"] <= -120 and own_over(x) and 3 <= min(x["gn"], x.get("ogn") or 99) < 10])
o.c("...-120..-150, own-beats, the efficiency read 3+ over too", [x for x in L if -150 <= x["ml"] <= -120 and own_over(x) and x.get("eff") is not None and x["eff"] - x["p"] >= 0.03])
lib.cuts(o, "Lock-grade -120..-150 own-beats by tier", [x for x in L if -150 <= x["ml"] <= -120 and own_over(x)], lib.tier_of, ["P", "M", "L"])
lib.cuts(o, "Lock-grade -120..-150 own-beats by the edge (weighed - price)", [x for x in L if -150 <= x["ml"] <= -120 and own_over(x)], lambda x: lib.bk(edge(x), [0.01, 0.03, 0.05]), lib.bk_labels([0.01, 0.03, 0.05]))

o.h("E. THE DOG as the engine would gate it (score 4+, own-beats) - the college hoops Dog is OFF; this is what it would have done")
G = [x for x in S if x["ml"] >= 100 and x.get("dog_score") is not None and x["dog_score"] >= 4 and own_over(x)]
o.c("dog score 4+ and own-beats, +100..+350", G)
lib.cuts(o, "dog score 4+ own-beats by price band", G, lambda x: lib.band(x["ml"]), BANDS[3:])
lib.cuts(o, "dog score 4+ own-beats by tier", G, lib.tier_of, ["P", "M", "L"])
lib.cuts(o, "dog score 4+ own-beats by month", G, lib.phase, MONTHS)
o.c("dog score 6+ and own-beats", [x for x in G if x["dog_score"] >= 6])
o.c("dog score 4+, own-beats, home", [x for x in G if x["venue"] == "home"])
o.c("the college hoops floor dog as replayed: the best dog score a night (own-beats, +100..+350)", [])
best = {}
for x in G:
    k = (x["season"], x["night"])
    if k not in best or x["dog_score"] > best[k]["dog_score"]:
        best[k] = x
o.c("the best own-beats dog a night (score 4+)", list(best.values()))
o.save()
