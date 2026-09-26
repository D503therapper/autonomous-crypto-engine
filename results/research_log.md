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
Also test a CONCENTRATION CAP (owner: "never hit a Luna Classic"): when one position grows past 20/25/33%
of total equity, sell back down to the cap and bank the rest; keep the remainder on the runner rules. Add
LUNA (May 2022), FTT and other collapses to the replay. Recommend a cap level (or none) with the numbers.
LEGENDS SCREEN CHECK (owner: "that checkbox needs to say YES"): for each legend, reconstruct what our screen
would have seen in its first days (holders, LP burn/lock, owner/blacklist functions, taxes, liquidity, age)
from on-chain history / explorers, and say PASS or which rule blocked it and for how long. Known: SHIB's
first run would fail the top-10 <= 40% rule (50% sent to Vitalik's wallet until his May 2021 burn); PEPE
likely passes after ownership renounce. Two checkboxes per legend (owner): (1) WOULD WE HAVE CAUGHT IT?
(2) WOULD WE HAVE MAXIMIZED PROFIT? - share of the achievable gain our exit kept (our sell vs the peak and
vs the best simple rule in hindsight). Also test TAKE-PROFITS AT BIG MULTIPLES only (owner: not too early, not
too late, bank profits): e.g. sell 10-25% at 10x / 50x / 100x vs none, combined with the concentration cap
(the 2x half-sell already lost in dex_exit_study). For every wrongful block, propose a narrow fix (e.g. treat burn /
famous-dev / CEX wallets separately) and check it against the rugged coins so real scams still fail.

### Social AI hype-reader (owner: "trending on social media is everything to us") - after the home box
Plan once the owner's box (Xeon 14c, 62 GB RAM, RTX A4500 20 GB, no sudo) is a self-hosted runner:
collect Reddit (home IP or free OAuth app) + public Telegram meme channels (free Telegram API with the
owner's account) + existing CoinGecko/DexScreener/GeckoTerminal trending; a local LLM (GPU when free,
CPU fallback while the owner renders video) scores each coin: mention growth, organic vs bot/shill, scam
talk. Feed the score into the DEX hunter's discovery (screen rising coins first) and log it so the runner
study can measure whether buzz came before the runs. X/Twitter is paid (~$200/mo) - revisit once profitable.

## 2026-09-26 - DEX runner study (results/dex_runner_study.txt)
346 pools, 13,704 decision points (Jul-Sep 2026). Before 10x runs coins were young (~22h), small (liq ~$82k,
mcap ~$340k), heavily traded (vol24/liq ~3.7), often 50% off their 7-day high, mostly Solana / pump.fun.
Points score and logistic model separated runners well (logit AUC 0.89 out-of-sample) but did NOT trade better
than the engine's current entry. Current entry (1h +10%, age >= 6h, $100k floors) + live exit: ~5-7 trades/day,
mean +29%/trade (median -6.6%), 12% of trades >= 2x, 4-slot account +101%/month (older +62%, newer +73%),
max drawdown -54% - kept as is. Survivorship bias: absolute returns are a ceiling. Added dex snapshot logging
(data/dex/snapshots.csv: buys/sells, boosts, vol1/6/24, source) so the re-run in 2-4 weeks can test live-only signs.

## 2026-09-26 - crypto_studies.py results (results/crypto_studies.txt)
A. breakout10 rotation over 5 years (2021-07 .. 2026-09, engine replay, 0.5%/side): +0.21%/month, max drawdown 76%
   - WORSE than holding BTC (+1.57%/mo, DD 77%). Earlier tournament's +85% OOS was a favourable window. Top1 worse
   (-3.1%/mo), top3/daily not reliably better. Memes on Crypto.com: every one too thin (SHIB median $171k/day, PEPE
   $100k, BONK $33k) - the exchange's order books are shallow, so meme exposure belongs on DEX. OPEN DECISION for
   the owner: the rotation half of official crypto doesn't earn its keep.
B. Crypto.com top gainers: 57 one-day +30% gainers in 548 days; no early signal traded profitably walk-forward
   (-0.99%/trade, CI -2.2..+0.2); chasing -1.6%. Keep movers off.
C. Listing exits: 40% trail beat 50% (+5.6% vs +3.3%/trade, both halves positive, walk-forward picked it 69/89).
   APPLIED: config.MOON trail 0.40, EARLY_MOVER trail 0.40.
