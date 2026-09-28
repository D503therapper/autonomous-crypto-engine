"""Owner question (results/research_log.md, "Stocks: park idle cash in SPY between RSI2 trades"):
the official stocks account (strategy.RSI2MeanReversion, $500 base) sits in cash most of the time.
Does parking that idle cash in SPY / QQQ - and selling just the needed amount when an rsi2 signal
fires - beat plain rsi2 over a long history? Also: rsi2 + parking vs just holding SPY / QQQ, and
rsi2 with more slots / bigger positions so less cash is idle.

Data: Yahoo daily bars via lab.load_stocks (--years, default 25), universe = the live rsi2
universe (config.STOCK_UNIVERSE + config.STOCK_ETFS). Costs = config.STOCK_FEE_RATE +
config.STOCK_SLIPPAGE_RATE per side (0 + 0.05%), on every rsi2 AND every parking trade.

Execution (no look-ahead, same as lab.simulate / the live account): signals use day i's close,
orders fill at day i+1's open. Order of fills at an open: rsi2 exits -> rsi2 entries (the parked
ETF is sold first for whatever the entry needs beyond free cash) -> spare cash parked. rsi2 rules
are the live ones: RSI(2) < 15 and close > 200-day average, lowest RSI first, sell when close >
5-day average or RSI(2) > 70 or after 10 calendar days (strategy.RSI2MeanReversion.manage);
position = 18% of equity (0.9 / 5), 5 slots, 10% cash reserve, $10 minimum order.
Parked money never counts as a slot. Parking keeps `park_reserve` of equity in cash (0 = fully
invested, the owner's wish) and only tops up when idle cash exceeds 2% of equity (no dust trades).

Walk-forward: no parameters are tuned here (every variant is fixed in advance), so the test is
simply the two halves of the history, each simulated from a flat $500 account, plus the full span.

    python stock_park_study.py                   # real data (GitHub Actions)
    python stock_park_study.py --synthetic       # offline plumbing check (fake prices!)
"""
import argparse

import config
import lab

COST = config.STOCK_FEE_RATE + config.STOCK_SLIPPAGE_RATE
BASE = 500.0
UNIVERSE = sorted(set(config.STOCK_UNIVERSE) | set(config.STOCK_ETFS))
WARMUP = 215                      # 200-day average + slack before the first trade
DAY = 86_400


def variant(name, slots=5, size=0.18, reserve=0.10, park=None, park_reserve=0.0, park_trend=0,
            rsi_max=15, hold=10):
    return {"name": name, "slots": slots, "size": size, "reserve": reserve, "park": park,
            "park_reserve": park_reserve, "park_trend": park_trend, "rsi_max": rsi_max, "hold": hold}


VARIANTS = [
    variant("rsi2 live (5x18%)"),
    variant("rsi2 + park SPY", park="SPY"),
    variant("rsi2 + park QQQ", park="QQQ"),
    variant("rsi2 + park SPY >200d", park="SPY", park_trend=200),   # park only while SPY > its 200-day avg
    variant("rsi2 + park QQQ >200d", park="QQQ", park_trend=200),
    # less idle cash without parking: no 10% reserve, more / bigger slots (total rsi2 exposure capped at 100%)
    variant("rsi2 5x20%", slots=5, size=0.20, reserve=0.0),
    variant("rsi2 8x12.5%", slots=8, size=0.125, reserve=0.0),
    variant("rsi2 10x10%", slots=10, size=0.10, reserve=0.0),
    variant("rsi2 3x33%", slots=3, size=0.333, reserve=0.0),
    variant("rsi2 2x50%", slots=2, size=0.50, reserve=0.0),
    variant("rsi2 10x10% + park SPY", slots=10, size=0.10, reserve=0.0, park="SPY"),
    variant("rsi2 10x10% + park QQQ", slots=10, size=0.10, reserve=0.0, park="QQQ"),
]


def simulate(ctx, v, start, end, cost=COST):
    """Dollar account from BASE at day `start`. Returns (daily returns, invested fraction per day,
    closed rsi2 trade returns, number of parking orders, 1/0 per day: any rsi2 position held at the close).
    v["rsi_max"] / v["hold"] (default 15 / 10 calendar days) are the live entry threshold and time limit."""
    K, size, rsv, P = v["slots"], v["size"], v["reserve"], v["park"]
    cash, pos, park = BASE, {}, 0.0          # pos: sym -> {"u", "basis", "e": entry day number}
    exits, entries = set(), []
    rets, expo, trades, park_orders, eq_prev, held = [], [], [], 0, BASE, []
    rsi_max, hold_days = v.get("rsi_max", 15), v.get("hold", 10)
    for i in range(start, end):
        o = lambda s: ctx.o[s][i]
        # 1) rsi2 exits at the open
        for s in list(exits):
            if s in pos and o(s):
                pr = pos[s]["u"] * o(s) * (1 - cost)
                cash += pr
                trades.append(pr / pos[s]["basis"] - 1)
                del pos[s]
        park_px = (o(P) or ctx.c[P][i]) if P else None
        eq = cash + park * (park_px or 0) + sum(x["u"] * (o(s) or ctx.c[s][i]) for s, x in pos.items())
        # 2) rsi2 entries, lowest RSI first; parked ETF sold first for the part cash can't cover
        for s in entries:
            if len(pos) >= K or s in pos or not o(s):
                continue
            room = cash + (park * park_px * (1 - cost) if P and park_px else 0.0) - rsv * eq
            usd = min(size * eq, room)
            if usd < config.MIN_ORDER_USD:
                continue
            need = usd - (cash - rsv * eq)
            if need > 0 and P and park_px:                        # unpark just what is needed
                u = min(park, need / (park_px * (1 - cost)))
                cash += u * park_px * (1 - cost)
                park -= u
                park_orders += 1
            usd = min(usd, cash)
            cash -= usd
            pos[s] = {"u": usd * (1 - cost) / o(s), "basis": usd, "e": ctx.days[i]}
        # 3) park the spare cash (optionally only while the parking ETF is above its trend average)
        if P and park_px and ctx.live[P][i]:
            trend_ok = True
            if v["park_trend"]:
                m = ctx.ind(P, "sma", v["park_trend"])[i - 1]
                trend_ok = m is not None and ctx.c[P][i - 1] > m          # yesterday's close decides
            if not trend_ok and park > 0:
                cash += park * park_px * (1 - cost)
                park, park_orders = 0.0, park_orders + 1
            spare = cash - v["park_reserve"] * eq
            if trend_ok and spare > 0.02 * eq and spare >= config.MIN_ORDER_USD:
                park += spare * (1 - cost) / park_px
                cash -= spare
                park_orders += 1
        # 4) mark to the close
        eq = cash + (park * ctx.c[P][i] if P else 0.0) + sum(x["u"] * ctx.c[s][i] for s, x in pos.items())
        rets.append(eq / eq_prev - 1)
        expo.append(1 - cash / eq)
        held.append(1 if pos else 0)
        eq_prev = eq
        # 5) tomorrow's orders from today's close (live RSI2MeanReversion rules)
        exits = set()
        for s, x in pos.items():
            r, m5 = ctx.ind(s, "rsi", 2)[i], ctx.ind(s, "sma", 5)[i]
            if (ctx.days[i] - x["e"] >= hold_days or (m5 is not None and ctx.c[s][i] > m5)
                    or (r is not None and r > 70)):
                exits.add(s)
        cands = []
        for s in ctx.syms:
            if s in pos or not ctx.live[s][i]:
                continue
            r, m = ctx.ind(s, "rsi", 2)[i], ctx.ind(s, "sma", 200)[i]
            if r is not None and m is not None and r < rsi_max and ctx.c[s][i] > m:
                cands.append((r, s))
        entries = [s for _, s in sorted(cands)]
    return rets, expo, trades, park_orders, held


def hold(ctx, sym, start, end, cost=COST):
    c, o = ctx.c[sym], ctx.o[sym]
    i0 = next((i for i in range(start, end) if o[i]), None)
    rets, eq_prev = [], 1.0
    for i in range(start, end):
        eq = c[i] / o[i0] * (1 - cost) if i0 is not None and i >= i0 and c[i] else 1.0
        rets.append(eq / eq_prev - 1)
        eq_prev = eq
    return rets, [1.0 if i0 is not None and i >= i0 else 0.0 for i in range(start, end)], [], 2, []


def worst_month(rets, months):
    out, cur, last = [], 1.0, None
    for r, m in zip(rets, months):
        if m != last and last is not None:
            out.append(cur - 1)
            cur = 1.0
        cur *= 1 + r
        last = m
    out.append(cur - 1)
    return min(out)


HDR = (f"{'variant':<26} {'CAGR':>7} {'avg/mo':>7} {'maxDD':>6} {'worstMo':>7} {'Sharpe':>6} "
       f"{'invested':>8} {'rsi2 trd':>8} {'park ord':>8} {'$500 ->':>9}")


# names in today's universe that were picked with hindsight (the big winners of the last decade / late listings)
HINDSIGHT = {"NVDA", "TSLA", "PLTR", "COIN", "MSTR", "AMD", "AVGO", "META", "NFLX", "UBER"}
ROBUST = ["rsi2 live (5x18%)", "rsi2 + park SPY", "rsi2 + park QQQ", "rsi2 5x20%", "rsi2 3x33%", "rsi2 2x50%"]


def row(ctx, name, res, start, end):
    rets, expo, trades, porders = res[:4]
    st = lab.stats(rets, expo, trades, ctx.month[start:end], ctx.ppy)
    end_usd = BASE * (1 + st["total"])
    return st, (f"{name:<26} {st['cagr']:>+7.1%} {st['monthly']:>+7.2%} {st['mdd']:>6.1%} "
                f"{worst_month(rets, ctx.month[start:end]):>+7.1%} {st['sharpe']:>6.2f} {st['expo']:>8.0%} "
                f"{st['n_trades']:>8} {porders:>8} {end_usd:>9,.0f}")


def span_label(ctx, a, b):
    return f"{ctx.dates[a]} .. {ctx.dates[b - 1]} ({(b - a) / 252:.1f} years)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=25)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    print(f"=== stock parking study: {len(UNIVERSE)} symbols, {a.years} years of daily bars, "
          f"cost {COST:.3%}/side ===")
    prices = (lab.load_synthetic(UNIVERSE, a.years, "stocks") if a.synthetic
              else lab.load_stocks(UNIVERSE, a.years))
    ctx = lab.Ctx(prices, "stocks", "SPY")
    first = min(i for i in range(ctx.n) if ctx.live["SPY"][i]) + WARMUP
    mid = first + (ctx.n - first) // 2
    spans = [("OLDER HALF", first, mid), ("NEWER HALF", mid, ctx.n), ("FULL HISTORY", first, ctx.n)]
    table = {}
    for label, s0, s1 in spans:
        live_syms = sum(1 for s in ctx.syms if ctx.live[s][s0])
        print(f"\n--- {label}: {span_label(ctx, s0, s1)}; {live_syms} of {len(ctx.syms)} symbols trading at the start")
        print(HDR)
        for v in VARIANTS:
            st, line = row(ctx, v["name"], simulate(ctx, v, s0, s1), s0, s1)
            table[(label, v["name"])] = st
            print(line)
        for sym in ("SPY", "QQQ"):
            st, line = row(ctx, f"hold {sym}", hold(ctx, sym, s0, s1), s0, s1)
            table[(label, f"hold {sym}")] = st
            print(line)

    print("\n=== DECISION CHECK (apply only if better CAGR than rsi2 live in BOTH halves and max drawdown "
          "not worse than holding SPY in each half) ===")
    base = "rsi2 live (5x18%)"
    for v in VARIANTS[1:]:
        ok, notes = True, []
        for half in ("OLDER HALF", "NEWER HALF"):
            st, b, spy = table[(half, v["name"])], table[(half, base)], table[(half, "hold SPY")]
            better = st["cagr"] > b["cagr"]
            dd_ok = st["mdd"] <= spy["mdd"] + 1e-9
            ok &= better and dd_ok
            notes.append(f"{half.split()[0].lower()}: CAGR {st['cagr']:+.1%} vs {b['cagr']:+.1%}, "
                         f"DD {st['mdd']:.0%} vs SPY {spy['mdd']:.0%}")
        print(f"{'PASS' if ok else 'fail'}  {v['name']:<26} " + " | ".join(notes))
    print("\n=== ROBUSTNESS: the variants above on the universe WITHOUT the hindsight names "
          f"({', '.join(sorted(HINDSIGHT))}), and at 3x the cost (0.15%/side) ===")
    ctx2 = lab.Ctx({s: v for s, v in prices.items() if s not in HINDSIGHT}, "stocks", "SPY")
    for label, s0, s1 in spans[:2]:
        print(f"\n--- {label}")
        print(HDR)
        for v in VARIANTS:
            if v["name"] in ROBUST:
                print(row(ctx2, v["name"] + " -hs", simulate(ctx2, v, s0, s1), s0, s1)[1])
        for v in VARIANTS:
            if v["name"] in ROBUST:
                print(row(ctx, v["name"] + " 3xcost", simulate(ctx, v, s0, s1, cost=3 * COST), s0, s1)[1])
    print("\nCaveat: the universe is TODAY's list (NVDA, TSLA, PLTR, MSTR, COIN ... chosen with hindsight); names "
          "join when their data starts. Absolute rsi2 returns are a ceiling; the SPY/QQQ parking leg has no such bias.")


if __name__ == "__main__":
    main()
