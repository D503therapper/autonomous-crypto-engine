"""Empirical study of ENTRY + EXIT rules for DEX meme-coin runners (dex.py / config.DEX["exit"]).

Question: dex.py sells half at 2x, laddering out at 5x/10x and riding a ~17% moonbag on a widening
trail (30% -> 40% at 3x -> 50% at 10x), with a break-even stop after the first sale and a 14-day limit
for trades that never doubled. Is that the best way to exit? And, for the owner's priority (fastest
gains, most profit per MONTH), do one-day pump entries on 15-min bars with short exits do better?

  1. pools     GeckoTerminal (free API, 2.1 s between calls, 429 -> backoff) for solana/base/eth:
               trending_pools (1h/6h/24h, several pages), new_pools, pools?sort=h24_volume_usd_desc.
               Pools are kept REGARDLESS of outcome. A registry (results/dex_exit_pools.json) keeps
               every pool seen by earlier runs, so new pools that later rugged are still studied
               (survivorship falls with every run). Majors/stables as base token are skipped.
  2. history   hourly OHLCV from pool creation (or --months back), paged with before_timestamp;
               15-min OHLCV for the first days after creation and around entries found later.
  3. entries   one per pool per variant; liquidity >= $250k estimated at entry (see LIMITS):
               slow24h  the engine's screen: pool >= 24h old, hourly close 1h >= +5%, 6h >= +10%,
                        24h volume >= $300k
               fast10 / fast20      any 15-min (or hourly) close: 1h >= +10% / +20% and last-hour
                        volume >= 3x the prior 24h hourly average, pool >= 24h old
               fast10_new / fast20_new   the same WITHOUT the 24h age filter (pool >= 2h old)
  4. costs     $500 position: 0.3% fee + 1% slippage + price impact (usd / liquidity) per side.
  5. rugs      close <= 10% of the max close of the prior 24h, or the series ends (> 72h without a
               trade before now) -> whatever is still held exits at -95%.
  6. exits     long family: the current ladder (from config.DEX), all at 2x, half at 2x + fixed or
               widening trail, trail-only 30/40/50%, ladder shapes x moonbag 10/20/30%, time 3/7/14d;
               short family (one-day pumps, 15-min bars): trail 10/15/20% x max hold 6/12/24/48h,
               with ladders 1.3x/1.5x/2x in thirds, all at 1.5x, half at 1.3x.
  7. report    per-trade stats (mean/median/win/CI/tails/top-5 share/regret) per rule, splits by
               network and liquidity bucket, walk-forward (older half -> newer half), and a 4-slot
               COMPOUNDING portfolio per entry x exit combo (time in trade counts: faster turnover
               wins) ranked by MONTHLY return; plain-English recommendation + config values.

LIMITS: GeckoTerminal has no liquidity history, so entry liquidity = the largest reserve ever seen
for the pool x sqrt(price_then / price_seen) (constant-product estimate; ignores LP adds/removals).
No buy/sell counts in OHLCV, so the engine's buys >= 1.2 x sells check and the scam screen are not
applied (rug rates here are higher than the screened engine should see). Sampled pools are a small
share of all DEX pools, so trades/month (and monthly return) are LOWER than a live scanner would see;
use them to rank rules, not as a forecast.

    python dex_exit_study.py                  # real run (GitHub Actions; ~60-100 min)
    python dex_exit_study.py --synthetic      # offline plumbing test (fake prices!)
"""
import argparse
import bisect
import json
import math
import os
import random
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

try:                                   # current engine settings (stdlib-only config file)
    import config
    DEXC = config.DEX
except Exception:                      # pragma: no cover - study still runs standalone
    DEXC = {}

HOUR, DAY, M15 = 3600, 86400, 900      # GeckoTerminal timestamps are in SECONDS
GT = "https://api.geckoterminal.com/api/v2"
NETS = ["solana", "base", "eth"]
SIZE = 500.0
FEE = DEXC.get("cost", {}).get("fee", 0.003)
SLIP = DEXC.get("cost", {}).get("slip", 0.01)
MIN_LIQ = DEXC.get("screen", {}).get("min_liq", 250_000)
MIN_VOL24 = DEXC.get("screen", {}).get("min_vol24", 300_000)
RUG_KEEP, RUG_LOSS, DEAD_H = 0.10, -0.95, 72   # rug: close <= 10% of 24h max; the rest exits at -95%
MAJORS = {"SOL", "WSOL", "ETH", "WETH", "USDC", "USDT", "DAI", "WBTC", "CBBTC", "CBETH", "WSTETH", "STETH", "USDS",
          "USDE", "PYUSD", "EURC", "JITOSOL", "MSOL", "BSOL", "JUPSOL", "USD1", "FDUSD", "TUSD", "BTC", "USDC.E",
          "USDBC", "SUSDE", "RETH", "EZETH", "WEETH", "LBTC", "TBTC", "FRAX", "LUSD", "GHO", "CRVUSD"}
BUCKETS = [(5e6, ">5M"), (1e6, "1M-5M"), (5e5, "500k-1M"), (0, "250k-500k")]
ENTRIES = ["slow24h", "fast10", "fast20", "fast10_new", "fast20_new"]
SLOTS = 4


# ----------------------------------------------------------------------------- exit rules
def R(name, fam, tps=(), trail=None, steps=(), be=False, soft_h=None, hard_h=None):
    """tps: [(price multiple, fraction of the ORIGINAL position)]; trail: stop % below the peak (also
    the initial stop below entry); steps: [(peak multiple, wider trail)]; be: stop >= break-even after
    the first sale; soft_h: time limit only while no profit was taken and peak < 2x (engine rule);
    hard_h: unconditional time exit."""
    return {"name": name, "fam": fam, "tps": list(tps), "trail": trail, "steps": list(steps), "be": be,
            "soft_h": soft_h, "hard_h": hard_h}


def engine_rule():
    """config.DEX['exit'] -> rule (tp1 + ladder fractions are of the REMAINING position)."""
    X = DEXC.get("exit") or {"trail": 0.30, "tp1": (1.0, 0.5), "ladder": [(4.0, 1 / 3), (9.0, 0.5)],
                            "trail_steps": [(3.0, 0.40), (10.0, 0.50)], "max_hold_days": 14}
    left, tps = 1.0, []
    for gain, frac in [tuple(X["tp1"])] + [tuple(x) for x in X.get("ladder", [])]:
        tps.append((1 + gain, left * frac))
        left -= left * frac
    return R("current (config)", "long", tps, X["trail"], X.get("trail_steps", []), True, X["max_hold_days"] * 24)


WIDEN = [(3.0, 0.40), (10.0, 0.50)]
SHAPES = {"2x/3x/5x": [(2, 0.5), (3, 1 / 6), (5, 1 / 6)],          # half, a third of the rest, half again
          "2x/5x/10x": [(2, 1 / 3), (5, 1 / 3), (10, 1 / 3)],       # thirds
          "2x/10x": [(2, 0.5), (10, 0.5)]}


def build_rules():
    rs = [engine_rule(),
          R("all@2x trail30", "long", [(2, 1.0)], 0.30, soft_h=336),
          R("half@2x trail30", "long", [(2, 0.5)], 0.30, be=True, soft_h=336),
          R("half@2x widen", "long", [(2, 0.5)], 0.30, WIDEN, True, 336)]
    rs += [R(f"trail{int(t * 100)} only", "long", trail=t, soft_h=336) for t in (0.30, 0.40, 0.50)]
    rs.append(R("widen only", "long", trail=0.30, steps=WIDEN, soft_h=336))
    for sh, tps in SHAPES.items():                  # rescale the shape so the moonbag is exactly m
        s = sum(f for _, f in tps)
        for m in (0.10, 0.20, 0.30):
            rs.append(R(f"L{sh} moon{int(m * 100)}", "long", [(x, f * (1 - m) / s) for x, f in tps], 0.30, WIDEN, True, 336))
    rs += [R(f"time {d}d", "long", hard_h=d * 24) for d in (3, 7, 14)]
    for t in (0.10, 0.15, 0.20):                    # one-day pump family (15-min bars where available)
        for h in (6, 12, 24, 48):
            k = f"t{int(t * 100)} {h}h"
            rs += [R(f"trail {k}", "short", trail=t, hard_h=h),
                   R(f"1.3/1.5/2x {k}", "short", [(1.3, 1 / 3), (1.5, 1 / 3), (2.0, 1 / 3)], t, be=True, hard_h=h),
                   R(f"all@1.5x {k}", "short", [(1.5, 1.0)], t, hard_h=h),
                   R(f"half@1.3x {k}", "short", [(1.3, 0.5)], t, be=True, hard_h=h)]
    return rs


def engine_config(rule):
    """Rule -> (config.DEX['exit'] values, notes). Ladder fractions go back to 'of the remaining'."""
    left, steps, notes = 1.0, [], []
    for x, f in rule["tps"]:
        steps.append((round(x - 1, 3), round(min(1.0, f / left), 4)))
        left -= f
    hold = rule["hard_h"] or rule["soft_h"] or 336
    out = {"trail": rule["trail"] or 0.95, "tp1": steps[0] if steps else (999.0, 0.0), "ladder": steps[1:],
           "trail_steps": rule["steps"], "max_hold_days": round(hold / 24, 2)}
    if not rule["trail"]:
        notes.append("trail 0.95 = practically no stop (the engine needs a number)")
    if not steps:
        notes.append("tp1 999x = never; the engine then applies max_hold_days to EVERY trade")
    elif rule["hard_h"]:
        out["max_hold_hours"] = rule["hard_h"]
        notes.append("max_hold_hours is a NEW key: a hard time exit even after tp1 (engine change needed)")
    return out, notes


def engine_ready(rule):
    """Expressible with today's dex.py (no code change)."""
    return bool(rule["trail"]) and not (rule["tps"] and rule["hard_h"])


# ----------------------------------------------------------------------------- HTTP
class GTClient:
    """GeckoTerminal public API, >= gap seconds between calls (~28/min), 429/5xx -> backoff."""

    def __init__(self, gap=2.1):
        self.gap, self.last, self.calls, self.fails, self.r429 = gap, 0.0, 0, 0, 0

    def get(self, path, **q):
        url = GT + path + ("?" + urllib.parse.urlencode(q) if q else "")
        for attempt in range(5):
            wait = self.last + self.gap - time.time()
            if wait > 0:
                time.sleep(wait)
            self.last, self.calls = time.time(), self.calls + 1
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "paper-trader-study/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    return json.loads(r.read().decode("utf-8", "replace"))
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    self.r429 += e.code == 429
                    time.sleep(min(120, 10 * 2 ** attempt))
                    continue
                break                                      # 400/404: pool unknown / bad params
            except Exception:
                time.sleep(5)
        self.fails += 1
        return None


def fnum(x):
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def iso_s(s):
    try:
        return int(datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def parse_pools(body, net, src, now):
    out = []
    for p in (body or {}).get("data") or []:
        a = p.get("attributes") or {} if isinstance(p, dict) else {}
        tid = str((((p.get("relationships") or {}).get("base_token") or {}).get("data") or {}).get("id", ""))
        created = iso_s(a.get("pool_created_at"))
        if not a.get("address") or not created or "_" not in tid:
            continue
        out.append({"net": net, "pool": a["address"], "token": tid.split("_", 1)[1], "created": created,
                    "sym": str(a.get("name") or "?").split("/")[0].strip().upper()[:14],
                    "reserve": fnum(a.get("reserve_in_usd")) or 0.0, "price": fnum(a.get("base_token_price_usd")),
                    "seen": now, "src": src})
    return out


def ohlcv(body):
    """-> [[t, o, h, l, c, v_usd]] oldest first (GeckoTerminal returns newest first)."""
    rows = ((((body or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list")) or []
    out = [[int(r[0])] + [float(x) for x in r[1:6]] for r in rows if len(r) >= 6 and all(x is not None for x in r[:6])]
    return sorted(b for b in out if min(b[1:5]) > 0)


def clean(bars):
    """Bad ticks: a close > 10x (or < 1/10) BOTH neighbours is a one-bar glitch -> flattened; wicks
    are clipped to 1.5x beyond the candle body (thin pools print unfillable single-trade wicks)."""
    for i in range(1, len(bars) - 1):
        a, b, c = bars[i - 1][4], bars[i][4], bars[i + 1][4]
        if b > 10 * max(a, c) or b * 10 < min(a, c):
            bars[i][1:5] = [a, a, a, a]
    for x in bars:
        x[2] = min(x[2], 1.5 * max(x[1], x[4]))
        x[3] = max(x[3], min(x[1], x[4]) / 1.5)
    return bars


# ----------------------------------------------------------------------------- data collection
def discover(cl, now, pages):
    rows = []
    for net in NETS:
        qs = [(f"/networks/{net}/trending_pools", {"duration": d, "page": p}, f"trending_{d}")
              for d in ("1h", "6h", "24h") for p in range(1, pages + 1)]
        qs += [(f"/networks/{net}/new_pools", {"page": p}, "new") for p in range(1, pages + 1)]
        qs += [(f"/networks/{net}/pools", {"sort": "h24_volume_usd_desc", "page": p}, "top_volume")
               for p in range(1, 2 * pages + 1)]
        for path, q, src in qs:
            rows += parse_pools(cl.get(path, **q), net, src, now)
    return rows


def merge(reg, rows):
    """One pool per token (the one with the largest reserve seen); keep the reference sighting
    (largest reserve and the price at that moment) for the liquidity estimate."""
    for r in rows:
        if r["sym"] in MAJORS or r["sym"].lstrip("$") in MAJORS:
            continue
        k = f"{r['net']}:{r['token']}"
        e = reg.get(k)
        if e is None:
            reg[k] = e = dict(r, srcs=[], ref_reserve=r["reserve"], ref_price=r["price"])
        if r["src"] not in e["srcs"]:
            e["srcs"].append(r["src"])
        if r["reserve"] > e["ref_reserve"] and r["price"]:
            e.update(pool=r["pool"], created=r["created"], ref_reserve=r["reserve"], ref_price=r["price"])
    return reg


def load_registry(path):
    try:
        with open(path) as f:
            return {f"{e['net']}:{e['token']}": e for e in json.load(f)}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def save_registry(path, reg, cap=6000):
    keep = sorted(reg.values(), key=lambda e: -e["seen"])[:cap]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(keep, f, separators=(",", ":"))


def fetch_series(cl, p, tf, agg, start, end, max_pages):
    """Bars in [start, end), paging FORWARD (each call returns up to 1000 bars before before_timestamp).
    -> (bars, reached_end)."""
    bars, span, before = {}, 1000 * agg * (HOUR if tf == "hour" else 60), start
    for _ in range(max_pages):
        if before >= end:
            break
        before = min(end, before + span)
        body = cl.get(f"/networks/{p['net']}/pools/{p['pool']}/ohlcv/{tf}", aggregate=agg, limit=1000,
                      before_timestamp=int(before), currency="usd", token="base")
        for b in ohlcv(body):
            if start <= b[0] < end:
                bars[b[0]] = b
    return [bars[t] for t in sorted(bars)], before >= end


def merge_bars(hourly, fine):
    """15-min bars where we have them, hourly bars elsewhere -> [t, o, h, l, c, v, dur]."""
    segs, out = [], [b + [M15] for b in fine]
    for b in fine:                                     # contiguous-ish 15m coverage ranges
        if segs and b[0] <= segs[-1][1] + 6 * HOUR:
            segs[-1][1] = b[0] + M15
        else:
            segs.append([b[0], b[0] + M15])
    out += [b + [HOUR] for b in hourly if not any(s <= b[0] < e or s < b[0] + HOUR <= e for s, e in segs)]
    return clean(sorted(out)), segs


class Series:
    """Time-indexed view of the merged bars: close-at-time and volume-in-window lookups."""

    def __init__(self, bars):
        self.b = bars
        self.tc = [b[0] + b[6] for b in bars]          # close times
        self.cv = [0.0]
        for b in bars:
            self.cv.append(self.cv[-1] + b[5])

    def close_at(self, t):                             # last close at or before t
        i = bisect.bisect_right(self.tc, t) - 1
        return self.b[i][4] if i >= 0 else None

    def vol(self, a, b):                               # volume of bars closing in (a, b]
        return self.cv[bisect.bisect_right(self.tc, b)] - self.cv[bisect.bisect_right(self.tc, a)]


def liq_at(p, price):
    """Constant-product estimate: pool USD depth ~ sqrt(price); anchored on the biggest sighting."""
    if not p.get("ref_price"):
        return p["ref_reserve"]
    return p["ref_reserve"] * min(100.0, max(0.01, math.sqrt(price / p["ref_price"])))


def find_entries(p, S, ws):
    """First qualifying bar close per entry variant -> {variant: (bar index, close time, price, liq)}."""
    out = {}
    for k, b in enumerate(S.b):
        tc, c = S.tc[k], b[4]
        age = tc - p["created"]
        if tc < ws + 2 * HOUR or age < 2 * HOUR:
            continue
        c1 = S.close_at(tc - HOUR)
        if not c1:
            continue
        h1 = c / c1 - 1
        if h1 < 0.05:
            continue
        liq = liq_at(p, c)
        if liq < MIN_LIQ:
            continue
        if "slow24h" not in out and tc % HOUR == 0 and age >= 24 * HOUR:
            c6 = S.close_at(tc - 6 * HOUR)
            if c6 and c / c6 - 1 >= 0.10 and S.vol(tc - DAY, tc) >= MIN_VOL24:
                out["slow24h"] = (k, tc, c, liq)
        if h1 >= 0.10:
            lo = max(p["created"], tc - 25 * HOUR)
            prior = S.vol(lo, tc - HOUR) / max(1.0, (tc - HOUR - lo) / HOUR)
            if prior > 0 and S.vol(tc - HOUR, tc) >= 3 * prior:
                for x in (10, 20):
                    if h1 >= x / 100:
                        for v, ok in ((f"fast{x}", age >= 24 * HOUR), (f"fast{x}_new", True)):
                            if ok and v not in out:
                                out[v] = (k, tc, c, liq)
        if len(out) == len(ENTRIES):
            break
    return out


def make_trade(p, S, var, ent, now, horizon_d, last_close):
    """Path after entry, rug point (close <= 10% of the prior-24h max close, or series ends), peaks."""
    k, t0, e, liq = ent
    t_end = min(now, t0 + horizon_d * DAY)
    path = [b for b in S.b[k + 1:] if b[0] < t_end]
    rug_j, dead = None, False
    for j, b in enumerate(path):
        tc = b[0] + b[6]
        i0 = bisect.bisect_left(S.tc, tc - DAY)
        i1 = bisect.bisect_left(S.tc, tc)
        ref = max((x[4] for x in S.b[i0:i1]), default=b[4])
        if b[4] <= RUG_KEEP * ref:                    # crash; a rug only if it never gets back to 30% within 24h
            k2 = bisect.bisect_right(S.tc, tc + DAY)
            if max((x[4] for x in S.b[i1 + 1:k2]), default=0) < 0.3 * ref:
                rug_j = j
                break
    if rug_j is None and now - last_close > DEAD_H * HOUR and last_close < t_end:
        rug_j, dead = len(path), True                  # no trades for > 72h before now: pool is gone
    live = path[:rug_j] if rug_j is not None else path
    peak = max([b[2] for b in live] + [e])
    t10 = next((b[0] for b in live if b[2] >= 10 * e), None)
    t_peak = next((b[0] for b in live if b[2] >= peak), t0)
    rug_t = (path[rug_j][0] + path[rug_j][6] if rug_j < len(path) else last_close) if rug_j is not None else None
    return {"var": var, "net": p["net"], "sym": p["sym"], "pool": p["pool"], "t0": t0, "e": e, "liq": liq,
            "bucket": next(n for lo, n in BUCKETS if liq >= lo), "path": live, "rug": rug_t, "dead": dead,
            "t_end": t_end, "peak": peak / e, "t10": t10, "tpeak_h": (t_peak - t0) / HOUR,
            "fine": bool(live) and live[0][6] == M15, "age_h": (t0 - p["created"]) / HOUR}


# ----------------------------------------------------------------------------- simulation
def cost(usd, liq):
    return min(1.0, FEE + SLIP + (usd / liq if liq > 0 else 1.0))


def simulate(tr, r):
    """One rule on one trade -> (return, exit time, peak multiple while held, still open?)."""
    e, liq0, t0 = tr["e"], tr["liq"], tr["t0"]
    q0 = q = SIZE * (1 - cost(SIZE, liq0)) / e
    cash, peak, held, n, took = 0.0, e, e, 0, False
    stop = e * (1 - r["trail"]) if r["trail"] else 0.0
    tps = r["tps"]

    def sell(qty, px):
        nonlocal q, cash
        qty = min(q, qty)
        usd = qty * px
        cash += usd * (1 - cost(usd, liq0 * math.sqrt(px / e)))
        q -= qty

    for t, o, h, l, c, v, dur in tr["path"]:
        if r["hard_h"] and t >= t0 + r["hard_h"] * HOUR or \
                r["soft_h"] and not took and peak < 2 * e and t >= t0 + r["soft_h"] * HOUR:
            sell(q, o)
            return cash / SIZE - 1, t, held / e, False
        held = max(held, h)
        if stop and l <= stop:                          # stop first (conservative), gaps fill at the open
            sell(q, min(o, stop))
            return cash / SIZE - 1, t + dur, held / e, False
        while n < len(tps) and h >= e * tps[n][0]:
            sell(tps[n][1] * q0, max(o, e * tps[n][0]))
            n, took = n + 1, True
            if r["be"]:
                stop = max(stop, e * (1 + SLIP + 2 * FEE))
        if q <= 1e-9 * q0:
            return cash / SIZE - 1, t + dur, held / e, False
        peak = max(peak, h)
        if r["trail"]:
            tr_ = r["trail"]
            for mult, w in r["steps"]:
                if peak >= e * mult:
                    tr_ = w
            stop = max(stop, peak * (1 - tr_))
    if tr["rug"] is not None:                          # rugged / dead: the rest is worth -95%
        return (cash + q * e * (1 + RUG_LOSS)) / SIZE - 1, tr["rug"], held / e, False
    last = tr["path"][-1][4] if tr["path"] else e
    return (cash + q * last * (1 - cost(q * last, liq0 * math.sqrt(last / e)))) / SIZE - 1, tr["t_end"], held / e, q > 0


# ----------------------------------------------------------------------------- statistics
def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def boot_ci(xs, n=2000, seed=1):
    if len(xs) < 3:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    ms = sorted(mean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return ms[int(0.025 * n)], ms[int(0.975 * n) - 1]


def stats(trades, res):
    xs = [x[0] for x in res]
    if not xs:
        return None
    tot, top5 = sum(xs), sorted(xs, reverse=True)[:5]
    gb = [(pk - 1 - x) / (pk - 1) for x, _, pk, _ in res if pk >= 1.5]
    hit10 = [(tr, x) for tr, x in zip(trades, res) if tr["t10"] is not None]
    rest = sorted(xs)[:-5]
    return {"n": len(xs), "mean": mean(xs), "med": statistics.median(xs), "win": mean([x > 0 for x in xs]),
            "ci": boot_ci(xs), "top5": sum(top5) / tot if tot > 0 else float("nan"), "ex5": mean(rest),
            "r": [mean([x >= m - 1 for x in xs]) for m in (2, 5, 10, 100)],
            "pk": [mean([x[2] >= m for x in res]) for m in (2, 5, 10, 100)],
            "gb": mean(gb), "miss10": (sum(1 for tr, x in hit10 if x[1] < tr["t10"]), len(hit10)),
            "open": mean([x[3] for x in res]), "hold": mean([(x[1] - tr["t0"]) / HOUR for tr, x in zip(trades, res)])}


def portfolio(trades, res, t_from, t_to, slots=SLOTS):
    """4 slots, each new trade gets 1/4 of equity (at cost) if a slot and cash are free; proceeds
    come back at the final exit. Compounding. -> monthly return, max drawdown, taken, skipped."""
    ev = sorted((tr["t0"], x[1], x[0]) for tr, x in zip(trades, res) if t_from <= tr["t0"] < t_to)
    cash, opn, taken, skipped, peak, dd = 1.0, [], 0, 0, 1.0, 0.0
    for t0, t1, r in ev:
        for o in [o for o in opn if o[0] <= t0]:
            cash += o[1] * (1 + o[2])
            opn.remove(o)
        eq = cash + sum(o[1] for o in opn)
        peak, dd = max(peak, eq), min(dd, eq / peak - 1)
        if len(opn) < slots and cash > 1e-9:
            size = min(cash, eq / slots)
            cash -= size
            opn.append((max(t1, t0), size, r))
            taken += 1
        else:
            skipped += 1
    cash += sum(o[1] * (1 + o[2]) for o in opn)
    dd = min(dd, cash / peak - 1)
    months = max(0.5, (t_to - t_from) / (30.44 * DAY))
    return {"monthly": max(cash, 1e-9) ** (1 / months) - 1, "final": cash, "dd": dd, "taken": taken,
            "skipped": skipped, "tpm": taken / months}


def pct(x, w=6, d=1):
    return f"{x * 100:+{w - 1}.{d}f}%" if x == x else f"{'n/a':>{w}}"


def share(x):
    return f"{x:>5.0%}" if x == x else "  n/a"


def ts(s):
    return datetime.fromtimestamp(s, timezone.utc).strftime("%Y-%m-%d %H:%M")


def banner(t):
    print("\n" + "=" * 118 + "\n" + t + "\n" + "=" * 118)


def rule_tables(trades, rules, results, title):
    banner(title + "\n(top5 = share of total profit from the 5 best trades; > 100% means the others lost money in sum)")
    print(f"{'rule':<26} {'n':>4} {'mean':>7} {'95% CI of mean':>17} {'median':>7} {'win':>5} {'top5':>5} "
          f"{'ex-top5':>7} {'hold h':>6} {'open':>4} | realized >=2x/5x/10x/100x | held peak >=2x/5x/10x/100x")
    S = {}
    for r in rules:
        s = S[r["name"]] = stats(trades, results[r["name"]])
        if not s:
            continue
        print(f"{r['name']:<26} {s['n']:>4} {pct(s['mean'], 7)} [{pct(s['ci'][0])}, {pct(s['ci'][1])}] {pct(s['med'], 7)} "
              f"{s['win']:>5.0%} {share(s['top5'])} {pct(s['ex5'], 7)} {s['hold']:>6.0f} {s['open']:>4.0%} | "
              + " ".join(f"{x:>5.1%}" for x in s["r"]) + " | " + " ".join(f"{x:>5.1%}" for x in s["pk"]))
    print(f"\nREGRET  {'rule':<26} {'gave back of peak gain (trades peaking >= 1.5x)':>48} {'fully out before a later 10x':>30}")
    for r in rules:
        s = S[r["name"]]
        if s:
            m, n = s["miss10"]
            print(f"        {r['name']:<26} {pct(s['gb'], 48, 0)} {f'{m}/{n}' + (f' ({m / n:.0%})' if n else ''):>30}")
    return S


# ----------------------------------------------------------------------------- synthetic
class SyntheticGT:
    """Fake GeckoTerminal: pools with fat-tailed 15-min paths - chop, pump-and-fade, rare 3x-200x
    runners, rugs (-98% then the series stops) and dead pools. ONLY tests the plumbing."""

    def __init__(self, seed=7, per_net=110):
        self.rng, self.now, self.calls, self.fails, self.r429 = random.Random(seed), 1_780_000_000 // HOUR * HOUR, 0, 0, 0
        self.pools = {}
        for net in NETS:
            for i in range(per_net):
                rng = self.rng
                kind = rng.choices(["runner", "pumpfade", "rug", "dead", "chop"], [12, 35, 15, 8, 30])[0]
                p = {"net": net, "addr": f"{net[:3]}pool{i}", "tok": f"{net[:3]}tok{i}", "sym": f"M{net[:1].upper()}{i}",
                     "kind": kind, "created": self.now - rng.randint(1, 100 * 24) * HOUR - rng.choice([0, 900, 1800]),
                     "L0": math.exp(rng.uniform(math.log(8e4), math.log(6e6))), "p0": math.exp(rng.uniform(-12, 0))}
                self.pools[p["addr"]] = p
        self.cache = {}

    def bars(self, p):
        if p["addr"] in self.cache:
            return self.cache[p["addr"]]
        rng = random.Random(p["addr"])
        n = (self.now - p["created"]) // M15
        segs, end = [], n
        a = rng.randint(4, min(n, 1600)) if n > 8 else 0
        if p["kind"] == "runner":
            d = rng.randint(16, 800)
            segs = [(a, a + d, rng.uniform(math.log(3), math.log(200)) / d), (a + d, n, -0.001)]
        elif p["kind"] == "pumpfade":
            d, f = rng.randint(4, 48), rng.randint(192, 800)
            segs = [(a, a + d, math.log(rng.uniform(1.3, 3.0)) / d), (a + d, a + d + f, math.log(rng.uniform(0.2, 0.6)) / f)]
        elif p["kind"] in ("rug", "dead"):
            end = min(n, rng.randint(12, 2000))
        else:
            segs = [(0, n, -0.0003)]
        sig, px, out = rng.uniform(0.012, 0.04), p["p0"], []
        base = p["L0"] / 40
        for i in range(end):
            r = sum(dr for s, e_, dr in segs if s <= i < e_) + rng.gauss(0, sig)
            if rng.random() < 0.01:
                r += rng.choice((-1, 1)) * rng.uniform(0.05, 0.3)            # fat tail jumps
            if p["kind"] == "rug" and i == end - 4:
                r = math.log(0.02)
            o, px = px, px * math.exp(r)
            h, l = max(o, px) * math.exp(abs(rng.gauss(0, sig / 2))), min(o, px) * math.exp(-abs(rng.gauss(0, sig / 2)))
            out.append([p["created"] + i * M15, o, h, l, px, base * math.exp(rng.gauss(0, 0.7)) * (1 + 30 * abs(r))])
        self.cache[p["addr"]] = out
        return out

    def _pool_json(self, p, reserve, price):
        return {"id": f"{p['net']}_{p['addr']}", "attributes": {
            "address": p["addr"], "name": f"{p['sym']} / SOL", "reserve_in_usd": str(reserve),
            "base_token_price_usd": str(price), "pool_created_at": datetime.fromtimestamp(p["created"], timezone.utc).isoformat()},
            "relationships": {"base_token": {"data": {"id": f"{p['net']}_{p['tok']}"}}}}

    def now_json(self, p):
        b = self.bars(p)
        px = b[-1][4] if b else p["p0"]
        dead = p["kind"] in ("rug", "dead")
        return self._pool_json(p, 300.0 if dead else p["L0"] * math.sqrt(px / p["p0"]), px)

    def seed_registry(self):
        """Earlier runs' sightings (pre-rug reserve) for rugs and half the rest - mimics the registry."""
        rows = []
        for p in self.pools.values():
            if p["kind"] in ("rug", "dead") or self.rng.random() < 0.5:
                rows += parse_pools({"data": [self._pool_json(p, p["L0"], p["p0"])]}, p["net"], "registry", p["created"] + HOUR)
        return rows

    def get(self, path, **q):
        self.calls += 1
        parts = path.strip("/").split("/")
        net = parts[1]
        pools = [p for p in self.pools.values() if p["net"] == net]
        if parts[-1] in ("trending_pools", "new_pools", "pools"):
            alive = [p for p in pools if p["kind"] not in ("rug", "dead")]
            key = {"new_pools": lambda p: -p["created"], "pools": lambda p: -p["L0"]}.get(parts[-1], lambda p: random.Random(p["addr"] + str(q.get("duration"))).random())
            lst = sorted(pools if parts[-1] == "new_pools" else alive, key=key)
            pg = int(q.get("page", 1))
            return {"data": [self.now_json(p) for p in lst[(pg - 1) * 20: pg * 20]]}
        p, tf = self.pools.get(parts[3]), parts[5]
        if not p:
            return None
        step = M15 * int(q.get("aggregate", 1)) // 15 if tf == "minute" else HOUR
        src, g = self.bars(p), {}
        for b in src:
            g.setdefault(b[0] // step * step, []).append(b)
        rows = [[t, x[0][1], max(y[2] for y in x), min(y[3] for y in x), x[-1][4], sum(y[5] for y in x)] for t, x in g.items()
                if t < int(q["before_timestamp"])]
        rows = sorted(rows, reverse=True)[:int(q.get("limit", 100))]
        return {"data": {"attributes": {"ohlcv_list": rows}}}


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--max-pools", type=int, default=520)
    ap.add_argument("--pages", type=int, default=5, help="list pages per endpoint / duration")
    ap.add_argument("--months", type=float, default=6)
    ap.add_argument("--horizon-days", type=float, default=45)
    ap.add_argument("--hourly-pages", type=int, default=5)
    ap.add_argument("--budget-min", type=float, default=95, help="stop fetching new pools after this")
    ap.add_argument("--registry", default="results/dex_exit_pools.json")
    a = ap.parse_args()
    t_start = time.time()
    rules = build_rules()

    if a.synthetic:
        print("SYNTHETIC MODE: fake prices, only checks that the study runs end to end\n")
        cl = SyntheticGT()
        now, reg = cl.now, merge({}, cl.seed_registry())
    else:
        cl, now = GTClient(), int(time.time())
        reg = load_registry(a.registry)
    n_prev = len(reg)

    # 1. pools ------------------------------------------------------------------------------------
    banner("1. POOLS AND DATA")
    rows = discover(cl, now, a.pages)
    by_src = {}
    for r in rows:
        by_src[r["src"]] = by_src.get(r["src"], 0) + 1
    merge(reg, rows)
    if not a.synthetic:
        save_registry(a.registry, reg)
    print(f"listed now: {len(rows)} pool rows ({', '.join(f'{k} {v}' for k, v in sorted(by_src.items()))}); "
          f"registry {n_prev} -> {len(reg)} tokens (majors/stables skipped, one pool per token)")
    ws0 = now - int(a.months * 30.44 * DAY)
    cand = [p for p in reg.values() if p["created"] <= now - 3 * DAY and p["ref_reserve"] >= 25_000]
    young = sum(1 for p in reg.values() if p["created"] > now - 3 * DAY)
    rng = random.Random(42)
    rng.shuffle(cand)
    cand.sort(key=lambda p: "registry" not in p["srcs"] and "new" not in p["srcs"])   # outcome-blind pools first
    cand = cand[:a.max_pools]
    print(f"{len(cand)} pools to fetch ({young} too young (< 3 days), others below $25k reserve ever seen)")

    trades, why, fine_n = {v: [] for v in ENTRIES}, {"no data": 0, "no entry": 0, "budget": 0}, 0
    for n, p in enumerate(cand):
        if time.time() - t_start > a.budget_min * 60:
            why["budget"] += len(cand) - n
            break
        ws = max(p["created"], ws0)
        fine = fetch_series(cl, p, "minute", 15, p["created"], now, 1)[0] if p["created"] >= ws0 else []
        hourly, complete = fetch_series(cl, p, "hour", 1, ws, now, a.hourly_pages)
        if not hourly and not fine:
            why["no data"] += 1
            continue
        bars, segs = merge_bars(hourly, fine)
        S = Series(bars)
        ents = find_entries(p, S, ws)
        extra = sorted({e[1] for e in ents.values() if not any(s <= e[1] < x for s, x in segs)})
        if extra:                                          # 15-min bars after a later entry, too
            fine += fetch_series(cl, p, "minute", 15, extra[0] - 2 * HOUR, now, 1)[0]
            bars, segs = merge_bars(hourly, sorted({b[0]: b for b in fine}.values()))
            S = Series(bars)
            ents = find_entries(p, S, ws)
        fine_n += bool(fine)
        if not ents:
            why["no entry"] += 1
        last_close = S.tc[-1] if complete and S.tc else now      # history cut short -> cannot call it dead
        for v, ent in ents.items():
            if ent[1] <= now - 2 * DAY:                   # need some future to judge an exit
                trades[v].append(make_trade(p, S, v, ent, now, a.horizon_days, last_close))
        if n % 25 == 0:
            print(f"  fetched {n + 1}/{len(cand)}  calls {cl.calls}  entries " + " ".join(f"{v} {len(trades[v])}" for v in ENTRIES)
                  + f"  {time.time() - t_start:.0f}s")
    print(f"API calls {cl.calls} (429s {cl.r429}, failed {cl.fails}); pools with 15-min bars {fine_n}; skipped: "
          + ", ".join(f"{k} {v}" for k, v in why.items()))
    for v in ENTRIES:
        trades[v].sort(key=lambda t: t["t0"])
    alltr = [t for v in ENTRIES for t in trades[v]]
    if len(trades["slow24h"]) < 10 and len(alltr) < 30:
        print("\ntoo few entries to study - check API reachability / the pool sample above")
        return
    T0, T1 = min(t["t0"] for t in alltr), now
    split = sorted(t["t0"] for t in alltr)[len(alltr) // 2]
    print(f"entries {ts(T0)} .. {ts(max(t['t0'] for t in alltr))}; halves split at {ts(split)}")

    banner("2. ENTRY VARIANTS  (what the price did after entry, before any exit rule; peak within the horizon)")
    print(f"{'entry':<11} {'n':>4} {'sol/base/eth':>13} {'15m bars':>8} {'age h med':>9} {'rug 7d':>6} {'rug all':>7} "
          f"{'peak>=1.3x':>10} {'2x':>5} {'5x':>5} {'10x':>5} {'100x':>5} {'peak<24h':>8} {'med peak h':>10}")
    for v in ENTRIES:
        T = trades[v]
        if not T:
            print(f"{v:<11}    0")
            continue
        nets = "/".join(str(sum(t["net"] == x for t in T)) for x in NETS)
        print(f"{v:<11} {len(T):>4} {nets:>13} {mean([t['fine'] for t in T]):>8.0%} {statistics.median(t['age_h'] for t in T):>9.0f} "
              f"{mean([t['rug'] is not None and t['rug'] - t['t0'] <= 7 * DAY for t in T]):>6.0%} {mean([t['rug'] is not None for t in T]):>7.0%} "
              + " ".join(f"{mean([t['peak'] >= m for t in T]):>{w}.0%}" for m, w in ((1.3, 10), (2, 5), (5, 5), (10, 5), (100, 5)))
              + f" {mean([t['tpeak_h'] <= 24 for t in T]):>8.0%} {statistics.median(t['tpeak_h'] for t in T):>10.0f}")

    top = sorted(trades["slow24h"], key=lambda t: -t["peak"])[:8]
    if top:
        print("biggest runners after a slow24h entry: " + ", ".join(f"{t['sym']} ({t['net']}) {t['peak']:.1f}x" for t in top))

    # simulate every entry x rule -------------------------------------------------------------------
    res = {v: {r["name"]: [simulate(t, r) for t in trades[v]] for r in rules} for v in ENTRIES}
    rmap = {r["name"]: r for r in rules}
    cur = rules[0]["name"]

    # 3. per-trade tables ----------------------------------------------------------------------------
    long_rules = [r for r in rules if r["fam"] == "long"]
    S_slow = rule_tables(trades["slow24h"], long_rules, res["slow24h"],
                         "3. ENGINE ENTRY (slow24h) x LONG-HORIZON EXITS  (per trade, $500, net of costs)")
    best_fast = max((v for v in ENTRIES[1:] if trades[v]), key=lambda v: len(trades[v]), default=None)
    short_pick = [r for r in rules if r["fam"] == "short" and ("24h" in r["name"] or "t15" in r["name"])]
    rule_tables(trades["slow24h"], short_pick, res["slow24h"], "3b. ENGINE ENTRY (slow24h) x SHORT EXITS (subset: trail 15% or 24h hold)")
    if best_fast:
        rule_tables(trades[best_fast], [rules[0]] + short_pick, res[best_fast],
                    f"3c. FAST ENTRY ({best_fast}, most trades) x current + SHORT EXITS (subset)")

    # 4. monthly portfolio ranking over every entry x exit ---------------------------------------------
    banner(f"4. {SLOTS}-SLOT COMPOUNDING PORTFOLIO, EVERY ENTRY x EXIT  (1/{SLOTS} of equity per trade, busy slots skip signals;"
           f" older half < {ts(split)[:10]} <= newer half)")
    P = {}
    for v in ENTRIES:
        for r in rules:
            if len(trades[v]) < 6:
                continue
            x = res[v][r["name"]]
            full, old, new = (portfolio(trades[v], x, a_, b_) for a_, b_ in ((T0, T1), (T0, split), (split, T1)))
            n_old = sum(t["t0"] < split for t in trades[v])
            P[(v, r["name"])] = {"full": full, "old": old, "new": new, "robust": min(old["monthly"], new["monthly"]),
                                 "ok": n_old >= 5 and len(trades[v]) - n_old >= 5, "st": stats(trades[v], x)}
    ok = sorted((k for k in P if P[k]["ok"]), key=lambda k: -P[k]["robust"])
    print(f"{'entry':<11} {'exit rule':<26} {'monthly':>8} {'older':>7} {'newer':>7} {'maxDD':>6} {'trades/mo':>9} "
          f"{'skipped':>7} {'hold h':>6} {'mean/trade':>10} {'median':>7} {'win':>5}   (sorted by min(older, newer) monthly)")
    for k in ok[:30]:
        q = P[k]
        print(f"{k[0]:<11} {k[1]:<26} {pct(q['full']['monthly'], 8)} {pct(q['old']['monthly'], 7)} {pct(q['new']['monthly'], 7)} "
              f"{pct(q['full']['dd'], 6, 0)} {q['full']['tpm']:>9.1f} {q['full']['skipped']:>7} {q['st']['hold']:>6.0f} "
              f"{pct(q['st']['mean'], 10)} {pct(q['st']['med'], 7)} {q['st']['win']:>5.0%}")
    print("\nbest combo per entry (robust = min of halves) and the current exit on that entry:")
    for v in ENTRIES:
        ks = [k for k in ok if k[0] == v]
        if ks and (v, cur) in P:
            b, c = P[ks[0]], P[(v, cur)]
            print(f"  {v:<11} best {ks[0][1]:<24} monthly {pct(b['full']['monthly'])} (older {pct(b['old']['monthly'])}, newer "
                  f"{pct(b['new']['monthly'])})  | current exit: {pct(c['full']['monthly'])} (older {pct(c['old']['monthly'])}, newer {pct(c['new']['monthly'])})")

    # 5. splits ----------------------------------------------------------------------------------------
    key_rules = [cur] + [k[1] for k in ok if k[0] == "slow24h"][:5]
    key_rules += [n for n in ("all@2x trail30", "half@2x widen", "trail30 only", "time 7d") if n not in key_rules]
    for v in ["slow24h"] + ([best_fast] if best_fast else []):
        banner(f"5. SPLITS for entry {v}: mean return per trade (n)")
        T = trades[v]
        cols = [("net", x) for x in NETS] + [("bucket", b) for _, b in reversed(BUCKETS)]
        print(f"{'rule':<26} " + " ".join(f"{c[1]:>11}" for c in cols))
        print(f"{'(n)':<26} " + " ".join(f"{sum(t[c[0]] == c[1] for t in T):>11}" for c in cols))
        for name in dict.fromkeys(key_rules + ([k[1] for k in ok if k[0] == v][:3])):
            x = res[v][name]
            print(f"{name:<26} " + " ".join(f"{pct(mean([x[i][0] for i, t in enumerate(T) if t[c[0]] == c[1]]), 11)}" for c in cols))

    # 6. walk-forward ----------------------------------------------------------------------------------
    banner("6. WALK-FORWARD  (choose on the older half of entries, evaluate on the newer half)")
    T = trades["slow24h"]
    h = len(T) // 2
    if h >= 5:
        old = {r["name"]: mean([x[0] for x in res["slow24h"][r["name"]][:h]]) for r in rules}
        new = {r["name"]: mean([x[0] for x in res["slow24h"][r["name"]][h:]]) for r in rules}
        rk = {n: i + 1 for i, n in enumerate(sorted(new, key=lambda n: -new[n]))}
        pick = max(old, key=old.get)
        print(f"per trade, slow24h entry ({h} older / {len(T) - h} newer trades, split {ts(T[h]['t0'])}):")
        print(f"  best mean on older half: {pick} ({pct(old[pick])}) -> newer half {pct(new[pick])}, rank {rk[pick]}/{len(rk)}")
        print(f"  current rule:            older {pct(old[cur])} -> newer {pct(new[cur])}, rank {rk[cur]}/{len(rk)}")
        print(f"  top 5 on the newer half: " + ", ".join(f"{n} {pct(new[n])}" for n in sorted(new, key=lambda n: -new[n])[:5]))
    for label, score in (("best monthly on older half", lambda q: q["old"]["monthly"]),
                         ("most consistent on older half (min of its quarters)", None)):
        cands = [k for k in P if P[k]["ok"]]
        if not cands:
            break
        if score is None:
            q1 = sorted(t["t0"] for t in alltr if t["t0"] < split)
            mid = q1[len(q1) // 2] if q1 else split
            sc = {k: min(portfolio(trades[k[0]], res[k[0]][k[1]], T0, mid)["monthly"],
                         portfolio(trades[k[0]], res[k[0]][k[1]], mid, split)["monthly"]) for k in cands}
        else:
            sc = {k: score(P[k]) for k in cands}
        k = max(sc, key=sc.get)
        rank = sorted(cands, key=lambda c: -P[c]["new"]["monthly"]).index(k) + 1
        print(f"monthly portfolio, {label}: {k[0]} + {k[1]} (older {pct(P[k]['old']['monthly'])}) -> newer "
              f"{pct(P[k]['new']['monthly'])}/month, rank {rank}/{len(cands)} on the newer half")
    if ("slow24h", cur) in P:
        print(f"monthly portfolio, engine today (slow24h + current exit): older {pct(P[('slow24h', cur)]['old']['monthly'])} -> "
              f"newer {pct(P[('slow24h', cur)]['new']['monthly'])}/month")

    # 7. robust per-trade ranking for the engine entry + recommendation ---------------------------------
    banner("7. ROBUST RANKING, engine entry, long exits (average rank over: mean, median, CI low, mean ex-top-5, "
           "min of halves, worst network)")
    rows = []
    for r in long_rules:
        x = res["slow24h"][r["name"]]
        if not x:
            continue
        s = S_slow[r["name"]]
        halves = min(mean([y[0] for y in x[:h]]), mean([y[0] for y in x[h:]])) if h >= 5 else s["mean"]
        netm = [mean([y[0] for y, t in zip(x, T) if t["net"] == n]) for n in NETS if sum(t["net"] == n for t in T) >= 10]
        rows.append((r["name"], [s["mean"], s["med"], s["ci"][0], s["ex5"], halves, min(netm) if netm else s["mean"]]))
    if rows:
        ranks = {n: 0.0 for n, _ in rows}
        for i in range(6):
            for j, (n, _) in enumerate(sorted(rows, key=lambda z: -(z[1][i] if z[1][i] == z[1][i] else -9))):
                ranks[n] += (j + 1) / 6
        print(f"{'rule':<26} {'avg rank':>8} {'mean':>7} {'median':>7} {'CI low':>7} {'ex-top5':>7} {'min half':>8} {'worst net':>9}")
        for n, m in sorted(rows, key=lambda z: ranks[z[0]])[:12]:
            print(f"{n:<26} {ranks[n]:>8.1f} " + " ".join(pct(v_, 7) for v_ in m[:5]) + f" {pct(m[5], 9)}")
        robust = min(ranks, key=ranks.get)
        insample = max(rows, key=lambda z: z[1][0])[0]
        xr, xc = [y[0] for y in res["slow24h"][robust]], [y[0] for y in res["slow24h"][cur]]
        diff = [p_ - q_ for p_, q_ in zip(xr, xc)]
        dlo, dhi = boot_ci(diff)
        print(f"\npaired bootstrap, {robust} minus current: mean {pct(mean(diff))} per trade, 95% CI [{pct(dlo)}, {pct(dhi)}]")

        banner("8. RECOMMENDATION")
        kbest = ok[0] if ok else None
        sr, sc_ = S_slow[robust], S_slow[cur]
        sig = "clearly better than" if dlo > 0 else "clearly worse than" if dhi < 0 else "not statistically different from"
        txt = (f"On {len(T)} engine-style entries (slow24h) the current exit ({cur}) made {pct(sc_['mean'], 1)} per trade "
               f"(median {pct(sc_['med'], 1)}, win {sc_['win']:.0%}, CI [{pct(sc_['ci'][0], 1)}, {pct(sc_['ci'][1], 1)}]). "
               f"The best rule in-sample was '{insample}', but the most ROBUST long exit (good on mean, median, the worst "
               f"half, the worst network and without its 5 best trades) is '{robust}': {pct(sr['mean'], 1)} per trade "
               f"(median {pct(sr['med'], 1)}, CI [{pct(sr['ci'][0], 1)}, {pct(sr['ci'][1], 1)}]), gives back {pct(sr['gb'], 1, 0)} of "
               f"its peak gains and was fully out before {sr['miss10'][0]} of {sr['miss10'][1]} later 10x moves; it is {sig} "
               f"the current rule (paired difference {pct(mean(diff), 1)}, CI [{pct(dlo, 1)}, {pct(dhi, 1)}]). ")
        if dlo > 0:
            txt += "Switch config.DEX['exit'] to it. "
        else:
            txt += ("Because the difference is not proven, keep the current exit unless the robust rule also wins the "
                    "walk-forward above; in that case switching is low-risk. ")
        if kbest:
            q = P[kbest]
            txt += (f"For the owner's goal (most profit per MONTH with {SLOTS} slots and compounding), the most robust "
                    f"entry+exit combo is {kbest[0]} + '{kbest[1]}': {pct(q['full']['monthly'], 1)}/month overall, "
                    f"{pct(q['old']['monthly'], 1)} in the older half and {pct(q['new']['monthly'], 1)} in the newer half, "
                    f"{q['full']['tpm']:.1f} trades/month in this sample, average hold {q['st']['hold']:.0f}h, max drawdown "
                    f"{pct(q['full']['dd'], 1, 0)}. Rug rate for that entry: "
                    f"{mean([t['rug'] is not None for t in trades[kbest[0]]]):.0%} (the live scam screen should cut it). "
                    f"Trades/month here are a floor: the sample is a few hundred pools, the live scanner sees far more. "
                    f"Trust a switch only if the combo is positive in BOTH halves and the walk-forward pick did not collapse.")
        print(txt)
        ready = min((n for n in ranks if engine_ready(rmap[n])), key=ranks.get)
        if ready != robust:
            s_ = S_slow[ready]
            print(f"\nBest robust long exit that today's dex.py can run without a code change: '{ready}' "
                  f"({pct(s_['mean'], 1)} per trade, median {pct(s_['med'], 1)}, CI [{pct(s_['ci'][0], 1)}, {pct(s_['ci'][1], 1)}]).")
        shown = [("robust long exit", robust)] + ([("no-code-change exit", ready)] if ready != robust else [])
        shown += [(f"best monthly combo, entry {kbest[0]}", kbest[1])] if kbest else []
        for label, n in shown:
            cfg, notes = engine_config(rmap[n])
            print(f"\nconfig.DEX['exit'] for the {label} ('{n}'):\n  " + json.dumps(cfg) + "".join(f"\n  note: {x}" for x in notes))
        if kbest and kbest[0] != "slow24h":
            x = int(kbest[0][4:6])
            print("config.DEX['entry'] for that combo: " + json.dumps({"h1": x / 100, "vol_x_24h_avg": 3, "bars": "15m",
                  "min_age_h": 2 if kbest[0].endswith("_new") else 24}) + "\n  note: NEW keys - the engine checks 1h/6h change "
                  "and buys/sells today (screen.min_age_h would drop to 2 for a _new entry)")
    print(f"\n({time.time() - t_start:.0f}s)")


if __name__ == "__main__":
    main()
