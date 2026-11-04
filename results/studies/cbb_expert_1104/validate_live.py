"""Replay the live 11/4 EXPERT marks on one past college hoops slate: python validate_live.py 2026-02-21 - how many
sides each mark flagged (the star's 2nd game back, the road-cold dog, the long top-scorer absence, turmoil, shooting,
the upset winner, the good / bad facts), with examples, and the study table's own flags on the same day as a check."""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sports_data as sd
import sports
import sports_model

day = sys.argv[1] if len(sys.argv) > 1 else "2026-02-21"
games = sd.load_games()
d = sports.sd.decimal
cands = []
for gid, g in games.items():
    if g.get("league") != "ncaab" or not str(g.get("start", "")).startswith(day) or g.get("status") != "final":
        continue
    try:
        mh, ma = int(float(g["ml_home"])), int(float(g["ml_away"]))
    except (KeyError, TypeError, ValueError):
        continue
    for side, odds in (("home", mh), ("away", ma)):
        p = 1 / d(odds)
        for market in ("ml", "spread"):
            o = odds if market == "ml" else -110
            cands.append({"league": "ncaab", "market": market, "odds": o, "dec": d(o), "p": p, "side": side, "game_id": gid,
                          "start": g["start"], "reasons": [], "dog_ctx": {}, "edge_own": p * d(o) - 1, "team": g[side],
                          "opp": g["away" if side == "home" else "home"], "home": side == "home",
                          "neutral": str(g.get("neutral")) == "1"})
t = time.time()
sports._SCHED.clear()
elo = None
try:
    elo = sports_model.Elo(20, 75, "ncaab")
    for gid, g in sorted(games.items(), key=lambda kv: str(kv[1].get("start"))):
        if g.get("league") == "ncaab" and g.get("status") == "final" and str(g.get("start")) < day:
            elo.update(g)
except Exception as e:  # noqa: BLE001
    print("no Elo:", e)
sports.mark_ncaab_top_out(games, cands)
sports.mark_ncaab_star_back(games, cands)
sports.mark_ncaab_road_cold(games, cands)
sports.mark_ncaab_turmoil(games, cands)
sports.mark_ncaab_shooting(games, cands)
sports.mark_ncaab_upset_winner(games, cands, elo)
sports.mark_ncaab_facts(cands)
sports.weigh_favorites(cands)
sports.weigh_ncaab_star_back_fav(cands)
print(f"{day}: {len(cands)} sides ({len(cands)//4} priced games), marks in {time.time()-t:.1f}s")
ml = [c for c in cands if c["market"] == "ml"]
sp = [c for c in cands if c["market"] == "spread"]
nm = lambda c: games[c["game_id"]][c["side"] + "_name"]
print("star_back:", sum(1 for c in ml if c.get("star_back")), [(nm(c), c["odds"], c["star_back_who"], sports.dog_spots(c) if c["odds"] >= 100 else c.get("w_p")) for c in ml if c.get("star_back")][:5])
print("opp_star_back reasons:", [c["reasons"][-1] for c in ml if c.get("opp_star_back")][:1])
print("spread rank nudge:", {w: sum(1 for c in sp if sports.ncaab_star_back_spread_w(c) == w) for w in (-0.03, 0.0, 0.03)})
print("road_cm read:", sum(1 for c in ml if c.get("road_cm") is not None), "road-cold dogs:", sum(1 for c in ml if c.get("ncaab_road_cold")),
      [(nm(c), c["odds"], c["road_cm"], c["road_games"], sports.dog_spots(c)) for c in ml if c.get("ncaab_road_cold")][:5])
print("vs_road_cold reasons:", [c["reasons"][-1] for c in ml if c.get("vs_road_cold")][:1])
print("top_out:", sum(1 for c in ml if c.get("top_out")), "5+ games:", [(nm(c), c["odds"], c["top_out_who"], c["top_out_run"]) for c in ml if (c.get("top_out_run") or 0) >= 5][:4])
print("turmoil read:", sum(1 for c in ml if c.get("turmoil") is not None), "lost 1+:", sum(1 for c in ml if c.get("turmoil")),
      [(nm(c), c["turmoil_who"]) for c in ml if c.get("turmoil")][:3], "news:", sum(1 for c in ml if c.get("turmoil_news")))
print("shooting read:", sum(1 for c in ml if c.get("efg_gap") is not None), "cold:", sum(1 for c in ml if c.get("cold_shoot")),
      "hot deep:", sum(1 for c in ml if c.get("hot_deep")), [(nm(c), c["efg_gap"]) for c in ml if c.get("cold_shoot")][:3])
print("upset winners:", [(nm(c), c["odds"], c.get("upset_winner_over")) for c in ml if c.get("upset_winner")][:5])
dogs = [c for c in ml if c["odds"] >= 100]
print("dog facts:", "good+no bad", sum(1 for c in dogs if c.get("dog_good") and not c.get("dog_bad")),
      "2+ bad", sum(1 for c in dogs if len(c.get("dog_bad") or []) >= 2),
      [(nm(c), c["dog_good"], c["dog_bad"]) for c in dogs if c.get("dog_good") or len(c.get("dog_bad") or []) >= 2][:5])
import sports_leads as sl
from collections import Counter
tags = Counter(t for c in cands for t in (sl.tags(c, sports) if c["market"] == "ml" else sl.spread_tags(c, sports))
               if "2nd game back" in t or "road dog 6+" in t or "5+ games" in t or "cold-shooting" in t or "3P-hot" in t
               or "rotation men" in t or "upset winner" in t or "good fact" in t or "bad facts" in t or "top scorer out, Nov" in t)
print("tags:", dict(tags))
# the study table's flags on the same day (a cross-check of the live reads)
try:
    import lib
    rows = [x for x in lib.build() if x["start"].startswith(day) and x.get("ml")]
    print("STUDY on the day:", len(rows), "sides; back2", sum(1 for x in rows if x.get("back2")),
          "road-cold road dogs", sum(1 for x in rows if x["venue"] == "away" and x["ml"] >= 100 and x.get("road_cm") is not None and x["road_cm"] <= -6),
          "top_out 5+", sum(1 for x in rows if x.get("top_out") and (x.get("miss_run") or 0) >= 5),
          "cold_shoot", sum(1 for x in rows if x.get("efg5") is not None and x["efg5"] - x["efg_s"] <= -0.04))
    live_rc = {(c["game_id"], c["side"]) for c in ml if c.get("ncaab_road_cold")}
    study_rc = {(x["id"], x["side"]) for x in rows if x["venue"] == "away" and x["ml"] >= 100 and x.get("road_cm") is not None and x["road_cm"] <= -6 and x["road_w"] + x["road_l"] >= 3}
    print("road-cold agreement: live", len(live_rc), "study", len(study_rc), "both", len(live_rc & study_rc))
    live_sb = {(c["game_id"], c["side"]) for c in ml if c.get("star_back")}
    study_sb = {(x["id"], x["side"]) for x in rows if x.get("back2")}
    print("star-back agreement: live", len(live_sb), "study", len(study_sb), "both", len(live_sb & study_sb))
except Exception as e:  # noqa: BLE001
    print("study cross-check skipped:", e)
