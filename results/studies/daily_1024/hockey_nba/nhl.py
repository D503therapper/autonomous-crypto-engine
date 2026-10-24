"""NHL, 3 NEW studies (10/24). Train 2016-24, HOLDOUT 2025-26, current 2026-27. Flat 1u at the closing ML.
S1 'dominated but lost' / 'lucky winner': last game shot gap (from goalie shots-against lines) vs the result.
S2 the NEW GOALIE: tonight's confirmed starter making his first start of the season for this team (team game 6+).
S3 the 'all close' winner: a side whose last 3 wins were ALL one-goal games (incl. OT/SO).
Every feature from earlier games only (S2 uses the confirmed game-day starter - the bet waits for it)."""
import collections, csv
from common import *
fin, sched = load("nhl")
TR = tuple(range(2016, 2025)); HO = (2025,); CU = (2026,)
gl = collections.defaultdict(dict); sa_team = collections.defaultdict(float)
with open(WT + "/data/sports/players/nhl.csv") as f:
    for r in csv.DictReader(f):
        if r["role"] == "G" and r["sa"]:
            gl[(r["gid"], r["team"])][r["player"]] = (float(r["sa"]), float(r["ga"] or 0))
            sa_team[(r["gid"], r["team"])] += float(r["sa"])
idx = {t: {g["id"]: i for i, g in enumerate(gs)} for t, gs in sched.items()}
starts = collections.Counter()  # (team, season, goalie) starts so far
gp = collections.Counter()
sh10 = collections.defaultdict(list)
wins = collections.defaultdict(list)  # (team, season) -> margins of wins
rows = []
for g in fin:
    s = season(g["start"]); feats = {}
    for side, oside in (("home", "away"), ("away", "home")):
        t = g[side]; i = idx[t][g["id"]]; prev = sched[t][i-1] if i else None
        if prev is not None and season(prev["start"]) != s: prev = None
        b2b = prev is not None and (dt(g["start"]) - dt(prev["start"])).total_seconds() <= 30*3600
        shotgap = pwon = None; sa_last = None
        h10 = [x for x in sh10[t] if x[0]==s][-10:]
        ss10 = (sum(x[1] for x in h10)/max(1,sum(x[1]+x[2] for x in h10))) if len(h10)==10 else None
        if prev is not None:
            ps = "home" if prev["home"] == t else "away"; po = "away" if ps == "home" else "home"
            mine = sa_team.get((prev["id"], prev[po])); theirs = sa_team.get((prev["id"], t))
            if mine and theirs: shotgap = mine - theirs   # my shots - their shots
            sa_last = theirs
            within2 = (dt(g['start']) - dt(prev['start'])).days <= 2
            pwon = float(prev[f"{ps}_score"]) > float(prev[f"{po}_score"])
        sp = g.get(f"sp_{side}") or ""
        newg = bool(sp) and gp[(t, s)] >= 5 and starts[(t, s, sp)] == 0
        w3 = wins[(t, s)][-3:]
        allclose = len(w3) == 3 and all(m == 1 for m in w3)
        noneclose = len(w3) == 3 and all(m >= 2 for m in w3)
        feats[side] = dict(b2b=b2b, shotgap=shotgap, pwon=pwon, newg=newg, hasg=bool(sp) and gp[(t, s)] >= 5,
                           allclose=allclose, noneclose=noneclose, sa_last=sa_last, ss10=ss10)
    if g.get("ml_home") and g.get("ml_away"):
        for side, oside in (("home", "away"), ("away", "home")):
            ml = float(g[f"ml_{side}"]); oml = float(g[f"ml_{oside}"])
            nv = prob(ml) / (prob(ml) + prob(oml)); won = float(g[f"{side}_score"]) > float(g[f"{oside}_score"])
            rows.append(dict(season=s, ml=ml, nv=nv, won=won, roi=pay(ml) if won else -1.0, band=band(ml), home=side == "home",
                             **feats[side], **{"o_"+k: v for k, v in feats[oside].items()}))
    for side, oside in (("home", "away"), ("away", "home")):
        t = g[side]; m = float(g[f"{side}_score"]) - float(g[f"{oside}_score"])
        if m > 0: wins[(t, s)].append(m)
        gp[(t, s)] += 1
        a=sa_team.get((g['id'], g[oside])); b_=sa_team.get((g['id'], t))
        if a and b_: sh10[t].append((s, a, b_))
        sp = g.get(f"sp_{side}") or ""
        if sp: starts[(t, s, sp)] += 1
R = lambda f, n: report(rows, f, n, TR, HO, CU)
print("rows", len(rows), "shotgap", sum(r["shotgap"] is not None for r in rows), "goalie known", sum(r["hasg"] for r in rows))
print("\n#### baselines")
for b in ("dog", "fav"): R(lambda x, b=b: x["band"] == b, f"BASE {b}")
print("\n#### S1 DOMINATED BUT LOST / LUCKY WINNER (last game)  [8 cells]")
for b in ("dog", "fav"):
    R(lambda x, b=b: x["band"] == b and x["shotgap"] is not None and x["shotgap"] >= 15 and x["pwon"] is False, f"S1 {b}: outshot them by 15+ and LOST last game")
    R(lambda x, b=b: x["band"] == b and x["shotgap"] is not None and x["shotgap"] >= 10 and x["pwon"] is False, f"S1 {b}: outshot them by 10+ and LOST last game")
    R(lambda x, b=b: x["band"] == b and x["shotgap"] is not None and x["shotgap"] <= -15 and x["pwon"] is True, f"S1 {b}: outshot by 15+ and WON last game (lucky)")
    R(lambda x, b=b: x["band"] == b and x["o_shotgap"] is not None and x["o_shotgap"] <= -15 and x["o_pwon"] is True, f"S1 {b}: vs a lucky winner (opp outshot 15+ and won)")
print("\n#### S2 THE NEW GOALIE (first start of the season for this team, team game 6+)  [6 cells]")
for b in ("dog", "fav", None):
    R(lambda x, b=b: (b is None or x["band"] == b) and x["newg"], f"S2 {b or 'all'}: my goalie's first start of the season")
    R(lambda x, b=b: (b is None or x["band"] == b) and x["o_newg"] and not x["newg"], f"S2 {b or 'all'}: vs a goalie's first start")
print("\n#### S3 ALL-CLOSE WINNER (last 3 wins all one-goal)  [6 cells]")
for b in ("dog", "fav"):
    R(lambda x, b=b: x["band"] == b and x["allclose"], f"S3 {b}: my last 3 wins all one-goal")
    R(lambda x, b=b: x["band"] == b and x["noneclose"], f"S3 {b}: my last 3 wins all 2+ goals (mirror)")
    R(lambda x, b=b: x["band"] == b and x["o_allclose"] and not x["allclose"], f"S3 {b}: vs an all-close winner")

print("\n#### S1 CONTROLS: beyond the built 40+ shots weight and the last-10 shot share?")
dom = lambda x: x["shotgap"] is not None and x["shotgap"] >= 15 and x["pwon"] is False
luck = lambda x: x["shotgap"] is not None and x["shotgap"] <= -15 and x["pwon"] is True
R(lambda x: x["band"] == "dog" and dom(x) and x["ss10"] is not None and x["ss10"] >= .5, "S1c dog dominated-lost, last-10 shot share >= 50%")
R(lambda x: x["band"] == "dog" and dom(x) and x["ss10"] is not None and x["ss10"] < .5, "S1c dog dominated-lost, last-10 shot share < 50%")
R(lambda x: x["band"] == "dog" and x["pwon"] is False and x["shotgap"] is not None and 0 <= x["shotgap"] < 15, "S1c dog lost, outshot them by 0-14 (control)")
R(lambda x: x["band"] == "dog" and x["pwon"] is False, "S1c dog lost last (any)")
for b in ("dog","fav"):
    R(lambda x, b=b: x["band"] == b and luck(x) and x["sa_last"] < 40, f"S1c {b} lucky winner, allowed UNDER 40 shots (outside the built weight)")
    R(lambda x, b=b: x["band"] == b and luck(x) and x["ss10"] is not None and x["ss10"] >= .5, f"S1c {b} lucky winner, last-10 shot share >= 50%")
R(lambda x: x["band"] == "fav" and x["o_shotgap"] is not None and x["o_shotgap"] <= -15 and x["o_pwon"] is True and x["o_sa_last"] < 40, "S1c fav vs a lucky winner that allowed under 40")
R(lambda x: x["band"] == "dog" and x["pwon"] is True, "S1c dog won last (any)")
R(lambda x: x["band"] == "fav" and x["pwon"] is True, "S1c fav won last (any)")
print("\n#### S1 COMBINED (one rule, both sides): back the side that dominated-but-lost OR face a lucky winner; dogs +100..+300 / favs -150..-100")
R(lambda x: x["band"] in ("dog","fav") and (dom(x) or (x["o_shotgap"] is not None and x["o_shotgap"] <= -15 and x["o_pwon"] is True)) and not luck(x), "S1 BACK combined")
R(lambda x: x["band"] in ("dog","fav") and luck(x), "S1 FADE: the lucky winner (all bands)")
