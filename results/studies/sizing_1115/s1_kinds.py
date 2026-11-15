"""11/15 - SIZING BY KIND: every unit kind on both replay boards (sizing_1114/lib.py: R1 = the 10/30 rows, R2 = the 11/12
deep-program rows on today's code), flat 1u vs its price by half, then the question yesterday's study did not ask:
IF THE SIZES WERE FIT TO MAXIMIZE PROFIT ON THE TRAIN HALF, WOULD THEY MAKE MORE ON THE HELD-OUT HALF THAN TODAY'S?
 (a) the kind table (today's units, W-L, flat ROI train / held, z, seasons)
 (b) "Kelly by kind": each kind's quarter-Kelly stake from its TRAIN win rate and average price, shrunk toward no edge
     (the train edge x n / (n + 150)), rounded to ½u, ½u..3u (0 = the kind is off) - applied to the HELD half, against
     today's sizes on the same held plays, at the SAME total risk (scaled) and raw.
 (c) sizing by EDGE instead of by kind: quarter-Kelly on the read each play's units ride on (sports.kelly_units' rule),
     held half - the engine's old sizing.
Usage: python results/studies/sizing_1115/s1_kinds.py > results/studies/sizing_1115/s1_kinds.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sizing_1114"))
import lib as L  # noqa: E402
import s1_star as S  # noqa: E402

FOOT = ("nfl", "ncaaf")


def kind_of(r, u, k):
    """the size cells the engine really has (sports.units_for's branches)."""
    if k == "lock":
        return "lock football 1u" if r["league"] in FOOT else f"lock {u:g}u"
    if k == "dog":
        if r["league"] == "nba":
            return f"dog nba {u:g}u"
        return "dog short 2u (+100..+150)" if u == 2.0 else "dog long ½u (+151..+350)"
    return {"backup": "backup lock ½u", "play": "value play ½u", "dogplay": "runner-up dog ½u", "nbafav": "nba fav play 1u",
            "nbafloor": "nba floor ½u", "floor": "floor ½u", "floorfb": "floor fallback ½u", "solo": f"solo {u:g}u"}.get(k, k)


def kelly_q(p, dec):
    k = (p * dec - 1) / (dec - 1)
    return 0.0 if k <= 0 else min(5.0, max(0.5, round(0.25 * k / 0.01 * 2) / 2))


def main():
    for name, (board, _by) in L.boards().items():
        st = {(d, r["team"], k) for d, r, u, k in S.stars(board, S.today)}
        plays = [(d, r, u, k) for d in sorted(board) for r, u, k in board[d]]
        print("=" * 30, f"BOARD {name}: {len(plays)} unit plays")
        print("(a) THE KIND TABLE (flat 1u vs the price; then its units at today's size)")
        cells = defaultdict(list)
        for d, r, u, k in plays:
            cells[kind_of(r, u, k)].append((d, r, u))
        for c in sorted(cells, key=lambda c: -len(cells[c])):
            L.line(c, cells[c])
            L.line("    ... at its units", cells[c], units=True)
        L.line("THE ⭐ (today's rule), flat", [(d, r, u) for d, r, u, k in plays if (d, r["team"], k) in st])

        print("(b) KELLY BY KIND, FIT ON TRAIN -> HELD")
        fit = {}
        for c, rs in cells.items():
            tr = [x for x in rs if L.half(x[0]) == "train"]
            n = len(tr)
            if n < 15:
                fit[c] = None                                   # too few to fit: keep today's size
                continue
            w = sum(r["result"] == "won" for _, r, _ in tr)
            l = sum(r["result"] == "lost" for _, r, _ in tr)
            dec = sum(r["dec"] for _, r, _ in tr) / n
            p0 = 1 / dec                                        # no edge
            p = w / max(1, w + l)
            ps = p0 + (p - p0) * n / (n + 150)                  # shrunk toward no edge
            fit[c] = kelly_q(ps, dec)
            if fit[c] > 3:
                fit[c] = 3.0
            print(f"     {c:30s} train n {n:3d} won {100 * p:4.1f}% at an average {dec:.2f} -> shrunk {100 * ps:4.1f}% -> {fit[c]:g}u"
                  f" (today {sorted({u for _, _, u in rs})})")
        held = [(d, r, u, k) for d, r, u, k in plays if L.half(d) == "held"]

        def tot(fn):
            net = risk = 0.0
            per = defaultdict(float)
            for d, r, u, k in held:
                nu = fn(d, r, u, k)
                net += L.pnl(r, nu)
                risk += nu
                per[d] += L.pnl(r, nu)
            return net, risk, L.worst(per, sorted(per))
        today = lambda d, r, u, k: max(1.0, u) if (d, r["team"], k) in st else u   # noqa: E731
        byk = lambda d, r, u, k: (fit[kind_of(r, u, k)] if fit[kind_of(r, u, k)] is not None else u)   # noqa: E731
        edge = lambda d, r, u, k: kelly_q(L.read_of(r, k), r["dec"]) or 0.5   # noqa: E731
        own = lambda d, r, u, k: (kelly_q((r["edge_own"] + 1) / r["dec"], r["dec"]) or 0.5) if r.get("edge_own") is not None else 0.5   # noqa: E731
        base = tot(today)
        for nm, fn in (("today's sizes (+ the ⭐ raise)", today), ("Kelly by kind, fit on train", byk),
                       ("(c) quarter-Kelly on the read (by EDGE)", edge), ("(c) quarter-Kelly on the RAW OWN read", own),
                       ("flat ½u on everything", lambda d, r, u, k: 0.5), ("flat 1u on everything", lambda d, r, u, k: 1.0)):
            net, risk, dd = tot(fn)
            sc = base[1] / risk if risk else 0
            print(f"     HELD {nm:40s} {net:+7.1f}u on {risk:6.0f}u ({100 * net / risk:+5.1f}%) worst {dd:+6.1f}u"
                  f" | at today's total risk: {net * sc:+7.1f}u worst {dd * sc:+6.1f}u")


if __name__ == "__main__":
    main()
