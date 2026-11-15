"""11/15 - THE WHOLE BOARD UNDER EACH SIZING PROCESS (both replay boards; sizing_1114/lib.py). Yesterday (sizing_1114)
asked "does any cell earn MORE"; this asks the process questions the owner's "best sizing process for maximum profits"
needs:
 (A) today's sizes vs the single-kind changes still open (the football Lock ½u, the big-gap 1u Lock, the NBA favorite
     play at 2u, the NBA floor at 1u, value plays off, the long Dog off)
 (B) A DAILY RISK CAP: at most N units a day - the lowest-trust plays dropped first (the ⭐'s kind order) or every play
     scaled down
 (C) the day's risk as it is: how many units a day, the worst day, how the losing stretches happen
 (D) FLAT UNITS vs A BANKROLL FRACTION: 1u = $1,000 flat forever; the owner's rule (1u = $1,000 on $100,000, +$500 per
     full $50,000 - sports' unit ladder); 1u = 1% of the roll re-set every day; the same at 0.75% / 1.5% / 2% - dollars
     at the end and the deepest drop from a peak in % of the roll.
Usage: python results/studies/sizing_1115/s2_schedules.py > results/studies/sizing_1115/s2_schedules.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sizing_1114"))
import lib as L  # noqa: E402
import s1_star as S  # noqa: E402

FOOT = ("nfl", "ncaaf")
KR = S.KR


def star_fn(board):
    st = {(d, r["team"], k) for d, r, u, k in S.stars(board, S.today)}
    return lambda d, r, u, k: max(1.0, u) if (d, r["team"], k) in st else u


def capped(board, star, cap, how):
    """{(d, team, kind): units} under a daily cap. how = 'drop' (the lowest-trust plays lose their units first, ½u at a
    time from the bottom) or 'scale' (every play x cap / day risk, to the nearest ½u, ½u at least)."""
    out = {}
    for d, ps in board.items():
        us = [(r, star(d, r, u, k), k) for r, u, k in ps]
        tot = sum(u for _, u, _ in us)
        if tot <= cap:
            for r, u, k in us:
                out[(d, r["team"], k)] = u
            continue
        if how == "scale":
            for r, u, k in us:
                out[(d, r["team"], k)] = max(0.5, round(u * cap / tot * 2) / 2)
            continue
        order = sorted(us, key=lambda x: (KR.get(x[2], 9), -x[1]))
        left = cap
        for r, u, k in order:
            nu = min(u, left)
            out[(d, r["team"], k)] = nu
            left -= nu
    return out


def run(name, board):
    star = star_fn(board)
    T = lambda d, r, u, k, ps: star(d, r, u, k)   # noqa: E731
    gapv = lambda r: L.sv.gap(r)   # noqa: E731
    print("(A) single-kind changes")
    V = [
        ("TODAY (today's sizes + the ⭐ raise)", T),
        ("   football Locks ½u (today 1u)", lambda d, r, u, k, ps: 0.5 if k == "lock" and r["league"] in FOOT else T(d, r, u, k, ps)),
        ("   the 1u Lock (own read 7+ over the market) at ½u", lambda d, r, u, k, ps: 0.5 if k == "lock" and u == 1.0 and r["league"] not in FOOT else T(d, r, u, k, ps)),
        ("   the 1u Lock (7+ over the market) OFF", lambda d, r, u, k, ps: 0.0 if k == "lock" and u == 1.0 and r["league"] not in FOOT else T(d, r, u, k, ps)),
        ("   every Lock 1u (no 2u Lock)", lambda d, r, u, k, ps: min(1.0, T(d, r, u, k, ps)) if k == "lock" else T(d, r, u, k, ps)),
        ("   the NBA favorite play 2u (today 1u)", lambda d, r, u, k, ps: 2.0 if k == "nbafav" else T(d, r, u, k, ps)),
        ("   the NBA favorite play ½u", lambda d, r, u, k, ps: 0.5 if k == "nbafav" else T(d, r, u, k, ps)),
        ("   the NBA floor 1u (today ½u)", lambda d, r, u, k, ps: 1.0 if k == "nbafloor" else T(d, r, u, k, ps)),
        ("   value plays OFF", lambda d, r, u, k, ps: 0.0 if k == "play" else T(d, r, u, k, ps)),
        ("   the long Dog (+151..+350) OFF", lambda d, r, u, k, ps: 0.0 if k == "dog" and r["league"] != "nba" and r["odds"] > 150 else T(d, r, u, k, ps)),
        ("   the short Dog 1u (today 2u)", lambda d, r, u, k, ps: 1.0 if k == "dog" and u == 2.0 else T(d, r, u, k, ps)),
        ("   the general floor 1u (today ½u)", lambda d, r, u, k, ps: max(1.0, T(d, r, u, k, ps)) if k in ("floor", "floorfb") else T(d, r, u, k, ps)),
        ("   the general floor OFF", lambda d, r, u, k, ps: 0.0 if k in ("floor", "floorfb") else T(d, r, u, k, ps)),
        ("   every play flat ½u", lambda d, r, u, k, ps: 0.5),
        ("   every play flat 1u", lambda d, r, u, k, ps: 1.0),
    ]
    base = None
    for nm, fn in V:
        o = L.schedule(nm, board, fn)
        base = base or o
    print("(B) a daily risk cap")
    for cap in (2.0, 3.0, 4.0, 5.0, 6.0):
        for how in ("drop", "scale"):
            m = capped(board, star, cap, how)
            L.schedule(f"   at most {cap:g}u a day ({how})", board, lambda d, r, u, k, ps: m[(d, r["team"], k)])
    print("(C) the day's risk as it is (train + held)")
    risk, net = defaultdict(float), defaultdict(float)
    for d, ps in board.items():
        if L.half(d) == "live":
            continue
        for r, u, k in ps:
            nu = star(d, r, u, k)
            risk[d] += nu
            net[d] += L.pnl(r, nu)
    ds = sorted(d for d in board if L.half(d) != "live")
    rs = sorted(risk.get(d, 0.0) for d in ds)
    n = len(rs)
    print(f"   board days {n}; units risked a day: average {sum(rs) / n:.2f}, median {rs[n // 2]:g}, 90% of days {rs[int(n * .9)]:g} or less, "
          f"the most {rs[-1]:g}; days over 4u: {sum(x > 4 for x in rs)}, over 5u: {sum(x > 5 for x in rs)}")
    for lo, hi in ((0.01, 1.0), (1.01, 2.0), (2.01, 3.0), (3.01, 4.0), (4.01, 99)):
        dd = [d for d in ds if lo <= risk.get(d, 0) <= hi]
        if dd:
            tr = [d for d in dd if L.half(d) == "train"]
            he = [d for d in dd if L.half(d) == "held"]
            f = lambda x: f"{sum(net[d] for d in x):+6.1f}u/{sum(risk[d] for d in x):5.0f}u {100 * sum(net[d] for d in x) / max(1e-9, sum(risk[d] for d in x)):+5.1f}%"   # noqa: E731
            print(f"   days risking {lo:.1f}..{hi:g}u: {len(dd):4d} days | ALL {f(dd)} | train {f(tr)} | held {f(he)} | worst day {min(net[d] for d in dd):+.1f}u")
    wd = sorted(ds, key=lambda d: net.get(d, 0))[:5]
    print("   the five worst days: " + "; ".join(f"{d} {net[d]:+.1f}u on {risk[d]:g}u" for d in wd))
    print("(D) flat units vs a bankroll fraction ($100,000 start, train + held, in date order)")

    def roll(rule):
        b, peak, dd = 100000.0, 100000.0, 0.0
        low = b
        for d in ds:
            unit = rule(b)
            b += unit * net.get(d, 0.0)
            peak = max(peak, b)
            dd = min(dd, b / peak - 1)
            low = min(low, b)
        return b, dd, low
    ladder = lambda b: 1000 + 500 * max(0, int((b - 100000) // 50000))   # noqa: E731
    for nm, rule in (("1u = $1,000 flat, forever", lambda b: 1000.0),
                     ("THE OWNER'S LADDER: $1,000, +$500 per full $50,000", ladder),
                     ("1u = 1% of the roll, re-set daily", lambda b: 0.01 * b),
                     ("1u = 0.75% of the roll", lambda b: 0.0075 * b),
                     ("1u = 1.5% of the roll", lambda b: 0.015 * b),
                     ("1u = 2% of the roll", lambda b: 0.02 * b),
                     ("1u = 3% of the roll", lambda b: 0.03 * b)):
        b, dd, low = roll(rule)
        print(f"   {nm:52s} ends ${b:>12,.0f}  deepest drop from a peak {100 * dd:+6.1f}%  lowest ${low:>10,.0f}")


if __name__ == "__main__":
    for name, (board, _by) in L.boards().items():
        print("=" * 30, f"BOARD {name}")
        run(name, board)
