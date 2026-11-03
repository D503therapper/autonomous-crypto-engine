"""The live code on a real slate: the three marks (sports.mark_ncaab_ranked_road / mark_ncaab_ats_gap / mark_ncaab_reb)
run on every priced college hoops game of one day with the engine's own Elo replayed to that morning - how many sides
flag, how long it takes, and which ranked road teams it names (read against the final scores)."""
import json, os, sys, time
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports, sports_data as sd, sports_model as sm  # noqa: E402

DAY = sys.argv[1] if len(sys.argv) > 1 else "2025-11-20"
t0 = time.time()
games = sd.load_games("ncaab")
print("games", len(games), round(time.time() - t0, 1), "s")
p = json.load(open("data/sports/model.json"))["params"]["ncaab"]
elo, _ = sm.replay([g for g in sm.finals(games, "ncaab") if g["start"] < DAY], p["k"], p["hfa"])
day = [g for g in games.values() if str(g.get("start", "")).startswith(DAY) and g.get("ml_home")]
cands = []
for g in day:
    for side in ("home", "away"):
        for m in ("ml", "spread"):
            cands.append({"league": "ncaab", "market": m, "odds": int(float(g[f"ml_{side}"])) if m == "ml" else -110,
                          "side": side, "game_id": g["id"], "start": g["start"], "reasons": [], "dog_ctx": {}})
t1 = time.time()
sports.mark_ncaab_ranked_road(games, cands, elo)
sports.mark_ncaab_ats_gap(games, cands)
sports.mark_ncaab_reb(games, cands)
print("marks took", round(time.time() - t1, 1), "s on", len(cands), "sides of", len(day), "priced games")
c = Counter()
for x in cands:
    for k in ("ranked_road", "vs_ranked_road"):
        c[k] += bool(x.get(k))
    c["ats_gap known"] += x.get("ats_gap") is not None
    c["ats_gap 3+"] += (x.get("ats_gap") or 0) >= 3
    c["reb_gap known"] += x.get("reb_gap") is not None
    c["reb_gap 6+"] += (x.get("reb_gap") or 0) >= 6
print(dict(c))
for x in cands:
    if x.get("ranked_road") and x["market"] == "ml":
        g = games[x["game_id"]]
        print(f"  ranked road: {g['away_name']} @ {g['home_name']} {x['odds']:+d}  final {g['away_score']}-{g['home_score']}")
