"""Which DEX entries have an edge? (owner 11-17: "figure it out") - every cell of a small grid, judged out of sample.
Scanner snapshots data/dex/scan/*.csv.gz (09-26 ..), hourly per pool, pools with $100k+ liquidity. For each rule cell,
the FIRST hour a pool meets it is the entry; the live exit is simulated on the next 7 days (80% at 5x, after 3x a 40%
drop sells all, rug = liquidity beyond the price move gone or -98%, fills at the lower of 2 snapshots, 0.3%/side).
Cells are scored on the first 60% of the days (train) and the last 40% (test): only cells positive in BOTH count.
No scam screen is modelled (the live screen rejects many of the rugs here), so absolute numbers are pessimistic."""
import csv, glob, gzip, sys
from collections import defaultdict
from datetime import datetime

C = 0.003
F = lambda x: float(x) if x not in (None, "", "nan") else None


def load():
    S = defaultdict(dict)                       # (chain, addr) -> {hour: row}
    for fn in sorted(glob.glob("data/dex/scan/*.csv.gz")):
        for r in csv.DictReader(gzip.open(fn, "rt")):
            liq, p = F(r["liq"]), F(r["price"])
            if not p or p <= 0 or not liq or liq < 50_000:
                continue
            hr = r["time"][:13]
            S[(r["chain"], r["addr"].lower())][hr] = (r, p, liq)
    out = {}
    for k, d in S.items():
        hs = sorted(d)
        out[k] = [(datetime.strptime(h, "%Y-%m-%d %H").timestamp(), d[h][0], d[h][1], d[h][2]) for h in hs]
    return out


def sim(path, p0, l0):
    """path: [(t, price, liq)] after entry (7 days). Returns $ back per $1."""
    pk, cash, held, armed, sold, prev = 1.0, 0.0, 1.0, False, False, None
    if any(p / p0 > 1000 for _, p, _ in path):
        return None                                             # feed glitch (1e6x prints): drop the entry
    for _, p, l in path:
        x = p / p0
        if prev is not None and (x > 20 * prev or x < prev / 20) and l < 0.3 * l0:
            continue                                            # a lone bad print with no liquidity behind it
        if l < 0.5 * l0 * min(1, x) ** 0.5 or x < 0.02:
            return cash                                         # rug: the rest is lost
        if prev is None:
            prev = x
            continue
        y, prev = min(prev, x), x
        pk = max(pk, y)
        if not sold and y >= 5:
            cash += 0.8 * 5 * (1 - C) ** 2; held -= 0.8; sold = True
        if pk >= 3:
            armed = True
        if armed and y <= pk * 0.6:
            return cash + held * y * (1 - C) ** 2
    return cash + held * (prev or 1) * (1 - C) ** 2


def bucket(v, edges, names):
    if v is None:
        return None
    for e, n in zip(edges, names):
        if v < e:
            return n
    return names[-1]


AGE = ([24, 72, 168, 720], ["age<1d", "age1-3d", "age3-7d", "age7-30d", "age30d+"])
LIQ = ([250e3, 1e6], ["liq100-250k", "liq250k-1M", "liq1M+"])
H24 = ([-0.3, 0, 0.5, 2.0], ["24h<-30%", "24h-30..0", "24h0..+50%", "24h+50..200%", "24h>+200%"])
H1 = ([-0.05, 0.05, 0.2], ["1h<-5%", "1h-5..+5%", "1h+5..20%", "1h>+20%"])


def cells(r, liq):
    age, h24, h1 = F(r["age_h"]), F(r["h24"]), F(r["h1"])
    b = {"chain": r["chain"], "age": bucket(age, *AGE), "liq": bucket(liq, *LIQ), "h24": bucket(h24, *H24),
         "h1": bucket(h1, *H1)}
    if None in b.values():
        return []
    keys = list(b)
    out = [(k, b[k]) for k in keys]
    out += [(f"{a}+{c}", f"{b[a]} {b[c]}") for i, a in enumerate(keys) for c in keys[i + 1:]]
    return out


def main():
    data = load()
    tmin = min(s[0][0] for s in data.values()); tmax = max(s[-1][0] for s in data.values())
    split = tmin + 0.6 * (tmax - tmin)
    res = defaultdict(lambda: [[], []])                  # cell -> [train returns, test returns]
    for k, s in data.items():
        seen = set()
        for i, (t, r, p, l) in enumerate(s):
            if tmax - t < 3 * 86400 or F(r["liq"]) < 100_000:
                continue
            for c in cells(r, l):
                if c in seen:
                    continue
                seen.add(c)
                path = [(tt, pp, ll) for tt, _, pp, ll in s[i + 1:] if tt - t <= 7 * 86400]
                horizon = min(t + 7 * 86400, tmax)
                if not path or horizon - path[-1][0] > 24 * 3600:   # the scanner dropped the pool (dead / gone):
                    path = path + [(horizon, 0.0, 0.0)]          # count what was still held as lost, not as kept
                v = sim(path, p, l)
                if v is not None:
                    res[c][0 if t < split else 1].append(min(v, 100.0) - 1)   # cap one trade at 100x
    rows = []
    for c, (a, b) in res.items():
        if len(a) >= 20 and len(b) >= 15:
            ma, mb = sum(a) / len(a), sum(b) / len(b)
            rows.append((min(ma, mb), ma, mb, len(a), len(b), c))
    rows.sort(reverse=True)
    print(f"pools {len(data)}, span {datetime.utcfromtimestamp(tmin):%m-%d} .. {datetime.utcfromtimestamp(tmax):%m-%d}, "
          f"split {datetime.utcfromtimestamp(split):%m-%d}; cells with n>=20 train / 15 test: {len(rows)}")
    print("per $1 (live exit, 7 days): worst-of-halves | train | test | n train / test | cell")
    for w, ma, mb, na, nb, c in rows[:30]:
        print(f"  {w:+.3f} | {ma:+.3f} | {mb:+.3f} | {na:4d} / {nb:4d} | {c[0]}: {c[1]}")
    print(f"cells positive in both halves: {sum(1 for r in rows if r[0] > 0)} of {len(rows)}")
    allr = [x for c, (a, b) in res.items() if c[0] == 'chain' for x in a + b]
    print(f"baseline (any $100k+ pool, first hour seen): {sum(allr) / max(len(allr), 1):+.3f} per $1, n {len(allr)}")


if __name__ == "__main__":
    main()
