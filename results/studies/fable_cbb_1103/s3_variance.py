"""S3 - VARIANCE: a dog needs variance, a favorite needs none. The spread of a team's margins (m_sd) and of its cover
margins (cm_sd) over its earlier games (8+), this team and the opponent, the pair's combined - dogs ML by price band,
favorites ML, ATS. Plus the pair's expected total variance proxy: both teams' pace. Regular season 2018-26 at the close."""
import lib

R = [x for x in lib.regular(lib.build()) if (x.get("n_prev") or 0) >= 8 and x.get("m_sd") is not None]
o = lib.Out("s3")
SP, DG, FV = lib.spreads(R), lib.dogs(R), lib.favs(R)


def both(x):
    if x.get("o_m_sd") is None:
        return None
    return (x["m_sd"] + x["o_m_sd"]) / 2


o.h("A. The dog's own margin spread (sd of its margins so far)")
for lo, hi in ((0, 10), (10, 12), (12, 14), (14, 16), (16, 99)):
    o.c(f"dog ML own m_sd {lo}..{hi}", [x for x in DG if lo <= x["m_sd"] < hi])
o.h("B. The pair's average margin spread, dogs by price band")
for blo, bhi in ((100, 150), (151, 220), (221, 350)):
    for lo, hi in ((0, 11), (11, 13), (13, 15), (15, 99)):
        o.c(f"dog +{blo}..+{bhi}, pair sd {lo}..{hi}", [x for x in DG if blo <= x["ml"] <= bhi and both(x) is not None and lo <= both(x) < hi])
o.h("C. Favorites: low-variance favorites ML / ATS")
for lo, hi in ((0, 11), (11, 13), (13, 15), (15, 99)):
    o.c(f"fav -101..-150 ML pair sd {lo}..{hi}", [x for x in FV if both(x) is not None and lo <= both(x) < hi])
    o.c(f"fav -151..-300 ML pair sd {lo}..{hi}", [x for x in lib.favs(R, -300, -151) if both(x) is not None and lo <= both(x) < hi])
    o.c(f"ATS favorite, pair sd {lo}..{hi}", [x for x in SP if x["sp"] < 0 and both(x) is not None and lo <= both(x) < hi], lib.profit_ats)
    o.c(f"ATS dog, pair sd {lo}..{hi}", [x for x in SP if x["sp"] > 0 and both(x) is not None and lo <= both(x) < hi], lib.profit_ats)
o.h("D. The cover-margin spread (how far the team runs from its OWN lines) - the dog ML and ATS")
CS = [x for x in R if x.get("cm_sd") is not None and x.get("n_cm", 0) >= 8]
for lo, hi in ((0, 9), (9, 11), (11, 13), (13, 99)):
    o.c(f"dog ML own cm_sd {lo}..{hi}", [x for x in lib.dogs(CS) if lo <= x["cm_sd"] < hi])
    o.c(f"ATS own cm_sd {lo}..{hi}", [x for x in lib.spreads(CS) if lo <= x["cm_sd"] < hi], lib.profit_ats)
    o.c(f"ATS as a favorite, own cm_sd {lo}..{hi}", [x for x in lib.spreads(CS) if x["sp"] < 0 and lo <= x["cm_sd"] < hi], lib.profit_ats)
o.h("E. The mismatch: a high-variance dog vs a low-variance favorite and the reverse")
for a, b, name in ((16, 11, "dog sd 16+ vs fav sd under 11"), (11, 16, "dog sd under 11 vs fav sd 16+")):
    if a > b:
        rows = [x for x in DG if x["m_sd"] >= a and x.get("o_m_sd") is not None and x["o_m_sd"] < b]
    else:
        rows = [x for x in DG if x["m_sd"] < a and x.get("o_m_sd") is not None and x["o_m_sd"] >= b]
    o.c(f"dog ML {name}", rows)
o.h("F. Does the market price variance? the closing spread vs the ML-implied spread by pair sd")
import math
for lo, hi in ((0, 11), (11, 13), (13, 15), (15, 99)):
    rows = [x for x in SP if x.get("p") is not None and both(x) is not None and lo <= both(x) < hi and x["side"] == "home"]
    if rows:
        # the implied spread from the ML with a sd-11 normal; a bigger true sd means the ML should be CLOSER to even
        # for the same spread: compare the ML-implied margin (sd 11) with the posted spread
        wins = sum(1 for x in rows if x["won"]) / len(rows)
        pr = sum(x["p"] for x in rows) / len(rows)
        o.note(f"pair sd {lo}..{hi}: n {len(rows)} home win {wins:.3f} vs priced {pr:.3f}  (favorites in it: "
               f"{sum(1 for x in rows if x['sp'] < 0 and x['won']) / max(1, sum(1 for x in rows if x['sp'] < 0)):.3f} won vs "
               f"{sum(x['p'] for x in rows if x['sp'] < 0) / max(1, sum(1 for x in rows if x['sp'] < 0)):.3f} priced)")
o.save()
