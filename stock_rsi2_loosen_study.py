"""Owner complaint (results/research_log.md, "Stocks: rsi2 made no trade on its first day - loosen it?"):
the official stocks account (strategy.RSI2MeanReversion, 3 slots x 33%, no reserve) bought nothing on its
first trading day; he wants the money working ("all in"). rsi2 only buys names with RSI(2) < 15 above their
200-day average. Would a looser entry, parking idle cash in SPY, or a shorter hold beat the live setup?

Grid (all fixed in advance, 3 slots x 1/3 of equity, no cash reserve, same exits as live):
  rsi_max   15 (live) / 20 / 25 / 30 / 35
  parking   none (live) / idle cash in SPY only while SPY closed above its 200-day average
            (parked SPY sold first for whatever an rsi2 buy needs; stock_park_study.simulate)
  hold      10 calendar days (live) / 5
Machinery, universe, data, costs (0.05%/side), next-open fills and the two halves are stock_park_study's;
the robustness checks (universe without the hindsight names, 3x costs) likewise.

Decision rule (pre-registered): a variant is applied only if, in BOTH halves, its CAGR beats live in all
three checks (full universe, no hindsight names, 3x costs) AND its max drawdown is at most 5 points deeper
than live's in each of those six runs. If several pass, the one with the largest minimum CAGR margin wins.

    python stock_rsi2_loosen_study.py               # real data (GitHub Actions)
    python stock_rsi2_loosen_study.py --synthetic   # offline plumbing check (fake prices!)
"""
import argparse

import lab
import stock_park_study as sp

LIVE = "rsi<15 hold10"
DD_SLACK = 0.05


def grid():
    out = []
    for park in (False, True):
        for hold in (10, 5):
            for rmax in (15, 20, 25, 30, 35):
                name = f"rsi<{rmax} hold{hold}" + (" +SPY>200d" if park else "")
                out.append(sp.variant(name, slots=3, size=1 / 3, reserve=0.0, rsi_max=rmax, hold=hold,
                                      park="SPY" if park else None, park_trend=200 if park else 0))
    return out


HDR = (f"{'variant':<26} {'CAGR':>7} {'maxDD':>6} {'Sharpe':>6} {'invested':>8} {'days in':>7} "
       f"{'trd/yr':>6} {'win%':>5} {'$500 ->':>9}")


def run(ctx, v, s0, s1, cost=sp.COST):
    res = sp.simulate(ctx, v, s0, s1, cost=cost)
    rets, expo, trades, _, held = res
    st = lab.stats(rets, expo, trades, ctx.month[s0:s1], ctx.ppy)
    st["days_in"] = sum(held) / len(held) if held else 0.0
    st["tpy"] = len(trades) / (len(rets) / 252) if rets else 0.0
    line = (f"{v['name']:<26} {st['cagr']:>+7.1%} {st['mdd']:>6.1%} {st['sharpe']:>6.2f} {st['expo']:>8.0%} "
            f"{st['days_in']:>7.0%} {st['tpy']:>6.0f} {st['win']:>5.0%} {sp.BASE * (1 + st['total']):>9,.0f}")
    return st, line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=25)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    print(f"=== rsi2 loosen study: {len(sp.UNIVERSE)} symbols, {a.years} years of daily bars, "
          f"cost {sp.COST:.3%}/side, 3 slots x 33%, no reserve ===")
    print("invested = average share of equity in positions (incl. parked SPY); days in = share of days holding "
          ">= 1 rsi2 name")
    prices = (lab.load_synthetic(sp.UNIVERSE, a.years, "stocks") if a.synthetic
              else lab.load_stocks(sp.UNIVERSE, a.years))
    ctx = lab.Ctx(prices, "stocks", "SPY")
    ctx_hs = lab.Ctx({s: x for s, x in prices.items() if s not in sp.HINDSIGHT}, "stocks", "SPY")
    first = min(i for i in range(ctx.n) if ctx.live["SPY"][i]) + sp.WARMUP
    mid = first + (ctx.n - first) // 2
    halves = [("OLDER", first, mid), ("NEWER", mid, ctx.n)]
    checks = [("full", ctx, 1), ("-hindsight", ctx_hs, 1), ("3x cost", ctx, 3)]
    V = grid()
    T = {}
    for ck, c, mult in checks:
        for h, s0, s1 in halves:
            print(f"\n--- {h} HALF, {ck}: {sp.span_label(ctx, s0, s1)}")
            print(HDR)
            for v in V:
                st, line = run(c, v, s0, s1, cost=mult * sp.COST)
                T[(ck, h, v["name"])] = st
                print(line)
            if ck == "full":
                st, line = sp.row(ctx, "hold SPY", sp.hold(ctx, "SPY", s0, s1), s0, s1)
                print(f"{'hold SPY':<26} {st['cagr']:>+7.1%} {st['mdd']:>6.1%} {st['sharpe']:>6.2f}")

    print(f"\n--- FULL HISTORY, full universe: {sp.span_label(ctx, first, ctx.n)}")
    print(HDR)
    for v in V:
        print(run(ctx, v, first, ctx.n)[1])

    print(f"\n=== DECISION CHECK vs live ({LIVE}): CAGR better in all 6 runs (2 halves x full / -hindsight / "
          f"3x cost) and max DD at most {DD_SLACK:.0%} points deeper in each ===")
    passed = []
    for v in V[1:]:
        ok, margins, notes = True, [], []
        for ck, _, _ in checks:
            for h, _, _ in halves:
                st, b = T[(ck, h, v["name"])], T[(ck, h, LIVE)]
                m = st["cagr"] - b["cagr"]
                margins.append(m)
                ok &= m > 0 and st["mdd"] <= b["mdd"] + DD_SLACK
                notes.append(f"{h[0].lower()}/{ck.split()[0][:4]} {m:+.1%} DD {st['mdd']:.0%}v{b['mdd']:.0%}")
        if ok:
            passed.append((min(margins), v["name"]))
        print(f"{'PASS' if ok else 'fail'}  {v['name']:<24} " + " | ".join(notes))
    if passed:
        print(f"\nWINNER (largest minimum CAGR margin): {max(passed)[1]} (min margin {max(passed)[0]:+.1%})")
    else:
        print("\nNO variant passes: keep the live rsi2 (RSI2 < 15, hold 10 days, no parking).")
    print("\nCaveat: the universe is TODAY's list (hindsight); absolute rsi2 returns are a ceiling.")


if __name__ == "__main__":
    main()
