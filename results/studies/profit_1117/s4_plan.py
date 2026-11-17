"""11/17 MAX PROFIT - (4) THE PLAN AS WIRED vs TODAY, each piece's share, and the size tiers before / after.
THE PLAN (sports.PROFIT_1117_FROM): the hockey runner-up dog +100..+150 at 2u; the college football thin Lock at 1u; the
⭐ at 2u when it sits on a Lock / a Dog of the Day / a play 1u+ by its own size at +150 or shorter (sports.best_2u_ok).
Usage: python results/studies/profit_1117/s4_plan.py > results/studies/profit_1117/s4_plan.out"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plib as L  # noqa: E402

M = L.M
CE = ["ru2", "cfb_thin"]
t0 = L.sizes()
_pre = L.sizes(pieces=CE)


def wired(r):
    return r["odds"] <= 150 and (r["kind"] in ("lock", "dog") or _pre[id(r)][0] >= 1.0)


PLAN = dict(pieces=CE, star=2.0, star_ok=wired)
sp = L.sizes(**PLAN)
a, b = L.summ(t0), L.summ(sp)


def report(name, o):
    print(L.row(name, o))
    print(f"      {o['net'] / L.YEARS:+.1f}u a year ({o['risk'] / L.YEARS:.0f}u risked a year) | ROI {o['roi']:+.1f}% | won {100 * o['w'] / o['n']:.1f}% of {o['n']} plays"
          f" | worst stretch {o['dd']:+.1f}u (train {o['ddtr']:+.1f}u / held {o['ddhe']:+.1f}u) | worst season {min(o['seas'].values()):+.1f}u"
          f" | by season: {M.seas_str(o)} | a unit play on {o['dayshare']:.1f}% of board days")


print("===== TODAY vs THE PLAN (train + held; the live stretch apart)")
report("TODAY (the 11/17 code)", a)
report("THE PLAN (11/17 max profit)", b)
print(f"  the plan vs today: {b['net'] - a['net']:+.1f}u ({(b['net'] - a['net']) / L.YEARS:+.1f}u a year) on {b['risk'] - a['risk']:+.1f}u more risk "
      f"({M.roi(b['net'] - a['net'], b['risk'] - a['risk']):+.1f}% a unit added); train {b['tr'] - a['tr']:+.1f}u / held {b['he'] - a['he']:+.1f}u;"
      f" the worst stretch x{b['dd'] / a['dd']:.2f}; units won per unit of worst stretch {-a['net'] / a['dd']:.1f} -> {-b['net'] / b['dd']:.1f}")

print("\n===== EACH PIECE INSIDE THE PLAN (the plan vs the plan without it)")
for label, kw in (("the hockey runner-up dog +100..+150 at 2u", dict(pieces=["cfb_thin"], star=2.0, star_ok=wired)),
                  ("the college football thin Lock at 1u", dict(pieces=["ru2"], star=2.0, star_ok=wired)),
                  ("the ⭐ at 2u (Lock / Dog / 1u+ play, +150 or shorter)", dict(pieces=CE))):
    s2 = L.sizes(**kw)
    o2 = L.summ(s2)
    print(f"   - {label:54s} " + L.added_str(L.added(s2, sp)) + f" | without it: {o2['net'] / L.YEARS:+.1f}u/yr, worst {o2['dd']:+.1f}u")


def f(x):
    w = sum(r["result"] == "won" for r in x)
    return w, len(x) - w, 100 * sum(M.flat(r) for r in x) / len(x) if x else 0.0


def tiers(title, sz):
    print(f"\n===== {title}")
    for star_in in (False, True):
        print(f"  -- {'as the board shows it (the ⭐ raise in)' if star_in else 'by the kind (the ⭐ raise left off)'}")
        t = defaultdict(list)
        for r in L.P:
            t[sz[id(r)][1 if star_in else 0]].append(r)
        for u in sorted(t):
            rs = t[u]
            g = lambda h: [r for r in rs if M.half(r["date"]) == h]     # noqa: E731
            tr, he, lv, al = f(g("train")), f(g("held")), f(g("live")), f(g("train") + g("held"))
            print(f"   {u:g}u: {al[0] + al[1]:4d} plays {al[0]}-{al[1]} {al[2]:+5.1f}% | train {tr[0]}-{tr[1]} {tr[2]:+5.1f}% | HELD OUT {he[0]}-{he[1]} {he[2]:+5.1f}%"
                  f" ({u * sum(M.flat(r) for r in g('held')):+.1f}u) | live-replay {lv[0]}-{lv[1]}")
            c = defaultdict(list)
            for r in rs:
                if M.half(r["date"]) != "live":
                    c[L.k(r) + (" ⭐" if star_in and sz[id(r)][2] and sz[id(r)][1] > sz[id(r)][0] else "")].append(r)
            for kk, x in sorted(c.items(), key=lambda kv: -len(kv[1])):
                hs = f([r for r in x if M.half(r["date"]) == "held"])
                print(f"         {kk:46s} {len(x):4d} plays {f(x)[2]:+6.1f}% | held out {hs[0]}-{hs[1]} {hs[2]:+6.1f}%")


tiers("THE SIZE TIERS TODAY", t0)
tiers("THE SIZE TIERS UNDER THE PLAN", sp)

print("\n===== THE LIVE-REPLAY WEEKS (10/13 on - after the held-out half; today's code replayed, not the live record)")
for nm, sz in (("today", t0), ("the plan", sp)):
    rs = [r for r in L.P if M.half(r["date"]) == "live"]
    print(f"   {nm:9s} {sum(sz[id(r)][1] * M.flat(r) for r in rs):+.1f}u on {sum(sz[id(r)][1] for r in rs):.1f}u")
