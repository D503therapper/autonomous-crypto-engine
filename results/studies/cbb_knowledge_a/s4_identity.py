"""S4 - TEAM IDENTITY FROM THE FULL TEAM BOX (data/sports/teamstats - threes, free throws, turnovers, steals,
rebounds; 2021-22 .. now, ~100% of finals). Walk-forward, season to date before tonight, both teams 5+ box games:
  off = points per 100 possessions, def = allowed per 100 (possessions = FGA - OREB + TO + 0.475 FTA), each against
  the D1 average so far that season; DEFENSE-FIRST = def in the best third and off under the median, OFFENSE-FIRST the
  reverse; TURNOVER MARGIN = turnovers forced minus committed, a game; FREE-THROW RATE = FTA / FGA; THREE RATE = 3PA / FGA.
Cells: each identity as a dog / favorite / spread side, the matchup gap, the close-game price (a dog +100..+130 or a
favorite -101..-130 = the spread inside 3), Jan-Mar vs Nov-Dec. Train 2021-22, held out 2023 / 2024 / 2025; ESPN's
open on dog cells. (The 11/3 FABLE style pass had only five player-box stats - no threes / free throws / turnovers.)"""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *  # noqa: F401,F403

out = Out("s4")
TB = teambox()
rows_ = [x for x in regular(rows()) if x["season"] >= 2021]
rows_.sort(key=lambda x: (x["start"], x["id"]))
# per-game team lines with points (from the games file) - the row holds the score
score = {}
for x in rows_:
    score[(x["id"], x["team"])] = x["margin"] + (x["pts"] - x["margin"]) / 2   # my points = (total + margin) / 2
agg = defaultdict(lambda: defaultdict(float))     # (season, team) -> running sums
lg = defaultdict(lambda: defaultdict(float))      # season -> D1 running sums (for the average)
feat = {}
for x in rows_:
    s, tm, op = x["season"], x["team"], x["opp"]
    a = agg[(s, tm)]
    L = lg[s]
    if a["n"] >= 5 and L["n"] >= 200:
        poss = a["poss"] / a["n"]
        f = {"n": a["n"], "off": 100 * a["pts"] / a["poss"] - 100 * L["pts"] / L["poss"],
             "def": 100 * a["opts"] / a["oposs"] - 100 * L["pts"] / L["poss"],
             "tom": (a["oto"] - a["to"]) / a["n"], "to_rate": a["to"] / a["poss"], "force": a["oto"] / a["oposs"],
             "ftr": a["fta"] / a["fga"], "tpr": a["tpa"] / a["fga"], "pace": poss, "ftp": a["ftm"] / max(a["fta"], 1),
             "oreb": a["oreb"] / max(a["oreb"] + a["odreb"], 1), "stl": a["stl"] / a["n"]}
        feat[(x["id"], tm)] = f
    # update after reading (the game's own box is NOT in its own read)
    b = TB.get(x["id"])
    if b and tm in b and op in b:
        me, th = b[tm], b[op]
        mp = score.get((x["id"], tm))
        opts = score.get((x["id"], op))
        if mp is None or opts is None:
            continue
        for d, key in ((a, None), (L, None)):
            d["n"] += 1
            d["pts"] += mp; d["poss"] += me["poss"]; d["opts"] += opts; d["oposs"] += th["poss"]
            d["to"] += me["to"]; d["oto"] += th["to"]; d["fta"] += me["fta"]; d["fga"] += me["fga"]; d["ftm"] += me["ftm"]
            d["tpa"] += me["tpa"]; d["oreb"] += me["oreb"]; d["odreb"] += th["dreb"]; d["stl"] += me["stl"]
for x in rows_:
    x["f"] = feat.get((x["id"], x["team"]))
    x["of"] = feat.get((x["id"], x["opp"]))
have = [x for x in rows_ if x["f"] and x["of"]]
out.note(f"sides 2021+ {len(rows_)}, both teams 5+ box games {len(have)}")
# season-to-date terciles on each stat (by season, over the sides so far - a rank)
def tercile(key):
    cuts = {}
    for s in sorted({x["season"] for x in have}):
        v = sorted(x["f"][key] for x in have if x["season"] == s)
        cuts[s] = (v[len(v) // 3], v[2 * len(v) // 3])
    return cuts
C = {k: tercile(k) for k in ("off", "def", "tom", "ftr", "tpr", "force", "to_rate", "pace")}


def hi(x, k, who="f"):
    return x[who][k] >= C[k][x["season"]][1]


def lo(x, k, who="f"):
    return x[who][k] <= C[k][x["season"]][0]


month = lambda x: x["start"][5:7]
closeish = lambda xs: [x for x in xs if x.get("ml") is not None and -130 <= x["ml"] <= 130]
# defense-first: def in the best third (lowest allowed), off NOT in the top third; offense-first the reverse
dfirst = [x for x in have if lo(x, "def") and not hi(x, "off")]
ofirst = [x for x in have if hi(x, "off") and not lo(x, "def")]
both = [x for x in have if hi(x, "off") and lo(x, "def")]
out.h("A. DEFENSE-FIRST vs OFFENSE-FIRST (season to date, vs the D1 average)")
by_season_ats(have, "base: every side with both reads", out)
by_season_ats(dfirst, "defense-first team", out)
by_season_ats(ofirst, "offense-first team", out)
by_season_ats(both, "good at both", out)
out.c("defense-first dog +100..+200", dogs(dfirst, 100, 200))
out.c("defense-first dog +201..+350", dogs(dfirst, 201, 350))
out.c("offense-first dog +100..+200", dogs(ofirst, 100, 200))
out.c("offense-first dog +201..+350", dogs(ofirst, 201, 350))
out.c("defense-first dog, Jan-Mar", [x for x in dogs(dfirst) if month(x) in ("01", "02", "03")])
out.c("offense-first dog, Jan-Mar", [x for x in dogs(ofirst) if month(x) in ("01", "02", "03")])
out.c("defense-first dog, away", [x for x in dogs(dfirst) if x["venue"] == "away"])
out.c("defense-first dog, home", [x for x in dogs(dfirst) if x["venue"] == "home"])
out.c("defense-first vs offense-first, ATS", [x for x in spreads(dfirst) if hi(x, "off", "of") and not lo(x, "def", "of")], profit_ats)
out.c("defense-first vs offense-first, dog ML", [x for x in dogs(dfirst) if hi(x, "off", "of") and not lo(x, "def", "of")])
out.c("offense-first vs defense-first, ATS", [x for x in spreads(ofirst) if lo(x, "def", "of") and not hi(x, "off", "of")], profit_ats)
out.c("offense-first vs defense-first, dog ML", [x for x in dogs(ofirst) if lo(x, "def", "of") and not hi(x, "off", "of")])
out.c("defense-first fav -151..-300", favs(dfirst, -300, -151))
out.c("offense-first fav -151..-300", favs(ofirst, -300, -151))
out.c("defense-first, close price (-130..+130), ML", closeish(dfirst))
out.c("offense-first, close price (-130..+130), ML", closeish(ofirst))
out.c("defense-first vs a bad offense (bottom third), dog ML", [x for x in dogs(dfirst) if lo(x, "off", "of")])
out.c("the UNDER with a defense-first dog in it (over odds as -110)", [x for x in dogs(dfirst) if x.get("total")],
      lambda x: (None if x["pts"] == x["total"] else (0.909 if x["pts"] < x["total"] else -1.0)))

out.h("B. TURNOVER MARGIN (forced minus committed, a game)")
tplus = [x for x in have if hi(x, "tom")]
tminus = [x for x in have if lo(x, "tom")]
by_season_ats(tplus, "turnover-margin team (top third)", out)
by_season_ats(tminus, "turnover-prone team (bottom third)", out)
out.c("turnover-margin dog +100..+200", dogs(tplus, 100, 200))
out.c("turnover-margin dog +201..+350", dogs(tplus, 201, 350))
out.c("turnover-margin dog vs a turnover-prone fav, ML", [x for x in dogs(tplus) if lo(x, "tom", "of")])
out.c("turnover-margin side vs a turnover-prone side, ATS", [x for x in spreads(tplus) if lo(x, "tom", "of")], profit_ats)
out.c("turnover-prone side vs a turnover-margin side, ATS", [x for x in spreads(tminus) if hi(x, "tom", "of")], profit_ats)
out.c("turnover-prone dog +100..+350", dogs(tminus))
out.c("turnover-prone fav -101..-150", favs(tminus))
out.c("forces turnovers (top third) vs a team that coughs it up (top third to_rate), ATS",
      [x for x in spreads(have) if hi(x, "force") and hi(x, "to_rate", "of")], profit_ats)
out.c("forces turnovers vs a team that coughs it up, dog ML", [x for x in dogs(have) if hi(x, "force") and hi(x, "to_rate", "of")])
out.c("forces turnovers vs a team that coughs it up, fav -101..-150", [x for x in favs(have) if hi(x, "force") and hi(x, "to_rate", "of")])
out.c("careful (bottom third to_rate) dog vs a team that forces nothing, ML", [x for x in dogs(have) if lo(x, "to_rate") and lo(x, "force", "of")])
out.c("turnover-margin team, close price, ML", closeish(tplus))
out.c("turnover-prone team, close price, ML", closeish(tminus))
out.c("turnover-margin team, Jan-Mar, ATS", [x for x in spreads(tplus) if month(x) in ("01", "02", "03")], profit_ats)
out.c("turnover-margin dog, Jan-Mar, ML", [x for x in dogs(tplus) if month(x) in ("01", "02", "03")])

out.h("C. FREE-THROW RELIANT (FTA / FGA top third) - and the close game")
fplus = [x for x in have if hi(x, "ftr")]
fminus = [x for x in have if lo(x, "ftr")]
by_season_ats(fplus, "free-throw reliant team", out)
by_season_ats(fminus, "rarely at the line", out)
out.c("free-throw reliant, close price (-130..+130), ML", closeish(fplus))
out.c("rarely at the line, close price (-130..+130), ML", closeish(fminus))
out.c("free-throw reliant, close price, ATS", [x for x in spreads(fplus) if x.get("sp") is not None and abs(x["sp"]) <= 3], profit_ats)
out.c("rarely at the line, close price, ATS", [x for x in spreads(fminus) if x.get("sp") is not None and abs(x["sp"]) <= 3], profit_ats)
good_ft = [x for x in fplus if x["f"]["ftp"] >= 0.74]
out.c("free-throw reliant AND shoots 74%+, close price, ML", closeish(good_ft))
out.c("free-throw reliant AND shoots 74%+, close price, ATS", [x for x in spreads(good_ft) if abs(x["sp"]) <= 3], profit_ats)
out.c("free-throw reliant but shoots under 68%, close price, ML", closeish([x for x in fplus if x["f"]["ftp"] < 0.68]))
out.c("free-throw reliant dog +100..+200", dogs(fplus, 100, 200))
out.c("free-throw reliant fav -101..-150", favs(fplus))
out.c("free-throw reliant vs a team that fouls little (bottom third opp FT rate proxy: its own ftr), ATS",
      [x for x in spreads(fplus) if lo(x, "ftr", "of")], profit_ats)
out.c("free-throw reliant dog, Jan-Mar, close price", [x for x in closeish(fplus) if month(x) in ("01", "02", "03") and x["ml"] > 0])

out.h("D. THREE-POINT RELIANT (3PA / FGA top third) and PACE")
tp = [x for x in have if hi(x, "tpr")]
tm = [x for x in have if lo(x, "tpr")]
by_season_ats(tp, "three-heavy team", out)
by_season_ats(tm, "three-light team", out)
out.c("three-heavy dog +201..+350 (variance)", dogs(tp, 201, 350))
out.c("three-light dog +201..+350", dogs(tm, 201, 350))
out.c("three-heavy dog, away", [x for x in dogs(tp) if x["venue"] == "away"])
out.c("three-heavy vs three-light, ATS", [x for x in spreads(tp) if lo(x, "tpr", "of")], profit_ats)
out.c("three-light vs three-heavy, ATS", [x for x in spreads(tm) if hi(x, "tpr", "of")], profit_ats)
out.c("three-heavy fav -101..-150", favs(tp))
out.c("three-heavy, close price, ML", closeish(tp))
fast = [x for x in have if hi(x, "pace")]
slow = [x for x in have if lo(x, "pace")]
out.c("fast team (top third pace) fav -101..-150", favs(fast))
out.c("fast fav -101..-150 vs a slow dog", [x for x in favs(fast) if lo(x, "pace", "of")])
out.c("slow dog vs a fast fav, ML", [x for x in dogs(slow) if hi(x, "pace", "of")])
out.c("fast dog vs a slow fav, ML", [x for x in dogs(fast) if lo(x, "pace", "of")])
out.c("fast side ATS", spreads(fast), profit_ats)
out.c("slow side ATS", spreads(slow), profit_ats)
out.save()
