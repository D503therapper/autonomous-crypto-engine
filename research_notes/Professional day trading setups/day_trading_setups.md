# Professional / Systematic Day-Trading Setups: Evidence and Implementable Rules (as of 2026-09-25)

Scope: intraday setups for US stocks/ETFs and crypto that could become `analyze()` / `manage()` rules in this engine. It does not repeat `../Fast crypto trading bot plan/`. That folder already covers weekly TSMOM, top gainers, volume spikes, listings, funding signals, and the basic crypto hour-of-day/weekend seasonality, plus retail day-trader outcome statistics (Brazil/Taiwan).

**Source labels:** [PEER] peer-reviewed journal. [WP] working paper / SSRN / arXiv, not peer-reviewed. [VENDOR] written by people who sell trading education, signals or funds on the same idea (a conflict of interest). [REPL] independent replication, usually a GitHub repo or blog by one person. [PRACT] practitioner book or blog, anecdotal. [WEAK] secondary summary or marketing page.

**Method caveat:** Only GitHub was reachable from this sandbox. SSRN, arXiv, Concretum, FINRA and SEC pages were blocked. Numbers come from search-engine extracts of those pages plus GitHub replications. Treat every figure as "reported by", and re-check the PDF before relying on an exact parameter.

---

## 0. Bottom line

1. **Nearly all published intraday edges are a few basis points per trade, gross.** The QQQ 5-minute ORB grosses about $0.07/share, roughly 1.5-2 bp. It breaks even at about 2.2¢/share of slippage [REPL]. A pre-registered 225-cell futures study (2010-2026) found **zero** ORB variants that survive costs [WP]. A 14-family falsification study on MNQ (2021-2025) found no OHLCV intraday signal that clears a 2-point round-trip cost [WP].
2. **The best-documented stock setups come from authors who sell the product.** Zarattini (Concretum Group) and Aziz (Bear Bull Traders) wrote the ORB and noise-area papers. Independent replications of the ORB papers are much weaker: net about zero, or negative out of sample.
3. **Crypto intraday is ruled out at this account's costs.** Config charges 0.4% fee + 0.1% slippage per side, about 1% per round trip. Every crypto intraday effect found is measured in bp per day or per trade. A strategy that trades daily at 1%/round trip pays about 250-365%/yr in costs. Crypto "day-trading" rules only make sense here if they hold for days, which makes them trend following again.
4. **Regulation (§6):** the PDT $25k rule is gone as of 2026-06-04. A $500 account still cannot get margin, because $2,000 is the minimum for a margin account. So it is a **cash, long-only, unlevered** account. The published results rely on 4x leverage and short selling, and neither is available here.
5. **Fit to current data:** Yahoo **1h** bars (730 days of history) already support two of the stock candidates: the noise-area momentum approximation and the last-half-hour momentum trade. The ORB needs 5m bars, and Yahoo keeps only 60 days of those.

### Ranking
**Stocks, implement first:**
1. **SPY/QQQ noise-area intraday momentum** ("Beat the Market"), long-only, on the existing 1h bars. → IMPLEMENT (paper).
2. **Last-half-hour market intraday momentum** (Gao et al.; Baltussen et al.) on SPY. The 15:30-16:00 bar is already in the 1h feed. → IMPLEMENT (cheap), but expect about zero: post-2022 evidence is flat.
3. **5-minute ORB on QQQ** (optionally on "stocks in play"). → TEST only, once 5m data is available. Replications say net ≈ 0.

**Crypto, implement first:**
1. **BTC/ETH "MAX" breakout (close at a 10-day high), with entries/exits checked on 1h bars and multi-day holds** (Padyšák & Vojtko 2022; revisited 2024). → IMPLEMENT (paper). This is trend following, not true day trading.
2. **BTC/ETH intraday noise-area / session momentum on 1h bars** (Shen et al. 2022; Concretum Bitcoin intraday trend work). → TEST only, and only under maker-fee assumptions (≤0.25%/side) with a cap on trade count. At the config's 0.5%/side it is expected to lose.

Everything else below is SKIP: gap fade/continuation, VWAP reversion, overnight hold, crypto hour-of-day seasonality as a standalone, and quarter-hour/funding-time effects.

---

## 1. Opening Range Breakout (ORB)

### 1a. 5-minute ORB on QQQ / TQQQ
**Evidence**
- Zarattini & Aziz, "Can Day Trading Really Be Profitable?", SSRN 4416622 (first posted Apr 2023, revised Apr 2025) [WP][VENDOR]. Sample: QQQ, 2016 to Feb 2023, $25k start, commission only, **no spread or slippage**, no out-of-sample period. Reported results: about 24% hit rate, about +0.13R per trade, and about 33%/yr on QQQ with up to 4x leverage. The TQQQ version is quoted at 1,484% (another variant, using a 5%-of-ATR stop, at 9,350%) against 169% for QQQ buy-and-hold. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622); [CXO summary](https://www.cxoadvisory.com/technical-trading/day-trading-with-an-opening-range-breakout-strategy/); [Semantic Scholar](https://www.semanticscholar.org/paper/Can-Day-Trading-Really-Be-Profitable-Evidence-of-in-Zarattini-Aziz/4d55f526cc56f08662cb8976796cd3b719ef6d2b)
- **Independent replication** (Brusco, GitHub) [REPL]: 1,775 trades against the paper's 1,795.

  | Scenario | Sharpe | CAGR | MaxDD |
  |---|---|---|---|
  | No slippage | 1.06 | 30.4% | 22.4% |
  | $0.02/share slippage | 0.23 | 2.7% | 43.9% |

  Gross edge is $0.070/share, and the strategy **breaks even at about 2.2¢/share of slippage** ("the edge lives inside the bid-ask spread"). An NQ pre-market confirmation filter helps (t = 2.05), but 76% of its P&L came from 2022 alone. — [GitHub: zarattini-2023-orb-qqq](https://github.com/giovannibrusco/zarattini-2023-orb-qqq)
- An out-of-sample report on ES futures (Mar-Sep 2026) using the same frozen spec [REPL, WEAK: a GitHub issue] found −0.284R per trade, an 18.6% win rate, and Sharpe −2.2. It was **negative even at zero slippage**. — [GitHub issue #3](https://github.com/giovannibrusco/zarattini-2023-orb-qqq/issues/3)
- Fetna (SSRN 7428398, Sep 2026) [WP] pre-registered 225 ORB variants: 9 futures markets, 1-minute data 2010-2026, several range lengths, anchors and exits. **0 of 225** passed at $25 per round trip. 28 were significantly negative. The 5-minute window was the worst of the four range lengths. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7428398)
- Mesfin (arXiv 2605.04004 / SSRN 6709401) [WP] tested 14 families on MNQ 5m bars from 2021-2025: ORB, gap continuation/fade, Asia-session momentum and others. Maximum gross edge was 0.07-1.5 points per trade, below a 2-point round-trip cost, and none survived walk-forward testing. — [arXiv](https://arxiv.org/abs/2605.04004)

**Rules (as published)**
- Bar: 5m, regular session only. OR = the 09:30-09:35 bar.
- If OR close > OR open, go long at the 09:35 open. If OR close < OR open, go short. If a doji (close = open), no trade.
- Stop: the OR low for longs, the OR high for shorts (1R = entry − OR low). The paper also has variants with a stop at 5-10% of ATR(14).
- Target: 10R, which is rarely hit. Otherwise flat at 16:00.
- Size: shares = min(1% of equity / R, 4x equity / price).
- Costs in the paper: commission only. Model at least 1-2¢/share of slippage.

**Bar size:** 5m (1m preferred for the stop). **Cost sensitivity:** extreme. Break-even is about 2¢/share, and config's 5 bp stock slippage on QQQ (~$1.5+/share at 2026 prices) is about 10x that. **Recommendation: TEST** (forward paper only). Long-only in a cash account removes half the trades.

### 1b. ORB on "Stocks in Play"
**Evidence**
- Zarattini, Barbon & Aziz, "A Profitable Day Trading Strategy For The U.S. Equity Market", SSRN 4729284 / SFI RP 24-98 (Feb 2024) [WP][VENDOR]. Sample: more than 7,000 US stocks, 2016-2023, $25k start, $0.0035/share commission, **no slippage**. Results:
  - Top-20 stocks by relative volume with a 5m OR: about 1,600-1,637% total, 41.6%/yr, Sharpe 2.81 (the abstract says 2.4), beta ≈ 0, annualized alpha ≈ 36%.
  - The same ORB on **all** stocks: 3.2%/yr, Sharpe 0.48, MDD 13%.

  The paper's central claim is that the "stocks in play" filter matters more than the breakout itself. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284); [SFI](https://www.sfi.ch/en/publications/n-24-98-a-profitable-day-trading-strategy-for-the-u.s.-equity-market); [Concretum](https://concretumgroup.com/a-profitable-day-trading-strategy-for-the-u-s-equity-market/)
- QuantConnect's own replication covers **2016 only** (Sharpe 2.4) [REPL, WEAK]. A port of it by a GitHub user [REPL, WEAK] got:
  - DEV (2016-2019): Sharpe 0.17, CAGR 4.1%, with fees of about 32% of starting capital.
  - OOS (2020-2023): Sharpe −0.47, −5.2%, MDD 24.6%. Verdict: no edge after costs.

  Community comments on QC report a 17% win rate and costs of about 25% of P&L. — [QC research 18444](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/); [GitHub PR](https://github.com/jsboige/CoursIA/pull/16960); [GitHub issue](https://github.com/jsboige/CoursIA/issues/16355)

**Rules (as published)**
- Universe:
  - Open > $5.
  - 14-day average volume ≥ 1M shares.
  - ATR(14) > $0.50.
- Relative volume RV = volume of the first 5m bar ÷ average first-5m-bar volume over the prior 14 days. Require RV > 1 (100%) and keep the top 20 by RV.
- Direction comes from the first 5m candle: bullish means a buy-stop at the OR high, bearish means a sell-stop at the OR low, doji means skip.
- Stop = 10% of ATR(14) from entry. Risk 1% of equity per trade, 4x leverage cap. Flat at the close.
- Variants tested: 5/15/30/60-minute OR. 5 minutes was best in the paper.

**Bar size:** 5m for the whole universe, at the open. That means about 7,000 symbols' first-bar volume by 09:35, which Yahoo cannot deliver in time. **Cost sensitivity:** very high. Stops at 10% of ATR sit inside the noise, so the win rate is low (~17-25%) and slippage on stop fills dominates. **Recommendation: SKIP** for now. Keep the idea of **relative-volume filtering** (§5) as a filter, not as this strategy.

---

## 2. Market intraday momentum (SPY)

### 2a. First half-hour / rest-of-day → last half-hour (Gao et al.; Baltussen et al.)
**Evidence**
- Gao, Han, Li & Zhou, "Market Intraday Momentum", *JFE* 129(2) 2018 [PEER]. Sample: SPY 1993-2013.
  - The first half-hour return, measured from the prior close to 10:00, predicts the last half-hour return (15:30-16:00) with R² ≈ 1.6%.
  - The effect is stronger on volatile days, high-volume days, recession days and macro-news days.
  - A timing strategy (long/short over the last 30 minutes by the sign of the first half-hour) earns about 6.67%/yr against 6.04% buy-and-hold, with far lower volatility.
  - The cost-adjusted figures quoted in summaries are about 6.5% (versus 8.0% gross) for one variant and about 4.3% for another. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351); [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866)
- Baltussen, Da, Lammers & Martens, "Hedging demand and market intraday momentum", *JFE* 142(1) 2021 [PEER]. Sample: 60+ futures, 1974-2020.
  - The return from the previous close to 15:30 predicts the **last 30 minutes** in every asset class.
  - The mechanism is gamma hedging by option dealers and leveraged-ETF rebalancing.
  - The move reverts over the following days. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365); [PDF](https://www3.nd.edu/~zda/intramom.pdf)
- Li, Sakkas & Urquhart, *J. Financial Markets* 57 (2022) [PEER]: intraday TSMOM holds in and out of sample in most of 16 developed markets, and is stronger when liquidity is low and volatility high. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S138641812100001X)
- **Decay:** a practitioner measurement on 1,085 SPX sessions (Apr 2022 to Aug 2026, the 0DTE era) [REPL, WEAK] found the strategy "flat overall and flat in every single year". Another replication notes the overnight-return predictor loses its power out of sample. — [dev.to/firmtape](https://dev.to/firmtape/intraday-momentum-is-dead-in-the-0dte-era-we-measured-it-on-1085-spx-sessions-43g0); [QuantSeeker](https://www.quantseeker.com/p/revisiting-intraday-momentum)

**Rules (implementable, long-only)**
- Signal at 15:30 ET: r = close(15:30) / prior close − 1. This is the Baltussen version. A Gao-style variant uses r1 = price(10:00) / prior close − 1, which needs a 30m bar.
- If r > 0, and optionally |r| > 0.5 × its 20-day average absolute value to drop the smallest signals, buy SPY at 15:30 and sell at 16:00 (the close).
- Long-only cash account: skip days with r < 0.
- Optional filter: trade only when the prior 20-day realized volatility is above its 1-year median, since the effect is stronger on volatile days.
- Size: 100% of settled cash. One round trip per day, so no settlement problem.
- **Engine fit:** Yahoo's regular-session 60m bars run 09:30, 10:30, …, 14:30, 15:30. The last bar is the **15:30-16:00 half hour**, which is why `bars_per_day = 7`. So `analyze()` on the 14:30 bar (closing 15:30) produces the signal, and `manage()` exits on the 15:30 bar. Check the bar alignment on real data first.

**Bar size:** 1h is enough (the 30m version needs 30m bars). **Cost sensitivity:** high. The average last-half-hour move is a few bp. At config's 5 bp per side the strategy cannot be profitable, so set SPY slippage to about 1 bp to test, and stress-test at 2-3 bp. **Recommendation: IMPLEMENT** (cheap, and data already exists) as a live paper experiment. Recent evidence says the edge may be gone.

### 2b. Noise-area intraday momentum ("Beat the Market", Concretum Bands)
**Evidence**
- Zarattini, Aziz & Barbon, "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", SSRN 4824172 / SFI RP 24-97 (May 2024) [WP][VENDOR]. Sample: SPY 2007 to early 2024, 1-minute data. Reported results: **1,985% total net of costs, 19.6%/yr, Sharpe 1.33**, with leverage of up to 4x. Costs: $0.0035/share commission (IBKR) plus a small per-share slippage, reportedly $0.001. — [SSRN](https://ssrn.com/abstract=4824172); [SFI](https://www.sfi.ch/en/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy); [CXO](https://www.cxoadvisory.com/momentum-investing/complex-intraday-time-series-momentum-strategy-applied-to-spy/)
- Concretum's own follow-up [VENDOR]: the short leg pays even in bull markets, and VIX/SMA filters on shorts reduce total profit. — [Concretum: Conditional Profitability of Intraday Shorts](https://concretumgroup.com/conditional-profitability-of-intraday-shorts/)
- Maróy (SSRN 5095349, Jan 2025) [WP] optimizes the parameters and exits (VWAP, Ladder) and reports Sharpe > 3 and > 50%/yr, mostly on QQQ. The optimization is heavy, so this is **likely overfit**. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5095349)
- Quantitativo applies the same idea to NQ futures [PRACT]: 24.3%/yr vs 17.6%, Sharpe 1.67 vs 0.93, MDD 24% vs 35%. Per trade: **+6 bp expectancy**, 38% win rate, payoff ratio 2.25. — [Quantitativo](https://www.quantitativo.com/p/intraday-momentum-for-es-and-nq)
- A long-only replication with next-minute fills and no look-ahead, 2016 to Sep 2026 including 590 sessions after publication [REPL, WEAK: a GitHub PR with terse stats], reports a small positive daily return in both windows, larger since May 2024 (0.052 vs 0.036 "points"/day). It tested costs of $0.0045-0.01/share and gave an "ACCEPT" verdict. — [GitHub SwingDesk PR #207](https://github.com/golub-kirill/SwingDesk/pull/207)
- The replications on critical analyst blogs call the paper's results "a bit too good to be true" [WEAK]. — [quantmacro](https://quantmacro.substack.com/p/paper-review-an-effective-intraday)

**Rules (as published, then an hourly adaptation)**
- For each time-of-day t: σ_t = mean over the previous 14 sessions of |Close(d, t) / Open(d) − 1|. Exclude today.
- UB_t = max(Open_today, PrevClose) × (1 + VM·σ_t). LB_t = min(Open_today, PrevClose) × (1 − VM·σ_t). VM = 1.
- The paper evaluates only at HH:00 and HH:30, from 10:00 to 15:30:
  - Long if price > UB_t.
  - Short if price < LB_t. Omit shorts in a cash account.
- Trailing stop, checked at the same marks:
  - A long exits if price < max(UB_t, session VWAP).
  - A short exits if price > min(LB_t, VWAP).
- Flat at 16:00.
- Size: shares = equity × min(4, 0.02 / σ_SPY,daily,14d) / Open. Long-only cash means capping at 1x.
- **Hourly adaptation for this engine:** evaluate at each 1h bar close (10:30, 11:30, …, 15:30), with σ_t per bar index over 14 days. Approximate VWAP from hourly bars as Σ(typical price × volume) / Σ volume, where typical price = (h + l + c) / 3. The exit goes into `manage()`, plus a forced exit on the last bar of the day. The paper itself shows hourly checking still works, though with a smaller edge than half-hourly.
- Instruments: SPY and QQQ (QQQ was better in the follow-ups). A cash account can hold only one position at a time on full capital.

**Bar size:** 1m in the paper, 30m is acceptable, and 1h is an approximation that is testable on 730 days of Yahoo data. **Cost sensitivity:** high. The edge is roughly 5-10 bp per trade unlevered, so it is about **break-even at config's 5 bp/side**. Model SPY/QQQ at about 1 bp slippage plus $0 commission, and report 1/2/5 bp stress results. **Recommendation: IMPLEMENT** (paper). It is the best-supported stock intraday setup that fits the existing data. Expect the long-only, 1x, hourly version to earn a fraction of the published 19.6% (the paper's number uses up to 4x leverage and includes shorts).

---

## 3. Gaps, VWAP reversion, end-of-day, overnight decomposition

| Setup | Net-of-cost evidence | Verdict |
|---|---|---|
| **Gap fade / gap fill (SPY)** | Mostly vendor statistics: "70-80% of common gaps fill", news gaps fill only 20-30% [WEAK]. Academic studies find gap strategies fail to beat the market after costs. The MNQ falsification study [WP] tested gap continuation and fade: neither survived, and gap-continuation short failed in 2024 OOS. — [QuantifiedStrategies](https://www.quantifiedstrategies.com/gap-fill-trading-strategies/) [WEAK]; [MDPI weekend gaps](https://www.mdpi.com/1911-8074/18/3/132); [arXiv 2605.04004](https://arxiv.org/abs/2605.04004) | SKIP |
| **VWAP mean reversion** | No peer-reviewed or net-of-cost evidence found. Vendor backtests are gross, with explicit notes that costs would sink them [WEAK]. It is also the mirror image of 2b, which uses VWAP as a *trend* stop. — [QuantifiedStrategies VWAP](https://www.quantifiedstrategies.com/vwap-trading-strategy/) [WEAK] | SKIP (use VWAP only as a stop/filter) |
| **End-of-day / last 30 min** | See 2a. Documented [PEER] but decaying [REPL]. | Covered by 2a |
| **Same half-hour periodicity** (Heston, Korajczyk & Sadka, *JF* 2010) [PEER] | Returns in the same half-hour continue for up to 40 days, cross-sectionally. The effect is a few bp and mainly useful for **timing execution** to save about one effective spread. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1107590) | SKIP as a strategy |
| **Overnight vs intraday split** | Lou, Polk & Skouras (*JFE* 2019) [PEER]: momentum profits are earned overnight and reversal profits intraday, a "tug of war". Index overnight returns exceed intraday returns, but at 1-2 bp per execution the costs (~5-10%/yr) consume the ~9%/yr overnight premium [WEAK, Alpha Architect summary]. — [LSE PDF](https://personal.lse.ac.uk/polk/research/TugOfWar.pdf); [Alpha Architect](https://alphaarchitect.com/trading-costs-wipe-out-the-overnight-return-anomaly/) | SKIP (buy close / sell open) |
| **Overnight drift (02:00-03:00 ET, European open)** | Boyarchenko, Larsen & Whelan (*RFS* 2023) [PEER]: 1998-2019 ES futures earned about 3.6%/yr in that one hour. **NY Fed follow-up (Jul 2026): it has averaged ≈ 0 since 2021.** It also needs futures, which this account cannot trade. — [RFS](https://academic.oup.com/rfs/article-abstract/36/9/3502/7076616); [Liberty Street 2026](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/) | SKIP |

---

## 4. Crypto intraday

The prior notes already cover crypto hour-of-day effects, the "Monday Asia Open" effect, weekend flips and funding-as-signal. Only the new or rule-level material is here.

### 4a. BTC intraday session momentum (first half-hour → last half-hour)
- Shen, Urquhart & Wang, "Bitcoin intraday time series momentum", *Financial Review* 57(2) 2022 [PEER]. Sample: BTC 2013-2020.
  - The "day" is defined by volume, because BTC has no open or close. The first half-hour predicts the last half-hour (pooled β ≈ 0.97, NW t = 4.4, R² ≈ 1.4%).
  - The effect is strongest in high-volume and high-volatility sessions and in downturns.
  - It is driven by liquidity provision.
  - It is "positive after fees, especially for leveraged investors", with fee levels far below 0.5%/side. — [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/fire.12290); [Reading accepted version](https://centaur.reading.ac.uk/100181/)
- Wen, Bouri, Xu & Zhao, *NAJEF* 62 (2022) [PEER]: BTC 2013-2020 shows both momentum and reversal. The pattern changes around jumps, FOMC and COVID, and is also present in ETH, LTC and XRP. Economic value is measured against always-long. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1062940822000833)
- Concretum "Seasonality in Bitcoin Intraday Trend Trading" [VENDOR]: an ensemble of high-frequency, volatility-targeted long-short trend models over 2018-2025. **Gross** Sharpe ≈ 1.6, with most of it on Sunday evening NY time into Monday. — [Concretum substack](https://concretumgroup.substack.com/p/bitcoin-trends-around-the-clock)
- **Rules to test (1h bars):**
  - Treat 00:00 UTC as the session open. σ_h = 14-day mean of |close_h / open_00UTC − 1| for each hour h.
  - At each hourly close, go long if price > open × (1 + σ_h) and price > session VWAP. Exit on the VWAP/UB trailing stop or at 23:00 UTC.
  - Entries only in the high-volume window, 13:00-21:00 UTC (US hours).
  - Cap at 1 trade/day/coin, BTC and ETH only.
- **Cost sensitivity:** fatal at config's 0.5%/side. The per-trade edge is tens of bp at best. **Recommendation: TEST** only in a parallel account with fees set to maker 0.25% (or 0.1% as an "if we move venue" scenario). Do not run it live at app spreads.

### 4b. BTC "MAX" trend (price at a 10-day high) and hour-of-day hold
- Padyšák & Vojtko, "Seasonality, Trend-following, and Mean reversion in Bitcoin" (SSRN 4081000, 2022) [WP][VENDOR: Quantpedia]. Sample: Gemini hourly data, Oct 2015 to Feb 2022.
  - BTC keeps trending when it closes at an x-day **maximum** and bounces at a minimum. The 10-day lookback was best.
  - Holding BTC only from 21:00/22:00 to 23:00/00:00 UTC returned about 33%/yr, with 20.9% volatility and a −22% MDD. This is gross, and 2022-23 was rough.
- Beluská & Vojtko (SSRN 4955617, Oct 2024) [WP][VENDOR] re-tested with data to Aug 2024: MAX "remains alive" out of sample, and MIN+MAX combined beat buy-and-hold with smaller drawdowns. — [SSRN 4081000](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4081000); [SSRN 4955617](https://papers.ssrn.com/sol3/Delivery.cfm/4955617.pdf?abstractid=4955617&mirid=1); [Quantpedia](https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin/); [code for the 22-00 UTC hold](https://github.com/paperswithbacktest/awesome-systematic-trading/blob/main/static/strategies/intraday-seasonality-in-bitcoin.py)
- Supporting evidence on daily bars: Zarattini, Pagani & Barbon, "Catching Crypto Trends" (SSRN 5209907, 2025) [WP][VENDOR]. An ensemble of Donchian channels with volatility sizing on a top-20 rotation, Jan 2015 to Mar 2025, reports Sharpe about 1.5-1.6 and CAGR about 30% **net of 0.10-0.50% fees**. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5209907)
- **Rules (MAX):**
  - Once per day at 00:00 UTC, if BTC (or ETH) daily close ≥ max(close of the prior 10 days), buy (or hold).
  - Exit when the daily close falls below the 10-day max, or better, below the 10-day low (Donchian) or an ATR trail checked on 1h bars. Verify the paper's exact exit, which may be "hold 1 day and re-evaluate".
  - Optional ensemble: signals at lookbacks 10/20/40/80, with position = the fraction of lookbacks that are long.
  - Optional timing: place entries around 21:00-00:00 UTC instead of at a random hour.
- **Bar size:** daily signal, 1h for stops and fill timing. **Cost sensitivity:** moderate. Trades number in the tens per year, so the ~1% round trip is survivable. **Recommendation: IMPLEMENT.** This is a crypto "fast" strategy with net-of-fee evidence, though it is really trend following. It overlaps with the existing `TrendFollower` and `WeeklyMomentum`, so check the correlation before adding capital.
- The **hour-of-day hold by itself** (365 round trips a year) is **SKIP**: about 365%/yr in costs at config fees.

### 4c. Funding-time / quarter-hour effects
- Kim & Hansen, "The Quarter-Hour Effect" (arXiv 2607.09426, Jul 2026) [WP]. Binance perpetuals show volume and volatility bursts at the 1-, 5- and 15-minute marks. Quarter-hour opening returns are forecastable out of sample (R² 3.4%, AUC 0.60) over horizons of **seconds**. The pattern is unchanged when the funding settlements at 00/08/16 UTC are excluded, so it is **not** a funding effect. Order imbalance weakly predicts returns 4-12 hours ahead. — [arXiv](https://arxiv.org/abs/2607.09426)
- **Recommendation: SKIP.** It is HFT-scale, perp-only, and cannot be captured with 1h spot bars. At most, avoid placing market orders in the first seconds after :00, :15, :30 and :45.

---

## 5. What professional / prop day traders emphasize (operational rules)

These are practitioner sources [PRACT][VENDOR], with no controlled evidence that they create edge. They are mainly risk hygiene, and they are cheap to encode.

- **Trade only "stocks in play"**: stocks with fresh news, a large gap, and pre-market or early relative volume well above normal. This is Bear Bull Traders (Aziz, *How to Day Trade for a Living*) and SMB Capital (Bellafiore, *One Good Trade* ch. 7 "Stocks in Play", *The PlayBook*). Zarattini et al. is the only quantitative support: "all stocks" gave Sharpe 0.48, the top-20 by RV gave 2.4-2.8 gross, and replications could not reproduce it net. — [Wiley: One Good Trade ch.7](https://onlinelibrary.wiley.com/doi/abs/10.1002/9781119203063.ch7); [TraderLion summary of Aziz](https://traderlion.com/trading-books/how-to-day-trade-for-a-living/) [WEAK]
  - Engine rule: RV = today's cumulative volume up to bar k ÷ 14-day average cumulative volume up to bar k. Trade a stock or ETF intraday only if RV ≥ 1.5-2. For SPY/QQQ this is a regime filter ("active day").
- **Size by volatility/ATR, with fixed fractional risk:**
  - Aziz: risk ≤ 2% of the account per trade, target ≥ 2:1 reward-to-risk.
  - The papers: 1% risk with stop distance from ATR(14), or a 2% daily volatility target.
  - Engine rule: qty = min(risk% × equity / stop distance, cash / price).
- **Max daily loss / "three strikes":**
  - Stop trading for the day after about 2-3R lost or 3 losing trades.
  - Some coaches cut size 25% and then 50% after the first and second loss [WEAK].
  - Prop firms enforce hard daily loss limits.

  Engine rule: a per-strategy per-day loss counter in `Portfolio`, sitting next to the existing drawdown breaker.
- **Trade the first and last hour:**
  - The open is where the ORB and stocks-in-play volume happens.
  - The last 30 minutes is where gamma and leveraged-ETF flows drive momentum (Baltussen et al. [PEER]).
  - Volume is U-shaped, and midday is the chop the noise-area band is designed to filter.

  Engine rule: new entries only from 09:30 to 11:30 and from 15:00 to 16:00 ET, except for 2b, which uses its own band.
- **Avoid overtrading:** at most 1-2 trades per instrument per day. Costs, not signals, sank every replication above. Retail day-trader outcome data is already in the prior notes (97% of Brazilian persistent day traders lost money; fewer than 1% of Taiwanese day traders were reliably profitable).

---

## 6. Pattern Day Trader rule and the $500 account (status 2026-09-25)

- **The PDT rule is abolished.** The SEC approved the FINRA Rule 4210 amendments (SR-FINRA-2025-017) on **2026-04-14**. FINRA Regulatory Notice 26-10 set the **effective date at 2026-06-04**.
  - The "pattern day trader" designation, the 4-day-trades-in-5-days count, and the **$25,000 minimum** are gone.
  - They are replaced by an **intraday margin standard**: brokers monitor real-time intraday margin excess and either block trades that would create a deficit or issue an end-of-day margin call.
  - Firms may phase this in over 18 months, until **2027-10-20**.
  - Webull, Robinhood, Fidelity, tastytrade, Lightspeed and Cobra went live on 2026-06-04, Schwab on 06-08, and E*TRADE on 06-09 [WEAK: blog aggregations].
  - Sources: [FINRA RN 26-10](https://www.finra.org/rules-guidance/notices/26-10); [SEC approval order 34-105226](https://www.sec.gov/files/rules/sro/finra/2026/34-105226.pdf); [WilmerHale](https://www.wilmerhale.com/en/insights/client-alerts/20260423-sec-approves-amendments-to-finra-rule-4210-replacing-day-trading-margin-requirements-with-a-modernized-intraday-margin-standard); [E*TRADE](https://us.etrade.com/knowledge/library/margin/pattern-day-trading-rule-change); [FINRA investor insight](https://www.finra.org/investors/insights/intraday-margin-requirements); [tastytrade](https://support.tastytrade.com/support/s/solutions/articles/43000435180)
- **Margin accounts still need $2,000 minimum equity** (FINRA/Reg T floor), and brokers may set higher house minimums. **A $500 account is therefore a cash account.** That means:
  - No leverage. Every published result above used up to 4x.
  - **No short selling**, which removes about half the ORB and noise-area trades.
  - Unlimited day trades **only with settled cash**. Under **T+1** settlement, sale proceeds settle the next business day.
  - Buying with unsettled proceeds and then selling before they settle is a **good-faith violation**. Repeated violations get the account restricted to settled-cash-only for 90 days. Free-riding rules still apply. — [QuantInsti](https://www.quantinsti.com/articles/finra-pdt-rule-removal-2026/) [WEAK]; [Britannica](https://www.britannica.com/money/pattern-day-trader-rule)
- **Practical rule for the engine's stock accounts:** at most **one full-capital round trip per day**, or split cash into N sleeves with one round trip per sleeve per day. Model long-only at 1x. Crypto has no PDT or settlement constraint.

---

## 7. Data needs and feasibility

| Strategy | Minimum bar | Source today | Backtest depth |
|---|---|---|---|
| 2a Last-half-hour momentum | 1h (30m better) | Yahoo 1h ✓ | ~730 days |
| 2b Noise-area momentum | 1h approximation (30m/1m in paper) | Yahoo 1h ✓ | ~730 days (1h); 60 days (5m/30m) |
| 1a QQQ 5m ORB | 5m (1m for stops) | Yahoo 5m, **60 days only** | Forward paper only, unless another source is added |
| 1b Stocks-in-play ORB | 5m for ~thousands of symbols at 09:35 | Not feasible on Yahoo | — |
| 4a BTC intraday momentum | 1h (30m in paper) | Crypto.com 1h ✓ | Limited by API paging |
| 4b BTC MAX / Donchian | 1D signal, 1h execution | Crypto.com ✓ | Long |

- **Yahoo Finance (yfinance) limits:**
  - 1m: last ~7 days per request (~30 days total, fetched in 7-day chunks).
  - 2m/5m/15m/30m/90m: last **60 days**.
  - 60m/1h: ~**730 days**.

  Could not be re-verified live, because Yahoo is blocked from this sandbox. — [yfinance docs](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html); [IBKR Campus guide](https://www.interactivebrokers.com/campus/ibkr-quant-news/yfinance-library-a-complete-guide/); [yfinance issue #2451](https://github.com/ranaroussi/yfinance/issues/2451)
- **Crypto.com Exchange `public/get-candlestick`:** supports 1m, 5m, 15m, 30m, 1h, 4h, 12h and 1D. The engine's `TF_MS` already maps 1m-1D. There is a 300-candle cap per call, and `CryptoComClient.candles` already pages backwards. How far back 1m/5m history goes is **unverified**: the docs were blocked and a live curl got a 403 from the sandbox proxy. For deep crypto intraday backtests, Kraken publishes downloadable OHLCVT history. — [Crypto.com API docs](https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html); [CCXT cryptocom](https://docs.ccxt.com/docs/exchanges/cryptocom); [Kraken OHLCVT](https://support.kraken.com/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data)
- **Free deeper US intraday history:** Alpaca's data API has minute bars back to 2016 on the free plan. SIP data is available only if older than 15 minutes, which is fine for backtests. This is the easiest way to backtest 1a or a 30m version of 2b. — [Alpaca FAQ](https://docs.alpaca.markets/us/docs/market-data-faq); [Alpaca data timeline](https://alpaca.markets/support/alpaca-data-timeline)
- **Backtest implications:**
  - With 60 days of 5m data (about 40 sessions), a ~+0.1R/trade edge is impossible to distinguish from noise. See the t-stat table in `risk_sizing_outcomes.md`, which requires hundreds of trades.
  - Intraday strategies need **time-of-day-aware bars**: the `t` field in ET for stocks, UTC for crypto, plus a forced end-of-day exit in `manage()`.
  - Fills should be at the **next bar's open**, not the signal bar's close, to avoid look-ahead. The SwingDesk replication stresses this.
  - Cost settings matter more than rules. Current config is `STOCK_SLIPPAGE_RATE = 0.0005` (5 bp/side) and `FEE_RATE + SLIPPAGE_RATE = 0.5%/side` for crypto. Run SPY/QQQ at 1, 2 and 5 bp, and crypto at 0.1%, 0.25% and 0.5%/side, and report all of them.

---

## 8. Strategy cards (summary)

| # | Strategy | Evidence quality | Bar | Cost sensitivity | Verdict |
|---|---|---|---|---|---|
| S1 | SPY/QQQ noise-area momentum (long-only, 1h adaptation) | WP+VENDOR; 1 weak positive post-publication replication | 1h (30m better) | High (~5-10 bp/trade edge) | **IMPLEMENT (stocks #1)** |
| S2 | Last-half-hour momentum on SPY (Baltussen/Gao) | PEER ×3; decayed after 2022 [REPL] | 1h (last bar = 15:30-16:00) | High (few bp) | **IMPLEMENT (stocks #2)**, low expectations |
| S3 | QQQ 5m ORB | WP+VENDOR; replications: net ≈ 0 at 2¢, negative on ES 2026, 0/225 in pre-registered study | 5m | Extreme | **TEST (stocks #3)**, forward paper only |
| S4 | Stocks-in-play ORB | WP+VENDOR; OOS replication Sharpe −0.47 | 5m, whole market | Extreme | SKIP (keep the RV filter idea) |
| S5 | Gap fade / continuation | WEAK / falsified | 5m | High | SKIP |
| S6 | VWAP reversion | WEAK, gross only | 5m | High | SKIP |
| S7 | Overnight hold / overnight drift | PEER, but costs ≈ premium; drift ≈ 0 since 2021 | 1D / futures | High | SKIP |
| C1 | BTC/ETH 10-day-MAX / Donchian ensemble, 1h execution | WP+VENDOR, OOS to 2024; net-of-fee support from daily Donchian ensemble | 1D signal / 1h stops | Moderate (low turnover) | **IMPLEMENT (crypto #1)** |
| C2 | BTC/ETH intraday noise-area / session momentum | PEER (in-sample to 2020) + VENDOR (gross) | 1h | Fatal at 0.5%/side | **TEST (crypto #2)** at maker/low-fee assumptions only |
| C3 | BTC hour-of-day hold (22-00 UTC) | WP+VENDOR, gross | 1h | Fatal (daily round trip) | SKIP (use as entry-timing filter only) |
| C4 | Quarter-hour / funding-time effects | WP, seconds horizon | Tick/1s | n/a | SKIP |

### Engine notes (no code changed)
- The engine is long-only (`Portfolio.buy/sell`), so every rule above is written long-only.
- Intraday strategies need:
  1. A time-of-day helper that turns `t` into ET for stocks and UTC for crypto.
  2. A `manage()` exit on the last bar of the session (`"session close"`).
  3. Per-day state: σ-by-bar-index over 14 days, a cumulative VWAP, and a trades-today counter.
  4. A daily loss stop.
- `analyze()` already receives the whole candle window, so σ_t can be computed there from the last 14 × `bars_per_day` bars.
- `window` must be at least 15 × `bars_per_day` + 1 (≥106 for stocks, ≥361 for crypto hourly).
