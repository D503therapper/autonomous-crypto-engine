"""11/15 - THE NEXT HOCKEY DOG ON SEASONS THE WEIGHTS NEVER SAW. Boards R1 / R2 (2023-26) say a hockey dog that passes the
floor's checks at a dog score of 4-6 and was kept off made money in both halves (s6_hockey.out). But the dog score's
hockey weights were fit on those same seasons. The 11/2 NHL odds-history rig (results/studies/nhl_odds_1102/lib.py - the
owner's paid 2020-23 prices, the live read = the line + b2b / rest, the dog score rebuilt from history) is three seasons
NONE of it saw. The same rule there, at the MORNING price (the 8 AM board's number) and graded at the close too:
  the day's Dog = the best gated dog (6+) or the fallback (s1_hockey_dog.pick); the NEXT hockey dog = the best-scored
  dog of the rest, not fighting, own read not under the market, score 4+ (and 4-6 only), one a day.
(That rig has no named-reason flag: every not-fighting dog counts - the floor's named-reason check can only shrink it.)
Usage: python results/studies/sizing_1115/s7_hockey_oos.py > results/studies/sizing_1115/s7_hockey_oos.out"""
import importlib.util
import io
import contextlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NH = os.path.join(os.path.dirname(HERE), "nhl_odds_1102")
sys.path.insert(0, NH)
import lib  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):          # s1 prints its own study on import - not ours
    spec = importlib.util.spec_from_file_location("s1h", os.path.join(NH, "s1_hockey_dog.py"))
    s1 = importlib.util.module_from_spec(spec)
    cwd = os.getcwd()
    try:
        spec.loader.exec_module(s1)
    finally:
        pass


def show(name, xs, close=False):
    print(lib.line(name, lib.st([(x["r"]["season"], s1.close_profit(x) if close else x["profit"], 1) for x in xs])))


for at in ("morning", "open"):
    print(f"\n===== AT THE {at.upper()} PRICE, 2020-21 / 2021-22 / 2022-23 (seasons no weight ever saw) =====")
    bd = s1.cands(at)
    ok = lambda x: not s1.fighting(x) and x["own"] >= x["pm"]   # noqa: E731
    alld = [x for d in bd.values() for x in d if ok(x)]
    for lo, hi in ((-99, 0), (0, 2), (2, 4), (4, 6), (6, 99)):
        show(f"every dog, score {lo}..{hi} (not fighting, own >= market)", [x for x in alld if lo <= x["score"] < hi])
    nxt, nxt46, nxt_thin, second = [], [], [], []
    for day, xs in sorted(bd.items()):
        dog, kind = s1.pick(xs)
        rest = sorted([x for x in xs if ok(x) and x is not dog and (dog is None or x["r"] is not dog["r"])],
                      key=lambda x: -x["score"])
        r4 = [x for x in rest if x["score"] >= 4]
        if r4:
            nxt.append(r4[0])
            if len(r4) > 1:
                second.append(r4[1])
        r46 = [x for x in rest if 4 <= x["score"] < 6]
        if r46:
            nxt46.append(r46[0])
        rt = [x for x in rest if x["score"] >= 4 and x["own"] * x["dec"] - 1 < 0.03]     # thin (sports.THIN_EDGE)
        if rt:
            nxt_thin.append(rt[0])
    show("THE NEXT HOCKEY DOG: the best of the rest at 4+, one a day", nxt)
    show("   ... graded at the CLOSE", nxt, close=True)
    show("   ... under the gate only (4-6)", nxt46)
    show("   ... thin only (own read under 3c over the price)", nxt_thin)
    show("   ... +100..+159", [x for x in nxt if x["am"] <= 159])
    show("   ... on a day the board has a hockey Dog", [x for x, d in ((x, s1.pick(bd[x["r"]["date"]])[0]) for x in nxt) if d is not None])
    show("   ... on a day with no hockey Dog", [x for x, d in ((x, s1.pick(bd[x["r"]["date"]])[0]) for x in nxt) if d is None])
    show("   the SECOND one a day", second)
