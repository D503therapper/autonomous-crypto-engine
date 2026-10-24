"""NBA, 2 NEW studies (10/24). Train 2018-24, HOLDOUT 2025-26, current 2026-27. Flat 1u at the close (ML) and ATS at the
closing spread. S4: the game after a 30+ point loss (and 20-29). S5: the FAVORITE whose last 3 wins were all close (5 or
less / OT) - the built 'won 2+ close' fade is for dogs only. Every feature from earlier games only."""
from common import *
fin, sched = load("nba")
TR = tuple(range(2018, 2025)); HO = (2025,); CU = (2026,)
idx = {t: {g["id"]: i for i, g in enumerate(gs)} for t, gs in sched.items()}
wins = collections.defaultdict(list); wm = collections.defaultdict(list)
rows = []; ats = []
for g in fin:
    s = season(g["start"]); feats = {}
    for side in ("home", "away"):
        t = g[side]; i = idx[t][g["id"]]; prev = sched[t][i-1] if i else None
        if prev is not None and season(prev["start"]) != s: prev = None
        b2b = prev is not None and (dt(g["start"]) - dt(prev["start"])).total_seconds() <= 30*3600
        pm = None
        if prev is not None:
            ps = "home" if prev["home"] == t else "away"; po = "away" if ps == "home" else "home"
            pm = float(prev[f"{ps}_score"]) - float(prev[f"{po}_score"])
        w3 = wins[(t, s)][-3:]
        feats[side] = dict(b2b=b2b, pm=pm, allclose=len(w3) == 3 and all(c for c in w3),
                           noneclose=len(w3) == 3 and not any(c for c in w3),
                           two3=len(w3) == 3 and sum(w3) >= 2, reg3=len(wm[(t, s)]) >= 3 and all(m <= 5 and not o for m, o in wm[(t, s)][-3:]),
                           tight3=len(wm[(t, s)]) >= 3 and all(m <= 3 for m, o in wm[(t, s)][-3:]), gp=len(wm[(t,s)]))
    for side, oside in (("home", "away"), ("away", "home")):
        me, op = feats[side], feats[oside]
        won = float(g[f"{side}_score"]) > float(g[f"{oside}_score"])
        base = dict(season=s, home=side == "home", **me, **{"o_"+k: v for k, v in op.items()})
        if g.get("ml_home") and g.get("ml_away"):
            ml = float(g[f"ml_{side}"]); oml = float(g[f"ml_{oside}"])
            nv = prob(ml) / (prob(ml) + prob(oml))
            rows.append(dict(base, ml=ml, nv=nv, won=won, roi=pay(ml) if won else -1.0, band=band(ml)))
        if g.get("spread_home") not in ("", None) and g.get("spread_home_odds") and g.get("spread_away_odds"):
            sp = float(g["spread_home"]) * (1 if side == "home" else -1)
            mg = float(g[f"{side}_score"]) - float(g[f"{oside}_score"]) + sp
            if mg != 0:
                o = float(g[f"spread_{side}_odds"]); oo = float(g[f"spread_{oside}_odds"])
                ats.append(dict(base, ml=o, nv=prob(o)/(prob(o)+prob(oo)), won=mg > 0, roi=pay(o) if mg > 0 else -1.0,
                                band="dog" if sp > 0 else "fav"))
    ot = len((g.get("ls_home") or "").split(",")) > 4
    for side, oside in (("home", "away"), ("away", "home")):
        m = float(g[f"{side}_score"]) - float(g[f"{oside}_score"])
        if m > 0: wins[(g[side], s)].append(m <= 5 or ot); wm[(g[side], s)].append((m, ot))
R = lambda f, n, rs=rows: report(rs, f, n, TR, HO, CU)
print("rows", len(rows), "ats", len(ats))
print("\n#### baselines")
for nm, rs in (("ML", rows), ("ATS", ats)):
    for b in ("dog", "fav"): R(lambda x, b=b: x["band"] == b, f"BASE {nm} {b}", rs)
    for b in ("dog", "fav"): R(lambda x, b=b: x["band"] == b and x["pm"] is not None and x["pm"] < 0, f"BASE {nm} {b} lost last (any)", rs)
print("\n#### S4 THE GAME AFTER A 30+ POINT LOSS  [12 cells]")
for nm, rs in (("ML", rows), ("ATS", ats)):
    for b in ("dog", "fav"):
        R(lambda x, b=b: x["band"] == b and x["pm"] is not None and x["pm"] <= -30, f"S4 {nm} {b}: lost last by 30+", rs)
        R(lambda x, b=b: x["band"] == b and x["pm"] is not None and -29 <= x["pm"] <= -20, f"S4 {nm} {b}: lost last by 20-29", rs)
        R(lambda x, b=b: x["band"] == b and x["o_pm"] is not None and x["o_pm"] <= -30 and not (x["pm"] is not None and x["pm"] <= -30), f"S4 {nm} {b}: vs a team off a 30+ loss", rs)
print("\n#### S5 THE ALL-CLOSE WINNER: last 3 wins all 5 or less / OT  [8 cells]")
for nm, rs in (("ML", rows), ("ATS", ats)):
    R(lambda x: x["band"] == "fav" and x["allclose"], f"S5 {nm} fav: last 3 wins all close", rs)
    R(lambda x: x["band"] == "fav" and x["noneclose"], f"S5 {nm} fav: last 3 wins all 6+ (mirror)", rs)
    R(lambda x: x["band"] == "dog" and x["o_allclose"] and not x["allclose"], f"S5 {nm} dog vs an all-close favorite", rs)
    R(lambda x: x["band"] == "fav" and x["allclose"] and not x["o_allclose"] and x["home"], f"S5 {nm} HOME fav: last 3 wins all close", rs)

print("\n#### S5 ROBUSTNESS (ATS + ML favorites)")
for nm, rs in (("ML", rows), ("ATS", ats)):
    R(lambda x: x["band"] == "fav" and x["two3"] and not x["allclose"], f"S5r {nm} fav: exactly 2 of last 3 wins close", rs)
    R(lambda x: x["band"] == "fav" and x["reg3"], f"S5r {nm} fav: last 3 wins all 5 or less in regulation (no OT)", rs)
    R(lambda x: x["band"] == "fav" and x["tight3"], f"S5r {nm} fav: last 3 wins all 3 or less", rs)
    R(lambda x: x["band"] == "fav" and x["allclose"] and x["pm"] is not None and x["pm"] > 0, f"S5r {nm} fav: all-close AND won last game", rs)
    R(lambda x: x["band"] == "fav" and x["allclose"] and x["pm"] is not None and x["pm"] < 0, f"S5r {nm} fav: all-close AND lost last game", rs)
    R(lambda x: x["band"] == "fav" and x["allclose"] and x["o_allclose"], f"S5r {nm} fav: all-close vs an all-close opp", rs)
R(lambda x: x["band"] == "fav" and x["allclose"] and x["ml"] >= -400, "S5r ATS fav all-close, ML -400 or shorter-priced only", ats)
