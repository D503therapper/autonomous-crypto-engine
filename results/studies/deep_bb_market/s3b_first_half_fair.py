"""S3b - THE 1ST-HALF LINE vs ITS FAIR NUMBER FROM THE FULL GAME (the s3 share signal done properly).

Fair 1H margin for a side = a + b*spread + c*spread*(total-mean)/10 + d*home, fit by least squares on TRAIN seasons
only (college 2018-22, NBA 2018-20) from the CLOSING full-game spread and total. Edge (points) = fair 1H margin +
the side's 1H spread. Bet the side with edge >= X at its REAL 1H juice (ESPN's 1H odds - often -115 / -115; s3 used
-110 for the dog side, wrong). Graded on the 1st-half score (pushes = 0).
Checks: every season, both leagues, tiers, the price (juice) the bet carries, and the stale-derivative test - does it
live where the FULL-GAME moneyline moved open -> close (the 1H number not following the full game)?"""
import math
from collections import defaultdict

import lib

out = lib.Out("s3b_first_half_fair")


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


def feats(sp, tot, home, tmean):
    return [1.0, sp, sp * ((tot or tmean) - tmean) / 10, home]


def run(lg, sides, train, held):
    out.train, out.held = train, held
    tr = [s for s in sides if s["season"] in train]
    tmean = sum(s["tot"] for s in tr if s["tot"]) / sum(1 for s in tr if s["tot"])
    w = lsq([feats(s["sp"], s["tot"], s["home"], tmean) for s in tr], [s["h1m"] for s in tr])
    out.h(f"{lg}: fair 1H margin = {w[0]:+.2f} {w[1]:+.3f}*spread {w[2]:+.3f}*spread*(total-{tmean:.0f})/10 {w[3]:+.2f}*home"
          f" (sign: spread is the side's, so -0.5 = half the full number)")
    for s in sides:
        s["fair"] = sum(a * b for a, b in zip(w, feats(s["sp"], s["tot"], s["home"], tmean)))
        s["edge"] = s["fair"] + s["h1sp"]
    for lo, hi in ((0.5, 1.0), (1.0, 1.5), (1.5, 99), (1.0, 99), (0.75, 99)):
        S = [s for s in sides if lo <= s["edge"] < hi]
        out.bets(f"{lg} edge {lo}-{hi if hi < 99 else '+'} at real 1H juice",
                 [(s["season"], lib.ats_pl(s["h1m"] + s["h1sp"], s["h1o"])) for s in S])
    S = [s for s in sides if s["edge"] >= 1.0]
    out.bets(f"{lg} edge 1+  - the 1H FAVORITE side", [(s["season"], lib.ats_pl(s["h1m"] + s["h1sp"], s["h1o"])) for s in S if s["h1sp"] < 0])
    out.bets(f"{lg} edge 1+  - the 1H DOG side", [(s["season"], lib.ats_pl(s["h1m"] + s["h1sp"], s["h1o"])) for s in S if s["h1sp"] > 0])
    out.bets(f"{lg} edge 1+  - same side FULL GAME", [(s["season"], lib.ats_pl(s["m"] + s["sp"], s["o"])) for s in S])
    for jl, jf in (("juice -105..-112", lambda o: o >= -112), ("juice -113..-117", lambda o: -117 <= o < -112), ("juice -118 or more", lambda o: o < -117)):
        out.bets(f"{lg} edge 1+ {jl}", [(s["season"], lib.ats_pl(s["h1m"] + s["h1sp"], s["h1o"])) for s in S if jf(s["h1o"])])
    if any("gtier" in s for s in S):
        for t in "PML":
            out.bets(f"{lg} edge 1+ tier {t}", [(s["season"], lib.ats_pl(s["h1m"] + s["h1sp"], s["h1o"])) for s in S if s.get("gtier") == t])
        for lab, f in (("Nov-Dec", lambda s: s["month"] in (11, 12)), ("Jan-Apr", lambda s: s["month"] in (1, 2, 3, 4))):
            out.bets(f"{lg} edge 1+ {lab}", [(s["season"], lib.ats_pl(s["h1m"] + s["h1sp"], s["h1o"])) for s in S if f(s)])
    # stale derivative: full-game ML moved toward this side by 2+ pts (open -> close) / away / flat (2023+ opens)
    O = [s for s in S if s.get("mv") is not None]
    for lab, f in (("full ML moved TO it 2+", lambda s: s["mv"] >= 0.02), ("flat", lambda s: abs(s["mv"]) < 0.02),
                   ("moved AWAY 2+", lambda s: s["mv"] <= -0.02)):
        out.bets(f"{lg} edge 1+ & {lab}", [(s["season"], lib.ats_pl(s["h1m"] + s["h1sp"], s["h1o"])) for s in O if f(s)])
    # 1H ML check: no; by price of the full spread
    for lab, f in (("full |spread| <5", lambda s: abs(s["sp"]) < 5), ("5-9.5", lambda s: 5 <= abs(s["sp"]) < 10), ("10+", lambda s: abs(s["sp"]) >= 10)):
        out.bets(f"{lg} edge 1+ {lab}", [(s["season"], lib.ats_pl(s["h1m"] + s["h1sp"], s["h1o"])) for s in S if f(s)])
    return w


NC = []
for x in lib.nc_sides():
    if x["stype"] != "2" or x["season"] < 2018 or x.get("h1sp") is None or x.get("h1m") is None or not x.get("sp"):
        continue
    if not lib.h1_ok(x["sp"], x["h1sp"]):
        continue
    NC.append({"season": x["season"], "sp": x["sp"], "h1sp": x["h1sp"], "h1o": x["h1odds"], "o": x["spodds"],
               "m": x["margin"], "h1m": x["h1m"], "home": 1 if (x["side"] == "home" and not x["neutral"]) else (-1 if not x["neutral"] else 0),
               "tot": x.get("total"), "month": x["month"],
               "gtier": "P" if "power" in (x["tier"], x["otier"]) else ("M" if "mid" in (x["tier"], x["otier"]) else "L"),
               "mv": (x["p"] - x["po"]) if x.get("po") is not None and x.get("p") is not None else None, "id": x["id"]})
run("COLLEGE", NC, lib.TRAIN, lib.HELD)

NB = []
for g in lib.nba_games():
    if g.get("h1sp") is None or g.get("h1m") is None or not g.get("sp") or g["season"] < 2018:
        continue
    if not lib.h1_ok(g["sp"], g["h1sp"], 0.57):
        continue
    for s in (1, -1):
        mv = None
        if g.get("mloh") and g.get("mlh"):
            mv = (lib.nv(g["mlh"], g["mla"]) - lib.nv(g["mloh"], g["mloa"])) * s
        NB.append({"season": g["season"], "sp": g["sp"] * s, "h1sp": g["h1sp"] * s, "m": g["margin"] * s, "h1m": g["h1m"] * s,
                   "h1o": g["h1sph_o"] if s == 1 else g["h1spa_o"], "o": g["sph_o"] if s == 1 else g["spa_o"],
                   "home": s, "tot": g["total"], "month": int(g["start"][5:7]), "mv": mv})
run("NBA", NB, (2018, 2019, 2020), (2021, 2022, 2023, 2026))
out.save()
