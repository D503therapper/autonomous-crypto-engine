"""STUDY 1 - rest and schedule density (college hoops, regular season, closing prices; the OPEN 2023-25 = 2nd check).
Non-tournament = this game is NOT at a neutral site (the early-season events are; their back-to-back has its own 11/1
lead). 2-in-3 = last game 1-2 nights ago; b2b = 1 night; 3-in-5 = 2+ games in the 4 nights before; rest edge = this
side's nights off minus the opponent's; road trip = consecutive true road games incl. this one; travel = miles from the
road team's usual home floor to tonight's floor + time zones crossed (+ = flew east). Every condition: ATS (every side
in it), the ML dog +100..+350, the ML favorite -101..-150; and the early slice (team games 1-5, the owner's 11/3 focus)."""
import lib

R = lib.regular(lib.build())
o = lib.Out("s1")


def trio(name, sub, early=True):
    o.c(f"{name} | ATS", lib.spreads(sub), lib.profit_ats)
    o.c(f"{name} | dog +100..+350", lib.dogs(sub))
    o.c(f"{name} | fav -101..-150", lib.favs(sub))
    if early:
        e = [x for x in sub if x["gn"] <= 5]
        o.c(f"{name} | games 1-5 ATS", lib.spreads(e), lib.profit_ats)
        o.c(f"{name} | games 1-5 dog", lib.dogs(e))


NN = [x for x in R if not x["neutral"] and x.get("rest") is not None and x.get("orest") is not None]
o.h("BASE (non-neutral, both teams have a prior game)")
trio("every side", NN)

o.h("A. Density, non-tournament")
trio("b2b (1 night)", [x for x in NN if x["rest"] == 1])
trio("2-in-3 (1-2 nights)", [x for x in NN if x["rest"] <= 2])
trio("3-in-5", [x for x in NN if x["g5"] >= 2])
trio("2-in-3 vs a team on 3+ nights", [x for x in NN if x["rest"] <= 2 and x["orest"] >= 3])
trio("3+ nights vs a team on 2-in-3", [x for x in NN if x["rest"] >= 3 and x["orest"] <= 2])
trio("3-in-5 vs a team NOT 3-in-5", [x for x in NN if x["g5"] >= 2 and x["og5"] == 0])
trio("rest edge +3 nights or more (not 7+ layoff)", [x for x in NN if x["rest"] - x["orest"] >= 3 and x["rest"] <= 6])
trio("rest edge -3 or worse (opp not 7+ layoff)", [x for x in NN if x["orest"] - x["rest"] >= 3 and x["orest"] <= 6])
trio("Saturday-after-Thursday road (2 nights, away)", [x for x in NN if x["rest"] == 2 and x["side"] == "away"])

o.h("B. Road trip length (the road team)")
AW = [x for x in NN if x["side"] == "away"]
trio("road team, trip game 1", [x for x in AW if x["trip"] == 1])
trio("road team, trip game 2", [x for x in AW if x["trip"] == 2])
trio("road team, trip game 3+", [x for x in AW if x["trip"] >= 3])
trio("home team after a 2+ game road trip (first game home)", [x for x in NN if x["side"] == "home" and x.get("last") and x["last"]["venue"] == "away"
      and x.get("prev_i") is not None])

o.h("C. Travel and time zones (the road team)")
AM = [x for x in AW if x.get("miles") is not None]
trio("road, under 300 miles", [x for x in AM if x["miles"] < 300])
trio("road, 300-1000 miles", [x for x in AM if 300 <= x["miles"] < 1000])
trio("road, 1000+ miles", [x for x in AM if x["miles"] >= 1000])
trio("road, flew EAST 2+ zones", [x for x in AM if (x.get("tzd") or 0) >= 2])
trio("road, flew WEST 2+ zones", [x for x in AM if (x.get("tzd") or 0) <= -2])
trio("road, 1000+ miles on 2-in-3", [x for x in AM if x["miles"] >= 1000 and x["rest"] <= 2])
o.h("D. Neutral-site travel (the early-season events): the side that flew 1000+ vs the side under 500")
NT = [x for x in R if x["neutral"] and x.get("miles") is not None]
mi = {(x["id"], x["side"]): x["miles"] for x in NT}
far = [x for x in NT if x["miles"] >= 1000 and mi.get((x["id"], "home" if x["side"] == "away" else "away"), 9e9) < 500]
near = [x for x in NT if x["miles"] < 500 and mi.get((x["id"], "home" if x["side"] == "away" else "away"), -1) >= 1000]
trio("neutral, flew 1000+ vs a team under 500 away", far)
trio("neutral, under 500 vs a team that flew 1000+", near)
o.save()
