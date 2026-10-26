"""NHL, 3 studies (10/26). Train 2016-24, HOLDOUT 2025, current 2026. Flat 1u at the closing ML. Schedule + results of
EARLIER games only.
S6 CROSS-CONFERENCE games (East vs West - two meetings a season, the teams barely know each other) - dogs / favorites,
   home / road, the travelling West team in the East and the other way.
S7 THE SECOND GAME OF A HOME-AND-HOME (same two teams within 4 days, venue swapped) - the game-1 loser / winner.
S8 COLD OFFENSE: scored 1 or fewer goals in each of the last 2 games (and 0-1 in 3 of the last 3)."""
from common import *  # noqa: F401,F403
EAST = {"Bruins", "Sabres", "Red Wings", "Panthers", "Canadiens", "Senators", "Lightning", "Maple Leafs", "Hurricanes",
        "Blue Jackets", "Devils", "Islanders", "Rangers", "Flyers", "Penguins", "Capitals"}
fin, sched = load("nhl")
TR = tuple(range(2016, 2025)); HO = (2025,); CU = (2026,)


def feat(g, side, prev, s):
    t = g[side]; nm = g[f"{side}_name"]
    prev = [p for p in prev if season(p["start"]) == s]
    goals = []
    for p in prev[-3:]:
        ps = "home" if p["home"] == t else "away"
        goals.append(float(p[f"{ps}_score"]))
    p1 = prev[-1] if prev else None
    hh = m1 = None
    if p1 is not None and {p1["home"], p1["away"]} == {g["home"], g["away"]} and (dt(g["start"]) - dt(p1["start"])).days <= 4:
        ps = "home" if p1["home"] == t else "away"; po = "away" if ps == "home" else "home"
        m1 = float(p1[f"{ps}_score"]) - float(p1[f"{po}_score"])
        hh = p1["home"] != g["home"]           # venue swapped = a home-and-home
    gp = len(prev); w = 0
    for p in prev:
        ps = "home" if p["home"] == t else "away"; po = "away" if ps == "home" else "home"
        w += float(p[f"{ps}_score"]) > float(p[f"{po}_score"])
    return dict(east=nm in EAST, west=nm not in EAST, g2=goals[-2:], g3=goals, hh=hh, m1=m1, gp=gp, wp=w / gp if gp else None)


rows = sides(fin, sched, feat)
R = lambda f, n: report(rows, f, n, TR, HO, CU)
dog = lambda x: 100 <= x["ml"] <= 350; fav = lambda x: -150 <= x["ml"] <= -100; bigf = lambda x: -250 <= x["ml"] < -150
cross = lambda x: x["east"] != x["o_east"] and x["season"] != 2020      # (2020-21: no cross-conference games)
print("rows", len(rows), "cross-conference sides", sum(1 for x in rows if cross(x)))
print("\n#### baselines"); R(dog, "BASE dog +100..+350"); R(fav, "BASE fav -150..-100"); R(bigf, "BASE fav -151..-250")
print("\n#### S6 CROSS-CONFERENCE  [10 cells]")
for nm, f in [("cross-conf dog", lambda x: cross(x) and dog(x)), ("cross-conf fav -150..-100", lambda x: cross(x) and fav(x)),
              ("cross-conf HOME dog", lambda x: cross(x) and dog(x) and x["home"]), ("cross-conf ROAD dog", lambda x: cross(x) and dog(x) and not x["home"]),
              ("cross-conf HOME fav -150..-100", lambda x: cross(x) and fav(x) and x["home"]),
              ("cross-conf ROAD fav -150..-100", lambda x: cross(x) and fav(x) and not x["home"]),
              ("West team at an East home - dog", lambda x: cross(x) and dog(x) and not x["home"] and x["west"]),
              ("East team at a West home - dog", lambda x: cross(x) and dog(x) and not x["home"] and x["east"]),
              ("West team at an East home - fav", lambda x: cross(x) and fav(x) and not x["home"] and x["west"]),
              ("East team at a West home - fav", lambda x: cross(x) and fav(x) and not x["home"] and x["east"])]:
    R(f, "S6 " + nm)
R(lambda x: not cross(x) and dog(x), "S6 control: same-conference dog")
print("\n#### S7 SECOND GAME OF A HOME-AND-HOME  [6 cells]")
for nm, f in [("game-1 LOSER - dog", lambda x: x["hh"] and x["m1"] < 0 and dog(x)), ("game-1 LOSER - fav", lambda x: x["hh"] and x["m1"] < 0 and fav(x)),
              ("game-1 WINNER - dog", lambda x: x["hh"] and x["m1"] > 0 and dog(x)), ("game-1 WINNER - fav", lambda x: x["hh"] and x["m1"] > 0 and fav(x)),
              ("game-1 loser by 3+ - dog", lambda x: x["hh"] and x["m1"] <= -3 and dog(x)), ("game-1 loser by 3+ - fav", lambda x: x["hh"] and x["m1"] <= -3 and fav(x))]:
    R(f, "S7 " + nm)
R(lambda x: x["hh"] is False and x["m1"] < 0 and dog(x), "S7 control: same-building rematch, game-1 loser - dog")
print("\n#### S8 COLD OFFENSE (<=1 goal in each of the last 2 / 3)  [8 cells]")
c2 = lambda x: len(x["g2"]) == 2 and max(x["g2"]) <= 1
c3 = lambda x: len(x["g3"]) == 3 and max(x["g3"]) <= 1
oc2 = lambda x: len(x["o_g2"]) == 2 and max(x["o_g2"]) <= 1
for nm, f in [("cold 2 - dog", lambda x: c2(x) and dog(x)), ("cold 2 - fav -150..-100", lambda x: c2(x) and fav(x)),
              ("cold 2 - fav -151..-250", lambda x: c2(x) and bigf(x)), ("cold 3 - dog", lambda x: c3(x) and dog(x)),
              ("cold 3 - fav -150..-100", lambda x: c3(x) and fav(x)),
              ("FACING a cold-2 team - dog", lambda x: oc2(x) and dog(x)), ("FACING a cold-2 team - fav -150..-100", lambda x: oc2(x) and fav(x)),
              ("FACING a cold-2 team - fav -151..-250", lambda x: oc2(x) and bigf(x))]:
    R(f, "S8 " + nm)
