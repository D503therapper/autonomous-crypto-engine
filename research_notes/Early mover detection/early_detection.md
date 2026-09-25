# Early Detection of Big Movers and New Listings: Signals a Free-Data Bot Can Use (as of 2026-09-25)

Scope: how professionals catch +100% to +1000% movers and new listings before they hit "top gainers" lists, restricted to what a paper-trading bot can detect from free/public data, for spot coins tradable on Crypto.com (US user). This note does not repeat the earlier findings in `../Fast crypto trading bot plan/strategy_evidence.md` (sections 3, 4, 5, 6, 7) and `../Fast crypto trading bot plan/practitioner_evidence.md` (section 4); it builds on them. Their headline results still stand: buying after a pump or on listing day loses on average, listing announcements are front-run, and abnormal volume predicts lower (not higher) multi-day returns.

Research method note: the sandbox egress proxy blocked direct fetches of nearly every primary source (arxiv, ACM, USENIX, Springer, PLOS, MDPI, Coinbase, Crypto.com, CoinGecko, DexScreener, GeckoTerminal, Kaiko, Medium, cryptorank, the exchange APIs themselves). Only github.com pages fetched. Everything else comes from web-search result snippets. Figures marked [snippet] were read only from a search snippet and should be verified from the primary source before being hard-coded. Labels: [peer-reviewed], [preprint], [vendor] (data or alert vendor with a product to sell), [news], [anecdotal], [snippet].

---

## 0. Bottom line

1. The only early-detection signals with documented, repeatable, minute-scale lead times are **exchange listing announcements** (Upbit/Bithumb strongest, then Binance, then Coinbase/Robinhood/Kraken) and **pre-announcement derivatives/flow footprints** that precede them by hours. Both are exploited by professional bots; a REST-polling retail bot arrives seconds to minutes late. The workable retail version is not "buy the spike" but "buy the coin on Crypto.com within 1-2 minutes of an Upbit/Binance/Coinbase notice, only if it has not yet moved more than X%, exit within minutes to hours."
2. **Pre-listing positioning is where the money is** in the literature (Xu & Livshits 2019; Hu et al. 2023; Félez-Viñas, Johnson & Putniņš 2022; Kaiko 2026). Buy-in starts about 57 hours before Telegram pumps [preprint, snippet], insiders' cumulative abnormal returns are +15% over 3 days before Coinbase announcements [peer-reviewed working paper, snippet], and open interest and funding rise hours before Robinhood listings [vendor, snippet]. A bot cannot see the Telegram or the insider, but it can see the footprint: gradual price drift + volume hikes + OI/funding creep on an otherwise quiet coin.
3. **Real-time pump detection** (La Morgia et al.) works within one 25-second chunk with ~91% recall on Binance BTC pairs, using rush orders and trade counts, but the authors frame it as a tool to stay OUT; the pump peaks in seconds to a couple of minutes and the median community-pump return at peak is 4-8%. Not a long-entry signal for a REST bot.
4. **On-chain/DEX trending** feeds (DexScreener, GeckoTerminal) are free and fast, but 76% of new DEX tokens in H1 2025 were rug pulls [preprint, snippet] and the DEX-to-CEX conversion is a small fraction (Binance Alpha to Spot 12% [vendor, snippet]). The tradable link for a Crypto.com spot bot is indirect: DEX-trending tokens that already trade on Crypto.com are candidates for a CEX listing cascade (Binance Futures -> Upbit -> Coinbase), each step of which is an announcement event.
5. **Social/attention** signals have weak, mostly daily-horizon evidence and the strong data (LunarCrush social endpoints) is paid. CoinGecko `/search/trending` is free but is itself a lagging "already popular" list.
6. **Order-book imbalance** predicts returns for seconds to a minute, not hours; useful for execution timing, not for finding movers.
7. **Narrative contagion** exists (large caps lead memecoins; a rip in one coin lifts peers), but the sign flips by horizon and the 2025 hyped narratives lost money. Test as a follow-through filter only.

Verdict summary: implement (A) multi-exchange listing-announcement watcher with a "not-yet-moved" gate, (B) pre-listing footprint scanner (drift + volume + OI/funding creep) on Crypto.com tickers, (C) DEX-trending-to-CEX cascade watchlist; test (D) narrative follow-through; skip social scraping and pure pump-chasing.

---

## 1. Exchange listing pipelines: how listings are announced and what moves when

### Evidence summary

**Coinbase.** Since the 2022 insider case (SEC v. Wahi, where a wallet bought two minutes before an announcement [snippet]), Coinbase publishes (i) a listing roadmap (assets under consideration, "roadmap inclusion is not a guarantee"), (ii) a listing decision announcement, and (iii) a trading-start post ("will begin later today if liquidity conditions are met", phased: transfer-only -> limit-order auction/post-only -> full trading). Announcements moved from @CoinbaseAssets to **@CoinbaseMarkets** on X; trading starts during Pacific business hours and is also posted on **status.exchange.coinbase.com** (Atom/RSS available) [news/official, snippet]. Coinbase itself admitted traders detect "small differences in Coinbase API responses to detect when assets might be configured but not yet launched" and on-chain test integrations, and said it would announce before integration work begins to kill that edge [official blog, snippet]. Example lead times: BIRB roadmap-to-trading and INX in Jan 2026 announced the same day trading opened [snippet]. Coinbase listed 110 spot assets in 2025 and 3-6 per month in 2026 [news, snippet].
- Price reactions [all snippet, mixed quality]: roadmap addition BIO +19%, RSC +15% "very shortly after"; SAROS +1,379% "hours after listing" (Oct 2025), APR +155% within 48h. Vendor stats: "78% of roadmap assets list within 90 days, average +34% roadmap-to-listing" and "average listing period ~30 days" [vendor/SEO blogs, unverifiable]. CryptoCompare 2024 [snippet]: 35 roadmap additions produced +18% 24h volume on secondary exchanges and 15-25% higher volatility the following week "not always positive". Older baseline: Messari +91% 5-day (2020-21 bull), Coin Metrics -1% to +14% (already in earlier notes).
- Gains concentrate in the first 24-48h and "many tokens give back 30-60%" after [SEO/news, snippet].

**Binance.** Announcements at binance.com/en/support/announcement/list/48 (new listings catalog) and the internal JSON `https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo=1&pageSize=20` (used by many bots; returns 403 intermittently and is "not intended for public use" [GitHub fabius8/binanceAlert, dev.binance.vision]). Pipeline in 2025-26: **Binance Alpha -> Futures -> Spot**. Alpha 2025: 221 tokens, 105 graduated to Futures, Alpha-to-Spot conversion ~12% [vendor DWF/CMC, snippet]; over 40% of Alpha tokens traded below pre-announcement FDV [news, snippet]. Spot announcements come hours before trading (HYPE: announced Sept 24 2026 morning for 11:00 UTC start; +1.5-1.9% within 10 minutes, then sold off below $90 "traders used it as an exit" [news, snippet]; BANK +60% in the 4 hours between announcement and trading [news, snippet]; Toncoin +11% on announcement Aug 2024). Study of 389 tokens listed in 2024 on six CEXs (CryptoNinjas/Storible, Feb 2025) [vendor/news, snippet]: average +54% surge at listing (Binance +87%), 37% hit ATH at listing and never again, 89% dumped post-listing (average -52%), 98% of Binance listings eventually dumped (average -70% from listing price). Memecoins are the exception cluster: PNUT (Pump.fun launch Nov 2-5 2024, Binance spot Nov 11 = 6-9 days), ACT (~18 days), MOODENG (44 days) rose 4-12x after listing [news, snippet].

**Upbit / Bithumb (Korea).** Strongest and fastest reaction in the market. Notices at upbit.com/service_center/notice; JSON at `https://api-manager.upbit.com/api/v1/announcements` (a public sniper polls it every 2 s and claims the notice lands 10-60 minutes before trading opens [GitHub whatislove666/upbit-listing-sniper]). Bithumb: feed.bithumb.com/notice. Reported reactions [vendor/news, snippet]: 30-100% within minutes on Binance/OKX/Bybit for small caps; CAP +34% in one minute; CFG +180%; SKR +62%; UP +80% then +140% in 24h; PRL +67% same day (Apr 2026); ENA +19%; TAO +8% (large cap). DataMaxi+ [vendor, snippet]: 2025 "maximum expected return" 51.9% (Upbit) and 108.9% (Bithumb), best cases >800% intraday. Fade: Sept 2025 sequence of 7 Upbit listings in 11 days (PUMP, HOLO, OPEN, WLD, FLOCK, RED, WLFI) showed "upper wicks", all back near pre-listing price [news, snippet]; Four Pillars: buying day one on Upbit -69.5% / Bithumb -69.1% average through Feb 2025 (already in earlier notes). Insider evidence: VVV wallet bought 14 hours before the Upbit notice [news, snippet]; Kaiko (older) said Upbit listings pop 10-40% within hours and the effect lasts longer than Coinbase's [vendor, snippet].

**Robinhood.** Lists "with no advance public notice" via newsroom (robinhood.com/us/en/newsroom) and X; Kaiko (May 2026) [vendor, snippet] found across multiple listings (ZEC, SNX, NEAR, LIT) that open interest rose in the hours before the announcement, funding rates climbed days earlier, Hyperliquid wallets took directional exposure ~1 hour before (LIT long at 11:05 UTC, announcement 12:12 UTC, closed 13:00 UTC), and abnormal returns appeared both before and after announcements. Kaiko says this could be inside information or "highly effective front-running strategies based on public indicators". BNB's Robinhood listing (Oct 2025) moved nothing; HYPE's "stirred excitement" [news, snippet]. The official Crypto Trading API has a read-only "products" endpoint but it needs an authenticated key [official docs, snippet].

**Kraken.** Blog category "Asset Listings" (blog.kraken.com/category/product/asset-listings, RSS at blog.kraken.com/feed); wording "X is available for trading" with funding/trading dates; separate API-change RSS at announcements.kraken.tech/rss/public/. Public `https://api.kraken.com/0/public/AssetPairs` returns tradable pairs. No listing-effect statistics found for Kraken beyond "often lead to a bullish run" [SEO, snippet]; earlier notes report Binance/Gemini 5-day returns slightly negative on average.

**Crypto.com.** Announcements at crypto.com/exchange/announcements (titles like "Crypto.com Exchange lists NEWT/USD"); the v1 API has **`public/get-announcements`** returning `id, category, product_type (Spot, Margin, Derivative, ...), announced_at, title, content, instrument_name, impacted_params{spot_trading_impacted,...}, start_time, end_time` [official docs, snippet]. Advance-notice window not documented; third-party alerting sites say "under an hour to several days" across exchanges [vendor, snippet]. No study of a "Crypto.com listing effect" was found; Crypto.com is a follower venue, so the relevant question is #2 (does the Crypto.com price react to other exchanges' announcements).

### Data sources (all free unless stated)

| Exchange | Announcement source | Machine-readable? | Trading-pair endpoint (detect "instrument appeared") |
|---|---|---|---|
| Coinbase | @CoinbaseMarkets (X), coinbase.com/blog, status.exchange.coinbase.com (Atom/RSS) | RSS yes; X needs paid API or scraping | `GET https://api.exchange.coinbase.com/products` (fields `status` online/offline/delisted, `trading_disabled`, `post_only`, `limit_only`, `auction_mode`, `status_message`; ~10 rps/IP) and `GET https://api.coinbase.com/api/v3/brokerage/market/products` (public, IP bucket 10-20 rps) [official docs, snippet] |
| Binance | binance.com/en/support/announcement/list/48; Telegram "Binance Announcements" | JSON bapi (unofficial, 403-prone) | `data-api.binance.vision/api/v3/exchangeInfo` (market-data mirror; `api.binance.com` returns 451 from US IPs) [official FAQ + ccxt issue 15891] |
| Upbit | upbit.com/service_center/notice | `api-manager.upbit.com/api/v1/announcements` (JSON, unofficial but widely polled), also `/api/v1/notices/search?search=...` | `https://api.upbit.com/v1/market/all` |
| Bithumb | feed.bithumb.com/notice | HTML scrape | Bithumb public API market list |
| Kraken | blog.kraken.com/feed (RSS) | RSS yes | `api.kraken.com/0/public/AssetPairs` |
| Robinhood | newsroom + X | HTML scrape | products endpoint needs auth |
| Crypto.com | crypto.com/exchange/announcements | `POST/GET api.crypto.com/exchange/v1/public/get-announcements` (official) | `public/get-instruments` |
| Aggregators | tokenearly.com/api/public/listings.json (no key, unverified freshness) [GitHub awesome-crypto-listing-alerts]; cryptolisting.ws / newlistings.pro WebSocket (paid tiers) [vendor] | | |

Reachability warning: none of these hosts were reachable from this sandbox (proxy policy), so nothing above was live-tested. Test from the real run host first.

### Concrete rule (announcement reaction, follower-venue version)
- Poll every 2-5 s: Upbit announcements JSON, Binance bapi (fallback: scrape list/48), Coinbase status Atom + blog RSS, Kraken RSS, Crypto.com get-announcements. Diff by announcement id.
- Parse symbol(s). Keep only symbols in Crypto.com `public/get-instruments` with USD/USDT spot pairs and 24h `vv` >= $2M.
- Gate: fetch Crypto.com `public/get-ticker` and last 1m candles; require price move since announcement timestamp < +8% (Upbit) / < +4% (Binance/Coinbase) and best-ask spread < 0.5%. If already above the gate, do not chase (the earlier notes' "exit liquidity" finding).
- Enter market/IOC at ask; size 2-5% of equity; take profit at +15% (Upbit) / +8% (others) or trail 1m lows after +5%; hard stop -6%; time stop 60 min (Upbit) / 4 h (Binance, Coinbase); never hold into the actual trading start on the announcing exchange if it is more than 24 h away (fade risk).
- Log announcement-to-detection latency and detection-to-fill slippage for every event; the paper test only means something if these are recorded.

### Expected lead time
Upbit/Bithumb: notice 10-60 min before Korean trading opens; global price reacts within 1 minute of the notice; a 2-5 s poller is 5-30 s behind pro bots. Binance: announcement 2-6 h before trading; most of the move happens in the first 10-15 minutes ("traders who saw it in the first 15 minutes caught the majority" [SEO, snippet]). Coinbase: roadmap can precede trading by days-weeks (median ~30 days claimed by vendors, unverified); the trading-start post precedes trading by hours the same day.

### Verdict
Implement as the #1 event engine, but with the not-yet-moved gate and full latency logging. Expect a large fraction of events to be gated out; the edge (if any) lives in the minority of notices for coins that are illiquid on Korea-facing venues but liquid on Crypto.com.

---

## 2. Cross-exchange lead-lag: does Crypto.com's price lag the announcing exchange?

### Evidence summary
- No study measures Crypto.com specifically. General evidence: after an Upbit notice, the token "on international exchanges (Binance, OKX, Bybit) can surge 30-100% within minutes" and "international traders need time to catch up" [vendor cryptolisting.ws / DataMaxi+, snippet]. Kimchi-premium literature: Korean prices can lead and stay dislocated because capital controls slow arbitrage [news/vendor, snippet]. Arbitrage practitioners: cross-exchange dislocations "persist for seconds to minutes and can be captured using REST APIs", while latency arbitrage needs 100-500 ms WebSocket execution and a home-internet bot 50 ms behind co-located bots "gets a partial fill or nothing" [vendor blogs, snippet].
- Coinbase's own admission that API-response differences leak configured-but-unlaunched assets [official, snippet] and Kaiko's Robinhood findings (OI/funding creep hours before, wallets positioned 1 h before) [vendor, snippet] mean the *first* move on Binance/Hyperliquid often happens before any public announcement; by the time the notice is public, the cross-venue move is the second leg.
- Academic lead-lag (earlier notes): BTC leads alts with a delay; large caps lead small caps; sign flips at some horizons. Microstructure: order-flow imbalance predicts seconds-to-minute returns across BTC/LTC/ETC/ENJ/ROSE on Binance Futures 1-second data 2022-2025 [preprint arXiv 2602.00776, snippet].
- Magnitudes for a follower venue are unknown. Inference: Crypto.com market makers quote off Binance/Coinbase aggregates within sub-second, so the pure price lag is ~0; the exploitable lag is the *liquidity* lag (thin book on Crypto.com re-prices in jumps, wide spread for minutes) which hurts, not helps, a taker.

### Data sources
- Crypto.com: `public/get-ticker` (fields `i,h,l,a,v,vv,oi,c,b,k,t`), `public/get-book` (depth to 50), `public/get-trades`, `public/get-candlestick` (1m..1M); public rate limit ~100 req/s (recalled, unverified) [official docs, snippet].
- Reference venue: OKX or Bybit public REST/WS (no key, US-accessible for market data [snippet]); `data-api.binance.vision` for Binance market data.

### Concrete rule (paper test only)
Record, for each announcement event, the 1-second mid on Crypto.com vs OKX/Bybit for 10 minutes after the notice. Compute lag (cross-correlation peak) and the spread-adjusted "catch-up" available to a taker on Crypto.com at t+5 s, t+15 s, t+60 s. Only if the t+15 s catch-up exceeds 1.5x round-trip cost across >= 30 events does a live rule make sense.

### Expected lead time
Seconds. Realistically zero net of spread for a REST bot.

### Verdict
Test (measurement only). Do not build a lead-lag trading rule until the measurement exists; no source gives a usable magnitude.

---

## 3. On-chain / DEX early signals

### Evidence summary
- Rug-pull base rates: 100,063 new DEX tokens Jan-Jun 2025, 76.4% rug pulls (60,402 pump-and-dump type, 15,606 liquidity withdrawal, 461 freeze-authority) [preprint, snippet]; Solidus Labs 2025: ~13% rug within 90 days (BSC 18%, ETH 9%) [vendor, snippet]; >98% of daily Uniswap V2 mints fraudulent [snippet]; Cernera et al. USENIX 2023: ~60% of BSC/ETH pools rugged on day one, 85.5%/48.8% of sniper operations never exited (already in earlier notes).
- Pump.fun lifespan: average lifespan under a day, graduation rate ~0.7-0.8% (mid-2025) falling to 0.26% (June 2026) [CoinGecko research/The Block, snippet]. Only ~1-1.4% ever reach Raydium/PumpSwap.
- DEX-to-CEX: the documented successes (PNUT 6-9 days, ACT ~18 days, MOODENG 44 days from Pump.fun launch to Binance) [news, snippet] were all Solana memecoins that were DexScreener-trending for days first; "around 80% of memecoins listed on Binance in 2024 saw market caps skyrocket after listing" [news, snippet], versus 11.1% positive for all 2025 Binance listings (earlier notes). Binance Alpha (the formal on-chain-to-CEX funnel): 221 tokens in 2025, ~38-48% reach Futures, ~12% reach Spot [vendor, snippet]; >40% trade below pre-Alpha FDV [news, snippet]. No source gives "% of DexScreener-trending tokens that later list on a CEX"; from the funnel numbers it is well under 5%.
- DexScreener's trending score "is a snapshot of buzz and market activity" and can be bought (paid boosts, "trending services" sold openly) [vendor, snippet], so the trending list is partly pay-to-play.

### Data sources (free, no key)
- DexScreener: `GET https://api.dexscreener.com/token-boosts/top/v1` and `/token-boosts/latest/v1` (60 req/min), `/token-profiles/latest/v1` (60/min), `GET /latest/dex/search?q=` , `/latest/dex/pairs/{chainId}/{pairId}`, `/token-pairs/v1/{chainId}/{tokenAddress}`, `/tokens/v1/{chainId}/{addresses}` (300 req/min). Fields include priceUsd, priceChange{m5,h1,h6,h24}, volume, txns{buys,sells}, liquidity.usd, fdv, marketCap, pairCreatedAt. No historical/OHLC endpoint; no rate-limit headers (pace yourself) [docs via snippet]. Boosted lists are advertising, not organic trending; there is no official "trending" endpoint.
- GeckoTerminal: base `https://api.geckoterminal.com/api/v2/`, `/networks/{network}/trending_pools?duration=5m|1h|6h|24h`, `/networks/trending_pools`, `/networks/{network}/new_pools`, `/networks/new_pools`, `/networks/{network}/pools/{addr}/ohlcv/{timeframe}`; responses carry price_change_percentage, transactions, volume_usd at 5m/1h/6h/24h, reserve_in_usd; ~30 calls/min keyless [docs changelog, snippet]. Trending is "based on web visits and on-chain activity" (organic, not paid).
- CoinGecko onchain (`/onchain/...`) mirrors GeckoTerminal under the Demo key (100 calls/min, 10k/month).
- Birdeye: requires API key; free tier exists but limits not confirmed here. Skip.

### Concrete rule ("DEX heat -> CEX cascade watchlist")
1. Every 5 min pull GeckoTerminal `/networks/trending_pools?duration=1h` (all networks) and DexScreener `/token-boosts/top/v1`.
2. Map base tokens to Crypto.com instruments by symbol + CoinGecko id (`/coins/list?include_platform=true` to match contract addresses; avoid symbol collisions).
3. For tokens that ARE on Crypto.com: add to a "cascade watchlist" if liquidity >= $1M, h24 volume >= $5M, pool age >= 3 days (rug filter), buys/sells ratio 1h > 1.2.
4. Trigger entry only on a *second* confirmation: (a) a Binance Futures/Alpha, Upbit, or Coinbase notice for that token (section 1), or (b) Crypto.com 1h volume >= 4x its 7-day hourly median with price still < +10% from the 24h open.
5. Exit: +25% target, -8% stop, 48 h time stop.
Tokens not on Crypto.com are not tradable and are only logged (useful later for measuring what fraction ever list).

### Expected lead time
Days (PNUT 6-9 days, MOODENG 44 days) between DEX trending and top-tier CEX listing. This is the longest lead of any signal here, but with a very low hit rate.

### Verdict
Implement the watchlist and logging (cheap); trade only through the cascade confirmation. The DEX rug base rate makes standalone DEX signals unsuitable for a spot bot that cannot even buy them.

---

## 4. Social / attention signals

### Evidence summary
- Google Trends: mixed. Past attention explains returns for the five largest coins except ETH in one study; others find Trends predicts volatility not returns, or that returns cause attention rather than the reverse [journal papers, snippet]. Search-based attention shows "consistent long-term predictive power", social-media attention is shorter-lived [thesis, snippet].
- Twitter/Reddit: Steinert & Herff (PLOS ONE 2018) [peer-reviewed]: 181 altcoins, 426k tweets, 71 days; tweet counts and sentiment predict short-term (daily) returns in-sample; no cost analysis. "Wisdom of the crowd signals" (Electronic Markets, July 2025) [peer-reviewed, snippet]: explicit directional social trading signals are followed by short-term abnormal returns in the signal's direction. A Reddit relative-volume/sentiment rule on six majors 2018-2024 claims to beat buy-and-hold [SSRN 2025, snippet; unreplicated]. PulseReddit (2025) benchmarks Reddit for high-frequency crypto agents [preprint].
- LunarCrush sells Galaxy Score/AltRank; claims like "engagement 2x with high sentiment often leads price" are vendor marketing [vendor]. Free tier is market-data only; social endpoints start at $90/month [vendor pricing, snippet].
- No peer-reviewed study found that attention spikes on small caps precede +100% moves by a usable lag; the pump literature says the causality runs from coordinated buying to attention.

### Data sources
- CoinGecko `GET https://api.coingecko.com/api/v3/search/trending` (top 15 coins by search volume in the last 24 h, plus trending NFTs/categories; keyless 5-15 calls/min, Demo key 100/min; data cached 1-5 min) [official support pages, snippet]. `/coins/top_gainers_losers` is paid (Analyst+); `/coins/markets` ordered by volume/price change is free on Demo.
- CoinMarketCap: keyless public API subset at `pro-api.coinmarketcap.com/public-api` (35 endpoints); free Basic key 15k credits/month; whether `/v1/cryptocurrency/trending/latest` and `/trending/gainers-losers` are on the free tier was not confirmed [official, snippet].
- Google Trends: no self-serve API (official API in alpha since July 2025, application only); pytrends archived Apr 2025, trending methods 404 as of Sept 2026, `pytrends-modern` exists; scraping services are paid [snippet]. Skip.
- Reddit: official API needs OAuth app (free for low volume); X API paid. Skip for v1.

### Concrete rule
Attention is a *filter*, not a trigger: when a candidate from sections 1, 3 or 5 fires, record whether the coin was in CoinGecko trending in the prior 24 h. After >= 50 events, compare outcomes with vs without prior trending. Hypothesis to test: prior trending = already crowded = worse follow-through (consistent with the "return causes attention" and lottery-overpricing findings).

### Expected lead time
Daily-horizon studies only; no reliable minute/hour lead.

### Verdict
Skip as a trigger; keep the free CoinGecko trending snapshot as a logged feature.

---

## 5. Order-flow / volume precursors on the CEX itself

### Evidence summary
- Pre-pump footprint [preprint/peer-reviewed, snippet]: Hu et al. (SIGMOD/PACMMOD 2023, 709 Telegram pumps 2019-2022): "coin price gradually increases even tens of hours prior to the pump time, with buy-in starting about 57 hours before", volume stays low then "several volume hikes appear from 48 hours to 1 hour before the pump" similar in size to the pump itself. Xu & Livshits 2019: predicting the target coin from such features gave up to 60% return over 2.5 months (earlier notes). Félez-Viñas, Johnson & Putniņš (SSRN 4184367, 146 Coinbase listings 2018-2022): suspicious tokens carry +15% CAR in the 3 days and +19% in the 7 days before the announcement; 10-25% of listings show it. Kaiko 2026: OI up in the hours before, funding up days before Robinhood listings; wallets positioned ~1 h before. La Morgia dataset notes pumps often start up to 120 s before the Telegram signal because "the admin pre-pumps" [GitHub].
- Volume as a predictor: Garfinkel et al. 2025 (earlier notes) show abnormal volume predicts *lower* multi-day returns cross-sectionally; volume is a conditioning variable. The pre-pump studies show a specific shape: quiet coin, price drifting up on low volume, then discrete volume hikes; that is different from a generic "volume spike".
- Order-book imbalance: predictive for seconds to about a minute, across caps, stable 2022-2025 [preprint, snippet]; useless for hours-ahead detection but useful to time entries once another signal fires.
- OI/funding: Kaiko's Robinhood finding is the only quantified "OI rises hours before" evidence; the BIS carry paper (earlier notes) says high carry predicts crashes. Crypto.com perps expose `oi` in `public/get-tickers` and funding via `public/get-valuations` (`funding_rate`, `estimated_funding_rate`, `funding_hist`, `index_price`, `mark_price`) [official docs, snippet; parameter names recalled, unverified]. Crypto.com perps are not tradable by US retail, but their public data is readable. Coinalyze (free key, 40 calls/min) aggregates OI/funding/liquidations across exchanges (Crypto.com coverage not confirmed) [official docs, snippet].

### Data sources
- Crypto.com: `public/get-tickers` (all instruments in one call, includes `oi` for `-PERP`), `public/get-candlestick?instrument_name=X_USD&timeframe=1m|5m|1h&count<=300`, `public/get-trades`, `public/get-book?depth=50`, `public/get-valuations?instrument_name=X_USD-PERP&valuation_type=funding_rate`.
- Cross-check: OKX `GET /api/v5/public/open-interest`, `/api/v5/public/funding-rate` (public, no key); Bybit `/v5/market/tickers?category=linear` (openInterest, fundingRate).

### Concrete rule ("pre-listing / pre-pump footprint scanner")
Universe: all Crypto.com USD/USDT spot instruments with 30-day median daily `vv` between $300k and $30M (small enough to be listable elsewhere, liquid enough to trade).
Every 15 min compute, per coin:
- D = 48 h return; require +5% <= D <= +25% (drifting, not exploded).
- LowVolDrift = at least 60% of the 1h candles in the last 48 h have volume below the 30-day hourly median (accumulation on low volume).
- Hikes = count of 1h candles in the last 48 h with volume >= 3x the 30-day hourly median; require 2 <= Hikes <= 6.
- Book = bid depth within 1% / ask depth within 1% >= 1.3 (net bids).
- Deriv (if a `-PERP` exists on Crypto.com or OKX/Bybit): OI 24h change >= +20% and funding rising over 3 consecutive periods; if no perp, skip this term.
- Score = sum of satisfied terms; enter top-3 scores >= 3 with 3% of equity each; exit at +30%, -10%, or 5 days; exit immediately at +15% if the move comes with an announcement from section 1 (that is the event; take it).
This is a hypothesis constructed from the studies above, not a parameter set from any paper. Expect a low hit rate and many false positives; the paper test is to find out whether the true positives (later listings/pumps) pay for them.

### Expected lead time
Hours to ~2 days before the announcement/pump (57 h in Hu et al.; 3-7 days in Félez-Viñas et al.; hours for OI in Kaiko).

### Verdict
Implement (paper). It is the only signal that targets the pre-announcement window where the literature says the profits are.

---

## 6. Pump-and-dump detection literature

### Evidence summary
- Kamps & Kleinberg 2018 (Crime Science) [peer-reviewed, snippet]: 1-hour candles, thresholds computed from a 12 h estimation window; "initial" config = volume +25% and price +3% above window, plus "balanced" and "strict" configs; both must trigger; the 25% volume threshold flagged too many events. Detects pumps in hindsight, ~30 minutes best expected latency [snippet]. Pumps revert "after some minutes" (earlier notes).
- La Morgia et al. 2020 (ICCCN) / 2023 (ACM TOIT "The Doge of Wall Street") [peer-reviewed, snippet + GitHub]: Binance BTC-pair pumps organized on Telegram; features over 5/15/25 s chunks: std/avg of *rush orders* (bursts of buy orders in the same second), trade counts, volume, price, max/min price movements, plus time-of-day; Random Forest precision high, recall 91.2% at 25 s falling to 72.9% at 5 s; most important features are rush orders and number of trades; trained on 3 days, tested on 2 weeks; they position it as helping investors "stay out of the market when these frauds are in action". Pump peaks in seconds to ~2 minutes; admin pre-pump up to 120 s before the signal.
- Hamrick et al. (earlier notes): median return at peak 7.7% (transparent) / 4.1% (obscured); many members lose.
- Clough & Edwards 2023 (APWG eCrime, 765 coins) [peer-reviewed, snippet]: average -30% relative to market one year after a pump.
- PumpSense 2026 (arXiv 2605.09431) [preprint, snippet]: 280k Telegram posts, 2,246 pump announcements; LightGBM F1 0.79, BGE-M3 F1 0.83 at 50 ms/sample; LLM target extraction 0.91. Detects from the coordination message, so it is earlier than market-data detectors (which are "tens of seconds" late). Requires joining the Telegram groups.
- Detecting pumps with insiders' anticipated purchases (Econometrics/MDPI 2023) [peer-reviewed, snippet]: insider pre-purchases are detectable ahead of the pump on imbalanced data; details not accessible.
- Profitability of buying after detection: no study reports positive net returns for late entrants; every study reports the opposite (peak within a minute or two, median peak return single-digit percent, one-year -30%). Pre-positioning studies (Xu & Livshits, Hu et al.) are the profitable side.

### Data sources
Crypto.com `public/get-trades` (last N trades, per-second resolution) and WebSocket `trade.{instrument}` / `book.{instrument}` channels for rush-order counting; 1m candles for a Kamps-style fallback.

### Concrete rule
Use as an **exclusion / exit** rule, not entry: on any coin the bot holds or is about to buy, compute over the last 25 s: rush orders (>= 3 buy trades in the same second), trade count z-score vs the trailing hour, 25 s return. If rush-order count >= 5 and 25 s return >= +3% and 24h volume < $20M: flag PUMP; do not open new longs for 30 min; if holding, sell at market once the 5 s return turns negative (the dump starts within a minute or two).

### Expected lead time
Detection lag 5-25 s after the pump starts, while the pump lasts 30-120 s. No positive lead for entry.

### Verdict
Implement as a guard (cheap, protects the listing and footprint strategies from being exit liquidity). Skip as an entry.

---

## 7. Sector / narrative contagion

### Evidence summary
- "Measuring Memecoin Fragility" (arXiv 2512.00377, Nov 2025) [preprint, snippet]: spillover tests show bidirectional transmission; large caps usually lead memecoins; memecoins amplify contagion in bullish phases and absorb shocks in downturns; positive net spillovers from memecoins can precede market-wide corrections.
- Cross-crypto predictability (JEDC 2024) and the "seesaw" (JEF 2023) in earlier notes: small coins react with a delay; large-coin returns can negatively predict small-coin returns next period.
- Practitioner pattern (unquantified): a listing or rip in one AI/meme/RWA coin lifts the category on CoinGecko's category gainers page; the 2024 Binance memecoin listings (PNUT/ACT) coincided with a Solana-meme category melt-up [news, snippet]. No peer-reviewed sector-momentum study with post-2022 data was found (same gap as earlier notes). 2025: memecoins -31.6%, AI -50.2% while being 62.8% of "interest" (earlier notes).

### Data sources
CoinGecko `GET /coins/categories` (category market cap and 24h change; free Demo) and `GET /coins/markets?category=<id>&order=volume_desc` to get peers; map to Crypto.com instruments.

### Concrete rule (test only)
When a section-1 event or a section-5 footprint fires on coin X, fetch X's CoinGecko categories; pick the 3 most liquid peers on Crypto.com in the same narrowest category (exclude BTC/ETH/stables). Paper-buy peers 15 minutes after the leader's move only if the peer is < +3% since the event and its 1h volume >= 2x median. Exit +10% / -5% / 6 h. Compare against the leader trade itself.

### Expected lead time
Minutes to a day (limited-attention delay for small caps); direction not guaranteed.

### Verdict
Test. Low priority; do not build until sections 1 and 5 have event logs to attach it to.

---

## Ranked top-5 early-detection signals to build

Ranking criterion: documented lead time x detectability from free endpoints x tradability on Crypto.com spot. All specs are paper-trade hypotheses; thresholds are mine unless a source is cited.

### 1. Multi-exchange listing-notice reactor with a not-yet-moved gate (section 1)
- Inputs: Upbit announcements JSON (poll 2 s), Binance bapi list (5 s; scrape fallback), Coinbase status Atom + blog RSS (10 s), Kraken RSS (30 s), Crypto.com `public/get-announcements` (10 s); Crypto.com `public/get-instruments`, `get-ticker`, `get-book`.
- Trigger: new announcement id whose title matches listing patterns (Upbit: "신규 거래지원 안내"/"Market Support"; Binance: "Binance Will List"/"Binance Futures Will Launch"; Coinbase: "will list"/"trading ... will begin"/roadmap adds; Kraken: "available for trading").
- Filters: symbol tradable on Crypto.com; 24h `vv` >= $2M; spread <= 0.5%; move since announcement `t0` <= +8% (Upbit/Bithumb) or <= +4% (others); not already listed on the announcing venue (skip "adds pair" notices for coins the venue already lists).
- Entry: IOC market buy, 3% equity (Upbit) / 2% (others), max 2 concurrent.
- Exit: TP +15%/+8%; stop -6%; trail 1m lows after +5%; time stop 60 min (Upbit), 4 h (Binance/Kraken), or Coinbase trading-start post (whichever first).
- Log: t0, t_detect, t_fill, fill vs mid at t0, peak in 60 min, MAE/MFE.
- Endpoint to poll: `https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=trade` (parameter names from a public bot; unverified), `https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo=1&pageSize=20`, `https://status.exchange.coinbase.com/history.atom`, `https://blog.kraken.com/feed`, `https://api.crypto.com/exchange/v1/public/get-announcements`.
- Expected lead: 0-2 min after notice; notice 10 min-6 h before trading.

### 2. Pre-listing / pre-pump footprint scanner (section 5)
- Inputs: Crypto.com `public/get-tickers` (every 60 s, all instruments), `public/get-candlestick` 1h x 720 and 1m x 300 for candidates, `public/get-book` depth 50, `oi` from `-PERP` tickers, `public/get-valuations` funding; OKX `/api/v5/public/open-interest` as fallback.
- Universe: spot USD/USDT pairs with 30-day median `vv` $300k-$30M.
- Score terms (each 1 point): 48 h return in [+5%, +25%]; >= 60% of last 48 hourly candles below 30-day hourly median volume; 2-6 hourly volume hikes >= 3x median in last 48 h; bid/ask 1%-depth ratio >= 1.3; perp OI +20% in 24 h with funding rising 3 periods (skip term if no perp).
- Entry: top 3 by score with score >= 3, 3% equity each, limit at best bid + 1 tick (maker), cancel after 5 min.
- Exit: +30% TP, -10% stop, 5-day time stop; if a signal-1 event fires on the coin, switch to signal-1 exits.
- Expected lead: hours to 2 days before an announcement/pump (Hu et al. 57 h; Félez-Viñas 3-7 d; Kaiko hours).

### 3. DEX-heat to CEX-cascade watchlist (section 3)
- Inputs: GeckoTerminal `/networks/trending_pools?duration=1h` and `/networks/new_pools` (every 5 min, keyless 30/min), DexScreener `/token-boosts/top/v1` (every 5 min, 60/min), CoinGecko `/coins/list?include_platform=true` (daily) for contract-to-coin mapping, Crypto.com instruments.
- Watchlist admission: base token maps to a Crypto.com spot pair; liquidity >= $1M; h24 volume >= $5M; pool age >= 3 days; 1h buys/sells >= 1.2; appears in trending on >= 2 consecutive pulls.
- Trigger: watchlist coin gets (a) any signal-1 notice, or (b) Crypto.com 1h volume >= 4x 7-day hourly median with price < +10% vs 24h open.
- Entry/exit: 2% equity; +25% TP, -8% stop, 48 h time stop.
- Expected lead: days (6-44 days in the 2024 memecoin cases) with a low hit rate; the value is the pre-built shortlist that makes signal 1 faster and signal 2 more targeted.

### 4. Pump guard and dump exit (section 6)
- Inputs: Crypto.com WebSocket `trade.{instrument}` (or `public/get-trades` polled every 5 s) for held/candidate coins.
- Detector (25 s window): rush orders (>= 3 buys in one second) >= 5, trade count z >= 3 vs trailing hour, 25 s return >= +3%, 24h `vv` < $20M -> PUMP flag.
- Action: block new entries for 30 min; if holding, market-sell when the 5 s return turns negative or +2 min after the flag, whichever first.
- Expected lead: none for entry; 5-25 s detection lag; prevents being exit liquidity.

### 5. Narrative follow-through (section 7), test only
- Inputs: CoinGecko `/coins/categories`, `/coins/markets?category=`; Crypto.com tickers.
- Trigger: signal 1 or 2 fires on leader X; 15 min later, buy up to 3 same-category peers on Crypto.com that are < +3% since t0 with 1h volume >= 2x median.
- Exit: +10% / -5% / 6 h.
- Expected lead: minutes to a day; sign uncertain (seesaw evidence); evaluate only against the leader trade.

Skip list: LunarCrush/X/Reddit scraping (paid or weak), Google Trends (no API), CoinGecko trending as a trigger (lagging), Binance Alpha "graduation" chasing (>40% below pre-announcement FDV), buying on trading-start day of any exchange (earlier notes), buying anything >+30% in 24 h (earlier notes).

---

## Gaps and verification needed
- Not one endpoint above was live-tested (proxy policy). First task on the run host: curl each, record real latency, rate limits, US geo-blocks (api.binance.com returns 451 from US; use data-api.binance.vision), and whether api-manager.upbit.com tolerates 2 s polling without 429/403.
- Crypto.com `get-announcements` request parameters, categories and typical advance-notice window are undocumented in what I could read.
- Coinbase Exchange `/products` "configured but not launched" leak: Coinbase said in 2022 it would close this; whether new products still appear in `/products` with `status: offline` before the announcement should be measured (poll every 30 s, diff, timestamp against @CoinbaseMarkets).
- The Upbit/Bithumb magnitudes (30-100% in minutes; 51.9%/108.9% "maximum expected return") are vendor figures; the Four Pillars -69% day-one figure is a secondary source. Build the event log and measure on Crypto.com prices directly.
- Kaiko's Robinhood front-running report (May 2026) was read only via news snippets; the exact abnormal-return numbers were not visible.
- Hu et al. "57 hours" and Félez-Viñas "+15%/3 days" are the load-bearing numbers for signal 2; both were read from snippets. Re-read the papers (arXiv 2204.12929; SSRN 4184367) before tuning thresholds.
- No source quantifies the fraction of DEX-trending tokens that reach any CEX, nor Crypto.com's own listing effect. Both can be measured from the logs this plan produces.
