"""S4 - THE SECOND HALF OF THE SEASON: in conference play (Jan-Mar) the market knows more, but so does the engine. Do
the engine's reads - the old own read (Elo + features blended with the market, pulled to it by early_trust), the raw Elo,
the efficiency model, and the WEIGHED reads (the 11/3 weights stacked) - beat the price more in conference play than in
November? Two tests by month and by games played: (1) log loss vs the market (does the read know anything the close
doesn't), (2) the money - bet every side the read has 2+ / 3+ points over the no-vig close. Regular season 2018-25;
train 2018-22, held out 2023 / 2024 / 2025 apart; the ESPN open (2023-25) is the second check."""
import math
from collections import defaultdict

import lib

rows = lib.regular(lib.build())
S = [x for x in rows if x.get("ml") is not None and x.get("own") is not None and 100 >= 0]
S = [x for x in S if -350 <= x["ml"] <= 350]
o = lib.Out("s4")
o.note(f"priced sides -350..+350 with an engine read: {len(S)}")
MONTHS = ["Nov", "Dec", "Jan", "Feb", "Mar"]


def weighed(x):
    if x["ml"] < 0:
        return x.get("fav_read")
    return x.get("dog_read")


READS = {"market": lambda x: x["p"], "own (old read)": lambda x: x["own"], "raw Elo": lambda x: x.get("raw"),
         "efficiency": lambda x: x.get("eff"), "weighed (11/3 weights)": weighed}


def ll(ps):
    v = [-(math.log(p) if w else math.log(1 - p)) for p, w in ps if p is not None and 0 < p < 1]
    return (sum(v) / len(v), len(v)) if v else (None, 0)


o.h("A. LOG LOSS vs THE MARKET by month (held out 2023-25; lower = better; milli = x1000 under the market)")
for lab, pick in (("held out 2023-25", lambda x: x["season"] in lib.HELD), ("train 2018-22", lambda x: x["season"] <= 2022)):
    o.note(f"-- {lab}")
    for mo in MONTHS + ["Jan-Mar conference only", "Nov-Dec non-conference only"]:
        if mo in MONTHS:
            xs = [x for x in S if pick(x) and lib.phase(x) == mo and x["side"] == "home"]
        elif mo.startswith("Jan"):
            xs = [x for x in S if pick(x) and not x["nd"] and x.get("same_conf") and x["side"] == "home"]
        else:
            xs = [x for x in S if pick(x) and x["nd"] and not x.get("same_conf") and x["side"] == "home"]
        base, n = ll([(x["p"], x["won"]) for x in xs])
        line = f"{mo:28s} n{n:<6d} market {base:.4f}"
        for nm, fn in READS.items():
            if nm == "market":
                continue
            v, k = ll([(fn(x), x["won"]) for x in xs])
            if v is not None:
                line += f" | {nm} {(base - v) * 1000:+.1f}m"
        o.note(line)
o.note("(a home side's read only - one per game; the weighed read is the favorite's weighed read / the dog's gated read)")

o.h("B. BY GAMES PLAYED (held out) - the own read is the market until 10 games (early_trust)")
for g0, g1 in ((1, 5), (6, 10), (11, 15), (16, 20), (21, 25), (26, 40)):
    xs = [x for x in S if x["season"] in lib.HELD and g0 <= x["gn"] <= g1 and x["side"] == "home"]
    base, n = ll([(x["p"], x["won"]) for x in xs])
    line = f"games {g0}-{g1:<3d} n{n:<6d} market {base:.4f}"
    for nm, fn in READS.items():
        if nm == "market":
            continue
        v, k = ll([(fn(x), x["won"]) for x in xs])
        if v is not None:
            line += f" | {nm} {(base - v) * 1000:+.1f}m"
    o.note(line)

o.h("C. THE MONEY - bet every side a read has 2+ / 3+ points over the no-vig close, by month")
for nm, fn, cut in (("own (old read)", lambda x: x["own"], 0.02), ("own (old read)", lambda x: x["own"], 0.03),
                    ("efficiency", lambda x: x.get("eff"), 0.03), ("efficiency", lambda x: x.get("eff"), 0.06),
                    ("raw Elo", lambda x: x.get("raw"), 0.05), ("raw Elo", lambda x: x.get("raw"), 0.10),
                    ("weighed (11/3 weights)", weighed, 0.02), ("weighed (11/3 weights)", weighed, 0.03)):
    picks = [x for x in S if fn(x) is not None and fn(x) - x["p"] >= cut]
    o.c(f"{nm} {cut * 100:.0f}+ over the price - ALL months", picks)
    lib.cuts(o, f"{nm} {cut * 100:.0f}+ over, by month", picks, lib.phase, MONTHS)
    o.c(f"{nm} {cut * 100:.0f}+ over, Jan-Mar CONFERENCE games", [x for x in picks if not x["nd"] and x.get("same_conf")])
    o.c(f"{nm} {cut * 100:.0f}+ over, Jan-Mar conference, FAVORITES", [x for x in picks if not x["nd"] and x.get("same_conf") and x["ml"] < 0])
    o.c(f"{nm} {cut * 100:.0f}+ over, Jan-Mar conference, DOGS", [x for x in picks if not x["nd"] and x.get("same_conf") and x["ml"] >= 100])
    o.c(f"{nm} {cut * 100:.0f}+ over, Nov-Dec NON-conference", [x for x in picks if x["nd"] and not x.get("same_conf")])

o.h("D. THE SIDE THE READS AGREE ON (own 2+ AND efficiency 3+ over the price) by month and games played")
both = [x for x in S if x.get("eff") is not None and x["own"] - x["p"] >= 0.02 and x["eff"] - x["p"] >= 0.03]
o.c("own 2+ and efficiency 3+ over - ALL", both)
lib.cuts(o, "own 2+ and efficiency 3+ over, by month", both, lib.phase, MONTHS)
lib.cuts(o, "own 2+ and efficiency 3+ over, by games played", both, lambda x: lib.bk(x["gn"], [11, 16, 21, 26]), lib.bk_labels([11, 16, 21, 26]))
lib.cuts(o, "own 2+ and efficiency 3+ over, by price band", both, lambda x: lib.band(x["ml"]), ["-251 and up", "-151..-250", "-101..-150", "+100..+150", "+151..+250", "+251..+350"])
o.c("own 2+ and efficiency 3+ over, Jan-Mar conference favorites -101..-150", [x for x in both if not x["nd"] and x.get("same_conf") and -150 <= x["ml"] <= -101])
o.c("own 2+ and efficiency 3+ over, Jan-Mar conference favorites -151..-250", [x for x in both if not x["nd"] and x.get("same_conf") and -250 <= x["ml"] <= -151])
o.c("own 2+ and efficiency 3+ over, Jan-Mar conference dogs +100..+150", [x for x in both if not x["nd"] and x.get("same_conf") and 100 <= x["ml"] <= 150])
o.c("own 2+ and efficiency 3+ over, Jan-Mar conference dogs +151..+350", [x for x in both if not x["nd"] and x.get("same_conf") and 151 <= x["ml"] <= 350])

o.h("E. WHERE THE MARKET IS LOOSEST - the close's own error by month (the no-vig favorite's win % minus its price)")
for mo in MONTHS:
    xs = [x for x in S if x["season"] >= 2018 and lib.phase(x) == mo and x["ml"] < 0]
    if xs:
        w, p_, n = lib.win_vs_price(xs)
        o.note(f"{mo}: favorites won {w * 100:.1f}% vs {p_ * 100:.1f}% priced (n{n}); dogs {(1 - w) * 100:.1f}% vs {(1 - p_) * 100:.1f}%")
o.save()
