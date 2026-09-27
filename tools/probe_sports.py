"""Time each step of one live check (where does the watcher hang?)."""
import sys
import time

sys.path.insert(0, ".")
t0 = time.time()
import sports_data as sd  # noqa: E402
import sports_live as sl  # noqa: E402
import sports_model as sm  # noqa: E402
import sports_players as sp  # noqa: E402

t = time.time(); games = sd.load_games(); print(f"load games: {len(games)} in {time.time() - t:.1f}s", flush=True)
t = time.time(); sp.CACHE = sp.load(); print(f"load players: {time.time() - t:.1f}s", flush=True)
t = time.time(); sm.KEY_EDGE = sp.key_edges(games, sp.CACHE); print(f"key edges: {time.time() - t:.1f}s", flush=True)
t = time.time(); sl._DATA.clear(); sl._data(); print(f"_data(): {time.time() - t:.1f}s", flush=True)
t = time.time(); plays = sl.run(); print(f"run(): {time.time() - t:.1f}s, {len(plays)} plays", flush=True)
t = time.time(); plays = sl.run(); print(f"second run(): {time.time() - t:.1f}s", flush=True)
print(f"total {time.time() - t0:.1f}s")
