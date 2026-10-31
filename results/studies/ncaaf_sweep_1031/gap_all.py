"""10/31 college sweep: the 🔍 gap rule (the raw ratings read 15+ over the no-vig close, Elo backing the dog, +100..+350)
on EVERY priced college game in our feed 2020-26 (not only the games the paid odds history holds), split FBS / FCS.
Walk-forward: each season's params tuned on the 3 seasons before it (as the 10/30 build). Flat 1u at the close.
Also every college dog / slight favorite by FBS-ness, and the gap bands 10-15 / 15-20 / 20+."""
import json
import math
import os
import sys
from collections import defaultdict

REPO = sys.argv[1]
sys.path.insert(0, REPO)
os.chdir(REPO)
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402
import sports_players as sp  # noqa: E402

games = sd.load_games("ncaaf")
rows = []
for season in range(2020, 2027):
    lo, hi = f"{season}-07-01", f"{season + 1}-07-01"
    learn = {k: g for k, g in games.items() if f"{season - 3}-07-01" <= g.get("start", "") < lo}
    p = sm.tune(learn, "ncaaf")
    if not p or "w" not in p:
        print("no params", season)
        continue
    _, played = sm.replay(sm.finals(games, "ncaaf"), p["k"], p["hfa"], "ncaaf")
    for g, f, *_ in played:
        if not lo <= g["start"] < hi:
            continue
        try:
            hs, as_ = float(g["home_score"]), float(g["away_score"])
            ch, ca = int(float(g["ml_home"])), int(float(g["ml_away"]))
        except (KeyError, ValueError, TypeError):
            continue
        if hs == as_ or not ch or not ca:
            continue
        dec = lambda o: 1 + (o / 100 if o > 0 else 100 / -o)  # noqa: E731
        ih, ia = 1 / dec(ch), 1 / dec(ca)
        nv_h = ih / (ih + ia)
        own = sm.own_p(p, f)
        fbs = sp.fbs_set(games, g["start"])
        kind = None
        if fbs is not None:
            kind = sum(str(t) in {str(x) for x in fbs} for t in (g["home"], g["away"]))
        for side, sign in (("home", 1), ("away", -1)):
            o = ch if side == "home" else ca
            pr = own if side == "home" else 1 - own
            nv = nv_h if side == "home" else 1 - nv_h
            won = (hs > as_) == (side == "home")
            elo = f.get("elo_pts")
            rows.append({"season": season, "start": g["start"], "odds": o, "dec": dec(o), "own": pr, "nv": nv,
                         "won": won, "fbs": kind, "elo": None if elo is None else sign * elo,
                         "team": g[side + "_name"], "opp": g[("away" if side == "home" else "home") + "_name"]})
print("rows", len(rows), "feature keys sample:", sorted(played[0][1].keys())[:30] if played else None)
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gap_rows.json"), "w"))
