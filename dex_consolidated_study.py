"""DEX CONSOLIDATED study: is the live DEX strategy profitable at all?  One run that reconciles the earlier studies.

The SAME live entry / exit gave very different monthly results: dex_runner_study +101% (its 2026-09-26 run; the
09-27 re-run said -3.6%), dex_floor_study +44% (-3% / +276% halves), dex_filter_study +16.6% (-14.9% / -0.6%),
dex_age_study -26.3% / -0.1%.  This study puts every cached pool through ONE account model that follows the live
rules as closely as the data allows, then asks how much of any result is luck.

  pools     union of the cached hourly grids (no network): results/dex_floor_hourly.json.gz (dex_runner_study's
            selection, the 183 pools the floor study traded) + results/dex_filter_pools.json.gz (205 pools with an entry
            signal, incl. pools launched inside the window), deduped by net:token (the longer grid wins).  The runner
            study keeps no price paths (results/dex_runner_points.csv.gz holds labels only), so it can't be replayed.
  entry     config.DEX: 1h >= +10%, pool age >= 6h, liquidity >= $100k (and >= 50 x the planned tier-A stake, like
            dex.py's screen), vol24 >= $100k.  The buys > 1.2 x sells condition can NOT be replayed (no buy/sell counts).
  exit      config.DEX["exit"] through dex_floor_study.simulate: hold <= 14 days, no price stop, >= 2x at day 14 rides a
            40% trail, rugs / dead pools -95%; 0.3% fee + 1% slippage + price impact per side.
  account   event-driven like dex.py: $1,000 start (config.ACCOUNT_BASE), 5 slots, tier A 20% / "proven" pools 25% of
            equity (age >= 7d, liq >= $1M, vol24 >= $1M: dex.py tops these up to tier B after 2 clean re-screens), each
            capped at 0.5% of pool liquidity, cash and 100% exposure; one position per pool and per symbol, 1-day
            cooldown after an exit.  A signal the account skips (slots full) does NOT lock the pool (the earlier studies
            locked every pool for every signal whether the account took it or not).  Compounding; halves split at
            the median signal-trade entry, each half starts fresh at $1,000.
  luck      300 resampled accounts, each drops a random 30% of the signals (same drop for every variant):
            median and 10th / 90th percentile monthly return per half.
  variants  max hold 7d / 10d / 14d (runner rule kept at the limit); 5 / 8 / 10 slots (1/slots of equity, x1.25 proven).

    python dex_consolidated_study.py                  # offline, ~1-3 minutes
"""
import argparse
import random
import statistics

import dex_floor_study as FL
from dex_exit_study import DAY, HOUR, pct, portfolio, ts
from dex_filter_study import load_pools

try:
    import config
    DEXC, BASE_USD = config.DEX, float(config.ACCOUNT_BASE.get("dex", 1000.0))
    MIN_ORDER = float(getattr(config, "MIN_ORDER_USD", 10.0))
except Exception:                      # pragma: no cover
    DEXC, BASE_USD, MIN_ORDER = {}, 1000.0, 10.0

SCREEN = DEXC.get("screen") or {"min_liq": 100_000, "min_vol24": 100_000, "min_age_h": 6, "liq_x_size": 50}
ENTRY = DEXC.get("entry") or {"h1": 0.10}
TIERS = DEXC.get("tiers") or {"A": {"pct": 0.20}, "B": {"pct": 0.25, "age_d": 7, "liq": 1e6, "vol24": 1e6}}
SIZE_P = DEXC.get("size") or {"liq_pct": 0.005, "max_exposure": 1.0}
LIVE_EXIT = dict(FL.EXIT)
LIVE_SLOTS = int(DEXC.get("slots", 5))
LIVE_HOLD = LIVE_EXIT.get("max_hold_days", 14)
COOLDOWN = DAY
MONTH = 30.44 * DAY


# ----------------------------------------------------------------------------- data
def load_union(floor_path, filter_path):
    """-> ({key: Pool}, info).  The longer hourly grid wins when both caches hold a pool."""
    fpools, _, ws0, now_f = FL.load_dump(floor_path)
    gpools = load_pools(filter_path)
    out, src, same = {}, {}, 0
    for tag, pools in (("floor", fpools), ("filter", gpools)):
        for P in pools:
            k = P.key
            if k in out:
                Q = out[k]
                same += int(Q.n == P.n and Q.t0 == P.t0)
                if P.n <= Q.n:
                    src[k] += "+" + tag
                    continue
            out[k], src[k] = P, src.get(k, "") + ("+" if k in src else "") + tag
    now = max(max(P.now for P in gpools), now_f)
    for P in out.values():
        P.derive()
        P.t0_list = [P.t0 + j * HOUR for j in range(P.n)]
    info = {"floor": len(fpools), "filter": len(gpools), "union": len(out), "both": sum("+" in s for s in src.values()),
            "same_grid": same, "src": src, "now": now, "ws0_floor": ws0}
    return out, info


def proven(sig):
    B = TIERS.get("B", {})
    return sig["age"] >= B.get("age_d", 7) * 24 and sig["liq"] >= B.get("liq", 1e6) and sig["vol24"] >= B.get("vol24", 1e6)


def signals(pools, ws0, t_last):
    """Every pool-hour passing the replayable live entry (the dynamic liquidity floor is applied by the account)."""
    out = []
    for k, P in pools.items():
        for i in range(1, P.n):
            t = P.t0 + (i + 1) * HOUR
            if t < ws0 or t > t_last or P.cv[i + 1] - P.cv[max(0, i - 23)] < SCREEN.get("min_vol24", 100_000):
                continue
            f = P.features(i)
            if not f or not FL.pool_entry_ok(f):
                continue
            out.append({"t": t, "k": k, "sym": str(P.p.get("sym") or "?").upper(), "i": i, "liq": f["liq"], "age": f["age_h"],
                        "vol24": f["vol24"], "ch1": f["ch1"]})
    out.sort(key=lambda s: (s["t"], s["k"]))
    for n, s in enumerate(out):
        s["id"] = n
    return out


def outcomes(pools, sigs, hold_d):
    """Live exit with max_hold_days = hold_d for every signal -> list of (ret, exit_t, peak, rug)."""
    FL.EXIT = dict(LIVE_EXIT, max_hold_days=hold_d)
    live = {"key": "live"}
    res = []
    try:
        for s in sigs:
            P = pools[s["k"]]
            rug = P.rugset if hasattr(P, "rugset") else None
            if rug is None:
                rug = P.rugset = {j for j in range(P.n) if P.rug[j]}
            x = FL.simulate(P.t0_list, P.O, P.H, P.L, P.C, HOUR, s["i"], live, s["liq"], rug, P.dead)
            res.append((x["ret"], x["exit_t"], x["peak"], x["rug"]))
    finally:
        FL.EXIT = LIVE_EXIT
    return res


# ----------------------------------------------------------------------------- the account (dex.py rules)
def account(sigs, res, t_from, t_to, slots=LIVE_SLOTS, drop=frozenset(), start=BASE_USD, log=False):
    """Event-driven dex.py account over the signals entered in [t_from, t_to).  Proceeds come back at each exit;
    open positions at the end are valued at their simulated final exit (as the earlier studies do)."""
    scale = LIVE_SLOTS / slots                             # 8 / 10 slots: 1/slots of equity (x1.25 proven)
    pa, pb = TIERS["A"]["pct"] * scale, TIERS.get("B", TIERS["A"])["pct"] * scale
    cash, opn, cool, peak, dd, taken, skipped, log_ = start, [], {}, start, 0.0, 0, 0, []
    for s in sigs:
        t = s["t"]
        if t < t_from or t >= t_to:
            continue
        for o in [o for o in opn if o["exit"] <= t]:
            cash += o["usd"] * (1 + o["ret"])
            cool[o["k"]] = o["exit"] + COOLDOWN
            opn.remove(o)
        if s["id"] in drop:
            continue
        eq = cash + sum(o["usd"] for o in opn)
        peak, dd = max(peak, eq), min(dd, eq / peak - 1)
        if (len(opn) >= slots or any(o["k"] == s["k"] or o["sym"] == s["sym"] for o in opn) or cool.get(s["k"], 0) > t
                or s["liq"] < max(SCREEN.get("min_liq", 100_000), SCREEN.get("liq_x_size", 50) * eq * pa)):
            skipped += 1
            continue
        usd = min(eq * (pb if proven(s) else pa), s["liq"] * SIZE_P.get("liq_pct", 0.005), s["liq"] / SCREEN.get("liq_x_size", 50),
                  cash, eq * SIZE_P.get("max_exposure", 1.0) - sum(o["usd"] for o in opn))
        if usd < MIN_ORDER:
            skipped += 1
            continue
        r = res[s["id"]]
        cash -= usd
        opn.append({"k": s["k"], "sym": s["sym"], "exit": max(r[1], t), "usd": usd, "ret": r[0], "id": s["id"]})
        taken += 1
        if log:
            log_.append((s, usd, r))
    for o in opn:
        cash += o["usd"] * (1 + o["ret"])
    dd = min(dd, cash / peak - 1)
    months = max(0.5, (t_to - t_from) / MONTH)
    return {"monthly": max(cash / start, 1e-9) ** (1 / months) - 1, "final": cash, "dd": dd, "taken": taken,
            "skipped": skipped, "log": log_}


def pool_sequence(sigs, res):
    """Account-independent trade list: per pool the first signal, the next one after exit + 1-day cooldown
    (what the earlier studies called 'trades')."""
    free, out = {}, []
    for s in sigs:
        if free.get(s["k"], 0) > s["t"]:
            continue
        r = res[s["id"]]
        free[s["k"]] = r[1] + COOLDOWN
        out.append((s, r))
    return out


def trade_stats(seq):
    xs = [r[0] for _, r in seq]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": statistics.fmean(xs), "med": statistics.median(xs), "x2": sum(x >= 1.0 for x in xs) / len(xs),
            "l70": sum(x <= -0.70 for x in xs) / len(xs), "rug": sum(r[3] for _, r in seq) / len(xs),
            "mean_x1": statistics.fmean(sorted(xs)[:-1]) if len(xs) > 1 else float("nan")}


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, int(round(p * (len(xs) - 1)))))]


UNITS = {"coin-day": lambda s: (s["k"], s["t"] // DAY), "signal-hour": lambda s: s["id"]}


def resample(sigs, R, variants, halves, runs=300, keep=0.7, seed=7, unit="coin-day"):
    """Drop a random 30% of the signals and re-run the account.  unit "coin-day": all of a pool's signal hours on one
    UTC day go together (a pump fires for many hours in a row; dropping single hours barely changes which coins the
    account can buy, so the luck of catching one 40x coin survives almost every run).  "signal-hour": literal hours."""
    rng = random.Random(seed)
    key = UNITS[unit]
    units = sorted({key(s) for s in sigs}, key=str)
    out = {v: {h: [] for h in halves} for v in variants}
    for _ in range(runs):
        gone = {u for u in units if rng.random() > keep}
        drop = frozenset(s["id"] for s in sigs if key(s) in gone)
        for v, (hold, slots) in variants.items():
            for h, (a, b) in halves.items():
                out[v][h].append(account(sigs, R[hold], a, b, slots, drop)["monthly"])
    return out


# ----------------------------------------------------------------------------- reconciliation helpers
def as_study_lists(seq):
    """(trades, res) in dex_exit_study.portfolio's format (fraction-of-equity account, pool-locked trade list)."""
    return [{"t0": s["t"]} for s, _ in seq], [(r[0], r[1]) for _, r in seq]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", default="results/dex_floor_hourly.json.gz")
    ap.add_argument("--filter", default="results/dex_filter_pools.json.gz")
    ap.add_argument("--months", type=float, default=2.7)
    ap.add_argument("--runs", type=int, default=300)
    a = ap.parse_args()

    pools, info = load_union(a.floor, a.filter)
    now = info["now"]
    ws0, t_last = now - int(a.months * MONTH), now - DAY
    print(f"pools: floor dump {info['floor']}, filter dump {info['filter']} -> union {info['union']} (in both {info['both']}, "
          f"identical grids {info['same_grid']}); runner study: no price cache (labels only) - not replayable")
    print(f"entry 1h >= {ENTRY.get('h1', 0.10):+.0%}, age >= {SCREEN.get('min_age_h', 6)}h, liq >= max(${SCREEN.get('min_liq', 1e5):,.0f}, "
          f"50 x tier-A stake), vol24 >= ${SCREEN.get('min_vol24', 1e5):,.0f}; buys > {ENTRY.get('buy_ratio', 1.2)} x sells NOT replayable")
    print(f"exit {LIVE_EXIT}; costs {FL.FEE:.1%} + {FL.SLIP:.0%} + impact per side, rugs {FL.RUG_LOSS:.0%}; account ${BASE_USD:,.0f}, "
          f"{LIVE_SLOTS} slots, tiers A {TIERS['A']['pct']:.0%} / proven {TIERS.get('B', TIERS['A'])['pct']:.0%}, 0.5% of liq cap, 1-day cooldown")

    sigs = signals(pools, ws0, t_last)
    holds = sorted({7, 10, LIVE_HOLD})
    R = {h: outcomes(pools, sigs, h) for h in holds}
    seq = pool_sequence(sigs, R[LIVE_HOLD])
    T0, T1 = min(s["t"] for s in sigs), now
    split = sorted(s["t"] for s, _ in seq)[len(seq) // 2]
    halves = {"older": (T0, split), "newer": (split, T1)}
    print(f"window {ts(T0)} .. {ts(T1)}; {len(sigs)} signal hours in {len({s['k'] for s in sigs})} pools; {len(seq)} pool-sequential "
          f"trades; halves split at {ts(split)} (median trade entry); older {(split - T0) / MONTH:.2f} months, newer {(T1 - split) / MONTH:.2f}")

    FL.banner("1. LIVE RULES, ACTUAL ACCOUNT (every signal, $1,000 start per half)")
    live = {h: account(sigs, R[LIVE_HOLD], x, y, LIVE_SLOTS, log=True) for h, (x, y) in {"full": (T0, T1), **halves}.items()}
    for h, r in live.items():
        print(f"  {h:<6} monthly {pct(r['monthly'], 8)}  final ${r['final']:>9,.0f}  maxDD {pct(r['dd'], 6, 0)}  taken {r['taken']:>3}  "
              f"skipped {r['skipped']}")
    for h in ("older", "newer"):
        lg = live[h]["log"]
        contrib = sorted(((u * r[0], s["sym"], r[0], s["id"]) for s, u, r in lg), reverse=True)
        best = contrib[0]
        x, y = halves[h]
        wo = account(sigs, R[LIVE_HOLD], x, y, LIVE_SLOTS, frozenset({best[3]}))
        print(f"  {h}: trades " + ", ".join(f"{s['sym']} {pct(r[0], 1)}" for s, u, r in lg[:40])
              + ("..." if len(lg) > 40 else ""))
        print(f"  {h}: best trade {best[1]} {pct(best[2], 1)} (${best[0]:+,.0f}); without that ONE signal the half makes "
              f"{pct(wo['monthly'], 1)}/month (vs {pct(live[h]['monthly'], 1)})")

    FL.banner("2. PER-TRADE STATS (pool-sequential trades, account-independent)")
    print(f"{'max hold':<10} {'half':<6} {'n':>4} {'mean':>8} {'median':>8} {'>=2x':>6} {'<=-70%':>7} {'rug':>5} {'mean w/o best':>14}")
    for hd in holds:
        sq = pool_sequence(sigs, R[hd])
        for h, (x, y) in {"all": (T0, T1), **halves}.items():
            st = trade_stats([z for z in sq if x <= z[0]["t"] < y])
            if st["n"]:
                print(f"{str(hd) + 'd':<10} {h:<6} {st['n']:>4} {pct(st['mean'], 8)} {pct(st['med'], 8)} {st['x2']:>6.0%} {st['l70']:>7.0%} "
                      f"{st['rug']:>5.0%} {pct(st['mean_x1'], 14)}")

    variants = {f"hold {hd}d, {sl} slots": (hd, sl) for hd in holds for sl in (5, 8, 10) if hd == LIVE_HOLD or sl == LIVE_SLOTS}
    live_name = f"hold {LIVE_HOLD}d, {LIVE_SLOTS} slots"
    ACT = {}
    for name, (hd, sl) in variants.items():
        ACT[name] = (account(sigs, R[hd], *halves["older"], sl), account(sigs, R[hd], *halves["newer"], sl),
                     account(sigs, R[hd], T0, T1, sl))
    RSM = {}
    for unit in ("coin-day", "signal-hour"):
        FL.banner(f"3. VARIANTS: actual account + {a.runs} resampled accounts (each drops a random 30% of the signals, unit = {unit})")
        RSM[unit] = resample(sigs, R, variants, halves, a.runs, unit=unit)
        print(f"{'variant':<22} | {'actual older':>12} {'actual newer':>12} {'maxDD':>6} | {'older p10':>9} {'median':>8} {'p90':>8} "
              f"{'>0':>4} | {'newer p10':>9} {'median':>8} {'p90':>8} {'>0':>4}")
        for name in variants:
            ao, an, af = ACT[name]
            o, n = RSM[unit][name]["older"], RSM[unit][name]["newer"]
            print(f"{name:<22} | {pct(ao['monthly'], 12)} {pct(an['monthly'], 12)} {pct(af['dd'], 6, 0)} | {pct(q(o, .1), 9)} "
                  f"{pct(statistics.median(o), 8)} {pct(q(o, .9), 8)} {sum(x > 0 for x in o) / len(o):>4.0%} | {pct(q(n, .1), 9)} "
                  f"{pct(statistics.median(n), 8)} {pct(q(n, .9), 8)} {sum(x > 0 for x in n) / len(n):>4.0%}")
        print("(>0 = share of resampled accounts with a positive month)")

    FL.banner("4. WHY THE EARLIER STUDIES DISAGREED (their own trade lists / account models on the cached data)")
    ft, fres, _ = FL.pool_trades([p for p in pools.values() if "floor" in info["src"][p.key]], ws0, now)
    lt, lr = ft["live"], fres["live"]
    fs = sorted(t["t0"] for t in lt)[len(lt) // 2]
    fT0 = min(t["t0"] for t in lt)
    tr_all, rs_all = as_study_lists(seq)
    rows = [("floor study: 183 floor pools, pool-locked list, 5 slots", lt, lr, fT0, fs, 5),
            ("  same list, 4 slots", lt, lr, fT0, fs, 4),
            ("union pools, pool-locked list, 5 slots", tr_all, rs_all, T0, split, 5),
            ("union pools, pool-locked list, 4 slots", tr_all, rs_all, T0, split, 4)]
    for name, tr, rs, x0, sp, sl in rows:
        o, n, f = portfolio(tr, rs, x0, sp, sl), portfolio(tr, rs, sp, T1, sl), portfolio(tr, rs, x0, T1, sl)
        print(f"  {name:<58} n {len(tr):>3} | month {pct(f['monthly'], 8)} older {pct(o['monthly'], 8)} newer {pct(n['monthly'], 8)} "
              f"(split {ts(sp)[:10]})")
    seq_ids = {z[0]["id"] for z in seq}
    for h in ("older", "newer"):
        lg = live[h]["log"]
        print(f"  live account {h}: {sum(z[0]['id'] not in seq_ids for z in lg)} of {len(lg)} trades are signals the pool-locked list "
              f"never has (the pool was 'locked' by an earlier signal the account had skipped)")
    rng, key = random.Random(7), UNITS["coin-day"]
    units = sorted({key(z[0]) for z in seq}, key=str)
    pl = {"older": [], "newer": []}
    for _ in range(a.runs):
        gone = {u for u in units if rng.random() > 0.7}
        kept = [z for z in seq if key(z[0]) not in gone]
        tr, rs = as_study_lists(kept)
        pl["older"].append(portfolio(tr, rs, T0, split, LIVE_SLOTS)["monthly"])
        pl["newer"].append(portfolio(tr, rs, split, T1, LIVE_SLOTS)["monthly"])
    print(f"  union pools, pool-locked list, 5 slots, {a.runs} resampled (coin-day): median older {pct(statistics.median(pl['older']), 1)} "
          f"(p10 {pct(q(pl['older'], .1), 1)}, p90 {pct(q(pl['older'], .9), 1)}), newer {pct(statistics.median(pl['newer']), 1)} "
          f"(p10 {pct(q(pl['newer'], .1), 1)}, p90 {pct(q(pl['newer'], .9), 1)})")
    shift = [split + d * DAY for d in (-3, -1, 1, 3)]
    print("  live account, split moved by -3 / -1 / +1 / +3 days (older | newer monthly): " + "; ".join(
        f"{pct(account(sigs, R[LIVE_HOLD], T0, s_, LIVE_SLOTS)['monthly'], 1)} | {pct(account(sigs, R[LIVE_HOLD], s_, T1, LIVE_SLOTS)['monthly'], 1)}"
        for s_ in shift))

    FL.banner("5. VERDICT  (resampled medians must hold under BOTH resampling units)")
    med = lambda name, h: min(statistics.median(RSM[u][name][h]) for u in RSM)
    p10 = lambda name, h: min(q(RSM[u][name][h], .1) for u in RSM)
    Lo, Ln = med(live_name, "older"), med(live_name, "newer")
    ok = Lo > 0.05 and Ln > 0.05
    print(f"live rules: worst-unit median resampled month older {pct(Lo, 1)}, newer {pct(Ln, 1)}; worst-unit p10 older "
          f"{pct(p10(live_name, 'older'), 1)}, newer {pct(p10(live_name, 'newer'), 1)} -> "
          + ("clearly positive in both halves" if ok else "NOT clearly positive in both halves"))
    better = []
    L_ao, L_an, _ = ACT[live_name]
    for name in variants:
        if name == live_name:
            continue
        do = min(statistics.median(RSM[u][name]["older"]) - statistics.median(RSM[u][live_name]["older"]) for u in RSM)
        dn = min(statistics.median(RSM[u][name]["newer"]) - statistics.median(RSM[u][live_name]["newer"]) for u in RSM)
        ao, an, _ = ACT[name]
        clear = do >= 0.03 and dn >= 0.03 and ao["monthly"] > L_ao["monthly"] and an["monthly"] > L_an["monthly"]
        print(f"  {name:<22} median older {pct(do, 1)} pts, newer {pct(dn, 1)} pts (worst unit); actual older "
              f"{pct(ao['monthly'] - L_ao['monthly'], 1)} pts, newer {pct(an['monthly'] - L_an['monthly'], 1)} pts -> {'BETTER' if clear else 'no'}")
        if clear:
            better.append(name)
    print("clearly better in both halves (median resampled >= +3 pts, both units) AND in the actual account: " + (", ".join(better) or "none"))
    print("\nCAVEATS: pools picked from today's registry (survivorship: early rugs missing, rug rates are floors); liquidity is a "
          "constant-product estimate; hourly bars; no buys/sells filter; ~2.7 months of one market regime.")


if __name__ == "__main__":
    main()
