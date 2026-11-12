"""11/12 studies 8 and 9 (the team box 2021-26, TRAIN 2021-22 / HELD 2023-25; the rematch totals use every priced
season 2018-25, TRAIN 2018-21 / HELD 2022-25):
S8 the turnover MATCHUP - a ball-pressure defense (turnovers forced / steals per possession) against an offense that
   coughs it up: the side, the spread, the total, with a dose. (The turnover-prone small FAVORITE is built 11/3; the
   11/3 note read "forces turnovers vs coughs it up (nothing)" on a per-game margin - this is per possession, with the
   steals, the dose and the total.)
S9 pace: who sets the tempo when a fast team meets a slow one, the total at an extreme mismatch by who is at home /
   favored (the 11/11 A2 pace PAIR is dead and not re-run), and the conference REMATCH: does the second total / spread
   adjust to what the first meeting did?
Every input = the box scores / the first meeting, before tip."""
from collections import defaultdict
import lib

R = lib.build()
c8 = lib.Cells("s8", (2021, 2022), (2023, 2024, 2025))
c9 = lib.Cells("s9", (2021, 2022), (2023, 2024, 2025))
c9b = lib.Cells("s9b", (2018, 2021), (2022, 2023, 2024, 2025))
AVG_TO, AVG_PACE = 0.178, 69.5
reg_rows = []      # (fast pace - avg, slow pace - avg, actual possessions - avg, fast team at home)
for g in R:
    if g["stype"] != "2" or not g["mlh"]:
        continue
    mon = g["day"].month
    ov, un = lib.tot_p(g, True), lib.tot_p(g, False)
    # ---------------- S9b: the conference rematch (the 2nd meeting of the season, a true home floor) ----------------
    if g["season"] >= 2018 and g["conf"] and len(g["meet"]) == 1 and not g["neutral"] and g["total"] is not None:
        m1 = g["meet"][0]
        c9b.add("REMATCH base: OVER", g, ov)
        c9b.add("REMATCH base: UNDER", g, un)
        if m1["total"] is not None:
            miss = m1["pts"] - m1["total"]
            mb = ("went 20+ over" if miss >= 20 else "went 10-19.5 over" if miss >= 10 else "within 10" if miss > -10
                  else "went 10-19.5 under" if miss > -20 else "went 20+ under")
            c9b.add(f"REMATCH, the first meeting {mb}: OVER", g, ov)
            c9b.add(f"REMATCH, the first meeting {mb}: UNDER", g, un)
            c9b.add(f"REMATCH, the first meeting {mb}: this total minus the first total", g, g["total"] - m1["total"])
            c9b.add(f"REMATCH, the first meeting {mb}: this game's miss (points - total)", g, g["hs"] + g["as"] - g["total"])
            mv = g["total"] - m1["total"]
            if miss >= 10:
                c9b.add(f"REMATCH after a 10+ over, total {'raised 4+' if mv >= 4 else 'raised 0.5-3.5' if mv > 0 else 'not raised'}: UNDER", g, un)
                c9b.add(f"REMATCH after a 10+ over, total {'raised 4+' if mv >= 4 else 'raised 0.5-3.5' if mv > 0 else 'not raised'}: OVER", g, ov)
            if miss <= -10:
                c9b.add(f"REMATCH after a 10+ under, total {'cut 4+' if mv <= -4 else 'cut 0.5-3.5' if mv < 0 else 'not cut'}: OVER", g, ov)
                c9b.add(f"REMATCH after a 10+ under, total {'cut 4+' if mv <= -4 else 'cut 0.5-3.5' if mv < 0 else 'not cut'}: UNDER", g, un)
            if (g["day"] - m1["day"]).days <= 21:
                c9b.add("REMATCH within 3 weeks: UNDER", g, un)
                c9b.add("REMATCH within 3 weeks: OVER", g, ov)
        # the spread: did the first meeting's cover margin move the second number too far?
        if m1["sp"] is not None and g["sp"] is not None:
            # the first game's home team is tonight's away team (a home-and-home)
            if m1["home"] == g["away"]:
                cm1_home_now = -(m1["m"] + m1["sp"])          # tonight's HOME team's cover margin in game 1 (it was away)
                swing = g["sp"] + m1["sp"]                    # tonight's home spread vs the mirror of game 1's
                cb = ("covered by 15+" if cm1_home_now >= 15 else "covered by 7-14.5" if cm1_home_now >= 7 else "within 7"
                      if cm1_home_now > -7 else "failed by 7-14.5" if cm1_home_now > -15 else "failed by 15+")
                c9b.add(f"REMATCH, tonight's home team {cb} in game 1: home ATS", g, lib.ats_p(g, "H"))
    if g["season"] < 2021:
        continue
    bs = lib.both(g, 5)
    if not bs:
        continue
    H, A = g["H"]["bx"], g["A"]["bx"]
    # ---------------- S8: the turnover matchup ----------------
    for side, f, o in bs:
        b, ob = f["bx"], o["bx"]
        od, sp = lib.odds(g, side), lib.spread(g, side)
        bd = lib.band(od)
        ml, at = lib.ml_p(g, side), lib.ats_p(g, side)
        v = lib.ven(g, side)
        press = b["o_tor"] >= 0.205
        steal = b["stl"] >= 0.115
        sloppy = ob["tor"] >= 0.194
        careful = ob["tor"] <= 0.157
        x = b["o_tor"] + ob["tor"] - 2 * AVG_TO      # the turnovers this defense should force over an average matchup
        y = ob["o_tor"] + b["tor"] - 2 * AVG_TO      # ...and what this offense should give away
        net = x - y                                  # the turnover matchup edge, per possession
        nb = ("+.05 or more" if net >= 0.05 else "+.03..+.05" if net >= 0.03 else "-.03..+.03" if net > -0.03
              else "-.05..-.03" if net > -0.05 else "-.05 or less")
        c8.add("BASE ATS", g, at)
        if bd:
            c8.add(f"BASE {bd} ML", g, ml)
            c8.add(f"NET turnover edge {nb}: {bd} ML", g, ml)
        c8.add(f"NET turnover edge {nb}: ATS", g, at)
        if press and sloppy:
            c8.add("PRESSURE D vs a SLOPPY offense: ATS", g, at)
            c8.add(f"PRESSURE D vs a SLOPPY offense: ATS ven {v}", g, at)
            c8.add(f"PRESSURE D vs a SLOPPY offense: ATS {'Nov-Dec' if mon in (11, 12) else 'Jan-Mar'}", g, at)
            if bd:
                c8.add(f"PRESSURE D vs a SLOPPY offense: {bd} ML", g, ml)
                c8.add(f"PRESSURE D vs a SLOPPY offense: {bd} ML at the OPEN", g, lib.ml_open_p(g, side))
            c8.add("PRESSURE D vs a SLOPPY offense: OVER", g, ov)
            c8.add("PRESSURE D vs a SLOPPY offense: UNDER", g, un)
            if sp is not None:
                c8.add(f"PRESSURE D vs a SLOPPY offense, {'laying 8+' if sp <= -8 else 'laying under 8' if sp < 0 else 'getting points'}: ATS", g, at)
        if press and careful:
            c8.add("PRESSURE D vs a CAREFUL offense: ATS", g, at)
            if bd:
                c8.add(f"PRESSURE D vs a CAREFUL offense: {bd} ML", g, ml)
        if steal and sloppy:
            c8.add("STEALS D (top fifth) vs a SLOPPY offense: ATS", g, at)
            if bd:
                c8.add(f"STEALS D vs a SLOPPY offense: {bd} ML", g, ml)
        if sloppy and not press:
            c8.add("an ordinary D vs a SLOPPY offense: ATS", g, at)
        if net >= 0.05 and bd == "dog":
            c8.add(f"NET +.05 dog {'+100..+200' if od <= 200 else '+201..+350'}: ML", g, ml)
            c8.add(f"NET +.05 dog ven {v}: ML", g, ml)
            c8.add("NET +.05 dog: ML at the OPEN", g, lib.ml_open_p(g, side))
        if net <= -0.05 and bd in ("sfav", "bfav"):
            c8.add(f"NET -.05 {bd} ven {v}: ML", g, ml)
    tsum = (H["o_tor"] + A["tor"] + A["o_tor"] + H["tor"]) / 2 - 2 * AVG_TO     # the game's turnover rate over average
    tb = "+.04 or more" if tsum >= 0.04 else "+.02..+.04" if tsum >= 0.02 else "-.02..+.02" if tsum > -0.02 else "-.02 or less"
    c8.add(f"GAME turnovers expected {tb}: OVER", g, ov)
    c8.add(f"GAME turnovers expected {tb}: UNDER", g, un)
    # ---------------- S9: pace ----------------
    fast, slow = (("H", "A") if H["pace"] >= A["pace"] else ("A", "H"))
    pf, ps = g[fast]["bx"]["pace"], g[slow]["bx"]["pace"]
    gap = pf - ps
    if g["poss"]:
        reg_rows.append((pf - AVG_PACE, ps - AVG_PACE, g["poss"] - AVG_PACE, fast == "H", g["neutral"], gap,
                         (lib.spread(g, fast) or 0) < 0))
    c9.add("BASE OVER", g, ov)
    c9.add("BASE UNDER", g, un)
    if gap >= 5:
        gb = "8+" if gap >= 8 else "5-8"
        who = "neutral floor" if g["neutral"] else "the SLOW team at home" if slow == "H" else "the FAST team at home"
        fv = lib.spread(g, slow)
        whof = "the SLOW team favored" if (fv or 0) < 0 else "the FAST team favored"
        c9.add(f"MISMATCH {gb} possessions: OVER", g, ov)
        c9.add(f"MISMATCH {gb} possessions: UNDER", g, un)
        c9.add(f"MISMATCH 5+, {who}: OVER", g, ov)
        c9.add(f"MISMATCH 5+, {who}: UNDER", g, un)
        c9.add(f"MISMATCH 5+, {whof}: OVER", g, ov)
        c9.add(f"MISMATCH 5+, {whof}: UNDER", g, un)
        if fv is not None:
            c9.add(f"MISMATCH 5+, {whof}, laying {'8+' if abs(fv) >= 8 else 'under 8'}: OVER", g, ov)
            c9.add(f"MISMATCH 5+, {whof}, laying {'8+' if abs(fv) >= 8 else 'under 8'}: UNDER", g, un)
        c9.add(f"MISMATCH 5+: the SLOW team ATS ({who})", g, lib.ats_p(g, slow))
        c9.add(f"MISMATCH 5+: the SLOW team ATS ({whof})", g, lib.ats_p(g, slow))
        if g["lsh"] and g["lsa"] and g["total"] is not None:
            c9.add(f"MISMATCH 5+, {who}: 1st-half points minus 0.47 x the total", g, g["lsh"][0] + g["lsa"][0] - 0.47 * g["total"])
        ext_slow = ps <= 66.0
        ext_fast = pf >= 73.4
        if ext_slow and not ext_fast:
            c9.add(f"an EXTREME slow team (bottom tenth) in a mismatch, {who}: UNDER", g, un)
            c9.add(f"an EXTREME slow team (bottom tenth) in a mismatch, {who}: OVER", g, ov)
        if ext_fast and not ext_slow:
            c9.add(f"an EXTREME fast team (top tenth) in a mismatch, {who}: OVER", g, ov)
            c9.add(f"an EXTREME fast team (top tenth) in a mismatch, {who}: UNDER", g, un)

# who sets the tempo: actual possessions on the fast team's and the slow team's pace (least squares, no intercept bias)
import numpy as np


def fit(rows, tag):
    X = np.array([[1.0, r[0], r[1]] for r in rows])
    y = np.array([r[2] for r in rows])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    c9.p(f"TEMPO {tag:44s} n{len(rows):<6d} possessions over average = {b[0]:+.2f} {b[1]:+.3f} x the fast team's pace "
         f"{b[2]:+.3f} x the slow team's pace")


c9.lines.append("S9 - PACE: WHO SETS THE TEMPO + THE MISMATCH TOTAL  (TRAIN 2021-22 | HELD 2023-25)")
fit(reg_rows, "every game")
fit([r for r in reg_rows if r[5] >= 5], "a 5+ possession mismatch")
fit([r for r in reg_rows if r[5] >= 5 and r[3] and not r[4]], "mismatch, the FAST team at home")
fit([r for r in reg_rows if r[5] >= 5 and not r[3] and not r[4]], "mismatch, the SLOW team at home")
fit([r for r in reg_rows if r[5] >= 5 and r[6]], "mismatch, the FAST team favored")
fit([r for r in reg_rows if r[5] >= 5 and not r[6]], "mismatch, the SLOW team favored")
for c, t in ((c8, "S8 - THE TURNOVER MATCHUP  (TRAIN 2021-22 | HELD 2023-25; profit a unit at the close)"), (c9, None),
             (c9b, "S9b - THE CONFERENCE REMATCH  (TRAIN 2018-21 | HELD 2022-25; profit a unit at the close)")):
    print("\n=====", t or "S9")
    if t:
        c.lines.append(t)
    c.dump()
