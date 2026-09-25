"""Paper portfolio + decision loop. Shared by the backtester and the live runner,
so what you backtest is exactly what runs live."""
import csv
import json
import os
from datetime import datetime, timezone

import config
from strategy import analyze


def ts(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")


class Portfolio:
    def __init__(self, cash=config.STARTING_CASH_USD):
        self.cash = cash
        self.positions = {}   # coin -> {qty, entry, stop, peak, took_profit, opened}
        self.peak_equity = cash
        self.cooldown = {}    # coin -> ms timestamp until which we skip it
        self.trades = []
        self.halted = False
        self.halt_until = 0

    # ---- persistence ----
    def to_dict(self):
        return {k: getattr(self, k) for k in ("cash", "positions", "peak_equity", "cooldown", "halted", "halt_until")}

    @classmethod
    def load(cls, path):
        p = cls()
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

    def buy(self, t, coin, usd, price, atr_):
        fill = price * (1 + config.SLIPPAGE_RATE)
        fee = usd * config.FEE_RATE
        qty = (usd - fee) / fill
        self.cash -= usd
        self.positions[coin] = {"qty": qty, "entry": fill, "cost": usd, "peak": fill,
                                "stop": fill - config.STOP_ATR_MULT * atr_,
                                "took_profit": False, "opened": t}
        self._record(t, "BUY", coin, qty, fill, fee, "trend entry")

    def sell(self, t, coin, frac, price, reason):
        pos = self.positions[coin]
        qty = pos["qty"] * frac
        fill = price * (1 - config.SLIPPAGE_RATE)
        gross = qty * fill
        fee = gross * config.FEE_RATE
        cost = pos["cost"] * frac
        self.cash += gross - fee
        pnl = gross - fee - cost
        pos["qty"] -= qty
        pos["cost"] -= cost
        if frac >= 0.999:
            del self.positions[coin]
        self._record(t, "SELL", coin, qty, fill, fee, reason, pnl)
        return pnl


def step(pf, candles_by_coin):
    """One decision cycle. candles_by_coin: {coin: [candles oldest-first]}."""
    sig = {c: analyze(cs) for c, cs in candles_by_coin.items()}
    sig = {c: s for c, s in sig.items() if s}
    if not sig:
        return
    now = max(s["t"] for s in sig.values())
    prices = {c: s["price"] for c, s in sig.items()}

    # 1) Manage open positions: stops, partial take-profit, trend exit.
    for coin in list(pf.positions):
        s = sig.get(coin)
        if not s:
            continue
        pos = pf.positions[coin]
        if s["low"] <= pos["stop"]:
            exit_px = min(pos["stop"], s["price"]) if s["price"] < pos["stop"] else pos["stop"]
            pnl = pf.sell(now, coin, 1.0, exit_px, "stop hit")
            if pnl < 0:
                pf.cooldown[coin] = now + config.COOLDOWN_CANDLES * 3_600_000
            continue
        if s["trend_broken"]:
            pf.sell(now, coin, 1.0, s["price"], "trend reversed")
            continue
        if not pos["took_profit"] and s["price"] >= pos["entry"] + config.TAKE_PROFIT_ATR_MULT * s["atr"]:
            pf.sell(now, coin, 0.5, s["price"], "take half profit")
            pos["took_profit"] = True
            pos["stop"] = max(pos["stop"], pos["entry"])  # rest of trade can't lose
        pos["peak"] = max(pos["peak"], s["high"])
        pos["stop"] = max(pos["stop"], pos["peak"] - config.TRAIL_ATR_MULT * s["atr"])

    # 2) Drawdown circuit breaker.
    eq = pf.equity(prices)
    pf.peak_equity = max(pf.peak_equity, eq)
    if not pf.halted and eq < pf.peak_equity * (1 - config.MAX_DRAWDOWN_HALT):
        pf.halted, pf.halt_until = True, now + config.HALT_HOURS * 3_600_000
    if pf.halted:
        if now < pf.halt_until:
            return
        pf.halted, pf.peak_equity = False, eq  # pause over: reset the high-water mark

    # 3) New entries: strongest momentum first.
    cands = sorted((c for c, s in sig.items() if s["buy"] and c not in pf.positions
                    and pf.cooldown.get(c, 0) <= now),
                   key=lambda c: sig[c]["momentum"], reverse=True)
    for coin in cands:
        if len(pf.positions) >= config.MAX_POSITIONS:
            break
        s = sig[coin]
        stop_dist = config.STOP_ATR_MULT * s["atr"] / s["price"]
        usd = min(eq * config.RISK_PER_TRADE / max(stop_dist, 1e-9),
                  eq * config.MAX_POSITION_PCT,
                  pf.cash - eq * config.MIN_CASH_RESERVE_PCT)
        if usd >= config.MIN_ORDER_USD:
            pf.buy(now, coin, usd, s["price"], s["atr"])


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
