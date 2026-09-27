"""DEX PROFIT-FLOOR study: should a coin that is already up big early get a floor, so a TEXTIT round trip
(bought 0.021237 on 2026-09-27 08:55, +104% within ~2h, back to +6%, -24% at one point) can't happen?

Owner's NEXT item in results/research_log.md ("Profit floor below 2x (TEXTIT...)").  The live exit
(config.DEX["exit"]): hold up to 14 days, no price stop (95% trail), a coin >= 2x at day 14 rides a 40% trail.
The exit / legends studies removed a protection trail because it cut the big runners; these floors only arm
after a big early gain:

  live   the current rule
  a      once the peak is >= +50%: floor at break-even (entry + fees + slippage, like dex.py's post-tp1 stop)
  b      once the peak is >= +75%: floor at +25%
  c      once the peak is >= +100%: the 40% runner trail from the peak (armed early instead of at day 14)
  d      once the peak is >= +100%: floor at +50%; once >= 3x: 50% trail from the peak
  e      sell half at +100% (stake back); the rest keeps the current rule (clock + runner at day 14)
  e_dex  e the way dex.py's tp1 flag would run it: the rest is never put on the clock, stop at break-even

  1. legends  every famous coin of dex_legends_study.py (same free sources, hourly preferred; the cached daily
              bars in results/dex_legends_daily.json.gz when a coin can't be fetched) through the live entry
              AND a "caught early" entry (first +10% bar after launch, volume ignored: PEPE / SHIB style legends
              the live entry never fired on): does each variant still ride them to their big multiples?
  2. pools    dex_runner_study.py's pool sample (registry, hourly GeckoTerminal history, 2.7 months) through
              the engine's entry (1h >= +10%, age >= 6h, liq >= $100k, vol24 >= $100k; one trade per pool at a
              time, 1-day cooldown after an exit like dex.py) and each exit variant; costs 0.3% fee + 1% slippage
              + price impact per side, rugs -95%; a compounding account with config.DEX["slots"] slots.
              Monthly return (full / older half / newer half = out-of-sample), max drawdown, 2x-rate, average
              winner, how many trades peaked >= +50% and still closed at a loss (the TEXTIT shape).
  3. verdict  a variant is only worth applying if its monthly return beats or matches the current rule in
              BOTH halves and no legend loses its big multiple (keeps >= 80% of the current rule's multiple).

    python dex_floor_study.py                         # real run (GitHub Actions)
    python dex_floor_study.py --synthetic             # offline plumbing test (fake prices!)
    python dex_floor_study.py --from-dump FILE        # re-analyse the committed hourly dump, no network
"""
import argparse
import collections
import gzip
import json
import math
import os
import random
import statistics
import sys
import time

import dex_legends_study as LG
from dex_exit_study import DAY, FEE, HOUR, SLIP, SIZE, SyntheticGT, banner, clean, fetch_series, load_registry, mean, pct, portfolio, ts
from dex_runner_study import DEAD_H, HORIZON_D, RUG_LOSS, AdaptiveGT, ChaosGT, Pool, hourly_grid, merge_reg

try:
    import config
    DEXC = config.DEX
except Exception:                      # pragma: no cover
    DEXC = {}

EXIT = DEXC.get("exit") or {"trail": 0.95, "trail_steps": [], "max_hold_days": 14, "runner_at_limit": (1.0, 0.40)}
SCREEN = DEXC.get("screen") or {"min_liq": 100_000, "min_vol24": 100_000, "min_age_h": 6}
ENTRY = DEXC.get("entry") or {"h1": 0.10}
SLOTS = int(DEXC.get("slots", 5))
BE = 1 + SLIP + 2 * FEE                # dex.py's break-even: entry x (1 + slip + 2 fees)
COOLDOWN = DAY                         # dex.py: pf.cooldown = now + DAY after a full exit
KEEP_LEGEND = 0.80                     # a legend "keeps its big multiple" if a variant gets >= 80% of the live multiple
BIG = 5.0                              # legends checked: live multiple >= 5x (on either entry)

VARIANTS = [
    {"key": "live", "name": "current: hold 14d, no stop; >=2x at day 14 -> 40% trail"},
    {"key": "a", "name": "a) peak>=+50% -> floor at break-even", "floors": [(1.5, BE)]},
    {"key": "b", "name": "b) peak>=+75% -> floor at +25%", "floors": [(1.75, 1.25)]},
    {"key": "c", "name": "c) peak>=+100% -> 40% trail from peak", "trails": [(2.0, 0.40)]},
    {"key": "d", "name": "d) peak>=+100% -> floor +50%; 3x -> 50% trail", "floors": [(2.0, 1.5)], "trails": [(3.0, 0.50)]},
    {"key": "e", "name": "e) sell half at +100%, rest current rule", "tp": (2.0, 0.5)},
    {"key": "e_dex", "name": "e') half at +100% as dex.py tp1 (no clock, BE stop)", "tp": (2.0, 0.5), "tp_free": True},
]


# ----------------------------------------------------------------------------- the exit (dex.py _manage + variant)
def simulate(T, O, H, L, C, dur, i0, v, liq0=None, rug=(), dead=False, horizon_d=HORIZON_D, stake=SIZE, log=False):
    """Entry at the close of bar i0; the live exit from config.DEX['exit'] plus the variant's floors / trails /
    half-sale.  Per bar: rug -> clock (at the open) -> stop (gaps fill at the open) -> take-profit -> peak / stop
    update, so a floor armed in one bar protects from the next bar on (hourly: from the next hour).
    liq0: pool liquidity at entry (price impact ~ usd / liquidity, liquidity ~ sqrt(price)); None = no impact.
    -> dict(ret, exit_t, peak (x entry), open, rug, runner, sells[(t, px, x entry, share of what was left, why)])."""
    e = C[i0]
    X = EXIT

    def cost(usd, px):
        lq = liq0 * math.sqrt(px / e) if liq0 else None
        return min(1.0, FEE + SLIP + (usd / lq if lq else 0.0))

    q = stake * (1 - cost(stake, e)) / e
    cash, peak, trail0 = 0.0, e, X.get("trail", 0.95)
    stop, runner, took = e * (1 - trail0), False, False
    R = X.get("runner_at_limit") or (1.0, 0.40)
    t_in = T[i0] + dur
    limit, end_t = t_in + X.get("max_hold_days", 14) * DAY, t_in + horizon_d * DAY
    sells = []
    st = {"q": q, "cash": cash}

    def sell(qty, px, t, why):
        qty = min(st["q"], qty)
        if qty <= 0:
            return
        usd = qty * px
        st["cash"] += usd * (1 - cost(usd, px))
        if log:
            sells.append((t, px, px / e, qty / st["q"], why))
        st["q"] -= qty

    def done(t, is_open=False, rugged=False):
        val = st["cash"]
        if is_open and st["q"] > 0:
            usd = st["q"] * C[-1]
            val += usd * (1 - cost(usd, C[-1]))
        return {"ret": val / stake - 1, "exit_t": t, "peak": peak / e, "open": is_open and st["q"] > 0, "rug": rugged,
                "runner": runner, "sells": sells}

    def wipe(t, why):
        if log:
            sells.append((t, e * (1 + RUG_LOSS), 1 + RUG_LOSS, 1.0, why))
        st["cash"] += st["q"] * e * (1 + RUG_LOSS)
        st["q"] = 0.0

    for j in range(i0 + 1, len(T)):
        t, o, h, l, c = T[j], O[j], H[j], L[j], C[j]
        if j in rug:                                          # rug / dead pool: the rest is worth -95%
            wipe(t, "rug")
            return done(t + dur, rugged=True)
        if not runner and not (took and v.get("tp_free")) and t >= limit:
            if o >= e * (1 + R[0]):                           # never sell a runner on the clock (owner rule)
                runner = True
            else:
                sell(st["q"], o, t, "time limit")
                return done(t)
        if l <= stop:
            why = "runner trail" if runner else "floor/trail" if v.get("floors") or v.get("trails") or took else "95% trail"
            sell(st["q"], min(o, stop), t, why)
            return done(t + dur)
        tp = v.get("tp")
        if tp and not took and h >= e * tp[0]:
            sell(st["q"] * tp[1], max(o, e * tp[0]), t, f"sell {tp[1]:.0%} at {tp[0]:g}x")
            took = True
            if v.get("tp_free"):
                stop = max(stop, e * BE)
        peak = max(peak, h)
        tr = trail0
        for m, w in X.get("trail_steps", []):
            if peak >= e * m:
                tr = w
        for m, w in v.get("trails", ()):
            if peak >= e * m:
                tr = min(tr, w)
        if runner:
            tr = min(tr, R[1])
        stop = max(stop, peak * (1 - tr))
        for m, f in v.get("floors", ()):
            if peak >= e * m:
                stop = max(stop, e * f)
        if t + dur >= end_t:
            sell(st["q"], c, t, "horizon")
            return done(t + dur)
        if st["q"] <= 1e-15:
            return done(t + dur)
    if dead and st["q"] > 0:                                  # history ended for good: -95% on the rest
        wipe(T[-1] + dur, "dead")
        return done(T[-1] + dur, rugged=True)
    return done(T[-1] + dur, True)


# ----------------------------------------------------------------------------- legends
def first_pop(S):
    """'Caught early': the first bar >= 6h after launch closing >= +10% over the previous close, volume ignored."""
    lo = S.launch + LG.MIN_AGE_H * HOUR
    for i in range(1, len(S.T)):
        if S.T[i] + S.dur >= lo and S.Cl[i - 1] > 0 and S.Cl[i] / S.Cl[i - 1] - 1 >= LG.H1:
            return i
    return None


def load_cache(path):
    try:
        with gzip.open(path, "rt") as f:
            return json.load(f)
    except Exception:
        return {}


def fetch_legends(net, gt, now, deadline, cache, offline=False):
    """dex_legends_study's per-coin source probing (hourly preferred); cached daily bars as the fallback."""
    out = []
    for coin in LG.COINS:
        found = []
        if not offline:
            for name, fn, cl in (("cryptocompare", LG.src_cryptocompare, net), ("yahoo", LG.src_yahoo, net),
                                 ("coingecko", LG.src_coingecko, net), ("coinmarketcap", LG.src_cmc, net),
                                 ("geckoterminal", LG.src_gecko, gt)):
                if time.time() > deadline:
                    break
                if name == "geckoterminal" and any(s["dur"] == HOUR and s["bars"][0][0] <= coin["launch"] + 3 * DAY for s in found):
                    continue
                try:
                    got, _ = fn(cl, coin, now)
                except Exception:
                    got = []
                found += got
        best = LG.pick(found, coin)
        if not best and coin["sym"] in cache:
            c = cache[coin["sym"]]
            best = {"src": c["src"] + " (cached daily)", "dur": DAY, "bars": c["bars"]}
        if not best:
            print(f"  {coin['sym']:<9} no price history")
            continue
        b = best["bars"]
        lag = (b[0][0] - coin["launch"]) / DAY
        S = LG.Ser(b, best["dur"], coin["sym"], coin["kind"], coin["name"], launch=max(coin["launch"], b[0][0]) if lag <= 3 else b[0][0],
                   now=now, src=best["src"], meta={"coin": coin, "lag": lag})
        print(f"  {coin['sym']:<9} {coin['kind']:<8} {best['src']} ({'hourly' if best['dur'] == HOUR else 'daily'}) "
              f"{LG.day(b[0][0])}..{LG.day(b[-1][0])}, {len(b)} bars" + (f"; starts {lag:.0f}d after launch" if lag > 3 else ""))
        out.append(S)
    return out


def legend_trades(series):
    """[(label, Ser, i0)]: the live entry (+ the late entry for LUNA / FTT) and the 'caught early' entry."""
    tr = []
    for S in series:
        i0 = LG.find_entry(S)
        if i0 is not None:
            tr.append((f"{S.key} live entry", S, i0))
        late = S.meta["coin"].get("late")
        if late:
            j = LG.find_entry(S, after=late)
            if j is not None:
                tr.append((f"{S.key} late entry", S, j))
        k = first_pop(S)
        if k is not None and k != i0:
            tr.append((f"{S.key} caught early", S, k))
    return tr


def run_legends(series):
    banner("1. LEGENDS / COLLAPSES / RUGS  (x = multiple of the stake at the final exit; stake $100, no price impact)")
    tr = legend_trades(series)
    keys = [v["key"] for v in VARIANTS]
    print(f"{'coin / entry':<28} {'src':<6} {'entry':>10} {'peak':>7} " + " ".join(f"{k:>7}" for k in keys))
    res = {}
    for label, S, i0 in tr:
        rs = {v["key"]: simulate(S.T, S.O, S.H, S.L, S.Cl, S.dur, i0, v, None, S.rug, S.dead_end, LG.HORIZON_D, 100.0, True) for v in VARIANTS}
        res[label] = (S, i0, rs)
        print(f"{label:<28} {'hour' if S.dur == HOUR else 'day':<6} {LG.day(S.T[i0] + S.dur):>10} {rs['live']['peak']:>6.1f}x "
              + " ".join(f"{1 + rs[k]['ret']:>6.1f}x" for k in keys))
    print("\nwhere each variant sold the big ones (x entry price, date, why):")
    big = [lb for lb, (S, i0, rs) in res.items() if 1 + rs["live"]["ret"] >= BIG or rs["live"]["peak"] >= 10]
    for lb in big:
        S, i0, rs = res[lb]
        print(f"  {lb}")
        for k in keys:
            s = rs[k]["sells"]
            print(f"    {k:<6} {1 + rs[k]['ret']:>6.1f}x  " + "; ".join(f"{x[3]:.0%} at {x[2]:.1f}x {LG.day(x[0])} ({x[4]})" for x in s[:4])
                  + (" (still open)" if rs[k]["open"] else ""))
    ok = {}
    for v in VARIANTS:
        lost = [lb for lb in big if 1 + res[lb][2]["live"]["ret"] >= BIG
                and 1 + res[lb][2][v["key"]]["ret"] < KEEP_LEGEND * (1 + res[lb][2]["live"]["ret"])]
        ok[v["key"]] = lost
    print("\nlegends that lose their big multiple (< 80% of the live multiple, where live >= 5x):")
    for v in VARIANTS[1:]:
        print(f"  {v['name']:<52} {'none' if not ok[v['key']] else ', '.join(ok[v['key']])}")
    return res, ok


# ----------------------------------------------------------------------------- pools
def pool_entry_ok(f):
    return (f["liq"] >= SCREEN.get("min_liq", 100_000) and f["vol24"] >= SCREEN.get("min_vol24", 100_000)
            and f["age_h"] >= SCREEN.get("min_age_h", 6) and f["ch1"] >= ENTRY.get("h1", 0.10))


def pool_trades(pools, ws0, now):
    """Engine entry through every variant; one trade per pool at a time + 1-day cooldown (per variant)."""
    trades = {v["key"]: [] for v in VARIANTS}
    res = {v["key"]: [] for v in VARIANTS}
    used = set()
    for P in pools:
        rug = {j for j in range(P.n) if P.rug[j]}
        locked = {v["key"]: 0 for v in VARIANTS}
        for i in range(1, P.n):
            t = P.t0 + (i + 1) * HOUR
            if t < ws0 or t > now - DAY or P.cv[i + 1] - P.cv[max(0, i - 23)] < SCREEN.get("min_vol24", 100_000):
                continue
            if all(t < locked[k] for k in locked):
                continue
            f = P.features(i)
            if not f or not pool_entry_ok(f):
                continue
            for v in VARIANTS:
                k = v["key"]
                if t < locked[k]:
                    continue
                x = simulate(P.t0_list, P.O, P.H, P.L, P.C, HOUR, i, v, f["liq"], rug, P.dead)
                locked[k] = x["exit_t"] + COOLDOWN
                trades[k].append({"t0": t, "k": P.key, "sym": P.p.get("sym", "?"), "net": P.p.get("net", "?")})
                res[k].append((x["ret"], x["exit_t"], x["peak"], x["open"], x["rug"]))
                used.add(P.key)
    return trades, res, used


def stats(tr, rs, T0, T1, split):
    xs = [r[0] for r in rs]
    if not xs:
        return None
    wins = [x for x in xs if x > 0]
    return {"n": len(xs), "mean": mean(xs), "med": statistics.median(xs), "win": len(wins) / len(xs),
            "x2": sum(x >= 1.0 for x in xs) / len(xs), "avgwin": mean(wins) if wins else float("nan"),
            "gaveback": sum(1 for r in rs if r[2] >= 1.5 and r[0] < 0), "p50": sum(1 for r in rs if r[2] >= 1.5),
            "full": portfolio(tr, rs, T0, T1, SLOTS), "old": portfolio(tr, rs, T0, split, SLOTS),
            "new": portfolio(tr, rs, split, T1, SLOTS)}


def run_pools(pools, ws0, now):
    banner(f"2. POOLS: the engine's entry through each exit variant  ({len(pools)} pools; costs {FEE:.1%} + {SLIP:.0%} + impact per side, "
           f"rug -95%; {SLOTS}-slot compounding account, 1/{SLOTS} of equity per trade)")
    for P in pools:
        P.derive()
        P.t0_list = [P.t0 + j * HOUR for j in range(P.n)]
    trades, res, used = pool_trades(pools, ws0, now)
    live_t = sorted(t["t0"] for t in trades["live"])
    if len(live_t) < 10:
        print(f"only {len(live_t)} engine trades - too few")
        return None, used
    T0, T1 = min(min((t["t0"] for t in trades[k]), default=now) for k in trades), now
    split = live_t[len(live_t) // 2]
    print(f"window {ts(T0)} .. {ts(T1)}; older half < {ts(split)} <= newer half (split = median live-rule entry)\n")
    print(f"{'exit variant':<52} {'n':>4} {'mean':>7} {'median':>7} {'win':>4} {'>=2x':>5} {'avg win':>8} {'TEXTIT':>7} | "
          f"{'month':>7} {'older':>7} {'newer':>7} {'maxDD':>6}")
    ST = {}
    for v in VARIANTS:
        k = v["key"]
        s = ST[k] = stats(trades[k], res[k], T0, T1, split)
        if not s:
            continue
        print(f"{v['name']:<52} {s['n']:>4} {pct(s['mean'], 7)} {pct(s['med'], 7)} {s['win']:>4.0%} {s['x2']:>5.0%} {pct(s['avgwin'], 8)} "
              f"{s['gaveback']:>3}/{s['p50']:<3} | {pct(s['full']['monthly'], 7)} {pct(s['old']['monthly'], 7)} {pct(s['new']['monthly'], 7)} "
              f"{pct(s['full']['dd'], 6, 0)}")
    print("(>=2x = share of trades closed at >= +100%; avg win = mean return of the winning trades; TEXTIT = trades that peaked >= +50% "
          "and still closed at a loss / trades that peaked >= +50%; month / older / newer = compounding monthly return, the newer half is "
          "out-of-sample for every variant since none was fitted on this data)")
    for k in ("live", "a", "c", "e"):
        top = sorted(zip(trades[k], res[k]), key=lambda z: -z[1][0])[:6]
        print(f"  best trades {k:<5}: " + ", ".join(f"{tr['sym']} {pct(x[0], 1)} (peak {x[2]:.1f}x)" for tr, x in top))
    return ST, used


# ----------------------------------------------------------------------------- data
def fetch_pools(cl, reg, now, months, hourly_pages, budget_s, max_pools, t_start):
    ws0 = now - int(months * 30.44 * DAY)
    cand = [p for p in reg.values() if p["created"] <= now - 8 * DAY and p.get("ref_reserve", 0) >= 15_000 and p.get("pool")]
    rng = random.Random(42)
    rng.shuffle(cand)
    blind = lambda p: p.get("first_seen", now) <= now - 8 * DAY or "new" in p.get("srcs", [])
    cand.sort(key=lambda p: (not blind(p), -p.get("ref_reserve", 0) if not blind(p) else 0))
    cand = cand[:max_pools]
    print(f"{len(cand)} candidate pools (dex_runner_study's selection: >= 8 days old, >= $15k reserve ever seen); window from {ts(ws0)}")
    pools, why = [], collections.Counter()
    for n, p in enumerate(cand):
        if time.time() - t_start > budget_s:
            why["budget"] += len(cand) - n
            break
        try:
            hourly, complete = fetch_series(cl, p, "hour", 1, max(p["created"], ws0), now, hourly_pages)
        except Exception:
            hourly, complete = [], False
            why["error"] += 1
        if len(hourly) < 30:
            why["no data"] += 1
            continue
        grid = hourly_grid(clean(hourly))
        if not grid:
            why["short"] += 1
            continue
        dead = complete and now - (hourly[-1][0] + HOUR) > DEAD_H * HOUR
        P = Pool(p, grid, now, dead)
        P.key = f"{p['net']}:{p['token']}"
        pools.append(P)
        if n % 100 == 0:
            print(f"  fetched {n + 1}/{len(cand)}  calls {cl.calls}  429s {cl.r429}  pools kept {len(pools)}  {time.time() - t_start:.0f}s")
            sys.stdout.flush()
    print(f"API calls {cl.calls} (429s {cl.r429}); pools with usable history {len(pools)}; skipped: "
          + ", ".join(f"{k} {v}" for k, v in why.items()))
    return pools, ws0


P_FIELDS = ("net", "token", "pool", "sym", "created", "ref_reserve", "ref_price", "fdv", "price_now", "first_seen")


def g6(x):
    return float(f"{x:.6g}")


def dump(path, pools, used, series, now, ws0):
    d = {"now": now, "ws0": ws0, "pools": [], "legends": []}
    for P in pools:
        if P.key in used:
            d["pools"].append({"p": {k: P.p.get(k) for k in P_FIELDS}, "dead": P.dead, "t0": P.t0,
                               "ohlcv": [[g6(x) for x in a] for a in (P.O, P.H, P.L, P.C, P.V)]})
    for S in series:
        d["legends"].append({"sym": S.key, "kind": S.group, "name": S.name, "src": S.src, "dur": S.dur, "launch": S.launch,
                             "lag": S.meta.get("lag", 0),
                             "bars": [[S.T[i], g6(S.O[i]), g6(S.H[i]), g6(S.L[i]), g6(S.Cl[i]), g6(S.V[i])] for i in range(len(S.T))]})
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with gzip.open(path, "wt") as f:
        json.dump(d, f, separators=(",", ":"))
    print(f"\nwrote {len(d['pools'])} traded pools + {len(d['legends'])} legend series to {path} (offline re-analysis: --from-dump)")


def load_dump(path):
    from array import array
    with gzip.open(path, "rt") as f:
        d = json.load(f)
    now, pools, series = d["now"], [], []
    for x in d["pools"]:
        grid = (x["t0"],) + tuple(array("d", a) for a in x["ohlcv"])
        P = Pool(x["p"], grid, now, x["dead"])
        P.key = f"{x['p']['net']}:{x['p']['token']}"
        pools.append(P)
    coins = {c["sym"]: c for c in LG.COINS}
    for x in d["legends"]:
        series.append(LG.Ser(x["bars"], x["dur"], x["sym"], x["kind"], x["name"], launch=x["launch"], now=now, src=x["src"],
                             meta={"coin": coins.get(x["sym"], {"late": None}), "lag": x["lag"]}))
    return pools, series, d["ws0"], now


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--chaos", action="store_true")
    ap.add_argument("--from-dump", default=None)
    ap.add_argument("--offline-legends", action="store_true", help="legends from the cached daily bars only")
    ap.add_argument("--legend-min", type=float, default=35)
    ap.add_argument("--budget-min", type=float, default=200, help="total fetch budget (legends + pools)")
    ap.add_argument("--max-pools", type=int, default=3000)
    ap.add_argument("--months", type=float, default=2.7)
    ap.add_argument("--hourly-pages", type=int, default=2)
    ap.add_argument("--legends-cache", default="results/dex_legends_daily.json.gz")
    ap.add_argument("--data-out", default="results/dex_floor_hourly.json.gz")
    a = ap.parse_args()
    t_start = time.time()
    print(f"live exit (config.DEX['exit']): {EXIT}; break-even floor = entry x {BE:.3f}; slots {SLOTS}")
    for v in VARIANTS:
        print(f"  {v['key']:<6} {v['name']}")

    if a.from_dump:
        pools, series, ws0, now = load_dump(a.from_dump)
        print(f"\nfrom {a.from_dump}: {len(pools)} pools, {len(series)} legend series")
    else:
        if a.synthetic:
            print("\nSYNTHETIC MODE: fake prices, only checks that the study runs end to end" + (" (chaos on)" if a.chaos else ""))
            net = LG.FakeNet(a.chaos)
            sg = SyntheticGT(per_net=40)
            cl = ChaosGT(sg) if a.chaos else sg
            now = sg.now
            reg = merge_reg({}, [dict(r, first_seen=r["seen"]) for r in sg.seed_registry()], now)
            cache = {}
        else:
            net, cl, now = LG.Net(t_start + a.budget_min * 60), AdaptiveGT(), int(time.time())
            reg = load_registry("results/dex_runner_pools.json")
            for k, e in load_registry("results/dex_exit_pools.json").items():
                reg.setdefault(k, dict(e, first_seen=e.get("first_seen") or e.get("seen", now)))
            cache = load_cache(a.legends_cache)
        banner("0. DATA")
        deadline = time.time() + a.legend_min * 60
        if not a.synthetic:
            net.deadline = deadline
        print("legends (dex_legends_study's sources, hourly preferred):")
        series = fetch_legends(net, LG.Until(cl, deadline), (net.now if a.synthetic else now), deadline, cache, a.offline_legends)
        print("\npools (dex_runner_study's registry + selection, hourly GeckoTerminal):")
        pools, ws0 = fetch_pools(cl, reg, now, a.months, a.hourly_pages, a.budget_min * 60, a.max_pools, t_start)

    leg, lost = run_legends(series)
    ST, used = run_pools(pools, ws0, now) if len(pools) >= 10 else (None, set())
    if not a.from_dump and not a.synthetic:
        try:
            dump(a.data_out, pools, used, series, now, ws0)
        except Exception as ex:
            print(f"could not write {a.data_out}: {ex}")

    banner("3. VERDICT  (apply only if monthly return >= the current rule in BOTH halves AND no legend loses its big multiple)")
    if not ST or not ST.get("live"):
        print("no pool results - nothing to decide")
        return
    L0 = ST["live"]
    print(f"current rule: {pct(L0['full']['monthly'], 1)}/month (older {pct(L0['old']['monthly'], 1)}, newer {pct(L0['new']['monthly'], 1)}), "
          f"max drawdown {pct(L0['full']['dd'], 1, 0)}, 2x-rate {L0['x2']:.0%}, avg winner {pct(L0['avgwin'], 1)}")
    winners = []
    for v in VARIANTS[1:]:
        s = ST.get(v["key"])
        if not s:
            continue
        both = s["old"]["monthly"] >= L0["old"]["monthly"] - 1e-9 and s["new"]["monthly"] >= L0["new"]["monthly"] - 1e-9
        legends_ok = not lost.get(v["key"])
        ok = both and legends_ok
        if ok:
            winners.append((v, s))
        print(f"  {v['name']:<52} older {pct(s['old']['monthly'] - L0['old']['monthly'], 1)} pts, newer "
              f"{pct(s['new']['monthly'] - L0['new']['monthly'], 1)} pts, maxDD {pct(s['full']['dd'], 1, 0)}, legends "
              f"{'kept' if legends_ok else 'LOST ' + ', '.join(lost[v['key']])} -> {'PASSES' if ok else 'fails'}")
    if winners:
        v, s = max(winners, key=lambda z: min(z[1]["old"]["monthly"], z[1]["new"]["monthly"]))
        print(f"\nBEST PASSING VARIANT: {v['name']}: {pct(s['full']['monthly'], 1)}/month (older {pct(s['old']['monthly'], 1)}, newer "
              f"{pct(s['new']['monthly'], 1)}), max drawdown {pct(s['full']['dd'], 1, 0)}")
    else:
        print("\nNO VARIANT PASSES: keep the current exit.")
    print("\nCAVEATS: pools are picked today (survivorship: rugs before the registry saw them are missing); liquidity is estimated "
          "(sqrt of price); hourly bars can't see a spike inside the hour, so a floor fills at the next hourly open or its level; "
          "legends are chosen in hindsight and some only have daily bars. Rank the variants, don't read the totals as a forecast.")
    print(f"({time.time() - t_start:.0f}s)")


if __name__ == "__main__":
    main()
