"""DEX ENTRY-FILTER study: would skipping "already pumped" coins (GENO-type pump-and-dumps) have helped?

Trigger (2026-09-27): the live DEX hunter lost -$167 of $213 (-78%) on GENO (solana, pump.fun) within ~1 hour.
At entry it was 6.9h old (floor 6h), liquidity $104k (floor $100k), FDV $931k, 1h +22%, 6h +258%, 24h +1830%,
buys/sells 1573/648: every floor barely cleared and the coin had already run ~18x.

Question: which extra entry filter on top of the live entry (1h >= +10%, age >= 6h, liq / vol24 >= $100k) cuts the
-70% losers / rugs and the drawdown while keeping the monthly return in BOTH halves and the big runners?

  variants  (a) skip if 6h run > +100% / +200% / +300%   (b) skip if 24h run > +500% / +1000%
            (c) min age 12h / 24h                        (d) young AND pumped combos (age < 24h AND 6h > +150% ...)
            (e) liquidity floor $150k / $250k
            A skipped coin is NOT blacklisted: the next hour that passes the entry AND the filter can still buy it
            (the live hunter re-evaluates every coin on its watch-list / scanner all day).
  data      the same GeckoTerminal hourly pool histories as dex_runner_study.py (its registry, seeded from
            dex_exit_study's), pools created >= 2 days ago (the runner study used >= 8 days: the young, outcome-blind
            pools are exactly the pump-and-dumps that matter here), the same features (ch6 / ch24 = close vs 6 / 24
            hours earlier or vs the first bar for younger pools, liquidity = the registry's constant-product estimate),
            the same live exit (config.DEX["exit"]) and costs (0.3% fee + 1% slippage + price impact per side), the
            same 4-slot compounding account (dex_exit_study.portfolio).
  legends   the legends of dex_legends_study.py with HOURLY history (Yahoo / GeckoTerminal) through the live entry
            with and without each filter: still caught? how much later / at what multiple?  (PNUT is the one legend
            the live rules caught with >= 10x left.)
  live      every PASS row of data/dex/screen.csv (the live hunter's own screen, incl. GENO) with the snapshot values
            it saw: which filters would have skipped it, and what the coin did afterwards (GeckoTerminal hourly).
  output    results/dex_filter_study.txt; results/dex_filter_pools.json.gz = the hourly grids of every pool with an
            entry signal (re-analyse offline with --offline, no network).

LIMITS: no buys / sells history (the live buys > sells condition can't be replayed), pools are picked from a registry
built by listing today's pools (rugs that died before the registry saw them are missing -> rug rates are floors),
liquidity is an estimate.  Rank the variants, don't read the absolute returns as a forecast.

    python dex_filter_study.py                    # real run (GitHub Actions)
    python dex_filter_study.py --offline          # re-analyse results/dex_filter_pools.json.gz
    python dex_filter_study.py --synthetic        # offline plumbing test (fake prices!)
"""
import argparse
import collections
import csv
import gzip
import json
import os
import random
import statistics
import sys
import time
from datetime import datetime, timezone

from dex_exit_study import DAY, HOUR, SyntheticGT, banner, boot_ci, clean, fetch_series, load_registry, pct, portfolio, ts
import dex_runner_study as RS
from dex_runner_study import AdaptiveGT, ChaosGT, Pool, hourly_grid, merge_reg

try:
    import dex_legends_study as DL
except Exception:                      # pragma: no cover
    DL = None

SCREEN, ENTRY, EXIT = RS.SCREEN, RS.ENTRY, RS.EXIT
MIN_LIQ, MIN_VOL, MIN_AGE = SCREEN.get("min_liq", 100_000), SCREEN.get("min_vol24", 100_000), SCREEN.get("min_age_h", 6)
H1 = ENTRY.get("h1", 0.10)
GT_NET = {"solana": "solana", "base": "base", "ethereum": "eth", "eth": "eth"}
NAN = float("nan")


def _gt(x, lim):
    """x > lim, unknown (None / NaN) = not proven -> False (the filter lets it through)."""
    return x is not None and x == x and x > lim


def _lt(x, lim):
    return x is not None and x == x and x < lim


# name -> (group, allow(f)); f has age_h, liq, ch6, ch24 (fractions: +1.0 = +100%); True = the entry may fire
VARIANTS = [
    ("base: live entry (1h>=+10%, age>=6h, liq/vol24>=$100k)", "base", lambda f: True),
    ("a) skip 6h > +100%", "a", lambda f: not _gt(f["ch6"], 1.0)),
    ("a) skip 6h > +200%", "a", lambda f: not _gt(f["ch6"], 2.0)),
    ("a) skip 6h > +300%", "a", lambda f: not _gt(f["ch6"], 3.0)),
    ("b) skip 24h > +500%", "b", lambda f: not _gt(f["ch24"], 5.0)),
    ("b) skip 24h > +1000%", "b", lambda f: not _gt(f["ch24"], 10.0)),
    ("c) min age 12h", "c", lambda f: not _lt(f["age_h"], 12)),
    ("c) min age 24h", "c", lambda f: not _lt(f["age_h"], 24)),
    ("d) skip age<24h & 6h>+150%", "d", lambda f: not (_lt(f["age_h"], 24) and _gt(f["ch6"], 1.5))),
    ("d) skip age<24h & 6h>+100%", "d", lambda f: not (_lt(f["age_h"], 24) and _gt(f["ch6"], 1.0))),
    ("d) skip age<24h & 6h>+200%", "d", lambda f: not (_lt(f["age_h"], 24) and _gt(f["ch6"], 2.0))),
    ("d) skip age<12h & 6h>+150%", "d", lambda f: not (_lt(f["age_h"], 12) and _gt(f["ch6"], 1.5))),
    ("d) skip age<24h & 24h>+500%", "d", lambda f: not (_lt(f["age_h"], 24) and _gt(f["ch24"], 5.0))),
    ("d) skip age<24h & 24h>+1000%", "d", lambda f: not (_lt(f["age_h"], 24) and _gt(f["ch24"], 10.0))),
    ("d) skip 6h>+200% or 24h>+1000%", "d", lambda f: not (_gt(f["ch6"], 2.0) or _gt(f["ch24"], 10.0))),
    ("e) liq floor $150k", "e", lambda f: not _lt(f["liq"], 150_000)),
    ("e) liq floor $250k", "e", lambda f: not _lt(f["liq"], 250_000)),
]
BIG = 3.0          # a "big winner" trade: >= +300% (4x) under the base rule
RUNNER_PEAK = 10.0  # a "runner": the base trade's peak after entry >= 10x


def base_entry(f):
    return f["liq"] >= MIN_LIQ and f["vol24"] >= MIN_VOL and f["age_h"] >= MIN_AGE and f["ch1"] >= H1


# ----------------------------------------------------------------------------- pool cache (offline re-analysis)
def dump_pools(path, pools):
    rows = []
    for P in pools:
        p = {k: P.p.get(k) for k in ("net", "pool", "token", "created", "sym", "ref_reserve", "ref_price", "fdv", "price_now", "first_seen")}
        rows.append({"p": p, "dead": P.dead, "now": P.now, "t0": P.t0,
                     "b": [[float(f"{x:.6g}") for x in (P.O[i], P.H[i], P.L[i], P.C[i])] + [round(P.V[i])] for i in range(P.n)]})
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with gzip.open(path, "wt") as f:
        json.dump(rows, f, separators=(",", ":"))


def load_pools(path):
    with gzip.open(path, "rt") as f:
        rows = json.load(f)
    out = []
    for r in rows:
        bars = [[r["t0"] + i * HOUR] + b for i, b in enumerate(r["b"])]
        P = Pool(r["p"], hourly_grid(bars), r["now"], r["dead"])
        P.key = f"{r['p']['net']}:{r['p']['token']}"
        out.append(P)
    return out


# ----------------------------------------------------------------------------- trading
def run_variants(pools, ws0, t_last):
    """Every variant on every pool: first hour passing base entry AND the filter; one trade per pool at a time."""
    trades = {v[0]: [] for v in VARIANTS}
    res = {v[0]: [] for v in VARIANTS}
    for P in pools:
        locked = {v[0]: 0 for v in VARIANTS}
        for i in range(1, P.n):
            t = P.t0 + (i + 1) * HOUR
            if t < ws0 or t > t_last or P.cv[i + 1] - P.cv[max(0, i - 23)] < MIN_VOL:
                continue
            f = P.features(i)
            if not f or not base_entry(f):
                continue
            for name, _, allow in VARIANTS:
                if t < locked[name] or not allow(f):
                    continue
                x = RS.simulate(P, i, f["liq"])
                locked[name] = x[1]
                trades[name].append({"t0": t, "k": P.key, "sym": P.p.get("sym", "?"), "net": P.p["net"], "liq": f["liq"],
                                     "age": f["age_h"], "ch6": f["ch6"], "ch24": f["ch24"]})
                res[name].append(x)
    return trades, res


def stats(tr, rs, T0, T1, split):
    xs = [x[0] for x in rs]
    if not xs:
        return None
    days = max(1.0, (T1 - T0) / DAY)
    srt = sorted(xs)
    return {"n": len(xs), "per_day": len(xs) / days, "win": RS.rate([x > 0 for x in xs]), "med": statistics.median(xs),
            "mean": RS.mean(xs), "ci": boot_ci(xs), "mean_x1": RS.mean(srt[:-1]) if len(srt) > 1 else NAN,
            "x2": RS.rate([x >= 1.0 for x in xs]), "l70": RS.rate([x <= -0.70 for x in xs]), "rug": RS.rate([x[4] for x in rs]),
            "n_l70": sum(x <= -0.70 for x in xs), "n_x2": sum(x >= 1.0 for x in xs),
            "full": portfolio(tr, rs, T0, T1), "old": portfolio(tr, rs, T0, split), "new": portfolio(tr, rs, split, T1),
            "n_o": sum(t["t0"] < split for t in tr), "n_n": sum(t["t0"] >= split for t in tr)}


def kept(base_tr, base_rs, tr, rs, pick):
    """Base-rule trades picked by `pick` (big winners / 10x runners): does the variant still make >= half of that
    trade's gain (or >= +300%) in the same pool?  -> (kept, total, lost symbols)."""
    by = collections.defaultdict(list)
    for t, x in zip(tr, rs):
        by[t["k"]].append(x)
    tot, ok, lost = 0, 0, []
    for t, x in zip(base_tr, base_rs):
        if not pick(x):
            continue
        tot += 1
        best = max((y[0] for y in by.get(t["k"], [])), default=-1.0)
        if best >= min(BIG, 0.5 * x[0]):
            ok += 1
        else:
            lost.append(f"{t['sym']} {pct(x[0], 1)}->{pct(best, 1) if t['k'] in by else 'skipped'}")
    return ok, tot, lost


# ----------------------------------------------------------------------------- legends (hourly series)
def ser_feats(S, i):
    """dex_legends_study.Ser bar i -> the filter features (unknown = None: filters let it through)."""
    k6, k24 = int(6 * HOUR / S.dur), int(DAY / S.dur)
    c = S.Cl[i]
    launch = (S.meta.get("coin") or {}).get("launch") or S.launch     # the real launch, not the data start
    return {"age_h": (S.T[i] + S.dur - launch) / HOUR,
            "ch6": c / S.Cl[i - k6] - 1 if k6 >= 1 and i - k6 >= 0 and S.dur <= HOUR else None,
            "ch24": c / S.Cl[max(0, i - k24)] - 1 if i >= 1 else None,
            "liq": S.liq(c) if S.liq else None}


def legend_entry(S, allow):
    """dex_legends_study.find_entry + the filter: first bar >= 6h after launch, close >= +10% over the previous
    bar, vol24 >= $100k when known, filter allows it."""
    lo = S.launch + MIN_AGE * HOUR
    for i in range(1, len(S.T)):
        if S.T[i] + S.dur < lo or S.Cl[i - 1] <= 0 or S.Cl[i] / S.Cl[i - 1] - 1 < H1:
            continue
        if S.has_vol and S.vol24(i) < MIN_VOL:
            continue
        if allow(ser_feats(S, i)):
            return i
    return None


def fetch_legends(net, gt, now, deadline, synthetic):
    out = []
    if DL is None:
        return out
    for coin in DL.COINS:
        if coin["kind"] != "legend" or time.time() > deadline:
            continue
        found, log = [], []
        srcs = (("yahoo", DL.src_yahoo, net), ("geckoterminal", DL.src_gecko, gt))
        if synthetic:
            srcs = (("cryptocompare", DL.src_cryptocompare, net),) + srcs
        for name, fn, cl in srcs:
            if time.time() > deadline:
                break
            try:
                got, why = fn(cl, coin, now)
            except Exception as ex:                                     # never die on one source
                got, why = [], f"error {type(ex).__name__}"
            found += [s for s in got if s["dur"] == HOUR]
            log.append(f"{name}: {why[:90]}")
        best = DL.pick(found, coin)
        if not best:
            print(f"  {coin['sym']:<9} no hourly history ({'; '.join(log)[:150]})")
            continue
        b = best["bars"]
        lag = (b[0][0] - coin["launch"]) / DAY
        S = DL.Ser(b, HOUR, coin["sym"], "legend", coin["name"], launch=max(coin["launch"], b[0][0]) if lag <= 3 else b[0][0],
                   now=now, src=best["src"], meta={"coin": coin, "lag": lag})
        print(f"  {coin['sym']:<9} {best['src']} hourly {DL.day(b[0][0])}..{DL.day(b[-1][0])}" + (f" (starts {lag:.0f}d after launch)" if lag > 3 else ""))
        out.append(S)
    return out


# ----------------------------------------------------------------------------- live screen rows (GENO & co)
def live_rows(path="data/dex/screen.csv"):
    try:
        with open(path) as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return []
    out = []
    for r in rows:
        if r.get("verdict") != "PASS":
            continue
        try:
            t = int(datetime.strptime(r["time"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())
            g = lambda k: float(r[k]) if r.get(k) not in (None, "") else None
            out.append({"t": t, "chain": r["chain"], "sym": r["symbol"].strip(), "addr": r["address"], "pair": r["pair"],
                        "price": g("price"), "liq": g("liq_usd"), "age_h": g("age_h"), "b1": g("buys_h1"), "s1": g("sells_h1"),
                        "ch1": g("h1"), "ch6": g("h6"), "ch24": g("h24")})
        except (ValueError, KeyError, TypeError):
            continue
    return out


def live_fires(r):
    """The live entry trigger on the screen snapshot: 1h >= +10% and buys >= 1.2 x sells (config.DEX['entry'])."""
    return (r["ch1"] or 0) >= H1 and (r["b1"] or 0) >= max(1, (r["s1"] or 0) * ENTRY.get("buy_ratio", 1.2))


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--chaos", action="store_true")
    ap.add_argument("--offline", action="store_true", help="re-analyse --cache instead of fetching")
    ap.add_argument("--budget-min", type=float, default=285, help="stop fetching pools after this many minutes (from the start)")
    ap.add_argument("--legend-min", type=float, default=25)
    ap.add_argument("--months", type=float, default=2.7)
    ap.add_argument("--hourly-pages", type=int, default=2)
    ap.add_argument("--max-pools", type=int, default=1500)
    ap.add_argument("--min-age-d", type=float, default=2.0, help="pools must be at least this old")
    ap.add_argument("--cache", default="results/dex_filter_pools.json.gz")
    a = ap.parse_args()
    t_start = time.time()
    print(f"live entry: 1h >= {H1:+.0%}, age >= {MIN_AGE}h, liq >= ${MIN_LIQ:,.0f}, vol24 >= ${MIN_VOL:,.0f} (buys > sells not replayable)")
    print(f"live exit (config.DEX['exit']): {EXIT}")

    legends, live_ser = [], {}
    if a.offline:
        pools = load_pools(a.cache)
        now = max(P.now for P in pools)
        print(f"OFFLINE: {len(pools)} pools from {a.cache}")
    else:
        if a.synthetic:
            print("SYNTHETIC MODE: fake prices, only checks that the study runs end to end" + (" (chaos on)" if a.chaos else ""))
            sg = SyntheticGT(per_net=40)
            cl, now = (ChaosGT(sg) if a.chaos else sg), sg.now
            reg = merge_reg({}, [dict(r, first_seen=r["seen"]) for r in sg.seed_registry()], now)
            net = DL.FakeNet(a.chaos) if DL else None
        else:
            cl, now = AdaptiveGT(), int(time.time())
            reg = load_registry("results/dex_runner_pools.json")
            for k, e in load_registry("results/dex_exit_pools.json").items():
                reg.setdefault(k, dict(e, first_seen=e.get("first_seen") or e.get("seen", now)))
            net = DL.Net(time.time() + a.legend_min * 60) if DL else None

        banner("1. LEGENDS WITH HOURLY HISTORY (Yahoo keeps ~730 days of hourly bars; GeckoTerminal only recent pools)")
        legends = fetch_legends(net, DL.Until(cl, time.time() + a.legend_min * 60) if DL else cl, now,
                                time.time() + a.legend_min * 60, a.synthetic)

        banner("2. LIVE SCREEN PASSES (data/dex/screen.csv) - hourly history after the snapshot")
        lr = [] if a.synthetic else live_rows()
        for key in sorted({(r["chain"], r["pair"]) for r in lr}):
            if key[0] not in GT_NET or not key[1]:
                continue
            t_first = min(r["t"] for r in lr if (r["chain"], r["pair"]) == key)
            bars, _ = fetch_series(cl, {"net": GT_NET[key[0]], "pool": key[1]}, "hour", 1, t_first - 2 * DAY, now + HOUR, 1)
            if bars:
                live_ser[key] = clean(bars)
        print(f"{len(lr)} PASS rows, {len({(r['chain'], r['pair']) for r in lr})} coins, hourly history for {len(live_ser)}")

        banner("3. POOLS (dex_runner_study registry; hourly GeckoTerminal history)")
        ws0 = now - int(a.months * 30.44 * DAY)
        cand = [p for p in reg.values() if p.get("pool") and p.get("ref_reserve", 0) >= 15_000
                and p.get("created", 0) <= now - a.min_age_d * DAY]
        rng = random.Random(42)
        rng.shuffle(cand)
        blind = lambda p: p.get("first_seen", now) <= p["created"] + 2 * DAY or "new" in p.get("srcs", [])
        young = lambda p: p["created"] >= ws0                 # launched inside the window: its whole life is studied
        cand.sort(key=lambda p: (not blind(p), not young(p), -p.get("ref_reserve", 0)))
        cand = cand[:a.max_pools]
        print(f"{len(cand)} candidate pools (>= {a.min_age_d:g} days old, >= $15k reserve ever seen; {sum(blind(p) for p in cand)} outcome-blind "
              f"and {sum(young(p) for p in cand)} launched inside the window, fetched first); window from {ts(ws0)}")
        pools, why = [], collections.Counter()
        for n, p in enumerate(cand):
            if time.time() - t_start > a.budget_min * 60:
                why["budget"] += len(cand) - n
                break
            try:
                hourly, complete = fetch_series(cl, p, "hour", 1, max(p["created"], ws0), now, a.hourly_pages)
            except Exception:                                   # never die on one pool
                hourly, complete = [], False
                why["error"] += 1
            if len(hourly) < 30:
                why["no data"] += 1
                continue
            grid = hourly_grid(clean(hourly))
            if not grid:
                why["short"] += 1
                continue
            dead = complete and now - (hourly[-1][0] + HOUR) > RS.DEAD_H * HOUR
            P = Pool(p, grid, now, dead)
            P.key = f"{p['net']}:{p['token']}"
            pools.append(P)
            if n % 100 == 0:
                print(f"  fetched {n + 1}/{len(cand)}  calls {cl.calls}  429s {cl.r429}  gap {getattr(cl, 'gap', 0):.1f}s  pools {len(pools)}"
                      f"  {time.time() - t_start:.0f}s")
                sys.stdout.flush()
        print(f"API calls {cl.calls} (429s {cl.r429}); pools with usable history {len(pools)}; skipped: "
              + ", ".join(f"{k} {v}" for k, v in why.items()) + f"; {time.time() - t_start:.0f}s")

    if len(pools) < 5:
        print("\ntoo few pools with history - check API reachability above")
        return
    for P in pools:
        P.derive()
    ws0 = now - int(a.months * 30.44 * DAY)
    t_last = now - DAY
    trades, res = run_variants(pools, ws0, t_last)
    if not a.offline and not a.synthetic:
        keys = {t["k"] for v in trades.values() for t in v}
        try:
            dump_pools(a.cache, [P for P in pools if P.key in keys])
            print(f"wrote {len(keys)} pools with an entry signal to {a.cache}")
        except Exception as e:                                   # pragma: no cover
            print(f"could not write {a.cache}: {e}")

    base = VARIANTS[0][0]
    bt, br = trades[base], res[base]
    if not bt:
        print("\nthe live entry never fired in this sample")
        return
    T0, T1 = min(min((t["t0"] for t in v), default=now) for v in trades.values()), now
    split = sorted(t["t0"] for t in bt)[len(bt) // 2]

    banner(f"4. ENTRY FILTERS THROUGH THE LIVE EXIT  ({len(pools)} pools, {ts(T0)[:10]}..{ts(t_last)[:10]}, halves split at {ts(split)[:16]}; "
           f"costs {RS.FEE:.1%} fee + {RS.SLIP:.0%} slippage + impact per side)")
    print(f"{'variant':<56} {'n':>4} {'/day':>5} {'win':>4} {'median':>7} {'mean':>7} {'mean-top1':>9} {'>=2x':>5} {'<=-70%':>6} {'rug':>4} | "
          f"{'month':>8} {'older':>8} {'newer':>8} {'maxDD':>6} | {'big kept':>8} {'10x kept':>8}")
    ST = {}
    for name, grp, _ in VARIANTS:
        s = ST[name] = stats(trades[name], res[name], T0, T1, split)
        if not s:
            print(f"{name:<56} {0:>4}")
            continue
        s["big"] = kept(bt, br, trades[name], res[name], lambda x: x[0] >= BIG)
        s["run"] = kept(bt, br, trades[name], res[name], lambda x: x[2] >= RUNNER_PEAK)
        print(f"{name:<56} {s['n']:>4} {s['per_day']:>5.2f} {s['win']:>4.0%} {pct(s['med'], 7)} {pct(s['mean'], 7)} {pct(s['mean_x1'], 9)} "
              f"{s['x2']:>5.0%} {s['l70']:>6.0%} {s['rug']:>4.0%} | {pct(s['full']['monthly'], 8)} {pct(s['old']['monthly'], 8)} "
              f"{pct(s['new']['monthly'], 8)} {pct(s['full']['dd'], 6, 0)} | {s['big'][0]:>3}/{s['big'][1]:<4} {s['run'][0]:>3}/{s['run'][1]:<4}")
    print(f"(month = compounding {4}-slot account, 1/4 of equity per trade; older / newer = trades before / after the split; "
          f"mean-top1 = mean without the single best trade; <=-70% = trades that lost 70% or more; rug = the pool rugged "
          f"(-95%); big kept = base trades >= +{BIG:.0%} still made >= half their gain (or >= +{BIG:.0%}); 10x kept = same for base "
          f"trades whose peak reached {RUNNER_PEAK:g}x)")
    for name, _, _ in VARIANTS[1:]:
        s = ST[name]
        if s and (s["big"][2] or s["run"][2]):
            print(f"  lost by '{name}': " + ", ".join(sorted(set(s["big"][2] + s["run"][2]))[:8]))

    banner("5. THE BASE RULE'S WORST AND BEST TRADES AND WHAT THEY LOOKED LIKE AT ENTRY")
    z = sorted(zip(bt, br), key=lambda q: q[1][0])
    for lab, grp in (("worst", z[:12]), ("best", z[::-1][:12])):
        print(f"{lab}:")
        for t, x in grp:
            blocked = [n for n, _, al in VARIANTS[1:] if not al({"age_h": t["age"], "ch6": t["ch6"], "ch24": t["ch24"], "liq": t["liq"]})]
            print(f"  {t['sym']:<12} {t['net']:<7} {ts(t['t0'])[:16]}  {pct(x[0], 8)} peak {x[2]:>6.1f}x  age {t['age']:>6.0f}h  "
                  f"6h {pct(t['ch6'], 8)}  24h {pct(t['ch24'], 8)}  liq ${t['liq'] / 1000:>6.0f}k  skipped by {len(blocked)} of {len(VARIANTS) - 1}")
    young = [(t, x) for t, x in zip(bt, br) if t["age"] < 24]
    pumped = [(t, x) for t, x in young if (t["ch6"] or 0) > 1.5]
    for lab, g in (("all base trades", list(zip(bt, br))), ("age < 24h", young), ("age < 24h and 6h > +150% (GENO-type)", pumped)):
        if g:
            xs = [x[0] for _, x in g]
            print(f"  {lab:<40} n {len(g):>4}  mean {pct(RS.mean(xs), 7)}  median {pct(statistics.median(xs), 7)}  "
                  f">=2x {RS.rate([v >= 1 for v in xs]):>4.0%}  <=-70% {RS.rate([v <= -0.7 for v in xs]):>4.0%}")

    banner("6. LEGENDS: still caught with each filter?  (live entry + live exit, $100 stake, hourly data only)")
    if not legends:
        print("no legend with hourly history" + (" (offline run: legends need the network)" if a.offline else ""))
    leg_ok = {}
    for S in legends:
        i0 = legend_entry(S, VARIANTS[0][2])
        if i0 is None:
            print(f"{S.key:<9} live entry never fires in the data")
            continue
        r0 = DL.simulate(S, i0, DL.LIVE_RULE)
        f0 = ser_feats(S, i0)
        print(f"{S.key:<9} live entry {DL.day(S.T[i0])} age {f0['age_h']:.0f}h 6h {pct(f0['ch6'] if f0['ch6'] is not None else NAN, 1)} "
              f"24h {pct(f0['ch24'] if f0['ch24'] is not None else NAN, 1)} -> {r0['ret'] + 1:.1f}x of stake (peak {r0['peak']:.1f}x)"
              + ("   [data starts after launch: age filters can't be judged]" if S.meta.get("lag", 0) > 3 else ""))
        for name, _, allow in VARIANTS[1:]:
            j = legend_entry(S, allow)
            if j == i0:
                leg_ok.setdefault(name, []).append((S.key, True))
                continue
            r = DL.simulate(S, j, DL.LIVE_RULE) if j is not None else None
            good = bool(r) and r["ret"] >= 0.5 * r0["ret"]
            leg_ok.setdefault(name, []).append((S.key, good))
            print(f"    {name:<34} " + (f"entry {DL.day(S.T[j])} ({(S.T[j] - S.T[i0]) / HOUR:.0f}h later, at {S.Cl[j] / S.Cl[i0]:.1f}x the live entry) "
                                         f"-> {r['ret'] + 1:.1f}x of stake" if r else "NEVER enters") + ("" if good else "   <- LOST"))

    banner("7. LIVE SCREEN PASSES (the hunter's own snapshots): which filter skips which coin, and what happened next")
    lr = [] if a.offline or a.synthetic else live_rows()
    GENO = {"t": 0, "chain": "solana", "sym": "GENO", "addr": "6XBj4xjqJeF7R4aqfrSdyyx6TUHgKEjUkCttmoECpump", "pair": "", "age_h": 6.9,
            "liq": 104_465, "ch1": 0.2176, "ch6": 2.58, "ch24": 18.3, "b1": 1573, "s1": 648, "price": None}
    if not any(r["sym"] == "GENO" for r in lr):
        lr.append(GENO)
    fired = [r for r in lr if live_fires(r)]
    print(f"{len(lr)} PASS rows, {len(fired)} where the live entry trigger was on (1h >= +10%, buys >= 1.2x sells)")
    print(f"{'time':<17} {'coin':<11} {'age h':>6} {'liq':>7} {'1h':>6} {'6h':>7} {'24h':>8} | {'max after':>9} {'min after':>9} {'last':>7} | skipped by")
    for r in sorted(fired, key=lambda r: r["t"]):
        bars = live_ser.get((r["chain"], r["pair"])) or []
        after = [b for b in bars if b[0] >= r["t"]]
        e = r["price"]
        mx = max(b[2] for b in after) / e - 1 if after and e else NAN
        mn = min(b[3] for b in after) / e - 1 if after and e else NAN
        la = after[-1][4] / e - 1 if after and e else NAN
        sk = [n.split(" ", 1)[1] if " " in n else n for n, _, al in VARIANTS[1:] if not al(r)]
        nz = lambda v: NAN if v is None else v
        print(f"{ts(r['t'])[:16] if r['t'] else 'live 09-27 09:39':<17} {r['sym'][:11]:<11} {r['age_h'] or 0:>6.1f} {(r['liq'] or 0) / 1000:>6.0f}k "
              f"{pct(nz(r['ch1']), 6, 0)} {pct(nz(r['ch6']), 7, 0)} {pct(nz(r['ch24']), 8, 0)} | {pct(mx, 9, 0)} {pct(mn, 9, 0)} {pct(la, 7, 0)} | "
              + (", ".join(sk) if sk else "-"))

    banner("8. VERDICT PER FILTER  (pass = fewer <=-70% losers AND no deeper drawdown AND monthly about equal or better in BOTH "
           "halves AND no big winner / 10x runner / legend lost)")
    b = ST[base]
    tol = lambda x: x - max(0.05, 0.10 * abs(x))          # "about equal": within 5 points or 10% of the base month
    winners = []
    for name, _, _ in VARIANTS[1:]:
        s = ST[name]
        if not s:
            print(f"  {name:<34} no trades")
            continue
        checks = {"fewer -70% losers": s["l70"] < b["l70"] and s["n_l70"] < b["n_l70"],
                  "drawdown no deeper": s["full"]["dd"] >= b["full"]["dd"] - 0.01,
                  "older half ~equal+": s["old"]["monthly"] >= tol(b["old"]["monthly"]),
                  "newer half ~equal+": s["new"]["monthly"] >= tol(b["new"]["monthly"]),
                  "big winners kept": s["big"][0] >= s["big"][1],
                  "10x runners kept": s["run"][0] >= s["run"][1],
                  "legends kept": all(ok for _, ok in leg_ok.get(name, []))}
        ok = all(checks.values())
        if ok:
            winners.append(name)
        print(f"  {name:<34} {'PASS' if ok else 'fail'}   " + ", ".join(("" if v else "NOT ") + k for k, v in checks.items()))
    banner("9. SUMMARY IN PLAIN WORDS")
    print(f"Base (live entry): {b['n']} trades, mean {pct(b['mean'], 1)}, median {pct(b['med'], 1)}, >=2x {b['x2']:.0%}, <=-70% {b['l70']:.0%}, "
          f"rug {b['rug']:.0%}; account {pct(b['full']['monthly'], 1)}/month (older {pct(b['old']['monthly'], 1)}, newer "
          f"{pct(b['new']['monthly'], 1)}), max drawdown {pct(b['full']['dd'], 1, 0)}.")
    if winners:
        best = max(winners, key=lambda n: min(ST[n]["old"]["monthly"], ST[n]["new"]["monthly"]))
        s = ST[best]
        print(f"Filters that passed every check: {', '.join(winners)}.  Best of them (best worse half): '{best}': {s['n']} trades, "
              f"<=-70% {s['l70']:.0%}, account {pct(s['full']['monthly'], 1)}/month (older {pct(s['old']['monthly'], 1)}, newer "
              f"{pct(s['new']['monthly'], 1)}), max drawdown {pct(s['full']['dd'], 1, 0)}.  RECOMMEND applying it (tightening only).")
    else:
        print("No filter passed every check: skipping 'already pumped' coins did not cut the -70% losers and drawdown without "
              "costing return in one of the halves or losing big winners. RECOMMEND no change.")
    print(f"({time.time() - t_start:.0f}s)")


if __name__ == "__main__":
    main()
