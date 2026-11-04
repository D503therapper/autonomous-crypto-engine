"""S4 - THE RULE AS THE ENGINE WOULD POST IT, AND ITS SIZING: a college hoops dog +100..+350 whose efficiency read sits
15+ points over the no-vig close, the ratings backing the dog on this floor, no study fade on it (dog points 0+ - the
CFB play's 'never a trap'), both teams 4+ games (the ratings' worst stretch is games 0-3) - the gap dose (15-20 / 20+),
the price bands, Kelly on the CALIBRATED win rate (the read says 61%, the dogs win ~45%), and what 1u / the dose would
have made a season. Plus the controls: the same rule at 10+, without the no-fade rule, without the games rule."""
from collections import defaultdict

import lib

o = lib.Out("s4")
rows = lib.load()
D = [x for x in lib.dogs(rows) if x.get("eff") is not None and x["season"] <= 2025
     and not (x.get("sp") is not None and x["sp"] < 0)]


def rule(x, gmin=15, fade_ok=False, games=4):
    return lib.backed(x) and lib.gap(x) >= gmin and (fade_ok or (x.get("dog_pts") or 0) >= 0) and min(x["gn"], x["ogn"]) >= games


R = [x for x in D if rule(x)]
o.p("== THE RULE: backed, eff gap 15+, dog points 0+, both teams 4+ games ==")
o.c("THE RULE", R)
w = lib.win_vs_price(R)
o.p(f"  won {w[0] * 100:.1f}% vs priced {w[1] * 100:.1f}% (the read said {sum(x['eff'] for x in R) / len(R) * 100:.1f}%), avg price +{sum(x['ml'] for x in R) / len(R):.0f}")
cnt = defaultdict(int)
for x in R:
    cnt[x["season"]] += 1
o.p("  a season: " + " ".join(f"{s}:{n}" for s, n in sorted(cnt.items())))
o.p("-- controls --")
o.c("without the no-fade rule", [x for x in D if rule(x, fade_ok=True)])
o.c("without the games rule", [x for x in D if rule(x, games=1)])
o.c("the same at 10+", [x for x in D if rule(x, gmin=10)])
o.c("the same at 10..15 only", [x for x in D if rule(x, gmin=10) and lib.gap(x) < 15])
o.c("the same at 12+", [x for x in D if rule(x, gmin=12)])
o.c("the same at 20+", [x for x in D if rule(x, gmin=20)])
o.c("NOT backed, gap 15+, dog points 0+, 4+ games", [x for x in D if not lib.backed(x) and lib.gap(x) >= 15 and (x.get("dog_pts") or 0) >= 0 and min(x["gn"], x["ogn"]) >= 4])
o.c("the rule, dog points 2+", [x for x in R if (x.get("dog_pts") or 0) >= 2])
o.c("the rule, dog points exactly 0..2", [x for x in R if 0 <= (x.get("dog_pts") or 0) < 2])

o.p("\n== THE DOSE (sizing by the gap) ==")
lib.cuts(o, "gap", R, lambda x: lib.bk(lib.gap(x), [15, 20, 25]), lib.bk_labels([15, 20, 25]))
lib.cuts(o, "band", R, lambda x: lib.band(x["ml"]), ["+100..+150", "+151..+250", "+251..+350"])
lib.cuts(o, "venue", R, lambda x: x["venue"], ["home", "away", "neutral"])
lib.cuts(o, "month", R, lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"])
lib.cuts(o, "conf", R, lambda x: "conf" if x.get("same_conf") else "non-conf", ["conf", "non-conf"])
lib.cuts(o, "tier", R, lib.tier_of, ["P", "M", "L"])
lib.cuts(o, "games in", R, lambda x: lib.bk(min(x["gn"], x["ogn"]), [8, 12, 20]), lib.bk_labels([8, 12, 20]))
o.c("the OLD own read over the no-vig too", [x for x in R if x.get("own") is not None and x["own"] > x["p"]])
o.c("the OLD own read under the no-vig", [x for x in R if x.get("own") is not None and x["own"] <= x["p"]])
o.c("the raw Elo read agrees (raw gap 10+)", [x for x in R if x.get("raw") is not None and (x["raw"] - x["p"]) * 100 >= 10])
o.c("the raw Elo read does not (raw gap < 10)", [x for x in R if x.get("raw") is not None and (x["raw"] - x["p"]) * 100 < 10])
o.c("home dog", [x for x in R if x["venue"] == "home"])
o.c("home dog, conference", [x for x in R if x["venue"] == "home" and x.get("same_conf")])

o.p("\n== UNITS: flat 1u vs the dose (2u at a 20+ gap) vs quarter-Kelly on the calibrated read ==")


def kelly_units(p, ml, frac=0.25, cap=3.0, floor=0.5):
    b = lib.dec(ml) - 1
    f = (p * b - (1 - p)) / b
    return max(floor, min(cap, round(f * frac * 100 / 5, 1))) if f > 0 else 0.0


for lab, units in (("flat 1u", lambda x: 1.0), ("2u at 20+ / 1u", lambda x: 2.0 if lib.gap(x) >= 20 else 1.0),
                   ("quarter-Kelly on the read SHRUNK to the calibration (won 45% at a 61% read: read x 0.74)",
                    lambda x: kelly_units(x["eff"] * 0.74, x["ml"])),
                   ("quarter-Kelly on the raw read (what the CFB play's edge_own would say)", lambda x: kelly_units(x["eff"], x["ml"]))):
    by = defaultdict(float)
    tot = defaultdict(float)
    for x in R:
        u = units(x)
        by[x["season"]] += u * lib.profit_ml(x)
        tot[x["season"]] += u
    o.p(f"  {lab}: " + " ".join(f"{s}:{by[s]:+.1f}u/{tot[s]:.0f}u" for s in sorted(by))
        + f" | all {sum(by.values()):+.1f}u on {sum(tot.values()):.0f}u ({sum(by.values()) / sum(tot.values()) * 100:+.1f}%)")
o.save()
