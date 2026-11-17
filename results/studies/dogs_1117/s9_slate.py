"""11/17 UNDERDOG EDGE - (9) A NEW-WEIGHT CANDIDATE: THE HOCKEY SLATE. On R3 the day's SECOND and THIRD gated hockey
dogs beat the first (s8_rank) - is it the day (a big slate, many spots), not the rank? The NBA dog score carries a
12+ game slate weight (10/28); hockey carries none. Tested on the RAW rig, where nothing was fit: every NHL (and NBA)
regular-season side at ESPN's closing moneyline 2018-26 (max_pro_1116/mp.py), train 2018-21 / held out 2022-26, each
season apart - dogs +100..+350 by the number of games that night, and the stacks the engine's own gate implies.
Usage: python results/studies/dogs_1117/s9_slate.py > results/studies/dogs_1117/s9_slate.out"""
import os
import pickle
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "max_pro_1116"))
import mp  # noqa: E402


def rows(lg):
    f = os.path.join(mp.CACHE, f"dogs1117_raw_{lg}.pkl")
    if os.path.exists(f):
        return pickle.load(open(f, "rb"))
    r = mp.build(lg)
    pickle.dump(r, open(f, "wb"))
    return r


for lg in ("nhl", "nba"):
    R = rows(lg)
    n_day = Counter()
    for r in R:
        if r["home"]:
            n_day[r["date"]] += 1
    dogs = [r for r in R if 100 <= r["odds"] <= 350]
    for r in dogs:
        r["slate"] = n_day[r["date"]]
    print(f"\n===== {lg}: {len(dogs)} dogs +100..+350 at the close, {min(r['season'] for r in dogs)}-{max(r['season'] for r in dogs)}")
    mp.cell("every dog (the vig)", dogs, lg)
    print("-- by the number of games that night")
    for lo, hi in ((1, 3), (3, 5), (5, 7), (7, 9), (9, 11), (11, 13), (13, 17)):
        mp.cell(f"slate {lo}..{hi - 1} games", [r for r in dogs if lo <= r["slate"] < hi], lg)
    for cut in (8, 10, 12):
        big = [r for r in dogs if r["slate"] >= cut]
        c = mp.cell(f"slate {cut}+ games", big, lg)
        print(f"        placebo vs every dog: {mp.placebo(big, dogs)} of 2,000")
        mp.cell(f"   ... +100..+150", [r for r in big if r["odds"] <= 150], lg)
        mp.cell(f"   ... +151..+350", [r for r in big if r["odds"] > 150], lg)
        mp.cell(f"   ... road", [r for r in big if not r["home"]], lg)
        mp.cell(f"   ... home", [r for r in big if r["home"]], lg)
    print("-- the b2b spot (the dog rested, the favorite played last night) by the slate")
    b = [r for r in dogs if not r["b2b"] and r["o_b2b"]]
    mp.cell("the b2b spot, every slate", b, lg)
    for lo, hi in ((1, 6), (6, 10), (10, 17)):
        mp.cell(f"   slate {lo}..{hi - 1}", [r for r in b if lo <= r["slate"] < hi], lg)
    print("-- how many b2b spots that night (the engine's own-read edge in hockey)")
    nb = Counter(r["date"] for r in b)
    for k in (1, 2, 3):
        mp.cell(f"   a night with {k}{'+' if k == 3 else ''} b2b-spot dogs: those dogs", [r for r in b if (nb[r["date"]] >= 3 if k == 3 else nb[r["date"]] == k)], lg)
    print("-- by the day of the week (the big slates are Tue / Thu / Sat)")
    import datetime
    for wd, nm in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
        mp.cell(f"   {nm}", [r for r in dogs if datetime.date.fromisoformat(r["date"]).weekday() == wd], lg)
print(f"\ncells printed: {len(mp.TRIED)}")
