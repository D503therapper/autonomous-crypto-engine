"""10/27 robustness on the NBA cell that ran red in both halves: a -151..-400 favorite on a 5+ game win streak (train
-9.1% on 331, 0 of 7 seasons up; holdout -11.7% on 47) - other streak lengths, home / road, the dog across from it,
2023+ alone, and the same idea in the NHL (the second sport)."""
import sys, os
sys.argv = [sys.argv[0]]
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "studies.py")).read().split("# ---------------- NHL ----------------")[0]
exec(src)
L3 = (2023, 2024)
for lg in ("nba", "nhl"):
    fin, sched = load(lg)
    R = sides(fin, sched, feat)
    print(f"\n######## {lg.upper()}")
    report(R, bigf, f"{lg} BASE fav -151..-400", TR, HO)
    report(R, dog, f"{lg} BASE dog +100..+350", TR, HO)
    for k in (3, 4, 5, 6, 8):
        report(R, lambda x, k=k: bigf(x) and x["streak"] >= k, f"{lg} fav -151..-400 on a {k}+ win streak", TR, HO)
    report(R, lambda x: bigf(x) and x["streak"] >= 5 and x["home"], f"{lg} HOME fav -151..-400 on a 5+ win streak", TR, HO)
    report(R, lambda x: bigf(x) and x["streak"] >= 5 and not x["home"], f"{lg} ROAD fav -151..-400 on a 5+ win streak", TR, HO)
    report(R, lambda x: -250 <= x["ml"] < -150 and x["streak"] >= 5, f"{lg} fav -151..-250 on a 5+ win streak", TR, HO)
    report(R, lambda x: bigf(x) and x["streak"] >= 5 and x["gp"] >= 20, f"{lg} fav -151..-400 on a 5+ win streak, 20+ games in", TR, HO)
    report(R, lambda x: bigf(x) and x["streak"] >= 5 and x["season"] in L3, f"{lg} fav -151..-400 on a 5+ win streak, 2023-24 only", L3, HO)
    report(R, lambda x: 151 <= x["ml"] <= 400 and x["o_streak"] >= 5, f"{lg} MIRROR: the dog +151..+400 facing a 5+ streak fav", TR, HO)
    report(R, lambda x: 151 <= x["ml"] <= 400, f"{lg} BASE dog +151..+400", TR, HO)
    report(R, lambda x: 151 <= x["ml"] <= 400 and x["o_streak"] >= 5 and x["season"] in L3,
           f"{lg} MIRROR dog +151..+400 vs a 5+ streak fav, 2023-24 only", L3, HO)

print("\n######## NBA COMEBACK WINNER AS A SMALL FAVORITE (train z +3.3 on 68, holdout 3-6)")
fin, sched = load("nba")
R = sides(fin, sched, feat)
cb = lambda x, d: x["l_half"] is not None and x["l_half"] <= -d and x["l_won"] and x["gp"] >= 3   # noqa: E731
for d in (6, 8, 10, 12, 15):
    report(R, lambda x, d=d: fav(x) and cb(x, d), f"nba came back from {d}+ down at the half - fav -100..-150", TR, HO)
report(R, lambda x: -200 <= x["ml"] <= -100 and cb(x, 10), "nba came back from 10+ down - fav -100..-200", TR, HO)
report(R, lambda x: fav(x) and cb(x, 10) and x["home"], "nba came back from 10+ down - HOME fav -100..-150", TR, HO)
report(R, lambda x: fav(x) and cb(x, 10) and not x["home"], "nba came back from 10+ down - ROAD fav -100..-150", TR, HO)
report(R, lambda x: 100 <= x["ml"] <= 150 and x["o_l_half"] is not None and x["o_l_half"] <= -10 and x["o_l_won"] and x["o_gp"] >= 3,
       "nba MIRROR: the dog +100..+150 facing a comeback winner", TR, HO)
report(R, lambda x: fav(x) and x["l_won"] and x["gp"] >= 3, "nba control: any fav -100..-150 off a win", TR, HO)
report(R, lambda x: fav(x) and x["l_won"] and x["l_half"] is not None and x["l_half"] < 0 and x["gp"] >= 3,
       "nba control: fav -100..-150 off a win it trailed at the half (any)", TR, HO)
fin, sched = load("nhl")
R = sides(fin, sched, feat)
report(R, lambda x: fav(x) and x["l_half"] is not None and x["l_won"] and x["gp"] >= 3 and x["l_half"] <= -2,
       "NHL second sport: fav -100..-150 that won last after trailing by 2+ after 2 periods", TR, HO)
