"""Deep study of the "buy new Crypto.com listings" rule (config.EARLY_MOVER / strategy.EarlyMover).

pumps.py found 22 listings in ~5 months and +13.5%/trade at trail 35% / 72h hold. That sample is
small and the winning cell may be a spike. This script goes further back (as far as the public
API allows), uses 5m/15m bars for the first 72h after listing, and asks whether the rule is ROBUST:

  1. universe   every USD spot coin; a "listing" is a coin whose 1D history starts inside the lookback
                window and NOT at the API's own limit (many coins starting on the same first day).
  2. entries    first bar close (5m/15m/1h), delays of 1h/3h/6h/24h, "wait for a dip" (-10/-20/-30%
                from the first high, within 24h).
  3. exits      trailing stop 15/25/35/50%  x  max hold 24h/72h/7d/14d  x  ladder (none, or sell
                half at +100% / +50% and trail the rest).
  4. costs      0.8% per side (fees + wide spread), stress case 1.5%.
  5. robustness walk-forward (pick params on earlier listings, test on the next one, expanding),
                bootstrap CI of the mean, distribution / top-3 share, by month, by first-day
                volume, 5-slot portfolio drawdown, trail x hold sensitivity heatmap (plateau vs spike).
  6. output     most ROBUST config, expected return per trade with CI, trades/month, worst streak.

    python listings_study.py --months 18
    python listings_study.py --synthetic          # offline plumbing test (fake prices!)
"""
import argparse
import itertools
import math
import random
import statistics
import time
from datetime import datetime, timezone

MIN = 60_000
HOUR = 3_600_000
DAY = 86_400_000
TF_MS = {"1m": MIN, "5m": 5 * MIN, "15m": 15 * MIN, "1h": HOUR, "1D": DAY}

COST_BASE = 0.008          # per side: fees + wide spread on a brand-new coin
COST_STRESS = 0.015
FINE_HOURS = 72            # first 72h after listing on fine (5m/15m) bars, hourly afterwards
PATH_DAYS = 15             # hourly bars fetched after listing (covers the 14d max hold)
MIN_TRAIN = 8              # walk-forward: first test only after this many earlier listings

ENTRIES = ["first_bar", "close_15m", "close_1h", "delay_3h", "delay_6h", "delay_24h",
           "dip_10", "dip_20", "dip_30"]
TRAILS = [0.15, 0.25, 0.35, 0.50]
HOLDS_H = [24, 72, 168, 336]
LADDERS = [None, 1.0, 0.5]           # sell 50% at +100% / +50%, trail the rest
LIVE = ("close_1h", 0.35, 72, None)  # what config.EARLY_MOVER does today (buys within listing_hours)
SLOTS = 5


# ----------------------------------------------------------------------------- data


def fetch_range(client, coin, tf, start_ms, end_ms):
    """All candles with start_ms <= t < end_ms, oldest first (client pages backwards)."""
    step = TF_MS[tf]
    count = int((end_ms - start_ms) // step) + 2
    rows = client.candles(coin, timeframe=tf, count=count, end_ms=end_ms)
    return [r for r in rows if start_ms <= r["t"] < end_ms]


def discover_listings(client, months, now_ms, sleep=0.05):
    """Fetch 1D history for every coin; return (listings, stats). A coin whose 1D history is as
    long as we asked for, or starts on the same day as the earliest history seen for >= 4 coins
    (the API's lookback limit), is NOT a listing."""
    syms = client.list_spot_symbols()
    days = int(months * 30.5)
    print(f"{len(syms)} USD coins listed on Crypto.com; asking for {days} days of 1D history each")
    first = {}
    full = set()
    for n, s in enumerate(syms):
        try:
            cs = client.candles(s, timeframe="1D", count=days, end_ms=now_ms)
        except Exception as e:
            print(f"  skip {s}: {e}")
            continue
        cs = [c for c in cs if c["v"] > 0] or cs        # ignore empty placeholder days
        if not cs:
            continue
        first[s] = cs[0]["t"]
        if len(cs) >= days:
            full.add(s)
        time.sleep(sleep)
        if n % 50 == 0:
            print(f"  loaded {n}/{len(syms)}")
    if not first:
        return [], {"syms": len(syms), "limit_day": None, "at_limit": 0, "full": 0}
    # lookback limit: the earliest first-day among coins that are not simply "full"
    days_seen = {}
    for s, t in first.items():
        days_seen.setdefault(t // DAY, []).append(s)
    earliest = min(days_seen)
    at_limit = set()
    for d in (earliest, earliest + 1):
        if len(days_seen.get(d, [])) >= 4:            # a cluster = the API's lookback limit
            at_limit |= set(days_seen.get(d, []))
    cutoff = now_ms - PATH_DAYS * DAY
    listings = sorted((t, s) for s, t in first.items()
                      if s not in full and s not in at_limit and t <= cutoff)
    stats = {"syms": len(syms), "limit_day": earliest * DAY, "at_limit": len(at_limit),
             "full": len(full), "too_young": sum(1 for s, t in first.items()
                                                 if s not in full and s not in at_limit and t > cutoff)}
    return listings, stats


def load_paths(client, listings, now_ms, sleep=0.05):
    """For each listing: fine bars (5m -> 15m -> 1h) for the first 72h, hourly bars afterwards."""
    out = []
    for n, (day_t, s) in enumerate(listings):
        try:
            hourly = fetch_range(client, s, "1h", day_t - DAY, day_t + (PATH_DAYS + 2) * DAY)
            hourly = [c for c in hourly if c["v"] > 0]
            if len(hourly) < 24:
                # the API keeps less 1h than 1D history: fall back to daily bars (coarse: every
                # entry variant becomes "first daily close", stops fire on daily lows)
                daily = fetch_range(client, s, "1D", day_t - DAY, day_t + (PATH_DAYS + 2) * DAY)
                daily = [c for c in daily if c["v"] > 0]
                if len(daily) < 3:
                    print(f"  skip {s}: only {len(hourly)} hourly / {len(daily)} daily bars")
                    continue
                out.append(make_listing(s, daily[0]["t"], [dict(c, tf=DAY) for c in daily], "1D"))
                continue
            t0 = hourly[0]["t"]
            fine, tf_used = [], "1h"
            for tf in ("5m", "15m"):
                try:
                    cand = fetch_range(client, s, tf, t0 - HOUR, t0 + FINE_HOURS * HOUR)
                except Exception:
                    cand = []
                cand = [c for c in cand if c["v"] > 0]
                expect = FINE_HOURS * HOUR / TF_MS[tf]
                if len(cand) >= 0.5 * expect and cand[0]["t"] <= t0 + HOUR:
                    fine, tf_used = cand, tf
                    break
            if fine:
                t0 = min(t0, fine[0]["t"])
                last = fine[-1]["t"] + TF_MS[tf_used]
                bars = [dict(c, tf=TF_MS[tf_used]) for c in fine] + \
                       [dict(c, tf=HOUR) for c in hourly if c["t"] >= last]
            else:
                bars = [dict(c, tf=HOUR) for c in hourly]
            out.append(make_listing(s, t0, bars, tf_used))
        except Exception as e:
            print(f"  skip {s}: {e}")
        time.sleep(sleep)
        if n % 10 == 0:
            print(f"  paths {n}/{len(listings)}")
    return out


def make_listing(sym, t0, bars, tf_used):
    vol24 = sum(b["v"] * b["c"] for b in bars if b["t"] < t0 + DAY)
    hi72 = max(b["h"] for b in bars if b["t"] < t0 + FINE_HOURS * HOUR)
    return {"sym": sym, "t0": t0, "bars": bars, "tf": tf_used, "vol24": vol24,
            "month": datetime.fromtimestamp(t0 / 1000, timezone.utc).strftime("%Y-%m"),
            "first_close": bars[0]["c"], "hi72": hi72,
            "at_24h": close_at(bars, t0 + DAY), "at_72h": close_at(bars, t0 + 72 * HOUR)}


def close_at(bars, t):
    px = bars[0]["c"]
    for b in bars:
        if b["t"] + b["tf"] > t:
            break
        px = b["c"]
    return px


# ----------------------------------------------------------------------------- synthetic


class SyntheticListingClient:
    """Fake exchange with old coins (history hits the lookback limit) and new listings whose first
    days look like real ones: a spike, then either a slow bleed or an occasional multi-x run.
    ONLY for testing the plumbing - numbers from it say nothing about markets."""

    def __init__(self, seed=11, months=18, n_old=25, n_new=55):
        self.rng = random.Random(seed)
        self.now = int(time.time() * 1000) // HOUR * HOUR
        self.limit = self.now - int(months * 30.5) * DAY
        self.coins = {}
        for i in range(n_old):
            self.coins[f"OLD{i}"] = self.limit - self.rng.randint(0, 400) * DAY
        for i in range(n_new):
            self.coins[f"NEW{i}"] = self.limit + self.rng.randint(1, int(months * 30.5) - 1) * DAY \
                + self.rng.randint(0, 23) * HOUR + self.rng.choice([0, 5, 10, 30]) * MIN
        self.cache = {}

    def list_spot_symbols(self, quote="USD"):
        return sorted(self.coins)

    def _base(self, coin):
        """5-minute path for the first 20 days after the coin's own start (its listing)."""
        if coin in self.cache:
            return self.cache[coin]
        rng = random.Random(coin)
        t0 = self.coins[coin]
        price = rng.uniform(0.01, 20)
        kind = rng.random()
        n = 20 * DAY // TF_MS["5m"]
        rows = []
        for i in range(n):
            hrs = i * 5 / 60
            vol = 0.02 if hrs < 6 else 0.008 if hrs < 72 else 0.004
            drift = 0.0
            if hrs < 1:
                drift = 0.01 if kind < 0.6 else -0.01          # first-hour spike or dump
            elif hrs < 48:
                drift = -0.0015 if kind < 0.75 else 0.0012      # most bleed, a few run
            elif kind > 0.92 and hrs < 120:
                drift = 0.0015                                   # rare multi-x runner
            r = drift + rng.gauss(0, vol)
            o = price
            price = max(1e-6, price * math.exp(r))
            h = max(o, price) * (1 + abs(rng.gauss(0, vol / 2)))
            l = min(o, price) * (1 - abs(rng.gauss(0, vol / 2)))
            usd = rng.uniform(2e3, 3e4) * (20 if hrs < 24 else 1) * (0.2 + 5 * kind)
            rows.append({"t": t0 + i * TF_MS["5m"], "o": o, "h": h, "l": l, "c": price, "v": usd / price})
        self.cache[coin] = rows
        return rows

    def candles(self, coin, timeframe="1h", count=600, end_ms=None):
        end_ms = end_ms or self.now
        step = TF_MS[timeframe]
        t0 = self.coins[coin]
        if timeframe == "1D":
            rows = []
            rng = random.Random(coin + "D")
            px = 1.0
            d = max(t0 // DAY * DAY, self.limit // DAY * DAY)
            while d < end_ms:
                px *= math.exp(rng.gauss(0, 0.05))
                rows.append({"t": d, "o": px, "h": px * 1.03, "l": px * 0.97, "c": px, "v": 1000.0})
                d += DAY
            return rows[-count:]
        base = self._base(coin)
        if timeframe == "5m":
            rows = base
        else:
            groups = {}
            for x in base:                       # aggregate onto the timeframe grid
                groups.setdefault(x["t"] // step * step, []).append(x)
            rows = [{"t": t, "o": g[0]["o"], "h": max(x["h"] for x in g), "l": min(x["l"] for x in g),
                     "c": g[-1]["c"], "v": sum(x["v"] for x in g)} for t, g in sorted(groups.items())]
        rows = [r for r in rows if r["t"] < end_ms]
        return rows[-count:]


# ----------------------------------------------------------------------------- simulation


def entry_point(L, variant):
    """Return (bar index i, entry price, entry time) meaning: we hold from bar i+1 on; or None."""
    bars, t0 = L["bars"], L["t0"]
    if variant == "first_bar":
        b = bars[0]
        return 0, b["c"], b["t"] + b["tf"]
    if variant.startswith("close_") or variant.startswith("delay_"):
        d = {"close_15m": 15 * MIN, "close_1h": HOUR, "delay_3h": 3 * HOUR,
             "delay_6h": 6 * HOUR, "delay_24h": DAY}[variant]
        target = t0 + d
        i = 0
        for j, b in enumerate(bars):
            if b["t"] + b["tf"] <= target:
                i = j
            else:
                break
        b = bars[i]
        return i, b["c"], b["t"] + b["tf"]
    if variant.startswith("dip_"):
        x = int(variant[4:]) / 100
        hi = bars[0]["h"]
        for j in range(1, len(bars)):
            b = bars[j]
            if b["t"] >= t0 + DAY:
                return None
            level = hi * (1 - x)
            if b["l"] <= level:
                return j, min(level, b["o"]), b["t"] + b["tf"]
            hi = max(hi, b["h"])
        return None
    raise ValueError(variant)


def simulate(L, i, entry, entry_t, trail, hold_h, ladder, marks=False):
    """Walk bars after entry. Returns gross multiple (no costs), exit time, peak gain, and
    optionally hourly (t, multiple) marks for the portfolio simulation."""
    bars = L["bars"]
    peak, tp_done, sold = entry, False, 0.0        # sold = value already banked (per 1 unit)
    end_t = entry_t + hold_h * HOUR
    path = []
    last_t = entry_t
    for j in range(i + 1, len(bars)):
        b = bars[j]
        peak = max(peak, b["h"])
        stop = peak * (1 - trail)
        if b["l"] <= stop:
            px = min(stop, b["o"])
            mult = sold + (0.5 if tp_done else 1.0) * px / entry
            return _done(mult, b["t"] + b["tf"], peak / entry - 1, path, marks)
        if ladder and not tp_done and b["h"] >= entry * (1 + ladder):
            tp_done, sold = True, 0.5 * (1 + ladder)
        mult = sold + (0.5 if tp_done else 1.0) * b["c"] / entry
        if marks and b["t"] + b["tf"] - last_t >= HOUR:
            path.append((b["t"] + b["tf"], mult))
            last_t = b["t"] + b["tf"]
        if b["t"] + b["tf"] >= end_t:
            return _done(mult, b["t"] + b["tf"], peak / entry - 1, path, marks)
    b = bars[-1]
    mult = sold + (0.5 if tp_done else 1.0) * b["c"] / entry
    return _done(mult, b["t"] + b["tf"], peak / entry - 1, path, marks)


def _done(mult, t, peak_gain, path, marks):
    return {"mult": mult, "exit_t": t, "peak": peak_gain, "marks": path if marks else None}


def net(mult, cost):
    return mult * (1 - cost) / (1 + cost) - 1


def all_configs():
    return list(itertools.product(ENTRIES, TRAILS, HOLDS_H, LADDERS))


def build_matrix(listings):
    """R[config] = list of (listing index, gross mult, exit_t, peak) for listings where the entry fills."""
    entries = {v: [entry_point(L, v) for L in listings] for v in ENTRIES}
    R = {}
    for cfg in all_configs():
        v, trail, hold, ladder = cfg
        rows = []
        for k, L in enumerate(listings):
            e = entries[v][k]
            if e is None:
                continue
            i, px, t = e
            s = simulate(L, i, px, t, trail, hold, ladder)
            rows.append((k, s["mult"], s["exit_t"], s["peak"]))
        R[cfg] = rows
    return R, entries


# ----------------------------------------------------------------------------- statistics


def rets(rows, cost):
    return [net(m, cost) for _, m, _, _ in rows]


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def bootstrap_ci(xs, n=4000, lo=0.025, hi=0.975, seed=1):
    if len(xs) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    ms = sorted(mean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return ms[int(lo * n)], ms[min(n - 1, int(hi * n))]


def describe(xs):
    if not xs:
        return {"n": 0}
    pos = sum(1 for x in xs if x > 0)
    top3 = sorted(xs, reverse=True)[:3]
    total = sum(xs)
    share = sum(top3) / total if total > 0 else float("nan")
    rest = [x for x in xs if x not in top3] if len(xs) > 3 else []
    return {"n": len(xs), "mean": mean(xs), "median": statistics.median(xs), "win": pos / len(xs),
            "top3_share": share, "mean_ex_top3": mean(rest) if rest else float("nan"),
            "best": max(xs), "worst": min(xs), "ci": bootstrap_ci(xs)}


def streaks(xs):
    """Longest run of losing trades, and worst peak-to-trough of the cumulative sum of returns
    (equal money per trade, no compounding)."""
    run = worst_run = 0
    cum = peak = 0.0
    dd = 0.0
    for x in xs:
        run = run + 1 if x <= 0 else 0
        worst_run = max(worst_run, run)
        cum += x
        peak = max(peak, cum)
        dd = min(dd, cum - peak)
    return worst_run, dd


def walk_forward(R, listings, cost, entries=None, score="mean"):
    """Expanding window: for each listing k >= MIN_TRAIN choose the config with the best score on
    listings < k, trade listing k with it. Returns (oos returns, chosen configs)."""
    cfgs = [c for c in R if entries is None or c[0] in entries]
    by_listing = {c: {k: m for k, m, _, _ in R[c]} for c in cfgs}
    oos, chosen = [], []
    for k in range(MIN_TRAIN, len(listings)):
        best, best_s = None, -1e9
        for c in cfgs:
            xs = [net(m, cost) for kk, m in by_listing[c].items() if kk < k]
            if len(xs) < max(4, k // 2):        # a variant that rarely fills is not eligible
                continue
            s = mean(xs) if score == "mean" else statistics.median(xs)
            if s > best_s:
                best, best_s = c, s
        if best is None:
            continue
        chosen.append(best)
        if k in by_listing[best]:
            oos.append(net(by_listing[best][k], cost))
    return oos, chosen


def portfolio(R_cfg, listings, cost, cfg):
    """5 equal slots, 20% of current equity per trade, hourly mark-to-market. A listing that
    arrives while all slots are busy is skipped."""
    v, trail, hold, ladder = cfg
    trades = []
    for k, _, _, _ in R_cfg:
        e = entry_point(listings[k], v)
        i, px, t = e
        s = simulate(listings[k], i, px, t, trail, hold, ladder, marks=True)
        trades.append({"t": t, "exit_t": s["exit_t"], "mult": s["mult"], "marks": s["marks"]})
    trades.sort(key=lambda x: x["t"])
    if not trades:
        return None
    f = (1 - cost) / (1 + cost)
    cash, open_, skipped = 1.0, [], 0
    equity, peak, maxdd = 1.0, 1.0, 0.0
    t = trades[0]["t"] // HOUR * HOUR
    end = max(x["exit_t"] for x in trades) + HOUR
    q = list(trades)
    curve = []
    while t <= end:
        for p in list(open_):
            if p["exit_t"] <= t:
                cash += p["size"] * p["mult"] * f
                open_.remove(p)
        while q and q[0]["t"] <= t:
            tr = q.pop(0)
            if len(open_) >= SLOTS:
                skipped += 1
                continue
            eq = cash + sum(p["size"] * _mark(p, t) * f for p in open_)
            size = min(cash, eq / SLOTS)
            cash -= size
            open_.append(dict(tr, size=size))
        equity = cash + sum(p["size"] * _mark(p, t) * f for p in open_)
        peak = max(peak, equity)
        maxdd = min(maxdd, equity / peak - 1)
        curve.append((t, equity))
        t += HOUR
    months = (end - trades[0]["t"]) / (30.4 * DAY)
    return {"final": equity, "maxdd": maxdd, "skipped": skipped, "taken": len(trades) - skipped,
            "months": months, "monthly": equity ** (1 / max(months, 1e-9)) - 1, "curve": curve}


def _mark(p, t):
    m = 1.0
    for tt, mult in p["marks"]:
        if tt <= t:
            m = mult
        else:
            break
    return m


# ----------------------------------------------------------------------------- report


def fmt_cfg(c):
    v, trail, hold, ladder = c
    lad = "none" if ladder is None else f"half@+{ladder:.0%}"
    return f"{v:<10} trail={trail:.0%} hold={hold:>3}h ladder={lad}"


def heatmap(R, entry, ladder, cost, listings, title):
    print(f"\n{title}")
    print("trail / hold  " + "".join(f"{h:>5}h{'':>6}" for h in HOLDS_H))
    grid = {}
    for tr in TRAILS:
        cells = []
        for h in HOLDS_H:
            xs = rets(R[(entry, tr, h, ladder)], cost)
            grid[(tr, h)] = mean(xs)
            cells.append(f"{mean(xs):>+7.1%}/{statistics.median(xs):>+4.0%}" if xs else "      -     ")
        print(f"{tr:<14.0%}" + " ".join(cells))
    return grid


def plateau(grid, tr, h):
    """Mean of the neighbouring cells vs the cell itself: a robust config sits on a plateau."""
    ti, hi = TRAILS.index(tr), HOLDS_H.index(h)
    nb = [grid[(TRAILS[a], HOLDS_H[b])] for a in range(max(0, ti - 1), min(len(TRAILS), ti + 2))
          for b in range(max(0, hi - 1), min(len(HOLDS_H), hi + 2)) if (a, b) != (ti, hi)]
    return mean(nb), grid[(tr, h)]


def robust_score(R, cfg, cost_base, cost_stress, grids):
    """Half the 3x3 neighbourhood mean at STRESS cost, half the bootstrap 10th percentile of the
    mean at base cost. Both punish a config that only works in one cell or on one trade."""
    v, tr, h, lad = cfg
    xs = rets(R[cfg], cost_base)
    if len(xs) < 8:
        return None
    lo = bootstrap_ci(xs, n=2000, lo=0.10, hi=0.90)[0]
    nb, cell = plateau(grids[(v, lad)], tr, h)
    hood = (nb * 8 + cell) / 9 if not math.isnan(nb) else cell
    return 0.5 * hood + 0.5 * lo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=float, default=18)
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.05)
    a = ap.parse_args()
    now_ms = int(time.time() * 1000)
    t_start = time.time()

    if a.synthetic:
        print("SYNTHETIC MODE: fake prices, only checks that the study runs end to end\n")
        client = SyntheticListingClient(months=a.months)
        now_ms = client.now
    else:
        from data_source import CryptoComClient
        client = CryptoComClient()

    # 1. universe / listings ---------------------------------------------------------------
    print("=" * 100 + "\n1. LISTINGS FOUND\n" + "=" * 100)
    cand, st = discover_listings(client, a.months, now_ms, a.sleep)
    if st["limit_day"] is not None:
        print(f"\nearliest 1D history available: {ts(st['limit_day'])}  "
              f"({st['at_limit']} coins start there = API lookback limit, excluded; "
              f"{st['full']} coins have the full {int(a.months * 30.5)} days, excluded; "
              f"{st.get('too_young', 0)} listed in the last {PATH_DAYS} days, too young to judge)")
    print(f"{len(cand)} candidate listings; loading 5m/15m + hourly paths...")
    listings = load_paths(client, cand, now_ms, a.sleep)
    listings.sort(key=lambda L: L["t0"])
    if len(listings) < 5:
        print(f"\nonly {len(listings)} listings with usable data - nothing to study. "
              "Check that the API returns enough 1D history (see limit above).")
        return
    span_m = max(1e-9, (now_ms - listings[0]["t0"]) / (30.4 * DAY))
    per_month = {}
    for L in listings:
        per_month[L["month"]] = per_month.get(L["month"], 0) + 1
    print(f"\n{len(listings)} listings with usable data, {ts(listings[0]['t0'])} .. {ts(listings[-1]['t0'])}"
          f" = {len(listings) / span_m:.1f} listings/month over {span_m:.1f} months")
    print("per month: " + ", ".join(f"{m} {n}" for m, n in sorted(per_month.items())))
    tfs = {}
    for L in listings:
        tfs[L["tf"]] = tfs.get(L["tf"], 0) + 1
    print("finest bars available for the first 72h: " + ", ".join(f"{k}: {v}" for k, v in sorted(tfs.items())))
    print(f"\n{'coin':<8} {'listed (UTC)':<17} {'bars':>4} {'day-1 $vol':>11} {'high72h':>8} {'@24h':>7} {'@72h':>7}"
          "   (vs first bar close, before costs)")
    for L in listings:
        fc = L["first_close"]
        print(f"{L['sym']:<8} {ts(L['t0']):<17} {L['tf']:>4} {L['vol24']:>11,.0f} {L['hi72'] / fc - 1:>+8.0%} "
              f"{L['at_24h'] / fc - 1:>+7.0%} {L['at_72h'] / fc - 1:>+7.0%}")

    R, entries = build_matrix(listings)
    n_all = len(listings)

    # 2. entry variants ----------------------------------------------------------------------
    print("\n" + "=" * 100 + "\n2. ENTRY VARIANTS  (exit: trail 35% / 72h, no ladder; cost 0.8%/side)\n" + "=" * 100)
    print(f"{'entry':<11} {'fills':>5} {'mean':>7} {'95% CI of mean':>17} {'median':>7} {'win':>5} {'best':>6} {'worst':>6}")
    for v in ENTRIES:
        d = describe(rets(R[(v, 0.35, 72, None)], COST_BASE))
        if d["n"]:
            print(f"{v:<11} {d['n']:>3}/{n_all:<3} {d['mean']:>+7.1%} [{d['ci'][0]:>+6.1%}, {d['ci'][1]:>+6.1%}] "
                  f"{d['median']:>+7.1%} {d['win']:>5.0%} {d['best']:>+6.0%} {d['worst']:>+6.0%}")
        else:
            print(f"{v:<11}   0/{n_all:<3}  (never filled)")

    # 3/4. exit grid + costs -------------------------------------------------------------------
    print("\n" + "=" * 100 + "\n3. EXIT GRID  (cells: mean/median net return per trade)\n" + "=" * 100)
    grids = {}
    for v in ENTRIES:
        for lad in LADDERS:
            if v in ("first_bar", "close_1h") or (lad is None and v in ("delay_3h", "dip_20")):
                grids[(v, lad)] = heatmap(R, v, lad, COST_BASE, listings,
                                          f"entry={v}, ladder={'none' if lad is None else f'half@+{lad:.0%}'}, cost 0.8%")
            else:
                grids[(v, lad)] = {(tr, h): mean(rets(R[(v, tr, h, lad)], COST_BASE))
                                   for tr in TRAILS for h in HOLDS_H}
    grids_stress = {}
    for v in ENTRIES:
        for lad in LADDERS:
            if (v, lad) == (LIVE[0], LIVE[3]):
                grids_stress[(v, lad)] = heatmap(R, v, lad, COST_STRESS, listings,
                                                 f"4. STRESS COST 1.5%/side: entry={v}, ladder=none")
            else:
                grids_stress[(v, lad)] = {(tr, h): mean(rets(R[(v, tr, h, lad)], COST_STRESS))
                                          for tr in TRAILS for h in HOLDS_H}

    # the live config -------------------------------------------------------------------------
    print("\n" + "=" * 100 + "\n5. ROBUSTNESS\n" + "=" * 100)
    live_x = rets(R[LIVE], COST_BASE)
    d = describe(live_x)
    run, dd = streaks(live_x)
    nb, cell = plateau(grids[(LIVE[0], LIVE[3])], LIVE[1], LIVE[2])
    print(f"LIVE config ({fmt_cfg(LIVE)}):")
    print(f"  n={d['n']}  mean {d['mean']:+.1%}  95% CI [{d['ci'][0]:+.1%}, {d['ci'][1]:+.1%}]  median {d['median']:+.1%}"
          f"  win {d['win']:.0%}  top-3 trades = {d['top3_share']:.0%} of total profit"
          f"  mean without top 3 {d['mean_ex_top3']:+.1%}")
    print(f"  at 1.5% cost: mean {mean(rets(R[LIVE], COST_STRESS)):+.1%};  worst losing streak {run} trades;"
          f"  worst equal-money drawdown {dd:+.1%} (sum of returns)")
    print(f"  plateau check: cell {cell:+.1%} vs neighbours' mean {nb:+.1%} -> "
          + ("SPIKE (cell far above neighbours)" if cell - nb > 0.05 else "plateau"))

    # walk-forward ----------------------------------------------------------------------------
    print("\nWALK-FORWARD (expanding window: pick the best-mean config on all earlier listings, trade the next one)")
    for label, ents in (("all entries", None), ("no-dip entries", [e for e in ENTRIES if not e.startswith("dip")]),
                        ("live entry only", [LIVE[0]])):
        for cost in (COST_BASE, COST_STRESS):
            oos, chosen = walk_forward(R, listings, cost, ents)
            if not oos:
                print(f"  {label:<16} cost {cost:.1%}: not enough listings")
                continue
            dd_ = describe(oos)
            uniq = len(set(chosen))
            last = fmt_cfg(chosen[-1]) if chosen else "-"
            print(f"  {label:<16} cost {cost:.1%}: OOS mean {dd_['mean']:+.1%} CI [{dd_['ci'][0]:+.1%}, {dd_['ci'][1]:+.1%}]"
                  f" median {dd_['median']:+.1%} win {dd_['win']:.0%} n={dd_['n']};  {uniq} different configs chosen"
                  f" over time; last pick: {last}")
    oos_live = [net(m, COST_BASE) for k, m, _, _ in R[LIVE] if k >= MIN_TRAIN]
    if oos_live:
        print(f"  (same later listings, LIVE config held fixed: mean {mean(oos_live):+.1%}, n={len(oos_live)})")
    # rolling block version: 3-month blocks
    print("  rolling by quarter (train on everything before the quarter, best-mean config, test inside it):")
    quarters = sorted({q_of(L["month"]) for L in listings})
    for q in quarters[1:]:
        train = [k for k, L in enumerate(listings) if q_of(L["month"]) < q]
        test = [k for k, L in enumerate(listings) if q_of(L["month"]) == q]
        if len(train) < MIN_TRAIN or not test:
            continue
        best, bs = None, -1e9
        for c in R:
            xs = [net(m, COST_BASE) for k, m, _, _ in R[c] if k in set(train)]
            if len(xs) >= max(4, len(train) // 2) and mean(xs) > bs:
                best, bs = c, mean(xs)
        xs = [net(m, COST_BASE) for k, m, _, _ in R[best] if k in set(test)]
        lv = [net(m, COST_BASE) for k, m, _, _ in R[LIVE] if k in set(test)]
        print(f"    {q}: picked {fmt_cfg(best)} (train {bs:+.1%}) -> test {mean(xs):+.1%} n={len(xs)};"
              f"  live config in same quarter {mean(lv):+.1%}")

    # by month / by volume ---------------------------------------------------------------------
    print("\nBY LISTING MONTH (live config, cost 0.8%):")
    by_m = {}
    for k, m, _, _ in R[LIVE]:
        by_m.setdefault(listings[k]["month"], []).append(net(m, COST_BASE))
    for mth, xs in sorted(by_m.items()):
        print(f"  {mth}: n={len(xs):>2} mean {mean(xs):>+7.1%} median {statistics.median(xs):>+7.1%}"
              f" win {sum(x > 0 for x in xs) / len(xs):.0%}  {'#' * min(40, int(max(0, mean(xs)) * 100))}")
    pos_m = sum(1 for xs in by_m.values() if mean(xs) > 0)
    print(f"  months with a positive mean: {pos_m}/{len(by_m)}")

    print("\nBY FIRST-DAY USD VOLUME (terciles; live config):")
    vols = sorted(L["vol24"] for L in listings)
    cut = [vols[len(vols) // 3], vols[2 * len(vols) // 3]]
    buckets = {0: [], 1: [], 2: []}
    for k, m, _, _ in R[LIVE]:
        v = listings[k]["vol24"]
        buckets[0 if v < cut[0] else 1 if v < cut[1] else 2].append(net(m, COST_BASE))
    names = [f"< ${cut[0]:,.0f}", f"${cut[0]:,.0f} - ${cut[1]:,.0f}", f">= ${cut[1]:,.0f}"]
    for b, xs in buckets.items():
        if xs:
            print(f"  {names[b]:<28} n={len(xs):>2} mean {mean(xs):>+7.1%} median {statistics.median(xs):>+7.1%}"
                  f" win {sum(x > 0 for x in xs) / len(xs):.0%} best {max(xs):+.0%} worst {min(xs):+.0%}")

    # 6. recommendation ------------------------------------------------------------------------
    print("\n" + "=" * 100 + "\n6. MOST ROBUST CONFIG\n" + "=" * 100)
    print("score = 1/2 x (mean of the 3x3 trail/hold neighbourhood at 1.5% cost) + 1/2 x (bootstrap 10th pct of the mean at 0.8%)")
    scored = []
    for cfg in R:
        s = robust_score(R, cfg, COST_BASE, COST_STRESS, grids_stress)
        if s is not None:
            scored.append((s, cfg))
    scored.sort(key=lambda x: x[0], reverse=True)
    print(f"{'config':<52} {'score':>7} {'mean':>7} {'median':>7} {'win':>5} {'n':>3} {'@1.5%':>7}")
    for s, cfg in scored[:12]:
        xs = rets(R[cfg], COST_BASE)
        print(f"{fmt_cfg(cfg):<52} {s:>+7.1%} {mean(xs):>+7.1%} {statistics.median(xs):>+7.1%} "
              f"{sum(x > 0 for x in xs) / len(xs):>5.0%} {len(xs):>3} {mean(rets(R[cfg], COST_STRESS)):>+7.1%}")
    live_rank = next((i for i, (_, c) in enumerate(scored) if c == LIVE), None)
    print(f"live config rank: {live_rank + 1 if live_rank is not None else 'n/a'} of {len(scored)}")

    best_s, best = scored[0]
    xs = rets(R[best], COST_BASE)
    d = describe(xs)
    run, dd = streaks(xs)
    fills = len(xs) / n_all
    port = portfolio(R[best], listings, COST_BASE, best)
    port_live = portfolio(R[LIVE], listings, COST_BASE, LIVE)
    nb, cell = plateau(grids[(best[0], best[3])], best[1], best[2])
    print(f"\nRECOMMENDED: {fmt_cfg(best)}")
    print(f"  expected net return per trade: {d['mean']:+.1%}  (95% bootstrap CI [{d['ci'][0]:+.1%}, {d['ci'][1]:+.1%}];"
          f" at 1.5% cost {mean(rets(R[best], COST_STRESS)):+.1%})")
    print(f"  median {d['median']:+.1%}, win rate {d['win']:.0%}, top-3 trades = {d['top3_share']:.0%} of profit,"
          f" mean without top 3 {d['mean_ex_top3']:+.1%}, best {d['best']:+.0%}, worst {d['worst']:+.0%}")
    print(f"  trades per month: {len(xs) / span_m:.1f} ({fills:.0%} of {n_all / span_m:.1f} listings/month fill)")
    print(f"  worst losing streak: {run} trades in a row; worst equal-money drawdown {dd:+.1%}")
    print(f"  plateau: cell {cell:+.1%} vs neighbours {nb:+.1%}")
    if port:
        print(f"  5-slot portfolio (20% of equity per trade, hourly marks): {port['final'] - 1:+.1%} over {port['months']:.1f} months"
              f" = {port['monthly']:+.1%}/month, max drawdown {port['maxdd']:+.1%}, {port['taken']} taken, {port['skipped']} skipped (slots full)")
    if port_live:
        print(f"  same for LIVE config: {port_live['final'] - 1:+.1%}, {port_live['monthly']:+.1%}/month, max drawdown {port_live['maxdd']:+.1%}")

    # plain-English summary ----------------------------------------------------------------------
    live_d = describe(live_x)
    oos, chosen = walk_forward(R, listings, COST_BASE)
    wf = describe(oos) if oos else None
    if d["ci"][0] <= 0:
        verdict, advice = "is NOT proven", ("size it as an experiment, not a core strategy, until the "
                                            "confidence interval clears zero.")
    elif wf is not None and wf["mean"] <= 0:
        verdict, advice = "is fragile", ("it only shows up when the parameters are chosen with hindsight, "
                                         "so do not trust the in-sample numbers.")
    else:
        verdict, advice = "looks real but lumpy", ("keep trading it small, because a few big winners carry the "
                                                   "average and a long losing run is normal.")
    coarse = sum(1 for L in listings if L["tf"] == "1D")
    if coarse:
        advice += f" Caution: {coarse} of {n_all} listings only had daily bars, so their entries and stops are rough."
    print("\nSUMMARY: Over the last {:.0f} months Crypto.com listed {} coins we could test ({:.1f} a month). "
          "The rule the account trades today ({}) made {:+.1%} per trade on average, but the 95% range is "
          "[{:+.1%}, {:+.1%}], the median trade was {:+.1%}, {:.0%} of trades won and the three best trades "
          "supplied {:.0%} of all the profit. Picking parameters only from earlier listings and trading the "
          "next one (walk-forward) gave {}. The most robust setting is {}: {:+.1%} per trade "
          "(CI [{:+.1%}, {:+.1%}]), about {:.1f} trades a month, worst run of {} losers, and a 5-slot portfolio "
          "drawdown of {:.0%}. Conclusion: the edge {}; {}"
          .format(span_m, n_all, n_all / span_m, fmt_cfg(LIVE), live_d["mean"], live_d["ci"][0], live_d["ci"][1],
                  live_d["median"], live_d["win"], live_d["top3_share"] if not math.isnan(live_d["top3_share"]) else 0,
                  f"{wf['mean']:+.1%} per trade on {wf['n']} unseen listings" if wf else "too few listings to test",
                  fmt_cfg(best), d["mean"], d["ci"][0], d["ci"][1], len(xs) / span_m, run,
                  port["maxdd"] if port else 0, verdict, advice))
    print(f"\n({time.time() - t_start:.0f}s)")


def ts(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")


def q_of(month):
    y, m = month.split("-")
    return f"{y}-Q{(int(m) - 1) // 3 + 1}"


if __name__ == "__main__":
    main()
