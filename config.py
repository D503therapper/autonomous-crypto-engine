"""All tunable settings in one place. Nothing here touches real money."""

STARTING_CASH_USD = 500.00

# --- Market data -----------------------------------------------------------
# Public Crypto.com Exchange API (no API key needed for prices).
# NOTE: the Crypto.com *App* and *Exchange* list slightly different coins.
# Before going live, confirm every coin in UNIVERSE is buyable in your App.
API_BASE = "https://api.crypto.com/exchange/v1"
QUOTE = "USD"
TIMEFRAME = "1h"          # candle size the strategy reads
CANDLES_NEEDED = 300      # history pulled per coin on each tick

# Coins to trade. Kept to large, liquid coins on purpose: small caps on the
# App have wide spreads that eat a $500 account alive.
UNIVERSE = [
    "BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "LINK",
    "DOT", "LTC", "BCH", "ATOM", "NEAR", "UNI", "AAVE", "SUI",
]

# --- Costs (be pessimistic; the App prices by spread, not a visible fee) ---
FEE_RATE = 0.005          # 0.50% per side (card/App spread is often 0.5-1%+)
SLIPPAGE_RATE = 0.001     # 0.10% extra per fill

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

# --- Risk ------------------------------------------------------------------
MAX_POSITIONS = 4
RISK_PER_TRADE = 0.02     # lose at most ~2% of equity if the stop hits
MAX_POSITION_PCT = 0.30   # never put more than 30% of equity in one coin
MIN_CASH_RESERVE_PCT = 0.10
MIN_ORDER_USD = 10.00
MAX_DRAWDOWN_HALT = 0.25  # stop opening trades if equity falls 25% from peak...
HALT_HOURS = 168          # ...for 7 days, then resume
COOLDOWN_CANDLES = 12     # after a stop-out, leave that coin alone for 12h

# --- Files -----------------------------------------------------------------
STATE_FILE = "data/portfolio.json"
TRADE_LOG = "data/trades.csv"
EQUITY_LOG = "data/equity.csv"
LISTINGS_FILE = "data/known_listings.json"
