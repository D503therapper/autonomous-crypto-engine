"""Offline checks for dex_consolidated_study.account (the dex.py-style account)."""
import unittest

import config

import dex_consolidated_study as S
from dex_exit_study import DAY, HOUR

T0 = 1_700_000_000 // HOUR * HOUR


def sig(n, t, k, sym=None, liq=200_000):
    return {"id": n, "t": T0 + t, "k": k, "sym": sym or k, "liq": liq, "age": 10, "vol24": 200_000}


class T(unittest.TestCase):
    def test_skipped_signal_does_not_lock_the_pool(self):
        sigs = [sig(0, 0, "a"), sig(1, HOUR, "b"), sig(2, 3 * DAY, "b")]
        res = [(1.0, T0 + 2 * DAY, 2, False), (-0.5, T0 + 10 * DAY, 1, False), (0.5, T0 + 5 * DAY, 1, False)]
        r = S.account(sigs, res, T0, T0 + 30 * DAY, slots=1, log=True)
        self.assertEqual([s["id"] for s, _, _ in r["log"]], [0, 2])     # b skipped (slot full), re-entered on day 3
        self.assertAlmostEqual(r["final"], 1000 + 1000 * 1.0 + 1000 * 0.5, places=6)   # 1 slot = all equity, b capped at 0.5% of $200k

    def test_cooldown_and_same_symbol(self):
        sigs = [sig(0, 0, "a"), sig(1, HOUR, "a2", sym="a"), sig(2, 2 * DAY + HOUR, "a"), sig(3, 4 * DAY, "a")]
        res = [(0.0, T0 + 2 * DAY, 1, False)] * 4
        r = S.account(sigs, res, T0, T0 + 30 * DAY, slots=5, log=True)
        self.assertEqual([s["id"] for s, _, _ in r["log"]], [0, 3])     # same symbol held; then 1-day cooldown

    def test_liquidity_caps_the_stake(self):
        r = S.account([sig(0, 0, "a", liq=20_000_000)], [(0.0, T0 + DAY, 1, False)], T0, T0 + 30 * DAY, log=True)
        self.assertAlmostEqual(r["log"][0][1], 1000 * config.DEX["tiers"]["A"]["pct"])   # tier-A share of $1,000
        r = S.account([sig(0, 0, "a", liq=50_000)], [(0.0, T0 + DAY, 1, False)], T0, T0 + 30 * DAY, log=True)
        self.assertEqual(r["taken"], 0)                                  # below the $100k floor


if __name__ == "__main__":
    unittest.main()
