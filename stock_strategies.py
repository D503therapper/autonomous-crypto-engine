"""Live versions of the strongest stock families from the walk-forward lab (lab.py,
results/lab_stocks.txt, 2018-2026 daily bars, out-of-sample 2020-03 .. 2026-09):

    dual_momentum    +25.6%/yr  maxDD 24.8%  Sharpe 1.20   (monthly, index ETFs vs IEF)
    trend_ensemble   +31.1%/yr  maxDD 38.7%  Sharpe 1.06   (weekly, 10/20/50/100-day trend, SPY regime)
    hold SPY         +17.3%/yr  maxDD 28.3%  Sharpe 0.90

Both are TARGET-WEIGHT strategies: on a rebalance the class hands the engine
{symbol: fraction of equity} through `targets(sig)` and engine.rebalance_to() sells what
dropped out, trims / tops up what stayed and buys what is new - the same portfolio
mechanics as lab.simulate() on a rebalance day (2%-of-equity tolerance).

Daily closes come from Yahoo's hourly bars exactly as the official rsi2 account does
(strategy._daily_closes: one close per UTC date, the current unfinished day dropped), so
at the first cycle of a new week / month the signal is computed on the last COMPLETED
close of the previous period, which is the lab's "signal at the close of the last bar,
fill at the next open" (live: filled at the first hourly cycle after the open, ~10:00 ET).

Parity with lab.py's family functions is checked offline in stock_strategies_test.py.
"""
import config
from lab import INDEX_ETFS
from strategy import _base, _daily_closes


def _ret(closes, n):
    """closes[-1] / closes[-1-n] - 1 the way lab.Ctx._ret computes it; None if too short."""
    return closes[-1] / closes[-1 - n] - 1 if len(closes) > n and closes[-1 - n] else None


def _vol(closes, n=20):
    """Population std of the last n one-day returns (lab.Ctx._vol); None if too short."""
    if len(closes) < n + 1:
        return None
    r = [closes[j] / closes[j - 1] - 1 for j in range(len(closes) - n, len(closes))]
    m = sum(r) / n
    return (sum((x - m) ** 2 for x in r) / n) ** 0.5 or 1e-9


def _sma(closes, n):
    return sum(closes[-n:]) / n if n and len(closes) >= n else None


def _top(cands, k):
    """lab._rank_top: best score first, ties broken like the lab (tuple sort, reverse)."""
    cands.sort(reverse=True)
    return {s: 1 / k for _, s in cands[:k]}


class _TargetWeightStrategy:
    """Common plumbing: engine.step gates on `weekly` + `rebalance_key`, then calls
    targets(sig) instead of its own entry / rotate logic. manage() never exits between
    rebalances (the lab families hold untouched between rebalance days; no stops)."""
    weekly = True
    rebalance_key = "%G-%V"

    def manage(self, pos, s, now, rebalance=False):
        return None

    @staticmethod
    def _live(sig):
        """Symbols whose last completed daily close is the latest date seen across the
        universe (lab: ctx.live[s][i] - the asset had a bar on the signal day)."""
        if not sig:
            return set()
        last = max(s["day"] for s in sig.values())
        return {c for c, s in sig.items() if s["day"] == last}


class DualMomentum(_TargetWeightStrategy):
    """Lab family dual_momentum: on the last trading day of each month rank the index ETFs
    (SPY QQQ IWM DIA EFA EEM GLD TLT) by the average of their 12-, 6- and 3-month returns
    (252/126/63 trading days), keep the top N whose momentum beats IEF's, equal weight;
    every slot that finds no ETF beating IEF is held in IEF instead.

    Params = the walk-forward's current pick [top=2,safe=IEF,universe=index] (results/
    lab_stocks.txt): chosen for the last three 6-month windows in a row (2025-09 .. 2026-08,
    train Sharpe 1.29 / 2.14), i.e. what the walk-forward procedure itself would be trading
    now. universe=index was picked in 8 of 13 windows, top=2 is the modal / median top-N
    (top=1 is a 100% single-ETF bet; top=3 dilutes), IEF beat cash in every recent window.
    Needs ~253 completed daily closes: min_candles below makes run_live fetch about a
    year of hourly bars (YahooClient period cap 729d, so there is room)."""
    name = "dual_momentum"
    rebalance_key = "%Y-%m"          # first cycle of a new month = lab's fill at the next open
    LOOKBACKS = (252, 126, 63)

    def __init__(self, bars_per_day, top_n=2, safe="IEF", universe="index"):
        risk = INDEX_ETFS if universe == "index" else config.STOCK_ETFS
        self.risk = [s for s in risk if s != "IEF"]
        self.safe, self.max_positions, self.bpd = safe, top_n, bars_per_day
        self.universe = sorted(set(self.risk) | ({"IEF"} if safe == "IEF" else set()))
        self.regime_days = 0        # no benchmark regime in this family
        self.min_candles = (max(self.LOOKBACKS) + 8) * bars_per_day
        self.window = self.min_candles + 2 * bars_per_day
        self.position_pct = self.max_position_pct = (1 - config.MIN_CASH_RESERVE_PCT) / top_n

    def analyze(self, candles, market_ok=True):
        if not candles:
            return None
        daily = _daily_closes(candles)
        if not daily:
            return None
        closes = [x[1] for x in daily[-(max(self.LOOKBACKS) + 2):]]
        rs = [_ret(closes, L) for L in self.LOOKBACKS]
        mom = None if None in rs else sum(rs) / len(rs)
        sig = _base(candles)
        sig.update(rank=mom if mom is not None else -9.0, buy=mom is not None and mom > 0,
                   stop=0.0, mom=mom, day=daily[-1][0])
        return sig

    def targets(self, sig):
        """lab.fam_dual_momentum at a month end, on the completed closes in `sig`."""
        live, K = self._live(sig), self.max_positions
        safe = sig["IEF"]["mom"] if self.safe == "IEF" and "IEF" in sig else 0.0
        if safe is None:
            safe = 0.0
        cands = [(s["mom"], c) for c, s in sig.items()
                 if c in self.risk and s["mom"] is not None and s["mom"] > safe and c in live]
        target = _top(cands, K)
        if self.safe == "IEF" and len(target) < K and "IEF" in live:
            target["IEF"] = (K - len(target)) / K
        return target


class TrendEnsemble(_TargetWeightStrategy):
    """Lab family trend_ensemble: at each week's last close, while SPY is above its
    200-day average, score every name by the average of its 10/20/50/100-day returns
    divided by 20-day volatility, require a majority of those returns positive, hold the
    top K equal weight; below the SPY average hold cash.

    Params = [lookbacks=10/20/50/100,top=5,regime=200]: the most frequently picked exact
    variant in the walk-forward (4 of 13 windows) and the best fixed variant over the full
    2018-2026 history (+29.0%/yr, maxDD 20.7%, Sharpe 1.32 - the lowest drawdown of any
    trend pick). The other recurring pick, [10/20/50,top=2,regime=0], has no regime filter
    and two slots: higher return in bull windows, -20.6% in the 2022 window. The latest
    window's pick (regime=50) is the same variant with a faster seatbelt.
    The SPY regime is computed from SPY's own daily closes inside this class (SPY is in the
    universe), not from the engine's hourly market_ok, so it matches the lab's definition."""
    name = "trend_ensemble"

    def __init__(self, universe, bars_per_day, lookbacks=(10, 20, 50, 100), top_n=5, regime_days=200,
                 bench="SPY"):
        self.universe = sorted(set(universe) | {bench})
        self.lookbacks, self.max_positions, self.regime_days, self.bench = tuple(lookbacks), top_n, regime_days, bench
        self.bpd = bars_per_day
        self.min_candles = (max(max(lookbacks), regime_days, 21) + 8) * bars_per_day
        self.window = self.min_candles + 2 * bars_per_day
        self.position_pct = self.max_position_pct = (1 - config.MIN_CASH_RESERVE_PCT) / top_n

    def analyze(self, candles, market_ok=True):
        if not candles:
            return None
        daily = _daily_closes(candles)
        if not daily:
            return None
        n = max(max(self.lookbacks), self.regime_days, 21) + 2
        closes = [x[1] for x in daily[-n:]]
        rs = [_ret(closes, L) for L in self.lookbacks]
        v = _vol(closes, 20)
        score = None
        if None not in rs and v is not None:
            votes = sum(1 if r > 0 else -1 for r in rs) / len(rs)
            score = sum(rs) / len(rs) / v if votes > 0 else None
        sma = _sma(closes, self.regime_days)
        sig = _base(candles)
        sig.update(rank=score if score is not None else -9.0, buy=score is not None, stop=0.0,
                   score=score, day=daily[-1][0],
                   # own-close regime (used only for the benchmark's sig): lab.Ctx.regime
                   above_avg=True if not self.regime_days else (sma is not None and closes[-1] > sma))
        return sig

    def targets(self, sig):
        """lab.fam_trend_ensemble at a week end, on the completed closes in `sig`."""
        b = sig.get(self.bench)
        if self.regime_days and not (b and b["above_avg"]):
            return {}
        live = self._live(sig)
        cands = [(s["score"], c) for c, s in sig.items() if c in live and s["score"] is not None]
        return _top(cands, self.max_positions)
