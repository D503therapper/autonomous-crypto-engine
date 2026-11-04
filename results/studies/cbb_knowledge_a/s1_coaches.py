"""S1 - COACHES. The college hoops coach table (sports_ncaab_coaches - Wikipedia's coaching-change tables on disk +
ESPN's current list, walked forward from 2015-16) on every priced side 2018-26:
  A. the NEW coach's team (his first season with the program) by game number / venue / month / price, the opponent
     across it, the first-time head coach vs the experienced hire (the reason-text hint), the second-year coach;
  B. tenure - the long-tenured coach (8+ seasons, a lower bound for anyone there since 2015-16) as a dog / favorite;
     the interim coach after a mid-season change (the FIRED weight already covers it - reported);
  C. the coach's own ATS profile, walk-forward by name across programs (cover margin before tonight, 60+ priced
     games): the top / bottom quartile coaches, as dogs, as favorites, after a loss - does it persist?
Train 2018-22, held out 2023 / 2024 / 2025; ESPN's ML open 2023-25 on the dog cells."""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *  # noqa: F401,F403
import sports_ncaab_coaches as nc

out = Out("s1")
rows_ = regular(rows())
table = nc.load()
assert table, "build the coach file first: python sports_ncaab_coaches.py"


def cs(team, start):
    return nc.state(team, start, table)


# coach state on every row + the walk-forward profile by coach name
prof = defaultdict(lambda: {"n": 0, "cm": 0.0, "dog_n": 0, "dog_cm": 0.0, "fav_n": 0, "fav_cm": 0.0,
                            "loss_n": 0, "loss_cm": 0.0, "dog_ml_n": 0, "dog_ml": 0.0})
rows_.sort(key=lambda x: (x["start"], x["id"]))
for x in rows_:
    x["c"], x["oc"] = cs(x["team"], x["start"]), cs(x["opp"], x["start"])
# one pass in time order: read the coach's profile BEFORE tonight, then add tonight to it (the honest walk-forward)
for x in rows_:
    me = x.get("c")
    if me:
        p = prof[me["coach"]]
        x["pn"], x["pcm"] = p["n"], (p["cm"] / p["n"]) if p["n"] else None
        x["pdog"] = (p["dog_cm"] / p["dog_n"]) if p["dog_n"] >= 25 else None
        x["pfav"] = (p["fav_cm"] / p["fav_n"]) if p["fav_n"] >= 25 else None
        x["ploss"] = (p["loss_cm"] / p["loss_n"]) if p["loss_n"] >= 25 else None
        x["pdogml"] = (p["dog_ml"] / p["dog_ml_n"]) if p["dog_ml_n"] >= 25 else None
    if not me or x.get("cover") is None:
        continue
    p = prof[me["coach"]]
    cm = x["margin"] + x["sp"]
    p["n"] += 1
    p["cm"] += cm
    ml = x.get("ml")
    if ml is not None and ml >= 100:
        p["dog_n"] += 1
        p["dog_cm"] += cm
        p["dog_ml_n"] += 1
        p["dog_ml"] += profit_ml(x)
    elif ml is not None:
        p["fav_n"] += 1
        p["fav_cm"] += cm
    if x.get("last") and x["last"]["won"] is False:
        p["loss_n"] += 1
        p["loss_cm"] += cm

known = [x for x in rows_ if x.get("c")]
out.note(f"sides {len(rows_)}, with a coach on file {len(known)} ({len(known) / len(rows_):.0%}); "
         f"new-coach sides {sum(1 for x in known if x['c']['new'])}, first-time hint "
         f"{sum(1 for x in known if x['c']['new'] and x['c']['first_time'])}, experienced "
         f"{sum(1 for x in known if x['c']['new'] and x['c']['first_time'] is False)}")
new = [x for x in known if x["c"]["new"]]
old = [x for x in known if not x["c"]["new"]]
month = lambda x: x["start"][5:7]

out.h("A. THE NEW COACH'S TEAM (his first season with the program) - the base is every other side")
by_season_ats(old, "base: every side, coach not new", out)
by_season_ats(new, "new coach, all games", out)
for lo, hi in ((1, 5), (6, 10), (11, 20), (21, 99)):
    by_season_ats([x for x in new if lo <= x["gn"] <= hi], f"new coach, games {lo}-{hi}", out)
for m, lab in ((("11",), "November"), (("12",), "December"), (("01", "02", "03"), "Jan-Mar")):
    by_season_ats([x for x in new if month(x) in m], f"new coach, {lab}", out)
for v in ("home", "away", "neutral"):
    by_season_ats([x for x in new if x["venue"] == v], f"new coach, {v}", out)
out.c("new coach, fav -151..-300 ML", favs(new, -300, -151))
out.c("new coach, fav -301..-600 ML", favs(new, -600, -301))
out.c("new coach, dog +100..+200 ML", dogs(new, 100, 200))
out.c("new coach, dog +201..+350 ML", dogs(new, 201, 350))
out.c("new coach, dog +351..+800 ML", dogs(new, 351, 800))
out.c("new coach, dog +100..+350 ML, Nov-Dec", [x for x in dogs(new) if month(x) in ("11", "12")])
out.c("new coach, dog +100..+350 ML, Jan-Mar", [x for x in dogs(new) if month(x) in ("01", "02", "03")])
out.c("new coach, fav -101..-150 ML, Nov-Dec", [x for x in favs(new) if month(x) in ("11", "12")])
out.c("new coach, fav -101..-150 ML, Jan-Mar", [x for x in favs(new) if month(x) in ("01", "02", "03")])
out.c("new coach, fav -101..-150 ML, games 1-5", [x for x in favs(new) if x["gn"] <= 5])
out.c("new coach, fav -101..-150 ML, away / neutral, Nov-Dec", [x for x in favs(new) if month(x) in ("11", "12") and x["venue"] != "home"])
# the side ACROSS a new coach's team
across = [x for x in known if x.get("oc") and x["oc"]["new"]]
by_season_ats(across, "the side across a new-coach team", out)
by_season_ats([x for x in across if x["gn"] <= 10], "the side across a new-coach team, games 1-10", out)
out.c("the dog across a new-coach fav, Jan-Mar", [x for x in dogs(across) if month(x) in ("01", "02", "03")])
# both new / tiers
by_season_ats([x for x in new if x.get("oc") and x["oc"]["new"]], "new coach vs new coach", out)
for t in ("power", "mid", "low"):
    by_season_ats([x for x in new if x["tier"] == t], f"new coach, {t} tier", out)
# first-time vs experienced hire (the reason-text hint)
ft = [x for x in new if x["c"]["first_time"] is True]
ex = [x for x in new if x["c"]["first_time"] is False]
by_season_ats(ft, "new coach, FIRST-TIME head coach (hint)", out)
by_season_ats(ex, "new coach, experienced hire (hint)", out)
by_season_ats([x for x in ft if x["gn"] <= 10], "first-time head coach, games 1-10", out)
by_season_ats([x for x in ex if x["gn"] <= 10], "experienced hire, games 1-10", out)
out.c("first-time head coach, dog +200..+350 ML", dogs(ft, 200, 350))
out.c("experienced hire, dog +200..+350 ML", dogs(ex, 200, 350))
out.c("first-time head coach, dog +351..+800 ML", dogs(ft, 351, 800))
out.c("first-time head coach, fav -101..-150, Jan-Mar", [x for x in favs(ft) if month(x) in ("01", "02", "03")])
out.c("experienced hire, fav -101..-150, Jan-Mar", [x for x in favs(ex) if month(x) in ("01", "02", "03")])
# second year
yr2 = [x for x in known if x["c"].get("tenure") == 2]
by_season_ats(yr2, "second-year coach", out)
by_season_ats([x for x in yr2 if month(x) in ("11", "12")], "second-year coach, Nov-Dec", out)
yr3 = [x for x in known if x["c"].get("tenure") == 3]
by_season_ats(yr3, "third-year coach", out)

out.h("B. TENURE - the long-tenured coach, the interim")
ten = lambda x: x["c"].get("tenure") or x["c"].get("tenure_min")
vet = [x for x in known if ten(x) >= 8]
by_season_ats(vet, "coach 8+ seasons with the team", out)
by_season_ats([x for x in vet if ten(x) >= 12], "coach 12+ seasons with the team", out)
out.c("8+ year coach, dog +100..+200 ML", dogs(vet, 100, 200))
out.c("8+ year coach, dog +100..+350 ML, Jan-Mar", [x for x in dogs(vet) if month(x) in ("01", "02", "03")])
out.c("8+ year coach, dog +100..+350 ML, away", [x for x in dogs(vet) if x["venue"] == "away"])
out.c("8+ year coach, dog, after a loss", [x for x in dogs(vet) if x.get("last") and x["last"]["won"] is False])
out.c("8+ year coach vs a new coach, dog +100..+350", [x for x in dogs(vet) if x.get("oc") and x["oc"]["new"]])
out.c("8+ year coach vs a new coach, fav -101..-150", [x for x in favs(vet) if x.get("oc") and x["oc"]["new"]])
out.c("8+ year coach vs a new coach, ATS", [x for x in spreads(vet) if x.get("oc") and x["oc"]["new"]], profit_ats)
out.c("8+ year coach vs a 1-2 year coach, ATS", [x for x in spreads(vet) if x.get("oc") and (x["oc"].get("tenure") or 9) <= 2], profit_ats)
out.c("8+ year coach vs a 1-2 year coach, dog +100..+350", [x for x in dogs(vet) if x.get("oc") and (x["oc"].get("tenure") or 9) <= 2])
mid = [x for x in known if x["c"].get("mid") and x["start"][:10] > x["c"]["mid"]]
by_season_ats(mid, "the interim after a mid-season change (the FIRED weight's cell)", out)
out.c("the side across the interim, ATS", [x for x in spreads(known) if x.get("oc") and x["oc"].get("mid") and x["start"][:10] > x["oc"]["mid"]], profit_ats)

out.h("C. THE COACH'S OWN ATS PROFILE, walk-forward by name (cover margin before tonight, 60+ priced games)")
prof_rows = [x for x in known if x.get("pn", 0) >= 60 and x.get("pcm") is not None]
cuts = [-1.5, -0.5, 0.5, 1.5]
for i in range(5):
    lab = ["under -1.5", "-1.5..-0.5", "-0.5..0.5", "0.5..1.5", "1.5+"][i]
    sub = [x for x in prof_rows if q(x["pcm"], cuts) == i]
    out.c(f"coach prior cover margin {lab}: ATS", spreads(sub), profit_ats)
    out.c(f"coach prior cover margin {lab}: dog +100..+350 ML", dogs(sub))
    out.c(f"coach prior cover margin {lab}: fav -101..-150 ML", favs(sub))
# a hot profile ONLY in the years past (not this season) - the prior seasons' margin: approximated by 150+ games
big = [x for x in prof_rows if x["pn"] >= 150]
out.c("coach 150+ games, prior cover margin 1+: ATS", [x for x in spreads(big) if x["pcm"] >= 1.0], profit_ats)
out.c("coach 150+ games, prior cover margin -1 or worse: ATS", [x for x in spreads(big) if x["pcm"] <= -1.0], profit_ats)
# as a dog (his record as a dog), as a favorite, after a loss - each walk-forward on its own slice
for key, lab in (("pdog", "as a dog"), ("pfav", "as a favorite"), ("ploss", "after a loss")):
    have = [x for x in known if x.get(key) is not None]
    hi = [x for x in have if x[key] >= 1.5]
    lo = [x for x in have if x[key] <= -1.5]
    if key == "pdog":
        out.c(f"coach's prior cover margin {lab} 1.5+: tonight a dog, ML", dogs(hi))
        out.c(f"coach's prior cover margin {lab} 1.5+: tonight a dog, ATS", [x for x in spreads(hi) if x.get("ml", 0) >= 100], profit_ats)
        out.c(f"coach's prior cover margin {lab} -1.5 or worse: tonight a dog, ML", dogs(lo))
        out.c(f"coach's prior cover margin {lab} -1.5 or worse: tonight a dog, ATS", [x for x in spreads(lo) if x.get("ml", 0) >= 100], profit_ats)
    elif key == "pfav":
        out.c(f"coach's prior cover margin {lab} 1.5+: tonight a fav -101..-150, ML", favs(hi))
        out.c(f"coach's prior cover margin {lab} 1.5+: tonight a fav, ATS", [x for x in spreads(hi) if x.get("ml", 0) < 0], profit_ats)
        out.c(f"coach's prior cover margin {lab} -1.5 or worse: tonight a fav -101..-150, ML", favs(lo))
        out.c(f"coach's prior cover margin {lab} -1.5 or worse: tonight a fav, ATS", [x for x in spreads(lo) if x.get("ml", 0) < 0], profit_ats)
    else:
        al = lambda x: x.get("last") and x["last"]["won"] is False
        out.c(f"coach's prior cover margin {lab} 1.5+: tonight after a loss, ATS", [x for x in spreads(hi) if al(x)], profit_ats)
        out.c(f"coach's prior cover margin {lab} 1.5+: tonight after a loss, dog ML", [x for x in dogs(hi) if al(x)])
        out.c(f"coach's prior cover margin {lab} -1.5 or worse: tonight after a loss, ATS", [x for x in spreads(lo) if al(x)], profit_ats)
        out.c(f"coach's prior cover margin {lab} -1.5 or worse: tonight after a loss, dog ML", [x for x in dogs(lo) if al(x)])
# the dog ML profile (his dogs' ROI so far) -> tonight's dog
have = [x for x in known if x.get("pdogml") is not None]
out.c("coach whose dogs have paid +10%+ so far: tonight a dog ML", dogs([x for x in have if x["pdogml"] >= 0.10]))
out.c("coach whose dogs have lost -15% or worse so far: tonight a dog ML", dogs([x for x in have if x["pdogml"] <= -0.15]))
# the gap between the two coaches' profiles
both = [x for x in known if x.get("pcm") is not None and x.get("pn", 0) >= 60]
opc = {}
for x in both:
    opc[(x["id"], x["team"])] = x["pcm"]
for x in both:
    o = opc.get((x["id"], x["opp"]))
    x["pgap"] = (x["pcm"] - o) if o is not None else None
gap = [x for x in both if x.get("pgap") is not None]
out.c("coach profile gap 2+ over the other coach: ATS", [x for x in spreads(gap) if x["pgap"] >= 2], profit_ats)
out.c("coach profile gap -2 or worse: ATS", [x for x in spreads(gap) if x["pgap"] <= -2], profit_ats)
out.c("coach profile gap 2+: dog +100..+350 ML", dogs([x for x in gap if x["pgap"] >= 2]))
out.c("coach profile gap -2 or worse: dog +100..+350 ML", dogs([x for x in gap if x["pgap"] <= -2]))
out.save()
