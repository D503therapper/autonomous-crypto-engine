"""DEX MINIMUM-AGE study: should the hunter buy pools younger than 6 hours?

Trigger (2026-09-27 afternoon): every big DEX mover the hunter missed was younger than the 6h minimum age
(NEARPAD +195% at age 1-3h, liq $65-120k; METAMUSE +186% at 1-2h; VAULT +86% < 1h; GTA 6 COIN +64% at 2h).
dex_filter_study showed RAISING the age (12h / 24h) hurts; this tests LOWERING it.

  variants  min age 1h / 2h / 3h / 4h vs the live 6h, current entry (1h >= +10%, liq / vol24 >= $100k) and exit
            young (< 6h) entries only with liq >= $150k / $250k
            young (< 6h) entries at half size
  account   config.DEX["slots"] (5) slots, 1/slots of equity per trade (x0.5 for half-size young trades), compounding;
            costs 0.3% fee + 1% slippage + impact per side, rugs -95% (dex_runner_study.simulate)
  rugs      rug and <= -70% rates of the entries made at age < 6h separately, plus a STRESS run: the young rug rate is
            doubled (at least 2x the rug rate of >= 6h entries) by turning the worst extra young losers into -95% rugs
  data      results/dex_filter_pools.json.gz (dex_filter_study's hourly GeckoTerminal grids; pools launched inside the
            window start within ~1h of creation, so their first hours are visible).  The first hour (bar 0) is an entry
            point too: 1h change = close / open of the first bar (DexScreener's h1 at age ~1h).

LIMITS (read before trusting): the dump only holds pools the 6h rule also traded, and the registry only pools >= 2 days
old - a pool that pumped at 2h and rugged before 6h is MISSING.  Young-entry rug rates are floors; the stress test is
the guard.  No buys / sells history.  Liquidity is a constant-product estimate.

    python dex_age_study.py [--cache results/dex_filter_pools.json.gz]
"""
import argparse
import math
import statistics

import dex_runner_study as RS
from dex_exit_study import DAY, HOUR, liq_at, pct, ts
from dex_filter_study import load_pools

try:
    import config
    SLOTS = int(config.DEX.get("slots", 5))
except Exception:                      # pragma: no cover
    SLOTS = 5

SCREEN, ENTRY = RS.SCREEN, RS.ENTRY
MIN_LIQ, MIN_VOL, LIVE_AGE = SCREEN.get("min_liq", 100_000), SCREEN.get("min_vol24", 100_000), SCREEN.get("min_age_h", 6)
H1 = ENTRY.get("h1", 0.10)
YOUNG = 6.0
NAN = float("nan")


def V(name, age, yliq=None, ysize=1.0):
    return {"name": name, "age": age, "yliq": yliq, "ysize": ysize}


VARIANTS = [V("base: min age 6h (live)", 6)]
for a in (1, 2, 3, 4):
    VARIANTS.append(V(f"min age {a}h", a))
for a in (1, 2, 3, 4):
    VARIANTS += [V(f"min age {a}h, young liq>=$150k", a, 150_000), V(f"min age {a}h, young liq>=$250k", a, 250_000),
                 V(f"min age {a}h, young half size", a, None, 0.5)]


def feats(P, i):
    """P.features(i), plus the first bar (i = 0): 1h change = close / open of that bar."""
    if i >= 1:
        return P.features(i)
    c, o = P.C[0], P.O[0]
    if c <= 0 or o <= 0:
        return None
    t = P.t0 + HOUR
    return {"t": t, "age_h": (t - P.p["created"]) / HOUR, "liq": liq_at(P.p, c), "vol24": P.V[0], "ch1": c / o - 1}


def run(pools, v, ws0, t_last):
    tr, rs = [], []
    for P in pools:
        locked = 0
        for i in range(0, P.n):
            t = P.t0 + (i + 1) * HOUR
            if t < ws0 or t > t_last or t < locked or P.cv[i + 1] - P.cv[max(0, i - 23)] < MIN_VOL:
                continue
            f = feats(P, i)
            if not f or f["age_h"] < v["age"] or f["liq"] < MIN_LIQ or f["vol24"] < MIN_VOL or f["ch1"] < H1:
                continue
            young = f["age_h"] < YOUNG
            if young and v["yliq"] and f["liq"] < v["yliq"]:
                continue
            x = RS.simulate(P, i, f["liq"])
            locked = x[1]
            tr.append({"t0": t, "k": P.key, "sym": P.p.get("sym", "?"), "age": f["age_h"], "liq": f["liq"],
                       "young": young, "f": v["ysize"] if young else 1.0})
            rs.append(x)
    return tr, rs


def portfolio(trades, res, t_from, t_to, slots=SLOTS):
    """dex_exit_study.portfolio with a per-trade size factor (half-size young trades still use a slot)."""
    ev = sorted((tr["t0"], x[1], x[0], tr["f"]) for tr, x in zip(trades, res) if t_from <= tr["t0"] < t_to)
    cash, opn, peak, dd, taken = 1.0, [], 1.0, 0.0, 0
    for t0, t1, r, fz in ev:
        for o in [o for o in opn if o[0] <= t0]:
            cash += o[1] * (1 + o[2])
            opn.remove(o)
        eq = cash + sum(o[1] for o in opn)
        peak, dd = max(peak, eq), min(dd, eq / peak - 1)
        if len(opn) < slots and cash > 1e-9:
            size = min(cash, eq / slots * fz)
            cash -= size
            opn.append((max(t1, t0), size, r))
            taken += 1
    cash += sum(o[1] * (1 + o[2]) for o in opn)
    dd = min(dd, cash / peak - 1)
    months = max(0.5, (t_to - t_from) / (30.44 * DAY))
    return {"monthly": max(cash, 1e-9) ** (1 / months) - 1, "dd": dd, "taken": taken}


def stress(tr, rs, old_rug, bad=False):
    """Double the young rug rate (at least 2x the >= 6h entries' rate): the worst non-rug young trades become rugs.
    bad=True (harsh): double the young <= -70% rate instead (rugs + deep losers)."""
    yi = [k for k, t in enumerate(tr) if t["young"]]
    if not yi:
        return rs, 0
    n_rug = sum(rs[k][4] or (bad and rs[k][0] <= -0.7) for k in yi)
    extra = max(n_rug, math.ceil(old_rug * len(yi)))
    cand = sorted((k for k in yi if not rs[k][4] and not (bad and rs[k][0] <= -0.7)), key=lambda k: rs[k][0])[:extra]
    out = list(rs)
    for k in cand:
        x = out[k]
        out[k] = (RS.RUG_LOSS, x[1], x[2], x[3], True)
    return out, len(cand)


def resample(R, names, T0, T1, split, runs=300, keep=0.7, seed=7):
    """The 5-slot account takes only ~30 of ~380 signals (14-day holds keep the slots full), so ONE trade decides a
    half.  Robustness: drop 30% of the signals at random (the same pool-hour is dropped in every variant) and re-run
    the account -> median monthly per half and the share of runs a variant beats the 6h rule."""
    import random
    rng = random.Random(seed)
    keys = sorted({(t["k"], t["t0"]) for n in names for t in R[n][0]})
    out = {n: {"old": [], "new": [], "dd": []} for n in names}
    for _ in range(runs):
        drop = {k for k in keys if rng.random() > keep}
        for n in names:
            tr, rs = R[n]
            sel = [(t, x) for t, x in zip(tr, rs) if (t["k"], t["t0"]) not in drop]
            tr2, rs2 = [q[0] for q in sel], [q[1] for q in sel]
            out[n]["old"].append(portfolio(tr2, rs2, T0, split)["monthly"])
            out[n]["new"].append(portfolio(tr2, rs2, split, T1)["monthly"])
            out[n]["dd"].append(portfolio(tr2, rs2, T0, T1)["dd"])
    return out


def summ(tr, rs, T0, T1, split):
    xs = [x[0] for x in rs]
    y = [x for t, x in zip(tr, rs) if t["young"]]
    full, old, new = portfolio(tr, rs, T0, T1), portfolio(tr, rs, T0, split), portfolio(tr, rs, split, T1)
    return {"n": len(xs), "ny": len(y), "mean": RS.mean(xs) if xs else NAN, "med": statistics.median(xs) if xs else NAN,
            "l70": RS.rate([v <= -0.7 for v in xs]), "rug": RS.rate([x[4] for x in rs]),
            "y_mean": RS.mean([x[0] for x in y]) if y else NAN, "y_med": statistics.median([x[0] for x in y]) if y else NAN,
            "y_l70": RS.rate([x[0] <= -0.7 for x in y]), "y_rug": RS.rate([x[4] for x in y]),
            "y_x2": RS.rate([x[0] >= 1.0 for x in y]),
            "month": full["monthly"], "old": old["monthly"], "new": new["monthly"], "dd": full["dd"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="results/dex_filter_pools.json.gz")
    ap.add_argument("--months", type=float, default=2.7)
    a = ap.parse_args()
    pools = load_pools(a.cache)
    for P in pools:
        P.derive()
    now = max(P.now for P in pools)
    ws0 = now - int(a.months * 30.44 * DAY)
    t_last = now - DAY
    inw = [P for P in pools if P.p["created"] >= ws0]
    early = [P for P in inw if P.t0 - P.p["created"] <= 2 * HOUR]
    print(f"{len(pools)} pools from {a.cache}; {len(inw)} launched inside the window, {len(early)} of them with hourly bars "
          f"from their first 2 hours (only these can give < 6h entries)")
    print(f"entry: 1h >= {H1:+.0%}, liq >= ${MIN_LIQ:,.0f}, vol24 >= ${MIN_VOL:,.0f}; exit config.DEX['exit']; "
          f"costs {RS.FEE:.1%} fee + {RS.SLIP:.0%} slippage + impact per side, rugs {RS.RUG_LOSS:.0%}; {SLOTS}-slot account")

    R = {v["name"]: run(pools, v, ws0, t_last) for v in VARIANTS}
    bt, br = R[VARIANTS[0]["name"]]
    T0, T1 = min(min((t["t0"] for t in tr), default=now) for tr, _ in R.values()), now
    split = sorted(t["t0"] for t in bt)[len(bt) // 2]
    old_rug = RS.rate([x[4] for t, x in zip(bt, br)])
    print(f"window {ts(T0)[:10]}..{ts(t_last)[:10]}, halves split at {ts(split)[:16]}; rug rate of the 6h rule's entries "
          f"{old_rug:.1%} (the stress floor for young entries is 2x that)")

    hdr = (f"{'variant':<34} {'n':>4} {'<6h':>4} {'mean':>7} {'median':>7} {'<=-70%':>6} {'rug':>4} | {'young: mean':>11} "
           f"{'>=2x':>5} {'<=-70%':>6} {'rug':>5} | {'month':>8} {'older':>8} {'newer':>8} {'maxDD':>6} || STRESS {'month':>8} "
           f"{'older':>8} {'newer':>8} {'maxDD':>6} (+rugs)")
    print("\n" + hdr + "\n" + "-" * len(hdr))
    S = {}
    for v in VARIANTS:
        tr, rs = R[v["name"]]
        s = summ(tr, rs, T0, T1, split)
        rs2, extra = stress(tr, rs, old_rug)
        s2 = summ(tr, rs2, T0, T1, split)
        rs3, extra3 = stress(tr, rs, old_rug, bad=True)
        S[v["name"]] = (s, s2, extra)
        R[v["name"] + " #hard"] = (tr, rs3)
        R[v["name"] + " #stress"] = (tr, rs2)
        yl = (f"{pct(s['y_mean'], 11)} {s['y_x2']:>5.0%} {s['y_l70']:>6.0%} {s['y_rug']:>5.0%}" if s["ny"] else f"{'-':>11} {'':>5} {'':>6} {'':>5}")
        print(f"{v['name']:<34} {s['n']:>4} {s['ny']:>4} {pct(s['mean'], 7)} {pct(s['med'], 7)} {s['l70']:>6.0%} {s['rug']:>4.0%} | {yl} | "
              f"{pct(s['month'], 8)} {pct(s['old'], 8)} {pct(s['new'], 8)} {pct(s['dd'], 6, 0)} || STRESS {pct(s2['month'], 8)} "
              f"{pct(s2['old'], 8)} {pct(s2['new'], 8)} {pct(s2['dd'], 6, 0)} (+{extra})")
    print("(n = trades; <6h = entries made at pool age < 6h; young = those entries only; month = compounding account; "
          "older / newer = before / after the split; STRESS = young rug rate doubled, worst young losers -> -95%)")

    print("\nEntries at age < 6h (all variants pooled, unique pool + hour):")
    seen = {}
    for v in VARIANTS[1:5]:
        for t, x in zip(*R[v["name"]]):
            if t["young"]:
                seen[(t["k"], t["t0"])] = (t, x)
    for t, x in sorted(seen.values(), key=lambda q: q[0]["t0"]):
        print(f"  {ts(t['t0'])[:16]} {t['sym'][:12]:<12} age {t['age']:>4.1f}h liq ${t['liq'] / 1000:>5.0f}k -> {pct(x[0], 8)} "
              f"peak {x[2]:>5.1f}x" + ("  RUG" if x[4] else ""))

    print("\nSLOT-FREE per-trade view (sum of trade returns per half, 1 unit each; survivorship makes young ones look better):")
    for v in VARIANTS:
        tr, rs = R[v["name"]]
        o = sum(x[0] for t, x in zip(tr, rs) if t["t0"] < split)
        n = sum(x[0] for t, x in zip(tr, rs) if t["t0"] >= split)
        print(f"  {v['name']:<34} older {o:>+7.1f}  newer {n:>+7.1f}")

    base = VARIANTS[0]["name"]
    names = [v["name"] for v in VARIANTS] + [v["name"] + s for v in VARIANTS[1:] for s in (" #stress", " #hard")]
    RSM = resample(R, names, T0, T1, split)
    med = lambda xs: statistics.median(xs)
    beat = lambda n, h: RS.mean([a > b for a, b in zip(RSM[n][h], RSM[base][h])])
    print(f"\nRESAMPLED {SLOTS}-slot account (300 runs, each drops a random 30% of the signals, same drop in every variant):")
    print(f"{'variant':<44} {'older med':>9} {'newer med':>9} {'maxDD med':>9} | {'beats 6h: older':>15} {'newer':>6}")
    for n in names:
        print(f"{n:<44} {pct(med(RSM[n]['old']), 9)} {pct(med(RSM[n]['new']), 9)} {pct(med(RSM[n]['dd']), 9, 0)} | "
              f"{beat(n, 'old'):>15.0%} {beat(n, 'new'):>6.0%}")
    print("(#stress = young rug rate doubled; #hard = young <= -70% rate doubled, the extra losers at -95%)")

    b, b2, _ = S[VARIANTS[0]["name"]]
    bm = {h: med(RSM[base][h]) for h in ("old", "new", "dd")}
    print("\nVERDICT (apply only if: monthly better in BOTH halves - the single account AND the resampled median -, max drawdown "
          "no more than 5 points deeper, and the STRESS run still beats the 6h rule in both halves)")
    win = []
    for v in VARIANTS[1:]:
        s, s2, _ = S[v["name"]]
        c = {"older better": s["old"] > b["old"], "newer better": s["new"] > b["new"], "DD ok": s["dd"] >= b["dd"] - 0.05,
             "stress older": s2["old"] > b["old"], "stress newer": s2["new"] > b["new"],
             "resampled older": med(RSM[v["name"]]["old"]) > bm["old"], "resampled newer": med(RSM[v["name"]]["new"]) > bm["new"],
             "resampled stress both": all(med(RSM[v["name"] + " #stress"][h]) > bm[h] for h in ("old", "new"))}
        ok = all(c.values())
        win += [v["name"]] if ok else []
        print(f"  {v['name']:<34} {'PASS' if ok else 'fail'}  " + ", ".join(("" if y else "NOT ") + k for k, y in c.items()))
    print("\nRESULT: " + (f"passed: {', '.join(win)}" if win else "no variant passed - keep min age 6h"))


if __name__ == "__main__":
    main()
