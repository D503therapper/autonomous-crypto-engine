"""S5 / S6 (NHL) / S8 (NBA) - what the line scores say that the final doesn't (season to date, before tonight, 10+
games with line scores; regular season; the game file's ls_home / ls_away):
 S5 NHL FAST / SLOW STARTERS: the team's 1st-period goal differential a game minus a third of its whole goal
    differential a game (its 'first-period excess'): +0.25 or better = wins the first period more than its record
    says, -0.25 or worse = the slow starter. (The 3rd-period team over the last 5 is DEAD - this is the 1st, season long.)
 S6 NHL EXTRA-TIME LUCK: the team's record in games that went to OT / a shootout (5+ such games): .700+ = lucky
    (its standings points and record carry coin flips), .300 or under = unlucky; and the share of its wins that came
    in extra time (35%+).
 S8 NBA FAST STARTERS / CLOSERS: the 1st-quarter (and 4th-quarter) point differential a game minus a quarter of its
    whole differential: +2 / -2 points or more. (The 10/? 'lost the 4th 3 straight' is the last 3 only.)
Cells: as a dog +100..+350 and a favorite -101..-250 at the close; NBA also ATS. TRAIN = seasons to 2022, HELD 2023 /
2024 / 2025, 2026 live."""
from collections import defaultdict
import lib


def per(ls):
    try:
        return [int(x) for x in str(ls).split(",") if x != ""]
    except ValueError:
        return None


def run(lg, n_reg):
    fin = [g for g in lib.finals(lg) if g["stype"] == "2"]
    st = defaultdict(lambda: {"n": 0, "p1": 0, "plast": 0, "tot": 0, "otw": 0, "otl": 0, "w": 0})
    pre = {}
    for g in fin:
        for side in ("home", "away"):
            pre[(g["id"], side)] = dict(st[(g["season"], g[side])])
        h, a = per(g["ls_h"]), per(g["ls_a"])
        if not h or not a or len(h) < n_reg or len(a) < n_reg:
            continue
        ot = len(h) > n_reg or len(a) > n_reg
        for side, me, op, ms, os_ in (("home", h, a, g["hs"], g["as"]), ("away", a, h, g["as"], g["hs"])):
            r = st[(g["season"], g[side])]
            r["n"] += 1
            r["p1"] += me[0] - op[0]
            r["plast"] += me[n_reg - 1] - op[n_reg - 1]
            r["tot"] += ms - os_
            r["w"] += ms > os_
            if ot:
                r["otw" if ms > os_ else "otl"] += 1
    return fin, pre


cells = lib.Cells()
for lg, n_reg, thr in (("nhl", 3, 0.25), ("nba", 4, 2.0)):
    fin, pre = run(lg, n_reg)
    for g in fin:
        s = g["season"]
        for side, team, opp, o, won, home in lib.sides(g):
            r = pre.get((g["id"], side))
            if not r or r["n"] < 10:
                continue
            n = r["n"]
            share = r["tot"] / n / n_reg
            ex1 = r["p1"] / n - share
            exl = r["plast"] / n - share
            labs = []
            tag = "S5 NHL" if lg == "nhl" else "S8 NBA"
            if ex1 >= thr:
                labs.append(f"{tag} fast starter (1st excess +{thr}+)")
            elif ex1 <= -thr:
                labs.append(f"{tag} slow starter (1st excess -{thr}-)")
            else:
                labs.append(f"{tag} 1st excess within (control)")
            if lg == "nba":
                if exl >= thr:
                    labs.append("S8 NBA closer (4th excess +2+)")
                elif exl <= -thr:
                    labs.append("S8 NBA bad closer (4th excess -2-)")
            if lg == "nhl":
                otn = r["otw"] + r["otl"]
                if otn >= 5:
                    wp = r["otw"] / otn
                    if wp >= 0.7:
                        labs.append("S6 NHL OT/SO record .700+ (lucky)")
                    elif wp <= 0.3:
                        labs.append("S6 NHL OT/SO record .300- (unlucky)")
                    else:
                        labs.append("S6 NHL OT/SO record in between (control)")
                if r["w"] >= 5 and r["otw"] / r["w"] >= 0.35:
                    labs.append("S6 NHL 35%+ of its wins in extra time")
            pl = lib.profit(won, lib.dec(o))
            for lab in labs:
                if lib.dog_band(o):
                    cells.add(f"{lab} | DOG", s, pl)
                    if lg == "nhl" and "OT/SO" in lab:
                        oo = g["oh"] if home else g["oa"]
                        if oo and lib.dog_band(oo):
                            cells.add(f"{lab} | DOG open", s, lib.profit(won, lib.dec(oo)))
                elif -250 <= o <= -101:
                    cells.add(f"{lab} | FAV", s, pl)
                if lg == "nba":
                    cells.add(f"{lab} | ATS", s, lib.ats(g, side))
cells.dump("s5_s6_s8", "S5 / S6 / S8 - season-to-date period form (NHL 1st period, NHL extra time, NBA 1st / 4th quarter)",
           (2010, 2022), (2023, 2024, 2025, 2026))
