"""DEX: should a held coin be sold when its re-screen keeps saying "rugcheck lp locked 0% < 95%"?   (2026-11-27, after XTO)

Counts back every DEX position ever held (all seasons' trades.csv) that got that flag while held:
  group HELD  - the flag was ignored (experiment 10, from 2026-10-06, and the 09-27 19:20 .. 09-28 05:40 window):
                what would "sell at LP-0% flag #N" have got?   Price at the flag = the coin's own trades /
                snapshots around that time (data/dex/wallet_trades*.csv.gz, data/dex/snapshots.csv).
  group SOLD  - the old two-strike rule sold it on the flag (seasons 1-2): what would holding have got?  The later
                price path is walked with today's sell rules (80% at 5x, after 3x a 40% drop sells, 7-day limit,
                a path that ends near zero = rugged).
Flag times come from data/run_logs/*.gz + data/run.log (each line is stamped with the last "[... UTC]" header).
Every rule is compared with the CURRENT rule (never sell on this flag) in total and in two time halves.
Writes results/dex_lpflag_study.txt.     python dex_lpflag_study.py"""
import bisect
import csv
import glob
import gzip
import os
import re
import statistics
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
COST = 0.013                      # fee + slippage per side (config.DEX["cost"])
LP0 = "lp locked 0%"
FMT = "%Y-%m-%d %H:%M"


def T(s):
    return datetime.strptime(s[:16].replace("T", " "), FMT)


def load_flags():
    """-> {coin key: [(time, kind, n, why)]}; kind 'hold' (experiment 10 line) or 'once' (two-strike first flag)."""
    ev, now = {}, None
    files = sorted(glob.glob(f"{ROOT}/data/run_logs/*.gz")) + [f"{ROOT}/data/run.log"]
    for f in files:
        op = gzip.open if f.endswith(".gz") else open
        with op(f, "rt", errors="ignore") as fh:
            for line in fh:
                if line.startswith("[20"):
                    try:
                        now = T(line[1:17])
                    except ValueError:
                        pass
                    continue
                if "dex re-screen" not in line or now is None:
                    continue
                m = re.search(r"dex re-screen: (\S+) data flag #(\d+) \((.*)\); holding", line)
                if m:
                    ev.setdefault(m.group(1), []).append((now, "hold", int(m.group(2)), m.group(3)))
                    continue
                m = re.search(r"dex re-screen: (\S+) flagged once \((.*)\); re-checking", line)
                if m:
                    ev.setdefault(m.group(1), []).append((now, "once", 1, m.group(2)))
    return ev


def is_survivor(why):
    """Survivor-rule buy: mode 'survivor', or mode 'both' with a quiet hour (1h < +10% = not the fresh-pump rule)."""
    m = re.search(r"1h ([+-]\d+)%", why)
    return " survivor " in why or (" both " in why and m is not None and int(m.group(1)) < 10)


def load_positions():
    """Every position from every season's trades.csv -> list of dicts (one per buy..flat episode)."""
    rows, addr = [], {}
    for f in glob.glob(f"{ROOT}/data/dex/**/trades.csv", recursive=True):
        with open(f) as fh:
            rows += [dict(r, file=f) for r in csv.DictReader(fh)]
    for f in glob.glob(f"{ROOT}/data/dex/**/outcomes.csv", recursive=True):
        with open(f) as fh:
            for r in csv.DictReader(fh):
                addr[r["coin"]] = r["address"]
    rows.sort(key=lambda r: r["time"])
    open_, out = {}, []
    for r in rows:
        k = r["coin"]
        if r["side"] == "BUY":
            p = open_.get(k)
            if not p:
                p = open_[k] = {"key": k, "t0": T(r["time"]), "entry": float(r["price"]), "cost": 0.0, "qty": 0.0,
                                "pnl": 0.0, "sells": [], "why_buy": r["reason"], "addr": addr.get(k)}
                out.append(p)
            p["cost"] += float(r["usd"]) + float(r["fee"])
            p["qty"] += float(r["qty"])
        elif k in open_:
            p = open_[k]
            p["pnl"] += float(r["pnl"] or 0)
            p["sells"].append((T(r["time"]), float(r["price"]), float(r["qty"]), r["reason"]))
            p["qty"] -= float(r["qty"])
            if p["qty"] <= p["sells"][-1][2] * 1e-6:
                p["t1"] = T(r["time"])
                del open_[k]
    return [p for p in out if "t1" in p]           # closed positions only


def load_prices(prefixes):
    """-> {addr prefix: sorted [(time, price, liq or None)]} from snapshots + the wallet tracker's trades."""
    px = {p: [] for p in prefixes}
    plen = sorted({len(p) for p in prefixes})

    def hit(a):
        for n in plen:
            if a[:n] in px:
                return a[:n]
    with open(f"{ROOT}/data/dex/snapshots.csv") as fh:
        for r in csv.DictReader(fh):
            k = hit(r["addr"])
            if k:
                try:
                    px[k].append((T(r["time"]), float(r["price"]), float(r["liq"] or 0)))
                except ValueError:
                    pass
    for f in glob.glob(f"{ROOT}/data/dex/wallet_trades*.csv.gz"):
        with gzip.open(f, "rt", errors="ignore") as fh:
            for line in fh:
                c = line.rstrip("\n").split(",")
                if len(c) < 10 or c[0] == "time":
                    continue
                k = hit(c[3])
                if k:
                    try:
                        px[k].append((T(c[0]), float(c[8]), None))
                    except ValueError:
                        pass
    for v in px.values():
        v.sort(key=lambda x: x[0])
    return px


def price_at(series, t, win_h=3):
    """Median price within +-30 min of t; else the last print in the win_h hours before t; else the first print in
    the win_h hours after it; else None."""
    if not series:
        return None
    ts = [x[0] for x in series]
    lo, hi = bisect.bisect_left(ts, t - timedelta(minutes=30)), bisect.bisect_right(ts, t + timedelta(minutes=30))
    near = [x[1] for x in series[lo:hi] if x[1] > 0]
    if near:
        hi2 = bisect.bisect_right(ts, t + timedelta(minutes=90))
        after = [x[1] for x in series[hi:hi2] if x[1] > 0]         # fill at the lower of two looks (no lucky ticks)
        return min(statistics.median(near), statistics.median(after)) if after else statistics.median(near)
    i = bisect.bisect_right(ts, t) - 1
    if i >= 0 and t - ts[i] <= timedelta(hours=win_h) and series[i][1] > 0:
        return series[i][1]
    if i + 1 < len(ts) and ts[i + 1] - t <= timedelta(hours=win_h) and series[i + 1][1] > 0:
        return series[i + 1][1]
    return None


def hold_sim(series, entry, qty, t_from, t0, days=7, floor=None):
    """What the coins are worth if kept from t_from under today's sell rules -> (usd back, note).  Hourly medians of
    the path; 80% out at 5x, after 3x a 40% drop from the high sells, at buy + `days` sell (a 2x+ coin: 40% trail).
    A path that stops with the last price < 10% of the entry counts as zero (rugged / dumped)."""
    hours = {}
    for t, p, _ in series:
        if t > t_from and p > 0:
            hours.setdefault(t.replace(minute=0), []).append(p)
    path = [(h, statistics.median(v)) for h, v in sorted(hours.items())]
    if not path:
        return None, "no later prices"
    back, left, hi, limit, runner = 0.0, 1.0, entry, t0 + timedelta(days=days), False
    for h, p in path:
        hi = max(hi, p)
        if floor and p < floor * entry:           # the flag repeats every 30 min: sold once the price is under the bar
            return back + left * qty * p * (1 - COST), f"flag again under {floor}x ({p / entry:.2f}x)"
        if left == 1.0 and p >= 5 * entry:
            back += 0.8 * qty * 5 * entry * (1 - COST)
            left = 0.2
        if hi >= 3 * entry and p <= hi * 0.6:
            return back + left * qty * p * (1 - COST), f"3x then -40% ({p / entry:.2f}x)"
        if h >= limit:
            if p >= 2 * entry or left < 1.0:
                runner = True
            if not runner:
                return back + left * qty * p * (1 - COST), f"day {days} ({p / entry:.2f}x)"
            if p <= hi * 0.6:
                return back + left * qty * p * (1 - COST), f"runner -40% ({p / entry:.2f}x)"
    p = path[-1][1]
    if p < 0.1 * entry:
        return back, f"path ends ~0 ({p / entry:.2f}x)"
    return back + left * qty * p * (1 - COST), f"path ends {path[-1][0]:%m-%d} ({p / entry:.2f}x)"


def build():
    flags, pos = load_flags(), load_positions()
    prefixes = {p["key"].split(":")[1] for p in pos}
    px = load_prices(prefixes)
    out = []
    for p in pos:
        ser = px[p["key"].split(":")[1]]
        qty0 = sum(q for _, _, q, _ in p["sells"])
        evs = [e for e in flags.get(p["key"], []) if p["t0"] <= e[0] <= p["t1"] + timedelta(minutes=5) and LP0 in e[3]]
        sold_on = next((s for s in p["sells"] if s[3].startswith("re-screen flagged") and LP0 in s[3]
                        and "Low Liquidity" not in s[3] and "Missing metadata" not in s[3]), None)
        first_sell = min(s[0] for s in p["sells"])
        row = {"key": p["key"], "sym": p["key"].split("@")[0], "t0": p["t0"], "cost": p["cost"], "pnl": p["pnl"],
               "entry": p["entry"], "pump": p["key"].split("@")[1].startswith("solana") and (p["addr"] or "").endswith("pump"),
               "chain": p["key"].split("@")[1].split(":")[0], "survivor": is_survivor(p["why_buy"]), "n_flags": len(evs)}
        if sold_on and sold_on[0] == first_sell and sold_on[2] >= qty0 * 0.999:
            # SOLD group: the two-strike rule sold everything here.  rule "flag 2" = what happened; current = hold
            back, note = hold_sim(ser, p["entry"], qty0, sold_on[0], p["t0"])
            if back is None:
                continue
            row.update(group="SOLD", x2=sold_on[1] / p["entry"], sell2=p["pnl"], hold=back - p["cost"], note=note,
                       t2=sold_on[0])
            for thr in (1.0, 1.5):
                b2, _ = hold_sim(ser, p["entry"], qty0, sold_on[0], p["t0"], floor=thr)
                row[f"keep{thr}"] = b2 - p["cost"]
            once = [e for e in evs if e[1] == "once"]
            p1 = price_at(ser, once[-1][0]) if once else None
            row["x1"] = p1 / p["entry"] if p1 else row["x2"]
            row["x3"] = None
        elif evs:
            # HELD group: flags ignored.  current = what happened; rule "flag N" = sell at the Nth LP-0% flag
            evs = [e for e in evs if e[0] < first_sell]
            if not evs:
                continue
            row.update(group="HELD", hold=p["pnl"], note=p["sells"][-1][3][:38])
            for n in (1, 2, 3):
                # the engine's own counter (flags in a row; a clean re-screen resets it).  Before experiment 10 the
                # two-strike rule was live, so a coin still held then never had two in a row: only #1 exists
                e = next((e for e in evs if (e[1] == "hold" and e[2] >= n) or n == 1), None)
                pr = price_at(ser, e[0]) if e else None
                row[f"x{n}"] = pr / p["entry"] if pr else None
                row[f"t{n}"] = e[0] if e else None
            row["qty"] = qty0
            row["later"] = [price_at(ser, e[0]) for e in evs if e[1] == "hold" and e[2] >= 2]
            row["later"] = [x / p["entry"] for x in row["later"] if x]
        else:
            continue
        out.append(row)
    return sorted(out, key=lambda r: r["t0"]), pos


def rule_pnl(r, n, cond):
    """P/L of 'sell at LP-0% flag #n if cond(x)' for one coin; falls back to the current rule (hold) when the flag
    never came, the price at the flag is unknown, or the condition is not met."""
    x = r.get(f"x{n}")
    if r["group"] == "SOLD":
        if n == 3 or x is None:
            x = r["x2"]                           # two-strike sale price stands in (flag 3 came ~30 min later)
        if not cond(r, x):
            return r["hold"]
        return r["sell2"] if n >= 2 else r["cost"] * (x * (1 - COST) - 1)
    if x is None or not cond(r, x):
        return r["hold"]
    return r["cost"] * (x * (1 - COST) - 1)


def keep_runner(thr):
    """'From flag #2 on, sell at the first LP-0% flag where the coin is under thr x its buy price' - a coin above the
    bar keeps riding and is sold when a later flag finds it back under the bar."""
    def f(r):
        if r["group"] == "SOLD":
            return r["sell2"] if r["x2"] < thr else r[f"keep{thr}"]
        x = next((x for x in r.get("later", []) if x < thr), None)
        return r["hold"] if x is None else r["cost"] * (x * (1 - COST) - 1)
    return f


RULES = [
    ("sell at flag #1", 1, lambda r, x: True),
    ("sell at flag #2", 2, lambda r, x: True),
    ("sell at flag #3", 3, lambda r, x: True),
    ("flag #2, only if below entry", 2, lambda r, x: x < 1.0),
    ("flag #2, only if below 1.5x", 2, lambda r, x: x < 1.5),
    ("flag #2, only if at/above entry", 2, lambda r, x: x >= 1.0),
    ("flag #3, only if below entry", 3, lambda r, x: x < 1.0),
    ("flag #2, only pump.fun", 2, lambda r, x: r["pump"]),
    ("flag #2, only Solana", 2, lambda r, x: r["chain"] == "solana"),
    ("flag #2, pump.fun and below entry", 2, lambda r, x: r["pump"] and x < 1.0),
    ("from flag #2: sell when under 1.0x", keep_runner(1.0), None),
    ("from flag #2: sell when under 1.5x", keep_runner(1.5), None),
]


def report(rows, pos):
    L = []
    w = L.append
    w("DEX LP-flag study (dex_lpflag_study.py) - sell a held coin on repeated 'rugcheck lp locked 0%' flags?")
    w(f"positions ever closed: {len(pos)};  with the LP-0% flag while held and a usable price path: {len(rows)}")
    w("")
    w("x1/x2/x3 = price at LP-0% flag #1/#2/#3 as a multiple of the buy price; hold = P/L of never selling on the flag")
    w("(HELD: what really happened; SOLD: later path walked with today's sell rules); sell2 = P/L of selling at flag #2.")
    w(f"{'coin':11}{'bought':12}{'grp':5}{'pump':5}{'surv':5}{'cost':>6}{'flags':>6}{'x1':>6}{'x2':>6}{'x3':>6}{'hold':>8}{'sell2':>8}  note")
    for r in rows:
        f = lambda v: "   - " if v is None else f"{v:5.2f}"
        w(f"{r['sym'][:10]:11}{r['t0']:%m-%d %H:%M} {r['group']:5}{'y' if r['pump'] else 'n':5}{'y' if r['survivor'] else 'n':5}"
          f"{r['cost']:6.0f}{r['n_flags']:6d} {f(r.get('x1'))} {f(r.get('x2'))} {f(r.get('x3'))}{r['hold']:8.1f}"
          f"{rule_pnl(r, 2, lambda r, x: True):8.1f}  {r['note']}")
    mid = rows[len(rows) // 2]["t0"]
    h1, h2 = [r for r in rows if r["t0"] < mid], [r for r in rows if r["t0"] >= mid]
    w("")
    w(f"halves by buy time: older n {len(h1)} (to {mid:%m-%d %H:%M}), newer n {len(h2)}.  P/L in $; 'vs' = rule minus current.")
    w(f"{'rule':38}{'total':>9}{'vs':>8}{'older vs':>10}{'newer vs':>10}{'sold':>6}{'cost on winners':>17}{'saved on losers':>17}{'$1 older':>9}{'$1 newer':>9}  wins both")
    base = sum(r["hold"] for r in rows)
    w(f"{'CURRENT (never sell on the flag)':38}{base:9.1f}")
    res = {}
    for name, n, cond in RULES:
        d = [(r, (n(r) if cond is None else rule_pnl(r, n, cond)) - r["hold"]) for r in rows]
        tot = sum(x for _, x in d)
        a, b = sum(x for r, x in d if r["t0"] < mid), sum(x for r, x in d if r["t0"] >= mid)
        sold = sum(1 for _, x in d if abs(x) > 1e-9)
        lost = sum(x for r, x in d if r["hold"] > 0)
        saved = sum(x for r, x in d if r["hold"] <= 0)
        pa = sum(x / r["cost"] for r, x in d if r["t0"] < mid) / max(1, len(h1))      # per $1 bet (equal weight)
        pb = sum(x / r["cost"] for r, x in d if r["t0"] >= mid) / max(1, len(h2))
        ok = tot > 0 and a > 0 and b > 0 and pa > 0 and pb > 0
        res[name] = (tot, a, b, lost, saved, ok)
        w(f"{name:38}{base + tot:9.1f}{tot:+8.1f}{a:+10.1f}{b:+10.1f}{sold:6d}{lost:+17.1f}{saved:+17.1f}"
          f"{pa:+9.2f}{pb:+9.2f}  {'YES' if ok else 'no'}")
    w("")
    for g in ("HELD", "SOLD"):
        s = [r for r in rows if r["group"] == g]
        w(f"{g}: n {len(s)}, hold {sum(r['hold'] for r in s):+.1f}, sell at flag #2 {sum(rule_pnl(r, 2, lambda r, x: True) for r in s):+.1f}, "
          f"flag #2 only below entry {sum(rule_pnl(r, 2, lambda r, x: x < 1.0) for r in s):+.1f}")
    kr = keep_runner(1.5)
    w("'from flag #2: sell when under 1.5x' by coin (rule minus current), biggest costs: " + ", ".join(
        f"{r['sym']} {kr(r) - r['hold']:+.0f}" for r in sorted(rows, key=lambda r: kr(r) - r["hold"])[:5])
      + ";  biggest saves: " + ", ".join(
        f"{r['sym']} {kr(r) - r['hold']:+.0f}" for r in sorted(rows, key=lambda r: r["hold"] - kr(r))[:6]))
    w("biggest costs of 'sell at flag #2' (runners it sells): " + ", ".join(
        f"{r['sym']} {rule_pnl(r, 2, lambda r, x: True) - r['hold']:+.0f} (flag at {r.get('x2') or 0:.2f}x)"
        for r in sorted(rows, key=lambda r: rule_pnl(r, 2, lambda r, x: True) - r["hold"])[:5]))
    keys = {r["key"] for r in rows}
    rest = [p for p in pos if p["key"] not in keys]
    w("")
    w(f"for scale - positions with NO LP-0% flag while held: n {len(rest)}, cost ${sum(p['cost'] for p in rest):.0f}, "
      f"P/L {sum(p['pnl'] for p in rest):+.1f};  flagged ones above: cost ${sum(r['cost'] for r in rows):.0f}, P/L (current rule) {base:+.1f}")
    fl = {r["key"]: r for r in rows}
    w("biggest live winners, and did they carry the flag?  " + "; ".join(
        f"{p['key'].split('@')[0]} {p['pnl']:+.0f} ({'LP-0% flags ' + str(fl[p['key']]['n_flags']) if p['key'] in fl else 'no LP-0% flag'})"
        for p in sorted(pos, key=lambda p: -p["pnl"])[:8]))
    return "\n".join(L), res


def survivor_pump(pos):
    """Survivor-rule buys by pump.fun or not (live, all seasons)."""
    L = ["", "Survivor-rule buys, pump.fun (Solana address ending 'pump') vs the rest - live, all seasons:"]
    for lab, f in (("pump.fun", lambda p: p["pump"]), ("Solana, not pump.fun", lambda p: p["sol"] and not p["pump"]),
                   ("Base / Ethereum", lambda p: not p["sol"])):
        s = [p for p in pos if is_survivor(p["why_buy"]) and f(p)]
        c = sum(p["cost"] for p in s)
        L.append(f"  {lab:22} n {len(s):2d}  cost ${c:6.0f}  P/L {sum(p['pnl'] for p in s):+7.1f}"
                 f"  ({(sum(p['pnl'] for p in s) / c * 100 if c else 0):+.0f}%)  "
                 + ", ".join(f"{p['key'].split('@')[0]} {p['pnl']:+.0f}" for p in s))
    return "\n".join(L)


def survivor_replay():
    """Scanner replay of the survivor entry (2-6 days old, $250k+, liquidity +20% in 24h, price up on the day and
    within 30% of the high seen), first hour a pool meets it, live exit over 7 days (dex_entry_grid_study.sim).
    No scam screen is modelled.  Split pump.fun vs the rest, two time halves."""
    import dex_entry_grid_study as G
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        data = G.load()
    finally:
        os.chdir(cwd)
    tmax = max(s[-1][0] for s in data.values())
    ent = []
    for (chain, addr), s in data.items():
        hi = 0.0
        for i, (t, r, p, l) in enumerate(s):
            hi = max(hi, p)
            age = G.F(r["age_h"])
            if age is None or not 48 <= age <= 144 or l < 250_000 or tmax - t < 3 * 86400:
                continue
            old = [x for x in s[:i] if 24 * 3600 <= t - x[0] <= 30 * 3600]
            if not old or l < old[-1][3] * 1.2 or p < old[-1][2] or p < hi * 0.7:
                continue
            path = [(tt, pp, ll) for tt, _, pp, ll in s[i + 1:] if tt - t <= 7 * 86400]
            horizon = min(t + 7 * 86400, tmax)
            if not path or horizon - path[-1][0] > 24 * 3600:
                path = path + [(horizon, 0.0, 0.0)]
            x = G.sim(path, p, l)
            if x is not None:
                ent.append((t, chain, chain == "solana" and addr.endswith("pump"), x))
            break
    ent.sort()
    L = ["", f"Survivor rule on the scanner log (data/dex/scan, no scam screen), live exit, per $1 bet - n {len(ent)}:"]
    if not ent:
        return "\n".join(L)
    mid = ent[len(ent) // 2][0]
    for lab, f in (("pump.fun", lambda e: e[2]), ("Solana, not pump.fun", lambda e: e[1] == "solana" and not e[2]),
                   ("Base / Ethereum", lambda e: e[1] != "solana"), ("all", lambda e: True)):
        a, b = [e[3] - 1 for e in ent if f(e) and e[0] < mid], [e[3] - 1 for e in ent if f(e) and e[0] >= mid]
        m = lambda v: f"{sum(v) / len(v):+.2f} (n {len(v)}, lost 80%+ {sum(x <= -0.8 for x in v)}, 2x+ {sum(x >= 1 for x in v)})" if v else "-"
        L.append(f"  {lab:22} older {m(a):42} newer {m(b)}")
    return "\n".join(L)


def main():
    rows, pos = build()
    for p in pos:
        p["sol"] = p["key"].split("@")[1].startswith("solana")
        p["pump"] = p["sol"] and (p["addr"] or "").endswith("pump")
    txt, _ = report(rows, pos)
    txt += "\n" + survivor_pump(pos) + "\n" + survivor_replay()
    print(txt)
    with open(f"{ROOT}/results/dex_lpflag_study.txt", "w") as f:
        f.write(txt + "\n")


if __name__ == "__main__":
    main()
