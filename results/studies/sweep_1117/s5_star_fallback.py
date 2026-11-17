"""11/17 FULL SWEEP - S11 THE ⭐ ON A FLOOR FALLBACK. The 11/17 dry run of the board with no injury report loaded put
up ONE play - Ball State +350, a college football floor FALLBACK at a dog score of -0.0 ("the price is about fair and
the dog angles are mixed") - and the ⭐ made it "the engine's best pick today - a full unit on it".
A floor fallback is a dog of a kind the floor SITS OUT because the replay says it loses (a college football dog, an NBA
dog, a dog whose raw own read is 3c+ over the price with the full read short of the Dog gate; live also a college hoops
dog, an NFL home dog, a dog score under 0) - it goes up only so the day has one unit play (the owner, 10/27). The ⭐
needs a read that beats its price (11/5) - a fallback's weighed read can beat its price by a point and the star then
doubles the one bet the floor's own rules call a loser.
The boards have only 5-6 real fallback days, so the cell is judged on the KIND: every board day's best sit-out floor dog
by score whose read beats its price (what the ⭐ asks), whether or not that day needed it. Both replay boards
(sizing_1114/lib.py). The checks are a CUT's: does it lose / do worse than the ⭐ picks the board really makes?
Usage: python results/studies/sweep_1117/s5_star_fallback.py > results/studies/sweep_1117/s5_star_fallback.out"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "sizing_1114"))
import lib as L  # noqa: E402
import s1_star as S  # noqa: E402
import slib  # noqa: E402

half = L.half
sv = L.sv
for bn, (board, by) in L.boards().items():
    print("=" * 30, "BOARD", bn)
    stars = [(d, r, 1.0) for d, r, u, k in S.stars(board, S.today)]
    fb_posted = [(d, r, 0.5) for d, ps in board.items() for r, u, k in ps if k == "floorfb"]
    kind, kind_star = [], []
    for d in sorted(by):
        pool = [r for r in by[d] if sv.floor_ok(r) and not sv.floor_v2(r)]
        if not pool:
            continue
        b = max(pool, key=lambda r: (r["dog_score"], r["edge"]))
        kind.append((d, b, 0.5))
        if L.beats(b, "floor"):
            kind_star.append((d, b, 1.0))
    slib.five("the ⭐ picks the board makes (the frame)", stars, None, half)
    slib.five("the floor fallbacks the board really posted", fb_posted, None, half)
    slib.five("THE KIND: the day's best sit-out floor dog by score", kind, None, half)
    slib.loses("   ...against the ⭐ picks", kind, stars + kind, half)
    slib.five("THE KIND with its read over its price (⭐-eligible)", kind_star, None, half)
    slib.loses("   ...against the ⭐ picks", kind_star, stars + kind_star, half)
    for lg in ("ncaaf", "nba", "nhl", "mlb", "nfl", "ncaab"):
        c = [x for x in kind_star if x[1]["league"] == lg]
        if len(c) >= 10:
            slib.five(f"   ...{lg}", c, None, half)
    for nm, f in (("dog score under 0", lambda r: r["dog_score"] < 0), ("dog score 0+", lambda r: r["dog_score"] >= 0),
                  ("+200..+350", lambda r: r["odds"] >= 200), ("+100..+199", lambda r: r["odds"] < 200)):
        c = [x for x in kind_star if f(x[1])]
        if len(c) >= 10:
            slib.five(f"   ...{nm}", c, None, half)
    rs = [x for x in kind_star if half(x[0]) != "live"]
    print(f"   the ⭐'s extra half unit on every one of them: {sum(0.5 * slib.flat(r) for _, r, _ in rs):+.1f}u on {0.5 * len(rs):.0f}u more "
          f"(train {sum(0.5 * slib.flat(r) for d, r, _ in rs if half(d) == 'train'):+.1f}u / held "
          f"{sum(0.5 * slib.flat(r) for d, r, _ in rs if half(d) == 'held'):+.1f}u)")
