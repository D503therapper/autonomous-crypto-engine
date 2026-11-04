"""A first look at the 10/30 funnel rows: NHL / NBA counts by kind, the hockey fallback cells."""
import glob
import json
from collections import Counter, defaultdict

D = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/funnel1030"
rows = []
for q in sorted(glob.glob(D + "/f[A-D].jsonl")) + [D + "/fLive.jsonl"]:
    with open(q) as f:
        rows += [json.loads(l) for l in f if l.strip()]
print("rows", len(rows), "graded", sum(1 for r in rows if r.get("result") in ("won", "lost", "push")))
print("dates", min(r["date"] for r in rows), max(r["date"] for r in rows), "days", len({r["date"] for r in rows}))
print("kinds", Counter(r["kind"] for r in rows))
print("leagues", Counter(r["league"] for r in rows))
print("keys", sorted(rows[0].keys()))
# NHL days
nhl_days = {r["date"] for r in rows if r["league"] == "nhl"}
nba_days = {r["date"] for r in rows if r["league"] == "nba"}
print("nhl days", len(nhl_days), "nba days", len(nba_days))
# per NHL day: how many had a unit play of any kind, an nhl unit play
by_day = defaultdict(list)
for r in rows:
    by_day[r["date"]].append(r)
UNIT = ("lock", "dog", "solo", "play", "dogplay", "nbafav")
n_any = n_nhl = 0
for d in nhl_days:
    us = [r for r in by_day[d] if r["kind"] in UNIT and (r.get("units") or 0) > 0]
    n_any += bool(us)
    n_nhl += any(r["league"] == "nhl" for r in us)
print(f"NHL days with any unit play {n_any}/{len(nhl_days)}, with an NHL unit play {n_nhl}/{len(nhl_days)}")
n_any = n_nba = 0
for d in nba_days:
    us = [r for r in by_day[d] if r["kind"] in UNIT and (r.get("units") or 0) > 0]
    n_any += bool(us)
    n_nba += any(r["league"] == "nba" for r in us)
print(f"NBA days with any unit play {n_any}/{len(nba_days)}, with an NBA unit play {n_nba}/{len(nba_days)}")


def pnl(r, u=1.0):
    return u * (r["dec"] - 1) if r["result"] == "won" else -u if r["result"] == "lost" else 0.0


def cell(name, rs):
    rs = [r for r in rs if r.get("result") in ("won", "lost", "push")]
    w = sum(r["result"] == "won" for r in rs)
    l = sum(r["result"] == "lost" for r in rs)
    p = sum(pnl(r) for r in rs)
    n = w + l
    seasons = defaultdict(float)
    for r in rs:
        y, m = int(r["date"][:4]), int(r["date"][5:7])
        s = y if m >= 7 else y - 1
        seasons[s] += pnl(r)
    up = sum(v > 0 for v in seasons.values())
    print(f"  {name:70} {w}-{l} {p / n * 100 if n else 0:+.1f}% on {n}  seasons up {up}/{len(seasons)} "
          + " ".join(f"{k}:{v:+.1f}" for k, v in sorted(seasons.items())))


nhl_dogs = [r for r in rows if r["league"] == "nhl" and 100 <= r["odds"] <= 350 and not r["trap"] and not r["fighting"]
            and not r.get("waiting") and r.get("dog_score") is not None]
print("\nNHL dogs +100..+350, clean (not trap / fighting / waiting):")
cell("all", nhl_dogs)
cell("dog_own_ok", [r for r in nhl_dogs if r["dog_own_ok"]])
for lo, hi in ((-99, 0), (0, 3), (3, 6), (6, 99)):
    cell(f"score {lo}..{hi}, own_ok", [r for r in nhl_dogs if r["dog_own_ok"] and lo <= r["dog_score"] < hi])
for g in (0, 1, 2, 3):
    cell(f"score 3-6, own_gap >= {g}", [r for r in nhl_dogs if r["dog_own_ok"] and 3 < r["dog_score"] < 6 and (r.get("own_gap") or -99) >= g])
    cell(f"score 0-3, own_gap >= {g}", [r for r in nhl_dogs if r["dog_own_ok"] and 0 < r["dog_score"] <= 3 and (r.get("own_gap") or -99) >= g])
cell("gated (dog_gate)", [r for r in nhl_dogs if r.get("dog_gate")])
cell("kind dog", [r for r in rows if r["league"] == "nhl" and r["kind"] == "dog"])
# the best hockey dog a day by score at various gates
print("\nBEST hockey dog a day (one), by gate:")
for gate_sc, gate_gap in ((3, 2), (3, 1), (3, 0), (2, 2), (2, 1), (1, 2), (0, 2), (0, 0), (4, 2), (5, 2), (6, 0)):
    picks = []
    for d in nhl_days:
        pool = [r for r in by_day[d] if r["league"] == "nhl" and 100 <= r["odds"] <= 350 and not r["trap"] and not r["fighting"]
                and not r.get("waiting") and r.get("dog_score") is not None and r["dog_own_ok"]
                and r["dog_score"] > gate_sc and (r.get("own_gap") if r.get("own_gap") is not None else 99) >= gate_gap
                and (r["p_market"] + r["dog_score"] / 100) * r["dec"] - 1 >= 0.01]
        if pool:
            picks.append(max(pool, key=lambda r: (r["dog_score"], r["edge"])))
    cell(f"score > {gate_sc}, own_gap >= {gate_gap}", picks)
    cell(f"   ...+100..+150 only", [r for r in picks if r["odds"] <= 150])
    cell(f"   ...+151..+350 only", [r for r in picks if r["odds"] > 150])
