# Crypto Paper Trader ($500, hypothetical)

An automated **paper-trading** bot for coins listed on Crypto.com. It uses real prices and fake money.
It never places real orders and has no API keys.

## What it does (every hour)
1. Pulls hourly candles for the coins in `config.UNIVERSE` from Crypto.com's public API.
2. **Buys** coins that are in an uptrend: price above the 200h average, 20h average above the 50h average, and RSI below 70. Candidates are ranked by 72h momentum. It holds at most 4 coins.
3. **Sizes** each buy so that hitting the stop loses about 2% of equity. No coin gets more than 30% of equity, and 10% stays in cash.
4. **Sells** when any of these happen:
   - the stop is hit (starts 2.5×ATR below entry, then trails 3×ATR below the peak);
   - the trend reverses;
   - price reaches +6×ATR, at which point it sells half to lock in gains.
5. **Circuit breaker:** if equity drops 25% from its peak, it stops buying for 7 days.
6. **Flags new coin listings** (crypto has no IPOs; new listings are the closest thing). It only watches them and never buys them automatically.
7. Logs everything to `data/`: `portfolio.json`, `trades.csv` and `equity.csv`.

## Commands
```
python backtest.py --days 180      # test the strategy on real past data
python backtest.py --synthetic     # offline test of the code only (fake prices)
python run_live.py                 # one live paper-trading cycle
python run_live.py --loop          # run forever, hourly (for a PC or server)
```
The only requirement is Python 3.9 or newer. It has no dependencies.

## Before any real money: the pass criteria
Run it forward on paper for **at least 8–12 weeks**. Consider real money only if it:
- beats simply holding BTC over the same period, after fees;
- never draws down more than about 25%;
- makes 30 or more closed trades, so the result isn't luck;
- shows a similar backtest over a *different* date range (not just the one it was tuned on).

## Caveats
- The Crypto.com **App** charges through a spread, often 0.5–1%+ per side. That is why `FEE_RATE` is set to 0.5%. Frequent trading on the App is expensive.
- The Exchange API lists some coins the App doesn't carry, and the other way round. Check `UNIVERSE` against your App.
- A backtest is not a prediction, and past trends don't guarantee future ones.
