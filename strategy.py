"""Trading strategies. Each one decides entries (analyze) and exits (manage);
the engine handles money, fees, sizing and the drawdown breaker for all of them."""
import time

import config
from indicators import atr, ema, rsi

HOUR = 3_600_000


def _base(candles):
    return {"price": candles[-1]["c"], "high": candles[-1]["h"],
            "low": candles[-1]["l"], "t": candles[-1]["t"]}


def _stop_check(pos, s):
    """Exit at the stop if this candle traded through it (gap-downs fill at the close)."""
    if s["low"] <= pos["stop"]:
        return 1.0, min(pos["stop"], s["price"]) if s["price"] < pos["stop"] else pos["stop"], "stop hit"
    return None


class TrendFollower:
    """Ride multi-day uptrends; trailing ATR stop."""
    name = "trend"
    min_candles = config.EMA_TREND + 5
    window = config.EMA_TREND + 30
    weekly = False

    def __init__(self, universe):
        self.universe = universe

    def analyze(self, candles, market_ok=True):
        if len(candles) < self.min_candles:
            return None
        closes = [c["c"] for c in candles]
        f, s, t = ema(closes, config.EMA_FAST), ema(closes, config.EMA_SLOW), ema(closes, config.EMA_TREND)
        r, a = rsi(closes, config.RSI_PERIOD), atr(candles, config.ATR_PERIOD)
        price = closes[-1]
        lb = min(config.MOMENTUM_LOOKBACK, len(closes) - 1)
        uptrend = price > t[-1] and f[-1] > s[-1] and t[-1] > t[-24]
        fresh_cross = any(f[-i - 1] <= s[-i - 1] and f[-i] > s[-i] for i in range(1, 7))
        sig = _base(candles)
        sig.update(atr=a[-1], rank=closes[-1] / closes[-1 - lb] - 1,
                   buy=uptrend and (fresh_cross or price <= f[-1] * 1.03) and r[-1] < config.RSI_MAX_ENTRY,
                   stop=price - config.STOP_ATR_MULT * a[-1],
                   trend_broken=f[-1] < s[-1] and price < s[-1])
        return sig

    def manage(self, pos, s, now, rebalance=False):
        hit = _stop_check(pos, s)
        if hit:
            return hit
        if s["trend_broken"]:
            return 1.0, s["price"], "trend reversed"
        action = None
        if not pos["took_profit"] and s["price"] >= pos["entry"] + config.TAKE_PROFIT_ATR_MULT * s["atr"]:
            pos["took_profit"] = True
            pos["stop"] = max(pos["stop"], pos["entry"])
            action = 0.5, s["price"], "take half profit"
        pos["peak"] = max(pos["peak"], s["high"])
        pos["stop"] = max(pos["stop"], pos["peak"] - config.TRAIL_ATR_MULT * s["atr"])
        return action


class BreakoutHunter:
    """Catch a pump early: volume spike + breakout above the recent high while the
    coin is still only modestly up. Bank half at +10%, trail the rest, cut at -5%."""
    name = "breakout"
    min_candles = 100
    window = 130
    weekly = False
    B = config.BREAKOUT

    def __init__(self, universe):
        self.universe = universe

    def analyze(self, candles, market_ok=True):
        if len(candles) < self.min_candles:
            return None
        b = self.B
        closes = [c["c"] for c in candles]
        vols = [c["v"] * c["c"] for c in candles]            # volume in USD
        base_vol = sum(vols[-1 - b["vol_lookback"]:-1]) / b["vol_lookback"]
        recent_vol = sum(vols[-b["vol_window"]:]) / b["vol_window"]
        surge = recent_vol / base_vol if base_vol else 0
        prior_high = max(c["h"] for c in candles[-1 - b["breakout_lookback"]:-1])
        price = closes[-1]
        change_24h = price / closes[-25] - 1
        liquid = base_vol * 24 >= b["min_daily_usd_volume"]
        sig = _base(candles)
        sig.update(rank=surge, surge=surge, change_24h=change_24h,
                   buy=(market_ok and liquid and surge >= b["vol_surge"] and price > prior_high
                        and change_24h < b["max_24h_gain"]),
                   stop=price * (1 - b["stop_loss"]))
        return sig

    def manage(self, pos, s, now, rebalance=False):
        b = self.B
        hit = _stop_check(pos, s)
        if hit:
            return hit
        pos["peak"] = max(pos["peak"], s["high"])
        if not pos["took_profit"] and s["high"] >= pos["entry"] * (1 + b["take_profit"]):
            pos["took_profit"] = True
            pos["stop"] = max(pos["stop"], pos["entry"] * 1.01)   # rest can't turn into a loss
            return 0.5, pos["entry"] * (1 + b["take_profit"]), f"secured +{b['take_profit']:.0%}"
        if pos["took_profit"]:
            pos["stop"] = max(pos["stop"], pos["peak"] * (1 - b["trail"]))
        if not pos["took_profit"] and now - pos["opened"] >= b["max_hold_hours"] * HOUR:
            return 1.0, s["price"], "time stop: no move"
        return None


class WeeklyMomentum:
    """Time-series momentum, rebalanced weekly: hold assets whose own ~3-week and
    1-week returns are positive, while the market benchmark is in an uptrend.
    Low turnover keeps fees small. Wide trailing stop guards against crashes."""
    name = "momentum"
    weekly = True
    M = config.MOMENTUM

    def __init__(self, universe, bars_per_day, market):
        self.universe = universe
        self.lb = self.M["lookback_days"] * bars_per_day
        self.cf = self.M["confirm_days"] * bars_per_day
        self.trail = self.M["trail_stop"][market]
        self.min_candles = self.lb + 1
        self.window = self.lb + 5
        # Equal-weight slots: momentum's edge comes from being invested in trends,
        # so it is sized by slot rather than by the (deliberately wide) stop.
        self.position_pct = (1 - config.MIN_CASH_RESERVE_PCT) / config.MAX_POSITIONS

    def analyze(self, candles, market_ok=True):
        if len(candles) < self.min_candles:
            return None
        closes = [c["c"] for c in candles]
        price = closes[-1]
        r_long = price / closes[-1 - self.lb] - 1
        r_short = price / closes[-1 - self.cf] - 1
        rets = [closes[i] / closes[i - 1] - 1 for i in range(len(closes) - self.lb, len(closes))]
        vol = (sum(r * r for r in rets) / len(rets)) ** 0.5 or 1e-9
        sig = _base(candles)
        sig.update(rank=r_long / vol, momentum_lost=r_long < 0 or not market_ok,
                   buy=market_ok and r_long > 0 and r_short > 0,
                   stop=price * (1 - self.trail))
        return sig

    def manage(self, pos, s, now, rebalance=False):
        hit = _stop_check(pos, s)
        if hit:
            return hit
        if rebalance and s["momentum_lost"]:
            return 1.0, s["price"], "weekly rebalance: momentum gone"
        pos["peak"] = max(pos["peak"], s["high"])
        pos["stop"] = max(pos["stop"], pos["peak"] * (1 - self.trail))
        return None


class DonchianRotation:
    """Tournament winner (crypto, Sep 2026): every 7 days, hold the top-N coins that
    closed at a 10-day high (ranked by 10-day return / volatility); drop a coin when it
    closes below its 5-day low. Only while BTC is above its 100-day average.
    Out-of-sample 2025-26: +85% vs BTC -17.5%, max drawdown 33%. Uses daily closes."""
    name = "breakout10"
    weekly = True

    def __init__(self, universe, bars_per_day, lookback=10, top_n=2, regime_days=100):
        self.universe, self.bpd, self.L, self.max_positions = universe, bars_per_day, lookback, top_n
        self.regime_days = regime_days
        self.min_candles = (lookback + 21) * bars_per_day + 1
        self.window = self.min_candles + bars_per_day
        self.position_pct = self.max_position_pct = (1 - config.MIN_CASH_RESERVE_PCT) / top_n

    def analyze(self, candles, market_ok=True):
        if len(candles) < self.min_candles:
            return None
        # daily closes: every bars_per_day-th close counting back from the latest bar
        d = [c["c"] for c in candles[::-1][::self.bpd]][::-1]
        L, price = self.L, d[-1]
        rets = [d[j] / d[j - 1] - 1 for j in range(len(d) - 20, len(d))]
        vol = (sum(r * r for r in rets) / 20) ** 0.5 or 1e-9
        sig = _base(candles)
        sig.update(rank=(price / d[-1 - L] - 1) / vol,
                   buy=market_ok and price >= max(d[-1 - L:-1]),
                   exit=(not market_ok) or price < min(d[-1 - max(2, L // 2):-1]),
                   stop=0.0)   # no fixed stop: exits are weekly, as tested
        return sig

    def manage(self, pos, s, now, rebalance=False):
        if rebalance and s["exit"]:
            return 1.0, s["price"], "weekly: fell below 5-day low or BTC trend down"
        return None


class MomentumRotation:
    """Tournament pick (stocks, Sep 2026): each trading day, hold the top-N stocks by
    10-day return / volatility among those with positive 10-day momentum, while SPY is
    above its 200-day average. Out-of-sample 2024-26: +98% vs SPY +81.5% (weak evidence:
    1 of 15 top variants beat SPY). Uses daily closes."""
    name = "rotation10"
    weekly = True           # engine rebalances once per period (see rebalance_key)
    rebalance_key = "%Y-%m-%d"
    rotate = True           # engine sells holdings that drop out of the top N

    def __init__(self, universe, bars_per_day, lookback=10, top_n=2, regime_days=200):
        self.universe, self.bpd, self.L, self.max_positions = universe, bars_per_day, lookback, top_n
        self.regime_days = regime_days
        self.min_candles = (lookback + 21) * bars_per_day + 1
        self.window = self.min_candles + bars_per_day
        self.position_pct = self.max_position_pct = (1 - config.MIN_CASH_RESERVE_PCT) / top_n

    def analyze(self, candles, market_ok=True):
        if len(candles) < self.min_candles:
            return None
        d = [c["c"] for c in candles[::-1][::self.bpd]][::-1]
        mom = d[-1] / d[-1 - self.L] - 1
        rets = [d[j] / d[j - 1] - 1 for j in range(len(d) - 20, len(d))]
        vol = (sum(r * r for r in rets) / 20) ** 0.5 or 1e-9
        sig = _base(candles)
        sig.update(rank=mom / vol, buy=market_ok and mom > 0, stop=0.0)
        return sig

    def manage(self, pos, s, now, rebalance=False):
        return None


def _daily_closes(candles, include_today=False):
    """Collapse intraday bars into one close per UTC date (US sessions sit in one UTC day).
    Drops the current, unfinished day unless include_today."""
    out, last_day = [], None
    for c in candles:
        day = c["t"] // 86_400_000
        if day != last_day:
            out.append([day, c["c"]])
            last_day = day
        else:
            out[-1][1] = c["c"]
    if not include_today and out:
        out = out[:-1]
    return out


def _rsi_last(closes, n=2):
    """Wilder RSI of the last close."""
    gain = loss = 0.0
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        g, l_ = max(ch, 0), max(-ch, 0)
        if i <= n:
            gain += g / n
            loss += l_ / n
        else:
            gain = (gain * (n - 1) + g) / n
            loss = (loss * (n - 1) + l_) / n
    return 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)


class RSI2MeanReversion:
    """Lab winner (stocks, Sep 2026; walk-forward 2018-2026 out-of-sample +20%/yr, max
    drawdown 21%, vs SPY +17%/28%). Once a day, using completed daily closes: buy up to
    5 names whose RSI(2) < 15 while above their 200-day average (lowest RSI first); sell
    when the close is back above the 5-day average, RSI(2) > 70, or after 10 trading days."""
    name = "rsi2"
    weekly = True
    rebalance_key = "%Y-%m-%d"      # evaluate once per trading day (first cycle after the open)

    def __init__(self, universe, bars_per_day, rsi_max=15, sma=200, hold=10, slots=5):
        self.universe, self.bpd = universe, bars_per_day
        self.rsi_max, self.sma, self.hold, self.max_positions = rsi_max, sma, hold, slots
        self.min_candles = (sma + 15) * bars_per_day
        self.window = self.min_candles + 2 * bars_per_day
        self.position_pct = self.max_position_pct = (1 - config.MIN_CASH_RESERVE_PCT) / slots

    def analyze(self, candles, market_ok=True):
        daily = _daily_closes(candles)
        if len(daily) < self.sma + 5:
            return None
        closes = [x[1] for x in daily[-(self.sma + 40):]]
        last = closes[-1]
        r = _rsi_last(closes[-40:])
        sma_long = sum(closes[-self.sma:]) / self.sma
        sma5 = sum(closes[-5:]) / 5
        sig = _base(candles)
        sig.update(rank=-r, buy=r < self.rsi_max and last > sma_long, stop=0.0,
                   exit=last > sma5 or r > 70, day=daily[-1][0])
        return sig

    def manage(self, pos, s, now, rebalance=False):
        if not rebalance:
            return None
        held_days = s["day"] - pos["opened"] // 86_400_000
        if s["exit"] or held_days >= self.hold:
            return 1.0, s["price"], "mean reversion: bounced or time limit"
        return None


class EarlyMover:
    """Hunts coins that are starting to take off, across EVERY USD coin on Crypto.com:
    price up >= x over the last k hours on volume >= v times its normal hourly volume
    (normal = prior 7-day average), plus brand-new listings in their first hours.
    Exits with a trailing stop `trail` below the highest price since entry, or after h hours.
    Parameters come from pumps.py (backtest over all Crypto.com coins)."""
    name = "early_mover"
    weekly = False
    dynamic_universe = True          # runner refreshes the coin list every cycle
    P = config.EARLY_MOVER

    def __init__(self, name="early_mover", **overrides):
        self.name, self.universe = name, []
        self.P = dict(config.EARLY_MOVER, **overrides)
        self.max_positions = self.P["slots"]
        self.position_pct = self.max_position_pct = (1 - config.MIN_CASH_RESERVE_PCT) / self.P["slots"]
        self.trail = self.P["trail"]
        self.min_candles = 3
        self.window = 7 * 24 + self.P["k"] + 2

    def analyze(self, candles, market_ok=True):
        p, c = self.P, candles
        if len(c) < 3:
            return None
        sig = _base(c)
        sig.update(stop=c[-1]["c"] * (1 - p["trail"]), rank=0.0, buy=False)
        now_ms = time.time() * 1000
        if len(c) < 48:                       # brand-new listing
            fresh = now_ms - c[0]["t"] <= p["listing_hours"] * HOUR
            sig.update(buy=p["buy_listings"] and fresh, rank=99.0, reason="new listing")
            return sig
        k = p["k"]
        if len(c) < 7 * 24 + k + 1:
            return sig
        vol = [x["v"] * x["c"] for x in c]
        base = sum(vol[-1 - 7 * 24 - k:-1 - k]) / (7 * 24)
        recent = sum(vol[-k:]) / k
        rise = c[-1]["c"] / c[-1 - k]["c"] - 1
        if base > 0 and base * 24 >= p["min_daily_usd"] and rise >= p["x"] and recent >= p["v"] * base:
            sig.update(buy=True, rank=rise * recent / base)
        return sig

    def manage(self, pos, s, now, rebalance=False):
        hit = _stop_check(pos, s)
        if hit:
            return 1.0, hit[1], "trailing stop"
        if now - pos["opened"] >= self.P["h"] * HOUR:
            return 1.0, s["price"], "time limit"
        pos["peak"] = max(pos["peak"], s["high"])
        pos["stop"] = max(pos["stop"], pos["peak"] * (1 - self.trail))
        return None


class HoldBenchmark:
    """Just buy and hold the benchmark (BTC / SPY): the bar every strategy must beat."""
    weekly = False
    min_candles = 1
    window = 2
    max_positions = 1
    position_pct = max_position_pct = 1 - config.MIN_CASH_RESERVE_PCT

    def __init__(self, symbol):
        self.universe = [symbol]
        self.name = f"hold_{symbol.lower()}"

    def analyze(self, candles, market_ok=True):
        sig = _base(candles)
        sig.update(rank=1, buy=True, stop=0.0)
        return sig

    def manage(self, pos, s, now, rebalance=False):
        return None


def regime_ok(bench_closes, bars_per_day, days=None):
    """True when the benchmark (BTC or SPY) closes above its N-day average.
    Research: this mainly cuts drawdowns; it's a seatbelt, not an engine."""
    n = (days or config.REGIME_DAYS) * bars_per_day
    if len(bench_closes) < n:
        return True
    return bench_closes[-1] > sum(bench_closes[-n:]) / n
