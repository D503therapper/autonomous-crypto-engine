"""S2 - A DOG-SPECIFIC MODEL: a ridge logistic regression on DOGS ONLY (+100..+350), the market's logit plus every piece of
knowledge on the row, fit walk-forward by season (each held season predicted by a fit on the seasons before it; the
first fit is 2018-20 -> 2021, so 2021 / 2022 give a train-era read and 2023 / 2024 / 2025 the held-out one).
Scored on log loss vs the market on dogs only, then the money: the top decile of model edge (model chance minus the
no-vig), 2+ / 5+ / 8+ points over, and the best dog a night, at the close and at ESPN's open (2023-25)."""
import math
from collections import defaultdict

import numpy as np

import lib

o = lib.Out("s2")
rows = lib.load()
D = [x for x in lib.dogs(rows) if x.get("eff") is not None and x.get("own") is not None and x["season"] <= 2025]


from lib_model import feats, fit, ll, predict  # noqa: E402

NAMES = list(feats(D[0]).keys())
X = np.array([[feats(x)[k] for k in NAMES] for x in D])
y = np.array([1.0 if x["won"] else 0.0 for x in D])
S = np.array([x["season"] for x in D])
P = np.array([x["p"] for x in D])


pm = np.zeros(len(D))
for s in (2021, 2022, 2023, 2024, 2025):
    tr = S < s
    te = S == s
    m = fit(X[tr], y[tr], NAMES)
    pm[te] = predict(m, X[te])
    o.p(f"season {s}: fit on {tr.sum()} dogs | log loss model {ll(pm[te], y[te]):.4f} vs market {ll(P[te], y[te]):.4f} "
        f"({(ll(P[te], y[te]) - ll(pm[te], y[te])) * 1000:+.1f} milli for the model) | n {te.sum()}")
    if s == 2025:
        w = m[0]
        top = sorted(zip(NAMES, w[1:]), key=lambda t: -abs(t[1]))[:12]
        o.p("  the biggest standardized weights (the 2018-24 fit): " + ", ".join(f"{k} {v:+.3f}" for k, v in top))

for i, x in enumerate(D):
    x["m_p"] = float(pm[i]) if S[i] >= 2021 else None
    x["m_edge"] = (x["m_p"] - x["p"]) * 100 if x["m_p"] is not None else None
M = [x for x in D if x["m_p"] is not None]
lib.TRAIN = (2021, 2022)
o.p("\n(for this study TRAIN = 2021-22, the walk-forward seasons before the held-out ones; HELD = 2023-25)")

o.p("\n== THE MONEY: the model's edge over the no-vig close (all walk-forward seasons) ==")
edges = [-5, 0, 2, 5, 8]
lib.cuts(o, "model edge", M, lambda x: lib.bk(x["m_edge"], edges), lib.bk_labels(edges))
for t in (2, 5, 8):
    o.c(f"model edge {t}+", [x for x in M if x["m_edge"] >= t])
o.p("-- deciles of the model edge, each season on its own fit --")
for s in sorted(set(x["season"] for x in M)):
    xs = sorted([x for x in M if x["season"] == s], key=lambda x: x["m_edge"])
    n = len(xs)
    parts = []
    for d in range(10):
        q = xs[d * n // 10:(d + 1) * n // 10]
        r = sum(lib.profit_ml(x) for x in q) / len(q)
        parts.append(f"{r * 100:+.0f}")
    o.p(f"  {s}: " + " ".join(parts) + f"  (n {n}; the top decile's edge from {xs[9 * n // 10]['m_edge']:+.1f})")
o.c("top decile of the model edge, by season", [x for s in sorted(set(x["season"] for x in M))
                                                for x in sorted([x for x in M if x["season"] == s], key=lambda x: -x["m_edge"])[:len([x for x in M if x["season"] == s]) // 10]])
o.c("best model-edge dog a night", lib.best_per_night([x for x in M if x["m_edge"] > 0], lambda x: x["m_edge"]))
o.c("best model-edge dog a night, edge 3+", lib.best_per_night([x for x in M if x["m_edge"] >= 3], lambda x: x["m_edge"]))
byn = defaultdict(list)
for x in M:
    if x["m_edge"] >= 3:
        byn[(x["season"], x["night"])].append(x)
o.c("top 2 a night, edge 3+", [x for xs in byn.values() for x in sorted(xs, key=lambda x: -x["m_edge"])[:2]])

o.p("\n== THE MODEL vs THE PLAIN GAP RULE (S1's backed 15+) on the same walk-forward seasons ==")
G15 = [x for x in M if lib.backed(x) and lib.gap(x) >= 15]
o.c("backed eff gap 15+ (2021-25)", G15)
o.c("  ... and the model agrees (edge 0+)", [x for x in G15 if x["m_edge"] >= 0])
o.c("  ... the model disagrees (edge < 0)", [x for x in G15 if x["m_edge"] < 0])
o.c("  ... model edge 3+", [x for x in G15 if x["m_edge"] >= 3])
o.c("model edge 3+ WITHOUT the gap-15 rule", [x for x in M if x["m_edge"] >= 3 and not (lib.backed(x) and lib.gap(x) >= 15)])

o.p("\n== THE FADE END (what the model is sure about) ==")
o.c("model edge -5 or worse", [x for x in M if x["m_edge"] <= -5])
o.c("model edge -8 or worse", [x for x in M if x["m_edge"] <= -8])
o.save()
