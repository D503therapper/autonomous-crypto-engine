"""Re-render the FULL BREAKDOWN + one-liner of today's posted picks with the current writer (wording only - the picks,
units and prices never change). Run from the repo root: python results/refresh_cards_1027.py [YYYY-MM-DD]
(10/27, the owner: "I don't need to see the difference, just fix it.")"""
import sys
from datetime import datetime, timezone

import sports
import sports_data as sd
import sports_players as sp

day = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).astimezone(sports.PT).strftime("%Y-%m-%d")
picks = sports._load("picks.json", [])
model = sports._load("model.json", {"params": {}, "log": []})
games = sd.load_games()
sp.CACHE = sp.load()
n = 0
for p in picks:                      # force the rewrite on today's open cards (add_breakdowns skips the current version)
    if p.get("date") == day and p.get("status") == "open":
        for leg in p["legs"]:
            leg["bv"] = -1
            n += 1
sports.add_breakdowns(games, model, picks)
sports._save("picks.json", picks)
print(f"re-rendered {n} legs for {day}")
for p in picks:
    if p.get("date") == day and p.get("status") == "open":
        for leg in p["legs"]:
            print("=====", leg["team"], "vs", leg["opp"], leg["odds"])
            print("LINE:", leg.get("why_line"))
            for x in leg.get("breakdown") or []:
                print("  ", x)
