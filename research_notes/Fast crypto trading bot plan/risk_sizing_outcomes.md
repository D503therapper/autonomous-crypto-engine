# Position Sizing, Risk of Ruin, Compounding Math, and Real-World Trader Outcomes (for a $500 automated crypto bot)

Context: automated crypto bot, $500 start, owner wants fast growth over 30-day cycles, monthly profit sweeps, scaling capital over time. All simulation code and full output are in the appendix section at the end of the last key question (they were run 2026-09-25 with numpy, 100,000 Monte Carlo paths per cell unless stated).

**Simulation model used throughout (state these assumptions when using the numbers):**
- Each trade risks a fixed fraction f of *current* equity (fixed-fractional compounding). Loss = -1R, win = +bR.
- Trades are independent (IID). Real crypto trades are **not** independent: alts move together, so losses cluster. That makes every drawdown number below **optimistic**.
- Costs: 0.10% taker fee per side + 0.05% slippage per side = 0.30% round trip on notional. With a 2% stop distance, notional = f x equity / 0.02, so cost per trade = 0.30%/2% = **0.15R** (win becomes +(b-0.15)R, loss becomes -1.15R). Tighter stops make costs bigger in R terms: a 1% stop means 0.30R per trade.
- No gap-through-stop slippage, no exchange outage, no funding costs. Real outcomes will be worse.
- Strategies: A = 45% win rate, 2.0 payoff ("good breakout"); B = 40%/2.0 ("marginal breakout"); C = 55%/1.5 ("high hit rate"); D = 33.3%/2.0 (zero edge before costs).

---

## 1. Kelly criterion and fractional Kelly: formulas, growth vs. drawdown, overbetting, estimation error

### Takeaway
For breakout-style edges (40-55% win rate, 1.5-2.5 payoff), full Kelly after realistic costs is only about 2-15% of equity risked per trade, and it is very sensitive to the true win rate. Betting 2x Kelly brings growth to about zero; above that, wealth shrinks. Because the true edge is never known, practitioners use half or quarter Kelly: half Kelly keeps about 75% of the growth rate and cuts the chance of a 50% drawdown from 50% to 12.5%.

### Cited Findings
- Kelly maximizes E[log wealth], which maximizes the long-run exponential growth rate of capital (for IID bets, no transaction costs); it also maximizes the expected probability of reaching a target wealth. — [MacLean, Thorp, Ziemba, "Good and bad properties of the Kelly criterion" (via World Scientific / ResearchGate)](https://www.researchgate.net/publication/227623956_Long-term_capital_growth_the_good_and_bad_properties_of_the_Kelly_and_fractional_Kelly_capital_growth_criteria)
- Main drawback: Kelly bets are very large because its Arrow-Pratt risk aversion is low, so Kelly is "relatively risky in the short term". Even after a long run of favorable bets, bad sequences can lose most of the wealth. Fractional Kelly (mixing the Kelly bet with cash) gives more safety in exchange for lower expected final wealth. — [MacLean, Thorp, Ziemba (ResearchGate)](https://www.researchgate.net/publication/227623956_Long-term_capital_growth_the_good_and_bad_properties_of_the_Kelly_and_fractional_Kelly_capital_growth_criteria); [Ziemba, "Using the Kelly criterion for investing" (chapter PDF)](https://webhomes.maths.ed.ac.uk/mckinnon/blackouts/StochOptFinanceAndEnergySpringer/Chap1_KellyZiemba.pdf)
- Formulas (standard; see Ziemba chapter above):
  - Binary bet, win +W per unit risked with probability p, lose L per unit with probability q=1-p: growth per trade g(f) = p·ln(1+fW) + q·ln(1−fL); Kelly fraction **f\* = (pW − qL)/(WL)**. With L=1 this is the familiar **f\* = p − q/b**.
  - Continuous (GBM) approximation: f\* = μ/σ², maximum growth g\* = μ²/(2σ²) = SR²/2. Betting a fraction c of Kelly gives growth **c(2−c)·g\***. So half Kelly gets 75% of max growth, and 2x Kelly gets zero growth.
  - Drawdown under fraction c of Kelly (continuous approximation): P(wealth ever falls to x of its start) = **x^(2/c − 1)**. At full Kelly, P(ever halving) = 50% and P(ever losing 90%) = 10%.

**Kelly fractions for the example strategies (from simulation script, costs = 0.15R/trade):**

| strategy | gross EV (R) | net EV (R) after c=0.15R | full Kelly gross | full Kelly net | half Kelly net | quarter Kelly net | max log-growth/trade net |
|---|---|---|---|---|---|---|---|
| A: p=0.45, b=2.0 (good breakout) | +0.350 | +0.200 | 17.5% | 9.4% | 4.7% | 2.4% | 0.923% |
| B: p=0.40, b=2.0 (marginal breakout) | +0.200 | +0.050 | 10.0% | 2.4% | 1.2% | 0.6% | 0.058% |
| C: p=0.55, b=1.5 (high-hit-rate) | +0.375 | +0.225 | 25.0% | 14.5% | 7.2% | 3.6% | 1.624% |
| D: p=0.33, b=2.0 (no edge before costs) | -0.000 | -0.150 | n/a | n/a (negative: do not trade) | | | |

**Overbetting (strategy A, net of costs; full Kelly = 9.4%):**

| multiple of Kelly | risk/trade | expected log growth/trade | growth as % of max | median equity multiple after 100 trades |
|---|---|---|---|---|
| 0.25x | 2.4% | +0.408% | 44% | 1.50x |
| 0.5x | 4.7% | +0.696% | 75% | 2.01x |
| 0.75x | 7.1% | +0.866% | 94% | 2.38x |
| 1.0x | 9.4% | +0.923% | 100% | 2.52x |
| 1.5x | 14.1% | +0.700% | 76% | 2.01x |
| 2.0x | 18.8% | +0.033% | 4% | 1.03x |
| 2.5x | 23.5% | -1.084% | negative | 0.34x |
| 3.0x | 28.2% | -2.669% | negative | 0.07x |

**Theoretical drawdown vs. Kelly fraction (continuous approximation x^(2/c−1)):**

| Kelly fraction c | P(ever down 50%) | P(ever down 80%) | P(ever down 90%) | growth as % of max |
|---|---|---|---|---|
| 0.25 | 0.8% | ~0% | ~0% | 44% |
| 0.5 | 12.5% | 0.8% | 0.1% | 75% |
| 0.75 | 31.5% | 6.8% | 2.2% | 94% |
| 1.0 | 50.0% | 20.0% | 10.0% | 100% |
| 1.5 | 79.4% | 58.5% | 46.4% | 75% |
| 2.0 | 100% | 100% | 100% | 0% |

**Estimation error (sized as if p=0.45, but the true win rate is lower; 150 trades ≈ one aggressive month):**

| true p / sizing | mean x | p5 | median | p95 | P(loss) | P(maxDD≥50%) | P(equity ever ≤20% of start) |
|---|---|---|---|---|---|---|---|
| p=0.45, 1/4 K (2.4%) | 2.02 | 0.88 | 1.78 | 3.59 | 7.0% | 1.3% | 0.0% |
| p=0.45, 1/2 K (4.7%) | 4.06 | 0.76 | 2.65 | 12.22 | 9.5% | 38.5% | 0.3% |
| p=0.45, full K (9.4%) | 16.17 | 0.22 | 3.48 | 71.46 | 20.7% | 97.0% | 11.6% |
| p=0.40, 1/4 K | 1.19 | 0.54 | 1.09 | 2.20 | 40.2% | 12.3% | 0.0% |
| p=0.40, 1/2 K | 1.43 | 0.25 | 1.00 | 4.02 | 46.7% | 73.5% | 5.0% |
| p=0.40, full K | 2.03 | 0.03 | 0.51 | 7.93 | 66.0% | 99.7% | 45.2% |
| p=0.36, 1/4 K | 0.78 | 0.36 | 0.72 | 1.44 | 77.8% | 39.5% | 0.1% |
| p=0.36, 1/2 K | 0.61 | 0.11 | 0.44 | 1.75 | 82.5% | 92.6% | 24.3% |
| p=0.36, full K | 0.37 | 0.01 | 0.10 | 1.53 | 92.4% | 100% | 79.3% |

### Inferences
- Costs roughly halve Kelly for breakout systems. For strategy B, costs take Kelly from 10% gross to 2.4% net, and growth becomes almost nothing (0.058% per trade). Fee and slippage modelling matters more than the choice of Kelly fraction.
- A win-rate error of 5 points (45% believed, 40% true) turns full-Kelly sizing into a median *loss* of 49% in a month. Quarter Kelly under the same error still roughly breaks even. Backtest win rates are almost always overstated (see Q7), so **1/4 Kelly or less of the backtested edge** is the defensible ceiling. For typical breakout parameters that means risking about 1-2.5% of equity per trade.
- Mean and median separate sharply as size grows. At high risk, the *mean* outcome looks spectacular because a few paths explode, while the *typical* (median) outcome is ruin. An owner who looks at the mean or at the best backtest path will pick sizes that are too large.

### Gaps
- Could not fetch the full text of Thorp's or Kelly's (1956) original papers (sources blocked or not fetched). The formulas above are standard results, attributed via the MacLean/Thorp/Ziemba literature.

---

## 2. Risk of ruin and drawdown probabilities for fixed-fractional risk (1%, 2%, 5%, 10%, 25%/"all-in-ish")

### Takeaway
With a real but modest edge, 1-2% risk per trade almost never produces a 50% drawdown in a month. 5% risk produces one 15-43% of the time, 10% risk 78-98% of the time, and 25% risk nearly always. With no edge, higher risk only speeds up ruin. Long losing streaks are certain over a year: at a 45% win rate, a streak of 10 or more losses happens in 88% of 1,800-trade years.

### Cited Findings (own simulation; see appendix for code)
**30 days, 60 trades (2/day), costs 0.15R/trade. Outcome = equity multiple of starting $500.**

Strategy A (p=0.45, b=2):

| risk/trade | mean x | p5 | median | p95 | P(loss) | P(≥2x) | P(maxDD≥20%) | P(maxDD≥50%) | P(ever ≤20% of start) |
|---|---|---|---|---|---|---|---|---|---|
| 1% | 1.13 | 0.94 | 1.12 | 1.34 | 18.2% | 0.0% | 0.9% | 0.0% | 0.0% |
| 2% | 1.27 | 0.87 | 1.24 | 1.77 | 17.9% | 1.4% | 26.0% | 0.0% | 0.0% |
| 5% | 1.81 | 0.64 | 1.54 | 3.75 | 26.0% | 34.5% | 97.2% | 15.2% | 0.0% |
| 10% | 3.29 | 0.30 | 1.74 | 10.00 | 35.2% | 44.5% | 100% | 78.2% | 5.7% |
| 25% | 17.30 | 0.01 | 0.40 | 29.74 | 65.4% | 25.6% | 100% | 100% | 64.8% |

Strategy B (p=0.40, b=2, marginal edge):

| risk/trade | mean x | p5 | median | p95 | P(loss) | P(≥2x) | P(maxDD≥50%) | P(ever ≤20%) |
|---|---|---|---|---|---|---|---|---|
| 1% | 1.03 | 0.86 | 1.02 | 1.22 | 45.1% | 0.0% | 0.0% | 0.0% |
| 2% | 1.06 | 0.72 | 1.03 | 1.48 | 45.1% | 0.1% | 0.1% | 0.0% |
| 5% | 1.17 | 0.41 | 0.99 | 2.40 | 55.3% | 11.9% | 34.8% | 0.3% |
| 10% | 1.35 | 0.13 | 0.72 | 4.17 | 65.6% | 17.9% | 91.4% | 19.3% |
| 25% | 2.13 | 0.00 | 0.05 | 3.44 | 88.2% | 7.4% | 100% | 86.0% |

Strategy D (zero gross edge; costs make it negative):

| risk/trade | mean x | median | P(loss) | P(≥2x) | P(maxDD≥50%) | P(ever ≤20%) |
|---|---|---|---|---|---|---|
| 1% | 0.91 | 0.91 | 83.2% | 0.0% | 0.0% | 0.0% |
| 2% | 0.83 | 0.82 | 83.3% | 0.0% | 2.0% | 0.0% |
| 5% | 0.64 | 0.55 | 89.0% | 1.1% | 71.0% | 4.0% |
| 10% | 0.40 | 0.22 | 93.2% | 2.2% | 98.8% | 56.2% |
| 25% | 0.10 | 0.00 | 98.8% | 0.6% | 100% | 98.1% |

**30 days, 150 trades (5/day), costs 0.15R/trade:**

| strategy / risk | mean x | p5 | median | p95 | P(loss) | P(≥2x) | P(maxDD≥50%) | P(ever ≤20%) |
|---|---|---|---|---|---|---|---|---|
| A 1% | 1.35 | 0.97 | 1.31 | 1.82 | 7.0% | 1.2% | 0.0% | 0.0% |
| A 2% | 1.82 | 0.97 | 1.65 | 3.19 | 7.0% | 31.2% | 0.4% | 0.0% |
| A 5% | 4.43 | 0.73 | 2.75 | 13.97 | 12.5% | 68.6% | 42.9% | 0.4% |
| A 10% | 19.81 | 0.25 | 3.43 | 85.10 | 20.8% | 62.8% | 98.4% | 14.3% |
| A 25% | 811 | 0.00 | 0.07 | 189.67 | 68.9% | 25.6% | 100% | 82.0% |
| B 1% | 1.08 | 0.79 | 1.06 | 1.43 | 40.3% | 0.0% | 0.0% | 0.0% |
| B 2% | 1.16 | 0.60 | 1.09 | 1.98 | 40.3% | 4.1% | 5.4% | 0.0% |
| B 5% | 1.45 | 0.22 | 0.98 | 4.29 | 53.5% | 22.3% | 77.0% | 6.6% |
| B 10% | 2.11 | 0.02 | 0.44 | 8.24 | 66.2% | 18.1% | 99.9% | 50.3% |
| C 2% | 1.96 | 1.11 | 1.92 | 3.01 | 1.6% | 43.4% | 0.0% | 0.0% |
| C 5% | 5.35 | 1.09 | 3.78 | 13.13 | 3.6% | 83.6% | 16.1% | 0.0% |
| C 10% | 28.32 | 0.66 | 7.98 | 96.01 | 7.0% | 83.7% | 89.9% | 3.2% |
| D 1% | 0.80 | 0.60 | 0.79 | 1.06 | 92.8% | 0.0% | 0.7% | 0.0% |
| D 2% | 0.64 | 0.35 | 0.60 | 1.09 | 92.9% | 0.0% | 48.0% | 0.1% |
| D 5% | 0.32 | 0.06 | 0.22 | 0.98 | 96.3% | 0.7% | 98.3% | 54.7% |

**12 months (1,800 trades, no sweeps, 20,000 paths):**

| strategy / risk | median x | p5 | p95 | P(loss) | P(maxDD≥20%) | P(maxDD≥50%) | P(ever ≤20%) |
|---|---|---|---|---|---|---|---|
| A 1% | 29.9 | 10.5 | 85.1 | 0.0% | 64.9% | 0.0% | 0.0% |
| A 2% | 598 | 74 | 4,812 | 0.0% | 100% | 12.4% | 0.0% |
| B 1% | 2.03 | 0.73 | 5.60 | 12.7% | 99.7% | 18.6% | 0.0% |
| B 2% | 2.80 | 0.37 | 21.2 | 19.8% | 100% | 89.7% | 5.2% |
| B 5% | 0.77 | 0.00 | 135.6 | 52.9% | 100% | 100% | 62.5% |

**Losing streaks (P of at least one streak of length ≥k):**

| win rate | trades | ≥5 | ≥8 | ≥10 | ≥12 |
|---|---|---|---|---|---|
| 0.40 | 150 | 99.7% | 64.2% | 29.6% | 11.7% |
| 0.40 | 1800 | 100% | 100% | 98.8% | 79.5% |
| 0.45 | 150 | 97.8% | 43.1% | 15.3% | 4.9% |
| 0.45 | 1800 | 100% | 99.9% | 87.5% | 46.2% |
| 0.55 | 150 | 79.4% | 12.5% | 2.6% | 0.5% |
| 0.55 | 1800 | 100% | 81.0% | 28.6% | 6.3% |

(At 5% risk, 10 straight losses at 1.15R each = 1 − (1−0.0575)^10 ≈ −45%; at 10% risk ≈ −70%.)

### Inferences
- **Treat the A/C numbers as an upper bound, not a forecast.** A +0.20R net edge over 150 trades per month compounds to about 30x per year at only 1% risk. No known fund comes close to that (see Q4), so a backtest showing it is far more likely overfit than real. Plan around B-like edges (small or zero) until live data proves otherwise.
- For B-like edges, raising risk from 2% to 5% *lowers* the median 30-day outcome (1.09x → 0.98x). Aggression only pays when the edge is large and known.
- "All-in"/25% risk: the median outcome is ruin even with a genuine edge (median 0.07x for strategy A at 150 trades). The attractive means come from a few lottery-like paths.
- Correlation: when 5 altcoin breakouts trigger together and fail together, the bot is effectively running one trade at 5x risk. The IID results above understate drawdowns. Cap the *total* open risk across correlated positions, not just the risk per trade.

### Gaps
- These are synthetic IID outcomes. I found no published empirical distribution of monthly returns for retail crypto bots (e.g., 3Commas/Pionex user cohorts) to calibrate against.

---

## 3. Volatility drag, geometric vs. arithmetic returns, loss asymmetry

### Takeaway
Compounding follows the geometric mean ≈ arithmetic mean − σ²/2. At crypto-like volatility, a strategy with a positive average monthly return can still shrink money. Losses are asymmetric: −50% needs +100% to recover, and −90% needs +900%.

### Cited Findings
- The continuous-time growth rate under fractional Kelly is c(2−c)·g\*, and the log-growth approximation g ≈ μ − σ²/2 is standard (Kelly/GBM framework). — [Ziemba chapter](https://webhomes.maths.ed.ac.uk/mckinnon/blackouts/StochOptFinanceAndEnergySpringer/Chap1_KellyZiemba.pdf)
- Own calculation, arithmetic mean +3%/month:

| monthly vol | geometric/month | 12-month median multiple |
|---|---|---|
| 5% | +2.88% | 1.41x |
| 10% | +2.50% | 1.35x |
| 20% | +1.00% | 1.13x |
| 30% | −1.50% | 0.84x |
| 40% | −5.00% | 0.55x |

- Recovery needed: −10% → +11%; −20% → +25%; −30% → +43%; −50% → +100%; −75% → +300%; −90% → +900% (arithmetic: 1/(1−L) − 1).
- Crypto hedge funds averaged about 46% annualized volatility in 2025 (per aggregator summary of Crypto Fund Research). — [Crypto Fund Research 2025 review (via search snippet; page blocked)](https://cryptofundresearch.com/crypto-hedge-fund-performance/)

### Inferences
- A bot running at 30-40% monthly volatility (common when risking 5-10% per trade on altcoins) needs an arithmetic edge above about 5-8% per month just to break even geometrically.
- The monthly sweep also reduces the compounding base. That is intended: it trades expected geometric growth for locked-in gains.

### Gaps
- None material.

---

## 4. Compounding math and what the best funds actually achieve

### Takeaway
Doubling every month (the implicit "grow as fast as possible" goal) compounds to 4,096x per year. 2% per day is 1,377x per year. The best-documented trading operation in history, Renaissance's Medallion fund, averaged about 66% per year gross (39% net) from 1988-2018. Crypto hedge fund indices return tens of percent in good years with 40%+ volatility, and many quant crypto funds were roughly flat in 2025. Any target above about 5-10% per month should be treated as unrealistic at scale.

### Cited Findings
- Constant-rate compounding (own calculation):

| return | per | 30-day multiple | 1-yr multiple | $500 after 1 yr |
|---|---|---|---|---|
| 0.5% | day | 1.16x | 6.2x | $3,087 |
| 1% | day | 1.35x | 37.8x | $18,892 |
| 2% | day | 1.81x | 1,377x | $688,704 |
| 5% | day | 4.32x | 5.4e7x | $27 billion |
| 5% | week | 1.23x | 12.6x | $6,321 |
| 10% | week | 1.50x | 142x | $71,021 |
| 10% | month | 1.10x | 3.1x | $1,569 |
| 20% | month | 1.20x | 8.9x | $4,458 |
| 50% | month | 1.50x | 130x | $64,873 |
| 100% | month | 2.00x | 4,096x | $2,048,000 |

- Medallion Fund: about 66% average annual return before fees and about 39% after fees, 1988-2018 (Zuckerman, *The Man Who Solved the Market*). Fees were 5% management and 44% performance after 2002. $100 grew to about $398.7M (63.3% compound gross). No negative year in 31 years. — [Visual Capitalist](https://www.visualcapitalist.com/growth-of-100-invested-in-jim-simons-medallion-fund/); [Cornell Capital Group](https://www.cornell-capital.com/blog/2020/02/medallion-fund-the-ultimate-counterexample.html)
- 2024: VisionTrack Quant Directional index +53.7%, Fundamental index +40.4%, Market Neutral index +18.5%. Crypto hedge funds overall trailed bitcoin (BTC was about +120% in 2024). — [Hedgeweek](https://www.hedgeweek.com/bitcoin-surges-ahead-of-crypto-in-2024/)
- 2025: the average crypto hedge fund returned about 36%. One aggregator summary says quant funds "led with 48%", but the same source reportedly gives a **median quant fund return of +3.2%, with only 58% (15 of 26) of quant funds positive**. Market-neutral funds were about +13%; average volatility 46%; average Sharpe about 1.6. — [Crypto Fund Research 2025 review (via search snippet; direct fetch blocked)](https://cryptofundresearch.com/crypto-hedge-fund-performance/); secondary: [SQ Magazine](https://sqmagazine.co.uk/crypto-hedge-funds-statistics/). **Conflict flag:** the "48%" average and the "+3.2% median" for quant funds are inconsistent unless a few funds had very large returns. I could not verify the primary page.
- The Eurekahedge Cryptocurrency Hedge Fund Index had only about 17 reporting funds (equal-weighted). Legacy Eurekahedge indices are being sunset in 2025 after the acquisition by With Intelligence. — [With Intelligence / Eurekahedge](https://www.withintelligence.com/solutions/indices/) (via search snippet)

### Inferences
- Realistic ceiling for a skilled systematic crypto strategy: about 20-60% per year, with some losing years. That is roughly 1.5-4% per month average, not 100%. A $500 bot targeting 2x per month is aiming at about 50-100x the returns of the best funds. The small base (no capacity constraint) helps a little, but not by orders of magnitude, because fees, slippage and edge decay stay the same.
- Medallion's edge came from very high trade counts, low per-trade risk, and leverage on a proven, low-variance edge. That is the opposite of large bets on a small account.

### Gaps
- Could not access HFR, PwC/AIMA Global Crypto Hedge Fund Report, or Eurekahedge crypto index year-by-year numbers for 2020-2025 directly (sites blocked or paywalled). From memory (unverified here): the Eurekahedge crypto index had very large gains in 2017 and 2020-21 and large losses in 2018 and 2022. The report writer should not state specific figures for those years without a source.

---

## 5. Retail day-trader and crypto-trader outcome statistics, and why most fail

### Takeaway
Every large dataset shows the same result. Among Brazilian day traders who persisted for more than 300 days, 97% lost money. Fewer than 1% of Taiwanese day traders were predictably profitable. 74-89% of EU retail CFD accounts lose money. About 73-81% of retail crypto app users lost money on bitcoin, having bought during rallies. Leverage-driven liquidation cascades (e.g., $19B on 10 Oct 2025) wipe out leveraged retail positions at once.

### Cited Findings
- **Brazil (Chague, De-Losso, Giovannetti, "Day Trading for a Living?", 2019/2020):** covers all individuals who began day trading Brazilian equity index futures in 2013-2015. 97% of those who persisted for more than 300 days lost money. Only 1.1% earned more than the Brazilian minimum wage, and only 0.5% (reported elsewhere as 0.4%) earned more than a bank teller's starting salary (about US$54/day). The top individual earned about US$310/day with a standard deviation of US$2,560. There was no evidence of learning with experience. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101); [summary (tradicted)](https://www.tradicted.com/research/chagu-day-2020/)
- **Taiwan (Barber, Lee, Liu, Odean, "The cross-section of speculator skill", 1992-2006):** fewer than 1% of day traders (about 4,000 people) could predictably and reliably earn positive abnormal returns net of fees. Top-ranked traders earned 61.3 bps/day before fees (37.9 after). Bottom-ranked traders earned −11.5 bps before fees (−28.9 after). — [eScholarship](https://escholarship.org/uc/item/7k75v0qx); [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1386418113000190)
- Barber et al. also show that day traders keep trading despite losing ("Do Day Traders Rationally Learn About Their Ability?"). — [Berkeley PDF](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf)
- **EU CFDs (ESMA 2018):** national regulators' analyses show that 74-89% of retail CFD accounts typically lose money, with average losses per client of €1,600 to €29,000. Reasons cited: excessive leverage, structurally negative expected returns (costs), and conflicts of interest. Response: leverage caps, margin close-out, negative balance protection, and mandatory loss-percentage disclosures. — [ESMA press release](https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors); [ESMA additional info PDF](https://www.esma.europa.eu/sites/default/files/library/esma35-43-1000_additional_information_on_the_agreed_product_intervention_measures_relating_to_contracts_for_differences_and_binary_options.pdf)
- **Retail crypto (BIS):** BIS research using Sensor Tower data on 200+ crypto exchange apps across 95 countries (Aug 2015 – Dec 2022) found that about 73-81% of retail users would have lost money on their bitcoin investment. Most downloads happened when BTC was above $20,000, and users were drawn in by rising prices. For a user buying $100/month, the median investor lost $431, or 48% of $900 invested. About 40% of new users were men under 35. — [Bloomberg Law](https://news.bloomberglaw.com/crypto/about-75-of-retail-buyers-of-bitcoin-lost-money-bis-study-says); [RinggitPlus summary](https://ringgitplus.com/en/blog/cryptocurrency/bis-study-three-quarters-of-bitcoin-investors-have-suffered-losses.html); [BIS WP 1049](https://www.bis.org/publ/work1049.htm)
- **BIS Bulletin 69 "Crypto shocks and retail losses" (Feb 2023, Cornelli, Doerr, Frost, Gambacorta):** after Terra/Luna and FTX, trading activity rose sharply, with large holders selling and small retail investors buying. A majority of crypto app users in nearly all economies made losses on bitcoin. Monthly active users rose from about 100,000 (Aug 2015) to more than 30 million (Nov 2021). — [BIS Bulletin 69](https://www.bis.org/publ/bisbull69.htm); [IDEAS/RePEc](https://ideas.repec.org/p/bis/bisblt/69.html)
- **Leverage and liquidations, 10-11 Oct 2025:** more than $19B of leveraged crypto positions were liquidated in about 24 hours, affecting more than 1.6 million traders. That was about 9x the previous single-day record. BTC fell about 14% (about $122k to $105k) and ETH about 12%. Some altcoins briefly collapsed much further intraday (SOL more than 40% at one point, reported TON −80%, WLD −70%). Analysts estimate actual trader losses at about 5-15% of the headline $19B. — [CoinDesk Research](https://www.coindesk.com/research/market-spotlight-the-19-billion-liquidation-that-shook-crypto); [CNBC](https://www.cnbc.com/2025/10/22/the-biggest-crypto-wipeout-was-led-not-by-bitcoin-but-much-smaller-tokens-heres-what-happened.html); [Yahoo Finance](https://finance.yahoo.com/news/19b-crypto-liquidations-didn-t-135537432.html); [FTI Consulting](https://www.fticonsulting.com/insights/articles/crypto-crash-october-2025-leverage-met-liquidity)
- Perpetual futures dominate crypto derivatives (more than $60T of volume in 2024), and higher-risk traders prefer perps. — [arXiv 2512.01112](https://arxiv.org/pdf/2512.01112v3) (via search snippet)

### Inferences
- Why they fail, as shown in these studies: (1) **costs**: Taiwan's bottom traders lost 17 bps/day to fees on top of negative gross alpha; in our sim, 0.15R per trade turns a 0.20R gross edge into 0.05R; (2) **overtrading**, with no learning (Brazil, Taiwan); (3) **leverage**, which ESMA names as the main harm and 10/10 illustrates; (4) **procyclical entry**, buying after rallies (BIS); (5) the disposition effect, holding losers and selling winners (Odean's broader work; not fetched here).
- An automated bot removes some behavioral errors (disposition effect, revenge trading) but not costs, overfitting, or leverage/gap risk. Altcoin gaps of 40-80% on 10/10 would jump straight through a 2% stop, so a "1R" loss can become 10-40R on leveraged alt positions.

### Gaps
- Could not fetch primary BIS PDFs (bis.org blocked). BIS figures come from reputable secondary summaries (Bloomberg Law, RinggitPlus).
- Found no peer-reviewed study giving the share of *leveraged crypto perp* retail accounts that are profitable. Exchanges do not publish this the way EU CFD brokers must.
- Disposition-effect sources (Odean 1998; Shefrin-Statman) were not fetched in this session.

---

## 6. Small-account doubling challenges, martingale, all-in compounding (gambler's ruin)

### Takeaway
All-in doubling challenges are a sequence of multiplicative coin flips. Going from $500 to $512k by 10 all-in doublings succeeds 0.1% of the time at even odds, and still under 3% even at a 70% success rate per step. Martingale converts many small wins into a rare, total loss. Any negative-edge or zero-edge system eventually hits ruin with probability 1 (gambler's ruin).

### Cited Findings (own calculations; Kelly theory from MacLean/Thorp/Ziemba)
- P(10 consecutive successful all-in doublings): p=0.50 → 0.098%; p=0.55 → 0.25%; p=0.60 → 0.61%; p=0.70 → 2.8%.
- Betting at or above 2x Kelly gives zero or negative expected log growth, so the typical path goes to zero even with a positive-EV edge (see Q1 table: 3x Kelly → median 0.07x after 100 trades). A 100% bet (risking the whole account) when any loss is possible makes long-run ruin certain. — Kelly framework: [Ziemba chapter](https://webhomes.maths.ed.ac.uk/mckinnon/blackouts/StochOptFinanceAndEnergySpringer/Chap1_KellyZiemba.pdf)
- 25%-risk simulation (strategy A, 150 trades): mean 811x, but median 0.07x, and 82% of paths fall below 20% of start at some point. This is the "doubling challenge" outcome in numbers.

### Inferences
- Published "I turned $500 into $50k" stories come from survivorship bias: the 99%+ of attempts that blew up are not posted.
- Martingale (doubling size after losses) breaks precisely in correlated crypto sell-offs, where losing streaks cluster. In our IID model, even a 45%-win system sees 10+ loss streaks in 88% of years. A 10-step martingale needs 1,023 units of capital to survive one such streak.

### Gaps
- Found no academic dataset on outcomes of public "small account challenges"; the evidence is theoretical plus simulation.

---

## 7. Best-practice risk controls, scaling rules, profit sweeps, and statistical significance (skill vs. luck)

### Takeaway
To show a strategy has real skill takes hundreds of trades, or months to years of daily returns. For an annual Sharpe of 2 (world-class), you need about 250 daily observations (about 8 months) for 95% confidence. For Sharpe 1 you need about 2.7 years. A backtest picked as the best of 100-1,000 variants will show an annual Sharpe of 2.5-3.3 on one year of data even with zero skill. So capital should scale up only after live (not backtested) evidence, with hard caps on per-trade, daily, correlated and drawdown risk.

### Cited Findings
- **Minimum Track Record Length** (Bailey & López de Prado 2012): MinTRL = 1 + [1 − γ₃·SR + ((γ₄−1)/4)·SR²]·(z₁₋α / SR)², with SR measured per observation, γ₃ = skewness and γ₄ = kurtosis. It gives the number of observations needed to reject SR ≤ 0 at confidence 1−α. — [Portfolio Optimizer (explainer)](https://portfoliooptimizer.io/blog/the-probabilistic-sharpe-ratio-bias-adjustment-confidence-intervals-hypothesis-testing-and-minimum-track-record-length/); [Bailey & López de Prado, "The Sharpe Ratio Efficient Frontier" (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1821643)
- Own computation (365 trading days/yr for crypto, α = 5% one-sided):

| annual Sharpe | daily obs (normal) | years | daily obs (skew −1, kurtosis 10) | years | monthly obs (normal) |
|---|---|---|---|---|---|
| 0.5 | 3,952 | 10.8 | 4,061 | 11.1 | 132 |
| 1.0 | 990 | 2.7 | 1,046 | 2.9 | 35 |
| 1.5 | 441 | 1.2 | 480 | 1.3 | 17 |
| 2.0 | 249 | 0.7 | 280 | 0.8 | 10 |
| 3.0 | 112 | 0.3 | 134 | 0.4 | 6 |

- **Deflated Sharpe Ratio** (Bailey & López de Prado 2014): corrects the Sharpe ratio for selection bias across multiple trials, backtest overfitting and non-normality. — [SSRN 2460551](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551); [PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf)
- Own computation (false strategy theorem approximation used in the DSR paper): expected maximum annualized Sharpe among N zero-skill strategy variants:

| N variants tried | 1 year of data | 3 years of data |
|---|---|---|
| 10 | 1.57 | 0.91 |
| 100 | 2.53 | 1.46 |
| 1,000 | 3.26 | 1.88 |
| 10,000 | 3.86 | 2.23 |

- Trades needed for a t-stat on mean R per trade (t = mean/sd·√n), net of costs (own calculation):

| strategy | net EV (R) | sd (R) | trades for t=2 | trades for t=3 |
|---|---|---|---|---|
| A (45%/2.0) | +0.200 | 1.49 | 223 | 502 |
| B (40%/2.0) | +0.050 | 1.47 | 3,456 | 7,776 |
| C (55%/1.5) | +0.225 | 1.24 | 123 | 275 |

- Regulators' structural controls on retail leverage (ESMA): margin close-out rules, negative balance protection, leverage limits by asset class (crypto CFDs are capped at 2:1 for EU retail under the 2018 measures). — [ESMA press release](https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors). The 2:1 crypto figure is from my knowledge of the ESMA measures; verify against the ESMA page.

### Inferences (recommended control set derived from the above; not from a single source)
- **Per-trade risk:** 0.5-2% of equity (≤ 1/4 of the Kelly fraction estimated from *live* results, after costs). Our sims show 1-2% keeps P(50% drawdown in a month) near 0% for any positive-edge system, while 5% or more puts it at 15-77%.
- **Total correlated open risk cap:** for example, ≤ 3-5% of equity summed across all open alt positions. Treat BTC/ETH/alt longs as one correlated bucket.
- **Daily loss limit:** stop trading for the day after about −3R to −4R (about −3-6% at 1-1.5% risk). **Weekly limit:** about −8-10%. **Circuit breaker:** halt and review when the drawdown from peak reaches 15-20%. Recovery math (−20% needs +25%) means stopping early costs little.
- **Leverage:** avoid it, or keep it low (≤ 2-3x notional), and use isolated margin. Gaps like 10/10 go through stops.
- **Scaling rule:** keep the $500 test size until live results reach statistical evidence. That means at least about 200-500 live trades (t ≥ 2-3 on mean R), or at least about 6-12 months of daily P&L with Sharpe clearly above what the MinTRL table requires. Then scale in steps (e.g., 2x capital per step), only while live win rate, payoff and slippage stay within the backtest's confidence band. Scale back down on a circuit-breaker hit.
- **Profit sweep:** a monthly sweep of profits above the starting base (or "withdraw principal after doubling") turns part of the paper growth into realized gains. It lowers the compounding base, so the median path grows more slowly, but it protects gains from later drawdowns. It fits a goal of "as fast as possible without blowing up".
- **Backtest hygiene:** record how many parameter variants were tried and apply a deflated-Sharpe haircut. If you tried 100 or more variants, treat a 1-year backtest Sharpe below about 2.5 as consistent with no skill. Paper-trade forward before risking money.
- Expectation setting: with a genuinely good edge at 1-2% risk, a realistic 30-day distribution is about −10% to +80%, centered around +10-60% (and that is only if the edge is real). Doubling in one month needs 5% or more risk, which means drawdowns of 50% or more are likely.

### Gaps
- Found no peer-reviewed study on the specific effect of "withdraw principal after doubling" rules; the reasoning here is analytical.
- MinTRL assumes stationary returns. Crypto regime changes (bull vs. bear) mean even a statistically significant track record may not carry forward.

### Appendix: simulation code (run with Python 3 + numpy 2.4 / scipy 1.17, seed 42)

```python
"""Position-sizing / ruin / compounding simulations for a $500 crypto bot.
Model: each trade risks fraction f of current equity. Stop = 1R loss, target = b R win.
Costs: round-trip fee+slippage as % of notional; stop distance s (% of price) sets notional = f*E/s,
so cost in R units c = cost_rt / s. Win -> +(b - c)R, Loss -> -(1 + c)R.
"""
import numpy as np
from scipy.stats import norm
rng = np.random.default_rng(42)
N_PATHS = 100_000

def kelly(p, W, L):
    q = 1 - p
    return (p * W - q * L) / (W * L)

def g(f, p, W, L):
    return p * np.log1p(f * W) + (1 - p) * np.log1p(-f * L)

def sim(p, b, f, n_trades, c=0.0, paths=N_PATHS, true_p=None):
    tp = p if true_p is None else true_p
    W, L = b - c, 1 + c
    wins = rng.random((paths, n_trades)) < tp
    mult = np.where(wins, 1 + f * W, np.maximum(1 - f * L, 0.0))
    eq = np.cumprod(mult, axis=1)
    peak = np.maximum.accumulate(np.concatenate([np.ones((paths, 1)), eq], axis=1), axis=1)[:, 1:]
    dd = 1 - eq / peak
    maxdd = dd.max(axis=1)
    final = eq[:, -1]
    return final, maxdd, eq.min(axis=1)

def row(label, final, maxdd, minEq):
    pct = np.percentile(final, [5, 25, 50, 75, 95])
    return (f"| {label} | {final.mean():.2f} | {pct[0]:.2f} | {pct[1]:.2f} | {pct[2]:.2f} | {pct[3]:.2f} | {pct[4]:.2f} | "
            f"{(final < 1).mean()*100:.1f}% | {(final >= 2).mean()*100:.1f}% | {(maxdd >= 0.2).mean()*100:.1f}% | "
            f"{(maxdd >= 0.5).mean()*100:.1f}% | {(minEq <= 0.2).mean()*100:.1f}% |")

HDR = ("| risk/trade | mean x | p5 | p25 | median | p75 | p95 | P(loss) | P(>=2x) | P(maxDD>=20%) | P(maxDD>=50%) | P(equity ever <=20% of start) |\n"
       "|---|---|---|---|---|---|---|---|---|---|---|---|")

# cost assumption: 0.10% taker each side + 0.05% slippage each side = 0.30% round trip; stop distance 2% -> c = 0.15R
COST_RT, STOP = 0.003, 0.02
C = COST_RT / STOP

strategies = {
    "A: p=0.45, b=2.0 (good breakout)": (0.45, 2.0),
    "B: p=0.40, b=2.0 (marginal breakout)": (0.40, 2.0),
    "C: p=0.55, b=1.5 (high-hit-rate)": (0.55, 1.5),
    "D: p=0.33, b=2.0 (no edge before costs)": (1/3, 2.0),
}

print("## Kelly fractions (per-trade fraction of equity risked)\n")
print("| strategy | gross EV (R) | net EV (R) after c=%.2fR | full Kelly gross | full Kelly net | half Kelly net | quarter Kelly net | max log-growth/trade net |" % C)
print("|---|---|---|---|---|---|---|---|")
for k, (p, b) in strategies.items():
    evg = p * b - (1 - p)
    evn = p * (b - C) - (1 - p) * (1 + C)
    kg = kelly(p, b, 1)
    kn = kelly(p, b - C, 1 + C)
    gmax = g(kn, p, b - C, 1 + C) if kn > 0 else float('nan')
    print(f"| {k} | {evg:+.3f} | {evn:+.3f} | {kg*100:.1f}% | {kn*100:.1f}% | {kn*50:.1f}% | {kn*25:.1f}% | {gmax*100:.3f}% |")

print("\n## Growth rate vs. betting fraction (strategy A net of costs): overbetting\n")
p, b = 0.45, 2.0
W, L = b - C, 1 + C
kn = kelly(p, W, L)
print(f"Full Kelly (net) = {kn*100:.1f}% of equity risked per trade\n")
print("| multiple of Kelly | risk/trade | expected log growth/trade | growth as % of max | median equity multiple after 100 trades |")
print("|---|---|---|---|---|")
gm = g(kn, p, W, L)
for m in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]:
    f = m * kn
    if f * L >= 1:
        print(f"| {m} | {f*100:.1f}% | -inf (ruin) | - | 0 |"); continue
    gg = g(f, p, W, L)
    print(f"| {m}x | {f*100:.1f}% | {gg*100:+.3f}% | {gg/gm*100:.0f}% | {np.exp(100*gg):.2f}x |")

for n_trades in [60, 150]:
    for k, (p, b) in strategies.items():
        print(f"\n## 30-day outcomes, {k}, {n_trades} trades/30 days, costs {C:.2f}R per trade, start = 1.0 (x $500)\n")
        print(HDR)
        for f in [0.01, 0.02, 0.05, 0.10, 0.25]:
            final, maxdd, minEq = sim(p, b, f, n_trades, C)
            print(row(f"{f*100:.0f}%", final, maxdd, minEq))

# estimation error: believe strategy A (p=.45) but true p=.40 or .38
print("\n## Estimation error: sized for p=0.45 (A) but true win rate lower; 150 trades\n")
print(HDR.replace("risk/trade", "true p / risk"))
for tp in [0.45, 0.40, 0.36]:
    for m, lab in [(0.25, "1/4K"), (0.5, "1/2K"), (1.0, "fullK")]:
        f = m * kelly(0.45, 2 - C, 1 + C)
        final, maxdd, minEq = sim(0.45, 2.0, f, 150, C, true_p=tp)
        print(row(f"p={tp} {lab} ({f*100:.1f}%)", final, maxdd, minEq))

# 1-year: 12 cycles of 150 trades, strategy A and B, no sweep
print("\n## 12 months (1,800 trades), no sweeps, costs included\n")
print(HDR)
for k in ["A: p=0.45, b=2.0 (good breakout)", "B: p=0.40, b=2.0 (marginal breakout)"]:
    p, b = strategies[k]
    for f in [0.01, 0.02, 0.05]:
        final, maxdd, minEq = sim(p, b, f, 1800, C, paths=20_000)
        print(row(f"{k[:1]} {f*100:.0f}%", final, maxdd, minEq))

# Kelly drawdown theory check: P(ever hitting x of start) ~ x^(2/c - 1) for fraction c of Kelly (continuous approx)
print("\n## Theory: probability of ever falling to fraction x of starting capital (continuous-time GBM approx)\n")
print("| Kelly fraction c | P(ever down 50%) | P(ever down 80%) | P(ever down 90%) | growth as % of max (c(2-c)) |")
print("|---|---|---|---|---|")
for cfr in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
    e = 2 / cfr - 1
    pr = lambda x: 1.0 if e <= 0 else x ** e
    print(f"| {cfr} | {pr(0.5)*100:.1f}% | {pr(0.2)*100:.2f}% | {pr(0.1)*100:.3f}% | {cfr*(2-cfr)*100:.0f}% |")

# Losing streaks
print("\n## Probability of at least one losing streak of length k within N trades\n")
def p_streak(q, k, n, paths=50_000):
    losses = rng.random((paths, n)) < q
    run = np.zeros(paths, int); best = np.zeros(paths, int)
    for i in range(n):
        run = np.where(losses[:, i], run + 1, 0); best = np.maximum(best, run)
    return (best >= k).mean()
print("| win rate | N trades | P(streak>=5) | P(>=8) | P(>=10) | P(>=12) |")
print("|---|---|---|---|---|---|")
for p_ in [0.40, 0.45, 0.55]:
    for n in [150, 1800]:
        print(f"| {p_} | {n} | " + " | ".join(f"{p_streak(1-p_, k, n)*100:.1f}%" for k in [5, 8, 10, 12]) + " |")

# Compounding table
print("\n## Compounding: constant per-period returns\n")
print("| return | per | 30-day multiple | 1-yr multiple | $500 after 1 yr |")
print("|---|---|---|---|---|")
for r, per, n30, n365 in [(0.005, "day", 30, 365), (0.01, "day", 30, 365), (0.02, "day", 30, 365), (0.05, "day", 30, 365),
                         (0.05, "week", 30/7, 52), (0.10, "week", 30/7, 52), (0.10, "month", 1, 12), (0.20, "month", 1, 12), (0.50, "month", 1, 12), (1.0, "month", 1, 12)]:
    print(f"| {r*100:.1f}% | {per} | {(1+r)**n30:.2f}x | {(1+r)**n365:,.1f}x | ${500*(1+r)**n365:,.0f} |")

# Volatility drag
print("\n## Volatility drag: arithmetic mean 3%/month, different monthly vol (lognormal approx g = mu - sigma^2/2)\n")
print("| monthly vol | geometric/month | 12-month median multiple |")
print("|---|---|---|")
for s in [0.05, 0.10, 0.20, 0.30, 0.40]:
    gg = 0.03 - s**2 / 2
    print(f"| {s*100:.0f}% | {gg*100:+.2f}% | {np.exp(12*gg):.2f}x |")
print("\nLoss recovery: " + ", ".join(f"-{l}% needs +{(1/(1-l/100)-1)*100:.0f}%" for l in [10, 20, 30, 50, 75, 90]))

# Doubling challenge / all-in
print("\n## All-in doubling challenge: $500 -> $512,000 needs 10 consecutive doublings\n")
for pw in [0.5, 0.55, 0.6, 0.7]:
    print(f"- per-bet success prob {pw}: P(10 in a row) = {pw**10*100:.3f}%")

# Statistical significance
print("\n## Trades needed for t-stat >= 2 on mean R per trade (t = mean/sd*sqrt(n))\n")
print("| strategy | net EV (R) | sd (R) | trades for t=2 | trades for t=3 |")
print("|---|---|---|---|---|")
for k, (p, b) in strategies.items():
    W, L = b - C, 1 + C
    mu = p * W - (1 - p) * L
    sd = np.sqrt(p * W**2 + (1 - p) * L**2 - mu**2)
    if mu <= 0:
        print(f"| {k} | {mu:+.3f} | {sd:.2f} | never (negative) | never |"); continue
    print(f"| {k} | {mu:+.3f} | {sd:.2f} | {int(np.ceil((2*sd/mu)**2))} | {int(np.ceil((3*sd/mu)**2))} |")

print("\n## Minimum Track Record Length (Bailey & Lopez de Prado 2012), SR*=0, 95% one-sided\n")
def mintrl(sr, skew=0.0, kurt=3.0, alpha=0.05):
    z = norm.ppf(1 - alpha)
    return 1 + (1 - skew * sr + (kurt - 1) / 4 * sr**2) * (z / sr) ** 2
print("| annual Sharpe | daily obs needed (normal) | = years | daily obs (skew -1, kurt 10) | = years | monthly obs needed (normal) |")
print("|---|---|---|---|---|---|")
for sra in [0.5, 1.0, 1.5, 2.0, 3.0]:
    srd = sra / np.sqrt(365); srm = sra / np.sqrt(12)
    d = mintrl(srd); d2 = mintrl(srd, -1, 10); m = mintrl(srm)
    print(f"| {sra} | {d:.0f} | {d/365:.1f} | {d2:.0f} | {d2/365:.1f} | {m:.0f} |")

# Expected max Sharpe from N trials of zero-skill strategies (false strategy theorem approx)
print("\n## Expected maximum Sharpe among N zero-skill backtests (Bailey et al. false strategy theorem), annualised, 1 year of daily data\n")
emc = 0.5772156649
print("| N configs tried | E[max annual SR] with 1y data | with 3y data |")
print("|---|---|---|")
for Nt in [10, 100, 1000, 10000]:
    z = (1 - emc) * norm.ppf(1 - 1 / Nt) + emc * norm.ppf(1 - 1 / (Nt * np.e))
    # sd of annualised SR estimate under null ~ 1/sqrt(years)
    print(f"| {Nt} | {z*1:.2f} | {z/np.sqrt(3):.2f} |")
```

Full raw output (all tables above were taken from this):

```text
## Kelly fractions (per-trade fraction of equity risked)

| strategy | gross EV (R) | net EV (R) after c=0.15R | full Kelly gross | full Kelly net | half Kelly net | quarter Kelly net | max log-growth/trade net |
|---|---|---|---|---|---|---|---|
| A: p=0.45, b=2.0 (good breakout) | +0.350 | +0.200 | 17.5% | 9.4% | 4.7% | 2.4% | 0.923% |
| B: p=0.40, b=2.0 (marginal breakout) | +0.200 | +0.050 | 10.0% | 2.4% | 1.2% | 0.6% | 0.058% |
| C: p=0.55, b=1.5 (high-hit-rate) | +0.375 | +0.225 | 25.0% | 14.5% | 7.2% | 3.6% | 1.624% |
| D: p=0.33, b=2.0 (no edge before costs) | -0.000 | -0.150 | -0.0% | -7.1% | -3.5% | -1.8% | nan% |

## Growth rate vs. betting fraction (strategy A net of costs): overbetting

Full Kelly (net) = 9.4% of equity risked per trade

| multiple of Kelly | risk/trade | expected log growth/trade | growth as % of max | median equity multiple after 100 trades |
|---|---|---|---|---|
| 0.25x | 2.4% | +0.408% | 44% | 1.50x |
| 0.5x | 4.7% | +0.696% | 75% | 2.01x |
| 0.75x | 7.1% | +0.866% | 94% | 2.38x |
| 1.0x | 9.4% | +0.923% | 100% | 2.52x |
| 1.5x | 14.1% | +0.700% | 76% | 2.01x |
| 2.0x | 18.8% | +0.033% | 4% | 1.03x |
| 2.5x | 23.5% | -1.084% | -117% | 0.34x |
| 3.0x | 28.2% | -2.669% | -289% | 0.07x |

## 30-day outcomes, A: p=0.45, b=2.0 (good breakout), 60 trades/30 days, costs 0.15R per trade, start = 1.0 (x $500)

| risk/trade | mean x | p5 | p25 | median | p75 | p95 | P(loss) | P(>=2x) | P(maxDD>=20%) | P(maxDD>=50%) | P(equity ever <=20% of start) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1% | 1.13 | 0.94 | 1.02 | 1.12 | 1.22 | 1.34 | 18.2% | 0.0% | 0.9% | 0.0% | 0.0% |
| 2% | 1.27 | 0.87 | 1.03 | 1.24 | 1.48 | 1.77 | 17.9% | 1.4% | 26.0% | 0.0% | 0.0% |
| 5% | 1.81 | 0.64 | 0.99 | 1.54 | 2.40 | 3.75 | 26.0% | 34.5% | 97.2% | 15.2% | 0.0% |
| 10% | 3.29 | 0.30 | 0.72 | 1.74 | 4.17 | 10.00 | 35.2% | 44.5% | 100.0% | 78.2% | 5.7% |
| 25% | 17.30 | 0.01 | 0.05 | 0.40 | 3.44 | 29.74 | 65.4% | 25.6% | 100.0% | 100.0% | 64.8% |

## 30-day outcomes, B: p=0.40, b=2.0 (marginal breakout), 60 trades/30 days, costs 0.15R per trade, start = 1.0 (x $500)

| risk/trade | mean x | p5 | p25 | median | p75 | p95 | P(loss) | P(>=2x) | P(maxDD>=20%) | P(maxDD>=50%) | P(equity ever <=20% of start) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1% | 1.03 | 0.86 | 0.94 | 1.02 | 1.12 | 1.22 | 45.1% | 0.0% | 4.5% | 0.0% | 0.0% |
| 2% | 1.06 | 0.72 | 0.87 | 1.03 | 1.24 | 1.48 | 45.1% | 0.1% | 49.2% | 0.1% | 0.0% |
| 5% | 1.17 | 0.41 | 0.64 | 0.99 | 1.54 | 2.40 | 55.3% | 11.9% | 99.3% | 34.8% | 0.3% |
| 10% | 1.35 | 0.13 | 0.30 | 0.72 | 1.74 | 4.17 | 65.6% | 17.9% | 100.0% | 91.4% | 19.3% |
| 25% | 2.13 | 0.00 | 0.01 | 0.05 | 0.40 | 3.44 | 88.2% | 7.4% | 100.0% | 100.0% | 86.0% |

## 30-day outcomes, C: p=0.55, b=1.5 (high-hit-rate), 60 trades/30 days, costs 0.15R per trade, start = 1.0 (x $500)

| risk/trade | mean x | p5 | p25 | median | p75 | p95 | P(loss) | P(>=2x) | P(maxDD>=20%) | P(maxDD>=50%) | P(equity ever <=20% of start) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1% | 1.14 | 0.98 | 1.06 | 1.14 | 1.23 | 1.32 | 7.8% | 0.0% | 0.1% | 0.0% | 0.0% |
| 2% | 1.31 | 0.95 | 1.11 | 1.29 | 1.49 | 1.73 | 7.7% | 1.3% | 9.9% | 0.0% | 0.0% |
| 5% | 1.96 | 0.83 | 1.20 | 1.74 | 2.54 | 3.68 | 12.2% | 35.2% | 89.1% | 4.5% | 0.0% |
| 10% | 3.82 | 0.54 | 1.14 | 2.41 | 5.09 | 10.73 | 18.2% | 55.1% | 100.0% | 57.1% | 1.3% |
| 25% | 24.91 | 0.04 | 0.24 | 1.56 | 10.31 | 68.22 | 45.0% | 44.7% | 100.0% | 99.9% | 41.2% |

## 30-day outcomes, D: p=0.33, b=2.0 (no edge before costs), 60 trades/30 days, costs 0.15R per trade, start = 1.0 (x $500)

| risk/trade | mean x | p5 | p25 | median | p75 | p95 | P(loss) | P(>=2x) | P(maxDD>=20%) | P(maxDD>=50%) | P(equity ever <=20% of start) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1% | 0.91 | 0.76 | 0.86 | 0.91 | 0.96 | 1.09 | 83.2% | 0.0% | 23.7% | 0.0% | 0.0% |
| 2% | 0.83 | 0.57 | 0.72 | 0.82 | 0.92 | 1.17 | 83.3% | 0.0% | 80.9% | 2.0% | 0.0% |
| 5% | 0.64 | 0.23 | 0.35 | 0.55 | 0.74 | 1.33 | 89.0% | 1.1% | 99.9% | 71.0% | 4.0% |
| 10% | 0.40 | 0.04 | 0.13 | 0.22 | 0.40 | 1.30 | 93.2% | 2.2% | 100.0% | 98.8% | 56.2% |
| 25% | 0.10 | 0.00 | 0.00 | 0.00 | 0.01 | 0.19 | 98.8% | 0.6% | 100.0% | 100.0% | 98.1% |

## 30-day outcomes, A: p=0.45, b=2.0 (good breakout), 150 trades/30 days, costs 0.15R per trade, start = 1.0 (x $500)

| risk/trade | mean x | p5 | p25 | median | p75 | p95 | P(loss) | P(>=2x) | P(maxDD>=20%) | P(maxDD>=50%) | P(equity ever <=20% of start) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1% | 1.35 | 0.97 | 1.16 | 1.31 | 1.52 | 1.82 | 7.0% | 1.2% | 5.7% | 0.0% | 0.0% |
| 2% | 1.82 | 0.97 | 1.30 | 1.65 | 2.23 | 3.19 | 7.0% | 31.2% | 60.2% | 0.4% | 0.0% |
| 5% | 4.43 | 0.73 | 1.52 | 2.75 | 5.76 | 13.97 | 12.5% | 68.6% | 100.0% | 42.9% | 0.4% |
| 10% | 19.81 | 0.25 | 1.07 | 3.43 | 14.77 | 85.10 | 20.8% | 62.8% | 100.0% | 98.4% | 14.3% |
| 25% | 811.01 | 0.00 | 0.00 | 0.07 | 2.54 | 189.67 | 68.9% | 25.6% | 100.0% | 100.0% | 82.0% |

## 30-day outcomes, B: p=0.40, b=2.0 (marginal breakout), 150 trades/30 days, costs 0.15R per trade, start = 1.0 (x $500)

| risk/trade | mean x | p5 | p25 | median | p75 | p95 | P(loss) | P(>=2x) | P(maxDD>=20%) | P(maxDD>=50%) | P(equity ever <=20% of start) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1% | 1.08 | 0.79 | 0.94 | 1.06 | 1.20 | 1.43 | 40.3% | 0.0% | 27.2% | 0.0% | 0.0% |
| 2% | 1.16 | 0.60 | 0.86 | 1.09 | 1.38 | 1.98 | 40.3% | 4.1% | 86.6% | 5.4% | 0.0% |
| 5% | 1.45 | 0.22 | 0.54 | 0.98 | 1.77 | 4.29 | 53.5% | 22.3% | 100.0% | 77.0% | 6.6% |
| 10% | 2.11 | 0.02 | 0.14 | 0.44 | 1.43 | 8.24 | 66.2% | 18.1% | 100.0% | 99.9% | 50.3% |
| 25% | 3.35 | 0.00 | 0.00 | 0.00 | 0.01 | 0.60 | 95.8% | 2.9% | 100.0% | 100.0% | 97.6% |

## 30-day outcomes, C: p=0.55, b=1.5 (high-hit-rate), 150 trades/30 days, costs 0.15R per trade, start = 1.0 (x $500)

| risk/trade | mean x | p5 | p25 | median | p75 | p95 | P(loss) | P(>=2x) | P(maxDD>=20%) | P(maxDD>=50%) | P(equity ever <=20% of start) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1% | 1.40 | 1.09 | 1.24 | 1.40 | 1.55 | 1.80 | 1.6% | 0.6% | 0.7% | 0.0% | 0.0% |
| 2% | 1.96 | 1.11 | 1.50 | 1.92 | 2.34 | 3.01 | 1.6% | 43.4% | 28.5% | 0.0% | 0.0% |
| 5% | 5.35 | 1.09 | 2.30 | 3.78 | 7.04 | 13.13 | 3.6% | 83.6% | 99.7% | 16.1% | 0.0% |
| 10% | 28.32 | 0.66 | 2.95 | 7.98 | 27.67 | 96.01 | 7.0% | 83.7% | 100.0% | 89.9% | 3.2% |
| 25% | 2811.18 | 0.00 | 0.18 | 4.16 | 51.64 | 2259.75 | 37.0% | 56.7% | 100.0% | 100.0% | 55.9% |

## 30-day outcomes, D: p=0.33, b=2.0 (no edge before costs), 150 trades/30 days, costs 0.15R per trade, start = 1.0 (x $500)

| risk/trade | mean x | p5 | p25 | median | p75 | p95 | P(loss) | P(>=2x) | P(maxDD>=20%) | P(maxDD>=50%) | P(equity ever <=20% of start) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1% | 0.80 | 0.60 | 0.70 | 0.79 | 0.89 | 1.06 | 92.8% | 0.0% | 80.3% | 0.7% | 0.0% |
| 2% | 0.64 | 0.35 | 0.47 | 0.60 | 0.76 | 1.09 | 92.9% | 0.0% | 99.3% | 48.0% | 0.1% |
| 5% | 0.32 | 0.06 | 0.12 | 0.22 | 0.40 | 0.98 | 96.3% | 0.7% | 100.0% | 98.3% | 54.7% |
| 10% | 0.11 | 0.00 | 0.01 | 0.02 | 0.08 | 0.44 | 98.4% | 0.4% | 100.0% | 100.0% | 94.6% |
| 25% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 100.0% | 0.0% | 100.0% | 100.0% | 100.0% |

## Estimation error: sized for p=0.45 (A) but true win rate lower; 150 trades

| true p / risk | mean x | p5 | p25 | median | p75 | p95 | P(loss) | P(>=2x) | P(maxDD>=20%) | P(maxDD>=50%) | P(equity ever <=20% of start) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| p=0.45 1/4K (2.4%) | 2.02 | 0.88 | 1.35 | 1.78 | 2.53 | 3.59 | 7.0% | 43.3% | 76.8% | 1.3% | 0.0% |
| p=0.45 1/2K (4.7%) | 4.06 | 0.76 | 1.52 | 2.65 | 5.31 | 12.22 | 9.5% | 68.8% | 99.8% | 38.5% | 0.3% |
| p=0.45 fullK (9.4%) | 16.17 | 0.22 | 1.16 | 3.48 | 13.74 | 71.46 | 20.7% | 68.7% | 100.0% | 97.0% | 11.6% |
| p=0.4 1/4K (2.4%) | 1.19 | 0.54 | 0.83 | 1.09 | 1.44 | 2.20 | 40.2% | 8.0% | 94.3% | 12.3% | 0.0% |
| p=0.4 1/2K (4.7%) | 1.43 | 0.25 | 0.57 | 1.00 | 1.75 | 4.02 | 46.7% | 22.9% | 100.0% | 73.5% | 5.0% |
| p=0.4 fullK (9.4%) | 2.03 | 0.03 | 0.17 | 0.51 | 1.53 | 7.93 | 66.0% | 23.0% | 100.0% | 99.7% | 45.2% |
| p=0.36 1/4K (2.4%) | 0.78 | 0.36 | 0.54 | 0.72 | 0.95 | 1.44 | 77.8% | 0.7% | 99.0% | 39.5% | 0.1% |
| p=0.36 1/2K (4.7%) | 0.61 | 0.11 | 0.25 | 0.44 | 0.76 | 1.75 | 82.5% | 3.7% | 100.0% | 92.6% | 24.3% |
| p=0.36 fullK (9.4%) | 0.37 | 0.01 | 0.03 | 0.10 | 0.29 | 1.53 | 92.4% | 3.8% | 100.0% | 100.0% | 79.3% |

## 12 months (1,800 trades), no sweeps, costs included

| risk/trade | mean x | p5 | p25 | median | p75 | p95 | P(loss) | P(>=2x) | P(maxDD>=20%) | P(maxDD>=50%) | P(equity ever <=20% of start) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A 1% | 36.50 | 10.49 | 19.66 | 29.88 | 45.41 | 85.07 | 0.0% | 100.0% | 64.9% | 0.0% | 0.0% |
| A 2% | 1356.43 | 74.21 | 259.44 | 597.60 | 1461.08 | 4812.35 | 0.0% | 100.0% | 100.0% | 12.4% | 0.0% |
| A 5% | 69300414.88 | 2600.24 | 57803.62 | 457000.06 | 3613079.14 | 80319185.59 | 0.0% | 100.0% | 100.0% | 100.0% | 1.1% |
| B 1% | 2.46 | 0.73 | 1.33 | 2.03 | 3.08 | 5.60 | 12.7% | 51.0% | 99.7% | 18.6% | 0.0% |
| B 2% | 5.96 | 0.37 | 1.21 | 2.80 | 6.44 | 21.23 | 19.8% | 60.3% | 100.0% | 89.7% | 5.2% |
| B 5% | 68.68 | 0.00 | 0.10 | 0.77 | 6.10 | 135.58 | 52.9% | 37.8% | 100.0% | 100.0% | 62.5% |

## Theory: probability of ever falling to fraction x of starting capital (continuous-time GBM approx)

| Kelly fraction c | P(ever down 50%) | P(ever down 80%) | P(ever down 90%) | growth as % of max (c(2-c)) |
|---|---|---|---|---|
| 0.25 | 0.8% | 0.00% | 0.000% | 44% |
| 0.5 | 12.5% | 0.80% | 0.100% | 75% |
| 0.75 | 31.5% | 6.84% | 2.154% | 94% |
| 1.0 | 50.0% | 20.00% | 10.000% | 100% |
| 1.5 | 79.4% | 58.48% | 46.416% | 75% |
| 2.0 | 100.0% | 100.00% | 100.000% | 0% |

## Probability of at least one losing streak of length k within N trades

| win rate | N trades | P(streak>=5) | P(>=8) | P(>=10) | P(>=12) |
|---|---|---|---|---|---|
| 0.4 | 150 | 99.7% | 64.2% | 29.6% | 11.7% |
| 0.4 | 1800 | 100.0% | 100.0% | 98.8% | 79.5% |
| 0.45 | 150 | 97.8% | 43.1% | 15.3% | 4.9% |
| 0.45 | 1800 | 100.0% | 99.9% | 87.5% | 46.2% |
| 0.55 | 150 | 79.4% | 12.5% | 2.6% | 0.5% |
| 0.55 | 1800 | 100.0% | 81.0% | 28.6% | 6.3% |

## Compounding: constant per-period returns

| return | per | 30-day multiple | 1-yr multiple | $500 after 1 yr |
|---|---|---|---|---|
| 0.5% | day | 1.16x | 6.2x | $3,087 |
| 1.0% | day | 1.35x | 37.8x | $18,892 |
| 2.0% | day | 1.81x | 1,377.4x | $688,704 |
| 5.0% | day | 4.32x | 54,211,841.6x | $27,105,920,789 |
| 5.0% | week | 1.23x | 12.6x | $6,321 |
| 10.0% | week | 1.50x | 142.0x | $71,021 |
| 10.0% | month | 1.10x | 3.1x | $1,569 |
| 20.0% | month | 1.20x | 8.9x | $4,458 |
| 50.0% | month | 1.50x | 129.7x | $64,873 |
| 100.0% | month | 2.00x | 4,096.0x | $2,048,000 |

## Volatility drag: arithmetic mean 3%/month, different monthly vol (lognormal approx g = mu - sigma^2/2)

| monthly vol | geometric/month | 12-month median multiple |
|---|---|---|
| 5% | +2.88% | 1.41x |
| 10% | +2.50% | 1.35x |
| 20% | +1.00% | 1.13x |
| 30% | -1.50% | 0.84x |
| 40% | -5.00% | 0.55x |

Loss recovery: -10% needs +11%, -20% needs +25%, -30% needs +43%, -50% needs +100%, -75% needs +300%, -90% needs +900%

## All-in doubling challenge: $500 -> $512,000 needs 10 consecutive doublings

- per-bet success prob 0.5: P(10 in a row) = 0.098%
- per-bet success prob 0.55: P(10 in a row) = 0.253%
- per-bet success prob 0.6: P(10 in a row) = 0.605%
- per-bet success prob 0.7: P(10 in a row) = 2.825%

## Trades needed for t-stat >= 2 on mean R per trade (t = mean/sd*sqrt(n))

| strategy | net EV (R) | sd (R) | trades for t=2 | trades for t=3 |
|---|---|---|---|---|
| A: p=0.45, b=2.0 (good breakout) | +0.200 | 1.49 | 223 | 502 |
| B: p=0.40, b=2.0 (marginal breakout) | +0.050 | 1.47 | 3456 | 7776 |
| C: p=0.55, b=1.5 (high-hit-rate) | +0.225 | 1.24 | 123 | 275 |
| D: p=0.33, b=2.0 (no edge before costs) | -0.150 | 1.41 | never (negative) | never |

## Minimum Track Record Length (Bailey & Lopez de Prado 2012), SR*=0, 95% one-sided

| annual Sharpe | daily obs needed (normal) | = years | daily obs (skew -1, kurt 10) | = years | monthly obs needed (normal) |
|---|---|---|---|---|---|
| 0.5 | 3952 | 10.8 | 4061 | 11.1 | 132 |
| 1.0 | 990 | 2.7 | 1046 | 2.9 | 35 |
| 1.5 | 441 | 1.2 | 480 | 1.3 | 17 |
| 2.0 | 249 | 0.7 | 280 | 0.8 | 10 |
| 3.0 | 112 | 0.3 | 134 | 0.4 | 6 |

## Expected maximum Sharpe among N zero-skill backtests (Bailey et al. false strategy theorem), annualised, 1 year of daily data

| N configs tried | E[max annual SR] with 1y data | with 3y data |
|---|---|---|
| 10 | 1.57 | 0.91 |
| 100 | 2.53 | 1.46 |
| 1000 | 3.26 | 1.88 |
| 10000 | 3.86 | 2.23 |
```
