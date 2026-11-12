"""11/12 DEEP PROGRAM - B4: COLLEGE FOOTBALL - THE LATE-SEASON SPOTS + THE SCHEDULE-STRENGTH MISMATCH (FBS-vs-FBS games,
closes 2018-26, the fifteen-studies table; train to 2021 / blind 2022 on; the close at its juice).
NOT re-run (dead / built): rivalry week (10/31), the interim coach after a mid-season firing (the built FIRED weight's
cell, ATS -11.6% on 391), big dogs late (11/11 S8), annual-opponent November totals (11/12 s12).
  1. BOWL ELIGIBILITY: a team that needs ONE more win for six, in its last two regular-season games (its schedule
     length is known in August - no look-ahead): its moneyline and its spread, by price, by who it plays (a team
     already in / a team with nothing to play for), and the last game alone ('win and in').
  2. NOTHING TO PLAY FOR: a team that can no longer reach six wins, in November - the string.
  3. THE SCHEDULE-STRENGTH MISMATCH (the conference-strength question without a conference table): each team's
     opponents so far, by the engine's own ratings at kickoff (walk-forward); the battle-tested team (opponents 75+ /
     125+ Elo points tougher) against the team with the padded record, both 5+ games in.
Usage: python results/studies/deep_1112/b4_ncaaf_november.py > results/studies/deep_1112/b4_ncaaf_november.out"""
import json, os, sys
from collections import defaultdict
import dlib as D
import lib as L

os.chdir(D.ROOT)
sys.path.insert(0, D.ROOT)
import sports_data as sd       # noqa: E402
import sports_model as sm      # noqa: E402
import sports_players as sp    # noqa: E402

games = sd.load_games("ncaaf")
T = [g for g in L.table("ncaaf") if L.reg(g)]
# every team's regular-season schedule length (known before the season) and each game's place in it
sched = defaultdict(list)
for g in sd.load_games("ncaaf").values():
    if (g.get("stype") or "") == "2" and g.get("start"):
        s = L.season(g["start"], "ncaaf")
        for t in (g["home"], g["away"]):
            sched[(s, t)].append(g["start"])
for k in sched:
    sched[k].sort()
# the ratings at kickoff, walk-forward
p0 = json.load(open("data/sports/model.json"))["params"]["ncaaf"]
elo = sm.Elo(p0["k"], p0["hfa"], "ncaaf")
RAT = {}
for g in sm.finals(games, "ncaaf"):
    t = sm._ts(g["start"])
    RAT[g["id"]] = (elo.rating(g["home"], t), elo.rating(g["away"], t))
    elo.update(g)
opp_r = defaultdict(list)          # (season, team) -> ratings of the opponents it has played
rows = []
for g in T:
    fbs = sp.fbs_set(games, g["start"])
    both = fbs is not None and g["home"] in fbs and g["away"] in fbs
    rec = {"g": g, "fbs": both}
    for side, t, o in (("H", g["home"], g["away"]), ("A", g["away"], g["home"])):
        k = (g["season"], t)
        sc = sched[k]
        left = len([x for x in sc if x >= g["start"]])            # games left counting this one
        w = g[side].get("w", 0) if g[side]["n"] else 0
        n = g[side]["n"]
        orr = opp_r[k]
        rec[side] = {"w": w, "n": n, "left": left, "sos": (sum(orr) / len(orr)) if len(orr) >= 5 else None,
                     "need1": w == 5 and left <= 2, "last": left == 1, "in": w >= 6, "dead": w + left < 6}
    rows.append(rec)
    if g["id"] in RAT:
        opp_r[(g["season"], g["home"])].append(RAT[g["id"]][1])
        opp_r[(g["season"], g["away"])].append(RAT[g["id"]][0])
F = [r for r in rows if r["fbs"]]
print(f"FBS-vs-FBS regular-season games with a close: {sum(1 for r in F if r['g']['mlh'])} of {len(F)}")


def cells(name, pick):
    """pick(r) -> list of sides ('H' / 'A') the cell holds in game r"""
    ml_all, ml_dog, ml_fav, ats_all, ats_dog, ats_fav, across = [], [], [], [], [], [], []
    for r in F:
        g = r["g"]
        for s in pick(r):
            o = L.odds(g, s)
            ats_all.append((g["season"], L.ats(g, s)))
            across.append((g["season"], L.ats(g, L.other(s))))
            sp_ = L.spread(g, s)
            if sp_ is not None:
                (ats_dog if sp_ > 0 else ats_fav).append((g["season"], L.ats(g, s)))
            if o is not None:
                ml_all.append((g["season"], L.ml(g, s)))
                if 100 <= o <= 350:
                    ml_dog.append((g["season"], L.ml(g, s)))
                elif -150 <= o <= -101:
                    ml_fav.append((g["season"], L.ml(g, s)))
    print(f" -- {name}")
    L.cell("   ATS, every one", ats_all)
    L.cell("   ATS as a dog", ats_dog)
    L.cell("   ATS as a favorite", ats_fav)
    L.cell("   the side ACROSS, ATS", across)
    L.cell("   moneyline dog +100..+350", ml_dog)
    L.cell("   moneyline favorite -150..-101", ml_fav)


oth = L.other
print("\n1. NEEDS ONE WIN FOR SIX (5 wins, in its last two regular-season games)")
cells("the 5-win team, last two games", lambda r: [s for s in "HA" if r[s]["need1"] and not r[oth(s)]["need1"]])
cells("the 5-win team, its LAST game (win and in)", lambda r: [s for s in "HA" if r[s]["need1"] and r[s]["last"] and not r[oth(s)]["need1"]])
cells("the 5-win team vs a team already bowl-eligible", lambda r: [s for s in "HA" if r[s]["need1"] and r[oth(s)]["in"]])
cells("the 5-win team vs a team that can't get to six", lambda r: [s for s in "HA" if r[s]["need1"] and r[oth(s)]["dead"]])
cells("the 5-win team AT HOME", lambda r: ["H"] if r["H"]["need1"] and not r["A"]["need1"] else [])
cells("the 5-win team ON THE ROAD", lambda r: ["A"] if r["A"]["need1"] and not r["H"]["need1"] else [])
print("\n2. NOTHING TO PLAY FOR (can't reach six wins any more), November on")
nov = lambda r: r["g"]["start"][5:7] in ("11", "12")      # noqa: E731
cells("the eliminated team vs a team still alive or in", lambda r: [s for s in "HA" if nov(r) and r[s]["dead"] and not r[oth(s)]["dead"]])
cells("the eliminated team AT HOME vs a team that needs the game (4-5 wins, alive)", lambda r: ["H"] if nov(r) and r["H"]["dead"] and not r["A"]["dead"] and not r["A"]["in"] else [])
print("\n3. THE SCHEDULE-STRENGTH MISMATCH (opponents so far, by rating; both 5+ games in)")
for cut in (75, 125):
    def tough(r, cut=cut):
        a, b = r["H"]["sos"], r["A"]["sos"]
        if a is None or b is None or abs(a - b) < cut:
            return []
        return ["H" if a > b else "A"]
    cells(f"the battle-tested team (its opponents {cut}+ points tougher)", tough)

    def tough_worse(r, cut=cut):
        s = tough(r)
        if not s:
            return []
        me, them = r[s[0]], r[oth(s[0])]
        return s if me["n"] and them["n"] and me["w"] / me["n"] < them["w"] / them["n"] else []
    cells(f"   ... with the WORSE record of the two (the padded record across) - {cut}+", tough_worse)
L.done()
