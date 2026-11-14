"""11/14 daily studies - compact feature tables from the saved box scores (streamed, never the whole file in memory).
nhl_skaters.pkl: {gid: {team: [(pid, toi minutes, group, points)]}}  (data/sports/roster/nhl_*.csv.gz, 2021-26)
nhl_goalies.pkl: {gid: {team: goalie name}}  (data/sports/players/nhl.csv - the goalie who faced the most shots, 2016-26)
nba_team.pkl:    {gid: {team: {fga, tpa, fta, pts, oreb, tov, min5}}}  (data/sports/roster/nba_*.csv.gz, 2016-26)
Every value is the game's own box - the studies read only games BEFORE the one being bet (no look-ahead), except S1-S3's
"who dressed tonight" (the lineup is known at puck drop - the injury report / morning skate carries it)."""
import csv
import gzip
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402  (chdir to the repo root)

D = os.path.join("data", "sports", "roster")


def toi(s):
    try:
        m, sec = str(s).split(":")
        return int(m) + int(sec) / 60
    except (ValueError, AttributeError):
        return None


def pair(s):
    try:
        a, b = str(s).split("-")[:2]
        return float(a), float(b)
    except (ValueError, AttributeError):
        return None


def nhl():
    out = {}
    for fn in sorted(os.listdir(D)):
        if not (fn.startswith("nhl_") and fn.endswith(".csv.gz")):
            continue
        with gzip.open(os.path.join(D, fn), "rt") as f:
            for r in csv.DictReader(f):
                if r["group"] == "goalies":
                    continue
                try:
                    st = json.loads(r["stats"] or "{}")
                except ValueError:
                    continue
                t = toi(st.get("timeOnIce"))
                if t is None:
                    continue
                pts = (lib.num(st.get("goals")) or 0) + (lib.num(st.get("assists")) or 0)
                out.setdefault(r["gid"], {}).setdefault(r["team"], []).append((r["pid"], t, r["group"], pts))
    pickle.dump(out, open(os.path.join(lib.CACHE, "nhl_skaters.pkl"), "wb"))
    print("nhl skater games", len(out))
    g = {}
    with open(os.path.join("data", "sports", "players", "nhl.csv")) as f:
        for r in csv.DictReader(f):
            if r["role"] == "G":
                g.setdefault(r["gid"], {})[r["team"]] = r["player"]
    pickle.dump(g, open(os.path.join(lib.CACHE, "nhl_goalies.pkl"), "wb"))
    print("nhl goalie games", len(g))


def nba():
    out = {}
    for fn in sorted(os.listdir(D)):
        if not (fn.startswith("nba_") and fn.endswith(".csv.gz")):
            continue
        with gzip.open(os.path.join(D, fn), "rt") as f:
            for r in csv.DictReader(f):
                try:
                    st = json.loads(r["stats"] or "{}")
                except ValueError:
                    continue
                fg = pair(st.get("fieldGoalsMade-fieldGoalsAttempted"))
                tp = pair(st.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
                ft = pair(st.get("freeThrowsMade-freeThrowsAttempted"))
                if fg is None:
                    continue
                d = out.setdefault(r["gid"], {}).setdefault(r["team"], {"fga": 0, "tpa": 0, "tpm": 0, "fta": 0,
                                                                         "pts": 0, "oreb": 0, "tov": 0})
                d["fga"] += fg[1]
                d["tpa"] += tp[1] if tp else 0
                d["tpm"] += tp[0] if tp else 0
                d["fta"] += ft[1] if ft else 0
                d["pts"] += lib.num(st.get("points")) or 0
                d["oreb"] += lib.num(st.get("offensiveRebounds")) or 0
                d["tov"] += lib.num(st.get("turnovers")) or 0
    pickle.dump(out, open(os.path.join(lib.CACHE, "nba_team.pkl"), "wb"))
    print("nba team games", len(out))


if __name__ == "__main__":
    nhl()
    nba()
