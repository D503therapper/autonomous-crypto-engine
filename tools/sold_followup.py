"""Was each DEX sale a good call?  For every closed DEX trade, compare the sell price with the
coin's later prices (from data/dex/snapshots.csv): latest, highest and lowest since the sale.
Writes results/sold_followup.txt.   python tools/sold_followup.py"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "dex", "outcomes.csv")
SNAP = os.path.join(ROOT, "data", "dex", "snapshots.csv")


def rows(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def followup(outcomes, snaps):
    """-> [(outcome row, after-sale info or None)]; 'kept' = what the sold stake would be worth now."""
    by_addr = {}
    for s in snaps:
        try:
            by_addr.setdefault(s["addr"], []).append((s["time"], float(s["price"])))
        except (KeyError, ValueError):
            continue
    res = []
    for o in outcomes:
        sold_at, px = o["time"], float(o["exit"])
        later = [p for t, p in by_addr.get(o["address"], []) if t > sold_at and p > 0]
        if not later or px <= 0:
            res.append((o, None))
            continue
        stake = float(o["cost_usd"]) + float(o["pnl"])          # what we got back
        res.append((o, {"now": later[-1] / px - 1, "high": max(later) / px - 1,
                        "low": min(later) / px - 1, "kept": stake * (later[-1] / px - 1)}))
    return res


def report(res):
    lines = ["Was each DEX sale a good call?  (+ = price rose after we sold)", ""]
    total = 0.0
    for o, a in res:
        name = o["coin"].split("@")[0]
        head = f"{o['time']}  {name:<10} sold {float(o['pnl']):+8.2f}  ({o['outcome']})"
        if a is None:
            lines.append(head + "  - no prices after the sale yet")
            continue
        total += a["kept"]
        verdict = "GOOD SELL" if a["now"] <= 0 else "SOLD TOO EARLY"
        lines.append(f"{head}  since: now {a['now']:+.0%}, high {a['high']:+.0%}, low {a['low']:+.0%}"
                     f"  -> holding would be {a['kept']:+.2f}  {verdict}")
    lines += ["", f"Net: holding everything we sold would be {total:+.2f} vs selling."]
    return "\n".join(lines)


if __name__ == "__main__":
    text = report(followup(rows(OUT), rows(SNAP)))
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "sold_followup.txt"), "w") as f:
        f.write(text + "\n")
    print(text)
