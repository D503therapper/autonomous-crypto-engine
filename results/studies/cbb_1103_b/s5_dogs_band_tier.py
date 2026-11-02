"""STUDY 5 - college hoops underdog moneylines +100..+350 by price band x conference tier x stage of the season, weighted
toward OPENING WEEK and the first 2-3 weeks (each team's games 1-5) - the owner, 11/3: "especially opening week ... so
many games, so many upsets ... huge edges to be had". Closing ML; the OPEN (2023-25) is the 2nd check.
Stages: OPENING WEEK = the season's first 7 nights (by date), G1-2 / G3-5 = the dog's own game number, G6+ Nov-Dec,
CONF = Jan-Mar regular season. Tier of the dog vs the favorite (power / mid / low; 'none' = non-D1, dropped)."""
import lib
from collections import defaultdict

R = lib.regular(lib.build())
first_night = {}
for x in R:
    first_night[x["season"]] = min(first_night.get(x["season"], 10**9), x["night"])
for x in R:
    x["wk"] = (x["night"] - first_night[x["season"]]) // 7 + 1


def stage(x):
    if x["wk"] == 1:
        return "opening week"
    if x["start"][5:7] in ("11", "12"):
        return "G1-5 after week 1" if x["gn"] <= 5 else "G6+ Nov-Dec"
    return "Jan-Mar"


o = lib.Out("s5")
D = [x for x in lib.dogs(R) if x["tier"] != "none" and x["otier"] != "none"]
o.h("A. Every dog by stage (the base the cells below are judged against)")
for sg in ("opening week", "G1-5 after week 1", "G6+ Nov-Dec", "Jan-Mar"):
    o.c(f"dog, {sg}", [x for x in D if stage(x) == sg])
o.c("dog, season weeks 1-3", [x for x in D if x["wk"] <= 3])
for w in range(1, 7):
    o.c(f"dog, season week {w}", [x for x in D if x["wk"] == w])

o.h("B. Price band x stage")
BANDS = ((100, 129), (130, 159), (160, 199), (200, 249), (250, 350))
for lo, hi in BANDS:
    for sg in ("opening week", "G1-5 after week 1", "G6+ Nov-Dec", "Jan-Mar"):
        o.c(f"dog +{lo}..+{hi}, {sg}", [x for x in D if lo <= x["ml"] <= hi and stage(x) == sg])

o.h("C. Tier matchup (dog tier v fav tier) x early (weeks 1-3) / Dec / Jan-Mar")
for dt in ("power", "mid", "low"):
    for ft in ("power", "mid", "low"):
        sub = [x for x in D if x["tier"] == dt and x["otier"] == ft]
        if len(sub) < 150:
            continue
        o.c(f"{dt} dog v {ft} fav, weeks 1-3", [x for x in sub if x["wk"] <= 3])
        o.c(f"{dt} dog v {ft} fav, week 4+ Nov-Dec", [x for x in sub if x["wk"] > 3 and x["start"][5:7] in ("11", "12")])
        o.c(f"{dt} dog v {ft} fav, Jan-Mar", [x for x in sub if x["start"][5:7] not in ("11", "12")])

o.h("D. Venue x early (weeks 1-3) vs later Nov-Dec")
for v in ("home", "away", "neutral"):
    o.c(f"{v} dog, opening week", [x for x in D if x["venue"] == v and x["wk"] == 1])
    o.c(f"{v} dog, weeks 2-3", [x for x in D if x["venue"] == v and 2 <= x["wk"] <= 3])
    o.c(f"{v} dog, week 4+ Nov-Dec", [x for x in D if x["venue"] == v and x["wk"] > 3 and x["start"][5:7] in ("11", "12")])
    o.c(f"{v} dog, Jan-Mar", [x for x in D if x["venue"] == v and x["start"][5:7] not in ("11", "12")])

o.h("E. Opening-week / weeks 1-3 dog x band x venue (the owner's 'huge edges' question, sliced finer)")
for lo, hi in ((100, 159), (160, 249), (250, 350)):
    for v in ("home", "away", "neutral"):
        o.c(f"dog +{lo}..+{hi} {v}, weeks 1-3", [x for x in D if lo <= x["ml"] <= hi and x["venue"] == v and x["wk"] <= 3])

o.h("F. Early-season dogs by last season's strength (Elo carried, 1/3 to the mean) vs the favorite")
for lo, hi, lab in ((-1e9, -150, "dog rated 150+ Elo under"), (-150, -50, "dog 50-150 under"), (-50, 1e9, "dog within 50 / rated higher")):
    o.c(f"{lab}, weeks 1-3", [x for x in D if x["wk"] <= 3 and lo <= x["elo"] - x["oelo"] < hi])
    o.c(f"{lab}, Jan-Mar", [x for x in D if x["start"][5:7] not in ("11", "12") and lo <= x["elo"] - x["oelo"] < hi])

o.h("G. The same, ATS (the dog side of the spread) - is the early dog a SPREAD dog instead?")
S = [x for x in lib.spreads(R) if x["sp"] > 0 and x["tier"] != "none" and x["otier"] != "none"]
for sg in ("opening week", "G1-5 after week 1", "G6+ Nov-Dec", "Jan-Mar"):
    o.c(f"spread dog, {sg}", [x for x in S if stage(x) == sg], lib.profit_ats)
for v in ("home", "away", "neutral"):
    o.c(f"spread dog {v}, weeks 1-3", [x for x in S if x["venue"] == v and x["wk"] <= 3], lib.profit_ats)

o.h("H. Opening week FAVORITES -101..-150 (the other side of the upsets)")
F = [x for x in lib.favs(R) if x["tier"] != "none" and x["otier"] != "none"]
for sg in ("opening week", "G1-5 after week 1", "G6+ Nov-Dec", "Jan-Mar"):
    o.c(f"fav -101..-150, {sg}", [x for x in F if stage(x) == sg])
F2 = [x for x in R if x.get("ml") is not None and -400 <= x["ml"] <= -151 and x["tier"] != "none"]
for sg in ("opening week", "G1-5 after week 1", "G6+ Nov-Dec", "Jan-Mar"):
    o.c(f"fav -151..-400, {sg}", [x for x in F2 if stage(x) == sg])

o.h("I. How often the upset lands vs the price: win % minus the no-vig % (dogs +100..+350)")
for sg in ("opening week", "G1-5 after week 1", "G6+ Nov-Dec", "Jan-Mar"):
    sub = [x for x in D if stage(x) == sg]
    if sub:
        w = sum(x["won"] for x in sub) / len(sub)
        p = sum(x["p"] for x in sub) / len(sub)
        o.note(f"  {sg:20s} n {len(sub):5d}  dogs won {w*100:5.1f}%  no-vig said {p*100:5.1f}%  gap {100*(w-p):+.1f}")
o.save()
