"""11/12 studies 1-4 (the team box 2021-26; TRAIN 2021-22, HELD 2023 / 2024 / 2025; 2026 = the live season, shown):
S1 the 45%+ three-point team (the owner's cut - the 11/3 tercile read is on file: dog -3.6%, small favorite -7.4%);
S2 free-throw shooting in close games (the bad FT% team laying a short number);
S3 SWAP for the referee crews (dead 10/31, and crews aren't known before tip): the WHISTLE the teams bring - both
   teams' fouls / free-throw attempts season to date, on the total;
S4 SWAP for returning minutes (dead 11/3 DEEP): the defense that gives up the three (opponents' 3PA share).
Every input = the season's box scores BEFORE tip (both teams 5+ box games)."""
from collections import defaultdict
import lib

R = lib.build()
TR, HE = (2021, 2022), (2023, 2024, 2025)
c1, c2, c3, c4 = (lib.Cells(f"s{i}", TR, HE) for i in (1, 2, 3, 4))
run = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))     # season -> stat -> [sum, n] of pre-tip team values so far


def avg(s, k, default):
    a = run[s][k]
    return a[0] / a[1] if a[1] >= 200 else default


DEF = {"pf": 16.9, "fta": 19.1, "o_fta": 18.3, "o_pf": 17.3}
for g in R:
    if g["season"] < 2021 or g["stype"] != "2" or not g["mlh"]:
        continue
    bs = lib.both(g, 5)
    if not bs:
        continue
    s = g["season"]
    mon = g["day"].month
    early = mon in (11, 12)
    for side, f, o in bs:
        b, ob = f["bx"], o["bx"]
        od, sp = lib.odds(g, side), lib.spread(g, side)
        bd = lib.band(od)
        ml, at, op = lib.ml_p(g, side), lib.ats_p(g, side), lib.ml_open_p(g, side)
        v = lib.ven(g, side)
        # ---------- S1: the three-point share ----------
        t3 = "45+" if b["tpr"] >= 0.45 else "40-45" if b["tpr"] >= 0.40 else "33-40" if b["tpr"] >= 0.33 else "<33"
        c1.add("BASE ATS", g, at)
        if bd:
            c1.add(f"BASE {bd} ML", g, ml)
            c1.add(f"3PA {t3} {bd} ML", g, ml)
            c1.add(f"3PA {t3} {bd} ML at the OPEN", g, op)
            c1.add(f"3PA {t3} {bd} ATS", g, at)
        c1.add(f"3PA {t3} ATS", g, at)
        if b["tpr"] >= 0.45:
            if bd == "dog":
                c1.add(f"3PA 45+ dog {'+100..+200' if od <= 200 else '+201..+350'} ML", g, ml)
                c1.add(f"3PA 45+ dog ven {v} ML", g, ml)
                c1.add(f"3PA 45+ dog {'Nov-Dec' if early else 'Jan-Mar'} ML", g, ml)
                c1.add(f"3PA 45+ dog, makes them ({'36%+' if b['tp'] >= 0.36 else 'under 33%' if b['tp'] < 0.33 else '33-36%'}) ML", g, ml)
                c1.add(f"3PA 45+ dog vs a defense that {'gives up threes (41%+)' if ob['o_tpr'] >= 0.41 else 'takes them away (<35%)' if ob['o_tpr'] < 0.35 else 'is in between'} ML", g, ml)
            if bd == "sfav":
                c1.add(f"3PA 45+ small fav ven {v} ML", g, ml)
                c1.add(f"3PA 45+ small fav {'Nov-Dec' if early else 'Jan-Mar'} ML", g, ml)
                c1.add(f"3PA 45+ small fav, turnover-prone too ({b['tor'] - b['o_tor'] >= 0.007}) ML", g, ml)
            if bd == "bfav":
                c1.add(f"3PA 45+ fav -151..-400 ATS {'Nov-Dec' if early else 'Jan-Mar'}", g, at)
            c1.add("3PA 45+ game: OVER", g, lib.tot_p(g, True) if side == "H" or o["bx"]["tpr"] < 0.45 else None)
            c1.add("3PA 45+ game: UNDER", g, lib.tot_p(g, False) if side == "H" or o["bx"]["tpr"] < 0.45 else None)
        if b["tpr"] >= 0.42 and bd == "sfav":
            c1.add("3PA 42+ small fav ML", g, ml)
            c1.add("3PA 42+ small fav ML at the OPEN", g, op)
            c1.add(f"3PA 42+ small fav, NOT turnover-prone ({b['tor'] - b['o_tor'] < 0.007}) ML", g, ml)
        if b["tpr"] < 0.33 and bd == "sfav":
            c1.add(f"3PA <33 small fav ven {v} ML", g, ml)
        # ---------- S2: free throws ----------
        if b["fta"] * b["n"] >= 60:
            ft = "bad (<=67%)" if b["ftp"] <= 0.67 else "good (75%+)" if b["ftp"] >= 0.75 else "middle"
            oft = "bad" if ob["ftp"] <= 0.67 else "good" if ob["ftp"] >= 0.75 else "middle"
            if sp is not None and -5 <= sp <= -1:
                c2.add("BASE fav laying 1-5 ATS", g, at)
                c2.add("BASE fav laying 1-5 ML", g, ml)
                c2.add(f"FT {ft} fav laying 1-5 ATS", g, at)
                c2.add(f"FT {ft} fav laying 1-5 ML", g, ml)
                c2.add(f"FT {ft} fav laying 1-5 ML at the OPEN", g, op)
                if ft != "middle":
                    c2.add(f"FT {ft} fav laying 1-5 ATS ven {v}", g, at)
                    c2.add(f"FT {ft} fav laying 1-5 ATS {'Nov-Dec' if early else 'Jan-Mar'}", g, at)
                    c2.add(f"FT {ft} fav laying 1-5 vs a {oft} FT dog ATS", g, at)
                    c2.add(f"FT {ft} fav laying 1-5, lives at the line ({b['ftr'] >= 0.35}) ATS", g, at)
                if b["ftp"] <= 0.64:
                    c2.add("FT worst (<=64%) fav laying 1-5 ATS", g, at)
                    c2.add("FT worst (<=64%) fav laying 1-5 ML", g, ml)
                if b["ftp"] >= 0.77:
                    c2.add("FT best (77%+) fav laying 1-5 ATS", g, at)
                    c2.add("FT best (77%+) fav laying 1-5 ML", g, ml)
            if sp is not None and 1 <= sp <= 5:
                c2.add("BASE dog getting 1-5 ATS", g, at)
                c2.add(f"FT {ft} dog getting 1-5 ATS", g, at)
                c2.add(f"FT {ft} dog getting 1-5 ML", g, ml)
            if sp is not None and -12 <= sp <= -5.5:
                c2.add(f"FT {ft} fav laying 5.5-12 ATS", g, at)
            if bd == "sfav":
                c2.add(f"FT {ft} small fav -101..-150 ML", g, ml)
            # ex post (not a bet): the favorite up 1-9 at the half - does it hold the win / the cover?
            if sp is not None and sp < 0 and g["lsh"] and g["lsa"]:
                hm = (g["lsh"][0] - g["lsa"][0]) * (1 if side == "H" else -1)
                if 1 <= hm <= 9:
                    won = (g["hs"] > g["as"]) == (side == "H")
                    c2.add(f"EX POST fav up 1-9 at the half, FT {ft}: held the WIN (1 = yes)", g, 1.0 if won else 0.0)
                    c2.add(f"EX POST fav up 1-9 at the half, FT {ft}: ATS", g, at)
        # ---------- S4 (swap): the defense that gives up the three ----------
        d3 = "gives up threes (42%+)" if b["o_tpr"] >= 0.42 else "takes them away (<=34%)" if b["o_tpr"] <= 0.34 else "middle"
        if bd:
            c4.add(f"BASE {bd} ML", g, ml)
            c4.add(f"D {d3} {bd} ML", g, ml)
            c4.add(f"D {d3} {bd} ML at the OPEN", g, op)
        c4.add("BASE ATS", g, at)
        c4.add(f"D {d3} ATS", g, at)
        if d3 != "middle":
            c4.add(f"D {d3} ATS ven {v}", g, at)
            c4.add(f"D {d3} ATS {'Nov-Dec' if early else 'Jan-Mar'}", g, at)
            if bd == "sfav":
                c4.add(f"D {d3} small fav vs a {'3PA 40+' if ob['tpr'] >= 0.40 else '3PA <36' if ob['tpr'] < 0.36 else 'middle'} offense ML", g, ml)
            if bd == "dog":
                c4.add(f"D {d3} dog {'+100..+200' if od <= 200 else '+201..+350'} ML", g, ml)
            if sp is not None and sp <= -8:
                c4.add(f"D {d3} fav laying 8+ ATS", g, at)
        ex3 = b["tpr"] + ob["o_tpr"]
        if ex3 >= 0.86:
            c4.add("MATCHUP a 3PA 43+ offense vs a defense giving up 43+: ATS", g, at if b["tpr"] >= 0.43 and ob["o_tpr"] >= 0.43 else None)
            if bd == "dog" and b["tpr"] >= 0.43 and ob["o_tpr"] >= 0.43:
                c4.add("MATCHUP a 3PA 43+ dog vs a defense giving up 43+: ML", g, ml)
    # ---------- S3 (swap): the whistle on the total ----------
    H, A = g["H"]["bx"], g["A"]["bx"]
    if H["pf"] and A["pf"] and g["total"] is not None:
        a_pf, a_fta = avg(s, "pf", DEF["pf"]), avg(s, "fta", DEF["fta"])
        fouls = (H["pf"] + H["o_pf"] + A["pf"] + A["o_pf"]) / 2 - 2 * a_pf      # expected game fouls over the average
        ftas = (H["fta"] + H["o_fta"] + A["fta"] + A["o_fta"]) / 2 - 2 * a_fta  # expected game FTA over the average
        ov, un = lib.tot_p(g, True), lib.tot_p(g, False)
        c3.add("BASE OVER", g, ov)
        c3.add("BASE UNDER", g, un)
        fb = ("+5 or more" if fouls >= 5 else "+2.5..+5" if fouls >= 2.5 else "-2.5..+2.5" if fouls > -2.5
              else "-5..-2.5" if fouls > -5 else "-5 or less")
        tb = ("+8 or more" if ftas >= 8 else "+4..+8" if ftas >= 4 else "-4..+4" if ftas > -4 else "-8..-4" if ftas > -8
              else "-8 or less")
        c3.add(f"FOULS expected {fb}: OVER", g, ov)
        c3.add(f"FOULS expected {fb}: UNDER", g, un)
        c3.add(f"FTA expected {tb}: OVER", g, ov)
        c3.add(f"FTA expected {tb}: UNDER", g, un)
        c3.add(f"FOULS expected {fb}: the miss (points - total)", g, g["hs"] + g["as"] - g["total"])
        if fouls >= 5 or fouls <= -5:
            w = "whistle-heavy" if fouls >= 5 else "whistle-light"
            c3.add(f"{w} {'Nov-Dec' if early else 'Jan-Mar'}: OVER", g, ov)
            c3.add(f"{w} {'Nov-Dec' if early else 'Jan-Mar'}: UNDER", g, un)
            c3.add(f"{w}, total {'150+' if g['total'] >= 150 else 'under 140' if g['total'] < 140 else '140-150'}: OVER", g, ov)
            c3.add(f"{w}, total {'150+' if g['total'] >= 150 else 'under 140' if g['total'] < 140 else '140-150'}: UNDER", g, un)
            c3.add(f"{w}, {'conference' if g['conf'] else 'non-conference'}: OVER", g, ov)
            c3.add(f"{w}, {'conference' if g['conf'] else 'non-conference'}: UNDER", g, un)
        # both teams good from the line and whistle-heavy = free points
        if fouls >= 2.5 and H["ftp"] >= 0.74 and A["ftp"] >= 0.74:
            c3.add("whistle +2.5 and both teams shoot 74%+ at the line: OVER", g, ov)
        if fouls >= 2.5 and H["ftp"] <= 0.69 and A["ftp"] <= 0.69:
            c3.add("whistle +2.5 and both teams shoot 69% or worse: UNDER", g, un)
    for side in "HA":
        for k in ("pf", "fta"):
            if g[side]["bx"][k]:
                run[s][k][0] += g[side]["bx"][k]
                run[s][k][1] += 1
for c, t in ((c1, "S1 - THE 45%+ THREE-POINT TEAM"), (c2, "S2 - FREE THROWS IN CLOSE GAMES"),
             (c3, "S3 (swap) - THE WHISTLE THE TEAMS BRING, ON THE TOTAL"),
             (c4, "S4 (swap) - THE DEFENSE THAT GIVES UP THE THREE")):
    print("\n=====", t)
    c.lines.append(t + "  (TRAIN 2021-22 | HELD 2023-25; profit a unit at the close)")
    c.dump()
