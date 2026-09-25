# Trade slow trends, not fast pumps

The plan with the best evidence behind it for a $500 automated crypto account is a **low-turnover, long-only trend system**. Each week it holds the liquid large-cap coins whose own 1-to-4-week returns are positive. It switches off when Bitcoin is in a downtrend, cuts exposure when futures funding rates run hot, and runs on a low-fee exchange API rather than the Crypto.com App. It sizes positions so that no single month can plausibly cost half the account. Several of your ideas have the most evidence *against* them: buying the day's top gainers, buying volume spikes, and sniping new listings. The existing bot's "breakout hunter" rests on those ideas, so it should be demoted to a test-only side strategy. Be ready for the pace to disappoint. The best-documented trading operation in history, Renaissance's Medallion fund, averaged about 66% a year before fees ([Visual Capitalist](https://www.visualcapitalist.com/growth-of-100-invested-in-jim-simons-medallion-fund/)). A skilled crypto system can realistically hope for something like 1.5-4% a month on average, with losing months. At those rates **$20,000 a month in profit requires roughly $400,000 to $1,000,000 of working capital**, and that capital will come mainly from proven results plus your own added savings, not from compounding $500. The roadmap below is built to find out cheaply whether you have a real edge. It runs as a backtest tournament, then 8 weeks of paper trading, then two live $500 cycles, then scaling in 2x steps with each step gated by numbers. Every step down that road is fast. Only the blow-up risk is slowed.

## Doubling monthly is a lottery ticket, not a plan

"Grow as fast as possible" has an arithmetic trap, and the owner should understand it before choosing position sizes. Doubling every month compounds to 4,096x a year: $500 would become about $2 million. Even 2% a day compounds to about 1,377x a year ([Ziemba, Kelly criterion chapter](https://webhomes.maths.ed.ac.uk/mckinnon/blackouts/StochOptFinanceAndEnergySpringer/Chap1_KellyZiemba.pdf) for the growth framework; the multiples are straightforward compounding). Professionals come nowhere near these numbers. Medallion made **about 39% a year after fees** from 1988 to 2018 ([Cornell Capital Group](https://www.cornell-capital.com/blog/2020/02/medallion-fund-the-ultimate-counterexample.html)). In 2024, crypto quant-directional funds returned about **53.7%** while Bitcoin roughly doubled ([Hedgeweek](https://www.hedgeweek.com/bitcoin-surges-ahead-of-crypto-in-2024/)). A 2025 industry review reportedly put the **median quant crypto fund at +3.2%**, with only 15 of 26 finishing positive, although the aggregator's numbers conflict internally ([Crypto Fund Research](https://cryptofundresearch.com/crypto-hedge-fund-performance/)).

Retail traders do far worse. Among Brazilians who day-traded futures for more than 300 days, **97% lost money** ([Chague, De-Losso & Giovannetti, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101)). **Fewer than 1%** of Taiwanese day traders were reliably profitable after fees ([Barber, Lee, Liu & Odean](https://escholarship.org/uc/item/7k75v0qx)). The BIS estimates that **73-81% of retail crypto-app users lost money on bitcoin**, mostly because they bought into rallies ([Bloomberg Law on BIS](https://news.bloomberglaw.com/crypto/about-75-of-retail-buyers-of-bitcoin-lost-money-bis-study-says)). A bot removes some of the emotional mistakes, such as revenge trading and holding losers. It does not remove fees, overfitting, or crashes that jump straight through stop-loss orders.

The research team's Monte Carlo simulations show why aggressive sizing backfires. A "good" system (45% win rate, winners twice the size of losers, realistic costs) that risks **2% per trade** over 60 trades in 30 days has a median result of **+24%** and essentially zero chance of a 50% drawdown. At **25% risk per trade**, the *average* outcome looks spectacular, but the *typical* (median) account falls to **0.40x**, and 65% of paths touch 20% of the starting balance at some point. For a merely "marginal" system, raising risk from 2% to 5% *lowers* the median 30-day outcome. The theory agrees. Betting twice the Kelly-optimal amount drives expected growth to zero, and betting more makes it negative ([MacLean, Thorp & Ziemba](https://www.researchgate.net/publication/227623956_Long-term_capital_growth_the_good_and_bad_properties_of_the_Kelly_and_fractional_Kelly_capital_growth_criteria)). (Kelly is the formula for the bet size that maximizes long-run growth. Betting more than Kelly makes you grow *slower*, not faster.) A "10 all-in doublings" challenge succeeds 0.1% of the time at coin-flip odds and under 3% even at a 70% success rate per step. The "$500 to $50k" stories online are the survivors of a much larger pile of wiped-out accounts.

Here is what that means for the $20,000/month goal. At 3% a month you need about **$667,000** of capital, and at 5% a month about **$400,000**. Compounding $500 alone at a steady 5% a month would take about **11 years** to get there, and 5% a month sustained would already beat almost every fund on record. The realistic route has three parts: prove an edge at small size, scale capital in steps as live evidence builds, and add outside savings to the base. The table shows what constant rates imply, so you can check any claim you see:

| Monthly return | $500 after 12 months | Capital needed for $20k/month |
|---|---|---|
| 2% | ~$634 | $1,000,000 |
| 5% | ~$898 | $400,000 |
| 10% | $1,569 | $200,000 |
| 20% | $4,458 | $100,000 |
| 100% (doubling) | $2,048,000 | $20,000 |

## Weekly trend-following is the one edge that survives fees

The strongest short-horizon effect in the crypto literature is **time-series momentum** (TSMOM). The idea is that a coin that has risen over the past few weeks tends to keep rising in the following week. Liu and Tsyvinski found "a strong time-series momentum effect" in crypto ([Review of Financial Studies](https://academic.oup.com/rfs/article-abstract/34/6/2689/5912024)). Liu, Tsyvinski and Wu documented momentum using 1-, 2-, 3- and 4-week lookbacks with **weekly rebalancing** ([Journal of Finance 2022](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13119)). Other work reports that TSMOM still earns "considerable" returns after 0.1% transaction costs ([Springer summary](https://www.springerprofessional.de/en/time-series-momentum-trading-strategy-for-cryptocurrencies/26140838)).

There are three caveats. First, a realistic-costs study found TSMOM "strong" but **cross-sectional momentum** (buying whichever coins rose most relative to the others) "almost non-existent", and many statistically significant portfolios became insignificant once fees and intra-week drawdowns were included ([Han, Kang & Ryu, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565)). Second, momentum strategies reportedly **lost money in 2022-2023** and made only modest gains in 2024-2025 ([comparative study, ResearchGate](https://www.researchgate.net/publication/401623816_Momentum_Mean_Reversion_and_Market_Timing_A_Comparative_Study_of_Active_Allocation_Strategies_versus_1N_Diversification_in_Digital_Assets)). Third, the famous pre-2019 effect sizes came from a younger, thinner market and will not repeat. The edge is real but regime-dependent. It pays in bull trends and bleeds in chop.

That regime dependence is why a **Bitcoin regime filter** belongs in the design, as a seatbelt rather than an engine. In the one reproducible public backtest the team found (10 large caps, 2021 to May 2026, 10 bps costs), naive top-3 momentum rotation returned **-7.7% a year with a -89.8% maximum drawdown**. Adding a "BTC above its 200-day average" rule turned that into **+10.8% a year with a -53.8% drawdown**, yet it still lagged simply holding all 10 coins equally (+35.6%) ([IsaacDodds backtest](https://github.com/IsaacDodds/crypto-momentum-backtest)). The author's conclusion was that the filter is "a drawdown control, not an alpha source." The practical lesson is to always judge the bot against a dumb baseline. The right baseline is "hold BTC only when it is above its 200-day average", not cash.

Futures data adds a useful **de-risking signal**. When perpetual-futures funding rates are high, meaning leveraged longs are paying a lot to stay in their positions, crashes become more likely. BIS researchers found that a 10% rise in standardized crypto carry predicts liquidations of **22% of open interest** over the following month ([BIS WP 1087](https://www.bis.org/publications/working-paper-1087-crypto-carry)). As a timing signal, funding is nearly useless: its 8-hour predictive R² for BTC was about 0.003 ([Fulgur Ventures](https://medium.com/@fulgur.ventures/bitcoin-funding-rates-and-price-predictability-27ce95535af1)). Use it to stop opening new longs. Never use it as a reason to buy.

Timing effects are too small to trade on their own. The best-documented one is the "turn of the candle" pattern, worth about 0.58 basis points per minute ([Heliyon 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10015199/)). That is a fraction of a single 0.1% fee. They are still worth one scheduling decision: rebalance away from the historically weakest 03:00-04:00 UTC window ([Quantpedia](https://quantpedia.com/are-there-seasonal-intraday-or-overnight-anomalies-in-bitcoin/)).

Fees decide everything at this account size. If the whole portfolio turns over every week, that is 52 round trips a year. At 0.2% per round trip the drag is about **10% a year**. At the 1-2% round-trip cost of App-style spreads it is **52-104% a year**, which is more than any documented edge. Hourly strategies with tight stops make this worse. The research team's cost model shows that cost expressed in units of risk is round-trip cost divided by stop distance. The current config assumes 1.2% round-trip cost (0.5% fee plus 0.1% slippage per side). With a 2% hourly-ATR stop, that means **each trade starts 0.6R in the hole**, where R is the amount you lose if the stop is hit. That is more than the entire net edge of a "good" system (+0.2R) in the team's simulations.

## Chasing gainers, volume spikes and listings loses money on average

Three of your ideas run straight into the most consistent negative findings in this research.

**Buying the top 24h gainers** collides with three documented effects at once. The first is daily reversal: coins with low returns the previous day significantly outperform the previous day's winners ([IRFA 2021](https://www.sciencedirect.com/science/article/pii/S1057521921002349)). The second is lottery-style overpricing of stocks with extreme recent jumps ([Bali, Cakici & Whitelaw](https://pages.stern.nyu.edu/~rwhitela/papers/max%20jfe11.pdf)). The third is pump reversal. Coordinated pumps reverse "after some minutes" ([Kamps & Kleinberg, Crime Science](https://link.springer.com/article/10.1186/s40163-018-0093-5)), and only people positioned *before* the pump profit ([Xu & Livshits, USENIX Security 2019](https://www.usenix.org/system/files/sec19-xu-jiahua_0.pdf)). Even pump-group insiders often lose ([Hamrick et al., SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3303365)).

**Buying volume spikes** has the evidence backwards. In crypto, unlike stocks, abnormally high trading volume signals disagreement among traders and **predicts lower future returns** ([Garfinkel, Hsiao & Hu, Financial Management 2025](https://onlinelibrary.wiley.com/doi/10.1111/fima.12491)).

**Listing sniping** fails for reasons of both speed and direction. About 25% of Coinbase listings showed insider buying, with abnormal returns 15-19% higher in the days *before* the announcement ([CoinGeek](https://coingeek.com/coinbase-study-reveals-insider-trading-on-25-of-new-token-listings/)). The reaction window has shrunk to minutes ([FinanceFeeds](https://financefeeds.com/binance-opens-the-gates-for-hyperliquids-hype/)). A news analysis found that only **11.1% of 2025 Binance listings** had positive returns ([BeInCrypto](https://beincrypto.com/binance-listed-tokens-negative-return/)). On-chain, **85.5% of BSC sniping operations never sold at all** ([Cernera et al., USENIX Security 2023](https://www.usenix.org/system/files/sec23fall-prepub-460-cernera.pdf)). A bot that checks prices once an hour is exit liquidity, meaning it is the buyer that faster traders sell to.

Two other popular bot types fail on their own terms. **Grid bots** lag buy-and-hold in strong uptrends, and the vendors themselves say so ([Pionex](https://www.pionex.com/blog/grid-bot/)). **DCA "safety order" bots** double down in falling markets and leave "red bags", meaning positions stuck deep in the red ([3Commas DCA FAQ](https://help.3commas.io/en/articles/11865862-dca-bot-faq)). Retail market making is also out: fees at small-account tiers are larger than the spreads on liquid pairs, and even Hummingbot warns it is "not a risk-free, always profitable trading operation" ([Hummingbot](https://hummingbot.org/blog/what-is-market-making/)). **Narrative chasing** was a losing trade in 2025. Memecoins returned -31.6% and AI tokens -50.2% despite dominating investor attention ([CCN on CoinGecko data](https://www.ccn.com/news/crypto/crypto-sector-coingecko-rwa-win-ai-memecoin-lose/)).

One usable idea comes out of all this: an **exclusion filter**. Never buy a coin that is up more than about 30% in 24 hours on more than 5x its normal volume. Those thresholds are the research team's illustration, not published values, so backtest them.

## Rebuild the codebase around a weekly momentum sleeve

The existing engine is a sound skeleton: cost modelling, ATR stops, a drawdown breaker and an hourly runner. Its strategy mix, though, points at the weakest evidence. The fixes, in order of importance:

**1. Add a `WeeklyMomentum` strategy as the core strategy (planned at 70-100% of capital).** It reads daily candles. Its universe is the current `UNIVERSE` of 16 liquid large caps, filtered to coins your chosen exchange actually lists. Its signal is each coin's own trailing return over the lookback. Hold a coin only if that return is positive, then take the top N by return. Weight each holding by inverse volatility, so calmer coins get more money. Rebalance once a week at a fixed time outside 03:00-04:00 UTC. Skip any rebalance trade that is smaller than a minimum size, which saves fees.

**2. Replace `market_ok()` with a slow regime filter.** The current rule, "BTC below its 24h EMA and down 3% in 24h", reacts to noise. Use "BTC daily close above its N-day SMA, with a buffer band" or "BTC 4-week return greater than zero". When the filter is off, the bot holds cash, or BTC only if that variant wins in the tests.

**3. Add a funding-rate brake.** Pull BTC perpetual funding history. The Crypto.com Exchange's `public/get-valuations` endpoint is *believed* to provide it with `valuation_type=funding_hist`, but this has not been verified. If 30-day average annualized funding sits in the top decile of its trailing-year range, stop opening new longs and halve target exposure.

**4. Demote `BreakoutHunter` to a paper-only side strategy (at most 20% of risk)** until it beats a control version of itself. Test "48h high breakout *without* the volume requirement" against the current "volume surge 3x" version, because the evidence predicts the volume condition hurts. Trim `BREAKOUT_UNIVERSE` to coins with deep order books. SHIB, PEPE, BONK, WIF and FLOKI are exactly the lottery-type names where reversal dominates. Keep the existing "max 8% up in 24h" guard and add the 30%/5x exclusion above.

**5. Retest `TrendFollower` on 4h and daily candles.** On 1h candles its 2.5-ATR stops are tight enough that costs eat a large share of each trade's risk budget.

**6. Model fees per exchange and run every backtest at three cost levels:** 0.1%, 0.4% and 1.0% per side, each plus slippage. A strategy that only works at 0.1% is a Binance.US-only strategy.

**7. Fix the data sources.** Weekly strategies need years of daily history. Crypto.com's older API capped candle requests at 300 per call, and the v1 limits are unverified ([Crypto.com old API docs](https://crypto.com/exchange-docs-v1)). Pull history through CCXT from the exchange you will actually trade on. Build a **point-in-time universe that includes delisted coins**, because more than half of all listed tokens have died ([Concretum Group guide](https://concretumgroup.com/building-a-survivorship-bias-free-crypto-dataset-with-coinmarketcap-api/)).

The backtest tournament should test only this grid and record how many variants you tried:

| Component | Values to test | Notes |
|---|---|---|
| Momentum lookback | 7, 14, 21, 28 days; blend of all four | Literature range is 1-4 weeks ([JF 2022](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13119)) |
| Holdings (top N) | 3, 5, "all with positive momentum" | Compare against equal-weight hold |
| Rebalance | Weekly (primary); every 3 days (check) | Daily turnover costs ~7x more |
| Weighting | Equal; inverse 30-day volatility | Cap any coin at 40% |
| BTC regime filter | Close > 50, 100, 200-day SMA; 4-week return > 0; ±2% buffer band | Report drawdown and time in market |
| Funding brake | Off; top-decile 30d funding = no new longs + 50% exposure | Derived from BIS carry-crash evidence |
| Pump exclusion | Off; >30% 24h and >5x volume | Illustrative thresholds |
| Costs per side | 0.1%, 0.4%, 1.0% + 0.05-0.1% slippage | Kraken maker ~0.25%, App 0.5-2% |
| Baselines | BTC buy-and-hold; BTC with 200-day filter; equal-weight universe | The bot must beat the filtered-BTC baseline |

Tournament rules matter as much as the parameters. A single backtest Sharpe ratio (return per unit of volatility) predicts live results poorly: backtest metrics explained **less than 2.5% of live performance** across a large cohort of Quantopian algorithms ([Wiecki et al.](https://www.researchgate.net/publication/307553701_All_That_Glitters_Is_Not_Gold_Comparing_Backtest_and_Out-of-Sample_Performance_on_a_Large_Cohort_of_Trading_Algorithms)). If you try 100 zero-skill variants on one year of data, the best one will show an annual Sharpe of about **2.5** by luck alone ([Bailey & López de Prado, Deflated Sharpe Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)).

Split the data by date. Tune on 2021-2023. Walk forward through 2024-2025 in rolling 6-month windows. Keep 2026 year-to-date **completely untouched** for a single final check. Require that neighbouring parameter values also work: if the 14-day lookback works but 7 and 21 do not, that is noise. Then assume live results will be **about half of out-of-sample returns, with drawdowns 1.5-2x worse**, which is the practitioners' usual haircut ([techinterview on backtest decay](https://www.techinterview.org/post/3233477314/why-backtest-sharpe-collapses-live/)).

## Trade through Kraken Pro or Binance.US, not the App

The **Crypto.com App has no public trading API**, so a bot cannot trade inside it. App trades also carry a variable spread estimated at **0.5% to 2%+**, and card purchases cost another 1.5-2.99% ([GOBankingRates](https://www.gobankingrates.com/investing/crypto/crypto-com-fees/)). The **Crypto.com Exchange** launched in the US in January 2025 for "institutional and advanced traders", funded by Fedwire, with REST, WebSocket and FIX APIs ([Crypto.com](https://crypto.com/us/company-news/crypto-com-exchange-set-for-u-s-launch)). Its entry-tier fees are **0.25% maker / 0.50% taker** ([Coin Bureau](https://coinbureau.com/review/crypto-com-review)). Whether a normal retail user in your state can open an account is unconfirmed, so check eligibility inside the Exchange app before building around it. The main choices:

| Venue | Fees at <$10k volume (maker/taker) | Fit |
|---|---|---|
| Binance.US | Near zero on many pairs since 2026 ([Business Wire](https://www.businesswire.com/news/home/20260422787826/en/Binance.US-Slashes-Spot-Trading-Fees-to-Near-Zero-for-All-Users)) | Cheapest; not available in NY, TX, GA; promotional fees can end |
| Kraken Pro | 0.25% / 0.40% ([Kraken](https://www.kraken.com/features/fee-schedule)) | Best all-round default; mature API; paper engine in `kraken-cli` ([GitHub](https://github.com/krakenfx/kraken-cli)) |
| Crypto.com Exchange (US) | 0.25% / 0.50% | Keeps you in the Crypto.com ecosystem; eligibility unclear |
| Coinbase Advanced | 0.40% / 0.60% ([Datawallet](https://www.datawallet.com/crypto/coinbase-fees)) | Widest altcoin list, best docs, most expensive |
| Alpaca | ~0.15% / 0.25% ([Alpaca docs](https://docs.alpaca.markets/us/docs/crypto-fees)) | Free full paper account; small coin list |

The recommendation is **Kraken Pro, or Binance.US if your state allows it**. Use post-only limit orders, which rest on the book and pay the lower maker fee. Keep the Crypto.com App as the place where swept profits land and long-term holdings sit. Fund by ACH or wire, never by card. Skip perpetual futures at first. Coinbase does offer CFTC-regulated perps to US retail with up to 10x leverage ([Coinbase](https://www.coinbase.com/blog/perpetual-futures-have-arrived-in-the-us)), but on 10-11 October 2025, **$19 billion of leveraged positions were liquidated in about 24 hours**, and some altcoins briefly fell 40-80% ([CoinDesk](https://www.coindesk.com/research/market-spotlight-the-19-billion-liquidation-that-shook-crypto)). Moves like that go straight through any stop.

**Getting real data is the immediate blocker.** This cloud environment's network policy is refusing `api.crypto.com`; that refusal comes from the sandbox's own proxy, not from Crypto.com. To fix it, open the cloud environment menu in the session title bar, choose Edit, and under Network access either add `api.crypto.com` (plus your chosen exchange's API domain, such as `api.kraken.com`) to the allowed domains or pick a broader access level. Alternatively, run the backtest on GitHub Actions with `workflow_dispatch`. As a first test, have one job `curl` the candlestick endpoint to confirm that GitHub's runner IPs are not blocked. No source documents geo-blocking either way.

The existing hourly workflow is adequate for paper trading. It uses about 720 billed minutes a month, well inside the private-repo allowance of 2,000 free minutes ([GitHub](https://github.com/resources/insights/2026-pricing-changes-for-github-actions)). It does have two weaknesses. Runs are often delayed 5-30 minutes ([Runhooks](https://runhooks.app/blog/github-actions-scheduled-workflows-unreliable/)), which is harmless for a weekly rebalance. And runner IPs rotate, so you cannot whitelist them on an API key. For live money, move to a **$4-6/month VPS with a static IP**. Avoid Oracle's free tier: it reclaims idle instances, and a mostly idle bot qualifies ([InfoQ](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)).

**Security** starts from the biggest historical bot disaster, which was not a bad strategy. An attacker posted **about 100,000 API keys leaked from 3Commas**, and roughly $20M was stolen ([SiliconANGLE](https://siliconangle.com/2022/12/29/crypto-trading-service-3commas-confirms-massive-api-key-leak-hack/)). Create keys with **trade and read permissions only and withdrawals disabled**, and **IP-whitelist them to the VPS** ([Crypto.com Help](https://help.crypto.com/en/articles/3511424-api)). Never paste them into third-party bot services. Keep only the bot's capital on the trading account. Store secrets in GitHub Secrets or a `.env` file readable only by its owner (permissions 600).

**Operational safety** matters because many "the bot lost money" incidents turn out to be infrastructure failures. In one case, orders the exchange accepted silently dropped out of the bot's tracking during a DNS outage ([Hummingbot #8457](https://github.com/hummingbot/hummingbot/issues/8457)). Build these in:

- A reconciliation step every cycle that treats the exchange's balances and open orders as the truth.
- Unique client order IDs so a retried order never duplicates.
- A refusal to trade on stale prices.
- A heartbeat that alerts you if a run is missed.

**Phone alerts and the SOS kill switch.** Use a **Telegram bot** for two-way control. It is free ([Optimum Web](https://www.optimum-web.com/blog/telegram-bot-api-pricing-2026-complete-guide/)) and lets you send `/status` and `/stop`. Use **ntfy.sh** with a long random topic name as a zero-setup push backup ([GitHub example](https://github.com/dasunpamod/crypto-mobile-notifications-bot)). The bot should alert on every fill, on any daily loss beyond limits, on API errors, and on a missed heartbeat.

The SOS command should work in three layers:

1. **`/stop`:** stop opening new trades.
2. **`/flatten`:** cancel all open orders and sell everything to USD at market.
3. **Last resort from the phone:** delete the API key in the exchange app. That kills the bot instantly wherever it is running.

Test all three during paper trading.

## Risk 1% per trade, sweep half, scale in doublings

**Position sizing.** Risk **1% of equity per trade** during the first live cycles, with a 2% hard ceiling. The team's estimation-error simulations explain why. If you size for a 45% win rate but the true rate is 40%, full-Kelly sizing produces a *median monthly loss of 49%*, while quarter-Kelly roughly breaks even. Backtests almost always overstate win rates. For the weekly momentum sleeve, size by volatility instead of by stop: target something like 1% of equity in expected daily move per coin, and cap any single coin at 40% of the portfolio. Never use leverage.

**Portfolio limits.** Cap **total open risk across all altcoin positions at 4-5% of equity**. Alts crash together, so five simultaneous breakouts are really one trade at five times the size. The loss limits:

- **Daily:** stop for the day at about 3R lost (roughly -3% to -5%).
- **Weekly:** stop for the week at -8% to -10%.
- **Breaker:** lower `MAX_DRAWDOWN_HALT` from 25% to **15-20% from peak**. When it trips, go back to paper trading rather than just waiting 7 days.

Stopping early is cheap because recovery math is brutal. A 20% loss needs a 25% gain to recover, and a 50% loss needs 100%. Losing streaks will happen. At a 45% win rate, a run of 10 or more straight losses appears in **88% of 1,800-trade years** in the team's simulations.

**Monthly profit sweep.** Tax is owed on **realized net gains**, not on withdrawals. At each 30-day cycle end:

1. Move a tax reserve equal to your combined marginal rate on that month's realized gains into a USD account. A typical middle-income filer in a 5% state needs about 29%.
2. Sweep **half of the remaining profit** to the Crypto.com App or your bank.
3. Leave the other half to compound.

Never top the account back up after a losing month unless a scaling gate has been passed. The sweep deliberately slows median compounding in exchange for locked-in gains. That trade-off fits "as fast as possible without blowing up".

**Scaling.** Double capital only after a gate is passed: $500 → $1,000 → $2,000 → $4,000, and so on. Each step needs two consecutive live cycles in which realized fees and slippage were within 1.25x of the model, drawdown stayed within the plan, and returns beat the filtered-BTC baseline. After any breaker trip, drop back one step.

Be honest about the statistics. Proving skill takes a long time. Showing a genuine annual Sharpe of 2 at 95% confidence takes about **250 days of daily returns**, and a Sharpe of 1 takes about **2.7 years** ([Bailey & López de Prado, MinTRL](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1821643)). A breakout system with a +0.2R edge needs about **220-500 trades** to reach t = 2-3 (a t-statistic that high means the average result is unlikely to be luck). So the early 2x steps are affordable *experiments*. Scaling beyond about $10,000 should wait for 6-12 months of live data that clears those bars.

## Every bot trade is a taxable event

Crypto is property for US tax purposes, so **every sale and every crypto-to-crypto swap, including swaps into USDC, is a taxable disposal** ([IRS virtual currency FAQ](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-virtual-currency-transactions)). A bot holding for days produces short-term gains taxed as ordinary income at 10-37% ([IRS Topic 409](https://www.irs.gov/taxtopics/tc409)). A 3.8% surtax on investment income applies above $200,000 (single) or $250,000 (married filing jointly), and most states tax the gains too. Eight states have no income tax: Alaska, Florida, Nevada, New Hampshire, South Dakota, Tennessee, Texas and Wyoming. Washington taxes only large long-term gains ([CoinTracker](https://www.cointracker.com/blog/states-with-no-income-tax)).

Losses help less than people expect. Net capital losses offset only **$3,000 a year of wages**, and the rest carries forward ([IRS Topic 409](https://www.irs.gov/taxtopics/tc409)). The mark-to-market election that full-time traders use to escape that limit is a gray area for spot crypto ([Green Trader Tax](https://greentradertax.com/cryptocurrencies-trader-tax-status-and-section-475-issues/)).

The **wash-sale rule does not currently apply to crypto**. (That rule stops you claiming a loss if you rebuy the same asset within 30 days.) However, H.R. 10357 cleared the House Ways and Means Committee **38-5 on 16 September 2026**. It would extend wash-sale rules to digital assets, most likely from the tax year after enactment ([Ways & Means](https://waysandmeans.house.gov/2026/09/16/historic-digital-asset-tax-legislation-advances-to-keep-america-the-crypto-capital-of-the-world/)). A separate bill, H.R. 9172, may apply retroactively as drafted ([Congress.gov](https://www.congress.gov/bill/119th-congress/house-bill/9172/text)). Have the bot log every loss sale and any rebuy of the same coin within 30 days either side, so the adjustment can be computed if the law changes.

**Paperwork.** Brokers send **Form 1099-DA**. For 2025 trades it shows proceeds only. For assets bought from 1 January 2026 in the same account, it also shows cost basis ([IRS 1099-DA instructions](https://www.irs.gov/pub/irs-pdf/i1099da.pdf)). Basis must be tracked **per account**, because pooling across wallets ended in 2025 ([Rev. Proc. 2024-28](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf)).

**Estimated taxes.** Pay quarterly: 15 April, 15 June, 15 September and 15 January. The safe harbor is to pay 90% of this year's tax or 100% of last year's (110% if last year's income was above $150,000) ([TaxGuidance](https://taxguidance.org/irs-estimated-tax-payment-dates-safe-harbor-and-penalties/)). If you have a salary, raising your W-4 withholding is the simplest way to stay covered.

**Records.** Log each fill with UTC timestamp, account, pair, side, quantity, price, USD value, fee and order ID. Sync the exchange to Koinly or CoinLedger. Tiers cost about $49-$299 a year depending on transaction count ([Koinly](https://koinly.io/blog/coinledger-vs-cointracker/)), and the weekly rebalance design keeps you in the cheap tiers.

## Four gates from backtest to real money

| Phase | Timing | What happens | Pass to next phase if… | Fail / stop if… |
|---|---|---|---|---|
| 0. Data access | Week 1 | Allowlist API domains or run on Actions; pull 4+ years of daily candles via CCXT, including delisted coins; open Kraken/Binance.US account | Clean data for all universe coins | — |
| 1. Backtest tournament | Weeks 2-4 | Run the parameter grid above with walk-forward testing; one final look at the 2026 holdout | Out-of-sample net return > 0 at 0.4%/side **and** beats the BTC-with-200-day-filter baseline; max drawdown < 35%; neighbouring parameters also positive; Sharpe holds up after correcting for the number of variants tried | Only works at 0.1% fees, or only one lookback works: redesign |
| 2. Paper trading | Weeks 5-12 (8 weeks minimum) | Hourly Actions runner; Telegram/ntfy alerts; test the kill switch | Signals match the backtest candle-for-candle; return within about 15% of the backtest over the same weeks; drawdown < 15%; zero unreconciled incidents; for the breakout side strategy, 30+ closed trades beating its no-volume control | Drawdown > 20% or systematic mismatch: back to Phase 1 |
| 3. Live $500 | Months 4-5 (two 30-day cycles) | VPS, trade-only IP-locked keys, 1% risk, sweep rules active | Realized costs ≤ 1.25x model; drawdown within plan; beats filtered-BTC baseline over both cycles | 15-20% drawdown, or 2 losing cycles in a row: back to paper |
| 4. Scaling | Month 6 onward | Double capital per gate; add savings deliberately | Same Phase 3 tests at each step; beyond ~$10k, 6-12 months of live data meeting the MinTRL bar | Any breaker trip: drop one step |

Practitioners report that forward testing is often sobering. One Freqtrade user saw win rates fall from 70% in backtest to 35% in dry-run ([freqtrade #8451](https://github.com/freqtrade/freqtrade/issues/8451)), and Freqtrade's own docs warn that backtests assume every order fills ([Freqtrade docs](https://www.freqtrade.io/en/stable/backtesting/)). If you would rather not maintain custom code, Freqtrade's dry-run mode with built-in Telegram control on Kraken is a proven substitute for Phases 2-3.

## Conclusion

The research turns the owner's instinct upside down. The fastest-feeling signals are 24-hour gainers, volume surges and new listings, and they are exactly where the evidence shows negative expected returns: the price move has already been paid to insiders and faster bots. The edge that survives is slow, boring and regime-dependent. It is trend exposure measured over weeks, switched off in bear markets and trimmed when leverage is crowded. It works only if fees are kept to a fraction of a percent. That makes exchange choice and trade frequency bigger decisions than any indicator setting. Moving off the App's spread is worth more than any parameter tuning.

The $500 stage has a clear purpose. It is not there to make money. It is a cheap measuring instrument that answers one question: does this system's live edge, after real costs, match its out-of-sample backtest? If it does, scaling capital is how income grows, since 3% a month on $400,000 or more is the realistic shape of $20,000 a month. If it does not, the plan has cost a few hundred dollars and a few months instead of the account. A realistic best case for year one is a tested system, a few doublings of capital through the gates, and a track record strong enough to justify adding real savings.
