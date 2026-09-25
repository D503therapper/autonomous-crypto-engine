# Evidence Review: Short-Term (Hours to ~2 Weeks) Crypto Trading Strategies, Net of Costs

Method note for the report writer: the web-fetch tool was blocked for almost every primary source (arxiv.org, ssrn.com, nber.org, bis.org, springer, quantpedia, concretumgroup, cryptorank). Everything below comes from search-result abstracts and snippets, not full-text reads. Figures are as stated in those snippets. Where a claim could not be checked against the paper's own tables, it is flagged. Before any parameter goes into the bot, the key numbers should be checked against the original PDFs.

## 1. Time-series momentum (TSMOM) / trend following: what lookbacks work?

### Takeaway
Time-series momentum is the best-documented short-horizon crypto effect. The strongest evidence is at 1 to 4 week lookbacks. Recent work that uses realistic assumptions finds TSMOM is "strong" but that many paper profits disappear after costs and intraperiod drawdowns. Performance was also negative in the choppy 2022-2023 period. Treat it as a regime-dependent edge, not a steady one.

### Cited Findings
- Liu & Tsyvinski (RFS 2021) find "a strong time-series momentum effect" in crypto, and proxies for investor attention strongly forecast returns. At the 1-week horizon, the top quintile averages 11.22%/week (Sharpe 0.45) and the bottom quintile 2.60%/week (Sharpe 0.19). The sample is pre-2019. The snippet does not make clear exactly what is sorted into quintiles, so check the paper. — [Liu & Tsyvinski, RFS](https://academic.oup.com/rfs/article-abstract/34/6/2689/5912024); [NBER WP](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
- Liu, Tsyvinski & Wu (JF 2022): three factors (crypto market, size, momentum) capture the cross-section of expected crypto returns. For 1-, 2-, 3- and 4-week momentum strategies, mean excess returns rise across quintiles. Portfolios rebalance weekly. The sample is roughly 2014-2018. — [JF 2022](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13119); [NBER WP](https://www.nber.org/system/files/working_papers/w25882/w25882.pdf)
- Han, Kang & Ryu (SSRN 4675565, Dec 2023), "Time-Series and Cross-Sectional Momentum in the Cryptocurrency Market: A Comprehensive Analysis under Realistic Assumptions": evidence for TSMOM is strong and cross-sectional momentum is "almost non-existent" or weak, concentrated among large winners. After transaction costs and daily price fluctuations (liquidation of portfolios), "many momentum portfolios are liquidated and many with statistically significant returns earn insignificant profits." Returns are skewed and fat-tailed enough that mean return alone is an inadequate test. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565); [ResearchGate](https://www.researchgate.net/publication/377457967_Time-Series_and_Cross-Sectional_Momentum_in_the_Cryptocurrency_Market_A_Comprehensive_Analysis_under_Realistic_Assumptions)
- A Springer study of TSMOM reports the strategy still earns "considerable" returns after a 0.1% transaction cost. Other studies assume 15 bps per trade. — [Springer Professional summary](https://www.springerprofessional.de/en/time-series-momentum-trading-strategy-for-cryptocurrencies/26140838)
- Decay in 2022-2023: search summaries of recent comparative studies say "all momentum strategies failed from 2022 to 2023" and TSMOM had negative annual returns in the downturn and choppy years 2022-2023. In 2024-2025, momentum variants converged to modest positive returns. I could not confirm which paper each line comes from; it appears to be the comparative study below. — [ResearchGate: Momentum, Mean Reversion, and Market Timing vs 1/N](https://www.researchgate.net/publication/401623816_Momentum_Mean_Reversion_and_Market_Timing_A_Comparative_Study_of_Active_Allocation_Strategies_versus_1N_Diversification_in_Digital_Assets); see also [Cryptocurrency momentum has (not) its moments, FMPM 2025](https://link.springer.com/article/10.1007/s11408-025-00474-9)
- An arXiv preprint (2602.11708, 2026) reports an adaptive trend-following framework with out-of-sample Sharpe 2.41 across 150+ pairs over a 36-month window (2022-2024). Costs modelled: 4 bps taker fee, slippage linear in trade size relative to 5-minute volume, and perp funding. This is a single, non-peer-reviewed preprint with complex adaptive construction, so overfitting risk is high. Its 4 bps fee is far below a $500 spot account's 10+ bps. — [arXiv 2602.11708](https://arxiv.org/html/2602.11708v1)
- Risk-managed (volatility-scaled) momentum is studied in Finance Research Letters (2025). — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1544612325011377)
- Intraday: Bitcoin's first half-hour return (sessions defined by volume) positively predicts the last half-hour return. Predictability is strongest in the highest-volume and highest-volatility sessions and is driven by liquidity provision. Sample: March 2013 to May 2020. — [Wen, Bouri et al., Intraday return predictability](https://www.sciencedirect.com/science/article/abs/pii/S1062940822000833); [Bitcoin intraday TSMOM (Reading)](https://centaur.reading.ac.uk/100181/)
- Caporale & Plastun (2017 to Sept 2019, BTC/ETH/LTC): on days with abnormal returns, hourly returns keep moving in the direction of the overreaction until day end, and the effect carries into the next day. Exceptions: BTC positive overreactions and ETH negative overreactions showed a contrarian effect. — [FMPM 2020](https://link.springer.com/article/10.1007/s11408-020-00357-1); [CESifo WP](https://ideas.repec.org/p/ces/ceswps/_7917.html)

### Inferences
- Parameters to backtest: lookbacks of 1, 2, 3 and 4 weeks (LTW); 1-week hold with weekly rebalance; volatility scaling. For intraday, trade in the direction of the first high-volume session into the session close. These are the literature's parameters. Weekly rebalancing keeps turnover low enough that 0.1%/side fees are tolerable. At 0.5-1%/side, a weekly-rebalanced strategy loses about 1-2% per round trip. That is on the order of the edge for most signals outside strong bull regimes.
- The effect is mostly a bull-market phenomenon (2022-2023 failures). A regime filter (Section 8) is complementary.
- The pre-2019 effect sizes (for example, 11%/week) came from a thin, small-cap, early market. Do not expect them now.

### Gaps
- I could not access full-text tables for net-of-cost Sharpe ratios by lookback in Han, Kang & Ryu, or for post-2022 subsamples.
- I found no clean peer-reviewed estimate of TSMOM Sharpe on BTC/ETH spot for 2023-2026 specifically.

## 2. Cross-sectional momentum vs. short-term reversal among altcoins

### Takeaway
Horizon matters. At 1-day horizons, reversal dominates, mostly in small and illiquid coins, and is largely a liquidity-provision premium that fees and spreads eat. At 1-4 weeks, cross-sectional momentum exists, stronger in small coins, but realistic-cost studies find it weak. Beyond about 1 month, reversal returns.

### Cited Findings
- Coins with low previous-day returns significantly outperform coins with high previous-day returns. The daily reversal comes from the illiquidity of most traded cryptocurrencies. Size and momentum also matter: anomalous returns fall with size, momentum is more significant in small coins, and distance from the 1-week high negatively predicts returns of small, illiquid coins. — [Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets (IRFA 2021)](https://www.sciencedirect.com/science/article/pii/S1057521921002349)
- Dobrynskaya (2,000 largest coins, 2014-2020): positive momentum at horizons up to 2-4 weeks, then significant reversal beyond 1 month. This predates 2022. — [SSRN 3913263](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3913263); [J. Alternative Investments](https://www.pm-research.com/content/iijaltinv/26/1/65)
- Han, Kang & Ryu: cross-sectional momentum is weak or "almost non-existent" under realistic assumptions and concentrated among large winners. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565)
- "Cryptocurrency anomalies and economic constraints" (IRFA 2024) examines whether anomalies survive economic constraints. I could only see the title; per its framing, many do not. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1057521924001509)
- A 2026 arXiv preprint measures short-horizon mean reversion across crypto markets (2608.21888). The content was not accessible. — [arXiv 2608.21888](https://arxiv.org/pdf/2608.21888)
- A JFQA trend factor that combines short-, medium- and long-horizon moving-average signals prices the crypto cross-section. — [Cambridge/JFQA](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/trend-factor-for-the-cross-section-of-cryptocurrency-returns/4C1509ACBA33D5DCAF0AC24379148178)

### Inferences
- For a $500 spot, long-only bot: the daily-reversal premium sits in illiquid small caps with wide spreads, so it is probably not capturable after 0.1% fees plus spread. It is certainly not capturable at 0.5-1%/side. Long-only cross-sectional momentum (buy the top weekly performers among liquid coins, hold 1 week) is testable, but the evidence that it survives costs is weak.
- Parameters to test: universe of top 50-100 by market cap or volume; rank on 1-week (and 2-4 week) returns; long the top quintile or top N; weekly rebalance; exclude coins more than X% from their 1-week high (weak small-cap evidence).

### Gaps
- There are no reliable post-2022 net-of-cost numbers for cross-sectional momentum vs. reversal split by size.

## 3. Breakout and volume-surge signals ("volume precedes price")

### Takeaway
The best cross-sectional evidence goes against the folk idea that high abnormal volume predicts higher returns in crypto. High abnormal volume predicts lower future returns (a disagreement / short-sale-constraint story). Volume is informative mainly as a conditioning variable.

### Cited Findings
- Garfinkel, Hsiao & Hu (Financial Management 2025): abnormal volume, read as disagreement, predicts lower future returns in crypto. This is a negative volume-return relation, the opposite of the high-volume premium in stocks. They use abnormal rather than raw volume to separate the effect from liquidity. — [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/fima.12491); [SSRN PDF](https://papers.ssrn.com/sol3/Delivery.cfm/4345640.pdf?abstractid=4345640)
- Volume can predict Bitcoin returns except during bull and bear periods, according to search-result summaries of the cross-predictability literature. — [Cross-cryptocurrency return predictability (JEDC 2024)](https://www.sciencedirect.com/science/article/abs/pii/S0165188924000551)
- Order-flow imbalance is studied as a crypto return predictor (EFMA 2025 paper). The content was not accessible. — [Order Flow and Cryptocurrency Returns](https://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2025-Greece/papers/OrderFlowpaper.pdf)
- Intraday momentum is strongest in high-volume sessions (see Section 1). — [Bitcoin intraday TSMOM](https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/)

### Inferences
- A naive "buy when volume spikes X× average" rule is not supported by the peer-reviewed evidence and may have negative expected return at multi-day horizons. If tested, use volume as a filter on trend signals, for example requiring a breakout above an N-day high, and compare against the same breakouts without volume confirmation.

### Gaps
- I found no rigorous crypto-specific study of N-day-high breakouts (Donchian channels) net of costs with post-2022 data.

## 4. Exchange listing announcement effects (Coinbase, Binance, Upbit)

### Takeaway
Listing announcements produce large, fast pops. Much of the move is front-run by insiders before the announcement, and the reaction window is now minutes. Buying on or after listing day has been strongly negative on average in 2024-2025. A retail bot with ordinary polling latency should expect to be exit liquidity.

### Cited Findings
- Messari (2021): Coinbase listings had the highest average 5-day return among exchanges, 91%, with a range of -32% to +645%. The sample is from the 2020-2021 bull market. — [Nasdaq/Messari](https://www.nasdaq.com/articles/coinbase-effect-means-average-91-token-price-gain-in-5-days-messari-says-2021-04-07)
- Coin Metrics (2020) contradicts this: average and median performance from 10 days before to 10 days after the announcement was only -1% to +14%. — [Cointelegraph on Coin Metrics](https://cointelegraph.com/news/coinmetrics-finds-the-coinbase-effect-is-actually-pretty-lame)
- A 2025 study found insider trading on about 25% of Coinbase listings: those tokens had cumulative abnormal returns 15% higher in the 3 days, and 19% higher in the 7 days, before the announcement. — [CoinGeek](https://coingeek.com/coinbase-study-reveals-insider-trading-on-25-of-new-token-listings/)
- Buying new listings on day one on Upbit, Bithumb or Binance lost about 70% on average (Upbit -69.5%, Bithumb -69.1%). The source is a secondary crypto-news analysis; I could not verify its methodology. — [CryptoRank via search](https://cryptorank.io/news/feed/94ca0-cryptocurrency-investment-losses-upbit-bithumb)
- Only 11.1% of tokens listed on Binance in 2025 had a positive return (news analysis). — [BeInCrypto](https://beincrypto.com/binance-listed-tokens-negative-return/)
- Speed: HYPE rose about 1.5-1.9% within 10 minutes of Binance's listing notice (Sept 2026). The announcement-to-move window has shrunk from hours to minutes. — [FinanceFeeds](https://financefeeds.com/binance-opens-the-gates-for-hyperliquids-hype/); [PageCrawl](https://pagecrawl.io/blog/crypto-new-coin-listing-alerts-binance)
- An academic event study found abnormal returns up to 3 days before events. Coins mostly traded on Upbit reacted sharply negatively to some announcements. — [Announcement effects in the cryptocurrency market](https://www.researchgate.net/publication/341117503_Announcement_effects_in_the_cryptocurrency_market); [Blockchain Research Lab WP](https://www.blockchainresearchlab.org/wp-content/uploads/2019/10/Exploring-Market-Reactions-to-Exchange-Listings-of-Cryptocurrencies-BRL-working-paper3.pdf)

### Inferences
- The only plausibly capturable version is sub-minute: detect the announcement and buy the token on a different venue where it already trades. That needs low-latency infrastructure, and professional bots compete for the same trade. With a $500 account, latency and slippage probably consume the edge. The sign of the post-listing drift (negative) favours avoiding tokens after listings rather than chasing them.

### Gaps
- No peer-reviewed minute-level study of 2023-2026 listing reactions was found in accessible form. The 70% loss figure is from a secondary source.

## 5. Derivatives signals: funding rates, open interest, long/short ratios, liquidations

### Takeaway
High funding or carry is a crash-risk and sentiment indicator, not a reliable return timer. Its predictive R² for short-horizon BTC returns is tiny. Open interest and liquidation data are risk-management inputs, not standalone predictors.

### Cited Findings
- BIS WP 1087 "Crypto carry" (Schmeling, Schrimpf, Todorov): high carry predicts future price crashes. A 10% rise in standardized carry predicts short-futures liquidations of 22% of open interest over the next month. Carry averages above 10% p.a. and can reach 60% p.a., driven by trend-chasing, attention-driven small investors seeking leveraged upside. — [BIS](https://www.bis.org/publications/working-paper-1087-crypto-carry); [VoxEU/CEPR](https://cepr.org/voxeu/columns/crypto-carry-market-segmentation-and-price-distortions-digital-asset-markets)
- Fulgur Ventures (practitioner): BTC 8-hour returns are slightly negatively correlated with BitMEX funding, consistent with contrarian mean reversion, but R² is 0.003. — [Medium/Fulgur](https://medium.com/@fulgur.ventures/bitcoin-funding-rates-and-price-predictability-27ce95535af1)
- Funding rates themselves are predictable one step ahead with double autoregressive (DAR) models on Binance and Bybit BTC contracts, beating a no-change forecast. That makes the rate predictable, not the price. — [Inan, SSRN 5576424](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5576424)
- Across 7 BTCUSDT liquidation cascades (2022-2025), no single pre-event measure reliably ranked severity. In the October 2025 case, 87.8% of post-onset forced selling happened within 30 minutes, and OI cleared 25-70%. This is a preprint based on 7 events. — [arXiv 2607.27070](https://arxiv.org/pdf/2607.27070)
- The risk/return of funding-rate arbitrage on CEX and DEX has been studied (a delta-neutral carry trade, not directional). — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2096720925000818)
- A "Quarter-Hour Effect" preprint documents periodic algorithmic trading and return predictability in crypto futures. — [arXiv 2607.09426](https://arxiv.org/pdf/2607.09426)

### Inferences
- For a spot long-only bot: use extreme positive funding or basis (for example, annualized funding in the top decile of its trailing distribution) as a de-risk or no-new-longs filter. Do not use it as an entry signal. Buying after capitulation (a large liquidation spike with funding flipping negative) is a plausible contrarian entry, but the systematic evidence is thin.

### Gaps
- No robust peer-reviewed evidence was found on long/short ratios predicting spot returns. There is no net-of-cost backtest evidence for funding-based directional spot strategies.

## 6. Sector/narrative rotation and BTC-to-altcoin lead-lag

### Takeaway
There is academic evidence of cross-coin lead-lag: large coins react first and small coins with a delay. But one JEDC-type result finds large-coin returns negatively predict small-coin returns next period (a "seesaw"). Evidence on narrative rotation is almost entirely industry commentary, and 2025 sector data shows the hyped narratives (AI, memes) lost money.

### Cited Findings
- Lagged returns of other cryptocurrencies significantly predict a given coin. Bitcoin reacts faster to common shocks and smaller coins react with a delay, which is consistent with limited attention. — [Cross-cryptocurrency return predictability, JEDC 2024](https://www.sciencedirect.com/science/article/abs/pii/S0165188924000551)
- The "seesaw effect": the five largest coins lead small coins negatively (large-coin returns negatively predict next-period small-coin returns), not vice versa. — [J. Empirical Finance 2023](https://www.sciencedirect.com/science/article/abs/pii/S0927539823000956)
- A 2026 high-frequency study of price transmission from Bitcoin to altcoins discusses trading implications. The content was not accessible. — [Asia-Pacific Financial Markets 2026](https://link.springer.com/article/10.1007/s10690-026-09589-z)
- BTC daily lagged returns positively predict ETH, ADA and BNB but not XRP (small-sample thesis-level study). — [Dergipark](https://dergipark.org.tr/en/download/article-file/2206815)
- In 2025, memecoins returned -31.61% and AI tokens -50.18% despite being the dominant narratives (62.8% of investor interest in Q1 2025). RWA returned +185.76% YTD (CoinGecko data). — [CCN on CoinGecko](https://www.ccn.com/news/crypto/crypto-sector-coingecko-rwa-win-ai-memecoin-lose/); [Cointelegraph on CoinGecko Q1 2025](https://cointelegraph.com/news/ai-memecoins-leading-crypto-narratives-q1-2025-coin-gecko)

### Inferences
- The lead-lag sign conflicts across studies (positive delayed reaction vs. a negative seesaw) and depends on horizon. Any "BTC up, buy lagging alts" rule has to be backtested at the specific horizon (minutes vs. days). At minute horizons, fees of 0.1%/side probably exceed the lag profit.
- Narrative momentum could in principle be a sector-level version of 1-4 week cross-sectional momentum. No rigorous evidence was found, and chasing the most popular narrative was a losing trade in 2025.

### Gaps
- No peer-reviewed sector-momentum study for crypto with post-2022 data and costs was found.

## 7. Mean reversion after extreme moves / pump-and-dump dynamics / chasing top 24h gainers

### Takeaway
Buying coins after extreme pumps is consistently a losing strategy. Pumps revert within minutes, only pre-positioned insiders profit, and lottery-like extreme-return coins underperform. This is the strongest "don't do this" finding in this review and bears directly on any "chase top 24h gainers" logic.

### Cited Findings
- Xu & Livshits (USENIX Security 2019): 412 Telegram pumps, June 2018 to Feb 2019. A model that predicts which coin will be pumped, buying before the pump, produced up to 60% return on small investments over 2.5 months. The profit comes from pre-positioning, not from buying after the signal. — [USENIX PDF](https://www.usenix.org/system/files/sec19-xu-jiahua_0.pdf); [arXiv 1811.10109](https://arxiv.org/abs/1811.10109)
- Kamps & Kleinberg: pump-and-dumps cause short-lived price, volume and volatility spikes followed by reversal "after some minutes." — [Crime Science 2018](https://link.springer.com/article/10.1186/s40163-018-0093-5)
- Hamrick, Gandal, Moore, Vasek et al.: thousands of Discord and Telegram pumps. Median returns were 7.7% for transparent pumps and 4.1% for obscured ones, measured at the peak. Many even of the insider members lose money, and admins buy before the pump starts. — [SSRN 3303365](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3303365); [BFI PDF](https://bfi.uchicago.edu/wp-content/uploads/Gandal-Neil-etal-An-examination-of-the-cryptocurrency-pump-and-dump-ecosystem.pdf)
- Pumps revert to the mean within minutes, and prices are about 30% lower one year after a pump (per a 2026 arXiv study summary). — [arXiv 2609.01176](https://arxiv.org/html/2609.01176v1)
- UCL researchers attributed $3.2T of artificial activity (Feb-Oct 2024 Telegram pumps) to 489 individuals who made about $250M in 2023. This comes via a Medium summary; the magnitude is implausibly large and should be treated with caution. — [Medium/Nefture](https://medium.com/coinmonks/cryptos-3-2-trillion-scam-just-489-people-behind-massive-telegram-pump-and-dump-9486c39cc6e3)
- Twitter-promoted pumps are studied in IRFA (2024). — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1057521924004113)
- Pump-and-dump manipulation in crypto is analysed in Review of Finance 2023 ("A New Wolf in Town?"). — [RePEc](https://ideas.repec.org/a/oup/revfin/v27y2023i3p935-975..html)
- In equities, the MAX effect (high maximum daily return last month) predicts underperformance, mostly on the short side, through lottery demand. — [Bali, Cakici & Whitelaw, JFE](https://pages.stern.nyu.edu/~rwhitela/papers/max%20jfe11.pdf). The crypto 1-day reversal result points the same way: prior-day losers outperform prior-day winners. — [IRFA 2021](https://www.sciencedirect.com/science/article/pii/S1057521921002349)
- A counterpoint at the major-coin level: after abnormal days in BTC, ETH and LTC (2017-2019), prices tended to keep moving in the same direction intraday and into the next day. Exceptions included BTC after positive overreactions, which reversed. — [Caporale & Plastun](https://link.springer.com/article/10.1007/s11408-020-00357-1)

### Inferences
- "Buy the top 24h gainers" collides with three effects at once: daily cross-sectional reversal, lottery overpricing, and pump reversal. For small caps, expect negative expectancy, before fees and worse after. Possible exception: 1-4 week relative-strength leaders among liquid large caps, which is the momentum result in Sections 1-2, not the 24h gainer list.
- A contrarian "fade the pump" requires shorting, which spot long-only cannot do. The usable implication is an exclusion filter: never buy coins with a very large 24h move and volume spike (for example, >+30% in 24h and more than 5× average volume). Those thresholds are my own illustration, not literature parameters.

### Gaps
- No direct academic backtest of "buy top-N 24h gainers on centralized exchanges" with post-2022 data was found.

## 8. BTC regime filters (trade alts only when BTC is above a moving average)

### Takeaway
The evidence on regime filters comes almost entirely from practitioner backtests. It consistently shows large drawdown reduction but little or no improvement in Sharpe. Treat a filter as risk control, not alpha.

### Cited Findings
- A GitHub cross-sectional momentum backtest on 10 large caps: adding a BTC 200-day MA filter cut max drawdown from -89.8% (naive momentum) and -81.9% (equal-weight benchmark) to -53.8%. It turned return positive but still did not beat equal-weight buy-and-hold on Sharpe. This is a hobbyist repo, not peer-reviewed. — [GitHub IsaacDodds](https://github.com/IsaacDodds/crypto-momentum-backtest)
- A vendor blog reports that adding a daily trend filter to a 4H RSI BTC strategy raised return from 27.18% to 34.81%, cut max DD from 42.42% to 23.54%, and raised Sharpe from 0.46 to 0.58. This is a vendor source with marketing incentives and unknown overfitting. — [Coinquant](https://www.coinquant.ai/blog/multi-timeframe-rsi-strategy-4h-entry-1d-trend-filter-on-bitcoin)
- Time-series momentum was negative in the 2022-2023 downturn (Section 1), which is the regime a BTC trend filter is meant to sit out. — [ResearchGate comparative study](https://www.researchgate.net/publication/401623816_Momentum_Mean_Reversion_and_Market_Timing_A_Comparative_Study_of_Active_Allocation_Strategies_versus_1N_Diversification_in_Digital_Assets)

### Inferences
- Parameters to test: BTC close above 50-, 100- or 200-day SMA (or 20-week); a BTC 4-week TSMOM sign; with and without a buffer band to reduce whipsaw. Report drawdown and time-in-market, not only return.

### Gaps
- No peer-reviewed study of BTC-MA regime filters on altcoin strategies was found.

## 9. Seasonality, time-of-day and weekend effects

### Takeaway
There are documented intraday patterns, but they are small, a few basis points or less. They are useful for timing execution and cannot stand alone at retail fees.

### Cited Findings
- Turn-of-the-candle (Shanaev, Vasenin & Stepanov, Heliyon 2023): +0.58 bps per minute concentrated at minutes 0, 15, 30 and 45 of each hour, with other minutes negative on average. It appears from mid-to-late 2020, holds out of sample and across exchanges, and a high-frequency strategy is described as net-outperforming from $5,000. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10015199/)
- Worst hours are around 03:00-04:00 UTC, though no hour is statistically negative. The split between intraday and overnight returns flips depending on whether the NYSE is open. — [Quantpedia](https://quantpedia.com/are-there-seasonal-intraday-or-overnight-anomalies-in-bitcoin/)
- There is a "Monday Asia Open" pickup from Sunday evening NY time into Monday. On NYSE days, most BTC gains accrue while the US stock market is closed, and the pattern reverses on weekends. — [PapersWithBacktest](https://paperswithbacktest.com/blog/bitcoin-never-sleeps-exploiting-seasonality); [Concretum Group](https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/)
- A day-of-week effect is studied with an hourly event-study approach. — [Oeconomia Copernicana](https://oeconomia.pl/index.php/oc/article/view/2091)
- Lagged momentum and reversal differ between daytime and overnight sessions for BTC and ETH (JRFM 2026). — [MDPI](https://www.mdpi.com/1911-8074/19/9/692)

### Inferences
- These effects are far smaller than 0.1%/side fees (0.58 bps per minute of edge vs. 10 bps per side). Use them only to schedule entries and exits for other strategies, for example avoiding the 03:00-04:00 UTC window, or as a secondary filter on intraday momentum.

### Gaps
- The time-of-day evidence reviewed here is almost entirely for BTC and gives no net-of-cost numbers for altcoins.

## 10. Cross-cutting: fees, decay, and overfitting

### Takeaway
At 0.1%/side, only low-turnover strategies (weekly-rebalanced TSMOM or cross-sectional momentum, regime-filtered) plausibly keep a positive edge. At 0.5-1%/side, essentially every short-horizon strategy in this review is likely erased except rare large-trend captures. Much of the headline evidence is pre-2022, from small illiquid coins, with survivorship risk.

### Cited Findings
- Realistic-cost analysis turns many statistically significant momentum portfolios into insignificant profits. — [Han, Kang & Ryu](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565)
- Reversal effects are driven by illiquidity, which is exactly where spreads and slippage are largest. — [IRFA 2021](https://www.sciencedirect.com/science/article/pii/S1057521921002349)
- Momentum strategies failed in 2022-2023 and were modestly positive in 2024-2025. — [ResearchGate comparative study](https://www.researchgate.net/publication/401623816_Momentum_Mean_Reversion_and_Market_Timing_A_Comparative_Study_of_Active_Allocation_Strategies_versus_1N_Diversification_in_Digital_Assets)

### Inferences
- Rough arithmetic: weekly rebalancing with 100% turnover means 52 round trips a year. At 0.2% per round trip that costs about 10%/yr; at 1-2% per round trip, about 52-104%/yr. Daily-turnover strategies cost 7× more. So fee tier is the first-order design decision: use maker orders on a low-fee venue.
- Survivorship: universes built from today's top-N coins overstate returns, because many coins from 2018-2021 are delisted or dead. Backtests should use point-in-time universes, including delisted coins.
- On the "grow capital fast over 30 days" goal: none of the documented edges supports reliable high 30-day returns. The best documented effects produce modest Sharpe ratios, with the edge concentrated in bull regimes. Aggressive sizing to chase fast growth increases the risk of ruin.

### Gaps
- There are no peer-reviewed post-2022 net-of-fee Sharpe estimates for most strategies. Full-text verification of every number above is still pending because primary-source fetches were blocked.
