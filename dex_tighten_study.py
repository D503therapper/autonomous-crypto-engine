"""DEX TIGHTEN study (owner 2026-10-01: "we're losing our ass - tighten up and go to the moon").

Two questions on the consolidated study's 205 cached pools (offline, same account model as dex_consolidated_study):
  exit   take the stake back at 2x (sell half; live since 2026-09-30, EXPERIMENT 3b) vs at 3x (sell a third) vs never.
  entry  the live buys after 2026-09-30 were bounces in a crash (SHARTCOIN 1h +12% / 6h -45%, MORI +22% / -57%);
         does skipping a +10% hour that comes after a big 6h drop help?  And skipping a coin already up a lot in 6h?
Scored like the other studies: monthly return per half (older / newer, each from $1,000), max drawdown, and 300
resampled accounts that drop 30% of the signals by coin-day (median / 10th / 90th percentile).  A change is worth it
only if it wins in BOTH halves and in the resampled medians.

    python dex_tighten_study.py          # offline, ~1-3 minutes
"""
import random
import statistics

import dex_consolidated_study as CS
import dex_floor_study as FL
from dex_exit_study import DAY, pct, ts

EXITS = {"never sell early": {}, "stake back at 3x": {"tp": (3.0, 1 / 3)}, "stake back at 2x (live)": {"tp": (2.0, 0.5)}}
ENTRIES = {
    "live entry": lambda s: True,
    "skip if 6h <= -30%": lambda s: s["ch6"] > -0.30,
    "skip if 6h <= -40%": lambda s: s["ch6"] > -0.40,
    "skip if 6h <= -20%": lambda s: s["ch6"] > -0.20,
    "skip if 6h >= +200%": lambda s: s["ch6"] < 2.0,
    "skip 6h <= -30% or >= +200%": lambda s: -0.30 < s["ch6"] < 2.0,
    "need 6h >= +25%": lambda s: s["ch6"] >= 0.25,
    "need 6h >= +50%": lambda s: s["ch6"] >= 0.50,
    "need 6h >= +100%": lambda s: s["ch6"] >= 1.0,
}


def outcomes(pools, sigs, v):
    FL.EXIT = dict(CS.LIVE_EXIT, max_hold_days=CS.LIVE_HOLD)
    v = {"key": "x", **v}
    res = []
    try:
        for s in sigs:
            P = pools[s["k"]]
            rug = P.rugset if hasattr(P, "rugset") else None
            if rug is None:
                rug = P.rugset = {j for j in range(P.n) if P.rug[j]}
            x = FL.simulate(P.t0_list, P.O, P.H, P.L, P.C, CS.HOUR, s["i"], v, s["liq"], rug, P.dead)
            res.append((x["ret"], x["exit_t"], x["peak"], x["rug"]))
    finally:
        FL.EXIT = CS.LIVE_EXIT
    return res


def add_ch6(pools, sigs):
    for s in sigs:
        P = pools[s["k"]]
        f = P.features(s["i"])
        s["ch6"] = f["ch6"]


def drops(sigs, runs, keep=0.7, seed=7):
    rnd = random.Random(seed)
    units = {}
    for s in sigs:
        units.setdefault((s["k"], s["t"] // DAY), []).append(s["id"])
    keys = sorted(units)
    out = []
    for _ in range(runs):
        d = set()
        for u in keys:
            if rnd.random() > keep:
                d.update(units[u])
        out.append(frozenset(d))
    return out


def main():
    pools, info = CS.load_union("results/dex_floor_hourly.json.gz", "results/dex_filter_pools.json.gz")
    now = info["now"]
    ws0, t_last = now - int(2.7 * CS.MONTH), now - DAY
    sigs = CS.signals(pools, ws0, t_last)
    add_ch6(pools, sigs)
    R = {name: outcomes(pools, sigs, v) for name, v in EXITS.items()}
    seq = CS.pool_sequence(sigs, R["never sell early"])
    T0, T1 = min(s["t"] for s in sigs), now
    split = sorted(s["t"] for s, _ in seq)[len(seq) // 2]
    halves = {"older": (T0, split), "newer": (split, T1)}
    D = drops(sigs, 300)
    print(f"pools {info['union']}; {len(sigs)} signal hours; window {ts(T0)} .. {ts(T1)}; halves split at {ts(split)}; "
          f"{CS.LIVE_SLOTS} slots, tiers A {CS.TIERS['A']['pct']:.1%}; exit {CS.LIVE_EXIT}")

    FL.banner("1. PER-TRADE (pool-sequential, live entry): what each exit does to the trades that doubled")
    for name in EXITS:
        sq = CS.pool_sequence(sigs, R[name])
        st = CS.trade_stats(sq)
        dbl = [r for _, r in sq if r[2] >= 2.0]
        print(f"  {name:<26} n {st['n']:>3}  mean {pct(st['mean'], 7)}  median {pct(st['med'], 6)}  >=2x closed {st['x2']:.0%}  "
              f"<=-70% {st['l70']:.0%} | trades that peaked >=2x: {len(dbl)}, closed at a loss {sum(r[0] < 0 for r in dbl)}, "
              f"mean {pct(statistics.fmean([r[0] for r in dbl]) if dbl else 0, 7)}")

    FL.banner("2. ENTRY: trades by the 6h move before the +10% hour (pool-sequential, live exit)")
    sq = CS.pool_sequence(sigs, R["stake back at 2x (live)"])
    for lo, hi in ((-9, -0.4), (-0.4, -0.2), (-0.2, 0), (0, 0.5), (0.5, 2.0), (2.0, 99)):
        xs = [r[0] for s, r in sq if lo <= s["ch6"] < hi]
        if xs:
            print(f"  6h {pct(lo, 5, 0) if lo > -9 else '  low'} .. {pct(hi, 5, 0) if hi < 99 else 'high'}: n {len(xs):>3}  "
                  f"mean {pct(statistics.fmean(xs), 7)}  median {pct(statistics.median(xs), 6)}  "
                  f"win {sum(x > 0 for x in xs) / len(xs):.0%}  <=-50% {sum(x <= -0.5 for x in xs) / len(xs):.0%}")

    FL.banner("3. ACCOUNT: monthly return per half (each half from $1,000) and resampled medians [p10..p90]")
    print(f"  {'entry':<30}{'exit':<26}{'older':>9}{'newer':>9}{'maxDD':>7}  resampled older            resampled newer")
    rows = []
    for en, ok in ENTRIES.items():
        sub_drop = frozenset(s["id"] for s in sigs if not ok(s))
        for ex in EXITS:
            r = {h: CS.account(sigs, R[ex], x, y, CS.LIVE_SLOTS, sub_drop) for h, (x, y) in halves.items()}
            rs = {h: sorted(CS.account(sigs, R[ex], x, y, CS.LIVE_SLOTS, sub_drop | d)["monthly"] for d in D)
                  for h, (x, y) in halves.items()}
            q = {h: (rs[h][150], rs[h][30], rs[h][270]) for h in rs}
            dd = min(r["older"]["dd"], r["newer"]["dd"])
            rows.append((en, ex, r, q, dd))
            print(f"  {en:<30}{ex:<26}{pct(r['older']['monthly'], 9)}{pct(r['newer']['monthly'], 9)}{pct(dd, 7, 0)}  "
                  + "  ".join(f"{pct(q[h][0], 7)} [{pct(q[h][1], 6, 0)}..{pct(q[h][2], 6, 0)}]" for h in ("older", "newer")))

    FL.banner("4. VERDICT  (vs live entry + live exit; must win both halves AND both resampled medians)")
    base = next(x for x in rows if x[0] == "live entry" and x[1] == "stake back at 2x (live)")
    for en, ex, r, q, dd in rows:
        if (en, ex) == base[:2]:
            continue
        wins = all(r[h]["monthly"] > base[2][h]["monthly"] for h in ("older", "newer")) and \
            all(q[h][0] > base[3][h][0] for h in ("older", "newer"))
        if wins:
            print(f"  PASSES  {en} + {ex}: older {pct(r['older']['monthly'], 1)} / newer {pct(r['newer']['monthly'], 1)} "
                  f"(live {pct(base[2]['older']['monthly'], 1)} / {pct(base[2]['newer']['monthly'], 1)}), maxDD {pct(dd, 1, 0)}")
    print("  (no line above = nothing beats the live rules everywhere)")


if __name__ == "__main__":
    main()
