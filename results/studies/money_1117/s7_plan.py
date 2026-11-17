"""11/17 MOST MONEY - (7) THE PLAN vs TODAY, and the size tiers. THE PLAN = today's board with the ONE change that clears
the bar: the hockey runner-up dog at +100..+150 is 1u (was ½u; past +150 it stays ½u, like the Dog of the Day's own
price split). Printed: today vs the plan (units a season, ROI, win %, the worst stretch, the worst season, the days with
a unit play); every size tier with what is in it and its held-out record; the placebo on five seeds; the two older
replay boards (sizing_1114/lib.py - R1 the 10/30 rows, R2 the 11/12 rows) for the same change.
Usage: python results/studies/money_1117/s7_plan.py > results/studies/money_1117/s7_plan.out"""
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlib as M  # noqa: E402

P, DAYS = M.board()
NL = [r for r in P if M.half(r["date"]) != "live"]


def is_ru(r):
    return r["kind"] == "dogplay" and r["league"] == "nhl" and r["odds"] <= 150


def plan(r):
    return max(1.0, r["u"]) if is_ru(r) else r["u"]


def plan0(r):                       # the kind's own size under the plan (the ⭐ raise left off)
    return max(1.0, r["u0"]) if is_ru(r) else r["u0"]


def report(name, f):
    o = M.summ(P, DAYS, f)
    ns = len({M.season(d) for d in DAYS if M.half(d) != "live"})
    yrs = sum(M.half(d) != "live" for d in DAYS) / (len([d for d in DAYS if M.half(d) != "live"]) / 3.03)   # 2023-10 -> 2026-10 = 3.03 years
    print(M.line(name, o, w=30))
    print(f"      {o['net'] / 3.03:+.1f}u a year ({o['risk'] / 3.03:.0f}u risked a year) | ROI {o['roi']:+.1f}% | won {100 * o['w'] / o['n']:.1f}% of {o['n']} plays"
          f" | worst stretch {o['dd']:+.1f}u (train {o['ddtr']:+.1f}u / held {o['ddhe']:+.1f}u) | worst season {min(o['seas'].values()):+.1f}u | by season: {M.seas_str(o)} | a unit play on {o['dayshare']:.1f}% of board days")
    return o


print("===== TODAY vs THE PLAN (train + held; the live stretch apart)")
a = report("TODAY", lambda r: r["u"])
b = report("THE PLAN", plan)
print(f"  the plan vs today: {b['net'] - a['net']:+.1f}u ({(b['net'] - a['net']) / 3.03:+.1f}u a year) on {b['risk'] - a['risk']:+.1f}u more risk; train {b['tr'] - a['tr']:+.1f}u / held {b['he'] - a['he']:+.1f}u;"
      f" the worst stretch x{b['dd'] / a['dd']:.2f}; units won per unit of worst stretch {-a['net'] / a['dd']:.1f} -> {-b['net'] / b['dd']:.1f}")
ch = [r for r in NL if plan(r) != r["u"]]
print(f"  {len(ch)} plays change size ({len([r for r in NL if is_ru(r)])} short runner-up dogs; the ⭐ had already raised {len([r for r in NL if is_ru(r)]) - len(ch)})")
for pname, pool in (("the ½u plays", [r for r in NL if r["u"] == 0.5]), ("the ½u dogs", [r for r in NL if r["u"] == 0.5 and r["odds"] >= 100]),
                    ("every posted hockey dog", [r for r in NL if r["league"] == "nhl" and r["odds"] >= 100]),
                    ("the gated hockey dogs (the Dog + the runner-up)", [r for r in NL if r["league"] == "nhl" and r["kind"] in ("dog", "dogplay")]),
                    ("the gated hockey dogs at +100..+150", [r for r in NL if r["league"] == "nhl" and r["kind"] in ("dog", "dogplay") and r["odds"] <= 150])):
    mine = sum(M.flat(r) for r in ch)
    fl = [M.flat(r) for r in pool]
    hits = []
    for seed in (1117, 1, 2, 3, 4):
        rnd = random.Random(seed)
        hits.append(sum(1 for _ in range(2000) if sum(rnd.sample(fl, len(ch))) >= mine))
    print(f"  placebo - the extra ½u dealt to a random {len(ch)} of {pname} ({len(pool)}): as good {hits} of 2,000 on five seeds ({100 * sum(hits) / 10000:.1f}%)")


def tier_table(title, f, f0):
    print(f"\n===== {title}")
    for star_in, fn in ((False, f0), (True, f)):
        print(f"  -- {'as the board shows it (the ⭐ raise in)' if star_in else 'by the kind (the ⭐ raise left off)'}")
        t = defaultdict(list)
        for r in P:
            t[fn(r)].append(r)
        for u in sorted(t):
            rs = t[u]
            g = lambda h: [r for r in rs if M.half(r["date"]) == h]     # noqa: E731
            s = lambda x: (sum(r["result"] == "won" for r in x), len(x), 100 * sum(M.flat(r) for r in x) / len(x) if x else 0.0)   # noqa: E731
            tr, he, lv = s(g("train")), s(g("held")), s(g("live"))
            al = s(g("train") + g("held"))
            print(f"   {u:g}u: {al[1]:4d} plays {al[0]}-{al[1] - al[0]} {al[2]:+5.1f}% | train {tr[0]}-{tr[1] - tr[0]} {tr[2]:+5.1f}% | HELD OUT {he[0]}-{he[1] - he[0]} {he[2]:+5.1f}%"
                  f" ({u * sum(M.flat(r) for r in g('held')):+.1f}u) | live-replay {lv[0]}-{lv[1] - lv[0]}")
            if not star_in:
                c = defaultdict(list)
                for r in rs:
                    if M.half(r["date"]) != "live":
                        c[r["k"].rsplit(" (", 1)[0]].append(r)
                for k, x in sorted(c.items(), key=lambda kv: -len(kv[1])):
                    hx = [r for r in x if M.half(r["date"]) == "held"]
                    hs = s(hx)
                    print(f"         {k:44s} {len(x):4d} plays {s(x)[2]:+6.1f}% | held out {hs[0]}-{hs[1] - hs[0]} {hs[2]:+6.1f}%")


tier_table("THE SIZE TIERS TODAY", lambda r: r["u"], lambda r: r["u0"])
tier_table("THE SIZE TIERS UNDER THE PLAN", plan, plan0)

print("\n===== THE SAME CHANGE ON THE TWO OLDER REPLAY BOARDS (sizing_1114/lib.py)")
try:
    sys.path.insert(0, os.path.join(os.path.dirname(M.HERE), "sizing_1114"))
    import lib as L  # noqa: E402
    for nm, (bd, _) in L.boards().items():
        ru = [(d, r, u) for d, ps in bd.items() for r, u, k in ps if k == "dogplay" and r["league"] == "nhl"]
        sh = [x for x in ru if x[1]["odds"] <= 150]
        print(f"  BOARD {nm}")
        L.line("the hockey runner-up dog (flat 1u)", ru)
        L.line("   +100..+150", sh)
        L.line("   +151..+350", [x for x in ru if x[1]["odds"] > 150])
        gh = [(d, r, u) for d, ps in bd.items() for r, u, k in ps if k in ("dog", "dogplay") and r["league"] == "nhl"]
        hp = [(d, r, u) for d, ps in bd.items() for r, u, k in ps if u == 0.5]
        print(f"      placebo: the short runner-up vs a random set of the gated hockey dogs {L.placebo(sh, gh)} / of the ½u plays {L.placebo(sh, hp)} of 2,000")
        t0 = L.schedule("TODAY's sizes", bd, lambda d, r, u, k, ps: u)
        L.schedule("the short hockey runner-up at 1u", bd, lambda d, r, u, k, ps: max(1.0, u) if (k == "dogplay" and r["league"] == "nhl" and r["odds"] <= 150) else u)
        L.schedule("every hockey runner-up at 1u", bd, lambda d, r, u, k, ps: max(1.0, u) if (k == "dogplay" and r["league"] == "nhl") else u)
except Exception as e:  # noqa: BLE001
    print("  (the older boards' caches are not on this machine:", str(e)[:120], ")")
