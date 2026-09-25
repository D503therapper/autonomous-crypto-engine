"""Paper portfolio + decision loop. Shared by the backtester and the live runner,
so what you backtest is exactly what runs live."""
import csv
import json
import os
from datetime import datetime, timezone

import config


def ts(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")


class Portfolio:
    def __init__(self, cash=config.STARTING_CASH_USD, fee=config.FEE_RATE, slippage=config.SLIPPAGE_RATE):
        self.fee, self.slippage = fee, slippage   # per market; not saved
        self.last_rebalance_week = None
        self.cash = cash
        self.positions = {}   # coin -> {qty, entry, stop, peak, took_profit, opened}
        self.peak_equity = cash
        self.cooldown = {}    # coin -> ms timestamp until which we skip it
        self.trades = []
        self.halted = False
        self.halt_until = 0

    # ---- persistence ----
    def to_dict(self):
        return {k: getattr(self, k) for k in ("cash", "positions", "peak_equity", "cooldown", "halted", "halt_until",
                                                   "last_rebalance_week")}

    @classmethod
    def load(cls, path, **kw):
        p = cls(**kw)
        if os.path.exists(path):
            with open(path) as f:
                for k, v in json.load(f).items():
                    setattr(p, k, v)
        return p

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    # ---- accounting ----
    def equity(self, prices):
        return self.cash + sum(p["qty"] * prices.get(c, p["entry"]) for c, p in self.positions.items())

    def _record(self, t, side, coin, qty, price, fee, reason, pnl=None):
        self.trades.append({"time": ts(t), "side": side, "coin": coin, "qty": round(qty, 8),
                            "price": round(price, 6), "usd": round(qty * price, 2),
                            "fee": round(fee, 2), "pnl": None if pnl is None else round(pnl, 2),
                            "reason": reason})

    def buy(self, t, coin, usd, price, stop):
        fill = price * (1 + self.slippage)
        fee = usd * self.fee
        qty = (usd - fee) / fill
        self.cash -= usd
        self.positions[coin] = {"qty": qty, "entry": fill, "cost": usd, "peak": fill,
                                "stop": stop,
                                "took_profit": False, "opened": t}
        self._record(t, "BUY", coin, qty, fill, fee, "entry")

    def sell(self, t, coin, frac, price, reason):
        pos = self.positions[coin]
        qty = pos["qty"] * frac
        fill = price * (1 - self.slippage)
        gross = qty * fill
        fee = gross * self.fee
        cost = pos["cost"] * frac
        self.cash += gross - fee
        pnl = gross - fee - cost
        pos["qty"] -= qty
        pos["cost"] -= cost
        if frac >= 0.999:
            del self.positions[coin]
        self._record(t, "SELL", coin, qty, fill, fee, reason, pnl)
        return pnl


def step(pf, candles_by_coin, strat, market_ok=True):
    """One decision cycle. candles_by_coin: {symbol: [candles oldest-first]}.
    market_ok: benchmark regime (BTC / SPY above its long average)."""
    sig = {c: strat.analyze(cs, market_ok) for c, cs in candles_by_coin.items()}
    sig = {c: s for c, s in sig.items() if s}
    if not sig:
        return
    now = max(s["t"] for s in sig.values())
    prices = {c: s["price"] for c, s in sig.items()}

    # Weekly strategies only rebalance once per ISO week; stops still run every cycle.
    week = datetime.fromtimestamp(now / 1000, timezone.utc).strftime("%G-%V")
    rebalance = strat.weekly and week != pf.last_rebalance_week

    # 1) Manage open positions (the strategy decides stops / profit-taking).
    for coin in list(pf.positions):
        s = sig.get(coin)
        if not s:
            continue
        action = strat.manage(pf.positions[coin], s, now, rebalance)
        if action:
            frac, px, reason = action
            pnl = pf.sell(now, coin, frac, px, reason)
            if frac >= 0.999 and pnl < 0:
                pf.cooldown[coin] = now + config.COOLDOWN_CANDLES * 3_600_000

    # 2) Drawdown circuit breaker.
    eq = pf.equity(prices)
    pf.peak_equity = max(pf.peak_equity, eq)
    if config.MAX_DRAWDOWN_HALT and not pf.halted and eq < pf.peak_equity * (1 - config.MAX_DRAWDOWN_HALT):
        pf.halted, pf.halt_until = True, now + config.HALT_HOURS * 3_600_000
    if pf.halted:
        if now < pf.halt_until:
            return
        pf.halted, pf.peak_equity = False, eq  # pause over: reset the high-water mark

    if strat.weekly:
        if not rebalance:
            return
        pf.last_rebalance_week = week

    # 3) New entries, best-ranked first.
    cands = sorted((c for c, s in sig.items() if s["buy"] and c not in pf.positions
                    and pf.cooldown.get(c, 0) <= now),
                   key=lambda c: sig[c]["rank"], reverse=True)
    for coin in cands:
        if len(pf.positions) >= config.MAX_POSITIONS:
            break
        s = sig[coin]
        stop_dist = 1 - s["stop"] / s["price"]
        target = (eq * strat.position_pct if hasattr(strat, "position_pct")
                  else eq * config.RISK_PER_TRADE / max(stop_dist, 1e-9))
        usd = min(target,
                  eq * config.MAX_POSITION_PCT,
                  pf.cash - eq * config.MIN_CASH_RESERVE_PCT)
        if usd >= config.MIN_ORDER_USD:
            pf.buy(now, coin, usd, s["price"], s["stop"])


def append_csv(path, rows):
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if new:
            w.writeheader()
        w.writerows(rows)
