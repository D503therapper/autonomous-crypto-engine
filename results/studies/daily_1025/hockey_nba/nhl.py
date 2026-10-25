"""NHL, 3 studies (10/25). Train 2016-24, HOLDOUT 2025-26, current 2026-27. Flat 1u at the closing ML. No look-ahead:
records / goalie sv% from EARLIER games only (tonight's starter = the confirmed game-day starter).
S1 bad teams (win% < .350 after 10+ games) as dogs.  S2 favorite on night 2 of a ROAD back-to-back, by price.
S3 what separates winning / losing engine-passed hockey dogs (replay rows, cutoff_study r_*.jsonl, 2023-26)."""
import collections, csv, json, glob
from common import *
fin, sched = load("nhl")
TR = tuple(range(2016, 2025)); HO = (2025,); CU = (2026,)
gsa = collections.defaultdict(lambda: [0.0, 0.0])   # (goalie, season) -> sa, ga so far
gl = {}
with open(WT + "/data/sports/players/nhl.csv") as f:
    for r in csv.DictReader(f):
        if r["role"] == "G" and r["sa"]:
            gl.setdefault(r["gid"], []).append((r["player"], float(r["sa"]), float(r["ga"] or 0)))
idx = {t: {g["id"]: i for i, g in enumerate(gs)} for t, gs in sched.items()}
rec = collections.defaultdict(lambda: [0, 0])  # (team, season) -> W, GP
rows = []; NAME = {}; KEY = {}
for g in fin:
    s = season(g["start"]); feats = {}
    NAME[g["home"]] = g["home_name"]; NAME[g["away"]] = g["away_name"]
    for side in ("home", "away"):
        t = g[side]; i = idx[t][g["id"]]; prev = sched[t][i-1] if i else None
        if prev is not None and season(prev["start"]) != s: prev = None
        b2b = prev is not None and (dt(g["start"]) - dt(prev["start"])).total_seconds() <= 30*3600
        prev_away = prev is not None and prev["away"] == t
        w, gp = rec[(t, s)]
        sp = g.get(f"sp_{side}") or ""
        sa, ga = gsa[(sp, s)]
        feats[side] = dict(b2b=b2b, rb2b=b2b and prev_away and side == "away", gp=gp, wp=(w/gp if gp else None),
                           gsv=((sa-ga)/sa if sa >= 300 else None), gsa=sa)
    if g.get("ml_home") and g.get("ml_away"):
        for side, oside in (("home", "away"), ("away", "home")):
            ml = float(g[f"ml_{side}"]); oml = float(g[f"ml_{oside}"])
            nv = prob(ml) / (prob(ml) + prob(oml)); won = float(g[f"{side}_score"]) > float(g[f"{oside}_score"])
            row = dict(season=s, ml=ml, nv=nv, won=won, roi=pay(ml) if won else -1.0, band=band(ml), home=side == "home",
                       date=us_date(g["start"]).isoformat(), team=NAME[g[side]], **feats[side], **{"o_"+k: v for k, v in feats[oside].items()})
            rows.append(row); KEY[(row["date"], row["team"])] = row
    for side, oside in (("home", "away"), ("away", "home")):
        t = g[side]; rec[(t, s)][1] += 1
        if float(g[f"{side}_score"]) > float(g[f"{oside}_score"]): rec[(t, s)][0] += 1
    for (p, sa, ga) in gl.get(g["id"], []):
        gsa[(p, s)][0] += sa; gsa[(p, s)][1] += ga
R = lambda f, n: report(rows, f, n, TR, HO, CU)
dog = lambda x: 100 <= x["ml"] <= 350
print("rows", len(rows))
print("\n#### baselines"); R(dog, "BASE dog +100..+350"); R(lambda x: -150 <= x["ml"] <= -100, "BASE fav -150..-100")
print("\n#### S1 BAD TEAMS (<.350 after 10+ GP) AS DOGS  [8 cells]")
bad = lambda x, c=.350: x["gp"] >= 10 and x["wp"] is not None and x["wp"] < c
R(lambda x: dog(x) and bad(x), "S1 dog, win% < .350, 10+ GP")
R(lambda x: dog(x) and bad(x, .300), "S1 dog, win% < .300, 10+ GP (dose)")
R(lambda x: dog(x) and bad(x) and x["home"], "S1 home dog, < .350")
R(lambda x: dog(x) and bad(x) and not x["home"], "S1 road dog, < .350")
R(lambda x: 100 <= x["ml"] < 150 and bad(x), "S1 dog +100..+149, < .350")
R(lambda x: 150 <= x["ml"] <= 350 and bad(x), "S1 dog +150..+350, < .350")
R(lambda x: dog(x) and bad(x) and x["gp"] < 25, "S1 dog < .350, GP 10-24 (early)")
R(lambda x: -200 <= x["ml"] <= -100 and x["o_gp"] >= 10 and x["o_wp"] is not None and x["o_wp"] < .350, "S1 mirror: fav -200..-100 vs a <.350 team")
print("\n#### S2 FAVORITE ON NIGHT 2 OF A ROAD B2B (prev game also away), by price  [7 cells]")
f2 = lambda x: x["rb2b"] and x["ml"] < 0
R(lambda x: f2(x) and x["ml"] >= -150, "S2 road b2b fav -150..-100")
R(lambda x: f2(x) and x["ml"] >= -125, "S2 road b2b fav -125..-100")
R(lambda x: f2(x) and -150 <= x["ml"] < -125, "S2 road b2b fav -150..-126")
R(lambda x: f2(x) and -200 <= x["ml"] < -150, "S2 road b2b fav -200..-151")
R(lambda x: f2(x) and x["ml"] < -200, "S2 road b2b fav under -200")
R(lambda x: f2(x) and x["ml"] >= -150 and not x["o_b2b"], "S2 road b2b fav -150..-100 vs RESTED home")
R(lambda x: x["ml"] < 0 and x["ml"] >= -150 and x["b2b"] and not x["rb2b"] and not x["home"], "S2 control: road fav b2b, prev game HOME")
R(lambda x: x["ml"] < 0 and x["ml"] >= -150 and not x["b2b"] and not x["home"], "S2 control: road fav -150..-100 not on b2b")

R(lambda x: -150 <= x["ml"] < -125 and not x["b2b"] and not x["home"], "S2 control: road fav -150..-126 not on b2b")
R(lambda x: -150 <= x["ml"] < -125 and x["b2b"] and x["home"], "S2 control: HOME fav -150..-126 on b2b")
R(lambda x: f2(x) and -150 <= x["ml"] < -125 and x["gsv"] is not None and x["gsv"] < .900, "S2 road b2b fav -150..-126, goalie sv% < .900 (likely backup)")
print("\n#### S3 ENGINE-PASSED HOCKEY DOGS (replay rows 2023-26, own read over the price)")
S = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/cutoff_study/"
seen = {}
for fn in sorted(glob.glob(S + "r_20*.jsonl")):
    for l in open(fn):
        r = json.loads(l)
        if r["league"] != "nhl" or r["market"] != "ml" or r["variant"] not in ("A", "cand"): continue
        if r["result"] not in ("won", "lost") or not (100 <= r["odds"] <= 350) or r.get("dog_score") is None: continue
        k = (r["date"], r["team"]); o = seen.get(k)
        if o is not None:   # merge: the cand row and the posted-Dog row are the same side
            r = dict(r, kind="dog" if "dog" in (r["kind"], o["kind"]) else r["kind"], dog_gate=r["dog_gate"] or o["dog_gate"],
                     edge_own=max(r.get("edge_own") or 0, o.get("edge_own") or 0))
        seen[k] = r
E = []
miss = 0; MISSP = []
for (d, t), r in seen.items():
    from datetime import date, timedelta as TD
    x = None
    for k in (0, -1, 1):
        x = KEY.get(((date.fromisoformat(d) + TD(days=k)).isoformat(), t))
        if x is not None: break
    if x is None:
        miss += 1
        if r["kind"] == "dog" or r["dog_gate"]: MISSP.append((d, t, r["opp"]))
        continue
    E.append(dict(x, ds=r["dog_score"], gate=r["dog_gate"], own=(r.get("edge_own") or 0) > 0, kind=r["kind"]))
print("replay dogs", len(seen), "joined", len(E), "miss", miss, "passed-pool misses", len(MISSP), MISSP[:8])
TR3 = (2022, 2023, 2024); HO3 = (2025,); CU3 = (2026,)
R3 = lambda f, n: report(E, f, n, TR3, HO3, CU3)
P = lambda x: x["own"] and (x["gate"] or x["kind"] == "dog")   # the engine's own-over dogs that clear the dog check
R3(lambda x: True, "S3 all replay NHL dog candidates")
R3(P, "S3 PASSED: own over + dog check (the Dog pool)")
for nm, f in [("home", lambda x: x["home"]), ("road", lambda x: not x["home"]),
              ("+100..+149", lambda x: x["ml"] < 150), ("+150..+350", lambda x: x["ml"] >= 150),
              ("dog win% < .400 (10+ GP)", lambda x: x["gp"] >= 10 and x["wp"] < .400),
              ("dog win% .400-.500", lambda x: x["gp"] >= 10 and .400 <= x["wp"] < .500),
              ("dog win% .500+", lambda x: x["gp"] >= 10 and x["wp"] >= .500),
              ("dog GP < 10", lambda x: x["gp"] < 10),
              ("dog goalie sv% >= .905", lambda x: x["gsv"] is not None and x["gsv"] >= .905),
              ("dog goalie sv% < .895", lambda x: x["gsv"] is not None and x["gsv"] < .895),
              ("dog goalie < 300 SA (backup/new)", lambda x: x["gsv"] is None),
              ("opp goalie sv% >= .910", lambda x: x["o_gsv"] is not None and x["o_gsv"] >= .910),
              ("dog on b2b", lambda x: x["b2b"]), ("score 6+", lambda x: x["ds"] >= 6), ("score < 6", lambda x: x["ds"] < 6)]:
    R3(lambda x, f=f: P(x) and f(x), "S3 PASSED & " + nm)
print("\n#### S3 the same cuts on ALL NHL dogs +100..+350 at the close 2016-26 (the bigger sample)")
for nm, f in [("dog win% < .400", lambda x: x["gp"] >= 10 and x["wp"] < .400), ("goalie sv% < .895", lambda x: x["gsv"] is not None and x["gsv"] < .895),
              ("goalie sv% >= .905", lambda x: x["gsv"] is not None and x["gsv"] >= .905), ("goalie < 300 SA", lambda x: x["gp"] >= 10 and x["gsv"] is None)]:
    R(lambda x, f=f: dog(x) and f(x), "S3x all dogs & " + nm)
