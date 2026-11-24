"""The test fixture rows for one posted card, off the real files (the _Fx1122 format in sports_test.py): both teams'
games this season with both box lines, their opponents' other games (scores only - the schedule lines count them) and
the ratings of every team named.  python results/studies/cards_1124/fixture.py "Illinois St" 2026-11-24"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "cards_1122"))
from h import games, picks, elo                             # noqa: E402
import sports_card_sell as cs                               # noqa: E402

KEYS = ("fieldGoalsMade-fieldGoalsAttempted", "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
        "freeThrowsMade-freeThrowsAttempted", "totalRebounds", "offensiveRebounds", "totalTurnovers", "pointsInPaint",
        "fastBreakPoints", "assists", "steals", "blocks")
want, day = sys.argv[1], sys.argv[2]
leg = next(l for p in picks if p["date"] == day for l in p["legs"] if l.get("team") == want)
g0 = games[leg["game_id"]]
lg = leg["league"]
box = cs.load(lg)
two = {str(g0["home"]), str(g0["away"])}
mine = [g for g in games.values() if g.get("league") == lg and g.get("status") == "final" and "2026-10-15" < g["start"] < g0["start"]
        and two & {str(g["home"]), str(g["away"])}]
opps = {str(t) for g in mine for t in (g["home"], g["away"])} - two
rest = [g for g in games.values() if g.get("league") == lg and g.get("status") == "final" and "2026-10-15" < g["start"] < g0["start"]
        and opps & {str(g["home"]), str(g["away"])} and g not in mine]
ids = set()
for g in sorted(mine + rest, key=lambda x: x["start"]):
    b = box.get(g["id"]) or {}
    ba = bh = ""
    if g in mine and len(b) == 2:
        row = lambda t: " ".join(str(b[str(t)].get(k, 0)) for k in KEYS)   # noqa: E731
        ba, bh = row(g["away"]), row(g["home"])
    ids |= {str(g["home"]), str(g["away"])}
    print('    "' + "|".join([g["start"][:16], str(g["away"]), g["away_name"], str(g["away_score"]), str(g["home"]), g["home_name"],
                              str(g["home_score"]), str(g.get("neutral") or "0"), ba, bh]) + '",')
e = elo[lg]
print(json.dumps({t: round(e.r.get(t, 1500.0)) for t in sorted(ids)}))
print("pre:", {k: g0.get(k) for k in ("id", "start", "home", "away", "home_name", "away_name", "neutral")})
