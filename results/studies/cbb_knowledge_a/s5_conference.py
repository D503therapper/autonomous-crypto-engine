"""S5 - CONFERENCE KNOWLEDGE (the 11/3 (B) inferred conferences - teams sharing 3+ Jan-Feb opponents, tiers by anchor
schools; no conference field on file).
  A. HOME-COURT STRENGTH BY LEAGUE, walk-forward: a league's home side cover margin in conference games in the seasons
     BEFORE this one (300+ sides) -> this season's home side ATS / home dog ML in that league (the strong-floor leagues
     vs the weak ones); the road side across.
  B. ROAD TEAMS IN SPECIFIC LEAGUES: the league's road cover record so far THIS season (walk-forward, 60+ sides) and
     the prior seasons' road record; the road dog / road favorite by league tier in conference play.
  C. LATE-SEASON STANDINGS PRESSURE (Feb-Mar, conference games): the conference standings at tip (conference W-L so
     far) - the leader / within a game, the bottom three, a team 5+ games out of first; the engine's Elo rank as the
     bubble proxy (top 8 = locked, 25-60 = the bubble, 100+ = nothing to play for); each as a dog / favorite / ATS and
     the matchup between them. Train 2018-22, held out 2023 / 2024 / 2025; ESPN's open on dog cells."""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *  # noqa: F401,F403

out = Out("s5")
rows_ = regular(rows())
rows_.sort(key=lambda x: (x["start"], x["id"]))
conf_rows = [x for x in rows_ if x["same_conf"] and x["venue"] != "neutral" and x["conf"]]
out.note(f"regular-season sides {len(rows_)}, conference home / road sides {len(conf_rows)}")
# A. prior-season home cover margin by league (the conf key is per season - link leagues across seasons by their members)
# (a league = the set of its member ids; across seasons match on 60%+ shared members)
members = defaultdict(set)
for x in conf_rows:
    members[(x["season"], x["conf"])].add(x["team"])
link = {}            # (season, conf) -> a stable league id
stable = {}
for key in sorted(members):
    s, c = key
    best = None
    for (ps, pc), lid in link.items():
        if ps == s - 1:
            shared = len(members[key] & members[(ps, pc)]) / max(len(members[key]), 1)
            if shared >= 0.6 and (best is None or shared > best[0]):
                best = (shared, lid)
    link[key] = best[1] if best else f"L{len(stable)}"
    stable.setdefault(link[key], set()).update(members[key])
for x in conf_rows:
    x["lid"] = link[(x["season"], x["conf"])]
hcm = defaultdict(list)       # (lid, season) -> home cover margins in conference games
rcm = defaultdict(list)
for x in conf_rows:
    if x.get("sp") is not None:
        (hcm if x["venue"] == "home" else rcm)[(x["lid"], x["season"])].append(x["margin"] + x["sp"])
def prior_home(lid, s):
    v = [m for (l, ss), ms in hcm.items() if l == lid and ss < s for m in ms]
    return (sum(v) / len(v), len(v)) if len(v) >= 300 else (None, len(v))
for x in conf_rows:
    x["ph"], x["phn"] = prior_home(x["lid"], x["season"])
pr = [x for x in conf_rows if x["ph"] is not None]
out.note(f"conference sides with a prior-seasons league home read (300+): {len(pr)}")
cuts = {}
for s in sorted({x["season"] for x in pr}):
    v = sorted({(x["lid"], x["ph"]) for x in pr if x["season"] == s}, key=lambda t: t[1])
    if len(v) >= 6:
        cuts[s] = (v[len(v) // 4][1], v[3 * len(v) // 4][1])
out.note("league home-margin quartile cuts: " + ", ".join(f"{s} {a:+.2f}/{b:+.2f}" for s, (a, b) in cuts.items()))
strong = [x for x in pr if x["season"] in cuts and x["ph"] >= cuts[x["season"]][1]]
weak = [x for x in pr if x["season"] in cuts and x["ph"] <= cuts[x["season"]][0]]
out.h("A. HOME-COURT STRENGTH BY LEAGUE (prior seasons' home cover margin in conference play -> this season)")
out.c("base: conference home side ATS", [x for x in spreads(pr) if x["venue"] == "home"], profit_ats)
out.c("base: conference home dog +100..+350 ML", [x for x in dogs(pr) if x["venue"] == "home"])
out.c("strong-floor league (top quartile): home side ATS", [x for x in spreads(strong) if x["venue"] == "home"], profit_ats)
out.c("strong-floor league: home dog +100..+350 ML", [x for x in dogs(strong) if x["venue"] == "home"])
out.c("strong-floor league: home fav -101..-150 ML", [x for x in favs(strong) if x["venue"] == "home"])
out.c("strong-floor league: road side ATS", [x for x in spreads(strong) if x["venue"] == "away"], profit_ats)
out.c("strong-floor league: road dog +100..+350 ML", [x for x in dogs(strong) if x["venue"] == "away"])
out.c("weak-floor league (bottom quartile): home side ATS", [x for x in spreads(weak) if x["venue"] == "home"], profit_ats)
out.c("weak-floor league: home dog +100..+350 ML", [x for x in dogs(weak) if x["venue"] == "home"])
out.c("weak-floor league: road side ATS", [x for x in spreads(weak) if x["venue"] == "away"], profit_ats)
out.c("weak-floor league: road dog +100..+350 ML", [x for x in dogs(weak) if x["venue"] == "away"])
out.c("weak-floor league: road fav -101..-150 ML", [x for x in favs(weak) if x["venue"] == "away"])
# does last season's league home margin predict this season's? (price-free)
import statistics as stt
pairs = [(x["ph"], x["margin"] + x["sp"]) for x in pr if x["venue"] == "home" and x.get("sp") is not None]
if len(pairs) > 100:
    out.note(f"   corr(prior league home margin, this game's home cover margin) = {stt.correlation([a for a, _ in pairs], [b for _, b in pairs]):+.3f} on {len(pairs)}")
for t in ("power", "mid", "low"):
    out.c(f"{t}-tier league: conference home side ATS", [x for x in spreads(pr) if x["venue"] == "home" and x["tier"] == t], profit_ats)
    out.c(f"{t}-tier league: conference home dog ML", [x for x in dogs(pr) if x["venue"] == "home" and x["tier"] == t])
    out.c(f"{t}-tier league: conference road dog ML", [x for x in dogs(pr) if x["venue"] == "away" and x["tier"] == t])
    out.c(f"{t}-tier league: conference road fav -101..-150 ML", [x for x in favs(pr) if x["venue"] == "away" and x["tier"] == t])

out.h("B. ROAD TEAMS BY LEAGUE - this season's league road cover record so far (60+ sides) and the prior seasons'")
run = defaultdict(list)
for x in conf_rows:
    key = (x["lid"], x["season"])
    v = run[key]
    x["rr"] = (sum(v) / len(v)) if len(v) >= 60 else None
    x["rrn"] = len(v)
    if x.get("sp") is not None and x["venue"] == "away":
        v.append(x["margin"] + x["sp"])
rr = [x for x in conf_rows if x["rr"] is not None]
out.c("league road cover margin so far 1.5+: road side ATS", [x for x in spreads(rr) if x["venue"] == "away" and x["rr"] >= 1.5], profit_ats)
out.c("league road cover margin so far 1.5+: road dog ML", [x for x in dogs(rr) if x["venue"] == "away" and x["rr"] >= 1.5])
out.c("league road cover margin so far -1.5 or worse: road side ATS", [x for x in spreads(rr) if x["venue"] == "away" and x["rr"] <= -1.5], profit_ats)
out.c("league road cover margin so far -1.5 or worse: home side ATS", [x for x in spreads(rr) if x["venue"] == "home" and x["rr"] <= -1.5], profit_ats)
out.c("league road cover margin so far -1.5 or worse: home dog ML", [x for x in dogs(rr) if x["venue"] == "home" and x["rr"] <= -1.5])
def prior_road(lid, s):
    v = [m for (l, ss), ms in rcm.items() if l == lid and ss < s for m in ms]
    return (sum(v) / len(v)) if len(v) >= 300 else None
for x in conf_rows:
    x["prr"] = prior_road(x["lid"], x["season"])
prr = [x for x in conf_rows if x["prr"] is not None]
out.c("prior seasons' league road margin +1 or better: road side ATS", [x for x in spreads(prr) if x["venue"] == "away" and x["prr"] >= 1], profit_ats)
out.c("prior seasons' league road margin +1 or better: road dog ML", [x for x in dogs(prr) if x["venue"] == "away" and x["prr"] >= 1])
out.c("prior seasons' league road margin -1 or worse: road side ATS", [x for x in spreads(prr) if x["venue"] == "away" and x["prr"] <= -1], profit_ats)
out.c("prior seasons' league road margin -1 or worse: home dog ML", [x for x in dogs(prr) if x["venue"] == "home" and x["prr"] <= -1])

out.h("C. LATE-SEASON STANDINGS PRESSURE (Feb-Mar conference games)")
# conference standings at tip: conference W-L so far this season (home / road / neutral conference games)
stand = defaultdict(lambda: defaultdict(lambda: [0, 0]))     # (season, conf) -> team -> [w, l]
for x in rows_:
    if not x["same_conf"] or not x["conf"]:
        continue
    key = (x["season"], x["conf"])
    tab = stand[key]
    mine, theirs = tab[x["team"]], tab[x["opp"]]
    gp = mine[0] + mine[1]
    x["cw"], x["cl"] = mine[0], mine[1]
    wins = sorted((v[0] - v[1] for v in tab.values()), reverse=True)
    if len(tab) >= 6 and gp >= 8:
        lead = wins[0]
        x["gb"] = (lead - (mine[0] - mine[1])) / 2
        rank = 1 + sum(1 for v in tab.values() if v[0] - v[1] > mine[0] - mine[1])
        x["crank"], x["csize"] = rank, len(tab)
        orank = 1 + sum(1 for v in tab.values() if v[0] - v[1] > theirs[0] - theirs[1])
        x["ocrank"] = orank
        x["ogb"] = (lead - (theirs[0] - theirs[1])) / 2
    # update after reading: only once per game (the home row comes first in the pair? no - update on each side's row
    # for its own team only)
    tab[x["team"]][0 if x["won"] else 1] += 1
late = [x for x in rows_ if x["start"][5:7] in ("02", "03") and x.get("crank") and x["same_conf"]]
out.note(f"Feb-Mar conference sides with standings at tip: {len(late)}")
by_season_ats(late, "base: Feb-Mar conference side with standings", out)
lead = [x for x in late if x["gb"] <= 1.0]
bottom = [x for x in late if x["crank"] >= x["csize"] - 2]
far = [x for x in late if x["gb"] >= 5]
by_season_ats(lead, "the leader / within a game of first", out)
by_season_ats(bottom, "the bottom three of the league", out)
by_season_ats(far, "5+ games out of first", out)
by_season_ats([x for x in lead if x["ogb"] >= 5], "the leader vs a team 5+ games out", out)
by_season_ats([x for x in far if x["ogb"] <= 1], "5+ games out vs the leader / contender", out)
by_season_ats([x for x in lead if x["ogb"] <= 1], "contender vs contender (both within a game)", out)
out.c("bottom-three home dog +100..+350", [x for x in dogs(bottom) if x["venue"] == "home"])
out.c("bottom-three road dog +100..+350", [x for x in dogs(bottom) if x["venue"] == "away"])
out.c("the leader as a road fav -101..-150", [x for x in favs(lead) if x["venue"] == "away"])
out.c("the leader as a road dog", [x for x in dogs(lead) if x["venue"] == "away"])
out.c("the leader at home, fav -151..-400", [x for x in favs(lead, -400, -151) if x["venue"] == "home"])
# the last two weeks (March conference games before the tournaments) - the seeds are set
mar = [x for x in late if x["start"][5:7] == "03"]
by_season_ats([x for x in mar if x["gb"] <= 1], "March: the leader / within a game", out)
by_season_ats([x for x in mar if x["crank"] >= x["csize"] - 2], "March: the bottom three", out)
# Elo rank as the bubble proxy (top 8 locked, 25-60 bubble, 100+ nothing)
by_n = defaultdict(list)
for x in rows_:
    by_n[(x["season"], x["night"])].append(x)
cur = {}
for key in sorted(by_n):
    s = key[0]
    pool = sorted(((e, t) for (ss, t), (e, n) in cur.items() if ss == s and n >= 10), reverse=True)
    rank = {t: i + 1 for i, (e, t) in enumerate(pool)}
    for x in by_n[key]:
        x["erank"], x["oerank"] = rank.get(x["team"]), rank.get(x["opp"])
    for x in by_n[key]:
        cur[(s, x["team"])] = (x["elo"], x["gn"])
lr = [x for x in rows_ if x["start"][5:7] in ("02", "03") and x.get("erank") and x.get("oerank")]
locked = [x for x in lr if x["erank"] <= 8]
bubble = [x for x in lr if 25 <= x["erank"] <= 60]
nothing = [x for x in lr if x["erank"] >= 100]
by_season_ats(locked, "Feb-Mar: a top-8 team (locked)", out)
by_season_ats(bubble, "Feb-Mar: the bubble (Elo rank 25-60)", out)
by_season_ats(nothing, "Feb-Mar: rank 100+ (nothing to play for)", out)
out.c("locked team as a fav -101..-200 on the road", [x for x in favs(locked, -200, -101) if x["venue"] == "away"])
out.c("the dog across a locked team, Feb-Mar", [x for x in dogs(lr) if x["oerank"] <= 8])
out.c("the dog across a locked team, March", [x for x in dogs(lr) if x["oerank"] <= 8 and x["start"][5:7] == "03"])
out.c("the bubble team as a dog vs a locked team", [x for x in dogs(bubble) if x["oerank"] <= 8])
out.c("the bubble team as a dog vs a rank 100+ team", [x for x in dogs(bubble) if x["oerank"] >= 100])
out.c("the bubble team as a fav -101..-150 vs a rank 100+ team", [x for x in favs(bubble) if x["oerank"] >= 100])
out.c("the bubble team as a fav -151..-300 vs a rank 100+ team", [x for x in favs(bubble, -300, -151) if x["oerank"] >= 100])
out.c("rank 100+ home dog vs a bubble team", [x for x in dogs(nothing) if x["venue"] == "home" and 25 <= x["oerank"] <= 60])
out.c("the bubble team on the road, ATS, Feb-Mar", [x for x in spreads(bubble) if x["venue"] == "away"], profit_ats)
out.c("the bubble team at home, ATS, Feb-Mar", [x for x in spreads(bubble) if x["venue"] == "home"], profit_ats)
out.c("the bubble team off a loss, dog ML, Feb-Mar", [x for x in dogs(bubble) if x.get("last") and x["last"]["won"] is False])
out.c("the bubble team off a loss, ATS, Feb-Mar", [x for x in spreads(bubble) if x.get("last") and x["last"]["won"] is False], profit_ats)
out.c("the bubble team off a loss, fav -101..-150, Feb-Mar", [x for x in favs(bubble) if x.get("last") and x["last"]["won"] is False])
out.c("the bubble team after 2 straight losses, ATS, Feb-Mar", [x for x in spreads(bubble) if x.get("streak", 0) <= -2], profit_ats)
out.save()
