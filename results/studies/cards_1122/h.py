"""The dry run's rig: the games, the ratings, the picks, and a re-write of one posted leg off the injury lists it stored."""
import sys, json, copy, re, os, time
sys.path.insert(0, os.getcwd())
import sports_data as sd, sports_model as sm, sports, sports_breakdown, sports_breakdown_v24 as v24
import sports_card_check as cc
t0 = time.time()
games = sd.load_games()
model = json.load(open("data/sports/model.json"))
elo = sm.ratings(games, model)
picks = json.load(open("data/sports/picks.json"))
print("loaded", round(time.time() - t0, 1), file=sys.stderr)


def inj_of(leg, g):
    """the report the posted card stored (no network here)"""
    side = leg["side"]
    other = "away" if side == "home" else "home"

    def rows(lst):
        out = []
        for x in lst or []:
            m = re.match(r"(.+?) \((\w+)\)$", x)
            nm, pos = (m.group(1), m.group(2)) if m else (x, "")
            out.append((nm, pos, "Out"))
        return out
    return {leg["league"]: {g[side]: rows(leg.get("outs")), g[other]: rows(leg.get("opp_outs"))}}


def rewrite(leg, used=None):
    leg = copy.deepcopy(leg)
    g = games[leg["game_id"]]
    inj = inj_of(leg, g)
    leg["breakdown"] = sports_breakdown.breakdown(leg, games, elo, inj, used if used is not None else set())
    try:
        sports.card_extras(leg, g, inj)
    except Exception as e:
        print("extras err", e, file=sys.stderr)
    return leg


def show(leg, tag=""):
    print(f"--- {tag} {leg['team']} {leg.get('odds')} vs {leg['opp']} ({leg['league']})")
    print("WHY:", leg.get("why_line"))
    for x in leg.get("breakdown") or []:
        print("  ", x)


if __name__ == "__main__":
    want = sys.argv[1:]
    for p in picks:
        for l in p["legs"]:
            if l.get("team") in want and p["date"] >= "2026-11-20":
                show(l, "POSTED " + p["date"])
                show(rewrite(l), "REWRITE")
