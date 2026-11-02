"""Readiness: the college hoops SPREAD sides on a day's slate - their cover read (sm.cover_p, NOT pulled to the market by
early_trust the way the moneyline read is) and which would make the lean pool (viewer_leans' ok()).
Usage: python spreads.py YYYY-MM-DD"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
import sports                   # noqa: E402
import sports_data as sd        # noqa: E402
import sports_model as sm       # noqa: E402
import sports_players as sp     # noqa: E402

day = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
games = sd.load_games()
ids = {}
for g in games.values():
    for s in ("home", "away"):
        ids.setdefault(g["league"], set()).add(g[s])
inj = {lg: {t: [] for t in ids.get(lg, ())} for lg in sd.LEAGUES}
model = sports._load("model.json", {"params": {}, "log": []})
sp.CACHE = sp.load()
sm.KEY_EDGE = sp.key_edges(games, sp.CACHE)
sports.load_states(games)
now = datetime(day.year, day.month, day.day, 8, 35, tzinfo=sports.PT).astimezone(timezone.utc)
cands = [c for c in sports.candidates(games, model, now, day, inj) if c["league"] == "ncaab"]
spr = [c for c in cands if c["market"] == "spread"]
leans = sports.viewer_leans(cands, set())
print(f"{len(spr)} college hoops spread sides; cover read >= 0.55: {sum(c['p'] >= 0.55 for c in spr)}, >= 0.60: {sum(c['p'] >= 0.60 for c in spr)}")
for c in sorted(spr, key=lambda c: -c["p"])[:15]:
    g = games[c["game_id"]]
    print(f"  {c['team']:18} {c['line']:+6.1f} ({c['odds']:+}) p {c['p']:.3f} home={c['home']} neutral={g.get('neutral')} rank {sports.lean_rank(c):.3f}")
print("viewer_leans (college hoops only, no avoid):")
for c in leans:
    print(f"  {c['market']:6} {c['team']:18} {c.get('line')} ({c['odds']:+}) p {c['p']:.3f} home={c['home']}")
