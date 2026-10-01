# Research log

Daily deep-study notes. Newest first. Open questions at the top get studied next.

## Open questions

> WARNING: never push to branch "pending/crypto-into-dex" - its copy of paper-trade.yml has no branch filter, so a
> push there starts a live engine on that branch and cancels main's (happened 2026-09-27 02:47-03:20 UTC; that
> run's trades - a 3rd HOLDOWEEN - and its crypto->DEX move exist only on that branch and were discarded). To apply
> it, cherry-pick commit 8d347f9 onto main when the owner says yes.


### DONE 2026-09-28 - Smart-money wallets: free to track LIVE, not free to backfill; history test inconclusive (tiny) - NO CHANGE
Q (owner): can we follow "smart money" - wallets that keep buying meme coins early before big runs - with free, keyless data,
and would "N known-good wallets bought in the last hour" at our +10% entry separate runners from duds?
METHOD: tools/probe_smartmoney.py on GitHub Actions (4 runs; workflow probe_smartmoney.yml, log results/probe_smartmoney.txt +
git history, raw buyers results/smartmoney_raw.json.gz). Events = the consolidated study's 366 pool-sequential live-entry trades
(205 pools, 07-07..09-27, live exit outcome; tools/smartmoney_sample.json). Buyers = wallets with a net token inflow in a tx where
the pool (or the Uniswap v4 PoolManager) paid out tokens (EVM) / the tx signer's token balance rose (Solana). smartmoney_study.py
(offline, tests smartmoney_study_test.py): reputation only from OTHER pools of the same chain whose outcome (>= 2x peak = runner,
exit <= 0 = dud) was known before the entry; wallets in >= 20% of prior lists dropped as bots; known-good = >= 1 runner and more
runners than duds. Results in results/smartmoney_study.txt.
SOURCES (keyless, from a GitHub runner):
  GeckoTerminal /pools/{pool}/trades   WORKS on solana/base/eth: tx_from_address, kind buy/sell, volume_usd, block time. Only the
                                       last 300 trades (~7h on WOJAK; before_timestamp ignored) -> live only. 12-call burst: 6 x 429
                                       (keep >= 2 s between calls, ~30/min).
  Solana public RPC (mainnet-beta,     getSignaturesForAddress 1000/call ok, ~10 calls then 429; getTransaction needs
   publicnode; drpc failed)            maxSupportedTransactionVersion 1 now. Pools run ~1,000 tx/hour (median, max 600k/h): 40 pages
                                       reach back only ~25 h (median) -> 105 of 114 Solana entry hours unreachable; ~100k calls for
                                       Jul-Sep. NOT feasible for history.
  Blockscout base/eth (etherscan api)  works but keyless limit ~10 calls per ~20 min window: 359/400 calls 429 (run 2).
  Public EVM RPC eth_getLogs           mainnet.base.org + base-rpc.publicnode.com (20k-result cap, ~50-300 blocks/call) worked for
                                       Base: 58 entry hours + 30 launch hours in 93 min. Ethereum (publicnode) timed out / failed for
                                       every window (37 tried); llamarpc / cloudflare-eth refused.
  DexScreener (no trader API; io log empty), pump.fun (v3 needs chainId, old host dead), Birdeye / Helius / Solscan pro / Moralis
  (401 without key), Solscan web (403 Cloudflare), Solscan public v1 (404), SolanaFM (502): none usable.
RESULT (67 entries with buyers: 58 Base 07-08..08-21 + 9 Solana from the last day; runner = peak >= 2x):
  Overlap: 4,687 wallets in 70 pools; 307 in >= 2 pools, 86 in >= 3; 5 bot-like (in 15-26 pools, runner:dud ~ base rate).
  Non-bot wallets early in >= 2 runner pools: 104 vs 73 with shuffled labels (95th pct 113, p = 0.13) - not significant.
  Walk-forward: known-good wallet(s) in the hour before entry fired on only 3 of 67 entries (all in the newer half, Aug 13-21;
  1 runner = BASECAT +3650%, 2 mids); 0 fired in the older half. Known-good wallet among the launch buyers: 8 entries, 38% runners
  vs 19% baseline (3 of 8, incl. BASECAT; 4 duds). Wallets are mostly "bad" (32 entries had more known-bad than known-good) because
  duds outnumber runners 3:1. Far too few firings to trust either way; no half-split test possible.
DECISION: nothing to change in dex.py. Smart money cannot be backfilled for free on Solana (our main runner chain), so the only
honest test is forward. Probe/collector left as a tool; the 95-min workflow re-runs only on edits to its two files.

### DONE 2026-10-01 04:30 - Tighten the DEX (owner: "we're losing our ass") -> EXPERIMENT 6 (entry needs 6h >= +50%), 3b undone
Q: what separates the live losers from winners? METHOD: (1) dex_tighten_study.py on the consolidated 205 cached pools (same
account as dex_consolidated_study, 10 slots, halves + 300 resampled accounts); (2) NEW dex_live_replay_study.py on the engine's
own scanner log data/dex/scan/*.csv.gz (09-27..09-30, 13,969 pairs, 111 live-entry trades; dead coins included, so NO
survivorship bias - the earlier studies only saw pools >= 8 days old; scam screen not replayable; ~2 days of follow-up).
RESULTS: entry by the 6h move before the +10% hour - live replay: 6h < +50% n 73, sum per $1 -6.0 (2x) / -9.8 (no sell), both
halves negative under all 7 exits; 6h >= +50% n 38, +6.8 / +13.4. Backtest per trade: 6h 0..+50% n 360 mean +11% median -7%;
+50..200% mean +113% median +9%; > +200% mean +145% median +45%. Account "need 6h >= +50%": older/newer +626% / +507% with
3x stake back vs live +392% / +364% (2x), resampled medians higher in both halves, maxDD -18% vs -26%. Exit: 3x stake back beat
2x in both data sets (backtest both halves; live replay +9.3 vs +6.8 on the 6h >= +50% trades) -> 3b undone, stake back at 3x.
CAVEAT: the backtest's monthly numbers are far too rosy (survivorship); the live replay is only 4 days. Judge on live results.

## Hourly check fixes
- 2026-09-30 09:40 UTC: the engine's 09:05 hourly save never reached GitHub (one pull + push attempt; other sessions push
  every minute; a dirty tracked file also blocks a plain rebase). The end-of-run save of the run my fix push replaced
  failed the same way, so ~1.5 h of DEX paper trades were lost (08:05 -> 09:44: ASTEROID sold, BOTIFY and SI bought;
  that run showed $974.14, the restored 08:05 state $1,004.22). Fix (e973fb9): git_sync and the end-of-run commit retry
  5x with --autostash and abort failed rebases; tested against a racing bare remote.
- 2026-09-30 22:30 UTC: moon alerts never reached the phone - the rocket emoji in the title isn't allowed in an HTTP
  header ('latin-1' error at the AIRPAD 2.1x alert, 19:06). Fix: non-latin-1 titles go RFC 2047-encoded (ntfy decodes
  them); regression test in moon_alerts_test.py. AIRPAD itself faded back to 0.26x - no alert missed now.

- 2026-10-01 05:30 UTC: AIRPAD sold at 8e-06 (2026-09-30 22:34) on bad DexScreener-profile readings for its real pool
  (1/50th of the price, $5.7k liquidity, on and off for hours). A 20x+ drop between readings now needs 15 min of
  readings before a stop / rug sale (dex.py _confirmed; test_far_off_tick_needs_15_minutes). Cost: ~$33 vs a real-price sale.

## EXPERIMENTS LOG (owner 2026-09-28: experiment directly in the main paper account; log what works, keep winners)
| # | Started (UTC) | Change | Judge at | Baseline | Result |
|---|---|---|---|---|---|
| 1 | 2026-09-28 12:40 | DEX: 10 coins x ~10% (tiers A 10% / B,C 12.5%) instead of 5 x 20-25% | ~2026-10-12 | DEX -39% after 13 closed trades on 5 slots | pending |
| 2 | 2026-09-28 19:00 (first trades 09-29: AMZN, IWM, COIN) | Stocks rsi2: buy at RSI(2) < 25 (was < 15), 3 x 33%, hold 10d, no parking (stock_rsi2_loosen_study) | ~2026-11-28 | backtest 24y: +17.0% / +21.6% CAGR per half, DD 25% / 23%, 60-66% invested; live: 0 trades on day 1 | pending |
| 3 | 2026-09-28 20:50 | DEX: at 3x sell the stake (~1/3) once; the rest rides the current rule | ~2026-10-28 | BABYCALI 2026-09-28: 4.3x peak (+$346 paper) then -95% within ~40 min, sold at -$101 | pending |
| 4 | 2026-09-29 05:40 | DEX: max hold 7 days instead of 14 (runner rule at day 7) | ~2026-10-20 | DEX frozen: $8 cash, 4 coins locked up to 12 more days; consolidated study resampled 7d > 14d both halves | pending |
| - | 2026-09-29 ~14:00 | DEX SEASON 2: account restarted at $1,000 (season 1: -$700, archived in data/dex/archive/season1/). Experiments 1, 3, 4 are measured from here | - | season 1 | - |
| 5 | 2026-09-30 21:40 | DEX: no price stop inside the hold (95% trail removed); rug check + 7-day limit + stake-back remain | ~2026-10-14 | 95% trail sold SS at the wick bottom (-$93; +417% after), BABYCALI +30% after | pending |
| 3b | 2026-09-30 23:30 | DEX: take the stake back at 2x (sells ~half) instead of 3x; the rest rides free, no stop | ~2026-10-28 | live: 3 of 3 coins that doubled went on to lose 79-99% (BABYCALI 4.3x -> -$101, SS 2.1x -> -$93, AIRPAD 2.05x -> -$93); with this rule each ends about break-even or better (~+$290 on the DEX). Cost: a legend keeps about half its multiple (PNUT 30x -> ~16x); the floor study's half-at-2x variant was mixed by half | UNDONE 2026-10-01: 3x kept more than 2x in both studies below |
| 6 | 2026-10-01 04:30 | DEX entry: buy a +10% hour only if the coin is already up >= +50% over 6h (was: any 6h) | ~2026-10-22 | live season 2: 6 of 6 buys with 6h < +50% are down (TIBBIR, ASTEROID, FARTCOIN, ZCAT, SHARTCOIN, MORI); replay of the live scanner log (111 trades, no survivorship): 6h < +50% lost under every exit in both halves (-$6 per $73 bet), 6h >= +50% +$7 per $38; 205-pool backtest: wins both halves and resampled, maxDD -25% -> -18% | pending |
Queue (one or two per area at a time): entry filters (younger coins at small size, LP-lock 50-95%, buy/sell ratio),
exits (7-day hold, half off at 2x), stocks dip rules, smart-money signal (after ~4 weeks of wallet_trades).

### NEXT - live wallet tracker (smart money, forward test; no engine change)
IN PROGRESS: tracker live since 2026-09-28 (first data commit 09:27 UTC); re-run smartmoney_study.py on wallet_trades after
~4 weeks; adopt only if known-good wallets raise the runner rate in both halves with >= 20 firings each.
HOW: tools/wallet_tracker.py (tests wallet_tracker_test.py), own workflow wallet_tracker.yml at :17/:47 every hour, 8-min
budget, commits ONLY data/dex/wallet_trades*.csv.gz + data/dex/wallet_tracker_state.json (engine never restarted). Each run
polls <= 25 pools screened (any verdict) in the last 48h or held (held x4, PASS < 12h x2, stalest first), GeckoTerminal
/pools/{pool}/trades, >= 3 s between calls (x1.5 after each 429, max 8 s; 20/40/60 s backoff; stop after 12 x 429).
Columns time, chain, pool, token, sym, side, wallet (tx_from_address), usd, price, tx (20-char prefix; first run full).
Trades < $10 not logged (from run 2). One gzip member appended per run; file renamed wallet_trades_<date>.csv.gz at
40 MB -> read data/dex/wallet_trades*.csv.gz. Dedupe: per-pool high-water mark + capped seen-id hashes.
First run (09:25 UTC, 2.1 s gap): 25 selected, 15 polled, 23 calls, 8 x 429 (run stopped at the 429 cap), 4,500 trades
(300 = GT cap on every pool, back to 09-27 13:55), 1,767 wallets, 366 KB. Busy pools (BABYCALI ~2,100/30 min, CATE, ANTFUN)
exceed 300 trades per poll interval, so their log has gaps - fine for "who bought early", note it in the study.
Run 2 (09:31 UTC, new pacing): 25/25 polled, 30 calls, 5 x 429 (all retried ok; gap widened to 8 s), 7,113 new trades,
4,656 logged >= $10 (~42 B/row gz, ~4-9 MB/day expected).
For the study: label pools from snapshots / outcomes (>= 2x within 14 days vs <= 0); walk-forward reputation, bot filter,
older/newer halves. Optional: Base history via mainnet.base.org getLogs; free Blockscout / Helius keys - owner decision.

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

### DONE 2026-09-27 16:30 - Profit floor below 2x (TEXTIT: +104% in 2h -> +6%, -24% low): NO CHANGE, keep the live exit
Q: should a coin up big early get a floor, so a TEXTIT round trip can't happen? METHOD: dex_floor_study.py (890211d,
results adcefb8, results/dex_floor_study.txt; hourly dump results/dex_floor_hourly.json.gz, re-run with --from-dump):
dex_runner_study's pool selection (349 pools, 2026-07-07..09-27, hourly GeckoTerminal) through the engine's entry (1h
>= +10%, age >= 6h, liq/vol24 >= $100k; 1 trade per pool at a time, 1-day cooldown), 0.3% fee + 1% slip + impact per
side, rugs -95%, 5-slot compounding account, halves split at the median entry (Sep 1); + dex_legends_study's coins
(PNUT/AKITA hourly, others cached daily bars) with the live entry and a "caught early" entry (first +10% bar).
RESULT (monthly full / older / newer, maxDD, 2x-rate, avg winner; legends lost = < 80% of the live multiple where live >= 5x):
  current (14d hold, no stop, >=2x at day 14 -> 40% trail)  +44.0% / -2.9% / +275.8%  -46%  12%  +179%  -
  a) peak +50% -> floor break-even                          +24.0% / -12.2% / -37.6%  -38%   8%  +121%  none
  b) peak +75% -> floor +25%                                +10.4% / -15.4% / +60.9%  -37%   7%   +76%  none
  c) peak +100% -> 40% trail from peak                      +58.0% / -14.4% / +464.9% -40%   9%   +81%  PEPE 110x->31x, POPCAT, BRETT, PNUT 30x->1.9x
  d) peak +100% -> floor +50%, 3x -> 50% trail              +44.5% / +15.9% / +194.0% -37%   7%   +75%  PEPE, BONK, POPCAT, BRETT, PNUT 30x->1.6x
  e) half at +100%, rest current rule (moon bag)            +28.7% / -4.7% / +173.8%  -47%  12%  +110%  all big ones halved (PNUT 15.9x)
  e') same via dex.py tp1 (no clock, break-even stop)       -2.1% / -19.3% / +73.7%   -52%  10%   +92%  BONK, BRETT, FARTCOIN, PNUT
Floors a/b catch the TEXTIT shape (a: most trades that peak +50% then exit at break-even; b: 25/206 still lose vs
52/163 live) but cut the big winners' tails: avg winner +179% -> +76..121% and 2x-rate 12% -> 7-8%, so they lose in
both halves. c/d each win one half but lose the other and cut PNUT/PEPE-style runners early (the runner trail needs
the 14-day clock to let the early +100% shakeouts pass). An offline cross-check on dex_filter_study's pools (199,
dex_filter_pools.json.gz) gave the same ranking. DECISION: no variant beats the current rule in BOTH halves while
keeping the legends -> config.DEX["exit"] unchanged. TEXTIT-style give-backs are the price of riding the 30-90x runners.

### QUEUED (owner, 2026-09-27) - bigger bets on proven runners, account brake, big-win playbook
1. Pyramiding: add to a held coin once proven (>=14d old, >=2x, big liquidity/holders, or listed on a major
   exchange) with a trail protecting it; does it beat no-add without Luna-style wipeouts?
2. Account-level brake: stop new buys / tighten exits after a 20-25% drawdown from the account high - test levels.
3. Big-win playbook: take the stake back at 2x, moon bag on the 40% trail, bank chunks at milestones; tax set-aside.

### DONE 2026-09-28 05:40 - REVERTED the "data flags never sell a held coin" change (8a6b3cb, 2026-09-27 19:20)
It was decided on 6 exits (5 of 6 worth more after the sale). 10 hours later the after-sale prices flipped:
HOLDOWEEN qYCU -100% after we sold (holding: -$148), ARENA ("missing metadata") -99% (-$101), 7 -59% (-$62);
winners missed: SDOG +$49, ANTFUN +$30, HOLDOWEEN Bxft +$4. Data-flag exits saved about $230 net. Lesson: re-screen
data flags DO carry rug information on Solana pump pools; and after-sale grades need days, not hours - never change a
scam rule on < 24h of after-sale data. Back to: contract flags / "missing metadata" exit at once, data flags on 2 strikes.

### (older) Re-screen "safety data" exits: are they selling good coins? (2026-09-27)
All 4 DEX sales so far were emergency exits on re-screen DATA flags (holders/LP holders unknown, RugCheck
"lp locked 0%"), none on a real rug. tools/sold_followup.py after them: ANTFUN -1% (good sell), SDOG +37%
(high +71%, too early, ~$32 missed), HOLDOWEEN qYCU +2%, HOLDOWEEN Bxft -6% (good sell). Net: holding would
have been +$30. Coins that PASSED the entry screen later fail the same data checks - likely flaky Solana
LP/holder data on pump.fun pools, not new danger. 4 trades is too few to loosen scam protection: keep
collecting; test = replay every re-screen data-flag exit in outcomes.csv vs later snapshots; if data-flag
exits keep losing vs holding while zero turn into rugs, require a real change (liquidity drop, mint/freeze,
owner) before an emergency exit instead of "data unknown".

### DONE 2026-09-27 22:30 - Is the live DEX strategy profitable at all? Reconciled: yes in simulation, but thin and lumpy - NO CHANGE
Q: the SAME live entry/exit gave runner +101%/mo, floor +44% (-3% / +276%), filter +16.6% (-14.9% / -0.6%), age -26.3% / -0.1%.
Which is right? METHOD: dex_consolidated_study.py (offline, results/dex_consolidated_study.txt): union of the cached hourly grids
(floor dump 183 + filter dump 205 -> 205 pools; the floor pools are a subset with identical grids; the runner study keeps no price
paths, only labels, so it can't be replayed), window 2026-07-07..09-27, 3,464 signal hours. Live rules: 1h >= +10%, age >= 6h,
liq >= max($100k, 50 x tier-A stake), vol24 >= $100k (buys > 1.2 x sells NOT replayable); config.DEX["exit"] via
dex_floor_study.simulate (14d, no stop, >= 2x at day 14 -> 40% trail, rugs -95%, 0.3% + 1% + impact per side). Account like
dex.py: $1,000, 5 slots, 20% (25% for age >= 7d / liq >= $1M / vol24 >= $1M), <= 0.5% of pool liquidity, one per pool and symbol,
1-day cooldown; a skipped signal does NOT lock the pool. Halves split at the median entry (Sep 3; older 1.9 months, newer 0.8).
300 resampled accounts dropping 30% of signals by coin-day (a pump's hours together) and by single hour.
RESULT (monthly; resampled = median [p10..p90], coin-day unit):
  variant          actual older / newer   maxDD | resampled older          | resampled newer
  14d, 5 slots LIVE   +56.2% / +577.7%    -49%  | +42.6% [-10.4..+128.3]   | +372.5% [+102.3..+1024.0]
  7d,  5 slots       +516.2% /  +53.1%    -43%  | +301.8% [+57.2..+561.5]  | +1106.1% [+60.7..+2517.9]
  10d, 5 slots         -4.4% /  +65.8%    -54%  | +60.3% [-4.4..+188.6]    | +188.6% [+27.6..+1069.5]
  14d, 8 slots        +32.3% / +612.7%    -33%  | +57.8% [+13.1..+118.9]   | +428.3% [+146.6..+689.0]
  14d, 10 slots       +81.1% / +522.3%    -20%  | +66.1% [+30.7..+153.1]   | +332.1% [+119.2..+515.5]
Per trade (14d, pool-sequential, n 366): mean +57.9%, median -7.4%, 2x-rate 13%, <= -70% 5%, rug 2% (older +84.6% / newer +31.2%
mean). 7d: mean +50.5%, 2x 9%; 10d: +58.1%, 2x 10%. The edge is a fat tail: the typical trade loses ~7-11%, 1 in 8 doubles.
WHY THE STUDIES DISAGREED: (1) account model - the earlier studies pre-lock each pool for 14 days at its first signal even when the
account skipped it; the live bot doesn't. On the same 205 pools the pool-locked list gives -14.8% / -5.8% (5 slots; resampled
median +3.4% / +72.8%) vs +56.2% / +577.7% event-driven; 15 of 24 older and 9 of 10 newer live-account trades are re-entries the
pool-locked list never has (re-entry signals have the same mean, +58%, so it is luck of timing, not a bias). (2) slots: filter and
runner used 4 slots (dex_exit_study default), floor/age 5: same list -6.1%/+58.9% at 4 vs -13.5%/+37.2% at 5. (3) pool sets and
windows: runner's +101% was its 09-26 run (346 pools, older exit); its 09-27 re-run said -3.6%. (4) one trade decides a half: with
~30 trades in 2.7 months, SEND +1,231% is $3,189 of the newer half's $3,618 gain (without it +122%/mo); moving the split by +3 days
turns the newer half from +578% to -36%. Even the studies themselves don't reproduce: dex_floor_study --from-dump now gives
+25.7% / -13.5% / +37.2% (was +44% / -2.9% / +276% on the live fetch), dex_filter_study --offline +18.5% / -22.1% / -33.8%.
DECISION: the median resampled month of the live rules IS positive in both halves (+42.6% older, +372.5% newer; hour-unit +55.5% /
+694.7%), so no rethink is forced - but it is thin in the older half (p10 -10%, pool-locked median +3%), rests on 1-2 big winners
per month, survivorship inflates it (early rugs missing, rug rate 2% is a floor), and the newer half is only 0.8 months. No hold /
slot variant is better in both halves AND in the actual account (7d wins the medians but loses the actual newer half, 10d is worse
than both 7d and 14d = path noise; 8/10 slots cut drawdown -49% -> -33%/-20% but lose the newer-half median) -> config unchanged.
Re-run when the snapshot logs (buys/sells) and ~2 more months exist; watch 10 slots (lower drawdown) and 7d (more turnover).

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

## 2026-09-28 - rsi2 loosen study (results/stock_rsi2_loosen_study.txt) -> APPLIED: rsi2 buys at RSI(2) < 25 (was < 15)
Question (owner: the stocks account made no trade on its first day, wants the money working, "all in"): rsi2 only
buys names with RSI(2) < 15 above their 200-day average. Does a looser entry (20/25/30/35), parking idle cash in SPY
while SPY > its 200-day average, or a 5-day hold (vs 10) beat the live setup?
Method: stock_rsi2_loosen_study.py (workflow stock_rsi2_loosen_study.yml, commit acfdef8, results 94dca1d) on
stock_park_study's machinery (simulate now takes rsi_max / hold; defaults = live, re-run b3f1ba04 unchanged apart from
one more day): 38-name live universe, Yahoo daily 2002-08 .. 2026-09, 0.05%/side, signal at close / fill next open,
3 slots x 1/3, no reserve, exits unchanged; 20 variants fixed in advance; halves 2002-14 / 2014-26 from a flat $500,
each also without the hindsight names (NVDA TSLA PLTR COIN MSTR AMD AVGO META NFLX UBER) and at 3x cost. Rule
(pre-registered): CAGR better than live in all 6 runs and max DD at most 5 points deeper in each; best minimum margin wins.
Result (CAGR / max DD / % invested / trades per yr; older | newer half; full universe):
  rsi<15 hold10 (live)      +17.0% / 25% / 60% / 125 | +21.6% / 23% / 66% / 138
  rsi<20 hold10             +18.8% / 26% / 68% / 143 | +24.7% / 26% / 74% / 156   PASS
  rsi<25 hold10             +22.3% / 25% / 73% / 158 | +25.2% / 25% / 79% / 170   PASS (winner, min margin +0.9%)
  rsi<30 hold10             +24.1% / 25% / 77% / 171 | +24.4% / 28% / 84% / 182   fail: 3x cost newer +10.2% vs +10.8%, DD 41%
  rsi<35 hold10             +23.4% / 24% / 81% / 183 | +22.5% / 27% / 87% / 191   fail: 3x cost newer +7.9%, DD 45%
  rsi<15 hold5              +14.3% / 21% / 58% / 143 | +19.0% / 27% / 64% / 161   fail (worse everywhere; loosened hold5 also fail)
  rsi<15 hold10 +SPY>200d   +15.6% / 29% / 86% / 125 | +20.5% / 29% / 91% / 138   fail (worse in both halves)
  rsi<25 hold10 +SPY>200d   +22.1% / 25% / 89% / 158 | +23.2% / 28% / 93% / 170   fail (-hindsight newer, all 3x cost)
  hold SPY                  +9.0% / 55%                | +13.6% / 34%
rsi<25 in the checks: -hindsight +13.0% vs +10.0% | +8.6% vs +7.3% (DD 17% / 19% vs 17% / 24%); 3x cost +10.0% vs
+7.7% | +11.8% vs +10.8% (DD 33% / 32% vs 33% / 30%). Days holding >= 1 rsi2 name: 88% / 92% vs 79% / 83%.
Parking in SPY raises "invested" to ~90% but costs return in every half once costs or the hindsight names are
taken out (the SPY leg drags when rsi2 is sold out of it at dips). A 5-day hold cuts winners short.
Decision: APPLIED config.RSI2["rsi_max"] = 25 (strategy.RSI2MeanReversion reads it; run_live's "closest to a buy"
line shows the live threshold; test stock_strategies_test.test_rsi2_entry_threshold). No parking, hold stays 10 days.
It will not make the account "all in" (~75-80% invested on average; cash still waits on calm days) but the extra
dips it buys earned more in every test. rsi<20 also passed; 25..30 form a plateau, so 25 is not a lone spike.
Caveat: universe is today's list (hindsight) - absolute returns are a ceiling. Experiments log #2.

## 2026-09-27 - stock parking study (results/stock_park_study.txt) -> parking NOT applied; rsi2 now 3 x 33%, no reserve
Question (owner: "whole base invested at all times"): the official stocks account (rsi2, $500) was ~48% invested. Does
parking the idle cash in SPY or QQQ (sold just enough to fund each rsi2 buy) beat plain rsi2? vs just holding SPY/QQQ?
And does rsi2 with more slots / bigger positions (less idle cash, no parking) do better?
Method: stock_park_study.py (workflow stock_park_study.yml, commits e2cdc41 + 0aa0b67, results 6f59cfb + 8620866):
Yahoo daily bars 2002-08 .. 2026-09 (24 years) for the live universe (38 names), live rsi2 rules (RSI2 < 15 above the
200-day avg, lowest first; exit close > 5-day avg / RSI2 > 70 / 10 calendar days), signal at the close, fill next open,
0.05%/side on every rsi2 AND parking order, $10 min order. Parking: rsi2 exits/entries first (parked ETF sold for the
shortfall), spare cash > 2% parked. No tuned parameters, so the walk-forward is the two halves, each from a flat $500.
Result (CAGR / max drawdown / % invested; older half 2002-14 | newer half 2014-26):
  rsi2 live 5x18% + 10% reserve  +12.2% / 19% / 44%   | +14.9% / 21% / 52%
  rsi2 + park SPY                +10.7% / 52% / 100%  | +17.3% / 31% / 100%   (loses the older half)
  rsi2 + park QQQ                +13.9% / 52% / 100%  | +18.2% / 38% / 100%   (DD > SPY's 34% in the newer half)
  rsi2 + park only if >200d avg  SPY +11.3%/24%, QQQ +12.1%/26% | SPY +14.9%/28%, QQQ +17.0%/31%  (not better both)
  rsi2 10x10% / 8x12.5%          +9.0% / +10.2%       | +12.0% / +13.6%       (more slots = more idle cash, worse)
  rsi2 5x20% no reserve          +13.5% / 21% / 49%   | +16.5% / 23% / 57%    PASS
  rsi2 3x33% no reserve          +17.2% / 25% / 60%   | +21.4% / 23% / 66%    PASS  (Sharpe 1.06 / 1.09 vs 1.04 / 0.98)
  rsi2 2x50% no reserve          +22.3% / 28% / 67%   | +20.5% / 30% / 72%    PASS  (worst month -19%)
  hold SPY                       +9.0% / 55%          | +13.7% / 34%
  hold QQQ                       +13.7% / 53%         | +19.0% / 35%
rsi2 + QQQ parking ~= holding QQQ (same return, same drawdown): the parking leg dominates and rsi2 adds nothing on top.
Parking is also cost-fragile: ~300 parking orders/yr; at 3x costs (0.15%/side) park SPY drops to -1.8% | +2.7%/yr while
rsi2 3x33% stays ahead of live (+7.8% vs +5.4% | +10.7% vs +7.0%). Without the hindsight names (NVDA TSLA PLTR COIN MSTR
AMD AVGO META NFLX UBER) 3x33% still beats live in both halves (+10.0% vs +7.7% | +7.6% vs +6.0%, DD 17% / 24% vs 14% / 18%).
Decision: parking in SPY/QQQ NOT applied (fails the rule: better return in BOTH halves with a drawdown no worse than
holding SPY). APPLIED instead: rsi2 3 slots x 33% with no cash reserve (config.RSI2; engine.step honours a strategy's own
cash_reserve, other strategies keep the 10% reserve). It passed every check; 2x50% is stronger in the older half but
weaker newer and deeper (-19% worst month, 43% DD at 3x costs), so 3 slots is the middle choice. Invested time rises to
~63%; the rest is cash only because no dip qualifies. Existing positions exit normally; new buys wait for < 3 open.
Caveat: today's universe (hindsight); absolute returns are a ceiling. Test stock_strategies_test.test_rsi2_sizing.

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

### DONE 2026-09-27 (see the dated entry "stock parking study") - Stocks: park idle cash in SPY between RSI2 trades (owner: "whole base invested at all times")
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

## 2026-09-27 - DEX minimum-age study (results/dex_age_study.txt) -> NO CHANGE (min age stays 6h)
Question: every big DEX mover missed on 2026-09-27 afternoon was younger than the 6h minimum age (NEARPAD +195% at
1-3h, liq $65-120k; METAMUSE +186% at 1-2h; VAULT +86% < 1h; GTA 6 COIN +64% at 2h). Raising the age hurt
(dex_filter_study); does LOWERING it to 1h / 2h / 3h / 4h help?
Method: dex_age_study.py, offline on results/dex_filter_pools.json.gz (205 pools, 2026-07-07..09-26; 61 of the 71
pools launched inside the window have hourly bars from their first 2 hours, so < 6h entries are visible; the first bar
counts, 1h change = its close / open). Live entry (1h >= +10%, liq / vol24 >= $100k) + live exit, 0.3% fee + 1%
slippage + impact per side, rugs -95%, 5-slot compounding account, halves split 2026-09-03. Variants: min age
1/2/3/4h; young (< 6h) entries only at liq >= $150k / $250k; young entries at half size. Rug stress: young rug rate
doubled (worst young losers -> -95%), and a harsh one doubling the young <= -70% rate. Because the 5-slot account
takes only ~32 of ~380 signals (14-day holds keep slots full), a resampled account was added too (300 runs, each
drops a random 30% of signals, same drop in every variant).
Result:
  6h (live):          381 trades, account +7.5%/mo (older -26.3%, newer -0.1%), maxDD -53%; resampled median -14.2% / +6.2%
  1h / 2h / 3h:       +28 young entries (mean +597% / +440% / +259%, >=2x 43/32/32%, <=-70% 25%, rug 4%);
                      account +7.5%/mo, older -26.3% (same), newer -28.5% (WORSE: young SOLCAT -93% took the slot
                      KITTY +115% had), maxDD -53%; resampled -11.3% / ~0% (newer worse)
  4h:                 16 young entries, account identical to 6h; resampled -10.3% / +3.6% (newer worse)
  young liq $150k/$250k: fewer young losers (<=-70% 21% / 8%) but account = 6h exactly; resampled newer ~equal-worse
  young half size (1-3h): account older same, newer -19.4% (worse); resampled -11.3% / +8.2..9.0% (better, also
                      under both stresses) - the only near-miss
Young entries are the lottery tail: CATE (+6024% at 1.5h), STONKEX, BASECAT, OTC, GTR carry the mean, but 25% of
them lost >= 70% (6% for >= 6h entries: SOLCAT, FAMILIARS, ETN, MOONKEY, STOCKER, VOSF). And these rates are FLOORS: the
dump only holds pools the 6h rule also traded, so pools that pumped at 2h and died before 6h are missing.
Decision: NO variant improved the monthly return in BOTH halves of the actual account; config.DEX / dex.py unchanged,
scam checks unchanged. The account barely changes because the slots are almost always full when a young pool pumps.
Watch: "young at half size" won the resampled account in both halves and both stress tests - re-test when the live
snapshots (data/dex/snapshots.csv) hold enough real < 6h pools, incl. the ones that died young (no survivorship).
