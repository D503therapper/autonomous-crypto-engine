"""S4 - TOTALS BY CONTEXT (the 11/1 NBA pace study was dead; these are the other angles): college hoops and NBA closing
totals at their real over / under juice. One row per game. Over AND under graded in every cell (the vig makes both
lose at a fair line; a real cell has one side clearly up in train AND held out).
College contexts: tier, conference vs non-conference, month (Nov / Dec / Jan-Feb / March), neutral site, altitude
(venue 4,000+ ft), late tip, big spread (15+), extreme totals (bottom / top 10% of the season so far), the 2nd / 3rd
meeting after a first meeting that went 15+ over / under its total (anchoring), both teams on 1-2 nights' rest.
NBA contexts: both on a back-to-back / one, Denver + Utah home (altitude), April (tanking), big spread 12+, extreme
totals, the game after both teams' last games went 15+ over (streaky public overs), OT-prone (both spreads tiny)."""
from collections import defaultdict

import lib

out = lib.Out("s4_totals")


def ou(rows, side):
    if side == "over":
        return [(r["season"], lib.ats_pl(r["pts"] - r["total"], r["over_odds"])) for r in rows]
    return [(r["season"], lib.ats_pl(r["total"] - r["pts"], r["under_odds"])) for r in rows]


def both(label, rows):
    out.bets(f"{label} OVER", ou(rows, "over"))
    out.bets(f"{label} UNDER", ou(rows, "under"))


# ---------------- college
S = [x for x in lib.nc_sides() if x["stype"] in ("2", "3") and x["season"] >= 2018 and x.get("total")]
G = [x for x in S if x["side"] == "home"]
for g in G:
    g["gt"] = "P" if "power" in (g["tier"], g["otier"]) else ("M" if "mid" in (g["tier"], g["otier"]) else "L")
# running season total percentiles (no look-ahead: totals seen before this night)
seen = defaultdict(list)
for g in sorted(G, key=lambda g: g["start"]):
    v = sorted(seen[g["season"]])
    if len(v) >= 200:
        g["tlo"] = g["total"] <= v[len(v) // 10]
        g["thi"] = g["total"] >= v[9 * len(v) // 10]
    seen[g["season"]].append(g["total"])
# meetings: previous meeting this season's total miss (pts - total)
lastmeet = {}
for g in sorted(G, key=lambda g: g["start"]):
    k = (g["season"], frozenset((g["team"], g["opp"])))
    if k in lastmeet:
        g["prev_miss"] = lastmeet[k]
    lastmeet[k] = g["pts"] - g["total"]
out.h("COLLEGE baseline")
both("all", [g for g in G if g["stype"] == "2"])
out.h("COLLEGE by context")
R = [g for g in G if g["stype"] == "2"]
for t in "PML":
    both(f"tier {t}", [g for g in R if g["gt"] == t])
both("conference game", [g for g in R if g["same_conf"]])
both("non-conference", [g for g in R if not g["same_conf"]])
for lab, ms in (("November", (11,)), ("December", (12,)), ("Jan-Feb", (1, 2)), ("March reg", (3,))):
    both(lab, [g for g in R if g["month"] in ms])
both("conf tournament / March neutral", [g for g in G if g["month"] == 3 and g["neutral"]])
both("postseason (stype 3)", [g for g in G if g["stype"] == "3"])
both("neutral (non-March)", [g for g in R if g["neutral"] and g["month"] != 3])
both("altitude 4000+ ft", [g for g in R if (g.get("elev") or 0) >= 1220])
both("late tip 22:00+ ET", [g for g in R if g["et"] >= 22])
both("big spread 15+", [g for g in R if g.get("sp") is not None and abs(g["sp"]) >= 15])
both("pick'em-ish spread <=2", [g for g in R if g.get("sp") is not None and abs(g["sp"]) <= 2])
both("total bottom 10% so far", [g for g in R if g.get("tlo")])
both("total top 10% so far", [g for g in R if g.get("thi")])
both("rematch, 1st went 15+ OVER", [g for g in R if g.get("prev_miss") is not None and g["prev_miss"] >= 15])
both("rematch, 1st went 15+ UNDER", [g for g in R if g.get("prev_miss") is not None and g["prev_miss"] <= -15])
both("both teams rest <=2 nights", [g for g in R if (g.get("rest") or 9) <= 2 and (g.get("orest") or 9) <= 2])
both("games 1-3 either team", [g for g in R if min(g["gn"], g["ogn"]) <= 3])
both("L tier Nov-Dec", [g for g in R if g["gt"] == "L" and g["month"] in (11, 12)])
both("L tier non-conference", [g for g in R if g["gt"] == "L" and not g["same_conf"]])

# ---------------- NBA
out.train, out.held = (2018, 2019, 2020, 2021, 2022), (2023, 2024, 2025)
NB = [g for g in lib.nba_games() if g.get("total") and g["season"] >= 2018]
for g in NB:
    g["over_odds"], g["under_odds"] = g["over_o"], g["under_o"]
last = {}
hist = defaultdict(list)
for g in NB:
    from datetime import datetime
    d = datetime.strptime(g["start"][:10], "%Y-%m-%d").toordinal()
    for side in ("home", "away"):
        t = g[side]
        lt = last.get(t)
        g[side + "_b2b"] = lt is not None and d - lt[0] <= 1
        g[side + "_lastmiss"] = lt[1] if lt else None
    seen_s = hist[g["season"]]
    if len(seen_s) >= 150:
        v = sorted(seen_s)
        g["tlo"], g["thi"] = g["total"] <= v[len(v) // 10], g["total"] >= v[9 * len(v) // 10]
    seen_s.append(g["total"])
    for side in ("home", "away"):
        last[g[side]] = (d, g["pts"] - g["total"])
out.h("NBA baseline")
both("all", NB)
out.h("NBA by context")
both("both on a b2b", [g for g in NB if g["home_b2b"] and g["away_b2b"]])
both("one on a b2b", [g for g in NB if g["home_b2b"] != g["away_b2b"]])
both("Denver / Utah home (altitude)", [g for g in NB if (g.get("elev") or 0) >= 1200])
both("April", [g for g in NB if g["start"][5:7] == "04"])
both("October-November", [g for g in NB if g["start"][5:7] in ("10", "11")])
both("big spread 12+", [g for g in NB if g.get("sp") is not None and abs(g["sp"]) >= 12])
both("spread <=2", [g for g in NB if g.get("sp") is not None and abs(g["sp"]) <= 2])
both("total bottom 10% so far", [g for g in NB if g.get("tlo")])
both("total top 10% so far", [g for g in NB if g.get("thi")])
both("both last games 15+ OVER", [g for g in NB if (g["home_lastmiss"] or 0) >= 15 and (g["away_lastmiss"] or 0) >= 15])
both("both last games 15+ UNDER", [g for g in NB if (g["home_lastmiss"] or 0) <= -15 and (g["away_lastmiss"] or 0) <= -15])
both("late tip 22:00+ ET", [g for g in NB if g["et"] >= 22])
out.save()
