"""11/14 STUDY 8 - CONFERENCE SEASON ANGLES TO HAVE READY FOR JANUARY (priority 5). Sides (moneyline + spread at the
close, their own juice; -110 where a spread price is missing) in league play, every input known before tip. Not re-run
(dead or built on file): the race dog, the league leader on the road / the home side across (built 11/12), the rusty
home side, rest / density / travel / road swings as sides, revenge and the rematch, the rubber match, the home-loss
bounce, buy games, the both-teams-out-of-it over (a Feb 15 re-read).
  (a) THE LEAGUE OPENER - each team's first league game
  (b) SENIOR NIGHT - the team's last regular-season home game of the season (the schedule is known)
  (c) THE NON-CONFERENCE RECORD LIES - league games 1-4, a team whose non-conference win % beat its opponent's by .300+
  (d) OFF A ROAD UPSET - the team's last game a road win as a +150 or longer dog, next game
  (e) THE MIDWEEK / SATURDAY ROAD FAVORITE in league play"""
import math, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
import tlib

G = [g for g in tlib.build() if g["stype"] == "2"]
last_home = {}
for g in G:
    if not g["neu"]:
        last_home[(g["home"], g["season"])] = g["id"]
nc = defaultdict(lambda: [0, 0])     # (team, season) -> non-conference W, L
cg = defaultdict(int)                # (team, season) -> league games played
lastg = {}                           # (team, season) -> (won, road, ml)
S = []                               # side rows


def mlp(o, won):
    return (L.dec(o) - 1) if won else -1.0


for g in G:
    s = g["season"]
    for side in ("home", "away"):
        me, op = (g["home"], g["away"]) if side == "home" else (g["away"], g["home"])
        ml = g["mlh"] if side == "home" else g["mla"]
        sp = None if g["sp"] is None else (g["sp"] if side == "home" else -g["sp"])
        spo = (g["spo_h"] if side == "home" else g["spo_a"]) or -110
        mar = g["margin"] if side == "home" else -g["margin"]
        won = mar > 0
        a, b = nc[(me, s)], nc[(op, s)]
        row = {"season": s, "month": g["month"], "side": side, "conf": g["conf"], "neu": g["neu"], "ml": ml, "sp": sp,
               "won": won, "cg": cg[(me, s)], "ocg": cg[(op, s)],
               "ncw": (a[0] / (a[0] + a[1])) if a[0] + a[1] >= 6 else None,
               "oncw": (b[0] / (b[0] + b[1])) if b[0] + b[1] >= 6 else None,
               "senior": side == "home" and not g["neu"] and last_home.get((me, s)) == g["id"] and g["month"] in ("02", "03"),
               "last": lastg.get((me, s)), "wd": g["start"][:10]}
        row["mlpnl"] = None if ml is None else mlp(ml, won)
        if sp is not None:
            cov = mar + sp
            row["atspnl"] = 0.0 if cov == 0 else ((L.dec(spo) - 1) if cov > 0 else -1.0)
        else:
            row["atspnl"] = None
        S.append(row)
    # update after the game
    for side in ("home", "away"):
        me = g["home"] if side == "home" else g["away"]
        mar = g["margin"] if side == "home" else -g["margin"]
        if g["conf"]:
            cg[(me, s)] += 1
        else:
            nc[(me, s)][0 if mar > 0 else 1] += 1
        ml = g["mlh"] if side == "home" else g["mla"]
        lastg[(me, s)] = (mar > 0, side == "away" and not g["neu"], ml)

S = [r for r in S if r["season"] >= 2018]


def cell(name, rows, mk):
    rr = [dict(r, pnl=r[mk + "pnl"], win=(r[mk + "pnl"] or 0) > 0) for r in rows if r[mk + "pnl"] is not None]
    L.rec(f"{name} [{mk.upper()}]", rr, None, min_n=40)


LG = [r for r in S if r["conf"] and not r["neu"]]
print(f"league sides (true home / road): {len(LG)}")
cell("every league side", LG, "ats")
cell("every league home side", [r for r in LG if r["side"] == "home"], "ats")
print("\n(a) THE LEAGUE OPENER")
op = [r for r in LG if r["cg"] == 0]
for nm, f in (("home", lambda r: r["side"] == "home"), ("road", lambda r: r["side"] == "away"),
              ("home favorite", lambda r: r["side"] == "home" and (r["ml"] or 0) < 0), ("road favorite", lambda r: r["side"] == "away" and (r["ml"] or 0) < 0),
              ("home dog", lambda r: r["side"] == "home" and (r["ml"] or 0) > 0), ("road dog", lambda r: r["side"] == "away" and (r["ml"] or 0) > 0)):
    cell(f"opener {nm}", [r for r in op if f(r)], "ats")
    cell(f"opener {nm}", [r for r in op if f(r)], "ml")
print("\n(b) SENIOR NIGHT (the last home game, Feb-Mar)")
sn = [r for r in LG if r["senior"]]
for nm, f in (("home side", lambda r: True), ("home favorite", lambda r: (r["ml"] or 0) < 0), ("home dog", lambda r: (r["ml"] or 0) > 0),
              ("home favorite laying 10+", lambda r: (r["sp"] or 0) <= -10), ("home side laying 0.5-9.5", lambda r: -10 < (r["sp"] or 0) < 0)):
    cell(f"senior night {nm}", [r for r in sn if f(r)], "ats")
    cell(f"senior night {nm}", [r for r in sn if f(r)], "ml")
print("\n(c) THE NON-CONFERENCE RECORD LIES (league games 1-4, both 6+ non-league games)")
e = [r for r in LG if r["cg"] <= 3 and r["ncw"] is not None and r["oncw"] is not None]
for nm, f in (("non-league win % .300+ better", lambda r: r["ncw"] - r["oncw"] >= 0.3),
              ("non-league win % .300+ worse", lambda r: r["ncw"] - r["oncw"] <= -0.3),
              (".300+ better, favorite", lambda r: r["ncw"] - r["oncw"] >= 0.3 and (r["ml"] or 0) < 0),
              (".300+ worse, dog", lambda r: r["ncw"] - r["oncw"] <= -0.3 and (r["ml"] or 0) > 0),
              (".300+ worse, dog, at home", lambda r: r["ncw"] - r["oncw"] <= -0.3 and (r["ml"] or 0) > 0 and r["side"] == "home")):
    cell(nm, [r for r in e if f(r)], "ats")
    cell(nm, [r for r in e if f(r)], "ml")
print("\n(d) OFF A ROAD UPSET (last game: a road win at +150 or longer), next game - any game, true home / road")
a = [r for r in S if not r["neu"] and r["last"] and r["last"][0] and r["last"][1] and (r["last"][2] or 0) >= 150]
for nm, f in (("all", lambda r: True), ("league", lambda r: r["conf"]), ("now a favorite", lambda r: (r["ml"] or 0) < 0),
              ("now a dog", lambda r: (r["ml"] or 0) > 0), ("now at home", lambda r: r["side"] == "home"), ("now on the road", lambda r: r["side"] == "away")):
    cell(f"off a road upset, {nm}", [r for r in a if f(r)], "ats")
    cell(f"off a road upset, {nm}", [r for r in a if f(r)], "ml")
print("\n(e) THE ROAD FAVORITE BY DAY (league play)")
from datetime import datetime
rf = [r for r in LG if r["side"] == "away" and (r["ml"] or 0) < 0]
for nm, f in (("Saturday", lambda r: datetime.strptime(r["wd"], "%Y-%m-%d").weekday() == 5),
              ("Mon-Thu", lambda r: datetime.strptime(r["wd"], "%Y-%m-%d").weekday() <= 3),
              ("Sunday", lambda r: datetime.strptime(r["wd"], "%Y-%m-%d").weekday() == 6)):
    cell(f"road favorite {nm}", [r for r in rf if f(r)], "ats")
    cell(f"road favorite {nm}", [r for r in rf if f(r)], "ml")
print(f"\ncells read: {L.CELLS[0]}")
