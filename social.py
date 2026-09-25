"""Social "heat" tracker: records attention for every Crypto.com USD coin (no free history
exists, so we build our own going forward) and trades the hottest ones on paper.

Sources (all keyless, all optional via config.SOCIAL; each polled on its own interval):
    coingecko    GET api.coingecko.com/api/v3/search/trending   (top-15 searched, ~15 min)
    cmc          CoinMarketCap: no keyless trending endpoint is documented in the research
                 notes -> off by default; set config.SOCIAL["cmc_url"] once one is verified
    reddit       GET reddit.com/r/<sub>/new.json?limit=100 per sub (~15 min); ticker/name
                 mentions in title + text; short/common tickers need a $ prefix or a name match
    dexscreener  token-boosts/top|latest, token-profiles/latest (rotating) + tokens/v1 lookup
                 for symbols (~5 min); boosts are paid ads -> low weight
    geckoterminal /networks/trending_pools?duration=5m|1h (~10 min; organic)

    tracker = HeatTracker(universe=coins)     # coins = Crypto.com base symbols
    tracker.poll()                            # call every second; polls at most ONE overdue
                                              # source (<= 2 HTTP calls, timeout <= 8s), so the
                                              # engine's 1-second stop checks are never starved
    tracker.heat()                            # ranked [{coin, score, trend, reddit, dex, ...}]
    python social.py [--check]                # one live round + heat table (or self-check only)

Files: data/social/heat.csv (one row per coin/source/round: time, coin, source, rank,
mentions; rolled to heat_YYYY-MM.csv monthly or at 20 MB), data/social/state.json (rolling
windows), data/social/dex_watch.json (DEX-trending tokens NOT on Crypto.com: a watchlist).

Heat score 0-100 = trend (0-40: CoinGecko/CMC trending rank) + reddit (0-40: mentions in the
last hour vs the 24h hourly baseline, min count) + dex (0-20: GeckoTerminal rank + boosted).
Nothing here raises into the engine loop: every fetch/parse failure is logged and skipped.
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request

import config
from engine import append_csv, ts
from scanner import excluded

MIN = 60_000
HOUR = 3_600_000
DAY = 24 * HOUR
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36 crypto-paper-trader/1.0 (social heat research; paper trading)")

DEFAULTS = {
    "coingecko": True, "cmc": False, "reddit": True, "dex": True,
    "cmc_url": "",                   # keyless CMC trending URL, once verified (see module doc)
    "subreddits": ["CryptoMoonShots", "SatoshiStreetBets", "CryptoCurrency", "memecoins"],
    "poll_min": {"coingecko": 15, "cmc": 15, "reddit": 15, "dexscreener": 5, "geckoterminal": 10},
    "timeout": 8,                    # seconds per HTTP call (hard cap: 8)
    "dir": "data/social",
    "csv_cap_mb": 20,                # roll heat.csv early if it grows past this
    "ttl_min": {"trend": 45, "dex": 30},   # how long a trending/boosted sighting counts
    "reddit_min_mentions": 3,        # ignore 1-2 stray mentions
    "reddit_full": 8.0,              # 8x the hourly baseline = full reddit score
    # social_heat test account
    "enter": 50, "floor": 20, "floor_hours": 12,    # buy at >= 50; sell after 12h below 20
    "trail": 0.25, "max_hold_days": 10, "min_24h_change": -0.10, "slots": 5,
}
SOCIAL = dict(DEFAULTS, **getattr(config, "SOCIAL", {}))

# Well-known coin names (lower case) for mention counting; CoinGecko trending adds more at runtime.
NAMES = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple", "ADA": "cardano",
    "DOGE": "dogecoin", "SHIB": "shiba inu", "PEPE": "pepe", "BONK": "bonk", "WIF": "dogwifhat",
    "FLOKI": "floki", "LTC": "litecoin", "AVAX": "avalanche", "LINK": "chainlink", "DOT": "polkadot",
    "TRX": "tron", "TON": "toncoin", "APT": "aptos", "HBAR": "hedera", "XLM": "stellar",
    "PNUT": "peanut the squirrel", "MOODENG": "moo deng", "POPCAT": "popcat", "FARTCOIN": "fartcoin",
    "SPX": "spx6900", "PENGU": "pudgy penguins", "HYPE": "hyperliquid", "TAO": "bittensor",
    "ENA": "ethena", "ARB": "arbitrum", "NEAR": "near protocol", "ATOM": "cosmos", "UNI": "uniswap",
    "AAVE": "aave", "CRO": "cronos", "BCH": "bitcoin cash", "POL": "polygon", "ALGO": "algorand",
    "FIL": "filecoin", "INJ": "injective", "SEI": "sei network", "TIA": "celestia", "ONDO": "ondo",
    "NEIRO": "neiro", "GOAT": "goatseus maximus", "MOG": "mog coin", "BRETT": "brett",
    "TRUMP": "official trump", "SUI": "sui network", "OP": "optimism", "JUP": "jupiter", "FET": "fetch.ai",
}
# Tickers/names that are also ordinary words: count them only as $TICKER or by full name.
COMMON = {"ONE", "GAS", "ME", "AI", "OP", "ARB", "SAND", "MANA", "NEAR", "LINK", "DOT", "ATOM", "APT",
          "SEI", "ENA", "POL", "HYPE", "GRT", "CRO", "JUP", "ACT", "MOON", "PUMP", "BAN", "CAT", "DOG",
          "GAME", "PLAY", "SUN", "TIME", "FUN", "HOT", "PAY", "BOOK", "BAND", "CAKE", "CORE", "BLUR",
          "RAY", "STEP", "LOOKS", "PORT", "FLOW", "ROSE", "MASK", "LIT", "DASH", "WIN", "TRUE", "MAGIC",
          "PEOPLE", "ZERO", "MOVE", "ORDER", "BOND", "COMP", "WAVES", "HIGH", "DEGEN", "WHY", "ALPHA",
          "BETA", "BEAM", "GOAT", "BRETT", "TURBO", "TRUMP", "MOG",
          "RENDER", "COSMOS", "STELLAR", "OPTIMISM", "JUPITER", "PEANUT", "ONDO", "SUI", "TON", "APE",
          "ARK", "LUNA", "LUNC", "OM", "IO", "W", "S", "T", "G", "A", "ETF", "USD", "CEO", "DEX", "CEX",
          "NFT", "USA", "UTC", "AM", "PM", "IMO", "DYOR", "ATH", "ATL", "FOMO", "LOL", "OK", "TL", "DR",
          "NEW", "TOP", "BIG", "LOW", "BUY", "SELL", "HOLD", "HODL", "SAFE", "MEME", "DAO", "APP", "AND",
          "THE", "FOR", "ALL", "NOW", "YOU", "ARE", "NOT", "BUT", "CAN", "GET", "OUT", "SOON", "REAL"}
_CASHTAG_RE = re.compile(r"\$([A-Za-z][A-Za-z0-9]{1,9})\b")
_WORD_RE = re.compile(r"(?<![A-Za-z0-9$])([A-Z][A-Z0-9]{1,9})(?![A-Za-z0-9])")   # bare UPPERCASE ticker


def _f(x):
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


# ---- HTTP ----------------------------------------------------------------------------------
def http_get(url, timeout=8):
    """(status, text). Never raises: network errors come back as (0, message)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=min(timeout, 8)) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, str(e)[:120]


def _json(text):
    try:
        return json.loads(text) if text else None
    except ValueError:
        return None


# ---- parsers (pure; each returns [{coin, name, rank, extra}] sightings) -------------------
def parse_coingecko(body):
    """/search/trending: coins[i].item {id, name, symbol, market_cap_rank, score}; rank 1 = hottest."""
    body = _json(body) if isinstance(body, str) else body
    out = []
    for i, c in enumerate((body or {}).get("coins") or []):
        it = c.get("item") if isinstance(c, dict) else None
        if not isinstance(it, dict) or not it.get("symbol"):
            continue
        sc = it.get("score")
        rank = int(sc) + 1 if isinstance(sc, (int, float)) else i + 1
        out.append({"coin": str(it["symbol"]).upper(), "name": str(it.get("name") or "").lower(),
                    "rank": rank, "id": it.get("id")})
    return out


def parse_cmc(body):
    """Best-effort for a CMC trending payload: data[] or data.cryptoCurrencyList[] with symbol/name."""
    body = _json(body) if isinstance(body, str) else body
    d = (body or {}).get("data")
    if isinstance(d, dict):
        d = d.get("cryptoCurrencyList") or d.get("list") or []
    out = []
    for i, c in enumerate(d or []):
        if isinstance(c, dict) and c.get("symbol"):
            out.append({"coin": str(c["symbol"]).upper(), "name": str(c.get("name") or "").lower(),
                        "rank": i + 1})
    return out


def parse_reddit(body):
    """/r/<sub>/new.json -> [{id, t (ms), text}] newest first."""
    body = _json(body) if isinstance(body, str) else body
    out = []
    for ch in ((body or {}).get("data") or {}).get("children") or []:
        d = ch.get("data") if isinstance(ch, dict) else None
        if not isinstance(d, dict) or not d.get("id"):
            continue
        t = _f(d.get("created_utc"))
        out.append({"id": d["id"], "t": int(t * 1000) if t else None,
                    "text": f"{d.get('title') or ''}\n{(d.get('selftext') or '')[:2000]}"})
    return out


def parse_dex_list(body):
    """DexScreener boosts/profiles: [{chainId, tokenAddress, ...}] -> [(chain, address)] in order."""
    body = _json(body) if isinstance(body, str) else body
    if isinstance(body, dict):
        body = body.get("data") or body.get("pairs") or []
    out, seen = [], set()
    for x in body or []:
        if isinstance(x, dict) and x.get("chainId") and x.get("tokenAddress"):
            key = (x["chainId"], x["tokenAddress"])
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out


def parse_dex_tokens(body):
    """DexScreener tokens/v1: pairs -> {address: {coin, name, chain, liq, vol24, chg24}} (best pair)."""
    body = _json(body) if isinstance(body, str) else body
    if isinstance(body, dict):
        body = body.get("pairs") or []
    out = {}
    for p in body or []:
        bt = p.get("baseToken") if isinstance(p, dict) else None
        if not isinstance(bt, dict) or not bt.get("symbol") or not bt.get("address"):
            continue
        liq = _f((p.get("liquidity") or {}).get("usd")) or 0.0
        cur = out.get(bt["address"])
        if cur is None or liq > cur["liq"]:
            out[bt["address"]] = {"coin": str(bt["symbol"]).upper(), "name": str(bt.get("name") or "").lower(),
                                  "chain": p.get("chainId"), "liq": liq,
                                  "vol24": _f((p.get("volume") or {}).get("h24")),
                                  "chg24": _f((p.get("priceChange") or {}).get("h24"))}
    return out


def parse_geckoterminal(body):
    """/networks/trending_pools: data[].attributes.name "PEPE / WETH" -> sightings ranked in order."""
    body = _json(body) if isinstance(body, str) else body
    out = []
    for i, p in enumerate((body or {}).get("data") or []):
        a = p.get("attributes") if isinstance(p, dict) else None
        if not isinstance(a, dict) or not a.get("name"):
            continue
        sym = str(a["name"]).split("/")[0].strip().upper()
        sym = re.sub(r"\s+\d+(\.\d+)?%$", "", sym)     # "PEPE 0.3%" fee-tier suffix on some pools
        if not sym:
            continue
        net = ((p.get("relationships") or {}).get("network") or {}).get("data") or {}
        tid = ((p.get("relationships") or {}).get("base_token") or {}).get("data") or {}
        out.append({"coin": sym, "name": "", "rank": i + 1, "chain": net.get("id") or str(tid.get("id", "")).split("_")[0],
                    "liq": _f(a.get("reserve_in_usd")), "vol24": _f((a.get("volume_usd") or {}).get("h24")),
                    "chg24": _f((a.get("price_change_percentage") or {}).get("h24"))})
    return out


# ---- mention extraction ----------------------------------------------------------------
def extract_mentions(text, universe, names=None):
    """Coins from `universe` mentioned in text (each at most once). Rules:
    $TICKER (any case) always counts; a bare ticker counts only when UPPERCASE, >= 4 chars and
    not a common word; a coin name (>= 5 chars, not a common word) counts case-insensitively."""
    uni = set(universe)
    found = set(m.upper() for m in _CASHTAG_RE.findall(text)) & uni
    for w in set(_WORD_RE.findall(text)):
        if w in uni and len(w) >= 4 and w not in COMMON:
            found.add(w)
    low = text.lower()
    for coin, name in dict(NAMES, **(names or {})).items():
        if coin in uni and coin not in found and len(name) >= 5 and name.upper() not in COMMON \
                and re.search(r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])", low):
            found.add(coin)
    return found


# ---- collectors -------------------------------------------------------------------------
class Collector:
    """One polled source. run(now) -> (status, sightings, note) via fetch(url) -> (status, text).
    Backs off on 429/403 (15 min doubling to 6 h) and on other failures (2 min doubling to 1 h)."""
    kind = "trend"          # which ttl applies to its sightings
    max_calls = 1

    def __init__(self, name, every_min, fetch=http_get, timeout=8):
        self.name, self.every, self.fetch, self.timeout = name, every_min * MIN, fetch, min(timeout, 8)
        self.next_at, self.fails, self.status = 0, 0, None

    def due(self, now):
        return now >= self.next_at

    def get(self, url):
        st, body = self.fetch(url, self.timeout)
        self.status = st
        return st, body

    def poll(self, now, tracker):
        try:
            st, sights, note = self.run(now, tracker)
        except Exception as e:                        # a parser bug must never kill the loop
            st, sights, note = -1, [], f"error {e}"[:120]
        ok = st == 200
        if ok:
            self.fails, self.next_at = 0, now + self.every
        else:
            self.fails += 1
            base, cap = (15 * MIN, 6 * HOUR) if st in (429, 403) else (2 * MIN, HOUR)
            self.next_at = now + min(cap, base * 2 ** (self.fails - 1))
        return st, sights, note

    def run(self, now, tracker):     # -> (status, [sighting], note)
        raise NotImplementedError


class CoinGecko(Collector):
    URL = "https://api.coingecko.com/api/v3/search/trending"

    def run(self, now, tracker):
        st, body = self.get(self.URL)
        s = parse_coingecko(body) if st == 200 else []
        for x in s:                                  # learn names for mention counting
            if x["name"] and x["coin"] in tracker.universe:
                tracker.state["names"][x["coin"]] = x["name"]
        return st, s, f"{len(s)} trending"


class CMC(Collector):
    def __init__(self, url, **kw):
        super().__init__("cmc", **kw)
        self.url = url

    def run(self, now, tracker):
        st, body = self.get(self.url)
        s = parse_cmc(body) if st == 200 else []
        return st, s, f"{len(s)} trending"


class Reddit(Collector):
    kind = "reddit"

    def __init__(self, sub, **kw):
        super().__init__(f"reddit/{sub}", **kw)
        self.url = f"https://www.reddit.com/r/{sub}/new.json?limit=100&raw_json=1"

    def run(self, now, tracker):
        st, body = self.get(self.url)
        if st != 200:
            return st, [], ""
        seen, counts, new = tracker.state["seen_posts"], {}, 0
        for p in parse_reddit(body):
            key = f"{self.name}:{p['id']}"
            if key in seen or (p["t"] and now - p["t"] > DAY):
                continue
            seen[key] = now
            new += 1
            for coin in extract_mentions(p["text"], tracker.universe, tracker.state["names"]):
                counts[coin] = counts.get(coin, 0) + 1
        return st, [{"coin": c, "name": "", "mentions": n} for c, n in counts.items()], f"{new} new posts"


class DexScreener(Collector):
    kind = "dex"
    max_calls = 2
    BASE = "https://api.dexscreener.com"
    LISTS = ["token-boosts/top/v1", "token-boosts/latest/v1", "token-profiles/latest/v1"]

    def __init__(self, **kw):
        super().__init__("dexscreener", **kw)
        self.i = 0

    def run(self, now, tracker):
        path = self.LISTS[self.i % len(self.LISTS)]
        self.i += 1
        st, body = self.get(f"{self.BASE}/{path}")
        if st != 200:
            return st, [], path
        toks = parse_dex_list(body)
        if not toks:
            return st, [], f"{path}: empty"
        chain = max({c for c, _ in toks}, key=lambda c: sum(1 for x in toks if x[0] == c))
        addrs = [a for c, a in toks if c == chain][:30]     # tokens/v1 takes up to 30 addresses
        st2, body2 = self.get(f"{self.BASE}/tokens/v1/{chain}/{','.join(addrs)}")
        if st2 != 200:
            return st2, [], f"{path}: tokens lookup"
        info = parse_dex_tokens(body2)
        out = []
        for i, a in enumerate(addrs):
            if a in info:
                out.append(dict(info[a], rank=i + 1))
        return st, out, f"{path}: {len(out)}/{len(addrs)} {chain} tokens"


class GeckoTerminal(Collector):
    kind = "dex"
    BASE = "https://api.geckoterminal.com/api/v2/networks/trending_pools"

    def __init__(self, duration, **kw):
        super().__init__(f"geckoterminal_{duration}", **kw)
        self.url = f"{self.BASE}?duration={duration}"

    def run(self, now, tracker):
        st, body = self.get(self.url)
        s = parse_geckoterminal(body) if st == 200 else []
        return st, s, f"{len(s)} pools"


# ---- tracker ---------------------------------------------------------------------------
_EMPTY = {"names": {}, "seen_posts": {}, "mentions": {}, "sightings": {}, "last_hot": {},
          "csv_month": None, "status": {}}


class HeatTracker:
    def __init__(self, params=None, universe=None, fetch=http_get, now_ms=None):
        self.p = dict(SOCIAL, **(params or {}))
        self.dir = self.p["dir"]
        self.universe = set(universe or config.BREAKOUT_UNIVERSE)
        self.state = None
        self.dex_watch = {}
        self.collectors = self._build(fetch)
        self._load()
        self.now = now_ms or int(time.time() * 1000)

    def _build(self, fetch):
        p, pm, cs = self.p, self.p["poll_min"], []
        kw = {"fetch": fetch, "timeout": p["timeout"]}
        if p["coingecko"]:
            cs.append(CoinGecko("coingecko", pm["coingecko"], **kw))
        if p["cmc"] and p["cmc_url"]:
            cs.append(CMC(p["cmc_url"], every_min=pm["cmc"], **kw))
        if p["reddit"]:
            cs += [Reddit(s, every_min=pm["reddit"], **kw) for s in p["subreddits"]]
        if p["dex"]:
            cs.append(DexScreener(every_min=pm["dexscreener"], **kw))
            cs += [GeckoTerminal(d, every_min=pm["geckoterminal"], **kw) for d in ("5m", "1h")]
        return cs

    # ---- persistence ----
    def _load(self):
        self.state = json.loads(json.dumps(_EMPTY))
        for fn, target in (("state.json", "state"), ("dex_watch.json", "dex_watch")):
            path = f"{self.dir}/{fn}"
            try:
                if os.path.exists(path):
                    with open(path) as f:
                        getattr(self, target).update(json.load(f))
            except Exception as e:
                print(f"   social: could not read {path}: {e}")

    def save(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            for fn, obj in (("state.json", self.state), ("dex_watch.json", self.dex_watch)):
                tmp = f"{self.dir}/{fn}.tmp"
                with open(tmp, "w") as f:
                    json.dump(obj, f)
                os.replace(tmp, f"{self.dir}/{fn}")
        except Exception as e:
            print(f"   social: save failed: {e}")

    def _csv(self, rows, now):
        """Append rows to heat.csv; roll it monthly (heat_YYYY-MM.csv) or when it passes the size cap."""
        path, month = f"{self.dir}/heat.csv", time.strftime("%Y-%m", time.gmtime(now / 1000))
        st = self.state
        if os.path.exists(path):
            if st.get("csv_month") and st["csv_month"] != month:
                os.replace(path, f"{self.dir}/heat_{st['csv_month']}.csv")
            elif os.path.getsize(path) > self.p["csv_cap_mb"] * 1e6:
                os.replace(path, f"{self.dir}/heat_{month}_{now // 1000}.csv")
        st["csv_month"] = month
        append_csv(path, rows)

    # ---- polling ----
    def due(self, now=None):
        now = now or int(time.time() * 1000)
        return [c for c in self.collectors if c.due(now)]

    def poll(self, now=None, all_due=False):
        """Poll the most overdue collector (or every due one). Returns the names polled."""
        now = now or int(time.time() * 1000)
        self.now = now
        due = sorted(self.due(now), key=lambda c: c.next_at)
        if not due:
            return []
        polled = []
        for c in (due if all_due else due[:1]):
            st, sights, note = c.poll(now, self)
            self.state["status"][c.name] = {"code": st, "t": ts(now), "note": note}
            polled.append(c.name)
            if st != 200:
                print(f"   social: {c.name} HTTP {st} {note} (retry in {(c.next_at - now) // MIN} min)")
                continue
            self._ingest(c, sights, now)
        self._prune(now)
        self._mark_hot(now)
        self.save()
        return polled

    def _ingest(self, c, sights, now):
        rows = []
        for s in sights:
            coin = s["coin"]
            if coin not in self.universe or excluded(coin):
                if c.kind == "dex":                     # not on Crypto.com: watchlist only
                    w = self.dex_watch.get(coin) or {"first": ts(now), "n": 0}
                    w.update(last=ts(now), n=w["n"] + 1, src=c.name, chain=s.get("chain"),
                             name=s.get("name") or w.get("name", ""), liq=s.get("liq"), vol24=s.get("vol24"))
                    self.dex_watch[coin] = w
                continue
            if c.kind == "reddit":
                hour = str(now // HOUR)
                m = self.state["mentions"].setdefault(coin, {})
                m[hour] = m.get(hour, 0) + s["mentions"]
            else:
                self.state["sightings"].setdefault(coin, {})[c.name] = {"rank": s.get("rank"), "t": now}
            rows.append({"time": ts(now), "coin": coin, "source": c.name,
                         "rank": s.get("rank", ""), "mentions": s.get("mentions", "")})
        if rows:
            self._csv(rows, now)

    def _prune(self, now):
        st = self.state
        st["seen_posts"] = {k: t for k, t in st["seen_posts"].items() if now - t <= 2 * DAY}
        h0 = now // HOUR - 25
        st["mentions"] = {c: {h: n for h, n in m.items() if int(h) >= h0} for c, m in st["mentions"].items()}
        st["mentions"] = {c: m for c, m in st["mentions"].items() if m}
        st["sightings"] = {c: {k: v for k, v in d.items() if now - v["t"] <= DAY}
                           for c, d in st["sightings"].items()}
        st["sightings"] = {c: d for c, d in st["sightings"].items() if d}
        if len(self.dex_watch) > 2000:                 # keep the watchlist bounded
            keep = sorted(self.dex_watch, key=lambda k: self.dex_watch[k]["last"])[-1500:]
            self.dex_watch = {k: self.dex_watch[k] for k in keep}

    def _mark_hot(self, now):
        for h in self.heat(now):
            if h["score"] >= self.p["floor"]:
                self.state["last_hot"][h["coin"]] = now

    # ---- scoring ----
    def components(self, coin, now=None):
        now = now or self.now
        p, st = self.p, self.state
        ttl_t, ttl_d = p["ttl_min"]["trend"] * MIN, p["ttl_min"]["dex"] * MIN
        trend = dex = 0.0
        srcs = []
        for src, v in st["sightings"].get(coin, {}).items():
            r = v.get("rank") or 15
            if src in ("coingecko", "cmc") and now - v["t"] <= ttl_t:
                trend = max(trend, 40 * max(0.0, 1 - (r - 1) / 15))
                srcs.append(f"{src}#{r}")
            elif src.startswith("geckoterminal") and now - v["t"] <= ttl_d:
                dex = max(dex, 15 * max(0.0, 1 - (r - 1) / 20))
                srcs.append(f"{src}#{r}")
            elif src == "dexscreener" and now - v["t"] <= ttl_d:
                dex = min(20.0, dex + 5)
                srcs.append("boosted")
        m = st["mentions"].get(coin, {})
        h = now // HOUR
        m1 = m.get(str(h), 0) + m.get(str(h - 1), 0) * ((HOUR - now % HOUR) / HOUR)   # rolling ~1h
        m24 = sum(n for k, n in m.items() if h - 24 <= int(k) <= h)
        base = max(1.0, (m24 - m1) / 23)
        reddit = 40 * min(1.0, (m1 / base) / p["reddit_full"]) if m1 >= p["reddit_min_mentions"] else 0.0
        if reddit:
            srcs.append(f"reddit {m1:.0f}/{m24}")
        return {"coin": coin, "score": round(trend + reddit + dex, 1), "trend": round(trend, 1),
                "reddit": round(reddit, 1), "dex": round(min(dex, 20), 1), "m1": round(m1, 1), "m24": m24,
                "srcs": srcs}

    def score(self, coin, now=None):
        return self.components(coin, now)["score"]

    def heat(self, now=None):
        """Ranked heat list (only coins with any signal), hottest first."""
        now = now or self.now
        coins = set(self.state["sightings"]) | set(self.state["mentions"])
        out = [self.components(c, now) for c in coins if c in self.universe and not excluded(c)]
        return sorted((h for h in out if h["score"] > 0), key=lambda h: -h["score"])

    def cold_hours(self, coin, now=None):
        """Hours since the coin last scored >= floor (0 if never seen hot)."""
        now = now or self.now
        t = self.state["last_hot"].get(coin)
        return 0.0 if t is None else (now - t) / HOUR

    def top_line(self, n=5, now=None):
        hs = self.heat(now)[:n]
        if not hs:
            return "social heat: nothing trending on Crypto.com coins"
        return "social heat top: " + ", ".join(
            f"{h['coin']} {h['score']:.0f} ({h['trend']:.0f}/{h['reddit']:.0f}/{h['dex']:.0f})" for h in hs)

    def self_check(self, now=None):
        """Once per run: poll every source now and log each HTTP status (for data/run.log)."""
        now = now or int(time.time() * 1000)
        for c in self.collectors:
            c.next_at = 0
        self.poll(now, all_due=True)
        parts = [f"{c.name} {c.status if c.status is not None else '-'}" for c in self.collectors]
        line = "social self-check: " + " | ".join(parts) if parts else "social self-check: all sources disabled"
        print(f"   {line}")
        return line


_TRACKER = None


def tracker(**kw):
    """Process-wide tracker (the strategy and the runner share one)."""
    global _TRACKER
    if _TRACKER is None:
        _TRACKER = HeatTracker(**kw)
    return _TRACKER


# ---- strategy ---------------------------------------------------------------------------
class Tagged(list):
    """Candle list that knows its coin: engine.step calls analyze(candles) without the coin
    name, and heat is looked up by coin. run_live wraps the candle dict with tag()."""

    def __init__(self, candles, coin):
        super().__init__(candles)
        self.coin = coin


def tag(candles_by_coin):
    return {c: Tagged(cs, c) for c, cs in candles_by_coin.items()}


class SocialHeat:
    """Test account: buy Crypto.com coins whose heat score crosses `enter` while the price is
    not in a spike-and-fade (24h change >= -10%; no upper cap on purpose: ride the runners).
    Exits: trailing stop 25% below the peak (also enforced by run_live.fast_check every second),
    10-day time limit, or the heat staying below `floor` for 12 hours."""
    name = "social_heat"
    weekly = False
    dynamic_universe = True       # candles for every USD coin are already loaded for early_mover
    needs_coin = True             # runner passes tag(data) so analyze() knows the coin
    min_candles = 3

    def __init__(self, name="social_heat", tracker_=None, **overrides):
        self.name, self.universe = name, []
        self.P = dict(SOCIAL, **overrides)
        self.max_positions = self.P["slots"]
        self.position_pct = self.max_position_pct = (1 - config.MIN_CASH_RESERVE_PCT) / self.P["slots"]
        self.trail = self.P["trail"]
        self.window = 26
        self._tracker, self.clock = tracker_, None    # clock: fixed ms for tests

    @property
    def tracker(self):
        return self._tracker or tracker()

    def _now(self):
        return self.clock or int(time.time() * 1000)

    def _sig(self, coin, price, change_24h, now_ms):
        h = self.tracker.components(coin, now_ms)
        ok_px = change_24h is not None and change_24h >= self.P["min_24h_change"]
        return {"heat": h["score"], "rank": h["score"], "change_24h": change_24h,
                "buy": bool(coin) and h["score"] >= self.P["enter"] and ok_px and not excluded(coin),
                "stop": price * (1 - self.trail),
                "cold": self.tracker.cold_hours(coin, now_ms) >= self.P["floor_hours"]}

    def analyze(self, candles, market_ok=True):
        if len(candles) < self.min_candles:
            return None
        c = candles[-1]
        sig = {"price": c["c"], "high": c["h"], "low": c["l"], "t": c["t"]}
        chg = c["c"] / candles[-25]["c"] - 1 if len(candles) >= 25 else None
        sig.update(self._sig(getattr(candles, "coin", ""), c["c"], chg, self._now()))
        return sig

    def entry(self, coin, ticker, now_ms=None):
        """Between hourly cycles: (price, reason) if `coin` should be bought now given its live
        Crypto.com ticker ('a' last price, 'c' 24h change), else None."""
        price, chg = _f(ticker.get("a")), _f(ticker.get("c"))
        if not price or price <= 0:
            return None
        now_ms = now_ms or self._now()
        s = self._sig(coin, price, chg, now_ms)
        if not s["buy"]:
            return None
        return price, f"heat {s['heat']:.0f}: " + " ".join(self.tracker.components(coin, now_ms)["srcs"])

    def manage(self, pos, s, now, rebalance=False):
        if s["low"] <= pos["stop"]:
            return 1.0, min(pos["stop"], s["price"]) if s["price"] < pos["stop"] else pos["stop"], "trailing stop"
        if now - pos["opened"] >= self.P["max_hold_days"] * DAY:
            return 1.0, s["price"], "time limit"
        if s.get("cold"):
            return 1.0, s["price"], f"heat collapsed (<{self.P['floor']} for {self.P['floor_hours']}h)"
        pos["peak"] = max(pos["peak"], s["high"])
        pos["stop"] = max(pos["stop"], pos["peak"] * (1 - self.trail))
        return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="self-check only (one call per source)")
    ap.add_argument("--dir", default=SOCIAL["dir"])
    a = ap.parse_args()
    try:
        from data_source import CryptoComClient
        uni = CryptoComClient().list_spot_symbols()
    except Exception as e:
        print(f"coin list failed ({e}); using config.BREAKOUT_UNIVERSE")
        uni = config.BREAKOUT_UNIVERSE
    tr = HeatTracker(params={"dir": a.dir}, universe=uni)
    tr.self_check()
    for h in tr.heat()[:20]:
        print(f"  {h['coin']:8} {h['score']:5.1f}  trend {h['trend']:4.1f} reddit {h['reddit']:4.1f} "
              f"dex {h['dex']:4.1f}  {' '.join(h['srcs'])}")
    if tr.dex_watch:
        print(f"  DEX-only watchlist: {len(tr.dex_watch)} tokens (data/social/dex_watch.json)")
