"""Offline checks for dex_floor_study.py (no network): the live exit and each profit-floor variant on hand-made paths."""
import unittest

import dex_floor_study as S
from dex_exit_study import DAY, HOUR

T0 = 1_700_000_000 // HOUR * HOUR
V = {v["key"]: v for v in S.VARIANTS}


def bars(closes):
    T = [T0 + i * HOUR for i in range(len(closes))]
    O = [closes[0]] + closes[:-1]
    H = [max(o, c) for o, c in zip(O, closes)]
    L = [min(o, c) for o, c in zip(O, closes)]
    return T, O, H, L, list(closes)


def run(closes, key, **kw):
    T, O, H, L, C = bars(closes)
    return S.simulate(T, O, H, L, C, HOUR, 0, V[key], log=True, **kw)


# TEXTIT: +104% within 2 hours, back to -24%, then drifts to +6%, flat to the end of 20 days
TEXTIT = [1.0, 1.5, 2.04, 1.7, 1.3, 1.0, 0.76, 0.9, 1.06] + [1.06] * (20 * 24)


class T(unittest.TestCase):
    def test_live_holds_textit_to_the_clock(self):
        x = run(TEXTIT, "live")
        self.assertEqual(x["sells"][-1][4], "time limit")
        self.assertAlmostEqual(x["sells"][-1][2], 1.06, delta=0.01)

    def test_a_break_even_floor(self):
        x = run(TEXTIT, "a")
        self.assertAlmostEqual(x["sells"][-1][2], S.BE, delta=0.01)
        self.assertLess(abs(x["ret"]), 0.03)                       # about flat after costs

    def test_b_floor_25(self):
        x = run(TEXTIT, "b")
        self.assertAlmostEqual(x["sells"][-1][2], 1.25, delta=0.01)

    def test_c_trail_40_from_peak(self):
        x = run(TEXTIT, "c")
        self.assertAlmostEqual(x["sells"][-1][2], 2.04 * 0.6, delta=0.01)

    def test_d_floor_50_and_trail_after_3x(self):
        self.assertAlmostEqual(run(TEXTIT, "d")["sells"][-1][2], 1.5, delta=0.01)
        up = [1.0 + 0.1 * i for i in range(41)] + [5.0 - 0.1 * i for i in range(1, 40)]      # 5x then down
        self.assertAlmostEqual(run(up, "d")["sells"][-1][2], 2.5, delta=0.11)

    def test_e_half_at_2x_rest_keeps_clock(self):
        x = run(TEXTIT, "e")
        self.assertEqual(x["sells"][0][4], "sell 50% at 2x")
        self.assertAlmostEqual(x["sells"][0][2], 2.0, delta=0.01)
        self.assertEqual(x["sells"][-1][4], "time limit")
        y = run(TEXTIT, "e_dex")                                   # dex.py tp1: no clock, stop at break-even
        self.assertAlmostEqual(y["sells"][-1][2], S.BE, delta=0.01)

    def test_floors_dont_arm_below_trigger(self):
        c = [1.0, 1.45, 1.0, 0.5] + [0.5] * (15 * 24)
        for k in ("a", "b", "c", "d"):
            self.assertEqual(run(c, k)["sells"][-1][4], "time limit")

    def test_runner_at_day_14_and_rug(self):
        up = [1.0] + [2.5] * (14 * 24 + 10) + [2.5 - 0.02 * i for i in range(1, 100)]
        x = run(up, "live")
        self.assertTrue(x["runner"])
        self.assertAlmostEqual(x["sells"][-1][2], 2.5 * (1 - S.EXIT["runner_at_limit"][1]), delta=0.03)
        r = run([1.0, 1.2, 1.3, 0.01], "a", rug={3})
        self.assertTrue(r["rug"])
        self.assertAlmostEqual(r["ret"], -0.95, delta=0.02)

    def test_clock_is_14_days(self):
        x = run([1.0] * (20 * 24), "live")
        self.assertAlmostEqual((x["exit_t"] - (T0 + HOUR)) / DAY, S.EXIT["max_hold_days"], delta=0.05)


if __name__ == "__main__":
    unittest.main()
