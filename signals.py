"""Early-detection signals for the early_mover account (paper trading only).

Built from research_notes/Early mover detection/early_detection.md (ranked top-5):

    ListingNoticeReactor   #1  poll exchange listing announcements (Crypto.com, Upbit, Coinbase,
                               Binance, Kraken), map to coins that already trade as <COIN>_USD on
                               Crypto.com, buy only if the coin has NOT already moved.
    PrePumpFootprint       #2  hourly: score coins on the pre-pump / pre-listing footprint
                               (48h drift on quiet volume + repeated volume hikes + rising lows
                               + optional open-interest creep) and rank buy candidates.
    PumpGuard              #4  veto before ANY early_mover entry: already up > 30% in 24h, or a
                               spike-and-fade in the last hour (we would be the exit liquidity).

Everything is stdlib only, offline-testable (fetch is injectable) and defensive: a failing
source, a malformed payload or a missing field never raises out of poll()/rank()/check().
Thresholds live in config.EARLY_SIGNALS (same keys as DEFAULTS below override them).

Wiring (run_live.py): reactor.poll() every ~10 s in the main loop -> reactor.candidates(events,
scanner) -> buy through the same helper as the minute scanner; footprint.rank(CRYPTO_CANDLES)
once an hour; PumpGuard.check() inside that shared buy helper and as EarlyMover's veto hook.
"""
import json
import os
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import deque
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from statistics import median

import config
from scanner import excluded

MIN = 60_000
HOUR = 3_600_000

DEFAULTS = {
    "listing": {
        "loop_s": 10,               # how often run_live asks the reactor to poll (any source)
        "timeout_s": 4,             # per-request timeout: never stall the 1-second stop checks
        "max_sources_per_poll": 2,  # sources fetched per poll() call (bounds worst-case latency)
        "backoff_s": (30, 600),     # after a failure: 30 s, doubling up to 10 min
        "max_age_min": 45,          # ignore notices older than this (the move is over by then)
        "max_move_since": 0.08,     # gate: price now vs price at the notice (or first detection)
        "max_move_by_source": {"upbit": 0.08, "cryptocom": 0.08, "binance": 0.04, "coinbase": 0.04,
                               "kraken": 0.04},   # notes: 8% Upbit/Bithumb, 4% others
        "max_24h_change": 0.30,     # gate: skip anything already up > 30% in 24h (notes' skip list)
        "min_daily_usd": 500_000,   # skip coins too thin on Crypto.com (notes suggest $2M; paper: $500k)
        "max_spread": 0.01,
        "seen_file": "data/seen_announcements.json",
        "seen_keep": 500,           # ids remembered per source
        "events_file": "data/listing_events.csv",   # latency / gate log (t0, t_detect, price, verdict)
        # Sources: url (from the notes; every one UNVERIFIED from this sandbox), poll interval.
        # An empty url disables the source. Fields parsed per source are in the parse_* functions.
        "sources": {
            "cryptocom": {"url": "https://api.crypto.com/exchange/v1/public/get-announcements", "every_s": 10},
            "upbit": {"url": "https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=trade",
                      "every_s": 5},
            "binance": {"url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
                               "?type=1&catalogId=48&pageNo=1&pageSize=20", "every_s": 15},
            "coinbase": {"url": "https://status.exchange.coinbase.com/history.atom", "every_s": 15},
            "coinbase_blog": {"url": "", "every_s": 60},     # blog RSS url unknown: set it when verified
            "kraken": {"url": "https://blog.kraken.com/feed", "every_s": 30},
        },
    },
    "footprint": {
        "drift": (0.05, 0.25),      # 48h return band: drifting, not exploded
        "max_1h_move": 0.06,        # any single hourly move above this = a spike, not accumulation
        "quiet_frac": 0.60,         # >= 60% of the last 48 candles below the baseline median volume
        "hike_mult": 3.0,           # a "hike" = hourly USD volume >= 3x baseline median
        "hikes": (2, 6),            # required number of hikes in the last 48h
        "spike_vol_mult": 20.0,     # one candle >= 20x median = the pump already happened
        "oi_creep": 0.20,           # optional term: perp open interest up >= 20% in 24h
        "min_history_h": 96,        # baseline needs >= 4 days of candles before the 48h window
        "baseline_h": 720,          # baseline window (30 days) when that much history exists
        "daily_usd": (300_000, 30_000_000),   # universe: small enough to be listable elsewhere
        "max_24h_change": 0.30,
        "min_score": 3, "top_n": 3,
        "oi_file": "data/oi_history.json",
    },
    "guard": {
        "max_24h_change": 0.30,     # never buy anything already up > 30% in 24h
        "spike": 0.15,              # last 60 min: a +15% spike...
        "fade": 0.40,               # ...that gave back >= 40% of the move = spike-and-fade
        "block_min": 30,            # coins flagged stay blocked this long
    },
}


def _cfg(section):
    user = getattr(config, "EARLY_SIGNALS", {}) or {}
    out = dict(DEFAULTS[section])
    out.update(user.get(section, {}))
    if section == "listing":      # nested dicts: merge per source so users can override one url
        src = {k: dict(v) for k, v in DEFAULTS["listing"]["sources"].items()}
        for k, v in (user.get("listing", {}).get("sources") or {}).items():
            src[k] = dict(src.get(k, {}), **v)
        out["sources"] = src
    return out


def _f(x):
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Title parsing
# ---------------------------------------------------------------------------
# Quote / base currencies that appear in titles but are never the listed coin.
_QUOTES = {"USD", "USDT", "USDC", "USDE", "KRW", "BTC", "ETH", "BNB", "EUR", "GBP", "JPY", "TRY", "BRL",
           "FDUSD", "TUSD", "DAI", "SOL", "XRP", "BUSD", "AUD", "SGD", "USDS", "PYUSD", "RLUSD"}
# Words that look like tickers when shouted in titles.
_NOISE = {"NEW", "API", "APP", "USA", "UTC", "KST", "AM", "PM", "IOC", "FAQ", "NFT", "ETF", "DEX", "CEX",
          "SPOT", "PERP", "USDM", "ALPHA", "LAUNCHPOOL", "LAUNCHPAD", "HODLER", "P2P", "OTC", "VIP", "Q1",
          "Q2", "Q3", "Q4", "TGE", "RSS", "AND", "OR", "THE", "FOR", "OF", "TO", "ON", "IN", "IS", "ARE",
          "NOW", "LIVE", "ADDS", "LIST", "LISTS", "LISTING", "TRADE", "TRADING", "PAIR", "PAIRS", "MARKET",
          "MARKETS", "MARGIN", "FUTURES", "EARN", "WEB3", "US", "EU", "UK", "KR", "JP", "ID", "PRE"}

# A notice is a listing when its title says so...
_LISTING_RE = re.compile(
    r"will list|will add|lists?\b|listing|now available|available for trading|is launching|launches|"
    r"adds? support|added to|to list|now live|trading (for|of|pair|is|enabled|will (begin|start|open))|"
    r"new (spot )?(trading )?pairs?|"
    r"신규 거래지원|거래지원 안내|상장|market support|new asset|asset listing|"
    r"(coinbase|kraken|binance|crypto\.com|upbit).*(list|support)", re.I)
# ...and it is NOT one of these (delisting, halt, maintenance, warnings, deposits, incidents).
_NEGATIVE_RE = re.compile(
    r"delist|de-list|remov|suspend|halt|maintenance|terminat|discontinu|wind.?down|cease|"
    r"degraded|incident|outage|resolved|investigat|delay|unavailable|"
    r"airdrop|staking|reward|promotion|contest|campaign|referral|survey|"
    r"거래지원 종료|유의|입출금|투자유의|점검|폐지", re.I)

_PAREN_RE = re.compile(r"\(([A-Z0-9]{2,10})\)")
_PAIR_RE = re.compile(r"\b([A-Z0-9]{2,10})[/_\-](USD|USDT|USDC|USDE|EUR|GBP|KRW|BTC|ETH)\b")
_WILL_LIST_RE = re.compile(r"\b(?:will list|lists?|listing|adds? support for|available for trading:?)\s+"
                           r"([A-Z0-9]{2,10})\b", re.I)


def is_listing(title):
    """True for 'new spot listing' notices; delistings, halts, maintenance, warnings -> False."""
    t = title or ""
    return bool(_LISTING_RE.search(t)) and not _NEGATIVE_RE.search(t)


def extract_tickers(title, content=""):
    """Ticker symbols named in a notice title: "(XYZ)" groups (also in Korean titles), "XYZ/USD" or
    "XYZ-USD" pairs and "Will List XYZ". Quote currencies and shouted words are dropped.
    Returns [] for non-listing notices. `content` is only searched for pair names."""
    if not is_listing(title):
        return []
    found = []
    for m in _PAREN_RE.finditer(title):
        found.append(m.group(1))
    for m in _PAIR_RE.finditer(title + " " + (content or "")[:2000]):
        found.append(m.group(1))
    for m in _WILL_LIST_RE.finditer(title):
        w = m.group(1)
        if w.isupper() and any(ch.isalpha() for ch in w):
            found.append(w)
    out = []
    for sym in found:
        sym = sym.upper()
        if sym in _QUOTES or sym in _NOISE or sym.isdigit() or sym in out:
            continue
        out.append(sym)
    return out


# ---------------------------------------------------------------------------
# Source parsers: bytes -> [{id, title, t0 (ms or None), content, extra}]
# ---------------------------------------------------------------------------
def _iso_ms(s):
    """ISO-8601 ('2025-09-25T10:00:00+09:00', '...Z') or epoch seconds/ms -> ms or None."""
    if s in (None, ""):
        return None
    if isinstance(s, (int, float)):
        return int(s if s > 1e11 else s * 1000)
    try:
        s = str(s).strip()
        if s.isdigit():
            return _iso_ms(int(s))
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return int(d.timestamp() * 1000)
    except ValueError:
        try:
            return int(parsedate_to_datetime(s).timestamp() * 1000)
        except Exception:
            return None


def _json(body):
    return json.loads(body if isinstance(body, str) else body.decode("utf-8", "replace"))


def parse_cryptocom(body):
    """v1 public/get-announcements: result.data[] with id, category, product_type, announced_at,
    title, content, instrument_name, ... (field names from the docs, unverified live)."""
    res = _json(body)
    rows = res.get("result", res)
    rows = rows.get("data", rows) if isinstance(rows, dict) else rows
    out = []
    for a in rows or []:
        if not isinstance(a, dict):
            continue
        ptype = str(a.get("product_type") or "Spot")
        if ptype.lower() not in ("spot", ""):
            continue
        title = a.get("title") or ""
        inst = a.get("instrument_name") or ""
        if inst and "_" in inst and not _PAIR_RE.search(title):
            title = f"{title} {inst}"              # "Crypto.com Exchange lists NEWT" + NEWT_USD
        out.append({"id": str(a.get("id") or title), "title": title,
                    "t0": _iso_ms(a.get("announced_at")), "content": a.get("content") or "",
                    "category": a.get("category")})
    return out


def parse_upbit(body):
    """api-manager.upbit.com/api/v1/announcements: data.notices[] (or data.list[]) with id, title,
    category, listed_at / first_listed_at / created_at."""
    res = _json(body)
    data = res.get("data", res) if isinstance(res, dict) else res
    rows = data
    if isinstance(data, dict):
        rows = data.get("notices") or data.get("list") or data.get("items") or []
    out = []
    for a in rows or []:
        if not isinstance(a, dict):
            continue
        t0 = a.get("first_listed_at") or a.get("listed_at") or a.get("created_at")
        out.append({"id": str(a.get("id") or a.get("title")), "title": a.get("title") or "",
                    "t0": _iso_ms(t0), "content": "", "category": a.get("category")})
    return out


def parse_binance(body):
    """bapi cms article list (catalog 48 = new listings): data.catalogs[].articles[] or
    data.articles[] with id/code, title, releaseDate (ms). 403-prone; not an official API."""
    res = _json(body)
    data = res.get("data") or {}
    rows = list(data.get("articles") or [])
    for cat in data.get("catalogs") or []:
        rows += cat.get("articles") or []
    out = []
    for a in rows:
        if not isinstance(a, dict):
            continue
        out.append({"id": str(a.get("code") or a.get("id") or a.get("title")), "title": a.get("title") or "",
                    "t0": _iso_ms(a.get("releaseDate")), "content": "", "category": None})
    return out


def parse_feed(body):
    """Atom (<feed><entry>) or RSS 2.0 (<rss><channel><item>) -> notices. Used for the Coinbase
    status feed, Coinbase blog and Kraken blog."""
    root = ET.fromstring(body)
    if root.tag.split("}")[-1].lower() not in ("feed", "rss", "rdf"):
        raise ValueError(f"not a feed: <{root.tag[:40]}>")     # e.g. an HTML error page
    out = []
    for e in list(root.iterfind(".//{*}entry")) + list(root.iterfind(".//{*}item")):
        def txt(*names):
            for n in names:
                el = e.find("{*}" + n)
                if el is not None and (el.text or "").strip():
                    return el.text.strip()
            return ""
        title = txt("title")
        ident = txt("id", "guid", "link") or title
        t0 = _iso_ms(txt("published", "updated", "pubDate"))
        out.append({"id": ident, "title": title, "t0": t0, "content": txt("content", "summary", "description"),
                    "category": txt("category") or None})
    return out


PARSERS = {"cryptocom": parse_cryptocom, "upbit": parse_upbit, "binance": parse_binance,
           "coinbase": parse_feed, "coinbase_blog": parse_feed, "kraken": parse_feed}

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")   # Binance/Upbit reject python's default agent


def http_get(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, application/xml, "
                                                                            "application/rss+xml, */*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------------------------------------------------------------------------
# 1. Listing notice reactor
# ---------------------------------------------------------------------------
class ListingNoticeReactor:
    """poll() the announcement sources (each on its own interval, with backoff) and return NEW
    listing notices; candidates(events, scanner) applies the not-yet-moved gate against the
    minute scanner's latest tickers and ring buffer.

        reactor = ListingNoticeReactor()            # thresholds/urls: DEFAULTS / config.EARLY_SIGNALS
        events = reactor.poll()                     # every ~10 s; [] almost always
        cands = reactor.candidates(events, scanner) # [{coin, price, reason, text, ...}] to buy

    Dedupe: (source, id) pairs are persisted to data/seen_announcements.json. The first poll of a
    source that has no persisted ids only primes the file (nothing is traded from a backlog),
    except notices whose own timestamp is within max_age_min."""

    def __init__(self, params=None, fetch=None, now_ms=None):
        self.p = _cfg("listing")
        if params:
            self.p.update(params)
        self.fetch = fetch or (lambda url: http_get(url, self.p["timeout_s"]))
        self.seen = {}          # source -> deque of ids (oldest first)
        self.state = {}         # source -> {next, fails, backoff}
        self.first_price = {}   # (source, id, coin) -> price at first detection
        self.now = now_ms or int(time.time() * 1000)
        self._load_seen()

    # ---- persistence ----
    def _load_seen(self):
        f = self.p.get("seen_file")
        if f and os.path.exists(f):
            try:
                with open(f) as fh:
                    for src, ids in json.load(fh).items():
                        self.seen[src] = deque(ids, maxlen=self.p["seen_keep"])
            except Exception:
                pass

    def _save_seen(self):
        f = self.p.get("seen_file")
        if not f:
            return
        try:
            os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
            with open(f, "w") as fh:
                json.dump({k: list(v) for k, v in self.seen.items()}, fh)
        except Exception as e:
            print(f"   listings: could not save seen ids: {e}")

    # ---- polling ----
    def due(self, now_ms=None):
        """Sources whose interval (or backoff) has elapsed, most overdue first."""
        now = now_ms or int(time.time() * 1000)
        out = []
        for name, src in self.p["sources"].items():
            if not src.get("url") or name not in PARSERS:
                continue
            st = self.state.setdefault(name, {"next": 0, "fails": 0, "backoff": 0})
            if now >= st["next"]:
                out.append((st["next"], name))
        return [n for _, n in sorted(out)]

    def poll(self, now_ms=None):
        """Fetch the due sources (at most max_sources_per_poll) and return the NEW listing notices:
        [{source, id, title, coins, t0, t_detect}]. Never raises."""
        now = now_ms or int(time.time() * 1000)
        self.now = now
        events = []
        for name in self.due(now)[:self.p["max_sources_per_poll"]]:
            src, st = self.p["sources"][name], self.state[name]
            try:
                notices = PARSERS[name](self.fetch(src["url"]))
                st["fails"], st["backoff"] = 0, 0
                st["next"] = now + src["every_s"] * 1000
            except Exception as e:
                lo, hi = self.p["backoff_s"]
                st["fails"] += 1
                st["backoff"] = min(hi, max(lo, st["backoff"] * 2))
                st["next"] = now + st["backoff"] * 1000
                if st["fails"] == 1 or st["fails"] % 10 == 0:
                    print(f"   listings: {name} failed ({st['fails']}x, retry in {st['backoff']}s): "
                          f"{type(e).__name__}: {str(e)[:120]}")
                continue
            events += self._new_events(name, notices, now)
        return events

    def _new_events(self, name, notices, now):
        priming = name not in self.seen        # never seen this source: swallow the backlog
        seen = self.seen.setdefault(name, deque(maxlen=self.p["seen_keep"]))
        known = set(seen)
        out, added = [], False
        for n in notices:
            nid = str(n.get("id") or "")
            if not nid or nid in known:
                continue
            seen.append(nid)
            known.add(nid)
            added = True
            t0 = n.get("t0")
            if t0 and now - t0 > self.p["max_age_min"] * MIN:
                continue                         # old news (also skips the backlog when priming)
            if priming and not t0:
                continue
            coins = extract_tickers(n.get("title", ""), n.get("content", ""))
            if coins:
                out.append({"source": name, "id": nid, "title": n.get("title", ""), "coins": coins,
                            "t0": t0, "t_detect": now})
        if priming or added:
            self._save_seen()
        return out

    # ---- gating ----
    @staticmethod
    def price_at(buf, t_ms, tol_ms=2 * HOUR):
        """Last ring-buffer snapshot at or before t_ms (None if the buffer does not reach back)."""
        best = None
        for s in buf or ():
            if s[0] <= t_ms:
                best = s
            else:
                break
        if best is None and buf and buf[0][0] - t_ms <= tol_ms:
            best = buf[0]                        # notice just before the buffer starts: close enough
        return best[1] if best else None

    def gate(self, ev, coin, cur, buf=None, now_ms=None):
        """Not-yet-moved gate for one coin of one event. cur = scanner.last[coin] ({price, vv,
        spread, c24?}); buf = scanner.hist[coin]. Returns (ok, reason, move_since, c24)."""
        p, now = self.p, now_ms or self.now
        if excluded(coin):
            return False, "stable/wrapped", None, None
        price = cur.get("price")
        if not price:
            return False, "no price", None, None
        if cur.get("spread") is not None and cur["spread"] > p["max_spread"]:
            return False, f"spread {cur['spread']:.2%}", None, None
        if cur.get("vv") is not None and cur["vv"] < p["min_daily_usd"]:
            return False, f"thin ${cur['vv']:,.0f}/24h", None, None
        if ev.get("t0") and now - ev["t0"] > p["max_age_min"] * MIN:
            return False, "notice too old", None, None
        key = (ev["source"], ev["id"], coin)
        p0 = self.price_at(buf, ev["t0"]) if ev.get("t0") else None
        if p0 is None:
            p0 = self.first_price.setdefault(key, price)   # fall back to price at first detection
        move = price / p0 - 1
        c24 = _f(cur.get("c24"))
        limit = p["max_move_by_source"].get(ev["source"], p["max_move_since"])
        if move > limit:
            return False, f"already +{move:.1%} since notice", move, c24
        if c24 is not None and c24 > p["max_24h_change"]:
            return False, f"already +{c24:.0%} in 24h", move, c24
        return True, "ok", move, c24

    def candidates(self, events, scanner, now_ms=None):
        """Apply the gate to every coin of every event using the minute scanner's latest tickers.
        Returns buy candidates [{coin, price, reason, text, source, move, c24, latency_s}] and
        logs every (event, coin) verdict to events_file."""
        now = now_ms or self.now
        out, rows = [], []
        for ev in events:
            for coin in ev["coins"]:
                cur = scanner.last.get(coin)
                if not cur:
                    verdict, move, c24 = "not on Crypto.com USD", None, None
                    ok = False
                else:
                    ok, verdict, move, c24 = self.gate(ev, coin, cur, scanner.hist.get(coin), now)
                lat = (now - ev["t0"]) / 1000 if ev.get("t0") else None
                rows.append({"t_detect": _ts(now), "t0": _ts(ev["t0"]) if ev.get("t0") else "",
                             "latency_s": "" if lat is None else round(lat), "source": ev["source"],
                             "coin": coin, "price": cur["price"] if cur else "",
                             "move_since": "" if move is None else round(move, 4),
                             "change_24h": "" if c24 is None else round(c24, 4),
                             "verdict": verdict, "title": ev["title"][:120]})
                text = (f"{coin}: {ev['source']} notice \"{ev['title'][:80]}\" "
                        f"{'' if lat is None else f'{lat:.0f}s ago '}-> {verdict}")
                print(f"   listing: {text}")
                if ok:
                    out.append({"coin": coin, "price": cur["price"], "source": ev["source"],
                                "reason": f"listing:{ev['source']} {ev['id'][:24]}", "text": text,
                                "move": move, "c24": c24, "latency_s": lat, "score": 1.0})
        if rows and self.p.get("events_file"):
            try:
                from engine import append_csv
                append_csv(self.p["events_file"], rows)
            except Exception as e:
                print(f"   listings: event log failed: {e}")
        return out


def _ts(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# 2. Pre-pump / pre-listing footprint scanner
# ---------------------------------------------------------------------------
def score_footprint(candles, params=None, oi_change=None):
    """Score one coin's hourly candles (oldest first, USD quote) on the accumulation footprint.
    Returns {score, max_score, terms, ret48, hikes, quiet, daily_usd, change_24h, price} or
    {"skip": reason} when the coin is out of universe / already spiked / too little history."""
    p = dict(DEFAULTS["footprint"], **(params or {}))
    if not candles or len(candles) < 48 + p["min_history_h"]:
        return {"skip": "history"}
    usd = [c["v"] * c["c"] for c in candles]
    closes = [c["c"] for c in candles]
    last48, base = candles[-48:], usd[-48 - p["baseline_h"]:-48]
    med = median(base) if base else 0.0
    if med <= 0 or closes[-49] <= 0:
        return {"skip": "no volume"}
    daily = med * 24
    lo, hi = p["daily_usd"]
    if not lo <= daily <= hi:
        return {"skip": f"daily ${daily:,.0f} out of range"}
    change_24h = closes[-1] / closes[-25] - 1
    if change_24h > p["max_24h_change"]:
        return {"skip": f"already +{change_24h:.0%} in 24h"}
    moves = [abs(last48[i]["c"] / last48[i - 1]["c"] - 1) for i in range(1, 48)] + \
            [abs(last48[0]["c"] / closes[-49] - 1)]
    if max(moves) > p["max_1h_move"]:
        return {"skip": f"1h spike {max(moves):+.1%}"}
    vols48 = usd[-48:]
    if max(vols48) >= p["spike_vol_mult"] * med:
        return {"skip": f"volume spike {max(vols48) / med:.0f}x"}
    ret48 = closes[-1] / closes[-49] - 1
    quiet = sum(1 for v in vols48 if v < med) / 48
    hikes = sum(1 for v in vols48 if v >= p["hike_mult"] * med)
    blocks = [min(c["l"] for c in last48[i:i + 12]) for i in range(0, 48, 12)]
    rising = all(b > a for a, b in zip(blocks, blocks[1:]))
    terms = {"drift": p["drift"][0] <= ret48 <= p["drift"][1],
             "quiet": quiet >= p["quiet_frac"],
             "hikes": p["hikes"][0] <= hikes <= p["hikes"][1],
             "rising_lows": rising}
    if oi_change is not None:
        terms["oi_creep"] = oi_change >= p["oi_creep"]
    return {"score": sum(terms.values()), "max_score": len(terms), "terms": terms,
            "ret48": ret48, "hikes": hikes, "quiet": quiet, "daily_usd": daily,
            "change_24h": change_24h, "price": closes[-1], "oi_change": oi_change}


class PrePumpFootprint:
    """Hourly ranking of accumulation footprints across all coins the engine already has
    candles for. Optional open-interest term from Crypto.com perp tickers (note_oi)."""

    def __init__(self, params=None, now_ms=None):
        self.p = _cfg("footprint")
        if params:
            self.p.update(params)
        self.oi = {}      # coin -> [(t_ms, oi)] hourly snapshots, ~26h kept
        self._load_oi()

    # ---- optional open-interest creep from public/get-tickers (perp instruments carry `oi`) ----
    def _load_oi(self):
        f = self.p.get("oi_file")
        if f and os.path.exists(f):
            try:
                with open(f) as fh:
                    self.oi = {k: [tuple(x) for x in v] for k, v in json.load(fh).items()}
            except Exception:
                self.oi = {}

    def note_oi(self, tickers, now_ms=None):
        """Record perp open interest per coin (once an hour is enough). Instrument names like
        BTCUSD-PERP / BTC_USD-PERP / BTC-PERP are all mapped to BTC."""
        now = now_ms or int(time.time() * 1000)
        rows = tickers.get("data", tickers) if isinstance(tickers, dict) else tickers
        n = 0
        for t in rows or []:
            name, oi = str(t.get("i") or ""), _f(t.get("oi"))
            if oi is None or "PERP" not in name.upper():
                continue
            coin = re.sub(r"[-_]?PERP$", "", name.upper()).replace("_", "")
            coin = re.sub(r"(USDT|USDC|USD)$", "", coin)
            if not coin:
                continue
            hist = self.oi.setdefault(coin, [])
            if hist and now - hist[-1][0] < 30 * MIN:
                continue
            hist.append((now, oi))
            del hist[:-30]
            n += 1
        f = self.p.get("oi_file")
        if n and f:
            try:
                os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
                with open(f, "w") as fh:
                    json.dump(self.oi, fh)
            except Exception:
                pass
        return n

    def oi_change(self, coin, now_ms=None):
        """24h open-interest change for coin, or None without ~24h of snapshots."""
        now = now_ms or int(time.time() * 1000)
        hist = self.oi.get(coin) or []
        then = [x for x in hist if x[0] <= now - 22 * HOUR]
        if not hist or not then or then[-1][1] <= 0:
            return None
        return hist[-1][1] / then[-1][1] - 1

    # ---- ranking ----
    def rank(self, candles_by_coin, now_ms=None):
        """Ranked buy candidates [{coin, price, score, reason, text, ...}] with score >= min_score,
        best first, at most top_n. Never raises on a bad coin."""
        now = now_ms or int(time.time() * 1000)
        out = []
        for coin, cs in candles_by_coin.items():
            if excluded(coin):
                continue
            try:
                r = score_footprint(cs, self.p, self.oi_change(coin, now))
            except Exception as e:
                print(f"   footprint: {coin} failed: {e}")
                continue
            if "skip" in r or r["score"] < self.p["min_score"]:
                continue
            on = "+".join(k for k, v in r["terms"].items() if v)
            r.update(coin=coin, reason=f"footprint {r['score']}/{r['max_score']} {on}",
                     text=(f"{coin}: footprint {r['score']}/{r['max_score']} ({on}) 48h {r['ret48']:+.1%}, "
                           f"{r['hikes']} volume hikes, {r['quiet']:.0%} quiet hours @ {r['price']:g}"))
            out.append(r)
        out.sort(key=lambda r: (r["score"], r["hikes"], r["ret48"]), reverse=True)
        return out[:self.p["top_n"]]


# ---------------------------------------------------------------------------
# 4. Pump guard
# ---------------------------------------------------------------------------
class PumpGuard:
    """Veto for every early_mover entry: (a) already up > max_24h_change in 24h (ticker `c`, or
    hourly candles), (b) spike-and-fade in the last 60 minutes of the minute scanner's ring buffer
    (price rose >= spike, then gave back >= fade of that move). A vetoed coin stays blocked for
    block_min minutes so the three signals do not keep re-trying it."""

    def __init__(self, params=None):
        self.p = _cfg("guard")
        if params:
            self.p.update(params)
        self.blocked = {}   # coin -> ms until

    @staticmethod
    def change_24h(cur=None, candles=None):
        c = _f((cur or {}).get("c24"))
        if c is None and candles and len(candles) >= 25 and candles[-25]["c"] > 0:
            c = candles[-1]["c"] / candles[-25]["c"] - 1
        return c

    @staticmethod
    def spike_and_fade(buf, now_ms, spike, fade, window_ms=60 * MIN):
        """(True, detail) when the last window shows a +spike rise that retraced >= fade of it."""
        pts = [s for s in (buf or ()) if s[0] >= now_ms - window_ms and s[1]]
        if len(pts) < 3:
            return False, None
        p_start, p_now = pts[0][1], pts[-1][1]
        peak = max(s[1] for s in pts)
        rise = peak / p_start - 1
        if rise < spike or peak <= p_start:
            return False, None
        retrace = (peak - p_now) / (peak - p_start)
        return retrace >= fade, f"+{rise:.0%} then gave back {retrace:.0%}"

    def check(self, coin, now_ms=None, cur=None, buf=None, candles=None):
        """(ok, reason). cur = scanner.last[coin] (uses price, c24), buf = scanner.hist[coin],
        candles = hourly candles (24h fallback). Missing inputs just skip that check."""
        now = now_ms or int(time.time() * 1000)
        p = self.p
        if self.blocked.get(coin, 0) > now:
            return False, f"blocked {int((self.blocked[coin] - now) / MIN)} more min"
        c24 = self.change_24h(cur, candles)
        if c24 is not None and c24 > p["max_24h_change"]:
            self.blocked[coin] = now + p["block_min"] * MIN
            return False, f"already +{c24:.0%} in 24h"
        hit, detail = self.spike_and_fade(buf, now, p["spike"], p["fade"])
        if hit:
            self.blocked[coin] = now + p["block_min"] * MIN
            return False, f"spike-and-fade in the last hour ({detail})"
        return True, "ok"
