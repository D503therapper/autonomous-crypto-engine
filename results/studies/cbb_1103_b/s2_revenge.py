"""STUDY 2 - revenge and rematches: conference teams in their SECOND regular-season meeting of a season (inferred
conference, both meetings regular season, not at a neutral site), by how the first one went (margin, who hosted) and
whether the floor swapped; plus the THIRD meeting (the conference tournament) after a sweep. Closing prices; the OPEN
(2023-25) is the 2nd check."""
import lib

R = lib.regular(lib.build())
o = lib.Out("s2")
SM = [x for x in R if x["same_conf"] and not x["neutral"] and len(x["prev_meet"]) == 1
      and x["prev_meet"][0]["stype"] == "2" and x["prev_meet"][0]["venue"] != "neutral"]


def trio(name, sub):
    o.c(f"{name} | ATS", lib.spreads(sub), lib.profit_ats)
    o.c(f"{name} | dog +100..+350", lib.dogs(sub))
    o.c(f"{name} | fav -101..-150", lib.favs(sub))
    o.c(f"{name} | fav -151..-400", [x for x in sub if x.get("ml") is not None and -400 <= x["ml"] <= -151])


o.h("BASE: every conference second meeting (home / road)")
trio("2nd meeting, every side", SM)
o.h("A. By the first meeting's margin (this side's view)")
for lo, hi, lab in ((-200, -20, "lost it by 20+"), (-19, -10, "lost by 10-19"), (-9, -1, "lost by 1-9"),
                    (1, 9, "won by 1-9"), (10, 19, "won by 10-19"), (20, 200, "won by 20+")):
    trio(f"2nd meeting, {lab}", [x for x in SM if lo <= x["prev_meet"][0]["margin"] <= hi])
o.h("B. Floor swap (first at the other place, now at home) x the first result")
for lab, f in (("lost at their place, now home", lambda m: m["venue"] == "away" and m["margin"] < 0),
               ("lost at home, now away", lambda m: m["venue"] == "home" and m["margin"] < 0),
               ("won at their place, now home", lambda m: m["venue"] == "away" and m["margin"] > 0),
               ("won at home, now away", lambda m: m["venue"] == "home" and m["margin"] > 0),
               ("blown out 15+ AT HOME, now away (revenge on the road)", lambda m: m["venue"] == "home" and m["margin"] <= -15),
               ("blown out 15+ on the road, now home (revenge at home)", lambda m: m["venue"] == "away" and m["margin"] <= -15)):
    trio(f"2nd meeting, {lab}", [x for x in SM if f(x["prev_meet"][0])])
o.h("C. Lost the first one as the FAVORITE (an upset) / won it as a dog")
idx = {}
for x in R:
    idx[(x["id"], x["team"])] = x
# first meeting's price for this side: find the earlier row of this team vs this opponent this season
by_pair = {}
for x in R:
    by_pair.setdefault((x["season"], x["team"], x["opp"]), []).append(x)
up, dw = [], []
for x in SM:
    prev = [y for y in by_pair.get((x["season"], x["team"], x["opp"]), []) if y["night"] < x["night"]]
    if not prev or prev[-1].get("ml") is None:
        continue
    p = prev[-1]
    if p["ml"] < 0 and not p["won"]:
        up.append(x)
    if p["ml"] > 0 and p["won"]:
        dw.append(x)
trio("2nd meeting, got upset in the 1st (was the fav, lost)", up)
trio("2nd meeting, pulled the upset in the 1st (was the dog, won)", dw)
o.h("D. Early conference rematches (the 2nd meeting before Feb 1) vs late")
trio("2nd meeting before Feb 1, lost the 1st by 10+", [x for x in SM if x["start"][5:7] in ("12", "01") and x["prev_meet"][0]["margin"] <= -10])
trio("2nd meeting Feb+, lost the 1st by 10+", [x for x in SM if x["start"][5:7] in ("02", "03") and x["prev_meet"][0]["margin"] <= -10])
o.h("E. Third meeting (conference tournament, neutral / any) after losing both")
TM = [x for x in R if len(x["prev_meet"]) == 2 and all(m["stype"] == "2" for m in x["prev_meet"])]
trio("3rd meeting, lost both", [x for x in TM if all(m["margin"] < 0 for m in x["prev_meet"])])
trio("3rd meeting, won both", [x for x in TM if all(m["margin"] > 0 for m in x["prev_meet"])])
trio("3rd meeting, split", [x for x in TM if (x["prev_meet"][0]["margin"] > 0) != (x["prev_meet"][1]["margin"] > 0)])
o.h("F. Non-conference rematch in the same season (an early-event team met again)")
NC = [x for x in R if not x["same_conf"] and len(x["prev_meet"]) >= 1]
trio("non-conference rematch, lost the 1st", [x for x in NC if x["prev_meet"][-1]["margin"] < 0])
o.save()
