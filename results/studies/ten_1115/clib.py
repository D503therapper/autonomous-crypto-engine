"""11/15 ten studies - college hoops helpers: the 11/13 lean funnel's replay rows (the board re-built at ESPN's close
every college hoops day 2018-26 - results/studies/leans_1113/funnel4.py; the college hoops unit paths) through the
11/14 loaders (cbb_profit_1114/lib.py + recon.py: the dog slot rebuilt) + each team's LAST game from the game table
(when, where - home / road / neutral - and who), all known before the tip. TRAIN 2018-22 / HELD OUT 2023-26."""
import os
import sys
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "cbb_profit_1114"))
import lib as L  # noqa: E402
import recon  # noqa: E402
import tlib  # noqa: E402


def _t(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


def prev_table():
    """{(gid, 'home'|'away'): {gap_h, where (home/road/neutral of the LAST game), opp, n_road (straight games away
    from home before tonight), last2_gap_h}}"""
    G = sorted(tlib.build(), key=lambda g: g["start"])
    log = defaultdict(list)       # team -> [(start, where, opp, season)]
    out = {}
    for g in G:
        for side, team, opp in (("home", g["home"], g["away"]), ("away", g["away"], g["home"])):
            h = [x for x in log[team] if x[3] == g["season"]]
            d = {"gap_h": None, "where": None, "n_away": 0, "n3": 0, "gid": g["id"], "tz": g.get("tz_trip") if side == "away" else g.get("tz_trip_h")}
            if h:
                p = h[-1]
                d["gap_h"] = (_t(g["start"]) - _t(p[0])).total_seconds() / 3600
                d["where"] = p[1]
                k = 0
                for x in reversed(h):
                    if x[1] == "home":
                        break
                    k += 1
                d["n_away"] = k
                d["n3"] = sum(1 for x in h if (_t(g["start"]) - _t(x[0])).total_seconds() <= 4.5 * 86400)
            out[(g["id"], side)] = d
        for side, team, opp in (("home", g["home"], g["away"]), ("away", g["away"], g["home"])):
            w = "neutral" if g["neu"] else ("home" if side == "home" else "road")
            log[team].append((g["start"], w, opp, g["season"]))
    return out


def attach(R, P=None):
    P = P or prev_table()
    for r in R:
        d = P.get((r["gid"], r["side"])) or {}
        o = P.get((r["gid"], "away" if r["side"] == "home" else "home")) or {}
        r["gap_h"], r["pwhere"], r["n_away"], r["n3"] = d.get("gap_h"), d.get("where"), d.get("n_away", 0), d.get("n3", 0)
        r["ogap_h"], r["opwhere"], r["on_away"] = o.get("gap_h"), o.get("where"), o.get("n_away", 0)
    return R
