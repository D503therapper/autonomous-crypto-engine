"""COLTS @ TEXANS (nfl:401873066, Thu 11/19 5:15 PM PT) THROUGH THE OLD AND THE NEW CODE.
The injury report = nflverse's week-11 final report (Out / Doubtful / Questionable, every NFL team); who starts = the
season's snap counts through week 10 (fetch.py's files) run through sports_starters.reduce - exactly what the live run
saves. The game is a Pacific 11/19 game, so the WEIGHT (OLINE_FROM 11/20) does not touch it live; "new" below sets the
date back a day to show what the same game reads under the rule.   Usage: python colts_texans.py > colts_texans.out"""
import csv
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import sports                     # noqa: E402
import sports_absences            # noqa: E402
import sports_data as sd          # noqa: E402
import sports_starters            # noqa: E402

DL = os.path.join(os.path.expanduser("~"), ".cache", "d503_oline1119", "dl")
GID = "nfl:401873066"
sports_starters.ON[0] = False
games = sd.load_games()
g = games[GID]
model = sports._load("model.json", {"params": {}, "log": []})
now = datetime(2026, 11, 19, 16, 0, tzinfo=timezone.utc)

inj = {}
for r in csv.DictReader(open(os.path.join(DL, "injuries_2026.csv"))):
    if r["week"] != "11" or not r["report_status"]:
        continue
    tid = sports_starters.ESPN_ID.get(r["team"])
    pos = {"T": "OT", "G": "G"}.get(r["position"], r["position"])
    inj.setdefault(tid, []).append((r["full_name"], pos, r["report_status"]))
injuries = {"nfl": inj}
for s in ("away", "home"):
    print(f"{g[s + '_name']} report: " + ", ".join(f"{p} {n} ({st})" for n, p, st in inj.get(g[s], [])))


def read(label):
    sports_absences._TEAM.clear() if False else None
    cands = [c for c in sports.candidates(games, model, now, None, injuries) if c["game_id"] == GID and c.get("market") == "ml"]
    print(f"\n--- {label}")
    for s in ("away", "home"):
        reg = sports_absences.regulars(None, "nfl", g[s], g["start"])
        print(f"  {g[s + '_name']}: banged-up count {sports.out_count(g, s, injuries)}"
              f" · starting linemen out {sports.ol_out(g, s, injuries)}"
              f" · starters out the box score can't show: {[(m[0], sports_starters.word(m[1])) for m in sports.starters_out(g, s, injuries)]}")
    for c in sorted(cands, key=lambda c: c["side"]):
        own = c["edge_own"] / c["dec"] + 1 / c["dec"] if c.get("edge_own") is not None else None   # (edge = p * dec - 1)
        print(f"  {c['team']:7s} {c.get('odds')}: read {100 * c['p']:.1f}%  own read {100 * own:.1f}%  no-vig market {100 * c['p_market']:.1f}%"
              f"  depth weight {c.get('depth_pts', 0)}  depth gap {c.get('depth_gap')}  OL gap {c.get('ol_gap')}")
        print(f"          reasons: {c.get('reasons')}")
    for s, name in (("away", g["away_name"]), ("home", g["home_name"])):
        print(f"  card, {name} who's out: {sports.card_outs(games, g, s, name, injuries)}")
        print(f"        holes: {sports.side_holes(g, s, injuries)[0]!r}")
        print(f"        {sports.injury_line(g, s, injuries)}")


# OLD: no snap counts on file, the weight off
sports_starters.PATH = os.path.join(tempfile.mkdtemp(), "none.json")
sports_starters._CACHE.clear()
sports.OLINE_FROM = None
read("BEFORE (the box score's regulars only)")

# NEW: the snap counts in, the rule dated so this game is under it
sports_starters.PATH = os.path.join(tempfile.mkdtemp(), "nfl_snaps.json")
sports_starters._CACHE.clear()
n = sports_starters.sync(now, get=lambda url: open(os.path.join(DL, "snap_counts_2026.csv")).read())
print(f"\nsnap counts read: {n} teams; the file is {os.path.getsize(sports_starters.PATH)} bytes")
for s in ("away", "home"):
    st = sports_starters.starters("nfl", g[s], g["start"])
    print(f"  {g[s + '_name']} starters the box score can't show ({len(st)}): "
          + ", ".join(f"{v[1]} {v[0]}" for v in sorted(st.values(), key=lambda v: (v[2], v[1]))))
sports.OLINE_FROM = "2026-11-19"
read("AFTER (the snap counts' starters seen; the 11/20 rule applied to this game to show it)")
sports.OLINE_FROM = "2026-11-20"
read("AFTER, as it runs LIVE tonight (the cards see the men; the weight starts with the 11/20 games)")
