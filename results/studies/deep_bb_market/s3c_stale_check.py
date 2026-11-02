"""S3c - IS THE COLLEGE 1H EDGE A MISPRICED DERIVATIVE, OR A STALE NUMBER?

Our 1H lines come from Action Network's boxscore 'latest_odds.firsthalf' (one number, its own time stamp unknown); the
full-game close is AN's consensus (book 15). If the 1H number was hung off an EARLIER full line, then 'the 1H line is
off the full close' = 'the full line moved after the 1H number was taken' - the close's information, not a derivative
the books misprice, and not bettable unless the book's own 1H line really lags.
Tests (2023-25, ESPN/AN's ML open as the earlier full line, turned into a spread with a map fit on train 2018-22):
  1. regress the 1H spread on the CLOSING full spread and the OPEN-implied full spread - weight on the open = stale;
  2. the s3b edge recomputed from the OPEN-implied full spread (what the 1H number 'should' be at the open);
  3. the s3b edge on games where the full ML did not move open -> close (< 1 pt) - the clean derivative test."""
import math

import lib

out = lib.Out("s3c_stale_check", train=(2023,), held=(2024, 2025))
R = [x for x in lib.nc_sides() if x["stype"] == "2" and x["season"] >= 2018 and x.get("sp") and x.get("p")
     and 0.02 < x["p"] < 0.98]


def lsq(X, y):
    k = len(X[0])
    A = [[sum(r[i] * r[j] for r in X) for j in range(k)] for i in range(k)]
    b = [sum(r[i] * yy for r, yy in zip(X, y)) for i in range(k)]
    M = [A[i] + [b[i]] for i in range(k)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        for r in range(k):
            if r != c:
                f = M[r][c] / M[c][c]
                for j in range(c, k + 1):
                    M[r][j] -= f * M[c][j]
    return [M[i][k] / M[i][i] for i in range(k)]


lg = lambda p: math.log(p / (1 - p))
tr = [x for x in R if x["season"] in lib.TRAIN]
w = lsq([[lg(x["p"]), lg(x["p"]) ** 3] for x in tr], [x["sp"] for x in tr])
spmap = lambda p: w[0] * lg(p) + w[1] * lg(p) ** 3
out.note(f"ML -> spread map (train): spread = {w[0]:+.3f}*logit {w[1]:+.4f}*logit^3; "
         f"check: p .75 -> {spmap(.75):+.1f}, p .5 -> {spmap(.5):+.1f}")
H = [x for x in R if x.get("po") and 0.02 < x["po"] < 0.98 and x.get("h1sp") is not None and x.get("h1m") is not None
     and x["season"] in (2023, 2024, 2025) and lib.h1_ok(x["sp"], x["h1sp"])]
for x in H:
    x["sp_open"] = spmap(x["po"])
    x["sp_closeml"] = spmap(x["p"])
out.h("1. the 1H spread regressed on the full CLOSE spread and the OPEN-implied full spread (2023-25)")
c = lsq([[x["sp"], x["sp_open"]] for x in H], [x["h1sp"] for x in H])
out.note(f"h1 = {c[0]:+.3f}*close_spread {c[1]:+.3f}*open_spread  (a fresh 1H number: all weight on the close)")
c2 = lsq([[x["sp_closeml"], x["sp_open"]] for x in H], [x["h1sp"] for x in H])
out.note(f"h1 = {c2[0]:+.3f}*closeML_spread {c2[1]:+.3f}*openML_spread  (same map both sides - apples to apples)")
mv = [x for x in H if abs(x["p"] - x["po"]) >= 0.04]
c3 = lsq([[x["sp_closeml"], x["sp_open"]] for x in mv], [x["h1sp"] for x in mv])
out.note(f"games whose full ML moved 4+ pts: h1 = {c3[0]:+.3f}*closeML_spread {c3[1]:+.3f}*openML_spread on {len(mv)}")

K = 0.547   # the s3b train fit (college): fair 1H margin = -0.547 * the side's full spread
out.h("2. the edge vs the CLOSE full spread (s3b) and vs the OPEN-implied full spread, edge 1+")
for lab, f in (("vs CLOSE", lambda x: -K * x["sp"] + x["h1sp"]), ("vs OPEN-implied", lambda x: -K * x["sp_open"] + x["h1sp"]),
               ("vs CLOSE-ML-implied", lambda x: -K * x["sp_closeml"] + x["h1sp"])):
    for thr in (0.75, 1.0, 1.5):
        S = [x for x in H if f(x) >= thr]
        out.bets(f"{lab} edge {thr}+", [(x["season"], lib.ats_pl(x["h1m"] + x["h1sp"], x["h1odds"])) for x in S])
out.h("3. the CLEAN test - the full ML did NOT move (|close - open| < 1 pt), edge vs the close")
F = [x for x in H if abs(x["p"] - x["po"]) < 0.01]
for thr in (0.5, 0.75, 1.0):
    S = [x for x in F if -K * x["sp"] + x["h1sp"] >= thr]
    out.bets(f"no move, edge {thr}+", [(x["season"], lib.ats_pl(x["h1m"] + x["h1sp"], x["h1odds"])) for x in S])
F = [x for x in H if abs(x["p"] - x["po"]) >= 0.03]
for thr in (0.5, 0.75, 1.0):
    S = [x for x in F if -K * x["sp"] + x["h1sp"] >= thr]
    out.bets(f"moved 3+, edge {thr}+", [(x["season"], lib.ats_pl(x["h1m"] + x["h1sp"], x["h1odds"])) for x in S])
    out.bets(f"    ...of those, the side the full ML moved TO", [(x["season"], lib.ats_pl(x["h1m"] + x["h1sp"], x["h1odds"])) for x in S if x["p"] > x["po"]])
out.save()
