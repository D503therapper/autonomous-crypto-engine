"""THE LEAD TRACKER (data/sports/lead_tracker.json, read only; graded on the game files the way sports_leads.grade
does - in the engine's band only, sports_leads.counts). Every tag at 75+ graded rows: W-L, units at 1u, ROI, the z of
the wins vs the price, by league and by month, and what changed since the 11/10 read (rows logged 11/8 on)."""
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sports_data as sd  # noqa: E402
import sports_leads as sl  # noqa: E402

out = []


def say(s=""):
    print(s)
    out.append(s)


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


games = {}
for lg in ("nfl", "ncaaf", "nhl", "nba", "ncaab", "mlb"):
    games.update(sd.load_games(lg))
by = defaultdict(list)
for r in sl.load():
    g = games.get(r["game_id"]) or {}
    if g.get("status") != "final":
        continue
    try:
        hs, as_ = float(g["home_score"]), float(g["away_score"])
    except (KeyError, TypeError, ValueError):
        continue
    if r.get("market") == "spread":
        try:
            m = (hs - as_ if r["side"] == "home" else as_ - hs) + float(r["line"])
        except (KeyError, TypeError, ValueError):
            continue
        if m == 0:
            continue
        won, o = m > 0, -110
    elif hs == as_:
        continue
    else:
        won, o = (hs > as_) == (r["side"] == "home"), r.get("odds") or 100
    for t in r["tags"]:
        if sl.counts(t, r.get("odds")):
            by[t].append(dict(day=r["day"], lg=r.get("league"), o=o, won=won))


def line(name, rs):
    if not rs:
        return
    w = sum(r["won"] for r in rs)
    pr = sum((dec(r["o"]) - 1) if r["won"] else -1 for r in rs)
    bev = sum(1 / dec(r["o"]) for r in rs)
    var = sum((1 / dec(r["o"])) * (1 - 1 / dec(r["o"])) for r in rs)
    z = (w - bev) / math.sqrt(var) if var else 0
    say(f"  {name:52s} {w:4d}-{len(rs)-w:<4d} {pr:+7.1f}u {pr/len(rs)*100:+6.1f}% on {len(rs):4d}  z {z:+.2f}")


for t, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
    if len(rs) < 75:
        continue
    say(t)
    line("ALL", rs)
    line("since the 11/10 read (logged 11/10 on)", [r for r in rs if r["day"] >= "2026-11-10"])
    for lg in sorted({r["lg"] for r in rs}):
        line(f"league {lg}", [r for r in rs if r["lg"] == lg])
    for mth in sorted({r["day"][:7] for r in rs}):
        line(f"month {mth}", [r for r in rs if r["day"][:7] == mth])
    line("dogs", [r for r in rs if r["o"] > 0])
    line("favorites", [r for r in rs if r["o"] < 0])
    say()
say(f"tags with 50-74 graded rows: " + "; ".join(f"{t} {len(rs)}" for t, rs in sorted(by.items(), key=lambda kv: -len(kv[1]))
                                                 if 50 <= len(rs) < 75))
open(os.path.join(HERE, "lead_tracker_out.txt"), "w").write("\n".join(out) + "\n")
