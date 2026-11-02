"""S8 - THE BUILT ⛰️ ALTITUDE OVER (sports_early.alt_overs, the live code) replayed on 2023-24 .. 2025-26: every night
at 7 PM PT, tomorrow's college hoops games are 'pre' (their totals = ESPN's close - the study's price; live it's the
night-before number), the finals before then are the season so far. Checks the live code fires on the study's games
at the study's rate and grades them the same way."""
import os
import sys
from datetime import datetime, timedelta, timezone

import lib

sys.path.insert(0, lib.ROOT)
os.chdir(lib.ROOT)
import sports_data as sd      # noqa: E402
import sports_early as se     # noqa: E402

out = lib.Out("s8_alt_replay", train=(), held=(2023, 2024, 2025))
G = sd.load_games("ncaab")
bets = []
for season in (2023, 2024, 2025):
    d = datetime(season, 11, 3, 3, 0, tzinfo=timezone.utc)
    end = datetime(season + 1, 4, 10, tzinfo=timezone.utc)
    while d < end:
        nxt = {k: g for k, g in G.items() if g.get("status") == "final" and d < se._t(g["start"]) <= d + timedelta(hours=40)}
        view = {k: (dict(g, status="pre") if k in nxt else g) for k, g in G.items()
                if k in nxt or se._t(g["start"]) < d}
        for c in se.alt_overs(view, {"picks": []}, d):
            g = G[c["game_id"]]
            pts = float(g["home_score"]) + float(g["away_score"])
            bets.append((season, lib.ats_pl(pts - c["line"], c["odds"]), c["game_id"]))
        d += timedelta(days=1)
seen, uniq = set(), []
for s, p, gid in bets:
    if gid not in seen:
        seen.add(gid)
        uniq.append((s, p))
out.bets("the live alt_overs code, night-before view at the close total", uniq)
out.save()
