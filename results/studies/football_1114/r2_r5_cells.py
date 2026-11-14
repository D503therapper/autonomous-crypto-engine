"""11/14 FOOTBALL - R2-R5 ON THE REPLAY BOARD (funnel5 rows, today's code, every football board day 2018-26, closes).
R2  NFL FAVORITES -101..-150 (the live strength, 8-4): every candidate by its reads - the own read over the price, the
    weighed read over it, both, the blend, the month, home / road; what the board posts vs what it leaves.
    Is there a cell that deserves to be a unit play more often, or bigger?
R3  COLLEGE FAVORITES -101..-150: the same, plus the 11/12 MC1 lead (the WEIGHED read over the price: 54-27 +19.0% on
    81 on the 2023-26 rows) on eight seasons, and the rule-A weight's sides.
R4  FOOTBALL SPREADS: the board's spread leans and every spread side by its cover read WITH the studied weights
    (lean_read), the studied weight present or not; ATS at the side's own juice.
R5  FOOTBALL DOGS +100..+350 ON TODAY'S CHECKS: the own-read rule, the re-based weighed check (wdb), the dog score;
    the board's dogs by kind; the floor's NFL dogs.
Train = 2018-22 seasons / held out = 2023-26. Placebo: a random same-size set drawn season by season from the cell's pool.
Usage: python results/studies/football_1114/r2_r5_cells.py > results/studies/football_1114/r2_r5_out.txt"""
import flib as F

ML = F.replay(markets=("ml",))
SP = F.replay(markets=("spread",))
SIDE = {}
for lg in ("nfl", "ncaaf"):
    for s in F.sides(lg):
        SIDE[(s["id"], s["side"])] = s
for r in ML + SP:
    s = SIDE.get((r["gid"], r["side"])) or {}
    r["conf_game"], r["week"] = s.get("conf_game"), s.get("week")
    r["neutral"] = str(r.get("neutral_g")) == "1"
    r["month"] = int(r["date"][5:7])
    r["need"] = 1 / r["dec"]
    r["o_m"] = None if r["own"] is None else (r["own"] - r["need"]) * 100          # own read over the price, points
    r["w_m"] = None if r.get("w_p") is None else (r["w_p"] - r["need"]) * 100       # weighed read over the price
    r["nv_m"] = None if r.get("p_market") is None else (r["p_market"] - r["need"]) * 100
N = [0]


def L(name, rs, pool=None, worse=False):
    N[0] += 1
    x = F.rline(name, rs)
    if pool is not None and x["n"] >= 25:
        print(f"      placebo ({'as badly' if worse else 'as well'}): {F.rplacebo(rs, pool, worse=worse)} of 2000")
    return x


def favs(lg, lo=-150, hi=-101):
    return [r for r in ML if r["league"] == lg and lo <= r["odds"] <= hi and not r.get("trap")]


for lg, tag in (("nfl", "R2"), ("ncaaf", "R3")):
    P = favs(lg)
    print(f"\n=================== {tag} {lg.upper()} FAVORITES -101..-150 ({len(P)} candidates) ===================")
    L("every one", P)
    L("posted as a unit play", [r for r in P if r.get("kind")], pool=P)
    L("not posted", [r for r in P if not r.get("kind")])
    L("posted as a lean", [r for r in P if r.get("lean") and not r.get("kind")], pool=P)
    print(" -- the own read over the price (points)")
    for lo, hi in ((-99, -3), (-3, 0), (0, 1), (1, 3), (3, 6), (6, 99)):
        L(f"own {lo}..{hi}", [r for r in P if r["o_m"] is not None and lo <= r["o_m"] < hi])
    print(" -- the weighed read over the price")
    for lo, hi in ((-99, -3), (-3, 0), (0, 1), (1, 3), (3, 99)):
        L(f"weighed {lo}..{hi}", [r for r in P if r["w_m"] is not None and lo <= r["w_m"] < hi])
    print(" -- together")
    B = [r for r in P if r["o_m"] is not None and r["w_m"] is not None]
    L("own 1+ AND weighed 0+ over", [r for r in B if r["o_m"] >= 1 and r["w_m"] >= 0], pool=P)
    L("own 1+ AND weighed 0+ over, NOT posted", [r for r in B if r["o_m"] >= 1 and r["w_m"] >= 0 and not r.get("kind")], pool=P)
    L("own 0+ AND weighed 1+ over", [r for r in B if r["o_m"] >= 0 and r["w_m"] >= 1], pool=P)
    L("weighed 0+ over, own UNDER", [r for r in B if r["o_m"] < 0 and r["w_m"] >= 0], pool=P)
    L("own 0+ over, weighed UNDER", [r for r in B if r["o_m"] >= 0 and r["w_m"] < 0], pool=P)
    L("both under", [r for r in B if r["o_m"] < 0 and r["w_m"] < 0], pool=P, worse=True)
    L("blend 56%+ (Lock-grade), own over", [r for r in P if r["p"] >= 0.56 and (r["o_m"] or -1) >= 0], pool=P)
    L("good() + real_value, own over (the play bar minus the edge size)", [r for r in P if r.get("good") and r.get("real_value") and r.get("own_beats")], pool=P)
    print(" -- the calendar / site (every candidate, then own 0+ over)")
    for nm, ms in (("Aug-Sep", (8, 9)), ("Oct-Nov", (10, 11)), ("Dec-Jan", (12, 1))):
        L(f"{nm}", [r for r in P if r["month"] in ms])
        L(f"{nm}, own 0+ over", [r for r in P if r["month"] in ms and (r["o_m"] or -1) >= 0])
        L(f"{nm}, posted", [r for r in P if r["month"] in ms and r.get("kind")])
    for nm, f in (("home", lambda r: r["home"] and not r["neutral"]), ("road", lambda r: not r["home"] and not r["neutral"])):
        L(f"{nm}", [r for r in P if f(r)])
        L(f"{nm}, own 0+ over", [r for r in P if f(r) and (r["o_m"] or -1) >= 0])
        L(f"{nm}, posted", [r for r in P if f(r) and r.get("kind")])
    if lg == "ncaaf":
        L("conference game", [r for r in P if r["conf_game"]])
        L("non-conference", [r for r in P if r["conf_game"] is False])
        RA = [r for r in P if any("rule a" in (x or "").lower() or "off a win" in (x or "").lower() for x in r.get("reasons") or [])]
        L("a reason names the off-a-win / off-a-loss spot (rule A)", RA, pool=P)
    print(" -- the posted ones by units")
    for u in (0.5, 1, 2, 3):
        x = [r for r in P if r.get("kind") and r.get("units") == u]
        if x:
            L(f"posted at {u}u", x)
    print(" -- bigger favorites -151..-250 (never a play - the -150 rule; for the record)")
    Q = favs(lg, -250, -151)
    L("every one", Q)
    L("own 3+ AND weighed 0+ over", [r for r in Q if (r["o_m"] or -9) >= 3 and (r["w_m"] if r["w_m"] is not None else -9) >= 0])

print("\n=================== R4 FOOTBALL SPREADS (ATS at the side's own juice) ===================")
for lg in ("nfl", "ncaaf"):
    S = [r for r in SP if r["league"] == lg]
    print(f" -- {lg.upper()} ({len(S)} spread sides)")
    L("every side", S)
    L("the board's spread leans", [r for r in S if r.get("lean") and not r.get("kind")], pool=S)
    L("the night spread picks (Mon / Thu)", [r for r in S if r.get("night")])
    L("spread unit plays (any kind)", [r for r in S if r.get("kind")])
    W = [r for r in S if (r.get("sw") or 0) > 1e-9]
    L("a studied spread weight on the side", W, pool=S)
    L("no studied weight for the side", [r for r in S if (r.get("sw") or 0) <= 1e-9])
    for lo, hi in ((0.50, 0.53), (0.53, 0.55), (0.55, 0.57), (0.57, 0.60), (0.60, 1)):
        L(f"lean_read {lo:.2f}..{hi:.2f}", [r for r in S if r.get("lean_read") is not None and lo <= r["lean_read"] < hi])
        L(f"lean_read {lo:.2f}..{hi:.2f} with a studied weight", [r for r in W if r.get("lean_read") is not None and lo <= r["lean_read"] < hi])
    for nm, f in (("fav", lambda r: (r.get("line") or 0) < 0), ("dog", lambda r: (r.get("line") or 0) > 0)):
        for hn, h in (("home", lambda r: r["home"] and not r["neutral"]), ("road", lambda r: not r["home"] and not r["neutral"])):
            L(f"lean {hn} {nm}", [r for r in S if r.get("lean") and f(r) and h(r)])
    if W:
        sw = sorted(W, key=lambda r: -(r["sw"] if isinstance(r["sw"], (int, float)) else 0))
        top = sw[:max(25, len(sw) // 5)]
        L("the top fifth by studied weight", top, pool=S)

print("\n=================== R5 FOOTBALL DOGS +100..+350 ON TODAY'S CHECKS ===================")
for lg in ("nfl", "ncaaf"):
    D = [r for r in ML if r["league"] == lg and 100 <= r["odds"] <= 350 and not r.get("trap")]
    print(f" -- {lg.upper()} ({len(D)} dogs)")
    L("every dog", D)
    L("own read over the price", [r for r in D if (r["o_m"] or -1) > 0], pool=D)
    L("own over + the weighed check (dog_own_ok)", [r for r in D if r.get("dog_own_ok")], pool=D)
    L("dog_own_ok, dog score 4+", [r for r in D if r.get("dog_own_ok") and (r.get("dog_score") or -9) >= 4], pool=D)
    L("dog_own_ok, dog score 8+", [r for r in D if r.get("dog_own_ok") and (r.get("dog_score") or -9) >= 8], pool=D)
    L("weighed check passes, own read under", [r for r in D if r.get("wdb") and (r["o_m"] or -1) <= 0], pool=D)
    for lo, hi in ((-99, 0), (0, 2), (2, 4), (4, 6), (6, 8), (8, 99)):
        L(f"dog score {lo}..{hi}", [r for r in D if r.get("dog_score") is not None and lo <= r["dog_score"] < hi])
    for k in sorted({r["kind"] for r in D if r.get("kind")}):
        L(f"posted: {k}", [r for r in D if r.get("kind") == k], pool=D)
    for nm, f in (("home", lambda r: r["home"] and not r["neutral"]), ("road", lambda r: not r["home"] and not r["neutral"])):
        L(f"{nm}, dog_own_ok", [r for r in D if f(r) and r.get("dog_own_ok")])
    for b, lo, hi in (("+100..+150", 100, 150), ("+151..+200", 151, 200), ("+201..+350", 201, 350)):
        L(f"{b}, dog_own_ok", [r for r in D if lo <= r["odds"] <= hi and r.get("dog_own_ok")])
print(f"\n{N[0]} cells printed (x3 halves) - about {N[0] * 3 // 20} would clear |z| 2 by luck.")
