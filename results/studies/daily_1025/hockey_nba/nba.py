"""NBA, 2 studies (10/25). Train 2016-24, HOLDOUT 2025-26, current 2026-27. Flat 1u at the closing ML; ATS shown too.
S4 the SECOND game of a back-to-back set vs the same opponent (home-and-home = venue swapped; mini-series = same floor).
S5 a team's first game after a 5+ game homestand (its first road game).  Schedule of EARLIER games only."""
import collections
from common import *
fin, sched = load("nba")
TR = tuple(range(2016, 2025)); HO = (2025,); CU = (2026,)
idx = {t: {g["id"]: i for i, g in enumerate(gs)} for t, gs in sched.items()}
rows = []
for g in fin:
    s = season(g["start"]); feats = {}
    for side, oside in (("home", "away"), ("away", "home")):
        t = g[side]; i = idx[t][g["id"]]; prev = sched[t][i-1] if i else None
        if prev is not None and season(prev["start"]) != s: prev = None
        b2b = prev is not None and (dt(g["start"]) - dt(prev["start"])).total_seconds() <= 30*3600
        same = prev is not None and {prev["home"], prev["away"]} == {g["home"], g["away"]} and (dt(g["start"]) - dt(prev["start"])).days <= 4
        hh = same and prev["home"] != g["home"]; ms = same and prev["home"] == g["home"]
        lost1 = won1 = None; m1 = None
        if same:
            ps = "home" if prev["home"] == t else "away"; po = "away" if ps == "home" else "home"
            m1 = float(prev[f"{ps}_score"]) - float(prev[f"{po}_score"]); lost1 = m1 < 0
        # homestand length just finished: consecutive home games right before tonight
        hs = 0; j = i - 1
        while j >= 0 and sched[t][j]["home"] == t and season(sched[t][j]["start"]) == s: hs += 1; j -= 1
        feats[side] = dict(b2b=b2b, hh=hh, ms=ms, lost1=lost1, m1=m1, hs=hs)
    if g.get("ml_home") and g.get("ml_away"):
        for side, oside in (("home", "away"), ("away", "home")):
            ml = float(g[f"ml_{side}"]); oml = float(g[f"ml_{oside}"])
            nv = prob(ml) / (prob(ml) + prob(oml)); mar = float(g[f"{side}_score"]) - float(g[f"{oside}_score"]); won = mar > 0
            sp = g.get("spread_home"); ats = None
            if sp not in ("", None):
                line = float(sp) if side == "home" else -float(sp); c = mar + line
                ats = None if c == 0 else c > 0
            rows.append(dict(season=s, ml=ml, nv=nv, won=won, roi=pay(ml) if won else -1.0, home=side == "home", ats=ats,
                             **feats[side], **{"o_"+k: v for k, v in feats[oside].items()}))
R = lambda f, n: report(rows, f, n, TR, HO, CU)
def A(f, n):   # ATS at -110
    out = [n + " ATS"]
    for part, ss in (("TRAIN", TR), ("HOLD", HO)):
        rs = [x for x in rows if f(x) and x["season"] in ss and x["ats"] is not None]
        if rs:
            w = sum(x["ats"] for x in rs); out.append(f"{part} {w}-{len(rs)-w} {w/len(rs)*100:.1f}% ROI {(w*100/110-(len(rs)-w))/len(rs)*100:+.1f}%")
    print("   " + " | ".join(out))
dog = lambda x: 100 <= x["ml"] <= 350; fav = lambda x: -150 <= x["ml"] <= -100
print("rows", len(rows), "home-and-home 2nd games (sides)", sum(r["hh"] for r in rows), "mini-series 2nd", sum(r["ms"] for r in rows))
print("\n#### baselines"); R(dog, "BASE dog +100..+350"); R(fav, "BASE fav -150..-100")
print("\n#### S4 SECOND GAME vs the SAME OPPONENT  [10 cells]")
for nm, f in [("home-and-home, game-1 LOSER", lambda x: x["hh"] and x["lost1"]),
              ("home-and-home, game-1 WINNER", lambda x: x["hh"] and not x["lost1"]),
              ("home-and-home, tonight HOME", lambda x: x["hh"] and x["home"]),
              ("home-and-home, game-1 loser by 15+", lambda x: x["hh"] and x["m1"] <= -15),
              ("mini-series (same floor), game-1 LOSER", lambda x: x["ms"] and x["lost1"]),
              ("mini-series, game-1 loser by 15+", lambda x: x["ms"] and x["m1"] <= -15)]:
    for bn, b in (("dog", dog), ("fav", fav)):
        if "15+" in nm and bn == "fav": continue
        R(lambda x, f=f, b=b: b(x) and f(x), f"S4 {bn}: {nm}")
        A(lambda x, f=f, b=b: b(x) and f(x), f"S4 {bn}: {nm}")
print("\n#### S5 FIRST GAME AFTER A 5+ GAME HOMESTAND (first road game)  [8 cells]")
for k in (5, 6):
    for bn, b in (("dog", dog), ("fav", fav), ("all", lambda x: True)):
        if k == 6 and bn == "all": continue
        R(lambda x, b=b, k=k: b(x) and not x["home"] and x["hs"] >= k, f"S5 {bn}: first road game after {k}+ home")
        A(lambda x, b=b, k=k: b(x) and not x["home"] and x["hs"] >= k, f"S5 {bn}: first road game after {k}+ home")
R(lambda x: dog(x) and x["home"] and x["o_hs"] >= 5, "S5 home dog vs a team off a 5+ homestand")
R(lambda x: fav(x) and x["home"] and x["o_hs"] >= 5, "S5 home fav vs a team off a 5+ homestand")
R(lambda x: not x["home"] and x["hs"] >= 5 and x["b2b"], "S5 control: off 5+ homestand AND on a b2b")
R(lambda x: not x["home"] and x["hs"] >= 5 and not x["b2b"], "S5 control: off 5+ homestand, rested")
print("\n#### S5 follow-up: the HOME side facing a team off a 5+ homestand, any price; ATS by season")
R(lambda x: x["home"] and x["o_hs"] >= 5, "S5 home side (any price) vs a team off a 5+ homestand")
R(lambda x: x["home"] and x["o_hs"] >= 5 and -250 <= x["ml"] <= 350, "S5 home side -250..+350 vs a team off a 5+ homestand")
by = collections.defaultdict(lambda: [0, 0])
for x in rows:
    if not x["home"] and x["hs"] >= 5 and x["ats"] is not None: by[x["season"]][0 if x["ats"] else 1] += 1
print("   road team off 5+ homestand ATS by season (W-L): " + " ".join(f"{s%100}:{w}-{l}" for s, (w, l) in sorted(by.items())))
