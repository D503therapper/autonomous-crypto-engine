"""11/27 daily studies - the Chiefs @ Bills box (team + passers) and the season-line check on the card's "leaking 21".
python results/studies/daily_1127/yday4.py"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_data as sd  # noqa: E402
import sports_roster as sr  # noqa: E402
import sports_breakdown_v24 as v24  # noqa: E402

GID = "nfl:401873082"


def main():
    for r in sr.team_rows("nfl"):
        if r["gid"] == GID:
            for t, b in r["teams"].items():
                print(t, b)
    try:
        import csv
        import gzip
        with gzip.open(os.path.join(sd.DATA, "roster", "nfl_2026.csv.gz"), "rt") as f:
            for row in csv.DictReader(f):
                if row["gid"] == GID and row["group"] in ("passing", "rushing"):
                    print(row["team"], row["player"], row["group"], row["stats"])
    except OSError as e:
        print("no player box", e)
    games = sd.load_games("nfl")
    for tid, nm in (("2", "Bills"), ("12", "Chiefs")):
        gs = sorted((g for g in games.values() if g.get("status") == "final" and tid in (g.get("home"), g.get("away"))
                     and "2026-09-01" <= g["start"] < "2026-11-27T00:00Z" and str(g.get("stype") or "2") == "2"), key=lambda g: g["start"])
        print(nm, "season (scored, allowed):", v24._per_game(gs, tid), "last 3:", v24._per_game(gs[-3:], tid),
              "| allowed line still true:", v24.season_still(gs, tid, 1, "nfl"), "| scored:", v24.season_still(gs, tid, 0, "nfl"))


if __name__ == "__main__":
    main()
