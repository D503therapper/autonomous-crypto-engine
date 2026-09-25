# US Federal Tax Treatment and Record-Keeping for an Individual Running a High-Frequency Crypto Trading Bot (2025-2026)

> Current as of 2026-09-25. **Not tax advice.** Research method note: IRS.gov, Congress.gov, Ways & Means, Tax Foundation, CNBC, Gordon Law and Green Trader Tax pages were **blocked from direct fetch** in this research environment, so many findings below come from search-result extracts of those pages (URLs still cited). Figures that could not be cross-checked against a primary page are flagged. A CPA experienced with digital assets / trader tax status should review before acting.

## 1. Every trade is a taxable disposal; short-term vs long-term; 2025/2026 brackets

### Takeaway
Crypto is "property": every crypto-to-USD sale **and every crypto-to-crypto swap** (including into stablecoins) is a taxable disposal that realizes gain or loss. A bot that holds positions for minutes/days produces almost entirely **short-term** gains (held one year or less), taxed at ordinary income rates (10%-37%), not the 0/15/20% long-term rates.

### Cited Findings
- Notice 2014-21: convertible virtual currency is treated as property for federal tax purposes; general property-transaction principles apply — [Tax Notes summary of IRS guidance](https://www.taxnotes.com/research/federal/irs-guidance/notices/irs-updates-crypto-guidance-to-reflect-bitcoin-characterization/7gks6); [IRS virtual currency FAQ](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-virtual-currency-transactions)
- Exchanges of one virtual currency for another are sales/exchanges of property that trigger gain or loss — [Boston Bar Association](https://bostonbar.org/journal/irs-focus-on-tax-reporting-of-virtual-currency-transactions/); [IRS FAQ](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-virtual-currency-transactions)
- Rev. Rul. 2019-24 (Oct 9, 2019) addresses hard forks and airdrops, released with the IRS virtual currency FAQs — [Fenwick](https://www.fenwick.com/insights/publications/irs-issues-long-awaited-cryptocurrency-guidance-in-revenue-ruling-2019-24-and-new-faqs); [IRS newsroom](https://www.irs.gov/newsroom/virtual-currency-irs-issues-additional-guidance-on-tax-treatment-and-reminds-taxpayers-of-reporting-obligations)
- Short-term = held one year or less; long-term = held more than one year — [IRS Topic 409](https://www.irs.gov/taxtopics/tc409)
- Seven ordinary rates (10, 12, 22, 24, 32, 35, 37%) made permanent by the One Big Beautiful Bill Act (OBBBA, 2025) — [Tax Foundation 2025](https://taxfoundation.org/data/all/federal/2025-tax-brackets/); [IRS 2026 inflation adjustments release](https://www.irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-2026-including-amendments-from-the-one-big-beautiful-bill)
- **2026 ordinary brackets (taxable income)** — Single: 10% to $12,400; 12% to $50,400; 22% to $105,700; 24% to $201,775; 32% to $256,225; 35% to $640,600; 37% above. MFJ: 10% to $24,800; 12% to $100,800; 22% to $211,400; 24% to $403,550; 32% to $512,450; 35% to $768,700; 37% above — [search extract, IRS/Tax Foundation/TIAA](https://www.tiaa.org/public/pdf/q/quick_tax_reference_guide.pdf); [IRS release](https://www.irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-2026-including-amendments-from-the-one-big-beautiful-bill). NOTE: one search summary gave the MFJ 37% threshold as $768,600 ([MOAA/Tax Foundation extract](https://taxfoundation.org/data/all/federal/2026-tax-brackets/)); the bracket table extract says $768,700 — verify on IRS page.
- 2026 standard deduction: $16,100 single / $32,200 MFJ / $24,150 HoH — [IRS release via search](https://www.irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-2026-including-amendments-from-the-one-big-beautiful-bill)
- **2025 ordinary brackets** (partial, from extracts): single 22% bracket starts at $48,475, 37% above $626,350; MFJ 22% starts at $96,950, 37% above $751,600. 2025 standard deduction $15,750 single / $31,500 MFJ / $23,625 HoH (OBBBA-increased) — [Tax Foundation 2025](https://taxfoundation.org/data/all/federal/2025-tax-brackets/); [Bipartisan Policy Center](https://bipartisanpolicy.org/explainer/2025-federal-income-tax-brackets-and-other-2025-tax-rules/)
- **LTCG brackets 2026**: 0% up to $49,450 (single) / $98,900 (MFJ); 15% up to $545,500 / $613,700; 20% above — [Kiplinger](https://www.kiplinger.com/taxes/irs-updates-capital-gains-tax-thresholds); [Tax Foundation](https://taxfoundation.org/data/all/federal/2026-tax-brackets/)
- **LTCG brackets 2025**: 0% up to $48,350 single / $96,700 MFJ — [CNBC](https://www.cnbc.com/2025/12/12/capital-gains-tax-bracket-2025.html); [Kiplinger](https://www.kiplinger.com/taxes/capital-gains-tax/602224/capital-gains-tax-rates). The 15%/20% single threshold is conflicting in extracts: one extract says $583,400; the widely published IRS figure (Rev. Proc. 2024-40) is $533,400 single / $600,050 MFJ — treat $533,400 as likely correct but verify.
- 3.8% Net Investment Income Tax applies on top for MAGI above $200,000 single / $250,000 MFJ / $125,000 MFS — [Kiplinger/NerdWallet extract](https://www.nerdwallet.com/taxes/learn/capital-gains-tax-rates)

### Inferences
- A bot's profit is effectively taxed like wages at the marginal rate (plus NIIT if high income, plus state). Example: a single filer with $90k salary + $40k net bot gains in 2026 has the bot gains taxed largely at 22%-24% federal.
- Swapping to USDC/USDT at each cycle does not defer tax — each swap is a disposal. Fees generally adjust basis/proceeds (1099-DA proceeds are reported net of transaction fees; see §3).
- Short-term capital gains are not subject to self-employment tax for a non-dealer (general rule; see §6 for TTS nuance).

### Gaps
- Could not open IRS.gov directly to confirm every 2025 bracket boundary; full 2025 single table (10% to $11,925; 12% to $48,475; 22% to $103,350; 24% to $197,300; 32% to $250,525; 35% to $626,350) is from prior knowledge of Rev. Proc. 2024-40 and only partially confirmed by extracts.

## 2. Wash sale rule — current law and pending legislation

### Takeaway
As of 2026-09-25, the §1091 wash-sale rule **does not apply** to crypto held directly (it covers "stock or securities"; crypto is property). But two live House bills would change that, and one (H.R. 10357) cleared Ways & Means 38-5 on Sept 16, 2026. Nothing is enacted. A bot that harvests losses and immediately rebuys is currently allowed to realize those losses, but this is the most at-risk area.

### Cited Findings
- Wash sale rule does not apply to direct sales of crypto because IRS classifies crypto as property, not a security (§1091 covers stock or securities) — [Gordon Law Group](https://gordonlaw.com/learn/crypto-wash-sale-rule-in-2026-is-the-loophole-finally-closed/); [TokenTax](https://tokentax.co/blog/wash-sale-trading-in-crypto); [Chainwise CPA](https://chainwisecpa.com/crypto-wash-sale-2026/)
- Build Back Better Act (2021) would have extended §1091 to digital assets; passed House, not Senate — [search extract, Gordon Law/TokenTax](https://tokentax.co/blog/wash-sale-trading-in-crypto)
- **H.R. 9172**, "Applying Existing Tax Anti-Abuse Rules to Digital Assets Act," introduced June 8, 2026 by Rep. Jodey Arrington (R-TX), referred to Ways & Means; applies wash sale and constructive sale rules to digital assets by replacing "stock or securities" with "specified assets," excluding qualified U.S. dollar stablecoins — [Congress.gov](https://www.congress.gov/bill/119th-congress/house-bill/9172/text); [GovInfo](https://www.govinfo.gov/app/details/BILLS-119hr9172ih); [Ripon Advance](https://riponadvance.com/stories/arrington-proposes-anti-abuse-tax-rules-bill-for-digital-assets/)
- One secondary source claims H.R. 9172's wash-sale changes as drafted would apply to dispositions after the bill's introduction date (i.e., potentially retroactive to June 2026 if enacted in that form) — [search extract, TokenTax/Gordon Law](https://tokentax.co/blog/wash-sale-trading-in-crypto). UNVERIFIED against bill text.
- CNBC (July 28, 2026): "Congress renews push to end crypto wash sale tax loophole" — [CNBC](https://www.cnbc.com/2026/07/28/congress-renews-push-to-end-crypto-wash-sale-tax-loophole.html) (headline only; page not fetchable)
- **H.R. 10357, "Digital Asset Tax Certainty Act"**: Ways & Means markup Sept 16, 2026; ordered reported 38-5 with an amendment in the nature of a substitute; addresses reporting, wash sales, constructive sales, mining, staking, charitable donations, and parity with traditional assets — [Ways & Means markup page](https://waysandmeans.house.gov/event/markup-of-h-r-10357-h-r-10334-h-r-6130-h-r-5439-h-r-4093-h-r-10346-h-r-10356/); [W&M press release](https://waysandmeans.house.gov/2026/09/16/historic-digital-asset-tax-legislation-advances-to-keep-america-the-crypto-capital-of-the-world/); [Rep. Kelly release](https://kelly.house.gov/media/press-releases/kelly-backed-digital-asset-tax-certainty-act-passes-ways-means-committee); [JCT description](https://waysandmeans.house.gov/wp-content/uploads/2026/09/JCT-Description-of-HR-10357.pdf)
- H.R. 10357 extends wash-sale and constructive-sale provisions to digital assets; generally effective for taxable years beginning after date of enactment; simplified accounting for widely traded digital assets effective after Dec 31, 2027 — [search extract of JCT description / Phemex / Cryptopolitan](https://phemex.com/news/article/house-committee-advances-digital-asset-tax-certainty-act-with-wash-sale-rules-and-stablecoin-provisions-97074); [Cryptopolitan](https://www.cryptopolitan.com/house-crypto-tax-bill-digital-assets-rules/)
- H.R. 10357 includes a $10 de minimis exemption (reported as for certain transactions / network and transaction fees, delayed to 2028) — [dig.watch](https://dig.watch/updates/us-advance-digital-asset-tax-certainty-act); [KuCoin news](https://www.kucoin.com/news/flash/u-s-house-panel-advances-first-digital-asset-tax-framework-with-key-exemptions). Descriptions vary; scope unclear.
- The OBBBA (2025 reconciliation law) did not appear in any source as extending wash sale rules to crypto — sources describing 2026 status all say the rule still does not apply — [Chainwise CPA](https://chainwisecpa.com/crypto-wash-sale-2026/)

### Inferences
- If H.R. 10357 is enacted in its committee form in late 2026, wash-sale rules would most likely first bite for tax year 2027 (taxable years beginning after enactment). H.R. 9172's possible retroactivity is a tail risk for 2026 loss-harvesting.
- Bot design implication: log every loss sale and any repurchase of the same asset within ±30 days now, so that wash-sale adjustments could be computed later if law changes. Crypto tax software already has wash-sale toggles for stocks.
- Even under current law, economic-substance / sham-transaction doctrines could theoretically be raised against purely tax-motivated round trips; consult a CPA.

### Gaps
- Could not read the JCT description or bill text directly to confirm exact effective dates, definition of "substantially identical," and whether stablecoin trades are carved out in H.R. 10357.
- No Senate companion status found in this pass (a Lummis bill was previously reported; not verified here).

## 3. Capital loss limits

### Takeaway
Net capital losses offset capital gains without limit, but only **$3,000/yr ($1,500 MFS)** of net loss can offset ordinary income (e.g., wages); the rest carries forward indefinitely, keeping its short/long-term character.

### Cited Findings
- Excess loss deductible against income is the lesser of $3,000 ($1,500 MFS) or total net loss; excess carries forward to later years — [IRS Topic 409](https://www.irs.gov/taxtopics/tc409)
- Carryover retains its character (short-term stays short-term) and carries forward indefinitely — [H&R Block](https://www.hrblock.com/tax-center/income/investments/capital-loss-carryover/); [TaxAct](https://support.taxact.com/support/19792/capital-gains-and-losses-capital-loss-limit-and-carryforward-to-next-year)

### Inferences
- A losing bot year does little to reduce wage tax (max $3k). This is a key reason people consider §475 mark-to-market (ordinary losses) — but see §6 on whether that is available for spot crypto.

### Gaps
- None material.

## 4. Form 1099-DA, Form 8949 / Schedule D

### Takeaway
Custodial exchanges/brokers (e.g., Coinbase, Kraken) issue Form 1099-DA: **gross proceeds only for 2025 transactions** (forms delivered early 2026), and **gross proceeds + cost basis for "covered" assets acquired on/after Jan 1, 2026** in the same account (forms delivered early 2027). DeFi/non-custodial platforms do not issue it (DeFi broker rule repealed April 2025). Taxpayers still report each disposal on Form 8949, totals to Schedule D.

### Cited Findings
- For 2025 transactions, brokers report gross proceeds only; basis reporting optional; proceeds reported net of transaction fees — [IRS 2025 Instructions for Form 1099-DA](https://www.irs.gov/pub/irs-pdf/i1099da.pdf); [Count On Sheep](https://countonsheep.com/blog/1099-da-instructions)
- From Jan 1, 2026, brokers must report gross proceeds and adjusted basis for covered digital assets (acquired and held in the same broker account); for noncovered assets (transferred-in, pre-2026, cross-wallet) basis reporting remains optional — [TaxZerone summary of IRS instructions](https://www.taxzerone.com/resources/information-returns/form-1099-da-instructions/); [IRS: Understanding your Form 1099-DA](https://www.irs.gov/businesses/understanding-your-form-1099-da)
- If basis is not reported, the IRS may effectively treat it as zero, risking CP2000-type notices unless the taxpayer reports correct basis — [TaxZerone](https://www.taxzerone.com/resources/information-returns/form-1099-da-instructions/); [Camuso CPA](https://camusocpa.com/1099-da-guide/)
- Transactions are still reported on Form 8949 and totaled on Schedule D; 1099-DA data feeds Form 8949 — [TaxAct blog](https://blog.taxact.com/guide-to-form-1099-da-digital-asset-reporting/); [Camuso CPA](https://camusocpa.com/form-8949-crypto-taxes-1099-da-2025-compliance/); [The Tax Adviser (AICPA), Mar 2026](https://www.thetaxadviser.com/issues/2026/mar/navigating-the-form-1099-da-reporting-maze/)
- H.J. Res. 25 signed April 10, 2025 repealed the DeFi (non-custodial) broker reporting rule under the Congressional Review Act; custodial exchanges like Coinbase must still issue 1099-DA for 2025 trades — [Cooley](https://www.cooley.com/news/insight/2025/2025-04-21-congress-repeals-digital-asset-regulations-applicable-to-decentralized-finance-platforms); [Rep. Carey](https://carey.house.gov/2025/04/10/carey-bill-to-eliminate-burdensome-irs-defi-crypto-broker-rule-signed-into-law-by-president-trump/); [Awaken](https://awaken.tax/media/article/congress-nixes-defi-broker-rule-1099da-impact)

### Inferences
- For 2025 returns (filed 2026), the 1099-DA shows proceeds with no basis — the trader must supply basis from their own records for every trade. For a bot with thousands of trades, this essentially requires tax software.
- For 2026, bot trades executed entirely within one exchange account on assets bought there in 2026 should show basis on the 1099-DA; anything transferred in from another wallet/exchange is "noncovered" and needs own records.
- Foreign/offshore exchanges not subject to US broker rules may issue nothing; all gains are still reportable.
- Form 8949 may accept summary totals with attached statements when transactions are numerous (common practice; confirm with CPA/software).

### Gaps
- Could not confirm the new 2025 Form 8949 checkbox letters for 1099-DA-reported digital asset transactions (search did not return them); check current Form 8949 instructions.
- No authoritative list of which exchanges issued 2025 1099-DAs found beyond Coinbase as example.

## 5. Cost-basis methods and per-wallet tracking (Rev. Proc. 2024-28)

### Takeaway
From Jan 1, 2025, basis must be tracked **per wallet/account** ("universal" pooling across wallets is no longer allowed). Within each account you may use specific identification (which enables HIFO/LIFO-like selection) if identified at or before the sale — otherwise FIFO applies by default at brokers.

### Cited Findings
- Starting Jan 1, 2025, taxpayers can no longer track basis as if all digital assets were held in a single account; each wallet/account tracked separately — [RSM](https://rsmus.com/insights/tax-alerts/2024/end-universal-wallet-rev-proc-2024-28-safe-harbor-relief.html); [IRS Rev. Proc. 2024-28](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf); [CoinLedger](https://coinledger.io/blog/irs-new-crypto-cost-basis-rules-rev-proc-2024-28)
- Absent specific identification at or before the sale, brokers apply FIFO within the account; self-custody taxpayers may adopt a standing rule in books and records to identify units sold — [search extract, Rev. Proc. 2024-28 summaries](https://coinledger.io/blog/irs-new-crypto-cost-basis-rules-rev-proc-2024-28); [Duane Morris](https://www.duanemorris.com/alerts/action_needed_before_year_end_favorably_allocate_tax_basis_1224.html)
- Safe harbor allowed a reasonable reallocation of unused basis to assets held in each wallet as of Jan 1, 2025; the allocation method had to be determined before Jan 1, 2025 — [RSM](https://rsmus.com/insights/tax-alerts/2024/end-universal-wallet-rev-proc-2024-28-safe-harbor-relief.html); [Camuso CPA](https://camusocpa.com/rev-proc-2024-28-crypto-tax/)
- CoinLedger supports per-wallet cost basis tracking — [CoinLedger Help](https://help.coinledger.io/en/articles/10309974-how-will-coinledger-support-new-per-wallet-cost-basis-tracking-rules-irs-rev-proc-2024-28)

### Inferences
- For a bot on a single exchange, per-wallet rules are simple: that account is its own basis pool. Moving funds between exchanges/wallets carries basis with the specific units — keep transfer records.
- HIFO via specific ID can minimize short-term gains, but at a broker the identification generally must be communicated to the broker (or a standing order) — confirm whether the exchange supports standing specific-ID instructions; otherwise its 1099-DA will be FIFO and your return must reconcile.
- If the bot trades a single asset in and out within short windows, FIFO vs HIFO differences may be small; the method mostly matters for timing of gains.

### Gaps
- Extent of broker support for customer-directed specific ID (e.g., Coinbase, Kraken) not verified.

## 6. Trader Tax Status (TTS) and §475(f) mark-to-market

### Takeaway
TTS (a facts-and-circumstances "business of trading" status) can let an individual deduct trading expenses (bot hosting, data, software). But the §475(f) mark-to-market election — which converts gains/losses to ordinary and escapes the $3,000 limit and wash-sale rule — applies to "securities" and "commodities," and **most practitioners say spot crypto is neither for §475 purposes; it is a gray area.** H.R. 10357 would create an explicit digital-asset trader MTM election, but it is not law.

### Cited Findings
- IRS treats crypto as property, not securities, so the §475(f) election for securities traders typically does not apply directly to spot crypto; some argue certain crypto are "commodities" (Bitcoin and some crypto derivatives are commodities per CFTC), but this is not settled — [Green Trader Tax, Cryptocurrencies: TTS and Section 475 issues](https://greentradertax.com/cryptocurrencies-trader-tax-status-and-section-475-issues/); [Green Trader Tax, Can business traders apply 475 to bitcoin](https://greentradertax.com/can-business-traders-apply-section-475-elections-to-bitcoin-trades/); [Forbes, 2020](https://www.forbes.com/sites/shehanchandrasekera/2020/06/09/one-simple-tax-election-could-let-crypto-traders-write-off-unlimited-losses/)
- A bipartisan proposal would allow qualifying traders/dealers in covered digital assets to elect MTM, with year-end marks and ordinary gains/losses — [Green Trader Tax](https://greentradertax.com/bipartisan-digital-asset-tax-bill-could-apply-wash-sale-and-section-475-rules-to-crypto/)
- H.R. 10357 allows digital asset dealers and traders to use mark-to-market accounting, with transitional rules for an election in the first taxable year beginning after enactment — [search extract of JCT description](https://waysandmeans.house.gov/wp-content/uploads/2026/09/JCT-Description-of-HR-10357.pdf); [Unlock Blockchain](https://www.unlock-bc.com/en/house-committee-advances-digital-asset-tax-bill)

### Inferences
- Benefits of TTS (if qualified): business expense deductions (VPS/cloud, API/data fees, bot software, home office) on Schedule C; gains remain capital gains without §475. Risks: TTS is fact-intensive (substantial, regular, continuous trading; automated bots raise the question of whether the individual is "actively" trading) and is an audit flag.
- Claiming §475(f) ordinary treatment on spot crypto today is aggressive; a CPA should evaluate. If H.R. 10357 is enacted, an explicit election could become available from the next tax year after enactment.
- An MTM election, once made, would also make gains ordinary (no LTCG), which is irrelevant for a short-term bot but matters for any long-held coins in the same account.

### Gaps
- §475(f) election timing (generally by the original due date of the prior year's return, per Rev. Proc. 99-17) and TTS qualification tests could not be sourced from primary pages in this pass — confirm with CPA.
- Exact H.R. 10357 MTM eligibility definition ("covered digital assets") not verified.

## 7. Quarterly estimated taxes, safe harbors, and how much to set aside

### Takeaway
No tax is withheld on bot profits, so estimated payments are generally required (due Apr 15, Jun 15, Sep 15, Jan 15). To avoid underpayment penalties, pay the lesser of 90% of current-year tax or 100% of prior-year tax (**110% if prior-year AGI > $150,000**). The annualized-income method helps if profits are lumpy. Setting aside roughly the combined marginal rate (federal + NIIT if applicable + state) from each monthly withdrawal is a reasonable planning heuristic.

### Cited Findings
- 2026 estimated tax due dates: April 15, 2026; June 15, 2026; September 15, 2026; January 15, 2027 — [Instead](https://www.instead.com/resources/blog/how-to-calculate-q2-estimated-taxes-for-2026); [CountryTaxCalc](https://www.countrytaxcalc.com/tax-guides/usa/quarterly-estimated-tax-guide-2026/)
- Safe harbor: pay at least 90% of current-year tax, or 100% of prior-year tax (110% if prior-year AGI > $150,000; $75,000 MFS) — [TaxGuidance](https://taxguidance.org/irs-estimated-tax-payment-dates-safe-harbor-and-penalties/); [Taxstra](https://taxstra.com/strategies/estimated-taxes/)
- Annualized income installment method (Form 2210 instructions) allows uneven payments matched to when income was earned — [TaxPayers.net](https://taxpayers.net/guides/estimated-tax-safe-harbor); [Taxspecialty](https://taxspecialty.com/underpayment-penalty-safe-harbor-2026/)

### Inferences
- Practical rule: tax is owed on **realized net gains**, not on withdrawals. Withdrawing $0 does not avoid tax; withdrawing everything does not create extra tax. Set-aside should be computed on net realized gains month-to-date, not on the bank sweep amount.
- Suggested set-aside heuristic (planning, not advice): federal marginal rate (e.g., 22%-24% for typical middle incomes, 32%-37% at high income) + 3.8% NIIT if MAGI > $200k/$250k + state rate (0%-~13%). E.g., single filer at 24% bracket in a 5% state: ~29%; at 35% bracket in California: ~50%+.
- Easiest penalty protection for a new bot: if you have wage withholding, increase W-4 withholding (withholding is treated as paid evenly through the year), or pay 110%/100% of last year's tax in four installments and settle the rest in April.
- Keep the set-aside in USD (not crypto) so a drawdown doesn't eat the tax reserve.

### Gaps
- IRS Pub 505 / Form 1040-ES could not be fetched directly; figures come from secondary summaries consistent with long-standing rules.

## 8. State taxes

### Takeaway
Most states tax capital gains (including short-term crypto gains) as ordinary income. Eight states have no personal income tax; Washington taxes only large long-term gains; Missouri exempted capital gains starting 2025.

### Cited Findings
- Nine states levy no broad personal income tax in 2026: Alaska, Florida, Nevada, New Hampshire, South Dakota, Tennessee, Texas, Washington, Wyoming; Washington does tax large long-term capital gains — [CoinTracker](https://www.cointracker.com/blog/states-with-no-income-tax); [TokenTax](https://tokentax.co/blog/state-by-state-guide)
- Missouri became first state to exempt capital gains from its income tax (effective tax year 2025) — [Count On Sheep](https://countonsheep.com/blog/crypto-taxes-by-state-tx-fl-ca-ny-2026)
- Washington capital gains excise tax: 7% on first $1M of taxable WA capital gains, plus 2.9% on amounts over $1M (9.9% top); 2026 return due date moved to May 1, 2026 — [WA DOR](https://dor.wa.gov/taxes-rates/other-taxes/capital-gains-tax); [WA DOR tiered rates notice](https://dor.wa.gov/forms-publications/publications-subject/special-notices/new-tiered-rates-washingtons-capital-gains-tax); [WA DOR news](https://dor.wa.gov/about/news-releases/2026/capital-gains-excise-tax-returns-due-date-moved-may-1-2026)

### Inferences
- Washington's tax applies to long-term gains, so a short-term bot in WA likely owes no WA capital gains tax (verify; WA DOR). Some sources reference 2026 WA "millionaires tax" legislation — not verified.
- High-tax states (e.g., CA, NY) can add ~10%+ to the set-aside; many states also require their own estimated payments.

### Gaps
- Did not verify each state's rate; WA 2026 legislation beyond capital gains not verified.

## 9. Tools and record-keeping for bot trades

### Takeaway
Use crypto tax software (Koinly, CoinTracker, CoinLedger, etc.) fed by exchange API sync plus CSV exports; keep the bot's own trade log as a backup/reconciliation source. Pricing tiers are by transaction count, so a high-frequency bot may need a top tier.

### Cited Findings
- Entry pricing ~$49/tax year for Koinly and CoinLedger, $59 for CoinTracker; Koinly roughly $49 (100 tx), $99 (1,000), $199 (3,000), $299 (10,000+) — [Koinly comparison](https://koinly.io/blog/coinledger-vs-cointracker/); [Crypto Adventure Koinly review](https://cryptoadventure.com/koinly-review-2026-pricing-transaction-limits-and-tax-report-exports/)
- Koinly supports API sync and CSV upload with negative-balance warnings; CoinTracker leans on CSV uploads that may need reformatting; CoinLedger has missing-basis detection/reconciliation — [Koinly comparison](https://koinly.io/blog/compare-crypto-tax-software/); [Count On Sheep](https://countonsheep.com/blog/coinledger-vs-koinly-2026)
- CoinLedger supports per-wallet (Rev. Proc. 2024-28) basis tracking — [CoinLedger Help](https://help.coinledger.io/en/articles/10309974-how-will-coinledger-support-new-per-wallet-cost-basis-tracking-rules-irs-rev-proc-2024-28)
- Reconcile own records to 1099-DA, since missing basis can be treated as zero — [TaxZerone](https://www.taxzerone.com/resources/information-returns/form-1099-da-instructions/)

### Inferences
- Minimum records per fill (bot should log): UTC timestamp, exchange/account (wallet ID), pair, side, quantity, price, USD value at execution, fee amount and fee asset, order/trade ID; plus deposits/withdrawals (crypto transfers between own wallets and USD bank withdrawals), and any airdrops/staking/interest income (ordinary income at receipt). Store exchange CSV exports annually; retain at least 3 years after filing (longer, e.g. 6-7 years, is prudent given substantial-understatement lookbacks).
- Fees paid in crypto (e.g., BNB, or network gas) can themselves be disposals — log them.
- Confirm the chosen tool's transaction tier fits bot volume (thousands of fills/month could exceed 10,000/yr quickly; top tiers may be needed).

### Gaps
- Could not verify specific bot-platform integrations (e.g., 3Commas, Hummingbot) or current top-tier pricing for CoinTracker/CoinLedger.
- Record-retention period not sourced from IRS primary page in this pass.
