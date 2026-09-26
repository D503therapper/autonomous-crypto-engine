"""The two markets we paper trade side by side, each with its own strategies
and its own $500 paper account per strategy."""
import config
from social import SocialHeat
from stock_strategies import DualMomentum, TrendEnsemble
from strategy import (BreakoutHunter, DonchianRotation, EarlyMover, HoldBenchmark, MomentumRotation,
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
        # official $500 = two $500 accounts averaged: the 10-day breakout rotation, and the new-listing
        # hunter whose idle cash rides the rotation's current picks (run_live.park_idle), so all of it
        # is always actively trading; new listings are funded by selling a slice of those picks.
        # owner 2026-09-26: official crypto = the listing hunter only. crypto_studies.py showed the breakout10
        # rotation made +0.2%/month over 5 years (< hold BTC); it keeps running as a test account.
        "main": ["early_mover"],
        "bars_per_day": 24,
        "fee": config.FEE_RATE, "slippage": config.SLIPPAGE_RATE,
        "strategies": [
            EarlyMover(),                    # official: new Crypto.com listings in their first hours
            EarlyMover("mover", movers=True, buy_listings=False, trail=0.20),   # take-offs + footprint (test)
            EarlyMover("announce", movers=False, buy_listings=False),           # exchange listing notices (test)
            # "no-limit chaser": buys coins already up >= 30% in 24h on heavy volume and
            # rides them with a trailing stop (owner's idea; tested live against the official)
            EarlyMover("chaser", k=24, x=0.30, v=3, trail=0.25, h=240, buy_listings=False),
            # social heat: buys coins trending on CoinGecko / Reddit / DEX feeds (social.py)
            SocialHeat(),
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
            # lab walk-forward picks (results/lab_stocks.txt), target-weight accounts (test):
            DualMomentum(7),                                    # monthly index-ETF momentum vs IEF
            TrendEnsemble(sorted(set(config.STOCK_UNIVERSE) | set(config.STOCK_ETFS)), 7),  # weekly trend top-5
            MomentumRotation(config.STOCK_UNIVERSE, 7),
            WeeklyMomentum(config.STOCK_UNIVERSE, 7, "stocks"),
            TrendFollower(config.STOCK_UNIVERSE),
            HoldBenchmark("SPY"),
        ],
    },
}
