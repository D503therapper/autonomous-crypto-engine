"""11/27 daily studies - the Chiefs @ Bills game file, the two teams' meetings, the price tape.
python results/studies/daily_1127/yday2.py"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_data as sd  # noqa: E402
import sports  # noqa: E402
import sports_breakdown_v24 as v24  # noqa: E402

GID = "nfl:401873082"


def main():
    games = sd.load_games("nfl")
    g = games.get(GID) or games.get(GID.split(":")[1])
    print(json.dumps({k: v for k, v in g.items() if not isinstance(v, (dict, list))}, indent=0)[:3000])
    pair = {g["home"], g["away"]}
    for x in sorted(games.values(), key=lambda x: x.get("start") or ""):
        if {x.get("home"), x.get("away")} == pair:
            print(x.get("start"), x.get("away_name"), x.get("away_score"), "@", x.get("home_name"), x.get("home_score"),
                  x.get("status"), "stype", x.get("stype"))
    print("REVENGE_DAYS", v24.REVENGE_DAYS, "stale_revenge:", sports.stale_revenge(games, g))
    for t, nm in ((g["home"], g["home_name"]), (g["away"], g["away_name"])):
        print("--", nm)
        for x in sorted(games.values(), key=lambda x: x.get("start") or ""):
            if (x.get("start") or "") >= "2026-09-01" and t in (x.get("home"), x.get("away")) and x.get("status") == "final":
                print("  ", x["start"][:10], x.get("away_name"), x.get("away_score"), "@", x.get("home_name"),
                      x.get("home_score"), "ml", x.get("ml_away"), x.get("ml_home"), "sp", x.get("spread_home"))


if __name__ == "__main__":
    main()
