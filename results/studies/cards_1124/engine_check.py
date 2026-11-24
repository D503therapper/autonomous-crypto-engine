"""Victor's question, 11/24 (a fact check of the ENGINE, not the card): why did the dog read like Illinois St (3-4) over
Tulsa? Prints both teams' efficiency ratings (this season's solve and the preseason prior), every game with the
opponent's rating, the schedule strength, and what the read says with the prior taken out. No network.
    python results/studies/cards_1124/engine_check.py [game id]"""
import os
import sys

sys.path.insert(0, os.getcwd())
import sports_data as sd
import sports_cbb_eff as ce

gid = sys.argv[1] if len(sys.argv) > 1 else "ncaab:401921666"
games = sd.load_games()
g = games[gid]
print({k: g.get(k) for k in ("home", "away", "home_name", "away_name", "neutral", "start", "home_score", "away_score")})
f = ce.ratings(games, g["start"])
prev, po, pd, pt = f["prior"]
names = {}
for x in games.values():
    if x.get("league") == "ncaab":
        names[str(x.get("home"))] = x.get("home_name")
        names[str(x.get("away"))] = x.get("away_name")
print("mu", round(f["mu"], 1), "hfa", round(f["hfa"], 2), "T0", round(f["T0"], 1))
allnet = sorted(((f["O"][t] + f["D"][t]) for t in f["O"] if f["n"].get(t, 0) >= 3), reverse=True)


def rank(v):
    return sum(1 for a in allnet if a > v) + 1


s = ce.season_of(g["start"])
for t in (str(g["home"]), str(g["away"])):
    o, d, tt = ce._team(f, t)
    print("%s: O %+.1f D %+.1f net %+.1f tempo %+.1f rank %d of %d | prior O %+.1f D %+.1f net %+.1f | games %s" % (
        names[t], o, d, o + d, tt, rank(o + d), len(allnet), po.get(t, 0), pd.get(t, 0), po.get(t, 0) + pd.get(t, 0), f["n"].get(t)))
    rows = sorted([x for x in games.values() if x.get("league") == "ncaab" and t in (str(x.get("home")), str(x.get("away")))
                   and x.get("home_score") not in (None, "") and str(x.get("start", ""))[:4].isdigit()
                   and ce.season_of(x["start"]) == s and x["start"] < g["start"]], key=lambda x: x["start"])
    nets = []
    for x in rows:
        home = str(x["home"]) == t
        o_ = str(x["away"] if home else x["home"])
        pf, pa = (x["home_score"], x["away_score"]) if home else (x["away_score"], x["home_score"])
        n_ = rk = None
        if o_ in f["O"] and f["n"].get(o_, 0) >= 3:
            n_ = f["O"][o_] + f["D"][o_]
            nets.append(n_)
            rk = rank(n_)
        where = "N" if str(x.get("neutral")) == "1" else ("H" if home else "A")
        print("   ", x["start"][:10], where, names.get(o_), pf, "-", pa, "| opp net", None if n_ is None else round(n_, 1), "rank", rk)
    print("    D1 opponents' average net rating:", round(sum(nets) / len(nets), 1) if nets else None, "over", len(nets))
print("the read:", ce.predict(games, g))
