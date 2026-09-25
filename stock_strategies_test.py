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


def candles_at(hourly, day):
    """Bars up to the close of `day` plus the first bar of the next session (the unfinished
    day the live cycle sees at ~10:00 ET, which _daily_closes drops)."""
    bars = [b for b in hourly if b["t"] // DAY_MS <= day]
    if not bars:
        return []
    return bars + [dict(bars[-1], t=(day + 1) * DAY_MS + 14 * HOUR)]


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
    i = max(j for j in range(ctx.n - 1) if ctx.mrem[j] == 1)
    day = ctx.days[i]
    sig = {s: strat.analyze(candles_at(hourly[s], day)) for s in strat.universe}
    full = strat.targets(sig)
    top = max(full, key=full.get)
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
    # A doubles, B halves -> equity 1350: A trimmed to 45% of it, B topped up, C new, cash kept
    rebalance_to(pf, 2, {"A": 0.5, "B": 0.25, "C": 0.25}, sigs({"A": 20.0, "B": 10.0, "C": 5.0}))
    eq = pf.equity({"A": 20.0, "B": 10.0, "C": 5.0})
    assert abs(eq - 1350) < 1e-6
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
    assert pf.trades[-1]["reason"] == "rebalance: dropped from targets"
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


if __name__ == "__main__":
    print("stock_strategies_test")
    assert hasattr(__import__("engine"), "rebalance_to"), \
        "engine.py lacks the target-weight hook: apply stocks_patch.diff first"
    test_universe_matches_lab()
    test_rebalance_to()
    test_step_gating()
    ctx, hourly = synthetic()
    print(f"  synthetic stocks: {len(ctx.syms)} symbols, {ctx.n} days {ctx.dates[0]} .. {ctx.dates[-1]}")
    test_dual_momentum_parity(ctx, hourly)
    test_trend_ensemble_parity(ctx, hourly)
    test_missing_and_stale_symbols(ctx, hourly)
    print("all stock_strategies tests passed")
