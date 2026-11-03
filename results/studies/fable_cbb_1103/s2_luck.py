"""S2 - LUCK REGRESSION: the record in close games (decided by 5 or fewer, 3 or fewer) and win % minus the margin-implied
win % (a normal with sd 11 on the average margin) - does the market over-rate the lucky team / under-rate the unlucky
one? Teams 8+ games in; dogs ML, small favorites ML, ATS; by season phase; the second-half team (2nd-half margin minus
1st-half margin on average). Regular season 2018-26 at the close, the 2023-25 open as the second check."""
import lib

R = [x for x in lib.regular(lib.build()) if (x.get("n_prev") or 0) >= 8]
o = lib.Out("s2")
SP, DG, FV = lib.spreads(R), lib.dogs(R), lib.favs(R)
o.h("A. Net close-game record (wins minus losses by 5 or fewer), ATS - the team itself")
for lo, hi in ((-99, -3), (-2, -2), (-1, -1), (0, 0), (1, 1), (2, 2), (3, 99)):
    o.c(f"ATS cnet5 {lo}..{hi}", [x for x in SP if lo <= x["cnet5"] <= hi], lib.profit_ats)
o.h("B. Net close-game record, the dog ML +100..+350 and the small favorite ML")
for lo, hi in ((-99, -2), (-1, 1), (2, 99)):
    o.c(f"dog ML cnet5 {lo}..{hi}", [x for x in DG if lo <= x["cnet5"] <= hi])
    o.c(f"dog ML, OPPONENT cnet5 {lo}..{hi}", [x for x in DG if x.get("o_cnet5") is not None and lo <= x["o_cnet5"] <= hi])
    o.c(f"fav -101..-150 ML cnet5 {lo}..{hi}", [x for x in FV if lo <= x["cnet5"] <= hi])
    o.c(f"fav -101..-150 ML, OPPONENT cnet5 {lo}..{hi}", [x for x in FV if x.get("o_cnet5") is not None and lo <= x["o_cnet5"] <= hi])
o.h("C. The luck gap: win % minus margin-implied (this team minus the opponent), ATS")
for lo, hi in ((-9, -0.15), (-0.15, -0.08), (-0.08, -0.03), (-0.03, 0.03), (0.03, 0.08), (0.08, 0.15), (0.15, 9)):
    rows = [x for x in SP if x.get("o_luck") is not None and lo <= x["luck"] - x["o_luck"] < hi]
    o.c(f"ATS luck gap {lo}..{hi}", rows, lib.profit_ats)
o.h("D. The luck gap, dogs and small favorites ML")
for lo, hi in ((-9, -0.08), (-0.08, 0.08), (0.08, 9)):
    o.c(f"dog ML luck gap {lo}..{hi}", [x for x in DG if x.get("o_luck") is not None and lo <= x["luck"] - x["o_luck"] < hi])
    o.c(f"fav -101..-150 ML luck gap {lo}..{hi}", [x for x in FV if x.get("o_luck") is not None and lo <= x["luck"] - x["o_luck"] < hi])
    o.c(f"fav -151..-250 ML luck gap {lo}..{hi}", [x for x in lib.favs(R, -250, -151) if x.get("o_luck") is not None and lo <= x["luck"] - x["o_luck"] < hi])
o.h("E. Unlucky team (luck under -0.08) by phase / venue / tier, ATS")
UL = [x for x in SP if x.get("o_luck") is not None and x["luck"] - x["o_luck"] <= -0.08]
o.c("ATS unlucky, Nov-Dec", [x for x in UL if x["start"][5:7] in ("11", "12")], lib.profit_ats)
o.c("ATS unlucky, Jan", [x for x in UL if x["start"][5:7] == "01"], lib.profit_ats)
o.c("ATS unlucky, Feb-Mar", [x for x in UL if x["start"][5:7] in ("02", "03")], lib.profit_ats)
o.c("ATS unlucky, home", [x for x in UL if x["venue"] == "home"], lib.profit_ats)
o.c("ATS unlucky, road", [x for x in UL if x["venue"] == "away"], lib.profit_ats)
o.c("ATS unlucky, as the favorite", [x for x in UL if x["sp"] < 0], lib.profit_ats)
o.c("ATS unlucky, as the dog", [x for x in UL if x["sp"] > 0], lib.profit_ats)
o.c("ATS unlucky, 15+ games in", [x for x in UL if x["n_prev"] >= 15], lib.profit_ats)
o.c("ATS unlucky, same conference", [x for x in UL if x["same_conf"]], lib.profit_ats)
o.c("ATS unlucky, gap under -0.15", [x for x in UL if x["luck"] - x["o_luck"] <= -0.15], lib.profit_ats)
o.h("F. Does the market already carry luck? mean (margin + spread) by luck gap (home rows, + = the team beat the number)")
for lo, hi in ((-9, -0.15), (-0.15, -0.08), (-0.08, -0.03), (-0.03, 0.03), (0.03, 0.08), (0.08, 0.15), (0.15, 9)):
    rows = [x for x in SP if x.get("o_luck") is not None and lo <= x["luck"] - x["o_luck"] < hi]
    if rows:
        m = sum(x["margin"] + x["sp"] for x in rows) / len(rows)
        o.note(f"luck gap {lo}..{hi}: n {len(rows)} mean cover margin {m:+.2f}")
o.h("G. The second-half team: average 2nd-half margin minus 1st-half margin (8+ games), ATS and dog ML")
for lo, hi in ((-99, -4), (-4, -2), (-2, 0), (0, 2), (2, 4), (4, 99)):
    o.c(f"ATS h2 gain {lo}..{hi}", [x for x in SP if lo <= x["h2_gain"] < hi], lib.profit_ats)
for lo, hi in ((-99, -3), (-3, 3), (3, 99)):
    o.c(f"dog ML h2 gain {lo}..{hi}", [x for x in DG if lo <= x["h2_gain"] < hi])
    o.c(f"fav -101..-150 ML h2 gain {lo}..{hi}", [x for x in FV if lo <= x["h2_gain"] < hi])
    rows = [x for x in SP if x.get("o_h2_gain") is not None and lo <= x["h2_gain"] - x["o_h2_gain"] < hi]
    o.c(f"ATS h2 gain GAP (me minus opp) {lo}..{hi}", rows, lib.profit_ats)
o.h("H. The first-half team: average 1H margin vs full margin - strong starters as dogs")
for lo, hi in ((-99, -2), (-2, 2), (2, 99)):
    o.c(f"dog ML h1 avg {lo}..{hi}", [x for x in DG if x.get("h1_avg") is not None and lo <= x["h1_avg"] < hi])
o.save()
