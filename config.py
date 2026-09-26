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
    "trail": 0.50, "h": 24,           # trailing stop 50% below peak; max 24h hold. listings_study.py
                                      # (91 listings, 17 months): most robust cell, +12.9%/trade
                                      # (CI -0.2%..+30%), walk-forward's consistent last pick; edge lumpy.
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
                               "kraken": 0.04, "upbit_markets": 0.08, "coinbase_products": 0.05,
                               "kraken_pairs": 0.05, "binanceus_symbols": 0.05, "gemini_symbols": 0.05,
                               "okx_symbols": 0.05},
        "max_24h_change": 0.30,      # never chase a coin already up 30% in a day
        "min_daily_usd": 500_000, "max_spread": 0.01,
        "seen_file": "data/seen_announcements.json",
        "events_file": "data/listing_events.csv",   # t0 / detection / gate verdict per notice
        # URLs from the research notes, none verified from the sandbox; "" disables a source.
        "sources": {
            # verified from the GitHub runner 2026-09-25 (tools/probe.py -> results/probe.txt)
            "cryptocom": {"url": "https://api.crypto.com/v1/public/get-announcements?category=list&product_type=Spot",
                          "every_s": 10},
            "binance": {"url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
                               "?type=1&catalogId=48&pageNo=1&pageSize=20", "every_s": 15},
            "coinbase": {"url": "https://status.exchange.coinbase.com/history.atom", "every_s": 30},
            "upbit": {"url": "", "every_s": 5},          # announcements API: 403 from GitHub runners
            "coinbase_blog": {"url": "", "every_s": 60},
            "kraken": {"url": "", "every_s": 30},        # blog feed: 403 from GitHub runners
            # coin-list watchers (new coin in the exchange's public market list = listing)
            "upbit_markets": {"url": "https://api.upbit.com/v1/market/all", "every_s": 30},
            "coinbase_products": {"url": "https://api.exchange.coinbase.com/products", "every_s": 30},
            "kraken_pairs": {"url": "https://api.kraken.com/0/public/AssetPairs", "every_s": 60},
            "binanceus_symbols": {"url": "https://api.binance.us/api/v3/exchangeInfo", "every_s": 120},
            "gemini_symbols": {"url": "https://api.gemini.com/v1/symbols", "every_s": 60},
            "okx_symbols": {"url": "https://www.okx.com/api/v5/public/instruments?instType=SPOT", "every_s": 60},
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
# --- Runners: never sell a coin while it's flying ------------------------------
# Once a position has been up >= "ride" (peak vs entry), the engine blocks every exit except a
# trailing stop: no time limits, no rotation / rebalance sales, no take-profits, no unparking.
# It only sells after the price gives back "trail" from its peak (same 50% as the listing hunter).
# Live crypto accounts only. Dashboard badge: up >= "hot" (50%) vs entry right now -> 🔥 ON FIRE 🚀.
MOON = {"ride": 0.50, "trail": 0.50, "hot": 0.50}

COOLDOWN_CANDLES = 12     # after a stop-out, leave that coin alone for 12h

# --- Files -----------------------------------------------------------------
LISTINGS_FILE = "data/known_listings.json"

# --- Social heat tracker (social.py) + "social_heat" test account ----------
# Attention is recorded for every Crypto.com USD coin (data/social/); the account buys
# the hottest coins. Sources are keyless and optional; CMC stays off until a keyless
# trending endpoint is verified live (set cmc_url and cmc=True).
SOCIAL = {
    "coingecko": True, "cmc": False, "cmc_url": "", "reddit": True, "dex": True,
    "subreddits": ["CryptoMoonShots", "SatoshiStreetBets", "CryptoCurrency", "memecoins"],
    "poll_min": {"coingecko": 15, "cmc": 15, "reddit": 15, "dexscreener": 5, "geckoterminal": 10},
    "timeout": 8,                     # seconds per HTTP call (never blocks the 1s stop checks for long)
    "enter": 50, "floor": 20, "floor_hours": 12,   # buy at heat >= 50; sell after 12h below 20
    "trail": 0.25, "max_hold_days": 10,            # trailing stop 25% below peak; 10-day max hold
    "min_24h_change": -0.10,          # skip spike-and-fade (down >10% in 24h); no upper cap on purpose
    "slots": 5,
}

# --- DEX (on-chain) paper trader (dex.py) + "dex_hunter" $500 account ----------
# Keys override dex.DEFAULTS (nested keys merge). Paper only: no wallet, no keys, no transactions.
# Owner priorities: big wins on DEX coins, avoid scams above all -> STRICT screen, tiered sizing.
DEX = {
    "chains": ["solana", "base", "ethereum"],
    "urls": {   # GoPlus EVM, honeypot.is, RugCheck summary, DexScreener, GeckoTerminal verified from the
                # GitHub runner (results/probe.txt); the GoPlus Solana path is NOT verified yet
        "goplus_evm": "https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={addr}",
        "goplus_sol": "https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={addr}",
        "honeypot": "https://api.honeypot.is/v2/IsHoneypot?address={addr}&chainID={chain_id}",
        "rugcheck": "https://api.rugcheck.xyz/v1/tokens/{addr}/report/summary",
        "ds_tokens": "https://api.dexscreener.com/tokens/v1/{chain}/{addrs}",
        "ds_search": "https://api.dexscreener.com/latest/dex/search?q={q}",
        "ds_boosts": "https://api.dexscreener.com/token-boosts/top/v1",
        "gt_trending": "https://api.geckoterminal.com/api/v2/networks/{network}/trending_pools?duration=1h",
    },
    "timeout": 6,                                  # seconds per request (hard cap 8: never stalls the 1s loop)
    "every_s": {"discover": 300, "watch": 600, "prices": 60, "rescreen": 1800, "followup": 3600},
    "screen": {                                    # every check must pass; unreachable source = not tradable
        "max_tax": 0.03, "max_creator_pct": 0.05, "max_top10_pct": 0.40, "min_lp_locked": 0.95,
        # owner 2026-09-26: trade the DEX all day. Floors lowered from $250k / 24h / $300k so fresh meme pools
        # reach the scam checks; every contract / LP-lock / holder / honeypot check still applies, tier A stays 3%
        "min_liq": 100_000, "liq_x_size": 50, "min_age_h": 6, "min_vol24": 100_000,
        "max_24h_change": None,                    # no cap on prior gains (owner)
        "mature": {"age_h": 720, "liq": 1_000_000},   # 30+ days with $1M+: LP lock not required (v3/CLMM can't lock)
        "age_unknown_liq": 1_000_000,                 # source gave no pool age: fine on a $1M+ pool
    },
    # dex_exit_study.py (results/dex_exit_study.txt, 2026-09-26): the "fast10" entry (1h >= +10%) beat the old
    # 1h +5% / 6h +10% entry; buys must still outnumber sells
    "entry": {"h1": 0.10, "h6": -1.0, "buy_ratio": 1.2},
    "tiers": {                                     # share of equity; all capped at 0.5% of pool liquidity + cash
        "A": {"pct": 0.03},                                                                   # "new"
        "B": {"pct": 0.10, "age_d": 7, "liq": 1_000_000, "vol24": 1_000_000, "clean": 2},    # "proven"
        "C": {"pct": 0.20, "age_d": 30, "liq": 5_000_000, "clean": 0, "cex": True},           # "blue"
    },
    "cex_list": [],                                # extra CEX-listed symbols (Crypto.com tickers are used live)
    "size": {"liq_pct": 0.005, "max_exposure": 0.60},
    "cost": {"fee": 0.003, "slip": 0.01},          # + price impact usd / liquidity, per side
    # dex_exit_study.py: the old exit (30% trail + take-profit ladder) lost -6.4%/trade and sold 3 of 3 later
    # 10x coins early; "hold 14 days, no stop" was the robust winner (+85%/trade, walk-forward rank 1;
    # 4-slot portfolio with the fast entry +55%/month, both halves positive, max drawdown -37%). Meme coins
    # swing 30-50% on the way up, so any tight stop shakes us out. Rug protection stays: liquidity pull /
    # failed re-screen still sell at once. Owner rule: a coin up >= 2x at day 14 keeps riding on a 50% trail.
    # Owner: never miss a 1000x, never give it all back -> once a coin has hit 3x, a 60% trail from its high
    # (a 10x that collapses is sold around 4x; big runners' normal 50% pullbacks don't trigger it).
    "exit": {"trail": 0.95, "tp1": (999.0, 0.0), "ladder": [], "trail_steps": [(3.0, 0.60)],
             "max_hold_days": 14, "runner_at_limit": (1.0, 0.50),   # >= +100% at the limit: 50% trail, no clock
             "liq_pull": 0.50, "rug_tax": 0.50},
    "slots": 4,
    "scam_pause": {"max": 2, "days": 30, "reset_after": ""},   # 2 scams / 30 days -> no new entries; to
                                                   # re-enable set reset_after "YYYY-MM-DD HH:MM" (UTC) > pause time
}
