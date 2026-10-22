import sys, collections
from datetime import datetime
sys.path.insert(0, "/home/user/autonomous-crypto-engine/.claude/worktrees/agent-ae8e16fb99d8cc853")
import sports_data as sd

ALL = sd.load_games("nhl")
games = [g for g in ALL.values()
         if g.get("status") == "final" and str(g.get("stype")) == "2" and g.get("ml_home") and g.get("ml_away")
         and g.get("home_score") not in ("", None) and g.get("start", "") >= "2018-07-01"]
games.sort(key=lambda g: g["start"])
def season(g):
    y = int(g["start"][:4]); return y if int(g["start"][5:7]) >= 7 else y - 1
def dt(g): return datetime.strptime(g["start"][:13], "%Y-%m-%dT%H")
def prob(ml):
    ml = float(ml); return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)
def payout(ml):
    ml = float(ml); return ml / 100 if ml > 0 else 100 / -ml

allg = [g for g in ALL.values() if str(g.get("stype")) == "2" and g.get("start", "") >= "2018-07-01"
        and g.get("home") and g.get("away")]
allg.sort(key=lambda g: g["start"])
sched = collections.defaultdict(list)
for g in allg:
    sched[g["home"]].append(g); sched[g["away"]].append(g)
home_tz = {}
for t, gs in sched.items():
    c = collections.Counter(g.get("tzo") for g in gs if g["home"] == t and g.get("tzo") not in ("", None))
    home_tz[t] = float(c.most_common(1)[0][0]) if c else None

def tz(g):
    try: return float(g.get("tzo"))
    except (TypeError, ValueError): return None

def situation(t, g):
    gs = sched[t]
    i = gs.index(g)
    s = season(g)
    prev = [x for x in gs[:i] if season(x) == s]
    nxt = [x for x in gs[i+1:] if season(x) == s]
    out = {}
    away = g["away"] == t and str(g.get("neutral")) != "1"
    trip = 0; days = 0; zones = 0.0
    if away:
        trip = 1; zones = abs((tz(g) or 0) - (home_tz.get(t) or 0))
        first = g
        for x in reversed(prev):
            if x["away"] == t:
                trip += 1; first = x
                zones = max(zones, abs((tz(x) or 0) - (home_tz.get(t) or 0)))
            else: break
        days = (dt(g) - dt(first)).days
    out["trip"] = trip; out["days"] = days; out["zones"] = zones
    out["b2b"] = bool(prev) and (dt(g) - dt(prev[-1])).total_seconds() <= 30 * 3600
    out["back"] = 0
    if not away and prev and prev[-1]["away"] == t:
        n = 0
        for x in reversed(prev):
            if x["away"] == t: n += 1
            else: break
        out["back"] = n
    out["last"] = away and bool(nxt) and nxt[0]["home"] == t
    hs = 0
    if not away:
        hs = 1
        for x in reversed(prev):
            if x["home"] == t: hs += 1
            else: break
    out["hs"] = hs
    return out

rows = []
for g in games:
    for side in ("home", "away"):
        t, o = g[side], g["away" if side == "home" else "home"]
        ml = float(g[f"ml_{side}"]); oml = float(g["ml_away" if side == "home" else "ml_home"])
        p = prob(ml); nv = p / (p + prob(oml))
        won = float(g[f"{side}_score"]) > float(g["away_score" if side == "home" else "home_score"])
        st = situation(t, g); ost = situation(o, g)
        rows.append(dict(season=season(g), side=side, ml=ml, nv=nv, won=won, roi=payout(ml) if won else -1.0,
                         band="dog" if 100 <= ml <= 300 else "fav" if -150 <= ml <= -100 else None, **st,
                         otrip=ost["trip"], ohs=ost["hs"], ob2b=ost["b2b"], oback=ost["back"]))

TRAIN = range(2018, 2023)
def grade(f):
    res = {}
    for part, seasons in (("train", TRAIN), ("blind", range(2023, 2027))):
        r = [x for x in rows if f(x) and x["season"] in seasons]
        if not r: res[part] = (0, 0, 0, 0, ""); continue
        n = len(r); w = sum(x["won"] for x in r); exp = sum(x["nv"] for x in r)
        roi = sum(x["roi"] for x in r) / n
        bys = []
        for s in seasons:
            rs = [x for x in r if x["season"] == s]
            if rs: bys.append(f"{s%100}:{sum(x['roi'] for x in rs)/len(rs)*100:+.0f}({len(rs)})")
        res[part] = (n, w / n * 100, exp / n * 100, roi * 100, " ".join(bys))
    return res

cells = []
def cell(name, f):
    cells.append((name, grade(f)))

for band in ("dog", "fav"):
    cell(f"BASE {band} all", lambda x, b=band: x["band"] == b)
    cell(f"BASE {band} road", lambda x, b=band: x["band"] == b and x["trip"] >= 1)
    cell(f"BASE {band} home", lambda x, b=band: x["band"] == b and x["trip"] == 0)
    for k in (1, 2, 3, 4):
        cell(f"{band} road trip game {k}", lambda x, b=band, k=k: x["band"] == b and x["trip"] == k)
    cell(f"{band} road trip game 5+", lambda x, b=band: x["band"] == b and x["trip"] >= 5)
    cell(f"{band} road trip game 4+", lambda x, b=band: x["band"] == b and x["trip"] >= 4)
    cell(f"{band} road trip game 3+", lambda x, b=band: x["band"] == b and x["trip"] >= 3)
    for k in (3, 4, 5):
        cell(f"{band} home first back after {k}+ road", lambda x, b=band, k=k: x["band"] == b and x["back"] >= k)
    cell(f"{band} home vs road team on trip game 4+", lambda x, b=band: x["band"] == b and x["trip"] == 0 and x["otrip"] >= 4)
    cell(f"{band} home vs road team on trip game 3+", lambda x, b=band: x["band"] == b and x["trip"] == 0 and x["otrip"] >= 3)
    cell(f"{band} road, last game of trip (trip 2+)", lambda x, b=band: x["band"] == b and x["last"] and x["trip"] >= 2)
    cell(f"{band} road, last game of trip (trip 4+)", lambda x, b=band: x["band"] == b and x["last"] and x["trip"] >= 4)
    cell(f"{band} road trip 4+ AND b2b", lambda x, b=band: x["band"] == b and x["trip"] >= 4 and x["b2b"])
    cell(f"{band} road trip 4+ NOT b2b", lambda x, b=band: x["band"] == b and x["trip"] >= 4 and not x["b2b"])
    cell(f"{band} road trip 4+ zones 2+", lambda x, b=band: x["band"] == b and x["trip"] >= 4 and x["zones"] >= 2)
    cell(f"{band} road trip 4+ zones <2", lambda x, b=band: x["band"] == b and x["trip"] >= 4 and x["zones"] < 2)
    cell(f"{band} road trip 4+ days 7+", lambda x, b=band: x["band"] == b and x["trip"] >= 4 and x["days"] >= 7)
    cell(f"{band} road trip 4+ vs home team homestand 4+", lambda x, b=band: x["band"] == b and x["trip"] >= 4 and x["ohs"] >= 4)
    cell(f"{band} road trip 4+ vs home first back 3+", lambda x, b=band: x["band"] == b and x["trip"] >= 4 and x["oback"] >= 3)
    cell(f"{band} road trip 3+ zones 2+", lambda x, b=band: x["band"] == b and x["trip"] >= 3 and x["zones"] >= 2)
    cell(f"{band} home first back 4+, on b2b", lambda x, b=band: x["band"] == b and x["back"] >= 4 and x["b2b"])
    cell(f"{band} home first back 3+, NOT b2b", lambda x, b=band: x["band"] == b and x["back"] >= 3 and not x["b2b"])

print(f"sides {len(rows)}  cells {len(cells)} (6 are baselines)")
print(f"{'cell':46s} {'n':>5s} {'win%':>5s} {'exp%':>5s} {'ROI%':>6s} | {'n':>5s} {'win%':>5s} {'exp%':>5s} {'ROI%':>6s}  blind seasons")
for name, r in cells:
    a, b = r["train"], r["blind"]
    print(f"{name:46s} {a[0]:5d} {a[1]:5.1f} {a[2]:5.1f} {a[3]:+6.1f} | {b[0]:5d} {b[1]:5.1f} {b[2]:5.1f} {b[3]:+6.1f}  {b[4]}")

print("\n--- controls / pooled (all prices -200..+300) ---")
import math
def z(name, f, seasons=range(2018, 2027)):
    r = [x for x in rows if f(x) and x["season"] in seasons and -200 <= x["ml"] <= 300]
    if not r: print(name, "n 0"); return
    n = len(r); w = sum(x["won"] for x in r); e = sum(x["nv"] for x in r); v = sum(x["nv"] * (1 - x["nv"]) for x in r)
    roi = sum(x["roi"] for x in r) / n * 100
    bys = " ".join(f"{s%100}:{(sum(x['won'] for x in rs)-sum(x['nv'] for x in rs))/len(rs)*100:+.1f}({len(rs)})"
                   for s in seasons for rs in [[x for x in r if x['season'] == s]] if rs)
    print(f"{name:50s} n {n:5d} win-exp {(w-e)/n*100:+5.1f} z {(w-e)/math.sqrt(v):+5.2f} ROI {roi:+5.1f}  {bys}")
for part, ss in (("train", range(2018, 2023)), ("blind", range(2023, 2027))):
    print(part)
    z("road team, trip game 4+", lambda x: x["trip"] >= 4, ss)
    z("road team, trip game 1-3", lambda x: 1 <= x["trip"] <= 3, ss)
    z("home team vs road trip game 4+", lambda x: x["trip"] == 0 and x["otrip"] >= 4, ss)
    z("home team, first back after 3+", lambda x: x["back"] >= 3, ss)
    z("home team, first back after 4+", lambda x: x["back"] >= 4, ss)
    z("fav road b2b (any trip)", lambda x: x["band"] == "fav" and x["trip"] >= 1 and x["b2b"], ss)
    z("fav road b2b trip 1-3", lambda x: x["band"] == "fav" and 1 <= x["trip"] <= 3 and x["b2b"], ss)
    z("fav road b2b trip 4+", lambda x: x["band"] == "fav" and x["trip"] >= 4 and x["b2b"], ss)
    z("any road b2b trip 4+", lambda x: x["trip"] >= 4 and x["b2b"], ss)
    z("any road b2b trip 1-3", lambda x: 1 <= x["trip"] <= 3 and x["b2b"], ss)
    z("fav road trip 4+ not b2b", lambda x: x["band"] == "fav" and x["trip"] >= 4 and not x["b2b"], ss)
    z("road trip 4+ zones 2+", lambda x: x["trip"] >= 4 and x["zones"] >= 2, ss)
    z("road trip 6+", lambda x: x["trip"] >= 6, ss)
