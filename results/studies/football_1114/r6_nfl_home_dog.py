"""11/14 FOOTBALL - R6 THE NFL HOME DOG ON THE BOARD (the leak R1 named: the board's NFL home-dog unit plays lose in both
halves while its NFL ROAD dogs carry the NFL money). Where it comes from - by kind, by dog score, by the read that waved
it through (own read over the price - the old fit's home tilt? the dog score's study part?), the price, the month - and
what a cut would have done to the board (the floor's NFL dogs home vs road, the Dog home vs road). Also the same cells on
EVERY NFL dog (not just the board's), and the game files 2018-26 (every NFL home dog +100..+350 at the close) for the
market base. Funnel5 rows, closes, train 2018-22 / held 2023-26.
Usage: python results/studies/football_1114/r6_nfl_home_dog.py > results/studies/football_1114/r6_out.txt"""
import flib as F

ML = [r for r in F.replay(markets=("ml",)) if r["league"] == "nfl"]
for r in ML:
    r["neutral"] = str(r.get("neutral_g")) == "1"
    r["need"] = 1 / r["dec"]
    r["o_m"] = None if r["own"] is None else (r["own"] - r["need"]) * 100
    r["tilt"] = None if r.get("raw_own") is None or r.get("p_market") is None else (r["raw_own"] - r["p_market"]) * 100


def L(name, rs, pool=None, worse=False):
    x = F.rline(name, rs)
    if pool is not None and x["n"] >= 20:
        print(f"      placebo ({'as badly' if worse else 'as well'}): {F.rplacebo(rs, pool, worse=worse)} of 2000")
    return x


D = [r for r in ML if 100 <= r["odds"] <= 350 and not r.get("trap")]
H = [r for r in D if r["home"] and not r["neutral"]]
A = [r for r in D if not r["home"] and not r["neutral"]]
U = [r for r in D if r.get("kind")]
print(f"NFL dogs +100..+350: {len(D)} (home {len(H)}, road {len(A)}); board unit plays on them {len(U)}")
print("\n-- the board's NFL dog unit plays, home vs road, by kind")
for nm, pool in (("HOME", H), ("ROAD", A)):
    x = [r for r in pool if r.get("kind")]
    L(f"{nm} all", x, pool=pool, worse=(nm == "HOME"))
    for k in sorted({r["kind"] for r in x}):
        L(f"{nm} {k}", [r for r in x if r["kind"] == k])
    for b, lo, hi in (("+100..+150", 100, 150), ("+151..+200", 151, 200), ("+201..+350", 201, 350)):
        L(f"{nm} {b}", [r for r in x if lo <= r["odds"] <= hi])
    for nmm, ms in (("Sep-Oct", (8, 9, 10)), ("Nov", (11,)), ("Dec-Jan", (12, 1, 2))):
        L(f"{nm} {nmm}", [r for r in x if int(r["date"][5:7]) in ms])
print("\n-- every NFL dog (not just the board's): home vs road, by the reads")
for nm, pool in (("HOME", H), ("ROAD", A)):
    L(f"{nm} every dog", pool)
    L(f"{nm} own read over the price", [r for r in pool if (r["o_m"] or -1) > 0])
    L(f"{nm} dog_own_ok (own + the weighed check)", [r for r in pool if r.get("dog_own_ok")])
    L(f"{nm} dog score 4+", [r for r in pool if (r.get("dog_score") or -9) >= 4])
    L(f"{nm} dog score 4+, dog_own_ok", [r for r in pool if (r.get("dog_score") or -9) >= 4 and r.get("dog_own_ok")])
    L(f"{nm} floor-shaped: a named reason, not fighting, thin own edge", [r for r in pool if r.get("reasons") and not r.get("fighting")
                                                                          and r["o_m"] is not None and r["o_m"] < 3])
    t = [r["tilt"] for r in pool if r["tilt"] is not None]
    print(f"      the raw ratings read minus the no-vig close: mean {sum(t) / max(1, len(t)):+.2f} points on {len(t)}")
    o = [r["o_m"] for r in pool if r["o_m"] is not None]
    print(f"      the own read minus the price: mean {sum(o) / max(1, len(o)):+.2f} points")
print("\n-- the game files (every priced regular-season NFL game 2018-26 at the close): the market base")
S = [s for s in F.sides("nfl") if 100 <= s["odds"] <= 350 and not s["neutral"]]
F.cell("home dog +100..+350", [s for s in S if s["home"]])
F.cell("road dog +100..+350", [s for s in S if not s["home"]])
F.cell("home dog +100..+150", [s for s in S if s["home"] and s["odds"] <= 150])
F.cell("road dog +100..+150", [s for s in S if not s["home"] and s["odds"] <= 150])
print("\n-- what a cut does to the board (the NFL dog unit plays without the HOME floor dog / without every HOME dog)")
L("today: every NFL dog unit play", U)
L("without the HOME floor dog", [r for r in U if not (r["kind"] == "floor" and r["home"] and not r["neutral"])])
L("without any HOME dog unit play", [r for r in U if not (r["home"] and not r["neutral"])])
L("the HOME floor dogs alone", [r for r in U if r["kind"] == "floor" and r["home"] and not r["neutral"]], pool=H, worse=True)
L("the HOME Dogs of the Day alone", [r for r in U if r["kind"] == "dog" and r["home"] and not r["neutral"]], pool=H, worse=True)
