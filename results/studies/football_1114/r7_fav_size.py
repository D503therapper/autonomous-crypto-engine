"""11/14 FOOTBALL - R7 THE FOOTBALL FAVORITE'S SIZE (R2 / R3 found the board's ½u football favorites 60-24 and its 1u
ones 16-19): by kind, by units, by the own read's margin over the price; NFL and college apart and together. Is the 1u
football Lock a size the replay earns, and is there a bigger size anywhere (the owner: "more units")?
Funnel5 rows, closes, train 2018-22 / held 2023-26.
Usage: python results/studies/football_1114/r7_fav_size.py > results/studies/football_1114/r7_out.txt"""
import flib as F

ML = [r for r in F.replay(markets=("ml",)) if r.get("kind") and r["odds"] < 100]
for r in ML:
    r["o_m"] = None if r["own"] is None else (r["own"] - 1 / r["dec"]) * 100
    r["nv_gap"] = None if r["own"] is None or r.get("p_market") is None else (r["own"] - r["p_market"]) * 100
for lg in ("nfl", "ncaaf", None):
    x = [r for r in ML if lg is None or r["league"] == lg]
    print(f"\n-- {(lg or 'football').upper()} favorite unit plays ({len(x)})")
    F.rline("all", x)
    for k in sorted({r["kind"] for r in x}):
        for u in sorted({r.get("units") for r in x if r["kind"] == k}, key=lambda v: v or 0):
            F.rline(f"{k} at {u}u", [r for r in x if r["kind"] == k and r.get("units") == u])
    for lo, hi in ((0, 1), (1, 3), (3, 6), (6, 99)):
        F.rline(f"own read {lo}..{hi} points over the price", [r for r in x if r["o_m"] is not None and lo <= r["o_m"] < hi])
    for lo, hi in ((-99, 3), (3, 7), (7, 99)):
        F.rline(f"own read {lo}..{hi} over the no-vig market", [r for r in x if r["nv_gap"] is not None and lo <= r["nv_gap"] < hi])
    for p0, p1 in ((0, 0.56), (0.56, 0.60), (0.60, 1)):
        F.rline(f"blend {p0:.2f}..{p1:.2f}", [r for r in x if p0 <= r["p"] < p1])
    s1 = [r for r in x if r.get("units") == 1]
    if len(s1) >= 10:
        print(f"      placebo: a random same-size set of these favorite plays did as BADLY as the 1u ones "
              f"{F.rplacebo(s1, x, worse=True)} of 2000")
