"""11/15 - THE HOCKEY FLOOR ON SEASONS NOTHING SAW (is a posted cell too loose?). The daily floor's hockey dogs made
+12.5% (the 10/30 rows) / +3.0% (today's code) on the 2023-26 boards - the seasons the floor's rules were picked on.
The 11/2 NHL odds-history rig (2020-23, the morning price, the dog score rebuilt from history) is the unseen test:
  a hockey day's board = the Dog (s1_hockey_dog.pick) if there is one; the FLOOR then fills the day to 2 unit plays with
  the best-scored dogs that are not fighting and THIN (own read under 3c over the price), the second one only at a dog
  score of 0+ (FLOOR_SECOND_SCORE), one a game. (No named-reason flag on that rig, and hockey is the only sport on it -
  live, baseball / the NFL share the floor - so this is the floor's hockey leg at its widest.)
Usage: python results/studies/sizing_1115/s9_floor_oos.py > results/studies/sizing_1115/s9_floor_oos.out"""
import contextlib
import importlib.util
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NH = os.path.join(os.path.dirname(HERE), "nhl_odds_1102")
sys.path.insert(0, NH)
import lib  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    spec = importlib.util.spec_from_file_location("s1h", os.path.join(NH, "s1_hockey_dog.py"))
    s1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s1)


def show(name, xs, close=False):
    print(lib.line(name, lib.st([(x["r"]["season"], s1.close_profit(x) if close else x["profit"], 1) for x in xs])))


for at in ("morning",):
    print(f"===== AT THE {at.upper()} PRICE, 2020-21 / 2021-22 / 2022-23 =====")
    bd = s1.cands(at)
    dogs, floor1, floor2, fb = [], [], [], []
    for day, xs in sorted(bd.items()):
        dog, kind = s1.pick(xs)
        have = 1 if dog else 0
        if dog:
            dogs.append(dog)
        pool = sorted([x for x in xs if not s1.fighting(x) and x["own"] * x["dec"] - 1 < 0.03
                       and (dog is None or x["r"] is not dog["r"])], key=lambda x: -x["score"])
        used = set()
        for x in pool:
            if have >= 2:
                break
            if id(x["r"]) in used:
                continue
            if have >= 1 and x["score"] < 0:
                continue
            used.add(id(x["r"]))
            (floor1 if have == 0 else floor2).append(x)
            if have == 0 and x["score"] < 0:
                fb.append(x)
            have += 1
    show("the hockey Dog of the Day (for scale)", dogs)
    fl = floor1 + floor2
    show("THE FLOOR's hockey dogs (fills the day to 2)", fl)
    show("   ... graded at the CLOSE", fl, close=True)
    show("   the day's FIRST unit play (no Dog that day)", floor1)
    show("   the SECOND play (score 0+)", floor2)
    show("   a first play at a score under 0 (the one-a-day fallback)", fb)
    for lo, hi in ((-99, 0), (0, 2), (2, 4), (4, 6), (6, 99)):
        show(f"   floor dogs, score {lo}..{hi}", [x for x in fl if lo <= x["score"] < hi])
    for lo, hi in ((100, 129), (130, 159), (160, 199), (200, 350)):
        show(f"   floor dogs, +{lo}..+{hi}", [x for x in fl if lo <= x["am"] <= hi])
    show("   floor dogs, own read not under the market", [x for x in fl if x["own"] >= x["pm"]])
    show("   floor dogs, own read UNDER the market (the dog on a back-to-back)", [x for x in fl if x["own"] < x["pm"]])
    show("   floor dogs, score 0+ and own read not under the market", [x for x in fl if x["own"] >= x["pm"] and x["score"] >= 0])
    # the ⭐ on a floor-only day: the floor's first play when the read its units ride on (the no-vig market + its dog
    # score, sports.read_of for a dog) beats the price - raised to 1u (BEST_MIN_UNITS)
    star = [x for x in floor1 if (x["pm"] + x["score"] / 100) * x["dec"] > 1]
    show("THE ⭐ ON A FLOOR-ONLY DAY (the first floor dog, its read over the price - 1u live)", star)
    show("   ... the floor-only days' first dog whose read does NOT beat the price (stays ½u)", [x for x in floor1 if x not in star])
    show("   the ⭐ on the Dog of the Day (its read over the price)", [x for x in dogs if (x["pm"] + x["score"] / 100) * x["dec"] > 1])
