# Research log

Daily deep-study notes. Newest first. Open questions at the top get studied next.

## Open questions

### #1 PRIORITY - How to find the DEX coins that run 100%-1000%+ every day (owner, 2026-09-26)
"If we master finding these coins on the DEX, that is the jackpot." Build a study (GitHub workflow, like
dex_exit_study.py) on thousands of Solana / Base / Ethereum pools from GeckoTerminal + DexScreener:
- Label every pool by what it did next: ran 2x / 5x / 10x+ within 1-7 days, went nowhere, or rugged.
- Features visible BEFORE the run, at 5m / 15m / 1h resolution: pool age, pump.fun graduation (address
  ends in "pump", LP auto-burned), liquidity and its growth, volume / liquidity, buys vs sells and unique
  buyers growth, holder count growth, price trend (1h / 6h / 24h), market cap, DexScreener boosts and
  trending rank, GeckoTerminal trending, CoinGecko trending, social mentions (dex_watch), time of day.
- Find which features separate the runners from the duds and the rugs; build a simple score, check it
  walk-forward (fit on older months, test on newer), and measure trades/day, win rate, profit/month
  after costs with the live exit (14-day hold, runner rules).
- Wire the winning score into dex.py discovery / entry (more candidates, earlier, fewer duds) and report
  to the owner in plain words: how many runners/day it would have caught and what it would have made.
Real misses to learn from: PAID (solana, +247% after a data-gap rejection), ELON (+68%).
Follow-up: SMART-MONEY WALLETS - find wallets that repeatedly bought early into pools that later ran 5x+
(from on-chain trade history of past runners), then test "buy when N smart wallets buy" walk-forward.
Check free data sources reachable from the GitHub runner (GeckoTerminal trades endpoint, Solana RPC,
DexScreener) before building it.


### Runner exits (asked by the owner 2026-09-26)
Goal: never lose a big gain, and never sell a coin that is on its way to 100x. These pull in
opposite directions, so settle it with data (listings_study.py histories, plus dex_exit_study for DEX):

1. **Break-even floor.** Once a coin is up 50% (config.MOON "ride"), never sell below entry.
   Does it beat the current rule (50% trail from the high only)?
2. **Wider trail for the biggest winners.** For example 50% until 5x, then 60% (a 100x coin often
   has 50-70% pullbacks on the way up). Does it catch more of the giant runs without losing more elsewhere?
3. Score each option on: average profit per trade, the share of the top-3 trades we captured,
   and how many runners that went on to 10x+ were sold before 3x.

Switch config.MOON or EARLY_MOVER only if the walk-forward (unseen months) result is better.
Report the answer to the owner in plain words.

### Meme coins in the rotation (asked by the owner 2026-09-26)
The official rotation (breakout10) only picks from config.UNIVERSE (16 large coins). Test adding the
Crypto.com meme coins (PEPE, BONK, WIF, FLOKI, SHIB, DOGE already in, etc.) to its universe with the lab's
walk-forward: more profit on unseen months with an acceptable drawdown? Also compare a separate
meme-only rotation. Switch only if it wins out-of-sample; report in plain words.

### Anatomy of the top gainers (asked by the owner 2026-09-26) - HIGH PRIORITY
Goal: get in BEFORE the spikes (meme coins, top daily gainers). Take the biggest one-day gainers on
Crypto.com (and top DEX meme runs from GeckoTerminal) over the last ~18 months. For each, measure what
was visible 1h / 6h / 24h / 72h BEFORE the move: volume vs normal (quiet accumulation), price drift,
open interest, listing notices on other exchanges, CoinGecko trending, DEX pool age / buyers / liquidity.
Then check the same signals on random non-pumping coins (false alarms). Output: which early signs
actually came first, how often they fired without a pump, and whether trading them makes money after
costs (walk-forward). Wire the winners into the scanner / footprint / social signals. Report in plain words.
Note: X/Twitter (Elon) needs a paid API and bots react in seconds - study how long tweet-driven pumps
lasted historically before deciding it's worth paying for.

### One coin vs two in the rotation (asked by the owner 2026-09-26)
Owner wants bigger gains: test the breakout10 rotation (and the ens_donchian family) with top_n=1 vs 2
(tournament only tried 2 and 5). Walk-forward, after costs: profit per month, max drawdown, worst month.
Switch to 1 only if it wins on unseen months with a drawdown the owner can live with; report plainly.
Do NOT concentrate the listing hunter (lumpy edge: top 3 of 91 listings = 94% of profit).

## 2026-09-26 - DEX exit study applied
results/dex_exit_study.txt (47-67 real meme pools, Mar-Sep 2026): the old DEX exit (30% trail + take-profit
ladder) lost -6.4%/trade and sold 3/3 later-10x coins early. Robust winner: hold 14 days, no stop
(+85%/trade mean, median -7%, walk-forward rank 1 of 68; paired vs old +91%/trade CI [+6%, +233%]).
Portfolio (4 slots, fast 1h >= +10% entry): +55%/month, both halves positive, max drawdown -37%.
Applied: entry 1h >= +10% with buys > sells; hold 14 days; owner rules added on top (untested, watch them):
a coin >= 2x at day 14 keeps riding on a 50% trail; once a coin hits 3x, a 60% trail from its high.
Rug exits (liquidity pull, failed re-screen) unchanged. Caveats: small sample, profit comes from few big
winners (median trade loses), so expect many small red trades between big ones. Re-run the study monthly.
TODO (owner asked): test the untested owner-rule add-ons on the same dex_exit_study data - protection trail
after 3x at 50% / 60% / 70% / none, trigger at 3x vs 5x, and the day-14 runner trail 40/50/60%. Pick the
most profitable robust one (walk-forward) and update config.DEX["exit"]; report in plain words.
Include a LEGENDS replay (owner): run SHIB 2021, PEPE 2023, BONK, WIF, POPCAT, MOG, FLOKI and famous rugs /
dead memes through the exact live DEX rules (entry at the first 1h +10% day after launch, 14-day hold,
runner trail, protection trail 50/60/70/none). Show where each rule would have sold vs the peak and the later
second leg, and pick by total profit across legends AND duds together, not legends alone.

### Social AI hype-reader (owner: "trending on social media is everything to us") - after the home box
Plan once the owner's box (Xeon 14c, 62 GB RAM, RTX A4500 20 GB, no sudo) is a self-hosted runner:
collect Reddit (home IP or free OAuth app) + public Telegram meme channels (free Telegram API with the
owner's account) + existing CoinGecko/DexScreener/GeckoTerminal trending; a local LLM (GPU when free,
CPU fallback while the owner renders video) scores each coin: mention growth, organic vs bot/shill, scam
talk. Feed the score into the DEX hunter's discovery (screen rising coins first) and log it so the runner
study can measure whether buzz came before the runs. X/Twitter is paid (~$200/mo) - revisit once profitable.
