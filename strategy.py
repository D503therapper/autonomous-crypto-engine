"""Trend-following strategy: buy strong coins in uptrends, cut losers fast,
let winners run with a trailing stop, bank partial profits on big moves."""
import config
from indicators import atr, ema, rsi


def analyze(candles):
    """Return the latest signal snapshot for one coin, or None if not enough data."""
    if len(candles) < config.EMA_TREND + 5:
        return None
    closes = [c["c"] for c in candles]
    f, s, t = ema(closes, config.EMA_FAST), ema(closes, config.EMA_SLOW), ema(closes, config.EMA_TREND)
    r = rsi(closes, config.RSI_PERIOD)
    a = atr(candles, config.ATR_PERIOD)
    lb = min(config.MOMENTUM_LOOKBACK, len(closes) - 1)
    price = closes[-1]
    uptrend = price > t[-1] and f[-1] > s[-1] and t[-1] > t[-24]
    fresh_cross = any(f[-i - 1] <= s[-i - 1] and f[-i] > s[-i] for i in range(1, 7))
    pullback_ok = price <= f[-1] * 1.03  # not stretched far above the fast average
    return {
        "price": price,
        "atr": a[-1],
        "rsi": r[-1],
        "momentum": closes[-1] / closes[-1 - lb] - 1,
        "buy": uptrend and (fresh_cross or pullback_ok) and r[-1] < config.RSI_MAX_ENTRY,
        "trend_broken": f[-1] < s[-1] and price < s[-1],
        "high": candles[-1]["h"],
        "low": candles[-1]["l"],
        "t": candles[-1]["t"],
    }
