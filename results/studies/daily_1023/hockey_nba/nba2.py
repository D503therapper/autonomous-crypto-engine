"""NBA, 2 studies (10/23): (4) late-season motivation (tanking / clinched teams in the last 20% of the schedule),
(5) the game after an OVERTIME game (extra minutes, worse on a back-to-back). Train 2018-24, HOLDOUT 2025-26,
current 2026-27. Every feature from earlier games only. Flat 1u at the close; also ATS at the closing spread."""
from common import *

fin, sched = load("nba")
TR = tuple(range(2018, 2025)); HO = (2025,); CU = (2026,)
idx = {t: {g["id"]: i for i, g in enumerate(gs)} for t, gs in sched.items()}
seasonlen = collections.Counter((t, season(g["start"])) for t, gs in sched.items() for g in gs)
rec = collections.defaultdict(lambda: [0, 0])
rows = []; ats = []
for g in fin:
    s = season(g["start"])
    feats = {}
    for side in ("home", "away"):
        t = g[side]; i = idx[t][g["id"]]; prev = sched[t][i-1] if i else None
        if prev is not None and season(prev["start"]) != s: prev = None
        b2b = prev is not None and (dt(g["start"]) - dt(prev["start"])).total_seconds() <= 30*3600
        pot = prev is not None and len((prev.get("ls_home") or "").split(",")) > 4
        p2ot = prev is not None and len((prev.get("ls_home") or "").split(",")) > 5
        pwon = None
        if prev is not None:
            ps = "home" if prev["home"] == t else "away"; po = "away" if ps == "home" else "home"
            pwon = float(prev[f"{ps}_score"]) > float(prev[f"{po}_score"])
        w, n = rec[(t, s)]; L = seasonlen[(t, s)]
        feats[side] = dict(b2b=b2b, pot=pot, p2ot=p2ot, pwon=pwon, gp=n, wp=(w / n if n else None), L=L, left=L - n)
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
                                dog=sp > 0, band="dog" if sp > 0 else "fav"))
    for side, oside in (("home", "away"), ("away", "home")):
        rec[(g[side], s)][0] += float(g[f"{side}_score"]) > float(g[f"{oside}_score"]); rec[(g[side], s)][1] += 1

R = lambda f, n, rs=rows: report(rs, f, n, TR, HO, CU)
print("rows", len(rows), "ats", len(ats))
print("\n#### baselines")
for b in ("dog", "fav"): R(lambda x, b=b: x["band"] == b, f"BASE ML {b}")
for b in ("dog", "fav"): R(lambda x, b=b: x["band"] == b, f"BASE ATS {b}", ats)

late = lambda x: x["L"] >= 60 and x["gp"] >= 0.8 * x["L"] and x["wp"] is not None and x["o_wp"] is not None
print("\n#### STUDY 4: LATE SEASON motivation (last 20% of the schedule)  [8 cells, ML + ATS]")
for nm, rs in (("ML", rows), ("ATS", ats)):
    R(lambda x: late(x) and x["band"] == "dog" and x["wp"] < .40, f"S4 {nm} dog, tanking-type team (< .400)", rs)
    R(lambda x: late(x) and x["band"] == "fav" and x["o_wp"] < .40 and .48 <= x["wp"] <= .60, f"S4 {nm} fav, bubble team (.480-.600) vs a < .400 team", rs)
    R(lambda x: late(x) and x["band"] == "fav" and x["wp"] >= .68 and x["left"] <= 6, f"S4 {nm} fav, .680+ team in its last 6 (rest risk)", rs)
    R(lambda x: late(x) and x["band"] == "dog" and x["o_wp"] >= .68 and x["o_left"] <= 6, f"S4 {nm} dog vs a .680+ team in its last 6", rs)

print("\n#### STUDY 5: the game AFTER an OVERTIME game  [8 cells]")
R(lambda x: x["band"] == "dog" and x["pot"], "S5 ML dog, I played OT last game")
R(lambda x: x["band"] == "fav" and x["pot"], "S5 ML fav, I played OT last game")
R(lambda x: x["band"] == "dog" and x["pot"] and x["b2b"], "S5 ML dog, OT last night (b2b)")
R(lambda x: x["band"] == "fav" and x["pot"] and x["b2b"], "S5 ML fav, OT last night (b2b)")
R(lambda x: x["band"] == "fav" and x["o_pot"] and x["o_b2b"] and not x["b2b"], "S5 ML fav vs a team off OT last night, me not b2b")
R(lambda x: x["band"] == "dog" and x["o_pot"] and x["o_b2b"] and not x["b2b"], "S5 ML dog vs a team off OT last night, me not b2b")
R(lambda x: x["pot"] and x["b2b"] and not x["o_b2b"], "S5 ATS off OT last night vs a non-b2b opp", ats)
R(lambda x: x["o_pot"] and x["o_b2b"] and not x["b2b"], "S5 ATS vs a team off OT last night, me not b2b", ats)
print("\n#### control: plain b2b vs non-b2b (built weight) so the OT add-on is read against it")
R(lambda x: x["b2b"] and not x["o_b2b"] and not x["pot"], "CTRL ATS b2b (no OT) vs non-b2b", ats)
R(lambda x: x["band"] == "fav" and x["o_b2b"] and not x["o_pot"] and not x["b2b"], "CTRL ML fav vs b2b (no OT) opp")
R(lambda x: x["band"] == "dog" and x["o_b2b"] and not x["o_pot"] and not x["b2b"], "CTRL ML dog vs b2b (no OT) opp")

print("\n#### STUDY 4 follow-up: FADE the tanking team AGAINST THE SPREAD (any opponent not itself < .400) + robustness cuts")
for wcut in (.35, .40, .45):
    for frac in (.75, .80, .85):
        lt = lambda x, frac=frac: x["L"] >= 60 and x["gp"] >= frac * x["L"] and x["wp"] is not None and x["o_wp"] is not None
        R(lambda x, w=wcut, lt=lt: lt(x) and x["o_wp"] < w and x["wp"] >= w, f"S4f ATS vs a < {w:.2f} team, last {int((1-frac)*100)}% of schedule", ats)
lt = lambda x: x["L"] >= 60 and x["gp"] >= .8 * x["L"] and x["wp"] is not None and x["o_wp"] is not None
R(lambda x: lt(x) and x["o_wp"] < .40 and x["wp"] >= .40 and x["ml"] < 0 and x["band"] == "fav", "S4f ATS fav side vs < .400 (spread fav)", ats)
R(lambda x: lt(x) and x["o_wp"] < .40 and x["wp"] >= .40, "S4f ML any price vs a < .400 team (second check: moneyline)")
R(lambda x: lt(x) and x["o_wp"] < .40 and x["wp"] >= .40 and -150 <= x["ml"] <= -100, "S4f ML -150..-100 vs a < .400 team")
R(lambda x: x["L"] >= 60 and x["gp"] < .5 * x["L"] and x["gp"] >= 20 and x["o_wp"] is not None and x["o_wp"] < .40 and x["wp"] >= .40, "S4f ATS vs a < .400 team in the FIRST half (control: is it late-season or just bad teams?)", ats)
R(lambda x: x["L"] >= 60 and .5 * x["L"] <= x["gp"] < .8 * x["L"] and x["o_wp"] is not None and x["o_wp"] < .40 and x["wp"] >= .40, "S4f ATS vs a < .400 team, games 50-80% (control)", ats)
