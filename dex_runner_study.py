"""DEX runner study: which EARLY signs come before the meme coins that run 2x / 5x / 10x+ within 1-7 days?

Owner's #1 priority (results/research_log.md): find the Solana / Base / Ethereum DEX coins that run
100%-1000%+ every day, avoid the duds and the rugs, and wire the winning score into dex.py.

  1. pools     GeckoTerminal (free API; adaptive gap, 429 -> back off) for solana / base / eth:
               trending_pools (1h / 6h / 24h), new_pools, pools sorted by 24h volume and by 24h trades,
               paginated; DexScreener boosts / profiles (token -> pair via tokens/v1).  A registry
               (results/dex_runner_pools.json, seeded from results/dex_exit_pools.json) keeps every pool
               ever seen with its FIRST sighting, so later runs also study pools that rugged since.
  2. history   hourly OHLCV for the last --months (up to --hourly-pages x 1000 bars per pool), resampled
               to an hourly grid (hours without trades carry the last close, volume 0).
  3. points    many decision points per pool (every hour in the first day, then every 4h / 12h / 24h);
               at each one ONLY the past is used: pool age, pump.fun origin (token address ends in
               "pump"), network, estimated liquidity, market cap (today's FDV scaled by price), 1h / 6h /
               24h volume, volume vs its own recent average, day-over-day volume, volume / liquidity,
               price change 1h / 6h / 24h / since first bar, distance from the 7-day high, bounce from
               the 24h low, 24h volatility, share of green hours, share of active hours, hour of day,
               weekday.  Holder / buyer counts, LP burn and trending ranks are NOT available
               historically (see section 9 for what dex.py should start logging).
  4. labels    what happened next: max gain within 1d / 3d / 7d (>= 2x / 5x / 10x) and rug7 (a close
               <= 10% of the prior-24h high without recovering to 30% within a day, or the pool's
               trades stop for good, within 7 days).
  5. analysis  bucketed hit rates and lift tables per feature (older half vs newer half), runner-vs-dud
               medians, a points score built ONLY on the older half and tested on the newer half, a
               small L2 logistic regression (older -> newer), pool-clustered bootstrap intervals.
  6. trading   the scores as entry rules through the engine's live exit (config.DEX["exit"]: hold 14
               days with no stop, 60% trail once 3x, a runner still >= 2x at day 14 rides a 50% trail)
               with the engine's costs (0.3% fee + 1% slippage + price impact per side), one trade per
               pool at a time, in a 4-slot compounding account: trades/day, win rate, median / mean per
               trade, profit per month (older / newer half), max drawdown, rug rate.
  7. output    results/dex_runner_study.txt (this log; plain-English summary at the end),
               results/dex_runner_points.csv.gz (the labelled decision points, for offline re-analysis),
               results/dex_runner_pools.json (registry).

LIMITS: pools are selected TODAY (trending / top volume / registry), so pools that rugged before the
registry knew them are under-represented: absolute rug rates are too low and runner base rates too
high, especially in the newer half.  Relative comparisons (which buckets run more often) are what the
study is for; the registry makes every next run less biased.  GeckoTerminal has no liquidity history:
liquidity = the largest reserve ever seen x sqrt(price then / price at that sighting).  No buy / sell
counts in OHLCV.  Trades/day here are a FLOOR (a few thousand pools vs the whole market).

    python dex_runner_study.py                       # real run (GitHub Actions, ~5h)
    python dex_runner_study.py --synthetic           # offline plumbing test (fake prices!)
    python dex_runner_study.py --synthetic --chaos   # ... with 429s, empty / broken responses
"""
import argparse
import bisect
import collections
import csv
import gzip
import json
import math
import os
import random
import statistics
import sys
import time
import urllib.request
from array import array
from datetime import datetime, timezone

from dex_exit_study import (DAY, FEE, HOUR, MAJORS, NETS, SLIP, SIZE, GTClient, SyntheticGT, banner, boot_ci, clean,
                            fetch_series, fnum, iso_s, liq_at, load_registry, mean, ohlcv, parse_pools, pct, portfolio, ts)

try:
    import config
    DEXC = config.DEX
except Exception:                      # pragma: no cover
    DEXC = {}
try:
    from dex import norm_ds
    from social import parse_dex_list
except Exception:                      # pragma: no cover - standalone fallback
    norm_ds = parse_dex_list = None

EXIT = DEXC.get("exit") or {"trail": 0.95, "trail_steps": [(3.0, 0.60)], "max_hold_days": 14, "runner_at_limit": (1.0, 0.50)}
SCREEN = DEXC.get("screen") or {"min_liq": 100_000, "min_vol24": 100_000, "min_age_h": 6}
ENTRY = DEXC.get("entry") or {"h1": 0.10}
DS_CHAIN = {"solana": "solana", "base": "base", "ethereum": "eth"}          # DexScreener chainId -> GT network
RUG_KEEP, RUG_LOSS, DEAD_H, HORIZON_D = 0.10, -0.95, 72, 45
W1, W3, W7 = 24, 72, 168
FEATS = ["age_h", "pump", "sol", "base", "liq", "mcap", "vol1", "vol6", "vol24", "v1_rel", "v6_rel", "v24_rel", "vol24_liq",
         "ch1", "ch6", "ch24", "ch0", "dd7", "up24", "vola24", "green6", "act24", "hour", "wday"]
LABELS = ["m1", "m3", "m7", "low7", "rug7"]
LIVE = {  # feature -> how dex.py can compute it live (DexScreener pair fields) or None if it must be logged first
    "age_h": "pairCreatedAt", "pump": "token address ends with 'pump'", "sol": "chainId", "base": "chainId",
    "liq": "liquidity.usd", "mcap": "fdv", "vol1": "volume.h1", "vol6": "volume.h6", "vol24": "volume.h24",
    "v1_rel": "volume.h1 / (volume.h24 / 24)", "v6_rel": "volume.h6 / ((volume.h24 - volume.h6) / 18 * 6)",
    "v24_rel": None, "vol24_liq": "volume.h24 / liquidity.usd", "ch1": "priceChange.h1", "ch6": "priceChange.h6",
    "ch24": "priceChange.h24", "ch0": None, "dd7": None, "up24": None, "vola24": None, "green6": None,
    "act24": None, "hour": "clock (UTC)", "wday": "clock (UTC)"}
NAN = float("nan")


# ----------------------------------------------------------------------------- HTTP
class AdaptiveGT(GTClient):
    """GeckoTerminal client whose gap grows on 429s (GitHub runners share IPs) and shrinks back slowly."""

    def __init__(self, gap=2.2):
        super().__init__(gap)
        self.ok_run, self.max_gap = 0, 12.0

    def get(self, path, **q):
        import urllib.error
        import urllib.parse
        url = "https://api.geckoterminal.com/api/v2" + path + ("?" + urllib.parse.urlencode(q) if q else "")
        for attempt in range(6):
            wait = self.last + self.gap - time.time()
            if wait > 0:
                time.sleep(wait)
            self.last, self.calls = time.time(), self.calls + 1
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "paper-trader-study/2.0"})
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    body = json.loads(r.read().decode("utf-8", "replace"))
                self.ok_run += 1
                if self.ok_run >= 25:
                    self.ok_run, self.gap = 0, max(2.0, self.gap * 0.9)
                return body
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    self.r429 += e.code == 429
                    self.ok_run, self.gap = 0, min(self.max_gap, self.gap * 1.5)
                    time.sleep(min(150, 15 * (attempt + 1)))
                    continue
                break
            except Exception:
                time.sleep(5)
        self.fails += 1
        return None


class ChaosGT:
    """Wraps a client: random 429-like failures (None), empty and malformed bodies. Synthetic tests only."""

    def __init__(self, inner, seed=3):
        self.inner, self.rng = inner, random.Random(seed)

    def __getattr__(self, k):
        return getattr(self.inner, k)

    def get(self, path, **q):
        r = self.rng.random()
        if r < 0.08:
            return None
        if r < 0.12:
            return {}
        if r < 0.16:
            return {"data": {"attributes": {"ohlcv_list": [[1, None, 2], "x", []]}}} if "ohlcv" in path else {"data": [{"attributes": None}, 5]}
        return self.inner.get(path, **q)


def http_json(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "paper-trader-study/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


# ----------------------------------------------------------------------------- pools
def parse_gt(body, net, src, now):
    """dex_exit_study.parse_pools + FDV / market cap / current volume (for the market-cap estimate)."""
    out = []
    for p in (body or {}).get("data") or [] if isinstance(body, dict) else []:
        if not isinstance(p, dict):
            continue
        rows = parse_pools({"data": [p]}, net, src, now)
        if rows:
            a = p.get("attributes") or {}
            rows[0]["fdv"] = fnum(a.get("fdv_usd")) or fnum(a.get("market_cap_usd"))
            rows[0]["vol24_now"] = fnum(((a.get("volume_usd") or {}) if isinstance(a.get("volume_usd"), dict) else {}).get("h24"))
            out.append(rows[0])
    return out


def discover_gt(cl, now, pages):
    rows, by = [], collections.Counter()
    for net in NETS:
        qs = [(f"/networks/{net}/trending_pools", {"duration": d, "page": p}, f"trending_{d}")
              for d in ("1h", "6h", "24h") for p in range(1, pages + 1)]
        qs += [(f"/networks/{net}/new_pools", {"page": p}, "new") for p in range(1, 2 * pages + 1)]
        qs += [(f"/networks/{net}/pools", {"sort": "h24_volume_usd_desc", "page": p}, "top_volume") for p in range(1, 2 * pages + 1)]
        qs += [(f"/networks/{net}/pools", {"sort": "h24_tx_count_desc", "page": p}, "top_trades") for p in range(1, pages + 1)]
        for path, q, src in qs:
            got = parse_gt(cl.get(path, **q), net, src, now)
            by[src] += len(got)
            rows += got
    return rows, by


def discover_ds(now, fetch=http_json):
    """DexScreener boosts / profiles -> pairs (chain, pair address, created, liquidity, fdv) as GT-style rows."""
    if norm_ds is None or parse_dex_list is None:
        return [], collections.Counter()
    toks, by = [], collections.Counter()
    for u in ("https://api.dexscreener.com/token-boosts/top/v1", "https://api.dexscreener.com/token-boosts/latest/v1",
              "https://api.dexscreener.com/token-profiles/latest/v1"):
        try:
            toks += [(c, a) for c, a in parse_dex_list(fetch(u) or []) if c in DS_CHAIN]
        except Exception:
            pass
    rows, seen = [], set()
    for chain in DS_CHAIN:
        addrs = [a for c, a in toks if c == chain and (c, a) not in seen]
        for i in range(0, min(len(addrs), 150), 30):
            batch = addrs[i:i + 30]
            seen.update((chain, a) for a in batch)
            body = fetch(f"https://api.dexscreener.com/tokens/v1/{chain}/{','.join(batch)}")
            for p in body if isinstance(body, list) else []:
                try:
                    c = norm_ds(p, now)
                except Exception:
                    c = None
                if not c or not c.get("pair") or c["age_h"] is None or c["sym"] in MAJORS:
                    continue
                rows.append({"net": DS_CHAIN[chain], "pool": c["pair"], "token": c["addr"], "created": int(now - c["age_h"] * HOUR),
                             "sym": c["sym"][:14], "reserve": c["liq"], "price": c["price"], "seen": now, "src": "ds_boosts",
                             "fdv": c["fdv"], "vol24_now": c["vol24"]})
                by["ds_boosts"] += 1
    return rows, by


def merge_reg(reg, rows, now):
    """One entry per token; keeps the FIRST sighting (first_seen) and the largest-reserve sighting."""
    for r in rows:
        if r["sym"] in MAJORS or r["sym"].lstrip("$") in MAJORS:
            continue
        k = f"{r['net']}:{r['token']}"
        e = reg.get(k)
        if e is None:
            reg[k] = e = dict(r, srcs=[], ref_reserve=r["reserve"], ref_price=r["price"], first_seen=r.get("first_seen") or r["seen"])
        e.setdefault("first_seen", e.get("seen", now))
        e["first_seen"] = min(e["first_seen"], r.get("first_seen") or r["seen"])
        if r["src"] not in e["srcs"]:
            e["srcs"].append(r["src"])
        if r["reserve"] > e.get("ref_reserve", 0) and r["price"]:
            e.update(pool=r["pool"], created=r["created"], ref_reserve=r["reserve"], ref_price=r["price"])
        for k2 in ("fdv", "vol24_now"):
            if r.get(k2) and r["seen"] >= e.get("seen", 0):
                e[k2], e["price_now"], e["seen_now"] = r[k2], r["price"], r["seen"]
    return reg


def save_reg(path, reg, cap=12000):
    keep = sorted(reg.values(), key=lambda e: -e.get("seen", 0))[:cap]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(keep, f, separators=(",", ":"))


# ----------------------------------------------------------------------------- hourly grid + per-pool arrays
def hourly_grid(bars):
    """Hourly bars (sorted, cleaned) -> (t0, O, H, L, C, V) arrays on a full hourly grid; hours without
    trades carry the last close with zero volume."""
    if not bars:
        return None
    t0 = bars[0][0] // HOUR * HOUR
    n = (bars[-1][0] // HOUR * HOUR - t0) // HOUR + 1
    if n < 30 or n > 200_000:
        return None
    O, H, L, C, V = (array("d", [0.0]) * n for _ in range(5))
    j, last = 0, bars[0][1]
    by = {(b[0] // HOUR * HOUR - t0) // HOUR: b for b in bars}
    for i in range(n):
        b = by.get(i)
        if b:
            O[i], H[i], L[i], C[i], V[i] = b[1], b[2], b[3], b[4], b[5]
            last = b[4]
        else:
            O[i] = H[i] = L[i] = C[i] = last
    return t0, O, H, L, C, V


def roll_max(a, w, fwd=False):
    """out[i] = max(a[i-w+1..i]) (or, fwd: max(a[i+1..i+w])) with a monotonic deque, O(n)."""
    n, out, dq = len(a), array("d", [0.0]) * len(a), collections.deque()
    rng = range(n - 1, -1, -1) if fwd else range(n)
    for i in rng:
        if fwd:
            while dq and dq[0] > i + w:
                dq.popleft()
            out[i] = a[dq[0]] if dq else NAN
            while dq and a[dq[-1]] <= a[i]:
                dq.pop()
            dq.append(i)
        else:
            while dq and a[dq[-1]] <= a[i]:
                dq.pop()
            dq.append(i)
            while dq[0] <= i - w:
                dq.popleft()
            out[i] = a[dq[0]]
    return out


def roll_min(a, w, fwd=False):
    neg = array("d", [-x for x in a])
    return array("d", [-x for x in roll_max(neg, w, fwd)])


def prefix(a):
    out, s = array("d", [0.0]) * (len(a) + 1), 0.0
    for i, x in enumerate(a):
        s += x
        out[i + 1] = s
    return out


class Pool:
    """A pool's hourly grid plus everything the point features / labels / trade simulation need."""

    def __init__(self, p, grid, now, dead):
        self.p, self.now, self.dead = p, now, dead
        self.t0, self.O, self.H, self.L, self.C, self.V = grid
        self.n = len(self.C)
        self.pump = p["token"].lower().endswith("pump")
        self.fdv_ratio = (p["fdv"] / p["price_now"]) if p.get("fdv") and p.get("price_now") else None

    def derive(self):
        C, V, n = self.C, self.V, self.n
        self.cv = prefix(V)
        self.act = prefix(array("d", [1.0 if v > 0 else 0.0 for v in V]))
        r = array("d", [0.0] + [math.log(C[i] / C[i - 1]) if C[i - 1] > 0 and C[i] > 0 else 0.0 for i in range(1, n)])
        self.cr, self.cr2 = prefix(r), prefix(array("d", [x * x for x in r]))
        self.green = prefix(array("d", [1.0 if x > 0 else 0.0 for x in r]))
        self.rmax7, self.rmin24 = roll_max(C, W7), roll_min(C, W1)
        self.fmax1, self.fmax3, self.fmax7 = (roll_max(self.H, w, True) for w in (W1, W3, W7))
        self.fmin7 = roll_min(C, W7, True)
        prev24 = roll_max(C, W1)                    # max close of THIS and the previous 23 hours
        fwd24 = roll_max(C, W1, True)
        rug = array("d", [0.0]) * n
        for j in range(1, n):
            ref = prev24[j - 1]
            if ref > 0 and C[j] <= RUG_KEEP * ref and (fwd24[j] != fwd24[j] or fwd24[j] < 0.3 * ref):
                rug[j] = 1.0
        if self.dead:
            rug[n - 1] = 1.0
        self.rug, self.crug = rug, prefix(rug)

    def features(self, i):
        """Only data up to and including hour i (its close = decision time)."""
        C, V, cv = self.C, self.V, self.cv
        t = self.t0 + (i + 1) * HOUR
        c = C[i]
        if c <= 0 or i < 1:
            return None
        vol1, vol6, vol24 = V[i], cv[i + 1] - cv[max(0, i - 5)], cv[i + 1] - cv[max(0, i - 23)]
        h24 = min(24, i + 1)
        avg_ex1 = (vol24 - vol1) / max(1, h24 - 1)
        avg6_ex = (vol24 - vol6) / max(1, h24 - 6) * 6 if h24 > 6 else NAN
        prev24 = (cv[max(0, i - 23)] - cv[max(0, i - 47)]) if i >= 47 else NAN
        liq = liq_at(self.p, c)
        k = min(24, i)
        m = (self.cr[i + 1] - self.cr[i + 1 - k]) / k if k else 0.0
        var = (self.cr2[i + 1] - self.cr2[i + 1 - k]) / k - m * m if k >= 12 else NAN
        return {"t": t, "age_h": (t - self.p["created"]) / HOUR, "pump": float(self.pump), "sol": float(self.p["net"] == "solana"),
                "base": float(self.p["net"] == "base"), "liq": liq, "mcap": self.fdv_ratio * c if self.fdv_ratio else NAN,
                "vol1": vol1, "vol6": vol6, "vol24": vol24,
                "v1_rel": min(50.0, vol1 / avg_ex1) if avg_ex1 > 0 else (50.0 if vol1 > 0 else 0.0),
                "v6_rel": (min(50.0, vol6 / avg6_ex) if avg6_ex > 0 else (50.0 if vol6 > 0 else 0.0)) if avg6_ex == avg6_ex else NAN,
                "v24_rel": (min(50.0, vol24 / prev24) if prev24 > 0 else (50.0 if vol24 > 0 else 0.0)) if prev24 == prev24 else NAN,
                "vol24_liq": vol24 / liq if liq > 0 else NAN,
                "ch1": c / C[i - 1] - 1, "ch6": c / C[max(0, i - 6)] - 1, "ch24": c / C[max(0, i - 24)] - 1, "ch0": c / C[0] - 1,
                "dd7": c / self.rmax7[i] - 1, "up24": c / self.rmin24[i] - 1,
                "vola24": math.sqrt(max(0.0, var)) if var == var else NAN,
                "green6": (self.green[i + 1] - self.green[max(0, i - 5)]) / min(6, i),
                "act24": (self.act[i + 1] - self.act[max(0, i - 23)]) / h24,
                "hour": float(t // HOUR % 24), "wday": float((t // DAY + 3) % 7), "c": c, "i": i}

    def labels(self, i):
        """What happened in the 7 days after hour i. None if the window is cut short (pool still alive)."""
        if i + W7 >= self.n and not self.dead:
            return None
        c = self.C[i]
        f7 = self.fmax7[i]
        if f7 != f7:                                    # dead pool, no bars after i at all
            return {"m1": 1.0, "m3": 1.0, "m7": 1.0, "low7": 0.0, "rug7": 1.0}
        m1, m3, lo = self.fmax1[i], self.fmax3[i], self.fmin7[i]
        rug = self.crug[min(self.n, i + W7 + 1)] - self.crug[i + 1] > 0
        return {"m1": (m1 if m1 == m1 else f7) / c, "m3": (m3 if m3 == m3 else f7) / c, "m7": f7 / c,
                "low7": (lo if lo == lo else 0.0) / c, "rug7": float(rug)}

    def sample_idx(self, rng, ws0):
        """Decision hours: every hour in the first day of life, every 6h up to a week, daily to a month, 48h after."""
        out, off = [], rng.randint(0, 47)             # random phase per pool: hours of day stay evenly sampled
        for i in range(1, self.n):
            t = self.t0 + (i + 1) * HOUR
            if t < ws0 or t > self.now - W7 * HOUR and not self.dead:
                continue
            age = (t - self.p["created"]) / HOUR
            step = 1 if age <= 24 else 6 if age <= 168 else 24 if age <= 720 else 48
            if (t // HOUR + off) % step == 0:
                out.append(i)
        return out


# ----------------------------------------------------------------------------- trade simulation (engine exit)
def cost(usd, liq):
    return min(1.0, FEE + SLIP + (usd / liq if liq > 0 else 1.0))


def simulate(P, i, liq):
    """Engine exit from config.DEX['exit'] on the hourly grid after hour i (entry at its close).
    -> (return, exit time, peak multiple, still open?, rugged?)"""
    e, X = P.C[i], EXIT
    t0 = P.t0 + (i + 1) * HOUR
    q = SIZE * (1 - cost(SIZE, liq)) / e
    trail0, steps, R = X.get("trail", 0.95), X.get("trail_steps", []), X.get("runner_at_limit")
    hold_h, hz = int(X.get("max_hold_days", 14) * 24), HORIZON_D * 24
    peak, stop, runner = e, e * (1 - trail0), False

    def out(px, t, rug=False):
        usd = q * px
        v = usd * (1 + RUG_LOSS) if rug else usd * (1 - cost(usd, liq * math.sqrt(px / e)))
        return v / SIZE - 1, t, peak / e, False, rug

    for j in range(i + 1, min(P.n, i + hz + 1)):
        tj = P.t0 + j * HOUR
        if P.rug[j]:
            return out(e, tj + HOUR, True)
        if not runner and j - i > hold_h:              # hour j starts >= max_hold after the entry
            if R and P.O[j] >= e * (1 + R[0]):
                runner = True
            else:
                return out(P.O[j], tj)
        if P.L[j] <= stop:
            return out(min(P.O[j], stop), tj + HOUR)
        peak = max(peak, P.H[j])
        tr = trail0
        for mult, w in steps:
            if peak >= e * mult:
                tr = w
        if runner:
            tr = min(tr, R[1])
        stop = max(stop, peak * (1 - tr))
        if j - i >= hz:
            return out(P.C[j], tj + HOUR)
    if P.dead:
        return out(e, P.t0 + P.n * HOUR, True)
    last = P.C[P.n - 1]
    usd = q * last
    return usd * (1 - cost(usd, liq * math.sqrt(last / e))) / SIZE - 1, P.t0 + P.n * HOUR, peak / e, True, False


# ----------------------------------------------------------------------------- statistics helpers
def rate(xs):
    return mean(xs) if xs else NAN


def quantiles(xs, k=5):
    xs = sorted(x for x in xs if x == x)
    if len(xs) < 2 * k:
        return []
    return [xs[int(len(xs) * j / k)] for j in range(1, k)]


def bucket(x, edges):
    return bisect.bisect_right(edges, x) if x == x else -1


def auc(scores, ys):
    """Rank AUC (ties get half credit)."""
    pairs = sorted(zip(scores, ys))
    n1 = sum(ys)
    n0 = len(ys) - n1
    if n1 == 0 or n0 == 0:
        return NAN
    s, i = 0.0, 0
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        r = (i + j + 1) / 2                          # average rank (1-based) of the tie group
        s += sum(r for k in range(i, j) if pairs[k][1])
        i = j
    return (s - n1 * (n1 + 1) / 2) / (n1 * n0)


def pool_boot(keys, ys, n=1000, seed=5):
    """95% CI of a hit rate with pools as the resampling unit (points of one pool are not independent)."""
    agg = collections.defaultdict(lambda: [0, 0])
    for k, y in zip(keys, ys):
        agg[k][0] += y
        agg[k][1] += 1
    pools = list(agg.values())
    if len(pools) < 3:
        return NAN, NAN
    rng = random.Random(seed)
    ms = []
    for _ in range(n):
        s = rng.choices(pools, k=len(pools))
        tot = sum(x[1] for x in s)
        ms.append(sum(x[0] for x in s) / tot if tot else NAN)
    ms.sort()
    return ms[int(0.025 * n)], ms[int(0.975 * n) - 1]


def med(xs):
    xs = [x for x in xs if x == x]
    return statistics.median(xs) if xs else NAN


def fmt(x, kind="f"):
    if x != x:
        return "n/a"
    if kind == "%":
        return f"{x * 100:.0f}%"
    if kind == "$":
        return f"${x / 1e6:.1f}M" if abs(x) >= 1e6 else f"${x / 1e3:.0f}k"
    return f"{x:.2f}"


# ----------------------------------------------------------------------------- feature analysis
FIXED = {"age_h": ([6, 24, 72, 168, 720], "h"), "liq": ([50e3, 100e3, 250e3, 1e6], "$"), "mcap": ([1e5, 1e6, 1e7, 1e8], "$"),
         "hour": ([4, 8, 12, 16, 20], "h"), "wday": ([1, 2, 3, 4, 5, 6], "d"), "vol24": ([50e3, 100e3, 300e3, 1e6], "$")}
BIN = {"pump": ("other", "pump.fun"), "sol": ("not solana", "solana"), "base": ("not base", "base")}
DOLLAR = {"liq", "mcap", "vol1", "vol6", "vol24"}


def edges_for(f, old_pts):
    if f in FIXED:
        return FIXED[f][0]
    if f in BIN:
        return [0.5]
    return quantiles([p[f] for p in old_pts], 5)


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def bucket_name(f, edges, b):
    if b < 0:
        return "n/a"
    if f in BIN:
        return BIN[f][b]
    if f == "hour":
        return f"{4 * b:02d}-{4 * b + 4:02d} UTC"
    if f == "wday":
        return DAYS[b] if b < 7 else "?"
    lo = edges[b - 1] if b > 0 else None
    hi = edges[b] if b < len(edges) else None
    kind = FIXED.get(f, (None, "f"))[1]
    g = (lambda x: fmt(x, "$")) if kind == "$" else (lambda x: f"{x:g}h") if kind == "h" else (lambda x: f"{x:.2f}")
    return ("<" + g(hi)) if lo is None else (">=" + g(lo)) if hi is None else f"{g(lo)}..{g(hi)}"


def lift_table(f, pts, old, new, target="run2"):
    """Per bucket: n (old/new), P(2x/7d) old & new with lift, P(5x), P(rug) (all), on edges from the older half."""
    edges = edges_for(f, old)
    if not edges:
        return None, []
    rows = []
    base_o, base_n = rate([p[target] for p in old]), rate([p[target] for p in new])
    nb = len(edges) + 1
    go, gn = collections.defaultdict(list), collections.defaultdict(list)
    for p in old:
        go[bucket(p[f], edges)].append(p)
    for p in new:
        gn[bucket(p[f], edges)].append(p)
    for b in list(range(nb)) + [-1]:
        o, nn = go.get(b, []), gn.get(b, [])
        if not o and not nn:
            continue
        a = o + nn
        rows.append({"b": b, "name": bucket_name(f, edges, b), "n_o": len(o), "n_n": len(nn),
                     "r_o": rate([p[target] for p in o]), "r_n": rate([p[target] for p in nn]),
                     "r5": rate([p["run5"] for p in a]), "r10": rate([p["run10"] for p in a]), "rug": rate([p["rug7"] for p in a]),
                     "m1": rate([p["m1"] >= 2 for p in a]), "pools": len({p["k"] for p in a})})
    for r in rows:
        r["l_o"] = r["r_o"] / base_o if base_o > 0 and r["r_o"] == r["r_o"] else NAN
        r["l_n"] = r["r_n"] / base_n if base_n > 0 and r["r_n"] == r["r_n"] else NAN
    return edges, rows


def print_lift(f, rows, live):
    print(f"\n{f:<10} {'bucket':<16} {'n old':>6} {'2x/7d old':>9} {'lift':>5} | {'n new':>6} {'2x/7d new':>9} {'lift':>5} | "
          f"{'2x/1d':>5} {'5x/7d':>5} {'10x/7d':>6} {'rug7':>5} {'pools':>5}   live: {live or 'NOT available live - log it (section 9)'}")
    for r in rows:
        print(f"{'':<10} {r['name']:<16} {r['n_o']:>6} {fmt(r['r_o'], '%'):>9} {fmt(r['l_o']):>5} | {r['n_n']:>6} {fmt(r['r_n'], '%'):>9} "
              f"{fmt(r['l_n']):>5} | {fmt(r['m1'], '%'):>5} {fmt(r['r5'], '%'):>5} {fmt(r['r10'], '%'):>6} {fmt(r['rug'], '%'):>5} {r['pools']:>5}")


def build_score(pts, old, new, min_n=300, min_lift=1.3, max_rug_lift=1.6):
    """Points score from the OLDER half only: +1 per feature whose good buckets (lift >= 1.3 on 2x/7d, not
    rug-prone) contain the point. -> (rules, tables)"""
    rules, tables = [], {}
    base_rug = rate([p["rug7"] for p in old])
    for f in FEATS:
        edges, rows = lift_table(f, pts, old, new)
        tables[f] = (edges, rows)
        if not rows:
            continue
        good = [r["b"] for r in rows if r["b"] >= 0 and r["n_o"] >= min_n and r["l_o"] >= min_lift
                and (base_rug <= 0 or r["rug"] <= max_rug_lift * base_rug + 0.02)]
        if good:
            cover = sum(r["n_o"] for r in rows if r["b"] in good) / max(1, len(old))
            lift = mean([r["l_o"] for r in rows if r["b"] in good])
            rules.append({"f": f, "edges": edges, "good": good, "cover": cover, "lift": lift,
                          "words": " or ".join(bucket_name(f, edges, b) for b in good), "live": LIVE.get(f)})
    return rules, tables


def score_of(p, rules):
    return sum(1 for r in rules if bucket(p[r["f"]], r["edges"]) in r["good"])


# ----------------------------------------------------------------------------- logistic regression (stdlib)
LOGIT_X = ["age_h", "pump", "sol", "base", "liq", "mcap", "vol1", "vol24", "v1_rel", "v6_rel", "v24_rel", "vol24_liq",
           "ch1", "ch6", "ch24", "dd7", "up24", "vola24", "green6", "act24"]
LOGS = {"age_h", "liq", "mcap", "vol1", "vol24", "v1_rel", "v6_rel", "v24_rel", "vol24_liq"}


class Logit:
    def __init__(self, old, seed=11, max_rows=20000, iters=250, l2=0.02):
        rng = random.Random(seed)
        rows = old if len(old) <= max_rows else rng.sample(old, max_rows)
        self.fill = {f: med([self._raw(p, f) for p in rows]) for f in LOGIT_X}
        X = [[self._t(p, f) for f in LOGIT_X] for p in rows]
        self.mu = [mean([x[j] for x in X]) for j in range(len(LOGIT_X))]
        self.sd = [max(1e-9, statistics.pstdev([x[j] for x in X])) for j in range(len(LOGIT_X))]
        Z = [self._z(x) for x in X]
        y = [float(p["run2"]) for p in rows]
        k, n = len(LOGIT_X) + 1, len(Z)
        w = [0.0] * k
        w[0] = math.log(max(1e-6, mean(y)) / max(1e-6, 1 - mean(y)))
        lr = 0.5
        for _ in range(iters):
            g = [0.0] * k
            for z, yy in zip(Z, y):
                s = w[0] + sum(wi * zi for wi, zi in zip(w[1:], z))
                pr = 1 / (1 + math.exp(-max(-30, min(30, s))))
                d = pr - yy
                g[0] += d
                for j in range(1, k):
                    g[j] += d * z[j - 1]
            for j in range(k):
                w[j] -= lr * (g[j] / n + (l2 * w[j] if j else 0.0))
        self.w = w

    @staticmethod
    def _raw(p, f):
        return p.get(f, NAN)

    def _t(self, p, f):
        x = p.get(f, NAN)
        if x != x:
            x = self.fill[f]
        if x != x:
            x = 0.0
        if f in LOGS:
            return math.log1p(max(0.0, x))
        return max(-1.0, min(5.0, x))

    def _z(self, x):
        return [max(-3.0, min(3.0, (xi - m) / s)) for xi, m, s in zip(x, self.mu, self.sd)]

    def prob(self, p):
        z = self._z([self._t(p, f) for f in LOGIT_X])
        s = self.w[0] + sum(wi * zi for wi, zi in zip(self.w[1:], z))
        return 1 / (1 + math.exp(-max(-30, min(30, s))))


# ----------------------------------------------------------------------------- trading rules
def make_rules(s_star, p90, p95):
    ml, mv, ma = SCREEN.get("min_liq", 100_000), SCREEN.get("min_vol24", 100_000), SCREEN.get("min_age_h", 6)
    h1 = ENTRY.get("h1", 0.10)

    def floors(f, liq=ml, vol=mv, age=ma):
        return f["liq"] >= liq and f["vol24"] >= vol and f["age_h"] >= age

    R = [("engine today: 1h>=+{:.0%}, age>={}h, liq>=${}k, vol24>=${}k".format(h1, ma, ml // 1000, mv // 1000),
          lambda f, s, q: floors(f) and f["ch1"] >= h1),
         (f"engine + score>={s_star}", lambda f, s, q: floors(f) and f["ch1"] >= h1 and s >= s_star),
         (f"score>={s_star}, age>={ma}h, engine floors", lambda f, s, q: floors(f) and s >= s_star),
         (f"score>={s_star + 1}, age>={ma}h, engine floors", lambda f, s, q: floors(f) and s >= s_star + 1),
         (f"score>={s_star}, age>=1h, engine floors", lambda f, s, q: floors(f, age=1) and s >= s_star),
         (f"score>={s_star}, age>=1h, liq>=$50k, vol24>=$50k", lambda f, s, q: floors(f, 50_000, 50_000, 1) and s >= s_star),
         (f"logit top 10% (p>={p90:.3f}), engine floors", lambda f, s, q: floors(f) and q >= p90),
         (f"logit top 5% (p>={p95:.3f}), engine floors", lambda f, s, q: floors(f) and q >= p95),
         (f"logit top 10%, age>=1h, liq>=$50k", lambda f, s, q: floors(f, 50_000, 50_000, 1) and q >= p90)]
    return R


def trade_stats(trades, res, t_from, t_to, split):
    xs = [x[0] for x in res]
    if not xs:
        return None
    days = max(1.0, (t_to - t_from) / DAY)
    o = [x[0] for tr, x in zip(trades, res) if tr["t0"] < split]
    n_ = [x[0] for tr, x in zip(trades, res) if tr["t0"] >= split]
    return {"n": len(xs), "per_day": len(xs) / days, "win": rate([x > 0 for x in xs]), "med": statistics.median(xs),
            "mean": mean(xs), "ci": boot_ci(xs), "rug": rate([x[4] for x in res]), "x2": rate([x >= 1.0 for x in xs]),
            "x5": rate([x >= 4.0 for x in xs]), "open": rate([x[3] for x in res]),
            "hold": mean([(x[1] - tr["t0"]) / HOUR for tr, x in zip(trades, res)]),
            "mean_o": mean(o) if o else NAN, "mean_n": mean(n_) if n_ else NAN, "n_o": len(o), "n_n": len(n_),
            "pf_full": portfolio(trades, res, t_from, t_to), "pf_old": portfolio(trades, res, t_from, split),
            "pf_new": portfolio(trades, res, split, t_to)}


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--chaos", action="store_true", help="synthetic: inject 429s / empty / broken responses")
    ap.add_argument("--max-pools", type=int, default=3000)
    ap.add_argument("--pages", type=int, default=5)
    ap.add_argument("--months", type=float, default=2.7, help="history window (2.7 months = 2 hourly pages)")
    ap.add_argument("--hourly-pages", type=int, default=2)
    ap.add_argument("--budget-min", type=float, default=290, help="stop fetching new pools after this")
    ap.add_argument("--registry", default="results/dex_runner_pools.json")
    ap.add_argument("--seed-registry", default="results/dex_exit_pools.json")
    ap.add_argument("--points-out", default="results/dex_runner_points.csv.gz")
    ap.add_argument("--max-csv", type=int, default=60_000)
    ap.add_argument("--max-points", type=int, default=220_000)
    a = ap.parse_args()
    t_start = time.time()

    if a.synthetic:
        print("SYNTHETIC MODE: fake prices, only checks that the study runs end to end" + (" (chaos on)" if a.chaos else "") + "\n")
        cl = SyntheticGT()
        now = cl.now
        reg = merge_reg({}, [dict(r, first_seen=r["seen"]) for r in cl.seed_registry()], now)
        if a.chaos:
            cl = ChaosGT(cl)
        ds_fetch = lambda u: None
    else:
        cl, now = AdaptiveGT(), int(time.time())
        reg = load_registry(a.registry)
        seed = load_registry(a.seed_registry)
        for k, e in seed.items():
            if k not in reg:
                reg[k] = dict(e, first_seen=e.get("first_seen") or e.get("seen", now))
        ds_fetch = http_json
    n_prev = len(reg)

    # 1. pools ---------------------------------------------------------------------------------------
    banner("1. POOLS AND DATA")
    rows, by = discover_gt(cl, now, a.pages)
    rows2, by2 = discover_ds(now, ds_fetch)
    rows += rows2
    by.update(by2)
    merge_reg(reg, rows, now)
    if not a.synthetic:
        save_reg(a.registry, reg)
    print(f"listed now: {len(rows)} pool rows ({', '.join(f'{k} {v}' for k, v in sorted(by.items()))}); registry {n_prev} -> {len(reg)} tokens")
    ws0 = now - int(a.months * 30.44 * DAY)
    cand = [p for p in reg.values() if p["created"] <= now - 8 * DAY and p.get("ref_reserve", 0) >= 15_000 and p.get("pool")]
    rng = random.Random(42)
    rng.shuffle(cand)
    blind = lambda p: p.get("first_seen", now) <= now - 8 * DAY or "new" in p.get("srcs", [])
    cand.sort(key=lambda p: (not blind(p), -p.get("ref_reserve", 0) if not blind(p) else 0))
    cand = cand[:a.max_pools]
    print(f"{len(cand)} candidate pools (>= 8 days old, >= $15k reserve ever seen; {sum(blind(p) for p in cand)} known before their "
          f"outcome = outcome-blind, fetched first); window from {ts(ws0)}")

    pools, why = [], collections.Counter()
    for n, p in enumerate(cand):
        if time.time() - t_start > a.budget_min * 60:
            why["budget"] += len(cand) - n
            break
        ws = max(p["created"], ws0)
        try:
            hourly, complete = fetch_series(cl, p, "hour", 1, ws, now, a.hourly_pages)
        except Exception as e:                       # never die on one pool
            hourly, complete = [], False
            why["error"] += 1
        if len(hourly) < 30:
            why["no data"] += 1
            continue
        grid = hourly_grid(clean(hourly))
        if not grid:
            why["short"] += 1
            continue
        last_close = hourly[-1][0] + HOUR
        dead = complete and now - last_close > DEAD_H * HOUR
        P = Pool(p, grid, now, dead)
        P.key = f"{p['net']}:{p['token']}"
        pools.append(P)
        if n % 100 == 0:
            print(f"  fetched {n + 1}/{len(cand)}  calls {cl.calls}  429s {cl.r429}  gap {getattr(cl, 'gap', 0):.1f}s  pools kept {len(pools)}"
                  f"  {time.time() - t_start:.0f}s")
            sys.stdout.flush()
    print(f"API calls {cl.calls} (429s {cl.r429}, failed {cl.fails}); pools with usable history {len(pools)}; skipped: "
          + ", ".join(f"{k} {v}" for k, v in why.items()) + f"; {time.time() - t_start:.0f}s")
    if len(pools) < 10:
        print("\ntoo few pools with history - check API reachability above")
        return

    # 2. decision points --------------------------------------------------------------------------------
    banner("2. DECISION POINTS AND LABELS")
    pts, rngp = [], random.Random(7)
    for P in pools:
        P.derive()
        for i in P.sample_idx(rngp, ws0):
            f = P.features(i)
            lab = P.labels(i)
            if not f or not lab:
                continue
            f.update(lab)
            f["k"], f["blind"] = P.key, float(P.p.get("first_seen", now) <= f["t"] + W7 * HOUR)
            f["run2"], f["run5"], f["run10"], f["dud"] = float(lab["m7"] >= 2), float(lab["m7"] >= 5), float(lab["m7"] >= 10), \
                float(lab["m7"] < 1.3 and not lab["rug7"])
            pts.append(f)
        for k in ("fmax1", "fmax3", "fmax7", "fmin7", "crug"):      # labels done: free memory
            delattr(P, k)
    if len(pts) > a.max_points:
        pts = random.Random(9).sample(pts, a.max_points)
    if len(pts) < 200:
        print(f"only {len(pts)} labelled points - too few to study")
        return
    pts.sort(key=lambda p: p["t"])
    split = pts[len(pts) // 2]["t"]
    old, new = [p for p in pts if p["t"] < split], [p for p in pts if p["t"] >= split]
    T0, T1 = pts[0]["t"], now
    print(f"{len(pts)} decision points from {len(pools)} pools, {ts(T0)} .. {ts(pts[-1]['t'])}; older half < {ts(split)} <= newer half "
          f"({len(old)} / {len(new)} points); outcome-blind points {sum(p['blind'] for p in pts):.0f}")
    for lab, key in (("2x within 1d", lambda p: p["m1"] >= 2), ("2x within 3d", lambda p: p["m3"] >= 2), ("2x within 7d", lambda p: p["run2"]),
                     ("5x within 7d", lambda p: p["run5"]), ("10x within 7d", lambda p: p["run10"]), ("rug within 7d", lambda p: p["rug7"]),
                     ("dud (peak < 1.3x, no rug)", lambda p: p["dud"])):
        ys = [float(bool(key(p))) for p in pts]
        lo, hi = pool_boot([p["k"] for p in pts], ys)
        print(f"  {lab:<28} {rate(ys):>6.1%}  (pool-clustered 95% CI {fmt(lo, '%')}..{fmt(hi, '%')});  older {rate([float(bool(key(p))) for p in old]):.1%}"
              f"  newer {rate([float(bool(key(p))) for p in new]):.1%}  |  by network: "
              + "  ".join(f"{n} {rate([float(bool(key(p))) for p in pts if P_net(p) == n]):.1%}" for n in NETS))
    bl = [p for p in pts if p["blind"]]
    if len(bl) >= 100:
        print(f"  outcome-blind points only ({len(bl)}): 2x/7d {rate([p['run2'] for p in bl]):.1%}, 5x/7d {rate([p['run5'] for p in bl]):.1%}, "
              f"rug7 {rate([p['rug7'] for p in bl]):.1%}  <- the least biased base rates")
    print("  NOTE: pools were picked today, so pools that rugged before we knew them are missing; rug rates are floors, "
          "runner rates are ceilings (worst in the newer half). Compare buckets, don't trust the absolute level.")

    # 3. runner vs dud vs rug medians ---------------------------------------------------------------------
    banner("3. WHAT THE RUNNERS LOOKED LIKE BEFORE THE RUN  (median of each feature at the decision point)")
    groups = [("10x+/7d", [p for p in pts if p["run10"]]), ("5x-10x/7d", [p for p in pts if p["run5"] and not p["run10"]]),
              ("2x-5x/7d", [p for p in pts if p["run2"] and not p["run5"]]), ("dud", [p for p in pts if p["dud"]]),
              ("rug7", [p for p in pts if p["rug7"]])]
    print(f"{'feature':<10} " + " ".join(f"{g:>12}" for g, _ in groups) + "   (n = " + ", ".join(str(len(g)) for _, g in groups) + ")")
    for f in FEATS:
        vals = []
        for _, g in groups:
            m = med([p[f] for p in g])
            vals.append("n/a" if m != m else fmt(m, "$") if f in DOLLAR else f"{m:.0f}h" if f == "age_h" else f"{m:.0f}:00 UTC" if f == "hour"
                        else DAYS[int(m)] if f == "wday" else fmt(m, "%") if f in BIN or f.startswith("ch") or f in ("dd7", "up24", "green6", "act24") else fmt(m))
        print(f"{f:<10} " + " ".join(f"{v:>12}" for v in vals))

    # 4. lift tables + points score (older half) -----------------------------------------------------------
    banner("4. HIT RATES PER FEATURE BUCKET  (bucket edges from the older half; lift = rate / base rate of that half)")
    print(f"base rate 2x within 7d: older {rate([p['run2'] for p in old]):.1%}, newer {rate([p['run2'] for p in new]):.1%}; "
          f"rug7 older {rate([p['rug7'] for p in old]):.1%}, newer {rate([p['rug7'] for p in new]):.1%}")
    rules, tables = build_score(pts, old, new)
    for f in FEATS:
        edges, rws = tables[f]
        if rws:
            print_lift(f, rws, LIVE.get(f))
    print("\nsingle-feature AUC for 2x/7d (0.5 = useless; > 0.5 higher is better, < 0.5 lower is better), older | newer:")
    for f in FEATS:
        ao = auc([p[f] if p[f] == p[f] else -1e18 for p in old], [p["run2"] for p in old])
        an = auc([p[f] if p[f] == p[f] else -1e18 for p in new], [p["run2"] for p in new])
        print(f"  {f:<10} {ao:>5.3f} | {an:>5.3f}" + ("   consistent" if (ao - 0.5) * (an - 0.5) > 0 and min(abs(ao - 0.5), abs(an - 0.5)) >= 0.03 else ""))

    banner("5. POINTS SCORE  (built on the OLDER half only: +1 per rule; tested on the NEWER half)")
    if not rules:
        print("no feature bucket reached lift >= 1.3 with >= 300 older points: no score can be built from this sample")
    for r in rules:
        print(f"  +1 if {r['f']} in {r['words']:<40} (older-half lift {r['lift']:.2f}, covers {r['cover']:.0%} of points; "
              f"live: {r['live'] or 'NOT available live'})")
    for p in pts:
        p["score"] = score_of(p, rules)
    smax = len(rules)
    print(f"\n{'score':>6} {'n old':>6} {'2x/7d old':>9} {'5x/7d':>6} {'rug7':>5} | {'n new':>6} {'2x/7d new':>9} {'5x/7d':>6} {'10x':>5} {'rug7':>5} "
          f"{'95% CI (pools)':>16} | {'pools new':>9}")
    levels = {}
    for s in range(smax + 1):
        o = [p for p in old if p["score"] >= s]
        n_ = [p for p in new if p["score"] >= s]
        if not o and not n_:
            continue
        lo, hi = pool_boot([p["k"] for p in n_], [p["run2"] for p in n_])
        levels[s] = (rate([p["run2"] for p in o]), len(o), rate([p["run2"] for p in n_]), len(n_))
        print(f">={s:>4} {len(o):>6} {fmt(rate([p['run2'] for p in o]), '%'):>9} {fmt(rate([p['run5'] for p in o]), '%'):>6} "
              f"{fmt(rate([p['rug7'] for p in o]), '%'):>5} | {len(n_):>6} {fmt(rate([p['run2'] for p in n_]), '%'):>9} "
              f"{fmt(rate([p['run5'] for p in n_]), '%'):>6} {fmt(rate([p['run10'] for p in n_]), '%'):>5} {fmt(rate([p['rug7'] for p in n_]), '%'):>5} "
              f"{fmt(lo, '%') + '..' + fmt(hi, '%'):>16} | {len({p['k'] for p in n_}):>9}")
    base_o = rate([p["run2"] for p in old])
    s_star = next((s for s in sorted(levels) if levels[s][1] >= 200 and levels[s][0] >= 1.5 * base_o), None)
    if s_star is None:
        s_star = max((s for s in levels if levels[s][1] >= 100), default=0)
    print(f"chosen threshold (older half: first level with >= 200 points and >= 1.5x the base rate, else the highest with >= 100): score >= {s_star}"
          + (f" -> newer half {fmt(levels[s_star][2], '%')} of {levels[s_star][3]} points ran 2x within 7d" if s_star in levels else ""))
    a_o = auc([p["score"] for p in old], [p["run2"] for p in old])
    a_n = auc([p["score"] for p in new], [p["run2"] for p in new])
    print(f"score AUC for 2x/7d: older (in-sample) {a_o:.3f}, newer (out-of-sample) {a_n:.3f}")

    banner("6. LOGISTIC REGRESSION  (L2, standardized log features, fit on the older half, tested on the newer half)")
    L = Logit(old)
    for p in pts:
        p["q"] = L.prob(p)
    print("coefficients (per standard deviation; + = more 2x runs):")
    for f, w in sorted(zip(LOGIT_X, L.w[1:]), key=lambda z: -abs(z[1])):
        print(f"  {f:<10} {w:+.3f}")
    qo = sorted(p["q"] for p in old)
    p90, p95 = qo[int(0.9 * len(qo))], qo[int(0.95 * len(qo))]
    print(f"AUC 2x/7d: older (in-sample) {auc([p['q'] for p in old], [p['run2'] for p in old]):.3f}, newer (out-of-sample) "
          f"{auc([p['q'] for p in new], [p['run2'] for p in new]):.3f}")
    print(f"{'newer half decile':>18} {'n':>6} {'2x/7d':>6} {'5x/7d':>6} {'10x/7d':>6} {'rug7':>5} {'lift':>5}")
    qn = sorted(new, key=lambda p: p["q"])
    base_n = rate([p["run2"] for p in new])
    for d in range(10):
        g = qn[int(len(qn) * d / 10): int(len(qn) * (d + 1) / 10)]
        if g:
            r2 = rate([p["run2"] for p in g])
            print(f"{d + 1:>18} {len(g):>6} {fmt(r2, '%'):>6} {fmt(rate([p['run5'] for p in g]), '%'):>6} {fmt(rate([p['run10'] for p in g]), '%'):>6} "
                  f"{fmt(rate([p['rug7'] for p in g]), '%'):>5} {fmt(r2 / base_n if base_n else NAN):>5}")
    top_n = [p for p in new if p["q"] >= p90]
    print(f"newer half, logit top 10% (older cut p >= {p90:.3f}): n {len(top_n)}, 2x/7d {fmt(rate([p['run2'] for p in top_n]), '%')}, "
          f"5x/7d {fmt(rate([p['run5'] for p in top_n]), '%')}, rug7 {fmt(rate([p['rug7'] for p in top_n]), '%')}")

    # 7. trading ----------------------------------------------------------------------------------------------
    banner(f"7. TRADING THE SCORES THROUGH THE ENGINE'S LIVE EXIT  ($500 per trade, costs {FEE:.1%} + {SLIP:.0%} + impact per side; "
           f"hold {EXIT.get('max_hold_days', 14)}d, trail {EXIT.get('trail')}, steps {EXIT.get('trail_steps')}, runner {EXIT.get('runner_at_limit')})")
    R = make_rules(s_star, p90, p95)
    trades = {name: [] for name, _ in R}
    res = {name: [] for name, _ in R}
    t_last = now - DAY
    for P in pools:
        locked = {name: 0 for name, _ in R}
        for i in range(1, P.n):
            t = P.t0 + (i + 1) * HOUR
            if t < ws0 or t > t_last or P.cv[i + 1] - P.cv[max(0, i - 23)] < 50_000:   # every rule needs vol24 >= $50k
                continue
            f = None
            for name, fn in R:
                if t < locked[name]:
                    continue
                if f is None:
                    f = P.features(i)
                    if not f:
                        break
                    f["score"], f["q"] = score_of(f, rules), L.prob(f)
                try:
                    hit = fn(f, f["score"], f["q"])
                except (TypeError, ValueError):
                    hit = False
                if hit:
                    x = simulate(P, i, f["liq"])
                    locked[name] = x[1]
                    trades[name].append({"t0": t, "k": P.key, "sym": P.p["sym"], "net": P.p["net"], "liq": f["liq"]})
                    res[name].append(x)
    print(f"{'entry rule':<52} {'n':>5} {'/day':>5} {'win':>4} {'median':>7} {'mean':>7} {'95% CI':>16} {'>=2x':>5} {'>=5x':>5} {'rug':>4} "
          f"{'hold h':>6} | {'month full':>10} {'older':>7} {'newer':>7} {'maxDD':>6} {'/day new':>8}")
    ST = {}
    for name, _ in R:
        s = ST[name] = trade_stats(trades[name], res[name], T0, T1, split)
        if not s:
            print(f"{name:<52} {0:>5}")
            continue
        print(f"{name:<52} {s['n']:>5} {s['per_day']:>5.2f} {s['win']:>4.0%} {pct(s['med'], 7)} {pct(s['mean'], 7)} "
              f"[{pct(s['ci'][0])},{pct(s['ci'][1])}] {s['x2']:>5.0%} {s['x5']:>5.0%} {s['rug']:>4.0%} {s['hold']:>6.0f} | "
              f"{pct(s['pf_full']['monthly'], 10)} {pct(s['pf_old']['monthly'], 7)} {pct(s['pf_new']['monthly'], 7)} "
              f"{pct(s['pf_full']['dd'], 6, 0)} {s['n_n'] / max(1.0, (T1 - split) / DAY):>8.2f}")
    print("(month = compounding 4-slot account, 1/4 of equity per trade, busy slots skip signals; older / newer = the two halves of "
          "the window; the score thresholds were chosen on the older half, so 'newer' is out-of-sample)")
    for name in list(ST)[:3]:
        if ST[name]:
            top = sorted(zip(trades[name], res[name]), key=lambda z: -z[1][0])[:6]
            print(f"  best trades, {name[:40]}: " + ", ".join(f"{tr['sym']} ({tr['net']}) {pct(x[0], 1)}" for tr, x in top))

    # 8. recommendation -----------------------------------------------------------------------------------------
    banner("8. RECOMMENDATION FOR config.DEX / dex.py")
    eng = ST[R[0][0]]
    cands = [(n, s) for n, s in ST.items() if s and s["n_o"] >= 15 and s["n_n"] >= 15]
    best = max(cands, key=lambda z: min(z[1]["pf_old"]["monthly"], z[1]["pf_new"]["monthly"]), default=None)
    rec = {}
    if rules:
        rec["runner_score"] = {"min_points": s_star, "rules": [{"feature": r["f"], "buckets": r["words"], "edges": [round(x, 4) for x in r["edges"]],
                                                                 "good": r["good"], "live_field": r["live"]} for r in rules]}
    live_ok = [r for r in rules if r["live"]]
    if best:
        nm, s = best
        low_age = "age>=1h" in nm
        low_liq = "$50k" in nm
        rec["screen"] = {"min_age_h": 1 if low_age else SCREEN.get("min_age_h", 6), "min_liq": 50_000 if low_liq else SCREEN.get("min_liq", 100_000),
                         "min_vol24": 50_000 if low_liq else SCREEN.get("min_vol24", 100_000)}
        rec["entry"] = {"h1": ENTRY.get("h1", 0.10) if nm.startswith("engine") else 0.0, "h6": -1.0, "buy_ratio": 1.2,
                        "score_min": s_star if "score" in nm else None, "logit_min": round(p90, 4) if "logit" in nm else None}
    print(json.dumps(rec, indent=1))

    banner("9. FEATURES THAT ONLY EXIST LIVE - dex.py should start logging them now")
    print("""Not in any price history: buys vs sells (1h / 24h), unique buyers, holder count and its growth, top-10 holder share,
LP burned / locked, DexScreener boosts and trending rank, GeckoTerminal trending rank, CoinGecko trending, social
mentions.  Proposal (small dex.py change, no strategy change): in DexHunter._enqueue / the screen, append one line per
candidate snapshot to data/dex_snapshots.csv: t, chain, addr, pair, sym, src, rank_in_list, age_h, liq, vol1, vol6,
vol24, fdv, b1, s1, b24, s24, h1, h6, h24, boosts, holders (GoPlus / RugCheck if fetched), top10_pct, lp_locked, and
the study's score.  After 2-4 weeks this study can join those rows with GeckoTerminal OHLCV outcomes and measure the
lift of buyer growth / holder growth / boosts / trending rank exactly like section 4 above.""")

    # 10. plain-English summary ------------------------------------------------------------------------------------
    banner("10. SUMMARY IN PLAIN WORDS")
    b2, b5, b10, brug = (rate([p[k] for p in pts]) for k in ("run2", "run5", "run10", "rug7"))
    nets_txt = ", ".join(f"{sum(P.p['net'] == n for P in pools)} {n}" for n in NETS)
    lines = [f"Sample: {len(pools)} pools ({nets_txt}), {len(pts)} decision "
             f"points between {ts(T0)[:10]} and {ts(pts[-1]['t'])[:10]}. At a random moment, {b2:.1%} of the time a coin doubled within "
             f"7 days, {b5:.1%} went 5x, {b10:.1%} went 10x, and {brug:.1%} rugged (the rug share is a floor: pools that died before we "
             f"listed them are missing)."]
    r10 = [p for p in pts if p["run10"]]
    dud = [p for p in pts if p["dud"]]
    if r10 and dud:
        lines.append(f"Before a 10x+ run the coin typically looked like this (medians of the 10x group vs the duds): age {med([p['age_h'] for p in r10]):.0f}h vs "
                     f"{med([p['age_h'] for p in dud]):.0f}h, liquidity {fmt(med([p['liq'] for p in r10]), '$')} vs {fmt(med([p['liq'] for p in dud]), '$')}, "
                     f"market cap {fmt(med([p['mcap'] for p in r10]), '$')} vs {fmt(med([p['mcap'] for p in dud]), '$')}, 24h volume / liquidity "
                     f"{fmt(med([p['vol24_liq'] for p in r10]))} vs {fmt(med([p['vol24_liq'] for p in dud]))}, last-hour volume vs its 24h average "
                     f"{fmt(med([p['v1_rel'] for p in r10]))}x vs {fmt(med([p['v1_rel'] for p in dud]))}x, 1h change {fmt(med([p['ch1'] for p in r10]), '%')} vs "
                     f"{fmt(med([p['ch1'] for p in dud]), '%')}, 24h change {fmt(med([p['ch24'] for p in r10]), '%')} vs {fmt(med([p['ch24'] for p in dud]), '%')}, "
                     f"distance from the 7-day high {fmt(med([p['dd7'] for p in r10]), '%')} vs {fmt(med([p['dd7'] for p in dud]), '%')}, pump.fun share "
                     f"{fmt(rate([p['pump'] for p in r10]), '%')} vs {fmt(rate([p['pump'] for p in dud]), '%')}.")
    cons = [f for f in FEATS if (lambda ao, an: (ao - 0.5) * (an - 0.5) > 0 and min(abs(ao - 0.5), abs(an - 0.5)) >= 0.03)(
        auc([p[f] if p[f] == p[f] else -1e18 for p in old], [p["run2"] for p in old]), auc([p[f] if p[f] == p[f] else -1e18 for p in new], [p["run2"] for p in new]))]
    lines.append(f"Signs that held up in BOTH halves of the window (single-feature AUC): {', '.join(cons) if cons else 'none - no single feature was stable'}.")
    if rules and s_star in levels:
        lo_, n_o_, hi_, n_n_ = levels[s_star]
        lines.append(f"The points score ({len(rules)} rules: " + "; ".join(f"{r['f']} {r['words']}" for r in rules) + f") at >= {s_star} points picked "
                     f"{n_n_} moments in the newer (unseen) half of which {fmt(hi_, '%')} doubled within 7 days, against a base rate of "
                     f"{rate([p['run2'] for p in new]):.1%} (older half, in-sample: {fmt(lo_, '%')}). {len(live_ok)} of the {len(rules)} rules can be "
                     f"computed live from DexScreener fields today.")
    if eng:
        lines.append(f"The engine's current entry (1h >= +{ENTRY.get('h1', 0.1):.0%}, age >= {SCREEN.get('min_age_h', 6)}h, liq >= "
                     f"${SCREEN.get('min_liq', 100000) // 1000}k, vol24 >= ${SCREEN.get('min_vol24', 100000) // 1000}k) fired {eng['per_day']:.2f} times/day in this "
                     f"sample, won {eng['win']:.0%}, median {pct(eng['med'], 1)}, mean {pct(eng['mean'], 1)} per trade, {eng['x2']:.0%} of trades "
                     f"closed >= 2x, rug rate {eng['rug']:.0%}; the 4-slot account made {pct(eng['pf_full']['monthly'], 1)}/month "
                     f"(older {pct(eng['pf_old']['monthly'], 1)}, newer {pct(eng['pf_new']['monthly'], 1)}, max drawdown {pct(eng['pf_full']['dd'], 1, 0)}).")
    if best:
        nm, s = best
        lines.append(f"Most robust entry (best of the worse half): '{nm}': {s['per_day']:.2f} trades/day in this sample ({s['n_n'] / max(1.0, (T1 - split) / DAY):.2f}/day "
                     f"in the newer half; the live scanner sees far more pools, so treat this as a floor), win {s['win']:.0%}, median {pct(s['med'], 1)}, "
                     f"mean {pct(s['mean'], 1)} (CI {pct(s['ci'][0], 1)}..{pct(s['ci'][1], 1)}), {s['x2']:.0%} of trades >= 2x, {s['x5']:.0%} >= 5x, rug "
                     f"{s['rug']:.0%}; account {pct(s['pf_full']['monthly'], 1)}/month, older {pct(s['pf_old']['monthly'], 1)}, NEWER (out-of-sample) "
                     f"{pct(s['pf_new']['monthly'], 1)}, max drawdown {pct(s['pf_full']['dd'], 1, 0)}.")
        if eng and s["pf_new"]["monthly"] > eng["pf_new"]["monthly"] and s["pf_old"]["monthly"] > eng["pf_old"]["monthly"] and nm != R[0][0]:
            lines.append(f"It beat the engine's entry in BOTH halves, so the recommended change is: " + (
                f"lower config.DEX['screen']['min_age_h'] to 1 " if "age>=1h" in nm else "keep the screen floors ") + (
                "and min_liq / min_vol24 to $50k, " if "$50k" in nm else "") + (
                f"add the points score (config block 'runner_score' above, require >= {s_star}) to dex.py's entry check " if "score" in nm else
                "add the logistic score (coefficients in section 6) to dex.py's entry check ") + (
                "and keep the 1h >= +10% momentum condition." if nm.startswith("engine") else "in place of the 1h >= +10% condition (the score already "
                "contains the momentum rules that matter)."))
        else:
            lines.append("It did NOT beat the engine's current entry in both halves, so do not change config.DEX yet; keep the exit as it is, "
                         "add the snapshot logging from section 9, and re-run this study (the registry grows every run, which removes the survivorship bias).")
    lines.append("Every number above comes from a few thousand pools chosen today; the ranking of signs is what to trust, the absolute "
                 "profit per month is not a forecast.")
    print("\n".join(lines))

    # points CSV for offline re-analysis ---------------------------------------------------------------------------
    try:
        os.makedirs(os.path.dirname(a.points_out) or ".", exist_ok=True)
        keep = pts if len(pts) <= a.max_csv else random.Random(3).sample(pts, a.max_csv)
        cols = ["k", "t", "c", "score", "q", "blind"] + FEATS + LABELS
        with gzip.open(a.points_out, "wt", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for p in sorted(keep, key=lambda p: p["t"]):
                w.writerow([p["k"], p["t"], f"{p['c']:.6g}", p["score"], f"{p['q']:.4f}", int(p["blind"])]
                           + [("" if p[c] != p[c] else f"{p[c]:.5g}") for c in FEATS + LABELS])
        print(f"\nwrote {len(keep)} labelled points to {a.points_out}")
    except Exception as e:
        print(f"\ncould not write points CSV: {e}")
    print(f"({time.time() - t_start:.0f}s)")


def P_net(p):
    return "solana" if p["sol"] else "base" if p["base"] else "eth"


if __name__ == "__main__":
    main()
