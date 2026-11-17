"""11/17 FULL SWEEP - S6 THE THIN LOCK ROWS. The day's best Lock-grade favorite whose own read beats the price by under
3c is never the Lock (the 10/29 rule; football excepted from 11/16) - it rides as a ½u value play only when the value
bar clears (the read 1+ point over the price), else it is off the board. On R1 (the old read) those rows lose; on R2
(TODAY's code) they are most of the Lock-grade favorites the engine finds. What are they, which of them post today, and
does any cell of the ones left off earn a ½u play (the football rule's twin in another sport)?
Both replay boards (sizing_1114/lib.py); five checks, the pool = every thin Lock row of that board.
Usage: python results/studies/sweep_1117/s2_thin_lock.py > results/studies/sweep_1117/s2_thin_lock.out"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "sizing_1114"))
import lib as L  # noqa: E402
import slib  # noqa: E402

half = L.half
om = lambda r: -99 if L.own_margin(r) is None else 100 * L.own_margin(r)  # noqa: E731
keep = {}
for bn, (board, by) in L.boards().items():
    print("=" * 30, "BOARD", bn)
    thin = [(d, r, 0.5) for d in sorted(by) for r in by[d] if r.get("kind") == "lock" and r.get("thin")]
    full = [(d, r, 1.0) for d in sorted(by) for r in by[d] if r.get("kind") == "lock" and not r.get("thin")]
    posted = {id(r) for d, ps in board.items() for r, u, k in ps}
    print("thin Lock rows by sport:", dict(collections.Counter(r["league"] for _, r, _ in thin)), "| not-thin Lock rows:",
          dict(collections.Counter(r["league"] for _, r, _ in full)))
    slib.five("every thin Lock row", thin, None, half)
    slib.five("every NOT-thin Lock row (the Lock as posted)", full, None, half)
    slib.five("thin rows POSTED today (a ½u value play: the 1-point bar)", [x for x in thin if id(x[1]) in posted], thin, half)
    off = [x for x in thin if id(x[1]) not in posted]
    slib.five("thin rows LEFT OFF the board today", off, thin, half)
    cells = [(f"left off, {lg}", (lambda r, lg=lg: r["league"] == lg)) for lg in ("nhl", "nba", "mlb", "ncaab", "nfl", "ncaaf")] + [
        ("left off, hockey at -150..-135", lambda r: r["league"] == "nhl" and r["odds"] <= -135),
        ("left off, hockey at -134..-120", lambda r: r["league"] == "nhl" and r["odds"] > -135),
        ("left off, hockey at home", lambda r: r["league"] == "nhl" and r["home"]),
        ("left off, hockey on the road", lambda r: r["league"] == "nhl" and not r["home"]),
        ("left off, the read 0-0.5 points over the price", lambda r: 0 <= om(r) < 0.5),
        ("left off, the read 0.5-1 point over the price", lambda r: 0.5 <= om(r) < 1),
        ("left off, the read UNDER the price", lambda r: -90 < om(r) < 0),
        ("left off, baseball", lambda r: r["league"] == "mlb"),
        ("left off, hockey Oct-Dec", lambda r: r["league"] == "nhl" and r["date"][5:7] in ("10", "11", "12")),
        ("left off, hockey Jan-Apr", lambda r: r["league"] == "nhl" and r["date"][5:7] in ("01", "02", "03", "04"))]
    for nm, f in cells:
        c = [x for x in off if f(x[1])]
        if len([x for x in c if half(x[0]) != "live"]) >= 10:
            keep[(bn, nm)] = slib.five(nm, c, thin, half)
    hk = [x for x in off if x[1]["league"] == "nhl" and half(x[0]) != "live"]
    if hk:
        net = sum(slib.flat(r) * 0.5 for _, r, _ in hk)
        tr = sum(slib.flat(r) * 0.5 for d, r, _ in hk if half(d) == "train")
        print(f"   every left-off hockey thin Lock row at ½u: {net:+.1f}u on {0.5 * len(hk):.1f}u (train {tr:+.1f}u / held {net - tr:+.1f}u), "
              f"worst stretch {0.5 * slib.worst(hk):+.1f}u")
        seas = collections.defaultdict(float)
        for d, r, _ in hk:
            seas[slib.season(d)] += 0.5 * slib.flat(r)
        print("      by season at ½u: " + "  ".join(f"{s} {v:+.1f}u" for s, v in sorted(seas.items())))
print("=" * 30, "VERDICT (a cell has to CLEAR on both boards)")
for nm in sorted({n for _, n in keep}):
    v = {b: keep[(b, n)]["clears"] for b, n in keep if n == nm}
    print(f"  {nm:52s} " + "  ".join(f"{b}: {'CLEARS' if x else 'no'}" for b, x in sorted(v.items())))
