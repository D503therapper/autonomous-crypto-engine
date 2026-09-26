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
        tmp = path + ".tmp"          # atomic: a kill mid-write must not leave a half-written file
        with open(tmp, "w") as f:    # (an unloadable portfolio.json takes every later fast_check down)
            json.dump(self.to_dict(), f, indent=2)
        os.replace(tmp, path)

    # ---- accounting ----
    def equity(self, prices):
        return self.cash + sum(p["qty"] * prices.get(c, p["entry"]) for c, p in self.positions.items())

    def _record(self, t, side, coin, qty, price, fee, reason, pnl=None):
        self.trades.append({"time": ts(t), "side": side, "coin": coin, "qty": round(qty, 8),
                            "price": round(price, 6), "usd": round(qty * price, 2),
                            "fee": round(fee, 2), "pnl": None if pnl is None else round(pnl, 2),
                            "reason": reason})

    def buy(self, t, coin, usd, price, stop, reason="entry"):
        fill = price * (1 + self.slippage)
        fee = usd * self.fee
        qty = (usd - fee) / fill
        self.cash -= usd
        if coin in self.positions:          # top-up (rebalance_to): average in, keep opened / stop / peak
            pos = self.positions[coin]
            pos["entry"] = (pos["entry"] * pos["qty"] + fill * qty) / (pos["qty"] + qty)
            pos["qty"] += qty
            pos["cost"] += usd
            pos["peak"] = max(pos["peak"], fill)
        else:
            self.positions[coin] = {"qty": qty, "entry": fill, "cost": usd, "peak": fill,
                                    "stop": stop,
                                    "took_profit": False, "opened": t}
        self._record(t, "BUY", coin, qty, fill, fee, reason)

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


def open_trades(pf):
    """Positions that count against a strategy's slots (parked idle cash doesn't)."""
    return sum(1 for p in pf.positions.values() if not p.get("park"))


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
    week = datetime.fromtimestamp(now / 1000, timezone.utc).strftime(getattr(strat, "rebalance_key", "%G-%V"))
    rebalance = strat.weekly and week != pf.last_rebalance_week

    # 1) Manage open positions (the strategy decides stops / profit-taking).
    for coin in list(pf.positions):
        s = sig.get(coin)
        if not s or pf.positions[coin].get("park"):   # parked idle cash (run_live.park_idle) isn't a trade
            continue
        if pf.positions[coin].get("opened", 0) > s["t"]:
            # bought inside this candle at wall-clock time (minute scanner / listing / footprint /
            # social buys) and re-evaluated on it (e.g. a restart within the hour): its high and
            # low may predate the entry, so only the close is a price the position actually saw
            # (no phantom stop-out, no phantom peak for the trailing stop)
            s = dict(s, high=s["price"], low=s["price"])
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

    # Target-weight strategies (stock_strategies.py): the strategy hands back
    # {symbol: fraction of equity}; rebalance_to() does the selling / resizing / buying.
    if hasattr(strat, "targets"):
        rebalance_to(pf, now, strat.targets(sig), sig, getattr(strat, "name", "rebalance"))
        return

    # Rotation strategies: on rebalance, sell holdings that fell out of the top N.
    if getattr(strat, "rotate", False):
        top = sorted((c for c, s in sig.items() if s["buy"]), key=lambda c: sig[c]["rank"],
                     reverse=True)[:strat.max_positions]
        for coin in list(pf.positions):
            if coin in sig and coin not in top:
                pf.sell(now, coin, 1.0, sig[coin]["price"], "rebalance: dropped out of top picks")
        eq = pf.equity(prices)

    # 3) New entries, best-ranked first.
    cands = sorted((c for c, s in sig.items() if s["buy"] and c not in pf.positions
                    and pf.cooldown.get(c, 0) <= now),
                   key=lambda c: sig[c]["rank"], reverse=True)
    veto = getattr(strat, "veto", None)   # optional hook (run_live wires signals.PumpGuard into it)
    for coin in cands:
        if open_trades(pf) >= getattr(strat, "max_positions", config.MAX_POSITIONS):
            break
        s = sig[coin]
        if veto and veto(coin, s):
            continue
        stop_dist = 1 - s["stop"] / s["price"]
        target = (eq * strat.position_pct if hasattr(strat, "position_pct")
                  else eq * config.RISK_PER_TRADE / max(stop_dist, 1e-9))
        usd = min(target,
                  eq * getattr(strat, "max_position_pct", config.MAX_POSITION_PCT),
                  pf.cash - eq * config.MIN_CASH_RESERVE_PCT)
        if usd >= config.MIN_ORDER_USD:
            pf.buy(now, coin, usd, s["price"], s["stop"], reason=s.get("reason", "entry"))


def rebalance_to(pf, now, weights, sig, tag="rebalance", tol=0.02):
    """Move the account to target weights ({symbol: fraction of equity}), as lab.simulate()
    does on a rebalance day: sell what is no longer wanted, trim / top up what stayed when it
    is off target by more than `tol` of equity, buy what is new. Weights are scaled by the
    investable share (1 - MIN_CASH_RESERVE_PCT) so the cash reserve rule still holds.
    Symbols without a signal this cycle (no data) are left untouched."""
    prices = {c: s["price"] for c, s in sig.items()}
    for coin in list(pf.positions):
        if coin not in weights and coin in prices:
            pf.sell(now, coin, 1.0, prices[coin], f"{tag}: dropped from targets")
    eq = pf.equity(prices)
    band, investable = tol * eq, 1 - config.MIN_CASH_RESERVE_PCT
    order = sorted((c for c in weights if c in prices), key=lambda c: -weights[c])

    def gap(coin):
        held = pf.positions[coin]["qty"] * prices[coin] if coin in pf.positions else 0.0
        return weights[coin] * investable * eq - held, held
    for coin in order:                                   # trims first: they free the cash
        delta, held = gap(coin)
        if delta < -band:
            pf.sell(now, coin, min(1.0, -delta / held), prices[coin], f"{tag}: trim to target")
    for coin in order:                                   # then top-ups and new entries
        delta, held = gap(coin)
        if delta > band:
            usd = min(delta, pf.cash - eq * config.MIN_CASH_RESERVE_PCT)
            if usd >= config.MIN_ORDER_USD:
                pf.buy(now, coin, usd, prices[coin], sig[coin]["stop"],
                       reason=f"{tag}: {'top up' if held else 'entry'} {weights[coin]:.0%}")


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
