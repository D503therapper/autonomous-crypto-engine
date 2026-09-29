"""Backstop for the live watcher: prints "yes" when a game is live or starts within 2 hours (the hourly engine run
then starts a watch if none is running - GitHub's own 30-minute schedule skips runs, and once left MNF unwatched)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd       # noqa: E402
import sports_live as sl       # noqa: E402

print("yes" if sl.any_live_soon(sd.load_games(), sl.STAY_MIN) else "no")
