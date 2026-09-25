"""Minute-level "early mover" scanner across EVERY USD coin on Crypto.com.

The hourly EarlyMover strategy only sees a take-off after the candle closes. This
module watches the whole exchange with ONE public call per minute (public/get-tickers)
and flags coins whose price jumped X% over the last M minutes on unusually heavy volume,
plus brand-new listings the moment they show up in the ticker list.

    scanner = MinuteScanner()                       # thresholds: SCANNER defaults / config
    scanner.warm_start({coin: hourly_candles})      # optional: usable right after a restart
    scanner.update(client.tickers())                # once a minute
    for sig in scanner.signals(): ...               # strongest first

Ticker fields (Crypto.com Exchange v1 public/get-tickers, all strings):
    i instrument ("PEPE_USD")   a last price   b best bid   k best ask
    v 24h base volume           vv 24h USD volume           c 24h change   h/l 24h high/low   t ms
Everything is parsed defensively: a missing field just disables the check that needs it.

Volume note: "vv" is a rolling 24h total, so vv(now) - vv(then) = volume traded since `then`
minus the volume that fell out of the 24h window. In a quiet market that difference is ~0,
so the window's traded volume is estimated as  max(diff, 0) + normal_rate * M  and compared
with normal_rate * M (normal = vv / 1440 at the window start, or the 7-day hourly average
from warm_start). Exact enough to separate a 3-5x surge from noise; not exact accounting.
"""
import json
import os
import re
import time
from collections import deque

import config

MIN = 60_000
HOUR = 3_600_000

# All thresholds in one place so backtests can tune them. config.EARLY_MOVER_SCANNER (same keys)
# overrides these defaults when present.
DEFAULTS = {
    "tiers": [(15, 0.05), (30, 0.08), (60, 0.12)],   # (window minutes, min rise) - any tier fires
    "vol_ratio": 3.0,           # window volume must be >= 3x the normal rate for that window
    "min_daily_usd": 100_000,   # skip coins with < $100k traded in 24h (unless brand-new)
    "max_spread": 0.015,        # skip coins whose bid/ask spread is > 1.5%
    "spread_required": True,    # no bid/ask in the ticker -> treat as untradable
    "history_min": 6 * 60,      # ring buffer length in minutes (process restarts every ~6h)
    "listing_min": 180,         # keep reporting a new listing for its first 3h
    "known_file": config.LISTINGS_FILE,
}
SCANNER = dict(DEFAULTS, **getattr(config, "EARLY_MOVER_SCANNER", {}))

# Stablecoins / pegged tokens: they never "take off".
STABLES = {"USDT", "USDC", "DAI", "FDUSD", "TUSD", "PYUSD", "USDS", "USDE", "USDD", "USDP",
           "USD1", "USDG", "USDB", "USDY", "USDX", "GUSD", "BUSD", "LUSD", "CUSD", "SUSD",
           "FRAX", "CRVUSD", "GHO", "RLUSD", "DOLA", "MIM", "EURC", "EURT", "EURS", "AEUR",
           "XSGD", "GYEN", "ZUSD", "USTC", "UST"}
_STABLE_RE = re.compile(r"^(USD|EUR|GBP)[A-Z0-9]{0,3}$|^[A-Z]{1,4}(USD|EUR)$")
# Wrapped / staked / leveraged tokens: not the kind of "early move" we want.
WRAPPED = {"WBTC", "WETH", "WSOL", "WBNB", "WAVAX", "WMATIC", "WPOL", "WTRX",
           "STETH", "WSTETH", "RETH", "CBETH", "CBBTC", "TBTC", "SBTC", "BTCB", "SETH", "MSOL",
           "JITOSOL", "BSOL", "STSOL", "SFRXETH", "FRXETH", "WEETH", "EZETH", "RSETH"}
# leveraged tokens: BTC3L/ETH3S, or a major coin + UP/DOWN/BULL/BEAR (BTCUP). Plain names
# that merely end in "UP" (JUP, SYRUP) are real coins and must not match.
_LEVERAGED_RE = re.compile(r"^[A-Z0-9]+\d+[LS]$|^(BTC|ETH|BNB|XRP|ADA|DOT|LINK|LTC|EOS|TRX|XTZ|SOL|DOGE)"
                           r"(UP|DOWN|BULL|BEAR)$")


def excluded(coin):
    """True for stable, pegged, wrapped or leveraged tokens."""
    c = coin.upper()
    return c in STABLES or c in WRAPPED or bool(_STABLE_RE.match(c)) or bool(_LEVERAGED_RE.match(c))


def _f(x):
    """Float or None (ticker fields are strings; missing ones arrive as None or "")."""
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def parse_tickers(res, quote=config.QUOTE):
    """{coin: raw ticker dict} from the API result ({"data": [...]}), a list of tickers,
    or an already keyed {coin: ticker} dict. Only <COIN>_<quote> instruments are kept."""
    if isinstance(res, dict) and "data" in res:
        res = res["data"]
    if isinstance(res, dict):
        return {k.split("_")[0]: v for k, v in res.items()}
    out = {}
    for t in res or []:
        name = t.get("i") or ""
        if name.endswith("_" + quote):
            out[name[:-len(quote) - 1]] = t
    return out


class MinuteScanner:
    def __init__(self, params=None, known=None, now_ms=None):
        self.p = dict(SCANNER, **(params or {}))
        self.hist = {}       # coin -> deque of (t_ms, price, vv) once a minute, oldest first
        self.last = {}       # coin -> parsed latest ticker {price, vv, spread, t}
        self.warm = {}       # coin -> {rate: 7-day USD/min, recent: last-hour USD/min} from candles
        self.first_seen = {} # coin -> ms when it first appeared in tickers after start
        self.known = set(known or [])   # coins that are NOT new listings
        self.started = False
        kf = self.p.get("known_file")
        if kf and os.path.exists(kf):
            try:
                with open(kf) as f:
                    self.known |= set(json.load(f))
            except Exception:
                pass
        self.now = now_ms or int(time.time() * 1000)

    # ---- feeding ----
    def warm_start(self, candles_by_coin, now_ms=None):
        """Seed history from hourly candles so 60-min signals (and the volume baseline) work
        right after a restart. Warm entries carry vv=None (24h totals unknown)."""
        now = now_ms or self.now
        keep = self.p["history_min"] * MIN + HOUR
        for coin, cs in candles_by_coin.items():
            if not cs or excluded(coin):
                continue
            self.known.add(coin)
            usd = [c["v"] * c["c"] for c in cs]
            week = usd[-1 - 7 * 24:-1] if len(cs) > 7 * 24 else usd[:-1]
            rate = sum(week) / len(week) / 60 if week else 0.0
            lastc = cs[-1]
            elapsed = max(1.0, min(60.0, (now - lastc["t"]) / MIN))     # in-progress candle
            recent = max(usd[-1] / elapsed, usd[-2] / 60 if len(usd) > 1 else 0.0)
            self.warm[coin] = {"rate": rate, "recent": recent}
            buf = self._buf(coin)
            for c in cs:
                t = min(c["t"] + HOUR, now)   # candle close time
                if t >= now - keep and (not buf or t > buf[-1][0]):
                    buf.append((t, c["c"], None))

    def _buf(self, coin):
        if coin not in self.hist:
            self.hist[coin] = deque(maxlen=self.p["history_min"] + 5)
        return self.hist[coin]

    def update(self, tickers, now_ms=None):
        """One snapshot per coin from a public/get-tickers result. Call once a minute.
        Returns the coins that appeared for the first time since start (new listings)."""
        now = now_ms or int(time.time() * 1000)
        self.now = now
        tk = parse_tickers(tickers)
        new = []
        for coin, t in tk.items():
            price = _f(t.get("a"))
            if price is None or price <= 0:
                continue
            bid, ask = _f(t.get("b")), _f(t.get("k"))
            spread = (ask - bid) / ((ask + bid) / 2) if bid and ask and ask >= bid else None
            self.last[coin] = {"price": price, "vv": _f(t.get("vv")), "spread": spread,
                               "t": _f(t.get("t")) or now}
            buf = self._buf(coin)
            if buf and now - buf[-1][0] < 30_000 and buf[-1][2] is not None:
                buf.pop()                     # called twice within a minute: keep one snapshot
            buf.append((now, price, self.last[coin]["vv"]))
            if self.started and coin not in self.known and coin not in self.first_seen:
                self.first_seen[coin] = now
                new.append(coin)
        if not self.started:                  # everything present at start is "known"
            self.known |= set(tk)
            self.started = True
        for coin in list(self.last):          # delisted / missing this round: drop stale price
            if coin not in tk:
                del self.last[coin]
        return new

    # ---- reading ----
    def _at(self, buf, t_target, tol):
        """Snapshot closest to t_target if within tol ms, else None."""
        best = None
        for s in reversed(buf):
            if s[0] > t_target + tol:
                continue
            if s[0] < t_target - tol:
                break
            if best is None or abs(s[0] - t_target) < abs(best[0] - t_target):
                best = s
        return best

    def _mover(self, coin, now):
        """Best (highest score) tier signal for one coin, or None."""
        p, buf, cur = self.p, self.hist.get(coin), self.last.get(coin)
        if not buf or not cur or len(buf) < 2:
            return None
        warm = self.warm.get(coin, {})
        best = None
        for m, x in p["tiers"]:
            s0 = self._at(buf, now - m * MIN, max(2 * MIN, m * MIN // 2))
            if not s0 or s0[1] <= 0:
                continue
            mins = max(1.0, (now - s0[0]) / MIN)     # actual window length (warm entries are hourly)
            rise = cur["price"] / s0[1] - 1
            if rise < x:
                continue
            # normal per-minute USD rate at the window start
            rate = s0[2] / 1440 if s0[2] else warm.get("rate", 0.0)
            if rate <= 0:
                continue
            if s0[2] is not None and cur["vv"] is not None:
                traded = max(cur["vv"] - s0[2], 0.0) + rate * mins   # see module docstring
            else:                                    # no 24h totals yet: last hourly candle rate
                traded = warm.get("recent", 0.0) * mins
            ratio = traded / (rate * mins)
            if ratio < p["vol_ratio"]:
                continue
            sig = {"coin": coin, "kind": "mover", "rise": round(rise, 4), "window_min": int(round(mins)),
                   "vol_ratio": round(ratio, 2), "price": cur["price"], "spread": cur["spread"],
                   "score": rise * ratio}
            if best is None or sig["score"] > best["score"]:
                best = sig
        return best

    def _tradable(self, coin, cur, listing=False):
        p = self.p
        if excluded(coin):
            return False
        if cur["spread"] is None:
            if p["spread_required"]:
                return False
        elif cur["spread"] > p["max_spread"]:
            return False
        if listing:
            return True
        day = cur["vv"] if cur["vv"] is not None else self.warm.get(coin, {}).get("rate", 0.0) * 1440
        return day >= p["min_daily_usd"]

    def signals(self, now_ms=None):
        """Current take-offs, strongest first: [{coin, kind, rise, window_min, vol_ratio,
        price, spread, score}]. kind is "mover" or "new_listing"."""
        now = now_ms or self.now
        out = []
        for coin, cur in self.last.items():
            age = now - self.first_seen.get(coin, -1)
            if coin in self.first_seen and age <= self.p["listing_min"] * MIN:
                if self._tradable(coin, cur, listing=True):
                    out.append({"coin": coin, "kind": "new_listing", "rise": 0.0, "window_min": int(age // MIN),
                                "vol_ratio": 0.0, "price": cur["price"], "spread": cur["spread"], "score": 1e9})
                continue
            if not self._tradable(coin, cur):
                continue
            sig = self._mover(coin, now)
            if sig:
                out.append(sig)
        out.sort(key=lambda s: s["score"], reverse=True)
        return out


def describe(sig):
    """One-line log text for a signal."""
    sp = "?" if sig["spread"] is None else f"{sig['spread']:.2%}"
    if sig["kind"] == "new_listing":
        return f"{sig['coin']}: NEW LISTING ({sig['window_min']} min old) @ {sig['price']:g} spread {sp}"
    return (f"{sig['coin']}: +{sig['rise']:.1%} in {sig['window_min']} min on {sig['vol_ratio']:.1f}x volume "
            f"@ {sig['price']:g} spread {sp}")
