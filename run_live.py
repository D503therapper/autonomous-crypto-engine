"""Forward paper-trading with live prices. Each run = one decision cycle.

    python run_live.py            # one cycle (schedule this hourly)
    python run_live.py --loop     # keep running, one cycle per hour
"""
import argparse
import json
import os
import time

import config
from data_source import CryptoComClient
from engine import Portfolio, append_csv, step, ts


def check_new_listings(client):
    """Crypto has no IPOs; the closest thing is a new coin listing. We flag these
    but never auto-buy them — fresh listings are the most volatile, scam-prone trades."""
    now = client.list_spot_symbols()
    if not os.path.exists(config.LISTINGS_FILE):
        new = []
    else:
        with open(config.LISTINGS_FILE) as f:
            new = sorted(set(now) - set(json.load(f)))
    os.makedirs(os.path.dirname(config.LISTINGS_FILE), exist_ok=True)
    with open(config.LISTINGS_FILE, "w") as f:
        json.dump(now, f)
    return new


def cycle(client):
    pf = Portfolio.load(config.STATE_FILE)
    data = {}
    for coin in config.UNIVERSE:
        try:
            data[coin] = client.candles(coin)
        except Exception as e:
            print(f"  skip {coin}: {e}")
    n_before = len(pf.trades)
    step(pf, data)
    prices = {c: cs[-1]["c"] for c, cs in data.items() if cs}
    eq = pf.equity(prices)
    now = int(time.time() * 1000)
    append_csv(config.TRADE_LOG, pf.trades[n_before:])
    append_csv(config.EQUITY_LOG, [{"time": ts(now), "equity": round(eq, 2),
                                    "cash": round(pf.cash, 2), "positions": len(pf.positions)}])
    pf.save(config.STATE_FILE)

    print(f"[{ts(now)} UTC] equity ${eq:,.2f} ({eq / config.STARTING_CASH_USD - 1:+.1%})  "
          f"cash ${pf.cash:,.2f}{'  [HALTED: drawdown limit]' if pf.halted else ''}")
    for c, p in pf.positions.items():
        px = prices.get(c, p["entry"])
        print(f"   {c:5} {p['qty']:.6g} @ {p['entry']:.6g} -> {px:.6g} "
              f"({px / p['entry'] - 1:+.1%}) stop {p['stop']:.6g}")
    for t in pf.trades[n_before:]:
        print(f"   >> {t['side']} {t['coin']} ${t['usd']:.2f} ({t['reason']})")
    try:
        for coin in check_new_listings(client):
            print(f"   ** NEW LISTING on Crypto.com: {coin} (watch only, not traded)")
    except Exception as e:
        print(f"   listing check failed: {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", action="store_true")
    a = ap.parse_args()
    client = CryptoComClient()
    while True:
        try:
            cycle(client)
        except Exception as e:
            print(f"cycle failed: {e}")
        if not a.loop:
            break
        time.sleep(3600 - time.time() % 3600 + 30)  # wake just after each hourly candle closes
