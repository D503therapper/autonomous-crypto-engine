"""The gated hockey dog with NO named reason (the 10/28 named-reason hole, hockey's half): its record in the funnel rows."""
import glob
import json
from collections import defaultdict

D = "/tmp/claude-0/-home-user-autonomous-crypto-engine/5dde3d3a-fafc-58c9-b906-e7206cad0b55/scratchpad/funnel1030"
rows = []
for q in sorted(glob.glob(D + "/f[A-D].jsonl")) + [D + "/fLive.jsonl"]:
    with open(q) as f:
        rows += [json.loads(l) for l in f if l.strip()]
rows = [r for r in rows if r.get("result") in ("won", "lost", "push")]
by_day = defaultdict(list)
for r in rows:
    by_day[r["date"]].append(r)


def pnl(r, u=1.0):
    return u * (r["dec"] - 1) if r["result"] == "won" else -u if r["result"] == "lost" else 0.0


def cell(name, rs):
    w = sum(r["result"] == "won" for r in rs)
    l = sum(r["result"] == "lost" for r in rs)
    p = sum(pnl(r) for r in rs)
    n = w + l
    seasons = defaultdict(float)
    for r in rs:
        y, m = int(r["date"][:4]), int(r["date"][5:7])
        seasons[y if m >= 7 else y - 1] += pnl(r)
    tr = [r for r in rs if r["date"] < "2025-07-01"]
    he = [r for r in rs if r["date"] >= "2025-07-01"]
    f = lambda xs: (sum(pnl(r) for r in xs) / max(1, sum(r["result"] in ("won", "lost") for r in xs)) * 100, sum(r["result"] in ("won", "lost") for r in xs))   # noqa: E731
    print(f"  {name:72} {w}-{l} {p / n * 100 if n else 0:+.1f}% on {n}  train {f(tr)[0]:+.1f}% ({f(tr)[1]}) held {f(he)[0]:+.1f}% ({f(he)[1]})  seasons up "
          f"{sum(v > 0 for v in seasons.values())}/{len(seasons)} " + " ".join(f"{k}:{v:+.1f}" for k, v in sorted(seasons.items())))


nhl = [r for r in rows if r["league"] == "nhl" and 100 <= r["odds"] <= 350 and not r["trap"] and not r["fighting"] and not r.get("waiting")]
gated = [r for r in nhl if r.get("dog_gate")]
print("NHL gated dogs (dog_gate True, clean):")
cell("all gated", gated)
cell("gated, named reason (n_reasons 1+)", [r for r in gated if r["n_reasons"] > 0])
cell("gated, NO named reason", [r for r in gated if r["n_reasons"] == 0])
cell("gated, NO named reason, +100..+150", [r for r in gated if r["n_reasons"] == 0 and r["odds"] <= 150])
cell("gated, NO named reason, +151..+350", [r for r in gated if r["n_reasons"] == 0 and r["odds"] > 150])
cell("gated, named, +100..+150", [r for r in gated if r["n_reasons"] > 0 and r["odds"] <= 150])
cell("gated, named, +151..+350", [r for r in gated if r["n_reasons"] > 0 and r["odds"] > 150])
cell("gated, posted as the Dog (kind dog)", [r for r in gated if r["kind"] == "dog"])
cell("gated, NOT posted as anything", [r for r in gated if r["kind"] is None])
cell("gated, NOT posted, no reason", [r for r in gated if r["kind"] is None and r["n_reasons"] == 0])
cell("gated, NOT posted, named reason (a 2nd gated dog / the Lock's game...)", [r for r in gated if r["kind"] is None and r["n_reasons"] > 0])
# the best gated no-reason dog a day on days with no Dog posted
picks = []
for d, rs in by_day.items():
    if any(r["league"] == "nhl" and r["kind"] == "dog" for r in rs):
        continue
    pool = [r for r in rs if r["league"] == "nhl" and r.get("dog_gate") and r["n_reasons"] == 0 and not r["trap"] and not r["fighting"] and not r.get("waiting")]
    if pool:
        picks.append(max(pool, key=lambda r: (r["dog_score"], r["edge"])))
cell("the best no-reason gated hockey dog a day, days with no NHL Dog", picks)
cell("   ...+100..+150", [r for r in picks if r["odds"] <= 150])
cell("   ...+151..+350", [r for r in picks if r["odds"] > 150])
# how often a hockey day had a gated dog but no Dog
nhl_days = {r["date"] for r in nhl}
n_gated = sum(1 for d in nhl_days if any(r["league"] == "nhl" and r.get("dog_gate") for r in by_day[d]))
n_dog = sum(1 for d in nhl_days if any(r["league"] == "nhl" and r["kind"] == "dog" for r in by_day[d]))
n_both = sum(1 for d in nhl_days if any(r["league"] == "nhl" and r.get("dog_gate") for r in by_day[d]) and not any(r["league"] == "nhl" and r["kind"] == "dog" for r in by_day[d]))
print(f"\nNHL days {len(nhl_days)}: days with a gated hockey dog {n_gated}, days with a hockey Dog posted {n_dog}, gated-but-no-Dog days {n_both}")
# reasons share
print("gated hockey dogs with a named reason:", sum(1 for r in gated if r["n_reasons"] > 0), "of", len(gated))
print("\nNHL floor-type dogs (clean, score 0+, own ok) by reasons:")
fl = [r for r in nhl if r.get("dog_score") is not None and r["dog_score"] >= 0 and r["dog_own_ok"]]
cell("score 0+, named reason", [r for r in fl if r["n_reasons"] > 0])
cell("score 0+, NO named reason", [r for r in fl if r["n_reasons"] == 0])
cell("score 0-6, named reason", [r for r in fl if r["n_reasons"] > 0 and r["dog_score"] < 6])
cell("score 0-6, NO named reason", [r for r in fl if r["n_reasons"] == 0 and r["dog_score"] < 6])
cell("score 3-6, named reason", [r for r in fl if r["n_reasons"] > 0 and 3 <= r["dog_score"] < 6])
cell("score 3-6, NO named reason", [r for r in fl if r["n_reasons"] == 0 and 3 <= r["dog_score"] < 6])
cell("score 0-3, named reason", [r for r in fl if r["n_reasons"] > 0 and r["dog_score"] < 3])
cell("score 0-3, NO named reason", [r for r in fl if r["n_reasons"] == 0 and r["dog_score"] < 3])
