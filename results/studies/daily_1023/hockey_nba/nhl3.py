"""NHL, 3 studies (10/23): (1) Sat->Sun back-to-back, (2) late-season motivation (out-of-race / clinched teams),
(3) the HOT starting goalie (last-5-starts save %). Train 2016-24, HOLDOUT 2025-26, current 2026-27.
No look-ahead: every feature from earlier games; the starter is the confirmed game-day starter (the bet waits for it,
like the engine's goalie line). Flat 1u at the close."""
import collections, csv
from common import *

fin, sched = load("nhl")
TR = tuple(range(2016, 2025)); HO = (2025,); CU = (2026,)
# goalie lines: (gid, team) -> {name: (sa, ga)}
gl = collections.defaultdict(dict)
with open(WT + "/data/sports/players/nhl.csv") as f:
    for r in csv.DictReader(f):
        if r["role"] == "G" and r["sa"]:
            gl[(r["gid"], r["team"])][r["player"]] = (float(r["sa"]), float(r["ga"] or 0))
idx = {t: {g["id"]: i for i, g in enumerate(gs)} for t, gs in sched.items()}
seasonlen = collections.Counter((t, season(g["start"])) for t, gs in sched.items() for g in gs)
goalie_hist = collections.defaultdict(list)  # (team, name) -> [(start, sa, ga)] built in order
# walk games in order, compute features first, then update
rows = []
pts = collections.defaultdict(lambda: [0, 0])  # (team, season) -> [points, gp]
for g in fin:
    s = season(g["start"]); ot = len((g.get("ls_home") or "").split(",")) > 3
    feats = {}
    for side, oside in (("home", "away"), ("away", "home")):
        t = g[side]; i = idx[t][g["id"]]; prev = sched[t][i-1] if i else None
        if prev is not None and season(prev["start"]) != s: prev = None
        b2b = prev is not None and (dt(g["start"]) - dt(prev["start"])).total_seconds() <= 30*3600
        d = us_date(g["start"]); pd_ = us_date(prev["start"]) if prev else None
        satsun = b2b and d.weekday() == 6 and pd_ is not None and pd_.weekday() == 5
        rest = (d - pd_).days if pd_ else 9
        p, gp = pts[(t, s)]
        L = seasonlen[(t, s)]
        sp = g.get(f"sp_{side}") or ""
        h = [x for x in goalie_hist[(t, sp)] if season(x[0]) == s][-5:]
        sv5 = (1 - sum(x[2] for x in h) / sum(x[1] for x in h)) if len(h) == 5 and sum(x[1] for x in h) > 0 else None
        feats[side] = dict(b2b=b2b, satsun=satsun, rest=rest, gp=gp, ptp=(p / (2*gp) if gp else None), L=L,
                           left=L - gp, sv5=sv5, sun_early=satsun and dt(g["start"]).hour < 21)
    if g.get("ml_home") and g.get("ml_away"):
        for side, oside in (("home", "away"), ("away", "home")):
            ml = float(g[f"ml_{side}"]); oml = float(g[f"ml_{oside}"])
            nv = prob(ml) / (prob(ml) + prob(oml))
            won = float(g[f"{side}_score"]) > float(g[f"{oside}_score"])
            me, op = feats[side], feats[oside]
            rows.append(dict(season=s, ml=ml, nv=nv, won=won, roi=pay(ml) if won else -1.0, band=band(ml), home=side == "home",
                             **{k: v for k, v in me.items()}, **{"o_"+k: v for k, v in op.items()}))
    # update after the game
    for side, oside in (("home", "away"), ("away", "home")):
        t = g[side]; won = float(g[f"{side}_score"]) > float(g[f"{oside}_score"])
        pts[(t, s)][0] += 2 if won else (1 if ot else 0); pts[(t, s)][1] += 1
        sp = g.get(f"sp_{side}") or ""
        gstat = gl.get((g["id"], t), {}).get(sp)
        if sp and gstat: goalie_hist[(t, sp)].append((g["start"], gstat[0], gstat[1]))

print("rows", len(rows), "with sv5", sum(1 for r in rows if r["sv5"] is not None))
R = lambda f, n: report(rows, f, n, TR, HO, CU)
print("\n#### baselines")
for b in ("dog", "fav"): R(lambda x, b=b: x["band"] == b, f"BASE {b}")
R(lambda x: x["band"] == "dog" and x["b2b"] and not x["o_b2b"], "BASE dog on b2b vs non-b2b (built weight)")
R(lambda x: x["band"] == "fav" and x["b2b"] and not x["o_b2b"], "BASE fav on b2b vs non-b2b")

print("\n#### STUDY 1: SAT -> SUN back-to-back (night 2 on Sunday) vs other b2b nights  [6 cells]")
for b in ("dog", "fav", None):
    bn = b or "all prices"
    R(lambda x, b=b: (b is None or x["band"] == b) and x["satsun"] and not x["o_b2b"], f"S1 {bn}: me Sat->Sun b2b, opp not")
    R(lambda x, b=b: (b is None or x["band"] == b) and x["b2b"] and not x["satsun"] and not x["o_b2b"], f"S1 {bn}: me other b2b, opp not")
R(lambda x: x["band"] == "fav" and x["o_satsun"] and not x["b2b"], "S1 fav vs a Sat->Sun b2b opp")
R(lambda x: x["band"] == "dog" and x["o_satsun"] and not x["b2b"], "S1 dog vs a Sat->Sun b2b opp")
R(lambda x: x["satsun"] and x["sun_early"] and not x["o_b2b"], "S1 all: me Sat->Sun, Sunday early (before 1 PM PT) start")

print("\n#### STUDY 2: LATE SEASON motivation (last 20% of the team's schedule)  [6 cells]")
late = lambda x: x["L"] >= 48 and x["gp"] >= 0.8 * x["L"] and x["ptp"] is not None
R(lambda x: late(x) and x["band"] == "dog" and x["ptp"] < .45, "S2 dog, out of the race (pts% < .450)")
R(lambda x: late(x) and x["band"] == "dog" and x["ptp"] < .45 and x["o_ptp"] is not None and .52 <= x["o_ptp"] <= .60, "S2 out-of-race dog vs a bubble team (.520-.600)")
R(lambda x: late(x) and x["band"] == "fav" and x["o_ptp"] is not None and x["o_ptp"] < .45, "S2 fav vs an out-of-race team")
R(lambda x: late(x) and x["band"] == "fav" and x["ptp"] >= .65, "S2 fav, clinched-type team (.650+)")
R(lambda x: late(x) and x["band"] == "fav" and x["ptp"] >= .65 and x["left"] <= 5, "S2 fav, .650+ team, last 5 games")
R(lambda x: late(x) and x["band"] == "dog" and x["o_ptp"] is not None and x["o_ptp"] >= .65 and x["o_left"] <= 5, "S2 dog vs a .650+ team in its last 5")

print("\n#### STUDY 3: the HOT starting goalie (last 5 starts this season save % .935+)  [6 cells]")
R(lambda x: x["band"] == "dog" and x["sv5"] is not None and x["sv5"] >= .935, "S3 dog, my starter hot")
R(lambda x: x["band"] == "fav" and x["sv5"] is not None and x["sv5"] >= .935, "S3 fav, my starter hot")
R(lambda x: x["band"] == "dog" and x["sv5"] is not None and x["sv5"] >= .935 and x["o_sv5"] is not None and x["o_sv5"] < .900, "S3 dog, my starter hot, theirs cold (<.900)")
R(lambda x: x["band"] == "fav" and x["o_sv5"] is not None and x["o_sv5"] >= .935, "S3 fav vs a hot opposing starter")
R(lambda x: x["band"] == "dog" and x["sv5"] is not None and x["sv5"] < .880, "S3 dog, my starter ice cold (<.880, mirror)")
R(lambda x: x["sv5"] is not None and x["sv5"] >= .935, "S3 all prices, my starter hot")

print("\n#### STUDY 1 control: the same spot on OTHER b2b nights (is Sat->Sun anything beyond the built b2b weight?)")
R(lambda x: x["band"] == "dog" and x["o_b2b"] and not x["o_satsun"] and not x["b2b"], "S1c dog vs an other-night b2b opp")
R(lambda x: x["band"] == "fav" and x["o_b2b"] and not x["o_satsun"] and not x["b2b"], "S1c fav vs an other-night b2b opp")
R(lambda x: x["band"] == "dog" and x["o_b2b"] and not x["b2b"], "S1c dog vs ANY b2b opp")

print("\n#### STUDY 1 robustness: dog vs a Sat->Sun b2b opp, by my rest; and the NBA second check")
R(lambda x: x["band"] == "dog" and x["o_satsun"] and not x["b2b"] and x["home"], "S1r home dog vs Sat->Sun b2b visitor")
R(lambda x: x["band"] == "dog" and x["o_satsun"] and not x["b2b"] and not x["home"], "S1r road dog vs Sat->Sun b2b home team")
R(lambda x: x["o_satsun"] and not x["b2b"], "S1r ALL prices vs a Sat->Sun b2b opp")
R(lambda x: x["o_b2b"] and not x["o_satsun"] and not x["b2b"], "S1r ALL prices vs an other-night b2b opp")
