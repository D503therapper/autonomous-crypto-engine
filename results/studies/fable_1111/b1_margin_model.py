"""B1 (NFL, college football) / B2 (NBA) - A SPREAD HANDICAPPER'S MARGIN MODEL vs THE CLOSING SPREAD.
The 10/3 sweep graded the engine's own margin model (Elo + features) against the close: worse every season, strust = 0.
The owner's friend (11/11): the pros (Dr. Bob) bet spreads off their own number. This is that kind of number, built
from what spread handicappers use - the TEAM box scores (2021-26), season to date before kickoff / tip, no look-ahead:
  football: yards per play for / against, first downs per play (the success-rate stand-in the box allows), third-down
            rate, turnover margin (mostly luck - a handicapper regresses it), the point margin, the yard margin (the
            two together = the 11/10 yard luck), penalty yards, rest days, the home field;
  NBA:      the four factors for / against (eFG%, turnover rate, offensive-rebound rate, free-throw rate), the 3P luck
            (own 3P% minus the opponents'), the point margin, rest (a back-to-back), the home floor.
Two tests, each WALK-FORWARD (a season is read on a fit of the seasons before it only):
  (1) THE NUMBER: a ridge on the final margin -> the model's line; its error vs the closing spread's; the pros' rule
      'my number is 2 / 3 / 4+ points off the line' graded ATS at the close (and, in football, at the first FAIR
      spread of the paid odds history - the early price a pro would have taken);
  (2) THE RESIDUAL: a ridge on the COVER margin (what the spread missed) -> the predicted edge, ATS by its size.
First test season 2023 (2021-22 = the first fit); 2026 = the live season. Both teams 3+ boxed games (NBA 8+)."""
import math, statistics, sys
from collections import defaultdict
import numpy as np
import lib

B = lib.B
LG = sys.argv[1] if len(sys.argv) > 1 else "nfl"
TAG = {"nfl": "b1_nfl", "ncaaf": "b1_ncaaf", "nba": "b2_nba"}[LG]
FB = LG in ("nfl", "ncaaf")
MING = 8 if LG == "nba" else 3
o = lib.Out(TAG)
tb = lib.teambox(LG)
fin = [g for g in B.finals(LG) if g["stype"] == "2" and g["season"] >= 2021]
allf = [g for g in B.all_finals(LG) if g["stype"] == "2" and g["season"] >= 2021]
hist = {x["id"]: x for x in B.load_football(LG)} if FB else {}


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def line(t):
    """One team's box line -> the numbers the features need (None when the box is short)."""
    try:
        if FB:
            ca = lib.pair(t["completionAttempts"], "/")
            ra = f(t["rushingAttempts"])
            plays = f(t.get("totalOffensivePlays")) or (ca[1] + ra)
            td = lib.pair(t["thirdDownEff"])
            pen = lib.pair(t["totalPenaltiesYards"])
            return {"yd": f(t["totalYards"]), "pl": plays, "fd": f(t["firstDowns"]), "t3m": td[0], "t3a": td[1],
                    "to": f(t["turnovers"]), "pen": pen[1], "py": f(t["netPassingYards"]), "pa": ca[1],
                    "ry": f(t["rushingYards"]), "ra": ra}
        fg = lib.pair(t["fieldGoalsMade-fieldGoalsAttempted"])
        tp = lib.pair(t["threePointFieldGoalsMade-threePointFieldGoalsAttempted"])
        ft = lib.pair(t["freeThrowsMade-freeThrowsAttempted"])
        return {"fgm": fg[0], "fga": fg[1], "tpm": tp[0], "tpa": tp[1], "ftm": ft[0], "fta": ft[1],
                "orb": f(t["offensiveRebounds"]), "drb": f(t["defensiveRebounds"]),
                "to": f(t.get("totalTurnovers") or t["turnovers"])}
    except (KeyError, TypeError, ValueError):
        return None


KEYS = ["yd", "pl", "fd", "t3m", "t3a", "to", "pen", "py", "pa", "ry", "ra"] if FB else \
       ["fgm", "fga", "tpm", "tpa", "ftm", "fta", "orb", "drb", "to"]
run = defaultdict(lambda: {"n": 0, "pm": 0.0, "me": defaultdict(float), "op": defaultdict(float), "last": None})
pre = {}
for g in allf:
    for sd in ("home", "away"):
        r = run[(g["season"], g[sd])]
        pre[(g["id"], sd)] = {"n": r["n"], "pm": r["pm"], "me": dict(r["me"]), "op": dict(r["op"]), "last": r["last"]}
    t = tb.get(g["id"]) or {}
    lh, la = line(t.get(g["home"]) or {}), line(t.get(g["away"]) or {})
    ok = lh and la and all(v is not None for v in lh.values()) and all(v is not None for v in la.values())
    for sd, me, op, sg in (("home", lh, la, 1), ("away", la, lh, -1)):
        r = run[(g["season"], g[sd])]
        r["last"] = g["start"]
        if ok:
            r["n"] += 1
            r["pm"] += sg * (g["hs"] - g["as"])
            for k in KEYS:
                r["me"][k] += me[k]
                r["op"][k] += op[k]


def feats(p):
    n, me, op = p["n"], p["me"], p["op"]
    if FB:
        return [me["yd"] / me["pl"] - op["yd"] / op["pl"],                      # net yards per play
                me["fd"] / me["pl"] - op["fd"] / op["pl"],                      # net first downs per play
                me["t3m"] / max(1, me["t3a"]) - op["t3m"] / max(1, op["t3a"]),  # net third-down rate
                (op["to"] - me["to"]) / n,                                      # turnover margin a game
                p["pm"] / n,                                                    # point margin a game
                (me["yd"] - op["yd"]) / n / 10.0,                               # yard margin a game (per 10)
                (op["pen"] - me["pen"]) / n / 10.0,                             # penalty yards net (per 10)
                me["py"] / max(1, me["pa"]) - op["py"] / max(1, op["pa"]),      # net yards per pass
                me["ry"] / max(1, me["ra"]) - op["ry"] / max(1, op["ra"])]      # net yards per rush

    def four(a, b):
        poss = a["fga"] - a["orb"] + a["to"] + 0.44 * a["fta"]
        return ((a["fgm"] + 0.5 * a["tpm"]) / a["fga"], a["to"] / poss, a["orb"] / (a["orb"] + b["drb"]), a["fta"] / a["fga"])
    mo, od = four(me, op), four(op, me)
    return [100 * (mo[0] - od[0]), 100 * (od[1] - mo[1]), 100 * (mo[2] - od[2]), 100 * (mo[3] - od[3]),
            p["pm"] / n, 100 * (me["tpm"] / me["tpa"] - op["tpm"] / op["tpa"])]


NAMES = (["net yards/play", "net 1st downs/play", "net 3rd-down rate", "turnover margin", "point margin", "yard margin /10",
          "penalty yds net /10", "net yards/pass", "net yards/rush"] if FB else
         ["net eFG%", "net turnover rate", "net off-rebound rate", "net FT rate", "point margin", "3P% net (luck)"])
NAMES = ["home field"] + NAMES + ["rest edge (days, capped 3)"] + ([] if FB else ["home b2b", "away b2b"])
rows = []
for g in fin:
    ph, pa = pre.get((g["id"], "home")), pre.get((g["id"], "away"))
    if not ph or not pa or ph["n"] < MING or pa["n"] < MING or g["sp"] is None:
        continue
    try:
        fh, fa = feats(ph), feats(pa)
    except (ZeroDivisionError, KeyError):
        continue
    rh = B.days_between(ph["last"], g["start"]) if ph["last"] else 7
    ra = B.days_between(pa["last"], g["start"]) if pa["last"] else 7
    x = [0.0 if g["neutral"] else 1.0] + [a - b for a, b in zip(fh, fa)] + [max(-3, min(3, rh - ra))]
    if not FB:
        x += [1.0 if rh <= 1.3 else 0.0, 1.0 if ra <= 1.3 else 0.0]
    m = g["hs"] - g["as"]
    e = None
    if FB and g["id"] in hist:
        ff = B.first_fair(hist[g["id"]]["sp"])
        if ff:
            e = B.sp_med(ff[1])                                       # (home pts, home dec, away dec) at the first fair look
    rows.append({"s": g["season"], "x": x, "m": m, "sp": g["sp"], "g": g, "early": e})

o.p(f"{TAG} - {LG}: {len(rows)} priced regular-season games with {MING}+ boxed games each (2021-26)")
mu = np.mean([r["x"] for r in rows if r["s"] <= 2022], axis=0)
sdv = np.std([r["x"] for r in rows if r["s"] <= 2022], axis=0) + 1e-9
sdv[0], mu[0] = 1.0, 0.0
C = lib.Cells()
errs = defaultdict(lambda: [0.0, 0.0, 0.0, 0])
blend = defaultdict(lambda: [0.0, 0.0])
LAM = 30.0 if LG != "nba" else 10.0
CUTS = (2, 3, 4, 6) if FB else (1.5, 2.5, 4)
RC = (0.5, 1.0, 1.5) if LG != "ncaaf" else (1.0, 2.0, 3.0)
for hs in (2023, 2024, 2025, 2026):
    tr = [r for r in rows if r["s"] < hs]
    te = [r for r in rows if r["s"] == hs]
    if not te:
        continue
    Z = lambda r: list((np.array(r["x"]) - mu) / sdv)
    b1 = lib.ridge([Z(r) for r in tr], [r["m"] for r in tr], LAM)             # the number
    b2 = lib.ridge([Z(r) for r in tr], [r["m"] + r["sp"] for r in tr], LAM * 5)   # the residual
    if hs == 2025:
        o.p("the NUMBER's weights (points per 1 sd, fit 2021-24):  " + "; ".join(f"{n} {w:+.2f}" for n, w in zip(NAMES, b1)))
        o.p("the RESIDUAL's weights (what the spread misses):       " + "; ".join(f"{n} {w:+.2f}" for n, w in zip(NAMES, b2)))
    for r in te:
        g = r["g"]
        z = np.array(Z(r))
        num = float(z @ b1)
        res = float(z @ b2)
        mk = -r["sp"]
        E = errs[hs]
        E[0] += (r["m"] - num) ** 2; E[1] += (r["m"] - mk) ** 2; E[2] += (r["m"] - (mk + 0.2 * (num - mk))) ** 2; E[3] += 1
        blend[hs][0] += (num - mk) * (r["m"] - mk); blend[hs][1] += (num - mk) ** 2
        d = num - mk                                                      # + = my number likes the home side more
        side = "home" if d > 0 else "away"
        a = B.ats(g, side)
        for cut in CUTS:
            if abs(d) >= cut:
                C.add(f"KEY (1) my number {cut}+ pts off the CLOSE", hs, a)
                sp_side = g["sp"] if side == "home" else -g["sp"]
                C.add(f"(1) {cut}+ off the close: on the {'dog' if sp_side > 0 else 'favorite'}", hs, a)
                if r["early"]:
                    pts, dh, da = r["early"]
                    de = num + pts                                        # vs the early line (-pts)
                    if abs(de) >= cut:
                        es = "home" if de > 0 else "away"
                        cov = (r["m"] + pts) if es == "home" else -(r["m"] + pts)
                        if cov != 0:
                            C.add(f"KEY (1) my number {cut}+ off the FIRST FAIR spread (early price)", hs,
                                  lib.profit(cov > 0, dh if es == "home" else da))
        side2 = "home" if res > 0 else "away"
        a2 = B.ats(g, side2)
        for cut in RC:
            if abs(res) >= cut:
                C.add(f"KEY (2) predicted cover edge {cut}+ pts", hs, a2)
                sp_side = g["sp"] if side2 == "home" else -g["sp"]
                C.add(f"(2) cover edge {cut}+: on the {'dog' if sp_side > 0 else 'favorite'}", hs, a2)
        C.add("BASE every home side ATS", hs, B.ats(g, "home"))
o.p("\nRMSE of the final margin, each test season:  my number | the closing spread | the spread + 20% of my gap | OLS weight on (my number - the spread)")
for hs in sorted(errs):
    E = errs[hs]
    o.p(f"  {hs}: {math.sqrt(E[0]/E[3]):6.2f} | {math.sqrt(E[1]/E[3]):6.2f} | {math.sqrt(E[2]/E[3]):6.2f} | {blend[hs][0]/max(1e-9, blend[hs][1]):+.3f}   (n {E[3]})")
o.p("")
o.cells(C, (2023, 2023), (2024, 2025, 2026), zshow=99)
o.p(f"\ncells: {len(C.c)}  (TRAIN column = 2023, the first walk-forward season; every column is out of sample)")
o.save()
