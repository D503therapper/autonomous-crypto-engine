"""THE COLLEGE OWN READ, RECALIBRATED (10/16 - SPORTS_FINDINGS.md): can a calibration of sports_model.own_p fix a college
read that says 48% where the market says 24% (BYU +300 at Notre Dame)?

Walk-forward: every July 1 the params are re-tuned on the games before it (sm.tune), the season's reads come from the
ratings as they stood (sm.replay). Four recalibrations are fit on 2018-22 and graded blind on 2023-26: shrink toward
the no-vig market (logit p = logit(mkt) + a * (logit(own) - logit(mkt))), shrink + the market's own favorite bias,
temperature (c + d * logit(own)) and isotonic (PAV) - calibration table, Brier / log loss vs the market, and the blind
ROI of the sides each read says beat the closing price (+100..+300 and -150..-101).

    python tools/ncaaf_own_calibration_study.py [own|tue]     (tue = the Tuesday-known read the early spots use)
"""
import math  # noqa: F401
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sports_data as sd  # noqa: E402
import sports_model as sm  # noqa: E402

LG, TRAIN_TO, SEASONS = "ncaaf", 2022, range(2018, 2027)
L, SG = sm.logit, sm.sigmoid


def season_of(start):
    return int(start[:4]) if int(start[5:7]) >= 7 else int(start[:4]) - 1


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def rows():
    games = sd.load_games(LG)
    fin = sm.finals(games, LG)
    out = []
    for S in SEASONS:
        p = sm.tune({k: g for k, g in games.items() if g.get("start", "") < f"{S}-07-01"}, LG)
        if not p or "w" not in p:
            continue
        _, played = sm.replay(fin, p["k"], p["hfa"], LG)
        for g, f, y, _ in played:
            mk = sm.market_p(g)
            if season_of(g["start"]) != S or y == 0.5 or mk is None:
                continue
            out.append({"id": g["id"], "S": S, "y": y, "mk": mk, "own": sm.own_p(p, f),
                        "tue": sm.own_p(p, {**f, "inj": 0.0, "key": 0.0, "weather": 0.0, "cold": 0.0}),
                        "oh": sm._int(g.get("ml_home")), "oa": sm._int(g.get("ml_away"))})
        print(f"season {S}: k={p['k']} hfa={p['hfa']} trust={p['trust']:.3f}")
    return out


def fit_iso(R, read):
    out = []
    for p, y in sorted((r[read], r["y"]) for r in R):
        out.append([p, y, 1])
        while len(out) > 1 and out[-2][1] / out[-2][2] >= out[-1][1] / out[-1][2]:
            a = out.pop()
            out[-1] = [a[0], out[-1][1] + a[1], out[-1][2] + a[2]]
    return [(b[0], b[1] / b[2]) for b in out]


def iso_apply(iso, p):
    return min(max(next((v for hi, v in iso if p <= hi), iso[-1][1]), 0.02), 0.98)


def main(read="own"):
    R = rows()
    train, blind = [r for r in R if r["S"] <= TRAIN_TO], [r for r in R if r["S"] > TRAIN_TO]
    y_t, off = [r["y"] for r in train], [L(r["mk"]) for r in train]
    a = sm.fit_logistic_offset([[L(r[read]) - L(r["mk"])] for r in train], y_t, off, prior=[0.0], lam=0.5)[0]
    a2 = sm.fit_logistic_offset([[L(r[read]) - L(r["mk"]), L(r["mk"])] for r in train], y_t, off, prior=[0.0, 0.0], lam=0.5)
    tp = sm.fit_logistic([[1.0, L(r[read])] for r in train], y_t, prior=[0.0, 1.0], lam=0.5)
    iso = fit_iso(train, read)
    print(f"\nread={read}: train {len(train)} (2018-22) blind {len(blind)} (2023-26)")
    print(f"fits: shrink a={a:.3f} | shrink+bias a={a2[0]:.3f} b={a2[1]:.3f} | temperature c={tp[0]:.3f} d={tp[1]:.3f} | isotonic {len(iso)} steps")
    reads = {"market": lambda r: r["mk"], "own raw": lambda r: r[read],
             "shrink": lambda r: SG(L(r["mk"]) + a * (L(r[read]) - L(r["mk"]))),
             "shrink+bias": lambda r: SG(L(r["mk"]) + a2[0] * (L(r[read]) - L(r["mk"])) + a2[1] * L(r["mk"])),
             "temperature": lambda r: SG(tp[0] + tp[1] * L(r[read])), "isotonic": lambda r: iso_apply(iso, r[read])}
    print("\nblind Brier / log loss (home side):")
    for name, f in reads.items():
        ps = [(f(r), r["y"]) for r in blind]
        print(f"  {name:12s} Brier {sum((p - y) ** 2 for p, y in ps) / len(ps):.4f} logloss {sm.logloss(ps):.4f}")
    for name in ("own raw", "shrink", "temperature", "isotonic"):
        f, agg = reads[name], defaultdict(lambda: [0, 0.0, 0.0])
        for r in blind:
            p = f(r)
            for pp, yy in ((p, r["y"]), (1 - p, 1 - r["y"])):
                b = min(int(pp * 10), 9)
                agg[b][0] += 1
                agg[b][1] += pp
                agg[b][2] += yy
        print(f"\n  calibration, blind - {name}: " + "  ".join(
            f"{b * 10}s: said {100 * s / n:.1f} won {100 * w / n:.1f} ({n})" for b, (n, s, w) in sorted(agg.items())))
        agg = defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0.0])
        for r in blind:
            p = f(r)
            h = p > r["mk"]
            pp, m, yy, o = (p, r["mk"], r["y"], r["oh"]) if h else (1 - p, 1 - r["mk"], 1 - r["y"], r["oa"])
            gap = (pp - m) * 100
            b = "0-2" if gap < 2 else "2-5" if gap < 5 else "5-10" if gap < 10 else "10-15" if gap < 15 else "15-20" if gap < 20 else "20-25" if gap < 25 else "25+"
            agg[b][0] += 1
            agg[b][1] += pp
            agg[b][2] += m
            agg[b][3] += yy
            agg[b][4] += (dec(o) - 1) if yy else -1
        print(f"  the side it likes more than the market, by the gap - {name}: " + "  ".join(
            f"{b}: read {100 * s / n:.1f} mkt {100 * m / n:.1f} won {100 * w / n:.1f} ROI {100 * u / n:+.1f}% ({n})"
            for b, (n, s, m, w, u) in agg.items()))
    print("\nblind ROI at the close, the sides whose read beats the price:")
    for lo, hi, lab in ((100, 300, "dogs +100..+300"), (-150, -101, "favorites -150..-101")):
        for name, f in reads.items():
            n = w = 0
            u = 0.0
            for r in blind:
                p = f(r)
                for pp, yy, o in ((p, r["y"], r["oh"]), (1 - p, 1 - r["y"], r["oa"])):
                    if o is not None and lo <= o <= hi and (name == "market" or pp * dec(o) > 1):
                        n += 1
                        w += yy
                        u += (dec(o) - 1) if yy else -1
            print(f"  {lab} {name if name != 'market' else 'every side':12s} n={n:4d} {w:.0f}-{n - w:.0f} ROI {100 * u / n:+.1f}%" if n else f"  {lab} {name:12s} n=0")
    o, m = 0.48, 0.24
    print(f"\nBYU 48% / market 24% -> shrink {100 * SG(L(m) + a * (L(o) - L(m))):.1f}% | temperature {100 * SG(tp[0] + tp[1] * L(o)):.1f}% | isotonic {100 * iso_apply(iso, o):.1f}%")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "own")
