# Next Edges to Test: Short-Horizon (1 day to ~2 weeks) Strategies With Published, Replicated, Net-of-Cost Evidence

Date: 2026-09-25. Scope: US stocks/ETFs (Yahoo daily/hourly, zero commission, 1-5 bp slippage) and crypto spot (Crypto.com/Kraken, 0.1-0.5%/side), long-only, no leverage, cash account, $500 per market.

Already tested and excluded from this review: weekly TSMOM, 1h EMA trend, volume-spike breakout, 10-day Donchian top-2 with BTC>100d filter (the current crypto winner), 10-day momentum rotation (stocks), hourly N-hour breakouts, intraday noise-area momentum, 1h ORB. Prior notes in `../Fast crypto trading bot plan/` and `../Professional day trading setups/` already cover crypto hour-of-day and weekend effects, pump reversal, BTC regime filters, and the overnight-drift decomposition; those are referenced, not repeated.

**Source-access caveat.** Nearly every primary site (Quantpedia, SSRN, ScienceDirect, Springer, arXiv, Substacks, QuantifiedStrategies, Allocate Smartly, TuringTrader, Alpha Architect) was blocked by the egress proxy. Only github.com fetched. Every number below therefore comes from search-result snippets unless marked **[FETCHED]**. Labels: **[PEER]** peer-reviewed, **[WP]** working paper/SSRN, **[REPL]** independent replication, **[VENDOR]** commercial blog with a product to sell, **[WEAK]** hobbyist/unverified, **[SNIPPET]** figure seen only in a search snippet.

---

## 0. Bottom line

1. The strongest new candidates are (a) an **ensemble-Donchian, volatility-targeted upgrade of the existing crypto rotation** (Zarattini/Pagani/Barbon 2025, net-of-fee, survivorship-free universe), (b) **daily mean reversion on SPY/QQQ (IBS and Connors RSI(2)/cumulative RSI) above the 200-day MA**, which has 30 years of public evidence, near-zero cost at 1-5 bp, and low correlation with the crypto trend sleeve, and (c) **Quantpedia's 10-day MIN mean-reversion rule on BTC**, which is the mirror image of the MAX/Donchian rule already running and was re-confirmed out-of-sample through Aug 2024.
2. Calendar effects (turn-of-the-month, pre-FOMC, pre-holiday) are real but small (about 10-15 bp/day on the good days) and are best used as **overlays that decide when idle stock cash is invested**, not as standalone systems.
3. Monthly ETF rotation (GEM, BAA, DAA, HAA) is the most robust family in the list but compounds at roughly 8-14%/yr net with 15-25% drawdowns; it is a capital-parking baseline, not a fast compounder. GEM had its worst drawdown ever in 2021-2023.
4. PEAD in large caps is contested and hard to do properly with free data; the earnings *announcement premium* (hold through the event) is better documented in large caps. Low priority.
5. Portfolio: run the crypto trend sleeve and the stock mean-reversion sleeve as separate $500 books. Crypto trend has near-zero correlation with equity trend programs (Man Group: about 7% vs SG Trend), and mean reversion is structurally anti-correlated with trend in the same asset. A 35% max-DD budget is met by the 25% vol target on the crypto side and by the "mostly in cash" nature of the stock MR side.

Ranked shortlist with implementable specs is in Section 8.

---

## 1. Short-term mean reversion in stocks and ETFs

### 1a. Connors RSI(2) and cumulative RSI(2)

**Sources.** Connors & Alvarez, *Short Term Trading Strategies That Work* (2008) [book]. QuantifiedStrategies RSI(2) guide [VENDOR] — [rsi-2-strategy](https://www.quantifiedstrategies.com/rsi-2-strategy/), [rsi2-on-spy](https://www.quantifiedstrategies.com/rsi2-on-spy/), [cumulative RSI](https://www.quantifiedstrategies.com/cumulative-rsi-indicator/). GuruFinance Substack 26-year SPY replication [WEAK/REPL] — [link](https://gurufinanceinsights.substack.com/p/i-backtested-the-classic-rsi2-mean). Quantitativo cumulative-RSI study [WEAK/REPL] — [link](https://www.quantitativo.com/p/squeezing-more-profits-with-cumulative). StockSoft Research on US stocks [WEAK] — [link](https://stocksoftresearch.com/rsi-2-trading-strategy/). Betashorts Medium (generic Pine RSI, 5 assets) [WEAK] — [link](https://medium.com/@betashorts1998/i-backtested-the-same-pine-script-rsi-strategy-on-5-different-assets-every-single-one-lost-money-431dc2b9d13e).

**Original rules (Connors).** Close > 200-day SMA; RSI(2) < 5 (aggressive: < 10; cumulative variant: RSI(2)_t + RSI(2)_{t-1} < 35); buy at that close; exit at close when RSI(2) > 65 (or close > 5-day SMA). No stop.

**Evidence, numbers [SNIPPET].**
- Original SPY 1993-2008 cumulative RSI: 88% winners, avg +1.26%/trade, avg hold 3.7 days.
- QuantifiedStrategies SPY RSI(2), 1993-present: avg +0.57%/trade, 75% win, max DD 23% (no costs).
- GuruFinance replication (26 yrs SPY): 181 trades, 82% win, max DD -13.8% vs -55% B&H; in cash about 90% of the time; described as capital-preservation rather than return-maximiser.
- Recent decay: "slight decay 2015-2025 from HFT competition, core edge retained; win rate dropped below 60% in 2008 and March 2020" (QS, [VENDOR]). Betashorts (generic RSI script, not Connors filters) reports SPY 2024-Mar 2026: 30% win rate, -28.9% — this tests an RSI(14)-style Pine script without the 200-day filter and is not evidence against Connors' rules, but it shows that the 2024-2025 tape (sharp drops, V-recoveries) triggered entries before bounces completed.
- Cumulative RSI vs plain RSI(2): Quantitativo reports higher profit per trade with fewer trades (numbers not retrievable).

**Data needs.** Daily OHLC only. **Turnover.** About 6-10 round trips/yr on SPY, 8-15 on QQQ; average hold 2-5 days. **Cost sensitivity.** At 1-5 bp slippage the edge (50-120 bp/trade) is essentially intact; at crypto-level fees (0.2-1% round trip) it would be halved or erased, so this is a **stocks-only** idea. **Regime risk.** The 200-day filter is what keeps it out of 2008/2022; it still bleeds in fast crashes that start above the MA (Feb 2020, Apr 2025).

**Verdict: TEST (high priority, QQQ and SPY).** Cheap, decades of public evidence, orthogonal to the crypto trend sleeve. Expect roughly 5-10% CAGR on capital with 10-15% max DD if used alone; its value is higher when it shares capital with a calendar overlay (Section 2) because both are flat most of the time.

### 1b. Internal Bar Strength (IBS)

**Sources.** Pagonidis, "The IBS Effect: Mean Reversion in Equity ETFs", NAAIM Wagner Award paper 2013 [WP] — [PDF](https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf). Kinlay 2019 [practitioner] — [link](https://jonathankinlay.com/2019/07/the-internal-bar-strength-indicator/). Alvarez Quant Trading [practitioner] — [link](https://alvarezquanttrading.com/blog/internal-bar-strength-for-mean-reversion/). QuantifiedStrategies IBS pages [VENDOR] — [link](https://www.quantifiedstrategies.com/ibs-internal-bar-strength-indicator-strategies/). toniker10 GitHub SPY IBS engine, 1993-2026 [WEAK/REPL] **[FETCHED]** — [link](https://github.com/toniker10/SPY-IBS-Mean-Reversion-Strategy). TradingInvestingStrategies Substack (SPY/QQQ/Gold/BTC) [WEAK] — [link](https://tradinginvestingstrategies.substack.com/p/ibs-mean-reversion-strategy-backtest). StatOasis (NQ futures 2024) [VENDOR] — [link](https://statoasis.com/overfit/research/how-the-ibs-strategy-made-45k-in-2024-even-in-a-down-market). Algotradekit TradingView script with per-instrument parameters [WEAK] — [link](https://www.tradingview.com/script/C6uAEwxB-IBS-Internal-Bar-Strength-Trading-Strategy-for-SPY-and-NDQ/).

**Definition.** IBS = (Close − Low) / (High − Low), in [0, 1].

**Evidence.**
- Pagonidis 2013 [WP, SNIPPET]: across equity ETFs, next-day mean return +0.35% when IBS < 0.2 and −0.13% when IBS > 0.8; effect is strongest in index ETFs and stronger during volatile/bear periods.
- toniker10 **[FETCHED]**: rule "buy next open if IBS < 0.20, sell next open if IBS > 0.80", SPY 1993-2026: CAGR 12.67% vs 10.83% B&H, max DD −26.1% vs −55.2%, Sharpe 0.97 vs 0.65, 69.3% win, profit factor 1.93, 989 trades, zero commission and **no slippage**, single parameter set, no walk-forward. Note the entry is next open, so the overnight edge (Section 2d) is *not* captured; buying at the close should do better in principle.
- QuantifiedStrategies [VENDOR, SNIPPET]: "buy at close if IBS < 0.2, sell at close when IBS > 0.8": SPY avg +0.8%/trade, 78% win; QQQ avg +1.33%/trade, 75% win; QQQ variant "Sharpe 2.25, max DD −11.7%, 7.4% annualised"; only three losing years in the sample (1994, 2002, 2018).
- Substack test [WEAK, SNIPPET]: same thresholds on SPY, QQQ, GLD, BTC gave 61-70% win rates; "SPY +40% with 2.85% DD" (period not visible, treat as unverified).
- StatOasis [VENDOR, SNIPPET]: IBS on NQ futures had 100% winners in 2024 and 75% in 2025 YTD, i.e. the effect was alive in 2024-2025.
- Algotradekit recommended settings [WEAK]: QQQ entry IBS ≤ 0.09, exit ≥ 0.985, EMA(220) filter, max hold 14 days; SPY entry ≤ 0.11, exit ≥ 0.995, EMA(200), max hold 12 days. These look overfit; use the round 0.2/0.8 or 0.1/0.9 pair.

**Data needs.** Daily OHLC (Yahoo is fine; IBS needs true daily high/low, so use the regular-session bar). **Turnover.** 25-40 round trips/yr on SPY, more on QQQ; typical hold 1-3 days. **Cost sensitivity.** At 5 bp per side the roughly 50-130 bp average trade survives comfortably; not viable at crypto spot fees unless the crypto instrument's per-trade edge is far larger (Section 3c).

**Verdict: TEST (highest-priority stock idea).** More trades than RSI(2), so faster statistical verdict. Combine IBS and RSI(2) as an OR-entry (QuantifiedStrategies' "S&P 500 mean reversion using IBS and RSI" page does exactly this [VENDOR]).

### 1c. Double 7s and "buy the 3-day decline above the 200-day MA"

**Sources.** Connors & Alvarez 2008. QuantifiedStrategies/RobustTrader Double-7 pages [VENDOR] — [link](https://www.quantifiedstrategies.com/larry-connors-double-seven-strategy-does-it-still-work/), [link](https://therobusttrader.com/larry-connors-double-seven-strategy/). Ayrat Murtazin ETF-basket backtest [WEAK/REPL] — [link](https://ayratmurtazin.beehiiv.com/p/backtest-results-for-larry-connors-double-7-strategy).

**Rules.** Double 7s: close > 200-day SMA; buy at close when close is a 7-day closing low; sell at close when close is a 7-day closing high; no stop. "3-day decline": close > 200-day SMA, three consecutive lower closes (or 3-day return ≤ −X%), buy close, exit when close > previous day's high or RSI(2) > 65 (QuantifiedStrategies has several of these; exact thresholds not retrievable).

**Evidence [SNIPPET].** SPY since 1993: 154 trades, avg +1.18%, 82.5% win. Liquid-ETF basket over 21 years: 1,189 trades, avg +0.63%/trade, CAGR 6.3%, and "almost all gains before 2010". Vendor's own conclusion: still works on major indices, low trade count, does not beat buy-and-hold; useful only inside a basket.

**Verdict: SKIP as a standalone; fold into the IBS/RSI(2) entry logic** (a 7-day low is highly collinear with RSI(2) < 10). The "3-day decline" is likewise just a coarser RSI(2) signal.

### 1d. Cross-cutting notes on stock mean reversion (2015-2026)

- Regime: all these rules lose in prolonged declines (2008, 2022 below 200-day MA) and in fast crashes that begin above the MA. Public evidence for 2024-2025 is mixed: IBS on NQ was strongly positive [VENDOR], generic RSI scripts without filters lost [WEAK]. Nothing peer-reviewed post-2020.
- Filters with public support: 200-day SMA (all sources), VIX < 25 or a volatility cap (QS mention), and "only trade the index ETF, not single stocks" (Pagonidis: index ETFs mean-revert most).
- Overnight timing (Section 2d): enter at the close, exit at the close or the next open; never enter at the open.
- Cash-account mechanics: buying at close and selling 1-3 days later is fine in a cash account (T+1 settlement); a same-day round trip is a day trade only if bought and sold the same session, which these rules do not do. Prior notes (day-trading setups, Section 6) cover PDT.

---

## 2. Calendar anomalies (status 2020-2026)

### 2a. Turn-of-the-month (TOM)

**Sources.** Quantpedia "Turn of the Month in Equity Indexes" (last 4 + first 3 trading days) [Quantpedia] — [link](https://quantpedia.com/strategies/turn-of-the-month-in-equity-indexes). QuantSeeker, "Turn-of-the-Month Strategies: Do They Still Work?" (12 Jul 2026) [practitioner/REPL] — [link](https://www.quantseeker.com/p/turn-of-the-month-strategies-do-they). Zerodha "In the Money" TOM note [WEAK] — [link](https://inthemoneybyzerodha.substack.com/p/turn-of-the-month-tomtotm-strategy). QuantifiedStrategies TOM pages [VENDOR] — [link](https://www.quantifiedstrategies.com/end-of-month-strategy-in-sp-500/). Quantpedia "Sectoral Intramonth Momentum Cycle" (Dec 1998-Jun 2026) [Quantpedia] — [link](https://quantpedia.com/sectoral-intramonth-momentum-cycle/).

**Evidence [SNIPPET].**
- QuantSeeker 2026: the 4-day window (last trading day + first three) carries about **12 bp/day** on average with other days near zero; that is the classic Lakonishok-Smidt result re-estimated on recent data.
- Zerodha (index unspecified, likely US and NIFTY): TOM outperformed 2020-2023, then a lull 2024-2025.
- QuantifiedStrategies: S&P 500 first 4 trading days annualised 25.4%, middle of month 1.6%, last 2 days 19.1% (long sample). A plain SPY TOM system was quoted at CAGR 2.9%, max DD 12% (period unknown) — small because it is invested ~30% of the time.
- Quantpedia 2026 sector study: 252-day sector momentum spread is positive on trading day 1, reverses sharply on days 2-3, and reappears 10-5 days before month-end; composite long-short 5.99%/yr, Sharpe 0.55.
- The FPA "TOM in the age of ETFs" paper found that switching between T-bills and index funds on TOM underperformed buy-and-hold in recent samples (i.e. the effect is real per day but the strategy misses the other days' drift).

**Rule.** Buy SPY (or QQQ) at the close of the 4th-to-last trading day of the month (T-4); sell at the close of the 3rd trading day of the new month (T+3). 12 trades/yr, ~7 sessions each, ~30% time in market. Optional trend gate: only when SPY close > 200-day SMA.

**Costs.** 24 executions/yr at 1-5 bp is 0.1-0.25%/yr; negligible. **Verdict: TEST as an overlay** that deploys otherwise-idle stock cash; expect 3-6%/yr on capital with shallow drawdowns; do not expect it to compound fast.

### 2b. Pre-holiday effect

**Sources.** Quantpedia "Pre-Holiday Effect" [Quantpedia] — [link](https://quantpedia.com/strategies/pre-holiday-effect). "The Holiday Effect", SSRN 5073776 (1990-2024, global indexes) [WP] — [link](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5073776). Quantpedia Thanksgiving/Christmas [Quantpedia] — [link](https://quantpedia.com/thanksgiving-and-christmas-trading-strategies/). Quantpedia "Pre-Holiday Drift Signal for Bitcoin" (BITO, Jan 2018-Jun 2025) [Quantpedia] — [link](https://quantpedia.com/surprisingly-profitable-pre-holiday-drift-signal-for-bitcoin/).

**Evidence [SNIPPET].** Pre-holiday day returns are roughly 10x a normal day historically; SSRN 2024 study finds the pre-holiday effect still present in North American and Asian markets 1990-2024, with abnormal returns clustered around MLK Day, Presidents' Day and Thanksgiving. For Bitcoin, Quantpedia found a pre-holiday drift only when combined with a short-term momentum trigger (price at an N-day high entering the D-5..D+5 window).

**Rule.** Buy SPY at the close two sessions before a US market holiday (D-2), sell at the close of D-1 (or the first post-holiday close). About 9-10 events/yr, roughly 10-20 bp each: about 1-2%/yr. **Verdict: ADD to the calendar overlay** (cheap), not a standalone.

### 2c. FOMC drift

**Sources.** Lucca & Moench, *JF* 2015 [PEER]: 49 bp average in the 24 h before announcements, Sep 1994-Mar 2011, about 80% of annual equity premium. Kurov, Wolfe & Gilbert, *FRL* 2021 "The disappearing pre-FOMC announcement drift" [PEER] — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7525326/): drift essentially gone after 2015 (sample to Dec 2019). Ignatieva & Ohashi, *Applied Economics* 2024 [PEER] — [link](https://www.tandfonline.com/doi/full/10.1080/00036846.2024.2322573): drift on press-conference days is short-lived. QuantSeeker "Trading the Fed: The Pre-FOMC Drift is Alive" (1-min SPY, Jan 2014-Dec 2024) [practitioner/REPL] — [link](https://www.quantseeker.com/p/trading-the-fed-the-pre-fomc-drift). Hobbyist 2023-2025 confirmation on 24 meetings [WEAK] — [link](https://github.com/HarryWarre/trading-model-ai-lab/issues/60). Fed FEDS 2026-023 [WP] — [PDF](https://www.federalreserve.gov/econres/feds/files/2026023pap.pdf) (not readable; title suggests FOMC-return work).

**Status [SNIPPET].** Academic consensus 2015-2019: gone. QuantSeeker 2025 with minute data: prices drift up from the close of the day before the meeting through the end of the announcement day, peaking around the 2 pm decision/press conference; positive in 2014-2024. The hobbyist 2023-2025 check found non-negative average returns each year (bootstrap P(mean>0) ≥ 95%), but it is a 24-event sample. Post-announcement: when SPY closes up on FOMC day, T+1..T+5 averaged +0.72%; when down, −0.48% (source unclear, [WEAK]).

**Rule.** Buy SPY at the close of the session before the scheduled FOMC decision day; sell at the close of the decision day. 8 events/yr. Optionally hold 5 more days if the decision-day close was up. **Verdict: ADD to the calendar overlay, low weight.** Expected 1-3%/yr on capital; the evidence of a post-2015 revival rests on one practitioner study plus a hobbyist check.

### 2d. Overnight vs intraday

**Sources.** Lou, Polk & Skouras *JFE* 2019 [PEER]; Alpha Architect cost analysis [practitioner] — [link](https://alphaarchitect.com/trading-costs-wipe-out-the-overnight-return-anomaly/); Elm Wealth "Still working the night shift" [practitioner] — [link](https://elmwealth.com/night-shift/); Boyarchenko et al. *RFS* 2023 and NY Fed 2026 follow-up (overnight drift about zero since 2021; see prior day-trading notes); GuruFinance/HMA Quant Substacks [WEAK] — [link](https://hmaquant.substack.com/p/overnight-vs-intraday-returns-the).

**Status [SNIPPET].** SPY Q3 2020-Q3 2025: close-to-open +47.1% cumulative vs open-to-close +29.9%; over 30 years $1 overnight grew to about $17 vs $1.20 intraday. Alpha Architect: 250 round trips/yr at even 1-2 bp consume most of the roughly 9%/yr overnight premium; statistical robustness is low. **Verdict: SKIP as a system; USE as execution timing** — every stock entry above should be at the close, and exits should be at the close or open, never enter at the open.

---

## 3. Crypto short-term reversal, dip-buying, IBS, weekends, capitulation

### 3a. Cross-sectional short-term reversal (daily/weekly losers)

**Sources.** Zaremba, Bilgin, Long, Mercik & Szczygielski, "Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets", *IRFA* 2021 [PEER] — [link](https://www.sciencedirect.com/science/article/pii/S1057521921002349). "Cryptocurrency return reversals" (Fairfield) [WP] — [PDF](https://digitalcommons.fairfield.edu/cgi/viewcontent.cgi?article=1249&context=business-facultypubs). "New behaviorally-based cross-sectional reversal portfolios in the cryptocurrency market", *FRL* 2025 [PEER] — [link](https://www.sciencedirect.com/science/article/abs/pii/S154461232501058X). "Short-horizon mean reversion in cryptocurrency markets: a matched cross-market measurement", arXiv 2608.21888 (2026) [WP] — [link](https://arxiv.org/html/2608.21888v1).

**Findings [SNIPPET].**
- Zaremba et al. (3,600+ coins, 2015-2021): coins with the lowest prior-day return outperform the highest at daily, weekly and monthly horizons, but the effect is **driven by illiquidity; the largest, most tradeable coins show daily momentum, not reversal.**
- FRL 2025: reversal portfolios remain profitable under "conservative transaction costs" (long-short, and the long leg is in illiquid names).
- arXiv 2026: at 15-minute horizons, 90% of 183 Binance pairs show significant directional reversal vs 2.7% of US stocks/ETFs; this is microstructure reversal, not tradeable at 10-50 bp/side.

**Verdict: SKIP for long-only spot.** The tradeable-size long leg (majors) shows momentum, not reversal; the reversal is in coins where spread + fees exceed the edge. This agrees with the prior notes' "don't chase or fade 24h movers".

### 3b. Time-series dip-buying in majors: Quantpedia MIN rule

**Sources.** Padysak & Vojtko, "Seasonality, Trend-following, and Mean reversion in Bitcoin", SSRN 4081000 (2022) [WP] — [link](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4081000); Beluská & Vojtko, "Revisiting Trend-following and Mean-Reversion Strategies in Bitcoin", SSRN 4955617 (2024, Nov 2015-Aug 2024, with a Feb 2022-Aug 2024 out-of-sample section) [WP/REPL] — [link](https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin/); PapersWithBacktest summary [VENDOR] — [link](https://paperswithbacktest.com/blog/bitcoin-never-sleeps-exploiting-seasonality).

**Rules.** For lookback N in {10, 20, 30, 40, 50}: MAX = hold BTC on the day after the close is the highest close of the last N days (trend); MIN = hold BTC on the day after the close is the lowest close of the last N days (mean reversion). The two are mutually exclusive, so the combined rule holds BTC whenever either fires. The sources describe a one-day holding period re-evaluated daily; in practice the position persists on consecutive signal days.

**Numbers [SNIPPET].** Combined 10-day MAX+MIN, Nov 2015-Aug 2024: annualised 98.4%, vol 47.8%, max DD −37.7%, return/vol 2.06, vs buy-and-hold about 65% annualised at 75% vol and −83.7% max DD. Shorter windows (10 days) were the most robust; MIN alone is "less profitable but significantly less risky" than MAX alone. The 2024 revisit states both approaches "remained effective" in the Feb 2022-Aug 2024 out-of-sample window. Fees: the papers' cost assumptions were not retrievable; at 10-day MIN the average episode lasts 1-3 days, so at 0.1-0.5%/side the strategy needs roughly 0.5-2% per episode to break even. BTC's 5-day moves after a 10-day low are of that order in bull regimes only, which is why a trend gate matters.

**Related "capitulation" statistics [WEAK].** A LedgerMind guide citing Glassnode: 78% of BTC daily moves > 8% retrace at least 50% within 5 days; mean-reversion entries lose 62% of the time when ADX > 40 and an ADX filter raised win rate from 63% to 76%. Caporale & Plastun (prior notes) found BTC continued rather than reversed after abnormal down days in 2017-2019 but reversed after positive overreactions. The prior notes' pump-reversal evidence applies to small caps, not to BTC/ETH.

**Verdict: TEST.** Implement 10-day MIN on BTC and ETH with a regime gate (close > 100- or 200-day SMA) and a 3-day time stop, and log gross vs net at 0.1%, 0.25% and 0.5% per side. Priority is high because it is the natural complement to the running MAX/Donchian rule (combined MDD −37.7% vs −83.7% B&H is the best documented crypto drawdown reduction in this review).

### 3c. Crypto IBS

**Sources.** Only vendor/hobby tests: TradingInvestingStrategies Substack (BTC included, 61-70% win rates) [WEAK]; CoinGecko IBS explainer [VENDOR] — [link](https://www.coingecko.com/learn/internal-bar-strength-ibs); FMZ/TradingView scripts [WEAK]. No peer-reviewed crypto IBS study found.

**Issue.** Crypto has no session close; Yahoo's BTC-USD "day" is UTC. IBS near 0 after a −6% UTC day in a BTC uptrend is a plausible dip signal, but the evidence base is vendor-only. **Verdict: quick TEST only as a variant of 3b** (entry: IBS < 0.2 and close > 100-day SMA; exit: IBS > 0.8 or 3 days). Fees are the constraint: at 0.5%/side the per-trade edge must exceed 1%.

### 3d. Weekend effects

**Sources.** "Bitcoin's Weekend Effect: Returns, Volatility, and Volume (2014-2024)", PBES 2025 [PEER, low-tier journal] — [link](https://ojs.bbwpublisher.com/index.php/PBES/article/view/11691): no detectable weekend-weekday gap in average returns in 2020-2023 or early 2024; volatility and volume lower on weekends. ACR journal "weekend effect in crypto momentum" [PEER, low-tier]: weekend mean 0.26% vs 0.14% weekday for BTC/ETH, stronger in 2020-2021 bulls [SNIPPET]. "A crypto-stock weekend effect", *FRL* 2025 [PEER] — [link](https://www.sciencedirect.com/science/article/pii/S1544612325019154): weekend crypto returns predict Monday stock returns (a cross-asset signal, not a crypto trade). Prior notes already cover the Monday Asia-open pickup and Quantpedia's NYSE-open/closed split.

**Verdict: SKIP as a trade;** keep as an execution rule (avoid opening positions into low-liquidity weekend hours on Kraken/Crypto.com where spreads widen).

---

## 4. Volatility-managed momentum and multi-lookback ensembles (crypto)

### 4a. Ensemble Donchian with vol targeting (the direct upgrade to the current winner)

**Source.** Zarattini, Pagani & Barbon, "Catching Crypto Trends: A Tactical Approach for Bitcoin and Altcoins", SSRN 5209907 / Swiss Finance Institute RP 25-80 (2025) [WP, survivorship-bias-free CoinMarketCap universe] — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5209907), [Concretum](https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/). Rule details confirmed from a GitHub pre-registration that transcribes the paper **[FETCHED]** — [link](https://github.com/zebadee2kk/DeFi-TraderStack-Agent/issues/137). Independent replication attempt by "The Replicator" Substack [WEAK] — [link](https://delphicalpha.substack.com/p/the-replicator-catching-crypto-trends).

**Rules [FETCHED + SNIPPET].**
- Nine sub-models, lookbacks L in {5, 10, 20, 30, 60, 90, 150, 250, 360} days.
- Sub-model L is long when today's close is above the maximum close of the prior L days; it exits when price falls to its trailing stop, defined as max(previous stop, midpoint of the L-day Donchian channel). Stops only ratchet up.
- Signal = equal-weighted average of the nine sub-model states (0 or 1), so exposure is in {0, 1/9, ..., 1}.
- Position size = signal × min(1, 25% / realised vol), realised vol from 90-day daily returns, annualised; leverage capped at 1.0 (i.e. never more than 100% of the sleeve).
- Daily rebalance on closes. Universe: coins listed ≥ 1 year with 30-day median daily volume ≥ $2M, point-in-time monthly snapshots; rotational variant holds the top-20 most liquid names.
- Fees: net of 0.10-0.50% per trade (paper reports a range).

**Results [SNIPPET].** BTC, Jan 2015-Mar 2025: net CAGR 30%, Sharpe 1.56-1.58, Sortino 2.03, max DD 19% (vs > 80% for buy-and-hold), alpha about +14%/yr vs BTC. Top-20 rotational portfolio: net CAGR 18%, max DD 11%, Sharpe > 1.5, alpha 10.8%/yr vs BTC. Outperformance concentrated in 2017, 2020-2021 and late 2023; the model sits out much of 2022.

**Why it should beat single-lookback Donchian-10.** The 10-day model alone captures the 2025-26 tape well (your +85% OOS) but is one parameter; the ensemble spreads timing risk across horizons, and the vol target mechanically shrinks exposure when 90-day vol is above 25% (BTC's typical 40-60%), which is how the paper gets a 19% max DD. For a $500 no-leverage sleeve the vol target is a *de-leverager only*: expected exposure in a normal BTC regime is 40-60% of the sleeve, so CAGR is lower than the unscaled rotation but the DD budget (< 35%) is respected.

**Verdict: IMPLEMENT/TEST (top priority for crypto).** Compare three variants on the same 2025-26 OOS window: (i) current Donchian-10 top-2; (ii) 9-lookback ensemble on BTC/ETH only; (iii) ensemble rotation top-2/top-3 with 25% vol target.

### 4b. Volatility-managed cross-sectional crypto momentum

**Sources.** "Cryptocurrency market risk-managed momentum strategies", *FRL* 2025 [PEER] — [link](https://www.sciencedirect.com/science/article/abs/pii/S1544612325011377): weekly momentum scaled by inverse realised variance (Barroso & Santa-Clara style) raised weekly returns from 3.18% to 3.47% and Sharpe from 1.12 to 1.42; the average scaling weight is 1.14 (> 1), so the gain comes from *adding* exposure in calm periods, which a no-leverage account cannot do; robust to transaction costs and short-sale constraints in the paper. "Cryptocurrency momentum has (not) its moments", *FMPM* 2025 [PEER] — [link](https://link.springer.com/article/10.1007/s11408-025-00474-9): crypto momentum has severe crashes; volatility management mitigates them. Le & Ruthbah (Monash) trend-following for crypto [WP] — [PDF](https://www.monash.edu/__data/assets/pdf_file/0011/3744821/Trend-following-Strategies-for-Crypto-Investors.pdf): 20-day and 65-day momentum beat longer lookbacks; costs erode frequent rebalancing. Man Group "In Crypto We Trend" [practitioner] — [link](https://www.man.com/insights/in-crypto-we-trend): diversified crypto trend has about 7.4% average correlation to the SG Trend index. Grayscale "The trend is your friend" [VENDOR] — [link](https://research.grayscale.com/reports/the-trend-is-your-friend-managing-bitcoins-volatility-with-momentum-signals). Bernardi/"A Decade of Evidence of Trend Following in Cryptocurrencies", arXiv 2009.12155 [WP].

**Implication for a long-only, no-leverage $500 sleeve.** Vol scaling's documented Sharpe benefit in crypto comes partly from levering up in calm regimes, which is unavailable. What remains is the drawdown cap. Use 25% vol target with leverage cap 1 exactly as in 4a; expect Sharpe roughly unchanged and max DD roughly halved versus unscaled.

**Verdict: IMPLEMENT as part of 4a;** do not build a separate vol-managed cross-sectional system.

---

## 5. Monthly ETF rotation (GEM, BAA, DAA, HAA, sector momentum)

**Sources.** Antonacci, *Dual Momentum Investing* (2014) and extended backtest [practitioner] — [link](https://medium.com/@garyantonacci_30463/extended-backtest-of-global-equities-momentum-dual-momentum-eb12902612e0). Petit, "Global Equities Momentum, 1971-2026: A Replication of Antonacci's Dual Momentum and a Decomposition of its Returns", SSRN 7427878 (Sep 2026) [WP/REPL] — [link](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7427878). Keller, "Bold Asset Allocation", SSRN 4166845 (2022) [WP]; Keller & Keuning, "Defensive Asset Allocation", SSRN 3212862 (2018) [WP]; Keller & Keuning, "Hybrid Asset Allocation", SSRN 4346906 (2023) [WP]. Allocate Smartly trackers [VENDOR, but independent re-implementation] — [BAA](https://allocatesmartly.com/bold-asset-allocation/), [2022 bear-market review](https://allocatesmartly.com/tactical-asset-allocation-performance-during-the-2022-bear-market/). TuringTrader/PortfolioDB/BestFolio trackers [VENDOR]. Accelerating Dual Momentum (Engineered Portfolio) [WEAK]. TSX 60 sector rotation 2000-2025, *JRFM* 2026 [PEER] — [link](https://www.mdpi.com/1911-8074/19/1/70).

**GEM rules.** Monthly: if SPY 12-month return > T-bill 12-month return, hold the better of SPY and ACWX/VEU by 12-month return; else hold AGG/BND.
**GEM results [SNIPPET].** Petit 1971-Jul 2026: CAGR 15.18% vs 11.27% S&P, max DD 21.7% vs 50.9%, Sharpe 0.83 vs 0.50, 1.5 trades/yr; **but −4.8 pts/yr vs passive since 2010 and its deepest drawdown in 55 years occurred in 2021-2023 while holding the defensive bond asset.** A different implementation (1986-Sep 2026) shows 12.3% CAGR, −33.7% max DD. Accelerating Dual Momentum: Jan 2022-Oct 2023 CAGR −15.4%, max DD −33.4% (rates shock).

**BAA rules (Keller 2022).** Monthly. Momentum score 13612W = (12·r1 + 4·r3 + 2·r6 + 1·r12)/4 where r_k is the k-month total return. Canary universe {SPY, EFA, EEM, AGG}: if **any** canary has 13612W < 0, go defensive; else offensive. Offensive (BAA-G4): top 1 of {QQQ, EFA, EEM, AGG} by relative momentum SMA12 = price / average of last 13 month-end prices − 1 (BAA-G12: top 6 of 12: SPY, QQQ, IWM, VGK, EWJ, EEM, VNQ, DBC, GLD, TLT, HYG, LQD). Defensive: top 3 of {TIP, DBC, BIL, IEF, TLT, LQD, BND} by SMA12, with any asset whose SMA12 is below BIL's replaced by BIL.
**BAA results [SNIPPET].** Paper Dec 1970-Jun 2022: ≥ 20% CAGR with ≤ 15% monthly max DD (in-sample). Allocate Smartly re-implementation Apr 1997-Apr 2026: CAGR 11.2%, Sharpe 1.12, vol 9.9%, max DD −14.4%; since Jun 2008: 9.9% CAGR, −16.6% max DD. Allocate Smartly notes TAA as a group did "reasonably well in 2025 and very well in early 2026" vs 60/40; one member reported 2024 above 20% and 2025 above 30% for their best model (not named) [WEAK].

**DAA [SNIPPET].** Canary {VWO, BND}; offensive top 6 of 12 by 13612W; defensive best of {SHY, IEF, LQD}. Trackers: 13.7% CAGR, −16.6% max DD, Sharpe 0.98 since 1973; 2022 max DD −12.1%, worse than 2000-02 and 2007-08 because the defensive assets were bonds.

**HAA [SNIPPET].** Canary TIP (13612U = simple average of 1/3/6/12-month returns); offensive top 4 of {SPY, IWM, VEA, VWO, VNQ, DBC, IEF, TLT} by 13612U, any with negative score replaced by the best of {IEF, BIL}; defensive best of {IEF, BIL}. TuringTrader quotes Feb 1974-Aug 2026: 16.2% CAGR, −19.7% max DD, Sharpe 1.49 (long simulated history; treat as optimistic). A 2024 ensemble containing HAA: +12% with 3.4% max DD [WEAK].

**Sector rotation [SNIPPET].** TSX study 2020-2025 OOS: 16.9% vs 15.5% buy-and-hold, best Sharpe with quarterly rebalance. US sector momentum literature: 1-3%/yr excess with high year-to-year variance. Actively managed SECT ETF (not a pure rule): −12.8% (2022), +21.1% (2023), +18.6% (2024), +17.8% (2025), roughly SPY-like.

**Practical for $500.** Yahoo month-end closes are enough; fractional shares required; 12-24 trades/yr at 1-5 bp is negligible cost. Realistic net expectation from independent trackers: **8-14% CAGR, 15-25% max DD, and multi-year stretches behind the S&P (2010-2020, 2021-2023).**

**Verdict: TEST as the stock sleeve's "cash parking" baseline only if the mean-reversion + calendar overlay leaves capital idle > 60% of the time;** otherwise SKIP. It will not deliver fast compounding, and its bond leg is the weak point in inflationary regimes.

---

## 6. Post-earnings announcement drift (brief)

**Sources.** Martineau, "Rest in Peace Post-Earnings Announcement Drift", *Critical Finance Review* 2022 [PEER]: drift vanished from non-microcaps by 2006. UCLA Anderson Review 2025 "Is PEAD a thing again?" [summary] — [link](https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/): two 2025 papers claim PEAD is alive; Meursault et al. (2023) find it with text-based surprises 2008-2019; a UCLA study finds it diminished in large caps but present in small/mid caps. "Asymmetric PEAD and order flow imbalance", *IRFA* 2024 [PEER]. "Inverse PEAD" (2025) [WP]. Quantpedia PEAD and Earnings Announcement Premium pages [Quantpedia] — [link](https://quantpedia.com/strategies/post-earnings-announcement-effect), [link](https://quantpedia.com/strategies/earnings-announcement-premium). A 2025 paper reviving PEAD with long-history earnings patterns reports Sharpe nearly doubling, strongest in large caps [SNIPPET, unnamed].

**Status.** Contested. The classic SUE-decile PEAD is weak-to-absent in large caps post-2006; the *earnings announcement premium* (stocks earn abnormal returns in the announcement month itself) is documented as strong in large caps since 1927 (Quantpedia summary, [SNIPPET]) but is a hold-through-event exposure, not a drift.

**Free-data feasibility.** yfinance exposes upcoming earnings dates and recent EPS surprises, but historical consensus estimates are not reliably available for free, so a proper SUE backtest is not possible. A free proxy: earnings-day abnormal return (gap and close-to-close vs SPY), buy at the close of the reaction day when the abnormal move is in the top decile, hold 5-20 days. Several hobby repos do this (PEAD-Variant, pead-project on GitHub [WEAK]).

**Verdict: SKIP for now** (data quality, single-stock idiosyncratic risk on a $500 book, contested large-cap evidence). Revisit only if a free historical surprise source appears.

---

## 7. Combining sleeves for geometric growth with max DD under ~35%

**Correlation evidence.**
- Crypto trend vs equity trend: about 7.4% average rolling correlation with the SG Trend index over a decade (Man Group [practitioner, SNIPPET]); trend programs generally near-zero correlation to the S&P 500.
- BTC vs S&P spot correlation is regime-dependent and unstable: 30-day correlation reached about 0.87 after the Jan 2024 ETF launches, −0.82 in Jul 2024, and whipsawed between −0.68 and +0.74 in Feb-Mar 2026 [WEAK, Spark/blog snippets]. Do not rely on a fixed number; assume 0.3-0.5 in crises.
- Trend vs mean reversion in the same asset are mutually exclusive by construction (Quantpedia MAX/MIN): combined 10-day MAX+MIN cut BTC max DD from −83.7% to −37.7% while keeping about 98%/yr in-sample.
- Equity mean reversion (IBS/RSI2) is in cash roughly 70-90% of the time and profits from short bursts of panic, which are the same days trend systems give back gains; this is why practitioners pair them (Algomatic Trading note [WEAK]).

**Drawdown budgeting (own arithmetic, not a source).** Separate $500 books cannot cross-fund, so the 35% limit applies per book and to the sum.
- Crypto book: ensemble Donchian with 25% vol target and leverage cap 1 documented at 19% max DD on BTC and 11% on a top-20 rotation (Section 4a). A 2-3 coin rotation without the vol cap should be assumed to reach 30-45% DD in a 2022-type year, which is above budget; the vol target is what makes the budget credible.
- Stock book: IBS/RSI2 above the 200-day MA showed 14-26% max DD over 1993-2026 in the public replications; adding the calendar overlay adds exposure on about 30% of days, so assume 20-30%.
- Sum-of-books: with correlation at most 0.5 in crises and each book capped near 25-30%, combined equity DD should stay under 30%.

**Suggested allocation.** Crypto $500: ensemble Donchian rotation (4a) + 10-day MIN dip rule (3b) sharing the same book with MAX priority. Stock $500: IBS-or-RSI2 mean reversion on QQQ (1a/1b) with a TOM + FOMC + pre-holiday overlay (2a-2c) deploying the idle cash; optional BAA/HAA baseline only if idle time exceeds 60%. Expected geometric growth is dominated by the crypto book in bull regimes; the stock book's role is low-correlation positive carry with shallow drawdowns.

---

## 8. Ranked shortlist: six strategies to backtest, with exact daily-OHLC rule specs

Conventions: daily bars; "close" = regular-session close for ETFs, 00:00 UTC bar for crypto (Yahoo BTC-USD); SMA(n) = simple moving average of closes; RSI(2) = Wilder RSI with period 2; IBS = (C − L)/(H − L), set to 0.5 if H = L. All fills at the close of the signal bar unless stated (paper trader can submit at 15:55 ET for ETFs). Log gross and net at three fee levels for crypto (0.10%, 0.25%, 0.50% per side) and 5 bp per side for ETFs.

### 1. Crypto ensemble-Donchian rotation with 25% vol target (upgrade of the current winner)
- Universe: coins available on the venue with ≥ 1 year of history and 30-day median dollar volume ≥ $2M (recompute monthly, point-in-time). Always include BTC and ETH.
- For each coin and each L in {5, 10, 20, 30, 60, 90, 150, 250, 360}: state_L = 1 if close > max(close over prior L days, excluding today) and the sub-model is not stopped; once long, stop_L = max(stop_L(prev), (highest high over last L days + lowest low over last L days)/2); state_L returns to 0 when close < stop_L; re-entry requires a fresh breakout.
- signal = mean of the nine state_L in {0, 1/9, ..., 1}.
- vol90 = annualised std of the last 90 daily log returns; scale = min(1, 0.25 / vol90).
- Coin score for ranking = signal × (close / SMA(50) − 1) (or simply signal; test both). Hold the top 2 coins by score with signal > 0; weight each = 0.5 × signal × scale of that coin; remainder in cash. Regime gate: total exposure × 1 if BTC close > SMA(100), else × 0.5 (test with and without).
- Rebalance daily at 00:00 UTC only when target weight differs from current by more than 10 percentage points (reduces fee drag).
- Benchmarks: current Donchian-10 top-2; BTC buy-and-hold. Sources: Section 4a.

### 2. QQQ/SPY daily mean reversion: IBS or RSI(2), 200-day gated
- Instruments: QQQ primary, SPY secondary (one position at a time; QQQ has priority when both fire).
- Entry (at close) when close > SMA(200) and (IBS < 0.20 or RSI(2) < 10). Optional stricter: cumulative RSI(2) over 2 days < 35.
- Exit (at close) when IBS > 0.80 or RSI(2) > 65 or close > yesterday's high, whichever first; hard time stop after 7 trading days; no price stop.
- Position: 100% of stock book. No same-day round trips (cash account). Sources: Sections 1a-1b.
- Report: trades/yr, avg %/trade, win rate, max DD, and 2020-2026 sub-period alone.

### 3. BTC/ETH 10-day MIN dip-buy (Quantpedia MIN) with trend gate
- Signal on coin X at 00:00 UTC: close ≤ min(close over prior 10 days) and close > SMA(100) (test 200).
- Entry at the signal close; exit at the close of day 3 after entry, or earlier when close > max(close over prior 10 days) (which hands the position to strategy 1's MAX logic) or when close ≥ entry × 1.05.
- If strategy 1 is already fully long the same coin, do nothing (MAX has priority). Position: up to 50% of the crypto book per coin, max 2 coins.
- Kill criterion: net expectancy < 0 at 0.25%/side over ≥ 60 trades. Sources: Section 3b; ADX > 40 filter from the Glassnode-derived [WEAK] note is optional.

### 4. Stock calendar overlay (TOM + pre-holiday + FOMC) on idle cash
- Applies only when strategy 2 is flat. Instrument: SPY (or QQQ).
- TOM: buy at the close of the 4th-to-last trading day of the month; sell at the close of the 3rd trading day of the next month.
- Pre-holiday: buy at the close two sessions before each NYSE holiday; sell at the close of the last session before the holiday (skip if already long via TOM).
- FOMC: buy at the close of the session before each scheduled decision day; sell at the close of the decision day; if that close is above the entry, hold 5 more sessions (test both).
- Gate: SPY close > SMA(200) (test without). Expected 20-25 round trips/yr, 5 bp/side. Sources: Sections 2a-2c.

### 5. Ensemble-Donchian on BTC and ETH only (no rotation), 25% vol target
- Same sub-models, stops, signal and vol scaling as strategy 1, applied to BTC and ETH with fixed 50/50 split of the book; no universe maintenance, no altcoin liquidity risk.
- Purpose: isolates how much of strategy 1's return comes from altcoin selection versus the ensemble/vol-target mechanics; the paper's BTC-only figures (30% CAGR, 19% max DD net) are the benchmark. Source: Section 4a.

### 6. Keller BAA-G4 monthly rotation as the stock-book baseline (only if 2+4 leave cash idle > 60% of days)
- On the last trading day of each month, using month-end closes: 13612W(x) = (12·r1 + 4·r3 + 2·r6 + r12)/4 with r_k = close_t / close_{t−k months} − 1.
- Canary: if 13612W < 0 for any of SPY, EFA, EEM, AGG → defensive: rank TIP, DBC, BIL, IEF, TLT, LQD, BND by SMA12 = close / mean(last 13 month-end closes) − 1; hold the top 3 equally, replacing any whose SMA12 < BIL's SMA12 with BIL.
- Else offensive: hold the single best of QQQ, EFA, EEM, AGG by SMA12.
- Trades only at month-end; fractional shares. Strategies 2 and 4 then run only on the cash portion, or the baseline is dropped if it crowds them out. Expected 8-12% CAGR, 15-20% max DD net. Source: Section 5.

**Also worth a quick look, not in the six:** crypto IBS variant of strategy 3 (Section 3c); Quantpedia's BTC pre-holiday drift with N-day-high trigger (Section 2b); earnings-day abnormal-return continuation on large caps with 10-day hold (Section 6) if a free surprise source appears.

---

## 9. Gaps and verification still needed

- No full text was readable for the Zarattini et al. paper, the Quantpedia 2024 BTC revisit, Pagonidis 2013, or the Keller papers; the rule specs above follow the standard published descriptions and one fetched transcription, but parameters such as the exact Donchian-midpoint stop and the paper's per-trade fee should be re-checked against the SSRN PDFs when access is available.
- No peer-reviewed post-2020 evidence exists for IBS/RSI(2) decay; the 2024-2025 signals of health are vendor claims (StatOasis, QuantifiedStrategies). The backtests in Section 8 should report 2020-2026 separately for this reason.
- FOMC drift revival rests on one practitioner minute-data study plus a 24-event hobby check; treat the FOMC leg as the weakest part of strategy 4.
- Crypto weekend, IBS and capitulation numbers are all vendor or hobby sources; only the Quantpedia MIN rule has a working-paper-level out-of-sample check.
