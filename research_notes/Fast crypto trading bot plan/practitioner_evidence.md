# Practitioner Evidence on Automated Short-Term Crypto Bots (Small Accounts)

Scope note: Research done 2026-09-25. Many primary pages (freqtrade.io, pionex.com, dev.to, substack, halborn, siliconangle, brookmiles.github.io) were blocked by the network proxy, so several findings below rely on search-result snippets rather than full-page reads; these are marked "(snippet)". Evidence labels: **[SYSTEMATIC]** = structured backtest/study with stated methodology; **[ANECDOTAL]** = individual user report, forum/GitHub issue, blog; **[VENDOR]** = exchange/bot-vendor marketing or docs (conflict of interest).

## 1. Which strategy families hold up live (Freqtrade / Jesse / Hummingbot communities)?

### Takeaway
No public, audited live leaderboard exists that shows durable positive returns for retail short-term bot strategies; practitioner reports cluster around "backtest looks great, dry-run/live is materially worse." The families with the most defensible practitioner support are slow trend/regime-filtered exposure and flow/carry-type edges, not high-frequency indicator strategies or retail market making.

### Cited Findings
- [ANECDOTAL] Freqtrade user, Keltner Channel + RSI on Binance spot, 6h candles, 1000 USDT, Jan-Apr 2023: backtest -8.97% (175 trades, 28.6% win rate); live monthly results +9.60%, -10.95%, -13.42%, -3.70%. User observed live entries/exits happen "slightly late" vs backtest signals. — [freqtrade issue #8518](https://github.com/freqtrade/freqtrade/issues/8518)
- [ANECDOTAL] Freqtrade users report dramatic backtest-vs-dry-run gaps, e.g. ~1% drawdown / 70% win rate in backtest vs ~10% drawdown / 35% win rate in dry-run; another reported 50-100 trades/month in backtest vs ~50 trades/day in dry-run with the same setup (snippet). — [freqtrade issue #8451](https://github.com/freqtrade/freqtrade/issues/8451); [freqtrade-strategies issue #237 (Zeus strategy)](https://github.com/freqtrade/freqtrade-strategies/issues/237); [issue #7248 (resampled timeframe)](https://github.com/freqtrade/freqtrade/issues/7248); [issue #12894 (signals differ on 5m/30m)](https://github.com/freqtrade/freqtrade/issues/12894)
- [VENDOR/DOCS] Freqtrade's own docs: backtesting assumes all orders fill (dry/live may not with limit orders or low volume) and assumes entry at next candle's open; they advise always dry-running after backtesting and checking that signals appear on the same candles in both modes (snippet). — [Freqtrade Backtesting docs](https://www.freqtrade.io/en/stable/backtesting/)
- [ANALYST BLOG] Robot Wealth: trend effects persist across many crypto assets because crypto is fragmented, hard to value, retail-heavy and leveraged, but trend is "harder to be confident in than flow-based edges"; they highlight retail-flow-as-contrarian and perp funding carry as more robust edges (snippet). — [Robot Wealth: To Trend or Not To Trend](https://robotwealth.com/to-trend-or-not-to-trend-wrong-question/); [Robot Wealth: Cheat Code for Crypto](https://robotwealth.com/a-cheat-code-for-crypto/); [Robot Wealth: Art and Science of Carry](https://robotwealth.com/the-art-and-science-of-trading-carry/)
- [VENDOR/DOCS] Hummingbot: market making "is not a risk-free, always profitable trading operation"; paper trading differs from live because live accounts for order latency and bot errors in extreme conditions (snippet). — [Hummingbot: What is Market Making](https://hummingbot.org/blog/what-is-market-making/); [Hummingbot PMM docs](https://hummingbot.org/strategies/v1-strategies/pure-market-making/)
- [ANECDOTAL] A Hummingbot-related Substack post titled "How I lost 20% in 20 minutes" exists (content not retrievable). — [thecryptoquant substack](https://thecryptoquant.substack.com/p/how-i-lost-20-in-20-minutes)

### Inferences
- For a $500 spot account on Coinbase/Kraken/Crypto.com, retail market making is structurally disadvantaged: taker/maker fees at low-volume tiers are typically much larger than the spreads on liquid pairs, and inventory risk dominates. (Inference; fee tiers not verified in this pass.)
- Carry (perp funding) is not available on a spot-only setup, so the practitioner-favoured edge left is trend/regime-filtered exposure.
- A realistic prior for "typical live monthly return" of retail indicator bots is roughly zero-to-negative after costs, with double-digit monthly drawdowns possible (based on the anecdotes above; not a systematic figure).

### Gaps
- No public, verified Freqtrade/Jesse/Hummingbot live leaderboard with monthly returns/drawdowns was found. (FreqAI/strategy-ninja-style leaderboards of dry-run bots exist in the community historically, but I could not access or verify them.)
- No Jesse community live-performance data found.

## 2. Exchange grid and DCA bots (Crypto.com, Pionex, 3Commas): trending vs ranging; bag-holding

### Takeaway
Even vendors concede grid bots underperform buy-and-hold in strong uptrends (capital sits idle in unfilled buy orders) and lose in sustained downtrends (bot ends up fully in the falling coin). DCA "safety order" bots convert drawdowns into larger positions and leave "red bags" when the market dumps.

### Cited Findings
- [VENDOR] Pionex: in a strong bullish trend with few pullbacks, the grid bot is less profitable than holding spot, because it does not hold 100% position — a portion of capital is reserved for limit buys, lowering capital utilisation (snippet). — [Pionex Grid Bot Guide](https://www.pionex.com/blog/grid-bot/); [Pionex: Can a grid bot lose money in a bear market?](https://www.pionex.com/blog/we-lost-because-of-bearish-market-grid-trading-ideal-for-fluctuate-bullish-market/)
- [ANECDOTAL] A 150-day test with $1,000 across two Pionex bots reported ~30% on a BTC/USDT grid, but the tester attributed most of the gain to BTC appreciation rather than grid trading (snippet via review aggregator). — [Gainium Pionex review](https://gainium.io/review/pionex)
- [VENDOR] 3Commas: grid bots' "biggest weakness" is trending markets; trailing up/down grid shifting is offered as mitigation (snippet). — [3Commas Grid Bot](https://3commas.io/grid-bot); [Gainium best grid bots](https://gainium.io/best/grid)
- [ANECDOTAL/COMMUNITY] 3Commas DCA users describe being left with "significant red bags" after market dumps and using buy-only grids afterwards as a "recovery" approach (snippet). — [Recovery Grids (community doc)](https://docs.superhuman.com/@tjuh1/recovery-grids)
- [VENDOR/THIRD-PARTY] Typical DCA config example: $100 base order + five increasing safety orders at 2% drops; DCA bots "carry risk, especially in strongly trending markets without proper stop-loss" (snippet). — [Bitget Academy 3Commas setup guide](https://www.bitget.com/amp/academy/12560603876807); [3Commas DCA FAQ](https://help.3commas.io/en/articles/11865862-dca-bot-faq)

### Inferences
- Grid/DCA return profiles are short-volatility: many small wins, occasional large losses when range breaks down. High win rates in marketing screenshots are expected and uninformative.
- Martingale-style safety orders are incompatible with a $500 account aiming for fast growth: the geometric order sizing exhausts capital within a normal crypto drawdown (e.g. 5 safety orders at 2% steps cover only ~10% decline, while alt drawdowns of 30-50% within a month are common). (Inference.)
- If a grid is used at all, it should be gated by a regime filter (range detection) and have a hard lower-bound stop.

### Gaps
- No systematic, independent study of Crypto.com Trading Bots' realised user returns was found; Crypto.com does not appear to publish aggregate user bot P&L.

## 3. Momentum rotation (top-N by momentum with BTC regime filter)

### Takeaway
The one reproducible public backtest found shows naive top-N crypto momentum rotation lost money 2021-2026 and badly lagged equal-weight buy-and-hold; a BTC 200-day filter cut max drawdown roughly in half but acted as risk control, not alpha.

### Cited Findings
- [SYSTEMATIC, single open-source backtest] Universe: 10 large-cap USD pairs (BTC, ETH, SOL, BNB, XRP, ADA, AVAX, LINK, DOT, LTC), 2021-01-01 to 2026-05-25; top-3 by trailing 60-day return, monthly rebalance, equal weight, 10 bps round-trip costs. Results: naive V1 annual return -7.7%, Sharpe -0.16, max DD -89.8%; V2 with BTC>200DMA filter +10.8%, Sharpe 0.14, max DD -53.8%; equal-weight benchmark +35.6%, Sharpe 0.42, max DD -81.9%. Author: naive momentum "anti-selects at turning points" (top 60-day winners are late-cycle names that mean-revert harder); t-stat vs benchmark -2.5; filter is "a drawdown control, not an alpha source." Caveats listed: single period, universe chosen with hindsight, monthly rebalance coarse, no slippage/tax. Note the README both claims the universe was "fixed in advance to eliminate survivorship bias" and lists "universe selected with hindsight bias" as a caveat — the latter is the accurate reading (all 10 are survivors). — [IsaacDodds/crypto-momentum-backtest](https://github.com/IsaacDodds/crypto-momentum-backtest)
- [VENDOR/BLOG] Momentum strategies typically have 35-45% win rates, profitability depending on win size exceeding frequent small losses (snippet). — [TrendRider momentum strategies 2026](https://trendrider.net/blog/crypto-momentum-trading-strategies-2026)
- [BLOG] A Substack piece argues that backtesting systematic crypto momentum is heavily distorted by dead and "zombie" coins (title/snippet only). — [ParetoQuant: Dead Bombers & Zombie Coins](https://paretoquant.substack.com/p/dead-bombers-and-zombie-coins-the)

### Inferences
- Momentum rotation on a small large-cap universe should not be expected to beat simply holding BTC/ETH with a regime filter; any edge is lookback- and period-sensitive. Designs should test multiple lookbacks (e.g. 7/14/30/60/90d) and shorter rebalance intervals out-of-sample, and compare against "BTC with 200DMA filter" as the baseline, not against cash.
- Expect drawdowns of 40-55% even with a regime filter on a monthly-rebalanced long-only alt basket — incompatible with "fast growth over 30-day cycles" unless position sizing is reduced.

### Gaps
- No independent live track record of a retail weekly rotation bot with published monthly returns was found.

## 4. Pump/breakout scanners and new-listing snipers

### Takeaway
Academic measurements of on-chain sniper bots show most sniping operations fail to exit profitably and rug pulls are pervasive; retail practitioner write-ups report sniping as a "losing game" against faster, better-capitalised competitors. Centralised-exchange listing pumps are less exposed to rugs but still suffer latency and slippage.

### Cited Findings
- [SYSTEMATIC, peer-reviewed] 85.5% of BSC and 48.8% of Ethereum sniping operations were unsuccessful (bot never sold the token); ~60% of BSC and Ethereum liquidity pools had a rug pull in their first day. — [Cernera et al., USENIX Security 2023 "Token Spammers, Rug Pulls, and Sniper Bots"](https://www.usenix.org/system/files/sec23fall-prepub-460-cernera.pdf); [arXiv version](https://arxiv.org/pdf/2206.08202)
- [SYSTEMATIC] Sniper bot analysis paper on DeFi ecosystem impact. — [Ready, Aim, Snipe! (ACM WWW'23 companion)](https://dl.acm.org/doi/fullHtml/10.1145/3543873.3587612)
- [ANECDOTAL] Developer who built a BNB Chain liquidity sniper concluded it "proved a losing game"; snippet indicates only ~10 of 200+ bots competing on a launch realise a profitable exit (figure is from the snippet and not verified in full text). — [DEV Community: I Built a Liquidity Sniper Bot for BNB Chain](https://dev.to/jeyem/i-built-a-liquidity-sniper-bot-for-bnb-chain-and-it-proved-a-losing-game-39)

### Inferences
- For a spot bot on Coinbase/Kraken/Crypto.com, sniping new listings via REST polling is at a latency disadvantage to co-located/websocket competitors; first-minute spreads are wide, so fills will be far from the backtested "listing price". Volume-spike scanners on small caps face the same fill problem. Treat these as out of scope or as small, capped satellite allocations.

### Gaps
- No systematic data found on CEX (Coinbase/Kraken) new-listing pump returns net of slippage for retail bots.

## 5. Crypto-specific backtest pitfalls and live-vs-backtest degradation

### Takeaway
Survivorship bias is far worse in crypto than equities (majority of listed tokens have died), and backtest Sharpe has almost no predictive power for live results; practitioners routinely apply ~50% or larger haircuts.

### Cited Findings
- [BLOG, figures unverified] Of ~24,000 tokens listed on CoinMarketCap since 2013, over 14,000 are classified "dead" (>58%); survivorship bias "can inflate backtested returns by 200-400%" (snippet; the 200-400% figure lacks a stated methodology — treat as illustrative). — [StratBase: Survivorship Bias - Dead Coins](https://stratbase.ai/en/blog/survivorship-bias-crypto)
- [SYSTEMATIC] Academic paper on survivorship and delisting bias in crypto markets: including delisted coins materially shrinks factor premia (e.g., size premium reported falling to 1.89% in snippet). — [Survivorship and Delisting Bias in Cryptocurrency Markets (Univ. St. Gallen)](https://www.alexandria.unisg.ch/bitstreams/2bc8397d-47dd-4f66-8467-9004b2c9d212/download)
- [PRACTITIONER GUIDE] How to build a survivorship-free point-in-time universe from CoinMarketCap historical listings. — [Concretum Group](https://concretumgroup.com/building-a-survivorship-bias-free-crypto-dataset-with-coinmarketcap-api/); [Gimmer blog, Sept 2026](https://blog.gimmer.com/2026/09/01/crypto-backtest-survivorship-bias-point-in-time-universe/); [CoinAPI](https://www.coinapi.io/blog/how-to-eliminate-survivorship-bias-in-crypto-backtesting)
- [SYSTEMATIC] Quantopian cohort study (Wiecki et al.): commonly reported backtest metrics such as Sharpe offer little value in predicting out-of-sample performance (R² < 0.025). — [All That Glitters Is Not Gold](https://www.researchgate.net/publication/307553701_All_That_Glitters_Is_Not_Gold_Comparing_Backtest_and_Out-of-Sample_Performance_on_a_Large_Cohort_of_Trading_Algorithms)
- [PRACTITIONER] Rule of thumb of haircutting in-sample performance by ~50%; experienced researchers expect a backtest Sharpe of 4 to become 0-1 live; causes: cleaner-than-reality fills, peeking at unavailable information, selection of best-of-many attempts, and understated costs (snippet). — [techinterview: Why a backtest Sharpe of 4 becomes 0.5 live](https://www.techinterview.org/post/3233477314/why-backtest-sharpe-collapses-live/)
- [ANECDOTAL] Freqtrade users trace discrepancies to fill assumptions, look-ahead (e.g. `shift(-1)`, indicators referencing future candles), indicator bugs, and resampled/informative timeframe handling. — [freqtrade #8518](https://github.com/freqtrade/freqtrade/issues/8518); [freqtrade #7248](https://github.com/freqtrade/freqtrade/issues/7248); [freqtrade #7502](https://github.com/freqtrade/freqtrade/issues/7502)
- [PRACTITIONER GUIDE] Freqtrade-community "Backtesting Traps" write-up (not retrievable; exists as reference). — [Freqtrade Stuff: Backtesting Traps](https://brookmiles.github.io/freqtrade-stuff/2021/04/12/backtesting-traps/)

### Inferences
- Minimum hygiene for our design: point-in-time universe including delisted pairs; fills at next-bar open plus modelled spread and taker fee per exchange; liquidity filter (min 24h volume / max % of volume); walk-forward optimisation with untouched final out-of-sample window; parameter-stability check (neighbouring params should also work); use Freqtrade's lookahead/recursive-analysis style tooling or equivalent; then dry-run and compare signal-by-signal.
- Plan targets should assume live returns ≈ half of out-of-sample backtest (or less) and drawdowns ≥ 1.5-2× backtest.

### Gaps
- No systematic crypto-specific figure for average live degradation was found; the 50% haircut is a general quant rule of thumb.

## 6. Operational failure modes and safeguards

### Takeaway
Practitioners report that many "the bot lost money" incidents are infrastructure failures (dropped websockets, lost order state, duplicate orders, outages) rather than strategy failures; reconciliation against the exchange and kill switches are the core defences.

### Cited Findings
- [ANECDOTAL, bug report] Hummingbot connector: during a DNS outage, six sell orders were accepted by the exchange but dropped from the bot's tracking; after stopping, the account held an untracked 0.0006 BTC short exactly equal to the lost orders. — [hummingbot issue #8457](https://github.com/hummingbot/hummingbot/issues/8457)
- [INCIDENT] Hyperliquid API outage (~37 minutes) left traders unable to execute; the venue reimbursed ~$1.99M USDC (snippet via Cointelegraph/TradingView). — [TradingView/Cointelegraph](https://ru.tradingview.com/news/cointelegraph:b18f59353094b:0-hyperliquid-reimburses-2m-to-crypto-traders-after-api-outage)
- [PRACTITIONER BLOG] Most bot-loss incidents trace back to dropped WebSockets, throttled cancels, or double-placed orders; live bots need alerts for API errors, stale prices, rejected/duplicate orders, outages and failed stops, plus a manual kill switch (snippet). — [DEV Community: Exchange API integration without losing orders](https://dev.to/weston_carnes_d580b505e0c/exchange-api-integration-connecting-a-trading-system-without-losing-orders-13g9); [Coin Bureau: Bot mistakes to avoid](https://coinbureau.com/guides/crypto-trading-bot-mistakes-to-avoid); [Bitsgap: Why did my bot stop trading](https://bitsgap.com/blog/why-did-my-crypto-trading-bot-stop-trading)

### Inferences
- Required safeguards for our bot: (1) exchange-side reconciliation loop (open orders + balances) every cycle, treating the exchange as source of truth; (2) idempotent client order IDs to prevent duplicates on retry; (3) hard caps — max order notional, max open positions, max orders per minute, max daily loss → auto-halt; (4) stale-data check (refuse to trade if last candle/ticker older than N seconds); (5) heartbeat to an external monitor with alert on miss; (6) rate-limit-aware client with backoff; (7) exchange maintenance calendar awareness; (8) API keys trade-only, withdrawals disabled, IP-whitelisted.

### Gaps
- Could not retrieve Freqtrade "Protections" docs (StoplossGuard, MaxDrawdown, CooldownPeriod) due to proxy block; these are known built-in features but specifics were not verified here.

## 7. Paper-trading → live transition

### Takeaway
Community guidance ranges from 1-2 weeks to 2+ months of dry-run, with the common rule that live should begin at small stake only after dry-run tracks backtest closely; none of these thresholds is evidence-based.

### Cited Findings
- [ANECDOTAL/COMMUNITY] Suggested minimum of 2 months dry-run; others say 1-2 weeks is enough if dry-run is within 10-15% of backtest; small-capital lesson suggests at least 4 weeks live covering up/down/sideways regimes, with gating criteria like total return > 0 and max DD < 15% before scaling (snippets). — [DEV: Freqtrade pre-live checklist](https://dev.to/henry_lin_3ac6363747f45b4/lesson-22-freqtrade-pre-live-trading-checklist-1i8e); [DEV: Freqtrade small capital live trading](https://dev.to/henry_lin_3ac6363747f45b4/lesson-23-freqtrade-small-capital-live-trading-3ioc); [freqtrade issue #7300](https://github.com/freqtrade/freqtrade/issues/7300)
- [DOCS] Freqtrade recommends dry-running after backtest and verifying signals align candle-by-candle (snippet). — [Freqtrade Strategy Quickstart](https://www.freqtrade.io/en/stable/strategy-101/)

### Inferences
- Sensible plan for $500: paper-trade ≥ 30 days (one full cycle) with signal-level reconciliation to backtest; go live with the full $500 only if minimum order sizes permit (e.g. Coinbase/Kraken minimums ~$1-10) and fees are modelled; scale capital only after ≥ 2 live cycles where realised slippage/fees match model and drawdown stays within plan. Trade count matters more than calendar time: 30 days of a weekly-rotation bot is only ~4 decisions — too few to validate statistically.

### Gaps
- No systematic evidence on optimal paper-trading duration.

## 8. Notable blowups and cautionary examples

### Takeaway
The dominant catastrophic risk for retail bot users historically was third-party API key compromise (3Commas 2022), not strategy loss; keeping keys self-hosted, trade-only, withdrawal-disabled and IP-whitelisted is the key mitigation.

### Cited Findings
- [INCIDENT] 3Commas: in December 2022 an attacker posted ~100,000 API keys; CEO Yuriy Sorokin confirmed they came from 3Commas; estimated ~$20M stolen via compromised keys. — [SiliconANGLE, 2022-12-29](https://siliconangle.com/2022/12/29/crypto-trading-service-3commas-confirms-massive-api-key-leak-hack/); [Halborn explainer](https://www.halborn.com/blog/post/explained-the-3commas-breach-december-2022); [3Commas notice](https://3commas.io/blog/notice-on-api-data-disclosure-incident)
- [INCIDENT, conflicting accounts] Earlier (Oct-Nov 2022) FTX users with 3Commas-linked keys were exploited; FTX reportedly reimbursed ~$6M. 3Commas initially attributed this to phishing sites impersonating 3Commas and denied a leak, before the December disclosure confirmed keys came from its systems. — [Decrypt](https://decrypt.co/117826/3commas-api-dispute-highlights-risks-of-algorithmic-trading); [CoinCodeCap](https://coincodecap.com/ftx-users-get-drained-millions-in-3commas-api-exploit); [3Commas legal statement](https://3commas.io/blog/3commas-legal-statement-in-regard-of-violated-api-keys); [cr1337 substack analysis](https://cr1337.substack.com/p/3commas-incident-phishing-attack)

### Inferences
- The 3Commas exploit mechanism commonly reported was using stolen trade-enabled keys to buy illiquid tokens at inflated prices (draining value without withdrawal permission), so withdrawal-disabled keys alone are not sufficient; IP whitelisting and not sharing keys with third-party SaaS are important. (Mechanism from recall of press coverage; full articles could not be fetched to verify.)

### Gaps
- Could not verify full-text details of the 3Commas mechanism or the exact FTX reimbursement date due to blocked fetches.
