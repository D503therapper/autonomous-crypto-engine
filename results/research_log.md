# Research log

Daily deep-study notes. Newest first. Open questions at the top get studied next.

## Open questions

> WARNING: never push to branch "pending/crypto-into-dex" - its copy of paper-trade.yml has no branch filter, so a
> push there starts a live engine on that branch and cancels main's (happened 2026-09-27 02:47-03:20 UTC; that
> run's trades - a 3rd HOLDOWEEN - and its crypto->DEX move exist only on that branch and were discarded). To apply
> it, cherry-pick commit 8d347f9 onto main when the owner says yes.


### DONE 2026-09-27 - "goplus unreachable" on 0xb2000... Base tokens (BASECAT, NVDAc, AAPLc, METAC, BLUECHIP)
Probe (results/probe_goplus.txt + git history): GoPlus DID answer - HTTP 200, code 3, message "OK", a result with only
14-15 fields (name, supply, holders, lp_holders, dex, is_open_source, "" taxes, "" owner) and NO is_honeypot / mint /
owner / proxy fields. dex.py required code == "1", so it read "unreachable" forever. These tokens have runtime code
"0xef" (eth_getCode; not a normal CREATE-deployed contract), no creator on Blockscout, and their creation tx names
system address 0xb20f000000000000000000000000000000000000 (a chain-level token factory); NVDAc is "NVIDIA (Coinbase
Tokenized Stock)" minted by an issuer create(token,to,amount,mintId), with RoleGranted events. honeypot.is: isHoneypot
true, "execution reverted: STF", sellTax 100, 96% of holders' simulated sells fail (BASECAT 1287/1334) - its simulator
can't sell them (DexScreener shows real sells), but nothing confirms they are safe either.
FIX: code 1/2/3 accepted; a missing GoPlus field is "unknown", never "0": sell-simulation fields defer to honeypot.is,
missing mint / owner / pause / blacklist / proxy fields reject (screen still runs honeypot.is for the full reason list).
Open: a source for contract powers of 0xef native tokens (none free found yet); watch rejected_followup for them.

### DONE 2026-09-27 13:30 - Rug exit fired on a price dump (GENO), fixed (02a2935)
$ liquidity of a constant-product pool ~ sqrt(price): a -77.5% dump reads as -53% liquidity. GENO was sold as a rug at the
wick bottom (-$167); the pool was back at $100k near entry 34 min later. Rug now = liquidity <= 50% of liq0*sqrt(min(1,p/p0)).
Same flaw remains in the rejected-coin follow-up rug metric (and a missing pair = $0) - fix before using its rug rates.

### QUEUED - LP lock < 95% rejects on Solana (missed AQUA +86%, CALI +71%, JACK +66%, FONE +52% on 2026-09-27)
Interim: 24 coins rejected only on LP-lock/holder data; PAID +290%, FONE +130%. Wait for 7-day follow-ups (from ~10-03),
with the fixed rug metric, then compare ran-up vs rugged by lock % and liquidity.

### NEXT (owner, 2026-09-27) - Profit floor below 2x (TEXTIT: +94% peak -> -24% within 2h, no protection)
Test on dex_runner/legends data: once up +50% never below break-even; once +75% lock +25%; vs current (trail only
after 2x at day 14 / 0.95 trail). Keep only if monthly return holds in both halves AND the legends still get caught.

### QUEUED (owner, 2026-09-27) - bigger bets on proven runners, account brake, big-win playbook
1. Pyramiding: add to a held coin once proven (>=14d old, >=2x, big liquidity/holders, or listed on a major
   exchange) with a trail protecting it; does it beat no-add without Luna-style wipeouts?
2. Account-level brake: stop new buys / tighten exits after a 20-25% drawdown from the account high - test levels.
3. Big-win playbook: take the stake back at 2x, moon bag on the 40% trail, bank chunks at milestones; tax set-aside.

### NEXT (first) - Re-screen "safety data" exits: are they selling good coins? (2026-09-27)
All 4 DEX sales so far were emergency exits on re-screen DATA flags (holders/LP holders unknown, RugCheck
"lp locked 0%"), none on a real rug. tools/sold_followup.py after them: ANTFUN -1% (good sell), SDOG +37%
(high +71%, too early, ~$32 missed), HOLDOWEEN qYCU +2%, HOLDOWEEN Bxft -6% (good sell). Net: holding would
have been +$30. Coins that PASSED the entry screen later fail the same data checks - likely flaky Solana
LP/holder data on pump.fun pools, not new danger. 4 trades is too few to loosen scam protection: keep
collecting; test = replay every re-screen data-flag exit in outcomes.csv vs later snapshots; if data-flag
exits keep losing vs holding while zero turn into rugs, require a real change (liquidity drop, mint/freeze,
owner) before an emergency exit instead of "data unknown".

### NEXT - Second DEX entry: "dip + bounce" (owner asked 2026-09-27: buy the drop points?)
Quick label check on results/dex_runner_points.csv.gz (liq >= $100k, age >= 6h): current entry (1h >= +10%) n=251:
2x/7d 53%, 5x 24%, rug 2.0%, median worst-drop after entry -54%. "Dip + bounce" (>= 30% below 7d high AND 1h >= +5%)
n=170: 2x 52%, 5x 26%, rug 3.5%, median worst-drop -41% (older/newer halves 57%/51%). Pure dips without a bounce:
2x ~30% (worse). TODO: run both entries (alone and combined, 5 slots) through the live exit with costs in
dex_runner_study.py's trading section (walk-forward, both halves); add "dip + bounce" as a SECOND trigger in
dex._try_entry only if the combined account beats the current one. Also check live: typical coin drops 45-66%
within 7 days of our entry (bigger 1h jump = deeper drop, more 5x, more rugs).


### NEXT - Listings on the DEX, then drop the crypto category (owner, 2026-09-26)
Owner: "the DEX has all the coins - eliminate the crypto category." The only proven Crypto.com edge is the listing
hunter ($200). Test: when Binance / Upbit / Coinbase / Crypto.com / OKX announce a listing (data/listing_events.csv
+ listings_study.py history), was the token already trading on a DEX (GeckoTerminal / DexScreener), and what did
buying it THERE at the announcement (DEX costs 0.3% + 1% + impact) make vs buying on Crypto.com at listing? If the
DEX version is as good or better: move the listing reactor's buys to dex.py (same scam screen), fold the crypto $200
into the DEX account (config.ACCOUNT_BASE, one-time move like rebalance_accounts), and drop the crypto card - owner
wants DEX + Stocks only.


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

## 2026-09-26 - DEX legends study (results/dex_legends_study.txt)
Price data from launch was missing for most legends (CMC/Yahoo start after the DEX launch), so "caught?" could
only be judged for PNUT (caught: peak 54.8x, live exit kept 26.7x = +$2,571 on $100). Exit ranking over 420
variants x 72 trades (3 legends + 69 real pools): ROBUST winner = no protection trail inside the 14 days and a
40% runner trail after day 14 (+$82.7k vs live +$54.5k, without best trade +$25.7k vs +$7.0k, growth 20.1 vs
11.7, both halves better). The 60%-after-3x trail, concentration caps and take-profits at 10x/50x/100x all cost
money. APPLIED to config.DEX["exit"]. Screen check: PEPE failed on transfer_pausable + is_blacklisted although
its owner is renounced (0x0) -> FIX APPLIED: owner-only flags ignored when ownership is provably renounced (no
hidden owner, no take-back, not a proxy). SHIB/BRETT/SPX/KISHU "fails" were GoPlus tax-unknown, which the live
engine defers to honeypot.is (study didn't call it). Solana legends' launch-day holders can't be rebuilt with free
data. Re-run with a paid/archival data source later for a proper caught-checkbox on every legend.

### Stocks: park idle cash in SPY between RSI2 trades (owner: "whole base invested at all times") - NEXT
Test in lab.py walk-forward: RSI2 mean-reversion as today vs RSI2 with idle cash parked in SPY (sold to fund
dips). Compare return, max drawdown, worst month, older/newer halves. If it wins, add a stocks park like
run_live.park_idle (crypto) does. Also re-check crypto: listing hunter idle cash rides breakout10 picks, which
crypto_studies A found weaker than hold BTC (+0.2% vs +1.6%/mo) - owner once rejected BTC parking; show him the numbers.

## 2026-09-26 - crypto swing study (results/crypto_swing_study.txt) -> rebalance
Only 9 Crypto.com coins trade >= $1M/day. ~1,400 dip/bounce + momentum variants (1-72h holds), 18 months,
walk-forward: nothing profitable on unseen data at 0.5%/side (best account +0.57%/mo). At 0.2%/side (maker fees,
e.g. Kraken Pro) daily "drop 8% -> sell above 5-day avg or 3d" made +0.84%/mo (+3.4%/trade CI +0.4..+6.6) - revisit
when choosing the live exchange. Hold BTC over the window: -0.02%/mo. APPLIED: official Crypto $200 (listing hunter,
2 slots ~$90 each), DEX $800 (5 x 20%), Stocks $500; $300 moved once (run_live.rebalance_accounts, equity.csv
history shifted so no fake gain/loss). Parking off (PARK_IDLE False).

## 2026-09-27 - DEX entry-filter study after GENO (results/dex_filter_study.txt) -> NO CHANGE
Question: GENO (solana pump.fun) lost -$167 of $213 (-78%) within ~1h of entry; at entry it was 6.9h old, liq $104k,
6h +258%, 24h +1830%. Would an extra entry filter have skipped such coins without costing the runners?
Method: dex_filter_study.py (workflow dex_filter_study.yml): 379 GeckoTerminal pools from the dex_runner_study registry
(incl. pools only >= 2 days old), 2026-07-07..09-26, live entry (1h >= +10%, age >= 6h, liq/vol24 >= $100k) + live exit
+ costs, 4-slot account, halves split 2026-09-03. A filtered coin can still be bought later when it passes. Variants:
6h run caps +100/200/300%, 24h caps +500/1000%, min age 12h/24h, young-and-pumped combos, liq floor $150k/$250k.
Also PNUT (only legend with hourly data) and the live screen passes (GENO: afterwards min -89%, last -88%).
Result (base: 373 trades, mean +54.8%/trade, <=-70% 6%, account +16.6%/mo, older -14.9%, newer -0.6%, maxDD -40%):
  6h > +200% skip:          <=-70% 5%, +10.5%/mo, older -34.4%, newer -0.6%, DD -71%, big winners 15/15
  24h > +1000% skip:        <=-70% 6%, +16.6%/mo (same), DD -40%, loses CONDO (+1244% -> +70%)
  min age 12h / 24h:        -33.9% / -16.8%/mo, DD -76% / -66% (24h loses ALLINU)
  age<24h & 6h>+150% skip:  <=-70% 5%, per-trade mean +57.1% (older +83.8%, newer +30.2% vs +81.7%/+28.1%) but
                            account -3.9%/mo, DD -71% (5 slots: +11.3% vs +23.9%, DD -56% vs -33%)
  liq $150k / $250k:        lose 3 / 8 of the 15 big winners (BASECAT, CALI, CODEFORMER, CONDO ...)
The GENO-type group (age < 24h and 6h > +150%) was 14 base trades with median +100%, 50% >= 2x, 21% <= -70%
(OTC +779%, 🎒 +224%, SI +230% alongside CYS -95%, SWARM -83%, BATON -82%). The filters mostly moved those entries a few
hours later (CYS still lost -95% later). Only 1-3 trades change per filter, so the account results mostly reflect which
trades happened to get a slot. PNUT was caught by every variant.
Decision: NO filter passed (fewer -70% losers AND no deeper drawdown AND about equal or better monthly in both halves
AND no big winner / legend lost). config.DEX / dex.py unchanged. GENO is the stake-sized risk the strategy accepts (20%
stake = the loss limit). Re-run with --offline on results/dex_filter_pools.json.gz or re-trigger the workflow as the
registry grows. Caveats: no buys/sells history, survivorship (rug rates are floors), liquidity estimated.
