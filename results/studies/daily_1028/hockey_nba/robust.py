"""10/28 robustness on the NHL / NBA cells that looked like something: (a) the NHL home favorite -100..-150 deep in a
homestand (4th+ straight home game: -9.5% train 0 of 7, -26.3% held out) - game by game, and the road dog across from it;
(b) the NBA team that lost the 1st quarter in each of its last 3 (dogs -9.7% / -17.1%, favorites -13.9% / -11.0%) - is it
just a team on a losing streak? 2 / 4 straight, with the last 3 results held fixed; (c) the NHL dog outscored in the 1st
period 3 straight (-16.1% / -12.6%) - the same controls."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "studies.py")).read().split("# ---------------- NHL ----------------")[0])
_feat = feat


def feat2(g, side, prev, s):                                   # + the last 3 / 4 results and 1st-period diffs of the last 4
    d = _feat(g, side, prev, s)
    t = g[side]
    cur = [p for p in prev if season(p["start"]) == s]
    res, p1 = [], []
    for p in cur[-4:]:
        ps, os_ = me(p, t)
        res.append(float(p[f"{ps}_score"]) > float(p[f"{os_}_score"]))
        a, b = first(p, ps), first(p, os_)
        p1.append(None if a is None or b is None else a - b)
    d["res4"], d["p1_4"] = res, p1
    return d


def lostp1(x, k):
    v = x["p1_4"][-k:]
    return len(v) == k and None not in v and max(v) < 0


def l3(x):
    return sum(x["res4"][-3:]) if len(x["res4"]) >= 3 else None


fin, sched = load("nhl")
NHL = sides(fin, sched, feat2)
print("#### (a) NHL HOME FAVORITE -100..-150 BY ITS STRAIGHT HOME GAME (today included)")
for k in (1, 2, 3, 4, 5):
    cell(NHL, lambda x, k=k: fav(x) and x["home"] and x["homes"] == k, f"NHL home fav, home game {k} in a row", TR, HO)
cell(NHL, lambda x: fav(x) and x["home"] and x["homes"] >= 6, "NHL home fav, home game 6+ in a row", TR, HO)
cell(NHL, lambda x: fav(x) and x["home"] and 4 <= x["homes"] <= 5, "NHL home fav, home game 4-5 in a row", TR, HO)
cell(NHL, lambda x: dog(x) and not x["home"] and 100 <= x["ml"] <= 150 and x["o_homes"] >= 4,
     "MIRROR: road dog +100..+150 at a team on its 4th+ home game", TR, HO)
cell(NHL, lambda x: dog(x) and not x["home"] and 100 <= x["ml"] <= 150, "base: every road dog +100..+150", TR, HO)
print("\n#### (c) NHL DOG OUTSCORED IN THE 1ST PERIOD")
for k in (2, 3, 4):
    cell(NHL, lambda x, k=k: dog(x) and lostp1(x, k), f"NHL dog lost the 1st period {k} straight", TR, HO)
for w in (0, 1, 2, 3):
    cell(NHL, lambda x, w=w: dog(x) and l3(x) == w and lostp1(x, 3), f"NHL dog lost the 1st 3 straight, won {w} of the last 3", TR, HO)
    cell(NHL, lambda x, w=w: dog(x) and l3(x) == w and not lostp1(x, 3), f"   same results, NOT 3 slow starts (won {w} of 3)", TR, HO)

fin, sched = load("nba")
NBA = sides(fin, sched, feat2)
print("\n#### (b) NBA LOST THE 1ST QUARTER")
for bn, b in (("dog +100..+350", dog), ("fav -100..-150", fav)):
    for k in (2, 3, 4):
        f1 = lambda x, k=k, b=b: b(x) and lostp1(x, k)   # noqa: E731
        cell(NBA, f1, f"NBA {bn} lost the 1st quarter {k} straight", TR, HO)
        ats(NBA, f1, f"NBA {bn} lost the 1st quarter {k} straight")
    for w in (0, 1, 2, 3):
        cell(NBA, lambda x, w=w, b=b: b(x) and l3(x) == w and lostp1(x, 3), f"NBA {bn} lost the 1st 3 straight, won {w} of the last 3", TR, HO)
        cell(NBA, lambda x, w=w, b=b: b(x) and l3(x) == w and not lostp1(x, 3), f"   same results, NOT 3 slow starts (won {w} of 3)", TR, HO)
print("\n#### (b2) NHL the same idea for favorites -100..-150 (a second sport)")
cell(NHL, lambda x: fav(x) and lostp1(x, 3), "NHL fav -100..-150 lost the 1st period 3 straight", TR, HO)
