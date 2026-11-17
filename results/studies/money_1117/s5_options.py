"""11/17 MOST MONEY - (5) THE OPTIONS ON THE TABLE, one frame: units won, ROI, the worst stretch, units won per unit of
worst stretch, both halves, seasons - against today's board (mlib.board, R3L). For each: the ADDED units' own return (a
size-up is only "a better bet" when the added units earn at least what the board earns), and THE PLACEBO: the same size
change dealt to a random same-size set of plays of the same tier (2,000 deals; how many win as many units).
  1 every ½u play at 1u            2 the college football thin Lock at 1u      3 the hockey runner-up dog at 1u
  4 the ⭐ at 2u                    5 ... and the size-DOWNS a confidence ladder would ask for (the hockey Dog at 1u, the
  💎 at 2u, no ⭐ raise, the floor only as the day's one play)
Usage: python results/studies/money_1117/s5_options.py > results/studies/money_1117/s5_options.out"""
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M  # noqa: E402

P, DAYS = M.board()
base = M.summ(P, DAYS)
print(M.line("TODAY'S BOARD", base, w=60))
print("     by season:", M.seas_str(base))
NL = [r for r in P if M.half(r["date"]) != "live"]


def option(name, f, pool=None, changed=None):
    """f(r) -> the new units. pool = the plays the placebo deals the change across (default: plays of the changed plays' own size)."""
    o = M.summ(P, DAYS, f)
    print("\n" + M.line(name, o, base, w=60))
    print("     by season:", M.seas_str(o))
    ch = [r for r in NL if abs(f(r) - r["u"]) > 1e-9] if changed is None else [r for r in NL if changed(r)]
    if not ch:
        return o
    add = sum(f(r) - r["u"] for r in ch)
    gain = sum((f(r) - r["u"]) * M.flat(r) for r in ch)
    tr = sum((f(r) - r["u"]) * M.flat(r) for r in ch if M.half(r["date"]) == "train")
    he = gain - tr
    atr = sum(f(r) - r["u"] for r in ch if M.half(r["date"]) == "train")
    print(f"     {len(ch)} plays change; the added units: {gain:+.1f}u on {add:+.1f}u ({M.roi(gain, add):+.1f}% a unit; train {tr:+.1f}u {M.roi(tr, atr):+.1f}% / held {he:+.1f}u {M.roi(he, add - atr):+.1f}%)"
          f"  - the board earns {base['roi']:+.1f}% a unit")
    for pname, pl in (pool or [("the plays of the same size", [r for r in NL if r["u"] in {x["u"] for x in ch}])]):
        if len(pl) <= len(ch):
            continue
        deltas = [f(r) - r["u"] for r in ch]
        fl = [M.flat(r) for r in pl]
        rnd = random.Random(1117)
        hit = sum(1 for _ in range(2000) if sum(d * x for d, x in zip(deltas, rnd.sample(fl, len(ch)))) >= gain) if gain >= 0 else \
            sum(1 for _ in range(2000) if sum(d * x for d, x in zip(deltas, rnd.sample(fl, len(ch)))) >= gain)
        print(f"     placebo - the same change dealt to a random {len(ch)} of {pname} ({len(pl)}): as good {hit} of 2,000")
    return o


half_plays = [r for r in NL if r["u"] == 0.5]
hockey_dogs = [r for r in NL if r["league"] == "nhl" and r["odds"] >= 100]
gated_hockey = [r for r in NL if r["league"] == "nhl" and r["kind"] in ("dog", "dogplay")]
print("\n===================== THE SIZE-UPS")
option("1. EVERY ½u PLAY AT 1u", lambda r: max(1.0, r["u"]))
option("1b. every ½u play at 1u BUT the floor", lambda r: r["u"] if r["kind"] == "floor" else max(1.0, r["u"]))
option("2. the college football thin Lock at 1u", lambda r: 1.0 if r["k"].startswith("Lock - college football, thin") else r["u"],
       pool=[("the ½u plays", half_plays), ("the football Locks", [r for r in NL if r["kind"] == "lock" and r["league"] in M.FB])])
option("3. THE HOCKEY RUNNER-UP DOG AT 1u", lambda r: max(1.0, r["u"]) if r["kind"] == "dogplay" else r["u"],
       pool=[("the ½u plays", half_plays), ("the ½u DOGS", [r for r in half_plays if r["odds"] >= 100]),
             ("every posted hockey dog", hockey_dogs), ("the gated hockey dogs (the Dog + the runner-up)", gated_hockey)])
option("3b. ... at 2u (the Dog's size)", lambda r: 2.0 if r["kind"] == "dogplay" else r["u"],
       pool=[("the ½u plays", half_plays), ("the gated hockey dogs (the Dog + the runner-up)", gated_hockey)])
option("3c. ... 1u at +100..+150 only", lambda r: max(1.0, r["u"]) if r["kind"] == "dogplay" and r["odds"] <= 150 else r["u"],
       pool=[("the ½u plays", half_plays), ("the gated hockey dogs (the Dog + the runner-up)", gated_hockey)])
option("4. THE ⭐ AT 2u (at least)", lambda r: max(2.0, r["u"]) if r["star"] else r["u"], pool=[("every unit play", NL)])
option("4b. the ⭐ at 2u, only on a play already 1u+", lambda r: max(2.0, r["u"]) if r["star"] and r["u0"] >= 1 else r["u"], pool=[("every unit play", NL)])
option("5. the NBA favorite play at 2u", lambda r: 2.0 if r["kind"] == "nbafav" else r["u"], pool=[("the 1u plays", [r for r in NL if r["u"] == 1.0]), ("every unit play", NL)])
option("6. the college hoops dog slot's read-4 band at 2u", lambda r: 2.0 if r["k"].startswith("college hoops dog slot, read 4") else r["u"],
       pool=[("the 1u plays", [r for r in NL if r["u"] == 1.0])])
option("7. the NBA floor at 1u", lambda r: max(1.0, r["u"]) if r["kind"] == "nbafloor" else r["u"], pool=[("the ½u plays", half_plays)])

print("\n===================== THE SIZE-DOWNS (less risk; does the ROI and the worst stretch get better?)")
option("8. the hockey Dog +100..+150 at 1u (today 2u)", lambda r: 1.0 if r["k"].startswith("Dog - hockey +100..+150") else r["u"])
option("9. the 💎 hockey max play at 2u (today 3u)", lambda r: 2.0 if "💎" in r["k"] else r["u"])
option("10. no ⭐ raise", lambda r: r["u0"])
by = defaultdict(list)
for r in P:
    by[r["date"]].append(r)
beside = {id(r) for d, ps in by.items() for r in ps if r["kind"] == "floor" and any(q["kind"] != "floor" for q in ps)}
option("11. the floor only when it is the day's only play", lambda r: 0.0 if id(r) in beside else r["u"])
option("12. NO floor at all (breaks 'a play every day')", lambda r: 0.0 if r["kind"] == "floor" else r["u"])

print("\n===================== THE RUNNER-UP DOG, CLOSER (flat 1u)")
ru = [r for r in P if r["kind"] == "dogplay"]
M.D.cell("the hockey runner-up dog", ru)
M.D.cell("   +100..+150", [r for r in ru if r["odds"] <= 150])
M.D.cell("   +151..+350", [r for r in ru if r["odds"] > 150])
M.D.cell("   home", [r for r in ru if r["home"]])
M.D.cell("   road", [r for r in ru if not r["home"]])
dg = [r for r in P if r["kind"] == "dog" and r["league"] == "nhl"]
M.D.cell("the hockey Dog of the Day (every one)", dg)
days_ru = {r["date"] for r in ru}
M.D.cell("   the Dog on a day WITH a runner-up", [r for r in dg if r["date"] in days_ru])
M.D.cell("   the Dog on a day with none", [r for r in dg if r["date"] not in days_ru])
M.D.cell("every gated hockey dog on the board (Dog + runner-up)", dg + ru)
for s in sorted({M.season(r["date"]) for r in ru}):
    rs = [r for r in ru if M.season(r["date"]) == s]
    w = sum(r["result"] == "won" for r in rs)
    print(f"     {s}: {w}-{len(rs) - w} {sum(M.flat(r) for r in rs):+.1f}u flat")
o1 = M.summ(ru, None, lambda r: 0.5)
o2 = M.summ(ru, None, lambda r: 1.0)
print(f"  the runner-up alone: ½u {o1['net']:+.1f}u worst {o1['dd']:+.1f}u  |  1u {o2['net']:+.1f}u worst {o2['dd']:+.1f}u")
