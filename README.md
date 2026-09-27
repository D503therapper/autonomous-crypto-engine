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
python backtest.py --strategy breakout   # test one strategy (trend | breakout | all)
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

---

# THE D503 SPORTS ENGINE (paper picks, $100 each)
Phone dashboard: https://d503therapper.github.io/autonomous-crypto-engine/sports/
(Safari → Share → **Add to Home Screen**.)

Every hour, `.github/workflows/sports.yml` runs `sports.py`:
1. **Data:** games, final scores and odds (moneylines, spreads, opening lines) for NFL, college football,
   NBA, MLB and NHL from ESPN's free scoreboard API. On the first run it backfills about 18 months of results.
2. **Grades** every open pick once its games finish.
3. **Retrains** after every batch of new final scores (`sports_model.py`). It uses team ratings (Elo, with
   margin of victory), recent form, rest, back-to-backs, injuries (players Out/Doubtful), and line movement
   (the free stand-in for sharp money). These are blended with the betting market by a learned "trust" weight.
   What changed is logged in `data/sports/model.json` and shown on the dashboard under "The Brain".
4. **The board** shows as a PREVIEW from 6pm Pacific the night before and is re-picked every hour as lines
   and injury news move. Plays LOCK (official, graded) at 7am Pacific on game day, or 3 hours before an
   earlier game:
   - **2-Leg of the Day:** $100 wins at least $500. One leg per game, no moneyline leg shorter than −150.
   - **3-Leg of the Day:** $100 wins at least $1,000. Same leg rules.
   - **Lock of the Day:** a moneyline no shorter than −120, picked for the highest win chance.
   - **Dog of the Day:** a plus-money moneyline picked for the best value. Big dogs are allowed.
   - Spreads are used only in NFL, college football and NBA. There are no run lines, puck lines or player props.
5. Rebuilds `docs/sports/index.html`.

Files: `data/sports/picks.json` (every pick and result), `model.json` (the brain), `games/<league>/<month>.csv`.
Commands: `python sports.py` (one cycle), `python sports.py --repick` (redo today's board),
`python sports_test.py` (offline tests). Rule settings sit at the top of `sports.py`.
