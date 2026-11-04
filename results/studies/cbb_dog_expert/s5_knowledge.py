"""S5 - THE KNOWLEDGE (A) FACTS ON THE DOG READ: the gap rule (S4) with the coach / absence / roster / identity / race
facts on it (afacts.py = the (A) s7 dog view's exact construction), the (A) STACK (1+ good fact, no bad fact) next to
the ratings, the engine's dog points as the LIVE engine now has them (long_out -2, race_dog -3 added), and the dog
model (S2) refit with the (A) facts as inputs - log loss vs the market, the top decile, the gap rule inside it."""
from collections import defaultdict

import numpy as np

import afacts
import lib
from lib_model import feats, fit, ll, predict

o = lib.Out("s5")
rows = lib.load()
AF = afacts.build()
D = [x for x in lib.dogs(rows) if x.get("eff") is not None and x["season"] <= 2025
     and not (x.get("sp") is not None and x["sp"] < 0)]
for x in D:
    a = AF.get((x["id"], x["team"])) or {}
    x["a"] = a
    # the live engine's dog_spots now carries the (A) weights too: long_out -2, race_dog -3 (inside STUDY_CAP)
    raw = (x.get("dog_pts_raw") or 0) - (2 if a.get("bad", {}).get("long_out") else 0) - (3 if a.get("bad", {}).get("race_dog") else 0)
    x["dog_pts2"] = max(-6, min(6, raw))


def rule(x, pts="dog_pts2"):
    return lib.backed(x) and lib.gap(x) >= 15 and (x.get(pts) or 0) >= 0 and min(x["gn"], x["ogn"]) >= 4


R = [x for x in D if rule(x)]
o.p("== A. THE RULE with the live engine's dog points (long_out / race_dog in) ==")
o.c("THE RULE (dog points 0+, the (A) weights in)", R)
o.c("THE RULE (the S4 points, without them)", [x for x in D if rule(x, "dog_pts")])
RA = [x for x in R if x["a"].get("has_reads")]
o.p(f"\n== B. THE RULE x THE (A) FACTS (2021+ dogs with the box / roster reads: {len(RA)}) ==")
o.c("the rule, with (A) reads", RA)
o.c("  no bad (A) fact", [x for x in RA if x["a"]["nb"] == 0])
o.c("  1+ bad (A) fact", [x for x in RA if x["a"]["nb"] >= 1])
o.c("  2+ bad (A) facts", [x for x in RA if x["a"]["nb"] >= 2])
o.c("  1+ good (A) fact", [x for x in RA if x["a"]["ng"] >= 1])
o.c("  1+ good, no bad", [x for x in RA if x["a"]["ng"] >= 1 and x["a"]["nb"] == 0])
for k in ("new_coach_late", "long_out", "transfer_heavy_late", "offense_first_late", "race_dog"):
    o.c(f"  bad fact '{k}' on it", [x for x in RA if x["a"]["bad"].get(k)])
for k in ("whole_vs_2out", "def_first_vs_bad_off"):
    o.c(f"  good fact '{k}' on it", [x for x in RA if x["a"]["good"].get(k)])
o.c("  defense-first dog", [x for x in RA if x["a"].get("def_first")])
o.c("  offense-first dog", [x for x in RA if x["a"].get("off_first")])
o.c("  a new coach (any month)", [x for x in RA if x["a"].get("coach_new")])

o.p("\n== C. THE (A) STACK next to the ratings (every 2021+ dog with reads) ==")
DA = [x for x in D if x["a"].get("has_reads")]
S = [x for x in DA if x["a"]["ng"] >= 1 and x["a"]["nb"] == 0]
o.c("the stack: 1+ good, no bad", S)
o.c("  ...and the ratings back the dog", [x for x in S if lib.backed(x)])
o.c("  ...ratings against the dog", [x for x in S if not lib.backed(x)])
o.c("  ...backed, eff gap 5+", [x for x in S if lib.backed(x) and lib.gap(x) >= 5])
o.c("  ...eff gap under 0 (the ratings like the favorite)", [x for x in S if lib.gap(x) < 0])
o.c("  ...dog points 0+", [x for x in S if (x.get("dog_pts2") or 0) >= 0])
o.c("  ...dog points 2+", [x for x in S if (x.get("dog_pts2") or 0) >= 2])
o.c("2+ bad facts, ratings back the dog anyway", [x for x in DA if x["a"]["nb"] >= 2 and lib.backed(x)])
o.c("2+ bad facts, backed, gap 15+", [x for x in DA if x["a"]["nb"] >= 2 and lib.backed(x) and lib.gap(x) >= 15])
o.c("no bad fact, backed, gap 10+, dog points 0+, 4+ games", [x for x in DA if x["a"]["nb"] == 0 and lib.backed(x) and lib.gap(x) >= 10 and x["dog_pts2"] >= 0 and min(x["gn"], x["ogn"]) >= 4])
o.c("no bad fact, backed, gap 10..15, dog points 0+, 4+ games", [x for x in DA if x["a"]["nb"] == 0 and lib.backed(x) and 10 <= lib.gap(x) < 15 and x["dog_pts2"] >= 0 and min(x["gn"], x["ogn"]) >= 4])

o.p("\n== D. THE DOG MODEL with the (A) facts added (walk-forward; 2021+ rows carry the reads, earlier rows read 0) ==")


def feats2(x):
    f = feats(x)
    a = x["a"]
    f["a_nb"] = float(a.get("nb") or 0)
    f["a_ng"] = float(a.get("ng") or 0)
    for k in ("new_coach_late", "long_out", "transfer_heavy_late", "offense_first_late", "race_dog"):
        f["a_" + k] = 1.0 if a.get("bad", {}).get(k) else 0.0
    for k in ("whole_vs_2out", "def_first_vs_bad_off"):
        f["a_" + k] = 1.0 if a.get("good", {}).get(k) else 0.0
    f["a_def_first"] = 1.0 if a.get("def_first") else 0.0
    f["a_coach_new"] = 1.0 if a.get("coach_new") else 0.0
    f["a_tin"] = float(a.get("tin") or 0)
    f["a_has"] = 1.0 if a.get("has_reads") else 0.0
    return f


DM = [x for x in D if x.get("own") is not None]
NAMES = list(feats2(DM[0]).keys())
X = np.array([[feats2(x)[k] for k in NAMES] for x in DM])
y = np.array([1.0 if x["won"] else 0.0 for x in DM])
Sn = np.array([x["season"] for x in DM])
P = np.array([x["p"] for x in DM])
pm = np.zeros(len(DM))
for s in (2022, 2023, 2024, 2025):
    tr, te = Sn < s, Sn == s
    m = fit(X[tr], y[tr], NAMES)
    pm[te] = predict(m, X[te])
    o.p(f"season {s}: log loss model {ll(pm[te], y[te]):.4f} vs market {ll(P[te], y[te]):.4f} ({(ll(P[te], y[te]) - ll(pm[te], y[te])) * 1000:+.1f} milli) n {te.sum()}")
    if s == 2025:
        w = m[0]
        top = sorted(zip(NAMES, w[1:]), key=lambda t: -abs(t[1]))[:14]
        o.p("  biggest standardized weights: " + ", ".join(f"{k} {v:+.3f}" for k, v in top))
for i, x in enumerate(DM):
    x["m2_edge"] = (float(pm[i]) - x["p"]) * 100 if Sn[i] >= 2022 else None
M = [x for x in DM if x["m2_edge"] is not None]
lib.TRAIN = (2022, 2022)
o.p("(TRAIN here = 2022 (the first walk-forward season with the reads), HELD = 2023-25)")
for s in sorted(set(x["season"] for x in M)):
    xs = sorted([x for x in M if x["season"] == s], key=lambda x: x["m2_edge"])
    n = len(xs)
    o.p(f"  {s} deciles: " + " ".join(f"{sum(lib.profit_ml(x) for x in xs[d * n // 10:(d + 1) * n // 10]) / len(xs[d * n // 10:(d + 1) * n // 10]) * 100:+.0f}" for d in range(10)))
o.c("top decile of the (A)-model edge", [x for s in sorted(set(x["season"] for x in M))
                                         for x in sorted([x for x in M if x["season"] == s], key=lambda x: -x["m2_edge"])[:len([x for x in M if x["season"] == s]) // 10]])
o.c("(A)-model edge 3+", [x for x in M if x["m2_edge"] >= 3])
o.c("(A)-model edge 5+", [x for x in M if x["m2_edge"] >= 5])
o.c("(A)-model edge -5 or worse (the fade end)", [x for x in M if x["m2_edge"] <= -5])
o.c("the gap rule AND the (A)-model edge 0+", [x for x in M if rule(x) and x["m2_edge"] >= 0])
o.c("the gap rule AND the (A)-model edge < 0", [x for x in M if rule(x) and x["m2_edge"] < 0])
byn = defaultdict(list)
for x in M:
    if x["m2_edge"] >= 3:
        byn[(x["season"], x["night"])].append(x)
o.c("best (A)-model dog a night, edge 3+", [max(v, key=lambda x: x["m2_edge"]) for v in byn.values()])
o.save()
