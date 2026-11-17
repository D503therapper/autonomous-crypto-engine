"""11/17 MOST MONEY - (6) THE HOCKEY RUNNER-UP DOG ON SEASONS NO WEIGHT EVER SAW. The runner-up dog (sports.dog_plays) is
the day's best GATED hockey dog (a dog score of 6+) that is not the Dog of the Day - one a day. On today's code 2023-26 it
is +34% in both halves (s5_options.out), but the dog score's hockey weights were fit on those seasons. The 11/2 NHL
odds-history rig (results/studies/nhl_odds_1102/lib.py - the owner's paid 2020-23 prices, the dog score rebuilt from
history, three seasons nothing saw; the rig sizing_1115/s7_hockey_oos.py used): the same rule there, at the MORNING
price, the OPEN, and graded at the close.
Usage: python results/studies/money_1117/s6_runnerup_oos.py > results/studies/money_1117/s6_runnerup_oos.out"""
import contextlib
import importlib.util
import io
import os
import random
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
    return xs


for at in ("morning", "open"):
    print(f"\n===== AT THE {at.upper()} PRICE, 2020-21 / 2021-22 / 2022-23 (seasons no weight ever saw) =====")
    bd = s1.cands(at)
    ok = lambda x: not s1.fighting(x) and x["own"] >= x["pm"]   # noqa: E731
    dogs, gated_dogs, ru, ru_all, gated = [], [], [], [], []
    for day, xs in sorted(bd.items()):
        dog, kind = s1.pick(xs)
        if dog is not None:
            dogs.append(dog)
            if dog["score"] >= 6:
                gated_dogs.append(dog)
        g = [x for x in xs if ok(x) and x["score"] >= 6]
        gated += g
        rest = sorted([x for x in g if dog is None or x["r"] is not dog["r"]], key=lambda x: -x["score"])
        if rest and dog is not None:
            ru.append(rest[0])
            ru_all += rest
    show("the hockey Dog of the Day", dogs)
    show("   ... the gated ones (6+)", gated_dogs)
    show("every gated hockey dog (6+, not fighting, own >= market)", gated)
    show("THE RUNNER-UP: the best gated dog that is not the Dog, one a day", ru)
    show("   ... graded at the CLOSE", ru, close=True)
    show("   ... +100..+150", [x for x in ru if x["am"] <= 150])
    show("   ... +151 and longer", [x for x in ru if x["am"] > 150])
    show("   every gated dog that is not the Dog (no one-a-day cap)", ru_all)
    days_ru = {x["r"]["date"] for x in ru}
    show("   the Dog on a day WITH a runner-up", [d for d in dogs if d["r"]["date"] in days_ru])
    show("   the Dog on a day with none", [d for d in dogs if d["r"]["date"] not in days_ru])
    if len(ru) >= 10 and len(gated) > len(ru):
        mine = sum(x["profit"] for x in ru) / len(ru)
        fl = [x["profit"] for x in gated]
        rnd = random.Random(1117)
        print(f"   placebo: a random {len(ru)} of the gated dogs as good as the runner-up: {sum(1 for _ in range(2000) if sum(rnd.sample(fl, len(ru))) / len(ru) >= mine)} of 2,000")
