"""S1 + S10a. KEY NUMBERS AND LINE SHOPPING (NFL / college football).
A. What a half point is worth at each number: how often the favorite wins by EXACTLY k when the close sits on / next
   to k (nflverse closes 1999-2026; college = our game files' closes 2016-26), and what that makes the hook worth.
B. BUYING the half point (S10a): the same games at the number at -110 vs a half point better at -120 / -125 / -135.
C. SHOPPING: the paid odds history's first FAIR look (every book, timestamped) - how often some book hangs a half
   point better than the market number, at which numbers, and what betting that book's number at ITS juice returned
   (both sides of every game are in, so the only thing being bet is the better number). Train 2020-22, held 2023-26.
   python s1_keys.py"""
import statistics
from collections import defaultdict
import lib2 as L

o = L.Out("s1")
B, N = L.B, L.N

# ---------------- A. the push / landing rates ----------------
NFL = N.games()
CF = [g for g in B.finals("ncaaf") if g["sp"] is not None and abs(g["sp"]) <= 60]


def fav_rows(lg):
    """[(season, favorite's closing spread (positive number), favorite's margin)]"""
    if lg == "nfl":
        return [(g["season"], abs(g["hl"]), g["m"] if g["hl"] < 0 else -g["m"]) for g in NFL if g["hl"] != 0]
    return [(g["season"], abs(g["sp"]), (g["hs"] - g["as"]) if g["sp"] < 0 else (g["as"] - g["hs"])) for g in CF if g["sp"] != 0]


for lg, keys, eras in (("nfl", (1, 2, 3, 4, 6, 7, 10, 14), (("1999-2014", 1999, 2014), ("2015-2026", 2015, 2026))),
                       ("ncaaf", (3, 4, 7, 10, 14, 17, 21, 24), (("2016-2021", 2016, 2021), ("2022-2026", 2022, 2026)))):
    R = fav_rows(lg)
    o(f"\n== A. {lg.upper()}: the favorite wins by EXACTLY k (games closing within a point of k; then ON k = the push rate) ==")
    for k in keys:
        row = [f"k={k:2d}"]
        for en, a, b in eras + (("all", 0, 9999),):
            near = [m for s, sp, m in R if a <= s <= b and abs(sp - k) <= 1]
            on = [m for s, sp, m in R if a <= s <= b and sp == k]
            row.append(f"{en}: within a point {sum(1 for m in near if m == k) / max(1, len(near)) * 100:4.1f}% of {len(near):4d}; "
                       f"ON it pushes {sum(1 for m in on if m == k) / max(1, len(on)) * 100:4.1f}% of {len(on):4d}")
        o("   " + " | ".join(row))
    # the dog loses by exactly k-ish: what +k.5 instead of +k buys = the push rate; +k instead of +(k-.5) = half of it
    o("   (a hook ONTO the number turns losses into pushes, a hook OFF it turns pushes into wins - each is worth about half the push rate in cover %)")

# ---------------- B. buying the half point ----------------
o("\n== B. BUYING THE HALF POINT (the same games: the closing number at -110 vs a half point better at a price) ==")
for lg in ("nfl", "ncaaf"):
    R = fav_rows(lg)
    for k in ((3, 7, 2.5, 6.5, 3.5, 7.5, 10, 14) if lg == "nfl" else (3, 7, 2.5, 6.5, 10, 14)):
        for who in ("dog", "fav"):
            base, rows = [], defaultdict(list)
            for s, sp, m in R:
                if sp != k:
                    continue
                # dog holds +sp, buys to +sp+.5 ; fav holds -sp, buys to -sp+.5
                r0 = (-m + sp) if who == "dog" else (m - sp)
                r1 = r0 + 0.5
                base.append((s, 0.0 if r0 == 0 else (L.dec(-110) - 1 if r0 > 0 else -1.0)))
                for pr in (-120, -125, -135):
                    rows[pr].append((s, 0.0 if r1 == 0 else (L.dec(pr) - 1 if r1 > 0 else -1.0)))
            if len(base) < 80:
                continue
            split = 2015 if lg == "nfl" else 2022
            def two(rs):
                return f"{L.roi([p for s, p in rs]):+5.1f}% (old {L.roi([p for s, p in rs if s < split]):+5.1f} / new {L.roi([p for s, p in rs if s >= split]):+5.1f})"
            o(f"   {lg} {who} at {'+' if who == 'dog' else '-'}{k:<4} n {len(base):4d}: at -110 {two(base)} | half pt better at -120 {two(rows[-120])} | -125 {two(rows[-125])} | -135 {two(rows[-135])}")

# ---------------- C. shopping the first fair look ----------------
KEYS = {"nfl": (3, 7, 10, 6, 4, 14), "ncaaf": (3, 7, 10, 14, 17, 21)}


def clean(books, med):
    """Books whose line is within 1.5 of the market number at a normal price (drops alt lines / junk rows)."""
    out = {}
    for bk, (hp, hpr, ap, apr) in books.items():
        if abs(hp - med) <= 1.5 and hp == -ap and -140 <= hpr <= 125 and -140 <= apr <= 125:
            out[bk] = (hp, hpr, ap, apr)
    return out


def sides(g):
    """[(side, market line for the side, [(book, line, price)])] at the first fair look."""
    bk = clean(g["first"][1], g["med"])
    if len(bk) < 5:
        return []
    med = statistics.median(v[0] for v in bk.values())
    return [("home", med, [(b, v[0], v[1]) for b, v in bk.items()]), ("away", -med, [(b, v[2], v[3]) for b, v in bk.items()])]


for lg in ("nfl", "ncaaf"):
    F = [g for g in L.football(lg) if g["c_sp"] is None or abs(g["c_sp"] - g["med"]) <= (7 if lg == "nfl" else 10)]
    o(f"\n== C. {lg.upper()} SHOPPING at the first fair look ({len(F)} games, 5+ clean books) ==")
    T = defaultdict(list)
    ngames, nhook, nhook_key = 0, 0, 0
    for g in F:
        ss = sides(g)
        if not ss:
            continue
        ngames += 1
        anyh = anyk = False
        for side, m, bl in ss:
            s = g["season"]
            medpr = B.american(statistics.median(L.dec(p) for _, ln, p in bl if ln == m)) if any(ln == m for _, ln, p in bl) else -110
            T["every side at the market number, the median price"].append((s, L.cover(g["margin"], m if side == "home" else -m, side, medpr)))
            # the best book: best line, then best price
            bb = max(bl, key=lambda x: (x[1], L.dec(x[2])))
            T["every side at the BEST book (best number, then price)"].append((s, L.cover(g["margin"], bb[1] if side == "home" else -bb[1], side, bb[2])))
            bp = max((x for x in bl if x[1] == m), key=lambda x: L.dec(x[2]), default=None)
            if bp:
                T["every side at the market number, the best PRICE on it"].append((s, L.cover(g["margin"], m if side == "home" else -m, side, bp[2])))
            better = [x for x in bl if x[1] >= m + 0.5 and x[2] >= -120]
            if not better:
                continue
            anyh = True
            bb = max(better, key=lambda x: (x[1], L.dec(x[2])))
            p = L.cover(g["margin"], bb[1] if side == "home" else -bb[1], side, bb[2])
            T["a book a half point+ better than the market, -120 or cheaper"].append((s, p))
            T[f"   ... {'dog' if m > 0 else 'fav'} side"].append((s, p))
            if bb[1] >= m + 1:
                T["   ... a full point better"].append((s, p))
            cheap = [x for x in bl if x[1] >= m + 0.5 and x[2] >= -112]
            if cheap:
                cb = max(cheap, key=lambda x: (x[1], L.dec(x[2])))
                T["   ... the better number at -112 or cheaper (a free hook)"].append((s, L.cover(g["margin"], cb[1] if side == "home" else -cb[1], side, cb[2])))
                if any(b_ in L.SHARP for b_, ln, pr in bl if ln >= m + 0.5):
                    T["   ... free hook hung by a sharp book (lowvig / betonline / circa)"].append((s, L.cover(g["margin"], cb[1] if side == "home" else -cb[1], side, cb[2])))
                else:
                    T["   ... free hook hung only by soft books"].append((s, L.cover(g["margin"], cb[1] if side == "home" else -cb[1], side, cb[2])))
            for k in KEYS[lg]:
                # the better number sits ON or THROUGH the key (dog: market +k-.5 / +k -> +k / +k.5 ; fav: market -k / -k-.5 -> -k+.5 / -k)
                if m > 0 and m in (k - 0.5, k) and bb[1] >= m + 0.5:
                    T[f"   dog: market +{m:g} -> the book hangs +{m + .5:g} or better (key {k})"].append((s, p))
                    T[f"   KEY {k}: any side whose better number touches / crosses it"].append((s, p))
                    anyk = k in KEYS[lg][:2] or anyk
                if m < 0 and -m in (k, k + 0.5) and bb[1] >= m + 0.5:
                    T[f"   fav: market {m:g} -> the book hangs {m + .5:g} or better (key {k})"].append((s, p))
                    T[f"   KEY {k}: any side whose better number touches / crosses it"].append((s, p))
                    anyk = k in KEYS[lg][:2] or anyk
            if all(not (m > 0 and m in (k - 0.5, k)) and not (m < 0 and -m in (k, k + 0.5)) for k in KEYS[lg][:3]):
                T["   the better number is NOT at the 3 / 7 / 10"].append((s, p))
            # the same side at the market number, to see what the hook itself bought
            T["   (the same sides at the MARKET number, median price)"].append((s, L.cover(g["margin"], m if side == "home" else -m, side, medpr)))
            # the side ACROSS the off-market book (the stale book is the one out of line - is the market right?)
        nhook += anyh
        nhook_key += anyk
    o(f"   games where some book hangs a half point+ better than the market at -120 or cheaper: {nhook} of {ngames} ({nhook / max(1, ngames) * 100:.0f}%); touching the 3 or the 7: {nhook_key} ({nhook_key / max(1, ngames) * 100:.0f}%)")
    for k in sorted(T, key=lambda x: (x.startswith("   "), x)):
        if len(T[k]) >= 40:
            o("   " + L.line(k, T[k]))
o("\ncells read: A 16 numbers x 3 eras, B 28 rows x 4 prices, C ~2 x 35 rows = ~230")
o.save()
