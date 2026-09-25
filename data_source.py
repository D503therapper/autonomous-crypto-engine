"""Market data: live Crypto.com public API, plus a synthetic feed for offline tests."""
import json
import math
import random
import time
import urllib.parse
import urllib.request

import config

TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
         "1h": 3_600_000, "4h": 14_400_000, "1D": 86_400_000}


class Candle(dict):
    """{'t': ms, 'o','h','l','c','v': float}"""


class CryptoComClient:
    def __init__(self, base=config.API_BASE, timeout=15):
        self.base = base
        self.timeout = timeout

    def _get(self, method, **params):
        url = f"{self.base}/{method}?{urllib.parse.urlencode(params)}"
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=self.timeout) as r:
                    body = json.loads(r.read())
                if body.get("code") != 0:
                    raise RuntimeError(f"{method}: {body}")
                return body["result"]
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)

    def list_spot_symbols(self, quote=config.QUOTE):
        """Base coins that have a tradable <COIN>_<quote> spot pair."""
        out = set()
        for inst in self._get("public/get-instruments").get("data", []):
            if inst.get("inst_type") == "CCY_PAIR" and inst.get("quote_ccy") == quote \
                    and inst.get("tradable", True):
                out.add(inst["base_ccy"])
        return sorted(out)

    def candles(self, coin, timeframe=config.TIMEFRAME, count=config.CANDLES_NEEDED,
                end_ms=None):
        """Oldest-first candles. Pages backwards because the API caps each call."""
        step = TF_MS[timeframe]
        end_ms = end_ms or int(time.time() * 1000)
        got = {}
        while len(got) < count:
            start = end_ms - min(300, count - len(got) + 1) * step
            res = self._get("public/get-candlestick",
                            instrument_name=f"{coin}_{config.QUOTE}",
                            timeframe=timeframe, count=300,
                            start_ts=start, end_ts=end_ms)
            rows = res.get("data", [])
            if not rows:
                break
            for r in rows:
                got[int(r["t"])] = Candle(t=int(r["t"]), o=float(r["o"]), h=float(r["h"]),
                                          l=float(r["l"]), c=float(r["c"]), v=float(r["v"]))
            oldest = min(int(r["t"]) for r in rows)
            if oldest >= end_ms:
                break
            end_ms = oldest - 1
        return [got[k] for k in sorted(got)][-count:]


    def last_prices(self, coins):
        """Latest trade price for many coins in one call (for the fast stop monitor)."""
        want = {f"{c}_{config.QUOTE}": c for c in coins}
        out = {}
        for t in self._get("public/get-tickers").get("data", []):
            if t.get("i") in want and t.get("a") not in (None, ""):
                out[want[t["i"]]] = float(t["a"])
        return out


class YahooClient:
    """US stock prices from Yahoo Finance (free, delayed a few seconds, no account needed)."""

    def __init__(self):
        import yfinance  # installed by the GitHub workflow (requirements.txt)
        self.yf = yfinance
        self._cache = {}

    def list_spot_symbols(self, quote=None):
        return list(config.STOCK_UNIVERSE)

    def _download(self, symbols, days):
        key = (tuple(sorted(symbols)), days)
        if key not in self._cache:
            period = f"{min(days, 729)}d"
            df = self.yf.download(sorted(symbols), period=period, interval="1h", group_by="ticker",
                                  auto_adjust=True, prepost=False, progress=False, threads=True)
            self._cache[key] = df
        return self._cache[key]

    def candles(self, sym, timeframe="1h", count=config.CANDLES_NEEDED, end_ms=None, universe=None):
        days = max(30, count // 7 + 10)
        df = self._download(universe or config.STOCK_UNIVERSE + ["SPY"], days)
        try:
            d = df[sym].dropna()
        except KeyError:
            return []
        rows = [Candle(t=int(ix.timestamp() * 1000), o=float(r["Open"]), h=float(r["High"]),
                       l=float(r["Low"]), c=float(r["Close"]), v=float(r["Volume"]))
                for ix, r in d.iterrows()]
        return rows[-count:]

    def last_prices(self, syms):
        out = {}
        for s in syms:
            try:
                out[s] = float(self.yf.Ticker(s).fast_info["last_price"])
            except Exception:
                pass
        return out

    def market_open(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("America/New_York"))
        mins = now.hour * 60 + now.minute
        return now.weekday() < 5 and 9 * 60 + 30 <= mins < 16 * 60  # (ignores holidays)


class SyntheticClient:
    """Random-walk prices with regime changes. ONLY for testing the plumbing —
    results on this data say nothing about real markets."""

    def __init__(self, seed=7, n=4000):
        self.rng = random.Random(seed)
        self.n = n
        self.cache = {}

    def list_spot_symbols(self, quote=config.QUOTE):
        return list(config.UNIVERSE)

    def _series(self, coin):
        if coin not in self.cache:
            rng = random.Random(hash((coin, self.rng.random())))
            price = rng.uniform(0.5, 500)
            vol = rng.uniform(0.006, 0.02)
            drift, rows, pump = 0.0, [], 0
            base_usd_vol = rng.uniform(2e5, 5e6)   # USD traded per hour
            t0 = int(time.time() * 1000) - self.n * TF_MS["1h"]
            for i in range(self.n):
                if i % 300 == 0:
                    drift = rng.gauss(0, 0.0012)
                if pump == 0 and rng.random() < 0.004:   # occasional pump/fake-out
                    pump = rng.randint(4, 12) * (1 if rng.random() < 0.5 else -1)
                r = drift + rng.gauss(0, vol)
                if pump:
                    r += 0.012 if pump > 0 else (0.012 if abs(pump) > 3 else -0.03)
                    pump += -1 if pump > 0 else 1
                o = price
                price = max(1e-6, price * math.exp(r))
                h = max(o, price) * (1 + abs(rng.gauss(0, vol / 2)))
                l = min(o, price) * (1 - abs(rng.gauss(0, vol / 2)))
                rows.append(Candle(t=t0 + i * TF_MS["1h"], o=o, h=h, l=l, c=price,
                                   v=base_usd_vol * rng.uniform(0.5, 1.5) * (5 if pump else 1) / price))
            self.cache[coin] = rows
        return self.cache[coin]

    def candles(self, coin, timeframe=config.TIMEFRAME, count=config.CANDLES_NEEDED,
                end_ms=None):
        s = self._series(coin)
        if end_ms is not None:
            s = [c for c in s if c["t"] <= end_ms]
        return s[-count:]
