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

# --- Breakout hunter ("catch the pump early") ------------------------------
# Wider coin list: pumps happen more in mid/small caps. Confirm each is on your App.
BREAKOUT_UNIVERSE = UNIVERSE + [
    "SHIB", "PEPE", "BONK", "WIF", "FLOKI", "FET", "RENDER", "INJ", "ARB", "OP",
    "APT", "SEI", "TIA", "HBAR", "XLM", "ALGO", "FIL", "ICP", "IMX", "SAND",
    "MANA", "GRT", "CRO", "ONDO", "JUP", "TAO", "HYPE", "ENA", "POL", "TRX",
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
RISK_PER_TRADE = 0.02     # lose at most ~2% of equity if the stop hits
MAX_POSITION_PCT = 0.30   # never put more than 30% of equity in one coin
MIN_CASH_RESERVE_PCT = 0.10
MIN_ORDER_USD = 10.00
MAX_DRAWDOWN_HALT = 0.25  # stop opening trades if equity falls 25% from peak...
HALT_HOURS = 168          # ...for 7 days, then resume
COOLDOWN_CANDLES = 12     # after a stop-out, leave that coin alone for 12h

# --- Files -----------------------------------------------------------------
LISTINGS_FILE = "data/known_listings.json"
