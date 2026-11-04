"""Replay the live KNOWLEDGE (A) marks on one past college hoops slate: python validate_live.py 2026-02-21 - prints
how many sides each mark flagged, with examples (the coach, the long absence, the race, the identity, the roster mix)."""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
import sports_data as sd
import sports

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
                          "opp": g["away" if side == "home" else "home"]})
t = time.time()
sports._SCHED.clear()
sports.mark_ncaab_coach(games, cands)
sports.mark_ncaab_long_out(games, cands)
sports.mark_ncaab_race(games, cands)
sports.mark_ncaab_identity(games, cands)
sports.mark_ncaab_roster_mix(games, cands)
sports.weigh_favorites(cands)
sports.weigh_ncaab_new_coach_fav(games, cands)
sports.weigh_ncaab_to_fav(cands)
print(f"{day}: {len(cands)} sides ({len(cands)//4} priced games), marks in {time.time()-t:.1f}s")
ml = [c for c in cands if c["market"] == "ml"]
sp = [c for c in cands if c["market"] == "spread"]
nm = lambda c: games[c["game_id"]][c["side"] + "_name"]
print("coach on file:", sum(1 for c in ml if c.get("coach_name")), "new coach:", sum(1 for c in ml if c.get("ncaab_new_coach")),
      "new-coach small fav weighed:", [(nm(c), c["odds"], c.get("w_p")) for c in ml if c.get("ncaab_new_coach_fav")][:5])
print("long_out:", sum(1 for c in ml if c.get("long_out")), [(nm(c), c["long_out_who"]) for c in ml if c.get("long_out")][:4])
print("race_dog:", sum(1 for c in ml if c.get("race_dog")), [(nm(c), c["odds"], c["conf_gb"], c["opp_conf_gb"]) for c in ml if c.get("race_dog")][:6])
print("vs_race_dog reasons:", [c["reasons"][-1] for c in ml if c.get("vs_race_dog")][:2])
print("identity read:", sum(1 for c in ml if c.get("to_margin") is not None), "to-prone small favs weighed:",
      [(nm(c), c["odds"], c["to_margin"], c.get("w_p")) for c in ml if c.get("ncaab_to_fav")][:5],
      "offense-first:", sum(1 for c in ml if c.get("off_first")))
print("roster mix read:", sum(1 for c in sp if c.get("roster_tin") is not None),
      "rank weights:", {w: sum(1 for c in sp if sports.ncaab_roster_spread_w(c) == w) for w in (-0.02, 0.0, 0.02)},
      [(nm(c), c["roster_tin"], c["roster_new"]) for c in sp if sports.ncaab_roster_spread_w(c) < 0][:3])
print("dog_spots on the race dogs:", [(nm(c), sports.dog_spots(c)) for c in ml if c.get("race_dog")][:4])
import sports_leads as sl
from collections import Counter
tags = Counter(t for c in cands for t in (sl.tags(c, sports) if c["market"] == "ml" else sl.spread_tags(c, sports)) if "KNOWLEDGE" in t or "first-year" in t or "regular out" in t or "contender" in t or "offense-first" in t or "turnover" in t or "transfer-heavy" in t or "freshman-heavy" in t)
print("tags:", dict(tags))
