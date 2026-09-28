"""Smart-money study (offline): do wallets that bought early into past runners predict the next runner?

Inputs: tools/smartmoney_sample.json (the consolidated study's pool-sequential entry events: live entry 1h >= +10%,
age >= 6h, $100k floors; outcome = live exit, 14-day hold, costs) and results/smartmoney_raw.json.gz (buyer wallets
collected on GitHub Actions by tools/probe_smartmoney.py: the hour before each trigger + the earliest trades after
launch; Blockscout for Base / Ethereum, public Solana RPC for Solana).

Method (no lookahead): an event's label (RUNNER = peaked >= 2x entry, DUD = exited <= 0%) becomes known only at its
simulated exit time.  At each new event (time t) a wallet's reputation counts only events on OTHER pools that it
bought into (pre-trigger hour or launch window) and whose label was known before t.  "Bot-like" wallets (in >= 20%
of the prior buyer lists of that chain, min 5 lists) are dropped.  KNOWN-GOOD wallet: >= 1 runner and more runners
than duds.  Signal: number of known-good wallets among the buyers of the hour before our entry (and, variant, among
the launch buyers).  Compared: runner rate / mean return with signal vs without, older / newer halves.
Also: overlap - wallets early in >= 2 different runners vs the same count under shuffled labels (permutation)."""
import gzip
import json
import random
import statistics as st
import sys
import time

SAMPLE, RAW = "tools/smartmoney_sample.json", "results/smartmoney_raw.json.gz"
BOT_SHARE, BOT_MIN = 0.20, 5


def ts(t):
    return time.strftime("%Y-%m-%d", time.gmtime(t))


def label(e):
    return "run" if e["peak"] >= 2.0 else ("dud" if e["ret"] <= 0 else "mid")


def load():
    S = json.load(open(SAMPLE))
    with gzip.open(RAW, "rt") as f:
        R = json.load(f)
    pools = S["pools"]
    evs = {(e["k"], e["t"]): dict(e, net=pools[e["k"]]["net"], sym=pools[e["k"]]["sym"], lab=label(e)) for e in S["events"]}
    pre = {}
    for r in R["pre"]:
        if "buys" in r and (r["k"], r["t"]) in evs:
            pre[(r["k"], r["t"])] = r
    return S, R, pools, evs, pre


def signal_rows(ev_list, W, LW):
    """Walk-forward: per event with buyer data, known-good / known-bad wallets from OTHER pools' events of the same
    chain whose outcome was known (exit_t) before this entry.  W: {(k, t): set | None}, LW: {k: {(wallet, time)}}."""
    rows = []
    for e in ev_list:
        s = W[(e["k"], e["t"])]
        if s is None:
            continue
        t = e["t"]
        prior = [x for x in ev_list if x["exit_t"] < t and x["k"] != e["k"] and x["net"] == e["net"]]
        seen = {}
        nlists = 0
        for x in prior:
            sx = set(W[(x["k"], x["t"])] or ()) | {w for w, bt in LW.get(x["k"], ()) if bt < x["t"]}
            if not sx:
                continue
            nlists += 1
            for w in sx:
                d = seen.setdefault(w, {"run": 0, "dud": 0, "mid": 0, "n": 0, "k": set()})
                if x["k"] in d["k"]:
                    continue
                d["k"].add(x["k"])
                d[x["lab"]] += 1
                d["n"] += 1
        botc = {w for w, d in seen.items() if nlists >= BOT_MIN and d["n"] >= max(BOT_MIN, BOT_SHARE * nlists)}
        good = {w for w, d in seen.items() if w not in botc and d["run"] >= 1 and d["run"] > d["dud"]}
        bad = {w for w, d in seen.items() if w not in botc and d["dud"] >= 1 and d["dud"] > d["run"]}
        lw = {w for w, bt in LW.get(e["k"], ()) if bt < t}
        rows.append(dict(e=e, g_pre=len(s & good), b_pre=len(s & bad), g_launch=len(lw & good), n_buy=len(s), n_good=len(good),
                         known=len(seen), lists=nlists))
    return rows


def main():
    S, R, pools, evs, pre = load()
    out = []
    P = lambda *a: out.append(" ".join(str(x) for x in a))
    P(f"smart-money study {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}; raw collected {ts(R['made'])}")
    # ---------------------------------------------------------------- coverage
    P("\n1. COVERAGE (events = pool-sequential live-entry trades 2026-07-07..09-27)")
    for net in ("solana", "base", "eth"):
        E = [e for e in evs.values() if e["net"] == net]
        got = [pre[k] for k in pre if evs[k]["net"] == net]
        nb = [len(r["buys"]) for r in got]
        L = [v for k, v in R["launch"].items() if pools[k]["net"] == net]
        P(f"  {net:<7} events {len(E):>3}; pre-hour windows collected {len(got):>3} (with >= 1 buyer {sum(1 for x in nb if x)}; "
          f"buyers/window median {st.median(nb) if nb else 0}, max {max(nb) if nb else 0}); launch windows {len(L)} "
          f"(with buyers {sum(1 for v in L if v['buys'])})")
    errs = {}
    for r in R["pre"]:
        if "err" in r:
            errs[(pools[r["k"]]["net"], r["err"])] = errs.get((pools[r["k"]]["net"], r["err"]), 0) + 1
    if errs:
        P("  not collected:", errs)

    # ---------------------------------------------------------------- per-event wallet sets
    ev_list = sorted(evs.values(), key=lambda e: e["t"])
    W = {}                 # (k,t) -> set of pre-hour buyers
    for e in ev_list:
        r = pre.get((e["k"], e["t"]))
        W[(e["k"], e["t"])] = {b[1] for b in r["buys"] if b[1]} if r else None
    LW = {k: {(b[1], b[0]) for b in v["buys"] if b[1]} for k, v in R["launch"].items()}

    # ---------------------------------------------------------------- overlap + permutation
    P("\n2. OVERLAP: wallets among the buyers of >= 2 DIFFERENT pools' entry events (pre-hour or launch)")
    pool_w = {}
    for e in ev_list:
        s = W[(e["k"], e["t"])]
        if s is None:
            continue
        pool_w.setdefault(e["k"], set()).update(s)
    for k, s in LW.items():
        pool_w.setdefault(k, set()).update(w for w, _ in s)
    lab_pool = {}
    for e in ev_list:                                     # a pool is a runner if any of its events ran >= 2x
        if e["k"] in pool_w:
            labs = lab_pool.setdefault(e["k"], set())
            labs.add(e["lab"])
    lab_pool = {k: ("run" if "run" in v else "dud" if "dud" in v else "mid") for k, v in lab_pool.items()}
    cnt = {}
    for k, s in pool_w.items():
        for w in s:
            cnt.setdefault(w, []).append(k)
    multi = {w: ks for w, ks in cnt.items() if len(ks) >= 2}
    n_pools = len(pool_w)
    bots = {w for w, ks in cnt.items() if len(ks) >= max(BOT_MIN, BOT_SHARE * n_pools)}
    P(f"  pools with wallets {n_pools} ({sum(1 for k in pool_w if lab_pool.get(k) == 'run')} runner pools); distinct wallets {len(cnt)}; "
      f"in >= 2 pools {len(multi)}; in >= 3 {sum(1 for ks in cnt.values() if len(ks) >= 3)}; bot-like (>= {BOT_SHARE:.0%} of pools) {len(bots)}")
    top = sorted(cnt.items(), key=lambda x: -len(x[1]))[:12]
    for w, ks in top:
        labs = [lab_pool.get(k, "?") for k in ks]
        P(f"    {w[:14]}.. in {len(ks):>3} pools: run {labs.count('run')}, dud {labs.count('dud')}, mid {labs.count('mid')}"
          f"{'  [bot-like]' if w in bots else ''}  e.g. {', '.join(pools[k]['sym'] for k in ks[:6])}")

    def runner_hits(labmap):
        c = 0
        for w, ks in cnt.items():
            if w in bots or len(ks) < 2:
                continue
            if sum(1 for k in ks if labmap.get(k) == "run") >= 2:
                c += 1
        return c
    real = runner_hits(lab_pool)
    keys = list(lab_pool)
    rng = random.Random(7)
    perm = []
    for _ in range(300):
        v = [lab_pool[k] for k in keys]
        rng.shuffle(v)
        perm.append(runner_hits(dict(zip(keys, v))))
    pv = sum(1 for x in perm if x >= real) / len(perm)
    P(f"  non-bot wallets early in >= 2 RUNNER pools: {real}; shuffled labels median {st.median(perm)}, 95th pct "
      f"{sorted(perm)[int(0.95 * len(perm))]}; p = {pv:.2f}")

    # ---------------------------------------------------------------- walk-forward reputation
    P("\n3. WALK-FORWARD SIGNAL: known-good wallets (from earlier, resolved coins only) among the buyers before our entry")
    rows = signal_rows(ev_list, W, LW)
    if not rows:
        P("  no events with buyer data")
    else:
        split = sorted(r["e"]["t"] for r in rows)[len(rows) // 2]
        P(f"  events with buyer data {len(rows)}; halves split {ts(split)}; known-good wallets available at the split "
          f"(median over newer events) {st.median([r['n_good'] for r in rows if r['e']['t'] >= split] or [0])}")

        def summ(sub):
            if not sub:
                return "n   0"
            rets = [r["e"]["ret"] for r in sub]
            return (f"n {len(sub):>3}  runner(>=2x) {sum(r['e']['lab'] == 'run' for r in sub) / len(sub):>4.0%}  "
                    f"exit>=+100% {sum(r['e']['ret'] >= 1 for r in sub) / len(sub):>4.0%}  dud {sum(r['e']['lab'] == 'dud' for r in sub) / len(sub):>4.0%}  mean {st.mean(rets):+7.1%}  median {st.median(rets):+7.1%}")
        for name, f in (("all", lambda r: True), ("older", lambda r: r["e"]["t"] < split), ("newer", lambda r: r["e"]["t"] >= split)):
            sub = [r for r in rows if f(r)]
            P(f"  [{name}]")
            P(f"    baseline                      {summ(sub)}")
            for th in (1, 2, 3):
                P(f"    >= {th} good wallet(s) pre-hour   {summ([r for r in sub if r['g_pre'] >= th])}")
            P(f"    0 good wallets pre-hour       {summ([r for r in sub if r['g_pre'] == 0])}")
            P(f"    good > bad wallets pre-hour   {summ([r for r in sub if r['g_pre'] > r['b_pre']])}")
            P(f"    bad > good wallets pre-hour   {summ([r for r in sub if r['b_pre'] > r['g_pre']])}")
            P(f"    >= 1 good wallet at launch    {summ([r for r in sub if r['g_launch'] >= 1])}")
        for net in ("solana", "base", "eth"):
            sub = [r for r in rows if r["e"]["net"] == net]
            P(f"  [{net}] baseline {summ(sub)}")
            P(f"  [{net}] >=1 good pre   {summ([r for r in sub if r['g_pre'] >= 1])}")
        P("  runners and what the signal saw (good / bad pre-hour wallets, buyers in window):")
        for r in rows:
            if r["e"]["lab"] == "run":
                P(f"    {ts(r['e']['t'])} {r['e']['net']:<6} {r['e']['sym'][:14]:<14} peak {r['e']['peak']:>5.1f}x ret {r['e']['ret']:+6.0%}  "
                  f"good {r['g_pre']} bad {r['b_pre']} buyers {r['n_buy']}")
    txt = "\n".join(out)
    print(txt)
    if "--write" in sys.argv:
        open("results/smartmoney_study.txt", "w").write(txt + "\n")


if __name__ == "__main__":
    main()
