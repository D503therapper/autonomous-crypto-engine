"""STUDY 1 - THE HOCKEY DOG AS IT RUNS LIVE, re-validated on 2021-23 at the MORNING price (the 8 AM board's number) and at
the OPEN (the paid next-day line). The live read = the line + b2b / rest (data/sports/hockey.json weights); the gates =
dog +100..+350, never one the own read fights (3+ under the price), own read not under the no-vig market (DOG_OWN_RULE
'market'); the GATED Dog = dog score 6+ (NHL_DOG_GATE); the FALLBACK Dog = score over 3 (NHL_BEST_DOG_MIN) with the own read
2+ over the no-vig market (NHL_FALLBACK_OWN_GAP) and the weighed read 1%+ over the price (MIN_EDGE); one Dog a day (the
best gated, else the best fallback); sized by price (2u at +100..+150, ½u at +151..+350 - the 10/30 sizing).
The dog score is rebuilt from history (lib.dog_score - no hits / hot-goalie / coach pieces)."""
from collections import defaultdict
import json
import lib

D = lib.build()
ROWS = [r for r in D["rows"] if lib.in_seasons(r)]
out = []


def P(s):
    print(s); out.append(s)


def drift_of(x, r):
    """this side's no-vig move from the open to the morning (+ = away from it); None without an open."""
    if not r["open"] or not r["morning"]:
        return None
    mv = r["morning"]["p"] - r["open"]["p"]
    return -mv if x["side"] == "h" else mv


def cands(at):
    by_day = defaultdict(list)
    for r in ROWS:
        ss = lib.sides(r, at)
        if not ss:
            continue
        for x in ss:
            if not 100 <= x["am"] <= 350:
                continue
            x["drift"] = drift_of(x, r) if at == "morning" else None
            x["score"] = lib.dog_score(x, drift=x["drift"])
            by_day[r["date"]].append(x)
    return by_day


def units(x):
    return 2.0 if x["am"] <= 150 else 0.5


def fighting(x):
    return x["own"] < 1 / x["dec"] - 0.03


def pick(day, gate=6.0, fb_min=3.0, fb_gap=2.0):
    g = [x for x in day if not fighting(x) and x["own"] >= x["pm"] and x["score"] >= gate]
    if g:
        return max(g, key=lambda x: x["score"]), "gated"
    f = [x for x in day if not fighting(x) and x["own"] >= x["pm"] and x["score"] > fb_min and x["gap"] >= fb_gap
         and (x["pm"] + x["score"] / 100) * x["dec"] - 1 >= 0.01]
    if f:
        return max(f, key=lambda x: x["score"]), "fallback"
    return None, None


def close_profit(x):
    r = x["r"]
    won = x["won"]
    d = lib.dec(r["ch"] if x["side"] == "h" else r["ca"])
    return (d - 1) if won else -1.0


for at in ("morning", "open"):
    P(f"\n===== AT THE {at.upper()} (2020-21 / 2021-22 / 2022-23 = held out for the {at} price) =====")
    bd = cands(at)
    alld = [x for d in bd.values() for x in d]
    P(lib.line("every dog +100..+350", lib.st([(x["r"]["season"], x["profit"], 1) for x in alld])))
    for lo, hi in ((100, 150), (151, 199), (200, 350)):
        xs = [x for x in alld if lo <= x["am"] <= hi]
        P(lib.line(f"  every dog +{lo}..+{hi}", lib.st([(x["r"]["season"], x["profit"], 1) for x in xs])))
        P(lib.line(f"  own 2+ over the market +{lo}..+{hi}", lib.st([(x["r"]["season"], x["profit"], 1) for x in xs if x["gap"] >= 2])))
        P(lib.line(f"  own over the PRICE +{lo}..+{hi}", lib.st([(x["r"]["season"], x["profit"], 1) for x in xs if x["own"] > 1 / x["dec"]])))
        P(lib.line(f"  own UNDER the market 2+ (dog on a b2b) +{lo}..+{hi}", lib.st([(x["r"]["season"], x["profit"], 1) for x in xs if x["gap"] <= -2])))
    P(lib.line("rested dog vs a b2b favorite (any price)", lib.st([(x["r"]["season"], x["profit"], 1) for x in alld if x["ob2b"] and not x["b2b"]])))
    for lo, hi in ((-99, 0), (0, 3), (3, 6), (6, 99)):
        xs = [x for x in alld if lo <= x["score"] < hi and not fighting(x) and x["own"] >= x["pm"]]
        P(lib.line(f"  score {lo}..{hi} (not fighting, own >= market)", lib.st([(x["r"]["season"], x["profit"], 1) for x in xs])))
    # the live Dog, one a day
    picks = []
    for day, xs in sorted(bd.items()):
        x, kind = pick(xs)
        if x:
            picks.append((x, kind))
    P(lib.line("THE HOCKEY DOG (one a day, live gates) flat", lib.st([(x["r"]["season"], x["profit"], 1) for x, k in picks])))
    P(lib.line("THE HOCKEY DOG sized 2u / ½u", lib.st([(x["r"]["season"], x["profit"], units(x)) for x, k in picks])))
    for kind in ("gated", "fallback"):
        P(lib.line(f"  {kind}", lib.st([(x["r"]["season"], x["profit"], units(x)) for x, k in picks if k == kind])))
    for lo, hi in ((100, 150), (151, 350)):
        xs = [(x, k) for x, k in picks if lo <= x["am"] <= hi]
        P(lib.line(f"  the Dog +{lo}..+{hi}", lib.st([(x["r"]["season"], x["profit"], units(x)) for x, k in xs])))
        P(lib.line(f"    graded at the CLOSE", lib.st([(x["r"]["season"], close_profit(x), units(x)) for x, k in xs])))
    P(lib.line("  the Dog graded at the CLOSE (all)", lib.st([(x["r"]["season"], close_profit(x), units(x)) for x, k in picks])))
    P(lib.line("  the Dog with the own read over the PRICE", lib.st([(x["r"]["season"], x["profit"], units(x)) for x, k in picks if x["own"] > 1 / x["dec"]])))
    P(lib.line("  the Dog with the own read NOT over the price", lib.st([(x["r"]["season"], x["profit"], units(x)) for x, k in picks if x["own"] <= 1 / x["dec"]])))
    P(lib.line("  the Dog = rested vs a b2b favorite", lib.st([(x["r"]["season"], x["profit"], units(x)) for x, k in picks if x["ob2b"] and not x["b2b"]])))
    P(lib.line("  the Dog = NO b2b edge", lib.st([(x["r"]["season"], x["profit"], units(x)) for x, k in picks if not (x["ob2b"] and not x["b2b"])])))
    # alternatives: tighter versions
    for name, kw in (("gate 6 only (no fallback)", dict(fb_min=99)), ("fallback gap 3", dict(fb_gap=3.0)),
                     ("gate 8", dict(gate=8.0)), ("fallback score 4.5+", dict(fb_min=4.5))):
        ps = []
        for day, xs in sorted(bd.items()):
            x, kind = pick(xs, **{k: v for k, v in kw.items()})
            if x:
                ps.append(x)
        P(lib.line(f"  ALT {name}", lib.st([(x["r"]["season"], x["profit"], units(x)) for x in ps])))
    ps = []
    for day, xs in sorted(bd.items()):
        x, kind = pick([y for y in xs if y["am"] <= 150])
        if x:
            ps.append(x)
    P(lib.line("  ALT short only (+100..+150)", lib.st([(x["r"]["season"], x["profit"], units(x)) for x in ps])))
    P(lib.line("    ...graded at the close", lib.st([(x["r"]["season"], close_profit(x), units(x)) for x in ps])))
    ps = []
    for day, xs in sorted(bd.items()):
        x, kind = pick([y for y in xs if y["ob2b"] and not y["b2b"]])
        if x:
            ps.append(x)
    P(lib.line("  ALT only a rested dog vs a b2b favorite", lib.st([(x["r"]["season"], x["profit"], units(x)) for x in ps])))

json.dump(out, open(f"{lib.OUT}/s1_out.json", "w"), indent=0)
open(f"{lib.OUT}/s1_out.txt", "w").write("\n".join(out) + "\n")
