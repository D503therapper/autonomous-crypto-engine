"""S6 - THE DOG READ for the test's dog slot (the owner, 11/4: "more dogs ... more units on college basketball"): ONE
score that adds up everything the engine knows about a college hoops dog - the engine's study weights (dog_spots, with
the (A) long-absence / race weights in, capped at STUDY_CAP), the RATINGS (the efficiency read backing the dog on this
floor, the 15-point gap), and the KNOWLEDGE (A) facts not already in the weights (defense-first vs a bottom-third
offense, a whole team vs 2+ out across, the late-season offense-first / transfer-heavy / new-coach dog). The points are
set by hand from the earlier studies (never fit); only the THRESHOLD is chosen on train (2018-22) and read held out
(2023-25). Baselines: the weights-only score 2+ (the test's replay: +13.4% train / +2.3% held), the strict own-read
version, the ratings alone."""
from collections import defaultdict

import afacts
import lib

o = lib.Out("s6")
rows = lib.load()
AF = afacts.build()
D = [x for x in lib.dogs(rows) if x.get("eff") is not None and x["season"] <= 2025
     and not (x.get("sp") is not None and x["sp"] < 0)]
RATING_BACKED, RATING_GAP15, RATING_AGAINST = 2, 2, -2
FACTS = {"def_first_vs_bad_off": 2, "whole_vs_2out": 1, "offense_first_late": -1, "transfer_heavy_late": -1, "new_coach_late": -1}
for x in D:
    a = AF.get((x["id"], x["team"])) or {}
    x["a"] = a
    raw = (x.get("dog_pts_raw") or 0) - (2 if a.get("bad", {}).get("long_out") else 0) - (3 if a.get("bad", {}).get("race_dog") else 0)
    x["w"] = max(-6, min(6, raw))                              # the engine's weights (dog_spots as the live code has it)
    g = lib.gap(x)
    r = 0
    if lib.backed(x):
        r += RATING_BACKED + (RATING_GAP15 if g >= 15 else 0)
    elif g <= -5:
        r += RATING_AGAINST
    x["r"] = r
    k = 0
    for name, pts in FACTS.items():
        if a.get("good", {}).get(name) or a.get("bad", {}).get(name):
            k += pts
    x["k"] = k
    x["read"] = x["w"] + x["r"] + x["k"]
    x["own_over"] = x.get("own") is not None and x["own"] > x["p"]

o.p(f"dogs {len(D)}; the read = weights (capped ±6) + ratings (backed +{RATING_BACKED}, +{RATING_GAP15} more at a 15-point gap, "
    f"the ratings 5+ against -2) + knowledge facts {FACTS}")
o.p("\n== A. BASELINES (what the test's dog slot replayed) ==")
o.c("weights-only score 2+ (no own-read rule)", [x for x in D if x["w"] >= 2])
o.c("weights-only score 2+, the own read over the no-vig (the strict version)", [x for x in D if x["w"] >= 2 and x["own_over"]])
o.c("weights-only score 4+", [x for x in D if x["w"] >= 4])
o.c("the ratings alone: backed", [x for x in D if x["r"] >= 2])
o.c("the ratings alone: backed, gap 15+", [x for x in D if x["r"] >= 4])

o.p("\n== B. THE DOG READ by threshold (choose on train, read held out) ==")
edges = [-6, -3, 0, 2, 4, 6, 8]
lib.cuts(o, "read", D, lambda x: lib.bk(x["read"], edges), lib.bk_labels(edges))
for t in (2, 3, 4, 5, 6, 8):
    o.c(f"read {t}+", [x for x in D if x["read"] >= t])
o.p("-- counts a season --")
for t in (3, 4, 5, 6):
    cnt = defaultdict(int)
    for x in D:
        if x["read"] >= t:
            cnt[x["season"]] += 1
    o.p(f"  read {t}+: " + " ".join(f"{s}:{n}" for s, n in sorted(cnt.items())))

o.p("\n== C. THE READ's PIECES (does each add?) on read 4+ ==")
R4 = [x for x in D if x["read"] >= 4]
o.c("read 4+", R4)
o.c("  weights 2+ in it", [x for x in R4 if x["w"] >= 2])
o.c("  weights under 2 in it (the ratings / knowledge carry it)", [x for x in R4 if x["w"] < 2])
o.c("  backed in it", [x for x in R4 if x["r"] >= 2])
o.c("  NOT backed in it", [x for x in R4 if x["r"] < 2])
o.c("  a knowledge fact in it", [x for x in R4 if x["k"] != 0])
o.c("  4+ games both", [x for x in R4 if min(x["gn"], x["ogn"]) >= 4])
o.c("  games 1-3", [x for x in R4 if min(x["gn"], x["ogn"]) <= 3])
o.c("  own read over the no-vig", [x for x in R4 if x["own_over"]])
o.c("  own read under the no-vig", [x for x in R4 if not x["own_over"]])
o.c("weights 2+ AND backed (no threshold on the sum)", [x for x in D if x["w"] >= 2 and x["r"] >= 2])
o.c("weights 2+ AND NOT backed", [x for x in D if x["w"] >= 2 and x["r"] < 2])
o.c("weights 0..2 AND backed gap 15+", [x for x in D if 0 <= x["w"] < 2 and x["r"] >= 4])

o.p("\n== D. WHERE (read 4+, both 4+ games) ==")
R = [x for x in D if x["read"] >= 4 and min(x["gn"], x["ogn"]) >= 4]
o.c("read 4+, both 4+ games", R)
lib.cuts(o, "band", R, lambda x: lib.band(x["ml"]), ["+100..+150", "+151..+250", "+251..+350"])
lib.cuts(o, "venue", R, lambda x: x["venue"], ["home", "away", "neutral"])
lib.cuts(o, "month", R, lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"])
lib.cuts(o, "tier", R, lib.tier_of, ["P", "M", "L"])
lib.cuts(o, "conf", R, lambda x: "conf" if x.get("same_conf") else "non-conf", ["conf", "non-conf"])
o.c("the best read a night", lib.best_per_night(R, lambda x: (x["read"], lib.gap(x))))
o.c("the best read a night, read 5+", lib.best_per_night([x for x in R if x["read"] >= 5], lambda x: (x["read"], lib.gap(x))))
byn = defaultdict(list)
for x in R:
    byn[(x["season"], x["night"])].append(x)
o.c("the top 2 a night", [x for xs in byn.values() for x in sorted(xs, key=lambda x: (-x["read"], -lib.gap(x)))[:2]])
o.c("read 6+, both 4+ games", [x for x in R if x["read"] >= 6])
o.c("read 6+ without the 🔍 gap-play rows (backed gap 15+, weights 0+)", [x for x in R if x["read"] >= 6 and not (x["r"] >= 4 and x["w"] >= 0)])
o.c("read 4..6 (the 2u question: no)", [x for x in R if 4 <= x["read"] < 6])
o.c("read 4+ AND +100..+200", [x for x in R if x["ml"] <= 200])
o.c("read 4+ AND +201..+350", [x for x in R if x["ml"] > 200])
o.save()
