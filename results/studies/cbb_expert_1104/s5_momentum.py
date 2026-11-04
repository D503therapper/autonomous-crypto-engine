"""S5 - MOMENTUM AND PERFORMANCE (the owner, 11/4: "performances ... teams playing really good"): margin vs
expectation over the last 5 - against the LINE (cm5, the cover margin) and against the RATING (adjm5, margin minus the
Elo-expected margin - opponent-adjusted); whether the market lags real mid-season improvement (improve = the last 5
over the games before them); the dog that just beat a good team (confidence) vs the favorite that just did (letdown).
Prices 2018-26: train 2018-22, held 2023-25."""
import lib

rows = lib.regular(lib.build())
pr = [x for x in rows if x.get("ml")]
out = lib.Out("s5", train=lib.TRAIN_PRICE)
out.h("the table: every priced regular-season side 2018-26")
lib.three("base", pr, out)

out.h("A. PERFORMANCE OVER THE LINE, last 5 priced games (cover margin)")
c5 = [x for x in pr if x.get("cm5") is not None]
for lo, hi, nm in ((-99, -8, "-8-"), (-8, -3, "-8..-3"), (-3, 3, "flat"), (3, 8, "+3..8"), (8, 99, "+8+")):
    lib.three(f"cm5 {nm}", [x for x in c5 if lo <= x["cm5"] < hi], out)
lib.three("cm5 +8+ vs opp cm5 -3-", [x for x in c5 if x["cm5"] >= 8 and (x.get("opp_cm5") if x.get("opp_cm5") is not None else 0) <= -3], out)
lib.three("cm5 -8- vs opp cm5 +3+", [x for x in c5 if x["cm5"] <= -8 and (x.get("opp_cm5") if x.get("opp_cm5") is not None else 0) >= 3], out)

out.h("B. PERFORMANCE OVER THE RATING, last 5 (margin minus the Elo-expected margin, opponent-adjusted)")
a5 = [x for x in pr if x.get("adjm5") is not None]
for lo, hi, nm in ((-99, -10, "-10-"), (-10, -4, "-10..-4"), (-4, 4, "flat"), (4, 10, "+4..10"), (10, 99, "+10+")):
    lib.three(f"adjm5 {nm}", [x for x in a5 if lo <= x["adjm5"] < hi], out)

out.h("C. IMPROVING: the last 5 over the games before them (adjm5 - adjm_prev; both teams 10+ games)")
im = [x for x in pr if x.get("improve") is not None]
for lo, hi, nm in ((-99, -10, "-10- (falling apart)"), (-10, -5, "-10..-5"), (-5, 5, "flat"), (5, 10, "+5..10"), (10, 99, "+10+ (getting better)")):
    lib.three(f"improve {nm}", [x for x in im if lo <= x["improve"] < hi], out)
lib.three("improve +8+, games 10-20", [x for x in im if x["improve"] >= 8 and x["gn"] <= 20], out)
lib.three("improve +8+, games 21+", [x for x in im if x["improve"] >= 8 and x["gn"] > 20], out)
lib.three("improve +8+ vs opp improve -8-", [x for x in im if x["improve"] >= 8 and (x.get("opp_improve") if x.get("opp_improve") is not None else 0) <= -8], out)
lib.three("improve -8- vs opp improve +8+", [x for x in im if x["improve"] <= -8 and (x.get("opp_improve") if x.get("opp_improve") is not None else 0) >= 8], out)
lib.three("improve +8+, Jan-Mar", [x for x in im if x["improve"] >= 8 and lib.month(x) in ("01", "02", "03")], out)
lib.three("improve +8+ AND cm5 under +3 (better vs the rating, not yet vs the line)", [x for x in im if x["improve"] >= 8 and (x.get("cm5") if x.get("cm5") is not None else 0) < 3], out)
lib.three("improve +8+ AND cm5 +3+ (the line already sees it)", [x for x in im if x["improve"] >= 8 and (x.get("cm5") or 0) >= 3], out)

out.h("D. THE DOG THAT JUST BEAT A GOOD TEAM (confidence) / THE FAVORITE THAT JUST DID (letdown)")
bg = [x for x in pr if x.get("beat_good")]
lib.three("beat a top-25 team last game", bg, out)
lib.three("beat a top-25 team last game, as a dog that game too (upset_last)", [x for x in bg if x.get("upset_last")], out)
lib.three("beat a top-25 team last game, Nov-Dec", [x for x in bg if lib.month(x) in ("11", "12")], out)
lib.three("beat a top-25 team last game, Jan-Mar", [x for x in bg if lib.month(x) in ("01", "02", "03")], out)
lib.three("opp beat a top-25 team last game (the letdown side across)", [x for x in pr if x.get("opp_beat_good")], out)
lib.three("opp beat a top-25 last game AND I'm at home", [x for x in pr if x.get("opp_beat_good") and x["venue"] == "home"], out)
lib.three("lost to a top-25 team last game (no shame)", [x for x in pr if x.get("lost_to_good")], out)
lib.three("won last by 15+ (big win)", [x for x in pr if x.get("big_win")], out)
lib.three("opp won last by 15+", [x for x in pr if x.get("opp_big_win")], out)
lib.three("won last as a +150 dog (upset hangover)", [x for x in pr if x.get("upset_last")], out)
lib.three("opp won last as a +150 dog", [x for x in pr if x.get("opp_upset_last")], out)
out.save()
