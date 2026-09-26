"""DEX LEGENDS study: would the live DEX rules have caught and ridden SHIB / PEPE / BONK / WIF ... and survived
LUNA / FTT / SQUID-style collapses?  Which exit add-on (protection trail, runner trail, concentration cap,
take-profits at big multiples) makes the most money across the legends AND the duds / rugs together?

Owner's TODO in results/research_log.md ("DEX exit study applied": LEGENDS, CONCENTRATION CAP, LEGENDS SCREEN
CHECK, TAKE-PROFITS AT BIG MULTIPLES).

  1. data      for every famous coin (legends, collapses, rugs, dead memes) every free price source is probed
               from the runner and logged: CryptoCompare histoday/histohour, Yahoo Finance chart (search ->
               symbol), CoinGecko market_chart, CoinMarketCap data-api, GeckoTerminal pool OHLCV (original
               pool of the token address).  A source only counts if its all-time high is near the known one
               (symbol collisions).  The earliest series wins (hourly preferred on ties).
  2. duds      a random, outcome-blind sample of real DEX pools from the registries (results/dex_runner_pools.json,
               results/dex_exit_pools.json) with hourly GeckoTerminal history from launch: most of them are the
               typical dead pump.fun / Base / ETH memes the engine actually meets.
  3. entry     the live entry: first bar at least 6h after launch whose close is >= +10% over the prior hour
               (a +10% DAY when only daily data exists), with >= $100k volume in the last 24h when volume is
               known (pools: also estimated liquidity >= $100k, as dex_runner_study).  Legends / collapses: a
               second "late" entry just before the collapse (LUNA May 2022, FTT Nov 2022).
  4. exits     the live exit exactly as dex.py runs it (config.DEX["exit"]: 95% trail = no stop, 14-day hold,
               a coin >= 2x at day 14 becomes a runner on a 50% trail, 60% trail once it has hit 3x; a coin
               that took a profit is never put on the clock or turned into a runner, like dex.py's tp1 flag),
               plus every combination of:  protection trail 50/60/70% or none, trigger 3x vs 5x;  runner trail
               40/50/60%;  concentration cap none / 20 / 25 / 33% of a $500 account;  take-profits only at big
               multiples (none, 10% or 25% of the position at 10x/50x/100x, 25% at 10x only, 10%@10x+25%@50x+
               25%@100x).  Stake = tier A (20% of $500 = $100); the other $400 is assumed flat (cap model).
               Costs: 0.3% fee + 1% slippage per side (+ price impact for pools).  Rugged pools: the rest -95%.
  5. report    per coin: CAUGHT? (did the entry fire, how early, how much upside was left) and MAXIMIZED?
               (share of the gain kept vs the peak and vs the best rule in hindsight), the sell points vs the
               peak and the later second leg; rules ranked by total $ profit over legends + collapses + duds,
               by growth (log), excluding the best coin, and walk-forward (older / newer half).
  6. screen    LEGENDS SCREEN CHECK: EVM tokens are rebuilt from public-RPC Transfer logs (top-10 holders on
               day 1/3/7/14/30, LP burned/locked share of the Uniswap-V2-style pair, ownership renounce) and
               today's contract flags (GoPlus; RugCheck for Solana) run through dex.py's own checks.  Every line
               says VERIFIED (data) or ASSUMED (public history) or UNKNOWN.  A narrow fix for wrongful blocks
               (passive wallets that never sent a token) is re-checked on rugged pools from the sample.

    python dex_legends_study.py                     # real run (GitHub Actions)
    python dex_legends_study.py --synthetic         # offline plumbing test (fake prices!)
    python dex_legends_study.py --synthetic --chaos # ... with 429s, empty / broken responses
"""
import argparse
import bisect
import collections
import gzip
import json
import math
import os
import random
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from dex_exit_study import DAY, FEE, HOUR, SLIP, SyntheticGT, banner, clean, fetch_series, fnum, liq_at, load_registry, ts
from dex_runner_study import AdaptiveGT, ChaosGT, Pool, hourly_grid, merge_reg

try:
    import dex as DX                      # the engine's own screen checks (read only)
    XC, SCR = DX.DEX["exit"], DX.DEX["screen"]
    TIER_A = DX.DEX["tiers"]["A"]["pct"]
    BURN = set(DX.BURN)
except Exception:                         # pragma: no cover - standalone fallback
    DX = None
    XC = {"trail": 0.95, "trail_steps": [(3.0, 0.60)], "max_hold_days": 14, "runner_at_limit": (1.0, 0.50)}
    SCR = {"max_top10_pct": 0.40, "min_lp_locked": 0.95, "max_tax": 0.03, "max_creator_pct": 0.05, "min_liq": 100_000,
           "min_vol24": 100_000, "min_age_h": 6}
    TIER_A = 0.20
    BURN = {"0x0000000000000000000000000000000000000000", "0x000000000000000000000000000000000000dead"}

ACCOUNT = 500.0
STAKE = ACCOUNT * TIER_A                  # tier A share of the $500 account
OTHER = ACCOUNT - STAKE                   # rest of the account, assumed flat while one coin is replayed
RUG_LOSS = -0.95
MIN_VOL24 = SCR.get("min_vol24", 100_000)
MIN_LIQ = SCR.get("min_liq", 100_000)
MIN_AGE_H = SCR.get("min_age_h", 6)
H1 = 0.10
HORIZON_D = 1100                          # simulate at most ~3 years after the data starts
ZERO = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
OWNERSHIP = "0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0"


def d2t(s):
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def day(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d") if t else "?"


# ----------------------------------------------------------------------------- the famous coins
# launch dates, ids, addresses and all-time highs are from public history (memory) = ASSUMED; the run
# logs whether each source agreed.  ath: rough all-time high (USD) used only to reject symbol collisions.
def C(sym, name, kind, launch, chain=None, addr=None, cg=None, cc=None, cmc=None, ath=None, late=None, note=""):
    return {"sym": sym, "name": name, "kind": kind, "launch": d2t(launch), "chain": chain, "addr": addr, "cg": cg,
            "cc": cc or [sym], "cmc": cmc, "ath": ath, "late": d2t(late) if late else None, "note": note}


COINS = [
    C("SHIB", "Shiba Inu", "legend", "2020-08-01", "eth", "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE", "shiba-inu", cmc=5994, ath=8.8e-5,
      note="50% of supply sent to Vitalik Buterin's wallet at launch, 50% into the Uniswap pool; Vitalik burned 90% of it on 2021-05-17"),
    C("PEPE", "Pepe", "legend", "2023-04-14", "eth", "0x6982508145454Ce325dDbE47a25d4ec3d2311933", "pepe", cmc=24478, ath=2.8e-5,
      note="93% of supply in the pool with LP burned, 7% multisig for CEX listings, ownership renounced soon after launch"),
    C("BONK", "Bonk", "legend", "2022-12-25", "solana", "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "bonk", cmc=23095, ath=5.9e-5,
      note="about half of supply airdropped to Solana users / NFT holders, rest to contributors and the DAO"),
    C("WIF", "dogwifhat", "legend", "2023-11-20", "solana", "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm", "dogwifcoin", cmc=28752, ath=4.8),
    C("POPCAT", "Popcat", "legend", "2023-12-10", "solana", "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr", "popcat", cmc=28782, ath=2.0),
    C("MOG", "Mog Coin", "legend", "2023-07-19", "eth", "0xaaeE1A9723aaDB7afA2810263653A34bA2C21C7a", "mog-coin", cmc=27659, ath=4.0e-6),
    C("FLOKI", "Floki", "legend", "2021-06-25", "eth", "0x43f11c02439e2736800433b4594994Bd43Cd066D", "floki", cmc=10804, ath=3.4e-4,
      note="v1 token (migrated to v2 0xcf0C12... in Nov 2021)"),
    C("BRETT", "Brett", "legend", "2024-02-26", "base", "0x532f27101965dd16442E59d40670FaF5eBB142E4", "based-brett", cmc=29743, ath=0.23),
    C("BOME", "Book of Meme", "legend", "2024-03-14", "solana", "ukHH6c7mMyiWCf1b9pnWe25TSpkDDt3H5pQZgZ74J82", "book-of-meme", cmc=29870, ath=0.028),
    C("MEW", "cat in a dogs world", "legend", "2024-03-26", "solana", "MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5", "cat-in-a-dogs-world", ath=0.013),
    C("TURBO", "Turbo", "legend", "2023-04-29", "eth", "0xA35923162C49cF95e6BF26623385eb431ad920D3", "turbo", cmc=24911, ath=0.018),
    C("SPX", "SPX6900", "legend", "2023-08-20", "eth", "0xE0f63A424a4439cBE457D80E4f4b51aD25b2c56C", "spx6900", cc=["SPX", "SPX6900"], ath=1.8),
    C("FARTCOIN", "Fartcoin", "legend", "2024-10-18", "solana", "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump", "fartcoin", ath=2.5),
    C("GOAT", "Goatseus Maximus", "legend", "2024-10-10", "solana", "CzLSujWBLFsSjncfkh59rUFqvafWcY5tzedWJSuypump", "goatseus-maximus", ath=1.35),
    C("PNUT", "Peanut the Squirrel", "legend", "2024-11-01", "solana", "2qEHjDLDLbuBgRYvsxhc5D6uDWAivNFZGan56P1tpump", "peanut-the-squirrel", ath=2.5),
    C("MOODENG", "Moo Deng", "legend", "2024-09-10", "solana", "ED5nyyWEzpPPiWimP8vYm7sD7TD3LAt3Q3gRTWHzPJBY", "moo-deng", ath=0.62),
    C("ELON", "Dogelon Mars", "legend", "2021-04-23", "eth", "0x761D38e5ddf6ccf6Cf7c55759d5210750B5D60F3", "dogelon-mars", ath=2.6e-6,
      note="50% of supply sent to Vitalik's wallet (he later burned / donated it)"),
    C("AKITA", "Akita Inu", "legend", "2021-02-01", "eth", "0x3301Ee63Fb29F863f2333Bd4466acb46CD8323E6", "akita-inu",
      note="50% of supply sent to Vitalik's wallet (donated to Gitcoin in May 2021)"),
    C("KISHU", "Kishu Inu", "legend", "2021-04-08", "eth", "0xA2b4C0Af19cC16a6CfAcCe81F192B024d625817D", "kishu-inu"),
    C("SAMO", "Samoyedcoin", "legend", "2021-04-20", "solana", "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU", "samoyedcoin", ath=0.3),
    C("BABYDOGE", "Baby Doge Coin", "legend", "2021-06-01", "bsc", "0xc748673057861a797275CD8A068AbB95A902e8de", "baby-doge-coin",
      note="BSC reflection token with a 10% transfer tax (would fail the 3% tax rule)"),
    C("TRUMP", "Official Trump", "collapse", "2025-01-17", "solana", "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN", "official-trump", ath=73.0,
      note="80% of supply held by insiders on a vesting schedule"),
    C("MELANIA", "Melania Meme", "collapse", "2025-01-19", "solana", "FUAfBo2jgks6gB4Z4LfZkqSZgzNucisEHqnNebaRxM1P", "melania-meme", ath=13.0),
    C("LIBRA", "LIBRA (Milei)", "rug", "2025-02-14", "solana", "Bo9jh3wsmcC2AjakLWzNmKJ3SgtZmXEcSaW7L2FAvUsU", "libra-3", ath=4.5,
      note="insiders pulled ~$100M of one-sided liquidity within hours"),
    C("SLERF", "Slerf", "collapse", "2024-03-18", "solana", "7BgBvyjrZX1YKz4oh9mjb8ZScatkkwb8DzFx7LoiVkM3", "slerf", ath=1.3,
      note="dev burned the LP + presale tokens by mistake at launch"),
    C("SAITAMA", "Saitama Inu (v1)", "collapse", "2021-05-31", "eth", "0x8B3192f5eEBD8579568A2Ed41E6FEB402f93f73F", "saitama-inu"),
    C("SAFEMOON", "SafeMoon (v1)", "collapse", "2021-03-08", "bsc", "0x8076C74C5e3F5852037F31Ff0093Eeb8c8ADd8D3", "safemoon", ath=1.4e-5,
      note="10% transfer tax (would fail the 3% tax rule); later fraud charges"),
    C("SQUID", "Squid Game token", "rug", "2021-10-20", "bsc", "0x87230146E138d3F296a9a77e497A2A83012e9Bc5", "squid-game", ath=2800.0,
      note="anti-sell code (honeypot) then the devs pulled the liquidity on 2021-11-01"),
    C("LUNC", "Terra LUNA (classic)", "collapse", "2019-07-26", None, None, "terra-luna", cc=["LUNC", "LUNA"], cmc=4172, ath=119.0,
      late="2022-05-01", note="not a DEX meme: tests 'never hit a Luna'; late entry = first +10% hour from 2022-05-01"),
    C("FTT", "FTX Token", "collapse", "2019-07-29", "eth", "0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9", "ftx-token", cmc=4195, ath=85.0,
      late="2022-11-01", note="exchange token (not a DEX meme); late entry = first +10% hour from 2022-11-01"),
]

# RPC endpoints (public, no key); lockers (LP lock contracts) and pair factories for the LP check
RPCS = {"eth": ["https://ethereum-rpc.publicnode.com", "https://eth.drpc.org", "https://rpc.ankr.com/eth", "https://eth.llamarpc.com",
                "https://cloudflare-eth.com"],
        "base": ["https://base-rpc.publicnode.com", "https://mainnet.base.org", "https://base.drpc.org", "https://base.llamarpc.com"],
        "bsc": ["https://bsc-rpc.publicnode.com", "https://bsc-dataseed.binance.org", "https://bsc.drpc.org"]}
CHAIN_ID = {"eth": "1", "base": "8453", "bsc": "56"}
WETH = {"eth": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "base": "0x4200000000000000000000000000000000000006",
        "bsc": "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"}
FACTORIES = {"eth": ["0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f", "0xc0aee478e3658e2610c5f7a4a2e1777ce9e4f2ac"],
             "base": ["0x8909dc15e40173ff4699343b6eb8132c65e18ec6"], "bsc": ["0xca143ce32fe78f1f7019d7d551a6402fc5350c73"]}
LOCKERS = {"0x663a5c229c09b049e36dcc11a9b0d4a8eb9db214", "0xe2fe530c047f2d85298b07d9333c05737f1435fb", "0xdba68f07d1b7ca219f78ae8582c213d975c25caf",
           "0x71b5759d73262fbb223956913ecf4ecc51057641", "0x407993575c91ce7643a4d4ccacc9a98c36ee1bbe", "0xc765bddb93b0d1c1a88282ba0fa6b2d00e3e0c83"}
VITALIK = "0xab5801a7d398351b8be11c439e05c5b3259aec9b"
GT_NET = {"eth": "eth", "base": "base", "solana": "solana", "bsc": "bsc"}


# ----------------------------------------------------------------------------- HTTP
class Net:
    """Generic JSON client: per-host gap that grows on 429 and shrinks back, retries on 5xx, None on
    anything unusable (4xx, empty body, not JSON), hard deadline so a budget is never overrun."""

    def __init__(self, deadline=None):
        self.gap, self.last, self.ok_run = collections.defaultdict(lambda: 1.0), collections.defaultdict(float), collections.Counter()
        self.st = collections.defaultdict(collections.Counter)
        self.deadline = deadline or (time.time() + 1e9)
        self.gap["api.coingecko.com"] = 6.0
        self.gap["query1.finance.yahoo.com"] = self.gap["query2.finance.yahoo.com"] = 1.5
        self.gap["api.gopluslabs.io"] = self.gap["api.rugcheck.xyz"] = 3.0
        for urls in RPCS.values():
            for u in urls:
                self.gap[urllib.parse.urlsplit(u).netloc] = 0.35

    def get(self, url, payload=None, tries=4, timeout=25):
        host = urllib.parse.urlsplit(url).netloc
        for attempt in range(tries):
            if time.time() > self.deadline:
                self.st[host]["budget"] += 1
                return None
            wait = self.last[host] + self.gap[host] - time.time()
            if wait > 0:
                time.sleep(wait)
            self.last[host] = time.time()
            self.st[host]["calls"] += 1
            data = json.dumps(payload).encode() if payload is not None else None
            req = urllib.request.Request(url, data=data, headers={"Accept": "application/json", "Content-Type": "application/json",
                                                                  "User-Agent": "Mozilla/5.0 (paper-trader-study/3.0)"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    raw = r.read()
                if not raw:
                    self.st[host]["empty"] += 1
                    return None
                obj = json.loads(raw.decode("utf-8", "replace"))
                self.st[host]["ok"] += 1
                self.ok_run[host] += 1
                if self.ok_run[host] >= 20:
                    self.ok_run[host], self.gap[host] = 0, max(0.3, self.gap[host] * 0.85)
                return obj
            except urllib.error.HTTPError as e:
                self.st[host][f"http{e.code}"] += 1
                if e.code == 429 or e.code >= 500:
                    self.ok_run[host], self.gap[host] = 0, min(30.0, self.gap[host] * 1.6)
                    ra = fnum(e.headers.get("Retry-After")) if e.headers else None
                    time.sleep(min(90, ra if ra and ra > 0 else 8 * (attempt + 1)))
                    continue
                return None
            except Exception:
                self.st[host]["error"] += 1
                time.sleep(2)
        return None

    def report(self):
        return "; ".join(f"{h}: " + " ".join(f"{k} {v}" for k, v in sorted(c.items())) for h, c in sorted(self.st.items()))


class Until:
    """Wraps a GeckoTerminal client: after `until` every call returns None at once (keeps phases inside budget)."""

    def __init__(self, inner, until):
        self.inner, self.until = inner, until

    def __getattr__(self, k):
        return getattr(self.inner, k)

    def get(self, path, **q):
        return None if time.time() > self.until else self.inner.get(path, **q)


# ----------------------------------------------------------------------------- price sources
def mk(bars, dur, src):
    """[[t, o, h, l, c, v]] -> cleaned, deduplicated, positive bars."""
    out = {}
    for b in bars or []:
        try:
            t, o, h, l, c = int(b[0]), float(b[1]), float(b[2]), float(b[3]), float(b[4])
            v = float(b[5]) if len(b) > 5 and b[5] is not None else 0.0
        except (TypeError, ValueError, IndexError):
            continue
        if min(o, h, l, c) <= 0 or any(x != x or x == float("inf") for x in (o, h, l, c)):
            continue
        out[t // dur * dur] = [t // dur * dur, o, max(h, o, c), min(l, o, c), c, max(0.0, v if v == v else 0.0)]
    bars = clean([out[t] for t in sorted(out)])
    return {"src": src, "dur": dur, "bars": bars} if len(bars) >= 5 else None


def ath_ok(s, coin, partial=False):
    """Symbol collisions: the series' high must be within 8x of the known all-time high (if we know it);
    partial (a young pool's history): only 'not far above the known ATH'."""
    if not s:
        return False, "no data"
    hi = max(b[2] for b in s["bars"])
    if coin.get("ath") and not ((partial or coin["ath"] / 8 <= hi) and hi <= coin["ath"] * 8):
        return False, f"high {hi:.3g} vs known ATH {coin['ath']:.3g}: wrong coin"
    return True, f"{len(s['bars'])} {'hourly' if s['dur'] == HOUR else 'daily'} bars {day(s['bars'][0][0])}..{day(s['bars'][-1][0])}"


def src_cryptocompare(net, coin, now):
    base = "https://min-api.cryptocompare.com/data/v2/"
    notes = []
    for sym in coin["cc"]:
        body = net.get(f"{base}histoday?fsym={sym}&tsym=USD&allData=true")
        data = (((body or {}).get("Data") or {}).get("Data") if isinstance(body, dict) and isinstance(body.get("Data"), dict) else None) or []
        rows = [[r.get("time"), r.get("open"), r.get("high"), r.get("low"), r.get("close"), r.get("volumeto")] for r in data if isinstance(r, dict)]
        d = mk(rows, DAY, f"cryptocompare:{sym}")
        ok, why = ath_ok(d, coin)
        if not ok:
            notes.append(f"{sym}: {why}" + (f" ({str(body.get('Message'))[:60]})" if isinstance(body, dict) and body.get("Message") else ""))
            continue
        start = d["bars"][0][0]
        end = min(now, start + HORIZON_D * DAY)
        hours, to = [], start + 2000 * HOUR
        while to < end + 2000 * HOUR:
            b = net.get(f"{base}histohour?fsym={sym}&tsym=USD&limit=2000&toTs={int(min(to, end))}")
            data = (((b or {}).get("Data") or {}).get("Data") if isinstance(b, dict) and isinstance(b.get("Data"), dict) else None) or []
            hours += [[r.get("time"), r.get("open"), r.get("high"), r.get("low"), r.get("close"), r.get("volumeto")]
                      for r in data if isinstance(r, dict)]
            if to >= end:
                break
            to += 2000 * HOUR
        h = mk(hours, HOUR, f"cryptocompare:{sym}")
        out = [d]
        if h and len(h["bars"]) >= 48 and ath_ok(h, coin)[0]:
            out.insert(0, h)
        return out, f"{sym}: " + "; ".join(ath_ok(s, coin)[1] for s in out)
    return [], "; ".join(notes) or "no data"


def yahoo_rows(body):
    try:
        r = body["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        return [[t, o, h, l, c, v] for t, o, h, l, c, v in zip(r["timestamp"], q["open"], q["high"], q["low"], q["close"], q["volume"])]
    except (KeyError, IndexError, TypeError):
        return []


def src_yahoo(net, coin, now):
    notes, cands = [], []
    for q in (coin["sym"], coin["name"]):
        body = net.get("https://query2.finance.yahoo.com/v1/finance/search?" + urllib.parse.urlencode({"q": q, "quotesCount": 10, "newsCount": 0}))
        for x in (body or {}).get("quotes") or [] if isinstance(body, dict) else []:
            s = str((x or {}).get("symbol") or "") if isinstance(x, dict) else ""
            if x.get("quoteType") == "CRYPTOCURRENCY" and s.endswith("-USD") and s.upper().startswith(coin["sym"][:3]) and s not in cands:
                cands.append(s)
    for s in cands[:4]:
        body = net.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?period1=1262304000&period2={now}&interval=1d")
        d = mk(yahoo_rows(body), DAY, f"yahoo:{s}")
        ok, why = ath_ok(d, coin)
        if not ok:
            notes.append(f"{s}: {why}")
            continue
        out = [d]
        if d["bars"][0][0] > now - 700 * DAY:                   # Yahoo keeps hourly bars ~730 days back
            p1 = max(d["bars"][0][0] - DAY, now - 729 * DAY)
            h = mk(yahoo_rows(net.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?period1={p1}&period2={now}&interval=1h")),
                   HOUR, f"yahoo:{s}")
            if h and len(h["bars"]) >= 48 and ath_ok(h, coin)[0]:
                out.insert(0, h)
        return out, f"{s}: " + "; ".join(ath_ok(x, coin)[1] for x in out)
    return [], "; ".join(notes) or ("no symbol found" if not cands else "no data")


def points_to_bars(prices, vols, dur):
    """CoinGecko [[ms, price]] points -> OHLC bars per `dur` (volume: the day's rolling 24h volume / bars per day)."""
    g, vol = {}, {}
    for p in prices or []:
        try:
            t, v = int(p[0]) // 1000, float(p[1])
        except (TypeError, ValueError, IndexError):
            continue
        k = t // dur * dur
        g.setdefault(k, []).append(v)
    for p in vols or []:
        try:
            vol[int(p[0]) // 1000 // dur * dur] = float(p[1]) * dur / DAY
        except (TypeError, ValueError, IndexError):
            continue
    return [[k, xs[0], max(xs), min(xs), xs[-1], vol.get(k, 0.0)] for k, xs in sorted(g.items())]


def src_coingecko(net, coin, now):
    if not coin.get("cg"):
        return [], "no id"
    base = f"https://api.coingecko.com/api/v3/coins/{coin['cg']}/market_chart"
    body = net.get(f"{base}?vs_currency=usd&days=max")
    d = mk(points_to_bars((body or {}).get("prices") if isinstance(body, dict) else None,
                          (body or {}).get("total_volumes") if isinstance(body, dict) else None, DAY), DAY, f"coingecko:{coin['cg']}")
    ok, why = ath_ok(d, coin)
    if not ok:
        err = (body or {}).get("error") if isinstance(body, dict) else None
        return [], why + (f" ({str(err)[:80]})" if err else "")
    out = [d]
    start = d["bars"][0][0]
    if start > now - 360 * DAY:                                    # public API: hourly points for <= 90-day ranges in the last year
        pts, vols, a = [], [], start - DAY
        while a < min(now, start + 360 * DAY):
            b = net.get(f"{base}/range?vs_currency=usd&from={a}&to={min(now, a + 89 * DAY)}")
            pts += (b or {}).get("prices") or [] if isinstance(b, dict) else []
            vols += (b or {}).get("total_volumes") or [] if isinstance(b, dict) else []
            a += 89 * DAY
        h = mk(points_to_bars(pts, vols, HOUR), HOUR, f"coingecko:{coin['cg']}")
        if h and len(h["bars"]) >= 48:
            out.insert(0, h)
    return out, "; ".join(ath_ok(x, coin)[1] for x in out) + " (close-only points)"


def src_cmc(net, coin, now):
    if not coin.get("cmc"):
        return [], "no id"
    rows, a, sym = [], coin["launch"] - 5 * DAY, None
    end = min(now, coin["launch"] + HORIZON_D * DAY)
    while a < end:
        b = net.get(f"https://api.coinmarketcap.com/data-api/v3.1/cryptocurrency/historical?id={coin['cmc']}&convertId=2781"
                    f"&timeStart={a}&timeEnd={min(end, a + 360 * DAY)}&interval=1d")
        data = (b or {}).get("data") if isinstance(b, dict) else None
        if isinstance(data, dict):
            sym = sym or data.get("symbol")
            for x in data.get("quotes") or []:
                q = (x or {}).get("quote") if isinstance(x, dict) else None
                if isinstance(q, dict):
                    t = iso_t(x.get("timeOpen") or q.get("timestamp"))
                    rows.append([t, q.get("open"), q.get("high"), q.get("low"), q.get("close"), q.get("volume")])
        elif a == coin["launch"] - 5 * DAY:
            return [], "no data"
        a += 360 * DAY
    if sym and str(sym).upper() not in [coin["sym"]] + coin["cc"]:
        return [], f"id {coin['cmc']} is {sym}: wrong coin"
    d = mk([r for r in rows if r[0]], DAY, f"cmc:{coin['cmc']}")
    ok, why = ath_ok(d, coin)
    return ([d], why) if ok else ([], why)


def iso_t(s):
    try:
        return int(datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def src_gecko(gt, coin, now):
    """GeckoTerminal: the token's OLDEST pool (the launch pool) -> hourly OHLCV from its creation."""
    if not coin.get("addr") or coin.get("chain") not in GT_NET:
        return [], "no token address"
    net = GT_NET[coin["chain"]]
    body = gt.get(f"/networks/{net}/tokens/{coin['addr']}/pools", page=1)
    pools = []
    for p in (body or {}).get("data") or [] if isinstance(body, dict) else []:
        a = (p or {}).get("attributes") or {} if isinstance(p, dict) else {}
        c = iso_t(a.get("pool_created_at"))
        if a.get("address") and c and (fnum(a.get("reserve_in_usd")) or 0) >= 1000:
            pools.append({"net": net, "pool": a["address"], "created": c})
    if not pools:
        return [], "no pool"
    p = min(pools, key=lambda x: x["created"])
    bars, _ = fetch_series(gt, p, "hour", 1, p["created"], min(now, p["created"] + 4000 * HOUR), 4)
    head = f"pool {p['pool'][:10]}.. created {day(p['created'])}"
    if p["created"] > coin["launch"] + 30 * DAY:
        return [], f"{head}: oldest pool GeckoTerminal lists is > 30 days younger than the coin (launch pool not listed)"
    h = mk(bars, HOUR, f"geckoterminal:{p['pool'][:10]}")
    if h and len(h["bars"]) >= 48:
        ok, why = ath_ok(h, coin, partial=True)
        return ([h], f"{head}: {why}") if ok else ([], f"{head}: {why}")
    body = gt.get(f"/networks/{net}/pools/{p['pool']}/ohlcv/day", aggregate=1, limit=1000, before_timestamp=now, currency="usd", token="base")
    rows = ((((body or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list")) if isinstance(body, dict) and isinstance(body.get("data"), dict) else None
    d = mk(rows, DAY, f"geckoterminal:{p['pool'][:10]}")
    ok, why = ath_ok(d, coin, partial=True)
    if d and ok and d["bars"][0][0] <= coin["launch"] + 30 * DAY:
        return [d], f"{head}: {why}"
    return [], f"{head}: " + (why if d else "no OHLCV (public API keeps only recent months)") + ("" if not d or ok else "")


def pick(series, coin):
    """Earliest start wins (entry timing is what 'caught' is about); hourly wins ties within 3 days."""
    if not series:
        return None
    return min(series, key=lambda s: (s["bars"][0][0] + (0 if s["dur"] == HOUR else 3 * DAY), s["dur"]))


# ----------------------------------------------------------------------------- series + entry + exit simulation
class Ser:
    def __init__(self, bars, dur, key, group, name, launch=None, rug=None, liq=None, dead_end=False, now=None, src="", meta=None):
        n = len(bars)
        t0 = bars[0][0] if n else 0
        cut = [b for b in bars if b[0] <= t0 + HORIZON_D * DAY]
        self.T, self.O, self.H, self.L, self.Cl, self.V = (list(x) for x in zip(*[b[:6] for b in cut])) if cut else ([],) * 6
        self.dur, self.key, self.group, self.name, self.src, self.meta = dur, key, group, name, src, meta or {}
        self.launch = launch if launch else t0
        self.rug, self.liq, self.dead_end = rug or set(), liq, dead_end
        self.now = now or time.time()
        self.cv = [0.0]
        for v in self.V:
            self.cv.append(self.cv[-1] + v)
        self.has_vol = self.cv[-1] > 0

    def vol24(self, i):
        t = self.T[i] + self.dur
        j = bisect.bisect_right(self.T, t - DAY - 1e-9)
        return self.cv[i + 1] - self.cv[j]


def find_entry(S, after=None, check_liq=False):
    """First bar >= 6h after launch (and after `after`) whose close is >= +10% over the previous bar's close,
    with >= $100k volume in the last 24h when volume is known (and estimated liquidity >= $100k for pools)."""
    lo = max(S.launch + MIN_AGE_H * HOUR, after or 0)
    for i in range(1, len(S.T)):
        if S.T[i] + S.dur < lo or S.Cl[i - 1] <= 0:
            continue
        if S.Cl[i] / S.Cl[i - 1] - 1 < H1:
            continue
        if S.has_vol and S.vol24(i) < MIN_VOL24:
            continue
        if check_liq and S.liq and S.liq(S.Cl[i]) < MIN_LIQ:
            continue
        return i
    return None


def cost(usd, liq):
    return min(1.0, FEE + SLIP + (usd / liq if liq and liq > 0 else 0.0))


LIVE_RULE = {"prot": tuple(XC.get("trail_steps", [(3.0, 0.60)])[0]) if XC.get("trail_steps") else None,
             "rt": (XC.get("runner_at_limit") or (1.0, 0.50))[1], "cap": None, "tps": ()}
TP_SETS = [("none", ()), ("10% @10x/50x/100x", ((10, 0.10), (50, 0.10), (100, 0.10))), ("25% @10x/50x/100x", ((10, 0.25), (50, 0.25), (100, 0.25))),
           ("25% @10x only", ((10, 0.25),)), ("10%@10x 25%@50x 25%@100x", ((10, 0.10), (50, 0.25), (100, 0.25)))]


def rule_name(r):
    p = f"{r['prot'][1]:.0%} trail after {r['prot'][0]:g}x" if r["prot"] else "no protection trail"
    tp = next((n for n, t in TP_SETS if t == r["tps"]), str(r["tps"]))
    cap = "none" if not r["cap"] else f"{r['cap']:.0%}"
    return f"{p} | runner {r['rt']:.0%} | cap {cap} | tp {tp}"


def build_rules():
    rules = []
    for prot in [(3.0, 0.50), (3.0, 0.60), (3.0, 0.70), (5.0, 0.50), (5.0, 0.60), (5.0, 0.70), None]:
        for rt in (0.40, 0.50, 0.60):
            for cap in (None, 0.20, 0.25, 0.33):
                for _, tps in TP_SETS:
                    r = {"prot": prot, "rt": rt, "cap": cap, "tps": tps}
                    r["name"] = rule_name(r)
                    rules.append(r)
    return rules


def simulate(S, i0, r, log=False):
    """The live dex.py exit on S's bars after bar i0 (entry at its close), plus the rule's add-ons.
    -> dict(ret, pnl, exit_t, peak (held multiple), open, sells[(t, px, mult, frac, why)])."""
    T, O, H, L, Cl, dur = S.T, S.O, S.H, S.L, S.Cl, S.dur
    e = Cl[i0]
    liq = S.liq
    q = STAKE * (1 - cost(STAKE, liq(e) if liq else None)) / e
    cash, peak, stop, runner, ntp = 0.0, e, e * (1 - XC.get("trail", 0.95)), False, 0
    trail0, prot, rt, cap, tps = XC.get("trail", 0.95), r["prot"], r["rt"], r["cap"], r["tps"]
    R0 = (XC.get("runner_at_limit") or (1.0, 0.5))[0]
    t_in = T[i0] + dur
    limit = t_in + XC.get("max_hold_days", 14) * DAY
    sells = []

    def sell(qty, px, t, why):
        nonlocal q, cash
        qty = min(q, qty)
        if qty <= 0:
            return
        usd = qty * px
        cash += usd * (1 - cost(usd, liq(px) if liq else None))
        if log:
            sells.append((t, px, px / e, qty / q, why))
        q -= qty

    def done(t, is_open=False):
        val = cash + (q * Cl[-1] * (1 - cost(q * Cl[-1], liq(Cl[-1]) if liq else None)) if is_open and q > 0 else 0.0)
        return {"ret": val / STAKE - 1, "pnl": val - STAKE, "exit_t": t, "peak": peak / e, "open": is_open and q > 0, "sells": sells,
                "runner": runner}

    for j in range(i0 + 1, len(T)):
        t, o, h, l, c = T[j], O[j], H[j], L[j], Cl[j]
        if j in S.rug:                                       # rug / dead pool: the rest is worth -95%
            if log:
                sells.append((t, e * (1 + RUG_LOSS), 1 + RUG_LOSS, 1.0, "rug"))
            cash += q * e * (1 + RUG_LOSS)
            q = 0
            return done(t + dur)
        if not runner and ntp == 0 and t >= limit:            # dex.py: time limit only before any take-profit
            if o >= e * (1 + R0):
                runner = True
            else:
                sell(q, o, t, "time limit 14d")
                return done(t)
        if l <= stop:                                         # stop first (conservative), gaps fill at the open
            sell(q, min(o, stop), t, "runner trail" if runner else "protection trail" if prot and peak >= e * prot[0] else "95% trail")
            return done(t + dur)
        while ntp < len(tps) and h >= e * tps[ntp][0]:
            sell(q * tps[ntp][1], max(o, e * tps[ntp][0]), t, f"take-profit {tps[ntp][0]:g}x")
            ntp += 1
        peak = max(peak, h)
        tr = trail0
        if prot and peak >= e * prot[0]:
            tr = prot[1]
        if runner:
            tr = min(tr, rt)
        stop = max(stop, peak * (1 - tr))
        if cap:
            pos = q * c
            if pos > cap * (OTHER + cash + pos) * 1.001:
                target = cap * (OTHER + cash) / (1 - cap)
                sell((pos - target) / c, c, t, f"cap {cap:.0%}")
        if q <= 1e-12:
            return done(t + dur)
    if S.dead_end and q > 0:                                  # pool history ended for good: -95% on the rest
        if log:
            sells.append((T[-1] + dur, e * (1 + RUG_LOSS), 1 + RUG_LOSS, 1.0, "dead"))
        cash += q * e * (1 + RUG_LOSS)
        q = 0
        return done(T[-1] + dur)
    return done(T[-1] + dur, True)


# ----------------------------------------------------------------------------- synthetic network (offline tests)
class FakeNet:
    """Offline stand-in for Net: CryptoCompare answers for most coins with fake legend / collapse / rug paths,
    Yahoo / CoinGecko / CMC fail or answer garbage, a tiny fake EVM chain for the RPC calls, GoPlus / RugCheck
    minimal bodies.  chaos: random None / {} / broken bodies everywhere."""

    def __init__(self, chaos=False, seed=11):
        self.rng, self.chaos, self.st = random.Random(seed), chaos, collections.defaultdict(collections.Counter)
        self.cache = {}
        self.now = int(time.time()) // HOUR * HOUR

    def path(self, coin):
        if coin["sym"] in self.cache:
            return self.cache[coin["sym"]]
        rng = random.Random(coin["sym"])
        t0, px, out = coin["launch"], 1e-6 * rng.uniform(0.5, 2), []
        n = min(int((self.now - t0) / HOUR), HORIZON_D * 24)
        kind = coin["kind"]
        up = rng.randint(200, 3000)
        for i in range(n):
            if kind == "legend":
                drift = math.log(rng.uniform(50, 3000)) / up if i < up else -0.0004
            elif kind == "collapse":
                drift = math.log(8) / up if i < up else (-0.03 if i < up + 200 else -0.0002)
            else:
                drift = 0.004 if i < 200 else (-0.08 if i < 260 else -0.001)
            r = drift + rng.gauss(0, 0.03) + (rng.choice((-1, 1)) * rng.uniform(0.1, 0.3) if rng.random() < 0.01 else 0)
            o, px = px, max(1e-15, px * math.exp(r))
            out.append([t0 + i * HOUR, o, max(o, px) * 1.01, min(o, px) * 0.99, px, 2e4 * math.exp(rng.gauss(0, 1))])
        if coin.get("ath"):                                   # scale so the fake high matches the known ATH
            k = coin["ath"] / max(b[2] for b in out)
            out = [[b[0]] + [x * k for x in b[1:5]] + [b[5]] for b in out]
        self.cache[coin["sym"]] = out
        return out

    def _coin(self, sym):
        return next((c for c in COINS if sym in c["cc"] or sym == c["sym"]), None)

    def get(self, url, payload=None, **kw):
        host = urllib.parse.urlsplit(url).netloc
        self.st[host]["calls"] += 1
        if self.chaos:
            x = self.rng.random()
            if x < 0.06:
                return None
            if x < 0.09:
                return {}
            if x < 0.12:
                return {"Data": {"Data": [{"time": None, "close": "x"}, 5]}, "data": [None], "chart": {"result": []}, "result": 7}
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        if "cryptocompare" in host:
            c = self._coin(q.get("fsym", ""))
            if not c or c["sym"] in ("MEW", "LIBRA"):
                return {"Response": "Error", "Message": "no data"}
            p = self.path(c)
            if "histoday" in url:
                g = {}
                for b in p:
                    g.setdefault(b[0] // DAY * DAY, []).append(b)
                rows = [{"time": k, "open": x[0][1], "high": max(y[2] for y in x), "low": min(y[3] for y in x), "close": x[-1][4],
                         "volumeto": sum(y[5] for y in x)} for k, x in sorted(g.items())]
                return {"Response": "Success", "Data": {"Data": [{"time": rows[0]["time"] - DAY * k, "open": 0, "high": 0, "low": 0, "close": 0}
                                                                 for k in range(3, 0, -1)] + rows}}
            to = int(q.get("toTs", 0))
            rows = [{"time": b[0], "open": b[1], "high": b[2], "low": b[3], "close": b[4], "volumeto": b[5]} for b in p if to - 2000 * HOUR < b[0] <= to]
            return {"Response": "Success", "Data": {"Data": rows}}
        if "yahoo" in host:
            return {"quotes": [{"symbol": "SHIB-USD", "quoteType": "CRYPTOCURRENCY"}]} if "search" in url else {"chart": {"result": None}}
        if "coingecko" in host:
            return {"error": {"status": {"error_code": 10012, "error_message": "exceeds the allowed time range"}}}
        if "coinmarketcap" in host:
            return None
        if "gopluslabs" in host:
            a = url.split("contract_addresses=")[-1].lower()
            return {"code": 1, "result": {a: {"is_open_source": "1", "is_mintable": "0", "buy_tax": "0", "sell_tax": "0", "holders": [],
                                              "lp_holders": [], "is_blacklisted": "1" if "pepe" in a else "0"}}}
        if "rugcheck" in host:
            return {"risks": [{"name": "Top 10 holders high ownership", "level": "warn"}], "score_normalised": 12, "lpLockedPct": 100}
        if payload is not None:
            return self.rpc(payload)
        return None

    def rpc(self, p):
        m, a = p.get("method"), p.get("params") or []
        T0, BT, TIP = d2t("2015-07-30"), 12, (self.now - d2t("2015-07-30")) // 12
        if m == "eth_blockNumber":
            return {"result": hex(TIP)}
        if m == "eth_getBlockByNumber":
            b = int(a[0], 16) if a and a[0] != "latest" else TIP
            return {"result": {"number": hex(b), "timestamp": hex(T0 + b * BT)}}
        if m == "eth_getCode":
            b = int(a[1], 16) if len(a) > 1 and a[1] != "latest" else TIP
            c = next((c for c in COINS if c["addr"] and c["addr"].lower() == str(a[0]).lower()), None)
            return {"result": "0x6080" if c and T0 + b * BT >= c["launch"] else "0x"}
        if m == "eth_call":
            return {"result": "0x" + "0" * 24 + "ab" * 20}
        if m == "eth_getLogs":
            f = a[0] if a else {}
            b0, b1 = int(f.get("fromBlock", "0x0"), 16), int(f.get("toBlock", "0x0"), 16)
            if b1 - b0 > 20_000:
                return {"error": {"code": -32005, "message": "query returned more than 10000 results"}}
            c = next((c for c in COINS if c["addr"] and c["addr"].lower() == str(f.get("address")).lower()), None)
            lb = (c["launch"] - T0) // BT + 10 if c else None
            out = []
            pad = lambda x: "0x" + "0" * 24 + x[2:]
            if c and f.get("topics", [None])[0] == TRANSFER and b0 <= lb <= b1:
                out.append({"blockNumber": hex(lb), "logIndex": "0x0", "topics": [TRANSFER, pad(ZERO), pad("0x" + "11" * 20)], "data": hex(10 ** 24)})
                out.append({"blockNumber": hex(lb + 1), "logIndex": "0x0", "topics": [TRANSFER, pad("0x" + "11" * 20), pad(VITALIK)], "data": hex(5 * 10 ** 23)})
                out.append({"blockNumber": hex(lb + 2), "logIndex": "0x0", "topics": [TRANSFER, pad("0x" + "11" * 20), pad("0x" + "ab" * 20)],
                            "data": hex(5 * 10 ** 23)})
            if c and b0 <= lb + 500 <= b1 and f.get("topics", [None])[0] == TRANSFER:
                for k in range(30):
                    out.append({"blockNumber": hex(lb + 500 + k), "logIndex": hex(k), "topics": [TRANSFER, pad("0x" + "ab" * 20), pad("0x%040x" % (k + 99))],
                                "data": hex(10 ** 21 * (k + 1))})
            return {"result": out}
        return {"error": {"message": "unsupported"}}

    def report(self):
        return "; ".join(f"{h}: calls {c['calls']}" for h, c in sorted(self.st.items()))


# ----------------------------------------------------------------------------- EVM on-chain reconstruction
class RPC:
    def __init__(self, net, chain, deadline):
        self.net, self.chain, self.urls, self.i, self.deadline = net, chain, RPCS.get(chain, []), 0, deadline
        self.ts_cache, self.errors = {}, collections.Counter()

    def call(self, method, params):
        """-> (result, error message). Tries the endpoints in turn; the one that works stays first."""
        err = "no endpoint"
        for k in range(len(self.urls)):
            if time.time() > self.deadline:
                return None, "budget"
            u = self.urls[(self.i + k) % len(self.urls)]
            body = self.net.get(u, payload={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, tries=2)
            if isinstance(body, dict) and "result" in body and body["result"] is not None:
                self.i = (self.i + k) % len(self.urls)
                return body["result"], None
            if isinstance(body, dict) and isinstance(body.get("error"), dict):
                err = str(body["error"].get("message") or body["error"])[:120]
                self.errors[err[:40]] += 1
                if method == "eth_getLogs" and any(w in err.lower() for w in ("more than", "too many", "limit", "range", "exceed", "timeout", "10000")):
                    return None, err                     # the caller splits the range
            else:
                err = "no answer"
        return None, err

    def tip(self):
        r, _ = self.call("eth_blockNumber", [])
        try:
            return int(r, 16)
        except (TypeError, ValueError):
            return None

    def btime(self, b):
        if b in self.ts_cache:
            return self.ts_cache[b]
        r, _ = self.call("eth_getBlockByNumber", [hex(b), False])
        try:
            t = int(r["timestamp"], 16)
        except (TypeError, ValueError, KeyError):
            return None
        self.ts_cache[b] = t
        return t

    def block_at(self, t):
        """Last block with timestamp <= t (interpolation + bisection on block headers)."""
        hi = self.tip()
        if not hi:
            return None
        lo, tlo, thi = 1, self.btime(1), self.btime(hi)
        if tlo is None or thi is None:
            return None
        if t >= thi:
            return hi
        for it in range(80):
            if hi - lo <= 1:
                return lo
            if it < 8:                                     # interpolation first (block times are ~regular) ...
                g = min(hi - 1, max(lo + 1, lo + int((t - tlo) / max(1, thi - tlo) * (hi - lo))))
            else:                                          # ... then plain bisection (always converges)
                g = (lo + hi) // 2
            tg = self.btime(g)
            if tg is None:
                return None
            if tg <= t:
                lo, tlo = g, tg
            else:
                hi, thi = g, tg
        return lo

    def creation_block(self, addr, lo, hi):
        """First block where the contract has code (needs an archive node); None if unknown."""
        c_hi, e1 = self.call("eth_getCode", [addr, hex(hi)])
        c_lo, e2 = self.call("eth_getCode", [addr, hex(lo)])
        if e1 or e2 or not isinstance(c_hi, str) or not isinstance(c_lo, str) or len(c_hi) <= 2 or len(c_lo) > 2:
            return None
        while hi - lo > 1:
            m = (lo + hi) // 2
            c, e = self.call("eth_getCode", [addr, hex(m)])
            if e or not isinstance(c, str):
                return None
            if len(c) > 2:
                hi = m
            else:
                lo = m
        return hi

    def logs(self, addr, topic0, b0, b1, cap=250_000, stop_t=None):
        """All logs of `addr` with topic0 in [b0, b1], adaptive chunk (halve on 'too many', grow on small)."""
        out, a, step, fails = [], b0, 2000, 0
        while a <= b1 and len(out) < cap:
            if time.time() > (stop_t or self.deadline):
                return out, False
            b = min(b1, a + step - 1)
            r, err = self.call("eth_getLogs", [{"address": addr, "topics": [topic0], "fromBlock": hex(a), "toBlock": hex(b)}])
            if err or not isinstance(r, list):
                fails += 1
                if step > 1 and fails < 40:
                    step = max(1, step // 4)
                    continue
                return out, False
            out += [x for x in r if isinstance(x, dict)]
            a, fails = b + 1, 0
            if len(r) < 2000:
                step = min(50_000, int(step * 1.6) + 1)
            elif len(r) > 6000:
                step = max(1, step // 2)
        return out, a > b1


def addr_of(topic):
    return ("0x" + str(topic)[-40:]).lower() if topic else None


def parse_transfers(logs):
    out = []
    for x in logs:
        tp = x.get("topics") or []
        if len(tp) < 3:
            continue
        try:
            v = int(str(x.get("data") or "0x0")[:66], 16) if str(x.get("data") or "0x") not in ("0x", "") else 0
            out.append((int(x["blockNumber"], 16), int(str(x.get("logIndex") or "0x0"), 16), addr_of(tp[1]), addr_of(tp[2]), v))
        except (TypeError, ValueError, KeyError):
            continue
    return sorted(out)


def holders_timeline(tr, snaps, exclude, lp_tr=None, pair=None):
    """Replay transfers; at each snapshot block -> top-10 share (engine rule), top-10 excluding passive wallets
    (never sent a token: the proposed fix), minter-recipient share, holder count, LP locked/burned share."""
    bal, sent, out, i, first_to = collections.Counter(), set(), [], 0, None
    lbal, lburn, j = collections.Counter(), 0, 0
    for label, blk in snaps:
        while i < len(tr) and tr[i][0] <= blk:
            _, _, f, t, v = tr[i]
            bal[f] -= v
            bal[t] += v
            if f != ZERO:
                sent.add(f)
            elif first_to is None:
                first_to = t
            i += 1
        while lp_tr and j < len(lp_tr) and lp_tr[j][0] <= blk:
            _, _, f, t, v = lp_tr[j]
            lbal[f] -= v
            lbal[t] += v
            if t == ZERO and f != pair:
                lburn += v
            j += 1
        supply = sum(v for a, v in bal.items() if a != ZERO and v > 0)
        if supply <= 0:
            out.append((label, None))
            continue
        hs = sorted(((v, a) for a, v in bal.items() if a not in BURN and a not in exclude and v > 0), reverse=True)
        top = sum(v for v, _ in hs[:10]) / supply
        fix = sum(v for v, _ in [x for x in hs if x[1] in sent][:10]) / supply
        famous = sum(v for v, _ in [x for x in hs if x[1] != VITALIK][:10]) / supply
        neg = sum(1 for a, v in bal.items() if a != ZERO and v < 0)
        lp = None
        if lp_tr is not None:
            lsup = sum(v for a, v in lbal.items() if a != ZERO and v > 0) + lburn
            if lsup > 0:
                lp = (sum(v for a, v in lbal.items() if (a in BURN or a in LOCKERS) and a != ZERO and v > 0) + lburn) / lsup
        out.append((label, {"top10": top, "top10_fix": fix, "top10_famous": famous, "minter": bal.get(first_to, 0) / supply if first_to else None,
                            "holders": sum(1 for a, v in bal.items() if a != ZERO and v > 0), "lp": lp, "neg": neg,
                            "top": [(a, v / supply, a in sent) for v, a in hs[:3]]}))
    return out


def get_pair(rpc, token):
    for f in FACTORIES.get(rpc.chain, []):
        data = "0xe6a43905" + "0" * 24 + token.lower()[2:] + "0" * 24 + WETH[rpc.chain][2:]
        r, _ = rpc.call("eth_call", [{"to": f, "data": data}, "latest"])
        a = addr_of(r) if isinstance(r, str) and len(r) >= 42 else None
        if a and a != ZERO:
            return a
    return None


def evm_history(rpc, token, t_launch, days=(1, 3, 7, 14, 30), budget_s=420):
    """-> dict with snapshots (top-10 etc.), owner renounce, LP lock, notes; None if the chain is unreachable."""
    stop_t = min(rpc.deadline, time.time() + budget_s)
    token = token.lower()
    b_lo, b_hi = rpc.block_at(t_launch - 30 * DAY), rpc.block_at(t_launch + 5 * DAY)
    if not b_lo or not b_hi:
        return {"err": "RPC unreachable (no block headers)"}
    notes = []
    cb = rpc.creation_block(token, b_lo, b_hi)
    if cb is None:
        cb = rpc.block_at(t_launch - 2 * DAY)
        notes.append("creation block unknown (no archive getCode): logs start 2 days before the assumed launch date")
    else:
        notes.append(f"contract created in block {cb} ({day(rpc.btime(cb))}) [verified]")
    t_cb = rpc.btime(cb) or t_launch
    maxd = max(days) if rpc.chain == "eth" else min(max(days), 7)
    b_end = rpc.block_at(t_cb + maxd * DAY) or cb
    logs, complete = rpc.logs(token, TRANSFER, cb, b_end, stop_t=stop_t)
    tr = parse_transfers(logs)
    if not tr:
        return {"err": "no Transfer logs returned (public node without history / range limits)", "notes": notes}
    t_first = t_cb
    if not complete:
        notes.append(f"logs cut at block {tr[-1][0]} (time / result budget): later snapshots missing")
    pair = get_pair(rpc, token)
    lp_tr = None
    if pair:
        pl, pc = rpc.logs(pair, TRANSFER, cb, b_end, stop_t=stop_t + 120)
        lp_tr = parse_transfers(pl) if pl else None
        notes.append(f"Uniswap-V2-style pair {pair[:10]}.. with {len(pl)} LP transfers" + ("" if pc else " (incomplete)"))
    else:
        notes.append("no V2 pair vs WETH/WBNB found (v3 pool / other quote): LP lock not checkable")
    bt = (rpc.btime(b_end) - t_cb) / max(1, b_end - cb) if rpc.btime(b_end) else 12
    snaps = [(f"day {d}", cb + int(d * DAY / max(0.1, bt))) for d in days if d <= maxd and cb + int(d * DAY / max(0.1, bt)) <= tr[-1][0] + 50]
    if not snaps:
        snaps = [("first logs", tr[-1][0])]
    exclude = {pair} if pair else set()
    tl = holders_timeline(tr, snaps, exclude, lp_tr, pair)
    own, _ = rpc.logs(token, OWNERSHIP, cb, b_end, stop_t=stop_t + 120)
    owner = []
    for x in own:
        tp = x.get("topics") or []
        if len(tp) >= 3:
            try:
                owner.append((int(x["blockNumber"], 16), addr_of(tp[2])))
            except (TypeError, ValueError, KeyError):
                pass
    return {"snaps": tl, "notes": notes, "owner": owner, "t_cb": t_first, "cb": cb, "bt": bt, "n_logs": len(tr), "pair": pair}


# ----------------------------------------------------------------------------- statistics helpers
def fmt_x(x):
    return "n/a" if x is None or x != x else f"{x:,.0f}x" if x >= 100 else f"{x:.1f}x"


def fmt_d(x):
    return f"{'-' if x < 0 else '+'}${abs(x):,.0f}" if x == x else "n/a"


def pctf(x):
    return "n/a" if x is None or x != x else f"{x:+.2%}" if abs(x) < 0.01 else f"{x:+.1%}" if abs(x) < 0.1 else f"{x:+.0%}"


def med(xs):
    return statistics.median(xs) if xs else float("nan")


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--chaos", action="store_true")
    ap.add_argument("--budget-min", type=float, default=300, help="stop all fetching after this many minutes")
    ap.add_argument("--legend-min", type=float, default=70)
    ap.add_argument("--pool-min", type=float, default=120)
    ap.add_argument("--screen-min", type=float, default=45)
    ap.add_argument("--max-pools", type=int, default=260)
    ap.add_argument("--data-out", default="results/dex_legends_daily.json.gz")
    a = ap.parse_args()
    t_start = time.time()
    hard = t_start + a.budget_min * 60
    rules = build_rules()
    live_i = next(i for i, r in enumerate(rules) if r["prot"] == LIVE_RULE["prot"] and r["rt"] == LIVE_RULE["rt"] and not r["cap"] and not r["tps"])

    if a.synthetic:
        print("SYNTHETIC MODE: fake prices, only checks that the study runs end to end" + (" (chaos on)" if a.chaos else "") + "\n")
        net = FakeNet(a.chaos)
        now = net.now
        sg = SyntheticGT(per_net=40)
        gt = ChaosGT(sg) if a.chaos else sg
        reg = merge_reg({}, [dict(r, first_seen=r["seen"]) for r in sg.seed_registry()], sg.now)
        pool_now = sg.now
    else:
        net, now = Net(hard), int(time.time())
        gt = AdaptiveGT()
        reg = load_registry("results/dex_runner_pools.json")
        for k, e in load_registry("results/dex_exit_pools.json").items():
            reg.setdefault(k, dict(e, first_seen=e.get("first_seen") or e.get("seen", now)))
        pool_now = now
    print(f"live exit (config.DEX['exit']): {XC}")
    print(f"stake per trade ${STAKE:.0f} (tier A {TIER_A:.0%} of a ${ACCOUNT:.0f} account; the other ${OTHER:.0f} is assumed flat "
          f"for the concentration cap); {len(rules)} exit rules; live rule = '{rules[live_i]['name']}'")

    # 1. famous coins ------------------------------------------------------------------------------------
    banner("1. DATA SOURCES PER COIN  (probed from this runner; a source counts only if its all-time high matches)")
    legend_deadline = min(hard, time.time() + a.legend_min * 60)
    gt = Until(gt, legend_deadline)
    if not a.synthetic:
        net.deadline = legend_deadline
    series, src_log, daily_dump = [], {}, {}
    for coin in COINS:
        found, log = [], []
        for name, fn, cl in (("cryptocompare", src_cryptocompare, net), ("yahoo", src_yahoo, net), ("coingecko", src_coingecko, net),
                             ("coinmarketcap", src_cmc, net), ("geckoterminal", src_gecko, gt)):
            if time.time() > legend_deadline:
                log.append(f"{name}: skipped (budget)")
                continue
            if name == "geckoterminal" and any(s["dur"] == HOUR and s["bars"][0][0] <= coin["launch"] + 3 * DAY for s in found):
                log.append(f"{name}: not needed (hourly data from launch already)")
                continue
            try:
                got, why = fn(cl, coin, now)
            except Exception as ex:                               # never die on one source
                got, why = [], f"error {type(ex).__name__}: {str(ex)[:60]}"
            found += got
            log.append(f"{name}: {'OK ' if got else 'no '} {why}")
        best = pick(found, coin)
        src_log[coin["sym"]] = best["src"] if best else None
        print(f"{coin['sym']:<9} ({coin['kind']}, launched {day(coin['launch'])} [assumed])")
        for x in log:
            print(f"    {x}")
        if not best:
            print("    -> SKIPPED: no usable price history from any free source")
            continue
        b = best["bars"]
        lag = (b[0][0] - coin["launch"]) / DAY
        print(f"    -> using {best['src']} ({'hourly' if best['dur'] == HOUR else 'daily'}), {day(b[0][0])}..{day(b[-1][0])}"
              + (f"; data starts {lag:.0f} days after launch" if lag > 3 else ""))
        daily = pick([s for s in found if s["dur"] == DAY], coin) or best
        daily_dump[coin["sym"]] = {"src": daily["src"], "bars": [[x[0]] + [float(f"{y:.6g}") for y in x[1:6]] for x in daily["bars"]]}
        S = Ser(b, best["dur"], coin["sym"], coin["kind"], coin["name"], launch=max(coin["launch"], b[0][0]) if lag <= 3 else b[0][0],
                now=now, src=best["src"], meta={"coin": coin, "lag": lag})
        series.append(S)
    print(f"\nprice history for {len(series)} of {len(COINS)} coins; {time.time() - t_start:.0f}s")

    # trades on famous coins
    trades = []                                                      # (Ser, i0, group, t_entry)
    for S in series:
        i0 = find_entry(S)
        S.meta["i0"] = i0
        if i0 is not None:
            trades.append((S, i0, "legend" if S.group == "legend" else "collapse"))
        c = S.meta["coin"]
        if c.get("late"):
            j = find_entry(S, after=c["late"])
            if j is not None:
                S2 = Ser([[S.T[k], S.O[k], S.H[k], S.L[k], S.Cl[k], S.V[k]] for k in range(len(S.T))], S.dur, S.key + "-late", "collapse",
                         S.name + " (late entry)", launch=S.launch, now=now, src=S.src, meta={"coin": c, "lag": S.meta["lag"], "i0": j})
                trades.append((S2, j, "collapse"))

    # 2. pool sample (duds / rugs as the engine meets them) --------------------------------------------------
    banner("2. DUD / RUG SAMPLE: random outcome-blind DEX pools from the registries, hourly GeckoTerminal history from launch")
    pool_deadline = min(hard, time.time() + a.pool_min * 60)
    gt.until = pool_deadline + 300
    cand = [p for p in reg.values() if p.get("pool") and pool_now - 150 * DAY <= p.get("created", 0) <= pool_now - 8 * DAY
            and p.get("ref_reserve", 0) >= 15_000]
    rng = random.Random(42)
    rng.shuffle(cand)
    blind = lambda p: p.get("first_seen", pool_now) <= p["created"] + 2 * DAY or "new" in p.get("srcs", [])
    cand.sort(key=lambda p: not blind(p))
    cand = cand[:a.max_pools]
    print(f"{len(cand)} candidate pools created 8-150 days ago ({sum(blind(p) for p in cand)} seen within 2 days of launch = outcome-blind, "
          f"fetched first)")
    pools, why = [], collections.Counter()
    for n, p in enumerate(cand):
        if time.time() > pool_deadline:
            why["budget"] += len(cand) - n
            break
        try:
            pages = min(4, int((pool_now - p["created"]) / (1000 * HOUR)) + 1)
            hourly, complete = fetch_series(gt, p, "hour", 1, p["created"], pool_now, pages)
            if len(hourly) < 30:
                why["no data"] += 1
                continue
            grid = hourly_grid(clean(hourly))
            if not grid:
                why["short"] += 1
                continue
            dead = complete and pool_now - (hourly[-1][0] + HOUR) > 72 * HOUR
            P = Pool(p, grid, pool_now, dead)
            P.derive()
            bars = [[P.t0 + i * HOUR, P.O[i], P.H[i], P.L[i], P.C[i], P.V[i]] for i in range(P.n)]
            rug = {i for i in range(P.n) if P.rug[i]}
            S = Ser(bars, HOUR, f"{p['net']}:{p['token']}", "pool", p.get("sym", "?"), launch=p["created"], rug=rug,
                    liq=(lambda px, p=p: liq_at(p, px)), dead_end=False, now=pool_now, src="geckoterminal",
                    meta={"pump": p["token"].lower().endswith("pump"), "net": p["net"], "p": p, "rugged": bool(rug) or dead})
            pools.append(S)
            i0 = find_entry(S, check_liq=True)
            if i0 is not None:
                trades.append((S, i0, "pool"))
            else:
                why["no entry signal"] += 1
        except Exception as ex:                                          # never die on one pool
            why[f"error {type(ex).__name__}"] += 1
        if n % 50 == 0:
            print(f"  fetched {n + 1}/{len(cand)}  GT calls {gt.calls}  429s {gt.r429}  pools {len(pools)}  {time.time() - t_start:.0f}s")
            sys.stdout.flush()
    pt = [t for t in trades if t[2] == "pool"]
    print(f"pools with history {len(pools)}, with a live entry signal {len(pt)}; skipped: " + ", ".join(f"{k} {v}" for k, v in why.items()))
    print(f"(pump.fun {sum(t[0].meta['pump'] for t in pt)}, solana {sum(t[0].meta['net'] == 'solana' for t in pt)}, base "
          f"{sum(t[0].meta['net'] == 'base' for t in pt)}, eth {sum(t[0].meta['net'] == 'eth' for t in pt)}; rugged / dead later "
          f"{sum(t[0].meta['rugged'] for t in pt)})")

    if not trades:
        print("\nno trades at all - check source reachability above")
        return

    # 3. simulate every rule on every trade -----------------------------------------------------------------
    t_sim = time.time()
    res = [[None] * len(trades) for _ in rules]
    for k, (S, i0, g) in enumerate(trades):
        for ri, r in enumerate(rules):
            x = simulate(S, i0, r)
            res[ri][k] = (x["pnl"], x["ret"], x["exit_t"], x["open"])
    live = [simulate(S, i0, rules[live_i], log=True) for S, i0, g in trades]
    print(f"\nsimulated {len(rules)} rules x {len(trades)} trades in {time.time() - t_sim:.0f}s")
    VIEW, SHORT = [live_i], {live_i: "LIVE"}
    for ri, r in enumerate(rules):
        d = [r["prot"] != LIVE_RULE["prot"], r["rt"] != LIVE_RULE["rt"], r["cap"] != LIVE_RULE["cap"], r["tps"] != LIVE_RULE["tps"]]
        if sum(d) == 1:
            VIEW.append(ri)
            SHORT[ri] = (("prot " + (f"{r['prot'][1]:.0%}@{r['prot'][0]:g}x" if r["prot"] else "none")) if d[0] else f"runner {r['rt']:.0%}" if d[1]
                         else f"cap {r['cap']:.0%}" if d[2] else "tp " + next(n for n, t in TP_SETS if t == r["tps"]).replace(" ", ""))[:16]

    # 4. legends replay ------------------------------------------------------------------------------------
    banner(f"3. LEGENDS / COLLAPSES REPLAY WITH THE LIVE EXIT  (entry = first +10% bar >= 6h after launch; stake ${STAKE:.0f})")
    card = []
    for k, (S, i0, g) in enumerate(trades):
        if g == "pool":
            continue
        L = live[k]
        e = S.Cl[i0]
        t_in = S.T[i0] + S.dur
        rest = S.H[i0 + 1:]
        pk_i = max(range(len(rest)), key=rest.__getitem__) + i0 + 1 if rest else i0
        peak_after = S.H[pk_i] / e if rest else 1.0
        run0 = max(S.H[:i0 + 1]) / S.Cl[0] if i0 else 1.0
        bests = sorted(((res[ri][k][1], ri) for ri in range(len(rules))), reverse=True)
        best_ret, best_ri = bests[0]
        d_after = (t_in - S.launch) / DAY
        caught = peak_after >= 10 and d_after <= 60
        kept_peak = L["ret"] / (peak_after - 1) if peak_after > 1.05 else float("nan")
        kept_best = L["ret"] / best_ret if best_ret > 0.01 else float("nan")
        ex_t = L["exit_t"]
        after = [S.H[j] for j in range(len(S.T)) if S.T[j] >= ex_t]
        last_px = L["sells"][-1][1] if L["sells"] else S.Cl[-1]
        second = max(after) / last_px if after and not L["open"] and last_px > 0 else float("nan")
        print(f"\n{S.name} [{S.key}] ({S.group}; {S.src}, {'hourly' if S.dur == HOUR else 'daily'} bars)")
        if S.meta.get("lag", 0) > 3:
            print(f"  NOTE data starts {S.meta['lag']:.0f} days after the launch: the earliest possible entry is not in the data")
        print(f"  ENTRY  {ts(t_in)} UTC, {d_after:.1f} days after {'launch' if S.meta.get('lag', 0) <= 3 else 'data start'}, price {e:.4g} "
              f"(+{S.Cl[i0] / S.Cl[i0 - 1] - 1:.0%} in the bar); the coin had already run {fmt_x(run0)} from its first price")
        for t, px, m, fr, why_ in L["sells"]:
            print(f"  SELL   {ts(t)}  {fr:>4.0%} of the position at {fmt_x(m)} of entry  ({why_})")
        if L["open"]:
            print(f"  still HOLDING at the end of the data ({day(S.T[-1])}), marked at {fmt_x(S.Cl[-1] / e)}")
        print(f"  RESULT {fmt_x(1 + L['ret'])} of the stake ({fmt_d(L['pnl'])} on ${STAKE:.0f}); peak after entry {fmt_x(peak_after)} on {day(S.T[pk_i])}; "
              f"held peak {fmt_x(L['peak'])}; after our last sale it went on to {fmt_x(second)} of that price (second leg)")
        print(f"  CAUGHT?    {'YES' if caught else 'NO '}  ({'entry within 60 days with >= 10x still ahead' if caught else 'less than 10x left after entry' if peak_after < 10 else 'entry too late'})")
        print(f"  MAXIMIZED? kept {pctf(kept_peak) if kept_peak == kept_peak else 'n/a'} of the peak gain, {pctf(kept_best) if kept_best == kept_best else 'n/a'} "
              f"of the best rule in hindsight ('{rules[best_ri]['name']}': {fmt_x(1 + best_ret)})")
        print("  WHERE EACH RULE SOLD (one change vs live):  result x of stake / final exit date")
        cells = []
        for ri in VIEW:
            pnl_, ret_, xt, op = res[ri][k]
            cells.append(f"{SHORT[ri]:<16} {fmt_x(1 + ret_):>8} {'open' if op else day(xt)}")
        for n0 in range(0, len(cells), 3):
            print("    " + "   ".join(f"{c:<38}" for c in cells[n0:n0 + 3]))
        card.append({"coin": S.name, "group": g, "caught": caught, "entry_d": d_after, "peak": peak_after, "live": 1 + L["ret"], "pnl": L["pnl"],
                     "kept_peak": kept_peak, "kept_best": kept_best, "best": rules[best_ri]["name"], "best_x": 1 + best_ret, "k": k})
    for S in series:
        if S.meta.get("i0") is None:
            print(f"\n{S.name}: the entry NEVER fired (no bar >= +10% with >= $100k 24h volume after launch in the data)")
            card.append({"coin": S.name, "group": S.group, "caught": False, "entry_d": None, "peak": None, "live": None, "pnl": 0.0,
                         "kept_peak": float("nan"), "kept_best": float("nan"), "best": "-", "best_x": None, "k": None})

    # pool sample summary with the live rule
    pk = [k for k, t in enumerate(trades) if t[2] == "pool"]
    if pk:
        rets = [live[k]["ret"] for k in pk]
        print(f"\nDud / rug sample with the live exit: {len(pk)} trades, mean {pctf(statistics.mean(rets))}, median {pctf(med(rets))}, "
              f"win {sum(x > 0 for x in rets) / len(rets):.0%}, >= 2x {sum(x >= 1 for x in rets) / len(rets):.0%}, >= 10x {sum(x >= 9 for x in rets) / len(rets):.0%}, "
              f"rug exits {sum(any(s[4] in ('rug', 'dead') for s in live[k]['sells']) for k in pk)}; total {fmt_d(sum(live[k]['pnl'] for k in pk))}")
        pf = [k for k in pk if trades[k][0].meta["pump"]]
        if pf:
            print(f"  pump.fun pools only: {len(pf)} trades, mean {pctf(statistics.mean([live[k]['ret'] for k in pf]))}, "
                  f"median {pctf(med([live[k]['ret'] for k in pf]))}, total {fmt_d(sum(live[k]['pnl'] for k in pf))}")

    # 5. rule ranking ---------------------------------------------------------------------------------------
    banner(f"4. EXIT RULES RANKED BY TOTAL PROFIT ACROSS LEGENDS + COLLAPSES + DUDS  (${STAKE:.0f} stake per trade)")
    groups = {g: [k for k, t in enumerate(trades) if t[2] == g] for g in ("legend", "collapse", "pool")}
    fam = sorted(groups["legend"] + groups["collapse"], key=lambda k: trades[k][0].T[trades[k][1]])
    pls = sorted(groups["pool"], key=lambda k: trades[k][0].T[trades[k][1]])
    A = set(fam[:len(fam) // 2] + pls[:len(pls) // 2])
    B = set(range(len(trades))) - A
    tot = lambda ri, ks: sum(res[ri][k][0] for k in ks)
    allk = list(range(len(trades)))
    stat = []
    for ri in range(len(rules)):
        pnl = [res[ri][k][0] for k in allk]
        best_coin = max(pnl) if pnl else 0
        stat.append({"ri": ri, "tot": sum(pnl), "leg": tot(ri, groups["legend"]), "col": tot(ri, groups["collapse"]), "pool": tot(ri, groups["pool"]),
                     "ex1": sum(pnl) - best_coin, "log": sum(math.log(max(1e-6, (ACCOUNT + x) / ACCOUNT)) for x in pnl),
                     "A": tot(ri, A), "B": tot(ri, B)})
    rank = {key: {s["ri"]: n + 1 for n, s in enumerate(sorted(stat, key=lambda s: -s[key]))} for key in ("tot", "ex1", "log", "A", "B", "pool")}
    L0 = stat[live_i]
    hdr = f"{'rule':<78} {'total':>11} {'legends':>11} {'collapses':>10} {'duds':>9} {'ex-best':>10} {'growth':>7} {'older':>10} {'newer':>10}"

    def row(s):
        return (f"{rules[s['ri']]['name']:<78} {fmt_d(s['tot']):>11} {fmt_d(s['leg']):>11} {fmt_d(s['col']):>10} {fmt_d(s['pool']):>9} "
                f"{fmt_d(s['ex1']):>10} {s['log']:>7.2f} {fmt_d(s['A']):>10} {fmt_d(s['B']):>10}")
    print(f"trades: {len(groups['legend'])} legends, {len(groups['collapse'])} collapses / rugs, {len(groups['pool'])} dud-sample pools. "
          f"ex-best = total without the rule's single best trade; growth = sum of log(account after / before) per trade; "
          f"older / newer = walk-forward halves (each group split at its median entry time)")
    print("\nONE CHANGE AT A TIME vs the live rule:")
    print(hdr)
    print(row(L0) + "   <- LIVE")
    one = []
    for ri, r in enumerate(rules):
        diff = sum([r["prot"] != LIVE_RULE["prot"], r["rt"] != LIVE_RULE["rt"], r["cap"] != LIVE_RULE["cap"], r["tps"] != LIVE_RULE["tps"]])
        if diff == 1:
            one.append(stat[ri])
    for s in sorted(one, key=lambda s: -s["tot"]):
        print(row(s))
    print(f"\nTOP 15 BY TOTAL PROFIT (live rule is #{rank['tot'][live_i]} of {len(rules)}; #{rank['ex1'][live_i]} without the best trade, "
          f"#{rank['log'][live_i]} by growth, #{rank['A'][live_i]} older half, #{rank['B'][live_i]} newer half):")
    print(hdr)
    for s in sorted(stat, key=lambda s: -s["tot"])[:15]:
        print(row(s))
    print("\nTOP 10 BY GROWTH (log; punishes big losses, does not let one 1000x decide):")
    print(hdr)
    for s in sorted(stat, key=lambda s: -s["log"])[:10]:
        print(row(s))
    bestA = max(stat, key=lambda s: s["A"])
    bestB = max(stat, key=lambda s: s["B"])
    print(f"\nWALK-FORWARD: best on the older half = '{rules[bestA['ri']]['name']}' -> newer half {fmt_d(bestA['B'])} (rank #{rank['B'][bestA['ri']]}; "
          f"live {fmt_d(L0['B'])}, rank #{rank['B'][live_i]});  best on the newer half = '{rules[bestB['ri']]['name']}' -> older half "
          f"{fmt_d(bestB['A'])} (rank #{rank['A'][bestB['ri']]}; live {fmt_d(L0['A'])})")
    # robust winner: beats live on total, ex-best, growth, both halves, and does not lose more on the duds
    margin = lambda x, y: x > y + 0.03 * abs(y)
    robust = [s for s in stat if s["ri"] != live_i and margin(s["tot"], L0["tot"]) and s["ex1"] > L0["ex1"] and s["log"] >= L0["log"]
              and s["A"] > L0["A"] and s["B"] >= L0["B"] and s["pool"] >= L0["pool"] - 0.02 * STAKE * max(1, len(groups["pool"]))]
    win = max(robust, key=lambda s: s["tot"]) if robust else None
    print(f"\nROBUST (beats live on total by > 3%, without the best trade, on growth, in BOTH halves, and costs at most 2% of stake per dud-trade): "
          f"{len(robust)} rules" + (f"; best: '{rules[win['ri']]['name']}'" if win else " -> keep the live rule"))
    # marginal dimension views (averaged over the others)
    print("\nEACH SETTING AVERAGED OVER ALL OTHER SETTINGS (total $ per rule):")
    for dim, vals in (("prot", sorted({str(r["prot"]) for r in rules})), ("rt", sorted({str(r["rt"]) for r in rules})),
                      ("cap", sorted({str(r["cap"]) for r in rules})), ("tps", [str(t) for _, t in TP_SETS])):
        parts = []
        for v in vals:
            xs = [stat[ri]["tot"] for ri, r in enumerate(rules) if str(r[dim]) == v]
            lab = next((n for n, t in TP_SETS if str(t) == v), v) if dim == "tps" else v
            parts.append(f"{lab}: {fmt_d(statistics.mean(xs))}")
        print(f"  {dim:<5} " + " | ".join(parts))

    # 6. screen check --------------------------------------------------------------------------------------
    banner("5. LEGENDS SCREEN CHECK  (config.DEX['screen']: top-10 <= %.0f%%, LP locked >= %.0f%% on young pools, no mint / freeze / "
           "blacklist, taxes <= %.0f%%)" % (SCR.get("max_top10_pct", 0.4) * 100, SCR.get("min_lp_locked", 0.95) * 100, SCR.get("max_tax", 0.03) * 100))
    print("VERIFIED = rebuilt from on-chain logs or read from a live API in this run; TODAY = today's contract state (code does not "
          "change, owners may have renounced since); ASSUMED = public history, not checked here; UNKNOWN = no free data")
    screen_deadline = min(hard, time.time() + a.screen_min * 60)
    if not a.synthetic:
        net.deadline = screen_deadline
    verdict = {}
    fixcheck = []
    for coin in COINS:
        if coin["kind"] == "collapse" and coin["sym"] in ("LUNC", "FTT"):
            continue
        print(f"\n{coin['sym']} ({coin['chain'] or '-'} {coin['addr'] or ''})")
        lines, fails, unknown = [], [], []
        if coin.get("note"):
            lines.append(f"  ASSUMED  {coin['note']}")
        if coin["chain"] in RPCS and coin["addr"] and time.time() < screen_deadline:
            rpc = RPC(net, coin["chain"], screen_deadline)
            try:
                left = sum(1 for c2 in COINS[COINS.index(coin):] if c2["chain"] in RPCS and c2["addr"]) + 4
                h = evm_history(rpc, coin["addr"], coin["launch"], budget_s=max(60, min(420, (screen_deadline - time.time()) / left)) if not a.synthetic else 30)
            except Exception as ex:
                h = {"err": f"error {type(ex).__name__}: {str(ex)[:60]}"}
            if h.get("err"):
                lines.append(f"  UNKNOWN  on-chain history: {h['err']}")
                unknown.append("holders")
            else:
                for x in h["notes"]:
                    lines.append(f"  VERIFIED {x}" if "[verified]" in x else f"  NOTE     {x}")
                for lab, s in h["snaps"]:
                    if not s:
                        continue
                    ok = s["top10"] <= SCR.get("max_top10_pct", 0.4)
                    lp = "" if s["lp"] is None else f", LP burned/locked {s['lp']:.0%} ({'ok' if s['lp'] >= SCR.get('min_lp_locked', 0.95) else 'FAIL'})"
                    tops = ", ".join(f"{ad[:8]}..{' (Vitalik)' if ad == VITALIK else ''} {sh:.0%}{'' if sent else ' passive'}" for ad, sh, sent in s["top"])
                    lines.append(f"  VERIFIED {lab}: top-10 {s['top10']:.0%} ({'ok' if ok else 'FAIL'}); without Vitalik's wallet "
                                 f"{s['top10_famous']:.0%}; without passive wallets {s['top10_fix']:.0%}; {s['holders']} holders{lp}; largest: {tops}"
                                 + (f"  [{s['neg']} negative balances: reflection / rebase token, approximate]" if s["neg"] else ""))
                    if not ok:
                        fails.append(f"top-10 {s['top10']:.0%} on {lab}")
                    if s["lp"] is not None and s["lp"] < SCR.get("min_lp_locked", 0.95):
                        fails.append(f"LP locked {s['lp']:.0%} on {lab}")
                if h["owner"]:
                    ren = [b for b, o in h["owner"] if o == ZERO]
                    lines.append(f"  VERIFIED ownership events: {len(h['owner'])}; " + (f"renounced in block {ren[0]} (~{(ren[0] - h['cb']) * h['bt'] / 3600:.0f}h after creation)"
                                                                                      if ren else "NOT renounced in the window"))
                else:
                    lines.append("  VERIFIED no OwnershipTransferred events in the window (no owner role, or a non-standard one)")
        # today's flags
        if coin["addr"] and time.time() < screen_deadline:
            if coin["chain"] in CHAIN_ID:
                body = net.get(f"https://api.gopluslabs.io/api/v1/token_security/{CHAIN_ID[coin['chain']]}?contract_addresses={coin['addr']}")
                d = ((body or {}).get("result") or {}) if isinstance(body, dict) else {}
                d = d.get(coin["addr"].lower()) if isinstance(d, dict) else None
                if isinstance(d, dict) and DX:
                    fl = [f for f, _ in DX.check_goplus_evm(d, DX.DEX["screen"]) if not any(w in f for w in ("holders", "lp ", "creator", "owner_percent"))]
                    lines.append(f"  TODAY    GoPlus contract flags: {', '.join(fl) if fl else 'none'}  (buy tax {d.get('buy_tax')!r}, sell tax "
                                 f"{d.get('sell_tax')!r}, owner {str(d.get('owner_address') or '-')[:10]})")
                    fails += [f"today: {f}" for f in fl if any(w in f for w in ("tax", "mint", "blacklist", "honeypot", "proxy", "pausable"))]
                else:
                    lines.append("  UNKNOWN  GoPlus: no answer")
            elif coin["chain"] == "solana":
                body = net.get(f"https://api.rugcheck.xyz/v1/tokens/{coin['addr']}/report/summary")
                if isinstance(body, dict) and DX:
                    fl = DX.check_rugcheck(body, DX.DEX["screen"])
                    lines.append(f"  TODAY    RugCheck: {', '.join(f for f, _ in fl) if fl else 'passes'} (score {body.get('score_normalised')}, "
                                 f"LP locked {body.get('lpLockedPct')}%; risks: {', '.join(str(r.get('name')) for r in body.get('risks') or [] if isinstance(r, dict))[:120]})")
                else:
                    lines.append("  UNKNOWN  RugCheck: no answer")
                unknown.append("launch-day holders / LP (Solana history not reconstructable with free APIs)")
        if coin["chain"] is None:
            unknown.append("not a DEX token")
        v = "FAIL" if fails else "UNKNOWN" if unknown or not coin["addr"] else "PASS"
        verdict[coin["sym"]] = (v, fails, unknown)
        for x in lines:
            print(x)
        print(f"  => {v}" + (f": {'; '.join(fails[:4])}" if fails else f" ({'; '.join(unknown)})" if unknown else ""))
    # narrow fix check on rugged sample pools (EVM only)
    rugged = [S for S in pools if S.meta.get("rugged") and S.meta["net"] in ("eth", "base")][:8]
    if rugged and time.time() < screen_deadline:
        print("\nPROPOSED FIXES CHECKED ON RUGGED POOLS FROM THE SAMPLE (day 1): (a) 'ignore Vitalik's wallet' is too narrow to matter for "
              "rugs (a gift to Vitalik is not held by the dev); (b) 'ignore passive wallets (never sent a token)' is broad - does it let rugs pass?")
        for S in rugged:
            if time.time() > screen_deadline:
                break
            p = S.meta["p"]
            rpc = RPC(net, {"eth": "eth", "base": "base"}[p["net"]], screen_deadline)
            try:
                h = evm_history(rpc, p["token"], p["created"], days=(1,), budget_s=150 if not a.synthetic else 10)
            except Exception as ex:
                h = {"err": type(ex).__name__}
            s = next((s for _, s in (h.get("snaps") or []) if s), None)
            if not s:
                print(f"  {S.name:<12} {p['token'][:12]}..: no on-chain data ({h.get('err', 'no snapshot')})")
                continue
            fixcheck.append((s["top10"], s["top10_fix"]))
            lim = SCR.get("max_top10_pct", 0.4)
            print(f"  {S.name:<12} {p['token'][:12]}..: top-10 {s['top10']:.0%} ({'fails' if s['top10'] > lim else 'passes'} today's rule), "
                  f"without passive wallets {s['top10_fix']:.0%} -> "
                  f"{'still FAILS' if s['top10_fix'] > lim else 'PASSES with the fix' + (' (fix lets it through!)' if s['top10'] > lim else '')}; "
                  f"LP burned/locked {'n/a' if s['lp'] is None else format(s['lp'], '.0%')}")

    # 7. summary ---------------------------------------------------------------------------------------------
    banner("6. SUMMARY IN PLAIN WORDS")
    print(f"Sources: " + ", ".join(f"{k} {v or 'none'}" for k, v in src_log.items()))
    print(f"Network: {net.report()}")
    print(f"\nSCORECARD (live exit; stake ${STAKE:.0f}; maximized = share of the achievable gain kept, vs the peak and vs the best rule in hindsight)")
    print(f"{'coin':<26} {'kind':<9} {'caught':<7} {'entry day':>9} {'peak':>9} {'live':>9} {'$ P&L':>9} {'kept/peak':>9} {'kept/best':>9}  "
          f"{'screen':<8} best rule in hindsight")
    for c in card:
        sym = next((x["sym"] for x in COINS if c["coin"].startswith(x["name"])), "")
        v = verdict.get(sym, ("-",))[0]
        ed = f"{c['entry_d']:.1f}" if c["entry_d"] is not None else "never"
        mark = "✅" if c["caught"] else "❌"
        print(f"{c['coin'][:26]:<26} {c['group']:<9} {mark:<6} {ed:>9} "
              f"{fmt_x(c['peak']):>9} {fmt_x(c['live']):>9} {fmt_d(c['pnl']):>9} {pctf(c['kept_peak']):>9} {pctf(c['kept_best']):>9}  {v:<8} {c['best'][:60]}")
    leg = [c for c in card if c["group"] == "legend"]
    if leg:
        print(f"\nLegends caught early (entry within 60 days, >= 10x still ahead): {sum(c['caught'] for c in leg)} of {len(leg)}; "
              f"median share of the peak gain kept {pctf(med([c['kept_peak'] for c in leg if c['kept_peak'] == c['kept_peak']]))}, "
              f"of the best rule {pctf(med([c['kept_best'] for c in leg if c['kept_best'] == c['kept_best']]))}")
    col = [c for c in card if c["group"] == "collapse" and c["live"] is not None]
    if col:
        print("Collapses / rugs: live exit " + ", ".join(f"{c['coin']} {fmt_x(c['live'])}" for c in col))
    print(f"\nLive rule totals: {fmt_d(L0['tot'])} over {len(trades)} trades (legends {fmt_d(L0['leg'])}, collapses {fmt_d(L0['col'])}, "
          f"duds {fmt_d(L0['pool'])}); rank #{rank['tot'][live_i]} of {len(rules)} by total, #{rank['log'][live_i]} by growth, "
          f"#{rank['A'][live_i]} / #{rank['B'][live_i]} in the older / newer half.")
    capx = {c: statistics.mean([stat[ri]["tot"] for ri, r in enumerate(rules) if r["cap"] == c]) for c in (None, 0.20, 0.25, 0.33)}
    print("Concentration cap (averaged over the other settings): " + ", ".join(f"{'none' if c is None else format(c, '.0%')} {fmt_d(v)}" for c, v in capx.items())
          + ". A cap only banks GAINS: it cannot protect a fresh position that collapses inside the 14-day no-stop hold (the stake size is "
            "that protection: at most 20% of the account per coin).")
    if fixcheck:
        still = sum(f > SCR.get("max_top10_pct", 0.4) for _, f in fixcheck)
        print(f"Passive-wallet fix on {len(fixcheck)} rugged sample pools: {still} still fail the top-10 rule, {len(fixcheck) - still} would pass "
              f"({'fix looks safe on this sample' if still == len(fixcheck) else 'fix would let some rugs through - do NOT apply as is'}).")
    blocked = [s for s, (v, f, _) in verdict.items() if v == "FAIL" and next((c["kind"] for c in COINS if c["sym"] == s), "") == "legend"]
    if blocked:
        print(f"Legends the screen would have BLOCKED at launch (verified / today's flags): {', '.join(blocked)}.")
    print("\nRECOMMENDATION for config.DEX['exit']:")
    if win:
        r = rules[win["ri"]]
        steps = [r["prot"]] if r["prot"] else []
        tp = list(r["tps"])
        ex = {"trail": XC.get("trail", 0.95), "tp1": (tp[0][0] - 1, tp[0][1]) if tp else (999.0, 0.0),
              "ladder": [(m - 1, f) for m, f in tp[1:]], "trail_steps": steps, "max_hold_days": XC.get("max_hold_days", 14),
              "runner_at_limit": ((XC.get("runner_at_limit") or (1.0, 0.5))[0], r["rt"]), "liq_pull": XC.get("liq_pull", 0.5), "rug_tax": XC.get("rug_tax", 0.5)}
        print(f"  CHANGE to '{r['name']}': total {fmt_d(win['tot'])} vs live {fmt_d(L0['tot'])}, without the best trade {fmt_d(win['ex1'])} vs "
              f"{fmt_d(L0['ex1'])}, growth {win['log']:.2f} vs {L0['log']:.2f}, older half {fmt_d(win['A'])} vs {fmt_d(L0['A'])}, newer half "
              f"{fmt_d(win['B'])} vs {fmt_d(L0['B'])}, duds {fmt_d(win['pool'])} vs {fmt_d(L0['pool'])}.")
        print(f'  "exit": {ex},')
        if r["cap"]:
            print(f"  plus a concentration cap of {r['cap']:.0%} of equity - NOT a config key yet: dex.py needs a small change "
                  f"(sell a position back to {r['cap']:.0%} of equity whenever it grows past it).")
        if tp:
            print("  (take-profits map onto dex.py's tp1 + ladder: fractions are of the position left; after tp1 dex.py no longer applies "
                  "the 14-day clock - simulated that way here)")
    else:
        print(f"  KEEP the live exit {XC}: no rule beat it on total profit AND without its best trade AND on growth AND in both "
              f"walk-forward halves without costing more on the duds.")
        if rank["tot"][live_i] > 1:
            t1 = max(stat, key=lambda s: s["tot"])
            print(f"  (highest raw total: '{rules[t1['ri']]['name']}' {fmt_d(t1['tot'])}, but it fails the robustness checks above: "
                  f"ex-best {fmt_d(t1['ex1'])} vs {fmt_d(L0['ex1'])}, growth {t1['log']:.2f} vs {L0['log']:.2f}, halves {fmt_d(t1['A'])} / "
                  f"{fmt_d(t1['B'])} vs {fmt_d(L0['A'])} / {fmt_d(L0['B'])})")
    print("\nCAVEATS: legends are picked in hindsight (the whole point: would we have held them?); CEX-aggregator data often starts days "
          "after the DEX launch and has no liquidity, holders or buy/sell counts, so entries use price + volume only; daily data "
          "makes trails coarser; the dud sample is a few hundred recent pools (survivorship: pools that died before the registry saw them "
          "are missing). Rank the rules, don't read the dollar totals as a forecast.")
    try:
        if not a.synthetic:
            os.makedirs(os.path.dirname(a.data_out) or ".", exist_ok=True)
            with gzip.open(a.data_out, "wt") as f:
                json.dump(daily_dump, f, separators=(",", ":"))
            print(f"\nwrote daily bars of {len(daily_dump)} coins to {a.data_out} (for offline re-analysis)")
    except Exception as ex:
        print(f"could not write {a.data_out}: {ex}")
    print(f"({time.time() - t_start:.0f}s)")


if __name__ == "__main__":
    main()
