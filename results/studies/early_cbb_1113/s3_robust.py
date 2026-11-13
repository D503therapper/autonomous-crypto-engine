"""11/13 EARLY-SEASON COLLEGE HOOPS - s3: is the early dog read real? The dose, the union of the two dog plays as the
engine would post them (the dog slot up to 2 a night + the 🔍 gap play, twins allowed), by venue, by price band, the
gate chosen BEFORE looking at the result per gate (0/1/2/3 reported side by side, never one picked), the volume a night,
and the 2026 season so far (no efficiency join yet - the dog read's own ratings points come from the replay)."""
import os, pickle, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E
from s2_cells import ML, DOGP, dog_slot, gap_play

print("\n== the dose: every dog +100..+350 (not trap / fighting), early window by the fewer games in, by dog read")
for lo, hi in ((0, 0), (1, 1), (2, 3), (1, 3)):
    rows = [r for r in DOGP(ML) if lo <= r["mn"] <= hi and not r["trap"] and not r["fighting"] and r.get("dog_read") is not None]
    for a, b in ((-99, 0), (0, 2), (2, 4), (4, 6), (6, 99)):
        E.rec(f"mn {lo}-{hi}: dog read [{a},{b})", [r for r in rows if a <= r["dog_read"] < b], pool=rows, min_n=15)
print("\n== the dose: the efficiency gap (backed dogs, dog read 4+ not required), mn 2-3 / 1-3 / 4+")
for lo, hi in ((1, 3), (2, 3), (4, 999)):
    rows = [r for r in DOGP(ML) if lo <= r["mn"] <= hi and not r["trap"] and r.get("eff_p") is not None and r["eff_p"] > 0.5]
    for a, b in ((0, 0.05), (0.05, 0.10), (0.10, 0.15), (0.15, 0.20), (0.20, 1)):
        E.rec(f"mn {lo}-{hi}: backed, gap [{a:.2f},{b:.2f})", [r for r in rows if a <= r["eff_p"] - r["p_market"] < b], pool=DOGP([r for r in ML if lo <= r["mn"] <= hi]), min_n=15)


def union(rows):
    """The dog slot (2 a night) + the gap play, sized as wired: 1u, 2u at a dog read of 6+; a twin counts twice."""
    out = []
    for kind, got in (("slot", dog_slot(rows)), ("gap", gap_play(rows))):
        for r in got:
            u = 2.0 if (r.get("dog_read") or 0) >= 6 else 1.0
            out.append({**r, "kind_e": kind, "u": u, "upnl": u * r["pnl"], "uopen": None if r.get("open") is None else u * r["open"]})
    return out


print("\n== THE UNION (the dog slot + the gap play), flat 1u and sized as wired, by gate")
for k in (0, 1, 2, 3):
    rows = [r for r in ML if k <= r["mn"] <= 3]
    U = union(rows)
    E.rec(f"gate {k}: the new early plays, flat", U, pool=DOGP(rows))
    uu = sum(r["u"] for r in U)
    tr = [r for r in U if r["season"] <= 2022]
    he = [r for r in U if r["season"] >= 2023]
    f = lambda xs, key="upnl": (100 * sum(x[key] for x in xs) / max(1e-9, sum(x["u"] for x in xs)), sum(x[key] for x in xs))
    print(f"   gate {k}: sized {len(U)} plays, {uu:.0f}u risked, ROI {f(U)[0]:+.1f}% ({f(U)[1]:+.1f}u) | train {f(tr)[0]:+.1f}% ({f(tr)[1]:+.1f}u) | held {f(he)[0]:+.1f}% ({f(he)[1]:+.1f}u)")
    nights = Counter(r["date"] for r in U)
    print(f"   gate {k}: {len(nights)} nights with a play, {len(U) / max(1, len(nights)):.2f} a night, max {max(nights.values()) if nights else 0}; by season "
          + " ".join(f"{s % 100}:{n}" for s, n in sorted(Counter(r['season'] for r in U).items())))
    for v, fn in (("home", lambda r: r["home"] and not r["neu"]), ("road", lambda r: not r["home"] and not r["neu"]), ("neutral", lambda r: r["neu"])):
        E.rec(f"gate {k}: union, {v}", [r for r in U if fn(r)], min_n=10)
    for a, b in ((100, 150), (151, 250), (251, 350)):
        E.rec(f"gate {k}: union, +{a}..+{b}", [r for r in U if a <= r["odds"] <= b], min_n=10)

print("\n== the 2026 season so far (Nov 2026, rows through the funnel's last day): every early dog the dog read has 4+")
for r in sorted([r for r in DOGP(ML) if r["season"] == 2026 and r["mn"] < 4 and (r.get("dog_read") or -9) >= 4], key=lambda r: r["date"]):
    print(f"   {r['date']} {r['team']:22s} +{r['odds']:<4d} vs {r['opp']:22s} mn {r['mn']} read {r['dog_read']:+.1f} trap {r['trap']} fight {r['fighting']} {r['result']}")
print(f"\ncells looked at: {E.CELLS[0]}")
