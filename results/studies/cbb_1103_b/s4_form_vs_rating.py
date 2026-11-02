"""STUDY 4 - form vs rating (college hoops, regular season, closing prices; the OPEN 2023-25 the 2nd check).
Win / loss streaks 5+ (this season), ATS streaks 4+, and whether the market over-reacts in November-December vs
January-March. ALREADY BUILT (re-checked here, not re-proposed): the college hoops favorite on a 6+ losing streak (+3 /
overreact, 9/30) and the cover-streak weight (cover_run_w, spread picks). New here: the Nov-Dec split, the hot START
(5-0 / 6-0+ in games 6-10), the record-vs-the-market gap (wins minus the no-vig wins expected from its prices so far).
Also the mid-season 'G6+ Nov-Dec' favorite band (study 5 showed it) by what drives it."""
import lib

R = lib.regular(lib.build())
o = lib.Out("s4")


def trio(name, sub):
    o.c(f"{name} | ATS", lib.spreads(sub), lib.profit_ats)
    o.c(f"{name} | dog +100..+350", lib.dogs(sub))
    o.c(f"{name} | fav -101..-150", lib.favs(sub))
    o.c(f"{name} | fav -151..-400", [x for x in sub if x.get("ml") is not None and -400 <= x["ml"] <= -151])


ND = lambda x: x["start"][5:7] in ("11", "12")      # noqa: E731
JM = lambda x: not ND(x)                             # noqa: E731
o.h("A. Win / loss streaks, Nov-Dec vs Jan-Mar")
for lab, f in (("won 5+ straight", lambda x: x["streak"] >= 5), ("won 3-4 straight", lambda x: 3 <= x["streak"] <= 4),
               ("lost 5+ straight", lambda x: x["streak"] <= -5), ("lost 3-4 straight", lambda x: -4 <= x["streak"] <= -3)):
    trio(f"{lab}, Nov-Dec", [x for x in R if f(x) and ND(x)])
    trio(f"{lab}, Jan-Mar", [x for x in R if f(x) and JM(x)])
o.h("B. Hot vs cold matchups")
trio("5+ win streak vs a 3+ losing streak", [x for x in R if x["streak"] >= 5 and x["ostreak"] <= -3])
trio("3+ losing streak vs a 5+ win streak", [x for x in R if x["streak"] <= -3 and x["ostreak"] >= 5])
o.h("C. ATS streaks (covered / failed 4+ straight), Nov-Dec vs Jan-Mar")
for lab, f in (("covered 4+ straight", lambda x: x["ats"] >= 4), ("failed 4+ straight", lambda x: x["ats"] <= -4)):
    trio(f"{lab}, Nov-Dec", [x for x in R if f(x) and ND(x)])
    trio(f"{lab}, Jan-Mar", [x for x in R if f(x) and JM(x)])
o.h("D. The hot / cold START (games 6-10, unbeaten / winless so far)")
trio("unbeaten after 5+ (games 6-12)", [x for x in R if 6 <= x["gn"] <= 12 and x["streak"] == x["gn"] - 1])
trio("winless after 4+ (games 5-12)", [x for x in R if 5 <= x["gn"] <= 12 and -x["streak"] == x["gn"] - 1])
o.h("E. Record vs its prices: wins minus the no-vig wins expected this season (5+ priced games), per game")
ALL = lib.build()
luck = {}
acc = {}
for x in ALL:
    k = (x["season"], x["team"])
    a = acc.setdefault(k, [0, 0.0, 0])
    if a[2] >= 5:
        luck[(x["id"], x["team"])] = (a[0] - a[1]) / a[2]
    if x.get("p") is not None:
        a[0] += x["won"]
        a[1] += x["p"]
        a[2] += 1
for lab, lo, hi in (("beat its prices by 0.15+/game", 0.15, 9), ("beat by 0.08-0.15", 0.08, 0.15),
                    ("within 0.08", -0.08, 0.08), ("under by 0.08-0.15", -0.15, -0.08), ("under by 0.15+", -9, -0.15)):
    for per, f in (("Nov-Dec", ND), ("Jan-Mar", JM)):
        trio(f"{lab}, {per}", [x for x in R if f(x) and lo <= luck.get((x["id"], x["team"]), 99) < hi])
o.h("F. The mid-Nov / Dec favorite (games 6+, Nov-Dec) - where it loses")
F = [x for x in R if ND(x) and x["gn"] >= 6 and x.get("ml") is not None and -150 <= x["ml"] <= -101]
for v in ("home", "away", "neutral"):
    o.c(f"G6+ Nov-Dec fav -101..-150, {v}", [x for x in F if x["venue"] == v])
o.c("G6+ Nov-Dec fav -101..-150, same tier", [x for x in F if x["tier"] == x["otier"]])
o.c("G6+ Nov-Dec fav -101..-150, higher tier than the dog",
    [x for x in F if (x["tier"], x["otier"]) in (("power", "mid"), ("power", "low"), ("mid", "low"))])
o.c("G6+ Nov-Dec fav -101..-150, lower tier than the dog",
    [x for x in F if (x["otier"], x["tier"]) in (("power", "mid"), ("power", "low"), ("mid", "low"))])
o.c("G6+ Nov-Dec fav -101..-150, better record than the dog", [x for x in F if (x["wpct"] or 0) > (x["owpct"] or 0)])
o.c("G6+ Nov-Dec fav -101..-150, worse / same record", [x for x in F if (x["wpct"] or 0) <= (x["owpct"] or 0)])
o.c("G6+ Nov-Dec fav -101..-150, Elo says the dog is better", [x for x in F if x["oelo"] > x["elo"]])
o.c("G6+ Nov-Dec fav -101..-150, Elo agrees with the fav", [x for x in F if x["oelo"] <= x["elo"]])
o.c("G6+ Nov-Dec fav -101..-150, December only", [x for x in F if x["start"][5:7] == "12"])
o.c("G6+ Nov-Dec fav -101..-150, November only", [x for x in F if x["start"][5:7] == "11"])
o.c("fav -101..-150, December, ANY game number", [x for x in R if x["start"][5:7] == "12" and x.get("ml") is not None and -150 <= x["ml"] <= -101])
o.c("fav -101..-150, January", [x for x in R if x["start"][5:7] == "01" and x.get("ml") is not None and -150 <= x["ml"] <= -101])
o.c("ATS fav side, G6+ Nov-Dec (every spread fav)", [x for x in lib.spreads(R) if ND(x) and x["gn"] >= 6 and x["sp"] < 0], lib.profit_ats)
o.c("ATS fav side, Jan-Mar", [x for x in lib.spreads(R) if JM(x) and x["sp"] < 0], lib.profit_ats)
o.save()
