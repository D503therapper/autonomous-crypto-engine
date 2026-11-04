"""S6 - FOLLOW-UPS on the candidates from s1 / s4 / s5 before anything is wired: is each NEW next to the weights the
engine already carries, does it hold by dose / price / venue / tier, and does the open agree?
  a. the out-of-the-race dog (5+ games back) vs a contender (within a game) in Feb-Mar conference play (s5) - without
     the built 5+ skid, by games back, price band, venue, tier, the leader exactly vs 'within a game';
  b. the offense-first dog (s4) in Jan-Mar - by dose (def rank), price, venue, with / without a losing streak, and the
     offense-first team ATS / small favorite;
  c. the turnover-prone small favorite (s4) - by dose, venue, month, vs the opponent's turnover margin;
  d. the new coach's small favorite in Jan-Mar (s1) - by venue, tier, conference game, and the away-fav overlap."""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *  # noqa: F401,F403
import sports_ncaab_coaches as nc

out = Out("s6")
rows_ = regular(rows())
rows_.sort(key=lambda x: (x["start"], x["id"]))
month = lambda x: x["start"][5:7]
# ---- a. standings (s5's) ----
stand = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for x in rows_:
    if not x["same_conf"] or not x["conf"]:
        continue
    tab = stand[(x["season"], x["conf"])]
    mine, theirs = tab[x["team"]], tab[x["opp"]]
    if len(tab) >= 6 and mine[0] + mine[1] >= 8:
        lead = max(v[0] - v[1] for v in tab.values())
        x["gb"] = (lead - (mine[0] - mine[1])) / 2
        x["ogb"] = (lead - (theirs[0] - theirs[1])) / 2
        x["crank"] = 1 + sum(1 for v in tab.values() if v[0] - v[1] > mine[0] - mine[1])
    tab[x["team"]][0 if x["won"] else 1] += 1
late = [x for x in rows_ if month(x) in ("02", "03") and x.get("gb") is not None and x["same_conf"]]
race = [x for x in dogs(late) if x["gb"] >= 5 and x["ogb"] <= 1]
out.h("a. THE OUT-OF-THE-RACE DOG (5+ games back) vs A CONTENDER (within a game of first), Feb-Mar conference play")
out.c("base: Feb-Mar conference dog +100..+350", dogs(late))
out.c("the cell: 5+ back vs a contender, dog ML", race)
out.c("  not on a 5+ game skid (the built weight)", [x for x in race if x.get("streak", 0) > -5])
out.c("  on a 5+ game skid", [x for x in race if x.get("streak", 0) <= -5])
out.c("  the opponent is the LEADER (0 back)", [x for x in race if x["ogb"] == 0])
out.c("  the opponent half a game to a game back", [x for x in race if 0 < x["ogb"] <= 1])
out.c("  3-4.5 games back vs a contender (the dose below)", [x for x in dogs(late) if 3 <= x["gb"] < 5 and x["ogb"] <= 1])
out.c("  5-6.5 back", [x for x in race if x["gb"] < 7])
out.c("  7+ back", [x for x in race if x["gb"] >= 7])
out.c("  +100..+200", [x for x in race if x["ml"] <= 200])
out.c("  +201..+350", [x for x in race if x["ml"] > 200])
out.c("  home dog", [x for x in race if x["venue"] == "home"])
out.c("  road dog", [x for x in race if x["venue"] == "away"])
for t in ("power", "mid", "low"):
    out.c(f"  {t} tier", [x for x in race if x["tier"] == t])
out.c("  February", [x for x in race if month(x) == "02"])
out.c("  March", [x for x in race if month(x) == "03"])
out.c("  the contender's side ATS (across)", [x for x in spreads(late) if x["ogb"] >= 5 and x["gb"] <= 1 and x.get("ml", 0) < 0], profit_ats)
out.c("  5+ back vs a contender, the dog's ATS", [x for x in spreads(late) if x["gb"] >= 5 and x["ogb"] <= 1 and x.get("ml", 0) >= 100], profit_ats)
out.c("  5+ back vs a MID-table team (2-4 back), dog ML (control)", [x for x in dogs(late) if x["gb"] >= 5 and 2 <= x["ogb"] <= 4])
out.c("  5+ back vs another 5+ back team, dog ML (control)", [x for x in dogs(late) if x["gb"] >= 5 and x["ogb"] >= 5])
out.c("  January: 5+ back vs a contender (control month)", [x for x in dogs(rows_) if month(x) == "01" and x.get("gb") is not None and x["gb"] >= 5 and x["ogb"] <= 1 and x["same_conf"]])
out.c("  Feb-Mar, 5+ back vs a contender, NO 'we lost / they won' flag",
      [x for x in race if not (x.get("last") and x.get("olast") and x["last"]["won"] is False and x["olast"]["won"] is True)])

# ---- b / c. identities (s4's) ----
TB = teambox()
score = {}
for x in rows_:
    score[(x["id"], x["team"])] = (x["pts"] + x["margin"]) / 2
agg = defaultdict(lambda: defaultdict(float))
lg = defaultdict(lambda: defaultdict(float))
feat = {}
for x in rows_:
    if x["season"] < 2021:
        continue
    s, tm, op = x["season"], x["team"], x["opp"]
    a, L = agg[(s, tm)], lg[s]
    if a["n"] >= 5 and L["n"] >= 200:
        feat[(x["id"], tm)] = {"off": 100 * a["pts"] / a["poss"] - 100 * L["pts"] / L["poss"],
                               "def": 100 * a["opts"] / a["oposs"] - 100 * L["pts"] / L["poss"], "tom": (a["oto"] - a["to"]) / a["n"]}
    b = TB.get(x["id"])
    if b and tm in b and op in b and (x["id"], tm) in score and (x["id"], op) in score:
        me, th = b[tm], b[op]
        for d in (a, L):
            d["n"] += 1; d["pts"] += score[(x["id"], tm)]; d["poss"] += me["poss"]; d["opts"] += score[(x["id"], op)]
            d["oposs"] += th["poss"]; d["to"] += me["to"]; d["oto"] += th["to"]
have = []
for x in rows_:
    f, of = feat.get((x["id"], x["team"])), feat.get((x["id"], x["opp"]))
    if f and of:
        x["f"], x["of"] = f, of
        have.append(x)
C = {}
for k in ("off", "def", "tom"):
    for s in sorted({x["season"] for x in have}):
        v = sorted(x["f"][k] for x in have if x["season"] == s)
        C[(k, s)] = (v[len(v) // 6], v[len(v) // 3], v[len(v) // 2], v[2 * len(v) // 3], v[5 * len(v) // 6])
hi = lambda x, k, w="f": x[w][k] >= C[(k, x["season"])][3]
lo = lambda x, k, w="f": x[w][k] <= C[(k, x["season"])][1]
ofirst = [x for x in have if hi(x, "off") and not lo(x, "def")]
od = [x for x in dogs(ofirst) if month(x) in ("01", "02", "03")]
out.h("b. THE OFFENSE-FIRST DOG (top-third offense, defense not in the best third), Jan-Mar")
out.c("base: Jan-Mar dog with both reads", [x for x in dogs(have) if month(x) in ("01", "02", "03")])
out.c("the cell: offense-first dog, Jan-Mar", od)
out.c("  defense in the WORST third", [x for x in od if x["f"]["def"] >= C[("def", x["season"])][3]])
out.c("  defense in the middle third", [x for x in od if C[("def", x["season"])][1] < x["f"]["def"] < C[("def", x["season"])][3]])
out.c("  offense in the top SIXTH", [x for x in od if x["f"]["off"] >= C[("off", x["season"])][4]])
out.c("  +100..+200", [x for x in od if x["ml"] <= 200])
out.c("  +201..+350", [x for x in od if x["ml"] > 200])
out.c("  home", [x for x in od if x["venue"] == "home"])
out.c("  road", [x for x in od if x["venue"] == "away"])
out.c("  not on a 5+ skid", [x for x in od if x.get("streak", 0) > -5])
out.c("  Nov-Dec (control)", [x for x in dogs(ofirst) if month(x) in ("11", "12")])
out.c("  vs a defense-first favorite", [x for x in od if lo(x, "def", "of") and not hi(x, "off", "of")])
out.c("  vs any other favorite", [x for x in od if not (lo(x, "def", "of") and not hi(x, "off", "of"))])
for t in ("power", "mid", "low"):
    out.c(f"  {t} tier", [x for x in od if x["tier"] == t])
out.c("  the favorite ACROSS an offense-first dog, Jan-Mar, -101..-250", [x for x in have if month(x) in ("01", "02", "03") and -250 <= x.get("ml", 0) <= -101 and hi(x, "off", "of") and not lo(x, "def", "of")])
out.c("  offense-first side ATS, Jan-Mar", [x for x in spreads(ofirst) if month(x) in ("01", "02", "03")], profit_ats)
out.c("  offense-first small fav -101..-150, Jan-Mar", [x for x in favs(ofirst) if month(x) in ("01", "02", "03")])
out.c("  the mirror: defense-first dog, Jan-Mar", [x for x in dogs(have) if month(x) in ("01", "02", "03") and lo(x, "def") and not hi(x, "off")])
tp = [x for x in favs(have) if lo(x, "tom")]
out.h("c. THE TURNOVER-PRONE SMALL FAVORITE (-101..-150; turnover margin in the bottom third)")
out.c("base: small fav with both reads", favs(have))
out.c("the cell: turnover-prone small fav", tp)
out.c("  bottom SIXTH", [x for x in tp if x["f"]["tom"] <= C[("tom", x["season"])][0]])
out.c("  the middle of the bottom third", [x for x in tp if x["f"]["tom"] > C[("tom", x["season"])][0]])
out.c("  home", [x for x in tp if x["venue"] == "home"])
out.c("  away / neutral", [x for x in tp if x["venue"] != "home"])
out.c("  Nov-Dec", [x for x in tp if month(x) in ("11", "12")])
out.c("  Jan-Mar", [x for x in tp if month(x) in ("01", "02", "03")])
out.c("  vs a turnover-margin dog (top third)", [x for x in tp if hi(x, "tom", "of")])
out.c("  vs any other dog", [x for x in tp if not hi(x, "tom", "of")])
out.c("  -101..-125", [x for x in tp if x["ml"] >= -125])
out.c("  -126..-150", [x for x in tp if x["ml"] < -125])
out.c("  the dog across, ML", [x for x in dogs(have, 100, 150) if lo(x, "tom", "of")])
out.c("  turnover-prone fav -151..-250 (the band above)", [x for x in favs(have, -250, -151) if lo(x, "tom")])
out.c("  turnover-prone side ATS (all prices)", [x for x in spreads(have) if lo(x, "tom")], profit_ats)
out.c("  NOT an offense-first team either", [x for x in tp if not (hi(x, "off") and not lo(x, "def"))])

# ---- d. the new coach's small favorite (s1) ----
table = nc.load()
for x in rows_:
    x["c"] = nc.state(x["team"], x["start"], table)
    x["oc"] = nc.state(x["opp"], x["start"], table)
nf = [x for x in favs(rows_) if x.get("c") and x["c"]["new"] and month(x) in ("01", "02", "03")]
out.h("d. THE NEW COACH'S SMALL FAVORITE (-101..-150) IN JAN-MAR")
out.c("base: Jan-Mar small fav", [x for x in favs(rows_) if month(x) in ("01", "02", "03")])
out.c("the cell: new coach, small fav, Jan-Mar", nf)
out.c("  home", [x for x in nf if x["venue"] == "home"])
out.c("  away / neutral", [x for x in nf if x["venue"] != "home"])
out.c("  conference game", [x for x in nf if x["same_conf"]])
out.c("  non-conference", [x for x in nf if not x["same_conf"]])
for t in ("power", "mid", "low"):
    out.c(f"  {t} tier", [x for x in nf if x["tier"] == t])
out.c("  -101..-125", [x for x in nf if x["ml"] >= -125])
out.c("  -126..-150", [x for x in nf if x["ml"] < -125])
out.c("  vs a new coach too", [x for x in nf if x.get("oc") and x["oc"]["new"]])
out.c("  vs a coach in year 2+", [x for x in nf if x.get("oc") and not x["oc"]["new"]])
out.c("  the team's win % under .500 at tip", [x for x in nf if (x.get("wpct") or 0) < 0.5])
out.c("  the team's win % .500+ at tip", [x for x in nf if (x.get("wpct") or 0) >= 0.5])
out.c("  the dog across, ML", [x for x in dogs(rows_, 100, 150) if x.get("oc") and x["oc"]["new"] and month(x) in ("01", "02", "03")])
out.c("  new coach, fav -151..-250, Jan-Mar", [x for x in favs(rows_, -250, -151) if x.get("c") and x["c"]["new"] and month(x) in ("01", "02", "03")])
out.c("  new coach, fav -251..-500, Jan-Mar", [x for x in favs(rows_, -500, -251) if x.get("c") and x["c"]["new"] and month(x) in ("01", "02", "03")])
out.c("  December (control)", [x for x in favs(rows_) if x.get("c") and x["c"]["new"] and month(x) == "12"])
out.save()
