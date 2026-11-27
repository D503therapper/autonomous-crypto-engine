"""11/27 daily studies - one sample row of each file the studies read, and the coverage by season.
python results/studies/daily_1127/peek.py"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from core import teambox  # noqa: E402
import sports_data as sd  # noqa: E402


def main():
    for lg in ("nfl", "ncaaf", "nba", "ncaab", "nhl"):
        tb = teambox(lg)
        G = sd.load_games(lg)
        by = Counter()
        keyc = Counter()
        for gid, teams in tb.items():
            g = G.get(gid)
            if not g:
                continue
            s = lib.season(g["start"])
            by[s] += 1
            for b in teams.values():
                for k in ("leadChanges", "rushingYards", "sacksYardsLost", "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
                          "totalYards", "rushingAttempts", "completionAttempts"):
                    if b.get(k) not in (None, ""):
                        keyc[(s, k)] += 1
        gid = next(iter(tb))
        print(lg, "team box games by season:", sorted(by.items()))
        print("   keys by season:", sorted(keyc.items()))
        print("   sample:", list(tb[gid].items())[0])
        h1 = Counter()
        for g in G.values():
            if g.get("h1_spread_home") not in (None, "") and g.get("status") == "final":
                h1[lib.season(g["start"])] += 1
        print("   h1 spread by season:", sorted(h1.items()))
    for lg in ("nhl", "nfl"):
        bx = lib.box_rows(lg)
        gid = next(iter(bx))
        t = next(iter(bx[gid]))
        print(lg, "player rows:", bx[gid][t][:3])
    g = sd.load_games("ncaaf")
    dec = [x for x in g.values() if x.get("status") == "final" and x["start"][5:10] >= "11-29" and x["start"][5:10] <= "12-09"
           and str(x.get("neutral")) == "1"]
    print("college football neutral games Nov 29 - Dec 9:", len(dec), Counter(lib.season(x["start"]) for x in dec))
    for x in sorted(dec, key=lambda x: x["start"])[-14:]:
        print("  ", x["start"], x.get("away_name"), x.get("away_score"), "@", x.get("home_name"), x.get("home_score"), x.get("stype"),
              x.get("spread_home"), x.get("total"), x.get("city"))


if __name__ == "__main__":
    main()
