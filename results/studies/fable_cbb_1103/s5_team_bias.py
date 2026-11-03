"""S5 - TEAM-SPECIFIC MARKET BIAS: does the market's error on a team persist? (a) last season's mean cover margin
(10+ spread games) -> this season's ATS; (b) in-season: the mean cover margin over the team's first N spread games ->
its ATS from game N+1 on (walk-forward inside the season); (c) the public / blue-blood names by price band and venue;
(d) the ranked (top-25 by our Elo) side as a small favorite / dog. Regular season 2018-26 at the close."""
import lib
from collections import defaultdict

R = lib.regular(lib.build())
o = lib.Out("s5")
SP, DG, FV = lib.spreads(R), lib.dogs(R), lib.favs(R)
o.h("A. Last season's mean cover margin (10+ games) -> this season ATS")
for lo, hi in ((-99, -4), (-4, -2), (-2, -0.5), (-0.5, 0.5), (0.5, 2), (2, 4), (4, 99)):
    rows = [x for x in SP if x.get("lresid") is not None and lo <= x["lresid"] < hi]
    o.c(f"ATS last-season resid {lo}..{hi}", rows, lib.profit_ats)
    o.c(f"ATS last-season resid {lo}..{hi}, Nov-Dec", [x for x in rows if x["start"][5:7] in ("11", "12")], lib.profit_ats)
for lo, hi in ((-99, -2), (-2, 2), (2, 99)):
    o.c(f"dog ML last-season resid {lo}..{hi}", [x for x in DG if x.get("lresid") is not None and lo <= x["lresid"] < hi])
    o.c(f"fav -101..-150 ML last-season resid {lo}..{hi}", [x for x in FV if x.get("lresid") is not None and lo <= x["lresid"] < hi])
o.h("B. In-season: mean cover margin over the first 10+ spread games -> ATS after (the team the market keeps missing)")
CS = [x for x in SP if x.get("cm_mean") is not None and x.get("n_cm", 0) >= 10]
for lo, hi in ((-99, -5), (-5, -3), (-3, -1), (-1, 1), (1, 3), (3, 5), (5, 99)):
    rows = [x for x in CS if lo <= x["cm_mean"] < hi]
    o.c(f"ATS season resid so far {lo}..{hi}", rows, lib.profit_ats)
for lo, hi in ((-99, -3), (-3, 3), (3, 99)):
    rows = [x for x in CS if lo <= x["cm_mean"] < hi]
    o.c(f"ATS season resid {lo}..{hi}, as the dog", [x for x in rows if x["sp"] > 0], lib.profit_ats)
    o.c(f"ATS season resid {lo}..{hi}, as the favorite", [x for x in rows if x["sp"] < 0], lib.profit_ats)
    o.c(f"ATS season resid {lo}..{hi}, 20+ games", [x for x in rows if x["n_cm"] >= 20], lib.profit_ats)
    o.c(f"dog ML season resid {lo}..{hi}", [x for x in lib.dogs(CS) if lo <= x["cm_mean"] < hi])
    o.c(f"fav -101..-150 ML season resid {lo}..{hi}", [x for x in lib.favs(CS) if lo <= x["cm_mean"] < hi])
o.h("B2. The GAP: my season resid minus the opponent's (both 10+), ATS")
for lo, hi in ((-99, -6), (-6, -3), (-3, 3), (3, 6), (6, 99)):
    rows = [x for x in CS if x.get("o_cm_mean") is not None and lo <= x["cm_mean"] - x["o_cm_mean"] < hi]
    o.c(f"ATS resid gap {lo}..{hi}", rows, lib.profit_ats)
o.h("C. Public / blue-blood names, by venue and price band")
PUB = {"Duke", "Kentucky", "Kansas", "North Carolina", "UCLA", "Michigan St", "Indiana", "Syracuse", "Gonzaga", "Arizona",
       "Louisville", "Villanova", "UConn", "Michigan", "Ohio St", "Purdue", "Alabama", "Auburn", "Tennessee", "Houston",
       "Baylor", "Texas", "Florida", "LSU", "Memphis", "Georgetown", "Marquette", "Illinois", "Iowa St", "Creighton"}
P = [x for x in SP if x["name"] in PUB]
o.c("ATS public team", P, lib.profit_ats)
o.c("ATS public team, home", [x for x in P if x["venue"] == "home"], lib.profit_ats)
o.c("ATS public team, road", [x for x in P if x["venue"] == "away"], lib.profit_ats)
o.c("ATS public team, neutral", [x for x in P if x["venue"] == "neutral"], lib.profit_ats)
o.c("ATS public team as a favorite 10+", [x for x in P if x["sp"] <= -10], lib.profit_ats)
o.c("ATS public team as a favorite 1-9.5", [x for x in P if -10 < x["sp"] < 0], lib.profit_ats)
o.c("ATS public team as a dog", [x for x in P if x["sp"] > 0], lib.profit_ats)
o.c("ATS public team vs a public team", [x for x in P if x["oname"] in PUB], lib.profit_ats)
o.c("ATS public team vs a NON-public team, road", [x for x in P if x["oname"] not in PUB and x["venue"] == "away"], lib.profit_ats)
o.c("ATS the side FACING a public team", [x for x in SP if x["oname"] in PUB and x["name"] not in PUB], lib.profit_ats)
o.c("ATS facing a public team, at home", [x for x in SP if x["oname"] in PUB and x["name"] not in PUB and x["venue"] == "home"], lib.profit_ats)
o.c("ATS facing a public team, at home, as a dog", [x for x in SP if x["oname"] in PUB and x["name"] not in PUB and x["venue"] == "home" and x["sp"] > 0], lib.profit_ats)
o.c("dog ML public team", [x for x in DG if x["name"] in PUB])
o.c("dog ML vs a public team", [x for x in DG if x["oname"] in PUB and x["name"] not in PUB])
o.c("dog ML vs a public team, at home", [x for x in DG if x["oname"] in PUB and x["name"] not in PUB and x["venue"] == "home"])
o.c("fav -101..-150 public team", [x for x in FV if x["name"] in PUB])
o.c("fav -101..-200 public team, road", [x for x in lib.favs(R, -200, -101) if x["name"] in PUB and x["venue"] == "away"])
o.c("ATS public team, Saturday", [x for x in P if x["dow"] == 5], lib.profit_ats)
o.c("ATS public team, weeknight (Mon-Thu)", [x for x in P if x["dow"] <= 3], lib.profit_ats)
o.h("D. Ranked (top-25 by our Elo) as a small favorite / as a dog; the unranked side at home vs a ranked team")
o.c("fav -101..-150 ML, ranked", [x for x in FV if x["rank25"]])
o.c("fav -101..-150 ML, ranked vs ranked", [x for x in FV if x["rank25"] and x["orank25"]])
o.c("fav -101..-150 ML, unranked vs ranked", [x for x in FV if not x["rank25"] and x["orank25"]])
o.c("dog ML, ranked dog", [x for x in DG if x["rank25"]])
o.c("dog ML, unranked home dog vs ranked", [x for x in DG if not x["rank25"] and x["orank25"] and x["venue"] == "home"])
o.c("ATS ranked side, road", [x for x in SP if x["rank25"] and x["venue"] == "away"], lib.profit_ats)
o.c("ATS ranked side, home", [x for x in SP if x["rank25"] and x["venue"] == "home"], lib.profit_ats)
o.c("ATS ranked side, road, Feb-Mar", [x for x in SP if x["rank25"] and x["venue"] == "away" and x["start"][5:7] in ("02", "03")], lib.profit_ats)
o.c("ATS unranked home vs ranked", [x for x in SP if not x["rank25"] and x["orank25"] and x["venue"] == "home"], lib.profit_ats)
o.h("E. Team-level ATS the season after: the market's worst-missed 30 teams a season (lresid rank) ATS next season")
by = defaultdict(list)
for x in SP:
    if x.get("lresid") is not None:
        by[x["season"]].append(x)
top, bot = [], []
for s, rows in by.items():
    teams = sorted({(x["team"], x["lresid"]) for x in rows}, key=lambda t: t[1])
    lo_t = {t for t, _ in teams[:30]}
    hi_t = {t for t, _ in teams[-30:]}
    bot += [x for x in rows if x["team"] in lo_t]
    top += [x for x in rows if x["team"] in hi_t]
o.c("ATS the 30 teams the market over-rated most last season", bot, lib.profit_ats)
o.c("ATS the 30 teams the market under-rated most last season", top, lib.profit_ats)
o.save()
