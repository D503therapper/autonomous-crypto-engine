"""S3 - DERIVATIVE MARKETS: is the 1st-half SPREAD (the line itself, bet and graded on the 1st-half score) off
relative to the full game? NBA + college hoops, ESPN's closing 1st-half lines (college 2018-25, NBA 2018-23 + 2026).
Not a repeat: 10/29-10/30 studied the 1H SHARE as a signal for the FULL-GAME moneyline and the 1H 'flip'; nobody has
bet the 1H line itself.
  (a) 1H ATS by side (favorite / dog / home) and spread size vs the full game's ATS on the same games;
  (b) the share k = 1H spread / full spread: fit the typical k on train by spread band, then bet the 1H side the
      line leaves 'cheap' when the 1H number sits 1+ point off k x full (the 1H line too big -> 1H dog; too small ->
      1H favorite);
  (c) college by tier (thin games: is the derivative hung lazily = full x a constant?)."""
from collections import defaultdict

import lib

out = lib.Out("s3_first_half")


def g1(x, sp, odds):
    return lib.ats_pl(x + sp, odds)


# ---- college hoops: side rows, home side as the game
NC = [x for x in lib.nc_sides() if x["stype"] == "2" and x["season"] >= 2018 and x.get("h1sp") is not None
      and x.get("h1m") is not None and x.get("sp") is not None and x["sp"] != 0]
for x in NC:
    x["gtier"] = "P" if "power" in (x["tier"], x["otier"]) else ("M" if "mid" in (x["tier"], x["otier"]) else "L")
out.h("COLLEGE: 1H ATS vs FULL-GAME ATS on the same sides")
for lab, f in (("favorite", lambda x: x["sp"] < 0), ("dog", lambda x: x["sp"] > 0),
               ("home (true)", lambda x: x["side"] == "home" and not x["neutral"]),
               ("fav 1-4.5", lambda x: -4.5 <= x["sp"] < 0), ("fav 5-9.5", lambda x: -9.5 <= x["sp"] <= -5),
               ("fav 10-15.5", lambda x: -15.5 <= x["sp"] <= -10), ("fav 16+", lambda x: x["sp"] <= -16),
               ("dog 1-4.5", lambda x: 0 < x["sp"] <= 4.5), ("dog 10+", lambda x: x["sp"] >= 10)):
    S = [x for x in NC if f(x)]
    out.bets(f"1H   {lab}", [(x["season"], g1(x["h1m"], x["h1sp"], x["h1odds"])) for x in S])
    out.bets(f"FULL {lab}", [(x["season"], g1(x["margin"], x["sp"], x["spodds"])) for x in S])
out.h("COLLEGE 1H by tier (favorite / dog)")
for t in "PML":
    S = [x for x in NC if x["gtier"] == t]
    out.bets(f"1H fav tier {t}", [(x["season"], g1(x["h1m"], x["h1sp"], x["h1odds"])) for x in S if x["sp"] < 0])
    out.bets(f"1H dog tier {t}", [(x["season"], g1(x["h1m"], x["h1sp"], x["h1odds"])) for x in S if x["sp"] > 0])

# share model fit on train: k by full-spread band (favorite side)
def band(sp):
    a = abs(sp)
    return 0 if a < 3 else 1 if a < 6 else 2 if a < 10 else 3 if a < 15 else 4


def fit_k(rows, train):
    acc = defaultdict(list)
    for x in rows:
        if x["season"] in train and x["sp"] < 0:
            acc[band(x["sp"])].append(x["h1sp"] / x["sp"])
    return {b: sorted(v)[len(v) // 2] for b, v in acc.items()}


for lg, rows, train in (("COLLEGE", NC, lib.TRAIN),):
    k = fit_k(rows, train)
    out.h(f"{lg} SHARE: typical 1H/full share by band (train median) " + " ".join(f"b{b}:{v:.3f}" for b, v in sorted(k.items())))
    fav = [x for x in rows if x["sp"] < 0]
    for x in fav:
        x["resid"] = x["h1sp"] - k[band(x["sp"])] * x["sp"]   # + = 1H line smaller for the favorite than typical
    for lo, hi, lab in ((-99, -1.0, "1H line 1+ BIGGER than typical"), (-1.0, -0.5, "0.5-1 bigger"), (-0.5, 0.5, "typical"),
                        (0.5, 1.0, "0.5-1 smaller"), (1.0, 99, "1+ SMALLER than typical")):
        S = [x for x in fav if lo <= x["resid"] < hi]
        out.bets(f"{lab}: 1H FAV", [(x["season"], g1(x["h1m"], x["h1sp"], x["h1odds"])) for x in S])
        out.bets(f"{lab}: 1H DOG", [(x["season"], g1(-x["h1m"], -x["h1sp"], -110)) for x in S])
        out.bets(f"{lab}: FULL fav (same games)", [(x["season"], g1(x["margin"], x["sp"], x["spodds"])) for x in S])
    for t in "PML":
        S = [x for x in fav if x["gtier"] == t and x["resid"] <= -1.0]
        out.bets(f"tier {t} 1H line 1+ bigger: 1H DOG", [(x["season"], g1(-x["h1m"], -x["h1sp"], -110)) for x in S])
        S = [x for x in fav if x["gtier"] == t and x["resid"] >= 1.0]
        out.bets(f"tier {t} 1H line 1+ smaller: 1H FAV", [(x["season"], g1(x["h1m"], x["h1sp"], x["h1odds"])) for x in S])

# ---- NBA
NB = [g for g in lib.nba_games() if g.get("h1sp") is not None and g.get("h1m") is not None and g.get("sp") and g["season"] >= 2018]
out2 = out
out.train, out.held = (2018, 2019, 2020), (2021, 2022, 2023)
out.h("NBA (train 2018-20, held 2021-23; 2026 shown): 1H ATS vs FULL")
side = []
for g in NB:
    for s in (1, -1):
        sp, h1 = g["sp"] * s, g["h1sp"] * s
        side.append({"season": g["season"], "sp": sp, "h1sp": h1, "m": g["margin"] * s, "h1m": g["h1m"] * s,
                     "home": s == 1, "o": g["sph_o"] if s == 1 else g["spa_o"], "h1o": g["h1sph_o"] if s == 1 else g["h1spa_o"]})
for lab, f in (("favorite", lambda x: x["sp"] < 0), ("dog", lambda x: x["sp"] > 0), ("home", lambda x: x["home"]),
               ("fav 1-4.5", lambda x: -4.5 <= x["sp"] < 0), ("fav 5-9.5", lambda x: -9.5 <= x["sp"] <= -5),
               ("fav 10+", lambda x: x["sp"] <= -10)):
    S = [x for x in side if f(x)]
    out.bets(f"1H   {lab}", [(x["season"], g1(x["h1m"], x["h1sp"], x["h1o"])) for x in S])
    out.bets(f"FULL {lab}", [(x["season"], g1(x["m"], x["sp"], x["o"])) for x in S])
fav = [x for x in side if x["sp"] < 0]
k = fit_k(fav, (2018, 2019, 2020))
out.h("NBA SHARE: typical 1H/full share by band (train median) " + " ".join(f"b{b}:{v:.3f}" for b, v in sorted(k.items())))
for x in fav:
    x["resid"] = x["h1sp"] - k[band(x["sp"])] * x["sp"]
for lo, hi, lab in ((-99, -1.0, "1H line 1+ BIGGER"), (-1.0, -0.5, "0.5-1 bigger"), (-0.5, 0.5, "typical"),
                    (0.5, 1.0, "0.5-1 smaller"), (1.0, 99, "1+ SMALLER")):
    S = [x for x in fav if lo <= x["resid"] < hi]
    out.bets(f"NBA {lab}: 1H FAV", [(x["season"], g1(x["h1m"], x["h1sp"], x["h1o"])) for x in S])
    out.bets(f"NBA {lab}: 1H DOG", [(x["season"], g1(-x["h1m"], -x["h1sp"], -110)) for x in S])
out.save()
