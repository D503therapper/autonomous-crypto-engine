"""S4 - STYLE FROM THE BOX SCORES (2021-26; minutes / points / FGM-FGA / rebounds / assists only - no threes, free throws
or turnovers on file): pace (both teams' FGA a game), FG% for / against, rebound margin, assist share, bench share,
the top-5 minutes share (a tight rotation) - and the interactions a pro would look at: a tight rotation on a dense
schedule, pace mismatches on SIDES, a big (rebounding) team vs a small one, a shooting team vs a shooting defense.
Teams 5+ box games in. TRAIN here = 2021-22 (the box starts 2021), HELD = 2023 / 2024 / 2025."""
import lib

R = [x for x in lib.regular(lib.build()) if x.get("pace") is not None and x.get("o_pace") is not None and x["season"] >= 2021]
o = lib.Out("s4")
SP, DG, FV = lib.spreads(R), lib.dogs(R), lib.favs(R)


def gap(x, k):
    return x[k] - x["o_" + k]


o.h("A. Pace mismatch on sides: my pace minus the opponent's (FGA both teams a game), ATS / dog ML / fav ML")
for lo, hi in ((-99, -8), (-8, -4), (-4, 4), (4, 8), (8, 99)):
    rows = [x for x in SP if lo <= gap(x, "pace") < hi]
    o.c(f"ATS pace gap {lo}..{hi}", rows, lib.profit_ats)
    o.c(f"ATS pace gap {lo}..{hi}, as the dog", [x for x in rows if x["sp"] > 0], lib.profit_ats)
    o.c(f"ATS pace gap {lo}..{hi}, as the favorite", [x for x in rows if x["sp"] < 0], lib.profit_ats)
    o.c(f"dog ML pace gap {lo}..{hi}", [x for x in DG if lo <= gap(x, "pace") < hi])
    o.c(f"fav -101..-150 ML pace gap {lo}..{hi}", [x for x in FV if lo <= gap(x, "pace") < hi])
o.h("B. The fast dog / the slow dog (own pace vs the slate's median ~ 120 FGA)")
for lo, hi in ((0, 110), (110, 118), (118, 126), (126, 999)):
    o.c(f"dog ML own pace {lo}..{hi}", [x for x in DG if lo <= x["pace"] < hi])
    o.c(f"ATS as the dog, own pace {lo}..{hi}", [x for x in SP if x["sp"] > 0 and lo <= x["pace"] < hi], lib.profit_ats)
o.h("C. Rebounding: my rebound margin minus theirs, ATS / dog ML")
for lo, hi in ((-99, -8), (-8, -3), (-3, 3), (3, 8), (8, 99)):
    o.c(f"ATS reb-margin gap {lo}..{hi}", [x for x in SP if lo <= gap(x, "rebm") < hi], lib.profit_ats)
    o.c(f"dog ML reb-margin gap {lo}..{hi}", [x for x in DG if lo <= gap(x, "rebm") < hi])
    o.c(f"fav -101..-150 ML reb-margin gap {lo}..{hi}", [x for x in FV if lo <= gap(x, "rebm") < hi])
o.h("D. Shooting: my FG% minus the opponent's FG% ALLOWED (what I shoot vs what they give up), ATS / dog ML")
for lo, hi in ((-9, -0.05), (-0.05, -0.02), (-0.02, 0.02), (0.02, 0.05), (0.05, 9)):
    rows = [x for x in SP if lo <= x["fgp"] - x["o_ofgp"] < hi]
    o.c(f"ATS shoot-vs-allowed {lo}..{hi}", rows, lib.profit_ats)
    o.c(f"dog ML shoot-vs-allowed {lo}..{hi}", [x for x in DG if lo <= x["fgp"] - x["o_ofgp"] < hi])
o.h("E. Assist share (team ball) gap and bench share gap, ATS")
for lo, hi in ((-9, -0.1), (-0.1, -0.03), (-0.03, 0.03), (0.03, 0.1), (0.1, 9)):
    o.c(f"ATS assist-rate gap {lo}..{hi}", [x for x in SP if lo <= gap(x, "astr") < hi], lib.profit_ats)
    o.c(f"ATS bench-share gap {lo}..{hi}", [x for x in SP if lo <= gap(x, "bench") < hi], lib.profit_ats)
    o.c(f"dog ML bench-share gap {lo}..{hi}", [x for x in DG if lo <= gap(x, "bench") < hi])
o.h("F. The tight rotation (top-5 minutes share) x density (3 games in 5 nights / 2 in 3) - legs")
for lo, hi in ((0, 0.62), (0.62, 0.68), (0.68, 0.74), (0.74, 1.1)):
    rows = [x for x in SP if lo <= x["top5"] < hi]
    o.c(f"ATS top5 share {lo}..{hi}", rows, lib.profit_ats)
    o.c(f"ATS top5 share {lo}..{hi}, 3 games in 5 nights", [x for x in rows if (x.get("g5") or 0) >= 2], lib.profit_ats)
    o.c(f"ATS top5 share {lo}..{hi}, 2 in 3 nights", [x for x in rows if (x.get("g3") or 0) >= 1], lib.profit_ats)
    o.c(f"ATS top5 share {lo}..{hi}, rested 3+", [x for x in rows if (x.get("rest") or 0) >= 3 and (x.get("g5") or 0) == 0], lib.profit_ats)
    o.c(f"ATS top5 share {lo}..{hi}, Feb-Mar", [x for x in rows if x["start"][5:7] in ("02", "03")], lib.profit_ats)
    o.c(f"dog ML top5 share {lo}..{hi}", [x for x in DG if lo <= x["top5"] < hi])
    o.c(f"fav -101..-150 ML top5 share {lo}..{hi}", [x for x in FV if lo <= x["top5"] < hi])
o.h("G. Tight rotation gap (me minus opp) on a 2-in-3 for me only")
rows = [x for x in SP if (x.get("g3") or 0) >= 1 and (x.get("og3") or 0) == 0]
for lo, hi in ((-9, -0.05), (-0.05, 0.05), (0.05, 9)):
    o.c(f"ATS 2-in-3 (opp rested), top5 gap {lo}..{hi}", [x for x in rows if lo <= gap(x, "top5") < hi], lib.profit_ats)
o.h("H. The big-vs-small AND fast-vs-slow combined on the dog")
o.c("dog ML: out-rebounds (gap 5+) AND slower (pace gap -5 or less)", [x for x in DG if gap(x, "rebm") >= 5 and gap(x, "pace") <= -5])
o.c("dog ML: out-rebounded (gap -5) AND faster (pace gap 5+)", [x for x in DG if gap(x, "rebm") <= -5 and gap(x, "pace") >= 5])
o.c("ATS fav: out-rebounds (gap 5+) AND slower", [x for x in SP if x["sp"] < 0 and gap(x, "rebm") >= 5 and gap(x, "pace") <= -5], lib.profit_ats)
o.save()
