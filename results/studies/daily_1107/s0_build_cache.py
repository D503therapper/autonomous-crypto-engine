"""Builds the lib caches the 11/7 studies read (the paid football odds history, fair looks only; the game files)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
for lg in ("ncaaf", "nfl"):
    print(lg, len(lib.load_football(lg)), flush=True)
for lg in ("nba", "nhl", "ncaab", "ncaaf"):
    print(lg, len(lib.finals(lg)), flush=True)
