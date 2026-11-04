"""S7 - THE SIZING LADDER (the owner, 11/4: "like how we had 3 units on college football and it smacked ... we need to be
doing this with college basketball"): does a bigger ratings-backed gap, or a bigger dog read, earn more units? Tested
HONESTLY - the ladder is judged on train (2018-22) and held out (2023-25) separately, flat 1u vs the ladders, at the
close and at ESPN's open. The gap play's rows (S4's rule) by gap band; the dog read's rows (S6, read 4+, both 4+ games)
by read band; the gap play inside the dog read."""
from collections import defaultdict

import afacts
import lib

o = lib.Out("s7")
rows = lib.load()
AF = afacts.build()
D = [x for x in lib.dogs(rows) if x.get("eff") is not None and x["season"] <= 2025
     and not (x.get("sp") is not None and x["sp"] < 0)]
FACTS = {"def_first_vs_bad_off": 2, "whole_vs_2out": 1, "offense_first_late": -1, "transfer_heavy_late": -1, "new_coach_late": -1}
for x in D:
    a = AF.get((x["id"], x["team"])) or {}
    raw = (x.get("dog_pts_raw") or 0) - (2 if a.get("bad", {}).get("long_out") else 0) - (3 if a.get("bad", {}).get("race_dog") else 0)
    x["w"] = max(-6, min(6, raw))
    g = lib.gap(x)
    x["r"] = (2 + (2 if g >= 15 else 0)) if lib.backed(x) else (-2 if g <= -5 else 0)
    x["k"] = sum(p for n, p in FACTS.items() if a.get("good", {}).get(n) or a.get("bad", {}).get(n))
    x["read"] = x["w"] + x["r"] + x["k"]
    x["ok4"] = min(x["gn"], x["ogn"]) >= 4
GAP = [x for x in D if lib.backed(x) and lib.gap(x) >= 15 and x["w"] >= 0 and x["ok4"]]
READ = [x for x in D if x["read"] >= 4 and x["ok4"]]


def replay(name, rows_, units):
    """Units won a season at units(x) each, train / held / open - and the ROI on units bet."""
    for lab, sel in (("train", lambda x: 2018 <= x["season"] <= 2022), ("held", lambda x: x["season"] >= 2023)):
        xs = [x for x in rows_ if sel(x)]
        by, tot, byo = defaultdict(float), defaultdict(float), defaultdict(float)
        for x in xs:
            u = units(x)
            by[x["season"]] += u * lib.profit_ml(x)
            tot[x["season"]] += u
            po = lib.profit_open(x)
            if po is not None:
                byo[x["season"]] += u * po
        net, bet = sum(by.values()), sum(tot.values())
        up = sum(1 for s in by if by[s] > 0)
        line = f"  {name} | {lab}: {net:+.1f}u on {bet:.0f}u ({net / bet * 100:+.1f}%), {up}/{len(by)} seasons up"
        if lab == "held":
            line += f" | the open {sum(byo.values()):+.1f}u ({sum(byo.values()) / bet * 100:+.1f}%)"
        o.p(line)


o.p("== A. THE GAP PLAY by gap band (the rule's rows: backed, 15+, no fade, 4+ games) ==")
lib.cuts(o, "gap", GAP, lambda x: lib.bk(lib.gap(x), [15, 20, 25]), lib.bk_labels([15, 20, 25]))
lib.cuts(o, "gap", GAP, lambda x: lib.bk(lib.gap(x), [15, 20]), lib.bk_labels([15, 20]))
for lab, G in (("15-20", [x for x in GAP if lib.gap(x) < 20]), ("20+", [x for x in GAP if lib.gap(x) >= 20])):
    w = lib.win_vs_price(G)
    o.p(f"  {lab}: won {w[0] * 100:.1f}% vs priced {w[1] * 100:.1f}%, avg +{sum(x['ml'] for x in G) / len(G):.0f} (n {w[2]})")
o.p("-- the ladders --")
replay("flat 1u", GAP, lambda x: 1.0)
replay("1u / 2u at 20+", GAP, lambda x: 2.0 if lib.gap(x) >= 20 else 1.0)
replay("1u / 2u at 20+ / 3u at 25+", GAP, lambda x: 3.0 if lib.gap(x) >= 25 else 2.0 if lib.gap(x) >= 20 else 1.0)
replay("1u / 3u at 20+", GAP, lambda x: 3.0 if lib.gap(x) >= 20 else 1.0)

o.p("\n== B. THE DOG READ by read band (read 4+, both 4+ games) ==")
lib.cuts(o, "read", READ, lambda x: lib.bk(x["read"], [4, 6, 8]), lib.bk_labels([4, 6, 8]))
lib.cuts(o, "read", READ, lambda x: lib.bk(x["read"], [4, 5, 6, 7]), lib.bk_labels([4, 5, 6, 7]))
for lab, G in (("4-6", [x for x in READ if x["read"] < 6]), ("6+", [x for x in READ if x["read"] >= 6])):
    w = lib.win_vs_price(G)
    o.p(f"  {lab}: won {w[0] * 100:.1f}% vs priced {w[1] * 100:.1f}%, avg +{sum(x['ml'] for x in G) / len(G):.0f} (n {w[2]})")
o.p("-- the ladders --")
replay("flat 1u", READ, lambda x: 1.0)
replay("1u / 2u at read 6+", READ, lambda x: 2.0 if x["read"] >= 6 else 1.0)
replay("1u / 2u at 6+ / 3u at 8+", READ, lambda x: 3.0 if x["read"] >= 8 else 2.0 if x["read"] >= 6 else 1.0)
replay("1u / 3u at read 6+", READ, lambda x: 3.0 if x["read"] >= 6 else 1.0)
replay("½u / 1u at read 6+ (the test's ½u slot)", READ, lambda x: 1.0 if x["read"] >= 6 else 0.5)

o.p("\n== C. THE GAP PLAY INSIDE THE DOG READ (the two together on one dog) ==")
o.c("gap play rows, read 6+", [x for x in GAP if x["read"] >= 6])
o.c("gap play rows, read 4-6", [x for x in GAP if 4 <= x["read"] < 6])
o.c("gap play rows, read under 4", [x for x in GAP if x["read"] < 4])
o.c("read 6+ rows that are NOT gap plays", [x for x in READ if x["read"] >= 6 and x not in GAP])
replay("gap play: 1u / 2u when the read is 6+ too", GAP, lambda x: 2.0 if x["read"] >= 6 else 1.0)
replay("gap play: 1u / 2u when the read is 6+ / 3u at 8+", GAP, lambda x: 3.0 if x["read"] >= 8 else 2.0 if x["read"] >= 6 else 1.0)

o.p("\n== D. THE DOSE WITHIN SEASONS (is 20+ better than 15-20 in the SAME season?) ==")
for s in sorted(set(x["season"] for x in GAP)):
    lo_ = [x for x in GAP if x["season"] == s and lib.gap(x) < 20]
    hi_ = [x for x in GAP if x["season"] == s and lib.gap(x) >= 20]
    r = lambda xs: (sum(lib.profit_ml(x) for x in xs) / len(xs) * 100) if xs else float("nan")
    o.p(f"  {s}: gap 15-20 {r(lo_):+.0f}% n{len(lo_)} | 20+ {r(hi_):+.0f}% n{len(hi_)} | 20+ better: {r(hi_) > r(lo_) if lo_ and hi_ else '-'}")
o.p("-- the read --")
for s in sorted(set(x["season"] for x in READ)):
    lo_ = [x for x in READ if x["season"] == s and x["read"] < 6]
    hi_ = [x for x in READ if x["season"] == s and x["read"] >= 6]
    r = lambda xs: (sum(lib.profit_ml(x) for x in xs) / len(xs) * 100) if xs else float("nan")
    o.p(f"  {s}: read 4-6 {r(lo_):+.0f}% n{len(lo_)} | 6+ {r(hi_):+.0f}% n{len(hi_)} | 6+ better: {r(hi_) > r(lo_) if lo_ and hi_ else '-'}")
o.save()
