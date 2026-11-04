"""S1 - THE COLLEGE FOOTBALL PARALLEL: the 🔍 gap play's exact college hoops analogue.

College football's 🔍 play: a dog +100..+350 whose RAW ratings read (Elo + home edge, no market) sits 15+ points over the
no-vig price, and the ratings have the dog the better side (elo_edge >= 0). Here the ratings read is the efficiency
model (sports_cbb_eff - the 11/3 DEEP verdict: the raw Elo is far worse) and, for the record, the raw Elo read too.
Cuts: the gap at 5 / 10 / 15 / 20+, backed / not, by tier, month, venue, price band; train 2018-22, held 2023-25 apart,
the ESPN open on the same dogs (2023-25). Every dog +100..+350 at ESPN's close, regular season."""
import lib

o = lib.Out("s1")
rows = lib.load()
D = [x for x in lib.dogs(rows) if x.get("eff") is not None and x["season"] <= 2025]
o.p(f"dogs +100..+350 with an efficiency read: {len(D)} (train {sum(1 for x in D if x['season'] <= 2022)}, held {sum(1 for x in D if x['season'] >= 2023)})")
o.p("BASE: every dog")
o.c("every dog", D)
w = lib.win_vs_price(D)
o.p(f"  won {w[0] * 100:.1f}% vs priced {w[1] * 100:.1f}%")

o.p("\n== A. THE GAP (efficiency read minus the no-vig close), every dog ==")
edges = [-10, -5, 0, 5, 10, 15, 20]
lib.cuts(o, "eff gap", D, lambda x: lib.bk(lib.gap(x), edges), lib.bk_labels(edges))
for t in (5, 10, 15, 20):
    o.c(f"eff gap {t}+", [x for x in D if lib.gap(x) >= t])

o.p("\n== B. RATINGS-BACKED (the efficiency margin has the dog better on this floor) ==")
B = [x for x in D if lib.backed(x)]
o.c("backed, any gap", B)
w = lib.win_vs_price(B)
o.p(f"  won {w[0] * 100:.1f}% vs priced {w[1] * 100:.1f}%")
for t in (5, 10, 15, 20):
    o.c(f"backed, eff gap {t}+", [x for x in B if lib.gap(x) >= t])
o.p("-- not backed --")
for t in (5, 10, 15):
    o.c(f"NOT backed, eff gap {t}+", [x for x in D if not lib.backed(x) and lib.gap(x) >= t])

o.p("\n== C. THE RAW ELO READ (what the CFB play literally uses) - the gap raw minus the no-vig ==")
E = [x for x in D if x.get("raw") is not None]
for t in (5, 10, 15, 20):
    o.c(f"raw Elo gap {t}+", [x for x in E if (x["raw"] - x["p"]) * 100 >= t])
    o.c(f"raw Elo gap {t}+, Elo-backed (raw > 50%)", [x for x in E if (x["raw"] - x["p"]) * 100 >= t and x["raw"] > 0.5])
o.p("-- both reads agree --")
for t in (5, 10, 15):
    o.c(f"eff gap {t}+ AND raw Elo gap {t}+", [x for x in E if lib.gap(x) >= t and (x["raw"] - x["p"]) * 100 >= t])
o.c("backed by BOTH (eff_m > 0 and raw > 50%), eff gap 10+", [x for x in E if lib.backed(x) and x["raw"] > 0.5 and lib.gap(x) >= 10])

o.p("\n== D. BACKED 10+ / 15+ BY TIER / MONTH / VENUE / BAND / GAMES IN ==")
for t in (10, 15):
    G = [x for x in B if lib.gap(x) >= t]
    o.p(f"-- backed, gap {t}+ (n {len(G)}) --")
    lib.cuts(o, f"  tier", G, lib.tier_of, ["P", "M", "L"])
    lib.cuts(o, f"  month", G, lib.phase, ["Nov", "Dec", "Jan", "Feb", "Mar"])
    lib.cuts(o, f"  venue", G, lambda x: x["venue"], ["home", "away", "neutral"])
    lib.cuts(o, f"  band", G, lambda x: lib.band(x["ml"]), ["+100..+150", "+151..+250", "+251..+350"])
    lib.cuts(o, f"  conference game", G, lambda x: "conf" if x.get("same_conf") else "non-conf", ["conf", "non-conf"])
    lib.cuts(o, f"  games in", G, lambda x: lib.bk(min(x["gn"], x["ogn"]), [4, 8, 12, 20]), lib.bk_labels([4, 8, 12, 20]))

o.p("\n== E. THE BEST GAP DOG A NIGHT (backed, gap 5+ / 10+) ==")
for t in (5, 10):
    o.c(f"best backed gap dog a night, gap {t}+", lib.best_per_night([x for x in B if lib.gap(x) >= t], lib.gap))
o.c("best eff-gap dog a night, any gap 0+ (backed or not)", lib.best_per_night([x for x in D if lib.gap(x) >= 0], lib.gap))

o.p("\n== F. CALIBRATION OF THE RATINGS READ ON DOGS (is a 15-point gap a 15-point gap?) ==")
for lab, G in (("eff gap 5..10", [x for x in D if 5 <= lib.gap(x) < 10]), ("eff gap 10..15", [x for x in D if 10 <= lib.gap(x) < 15]),
               ("eff gap 15+", [x for x in D if lib.gap(x) >= 15]), ("backed 10+", [x for x in B if lib.gap(x) >= 10])):
    w = lib.win_vs_price(G)
    if w:
        e = sum(x["eff"] for x in G) / len(G)
        o.p(f"  {lab}: won {w[0] * 100:.1f}% | priced {w[1] * 100:.1f}% | the read said {e * 100:.1f}% (n {w[2]})")
o.save()
