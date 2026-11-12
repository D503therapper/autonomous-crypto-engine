"""11/12 follow-ups on the cells that stood out in studies 1-10: the dose, the venue / price / month cuts, the open,
the side across, a placebo (random draws of the same size from the cell's own base) and the live 2026-27 rows.
A the net turnover MATCHUP (S8); B the rusty HOME side and the rusty small favorite (S5); C the home loss as a small
favorite (S7); D the defense that takes the three away, as a small favorite (S4); F the leader with a cushion on the
road (S10); G the late-season over when both teams are out of it (S10)."""
from collections import defaultdict
import lib

R = lib.build()
BX = ((2021, 2022), (2023, 2024, 2025))
SC = ((2018, 2021), (2022, 2023, 2024, 2025))
A_, B_, C_, D_, F_, G_ = (lib.Cells(f"s11{x}", *sp) for x, sp in (("a", BX), ("b", SC), ("c", SC), ("d", BX), ("f", SC), ("g", SC)))
AVG_TO = 0.178
base = defaultdict(list)       # name -> profits (the placebo pools)
cell = defaultdict(list)
tab = defaultdict(dict)


def losing(f):
    """This season's current losing streak (from the last game back)."""
    return f.get("skid", 0)


hist_skid = defaultdict(int)
for g in R:
    if g["season"] < 2018:
        continue
    s, mon, d = g["season"], g["day"].month, g["day"]
    H, A = g["H"], g["A"]
    ov, un = lib.tot_p(g, True), lib.tot_p(g, False)
    reg = g["stype"] == "2"
    H["skid"], A["skid"] = hist_skid[(s, g["home"])], hist_skid[(s, g["away"])]
    for side, f in (("H", H), ("A", A)):
        t = g["home"] if side == "H" else g["away"]
        if f["ck"] is not None:
            tb = tab[(s, f["ck"])]
            tb.setdefault(t, [0, 0])
            ds = sorted((w - l for w, l in tb.values()), reverse=True)
            best, second = ds[0], (ds[1] if len(ds) > 1 else ds[0])
            f["gb"] = (best - (tb[t][0] - tb[t][1])) / 2
            f["cushion"] = (tb[t][0] - tb[t][1] - second) / 2 if tb[t][0] - tb[t][1] == best else None
            f["cg"] = tb[t][0] + tb[t][1]
            f["cpct"] = tb[t][0] / f["cg"] if f["cg"] else None
    if g["mlh"] and reg:
        boxed = bool(lib.both(g, 5))
        for side, f, o in lib.both(g):
            if "rest" not in f or "rest" not in o:
                continue
            od, sp = lib.odds(g, side), lib.spread(g, side)
            bd = lib.band(od)
            ml, at, op = lib.ml_p(g, side), lib.ats_p(g, side), lib.ml_open_p(g, side)
            v = lib.ven(g, side)
            os_ = lib.other(side)
            # ---------------- A: the net turnover matchup ----------------
            if boxed and s >= 2021:
                b, ob = f["bx"], o["bx"]
                own = b["o_tor"] - b["tor"]              # my turnover margin per possession
                opp = ob["o_tor"] - ob["tor"]
                net = own - opp
                if bd == "dog" and ml is not None:
                    base["dog"].append(ml)
                if at is not None:
                    base["ats"].append(at)
                if bd == "sfav" and ml is not None:
                    base["sfav"].append(ml)
                nb = ("-.07 or less" if net <= -0.07 else "-.07..-.05" if net <= -0.05 else "-.05..-.04" if net <= -0.04
                      else "-.04..-.02" if net <= -0.02 else "-.02..+.02" if net < 0.02 else "+.02..+.04" if net < 0.04
                      else "+.04..+.05" if net < 0.05 else "+.05..+.07" if net < 0.07 else "+.07 or more")
                if bd in ("dog", "sfav", "bfav"):
                    A_.add(f"DOSE net {nb}: {bd} ML", g, ml)
                A_.add(f"DOSE net {nb}: ATS", g, at)
                if net <= -0.05:
                    if at is not None:
                        cell["A ats"].append(at)
                    A_.add(f"NET -.05 ATS ven {v}", g, at)
                    A_.add(f"NET -.05 ATS {'Nov-Dec' if mon in (11, 12) else 'Jan-Mar'}", g, at)
                    A_.add(f"NET -.05 ATS as {'the favorite' if (sp or 0) < 0 else 'the dog'}", g, at)
                    A_.add("NET -.05: the side ACROSS ATS", g, lib.ats_p(g, os_))
                    if bd == "dog":
                        cell["A dog"].append(ml)
                        A_.add("NET -.05 dog ML", g, ml)
                        A_.add("NET -.05 dog ML at the OPEN", g, op)
                        A_.add(f"NET -.05 dog {'+100..+200' if od <= 200 else '+201..+350'} ML", g, ml)
                        A_.add(f"NET -.05 dog ven {v} ML", g, ml)
                        A_.add(f"NET -.05 dog {'Nov-Dec' if mon in (11, 12) else 'Jan-Mar'} ML", g, ml)
                        why = ("my own margin is bad AND theirs is good" if own <= -0.02 and opp >= 0.02 else
                               "my own margin is bad (theirs ordinary)" if own <= -0.02 else
                               "theirs is good (mine ordinary)" if opp >= 0.02 else "both middling")
                        A_.add(f"NET -.05 dog, {why}: ML", g, ml)
                        A_.add(f"NET -.05 dog, {'on a 5+ skid' if f['skid'] >= 5 else 'no 5+ skid'}: ML", g, ml)
                        A_.add(f"NET -.05 dog, {'5-9 box games' if b['n'] < 10 else '10-19 box games' if b['n'] < 20 else '20+ box games'}: ML", g, ml)
                        A_.add("NET -.05 dog: the FAVORITE across ML", g, lib.ml_p(g, os_))
                        if g["season"] == 2026:
                            A_.add("LIVE 2026-27: NET -.05 dog ML", g, ml)
                    if bd == "sfav":
                        cell["A sfav"].append(ml)
                        A_.add("NET -.05 small fav ML", g, ml)
                        A_.add("NET -.05 small fav ML at the OPEN", g, op)
                        prone = own * b["pace"] <= -0.5
                        A_.add(f"NET -.05 small fav, {'turnover-prone itself (the built weight)' if prone else 'NOT turnover-prone itself'}: ML", g, ml)
                        A_.add("NET -.05 small fav: the DOG across ML", g, lib.ml_p(g, os_))
                if net >= 0.05:
                    if bd == "sfav":
                        A_.add("NET +.05 small fav ML", g, ml)
                        A_.add("NET +.05 small fav ML at the OPEN", g, op)
                    if bd == "dog":
                        A_.add("NET +.05 dog ML", g, ml)
                        A_.add(f"NET +.05 dog ven {v} ML", g, ml)
                # the built weight's cell alone, for the overlap
                if bd == "dog" and own * b["pace"] <= -0.5:
                    A_.add(f"turnover-prone dog (own margin -0.5 a game), net {'-.05 or less' if net <= -0.05 else 'better than -.05'}: ML", g, ml)
                # ---------------- D: the defense that takes the three away ----------------
                if bd == "sfav":
                    x = b["o_tpr"]
                    db = ("<=.32" if x <= 0.32 else ".32-.34" if x <= 0.34 else ".34-.36" if x <= 0.36 else ".36-.39" if x <= 0.39
                          else ".39-.42" if x <= 0.42 else ".42+")
                    D_.add(f"small fav, opponents' 3PA share {db}: ML", g, ml)
                    D_.add(f"small fav, opponents' 3PA share {db}: ML at the OPEN", g, op)
                    D_.add(f"small fav, opponents' 3PA share {db}: ATS", g, at)
                    if x <= 0.34:
                        cell["D sfav"].append(ml)
                        D_.add(f"D takes the three away, small fav ven {v}: ML", g, ml)
                        D_.add(f"D takes the three away, small fav {'Nov-Dec' if mon in (11, 12) else 'Jan-Mar'}: ML", g, ml)
                        D_.add(f"D takes the three away, small fav, own 3PA share {'40+' if b['tpr'] >= 0.40 else 'under 40'}: ML", g, ml)
                        D_.add("D takes the three away, small fav: the DOG across ML", g, lib.ml_p(g, os_))
                    y = b["tpr"]
                    tb3 = "<.33" if y < 0.33 else ".33-.40" if y < 0.40 else ".40-.42" if y < 0.42 else ".42-.45" if y < 0.45 else ".45+"
                    D_.add(f"(S1 dose) small fav, own 3PA share {tb3}: ML", g, ml)
                    D_.add(f"(S1 dose) small fav, own 3PA share {tb3}: the DOG across ML", g, lib.ml_p(g, os_))
            # ---------------- B: rust ----------------
            if f["n"] >= 4 and o["n"] >= 4:
                if at is not None:
                    base["ats_all"].append(at)
                if bd == "sfav":
                    base["sfav_all"].append(ml)
                if f["rest"] >= 7:
                    ob_ = "1-2" if o["rest"] <= 2 else "3-4" if o["rest"] <= 4 else "5-6" if o["rest"] <= 6 else "7+"
                    if v == "H":
                        B_.add(f"RUSTY HOME side (7+ off), the visitor's rest {ob_}: ATS", g, at)
                    if bd == "sfav":
                        B_.add(f"RUSTY small fav, the opponent's rest {ob_}: ML", g, ml)
                if f["rest"] >= 7 and o["rest"] <= 4:
                    win = "Dec 10-31" if (mon == 12 and d.day >= 10) else "other dates"
                    if v == "H":
                        cell["B home"].append(at) if at is not None else None
                        B_.add("RUSTY HOME side vs a visitor in rhythm: ATS", g, at)
                        B_.add("RUSTY HOME: the visitor ACROSS ATS", g, lib.ats_p(g, os_))
                        B_.add(f"RUSTY HOME ATS, {'favorite' if (sp or 0) < 0 else 'dog'}", g, at)
                        B_.add(f"RUSTY HOME ATS, {win}", g, at)
                        B_.add(f"RUSTY HOME ATS, off {'7-9' if f['rest'] <= 9 else '10+'} days", g, at)
                        B_.add(f"RUSTY HOME ATS, {'conference' if g['conf'] else 'non-conference'}", g, at)
                        if sp is not None:
                            B_.add(f"RUSTY HOME ATS, {'laying 8+' if sp <= -8 else 'laying under 8' if sp < 0 else 'getting points'}", g, at)
                            B_.add(f"RUSTY HOME: the visitor ACROSS ATS, {'getting 8+' if sp <= -8 else 'getting under 8' if sp < 0 else 'laying points'}", g, lib.ats_p(g, os_))
                        if bd:
                            B_.add(f"RUSTY HOME {bd} ML", g, ml)
                            B_.add(f"RUSTY HOME {bd}: the side across ML", g, lib.ml_p(g, os_))
                        if g["season"] == 2026:
                            B_.add("LIVE 2026-27: RUSTY HOME ATS", g, at)
                    if bd == "sfav":
                        cell["B sfav"].append(ml)
                        B_.add("RUSTY small fav ML", g, ml)
                        B_.add("RUSTY small fav ML at the OPEN", g, op)
                        B_.add(f"RUSTY small fav ML, {win}", g, ml)
                        B_.add(f"RUSTY small fav ML, {'-101..-125' if od >= -125 else '-126..-150'}", g, ml)
                        B_.add("RUSTY small fav: the DOG across ML", g, lib.ml_p(g, os_))
                        B_.add("RUSTY small fav ATS", g, at)
            # ---------------- C: lost at home as a small favorite ----------------
            L = f["last"]
            if bd == "dog":
                base["dog_all"].append(ml)
            if L["ven"] == "H" and not L["won"] and L["ml"] is not None and L["ml"] < 0 and f["rest"] <= 10 and bd == "dog":
                pb = ("-101..-125" if L["ml"] >= -125 else "-126..-150" if L["ml"] >= -150 else "-151..-200" if L["ml"] >= -200
                      else "-201..-299" if L["ml"] > -300 else "-300..-499" if L["ml"] > -500 else "-500 or more")
                C_.add(f"DOSE lost at home as {pb}, next as a dog: ML", g, ml)
                C_.add(f"DOSE lost at home as {pb}, next as a dog: ML at the OPEN", g, op)
                if L["ml"] >= -150:
                    cell["C dog"].append(ml)
                    C_.add("LOST AT HOME AS A SMALL FAV, next as a dog: ML", g, ml)
                    C_.add(f"...ven {v}: ML", g, ml)
                    C_.add(f"...{'+100..+200' if od <= 200 else '+201..+350'}: ML", g, ml)
                    C_.add(f"...{'Nov-Dec' if mon in (11, 12) else 'Jan-Mar'}: ML", g, ml)
                    C_.add(f"...{'on a 5+ skid' if f['skid'] >= 5 else 'on a 2-4 skid' if f['skid'] >= 2 else 'first loss in a row'}: ML", g, ml)
                    C_.add(f"...lost by {'10+' if L['m'] <= -10 else '1-9'}: ML", g, ml)
                    C_.add("...the FAVORITE across ML", g, lib.ml_p(g, os_))
                    if g["season"] == 2026:
                        C_.add("LIVE 2026-27: lost at home as a small fav, next as a dog", g, ml)
                if L["ml"] <= -300:
                    cell["C big"].append(ml)
                    C_.add("LOST AT HOME AS A -300+ FAV, next as a dog: ML", g, ml)
                    C_.add(f"...(-300+) ven {v}: ML", g, ml)
                    C_.add(f"...(-300+) {'+100..+200' if od <= 200 else '+201..+350'}: ML", g, ml)
            # control: lost on the ROAD as a small favorite, next as a dog
            if L["ven"] == "A" and not L["won"] and L["ml"] is not None and -150 <= L["ml"] < 0 and f["rest"] <= 10 and bd == "dog":
                C_.add("CONTROL lost on the ROAD as a small fav, next as a dog: ML", g, ml)
            if L["ven"] == "H" and not L["won"] and L["ml"] is not None and L["ml"] > 0 and f["rest"] <= 10 and bd == "dog":
                C_.add("CONTROL lost at home as a DOG, next as a dog: ML", g, ml)
            # ---------------- F / G: late-season ----------------
            if mon in (2, 3) and g["conf"] and "gb" in f and "gb" in o and f["cg"] >= 8 and o["cg"] >= 8 and not g["neutral"]:
                late = (mon == 3) or d.day >= 15
                cu = f.get("cushion")
                if cu is not None and v == "A":
                    cb = "3+" if cu >= 3 else "2-2.5" if cu >= 2 else "1-1.5" if cu >= 1 else "0-0.5"
                    F_.add(f"the leader on the ROAD, cushion {cb}, {'Feb 15+' if late else 'Feb 1-14'}: ATS", g, at)
                    if late and cu >= 2:
                        cell["F road"].append(at) if at is not None else None
                        F_.add("CUSHION 2+ on the road: the HOME side across ATS", g, lib.ats_p(g, os_))
                        F_.add(f"CUSHION 2+ on the road, {'laying 6+' if (sp or 0) <= -6 else 'laying under 6 / a dog'}: ATS", g, at)
                        F_.add(f"CUSHION 2+ on the road, the home team {'.500+' if o['cpct'] >= 0.5 else 'under .500'} in the league: ATS", g, at)
                        if bd:
                            F_.add(f"CUSHION 2+ on the road: {bd} ML", g, ml)
                            F_.add(f"CUSHION 2+ on the road, {bd}: the home side across ML", g, lib.ml_p(g, os_))
                if late and at is not None and v == "A":
                    base["late_road"].append(at)
                if side == "H":
                    for cut in (0.25, 0.30, 0.35, 0.40):
                        if f["cpct"] <= cut and o["cpct"] <= cut:
                            G_.add(f"BOTH league {cut:.2f} or worse, {'Feb 15+' if late else 'Feb 1-14'}: OVER", g, ov)
                            G_.add(f"BOTH league {cut:.2f} or worse, {'Feb 15+' if late else 'Feb 1-14'}: UNDER", g, un)
                    if late:
                        if ov is not None:
                            base["late_over"].append(ov)
                        G_.add("BASE Feb 15+ conference: OVER", g, ov)
                        G_.add("BASE Feb 15+ conference: UNDER", g, un)
                        if f["cpct"] <= 0.30 and o["cpct"] <= 0.30:
                            cell["G over"].append(ov) if ov is not None else None
                            G_.add(f"BOTH .300 or worse, total {'under 140' if (g['total'] or 0) < 140 else '140+'}: OVER", g, ov)
                            G_.add("BOTH .300 or worse: this game's miss (points - total)", g, (g["hs"] + g["as"] - g["total"]) if g["total"] is not None else None)
                        if min(f["cpct"], o["cpct"]) <= 0.30 and max(f["cpct"], o["cpct"]) > 0.30:
                            G_.add("ONE team .300 or worse (the other not): OVER", g, ov)
                        if f["gb"] >= 5 and o["gb"] >= 5:
                            G_.add("BOTH 5+ games back, Feb 15+: OVER", g, ov)
                            G_.add("BOTH 5+ games back, Feb 15+: UNDER", g, un)
    # after the game
    hw = g["hs"] > g["as"]
    hist_skid[(s, g["home"])] = 0 if hw else hist_skid[(s, g["home"])] + 1
    hist_skid[(s, g["away"])] = 0 if not hw else hist_skid[(s, g["away"])] + 1
    if g["conf"] and reg and H["ck"] is not None:
        tb = tab[(s, H["ck"])]
        tb.setdefault(g["home"], [0, 0])[0 if hw else 1] += 1
        tb.setdefault(g["away"], [0, 0])[1 if hw else 0] += 1

PL = (("A dog", "dog", A_), ("A sfav", "sfav", A_), ("A ats", "ats", A_), ("B home", "ats_all", B_), ("B sfav", "sfav_all", B_),
      ("C dog", "dog_all", C_), ("C big", "dog_all", C_), ("D sfav", "sfav", D_), ("F road", "late_road", F_),
      ("G over", "late_over", G_))
for name, bname, c in PL:
    if cell[name]:
        k = lib.placebo(cell[name], base[bname])
        c.lines.append(f"PLACEBO {name}: {len(cell[name])} bets at {sum(cell[name])/len(cell[name])*100:+.1f}% vs the base "
                       f"{sum(base[bname])/len(base[bname])*100:+.1f}% on {len(base[bname])} - a random draw of the same size "
                       f"landed as far from the base {k} of 2,000 times")
        print(c.lines[-1])
for c, t in ((A_, "A - THE NET TURNOVER MATCHUP (S8)"), (B_, "B - RUST (S5)"), (C_, "C - LOST AT HOME AS A FAVORITE (S7)"),
             (D_, "D - THE DEFENSE THAT TAKES THE THREE AWAY + the S1 dose"), (F_, "F - THE LEADER WITH A CUSHION ON THE ROAD (S10)"),
             (G_, "G - BOTH TEAMS OUT OF IT: THE OVER (S10)")):
    print("\n=====", t)
    c.lines.insert(0, t)
    c.dump()
