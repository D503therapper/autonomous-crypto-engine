"""11/27 daily studies - what the paid football history's games hold (how many fair spread / moneyline looks a game).
python results/studies/daily_1127/peek2.py"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402


def main():
    for lg in ("nfl", "ncaaf"):
        games = lib.load_football(lg)
        c = Counter()
        for g in games:
            c["games"] += 1
            c["sp looks"] += bool(g["sp"])
            c["ml looks"] += bool(g["ml"])
            c["first fair sp"] += bool(lib.first_fair(g["sp"]))
            c["last look sp"] += bool(lib.last_look(g["sp"]))
            c["both sp"] += bool(lib.first_fair(g["sp"]) and lib.last_look(g["sp"]))
            c["c_sp"] += g["c_sp"] is not None
            c["neutral"] += g["neutral"]
        print(lg, dict(c))
        g = games[len(games) // 2]
        print("  sample:", {k: (v if not isinstance(v, list) else [(round(d, 2), len(b)) for d, b in v][:12]) for k, v in g.items()})


if __name__ == "__main__":
    main()
