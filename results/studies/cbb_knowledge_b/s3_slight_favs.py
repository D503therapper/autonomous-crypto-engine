"""S3 - SLIGHT FAVORITES (the owner's ask): which college hoops -101..-150 moneyline favorites WIN against the price?
The 11/3 weights mark the bad ones down (away in Nov-Dec -3, the efficiency read 3+ under -3, the top scorer out -2);
this looks for the GOOD ones - home vs road, the rest edge, the rebounding edge, the efficiency / Elo reads agreeing,
form, conference play - one cut at a time, then the honest combos, each with its dose. Regular season 2018-25 at ESPN's
close; train 2018-22, held out 2023 / 2024 / 2025 apart; the ESPN open (2023-25) is the second check."""
import lib

rows = lib.regular(lib.build())
FV = [x for x in rows if x.get("ml") is not None and -150 <= x["ml"] <= -101 and x.get("own") is not None]
o = lib.Out("s3")
o.note(f"slight favorites -101..-150: {len(FV)} (train {sum(1 for x in FV if x['season'] <= 2022)}, held {sum(1 for x in FV if x['season'] in lib.HELD)})")
w, p_, n = lib.win_vs_price(FV)
o.note(f"they won {w * 100:.1f}%; the no-vig close said {p_ * 100:.1f}%")
eff_gap = lambda x: (x["eff"] - x["p"]) if x.get("eff") is not None else None
own_gap = lambda x: x["own"] - x["p"]
raw_gap = lambda x: (x["raw"] - x["p"]) if x.get("raw") is not None else None
rest_gap = lambda x: (x["rest"] - x["orest"]) if x.get("rest") is not None and x.get("orest") is not None else None
EG = [-0.06, -0.03, 0, 0.03, 0.06]

o.h("A. THE BASE and the single cuts")
o.c("every slight favorite", FV)
lib.cuts(o, "venue", FV, lambda x: x["venue"], ["home", "away", "neutral"])
lib.cuts(o, "month", FV, lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"])
lib.cuts(o, "HOME slight fav by month", [x for x in FV if x["venue"] == "home"], lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"])
lib.cuts(o, "ROAD slight fav by month", [x for x in FV if x["venue"] == "away"], lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"])
lib.cuts(o, "tier", FV, lib.tier_of, ["P", "M", "L"])
lib.cuts(o, "conference game", FV, lambda x: "yes" if x.get("same_conf") else "no", ["yes", "no"])
lib.cuts(o, "games played", FV, lambda x: lib.bk(x["gn"], [4, 11, 21]), lib.bk_labels([4, 11, 21]))
lib.cuts(o, "rest gap (mine - theirs)", FV, lambda x: lib.bk(rest_gap(x), [-2, 0, 1, 2, 4]), lib.bk_labels([-2, 0, 1, 2, 4]))
lib.cuts(o, "rebound margin gap (both 5+ box games)", FV, lambda x: lib.bk(lib.reb_gap(x), [-8, -4, 0, 4, 8]), lib.bk_labels([-8, -4, 0, 4, 8]))
lib.cuts(o, "efficiency read - no-vig price", FV, lambda x: lib.bk(eff_gap(x), EG), lib.bk_labels(EG))
lib.cuts(o, "engine own read - no-vig price", FV, lambda x: lib.bk(own_gap(x), [-0.03, 0, 0.02, 0.04]), lib.bk_labels([-0.03, 0, 0.02, 0.04]))
lib.cuts(o, "raw Elo read - no-vig price", FV, lambda x: lib.bk(raw_gap(x), [-0.1, -0.05, 0, 0.05, 0.1]), lib.bk_labels([-0.1, -0.05, 0, 0.05, 0.1]))
lib.cuts(o, "win streak", FV, lambda x: lib.bk(x.get("streak"), [-3, 0, 3, 6]), lib.bk_labels([-3, 0, 3, 6]))
lib.cuts(o, "last margin", FV, lambda x: lib.bk(x.get("last_m"), [-15, -5, 0, 5, 15]), lib.bk_labels([-15, -5, 0, 5, 15]))
lib.cuts(o, "opp last margin", FV, lambda x: lib.bk(x.get("olast_m"), [-15, -5, 0, 5, 15]), lib.bk_labels([-15, -5, 0, 5, 15]))
lib.cuts(o, "the dog's study points (sports.dog_spots replayed) - the fav reads the other way", FV, lambda x: lib.bk(-lib._opp_pts(x) if lib._opp_pts(x) is not None else None, [-4, -2, 0, 2, 4]), lib.bk_labels([-4, -2, 0, 2, 4]))
lib.cuts(o, "win % so far (5+ games)", FV, lambda x: lib.bk(x["wpct"] if x["gn"] > 5 else None, [0.4, 0.6, 0.8]), lib.bk_labels([0.4, 0.6, 0.8]))
lib.cuts(o, "ats gap (hot-ATS +)", FV, lambda x: lib.bk(lib.ats_gap(x), [-5, -2, 2, 5]), lib.bk_labels([-5, -2, 2, 5]))
lib.cuts(o, "price", FV, lambda x: lib.bk(x["ml"], [-140, -130, -120, -110]), lib.bk_labels([-140, -130, -120, -110]))
lib.cuts(o, "the spread on the same favorite", FV, lambda x: lib.bk(-x["sp"] if x.get("sp") is not None else None, [1, 2, 3, 4]), lib.bk_labels([1, 2, 3, 4]))
lib.cuts(o, "line move open->close (to the fav +)", FV, lambda x: lib.bk(x.get("move"), [-0.03, -0.01, 0.01, 0.03]), lib.bk_labels([-0.03, -0.01, 0.01, 0.03]))

o.h("B. THE GOOD ONES - honest combos (each a single idea stacked once), with the dose")
home = [x for x in FV if x["venue"] == "home"]
jm = [x for x in FV if not x["nd"]]
agree = lambda x, k=0.03: (eff_gap(x) or -9) >= k
o.c("HOME slight fav, Jan-Mar", [x for x in home if not x["nd"]])
o.c("home slight fav, the efficiency read 3+ OVER the price", [x for x in home if agree(x)])
o.c("home slight fav, the efficiency read 3+ over, Jan-Mar", [x for x in home if agree(x) and not x["nd"]])
o.c("home slight fav, the efficiency read 3+ over, Nov-Dec", [x for x in home if agree(x) and x["nd"]])
o.c("home slight fav, the efficiency read 6+ over", [x for x in home if agree(x, 0.06)])
o.c("home slight fav, the efficiency read 0..3 over", [x for x in home if 0 <= (eff_gap(x) or -9) < 0.03])
o.c("home slight fav, the efficiency read within 3 (the 'agrees' band)", [x for x in home if abs(eff_gap(x) or 9) < 0.03])
o.c("ANY slight fav, the efficiency read 3+ over", [x for x in FV if agree(x)])
o.c("road slight fav, the efficiency read 3+ over", [x for x in FV if x["venue"] == "away" and agree(x)])
o.c("road slight fav, the efficiency read 3+ over, Jan-Mar", [x for x in FV if x["venue"] == "away" and agree(x) and not x["nd"]])
o.c("neutral slight fav, the efficiency read 3+ over", [x for x in FV if x["venue"] == "neutral" and agree(x)])
o.c("slight fav, efficiency 3+ over AND the engine's own read over the price", [x for x in FV if agree(x) and own_gap(x) > 0])
o.c("slight fav, efficiency 3+ over AND raw Elo 5+ over", [x for x in FV if agree(x) and (raw_gap(x) or -9) >= 0.05])
o.c("slight fav, efficiency 3+ over, both teams 10+ games", [x for x in FV if agree(x) and x["gn"] >= 10 and (x.get("ogn") or 0) >= 10])
o.c("slight fav, efficiency 3+ over, conference game", [x for x in FV if agree(x) and x.get("same_conf")])
o.c("slight fav, efficiency 3+ over, non-conference", [x for x in FV if agree(x) and not x.get("same_conf")])
lib.cuts(o, "slight fav, efficiency 3+ over, by tier", [x for x in FV if agree(x)], lib.tier_of, ["P", "M", "L"])
lib.cuts(o, "slight fav, efficiency 3+ over, by price", [x for x in FV if agree(x)], lambda x: lib.bk(x["ml"], [-130, -115]), lib.bk_labels([-130, -115]))
o.c("home slight fav with 2+ more nights rest", [x for x in home if (rest_gap(x) or 0) >= 2])
o.c("home slight fav with 2+ more nights rest, Jan-Mar", [x for x in home if (rest_gap(x) or 0) >= 2 and not x["nd"]])
o.c("home slight fav vs a favorite on 1 night rest (b2b)", [x for x in home if x.get("orest") == 1])
o.c("home slight fav out-rebounding by 4+ a game", [x for x in home if (lib.reb_gap(x) or 0) >= 4])
o.c("home slight fav out-rebounding by 4+, efficiency 3+ over", [x for x in home if (lib.reb_gap(x) or 0) >= 4 and agree(x)])
o.c("slight fav out-rebounding by 4+, efficiency 3+ over (any venue)", [x for x in FV if (lib.reb_gap(x) or 0) >= 4 and agree(x)])
o.c("home slight fav off a win, vs a team off a loss", [x for x in home if x.get("last_won") and x.get("olast_won") is False])
o.c("home slight fav off a win vs a team off a loss, efficiency 3+ over", [x for x in home if x.get("last_won") and x.get("olast_won") is False and agree(x)])
o.c("home slight fav on a 3+ win streak", [x for x in home if (x.get("streak") or 0) >= 3])
o.c("home slight fav, the COLD-ATS side (gap -3)", [x for x in home if (lib.ats_gap(x) or 0) <= -3])
o.c("slight fav, cold-ATS (gap -3), efficiency 3+ over", [x for x in FV if (lib.ats_gap(x) or 0) <= -3 and agree(x)])
o.c("home slight fav, Jan-Mar, conference, efficiency 3+ over", [x for x in home if not x["nd"] and x.get("same_conf") and agree(x)])
o.c("home slight fav, Jan-Mar, efficiency 3+ over, 2+ more rest", [x for x in home if not x["nd"] and agree(x) and (rest_gap(x) or 0) >= 2])
o.c("slight fav the dog's study points favor by 2+ (dog_spots -2 or worse across)", [x for x in FV if (lib._opp_pts(x) or 0) <= -2])
o.c("slight fav the dog's study points favor by 2+, efficiency 3+ over", [x for x in FV if (lib._opp_pts(x) or 0) <= -2 and agree(x)])
o.c("slight fav the dog's study points favor by 4+", [x for x in FV if (lib._opp_pts(x) or 0) <= -4])
o.c("slight fav with NO 11/3 favorite fade on it (away-ND / eff-under / top-out)", [x for x in FV if not any(k in (x.get("fav_w") or {}) for k in ("away_nd", "eff_under", "top_out"))])
o.c("...and the efficiency read 3+ over", [x for x in FV if not any(k in (x.get("fav_w") or {}) for k in ("away_nd", "eff_under", "top_out")) and agree(x)])
o.c("slight fav whose top scorer missed its last game (known fade)", [x for x in FV if x.get("top_out")])
o.c("slight fav vs a DOG whose top scorer missed its last game", [x for x in FV if x.get("o_top_out")])
o.c("slight fav vs a dog whose top scorer missed, efficiency 3+ over", [x for x in FV if x.get("o_top_out") and agree(x)])
o.c("slight fav vs a dog on a 5+ skid", [x for x in FV if (x.get("o_streak") or 0) <= -5])
o.c("slight fav vs a dog on a 5+ skid, Jan-Mar", [x for x in FV if (x.get("o_streak") or 0) <= -5 and not x["nd"]])
o.c("slight fav vs an early road dog (games 1-3)", [x for x in FV if x["venue"] == "home" and (x.get("ogn") or 99) <= 3])
o.c("slight fav vs a ranked road dog, Nov-Dec", [x for x in FV if x["venue"] == "home" and x.get("orank25") and x["nd"]])

o.h("C. THE DOSE on the efficiency agreement (home, Jan-Mar) - does more agreement pay more?")
lib.cuts(o, "home slight fav Jan-Mar by efficiency gap", [x for x in home if not x["nd"]], lambda x: lib.bk(eff_gap(x), [-0.06, -0.03, 0, 0.03, 0.06, 0.1]), lib.bk_labels([-0.06, -0.03, 0, 0.03, 0.06, 0.1]))
lib.cuts(o, "any slight fav by efficiency gap, both 10+ games", [x for x in FV if x["gn"] >= 10 and (x.get("ogn") or 0) >= 10], lambda x: lib.bk(eff_gap(x), [-0.06, -0.03, 0, 0.03, 0.06, 0.1]), lib.bk_labels([-0.06, -0.03, 0, 0.03, 0.06, 0.1]))
o.save()
