"""The two markets we paper trade side by side, each with its own strategies
and its own $500 paper account per strategy."""
import config
from strategy import (BreakoutHunter, DonchianRotation, HoldBenchmark, MomentumRotation,
                      RSI2MeanReversion, TrendFollower, WeeklyMomentum)


def _crypto():
    from data_source import CryptoComClient
    return CryptoComClient()


def _stocks():
    from data_source import YahooClient
    return YahooClient()


MARKETS = {
    "crypto": {
        "client": _crypto,
        "benchmark": "BTC",
        "main": "breakout10",      # the strategy trading this market's official $500
        "bars_per_day": 24,
        "fee": config.FEE_RATE, "slippage": config.SLIPPAGE_RATE,
        "strategies": [
            DonchianRotation(config.UNIVERSE, 24),
            WeeklyMomentum(config.UNIVERSE, 24, "crypto"),
            BreakoutHunter(config.BREAKOUT_UNIVERSE),
            HoldBenchmark("BTC"),
        ],
    },
    "stocks": {
        "client": _stocks,
        "benchmark": "SPY",
        "main": "rsi2",
        "bars_per_day": 7,   # regular session 9:30-16:00 ET in hourly bars
        "fee": config.STOCK_FEE_RATE, "slippage": config.STOCK_SLIPPAGE_RATE,
        "strategies": [
            RSI2MeanReversion(sorted(set(config.STOCK_UNIVERSE) | set(config.STOCK_ETFS)), 7),
            MomentumRotation(config.STOCK_UNIVERSE, 7),
            WeeklyMomentum(config.STOCK_UNIVERSE, 7, "stocks"),
            TrendFollower(config.STOCK_UNIVERSE),
            HoldBenchmark("SPY"),
        ],
    },
}
