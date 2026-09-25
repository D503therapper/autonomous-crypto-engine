"""Strategy research lab: walk-forward tournament over DAILY bars for many strategy
families (long-only, cash account). Unlike tournament.py's single 60/40 split, the
lab re-tunes every 6 months on the previous 18 months, trades the next 6 months with
that pick, and stitches those unseen 6-month stretches into one out-of-sample curve
per family. That is much closer to how the live engine would actually be run.

Execution model (no look-ahead): signals use day t's CLOSE, fills happen at day
t+1's OPEN, a cost is paid per side. Portfolio = equal slots, up to K positions.

    python lab.py --market crypto --years 5
    python lab.py --market stocks --years 8
    python lab.py --market both --synthetic     # code check only, no network
"""
import argparse
import itertools
import json
import math
import os
import random
import time
from datetime import date, datetime, timedelta, timezone

import config

ETFS = ["SPY", "QQQ", "IWM", "DIA", "TLT", "IEF", "GLD", "XLK", "XLF", "XLE", "XLV", "XLY",
        "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC", "SMH", "EFA", "EEM"]
INDEX_ETFS = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM", "GLD", "TLT"]
MARKET = {
    "crypto": {"syms": config.UNIVERSE, "bench": "BTC", "cost": 0.005, "ppy": 365, "slots": 4},
    "stocks": {"syms": sorted(set(config.STOCK_UNIVERSE) | set(ETFS)), "bench": "SPY",
               "cost": 0.0003, "ppy": 252, "slots": 5},
}
TRAIN_M, TEST_M, STEP_M = 18, 6, 6     # walk-forward window sizes in months
RESULTS_DIR = "results"
DAY_MS = 86_400_000


# ---------------------------------------------------------------- data
def load_crypto(symbols, years):
    from data_source import CryptoComClient
    c, out = CryptoComClient(), {}
    for s in symbols:
        try:
            cs = c.candles(s, timeframe="1D", count=years * 365)
            out[s] = {x["t"] // DAY_MS: (x["o"], x["h"], x["l"], x["c"]) for x in cs}
            print(f"  {s}: {len(out[s])} days")
        except Exception as e:
            print(f"  skip {s}: {e}")
        time.sleep(0.1)
    return out


def load_stocks(symbols, years):
    import yfinance as yf
    start = (date.today() - timedelta(days=years * 365)).isoformat()
    df = yf.download(sorted(symbols), start=start, interval="1d", auto_adjust=True,
                     group_by="ticker", progress=False, threads=True)
    out = {}
    for s in symbols:
        try:
            d = df[s].dropna()
        except KeyError:
            print(f"  skip {s}: no data")
            continue
        out[s] = {int(ix.timestamp()) // 86_400: (float(r["Open"]), float(r["High"]),
                                                 float(r["Low"]), float(r["Close"]))
                  for ix, r in d.iterrows()}
        print(f"  {s}: {len(out[s])} days")
    return out


def load_synthetic(symbols, years, market):
    """Random walks driven by a common market factor with bull/bear/chop regimes.
    ONLY tests the plumbing; numbers on this data say nothing about real markets."""
    rng = random.Random(11 if market == "crypto" else 12)
    today = date.today().toordinal() - date(1970, 1, 1).toordinal()
    days = [d for d in range(today - years * 365, today)
            if market == "crypto" or date.fromordinal(d + date(1970, 1, 1).toordinal()).weekday() < 5]
    mkt, drift = [], 0.0
    for i in range(len(days)):
        if i % 120 == 0:
            drift = rng.choice([0.003, 0.0005, -0.0015]) * (2 if market == "crypto" else 1)
        mkt.append(drift + rng.gauss(0, 0.03 if market == "crypto" else 0.01))
    out = {}
    for s in symbols:
        r2 = random.Random(hash((s, rng.random())))
        beta, vol = r2.uniform(0.6, 1.6), r2.uniform(0.01, 0.05 if market == "crypto" else 0.02)
        first = 0 if s in ("BTC", "SPY", "IEF") or r2.random() < 0.8 else r2.randint(0, len(days) // 2)  # some list late
        p, ser = r2.uniform(1, 500), {}
        for i in range(first, len(days)):
            r = beta * mkt[i] + r2.gauss(0, vol) - 0.15 * (r2.random() < 0.005)  # occasional crash
            o = p * math.exp(r2.gauss(0, vol / 3))
            p = max(1e-6, p * math.exp(r))
            h = max(o, p) * (1 + abs(r2.gauss(0, vol / 2)))
            l = min(o, p) * (1 - abs(r2.gauss(0, vol / 2)))
            ser[days[i]] = (o, h, l, p)
        out[s] = ser
    return out


class Ctx:
    """Aligned OHLC table on a common calendar plus lazily cached indicators.
    c is forward-filled so a held position can be marked every day; o/h/l are None
    on days the asset has no bar (no trading possible on that day)."""

    def __init__(self, prices, market, bench):
        self.days = sorted({d for ser in prices.values() for d in ser})
        self.n = len(self.days)
        self.dates = [date(1970, 1, 1) + timedelta(days=d) for d in self.days]
        self.syms, self.bench, self.market = sorted(prices), bench, market
        self.ppy = MARKET[market]["ppy"]
        self.o, self.h, self.l, self.c, self.live = {}, {}, {}, {}, {}
        for s, ser in prices.items():
            o, h, l, c, live, last = [], [], [], [], [], None
            for d in self.days:
                bar = ser.get(d)
                if bar:
                    last = bar[3]
                o.append(bar[0] if bar else None)
                h.append(bar[1] if bar else None)
                l.append(bar[2] if bar else None)
                c.append(last)
                live.append(bool(bar))
            self.o[s], self.h[s], self.l[s], self.c[s], self.live[s] = o, h, l, c, live
        # calendar helpers: position within month (1-based), trading days left in month
        # (1 = last), last bar of the week, and calendar month id
        self.mpos, self.mrem, self.wend, self.month = [], [], [], []
        for i, dt in enumerate(self.dates):
            self.month.append((dt.year, dt.month))
            self.mpos.append(1 if i == 0 or self.month[i] != self.month[i - 1] else self.mpos[-1] + 1)
            self.wend.append(i + 1 == self.n or self.dates[i + 1].weekday() < dt.weekday())
        for i in range(self.n - 1, -1, -1):
            nxt = 0 if i + 1 == self.n or self.month[i + 1] != self.month[i] else self.mrem[-1]
            self.mrem.append(nxt + 1)
        self.mrem.reverse()
        self._cache = {}

    # -- indicators, each a list aligned to the calendar with None when unavailable
    def ind(self, s, name, n=0):
        k = (s, name, n)
        if k not in self._cache:
            self._cache[k] = getattr(self, "_" + name)(s, n)
        return self._cache[k]

    def _sma(self, s, n):
        c, out, tot, cnt = self.c[s], [None] * self.n, 0.0, 0
        for i in range(self.n):
            if c[i] is None:
                continue
            tot += c[i]
            cnt += 1
            if cnt > n:
                tot -= c[i - n]
            if cnt >= n:
                out[i] = tot / n
        return out

    def _ret(self, s, n):
        c = self.c[s]
        return [c[i] / c[i - n] - 1 if i >= n and c[i - n] else None for i in range(self.n)]

    def _vol(self, s, n):
        r, out = self._ret(s, 1), [None] * self.n
        for i in range(n, self.n):
            win = r[i - n + 1:i + 1]
            if None not in win:
                m = sum(win) / n
                out[i] = math.sqrt(sum((x - m) ** 2 for x in win) / n) or 1e-9
        return out

    def _rsi(self, s, n):
        c, out, gain, loss, cnt = self.c[s], [None] * self.n, 0.0, 0.0, 0
        for i in range(1, self.n):
            if c[i] is None or c[i - 1] is None:
                continue
            ch = c[i] - c[i - 1]
            g, l_ = max(ch, 0), max(-ch, 0)
            cnt += 1
            if cnt <= n:
                gain, loss = gain + g / n, loss + l_ / n
            else:
                gain, loss = (gain * (n - 1) + g) / n, (loss * (n - 1) + l_) / n
            if cnt >= n:
                out[i] = 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
        return out

    def _hh(self, s, n):     # highest close of the PREVIOUS n days (excludes today)
        c, out = self.c[s], [None] * self.n
        for i in range(n, self.n):
            win = c[i - n:i]
            if win[0] is not None:
                out[i] = max(win)
        return out

    def _ll(self, s, n):
        c, out = self.c[s], [None] * self.n
        for i in range(n, self.n):
            win = c[i - n:i]
            if win[0] is not None:
                out[i] = min(win)
        return out

    def _ibs(self, s, n):
        return [(c - l) / (h - l) if h is not None and h > l else (0.5 if h is not None else None)
                for h, l, c in zip(self.h[s], self.l[s], self.c[s])]

    def _streak(self, s, n):  # consecutive down closes ending today
        c, out, k = self.c[s], [0] * self.n, 0
        for i in range(1, self.n):
            k = k + 1 if c[i] is not None and c[i - 1] is not None and c[i] < c[i - 1] else 0
            out[i] = k
        return out

    def _ens(self, s, n):
        """Ensemble Donchian signal in [0,1] (Zarattini, Pagani & Barbon 2025): for each
        lookback L, go long when the close reaches the previous L-day high; trail a stop at
        max(prior stop, channel midpoint); the signal is the average long state."""
        c, out = self.c[s], [None] * self.n
        states = {L: [False, None] for L in ENS_LOOKBACKS}
        from collections import deque
        for i in range(self.n):
            if c[i] is None:
                continue
            votes = []
            for L, st in states.items():
                if i < L or c[i - L] is None:
                    continue
                win = c[i - L:i]
                hh, ll = max(win), min(win)
                mid = (hh + ll) / 2
                if not st[0] and c[i] >= hh:
                    st[0], st[1] = True, mid
                elif st[0]:
                    st[1] = max(st[1], mid)
                    if c[i] < st[1]:
                        st[0], st[1] = False, None
                votes.append(1.0 if st[0] else 0.0)
            if len(votes) >= 3:
                out[i] = sum(votes) / len(votes)
        return out

    def regime(self, i, n):
        """Benchmark above its n-day average (n = 0: always on)."""
        if not n:
            return True
        b, m = self.c[self.bench][i], self.ind(self.bench, "sma", n)[i]
        return b is not None and m is not None and b > m


# ---------------------------------------------------------------- strategy families
# Each family function gets (ctx, i, held, p) at the CLOSE of day i, where held maps
# symbol -> (entry day index, avg entry price), and returns (target, rebalance):
# target = {symbol: weight of equity} to hold from tomorrow's open; rebalance=True
# also resizes existing positions to their weight (else they drift untouched).

def _mr(ctx, i, held, K, exit_fn, score_fn):
    """Mean-reversion helper: keep positions with no exit signal, fill free slots
    with the best-scoring (lowest score) new setups."""
    keep = {s: 1 / K for s in held if not exit_fn(s, *held[s])}
    if len(keep) < K:
        cands = []
        for s in ctx.syms:
            if s not in held and ctx.live[s][i]:
                sc = score_fn(s)
                if sc is not None:
                    cands.append((sc, s))
        for _, s in sorted(cands)[:K - len(keep)]:
            keep[s] = 1 / K
    return keep, False


def fam_rsi2(ctx, i, held, p):
    K = MARKET[ctx.market]["slots"]

    def score(s):
        r, m = ctx.ind(s, "rsi", 2)[i], ctx.ind(s, "sma", p["sma"])[i]
        return r if r is not None and m is not None and r < p["rsi"] and ctx.c[s][i] > m else None

    def exit_(s, e, px):
        r, m5 = ctx.ind(s, "rsi", 2)[i], ctx.ind(s, "sma", 5)[i]
        return i - e + 1 >= p["hold"] or (m5 is not None and ctx.c[s][i] > m5) or (r is not None and r > 70)
    return _mr(ctx, i, held, K, exit_, score)


def fam_ibs(ctx, i, held, p):
    K = MARKET[ctx.market]["slots"]

    def score(s):
        b, m = ctx.ind(s, "ibs")[i], ctx.ind(s, "sma", p["sma"])[i]
        return b if b is not None and m is not None and b < p["ibs"] and ctx.c[s][i] > m else None

    def exit_(s, e, px):
        b, ph = ctx.ind(s, "ibs")[i], ctx.h[s][i - 1]
        return i - e + 1 >= 5 or (ph is not None and ctx.c[s][i] > ph) or (b is not None and b > 0.8)
    return _mr(ctx, i, held, K, exit_, score)


def fam_down_days(ctx, i, held, p):
    K = MARKET[ctx.market]["slots"]

    def score(s):
        k, m = ctx.ind(s, "streak")[i], ctx.ind(s, "sma", p["sma"])[i]
        return -k if k >= p["n"] and m is not None and ctx.c[s][i] > m else None

    def exit_(s, e, px):
        return i - e + 1 >= 5 or ctx.c[s][i] > ctx.c[s][i - 1]
    return _mr(ctx, i, held, K, exit_, score)


def fam_dip_buy(ctx, i, held, p):
    K = MARKET[ctx.market]["slots"]

    def score(s):
        r = ctx.ind(s, "ret", 1)[i]
        return r if r is not None and r <= -p["drop"] and ctx.regime(i, 100) else None

    def exit_(s, e, px):
        return i - e + 1 >= p["hold"] or ctx.c[s][i] >= px * (1 + p["target"])
    return _mr(ctx, i, held, K, exit_, score)


def fam_turn_of_month(ctx, i, held, p):
    """Signal at the close of the `before`-th-to-last day -> filled next open; sell
    signal at the close of trading day `exit_day` -> filled at the next open."""
    a = p["asset"]
    if a not in ctx.c or not ctx.live[a][i]:
        return {}, False
    on = ctx.mrem[i] <= p["before"] or ctx.mpos[i] < p["exit_day"]
    return ({a: 1.0} if on else {}), False


def _rank_top(ctx, i, cands, K):
    cands.sort(reverse=True)
    return {s: 1 / K for _, s in cands[:K]}


def fam_trend_ensemble(ctx, i, held, p):
    K = p["top"]
    if not ctx.wend[i]:
        return {s: 1 / K for s in held}, False
    if not ctx.regime(i, p["regime"]):
        return {}, True
    cands = []
    for s in ctx.syms:
        if not ctx.live[s][i]:
            continue
        rs = [ctx.ind(s, "ret", L)[i] for L in p["lookbacks"]]
        v = ctx.ind(s, "vol", 20)[i]
        if None in rs or v is None:
            continue
        if sum(1 if r > 0 else -1 for r in rs) / len(rs) > 0:
            cands.append((sum(rs) / len(rs) / v, s))
    return _rank_top(ctx, i, cands, K), True


def fam_donchian(ctx, i, held, p):
    K = p["top"]
    if not ctx.wend[i]:
        return {s: 1 / K for s in held}, False
    if not ctx.regime(i, p["regime"]):
        return {}, True
    cands = []
    for s in ctx.syms:
        hh, ll, v = ctx.ind(s, "hh", p["entry"])[i], ctx.ind(s, "ll", p["exit"])[i], ctx.ind(s, "vol", 20)[i]
        if not ctx.live[s][i] or hh is None or ll is None or v is None:
            continue
        c = ctx.c[s][i]
        if (s in held and c >= ll) or (s not in held and c >= hh):
            cands.append(((c / ctx.c[s][i - p["entry"]] - 1) / v, s))
    return _rank_top(ctx, i, cands, K), True


def fam_dual_momentum(ctx, i, held, p):
    K = p["top"]
    if ctx.mrem[i] != 1:
        return {s: 1 / K for s in held}, False
    risk = [s for s in (INDEX_ETFS if p["universe"] == "index" else ETFS) if s in ctx.c and s != "IEF"]

    def mom(s):
        rs = [ctx.ind(s, "ret", L)[i] for L in (252, 126, 63)]
        return None if None in rs else sum(rs) / 3
    safe = mom("IEF") if p["safe"] == "IEF" and "IEF" in ctx.c else 0.0
    if safe is None:
        safe = 0.0
    cands = [(m, s) for s in risk if (m := mom(s)) is not None and m > safe and ctx.live[s][i]]
    target = _rank_top(ctx, i, cands, K)
    if p["safe"] == "IEF" and len(target) < K and "IEF" in ctx.c and ctx.live["IEF"][i]:
        target["IEF"] = (K - len(target)) / K
    return target, True


ENS_LOOKBACKS = (5, 10, 20, 30, 60, 90, 150, 250, 360)


def fam_ens_donchian(ctx, i, held, p):
    """Ensemble-Donchian trend with volatility targeting, long-only, no leverage.
    uni: BTC only, BTC+ETH, or the top-N assets by (signal x 20-day momentum)."""
    if p["uni"] in ("BTC", "BTC+ETH"):
        names = [x for x in p["uni"].split("+") if x in ctx.c]
    else:
        n = int(p["uni"][3:])
        cands = []
        for s in ctx.syms:
            sig, r = ctx.ind(s, "ens")[i], ctx.ind(s, "ret", 20)[i]
            if ctx.live[s][i] and sig and r is not None:
                cands.append((sig * (1 + r), s))
        names = [s for _, s in sorted(cands, reverse=True)[:n]]
    if not names:
        return {}, True
    target = {}
    for s in names:
        sig, v = ctx.ind(s, "ens")[i], ctx.ind(s, "vol", 90)[i]
        if not sig or v is None or not ctx.live[s][i]:
            continue
        ann = v * math.sqrt(ctx.ppy)
        scale = 1.0 if p["tv"] is None else min(1.0, p["tv"] / ann)
        w = sig * scale / len(names)
        if w >= 0.02:
            target[s] = w
    return target, True


FAMILIES = [
    {"name": "rsi2_meanrev", "fn": fam_rsi2, "markets": ("crypto", "stocks"),
     "grid": {"rsi": [5, 10, 15], "sma": [100, 200], "hold": [5, 10]}},
    {"name": "ibs", "fn": fam_ibs, "markets": ("crypto", "stocks"),
     "grid": {"ibs": [0.1, 0.2], "sma": [100, 200]}},
    {"name": "down_days", "fn": fam_down_days, "markets": ("crypto", "stocks"),
     "grid": {"n": [3, 4], "sma": [100, 200]}},
    {"name": "turn_of_month", "fn": fam_turn_of_month, "markets": ("crypto", "stocks"),
     "grid": {"asset": {"crypto": ["BTC", "ETH"], "stocks": ["SPY", "QQQ"]},
              "before": [4, 5], "exit_day": [3, 4]}},
    {"name": "trend_ensemble", "fn": fam_trend_ensemble, "markets": ("crypto", "stocks"),
     "grid": {"lookbacks": [(10, 20, 50), (10, 20, 50, 100)], "top": [2, 3, 5],
              "regime": [0, 50, 100, 200]}},
    {"name": "donchian_rotation", "fn": fam_donchian, "markets": ("crypto", "stocks"),
     "grid": {"entry": [10, 20], "exit": [5, 10], "top": [2, 3], "regime": [100, 200]}},
    {"name": "dual_momentum", "fn": fam_dual_momentum, "markets": ("stocks",),
     "grid": {"top": [1, 2, 3], "safe": ["IEF", "cash"], "universe": ["index", "all"]}},
    {"name": "ens_donchian", "fn": fam_ens_donchian, "markets": ("crypto",),
     "grid": {"uni": ["BTC", "BTC+ETH", "top2", "top4"], "tv": [0.25, 0.5, None]}},
    {"name": "dip_buy_crypto", "fn": fam_dip_buy, "markets": ("crypto",),
     "grid": {"drop": [0.07, 0.10, 0.15], "hold": [1, 3, 5], "target": [0.05, 0.10]}},
]


def grid(fam, market):
    g = {k: (v[market] if isinstance(v, dict) else v) for k, v in fam["grid"].items()}
    return [dict(zip(g, combo)) for combo in itertools.product(*g.values())]


def pstr(p):
    return ",".join(f"{k}={'/'.join(map(str, v)) if isinstance(v, tuple) else v}" for k, v in p.items())


# ---------------------------------------------------------------- simulation
def simulate(ctx, fn, p, start, end, cost):
    """Start flat with equity 1.0 at day `start`; return per-day returns, per-day
    invested fraction, and closed trades (net return each). Orders decided at the
    close of day i are filled at the open of day i+1."""
    cash, pos = 1.0, {}          # pos: sym -> {"u": units, "basis": cost paid, "real": proceeds so far, "e": entry i, "px": avg px}
    pending, reb = {}, False
    rets, expo, trades, eq_prev = [], [], [], 1.0
    for i in range(start, end):
        # 1) fills at today's open
        o = {s: ctx.o[s][i] for s in set(pos) | set(pending)}
        for s in list(pos):                                  # exits first (frees cash)
            if s not in pending and o[s]:
                pr = pos[s]["u"] * o[s] * (1 - cost)
                cash += pr
                trades.append((pos[s]["real"] + pr) / pos[s]["basis"] - 1)
                del pos[s]
        eq_open = cash + sum(x["u"] * (o[s] or ctx.c[s][i]) for s, x in pos.items())
        tol = 0.02 * eq_open
        if reb:                                              # resize survivors toward target
            for s, x in pos.items():
                if not o[s]:
                    continue
                delta = pending[s] * eq_open - x["u"] * o[s]
                if delta < -tol:
                    frac = -delta / (x["u"] * o[s])
                    pr = x["u"] * frac * o[s] * (1 - cost)
                    cash += pr                       # proceeds of the trim go back to cash
                    x["real"] += pr
                    x["u"] *= 1 - frac
                elif delta > tol and cash > tol:
                    amt = min(delta, cash)
                    cash -= amt
                    x["u"] += amt * (1 - cost) / o[s]
                    x["basis"] += amt
                    x["px"] = x["basis"] * (1 - cost) / x["u"]
        for s, w in pending.items():                         # new entries
            if s in pos or not o[s]:
                continue
            amt = min(w * eq_open, cash)
            if amt < 0.01 * eq_open:
                continue
            cash -= amt
            u = amt * (1 - cost) / o[s]
            pos[s] = {"u": u, "basis": amt, "real": 0.0, "e": i, "px": amt / u}
        # 2) mark to close
        eq = cash + sum(x["u"] * ctx.c[s][i] for s, x in pos.items())
        rets.append(eq / eq_prev - 1)
        expo.append(1 - cash / eq)
        eq_prev = eq
        # 3) decide tomorrow's orders from today's close
        held = {s: (x["e"], x["px"]) for s, x in pos.items()}
        pending, reb = fn(ctx, i, held, p)
    return rets, expo, trades


def hold_bench(ctx, start, end, cost):
    """Buy the benchmark at the first open of the span, hold to the end."""
    c, o = ctx.c[ctx.bench], ctx.o[ctx.bench]
    o0 = next((o[i] for i in range(start, end) if o[i]), None)
    eq_prev, rets = 1.0, []
    for i in range(start, end):
        eq = c[i] / o0 * (1 - cost) if o0 and c[i] else 1.0
        rets.append(eq / eq_prev - 1)
        eq_prev = eq
    return rets, [1.0] * len(rets), [eq_prev * (1 - cost) - 1]


def sharpe(rets, ppy):
    n = len(rets)
    if n < 20:
        return -9.0
    m = sum(rets) / n
    sd = math.sqrt(sum((r - m) ** 2 for r in rets) / n)
    return m / sd * math.sqrt(ppy) if sd > 0 else 0.0


def stats(rets, expo, trades, months, ppy):
    """months = calendar month id per day, aligned with rets."""
    n = len(rets)
    eq, peak, mdd, curve = 1.0, 1.0, 0.0, []
    for r in rets:
        eq *= 1 + r
        curve.append(eq)
        peak = max(peak, eq)
        mdd = max(mdd, 1 - eq / peak)
    by_month, cur, last = [], 1.0, None
    for r, m in zip(rets, months):
        if m != last and last is not None:
            by_month.append(cur - 1)
            cur = 1.0
        cur *= 1 + r
        last = m
    by_month.append(cur - 1)
    n_months = n / ppy * 12
    return {"total": eq - 1, "cagr": eq ** (ppy / n) - 1 if n else 0.0,
            "monthly": sum(by_month) / len(by_month), "mdd": mdd, "sharpe": sharpe(rets, ppy),
            "trades_mo": len(trades) / n_months if n_months else 0.0,
            "win": sum(1 for t in trades if t > 0) / len(trades) if trades else float("nan"),
            "expo": sum(expo) / n if n else 0.0, "n_trades": len(trades), "days": n}


def fmt(name, st, extra=""):
    return (f"{name:<22} {st['cagr']:>+7.1%} {st['monthly']:>+7.2%} {st['mdd']:>6.1%} {st['sharpe']:>6.2f} "
            f"{st['trades_mo']:>6.1f} {st['win']:>5.0%} {st['expo']:>5.0%} {extra}")


HDR = f"{'family':<22} {'CAGR':>7} {'avg/mo':>7} {'maxDD':>6} {'Sharpe':>6} {'trd/mo':>6} {'win%':>5} {'expo':>5}"


# ---------------------------------------------------------------- walk-forward
def windows(ctx):
    """(train_start, test_start, test_end) index triples, stepping by STEP_M months."""
    starts = [i for i in range(ctx.n) if i == 0 or ctx.month[i] != ctx.month[i - 1]]
    out, k = [], 0
    while k + TRAIN_M < len(starts):
        te = starts[k + TRAIN_M + TEST_M] if k + TRAIN_M + TEST_M < len(starts) else ctx.n
        if te - starts[k + TRAIN_M] >= 20:
            out.append((starts[k], starts[k + TRAIN_M], te))
        k += STEP_M
    return out


def run_market(market, years, cost, synthetic):
    m = MARKET[market]
    syms = sorted(set(m["syms"]) | {m["bench"]})
    cost = m["cost"] if cost is None else cost
    print(f"=== {market}: loading {len(syms)} symbols, {years} years of daily bars ===")
    if synthetic:
        print("*** SYNTHETIC DATA: tests the code only ***")
        prices = load_synthetic(syms, years, market)
    else:
        prices = load_crypto(syms, years) if market == "crypto" else load_stocks(syms, years)
    if m["bench"] not in prices:
        raise SystemExit(f"benchmark {m['bench']} missing")
    ctx = Ctx(prices, market, m["bench"])
    wins = windows(ctx)
    if not wins:
        raise SystemExit("not enough history for one walk-forward window")
    oos0 = wins[0][1]
    print(f"{len(ctx.syms)} assets, {ctx.n} days {ctx.dates[0]} .. {ctx.dates[-1]}; cost {cost:.2%} per side")
    print(f"walk-forward: train {TRAIN_M}m -> test {TEST_M}m, step {STEP_M}m: {len(wins)} windows; "
          f"out-of-sample span {ctx.dates[oos0]} .. {ctx.dates[-1]} ({ctx.n - oos0} days)")
    print("(first ~200 days are indicator warm-up; survivorship caveat: universe = assets listed today)\n")

    oos, insample, picks = {}, {}, {}
    t0 = time.time()
    for fam in FAMILIES:
        if market not in fam["markets"]:
            continue
        name, fn = fam["name"], fam["fn"]
        full = []                       # one full-history run per variant (used for training slices + in-sample table)
        for p in grid(fam, market):
            rets, expo, trades = simulate(ctx, fn, p, 0, ctx.n, cost)
            full.append((p, rets, expo, trades))
        rets_o, expo_o, trades_o, picks[name] = [], [], [], []
        for ts0, te0, te1 in wins:
            best = max(full, key=lambda f: (sharpe(f[1][ts0:te0], ctx.ppy), -full.index(f)))
            p = best[0]
            r, e, t = simulate(ctx, fn, p, te0, te1, cost)        # fresh, flat start on unseen data
            rets_o += r
            expo_o += e
            trades_o += t
            picks[name].append((te0, te1, p, sharpe(best[1][ts0:te0], ctx.ppy), math.prod(1 + x for x in r) - 1))
        oos[name] = (rets_o, expo_o, trades_o)
        best_is = max(full, key=lambda f: sharpe(f[1], ctx.ppy))
        insample[name] = (best_is[0], stats(best_is[1], best_is[2], best_is[3], ctx.month, ctx.ppy))
        print(f"  {name}: {len(full)} variants x {len(wins)} windows done ({time.time() - t0:.0f}s)")

    # ---- report
    months = ctx.month[oos0:]
    bench = stats(*hold_bench(ctx, oos0, ctx.n, cost), months, ctx.ppy)
    print(f"\n--- OUT-OF-SAMPLE (stitched walk-forward test windows, params re-picked each window) ---")
    print(HDR)
    print("-" * len(HDR))
    ranked = sorted(oos, key=lambda k: sharpe(oos[k][0], ctx.ppy), reverse=True)
    results = {}
    for name in ranked:
        st = stats(*oos[name], months, ctx.ppy)
        results[name] = st
        print(fmt(name, st, "<- beats hold" if st["total"] > bench["total"] else ""))
    print(fmt(f"hold {m['bench']}", bench))

    print(f"\n--- per-window picks (chosen on the prior {TRAIN_M} months by Sharpe; 'test' = return on the unseen window) ---")
    for name in ranked:
        print(f"{name}:")
        for te0, te1, p, sh, ret in picks[name]:
            print(f"    {ctx.dates[te0]} .. {ctx.dates[te1 - 1]}  train Sharpe {sh:>5.2f}  test {ret:>+7.1%}  [{pstr(p)}]")

    print(f"\n--- IN-SAMPLE: best single fixed variant per family over FULL history {ctx.dates[0]} .. {ctx.dates[-1]} "
          f"(optimistic: picked with hindsight, not comparable to the OOS table) ---")
    print(HDR)
    print("-" * len(HDR))
    for name in ranked:
        p, st = insample[name]
        print(fmt(name, st, f"[{pstr(p)}]"))

    best = ranked[0]
    out = {"market": market, "family": best, "days": ctx.days[oos0:], "rets": oos[best][0]}
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(f"{RESULTS_DIR}/lab_oos_{market}.json", "w") as f:
        json.dump(out, f)
    print(f"\nbest OOS family by Sharpe: {best} (curve saved to {RESULTS_DIR}/lab_oos_{market}.json)")
    return out


def combined(a, b):
    """50/50 of two OOS curves, rebalanced daily on the union calendar (a leg with no
    bar that day returns 0). Reported on a calendar-day basis (365/yr)."""
    ra, rb = dict(zip(a["days"], a["rets"])), dict(zip(b["days"], b["rets"]))
    lo, hi = max(min(ra), min(rb)), min(max(ra), max(rb))
    days = [d for d in sorted(set(ra) | set(rb)) if lo <= d <= hi]
    rets = [0.5 * ra.get(d, 0.0) + 0.5 * rb.get(d, 0.0) for d in days]
    months = [((date(1970, 1, 1) + timedelta(days=d)).year, (date(1970, 1, 1) + timedelta(days=d)).month) for d in days]
    st = stats(rets, [1.0] * len(rets), [], months, 365)
    print(f"\n--- COMBINED 50/50 {a['market']}:{a['family']} + {b['market']}:{b['family']} "
          f"(daily rebalanced, {len(days)} common days) ---")
    print(f"CAGR {st['cagr']:+.1%}  avg/mo {st['monthly']:+.2%}  maxDD {st['mdd']:.1%}  Sharpe {st['sharpe']:.2f}  "
          f"total {st['total']:+.1%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["crypto", "stocks", "both"], default="crypto")
    ap.add_argument("--cost", type=float, default=None, help="per-side cost; default crypto 0.005, stocks 0.0003")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    markets = ["crypto", "stocks"] if a.market == "both" else [a.market]
    outs = {}
    for mk in markets:
        outs[mk] = run_market(mk, a.years, a.cost, a.synthetic)
    other = "stocks" if a.market == "crypto" else "crypto"
    if a.market != "both" and os.path.exists(f"{RESULTS_DIR}/lab_oos_{other}.json"):   # combine with the other market's last run
        with open(f"{RESULTS_DIR}/lab_oos_{other}.json") as f:
            outs[other] = json.load(f)
    if len(outs) == 2:
        combined(outs["crypto"], outs["stocks"])


if __name__ == "__main__":
    main()
