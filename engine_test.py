"""Runner protection (config.MOON): a coin up big is never sold on a time limit / rule, only on
its trailing stop.   python engine_test.py"""
import config
from engine import Portfolio, step
from strategy import EarlyMover

H = 3_600_000


def bar(t, c, h=None, l=None):
    return {"t": t, "o": c, "h": h or c, "l": l or c, "c": c, "v": 1e6}


class Rule:
    """Holds one coin and wants to sell it every cycle for a non-stop reason."""
    weekly, max_positions, position_pct = False, 1, 0.9
    min_candles, window = 1, 2

    def analyze(self, cs, ok=True):
        return {"t": cs[-1]["t"], "price": cs[-1]["c"], "high": cs[-1]["h"], "low": cs[-1]["l"],
                "buy": False, "rank": 0, "stop": 0.0}

    def manage(self, pos, s, now, rebalance=False):
        return 1.0, s["price"], "time limit"


def held(entry):
    pf = Portfolio()
    pf.buy(0, "X", 400, entry, 0.0)
    return pf


def test_runner_not_sold_on_rules():
    pf = held(1.0)
    step(pf, {"X": [bar(H, 1.8)]}, Rule(), runners=True)        # +80%: runner -> rule sale blocked
    assert "X" in pf.positions
    step(pf, {"X": [bar(2 * H, 2.4)]}, Rule(), runners=True)
    assert "X" in pf.positions


def test_runner_sold_on_trail():
    pf = held(1.0)
    step(pf, {"X": [bar(H, 3.0)]}, Rule(), runners=True)
    step(pf, {"X": [bar(2 * H, 1.6, h=1.6, l=1.4)]}, Rule(), runners=True)   # gave back > 50% of 3.0
    assert "X" not in pf.positions
    assert "runner trail" in pf.trades[-1]["reason"]


def test_non_runner_and_backtests_unchanged():
    pf = held(1.0)
    step(pf, {"X": [bar(H, 1.2)]}, Rule(), runners=True)        # +20%: not a runner, rule sells
    assert "X" not in pf.positions
    pf = held(1.0)
    step(pf, {"X": [bar(H, 1.8)]}, Rule())                      # runners off (backtests): sells
    assert "X" not in pf.positions


def test_early_mover_time_limit_skipped_for_runner():
    st = EarlyMover()
    pf = held(1.0)
    pf.positions["X"]["opened"] = 0
    s = {"t": 30 * H, "price": 1.7, "high": 1.7, "low": 1.7, "buy": False, "rank": 0, "stop": 0.0}
    st.analyze = lambda cs, ok=True: dict(s)
    step(pf, {"X": [bar(30 * H, 1.7)]}, st, runners=True)       # past 24h, +70%, below 2x
    assert "X" in pf.positions


if __name__ == "__main__":
    assert config.MOON["ride"] == 0.50
    for f in [test_runner_not_sold_on_rules, test_runner_sold_on_trail,
              test_non_runner_and_backtests_unchanged, test_early_mover_time_limit_skipped_for_runner]:
        f()
        print("ok", f.__name__)
