"""Short-hold SWING trading on Crypto.com USD pairs (owner's thesis: "coins go up one day, drop the next,
then bounce - find those gains across the market"; money always working, holds of 1-72 hours).

Universe: every Crypto.com USD pair (stable / wrapped / leveraged excluded) with median daily USD volume
>= $1M over the study window; at each signal the coin must also have traded >= $1M/day (median of the
30 days before), so a coin is only bought while it is liquid.

Families (all on completed bars, entry at the signal bar's close, one open trade per coin):
  D-MR  daily mean reversion: RSI(2) < 5/10/15 or a -5/-8/-12% day, optional trend filter (close above
        its 100/200-day average), exits: close above the 5-day average / +3/5/8% take-profit / max hold
        1-3 days (strategy.RSI2MeanReversion translated to crypto and shortened to <= 72h).
  H-MR  hourly mean reversion: RSI(2) on 1h bars < 5/10/15 (fresh cross) or -5/-8/-12% in 24h,
        same trend filters (daily averages of the last completed day), exits: close above the 5-hour
        average / +2/3/5% / max hold 6-72h.
  MOM   momentum continuation (comparison): buy a day's +5/10/15% movers at the daily close and sell
        1/2/3 days later; hourly: 24h change crosses +5/10/15%, hold 24/72h.
  Market filter on every variant: any / BTC above its 50-day / 100-day average / BTC below them.

Per variant: trades/day, win rate, mean / median net per trade, a compounding 5-slot account (20% of
equity per trade, skip when full) -> profit/month, max drawdown, worst month, older vs newer half.
Walk-forward: 6 equal time blocks; before each test block (3rd..6th) pick the variant that did best on
ALL earlier blocks, trade the block with it; stitched unseen trades -> mean with a bootstrap 95% CI.
Costs: config.FEE_RATE + config.SLIPPAGE_RATE per side (0.5%), and 0.2%/side (cheap maker fees).

    python crypto_swing_study.py                   # real data (GitHub Actions; needs api.crypto.com)
    python crypto_swing_study.py --synthetic       # offline plumbing test (fake prices!)

Engine files are imported, never modified.
"""
import argparse
import bisect
import heapq
import time

import config
from crypto_studies import (DAY, HOUR, MEME_CANDIDATES, Cached, banner, boot_ci, curve_stats, day_s, load_daily,
                            load_hourly, mean, med, net, synthetic_exchange, ts)
from scanner import excluded

COST = config.FEE_RATE + config.SLIPPAGE_RATE      # 0.5%/side, the engine's own numbers
COST_CHEAP = 0.002                                 # Kraken Pro maker-ish
MIN_USD = 1_000_000                                # median daily USD volume
SLOTS, PCT = 5, 0.20
NB = 6                                             # walk-forward time blocks
MIN_TRAIN_N = 30

MKTS = [("any", None), ("BTC>50d", (0, True)), ("BTC>100d", (1, True)),
        ("BTC<50d", (0, False)), ("BTC<100d", (1, False))]
TRENDS = [("", None), (">100d", 0), (">200d", 1)]


# ============================================================================= series helpers
def rsi_series(C, n=2):
    """Wilder RSI(n) for every bar (same recursion as strategy._rsi_last)."""
    out = [50.0] * len(C)
    gain = loss = 0.0
    for i in range(1, len(C)):
        ch = C[i] - C[i - 1]
        g, l_ = max(ch, 0.0), max(-ch, 0.0)
        if i <= n:
            gain += g / n
            loss += l_ / n
        else:
            gain = (gain * (n - 1) + g) / n
            loss = (loss * (n - 1) + l_) / n
        if i >= n:
            out[i] = 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
    return out


def sma_series(C, n):
    out, s = [None] * len(C), 0.0
    for i, c in enumerate(C):
        s += c
        if i >= n:
            s -= C[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def daily_grid(cs):
    """Contiguous day grid (missing days forward-filled, flagged not real)."""
    t0 = cs[0]["t"] // DAY * DAY
    n = (cs[-1]["t"] // DAY * DAY - t0) // DAY + 1
    O, H, L, C, U, R = [0.0] * n, [0.0] * n, [0.0] * n, [0.0] * n, [0.0] * n, [False] * n
    k, last = 0, cs[0]["o"]
    for i in range(n):
        t = t0 + i * DAY
        if k < len(cs) and cs[k]["t"] // DAY * DAY == t:
            c = cs[k]
            O[i], H[i], L[i], C[i], U[i], R[i] = c["o"], c["h"], c["l"], c["c"], c["v"] * c["c"], True
            last = c["c"]
            k += 1
            while k < len(cs) and cs[k]["t"] // DAY * DAY == t:
                k += 1
        else:
            O[i] = H[i] = L[i] = C[i] = last
    d = {"t0": t0, "n": n, "O": O, "H": H, "L": L, "C": C, "U": U, "R": R}
    d["rsi"] = rsi_series(C)
    d["sma5"] = sma_series(C, 5)
    d["sma50"], d["sma100"], d["sma200"] = sma_series(C, 50), sma_series(C, 100), sma_series(C, 200)
    liq = [0.0] * n
    for i in range(n):
        w = [u for u, r in zip(U[max(0, i - 29):i + 1], R[max(0, i - 29):i + 1]) if r]
        liq[i] = sorted(w)[len(w) // 2] if len(w) >= 10 else 0.0
    d["liq30"] = liq
    return d


def dix(d, t_day):
    """Index of the day starting at t_day in grid d, or None."""
    i = (t_day - d["t0"]) // DAY
    return i if 0 <= i < d["n"] else None


def trend_bits(d, i):
    c = d["C"][i]
    s1, s2 = d["sma100"][i], d["sma200"][i]
    return (1 if s1 is not None and c > s1 else 0) | (2 if s2 is not None and c > s2 else 0)


def mkt_bits(btc, t_day):
    i = dix(btc, t_day)
    if i is None:
        return None
    c = btc["C"][i]
    s50, s100 = btc["sma50"][i], btc["sma100"][i]
    if s50 is None or s100 is None:
        return None
    return (1 if c > s50 else 0) | (2 if c > s100 else 0)


# ============================================================================= events and exits
def daily_events(daily, btc, W0, W1):
    """{entry_key: [(t_close, coin, i, score, trend_bits, mkt_bits)]} sorted by time."""
    ev = {k: [] for k in ("rsi<5", "rsi<10", "rsi<15", "drop5", "drop8", "drop12", "up5", "up10", "up15")}
    for s, d in daily.items():
        C, R = d["C"], d["R"]
        for i in range(1, d["n"] - 1):
            t_close = d["t0"] + (i + 1) * DAY
            if not (W0 <= t_close < W1) or not R[i] or d["liq30"][i] < MIN_USD or C[i - 1] <= 0:
                continue
            mb = mkt_bits(btc, d["t0"] + i * DAY)
            if mb is None:
                continue
            tb = trend_bits(d, i)
            r, ret = d["rsi"][i], C[i] / C[i - 1] - 1
            for thr in (5, 10, 15):
                if r < thr:
                    ev[f"rsi<{thr}"].append((t_close, s, i, -r, tb, mb))
            for x in (5, 8, 12):
                if ret <= -x / 100:
                    ev[f"drop{x}"].append((t_close, s, i, -ret, tb, mb))
            for x in (5, 10, 15):
                if ret >= x / 100:
                    ev[f"up{x}"].append((t_close, s, i, ret, tb, mb))
    for v in ev.values():
        v.sort()
    return ev


def hourly_events(hourly, daily, btc, W0, W1):
    """Fresh crosses only (the previous hour was not already signalling)."""
    ev = {k: [] for k in ("rsi<5", "rsi<10", "rsi<15", "drop5", "drop8", "drop12", "up5", "up10", "up15")}
    for s, h in hourly.items():
        d = daily.get(s)
        if d is None:
            continue
        C, U = h["C"], h["U"]
        rs = rsi_series(C)
        h["sma5"] = sma_series(C, 5)
        for i in range(25, h["n"] - 1):
            t_close = h["t0"] + (i + 1) * HOUR
            if not (W0 <= t_close < W1) or U[i] <= 0 or C[i - 24] <= 0 or C[i - 25] <= 0:
                continue
            t_day = t_close // DAY * DAY - DAY               # last COMPLETED day
            j = dix(d, t_day)
            if j is None or d["liq30"][j] < MIN_USD:
                continue
            r, rp = rs[i], rs[i - 1]
            ret, retp = C[i] / C[i - 24] - 1, C[i - 1] / C[i - 25] - 1
            hits = []
            for thr in (5, 10, 15):
                if r < thr <= rp:
                    hits.append((f"rsi<{thr}", -r))
            for x in (5, 8, 12):
                if ret <= -x / 100 < retp:
                    hits.append((f"drop{x}", -ret))
            for x in (5, 10, 15):
                if ret >= x / 100 > retp:
                    hits.append((f"up{x}", ret))
            if not hits:
                continue
            mb = mkt_bits(btc, t_day)
            if mb is None:
                continue
            tb = trend_bits(d, j)
            for k, sc in hits:
                ev[k].append((t_close, s, i, sc, tb, mb))
    for v in ev.values():
        v.sort()
    return ev


def sim_exit(g, i, kind, hold, tp, bar_ms):
    """Enter at bar i's close. kind: 'sma5' (close above the 5-bar average) / 'tp' (+tp, filled at the
    target or the open if it gaps above) / 'time'; always out at the close `hold` bars later.
    Returns (gross multiple, exit bar close time) or None at the data edge."""
    C, O, H, n = g["C"], g["O"], g["H"], g["n"]
    if i >= n - 1:
        return None
    entry = C[i]
    end = min(n - 1, i + hold)
    tgt = entry * (1 + tp) if kind == "tp" else 0.0
    s5 = g["sma5"]
    for j in range(i + 1, end + 1):
        if kind == "tp" and H[j] >= tgt:
            return max(O[j], tgt) / entry, g["t0"] + (j + 1) * bar_ms
        if kind == "sma5" and s5[j] is not None and C[j] > s5[j]:
            return C[j] / entry, g["t0"] + (j + 1) * bar_ms
    return C[end] / entry, g["t0"] + (end + 1) * bar_ms


D_EXITS = [("sma5", 2, 0), ("sma5", 3, 0), ("tp", 3, 0.03), ("tp", 3, 0.05), ("tp", 3, 0.08),
           ("time", 1, 0)]
H_EXITS = [("sma5", 6, 0), ("sma5", 24, 0), ("sma5", 72, 0), ("tp", 24, 0.02), ("tp", 24, 0.03), ("tp", 24, 0.05),
           ("tp", 72, 0.05), ("time", 24, 0)]
DM_EXITS = [("time", 1, 0), ("time", 2, 0), ("time", 3, 0)]
HM_EXITS = [("time", 24, 0), ("time", 72, 0)]


def exit_name(tf, e):
    kind, hold, tp = e
    u = "d" if tf == "D" else "h"
    if kind == "sma5":
        return f"close>5{u}avg or {hold}{u}"
    if kind == "tp":
        return f"+{tp:.0%} or {hold}{u}"
    return f"sell after {hold}{u}"


# ============================================================================= trades and accounts
def build_trades(events, exres, trend, mkt):
    out, last_out = [], {}
    for k, (t, s, i, sc, tb, mb) in enumerate(events):
        if trend is not None and not (tb >> trend) & 1:
            continue
        if mkt is not None and ((mb >> mkt[0]) & 1) != mkt[1]:
            continue
        if last_out.get(s, 0) >= t:
            continue
        r = exres[k]
        if r is None:
            continue
        last_out[s] = r[1]
        out.append((t, r[1], r[0], sc))
    return out


def account(trades, cost, t0, t1):
    """Compounding 5-slot account: each entry takes 20% of equity (at cost), skipped when 5 are open.
    Simultaneous signals: strongest first. Equity = cash + open positions at cost (realised)."""
    tr = sorted((x for x in trades if t0 <= x[0] < t1), key=lambda x: (x[0], -x[3]))
    cash, opn, curve, taken = 1.0, [], [(t0, 1.0)], 0
    invested = 0.0
    for t_in, t_out, m, _ in tr:
        while opn and opn[0][0] <= t_in:
            to, size, r = heapq.heappop(opn)
            cash += size * (1 + r)
            invested -= size
            curve.append((to, cash + invested))
        if len(opn) >= SLOTS:
            continue
        eq = cash + invested
        size = min(cash, eq * PCT)
        if size <= 0:
            continue
        cash -= size
        invested += size
        taken += 1
        heapq.heappush(opn, (t_out, size, net(m, cost)))
    while opn:
        to, size, r = heapq.heappop(opn)
        cash += size * (1 + r)
        invested -= size
        curve.append((to, cash + invested))
    curve.append((max(t1, curve[-1][0]), cash))
    months = max((t1 - t0) / DAY / 30.44, 1e-9)
    st = curve_stats(curve) if len(curve) >= 20 else None
    peak, mdd = 1.0, 0.0
    for _, e in curve:
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
    return {"final": cash, "monthly": cash ** (1 / months) - 1 if cash > 0 else -1.0, "mdd": mdd,
            "worst_m": st["worst_m"] if st else float("nan"), "taken": taken,
            "per_day": taken / max((t1 - t0) / DAY, 1e-9)}


def btc_bench(btc, t0, t1):
    curve = [(btc["t0"] + (i + 1) * DAY, btc["C"][i]) for i in range(btc["n"])
             if t0 <= btc["t0"] + (i + 1) * DAY < t1]
    st = curve_stats(curve)
    return st


class Variant:
    def __init__(self, fam, tf, entry, trend, ex, mkt, trades):
        self.fam, self.tf, self.entry, self.trend, self.ex, self.mkt = fam, tf, entry, trend, ex, mkt
        self.trades = trades                    # sorted by entry time
        self.tin = [x[0] for x in trades]
        self.pre = {}
        for c in (COST, COST_CHEAP):
            p = [0.0]
            for x in trades:
                p.append(p[-1] + net(x[2], c))
            self.pre[c] = p

    @property
    def name(self):
        tr = [n for n, t in TRENDS if t == self.trend][0]
        mk = [m for m, v in MKTS if v == self.mkt][0]
        return f"{self.tf} {self.entry}{tr} | {exit_name(self.tf, self.ex)} | {mk}"

    def rng(self, lo, hi):
        return bisect.bisect_left(self.tin, lo), bisect.bisect_left(self.tin, hi)

    def mean_in(self, lo, hi, cost):
        a, b = self.rng(lo, hi)
        return ((self.pre[cost][b] - self.pre[cost][a]) / (b - a), b - a) if b > a else (float("nan"), 0)

    def nets(self, lo, hi, cost):
        a, b = self.rng(lo, hi)
        return [net(x[2], cost) for x in self.trades[a:b]]


def row(v, W0, W1, t_half, cost_list=(COST, COST_CHEAP)):
    xs = v.nets(W0, W1, COST)
    if not xs:
        return None
    days = (W1 - W0) / DAY
    acc = account(v.trades, COST, W0, W1)
    acc2 = account(v.trades, COST_CHEAP, W0, W1)
    return {"n": len(xs), "per_day": len(xs) / days, "win": sum(x > 0 for x in xs) / len(xs), "mean": mean(xs),
            "median": med(xs), "mean2": mean(v.nets(W0, W1, COST_CHEAP)), "acc": acc, "acc2": acc2,
            "older": v.mean_in(W0, t_half, COST)[0], "newer": v.mean_in(t_half, W1, COST)[0],
            "hold_h": mean([(x[1] - x[0]) / HOUR for x in v.trades])}


HDR = (f"{'variant':<50} {'n':>5} {'/day':>5} {'win':>4} {'mean':>7} {'median':>7} {'@0.2%':>7} | "
       f"{'5slot/mo':>8} {'maxDD':>5} {'worstM':>7} {'@0.2%/mo':>8} | {'older':>7} {'newer':>7} {'hold':>5}")


def fmt(v, r):
    return (f"{v.name:<50.50} {r['n']:>5} {r['per_day']:>5.2f} {r['win']:>4.0%} {r['mean']:>+7.2%} {r['median']:>+7.2%} "
            f"{r['mean2']:>+7.2%} | {r['acc']['monthly']:>+8.1%} {r['acc']['mdd']:>5.0%} {r['acc']['worst_m']:>+7.1%} "
            f"{r['acc2']['monthly']:>+8.1%} | {r['older']:>+7.2%} {r['newer']:>+7.2%} {r['hold_h']:>4.0f}h")


# ============================================================================= walk-forward
def walk_forward(vs, edges, cost, selector):
    """Before each test block b (2..NB-1), pick the variant with the best record on blocks < b:
    selector 'mean' = best mean net per trade (n >= 30); 'account' = best 5-slot profit/month."""
    picks, oos_tr = [], []
    for b in range(2, NB):
        lo, hi = edges[0], edges[b]
        best, bs = None, -1e18
        for v in vs:
            m, n = v.mean_in(lo, hi, cost)
            if n < MIN_TRAIN_N or m != m:
                continue
            if selector == "mean":
                sc = m
            else:
                if m <= 0 and best is not None:
                    continue
                sc = account(v.trades, cost, lo, hi)["monthly"]
            if sc > bs:
                best, bs = v, sc
        if best is None:
            picks.append((b, None, 0, []))
            continue
        a, z = best.rng(edges[b], edges[b + 1])
        tr = best.trades[a:z]
        oos_tr += tr
        picks.append((b, best, bs, [net(x[2], cost) for x in tr]))
    xs = [net(x[2], cost) for x in oos_tr]
    acc = account(oos_tr, cost, edges[2], edges[-1])
    lo_ci, hi_ci = boot_ci(xs)
    return {"picks": picks, "xs": xs, "acc": acc, "ci": (lo_ci, hi_ci), "per_day": len(xs) / ((edges[-1] - edges[2]) / DAY),
            "last": picks[-1][1] if picks else None}


# ============================================================================= main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--months", type=float, default=18)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-coins", type=int, default=0, help="cap on hourly coins (0 = all qualifying)")
    a = ap.parse_args()
    t_start = time.time()
    now_ms = int(time.time() * 1000)
    win_days = int(a.months * 30.44)
    daily_days = win_days + 240
    print(f"crypto_swing_study.py  run {ts(now_ms)} UTC  cost {COST:.2%}/side (config.FEE_RATE {config.FEE_RATE:.2%} + "
          f"SLIPPAGE_RATE {config.SLIPPAGE_RATE:.2%}); cheap-exchange check {COST_CHEAP:.2%}/side")
    if a.synthetic:
        print("*** SYNTHETIC DATA: tests the code only - numbers say nothing about markets ***")
        ex = Cached(synthetic_exchange(daily_days))
        now_ms = ex.c.candles("BTC", "1h", 1)[-1]["t"] + HOUR
    else:
        from data_source import CryptoComClient
        ex = Cached(CryptoComClient())

    banner("1. UNIVERSE: Crypto.com USD pairs with median daily USD volume >= $1M")
    try:
        syms = [s for s in ex.list_spot_symbols() if not excluded(s)]
    except Exception as e:
        print(f"could not list symbols ({e!r}); falling back to config.UNIVERSE")
        syms = list(config.UNIVERSE)
    print(f"{len(syms)} USD pairs (stable / wrapped / leveraged excluded); loading {daily_days} daily bars each...", flush=True)
    raw = load_daily(ex, syms, daily_days, now_ms, a.workers)
    W1 = now_ms // HOUR * HOUR
    W0 = W1 - win_days * DAY
    info = []
    for s, cs in raw.items():
        usd = [c["v"] * c["c"] for c in cs if c["t"] + DAY > W0]
        m = sorted(usd)[len(usd) // 2] if usd else 0.0
        info.append((m, s, len(usd), day_s(cs[0]["t"])))
    info.sort(reverse=True)
    qual = [s for m, s, nd, _ in info if m >= MIN_USD and nd >= 60]
    if "BTC" not in raw:
        print("no BTC daily data - cannot run (market filter / benchmark need it)")
        return
    if "BTC" not in qual:
        qual.insert(0, "BTC")
    if a.max_coins:
        qual = qual[:a.max_coins]
    print(f"window {day_s(W0)} .. {day_s(W1)} ({win_days} days). {len(qual)} of {len(info)} coins qualify:")
    for k in range(0, len(qual), 10):
        chunk = qual[k:k + 10]
        med_of = {s: m for m, s, _, _ in info}
        print("  " + "  ".join(f"{s} ${med_of.get(s, 0) / 1e6:.1f}M" for s in chunk))
    memes = [(s, m, nd) for m, s, nd, _ in info if s in MEME_CANDIDATES]
    if memes:
        print("meme coins listed: " + ", ".join(f"{s} ${m / 1e6:.2f}M{'' if s in qual else ' (too thin)'}"
                                                for s, m, nd in sorted(memes, key=lambda x: -x[1])))
    thin = [s for m, s, nd, _ in info if s not in qual]
    print(f"{len(thin)} coins too thin (< $1M/day median) or too short; near misses: "
          + ", ".join(f"{s} ${m / 1e6:.2f}M" for m, s, nd, _ in info if s not in qual and m >= 300_000)[:600])

    daily = {s: daily_grid(raw[s]) for s in qual if s in raw and len(raw[s]) >= 30}
    btc = daily["BTC"] if "BTC" in daily else daily_grid(raw["BTC"])
    print(f"\nloading hourly bars ({win_days + 3} days) for {len(daily)} coins...", flush=True)
    t_l = time.time()
    hourly = load_hourly(ex, list(daily), win_days + 3, now_ms, a.workers)
    print(f"  .. {len(hourly)} coins with hourly history ({time.time() - t_l:.0f}s)", flush=True)

    # ---- events and exits
    t_s = time.time()
    dev = daily_events(daily, btc, W0, W1)
    hev = hourly_events(hourly, daily, btc, W0, W1) if hourly else {}
    print(f"  signals: daily " + ", ".join(f"{k} {len(v)}" for k, v in dev.items())
          + "; hourly " + ", ".join(f"{k} {len(v)}" for k, v in hev.items()))
    specs = []   # (fam, tf, entry, trends, exits)
    for e in ("rsi<5", "rsi<10", "rsi<15", "drop5", "drop8", "drop12"):
        specs.append(("D-MR", "D", e, [t for _, t in TRENDS], D_EXITS))
        specs.append(("H-MR", "H", e, [t for _, t in TRENDS], H_EXITS))
    for e in ("up5", "up10", "up15"):
        specs.append(("MOM", "D", e, [None, 0], DM_EXITS))
        specs.append(("MOM", "H", e, [None, 0], HM_EXITS))
    variants = []
    for fam, tf, e, trends, exits in specs:
        evs = (dev if tf == "D" else hev).get(e, [])
        src = daily if tf == "D" else hourly
        bar = DAY if tf == "D" else HOUR
        for exk in exits:
            res = [sim_exit(src[s], i, exk[0], exk[1], exk[2], bar) for _, s, i, _, _, _ in evs]
            for tr in trends:
                for _, mk in MKTS:
                    variants.append(Variant(fam, tf, e, tr, exk, mk, build_trades(evs, res, tr, mk)))
    print(f"  {len(variants)} variants simulated in {time.time() - t_s:.0f}s", flush=True)

    t_half = W0 + (W1 - W0) // 2
    edges = [W0 + (W1 - W0) * b // NB for b in range(NB + 1)]
    bench = btc_bench(btc, W0, W1)
    bench_oos = btc_bench(btc, edges[2], W1)
    bench_h = (btc_bench(btc, W0, t_half), btc_bench(btc, t_half, W1))

    banner("2. BENCHMARKS")
    if bench:
        print(f"hold BTC {day_s(W0)} .. {day_s(W1)}: {bench['monthly']:+.2%}/month, max DD {bench['mdd']:.0%}, worst month "
              f"{bench['worst_m']:+.1%}; older half {bench_h[0]['monthly'] if bench_h[0] else float('nan'):+.2%}/mo, newer half "
              f"{bench_h[1]['monthly'] if bench_h[1] else float('nan'):+.2%}/mo")
    if bench_oos:
        print(f"hold BTC over the walk-forward test blocks ({day_s(edges[2])} .. {day_s(W1)}): {bench_oos['monthly']:+.2%}/month, "
              f"max DD {bench_oos['mdd']:.0%}")
    print("cash: +0.00%/month, no drawdown")

    banner(f"3. ALL VARIANTS, WHOLE WINDOW (IN-SAMPLE = optimistic); cost {COST:.1%}/side, '@0.2%' = {COST_CHEAP:.1%}/side")
    print("mean/median = net per trade after costs; 5slot/mo = compounding account, 20% of equity per trade, max 5 open;\n"
          f"older/newer = mean per trade before/after {day_s(t_half)}; hold = average hours held; trend filter "
          ">100d/>200d = coin above its 100/200-day average")
    rows = {}
    t_r = time.time()
    for v in variants:
        if len(v.trades) >= 10:
            r = row(v, W0, W1, t_half)
            if r:
                rows[v] = r
    print(f"  ({len(rows)} variants with >= 10 trades; stats in {time.time() - t_r:.0f}s)")
    fam_names = {"D-MR": "DAILY MEAN REVERSION (buy the drop at the daily close)",
                 "H-MR": "HOURLY MEAN REVERSION (buy the dip on 1h bars)",
                 "MOM": "MOMENTUM CONTINUATION (buy the movers, sell 1-3 days later) - comparison"}
    for fam in ("D-MR", "H-MR", "MOM"):
        vs = [v for v in rows if v.fam == fam and rows[v]["n"] >= 30]
        print(f"\n--- {fam_names[fam]}: {len(vs)} variants with >= 30 trades")
        if not vs:
            continue
        print(HDR)
        top = sorted(vs, key=lambda v: -rows[v]["mean"])[:15]
        for v in top:
            print(fmt(v, rows[v]))
        print("  top 5 by 5-slot account profit/month:")
        for v in sorted(vs, key=lambda v: -rows[v]["acc"]["monthly"])[:5]:
            print(fmt(v, rows[v]))
        pos = sum(1 for v in vs if rows[v]["mean"] > 0)
        pos2 = sum(1 for v in vs if rows[v]["mean2"] > 0)
        both = sum(1 for v in vs if rows[v]["older"] > 0 and rows[v]["newer"] > 0)
        print(f"  {pos}/{len(vs)} variants positive per trade at {COST:.1%}/side, {pos2}/{len(vs)} at {COST_CHEAP:.1%}/side; "
              f"{both} positive in BOTH halves at {COST:.1%}")

    # reference rules
    print("\n--- reference rules (stock RSI2 translated; the owner's 'drop then bounce'; next-day momentum):")
    print(HDR)
    refs = [("D", "rsi<10", 1, ("sma5", 3, 0), None), ("D", "rsi<15", 1, ("sma5", 3, 0), None),
            ("D", "drop8", None, ("sma5", 3, 0), None), ("H", "rsi<5", None, ("sma5", 24, 0), None),
            ("H", "drop8", None, ("tp", 24, 0.03), None), ("D", "up10", None, ("time", 1, 0), None)]
    for tf, e, tr, exk, mk in refs:
        for v in variants:
            if (v.tf, v.entry, v.trend, v.ex, v.mkt) == (tf, e, tr, exk, mk) and v in rows:
                print(fmt(v, rows[v]))

    # market filter comparison for each family's best entry/exit (any market)
    print("\n--- market filter (BTC vs its 50/100-day average) for each family's best entry+exit:")
    print(HDR)
    for fam in ("D-MR", "H-MR", "MOM"):
        base = [v for v in rows if v.fam == fam and v.mkt is None and rows[v]["n"] >= 30]
        if not base:
            continue
        b = max(base, key=lambda v: rows[v]["mean"])
        for v in variants:
            if (v.fam, v.tf, v.entry, v.trend, v.ex) == (b.fam, b.tf, b.entry, b.trend, b.ex) and v in rows:
                print(fmt(v, rows[v]))

    banner(f"4. WALK-FORWARD ({NB} blocks of ~{(W1 - W0) / NB / DAY:.0f} days; before each of blocks 3..{NB} pick the best "
           f"variant on ALL earlier blocks, trade the next block with it)")
    print("blocks: " + " | ".join(day_s(e) for e in edges))
    wf = {}
    groups = [("D-MR", lambda v: v.fam == "D-MR"), ("H-MR", lambda v: v.fam == "H-MR"),
              ("MOM", lambda v: v.fam == "MOM"), ("ALL", lambda v: True)]
    for cost in (COST, COST_CHEAP):
        print(f"\n### cost {cost:.1%}/side (selection AND test at this cost)")
        for gname, f in groups:
            vs = [v for v in variants if f(v) and len(v.trades) >= MIN_TRAIN_N]
            for sel in ("mean", "account"):
                if not vs:
                    continue
                r = walk_forward(vs, edges, cost, sel)
                wf[(cost, gname, sel)] = r
                print(f"\n  {gname} / pick by best {'mean per trade' if sel == 'mean' else '5-slot profit/month'}:")
                for b, v, sc, xs in r["picks"]:
                    if v is None:
                        print(f"    {day_s(edges[b])}: no variant with >= {MIN_TRAIN_N} training trades")
                        continue
                    test = (f"TEST {mean(xs):+.2%}/trade n={len(xs)} win {sum(x > 0 for x in xs) / len(xs):.0%}"
                            if xs else "TEST no trades (filter kept it in cash)")
                    print(f"    {day_s(edges[b])} .. {day_s(edges[b + 1])}: {v.name:<52.52} train "
                          f"{sc:+.2%}{'/trade' if sel == 'mean' else '/mo'} -> {test}")
                xs = r["xs"]
                if xs:
                    print(f"    UNSEEN: {mean(xs):+.2%}/trade [95% CI {r['ci'][0]:+.2%} .. {r['ci'][1]:+.2%}], median "
                          f"{med(xs):+.2%}, win {sum(x > 0 for x in xs) / len(xs):.0%}, {r['per_day']:.2f} signals/day; 5-slot "
                          f"account {r['acc']['monthly']:+.2%}/month ({r['acc']['per_day']:.2f} trades/day), max DD "
                          f"{r['acc']['mdd']:.0%}, worst month {r['acc']['worst_m']:+.1%}")

    # ---- summary
    banner("SUMMARY (plain English)")
    b_oos = bench_oos["monthly"] if bench_oos else float("nan")
    lines = []
    if bench:
        lines.append(f"Holding BTC over the {a.months:.0f} months: {bench['monthly']:+.2%}/month (max drawdown {bench['mdd']:.0%}); "
                     f"over the unseen test blocks: {b_oos:+.2%}/month. Cash: 0%.")
    lines.append(f"{len(qual)} Crypto.com USD coins trade >= $1M/day (median): {', '.join(qual[:40])}"
                 + (" ..." if len(qual) > 40 else "") + ". Meme coins are mostly too thin there.")

    def works(r):
        return r and r["xs"] and len(r["xs"]) >= 30 and r["ci"][0] > 0 and r["acc"]["monthly"] > 0

    verdict = {}
    for cost in (COST, COST_CHEAP):
        ok = [(k, r) for k, r in wf.items() if k[0] == cost and works(r)]
        verdict[cost] = max(ok, key=lambda kr: kr[1]["acc"]["monthly"]) if ok else None
        best_any = max((r for k, r in wf.items() if k[0] == cost and r["xs"]),
                       key=lambda r: r["acc"]["monthly"], default=None)
        for gname in ("D-MR", "H-MR", "MOM"):
            r = wf.get((cost, gname, "mean"))
            r2 = wf.get((cost, gname, "account"))
            if r and r["xs"]:
                lines.append(f"[{cost:.1%}/side] {gname} walk-forward on unseen data: {mean(r['xs']):+.2%}/trade "
                             f"(95% CI {r['ci'][0]:+.2%} .. {r['ci'][1]:+.2%}), {r['per_day']:.1f} signals/day, 5-slot account "
                             f"{r['acc']['monthly']:+.2%}/month (DD {r['acc']['mdd']:.0%}); picking by account profit instead: "
                             + (f"{r2['acc']['monthly']:+.2%}/month, {mean(r2['xs']):+.2%}/trade." if r2 and r2["xs"] else "no trades."))
            else:
                lines.append(f"[{cost:.1%}/side] {gname}: no walk-forward result (no data / too few trades).")
        if verdict[cost] is None and best_any:
            lines.append(f"[{cost:.1%}/side] nothing passed (needs 95% CI of unseen mean per trade above 0 AND a profitable "
                         f"5-slot account); best unseen account was {best_any['acc']['monthly']:+.2%}/month.")
    for ln in lines:
        print(f"  - {ln}")

    print()
    v5, v2 = verdict[COST], verdict[COST_CHEAP]
    if v5:
        (cost, g, sel), r = v5
        p = r["last"]
        print(f"  => YES at the live {COST:.1%}/side: {g} (picked by {sel}) made {r['acc']['monthly']:+.2%}/month on unseen data "
              f"({mean(r['xs']):+.2%}/trade, CI {r['ci'][0]:+.2%} .. {r['ci'][1]:+.2%}, {r['acc']['per_day']:.1f} trades/day in the "
              f"5-slot account) vs BTC {b_oos:+.2%}/month.")
        if p:
            print(f"  => RECOMMENDED SETTINGS (latest walk-forward pick): {p.name}; 5 slots x 20% of equity; "
                  f"entry at the signal bar's close; coin must trade >= $1M/day (30-day median).")
            if not (b_oos == b_oos) or r["acc"]["monthly"] <= b_oos:
                print(f"     (note: it did NOT beat simply holding BTC over the same unseen months)")
    elif v2:
        (cost, g, sel), r = v2
        p = r["last"]
        print(f"  => ONLY WITH CHEAP FEES: nothing works at {COST:.1%}/side; at {COST_CHEAP:.1%}/side {g} (picked by {sel}) made "
              f"{r['acc']['monthly']:+.2%}/month on unseen data ({mean(r['xs']):+.2%}/trade, CI {r['ci'][0]:+.2%} .. "
              f"{r['ci'][1]:+.2%}, {r['acc']['per_day']:.1f} trades/day) - needs a maker-fee exchange (e.g. Kraken Pro limit orders).")
        if p:
            print(f"  => settings if moved to a cheap exchange: {p.name}")
        print("  => ON CRYPTO.COM TODAY: none works - move the crypto account's idle cash to the DEX strategy.")
    else:
        print("  => none works - move the crypto account's idle cash to the DEX strategy.")
    print(f"\n(total runtime {time.time() - t_start:.0f}s)")


if __name__ == "__main__":
    main()
