"""Four owner questions from results/research_log.md, answered in one walk-forward study on
Crypto.com data (all costs = config.FEE_RATE + config.SLIPPAGE_RATE per side unless noted).

  A. ROTATION  breakout10 (strategy.DonchianRotation, lookback 10, BTC 100-day regime, exit below the
               5-day low) replayed day by day through the live engine (engine.step, runner rules on):
               universe  = config.UNIVERSE  vs  + Crypto.com meme coins  vs  meme-only,
               top_n     = 1 / 2 / 3,  rebalance = weekly (live) / daily.
               Also lab.py's ens_donchian with top1 / top2 / top4 ("one coin vs two").
  B. ANATOMY   biggest one-day gainers across every Crypto.com USD pair; what was visible 1h/6h/24h/72h
               before (volume vs normal, quiet accumulation footprint, drift, 24h change); the same
               signals on every other coin-hour (false alarms); walk-forward trading of each signal.
  C. RUNNERS   listing-hunter exits on listings_study.py's listings with long (180-day) paths:
               live rule vs break-even floor once +50%, wider trail after 5x, and friends.

    python crypto_studies.py                       # real data (GitHub Actions; needs api.crypto.com)
    python crypto_studies.py --synthetic           # offline plumbing test (fake prices!)
    python crypto_studies.py --sections AC         # subset

Engine files are imported, never modified.
"""
import argparse
import bisect
import math
import random
import statistics
import time
from array import array
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import config
import lab
import listings_study as LS
import signals
from engine import Portfolio, step
from scanner import excluded
from strategy import DonchianRotation, regime_ok

HOUR = 3_600_000
DAY = 86_400_000
COST = config.FEE_RATE + config.SLIPPAGE_RATE          # per side, the engine's own numbers
COST_STRESS = 0.008                                    # small / new coins: wider spreads (pumps.py)
SUMMARY = []                                           # (section, plain-English lines, recommendation)

# Meme coins that may trade on Crypto.com; only those listed there with enough history / volume are used.
MEME_CANDIDATES = [
    "SHIB", "PEPE", "BONK", "WIF", "FLOKI", "BRETT", "POPCAT", "MOG", "TURBO", "NEIRO", "MEW", "BOME",
    "PNUT", "GOAT", "FARTCOIN", "TRUMP", "MOODENG", "PENGU", "SPX", "WEN", "MYRO", "BABYDOGE", "DOG",
    "TOSHI", "MEME", "PEOPLE", "SLERF", "CHILLGUY", "ACT", "AI16Z", "GIGA", "PONKE", "ELON", "SAMO",
    "CAT", "SNEK", "TROLL", "USELESS", "WOJAK", "APU", "LADYS", "KISHU", "MOCHI", "DEGEN", "SUNDOG",
    "MOTHER", "BAN", "HIPPO", "PUMP", "BITCOIN", "SPX6900", "NEIROCTO", "MANEKI", "MICHI", "BILLY",
]
MEME_MIN_DAYS = 180            # daily bars needed to be in a meme universe
MEME_MIN_DAILY_USD = 250_000   # median daily USD volume over the last 90 days


def ts(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")


def day_s(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def med(xs):
    return statistics.median(xs) if xs else float("nan")


def boot_ci(xs, n=2000, seed=1):
    if len(xs) < 2:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    ms = sorted(mean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return ms[int(0.025 * n)], ms[int(0.975 * n)]


def net(mult, cost=COST):
    return mult * (1 - cost) / (1 + cost) - 1


def banner(title):
    print("\n" + "=" * 110 + f"\n{title}\n" + "=" * 110, flush=True)


# ============================================================================= clients
class Cached:
    """Memoises daily candles (sections A/B/C all read them) and the coin list."""

    def __init__(self, c):
        self.c, self.memo = c, {}

    def list_spot_symbols(self, quote=config.QUOTE):
        if "syms" not in self.memo:
            self.memo["syms"] = self.c.list_spot_symbols()
        return self.memo["syms"]

    def candles(self, coin, timeframe="1h", count=600, end_ms=None):
        if timeframe != "1D":
            return self.c.candles(coin, timeframe=timeframe, count=count, end_ms=end_ms)
        k = (coin, count, end_ms)
        if k not in self.memo:
            self.memo[k] = self.c.candles(coin, timeframe="1D", count=count, end_ms=end_ms)
        return self.memo[k]


def synthetic_exchange(days):
    """data_source.SyntheticClient (hourly random walks with pumps) dressed up as an exchange with
    meme coins, a stablecoin and small alts; daily bars are aggregated from the hourly ones."""
    from data_source import SyntheticClient

    class Synth(SyntheticClient):
        def list_spot_symbols(self, quote=config.QUOTE):
            return sorted(set(config.UNIVERSE) | {"PEPE", "BONK", "WIF", "FLOKI", "SHIB", "BRETT", "USDT"}
                          | {f"ALT{i}" for i in range(14)})

        def candles(self, coin, timeframe="1h", count=600, end_ms=None):
            if timeframe != "1D":
                return super().candles(coin, "1h", count, end_ms)
            hs = super().candles(coin, "1h", self.n, end_ms)
            if coin in ("WIF", "BRETT"):          # listed later than the rest
                hs = hs[len(hs) // 3:]
            out = {}
            for h in hs:
                d = h["t"] // DAY * DAY
                if d not in out:
                    out[d] = dict(t=d, o=h["o"], h=h["h"], l=h["l"], c=h["c"], v=0.0)
                x = out[d]
                x["h"], x["l"], x["c"] = max(x["h"], h["h"]), min(x["l"], h["l"]), h["c"]
                x["v"] += h["v"] * h["c"]
            rows = [out[k] for k in sorted(out)]
            for r in rows:
                r["v"] /= r["c"]
            return rows[-count:]

    return Synth(seed=7, n=days * 24)


def pmap(fn, items, workers):
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        return list(ex.map(fn, items))


def load_daily(client, syms, days, now_ms, workers):
    def one(s):
        try:
            cs = client.candles(s, timeframe="1D", count=days, end_ms=now_ms)
            return s, [c for c in cs if c["v"] > 0]
        except Exception as e:
            print(f"  skip {s}: {e}")
            return s, []
    return {s: cs for s, cs in pmap(one, syms, workers) if cs}


# ============================================================================= A. rotation
def pick_memes(client, daily_days, now_ms, workers):
    avail = set(client.list_spot_symbols())
    cands = [m for m in MEME_CANDIDATES if m in avail and m not in config.UNIVERSE]
    data = load_daily(client, cands, daily_days, now_ms, workers)
    keep, report = [], []
    for s in cands:
        cs = data.get(s, [])
        usd = sorted(c["v"] * c["c"] for c in cs[-90:])
        m = usd[len(usd) // 2] if usd else 0.0
        ok = len(cs) >= MEME_MIN_DAYS and m >= MEME_MIN_DAILY_USD
        report.append((s, len(cs), m, day_s(cs[0]["t"]) if cs else "-", ok))
        if ok:
            keep.append(s)
    return keep, data, report, sorted(avail & set(MEME_CANDIDATES) - set(keep) - set(config.UNIVERSE))


def rotation(daily, universe, top_n, rebalance="weekly", runners=True, start=100):
    """Day-by-day replay of the live breakout10 account through engine.step (daily closes,
    bars_per_day=1). Returns [(t, equity)] and the portfolio."""
    strat = DonchianRotation(universe, 1, lookback=10, top_n=top_n, regime_days=100)
    if rebalance == "daily":
        strat.rebalance_key = "%Y-%m-%d"
    btc = daily["BTC"]
    bclose = [c["c"] for c in btc]
    idx = {s: {c["t"]: j for j, c in enumerate(daily[s])} for s in universe if s in daily}
    pf = Portfolio(fee=config.FEE_RATE, slippage=config.SLIPPAGE_RATE)
    last, curve = {}, []
    for i, b in enumerate(btc):
        t = b["t"]
        view = {}
        for s, ix in idx.items():
            j = ix.get(t)
            if j is None:
                continue
            last[s] = daily[s][j]["c"]
            if j + 1 >= strat.min_candles:
                view[s] = daily[s][max(0, j + 1 - strat.window):j + 1]
        if i < start:
            continue
        ok = regime_ok(bclose[max(0, i - 99):i + 1], 1, 100)
        step(pf, view, strat, ok, runners=runners)
        curve.append((t, pf.equity(last)))
    return curve, pf


def month_key(t):
    d = datetime.fromtimestamp(t / 1000, timezone.utc)
    return d.year, d.month


def curve_stats(curve):
    """curve: [(t, equity)]. Monthly = geometric average per 30.44 days; months = calendar months."""
    if len(curve) < 20:
        return None
    e0 = curve[0][1]
    eq = [e / e0 for _, e in curve]
    n_days = (curve[-1][0] - curve[0][0]) / DAY
    months = max(n_days / 30.44, 1e-9)
    peak, mdd = eq[0], 0.0
    for e in eq:
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
    by_m, prev_end, last_k, cur = [], 1.0, None, 1.0
    for (t, _), e in zip(curve, eq):
        k = month_key(t)
        if last_k is not None and k != last_k:
            by_m.append(cur / prev_end - 1)
            prev_end = cur
        cur, last_k = e, k
    by_m.append(eq[-1] / prev_end - 1)
    rets = [eq[i] / eq[i - 1] - 1 for i in range(1, len(eq))]
    sd = statistics.pstdev(rets) or 1e-12
    return {"total": eq[-1] - 1, "monthly": eq[-1] ** (1 / months) - 1, "mdd": mdd,
            "worst_m": min(by_m), "best_m": max(by_m), "pos_m": sum(1 for x in by_m if x > 0) / len(by_m),
            "n_m": len(by_m), "sharpe": mean(rets) / sd * math.sqrt(365)}


def sub_curve(curve, t0, t1):
    return [(t, e) for t, e in curve if t0 <= t < t1]


def wf_windows(curve, train_m, test_m, step_m):
    """(train_t0, test_t0, test_t1) on month boundaries of the curve."""
    starts = [curve[0][0]]
    for (t0, _), (t1, _) in zip(curve, curve[1:]):
        if month_key(t1) != month_key(t0):
            starts.append(t1)
    out, k = [], 0
    end = curve[-1][0] + DAY
    while k + train_m < len(starts):
        te = starts[k + train_m + test_m] if k + train_m + test_m < len(starts) else end
        if te - starts[k + train_m] >= 20 * DAY:
            out.append((starts[k], starts[k + train_m], te))
        k += step_m
    return out


def seg_ret(curve, t0, t1):
    s = sub_curve(curve, t0, t1)
    if len(s) < 2:
        return 0.0
    # include the move from the previous day's close into the window
    j = bisect.bisect_left([t for t, _ in curve], t0)
    base = curve[j - 1][1] if j > 0 else s[0][1]
    return s[-1][1] / base - 1


def seg_sharpe(curve, t0, t1):
    s = [e for t, e in curve if t0 <= t < t1]
    rets = [s[i] / s[i - 1] - 1 for i in range(1, len(s))]
    if len(rets) < 20:
        return -9.0
    sd = statistics.pstdev(rets)
    return mean(rets) / sd * math.sqrt(365) if sd > 0 else 0.0


def section_a(client, now_ms, a):
    banner("A. BREAKOUT10 ROTATION: meme coins in the universe, one coin vs two vs three, weekly vs daily")
    memes, meme_daily, report, dropped = pick_memes(client, a.daily_days, now_ms, a.workers)
    print(f"meme candidates on Crypto.com (need >= {MEME_MIN_DAYS} daily bars and median daily volume "
          f">= ${MEME_MIN_DAILY_USD:,} over the last 90 days):")
    for s, n, m, first, ok in report:
        print(f"  {s:<9} {n:>5} days since {first}  median daily ${m:>13,.0f}  {'USED' if ok else 'too thin / short'}")
    core = list(config.UNIVERSE)
    daily = load_daily(client, sorted(set(core) | {"BTC"}), a.daily_days, now_ms, a.workers)
    daily.update({s: meme_daily[s] for s in memes})
    if "BTC" not in daily:
        print("no BTC history - section A skipped")
        return
    meme_only = ["DOGE"] + memes
    unis = {"core (live)": core, "core+meme": core + memes, "meme-only": meme_only}
    print(f"\ncore = config.UNIVERSE ({len(core)}); memes used = {', '.join(memes) or 'none'}; "
          f"meme-only = DOGE + memes ({len(meme_only)})")
    print(f"BTC daily history {day_s(daily['BTC'][0]['t'])} .. {day_s(daily['BTC'][-1]['t'])} "
          f"({len(daily['BTC'])} days); simulation starts after a 100-day warm-up")
    print("engine replay: strategy.DonchianRotation(lookback 10, regime 100d) through engine.step on daily "
          f"closes, runner rules on (as live), cost {COST:.2%}/side; a meme coin only trades once it has 32 days of history")
    print("(survivorship caveat: memes are coins that still trade today with volume; old windows hold few or none of them)")

    runs = {}
    t_start = time.time()
    for uname, uni in unis.items():
        if len(uni) < 2:
            continue
        for top in (1, 2, 3):
            for reb in ("weekly", "daily"):
                curve, pf = rotation(daily, uni, top, reb)
                runs[(uname, top, reb)] = (curve, len(pf.trades))
    curve_nr, pf_nr = rotation(daily, core, 2, "weekly", runners=False)
    print(f"  .. {len(runs) + 1} engine replays in {time.time() - t_start:.0f}s")
    live_key = ("core (live)", 2, "weekly")
    live = runs[live_key][0]
    if len(live) < 60:
        print("not enough history for section A")
        return
    t0, t_end = live[0][0], live[-1][0] + DAY
    t_mid = t0 + (t_end - t0) // 2
    wins = wf_windows(live, a.train_m, a.test_m, a.step_m)
    print(f"\nspan {day_s(t0)} .. {day_s(t_end - DAY)}; older half < {day_s(t_mid)} <= newer half; walk-forward "
          f"{a.train_m}m train -> {a.test_m}m test, {len(wins)} test windows"
          + (f" ({day_s(wins[0][1])} .. {day_s(t_end - DAY)})" if wins else ""))

    def wf_total(curve):
        tot = 1.0
        for _, te0, te1 in wins:
            tot *= 1 + seg_ret(curve, te0, te1)
        return tot - 1

    oos_months = sum((te1 - te0) for _, te0, te1 in wins) / DAY / 30.44 if wins else 0
    live_new = curve_stats(sub_curve(live, t_mid, t_end))
    live_wf = wf_total(live)
    hdr = (f"{'universe':<12} {'top':>3} {'rebal':<6} | {'/month':>7} {'total':>8} {'maxDD':>6} {'worst mo':>8} "
           f"{'pos mo':>6} | {'old /mo':>7} {'new /mo':>7} {'new DD':>6} | {'WF-OOS/mo':>9} {'win vs live':>11} "
           f"{'trades':>6}  verdict")
    print("\n" + hdr + "\n" + "-" * len(hdr))
    rows = {}
    for key, (curve, ntr) in runs.items():
        st = curve_stats(curve)
        old, new = curve_stats(sub_curve(curve, t0, t_mid)), curve_stats(sub_curve(curve, t_mid, t_end))
        if not (st and old and new):
            continue
        wf = wf_total(curve)
        wf_mo = (1 + wf) ** (1 / oos_months) - 1 if oos_months else float("nan")
        won = sum(1 for _, a0, a1 in wins if seg_ret(curve, a0, a1) > seg_ret(live, a0, a1))
        beats = key != live_key and new["monthly"] > live_new["monthly"] and (not wins or wf > live_wf)
        ok_dd = new["mdd"] <= live_new["mdd"] + 0.10
        verdict = "LIVE" if key == live_key else ("BEATS live" + ("" if ok_dd else " (but deeper DD)")) if beats else "no"
        rows[key] = dict(st=st, old=old, new=new, wf=wf, wf_mo=wf_mo, won=won, beats=beats and ok_dd)
        print(f"{key[0]:<12} {key[1]:>3} {key[2]:<6} | {st['monthly']:>+7.2%} {st['total']:>+8.0%} {st['mdd']:>6.0%} "
              f"{st['worst_m']:>+8.1%} {st['pos_m']:>6.0%} | {old['monthly']:>+7.2%} {new['monthly']:>+7.2%} "
              f"{new['mdd']:>6.0%} | {wf_mo:>+9.2%} {won:>5}/{len(wins):<5} {ntr:>6}  {verdict}")
    st_nr = curve_stats(curve_nr)
    btc_c = [(c["t"], c["c"]) for c in daily["BTC"] if c["t"] >= t0]
    bst = curve_stats(btc_c)
    bnew = curve_stats(sub_curve(btc_c, t_mid, t_end))
    print(f"{'hold BTC':<23} | {bst['monthly']:>+7.2%} {bst['total']:>+8.0%} {bst['mdd']:>6.0%} {bst['worst_m']:>+8.1%} "
          f"{bst['pos_m']:>6.0%} |         {bnew['monthly']:>+7.2%} {bnew['mdd']:>6.0%} |")
    if st_nr:
        print(f"(live setup WITHOUT the runner rules: {st_nr['monthly']:+.2%}/month, max DD {st_nr['mdd']:.0%}, "
              f"worst month {st_nr['worst_m']:+.1%} - the runner rule's effect on the rotation)")

    # walk-forward selector: each window, pick the variant with the best trailing Sharpe
    if wins:
        print("\nWALK-FORWARD SELECTOR (each test window uses the variant with the best Sharpe over the prior "
              f"{a.train_m} months; no hindsight):")
        tot, tot_live = 1.0, 1.0
        for tr0, te0, te1 in wins:
            best = max(runs, key=lambda k: seg_sharpe(runs[k][0], tr0, te0))
            r, rl = seg_ret(runs[best][0], te0, te1), seg_ret(live, te0, te1)
            tot, tot_live = tot * (1 + r), tot_live * (1 + rl)
            print(f"  {day_s(te0)} .. {day_s(te1 - DAY)}  pick {best[0]:<12} top{best[1]} {best[2]:<6} -> {r:>+7.1%}"
                  f"   live {rl:>+7.1%}")
        print(f"  stitched: selector {tot - 1:+.1%} ({tot ** (1 / oos_months) - 1:+.2%}/mo) vs live "
              f"{tot_live - 1:+.1%} ({tot_live ** (1 / oos_months) - 1:+.2%}/mo)")

    # ens_donchian family (lab.py), one coin vs two vs four, core universe
    print("\nENS_DONCHIAN (lab.py family, core universe, fills at next open, same cost) - one coin vs two:")
    prices = {s: {c["t"] // DAY: (c["o"], c["h"], c["l"], c["c"]) for c in daily[s]}
              for s in sorted(set(core) | {"BTC"}) if s in daily}
    ctx = lab.Ctx(prices, "crypto", "BTC")
    st0 = next((i for i, d in enumerate(ctx.days) if d * DAY >= t0), 0)
    for uni in ("top1", "top2", "top4"):
        for tv in (None, 0.5):
            rets, _, trades = lab.simulate(ctx, lab.fam_ens_donchian, {"uni": uni, "tv": tv}, 0, ctx.n, COST)
            eq, curve = 1.0, []
            for i in range(st0, ctx.n):
                eq *= 1 + rets[i]
                curve.append((ctx.days[i] * DAY, eq))
            st, new = curve_stats(curve), curve_stats(sub_curve(curve, t_mid, t_end))
            if st and new:
                print(f"  {uni:<5} vol-target {str(tv):<5}: {st['monthly']:>+6.2%}/mo  maxDD {st['mdd']:>4.0%}  "
                      f"worst month {st['worst_m']:>+6.1%}  newer half {new['monthly']:>+6.2%}/mo (DD {new['mdd']:.0%})"
                      f"  trades {len(trades)}")

    # verdicts --------------------------------------------------------------------------------
    lv = rows.get(live_key)
    if not lv:
        return
    lines = [f"Live breakout10 (16 large coins, 2 at a time, weekly): {lv['st']['monthly']:+.2%}/month, max drawdown "
             f"{lv['st']['mdd']:.0%}, worst month {lv['st']['worst_m']:+.1%}; older half {lv['old']['monthly']:+.2%}/mo, "
             f"newer half {lv['new']['monthly']:+.2%}/mo."]
    recs = []
    for q, keys in (("meme", [("core+meme", 2, "weekly"), ("meme-only", 2, "weekly")]),
                    ("topn", [("core (live)", 1, "weekly"), ("core (live)", 3, "weekly")]),
                    ("daily", [("core (live)", 2, "daily")])):
        for k in keys:
            r = rows.get(k)
            if not r:
                lines.append(f"{k[0]} top{k[1]} {k[2]}: no data (no meme coin passed the history/volume filter).")
                continue
            lines.append(f"{k[0]} top{k[1]} {k[2]}: {r['st']['monthly']:+.2%}/month, max DD {r['st']['mdd']:.0%}, worst month "
                         f"{r['st']['worst_m']:+.1%}; newer half {r['new']['monthly']:+.2%}/mo; won {r['won']}/{len(wins)} "
                         f"walk-forward windows vs live -> {'BEATS live on unseen data' if r['beats'] else 'does not beat live'}.")
    winners = [k for k, r in rows.items() if r["beats"] and k[0] != "meme-only"]
    if winners:
        k = max(winners, key=lambda k: rows[k]["wf"])
        uni = f"config.UNIVERSE + {memes!r}" if k[0] == "core+meme" else "config.UNIVERSE"
        recs.append(f"best out-of-sample variant: {k[0]} top{k[1]} {k[2]} -> markets.py: DonchianRotation({uni}, 24"
                    + (f", top_n={k[1]})" if k[1] != 2 else ")")
                    + (" with rebalance_key = '%Y-%m-%d' on that instance (daily rebalance)" if k[2] == "daily" else "")
                    + (" (the memes are pulled automatically: run_live loads every strategy's universe)"
                       if k[0] == "core+meme" else ""))
    meme_only = rows.get(("meme-only", 2, "weekly"))
    if meme_only and meme_only["beats"]:
        recs.append("optionally add a separate TEST account DonchianRotation(['DOGE'] + memes, 24) named 'meme10' "
                    "(test only; meme-only beat live on unseen data)")
    SUMMARY.append(("A", lines, recs or ["keep: breakout10 on config.UNIVERSE, top_n=2, weekly rebalance "
                                         "(no variant beat it on the newer half AND the walk-forward windows with an "
                                         "acceptable drawdown)"]))


# ============================================================================= B. anatomy
PUMP = 0.30          # "top gainer": +30% within 24 hours (close to close)
MIN_DAILY_USD = 100_000
BASE_H, GAP_H = 168, 72   # "normal" hourly volume = mean over the 168h ending 72h before now
HIST = BASE_H + GAP_H
SIGNALS = [
    ("S1 1h volume >=5x, price flat (<3%)", "1h burst"),
    ("S2 1h volume >=10x, price <5%", "1h burst+"),
    ("S3 6h volume >=3x, price flat (<5%)", "6h build"),
    ("S4 6h volume >=5x, price <10%", "6h build+"),
    ("S5 24h volume >=2x, 24h change -5..+10%", "24h build"),
    ("S6 72h volume >=1.5x, 72h drift 0..+15%", "slow accum"),
    ("S7 live footprint score >=3 (signals.py)", "footprint"),
    ("S8 72h drift +5..+25%, no 1h move >6% in 48h", "drift"),
    ("S9 24h +10..30% on 6h volume >=3x", "take-off"),
    ("S10 CHASE: 24h >= +30% on 24h volume >=3x", "chase30"),
    ("S11 72h closing high on 6h volume >=3x, 24h <30%", "breakout"),
]
EXITS = [(0.10, 24), (0.20, 24), (0.10, 72), (0.20, 72), (0.35, 72), (0.35, 168)]


def load_hourly(client, syms, days, now_ms, workers):
    """Contiguous hourly grid per coin (missing hours forward-filled with zero volume), as arrays."""
    done = [0]

    def one(s):
        try:
            cs = client.candles(s, timeframe="1h", count=days * 24, end_ms=now_ms)
        except Exception as e:
            print(f"  skip {s}: {e}")
            return s, None
        done[0] += 1
        if done[0] % 50 == 0:
            print(f"  loaded {done[0]}/{len(syms)} hourly histories", flush=True)
        cs = [c for c in cs if c["v"] > 0]
        if len(cs) < HIST + 48:
            return s, None
        t0 = cs[0]["t"] // HOUR * HOUR
        n = (cs[-1]["t"] - t0) // HOUR + 1
        O, H, L, C, U = (array("d", [0.0]) * n for _ in range(5))
        k, last = 0, cs[0]["o"]
        for i in range(n):
            t = t0 + i * HOUR
            if k < len(cs) and cs[k]["t"] // HOUR * HOUR == t:
                c = cs[k]
                O[i], H[i], L[i], C[i], U[i] = c["o"], c["h"], c["l"], c["c"], c["v"] * c["c"]
                last = c["c"]
                k += 1
            else:
                O[i] = H[i] = L[i] = C[i] = last
        return s, {"t0": t0, "n": n, "O": O, "H": H, "L": L, "C": C, "U": U}
    return {s: d for s, d in pmap(one, syms, workers) if d}


FP = None


def footprint(C, L, U, i, p=None):
    """Same maths as signals.score_footprint on the hourly grid ending at bar i (inclusive).
    Returns (score, terms) or (None, reason)."""
    p = p or FP
    if i + 1 < 48 + p["min_history_h"]:
        return None, "history"
    lo_b = max(0, i + 1 - 48 - p["baseline_h"])
    base = U[lo_b:i - 47]
    m = statistics.median(base) if len(base) else 0.0
    if m <= 0 or C[i - 48] <= 0:
        return None, "no volume"
    daily = m * 24
    if not p["daily_usd"][0] <= daily <= p["daily_usd"][1]:
        return None, "daily"
    if C[i] / C[i - 24] - 1 > p["max_24h_change"]:
        return None, "24h"
    for k in range(i - 47, i + 1):
        if abs(C[k] / C[k - 1] - 1) > p["max_1h_move"]:
            return None, "spike"
    v48 = U[i - 47:i + 1]
    if max(v48) >= p["spike_vol_mult"] * m:
        return None, "volspike"
    ret48 = C[i] / C[i - 48] - 1
    quiet = sum(1 for v in v48 if v < m) / 48
    hikes = sum(1 for v in v48 if v >= p["hike_mult"] * m)
    blocks = [min(L[i - 47 + b:i - 47 + b + 12]) for b in range(0, 48, 12)]
    terms = {"drift": p["drift"][0] <= ret48 <= p["drift"][1], "quiet": quiet >= p["quiet_frac"],
             "hikes": p["hikes"][0] <= hikes <= p["hikes"][1],
             "rising_lows": all(y > x for x, y in zip(blocks, blocks[1:]))}
    return sum(terms.values()), dict(terms, quiet_frac=quiet, n_hikes=hikes, ret48=ret48)


def features(d, i, P):
    C, U = d["C"], d["U"]
    base = (P[i - GAP_H] - P[i - HIST]) / BASE_H
    f = {"base_daily": base * 24}
    for k in (1, 6, 24, 72):
        f[f"r{k}"] = C[i] / C[i - k] - 1
        f[f"vr{k}"] = ((P[i + 1] - P[i + 1 - k]) / k) / base if base > 0 else float("nan")
    sc, terms = footprint(C, d["L"], U, i)
    f["fp"] = sc if sc is not None else -1
    f["fp_quiet"] = terms["quiet_frac"] if sc is not None else float("nan")
    f["fp_hikes"] = terms["n_hikes"] if sc is not None else float("nan")
    return f


def scan_coin(sym, d, rng, control_p, pump):
    """One pass over a coin's hours: events, control samples, signal fires / hits / episodes."""
    C, L, U, n = d["C"], d["L"], d["U"], d["n"]
    P = [0.0] * (n + 1)
    for i in range(n):
        P[i + 1] = P[i] + U[i]
    # forward 24h max close
    fwd = [0.0] * n
    dq = deque()
    for i in range(n - 1, -1, -1):
        # window = closes i+1..i+24
        j = i + 1
        if j < n:
            while dq and C[dq[-1]] <= C[j]:
                dq.pop()
            dq.append(j)
        while dq and dq[0] > i + 24:
            dq.popleft()
        fwd[i] = C[dq[0]] / C[i] - 1 if dq and C[i] > 0 else 0.0
    # prior 72h max close (excluding i) and last "big 1h move" index
    pmax = [0.0] * n
    dq = deque()
    for i in range(n):
        while dq and dq[0] < i - 72:
            dq.popleft()
        pmax[i] = C[dq[0]] if dq else C[i]
        while dq and C[dq[-1]] <= C[i]:
            dq.pop()
        dq.append(i)
    lastbig = [-10 ** 9] * n
    lb = -10 ** 9
    for i in range(1, n):
        if C[i - 1] > 0 and abs(C[i] / C[i - 1] - 1) > 0.06:
            lb = i
        lastbig[i] = lb
    # events: peak P with close / min(prior 24 closes) - 1 >= pump; T0 = that low; 72h de-dup
    cands = []
    dq = deque()
    for i in range(n):
        while dq and dq[0] < i - 24:
            dq.popleft()
        if dq and C[dq[0]] > 0:
            g = C[i] / C[dq[0]] - 1
            if g >= pump:
                cands.append((g, i, dq[0]))
        while dq and C[dq[-1]] >= C[i]:
            dq.pop()
        dq.append(i)
    cands.sort(reverse=True)
    events, taken = [], []
    for g, pk, t0 in cands:
        if any(abs(pk - x) < 72 for x in taken):
            continue
        taken.append(pk)
        if t0 < HIST or t0 + 24 >= n:
            continue
        base = (P[t0 - GAP_H] - P[t0 - HIST]) / BASE_H
        if base * 24 < MIN_DAILY_USD:
            continue
        f = features(d, t0, P)
        f.update(sym=sym, t=d["t0"] + t0 * HOUR, gain=g, hours_to_peak=pk - t0, i=t0,
                 hit={}, hit0={})
        events.append(f)
    near = {}
    for e in events:
        for k in range(e["i"] - 6, e["i"] + 1):
            near.setdefault(k, []).append(e)
    nsig = len(SIGNALS)
    fires, hit30, hit10 = [0] * nsig, [0] * nsig, [0] * nsig
    episodes = [[] for _ in range(nsig)]
    last_fire = [-10 ** 9] * nsig
    elig = base30 = base10 = 0
    controls = []
    t_first = d["t0"]
    for i in range(HIST, n - 24):
        base = (P[i - GAP_H] - P[i - HIST]) / BASE_H
        if base * 24 < MIN_DAILY_USD:
            continue
        elig += 1
        fw = fwd[i]
        up30, up10 = fw >= pump, fw >= 0.10
        base30 += up30
        base10 += up10
        c = C[i]
        r1, r6, r24, r72 = c / C[i - 1] - 1, c / C[i - 6] - 1, c / C[i - 24] - 1, c / C[i - 72] - 1
        vr1 = U[i] / base
        vr6 = (P[i + 1] - P[i - 5]) / 6 / base
        vr24 = (P[i + 1] - P[i - 23]) / 24 / base
        vr72 = (P[i + 1] - P[i - 71]) / 72 / base
        calm48 = lastbig[i] < i - 47
        fp = False
        if calm48 and r24 <= FP["max_24h_change"]:
            sc, _ = footprint(C, L, U, i)
            fp = sc is not None and sc >= FP["min_score"]
        s = (vr1 >= 5 and abs(r1) < 0.03,
             vr1 >= 10 and abs(r1) < 0.05,
             vr6 >= 3 and abs(r6) < 0.05,
             vr6 >= 5 and abs(r6) < 0.10,
             vr24 >= 2 and -0.05 <= r24 <= 0.10,
             vr72 >= 1.5 and 0.0 <= r72 <= 0.15,
             fp,
             0.05 <= r72 <= 0.25 and calm48,
             0.10 <= r24 < 0.30 and vr6 >= 3,
             r24 >= 0.30 and vr24 >= 3,
             c >= pmax[i] and vr6 >= 3 and r24 < 0.30)
        ev = near.get(i)
        for k in range(nsig):
            if s[k]:
                fires[k] += 1
                hit30[k] += up30
                hit10[k] += up10
                if i - last_fire[k] > 24:
                    episodes[k].append(i)
                last_fire[k] = i
                if ev:
                    for e in ev:
                        e["hit"][k] = True
                        if i == e["i"]:
                            e["hit0"][k] = True
        if not up10 and rng.random() < control_p:
            f = features(d, i, P)
            f.update(sym=sym, t=t_first + i * HOUR)
            controls.append(f)
    return {"events": events, "controls": controls, "fires": fires, "hit30": hit30, "hit10": hit10,
            "episodes": episodes, "elig": elig, "base30": base30, "base10": base10}


def exit_sim(d, i, trail, hold):
    """Enter at bar i's close; trailing stop from the peak (checked with the pre-bar stop, gap fills at
    the open), else sell at the close after `hold` hours. Returns (gross multiple, exit bar)."""
    C, H, L, O, n = d["C"], d["H"], d["L"], d["O"], d["n"]
    entry = C[i]
    peak = entry
    end = min(n - 1, i + hold)
    for j in range(i + 1, end + 1):
        stop = peak * (1 - trail)
        if L[j] <= stop:
            return min(stop, O[j]) / entry, j
        peak = max(peak, H[j])
    return C[end] / entry, end


def slot_portfolio(trades, slots=5):
    """trades: [(t_in, t_out, net)] -> 5 equal slots of current equity, skip when full."""
    if not trades:
        return None
    trades = sorted(trades)
    cash, open_, eq_hist, skipped = 1.0, [], [1.0], 0
    for t_in, t_out, r in trades:
        for p in sorted([p for p in open_ if p[0] <= t_in]):
            cash += p[1] * (1 + p[2])
            open_.remove(p)
            eq_hist.append(cash + sum(x[1] for x in open_))
        if len(open_) >= slots:
            skipped += 1
            continue
        eq = cash + sum(x[1] for x in open_)
        size = min(cash, eq / slots)
        cash -= size
        open_.append((t_out, size, r))
    for p in sorted(open_):
        cash += p[1] * (1 + p[2])
    eq_hist.append(cash)
    peak, mdd = 1.0, 0.0
    for e in eq_hist:
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
    months = max((max(t[1] for t in trades) - trades[0][0]) / DAY / 30.44, 1e-9)
    return {"final": cash, "monthly": cash ** (1 / months) - 1 if cash > 0 else -1.0, "mdd": mdd,
            "skipped": skipped, "months": months}


def section_b(client, now_ms, a):
    global FP
    FP = signals._cfg("footprint")
    banner("B. ANATOMY OF THE TOP GAINERS (every Crypto.com USD pair)")
    syms = [s for s in client.list_spot_symbols() if not excluded(s)]
    print(f"{len(syms)} USD pairs (stable / wrapped / leveraged tokens excluded)")

    # --- B1. biggest one-day gainers, daily bars, full available history
    days = int(a.months * 30.5)
    daily = load_daily(client, syms, days, now_ms, a.workers)
    rows = []
    for s, cs in daily.items():
        for j in range(8, len(cs)):
            usd7 = sum(c["v"] * c["c"] for c in cs[j - 7:j]) / 7
            if usd7 < MIN_DAILY_USD or cs[j - 1]["c"] <= 0:
                continue
            g = cs[j]["c"] / cs[j - 1]["c"] - 1
            if g >= a.pump:
                rows.append((g, s, cs[j]["t"], cs[j - 1]["c"] / cs[j - 2]["c"] - 1,
                             cs[j - 1]["c"] / cs[j - 8]["c"] - 1, cs[j - 1]["v"] * cs[j - 1]["c"] / usd7,
                             cs[j]["h"] / cs[j - 1]["c"] - 1,
                             cs[min(len(cs) - 1, j + 3)]["c"] / cs[j]["c"] - 1))
    rows.sort(reverse=True)
    span = (max(c[-1]["t"] for c in daily.values()) - min(c[0]["t"] for c in daily.values())) / DAY if daily else 0
    print(f"\nB1. ONE-DAY GAINERS (daily close >= +{a.pump:.0%} vs the prior close; coin trading >= ${MIN_DAILY_USD:,}/day "
          f"the week before): {len(rows)} coin-days over {span:.0f} days = {len(rows) / max(span, 1):.2f} per day")
    print(f"{'coin':<9} {'day':<10} {'gain':>6} {'high':>6} | {'day-1 chg':>9} {'7d chg':>7} {'day-1 vol/7d':>12} | {'next 3d':>7}")
    for g, s, t, r1, r7, vr, hi, nxt in rows[:30]:
        print(f"{s:<9} {day_s(t):<10} {g:>+6.0%} {hi:>+6.0%} | {r1:>+9.1%} {r7:>+7.1%} {vr:>11.1f}x | {nxt:>+7.0%}")
    if rows:
        print(f"  median over all {len(rows)}: day-before change {med([r[3] for r in rows]):+.1%}, 7d change "
              f"{med([r[4] for r in rows]):+.1%}, day-before volume {med([r[5] for r in rows]):.1f}x its 7-day average, "
              f"next 3 days {med([r[7] for r in rows]):+.1%} (share still higher after 3 days: "
              f"{sum(1 for r in rows if r[7] > 0) / len(rows):.0%})")

    # --- B2. hourly anatomy
    print(f"\nloading up to {a.hourly_days} days of hourly bars for {len(syms)} coins...", flush=True)
    t_l = time.time()
    hourly = load_hourly(client, syms, a.hourly_days, now_ms, a.workers)
    if not hourly:
        print("no hourly data - section B stops here")
        return
    t_min = min(d["t0"] for d in hourly.values())
    t_max = max(d["t0"] + (d["n"] - 1) * HOUR for d in hourly.values())
    print(f"  .. {len(hourly)} coins with hourly history, {ts(t_min)} .. {ts(t_max)} "
          f"({sum(d['n'] for d in hourly.values()):,} coin-hours, {time.time() - t_l:.0f}s)")
    rng = random.Random(5)
    t_s = time.time()
    res = {s: scan_coin(s, d, rng, a.control_p, a.pump) for s, d in hourly.items()}
    print(f"  .. scanned in {time.time() - t_s:.0f}s")
    events = sorted((e for r in res.values() for e in r["events"]), key=lambda e: -e["gain"])
    controls = [c for r in res.values() for c in r["controls"]]
    elig = sum(r["elig"] for r in res.values())
    b30 = sum(r["base30"] for r in res.values())
    b10 = sum(r["base10"] for r in res.values())
    hspan = (t_max - t_min) / DAY
    print(f"\nB2. HOURLY EVENTS: +{a.pump:.0%} or more within 24h (close to close, from the lowest close of the prior "
          f"24h = T0), coin >= ${MIN_DAILY_USD:,}/day, >= 10 days listed: {len(events)} events "
          f"({len(events) / max(hspan, 1):.2f}/day); controls = {len(controls):,} random coin-hours that did NOT rise 10% next 24h")
    print(f"base rate: {b30 / max(elig, 1):.3%} of {elig:,} eligible coin-hours are followed by +{a.pump:.0%} within 24h "
          f"({b10 / max(elig, 1):.2%} by +10%)")
    print("open interest: NOT available - Crypto.com's public API has no OI history (get-tickers `oi` is live only;"
          " the engine logs it to data/oi_history.json for ~26h). Listing notices / CoinGecko trending: no history either.")
    print(f"\ntop 25 events (features at T0, i.e. what was visible BEFORE the move):")
    print(f"{'coin':<9} {'T0 (UTC)':<16} {'gain':>6} {'hrs':>3} | {'vol1h':>6} {'vol6h':>6} {'vol24h':>6} {'vol72h':>6} | "
          f"{'1h':>6} {'6h':>6} {'24h':>6} {'72h':>6} | {'fp':>2}  signals within 6h before")
    for e in events[:25]:
        sig = ",".join(SIGNALS[k][1] for k in sorted(e["hit"])) or "-"
        print(f"{e['sym']:<9} {ts(e['t']):<16} {e['gain']:>+6.0%} {e['hours_to_peak']:>3} | {e['vr1']:>5.1f}x {e['vr6']:>5.1f}x "
              f"{e['vr24']:>5.1f}x {e['vr72']:>5.1f}x | {e['r1']:>+6.1%} {e['r6']:>+6.1%} {e['r24']:>+6.1%} {e['r72']:>+6.1%} | "
              f"{e['fp']:>2}  {sig}")

    print("\nWHAT WAS VISIBLE BEFORE (median at T0; events vs non-pumping controls):")
    print(f"{'feature':<34} {'events':>9} {'controls':>9} {'ev <+50%':>9} {'ev 50-100%':>10} {'ev 100%+':>9}")
    buckets = [[e for e in events if lo <= e["gain"] < hi] for lo, hi in ((0, 0.5), (0.5, 1.0), (1.0, 1e9))]
    for key, label in (("vr1", "volume last 1h vs normal (x)"), ("vr6", "volume last 6h vs normal (x)"),
                       ("vr24", "volume last 24h vs normal (x)"), ("vr72", "volume last 72h vs normal (x)"),
                       ("r1", "price change last 1h"), ("r6", "price change last 6h"),
                       ("r24", "price change last 24h"), ("r72", "price change last 72h (drift)"),
                       ("fp_quiet", "quiet-hour share, last 48h"), ("fp_hikes", "volume hikes (>=3x), last 48h"),
                       ("base_daily", "normal daily USD volume")):
        vals = [med([x[key] for x in grp if not math.isnan(x[key])]) for grp in [events, controls] + buckets]
        pct = key.startswith("r") or key == "fp_quiet"
        print(f"{label:<34} " + " ".join((f"{v:>+9.1%}" if pct and key != "fp_quiet" else f"{v:>9.0%}" if pct
                                           else f"{v:>9,.0f}" if key == "base_daily" else f"{v:>9.2f}")
                                          for v in vals))
    for thr, label in ((3, "footprint score >= 3 (live rule)"), (2, "footprint score >= 2")):
        vals = [sum(1 for x in grp if x["fp"] >= thr) / len(grp) if grp else float("nan")
                for grp in [events, controls] + buckets]
        print(f"{label:<34} " + " ".join(f"{v:>9.1%}" for v in vals))
    print(f"(n = {len(events)} events, {len(controls)} controls, {len(buckets[0])} / {len(buckets[1])} / {len(buckets[2])} by size)")

    print("\nSIGNALS: how often each fired BEFORE a real pump, and how often it was a FALSE ALARM")
    print("  caught = share of events with the signal on in the 6h up to T0 (at T0 itself in brackets)")
    print(f"  precision = share of firing coin-hours followed by +{a.pump:.0%} within 24h (base rate {b30 / max(elig, 1):.3%});"
          " lift = precision / base rate; false alarms = episodes/day (24h de-dup) NOT followed by +30%")
    print(f"{'signal':<46} {'caught':>13} {'fires':>9} {'fire %':>7} {'prec':>7} {'lift':>5} {'prec10':>7} {'eps/day':>8} {'false/day':>9}")
    nsig = len(SIGNALS)
    fire_tot = [sum(r["fires"][k] for r in res.values()) for k in range(nsig)]
    h30 = [sum(r["hit30"][k] for r in res.values()) for k in range(nsig)]
    h10 = [sum(r["hit10"][k] for r in res.values()) for k in range(nsig)]
    base30 = b30 / max(elig, 1)
    ep_all = {k: [(hourly[s]["t0"] + i * HOUR, s, i) for s, r in res.items() for i in r["episodes"][k]]
              for k in range(nsig)}
    sig_rows = []
    for k, (label, short) in enumerate(SIGNALS):
        caught = sum(1 for e in events if k in e["hit"]) / max(len(events), 1)
        caught0 = sum(1 for e in events if k in e["hit0"]) / max(len(events), 1)
        prec = h30[k] / fire_tot[k] if fire_tot[k] else float("nan")
        eps = ep_all[k]
        good = sum(1 for _, s, i in eps if i < hourly[s]["n"] - 24 and
                   max(hourly[s]["C"][i + 1:i + 25]) / hourly[s]["C"][i] - 1 >= a.pump)
        sig_rows.append((k, caught, prec))
        print(f"{label:<46} {caught:>6.0%} ({caught0:>3.0%}) {fire_tot[k]:>9,} {fire_tot[k] / max(elig, 1):>7.2%} "
              f"{prec:>7.2%} {prec / base30 if base30 else float('nan'):>5.1f} "
              f"{h10[k] / fire_tot[k] if fire_tot[k] else float('nan'):>7.1%} {len(eps) / max(hspan, 1):>8.1f} "
              f"{(len(eps) - good) / max(hspan, 1):>9.1f}")

    # --- B3. trading each signal, walk-forward
    print(f"\nB3. TRADING THE SIGNALS (enter at the signal hour's close, one entry per coin per 24h episode; exits: "
          f"trailing stop from the peak or max hold). Cost {COST:.2%}/side (config), stress {COST_STRESS:.1%}/side.")
    t_s = time.time()
    trades = {}
    for k in range(nsig):
        for trail, hold in EXITS:
            tr = []
            for t_in, s, i in ep_all[k]:
                d = hourly[s]
                if i >= d["n"] - 1:
                    continue
                m, j = exit_sim(d, i, trail, hold)
                tr.append((t_in, d["t0"] + j * HOUR, m))
            trades[(k, trail, hold)] = tr
    print(f"  .. {sum(len(v) for v in trades.values()):,} simulated trades in {time.time() - t_s:.0f}s")
    t_lo = t_min + HIST * HOUR
    nb = 6
    edges = [t_lo + (t_max - t_lo) * b // nb for b in range(nb + 1)]
    edges[-1] = t_max + 1
    t_half = t_lo + (t_max - t_lo) // 2

    def pick(ts_, lo, hi, cost=COST):
        return [net(m, cost) for t, _, m in ts_ if lo <= t < hi]

    def rname(key):
        k, trail, hold = key
        return f"{SIGNALS[k][1]:<11} trail {trail:.0%} hold {hold:>3}h"

    print(f"\nall rules, whole period (IN-SAMPLE, optimistic), sorted by mean net per trade; halves split at {day_s(t_half)}:")
    print(f"{'rule':<34} {'n':>6} {'mean':>7} {'median':>7} {'win':>5} {'@0.8%':>7} | {'older':>7} {'newer':>7} | {'5-slot /mo':>10} {'DD':>5}")
    ranked = sorted(trades, key=lambda key: -mean(pick(trades[key], 0, 1 << 62)) if trades[key] else 1e9)
    for key in ranked[:15] + [x for x in ranked if x[0] == 9 and x[1:] == (0.20, 72)]:
        xs = pick(trades[key], 0, 1 << 62)
        if not xs:
            continue
        port = slot_portfolio([(t, u, net(m)) for t, u, m in trades[key]])
        print(f"{rname(key):<34} {len(xs):>6} {mean(xs):>+7.2%} {med(xs):>+7.2%} {sum(x > 0 for x in xs) / len(xs):>5.0%} "
              f"{mean(pick(trades[key], 0, 1 << 62, COST_STRESS)):>+7.2%} | {mean(pick(trades[key], 0, t_half)):>+7.2%} "
              f"{mean(pick(trades[key], t_half, 1 << 62)):>+7.2%} | {port['monthly']:>+10.1%} {port['mdd']:>5.0%}")

    print(f"\nper signal, best exit in-sample vs the newer half:")
    for k in range(nsig):
        keys = [x for x in trades if x[0] == k and trades[x]]
        if not keys:
            continue
        best = max(keys, key=lambda x: mean(pick(trades[x], 0, t_half)))
        o, nw = pick(trades[best], 0, t_half), pick(trades[best], t_half, 1 << 62)
        print(f"  {SIGNALS[k][0]:<46} best on older half: trail {best[1]:.0%} hold {best[2]}h -> older {mean(o):+.2%} "
              f"(n={len(o)}), NEWER {mean(nw):+.2%} (n={len(nw)})")

    print(f"\nWALK-FORWARD ({nb} time blocks; before each test block pick the rule with the best mean on ALL earlier blocks, "
          f"n >= 30; trade the block with it):")
    oos, oos_tr, chase_oos = [], [], []
    for b in range(2, nb):
        best, bs = None, -1e9
        for key, tr in trades.items():
            xs = pick(tr, 0, edges[b])
            if len(xs) >= 30 and mean(xs) > bs:
                best, bs = key, mean(xs)
        if best is None:
            continue
        xs = pick(trades[best], edges[b], edges[b + 1])
        oos += xs
        oos_tr += [(t, u, net(m)) for t, u, m in trades[best] if edges[b] <= t < edges[b + 1]]
        chase_oos += pick(trades[(9, 0.20, 72)], edges[b], edges[b + 1])
        last_pick = best
        print(f"  {day_s(edges[b])} .. {day_s(edges[b + 1] - 1)}: pick {rname(best)} (train {bs:+.2%}, n={len(pick(trades[best], 0, edges[b]))})"
              f" -> TEST {mean(xs):+.2%} per trade, n={len(xs)}, win {sum(x > 0 for x in xs) / max(len(xs), 1):.0%}")
    wf_ok, last_pick = False, None
    if oos:
        lo, hi = boot_ci(oos)
        port = slot_portfolio(oos_tr)
        wf_ok = lo > 0 and last_pick is not None and \
            mean(pick(trades[last_pick], t_half, 1 << 62, COST_STRESS)) > 0
        print(f"  stitched OOS: {mean(oos):+.2%} per trade [95% CI {lo:+.2%}, {hi:+.2%}], median {med(oos):+.2%}, "
              f"n={len(oos)}, 5-slot portfolio {port['monthly']:+.1%}/month (max DD {port['mdd']:.0%})")
        print(f"  (chasing coins already up 30% - S10, trail 20%/72h - in the same test blocks: {mean(chase_oos):+.2%} per trade, "
              f"n={len(chase_oos)})")

    # verdict
    lines = [f"{len(rows)} one-day +{a.pump:.0%} gainers over {span:.0f} days ({len(rows) / max(span, 1):.1f}/day); "
             f"{len(events)} hourly +{a.pump:.0%}-in-24h events in {hspan:.0f} days of hourly data."]
    if sig_rows:
        best_catch = max(sig_rows, key=lambda r: r[1])
        best_prec = max(sig_rows, key=lambda r: r[2] if not math.isnan(r[2]) else -1)
        lines.append(f"The early sign that came first most often: {SIGNALS[best_catch[0]][0]} (on in the 6h before "
                     f"{best_catch[1]:.0%} of pumps). The most precise: {SIGNALS[best_prec[0]][0]} - but only "
                     f"{best_prec[2]:.1%} of its firings were followed by +{a.pump:.0%} (base rate {base30:.2%}), so "
                     f"most firings are false alarms.")
    if oos:
        lines.append(f"Trading the signals walk-forward: {mean(oos):+.2%} per trade on unseen blocks (95% CI "
                     f"{boot_ci(oos)[0]:+.2%} .. {boot_ci(oos)[1]:+.2%}); chasing coins already +30%: {mean(chase_oos):+.2%}.")
    recs = ([f"keep the official config; add a TEST account for '{SIGNALS[last_pick[0]][0]}' with a "
             f"{last_pick[1]:.0%} trailing stop and {last_pick[2]}h max hold (the latest walk-forward pick: its 95% CI "
             f"clears zero and its newer half is positive even at {COST_STRESS:.1%}/side); promote only after a month live"]
            if wf_ok else
            ["keep: no early signal's walk-forward result was reliably profitable after costs (95% CI above zero AND "
             f"newer half positive at {COST_STRESS:.1%}/side); keep EARLY_MOVER movers=False, keep the 30% chase cap "
             "(max_24h_change 0.30) and leave the footprint / mover accounts as tests"])
    SUMMARY.append(("B", lines, recs))


# ============================================================================= C. runner exits
C_PATH_DAYS = 180
C_VARIANTS = {   # name: (base trail, [(peak multiple, trail)], break-even floor once hi >= x * entry)
    "live (50% trail)": (0.50, [], None),
    "BE floor at +50%": (0.50, [], 1.5),
    "BE floor at +100%": (0.50, [], 2.0),
    "60% trail after 5x": (0.50, [(5.0, 0.60)], None),
    "60% trail after 3x": (0.50, [(3.0, 0.60)], None),
    "BE+50% & 60% after 5x": (0.50, [(5.0, 0.60)], 1.5),
    "50/60@3x/70@10x": (0.50, [(3.0, 0.60), (10.0, 0.70)], None),
    "40% trail": (0.40, [], None),
    "60% trail": (0.60, [], None),
}


def runner_exit(L, trail, steps, be_at, h=None, ride=None):
    """Live listing hunter exit on one listing, replayed bar by bar in engine order: entry at the close
    of the first hour (strategy.EarlyMover buys within listing_hours); EarlyMover.manage (stop hit fills at
    the stop, or the close if it closed below; 24h time limit unless price >= 2x), engine runner rule
    (MOON: once the high is +50%, only trailing stops sell; runner trail from the high). Variants
    change the trail by peak multiple (steps) and add a break-even floor once hi >= be_at x entry."""
    h = config.EARLY_MOVER["h"] if h is None else h
    ride = config.MOON["ride"] if ride is None else ride
    e = LS.entry_point(L, "close_1h")
    if e is None:
        return None
    i, entry, t_in = e
    bars = L["bars"]

    def tr(hi):
        x = trail
        for mult, t in steps:
            if hi >= mult * entry:
                x = t
        return x

    stop, peak, hi = entry * (1 - trail), entry, entry
    for j in range(i + 1, len(bars)):
        b = bars[j]
        t_end = b["t"] + b["tf"]
        hi = max(hi, b["h"])                                   # engine.is_runner sees this bar's high first
        runner = hi >= entry * (1 + ride)
        if b["l"] <= stop:                                     # strategy._stop_check with the prior stop
            px = b["c"] if b["c"] < stop else stop
            return _res(px / entry, t_end, hi / entry, L, i, entry)
        if t_end - t_in >= h * HOUR and b["c"] < entry * 2 and not runner:
            return _res(b["c"] / entry, t_end, hi / entry, L, i, entry)
        peak = max(peak, b["h"])
        stop = max(stop, peak * (1 - tr(peak)))
        if be_at and hi >= be_at * entry:
            stop = max(stop, entry)
        rs = hi * (1 - tr(hi))                                 # engine runner_stop_hit (same bar)
        if runner and b["l"] <= rs:
            return _res(min(b["c"], rs) / entry, t_end, hi / entry, L, i, entry)
    b = bars[-1]
    r = _res(b["c"] / entry, b["t"] + b["tf"], hi / entry, L, i, entry)
    r["open"] = True
    return r


def _res(mult, t_exit, hi_mult, L, i, entry):
    peak_all = max([b["h"] for b in L["bars"][i + 1:]] + [entry]) / entry
    return {"mult": mult, "t_exit": t_exit, "hi_at_exit": hi_mult, "peak_all": peak_all, "open": False}


def section_c(client, now_ms, a):
    banner("C. LISTING-HUNTER RUNNER EXITS (listings_study.py listings, up to 180 days after listing)")
    cand, st = LS.discover_listings(client, a.months, now_ms, 0.0)
    old = LS.PATH_DAYS
    LS.PATH_DAYS = C_PATH_DAYS
    try:
        listings = LS.load_paths(client, cand, now_ms, 0.0)
    finally:
        LS.PATH_DAYS = old
    listings.sort(key=lambda L: L["t0"])
    print(f"{len(listings)} listings with usable data (of {len(cand)} candidates)")
    if len(listings) < 10:
        print("too few listings - section C skipped")
        return
    res = {}
    for name, (trail, steps, be) in C_VARIANTS.items():
        res[name] = [runner_exit(L, trail, steps, be) for L in listings]
    live = res["live (50% trail)"]
    ok_idx = [k for k, r in enumerate(live) if r]
    peaks = sorted(ok_idx, key=lambda k: -live[k]["peak_all"])
    top3 = peaks[:3]
    big10 = [k for k in ok_idx if live[k]["peak_all"] >= 10]
    big5 = [k for k in ok_idx if live[k]["peak_all"] >= 5]
    big3 = [k for k in ok_idx if live[k]["peak_all"] >= 3]
    print(f"entry: close of the first hour; exits as live (EARLY_MOVER trail {config.EARLY_MOVER['trail']:.0%}, "
          f"{config.EARLY_MOVER['h']}h limit unless >= 2x; MOON ride +{config.MOON['ride']:.0%} -> trailing stop only)")
    print(f"biggest peaks after entry (whole path): " + ", ".join(
        f"{listings[k]['sym']} {live[k]['peak_all']:.1f}x" for k in peaks[:8]))
    print(f"listings that went on to >= 3x: {len(big3)}, >= 5x: {len(big5)}, >= 10x: {len(big10)}; "
          f"top-3 = {', '.join(listings[k]['sym'] for k in top3)}")
    half = len(listings) // 2
    print(f"\n{'exit rule':<24} | {'mean':>7} {'@0.8%':>7} {'median':>7} {'win':>5} {'best':>6} | {'top3 capt':>9}  "
          f"{'top-3 trades (net)':<28} | {'>=5x sold<3x':>12} {'>=10x sold<3x':>13} | {'older':>7} {'newer':>7}")
    summ = {}
    for name, rs in res.items():
        xs = [net(r["mult"]) for r in rs if r]
        xs8 = [net(r["mult"], COST_STRESS) for r in rs if r]
        capt = sum(net(rs[k]["mult"]) for k in top3) / max(sum(rs[k]["peak_all"] - 1 for k in top3), 1e-9)
        t3 = " ".join(f"{net(rs[k]['mult']):+.0%}" for k in top3)
        s5 = sum(1 for k in big5 if not rs[k]["open"] and rs[k]["hi_at_exit"] < 3)
        s10 = sum(1 for k in big10 if not rs[k]["open"] and rs[k]["hi_at_exit"] < 3)
        o = [net(r["mult"]) for r in rs[:half] if r]
        nw = [net(r["mult"]) for r in rs[half:] if r]
        summ[name] = dict(mean=mean(xs), capt=capt, s5=s5, s10=s10, old=mean(o), new=mean(nw))
        print(f"{name:<24} | {mean(xs):>+7.1%} {mean(xs8):>+7.1%} {med(xs):>+7.1%} {sum(x > 0 for x in xs) / len(xs):>5.0%} "
              f"{max(xs):>+6.0%} | {capt:>9.0%}  {t3:<28} | {s5:>5}/{len(big5):<6} {s10:>6}/{len(big10):<6} | "
              f"{mean(o):>+7.1%} {mean(nw):>+7.1%}")
    n_open = sum(1 for r in live if r and r["open"])
    print(f"(top3 capt = net profit taken on the 3 biggest runners / their peak gain; 'sold<3x' = sold before the "
          f"price had reached 3x, among coins that later went >= 5x / >= 10x; {n_open} live trades still open at data end, "
          f"marked at the last close; older/newer = first/second half of listings by date)")

    print("\nWALK-FORWARD (expanding: before each listing pick the rule with the best mean on all earlier listings, "
          f"from listing {LS.MIN_TRAIN + 1}; trade the next one):")
    oos, oos_live, picks = [], [], []
    for k in range(LS.MIN_TRAIN, len(listings)):
        if not live[k]:
            continue
        best = max(res, key=lambda nm: mean([net(r["mult"]) for r in res[nm][:k] if r]))
        picks.append(best)
        oos.append(net(res[best][k]["mult"]))
        oos_live.append(net(live[k]["mult"]))
    if oos:
        cnt = {}
        for p in picks:
            cnt[p] = cnt.get(p, 0) + 1
        print(f"  walk-forward pick: {mean(oos):+.1%} per trade (n={len(oos)}) vs live held fixed {mean(oos_live):+.1%}; "
              f"picks: " + ", ".join(f"{p} x{n}" for p, n in sorted(cnt.items(), key=lambda x: -x[1])))
        print(f"  last pick: {picks[-1]}")
    lv = summ["live (50% trail)"]
    lines = [f"Live listing exit (50% trail, 24h limit, runners ride): {lv['mean']:+.1%} per trade, keeps "
             f"{lv['capt']:.0%} of the top-3 runners' peak gains; sold {lv['s10']} of {len(big10)} later-10x coins and "
             f"{lv['s5']} of {len(big5)} later-5x coins before 3x."]
    better = []
    for name, s in summ.items():
        if name.startswith("live"):
            continue
        lines.append(f"{name}: {s['mean']:+.1%} per trade ({s['mean'] - lv['mean']:+.1%} vs live), top-3 capture "
                     f"{s['capt']:.0%}, older {s['old']:+.1%} / newer {s['new']:+.1%}.")
        if s["mean"] > lv["mean"] and s["old"] >= lv["old"] and s["new"] >= lv["new"] and s["capt"] >= lv["capt"] \
                and s["s10"] <= lv["s10"]:
            better.append(name)
    wf_prefers = bool(oos) and mean(oos) > mean(oos_live) and picks[-1] != "live (50% trail)"
    recs = []
    if better and wf_prefers and picks[-1] in better:
        trail, steps, be = C_VARIANTS[picks[-1]]
        recs.append(f"switch runner exit to '{picks[-1]}': config.MOON = {{'ride': 0.50, 'trail': {trail}, 'hot': 0.50"
                    + (f", 'trail_steps': {steps}" if steps else "") + (f", 'breakeven_at': {be - 1:.2f}" if be else "")
                    + "} and config.EARLY_MOVER['trail'] = " + f"{trail}"
                    + (" (engine.runner_stop_hit / EarlyMover.manage must be taught the new keys)" if steps or be else "")
                    + "; note MOON applies to every live crypto account's runners")
    else:
        recs.append("keep config.MOON = {'ride': 0.50, 'trail': 0.50, 'hot': 0.50} and EARLY_MOVER trail 0.50"
                    + (f" (better in-sample but not confirmed walk-forward: {', '.join(better)})" if better else
                       " (no variant beat it on both halves, the top-3 capture and the walk-forward)"))
    SUMMARY.append(("C", lines, recs))


# ============================================================================= main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", default="ABC")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--daily-days", type=int, default=2000)
    ap.add_argument("--hourly-days", type=int, default=548)
    ap.add_argument("--months", type=float, default=18)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--pump", type=float, default=PUMP)
    ap.add_argument("--control-p", type=float, default=0.002)
    ap.add_argument("--train-m", type=int, default=18)
    ap.add_argument("--test-m", type=int, default=6)
    ap.add_argument("--step-m", type=int, default=6)
    a = ap.parse_args()
    t_start = time.time()
    now_ms = int(time.time() * 1000)
    print(f"crypto_studies.py  run {ts(now_ms)} UTC  cost {COST:.2%}/side (config.FEE_RATE {config.FEE_RATE:.2%} + "
          f"SLIPPAGE_RATE {config.SLIPPAGE_RATE:.2%})")
    if a.synthetic:
        print("*** SYNTHETIC DATA: tests the code only - numbers say nothing about markets ***")
        ex = Cached(synthetic_exchange(a.daily_days))
        lst = LS.SyntheticListingClient(months=a.months)
        now_ms = ex.c.candles("BTC", "1h", 1)[-1]["t"] + HOUR
    else:
        from data_source import CryptoComClient
        ex = Cached(CryptoComClient())
        lst = ex
    for sec, fn, cl in (("A", section_a, ex), ("B", section_b, ex), ("C", section_c, lst)):
        if sec in a.sections.upper():
            t0 = time.time()
            try:
                fn(cl, lst.now if (a.synthetic and sec == "C") else now_ms, a)
            except Exception as e:           # one failing section must not lose the others
                import traceback
                traceback.print_exc()
                SUMMARY.append((sec, [f"section {sec} FAILED: {e!r}"], ["keep (no result)"]))
            print(f"  .. section {sec} done in {time.time() - t0:.0f}s", flush=True)

    banner("SUMMARY (plain English) AND RECOMMENDED CONFIG CHANGES")
    titles = {"A": "Meme coins in the rotation / one coin vs two", "B": "Anatomy of the top gainers (Crypto.com)",
              "C": "Runner exits (listing hunter)"}
    for sec, lines, recs in SUMMARY:
        print(f"\n{sec}. {titles[sec]}")
        for ln in lines:
            print(f"  - {ln}")
        for r in recs:
            print(f"  => RECOMMENDATION: {r}")
    print(f"\n(total runtime {time.time() - t_start:.0f}s)")


if __name__ == "__main__":
    main()
