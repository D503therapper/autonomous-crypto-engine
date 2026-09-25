"""All tunable settings in one place. Nothing here touches real money."""

STARTING_CASH_USD = 500.00

# --- Market data -----------------------------------------------------------
# Public Crypto.com Exchange API (no API key needed for prices).
# NOTE: the Crypto.com *App* and *Exchange* list slightly different coins.
# Before going live, confirm every coin in UNIVERSE is buyable in your App.
API_BASE = "https://api.crypto.com/exchange/v1"
QUOTE = "USD"
TIMEFRAME = "1h"          # candle size the strategy reads
CANDLES_NEEDED = 600      # history pulled per coin on each tick (weekly momentum needs ~21 days)

# Coins to trade. Kept to large, liquid coins on purpose: small caps on the
# App have wide spreads that eat a $500 account alive.
UNIVERSE = [
    "BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "LINK",
    "DOT", "LTC", "BCH", "ATOM", "NEAR", "UNI", "AAVE", "SUI",
]

# --- Costs per side (pessimistic) -------------------------------------------
# Crypto: exchange taker fee (Kraken Pro 0.40%, Crypto.com Exchange ~0.50%);
# the Crypto.com App's spread is worse (0.5-2%) and can't be automated anyway.
FEE_RATE = 0.004
SLIPPAGE_RATE = 0.001
STOCK_FEE_RATE = 0.0      # US brokers: $0 commission
STOCK_SLIPPAGE_RATE = 0.0005

# --- Stocks (paper only; prices from Yahoo Finance, fractional shares assumed) --
# Liquid large caps + index ETFs. Held for hours-to-weeks (swing trading), which
# also avoids the pattern-day-trader limits on small accounts.
STOCK_UNIVERSE = [
    "SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
    "AMD", "AVGO", "NFLX", "JPM", "LLY", "COST", "PLTR", "COIN", "MSTR", "UBER",
]

STOCK_ETFS = ["SPY", "QQQ", "IWM", "DIA", "TLT", "IEF", "GLD", "XLK", "XLF", "XLE", "XLV", "XLY",
              "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC", "SMH", "EFA", "EEM"]

# --- Early mover hunter (all Crypto.com coins) -----------------------------
EARLY_MOVER = {
    "k": 3, "x": 0.10, "v": 3,        # up >= 10% in 3h on >= 3x normal volume
    "trail": 0.35, "h": 72,           # trailing stop 35% below peak; max 72h hold (pumps.py:
                                      # new listings +13.5%/trade avg at 35%/72h, Apr-Sep 2026)
    "movers": False,                  # official account: new listings only (take-off buying lost
                                      # out-of-sample in pumps.py; it runs in the "mover" test account)
    "min_daily_usd": 50_000,          # skip coins too thin to trade
    "buy_listings": True, "listing_hours": 3,
    "slots": 5,
}
# Minute-level scanner feeding the same early_mover account (scanner.py): one
# public/get-tickers call per minute across every USD coin. Any tier fires.
EARLY_MOVER_SCANNER = {
    "tiers": [(15, 0.05), (30, 0.08), (60, 0.12)],   # (window minutes, min rise)
    "vol_ratio": 3.0,           # window volume >= 3x the coin's normal rate
    "min_daily_usd": 100_000,   # skip coins with < $100k traded in 24h
    "max_spread": 0.015,        # skip coins with bid/ask spread > 1.5%
}

# Early-detection signals feeding the same early_mover account (signals.py; specs in
# research_notes/Early mover detection/early_detection.md). Keys override signals.DEFAULTS.
EARLY_SIGNALS = {
    "listing": {                     # 1. exchange listing notices -> buy if NOT yet moved
        "loop_s": 10,                # main loop asks the reactor to poll this often
        "timeout_s": 4,              # per request; never stalls the 1-second stop checks for long
        "max_age_min": 45,           # a notice older than this is old news
        "max_move_since": 0.08,      # price now vs price at the notice (fallback: first detection)
        "max_move_by_source": {"upbit": 0.08, "cryptocom": 0.08, "binance": 0.04, "coinbase": 0.04,
                               "kraken": 0.04},
        "max_24h_change": 0.30,      # never chase a coin already up 30% in a day
        "min_daily_usd": 500_000, "max_spread": 0.01,
        "seen_file": "data/seen_announcements.json",
        "events_file": "data/listing_events.csv",   # t0 / detection / gate verdict per notice
        # URLs from the research notes, none verified from the sandbox; "" disables a source.
        "sources": {
            "cryptocom": {"url": "https://api.crypto.com/exchange/v1/public/get-announcements", "every_s": 10},
            "upbit": {"url": "https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=trade",
                      "every_s": 5},
            "binance": {"url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
                               "?type=1&catalogId=48&pageNo=1&pageSize=20", "every_s": 15},   # 403-prone
            "coinbase": {"url": "https://status.exchange.coinbase.com/history.atom", "every_s": 15},
            "coinbase_blog": {"url": "", "every_s": 60},   # set the blog RSS url once known
            "kraken": {"url": "https://blog.kraken.com/feed", "every_s": 30},
        },
    },
    "footprint": {                   # 2. pre-pump / pre-listing accumulation footprint (hourly)
        "drift": (0.05, 0.25),       # 48h return band
        "max_1h_move": 0.06,         # a single hourly move above this is a spike, not accumulation
        "quiet_frac": 0.60,          # share of the last 48 hours below the median hourly volume
        "hike_mult": 3.0, "hikes": (2, 6),   # 2-6 hours at >= 3x median volume
        "oi_creep": 0.20,            # optional: perp open interest +20% in 24h (from get-tickers `oi`)
        "daily_usd": (300_000, 30_000_000),  # universe: listable elsewhere, still tradable
        "max_24h_change": 0.30, "min_score": 3, "top_n": 3,
    },
    "guard": {                       # 4. pump guard before ANY early_mover entry
        "max_24h_change": 0.30,
        "spike": 0.15, "fade": 0.40, # last 60 min: +15% then gave back 40% of it = exit liquidity
        "block_min": 30,
    },
}

# --- Weekly momentum (the strategy with the strongest research support) -----
MOMENTUM = {
    "lookback_days": 21,       # own return over ~3 weeks must be positive...
    "confirm_days": 7,         # ...and over the last week too
    "trail_stop": {"crypto": 0.15, "stocks": 0.08},  # wide trailing stop between rebalances
}
REGIME_DAYS = 50              # only buy when BTC / SPY is above its 50-day average

# --- Strategy --------------------------------------------------------------
EMA_FAST = 20
EMA_SLOW = 50
EMA_TREND = 200           # only buy coins above their 200-candle average
RSI_PERIOD = 14
RSI_MAX_ENTRY = 70        # don't chase overbought coins
ATR_PERIOD = 14
STOP_ATR_MULT = 2.5       # initial stop = entry - 2.5 * ATR
TRAIL_ATR_MULT = 3.0      # trailing stop follows the highest price since entry
TAKE_PROFIT_ATR_MULT = 6.0  # sell half at +6 ATR to lock in gains
MOMENTUM_LOOKBACK = 72    # rank candidates by 72h return

# --- Breakout hunter ("catch the pump early") ------------------------------
# Wider coin list: pumps happen more in mid/small caps. Confirm each is on your App.
BREAKOUT_UNIVERSE = UNIVERSE + [
    "SHIB", "PEPE", "BONK", "WIF", "FLOKI", "FET", "RENDER", "INJ", "ARB", "OP",
    "APT", "SEI", "TIA", "HBAR", "XLM", "ALGO", "FIL", "ICP", "IMX", "SAND",
    "MANA", "GRT", "CRO", "ONDO", "JUP", "TAO", "HYPE", "ENA", "POL",
]
BREAKOUT = {
    "vol_lookback": 72,        # "normal" volume = average of the last 72h
    "vol_window": 2,           # compare the last 2h against it...
    "vol_surge": 3.0,          # ...and require 3x normal
    "breakout_lookback": 48,   # price must beat its 48h high
    "max_24h_gain": 0.08,      # skip coins already up >8% (we want to be early)
    "min_daily_usd_volume": 2_000_000,  # skip thin coins: spreads + slippage kill profits
    "take_profit": 0.10,       # sell half at +10%
    "trail": 0.06,             # trail the rest 6% below its peak
    "stop_loss": 0.05,         # cut losers at -5%
    "max_hold_hours": 36,      # no move in 36h -> free the money
}

# --- Risk ------------------------------------------------------------------
MAX_POSITIONS = 4
RISK_PER_TRADE = 0.01     # lose at most ~1% of equity if the stop hits (research: 0.5-2%)
MAX_POSITION_PCT = 0.30   # never put more than 30% of equity in one coin
MIN_CASH_RESERVE_PCT = 0.10
MIN_ORDER_USD = 10.00
MAX_DRAWDOWN_HALT = None  # owner's choice: no account-level pause (set e.g. 0.20 to pause at -20%)
HALT_HOURS = 168          # ...for 7 days, then resume
COOLDOWN_CANDLES = 12     # after a stop-out, leave that coin alone for 12h

# --- Files -----------------------------------------------------------------
LISTINGS_FILE = "data/known_listings.json"
