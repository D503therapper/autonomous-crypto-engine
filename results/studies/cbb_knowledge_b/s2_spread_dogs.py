"""S2 - SPREAD UNDERDOGS: which college hoops spread dogs COVER (graded at the spread's own juice)? Home dogs, dogs off
a loss, dogs vs a team off a big win, big dogs 15+ by tier, conference dogs late in the season - and every cut not
already tested (the 11/3 studies did: the big home favorite 12+ (-8% ATS = the dog side ~even), the early road dog,
the ranked road team, the hot-ATS side, the glass, the top scorer out, rest 4-5 vs 2, the Thursday-Saturday team, revenge,
letdown / lookahead, travel, luck, variance, pace). Regular season 2018-25 at ESPN's close; train 2018-22, held out
2023 / 2024 / 2025 apart. No spread opens on file - the second check is the moneyline on the same side where one exists."""
import lib

rows = lib.regular(lib.build())
SD = [x for x in rows if x.get("cover") is not None and x.get("sp") is not None and x["sp"] > 0]
o = lib.Out("s2")
A = lib.profit_ats
o.note(f"spread dogs with a result: {len(SD)} (train {sum(1 for x in SD if x['season'] <= 2022)}, held {sum(1 for x in SD if x['season'] in lib.HELD)})")
SIZE = [3.5, 7, 11, 15, 21]
sz = lambda x: lib.bk(x["sp"], SIZE)
SZL = lib.bk_labels(SIZE)

o.h("A. THE BASE - every spread dog, by the size of the number")
o.c("every spread dog", SD, A)
lib.cuts(o, "spread dog by points", SD, sz, SZL, A)
lib.cuts(o, "spread dog by venue", SD, lambda x: x["venue"], ["home", "away", "neutral"], A)

o.h("B. HOME DOGS")
H = [x for x in SD if x["venue"] == "home"]
lib.cuts(o, "home dog by points", H, sz, SZL, A)
lib.cuts(o, "home dog by month", H, lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"], A)
lib.cuts(o, "home dog by tier", H, lib.tier_of, ["P", "M", "L"], A)
lib.cuts(o, "home dog, conference game", H, lambda x: "yes" if x.get("same_conf") else "no", ["yes", "no"], A)
o.c("home dog vs a ranked (top-25 Elo) road team, Jan-Mar", [x for x in H if x.get("orank25") and not x["nd"]], A)
o.c("home dog 7+ vs a ranked road team, Jan-Mar", [x for x in H if x.get("orank25") and not x["nd"] and x["sp"] >= 7], A)

o.h("C. FORM - dogs off a loss / a win, off a blowout, vs a team off a big win (the letdown spot)")
lib.cuts(o, "dog off", SD, lambda x: None if x.get("last_won") is None else ("a loss" if not x["last_won"] else "a win"), ["a loss", "a win"], A)
lib.cuts(o, "dog's last margin", SD, lambda x: lib.bk(x.get("last_m"), [-20, -10, 0, 10, 20]), lib.bk_labels([-20, -10, 0, 10, 20]), A)
lib.cuts(o, "opp's last margin (the favorite off...)", SD, lambda x: lib.bk(x.get("olast_m"), [-10, 0, 10, 20, 30]), lib.bk_labels([-10, 0, 10, 20, 30]), A)
o.c("dog vs a favorite off a 20+ win, home / road", [x for x in SD if (x.get("olast_m") or 0) >= 20 and x["venue"] != "neutral"], A)
o.c("dog vs a favorite off a 20+ win AND the dog off a loss", [x for x in SD if (x.get("olast_m") or 0) >= 20 and x.get("last_won") is False], A)
o.c("dog vs a favorite off a 20+ win, conference game", [x for x in SD if (x.get("olast_m") or 0) >= 20 and x.get("same_conf")], A)
o.c("dog vs a favorite off a 20+ win over a ranked team", [x for x in SD if (x.get("olast_m") or 0) >= 20 and x.get("olast") and x["olast"].get("oelo") is not None and x["olast"]["oelo"] >= (x.get("cut25") or 9e9)], A)
o.c("dog vs a favorite off a 20+ win, the favorite laying 7+", [x for x in SD if (x.get("olast_m") or 0) >= 20 and x["sp"] >= 7], A)
o.c("dog off a 20+ loss (the bounce)", [x for x in SD if (x.get("last_m") or 0) <= -20], A)
o.c("dog off a 20+ loss at home", [x for x in SD if (x.get("last_m") or 0) <= -20 and x["venue"] == "home"], A)
o.c("dog off a win AS A DOG (won its last as a plus-money side)", [x for x in SD if x.get("last") and x["last"].get("ml") and x["last"]["ml"] >= 100 and x["last"]["won"]], A)
lib.cuts(o, "dog win streak", SD, lambda x: lib.bk(x.get("streak"), [-5, -3, 0, 3]), lib.bk_labels([-5, -3, 0, 3]), A)
lib.cuts(o, "opp win streak", SD, lambda x: lib.bk(x.get("o_streak"), [-3, 0, 3, 6, 10]), lib.bk_labels([-3, 0, 3, 6, 10]), A)
o.c("dog vs a favorite on a 10+ game win streak", [x for x in SD if (x.get("o_streak") or 0) >= 10], A)
o.c("dog vs a favorite on a 10+ game win streak, Jan-Mar", [x for x in SD if (x.get("o_streak") or 0) >= 10 and not x["nd"]], A)

o.h("D. BIG DOGS 15+ by tier / venue / month (the big home favorite 12+ -8% ATS is known - this is the rest)")
BIG = [x for x in SD if x["sp"] >= 15]
lib.cuts(o, "big dog 15+ by tier", BIG, lib.tier_of, ["P", "M", "L"], A)
lib.cuts(o, "big dog 15+ by venue", BIG, lambda x: x["venue"], ["home", "away", "neutral"], A)
lib.cuts(o, "big dog 15+ by month", BIG, lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"], A)
lib.cuts(o, "big ROAD dog 15+ by tier", [x for x in BIG if x["venue"] == "away"], lib.tier_of, ["P", "M", "L"], A)
lib.cuts(o, "big road dog 15+ by month", [x for x in BIG if x["venue"] == "away"], lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"], A)
o.c("big road dog 15+, conference game", [x for x in BIG if x["venue"] == "away" and x.get("same_conf")], A)
o.c("big road dog 15+, non-conference (the buy game)", [x for x in BIG if x["venue"] == "away" and not x.get("same_conf")], A)
o.c("big road dog 15+, low-major visiting a power team", [x for x in BIG if x["venue"] == "away" and x.get("tier") == "low" and x.get("otier") == "power"], A)
o.c("big road dog 15+, low vs low", [x for x in BIG if x["venue"] == "away" and x.get("tier") == "low" and x.get("otier") == "low"], A)
lib.cuts(o, "big dog 20+ by venue", [x for x in SD if x["sp"] >= 20], lambda x: x["venue"], ["home", "away", "neutral"], A)
o.c("big dog 15+ in its games 1-5", [x for x in BIG if x["gn"] <= 5], A)
o.c("big dog 15+ in its games 1-5 vs a favorite in ITS games 1-5", [x for x in BIG if x["gn"] <= 5 and (x.get("ogn") or 99) <= 5], A)

o.h("E. CONFERENCE PLAY LATE (Feb-Mar, same conference)")
LATE = [x for x in SD if x.get("same_conf") and x.get("month") in ("02", "03")]
o.c("conference dog, Feb-Mar", LATE, A)
lib.cuts(o, "conference dog Feb-Mar by venue", LATE, lambda x: x["venue"], ["home", "away", "neutral"], A)
lib.cuts(o, "conference dog Feb-Mar by points", LATE, sz, SZL, A)
lib.cuts(o, "conference HOME dog Feb-Mar by points", [x for x in LATE if x["venue"] == "home"], sz, SZL, A)
lib.cuts(o, "conference dog Feb-Mar by tier", LATE, lib.tier_of, ["P", "M", "L"], A)
o.c("conference dog Feb-Mar, 2nd meeting (lost the 1st)", [x for x in LATE if len(x.get("prev_meet") or []) == 1 and x["prev_meet"][0]["margin"] < 0], A)
o.c("conference dog Feb-Mar, 2nd meeting (WON the 1st)", [x for x in LATE if len(x.get("prev_meet") or []) == 1 and x["prev_meet"][0]["margin"] > 0], A)
o.c("conference dog Feb-Mar, 2nd meeting lost the 1st by 15+", [x for x in LATE if len(x.get("prev_meet") or []) == 1 and x["prev_meet"][0]["margin"] <= -15], A)
o.c("conference dog Feb-Mar with a .500+ record", [x for x in LATE if (x.get("wpct") or 0) >= 0.5], A)
o.c("conference dog Feb-Mar under .300", [x for x in LATE if x.get("wpct") is not None and x["wpct"] < 0.3], A)
o.c("conference dog in March (the last week / tournaments)", [x for x in SD if x.get("same_conf") and x.get("month") == "03"], A)
o.c("conference HOME dog Jan (the first conference weeks)", [x for x in SD if x.get("same_conf") and x.get("month") == "01" and x["venue"] == "home"], A)

o.h("F. CUTS NOT TRIED BEFORE - rest, the model's number, availability, juice, the price mismatch")
lib.cuts(o, "dog rest gap (mine - theirs, nights)", SD, lambda x: lib.bk((x["rest"] - x["orest"]) if x.get("rest") is not None and x.get("orest") is not None else None, [-3, -1, 1, 3]), lib.bk_labels([-3, -1, 1, 3]), A)
o.c("dog on a back-to-back (rest 1) vs a rested favorite (3+)", [x for x in SD if x.get("rest") == 1 and (x.get("orest") or 0) >= 3], A)
o.c("dog rested 3+ vs a favorite on a back-to-back", [x for x in SD if (x.get("rest") or 0) >= 3 and x.get("orest") == 1], A)
em = lambda x: (x["eff_m"] + x["sp"]) if x.get("eff_m") is not None and x["gn"] >= 10 and (x.get("ogn") or 0) >= 10 else None
lib.cuts(o, "efficiency margin vs the spread (+ = the model likes the dog), both 10+ games", SD, lambda x: lib.bk(em(x), [-6, -3, 0, 3, 6]), lib.bk_labels([-6, -3, 0, 3, 6]), A)
o.c("home dog the model likes by 3+ (10+ games)", [x for x in SD if (em(x) or -99) >= 3 and x["venue"] == "home"], A)
o.c("road dog the model likes by 3+ (10+ games)", [x for x in SD if (em(x) or -99) >= 3 and x["venue"] == "away"], A)
o.c("dog the model likes by 3+ AND vs a favorite off a 20+ win", [x for x in SD if (em(x) or -99) >= 3 and (x.get("olast_m") or 0) >= 20], A)
o.c("dog the model likes by 3+, Feb-Mar conference", [x for x in LATE if (em(x) or -99) >= 3], A)
rawm = lambda x: (x["em"] + x["sp"]) if x.get("em") is not None and x["gn"] >= 10 and (x.get("ogn") or 0) >= 10 else None
lib.cuts(o, "the engine's Elo margin vs the spread (+ = likes the dog), both 10+ games", SD, lambda x: lib.bk(rawm(x), [-6, -3, 0, 3, 6]), lib.bk_labels([-6, -3, 0, 3, 6]), A)
o.c("dog whose top scorer missed its last game (known fade)", [x for x in SD if x.get("top_out")], A)
o.c("dog vs a favorite whose top scorer missed its last game", [x for x in SD if x.get("o_top_out")], A)
o.c("dog vs a favorite whose top scorer missed its last game, laying 7+", [x for x in SD if x.get("o_top_out") and x["sp"] >= 7], A)
lib.cuts(o, "dog's juice", SD, lambda x: "plus" if (x.get("spodds") or -110) >= 100 else "-105..-100" if x["spodds"] >= -105 else "-110" if x["spodds"] >= -112 else "-113 and worse", ["plus", "-105..-100", "-110", "-113 and worse"], A)
mm = lambda x: (x["p"] - (1 - lib.sig(0.1537 * x["sp"]))) if x.get("p") is not None else None   # the ML's chance vs what the spread implies
lib.cuts(o, "dog's moneyline chance minus the spread-implied chance (the two markets disagree)", SD, lambda x: lib.bk(mm(x), [-0.04, -0.015, 0.015, 0.04]), lib.bk_labels([-0.04, -0.015, 0.015, 0.04]), A)
o.c("dog on a 2-in-3 (g3 2+) at home", [x for x in SD if (x.get("g3") or 0) >= 2 and x["venue"] == "home"], A)
o.c("dog in its first game after 8+ days off", [x for x in SD if (x.get("rest") or 0) >= 8], A)
o.c("dog vs a favorite in its first game after 8+ days off", [x for x in SD if (x.get("orest") or 0) >= 8], A)
o.c("dog that covered its last 3", [x for x in SD if (x.get("ats") or 0) >= 3], A)
o.c("dog that failed to cover its last 3", [x for x in SD if (x.get("ats") or 0) <= -3], A)
o.c("dog getting 3.5-10.5 on a Saturday", [x for x in SD if 3.5 <= x["sp"] <= 10.5 and x.get("dow") == 5], A)
o.c("dog getting 3.5-10.5 on a weeknight (Mon-Thu)", [x for x in SD if 3.5 <= x["sp"] <= 10.5 and x.get("dow") in (0, 1, 2, 3)], A)
o.c("dog in a big slate (60+ priced games)", [x for x in SD if (x.get("slate") or 0) >= 60], A)
o.c("dog in a small slate (under 15 priced games)", [x for x in SD if 0 < (x.get("slate") or 0) < 15], A)
o.save()
