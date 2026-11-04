"""S3 - WHERE THE DOG EDGE LIVES: price bands, venue, months, conference / non-conference, tiers, the dog ACROSS a faded
favorite (the 11/3 fades flipped: the Nov-Dec away small favorite, the efficiency-under slight favorite, the top scorer
out, the top-25 road team, the hot-ATS favorite, the favorite out-rebounded) - on every dog, on the backed gap dogs, and
the data-error control (a dog whose spread says it is the favorite = a swapped / stale row)."""
from collections import defaultdict

import lib

o = lib.Out("s3")
rows = lib.load()
D = [x for x in lib.dogs(rows) if x.get("eff") is not None and x["season"] <= 2025]
by = {(x["id"], x["team"]): x for x in rows}


def opp(x):
    return by.get((x["id"], x["opp"]))


def fades(x):
    """The 11/3 favorite fades on the favorite ACROSS this dog (what the engine weighs the favorite down for)."""
    f = opp(x)
    out = set()
    if not f or f.get("ml") is None or f["ml"] >= 0:
        return out
    if -150 <= f["ml"] <= -101 and f["venue"] != "home" and f.get("nd"):
        out.add("away_nd")
    if -150 <= f["ml"] <= -101 and f.get("eff") is not None and f["eff"] - f["p"] <= -0.03:
        out.add("eff_under")
    if -250 <= f["ml"] <= -101 and f.get("top_out"):
        out.add("top_out")
    if f.get("rank25") and f["venue"] == "away" and f.get("nd"):
        out.add("ranked_road")
    rg = lib.K.reb_gap(f)
    if rg is not None and rg <= -6 and -200 <= f["ml"] <= -101:
        out.add("glass")
    ag = lib.K.ats_gap(f)
    if ag is not None and ag >= 3:
        out.add("hot_ats")
    return out


def swapped(x):
    return x.get("sp") is not None and x["sp"] < 0     # (a dog laying points - the ML and spread disagree: a bad row)


o.p(f"dogs {len(D)}; rows where the spread calls the dog the favorite (bad rows): {sum(1 for x in D if swapped(x))}")
B15 = [x for x in D if lib.backed(x) and lib.gap(x) >= 15]
o.c("backed gap 15+, all", B15)
o.c("backed gap 15+, clean rows only (spread agrees it is the dog)", [x for x in B15 if not swapped(x) and x.get("sp") is not None])
o.c("backed gap 15+, bad rows", [x for x in B15 if swapped(x)])
o.c("backed gap 15+, no spread on file", [x for x in B15 if x.get("sp") is None])
CLEAN = [x for x in D if not swapped(x)]

o.p("\n== A. THE DOSE on the backed gap (clean rows) ==")
edges = [5, 10, 15, 20, 25, 30]
BK = [x for x in CLEAN if lib.backed(x)]
lib.cuts(o, "backed gap", BK, lambda x: lib.bk(lib.gap(x), edges), lib.bk_labels(edges))
for lab, G in (("backed 15+", [x for x in BK if lib.gap(x) >= 15]), ("backed 15..20", [x for x in BK if 15 <= lib.gap(x) < 20]),
               ("backed 20+", [x for x in BK if lib.gap(x) >= 20]), ("backed 10..15", [x for x in BK if 10 <= lib.gap(x) < 15])):
    w = lib.win_vs_price(G)
    e = sum(x["eff"] for x in G) / len(G)
    o.p(f"  {lab}: won {w[0] * 100:.1f}% | priced {w[1] * 100:.1f}% | the read said {e * 100:.1f}% | avg price +{sum(x['ml'] for x in G) / len(G):.0f} (n {w[2]})")

o.p("\n== B. EVERY DOG by band / venue / month / conf / tier (the base rates the gap dogs sit on) ==")
lib.cuts(o, "band", CLEAN, lambda x: lib.band(x["ml"]), ["+100..+150", "+151..+250", "+251..+350"])
lib.cuts(o, "venue", CLEAN, lambda x: x["venue"], ["home", "away", "neutral"])
lib.cuts(o, "month", CLEAN, lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"])
lib.cuts(o, "conf", CLEAN, lambda x: "conf" if x.get("same_conf") else "non-conf", ["conf", "non-conf"])
lib.cuts(o, "tier", CLEAN, lib.tier_of, ["P", "M", "L"])
o.c("home dog, conference game", [x for x in CLEAN if x["venue"] == "home" and x.get("same_conf")])
o.c("home dog +100..+150", [x for x in CLEAN if x["venue"] == "home" and x["ml"] <= 150])

o.p("\n== C. THE DOG ACROSS A FADED FAVORITE (the 11/3 fades flipped) ==")
for name in ("away_nd", "eff_under", "top_out", "ranked_road", "glass", "hot_ats"):
    G = [x for x in CLEAN if name in fades(x)]
    o.c(f"dog across '{name}'", G)
o.c("dog across ANY fade", [x for x in CLEAN if fades(x)])
o.c("dog across 2+ fades", [x for x in CLEAN if len(fades(x)) >= 2])
o.c("dog across a fade AND backed by the ratings", [x for x in CLEAN if fades(x) and lib.backed(x)])
o.c("dog across a fade AND backed gap 10+", [x for x in CLEAN if fades(x) and lib.backed(x) and lib.gap(x) >= 10])
o.c("dog across a fade AND backed gap 15+", [x for x in CLEAN if fades(x) and lib.backed(x) and lib.gap(x) >= 15])
o.c("backed gap 15+ with NO fade across", [x for x in CLEAN if not fades(x) and lib.backed(x) and lib.gap(x) >= 15])
o.c("dog across a fade, dog_pts 0+ (no dog fade on it)", [x for x in CLEAN if fades(x) and (x.get("dog_pts") or 0) >= 0])
o.c("dog across 'eff_under' with its own dog_pts 0+", [x for x in CLEAN if "eff_under" in fades(x) and (x.get("dog_pts") or 0) >= 0])

o.p("\n== D. THE ENGINE'S DOG POINTS (dog_pts) x THE RATINGS ==")
lib.cuts(o, "dog_pts", CLEAN, lambda x: lib.bk(x.get("dog_pts"), [-3, 0, 2, 4]), lib.bk_labels([-3, 0, 2, 4]))
o.c("dog_pts 2+ AND backed", [x for x in CLEAN if (x.get("dog_pts") or 0) >= 2 and lib.backed(x)])
o.c("dog_pts 2+ AND backed gap 10+", [x for x in CLEAN if (x.get("dog_pts") or 0) >= 2 and lib.backed(x) and lib.gap(x) >= 10])
o.c("backed gap 15+ AND dog_pts 0+", [x for x in CLEAN if (x.get("dog_pts") or 0) >= 0 and lib.backed(x) and lib.gap(x) >= 15])
o.c("backed gap 15+ AND dog_pts < 0 (a dog fade on it)", [x for x in CLEAN if (x.get("dog_pts") or 0) < 0 and lib.backed(x) and lib.gap(x) >= 15])
o.c("backed gap 15+ AND dog_pts -3 or worse", [x for x in CLEAN if (x.get("dog_pts") or 0) <= -3 and lib.backed(x) and lib.gap(x) >= 15])
o.c("backed gap 15+, the engine's OLD own read also over the price", [x for x in CLEAN if lib.backed(x) and lib.gap(x) >= 15 and x.get("own") is not None and x["own"] > x["p"]])
o.c("backed gap 15+, the engine's OLD own read under the price", [x for x in CLEAN if lib.backed(x) and lib.gap(x) >= 15 and x.get("own") is not None and x["own"] <= x["p"]])

o.p("\n== E. THE COMBOS THE CFB PLAY USES (not a trap: the favorite not hot, the dog not cold) on backed 15+ ==")
G = [x for x in CLEAN if lib.backed(x) and lib.gap(x) >= 15]
o.c("  favorite NOT on a 5+ win streak", [x for x in G if (x.get("ostreak") or 0) < 5])
o.c("  favorite on a 5+ win streak", [x for x in G if (x.get("ostreak") or 0) >= 5])
o.c("  dog NOT on a 3+ skid", [x for x in G if (x.get("streak") or 0) > -3])
o.c("  dog on a 3+ skid", [x for x in G if (x.get("streak") or 0) <= -3])
o.c("  dog not ice cold", [x for x in G if not x.get("ice_cold")])
o.c("  both teams 8+ games", [x for x in G if min(x["gn"], x["ogn"]) >= 8])
o.c("  both teams 8+ games, +100..+250", [x for x in G if min(x["gn"], x["ogn"]) >= 8 and x["ml"] <= 250])
o.c("  both 8+ games, no dog fade (dog_pts 0+)", [x for x in G if min(x["gn"], x["ogn"]) >= 8 and (x.get("dog_pts") or 0) >= 0])
o.c("  games 1-3 (either team)", [x for x in G if min(x["gn"], x["ogn"]) <= 3])
o.c("  games 4-7", [x for x in G if 4 <= min(x["gn"], x["ogn"]) <= 7])

o.p("\n== F. A SEASON-BY-SEASON COUNT of backed 15+ (how many a season the live engine would post) ==")
cnt = defaultdict(int)
for x in G:
    cnt[x["season"]] += 1
o.p("  " + " ".join(f"{s}:{n}" for s, n in sorted(cnt.items())))
cnt = defaultdict(int)
for x in G:
    if min(x["gn"], x["ogn"]) >= 8:
        cnt[x["season"]] += 1
o.p("  both 8+ games: " + " ".join(f"{s}:{n}" for s, n in sorted(cnt.items())))
o.save()
