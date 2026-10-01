"""DEX LIVE-REPLAY study: the live entry and exit choices replayed on the engine's OWN scanner log.

Why: every earlier DEX study used pools picked from registries after the fact (>= 8 days old, >= $15k reserve ever
seen), so coins that die within a day are mostly missing - and those are exactly the ones that hurt us live (SS 2.1x
-> -93%, AIRPAD 2.05x -> -99% in hours).  data/dex/scan/*.csv.gz is every pool the live scanner looked at (~3,000 at
a time, ~hourly readings each, dead ones included): no survivorship bias, but only a few days long.

entry   live screen as far as the log allows: 1h >= +10% (<= +5,000%), buys > sells in the hour, liquidity >= $100k,
        24h volume >= $100k, age >= 6h.  The scam screen (contract / holders / LP) can NOT be replayed -> some of these
        coins would have been rejected; rugs here are real ones the screen may have caught.
exit    replayed on later readings of the same pair: rug (liquidity < 50% of entry liq x sqrt(price move)) sells at
        that reading; variants below; positions still open at the end are valued at the last reading.
costs   0.3% fee + 1% slippage per side.  One position per pool at a time.

    python dex_live_replay_study.py
"""
import csv
import glob
import gzip
import math
import statistics
from datetime import datetime, timezone

COST = 0.013
EXITS = {
    "never sell early": {},
    "stake back at 3x": {"tp": (3.0, 1 / 3)},
    "stake back at 2x (live)": {"tp": (2.0, 0.5)},
    "stake back at 1.5x": {"tp": (1.5, 1 / 1.5)},
    "2x stake back + stop -50%": {"tp": (2.0, 0.5), "stop": 0.5},
    "2x stake back + stop -30%": {"tp": (2.0, 0.5), "stop": 0.3},
    "stop -50% only": {"stop": 0.5},
}


def t_of(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load(paths):
    by = {}
    for p in paths:
        with gzip.open(p, "rt") as fh:
            for r in csv.DictReader(fh):
                px, liq = f(r["price"]), f(r["liq"])
                if not px or px <= 0 or liq is None:
                    continue
                by.setdefault((r["chain"], r["pair"]), []).append({
                    "t": t_of(r["time"]), "sym": r["sym"], "px": px, "liq": liq, "vol24": f(r["vol24"]) or 0,
                    "age": f(r["age_h"]) or 0, "b1": f(r["b1"]) or 0, "s1": f(r["s1"]) or 0, "h1": f(r["h1"]),
                    "h6": f(r["h6"])})
    for k, v in by.items():
        v.sort(key=lambda x: x["t"])
        ok, last = [], None                     # bad ticks: a reading 10x away from the last good one (junk pool / API
        for r in v:                             # glitch, e.g. SNOWMOON 1,000,000x) is dropped; the next reading decides
            if last is None or 0.1 <= r["px"] / last <= 10:
                ok.append(r)
                last = r["px"]
        by[k] = ok
    return by


def entry_ok(r):
    return (r["h1"] is not None and 0.10 <= r["h1"] <= 50 and r["b1"] > r["s1"] and r["liq"] >= 100_000
            and r["vol24"] >= 100_000 and r["age"] >= 6)


def run(rows, i0, v):
    e, liq0 = rows[i0]["px"], rows[i0]["liq"]
    q, cash, took, peak = 1.0, 0.0, False, e
    for r in rows[i0 + 1:]:
        p = r["px"]
        if r["liq"] <= 0 or r["liq"] < 0.5 * liq0 * math.sqrt(min(1.0, p / e)):
            return cash + q * p / e * (1 - COST) - 1, r["t"], peak / e, "rug"
        peak = max(peak, p)
        tp = v.get("tp")
        if tp and not took and p >= e * tp[0]:
            cash += q * tp[1] * p / e * (1 - COST)
            q *= 1 - tp[1]
            took = True
        st = v.get("stop")
        if st and not took and p <= e * (1 - st):
            return cash + q * p / e * (1 - COST) - 1, r["t"], peak / e, "stop"
    return cash + q * rows[-1]["px"] / e * (1 - COST) - 1, rows[-1]["t"], peak / e, "open"


def main():
    paths = sorted(glob.glob("data/dex/scan/*.csv.gz"))
    by = load(paths)
    sigs = []
    for k, rows in by.items():
        free = 0
        for i, r in enumerate(rows):
            if r["t"] < free or not entry_ok(r) or i == len(rows) - 1:
                continue
            res = {n: run(rows, i, v) for n, v in EXITS.items()}
            sigs.append({"k": k, "sym": r["sym"], "t": r["t"], "h6": r["h6"], "res": res,
                         "after_h": (rows[-1]["t"] - r["t"]) / 3600})
            free = res["never sell early"][1] + 86400
    t0 = min(s["t"] for s in sigs)
    t1 = max(s["t"] for s in sigs)
    print(f"scanner log {paths[0][-16:-7]} .. {paths[-1][-16:-7]}: {len(by):,} pairs; {len(sigs)} live-entry trades "
          f"{datetime.fromtimestamp(t0, timezone.utc):%m-%d %H:%M} .. {datetime.fromtimestamp(t1, timezone.utc):%m-%d %H:%M}; "
          f"median time watched after entry {statistics.median(s['after_h'] for s in sigs):.0f}h")
    print("\n1. EXITS (each trade = $1 stake; sum = total $ per $1 bet on every signal)")
    print(f"  {'exit':<28}{'n':>4}{'mean':>9}{'median':>9}{'win':>6}{'<=-50%':>8}{'rug':>6}{'sum':>9}   peaked>=2x: n / closed<0")
    for n in EXITS:
        xs = [s["res"][n][0] for s in sigs]
        d2 = [s["res"][n] for s in sigs if s["res"][n][2] >= 2]
        print(f"  {n:<28}{len(xs):>4}{statistics.fmean(xs):>+9.1%}{statistics.median(xs):>+9.1%}"
              f"{sum(x > 0 for x in xs) / len(xs):>6.0%}{sum(x <= -0.5 for x in xs) / len(xs):>8.0%}"
              f"{sum(s['res'][n][3] == 'rug' for s in sigs):>6}{sum(xs):>+9.2f}   {len(d2)} / {sum(r[0] < 0 for r in d2)}")
    mid = sorted(s["t"] for s in sigs)[len(sigs) // 2]
    print("\n   by half (sum per $1 bet):  older / newer")
    for n in EXITS:
        a = sum(s["res"][n][0] for s in sigs if s["t"] < mid)
        b = sum(s["res"][n][0] for s in sigs if s["t"] >= mid)
        print(f"  {n:<28}{a:>+8.2f} / {b:>+8.2f}")
    for lab, ok in (("6h >= +50% only", lambda x: (x["h6"] or 0) >= 0.5), ("6h < +50%", lambda x: (x["h6"] or 0) < 0.5)):
        sub = [x for x in sigs if ok(x)]
        print(f"\n   {lab}: {len(sub)} trades (sum per $1 bet, older / newer half)")
        for n in EXITS:
            xs = [x["res"][n][0] for x in sub]
            a = sum(x["res"][n][0] for x in sub if x["t"] < mid)
            b = sum(x["res"][n][0] for x in sub if x["t"] >= mid)
            print(f"  {n:<28} mean {statistics.fmean(xs):>+7.1%}  median {statistics.median(xs):>+7.1%}  "
                  f"sum {sum(xs):>+6.2f}  ({a:+.2f} / {b:+.2f})")
    print("\n2. ENTRY: by the 6h move before the signal (live exit = stake back at 2x)")
    for lo, hi in ((-9, -0.4), (-0.4, -0.2), (-0.2, 0), (0, 0.5), (0.5, 2), (2, 1e9)):
        xs = [s["res"]["stake back at 2x (live)"][0] for s in sigs if s["h6"] is not None and lo <= s["h6"] < hi]
        if xs:
            print(f"  6h {lo:>+6.0%} .. {hi:>+6.0%}: n {len(xs):>3}  mean {statistics.fmean(xs):>+7.1%}  "
                  f"median {statistics.median(xs):>+7.1%}  win {sum(x > 0 for x in xs) / len(xs):.0%}  "
                  f"<=-50% {sum(x <= -0.5 for x in xs) / len(xs):.0%}  sum {sum(xs):+.2f}")
    print("\n3. BIGGEST WINNERS / LOSERS (live exit)")
    srt = sorted(sigs, key=lambda s: s["res"]["stake back at 2x (live)"][0])
    for s in srt[:8] + srt[-8:]:
        r = s["res"]["stake back at 2x (live)"]
        print(f"  {s['sym'][:14]:<15}{datetime.fromtimestamp(s['t'], timezone.utc):%m-%d %H:%M}  6h {s['h6'] or 0:>+7.0%}  "
              f"peak {r[2]:>6.2f}x  live {r[0]:>+7.1%} ({r[3]})  never-sell {s['res']['never sell early'][0]:>+7.1%}")


if __name__ == "__main__":
    main()
