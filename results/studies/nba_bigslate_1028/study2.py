"""Follow-ups: (a) LIFT inside big slates - each trait's ROI minus the big-slate base, per slice (a trait 'carries' the
slate effect only if it beats the base in train AND both holdout seasons); (b) a proxy dog score from the facts this
table holds (the built weights we can rebuild here) - ROI by score threshold on big vs small slates; (c) slate size
dose-response; (d) how many dogs a night the big-slate +2 would put up."""
import os
import pickle
from collections import defaultdict

HERE = os.path.dirname(__file__)
sides = pickle.load(open(os.path.join(HERE, "sides.pkl"), "rb"))
DOGS = [d for d in sides if 100 <= d["ml"] <= 350]
BIG = [d for d in DOGS if d["slate"] >= 12]
TRAIN = {2018, 2019, 2020, 2021, 2022, 2023}
SL = (("train", TRAIN), ("24-25", {2024}), ("25-26", {2025}))


def dec(o):
    return 1 + (o / 100 if o > 0 else 100 / -o)


def roi(rows):
    if not rows:
        return 0, 0, 0.0
    w = sum(1 for d in rows if d["won"])
    pnl = sum((dec(d["ml"]) - 1) if d["won"] else -1 for d in rows)
    return len(rows), w, pnl / len(rows) * 100


def soft(d):
    return d["o_next_days"] is not None and d["o_next_days"] <= 2 and d["o_next_opp_wp"] is not None and d["o_next_opp_g"] >= 10 and d["o_next_opp_wp"] < .4


print("=== (a) LIFT over the big-slate base (ROI points) - carries = beats the base in train AND both holdout seasons ===")
base = {lab: roi([d for d in BIG if d["season"] in S])[2] for lab, S in SL}
print("  base: " + ", ".join(f"{k} {v:+.1f}%" for k, v in base.items()))
traits = [
    ("home dog", lambda d: d["home"]),
    ("road dog", lambda d: not d["home"]),
    ("+100..+150", lambda d: d["ml"] < 150),
    ("+150..+250", lambda d: 150 <= d["ml"] < 250),
    ("+250..+350", lambda d: d["ml"] >= 250),
    ("favorite on a b2b", lambda d: d["o_rest"] is not None and d["o_rest"] <= 1),
    ("dog rested 2+ vs fav b2b (built +3)", lambda d: (d["rest"] or 0) >= 2 and d["o_rest"] is not None and d["o_rest"] <= 1),
    ("both rested 2+", lambda d: (d["rest"] or 0) >= 2 and (d["o_rest"] or 0) >= 2),
    ("dog off a win", lambda d: d["last_won"] is True),
    ("dog off a loss", lambda d: d["last_won"] is False),
    ("favorite won 4+ of 5", lambda d: (d["o_w5"] or 0) >= 4),
    ("Elo gap 60-120", lambda d: 60 <= (d["o_elo"] + (70 if d["o_home"] else -70)) - d["elo"] < 120),
    ("fav's next game NOT soft", lambda d: not soft(d)),
    ("fav's next game soft (built -2)", soft),
    ("small-market dog", lambda d: d["market"] == "small"),
    ("mid-evening tip (00:30-02:00 UTC)", lambda d: 0.5 <= d["tip_utc"] < 2),
    ("late tip (02:00+ UTC)", lambda d: 2 <= d["tip_utc"] < 9),
    ("midweek", lambda d: d["wday"] < 4),
    ("sloppy favorite (top-quartile turnover rate)", None),
    ("dog net rating 5+ worse", lambda d: d["net100"] is not None and d["o_net100"] is not None and d["o_net100"] - d["net100"] >= 5),
    ("slate 13+", lambda d: d["slate"] >= 13),
    ("slate 14+", lambda d: d["slate"] >= 14),
]
import statistics
bys = defaultdict(list)
for d in DOGS:
    if d.get("o_tov_rate") is not None:
        bys[d["season"]].append(d["o_tov_rate"])
q = {s: statistics.quantiles(v, n=4)[2] for s, v in bys.items()}
for name, f in traits:
    if f is None:
        f = lambda d: d.get("o_tov_rate") is not None and d["season"] in q and d["o_tov_rate"] >= q[d["season"]]
    rows = [d for d in BIG if f(d)]
    lifts, ns = {}, {}
    for lab, S in SL:
        r = [d for d in rows if d["season"] in S]
        ns[lab] = len(r)
        lifts[lab] = roi(r)[2] - base[lab] if r else None
    carries = all(v is not None and v > 0 for v in lifts.values()) and ns["train"] >= 30 and ns["24-25"] >= 10 and ns["25-26"] >= 10
    print(f"  {name:48s} " + " | ".join(f"{lab} n{ns[lab]:4d} lift {lifts[lab]:+6.1f}" if lifts[lab] is not None else f"{lab} n0" for lab, _ in SL) + ("   <== carries" if carries else ""))

print("\n=== (b) a PROXY dog score from this table (the built weights we can rebuild: rested-vs-b2b +3, fav OT last -2.. (+2),"
      " dog off a 15+ win -2, fav off a 20+ win -2, home dog games 31-60 -2, fav 2+ more rest -2, Elo near even at +200 -2,"
      " cold dog -2, slate 12+ +2, fav soft next -2); ROI by threshold, big vs small slates ===")


def proxy(d, slate_w=True):
    sc = 0
    if (d["rest"] or 0) >= 2 and d["o_rest"] is not None and d["o_rest"] <= 1:
        sc += 3
    if d["o_last_ot"]:
        sc += 2
    if d["last_ot"]:
        sc -= 2
    if (d["last_margin"] or 0) >= 15:
        sc -= 2
    if (d["o_last_margin"] or 0) >= 20:
        sc -= 2
    if d["home"] and 30 <= d["g"] < 60:
        sc -= 2
    if d["rest"] is not None and d["o_rest"] is not None and d["o_rest"] - d["rest"] >= 2:
        sc -= 2
    gap = (d["o_elo"] + (70 if d["o_home"] else -70)) - d["elo"]
    if gap <= 30 and d["ml"] >= 200:
        sc -= 2
    if d["g"] >= 8 and d["wp"] is not None and d["wp"] < .3:
        sc -= 2
    if slate_w and d["slate"] >= 12:
        sc += 2
    if soft(d):
        sc -= 2
    return max(-6, min(6, sc))


for d in DOGS:
    d["px"] = proxy(d)
    d["px0"] = proxy(d, slate_w=False)
for lab_set, rows in (("BIG slates", BIG), ("small slates", [d for d in DOGS if d["slate"] < 12])):
    print(f"  -- {lab_set} (the score without the slate +2, so the threshold reads the same on both) --")
    for th in (-6, -2, 0, 2, 4):
        line = []
        for lab, S in SL:
            r = [d for d in rows if d["season"] in S and d["px0"] >= th]
            n, w, ro = roi(r)
            line.append(f"{lab} {w}-{n-w} {ro:+.1f}%")
        print(f"    proxy score {th:+d} or more: " + " | ".join(line))
    for lo, hi in ((-6, -3), (-2, -1), (0, 1), (2, 3), (4, 6)):
        line = []
        for lab, S in SL:
            r = [d for d in rows if d["season"] in S and lo <= d["px0"] <= hi]
            n, w, ro = roi(r)
            line.append(f"{lab} {w}-{n-w} {ro:+.1f}%")
        print(f"    proxy score {lo:+d}..{hi:+d}: " + " | ".join(line))

print("\n=== (c) slate size dose-response ===")
for s_ in range(8, 16):
    line = []
    for lab, S in SL:
        r = [d for d in DOGS if d["season"] in S and d["slate"] == s_]
        n, w, ro = roi(r)
        line.append(f"{lab} {w}-{n-w} {ro:+.1f}%")
    print(f"  slate {s_:2d}: " + " | ".join(line))

print("\n=== (d) big-slate nights: how many, how many dogs +100..+350 a night, how many won ===")
nights = defaultdict(list)
for d in BIG:
    nights[d["day"]].append(d)
by = defaultdict(list)
for day, ds in nights.items():
    by[ds[0]["season"]].append((len(ds), sum(1 for d in ds if d["won"])))
for s in sorted(by):
    n = by[s]
    print(f"  {s}-{str(s+1)[2:]}: {len(n)} big nights, {sum(a for a, _ in n)/len(n):.1f} dogs a night, {sum(b for _, b in n)/len(n):.1f} won a night")
