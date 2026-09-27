"""Where does one live check hang? Time each piece; dump every thread's stack if it takes over 90 seconds."""
import faulthandler
import json
import os
import sys
import time

sys.path.insert(0, ".")
faulthandler.dump_traceback_later(90, exit=True)
import sports_data as sd  # noqa: E402
import sports_live as sl  # noqa: E402
import sports_model as sm  # noqa: E402

games, model = sl._data()
t = time.time(); elo = sm.ratings(games, model); print(f"ratings: {time.time() - t:.1f}s", flush=True)
for lg in sd.LEAGUES:
    t = time.time(); a = sl.fetch_live(lg); print(f"fetch_live {lg}: {len(a)} in {time.time() - t:.1f}s", flush=True)
t = time.time(); b = sl.bovada_live("nfl"); print(f"bovada nfl: {len(b)} in {time.time() - t:.1f}s {sl.BOOKS}", flush=True)
t = time.time(); s = sl.espn_scores("nfl"); print(f"espn scores nfl: {len(s)} in {time.time() - t:.1f}s", flush=True)
t = time.time(); log = {"plays": {}}; plays = sl.cycle(games, model, log); print(f"cycle: {time.time() - t:.1f}s {len(plays)} plays", flush=True)
