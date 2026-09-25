# Exchanges, APIs, Fees and Infrastructure for a US Retail Crypto Trading Bot (as of 2026-09-25)

Research method note: the sandbox egress proxy blocked direct fetches of exchange-docs.crypto.com, crypto.com, api.crypto.com, coinbase.com, kraken.com and docs.ccxt.com. Findings below come from web-search result snippets (mostly secondary sources: review sites and aggregators) plus the primary-source titles/URLs they surfaced. A live test of `api.crypto.com/exchange/v1/public/*` from this sandbox was refused by the proxy (organization policy), so that is NOT evidence of Crypto.com geo-blocking. Numbers should be re-verified on the official pages before being hard-coded.

## Crypto.com App: API trading and effective costs

### Takeaway
The Crypto.com App (retail) has no public trading API; bots must use the Crypto.com Exchange or a different venue. App trades carry a variable spread (reported ~0.5% to 2%+) and card purchases add ~1.5% to 2.99%; the paid Level Up subscription (from $4.99/month) reduces fees.

### Cited Findings
- The Crypto.com App is available in 49 US states plus territories; New York is the exception — [Crypto.com Help Center: In which U.S. states the App is available](https://help.crypto.com/en/articles/2692288-in-which-u-s-states-the-crypto-com-app-is-available)
- A variable spread fee is charged on App swaps, estimated at 0.5% to 2%+ depending on market conditions — [GOBankingRates: Crypto.com fees](https://www.gobankingrates.com/investing/crypto/crypto-com-fees/)
- Bank card / Apple Pay / Google Pay purchase processing fees typically range from 1.5% to 2.99% — [GOBankingRates](https://www.gobankingrates.com/investing/crypto/crypto-com-fees/)
- Level Up is a paid subscription with three tiers starting at $4.99/month that reduces fees, to zero at some tiers per the reviewer — [GOBankingRates](https://www.gobankingrates.com/investing/crypto/crypto-com-fees/)
- A secondary source frames it as "the same $1,000 buy costs $8.00 in the App and $5.00 on the Exchange", i.e. App ~0.8% all-in versus Exchange 0.5% taker — [MEXC Learn: Crypto.com fees explained 2026](https://www.mexc.com/learn/article/crypto-com-fees-explained-2026-why-does-the-same-1-000-buy-cost-8-00-in-the-app-and-5/1) (competitor-hosted article, so treat with caution)
- One reviewer states that "some features of margin trading, API-based trading, and some OTC services are not available to US residents" — [GOBankingRates](https://www.gobankingrates.com/investing/crypto/crypto-com-fees/) (this conflicts with the January 2025 US launch of the Exchange with APIs, below; the statement is probably outdated or refers to the App)

### Inferences
- Moving from the App to any API-driven exchange order book saves roughly 0.3% to 1.5%+ per trade. That matters for a bot that trades often.
- The Visa card is irrelevant to bot trading. It only matters for how the user funds the account, and card funding (1.5% to 2.99%) should be avoided in favor of ACH or wire.

### Gaps
- I could not fetch the official crypto.com/us fee page or the current Level Up tier prices and benefits ($4.99 is the only price I confirmed). The Level Up tier names, prices and exact fee reductions for 2026 need to be checked on crypto.com/us.
- No official statement was found on whether the Crypto.com Visa card charges a fee for crypto purchases. The 1.5% to 2.99% figure applies to buying with a bank card.

## Crypto.com Exchange: US availability, API, fees, CRO discounts, minimums

### Takeaway
Crypto.com Exchange launched in the US in January 2025 for "institutional and advanced traders" and supports REST, WebSocket and FIX APIs. Whether an ordinary US retail App user can open an Exchange account depends on the state and on eligibility, which I could not confirm per state. Entry-tier fees are reported at 0.25% maker / 0.50% taker. CRO balances or lockups lower them (e.g., 0% maker / 0.44% taker at entry tier with a large CRO holding).

### Cited Findings
- Crypto.com Exchange launched in the US in January 2025 for "U.S. institutional and advanced traders", alongside the existing retail App. Funding is by Fedwire. Retail users "in supported jurisdictions" continue to use the App — [Crypto.com: Crypto.com Exchange Set for U.S. Launch](https://crypto.com/us/company-news/crypto-com-exchange-set-for-u-s-launch); [The Paypers](https://thepaypers.com/crypto-web3-and-cbdc/news/cryptocom-launches-exchange-in-the-us)
- "Eligible users of the Crypto.com Exchange in the U.S. can begin onboarding at Crypto.com/Exchange or the Crypto.com Exchange app" — [Crypto.com launch post via search snippet](https://crypto.com/us/company-news/crypto-com-exchange-set-for-u-s-launch)
- The Exchange API supports spot, margin, perpetuals and futures over REST, WebSocket and FIX 4.4. Trading bots are an explicitly supported use case — [Crypto.com Exchange API page](https://crypto.com/exchange-pro/en-US/api); [Crypto.com Exchange institution page](https://crypto.com/exchange/institution)
- API keys can be restricted to whitelisted IPs — [Crypto.com Help Center: API](https://help.crypto.com/en/articles/3511424-api)
- Entry tier (<$10k 30-day volume): 0.25% maker / 0.50% taker — [Coin Bureau review](https://coinbureau.com/review/crypto-com-review); [CryptoSlate](https://cryptoslate.com/crypto-exchanges/crypto-com-exchange-review/); [Crypto.com Help: Applicable Fees](https://help.crypto.com/en/articles/4894437-applicable-fees)
- Holding 50,000+ CRO on the Exchange is reported to set maker to 0% and cut taker by 12% to 0.44% at entry tier. Another source says staking 5,000 CRO cuts fees to 0.0725%. These CRO claims conflict and probably come from different eras of the program — [CryptoSlate](https://cryptoslate.com/crypto-exchanges/crypto-com-exchange-review/); [Coincub](https://coincub.com/exchanges/crypto-com/)
- Reported derivatives base fees are 0.02% maker / 0.04% taker (global Exchange, not necessarily US) — [GOBankingRates](https://www.gobankingrates.com/investing/crypto/crypto-com-fees/)

### Inferences
- For a $500 to $10k account, Crypto.com Exchange at 0.25/0.50% is no cheaper than Kraken Pro (0.25/0.40%) and costs more than Binance.US's promotional zero or near-zero fees. Buying CRO for fee discounts adds token price risk that is probably not worth it at this account size.
- "Institutional and advanced traders" wording plus Fedwire-only funding suggests that retail onboarding is limited. The user should check eligibility in the Exchange app before building around it.

### Gaps
- **State list for the US Exchange:** not found. The help center says the App excludes NY. The Exchange is likely at least as restrictive, but this is unconfirmed.
- **Minimum order sizes:** not verified. They are per-instrument (`min_quantity` / `qty_tick_size` in `public/get-instruments`) and were not retrievable here.
- The 2026 CRO lockup / "Level" fee table could not be fetched from the official help center.

## Crypto.com Exchange public API v1 (api.crypto.com/exchange/v1): endpoints, limits, geo-blocking

### Takeaway
The official docs (exchange-docs.crypto.com) were unreachable from this sandbox, so the endpoint details below are only partly verified. Public market data covers instruments, candlesticks, tickers, book, trades, and valuations (mark/index/funding) for perpetuals. No source was found that documents geo-blocking of US cloud IPs, and this remains an open risk to test from the target host.

### Cited Findings
- The v1 docs describe `public/get-candlestick` as retrieving "candlesticks (k-line data history) over a given period for an instrument" — [Crypto.com Exchange API v1 docs](https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html)
- The OLD (pre-v1) Exchange API capped candlestick requests at 300 entries (`pageSize` up to 300; last 300 returned when `endIdx` is empty) — [Crypto.com Exchange V1 API Doc [Old]](https://crypto.com/exchange-docs-v1). v1 behavior may differ.
- CCXT has a `cryptocom` exchange class — [CCXT docs: cryptocom](https://docs.ccxt.com/docs/exchanges/cryptocom)
- Separate institutional (US) API docs exist: "Exchange Institutional API v1" — [exchange-docs.crypto.com institutional](https://exchange-docs.crypto.com/exchange/v1/rest-ws/index-insto-8556ea5c-4dbb-44d4-beb0-20a4d31f63a7.html). This suggests the US entity may use a different base URL or host than the global api.crypto.com.

### Inferences
- A separate "Institutional API v1" doc for the US launch suggests that US accounts may trade through a different endpoint or instrument set than global `api.crypto.com/exchange/v1`. Global perpetual instruments such as `BTCUSD-PERP` are probably not tradable by US retail even if their market data is readable.
- Public market data (candles, tickers, funding) can usually be read without an account, so a paper-trading bot could use Crypto.com data even if the user cannot trade on the Exchange. This should be verified from the actual run host (GitHub Actions / VPS).

### Gaps (unverified, from prior knowledge — must check official docs)
- Believed but NOT verified here: v1 `public/get-candlestick` params `instrument_name`, `timeframe` (1m, 5m, 15m, 30m, 1h, 2h, 4h, 12h, 1D, 7D, 14D, 1M), `count` (default 25, max ~300) and `start_ts`/`end_ts` for paging. Other public endpoints are `public/get-instruments`, `public/get-tickers`, `public/get-book` (depth up to 50), `public/get-trades`, and `public/get-valuations` (valuation_type `index_price`, `mark_price`, `funding_hist`, `funding_rate`, `estimated_funding_rate`). Open interest is believed to appear in ticker data for derivatives, not in a dedicated endpoint. The rate limit is believed to be about 100 requests per second per IP for public market data, with lower per-method limits for private endpoints.
- Maximum historical depth of candles: unknown.
- Geo-blocking of US or cloud IPs (GitHub Actions on Azure, AWS us-east): no documentation or user reports were found either way. The sandbox 403 above came from our own proxy, not from Crypto.com. Recommendation: run a one-off `curl` from a GitHub Actions runner and from the chosen VPS before committing.

## Alternatives with US retail API trading: Coinbase, Kraken, Binance.US, Gemini, Alpaca

### Takeaway
For a $500 to $10k account, Binance.US currently has the lowest fees (zero or near-zero on many pairs since January/April 2026) but is unavailable in NY, TX and GA. Kraken Pro (0.25/0.40%) is the cheapest broadly available mainstream option. Coinbase Advanced (0.40/0.60% at <$10k) has the widest altcoin list and best tooling, but costs the most. Alpaca charges 0.15/0.25% and offers free paper trading with a small crypto list. Gemini ActiveTrader charges 0.20/0.40%.

### Cited Findings
- **Coinbase Advanced Trade:** 0.40% maker / 0.60% taker for <$10k 30-day volume, falling to 0.00%/0.05–0.08% at $100M+ tiers. There is no spread on order-book orders. Tiers update hourly using trailing volume. Eligible stablecoin pairs have 0% maker — [Datawallet: Coinbase fees](https://www.datawallet.com/crypto/coinbase-fees); [TokenEcho](https://tokenecho.io/guides/coinbase-advanced-trade-fees/); [BitDegree](https://www.bitdegree.org/crypto/tutorials/coinbase-fees). (One snippet cited a 0.60/1.20% "base tier", which conflicts with other sources and may refer to a $0–$1k tier or an old schedule. Verify on coinbase.com/advanced-fees.)
- **Coinbase sandbox:** a static Advanced Trade API sandbox returns production-formatted responses for Accounts and Orders endpoints only, at `https://api-sandbox.coinbase.com/api/v3/brokerage/{resource}`. It is not a full paper-trading engine — [Coinbase Developer Docs: Advanced Trade API Sandbox](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/sandbox)
- **Kraken Pro:** 0.25% maker / 0.40% taker under $10k monthly volume, then 0.20%/0.35% above $10k, down to 0%/0.05% at high volume — [CryptoVantage Kraken review](https://www.cryptovantage.com/best-crypto-exchanges/kraken/); [Kraken fee schedule](https://www.kraken.com/features/fee-schedule)
- Kraken is available in most but not all US states, and margin/futures may be restricted by location. Stocks are available "except ME or NY" — [CryptoVantage](https://www.cryptovantage.com/best-crypto-exchanges/kraken/). (NY residents: Kraken historically does not serve NY for crypto. Verify.)
- Kraken offers a futures demo environment at demo-futures.kraken.com. Kraken's `kraken-cli` includes spot and futures paper engines against live prices — [krakenfx/kraken-cli GitHub](https://github.com/krakenfx/kraken-cli)
- **Binance.US:** USD deposits and withdrawals were restored with a phased rollout and zero-fee trading on select pairs launched in January 2026. In April 2026 it "slashes spot trading fees to near zero for all users". It lists 160+ assets. Zero-maker-fee pairs include BTC, ETH, SOL, BNB, ADA, AVAX, DOT, NEAR and SUI against USD. It is unavailable in NY, GA and TX, and KS and WI are crypto-only — [Binance.US blog: USD services return](https://blog.binance.us/usd-services-return/); [Business Wire, Apr 2026](https://www.businesswire.com/news/home/20260422787826/en/Binance.US-Slashes-Spot-Trading-Fees-to-Near-Zero-for-All-Users); [Blockchain Reporter](https://blockchainreporter.net/binance-us-restores-usd-services-and-launches-zero-fee-trading-in-2026/)
- **Gemini ActiveTrader:** 0.20% maker / 0.40% taker at base, and 0.15%/0.30% from $10k monthly volume — [BitDegree: Gemini fees](https://www.bitdegree.org/crypto/tutorials/gemini-fees); [Coin Bureau](https://coinbureau.com/review/gemini)
- **Alpaca Crypto:** maker/taker fee schedule (commonly 0.15% maker / 0.25% taker at the lowest tier). Paper trading is free with simulated funds — [Alpaca docs: Crypto Spot Trading Fees](https://docs.alpaca.markets/us/docs/crypto-fees); [Alpaca Crypto Fee Schedule PDF](https://files.alpaca.markets/disclosures/library/AlpacaCryptoLLCFeeDisclosure.pdf); [BrokerChooser](https://brokerchooser.com/broker-reviews/alpaca-trading-review/alpaca-trading-fees)

### Inferences
- **Cheapest:** Binance.US, if the user's state allows it and the promo fees persist, since promotions can end. **Best balance:** Kraken Pro, with low fees, a mature API, CCXT/Freqtrade/Hummingbot support and broad state coverage. **Widest alts and best docs:** Coinbase Advanced, at the price of 0.6% taker.
- On a round trip at taker rates: Coinbase ~1.2%, Crypto.com Exchange ~1.0%, Kraken ~0.8%, Gemini ~0.8%, Alpaca ~0.5%, Binance.US ~0 to 0.2%. At these costs, high-frequency strategies are not viable on small accounts, and using maker (post-only limit) orders helps a lot.
- **Free paper trading:** Alpaca (full paper account) and Kraken (CLI paper engine; futures demo) are the best built-in options. Freqtrade's dry-run mode works on any supported exchange's live data.

### Gaps
- Exact Alpaca tier numbers were not confirmed from the doc text (the 0.15/0.25% figure is from the query context and aggregator snippets, and one source says a flat 0.25%).
- Binance.US post-April-2026 fee table details are unknown.
- Altcoin counts for Kraken, Coinbase and Gemini in 2026 were not found.

## US retail access to perpetual futures (brief)

### Takeaway
Yes. Since July 21, 2025, Coinbase Financial Markets offers CFTC-regulated "perpetual-style" nano BTC/ETH futures to US retail with up to 10x leverage, adding SOL and XRP on August 18, 2025. Kraken has announced CFTC-regulated US perps. Crypto.com's CDNA received CFTC margined-derivatives approval on September 26, 2025.

### Cited Findings
- Coinbase: US perpetual-style futures via CFM from July 21, 2025. Nano BTC (0.01 BTC) and nano ETH (0.10 ETH) contracts with 5-year expiries, 24/7 trading, a funding mechanism and up to 10x leverage — [Coinbase blog: Perpetual futures have arrived in the U.S.](https://www.coinbase.com/blog/perpetual-futures-have-arrived-in-the-us); [Coinbase: Coming July 21](https://www.coinbase.com/blog/coming-july-21-us-perpetual-style-futures)
- Nano XRP and SOL perps from August 18, 2025 — [MLQ.ai](https://mlq.ai/news/coinbase-to-launch-regulated-nano-xrp-and-sol-perpetual-futures-for-us-traders/)
- Crypto.com | Derivatives North America received CFTC approval for margined derivatives (Sept 26, 2025) — [Crypto.com news](https://crypto.com/us/company-news/cryptocom-obtains-cftc-margined-derivatives-licenses)
- Kraken announced CFTC-regulated perpetual futures for US traders — [Kraken Blog](https://blog.kraken.com/product/kraken-derivatives/announcing-cftc-regulated-us-perps)

### Inferences
- A futures bot for US retail is feasible on Coinbase CFM (via the Advanced Trade API). Futures accounts have separate eligibility and state rules, and leverage adds liquidation risk that a small-account bot should avoid at first.

### Gaps
- Whether Crypto.com CDNA perps are live for retail via API, and in which states, is not confirmed. API access details for Kraken US perps were also not found.

## Infrastructure: running a Python bot 24/7 cheaply

### Takeaway
GitHub Actions cron works for low-frequency bots (every 15 to 60 minutes) but is unreliable for anything time-sensitive: the minimum interval is 5 minutes and delays of 5 to 30+ minutes are common. It is free only in public repos, which would expose strategy code, while private repos quickly exhaust the 2,000 free minutes. A cheap always-on VPS or a Raspberry Pi is better for 24/7 or WebSocket bots. Hetzner raised prices in 2026, and Oracle's free ARM tier was halved.

### Cited Findings
- GitHub Actions `schedule`: the minimum interval is 5 minutes, so `*/5 * * * *` is the fastest. Runs can be delayed under high load, with 5 to 30 minute delays common. Scheduled workflows in **public** repos are auto-disabled after 60 days without repository activity — [Cronuru guide](https://cronuru.com/guides/github-actions-scheduled-workflows); [cronbuilder.dev](https://cronbuilder.dev/blog/github-actions-cron-schedule.html); [Runhooks](https://runhooks.app/blog/github-actions-scheduled-workflows-unreliable/)
- A `*/5` cron fires 8,640 times per month. At 30 seconds per job that is about 4,320 billed minutes, since jobs are billed in whole minutes, which exceeds the free private-repo quota — [cronpreview.com](https://cronpreview.com/guides/github-actions-cron-in-production)
- GitHub pricing changes: hosted-runner prices were cut by up to ~39% on January 1, 2026. Free included minutes for private repos are unchanged (2,000 per month on the Free plan). Public-repo usage on standard runners remains free. The proposed $0.002/min self-hosted runner charge (March 2026) was shelved indefinitely after backlash — [GitHub Changelog: reduced pricing](https://github.blog/changelog/2026-01-01-reduced-pricing-for-github-hosted-runners-usage/); [GitHub: 2026 pricing changes](https://github.com/resources/insights/2026-pricing-changes-for-github-actions); [SamExpert](https://samexpert.com/github-actions-pricing-backlash-2026/)
- Hetzner: price increases on April 1, 2026 (30–37%) and June 15, 2026. CX22 went from €3.79 to €4.44/month and CAX11 from €4.49 to €5.99. As of September 4, 2026, Hetzner reportedly marked shared-vCPU plans (CX23–CX53, CAX11–CAX41) as "not available" — [Hetzner Docs: Price Adjustment 15 June 2026](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/); [Northflank](https://northflank.com/blog/hetzner-cloud-server-price-increases); [privatedevops.com](https://privatedevops.com/news/hetzner-june-2026-cloud-price-increase-what-to-do)
- Oracle Cloud Always Free: Ampere A1 was cut from 4 OCPU / 24 GB to 2 OCPU / 12 GB effective June 15, 2026, without an announcement. Idle instances may be reclaimed if 95th-percentile CPU, network and memory are all below 20% over 7 days, and a lightweight bot would trigger this — [InfoQ, July 2026](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/); [Oracle Always Free docs](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)

### Inferences
- **Cheapest viable options:** (a) a public GitHub repo with secrets in GitHub Secrets and a 15-minute cron, at $0, for a paper or low-frequency bot, with a keep-alive commit to avoid the 60-day disable; (b) a ~$4–6/month VPS (Hetzner if available, otherwise DigitalOcean/Vultr ~$4–6) for real 24/7 operation; (c) a Raspberry Pi at home (one-time ~$50–100 cost, residential IP, depends on home internet).
- Oracle Free is risky for a mostly idle bot because of the idle-reclaim rule, and a pay-as-you-go upgrade is commonly recommended to avoid reclamation (unverified).
- IP whitelisting on exchange API keys is impossible with GitHub-hosted runners, whose IPs rotate. That argues for a VPS with a static IP for live trading.

### Gaps
- Current DigitalOcean and Vultr lowest droplet prices for 2026 were not verified (historically $4–6/month).
- The claim that Hetzner shared plans were "not available" comes from one secondary source. It may mean temporarily sold out.

## Open-source frameworks: Freqtrade, Hummingbot, CCXT, Jesse

### Takeaway
CCXT (a library) supports Crypto.com, Coinbase Advanced and Kraken. Freqtrade (built on CCXT) officially supports Kraken and Coinbase. Crypto.com is not on its officially tested list. Hummingbot has maintained Coinbase Advanced Trade and Kraken connectors and is geared to market making. A framework gives backtesting, dry-run, Telegram control and risk handling for free, whereas custom code gives full control over Crypto.com specifics.

### Cited Findings
- Freqtrade is free and open source, uses CCXT to connect to exchanges, and keeps an exchange-specific notes page and a list of officially and community-tested exchanges — [Freqtrade docs](https://www.freqtrade.io/en/stable/); [Freqtrade Exchange-specific notes](https://www.freqtrade.io/en/stable/exchanges/)
- CCXT supports Coinbase Advanced Trade endpoints for orders, balances and market data — [Bitget Academy (secondary)](https://www.bitget.com/academy/does-freqtrade-support-integration-with-coinbase-in-america-2026-comprehensive-guide)
- CCXT has a `cryptocom` class — [CCXT docs: cryptocom](https://docs.ccxt.com/docs/exchanges/cryptocom)
- Hummingbot connector `coinbase_advanced_trade` supports Coinbase spot, and a Kraken spot connector exists with a paper-trade mode — [Hummingbot: Coinbase](https://hummingbot.org/exchanges/coinbase/); [Hummingbot: Kraken](https://hummingbot.org/exchanges/kraken/)

### Inferences
- A good path is to prototype and paper-trade with Freqtrade (dry-run + Telegram built in) on Kraken or Coinbase, or with Alpaca's paper API. Use custom CCXT code only if the strategy needs Crypto.com-specific data such as funding or valuations.
- Jesse: no current exchange-support info was found. Historically its live trading was a paid plugin, which is unverified here.

### Gaps
- The current Freqtrade supported-exchange list (whether `cryptocom` is listed or tested) could not be fetched. Jesse's exchange list and licensing for 2026 were not found.

## API key security best practices

### Takeaway
Create trade-only keys with withdrawals disabled, whitelist the static IP of a VPS, store secrets outside the code (GitHub Secrets or `.env` with 600 permissions), use a subaccount holding only the bot's capital, and rotate keys.

### Cited Findings
- Crypto.com Exchange API keys support optional IP restrictions — [Crypto.com Help Center: API](https://help.crypto.com/en/articles/3511424-api)
- Scheduled GitHub workflows can store secrets in the repo (standard practice). Public-repo usage is free — [GitHub pricing changes](https://github.com/resources/insights/2026-pricing-changes-for-github-actions)

### Inferences
- Standard practice (not source-verified here): grant only the "trade" and "read" permissions, never "withdraw" or "transfer". Enable 2FA on the account. Use an exchange subaccount or a dedicated account to cap the loss if a key leaks. Never log secrets. Pin dependency versions. Coinbase CDP keys use ECDSA/Ed25519 key files that should be treated like SSH keys.

### Gaps
- Official best-practice pages from Coinbase and Kraken were not fetched (their domains were blocked).

## Phone alerting: Telegram, ntfy, Pushover, email, Twilio

### Takeaway
Telegram Bot API (free, two-way, and built into Freqtrade) or ntfy.sh (free, a single HTTP POST, no account) are the easiest options. Pushover is a one-time $5 purchase. Twilio SMS now requires 10DLC registration fees and is the most hassle for US numbers.

### Cited Findings
- The Telegram Bot API is free, and costs only come from hosting and add-ons — [Optimum Web: Telegram Bot API pricing 2026](https://www.optimum-web.com/blog/telegram-bot-api-pricing-2026-complete-guide/)
- ntfy.sh is free and open source and can be used on the public ntfy.sh server or self-hosted — [GitHub: crypto-mobile-notifications-bot](https://github.com/dasunpamod/crypto-mobile-notifications-bot)
- Pushover is a one-time $5 app purchase, free up to 10,000 notifications per month — [DEV Community: Pushover](https://dev.to/selfhostingsh/pushover-nn6)
- Twilio US A2P 10DLC requires a $4.50 one-time brand registration (updated August 2025) plus $1.50–$10 per month campaign fees, on top of per-message costs — [Apidog: Twilio SMS API cost 2026](https://apidog.com/blog/twilio-sms-api-cost/)

### Inferences
- On public ntfy topics anyone who guesses the topic name can read the messages, so use a long random topic. Telegram is best if the user wants two-way commands (/status, /stop).

### Gaps
- Email via SMTP (e.g., a Gmail app password) was not researched for current limits.
