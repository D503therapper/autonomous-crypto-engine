"""S10 (ours). THE TOTALS KEY NUMBERS (NFL - nflverse's closing totals 1999-2026): where finals land (37 / 41 / 43 /
44 / 47 / 51), how often a total sitting ON a number pushes, what a half point is worth there, and whether the under
below / the over above a key number is a bet at -110. (Buying the half point on a SIDE is S1-B.)
   python s10_totals_keys.py"""
from collections import Counter, defaultdict
import lib2 as L

o = L.Out("s10")
N = L.N
G = [g for g in N.games() if g["total"] is not None]
P = L.dec(-110) - 1
o(f"{len(G)} NFL games with a closing total, 1999-2026")
for en, a, b in (("1999-2014", 1999, 2014), ("2015-2026", 2015, 2026)):
    c = Counter(int(g["pts"]) for g in G if a <= g["season"] <= b)
    n = sum(c.values())
    o(f"   {en}: the most common final totals: " + ", ".join(f"{k} {v / n * 100:.1f}%" for k, v in c.most_common(10)))
o("\n== a total sitting ON the number: how often it lands there (the push), games closing within 1.5 of it ==")
for k in (37, 40, 41, 43, 44, 45, 47, 48, 51):
    on = [g for g in G if g["total"] == k]
    near = [g for g in G if abs(g["total"] - k) <= 1.5]
    new = [g for g in near if g["season"] >= 2015]
    o(f"   {k}: ON it pushes {sum(1 for g in on if g['pts'] == k) / max(1, len(on)) * 100:4.1f}% of {len(on):3d} | lands on it when the total is within 1.5: {sum(1 for g in near if g['pts'] == k) / max(1, len(near)) * 100:4.1f}% of {len(near)} (2015-26: {sum(1 for g in new if g['pts'] == k) / max(1, len(new)) * 100:4.1f}% of {len(new)})")
o("   (a half point on a total is worth 1-2 points of win chance at the best numbers - half of what the 3 is worth on a side)")
o("\n== the hook as a bet at -110 (train 1999-2014 / blind 2015-26) ==")
T = defaultdict(list)
for g in G:
    s, t, pts = g["season"], g["total"], g["pts"]
    over = 0.0 if pts == t else (P if pts > t else -1.0)
    under = 0.0 if pts == t else (P if pts < t else -1.0)
    T["every over"].append((s, over))
    T["every under"].append((s, under))
    for k in (41, 44, 47, 51):
        if t == k + 0.5:
            T[f"UNDER {k}.5 (the hook over the {k})"].append((s, under))
        if t == k - 0.5:
            T[f"OVER {k - 0.5} (the hook under the {k})"].append((s, over))
    if t in (41.5, 44.5, 47.5, 51.5):
        T["UNDER a half point over any of 41 / 44 / 47 / 51"].append((s, under))
    if t in (40.5, 43.5, 46.5, 50.5):
        T["OVER a half point under any of 41 / 44 / 47 / 51"].append((s, over))
for k, r in T.items():
    tr = [(s, p) for s, p in r if s <= 2014]
    bl = [(s, p) for s, p in r if s >= 2015]
    ub = L.by_season(bl)
    o(f"   {k[:52]:52s} {L.st([p for _, p in r])} | train {L.roi([p for _, p in tr]):+5.1f}% | BLIND {L.st([p for _, p in bl])} ({ub[0]}/{ub[1]})")
o(f"\ncells read: 9 numbers + {len(T)} = ~{9 + len(T)}")
o.save()
