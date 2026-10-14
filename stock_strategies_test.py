"""Offline tests for stock_strategies.py (no network).

1. Parity: lab.py's family functions (fam_dual_momentum, fam_trend_ensemble) and the live
   classes are run over the SAME synthetic daily data - the lab on its daily table, the live
   class on hourly bars rebuilt from those days plus the unfinished "today" bar the engine
   sees - and must pick the same holdings and weights on every rebalance date.
2. engine.rebalance_to / Portfolio.buy top-up / engine.step gating for target-weight
   strategies (needs the engine hook from the integration diff).

    python stock_strategies_test.py
"""
import lab
import stock_strategies as ss
from engine import Portfolio, step
from lab import Ctx, fam_dual_momentum, fam_trend_ensemble, load_synthetic

DAY_MS, HOUR = 86_400_000, 3_600_000
BPD = 7


# ---------------------------------------------------------------- helpers
def hourly_from_daily(ser):
    """7 hourly bars per trading day (14:00-20:00 UTC, one UTC date) whose last close is the
    daily close, like Yahoo's regular-session bars collapse in strategy._daily_closes."""
    out = []
    for d in sorted(ser):
        o, h, l, c = ser[d]
        for k in range(BPD):
            px = o + (c - o) * (k + 1) / BPD
            out.append({"t": d * DAY_MS + (14 + k) * HOUR, "o": o, "h": h, "l": l, "c": px, "v": 1.0})
    return out


def candles_at(hourly, day, next_day=None):
    """Bars up to the close of `day` plus the first bar of the next session (the unfinished
    day the live cycle sees at ~10:00 ET, which _daily_closes drops)."""
    bars = [b for b in hourly if b["t"] // DAY_MS <= day]
    if not bars:
        return []
    return bars + [dict(bars[-1], t=(next_day or day + 1) * DAY_MS + 14 * HOUR)]


def live_targets(strat, hourly, day):
    sig = {s: strat.analyze(candles_at(h, day)) for s, h in hourly.items() if s in strat.universe}
    sig = {s: x for s, x in sig.items() if x}
    return strat.targets(sig) if sig else {}


def same(a, b):
    return set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-9 for k in a)


def parity(name, ctx, fam, p, strat, hourly, days_idx):
    n, bad, nonempty = 0, [], 0
    for i in days_idx:
        want, _ = fam(ctx, i, {}, p)
        got = live_targets(strat, hourly, ctx.days[i])
        n += 1
        nonempty += bool(want)
        if not same(want, got):
            bad.append((ctx.dates[i], want, got))
    for dt, want, got in bad[:3]:
        print(f"    MISMATCH {dt}: lab {want} live {got}")
    print(f"  {name:<16} {lab.pstr(p):<48} {n - len(bad)}/{n} rebalance dates identical "
          f"({nonempty} with holdings)")
    assert not bad, f"{name} {p}: {len(bad)} mismatches"
    assert nonempty >= 3, f"{name} {p}: too few non-empty rebalances to be meaningful"


def synthetic():
    syms = sorted(set(lab.MARKET["stocks"]["syms"]) | {"SPY"})
    prices = load_synthetic(syms, 4, "stocks")
    ctx = Ctx(prices, "stocks", "SPY")
    hourly = {s: hourly_from_daily(ser) for s, ser in prices.items()}
    return ctx, hourly


# ---------------------------------------------------------------- parity
def test_universe_matches_lab():
    assert ss.INDEX_ETFS == lab.INDEX_ETFS
    dm = ss.DualMomentum(BPD)
    assert set(dm.universe) == set(lab.INDEX_ETFS) | {"IEF"}
    assert dm.rebalance_key == "%Y-%m" and dm.weekly
    te = ss.TrendEnsemble(["AAPL"], BPD)
    assert te.rebalance_key == "%G-%V" and "SPY" in te.universe
    # enough hourly bars for 253 completed daily closes + today, within Yahoo's 729-day cap
    assert dm.min_candles >= (252 + 2) * BPD
    assert int((dm.min_candles + 10) / 5 * 1.08) + 15 < 729
    print("  universe / keys / min_candles ok")


def test_dual_momentum_parity(ctx, hourly):
    month_ends = [i for i in range(300, ctx.n - 1) if ctx.mrem[i] == 1]
    for p in ({"top": 2, "safe": "IEF", "universe": "index"},      # the live pick
              {"top": 3, "safe": "IEF", "universe": "index"},
              {"top": 1, "safe": "cash", "universe": "all"},
              {"top": 3, "safe": "cash", "universe": "index"}):
        strat = ss.DualMomentum(BPD, top_n=p["top"], safe=p["safe"], universe=p["universe"])
        parity("dual_momentum", ctx, fam_dual_momentum, p, strat, hourly, month_ends)
    # the live class only rebalances at month boundaries: analyze()/targets() are pure, so
    # this is the engine's job (rebalance_key); a mid-month call must still be a valid pick
    strat = ss.DualMomentum(BPD)
    mid = next(i for i in range(300, ctx.n) if ctx.mpos[i] == 10)
    t = live_targets(strat, hourly, ctx.days[mid])
    assert abs(sum(t.values()) - 1) < 1e-9 or not t


def test_trend_ensemble_parity(ctx, hourly):
    week_ends = [i for i in range(230, ctx.n - 1) if ctx.wend[i]]
    uni = sorted(set(lab.MARKET["stocks"]["syms"]))
    for p in ({"lookbacks": (10, 20, 50, 100), "top": 5, "regime": 200},   # the live pick
              {"lookbacks": (10, 20, 50), "top": 2, "regime": 0},
              {"lookbacks": (10, 20, 50, 100), "top": 3, "regime": 50}):
        strat = ss.TrendEnsemble(uni, BPD, lookbacks=p["lookbacks"], top_n=p["top"], regime_days=p["regime"])
        parity("trend_ensemble", ctx, fam_trend_ensemble, p, strat, hourly, week_ends)
    # regime off -> flat, as in the lab
    strat = ss.TrendEnsemble(uni, BPD, regime_days=200)
    offs = [i for i in week_ends if not ctx.regime(i, 200)]
    assert offs and all(live_targets(strat, hourly, ctx.days[i]) == {} for i in offs)
    print(f"  trend_ensemble   regime-off weeks flat: {len(offs)}/{len(week_ends)}")


def test_missing_and_stale_symbols(ctx, hourly):
    """A symbol with no bars is skipped; one whose last close is stale is not a candidate
    (lab: ctx.live[s][i] is False) but a held one is left alone by the engine."""
    strat = ss.DualMomentum(BPD)
    assert strat.analyze([]) is None and strat.analyze([hourly["SPY"][0]]) is None
    for i in reversed([j for j in range(300, ctx.n - 1) if ctx.mrem[j] == 1]):   # last month end with a risk ETF held
        sig = {s: strat.analyze(candles_at(hourly[s], ctx.days[i])) for s in strat.universe}
        full = strat.targets(sig)
        if set(full) - {"IEF"}:
            break
    top = max((c for c in full if c != "IEF"), key=full.get)
    stale = dict(sig)
    stale[top] = strat.analyze(candles_at(hourly[top], ctx.days[i - 3]))     # 3 days stale
    t2 = strat.targets(stale)
    assert top not in t2 and abs(sum(t2.values()) - 1) < 1e-9
    print(f"  stale {top} dropped from candidates: {sorted(t2)}")


# ---------------------------------------------------------------- engine hook
def sigs(prices, t=1_700_000_000_000):
    return {c: {"price": p, "high": p, "low": p, "t": t, "stop": 0.0, "buy": True, "rank": 0.0}
            for c, p in prices.items()}


def test_rebalance_to():
    import config
    from engine import rebalance_to
    pf = Portfolio(cash=1000.0, fee=0.0, slippage=0.0)
    inv = 1 - config.MIN_CASH_RESERVE_PCT
    rebalance_to(pf, 1, {"A": 0.5, "B": 0.5}, sigs({"A": 10.0, "B": 20.0, "C": 5.0}))
    assert abs(pf.positions["A"]["qty"] * 10 - 500 * inv) < 1e-6
    assert abs(pf.positions["B"]["qty"] * 20 - 500 * inv) < 1e-6
    assert "C" not in pf.positions and abs(pf.cash - 1000 * (1 - inv)) < 1e-6
    # A doubles, B halves -> equity 1225: A trimmed to 45% of it, B topped up, C new, cash kept
    rebalance_to(pf, 2, {"A": 0.5, "B": 0.25, "C": 0.25}, sigs({"A": 20.0, "B": 10.0, "C": 5.0}))
    eq = pf.equity({"A": 20.0, "B": 10.0, "C": 5.0})
    assert abs(eq - 1225) < 1e-6
    for c, w, px in (("A", 0.5, 20.0), ("B", 0.25, 10.0), ("C", 0.25, 5.0)):
        assert abs(pf.positions[c]["qty"] * px - w * inv * eq) < 1e-6, c
    assert pf.positions["B"]["opened"] == 1 and pf.positions["C"]["opened"] == 2
    assert [t["reason"] for t in pf.trades[2:]] == ["rebalance: trim to target", "rebalance: top up 25%",
                                                    "rebalance: entry 25%"]
    # within the 2% band: nothing trades; dropped names are sold; no-price names untouched
    n = len(pf.trades)
    rebalance_to(pf, 3, {"A": 0.51, "B": 0.25, "C": 0.24}, sigs({"A": 20.0, "B": 10.0, "C": 5.0}))
    assert len(pf.trades) == n
    rebalance_to(pf, 4, {"A": 1.0}, sigs({"A": 20.0, "B": 10.0}))
    assert "B" not in pf.positions and "C" in pf.positions      # C had no price this cycle
    assert pf.trades[n]["reason"] == "rebalance: dropped from targets"   # then A topped up to 100%
    # top-up averages the entry price and keeps the cost basis additive
    pf2 = Portfolio(cash=1000.0, fee=0.0, slippage=0.0)
    pf2.buy(1, "X", 100.0, 10.0, 0.0)
    pf2.buy(2, "X", 100.0, 20.0, 0.0)
    assert abs(pf2.positions["X"]["qty"] - 15) < 1e-9 and abs(pf2.positions["X"]["entry"] - 100 / 7.5) < 1e-9
    assert pf2.positions["X"]["cost"] == 200 and pf2.positions["X"]["opened"] == 1
    print("  rebalance_to: sells / trims / top-ups / entries / band / cash reserve ok")


class _Stub:
    """Target-weight strategy with a monthly key, driven by the engine."""
    name, weekly, rebalance_key, universe = "stub", True, "%Y-%m", ["A", "B", "C"]

    def __init__(self):
        self.w = {"A": 0.5, "B": 0.5}

    def analyze(self, candles, market_ok=True):
        c = candles[-1]
        return {"price": c["c"], "high": c["c"], "low": c["c"], "t": c["t"], "stop": 0.0, "buy": True, "rank": 0.0}

    def manage(self, pos, s, now, rebalance=False):
        return None

    def targets(self, sig):
        return dict(self.w)


def test_step_gating():
    import config
    from datetime import datetime, timezone
    inv = 1 - config.MIN_CASH_RESERVE_PCT
    st, pf = _Stub(), Portfolio(cash=1000.0, fee=0.0, slippage=0.0)
    ms = lambda d: int(datetime(2026, *d, tzinfo=timezone.utc).timestamp() * 1000)
    bars = lambda t, px: {c: [{"t": t, "c": p, "h": p, "l": p, "o": p, "v": 1}] for c, p in px.items()}
    step(pf, bars(ms((9, 15, 14)), {"A": 10, "B": 10, "C": 10}), st)          # first ever cycle: rebalance
    assert set(pf.positions) == {"A", "B"} and pf.last_rebalance_week == "2026-09"
    st.w = {"C": 1.0}
    step(pf, bars(ms((9, 30, 15)), {"A": 12, "B": 8, "C": 10}), st)           # same month: nothing
    assert set(pf.positions) == {"A", "B"} and len(pf.trades) == 2
    step(pf, bars(ms((10, 1, 14)), {"A": 12, "B": 8, "C": 10}), st)           # new month: rotate to C
    assert set(pf.positions) == {"C"} and pf.last_rebalance_week == "2026-10"
    assert abs(pf.positions["C"]["qty"] * 10 - inv * pf.equity({"C": 10})) < 1e-6
    print("  engine.step: monthly gating + target-weight rebalance ok")


def test_engine_smoke(ctx, hourly):
    """The real classes driven through engine.step one cycle per trading day (as run_live
    does), on the synthetic hourly bars: monthly / weekly cadence, fully invested within the
    cash reserve, holdings equal to the lab's pick after each rebalance."""
    import config
    inv = 1 - config.MIN_CASH_RESERVE_PCT
    for strat, fam, p, key in ((ss.DualMomentum(BPD), fam_dual_momentum,
                                {"top": 2, "safe": "IEF", "universe": "index"}, "mrem"),
                               (ss.TrendEnsemble(sorted(ctx.syms), BPD), fam_trend_ensemble,
                                {"lookbacks": (10, 20, 50, 100), "top": 5, "regime": 200}, "wend")):
        pf, rebalances, checked = Portfolio(cash=500.0, fee=0.0, slippage=0.0005), 0, 0
        for i in range(ctx.n - 200, ctx.n - 1):
            # the cycle runs during session i+1 (first hourly bar of that day already open)
            bars = {s: candles_at(hourly[s], ctx.days[i], ctx.days[i + 1]) for s in strat.universe}
            bars = {s: b for s, b in bars.items() if b}
            n = len(pf.trades)
            step(pf, bars, strat, True)
            first_of_period = (ctx.mrem[i] == 1) if key == "mrem" else ctx.wend[i]
            if first_of_period:
                rebalances += 1
                want, _ = fam(ctx, i, {}, p)
                assert set(pf.positions) == set(want), (strat.name, ctx.dates[i], want, set(pf.positions))
                px = {s: b[-1]["c"] for s, b in bars.items()}
                eq = pf.equity(px)
                # nothing above target + the 2%-of-equity band; survivors inside the band keep
                # their excess (lab.simulate too) and the cash reserve is enforced only at buy
                # time (engine semantics), so the last new entry can come out short
                for s, w in want.items():
                    assert -0.10 < pf.positions[s]["qty"] * px[s] / eq - w * inv < 0.021, (s, w)
                checked += 1
            elif rebalances:
                assert len(pf.trades) == n, "traded between rebalances"
        assert checked >= 3 and pf.trades
        print(f"  engine smoke {strat.name:<15} {rebalances} rebalances, {len(pf.trades)} trades, "
              f"final equity ${pf.equity({s: hourly[s][-1]['c'] for s in pf.positions}):.2f}")


def test_rsi2_sizing():
    """config.RSI2 (stock_park_study.py): the official rsi2 account buys up to 3 names at 1/3 of
    equity each with no cash reserve; other strategies keep config.MIN_CASH_RESERVE_PCT."""
    import config
    from strategy import RSI2MeanReversion
    st = RSI2MeanReversion(["A", "B", "C", "D"], BPD)
    assert (st.max_positions, st.cash_reserve) == (config.RSI2["slots"], config.RSI2["cash_reserve"]) == (3, 0.0)
    assert abs(st.position_pct - 1 / 3) < 1e-9
    ranks = {"A": -3.0, "B": -1.0, "C": -8.0, "D": -12.0}     # rank = -RSI: B, A, C buy first, D last

    def analyze(cs, ok=True):
        c = cs[-1]
        return {"t": c["t"], "price": c["c"], "high": c["h"], "low": c["l"], "buy": True,
                "rank": ranks[c["sym"]], "stop": 0.0, "exit": False, "day": c["t"] // DAY_MS - 1}
    st.analyze = analyze
    bars = {s: [{"t": 20_000 * DAY_MS + 15 * HOUR, "o": 10.0, "h": 10.0, "l": 10.0, "c": 10.0, "v": 1.0, "sym": s}]
            for s in ranks}
    pf = Portfolio(cash=500.0, fee=config.STOCK_FEE_RATE, slippage=config.STOCK_SLIPPAGE_RATE)
    step(pf, bars, st, True)
    assert set(pf.positions) == {"B", "A", "C"}, pf.positions            # best 3 (lowest RSI), D skipped
    assert pf.cash < 1.0, pf.cash                                         # whole base invested
    for p_ in pf.positions.values():
        assert abs(p_["cost"] - 500 / 3) < 1.0, p_["cost"]
    # a strategy without its own cash_reserve still keeps the global 10%
    st2 = RSI2MeanReversion(["A", "B", "C", "D"], BPD, slots=2)
    st2.analyze = analyze
    del st2.cash_reserve                                                  # engine falls back to the global
    st2.position_pct = st2.max_position_pct = 0.5
    pf2 = Portfolio(cash=500.0, fee=config.STOCK_FEE_RATE, slippage=config.STOCK_SLIPPAGE_RATE)
    step(pf2, bars, st2, True)
    assert abs(pf2.cash - 500 * config.MIN_CASH_RESERVE_PCT) < 0.01, pf2.cash
    print("  rsi2 sizing: 3 x 33%, no reserve; others keep the 10% reserve")


def test_rsi2_entry_threshold():
    """config.RSI2["rsi_max"] (stock_rsi2_loosen_study.py): buy when RSI(2) < 25 above the 200-day average;
    an explicit rsi_max still overrides it."""
    import config
    from strategy import RSI2MeanReversion
    assert config.RSI2["rsi_max"] == 25
    assert RSI2MeanReversion(["A"], BPD).rsi_max == 25
    assert RSI2MeanReversion(["A"], BPD, rsi_max=15).rsi_max == 15

    def candles(tail):                       # 1 bar per day at 15:00 UTC: uptrend, then the tail
        closes = [100 + 0.5 * i for i in range(230)] + tail
        closes.append(closes[-1])            # today's unfinished bar (analyze ignores it)
        return [{"t": (20_000 + i) * DAY_MS + 15 * HOUR, "o": c, "h": c, "l": c, "c": c, "v": 1.0}
                for i, c in enumerate(closes)]

    def rsi(cs):
        return -RSI2MeanReversion(["A"], 1).analyze(cs)["rank"]

    mid = candles([213.5, 213.0])            # a modest dip: RSI(2) = 20
    assert 15 <= rsi(mid) < 25, rsi(mid)
    assert RSI2MeanReversion(["A"], 1).analyze(mid)["buy"]
    assert not RSI2MeanReversion(["A"], 1, rsi_max=15).analyze(mid)["buy"]
    below = candles([60.0, 61.0, 59.0])      # below the 200-day average: never a buy
    assert rsi(below) < 25 and not RSI2MeanReversion(["A"], 1).analyze(below)["buy"]
    print("  rsi2 entry: RSI(2) < 25 above the 200-day average")


# ---------------------------------------------------------------- breakout52 (EXPERIMENT 13)
def test_breakout52_setup():
    """config.STOCK_HIBETA is moonshot_study.HIBETA; the class carries the study's exact parameters; the
    high-beta names are downloaded as their own Yahoo group (a failure there never touches rsi2's bars)."""
    import config
    import moonshot_study
    from data_source import YahooClient
    assert config.STOCK_HIBETA == moonshot_study.HIBETA
    st = ss.Breakout52(config.STOCK_HIBETA, BPD)
    assert (st.max_positions, st.high_days, st.rank_days, st.exit_sma, st.trail_pct, st.regime_days) == (5, 252, 126, 50, 0.20, 200)
    assert st.rebalance_key == "%Y-%m-%d" and st.weekly and st.cash_reserve == 0.0 and abs(st.position_pct - 0.2) < 1e-12
    assert not hasattr(st, "trail"), "run_live.fast_check would trail it live; the study's exits are daily closes"
    assert "SPY" not in st.universe and set(st.universe) == set(config.STOCK_HIBETA)
    assert st.min_candles >= (252 + 2) * BPD and int((st.min_candles + 10) * 3 / 14) + 15 < 729
    core, hib = YahooClient.groups()
    assert "SPY" in core and "MSTR" in core and "MSTR" not in hib and "GME" in hib and not set(core) & set(hib)
    assert set(core) | set(hib) >= set(config.STOCK_HIBETA) | set(config.STOCK_UNIVERSE)
    print(f"  breakout52 setup ok: {len(st.universe)} names, {len(hib)} in their own download group")


def test_breakout52_regime():
    st = ss.Breakout52(["A"], 1)
    up = [{"t": (20_000 + i) * DAY_MS + 15 * HOUR, "o": 100 + i, "h": 100 + i, "l": 100 + i, "c": 100 + i, "v": 1.0}
          for i in range(202)]
    assert st.regime(up)                                     # last completed close above its 200-day average
    down = [dict(b, c=300 - i) for i, b in enumerate(up)]
    assert not st.regime(down) and not st.regime(up[:150]) and not st.regime([]) and not st.regime(None)
    print("  breakout52 regime: SPY's completed daily closes vs their 200-day average")


def synthetic_hibeta():
    import config
    syms = sorted(set(config.STOCK_HIBETA[:40]) | {"SPY"})
    prices = load_synthetic(syms, 4, "stocks")
    ctx = Ctx(prices, "stocks", "SPY")
    hourly = {s: hourly_from_daily(ser) for s, ser in prices.items()}
    return ctx, hourly


def test_breakout52_parity(ctx, hourly, p=None):
    """moonshot2_study.breakout2 through lab.simulate and Breakout52 through engine.step, one cycle per
    trading day on the same synthetic prices, must hold the same names every day (the lab's `held` at the
    open of day i+1 = the engine's positions after its cycle during day i+1). Run with the live parameters
    and with the 50-day exit off (exit_sma 1000: never available) so the 20% trail is the exit that fires."""
    import bisect
    import moonshot2_study as m2
    p = p or {"slots": 5, "trail": 0.20, "exit_sma": 50}
    uni = [s for s in ctx.syms if s != "SPY"]
    fn, first, seen = m2.breakout2(uni, p["slots"], trail=p["trail"], exit_sma=p["exit_sma"]), 260, {}

    def rec(c, i, held, pp):
        seen[i] = set(held)
        return fn(c, i, held, pp)
    lab.simulate(ctx, rec, {}, first, ctx.n, 0.0)
    strat = ss.Breakout52(uni, BPD, **p)
    days = {s: [b["t"] // DAY_MS for b in h] for s, h in hourly.items()}

    def bars_at(s, day, nxt):               # candles_at, without scanning the whole list each day
        k = bisect.bisect_right(days[s], day)
        return hourly[s][:k] + [dict(hourly[s][k - 1], t=nxt * DAY_MS + 14 * HOUR)] if k else []
    pf, bad, days_held, reasons = Portfolio(cash=1000.0, fee=0.0, slippage=0.0), [], 0, set()
    for i in range(first, ctx.n - 1):
        bars = {s: bars_at(s, ctx.days[i], ctx.days[i + 1]) for s in strat.universe}
        bars = {s: b for s, b in bars.items() if b}
        ok = strat.regime(bars_at("SPY", ctx.days[i], ctx.days[i + 1]))
        assert ok == ctx.regime(i, 200), ctx.dates[i]
        step(pf, bars, strat, ok)
        want = seen.get(i + 1, set())
        days_held += bool(want)
        if set(pf.positions) != want:
            bad.append((ctx.dates[i], sorted(want), sorted(pf.positions)))
        reasons |= {t["reason"] for t in pf.trades if t["side"] == "SELL"}
    for dt, want, got in bad[:3]:
        print(f"    MISMATCH {dt}: lab {want} live {got}")
    n = ctx.n - 1 - first
    print(f"  breakout52       {lab.pstr(p):<30} {n - len(bad)}/{n} days identical ({days_held} with holdings, "
          f"{len(pf.trades)} trades, exits: {sorted(reasons)})")
    assert not bad, f"{len(bad)} mismatching days"
    assert days_held >= 50 and len(pf.trades) >= 10, "too little activity to be meaningful"
    assert reasons == ({"gave back 20% from its highest close"} if p["exit_sma"] > 500 else
                       {"closed below its 50-day average"}) or p["exit_sma"] <= 500 and len(reasons) == 2, reasons
    for t in pf.trades:
        if t["side"] == "BUY":
            assert t["reason"] == "entry"


def test_breakout52_state_survives_restart():
    """The highest close since the buy is recomputed from the closes on/after the buy day (closes before it,
    even higher ones, never count) and kept on the position, which portfolio.json saves: a restart or a
    missed cycle never loses it."""
    import os, tempfile
    st = ss.Breakout52(["A"], BPD)
    d0 = 20_000
    pf = Portfolio(cash=500.0, fee=0.0, slippage=0.0)
    pf.buy(d0 * DAY_MS + 15 * HOUR, "A", 100.0, 10.0, 0.0)

    def sig(recent, buy=False, below=False):
        return {"price": recent[-1][1], "close": recent[-1][1], "buy": buy, "below_avg": below, "recent": recent}
    pos = pf.positions["A"]
    assert st.manage(pos, sig([(d0 - 1, 50.0)]), 0, rebalance=True) is None and pos.get("hc") is None   # fill day: no peak yet
    assert st.manage(pos, sig([(d0 - 1, 50.0), (d0, 10.0), (d0 + 1, 12.0), (d0 + 2, 9.7)]), 0, True) is None
    assert pos["hc"] == 12.0                                   # 9.7 is 19% under the peak: hold
    path = os.path.join(tempfile.mkdtemp(), "portfolio.json")
    pf.save(path)
    pf2 = Portfolio.load(path, fee=0.0, slippage=0.0)         # the engine restarts
    pos2 = pf2.positions["A"]
    assert pos2["hc"] == 12.0 and pos2["opened"] == d0 * DAY_MS + 15 * HOUR
    assert st.manage(pos2, sig([(d0 + 3, 9.5)]), 0, rebalance=False) is None     # between daily cycles: nothing
    act = st.manage(pos2, sig([(d0 + 3, 9.5)]), 0, rebalance=True)               # history window lost the peak: pos["hc"] has it
    assert act and act[0] == 1.0 and "20%" in act[2], act
    pos3 = dict(pos2, hc=None)                                 # no saved peak either: the full history gives it
    act = st.manage(pos3, sig([(d0 - 1, 50.0), (d0, 10.0), (d0 + 1, 12.0), (d0 + 2, 9.7), (d0 + 3, 9.5)]), 0, True)
    assert act and act[0] == 1.0 and pos3["hc"] == 12.0
    assert st.manage(dict(pos2), sig([(d0 + 3, 9.0)], buy=True), 0, True) is None   # a fresh 52-week high: never sold
    act = st.manage(dict(pos2), sig([(d0 + 3, 11.9)], below=True), 0, True)
    assert act and "50-day" in act[2]
    print("  breakout52 state: peak since the buy recomputed from history, saved on the position, survives a restart")


def test_join_official_and_average():
    """run_live.join_official: a strategy added to an official account starts at that account's balance (no
    fake jump in the official number, its daily P/L or its chart); dashboard._average draws that line."""
    import os, tempfile
    import dashboard
    import run_live
    cwd = os.getcwd()
    os.chdir(tempfile.mkdtemp())
    try:
        mk = {"stocks": {"main": ("rsi2", "breakout52"), "fee": 0.0, "slippage": 0.0005},
              "crypto": {"main": "early_mover", "fee": 0.0, "slippage": 0.0},
              "empty": {"main": ("x", "y"), "fee": 0.0, "slippage": 0.0}}
        os.makedirs("data/stocks/rsi2")
        with open("data/stocks/rsi2/equity.csv", "w") as f:
            f.write("time,equity,cash,positions\n2026-09-28 13:32,500.0,500.0,0\n2026-10-13 19:06,509.63,0.0,3\n")
        t = 1_792_000_000_000
        assert run_live.join_official(mk, t) == {("stocks", "breakout52"): 509.63}
        pf = run_live.load_pf("stocks", "breakout52") if False else run_live.Portfolio.load("data/stocks/breakout52/portfolio.json")
        assert pf.cash == 509.63 and not pf.positions
        with open("data/stocks/breakout52/equity.csv") as f:
            rows = f.read().splitlines()
        assert rows[0] == "time,equity,cash,positions" and rows[1].endswith(",509.63,509.63,0") and len(rows) == 2
        assert run_live._official("stocks", mk["stocks"]) == (509.63, 0)          # unchanged by the join
        assert run_live._start("stocks", "breakout52") == 509.63 and run_live._start("stocks", "rsi2") == 500.0
        assert run_live.join_official(mk, t + 1) == {}                             # once
        assert not os.path.exists("data/crypto") and not os.path.exists("data/empty")
        a = [(1, 500.0), (2, 510.0), (3, 520.0)]
        b = [(2, 510.0), (3, 500.0)]
        assert dashboard._average([a, b]) == [(1, 500.0), (2, 510.0), (3, 510.0)]
        assert dashboard._average([a]) == a and dashboard._average([]) == []
    finally:
        os.chdir(cwd)
    print("  join_official: the new account starts at the official balance; _average: continuous line")


if __name__ == "__main__":
    print("stock_strategies_test")
    assert hasattr(__import__("engine"), "rebalance_to"), \
        "engine.py lacks the target-weight hook: apply stocks_patch.diff first"
    test_universe_matches_lab()
    test_rebalance_to()
    test_step_gating()
    test_rsi2_sizing()
    test_rsi2_entry_threshold()
    ctx, hourly = synthetic()
    print(f"  synthetic stocks: {len(ctx.syms)} symbols, {ctx.n} days {ctx.dates[0]} .. {ctx.dates[-1]}")
    test_dual_momentum_parity(ctx, hourly)
    test_trend_ensemble_parity(ctx, hourly)
    test_missing_and_stale_symbols(ctx, hourly)
    test_engine_smoke(ctx, hourly)
    test_breakout52_setup()
    test_breakout52_regime()
    test_breakout52_state_survives_restart()
    test_join_official_and_average()
    ctx2, hourly2 = synthetic_hibeta()
    print(f"  synthetic high-beta: {len(ctx2.syms)} symbols, {ctx2.n} days")
    test_breakout52_parity(ctx2, hourly2)
    test_breakout52_parity(ctx2, hourly2, {"slots": 3, "trail": 0.20, "exit_sma": 1000})
    print("all stock_strategies tests passed")
