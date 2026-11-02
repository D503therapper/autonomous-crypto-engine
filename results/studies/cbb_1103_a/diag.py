"""Readiness diag: why each college hoops game on the 11/3 slate is in / out of sports.candidates."""
import os, sys, collections
from datetime import datetime, timezone, date
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
import sports, sports_data as sd, sports_model as sm
games = sd.load_games()
day = date(2026, 11, 3)
at = datetime(2026, 11, 3, 8, 35, tzinfo=sports.PT).astimezone(timezone.utc)
model = sports._load("model.json", {"params": {}, "log": []})
elo = sm.ratings(games, model)
why = collections.Counter(); ex = collections.defaultdict(list)
for g in games.values():
    if g["league"] != "ncaab": continue
    st = datetime.strptime(g["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    if st.astimezone(sports.PT).date() != day: continue
    r = []
    if g["status"] != "pre": r.append("status " + g["status"])
    if g.get("ml_home", "") == "": r.append("no ml")
    if (g.get("stype") or "?") not in sd.REAL: r.append("stype " + str(g.get("stype")))
    if g.get("tbd") == "1": r.append("tbd")
    if sd.exhibition(g): r.append("exhibition")
    f = elo["ncaab"].features(g)
    if f["known"] < sports.MIN_KNOWN: r.append(f"known {f['known']}")
    k = ";".join(r) or "IN"
    why[k] += 1; ex[k].append(f"{g['away_name']} @ {g['home_name']} {g.get('ml_home')}/{g.get('ml_away')} known={f['known']} elo_pts={f.get('elo_pts')}")
for k, n in why.most_common():
    print(n, k); [print("   ", e) for e in ex[k][:4]]
print("MIN_KNOWN", sports.MIN_KNOWN, "REAL", sd.REAL)
